"""文献综述编排模块。

编排流程:
  1. 学术 API 文献检索（literature_search.search_papers）
  2. 构建调查上下文（survey_context → 变量描述 + 关键发现摘要）
  3. 调用 LLM 合成文献综述（基于真实检索结果）
  4. 返回综述文本 + 论文元数据，供主报告注入

使用示例:
    from src.literature_review import generate_literature_review

    result = generate_literature_review(
        literature_config={"enabled": True, "keywords": "公众满意度 政务服务",
                          "max_sources": 15, "year_range": "近10年"},
        survey_context={"report_title": "...", "variable_descriptions": "...", ...},
        llm_provider_config=provider_config,
        llm_api_key=api_key,
        llm_model=model,
    )
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from src.literature_search import search_papers, PaperRecord
from src.llm_prompts import build_literature_review_prompt

logger = logging.getLogger(__name__)


def generate_literature_review(
    literature_config: Dict[str, Any],
    survey_context: Dict[str, Any],
    llm_provider_config: Dict[str, Any] = None,
    llm_api_key: str = "",
    llm_model: str = "",
    llm_provider_key: str = "",
    llm_chat_path: str = "/chat/completions",
    llm_temperature: float = 0.3,
    llm_max_tokens: int = 4096,
    extra_headers: Optional[Dict[str, str]] = None,
    llm_call_fn: Any = None,
    # P1.5: unified LLMConfig takes precedence
    llm_config: Any = None,
) -> Dict[str, Any]:
    """生成文献综述（基于真实学术文献检索）。

    流程：
      1. 解析配置参数
      2. 调用学术 API 搜索论文
      3. 构建 LLM 提示词（包含论文列表 + 调查上下文）
      4. 调用 LLM 合成文献综述
      5. 返回综述文本 + 论文元数据

    Args:
        literature_config: 文献配置
            - enabled: bool
            - keywords: str（研究关键词）
            - max_sources: int（5-50）
            - year_range: str（"不限" | "近5年" | "近10年" | "近20年"）
        survey_context: 调查上下文
            - report_title: str
            - research_subject: str
            - target_variable: str
            - variable_descriptions: str
            - key_findings_summary: str
        llm_provider_config: LLM 厂商配置
        llm_api_key: API Key
        llm_model: 模型名
        llm_provider_key: 厂商标识
        llm_chat_path: 自定义 API 路径
        llm_temperature: LLM 温度
        llm_max_tokens: 最大输出 token
        extra_headers: 额外请求头
        llm_call_fn: 可选的 LLM 调用函数（用于测试注入）。签名同 call_llm。

    Returns:
        {
            "success": bool,
            "literature_review_text": str,       # 合成的文献综述（Markdown）
            "papers_found": List[dict],          # 所有搜索到的论文
            "papers_used": List[dict],           # LLM 实际引用的论文（估算）
            "search_stats": {                    # 搜索统计
                "total_searched": int,
                "s2_count": int,
                "openalex_count": int,
                "crossref_count": int,
            },
            "warnings": List[str],
            "error": str,
        }
    """
    result: Dict[str, Any] = {
        "success": False,
        "literature_review_text": "",
        "papers_found": [],
        "papers_used": [],
        "search_stats": {
            "total_searched": 0,
            "s2_count": 0,
            "openalex_count": 0,
            "crossref_count": 0,
        },
        "warnings": [],
        "error": "",
    }

    # ── P1.5: 统一 LLMConfig → 回退到旧参数 ──
    from src.config_models import LLMConfig
    if llm_config is not None:
        _llm = llm_config
    else:
        _llm = LLMConfig.from_legacy_kwargs(
            provider_config=llm_provider_config or {},
            api_key=llm_api_key,
            model=llm_model,
            provider_key=llm_provider_key,
            chat_path=llm_chat_path,
            temperature=llm_temperature,
            max_tokens=llm_max_tokens,
            extra_headers=extra_headers,
        )

    # ── 预检查 ──
    if not literature_config or not literature_config.get("enabled"):
        result["error"] = "文献综述功能未启用。"
        return result

    keywords = (literature_config.get("keywords") or "").strip()
    if not keywords:
        result["error"] = "未输入研究关键词，跳过文献检索。"
        result["warnings"].append("未输入研究关键词，跳过文献检索。")
        return result

    max_sources = int(literature_config.get("max_sources", 15))
    max_sources = max(5, min(50, max_sources))

    year_from, year_to = parse_year_range(literature_config.get("year_range", "不限"))

    # ── Step 1: 学术文献检索 ──
    logger.info(f"Searching literature: keywords='{keywords}', max={max_sources}, "
                f"year_from={year_from}, year_to={year_to}")

    try:
        papers = search_papers(
            keywords=keywords,
            max_results=max_sources,
            year_from=year_from,
            year_to=year_to,
            timeout=25.0,
        )
    except Exception as e:
        logger.error(f"Literature search failed: {e}")
        result["error"] = f"文献检索失败: {e}"
        result["warnings"].append(f"文献检索失败: {e}")
        return result

    if not papers:
        result["error"] = "未找到与关键词相关的文献。"
        result["warnings"].append(
            f"未找到与关键词「{keywords}」相关的文献。请尝试调整关键词后重新生成。"
        )
        return result

    # 统计
    from collections import Counter
    source_counts = Counter(p.source for p in papers)
    result["search_stats"] = {
        "total_searched": len(papers),
        "s2_count": source_counts.get("semantic_scholar", 0),
        "openalex_count": source_counts.get("openalex", 0),
        "crossref_count": source_counts.get("crossref", 0),
    }
    result["papers_found"] = [p.to_dict() for p in papers]
    result["papers_used"] = result["papers_found"]  # 初始时相同，LLM 可能部分引用
    result["warnings"].append(
        f"共检索到 {len(papers)} 篇相关文献，将基于此合成文献综述。"
    )

    # ── Step 2: 构建 LLM 提示词 ──
    system_prompt, user_prompt = build_literature_review_prompt(
        papers=result["papers_found"],
        survey_context=survey_context,
    )

    # ── Step 3: 调用 LLM 合成文献综述 ──
    try:
        if llm_call_fn is not None:
            llm_result = llm_call_fn(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                llm_config=_llm,
            )
        else:
            from src.llm_client import call_llm
            llm_result = call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                llm_config=_llm,
            )
    except Exception as e:
        logger.error(f"LLM call for literature review failed: {e}")
        result["error"] = f"文献综述 LLM 合成失败: {e}"
        result["warnings"].append(
            f"文献综述 LLM 合成失败: {e}。主报告将使用不含文献综述的结构。"
        )
        return result

    if not llm_result.get("success"):
        err_msg = llm_result.get("error", "未知 LLM 错误")
        result["error"] = f"文献综述 LLM 合成失败: {err_msg}"
        result["warnings"].append(
            f"文献综述 LLM 合成失败: {err_msg}。主报告将使用不含文献综述的结构。"
        )
        return result

    review_text = llm_result.get("content", "").strip()
    if not review_text:
        result["error"] = "LLM 返回了空白文献综述。"
        result["warnings"].append("LLM 返回了空白文献综述。")
        return result

    result["success"] = True
    result["literature_review_text"] = review_text
    result["warnings"].append("文献综述已成功合成。")

    logger.info(
        f"Literature review generated: {len(review_text)} chars, "
        f"based on {len(papers)} papers"
    )

    return result


# ================================================================
# 工具函数
# ================================================================

def parse_year_range(year_range: str) -> Tuple[Optional[int], Optional[int]]:
    """将 UI 年份范围标签转为 from_year, to_year。

    Args:
        year_range: "不限" | "近5年" | "近10年" | "近20年"

    Returns:
        (year_from, year_to)，year_to 始终为 None（包含至今）
    """
    current_year = date.today().year
    mapping = {
        "不限": None,
        "近5年": current_year - 5,
        "近10年": current_year - 10,
        "近20年": current_year - 20,
    }
    year_from = mapping.get(year_range)
    return year_from, None
