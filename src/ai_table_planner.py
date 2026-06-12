"""AI 数据理解与分析方案生成器。

调用 LLM 读取 table_understanding_payload，输出结构化的 analysis_blueprint。
AI 只推荐「应该如何分析」，不能声称「已经发现了什么结果」。

流程:
  table_understanding_payload → LLM → analysis_blueprint → user confirms
  → analysis_recipe_runner executes → analysis_payload → AI report
"""

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.llm_client import call_llm

logger = logging.getLogger(__name__)


# ================================================================
# JSON 安全序列化：递归转换 numpy/pandas 类型为 Python 原生类型
# ================================================================

def make_json_safe(obj: Any) -> Any:
    """递归将 numpy/pandas 类型转换为 JSON 可序列化的 Python 原生类型。

    处理:
      - np.integer → int
      - np.floating → float（NaN / inf → None）
      - np.bool_ → bool
      - np.ndarray → list
      - pd.Timestamp / datetime / date → isoformat 字符串
      - pd.NaT → None
      - dict / list / tuple / set → 递归处理
      - dict key → str
    """
    # ── pandas Timestamp ──
    if isinstance(obj, (pd.Timestamp,)):
        return obj.isoformat()
    # NaT / NaN 必须在 datetime 之前（NaT 是 datetime 的子类）
    try:
        if pd.isna(obj) and not isinstance(obj, (str, list, dict, tuple, set)):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    # ── numpy 标量 ──
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        val = float(obj)
        if np.isnan(val) or np.isinf(val):
            return None
        return val
    if isinstance(obj, (np.bool_,)):
        return bool(obj)

    # ── numpy 数组 ──
    if isinstance(obj, (np.ndarray,)):
        return [make_json_safe(v) for v in obj.tolist()]

    # ── 容器类型 ──
    if isinstance(obj, dict):
        return {str(k): make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [make_json_safe(v) for v in obj]

    # ── 其他：直接返回（str / int / float / bool / None）──
    return obj


# ================================================================
# Prompt 模板
# ================================================================

_TABLE_UNDERSTANDING_SYSTEM_PROMPT = """你是一个专业的数据分析规划助手。你的任务是：

1. 理解用户上传的表格数据（基于程序提供的 table_understanding_payload）
2. 推荐适合的分析方案（变量选择、分析方法、图表、报告结构）

## 核心约束

1. **只能基于 table_understanding_payload 进行规划**：你收到的 payload 包含数据集的结构信息、变量元信息和压缩统计摘要。不能编造 payload 中不存在的数据。
2. **不能编造变量**：所有推荐的变量必须存在于 payload 的 variable_schema 中。
3. **不能声称已经发现了结果**：你是分析规划师，不是结果报告师。你只能推荐「应该如何分析」，不能说「已经发现了什么」。
4. **推荐必须可执行**：每个推荐的变量组合必须与 payload 中的变量类型匹配。
5. **如变量不适合分析，说明原因**。
6. **如数据更适合探索性分析，明确说明**。
7. **如果核心变量不明确，推荐 2-5 个候选**。
8. **充分利用变量说明表信息**：如果 variable_schema 中有 variable_usage_from_dict 和 value_labels，应充分利用。
9. **隐私风险变量**：如果 payload 中标注了隐私风险，说明建议以聚合或脱敏方式使用。
10. **派生变量必须说明来源和计算方法**，并要求用户确认。

## 变量组合推荐指南

你需要根据不同变量类型推荐以下组合：

1. **核心变量 + 分组变量** → 群体差异分析
   - 核心变量是关心的结果（如满意度、购买金额）
   - 分组变量是分类变量（如性别、地区、会员等级）
   - 用于卡方检验、t 检验、方差分析

2. **核心变量 + 解释变量** → 相关/回归分析
   - 解释变量是数值或有序变量
   - 用于 Pearson/Spearman 相关、OLS 回归

3. **分类变量 × 分类变量** → 交叉分析
   - 两个分类变量做卡方检验和交叉表
   - 如：渠道 × 满意度等级、地区 × 是否推荐

4. **分类变量 × 数值变量** → 分组均值比较
   - 如：性别 × 满意度评分、地区 × 购买金额
   - 使用 t 检验或 ANOVA

5. **数值变量 × 数值变量** → 相关分析
   - 两个数值变量做相关分析
   - 如：等待时间 × 满意度、浏览时长 × 购买金额

6. **综合指标** → 多个评分变量取均值
   - 如：服务体验指数 = 各服务维度评分的均值
   - 必须说明来源变量和计算方法
   - 如需标准化或反向计分，必须说明

## 输出格式

你必须输出严格符合以下 JSON Schema 的 analysis_blueprint。不要输出任何 JSON 之外的内容。

```json
{
  "dataset_understanding": {
    "dataset_type": "survey / transaction / education / etc.",
    "possible_research_subject": "对该数据研究对象的推测（1-2句话）",
    "main_analysis_theme": "该数据最可能的分析主题",
    "summary": "对数据集的整体理解（2-4句话）"
  },
  "recommended_report_titles": ["标题1", "标题2", "标题3"],
  "target_variable_candidates": [
    {
      "variable": "列名",
      "display_name": "显示名",
      "reason": "推荐理由",
      "priority": "high/medium/low"
    }
  ],
  "group_variable_candidates": [
    {
      "variable": "列名",
      "display_name": "显示名",
      "reason": "推荐理由",
      "priority": "high/medium/low"
    }
  ],
  "explanatory_variable_candidates": [
    {
      "variable": "列名",
      "display_name": "显示名",
      "reason": "推荐理由",
      "priority": "high/medium/low"
    }
  ],
  "derived_variable_suggestions": [
    {
      "new_variable_name": "新变量名",
      "method": "计算方法（如 mean / standardized_mean / reverse_score + mean）",
      "source_variables": ["源变量1", "源变量2"],
      "reason": "创建理由",
      "requires_user_confirmation": true
    }
  ],
  "analysis_recipes": [
    {
      "recipe_id": "唯一ID",
      "recipe_name": "推荐名称",
      "analysis_type": "categorical_frequency / numeric_descriptive / ordinal_distribution / categorical_categorical_chi_square / categorical_numeric_group_compare / numeric_numeric_correlation / linear_regression",
      "variables": ["变量1", "变量2（如适用）"],
      "method": "统计方法名",
      "reason": "推荐理由",
      "priority": "high/medium/low",
      "expected_output": "预期产出描述",
      "limitations": "该方法局限"
    }
  ],
  "chart_plan": [
    {
      "chart_name": "图表名",
      "chart_type": "bar / pie / histogram / scatter / box / heatmap / radar",
      "variables": ["变量"],
      "reason": "推荐理由"
    }
  ],
  "report_structure_recommendation": {
    "recommended_structure": "通用调研报告 / 学术论文式报告 / 政务决策报告 / 商业分析报告 / 课程作业报告",
    "reason": "推荐理由"
  },
  "warnings": ["注意事项1", "注意事项2"]
}
```

## JSON 输出规则（必须遵守）

由于启用了 JSON 模式（response_format=json_object），你必须：

1. 输出纯 JSON，不要包裹在 ```json ``` 代码块中
2. 每个逗号都不能省略，对象/数组元素之间必须有逗号分隔
3. 字符串用双引号，内部双引号必须转义为 \\\"
4. 不允许尾随逗号（最后一个元素后不能有逗号）
5. 不允许注释
6. 如某个推荐项确实不存在（如派生变量建议），返回空数组 [] 而非省略字段
"""


# ================================================================
# 主函数
# ================================================================

def generate_analysis_blueprint(
    table_understanding_payload: Dict[str, Any],
    provider_config: Dict[str, Any],
    api_key: str,
    model: str,
    temperature: float = 0.3,
    max_tokens: int = 8192,
    provider_key: str = "",
    chat_path: str = "/chat/completions",
    extra_headers: Optional[Dict[str, str]] = None,
    custom_options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """调用 LLM 生成分析方案蓝图。

    Args:
        table_understanding_payload: build_table_understanding_payload 的输出
        provider_config: LLM 厂商配置
        api_key: API Key
        model: 模型名
        temperature: 温度参数
        max_tokens: 最大输出 token
        provider_key: 厂商标识
        chat_path: 自定义 API 路径
        extra_headers: 额外请求头
        custom_options: 自定义选项（预留）

    Returns:
        {
            "success": bool,
            "blueprint": dict,    # 成功时的 analysis_blueprint
            "raw_response": str,  # LLM 原始响应
            "error": str,         # 失败时
            "llm_response": dict, # LLM 完整响应
        }
    """
    result: Dict[str, Any] = {
        "success": False,
        "blueprint": {},
        "raw_response": "",
        "error": "",
        "llm_response": None,
    }

    # ── 防御性检查 ──
    if not provider_config or not isinstance(provider_config, dict):
        result["error"] = "厂商配置为空或格式错误，请先在 AI 自动报告标签页中选择 AI 厂商。"
        return result
    if not provider_config.get("base_url", ""):
        result["error"] = f"厂商配置缺少 base_url，请检查厂商「{provider_config.get('display_name', provider_key)}」的配置。"
        return result
    if not api_key or not api_key.strip():
        result["error"] = "API Key 未配置，请在 AI 自动报告标签页中输入 API Key。"
        return result
    if not model or not model.strip():
        result["error"] = "模型名未指定，请在 AI 自动报告标签页中选择或输入模型名。"
        return result

    # ── 构建用户提示词 ──
    safe_payload = make_json_safe(table_understanding_payload)
    payload_json = json.dumps(safe_payload, ensure_ascii=False, indent=2)

    # 如果 payload 中有 user_goal，加入提示
    user_goal = table_understanding_payload.get("user_goal", {}).get("goal_text", "")
    goal_hint = ""
    if user_goal:
        goal_hint = f"\n\n## 用户的分析目标\n\n用户输入了以下分析目标：\n\n「{user_goal}」\n\n请在推荐分析方案时优先考虑这个目标。"

    user_prompt = f"""请基于以下 table_understanding_payload 理解数据结构并推荐分析方案。

## Table Understanding Payload

```json
{payload_json}
```
{goal_hint}

## 要求

1. 仔细阅读 variable_schema 了解每个变量的类型、含义和示例值。
2. 查看 data_quality_summary 了解数据质量问题。
3. 查看 quick_statistics 了解变量的基本分布。
4. 推荐适合的 target_variable、group_variables、explanatory_variables。
5. 推荐具体的 analysis_recipes（变量 + 方法组合）。
6. 推荐的变量必须存在于 payload 中。
7. 输出严格符合 JSON Schema 的 analysis_blueprint。
8. 已启用 JSON 模式，输出必须是合法 JSON，确保所有逗号正确、无尾随逗号。

请现在输出 analysis_blueprint JSON（纯 JSON，无需代码块包裹）。"""

    # ── 调用 LLM ──
    llm_result = call_llm(
        provider_config=provider_config,
        api_key=api_key,
        model=model,
        system_prompt=_TABLE_UNDERSTANDING_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        provider_key=provider_key,
        chat_path=chat_path,
        extra_headers=extra_headers,
        response_format={"type": "json_object"},
    )

    result["llm_response"] = llm_result

    if not llm_result.get("success"):
        result["error"] = f"LLM 调用失败: {llm_result.get('error', '未知错误')}"
        return result

    raw_content = llm_result.get("content", "")
    result["raw_response"] = raw_content

    if not raw_content.strip():
        result["error"] = "LLM 返回了空内容。"
        return result

    # ── 解析 JSON ──
    try:
        blueprint = _extract_json(raw_content)
        result["blueprint"] = blueprint
        result["success"] = True
    except json.JSONDecodeError as e:
        # 保存原始响应用于调试
        _save_debug_response(raw_content, "blueprint_parse_error")
        # 截取原始响应末尾（检测是否被截断）
        tail = raw_content[-200:] if len(raw_content) > 200 else raw_content
        result["error"] = (
            f"AI 输出 JSON 解析失败: {e}\n\n"
            f"原始响应末尾（检测截断）: ...{tail}"
        )
        result["blueprint"] = {"_raw": raw_content}
        logger.warning(f"analysis_blueprint JSON 解析失败: {e}")

    return result


def _save_debug_response(raw: str, tag: str = "debug") -> None:
    """保存 LLM 原始响应用于调试。"""
    import os
    try:
        debug_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")
        os.makedirs(debug_dir, exist_ok=True)
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(debug_dir, f"llm_debug_{tag}_{ts}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(raw)
        logger.info(f"LLM 调试响应已保存至: {path}")
    except Exception:
        pass  # 静默失败，不影响主流程


def _extract_json(content: str) -> Dict[str, Any]:
    """从 LLM 响应中提取并解析 JSON（含自动修复常见 LLM 语法错误）。"""
    import re

    content = content.strip()

    # 1. 尝试提取 ```json ... ``` 代码块
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', content, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
    else:
        # 2. 尝试提取最外层 { ... } 块（非贪婪匹配失败，用定位法）
        first_brace = content.find('{')
        if first_brace >= 0:
            json_str = content[first_brace:]
            # 从末尾找最后一个 }
            last_brace = json_str.rfind('}')
            if last_brace >= 0:
                json_str = json_str[:last_brace + 1]
            else:
                json_str = content
        else:
            json_str = content

    # 3. 尝试直接解析
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # 4. 自动修复常见 LLM JSON 错误后重试
    repaired = _repair_llm_json(json_str)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError as e2:
        # 5. 所有尝试均失败，提供错误位置的上下文
        pos = e2.pos
        start = max(0, pos - 120)
        end = min(len(json_str), pos + 120)
        snippet = json_str[start:end]
        raise json.JSONDecodeError(
            f"{e2.msg}（已尝试自动修复，仍失败。错误位置附近内容：…{snippet}…）",
            e2.doc, e2.pos,
        )


def _repair_llm_json(text: str) -> str:
    """修复 LLM 输出中常见的 JSON 语法错误。

    策略：
      1. 先做安全的正则修复（尾随逗号、双逗号）
      2. 然后迭代解析，利用 JSONDecodeError.pos 逐处插入缺失的逗号
    """
    import re

    # (a) 移除尾随逗号（在 ] 或 } 之前）—— 安全操作
    text = re.sub(r',(\s*[}\]])', r'\1', text)

    # (b) 移除连续逗号
    text = re.sub(r',\s*,', ',', text)

    # (c) 迭代修复：在解析器报错的位置尝试插入逗号
    max_attempts = 100
    prev_pos = -1
    for _ in range(max_attempts):
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError as e:
            if e.pos <= 0 or e.pos >= len(text):
                break
            # 防止在同位置死循环
            if e.pos == prev_pos:
                prev_pos = e.pos
                # 上次插入逗号无效，尝试跳过当前字符
                text = text[:e.pos] + text[e.pos + 1:]
            else:
                prev_pos = e.pos
                # 在错误位置插入逗号（适用于几乎所有 "Expecting X" 错误）
                text = text[:e.pos] + ',' + text[e.pos:]

    return text
