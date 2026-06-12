"""通用问卷数据 AI 辅助统计分析与报告生成平台

统一分析平台支持：
  - 任意 Excel / CSV 问卷数据（自动推断变量类型 + 变量说明表）
  - 可选预设分析方案（如政务满意度调查），一键填充分析配置
  - AI 驱动的分析规划与自动报告生成

数据流：
  uploaded_file → load_generic_data() → infer_variable_schema()
  → 用户配置（或预设方案） → generic_analysis → generic_charts → report
"""

import streamlit as st

# ---- 核心数据模块 ----
from src.data_loader import (
    load_generic_data,
    load_generic_variable_table,
    get_data_quality_report,
)
from src.schema_infer import infer_variable_schema
from src.analysis_context import AnalysisContext

# ── UI 组件模块 ──
from src.ui.state import init_session_state
from src.ui.sidebar import render_sidebar
from src.ui.styles import inject_app_css
from src.ui.analysis_helpers import auto_suggest_config_from_dict
from src.ui.messages import get_beginner_flow_guide, get_example_data_loaded_message
from src.ui.example_data import load_example_data as load_builtin_example_data
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


# ================================================================
# 页面配置
# ================================================================
st.set_page_config(
    page_title="通用问卷数据 AI 分析平台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ================================================================
# 自定义 CSS
# ================================================================
inject_app_css()


# ── 初始化所有 session_state 键 ──
init_session_state()


# ================================================================
# 统一分析平台
# ================================================================
# ---- 标题 ----
st.markdown(
    '<p class="main-title">📊 通用问卷数据<br>'
    'AI 辅助统计分析与报告生成平台</p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="main-subtitle">'
    '上传任意 Excel 或 CSV 问卷数据，自动识别变量类型，'
    '完成描述统计、交叉分析、相关分析、回归分析与报告生成。'
    '</p>',
    unsafe_allow_html=True,
)
st.markdown('<div class="disclaimer">'
    '📌 本平台用于辅助统计分析和报告生成。统计关联不等于因果关系，分析结果需结合实际情况进行人工判断。'
    '</div>',
    unsafe_allow_html=True,
)

# ---- 侧边栏 ----
sb = render_sidebar()

# ---- API 配置（侧边栏） ----
from src.ui.sidebar import render_api_sidebar_section
render_api_sidebar_section()

# ── 检测文件上传：如果用户上传了文件但当前处于示例数据模式，自动切换 ──
if sb["generic_file"] is not None and st.session_state.get("_use_example_data"):
    st.session_state["_use_example_data"] = False
    st.session_state.pop("_example_raw_df", None)
    st.session_state.pop("_example_var_dict_df", None)
    st.rerun()

# ── 示例数据加载 ──
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

# ---- 加载数据 ----
if sb["generic_file"] is None and not _using_example:
    st.info("👈 请在左侧边栏上传问卷数据文件（支持 .xlsx / .xls / .csv），或点击「📥 加载内置示例数据」快速体验。")
    st.markdown(get_beginner_flow_guide())
    st.stop()

# 加载数据（区分示例数据 vs 用户上传）
if _using_example:
    raw_df = st.session_state.get("_example_raw_df")
    variable_df_generic = st.session_state.get("_example_var_dict_df")
    if raw_df is None:
        st.error("示例数据加载失败，请检查 examples/ 目录。")
        st.stop()
    # 示例数据提示
    st.success(get_example_data_loaded_message())
    # 伪造一个 file key 用于检测
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

# 清理列名（去除空白）
raw_df.columns = [str(c).strip() for c in raw_df.columns]

# ── 检测是否为新文件，清理旧 session_state ──
if st.session_state.get("_last_file_key") != _current_file_key:
    st.session_state.pop("gen_tu_payload", None)
    st.session_state.pop("gen_blueprint", None)
    st.session_state.pop("_last_file_key", None)
    # 重置为默认配置（数据源变了，旧分析配置不再适用）
    st.session_state["generic_config"] = {
        "report_title": "问卷数据分析报告",
        "target_variable": "",
        "group_variables": [],
        "explanatory_variables": [],
    }
    st.session_state["_last_file_key"] = _current_file_key

# ── 构建变量说明字典（增强利用） ──
from src.schema_infer import build_variable_dict_map
generic_var_dict_map = build_variable_dict_map(variable_df_generic) if variable_df_generic is not None else {}

# 推断变量类型
schema_df = infer_variable_schema(
    raw_df,
    variable_table=variable_df_generic,
    variable_dict_map=generic_var_dict_map if generic_var_dict_map else None,
)

# 数据质量报告
quality = get_data_quality_report(raw_df)

# 构建类型查找
type_map = {row["column"]: row["inferred_type"] for _, row in schema_df.iterrows()}
cn_map = {row["column"]: row["display_name"] for _, row in schema_df.iterrows()}

config = st.session_state["generic_config"]

# ---- 顶部指标卡片 ----
mc1, mc2, mc3, mc4, mc5 = st.columns(5)
mc1.metric("📋 样本量", f"{quality['样本量']:,}")
mc2.metric("📊 变量数量", quality["变量数"])
mc3.metric("⚠️ 缺失值", quality["缺失值总数"])
mc4.metric("🔄 重复行", quality["重复行数"])
mc5.metric("💾 内存", quality["内存占用"])

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

# ── 创建 AnalysisContext（通用模式） ──
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
# 自动从变量说明表检测变量用途并建议配置
auto_suggest_config_from_dict(gen_ctx)

# ── 应用预设方案（仅首次加载或方案变更时） ──
if sb["gov_profile"] and sb["profile_key"]:
    gen_ctx.apply_preset_profile(sb["gov_profile"])
    # 同步到 session_state
    st.session_state["generic_config"] = gen_ctx.user_analysis_config
    config = st.session_state["generic_config"]
    auto_suggest_config_from_dict(gen_ctx)  # 重新检测（profile 可能改变了配置）

# ---- 可分析变量列表（供 Tab 4/5 共享） ----
analyzable_cols = schema_df[
    schema_df["inferred_type"].isin(["numeric", "categorical", "ordinal", "binary"])
]["column"].tolist()

# ---- 11 Tabs ----
gt1, gt2, gt3, gt4, gt5, gt6, gt7, gt8, gt9, gt10 = st.tabs([
    "📁 数据上传",
    "📋 数据概览",
    "🔍 变量识别",
    "⚙️ 分析配置",
    "📊 单变量分析",
    "🔗 双变量分析",
    "📈 多变量分析",
    "📉 可视化图表",
    "📄 报告生成",
    "🤖 AI 智能分析",
])

# ============ Tab 1: 数据上传 ============
with gt1:
    render_tab_data_upload(sb, raw_df, file_name=_file_name, selected_sheet=_selected_sheet)

# ============ Tab 2: 数据概览 ============
with gt2:
    render_tab_data_overview(raw_df, schema_df, quality)

# ============ Tab 3: 变量识别 ============
with gt3:
    render_tab_variable_config(
        sb, raw_df, schema_df, type_map,
        quality, generic_var_dict_map, gen_ctx,
        file_name=_file_name, selected_sheet=_selected_sheet,
    )
    render_tab_quick_report(raw_df, schema_df, quality, generic_var_dict_map)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

# ============ Tab 4: 分析配置 ============
with gt4:
    render_tab_analysis_config(schema_df, type_map, cn_map, config, analyzable_cols)

# ============ Tab 5: 单变量分析 ============
with gt5:
    render_tab_univariate_analysis(raw_df, schema_df, cn_map, analyzable_cols, variable_df_generic)

# ============ Tab 6: 双变量分析 ============
with gt6:
    render_tab_bivariate_analysis(raw_df, schema_df, config, type_map, cn_map, generic_var_dict_map)

# ============ Tab 7: 多变量分析 ============
with gt7:
    render_tab_multivariate_analysis(raw_df, config, type_map, cn_map)

# ============ Tab 8: 可视化图表 ============
with gt8:
    render_tab_visualization(raw_df, schema_df, config, type_map, cn_map)

# ============ Tab 9: 报告生成 ============
with gt9:
    render_tab_template_report(raw_df, schema_df, config, generic_var_dict_map)

# ============ Tab 10: AI 智能分析 ============
with gt10:
    render_tab_ai_analysis(
        raw_df, schema_df, config, quality,
        generic_var_dict_map,
        _file_name,
        _selected_sheet,
        gen_ctx,
    )
# ---- 页脚 ----
st.markdown("---")
st.caption("通用问卷数据 AI 辅助统计分析与报告生成平台  v3.0")
