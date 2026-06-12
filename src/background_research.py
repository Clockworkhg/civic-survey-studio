"""研究背景材料读取模块。

从 Deep-Research-skills 的 /research-deep 产出目录中读取结构化 JSON 调研结果，
将其转换为适合注入到报告「研究背景与问题提出」章节的语境文本。

支持的输入格式：
  - 单个 JSON 文件（如 report.md 转换后的结构）
  - 目录下的多个 JSON 文件（如 results/*.json）
  - 用户手写的 Markdown 背景材料

使用示例:
    from src.background_research import build_background_context

    bg_text = build_background_context("background/政务服务改革调研")
    print(bg_text)  # Markdown 格式的政策背景文本
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# 保留这些字段作为背景语境（按优先级排序）
_PRIORITY_TEXT_FIELDS = [
    "findings", "key_findings", "summary", "description",
    "background", "context", "policy_content", "policy_summary",
    "implementation", "current_status", "reform_measures",
    "impact", "evaluation", "challenges", "recommendations",
    "content", "overview", "abstract",
]

# 跳过这些元数据字段
_SKIP_FIELDS = {
    "name", "id", "uncertain", "_source_file", "filename",
    "timestamp", "version", "hash",
}


def build_background_context(
    source: Union[str, Path],
    max_items: int = 20,
    max_chars_per_item: int = 1500,
) -> str:
    """从调研结果目录构建研究背景语境文本。

    扫描目录中的所有 JSON 文件，提取结构化内容，
    格式化为 Markdown 文本供 LLM 报告生成使用。

    Args:
        source: 调研结果目录路径或单个 JSON 文件路径。
        max_items: 最多纳入的调研条目数。
        max_chars_per_item: 每条的字符数上限。

    Returns:
        Markdown 格式的背景语境文本。
        如果目录不存在或没有可解析的 JSON，返回空字符串。
    """
    source_path = Path(source).resolve()

    if not source_path.exists():
        logger.warning(f"Background source not found: {source_path}")
        return ""

    # ── 收集所有 JSON 文件 ──
    json_files: List[Path] = []
    if source_path.is_dir():
        for f in source_path.rglob("*.json"):
            if f.name not in {"outline.yaml", "fields.yaml"} and f not in json_files:
                json_files.append(f)
    elif source_path.suffix.lower() in (".json",):
        json_files.append(source_path)
    elif source_path.suffix.lower() in (".md", ".txt"):
        return source_path.read_text(encoding="utf-8")[:max_chars_per_item * max_items]

    if not json_files:
        logger.warning(f"No JSON files found in {source_path}")
        return ""

    # ── 解析每个 JSON 文件 ──
    items: List[Dict[str, Any]] = []
    for jf in sorted(json_files)[:max_items]:
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
            if isinstance(data, list):
                items.extend(data)
            elif isinstance(data, dict):
                items.append(data)
        except json.JSONDecodeError as e:
            logger.debug(f"Skipping invalid JSON {jf.name}: {e}")
        except Exception as e:
            logger.debug(f"Error reading {jf.name}: {e}")

    if not items:
        logger.warning(f"No valid JSON content extracted from {source_path}")
        return ""

    # ── 格式化为语境文本 ──
    sections: List[str] = [f"## 研究背景材料\n\n> 以下内容基于对 {len(json_files)} 个来源的结构化调研，供报告撰写参考。\n"]

    for i, item in enumerate(items[:max_items], 1):
        # 提取条目名称
        name = _extract_name(item, i)

        # 提取文本内容（优先高质量字段）
        text_parts = _extract_text_fields(item)

        # 组装
        if text_parts:
            sections.append(f"### {i}. {name}\n")
            combined = "\n".join(text_parts)
            if len(combined) > max_chars_per_item:
                combined = combined[:max_chars_per_item] + "\n\n...(内容截断)"
            sections.append(combined)
            sections.append("")

    result = "\n".join(sections)
    logger.info(f"Built background context: {len(items)} items, {len(result)} chars")
    return result


def _extract_name(item: Dict[str, Any], index: int) -> str:
    """从 JSON 条目中提取名称。"""
    # 直接字段
    for key in ("name", "title", "topic", "policy_name", "document_title"):
        val = item.get(key)
        if val and isinstance(val, str) and val.strip():
            return val.strip()

    # 嵌套在一个 category 下
    for category in item:
        if isinstance(item[category], dict):
            for key in ("name", "title", "topic"):
                val = item[category].get(key)
                if val and isinstance(val, str) and val.strip():
                    return val.strip()

    return f"调研条目 {index}"


def _extract_text_fields(item: Dict[str, Any]) -> List[str]:
    """从 JSON 条目中提取所有相关文本字段。

    递归遍历字典，收集所有文本内容。
    按优先级排序：先提取优先字段，再补充其他。
    """
    result: List[str] = []
    seen: set = set()

    # ── 第一遍：提取优先字段 ──
    for key in _PRIORITY_TEXT_FIELDS:
        val = item.get(key)
        if val:
            formatted = _format_value(key, val)
            if formatted and formatted not in seen:
                result.append(formatted)
                seen.add(formatted)

    # ── 第二遍：递归遍历嵌套 dict ──
    for key, val in item.items():
        if key in _SKIP_FIELDS or key in _PRIORITY_TEXT_FIELDS:
            continue
        if isinstance(val, dict):
            nested_texts = _extract_text_fields(val)
            for nt in nested_texts:
                if nt not in seen:
                    result.append(nt)
                    seen.add(nt)
        elif isinstance(val, str) and val.strip() and len(val) > 20:
            text = f"**{key}**: {val}"
            if text not in seen:
                result.append(text)
                seen.add(text)
        elif isinstance(val, list):
            list_text = _format_list_field(key, val)
            if list_text and list_text not in seen:
                result.append(list_text)
                seen.add(list_text)

    # ── 第三遍：cleanup — 移除过短/无意义的内容 ──
    result = [r for r in result if len(r) > 10]

    return result


def _format_value(key: str, val: Any) -> Optional[str]:
    """格式化单个字段值。"""
    if isinstance(val, str):
        stripped = val.strip()
        if not stripped or stripped == "[不确定]" or stripped == "N/A":
            return None
        # 用字段名作为标签
        label = _field_label(key)
        return f"**{label}**: {stripped}"
    elif isinstance(val, (list, tuple)):
        items = [str(v) for v in val if str(v).strip() and str(v).strip() != "[不确定]"]
        if not items:
            return None
        label = _field_label(key)
        return f"**{label}**: {'; '.join(items)}" if len(items) <= 3 else f"**{label}**:\n- " + "\n- ".join(items)
    elif isinstance(val, dict):
        # 嵌套字典：可能是子分类
        nested = _extract_text_fields(val)
        if nested:
            return "\n".join(nested)
        return None
    elif isinstance(val, (int, float)):
        return f"**{_field_label(key)}**: {val}"
    return None


def _format_list_field(key: str, val: List) -> Optional[str]:
    """格式化列表字段。"""
    items = []
    for v in val:
        if isinstance(v, dict):
            # 每个元素是 dict → 可能包含 name + description
            name = v.get("name", v.get("title", ""))
            desc = v.get("description", v.get("findings", v.get("summary", "")))
            if name and desc:
                items.append(f"- **{name}**: {desc}")
            elif name:
                items.append(f"- {name}")
            else:
                # 将 dict 的所有文本字段连接
                parts = _extract_text_fields(v)
                if parts:
                    items.append("; ".join(parts))
        elif isinstance(v, str) and v.strip():
            items.append(f"- {v.strip()}")

    if not items:
        return None

    label = _field_label(key)
    return f"**{label}**:\n" + "\n".join(items)


def _field_label(key: str) -> str:
    """将 JSON 字段名转为中文标签。"""
    mapping = {
        "findings": "主要发现",
        "key_findings": "关键发现",
        "summary": "摘要",
        "description": "描述",
        "background": "背景",
        "context": "语境",
        "policy_content": "政策内容",
        "policy_summary": "政策概要",
        "implementation": "实施情况",
        "current_status": "现状",
        "reform_measures": "改革措施",
        "impact": "影响",
        "evaluation": "评估",
        "challenges": "挑战",
        "recommendations": "建议",
        "content": "内容",
        "overview": "概述",
        "abstract": "摘要",
        "source": "来源",
        "date": "日期",
        "region": "地区",
        "scope": "范围",
        "status": "状态",
    }
    return mapping.get(key, key)


def list_background_sources(workspace_dir: Union[str, Path] = ".") -> List[Dict[str, Any]]:
    """列出工作目录中可用的背景调研数据。

    扫描以 'background' 或 'research' 开头的子目录，
    返回每个可用的调研项目摘要。

    Args:
        workspace_dir: 工作目录路径。

    Returns:
        [{"name": "...", "path": "...", "json_count": N, "size_kb": N}, ...]
    """
    root = Path(workspace_dir).resolve()
    sources = []

    for child in root.iterdir():
        if not child.is_dir():
            continue
        if not (child.name.startswith("background") or child.name.startswith("research")):
            continue

        json_count = 0
        total_size = 0
        for jf in child.rglob("*.json"):
            json_count += 1
            try:
                total_size += jf.stat().st_size
            except OSError:
                pass

        if json_count > 0 or (child / "outline.yaml").exists():
            sources.append({
                "name": child.name,
                "path": str(child),
                "json_count": json_count,
                "size_kb": total_size // 1024 if total_size > 0 else 0,
                "has_outline": (child / "outline.yaml").exists(),
                "has_fields": (child / "fields.yaml").exists(),
            })

    return sorted(sources, key=lambda s: s["name"])
