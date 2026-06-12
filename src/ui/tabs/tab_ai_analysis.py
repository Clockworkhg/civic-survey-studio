"""Tab 10: AI Intelligent Analysis — provider config, model selection,
literature search, background research, payload generation, AI report generation.

This module extracts the full Tab 10 UI from app.py into a standalone render
function.  No user-visible behaviour, widget keys, or session_state keys are
changed.
"""

from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from src.analysis_packager import build_analysis_payload, to_json_payload
from src.generic_analysis import run_full_analysis
from src.generic_charts import generate_dashboard_charts
from src.schema_infer import _assess_privacy_risk
from src.literature_search import search_papers
from src.literature_review import parse_year_range
from src.background_research import list_background_sources, build_background_context

from src.ui.options import (
    get_structure_options,
    get_style_options,
    get_length_options,
    get_html_theme_options,
    is_structure_supports_literature,
)
from src.ui.report_generation import (
    build_llm_config_from_ui,
    build_report_config_from_ui,
    run_report_generation_from_ui,
)
from src.ui.messages import (
    get_no_api_key_short_message,
    get_literature_empty_message,
    get_literature_error_message,
    get_literature_keywords_hint,
    get_privacy_warning_message,
    get_sensitive_field_data_explanation,
    get_ai_report_error_message,
)
from src.ui.security import (
    summarize_ai_variable_privacy,
    get_ai_privacy_summary_message,
    get_outputs_safety_hint,
)


# ================================================================
# Private helpers
# ================================================================

def _build_chart_summaries(dashboard_charts: List) -> List[Dict[str, Any]]:
    """将 generate_dashboard_charts 的输出转为文字摘要列表。"""
    summaries = []
    for item in dashboard_charts:
        if not isinstance(item, (tuple, list)) or len(item) < 3:
            continue
        chart_key, chart_title, fig = item[0], item[1], item[2]
        if fig is None:
            continue

        summary: Dict[str, Any] = {
            "title": chart_title,
            "key": chart_key,
            "type": "",
            "variables": [],
            "trend": "",
        }

        # 从 key 推断变量信息
        parts = str(chart_key).split("__") if "__" in str(chart_key) else [chart_key]
        try:
            # 尝试从 plotly figure 推断图表类型
            if hasattr(fig, "data") and fig.data:
                first_trace = fig.data[0]
                trace_type = getattr(first_trace, "type", "")
                if trace_type == "histogram" or "histogram" in str(type(first_trace)):
                    summary["type"] = "histogram"
                elif trace_type == "bar":
                    summary["type"] = "bar_chart"
                elif trace_type == "box":
                    summary["type"] = "box_plot"
                elif trace_type == "scatter":
                    summary["type"] = "scatter_plot"
                elif trace_type == "heatmap":
                    summary["type"] = "heatmap"
                elif trace_type == "pie":
                    summary["type"] = "pie_chart"
                else:
                    summary["type"] = trace_type or "chart"

                # 提取主要趋势 / 最值
                if hasattr(first_trace, "x") and hasattr(first_trace, "y"):
                    x_vals = list(first_trace.x) if first_trace.x is not None else []
                    y_vals = list(first_trace.y) if first_trace.y is not None else []
                    if y_vals:
                        clean_y = [v for v in y_vals if v is not None]
                        if clean_y:
                            max_idx = clean_y.index(max(clean_y)) if max(clean_y) > 0 else 0
                            min_idx = clean_y.index(min(clean_y)) if min(clean_y) < 0 else 0
                            if max_idx < len(x_vals):
                                summary["max_category"] = str(x_vals[max_idx])[:60]
                            if min_idx < len(x_vals):
                                summary["min_category"] = str(x_vals[min_idx])[:60]
        except Exception:
            pass

        summaries.append(summary)

    return summaries


# ================================================================
# Main render function
# ================================================================

def render_tab_ai_analysis(
    raw_df: pd.DataFrame,
    schema_df: pd.DataFrame,
    config: Dict[str, Any],
    quality: Dict[str, Any],
    generic_var_dict_map: Dict[str, Any],
    generic_file_name: str,
    selected_sheet: str,
    gen_ctx: Any = None,
) -> None:
    """Render Tab 10: AI Intelligent Analysis.

    Parameters
    ----------
    raw_df : pd.DataFrame
        The raw survey data.
    schema_df : pd.DataFrame
        Variable schema (mutated in-place by privacy settings).
    config : Dict[str, Any]
        Analysis configuration dict (mutated in-place for report_title / research_subject).
    quality : Dict[str, Any]
        Data quality report from ``get_data_quality_report``.
    generic_var_dict_map : Dict[str, Any]
        Variable dictionary (display_name → metadata mapping).
    generic_file_name : str
        Original upload filename (used for file-type detection).
    selected_sheet : str
        Selected sheet name (Excel) or empty string (CSV).
    """

    st.markdown("### 🤖 AI 自动分析与报告生成")
    st.caption("由大语言模型基于统计数据自动撰写分析报告。API 配置请在左侧边栏「🤖 AI API 设置」中完成。")

    # ---- 隐私提示 ----
    st.warning(
        "🔒 **隐私提示**：使用 AI 自动报告功能时，统计摘要、变量结构和必要的分析结果会"
        "发送给所选模型服务商。请勿上传未脱敏的个人身份信息、敏感信息或涉密数据。",
        icon="🔒",
    )

    # ---- 从 session_state 读取 API 配置（由侧边栏 api_config 模块设置） ----
    provider_key = st.session_state.get("_provider_key", "")
    provider_config = st.session_state.get("_provider_config", {})
    resolved_api_key = st.session_state.get("_api_key", "")
    selected_model = st.session_state.get("_ai_model", "")

    # ---- API 配置状态卡片 ----
    st.markdown("#### 1. API 配置状态")
    if not resolved_api_key or not selected_model:
        st.warning(
            "⚠️ 尚未配置 AI API。请在左侧边栏 **「🤖 AI API 设置」** 中"
            "选择厂商、输入 API Key 并选择模型。"
        )
    else:
        from src.ui.security import mask_api_key
        display_name = provider_config.get("display_name", provider_key) if provider_config else provider_key
        st.success(
            f"✅ 已配置：**{display_name}** · "
            f"模型：`{selected_model}` · "
            f"密钥：{mask_api_key(resolved_api_key)}"
        )

        # ============================================
        # Step 0: AI 数据理解 / 分析规划（蓝图）
        # ============================================
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown("#### 2. 🧠 AI 分析方案规划")
        st.caption("让 AI 理解数据结构，推荐最合适的分析方案和变量配置。")

        user_goal = st.text_input(
            "分析目标（可选）",
            placeholder="例如：分析影响满意度的因素 / 生成学术论文式报告",
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
                        selected_sheet=selected_sheet or "",
                        file_type="csv" if generic_file_name.endswith(".csv") else "xlsx",
                        dataset_name=generic_file_name,
                    )
                    tu_placeholder.success(
                        f"✅ 数据理解 Payload 生成完成 "
                        f"（{len(tu_to_json(st.session_state['gen_tu_payload']).encode('utf-8')) / 1024:.1f} KB）"
                    )
                except Exception as e:
                    tu_placeholder.error(f"❌ 生成失败：{e}")

        gen_tu_payload = st.session_state.get("gen_tu_payload")
        if gen_tu_payload and gen_ctx is not None:
            with st.expander("📋 数据理解 Payload 摘要", expanded=False):
                st.json(gen_ctx.to_dict())

        if gen_tu_payload:
            st.markdown("---")
            st.markdown("##### AI 分析方案推荐")

            if not resolved_api_key or not selected_model:
                st.info("💡 请先在左侧边栏「🤖 AI API 设置」中配置 API Key 和模型，然后生成分析方案。")
            elif not provider_config:
                st.warning("⚠️ 未找到厂商配置，请先在左侧边栏中选择厂商。")
            else:
                if st.button("🧠 生成 AI 分析方案", key="gen_blueprint_btn"):
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
                        st.success("✅ AI 分析方案生成完成！")
                    else:
                        st.error(f"❌ 生成失败：{bp_result.get('error', '未知错误')}")

            # 展示 AI 推荐方案
            gen_blueprint = st.session_state.get("gen_blueprint")
            if gen_blueprint:
                bp = gen_blueprint
                st.markdown("---")
                st.markdown("##### 📊 AI 推荐分析方案")

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
                if gen_ctx is not None:
                    st.markdown("---")
                    bp_c1, bp_c2 = st.columns([1, 3])
                    with bp_c1:
                        if st.button("✅ 采用推荐方案", type="primary", key="gen_adopt_blueprint"):
                            msgs = gen_ctx.apply_blueprint(gen_blueprint)
                            st.session_state["generic_config"] = gen_ctx.user_analysis_config
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

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

        # ---- LLM 生成参数 ----
        st.markdown("#### 3. LLM 生成参数")
        cp1, cp2 = st.columns(2)
        with cp1:
            temperature = st.slider(
                "Temperature", 0.0, 2.0, 0.3, 0.1,
                key="ai_temperature",
                help="越低越确定，越高越随机。报告建议 0.2-0.5。",
            )
        with cp2:
            max_tokens = st.number_input(
                "Max Tokens", 512, 32768, 4096, 512,
                key="ai_max_tokens",
                help="生成报告的最大 token 数。",
            )

        # ---- 报告参数设置 ----
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown("#### 5. 📝 报告参数设置")
        st.caption("设置报告主题、结构、写作风格和导出样式。")

        # 报告主题和研究对象
        rp_col1, rp_col2 = st.columns(2)
        with rp_col1:
            report_title_input = st.text_input(
                "报告标题",
                value=config.get("report_title", "问卷数据分析报告"),
                key="ai_report_title",
                help="将作为报告的主标题显示。",
            )
        with rp_col2:
            research_subject = st.text_input(
                "研究对象",
                value=config.get("research_subject", ""),
                key="ai_research_subject",
                placeholder="例如：某电商平台用户、某社区居民…",
                help="描述数据的研究对象/场景，帮助 AI 理解数据背景。",
            )

        # 报告结构 / 风格 / 长度 / 主题 — 统一来源
        report_structure = st.selectbox(
            "报告结构类型",
            get_structure_options(),
            key="ai_report_structure",
            help="决定报告的章节结构。不同结构适用于不同场景。",
        )

        rp_col3, rp_col4 = st.columns(2)
        with rp_col3:
            report_style = st.selectbox(
                "写作语言风格",
                get_style_options(),
                key="ai_report_style",
                help="决定报告的语言表达方式。",
            )
        with rp_col4:
            report_length = st.selectbox(
                "报告篇幅",
                get_length_options(),
                key="ai_report_length",
                help="控制报告的详细程度。",
            )

        # HTML 导出主题
        html_theme = st.selectbox(
            "HTML 导出主题",
            get_html_theme_options(),
            index=3,  # 默认"简洁课程作业风"
            key="ai_html_theme",
            help="决定 HTML 报告的视觉样式。不影响 Markdown 和 Word 导出。",
        )

        # 更新 config 中的标题
        if report_title_input:
            config["report_title"] = report_title_input
        if research_subject:
            config["research_subject"] = research_subject

        # ---- 文献综述检索（可选）----
        literature_config: dict = {"enabled": False}  # 默认值
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown("#### 📚 文献综述检索（可选）")
        st.caption(
            "自动检索真实学术文献（Semantic Scholar / OpenAlex / CrossRef），"
            "由 AI 合成文献综述并注入「学术论文式报告」。"
        )

        enable_literature = st.checkbox(
            "启用文献综述检索",
            value=st.session_state.get("_lit_enabled", False),
            key="ai_enable_literature",
            help=(
                "启用后，系统将根据您输入的关键词检索免费学术文献数据库，"
                "并由 AI 合成文献综述。**仅在「学术论文式报告」结构下生效。**"
            ),
        )

        if enable_literature:
            st.session_state["_lit_enabled"] = True
            lit_col1, lit_col2 = st.columns(2)
            with lit_col1:
                literature_keywords = st.text_input(
                    "研究关键词",
                    value=st.session_state.get("_lit_keywords", ""),
                    key="ai_literature_keywords",
                    placeholder="例如：公众满意度 政务服务 影响因素",
                    help="输入 2-5 个核心研究关键词（中文或英文均可），用于检索相关学术文献。",
                )
                st.caption(get_literature_keywords_hint())
                st.session_state["_lit_keywords"] = literature_keywords
            with lit_col2:
                literature_year_range = st.selectbox(
                    "发表时间范围",
                    ["不限", "近20年", "近10年", "近5年"],
                    index=0,
                    key="ai_literature_year_range",
                    help="限定检索文献的发表年份范围。",
                )

            literature_max_sources = st.slider(
                "最大文献来源数",
                min_value=5, max_value=30, value=15, step=5,
                key="ai_literature_max_sources",
                help="检索并引用的最大文献数量。更多文献可能延长检索和 AI 合成时间。",
            )

            literature_config = {
                "enabled": True,
                "keywords": literature_keywords,
                "max_sources": literature_max_sources,
                "year_range": literature_year_range,
            }

            # ── 文献检索预览 ──
            lit_prev_col1, lit_prev_col2 = st.columns([1, 3])
            with lit_prev_col1:
                preview_lit_btn = st.button(
                    "🔍 检索并预览文献",
                    key="preview_literature_btn",
                    help="立即检索学术文献并预览结果（不生成报告）。",
                )
            with lit_prev_col2:
                lit_preview_placeholder = st.empty()

            if preview_lit_btn:
                if not literature_keywords.strip():
                    lit_preview_placeholder.error("❌ 请先输入研究关键词。")
                else:
                    with lit_preview_placeholder.status(
                        f"正在检索文献: {literature_keywords}...", expanded=True
                    ) as lit_status:
                        try:
                            year_from, _ = parse_year_range(literature_year_range)
                            papers = search_papers(
                                literature_keywords,
                                max_results=literature_max_sources,
                                year_from=year_from,
                            )
                            if papers:
                                st.session_state["_lit_preview_papers"] = papers
                                st.session_state["_lit_preview_keywords"] = literature_keywords
                                lit_status.update(
                                    label=f"✅ 检索完成：找到 {len(papers)} 篇论文",
                                    state="complete",
                                )
                                # 展示论文卡片
                                for i, p in enumerate(papers[:10], 1):
                                    with st.container():
                                        st.markdown(
                                            f"**{i}. {p.title}**  "
                                            f"({p.year or 'n.d.'})  "
                                            f"`{p.source}`"
                                        )
                                        if p.doi:
                                            st.caption(f"DOI: [{p.doi}](https://doi.org/{p.doi})")
                                        if p.abstract:
                                            abs_preview = p.abstract[:250] + ("..." if len(p.abstract) > 250 else "")
                                            st.caption(abs_preview)
                                        st.markdown("---")
                                if len(papers) > 10:
                                    st.caption(f"... 还有 {len(papers) - 10} 篇，可在生成报告中查看完整列表")
                            else:
                                st.session_state["_lit_preview_papers"] = []
                                lit_status.update(
                                    label="⚠️ 未找到相关文献",
                                    state="error",
                                )
                                st.markdown(get_literature_empty_message(literature_keywords))
                        except Exception as e:
                            lit_status.update(
                                label="⚠️ 文献检索失败",
                                state="error",
                            )
                            st.markdown(get_literature_error_message(str(e)))

            # 显示上次检索的预览摘要（如果 session_state 中有）
            cached_papers = st.session_state.get("_lit_preview_papers")
            if cached_papers and not preview_lit_btn:
                st.caption(
                    f"📋 上次检索: {len(cached_papers)} 篇论文 "
                    f"（关键词: {st.session_state.get('_lit_preview_keywords', '')}）"
                )
        else:
            st.session_state["_lit_enabled"] = False
            literature_config = {"enabled": False}

        # ---- 研究背景材料（可选）----
        background_config: dict = {"enabled": False}  # 默认值
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown("#### 🌐 研究背景材料（可选）")
        st.caption(
            "加载结构化调研数据（政策文件、行业报告、背景研究），"
            "为报告的「研究背景」章节注入真实语境。适用于学术论文和政务决策报告。"
        )

        # 列出可用的背景调研目录（缓存避免每次重运行时扫描文件系统）
        @st.cache_data(ttl=300)
        def _cached_background_sources():
            return list_background_sources(".")

        try:
            available_sources = _cached_background_sources()
        except Exception:
            available_sources = []

        enable_background = st.checkbox(
            "启用研究背景注入",
            value=st.session_state.get("_bg_enabled", False),
            key="ai_enable_background",
            help=(
                "启用后，系统将读取指定目录中的结构化调研 JSON 文件，"
                "提取背景材料并注入到报告的「研究背景与问题提出」章节。"
                "\n\n背景材料可通过 `/research-deep` 命令生成，也可手动编写。"
                "示例数据位于 `background/example/` 目录。"
            ),
        )

        if enable_background:
            st.session_state["_bg_enabled"] = True
            if available_sources:
                bg_options = ["[手动输入路径]"] + [
                    f"{s['name']} ({s['json_count']} JSON, {s['size_kb']}KB)"
                    for s in available_sources
                ]
                bg_choice = st.selectbox(
                    "选择背景调研项目",
                    bg_options,
                    key="ai_background_select",
                    help="自动扫描的工作目录下的 background/ 或 research/ 子目录。",
                )
                if "手动输入" in bg_choice:
                    bg_source_path = st.text_input(
                        "背景材料路径",
                        value=st.session_state.get("_bg_path", "background/example"),
                        key="ai_background_path",
                        placeholder="输入目录路径（如 background/example）或 JSON/Markdown 文件路径",
                    )
                else:
                    bg_name = bg_choice.split(" (")[0]
                    bg_source_path = f"background/{bg_name}" if not bg_name.startswith("background") else bg_name
                    st.info(f"📂 将读取: {bg_source_path}")
            else:
                bg_source_path = st.text_input(
                    "背景材料路径",
                    value=st.session_state.get("_bg_path", "background/example"),
                    key="ai_background_path",
                    placeholder="输入目录路径（如 background/example）或 JSON/MD 文件路径",
                    help="可指向 /research-deep 产出的 results/ 目录，或手写的 Markdown 文件。",
                )

            st.session_state["_bg_path"] = bg_source_path
            background_config = {
                "enabled": True,
                "source_path": bg_source_path,
            }

            if bg_source_path and Path(bg_source_path).exists():
                st.success(f"✅ 路径有效: {bg_source_path}")

                # ── 背景材料预览 ──
                bg_prev_col1, bg_prev_col2 = st.columns([1, 3])
                with bg_prev_col1:
                    preview_bg_btn = st.button(
                        "📂 预览背景材料",
                        key="preview_background_btn",
                        help="加载并预览背景材料内容（不生成报告）。",
                    )
                with bg_prev_col2:
                    bg_preview_placeholder = st.empty()

                if preview_bg_btn:
                    with bg_preview_placeholder.status(
                        f"正在加载背景材料: {bg_source_path}...", expanded=True
                    ) as bg_status:
                        try:
                            ctx = build_background_context(bg_source_path)
                            if ctx:
                                st.session_state["_bg_preview_text"] = ctx
                                st.session_state["_bg_preview_path"] = bg_source_path
                                bg_status.update(
                                    label=f"✅ 加载完成：{len(ctx)} 字符",
                                    state="complete",
                                )
                                with st.expander("📄 背景材料预览", expanded=True):
                                    st.markdown(ctx)
                            else:
                                st.session_state["_bg_preview_text"] = ""
                                bg_status.update(
                                    label="⚠️ 未能从该路径提取有效内容",
                                    state="error",
                                )
                        except Exception as e:
                            bg_status.update(
                                label=f"❌ 加载失败: {e}",
                                state="error",
                            )

                # 显示上次加载的预览摘要
                cached_bg = st.session_state.get("_bg_preview_text")
                if cached_bg and not preview_bg_btn:
                    st.caption(
                        f"📋 上次加载: {len(cached_bg)} 字符 "
                        f"（路径: {st.session_state.get('_bg_preview_path', '')}）"
                    )
            elif bg_source_path:
                st.warning(f"⚠️ 路径不存在: {bg_source_path}")
        else:
            st.session_state["_bg_enabled"] = False
            background_config = {"enabled": False}

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

        # ---- 隐私与变量使用设置 ----
        st.markdown("#### 7. 🔒 隐私与变量使用设置")
        st.caption(
            "系统已自动评估每个变量的隐私风险。"
            "您可以逐列调整变量的使用方式和 AI 发送策略。"
        )

        # 筛选有隐私风险的变量（medium 和 high）
        if "privacy_risk" in schema_df.columns:
            privacy_vars = schema_df[
                schema_df["privacy_risk"].isin(["medium", "high"])
            ]
            high_risk_vars = schema_df[
                schema_df["privacy_risk"] == "high"
            ]
            medium_risk_vars = schema_df[
                schema_df["privacy_risk"] == "medium"
            ]
        else:
            privacy_vars = pd.DataFrame()
            high_risk_vars = pd.DataFrame()
            medium_risk_vars = pd.DataFrame()

        # ── 隐私风险汇总提醒 ──
        _high_count = len(high_risk_vars)
        _med_count = len(medium_risk_vars)
        if _high_count > 0 or _med_count > 0:
            st.warning(get_privacy_warning_message(_high_count, _med_count))

        if privacy_vars.empty:
            st.success(
                "✅ 所有变量的隐私风险均为低或无级别，"
                "默认以聚合统计形式纳入 AI 报告，无需额外设置。"
            )
        else:
            st.info(
                f"检测到 {len(privacy_vars)} 个变量存在中高隐私风险。"
                "默认情况下，高风险变量仅用于本地统计，不发送给 AI。"
                "您可以根据实际研究需要调整以下设置。"
            )

            for _, prow in privacy_vars.iterrows():
                col = prow["column"]
                risk = prow.get("privacy_risk", "medium")
                cat = prow.get("privacy_category", "unknown")
                cn_name = prow.get("display_name", "") or col
                vtype = prow.get("inferred_type", "")

                risk_emoji = {"medium": "🟡", "high": "🔴"}.get(risk, "⚪")
                cat_labels = {
                    "demographic_attribute": "人口统计属性",
                    "contact_info": "联系方式",
                    "direct_identifier": "直接身份标识",
                    "location_info": "地理位置",
                    "free_text": "自由文本",
                    "sensitive_attribute": "敏感属性",
                    "financial": "金融信息",
                    "unknown": "未知",
                }
                cat_cn = cat_labels.get(cat, cat)

                with st.expander(
                    f"{risk_emoji} {cn_name} (`{col}`) — {risk.upper()} 风险 · {cat_cn} · 类型: {vtype}",
                    expanded=(risk == "high"),
                ):
                    # 隐私类别说明
                    cat_explanation = get_sensitive_field_data_explanation(cat)
                    if cat_explanation:
                        st.caption(cat_explanation)

                    # 当前设置
                    allow_stats = prow.get("allow_local_stats", True)
                    allow_group = prow.get("allow_as_group_variable", risk != "high")
                    allow_model = prow.get("allow_in_model", risk != "high")
                    allow_ai = prow.get("allow_send_to_ai", risk != "high")
                    send_mode = prow.get("send_to_ai_mode", "aggregate_only" if risk != "high" else "exclude")

                    col1, col2, col3, col4 = st.columns(4)
                    new_allow_stats = col1.checkbox(
                        "📊 本地统计",
                        value=bool(allow_stats),
                        key=f"priv_stats_{col}",
                        help="允许对此变量进行缺失值、唯一值、类型判断等本地统计。",
                    )
                    new_allow_group = col2.checkbox(
                        "🔀 分组变量",
                        value=bool(allow_group),
                        key=f"priv_group_{col}",
                        help="允许将此变量作为分组变量用于交叉分析。",
                    )
                    new_allow_model = col3.checkbox(
                        "📈 进入模型",
                        value=bool(allow_model),
                        key=f"priv_model_{col}",
                        help="允许将此变量纳入相关分析和回归模型。",
                    )
                    new_allow_ai = col4.checkbox(
                        "🤖 发送 AI",
                        value=bool(allow_ai),
                        key=f"priv_ai_{col}",
                        help="允许将此变量的统计结果发送给 AI 模型。",
                    )

                    # AI 发送方式
                    send_options = ["exclude", "aggregate_only", "masked_examples", "full"]
                    send_labels = {
                        "exclude": "不发送（仅本地统计）",
                        "aggregate_only": "仅发送聚合统计",
                        "masked_examples": "发送脱敏样例",
                        "full": "完整发送（需确认）",
                    }
                    current_idx = send_options.index(send_mode) if send_mode in send_options else 1
                    new_send_mode = st.selectbox(
                        "AI 发送方式",
                        send_options,
                        index=current_idx,
                        key=f"priv_sendmode_{col}",
                        format_func=lambda x: send_labels.get(x, x),
                        help="控制此变量的哪些信息可以进入 AI 报告的 payload。",
                    )

                    # 完整发送的二次确认
                    if new_send_mode == "full":
                        st.warning(
                            f"⚠️ **该变量可能包含个人身份信息或敏感内容。**\n\n"
                            f"变量「{cn_name}」被识别为 **{cat_cn}** 类信息。"
                            f"完整发送给 AI 服务商可能存在隐私风险，"
                            f"请确认数据已经脱敏或你有权进行该操作。"
                        )
                        confirm_full = st.checkbox(
                            f"我确认「{cn_name}」的数据已脱敏，允许完整发送给 AI。",
                            key=f"priv_confirm_full_{col}",
                        )
                        if not confirm_full:
                            new_send_mode = send_mode  # 回退到之前的设置
                            st.caption("⚠️ 未确认，将使用之前的发送方式。")

                    # 应用按钮
                    if st.button("💾 应用设置", key=f"priv_apply_{col}"):
                        mask = schema_df["column"] == col
                        schema_df.loc[mask, "allow_local_stats"] = new_allow_stats
                        schema_df.loc[mask, "allow_as_group_variable"] = new_allow_group
                        schema_df.loc[mask, "allow_in_model"] = new_allow_model
                        schema_df.loc[mask, "allow_send_to_ai"] = new_allow_ai
                        schema_df.loc[mask, "send_to_ai_mode"] = new_send_mode
                        schema_df.loc[mask, "user_confirmed_privacy"] = True
                        st.success(f"✅ 变量「{cn_name}」的隐私设置已更新。")
                        st.rerun()

            # 批量操作
            st.markdown("---")
            st.caption("💡 **批量操作提示**：如需将所有变量恢复为系统默认设置，请点击下方按钮。")
            if st.button("🔄 恢复所有隐私设置为默认值", key="priv_reset_all"):
                for col in privacy_vars["column"]:
                    mask = schema_df["column"] == col
                    if "privacy_risk" in schema_df.columns:
                        # 重新调用 schema_infer 的隐私评估来获取默认值
                        series = raw_df[col] if col in raw_df.columns else None
                        vtype = schema_df.loc[mask, "inferred_type"].values[0] if mask.any() else "text"
                        if series is not None:
                            defaults = _assess_privacy_risk(col, series, vtype)
                            schema_df.loc[mask, "allow_local_stats"] = defaults["allow_local_stats"]
                            schema_df.loc[mask, "allow_as_group_variable"] = defaults["allow_as_group_variable"]
                            schema_df.loc[mask, "allow_in_model"] = defaults["allow_in_model"]
                            schema_df.loc[mask, "allow_send_to_ai"] = defaults["allow_send_to_ai"]
                            schema_df.loc[mask, "send_to_ai_mode"] = defaults["send_to_ai_mode"]
                            schema_df.loc[mask, "user_confirmed_privacy"] = False
                st.success("✅ 所有隐私设置已恢复为默认值。")
                st.rerun()

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

        # ---- 生成 Analysis Payload ----
        st.markdown("#### 8. 生成 Analysis Payload")
        st.caption("将统计分析结果打包为结构化 JSON，供 AI 模型使用。不包含原始数据。")

        target = config.get("target_variable", "")

        payload_col1, payload_col2 = st.columns([1, 3])
        with payload_col1:
            gen_payload_btn = st.button(
                "📦 生成 Payload",
                key="gen_payload_btn",
                help="运行分析并打包为 JSON",
            )
        with payload_col2:
            payload_placeholder = st.empty()

        if gen_payload_btn:
            with st.spinner("正在运行完整分析并生成 Payload…"):
                try:
                    # 运行分析
                    _analysis = run_full_analysis(
                        raw_df, schema_df, config, var_dict=generic_var_dict_map,
                    )

                    # 生成图表摘要
                    _dashboard = generate_dashboard_charts(raw_df, schema_df, config)
                    _chart_summaries = _build_chart_summaries(_dashboard)

                    # 确定文件类型
                    _file_type = "csv" if generic_file_name.endswith(".csv") else "xlsx"

                    # 构建 payload
                    _payload = build_analysis_payload(
                        df=raw_df,
                        schema_df=schema_df,
                        config=config,
                        analysis_results=_analysis,
                        quality=quality,
                        chart_summaries=_chart_summaries,
                        selected_sheet=selected_sheet or "",
                        file_type=_file_type,
                    )

                    # 存储到 session_state
                    st.session_state["ai_analysis_payload"] = _payload
                    st.session_state["ai_analysis_results"] = _analysis

                    # 摘要信息（从新 analysis_results 列表统计）
                    _json_str = to_json_payload(_payload)
                    _payload_size = len(_json_str.encode("utf-8"))
                    _warn_count = len(_payload.get("warnings", []))
                    _all_results = _payload.get("analysis_results", [])
                    _uv_count = sum(1 for r in _all_results if r.get("analysis_type") in ("categorical_frequency", "numeric_descriptive", "text_summary"))
                    _bv_groups = sum(1 for r in _all_results if r.get("analysis_type") in ("categorical_categorical_chi_square", "categorical_numeric_group_compare"))
                    _bv_corrs = sum(1 for r in _all_results if r.get("analysis_type") == "numeric_numeric_correlation")
                    _has_mv = any(r.get("analysis_type") == "linear_regression" for r in _all_results)
                    _plan_total = len(_payload.get("analysis_plan", []))
                    _truncated = _payload.get("_truncated", False)

                    payload_placeholder.success(
                        f"✅ Payload 生成完成 · "
                        f"{_plan_total} 项分析计划 · "
                        f"{_uv_count} 个单变量 · "
                        f"{_bv_groups} 组比较 · "
                        f"{_bv_corrs} 对相关 · "
                        f"回归: {'有' if _has_mv else '无'} · "
                        f"{_warn_count} 条警告 · "
                        f"{_payload_size / 1024:.1f} KB"
                        + (" · ⚠️ 已截断" if _truncated else "")
                    )

                except Exception as e:
                    payload_placeholder.error(f"❌ Payload 生成失败：{e}")
                    with st.expander("🔍 错误详情"):
                        st.code(traceback.format_exc())

        # 如果已有 payload，显示预览和下载
        if "ai_analysis_payload" in st.session_state and st.session_state["ai_analysis_payload"]:
            _payload = st.session_state["ai_analysis_payload"]

            with st.expander("📋 Payload 摘要", expanded=False):
                _pw = _payload.get("warnings", [])
                _all_results = _payload.get("analysis_results", [])
                _reg = next((r for r in _all_results if r.get("analysis_type") == "linear_regression"), None)
                _reg_r2 = (_reg.get("result") or {}).get("r_squared", "N/A") if _reg else "N/A"
                _plan = _payload.get("analysis_plan", [])
                _plan_completed = sum(1 for p in _plan if p.get("status") == "completed")
                _plan_skipped = sum(1 for p in _plan if p.get("status") == "skipped")

                st.markdown(f"""
                | 项目 | 值 |
                |------|-----|
                | 报告标题 | {_payload.get('project_meta', {}).get('report_title', '')} |
                | 样本量 | {_payload.get('data_overview', {}).get('row_count', '')} |
                | 变量数 | {_payload.get('data_overview', {}).get('column_count', '')} |
                | 目标变量 | {_payload.get('user_analysis_config', {}).get('target_variable', '')} |
                | 分组变量 | {', '.join(_payload.get('user_analysis_config', {}).get('group_variables', []))} |
                | 解释变量 | {', '.join(_payload.get('user_analysis_config', {}).get('explanatory_variables', []))} |
                | 排除的 ID 变量 | {', '.join(_payload.get('user_analysis_config', {}).get('excluded_id_variables', []))} |
                | 排除的文本变量 | {', '.join(_payload.get('user_analysis_config', {}).get('excluded_text_variables', []))} |
                | 排除的敏感变量 | {', '.join(_payload.get('user_analysis_config', {}).get('excluded_sensitive_variables', []))} |
                | 分析计划 | {len(_plan)} 项（{_plan_completed} 完成 / {_plan_skipped} 跳过） |
                | 分析结果 | {len(_all_results)} 条 |
                | R² | {_reg_r2} |
                | 警告数 | {len(_pw)} |
                """)

                if _pw:
                    st.markdown("**⚠️ 警告列表：**")
                    for w in _pw[:10]:
                        st.caption(f"· {w}")

            with st.expander("🔍 查看完整 JSON", expanded=False):
                _json_str = to_json_payload(_payload)
                st.code(_json_str[:50000], language="json")
                if len(_json_str) > 50000:
                    st.caption(f"… JSON 过大（{len(_json_str):,} 字符），仅显示前 50,000 字符。")

            # 下载按钮
            _json_full = to_json_payload(_payload)
            safe_title = config.get("report_title", "payload").replace(" ", "_")
            st.download_button(
                "📥 下载 analysis_payload.json",
                data=_json_full,
                file_name=f"analysis_payload_{safe_title}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json",
                key="dl_payload",
            )

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

        # ---- 生成报告 ----
        st.markdown("#### 9. 生成 AI 报告")

        target = config.get("target_variable", "")
        has_payload = "ai_analysis_payload" in st.session_state
        has_analysis = "ai_analysis_results" in st.session_state

        # ── 生成前检查 ──
        precheck_ok = True
        precheck_msgs = []

        if not resolved_api_key:
            precheck_msgs.append("❌ 未配置 API Key。请在上方「2. API Key」中填写。\n\n" + get_no_api_key_short_message())
            precheck_ok = False
        if not selected_model:
            precheck_msgs.append("❌ 未选择模型（见上方「3. 模型选择」）。")
            precheck_ok = False
        if not has_payload and not has_analysis:
            precheck_msgs.append("💡 建议先在「8. 生成 Analysis Payload」中生成分析结果。也可直接点击下方按钮（将自动运行分析）。")
        if not target:
            precheck_msgs.append("💡 未指定核心结果变量（target_variable），将生成探索性分析报告。")
        if report_structure == "学术论文式报告":
            # 检查 payload 中是否有回归和显著性结果
            if has_payload:
                _pre_payload = st.session_state["ai_analysis_payload"]
                _pre_has_reg = any(
                    r.get("analysis_type") == "linear_regression"
                    for r in _pre_payload.get("analysis_results", [])
                )
                _pre_has_sig = any(
                    r.get("p_value") is not None
                    for r in _pre_payload.get("analysis_results", [])
                )
                if not _pre_has_reg or not _pre_has_sig:
                    precheck_msgs.append(
                        "💡 当前数据仍可生成论文式分析报告，但实证结果部分将以已有描述统计和探索性分析为主。"
                    )
        if literature_config.get("enabled") and not is_structure_supports_literature(report_structure):
            precheck_msgs.append(
                "💡 已启用文献综述检索，但仅在「学术论文式报告」结构下生效。"
                "请将报告结构切换为「学术论文式报告」以启用文献综述。"
            )
        if literature_config.get("enabled") and not literature_config.get("keywords", "").strip():
            precheck_msgs.append(
                "💡 已启用文献综述检索但未输入研究关键词，将跳过文献检索。"
            )

        if not precheck_ok:
            for msg in precheck_msgs:
                if msg.startswith("❌"):
                    st.error(msg)
                elif msg.startswith("💡"):
                    st.info(msg)
        else:
            for msg in precheck_msgs:
                st.info(msg)

            # ── 生成前隐私变量确认 ──
            privacy_summary = summarize_ai_variable_privacy(schema_df)
            privacy_msg = get_ai_privacy_summary_message(privacy_summary)
            if privacy_summary.get("has_high_risk_sent"):
                st.warning(privacy_msg)
            else:
                st.success(privacy_msg)

            if st.button("🤖 生成 AI 分析报告", type="primary", key="gen_ai_report_btn"):
                with st.spinner("正在生成 AI 分析报告…"):
                    if has_analysis:
                        analysis_results = st.session_state["ai_analysis_results"]
                    else:
                        analysis_results = run_full_analysis(
                            raw_df, schema_df, config, var_dict=generic_var_dict_map,
                        )

                    ai_llm_cfg = build_llm_config_from_ui(
                        provider_config=provider_config,
                        api_key=resolved_api_key,
                        model=selected_model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        provider_key=provider_key,
                        chat_path=st.session_state.get("custom_chat_path", "/chat/completions") if provider_key == "custom_openai" else "/chat/completions",
                    )
                    ai_rpt_cfg = build_report_config_from_ui(
                        report_structure=report_structure,
                        report_style=report_style,
                        report_length=report_length,
                        html_theme=html_theme,
                        literature_enabled=literature_config.get("enabled", False) if literature_config else False,
                        literature_keywords=literature_config.get("keywords", "") if literature_config else "",
                        literature_max_sources=literature_config.get("max_sources", 15) if literature_config else 15,
                        literature_year_range=literature_config.get("year_range", "不限") if literature_config else "不限",
                        background_enabled=background_config.get("enabled", False) if background_config else False,
                        background_source_path=background_config.get("source_path", "") if background_config else "",
                    )
                    ai_result = run_report_generation_from_ui(
                        df=raw_df,
                        schema_df=schema_df,
                        config=config,
                        analysis_results=analysis_results,
                        quality=quality,
                        llm_config=ai_llm_cfg,
                        report_config=ai_rpt_cfg,
                    )

                if ai_result.get("success"):
                    # 显示生成警告（如有）
                    ai_warnings = ai_result.get("warnings", [])
                    if ai_warnings:
                        with st.expander(f"⚠️ 生成提示（{len(ai_warnings)} 条）", expanded=False):
                            for w in ai_warnings:
                                st.caption(f"· {w}")

                    st.success(
                        f"✅ AI 报告生成完成！"
                        f"（模型: {selected_model}，"
                        f"Token: {ai_result.get('llm_response', {}).get('usage', {}).get('total_tokens', 'N/A')}）"
                    )

                    # Markdown 报告预览
                    with st.expander("📝 AI 报告（Markdown）", expanded=True):
                        st.markdown(ai_result["markdown_report"])

                    # HTML 预览（使用所选主题）
                    with st.expander(f"🌐 HTML 报告预览（主题：{html_theme}）", expanded=False):
                        if ai_result.get("html_report"):
                            st.components.v1.html(
                                ai_result["html_report"],
                                height=800,
                                scrolling=True,
                            )

                    # 下载按钮
                    safe_title = config.get("report_title", "AI报告").replace(" ", "_")
                    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M")

                    dl1, dl2, dl3 = st.columns(3)
                    with dl1:
                        st.download_button(
                            "📥 下载 Markdown",
                            data=ai_result["markdown_report"],
                            file_name=f"AI_{safe_title}_{ts}.md",
                            mime="text/markdown",
                        )
                    with dl2:
                        if ai_result.get("html_report"):
                            st.download_button(
                                "📥 下载 HTML",
                                data=ai_result["html_report"],
                                file_name=f"AI_{safe_title}_{ts}.html",
                                mime="text/html",
                            )
                    with dl3:
                        if ai_result.get("docx_report"):
                            st.download_button(
                                "📥 下载 DOCX",
                                data=ai_result["docx_report"],
                                file_name=f"AI_{safe_title}_{ts}.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            )
                else:
                    raw_error = ai_result.get('error', '未知错误')
                    friendly_err = get_ai_report_error_message(raw_error)
                    st.error(friendly_err)
                    # 显示 LLM 原始错误（折叠）
                    llm_resp = ai_result.get("llm_response")
                    with st.expander("🔍 技术详情（调试信息）", expanded=False):
                        if llm_resp and not llm_resp.get("success"):
                            st.text(
                                f"Provider: {llm_resp.get('provider')}\n"
                                f"Model: {llm_resp.get('model')}\n"
                                f"Error: {llm_resp.get('error')}"
                            )
                        else:
                            st.text(f"Raw error: {raw_error}")

        # ---- 使用说明 ----
        with st.expander("📖 使用说明", expanded=False):
            st.markdown("""
            **AI 自动报告工作原理：**
            1. 系统使用 pandas/scipy/statsmodels 完成所有统计计算
            2. 统计结果被打包为结构化 JSON（不包含原始数据）
            3. JSON 随系统提示词发送给所选大语言模型
            4. 大语言模型基于统计结果撰写分析报告
            5. 系统将 Markdown 报告转换为 HTML/DOCX 格式

            **AI 的角色：** AI 仅负责解释统计结果、总结发现、生成报告文字。
            所有数值均为程序计算，AI 不直接进行任何数学计算。

            **注意事项：**
            - AI 生成内容可能存在误差，建议人工审阅
            - 报告中的结论应结合领域知识进行判断
            - 相关关系不等于因果关系
            """)

        # ---- outputs 安全提示 ----
        with st.expander("🔒 数据安全与 outputs/ 目录说明", expanded=False):
            st.markdown(get_outputs_safety_hint())
