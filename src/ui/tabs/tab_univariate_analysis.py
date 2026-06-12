"""Tab 3-子: Univariate analysis.

Displays per-variable descriptive statistics, auto-selecting the appropriate
analysis method based on inferred variable type.

v0.1.0 Phase 2: Default mode reads from precomputed results instead of
re-running individual analysis functions.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st

from src.generic_analysis import univariate_numeric, univariate_categorical, univariate_ordinal
from src.variable_metadata import get_variable_label, get_value_labels, format_variable_name


def render_tab_univariate_analysis(
    raw_df: pd.DataFrame,
    schema_df: pd.DataFrame,
    cn_map: Dict[str, str],
    analyzable_cols: list,
    variable_df_generic: pd.DataFrame | None = None,
    precomputed_results: Optional[Dict[str, Any]] = None,
    use_precomputed: bool = True,
    var_dict_map: Optional[Dict[str, Any]] = None,
) -> None:
    """Render the univariate analysis tab.

    Args:
        raw_df: Raw data DataFrame.
        schema_df: Variable schema with inferred types.
        cn_map: {column: display_name} lookup.
        analyzable_cols: List of analysable column names.
        variable_df_generic: Optional variable description table for label mapping.
        precomputed_results: Precomputed full-analysis results dict
            (from ``run_full_analysis`` / ``ctx.analysis_results``).
            Expected to contain a ``"univariate"`` key mapping col→result.
        use_precomputed: If True (default) and precomputed_results are available,
            render from the cache. Falls back to live computation only when
            precomputed_results is None or explicitly disabled.
        var_dict_map: Optional variable dictionary map for value label lookups
            (v0.1.0 Phase 3).
    """
    st.markdown("### 单变量分析")
    st.caption("对每个变量根据其类型自动执行适配的分析。")

    # ── v0.1.0: 预计算结果路径 ──
    uni_cache: Optional[Dict[str, Any]] = None
    if use_precomputed and precomputed_results is not None:
        uni_cache = precomputed_results.get("univariate")

    if uni_cache is not None:
        # ── 从预计算结果渲染 ──
        if not uni_cache:
            st.info("单变量分析结果为空，请检查数据或重新执行分析。")
            st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
            return

        # 按类型分组显示
        for vtype in ["numeric", "ordinal", "categorical"]:
            vars_of_type = schema_df[schema_df["inferred_type"] == vtype]["column"].tolist()
            vars_with_results = [v for v in vars_of_type if v in uni_cache]
            if not vars_with_results:
                continue

            type_labels = {"numeric": "数值变量", "ordinal": "有序变量", "categorical": "分类变量"}
            with st.expander(
                f"📐 {type_labels.get(vtype, vtype)}（{len(vars_with_results)} 个）",
                expanded=(vtype == "numeric"),
            ):
                for col in vars_with_results:
                    cn = cn_map.get(col, col)
                    st.markdown(f"**{col}**{' — ' + cn if cn else ''}")
                    result = uni_cache[col]

                    try:
                        if vtype == "numeric":
                            if "error" not in result:
                                desc_data = {
                                    k: v for k, v in result.items()
                                    if k in ("样本量", "均值", "标准差", "中位数", "最小值", "最大值", "Q25", "Q75")
                                }
                                st.dataframe(
                                    pd.DataFrame([desc_data]),
                                    use_container_width=True, hide_index=True,
                                )
                            else:
                                st.warning(result["error"])

                        elif vtype in ("categorical", "ordinal"):
                            if "error" not in result:
                                freq = result.get("频数表")
                                if freq is not None and not freq.empty:
                                    st.caption(
                                        f"有效样本: {result.get('有效样本', 'N/A')} | "
                                        f"类别数: {result.get('类别数', 'N/A')} | "
                                        f"众数: {result.get('众数', 'N/A')}"
                                    )
                                    if vtype == "ordinal" and result.get("均值") is not None:
                                        st.caption(f"均值: {result['均值']} | 中位数: {result['中位数']}")
                                    st.dataframe(freq, use_container_width=True, hide_index=True)
                            else:
                                st.warning(result["error"])
                    except Exception as e:
                        st.warning(f"渲染失败：{e}")

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        return

    # ── 无预计算结果：实时计算路径（兼容）──
    if not analyzable_cols:
        st.info("数据中无可分析的变量。")
    else:
        for vtype in ["numeric", "ordinal", "categorical"]:
            vars_of_type = schema_df[schema_df["inferred_type"] == vtype]["column"].tolist()
            if not vars_of_type:
                continue

            type_labels = {"numeric": "数值变量", "ordinal": "有序变量", "categorical": "分类变量"}
            with st.expander(
                f"📐 {type_labels.get(vtype, vtype)}（{len(vars_of_type)} 个）",
                expanded=(vtype == "numeric"),
            ):
                for col in vars_of_type:
                    cn = cn_map.get(col, col)
                    st.markdown(f"**{col}**{' — ' + cn if cn else ''}")

                    try:
                        if vtype == "numeric":
                            result = univariate_numeric(raw_df, col, cn)
                            if "error" not in result:
                                desc_data = {
                                    k: v for k, v in result.items()
                                    if k in ("样本量", "均值", "标准差", "中位数", "最小值", "最大值", "Q25", "Q75")
                                }
                                st.dataframe(
                                    pd.DataFrame([desc_data]),
                                    use_container_width=True, hide_index=True,
                                )
                            else:
                                st.warning(result["error"])

                        elif vtype in ("categorical", "ordinal"):
                            labels: Dict[Any, str] = {}
                            if variable_df_generic is not None:
                                from src.utils import get_value_label_mapping
                                labels = get_value_label_mapping(variable_df_generic, col)

                            fn = univariate_ordinal if vtype == "ordinal" else univariate_categorical
                            result = fn(raw_df, col, cn, labels)
                            if "error" not in result:
                                freq = result.get("频数表")
                                if freq is not None and not freq.empty:
                                    st.caption(
                                        f"有效样本: {result.get('有效样本', 'N/A')} | "
                                        f"类别数: {result.get('类别数', 'N/A')} | "
                                        f"众数: {result.get('众数', 'N/A')}"
                                    )
                                    if vtype == "ordinal" and result.get("均值") is not None:
                                        st.caption(f"均值: {result['均值']} | 中位数: {result['中位数']}")
                                    st.dataframe(freq, use_container_width=True, hide_index=True)
                            else:
                                st.warning(result["error"])
                    except Exception as e:
                        st.warning(f"分析失败：{e}")

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
