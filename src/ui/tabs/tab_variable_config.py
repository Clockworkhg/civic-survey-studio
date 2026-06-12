"""Tab 3 (part 1): Variable recognition and AI analysis planning.

Handles:
- Variable type inference result display
- Manual variable type editing
- AI data understanding payload generation
- AI analysis blueprint generation and adoption
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

import pandas as pd
import streamlit as st


def render_tab_variable_config(
    sb: Dict[str, Any],
    raw_df: pd.DataFrame,
    schema_df: pd.DataFrame,
    type_map: Dict[str, str],
    quality: Dict[str, Any],
    generic_var_dict_map: Dict[str, Any],
    gen_ctx: Any,
    file_name: str = "",
    selected_sheet: str = "",
) -> None:
    """Render variable recognition results and AI analysis planning.

    Args:
        sb: Sidebar return dict from render_sidebar().
        raw_df: Raw data DataFrame.
        schema_df: Variable schema DataFrame (mutable — type edits modify it).
        type_map: ``{column: inferred_type}`` lookup (mutable).
        quality: Data quality report dict.
        generic_var_dict_map: Value-label mappings for variables.
        gen_ctx: AnalysisContext instance.
    """
    st.markdown("### 变量类型识别结果")
    st.caption("系统已自动推断每个变量的类型和分析建议。您可以在下方手动修改。")

    # 显示推断结果
    display_cols = [
        "column", "display_name", "inferred_type",
        "missing_count", "missing_rate", "unique_count",
        "example_values", "suggested_role",
    ]
    display_names = {
        "column": "变量名", "display_name": "中文名称",
        "inferred_type": "推断类型", "missing_count": "缺失数",
        "missing_rate": "缺失率(%)", "unique_count": "唯一值数",
        "example_values": "示例值", "suggested_role": "建议角色",
    }
    display_schema = schema_df[display_cols].rename(columns=display_names)
    st.dataframe(display_schema, use_container_width=True, hide_index=True)

    # 手动修改变量类型
    st.markdown("---")
    st.markdown("#### 手动修改变量类型")
    st.caption("如需修正自动推断的类型，请在下方选择变量并指定新类型。修改后的类型将用于后续分析。")

    edit_col = st.selectbox(
        "选择要修改的变量：",
        schema_df["column"].tolist(),
        key="edit_var",
        format_func=lambda c: f"{c}（当前：{type_map.get(c, '')}）"
    )
    new_type = st.selectbox(
        "选择新类型：",
        ["numeric", "categorical", "ordinal", "datetime", "text", "id", "high_cardinality"],
        key="new_type",
    )

    if st.button("更新类型", key="update_type_btn"):
        mask = schema_df["column"] == edit_col
        schema_df.loc[mask, "inferred_type"] = new_type
        # 更新查找
        type_map[edit_col] = new_type
        # 重新推断角色
        from src.schema_infer import _suggest_role
        row_idx = schema_df[mask].index[0]
        new_role = _suggest_role(
            edit_col, new_type,
            int(schema_df.loc[row_idx, "unique_count"]),
            len(raw_df.dropna(subset=[edit_col])) / max(len(raw_df), 1),
            len(raw_df),
            schema_df.loc[row_idx, "display_name"],
        )
        schema_df.loc[mask, "suggested_role"] = new_role
        st.success(f"✅ 变量「{edit_col}」的类型已更新为「{new_type}」。")
        st.rerun()

