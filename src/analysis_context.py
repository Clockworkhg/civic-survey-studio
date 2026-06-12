"""统一分析上下文对象。

示例模式和通用模式共享同一个 AnalysisContext，消除模式割裂。

数据流:
  load data → AnalysisContext → variable schema → config
  → apply_analysis_config() → invalidate_downstream()
  → run_analysis_pipeline() → analysis_results / dashboard_charts / payload
  → AI report generation

v0.1.0 统一状态流:
  - apply_analysis_config() 是所有配置写入的唯一入口
  - apply_blueprint_to_config() 将 AI blueprint 转为正式配置
  - invalidate_downstream() 标记下游结果失效
  - run_analysis_pipeline() 统一执行所有分析
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass
class AnalysisContext:
    """统一分析上下文 —— 承载从数据加载到报告生成的完整状态。

    示例模式: mode="example", preset_profile 指向 gov_satisfaction_profile
    通用模式: mode="generic", preset_profile=None (可选)
    """

    # ── 基础标识 ──
    mode: str = "generic"  # "example" | "generic"
    dataset_name: str = ""
    data_file_name: str = ""

    # ── 数据 ──
    df: Optional[pd.DataFrame] = None
    sheet_name: str = ""
    file_type: str = ""  # "xlsx" | "csv"

    # ── 变量说明表（可选）──
    variable_dict_df: Optional[pd.DataFrame] = None
    variable_dict_map: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # ── 变量识别 ──
    variable_schema: Optional[pd.DataFrame] = None
    type_map: Dict[str, str] = field(default_factory=dict)
    cn_map: Dict[str, str] = field(default_factory=dict)

    # ── 隐私设置 ──
    privacy_settings: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # ── 数据质量 ──
    quality: Dict[str, Any] = field(default_factory=dict)

    # ── 预设分析方案 ──
    preset_profile: Optional[Dict[str, Any]] = None
    preset_profile_key: str = ""

    # ── 用户分析配置 ──
    user_analysis_config: Dict[str, Any] = field(default_factory=lambda: {
        "report_title": "问卷数据分析报告",
        "research_subject": "",
        "target_variable": "",
        "group_variables": [],
        "explanatory_variables": [],
        "gen_html": True,
        "gen_docx": True,
    })

    # ── v0.1.0: 配置来源追踪 ──
    config_source: str = ""          # "manual" | "ai" | "preset"
    config_applied_at: str = ""      # ISO timestamp of last config application

    # ── v0.1.0: 下游有效性 ──
    downstream_valid: bool = True
    invalidation_reason: str = ""

    # ── 统计结果 ──
    analysis_results: Dict[str, Any] = field(default_factory=dict)
    chart_summaries: List[Dict[str, Any]] = field(default_factory=list)
    dashboard_charts: List[Any] = field(default_factory=list)

    # ── Payload ──
    analysis_payload: Optional[Dict[str, Any]] = None
    table_understanding_payload: Optional[Dict[str, Any]] = None

    # ── AI 分析方案 ──
    analysis_blueprint: Optional[Dict[str, Any]] = None

    # ── 荐图表配置 ──
    recommended_charts: Optional[List[Dict[str, Any]]] = None

    # ── 累积 warning ──
    warnings: List[str] = field(default_factory=list)

    # ── 生成时间 ──
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

    # ── 元数据 ──
    meta: Dict[str, Any] = field(default_factory=dict)

    # ================================================================
    # 便捷属性
    # ================================================================

    @property
    def n_rows(self) -> int:
        if self.df is not None:
            return len(self.df)
        return 0

    @property
    def n_cols(self) -> int:
        if self.df is not None:
            return len(self.df.columns)
        return 0

    @property
    def columns(self) -> List[str]:
        if self.df is not None:
            return list(self.df.columns)
        return []

    @property
    def target(self) -> str:
        return self.user_analysis_config.get("target_variable", "")

    @property
    def group_vars(self) -> List[str]:
        return self.user_analysis_config.get("group_variables", []) or []

    @property
    def expl_vars(self) -> List[str]:
        return self.user_analysis_config.get("explanatory_variables", []) or []

    @property
    def report_title(self) -> str:
        return self.user_analysis_config.get("report_title", "数据分析报告")

    @property
    def research_subject(self) -> str:
        return self.user_analysis_config.get("research_subject", "")

    @property
    def is_example(self) -> bool:
        return self.mode == "example"

    @property
    def is_generic(self) -> bool:
        return self.mode == "generic"

    @property
    def has_profile(self) -> bool:
        return self.preset_profile is not None

    @property
    def has_payload(self) -> bool:
        return self.analysis_payload is not None

    @property
    def has_blueprint(self) -> bool:
        return self.analysis_blueprint is not None

    @property
    def has_results(self) -> bool:
        return bool(self.analysis_results) and self.downstream_valid

    @property
    def config_ready(self) -> bool:
        """配置是否足以运行分析。"""
        return bool(self.target)

    # ================================================================
    # 核心方法
    # ================================================================

    def build_type_maps(self) -> None:
        """从 variable_schema 重建 type_map 和 cn_map。"""
        if self.variable_schema is None:
            self.type_map = {}
            self.cn_map = {}
            return
        for _, row in self.variable_schema.iterrows():
            col = row["column"]
            self.type_map[col] = row.get("inferred_type", "")
            self.cn_map[col] = row.get("display_name", "") or col

    def get_display_name(self, col: str) -> str:
        """获取变量的显示名称（优先中文含义）。"""
        return self.cn_map.get(col, col)

    def get_type(self, col: str) -> str:
        """获取变量的推断类型。"""
        return self.type_map.get(col, "")

    def get_privacy(self, col: str) -> Dict[str, Any]:
        """获取变量的隐私设置。"""
        return self.privacy_settings.get(col, {})

    # ── v0.1.0: 变量标签辅助函数 ──

    def get_variable_label(self, var_name: str) -> str:
        """获取变量的显示标签：中文名（英文列名）。"""
        cn = self.cn_map.get(var_name, "")
        if cn and cn != var_name:
            return f"{cn}（{var_name}）"
        return var_name

    def get_variable_description(self, var_name: str) -> str:
        """获取变量说明文本。"""
        info = self.variable_dict_map.get(var_name, {})
        desc = info.get("变量用途", "") or info.get("取值或说明", "") or ""
        return str(desc) if desc else ""

    # ================================================================
    # v0.1.0: 统一配置写入入口
    # ================================================================

    def apply_analysis_config(
        self,
        config: Dict[str, Any],
        source: str = "manual",
    ) -> List[str]:
        """统一写入当前分析配置。所有配置变更必须通过此入口。

        记录配置来源，检测语义变化并自动标记下游失效。

        Args:
            config: 新配置字典
            source: 来源 — "manual" | "ai" | "preset"

        Returns:
            提示消息列表（成功/警告/错误）
        """
        messages: List[str] = []
        old_cfg = self.user_analysis_config

        # ── 检测语义变化 ──
        changed = False
        changed_fields = []

        for key in ("target_variable", "group_variables", "explanatory_variables"):
            old_val = old_cfg.get(key)
            new_val = config.get(key)

            if key in ("group_variables", "explanatory_variables"):
                old_set = set(old_val or [])
                new_set = set(new_val or [])
                if old_set != new_set:
                    changed = True
                    changed_fields.append(key)
            else:
                if old_val != new_val:
                    changed = True
                    changed_fields.append(key)

        # 摘要字段变化不触发失效
        if config.get("report_title") != old_cfg.get("report_title"):
            messages.append(f"报告标题已更新：{config.get('report_title', '')}")

        # ── 写入配置 ──
        self.user_analysis_config.update(config)

        # ── 记录来源 ──
        self.config_source = source
        self.config_applied_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        source_label = {"manual": "手动配置", "ai": "AI 推荐方案", "preset": "预设方案"}.get(source, source)
        messages.append(f"分析方案已应用（来源：{source_label}）")

        # ── 语义变化 → 标记下游失效 ──
        if changed:
            self.invalidate_downstream(
                f"配置字段已变更：{', '.join(changed_fields)}"
            )
            messages.append(
                "配置已更新，下游分析结果已标记为失效。"
                "请在「统计分析」页面重新执行分析。"
            )

        # ── 验证变量有效性 ──
        self._validate_config_variables(messages)

        # ── 累积 warnings ──
        self.warnings.extend(messages)

        return messages

    # ================================================================
    # v0.1.0: AI blueprint → 正式配置
    # ================================================================

    def apply_blueprint_to_config(
        self,
        blueprint: Dict[str, Any],
        schema_df: Optional[pd.DataFrame] = None,
        overwrite: bool = True,
    ) -> List[str]:
        """将 AI 推荐的 analysis_blueprint 转换为正式 AnalysisConfig。

        区别于旧 apply_blueprint:
          - 使用变量真实列名（从 candidate["variable"] 提取）
          - 验证变量是否存在于数据中
          - 保留变量说明表中的中文名称、用途、取值说明到 config metadata
          - 对不存在的变量产生 warning 而非崩溃

        Args:
            blueprint: AI 生成的 analysis_blueprint
            schema_df: 变量 schema（用于验证列名和获取中文名）
            overwrite: True = 覆盖现有配置；False = 仅填充空字段

        Returns:
            提示消息列表（含 warnings）
        """
        messages: List[str] = []

        # ── 收集变量说明表元数据 ──
        var_metadata: Dict[str, Dict[str, str]] = {}
        if schema_df is not None:
            for _, row in schema_df.iterrows():
                col = str(row.get("column", ""))
                var_metadata[col] = {
                    "display_name": str(row.get("display_name", "") or col),
                    "inferred_type": str(row.get("inferred_type", "")),
                }
        # 补充 variable_dict_map 信息
        for col, info in self.variable_dict_map.items():
            if col in var_metadata:
                var_metadata[col].update({
                    "purpose": str(info.get("变量用途", "")),
                    "value_desc": str(info.get("取值或说明", "")),
                })

        available_cols = set(self.columns)

        # ── 构建新配置 ──
        new_config: Dict[str, Any] = {}

        # 报告标题
        titles = blueprint.get("recommended_report_titles", [])
        _default_titles = {"数据分析报告", "问卷数据分析报告", ""}
        if titles and (overwrite or self.user_analysis_config.get("report_title", "") in _default_titles):
            new_config["report_title"] = titles[0]
            messages.append(f"报告标题已设为：{titles[0]}")

        # 研究对象
        ds = blueprint.get("dataset_understanding", {})
        subject = ds.get("possible_research_subject", "")
        if subject and (overwrite or not self.user_analysis_config.get("research_subject")):
            new_config["research_subject"] = subject
            messages.append(f"研究对象已设为：{subject}")

        # 核心变量 — 从候选列表提取真实列名
        target_candidates = blueprint.get("target_variable_candidates", [])
        if target_candidates and (overwrite or not self.user_analysis_config.get("target_variable")):
            best = _pick_best_candidate(target_candidates, list(available_cols))
            if best:
                new_config["target_variable"] = best
                label = self.get_variable_label(best)
                messages.append(f"核心变量已设为：{label}")
            else:
                messages.append("⚠ AI 推荐的核心变量均不存在于数据中，请手动选择。")

        # 分组变量
        group_candidates = blueprint.get("group_variable_candidates", [])
        if group_candidates and (overwrite or not self.user_analysis_config.get("group_variables")):
            selected = _pick_candidates(group_candidates, list(available_cols), max_count=5)
            if selected:
                skipped = len(group_candidates) - len(selected)
                new_config["group_variables"] = selected
                names = [self.get_variable_label(v) for v in selected]
                messages.append(f"分组变量已设为：{', '.join(names)}")
                if skipped > 0:
                    messages.append(f"⚠ {skipped} 个推荐的分组变量不存在于数据中，已跳过。")
            else:
                messages.append("⚠ AI 推荐的分组变量均不存在于数据中。")

        # 解释变量
        expl_candidates = blueprint.get("explanatory_variable_candidates", [])
        if expl_candidates and (overwrite or not self.user_analysis_config.get("explanatory_variables")):
            selected = _pick_candidates(expl_candidates, list(available_cols), max_count=10)
            if selected:
                skipped = len(expl_candidates) - len(selected)
                new_config["explanatory_variables"] = selected
                names = [self.get_variable_label(v) for v in selected]
                messages.append(f"解释变量已设为：{', '.join(names)}")
                if skipped > 0:
                    messages.append(f"⚠ {skipped} 个推荐的解释变量不存在于数据中，已跳过。")
            else:
                messages.append("⚠ AI 推荐的解释变量均不存在于数据中。")

        # 报告结构推荐
        struct_rec = blueprint.get("report_structure_recommendation", {})
        rec_struct = struct_rec.get("recommended_structure", "")
        if rec_struct and (overwrite or "report_structure" not in self.user_analysis_config):
            new_config["report_structure"] = rec_struct
            messages.append(f"报告结构推荐：{rec_struct}")

        # 报告风格
        rec_style = blueprint.get("recommended_report_style", "")
        if rec_style and overwrite:
            new_config["report_style"] = rec_style

        # 报告长度
        rec_length = blueprint.get("recommended_report_length", "")
        if rec_length and overwrite:
            new_config["report_length"] = rec_length

        # ── 保存 blueprint ──
        self.analysis_blueprint = blueprint

        # ── 保存变量元数据到 config ──
        new_config["_var_metadata"] = var_metadata

        # ── 统一写入 ──
        if new_config:
            apply_msgs = self.apply_analysis_config(new_config, source="ai")
            messages.extend(apply_msgs)

        return messages

    # 保留旧接口兼容性
    def apply_blueprint(self, blueprint: Dict[str, Any], overwrite: bool = False) -> List[str]:
        """旧版 apply_blueprint（兼容）。建议使用 apply_blueprint_to_config。"""
        return self.apply_blueprint_to_config(blueprint, schema_df=None, overwrite=overwrite)

    # ================================================================
    # v0.1.0: 下游失效
    # ================================================================

    def invalidate_downstream(self, reason: str = "") -> None:
        """标记下游分析结果为失效状态。

        当 target/group/predictors 改变后调用。
        清空或标记过期:
          - analysis_results
          - dashboard_charts / chart_summaries
          - analysis_payload
          - generated_report

        Args:
            reason: 失效原因（用于 UI 提示）
        """
        self.downstream_valid = False
        self.invalidation_reason = reason

        # 清空下游结果
        self.analysis_results = {}
        self.chart_summaries = []
        self.dashboard_charts = []
        self.analysis_payload = None

        # 同步 session_state（如果在 Streamlit 环境中）
        try:
            import streamlit as st
            st.session_state["_downstream_valid"] = False
            st.session_state["_invalidation_reason"] = reason
            st.session_state["_analysis_results"] = {}
            st.session_state["_dashboard_charts"] = []
            st.session_state["_analysis_payload"] = None
            st.session_state["_generated_report"] = None
        except Exception:
            pass

    def mark_downstream_valid(self) -> None:
        """标记下游结果为有效。分析成功完成后调用。"""
        self.downstream_valid = True
        self.invalidation_reason = ""
        try:
            import streamlit as st
            st.session_state["_downstream_valid"] = True
            st.session_state["_invalidation_reason"] = ""
        except Exception:
            pass

    # ================================================================
    # v0.1.0: 统一分析管道
    # ================================================================

    def run_analysis_pipeline(self, force: bool = False) -> Dict[str, Any]:
        """统一执行完整分析管道。

        根据当前配置执行:
          1. 单变量分析
          2. 双变量分析
          3. 多变量分析
          4. 图表生成
          5. Payload 打包

        结果写入 self.analysis_results / self.dashboard_charts / self.analysis_payload。

        Args:
            force: True = 强制执行（忽略缓存）；False = 仅在失效时执行

        Returns:
            {
                "success": bool,
                "analysis_results": dict,
                "dashboard_charts": list,
                "payload": dict | None,
                "error": str (if failed),
                "warnings": list[str],
            }
        """
        result: Dict[str, Any] = {
            "success": False,
            "analysis_results": {},
            "dashboard_charts": [],
            "payload": None,
            "error": "",
            "warnings": [],
        }

        # ── 预检查 ──
        if self.df is None or self.variable_schema is None:
            result["error"] = "数据未加载，无法执行分析。"
            return result

        if not self.config_ready:
            result["error"] = (
                "尚未设置核心变量（target_variable）。"
                "请在「分析方案」页面选择核心变量后再执行分析。"
            )
            return result

        if not force and self.downstream_valid and self.analysis_results:
            result["success"] = True
            result["analysis_results"] = self.analysis_results
            result["dashboard_charts"] = self.dashboard_charts
            result["payload"] = self.analysis_payload
            result["warnings"].append("使用缓存的分析结果（配置未更改）。")
            return result

        # ── Step 1: 统计分析 ──
        try:
            from src.generic_analysis import run_full_analysis
            self.analysis_results = run_full_analysis(
                self.df, self.variable_schema, self.user_analysis_config,
                var_dict=self.variable_dict_map,
            )
            result["analysis_results"] = self.analysis_results
        except Exception as e:
            result["error"] = f"统计分析失败: {e}"
            return result

        # ── Step 2: 图表生成 ──
        try:
            from src.generic_charts import generate_dashboard_charts
            self.dashboard_charts = generate_dashboard_charts(
                self.df, self.variable_schema, self.user_analysis_config,
            )
            result["dashboard_charts"] = self.dashboard_charts

            # 生成图表摘要
            self.chart_summaries = _build_chart_summaries(self.dashboard_charts)
        except Exception as e:
            result["warnings"].append(f"图表生成失败（非致命）: {e}")
            self.dashboard_charts = []
            self.chart_summaries = []

        # ── Step 3: Payload 打包 ──
        try:
            from src.analysis_packager import build_analysis_payload
            self.analysis_payload = build_analysis_payload(
                df=self.df,
                schema_df=self.variable_schema,
                config=self.user_analysis_config,
                analysis_results=self.analysis_results,
                quality=self.quality,
                chart_summaries=self.chart_summaries,
                selected_sheet=self.sheet_name or "",
                file_type=self.file_type or "",
            )
            result["payload"] = self.analysis_payload
        except Exception as e:
            result["warnings"].append(f"Payload 打包失败（非致命）: {e}")
            self.analysis_payload = None

        # ── 标记下游有效 ──
        self.mark_downstream_valid()
        result["success"] = True

        # 同步到 session_state
        try:
            import streamlit as st
            st.session_state["_analysis_results"] = self.analysis_results
            st.session_state["_dashboard_charts"] = self.dashboard_charts
            st.session_state["_analysis_payload"] = self.analysis_payload
            st.session_state["_downstream_valid"] = True
        except Exception:
            pass

        return result

    # ================================================================
    # 现有方法（保留兼容）
    # ================================================================

    def _validate_config_variables(self, messages: List[str]) -> None:
        """验证配置中的变量是否存在于数据中。"""
        cfg = self.user_analysis_config
        cols = set(self.columns)

        for key, label in [("target_variable", "核心变量"), ("group_variables", "分组变量"), ("explanatory_variables", "解释变量")]:
            val = cfg.get(key, "")
            if key == "target_variable":
                if val and val not in cols:
                    cfg[key] = ""
                    messages.append(f"⚠ 推荐的{label}「{val}」不存在于数据中，已清除。")
            else:
                vars_list = val or []
                invalid = [v for v in vars_list if v not in cols]
                if invalid:
                    cfg[key] = [v for v in vars_list if v in cols]
                    messages.append(f"⚠ 推荐的{label}中有 {len(invalid)} 个变量不存在于数据中：{', '.join(invalid)}，已自动过滤。")

    def apply_preset_profile(self, profile: Dict[str, Any]) -> None:
        """加载预设分析方案。使用统一的 apply_analysis_config。"""
        self.preset_profile = profile
        self.preset_profile_key = profile.get("profile_key", "")

        cfg_update = {}
        cfg_update["report_title"] = profile.get("report_title", self.user_analysis_config["report_title"])
        cfg_update["research_subject"] = profile.get("research_subject", self.user_analysis_config["research_subject"])
        cfg_update["target_variable"] = profile.get("target_variable", self.user_analysis_config["target_variable"])
        cfg_update["group_variables"] = profile.get("group_variables", []) or []
        cfg_update["explanatory_variables"] = profile.get("explanatory_variables", []) or []

        # 扩展字段
        if profile.get("correlation_var_group"):
            cfg_update["correlation_var_group"] = profile["correlation_var_group"]
        if profile.get("regression_independent_vars"):
            cfg_update["regression_independent_vars"] = profile["regression_independent_vars"]
        if profile.get("cross_analysis_pairs"):
            cfg_update["cross_analysis_pairs"] = profile["cross_analysis_pairs"]
        if profile.get("recommended_report_structure"):
            cfg_update["report_structure"] = profile["recommended_report_structure"]
        if profile.get("recommended_report_style"):
            cfg_update["report_style"] = profile["recommended_report_style"]
        if profile.get("recommended_charts"):
            self.recommended_charts = profile["recommended_charts"]

        self.apply_analysis_config(cfg_update, source="preset")

    def to_dict(self) -> Dict[str, Any]:
        """导出为可序列化的字典摘要（不含 DataFrame）。"""
        return {
            "mode": self.mode,
            "dataset_name": self.dataset_name,
            "data_file_name": self.data_file_name,
            "sheet_name": self.sheet_name,
            "file_type": self.file_type,
            "n_rows": self.n_rows,
            "n_cols": self.n_cols,
            "columns": self.columns,
            "user_analysis_config": self.user_analysis_config,
            "config_source": self.config_source,
            "config_applied_at": self.config_applied_at,
            "downstream_valid": self.downstream_valid,
            "preset_profile_key": self.preset_profile_key,
            "has_variable_dict": self.variable_dict_df is not None,
            "has_schema": self.variable_schema is not None,
            "has_payload": self.has_payload,
            "has_blueprint": self.has_blueprint,
            "has_results": bool(self.analysis_results) and self.downstream_valid,
            "warnings": self.warnings[-20:] if self.warnings else [],
            "quality_summary": {
                k: v for k, v in self.quality.items()
                if k in ("样本量", "变量数", "缺失值总数", "缺失率", "重复行数", "重复率")
            } if self.quality else {},
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        valid_str = "valid" if self.downstream_valid else "stale"
        return (
            f"AnalysisContext(mode={self.mode}, rows={self.n_rows}, cols={self.n_cols}, "
            f"target={self.target!r}, source={self.config_source or 'none'}, "
            f"downstream={valid_str}, has_payload={self.has_payload})"
        )


# ================================================================
# 辅助函数
# ================================================================

def _pick_best_candidate(
    candidates: List[Dict[str, Any]],
    available_columns: List[str],
) -> Optional[str]:
    """从候选变量列表中选择优先级最高的有效变量。"""
    priority_order = {"high": 0, "medium": 1, "low": 2}
    sorted_candidates = sorted(
        candidates,
        key=lambda c: priority_order.get(c.get("priority", "low"), 2),
    )
    for c in sorted_candidates:
        var = c.get("variable", "")
        if var in available_columns:
            return var
    return None


def _pick_candidates(
    candidates: List[Dict[str, Any]],
    available_columns: List[str],
    max_count: int = 5,
) -> List[str]:
    """从候选变量列表中选择有效的变量（按优先级排序，限制数量）。"""
    priority_order = {"high": 0, "medium": 1, "low": 2}
    sorted_candidates = sorted(
        candidates,
        key=lambda c: priority_order.get(c.get("priority", "low"), 2),
    )
    selected = []
    for c in sorted_candidates:
        var = c.get("variable", "")
        if var in available_columns and var not in selected:
            selected.append(var)
            if len(selected) >= max_count:
                break
    return selected


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

        try:
            if hasattr(fig, "data") and fig.data:
                first_trace = fig.data[0]
                trace_type = getattr(first_trace, "type", "")
                summary["type"] = trace_type or "chart"

                if hasattr(first_trace, "x") and hasattr(first_trace, "y"):
                    y_vals = list(first_trace.y) if first_trace.y is not None else []
                    if y_vals:
                        clean_y = [v for v in y_vals if v is not None]
                        if clean_y:
                            x_vals = list(first_trace.x) if first_trace.x is not None else []
                            max_idx = clean_y.index(max(clean_y))
                            min_idx = clean_y.index(min(clean_y))
                            if max_idx < len(x_vals):
                                summary["max_category"] = str(x_vals[max_idx])[:60]
                            if min_idx < len(x_vals):
                                summary["min_category"] = str(x_vals[min_idx])[:60]
        except Exception:
            pass

        summaries.append(summary)

    return summaries
