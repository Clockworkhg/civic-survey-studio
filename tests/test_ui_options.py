"""Tests for src/ui/options.py — verify re-exports match report_options."""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestUIOptionsReExports:
    """Verify every re-exported function returns the same as the original."""

    def test_get_structure_options_matches(self):
        from src.ui.options import get_structure_options
        from src.report_options import get_structure_options as orig
        assert get_structure_options() == orig()

    def test_get_style_options_matches(self):
        from src.ui.options import get_style_options
        from src.report_options import get_style_options as orig
        assert get_style_options() == orig()

    def test_get_length_options_matches(self):
        from src.ui.options import get_length_options
        from src.report_options import get_length_options as orig
        assert get_length_options() == orig()

    def test_get_html_theme_options_matches(self):
        from src.ui.options import get_html_theme_options
        from src.report_options import get_html_theme_options as orig
        assert get_html_theme_options() == orig()

    def test_is_structure_supports_literature_matches(self):
        from src.ui.options import is_structure_supports_literature
        from src.report_options import is_structure_supports_literature as orig
        for s in ["学术论文式报告", "通用调研报告", "政务决策报告"]:
            assert is_structure_supports_literature(s) == orig(s)

    def test_is_structure_supports_background_matches(self):
        from src.ui.options import is_structure_supports_background
        from src.report_options import is_structure_supports_background as orig
        for s in ["学术论文式报告", "政务决策报告", "课程作业报告"]:
            assert is_structure_supports_background(s) == orig(s)

    def test_all_exported(self):
        """Verify all expected names are exported."""
        from src.ui import options
        for name in options.__all__:
            assert hasattr(options, name)
