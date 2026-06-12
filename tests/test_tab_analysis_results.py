"""Tests for the analysis results tabs (univariate, bivariate, multivariate)."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pytest


class TestTabUnivariateAnalysis:
    """Verify the univariate analysis tab module."""

    def test_render_function_exists(self):
        from src.ui.tabs.tab_univariate_analysis import render_tab_univariate_analysis
        assert callable(render_tab_univariate_analysis)

    def test_render_function_params(self):
        from src.ui.tabs.tab_univariate_analysis import render_tab_univariate_analysis
        import inspect
        sig = inspect.signature(render_tab_univariate_analysis)
        param_names = list(sig.parameters.keys())
        for name in ["raw_df", "schema_df", "cn_map", "analyzable_cols"]:
            assert name in param_names, f"Missing parameter: {name}"


class TestTabBivariateAnalysis:
    """Verify the bivariate analysis tab module."""

    def test_render_function_exists(self):
        from src.ui.tabs.tab_bivariate_analysis import render_tab_bivariate_analysis
        assert callable(render_tab_bivariate_analysis)

    def test_render_function_params(self):
        from src.ui.tabs.tab_bivariate_analysis import render_tab_bivariate_analysis
        import inspect
        sig = inspect.signature(render_tab_bivariate_analysis)
        param_names = list(sig.parameters.keys())
        for name in ["raw_df", "schema_df", "config", "type_map", "cn_map", "var_dict"]:
            assert name in param_names, f"Missing parameter: {name}"

    def test_render_cross_result_helper_exists(self):
        from src.ui.tabs.tab_bivariate_analysis import _render_cross_result
        assert callable(_render_cross_result)


class TestTabMultivariateAnalysis:
    """Verify the multivariate analysis tab module."""

    def test_render_function_exists(self):
        from src.ui.tabs.tab_multivariate_analysis import render_tab_multivariate_analysis
        assert callable(render_tab_multivariate_analysis)

    def test_render_function_params(self):
        from src.ui.tabs.tab_multivariate_analysis import render_tab_multivariate_analysis
        import inspect
        sig = inspect.signature(render_tab_multivariate_analysis)
        param_names = list(sig.parameters.keys())
        for name in ["raw_df", "config", "type_map", "cn_map"]:
            assert name in param_names, f"Missing parameter: {name}"


class TestTabVisualization:
    """Verify the visualization tab module."""

    def test_render_function_exists(self):
        from src.ui.tabs.tab_visualization import render_tab_visualization
        assert callable(render_tab_visualization)

    def test_render_function_params(self):
        from src.ui.tabs.tab_visualization import render_tab_visualization
        import inspect
        sig = inspect.signature(render_tab_visualization)
        param_names = list(sig.parameters.keys())
        for name in ["raw_df", "schema_df", "config", "type_map", "cn_map"]:
            assert name in param_names, f"Missing parameter: {name}"
