"""政务数据分析工作台 —— 通用问卷数据 AI 辅助统计分析与报告生成平台

5 步工作流:
  1. 数据与变量    — 上传数据、预览、变量识别
  2. 分析方案      — 手动配置或 AI 推荐分析方案
  3. 统计分析      — 单变量/双变量/多变量统一分析
  4. 可视化仪表盘  — 自动生成图表
  5. 报告工作台    — 报告生成、预览、导出
"""

import streamlit as st

# ── 核心数据模块 ──
from src.data_loader import (
    load_generic_data,
    load_generic_variable_table,
    get_data_quality_report,
)
from src.schema_infer import infer_variable_schema, build_variable_dict_map
from src.analysis_context import AnalysisContext

# ── UI 模块 ──
from src.ui.state import init_session_state
from src.ui.sidebar import render_sidebar, render_api_sidebar_section
from src.ui.styles import inject_app_css
from src.ui.analysis_helpers import auto_suggest_config_from_dict
from src.ui.messages import get_beginner_flow_guide, get_example_data_loaded_message
from src.ui.example_data import load_example_data as load_builtin_example_data
from src.ui.components import (
    render_page_header,
    render_pipeline_status,
    render_metric_card,
    render_empty_state,
    render_config_summary,
    render_section,
    render_warning_list,
)
from src.ui.tabs import (
    render_tab_data_upload,
    render_tab_data_overview,
    render_tab_variable_config,
    render_tab_quick_report,
    render_tab_analysis_config,
    render_tab_univariate_analysis,
    render_tab_bivariate_analysis,
    render_tab_multivariate_analysis,
    render_tab_visualization,
    render_tab_template_report,
    render_tab_ai_analysis,
)
from src.ui.tabs.tab_ai_analysis import apply_pending_blueprint_to_widget_state
from src.ui.theme import COLORS


# ================================================================
# 页面配置
# ================================================================
st.set_page_config(
    page_title="政务数据分析工作台",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 注入全局 CSS ──
inject_app_css()

# ── 初始化 session_state ──
init_session_state()


# ================================================================
# 侧边栏（全局输入）
# ================================================================
sb = render_sidebar()
render_api_sidebar_section()


# ================================================================
# 标题区
# ================================================================
render_page_header(
    title="政务数据分析工作台",
    subtitle="上传问卷数据，自动识别变量类型，完成统计分析并生成报告",
    step="",
)

# ── 免责声明（始终显示）──
st.markdown(
    f'<div style="font-size:11px;color:{COLORS.text_subtle};margin-bottom:16px;line-height:1.6;">'
    '本平台用于辅助统计分析和报告生成。统计关联不等于因果关系，分析结果需结合实际情况进行人工判断。'
    '</div>',
    unsafe_allow_html=True,
)


# ================================================================
# 示例数据 / 文件加载逻辑
# ================================================================
if sb["generic_file"] is not None and st.session_state.get("_use_example_data"):
    st.session_state["_use_example_data"] = False
    st.session_state.pop("_example_raw_df", None)
    st.session_state.pop("_example_var_dict_df", None)
    st.rerun()

if sb["load_example_clicked"]:
    example_df, example_var_df = load_builtin_example_data()
    if example_df is not None:
        st.session_state["_example_raw_df"] = example_df
        st.session_state["_example_var_dict_df"] = example_var_df
        st.session_state["_use_example_data"] = True
        st.rerun()
    else:
        st.session_state["_use_example_data"] = False

_using_example = st.session_state.get("_use_example_data", False)

# ── 无数据：引导页 ──
if sb["generic_file"] is None and not _using_example:
    render_section("开始使用")
    st.markdown(get_beginner_flow_guide())
    st.stop()


# ================================================================
# 加载数据
# ================================================================
if _using_example:
    raw_df = st.session_state.get("_example_raw_df")
    variable_df_generic = st.session_state.get("_example_var_dict_df")
    if raw_df is None:
        st.error("示例数据加载失败，请检查 examples/ 目录。")
        st.stop()
    st.success(get_example_data_loaded_message())
    _current_file_key = "example_data_v1"
    _file_name = "政府服务满意度示例数据.csv"
    _selected_sheet = ""
    _header_row = 0
else:
    raw_df = load_generic_data(sb["generic_file"], sheet_name=sb["selected_sheet"], header_row=sb["header_row"])
    if raw_df is None:
        st.error("数据加载失败，请检查文件格式。")
        st.stop()
    variable_df_generic = load_generic_variable_table(sb["var_table_file"]) if sb["var_table_file"] else None
    _current_file_key = f"{sb['generic_file'].name}_{sb['selected_sheet']}_{raw_df.shape}"
    _file_name = sb["generic_file"].name if sb["generic_file"] else ""
    _selected_sheet = sb["selected_sheet"] or ""
    _header_row = sb["header_row"]

# 清理列名
raw_df.columns = [str(c).strip() for c in raw_df.columns]

# ── 新文件检测 ──
if st.session_state.get("_last_file_key") != _current_file_key:
    st.session_state.pop("gen_tu_payload", None)
    st.session_state.pop("gen_blueprint", None)
    st.session_state.pop("_last_file_key", None)
    st.session_state["generic_config"] = {
        "report_title": "问卷数据分析报告",
        "target_variable": "",
        "group_variables": [],
        "explanatory_variables": [],
    }
    st.session_state["_last_file_key"] = _current_file_key


# ================================================================
# 变量识别 & 上下文构建
# ================================================================
generic_var_dict_map = build_variable_dict_map(variable_df_generic) if variable_df_generic is not None else {}

schema_df = infer_variable_schema(
    raw_df,
    variable_table=variable_df_generic,
    variable_dict_map=generic_var_dict_map if generic_var_dict_map else None,
)

quality = get_data_quality_report(raw_df)

type_map = {row["column"]: row["inferred_type"] for _, row in schema_df.iterrows()}
cn_map = {row["column"]: row["display_name"] for _, row in schema_df.iterrows()}

config = st.session_state["generic_config"]

# ── 构建 AnalysisContext ──
gen_ctx = AnalysisContext(
    mode="generic",
    dataset_name=_file_name,
    data_file_name=_file_name,
    df=raw_df,
    sheet_name=_selected_sheet,
    file_type="csv" if _file_name.endswith(".csv") else "xlsx",
    variable_dict_df=variable_df_generic,
    variable_dict_map=generic_var_dict_map,
    variable_schema=schema_df,
    quality=quality,
    user_analysis_config=config,
)
gen_ctx.build_type_maps()
auto_suggest_config_from_dict(gen_ctx)

# ── 预设方案 ──
if sb["gov_profile"] and sb["profile_key"]:
    gen_ctx.apply_preset_profile(sb["gov_profile"])
    st.session_state["generic_config"] = gen_ctx.user_analysis_config
    config = st.session_state["generic_config"]
    auto_suggest_config_from_dict(gen_ctx)

# ── 可分析变量列表 ──
analyzable_cols = schema_df[
    schema_df["inferred_type"].isin(["numeric", "categorical", "ordinal", "binary"])
]["column"].tolist()

# ── 消费 AI blueprint pending ──
apply_pending_blueprint_to_widget_state()


# ================================================================
# AI 蓝图生成区（Tab 2 专用，从 tab_ai_analysis 提取）
# ================================================================
def _render_ai_blueprint_section(
    raw_df, schema_df, config, quality, generic_var_dict_map,
    generic_file_name, selected_sheet, gen_ctx,
):
    """渲染 AI 分析方案推荐区域（不含报告生成）。

    从 render_tab_ai_analysis 提取蓝图生成逻辑，
    避免在 Tab 2 中渲染整个报告工作台。
    """
    provider_key = st.session_state.get("_provider_key", "")
    provider_config = st.session_state.get("_provider_config", {})
    resolved_api_key = st.session_state.get("_api_key", "")
    selected_model = st.session_state.get("_ai_model", "")

    # ── API 状态 ──
    if not resolved_api_key or not selected_model:
        render_empty_state(
            "AI 分析方案需要 API 配置",
            "请在左侧边栏「AI API 设置」中选择厂商、输入 API Key 并选择模型。",
            action_label="前往侧边栏配置 API",
        )
        return

    from src.ui.security import mask_api_key
    display_name = provider_config.get("display_name", provider_key) if provider_config else provider_key
    st.caption(f"已配置：**{display_name}** · 模型：`{selected_model}` · 密钥：{mask_api_key(resolved_api_key)}")

    # ── 分析目标 ──
    user_goal = st.text_input(
        "分析目标（可选）",
        placeholder="例如：分析影响满意度的因素 / 探索变量间关系",
        key="gen_ai_goal_tab2",
    )

    # ── 生成数据理解 Payload ──
    tu_col1, tu_col2 = st.columns([1, 3])
    with tu_col1:
        gen_tu_btn = st.button("生成数据理解 Payload", key="gen_tu_btn_tab2")
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
                    selected_sheet=selected_sheet or "",
                    file_type="csv" if generic_file_name.endswith(".csv") else "xlsx",
                    dataset_name=generic_file_name,
                )
                tu_placeholder.success(
                    f"数据理解 Payload 生成完成 "
                    f"（{len(tu_to_json(st.session_state['gen_tu_payload']).encode('utf-8')) / 1024:.1f} KB）"
                )
            except Exception as e:
                tu_placeholder.error(f"生成失败：{e}")

    gen_tu_payload = st.session_state.get("gen_tu_payload")

    # ── AI 方案推荐 ──
    if gen_tu_payload:
        st.markdown("---")

        if not provider_config:
            st.warning("未找到厂商配置，请先在侧边栏中选择厂商。")
        else:
            if st.button("生成 AI 分析方案", key="gen_blueprint_btn_tab2"):
                with st.spinner("AI 正在分析数据结构并推荐方案…"):
                    from src.ai_table_planner import generate_analysis_blueprint
                    bp_result = generate_analysis_blueprint(
                        table_understanding_payload=st.session_state["gen_tu_payload"],
                        provider_config=provider_config,
                        api_key=resolved_api_key,
                        model=selected_model,
                        provider_key=provider_key,
                    )
                if bp_result.get("success"):
                    st.session_state["gen_blueprint"] = bp_result["blueprint"]
                    st.success("AI 分析方案生成完成！")
                else:
                    st.error(f"生成失败：{bp_result.get('error', '未知错误')}")

        # ── 展示 AI 推荐方案 ──
        gen_blueprint = st.session_state.get("gen_blueprint")
        if gen_blueprint:
            bp = gen_blueprint
            ds = bp.get("dataset_understanding", {})

            # 数据集理解
            with st.expander("数据集理解", expanded=True):
                st.markdown(f"**类型**: {ds.get('dataset_type', '')}")
                st.markdown(f"**研究对象**: {ds.get('possible_research_subject', '')}")
                st.markdown(f"**主题**: {ds.get('main_analysis_theme', '')}")
                if ds.get("summary"):
                    st.caption(ds["summary"])

            # 推荐标题
            titles = bp.get("recommended_report_titles", [])
            if titles:
                with st.expander(f"推荐报告标题（{len(titles)} 个）", expanded=False):
                    for t in titles:
                        st.caption(f"· {t}")

            # 变量候选（三列）
            col_bp1, col_bp2, col_bp3 = st.columns(3)
            with col_bp1:
                with st.expander("核心变量候选", expanded=True):
                    for c in bp.get("target_variable_candidates", []):
                        icon = {"high": "★", "medium": "●", "low": "○"}.get(c.get("priority", ""), "")
                        st.caption(f"{icon} **{c.get('display_name', '')}** (`{c.get('variable', '')}`)")
                        st.caption(f"  _{c.get('reason', '')}_")
            with col_bp2:
                with st.expander("分组变量候选", expanded=True):
                    for c in bp.get("group_variable_candidates", []):
                        icon = {"high": "★", "medium": "●", "low": "○"}.get(c.get("priority", ""), "")
                        st.caption(f"{icon} **{c.get('display_name', '')}** (`{c.get('variable', '')}`)")
            with col_bp3:
                with st.expander("解释变量候选", expanded=True):
                    for c in bp.get("explanatory_variable_candidates", []):
                        icon = {"high": "★", "medium": "●", "low": "○"}.get(c.get("priority", ""), "")
                        st.caption(f"{icon} **{c.get('display_name', '')}** (`{c.get('variable', '')}`)")

            # 推荐图表
            charts = bp.get("chart_plan", [])
            if charts:
                with st.expander(f"推荐图表（{len(charts)} 项）", expanded=False):
                    for c in charts:
                        st.caption(f"· **{c.get('chart_name', '')}** ({c.get('chart_type', '')})")

            # 风险提示
            bp_warnings = bp.get("warnings", [])
            if bp_warnings:
                render_warning_list(bp_warnings, title="AI 风险提示")

            # ── 一键采用 ──
            if gen_ctx is not None:
                st.markdown("---")
                bp_c1, bp_c2 = st.columns([1, 3])
                with bp_c1:
                    if st.button("采用推荐方案", type="primary", key="gen_adopt_blueprint_tab2"):
                        # v0.1.0: 使用统一状态流 — apply_blueprint_to_config 内部调用
                        # apply_analysis_config → invalidate_downstream
                        msgs = gen_ctx.apply_blueprint_to_config(
                            gen_blueprint, schema_df=schema_df, overwrite=True,
                        )
                        # 同步到全局 session_state
                        st.session_state["generic_config"] = gen_ctx.user_analysis_config
                        cfg = gen_ctx.user_analysis_config
                        # 写入 pending 标记（在 app.py 开头消费，早于所有 widget 渲染）
                        st.session_state["_pending_ai_blueprint_apply"] = {
                            "title":                cfg.get("report_title", ""),
                            "target_variable":      cfg.get("target_variable", ""),
                            "group_variables":      cfg.get("group_variables", []),
                            "explanatory_variables": cfg.get("explanatory_variables", []),
                            "research_subject":     cfg.get("research_subject", ""),
                            "report_structure":     cfg.get("report_structure", ""),
                            "report_style":         cfg.get("report_style", ""),
                            "report_length":        cfg.get("report_length", ""),
                            "html_theme":           cfg.get("html_theme", ""),
                        }
                        for m in msgs:
                            st.success(m)
                        # 下游已通过 invalidate_downstream 标记失效
                        if not gen_ctx.downstream_valid:
                            st.info("分析结果已标记为失效，请前往「统计分析」页面重新执行分析。")
                        st.rerun()
                with bp_c2:
                    st.caption("采用后将自动填入核心变量、分组变量和解释变量。")


# ================================================================
# 数据质量指标卡片（紧凑一行）
# ================================================================
mc1, mc2, mc3, mc4, mc5 = st.columns(5)
with mc1:
    render_metric_card("样本量", f"{quality['样本量']:,}")
with mc2:
    render_metric_card("变量数量", str(quality["变量数"]))
with mc3:
    missing = quality["缺失值总数"]
    render_metric_card("缺失值", str(missing), status="warning" if missing > 0 else "neutral")
with mc4:
    dup = quality["重复行数"]
    render_metric_card("重复行", str(dup), status="warning" if dup > 0 else "neutral")
with mc5:
    render_metric_card("内存占用", quality["内存占用"])


# ================================================================
# 流程状态条
# ================================================================
render_pipeline_status(gen_ctx)


# ================================================================
# 5 步主流程 Tab
# ================================================================
gt1, gt2, gt3, gt4, gt5 = st.tabs([
    "1  数据与变量",
    "2  分析方案",
    "3  统计分析",
    "4  可视化仪表盘",
    "5  报告工作台",
])


# ================================================================
# Tab 1: 数据与变量
# ================================================================
with gt1:
    render_page_header("数据与变量", "上传问卷数据、预览数据、识别变量类型", step="步骤 1/5")

    # ── 数据上传区 ──
    render_section("数据文件", "已加载的数据文件和基本信息")
    render_tab_data_upload(sb, raw_df, file_name=_file_name, selected_sheet=_selected_sheet)

    # ── 数据预览 ──
    render_section("数据预览", "前 100 行数据预览")
    render_tab_data_overview(raw_df, schema_df, quality)

    # ── 变量识别 ──
    render_section("变量识别与管理", "确认或修正自动推断的变量类型")
    render_tab_variable_config(
        sb, raw_df, schema_df, type_map,
        quality, generic_var_dict_map, gen_ctx,
        file_name=_file_name, selected_sheet=_selected_sheet,
    )


# ================================================================
# Tab 2: 分析方案
# ================================================================
with gt2:
    render_page_header("分析方案", "设置核心变量、分组变量与解释变量，或使用 AI 推荐方案", step="步骤 2/5")

    # ── 当前方案摘要 ──
    render_config_summary(config, schema_df)

    # ── 手动配置 ──
    render_section("变量配置", "选择分析的核心变量、分组变量和解释变量")
    render_tab_analysis_config(schema_df, type_map, cn_map, config, analyzable_cols)

    # ── 方案快速总结 ──
    with st.expander("方案摘要", expanded=False):
        render_tab_quick_report(raw_df, schema_df, quality, generic_var_dict_map)

    # ── AI 分析方案（仅蓝图部分）──
    render_section("AI 分析方案", "让 AI 理解数据结构并推荐最优分析方案")
    _render_ai_blueprint_section(raw_df, schema_df, config, quality,
                                  generic_var_dict_map, _file_name,
                                  _selected_sheet, gen_ctx)


# ================================================================
# Tab 3: 统计分析
# ================================================================
with gt3:
    render_page_header("统计分析", "单变量描述、双变量交叉、多变量回归分析", step="步骤 3/5")

    target = config.get("target_variable", "")
    if not target:
        render_empty_state(
            "尚未设置核心变量",
            "请先在「分析方案」中选择核心变量（target variable），再执行统计分析。",
            action_label="前往分析方案",
        )
    else:
        # ── v0.1.0: 下游失效状态提示 ──
        if not gen_ctx.downstream_valid:
            reason = gen_ctx.invalidation_reason or "配置已更新"
            st.info(f"分析配置已变更（{reason}），请点击下方按钮重新执行分析。")

        # ── 统一执行按钮 ──
        run_col1, run_col2 = st.columns([1, 3])
        with run_col1:
            run_label = "重新执行分析" if not gen_ctx.downstream_valid else "执行统计分析"
            if st.button(run_label, type="primary", key="run_analysis_pipeline_btn"):
                with st.spinner("正在执行完整分析管道…"):
                    pipeline_result = gen_ctx.run_analysis_pipeline(force=True)
                    if pipeline_result.get("success"):
                        st.success(
                            f"分析完成 — "
                            f"包含单变量、双变量、多变量分析"
                            + (f" 和 {len(pipeline_result.get('dashboard_charts', []))} 个图表"
                               if pipeline_result.get('dashboard_charts') else "")
                        )
                    else:
                        st.error(pipeline_result.get("error", "分析执行失败"))
                    st.rerun()
        with run_col2:
            if gen_ctx.downstream_valid and gen_ctx.analysis_results:
                st.caption("当前分析结果有效，可直接查看。配置变更后需要重新执行。")
            elif not gen_ctx.downstream_valid:
                st.caption("配置已变更，分析结果需要刷新。")

        # ── 分析结果展示（v0.1.0: 传入预计算结果，不再各自独立分析）──
        render_section("单变量分析", f"对 {target} 等变量进行描述统计")
        render_tab_univariate_analysis(
            raw_df, schema_df, cn_map, analyzable_cols, variable_df_generic,
            precomputed_results=gen_ctx.analysis_results if gen_ctx.analysis_results else None,
        )

        render_section("双变量分析", "分类变量间的交叉分析和数值变量间的相关性分析")
        render_tab_bivariate_analysis(
            raw_df, schema_df, config, type_map, cn_map, generic_var_dict_map,
            precomputed_results=gen_ctx.analysis_results if gen_ctx.analysis_results else None,
        )

        render_section("多变量分析", "多元回归分析")
        render_tab_multivariate_analysis(
            raw_df, config, type_map, cn_map,
            precomputed_results=gen_ctx.analysis_results if gen_ctx.analysis_results else None,
        )


# ================================================================
# Tab 4: 可视化仪表盘
# ================================================================
with gt4:
    render_page_header("可视化仪表盘", "基于分析方案自动生成交互式图表", step="步骤 4/5")

    if not target:
        render_empty_state(
            "还不能生成图表",
            "请先在「分析方案」中选择核心变量，然后执行统计分析。",
            action_label="前往分析方案",
        )
    elif not gen_ctx.downstream_valid:
        render_empty_state(
            "图表需要刷新",
            "分析配置已变更。请先在「统计分析」页面重新执行分析，"
            "然后再查看图表。",
            action_label="前往统计分析",
        )
    else:
        render_tab_visualization(
            raw_df, schema_df, config, type_map, cn_map,
            precomputed_charts=gen_ctx.dashboard_charts if gen_ctx.dashboard_charts else None,
            downstream_valid=gen_ctx.downstream_valid,
        )


# ================================================================
# Tab 5: 报告工作台
# ================================================================
with gt5:
    render_page_header("报告工作台", "生成报告草稿、配置文献综述与背景材料、预览并导出", step="步骤 5/5")

    if not target:
        render_empty_state(
            "还不能生成报告",
            "请先在「分析方案」中选择核心变量，系统将基于分析结果自动撰写报告。",
            action_label="前往分析方案",
        )
    else:
        # ── 模板报告 ──
        render_section("模板报告", "基于统计模板自动生成，不需要 AI API")
        render_tab_template_report(raw_df, schema_df, config, generic_var_dict_map)

        # ── AI 报告（完整报告生成工作台）──
        # v0.1.0: 传入统一管道预计算结果，避免重复分析
        render_section("AI 报告", "由大语言模型基于统计数据撰写分析报告")
        render_tab_ai_analysis(
            raw_df, schema_df, config, quality,
            generic_var_dict_map,
            _file_name,
            _selected_sheet,
            gen_ctx,
            precomputed_payload=gen_ctx.analysis_payload,
            precomputed_analysis_results=gen_ctx.analysis_results if gen_ctx.analysis_results else None,
            downstream_valid=gen_ctx.downstream_valid,
        )


# ================================================================
# 页脚
# ================================================================
st.markdown("---")
st.caption("政务数据分析工作台  v0.1.0")
