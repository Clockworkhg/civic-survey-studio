"""Tests for the quick report tab (tab_quick_report.py).

The tab now serves as a config summary display only — AI report
generation has been consolidated into Tab 10.
"""

import pytest
import sys
import os
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
        monkeypatch.setattr("src.ui.tabs.tab_quick_report.st", mock_st)
        return mock_st

    def test_quick_report_hidden_without_config(self, mock_st_hidden):
        """When no config variables are set, the function should return early."""
        import pandas as pd

        df = pd.DataFrame({"a": [1, 2]})
        schema = pd.DataFrame([{"column": "a", "inferred_type": "numeric"}])

        from src.ui.tabs.tab_quick_report import render_tab_quick_report
        result = render_tab_quick_report(
            raw_df=df,
            schema_df=schema,
            quality={},
            generic_var_dict_map={},
        )
        assert result is None  # Early return


class TestQuickReportConfigSummary:
    """Verify the config summary renders when config exists."""

    @pytest.fixture
    def mock_st_with_config(self, monkeypatch):
        """Mock streamlit with a valid config."""
        import streamlit as st_module
        mock_st = MagicMock(wraps=st_module)
        mock_st.session_state = {
            "generic_config": {
                "target_variable": "converted",
                "group_variables": ["region"],
                "explanatory_variables": ["score", "age"],
                "report_title": "测试报告",
            },
        }
        mock_st.markdown = MagicMock()
        mock_st.caption = MagicMock()
        mock_st.metric = MagicMock()
        mock_st.info = MagicMock()

        def _make_ctx():
            m = MagicMock()
            m.__enter__ = MagicMock(return_value=m)
            m.__exit__ = MagicMock(return_value=None)
            return m

        mock_st.columns = MagicMock(side_effect=lambda n, **kw: [_make_ctx() for _ in range(n)])
        monkeypatch.setattr("src.ui.tabs.tab_quick_report.st", mock_st)
        return mock_st

    def test_config_summary_shows_metrics(self, mock_st_with_config):
        """When config exists, should show metric columns and guidance info."""
        import pandas as pd

        df = pd.DataFrame({"a": [1, 2]})
        schema = pd.DataFrame([{"column": "a", "inferred_type": "numeric"}])

        from src.ui.tabs.tab_quick_report import render_tab_quick_report
        render_tab_quick_report(
            raw_df=df,
            schema_df=schema,
            quality={},
            generic_var_dict_map={},
        )

        # Should have shown metrics
        assert mock_st_with_config.metric.call_count >= 3
        # Should have shown the guidance message pointing to Tab 10
        assert mock_st_with_config.info.called, "Should show guidance to Tab 10"
