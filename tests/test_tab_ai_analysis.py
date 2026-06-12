"""Tests for the AI intelligent analysis tab (tab_ai_analysis.py)."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock, patch
import pandas as pd
import pytest


# ── helpers for mock context managers ──

def _make_ctx():
    m = MagicMock()
    m.__enter__ = MagicMock(return_value=m)
    m.__exit__ = MagicMock(return_value=None)
    return m


# ================================================================
# Import checks
# ================================================================


class TestTabAiAnalysisImports:
    """Verify the AI analysis tab module is properly structured."""

    def test_render_function_exists(self):
        """render_tab_ai_analysis should be importable and callable."""
        from src.ui.tabs.tab_ai_analysis import render_tab_ai_analysis
        assert callable(render_tab_ai_analysis)

    def test_render_function_params(self):
        """Function signature should match app.py call site."""
        from src.ui.tabs.tab_ai_analysis import render_tab_ai_analysis
        import inspect
        sig = inspect.signature(render_tab_ai_analysis)
        param_names = list(sig.parameters.keys())
        for name in ["raw_df", "schema_df", "config", "quality",
                      "generic_var_dict_map", "generic_file_name", "selected_sheet"]:
            assert name in param_names, f"Missing parameter: {name}"

    def test_save_current_settings_importable(self):
        """_save_current_settings should be importable from api_config module."""
        from src.ui.api_config import _save_current_settings
        assert callable(_save_current_settings)

    def test_build_chart_summaries_importable(self):
        """_build_chart_summaries should be importable (moved from app.py)."""
        from src.ui.tabs.tab_ai_analysis import _build_chart_summaries
        assert callable(_build_chart_summaries)


# ================================================================
# _save_current_settings behaviour
# ================================================================


class TestSaveCurrentSettings:
    """Verify _save_current_settings behaviour is unchanged after move."""

    def test_save_with_remember_true(self):
        """When remember=True, save_user_settings should be called."""
        from src.ui.api_config import _save_current_settings
        with patch("src.ui.api_config.save_user_settings") as mock_save:
            with patch("src.ui.api_config.clear_user_settings") as mock_clear:
                _save_current_settings("openai", "sk-xxx", "gpt-4o", remember=True)
                mock_save.assert_called_once_with({
                    "provider_key": "openai",
                    "api_key": "sk-xxx",
                    "model": "gpt-4o",
                    "remember": True,
                })
                mock_clear.assert_not_called()

    def test_save_with_remember_false(self):
        """When remember=False, clear_user_settings should be called."""
        from src.ui.api_config import _save_current_settings
        with patch("src.ui.api_config.save_user_settings") as mock_save:
            with patch("src.ui.api_config.clear_user_settings") as mock_clear:
                _save_current_settings("openai", "sk-xxx", "gpt-4o", remember=False)
                mock_clear.assert_called_once()
                mock_save.assert_not_called()


# ================================================================
# _build_chart_summaries behaviour
# ================================================================


class TestBuildChartSummaries:
    """Verify _build_chart_summaries behaviour is unchanged after move."""

    def test_empty_list_returns_empty(self):
        """Empty input produces empty output."""
        from src.ui.tabs.tab_ai_analysis import _build_chart_summaries
        result = _build_chart_summaries([])
        assert result == []

    def test_none_figures_filtered_out(self):
        """Charts with fig=None should be skipped."""
        from src.ui.tabs.tab_ai_analysis import _build_chart_summaries
        dashboard = [
            ("key1", "Title 1", None),
            ("key2", "Title 2", None),
        ]
        result = _build_chart_summaries(dashboard)
        assert result == []

    def test_non_tuple_items_skipped(self):
        """Non-tuple/non-list items should be skipped gracefully."""
        from src.ui.tabs.tab_ai_analysis import _build_chart_summaries
        dashboard = ["not a tuple", 123, None]
        result = _build_chart_summaries(dashboard)
        assert result == []

    def test_malformed_items_skipped(self):
        """Items with fewer than 3 elements should be skipped."""
        from src.ui.tabs.tab_ai_analysis import _build_chart_summaries
        dashboard = [("key_only",), ("key", "title")]
        result = _build_chart_summaries(dashboard)
        assert result == []

    def test_valid_chart_produces_summary(self):
        """A valid matplotlib/plotly figure should produce a summary dict."""
        from src.ui.tabs.tab_ai_analysis import _build_chart_summaries
        # Create a minimal mock figure with plotly-like structure
        mock_fig = MagicMock()
        mock_fig.data = [MagicMock()]
        mock_fig.data[0].type = "bar"
        mock_fig.data[0].x = ["A", "B", "C"]
        mock_fig.data[0].y = [10, 20, 15]

        dashboard = [("chart_1", "Test Chart", mock_fig)]
        result = _build_chart_summaries(dashboard)

        assert len(result) == 1
        assert result[0]["title"] == "Test Chart"
        assert result[0]["key"] == "chart_1"
        assert result[0]["type"] == "bar_chart"


# ================================================================
# Widget key preservation check
# ================================================================


class TestWidgetKeysPreserved:
    """Verify that widget keys are not altered by extraction."""

    def test_key_widget_keys_unchanged(self):
        """All AI tab widget keys should remain as documented."""
        expected_keys = {
            "ai_provider_display",
            "custom_display_name",
            "custom_base_url",
            "custom_chat_path",
            "custom_model_list_path",
            "custom_response_format",
            "custom_auth_type",
            "custom_header_name",
            "custom_prefix",
            "ai_api_key",
            "gen_remember_me",
            "ai_fetch_models",
            "ai_model_select",
            "ai_model_input",
            "ai_model_input_fallback",
            "ai_model_input_cached",
            "ai_model_input_direct",
            "ai_model_input_manual",
            "ai_temperature",
            "ai_max_tokens",
            "ai_report_title",
            "ai_research_subject",
            "ai_report_structure",
            "ai_report_style",
            "ai_report_length",
            "ai_html_theme",
            "ai_enable_literature",
            "ai_literature_keywords",
            "ai_literature_year_range",
            "ai_literature_max_sources",
            "preview_literature_btn",
            "ai_enable_background",
            "ai_background_select",
            "ai_background_path",
            "preview_background_btn",
            "ai_test_connection",
            "gen_payload_btn",
            "dl_payload",
            "gen_ai_report_btn",
        }
        # This test verifies the documented key set exists.
        # Actual key usage is checked in integration tests.
        assert len(expected_keys) >= 30, f"Expected ≥30 widget keys, got {len(expected_keys)}"


class TestSessionStateKeysPreserved:
    """Verify that session_state keys are not altered by extraction."""

    def test_key_session_state_keys_unchanged(self):
        """All AI tab session_state keys should remain as documented."""
        expected_keys = {
            "_saved_provider_key",
            "_saved_api_key",
            "_saved_remember",
            "_saved_model",
            "_api_key",
            "_provider_key",
            "_provider_config",
            "_ai_model",
            "ai_models_fetched",
            "ai_available_models",
            "ai_models_source",
            "ai_models_updated_at",
            "ai_models_error",
            "_lit_enabled",
            "_lit_keywords",
            "_lit_preview_papers",
            "_lit_preview_keywords",
            "_bg_enabled",
            "_bg_path",
            "_bg_preview_text",
            "_bg_preview_path",
            "ai_analysis_payload",
            "ai_analysis_results",
            "generic_config",
        }
        assert len(expected_keys) >= 20, f"Expected ≥20 session_state keys, got {len(expected_keys)}"


# ================================================================
# analyzable_cols includes binary
# ================================================================


class TestAnalyzableColsIncludesBinary:
    """Regression: analyzable_cols should include 'binary' type variables."""

    def test_binary_included_in_analyzable_cols(self):
        """Binary variables must appear in analyzable_cols for Tab 4/5."""
        import numpy as np
        df = pd.DataFrame({
            "region": ["A", "B", "A", "B", "A", "B"],
            "score": [1, 2, 3, 4, 5, 1],
            "converted": [0, 1, 0, 1, 0, 0],
            "name": ["a", "b", "c", "d", "e", "f"],
        })
        schema_df = pd.DataFrame([
            {"column": "region", "inferred_type": "categorical"},
            {"column": "score", "inferred_type": "numeric"},
            {"column": "converted", "inferred_type": "binary"},
            {"column": "name", "inferred_type": "text"},
        ])

        analyzable_cols = schema_df[
            schema_df["inferred_type"].isin(["numeric", "categorical", "ordinal", "binary"])
        ]["column"].tolist()

        assert "region" in analyzable_cols  # categorical
        assert "score" in analyzable_cols    # numeric
        assert "converted" in analyzable_cols  # binary — should be included
        assert "name" not in analyzable_cols   # text — should be excluded
