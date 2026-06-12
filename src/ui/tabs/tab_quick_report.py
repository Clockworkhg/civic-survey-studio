"""Current analysis configuration summary.

Shown within the variable recognition section when a valid analysis config
exists. Displays core variable, group variable, and explanatory variable
counts. AI report generation is in Tab 5 (报告工作台).
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import streamlit as st


def render_tab_quick_report(
    raw_df: pd.DataFrame,
    schema_df: pd.DataFrame,
    quality: Dict[str, Any],
    generic_var_dict_map: Dict[str, Any],
) -> None:
    """Render the current analysis configuration summary.

    Only shown when ``generic_config`` in session_state has at least one
    of target_variable, group_variables, or explanatory_variables set.

    Note: AI report generation is in Tab 5 (报告工作台).
    Please switch to that tab for full-featured report generation with
    literature review, background research, and privacy controls.

    Args:
        raw_df: Raw data DataFrame.
        schema_df: Variable schema DataFrame.
        quality: Data quality report dict.
        generic_var_dict_map: Value-label mappings for variables.
    """
    gen_cfg = st.session_state.get("generic_config", {})
    has_gen_config = bool(
        gen_cfg.get("target_variable")
        or gen_cfg.get("group_variables")
        or gen_cfg.get("explanatory_variables")
    )
    if not has_gen_config:
        return

    st.markdown("---")
    st.markdown("#### 📋 当前分析配置")
    gcfg_col1, gcfg_col2, gcfg_col3 = st.columns(3)
    with gcfg_col1:
        st.metric("核心变量", gen_cfg.get("target_variable", "未设置") or "未设置")
    with gcfg_col2:
        st.metric("分组变量", str(len(gen_cfg.get("group_variables", []) or [])) + " 个")
    with gcfg_col3:
        st.metric("解释变量", str(len(gen_cfg.get("explanatory_variables", []) or [])) + " 个")
    if gen_cfg.get("report_title"):
        st.caption(f"📝 报告标题：{gen_cfg['report_title']}")

    st.info(
        "如需生成 AI 分析报告（含文献综述、背景研究、隐私控制等完整功能），"
        "请切换到 **报告工作台** 标签页。"
        "API 配置请在左侧边栏 **AI 设置** 中完成。"
    )
