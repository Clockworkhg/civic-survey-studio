"""Tab 6: Bivariate analysis.

Displays pairwise relationships: group variables × target variable and
explanatory variables × target variable.
"""

from __future__ import annotations

from typing import Any, Dict

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


def render_tab_bivariate_analysis(
    raw_df: pd.DataFrame,
    schema_df: pd.DataFrame,
    config: Dict[str, Any],
    type_map: Dict[str, str],
    cn_map: Dict[str, str],
    var_dict: Dict[str, Any],
) -> None:
    """Render the bivariate analysis tab.

    Args:
        raw_df: Raw data DataFrame.
        schema_df: Variable schema with inferred types.
        config: Analysis configuration dict (session_state["generic_config"]).
        type_map: {column: inferred_type} lookup.
        cn_map: {column: display_name} lookup.
        var_dict: Variable dictionary map for value-label mappings.
    """
    st.markdown("### 双变量分析")
    st.caption("自动分析分组变量与核心变量、解释变量之间的两两关系。")

    target = config.get("target_variable", "")
    group_vars = config.get("group_variables", [])
    expl_vars = config.get("explanatory_variables", [])

    if not target:
        st.info("请在「分析配置」标签页中指定核心结果变量（Target）。")
    else:
        target_type = type_map.get(target, "")
        target_cn = cn_map.get(target, target)
        # 分组变量 × 目标变量
        if group_vars:
            st.markdown("#### 分组变量 × 核心变量")
            for gv in group_vars:
                if gv not in raw_df.columns or gv == target:
                    continue
                gv_cn = cn_map.get(gv, gv)
                gv_type = type_map.get(gv, "")

                st.markdown(f"**{gv_cn} × {target_cn}**")

                try:
                    if gv_type in ("categorical", "ordinal") and target_type in ("categorical", "ordinal"):
                        result = bivariate_cat_cat(raw_df, gv, target, gv_cn, target_cn, var_dict=var_dict)
                        _render_cross_result(result, 0)

                    elif gv_type in ("categorical", "ordinal") and target_type in ("numeric", "ordinal"):
                        result = bivariate_cat_num(raw_df, gv, target, gv_cn, target_cn)
                        if "error" not in result:
                            st.dataframe(result["group_stats"], use_container_width=True)
                            st.caption(result.get("interpretation", ""))
                        else:
                            st.warning(result["error"])
                    else:
                        st.info(f"「{gv_cn}」（{gv_type}）与「{target_cn}」（{target_type}）的组合暂不支持自动交叉分析。")
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
                    st.markdown(f"**{ev_cn} 与 {target_cn}**")
                    try:
                        result = bivariate_num_num(raw_df, ev, target, ev_cn, target_cn)
                        if "error" not in result:
                            st.markdown(f"Pearson r = {result['pearson_r']}（p = {result['pearson_p']}）| "
                                       f"Spearman ρ = {result['spearman_rho']}（p = {result['spearman_p']}）| n = {result['n']}")
                            st.caption(result.get("interpretation", ""))
                        else:
                            st.warning(result["error"])
                    except Exception as e:
                        st.warning(f"分析失败：{e}")
                    st.markdown("---")
        else:
            st.info("未指定解释变量，跳过相关性分析。")

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
