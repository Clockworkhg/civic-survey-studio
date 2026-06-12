"""用户设置本地持久化模块。

将 AI 厂商选择、API Key、模型名保存到本地文件，
下次打开应用时自动加载，免去重复输入。

安全提示：API Key 以明文存储，仅建议在个人设备上使用此功能。
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


# 设置文件路径
def _settings_path() -> Path:
    return Path(__file__).resolve().parent.parent / "config" / "user_settings.json"


def save_user_settings(settings: Dict[str, Any]) -> bool:
    """保存用户设置到本地 JSON 文件。

    Args:
        settings: 包含 provider_key, api_key, model, remember 等字段的字典

    Returns:
        是否保存成功
    """
    try:
        path = _settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def load_user_settings() -> Optional[Dict[str, Any]]:
    """从本地文件加载用户设置。

    Returns:
        设置字典；文件不存在或损坏时返回 None
    """
    path = _settings_path()
    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            settings = json.load(f)
        if isinstance(settings, dict) and settings.get("remember"):
            return settings
        return None
    except (json.JSONDecodeError, IOError):
        return None


def clear_user_settings() -> bool:
    """删除本地用户设置文件。

    Returns:
        是否删除成功
    """
    try:
        path = _settings_path()
        if path.exists():
            os.remove(path)
        return True
    except Exception:
        return False
