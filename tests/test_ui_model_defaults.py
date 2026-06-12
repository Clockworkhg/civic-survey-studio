"""Tests for resolve_default_ai_model() in src/ui/report_generation.py."""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ui.report_generation import resolve_default_ai_model


class TestResolveDefaultAIModel:
    """Test the AI model default resolution logic."""

    def test_saved_model_takes_priority(self):
        """Saved model should always win over provider default."""
        result = resolve_default_ai_model(
            provider_config={"default_model": "gpt-4o"},
            saved_model="claude-3",
        )
        assert result == "claude-3"

    def test_provider_default_when_no_saved(self):
        """When no saved model, provider default should be used."""
        result = resolve_default_ai_model(
            provider_config={"default_model": "deepseek-chat"},
            saved_model="",
        )
        assert result == "deepseek-chat"

    def test_empty_string_when_no_defaults(self):
        """When neither saved nor provider default, return empty string."""
        result = resolve_default_ai_model(
            provider_config={},
            saved_model="",
        )
        assert result == ""

    def test_none_provider_config(self):
        """None provider_config is safe."""
        result = resolve_default_ai_model(
            provider_config=None,
            saved_model="",
        )
        assert result == ""

    def test_saved_model_without_provider_config(self):
        """Saved model works even without provider_config."""
        result = resolve_default_ai_model(
            provider_config=None,
            saved_model="gpt-4",
        )
        assert result == "gpt-4"

    def test_provider_config_without_default_model_key(self):
        """Provider config without 'default_model' key returns empty."""
        result = resolve_default_ai_model(
            provider_config={"base_url": "https://api.example.com"},
            saved_model="",
        )
        assert result == ""

    def test_empty_saved_model_is_falsy(self):
        """Empty saved_model string is treated as 'not provided'."""
        result = resolve_default_ai_model(
            provider_config={"default_model": "qwen-plus"},
            saved_model="",
        )
        assert result == "qwen-plus"
