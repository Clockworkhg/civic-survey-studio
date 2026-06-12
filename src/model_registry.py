"""模型注册表模块。

负责:
  - 从厂商 API 获取可用模型列表
  - 统一 normalize 不同厂商的响应格式
  - 缓存到 cache/model_catalog.json（不缓存 API Key）
  - 提供手动输入模型名功能
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

import requests

from src.provider_config import build_auth_headers, get_query_key

logger = logging.getLogger(__name__)

CACHE_FILE = Path(__file__).resolve().parent.parent / "cache" / "model_catalog.json"
CACHE_TTL_SECONDS = 3600  # 1 小时


# ================================================================
# 缓存读写（不保存 API Key）
# ================================================================

def _load_cache() -> Dict[str, Any]:
    """加载模型缓存。"""
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 安全清理：确保没有 API Key 混入
        for key in list(data.keys()):
            entry = data[key]
            if isinstance(entry, dict):
                entry.pop("api_key", None)
                entry.pop("API_KEY", None)
        return data
    except (json.JSONDecodeError, IOError):
        return {}


def _save_cache(cache: Dict[str, Any]) -> None:
    """保存模型缓存。绝不写入 API Key。"""
    # 深拷贝并清理任何可能的 API Key
    clean = {}
    for key, entry in cache.items():
        if isinstance(entry, dict):
            clean_entry = {k: v for k, v in entry.items()
                          if k not in ("api_key", "API_KEY")}
            clean[key] = clean_entry
        else:
            clean[key] = entry

    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2, ensure_ascii=False)


def _is_cache_valid(cache_entry: Optional[Dict]) -> bool:
    """检查缓存条目是否在有效期内。"""
    if not cache_entry:
        return False
    updated_at = cache_entry.get("updated_at", 0)
    return (time.time() - updated_at) < CACHE_TTL_SECONDS


# ================================================================
# 公开 API：load_cached_models / save_cached_models
# ================================================================

def load_cached_models(provider_key: str) -> Dict[str, Any]:
    """从缓存读取某厂商的模型列表。

    Returns:
        {"models": [...], "updated_at": timestamp, "provider_key": str}
        无缓存时返回 {"models": [], "updated_at": None}
    """
    cache = _load_cache()
    cache_key = f"{provider_key}_models"
    entry = cache.get(cache_key)
    if entry:
        return {
            "models": entry.get("models", []),
            "updated_at": entry.get("updated_at"),
            "provider_key": provider_key,
        }
    return {"models": [], "updated_at": None, "provider_key": provider_key}


def save_cached_models(provider_key: str, models: List[Dict[str, Any]]) -> None:
    """保存某厂商的模型列表到缓存。不保存 API Key。"""
    cache = _load_cache()
    cache_key = f"{provider_key}_models"
    cache[cache_key] = {
        "models": models,
        "updated_at": time.time(),
        "provider_key": provider_key,
    }
    _save_cache(cache)


# ================================================================
# 主入口：get_available_models
# ================================================================

def get_available_models(
    provider_key: str,
    provider_config: Dict[str, Any],
    api_key: str = "",
    refresh: bool = False,
    custom_options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """获取某厂商的可用模型列表（缓存优先，可选刷新）。

    Args:
        provider_key: 厂商 key
        provider_config: 厂商配置（来自 llm_providers.yaml）
        api_key: API Key
        refresh: True 时强制跳过缓存，联网获取
        custom_options: 可选自定义项:
            - model_list_path: 自定义模型列表路径
            - response_format: 自定义响应格式
            - query_params: 额外的查询参数

    Returns:
        {
            "success": bool,
            "models": [{"id": ..., "name": ..., ...}, ...],
            "updated_at": float or None,
            "source": "remote" | "cache" | "cache_expired" | None,
            "error": str or None,
        }
    """
    model_list_cfg = provider_config.get("model_list", {})
    is_enabled = model_list_cfg.get("enabled", False)

    # 自定义选项覆盖
    if custom_options:
        model_list_cfg = dict(model_list_cfg)
        if custom_options.get("model_list_path"):
            model_list_cfg["path"] = custom_options["model_list_path"]
        if custom_options.get("response_format"):
            model_list_cfg["response_format"] = custom_options["response_format"]
        if custom_options.get("query_params"):
            model_list_cfg["query_params"] = custom_options["query_params"]

    if not is_enabled:
        return {
            "success": False,
            "models": [],
            "updated_at": None,
            "source": None,
            "error": model_list_cfg.get("note", "该厂商不支持自动获取模型列表，请手动输入模型名。"),
        }

    # ── 非刷新模式：优先读缓存 ──
    if not refresh:
        cached = load_cached_models(provider_key)
        if cached["models"] and cached["updated_at"]:
            entry = _load_cache().get(f"{provider_key}_models", {})
            if _is_cache_valid(entry):
                return {
                    "success": True,
                    "models": cached["models"],
                    "updated_at": cached["updated_at"],
                    "source": "cache",
                    "error": None,
                }
            else:
                # 过期缓存也返回（标注来源）
                return {
                    "success": True,
                    "models": cached["models"],
                    "updated_at": cached["updated_at"],
                    "source": "cache_expired",
                    "error": None,
                }

    # ── 刷新模式：联网获取 ──
    try:
        result = _request_model_list(provider_config, api_key, model_list_cfg)
        if result["success"]:
            save_cached_models(provider_key, result["models"])
            return {
                "success": True,
                "models": result["models"],
                "updated_at": time.time(),
                "source": "remote",
                "error": None,
            }
        else:
            # 联网失败，回退缓存
            cached = load_cached_models(provider_key)
            if cached["models"]:
                return {
                    "success": True,
                    "models": cached["models"],
                    "updated_at": cached["updated_at"],
                    "source": "cache_expired",
                    "error": result.get("error", "刷新失败，使用过期缓存"),
                }
            return {
                "success": False,
                "models": [],
                "updated_at": None,
                "source": None,
                "error": result.get("error", "获取模型列表失败"),
            }
    except Exception as e:
        logger.error(f"获取模型列表异常 [{provider_key}]: {e}")
        cached = load_cached_models(provider_key)
        if cached["models"]:
            return {
                "success": True,
                "models": cached["models"],
                "updated_at": cached["updated_at"],
                "source": "cache_expired",
                "error": f"刷新失败（{str(e)[:100]}），使用过期缓存",
            }
        return {
            "success": False,
            "models": [],
            "updated_at": None,
            "source": None,
            "error": str(e)[:300],
        }


# ================================================================
# 兼容旧接口
# ================================================================

def fetch_model_list(
    provider_config: Dict[str, Any],
    api_key: str,
    provider_key: str = "",
) -> Dict[str, Any]:
    """从厂商 API 获取模型列表（兼容旧接口，内部调用 get_available_models）。

    优先读缓存；缓存过期或不存在时发起 HTTP 请求。
    """
    return get_available_models(
        provider_key=provider_key,
        provider_config=provider_config,
        api_key=api_key,
        refresh=False,
    )


def get_cached_models(provider_key: str) -> List[Dict[str, str]]:
    """从缓存中获取某厂商的模型列表（不发起网络请求，返回简化格式）。"""
    cached = load_cached_models(provider_key)
    return cached.get("models", [])


def clear_model_cache() -> None:
    """清除所有模型缓存。"""
    if CACHE_FILE.exists():
        CACHE_FILE.unlink()


# ================================================================
# HTTP 请求
# ================================================================

def _request_model_list(
    provider_config: Dict[str, Any],
    api_key: str,
    model_list_cfg: Dict[str, Any],
) -> Dict[str, Any]:
    """执行模型列表 HTTP 请求。"""
    base_url = provider_config.get("base_url", "").rstrip("/")
    path = model_list_cfg.get("path", "/models")
    method = model_list_cfg.get("method", "GET").upper()
    response_format = model_list_cfg.get("response_format", "openai_models")

    url = f"{base_url}{path}"

    # 请求头
    auth_type = model_list_cfg.get("auth_type", "")
    if not auth_type:
        # 回退到 provider 级别的 auth
        auth_type = provider_config.get("auth", {}).get("type", "bearer")

    headers = {}
    if auth_type in ("bearer", "api_key_header"):
        headers = build_auth_headers(provider_config, api_key)
    elif auth_type == "query_key":
        headers = {"Content-Type": "application/json"}
    else:
        headers = {"Content-Type": "application/json"}

    # query_key 鉴权
    if auth_type == "query_key":
        qk = get_query_key(provider_config, api_key)
        if qk:
            sep = "&" if "?" in url else "?"
            url += f"{sep}{qk[0]}={qk[1]}"
    else:
        # 也检查 provider 级别的 query_key
        qk = get_query_key(provider_config, api_key)
        if qk:
            sep = "&" if "?" in url else "?"
            url += f"{sep}{qk[0]}={qk[1]}"

    # 自定义 query_params
    query_params = model_list_cfg.get("query_params", {})
    if query_params:
        for k, v in query_params.items():
            sep = "&" if "?" in url else "?"
            url += f"{sep}{k}={v}"

    # 发起请求
    try:
        resp = requests.request(method, url, headers=headers, timeout=30)
    except requests.exceptions.Timeout:
        return {"success": False, "models": [], "error": "请求超时（30s）"}
    except requests.exceptions.ConnectionError as e:
        return {"success": False, "models": [], "error": f"连接失败: {str(e)[:200]}"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "models": [], "error": f"请求异常: {str(e)[:200]}"}

    if resp.status_code != 200:
        return {
            "success": False,
            "models": [],
            "error": f"HTTP {resp.status_code}: {resp.text[:300]}",
        }

    try:
        data = resp.json()
    except json.JSONDecodeError as e:
        return {"success": False, "models": [], "error": f"JSON 解析失败: {str(e)[:200]}"}

    # 解析响应
    models = normalize_model_list(data, response_format)
    return {"success": True, "models": models}


# ================================================================
# normalize_model_list — 统一模型列表格式
# ================================================================

def normalize_model_list(
    raw_response: Union[Dict, List],
    response_format: str = "openai_models",
) -> List[Dict[str, Any]]:
    """将不同厂商的原始响应统一转换为模型列表。

    统一输出格式:
        [{
            "id": "model-id",
            "name": "human-readable name",
            "owned_by": "",
            "description": "",
            "context_length": null,
            "input_price": null,
            "output_price": null,
        }, ...]

    Args:
        raw_response: API 原始响应（dict 或 list）
        response_format: 响应格式类型

    Supported formats:
        - openai_models     — OpenAI /v1/models (兼容 DeepSeek, Groq, OpenRouter 等)
        - openrouter_models — OpenRouter /api/v1/models
        - gemini_models     — Google Gemini /v1beta/models
        - siliconflow_models— SiliconFlow /v1/models
        - anthropic_models  — Anthropic /v1/models (预留)
        - generic_models    — 自动探测常见结构
    """
    if raw_response is None:
        return []

    raw_models = []

    # ── 按格式提取原始条目 ──
    if response_format == "openai_models":
        # {"data": [{"id": "...", "object": "model", ...}, ...]}
        raw_models = _safe_list(raw_response, "data")

    elif response_format == "openrouter_models":
        # 同 OpenAI 格式，但字段更丰富
        raw_models = _safe_list(raw_response, "data")

    elif response_format == "gemini_models":
        # {"models": [{"name": "models/gemini-2.0-flash", "supportedGenerationMethods": [...]}, ...]}
        raw_models = _safe_list(raw_response, "models")
        # 过滤：只保留支持 generateContent 的模型
        raw_models = [
            m for m in raw_models
            if isinstance(m, dict) and (
                "generateContent" in m.get("supportedGenerationMethods", []) or
                "streamGenerateContent" in m.get("supportedGenerationMethods", [])
            )
        ]

    elif response_format == "siliconflow_models":
        # SiliconFlow 兼容 OpenAI 格式: {"data": [...]}
        raw_models = _safe_list(raw_response, "data")
        if not raw_models:
            # 备用：{"models": [...]} 或 {"data": {"models": [...]}}
            raw_models = _safe_list(raw_response, "models")

    elif response_format == "anthropic_models":
        # {"data": [{"id": "...", "display_name": "...", ...}, ...]}
        raw_models = _safe_list(raw_response, "data")

    elif response_format == "generic_models":
        # 自动探测：data → models → items → 列表本身
        raw_models = _detect_model_list(raw_response)

    else:
        # 未知格式，尝试自动探测
        raw_models = _detect_model_list(raw_response)

    # ── 统一归一化 ──
    normalized = []
    for item in raw_models:
        if isinstance(item, str):
            normalized.append(_make_model_entry(id=item, name=item))
        elif isinstance(item, dict):
            model_id = (
                item.get("id")
                or _strip_gemini_prefix(item.get("name", ""))
                or item.get("model")
                or ""
            )
            if not model_id:
                continue

            name = (
                item.get("name")
                or item.get("display_name")
                or item.get("displayName")
                or model_id
            )
            # 去除 Gemini models/ 前缀
            name = _strip_gemini_prefix(name)

            normalized.append(_make_model_entry(
                id=model_id,
                name=name,
                owned_by=item.get("owned_by", ""),
                description=item.get("description", ""),
                context_length=item.get("context_length") or item.get("max_tokens"),
                input_price=item.get("input_price") or item.get("pricing", {}).get("prompt"),
                output_price=item.get("output_price") or item.get("pricing", {}).get("completion"),
            ))

    # ── 过滤非对话模型 ──
    skip_patterns = [
        "whisper", "tts", "dall-e", "embedding", "moderation",
        "text-embedding", "audio", "vision", "image-gen",
    ]
    filtered = []
    for m in normalized:
        mid = m["id"].lower()
        if any(p in mid for p in skip_patterns):
            continue
        filtered.append(m)

    return filtered


# ================================================================
# normalize 辅助
# ================================================================

def _safe_list(data: Union[Dict, List], key: str) -> List:
    """安全地从 dict 中提取 list。"""
    if isinstance(data, dict):
        val = data.get(key, [])
        return val if isinstance(val, list) else []
    if isinstance(data, list):
        return data
    return []


def _detect_model_list(data: Union[Dict, List]) -> List:
    """自动探测模型列表在响应中的位置。"""
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []

    for key in ("data", "models", "items", "results"):
        val = data.get(key)
        if isinstance(val, list):
            return val
        elif isinstance(val, dict):
            # 嵌套结构：{"data": {"models": [...]}}
            for sub_key in ("models", "items", "data"):
                sub_val = val.get(sub_key)
                if isinstance(sub_val, list):
                    return sub_val

    return []


def _strip_gemini_prefix(name: str) -> str:
    """去除 Gemini 的 models/ 前缀。"""
    if name.startswith("models/"):
        return name[len("models/"):]
    return name


def _make_model_entry(
    id: str,
    name: str,
    owned_by: str = "",
    description: str = "",
    context_length: Any = None,
    input_price: Any = None,
    output_price: Any = None,
) -> Dict[str, Any]:
    """创建标准模型条目。"""
    return {
        "id": id,
        "name": name,
        "owned_by": owned_by,
        "description": description,
        "context_length": context_length,
        "input_price": input_price,
        "output_price": output_price,
    }
