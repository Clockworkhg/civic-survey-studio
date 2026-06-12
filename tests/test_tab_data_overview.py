"""Tests for the data overview tab (tab_data_overview.py)."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pytest


class TestTabDataOverviewImports:
    """Verify the data overview tab module is properly structured."""

    def test_render_function_exists(self):
        """render_tab_data_overview should be importable."""
        from src.ui.tabs.tab_data_overview import render_tab_data_overview
        assert callable(render_tab_data_overview)

    def test_render_function_params(self):
        """Function should accept raw_df, schema_df, quality."""
        from src.ui.tabs.tab_data_overview import render_tab_data_overview
        import inspect
        sig = inspect.signature(render_tab_data_overview)
        param_names = list(sig.parameters.keys())
        for name in ["raw_df", "schema_df", "quality"]:
            assert name in param_names, f"Missing parameter: {name}"

    def test_render_function_callable_with_mock(self):
        """Function should not raise when called with mock data and Streamlit mocked."""
        from unittest.mock import patch, MagicMock
        import streamlit as st_module

        mock_st = MagicMock(wraps=st_module)
        mock_st.markdown = MagicMock()
        def _make_ctx():
            m = MagicMock()
            m.__enter__ = MagicMock(return_value=m)
            m.__exit__ = MagicMock(return_value=None)
            return m
        mock_st.columns = MagicMock(side_effect=lambda n, **kw: [_make_ctx() for _ in range(n)])
        mock_st.metric = MagicMock()
        mock_st.dataframe = MagicMock()
        mock_st.success = MagicMock()
        mock_st.caption = MagicMock()

        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        schema = pd.DataFrame([
            {"column": "a", "inferred_type": "numeric"},
            {"column": "b", "inferred_type": "numeric"},
        ])
        quality = {"样本量": 3, "变量数": 2, "缺失值总数": 0, "缺失率": "0.0",
                    "重复行数": 0, "重复率": "0.0"}

        with patch("src.ui.tabs.tab_data_overview.st", mock_st):
            from src.ui.tabs.tab_data_overview import render_tab_data_overview
            result = render_tab_data_overview(df, schema, quality)
            assert result is None  # No return value
