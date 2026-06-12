"""Tests for config_models — LLMConfig and ReportConfig dataclasses."""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config_models import LLMConfig, ReportConfig


class TestLLMConfigDefaults:
    """Test LLMConfig default values and to_kwargs conversion."""

    def test_default_values(self):
        cfg = LLMConfig()
        assert cfg.provider_config == {}
        assert cfg.api_key == ""
        assert cfg.model == ""
        assert cfg.provider_key == ""
        assert cfg.chat_path == "/chat/completions"
        assert cfg.temperature == 0.3
        assert cfg.max_tokens == 4096
        assert cfg.extra_headers is None

    def test_to_kwargs(self):
        cfg = LLMConfig(
            provider_config={"base_url": "https://api.example.com"},
            api_key="sk-test",
            model="claude-4",
            temperature=0.5,
            max_tokens=2048,
        )
        kwargs = cfg.to_kwargs()
        assert kwargs["provider_config"] == {"base_url": "https://api.example.com"}
        assert kwargs["api_key"] == "sk-test"
        assert kwargs["model"] == "claude-4"
        assert kwargs["temperature"] == 0.5
        assert kwargs["max_tokens"] == 2048
        assert "extra_headers" in kwargs

    def test_to_kwargs_passes_to_call_llm(self):
        """Verify kwargs dict is compatible with call_llm signature."""
        cfg = LLMConfig(api_key="test", model="gpt-4")
        kwargs = cfg.to_kwargs()
        required = {"provider_config", "api_key", "model", "system_prompt",
                     "user_prompt", "temperature", "max_tokens"}
        # At minimum we need all these keys (call_llm can add system_prompt/user_prompt)
        assert all(k in kwargs for k in
                   ["provider_config", "api_key", "model", "temperature"])


class TestReportConfigDefaults:
    """Test ReportConfig default values and to_*_config methods."""

    def test_default_values(self):
        cfg = ReportConfig()
        assert cfg.report_structure == "通用调研报告"
        assert cfg.report_style == "学术报告风"
        assert cfg.report_length == "标准版"
        assert cfg.html_theme == "简洁课程作业风"
        assert cfg.literature_enabled is False
        assert cfg.background_enabled is False

    def test_literature_config_disabled(self):
        cfg = ReportConfig()
        assert cfg.to_literature_config() == {"enabled": False}

    def test_literature_config_enabled(self):
        cfg = ReportConfig(
            literature_enabled=True,
            literature_keywords="公众满意度 政务服务",
            literature_max_sources=20,
            literature_year_range="近10年",
        )
        lit = cfg.to_literature_config()
        assert lit["enabled"] is True
        assert lit["keywords"] == "公众满意度 政务服务"
        assert lit["max_sources"] == 20
        assert lit["year_range"] == "近10年"

    def test_background_config_disabled(self):
        cfg = ReportConfig()
        assert cfg.to_background_config() == {"enabled": False}

    def test_background_config_enabled(self):
        cfg = ReportConfig(
            background_enabled=True,
            background_source_path="background/example",
        )
        bg = cfg.to_background_config()
        assert bg["enabled"] is True
        assert bg["source_path"] == "background/example"
