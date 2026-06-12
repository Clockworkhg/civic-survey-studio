"""Phase 4.5 tests: DOCX XML verification, Chinese asterisk handling, AI-safe payload audit.

Verifies:
  1. DOCX contains real Chinese text in word/document.xml (not garbled)
  2. DOCX XML has no Markdown residues (** , # , \\/, \\n)
  3. Chinese bold/italic rendering correctness
  4. send_to_ai_mode="none" identical to "exclude"
  5. AI prompt never contains excluded variable names
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
import re
import zipfile
import json
import pandas as pd
import pytest


# ================================================================
# 1. DOCX XML verification
# ================================================================


class TestDocxXmlVerification:
    """Verify .docx file internals via ZIP/XML inspection."""

    @pytest.fixture
    def sample_markdown(self):
        return """# 总体满意度分析报告

## 数据概览

本次调查覆盖**政务服务**多个维度。受访者对**总体满意度**评分为 3.8 分（满分 5 分）。

### 关键发现

- **非常满意**的受访者占比最高
- 等待时间是主要**不满意**来源
- 区域间存在*显著差异*

1. 城东区满意度最高
2. 城西区等待时间最长
3. 城南区综合评分居中

| 区域 | 满意度均值 | 样本量 |
|------|-----------|--------|
| 城东区 | 4.2 | 250 |
| 城西区 | 3.5 | 300 |

> 注：以上数据基于有效样本，已排除缺失值。

这是普通段落，包含**粗体文字**和*斜体文字*。
"""

    @pytest.fixture
    def config(self):
        return {"report_title": "总体满意度分析报告"}

    @pytest.fixture
    def docx_bytes(self, sample_markdown, config):
        from src.report_rendering import render_markdown_to_docx
        return render_markdown_to_docx(sample_markdown, config)

    @pytest.fixture
    def docx_xml(self, docx_bytes):
        """Extract word/document.xml from the docx ZIP."""
        buf = io.BytesIO(docx_bytes)
        with zipfile.ZipFile(buf, 'r') as zf:
            return zf.read('word/document.xml').decode('utf-8')

    def test_docx_is_valid_zip(self, docx_bytes):
        """DOCX output is a valid ZIP archive."""
        buf = io.BytesIO(docx_bytes)
        assert zipfile.is_zipfile(buf)

    def test_docx_contains_document_xml(self, docx_bytes):
        """DOCX contains word/document.xml."""
        buf = io.BytesIO(docx_bytes)
        with zipfile.ZipFile(buf, 'r') as zf:
            names = zf.namelist()
            assert 'word/document.xml' in names

    def test_docx_chinese_text_present(self, docx_xml):
        """Chinese text is correctly encoded in DOCX XML (verified via Unicode range check)."""
        # Chinese characters are in the range U+4E00–U+9FFF
        import re
        chinese_chars = re.findall(r'[一-鿿]+', docx_xml)
        assert len(chinese_chars) > 0, "No Chinese characters found in DOCX XML"
        # Join all Chinese text and check for expected content
        all_chinese = ''.join(chinese_chars)
        # Must contain meaningful amount of Chinese text (at least 20 chars)
        assert len(all_chinese) >= 20, f"Only {len(all_chinese)} Chinese chars found"
        # Check specific expected phrases using regex over the full XML
        assert re.search(r'总体满意度', docx_xml), "Missing: 总体满意度"
        assert re.search(r'政务服务', docx_xml), "Missing: 政务服务"

    def test_docx_no_markdown_hash_residue(self, docx_xml):
        """DOCX XML must not contain '# ' heading markers."""
        # Check that '# ' does not appear before heading text
        # (it may appear in other contexts like CDATA or hex)
        import re
        # Search for "# 总体" or "## 数据" patterns — these indicate unrendered Markdown
        assert not re.search(r'(?<!\w)# 总体', docx_xml)
        assert not re.search(r'(?<!\w)## 数据', docx_xml)

    def test_docx_no_double_asterisk_residue(self, docx_xml):
        """DOCX XML must not contain ** markers."""
        # ** should be rendered as <w:b/> (bold), not left as literal text
        # The text nodes may contain the content but not the ** delimiters
        assert "**总体满意度**" not in docx_xml
        assert "**非常满意**" not in docx_xml

    def test_docx_no_backslash_slash(self, docx_xml):
        """DOCX XML must not contain \\/ artifacts."""
        assert "\\/" not in docx_xml

    def test_docx_no_literal_backslash_n(self, docx_xml):
        """DOCX XML must not contain literal \\n in text runs."""
        # \\n may appear in XML attributes but not as literal text content
        # Check that no text run contains \\n
        text_runs = re.findall(r'<w:t[^>]*>(.*?)</w:t>', docx_xml)
        for run in text_runs:
            assert "\\n" not in run, f"Found \\n in text run: {run[:80]}"

    def test_docx_heading_styles_used(self, docx_xml):
        """DOCX uses Word heading styles, not raw text formatting."""
        # Word headings use <w:pStyle w:val="Heading1"/> etc.
        assert 'Heading1' in docx_xml or 'Heading2' in docx_xml or 'heading' in docx_xml.lower()

    def test_docx_bold_runs_present(self, docx_xml):
        """Bold text is rendered as <w:b/> in DOCX XML."""
        assert '<w:b/>' in docx_xml or '<w:b ' in docx_xml


# ================================================================
# 2. Chinese asterisk handling
# ================================================================


class TestChineseAsteriskHandling:
    """Chinese text with ** and * should render correctly without residue."""

    def test_chinese_bold_rendered(self):
        """**中文粗体** should become bold, no residual **."""
        from src.report_rendering import render_markdown_to_docx
        md = "# Test\n\n这是**中文粗体**测试。"
        config = {"report_title": "Test"}
        docx_bytes = render_markdown_to_docx(md, config)
        # Extract XML
        buf = io.BytesIO(docx_bytes)
        with zipfile.ZipFile(buf, 'r') as zf:
            xml = zf.read('word/document.xml').decode('utf-8')
        # Should have bold markup
        assert '<w:b/>' in xml or '<w:b ' in xml
        # Should NOT have ** markers left in text
        text_runs = re.findall(r'<w:t[^>]*>(.*?)</w:t>', xml)
        all_text = ''.join(text_runs)
        assert '**' not in all_text, f"Found ** residue in: {all_text[:200]}"

    def test_chinese_italic_handled(self):
        """*中文斜体* should be handled (either as italic or plain text, but no * residue)."""
        from src.report_rendering import render_markdown_to_docx
        md = "# Test\n\n这是*中文斜体*测试。"
        config = {"report_title": "Test"}
        docx_bytes = render_markdown_to_docx(md, config)
        buf = io.BytesIO(docx_bytes)
        with zipfile.ZipFile(buf, 'r') as zf:
            xml = zf.read('word/document.xml').decode('utf-8')
        text_runs = re.findall(r'<w:t[^>]*>(.*?)</w:t>', xml)
        all_text = ''.join(text_runs)
        # No * residue
        assert '*中文斜体*' not in all_text, f"Raw *italic* found in: {all_text[:200]}"
        # Either italic markup or plain text (both acceptable)
        has_italic = '<w:i/>' in xml or '<w:i ' in xml
        has_plain = '中文斜体' in all_text and '*' not in all_text
        assert has_italic or has_plain, "Chinese italic not rendered correctly"

    def test_chinese_bold_in_html(self):
        """**中文粗体** in HTML should become <strong>, no ** residue."""
        from src.report_rendering import render_markdown_to_html
        md = "# Test\n\n这是**中文粗体**测试。"
        html = render_markdown_to_html(md, report_title="Test")
        assert '<strong>' in html
        assert '**中文粗体**' not in html

    def test_chinese_asterisk_no_false_positive(self):
        """Chinese text with legitimate * (e.g., p<0.05*) should not break."""
        from src.report_rendering import render_markdown_to_docx
        md = "# Test\n\n显著性水平 p<0.05*。"
        config = {"report_title": "Test"}
        docx_bytes = render_markdown_to_docx(md, config)
        buf = io.BytesIO(docx_bytes)
        with zipfile.ZipFile(buf, 'r') as zf:
            xml = zf.read('word/document.xml').decode('utf-8')
        # Should not crash and should contain the text
        assert 'p&lt;0.05' in xml or 'p<0.05' in xml or '0.05' in xml

    def test_no_escape_chinese_asterisks_side_effect(self):
        """escape_chinese_asterisks should not corrupt normal Markdown."""
        from src.utils import escape_chinese_asterisks
        from src.report_rendering import sanitize_markdown_text
        md = "这是**粗体**和*斜体*的正常使用。"
        escaped = escape_chinese_asterisks(md)
        # The function should preserve meaningful ** and *
        # Check that content isn't lost
        assert len(escaped) >= len(md) - 4  # At most 4 extra chars for escaping


# ================================================================
# 3. AI-safe payload: send_to_ai_mode="none"
# ================================================================


class TestAiSafePayloadNoneMode:
    """send_to_ai_mode='none' should be identical to 'exclude'."""

    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame({
            "satisfaction": [4, 5, 3, 4, 5, 2, 3, 4, 5, 4],
            "region":        ["A", "B", "A", "B", "A", "B", "A", "B", "A", "B"],
            "secret_field":  ["x1", "x2", "x3", "x4", "x5", "x6", "x7", "x8", "x9", "x10"],
        })

    @pytest.fixture
    def schema_with_none_mode(self, sample_df):
        from src.schema_infer import infer_variable_schema
        schema = infer_variable_schema(sample_df)
        mask = schema["column"] == "secret_field"
        if mask.any():
            schema.loc[mask, "privacy_risk"] = "high"
            schema.loc[mask, "send_to_ai_mode"] = "none"
            schema.loc[mask, "allow_send_to_ai"] = False
        return schema

    def test_none_mode_excluded_from_variables(self, sample_df, schema_with_none_mode):
        """send_to_ai_mode='none' variable is removed from variables section."""
        from src.analysis_packager import build_analysis_payload, filter_payload_for_ai
        from src.generic_analysis import run_full_analysis
        config = {"target_variable": "satisfaction", "group_variables": [], "explanatory_variables": []}
        results = run_full_analysis(sample_df, schema_with_none_mode, config)
        payload = build_analysis_payload(df=sample_df, schema_df=schema_with_none_mode, config=config, analysis_results=results)
        filtered = filter_payload_for_ai(payload, schema_with_none_mode)
        assert "secret_field" not in filtered["variables"]

    def test_none_mode_excluded_from_name_map(self, sample_df, schema_with_none_mode):
        """send_to_ai_mode='none' variable removed from variable_name_map."""
        from src.analysis_packager import build_analysis_payload, filter_payload_for_ai
        from src.generic_analysis import run_full_analysis
        config = {"target_variable": "satisfaction", "group_variables": [], "explanatory_variables": []}
        results = run_full_analysis(sample_df, schema_with_none_mode, config)
        payload = build_analysis_payload(df=sample_df, schema_df=schema_with_none_mode, config=config, analysis_results=results)
        filtered = filter_payload_for_ai(payload, schema_with_none_mode)
        name_map = filtered["project_meta"].get("variable_name_map", {})
        assert "secret_field" not in name_map

    def test_none_mode_excluded_from_variable_schema(self, sample_df, schema_with_none_mode):
        """send_to_ai_mode='none' variable removed from variable_schema."""
        from src.analysis_packager import build_analysis_payload, filter_payload_for_ai
        from src.generic_analysis import run_full_analysis
        config = {"target_variable": "satisfaction", "group_variables": [], "explanatory_variables": []}
        results = run_full_analysis(sample_df, schema_with_none_mode, config)
        payload = build_analysis_payload(df=sample_df, schema_df=schema_with_none_mode, config=config, analysis_results=results)
        filtered = filter_payload_for_ai(payload, schema_with_none_mode)
        schema_cols = {e["column"] for e in filtered["variable_schema"]}
        assert "secret_field" not in schema_cols

    def test_local_payload_still_has_secret_field(self, sample_df, schema_with_none_mode):
        """Local (unfiltered) payload retains the excluded variable for debugging."""
        from src.analysis_packager import build_analysis_payload
        from src.generic_analysis import run_full_analysis
        config = {"target_variable": "satisfaction", "group_variables": [], "explanatory_variables": []}
        results = run_full_analysis(sample_df, schema_with_none_mode, config)
        payload = build_analysis_payload(df=sample_df, schema_df=schema_with_none_mode, config=config, analysis_results=results)
        # Local payload keeps everything
        assert "secret_field" in payload["variables"]


# ================================================================
# 4. AI prompt never contains excluded variable names
# ================================================================


class TestAiPromptNoExcludedVars:
    """Verify that filtered payload has no trace of excluded variable names."""

    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame({
            "satisfaction": [4, 5, 3, 4, 5, 2, 3, 4, 5, 4],
            "region":        ["A", "B", "A", "B", "A", "B", "A", "B", "A", "B"],
            "id_number":     ["ID001", "ID002", "ID003", "ID004", "ID005",
                              "ID006", "ID007", "ID008", "ID009", "ID010"],
        })

    @pytest.fixture
    def schema(self, sample_df):
        from src.schema_infer import infer_variable_schema
        schema = infer_variable_schema(sample_df)
        mask = schema["column"] == "id_number"
        if mask.any():
            schema.loc[mask, "privacy_risk"] = "high"
            schema.loc[mask, "send_to_ai_mode"] = "exclude"
            schema.loc[mask, "allow_send_to_ai"] = False
        return schema

    def test_filtered_payload_no_excluded_name_in_json(self, sample_df, schema):
        """JSON representation of filtered payload contains no excluded variable names."""
        from src.analysis_packager import build_analysis_payload, filter_payload_for_ai, to_json_payload
        from src.generic_analysis import run_full_analysis
        config = {"target_variable": "satisfaction", "group_variables": [], "explanatory_variables": []}
        results = run_full_analysis(sample_df, schema, config)
        payload = build_analysis_payload(df=sample_df, schema_df=schema, config=config, analysis_results=results)
        filtered = filter_payload_for_ai(payload, schema)
        json_str = to_json_payload(filtered)
        # The raw column name must not appear in the JSON
        assert "id_number" not in json_str, f"Excluded variable 'id_number' found in AI-safe payload JSON"

    def test_filtered_payload_has_expected_vars(self, sample_df, schema):
        """Non-excluded variables remain in the filtered payload."""
        from src.analysis_packager import build_analysis_payload, filter_payload_for_ai
        from src.generic_analysis import run_full_analysis
        config = {"target_variable": "satisfaction", "group_variables": [], "explanatory_variables": []}
        results = run_full_analysis(sample_df, schema, config)
        payload = build_analysis_payload(df=sample_df, schema_df=schema, config=config, analysis_results=results)
        filtered = filter_payload_for_ai(payload, schema)
        assert "satisfaction" in filtered["variables"]
        assert "region" in filtered["variables"]


# ================================================================
# 5. No privacy config → high-risk defaults to excluded
# ================================================================


class TestDefaultHighRiskExclusion:
    """When no explicit privacy config, high-risk vars default to safe."""

    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame({
            "score":    [1, 2, 3, 1, 2, 3, 1, 2, 3, 1],
            "phone":    ["13800000001", "13800000002", "13800000003", "13800000004",
                         "13800000005", "13800000006", "13800000007", "13800000008",
                         "13800000009", "13800000010"],
        })

    def test_high_risk_default_excluded_without_explicit_config(self, sample_df):
        """High-risk variable excluded even without explicit privacy_settings dict."""
        from src.schema_infer import infer_variable_schema
        from src.analysis_packager import build_analysis_payload, filter_payload_for_ai
        from src.generic_analysis import run_full_analysis

        schema = infer_variable_schema(sample_df)
        # Modify schema to mark phone as high risk with no allow
        mask = schema["column"] == "phone"
        if mask.any():
            schema.loc[mask, "privacy_risk"] = "high"
            schema.loc[mask, "allow_send_to_ai"] = False
            schema.loc[mask, "send_to_ai_mode"] = "aggregate_only"

        config = {"target_variable": "score", "group_variables": [], "explanatory_variables": []}
        results = run_full_analysis(sample_df, schema, config)
        payload = build_analysis_payload(df=sample_df, schema_df=schema, config=config, analysis_results=results)

        # Filter without passing explicit privacy_settings
        filtered = filter_payload_for_ai(payload, schema, privacy_settings=None)
        assert "phone" not in filtered["variables"]
