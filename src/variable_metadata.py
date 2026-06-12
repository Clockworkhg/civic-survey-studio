"""统一变量元数据工具模块。

为全系统提供一致的变量中文名、说明、取值标签查询接口。
所有模块（图表、统计展示、Payload、AI 方案、报告）都应通过此模块
获取变量元数据，避免各处重复实现 cn_map 查找逻辑。

使用方式:
    from src.variable_metadata import (
        get_variable_label,
        get_variable_description,
        get_value_labels,
        format_variable_name,
        build_variable_metadata_map,
    )
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd


# ================================================================
# 核心查询函数
# ================================================================


def get_variable_label(
    var_name: str,
    schema_df: pd.DataFrame,
    var_dict_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> str:
    """获取变量的中文显示名。

    优先级:
      1. 变量说明表 (var_dict_map) 中的「中文含义」/「中文名称」/ label
      2. schema_df 中已有的 display_name
      3. 如果都没有，返回原始列名

    Args:
        var_name: 原始列名
        schema_df: 变量 schema DataFrame（含 display_name 列）
        var_dict_map: 可选的变量说明字典

    Returns:
        中文显示名；无映射时返回原始列名
    """
    # Priority 1: variable_dict_map
    if var_dict_map:
        info = var_dict_map.get(var_name, {})
        for key in ("中文含义", "中文名称", "label", "display_name"):
            val = info.get(key, "")
            if val and str(val).strip():
                return str(val).strip()

    # Priority 2: schema_df display_name
    if schema_df is not None and "column" in schema_df.columns:
        row = schema_df[schema_df["column"] == var_name]
        if not row.empty:
            dn = row.iloc[0].get("display_name", "")
            if dn and str(dn).strip() and str(dn).strip() != var_name:
                return str(dn).strip()

    # Fallback: raw column name
    return var_name


def get_variable_description(
    var_name: str,
    schema_df: pd.DataFrame,
    var_dict_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> str:
    """获取变量的用途说明文本。

    优先级:
      1. var_dict_map 中的「变量用途」/「用途」/ purpose
      2. var_dict_map 中的「说明」/ description
      3. 空字符串

    Args:
        var_name: 原始列名
        schema_df: 变量 schema（当前未使用，保留接口一致性）
        var_dict_map: 可选的变量说明字典

    Returns:
        变量说明文本；无信息时返回空字符串
    """
    if var_dict_map:
        info = var_dict_map.get(var_name, {})
        for key in ("变量用途", "用途", "purpose"):
            val = info.get(key, "")
            if val and str(val).strip():
                return str(val).strip()
        for key in ("说明", "description", "取值或说明"):
            val = info.get(key, "")
            if val and str(val).strip():
                return str(val).strip()
    return ""


def get_value_labels(
    var_name: str,
    schema_df: pd.DataFrame,
    var_dict_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[int, str]:
    """获取分类/有序变量的取值标签映射。

    来源:
      1. var_dict_map[var_name]["labels"] — 由 build_variable_dict_map 预解析
      2. var_dict_map[var_name]["取值或说明"] — 现场解析
      3. 空 dict

    Args:
        var_name: 原始列名
        schema_df: 变量 schema
        var_dict_map: 可选的变量说明字典

    Returns:
        {编码值(int): 标签(str)} 字典
    """
    if var_dict_map:
        info = var_dict_map.get(var_name, {})
        # Pre-parsed labels
        labels = info.get("labels")
        if isinstance(labels, dict) and labels:
            return {int(k): str(v) for k, v in labels.items()}
        # Parse from raw text
        raw = info.get("取值或说明", "")
        if raw and str(raw).strip():
            from src.utils import parse_value_description
            parsed = parse_value_description(str(raw))
            if parsed:
                return parsed
    return {}


def format_variable_name(
    var_name: str,
    schema_df: pd.DataFrame,
    var_dict_map: Optional[Dict[str, Dict[str, Any]]] = None,
    mode: str = "label_with_raw",
) -> str:
    """根据模式格式化变量名。

    Args:
        var_name: 原始列名
        schema_df: 变量 schema
        var_dict_map: 可选的变量说明字典
        mode: 格式化模式
            - "label": 只显示中文名（无中文名时回退到原始列名）
            - "raw": 只显示原始列名
            - "label_with_raw": 「中文名（原始列名）」（默认；无中文名时只显示原始列名）
            - "report": 报告正文使用 — 首次出现时用 label_with_raw 格式，
              后续用 label 格式。此函数只返回首次格式，调用方需自行跟踪出现次数。

    Returns:
        格式化后的变量名字符串
    """
    cn = get_variable_label(var_name, schema_df, var_dict_map)

    if mode == "raw":
        return var_name

    if mode == "label":
        return cn

    if mode == "label_with_raw":
        if cn and cn != var_name:
            return f"{cn}（{var_name}）"
        return var_name

    if mode == "report":
        # Report mode: first occurrence format
        if cn and cn != var_name:
            return f"{cn}（{var_name}）"
        return cn  # No CN mapping, just use raw

    # Unknown mode → label_with_raw fallback
    if cn and cn != var_name:
        return f"{cn}（{var_name}）"
    return var_name


# ================================================================
# 批量元数据构建
# ================================================================


def build_variable_metadata_map(
    schema_df: pd.DataFrame,
    var_dict_map: Optional[Dict[str, Dict[str, Any]]] = None,
    privacy_settings: Optional[Dict[str, Dict[str, Any]]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Dict[str, Any]]:
    """构建所有变量的统一元数据字典。

    供 AI Payload、报告生成模板、图表标题等使用。

    输出格式:
        {
            "var_name": {
                "label": "中文显示名",
                "raw_name": "var_name",
                "type": "numeric|categorical|ordinal|...",
                "description": "变量用途说明",
                "value_labels": {1: "非常不满意", 5: "非常满意"},
                "role": "target|group|predictor|id|skip|none",
                "privacy_risk": "none|low|medium|high",
                "send_to_ai_mode": "exclude|aggregate_only|masked_examples|full",
                "missing_rate": 0.05,
                "unique_count": 10,
            },
            ...
        }

    Args:
        schema_df: 变量 schema DataFrame
        var_dict_map: 可选的变量说明字典
        privacy_settings: 可选的隐私设置字典 {col: {privacy_risk, send_to_ai_mode, ...}}
        config: 可选的用户分析配置（用于确定变量角色）

    Returns:
        变量元数据字典
    """
    if schema_df is None:
        return {}

    metadata: Dict[str, Dict[str, Any]] = {}
    config = config or {}

    target = config.get("target_variable", "")
    group_vars = set(config.get("group_variables", []) or [])
    expl_vars = set(config.get("explanatory_variables", []) or [])

    for _, row in schema_df.iterrows():
        col = str(row.get("column", ""))
        if not col:
            continue

        # Determine role
        role = "none"
        if col == target:
            role = "target"
        elif col in group_vars:
            role = "group"
        elif col in expl_vars:
            role = "predictor"

        # Privacy info
        privacy_risk = str(row.get("privacy_risk", "none"))
        send_mode = str(row.get("send_to_ai_mode", "aggregate_only"))

        if privacy_settings and col in privacy_settings:
            ps = privacy_settings[col]
            privacy_risk = str(ps.get("privacy_risk", privacy_risk))
            send_mode = str(ps.get("send_to_ai_mode", send_mode))

        entry: Dict[str, Any] = {
            "label": get_variable_label(col, schema_df, var_dict_map),
            "raw_name": col,
            "type": str(row.get("inferred_type", "")),
            "description": get_variable_description(col, schema_df, var_dict_map),
            "value_labels": get_value_labels(col, schema_df, var_dict_map),
            "role": role,
            "privacy_risk": privacy_risk,
            "send_to_ai_mode": send_mode,
            "missing_rate": float(row.get("missing_rate", 0)),
            "unique_count": int(row.get("unique_count", 0)),
        }
        metadata[col] = entry

    return metadata


def build_variable_name_map(
    schema_df: pd.DataFrame,
    var_dict_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, str]:
    """构建 {原始列名: 中文显示名} 映射表。

    供 AI prompt 中的 variable_name_map 使用。

    Args:
        schema_df: 变量 schema
        var_dict_map: 可选的变量说明字典

    Returns:
        {raw_name: label, ...}
    """
    name_map: Dict[str, str] = {}
    if schema_df is None:
        return name_map

    for _, row in schema_df.iterrows():
        col = str(row.get("column", ""))
        if not col:
            continue
        name_map[col] = get_variable_label(col, schema_df, var_dict_map)

    return name_map


def get_variable_list_for_ai(
    schema_df: pd.DataFrame,
    var_dict_map: Optional[Dict[str, Dict[str, Any]]] = None,
    privacy_settings: Optional[Dict[str, Dict[str, Any]]] = None,
    include_excluded: bool = False,
) -> List[Dict[str, Any]]:
    """获取适合发送给 AI 的变量列表（遵守隐私设置）。

    Args:
        schema_df: 变量 schema
        var_dict_map: 可选的变量说明字典
        privacy_settings: 可选的隐私设置
        include_excluded: 是否包含被排除发送 AI 的变量（标记为 excluded=True）

    Returns:
        变量信息列表，每个元素为精简的变量摘要 dict
    """
    if schema_df is None:
        return []

    variables = []
    for _, row in schema_df.iterrows():
        col = str(row.get("column", ""))
        if not col:
            continue

        send_mode = str(row.get("send_to_ai_mode", "aggregate_only"))
        privacy_risk = str(row.get("privacy_risk", "none"))

        if privacy_settings and col in privacy_settings:
            ps = privacy_settings[col]
            send_mode = str(ps.get("send_to_ai_mode", send_mode))
            privacy_risk = str(ps.get("privacy_risk", privacy_risk))

        # Skip excluded variables unless explicitly requested
        if send_mode == "exclude" and not include_excluded:
            continue

        entry = {
            "variable": col,
            "label": get_variable_label(col, schema_df, var_dict_map),
            "type": str(row.get("inferred_type", "")),
            "description": get_variable_description(col, schema_df, var_dict_map),
            "value_labels": get_value_labels(col, schema_df, var_dict_map),
            "missing_rate": float(row.get("missing_rate", 0)),
            "unique_count": int(row.get("unique_count", 0)),
        }

        if include_excluded and send_mode == "exclude":
            entry["excluded"] = True

        variables.append(entry)

    return variables
