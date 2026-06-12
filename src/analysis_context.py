"""统一分析上下文对象。

示例模式和通用模式共享同一个 AnalysisContext，消除模式割裂。

数据流:
  load data → AnalysisContext → variable schema → config
  → analysis_results → analysis_payload → AI report

所有分析阶段均在 context 上操作，避免散乱变量传递。
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

    # ── 变量说明表（可选） ──
    variable_dict_df: Optional[pd.DataFrame] = None
    variable_dict_map: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # variable_dict_map: {col: {"中文含义": str, "类型": str, "取值或说明": str, "变量用途": str, "labels": dict}}

    # ── 变量识别 ──
    variable_schema: Optional[pd.DataFrame] = None
    type_map: Dict[str, str] = field(default_factory=dict)
    cn_map: Dict[str, str] = field(default_factory=dict)

    # ── 隐私设置 ──
    privacy_settings: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # ── 数据质量 ──
    quality: Dict[str, Any] = field(default_factory=dict)

    # ── 预设分析方案（仅示例模式或用户选择 profile 时） ──
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

    # ── 统计结果 ──
    analysis_results: Dict[str, Any] = field(default_factory=dict)
    chart_summaries: List[Dict[str, Any]] = field(default_factory=list)

    # ── Payload ──
    analysis_payload: Optional[Dict[str, Any]] = None
    table_understanding_payload: Optional[Dict[str, Any]] = None

    # ── AI 分析方案 ──
    analysis_blueprint: Optional[Dict[str, Any]] = None

    # ── 预设方案推荐的图表配置 ──
    recommended_charts: Optional[List[Dict[str, Any]]] = None

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

    def apply_preset_profile(self, profile: Dict[str, Any]) -> None:
        """加载预设分析方案。

        Args:
            profile: 来自 preset_profiles 的 profile 字典
        """
        self.preset_profile = profile
        self.preset_profile_key = profile.get("profile_key", "")

        cfg = self.user_analysis_config
        cfg["report_title"] = profile.get("report_title", cfg["report_title"])
        cfg["research_subject"] = profile.get("research_subject", cfg["research_subject"])
        cfg["target_variable"] = profile.get("target_variable", cfg["target_variable"])
        cfg["group_variables"] = profile.get("group_variables", []) or []
        cfg["explanatory_variables"] = profile.get("explanatory_variables", []) or []
        # 扩展字段 — 用于驱动通用分析管道的领域特定配置
        if profile.get("correlation_var_group"):
            cfg["correlation_var_group"] = profile["correlation_var_group"]
        if profile.get("regression_independent_vars"):
            cfg["regression_independent_vars"] = profile["regression_independent_vars"]
        if profile.get("cross_analysis_pairs"):
            cfg["cross_analysis_pairs"] = profile["cross_analysis_pairs"]
        if profile.get("recommended_report_structure"):
            cfg["report_structure"] = profile["recommended_report_structure"]
        if profile.get("recommended_report_style"):
            cfg["report_style"] = profile["recommended_report_style"]
        if profile.get("recommended_charts"):
            self.recommended_charts = profile["recommended_charts"]

    def apply_blueprint(self, blueprint: Dict[str, Any], overwrite: bool = False) -> List[str]:
        """将 AI 推荐的 analysis_blueprint 应用到用户配置。

        Args:
            blueprint: AI 生成的 analysis_blueprint
            overwrite: 是否覆盖用户已修改的内容

        Returns:
            提示消息列表
        """
        messages: List[str] = []
        cfg = self.user_analysis_config

        # ── 报告标题 ──
        titles = blueprint.get("recommended_report_titles", [])
        # 判断是否为默认标题：空值、"数据分析报告"、"问卷数据分析报告"
        _default_titles = {"数据分析报告", "问卷数据分析报告", ""}
        if titles and (overwrite or cfg.get("report_title", "") in _default_titles):
            cfg["report_title"] = titles[0]
            messages.append(f"报告标题已设为：{titles[0]}")

        # ── 研究对象 ──
        ds_understanding = blueprint.get("dataset_understanding", {})
        subject = ds_understanding.get("possible_research_subject", "")
        if subject and (overwrite or not cfg.get("research_subject")):
            cfg["research_subject"] = subject
            messages.append(f"研究对象已设为：{subject}")

        # ── 核心变量 ──
        target_candidates = blueprint.get("target_variable_candidates", [])
        if target_candidates and (overwrite or not cfg.get("target_variable")):
            # 选优先级最高的
            best = _pick_best_candidate(target_candidates, self.columns)
            if best:
                cfg["target_variable"] = best
                messages.append(f"核心结果变量已设为：{self.get_display_name(best)}（{best}）")

        # ── 分组变量 ──
        group_candidates = blueprint.get("group_variable_candidates", [])
        if group_candidates and (overwrite or not cfg.get("group_variables")):
            selected = _pick_candidates(group_candidates, self.columns, max_count=5)
            if selected:
                cfg["group_variables"] = selected
                names = [f"{self.get_display_name(v)}（{v}）" for v in selected]
                messages.append(f"分组变量已设为：{', '.join(names)}")

        # ── 解释变量 ──
        expl_candidates = blueprint.get("explanatory_variable_candidates", [])
        if expl_candidates and (overwrite or not cfg.get("explanatory_variables")):
            selected = _pick_candidates(expl_candidates, self.columns, max_count=10)
            if selected:
                cfg["explanatory_variables"] = selected
                names = [f"{self.get_display_name(v)}（{v}）" for v in selected]
                messages.append(f"解释变量已设为：{', '.join(names)}")

        # ── 报告结构推荐 ──
        struct_rec = blueprint.get("report_structure_recommendation", {})
        rec_struct = struct_rec.get("recommended_structure", "")
        if rec_struct and "report_structure" not in cfg:
            cfg["report_structure"] = rec_struct
            messages.append(f"报告结构推荐：{rec_struct}")

        # ── 保存 blueprint ──
        self.analysis_blueprint = blueprint

        # ── 过滤无效变量 ──
        self._validate_config_variables(messages)

        return messages

    def _validate_config_variables(self, messages: List[str]) -> None:
        """验证配置中的变量是否存在于数据中。"""
        cfg = self.user_analysis_config
        cols = set(self.columns)

        for key, label in [("target_variable", "核心变量"), ("group_variables", "分组变量"), ("explanatory_variables", "解释变量")]:
            val = cfg.get(key, "")
            if key == "target_variable":
                if val and val not in cols:
                    cfg[key] = ""
                    messages.append(f"⚠️ 推荐的{label}「{val}」不存在于数据中，已清除。")
            else:
                vars_list = val or []
                invalid = [v for v in vars_list if v not in cols]
                if invalid:
                    cfg[key] = [v for v in vars_list if v in cols]
                    messages.append(f"⚠️ 推荐的{label}中有 {len(invalid)} 个变量不存在于数据中：{', '.join(invalid)}，已自动过滤。")

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
            "preset_profile_key": self.preset_profile_key,
            "has_variable_dict": self.variable_dict_df is not None,
            "has_schema": self.variable_schema is not None,
            "has_payload": self.has_payload,
            "has_blueprint": self.has_blueprint,
            "has_results": bool(self.analysis_results),
            "quality_summary": {
                k: v for k, v in self.quality.items()
                if k in ("样本量", "变量数", "缺失值总数", "缺失率", "重复行数", "重复率")
            } if self.quality else {},
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            f"AnalysisContext(mode={self.mode}, rows={self.n_rows}, cols={self.n_cols}, "
            f"target={self.target!r}, has_profile={self.has_profile}, "
            f"has_payload={self.has_payload})"
        )


# ================================================================
# 辅助函数
# ================================================================

def _pick_best_candidate(
    candidates: List[Dict[str, Any]],
    available_columns: List[str],
) -> Optional[str]:
    """从候选变量列表中选择优先级最高的有效变量。"""
    # 按 priority 排序: high > medium > low
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
