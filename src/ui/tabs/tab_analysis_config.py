"""Analysis configuration.

Rendered within Tab 2 (分析方案) of the 5-tab main workspace.
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

    # ── 获取当前配置值 ──
    current_target = config.get("target_variable", "")
    current_groups = config.get("group_variables") or []
    current_expls = config.get("explanatory_variables") or []

    # ── 确保当前配置值始终在候选列表中 ──
    # （即使其 inferred_type 不在过滤范围内，或是被 AI blueprint 设置的
    #  非标准类型变量，也不能让控件因为找不到选项而回退到空值）
    _all_known_cols = list(type_map.keys())
    if current_target and current_target in _all_known_cols and current_target not in analyzable_cols:
        analyzable_cols = [current_target] + list(analyzable_cols)

    col_cfg1, col_cfg2 = st.columns(2)
    with col_cfg1:
        target_options = [""] + analyzable_cols
        target_idx = target_options.index(current_target) if current_target in target_options else 0
        widget_target = st.selectbox(
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
        # ── 防止控件回退到空值覆盖已有配置 ──
        if widget_target:
            config["target_variable"] = widget_target
        elif not current_target:
            config["target_variable"] = ""
        # else: 控件回退到了空值但 config 已有合法值 → 保留原值

    with col_cfg2:
        st.caption("")
        st.caption("")

    # ── 分组变量 ──
    group_variable_options = [c for c in analyzable_cols if type_map.get(c) in ("categorical", "ordinal")]
    # 确保当前分组变量在选项中
    for v in current_groups:
        if v not in group_variable_options and v in _all_known_cols:
            group_variable_options.append(v)
    saved_group_vars = current_groups
    valid_group_defaults = [v for v in saved_group_vars if v in group_variable_options]

    widget_groups = st.multiselect(
        "分组变量（Group）",
        options=group_variable_options,
        default=valid_group_defaults,
        key="cfg_groups",
        format_func=lambda c: f"{c}（{cn_map.get(c, '')}）[{type_map.get(c, '')}]",
        help="用于群体差异分析的分类变量，如「性别」、「区域」等。最多建议 5 个。",
    )
    # ── 防止多选控件丢失已有配置 ──
    # 如果 cfg_groups 的 session_state 值与 widget 返回值不一致
    # （例如某些变量不在选项中），合并两者
    cfg_groups_state = st.session_state.get("cfg_groups")
    if cfg_groups_state and isinstance(cfg_groups_state, list):
        merged = list(dict.fromkeys(list(widget_groups) + list(cfg_groups_state)))
        valid_merged = [v for v in merged if v in _all_known_cols]
        config["group_variables"] = valid_merged
    else:
        config["group_variables"] = widget_groups

    # ── 解释变量 ──
    # 根据当前 target 动态排除
    _exclude_target = widget_target or current_target
    explanatory_options = [c for c in analyzable_cols if c != _exclude_target]
    # 确保当前解释变量在选项中
    for v in current_expls:
        if v not in explanatory_options and v in _all_known_cols:
            explanatory_options.append(v)
    saved_expl_vars = current_expls
    valid_expl_defaults = [v for v in saved_expl_vars if v in explanatory_options]

    widget_expls = st.multiselect(
        "解释变量（Predictors）",
        options=explanatory_options,
        default=valid_expl_defaults,
        key="cfg_expl",
        format_func=lambda c: f"{c}（{cn_map.get(c, '')}）[{type_map.get(c, '')}]",
        help="用于相关分析和回归分析的自变量。",
    )
    # ── 防止多选控件丢失已有配置 ──
    cfg_expl_state = st.session_state.get("cfg_expl")
    if cfg_expl_state and isinstance(cfg_expl_state, list):
        merged = list(dict.fromkeys(list(widget_expls) + list(cfg_expl_state)))
        valid_merged = [v for v in merged if v in _all_known_cols]
        config["explanatory_variables"] = valid_merged
    else:
        config["explanatory_variables"] = widget_expls

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
