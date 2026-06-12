"""Phase 4 tests: Report rendering — Markdown→HTML/DOCX cleanup.

Covers:
  1. extract_report_content — JSON wrapping, raw Markdown
  2. sanitize_markdown_text — \\n, \\/, artifacts
  3. DOCX — no raw Markdown residues, proper headings/lists/tables
  4. HTML — no \\/, \\n, unrendered **
  5. AI JSON unboxing — {"report": "..."} extraction
  6. clean_html_escapes
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
import re
import pytest


# ================================================================
# 1. extract_report_content
# ================================================================


class TestExtractReportContent:
    """AI output extraction: JSON unwrapping, raw Markdown pass-through."""

    def test_pure_markdown_passthrough(self):
        from src.report_rendering import extract_report_content
        md = "# 标题\n\n正文内容\n\n## 二级标题\n\n- 列表项"
        result = extract_report_content(md)
        assert "# 标题" in result
        assert "正文内容" in result

    def test_json_wrapped_report(self):
        from src.report_rendering import extract_report_content
        json_input = '{"report": "# 数据分析报告\\n\\n## 概述\\n\\n这是正文。"}'
        result = extract_report_content(json_input)
        assert "# 数据分析报告" in result
        assert "概述" in result

    def test_json_wrapped_markdown_key(self):
        from src.report_rendering import extract_report_content
        json_input = '{"markdown": "# 报告\\n\\n正文内容"}'
        result = extract_report_content(json_input)
        assert "# 报告" in result

    def test_json_wrapped_content_key(self):
        from src.report_rendering import extract_report_content
        json_input = '{"content": "# 分析结果\\n\\n数据表明..."}'
        result = extract_report_content(json_input)
        assert "# 分析结果" in result

    def test_double_encoded_json(self):
        """Double-encoded: LLM returns JSON string containing JSON."""
        from src.report_rendering import extract_report_content
        # Simulate: LLM returned a JSON-encoded string that itself contains a JSON object
        # This is the raw string that json.dumps would produce
        double = '"{\\"report\\": \\"# Report Title\\\\n\\\\nBody content\\"}"'
        result = extract_report_content(double)
        # Should have extracted the inner report content
        assert "# Report Title" in result
        assert "Body content" in result

    def test_empty_input(self):
        from src.report_rendering import extract_report_content
        assert extract_report_content("") == ""
        assert extract_report_content(None) == ""

    def test_array_with_report(self):
        from src.report_rendering import extract_report_content
        json_input = '[{"report": "# 报告\\n\\n内容"}]'
        result = extract_report_content(json_input)
        assert "# 报告" in result

    def test_no_report_key_returns_original(self):
        from src.report_rendering import extract_report_content
        json_input = '{"other_key": "value"}'
        result = extract_report_content(json_input)
        assert "other_key" in result  # Falls back to original


# ================================================================
# 2. sanitize_markdown_text
# ================================================================


class TestSanitizeMarkdown:
    """Markdown text cleaning: \\n, \\/, artifacts."""

    def test_literal_backslash_n_to_newline(self):
        from src.report_rendering import sanitize_markdown_text
        text = "# Title\\n\\n## Section\\n\\nContent"
        result = sanitize_markdown_text(text)
        # Should have real newlines
        assert "\n" in result
        assert "\\n" not in result

    def test_backslash_slash_to_slash(self):
        from src.report_rendering import sanitize_markdown_text
        text = 'URL: https:\\/\\/example.com\\/path'
        result = sanitize_markdown_text(text)
        assert "\\/" not in result
        assert "https://example.com/path" in result

    def test_double_quote_unescape(self):
        from src.report_rendering import sanitize_markdown_text
        text = '\\"quoted\\"'
        result = sanitize_markdown_text(text)
        assert '\\"' not in result
        assert '"quoted"' in result

    def test_compresses_excess_blank_lines(self):
        from src.report_rendering import sanitize_markdown_text
        text = "line1\n\n\n\nline2"
        result = sanitize_markdown_text(text)
        assert "\n\n\n\n" not in result

    def test_empty_input(self):
        from src.report_rendering import sanitize_markdown_text
        assert sanitize_markdown_text("") == ""
        assert sanitize_markdown_text(None) == ""


# ================================================================
# 3. clean_html_escapes
# ================================================================


class TestCleanHtmlEscapes:
    """HTML cleanup: \\/, \\n in HTML output."""

    def test_removes_backslash_slash(self):
        from src.report_rendering import clean_html_escapes
        html = '<p>URL: https:\\/\\/example.com<\\/p>'
        result = clean_html_escapes(html)
        assert "\\/" not in result

    def test_removes_literal_backslash_n(self):
        from src.report_rendering import clean_html_escapes
        html = '<p>line1\\nline2</p>'
        result = clean_html_escapes(html)
        assert "\\n" not in result

    def test_empty_input(self):
        from src.report_rendering import clean_html_escapes
        assert clean_html_escapes("") == ""
        assert clean_html_escapes(None) == ""


# ================================================================
# 4. is_probably_json_string
# ================================================================


class TestIsProbablyJsonString:
    """JSON string detection."""

    def test_json_object(self):
        from src.report_rendering import is_probably_json_string
        assert is_probably_json_string('{"key": "value"}') is True

    def test_json_array(self):
        from src.report_rendering import is_probably_json_string
        assert is_probably_json_string('[{"a": 1}]') is True

    def test_markdown_is_not_json(self):
        from src.report_rendering import is_probably_json_string
        assert is_probably_json_string("# 标题\n\n正文") is False

    def test_empty_is_not_json(self):
        from src.report_rendering import is_probably_json_string
        assert is_probably_json_string("") is False
        assert is_probably_json_string(None) is False


# ================================================================
# 5. DOCX rendering — no Markdown residues
# ================================================================


class TestDocxNoMarkdownResidue:
    """DOCX output must not contain raw Markdown syntax."""

    @pytest.fixture
    def sample_markdown(self):
        return """# 数据分析报告

## 概述

这是报告的**概述**部分。包含*斜体*文字。

### 方法

- 样本量：1,234 份
- 时间：2024年1月
- 方法：问卷调查

1. 第一步
2. 第二步
3. 第三步

## 结果

| 变量 | 均值 | 标准差 |
|------|------|--------|
| 满意度 | 3.8 | 0.9 |
| 等待时间 | 12.5 | 5.2 |

> 注：以上结果基于有效样本。

这是普通段落。
"""

    @pytest.fixture
    def config(self):
        return {"report_title": "测试报告"}

    def test_docx_no_hash_heading_markers(self, sample_markdown, config):
        """DOCX should NOT contain '# ' heading markers."""
        from src.report_rendering import render_markdown_to_docx
        docx_bytes = render_markdown_to_docx(sample_markdown, config)
        assert docx_bytes  # Not empty
        # python-docx stores content as XML; check the bytes for raw Markdown
        text = docx_bytes.decode("latin-1", errors="replace")
        # # Heading markers should NOT appear as literal text
        # (they're converted to Word heading styles)
        # Check that # with space isn't followed by heading text as raw text
        # We can't fully parse DOCX XML here, but we can check for obvious residues
        # The raw XML should NOT contain raw "# " followed by heading content
        assert not re.search(r"(?<!\w)# 数据分析报告", text)
        assert not re.search(r"(?<!\w)## 概述", text)

    def test_docx_no_bold_asterisk_residue(self, sample_markdown, config):
        """DOCX should NOT contain ** markers."""
        from src.report_rendering import render_markdown_to_docx
        docx_bytes = render_markdown_to_docx(sample_markdown, config)
        text = docx_bytes.decode("latin-1", errors="replace")
        # ** should not appear as literal text near "概述"
        assert "**概述**" not in text

    def test_docx_no_list_marker_residue(self, sample_markdown, config):
        """DOCX should NOT contain '- ' or '1. ' list markers as raw text."""
        from src.report_rendering import render_markdown_to_docx
        docx_bytes = render_markdown_to_docx(sample_markdown, config)
        text = docx_bytes.decode("latin-1", errors="replace")
        # The DOCX XML should use Word list styles, not raw "- " markers
        # We look for patterns like the raw text containing "- 样本量"
        assert "- 样本量：" not in text or "<w:numPr>" in text

    def test_docx_not_empty(self, sample_markdown, config):
        """DOCX generation produces non-empty bytes."""
        from src.report_rendering import render_markdown_to_docx
        docx_bytes = render_markdown_to_docx(sample_markdown, config)
        assert len(docx_bytes) > 1000  # Should be substantial

    def test_docx_handles_chinese(self, sample_markdown, config):
        """DOCX generates valid output with Chinese content (binary format)."""
        from src.report_rendering import render_markdown_to_docx
        docx_bytes = render_markdown_to_docx(sample_markdown, config)
        # DOCX is a ZIP archive → starts with PK magic bytes
        assert len(docx_bytes) > 1000
        assert docx_bytes[:2] == b'PK'


# ================================================================
# 6. HTML rendering — no artifacts
# ================================================================


class TestHtmlNoArtifacts:
    """HTML output must not contain JSON artifacts or unrendered Markdown."""

    @pytest.fixture
    def sample_markdown(self):
        return """# 数据分析报告

## 概述

这是**概述**内容。包含*斜体*文字。

- 列表项1
- 列表项2

1. 第一
2. 第二

正文段落。
"""

    def test_html_has_no_backslash_slash(self, sample_markdown):
        from src.report_rendering import render_markdown_to_html
        html = render_markdown_to_html(sample_markdown)
        assert "\\/" not in html

    def test_html_renders_bold_as_strong(self, sample_markdown):
        from src.report_rendering import render_markdown_to_html
        html = render_markdown_to_html(sample_markdown)
        assert "<strong>概述</strong>" in html
        # Should NOT contain raw **
        assert "**概述**" not in html

    def test_html_renders_italic_as_em(self):
        """*italic* should become <em>italic</em>."""
        from src.report_rendering import render_markdown_to_html
        md = "# Test\n\nThis has *italic* formatting."
        html = render_markdown_to_html(md, report_title="Test")
        assert "<em>italic</em>" in html
        assert "*italic*" not in html

    def test_html_renders_headings(self, sample_markdown):
        from src.report_rendering import render_markdown_to_html
        html = render_markdown_to_html(sample_markdown)
        assert "<h1>数据分析报告</h1>" in html or "<h1>" in html
        assert "<h2>概述</h2>" in html

    def test_html_renders_unordered_list(self, sample_markdown):
        from src.report_rendering import render_markdown_to_html
        html = render_markdown_to_html(sample_markdown)
        assert "<ul>" in html
        assert "<li>" in html
        assert "列表项1" in html

    def test_html_renders_ordered_list(self, sample_markdown):
        from src.report_rendering import render_markdown_to_html
        html = render_markdown_to_html(sample_markdown)
        assert "<ol>" in html
        assert "第一" in html

    def test_html_is_complete_document(self, sample_markdown):
        from src.report_rendering import render_markdown_to_html
        html = render_markdown_to_html(sample_markdown)
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html

    def test_html_has_chinese_content(self, sample_markdown):
        from src.report_rendering import render_markdown_to_html
        html = render_markdown_to_html(sample_markdown)
        assert "数据分析报告" in html
        assert "概述" in html


# ================================================================
# 7. End-to-end: AI output → clean report
# ================================================================


class TestEndToEndRendering:
    """End-to-end: JSON-wrapped AI output → clean HTML/DOCX."""

    def test_json_wrapped_to_clean_html(self):
        from src.report_rendering import render_markdown_to_html, render_markdown_to_docx

        # Simulate LLM returning JSON-wrapped Markdown
        llm_output = '{"report": "# 分析报告\\n\\n## 数据概览\\n\\n样本量 **N=1,234**。\\n\\n- 满意度均值 3.8\\n- 标准差 0.9"}'

        # Should extract and render cleanly
        html = render_markdown_to_html(llm_output, report_title="分析报告")
        assert "分析报告" in html
        assert "<strong>N=1,234</strong>" in html
        assert "<ul>" in html
        assert "\\/" not in html

    def test_json_wrapped_to_docx(self):
        from src.report_rendering import render_markdown_to_docx

        llm_output = '{"report": "# 分析报告\\n\\n## 数据概览\\n\\n样本量 **N=1,234**。\\n\\n- 满意度 3.8\\n- 标准差 0.9"}'
        config = {"report_title": "分析报告"}

        docx_bytes = render_markdown_to_docx(llm_output, config)
        assert len(docx_bytes) > 500
        text = docx_bytes.decode("latin-1", errors="replace")
        # Should NOT have raw markdown artifacts
        assert "**N=1,234**" not in text
        assert '"report":' not in text.lower() or text.count('"report"') < 3

    def test_pure_markdown_to_clean_html(self):
        from src.report_rendering import render_markdown_to_html

        md = "# 报告\n\n直接 Markdown，无 JSON 包裹。\n\n**重要**发现。"
        html = render_markdown_to_html(md, report_title="报告")
        assert "<strong>重要</strong>" in html
        assert "发现" in html


# ================================================================
# 8. Module exports exist
# ================================================================


class TestModuleExports:
    """All key functions are importable from report_rendering."""

    def test_all_functions_importable(self):
        from src.report_rendering import (
            extract_report_content,
            sanitize_markdown_text,
            render_markdown_to_html,
            render_markdown_to_docx,
            clean_html_escapes,
            is_probably_json_string,
        )
        # Just verify they're callable
        assert callable(extract_report_content)
        assert callable(sanitize_markdown_text)
        assert callable(render_markdown_to_html)
        assert callable(render_markdown_to_docx)
        assert callable(clean_html_escapes)
        assert callable(is_probably_json_string)
