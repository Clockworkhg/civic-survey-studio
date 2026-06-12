"""分析方案执行器。

将 AI 推荐的 analysis_recipes 转换为程序可执行的统计分析任务。
真正的统计计算由 Python（pandas/scipy/statsmodels）完成，AI 只负责推荐。

使用方式:
  from src.analysis_recipe_runner import run_recipes
  results = run_recipes(context, recipes)
"""

from typing import Any, Dict, List, Optional

import pandas as pd


# ================================================================
# 主入口
# ================================================================

def run_recipes(
    df: pd.DataFrame,
    schema_df: pd.DataFrame,
    recipes: List[Dict[str, Any]],
    type_map: Optional[Dict[str, str]] = None,
    cn_map: Optional[Dict[str, str]] = None,
    var_dict: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """执行 AI 推荐的 analysis_recipes。

    Args:
        df: 原始数据
        schema_df: 变量类型推断结果
        recipes: AI 推荐的 analysis_recipes 列表
        type_map: {col: type} 查找表（可选，自动从 schema_df 构建）
        cn_map: {col: display_name} 查找表（可选）
        var_dict: 变量说明字典（可选）

    Returns:
        {
            "univariate": {col: result, ...},
            "bivariate_group": {key: result, ...},
            "bivariate_corr": {key: result, ...},
            "multivariate": result or None,
            "warnings": [...],
            "executed_recipes": int,
            "skipped_recipes": int,
        }
    """
    if type_map is None:
        type_map = {}
        for _, row in schema_df.iterrows():
            type_map[row["column"]] = row.get("inferred_type", "")

    if cn_map is None:
        cn_map = {}
        for _, row in schema_df.iterrows():
            col = row["column"]
            cn_map[col] = row.get("display_name", "") or col

    results: Dict[str, Any] = {
        "univariate": {},
        "bivariate_group": {},
        "bivariate_corr": {},
        "multivariate": None,
        "warnings": [],
        "executed_recipes": 0,
        "skipped_recipes": 0,
    }

    for recipe in recipes:
        analysis_type = recipe.get("analysis_type", "")
        variables = recipe.get("variables", [])
        recipe_id = recipe.get("recipe_id", "")

        try:
            # ── 执行前检查 ──
            check_msg = _precheck(analysis_type, variables, type_map, df)
            if check_msg:
                results["warnings"].append(f"[{recipe_id}] {check_msg}")
                results["skipped_recipes"] += 1
                continue

            # ── 按类型分发 ──
            result = _execute_recipe(analysis_type, variables, df, type_map, cn_map, var_dict)
            if result is None:
                results["warnings"].append(f"[{recipe_id}] 不支持的 analysis_type: {analysis_type}")
                results["skipped_recipes"] += 1
                continue

            # ── 存储结果 ──
            if analysis_type in ("categorical_frequency", "numeric_descriptive", "ordinal_distribution", "text_summary"):
                col = variables[0] if variables else ""
                results["univariate"][col] = result
            elif analysis_type in ("categorical_categorical_chi_square", "categorical_numeric_group_compare"):
                key = "__".join(variables[:2])
                results["bivariate_group"][key] = result
            elif analysis_type in ("numeric_numeric_correlation",):
                key = "__".join(variables[:2])
                results["bivariate_corr"][key] = result
            elif analysis_type in ("linear_regression", "logistic_regression", "logistic_regression_placeholder"):
                results["multivariate"] = result
            else:
                # 其他类型作为 univariate 处理
                col = variables[0] if variables else ""
                results["univariate"][f"{col}_{analysis_type}"] = result

            results["executed_recipes"] += 1

        except Exception as e:
            results["warnings"].append(f"[{recipe_id}] 执行异常: {e}")
            results["skipped_recipes"] += 1

    return results


# ================================================================
# 预检查
# ================================================================

def _precheck(
    analysis_type: str,
    variables: List[str],
    type_map: Dict[str, str],
    df: pd.DataFrame,
) -> str:
    """执行前检查变量是否存在、类型是否匹配。

    Returns:
        空字符串表示检查通过；否则返回跳过原因。
    """
    if not variables:
        return "未指定变量"

    # 检查变量是否在数据中
    for var in variables:
        if var not in df.columns:
            return f"变量「{var}」不存在于数据中"

    # 类型匹配检查
    var_types = [type_map.get(v, "") for v in variables]

    if analysis_type == "categorical_frequency":
        if var_types[0] not in ("categorical", "ordinal"):
            return f"变量类型「{var_types[0]}」不适合频数分析"
    elif analysis_type == "numeric_descriptive":
        if var_types[0] not in ("numeric", "ordinal"):
            return f"变量类型「{var_types[0]}」不适合描述统计"
    elif analysis_type == "categorical_categorical_chi_square":
        if len(variables) < 2:
            return "卡方检验需要至少 2 个变量"
        if var_types[0] not in ("categorical", "ordinal") or var_types[1] not in ("categorical", "ordinal"):
            return f"变量类型组合「{var_types[0]} × {var_types[1]}」不适合卡方检验"
    elif analysis_type == "categorical_numeric_group_compare":
        if len(variables) < 2:
            return "分组比较需要至少 2 个变量"
        if var_types[0] not in ("categorical", "ordinal") or var_types[1] not in ("numeric", "ordinal"):
            return f"变量类型组合「{var_types[0]} × {var_types[1]}」不适合分组均值比较"
    elif analysis_type == "numeric_numeric_correlation":
        if len(variables) < 2:
            return "相关分析需要至少 2 个变量"
        if var_types[0] not in ("numeric", "ordinal") or var_types[1] not in ("numeric", "ordinal"):
            return f"变量类型组合「{var_types[0]} × {var_types[1]}」不适合相关分析"
    elif analysis_type == "linear_regression":
        if len(variables) < 3:
            return "回归分析需要至少 3 个变量（1 因变量 + 2 自变量）"
        if var_types[0] not in ("numeric", "ordinal"):
            return f"因变量类型「{var_types[0]}」不适合线性回归"

    return ""  # 检查通过


# ================================================================
# 执行分发
# ================================================================

def _execute_recipe(
    analysis_type: str,
    variables: List[str],
    df: pd.DataFrame,
    type_map: Dict[str, str],
    cn_map: Dict[str, str],
    var_dict: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """按 analysis_type 分发到对应的执行函数。"""
    from src.generic_analysis import (
        univariate_numeric,
        univariate_categorical,
        univariate_ordinal,
        bivariate_cat_cat,
        bivariate_cat_num,
        bivariate_num_num,
        multivariate_regression,
        _execute_logistic_regression,
    )

    if analysis_type == "numeric_descriptive":
        return univariate_numeric(df, variables[0], cn_map.get(variables[0], variables[0]))

    elif analysis_type == "categorical_frequency":
        labels = _get_labels(var_dict, variables[0])
        return univariate_categorical(df, variables[0], cn_map.get(variables[0], variables[0]), labels)

    elif analysis_type == "ordinal_distribution":
        labels = _get_labels(var_dict, variables[0])
        return univariate_ordinal(df, variables[0], cn_map.get(variables[0], variables[0]), labels)

    elif analysis_type == "categorical_categorical_chi_square":
        return bivariate_cat_cat(
            df, variables[0], variables[1],
            cn_map.get(variables[0], variables[0]),
            cn_map.get(variables[1], variables[1]),
            var_dict=var_dict,
        )

    elif analysis_type == "categorical_numeric_group_compare":
        return bivariate_cat_num(
            df, variables[0], variables[1],
            cn_map.get(variables[0], variables[0]),
            cn_map.get(variables[1], variables[1]),
        )

    elif analysis_type == "numeric_numeric_correlation":
        return bivariate_num_num(
            df, variables[0], variables[1],
            cn_map.get(variables[0], variables[0]),
            cn_map.get(variables[1], variables[1]),
        )

    elif analysis_type == "linear_regression":
        # variables[0] = dependent, variables[1:] = independent
        return multivariate_regression(
            df, variables[0], variables[1:],
            var_dict=var_dict,
            cn_target=cn_map.get(variables[0], variables[0]),
        )

    elif analysis_type in ("logistic_regression", "logistic_regression_placeholder"):
        return _execute_logistic_regression(
            df, variables[0], variables[1:],
            var_dict=var_dict,
            cn_target=cn_map.get(variables[0], variables[0]),
        )

    elif analysis_type == "derived_index_mean":
        return _execute_derived_index(df, variables, method="mean")

    elif analysis_type == "derived_index_standardized_mean":
        return _execute_derived_index(df, variables, method="standardized_mean")

    elif analysis_type == "text_summary":
        return {
            "info": "文本摘要分析：程序仅提供基本统计（长度、唯一值数），不进行语义分析。",
        }

    return None


# ================================================================
# 派生指标
# ================================================================

def _execute_derived_index(
    df: pd.DataFrame,
    variables: List[str],
    method: str = "mean",
) -> Dict[str, Any]:
    """执行派生指标计算（多个评分变量取均值）。

    Args:
        df: 数据
        variables: 源变量列表
        method: "mean"（简单均值）或 "standardized_mean"（标准化后均值）

    Returns:
        派生指标的计算结果
    """
    valid_vars = [v for v in variables if v in df.columns]
    if len(valid_vars) < 2:
        return {"error": f"派生指标需要至少 2 个有效变量，当前仅有 {len(valid_vars)} 个。"}

    # 提取数值
    data = pd.DataFrame()
    for v in valid_vars:
        data[v] = pd.to_numeric(df[v], errors="coerce")

    if method == "standardized_mean":
        # Z-score 标准化后取均值
        data = (data - data.mean()) / data.std(ddof=0)
        index_name = f"index_{'_'.join(valid_vars)[:40]}_std"
    else:
        index_name = f"index_{'_'.join(valid_vars)[:40]}"

    index_values = data.mean(axis=1, skipnabool=True)

    return {
        "index_name": index_name,
        "source_variables": valid_vars,
        "method": method,
        "count": int(index_values.notna().sum()),
        "mean": round(index_values.mean(), 2) if index_values.notna().any() else None,
        "std": round(index_values.std(), 2) if index_values.notna().any() else None,
        "min": round(index_values.min(), 2) if index_values.notna().any() else None,
        "max": round(index_values.max(), 2) if index_values.notna().any() else None,
        "note": "此为 AI 推荐的派生指标，未经用户确认。" if method != "standardized_mean"
                else "此为 AI 推荐的标准化派生指标。注意：标准化后量纲消除，但原始单位信息丢失。",
    }


# ================================================================
# 辅助
# ================================================================

def _get_labels(var_dict: Optional[Dict[str, Dict[str, Any]]], col: str) -> Dict:
    """从变量说明字典中获取标签映射。"""
    if var_dict is None:
        return {}
    entry = var_dict.get(col, {})
    return entry.get("labels", {}) if isinstance(entry, dict) else {}
