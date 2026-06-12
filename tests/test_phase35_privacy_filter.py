"""Phase 3.5 tests: AI Payload privacy gate.

Verifies that filter_payload_for_ai correctly:
  1. Removes excluded variables from all payload sections
  2. Strips examples from aggregate_only variables
  3. Defaults to excluding high-risk unapproved variables
  4. Preserves the original payload unmodified
  5. Marks filtered payload with metadata
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import copy
import pandas as pd
import pytest


# ── Fixtures ──


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "satisfaction": [4, 5, 3, 4, 5, 2, 3, 4, 5, 4],
        "region":        ["A", "B", "A", "B", "A", "B", "A", "B", "A", "B"],
        "age":           [25, 30, 35, 40, 28, 33, 38, 45, 29, 31],
        "id_card":       ["id001", "id002", "id003", "id004", "id005",
                          "id006", "id007", "id008", "id009", "id010"],
        "phone":         ["13800000001", "13800000002", "13800000003", "13800000004",
                          "13800000005", "13800000006", "13800000007", "13800000008",
                          "13800000009", "13800000010"],
    })


@pytest.fixture
def sample_schema(sample_df):
    from src.schema_infer import infer_variable_schema
    schema = infer_variable_schema(sample_df)

    # Manually mark privacy settings for testing
    for _, row in schema.iterrows():
        col = row["column"]
        if col == "id_card":
            row["privacy_risk"] = "high"
            row["send_to_ai_mode"] = "exclude"
            row["allow_send_to_ai"] = False
        elif col == "phone":
            row["privacy_risk"] = "high"
            row["send_to_ai_mode"] = "exclude"
            row["allow_send_to_ai"] = False
        elif col == "age":
            row["privacy_risk"] = "medium"
            row["send_to_ai_mode"] = "aggregate_only"

    return schema


@pytest.fixture
def sample_payload(sample_df, sample_schema):
    """Build a full payload for filtering tests."""
    from src.analysis_packager import build_analysis_payload
    from src.generic_analysis import run_full_analysis

    config = {
        "target_variable": "satisfaction",
        "group_variables": ["region"],
        "explanatory_variables": ["age"],
    }
    results = run_full_analysis(sample_df, sample_schema, config)
    return build_analysis_payload(
        df=sample_df, schema_df=sample_schema, config=config,
        analysis_results=results,
    )


# ================================================================
# 1. Exclusion: send_to_ai_mode="exclude"
# ================================================================


class TestExcludeVariables:
    """Variables with send_to_ai_mode="exclude" must be completely removed."""

    def test_excluded_var_removed_from_variables(self, sample_payload, sample_schema):
        from src.analysis_packager import filter_payload_for_ai
        filtered = filter_payload_for_ai(sample_payload, sample_schema)
        # id_card and phone are marked exclude
        assert "id_card" not in filtered["variables"]
        assert "phone" not in filtered["variables"]

    def test_excluded_var_removed_from_variable_schema(self, sample_payload, sample_schema):
        from src.analysis_packager import filter_payload_for_ai
        filtered = filter_payload_for_ai(sample_payload, sample_schema)
        schema_cols = {e["column"] for e in filtered["variable_schema"]}
        assert "id_card" not in schema_cols
        assert "phone" not in schema_cols

    def test_excluded_var_removed_from_name_map(self, sample_payload, sample_schema):
        from src.analysis_packager import filter_payload_for_ai
        filtered = filter_payload_for_ai(sample_payload, sample_schema)
        name_map = filtered["project_meta"].get("variable_name_map", {})
        assert "id_card" not in name_map
        assert "phone" not in name_map

    def test_non_excluded_vars_still_present(self, sample_payload, sample_schema):
        from src.analysis_packager import filter_payload_for_ai
        filtered = filter_payload_for_ai(sample_payload, sample_schema)
        assert "satisfaction" in filtered["variables"]
        assert "region" in filtered["variables"]
        assert "age" in filtered["variables"]

    def test_original_payload_unmodified(self, sample_payload, sample_schema):
        from src.analysis_packager import filter_payload_for_ai
        original_vars = set(sample_payload["variables"].keys())
        filtered = filter_payload_for_ai(sample_payload, sample_schema)
        # Original should still have all variables
        assert "id_card" in sample_payload["variables"]
        assert "phone" in sample_payload["variables"]
        # Filtered should be a different object
        assert filtered is not sample_payload


# ================================================================
# 2. Aggregate-only: strip examples
# ================================================================


class TestAggregateOnly:
    """Variables with send_to_ai_mode="aggregate_only" must have examples stripped."""

    def test_aggregate_only_strips_value_labels(self, sample_payload, sample_schema):
        from src.analysis_packager import filter_payload_for_ai
        # Age is marked aggregate_only
        filtered = filter_payload_for_ai(sample_payload, sample_schema)
        age_var = filtered["variables"].get("age")
        assert age_var is not None  # Still present
        assert "value_labels" not in age_var  # But labels stripped

    def test_aggregate_only_keeps_label_and_type(self, sample_payload, sample_schema):
        from src.analysis_packager import filter_payload_for_ai
        filtered = filter_payload_for_ai(sample_payload, sample_schema)
        age_var = filtered["variables"].get("age")
        assert age_var is not None
        assert "label" in age_var
        assert "type" in age_var
        assert "role" in age_var

    def test_aggregate_only_schema_entries_stripped(self, sample_payload, sample_schema):
        from src.analysis_packager import filter_payload_for_ai
        filtered = filter_payload_for_ai(sample_payload, sample_schema)
        for entry in filtered["variable_schema"]:
            if entry["column"] == "age":
                assert "example_values" not in entry
                assert "value_labels" not in entry


# ================================================================
# 3. High-risk default exclusion
# ================================================================


class TestHighRiskDefault:
    """High-risk variables with no explicit allow should default to excluded."""

    def test_high_risk_no_allow_defaults_excluded(self, sample_df):
        from src.schema_infer import infer_variable_schema
        from src.analysis_packager import build_analysis_payload, filter_payload_for_ai
        from src.generic_analysis import run_full_analysis

        # Schema with high risk, no explicit allow
        schema = infer_variable_schema(sample_df)
        mask = schema["column"] == "id_card"
        if mask.any():
            schema.loc[mask, "privacy_risk"] = "high"
            schema.loc[mask, "allow_send_to_ai"] = False
            schema.loc[mask, "send_to_ai_mode"] = "aggregate_only"  # ignored because high+not allowed

        config = {"target_variable": "satisfaction", "group_variables": [], "explanatory_variables": []}
        results = run_full_analysis(sample_df, schema, config)
        payload = build_analysis_payload(df=sample_df, schema_df=schema, config=config, analysis_results=results)
        filtered = filter_payload_for_ai(payload, schema)

        assert "id_card" not in filtered["variables"]

    def test_high_risk_with_explicit_allow_kept(self, sample_df):
        from src.schema_infer import infer_variable_schema
        from src.analysis_packager import build_analysis_payload, filter_payload_for_ai
        from src.generic_analysis import run_full_analysis

        schema = infer_variable_schema(sample_df)
        mask = schema["column"] == "phone"
        if mask.any():
            schema.loc[mask, "privacy_risk"] = "high"
            schema.loc[mask, "allow_send_to_ai"] = True
            schema.loc[mask, "send_to_ai_mode"] = "aggregate_only"

        config = {"target_variable": "satisfaction", "group_variables": [], "explanatory_variables": []}
        results = run_full_analysis(sample_df, schema, config)
        payload = build_analysis_payload(df=sample_df, schema_df=schema, config=config, analysis_results=results)
        filtered = filter_payload_for_ai(payload, schema)

        # Should be present because explicitly allowed (but aggregate_only)
        assert "phone" in filtered["variables"]


# ================================================================
# 4. Filter metadata markers
# ================================================================


class TestFilterMetadata:
    """Filtered payload should be marked with metadata."""

    def test_filtered_payload_marked(self, sample_payload, sample_schema):
        from src.analysis_packager import filter_payload_for_ai
        filtered = filter_payload_for_ai(sample_payload, sample_schema)
        assert filtered.get("_privacy_filtered") is True

    def test_excluded_vars_listed(self, sample_payload, sample_schema):
        from src.analysis_packager import filter_payload_for_ai
        filtered = filter_payload_for_ai(sample_payload, sample_schema)
        excluded_count = filtered.get("_privacy_excluded_count", 0)
        assert excluded_count >= 2  # id_card and phone

    def test_aggregate_only_vars_listed(self, sample_payload, sample_schema):
        from src.analysis_packager import filter_payload_for_ai
        filtered = filter_payload_for_ai(sample_payload, sample_schema)
        agg_only_count = filtered.get("_privacy_aggregate_only_count", 0)
        assert agg_only_count >= 1  # age


# ================================================================
# 5. No privacy settings → safe defaults
# ================================================================


class TestNoPrivacySettings:
    """When no privacy settings exist, high-risk vars should default to safe."""

    def test_no_privacy_settings_handled(self, sample_df):
        from src.schema_infer import infer_variable_schema
        from src.analysis_packager import build_analysis_payload, filter_payload_for_ai
        from src.generic_analysis import run_full_analysis

        # Fresh schema — all defaults (usually low/none risk)
        schema = infer_variable_schema(sample_df)
        config = {"target_variable": "satisfaction", "group_variables": [], "explanatory_variables": []}
        results = run_full_analysis(sample_df, schema, config)
        payload = build_analysis_payload(df=sample_df, schema_df=schema, config=config, analysis_results=results)

        # Filter should not crash with default schema
        filtered = filter_payload_for_ai(payload, schema)
        assert filtered.get("_privacy_filtered") is True
        # Default: most vars have low risk → should remain
        assert "satisfaction" in filtered["variables"]


# ================================================================
# 6. Analysis results filtered
# ================================================================


class TestAnalysisResultsFiltered:
    """Analysis results involving excluded variables should be removed."""

    def test_excluded_var_results_removed(self, sample_payload, sample_schema):
        from src.analysis_packager import filter_payload_for_ai
        filtered = filter_payload_for_ai(sample_payload, sample_schema)

        # Check analysis_results don't reference excluded vars
        for result in filtered.get("analysis_results", []):
            if isinstance(result, dict):
                for field in ("variables", "variable", "row_col", "col_col"):
                    val = result.get(field)
                    if isinstance(val, str):
                        assert val not in ("id_card", "phone"), \
                            f"Excluded var '{val}' found in analysis_results.{field}"
                    elif isinstance(val, list):
                        for v in val:
                            assert v not in ("id_card", "phone"), \
                                f"Excluded var '{v}' found in analysis_results.{field}"


# ================================================================
# 7. End-to-end: generate_ai_report filters payload
# ================================================================


class TestEndToEndFilter:
    """generate_ai_report should produce filtered payload for LLM."""

    def test_generate_ai_report_imports_filter(self):
        """Verify filter is imported in ai_report_generator."""
        # Check that the filter import exists in the source
        import ast
        import inspect
        from src import ai_report_generator
        source = inspect.getsource(ai_report_generator.generate_ai_report)
        assert "filter_payload_for_ai" in source
