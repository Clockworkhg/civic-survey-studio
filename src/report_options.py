"""Report configuration options — single source of truth for structure, style, length, theme.

Both app.py (Streamlit dropdowns) and llm_prompts.py (prompt templates) read from
this module, ensuring the option lists never diverge.
"""

from __future__ import annotations

from typing import Dict, List


# ================================================================
# Report Structures (key used in prompt dispatch + session_state)
# ================================================================

REPORT_STRUCTURE_KEYS = [
    "通用调研报告",
    "学术论文式报告",
    "政务决策报告",
    "商业分析报告",
    "课程作业报告",
]

REPORT_STRUCTURE_LABELS: Dict[str, str] = {
    "通用调研报告": "通用调研报告",
    "学术论文式报告": "学术论文式报告",
    "政务决策报告": "政务决策报告",
    "商业分析报告": "商业分析报告",
    "课程作业报告": "课程作业报告",
}

REPORT_STRUCTURE_DESCRIPTIONS: Dict[str, str] = {
    "通用调研报告": "标准 8 章结构，适合一般问卷调查分析。",
    "学术论文式报告": "学术论文格式：摘要/关键词/理论基础/假设检验/实证结果/讨论/结论/局限。支持文献综述和背景注入。",
    "政务决策报告": "政务汇报格式：基本情况/数据表现/问题风险/原因分析/对策建议/方法说明。适合政府内部汇报。",
    "商业分析报告": "商业咨询格式：分析概览/核心指标/群体差异/影响因素/机会风险/行动建议/数据口径。",
    "课程作业报告": "课程作业格式：选题说明/数据说明/变量说明/分析过程/主要结果/结论与反思/方法局限。",
}

# Structures that support background context injection
BG_APPLICABLE_STRUCTURES = ["学术论文式报告", "政务决策报告"]

# Structures that support literature review injection
LIT_APPLICABLE_STRUCTURES = ["学术论文式报告"]


# ================================================================
# Report Styles
# ================================================================

REPORT_STYLE_KEYS = [
    "课程作业风",
    "政务汇报风",
    "学术报告风",
    "商业分析风",
]

REPORT_STYLE_LABELS: Dict[str, str] = {k: k for k in REPORT_STYLE_KEYS}

REPORT_STYLE_DESCRIPTIONS: Dict[str, str] = {
    "课程作业风": "语言清楚自然，适合课堂展示，不过度正式。",
    "政务汇报风": "语言稳健、规范、谨慎，适合政府内部汇报。",
    "学术报告风": "强调研究问题、变量、方法、显著性、局限，适合学术场合。",
    "商业分析风": "强调指标表现、群体差异、业务解释和行动建议。",
}


# ================================================================
# Report Lengths
# ================================================================

REPORT_LENGTH_KEYS = [
    "简短版",
    "标准版",
    "详细版",
]

REPORT_LENGTH_LABELS: Dict[str, str] = {k: k for k in REPORT_LENGTH_KEYS}

REPORT_LENGTH_DESCRIPTIONS: Dict[str, str] = {
    "简短版": "800-1500 字，像执行摘要，2-3 分钟阅读。",
    "标准版": "2500-4000 字，适合普通调研报告，8-12 分钟阅读。",
    "详细版": "5000-8000 字，适合正式报告或论文初稿，15-25 分钟阅读。",
}


# ================================================================
# HTML Themes
# ================================================================

HTML_THEME_KEYS = [
    "学术论文白底风",
    "政务蓝白汇报风",
    "现代数据看板风",
    "简洁课程作业风",
    "商业咨询报告风",
]

HTML_THEME_LABELS: Dict[str, str] = {k: k for k in HTML_THEME_KEYS}

HTML_THEME_DESCRIPTIONS: Dict[str, str] = {
    "学术论文白底风": "白色背景，正式学术排版，适合论文和期刊投稿。",
    "政务蓝白汇报风": "蓝色标题栏，白色背景，适合政府内部汇报。",
    "现代数据看板风": "深色侧边栏，卡片式布局，适合数据展示。",
    "简洁课程作业风": "干净简洁，适合课程作业和教学场景。",
    "商业咨询报告风": "专业配色，适合商业咨询和客户交付。",
}


# ================================================================
# Helpers to get option lists for Streamlit dropdowns
# ================================================================

def get_structure_options() -> List[str]:
    """Return report structure options for Streamlit selectbox (label list)."""
    return REPORT_STRUCTURE_KEYS


def get_style_options() -> List[str]:
    """Return writing style options for Streamlit selectbox."""
    return REPORT_STYLE_KEYS


def get_length_options() -> List[str]:
    """Return report length options for Streamlit selectbox."""
    return REPORT_LENGTH_KEYS


def get_html_theme_options() -> List[str]:
    """Return HTML theme options for Streamlit selectbox."""
    return HTML_THEME_KEYS


def is_structure_supports_background(structure: str) -> bool:
    """Check if a report structure supports background context injection."""
    return structure in BG_APPLICABLE_STRUCTURES


def is_structure_supports_literature(structure: str) -> bool:
    """Check if a report structure supports literature review injection."""
    return structure in LIT_APPLICABLE_STRUCTURES
