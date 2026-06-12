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
