"""统一样式注入模块。

基于 DESIGN.md 和 theme.py 注入全局 CSS，
弱化 Streamlit 默认风格，建立统一视觉系统。
"""

from __future__ import annotations

import streamlit as st

from src.ui.theme import (
    COLORS,
    FONT_FAMILY,
    RADIUS,
    SHADOWS,
    SPACING,
    TYPOGRAPHY,
)

# ================================================================
# 全局 CSS
# ================================================================

APP_CSS = f"""
<style>
/* ============================================================
   全局重置
   ============================================================ */

/* 全局字体 */
html, body, [class*="css"] {{
    font-family: {FONT_FAMILY} !important;
    color: {COLORS.text};
}}

/* 页面背景 */
section[data-testid="stAppViewContainer"] > .main {{
    background: {COLORS.bg};
}}

/* ============================================================
   主内容区宽度与间距
   ============================================================ */

/* 主内容容器 — 约束最大宽度，减少空白 */
.block-container {{
    max-width: 1200px !important;
    padding-top: 1.5rem !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
}}

/* Streamlit 全局 padding 缩减 */
section[data-testid="stAppViewContainer"] .main .block-container {{
    padding-top: 1rem !important;
    max-width: 1200px !important;
}}

/* ============================================================
   标题与排版
   ============================================================ */

h1, h2, h3, h4 {{
    font-family: {FONT_FAMILY} !important;
}}

/* Streamlit 默认标题弱化 */
[data-testid="stHeader"] {{
    background: transparent;
}}

/* ============================================================
   Sidebar
   ============================================================ */

section[data-testid="stSidebar"] {{
    background: {COLORS.surface};
    border-right: 1px solid {COLORS.border};
}}

section[data-testid="stSidebar"] .block-container {{
    padding-top: 0.8rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
}}

section[data-testid="stSidebar"] .stMarkdown {{
    font-size: 13px;
}}

section[data-testid="stSidebar"] h2 {{
    font-size: 13px !important;
    font-weight: 600 !important;
    color: {COLORS.text_muted} !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-top: 16px;
    margin-bottom: 4px;
    padding: 0;
}}

section[data-testid="stSidebar"] h3 {{
    font-size: 12px !important;
    font-weight: 600 !important;
    color: {COLORS.text_muted} !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-top: 14px;
    margin-bottom: 2px;
}}

/* Sidebar divider */
section[data-testid="stSidebar"] hr {{
    border-color: {COLORS.divider};
    margin: 8px 0;
}}

/* Sidebar file uploader — compact */
section[data-testid="stSidebar"] [data-testid="stFileUploadDropzone"] {{
    padding: 8px !important;
}}

/* Sidebar caption — smaller */
section[data-testid="stSidebar"] .st-caption {{
    font-size: 11px !important;
    color: {COLORS.text_subtle} !important;
}}

/* Sidebar buttons — full width, uniform */
section[data-testid="stSidebar"] .stButton > button {{
    width: 100% !important;
    font-size: 13px !important;
}}

/* Sidebar expander — no border, compact */
section[data-testid="stSidebar"] .streamlit-expanderHeader {{
    border: none !important;
    background: transparent !important;
    padding: 6px 0 !important;
    font-size: 12px !important;
}}

/* Sidebar selectbox / input — compact */
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stTextInput label,
section[data-testid="stSidebar"] .stNumberInput label {{
    font-size: 12px !important;
    color: {COLORS.text} !important;
}}

/* ============================================================
   Tab 导航栏
   ============================================================ */

/* Tab 容器 — 分段导航风格 */
.stTabs [data-baseweb="tab-list"] {{
    gap: 0;
    background: {COLORS.surface};
    border: 1px solid {COLORS.border};
    border-radius: {RADIUS["md"]};
    padding: 3px;
    margin-bottom: {SPACING["lg"]};
}}

/* 单个 Tab */
.stTabs [data-baseweb="tab"] {{
    height: 38px;
    border-radius: {RADIUS["sm"]} !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 0 18px !important;
    color: {COLORS.text_muted} !important;
    background: transparent !important;
    border: none !important;
    transition: all 0.15s ease;
}}

/* Tab 悬停 */
.stTabs [data-baseweb="tab"]:hover {{
    color: {COLORS.text} !important;
    background: {COLORS.surface_subtle} !important;
}}

/* Tab 激活态 */
.stTabs [aria-selected="true"] {{
    color: {COLORS.primary} !important;
    background: {COLORS.primary_soft} !important;
    font-weight: 600 !important;
}}

/* ============================================================
   按钮
   ============================================================ */

/* 主按钮 */
.stButton > button[kind="primary"] {{
    background: {COLORS.primary} !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: {RADIUS["sm"]} !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    padding: 8px 20px !important;
    min-height: 38px;
    transition: background 0.15s ease;
}}

.stButton > button[kind="primary"]:hover {{
    background: {COLORS.primary_hover} !important;
}}

/* 次按钮 */
.stButton > button[kind="secondary"] {{
    background: {COLORS.surface} !important;
    color: {COLORS.text} !important;
    border: 1px solid {COLORS.border_strong} !important;
    border-radius: {RADIUS["sm"]} !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 6px 16px !important;
    min-height: 36px;
}}

.stButton > button[kind="secondary"]:hover {{
    background: {COLORS.surface_subtle} !important;
}}

/* ============================================================
   卡片容器
   ============================================================ */

/* 统一卡片样式 — 用于自定义 HTML wrapper */
.card {{
    background: {COLORS.surface};
    border: 1px solid {COLORS.border};
    border-radius: {RADIUS["md"]};
    padding: 18px;
    box-shadow: {SHADOWS["card"]};
    margin-bottom: 16px;
}}

.card-ai {{
    background: {COLORS.accent_soft};
    border: 1px solid {COLORS.accent_border};
    border-radius: {RADIUS["md"]};
    padding: 18px;
    box-shadow: {SHADOWS["card"]};
    margin-bottom: 16px;
}}

.card-error {{
    background: {COLORS.error_soft};
    border: 1px solid {COLORS.error_light};
    border-radius: {RADIUS["md"]};
    padding: 18px;
    box-shadow: {SHADOWS["card"]};
    margin-bottom: 16px;
}}

/* ============================================================
   指标卡片（Streamlit metric 覆盖）
   ============================================================ */

[data-testid="metric-container"] {{
    background: {COLORS.surface} !important;
    border: 1px solid {COLORS.border} !important;
    border-radius: {RADIUS["md"]} !important;
    padding: 14px 18px !important;
    box-shadow: {SHADOWS["card"]} !important;
}}

[data-testid="metric-container"] label {{
    color: {COLORS.text_muted} !important;
    font-size: 11px !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}}

[data-testid="metric-container"] div[data-testid="stMetricValue"] {{
    color: {COLORS.primary} !important;
    font-size: 24px !important;
    font-weight: 700 !important;
}}

/* ============================================================
   Expander
   ============================================================ */

.streamlit-expanderHeader {{
    font-size: 13px !important;
    font-weight: 500 !important;
    color: {COLORS.text} !important;
    background: {COLORS.surface_subtle} !important;
    border-radius: {RADIUS["sm"]} !important;
    border: 1px solid {COLORS.border} !important;
}}

.streamlit-expanderHeader:hover {{
    background: {COLORS.surface_muted} !important;
}}

/* ============================================================
   表格
   ============================================================ */

[data-testid="stTable"] {{
    font-size: 13px !important;
}}

[data-testid="stTable"] th {{
    background: {COLORS.surface_subtle} !important;
    color: {COLORS.text_muted} !important;
    font-weight: 600 !important;
    font-size: 11px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
    padding: 8px 12px !important;
    border-color: {COLORS.border} !important;
}}

[data-testid="stTable"] td {{
    padding: 6px 12px !important;
    border-color: {COLORS.divider} !important;
    font-size: 13px !important;
}}

/* ============================================================
   输入控件
   ============================================================ */

/* 文本输入 */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {{
    border: 1px solid {COLORS.border} !important;
    border-radius: {RADIUS["sm"]} !important;
    font-size: 14px !important;
}}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {{
    border-color: {COLORS.primary} !important;
    box-shadow: 0 0 0 2px {COLORS.primary_soft} !important;
}}

/* Select / Multiselect */
.stSelectbox > div > div,
.stMultiSelect > div > div {{
    border: 1px solid {COLORS.border} !important;
    border-radius: {RADIUS["sm"]} !important;
}}

/* 上传区域 */
[data-testid="stFileUploadDropzone"] {{
    background: {COLORS.surface} !important;
    border: 1px dashed {COLORS.border_strong} !important;
    border-radius: {RADIUS["md"]} !important;
}}

[data-testid="stFileUploadDropzone"]:hover {{
    border-color: {COLORS.primary} !important;
    background: {COLORS.primary_soft} !important;
}}

/* ============================================================
   Callout 弱化（info/warning/error/success）
   ============================================================ */

/* 默认 info — 改为温和灰蓝 */
div[data-testid="stAlert"][kind="info"] {{
    background: {COLORS.surface_subtle} !important;
    border-left: 3px solid {COLORS.text_muted} !important;
    color: {COLORS.text} !important;
    border-radius: {RADIUS["sm"]} !important;
    font-size: 13px !important;
}}

/* 默认 warning — 改为琥珀左侧条 */
div[data-testid="stAlert"][kind="warning"] {{
    background: {COLORS.warning_soft} !important;
    border-left: 3px solid {COLORS.warning} !important;
    color: {COLORS.text} !important;
    border-radius: {RADIUS["sm"]} !important;
    font-size: 13px !important;
}}

/* 默认 error — 改为红色左侧条 */
div[data-testid="stAlert"][kind="error"] {{
    background: {COLORS.error_soft} !important;
    border-left: 3px solid {COLORS.error} !important;
    color: {COLORS.error_text} !important;
    border-radius: {RADIUS["sm"]} !important;
    font-size: 13px !important;
}}

/* 默认 success — 改为绿色左侧条 */
div[data-testid="stAlert"][kind="success"] {{
    background: {COLORS.success_soft} !important;
    border-left: 3px solid {COLORS.success} !important;
    color: {COLORS.text} !important;
    border-radius: {RADIUS["sm"]} !important;
    font-size: 13px !important;
}}

/* ============================================================
   分区分隔线
   ============================================================ */

.section-divider {{
    margin: 20px 0;
    border-top: 1px solid {COLORS.divider};
}}

/* ============================================================
   Download Button
   ============================================================ */

.stDownloadButton > button {{
    background: {COLORS.surface} !important;
    color: {COLORS.text} !important;
    border: 1px solid {COLORS.border_strong} !important;
    border-radius: {RADIUS["sm"]} !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 6px 14px !important;
    min-height: 34px;
}}

.stDownloadButton > button:hover {{
    background: {COLORS.surface_subtle} !important;
    border-color: {COLORS.primary} !important;
    color: {COLORS.primary} !important;
}}

/* ============================================================
   Code Block
   ============================================================ */

.stCodeBlock {{
    border-radius: {RADIUS["sm"]} !important;
    border: 1px solid {COLORS.border} !important;
    background: {COLORS.surface_subtle} !important;
    font-size: 12px !important;
}}

/* ============================================================
   Progress / Spinner
   ============================================================ */

.stSpinner > div {{
    border-color: {COLORS.primary} !important;
}}

/* ============================================================
   Footer
   ============================================================ */

footer {{
    visibility: hidden;
}}

/* ============================================================
   Helper: Hide Streamlit default menu
   ============================================================ */

#MainMenu {{ visibility: hidden; }}

</style>
"""


# ================================================================
# 公开接口
# ================================================================


def load_app_css() -> str:
    """返回完整应用 CSS。"""
    return APP_CSS


def inject_app_css() -> None:
    """向 Streamlit 页面注入全局 CSS。"""
    st.markdown(APP_CSS, unsafe_allow_html=True)
