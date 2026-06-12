"""Tab 2: Data quality overview.

Displays data quality metrics, data type distribution, and missing value
details for the uploaded dataset.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st


def render_tab_data_overview(
    raw_df: pd.DataFrame,
    schema_df: pd.DataFrame,
    quality: dict,
) -> None:
    """Render the data quality overview tab.

    Args:
        raw_df: Raw data DataFrame.
        schema_df: Variable schema with inferred types.
        quality: Data quality metrics dict from ``get_data_quality_report``.
    """
    st.markdown("### 数据质量报告")

    qc1, qc2, qc3 = st.columns(3)
    with qc1:
        st.metric("样本量", f"{quality['样本量']:,}")
        st.metric("变量数", quality["变量数"])
    with qc2:
        st.metric("缺失值总数", quality["缺失值总数"])
        st.metric("缺失率", f"{quality['缺失率']}%")
    with qc3:
        st.metric("重复行数", quality["重复行数"])
        st.metric("重复率", f"{quality['重复率']}%")

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # 数据类型分布
    st.markdown("#### 数据类型分布")
    c1, c2 = st.columns(2)
    with c1:
        dtype_counts = raw_df.dtypes.astype(str).value_counts()
        st.dataframe(
            pd.DataFrame({"数据类型": dtype_counts.index, "变量数": dtype_counts.values}),
            use_container_width=True, hide_index=True,
        )
    with c2:
        type_counts = schema_df["inferred_type"].value_counts()
        st.dataframe(
            pd.DataFrame({"推断类型": type_counts.index, "变量数": type_counts.values}),
            use_container_width=True, hide_index=True,
        )

    # 缺失值详情
    st.markdown("#### 缺失值情况")
    missing = raw_df.isnull().sum()
    total = len(raw_df)
    missing_detail = pd.DataFrame({
        "变量名": missing.index,
        "缺失数": missing.values,
        "缺失率(%)": (missing.values / total * 100).round(2),
    })
    missing_detail = missing_detail[missing_detail["缺失数"] > 0]
    if len(missing_detail) > 0:
        st.dataframe(missing_detail, use_container_width=True, hide_index=True)
    else:
        st.success("数据完整，所有变量均无缺失值。")

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
