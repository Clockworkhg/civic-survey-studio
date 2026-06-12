"""Tab 4: Analysis configuration.

UI for setting the analysis target variable, group variables, explanatory
variables, and report generation options.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd
import streamlit as st


def render_tab_analysis_config(
    schema_df: pd.DataFrame,
    type_map: Dict[str, str],
    cn_map: Dict[str, str],
    config: Dict[str, Any],
    analyzable_cols: List[str] | None = None,
) -> None:
    """Render the analysis configuration tab.

    Modifies ``config`` in-place and saves to ``st.session_state["generic_config"]``
    on button click.

    Args:
        schema_df: Variable schema with inferred types.
        type_map: {column: inferred_type} lookup.
        cn_map: {column: display_name} lookup.
        config: The generic analysis config dict (session_state["generic_config"]).
        analyzable_cols: Pre-computed list of analysable column names.
            Computed from schema_df if not provided.
    """
    st.markdown("### 分析配置")
    st.caption("设置报告主题、核心变量和分析参数。这些配置将影响后续所有分析和报告生成。")

    # 报告主题
    config["report_title"] = st.text_input(
        "报告主题",
        value=config.get("report_title", "问卷数据分析报告"),
        key="cfg_title",
        help="将显示在报告封面和页面标题中。",
    )

    st.markdown("---")

    # 变量角色分配
    # 获取候选变量列表
    if analyzable_cols is None:
        analyzable_cols = schema_df[
            schema_df["inferred_type"].isin(["numeric", "categorical", "ordinal"])
        ]["column"].tolist()

    col_cfg1, col_cfg2 = st.columns(2)
    with col_cfg1:
        target_options = [""] + analyzable_cols
        current_target = config.get("target_variable", "")
        target_idx = target_options.index(current_target) if current_target in target_options else 0
        config["target_variable"] = st.selectbox(
            "核心结果变量（Target）",
            target_options,
            index=target_idx,
            key="cfg_target",
            format_func=lambda c: (
                f"{c}（{cn_map.get(c, '')}）[{type_map.get(c, '')}]"
                if c else "— 请选择 —"
            ),
            help="分析的核心变量，如「总体满意度」、「购买意愿」等。",
        )
    with col_cfg2:
        st.caption("")
        st.caption("")

    # ── 分组变量 ──
    group_variable_options = [c for c in analyzable_cols if type_map.get(c) in ("categorical", "ordinal")]
    saved_group_vars = config.get("group_variables") or []
    valid_group_defaults = [v for v in saved_group_vars if v in group_variable_options]

    config["group_variables"] = st.multiselect(
        "分组变量（Group）",
        options=group_variable_options,
        default=valid_group_defaults,
        key="cfg_groups",
        format_func=lambda c: f"{c}（{cn_map.get(c, '')}）[{type_map.get(c, '')}]",
        help="用于群体差异分析的分类变量，如「性别」、「区域」等。最多建议 5 个。",
    )

    # ── 解释变量 ──
    explanatory_options = [c for c in analyzable_cols if c != config.get("target_variable", "")]
    saved_expl_vars = config.get("explanatory_variables") or []
    valid_expl_defaults = [v for v in saved_expl_vars if v in explanatory_options]

    config["explanatory_variables"] = st.multiselect(
        "解释变量（Predictors）",
        options=explanatory_options,
        default=valid_expl_defaults,
        key="cfg_expl",
        format_func=lambda c: f"{c}（{cn_map.get(c, '')}）[{type_map.get(c, '')}]",
        help="用于相关分析和回归分析的自变量。",
    )

    # 报告格式
    st.markdown("---")
    st.markdown("#### 报告生成选项")
    cfg_gen_html = st.checkbox("生成 HTML 报告", value=True, key="cfg_html")
    cfg_gen_docx = st.checkbox("生成 Word 报告（.docx）", value=True, key="cfg_docx")
    config["gen_html"] = cfg_gen_html
    config["gen_docx"] = cfg_gen_docx

    if st.button("💾 保存配置", type="primary", key="save_cfg_btn"):
        st.session_state["generic_config"] = config
        # v0.1.0: 标记下游失效（通过 session_state 中继）
        st.session_state["_downstream_valid"] = False
        st.session_state["_invalidation_reason"] = "手动配置已更新"
        st.session_state["_config_source"] = "manual"
        st.success("✅ 分析配置已保存！分析结果已标记为失效，请重新执行分析。")

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
