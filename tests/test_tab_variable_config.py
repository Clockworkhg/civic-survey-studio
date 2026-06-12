"""Tests for variable config tab helpers.

Since the tab renders Streamlit widgets, we test the import chain
and verify key functions are callable with proper signatures.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTabVariableConfigImports:
    """Verify the tab module can be imported and has correct exports."""

    def test_render_function_exists(self):
        """render_tab_variable_config should be importable."""
        from src.ui.tabs.tab_variable_config import render_tab_variable_config
        assert callable(render_tab_variable_config)

    def test_render_function_accepts_params(self):
        """Function should accept the expected parameter names."""
        from src.ui.tabs.tab_variable_config import render_tab_variable_config
        import inspect
        sig = inspect.signature(render_tab_variable_config)
        param_names = list(sig.parameters.keys())
        expected = ["sb", "raw_df", "schema_df", "type_map", "quality",
                     "generic_var_dict_map", "gen_ctx"]
        for name in expected:
            assert name in param_names, f"Missing parameter: {name}"


class TestTabDataUploadImports:
    """Verify the data upload tab module is properly structured."""

    def test_render_function_exists(self):
        """render_tab_data_upload should be importable."""
        from src.ui.tabs.tab_data_upload import render_tab_data_upload
        assert callable(render_tab_data_upload)

    def test_render_function_params(self):
        """Function should accept sb and raw_df."""
        from src.ui.tabs.tab_data_upload import render_tab_data_upload
        import inspect
        sig = inspect.signature(render_tab_data_upload)
        param_names = list(sig.parameters.keys())
        assert "sb" in param_names
        assert "raw_df" in param_names


class TestTabLegacyReportImports:
    """Verify the legacy report tab module is properly structured."""

    def test_render_function_exists(self):
        """render_tab_legacy_report should be importable."""
        from src.ui.tabs.tab_legacy_report import render_tab_legacy_report
        assert callable(render_tab_legacy_report)

    def test_render_function_params(self):
        """Function should accept raw_df, schema_df, config, var_dict."""
        from src.ui.tabs.tab_legacy_report import render_tab_legacy_report
        import inspect
        sig = inspect.signature(render_tab_legacy_report)
        param_names = list(sig.parameters.keys())
        for name in ["raw_df", "schema_df", "config", "var_dict"]:
            assert name in param_names, f"Missing parameter: {name}"


class TestTabsInitExports:
    """Verify all tab render functions are exported from __init__.py."""

    def test_all_exports_match(self):
        """All twelve render functions should be in __all__ (11 unique + 1 alias)."""
        from src.ui.tabs import __all__ as exports
        expected = [
            "render_tab_data_upload",
            "render_tab_data_overview",
            "render_tab_variable_config",
            "render_tab_quick_report",
            "render_tab_analysis_config",
            "render_tab_univariate_analysis",
            "render_tab_bivariate_analysis",
            "render_tab_multivariate_analysis",
            "render_tab_visualization",
            "render_tab_template_report",
            "render_tab_legacy_report",
            "render_tab_ai_analysis",
        ]
        for name in expected:
            assert name in exports, f"Missing from __all__: {name}"

    def test_all_exports_are_importable(self):
        """Each export should be callable."""
        from src.ui.tabs import (
            render_tab_data_upload,
            render_tab_data_overview,
            render_tab_variable_config,
            render_tab_quick_report,
            render_tab_analysis_config,
            render_tab_univariate_analysis,
            render_tab_bivariate_analysis,
            render_tab_multivariate_analysis,
            render_tab_visualization,
            render_tab_template_report,
            render_tab_legacy_report,
            render_tab_ai_analysis,
        )
        for func in [
            render_tab_data_upload,
            render_tab_data_overview,
            render_tab_variable_config,
            render_tab_quick_report,
            render_tab_analysis_config,
            render_tab_univariate_analysis,
            render_tab_bivariate_analysis,
            render_tab_multivariate_analysis,
            render_tab_visualization,
            render_tab_template_report,
            render_tab_legacy_report,
            render_tab_ai_analysis,
        ]:
            assert callable(func), f"Not callable: {func.__name__}"
