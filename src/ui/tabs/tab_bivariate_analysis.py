"""Tab 3-子: Bivariate analysis.

Displays pairwise relationships: group variables × target variable and
explanatory variables × target variable.

v0.1.0 Phase 2: Default mode reads from precomputed results instead of
re-running individual analysis functions.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st

from src.generic_analysis import bivariate_cat_cat, bivariate_cat_num, bivariate_num_num


def _render_cross_result(result: dict, index: int) -> None:
    """Render a single cross-tabulation result with chi-square test details."""
    row_cn = result.get("row_var_cn", result.get("row_col", ""))
    col_cn = result.get("col_var_cn", result.get("col_col", ""))
    st.markdown(f"#### {row_cn} × {col_cn}")

    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("卡方值 χ²", result.get("chi2"))
    mc2.metric("p 值", result.get("p_value"))
    mc3.metric("自由度 df", result.get("dof"))
    mc4.metric("有效样本 n", result.get("n"))

    tab_ct, tab_pct = st.columns(2)
    with tab_ct:
        st.markdown("**频次交叉表**")
        st.dataframe(result["crosstab"], use_container_width=True)
    with tab_pct:
        st.markdown("**行百分比表（%）**")
        st.dataframe(result["pct_table"], use_container_width=True)

    st.markdown("**统计检验小结：**")
    if result.get("significant"):
        st.success(result.get("interpretation", ""))
    else:
        st.info(result.get("interpretation", ""))


def _render_num_result(result: dict) -> None:
    """Render a bivariate numeric comparison result."""
    if "error" in result:
        st.warning(result["error"])
        return
    st.dataframe(result["group_stats"], use_container_width=True)
    if result.get("interpretation"):
        st.caption(result["interpretation"])


def _render_corr_result(result: dict) -> None:
    """Render a numeric-numeric correlation result."""
    if "error" in result:
        st.warning(result["error"])
        return
    st.markdown(
        f"Pearson r = {result['pearson_r']}（p = {result['pearson_p']}）| "
        f"Spearman ρ = {result['spearman_rho']}（p = {result['spearman_p']}）| "
        f"n = {result['n']}"
    )
    if result.get("interpretation"):
        st.caption(result["interpretation"])


def render_tab_bivariate_analysis(
    raw_df: pd.DataFrame,
    schema_df: pd.DataFrame,
    config: Dict[str, Any],
    type_map: Dict[str, str],
    cn_map: Dict[str, str],
    var_dict: Dict[str, Any],
    precomputed_results: Optional[Dict[str, Any]] = None,
    use_precomputed: bool = True,
) -> None:
    """Render the bivariate analysis tab.

    Args:
        raw_df: Raw data DataFrame.
        schema_df: Variable schema with inferred types.
        config: Analysis configuration dict (session_state["generic_config"]).
        type_map: {column: inferred_type} lookup.
        cn_map: {column: display_name} lookup.
        var_dict: Variable dictionary map for value-label mappings.
        precomputed_results: Precomputed full-analysis results dict
            (from ``run_full_analysis`` / ``ctx.analysis_results``).
            Expected to contain ``"bivariate_group"`` and ``"bivariate_corr"`` keys.
        use_precomputed: If True (default) and precomputed_results are available,
            render from the cache.
    """
    st.markdown("### 双变量分析")
    st.caption("自动分析分组变量与核心变量、解释变量之间的两两关系。")

    target = config.get("target_variable", "")

    if not target:
        st.info("请在「分析方案」标签页中指定核心结果变量（Target）。")
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        return

    # ── v0.1.0: 预计算结果路径 ──
    group_cache: Optional[Dict[str, Any]] = None
    corr_cache: Optional[Dict[str, Any]] = None
    multi_cache: Optional[Dict[str, Any]] = None

    if use_precomputed and precomputed_results is not None:
        group_cache = precomputed_results.get("bivariate_group")
        corr_cache = precomputed_results.get("bivariate_corr")
        # Precomputed multivariate result (OLS regression)
        multi_cache = precomputed_results.get("multivariate")

    has_precomputed = bool(group_cache or corr_cache)

    if has_precomputed:
        # ── 从预计算结果渲染 ──
        # 分组变量 × 核心变量
        if group_cache:
            st.markdown("#### 分组变量 × 核心变量")
            for key, result in group_cache.items():
                try:
                    if "crosstab" in result:
                        _render_cross_result(result, 0)
                    elif "group_stats" in result:
                        _render_num_result(result)
                    else:
                        st.caption(f"{key}: 结果格式未知")
                except Exception as e:
                    st.warning(f"渲染失败（{key}）：{e}")
                st.markdown("---")
        else:
            st.info("未指定分组变量，跳过群体差异分析。")

        # 解释变量 × 核心变量
        if corr_cache:
            st.markdown("#### 解释变量 × 核心变量")
            for key, result in corr_cache.items():
                try:
                    st.markdown(f"**{key.replace('__', ' 与 ')}**")
                    _render_corr_result(result)
                except Exception as e:
                    st.warning(f"渲染失败（{key}）：{e}")
                st.markdown("---")
        else:
            st.info("未指定解释变量，跳过相关性分析。")

        # 多元回归结果
        if multi_cache is not None:
            st.markdown("---")
            st.markdown("#### 多元回归分析")
            if isinstance(multi_cache, dict) and "error" not in multi_cache:
                sm1, sm2, sm3, sm4, sm5 = st.columns(5)
                sm1.metric("R²", f"{multi_cache.get('r_squared', 'N/A')}")
                sm2.metric("调整 R²", f"{multi_cache.get('adj_r_squared', 'N/A')}")
                sm3.metric("F 统计量", f"{multi_cache.get('f_statistic', 'N/A')}")
                sm4.metric("样本量 n", multi_cache.get("n", "N/A"))
                sm5.metric("条件数", multi_cache.get("condition_number", "N/A"))

                st.markdown("#### 回归系数")
                if "coefficients" in multi_cache:
                    st.dataframe(multi_cache["coefficients"], use_container_width=True, hide_index=True)
                    st.caption("显著性：*** p<0.001，** p<0.01，* p<0.05，· p<0.1")

                st.markdown("#### 结果解读")
                if multi_cache.get("interpretation"):
                    st.markdown(multi_cache["interpretation"])
                if "warning" in multi_cache:
                    st.warning(multi_cache["warning"])
            elif isinstance(multi_cache, dict) and "error" in multi_cache:
                st.warning(multi_cache["error"])

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        return

    # ── 无预计算结果：实时计算路径（兼容）──
    target_type = type_map.get(target, "")
    group_vars = config.get("group_variables", [])
    expl_vars = config.get("explanatory_variables", [])

    # 分组变量 × 目标变量
    if group_vars:
        st.markdown("#### 分组变量 × 核心变量")
        for gv in group_vars:
            if gv not in raw_df.columns or gv == target:
                continue
            gv_cn = cn_map.get(gv, gv)
            gv_type = type_map.get(gv, "")

            st.markdown(f"**{gv_cn} × {cn_map.get(target, target)}**")

            try:
                if gv_type in ("categorical", "ordinal") and target_type in ("categorical", "ordinal"):
                    result = bivariate_cat_cat(raw_df, gv, target, gv_cn, cn_map.get(target, target), var_dict=var_dict)
                    _render_cross_result(result, 0)

                elif gv_type in ("categorical", "ordinal") and target_type in ("numeric", "ordinal"):
                    result = bivariate_cat_num(raw_df, gv, target, gv_cn, cn_map.get(target, target))
                    _render_num_result(result)
                else:
                    st.info(f"「{gv_cn}」（{gv_type}）与「{cn_map.get(target, target)}」（{target_type}）的组合暂不支持自动交叉分析。")
            except Exception as e:
                st.warning(f"分析失败：{e}")

            st.markdown("---")
    else:
        st.info("未指定分组变量，跳过群体差异分析。")

    # 解释变量 × 目标变量
    if expl_vars:
        st.markdown("#### 解释变量 × 核心变量")
        num_expl = [v for v in expl_vars if type_map.get(v) in ("numeric", "ordinal") and v in raw_df.columns]
        if target_type in ("numeric", "ordinal") and num_expl:
            for ev in num_expl:
                if ev == target:
                    continue
                ev_cn = cn_map.get(ev, ev)
                st.markdown(f"**{ev_cn} 与 {cn_map.get(target, target)}**")
                try:
                    result = bivariate_num_num(raw_df, ev, target, ev_cn, cn_map.get(target, target))
                    _render_corr_result(result)
                except Exception as e:
                    st.warning(f"分析失败：{e}")
                st.markdown("---")
    else:
        st.info("未指定解释变量，跳过相关性分析。")

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
