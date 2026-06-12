"""Tab 8: Visualization / chart dashboard.

Displays auto-generated dashboard charts and an optional free-form chart explorer.
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import streamlit as st

from src.generic_charts import (
    generate_dashboard_charts,
    exploratory_chart,
)


def render_tab_visualization(
    raw_df: pd.DataFrame,
    schema_df: pd.DataFrame,
    config: Dict[str, Any],
    type_map: Dict[str, str],
    cn_map: Dict[str, str],
) -> None:
    """Render the visualization tab with dashboard charts and chart explorer.

    Args:
        raw_df: Raw data DataFrame.
        schema_df: Variable schema with inferred types.
        config: Analysis configuration dict (session_state["generic_config"]).
        type_map: {column: inferred_type} lookup.
        cn_map: {column: display_name} lookup.
    """
    st.markdown("### 可视化图表")
    st.caption("基于变量类型和分析配置自动生成的交互式图表。")

    # 使用 generate_dashboard_charts 生成图表仪表盘
    dashboard = generate_dashboard_charts(raw_df, schema_df, config)

    if not dashboard:
        st.info("当前配置下无可自动生成的图表。请在「分析配置」标签页设置核心变量。")
    else:
        # 过滤有效图表
        valid_charts = [(k, t, f) for k, t, f in dashboard if f is not None]
        missing_charts = [(k, t, f) for k, t, f in dashboard if f is None]

        if missing_charts:
            with st.expander(f"⚠️ {len(missing_charts)} 个图表未生成", expanded=False):
                for key, title, fig in missing_charts:
                    st.caption(f"· {title}")

        if not valid_charts:
            st.warning("未能生成任何图表。")
        else:
            # 两列布局
            for i in range(0, len(valid_charts), 2):
                cols = st.columns(2)
                for j in range(2):
                    idx = i + j
                    if idx < len(valid_charts):
                        key, title, fig = valid_charts[idx]
                        with cols[j]:
                            st.markdown(f"**{title}**")
                            st.plotly_chart(fig, use_container_width=True)

                if i + 2 < len(valid_charts):
                    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # 探索式图表
    st.markdown("---")
    with st.expander("🔧 自由探索图表", expanded=False):
        st.caption("选择变量和图表类型，自由生成图表。")

        exp_chart_type = st.selectbox(
            "图表类型：",
            ["bar", "pie", "histogram", "scatter", "box"],
            format_func=lambda t: {"bar": "柱状图", "pie": "饼图", "histogram": "直方图", "scatter": "散点图", "box": "箱线图"}.get(t, t),
            key="exp_chart_type",
        )

        all_cols = raw_df.columns.tolist()
        exp_x = st.selectbox(
            "X 轴变量：",
            all_cols,
            key="exp_x",
            format_func=lambda c: f"{c}（{cn_map.get(c, '')}）[{type_map.get(c, '')}]"
        )

        exp_y = None
        if exp_chart_type in ("scatter", "box"):
            exp_y = st.selectbox(
                "Y 轴变量：",
                all_cols,
                key="exp_y",
                format_func=lambda c: f"{c}（{cn_map.get(c, '')}）[{type_map.get(c, '')}]"
            )

        if st.button("生成图表", key="gen_explore_chart"):
            fig = exploratory_chart(
                raw_df, exp_chart_type, exp_x, exp_y or "",
                cn_x=cn_map.get(exp_x, exp_x),
                cn_y=cn_map.get(exp_y, exp_y) if exp_y else "",
            )
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("无法生成图表，请检查变量选择。")

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
