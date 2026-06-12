"""Tab 5: Univariate analysis.

Displays per-variable descriptive statistics, auto-selecting the appropriate
analysis method based on inferred variable type.
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import streamlit as st

from src.generic_analysis import univariate_numeric, univariate_categorical, univariate_ordinal


def render_tab_univariate_analysis(
    raw_df: pd.DataFrame,
    schema_df: pd.DataFrame,
    cn_map: Dict[str, str],
    analyzable_cols: list,
    variable_df_generic: pd.DataFrame | None = None,
) -> None:
    """Render the univariate analysis tab.

    Args:
        raw_df: Raw data DataFrame.
        schema_df: Variable schema with inferred types.
        cn_map: {column: display_name} lookup.
        analyzable_cols: List of analysable column names.
        variable_df_generic: Optional variable description table for label mapping.
    """
    st.markdown("### 单变量分析")
    st.caption("对每个变量根据其类型自动执行适配的分析。")

    if not analyzable_cols:
        st.info("数据中无可分析的变量。")
    else:
        # 按类型分组显示
        for vtype in ["numeric", "ordinal", "categorical"]:
            vars_of_type = schema_df[schema_df["inferred_type"] == vtype]["column"].tolist()
            if not vars_of_type:
                continue

            type_labels = {"numeric": "数值变量", "ordinal": "有序变量", "categorical": "分类变量"}
            with st.expander(f"📐 {type_labels.get(vtype, vtype)}（{len(vars_of_type)} 个）", expanded=(vtype == "numeric")):
                for col in vars_of_type:
                    cn = cn_map.get(col, col)
                    st.markdown(f"**{col}**{' — ' + cn if cn else ''}")

                    try:
                        if vtype == "numeric":
                            result = univariate_numeric(raw_df, col, cn)
                            if "error" not in result:
                                desc_data = {k: v for k, v in result.items()
                                            if k in ("样本量", "均值", "标准差", "中位数", "最小值", "最大值", "Q25", "Q75")}
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
                                    st.caption(f"有效样本: {result.get('有效样本', 'N/A')} | 类别数: {result.get('类别数', 'N/A')} | 众数: {result.get('众数', 'N/A')}")
                                    if vtype == "ordinal" and result.get("均值") is not None:
                                        st.caption(f"均值: {result['均值']} | 中位数: {result['中位数']}")
                                    st.dataframe(freq, use_container_width=True, hide_index=True)
                            else:
                                st.warning(result["error"])
                    except Exception as e:
                        st.warning(f"分析失败：{e}")

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
