"""LLM 厂商配置管理模块。

职责：
  - 读取 config/llm_providers.yaml
  - 提供按 key 获取厂商配置
  - API Key 获取（用户输入 > Streamlit secrets > 环境变量）
  - 根据 auth 字段构造请求头
"""

import os
import copy
from pathlib import Path
from typing import Optional, Dict, Any, List

import yaml


# ================================================================
# 配置文件路径
# ================================================================

def _config_path() -> Path:
    """获取 llm_providers.yaml 的绝对路径。"""
    return Path(__file__).resolve().parent.parent / "config" / "llm_providers.yaml"


# ================================================================
# 加载
# ================================================================

def load_provider_config() -> Dict[str, Any]:
    """读取 config/llm_providers.yaml，返回 providers 字典。

    Returns:
        {"providers": {...}, "openai": {...}, ...}
        顶层包含 "providers" 原始键，也按 provider key 平铺。
    """
    path = _config_path()
    if not path.exists():
        raise FileNotFoundError(
            f"LLM 厂商配置文件未找到: {path}\n"
            "请确保 config/llm_providers.yaml 存在。"
        )

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or "providers" not in data:
        raise ValueError("llm_providers.yaml 格式错误：缺少顶层 'providers' 键。")

    # 同时返回平铺访问（provider_key → config）和原始结构
    result = {"providers": data["providers"]}
    for key, cfg in data["providers"].items():
        result[key] = cfg
    return result


def get_provider(provider_key: str) -> Optional[Dict[str, Any]]:
    """根据 provider_key 获取某个厂商的完整配置。

    Args:
        provider_key: 如 "openai", "deepseek", "xiaomi_mimo"

    Returns:
        厂商配置字典；不存在时返回 None。
    """
    config = load_provider_config()
    providers = config.get("providers", {})
    return providers.get(provider_key)


def list_providers() -> List[Dict[str, Any]]:
    """列出所有厂商（简要信息），用于 UI 下拉框。

    Returns:
        [{"key": "openai", "display_name": "OpenAI", "protocol": "...", ...}, ...]
    """
    config = load_provider_config()
    result = []
    for key, cfg in config.get("providers", {}).items():
        result.append({
            "key": key,
            "display_name": cfg.get("display_name", key),
            "protocol": cfg.get("protocol", ""),
            "default_model": cfg.get("default_model", ""),
            "allow_custom_model": cfg.get("allow_custom_model", False),
            "api_key_env": cfg.get("api_key_env", ""),
        })
    return result


# ================================================================
# API Key
# ================================================================

def get_api_key(
    provider_config: Dict[str, Any],
    user_api_key: Optional[str] = None,
) -> str:
    """获取 API Key，优先级：用户输入 > Streamlit secrets > 环境变量。

    Args:
        provider_config: 厂商配置字典
        user_api_key: 用户在页面上输入的 API Key

    Returns:
        API Key 字符串；可能为空
    """
    # 1. 用户显式输入（优先）
    if user_api_key and user_api_key.strip():
        return user_api_key.strip()

    # 2. Streamlit secrets
    env_name = provider_config.get("api_key_env", "")
    if env_name:
        # 尝试从 st.secrets 读取（延迟导入以避免循环依赖）
        secret_val = _try_st_secret(env_name)
        if secret_val:
            return secret_val

    # 3. 环境变量
    if env_name:
        env_val = os.environ.get(env_name, "")
        if env_val:
            return env_val

    return ""


def _try_st_secret(env_name: str) -> str:
    """尝试从 Streamlit secrets 中读取 API Key。

    不会因为 st 不可用而报错。
    """
    try:
        import streamlit as st
        # st.secrets 是 dict-like，支持点号和下标访问
        if hasattr(st, "secrets"):
            secrets = st.secrets
            if secrets:
                # 尝试直接 key
                val = secrets.get(env_name)
                if val:
                    return str(val)
                # 尝试嵌套: llm_keys.openai 等
                for section in secrets:
                    section_data = secrets[section]
                    if isinstance(section_data, dict):
                        val = section_data.get(env_name)
                        if val:
                            return str(val)
    except Exception:
        pass
    return ""


# ================================================================
# Auth Headers
# ================================================================

def build_auth_headers(
    provider_config: Dict[str, Any],
    api_key: str,
) -> Dict[str, str]:
    """根据厂商 auth 配置构造 HTTP 请求头。

    支持:
      - bearer:         Authorization: Bearer <key>
      - api_key_header: 自定义 header（如 api-key: <key>）
      - query_key:      不写入 headers（由调用方添加到 URL 参数）

    Args:
        provider_config: 厂商配置字典
        api_key: API Key

    Returns:
        HTTP 请求头字典
    """
    auth_cfg = provider_config.get("auth", {})
    auth_type = auth_cfg.get("type", "bearer")

    headers = {}

    if auth_type == "bearer":
        header_name = auth_cfg.get("header_name", "Authorization")
        prefix = auth_cfg.get("prefix", "Bearer")
        headers[header_name] = f"{prefix} {api_key}".strip()

    elif auth_type == "api_key_header":
        header_name = auth_cfg.get("header_name", "api-key")
        prefix = auth_cfg.get("prefix", "")
        if prefix:
            headers[header_name] = f"{prefix} {api_key}".strip()
        else:
            headers[header_name] = api_key

    elif auth_type == "query_key":
        # query_key 不写入 header，由调用方附加到 URL
        pass

    # Content-Type
    headers["Content-Type"] = "application/json"

    return headers


def get_query_key(
    provider_config: Dict[str, Any],
    api_key: str,
) -> Optional[tuple]:
    """如果鉴权方式为 query_key，返回 (参数名, 参数值)。

    Returns:
        (param_name, api_key) 或 None
    """
    auth_cfg = provider_config.get("auth", {})
    if auth_cfg.get("type") == "query_key":
        param_name = auth_cfg.get("param_name", "key")
        return (param_name, api_key)
    return None
