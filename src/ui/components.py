"""统一 UI 组件库。

基于 DESIGN.md 和 theme.py，提供可复用的 Streamlit 渲染组件。
所有主要页面必须使用这些组件保持视觉一致。

组件列表:
  - render_page_header()      页面标题区
  - render_pipeline_status()  流程状态条
  - render_status_card()      状态卡片
  - render_metric_card()      指标卡片
  - render_empty_state()      空状态卡片
  - render_config_summary()   当前分析方案摘要
  - render_section()          通用分区
  - render_warning_list()     警告列表
  - render_action_bar()       操作按钮栏
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import streamlit as st

from src.ui.theme import (
    COLORS,
    CARD_STYLE,
    AI_CARD_STYLE,
    ERROR_CARD_STYLE,
    PIPELINE_STATUS_COLORS,
    PIPELINE_STATUS_BG,
    RADIUS,
    SHADOWS,
    SPACING,
)


# ================================================================
# 内部 HTML 辅助
# ================================================================

def _html_safe(text: str) -> str:
    """转义 HTML 特殊字符。"""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _card_css(card_style: dict, extra: str = "") -> str:
    """生成内联卡片 CSS。"""
    return (
        f"background:{card_style['background']};"
        f"border:{card_style['border']};"
        f"border-radius:{card_style['border_radius']};"
        f"padding:{card_style['padding']};"
        f"box-shadow:{card_style['box_shadow']};"
        + extra
    )


# ================================================================
# 1. 页面标题区
# ================================================================

def render_page_header(
    title: str,
    subtitle: Optional[str] = None,
    step: Optional[str] = None,
) -> None:
    """渲染页面标题区。

    Args:
        title: 页面主标题
        subtitle: 可选副标题/说明
        step: 可选步骤标记，如 "步骤 2/5"
    """
    parts = []
    if step:
        parts.append(
            f'<span style="font-size:13px;color:{COLORS.text_muted};'
            f'background:{COLORS.surface_subtle};padding:2px 10px;'
            f'border-radius:{RADIUS["pill"]};">'
            f'{_html_safe(step)}</span>'
        )
    parts.append(
        f'<span style="font-size:22px;font-weight:650;color:{COLORS.text_strong};">'
        f'{_html_safe(title)}</span>'
    )
    header_html = (
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:4px;">'
        f'{"".join(parts)}</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)

    if subtitle:
        st.markdown(
            f'<p style="color:{COLORS.text_muted};font-size:13px;margin:0 0 16px 0;">'
            f'{_html_safe(subtitle)}</p>',
            unsafe_allow_html=True,
        )


# ================================================================
# 2. 流程状态条
# ================================================================

# 默认 5 步工作流
DEFAULT_PIPELINE_STEPS = [
    {"key": "data",     "label": "数据已加载",   "hint": "上传问卷数据"},
    {"key": "vars",     "label": "变量已识别",   "hint": "确认变量类型"},
    {"key": "config",   "label": "方案已配置",   "hint": "选择核心变量"},
    {"key": "analysis", "label": "分析已完成",   "hint": "执行统计分析"},
    {"key": "report",   "label": "报告可生成",   "hint": "导出分析报告"},
]


def render_pipeline_status(
    ctx: Any = None,
    steps: Optional[List[Dict[str, str]]] = None,
) -> None:
    """渲染流程状态条。

    根据 AnalysisContext 或 session_state 自动判断每步状态。
    如果无法判断，所有步骤显示为 pending。

    Args:
        ctx: AnalysisContext 实例（可选）
        steps: 自定义步骤列表，默认使用 DEFAULT_PIPELINE_STEPS
    """
    if steps is None:
        steps = DEFAULT_PIPELINE_STEPS

    # ── 判断各步状态 ──
    statuses = _resolve_pipeline_statuses(ctx, steps)

    # ── 渲染 ──
    items_html = []
    for i, step in enumerate(steps):
        status = statuses.get(step["key"], "pending")
        color = PIPELINE_STATUS_COLORS.get(status, COLORS.text_subtle)
        bg = PIPELINE_STATUS_BG.get(status, COLORS.surface_muted)

        dot = f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{color};margin-right:6px;"></span>'
        label_html = (
            f'{dot}<span style="font-size:13px;font-weight:500;color:{COLORS.text};">'
            f'{_html_safe(step["label"])}</span>'
        )
        if step.get("hint") and status in ("pending", "current"):
            label_html += (
                f' <span style="font-size:11px;color:{COLORS.text_muted};">'
                f'({_html_safe(step["hint"])})</span>'
            )

        items_html.append(
            f'<span style="display:inline-flex;align-items:center;'
            f'padding:6px 12px;background:{bg};border-radius:{RADIUS["pill"]};'
            f'white-space:nowrap;">{label_html}</span>'
        )

        # 箭头分隔
        if i < len(steps) - 1:
            items_html.append(
                f'<span style="color:{COLORS.text_subtle};margin:0 4px;font-size:12px;">→</span>'
            )

    container_html = (
        f'<div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px;'
        f'padding:10px 16px;background:{COLORS.surface};'
        f'border:1px solid {COLORS.border};border-radius:{RADIUS["md"]};'
        f'margin-bottom:{SPACING["lg"]};">'
        f'{"".join(items_html)}'
        f'</div>'
    )
    st.markdown(container_html, unsafe_allow_html=True)


def _resolve_pipeline_statuses(ctx: Any, steps: List[Dict[str, str]]) -> Dict[str, str]:
    """根据上下文解析各步骤状态。"""
    statuses: Dict[str, str] = {}
    raw_df_loaded = False
    schema_ready = False
    config_ready = False
    analysis_ready = False
    report_ready = False

    # 从 ctx 或 session_state 推断
    if ctx is not None:
        raw_df_loaded = ctx.df is not None and len(ctx.df) > 0
        schema_ready = ctx.variable_schema is not None and len(ctx.variable_schema) > 0
        config_ready = bool(ctx.target or ctx.user_analysis_config.get("target_variable"))
        analysis_ready = bool(ctx.analysis_results)
        # report_ready — 不自动判断，由具体页面自行设置
    else:
        # 从 session_state 推断
        raw_df_loaded = bool(
            st.session_state.get("_last_file_key")
            or st.session_state.get("_use_example_data")
            or st.session_state.get("_example_raw_df") is not None
        )
        schema_ready = raw_df_loaded  # schema 随数据加载自动生成
        cfg = st.session_state.get("generic_config", {})
        config_ready = bool(cfg.get("target_variable", ""))
        analysis_ready = bool(st.session_state.get("_analysis_results"))
        report_ready = bool(
            st.session_state.get("_generated_report")
            or st.session_state.get("ai_analysis_payload")
        )

    statuses["data"] = "done" if raw_df_loaded else "pending"
    statuses["vars"] = "done" if schema_ready else "pending"
    statuses["config"] = "done" if config_ready else ("current" if raw_df_loaded else "pending")
    statuses["analysis"] = "done" if analysis_ready else ("current" if config_ready else "pending")
    statuses["report"] = "done" if report_ready else ("current" if analysis_ready else "pending")

    return statuses


# ================================================================
# 3. 状态卡片
# ================================================================

def render_status_card(
    title: str,
    value: str = "",
    help_text: Optional[str] = None,
    status: str = "neutral",
) -> None:
    """渲染状态卡片 — 用于显示配置状态、API 状态等。

    Args:
        title: 卡片标题
        value: 状态值
        help_text: 可选帮助文本
        status: "neutral" | "success" | "warning" | "error"
    """
    status_colors = {
        "neutral": COLORS.text_muted,
        "success": COLORS.success,
        "warning": COLORS.warning,
        "error": COLORS.error,
    }
    status_icon = {
        "neutral": "",
        "success": "✓ ",
        "warning": "△ ",
        "error": "✕ ",
    }
    dot_color = status_colors.get(status, COLORS.text_muted)
    icon = status_icon.get(status, "")

    parts = [
        f'<div style="{_card_css(CARD_STYLE)}margin-bottom:12px;">',
        f'<div style="font-size:12px;color:{COLORS.text_muted};margin-bottom:4px;">'
        f'{_html_safe(title)}</div>',
        f'<div style="font-size:15px;font-weight:600;color:{COLORS.text};">'
        f'<span style="color:{dot_color};">{icon}</span>'
        f'{_html_safe(value)}</div>',
    ]
    if help_text:
        parts.append(
            f'<div style="font-size:11px;color:{COLORS.text_subtle};margin-top:4px;">'
            f'{_html_safe(help_text)}</div>'
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


# ================================================================
# 4. 指标卡片
# ================================================================

def render_metric_card(
    label: str,
    value: str,
    hint: Optional[str] = None,
    status: str = "neutral",
) -> None:
    """渲染指标卡片 — 用于数据质量指标、分析摘要等。

    Args:
        label: 指标标签
        value: 指标数值
        hint: 可选补充信息
        status: "neutral" | "success" | "warning" | "error"
    """
    status_colors = {
        "neutral": COLORS.primary,
        "success": COLORS.success,
        "warning": COLORS.warning,
        "error": COLORS.error,
    }
    vcolor = status_colors.get(status, COLORS.primary)

    parts = [
        f'<div style="{_card_css(CARD_STYLE)}text-align:center;min-width:100px;">',
        f'<div style="font-size:11px;color:{COLORS.text_muted};margin-bottom:4px;'
        f'text-transform:uppercase;letter-spacing:0.5px;">{_html_safe(label)}</div>',
        f'<div style="font-size:24px;font-weight:700;color:{vcolor};">'
        f'{_html_safe(str(value))}</div>',
    ]
    if hint:
        parts.append(
            f'<div style="font-size:11px;color:{COLORS.text_subtle};margin-top:4px;">'
            f'{_html_safe(hint)}</div>'
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


# ================================================================
# 5. 空状态卡片
# ================================================================

def render_empty_state(
    title: str,
    message: str,
    action_label: Optional[str] = None,
) -> None:
    """渲染空状态卡片 — 替代空白页。

    Args:
        title: 简短标题，如 "还不能生成图表"
        message: 原因和建议，如 '请先在"分析方案"中选择核心变量。'
        action_label: 可选操作提示
    """
    parts = [
        f'<div style="{_card_css(CARD_STYLE)}text-align:center;padding:32px 18px;">',
        f'<div style="font-size:15px;font-weight:600;color:{COLORS.text};margin-bottom:8px;">'
        f'{_html_safe(title)}</div>',
        f'<div style="font-size:13px;color:{COLORS.text_muted};max-width:480px;margin:0 auto;'
        f'line-height:1.6;">{_html_safe(message)}</div>',
    ]
    if action_label:
        parts.append(
            f'<div style="margin-top:16px;">'
            f'<span style="font-size:12px;color:{COLORS.primary};'
            f'background:{COLORS.primary_soft};padding:4px 12px;'
            f'border-radius:{RADIUS["pill"]};">{_html_safe(action_label)}</span>'
            f'</div>'
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


# ================================================================
# 6. 当前配置摘要
# ================================================================

def render_config_summary(
    config: Dict[str, Any],
    schema_df: Any = None,
) -> None:
    """渲染当前分析方案摘要卡片。

    Args:
        config: 分析配置字典 (generic_config)
        schema_df: 可选变量 schema DataFrame，用于解析显示名
    """
    target = config.get("target_variable", "")
    groups = config.get("group_variables", []) or []
    expl = config.get("explanatory_variables", []) or []
    title = config.get("report_title", "")

    # 尝试解析中文名
    cn_map = {}
    if schema_df is not None:
        try:
            for _, row in schema_df.iterrows():
                cn_map[row["column"]] = row.get("display_name", "") or row["column"]
        except Exception:
            pass

    def _label(col):
        cn = cn_map.get(col, "")
        if cn and cn != col:
            return f"{cn} ({col})"
        return col

    rows = []
    if title:
        rows.append(
            f'<tr><td style="color:{COLORS.text_muted};padding:3px 12px 3px 0;'
            f'font-size:13px;white-space:nowrap;">报告标题</td>'
            f'<td style="color:{COLORS.text};font-size:13px;padding:3px 0;">'
            f'{_html_safe(title)}</td></tr>'
        )
    rows.append(
        f'<tr><td style="color:{COLORS.text_muted};padding:3px 12px 3px 0;'
        f'font-size:13px;white-space:nowrap;">核心变量</td>'
        f'<td style="color:{COLORS.text};font-size:13px;padding:3px 0;">'
        + (f'<b>{_html_safe(_label(target))}</b>' if target else
           f'<span style="color:{COLORS.error};">未设置</span>')
        + '</td></tr>'
    )
    rows.append(
        f'<tr><td style="color:{COLORS.text_muted};padding:3px 12px 3px 0;'
        f'font-size:13px;white-space:nowrap;">分组变量</td>'
        f'<td style="color:{COLORS.text};font-size:13px;padding:3px 0;">'
        + (", ".join(_label(g) for g in groups) if groups else
           f'<span style="color:{COLORS.text_subtle};">未设置</span>')
        + '</td></tr>'
    )
    rows.append(
        f'<tr><td style="color:{COLORS.text_muted};padding:3px 12px 3px 0;'
        f'font-size:13px;white-space:nowrap;">解释变量</td>'
        f'<td style="color:{COLORS.text};font-size:13px;padding:3px 0;">'
        + (", ".join(_label(e) for e in expl) if expl else
           f'<span style="color:{COLORS.text_subtle};">未设置</span>')
        + '</td></tr>'
    )

    html = (
        f'<div style="{_card_css(CARD_STYLE)}margin-bottom:16px;">'
        f'<div style="font-size:14px;font-weight:600;color:{COLORS.text};'
        f'margin-bottom:8px;">当前分析方案</div>'
        f'<table style="border-collapse:collapse;">{"".join(rows)}</table>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ================================================================
# 7. 通用分区
# ================================================================

def render_section(
    title: str,
    description: Optional[str] = None,
) -> None:
    """渲染通用分区标题。

    Args:
        title: 分区标题
        description: 可选分区说明
    """
    st.markdown(
        f'<div style="margin-top:{SPACING["lg"]};margin-bottom:{SPACING["sm"]};">'
        f'<span style="font-size:16px;font-weight:650;color:{COLORS.text_strong};">'
        f'{_html_safe(title)}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if description:
        st.markdown(
            f'<p style="color:{COLORS.text_muted};font-size:12px;margin:0 0 12px 0;">'
            f'{_html_safe(description)}</p>',
            unsafe_allow_html=True,
        )


# ================================================================
# 8. 警告列表
# ================================================================

def render_warning_list(
    warnings: List[str],
    title: str = "提示",
) -> None:
    """渲染警告列表 — 使用温和的样式，不大面积铺色。

    Args:
        warnings: 警告消息列表
        title: 列表标题
    """
    if not warnings:
        return

    items = "".join(
        f'<li style="font-size:13px;color:{COLORS.text};margin-bottom:4px;">'
        f'{_html_safe(w)}</li>'
        for w in warnings
    )
    html = (
        f'<div style="background:{COLORS.warning_soft};'
        f'border-left:3px solid {COLORS.warning};'
        f'border-radius:{RADIUS["sm"]};padding:12px 16px;margin-bottom:12px;">'
        f'<div style="font-size:12px;font-weight:600;color:{COLORS.warning};'
        f'margin-bottom:6px;">{_html_safe(title)}</div>'
        f'<ul style="margin:0;padding-left:18px;">{items}</ul>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ================================================================
# 9. 操作按钮栏
# ================================================================

def render_action_bar(
    primary: Optional[Dict[str, Any]] = None,
    secondary: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """渲染操作按钮栏 — 用自定义 HTML 按钮替代默认 Streamlit 按钮。

    ⚠️ 当前实现使用 st.button，因为自定义 HTML 按钮无法直接绑定 Streamlit 回调。
    这里提供的是视觉容器，实际按钮仍用 st.button 渲染。

    Args:
        primary: 主按钮配置 {"label": str, "key": str, "disabled": bool}
        secondary: 次按钮列表 [{"label": str, "key": str}, ...]
    """
    buttons_html_parts = []
    if primary:
        disabled = primary.get("disabled", False)
        opacity = "0.5" if disabled else "1"
        buttons_html_parts.append(
            f'<button style="background:{COLORS.primary};color:#FFFFFF;'
            f'border:none;border-radius:8px;padding:8px 20px;'
            f'font-size:14px;font-weight:500;cursor:pointer;opacity:{opacity};"'
            f'{"disabled" if disabled else ""}>'
            f'{_html_safe(primary["label"])}</button>'
        )
    if secondary:
        for btn in secondary:
            buttons_html_parts.append(
                f'<button style="background:#FFFFFF;color:{COLORS.text};'
                f'border:1px solid {COLORS.border_strong};border-radius:8px;'
                f'padding:8px 16px;font-size:13px;cursor:pointer;">'
                f'{_html_safe(btn["label"])}</button>'
            )

    if buttons_html_parts:
        bar_html = (
            f'<div style="display:flex;align-items:center;gap:10px;'
            f'padding:12px 0;margin-bottom:{SPACING["md"]};">'
            f'{"".join(buttons_html_parts)}'
            f'</div>'
        )
        st.markdown(bar_html, unsafe_allow_html=True)

    # 实际 Streamlit 按钮（保持功能可用）
    if primary:
        st.button(
            primary["label"],
            key=primary.get("key", "action_primary"),
            disabled=primary.get("disabled", False),
            type="primary",
        )
    if secondary:
        for btn in secondary:
            st.button(
                btn["label"],
                key=btn.get("key", f"action_{btn['label']}"),
            )
