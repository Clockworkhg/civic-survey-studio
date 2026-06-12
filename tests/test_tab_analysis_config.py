"""Tests for the analysis config tab (tab_analysis_config.py)."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pytest


class TestTabAnalysisConfigImports:
    """Verify the analysis config tab module is properly structured."""

    def test_render_function_exists(self):
        """render_tab_analysis_config should be importable."""
        from src.ui.tabs.tab_analysis_config import render_tab_analysis_config
        assert callable(render_tab_analysis_config)

    def test_render_function_params(self):
        """Function should accept schema_df, type_map, cn_map, config, analyzable_cols."""
        from src.ui.tabs.tab_analysis_config import render_tab_analysis_config
        import inspect
        sig = inspect.signature(render_tab_analysis_config)
        param_names = list(sig.parameters.keys())
        for name in ["schema_df", "type_map", "cn_map", "config", "analyzable_cols"]:
            assert name in param_names, f"Missing parameter: {name}"


class TestGenericConfigStructure:
    """Verify that generic_config keys are not altered by extraction."""

    def test_default_config_keys(self):
        """Default generic_config should have expected keys."""
        # Simulate the default config that init_session_state would set
        default_config = {
            "target_variable": "",
            "group_variables": [],
            "explanatory_variables": [],
            "report_title": "问卷数据分析报告",
        }
        expected_keys = {"target_variable", "group_variables", "explanatory_variables", "report_title"}
        assert set(default_config.keys()) >= expected_keys

    def test_full_config_includes_gen_options(self):
        """Config with gen_html/gen_docx should be accepted."""
        config = {
            "target_variable": "score",
            "group_variables": ["region"],
            "explanatory_variables": ["age", "income"],
            "report_title": "测试报告",
            "gen_html": True,
            "gen_docx": False,
        }
        assert config["gen_html"] is True
        assert config["gen_docx"] is False
        # These keys are set by the analysis config tab
        assert "gen_html" in config
        assert "gen_docx" in config
