"""统计分析模块 —— 描述统计、频数分析、交叉分析、相关分析。

所有统计计算均基于原始数值编码数据。
"""

import pandas as pd
import numpy as np
from scipy import stats as sp_stats
from typing import Optional, Dict, List


# ================================================================
# 数值变量描述统计
# ================================================================

def describe_numeric(df: pd.DataFrame, col: str) -> dict:
    """对单个数值列做描述统计。

    Returns:
        包含 变量、样本量、均值、标准差、最小值、最大值、中位数 的字典
    """
    series = pd.to_numeric(df[col], errors="coerce").dropna()
    desc = series.describe()
    return {
        "变量": col,
        "样本量": int(desc.get("count", 0)),
        "均值": round(desc.get("mean", 0), 2),
        "标准差": round(desc.get("std", 0), 2),
        "最小值": round(desc.get("min", 0), 2),
        "最大值": round(desc.get("max", 0), 2),
        "中位数": round(desc.get("50%", 0), 2),
    }


def describe_numeric_batch(
    df: pd.DataFrame,
    var_list: List[str],
    var_dict: Optional[Dict] = None,
) -> pd.DataFrame:
    """批量对多个数值变量输出描述统计，合并为一张表。

    Args:
        df: 原始调查数据
        var_list: 需要描述的变量名列表
        var_dict: 变量字典（用于获取中文含义作为别名）

    Returns:
        包含所有变量描述统计的 DataFrame（每行一个变量）
    """
    rows = []
    for col in var_list:
        if col not in df.columns:
            continue
        row = describe_numeric(df, col)
        # 如果提供了 var_dict，用中文含义替换变量名
        if var_dict and col in var_dict:
            cn = var_dict[col].get("中文含义", "")
            row["变量"] = f"{col}（{cn}）" if cn else col
        rows.append(row)

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows)
    # 按指定顺序排列列
    col_order = ["变量", "样本量", "均值", "标准差", "最小值", "最大值", "中位数"]
    result = result[[c for c in col_order if c in result.columns]]
    return result


# ================================================================
# 分类变量频数分析
# ================================================================

def frequency_table(
    df: pd.DataFrame,
    col: str,
    label_mapping: Optional[dict] = None,
) -> pd.DataFrame:
    """生成单个变量的频数分布表。

    Args:
        df: 数据框
        col: 列名
        label_mapping: 值→标签映射字典

    Returns:
        包含 值、标签、频次、百分比、有效百分比、累计百分比 的 DataFrame
    """
    series = df[col].copy()
    series_num = pd.to_numeric(series, errors="coerce")
    # 检测是否为数值编码（至少一半非空值可转为数值）
    valid_ratio = series_num.notna().sum() / max(series.notna().sum(), 1)
    is_numeric_coded = valid_ratio >= 0.5
    counts = series_num.value_counts(dropna=False).sort_index()

    # 如果数据不是数值编码（如已经是中文文本），直接用原始值计数
    if not is_numeric_coded:
        raw_counts = series.value_counts(dropna=False)
        # 按频次降序（与数值编码的按值排序不同）
        counts = raw_counts.sort_values(ascending=False)

    total = int(counts.sum())
    # 有效样本量（排除 NaN）
    if np.nan in counts.index:
        valid_mask = counts.index.notna()
        valid_total = int(counts[valid_mask].sum())
    else:
        valid_total = total

    rows = []
    cum_pct = 0.0
    for val, cnt in counts.items():
        if pd.isna(val):
            label = "缺失"
            val_display = "—"
        else:
            if is_numeric_coded:
                label = (
                    label_mapping.get(int(val), str(val))
                    if label_mapping
                    else str(int(val))
                )
                val_display = int(val) if val == int(val) else val
            else:
                # 非数值编码，直接使用原始值作为标签
                label = str(val)
                val_display = str(val)

        pct = cnt / total * 100 if total > 0 else 0.0
        if pd.isna(val):
            valid_pct_display = "—"
        else:
            valid_pct = cnt / valid_total * 100 if valid_total > 0 else 0.0
            valid_pct_display = round(valid_pct, 2)  # type: ignore
            cum_pct += valid_pct

        rows.append({
            "编码值": val_display,
            "标签": label,
            "频次": int(cnt),
            "百分比(%)": round(pct, 2),
            "有效百分比(%)": valid_pct_display,
            "累计百分比(%)": round(cum_pct, 2) if not pd.isna(val) else "—",
        })

    result = pd.DataFrame(rows)

    # 将"缺失"行移至末尾
    if "缺失" in result["标签"].values:
        result = pd.concat([
            result[result["标签"] != "缺失"],
            result[result["标签"] == "缺失"],
        ]).reset_index(drop=True)

    return result


def frequency_batch(
    df: pd.DataFrame,
    var_list: List[str],
    var_dict: Optional[Dict] = None,
) -> Dict[str, pd.DataFrame]:
    """批量生成多个变量的频数分布表。

    Args:
        df: 原始调查数据
        var_list: 需要分析的变量名列表
        var_dict: 变量字典（用于获取标签映射）

    Returns:
        {变量名: 频数表 DataFrame} 字典，不存在的变量会被跳过
    """
    results = {}
    for col in var_list:
        if col not in df.columns:
            continue

        label_map = None
        if var_dict and col in var_dict:
            label_map = var_dict[col].get("labels", {})

        try:
            freq_df = frequency_table(df, col, label_mapping=label_map)
            results[col] = freq_df
        except Exception:
            continue

    return results


def frequency_summary(
    df: pd.DataFrame,
    var_list: List[str],
    var_dict: Optional[Dict] = None,
) -> pd.DataFrame:
    """生成频数分布的摘要表（每个变量一行，展示众数及其占比）。

    Args:
        df: 原始调查数据
        var_list: 变量名列表
        var_dict: 变量字典

    Returns:
        摘要 DataFrame，列：变量、有效样本、众数标签、占比(%)、缺失数
    """
    rows = []
    for col in var_list:
        if col not in df.columns:
            continue

        label_map = None
        if var_dict and col in var_dict:
            label_map = var_dict[col].get("labels", {})

        freq_df = frequency_table(df, col, label_mapping=label_map)
        non_missing = freq_df[freq_df["标签"] != "缺失"]

        top_row = non_missing.iloc[0] if len(non_missing) > 0 else None
        missing_count = (
            freq_df[freq_df["标签"] == "缺失"]["频次"].sum()
            if "缺失" in freq_df["标签"].values else 0
        )
        valid_n = int(non_missing["频次"].sum())

        # 变量显示名
        var_label = col
        if var_dict and col in var_dict:
            cn = var_dict[col].get("中文含义", "")
            var_label = f"{col}（{cn}）" if cn else col

        rows.append({
            "变量": var_label,
            "有效样本": valid_n,
            "众数标签": top_row["标签"] if top_row is not None else "—",
            "众数频次": int(top_row["频次"]) if top_row is not None else 0,
            "众数占比(%)": top_row["百分比(%)"] if top_row is not None else "—",
            "缺失数": int(missing_count),
        })

    return pd.DataFrame(rows)


# ================================================================
# 交叉分析
# ================================================================

# 预设交叉分析对
CROSS_ANALYSIS_PAIRS: List[tuple] = [
    ("district", "satisfaction_level"),
    ("channel", "satisfaction_level"),
    ("age_group", "satisfaction_level"),
    ("education", "satisfaction_level"),
    ("gender", "satisfaction_level"),
    ("visit_frequency", "satisfaction_level"),
    ("service_type", "satisfaction_level"),
]


def cross_tabulation(
    df: pd.DataFrame,
    row_col: str,
    col_col: str,
    row_labels: Optional[dict] = None,
    col_labels: Optional[dict] = None,
) -> pd.DataFrame:
    """生成交叉分析表（频次）。

    Args:
        df: 数据框
        row_col: 行变量名
        col_col: 列变量名
        row_labels: 行变量值标签映射
        col_labels: 列变量值标签映射

    Returns:
        交叉表 DataFrame（含合计行列）
    """
    r_num = pd.to_numeric(df[row_col], errors="coerce")
    c_num = pd.to_numeric(df[col_col], errors="coerce")
    r_is_num = r_num.notna().sum() / max(len(df), 1) >= 0.5
    c_is_num = c_num.notna().sum() / max(len(df), 1) >= 0.5
    ctab = pd.crosstab(
        r_num if r_is_num else df[row_col],
        c_num if c_is_num else df[col_col],
        margins=True,
        margins_name="合计",
    )

    if row_labels:
        ctab.index = [
            row_labels.get(i, str(i)) if i != "合计" else "合计"
            for i in ctab.index
        ]
    if col_labels:
        ctab.columns = [
            col_labels.get(c, str(c)) if c != "合计" else "合计"
            for c in ctab.columns
        ]
    return ctab


def cross_tabulation_pct(
    df: pd.DataFrame,
    row_col: str,
    col_col: str,
    row_labels: Optional[dict] = None,
    col_labels: Optional[dict] = None,
    pct_direction: str = "row",
) -> pd.DataFrame:
    """生成百分比交叉表。

    Args:
        df: 数据框
        row_col: 行变量名
        col_col: 列变量名
        row_labels: 行变量值标签映射
        col_labels: 列变量值标签映射
        pct_direction: "row"=行百分比, "col"=列百分比

    Returns:
        百分比表 DataFrame（含合计行列），数值为百分比字符串
    """
    # 构建数值交叉表
    r_num = pd.to_numeric(df[row_col], errors="coerce")
    c_num = pd.to_numeric(df[col_col], errors="coerce")
    r_is_num = r_num.notna().sum() / max(len(df), 1) >= 0.5
    c_is_num = c_num.notna().sum() / max(len(df), 1) >= 0.5
    ctab_raw = pd.crosstab(
        r_num if r_is_num else df[row_col],
        c_num if c_is_num else df[col_col],
    )

    if pct_direction == "row":
        pct = ctab_raw.div(ctab_raw.sum(axis=1), axis=0) * 100
    else:
        pct = ctab_raw.div(ctab_raw.sum(axis=0), axis=1) * 100

    # 添加合计列/行
    pct["合计"] = ctab_raw.sum(axis=1)
    pct.loc["合计"] = ctab_raw.sum(axis=0).tolist() + [ctab_raw.sum().sum()]

    pct = pct.round(1)

    # 应用标签
    if row_labels:
        pct.index = [
            row_labels.get(i, str(i)) if i != "合计" else "合计"
            for i in pct.index
        ]
    if col_labels:
        pct.columns = [
            col_labels.get(c, str(c)) if c != "合计" else "合计"
            for c in pct.columns
        ]

    return pct


def chi_square_test(
    df: pd.DataFrame, col_a: str, col_b: str
) -> dict:
    """对两个分类变量执行卡方检验。

    Returns:
        {"chi2": 卡方值, "p_value": p值, "dof": 自由度, "n": 样本量,
         "significant": bool}
        或 {"error": str} 如果检验无法执行
    """
    clean = df[[col_a, col_b]].dropna()
    # 检测是否为数值编码
    a_num = pd.to_numeric(clean[col_a], errors="coerce")
    b_num = pd.to_numeric(clean[col_b], errors="coerce")
    a_is_num = a_num.notna().sum() / max(len(clean), 1) >= 0.5
    b_is_num = b_num.notna().sum() / max(len(clean), 1) >= 0.5
    use_a = a_num if a_is_num else clean[col_a]
    use_b = b_num if b_is_num else clean[col_b]
    ctab = pd.crosstab(use_a, use_b)
    if ctab.empty or ctab.shape[0] < 2 or ctab.shape[1] < 2:
        return {"error": "交叉表维度不足，无法进行卡方检验"}

    chi2, p, dof, expected = sp_stats.chi2_contingency(ctab)
    return {
        "chi2": round(chi2, 3),
        "p_value": round(p, 4),
        "dof": dof,
        "n": len(clean),
        "significant": p < 0.05,
    }


def cross_analysis_full(
    df: pd.DataFrame,
    row_col: str,
    col_col: str,
    var_dict: Optional[Dict] = None,
    pct_direction: str = "row",
) -> Dict:
    """对两个分类变量进行完整的交叉分析。

    一次调用返回：
      - 频次交叉表
      - 百分比表（默认行百分比）
      - 卡方检验结果
      - 中文解释文本
      - 变量中文名称

    Args:
        df: 原始调查数据
        row_col: 行变量名（分组变量）
        col_col: 列变量名（结果变量）
        var_dict: 变量字典
        pct_direction: 百分比方向 "row" 或 "col"

    Returns:
        {
            "crosstab": 频次交叉表,
            "pct_table": 百分比表,
            "chi2": 卡方值,
            "p_value": p值,
            "dof": 自由度,
            "n": 有效样本量,
            "significant": bool,
            "interpretation": 中文解释,
            "row_var_cn": 行变量中文名,
            "col_var_cn": 列变量中文名,
            "row_col": 行变量原始名,
            "col_col": 列变量原始名,
        }
        失败时返回 {"error": str}
    """
    if row_col not in df.columns:
        return {"error": f"数据中不存在变量「{row_col}」"}
    if col_col not in df.columns:
        return {"error": f"数据中不存在变量「{col_col}」"}

    # 获取标签
    row_labels = None
    col_labels = None
    if var_dict:
        row_labels = var_dict.get(row_col, {}).get("labels", {}) or None
        col_labels = var_dict.get(col_col, {}).get("labels", {}) or None

    row_cn = _get_cn_label(var_dict, row_col)
    col_cn = _get_cn_label(var_dict, col_col)

    # 频次交叉表
    try:
        ctab = cross_tabulation(df, row_col, col_col, row_labels, col_labels)
    except Exception as e:
        return {"error": f"生成交叉表失败：{e}"}

    # 百分比表
    try:
        pct_table = cross_tabulation_pct(df, row_col, col_col, row_labels, col_labels, pct_direction)
    except Exception as e:
        return {"error": f"生成百分比表失败：{e}"}

    # 卡方检验
    chi_result = chi_square_test(df, row_col, col_col)
    if "error" in chi_result:
        return {"error": chi_result["error"]}

    # 生成解释
    interpretation = _build_interpretation(
        chi2=chi_result["chi2"],
        p_value=chi_result["p_value"],
        dof=chi_result["dof"],
        n=chi_result["n"],
        significant=chi_result["significant"],
        row_cn=row_cn,
        col_cn=col_cn,
    )

    return {
        "crosstab": ctab,
        "pct_table": pct_table,
        "chi2": chi_result["chi2"],
        "p_value": chi_result["p_value"],
        "dof": chi_result["dof"],
        "n": chi_result["n"],
        "significant": chi_result["significant"],
        "interpretation": interpretation,
        "row_var_cn": row_cn,
        "col_var_cn": col_cn,
        "row_col": row_col,
        "col_col": col_col,
    }


def cross_analysis_batch(
    df: pd.DataFrame,
    pairs: List[tuple],
    var_dict: Optional[Dict] = None,
) -> List[Dict]:
    """批量执行预设交叉分析对。

    Args:
        df: 原始数据
        pairs: [(row_col, col_col), ...] 列表
        var_dict: 变量字典

    Returns:
        每个 pair 的 cross_analysis_full 结果列表（跳过不存在的变量对）
    """
    results = []
    for row_col, col_col in pairs:
        result = cross_analysis_full(df, row_col, col_col, var_dict)
        if "error" not in result:
            results.append(result)
    return results


# ================================================================
# 内部辅助
# ================================================================

def _get_cn_label(var_dict: Optional[Dict], col: str) -> str:
    """获取变量的中文含义，无则返回原始列名。"""
    if var_dict and col in var_dict:
        cn = var_dict[col].get("中文含义", "")
        return cn if cn else col
    return col


def _build_interpretation(
    chi2: float,
    p_value: float,
    dof: int,
    n: int,
    significant: bool,
    row_cn: str,
    col_cn: str,
) -> str:
    """构建卡方检验的中文解释文本。

    措辞规范：
      - 只用"关联""差异"，不用"导致""必然"
    """
    if significant:
        return (
            f"卡方检验结果显示，**{row_cn}** 与 **{col_cn}** 之间存在"
            f"统计显著的关联（χ² = {chi2}, df = {dof}, p = {p_value} < 0.05）。\n\n"
            f"这表明不同 **{row_cn}** 在 **{col_cn}** 上的分布存在差异，"
            f"该差异在统计学意义上显著。"
        )
    else:
        return (
            f"卡方检验结果显示，在当前样本（n = {n}）下，"
            f"**{row_cn}** 与 **{col_cn}** 之间未发现统计显著的关联"
            f"（χ² = {chi2}, df = {dof}, p = {p_value} ≥ 0.05）。\n\n"
            f"目前的数据不足以推断不同 **{row_cn}** 在 **{col_cn}** 上的分布存在差异。"
        )


# ================================================================
# 相关分析
# ================================================================

def correlation_matrix(
    df: pd.DataFrame,
    cols: list,
    var_dict: Optional[Dict] = None,
) -> pd.DataFrame:
    """计算数值列的 Pearson 相关系数矩阵。

    Args:
        df: 数据框
        cols: 数值列名列表
        var_dict: 变量字典（用中文含义标注行列名）

    Returns:
        Pearson 相关系数矩阵 DataFrame
    """
    numeric_df = df[cols].apply(lambda s: pd.to_numeric(s, errors="coerce"))
    numeric_df = numeric_df.dropna(axis=0, how="any")
    corr = numeric_df.corr(method="pearson").round(3)

    # 用中文含义重命名行列
    if var_dict:
        rename_map = {}
        for c in corr.columns:
            if c in var_dict:
                cn = var_dict[c].get("中文含义", "")
                rename_map[c] = f"{c}\n{cn}" if cn else c
        corr = corr.rename(index=rename_map, columns=rename_map)

    return corr


def correlation_with_pvalues(
    df: pd.DataFrame,
    cols: List[str],
    var_dict: Optional[Dict] = None,
) -> Dict[str, pd.DataFrame]:
    """计算 Pearson 相关系数矩阵及对应的 p 值矩阵。

    对每对变量调用 scipy.stats.pearsonr，返回 r 和 p。

    Args:
        df: 数据框
        cols: 数值列名列表
        var_dict: 变量字典

    Returns:
        {
            "r_matrix": 相关系数矩阵 DataFrame,
            "p_matrix": p 值矩阵 DataFrame,
            "n": 有效样本量（成对删除后）,
        }
    """
    n_vars = len(cols)
    r_mat = pd.DataFrame(np.eye(n_vars), index=cols, columns=cols)
    p_mat = pd.DataFrame(np.zeros((n_vars, n_vars)), index=cols, columns=cols)
    n_mat = pd.DataFrame(np.zeros((n_vars, n_vars), dtype=int), index=cols, columns=cols)

    for i, col_a in enumerate(cols):
        for j, col_b in enumerate(cols):
            if i == j:
                r_mat.iloc[i, j] = 1.0
                p_mat.iloc[i, j] = 0.0
                continue
            if i > j:
                # 对称矩阵，只算一次
                r_mat.iloc[i, j] = r_mat.iloc[j, i]
                p_mat.iloc[i, j] = p_mat.iloc[j, i]
                continue

            a = pd.to_numeric(df[col_a], errors="coerce")
            b = pd.to_numeric(df[col_b], errors="coerce")
            mask = a.notna() & b.notna()
            a_clean = a[mask]
            b_clean = b[mask]

            if len(a_clean) < 3:
                r_mat.iloc[i, j] = np.nan
                p_mat.iloc[i, j] = np.nan
            else:
                r, p_val = sp_stats.pearsonr(a_clean, b_clean)
                r_mat.iloc[i, j] = round(r, 3)
                p_mat.iloc[i, j] = round(p_val, 4)

    # 应用中文标签
    if var_dict:
        rename_map = {}
        for c in cols:
            cn = var_dict.get(c, {}).get("中文含义", "")
            rename_map[c] = f"{c}（{cn}）" if cn and cn != c else c
        r_mat = r_mat.rename(index=rename_map, columns=rename_map)
        p_mat = p_mat.rename(index=rename_map, columns=rename_map)

    return {"r_matrix": r_mat, "p_matrix": p_mat}


# ================================================================
# 回归分析
# ================================================================

def ols_regression(
    df: pd.DataFrame,
    dependent_var: str,
    independent_vars: List[str],
    var_dict: Optional[Dict] = None,
) -> Dict:
    """执行 OLS 多元线性回归分析。

    使用 statsmodels 进行回归，自动输出完整的回归结果表和解释文本。

    Args:
        df: 原始数据
        dependent_var: 因变量名
        independent_vars: 自变量名列表
        var_dict: 变量字典

    Returns:
        {
            "coefficients": 回归系数表 DataFrame,
            "r_squared": R²,
            "adj_r_squared": 调整 R²,
            "f_statistic": F 统计量,
            "f_pvalue": F 检验 p 值,
            "n": 有效样本量,
            "interpretation": 中文解释文本,
            "dependent_cn": 因变量中文名,
            "condition_number": 条件数,
        }
        失败时返回 {"error": str}
    """
    try:
        import statsmodels.api as sm
    except ImportError:
        return {"error": "缺少 statsmodels 库，请执行 pip install statsmodels"}

    if dependent_var not in df.columns:
        return {"error": f"数据中不存在因变量「{dependent_var}」"}

    missing_ind = [v for v in independent_vars if v not in df.columns]
    if missing_ind:
        return {"error": f"数据中不存在自变量：{', '.join(missing_ind)}"}

    # 提取有效样本
    all_vars = [dependent_var] + independent_vars
    clean = df[all_vars].copy()
    for v in all_vars:
        clean[v] = pd.to_numeric(clean[v], errors="coerce")
    clean = clean.dropna()
    n = len(clean)

    if n < len(independent_vars) + 5:
        return {"error": f"有效样本量不足（n={n}，需至少 {len(independent_vars) + 5}）。"}

    # 构造 X, y
    y = clean[dependent_var]
    X = clean[independent_vars]
    X = sm.add_constant(X)

    try:
        model = sm.OLS(y, X).fit()
    except Exception as e:
        return {"error": f"回归模型拟合失败：{e}"}

    # 整理系数表
    coef_rows = []
    for var_name in model.params.index:
        cn = _get_cn_label(var_dict, var_name) if var_name != "const" else "截距"
        coef_rows.append({
            "变量": cn if var_name == "const" else f"{var_name}（{cn}）" if cn != var_name else var_name,
            "回归系数": round(model.params[var_name], 4),
            "标准误": round(model.bse[var_name], 4),
            "t 值": round(model.tvalues[var_name], 3),
            "p 值": round(model.pvalues[var_name], 4),
            "显著性": _significance_stars(model.pvalues[var_name]),
        })

    coef_df = pd.DataFrame(coef_rows)

    # 解释文本
    dep_cn = _get_cn_label(var_dict, dependent_var)
    interpretation = _build_regression_interpretation(
        model=model,
        independent_vars=independent_vars,
        dependent_cn=dep_cn,
        var_dict=var_dict,
    )

    return {
        "coefficients": coef_df,
        "r_squared": round(model.rsquared, 4),
        "adj_r_squared": round(model.rsquared_adj, 4),
        "f_statistic": round(model.fvalue, 3),
        "f_pvalue": round(model.f_pvalue, 4),
        "n": n,
        "interpretation": interpretation,
        "dependent_cn": dep_cn,
        "condition_number": round(model.condition_number, 1),
    }


# ================================================================
# 内部辅助（回归）
# ================================================================

def _significance_stars(p: float) -> str:
    """p 值转显著性标记。"""
    if p < 0.001:
        return "***"
    elif p < 0.01:
        return "**"
    elif p < 0.05:
        return "*"
    elif p < 0.1:
        return "·"
    else:
        return ""


def _build_regression_interpretation(
    model,
    independent_vars: List[str],
    dependent_cn: str,
    var_dict: Optional[Dict] = None,
) -> str:
    """构建 OLS 回归的中文解释文本。

    措辞规范：
      - "与...显著正相关 / 负相关"，不用"导致""必然"
      - "可能"用于不确定性表述
    """
    lines = []
    r2 = model.rsquared
    adj_r2 = model.rsquared_adj
    n = int(model.nobs)

    # 模型整体
    lines.append(f"回归模型整体显著（F = {model.fvalue:.3f}, p = {model.f_pvalue:.4f}），")
    lines.append(f"R² = {r2:.3f}，调整 R² = {adj_r2:.3f}，有效样本 n = {n}。")
    lines.append(f"该模型可解释 **{dependent_cn}** 约 {adj_r2*100:.1f}% 的变异。")
    lines.append("")

    # 分类整理自变量
    pos_sig = []  # 显著正向
    neg_sig = []  # 显著负向
    not_sig = []  # 不显著

    for var_name in independent_vars:
        if var_name not in model.params.index:
            continue
        coef = model.params[var_name]
        p_val = model.pvalues[var_name]
        cn = _get_cn_label(var_dict, var_name)

        if p_val < 0.05:
            if coef > 0:
                pos_sig.append((cn, coef, p_val))
            else:
                neg_sig.append((cn, coef, p_val))
        else:
            not_sig.append((cn, coef, p_val))

    # 显著正向
    if pos_sig:
        pos_sig.sort(key=lambda x: x[1], reverse=True)
        lines.append("**显著正向关联的因素：**")
        for cn, coef, p_val in pos_sig:
            stars = _significance_stars(p_val)
            lines.append(
                f"- **{cn}**：回归系数 = {coef:.4f}（p = {p_val:.4f}{stars}），"
                f"在控制其他变量的条件下，**{cn}** 每提高 1 个单位，"
                f"**{dependent_cn}** 平均提高 {coef:.4f} 个单位。"
            )
        lines.append("")

    # 显著负向
    if neg_sig:
        neg_sig.sort(key=lambda x: x[1])
        lines.append("**显著负向关联的因素：**")
        for cn, coef, p_val in neg_sig:
            stars = _significance_stars(p_val)
            special_note = ""
            if "wait" in cn.lower() or "等待" in cn:
                special_note = (
                    f"这表明等待时间越长，**{dependent_cn}** 可能越低。"
                    f"需要注意的是，这反映的是统计关联，不能直接推断因果关系。"
                )
            lines.append(
                f"- **{cn}**：回归系数 = {coef:.4f}（p = {p_val:.4f}{stars}），"
                f"在控制其他变量的条件下，**{cn}** 每提高 1 个单位，"
                f"**{dependent_cn}** 平均降低 {abs(coef):.4f} 个单位。"
                f"{' ' + special_note if special_note else ''}"
            )
        lines.append("")

    # 不显著
    if not_sig:
        lines.append("**未发现显著关联的因素：**")
        for cn, coef, p_val in not_sig:
            lines.append(
                f"- **{cn}**（回归系数 = {coef:.4f}，p = {p_val:.4f}），"
                f"在当前样本下与 **{dependent_cn}** 的关联未达到统计显著水平。"
            )
        lines.append("")

    # 总结
    lines.append("---")
    lines.append(
        "**重要提示：** 以上分析基于横截面调查数据，回归系数反映的是变量间的"
        "统计关联强度，不能直接解释为因果关系。可能存在未观测的混淆变量影响结果。"
        "建议结合理论框架和领域知识进行综合判断。"
    )

    return "\n".join(lines)


# ================================================================
# 逻辑回归（二分类因变量）
# ================================================================

def logit_regression(
    df: pd.DataFrame,
    dependent_var: str,
    independent_vars: List[str],
    var_dict: Optional[Dict] = None,
) -> Dict:
    """执行二元逻辑回归分析（statsmodels.Logit）。

    使用 statsmodels 的 Logit 模型，自动输出系数、OR、z 值、p 值、
    伪 R² 和似然比检验结果。

    Args:
        df: 原始数据
        dependent_var: 二分类因变量名（必须恰好有 2 个唯一值）
        independent_vars: 自变量名列表
        var_dict: 变量字典（可选，用于显示中文名）

    Returns:
        {
            "coefficients": DataFrame（含 变量、回归系数、标准误、z 值、p 值、
                            显著性、OR (exp(B))、OR 95% CI 下限、OR 95% CI 上限）,
            "pseudo_r_squared": float（McFadden 伪 R²）,
            "log_likelihood": float,
            "llr_pvalue": float（似然比检验 p 值）,
            "n": int（有效样本量）,
            "interpretation": str（中文解释文本）,
            "dependent_cn": str（因变量中文名）,
        }
        失败时返回 {"error": str}
    """
    try:
        import statsmodels.api as sm
    except ImportError:
        return {"error": "缺少 statsmodels 库，请执行 pip install statsmodels"}

    if dependent_var not in df.columns:
        return {"error": f"数据中不存在因变量「{dependent_var}」"}

    missing_ind = [v for v in independent_vars if v not in df.columns]
    if missing_ind:
        return {"error": f"数据中不存在自变量：{', '.join(missing_ind)}"}

    # 提取有效样本
    all_vars = [dependent_var] + independent_vars
    clean = df[all_vars].copy()
    for v in independent_vars:
        clean[v] = pd.to_numeric(clean[v], errors="coerce")
    clean = clean.dropna()
    n = len(clean)

    # 检查因变量是否为二分类
    y_unique = clean[dependent_var].dropna().unique()
    if len(y_unique) < 2:
        return {"error": f"因变量「{dependent_var}」只剩一个类别，无法进行逻辑回归。"}
    if len(y_unique) > 2:
        return {
            "error": f"因变量「{dependent_var}」有 {len(y_unique)} 个类别，"
            "二元逻辑回归仅适用于二分类因变量。请考虑多项逻辑回归。"
        }

    if n < len(independent_vars) + 10:
        return {"error": f"有效样本量不足（n={n}，需至少 {len(independent_vars) + 10}）。"}

    # 构造 X, y（确保 y 是 0/1 编码）
    y_raw = clean[dependent_var]
    y_vals = sorted(y_raw.unique())
    y = (y_raw == y_vals[1]).astype(int)

    X = clean[independent_vars].astype(float)
    X = sm.add_constant(X)

    try:
        model = sm.Logit(y, X).fit(disp=False)
    except np.linalg.LinAlgError:
        return {"error": "矩阵奇异，可能由于多重共线性或自变量为常数。请检查自变量间是否存在高度线性相关。"}
    except Exception as e:
        err_msg = str(e)
        if "PerfectSeparation" in err_msg or "perfect separation" in err_msg.lower():
            return {
                "error": "数据存在完全分离，逻辑回归无法拟合。"
                "可能原因：某个自变量（或自变量组合）完美预测目标变量。"
                "建议检查数据或移除该自变量。"
            }
        if "Maximum number of iterations" in err_msg or "convergence" in err_msg.lower():
            return {"error": f"逻辑回归模型未收敛：{err_msg}。建议增加最大迭代次数或检查自变量尺度。"}
        return {"error": f"逻辑回归模型拟合失败：{err_msg}"}

    # 整理系数表（含 OR 和 CI）
    coef_rows = []
    for var_name in model.params.index:
        cn = _get_cn_label(var_dict, var_name) if var_name != "const" else "截距"
        or_val = np.exp(model.params[var_name])
        ci_lower = np.exp(model.conf_int().loc[var_name, 0])
        ci_upper = np.exp(model.conf_int().loc[var_name, 1])
        coef_rows.append({
            "变量": cn if var_name == "const" else f"{var_name}（{cn}）" if cn != var_name else var_name,
            "回归系数": round(model.params[var_name], 4),
            "标准误": round(model.bse[var_name], 4),
            "z 值": round(model.tvalues[var_name], 3),
            "p 值": round(model.pvalues[var_name], 4),
            "显著性": _significance_stars(model.pvalues[var_name]),
            "OR (exp(B))": round(or_val, 4),
            "OR 95% CI 下限": round(ci_lower, 4),
            "OR 95% CI 上限": round(ci_upper, 4),
        })

    coef_df = pd.DataFrame(coef_rows)

    # 解释文本
    dep_cn = _get_cn_label(var_dict, dependent_var)
    interpretation = _build_logit_interpretation(
        model=model,
        independent_vars=independent_vars,
        dependent_cn=dep_cn,
        var_dict=var_dict,
    )

    return {
        "coefficients": coef_df,
        "pseudo_r_squared": round(model.prsquared, 4),
        "log_likelihood": round(model.llf, 2),
        "llr_pvalue": round(model.llr_pvalue, 4),
        "n": n,
        "interpretation": interpretation,
        "dependent_cn": dep_cn,
    }


def _build_logit_interpretation(
    model,
    independent_vars: List[str],
    dependent_cn: str,
    var_dict: Optional[Dict] = None,
) -> str:
    """构建逻辑回归的中文解释文本。

    措辞规范：
      - 以优势比（OR）为核心解释指标
      - OR > 1 → "增加 Y=1 的几率"
      - OR < 1 → "降低 Y=1 的几率"
      - 谨慎表达，不把统计关联等同于因果
    """
    lines = []
    pseudo_r2 = model.prsquared
    n = int(model.nobs)

    # 模型整体
    lines.append(f"逻辑回归模型整体显著（似然比检验 p = {model.llr_pvalue:.4f}），")
    lines.append(f"McFadden 伪 R² = {pseudo_r2:.3f}，有效样本 n = {n}。")
    if pseudo_r2 >= 0.2:
        lines.append("模型拟合优度较高。")
    elif pseudo_r2 >= 0.1:
        lines.append("模型拟合优度尚可。")
    else:
        lines.append("模型拟合优度偏低，可能遗漏重要预测变量。")
    lines.append("")

    # 分类整理自变量
    pos_sig = []   # OR > 1 且显著
    neg_sig = []   # OR < 1 且显著
    not_sig = []   # 不显著

    for var_name in independent_vars:
        if var_name not in model.params.index:
            continue
        coef = model.params[var_name]
        p_val = model.pvalues[var_name]
        cn = _get_cn_label(var_dict, var_name)

        if p_val < 0.05:
            or_val = np.exp(coef)
            if or_val > 1:
                pos_sig.append((cn, or_val, p_val))
            else:
                neg_sig.append((cn, or_val, p_val))
        else:
            or_val = np.exp(coef)
            not_sig.append((cn, or_val, p_val))

    # 显著正向（OR > 1）
    if pos_sig:
        pos_sig.sort(key=lambda x: x[1], reverse=True)
        lines.append("**显著增加目标事件发生几率的因素（OR > 1）：**")
        for cn, or_val, p_val in pos_sig:
            stars = _significance_stars(p_val)
            pct_change = (or_val - 1) * 100
            lines.append(
                f"- **{cn}**：OR = {or_val:.4f}（p = {p_val:.4f}{stars}），"
                f"在控制其他变量的条件下，**{cn}** 每提高 1 个单位，"
                f"目标事件发生的几率增加约 **{pct_change:.1f}%**。"
            )
        lines.append("")

    # 显著负向（OR < 1）
    if neg_sig:
        neg_sig.sort(key=lambda x: x[1])
        lines.append("**显著降低目标事件发生几率的因素（OR < 1）：**")
        for cn, or_val, p_val in neg_sig:
            stars = _significance_stars(p_val)
            pct_change = (1 - or_val) * 100
            lines.append(
                f"- **{cn}**：OR = {or_val:.4f}（p = {p_val:.4f}{stars}），"
                f"在控制其他变量的条件下，**{cn}** 每提高 1 个单位，"
                f"目标事件发生的几率降低约 **{pct_change:.1f}%**。"
            )
        lines.append("")

    # 不显著
    if not_sig:
        lines.append("**未发现显著预测作用的因素：**")
        for cn, or_val, p_val in not_sig:
            lines.append(
                f"- **{cn}**（OR = {or_val:.4f}，p = {p_val:.4f}），"
                f"在当前样本下对目标事件的预测作用未达到统计显著水平。"
            )
        lines.append("")

    # 总结
    lines.append("---")
    lines.append(
        "**重要提示：** 以上分析基于横截面调查数据，优势比（OR）反映的是变量间的"
        "统计关联强度，不能直接解释为因果关系。逻辑回归假设自变量与对数几率之间存在"
        "线性关系，且样本量足够支持参数估计。建议结合理论框架和领域知识进行综合判断。"
    )

    return "\n".join(lines)


# ================================================================
# 满意度专属分析
# ================================================================

def satisfaction_summary(
    df: pd.DataFrame,
    satisfaction_cols: List[str],
    var_dict: Optional[Dict] = None,
) -> pd.DataFrame:
    """对满意度相关变量输出含均值和分布摘要的综合表。

    Args:
        df: 原始数据
        satisfaction_cols: 满意度变量列表（如 staff_attitude, overall_satisfaction 等）
        var_dict: 变量字典

    Returns:
        每行一个满意度变量，列含 均值、标准差、低评占比、高评占比 等
    """
    rows = []
    for col in satisfaction_cols:
        if col not in df.columns:
            continue

        series = pd.to_numeric(df[col], errors="coerce").dropna()
        n = len(series)
        mean_val = series.mean()
        std_val = series.std()

        # 低评：<=2；高评：>=4（假设 5 级量表）
        low_pct = (series <= 2).sum() / n * 100 if n > 0 else 0
        high_pct = (series >= 4).sum() / n * 100 if n > 0 else 0

        var_label = col
        if var_dict and col in var_dict:
            cn = var_dict[col].get("中文含义", "")
            var_label = f"{col}（{cn}）" if cn else col

        rows.append({
            "变量": var_label,
            "样本量": n,
            "均值": round(mean_val, 2),
            "标准差": round(std_val, 2),
            "低评占比(%)": round(low_pct, 2),
            "高评占比(%)": round(high_pct, 2),
        })

    return pd.DataFrame(rows)
