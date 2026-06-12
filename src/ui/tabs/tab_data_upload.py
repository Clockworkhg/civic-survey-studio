"""Tab 1: Data upload preview.

Displays a preview of the uploaded data file and basic stats.
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import streamlit as st


def render_tab_data_upload(
    sb: Dict[str, Any],
    raw_df: pd.DataFrame,
    file_name: str = "",
    selected_sheet: str = "",
) -> None:
    """Render the data upload preview tab.

    Args:
        sb: Sidebar return dict from render_sidebar().
        raw_df: Loaded raw data DataFrame.
        file_name: Display name of the loaded file (for example data fallback).
        selected_sheet: Selected sheet name (for example data fallback).
    """
    st.markdown("### 数据预览")

    # Use file_name param if provided (example data), otherwise from sb
    display_name = file_name or (sb["generic_file"].name if sb.get("generic_file") else "数据文件")
    st.caption(f"已加载：{display_name}")

    _sheet = selected_sheet or sb.get("selected_sheet", "")
    if _sheet and display_name.endswith((".xlsx", ".xls")):
        st.caption(f"工作表：{_sheet} | 表头行：第 {sb.get('header_row', 0) + 1} 行")

    st.dataframe(raw_df.head(20), use_container_width=True)
    st.caption(f"共 {len(raw_df):,} 条记录，{len(raw_df.columns)} 个变量。上表展示前 20 行。")

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
