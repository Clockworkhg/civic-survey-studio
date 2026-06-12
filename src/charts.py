"""可视化图表模块 —— 基于 Plotly 生成交互式图表。

包含：
  - 通用图表工具：柱状图、饼图、直方图、热力图、箱线图、堆叠图
  - 政务满意度专属图表：满意度分布、区域对比、渠道对比、散点趋势、
    雷达图、优先改进事项

整体风格：简洁、政务汇报风，蓝灰色调。
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, Dict, Any, List


# ================================================================
# 主题常量
# ================================================================
COLOR_PRIMARY   = "#2B5F8A"   # 深蓝主色
COLOR_SECONDARY = "#7FA3C2"   # 浅蓝辅色
COLOR_ACCENT    = "#C44E52"   # 强调红
COLOR_GRAY      = "#8C8C8C"   # 灰色
COLOR_BG        = "#F8F9FA"   # 背景浅灰
FONT_FAMILY     = "Microsoft YaHei, SimHei, sans-serif"

# 分类色板
CAT_COLORS = [
    COLOR_PRIMARY, COLOR_SECONDARY, "#5DADE2", "#58D68D",
    "#F5B041", COLOR_ACCENT, "#AF7AC5", COLOR_GRAY,
]

# 通用 layout 模板
BASE_LAYOUT: Dict[str, Any] = dict(
    font=dict(family=FONT_FAMILY, size=13, color="#333333"),
    plot_bgcolor=COLOR_BG,
    paper_bgcolor="white",
    margin=dict(t=50, b=50, l=60, r=30),
    hoverlabel=dict(font_family=FONT_FAMILY, font_size=12),
)

# ================================================================
# 内部辅助
# ================================================================

def _apply_base(fig: go.Figure, **overrides: Any) -> go.Figure:
    """应用通用样式，支持按需覆盖。"""
    layout = {**BASE_LAYOUT, **overrides}
    fig.update_layout(**layout)
    return fig


def _safe_column(df: pd.DataFrame, col: str) -> bool:
    """检查列是否存在且非空。"""
    return col in df.columns and df[col].notna().any()


def _get_cn(var_dict: Dict, col: str, fallback: str = "") -> str:
    """从变量字典获取中文含义。"""
    if var_dict and col in var_dict:
        return var_dict[col].get("中文含义", fallback)
    return fallback


def _get_labels(var_dict: Dict, col: str) -> Dict[int, str]:
    """从变量字典获取标签映射。"""
    if var_dict and col in var_dict:
        return var_dict[col].get("labels", {})
    return {}


# ================================================================
# 通用图表工具
# ================================================================

def bar_chart(
    data: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    horizontal: bool = False,
    color: str = COLOR_PRIMARY,
) -> go.Figure:
    """柱状图 / 条形图。"""
    if horizontal:
        fig = px.bar(
            data, y=x_col, x=y_col, orientation="h",
            title=title,
            labels={x_col: x_label or x_col, y_col: y_label or y_col},
            color_discrete_sequence=[color],
            text=y_col,
        )
    else:
        fig = px.bar(
            data, x=x_col, y=y_col,
            title=title,
            labels={x_col: x_label or x_col, y_col: y_label or y_col},
            color_discrete_sequence=[color],
            text=y_col,
        )
    fig.update_traces(
        textposition="outside",
        texttemplate="%{text:.1f}",
        marker_line_width=0,
    )
    return _apply_base(fig)


def pie_chart(
    data: pd.DataFrame,
    names_col: str,
    values_col: str,
    title: str = "",
    hole: float = 0.0,
) -> go.Figure:
    """饼图 / 环形图。

    Args:
        hole: 内径比例（0=饼图，0.4=环形图）
    """
    fig = px.pie(
        data, names=names_col, values=values_col, title=title,
        color_discrete_sequence=CAT_COLORS,
        hole=hole,
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="%{label}<br>频次: %{value}<br>占比: %{percent}",
    )
    return _apply_base(fig)


def histogram(
    series: pd.Series,
    title: str = "分布直方图",
    x_label: str = "",
    nbins: int = 20,
) -> go.Figure:
    """数值分布直方图。"""
    clean = pd.to_numeric(series, errors="coerce").dropna()
    fig = px.histogram(
        clean, nbins=nbins, title=title,
        labels={"value": x_label or series.name or "值", "count": "频次"},
        color_discrete_sequence=[COLOR_PRIMARY],
    )
    fig.update_traces(marker_line_width=0)
    return _apply_base(fig)


def box_plot(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str = "",
) -> go.Figure:
    """箱线图（按分组）。"""
    fig = px.box(
        df, x=x_col, y=y_col, title=title,
        color=x_col,
        color_discrete_sequence=[COLOR_PRIMARY, COLOR_SECONDARY, COLOR_ACCENT],
    )
    fig.update_traces(marker=dict(size=4))
    return _apply_base(fig)


def heatmap(
    corr_df: pd.DataFrame,
    title: str = "相关系数矩阵",
) -> go.Figure:
    """相关性热力图。"""
    fig = go.Figure(
        data=go.Heatmap(
            z=corr_df.values,
            x=corr_df.columns.tolist(),
            y=corr_df.index.tolist(),
            colorscale=[
                [0.0, "#FFFFFF"],
                [0.5, COLOR_SECONDARY],
                [1.0, COLOR_PRIMARY],
            ],
            zmin=-1, zmax=1,
            text=corr_df.values,
            texttemplate="%{text:.2f}",
            hoverongaps=False,
        )
    )
    fig.update_layout(
        title=title,
        xaxis=dict(tickangle=45),
        **{k: v for k, v in BASE_LAYOUT.items() if k != "margin"},
    )
    return fig


def stacked_bar(
    data: pd.DataFrame,
    x_col: str,
    y_cols: list,
    title: str = "",
    x_label: str = "",
    y_label: str = "",
) -> go.Figure:
    """堆叠柱状图。"""
    fig = go.Figure()
    for i, yc in enumerate(y_cols):
        fig.add_trace(go.Bar(
            name=yc,
            x=data[x_col],
            y=data[yc],
            marker_color=CAT_COLORS[i % len(CAT_COLORS)],
            text=data[yc],
            textposition="inside",
            texttemplate="%{text:.1f}",
        ))
    fig.update_layout(
        barmode="stack",
        title=title,
        xaxis_title=x_label or x_col,
        yaxis_title=y_label or "频次",
        **{k: v for k, v in BASE_LAYOUT.items() if k != "margin"},
    )
    return fig


# ================================================================
# 政务满意度专属图表
# ================================================================

def plot_overall_satisfaction(
    df: pd.DataFrame,
    var_dict: Optional[Dict] = None,
    col: str = "overall_satisfaction",
) -> Optional[go.Figure]:
    """图表1：总体满意度分布柱状图。

    变量：默认 overall_satisfaction（5 级评分），可通过 col 参数指定。
    """
    if not _safe_column(df, col):
        return None

    labels = _get_labels(var_dict, col)
    cn = _get_cn(var_dict, col, col)

    counts = df[col].value_counts().sort_index()
    plot_df = pd.DataFrame({
        "评分": [labels.get(int(k), str(int(k))) for k in counts.index],
        "频次": counts.values,
    })
    plot_df["百分比"] = (plot_df["频次"] / plot_df["频次"].sum() * 100).round(1)

    fig = px.bar(
        plot_df, x="评分", y="频次",
        title=f"总体满意度分布 — {cn}",
        labels={"评分": "满意度评分", "频次": "人数"},
        color_discrete_sequence=[COLOR_PRIMARY],
        text="频次",
    )
    fig.update_traces(
        textposition="outside",
        texttemplate="%{text}人",
        marker_line_width=0,
    )
    fig.update_layout(
        yaxis=dict(title="人数"),
    )
    return _apply_base(fig)


def plot_satisfaction_level(
    df: pd.DataFrame,
    var_dict: Optional[Dict] = None,
    col: str = "satisfaction_level",
) -> Optional[go.Figure]:
    """图表2：满意度等级分布环形图。

    变量：默认 satisfaction_level（1=低满意, 2=中等满意, 3=高满意），可通过 col 参数指定。
    """
    if not _safe_column(df, col):
        return None

    labels = _get_labels(var_dict, col)
    cn = _get_cn(var_dict, col, col)

    counts = df[col].value_counts().sort_index()
    plot_df = pd.DataFrame({
        "等级": [labels.get(int(k), f"等级{int(k)}") for k in counts.index],
        "频次": counts.values,
    })

    fig = px.pie(
        plot_df, names="等级", values="频次",
        title=f"满意度等级分布 — {cn}",
        color_discrete_sequence=CAT_COLORS,
        hole=0.45,
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="%{label}<br>人数: %{value}<br>占比: %{percent}",
    )
    # 中心文字
    total = plot_df["频次"].sum()
    fig.add_annotation(
        text=f"总样本<br><b>{total}</b>",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=16, color=COLOR_PRIMARY, family=FONT_FAMILY),
    )
    return _apply_base(fig)


def plot_district_comparison(
    df: pd.DataFrame,
    var_dict: Optional[Dict] = None,
    group_col: str = "district",
    value_col: str = "overall_satisfaction",
) -> Optional[go.Figure]:
    """图表3：各分组在目标变量上的均值对比柱状图。

    默认分组：district；默认指标：overall_satisfaction 均值。
    可通过 group_col / value_col 参数指定其他列。
    """
    if not _safe_column(df, group_col) or not _safe_column(df, value_col):
        return None

    labels = _get_labels(var_dict, group_col)
    cn_group = _get_cn(var_dict, group_col, group_col)
    cn_value = _get_cn(var_dict, value_col, value_col)

    means = df.groupby(group_col)[value_col].mean().round(2).sort_values(ascending=False)
    plot_df = pd.DataFrame({
        "分组": [labels.get(int(k), f"类别{int(k)}") for k in means.index],
        "均值": means.values,
    })

    fig = px.bar(
        plot_df, x="分组", y="均值",
        title=f"各{cn_group}在{cn_value}上的对比",
        labels={"分组": cn_group, "均值": cn_value},
        color="均值",
        color_continuous_scale=[
            [0.0, COLOR_SECONDARY],
            [0.5, COLOR_PRIMARY],
            [1.0, "#1A3A5C"],
        ],
        text="均值",
    )
    fig.update_traces(
        textposition="outside",
        texttemplate="%{text:.2f}",
        marker_line_width=0,
    )
    fig.update_layout(
        coloraxis_showscale=False,
        yaxis=dict(range=[0, max(means.values) * 1.15 if len(means) > 0 else 5]),
    )
    return _apply_base(fig)


def plot_channel_comparison(
    df: pd.DataFrame,
    var_dict: Optional[Dict] = None,
    group_col: str = "channel",
    value_col: str = "overall_satisfaction",
) -> Optional[go.Figure]:
    """图表4：不同分组在目标变量上的对比柱状图。

    默认分组：channel；默认指标：overall_satisfaction 均值。
    可通过 group_col / value_col 参数指定其他列。
    """
    if not _safe_column(df, group_col) or not _safe_column(df, value_col):
        return None

    labels = _get_labels(var_dict, group_col)
    cn_group = _get_cn(var_dict, group_col, group_col)

    means = df.groupby(group_col)[value_col].mean().round(2).sort_values(ascending=False)
    plot_df = pd.DataFrame({
        "分组": [labels.get(int(k), f"类别{int(k)}") for k in means.index],
        "均值": means.values,
    })

    fig = px.bar(
        plot_df, x="分组", y="均值",
        title=f"不同{cn_group}的{_get_cn(var_dict, value_col, value_col)}对比",
        labels={"分组": cn_group, "均值": "均值"},
        color_discrete_sequence=[COLOR_PRIMARY],
        text="均值",
    )
    fig.update_traces(
        textposition="outside",
        texttemplate="%{text:.2f}",
        marker_line_width=0,
    )
    fig.update_layout(
        yaxis=dict(range=[0, max(means.values) * 1.15 if len(means) > 0 else 5]),
    )
    return _apply_base(fig)


def plot_wait_satisfaction_scatter(
    df: pd.DataFrame,
    var_dict: Optional[Dict] = None,
    x_col: str = "wait_time_min",
    y_col: str = "overall_satisfaction",
) -> Optional[go.Figure]:
    """图表5：等待时间与满意度散点图（含趋势线）。

    默认 x：wait_time_min；默认 y：overall_satisfaction。
    可通过 x_col / y_col 参数指定其他列。
    """
    if not _safe_column(df, x_col) or not _safe_column(df, y_col):
        return None

    cn_x = _get_cn(var_dict, x_col, x_col)
    cn_y = _get_cn(var_dict, y_col, y_col)

    clean = df[[x_col, y_col]].dropna()
    clean[x_col] = pd.to_numeric(clean[x_col], errors="coerce")
    clean[y_col] = pd.to_numeric(clean[y_col], errors="coerce")
    clean = clean.dropna()

    if len(clean) == 0:
        return None

    fig = px.scatter(
        clean, x=x_col, y=y_col,
        title=f"{cn_x}与{cn_y}关系",
        labels={x_col: cn_x, y_col: cn_y},
        color_discrete_sequence=[COLOR_PRIMARY],
        opacity=0.5,
        trendline="ols",
        trendline_color_override=COLOR_ACCENT,
    )

    # 调整趋势线样式
    for trace in fig.data:
        if trace.mode == "lines":
            trace.name = "趋势线 (OLS)"

    fig.update_traces(
        marker=dict(size=8, line=dict(width=0)),
        selector=dict(mode="markers"),
    )
    return _apply_base(fig)


def plot_satisfaction_radar(
    df: pd.DataFrame,
    var_dict: Optional[Dict] = None,
    cols: Optional[List[str]] = None,
) -> Optional[go.Figure]:
    """图表6：多维度均值雷达图。

    默认维度：wait_satisfaction、staff_attitude、process_convenience、
      online_service、info_transparency、policy_trust、overall_satisfaction。
    可通过 cols 参数指定其他维度列表。
    """
    if cols is None:
        dimensions = [
            "wait_satisfaction", "staff_attitude", "process_convenience",
            "online_service", "info_transparency", "policy_trust",
            "overall_satisfaction",
        ]
    else:
        dimensions = cols

    # 仅保留数据中存在的维度
    dims_in_data = [d for d in dimensions if _safe_column(df, d)]
    if len(dims_in_data) < 3:
        return None

    means = []
    labels = []
    for d in dims_in_data:
        s = pd.to_numeric(df[d], errors="coerce").dropna()
        if len(s) > 0:
            means.append(round(s.mean(), 2))
            cn = _get_cn(var_dict, d, d)
            # 截断过长的中文名，适合雷达图显示
            labels.append(cn if len(cn) <= 8 else cn[:6] + "…")

    if len(means) < 3:
        return None

    # 闭合雷达图
    labels_closed = labels + [labels[0]]
    means_closed = means + [means[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=means_closed,
        theta=labels_closed,
        fill="toself",
        name="满意度均值",
        fillcolor="rgba(43, 95, 138, 0.25)",
        line=dict(color=COLOR_PRIMARY, width=2.5),
        marker=dict(color=COLOR_PRIMARY, size=7, symbol="circle"),
        hovertemplate="%{theta}: <b>%{r:.2f}</b><extra></extra>",
    ))

    # 参考线（3.0）
    fig.add_trace(go.Scatterpolar(
        r=[3.0] * len(labels_closed),
        theta=labels_closed,
        mode="lines",
        name="中性参考 (3.0)",
        line=dict(color=COLOR_GRAY, width=1.2, dash="dash"),
        hoverinfo="skip",
    ))

    fig.update_layout(
        title="各满意度维度均值雷达图",
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 5.5],
                tickfont=dict(size=10, family=FONT_FAMILY),
                gridcolor="#E0E0E0",
            ),
            angularaxis=dict(
                tickfont=dict(size=12, family=FONT_FAMILY, color=COLOR_PRIMARY),
                gridcolor="#E0E0E0",
            ),
            bgcolor=COLOR_BG,
        ),
        showlegend=True,
        legend=dict(orientation="h", y=-0.12, font=dict(size=11, family=FONT_FAMILY)),
        font=dict(family=FONT_FAMILY, size=13, color="#333333"),
        paper_bgcolor="white",
        margin=dict(t=50, b=60, l=40, r=40),
    )
    return fig


def plot_priority_improve(
    df: pd.DataFrame,
    var_dict: Optional[Dict] = None,
    col: str = "priority_improve",
) -> Optional[go.Figure]:
    """图表7：优先改进事项分布柱状图。

    变量：默认 priority_improve，可通过 col 参数指定。
    """
    if not _safe_column(df, col):
        return None

    labels = _get_labels(var_dict, col)
    cn = _get_cn(var_dict, col, col)

    counts = df[col].value_counts().sort_index()
    plot_df = pd.DataFrame({
        "改进事项": [labels.get(int(k), f"选项{int(k)}") for k in counts.index],
        "频次": counts.values,
    })
    plot_df["百分比"] = (plot_df["频次"] / plot_df["频次"].sum() * 100).round(1)
    # 按频次降序
    plot_df = plot_df.sort_values("频次", ascending=True)

    fig = px.bar(
        plot_df, y="改进事项", x="频次", orientation="h",
        title=f"公众认为最需优先改进的事项 — {cn}",
        labels={"改进事项": "", "频次": "选择人数"},
        color_discrete_sequence=[COLOR_PRIMARY],
        text="频次",
    )
    # 标注百分比
    hover_texts = [
        f"{row['改进事项']}<br>人数: {row['频次']}<br>占比: {row['百分比']}%"
        for _, row in plot_df.iterrows()
    ]
    fig.update_traces(
        textposition="outside",
        texttemplate="%{text}人",
        marker_line_width=0,
        hovertemplate="%{hovertext}",
        hovertext=hover_texts,
    )
    fig.update_layout(
        xaxis=dict(title="选择人数"),
        yaxis=dict(title=""),
    )
    return _apply_base(fig)
