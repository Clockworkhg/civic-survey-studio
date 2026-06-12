"""Tests for report_options — centralized report configuration."""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.report_options import (
    REPORT_STRUCTURE_KEYS,
    REPORT_STYLE_KEYS,
    REPORT_LENGTH_KEYS,
    HTML_THEME_KEYS,
    get_structure_options,
    get_style_options,
    get_length_options,
    get_html_theme_options,
    is_structure_supports_background,
    is_structure_supports_literature,
    LIT_APPLICABLE_STRUCTURES,
    BG_APPLICABLE_STRUCTURES,
)


class TestReportOptions:
    """Test that option lists exist and are consistent."""

    def test_structure_keys_defined(self):
        assert len(REPORT_STRUCTURE_KEYS) == 5
        assert "学术论文式报告" in REPORT_STRUCTURE_KEYS
        assert "通用调研报告" in REPORT_STRUCTURE_KEYS

    def test_style_keys_defined(self):
        assert len(REPORT_STYLE_KEYS) == 4
        assert "学术报告风" in REPORT_STYLE_KEYS

    def test_length_keys_defined(self):
        assert len(REPORT_LENGTH_KEYS) == 3
        assert "标准版" in REPORT_LENGTH_KEYS

    def test_html_theme_keys_defined(self):
        assert len(HTML_THEME_KEYS) == 5
        assert "简洁课程作业风" in HTML_THEME_KEYS

    def test_get_structure_options(self):
        opts = get_structure_options()
        assert isinstance(opts, list)
        assert len(opts) == 5
        assert all(isinstance(s, str) for s in opts)

    def test_get_style_options(self):
        opts = get_style_options()
        assert isinstance(opts, list)
        assert len(opts) == 4

    def test_get_length_options(self):
        opts = get_length_options()
        assert isinstance(opts, list)
        assert len(opts) == 3

    def test_get_html_theme_options(self):
        opts = get_html_theme_options()
        assert isinstance(opts, list)
        assert len(opts) == 5

    def test_literature_only_for_academic(self):
        assert is_structure_supports_literature("学术论文式报告") is True
        assert is_structure_supports_literature("通用调研报告") is False
        assert is_structure_supports_literature("政务决策报告") is False

    def test_background_for_academic_and_gov(self):
        assert is_structure_supports_background("学术论文式报告") is True
        assert is_structure_supports_background("政务决策报告") is True
        assert is_structure_supports_background("通用调研报告") is False
        assert is_structure_supports_background("商业分析报告") is False

    def test_lit_structures_list(self):
        assert LIT_APPLICABLE_STRUCTURES == ["学术论文式报告"]

    def test_bg_structures_list(self):
        assert set(BG_APPLICABLE_STRUCTURES) == {"学术论文式报告", "政务决策报告"}
