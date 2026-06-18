"""Tests for src.ui.styles — CSS loading and injection."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock, patch
import pytest


class TestLoadAppCss:
    """Verify CSS loading behaviour."""

    def test_css_string_non_empty(self):
        """The CSS string should be non-empty."""
        from src.ui.styles import load_app_css, APP_CSS
        css = load_app_css()
        assert len(css) > 0
        assert len(APP_CSS) > 0

    def test_css_contains_key_classes(self):
        """The CSS should contain key style classes used in app.py (v0.1.0 redesign)."""
        from src.ui.styles import load_app_css
        css = load_app_css()
        # v0.1.0 redesign: replaced .main-title/.main-subtitle/.disclaimer with
        # theme-based unified CSS. These legacy classes are no longer in CSS.
        assert ".section-divider" in css
        assert ".card" in css
        assert ".card-ai" in css
        assert ".card-error" in css
        assert "stTabs" in css
        assert "stMetricValue" in css

    def test_css_contains_metric_container_styles(self):
        """The CSS should contain metric container customization."""
        from src.ui.styles import load_app_css
        css = load_app_css()
        assert "metric-container" in css
        assert "stMetricValue" in css

    def test_css_contains_sidebar_styles(self):
        """The CSS should contain sidebar background styling."""
        from src.ui.styles import load_app_css
        css = load_app_css()
        assert "stSidebar" in css

    def test_load_and_app_css_are_identical(self):
        """load_app_css() should return the same string as APP_CSS."""
        from src.ui.styles import load_app_css, APP_CSS
        assert load_app_css() == APP_CSS


class TestInjectAppCss:
    """Verify CSS injection calls st.markdown correctly."""

    def test_inject_app_css_calls_st_markdown(self):
        """inject_app_css() should call st.markdown with unsafe_allow_html=True."""
        from src.ui.styles import inject_app_css
        with patch("src.ui.styles.st.markdown") as mock_md:
            inject_app_css()
            mock_md.assert_called_once()
            args, kwargs = mock_md.call_args
            assert kwargs.get("unsafe_allow_html") is True
            # First positional arg should be the CSS string
            assert len(args[0]) > 0

    def test_inject_app_css_called_with_app_css_content(self):
        """inject_app_css() should pass APP_CSS content to st.markdown."""
        from src.ui.styles import inject_app_css, APP_CSS
        with patch("src.ui.styles.st.markdown") as mock_md:
            inject_app_css()
            args, _ = mock_md.call_args
            assert args[0] == APP_CSS


class TestCssRegression:
    """Regression tests for CSS fixes from code review."""

    def test_report_sheet_uses_theme_surface(self):
        """.report-sheet should use COLORS.surface, not hardcoded #FFFFFF."""
        from src.ui.styles import APP_CSS
        import re
        m = re.search(r'\.report-sheet\s*\{\{([^}]+)\}\}', APP_CSS, re.DOTALL)
        if m:
            block = m.group(1)
            assert "#FFFFFF" not in block, (
                ".report-sheet should use COLORS.surface, not hardcoded #FFFFFF"
            )

    def test_tab_highlight_no_display_none(self):
        """Tab highlight CSS should not contain display:none."""
        from src.ui.styles import APP_CSS
        # Find the tab-highlight block and check it doesn't use display:none
        import re
        m = re.search(r'\[data-baseweb="tab-highlight"\]\s*\{\{([^}]+)\}\}', APP_CSS, re.DOTALL)
        if m:
            block = m.group(1)
            assert "display:" not in block or "display: none" not in block, \
                "tab-highlight block should not contain display:none"

    # ---- Alert selector regression (Streamlit 1.58 compatibility) ----

    def test_alert_css_no_kind_attribute_selector(self):
        """CSS must not use [data-testid="stAlert"][kind=...] selectors."""
        from src.ui.styles import APP_CSS
        assert 'stAlert"][kind=' not in APP_CSS, (
            "CSS should not contain [data-testid=\"stAlert\"][kind=...] selectors"
        )

    def test_alert_success_selector_uses_has_content_success(self):
        """Success alert should use :has([data-testid="stAlertContentSuccess"])."""
        from src.ui.styles import APP_CSS
        assert 'stAlertContentSuccess' in APP_CSS, (
            "Success alert CSS should reference stAlertContentSuccess"
        )

    def test_alert_warning_selector_uses_has_content_warning(self):
        """Warning alert should use :has([data-testid="stAlertContentWarning"])."""
        from src.ui.styles import APP_CSS
        assert 'stAlertContentWarning' in APP_CSS, (
            "Warning alert CSS should reference stAlertContentWarning"
        )

    def test_alert_info_selector_uses_has_content_info(self):
        """Info alert should use :has([data-testid="stAlertContentInfo"])."""
        from src.ui.styles import APP_CSS
        assert 'stAlertContentInfo' in APP_CSS, (
            "Info alert CSS should reference stAlertContentInfo"
        )

    def test_alert_error_selector_uses_has_content_error(self):
        """Error alert should use :has([data-testid="stAlertContentError"])."""
        from src.ui.styles import APP_CSS
        assert 'stAlertContentError' in APP_CSS, (
            "Error alert CSS should reference stAlertContentError"
        )

    def test_success_alert_uses_success_border_token(self):
        """Success alert CSS rule should use success_border token."""
        from src.ui.styles import APP_CSS
        import re
        # Find the success alert CSS block: from :has(ContentSuccess) to closing }}
        # The block may span multiple lines.
        m = re.search(
            r'stAlertContentSuccess\b',
            APP_CSS
        )
        assert m is not None, "Could not find success alert CSS selector"
        # Grab the surrounding 600 chars after the match to cover the full rule
        block = APP_CSS[m.start():m.start()+600]
        from src.ui.theme import COLORS
        assert COLORS.success_border in block, (
            f"Success alert should use success_border={COLORS.success_border}, got: {block[:120]}"
        )

    def test_warning_alert_uses_warning_border_token(self):
        """Warning alert CSS rule should use warning_border token."""
        from src.ui.styles import APP_CSS
        import re
        m = re.search(
            r'stAlertContentWarning\b',
            APP_CSS
        )
        assert m is not None, "Could not find warning alert CSS selector"
        block = APP_CSS[m.start():m.start()+600]
        from src.ui.theme import COLORS
        assert COLORS.warning_border in block, (
            f"Warning alert should use warning_border={COLORS.warning_border}, got: {block[:120]}"
        )
