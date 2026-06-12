"""Tab 3-子: Multivariate analysis.

Provides OLS multiple linear regression for numeric/ordinal target variables.

v0.1.0 Phase 2: Default mode reads from precomputed results instead of
running independent regression analysis.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st

from src.generic_analysis import multivariate_regression


def render_tab_multivariate_analysis(
    raw_df: pd.DataFrame,
    config: Dict[str, Any],
    type_map: Dict[str, str],
    cn_map: Dict[str, str],
    precomputed_results: Optional[Dict[str, Any]] = None,
    use_precomputed: bool = True,
) -> None:
    """Render the multivariate analysis tab.

    Args:
        raw_df: Raw data DataFrame.
        config: Analysis configuration dict (session_state["generic_config"]).
        type_map: {column: inferred_type} lookup.
        cn_map: {column: display_name} lookup.
        precomputed_results: Precomputed full-analysis results dict
            (from ``run_full_analysis`` / ``ctx.analysis_results``).
            Expected to contain a ``"multivariate"`` key with the regression result.
        use_precomputed: If True (default) and precomputed_results are available,
            render from the cache. Falls back to live computation only when
            precomputed_results is None or explicitly disabled.
    """
    st.markdown("### 多变量分析")
    st.caption("通过多元线性回归等方法，探究多个解释变量对核心变量的独立贡献。")

    target = config.get("target_variable", "")
    expl_vars = config.get("explanatory_variables", [])
    target_type = type_map.get(target, "")

    if not target:
        st.info("请在「分析方案」标签页中指定核心结果变量。")
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        return

    # ── v0.1.0: 预计算结果路径 ──
    multi_cache: Optional[Dict[str, Any]] = None
    if use_precomputed and precomputed_results is not None:
        multi_cache = precomputed_results.get("multivariate")

    if multi_cache is not None:
        # ── 从预计算结果渲染 ──
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
        else:
            st.info("回归分析结果格式无法识别。")

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        return

    # ── 无预计算结果：实时计算路径（兼容），保留独立按钮 ──
    if target_type not in ("numeric", "ordinal"):
        st.info(f"核心变量「{cn_map.get(target, target)}」为 {target_type} 类型，不适合线性回归分析。")
    elif not expl_vars:
        st.info("请在「分析方案」标签页中指定至少 2 个解释变量。")
    else:
        valid_predictors = [
            v for v in expl_vars
            if v in raw_df.columns and type_map.get(v) in ("numeric", "ordinal")
        ]

        if len(valid_predictors) < 2:
            st.info(f"有效的数值型解释变量不足（当前 {len(valid_predictors)} 个，需要至少 2 个）。")
            if valid_predictors:
                st.caption(f"有效变量：{', '.join(valid_predictors)}")
        else:
            if st.button("🚀 执行回归分析", type="primary", key="run_reg_btn"):
                with st.spinner("正在拟合 OLS 回归模型…"):
                    reg_result = multivariate_regression(
                        raw_df, target, valid_predictors,
                        cn_target=cn_map.get(target, target),
                    )

                if "error" in reg_result:
                    st.error(reg_result["error"])
                else:
                    st.markdown("#### 模型摘要")
                    sm1, sm2, sm3, sm4, sm5 = st.columns(5)
                    sm1.metric("R²", f"{reg_result.get('r_squared', 'N/A')}")
                    sm2.metric("调整 R²", f"{reg_result.get('adj_r_squared', 'N/A')}")
                    sm3.metric("F 统计量", f"{reg_result.get('f_statistic', 'N/A')}")
                    sm4.metric("样本量 n", reg_result.get("n", "N/A"))
                    sm5.metric("条件数", reg_result.get("condition_number", "N/A"))

                    st.markdown("#### 回归系数")
                    st.dataframe(reg_result["coefficients"], use_container_width=True, hide_index=True)
                    st.caption("显著性：*** p<0.001，** p<0.01，* p<0.05，· p<0.1")

                    st.markdown("#### 结果解读")
                    st.markdown(reg_result.get("interpretation", ""))

                    if "warning" in reg_result:
                        st.warning(reg_result["warning"])

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
