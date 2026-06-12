"""报告语境构建模块。

提供纯函数，从分析结果和变量模式中构建 LLM 上下文文本。
供 ai_report_generator.py 和 app.py 共同使用。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd


# ================================================================
# 变量摘要
# ================================================================

def build_variable_summary(
    schema_df: pd.DataFrame,
    config: Dict[str, Any],
) -> str:
    """构建关键变量摘要，供文献综述和报告语境使用。

    Args:
        schema_df: 变量类型推断结果
        config: 分析配置（含 target_variable, group_variables, explanatory_variables 等）

    Returns:
        简短的中文变量描述。
    """
    if schema_df is None or schema_df.empty:
        return "变量信息不可用。"

    # ── 一次构建查找字典（O(n) 扫描，O(1) 后续查找）──
    display_map: Dict[str, str] = {}
    type_map: Dict[str, str] = {}
    for _, row in schema_df.iterrows():
        col = str(row.get("column", ""))
        if not col:
            continue
        d = str(row.get("display_name", ""))
        if d and d != "nan":
            display_map[col] = d
        t = str(row.get("inferred_type", ""))
        if t and t != "nan":
            type_map[col] = t

    def _display(col: str) -> str:
        return display_map.get(col, col)

    parts: List[str] = []
    target = config.get("target_variable", "")
    group_vars: list = config.get("group_variables", [])
    expl_vars: list = config.get("explanatory_variables", [])

    if target:
        target_name = _display(target)
        parts.append(f"核心因变量为「{target_name}」")
        # 变量类型描述
        var_type = type_map.get(target, "")
        if "likert" in var_type.lower() or "ordinal" in var_type.lower():
            parts.append("（有序/Likert量表）")
        elif "numeric" in var_type.lower() or "continuous" in var_type.lower():
            parts.append("（连续数值型）")
        elif "categorical" in var_type.lower():
            parts.append("（分类变量）")

    if group_vars:
        names = [_display(v) for v in group_vars[:5]]
        parts.append(f"；分组变量包括「{'」「'.join(names)}」")

    if expl_vars:
        names = [_display(v) for v in expl_vars[:8]]
        parts.append(f"；解释变量包括「{'」「'.join(names)}」")

    return "本调查" + "".join(parts) + "。"


# ================================================================
# 关键发现摘要
# ================================================================

def _fmt_correlation(r: dict) -> Optional[str]:
    coef = r.get("coefficient", r.get("correlation", ""))
    vx = r.get("variable_x", r.get("variable", ""))
    vy = r.get("variable_y", "")
    direction = "正" if (isinstance(coef, (int, float)) and coef > 0) else "负"
    return f"「{vx}」与「{vy}」呈显著{direction}相关（r={coef}, p={round(r['p_value'], 4)}）"


def _fmt_regression(r: dict) -> Optional[str]:
    vy = r.get("variable_y", "")
    coef_table = r.get("coefficients", [])
    for row in coef_table:
        if row.get("p_value", 1.0) < 0.05:
            vn = row.get("variable", row.get("name", ""))
            beta = row.get("coefficient", row.get("beta", ""))
            return f"「{vn}」是「{vy}」的显著预测变量（β={beta}, p={round(row['p_value'], 4)}）"
    return None


def _fmt_group_compare(r: dict) -> Optional[str]:
    vx = r.get("variable_x", r.get("variable", ""))
    at = r.get("analysis_type", "")
    return f"「{vx}」在分组比较中呈现显著差异（{at}, p={round(r['p_value'], 4)}）"


def _fmt_logistic(r: dict) -> Optional[str]:
    """格式化逻辑回归的显著发现（以 OR 为核心解释指标）。"""
    vy = r.get("variable_y", r.get("dependent_variable", ""))
    coef_table = r.get("coefficients", [])
    for row in coef_table:
        if row.get("p_value", 1.0) < 0.05:
            vn = row.get("variable", row.get("name", ""))
            or_val = row.get("odds_ratio", row.get("OR", ""))
            return f"「{vn}」是「{vy}」的显著预测因子（OR={or_val}, p={round(row['p_value'], 4)}）"
    return None


_SIGNIFICANCE_FORMATTERS: Dict[str, Any] = {
    "pearson_correlation": _fmt_correlation,
    "spearman_correlation": _fmt_correlation,
    "linear_regression": _fmt_regression,
    "logistic_regression": _fmt_logistic,
    "chi_square": _fmt_group_compare,
    "anova": _fmt_group_compare,
    "t_test": _fmt_group_compare,
}


def build_key_findings_summary(payload: Dict[str, Any]) -> str:
    """从分析 payload 中提取 1-3 条关键统计发现。

    Args:
        payload: build_analysis_payload 的输出

    Returns:
        简短的统计发现摘要。
    """
    results = payload.get("analysis_results", [])
    if not results:
        return "尚未进行统计分析。"

    findings: List[str] = []

    # 单次遍历：先找显著结果
    for r in results:
        if len(findings) >= 3:
            break
        p_value = r.get("p_value")
        if p_value is None or not isinstance(p_value, (int, float)) or p_value >= 0.05:
            continue

        formatter = _SIGNIFICANCE_FORMATTERS.get(r.get("analysis_type", ""))
        if formatter:
            finding = formatter(r)
            if finding:
                findings.append(finding)

    # 回退：描述统计
    if not findings:
        for r in results:
            label = r.get("label", r.get("analysis_type", ""))
            if label and label != "skipped":
                findings.append(f"已完成{label}分析")
                if len(findings) >= 2:
                    break

    if not findings:
        return "数据分析尚未揭示显著关联。"

    return "初步分析显示：" + "；".join(findings) + "。"
