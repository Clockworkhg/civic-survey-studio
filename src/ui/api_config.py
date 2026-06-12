"""Shared AI API configuration module.

Extracted from ``tab_ai_analysis.py`` so that API provider selection,
API Key input, model selection, and connection testing can be used
from any location (sidebar, main area, expander) without duplicating
widget keys or session_state keys.

Usage::

    from src.ui.api_config import render_api_config_section
    render_api_config_section()           # standalone
    render_api_config_section(location="sidebar")  # inside st.sidebar

All widget keys and session_state keys are preserved from the original
Tab 10 implementation.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict

import streamlit as st

from src.provider_config import get_provider, get_api_key, list_providers
from src.llm_client import test_connection
from src.model_registry import get_available_models, load_cached_models
from src.user_settings import save_user_settings, clear_user_settings
from src.ui.report_generation import resolve_default_ai_model
from src.ui.messages import get_no_api_key_message, format_user_friendly_error
from src.ui.security import mask_api_key


# ================================================================
# Private helpers
# ================================================================

def _save_current_settings(provider_key: str, api_key: str, model: str, remember: bool) -> None:
    """保存或清除当前 API 设置到本地文件。"""
    if remember:
        save_user_settings({
            "provider_key": provider_key,
            "api_key": api_key,
            "model": model,
            "remember": True,
        })
    else:
        clear_user_settings()


# ================================================================
# Main render function
# ================================================================

def render_api_config_section(location: str = "inline") -> None:
    """Render AI API configuration: provider, key, model, connection test.

    Writes the following session_state keys (identical to the original
    Tab 10 behaviour):

    - ``_api_key``
    - ``_provider_key``
    - ``_provider_config``
    - ``_ai_model``
    - ``_saved_remember``
    - ``ai_models_fetched`` / ``ai_available_models`` / ``ai_models_source`` /
      ``ai_models_updated_at`` / ``ai_models_error``

    Parameters
    ----------
    location : str
        ``"inline"`` (default) renders as-is.
        ``"sidebar"`` suppresses the top-level heading (the caller
        provides its own via ``st.expander`` or ``st.sidebar``).
    """
    if location != "sidebar":
        st.markdown("### 🤖 AI API 设置")
        st.caption("选择 AI 厂商并配置模型，供所有 AI 功能使用。")

    # ---- 厂商配置 ----
    if location == "sidebar":
        st.markdown("##### 1. 选择 AI 厂商")
    else:
        st.markdown("#### 1. 选择 AI 厂商")

    # 加载厂商列表
    try:
        providers_list = list_providers()
    except Exception as e:
        st.error(f"加载 LLM 厂商配置失败：{e}")
        providers_list = []

    if not providers_list:
        st.warning("未找到 LLM 厂商配置。请检查 config/llm_providers.yaml 文件。")
        return

    provider_options = {p["display_name"]: p for p in providers_list}
    provider_names = list(provider_options.keys())
    # 使用保存的厂商作为默认选中
    saved_provider_key = st.session_state.get("_saved_provider_key", "")
    default_provider_idx = 0
    for i, name in enumerate(provider_names):
        if provider_options[name]["key"] == saved_provider_key:
            default_provider_idx = i
            break
    selected_display = st.selectbox(
        "AI 厂商：",
        provider_names,
        index=default_provider_idx,
        key="ai_provider_display",
    )
    selected_provider_info = provider_options[selected_display]
    provider_key = selected_provider_info["key"]
    provider_config = get_provider(provider_key)

    if provider_config is None:
        st.error(f"未找到厂商配置: {provider_key}")
        return

    protocol = provider_config.get("protocol", "")
    default_model = provider_config.get("default_model", "")
    api_key_env = provider_config.get("api_key_env", "")
    allow_custom = provider_config.get("allow_custom_model", True)
    model_list_cfg = provider_config.get("model_list", {})

    # 显示厂商信息
    with st.expander("📋 厂商配置详情", expanded=False):
        st.json({
            "display_name": selected_display,
            "protocol": protocol,
            "base_url": provider_config.get("base_url", ""),
            "default_model": default_model,
            "api_key_env": api_key_env,
            "model_list_enabled": model_list_cfg.get("enabled", False),
            "model_list_note": model_list_cfg.get("note", ""),
        })

    # ---- 自定义 OpenAI Compatible API ----
    custom_base_url = provider_config.get("base_url", "")
    custom_chat_path = "/chat/completions"
    custom_auth_type = "bearer"
    custom_header_name = "Authorization"
    custom_prefix = "Bearer"
    custom_model_list_path = model_list_cfg.get("path", "/models")
    custom_response_format = model_list_cfg.get("response_format", "openai_models")

    if provider_key == "custom_openai":
        if location == "sidebar":
            st.markdown("##### 自定义 API 配置")
        else:
            st.markdown("#### 自定义 API 配置")
        cc1, cc2 = st.columns(2)
        with cc1:
            custom_display_name = st.text_input(
                "自定义厂商名称", value="自定义 API",
                key="custom_display_name",
            )
            custom_base_url = st.text_input(
                "Base URL", value=custom_base_url or "",
                placeholder="https://your-api.example.com/v1",
                key="custom_base_url",
            )
            custom_chat_path = st.text_input(
                "Chat Path", value="/chat/completions",
                placeholder="/chat/completions",
                key="custom_chat_path",
            )
        with cc2:
            custom_model_list_path = st.text_input(
                "模型列表路径", value=custom_model_list_path,
                placeholder="/models",
                key="custom_model_list_path",
            )
            custom_response_format = st.selectbox(
                "响应格式",
                ["openai_models", "generic_models"],
                index=0 if custom_response_format in ("openai_models", "generic_models") else 1,
                key="custom_response_format",
                help="openai_models: 期望 {\"data\": [...]} 格式；generic_models: 自动探测",
            )

        st.markdown("**鉴权方式**")
        ca1, ca2, ca3 = st.columns(3)
        with ca1:
            custom_auth_type = st.selectbox(
                "Auth Type",
                ["bearer", "api_key_header"],
                key="custom_auth_type",
            )
        with ca2:
            custom_header_name = st.text_input(
                "Header Name",
                value="api-key" if custom_auth_type == "api_key_header" else "Authorization",
                key="custom_header_name",
            )
        with ca3:
            custom_prefix = st.text_input(
                "Prefix", value="" if custom_auth_type == "api_key_header" else "Bearer",
                key="custom_prefix",
            )

        # 重写 provider_config 以便后续使用
        provider_config = dict(provider_config)
        provider_config["base_url"] = custom_base_url
        provider_config["auth"] = {
            "type": custom_auth_type,
            "header_name": custom_header_name,
            "prefix": custom_prefix,
        }
        provider_config["model_list"] = {
            **model_list_cfg,
            "path": custom_model_list_path,
            "response_format": custom_response_format,
        }

    # ---- API Key ----
    if location == "sidebar":
        st.markdown("##### 2. API Key")
    else:
        st.markdown("#### 2. API Key")
    api_key_hint = ""
    if api_key_env:
        api_key_hint = f"环境变量: {api_key_env}"
    elif provider_key == "custom_openai":
        api_key_hint = "输入你的 API Key"

    # 使用保存的 API Key 作为默认值
    saved_api_key = st.session_state.get("_saved_api_key", "")
    user_api_key = st.text_input(
        "API Key" + (f"（{api_key_hint}）" if api_key_hint else ""),
        type="password",
        value=saved_api_key if saved_api_key else "",
        key="ai_api_key",
        placeholder="输入 API Key，或留空以使用环境变量 / Streamlit Secrets",
    )
    resolved_api_key = get_api_key(provider_config, user_api_key)
    # 持久化到 session_state 供其他 tab 使用
    st.session_state["_api_key"] = resolved_api_key
    st.session_state["_provider_key"] = provider_key
    st.session_state["_provider_config"] = provider_config

    # ── 记住设置 ──
    saved_remember = st.session_state.get("_saved_remember", False)
    remember_me = st.checkbox(
        "💾 记住设置（API Key 将以明文保存在本地文件中，仅建议在个人设备上使用）",
        value=saved_remember,
        key="gen_remember_me",
    )
    st.session_state["_saved_remember"] = remember_me

    if not resolved_api_key:
        st.info(get_no_api_key_message(api_key_env))

    # ============================================
    # 模型选择区域
    # ============================================
    if location == "sidebar":
        st.markdown("##### 3. 模型选择")
    else:
        st.markdown("#### 3. 模型选择")

    # 确保 _ai_model 有合理的默认值（保存值 > provider 默认 > 空）
    _effective_default = resolve_default_ai_model(
        provider_config, st.session_state.get("_saved_model", "")
    )
    if not st.session_state.get("_ai_model"):
        st.session_state["_ai_model"] = _effective_default

    model_list_enabled = model_list_cfg.get("enabled", False)
    ml_note = model_list_cfg.get("note", "")

    selected_model = st.session_state.get("_ai_model", "")

    # ── 支持联网获取的厂商 ──
    if model_list_enabled:
        # 检查缓存
        has_cache = False
        cache_info_text = ""
        try:
            cached = load_cached_models(provider_key)
            if cached.get("models"):
                cache_time = cached.get("updated_at")
                if cache_time:
                    cache_dt = datetime.datetime.fromtimestamp(cache_time)
                    cache_info_text = f"📦 缓存模型列表 · 更新时间：{cache_dt.strftime('%Y-%m-%d %H:%M:%S')}"
                    has_cache = True
                else:
                    cache_info_text = "📦 使用缓存模型列表"
                    has_cache = True
        except Exception:
            pass

        col_fetch1, col_fetch2 = st.columns([1, 3])
        with col_fetch1:
            fetch_btn = st.button(
                "🌐 联网获取模型列表",
                key="ai_fetch_models",
                disabled=not bool(resolved_api_key),
                help="需要先输入 API Key" if not resolved_api_key else "从 API 获取最新模型列表",
            )

        # 自定义 API 额外选项
        if provider_key == "custom_openai":
            with col_fetch2:
                st.caption(f"请求: GET {custom_base_url or provider_config.get('base_url', '')}{custom_model_list_path}")

        # 执行联网获取
        if fetch_btn and resolved_api_key:
            with st.spinner("正在联网获取模型列表…"):
                custom_opts = {}
                if provider_key == "custom_openai":
                    custom_opts = {
                        "model_list_path": custom_model_list_path,
                        "response_format": custom_response_format,
                    }
                result = get_available_models(
                    provider_key=provider_key,
                    provider_config=provider_config,
                    api_key=resolved_api_key,
                    refresh=True,
                    custom_options=custom_opts if custom_opts else None,
                )
                if result.get("success"):
                    st.session_state.ai_models_fetched = True
                    st.session_state.ai_available_models = result.get("models", [])
                    st.session_state.ai_models_source = result.get("source", "remote")
                    st.session_state.ai_models_updated_at = result.get("updated_at")
                    st.session_state.ai_models_error = ""
                    st.rerun()
                else:
                    st.session_state.ai_models_fetched = False
                    st.session_state.ai_models_error = result.get("error", "获取失败")
                    st.rerun()

        # 展示缓存状态 / 获取结果
        if st.session_state.ai_models_fetched and st.session_state.ai_available_models:
            source_label = {
                "remote": "🔄 已从 API 刷新",
                "cache": "📦 使用缓存",
                "cache_expired": "📦 使用过期缓存",
            }.get(st.session_state.ai_models_source, "")

            if st.session_state.ai_models_updated_at:
                dt = datetime.datetime.fromtimestamp(st.session_state.ai_models_updated_at)
                source_label += f" · {dt.strftime('%Y-%m-%d %H:%M:%S')}"

            st.success(f"{source_label} · 共 {len(st.session_state.ai_available_models)} 个模型")

            # 使用 session_state 中的模型列表
            available_models = st.session_state.ai_available_models

            if available_models:
                model_ids = [m["id"] for m in available_models]
                # 默认选中
                default_idx = 0
                for i, m in enumerate(available_models):
                    if m["id"] == default_model or m["id"] == st.session_state._ai_model:
                        default_idx = i
                        break

                selected_model = st.selectbox(
                    "从列表中选择模型：",
                    model_ids,
                    index=default_idx,
                    key="ai_model_select",
                )
                # 同步到 session_state
                st.session_state._ai_model = selected_model
            else:
                st.warning("模型列表为空，请手动输入模型名。")
                selected_model = st.text_input(
                    "模型名：",
                    value=st.session_state._ai_model or default_model,
                    key="ai_model_input",
                    placeholder="输入模型名",
                )
                st.session_state._ai_model = selected_model

        elif st.session_state.ai_models_error:
            st.warning(f"⚠️ {st.session_state.ai_models_error}")
            if has_cache:
                st.info(cache_info_text)
            selected_model = st.text_input(
                "模型名（手动输入）：",
                value=st.session_state._ai_model or default_model,
                key="ai_model_input_fallback",
                placeholder="输入模型名",
            )
            st.session_state._ai_model = selected_model

        elif has_cache and not st.session_state.ai_models_fetched:
            st.info(f"{cache_info_text} · 点击「联网获取」刷新")
            selected_model = st.text_input(
                "模型名：",
                value=st.session_state._ai_model or default_model,
                key="ai_model_input_cached",
                placeholder="输入模型名",
            )
            st.session_state._ai_model = selected_model

        else:
            if not resolved_api_key:
                st.caption("💡 输入 API Key 后可联网获取模型列表")
            selected_model = st.text_input(
                "模型名：",
                value=default_model,
                key="ai_model_input_direct",
                placeholder="输入模型名，如 gpt-4o, deepseek-chat",
            )
            st.session_state._ai_model = selected_model

    # ── 不支持联网获取的厂商 ──
    else:
        if ml_note:
            st.info(f"💡 {ml_note}")
        selected_model = st.text_input(
            "模型名（手动输入）：",
            value=default_model,
            key="ai_model_input_manual",
            placeholder="输入模型名或 Endpoint ID",
        )
        st.session_state._ai_model = selected_model

    # ── 自动保存设置 ──
    _save_current_settings(
        provider_key=provider_key,
        api_key=user_api_key,
        model=st.session_state.get("_ai_model", ""),
        remember=remember_me,
    )

    # ---- 测试连接 ----
    st.markdown("---")
    if location == "sidebar":
        st.markdown("##### 4. 测试连接")
    else:
        st.markdown("#### 4. 测试连接")
    tc1, tc2 = st.columns([1, 3])
    with tc1:
        test_btn = st.button("🔌 测试连接", key="ai_test_connection")
    with tc2:
        test_placeholder = st.empty()

    if test_btn:
        if not resolved_api_key:
            test_placeholder.error("❌ 请先输入 API Key。")
        elif not st.session_state.get("_ai_model"):
            test_placeholder.error("❌ 请先输入模型名。")
        else:
            with st.spinner("正在测试连接…"):
                test_result = test_connection(
                    provider_config=provider_config,
                    api_key=resolved_api_key,
                    model=st.session_state.get("_ai_model", ""),
                    provider_key=provider_key,
                    chat_path=custom_chat_path if provider_key == "custom_openai" else "/chat/completions",
                )
            if test_result.get("success"):
                usage = test_result.get("usage", {})
                test_placeholder.success(
                    f"✅ 连接成功！模型 `{st.session_state.get('_ai_model', '')}` 响应正常。"
                    f"（Token: {usage.get('total_tokens', 'N/A')}）"
                )
            else:
                # 脱敏处理：不要原样显示 API Key
                error_msg = test_result.get('error', '未知错误')
                if resolved_api_key and len(resolved_api_key) > 8:
                    masked_key = resolved_api_key[:4] + "****" + resolved_api_key[-4:]
                    error_msg = error_msg.replace(resolved_api_key, masked_key)
                # 使用用户友好的错误分类
                friendly = format_user_friendly_error(error_msg, context="连接测试")
                test_placeholder.error(friendly)
                with st.expander("🔍 技术详情"):
                    st.code(error_msg)


def get_api_status_summary() -> Dict[str, Any]:
    """Return a dict summarising the current API configuration status.

    Safe to call even before ``render_api_config_section`` has run —
    reads from session_state only.
    """
    provider_key = st.session_state.get("_provider_key", "")
    api_key = st.session_state.get("_api_key", "")
    model = st.session_state.get("_ai_model", "")
    provider_config = st.session_state.get("_provider_config", {})

    return {
        "configured": bool(api_key and model),
        "provider_key": provider_key,
        "provider_display": provider_config.get("display_name", provider_key),
        "model": model,
        "has_api_key": bool(api_key),
        "masked_key": mask_api_key(api_key) if api_key else "",
    }
