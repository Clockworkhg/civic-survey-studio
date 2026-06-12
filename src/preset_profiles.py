"""预设分析方案模块。

提供内置的分析方案配置。示例模式通过这些 profile 接入统一分析流程，
而不是使用硬编码的独立逻辑。

每个 profile 定义：
  - 推荐的分析变量（target / group / explanatory）
  - 推荐的图表
  - 推荐的报告配置

使用方式:
  from src.preset_profiles import get_profile, list_profiles
  profile = get_profile("gov_satisfaction")
  context.apply_preset_profile(profile)
"""

from typing import Any, Dict, List, Optional


# ================================================================
# Profile 1: 政务服务中心满意度调查
# ================================================================

GOV_SATISFACTION_PROFILE: Dict[str, Any] = {
    "profile_key": "gov_satisfaction",
    "profile_name": "政务服务中心公众满意度调查示例",
    "profile_description": (
        "内置的政务服务中心公众满意度调查数据分析方案。"
        "适用于与示例数据格式相同的满意度调查数据。"
    ),
    "report_title": "政务服务中心公众满意度调查数据分析报告",
    "research_subject": "办事群众 / 调查样本",

    # ── 核心变量 ──
    "target_variable": "overall_satisfaction",
    "group_variables": [
        "district", "gender", "age_group", "education",
        "channel", "service_type",
    ],
    "explanatory_variables": [
        "wait_time_min", "wait_satisfaction", "staff_attitude",
        "process_convenience", "online_service", "info_transparency",
        "complaint_intention", "policy_trust",
    ],

    # ── 变量分类 ──
    "key_categorical_variables": [
        "district", "gender", "age_group", "education",
        "channel", "visit_frequency", "service_type",
        "satisfaction_level", "recommend", "priority_improve",
    ],
    "key_numeric_variables": [
        "age", "wait_time_min", "wait_satisfaction",
        "staff_attitude", "process_convenience", "online_service",
        "info_transparency", "overall_satisfaction",
        "complaint_intention", "policy_trust",
    ],

    # ── 推荐图表 ──
    "recommended_charts": [
        {"chart_name": "总体满意度分布", "chart_type": "bar", "variables": ["overall_satisfaction"]},
        {"chart_name": "满意度等级分布", "chart_type": "pie", "variables": ["satisfaction_level"]},
        {"chart_name": "各政务中心满意度对比", "chart_type": "bar", "variables": ["district", "overall_satisfaction"]},
        {"chart_name": "不同办理渠道满意度对比", "chart_type": "bar", "variables": ["channel", "overall_satisfaction"]},
        {"chart_name": "等待时间与总体满意度关系", "chart_type": "scatter", "variables": ["wait_time_min", "overall_satisfaction"]},
        {"chart_name": "满意度维度雷达图", "chart_type": "radar", "variables": ["wait_satisfaction", "staff_attitude", "process_convenience", "online_service", "info_transparency"]},
        {"chart_name": "优先改进事项分布", "chart_type": "bar", "variables": ["priority_improve"]},
    ],

    # ── 推荐回归自变量（用于示例模式的回归分析） ──
    "regression_independent_vars": [
        "wait_satisfaction", "staff_attitude", "process_convenience",
        "online_service", "info_transparency", "policy_trust", "wait_time_min",
    ],

    # ── 相关分析变量组 ──
    "correlation_var_group": [
        "wait_satisfaction", "staff_attitude", "process_convenience",
        "online_service", "info_transparency", "policy_trust",
        "complaint_intention", "overall_satisfaction", "wait_time_min",
    ],

    # ── 预设交叉分析对 ──
    "cross_analysis_pairs": [
        ("district", "satisfaction_level"),
        ("gender", "satisfaction_level"),
        ("age_group", "satisfaction_level"),
        ("education", "satisfaction_level"),
        ("channel", "satisfaction_level"),
        ("visit_frequency", "satisfaction_level"),
        ("service_type", "satisfaction_level"),
    ],

    # ── 推荐报告结构／风格 ──
    "recommended_report_structure": "政务决策报告",
    "recommended_report_style": "政务汇报风",
}


# ================================================================
# 注册表
# ================================================================

_PROFILES: Dict[str, Dict[str, Any]] = {
    "gov_satisfaction": GOV_SATISFACTION_PROFILE,
}


# ================================================================
# 公开 API
# ================================================================

def get_profile(profile_key: str) -> Optional[Dict[str, Any]]:
    """获取指定 key 的预设分析方案。

    Args:
        profile_key: 方案 key，如 "gov_satisfaction"

    Returns:
        profile 字典；不存在时返回 None
    """
    return _PROFILES.get(profile_key)


def list_profiles() -> List[Dict[str, str]]:
    """列出所有可用的预设分析方案。

    Returns:
        [{"key": str, "name": str, "description": str}, ...]
    """
    return [
        {
            "key": key,
            "name": profile["profile_name"],
            "description": profile.get("profile_description", ""),
        }
        for key, profile in _PROFILES.items()
    ]


def register_profile(profile: Dict[str, Any]) -> None:
    """动态注册一个新的预设分析方案。

    Args:
        profile: profile 字典，必须包含 "profile_key"
    """
    key = profile.get("profile_key", "")
    if key:
        _PROFILES[key] = profile
