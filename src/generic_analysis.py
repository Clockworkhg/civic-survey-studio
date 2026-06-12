"""通用统计分析模块 —— 根据变量类型自动执行适配的分析。

支持：
  1. 单变量分析：数值/分类/有序
  2. 双变量分析：cat×cat / cat×num / num×num
  3. 多变量分析：OLS 回归 / 逻辑回归（预留）

所有函数均包含异常处理，不适合分析时返回友好错误信息而非抛出异常。
统计措辞遵循"关联≠因果"原则。
"""

import pandas as pd
import numpy as np
from scipy import stats as sp_stats
from typing import Optional, Dict, List, Any, Tuple

# 复用现有分析模块的核心函数
from src.analysis import (
    describe_numeric,
    frequency_table,
    cross_analysis_full,
    correlation_with_pvalues,
    ols_regression,
    logit_regression,
    _get_cn_label,
    _significance_stars,
)
from src.utils import parse_value_description


# ================================================================
# 单变量分析
# ================================================================

def univariate_numeric(
    df: pd.DataFrame,
    col: str,
    cn_name: str = "",
) -> Dict[str, Any]:
    """数值变量的单变量分析。

    Returns:
        {
            "变量": str, "中文名": str, "样本量": int, "均值": float,
            "标准差": float, "中位数": float, "最小值": float,
            "最大值": float, "Q25": float, "Q75": float,
            "偏度": float, "峰度": float,
        }
    """
    display = cn_name or col

    try:
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(series) < 3:
            return {"error": f"「{display}」的有效样本量不足（n={len(series)}），无法进行描述统计。"}

        return {
            "变量": col,
            "中文名": cn_name,
            "样本量": len(series),
            "均值": round(series.mean(), 2),
            "标准差": round(series.std(), 2),
            "中位数": round(series.median(), 2),
            "最小值": round(series.min(), 2),
            "最大值": round(series.max(), 2),
            "Q25": round(series.quantile(0.25), 2),
            "Q75": round(series.quantile(0.75), 2),
            "偏度": round(float(series.skew()), 3),
            "峰度": round(float(series.kurtosis()), 3),
        }
    except Exception as e:
        return {"error": f"分析「{display}」时出错：{e}"}


def univariate_categorical(
    df: pd.DataFrame,
    col: str,
    cn_name: str = "",
    label_map: Optional[Dict[int, str]] = None,
) -> Dict[str, Any]:
    """分类变量的单变量分析（频数分布）。

    Returns:
        {
            "变量": str, "中文名": str, "有效样本": int, "缺失数": int,
            "类别数": int, "频数表": DataFrame, "众数": str, "众数占比": float,
        }
    """
    display = cn_name or col

    try:
        freq = frequency_table(df, col, label_mapping=label_map)
        if freq.empty:
            return {"error": f"「{display}」的频数表为空。"}

        non_missing = freq[freq["标签"] != "缺失"]
        valid_n = int(non_missing["频次"].sum()) if len(non_missing) > 0 else 0
        missing_n = int(freq[freq["标签"] == "缺失"]["频次"].sum()) if "缺失" in freq["标签"].values else 0

        mode_label = ""
        mode_pct = 0.0
        if len(non_missing) > 0:
            top_row = non_missing.iloc[0]
            mode_label = str(top_row["标签"])
            mode_pct = float(top_row["百分比(%)"])

        return {
            "变量": col,
            "中文名": cn_name,
            "有效样本": valid_n,
            "缺失数": missing_n,
            "类别数": len(non_missing),
            "频数表": freq,
            "众数": mode_label,
            "众数占比": mode_pct,
        }
    except Exception as e:
        return {"error": f"分析「{display}」时出错：{e}"}


def univariate_ordinal(
    df: pd.DataFrame,
    col: str,
    cn_name: str = "",
    label_map: Optional[Dict[int, str]] = None,
) -> Dict[str, Any]:
    """有序分类变量的单变量分析（频数 + 均值 + 中位数）。

    Returns:
        与 categorical 相同，额外包含 "均值" 和 "中位数"。
    """
    display = cn_name or col

    try:
        cat_result = univariate_categorical(df, col, cn_name, label_map)
        if "error" in cat_result:
            return cat_result

        series = pd.to_numeric(df[col], errors="coerce").dropna()
        # 如果无法转为数值（如中文文本编码），从频数表位置计算序数均值
        if len(series) == 0 or series.isna().all():
            freq = cat_result.get("频数表")
            if freq is not None and len(freq) > 0:
                non_missing = freq[freq["标签"] != "缺失"]
                if len(non_missing) > 0:
                    # 用频数表中各行的位置作为序数值计算加权均值
                    total_freq = 0
                    weighted_sum = 0
                    for i, (_, row) in enumerate(non_missing.iterrows()):
                        pos_val = i + 1  # 位置序数
                        cnt = int(row["频次"])
                        total_freq += cnt
                        weighted_sum += pos_val * cnt
                    if total_freq > 0:
                        cat_result["均值"] = round(weighted_sum / total_freq, 2)
                        # 中位数：通过累计频次找中间位置
                        cum = 0
                        median_pos = None
                        for i, (_, row) in enumerate(non_missing.iterrows()):
                            cum += int(row["频次"])
                            if cum >= total_freq / 2:
                                median_pos = i + 1
                                break
                        cat_result["中位数"] = median_pos
                        cat_result["note"] = "均值基于序数位置计算（非原始数值）。"
                    return cat_result
            cat_result["均值"] = None
            cat_result["中位数"] = None
        else:
            cat_result["均值"] = round(series.mean(), 2) if len(series) > 0 else None
            cat_result["中位数"] = round(series.median(), 2) if len(series) > 0 else None

        return cat_result
    except Exception as e:
        return {"error": f"分析「{display}」时出错：{e}"}


# ================================================================
# 双变量分析
# ================================================================

def bivariate_cat_cat(
    df: pd.DataFrame,
    row_col: str,
    col_col: str,
    cn_row: str = "",
    cn_col: str = "",
    var_dict: Optional[Dict] = None,
) -> Dict[str, Any]:
    """两个分类变量的交叉分析（交叉表 + 卡方检验）。

    Args:
        df: 数据框
        row_col: 行变量（分组变量）
        col_col: 列变量（结果变量）
        cn_row: 行变量中文名
        cn_col: 列变量中文名
        var_dict: 变量字典（用于获取标签）

    Returns:
        与 cross_analysis_full 相同结构的字典
    """
    display_row = cn_row or row_col
    display_col = cn_col or col_col

    try:
        result = cross_analysis_full(df, row_col, col_col, var_dict)
        return result
    except Exception as e:
        return {"error": f"「{display_row}」×「{display_col}」交叉分析失败：{e}"}


def bivariate_cat_num(
    df: pd.DataFrame,
    cat_col: str,
    num_col: str,
    cn_cat: str = "",
    cn_num: str = "",
) -> Dict[str, Any]:
    """分类变量 × 数值变量的分组比较分析。

    包含：分组均值表、单因素方差分析（ANOVA）或 t 检验。

    Returns:
        {
            "cat_col": str, "num_col": str, "cn_cat": str, "cn_num": str,
            "group_stats": DataFrame,  # 各组的 n/均值/标准差
            "test_type": "ANOVA" | "t-test",
            "f_statistic": float | None,
            "p_value": float,
            "significant": bool,
            "interpretation": str,
        }
    """
    display_cat = cn_cat or cat_col
    display_num = cn_num or num_col

    try:
        # 清理数据
        clean = df[[cat_col, num_col]].copy()
        clean[num_col] = pd.to_numeric(clean[num_col], errors="coerce")
        clean = clean.dropna()

        if len(clean) < 10:
            return {"error": f"「{display_cat}」×「{display_num}」的有效样本量不足。"}

        groups = clean.groupby(cat_col)[num_col]
        group_stats = groups.agg(["count", "mean", "std"]).round(2)
        group_stats.columns = ["样本量", "均值", "标准差"]
        group_stats.index.name = display_cat

        # 获取各组数据
        group_data = [g[num_col].values for _, g in clean.groupby(cat_col)]
        n_groups = len(group_data)

        if n_groups < 2:
            return {"error": f"「{display_cat}」分组数不足（{n_groups}），无法进行组间比较。"}

        if n_groups == 2:
            # t 检验
            t_stat, p_val = sp_stats.ttest_ind(group_data[0], group_data[1])
            test_type = "独立样本 t 检验"
            f_stat = None
        else:
            # 单因素 ANOVA
            f_stat, p_val = sp_stats.f_oneway(*group_data)
            test_type = "单因素方差分析（ANOVA）"

        significant = p_val < 0.05

        # 构建解释
        if significant:
            interpretation = (
                f"{test_type}结果显示，不同 **{display_cat}** 在 **{display_num}** 上"
                f"存在统计显著的差异（p = {p_val:.4f} < 0.05）。"
            )
        else:
            interpretation = (
                f"{test_type}结果显示，在当前样本下，"
                f"不同 **{display_cat}** 在 **{display_num}** 上"
                f"未发现统计显著的差异（p = {p_val:.4f} ≥ 0.05）。"
            )

        return {
            "cat_col": cat_col,
            "num_col": num_col,
            "cn_cat": display_cat,
            "cn_num": display_num,
            "group_stats": group_stats,
            "test_type": test_type,
            "f_statistic": round(float(f_stat), 3) if f_stat is not None else None,
            "p_value": round(float(p_val), 4),
            "significant": significant,
            "interpretation": interpretation,
        }
    except Exception as e:
        return {"error": f"「{display_cat}」×「{display_num}」分析失败：{e}"}


def bivariate_num_num(
    df: pd.DataFrame,
    col1: str,
    col2: str,
    cn1: str = "",
    cn2: str = "",
) -> Dict[str, Any]:
    """两个数值变量的相关分析（Pearson + Spearman）。

    Returns:
        {
            "col1": str, "col2": str, "cn1": str, "cn2": str,
            "pearson_r": float, "pearson_p": float,
            "spearman_rho": float, "spearman_p": float,
            "n": int,
            "significant": bool,
            "interpretation": str,
        }
    """
    display1 = cn1 or col1
    display2 = cn2 or col2

    try:
        a = pd.to_numeric(df[col1], errors="coerce")
        b = pd.to_numeric(df[col2], errors="coerce")
        mask = a.notna() & b.notna()
        a_clean = a[mask]
        b_clean = b[mask]
        n = len(a_clean)

        if n < 10:
            return {"error": f"「{display1}」与「{display2}」的有效样本量不足（n={n}）。"}

        # Pearson
        r, rp = sp_stats.pearsonr(a_clean, b_clean)
        # Spearman
        rho, rhop = sp_stats.spearmanr(a_clean, b_clean)

        significant = rp < 0.05

        # 构建解释
        abs_r = abs(r)
        if abs_r < 0.2:
            strength = "极弱"
        elif abs_r < 0.4:
            strength = "弱"
        elif abs_r < 0.6:
            strength = "中等"
        elif abs_r < 0.8:
            strength = "强"
        else:
            strength = "极强"

        direction = "正相关" if r > 0 else "负相关"

        if significant:
            interpretation = (
                f"**{display1}** 与 **{display2}** 之间存在统计显著的{direction}"
                f"（Pearson r = {r:.3f}, p = {rp:.4f} < 0.05），"
                f"关联强度为「{strength}」。"
                f"Spearman 秩相关系数 ρ = {rho:.3f}（p = {rhop:.4f}）。"
            )
        else:
            interpretation = (
                f"**{display1}** 与 **{display2}** 之间未发现统计显著的线性关联"
                f"（Pearson r = {r:.3f}, p = {rp:.4f} ≥ 0.05）。"
            )

        interpretation += "\n\n注意：相关关系不等于因果关系。"

        return {
            "col1": col1,
            "col2": col2,
            "cn1": display1,
            "cn2": display2,
            "pearson_r": round(r, 3),
            "pearson_p": round(rp, 4),
            "spearman_rho": round(rho, 3),
            "spearman_p": round(rhop, 4),
            "n": n,
            "significant": significant,
            "interpretation": interpretation,
        }
    except Exception as e:
        return {"error": f"「{display1}」与「{display2}」相关分析失败：{e}"}


# ================================================================
# 多变量分析
# ================================================================

def multivariate_regression(
    df: pd.DataFrame,
    target: str,
    predictors: List[str],
    var_dict: Optional[Dict] = None,
    cn_target: str = "",
) -> Dict[str, Any]:
    """多元线性回归分析（OLS）。

    封装 src.analysis.ols_regression，增加参数校验和友好错误处理。

    Args:
        df: 数据框
        target: 因变量（数值型）
        predictors: 自变量列表（数值型）
        var_dict: 变量字典
        cn_target: 因变量中文名

    Returns:
        与 ols_regression 相同结构，额外包含 "warning" 提示
    """
    if not predictors:
        return {"error": "未指定自变量。请在分析配置中选择至少一个解释变量。"}

    if target not in df.columns:
        return {"error": f"数据中不存在目标变量「{cn_target or target}」。"}

    # 过滤掉不在数据中的自变量
    valid_predictors = [p for p in predictors if p in df.columns]
    skipped = [p for p in predictors if p not in df.columns]

    if len(valid_predictors) < 1:
        return {"error": "所有指定的自变量均不在数据中。"}

    result = ols_regression(df, target, valid_predictors, var_dict)

    if "error" not in result and skipped:
        result["warning"] = f"跳过了 {len(skipped)} 个不存在的变量：{', '.join(skipped)}"

    return result


def _execute_logistic_regression(
    df: pd.DataFrame,
    target: str,
    predictors: List[str],
    var_dict: Optional[Dict] = None,
    cn_target: str = "",
) -> Dict[str, Any]:
    """二元逻辑回归分析。

    封装 src.analysis.logit_regression，增加参数校验和友好错误处理。

    Args:
        df: 数据框
        target: 二分类因变量
        predictors: 自变量列表（数值型）
        var_dict: 变量字典
        cn_target: 因变量中文名

    Returns:
        与 logit_regression 相同结构，额外包含 "warning" 提示
    """
    if not predictors:
        return {"error": "未指定自变量。请在分析配置中选择至少一个解释变量。"}

    if target not in df.columns:
        return {"error": f"数据中不存在目标变量「{cn_target or target}」。"}

    valid_predictors = [p for p in predictors if p in df.columns]
    skipped = [p for p in predictors if p not in df.columns]

    if len(valid_predictors) < 1:
        return {"error": "所有指定的自变量均不在数据中。"}

    result = logit_regression(df, target, valid_predictors, var_dict)

    if "error" not in result and skipped:
        result["warning"] = f"跳过了 {len(skipped)} 个不存在的变量：{', '.join(skipped)}"

    return result


# ================================================================
# 分析编排器
# ================================================================

def run_full_analysis(
    df: pd.DataFrame,
    schema_df: pd.DataFrame,
    config: Dict[str, Any],
    var_dict: Optional[Dict] = None,
) -> Dict[str, Any]:
    """根据配置自动运行全套分析。

    Args:
        df: 原始数据
        schema_df: 变量类型推断结果（infer_variable_schema 的输出）
        config: 分析配置字典，包含：
            - target_variable: 核心结果变量名
            - group_variables: 分组变量名列表
            - explanatory_variables: 解释变量名列表
        var_dict: 可选变量字典

    Returns:
        {
            "univariate": {col: result, ...},
            "bivariate_group": {f"{cat}__{target}": result, ...},
            "bivariate_corr": {f"{col1}__{col2}": result, ...},
            "multivariate": result or None,
            "warnings": [...],
        }
    """
    results = {
        "univariate": {},
        "bivariate_group": {},
        "bivariate_corr": {},
        "multivariate": None,
        "warnings": [],
    }

    # 构建类型查找表
    type_map = {}
    cn_map = {}
    for _, row in schema_df.iterrows():
        col = row["column"]
        type_map[col] = row["inferred_type"]
        cn_map[col] = row.get("display_name", "") or col

    target = config.get("target_variable", "")
    group_vars = config.get("group_variables", []) or []
    expl_vars = config.get("explanatory_variables", []) or []

    target_type = type_map.get(target, "")
    target_cn = cn_map.get(target, target)

    # ---- 单变量分析 ----
    analyzable_types = {"numeric", "categorical", "ordinal"}
    for col in df.columns:
        vtype = type_map.get(col, "")
        cn = cn_map.get(col, col)

        if vtype == "numeric":
            results["univariate"][col] = univariate_numeric(df, col, cn)
        elif vtype == "categorical":
            labels = var_dict.get(col, {}).get("labels", {}) if var_dict else {}
            results["univariate"][col] = univariate_categorical(df, col, cn, labels)
        elif vtype == "ordinal":
            labels = var_dict.get(col, {}).get("labels", {}) if var_dict else {}
            results["univariate"][col] = univariate_ordinal(df, col, cn, labels)
        else:
            results["univariate"][col] = {
                "变量": col, "中文名": cn, "类型": vtype,
                "info": f"变量类型为「{vtype}」，跳过单变量分析。"
            }

    # ---- 双变量分析：分组变量 × 目标变量 ----
    if target and group_vars:
        for gv in group_vars:
            if gv not in df.columns:
                results["warnings"].append(f"分组变量「{gv}」不在数据中，已跳过。")
                continue
            gv_type = type_map.get(gv, "")
            gv_cn = cn_map.get(gv, gv)

            key = f"{gv}__{target}"

            if gv_type in ("categorical", "ordinal") and target_type in ("categorical", "ordinal"):
                results["bivariate_group"][key] = bivariate_cat_cat(
                    df, gv, target, gv_cn, target_cn, var_dict
                )
            elif gv_type in ("categorical", "ordinal") and target_type in ("numeric", "ordinal"):
                results["bivariate_group"][key] = bivariate_cat_num(
                    df, gv, target, gv_cn, target_cn
                )
            else:
                results["bivariate_group"][key] = {
                    "info": f"「{gv_cn}」（{gv_type}）与「{target_cn}」（{target_type}）的组合暂不支持自动分析。"
                }

    # ---- 双变量分析：解释变量之间的相关 ----
    # 如果配置中指定了 correlation_var_group，优先使用；否则从 expl_vars 推导
    corr_vars = config.get("correlation_var_group")
    if corr_vars:
        numeric_vars = [v for v in corr_vars if type_map.get(v) in ("numeric", "ordinal") and v in df.columns]
    else:
        numeric_vars = [v for v in expl_vars if type_map.get(v) in ("numeric", "ordinal") and v in df.columns]
    if len(numeric_vars) >= 2:
        for i, v1 in enumerate(numeric_vars):
            for v2 in numeric_vars[i + 1:]:
                key = f"{v1}__{v2}"
                results["bivariate_corr"][key] = bivariate_num_num(
                    df, v1, v2, cn_map.get(v1, v1), cn_map.get(v2, v2)
                )

    # 解释变量与目标变量的相关
    if target and target_type in ("numeric", "ordinal") and numeric_vars:
        for ev in numeric_vars:
            if ev == target:
                continue
            key = f"{ev}__{target}"
            if key not in results["bivariate_corr"]:
                results["bivariate_corr"][key] = bivariate_num_num(
                    df, ev, target, cn_map.get(ev, ev), target_cn
                )

    # ---- 多变量分析 ----
    if target and expl_vars:
        if target_type in ("numeric", "ordinal"):
            # 连续/有序目标 → OLS 线性回归
            # 如果配置中指定了 regression_independent_vars，优先使用；否则从 expl_vars 推导
            reg_vars = config.get("regression_independent_vars")
            if reg_vars:
                valid_predictors = [
                    v for v in reg_vars
                    if v in df.columns and type_map.get(v) in ("numeric", "ordinal")
                ]
            else:
                valid_predictors = [
                    v for v in expl_vars
                    if v in df.columns and type_map.get(v) in ("numeric", "ordinal")
                ]
            if len(valid_predictors) >= 2:
                results["multivariate"] = multivariate_regression(
                    df, target, valid_predictors, var_dict, target_cn
                )
            elif len(valid_predictors) == 1:
                results["warnings"].append("解释变量不足（至少需要 2 个数值型变量），跳过回归分析。")
        elif target_type in ("binary",):
            # 二分类目标 → 逻辑回归
            unique_n = df[target].dropna().nunique()
            if unique_n == 2:
                valid_predictors = [
                    v for v in expl_vars
                    if v in df.columns and type_map.get(v) in ("numeric", "ordinal")
                ]
                if len(valid_predictors) >= 1:
                    results["multivariate"] = _execute_logistic_regression(
                        df, target, valid_predictors, var_dict, target_cn
                    )
                else:
                    results["warnings"].append(
                        f"「{target_cn}」为二分类变量，适合逻辑回归但"
                        "解释变量不足（需至少 1 个数值型或有序变量）。"
                    )
            else:
                results["warnings"].append(
                    f"「{target_cn}」类型为 binary 但有 {unique_n} 个唯一值（预期 2 个），"
                    "已跳过逻辑回归。"
                )
        elif target_type == "categorical":
            # 多分类目标 → 不适合 OLS 或二元逻辑回归
            unique_n = df[target].dropna().nunique()
            if unique_n == 2:
                results["warnings"].append(
                    f"「{target_cn}」为二分类变量（{unique_n} 个取值），"
                    "更适合逻辑回归分析；当前版本可先进行频数分析、交叉分析和卡方检验。"
                )
            else:
                results["warnings"].append(
                    f"「{target_cn}」为分类变量（{unique_n} 个取值），"
                    "不适合普通线性回归；建议使用频数分析和卡方检验考察组间差异。"
                )

    return results


# ================================================================
# 辅助：获取分析摘要
# ================================================================

def get_analysis_summary(analysis_results: Dict[str, Any]) -> List[str]:
    """从分析结果中提取关键发现的摘要文本列表。

    可用于报告的主要发现章节。
    """
    findings = []

    # 从双变量分组分析中提取显著差异
    for key, result in analysis_results.get("bivariate_group", {}).items():
        if isinstance(result, dict) and result.get("significant"):
            findings.append(result.get("interpretation", ""))

    # 从双变量相关分析中提取显著相关
    for key, result in analysis_results.get("bivariate_corr", {}).items():
        if isinstance(result, dict) and result.get("significant"):
            findings.append(result.get("interpretation", ""))

    # 从回归中提取显著变量
    multi = analysis_results.get("multivariate", {})
    if isinstance(multi, dict) and "coefficients" in multi:
        coef_df = multi["coefficients"]
        sig_vars = coef_df[coef_df["显著性"].str.contains(r"\*", na=False)]
        if len(sig_vars) > 0:
            r2 = multi.get("adj_r_squared", 0)
            findings.append(
                f"回归分析显示（调整 R² = {r2:.3f}），以下变量具有统计显著的独立贡献："
                + "、".join(
                    v.split("（")[1].rstrip("）") if "（" in v else v
                    for v in sig_vars["变量"] if "截距" not in str(v)
                )
                + "。"
            )

    # 排序：优先显著的结果
    return findings[:5]  # 最多 5 条
