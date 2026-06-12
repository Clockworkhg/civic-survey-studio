"""统一视觉主题常量。

基于 DESIGN.md 的完整色彩、字体、间距、形状系统，
供所有 UI 组件和 CSS 样式引用。

使用方式:
    from src.ui.theme import COLORS, TYPOGRAPHY, SPACING, RADIUS, SHADOWS
"""

from __future__ import annotations

# ================================================================
# 色彩系统
# ================================================================


class _ColorGroup:
    """一组相关颜色，支持属性访问。"""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


COLORS = _ColorGroup(
    # ── 背景 ──
    bg="#F7F8FA",
    surface="#FFFFFF",
    surface_subtle="#F2F4F7",
    surface_muted="#EEF2F6",

    # ── 主色 ──
    primary="#245B7D",
    primary_hover="#1E4C69",
    primary_soft="#E8F1F6",

    # ── 辅色 ──
    secondary="#6B7280",
    secondary_soft="#F3F4F6",

    # ── 强调（AI 建议）──
    accent="#B7791F",
    accent_soft="#FFFCF5",
    accent_border="#F5D78E",

    # ── 语义色 ──
    success="#2F855A",
    success_soft="#EAF7F0",

    warning="#B7791F",
    warning_soft="#FFF8E5",

    error="#C2410C",
    error_soft="#FFF1EC",
    error_light="#FDBA9A",
    error_text="#9A3412",

    # ── 文字 ──
    text_strong="#18212F",
    text="#344054",
    text_muted="#667085",
    text_subtle="#98A2B3",

    # ── 边框 ──
    border="#E4E7EC",
    border_strong="#D0D5DD",
    divider="#EAECF0",
)


# ================================================================
# 字体
# ================================================================

FONT_FAMILY = (
    "Inter, ui-sans-serif, system-ui, -apple-system, "
    'BlinkMacSystemFont, "Segoe UI", "PingFang SC", '
    '"Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
)

TYPOGRAPHY = {
    "page_title":    {"size": "28px", "line_height": "36px", "weight": "700"},
    "section_title": {"size": "20px", "line_height": "28px", "weight": "650"},
    "card_title":    {"size": "16px", "line_height": "24px", "weight": "650"},
    "body":          {"size": "14px", "line_height": "22px", "weight": "400"},
    "small_body":    {"size": "13px", "line_height": "20px", "weight": "400"},
    "caption":       {"size": "12px", "line_height": "18px", "weight": "400"},
    "metric_value":  {"size": "28px", "line_height": "34px", "weight": "700"},
}


# ================================================================
# 间距
# ================================================================

SPACING = {
    "xs":   "4px",
    "sm":   "8px",
    "md":   "16px",
    "lg":   "24px",
    "xl":   "32px",
    "2xl":  "48px",
}


# ================================================================
# 圆角
# ================================================================

RADIUS = {
    "sm":   "6px",
    "md":   "10px",
    "lg":   "14px",
    "pill": "999px",
}


# ================================================================
# 阴影
# ================================================================

SHADOWS = {
    "card":  "0 1px 2px rgba(16, 24, 40, 0.04)",
    "raised": "0 4px 12px rgba(16, 24, 40, 0.06)",
}


# ================================================================
# 卡片预设
# ================================================================

CARD_STYLE = {
    "background": COLORS.surface,
    "border": f"1px solid {COLORS.border}",
    "border_radius": RADIUS["md"],
    "padding": "18px",
    "box_shadow": SHADOWS["card"],
}

AI_CARD_STYLE = {
    "background": COLORS.accent_soft,
    "border": f"1px solid {COLORS.accent_border}",
    "border_radius": RADIUS["md"],
    "padding": "18px",
    "box_shadow": SHADOWS["card"],
}

ERROR_CARD_STYLE = {
    "background": COLORS.error_soft,
    "border": f"1px solid {COLORS.error_light}",
    "border_radius": RADIUS["md"],
    "padding": "18px",
    "box_shadow": SHADOWS["card"],
}


# ================================================================
# 按钮预设
# ================================================================

PRIMARY_BUTTON_STYLE = {
    "background": COLORS.primary,
    "hover_background": COLORS.primary_hover,
    "color": "#FFFFFF",
    "border_radius": "8px",
    "min_height": "38px",
}

SECONDARY_BUTTON_STYLE = {
    "background": "#FFFFFF",
    "border": f"1px solid {COLORS.border_strong}",
    "color": COLORS.text,
    "hover_background": "#F9FAFB",
    "border_radius": "8px",
    "min_height": "38px",
}

GHOST_BUTTON_STYLE = {
    "background": "transparent",
    "color": COLORS.primary,
    "hover_background": COLORS.primary_soft,
    "border": "1px solid transparent",
    "border_radius": "8px",
    "min_height": "38px",
}


# ================================================================
# 流程状态颜色映射
# ================================================================

PIPELINE_STATUS_COLORS = {
    "pending":  COLORS.text_subtle,
    "current":  COLORS.primary,
    "done":     COLORS.success,
    "warning":  COLORS.warning,
    "blocked":  COLORS.error,
}

PIPELINE_STATUS_BG = {
    "pending":  COLORS.surface_muted,
    "current":  COLORS.primary_soft,
    "done":     COLORS.success_soft,
    "warning":  COLORS.warning_soft,
    "blocked":  COLORS.error_soft,
}
