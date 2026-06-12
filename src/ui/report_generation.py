"""Report generation call logic extracted from app.py.

Encapsulates the shared pattern of building LLMConfig/ReportConfig from
UI widget values and calling generate_ai_report().

Does NOT call run_full_analysis — the caller is responsible for running
analysis before calling these functions.
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from src.config_models import LLMConfig, ReportConfig
from src.ai_report_generator import generate_ai_report


def build_llm_config_from_ui(
    provider_config: Dict[str, Any],
    api_key: str,
    model: str,
    provider_key: str = "",
    temperature: float = 0.3,
    max_tokens: int = 4096,
    chat_path: str = "/chat/completions",
) -> LLMConfig:
    """Build an LLMConfig from UI widget values.

    Args:
        provider_config: The resolved provider configuration dict.
        api_key: Resolved API key string.
        model: Selected model name.
        provider_key: Provider key (e.g. "openai", "deepseek").
        temperature: Temperature for LLM generation.
        max_tokens: Max output tokens.
        chat_path: Chat completions path (overridden for custom_openai).

    Returns:
        LLMConfig with all fields populated.
    """
    return LLMConfig(
        provider_config=provider_config,
        api_key=api_key,
        model=model,
        provider_key=provider_key,
        temperature=temperature,
        max_tokens=max_tokens,
        chat_path=chat_path,
    )


def build_report_config_from_ui(
    report_structure: str = "通用调研报告",
    report_style: str = "学术报告风",
    report_length: str = "标准版",
    html_theme: str = "简洁课程作业风",
    literature_enabled: bool = False,
    literature_keywords: str = "",
    literature_max_sources: int = 15,
    literature_year_range: str = "不限",
    background_enabled: bool = False,
    background_source_path: str = "",
) -> ReportConfig:
    """Build a ReportConfig from UI widget values.

    Args:
        report_structure: Report structure type.
        report_style: Writing style.
        report_length: Report length.
        html_theme: HTML export theme.
        literature_enabled: Whether literature review is enabled.
        literature_keywords: Search keywords for literature.
        literature_max_sources: Max literature sources (5-50).
        literature_year_range: Year range filter ("不限" | "近5年" | ...).
        background_enabled: Whether background context is enabled.
        background_source_path: Path to background source file/directory.

    Returns:
        ReportConfig with all fields populated.
    """
    return ReportConfig(
        report_structure=report_structure,
        report_style=report_style,
        report_length=report_length,
        html_theme=html_theme,
        literature_enabled=literature_enabled,
        literature_keywords=literature_keywords,
        literature_max_sources=literature_max_sources,
        literature_year_range=literature_year_range,
        background_enabled=background_enabled,
        background_source_path=background_source_path,
    )


def run_report_generation_from_ui(
    df: pd.DataFrame,
    schema_df: pd.DataFrame,
    config: Dict[str, Any],
    analysis_results: Dict[str, Any],
    quality: Dict[str, Any] | None,
    llm_config: LLMConfig,
    report_config: ReportConfig,
) -> Dict[str, Any]:
    """Run AI report generation and return the result dict.

    Does NOT call run_full_analysis — the caller must do that first
    and pass the results as ``analysis_results``.

    Args:
        df: Raw data DataFrame.
        schema_df: Variable schema DataFrame (from infer_variable_schema).
        config: Analysis configuration dict (from session_state["generic_config"]).
        analysis_results: Results from run_full_analysis.
        quality: Data quality report dict (from get_data_quality_report).
        llm_config: LLMConfig built from UI values.
        report_config: ReportConfig built from UI values.

    Returns:
        Dict with keys: success, markdown_report, html_report, docx_report,
        llm_response, error, warnings.
    """
    return generate_ai_report(
        df=df,
        schema_df=schema_df,
        config=config,
        analysis_results=analysis_results,
        quality=quality,
        llm_config=llm_config,
        report_config=report_config,
    )


def resolve_default_ai_model(
    provider_config: Dict[str, Any] | None = None,
    saved_model: str = "",
) -> str:
    """Resolve the effective default AI model.

    Priority:
    1. ``saved_model`` — if the user previously saved a model choice
    2. ``provider_config["default_model"]`` — the provider's declared default
    3. ``""`` — empty string (no default available)

    This function is pure (no Streamlit dependency) and can be called
    both during session_state initialization and during widget rendering.

    Args:
        provider_config: Provider configuration dict (may be None or empty).
        saved_model: Previously saved model name (from user settings).

    Returns:
        The resolved model name, or "" if no default is available.
    """
    if saved_model:
        return saved_model
    if provider_config:
        return provider_config.get("default_model", "")
    return ""

