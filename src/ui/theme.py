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
    bg="#F6F7F4",
    canvas_muted="#EEF1EE",
    surface="#FFFFFF",
    surface_raised="#FCFDFB",
    surface_subtle="#F1F4F2",
    surface_muted="#E8EEEA",

    # ── 主色 ──
    primary="#245B7D",
    primary_hover="#183D54",
    primary_soft="#E6F0F4",
    primary_line="#BFD3DE",

    # ── 辅色 ──
    secondary="#6B7280",
    secondary_soft="#F1F4F2",

    # ── 强调（AI 建议）──
    accent="#A65F2B",
    accent_hover="#7D431D",
    accent_soft="#FFF4E8",
    accent_border="#E9C9A5",

    # ── 语义色 ──
    success="#2F6F55",
    success_soft="#E8F3ED",

    warning="#B7791F",
    warning_soft="#FFF7E5",

    error="#B42318",
    error_soft="#FFF1ED",
    error_light="#F4B6A6",
    error_text="#8F1D14",

    info="#2F5F73",
    info_soft="#E8F1F4",

    # ── 文字 ──
    text_strong="#17212B",
    text="#344054",
    text_muted="#667085",
    text_subtle="#98A2B3",

    # ── 边框 ──
    border="#DDE3E0",
    border_strong="#C7D0CC",
    divider="#E7ECE8",
)


# ================================================================
# 字体
# ================================================================

FONT_FAMILY = (
    '"Source Han Sans SC", "Noto Sans CJK SC", "PingFang SC", '
    '"Microsoft YaHei", "Microsoft JhengHei", sans-serif'
)

TYPOGRAPHY = {
    "app_title":     {"size": "24px", "line_height": "32px", "weight": "700"},
    "page_title":    {"size": "22px", "line_height": "30px", "weight": "700"},
    "section_title": {"size": "17px", "line_height": "25px", "weight": "650"},
    "card_title":    {"size": "14px", "line_height": "22px", "weight": "650"},
    "body":          {"size": "14px", "line_height": "22px", "weight": "400"},
    "small_body":    {"size": "13px", "line_height": "20px", "weight": "400"},
    "caption":       {"size": "12px", "line_height": "18px", "weight": "400"},
    "metric_value":  {"size": "28px", "line_height": "34px", "weight": "700"},
}


# ================================================================
# 间距
# ================================================================

SPACING = {
    "2xs":  "2px",
    "xs":   "4px",
    "sm":   "8px",
    "md":   "16px",
    "lg":   "24px",
    "xl":   "32px",
    "2xl":  "48px",
    "3xl":  "64px",
}


# ================================================================
# 圆角
# ================================================================

RADIUS = {
    "xs":   "4px",
    "sm":   "6px",
    "md":   "8px",
    "lg":   "12px",
    "pill": "999px",
}


# ================================================================
# 阴影
# ================================================================

SHADOWS = {
    "card":  "0 1px 2px rgba(23, 33, 43, 0.035)",
    "raised": "0 8px 24px rgba(23, 33, 43, 0.08)",
    "document": "0 18px 44px rgba(23, 33, 43, 0.10)",
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
