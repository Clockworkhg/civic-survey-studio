"""Tests for format_user_friendly_error — error classification and mapping."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from src.ui.messages import format_user_friendly_error


# ================================================================
# Helper
# ================================================================

def _assert_keywords_in(msg: str, *keywords: str):
    """Assert that at least one keyword is present in msg."""
    for kw in keywords:
        if kw in msg:
            return
    pytest.fail(f"None of {keywords} found in message: {msg[:200]}")


# ================================================================
# API Key errors
# ================================================================

class TestApiKeyErrors:
    def test_unauthorized_401(self):
        msg = format_user_friendly_error("401 Unauthorized")
        _assert_keywords_in(msg, "API Key", "无效", "缺失")

    def test_invalid_api_key(self):
        msg = format_user_friendly_error("invalid api key")
        _assert_keywords_in(msg, "API Key", "无效", "缺失")

    def test_incorrect_api_key(self):
        msg = format_user_friendly_error("incorrect api key provided")
        _assert_keywords_in(msg, "API Key", "无效", "缺失")

    def test_authentication_failed(self):
        msg = format_user_friendly_error("authentication failed")
        _assert_keywords_in(msg, "API Key", "无效", "缺失")

    def test_forbidden_403(self):
        msg = format_user_friendly_error("403 Forbidden")
        _assert_keywords_in(msg, "访问被拒绝", "配额", "余额", "权限")

    def test_insufficient_permissions(self):
        msg = format_user_friendly_error("insufficient permissions")
        _assert_keywords_in(msg, "访问被拒绝", "余额", "权限")

    def test_billing_quota(self):
        msg = format_user_friendly_error("billing quota exceeded")
        _assert_keywords_in(msg, "访问被拒绝", "余额", "配额")


# ================================================================
# Network errors
# ================================================================

class TestNetworkErrors:
    def test_connection_refused(self):
        msg = format_user_friendly_error("Connection refused")
        _assert_keywords_in(msg, "网络", "连接")

    def test_timeout(self):
        msg = format_user_friendly_error("Request timed out")
        _assert_keywords_in(msg, "超时", "网络", "重试")

    def test_dns_resolution(self):
        msg = format_user_friendly_error("Name or service not known")
        _assert_keywords_in(msg, "网络", "连接")

    def test_unreachable(self):
        msg = format_user_friendly_error("Host unreachable")
        _assert_keywords_in(msg, "网络", "连接")


# ================================================================
# Model errors
# ================================================================

class TestModelErrors:
    def test_model_not_found(self):
        msg = format_user_friendly_error("model not found")
        _assert_keywords_in(msg, "模型", "拼写", "可用")

    def test_invalid_model(self):
        msg = format_user_friendly_error("invalid model name")
        _assert_keywords_in(msg, "模型", "拼写", "可用")

    def test_model_does_not_exist(self):
        msg = format_user_friendly_error("The model does not exist")
        _assert_keywords_in(msg, "模型", "拼写", "可用")


# ================================================================
# Empty response errors
# ================================================================

class TestEmptyResponseErrors:
    def test_empty_response(self):
        msg = format_user_friendly_error("empty response from model")
        _assert_keywords_in(msg, "返回", "空")

    def test_no_content(self):
        msg = format_user_friendly_error("返回内容为空")
        _assert_keywords_in(msg, "返回", "空")


# ================================================================
# Server errors
# ================================================================

class TestServerErrors:
    def test_500_error(self):
        msg = format_user_friendly_error("500 Internal Server Error")
        _assert_keywords_in(msg, "服务端", "不可用")

    def test_503_error(self):
        msg = format_user_friendly_error("503 Service Unavailable")
        _assert_keywords_in(msg, "服务端", "不可用")

    def test_overloaded(self):
        msg = format_user_friendly_error("server overloaded")
        _assert_keywords_in(msg, "服务端", "不可用")


# ================================================================
# Rate limit errors
# ================================================================

class TestRateLimitErrors:
    def test_rate_limit(self):
        msg = format_user_friendly_error("rate limit exceeded")
        _assert_keywords_in(msg, "频率", "限流")

    def test_too_many_requests_429(self):
        msg = format_user_friendly_error("429 Too Many Requests")
        _assert_keywords_in(msg, "频率", "限流")


# ================================================================
# Payload errors
# ================================================================

class TestPayloadErrors:
    def test_empty_payload(self):
        msg = format_user_friendly_error("analysis payload is empty")
        _assert_keywords_in(msg, "分析结果", "不完整", "生成")

    def test_no_analysis_results(self):
        msg = format_user_friendly_error("no analysis results found")
        _assert_keywords_in(msg, "分析结果", "不完整", "生成")


# ================================================================
# Context handling
# ================================================================

class TestContextHandling:
    def test_context_appears_in_message(self):
        msg = format_user_friendly_error("401 Unauthorized", context="文献检索")
        assert "文献检索" in msg

    def test_custom_context(self):
        msg = format_user_friendly_error("timeout", context="模型获取")
        assert "模型获取" in msg

    def test_no_context_default(self):
        msg = format_user_friendly_error("timeout")
        assert "操作失败" in msg


# ================================================================
# Exception input
# ================================================================

class TestExceptionInput:
    def test_handles_exception_object(self):
        exc = Exception("401 Unauthorized")
        msg = format_user_friendly_error(exc)
        assert "API Key" in msg or "无效" in msg

    def test_handles_non_string_object(self):
        msg = format_user_friendly_error(42)
        assert isinstance(msg, str)
        assert len(msg) > 20


# ================================================================
# Fallback
# ================================================================

class TestFallback:
    def test_unknown_error_includes_original(self):
        msg = format_user_friendly_error("some completely unknown error XYZ123")
        assert "XYZ123" in msg

    def test_fallback_mentions_troubleshooting(self):
        msg = format_user_friendly_error("bizarre unknown thing")
        assert "API Key" in msg or "网络" in msg or "模型" in msg
