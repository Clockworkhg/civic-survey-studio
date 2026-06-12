"""通用可视化模块 —— 根据变量类型自动生成适配的交互式图表。

图表规则：
  1. 数值变量：直方图 + 箱线图
  2. 分类变量：柱状图 + 饼图
  3. 有序变量：柱状图（按值排序）
  4. cat × num：分组柱状图 + 箱线图
  5. num × num：散点图 + 趋势线
  6. 多数值变量：相关热力图

所有图表使用 src.charts 的主题常量和通用函数。
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, Dict, Any, List, Tuple

# 复用 charts 模块的主题和通用函数
from src.charts import (
    COLOR_PRIMARY, COLOR_SECONDARY, COLOR_ACCENT, COLOR_GRAY, COLOR_BG,
    FONT_FAMILY, CAT_COLORS, BASE_LAYOUT,
    bar_chart, pie_chart, histogram, box_plot, heatmap,
    _apply_base, _safe_column,
)


# ================================================================
# 单变量图表
# ================================================================

def auto_univariate_chart(
    df: pd.DataFrame,
    col: str,
    inferred_type: str,
    cn_name: str = "",
) -> Optional[go.Figure]:
    """根据变量类型自动生成单变量图表。

    Args:
        df: 数据框
        col: 列名
        inferred_type: 推断的变量类型
        cn_name: 中文显示名称

    Returns:
        Plotly Figure；不适用时返回 None
    """
    if not _safe_column(df, col):
        return None

    display = cn_name or col

    if inferred_type == "numeric":
        return _chart_numeric(df, col, display)

    elif inferred_type in ("categorical", "binary"):
        return _chart_categorical(df, col, display)

    elif inferred_type == "ordinal":
        return _chart_ordinal(df, col, display)

    elif inferred_type == "datetime":
        return _chart_datetime(df, col, display)

    else:
        # 尝试作为分类处理
        return _chart_categorical(df, col, display)


def _chart_numeric(df: pd.DataFrame, col: str, display: str) -> go.Figure:
    """数值变量：直方图。"""
    fig = histogram(
        pd.to_numeric(df[col], errors="coerce"),
        title=f"{display} 分布直方图",
        x_label=display,
    )
    return fig


def _chart_categorical(df: pd.DataFrame, col: str, display: str) -> go.Figure:
    """分类变量：柱状图（按频次降序）。"""
    counts = df[col].value_counts().sort_values(ascending=True)
    if len(counts) > 15:
        # 类别过多时只取前 15 个
        counts = counts.tail(15)

    plot_df = pd.DataFrame({
        "类别": counts.index.astype(str),
        "频次": counts.values,
    })

    fig = px.bar(
        plot_df, y="类别", x="频次", orientation="h",
        title=f"{display} 频数分布",
        labels={"类别": "", "频次": "频次"},
        color_discrete_sequence=[COLOR_PRIMARY],
        text="频次",
    )
    fig.update_traces(
        textposition="outside",
        texttemplate="%{text}",
        marker_line_width=0,
    )
    return _apply_base(fig)


def _chart_ordinal(df: pd.DataFrame, col: str, display: str) -> go.Figure:
    """有序变量：柱状图（按编码值排序，不按频次）。"""
    clean = pd.to_numeric(df[col], errors="coerce").dropna()
    counts = clean.value_counts().sort_index()

    # 限制显示
    if len(counts) > 20:
        counts = counts.head(20)

    plot_df = pd.DataFrame({
        "评分": counts.index.astype(int).astype(str),
        "频次": counts.values,
    })

    fig = px.bar(
        plot_df, x="评分", y="频次",
        title=f"{display} 分布",
        labels={"评分": display, "频次": "频次"},
        color_discrete_sequence=[COLOR_PRIMARY],
        text="频次",
    )
    fig.update_traces(
        textposition="outside",
        texttemplate="%{text}",
        marker_line_width=0,
    )
    fig.update_layout(xaxis=dict(type="category"))
    return _apply_base(fig)


def _chart_datetime(df: pd.DataFrame, col: str, display: str) -> Optional[go.Figure]:
    """日期时间变量：时间序列柱状图。"""
    try:
        dt_series = pd.to_datetime(df[col], errors="coerce").dropna()
        if len(dt_series) < 2:
            return None

        # 按日期分组计数
        counts = dt_series.dt.date.value_counts().sort_index()
        if len(counts) > 60:
            # 按月聚合
            counts = dt_series.dt.to_period("M").value_counts().sort_index()
            counts.index = counts.index.astype(str)

        plot_df = pd.DataFrame({
            "时间": counts.index.astype(str),
            "频次": counts.values,
        })

        fig = px.bar(
            plot_df, x="时间", y="频次",
            title=f"{display} 时间分布",
            labels={"时间": "", "频次": "频次"},
            color_discrete_sequence=[COLOR_PRIMARY],
        )
        fig.update_traces(marker_line_width=0)
        fig.update_layout(xaxis=dict(tickangle=45))
        return _apply_base(fig)
    except Exception:
        return None


# ================================================================
# 双变量图表
# ================================================================

def auto_bivariate_chart(
    df: pd.DataFrame,
    col1: str,
    col2: str,
    type1: str,
    type2: str,
    cn1: str = "",
    cn2: str = "",
) -> Optional[go.Figure]:
    """根据两个变量的类型自动生成双变量图表。

    Args:
        df: 数据框
        col1, col2: 列名
        type1, type2: 推断的变量类型
        cn1, cn2: 中文显示名称

    Returns:
        Plotly Figure；不适用时返回 None
    """
    if not _safe_column(df, col1) or not _safe_column(df, col2):
        return None

    d1 = cn1 or col1
    d2 = cn2 or col2

    # 确定哪个是分类，哪个是数值
    # binary 变量是特殊的分类变量（只有 2 个类别），可参与 cat×cat 和 cat×num 图表
    cat_type = {"categorical", "ordinal", "binary"}
    num_type = {"numeric", "ordinal"}

    is_cat1 = type1 in cat_type
    is_cat2 = type2 in cat_type
    is_num1 = type1 in num_type
    is_num2 = type2 in num_type

    # cat × cat → 堆叠柱状图
    if is_cat1 and is_cat2:
        return _chart_cat_cat(df, col1, col2, d1, d2)

    # cat × num → 箱线图
    if is_cat1 and is_num2:
        return _chart_cat_num(df, col1, col2, d1, d2)
    if is_num1 and is_cat2:
        return _chart_cat_num(df, col2, col1, d2, d1)

    # num × num → 散点图
    if is_num1 and is_num2:
        return _chart_num_num(df, col1, col2, d1, d2)

    return None


def _chart_cat_cat(
    df: pd.DataFrame, cat1: str, cat2: str, d1: str, d2: str
) -> go.Figure:
    """两个分类变量：堆叠柱状图。"""
    ctab = pd.crosstab(df[cat1], df[cat2])
    if ctab.empty or len(ctab) > 15:
        return None

    fig = go.Figure()
    for i, col_name in enumerate(ctab.columns):
        fig.add_trace(go.Bar(
            name=str(col_name),
            x=ctab.index.astype(str),
            y=ctab[col_name],
            marker_color=CAT_COLORS[i % len(CAT_COLORS)],
        ))

    fig.update_layout(
        barmode="stack",
        title=f"{d1} × {d2} 交叉分布",
        xaxis_title=d1,
        yaxis_title="频次",
        **{k: v for k, v in BASE_LAYOUT.items() if k != "margin"},
    )
    return fig


def _chart_cat_num(
    df: pd.DataFrame, cat: str, num: str, d_cat: str, d_num: str
) -> go.Figure:
    """分类 × 数值：箱线图。"""
    clean = df[[cat, num]].copy()
    clean[num] = pd.to_numeric(clean[num], errors="coerce")
    clean = clean.dropna()

    if clean[cat].nunique() > 12:
        # 类别太多，取频次最高的 12 个
        top_cats = clean[cat].value_counts().head(12).index
        clean = clean[clean[cat].isin(top_cats)]

    fig = px.box(
        clean, x=cat, y=num,
        title=f"{d_cat} × {d_num} 分组比较",
        labels={cat: d_cat, num: d_num},
        color=cat,
        color_discrete_sequence=CAT_COLORS,
    )
    fig.update_traces(marker=dict(size=4))
    return _apply_base(fig)


def _chart_num_num(
    df: pd.DataFrame, col1: str, col2: str, d1: str, d2: str
) -> go.Figure:
    """两个数值变量：散点图 + OLS 趋势线。"""
    clean = df[[col1, col2]].copy()
    clean[col1] = pd.to_numeric(clean[col1], errors="coerce")
    clean[col2] = pd.to_numeric(clean[col2], errors="coerce")
    clean = clean.dropna()

    if len(clean) < 5:
        return None

    fig = px.scatter(
        clean, x=col1, y=col2,
        title=f"{d1} 与 {d2} 的关系",
        labels={col1: d1, col2: d2},
        color_discrete_sequence=[COLOR_PRIMARY],
        opacity=0.5,
        trendline="ols",
        trendline_color_override=COLOR_ACCENT,
    )
    for trace in fig.data:
        if trace.mode == "lines":
            trace.name = "趋势线 (OLS)"

    fig.update_traces(
        marker=dict(size=8, line=dict(width=0)),
        selector=dict(mode="markers"),
    )
    return _apply_base(fig)


# ================================================================
# 图表仪表盘
# ================================================================

def correlation_heatmap_chart(
    df: pd.DataFrame,
    num_cols: List[str],
    cn_names: Optional[Dict[str, str]] = None,
) -> Optional[go.Figure]:
    """生成数值变量的相关热力图。

    Args:
        df: 数据框
        num_cols: 数值列名列表
        cn_names: {列名: 中文名} 映射

    Returns:
        Plotly Figure；列数不足时返回 None
    """
    if len(num_cols) < 2:
        return None

    numeric_df = df[num_cols].apply(lambda s: pd.to_numeric(s, errors="coerce"))
    numeric_df = numeric_df.dropna(axis=0, how="any")

    if len(numeric_df) < 5:
        return None

    corr = numeric_df.corr(method="pearson").round(3)

    # 重命名
    if cn_names:
        rename_map = {}
        for c in corr.columns:
            cn = cn_names.get(c, "")
            rename_map[c] = f"{c}（{cn}）" if cn else c
        corr = corr.rename(index=rename_map, columns=rename_map)

    return heatmap(corr, title="Pearson 相关系数矩阵")


def generate_dashboard_charts(
    df: pd.DataFrame,
    schema_df: pd.DataFrame,
    config: Optional[Dict[str, Any]] = None,
) -> List[Tuple[str, str, Optional[go.Figure]]]:
    """根据变量配置自动生成仪表盘图表列表。

    Args:
        df: 数据框
        schema_df: 变量类型推断结果
        config: 分析配置（target_variable, group_variables, explanatory_variables）

    Returns:
        [(chart_key, chart_title, Figure_or_None), ...] 列表
    """
    charts = []

    # 构建查找
    type_map = {}
    cn_map = {}
    for _, row in schema_df.iterrows():
        col = row["column"]
        type_map[col] = row["inferred_type"]
        cn_map[col] = row.get("display_name", "") or col

    config = config or {}
    target = config.get("target_variable", "")
    group_vars = config.get("group_variables", []) or []
    expl_vars = config.get("explanatory_variables", []) or []

    # 1. 目标变量图表
    if target and target in df.columns:
        fig = auto_univariate_chart(df, target, type_map.get(target, ""), cn_map.get(target, target))
        charts.append(("target", f"核心变量：{cn_map.get(target, target)} 分布", fig))

    # 2. 分组变量图表（分类变量 × 目标变量）
    for gv in group_vars:
        if gv not in df.columns or gv == target:
            continue
        if target and target in df.columns:
            fig = auto_bivariate_chart(
                df, gv, target,
                type_map.get(gv, ""), type_map.get(target, ""),
                cn_map.get(gv, gv), cn_map.get(target, target),
            )
            charts.append((f"group_{gv}", f"{cn_map.get(gv, gv)} × {cn_map.get(target, target)} 分组比较", fig))
        else:
            fig = auto_univariate_chart(df, gv, type_map.get(gv, ""), cn_map.get(gv, gv))
            charts.append((f"group_{gv}", f"分组变量：{cn_map.get(gv, gv)}", fig))

    # 3. 解释变量图表（数值变量 × 目标变量）
    for ev in expl_vars:
        if ev not in df.columns or ev == target:
            continue
        if target and target in df.columns and type_map.get(ev) in ("numeric", "ordinal") and type_map.get(target) in ("numeric", "ordinal", "binary"):
            fig = auto_bivariate_chart(
                df, ev, target,
                type_map.get(ev, ""), type_map.get(target, ""),
                cn_map.get(ev, ev), cn_map.get(target, target),
            )
            charts.append((f"expl_{ev}", f"{cn_map.get(ev, ev)} 与 {cn_map.get(target, target)}", fig))

    # 4. 相关热力图（所有数值型变量）
    num_vars = [c for c, t in type_map.items() if t in ("numeric", "ordinal") and c in df.columns]
    if target and target in df.columns and type_map.get(target) in ("numeric", "ordinal"):
        all_num = [target] + [v for v in num_vars if v != target]
    else:
        all_num = num_vars

    if len(all_num) >= 2:
        fig = correlation_heatmap_chart(df, all_num, cn_map)
        charts.append(("heatmap", "变量相关热力图", fig))

    return charts


# ================================================================
# 探索式图表（自由选择变量）
# ================================================================

def exploratory_chart(
    df: pd.DataFrame,
    chart_type: str,
    x_col: str,
    y_col: str = "",
    cn_x: str = "",
    cn_y: str = "",
    nbins: int = 20,
) -> Optional[go.Figure]:
    """生成探索式图表（用户自由选择变量）。

    Args:
        df: 数据框
        chart_type: "bar" | "pie" | "histogram" | "scatter" | "box" | "heatmap"
        x_col: X 轴变量
        y_col: Y 轴变量（散点图/箱线图需要）
        cn_x, cn_y: 中文名称

    Returns:
        Plotly Figure 或 None
    """
    if not _safe_column(df, x_col):
        return None

    dx = cn_x or x_col
    dy = cn_y or y_col

    try:
        if chart_type == "bar":
            counts = df[x_col].value_counts().sort_values(ascending=True)
            plot_df = pd.DataFrame({"类别": counts.index.astype(str), "频次": counts.values})
            return bar_chart(plot_df, x_col="频次", y_col="类别",
                           title=f"{dx} 频数分布", x_label="频次", y_label="",
                           horizontal=True)

        elif chart_type == "pie":
            counts = df[x_col].value_counts()
            plot_df = pd.DataFrame({"类别": counts.index.astype(str), "频次": counts.values})
            return pie_chart(plot_df, names_col="类别", values_col="频次",
                           title=f"{dx} 构成比例")

        elif chart_type == "histogram":
            return histogram(pd.to_numeric(df[x_col], errors="coerce"),
                           title=f"{dx} 分布直方图", x_label=dx, nbins=nbins)

        elif chart_type == "scatter" and y_col:
            if not _safe_column(df, y_col):
                return None
            clean = df[[x_col, y_col]].copy()
            clean[x_col] = pd.to_numeric(clean[x_col], errors="coerce")
            clean[y_col] = pd.to_numeric(clean[y_col], errors="coerce")
            clean = clean.dropna()
            fig = px.scatter(clean, x=x_col, y=y_col,
                           title=f"{dx} 与 {dy} 散点图",
                           labels={x_col: dx, y_col: dy},
                           color_discrete_sequence=[COLOR_PRIMARY],
                           opacity=0.5, trendline="ols",
                           trendline_color_override=COLOR_ACCENT)
            for trace in fig.data:
                if trace.mode == "lines":
                    trace.name = "趋势线 (OLS)"
            return _apply_base(fig)

        elif chart_type == "box" and y_col:
            if not _safe_column(df, y_col):
                return None
            return box_plot(df, x_col=x_col, y_col=y_col,
                          title=f"{dx} × {dy} 分组箱线图")

    except Exception:
        return None

    return None
