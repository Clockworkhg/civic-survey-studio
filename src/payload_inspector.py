"""Analysis payload inspector — centralized payload structure checks.

Replaces the duplicated has_regression / has_significance / has_logistic
checks that were scattered across app.py, llm_prompts.py, and ai_report_generator.py.

All functions are read-only and side-effect-free.
"""

from __future__ import annotations

from typing import Any, Dict, Set


def payload_has_regression(payload: Dict[str, Any]) -> bool:
    """Check if payload contains any regression results (OLS or logistic)."""
    return any(
        r.get("analysis_type") in ("linear_regression", "logistic_regression")
        for r in payload.get("analysis_results", [])
    )


def payload_has_logistic_regression(payload: Dict[str, Any]) -> bool:
    """Check if payload contains logistic regression results."""
    return any(
        r.get("analysis_type") == "logistic_regression"
        for r in payload.get("analysis_results", [])
    )


def payload_has_ols_regression(payload: Dict[str, Any]) -> bool:
    """Check if payload contains OLS linear regression results."""
    return any(
        r.get("analysis_type") == "linear_regression"
        for r in payload.get("analysis_results", [])
    )


def payload_has_significance(payload: Dict[str, Any]) -> bool:
    """Check if payload contains any significance-test results.

    Compatible with: OLS regression, logistic regression, chi-square,
    t-test, ANOVA, Pearson/Spearman correlation.
    """
    return any(
        r.get("p_value") is not None
        for r in payload.get("analysis_results", [])
    )


def get_analysis_types(payload: Dict[str, Any]) -> Set[str]:
    """Return the set of all analysis_type values present in the payload."""
    return {
        r.get("analysis_type", "")
        for r in payload.get("analysis_results", [])
    }


def payload_has_target(payload: Dict[str, Any]) -> bool:
    """Check if a target variable is configured."""
    return bool(
        payload.get("user_analysis_config", {}).get("target_variable", "")
    )
