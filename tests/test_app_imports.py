"""Tests for app.py — import sanity, no circular imports, tab coverage."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import py_compile
import pytest


class TestAppPyCompilation:
    """Verify app.py can be compiled without syntax errors."""

    def test_app_py_compiles(self):
        """app.py should pass py_compile without errors."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "app.py")
        app_path = os.path.abspath(app_path)
        py_compile.compile(app_path, doraise=True)
        # If we reach here, compilation succeeded


class TestAllTabRenderFunctionsImportable:
    """Verify all tab render functions can be imported from src.ui.tabs."""

    def test_all_exports_importable(self):
        """All 12 exports (11 unique + 1 alias) should be importable and callable."""
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
        funcs = [
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
        ]
        for func in funcs:
            assert callable(func), f"Not callable: {func}"

    def test_legacy_alias_points_to_template(self):
        """render_tab_legacy_report should be the same function as render_tab_template_report."""
        from src.ui.tabs import render_tab_template_report, render_tab_legacy_report
        assert render_tab_legacy_report is render_tab_template_report

    def test_template_report_from_new_module(self):
        """render_tab_template_report should be importable from tab_template_report module."""
        from src.ui.tabs.tab_template_report import render_tab_template_report
        assert callable(render_tab_template_report)

    def test_legacy_report_from_old_module_still_works(self):
        """render_tab_legacy_report should still be importable from the old module (alias)."""
        from src.ui.tabs.tab_legacy_report import render_tab_legacy_report
        assert callable(render_tab_legacy_report)


class TestNoCircularImports:
    """Verify core UI modules don't cause circular import errors."""

    def test_can_import_analysis_helpers(self):
        """src.ui.analysis_helpers should import without error."""
        from src.ui import analysis_helpers
        assert hasattr(analysis_helpers, "auto_suggest_config_from_dict")

    def test_can_import_styles(self):
        """src.ui.styles should import without error."""
        from src.ui import styles
        assert hasattr(styles, "inject_app_css")
        assert hasattr(styles, "load_app_css")

    def test_can_import_state(self):
        """src.ui.state should import without error."""
        from src.ui.state import init_session_state
        assert callable(init_session_state)

    def test_can_import_sidebar(self):
        """src.ui.sidebar should import without error."""
        from src.ui.sidebar import render_sidebar
        assert callable(render_sidebar)

    def test_can_import_messages(self):
        """src.ui.messages should import without error."""
        from src.ui import messages
        assert hasattr(messages, "format_user_friendly_error")
        assert hasattr(messages, "get_no_api_key_message")
        assert hasattr(messages, "get_beginner_flow_guide")
        # v0.1.1: landing page split functions
        assert hasattr(messages, "get_landing_hero")
        assert hasattr(messages, "get_landing_cards")
        assert callable(messages.get_landing_hero)
        assert callable(messages.get_landing_cards)

    def test_landing_hero_renders_brand(self):
        """get_landing_hero() should produce HTML with brand name."""
        from src.ui.messages import get_landing_hero
        html = get_landing_hero()
        assert "CivicSurvey Studio" in html
        assert "工作流概览" in html

    def test_landing_cards_renders_steps(self):
        """get_landing_cards() should produce HTML with 5 step cards."""
        from src.ui.messages import get_landing_cards
        html = get_landing_cards()
        for step in ["数据与变量", "分析方案", "统计分析", "可视化仪表盘", "报告工作台"]:
            assert step in html, f"Missing step: {step}"

    def test_can_import_example_data(self):
        """src.ui.example_data should import without error."""
        from src.ui import example_data
        assert hasattr(example_data, "load_example_data")
        assert hasattr(example_data, "example_data_available")

    def test_can_import_security(self):
        """src.ui.security should import without error."""
        from src.ui import security
        assert hasattr(security, "mask_api_key")
        assert hasattr(security, "contains_potential_secret")
        assert hasattr(security, "redact_potential_secrets")
        assert hasattr(security, "summarize_ai_variable_privacy")

    def test_can_import_src_version(self):
        """src.__version__ should be accessible."""
        import src
        assert hasattr(src, "__version__"), "src should have __version__"
        assert isinstance(src.__version__, str), "__version__ should be a string"
        assert src.__version__ == "0.1.0", (
            f"__version__ should be 0.1.0, got {src.__version__}"
        )


class TestAppStartsWithoutImportError:
    """Verify app.py starts via Streamlit AppTest without exceptions."""

    def test_app_starts_without_exception(self):
        """AppTest should run app.py without ImportError or other exceptions."""
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file("app.py")
        at.run(timeout=30)
        assert not at.exception, (
            f"App should start without exception, got: {at.exception}"
        )

    def test_landing_imports_resolve_at_runtime(self):
        """get_landing_hero and get_landing_cards must be importable."""
        import src.ui.messages as m
        assert hasattr(m, "get_landing_hero"), "get_landing_hero missing"
        assert hasattr(m, "get_landing_cards"), "get_landing_cards missing"
        assert callable(m.get_landing_hero)
        assert callable(m.get_landing_cards)
        # Verify they produce HTML with brand name
        assert "CivicSurvey Studio" in m.get_landing_hero()
        # get_landing_cards contains workflow step cards (5 steps)
        cards_html = m.get_landing_cards()
        assert "上传问卷数据" in cards_html
        assert "报告工作台" in cards_html
