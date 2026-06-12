"""AI 数据理解 Payload 打包模块。

将数据集的结构信息打包为轻量级的 table_understanding_payload，
供 AI 进行数据理解和分析方案推荐。

设计原则:
  - 不发送完整原始数据行
  - 仅发送结构信息 + 压缩统计摘要 + 变量元信息
  - 隐私字段按 send_to_ai_mode 处理
"""

import json
from datetime import datetime, timezone, date
from typing import Any, Dict, List, Optional

import pandas as pd
import numpy as np

from src.analysis_packager import _read_privacy_settings, _mask_value


def _make_json_safe(obj: Any) -> Any:
    """递归将 numpy/pandas 类型转为 JSON 可序列化的 Python 原生类型。"""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        val = float(obj)
        return None if np.isnan(val) or np.isinf(val) else val
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.ndarray,)):
        return [_make_json_safe(v) for v in obj.tolist()]
    if isinstance(obj, (pd.Timestamp,)):
        return obj.isoformat()
    try:
        if pd.isna(obj) and not isinstance(obj, (str, list, dict, tuple, set)):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): _make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_make_json_safe(v) for v in obj]
    return obj

# ── 限制 ──
MAX_EXAMPLE_VALUES = 5
MAX_FREQ_CATEGORIES = 10
MAX_QUICK_STATS_PREVIEW = 15


def build_table_understanding_payload(
    df: pd.DataFrame,
    schema_df: pd.DataFrame,
    quality: Optional[Dict[str, Any]] = None,
    variable_dict_map: Optional[Dict[str, Dict[str, Any]]] = None,
    user_goal: str = "",
    preset_profile: Optional[Dict[str, Any]] = None,
    selected_sheet: str = "",
    file_type: str = "",
    dataset_name: str = "",
) -> Dict[str, Any]:
    """构建 AI 数据理解所需的轻量级 payload。

    Args:
        df: 原始数据（仅用于提取元信息和压缩统计，不发送原始行）
        schema_df: 变量类型推断结果
        quality: 数据质量报告
        variable_dict_map: 变量说明字典（可选）
        user_goal: 用户的分析目标（自然语言）
        preset_profile: 当前预设方案（如有）
        selected_sheet: 选中的工作表名
        file_type: 文件类型
        dataset_name: 数据集名称

    Returns:
        table_understanding_payload 字典
    """
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    n_rows, n_cols = df.shape

    # ── 读取隐私设置 ──
    privacy_settings = _read_privacy_settings(schema_df)

    # ── 1. dataset_overview ──
    dataset_overview = _build_dataset_overview(
        df, quality, selected_sheet, file_type, dataset_name, n_rows, n_cols,
    )

    # ── 2. variable_schema ──
    variable_schema = _build_understanding_variable_schema(
        schema_df, privacy_settings, variable_dict_map,
    )

    # ── 3. data_quality_summary ──
    data_quality_summary = _build_data_quality_summary(
        df, schema_df, privacy_settings, quality,
    )

    # ── 4. quick_statistics ──
    quick_statistics = _build_quick_statistics(df, schema_df, privacy_settings)

    # ── 5. user_goal ──
    user_goal_section = {"goal_text": user_goal} if user_goal else None

    # ── 6. current_profile ──
    current_profile_section = None
    if preset_profile:
        current_profile_section = {
            "profile_key": preset_profile.get("profile_key", ""),
            "profile_name": preset_profile.get("profile_name", ""),
            "target_variable": preset_profile.get("target_variable", ""),
            "group_variables": preset_profile.get("group_variables", []),
            "explanatory_variables": preset_profile.get("explanatory_variables", []),
            "note": "当前数据加载了预设分析方案，以上变量配置仅供参考，AI 也可以另行推荐。",
        }

    # ── 组装 ──
    payload: Dict[str, Any] = {
        "generated_at": generated_at,
        "dataset_overview": dataset_overview,
        "variable_schema": variable_schema,
        "data_quality_summary": data_quality_summary,
        "quick_statistics": quick_statistics,
    }
    if user_goal_section:
        payload["user_goal"] = user_goal_section
    if current_profile_section:
        payload["current_profile"] = current_profile_section

    return payload


# ================================================================
# 1. dataset_overview
# ================================================================

def _build_dataset_overview(
    df: pd.DataFrame,
    quality: Optional[Dict[str, Any]],
    selected_sheet: str,
    file_type: str,
    dataset_name: str,
    n_rows: int,
    n_cols: int,
) -> Dict[str, Any]:
    overview: Dict[str, Any] = {
        "row_count": n_rows,
        "column_count": n_cols,
        "column_names": list(df.columns),
    }
    if dataset_name:
        overview["dataset_name"] = dataset_name
    if selected_sheet:
        overview["selected_sheet"] = selected_sheet
    if file_type:
        overview["file_type"] = file_type
    if quality:
        overview["missing_total"] = quality.get("缺失值总数", 0)
        overview["missing_rate_pct"] = quality.get("缺失率", 0)
        overview["duplicate_rows"] = quality.get("重复行数", 0)
        overview["duplicate_rate_pct"] = quality.get("重复率", 0)
    return overview


# ================================================================
# 2. variable_schema (understanding version)
# ================================================================

def _build_understanding_variable_schema(
    schema_df: pd.DataFrame,
    privacy_settings: Dict[str, Dict[str, Any]],
    variable_dict_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """构建 AI 数据理解用的变量结构信息（比 analysis_payload 更侧重规划）。"""
    schema_list = []
    for _, row in schema_df.iterrows():
        col = row["column"]
        ps = privacy_settings.get(col, {})
        send_mode = ps.get("send_to_ai_mode", "aggregate_only")
        privacy_cat = ps.get("privacy_category", "none")

        # 示例值处理
        raw_examples = _safe_example_values(row.get("example_values", ""), MAX_EXAMPLE_VALUES)
        if send_mode == "exclude":
            examples = []
        elif send_mode == "masked_examples":
            examples = [_mask_value(v, privacy_cat) for v in raw_examples]
        else:
            examples = raw_examples

        # 变量说明表信息
        vdict = (variable_dict_map or {}).get(col, {})

        entry: Dict[str, Any] = {
            "column": col,
            "display_name": row.get("display_name", "") or vdict.get("中文含义", "") or col,
            "inferred_type": row.get("inferred_type", ""),
            "user_confirmed_type": vdict.get("类型", "") or row.get("inferred_type", ""),
            "missing_rate_pct": float(row.get("missing_rate", 0)),
            "unique_count": int(row.get("unique_count", 0)),
            "example_values": examples,
            "value_labels": vdict.get("labels", {}),
            "variable_usage_from_dict": vdict.get("变量用途", ""),
            "detected_usage": vdict.get("detected_usage", ""),
            "suggested_role": row.get("suggested_role", ""),
            "privacy_risk": ps.get("privacy_risk", "none"),
            "privacy_category": privacy_cat,
            "send_to_ai_mode": send_mode,
        }

        schema_list.append(entry)
    return schema_list


# ================================================================
# 3. data_quality_summary
# ================================================================

def _build_data_quality_summary(
    df: pd.DataFrame,
    schema_df: pd.DataFrame,
    privacy_settings: Dict[str, Dict[str, Any]],
    quality: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """数据质量摘要，帮助 AI 理解数据使用注意事项。"""
    high_missing = []
    high_unique = []
    suspected_id = []
    suspected_text = []
    privacy_vars = []
    modelable_count = 0
    groupable_count = 0

    for _, row in schema_df.iterrows():
        col = row["column"]
        vtype = row.get("inferred_type", "")
        missing_rate = float(row.get("missing_rate", 0))
        unique_count = int(row.get("unique_count", 0))
        role = row.get("suggested_role", "")

        if missing_rate > 10:
            high_missing.append(col)
        if unique_count > 50 and vtype not in ("text", "id", "datetime"):
            high_unique.append(col)
        if role == "id":
            suspected_id.append(col)
        if vtype in ("text", "high_cardinality"):
            suspected_text.append(col)

        ps = privacy_settings.get(col, {})
        if ps.get("privacy_risk") in ("medium", "high"):
            privacy_vars.append({
                "column": col,
                "risk": ps.get("privacy_risk"),
                "category": ps.get("privacy_category"),
                "send_mode": ps.get("send_to_ai_mode"),
            })

        if vtype in ("numeric", "ordinal") and ps.get("allow_in_model", True):
            modelable_count += 1
        if vtype in ("categorical", "ordinal") and unique_count <= 15 and ps.get("allow_as_group_variable", True):
            groupable_count += 1

    return {
        "high_missing_vars": high_missing,
        "high_unique_vars": high_unique,
        "suspected_id_vars": suspected_id,
        "suspected_text_vars": suspected_text,
        "privacy_risk_vars": privacy_vars,
        "modelable_var_count": modelable_count,
        "groupable_var_count": groupable_count,
        "total_vars": len(schema_df),
        "total_rows": len(df),
    }


# ================================================================
# 4. quick_statistics (compressed)
# ================================================================

def _build_quick_statistics(
    df: pd.DataFrame,
    schema_df: pd.DataFrame,
    privacy_settings: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """构建压缩统计摘要（不发送完整原始明细）。"""
    numeric_summary: List[Dict[str, Any]] = []
    categorical_summary: List[Dict[str, Any]] = []
    ordinal_summary: List[Dict[str, Any]] = []

    for _, row in schema_df.iterrows():
        col = row["column"]
        vtype = row.get("inferred_type", "")
        ps = privacy_settings.get(col, {})
        send_mode = ps.get("send_to_ai_mode", "aggregate_only")

        if send_mode == "exclude":
            continue  # 完全跳过 exclude 的变量

        try:
            if vtype == "numeric":
                series = pd.to_numeric(df[col], errors="coerce").dropna()
                if len(series) >= 3:
                    numeric_summary.append({
                        "column": col,
                        "count": len(series),
                        "mean": round(series.mean(), 2),
                        "std": round(series.std(), 2),
                        "min": round(series.min(), 2),
                        "max": round(series.max(), 2),
                        "median": round(series.median(), 2),
                    })
                    if len(numeric_summary) >= MAX_QUICK_STATS_PREVIEW:
                        break

            elif vtype in ("categorical", "ordinal"):
                series = df[col].dropna().astype(str)
                freq = series.value_counts().head(MAX_FREQ_CATEGORIES)
                cats = [
                    {"category": str(k), "count": int(v), "pct": round(v / len(series) * 100, 1)}
                    for k, v in freq.items()
                ]
                entry = {
                    "column": col,
                    "valid_count": len(series),
                    "unique_count": series.nunique(),
                    "top_categories": cats,
                }
                if vtype == "ordinal":
                    ordinal_summary.append(entry)
                else:
                    categorical_summary.append(entry)

                if len(categorical_summary) + len(ordinal_summary) >= MAX_QUICK_STATS_PREVIEW:
                    break
        except Exception:
            continue

    return {
        "numeric_variables": numeric_summary,
        "categorical_variables": categorical_summary,
        "ordinal_variables": ordinal_summary,
        "note": (
            "以上为压缩统计摘要，仅展示前 {} 个变量和 {} 个类别。"
            "完整统计结果在 analysis_payload 中。"
        ).format(MAX_QUICK_STATS_PREVIEW, MAX_FREQ_CATEGORIES),
    }


# ================================================================
# 辅助
# ================================================================

def _safe_example_values(raw: Any, max_count: int) -> List[str]:
    """安全提取示例值列表。"""
    if isinstance(raw, list):
        return [str(v)[:80] for v in raw[:max_count]]
    if isinstance(raw, str):
        vals = [v.strip() for v in raw.split(",") if v.strip()]
        return vals[:max_count]
    return []


def to_json_payload(payload: Dict[str, Any]) -> str:
    """将 table_understanding_payload 序列化为 JSON 字符串。"""
    return json.dumps(_make_json_safe(payload), ensure_ascii=False, indent=2)
