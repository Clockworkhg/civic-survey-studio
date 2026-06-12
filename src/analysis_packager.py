"""分析结果打包模块 — 通用问卷 / 表格数据分析平台。

将 src/generic_analysis.py 的分析结果打包为结构化 JSON payload，
供 LLM 进行 AI 报告撰写。

设计原则:
  - "固定结构 + 动态内容"：外层结构固定，内部变量名/结果完全来自数据
  - 不写死任何特定数据集的变量名或场景描述
  - AI 只能基于 payload 中实际存在的内容生成报告

隐私原则:
  - 系统识别风险并标记，用户决定是否发送给 AI
  - 人口统计属性（年龄/性别/学历等）默认允许聚合统计和 AI 报告
  - 高风险字段（姓名/手机/身份证等）默认仅本地统计，不发送 AI
  - send_to_ai_mode 控制每个变量的 AI 发送方式

安全原则:
  - 不传原始数据行，只传统计摘要
  - 文本开放题只做简短摘要
  - 频数表最多 20 个类别
  - example_values 最多 5 个
  - JSON 超过 500KB 自动截断并附加警告
  - 支持 masked_examples 模式对示例值进行脱敏
"""

import json
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple

import pandas as pd
import numpy as np

# ── 最大 payload 大小 ──
MAX_PAYLOAD_BYTES = 500 * 1024  # 500 KB
MAX_PAYLOAD_CHARS = 200_000     # ~200K 字符

# ── 频数/示例值上限 ──
MAX_FREQ_ROWS = 20
MAX_EXAMPLE_VALUES = 5
MAX_CORR_PAIRS = 50
MAX_CROSSTAB_CELLS = 15



# ================================================================
# 值脱敏
# ================================================================

def _mask_value(val: Any, privacy_category: str) -> str:
    """根据隐私分类对单个值进行脱敏处理。

    Args:
        val: 原始值
        privacy_category: 隐私分类（contact_info / direct_identifier / location_info / free_text）

    Returns:
        脱敏后的字符串
    """
    s = str(val).strip()
    if not s:
        return s

    if privacy_category == "contact_info":
        # 手机号: 138****1234
        if re.match(r'^1[3-9]\d{9}$', s):
            return s[:3] + "****" + s[-4:]
        # 邮箱: a***@example.com
        if "@" in s:
            parts = s.split("@")
            local = parts[0]
            domain = parts[1] if len(parts) > 1 else ""
            if len(local) <= 2:
                masked_local = local[0] + "***"
            else:
                masked_local = local[0] + "***" + local[-1]
            return masked_local + "@" + domain
        # 通用电话脱敏: 保留后4位
        if re.match(r'^[\d\-+.() ]{7,}$', s):
            digits = re.sub(r'\D', '', s)
            if len(digits) >= 7:
                return "***" + digits[-4:]
        # 微信/QQ: 脱敏
        return s[:2] + "***" if len(s) > 3 else "***"

    elif privacy_category == "direct_identifier":
        # 身份证: 110101****1234
        if re.match(r'^\d{17}[\dXx]$', s):
            return s[:6] + "****" + s[-4:]
        # 中文姓名: 张**
        if re.match(r'^[一-鿿]{2,4}$', s):
            return s[0] + "**" if len(s) >= 2 else s[0] + "*"
        # 英文姓名: J***
        if re.match(r'^[A-Za-z]+$', s):
            return s[0] + "***"
        # 学号/工号: 保留前2后2
        if len(s) >= 6:
            return s[:2] + "****" + s[-2:]
        return "***"

    elif privacy_category == "location_info":
        # 详细地址脱敏: 保留到街道/区级别，去掉门牌号
        if len(s) > 10:
            # 尝试去掉最后的数字/室/号
            s = re.sub(r'[\d]+号.*$', '**号', s)
            s = re.sub(r'[\d]+室.*$', '**室', s)
            s = re.sub(r'[\d]+楼[\d]*$', '**楼', s)
        return s

    elif privacy_category == "free_text":
        # 文本截断
        if len(s) > 50:
            return s[:47] + "..."
        return s

    elif privacy_category == "financial":
        # 银行卡/账号: ****1234
        digits = re.sub(r'\D', '', s)
        if len(digits) >= 8:
            return "****" + digits[-4:]
        return "***"

    # 默认脱敏
    if len(s) > 6:
        return s[:3] + "***"
    return "***"


def _apply_masking_to_values(values: List[str], privacy_category: str) -> List[str]:
    """对一组值列表进行批量脱敏。"""
    return [_mask_value(v, privacy_category) for v in values]


# ================================================================
# 从 schema 读取隐私设置
# ================================================================

def _read_privacy_settings(schema_df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """从 schema DataFrame 读取每个变量的隐私设置。

    Returns:
        {column: {privacy_risk, privacy_category, allow_local_stats,
                  allow_as_group_variable, allow_in_model,
                  allow_send_to_ai, send_to_ai_mode, user_confirmed_privacy}}
    """
    settings = {}
    privacy_cols = [
        "privacy_risk", "privacy_category",
        "allow_local_stats", "allow_as_group_variable",
        "allow_in_model", "allow_send_to_ai",
        "send_to_ai_mode", "user_confirmed_privacy",
    ]
    for _, row in schema_df.iterrows():
        col = row["column"]
        entry = {}
        for pc in privacy_cols:
            if pc in schema_df.columns:
                val = row[pc]
                if isinstance(val, (np.bool_,)):
                    val = bool(val)
                entry[pc] = val
            else:
                # 兼容旧版 schema（无隐私列）
                entry[pc] = _default_privacy_value(pc)
        settings[col] = entry
    return settings


def _default_privacy_value(col_name: str) -> Any:
    """为缺少隐私列的旧版 schema 提供默认值。"""
    defaults = {
        "privacy_risk": "none",
        "privacy_category": "none",
        "allow_local_stats": True,
        "allow_as_group_variable": True,
        "allow_in_model": True,
        "allow_send_to_ai": True,
        "send_to_ai_mode": "aggregate_only",
        "user_confirmed_privacy": False,
    }
    return defaults.get(col_name, "none")

# ================================================================
# 主入口
# ================================================================

def build_analysis_payload(
    df: pd.DataFrame,
    schema_df: pd.DataFrame,
    config: Dict[str, Any],
    analysis_results: Dict[str, Any],
    quality: Optional[Dict[str, Any]] = None,
    chart_summaries: Optional[List[Dict[str, Any]]] = None,
    selected_sheet: str = "",
    file_type: str = "",
    research_subject: str = "",
    report_style: str = "standard",
    report_length: str = "standard",
    var_dict_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """构建发送给 LLM 的完整分析 payload。

    外层结构固定（8 个 section），内部变量名、分析类型、分析结果
    完全根据用户上传的数据动态生成。

    Args:
        df: 原始数据（仅用于提取元信息，不包含原始行数据）
        schema_df: 变量类型推断结果
        config: 分析配置
        analysis_results: run_full_analysis 的输出
        quality: 数据质量报告
        chart_summaries: 图表摘要列表
        selected_sheet: 选中的工作表名
        file_type: 文件类型（xlsx / csv）
        research_subject: 研究对象（由用户输入，如为空则自动推断）
        report_style: 报告风格
        report_length: 报告长度

    Returns:
        结构化 JSON payload（8 个 section）
    """
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ── 从 schema 读取隐私设置 ──
    privacy_settings = _read_privacy_settings(schema_df)

    # ── 类型/中文名查找表 ──
    type_map: Dict[str, str] = {}
    cn_map: Dict[str, str] = {}
    for _, row in schema_df.iterrows():
        col = row["column"]
        type_map[col] = row["inferred_type"]
        cn_map[col] = row.get("display_name", "") or col

    # ── 变量角色分类 ──
    id_vars = _get_vars_by_role(schema_df, "id")
    text_vars = _get_vars_by_role(schema_df, "skip") + _get_vars_by_type(schema_df, "text")
    datetime_vars = _get_vars_by_type(schema_df, "datetime")

    # ── 基于隐私设置的变量分类 ──
    # 高风险且不可发送 → excluded_sensitive
    # 中高风险但允许聚合 → privacy_restricted
    excluded_sensitive = []
    privacy_restricted = []
    for col in df.columns:
        ps = privacy_settings.get(col, {})
        risk = ps.get("privacy_risk", "none")
        allow_ai = ps.get("allow_send_to_ai", True)
        send_mode = ps.get("send_to_ai_mode", "aggregate_only")
        if risk == "high" and not allow_ai:
            excluded_sensitive.append(col)
        elif risk in ("medium", "high") and send_mode == "exclude":
            excluded_sensitive.append(col)
        elif risk in ("medium", "high"):
            privacy_restricted.append(col)

    # ── 目标变量信息 ──
    target = config.get("target_variable", "")
    target_type = ""
    if target:
        target_row = schema_df[schema_df["column"] == target]
        if len(target_row) > 0:
            target_type = target_row.iloc[0]["inferred_type"]

    # ── 收集警告 ──
    all_warnings: List[str] = list(analysis_results.get("warnings", []) or [])

    # 缺失值警告
    high_missing = _get_high_missing_vars(schema_df, threshold_pct=10.0)
    if high_missing:
        all_warnings.append(f"以下变量缺失率超过 10%：{', '.join(high_missing)}")

    # 隐私风险警告（新语言：不强制排除，而是说明当前处理方式）
    for col in excluded_sensitive:
        ps = privacy_settings.get(col, {})
        risk = ps.get("privacy_risk", "high")
        cat = ps.get("privacy_category", "unknown")
        cn = cn_map.get(col, col)
        all_warnings.append(
            f"变量「{cn}」被识别为{_risk_label(risk)}隐私风险字段"
            f"（{_cat_label(cat)}），当前仅用于本地统计，"
            f"未向 AI 发送原始明细。如需进一步分析，可在隐私与变量使用设置中手动调整。"
        )
    for col in privacy_restricted:
        ps = privacy_settings.get(col, {})
        risk = ps.get("privacy_risk", "medium")
        cat = ps.get("privacy_category", "unknown")
        cn = cn_map.get(col, col)
        all_warnings.append(
            f"变量「{cn}」被识别为{_risk_label(risk)}隐私风险字段"
            f"（{_cat_label(cat)}），当前以聚合统计形式纳入分析。"
            f"如需调整，可在隐私设置中修改。"
        )

    # 二分类目标变量提示
    if target and target_type == "categorical":
        unique_n = int(df[target].dropna().nunique())
        if unique_n == 2:
            all_warnings.append(
                f"目标变量「{cn_map.get(target, target)}」为二分类变量，"
                "不适合普通线性回归，建议使用逻辑回归或卡方检验。"
            )

    # ID 变量排除提示
    if id_vars:
        all_warnings.append(
            f"以下变量被识别为 ID 变量，已自动排除统计分析：{', '.join(id_vars)}"
        )

    # 文本变量提示
    if text_vars:
        all_warnings.append(
            f"以下变量为文本/开放题，未纳入统计模型，仅提供简要摘要：{', '.join(text_vars)}"
        )

    # 统计≠因果
    all_warnings.append(
        "本报告中的统计关联结果不等于因果关系。"
        "所有结论应结合领域知识和实际调研背景进行综合判断。"
    )

    # 去重
    all_warnings = list(dict.fromkeys(all_warnings))

    # ── 构建 analysis_plan ──
    analysis_plan = _build_analysis_plan(
        schema_df=schema_df,
        config=config,
        target_type=target_type,
        type_map=type_map,
        cn_map=cn_map,
        df=df,
    )

    # ── 构建 plan 查找表 ──
    plan_lookup: Dict[str, Dict[str, Any]] = {}
    for p in analysis_plan:
        plan_lookup[p["analysis_id"]] = p

    # ── 构建 analysis_results（统一列表） ──
    unified_results = _build_analysis_results(
        analysis_results=analysis_results,
        schema_df=schema_df,
        config=config,
        type_map=type_map,
        cn_map=cn_map,
        plan_lookup=plan_lookup,
        privacy_settings=privacy_settings,
    )

    # ── 更新 plan status ──
    completed_ids = {r["analysis_id"] for r in unified_results}
    for p in analysis_plan:
        if p["analysis_id"] in completed_ids:
            p["status"] = "completed"

    # ── v0.1.0 Phase 3: 变量元数据（统一来源，包含中文名/用途/取值标签/角色）──
    from src.variable_metadata import build_variable_metadata_map, build_variable_name_map
    _var_metadata = build_variable_metadata_map(
        schema_df, var_dict_map=var_dict_map, privacy_settings=privacy_settings, config=config,
    )
    _var_name_map = build_variable_name_map(schema_df, var_dict_map=var_dict_map)
    # 合并 variable_name_map 到 cn_map（优先使用元数据模块的结果）
    cn_map = {**{col: _var_metadata[col]["label"] for col in _var_metadata}, **cn_map}

    # ── 组装 payload ──
    payload = {
        "project_meta": _package_project_meta(
            config=config,
            generated_at=generated_at,
            research_subject=research_subject,
            report_style=report_style,
            report_length=report_length,
            cn_map=cn_map,
            variable_name_map=_var_name_map,
        ),
        "data_overview": _package_data_overview(df, quality, selected_sheet, file_type),
        "variable_schema": _enrich_variable_schema_with_metadata(
            _package_variable_schema(schema_df, privacy_settings),
            _var_metadata,
        ),
        "variables": _var_metadata,
        "user_analysis_config": _package_user_config(
            config=config,
            target_type=target_type,
            id_vars=id_vars,
            text_vars=text_vars,
            datetime_vars=datetime_vars,
            excluded_sensitive_vars=excluded_sensitive,
            privacy_restricted_vars=privacy_restricted,
        ),
        "analysis_plan": analysis_plan,
        "analysis_results": unified_results,
        "chart_summaries": _package_chart_summaries(chart_summaries),
        "warnings": all_warnings,
    }

    # ── 大小检查 ──
    json_str = _safe_json_dumps(payload)
    if len(json_str) > MAX_PAYLOAD_CHARS:
        payload = _truncate_payload(payload)
        payload["_truncated"] = True
        payload["_truncation_note"] = (
            f"分析结果过大，已自动截断至约 {MAX_PAYLOAD_CHARS // 1000}K 字符。"
            "如需完整数据，请缩减变量范围或分析配置。"
        )

    return payload


# ================================================================
# Section: analysis_plan（自动生成分析计划）
# ================================================================

def _build_analysis_plan(
    schema_df: pd.DataFrame,
    config: Dict[str, Any],
    target_type: str,
    type_map: Dict[str, str],
    cn_map: Dict[str, str],
    df: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """根据变量类型和用户配置，自动生成分析计划列表。

    每项计划包含：
        analysis_id, analysis_type, variables, display_names,
        method, reason, status (planned/skipped/completed),
        skipped_reason (仅 status=skipped 时)
    """
    plan: List[Dict[str, Any]] = []

    target = config.get("target_variable", "")
    group_vars = config.get("group_variables", []) or []
    expl_vars = config.get("explanatory_variables", []) or []

    # ── 单变量分析计划 ──
    for _, row in schema_df.iterrows():
        col = row["column"]
        vtype = row["inferred_type"]
        role = row.get("suggested_role", "")
        cn = cn_map.get(col, col)

        if vtype in ("categorical", "ordinal"):
            plan.append({
                "analysis_id": f"univariate_freq_{col}",
                "analysis_type": "categorical_frequency",
                "variables": [col],
                "display_names": [cn],
                "method": "frequency_distribution",
                "reason": f"对分类/有序变量「{cn}」进行频数分布分析，了解各类别的样本分布情况。",
                "status": "planned",
                "skipped_reason": None,
            })
        elif vtype == "numeric":
            plan.append({
                "analysis_id": f"univariate_desc_{col}",
                "analysis_type": "numeric_descriptive",
                "variables": [col],
                "display_names": [cn],
                "method": "descriptive_statistics",
                "reason": f"对数值变量「{cn}」进行描述统计，了解集中趋势和离散程度。",
                "status": "planned",
                "skipped_reason": None,
            })
        elif vtype == "text":
            plan.append({
                "analysis_id": f"univariate_text_{col}",
                "analysis_type": "text_summary",
                "variables": [col],
                "display_names": [cn],
                "method": "text_length_summary",
                "reason": f"文本变量「{cn}」仅提供简短摘要（唯一值数、平均长度），不进行深度文本分析。",
                "status": "planned",
                "skipped_reason": None,
            })
        elif role == "id":
            plan.append({
                "analysis_id": f"skip_id_{col}",
                "analysis_type": "skipped",
                "variables": [col],
                "display_names": [cn],
                "method": None,
                "reason": f"「{cn}」被识别为 ID 变量，每个值唯一，不适合统计分析。",
                "status": "skipped",
                "skipped_reason": "ID 变量，每个样本唯一，无统计意义。",
            })
        elif vtype == "datetime":
            plan.append({
                "analysis_id": f"skip_datetime_{col}",
                "analysis_type": "skipped",
                "variables": [col],
                "display_names": [cn],
                "method": None,
                "reason": f"「{cn}」为日期时间变量，当前版本不自动进行时间序列分析。",
                "status": "skipped",
                "skipped_reason": "日期时间变量，暂不支持自动分析。",
            })

    # ── 双变量：分组变量 × 目标变量 ──
    if target and group_vars:
        for gv in group_vars:
            if gv not in df.columns:
                continue
            gv_type = type_map.get(gv, "")
            gv_cn = cn_map.get(gv, gv)
            target_cn = cn_map.get(target, target)

            if gv_type in ("categorical", "ordinal") and target_type in ("categorical", "ordinal"):
                plan.append({
                    "analysis_id": f"bivariate_group_{gv}__{target}",
                    "analysis_type": "categorical_categorical_chi_square",
                    "variables": [gv, target],
                    "display_names": [gv_cn, target_cn],
                    "method": "chi_square_test",
                    "reason": (
                        f"检验「{gv_cn}」与「{target_cn}」两个分类变量之间是否存在统计关联。"
                    ),
                    "status": "planned",
                    "skipped_reason": None,
                })
            elif gv_type in ("categorical", "ordinal") and target_type in ("numeric", "ordinal"):
                plan.append({
                    "analysis_id": f"bivariate_group_{gv}__{target}",
                    "analysis_type": "categorical_numeric_group_compare",
                    "variables": [gv, target],
                    "display_names": [gv_cn, target_cn],
                    "method": "ANOVA_or_t_test",
                    "reason": (
                        f"比较不同「{gv_cn}」组别在「{target_cn}」上的均值差异，"
                        "判断组间差异是否具有统计显著性。"
                    ),
                    "status": "planned",
                    "skipped_reason": None,
                })
            else:
                plan.append({
                    "analysis_id": f"bivariate_group_{gv}__{target}",
                    "analysis_type": "unsupported_pair",
                    "variables": [gv, target],
                    "display_names": [gv_cn, target_cn],
                    "method": None,
                    "reason": f"「{gv_cn}」（{gv_type}）与「{target_cn}」（{target_type}）的组合暂不支持自动分析。",
                    "status": "skipped",
                    "skipped_reason": f"变量类型组合（{gv_type} × {target_type}）不在自动分析范围内。",
                })

    # ── 双变量：解释变量之间的相关 ──
    numeric_vars = [
        v for v in expl_vars
        if type_map.get(v) in ("numeric", "ordinal") and v in df.columns
    ]
    if len(numeric_vars) >= 2:
        for i, v1 in enumerate(numeric_vars):
            for v2 in numeric_vars[i + 1:]:
                v1_cn = cn_map.get(v1, v1)
                v2_cn = cn_map.get(v2, v2)
                plan.append({
                    "analysis_id": f"bivariate_corr_{v1}__{v2}",
                    "analysis_type": "numeric_numeric_correlation",
                    "variables": [v1, v2],
                    "display_names": [v1_cn, v2_cn],
                    "method": "pearson_spearman",
                    "reason": (
                        f"考察「{v1_cn}」与「{v2_cn}」之间的线性相关和非线性单调关系。"
                    ),
                    "status": "planned",
                    "skipped_reason": None,
                })

    # 解释变量与目标变量的相关
    if target and target_type in ("numeric", "ordinal") and numeric_vars:
        target_cn = cn_map.get(target, target)
        for ev in numeric_vars:
            if ev == target:
                continue
            ev_cn = cn_map.get(ev, ev)
            plan.append({
                "analysis_id": f"bivariate_corr_{ev}__{target}",
                "analysis_type": "numeric_numeric_correlation",
                "variables": [ev, target],
                "display_names": [ev_cn, target_cn],
                "method": "pearson_spearman",
                "reason": (
                    f"考察「{ev_cn}」与目标变量「{target_cn}」之间的相关关系。"
                ),
                "status": "planned",
                "skipped_reason": None,
            })

    # ── 多变量分析 ──
    if target and expl_vars:
        if target_type in ("numeric", "ordinal"):
            valid_predictors = [
                v for v in expl_vars
                if v in df.columns and type_map.get(v) in ("numeric", "ordinal")
            ]
            target_cn = cn_map.get(target, target)
            if len(valid_predictors) >= 2:
                pred_cn = [cn_map.get(v, v) for v in valid_predictors]
                plan.append({
                    "analysis_id": "multivariate_regression",
                    "analysis_type": "linear_regression",
                    "variables": [target] + valid_predictors,
                    "display_names": [target_cn] + pred_cn,
                    "method": "OLS",
                    "reason": (
                        f"以「{target_cn}」为因变量，{len(valid_predictors)} 个数值变量为自变量，"
                        "建立多元线性回归模型，考察各变量的独立贡献。"
                    ),
                    "status": "planned",
                    "skipped_reason": None,
                })
            elif len(valid_predictors) == 1:
                plan.append({
                    "analysis_id": "multivariate_regression",
                    "analysis_type": "linear_regression",
                    "variables": [target] + valid_predictors,
                    "display_names": [target_cn] + [cn_map.get(valid_predictors[0], valid_predictors[0])],
                    "method": "OLS",
                    "reason": "解释变量不足（至少需要 2 个），跳过回归分析。",
                    "status": "skipped",
                    "skipped_reason": "解释变量不足（至少需要 2 个数值型变量）。",
                })
        elif target_type == "binary":
            valid_predictors = [
                v for v in expl_vars
                if v in df.columns and type_map.get(v) in ("numeric", "ordinal")
            ]
            target_cn = cn_map.get(target, target)
            if len(valid_predictors) >= 1:
                pred_cn = [cn_map.get(v, v) for v in valid_predictors]
                plan.append({
                    "analysis_id": "multivariate_logistic",
                    "analysis_type": "logistic_regression",
                    "variables": [target] + valid_predictors,
                    "display_names": [target_cn] + pred_cn,
                    "method": "Logit",
                    "reason": (
                        f"以「{target_cn}」（二分类）为因变量，{len(valid_predictors)} 个变量为自变量，"
                        "建立二元逻辑回归模型，考察各变量对目标事件发生几率的预测作用。"
                    ),
                    "status": "planned",
                    "skipped_reason": None,
                })
            else:
                plan.append({
                    "analysis_id": "multivariate_logistic",
                    "analysis_type": "logistic_regression",
                    "variables": [target],
                    "display_names": [target_cn],
                    "method": "Logit",
                    "reason": "解释变量不足（需至少 1 个数值型或有序变量），跳过逻辑回归。",
                    "status": "skipped",
                    "skipped_reason": "解释变量不足（需至少 1 个数值型/有序变量）。",
                })
        elif target_type == "categorical":
            unique_n = int(df[target].dropna().nunique())
            target_cn = cn_map.get(target, target)
            if unique_n == 2:
                plan.append({
                    "analysis_id": "multivariate_logistic",
                    "analysis_type": "logistic_regression",
                    "variables": [target],
                    "display_names": [target_cn],
                    "method": "Logit",
                    "reason": (
                        f"目标变量「{target_cn}」为二分类变量（categorical 类型），"
                        "适合逻辑回归分析。建议在变量设置中将该变量标记为「二分类」类型。"
                    ),
                    "status": "skipped",
                    "skipped_reason": "二分类变量需标记为 binary 类型以启用逻辑回归。",
                })

    return plan


# ================================================================
# Section: analysis_results（统一结果列表）
# ================================================================

def _build_analysis_results(
    analysis_results: Dict[str, Any],
    schema_df: pd.DataFrame,
    config: Dict[str, Any],
    type_map: Dict[str, str],
    cn_map: Dict[str, str],
    plan_lookup: Dict[str, Dict[str, Any]],
    privacy_settings: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """将所有分析结果转换为统一列表格式。

    替代原来的 _package_univariate / _package_bivariate / _package_multivariate。
    每个结果条目包含：
        analysis_id, analysis_type, variables, display_names,
        variable_types, method, result, p_value?, significant?,
        interpretation_hint, limitations
    """
    if privacy_settings is None:
        privacy_settings = {}
    results: List[Dict[str, Any]] = []

    # ── 单变量结果 ──
    univariate = analysis_results.get("univariate", {})
    if univariate:
        for col, result in univariate.items():
            if not isinstance(result, dict):
                continue
            vtype = type_map.get(col, "")
            cn = cn_map.get(col, col)
            ps = privacy_settings.get(col, {})
            send_mode = ps.get("send_to_ai_mode", "aggregate_only")
            privacy_cat = ps.get("privacy_category", "none")

            # 确定 analysis_id
            if vtype in ("categorical", "ordinal"):
                aid = f"univariate_freq_{col}"
            elif vtype == "numeric":
                aid = f"univariate_desc_{col}"
            elif vtype == "text":
                aid = f"univariate_text_{col}"
            else:
                aid = f"univariate_skip_{col}"

            entry = _format_univariate_entry(
                col=col, cn=cn, vtype=vtype, result=result, analysis_id=aid,
                send_to_ai_mode=send_mode, privacy_category=privacy_cat,
            )
            if entry:
                results.append(entry)

    # ── 双变量：分组比较 ──
    biv_group = analysis_results.get("bivariate_group", {})
    if biv_group:
        for key, result in biv_group.items():
            if not isinstance(result, dict):
                continue
            aid = f"bivariate_group_{key}"
            entry = _format_bivariate_group_entry(key=key, result=result, aid=aid)
            if entry:
                results.append(entry)

    # ── 双变量：相关分析 ──
    biv_corr = analysis_results.get("bivariate_corr", {})
    if biv_corr:
        corr_entries = []
        for key, result in biv_corr.items():
            if not isinstance(result, dict):
                continue
            aid = f"bivariate_corr_{key}"
            entry = _format_bivariate_corr_entry(key=key, result=result, aid=aid)
            if entry:
                corr_entries.append(entry)

        # 按 |r| 降序排列，最多保留 MAX_CORR_PAIRS 对
        corr_entries.sort(
            key=lambda x: abs(x.get("result", {}).get("correlation") or 0),
            reverse=True,
        )
        results.extend(corr_entries[:MAX_CORR_PAIRS])

    # ── 多变量：回归 ──
    multi = analysis_results.get("multivariate")
    if multi is not None and isinstance(multi, dict):
        entry = _format_multivariate_entry(
            multi=multi, config=config, cn_map=cn_map,
        )
        if entry:
            results.append(entry)

    return results


# ── 单变量条目格式化 ──

def _format_univariate_entry(
    col: str,
    cn: str,
    vtype: str,
    result: Dict[str, Any],
    analysis_id: str,
    send_to_ai_mode: str = "aggregate_only",
    privacy_category: str = "none",
) -> Optional[Dict[str, Any]]:
    """将单个单变量分析结果格式化为统一条目。

    Args:
        send_to_ai_mode: 控制 AI 发送方式
            - exclude: 不发送频数类别明细（仅保留聚合计数）
            - masked_examples: 类别标签脱敏
            - aggregate_only: 保留聚合统计（默认）
            - full: 完整发送
        privacy_category: 隐私分类，用于脱敏模式
    """
    # 出错
    if "error" in result:
        return {
            "analysis_id": analysis_id,
            "analysis_type": _map_univariate_type(vtype),
            "variables": [col],
            "display_names": [cn],
            "variable_types": [vtype],
            "method": None,
            "result": {"error": str(result["error"])[:300]},
            "p_value": None,
            "significant": None,
            "interpretation_hint": "分析过程出错，无法提供解读。",
            "limitations": ["分析执行失败，结果不可用。"],
        }

    # 被跳过
    if "info" in result:
        return {
            "analysis_id": analysis_id,
            "analysis_type": "skipped",
            "variables": [col],
            "display_names": [cn],
            "variable_types": [vtype],
            "method": None,
            "result": {"reason": result["info"]},
            "p_value": None,
            "significant": None,
            "interpretation_hint": f"变量「{cn}」被跳过：{result['info']}",
            "limitations": [],
        }

    base = {
        "analysis_id": analysis_id,
        "variables": [col],
        "display_names": [cn],
        "variable_types": [vtype],
    }

    if vtype == "numeric":
        return {
            **base,
            "analysis_type": "numeric_descriptive",
            "method": "descriptive_statistics",
            "result": {
                "count": result.get("样本量"),
                "mean": _float_val(result.get("均值")),
                "std": _float_val(result.get("标准差")),
                "median": _float_val(result.get("中位数")),
                "min": _float_val(result.get("最小值")),
                "max": _float_val(result.get("最大值")),
                "q25": _float_val(result.get("Q25")),
                "q75": _float_val(result.get("Q75")),
                "skewness": _float_val(result.get("偏度")),
                "kurtosis": _float_val(result.get("峰度")),
            },
            "p_value": None,
            "significant": None,
            "interpretation_hint": (
                "描述统计反映样本在该变量上的集中趋势（均值、中位数）和离散程度（标准差）。"
                "偏度接近 0 表示分布对称，峰度反映分布的厚尾程度。"
            ),
            "limitations": [
                "描述统计仅反映样本特征，不能直接推广到总体。",
                "均值和标准差对极端值敏感，建议结合中位数和四分位数综合判断。",
            ],
        }

    elif vtype in ("categorical", "ordinal"):
        # 根据 send_to_ai_mode 决定如何处理频数表
        freq_table = _freq_table(result.get("频数表"), max_rows=MAX_FREQ_ROWS)
        mode_val = _safe_str(result.get("众数"))

        if send_to_ai_mode == "exclude":
            # 不发送类别明细，仅保留聚合计数
            freq_table = None
            mode_val = ""  # 不发送众数标签
        elif send_to_ai_mode == "masked_examples" and freq_table:
            # 对类别标签进行脱敏
            freq_table = [
                {**row, "category": _mask_value(row.get("category", ""), privacy_category)}
                for row in freq_table
            ]
            mode_val = _mask_value(mode_val, privacy_category)

        entry = {
            **base,
            "analysis_type": "categorical_frequency",
            "method": "frequency_distribution",
            "result": {
                "valid_count": result.get("有效样本"),
                "category_count": result.get("类别数"),
                "mode": mode_val,
                "mode_percentage": _float_val(result.get("众数占比")) if send_to_ai_mode != "exclude" else None,
                "categories": freq_table,
            },
            "p_value": None,
            "significant": None,
            "interpretation_hint": (
                "频数分布反映各类别的样本数量及占比。"
                "可重点关注占比最高和最低的类别。"
            ),
            "limitations": [
                "频数分布仅描述样本构成，不代表总体比例。",
                "类别过多时仅展示前 20 个类别。",
            ],
        }
        if send_to_ai_mode == "exclude":
            entry["result"]["_privacy_note"] = "该变量因隐私设置未向 AI 发送类别明细。"
        if vtype == "ordinal":
            entry["result"]["positional_mean"] = _float_val(result.get("均值"))
            entry["result"]["positional_median"] = _float_val(result.get("中位数"))
        return entry

    elif vtype == "text":
        return {
            **base,
            "analysis_type": "text_summary",
            "method": "text_length_summary",
            "result": {
                "non_null_count": result.get("有效样本", 0),
                "unique_count": result.get("类别数", 0),
                "avg_length_approx": _estimate_text_length(result),
            },
            "p_value": None,
            "significant": None,
            "interpretation_hint": (
                "文本变量仅提供基本摘要，不进行内容分析。"
                "如需深入分析文本内容，建议使用专门的文本分析工具。"
            ),
            "limitations": [
                "仅统计文本长度和唯一值数量，不分析文本语义内容。",
                "文本变量的统计意义有限，主要用于数据质量评估。",
            ],
        }

    # fallback
    return {
        **base,
        "analysis_type": "skipped",
        "method": None,
        "result": {"note": str(result)[:200]},
        "p_value": None,
        "significant": None,
        "interpretation_hint": "",
        "limitations": [],
    }


def _map_univariate_type(vtype: str) -> str:
    """单变量类型映射为 analysis_type。"""
    if vtype in ("categorical", "ordinal"):
        return "categorical_frequency"
    elif vtype == "numeric":
        return "numeric_descriptive"
    elif vtype == "text":
        return "text_summary"
    return "skipped"


# ── 双变量分组比较条目格式化 ──

def _format_bivariate_group_entry(
    key: str,
    result: Dict[str, Any],
    aid: str,
) -> Optional[Dict[str, Any]]:
    """将分组比较结果格式化为统一条目。"""
    # 解析变量
    parts = key.split("__")
    var1 = parts[0] if len(parts) > 0 else ""
    var2 = parts[1] if len(parts) > 1 else ""

    # 出错
    if "error" in result:
        return {
            "analysis_id": aid,
            "analysis_type": "group_comparison",
            "variables": [var1, var2],
            "display_names": [var1, var2],
            "variable_types": [],
            "method": None,
            "result": {"error": str(result["error"])[:300]},
            "p_value": None,
            "significant": None,
            "interpretation_hint": "分析过程出错，无法提供解读。",
            "limitations": ["分析执行失败，结果不可用。"],
        }

    # 被跳过
    if "info" in result:
        return {
            "analysis_id": aid,
            "analysis_type": "skipped",
            "variables": [var1, var2],
            "display_names": [var1, var2],
            "variable_types": [],
            "method": None,
            "result": {"reason": result["info"]},
            "p_value": None,
            "significant": None,
            "interpretation_hint": f"该组比较被跳过：{result['info']}",
            "limitations": [],
        }

    # 卡方检验
    if "chi2" in result:
        p_val = _float_val(result.get("p_value"))
        sig = result.get("significant", False)
        return {
            "analysis_id": aid,
            "analysis_type": "categorical_categorical_chi_square",
            "variables": [var1, var2],
            "display_names": [
                _safe_str(result.get("cn_row", var1)),
                _safe_str(result.get("cn_col", var2)),
            ],
            "variable_types": ["categorical", "categorical"],
            "method": "chi_square_test",
            "result": {
                "chi2": _float_val(result.get("chi2")),
                "p_value": p_val,
                "dof": result.get("df") or result.get("自由度"),
                "significant": sig,
                "crosstab_preview": _summarize_crosstab(result.get("crosstab")),
            },
            "p_value": p_val,
            "significant": sig,
            "interpretation_hint": (
                "卡方检验只能说明两个分类变量之间存在统计关联，"
                "不能说明因果关系或关联方向。"
                "结合交叉表可了解关联的具体模式。"
            ),
            "limitations": [
                "卡方检验要求期望频数不宜过小（通常要求 ≥5），小样本时结果可能不可靠。",
                "显著结果仅表示存在关联，不代表关联强度很大。",
                "相关关系不等于因果关系。",
            ],
        }

    # ANOVA / t-test
    if "f_statistic" in result or "F_statistic" in result or "f_stat" in result or "F_stat" in result:
        p_val = _float_val(result.get("p_value"))
        sig = result.get("significant", False)
        group_stats = result.get("group_stats", {})

        # 提取分组均值
        group_means: List[Dict[str, Any]] = []
        if isinstance(group_stats, dict):
            means_dict = group_stats.get("均值", {})
            if isinstance(means_dict, dict):
                for grp, mean_val in means_dict.items():
                    group_means.append({
                        "group": str(grp),
                        "mean": _float_val(mean_val),
                    })

        return {
            "analysis_id": aid,
            "analysis_type": "categorical_numeric_group_compare",
            "variables": [var1, var2],
            "display_names": [
                _safe_str(result.get("cn_cat", var1)),
                _safe_str(result.get("cn_num", var2)),
            ],
            "variable_types": ["categorical", "numeric"],
            "method": result.get("test_type", "ANOVA"),
            "result": {
                "group_means": group_means,
                "f_statistic": _float_val(
                    result.get("f_statistic")
                    or result.get("F_statistic")
                    or result.get("f_stat")
                    or result.get("F_stat")
                ),
                "p_value": p_val,
                "significant": sig,
            },
            "p_value": p_val,
            "significant": sig,
            "interpretation_hint": (
                "分组比较检验不同组别在数值变量上的均值是否存在统计显著差异。"
                "显著结果表示至少有一组与其他组不同，但不能说明具体是哪两组不同。"
                "事后检验（post-hoc）可进一步明确差异来源。"
            ),
            "limitations": [
                "ANOVA 假设各组方差齐性和正态性，若假设不满足结果可能不稳健。",
                "显著结果仅能说明组间存在差异，不能推断因果方向。",
                "分组均值的差异大小（效应量）比 p 值更能反映实际意义。",
            ],
        }

    # 未知结构
    return {
        "analysis_id": aid,
        "analysis_type": "group_comparison",
        "variables": [var1, var2],
        "display_names": [var1, var2],
        "variable_types": [],
        "method": "unknown",
        "result": {"note": "分析结果结构未知，无法标准化展示。"},
        "p_value": None,
        "significant": None,
        "interpretation_hint": "",
        "limitations": [],
    }


# ── 双变量相关条目格式化 ──

def _format_bivariate_corr_entry(
    key: str,
    result: Dict[str, Any],
    aid: str,
) -> Optional[Dict[str, Any]]:
    """将相关分析结果格式化为统一条目。"""
    parts = key.split("__")
    var1 = parts[0] if len(parts) > 0 else ""
    var2 = parts[1] if len(parts) > 1 else ""

    if "error" in result:
        return {
            "analysis_id": aid,
            "analysis_type": "numeric_numeric_correlation",
            "variables": [var1, var2],
            "display_names": [var1, var2],
            "variable_types": ["numeric", "numeric"],
            "method": "pearson_spearman",
            "result": {"error": str(result["error"])[:300]},
            "p_value": None,
            "significant": None,
            "interpretation_hint": "分析过程出错，无法提供解读。",
            "limitations": ["分析执行失败，结果不可用。"],
        }

    pr = _float_val(result.get("pearson_r"))
    pp = _float_val(result.get("pearson_p"))
    sr = _float_val(result.get("spearman_rho"))
    sp = _float_val(result.get("spearman_p"))
    sig = _is_sig(pp)

    return {
        "analysis_id": aid,
        "analysis_type": "numeric_numeric_correlation",
        "variables": [var1, var2],
        "display_names": [
            _safe_str(result.get("cn1", var1)),
            _safe_str(result.get("cn2", var2)),
        ],
        "variable_types": ["numeric", "numeric"],
        "method": "pearson_spearman",
        "result": {
            "pearson_r": pr,
            "pearson_p_value": pp,
            "pearson_significant": sig,
            "spearman_rho": sr,
            "spearman_p_value": sp,
            "spearman_significant": _is_sig(sp),
            "sample_size": result.get("n"),
            "strength": result.get("pearson_interpretation", ""),
        },
        "p_value": pp,
        "significant": sig,
        "interpretation_hint": (
            "Pearson 相关系数衡量线性关系的强度和方向（正/负），"
            "Spearman 秩相关系数衡量单调关系，对异常值更稳健。"
            "相关关系不等于因果关系：两变量相关可能是第三方因素导致，"
            "也可能是反向因果。报告时应使用「相关」「正相关」「负相关」等措辞，"
            "避免使用「导致」「引起」「影响」等因果性语言。"
        ),
        "limitations": [
            "Pearson 相关仅能检测线性关系，非线性关系可能被遗漏。",
            "相关系数对极端值敏感。",
            "相关关系不等于因果关系。",
            "样本量过小时相关系数估计不稳定。",
        ],
    }


# ── 多变量回归条目格式化 ──

def _format_multivariate_entry(
    multi: Dict[str, Any],
    config: Dict[str, Any],
    cn_map: Dict[str, str],
) -> Optional[Dict[str, Any]]:
    """将多元回归（OLS 或 Logit）结果格式化为统一条目。"""
    target = config.get("target_variable", "")
    expl_vars = config.get("explanatory_variables", []) or []
    target_cn = cn_map.get(target, target)

    # 检测回归类型：有 pseudo_r_squared → 逻辑回归；有 r_squared → OLS
    is_logistic = "pseudo_r_squared" in multi
    method = "Logit" if is_logistic else "OLS"
    analysis_type = "logistic_regression" if is_logistic else "linear_regression"

    # 回归出错
    if "error" in multi:
        return {
            "analysis_id": "multivariate_regression",
            "analysis_type": analysis_type,
            "variables": [target] + expl_vars,
            "display_names": [target_cn] + [cn_map.get(v, v) for v in expl_vars],
            "variable_types": [],
            "method": method,
            "result": {"error": str(multi["error"])[:300]},
            "p_value": None,
            "significant": None,
            "interpretation_hint": "回归分析执行失败，无法提供解读。",
            "limitations": ["分析执行失败，结果不可用。"],
        }

    # 提取系数表（OLS 和 Logit 通用）
    coefficients = []
    coeff_df = multi.get("coefficients")
    if coeff_df is not None and not coeff_df.empty:
        for _, row in coeff_df.iterrows():
            var_name = str(row.get("变量", ""))
            coef = _float_val(row.get("回归系数"))
            se = _float_val(row.get("标准误"))
            t_z_val = _float_val(row.get("z 值") if is_logistic else row.get("t 值"))
            sig_str = str(row.get("显著性", ""))

            # 找 p 值列
            p_val = None
            for c in coeff_df.columns:
                if "p" in str(c).lower():
                    p_val = _float_val(row.get(c))
                    break

            entry = {
                "variable": var_name,
                "coefficient": coef,
                "std_error": se,
                "p_value": p_val,
                "significant": _is_sig(p_val),
                "significance_mark": sig_str,
            }
            # OLS → t_value，Logit → z_value + OR
            if is_logistic:
                entry["z_value"] = t_z_val
                entry["odds_ratio"] = _float_val(row.get("OR (exp(B))"))
                entry["or_ci_lower"] = _float_val(row.get("OR 95% CI 下限"))
                entry["or_ci_upper"] = _float_val(row.get("OR 95% CI 上限"))
            else:
                entry["t_value"] = t_z_val
            coefficients.append(entry)

    # 模型统计
    n_obs = multi.get("n")
    n_pred = len(coefficients) - 1 if coefficients else 0
    model_warnings = []

    if is_logistic:
        pseudo_r2 = _float_val(multi.get("pseudo_r_squared"))
        if pseudo_r2 is not None and pseudo_r2 < 0.1:
            model_warnings.append(
                f"伪 R² 偏低（{pseudo_r2:.4f}），模型解释力有限。"
                "可能存在重要遗漏变量。"
            )
        result_dict = {
            "dependent_variable": target,
            "independent_variables": expl_vars,
            "sample_size": n_obs,
            "pseudo_r_squared": pseudo_r2,
            "log_likelihood": _float_val(multi.get("log_likelihood")),
            "llr_pvalue": _float_val(multi.get("llr_pvalue")),
            "coefficients": coefficients,
        }
        p_value = _float_val(multi.get("llr_pvalue"))
        interpretation_hint = (
            "二元逻辑回归估计各自变量对目标事件发生几率（odds）的预测作用。"
            "优势比（OR）表示「控制其他变量不变时，该变量每变化 1 个单位，"
            "目标事件发生几率的倍数变化」。OR > 1 表示几率增加，OR < 1 表示几率降低。"
            "伪 R²（McFadden）衡量模型整体拟合优度。"
            "显著的自变量意味着其对目标事件的预测作用具有统计显著性。"
            "回归结果反映样本中的统计关联，不应直接解释为因果关系。"
        )
        limitations = [
            "逻辑回归假设自变量与对数几率之间存在线性关系。",
            "完全分离（某个自变量完美预测因变量）会导致模型无法拟合。",
            "优势比反映统计关联，不能直接解释为因果效应。",
            "遗漏变量偏差可能导致系数估计有偏。",
            "模型外推（预测自变量范围之外的值）不可靠。",
        ]
    else:
        r2 = _float_val(multi.get("r_squared"))
        if r2 is not None:
            if r2 < 0.3:
                model_warnings.append(
                    f"模型解释力较低（R²={r2:.4f}），"
                    "可能存在重要遗漏变量或因变量的随机成分较大。"
                )
            if r2 > 0.9:
                model_warnings.append(
                    f"模型解释力异常高（R²={r2:.4f}），"
                    "请检查是否存在多重共线性或数据泄露。"
                )
        result_dict = {
            "dependent_variable": target,
            "independent_variables": expl_vars,
            "sample_size": n_obs,
            "r_squared": r2,
            "adj_r_squared": _float_val(multi.get("adj_r_squared")),
            "f_statistic": _float_val(multi.get("f_stat") or multi.get("F_statistic")),
            "f_p_value": _float_val(multi.get("f_p_value") or multi.get("F_p_value")),
            "coefficients": coefficients,
        }
        p_value = _float_val(multi.get("f_p_value") or multi.get("F_p_value"))
        interpretation_hint = (
            "OLS 回归估计各自变量与因变量之间的线性统计关联。"
            "回归系数表示「控制其他变量不变时，该变量每变化 1 个单位，"
            "因变量平均变化多少单位」。 "
            "R² 表示模型整体解释力。"
            "显著的自变量意味着其在样本中对因变量有统计显著的独立贡献。"
            "回归结果反映样本中的统计关联，不应直接解释为因果关系。"
        )
        limitations = [
            "OLS 回归假设线性关系、残差独立同分布、无完全多重共线性。",
            "回归系数不能直接解释为因果效应。",
            "遗漏变量偏差可能导致系数估计有偏。",
            "模型外推（预测自变量范围之外的值）不可靠。",
        ]

    if n_obs and n_pred and n_obs < n_pred * 15:
        model_warnings.append(
            f"样本量（{n_obs}）相对自变量数量（{n_pred}）偏小，"
            "回归系数估计可能不稳定。"
        )

    return {
        "analysis_id": "multivariate_regression",
        "analysis_type": analysis_type,
        "variables": [target] + expl_vars,
        "display_names": [target_cn] + [cn_map.get(v, v) for v in expl_vars],
        "variable_types": ["numeric"] * (1 + len(expl_vars)),
        "method": method,
        "result": result_dict,
        "p_value": p_value,
        "significant": _is_sig(p_value),
        "interpretation_hint": interpretation_hint,
        "limitations": limitations + model_warnings,
    }


# ================================================================
# Section: project_meta
# ================================================================

def _package_project_meta(
    config: Dict[str, Any],
    generated_at: str,
    research_subject: str = "",
    report_style: str = "standard",
    report_length: str = "standard",
    cn_map: Optional[Dict[str, str]] = None,
    variable_name_map: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """项目元信息（完全通用，无硬编码内容）。

    新增 variable_name_map：英文列名 → 中文显示名的完整映射，
    供 AI 在报告中用中文名称引用变量，避免暴露后台英文列名。
    """
    result: Dict[str, Any] = {
        "report_title": config.get("report_title", "数据分析报告"),
        "research_subject": research_subject or config.get("research_subject", ""),
        "report_style": report_style,
        "report_length": report_length,
        "generated_at": generated_at,
        "tool": "通用问卷数据 AI 辅助统计分析与报告生成平台",
    }
    # ── 变量名中英文映射（供 AI 报告使用）──
    if variable_name_map:
        result["variable_name_map"] = variable_name_map
    elif cn_map:
        result["variable_name_map"] = {
            col: display
            for col, display in cn_map.items()
            if display and display != col
        }
    return result


# ================================================================
# Section: data_overview
# ================================================================

def _package_data_overview(
    df: pd.DataFrame,
    quality: Optional[Dict[str, Any]],
    selected_sheet: str = "",
    file_type: str = "",
) -> Dict[str, Any]:
    """数据概览（仅聚合信息，不含原始行数据）。"""
    n_rows, n_cols = df.shape
    overview: Dict[str, Any] = {
        "row_count": n_rows,
        "column_count": n_cols,
        "column_names": list(df.columns),
    }

    if selected_sheet:
        overview["selected_sheet"] = selected_sheet
    if file_type:
        overview["file_type"] = file_type

    if quality:
        overview.update({
            "missing_total": quality.get("缺失值总数", 0),
            "missing_rate_pct": quality.get("缺失率", 0),
            "duplicate_rows": quality.get("重复行数", 0),
            "duplicate_rate_pct": quality.get("重复率", 0),
        })

    return overview


# ================================================================
# Section: variable_schema
# ================================================================

def _enrich_variable_schema_with_metadata(
    schema_list: List[Dict[str, Any]],
    var_metadata: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """将变量元数据（value_labels, description）注入到 variable_schema 列表。

    v0.1.0 Phase 3: 使 AI 可以直接从 variable_schema 获取取值标签和说明。
    """
    for entry in schema_list:
        col = entry.get("column", "")
        if col in var_metadata:
            meta = var_metadata[col]
            entry["value_labels"] = meta.get("value_labels", {})
            entry["description"] = meta.get("description", "")
            entry["role"] = meta.get("role", "none")
    return schema_list


def _package_variable_schema(
    schema_df: pd.DataFrame,
    privacy_settings: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """变量类型信息（遍历所有变量，含隐私设置）。"""
    schema_list = []
    for _, row in schema_df.iterrows():
        col = row["column"]
        ps = privacy_settings.get(col, {})
        send_mode = ps.get("send_to_ai_mode", "aggregate_only")
        privacy_cat = ps.get("privacy_category", "none")

        # 示例值处理：根据 send_to_ai_mode 决定是否保留/脱敏
        raw_examples = _safe_example_values(row.get("example_values", ""), MAX_EXAMPLE_VALUES)
        if send_mode == "exclude":
            examples = []
        elif send_mode == "masked_examples":
            examples = _apply_masking_to_values(raw_examples, privacy_cat)
        else:
            examples = raw_examples  # aggregate_only 或 full

        entry: Dict[str, Any] = {
            "column": col,
            "display_name": row.get("display_name", "") or col,
            "inferred_type": row["inferred_type"],
            "user_confirmed_type": row.get("inferred_type", ""),
            "missing_count": int(row.get("missing_count", 0)),
            "missing_rate_pct": float(row.get("missing_rate", 0)),
            "unique_count": int(row.get("unique_count", 0)),
            "example_values": examples,
            "suggested_role": row.get("suggested_role", ""),
            # 隐私字段
            "privacy_risk": ps.get("privacy_risk", "none"),
            "privacy_category": ps.get("privacy_category", "none"),
            "allow_local_stats": ps.get("allow_local_stats", True),
            "allow_as_group_variable": ps.get("allow_as_group_variable", True),
            "allow_in_model": ps.get("allow_in_model", True),
            "allow_send_to_ai": ps.get("allow_send_to_ai", True),
            "send_to_ai_mode": send_mode,
            "user_confirmed_privacy": ps.get("user_confirmed_privacy", False),
        }

        schema_list.append(entry)

    return schema_list


# ================================================================
# Section: user_analysis_config
# ================================================================

def _package_user_config(
    config: Dict[str, Any],
    target_type: str,
    id_vars: List[str],
    text_vars: List[str],
    datetime_vars: List[str],
    excluded_sensitive_vars: List[str],
    privacy_restricted_vars: List[str],
) -> Dict[str, Any]:
    """用户分析配置，含隐私分级排除清单。"""
    return {
        "target_variable": config.get("target_variable", ""),
        "target_variable_type": target_type,
        "group_variables": config.get("group_variables", []) or [],
        "explanatory_variables": config.get("explanatory_variables", []) or [],
        "excluded_id_variables": sorted(set(id_vars)),
        "excluded_text_variables": sorted(set(text_vars)),
        "excluded_datetime_variables": sorted(set(datetime_vars)),
        "excluded_sensitive_variables": sorted(set(excluded_sensitive_vars)),
        "privacy_restricted_variables": sorted(set(privacy_restricted_vars)),
    }


# ================================================================
# Section: chart_summaries
# ================================================================

def _package_chart_summaries(
    chart_summaries: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """图表摘要（不传图片，只传文字化描述）。"""
    if not chart_summaries:
        return []

    result = []
    for cs in chart_summaries:
        if not isinstance(cs, dict):
            continue
        result.append({
            "chart_title": cs.get("title", ""),
            "chart_type": cs.get("chart_type", cs.get("type", "")),
            "variables": cs.get("variables", []),
            "summary": cs.get("trend", cs.get("main_trend", "")),
            "key_pattern": cs.get("key_pattern", ""),
        })

    return result


# ================================================================
# JSON 序列化
# ================================================================

def to_json_payload(payload: Dict[str, Any], indent: int = 2) -> str:
    """将 payload 序列化为 JSON 字符串。"""
    return _safe_json_dumps(payload, indent=indent)


def _safe_json_dumps(payload: Dict[str, Any], indent: int = 2) -> str:
    """安全的 JSON 序列化（处理 numpy/pandas 类型）。"""
    return json.dumps(payload, indent=indent, ensure_ascii=False, default=_json_default)


def _json_default(obj):
    """处理 JSON 无法序列化的类型。"""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, pd.Timestamp):
        return str(obj)
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    if isinstance(obj, (set, frozenset)):
        return list(obj)
    return str(obj)


# ================================================================
# 辅助函数
# ================================================================

def _risk_label(risk: str) -> str:
    """隐私风险等级的中文标签。"""
    return {"none": "无", "low": "低", "medium": "中", "high": "高"}.get(risk, risk)


def _cat_label(cat: str) -> str:
    """隐私分类的中文标签。"""
    return {
        "none": "无",
        "demographic_attribute": "人口统计属性",
        "contact_info": "联系方式",
        "direct_identifier": "直接身份标识",
        "location_info": "地理位置",
        "free_text": "自由文本",
        "sensitive_attribute": "敏感属性",
        "financial": "金融信息",
        "unknown": "未知",
    }.get(cat, cat)


def _float_val(val) -> Optional[float]:
    """安全转为 float，NaN/Inf 返回 None。"""
    if val is None:
        return None
    try:
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return None
        return round(f, 4)
    except (ValueError, TypeError):
        return None


def _safe_str(val) -> str:
    """安全转为字符串。"""
    if val is None:
        return ""
    if isinstance(val, float) and (np.isnan(val) or np.isinf(val)):
        return ""
    return str(val)


def _is_sig(p_val) -> Optional[bool]:
    """判断 p 值是否在 0.05 水平显著。"""
    p = _float_val(p_val)
    if p is None:
        return None
    return p < 0.05


def _safe_example_values(raw: str, max_items: int = 5) -> List[str]:
    """安全解析示例值（逗号分隔），最多 max_items 个。"""
    if not raw:
        return []
    items = [x.strip() for x in raw.split(",") if x.strip()]
    return items[:max_items]


def _freq_table(freq_df, max_rows: int = 20) -> Optional[List[Dict[str, Any]]]:
    """频数表转为列表，最多 max_rows 行。"""
    if freq_df is None:
        return None
    if not hasattr(freq_df, "iterrows"):
        return None
    try:
        rows = []
        for _, row in freq_df.iterrows():
            label = _safe_str(row.get("标签", ""))
            if label == "缺失":
                continue  # 缺失在 missing_count 中已体现
            rows.append({
                "category": label,
                "count": int(row.get("频次", 0)),
                "percentage": _float_val(row.get("百分比(%)", 0)),
            })
            if len(rows) >= max_rows:
                break
        return rows
    except Exception:
        return None


def _estimate_text_length(result: Dict[str, Any]) -> Optional[int]:
    """估算文本变量的平均长度。"""
    freq = result.get("频数表")
    if freq is not None and hasattr(freq, "iterrows"):
        labels = []
        for _, row in freq.iterrows():
            label = str(row.get("标签", ""))
            if label != "缺失":
                labels.append(label)
        if labels:
            return int(sum(len(l) for l in labels) / len(labels))
    return None


def _summarize_crosstab(ct) -> List[Dict[str, Any]]:
    """交叉表摘要，最多 MAX_CROSSTAB_CELLS 个格子。"""
    summary = []
    try:
        if ct is not None and hasattr(ct, "to_dict"):
            d = ct.to_dict()
            count = 0
            for row_key, col_data in d.items():
                if isinstance(col_data, dict):
                    for col_key, val in col_data.items():
                        v = int(val) if not (isinstance(val, float) and (np.isnan(val) or np.isinf(val))) else 0
                        summary.append({
                            "row_category": str(row_key),
                            "col_category": str(col_key),
                            "count": v,
                        })
                        count += 1
                        if count >= MAX_CROSSTAB_CELLS:
                            return summary
                if count >= MAX_CROSSTAB_CELLS:
                    break
    except Exception:
        pass
    return summary


def _get_vars_by_role(schema_df: pd.DataFrame, role: str) -> List[str]:
    """按 suggested_role 获取变量列表。"""
    return schema_df[schema_df["suggested_role"] == role]["column"].tolist()


def _get_vars_by_type(schema_df: pd.DataFrame, vtype: str) -> List[str]:
    """按 inferred_type 获取变量列表。"""
    return schema_df[schema_df["inferred_type"] == vtype]["column"].tolist()


def _get_high_missing_vars(schema_df: pd.DataFrame, threshold_pct: float = 10.0) -> List[str]:
    """获取缺失率超过阈值的变量。"""
    high = schema_df[schema_df["missing_rate"] > threshold_pct]
    return [f"{row['column']}（{row['missing_rate']:.1f}%）" for _, row in high.iterrows()]


# ================================================================
# 截断
# ================================================================

def _truncate_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """对过大的 payload 进行安全截断。"""
    # 截断 analysis_results 中的频数表和相关系数
    results = payload.get("analysis_results", [])
    for entry in results:
        if not isinstance(entry, dict):
            continue
        atype = entry.get("analysis_type", "")
        r = entry.get("result", {})

        if atype == "categorical_frequency" and isinstance(r, dict):
            cats = r.get("categories")
            if isinstance(cats, list) and len(cats) > 10:
                r["categories"] = cats[:10]
                r["_truncated"] = True

    # 截断 variable_schema 中的 example_values
    vs = payload.get("variable_schema", [])
    if isinstance(vs, list):
        for entry in vs:
            if isinstance(entry, dict):
                ev = entry.get("example_values", [])
                if isinstance(ev, list) and len(ev) > 3:
                    entry["example_values"] = ev[:3]

    # 截断 analysis_results 中过多的相关条目
    corr_entries = [
        r for r in results
        if isinstance(r, dict) and r.get("analysis_type") == "numeric_numeric_correlation"
    ]
    if len(corr_entries) > 20:
        # 保留非相关条目 + 前 20 条相关
        non_corr = [r for r in results if r.get("analysis_type") != "numeric_numeric_correlation"]
        corr_sorted = sorted(
            corr_entries,
            key=lambda x: abs((x.get("result") or {}).get("pearson_r") or 0),
            reverse=True,
        )[:20]
        payload["analysis_results"] = non_corr + corr_sorted

    payload["warnings"].append("分析结果过大，部分内容已自动截断。如需完整数据，请缩减变量范围。")
    return payload
