"""统一 LLM 客户端模块。

支持的协议:
  - openai_compatible        — 标准 OpenAI Chat Completions API
  - custom_openai_compatible — 用户自定义 OpenAI Compatible API
  - gemini_native            — Google Gemini 原生 GenerateContent API
  - anthropic_native         — 预留接口

调用方只需传 provider_config + 参数，无需关心底层 HTTP 细节。
"""

import json
import logging
from typing import Optional, Dict, Any

import requests

from src.provider_config import build_auth_headers, get_query_key

logger = logging.getLogger(__name__)


# ================================================================
# 公开接口
# ================================================================

def call_llm(
    provider_config: Dict[str, Any] = None,
    api_key: str = "",
    model: str = "",
    system_prompt: str = "",
    user_prompt: str = "",
    temperature: float = 0.3,
    max_tokens: int = 4096,
    provider_key: str = "",
    chat_path: str = "/chat/completions",
    extra_headers: Optional[Dict[str, str]] = None,
    response_format: Optional[Dict[str, Any]] = None,
    # P1.6: unified LLMConfig takes precedence over flat params
    llm_config: Any = None,
) -> Dict[str, Any]:
    """统一 LLM 调用入口。

    根据 provider_config 中的 protocol 字段路由到对应的实现。

    Args:
        provider_config: 厂商配置（来自 llm_providers.yaml）
        api_key: API Key
        model: 模型名
        system_prompt: 系统提示
        user_prompt: 用户提示
        temperature: 温度参数（0-2）
        max_tokens: 最大输出 token
        provider_key: 厂商 key（用于返回结果标识）
        chat_path: 自定义 API 路径（仅 custom_openai_compatible 生效）
        extra_headers: 额外 HTTP 头（仅 custom_openai_compatible 生效）
        llm_config: 可选。LLMConfig 对象。传入后优先于各独立参数。

    Returns:
        {
            "success": bool,
            "content": str,        # 成功时
            "raw": dict,           # 原始响应
            "usage": dict,         # token 用量
            "provider": str,
            "model": str,
            "error": str,          # 失败时
        }
    """
    # ── P1.6: LLMConfig 优先 ──
    if llm_config is not None:
        provider_config = llm_config.provider_config or provider_config or {}
        api_key = llm_config.api_key or api_key
        model = llm_config.model or model
        temperature = llm_config.temperature
        max_tokens = llm_config.max_tokens
        if llm_config.provider_key:
            provider_key = llm_config.provider_key
        if llm_config.chat_path:
            chat_path = llm_config.chat_path
        if llm_config.extra_headers is not None:
            extra_headers = llm_config.extra_headers

    if provider_config is None:
        provider_config = {}

    protocol = provider_config.get("protocol", "openai_compatible")
    provider_name = provider_config.get("display_name", provider_key)

    try:
        if protocol == "gemini_native":
            return _call_gemini_native(
                provider_config, api_key, model,
                system_prompt, user_prompt, temperature, max_tokens,
                provider_key, provider_name,
            )
        elif protocol == "anthropic_native":
            return _call_anthropic_native(
                provider_config, api_key, model,
                system_prompt, user_prompt, temperature, max_tokens,
                provider_key, provider_name,
            )
        elif protocol == "custom_openai_compatible":
            return _call_openai_compatible(
                provider_config, api_key, model,
                system_prompt, user_prompt, temperature, max_tokens,
                provider_key, provider_name,
                chat_path=chat_path,
                extra_headers=extra_headers,
                response_format=response_format,
            )
        else:
            # openai_compatible (默认)
            return _call_openai_compatible(
                provider_config, api_key, model,
                system_prompt, user_prompt, temperature, max_tokens,
                provider_key, provider_name,
                response_format=response_format,
            )
    except Exception as e:
        logger.error(f"LLM 调用异常 [{provider_key}]: {e}")
        return {
            "success": False,
            "error": f"调用异常: {str(e)}",
            "provider": provider_key,
            "model": model,
        }


# ================================================================
# OpenAI Compatible
# ================================================================

def _call_openai_compatible(
    provider_config: Dict[str, Any],
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    provider_key: str,
    provider_name: str,
    chat_path: str = "/chat/completions",
    extra_headers: Optional[Dict[str, str]] = None,
    response_format: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """OpenAI Compatible Chat Completions API 调用。"""

    base_url = provider_config.get("base_url", "").rstrip("/")
    if not base_url:
        return {
            "success": False,
            "error": "厂商 base_url 未配置。",
            "provider": provider_key,
            "model": model,
        }

    url = f"{base_url}{chat_path}"

    # 请求头
    headers = build_auth_headers(provider_config, api_key)
    if extra_headers:
        headers.update(extra_headers)

    # 请求体
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        payload["response_format"] = response_format

    # API 调用
    try:
        resp = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=120,
        )
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "请求超时（120s）。请检查网络或 API 服务状态。",
            "provider": provider_key,
            "model": model,
        }
    except requests.exceptions.ConnectionError as e:
        return {
            "success": False,
            "error": f"连接失败: {str(e)}。请检查 base_url 和网络。",
            "provider": provider_key,
            "model": model,
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"网络请求异常: {str(e)}",
            "provider": provider_key,
            "model": model,
        }

    # 响应处理
    if resp.status_code == 200:
        try:
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")
            else:
                content = ""

            usage = data.get("usage", {})
            return {
                "success": True,
                "content": content,
                "raw": data,
                "usage": {
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
                "provider": provider_key,
                "model": model,
            }
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            return {
                "success": False,
                "error": f"解析响应失败: {str(e)}",
                "provider": provider_key,
                "model": model,
            }

    # 错误响应
    error_msg = f"HTTP {resp.status_code}"
    try:
        err_data = resp.json()
        if "error" in err_data:
            err_detail = err_data["error"]
            if isinstance(err_detail, dict):
                error_msg = err_detail.get("message", str(err_detail))
            else:
                error_msg = str(err_detail)
    except Exception:
        error_msg = resp.text[:500] if resp.text else error_msg

    return {
        "success": False,
        "error": error_msg,
        "provider": provider_key,
        "model": model,
    }


# ================================================================
# Gemini Native
# ================================================================

def _call_gemini_native(
    provider_config: Dict[str, Any],
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    provider_key: str,
    provider_name: str,
) -> Dict[str, Any]:
    """Google Gemini 原生 GenerateContent API 调用。

    URL: POST {base_url}/models/{model}:generateContent?key={API_KEY}
    """

    base_url = provider_config.get("base_url", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
    url = f"{base_url}/models/{model}:generateContent"

    # query_key 鉴权
    qk = get_query_key(provider_config, api_key)
    if qk:
        url += f"?{qk[0]}={qk[1]}"
    elif api_key:
        url += f"?key={api_key}"

    # 构建 contents
    contents = []
    if system_prompt:
        # Gemini 通过 systemInstruction 支持系统提示
        pass  # 在 payload 中处理

    parts = [{"text": user_prompt}]
    contents.append({"role": "user", "parts": parts})

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    if system_prompt:
        payload["systemInstruction"] = {
            "parts": [{"text": system_prompt}]
        }

    try:
        resp = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=120,
        )
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "请求超时（120s）。请检查网络或 API 服务状态。",
            "provider": provider_key,
            "model": model,
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"网络请求异常: {str(e)}",
            "provider": provider_key,
            "model": model,
        }

    if resp.status_code == 200:
        try:
            data = resp.json()
            candidates = data.get("candidates", [])
            content = ""
            if candidates:
                candidate = candidates[0]
                content_parts = candidate.get("content", {}).get("parts", [])
                content = "".join(p.get("text", "") for p in content_parts)

            usage = data.get("usageMetadata", {})
            return {
                "success": True,
                "content": content,
                "raw": data,
                "usage": {
                    "prompt_tokens": usage.get("promptTokenCount", 0),
                    "completion_tokens": usage.get("candidatesTokenCount", 0),
                    "total_tokens": usage.get("totalTokenCount", 0),
                },
                "provider": provider_key,
                "model": model,
            }
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            return {
                "success": False,
                "error": f"解析 Gemini 响应失败: {str(e)}",
                "provider": provider_key,
                "model": model,
            }

    error_msg = f"HTTP {resp.status_code}"
    try:
        err_data = resp.json()
        error_msg = str(err_data.get("error", {}).get("message", error_msg))
    except Exception:
        error_msg = resp.text[:500] if resp.text else error_msg

    return {
        "success": False,
        "error": error_msg,
        "provider": provider_key,
        "model": model,
    }


# ================================================================
# Anthropic Native (预留)
# ================================================================

def _call_anthropic_native(
    provider_config: Dict[str, Any],
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    provider_key: str,
    provider_name: str,
) -> Dict[str, Any]:
    """Anthropic Messages API（预留接口）。

    当前版本暂未完整实现。建议使用 OpenRouter 中转访问 Anthropic 模型。
    """
    return {
        "success": False,
        "error": (
            "Anthropic Native API 当前版本暂未完整实现。"
            "建议通过 OpenRouter 中转访问 Claude 模型，"
            "或使用自定义 OpenAI Compatible API 配置兼容代理。"
        ),
        "provider": provider_key,
        "model": model,
    }


# ================================================================
# 测试连接
# ================================================================

def test_connection(
    provider_config: Dict[str, Any],
    api_key: str,
    model: str,
    provider_key: str = "",
    chat_path: str = "/chat/completions",
    extra_headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """测试 LLM 连接是否可用。

    发送一条简短的 ping 消息，验证 API Key 和网络连通性。

    Returns:
        与 call_llm 相同的格式；success=True 表示连接正常。
    """
    return call_llm(
        provider_config=provider_config,
        api_key=api_key,
        model=model,
        system_prompt="",
        user_prompt="Hi",
        temperature=0,
        max_tokens=10,
        provider_key=provider_key,
        chat_path=chat_path,
        extra_headers=extra_headers,
    )
