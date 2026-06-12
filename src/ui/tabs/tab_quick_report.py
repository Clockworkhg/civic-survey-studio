"""Tab 3 (part 2): One-click AI report generation.

Shown within the variable recognition tab when a valid analysis config
exists and the table understanding payload has been generated.
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import streamlit as st

from src.generic_analysis import run_full_analysis
from src.ui.options import (
    get_structure_options, get_style_options,
    get_length_options, get_html_theme_options,
)
from src.ui.report_generation import (
    build_llm_config_from_ui,
    build_report_config_from_ui,
    run_report_generation_from_ui,
)


def render_tab_quick_report(
    raw_df: pd.DataFrame,
    schema_df: pd.DataFrame,
    quality: Dict[str, Any],
    generic_var_dict_map: Dict[str, Any],
) -> None:
    """Render the one-click AI report generation section.

    Only shown when ``generic_config`` in session_state has at least one
    of target_variable, group_variables, or explanatory_variables set.

    Reads API configuration from session_state (set by Tab 10).

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

    st.markdown("---")
    st.markdown("#### 🚀 一键生成 AI 报告")
    st.caption("基于当前配置，直接运行统计分析并调用 AI 撰写报告。")

    grp_col1, grp_col2 = st.columns(2)
    with grp_col1:
        gen_report_struct = st.selectbox(
            "报告结构", get_structure_options(),
            key="gen_direct_struct",
        )
        gen_report_style = st.selectbox(
            "写作风格", get_style_options(),
            key="gen_direct_style",
        )
    with grp_col2:
        gen_report_len = st.selectbox("报告篇幅", get_length_options(), index=1, key="gen_direct_len")
        gen_report_theme = st.selectbox("HTML 主题", get_html_theme_options(), key="gen_direct_theme")

    # 读取 API 配置
    grk = st.session_state.get("_api_key", "")
    gmk = st.session_state.get("_ai_model", "")
    gpc = st.session_state.get("_provider_config", {})
    gpn = st.session_state.get("_provider_key", "")

    if not grk or not gmk:
        st.warning("⚠️ 请先在「AI 自动报告」标签页配置 API Key 和模型（Tab 4）。")
    else:
        if st.button("🚀 生成 AI 分析报告", type="primary", key="gen_direct_report_btn"):
            with st.spinner("正在运行统计分析并生成报告…"):
                try:
                    gen_analysis = run_full_analysis(
                        raw_df, schema_df, gen_cfg,
                        var_dict=generic_var_dict_map,
                    )
                    gen_llm_cfg = build_llm_config_from_ui(
                        provider_config=gpc,
                        api_key=grk,
                        model=gmk,
                        provider_key=gpn,
                    )
                    gen_rpt_cfg = build_report_config_from_ui(
                        report_structure=gen_report_struct,
                        report_style=gen_report_style,
                        report_length=gen_report_len,
                        html_theme=gen_report_theme,
                    )
                    gen_ai_result = run_report_generation_from_ui(
                        df=raw_df, schema_df=schema_df,
                        config=gen_cfg,
                        analysis_results=gen_analysis,
                        quality=quality,
                        llm_config=gen_llm_cfg,
                        report_config=gen_rpt_cfg,
                    )
                    if gen_ai_result.get("success"):
                        st.success("✅ AI 报告生成完成！")
                        with st.expander("📝 Markdown 报告", expanded=True):
                            st.markdown(gen_ai_result["markdown_report"])
                        if gen_ai_result.get("html_report"):
                            with st.expander("🌐 HTML 预览", expanded=False):
                                st.components.v1.html(gen_ai_result["html_report"], height=800, scrolling=True)
                        gts = pd.Timestamp.now().strftime("%Y%m%d_%H%M")
                        gc1, gc2, gc3 = st.columns(3)
                        gc1.download_button("📥 Markdown", gen_ai_result["markdown_report"],
                                           f"AI报告_{gts}.md", key="gdr_md")
                        if gen_ai_result.get("html_report"):
                            gc2.download_button("📥 HTML", gen_ai_result["html_report"],
                                              f"AI报告_{gts}.html", key="gdr_html")
                        if gen_ai_result.get("docx_report"):
                            gc3.download_button("📥 DOCX", gen_ai_result["docx_report"],
                                              f"AI报告_{gts}.docx", key="gdr_docx")
                    else:
                        st.error(f"❌ {gen_ai_result.get('error', '未知错误')}")
                except Exception as e:
                    st.error(f"❌ 生成失败：{e}")
