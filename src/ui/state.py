"""Session state initialization for the Streamlit app.

Provides a single entry point `init_session_state()` that must be called
once at startup, after page config but before any widget rendering that
reads from session_state.
"""

from __future__ import annotations

import streamlit as st
from src.user_settings import load_user_settings


def init_session_state() -> None:
    """Initialize all session_state keys used by the Streamlit app.

    Must be called once at app startup, after page config but before
    any widget rendering that reads from session_state.

    Handles:
    1. Loading saved user settings from disk and writing _saved_* keys
    2. Initializing generic_config with defaults
    3. Initializing ai_models_* keys with defaults
    4. Initializing _ai_model from saved model or default

    All initializations use the ``if "key" not in st.session_state`` guard
    pattern, so the function is idempotent and safe to call multiple times.
    """
    # ── 1. 加载保存的 API 设置 ──
    saved = load_user_settings()
    if saved:
        _set_default("_saved_provider_key", saved.get("provider_key", ""))
        _set_default("_saved_api_key", saved.get("api_key", ""))
        _set_default("_saved_model", saved.get("model", ""))
        _set_default("_saved_remember", saved.get("remember", False))
    else:
        _set_default("_saved_provider_key", "")
        _set_default("_saved_api_key", "")
        _set_default("_saved_model", "")
        _set_default("_saved_remember", False)

    # ── 2. 通用分析配置 ──
    _set_default("generic_config", {
        "report_title": "问卷数据分析报告",
        "target_variable": "",
        "group_variables": [],
        "explanatory_variables": [],
    })

    # ── 3. AI 模型列表相关 ──
    _set_default("ai_models_fetched", False)
    _set_default("ai_available_models", [])
    _set_default("ai_models_source", "")
    _set_default("ai_models_updated_at", None)
    _set_default("ai_models_error", "")

    # ── 4. 当前 AI 模型（优先后保存的设置）──
    _set_default("_ai_model", st.session_state.get("_saved_model", ""))

    # ── 5. Landing page state ──
    _set_default("show_quickstart", False)

    # ── 6. v0.1.0: 下游有效性追踪 ──
    _set_default("_downstream_valid", True)
    _set_default("_invalidation_reason", "")
    _set_default("_config_source", "")
    _set_default("_config_applied_at", "")
    _set_default("_analysis_results", {})
    _set_default("_dashboard_charts", [])
    _set_default("_analysis_payload", None)
    _set_default("_generated_report", None)
    _set_default("_pipeline_warnings", [])


def _set_default(key: str, default: object) -> None:
    """Set a session_state key to *default* if it does not already exist."""
    if key not in st.session_state:
        st.session_state[key] = default
