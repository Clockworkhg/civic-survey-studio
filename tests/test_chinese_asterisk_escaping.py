"""Tests for Chinese asterisk escaping in Markdown→HTML/DOCX conversion."""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import escape_chinese_asterisks


class TestChineseAsteriskEscaping:
    """Test that CJK-wrapped asterisks are escaped but English ones are not."""

    def test_double_asterisks_with_chinese(self):
        """**标准差** should be escaped because it contains CJK."""
        text = "计算了**标准差**指标。"
        result = escape_chinese_asterisks(text)
        assert "\\*\\*标准差\\*\\*" in result
        assert "**标准差**" not in result

    def test_single_asterisk_with_chinese(self):
        """*均值* should be escaped because it contains CJK."""
        text = "包括*均值*等统计量。"
        result = escape_chinese_asterisks(text)
        assert "\\*均值\\*" in result
        assert "*均值*" not in result

    def test_english_bold_preserved(self):
        """**important** (English only) should NOT be escaped."""
        text = "This is **important** note."
        result = escape_chinese_asterisks(text)
        assert "**important**" in result, (
            "English bold text should be preserved"
        )

    def test_chinese_partial_asterisks(self):
        """*p值* with CJK should be escaped."""
        text = "发现*p值*显著。"
        result = escape_chinese_asterisks(text)
        assert "\\*p值\\*" in result

    def test_mixed_chinese_english_asterisks(self):
        """Chinese with English mixed inside ** should still be escaped."""
        text = "计算了**标准差(std)**和**均值(mean)**。"
        result = escape_chinese_asterisks(text)
        assert "\\*\\*标准差(std)\\*\\*" in result
        assert "\\*\\*均值(mean)\\*\\*" in result

    def test_no_asterisks_unchanged(self):
        """Text without asterisks should be unchanged."""
        text = "标准差和均值都很重要。"
        result = escape_chinese_asterisks(text)
        assert result == text

    def test_standalone_asterisk_unchanged(self):
        """Single standalone * without CJK inside should be unchanged."""
        text = "p < 0.05 *"
        result = escape_chinese_asterisks(text)
        assert result == text
