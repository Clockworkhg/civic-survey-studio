"""Visualization / chart dashboard.

Rendered within Tab 4 (可视化仪表盘) of the 5-tab main workspace.
Displays auto-generated dashboard charts and an optional free-form chart explorer.

v0.1.0 Phase 2: Default mode reads from precomputed charts
(``ctx.dashboard_charts``) instead of re-calling ``generate_dashboard_charts``.
Shows specific empty-state reasons when charts are unavailable.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from src.generic_charts import (
    generate_dashboard_charts,
    exploratory_chart,
)


_CHART_EMPTY_REASONS: Dict[str, str] = {
    "no_target": "未选择核心变量 — 请在「分析方案」中设置 target_variable。",
    "no_data": "样本量不足 — 当前数据无法生成有意义的图表。",
    "unsupported_type": "变量类型不支持 — 当前变量组合不适合自动生成图表。",
    "no_group_vars": "没有可用分组变量 — 请添加至少一个分类/有序变量到分组变量。",
    "no_expl_vars": "没有可用解释变量 — 请添加至少一个数值/有序变量到解释变量。",
    "not_run": "分析尚未执行 — 请先在「统计分析」页面点击「执行统计分析」。",
    "stale": "当前分析配置已变更，图表需要重新生成。"
                      "请先在「统计分析」页面重新执行分析。",
}


def _diagnose_empty_reason(
    config: Dict[str, Any],
    downstream_valid: bool,
    has_results: bool,
) -> str:
    """Determine the most likely reason why charts are empty."""
    if not config.get("target_variable"):
        return _CHART_EMPTY_REASONS["no_target"]
    if not downstream_valid:
        return _CHART_EMPTY_REASONS["stale"]
    if not has_results:
        return _CHART_EMPTY_REASONS["not_run"]
    # Generic fallback
    return "由于数据或配置原因，当前无法生成图表。请检查变量选择和数据质量。"


def render_tab_visualization(
    raw_df: pd.DataFrame,
    schema_df: pd.DataFrame,
    config: Dict[str, Any],
    type_map: Dict[str, str],
    cn_map: Dict[str, str],
    precomputed_charts: Optional[List[Any]] = None,
    use_precomputed: bool = True,
    downstream_valid: bool = True,
) -> None:
    """Render the visualization tab with dashboard charts and chart explorer.

    Args:
        raw_df: Raw data DataFrame.
        schema_df: Variable schema with inferred types.
        config: Analysis configuration dict (session_state["generic_config"]).
        type_map: {column: inferred_type} lookup.
        cn_map: {column: display_name} lookup.
        precomputed_charts: Precomputed list of (key, title, fig) tuples
            from ``generate_dashboard_charts`` / ``ctx.dashboard_charts``.
        use_precomputed: If True (default) and precomputed_charts is not None,
            render from the cache.
        downstream_valid: Whether the downstream results (and thus charts)
            are still valid for the current config.
    """
    st.markdown("### 可视化图表")
    st.caption("基于变量类型和分析配置自动生成的交互式图表。")

    # ── v0.1.0: 预计算结果路径 ──
    if use_precomputed and precomputed_charts is not None:
        _render_precomputed_charts(precomputed_charts, downstream_valid, config)
        _render_exploratory_section(raw_df, type_map, cn_map)
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        return

    # ── 无预计算结果：实时生成路径（兼容）──
    dashboard = generate_dashboard_charts(raw_df, schema_df, config)

    if not dashboard:
        reason = _diagnose_empty_reason(config, downstream_valid, False)
        st.info(reason)
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

    _render_exploratory_section(raw_df, type_map, cn_map)
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)


def _render_precomputed_charts(
    precomputed_charts: List[Any],
    downstream_valid: bool,
    config: Dict[str, Any],
) -> None:
    """Render charts from the precomputed cache with proper empty/warning states."""
    # ── Warning: config changed, charts may be stale ──
    if not downstream_valid:
        st.warning(_CHART_EMPTY_REASONS["stale"])
        # Still render whatever is available (user may want to see old charts)
        if not precomputed_charts:
            return

    # ── Empty charts ──
    if not precomputed_charts:
        reason = _diagnose_empty_reason(config, downstream_valid, False)
        st.info(reason)
        return

    # ── Filter valid charts ──
    valid_charts: List[tuple] = []
    missing_count = 0
    for item in precomputed_charts:
        if isinstance(item, (tuple, list)) and len(item) >= 3:
            key, title, fig = item[0], item[1], item[2]
            if fig is not None:
                valid_charts.append((key, title, fig))
            else:
                missing_count += 1

    if missing_count:
        st.caption(f"⚠️ {missing_count} 个图表未能生成（可能因数据不足或类型不支持）。")

    if not valid_charts:
        st.warning("未能生成任何图表。请检查变量配置和数据质量。")
        return

    # ── 两列布局渲染 ──
    for i in range(0, len(valid_charts), 2):
        cols = st.columns(2)
        for j in range(2):
            idx = i + j
            if idx < len(valid_charts):
                key, title, fig = valid_charts[idx]
                with cols[j]:
                    st.markdown(f"**{title}**")
                    try:
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.warning(f"图表渲染失败（{title}）：{e}")

        if i + 2 < len(valid_charts):
            st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)


def _render_exploratory_section(
    raw_df: pd.DataFrame,
    type_map: Dict[str, str],
    cn_map: Dict[str, str],
) -> None:
    """Render the free-form chart explorer section."""
    st.markdown("---")
    with st.expander("🔧 自由探索图表", expanded=False):
        st.caption("选择变量和图表类型，自由生成图表。")

        exp_chart_type = st.selectbox(
            "图表类型：",
            ["bar", "pie", "histogram", "scatter", "box"],
            format_func=lambda t: {
                "bar": "柱状图", "pie": "饼图", "histogram": "直方图",
                "scatter": "散点图", "box": "箱线图",
            }.get(t, t),
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
