"""Verify that call_llm() natively supports LLMConfig.

No real API calls — all tests use mocking.

Checks:
1. call_llm(llm_config=...) reads all fields from LLMConfig
2. Old flat-param call style still works
3. llm_config takes precedence over flat params
4. Mixed usage: llm_config + overriding individual params
5. call_llm() without any config defaults properly
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Mock response for a successful call
MOCK_SUCCESS = {
    "success": True,
    "content": "AI response",
    "raw": {"choices": [{"message": {"content": "AI response"}}]},
    "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    "provider": "test_provider",
    "model": "test-model",
}


class TestCallLlmWithLLMConfig:
    """Verify call_llm() handles LLMConfig correctly."""

    @pytest.fixture
    def llm_config(self):
        from src.config_models import LLMConfig
        return LLMConfig(
            provider_config={"base_url": "https://api.test.com", "protocol": "custom_openai_compatible"},
            api_key="sk-config-key",
            model="config-model",
            temperature=0.5,
            max_tokens=2048,
            provider_key="config_provider",
            chat_path="/v1/chat",
            extra_headers={"X-Custom": "config"},
        )

    def test_call_llm_with_llm_config_reads_provider_config(self, llm_config):
        """llm_config.provider_config should be used as the provider_config."""
        from src.llm_client import call_llm

        with patch("src.llm_client.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": "OK"}}],
                "usage": {},
            }
            mock_post.return_value = mock_resp

            result = call_llm(
                system_prompt="sys",
                user_prompt="usr",
                llm_config=llm_config,
            )

        assert result["success"] is True
        call_args = mock_post.call_args
        url = call_args[0][0]
        assert "api.test.com" in url
        assert "/v1/chat" in url

    def test_call_llm_with_llm_config_uses_model(self, llm_config):
        """llm_config.model should be used."""
        from src.llm_client import call_llm

        with patch("src.llm_client.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": "OK"}}],
                "usage": {},
            }
            mock_post.return_value = mock_resp

            call_llm(llm_config=llm_config)

        payload = mock_post.call_args[1]["json"]
        assert payload["model"] == "config-model"
        assert payload["temperature"] == 0.5
        assert payload["max_tokens"] == 2048

    def test_call_llm_with_llm_config_uses_provider_key(self, llm_config):
        """llm_config.provider_key should be used in the result."""
        from src.llm_client import call_llm

        with patch("src.llm_client.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": "OK"}}],
                "usage": {},
            }
            mock_post.return_value = mock_resp

            result = call_llm(llm_config=llm_config)

        assert result["provider"] == "config_provider"
        assert result["model"] == "config-model"

    # ── Backward compatibility: old flat params still work ──

    def test_call_llm_flat_params_still_work(self):
        """Old-style flat parameters should still work without llm_config."""
        from src.llm_client import call_llm

        with patch("src.llm_client.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": "OK"}}],
                "usage": {},
            }
            mock_post.return_value = mock_resp

            result = call_llm(
                provider_config={"base_url": "https://old.api.com", "protocol": "openai_compatible"},
                api_key="sk-old",
                model="old-model",
                temperature=0.7,
                max_tokens=1024,
                provider_key="old_provider",
            )

        assert result["success"] is True
        payload = mock_post.call_args[1]["json"]
        assert payload["model"] == "old-model"
        assert payload["temperature"] == 0.7
        assert payload["max_tokens"] == 1024

    def test_call_llm_flat_params_with_zero_temperature(self):
        """Temperature=0 should NOT be overridden by default 0.3."""
        from src.llm_client import call_llm

        with patch("src.llm_client.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": "OK"}}],
                "usage": {},
            }
            mock_post.return_value = mock_resp

            call_llm(
                provider_config={"base_url": "https://api.test.com", "protocol": "openai_compatible"},
                api_key="sk",
                model="m",
                temperature=0.0,  # Explicit zero should be respected
            )

        payload = mock_post.call_args[1]["json"]
        assert payload["temperature"] == 0.0

    # ── llm_config takes precedence ──

    def test_llm_config_overrides_flat_params(self, llm_config):
        """When llm_config is provided, its values should override flat params."""
        from src.llm_client import call_llm

        with patch("src.llm_client.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": "OK"}}],
                "usage": {},
            }
            mock_post.return_value = mock_resp

            call_llm(
                provider_config={"base_url": "https://should-be-overridden.com"},
                api_key="sk-should-override",
                model="should-override",
                temperature=0.9,
                max_tokens=999,
                llm_config=llm_config,
            )

        # llm_config values should win
        payload = mock_post.call_args[1]["json"]
        assert payload["model"] == "config-model"
        assert payload["temperature"] == 0.5
        assert payload["max_tokens"] == 2048
        call_url = mock_post.call_args[0][0]
        assert "api.test.com" in call_url

    # ── Extra headers from llm_config ──

    def test_call_llm_passes_extra_headers_from_config(self, llm_config):
        """Extra headers from LLMConfig should be passed to the HTTP request."""
        from src.llm_client import call_llm

        with patch("src.llm_client.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": "OK"}}],
                "usage": {},
            }
            mock_post.return_value = mock_resp

            call_llm(llm_config=llm_config)

        headers = mock_post.call_args[1]["headers"]
        assert "X-Custom" in headers
        assert headers["X-Custom"] == "config"

    # ── None / empty provider_config handling ──

    def test_call_llm_with_none_provider_config_and_no_llm_config(self):
        """call_llm() with no provider_config and no llm_config should error gracefully."""
        from src.llm_client import call_llm

        # No mock needed — should fail at base_url check
        result = call_llm(
            provider_config={},
            api_key="",
            model="",
        )
        assert result["success"] is False
        assert "base_url" in result.get("error", "").lower() or "error" in result

    def test_call_llm_with_none_llm_config_falls_back(self):
        """llm_config=None should fall back to flat params."""
        from src.llm_client import call_llm

        with patch("src.llm_client.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": "OK"}}],
                "usage": {},
            }
            mock_post.return_value = mock_resp

            result = call_llm(
                provider_config={"base_url": "https://fallback.api.com", "protocol": "openai_compatible"},
                api_key="sk-fallback",
                model="fallback-model",
                llm_config=None,
            )

        assert result["success"] is True
        payload = mock_post.call_args[1]["json"]
        assert payload["model"] == "fallback-model"


class TestCallLlmIntegrationWithAiReport:
    """Verify generate_ai_report passes llm_config through to call_llm."""

    def test_generate_ai_report_passes_llm_config_to_call_llm(self):
        """generate_ai_report should pass _llm as llm_config= to call_llm."""
        import pandas as pd
        import numpy as np
        from unittest.mock import patch, MagicMock
        from src.config_models import LLMConfig, ReportConfig

        llm_cfg = LLMConfig(
            api_key="sk-int",
            model="int-model",
            provider_config={"base_url": "https://int.api.com", "protocol": "custom_openai_compatible"},
        )
        rpt_cfg = ReportConfig(
            report_structure="通用调研报告",  # 通用调研报告
            report_style="学术报告风",           # 学术报告风
        )

        # Create minimal data
        np.random.seed(1)
        df = pd.DataFrame({"x": [1, 2, 3, 4, 5], "y": [0, 1, 0, 1, 0]})
        schema = pd.DataFrame([
            {"column": "x", "inferred_type": "numeric", "display_name": "X"},
            {"column": "y", "inferred_type": "binary", "display_name": "Y"},
        ])
        config = {
            "report_title": "Test",
            "target_variable": "y",
            "group_variables": [],
            "explanatory_variables": ["x"],
        }
        analysis = {"multivariate": None, "univariate": [], "bivariate": []}

        mock_llm_response = {"success": True, "content": "### Report\n\nTest report content."}

        # Patch both build_analysis_payload AND call_llm
        with patch("src.ai_report_generator.build_analysis_payload") as mock_payload:
            mock_payload.return_value = {
                "project_meta": {"report_title": "Test", "variable_name_map": {}},
                "data_overview": {"sample_size": 5},
                "variable_schema": [],
                "user_analysis_config": {"target_variable": "y"},
                "analysis_plan": [],
                "analysis_results": [],
                "chart_summaries": None,
                "warnings": [],
            }
            with patch("src.ai_report_generator.call_llm") as mock_call:
                mock_call.return_value = mock_llm_response
                from src.ai_report_generator import generate_ai_report

                result = generate_ai_report(
                    df=df,
                    schema_df=schema,
                    config=config,
                    analysis_results=analysis,
                    quality=None,
                    provider_config={},
                    api_key="",
                    model="",
                    llm_config=llm_cfg,
                    report_config=rpt_cfg,
                )

        assert result["success"], f"Should succeed: {result.get('error')}"
        # Verify call_llm was called with llm_config
        call_kwargs = mock_call.call_args[1]
        assert "llm_config" in call_kwargs
        passed_cfg = call_kwargs["llm_config"]
        assert passed_cfg.api_key == "sk-int"
        assert passed_cfg.model == "int-model"


class TestCallLlmErrorHandling:
    """Error handling in call_llm with llm_config."""

    def test_call_llm_http_error_with_llm_config(self):
        """HTTP errors should be surfaced correctly when using llm_config."""
        from src.config_models import LLMConfig
        from src.llm_client import call_llm

        llm_cfg = LLMConfig(
            provider_config={"base_url": "https://err.api.com"},
            api_key="sk",
            model="m",
        )

        with patch("src.llm_client.requests.post") as mock_post:
            mock_post.side_effect = Exception("Connection refused")

            result = call_llm(llm_config=llm_cfg)

        assert result["success"] is False
        assert "Connection refused" in result["error"]
        # Provider/model should still be set even on error
        assert "provider" in result
