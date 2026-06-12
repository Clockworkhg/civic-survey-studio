"""Tests for the quick report tab (tab_quick_report.py).

These tests mock Streamlit to verify the report generation call flow.
No real LLM API calls are made.
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestQuickReportCallFlow:
    """Verify the quick report tab calls run_report_generation_from_ui."""

    @pytest.fixture
    def mock_streamlit(self, monkeypatch):
        """Mock streamlit module to avoid actual rendering."""
        import streamlit as st_module
        mock_st = MagicMock(wraps=st_module)
        # Mock session_state
        mock_st.session_state = {
            "generic_config": {
                "target_variable": "converted",
                "group_variables": ["region"],
                "explanatory_variables": ["score", "age"],
                "report_title": "测试报告",
            },
            "_api_key": "sk-test",
            "_ai_model": "test-model",
            "_provider_config": {"base_url": "https://test.api.com"},
            "_provider_key": "test_provider",
        }
        mock_st.selectbox = MagicMock(return_value="测试选项")
        mock_st.button = MagicMock(return_value=False)
        def _make_ctx():
            """Create a MagicMock that works as a context manager."""
            m = MagicMock()
            m.__enter__ = MagicMock(return_value=m)
            m.__exit__ = MagicMock(return_value=None)
            return m

        mock_st.columns = MagicMock(side_effect=lambda n, **kw: [_make_ctx() for _ in range(n)])
        mock_st.markdown = MagicMock()
        mock_st.caption = MagicMock()
        mock_st.metric = MagicMock()
        mock_st.spinner = MagicMock()
        mock_st.success = MagicMock()
        mock_st.error = MagicMock()
        mock_st.warning = MagicMock()
        mock_st.expander = MagicMock()
        mock_st.components = MagicMock()
        mock_st.download_button = MagicMock()
        mock_st.info = MagicMock()
        mock_st.spinner.return_value.__enter__ = MagicMock()
        mock_st.spinner.return_value.__exit__ = MagicMock()
        mock_st.expander.return_value.__enter__ = MagicMock()
        mock_st.expander.return_value.__exit__ = MagicMock()

        monkeypatch.setattr("src.ui.tabs.tab_quick_report.st", mock_st)
        return mock_st

    def test_quick_report_calls_generate_when_button_clicked(self, mock_streamlit):
        """When button is clicked, should call run_report_generation_from_ui."""
        import pandas as pd
        from unittest.mock import patch

        # Set button to return True (clicked)
        mock_streamlit.button.return_value = True

        df = pd.DataFrame({"a": [1, 2, 3], "b": [0, 1, 0]})
        schema = pd.DataFrame([
            {"column": "a", "inferred_type": "numeric"},
            {"column": "b", "inferred_type": "binary"},
        ])

        # Mock run_full_analysis to avoid real computation
        mock_analysis = {"multivariate": {"test": "ok"}}

        with patch("src.ui.tabs.tab_quick_report.run_full_analysis", return_value=mock_analysis):
            with patch("src.ui.tabs.tab_quick_report.run_report_generation_from_ui") as mock_run:
                mock_run.return_value = {
                    "success": True,
                    "markdown_report": "报告内容",
                    "html_report": "<html>",
                    "docx_report": b"",
                }
                from src.ui.tabs.tab_quick_report import render_tab_quick_report
                render_tab_quick_report(
                    raw_df=df,
                    schema_df=schema,
                    quality={"样本量": 3},
                    generic_var_dict_map={},
                )

        # Verify the main function was called
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert "llm_config" in call_kwargs
        assert "report_config" in call_kwargs
        assert call_kwargs["df"] is df
        assert call_kwargs["schema_df"] is schema


class TestQuickReportHidden:
    """Verify the quick report section is hidden when no config exists."""

    @pytest.fixture
    def mock_st_hidden(self, monkeypatch):
        """Mock streamlit with empty config."""
        import streamlit as st_module
        mock_st = MagicMock(wraps=st_module)
        mock_st.session_state = {
            "generic_config": {
                "target_variable": "",
                "group_variables": [],
                "explanatory_variables": [],
            },
        }
        # The function reads st.session_state.get("generic_config", {})
        # and checks if any of the three keys are non-empty
        monkeypatch.setattr("src.ui.tabs.tab_quick_report.st", mock_st)
        return mock_st

    def test_quick_report_hidden_without_config(self, mock_st_hidden):
        """When no config variables are set, the function should return early
        without raising errors."""
        import pandas as pd

        df = pd.DataFrame({"a": [1, 2]})
        schema = pd.DataFrame([{"column": "a", "inferred_type": "numeric"}])

        from src.ui.tabs.tab_quick_report import render_tab_quick_report
        # Should return without error
        result = render_tab_quick_report(
            raw_df=df,
            schema_df=schema,
            quality={},
            generic_var_dict_map={},
        )
        assert result is None  # Early return
