"""Tab 9: Legacy report generation (non-AI).

Generates HTML and DOCX reports using statistical templates
without calling an external LLM.
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import streamlit as st

from src.report_generator import generate_generic_html_report, generate_generic_docx_report


def render_tab_legacy_report(
    raw_df: pd.DataFrame,
    schema_df: pd.DataFrame,
    config: Dict[str, Any],
    var_dict: Dict[str, Any],
) -> None:
    """Render the legacy (template-based) report generation tab.

    Args:
        raw_df: Raw data DataFrame.
        schema_df: Variable schema DataFrame.
        config: Analysis configuration dict (session_state["generic_config"]).
        var_dict: Variable dictionary map for value-label mappings.
    """
    st.markdown("### 报告生成")
    st.caption("基于分析配置和所有统计结果，自动生成结构化的数据分析报告。")

    target = config.get("target_variable", "")
    if not target:
        st.warning("⚠️ 请在「分析配置」标签页中至少指定核心结果变量，以获得完整的分析报告。")

    report_format_generic = st.radio(
        "报告格式：",
        ["HTML（可在浏览器中查看）", "Word 文档（.docx）", "两种格式都生成"],
        horizontal=True, key="report_fmt_generic",
    )

    if st.button("🔍 生成报告", type="primary", key="gen_report_generic_btn"):
        report_html_g = None
        report_docx_g = None

        with st.spinner("正在运行分析并生成报告，请稍候…"):
            try:
                if "HTML" in report_format_generic or "两种" in report_format_generic:
                    report_html_g = generate_generic_html_report(
                        raw_df, schema_df, config, var_dict=var_dict,
                    )
                if "Word" in report_format_generic or "两种" in report_format_generic:
                    try:
                        report_docx_g = generate_generic_docx_report(
                            raw_df, schema_df, config, var_dict=var_dict,
                        )
                    except ImportError as e:
                        st.warning(f"无法生成 Word 文档：{e}。请执行 pip install python-docx")
                    except Exception as e:
                        st.error(f"Word 文档生成失败：{e}")
            except Exception as e:
                st.error(f"报告生成失败：{e}")

        if report_html_g or report_docx_g:
            st.success("✅ 报告生成完成！")

            safe_title = config.get("report_title", "报告").replace(" ", "_")

            if report_html_g:
                st.markdown("### 📄 HTML 报告预览")
                with st.expander("点击展开 HTML 报告预览", expanded=True):
                    st.components.v1.html(report_html_g, height=600, scrolling=True)
                st.download_button(
                    label="📥 下载报告（HTML）",
                    data=report_html_g,
                    file_name=f"{safe_title}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.html",
                    mime="text/html",
                )

            if report_docx_g:
                st.markdown("### 📝 Word 文档")
                st.download_button(
                    label="📥 下载报告（Word .docx）",
                    data=report_docx_g,
                    file_name=f"{safe_title}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )

            st.markdown("---")
            st.info("报告中的统计结果均基于实际数据计算生成。统计关联不等于因果关系，建议结合实际情况进行人工审阅和补充。")
