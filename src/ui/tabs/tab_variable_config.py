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

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # ── AI 数据理解 / 分析规划 ──
    st.markdown("### 🧠 AI 数据理解 / 分析规划")
    st.caption("让 AI 理解当前数据结构，推荐最合适的分析方案。")

    user_goal = st.text_input(
        "分析目标（可选）",
        placeholder="例如：我想分析哪些因素影响满意度 / 我想生成学术论文式报告",
        key="gen_ai_goal",
    )

    tu_col1, tu_col2 = st.columns([1, 3])
    with tu_col1:
        gen_tu_btn = st.button("📦 生成数据理解 Payload", key="gen_tu_btn")
    with tu_col2:
        tu_placeholder = st.empty()

    if gen_tu_btn:
        with st.spinner("正在构建数据理解 payload…"):
            try:
                from src.table_understanding_packager import (
                    build_table_understanding_payload,
                    to_json_payload as tu_to_json,
                )
                st.session_state["gen_tu_payload"] = build_table_understanding_payload(
                    df=raw_df,
                    schema_df=schema_df,
                    quality=quality,
                    variable_dict_map=generic_var_dict_map,
                    user_goal=user_goal,
                    preset_profile=None,
                    selected_sheet=selected_sheet or sb.get("selected_sheet", "") or "",
                    file_type="csv" if (file_name or (sb["generic_file"].name if sb.get("generic_file") else "")).endswith(".csv") else "xlsx",
                    dataset_name=file_name or (sb["generic_file"].name if sb.get("generic_file") else ""),
                )
                tu_placeholder.success(
                    f"✅ 数据理解 Payload 生成完成 "
                    f"（{len(tu_to_json(st.session_state['gen_tu_payload']).encode('utf-8')) / 1024:.1f} KB）"
                )
            except Exception as e:
                tu_placeholder.error(f"❌ 生成失败：{e}")

    gen_tu_payload = st.session_state.get("gen_tu_payload")
    if gen_tu_payload:
        with st.expander("📋 数据理解 Payload 摘要", expanded=False):
            st.json(gen_ctx.to_dict())

        st.markdown("---")
        st.markdown("#### AI 分析方案推荐")

        # 使用 Tab 4 (AI 自动报告) 的已解析配置
        gen_resolved_key = st.session_state.get("_api_key", "")
        gen_model = st.session_state.get("_ai_model", "")
        gen_p_config = st.session_state.get("_provider_config", {})
        gen_p_key = st.session_state.get("_provider_key", "")

        if not gen_resolved_key or not gen_model:
            st.info("💡 请先在「AI 自动报告」标签页中配置 API Key 和模型，然后回到此页面生成分析方案。")
        elif not gen_p_config:
            st.warning("⚠️ 未找到厂商配置，请先在「AI 自动报告」标签页中选择厂商。")
        else:
            if st.button("🧠 生成 AI 分析方案", key="gen_blueprint_btn"):
                with st.spinner("AI 正在分析数据结构并推荐方案…"):
                    from src.ai_table_planner import generate_analysis_blueprint
                    bp_result = generate_analysis_blueprint(
                        table_understanding_payload=st.session_state["gen_tu_payload"],
                        provider_config=gen_p_config,
                        api_key=gen_resolved_key,
                        model=gen_model,
                        provider_key=gen_p_key,
                    )
                if bp_result.get("success"):
                    st.session_state["gen_blueprint"] = bp_result["blueprint"]
                    st.success("✅ AI 分析方案生成完成！")
                else:
                    st.error(f"❌ 生成失败：{bp_result.get('error', '未知错误')}")

        # 展示 AI 推荐方案
        gen_blueprint = st.session_state.get("gen_blueprint")
        if gen_blueprint:
            bp = gen_blueprint
            st.markdown("---")
            st.markdown("### 📊 AI 推荐分析方案")

            with st.expander("📖 数据集理解", expanded=True):
                ds = bp.get("dataset_understanding", {})
                st.markdown(f"**类型**: {ds.get('dataset_type', '')}")
                st.markdown(f"**研究对象**: {ds.get('possible_research_subject', '')}")
                st.markdown(f"**主题**: {ds.get('main_analysis_theme', '')}")
                st.markdown(ds.get("summary", ""))

            titles = bp.get("recommended_report_titles", [])
            if titles:
                with st.expander(f"📝 推荐报告标题（{len(titles)} 个）", expanded=False):
                    for t in titles:
                        st.caption(f"· {t}")

            col_bp1, col_bp2, col_bp3 = st.columns(3)
            with col_bp1:
                with st.expander("🎯 核心变量候选", expanded=True):
                    for c in bp.get("target_variable_candidates", []):
                        icon = {"high": "⭐", "medium": "●", "low": "○"}.get(c.get("priority", ""), "")
                        st.caption(f"{icon} **{c.get('display_name', '')}** (`{c.get('variable', '')}`)")
                        st.caption(f"  _{c.get('reason', '')}_")
            with col_bp2:
                with st.expander("🔀 分组变量候选", expanded=True):
                    for c in bp.get("group_variable_candidates", []):
                        icon = {"high": "⭐", "medium": "●", "low": "○"}.get(c.get("priority", ""), "")
                        st.caption(f"{icon} **{c.get('display_name', '')}** (`{c.get('variable', '')}`)")
            with col_bp3:
                with st.expander("📈 解释变量候选", expanded=True):
                    for c in bp.get("explanatory_variable_candidates", []):
                        icon = {"high": "⭐", "medium": "●", "low": "○"}.get(c.get("priority", ""), "")
                        st.caption(f"{icon} **{c.get('display_name', '')}** (`{c.get('variable', '')}`)")

            # Derived variables
            derived = bp.get("derived_variable_suggestions", [])
            if derived:
                with st.expander(f"🔧 推荐派生指标（{len(derived)} 个）", expanded=False):
                    for d in derived:
                        st.caption(f"· **{d.get('new_variable_name', '')}** = {d.get('method', '')}({', '.join(d.get('source_variables', []))})")
                        st.caption(f"  _{d.get('reason', '')}_")

            recipes = bp.get("analysis_recipes", [])
            if recipes:
                with st.expander(f"🔬 推荐分析方法（{len(recipes)} 项）", expanded=False):
                    for r in recipes:
                        st.caption(f"· **{r.get('recipe_name', '')}** — {r.get('analysis_type', '')} — {', '.join(r.get('variables', []))}")

            charts = bp.get("chart_plan", [])
            if charts:
                with st.expander(f"📊 推荐图表（{len(charts)} 项）", expanded=False):
                    for c in charts:
                        st.caption(f"· **{c.get('chart_name', '')}** ({c.get('chart_type', '')}) — {', '.join(c.get('variables', []))}")

            struct_rec = bp.get("report_structure_recommendation", {})
            if struct_rec:
                st.info(f"📄 推荐报告结构: **{struct_rec.get('recommended_structure', '')}** — {struct_rec.get('reason', '')}")

            bp_warnings = bp.get("warnings", [])
            if bp_warnings:
                with st.expander(f"⚠️ 风险提示（{len(bp_warnings)} 条）", expanded=False):
                    for w in bp_warnings:
                        st.caption(f"· {w}")

            # 一键采用
            st.markdown("---")
            bp_c1, bp_c2 = st.columns([1, 3])
            with bp_c1:
                if st.button("✅ 采用推荐方案", type="primary", key="gen_adopt_blueprint"):
                    msgs = gen_ctx.apply_blueprint(gen_blueprint)
                    # 同步到 session_state（gen_ctx.user_analysis_config 即同一 dict 对象）
                    st.session_state["generic_config"] = gen_ctx.user_analysis_config
                    # 清除 widget 缓存，确保所有相关控件读取新值
                    for wk in ["cfg_title", "cfg_target", "cfg_groups", "cfg_explanatory",
                               "ai_report_title", "ai_research_subject",
                               "ai_report_structure", "ai_report_style"]:
                        st.session_state.pop(wk, None)
                    for m in msgs:
                        st.success(m)
                    st.rerun()
            with bp_c2:
                st.caption("采用后将自动填入报告标题、核心变量、分组变量和解释变量。不会覆盖已手动修改的内容。")

            st.download_button(
                "📥 下载 analysis_blueprint.json",
                data=json.dumps(bp, ensure_ascii=False, indent=2, default=str),
                file_name=f"analysis_blueprint_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json",
                key="gen_dl_blueprint",
            )
