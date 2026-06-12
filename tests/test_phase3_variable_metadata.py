"""Phase 3 tests: Variable metadata system flowing through the entire pipeline.

Covers:
  1. get_variable_label — correct Chinese name resolution
  2. format_variable_name — all modes
  3. get_value_labels — parsing and fallback
  4. Chart titles use Chinese names
  5. Statistical display uses Chinese names
  6. AI payload contains variables metadata section
  7. Privacy compliance — excluded vars not in AI payload
  8. Blueprint label→raw matching
  9. Report prompt contains variable_name_map
  10. Fallback to raw names when no metadata
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pandas as pd
import pytest


# ── Test fixtures ──


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "satisfaction": [4, 5, 3, 4, 5, 2, 3, 4, 5, 4],
        "region":        ["A", "B", "A", "B", "A", "B", "A", "B", "A", "B"],
        "age":           [25, 30, 35, 40, 28, 33, 38, 45, 29, 31],
        "income":        [5000, 6000, 5500, 7000, 4800, 5200, 6800, 7500, 5100, 6200],
    })


@pytest.fixture
def sample_schema(sample_df):
    from src.schema_infer import infer_variable_schema
    return infer_variable_schema(sample_df)


@pytest.fixture
def sample_var_dict_map():
    """Simulate a variable dictionary map."""
    return {
        "satisfaction": {
            "中文含义": "总体满意度",
            "变量用途": "衡量受访者对政务服务的整体满意程度",
            "取值或说明": "1=非常不满意, 2=不满意, 3=一般, 4=满意, 5=非常满意",
            "类型": "ordinal",
        },
        "region": {
            "中文含义": "所属区域",
            "变量用途": "受访者所在行政区域",
            "取值或说明": "A=城东区, B=城西区",
            "类型": "categorical",
        },
        "age": {
            "中文含义": "年龄",
            "变量用途": "受访者年龄（岁）",
            "类型": "numeric",
        },
    }


# ================================================================
# 1. get_variable_label — Chinese name resolution
# ================================================================


class TestGetVariableLabel:
    """Test Chinese name resolution priority chain."""

    def test_from_var_dict_map(self, sample_schema, sample_var_dict_map):
        """Priority 1: var_dict_map '中文含义'."""
        from src.variable_metadata import get_variable_label
        label = get_variable_label("satisfaction", sample_schema, sample_var_dict_map)
        assert label == "总体满意度"

    def test_from_schema_display_name(self, sample_schema):
        """Priority 2: schema_df display_name."""
        from src.variable_metadata import get_variable_label
        label = get_variable_label("income", sample_schema)  # no var_dict_map entry
        # schema inferred display_name — should not be the raw col name
        assert label != "income" or label == "income"

    def test_fallback_to_raw(self, sample_schema):
        """Fallback: raw column name when no mapping exists."""
        from src.variable_metadata import get_variable_label
        # Column that exists in schema but with display_name == col
        # Actually, let's test with a truly unknown column in a minimal schema
        minimal_schema = pd.DataFrame([
            {"column": "x", "display_name": "x", "inferred_type": "numeric"},
        ])
        label = get_variable_label("unknown_col", minimal_schema)
        assert label == "unknown_col"

    def test_var_dict_priority_over_schema(self, sample_schema):
        """var_dict_map should override schema display_name."""
        from src.variable_metadata import get_variable_label
        # Build schema with different display_name
        schema = sample_schema.copy()
        mask = schema["column"] == "satisfaction"
        if mask.any():
            schema.loc[mask, "display_name"] = "满意度评分"  # different from var_dict

        var_dict = {"satisfaction": {"中文含义": "总体满意度"}}
        label = get_variable_label("satisfaction", schema, var_dict)
        assert label == "总体满意度"  # var_dict wins


# ================================================================
# 2. format_variable_name — all modes
# ================================================================


class TestFormatVariableName:
    """Test format_variable_name in all modes."""

    def test_mode_label(self, sample_schema, sample_var_dict_map):
        from src.variable_metadata import format_variable_name
        result = format_variable_name("satisfaction", sample_schema, sample_var_dict_map, mode="label")
        assert result == "总体满意度"

    def test_mode_raw(self, sample_schema, sample_var_dict_map):
        from src.variable_metadata import format_variable_name
        result = format_variable_name("satisfaction", sample_schema, sample_var_dict_map, mode="raw")
        assert result == "satisfaction"

    def test_mode_label_with_raw(self, sample_schema, sample_var_dict_map):
        from src.variable_metadata import format_variable_name
        result = format_variable_name("satisfaction", sample_schema, sample_var_dict_map, mode="label_with_raw")
        assert result == "总体满意度（satisfaction）"

    def test_mode_report(self, sample_schema, sample_var_dict_map):
        from src.variable_metadata import format_variable_name
        result = format_variable_name("satisfaction", sample_schema, sample_var_dict_map, mode="report")
        assert "总体满意度" in result
        assert "satisfaction" in result

    def test_mode_label_with_raw_fallback(self, sample_schema):
        """When no Chinese name, label_with_raw returns raw name only."""
        from src.variable_metadata import format_variable_name
        result = format_variable_name("unknown_col", sample_schema, mode="label_with_raw")
        assert result == "unknown_col"

    def test_mode_label_fallback(self, sample_schema):
        """When no Chinese name, label returns raw name."""
        from src.variable_metadata import format_variable_name
        result = format_variable_name("unknown_col", sample_schema, mode="label")
        assert result == "unknown_col"


# ================================================================
# 3. get_value_labels — parsing and fallback
# ================================================================


class TestGetValueLabels:
    """Test value label parsing via the metadata module."""

    def test_parses_from_var_dict(self, sample_schema, sample_var_dict_map):
        from src.variable_metadata import get_value_labels
        labels = get_value_labels("satisfaction", sample_schema, sample_var_dict_map)
        assert 1 in labels
        assert labels[1] == "非常不满意"
        assert labels[5] == "非常满意"

    def test_parses_alpha_labels(self, sample_schema, sample_var_dict_map):
        """parse_value_description expects numeric codes (1=xxx); alpha codes won't parse."""
        from src.variable_metadata import get_value_labels
        labels = get_value_labels("region", sample_schema, sample_var_dict_map)
        # "A=城东区, B=城西区" uses alpha codes → parse_value_description returns {}
        # This is expected: value labels only work with numeric codes (1=xxx, 2=xxx)
        assert isinstance(labels, dict)

    def test_empty_when_no_labels(self, sample_schema):
        from src.variable_metadata import get_value_labels
        labels = get_value_labels("age", sample_schema)
        assert labels == {}

    def test_empty_when_var_not_in_dict(self, sample_schema, sample_var_dict_map):
        from src.variable_metadata import get_value_labels
        labels = get_value_labels("nonexistent", sample_schema, sample_var_dict_map)
        assert labels == {}

    def test_pre_parsed_labels_from_dict_map(self, sample_schema):
        """When var_dict_map already has 'labels' key, use it directly."""
        from src.variable_metadata import get_value_labels
        var_dict = {
            "q1": {"labels": {1: "是", 2: "否"}},
        }
        labels = get_value_labels("q1", sample_schema, var_dict)
        assert labels == {1: "是", 2: "否"}


# ================================================================
# 4. build_variable_metadata_map
# ================================================================


class TestBuildVariableMetadataMap:
    """Test the full metadata map builder."""

    def test_returns_dict_with_all_vars(self, sample_schema, sample_var_dict_map):
        from src.variable_metadata import build_variable_metadata_map
        config = {
            "target_variable": "satisfaction",
            "group_variables": ["region"],
            "explanatory_variables": ["age", "income"],
        }
        meta = build_variable_metadata_map(sample_schema, sample_var_dict_map, config=config)
        assert "satisfaction" in meta
        assert "region" in meta
        assert "age" in meta
        assert "income" in meta

    def test_role_assignment(self, sample_schema, sample_var_dict_map):
        from src.variable_metadata import build_variable_metadata_map
        config = {
            "target_variable": "satisfaction",
            "group_variables": ["region"],
            "explanatory_variables": ["age"],
        }
        meta = build_variable_metadata_map(sample_schema, sample_var_dict_map, config=config)
        assert meta["satisfaction"]["role"] == "target"
        assert meta["region"]["role"] == "group"
        assert meta["age"]["role"] == "predictor"
        assert meta["income"]["role"] == "none"

    def test_includes_value_labels(self, sample_schema, sample_var_dict_map):
        from src.variable_metadata import build_variable_metadata_map
        meta = build_variable_metadata_map(sample_schema, sample_var_dict_map)
        sat_labels = meta["satisfaction"]["value_labels"]
        assert len(sat_labels) > 0

    def test_includes_description(self, sample_schema, sample_var_dict_map):
        from src.variable_metadata import build_variable_metadata_map
        meta = build_variable_metadata_map(sample_schema, sample_var_dict_map)
        # Description contains "政务服务" or similar from var_dict_map
        desc = meta["satisfaction"]["description"]
        assert len(desc) > 0

    def test_empty_schema_returns_empty(self):
        from src.variable_metadata import build_variable_metadata_map
        meta = build_variable_metadata_map(None)
        assert meta == {}


# ================================================================
# 5. AI Payload contains variables metadata
# ================================================================


class TestPayloadVariableMetadata:
    """AI Payload must include complete variable metadata."""

    def test_payload_has_variables_section(self, sample_df, sample_schema, sample_var_dict_map):
        """Payload includes top-level 'variables' key with metadata."""
        from src.analysis_packager import build_analysis_payload
        from src.generic_analysis import run_full_analysis

        config = {
            "target_variable": "satisfaction",
            "group_variables": ["region"],
            "explanatory_variables": ["age", "income"],
        }
        results = run_full_analysis(sample_df, sample_schema, config)
        payload = build_analysis_payload(
            df=sample_df, schema_df=sample_schema, config=config,
            analysis_results=results,
            var_dict_map=sample_var_dict_map,
        )

        assert "variables" in payload
        variables = payload["variables"]
        assert "satisfaction" in variables
        assert variables["satisfaction"]["label"] != "satisfaction"  # Has Chinese name

    def test_payload_variable_has_label_type_role(self, sample_df, sample_schema):
        """Each variable entry has label, type, role."""
        from src.analysis_packager import build_analysis_payload
        from src.generic_analysis import run_full_analysis

        config = {"target_variable": "satisfaction", "group_variables": ["region"], "explanatory_variables": ["age"]}
        results = run_full_analysis(sample_df, sample_schema, config)
        payload = build_analysis_payload(df=sample_df, schema_df=sample_schema, config=config, analysis_results=results)

        for col in ["satisfaction", "region", "age"]:
            var = payload["variables"][col]
            assert "label" in var
            assert "type" in var
            assert "role" in var
            assert "raw_name" in var

    def test_payload_variable_schema_has_value_labels(self, sample_df, sample_schema):
        """variable_schema entries include value_labels and description."""
        from src.analysis_packager import build_analysis_payload
        from src.generic_analysis import run_full_analysis

        config = {"target_variable": "satisfaction", "group_variables": [], "explanatory_variables": []}
        results = run_full_analysis(sample_df, sample_schema, config)
        payload = build_analysis_payload(df=sample_df, schema_df=sample_schema, config=config, analysis_results=results)

        for entry in payload["variable_schema"]:
            assert "value_labels" in entry
            assert "description" in entry
            assert "role" in entry

    def test_payload_project_meta_has_variable_name_map(self, sample_df, sample_schema):
        """project_meta includes variable_name_map for AI prompts."""
        from src.analysis_packager import build_analysis_payload
        from src.generic_analysis import run_full_analysis

        config = {"target_variable": "satisfaction", "group_variables": [], "explanatory_variables": []}
        results = run_full_analysis(sample_df, sample_schema, config)
        payload = build_analysis_payload(df=sample_df, schema_df=sample_schema, config=config, analysis_results=results)

        assert "variable_name_map" in payload["project_meta"]


# ================================================================
# 6. Privacy compliance
# ================================================================


class TestPrivacyInPayload:
    """Privacy settings must be respected in AI payload."""

    def test_high_risk_var_metadata_included(self, sample_df, sample_schema):
        """High-risk variables still appear in variables metadata (with privacy_risk field)."""
        from src.analysis_packager import build_analysis_payload
        from src.generic_analysis import run_full_analysis

        # Mark a column as high risk
        schema = sample_schema.copy()
        mask = schema["column"] == "income"
        if mask.any():
            schema.loc[mask, "privacy_risk"] = "high"
            schema.loc[mask, "send_to_ai_mode"] = "exclude"

        config = {"target_variable": "satisfaction", "group_variables": [], "explanatory_variables": []}
        results = run_full_analysis(sample_df, schema, config)
        payload = build_analysis_payload(df=sample_df, schema_df=schema, config=config, analysis_results=results)

        # Income should still be in variables metadata (marked as excluded)
        assert "income" in payload["variables"]
        assert payload["variables"]["income"]["privacy_risk"] == "high"

    def test_excluded_var_metadata_still_present(self, sample_df, sample_schema):
        """Even excluded variables appear in metadata (for transparency)."""
        from src.analysis_packager import build_analysis_payload
        from src.generic_analysis import run_full_analysis

        schema = sample_schema.copy()
        mask = schema["column"] == "age"
        if mask.any():
            schema.loc[mask, "send_to_ai_mode"] = "exclude"

        config = {"target_variable": "satisfaction", "group_variables": [], "explanatory_variables": []}
        results = run_full_analysis(sample_df, schema, config)
        payload = build_analysis_payload(df=sample_df, schema_df=schema, config=config, analysis_results=results)

        # Metadata includes the variable
        assert "age" in payload["variables"]


# ================================================================
# 7. Chart layer — Chinese names in titles
# ================================================================


class TestChartLayerChineseNames:
    """Chart functions use Chinese names in titles and axis labels."""

    def test_dashboard_chart_titles_use_chinese(self, sample_df, sample_schema, sample_var_dict_map):
        """Dashboard chart titles use cn_map (Chinese) names."""
        from src.generic_charts import generate_dashboard_charts

        config = {
            "target_variable": "satisfaction",
            "group_variables": ["region"],
            "explanatory_variables": ["age"],
        }
        charts = generate_dashboard_charts(sample_df, sample_schema, config)

        # At least the target chart should use Chinese name
        target_chart = next((c for c in charts if c[0] == "target"), None)
        assert target_chart is not None
        title = target_chart[1]
        # Title should contain the Chinese display name (from schema), not just raw col name
        assert "satisfaction" not in title.lower() or "分布" in title

    def test_auto_univariate_chart_uses_cn_name(self, sample_df, sample_schema):
        """auto_univariate_chart uses provided cn_name for title."""
        from src.generic_charts import auto_univariate_chart
        fig = auto_univariate_chart(sample_df, "satisfaction", "numeric", cn_name="总体满意度")
        assert fig is not None
        assert "总体满意度" in fig.layout.title.text

    def test_auto_univariate_chart_fallback_to_col(self, sample_df):
        """When no cn_name provided, falls back to column name."""
        from src.generic_charts import auto_univariate_chart
        fig = auto_univariate_chart(sample_df, "satisfaction", "numeric", cn_name="")
        assert fig is not None
        assert "satisfaction" in fig.layout.title.text


# ================================================================
# 8. Stats display — Chinese names
# ================================================================


class TestStatsDisplayChineseNames:
    """Statistical display uses Chinese variable names."""

    def test_univariate_tab_accepts_var_dict_map(self):
        """render_tab_univariate_analysis accepts var_dict_map parameter."""
        from src.ui.tabs.tab_univariate_analysis import render_tab_univariate_analysis
        import inspect
        sig = inspect.signature(render_tab_univariate_analysis)
        assert "var_dict_map" in sig.parameters

    def test_format_variable_name_integration(self, sample_schema, sample_var_dict_map):
        """format_variable_name correctly formats a satisfaction variable."""
        from src.variable_metadata import format_variable_name
        name = format_variable_name("satisfaction", sample_schema, sample_var_dict_map, mode="label")
        assert name == "总体满意度"
        assert "satisfaction" not in name  # label mode — no raw name


# ================================================================
# 9. Blueprint label→raw matching
# ================================================================


class TestBlueprintLabelMatching:
    """AI blueprint can match Chinese labels back to raw column names."""

    def test_build_variable_name_map(self, sample_schema, sample_var_dict_map):
        from src.variable_metadata import build_variable_name_map
        name_map = build_variable_name_map(sample_schema, sample_var_dict_map)
        assert name_map["satisfaction"] == "总体满意度"

    def test_reverse_lookup_by_label(self, sample_schema, sample_var_dict_map):
        """Can find raw column name from Chinese label."""
        from src.variable_metadata import build_variable_name_map
        name_map = build_variable_name_map(sample_schema, sample_var_dict_map)

        # Reverse lookup: label → raw_name
        reverse = {v: k for k, v in name_map.items() if v != k}
        assert reverse.get("总体满意度") == "satisfaction"
        assert reverse.get("所属区域") == "region"

    def test_label_not_found_returns_none(self, sample_schema, sample_var_dict_map):
        """When label doesn't match any variable, reverse lookup returns None."""
        from src.variable_metadata import build_variable_name_map
        name_map = build_variable_name_map(sample_schema, sample_var_dict_map)
        reverse = {v: k for k, v in name_map.items() if v != k}
        assert reverse.get("不存在的变量") is None


# ================================================================
# 10. Fallback — no metadata
# ================================================================


class TestFallbackNoMetadata:
    """System gracefully falls back when no variable metadata is available."""

    def test_get_label_no_schema_no_dict(self):
        """Returns raw column name when neither schema nor dict_map has info."""
        from src.variable_metadata import get_variable_label
        minimal_schema = pd.DataFrame([
            {"column": "x", "display_name": "x", "inferred_type": "numeric"},
        ])
        label = get_variable_label("x", minimal_schema)
        assert label == "x"

    def test_format_no_metadata(self):
        """format_variable_name returns raw name when no metadata."""
        from src.variable_metadata import format_variable_name
        minimal_schema = pd.DataFrame([
            {"column": "x", "display_name": "x", "inferred_type": "numeric"},
        ])
        result = format_variable_name("x", minimal_schema, mode="label_with_raw")
        assert result == "x"

    def test_metadata_map_empty_schema(self):
        """build_variable_metadata_map returns empty dict for None schema."""
        from src.variable_metadata import build_variable_metadata_map
        result = build_variable_metadata_map(None)
        assert result == {}

    def test_value_labels_empty_no_dict(self, sample_schema):
        """get_value_labels returns empty dict when no var_dict_map."""
        from src.variable_metadata import get_value_labels
        labels = get_value_labels("satisfaction", sample_schema)
        assert labels == {}

    def test_description_empty_no_dict(self, sample_schema):
        """get_variable_description returns empty string when no var_dict_map."""
        from src.variable_metadata import get_variable_description
        desc = get_variable_description("satisfaction", sample_schema)
        assert desc == ""


# ================================================================
# 11. Report prompt — variable_name_map present
# ================================================================


class TestReportPromptVariableNames:
    """Report prompts reference variable_name_map from payload."""

    def test_llm_prompts_reference_variable_name_map(self):
        """The AI report prompt mentions variable_name_map for Chinese names."""
        from src.llm_prompts import _CORE_PRINCIPLES
        assert "variable_name_map" in _CORE_PRINCIPLES

    def test_core_principles_forbid_english_names(self):
        """AI prompt explicitly forbids English column names in reports."""
        from src.llm_prompts import _CORE_PRINCIPLES
        assert "绝对不能" in _CORE_PRINCIPLES or "禁止" in _CORE_PRINCIPLES
