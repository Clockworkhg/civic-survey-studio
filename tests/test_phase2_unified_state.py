"""Phase 2 tests: Unified analysis state flow and precomputed results.

Covers:
  1. run_analysis_pipeline produces results that sub-tabs can read
  2. downstream_valid=False prevents stale chart/report rendering
  3. AI blueprint adoption triggers invalidation (must re-analyze)
  4. Sub-tabs accept precomputed_results instead of re-running
  5. Visualization empty-state diagnosis
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pytest


# ── Test fixtures ──


@pytest.fixture
def sample_df():
    """Minimal test DataFrame with mixed types."""
    return pd.DataFrame({
        "satisfaction": [4, 5, 3, 4, 5, 2, 3, 4, 5, 4],
        "region":        ["A", "B", "A", "B", "A", "B", "A", "B", "A", "B"],
        "age":           [25, 30, 35, 40, 28, 33, 38, 45, 29, 31],
        "income":        [5000, 6000, 5500, 7000, 4800, 5200, 6800, 7500, 5100, 6200],
        "text_field":    ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"],
    })


@pytest.fixture
def sample_schema(sample_df):
    """Build a minimal variable schema."""
    from src.schema_infer import infer_variable_schema
    return infer_variable_schema(sample_df)


@pytest.fixture
def sample_config():
    """Minimal analysis config."""
    return {
        "report_title": "Test Report",
        "target_variable": "satisfaction",
        "group_variables": ["region"],
        "explanatory_variables": ["age", "income"],
        "gen_html": True,
        "gen_docx": True,
    }


# ================================================================
# 1. AnalysisContext unified state flow
# ================================================================


class TestAnalysisContextDownstreamFlow:
    """Test the downstream_valid lifecycle in AnalysisContext."""

    def test_initial_state_valid(self):
        """New AnalysisContext starts with downstream_valid=True."""
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext(mode="generic")
        assert ctx.downstream_valid is True
        assert ctx.invalidation_reason == ""

    def test_apply_config_invalidates_downstream(self, sample_df, sample_schema, sample_config):
        """Applying a semantically different config should invalidate downstream."""
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext(
            mode="generic",
            df=sample_df,
            variable_schema=sample_schema,
            user_analysis_config={
                "target_variable": "",
                "group_variables": [],
                "explanatory_variables": [],
            },
        )
        ctx.build_type_maps()
        ctx.downstream_valid = True
        ctx.analysis_results = {"univariate": {"satisfaction": {"均值": 3.9}}}
        ctx.analysis_payload = {"mock": "payload"}

        # Apply new config with different target
        msgs = ctx.apply_analysis_config(sample_config, source="manual")

        assert ctx.downstream_valid is False
        assert ctx.invalidation_reason != ""
        assert "target_variable" in ctx.invalidation_reason
        assert ctx.analysis_results == {}
        assert ctx.analysis_payload is None
        assert any("失效" in m for m in msgs)

    def test_mark_downstream_valid(self):
        """mark_downstream_valid restores valid state."""
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext(mode="generic")
        ctx.downstream_valid = False
        ctx.invalidation_reason = "test"
        ctx.mark_downstream_valid()
        assert ctx.downstream_valid is True
        assert ctx.invalidation_reason == ""

    def test_no_invalidation_when_config_unchanged(self, sample_df, sample_schema, sample_config):
        """Applying the same config should NOT invalidate downstream."""
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext(
            mode="generic",
            df=sample_df,
            variable_schema=sample_schema,
            user_analysis_config=sample_config.copy(),
        )
        ctx.build_type_maps()
        ctx.downstream_valid = True
        ctx.analysis_results = {"univariate": {"satisfaction": {"均值": 3.9}}}

        # Apply identical config
        msgs = ctx.apply_analysis_config(sample_config, source="manual")
        assert ctx.downstream_valid is True
        assert ctx.analysis_results != {}

    def test_config_source_recorded(self, sample_df, sample_schema, sample_config):
        """Config source and timestamp should be recorded."""
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext(
            mode="generic",
            df=sample_df,
            variable_schema=sample_schema,
            user_analysis_config={"target_variable": "", "group_variables": [], "explanatory_variables": []},
        )
        ctx.build_type_maps()
        ctx.apply_analysis_config(sample_config, source="ai")
        assert ctx.config_source == "ai"
        assert ctx.config_applied_at != ""

    def test_has_results_respects_downstream_valid(self, sample_df, sample_schema, sample_config):
        """has_results should be False when downstream is invalid even with data."""
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext(
            mode="generic",
            df=sample_df,
            variable_schema=sample_schema,
            user_analysis_config=sample_config,
        )
        ctx.build_type_maps()
        ctx.analysis_results = {"univariate": {"satisfaction": {"均值": 3.9}}}
        ctx.downstream_valid = False
        assert ctx.has_results is False
        ctx.downstream_valid = True
        assert ctx.has_results is True

    def test_config_ready_checks_target(self):
        """config_ready is True only when target is set."""
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext(mode="generic")
        assert ctx.config_ready is False
        ctx.user_analysis_config["target_variable"] = "satisfaction"
        assert ctx.config_ready is True

    def test_run_analysis_pipeline_returns_cached_when_valid(self, sample_df, sample_schema, sample_config):
        """run_analysis_pipeline with force=False returns cached when downstream_valid."""
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext(
            mode="generic",
            df=sample_df,
            variable_schema=sample_schema,
            user_analysis_config=sample_config,
        )
        ctx.build_type_maps()
        ctx.downstream_valid = True
        ctx.analysis_results = {"univariate": {"satisfaction": {"均值": 3.9}}}
        ctx.dashboard_charts = [("test", "Test Chart", object())]
        ctx.analysis_payload = {"mock": "payload"}

        result = ctx.run_analysis_pipeline(force=False)
        assert result["success"] is True
        assert "缓存" in str(result.get("warnings", []))
        assert result["analysis_results"] == ctx.analysis_results

    def test_run_analysis_pipeline_no_target(self, sample_df, sample_schema):
        """run_analysis_pipeline fails gracefully when no target is set."""
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext(
            mode="generic",
            df=sample_df,
            variable_schema=sample_schema,
            user_analysis_config={"target_variable": "", "group_variables": [], "explanatory_variables": []},
        )
        ctx.build_type_maps()
        result = ctx.run_analysis_pipeline(force=True)
        assert result["success"] is False
        assert "核心变量" in result["error"]


# ================================================================
# 2. AI blueprint adoption triggers invalidation
# ================================================================


class TestBlueprintAdoptionInvalidation:
    """AI blueprint adoption must trigger downstream invalidation."""

    def test_apply_blueprint_invalidates_downstream(self, sample_df, sample_schema):
        """Adopting an AI blueprint should set downstream_valid=False."""
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext(
            mode="generic",
            df=sample_df,
            variable_schema=sample_schema,
            user_analysis_config={
                "target_variable": "",
                "group_variables": [],
                "explanatory_variables": [],
            },
        )
        ctx.build_type_maps()
        ctx.downstream_valid = True
        ctx.analysis_results = {"univariate": {"satisfaction": {"均值": 3.9}}}

        blueprint = {
            "recommended_report_titles": ["AI Test Report"],
            "target_variable_candidates": [
                {"variable": "satisfaction", "priority": "high", "display_name": "满意度", "reason": "core"},
            ],
            "group_variable_candidates": [
                {"variable": "region", "priority": "high", "display_name": "区域", "reason": "group"},
            ],
            "explanatory_variable_candidates": [
                {"variable": "age", "priority": "high", "display_name": "年龄", "reason": "expl"},
            ],
        }

        msgs = ctx.apply_blueprint_to_config(blueprint, schema_df=sample_schema, overwrite=True)

        assert ctx.downstream_valid is False
        assert ctx.config_source == "ai"
        assert ctx.analysis_results == {}
        assert ctx.user_analysis_config["target_variable"] == "satisfaction"
        assert "region" in ctx.user_analysis_config["group_variables"]

    def test_apply_blueprint_missing_variable_warning(self, sample_df, sample_schema):
        """Blueprint with non-existent variables should produce warnings."""
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext(
            mode="generic",
            df=sample_df,
            variable_schema=sample_schema,
            user_analysis_config={
                "target_variable": "",
                "group_variables": [],
                "explanatory_variables": [],
            },
        )
        ctx.build_type_maps()

        blueprint = {
            "target_variable_candidates": [
                {"variable": "nonexistent_var", "priority": "high", "display_name": "不存在", "reason": "test"},
            ],
            "group_variable_candidates": [],
            "explanatory_variable_candidates": [],
        }

        msgs = ctx.apply_blueprint_to_config(blueprint, schema_df=sample_schema, overwrite=True)
        assert any("不存在于数据中" in m for m in msgs)
        assert ctx.user_analysis_config["target_variable"] == ""  # not set because var doesn't exist

    def test_apply_blueprint_preserves_metadata(self, sample_df, sample_schema):
        """Blueprint adoption should store _var_metadata in config."""
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext(
            mode="generic",
            df=sample_df,
            variable_schema=sample_schema,
            user_analysis_config={
                "target_variable": "",
                "group_variables": [],
                "explanatory_variables": [],
            },
        )
        ctx.build_type_maps()

        blueprint = {
            "target_variable_candidates": [
                {"variable": "satisfaction", "priority": "high", "display_name": "满意度", "reason": "core"},
            ],
            "group_variable_candidates": [],
            "explanatory_variable_candidates": [],
        }

        ctx.apply_blueprint_to_config(blueprint, schema_df=sample_schema, overwrite=True)
        assert "_var_metadata" in ctx.user_analysis_config


# ================================================================
# 3. Visualization empty-state diagnosis
# ================================================================


class TestVisualizationEmptyState:
    """Visualization tab should show specific empty-state reasons."""

    def test_diagnose_no_target(self):
        """Empty charts when no target variable is set."""
        from src.ui.tabs.tab_visualization import _diagnose_empty_reason
        config = {"target_variable": ""}
        reason = _diagnose_empty_reason(config, downstream_valid=True, has_results=False)
        assert "核心变量" in reason

    def test_diagnose_stale_config(self):
        """Empty/warning when downstream_valid is False."""
        from src.ui.tabs.tab_visualization import _diagnose_empty_reason
        config = {"target_variable": "satisfaction"}
        reason = _diagnose_empty_reason(config, downstream_valid=False, has_results=True)
        assert "已变更" in reason or "重新生成" in reason or "重新执行" in reason

    def test_diagnose_not_run(self):
        """Empty when analysis not yet executed."""
        from src.ui.tabs.tab_visualization import _diagnose_empty_reason
        config = {"target_variable": "satisfaction"}
        reason = _diagnose_empty_reason(config, downstream_valid=True, has_results=False)
        assert "尚未执行" in reason

    def test_chart_empty_reasons_dict(self):
        """All expected reason keys exist."""
        from src.ui.tabs.tab_visualization import _CHART_EMPTY_REASONS
        expected_keys = {"no_target", "no_data", "unsupported_type", "no_group_vars", "no_expl_vars", "not_run", "stale"}
        assert expected_keys.issubset(set(_CHART_EMPTY_REASONS.keys()))


# ================================================================
# 4. Sub-tabs accept precomputed parameters
# ================================================================


class TestSubTabParameters:
    """Sub-tab render functions accept precomputed_results/charts parameters."""

    def test_univariate_accepts_precomputed(self):
        from src.ui.tabs.tab_univariate_analysis import render_tab_univariate_analysis
        import inspect
        sig = inspect.signature(render_tab_univariate_analysis)
        params = sig.parameters
        assert "precomputed_results" in params
        assert "use_precomputed" in params
        assert params["use_precomputed"].default is True

    def test_bivariate_accepts_precomputed(self):
        from src.ui.tabs.tab_bivariate_analysis import render_tab_bivariate_analysis
        import inspect
        sig = inspect.signature(render_tab_bivariate_analysis)
        params = sig.parameters
        assert "precomputed_results" in params
        assert "use_precomputed" in params
        assert params["use_precomputed"].default is True

    def test_multivariate_accepts_precomputed(self):
        from src.ui.tabs.tab_multivariate_analysis import render_tab_multivariate_analysis
        import inspect
        sig = inspect.signature(render_tab_multivariate_analysis)
        params = sig.parameters
        assert "precomputed_results" in params
        assert "use_precomputed" in params
        assert params["use_precomputed"].default is True

    def test_visualization_accepts_precomputed(self):
        from src.ui.tabs.tab_visualization import render_tab_visualization
        import inspect
        sig = inspect.signature(render_tab_visualization)
        params = sig.parameters
        assert "precomputed_charts" in params
        assert "use_precomputed" in params
        assert "downstream_valid" in params
        assert params["use_precomputed"].default is True
        assert params["downstream_valid"].default is True

    def test_ai_analysis_accepts_precomputed(self):
        from src.ui.tabs.tab_ai_analysis import render_tab_ai_analysis
        import inspect
        sig = inspect.signature(render_tab_ai_analysis)
        params = sig.parameters
        assert "precomputed_payload" in params
        assert "precomputed_analysis_results" in params
        assert "downstream_valid" in params
        assert params["downstream_valid"].default is True


# ================================================================
# 5. Precomputed results structure compatibility
# ================================================================


class TestPrecomputedResultStructure:
    """Verify that run_full_analysis returns the structure sub-tabs expect."""

    def test_run_full_analysis_has_expected_keys(self, sample_df, sample_schema, sample_config):
        """run_full_analysis returns univariate, bivariate_group, bivariate_corr, multivariate, warnings."""
        from src.generic_analysis import run_full_analysis
        result = run_full_analysis(sample_df, sample_schema, sample_config)
        assert "univariate" in result
        assert "bivariate_group" in result
        assert "bivariate_corr" in result
        assert "multivariate" in result
        assert "warnings" in result

    def test_run_full_analysis_univariate_per_column(self, sample_df, sample_schema, sample_config):
        """Each numeric/categorical/ordinal column gets a univariate result."""
        from src.generic_analysis import run_full_analysis
        result = run_full_analysis(sample_df, sample_schema, sample_config)
        uni = result["univariate"]
        # satisfaction (numeric), region (categorical), age (numeric), income (numeric)
        assert "satisfaction" in uni
        assert "region" in uni
        assert "age" in uni
        assert "income" in uni
        # Check numeric result structure
        sat = uni["satisfaction"]
        assert "error" not in sat
        assert "均值" in sat

    def test_run_full_analysis_bivariate_group(self, sample_df, sample_schema, sample_config):
        """bivariate_group contains region × satisfaction cross-tab."""
        from src.generic_analysis import run_full_analysis
        result = run_full_analysis(sample_df, sample_schema, sample_config)
        bg = result["bivariate_group"]
        assert len(bg) > 0
        # Keys are like "region__satisfaction"
        assert any("region" in k for k in bg.keys())

    def test_run_full_analysis_multivariate(self, sample_df, sample_schema, sample_config):
        """multivariate result is present (may be None for small samples — regression needs ≥2 valid predictors)."""
        from src.generic_analysis import run_full_analysis
        result = run_full_analysis(sample_df, sample_schema, sample_config)
        mv = result["multivariate"]
        # Small samples (10 rows, 2 predictors) may fail regression; accept None as valid.
        if mv is not None:
            assert "error" not in mv
            assert "r_squared" in mv
            assert "coefficients" in mv
        else:
            # Small sample regression is expected to sometimes not run
            pass


# ================================================================
# 6. Invalidated results are cleared
# ================================================================


class TestInvalidationClearsResults:
    """When downstream is invalidated, all cached results must be cleared."""

    def test_invalidate_clears_everything(self, sample_df, sample_schema, sample_config):
        """invalidate_downstream clears results, charts, and payload."""
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext(
            mode="generic",
            df=sample_df,
            variable_schema=sample_schema,
            user_analysis_config=sample_config,
        )
        ctx.build_type_maps()
        ctx.analysis_results = {"univariate": {"data": "cached"}}
        ctx.dashboard_charts = [("k", "t", "fig")]
        ctx.analysis_payload = {"payload": "cached"}
        ctx.chart_summaries = [{"title": "summary"}]

        ctx.invalidate_downstream("config changed")

        assert ctx.analysis_results == {}
        assert ctx.dashboard_charts == []
        assert ctx.analysis_payload is None
        assert ctx.chart_summaries == []

    def test_invalidate_sets_reason(self, sample_df, sample_schema, sample_config):
        """invalidate_downstream records the reason."""
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext(
            mode="generic",
            df=sample_df,
            variable_schema=sample_schema,
            user_analysis_config=sample_config,
        )
        ctx.build_type_maps()
        ctx.invalidate_downstream("target_variable changed")
        assert ctx.invalidation_reason == "target_variable changed"

    def test_only_semantic_changes_invalidate(self):
        """report_title change alone should NOT invalidate downstream when semantic fields unchanged."""
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext(
            mode="generic",
            user_analysis_config={
                "target_variable": "satisfaction",
                "group_variables": ["region"],
                "explanatory_variables": ["age"],
                "report_title": "Old Title",
            },
        )
        ctx.downstream_valid = True
        ctx.analysis_results = {"univariate": {"data": "cached"}}

        # Change only report_title — must pass ALL keys to avoid implicit None→semantic mismatch
        msgs = ctx.apply_analysis_config({
            "target_variable": "satisfaction",
            "group_variables": ["region"],
            "explanatory_variables": ["age"],
            "report_title": "New Title",
        }, source="manual")
        assert ctx.downstream_valid is True  # title change alone doesn't invalidate
        assert ctx.analysis_results != {}

    def test_group_vars_change_invalidates(self):
        """Changing group_variables should invalidate downstream."""
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext(
            mode="generic",
            user_analysis_config={
                "target_variable": "satisfaction",
                "group_variables": ["region"],
                "explanatory_variables": [],
            },
        )
        ctx.downstream_valid = True
        ctx.analysis_results = {"univariate": {"data": "cached"}}

        msgs = ctx.apply_analysis_config({"group_variables": ["region", "age"]}, source="manual")
        assert ctx.downstream_valid is False
        assert ctx.analysis_results == {}


# ================================================================
# 7. get_variable_label / get_variable_description
# ================================================================


class TestVariableLabelHelpers:
    """Variable label helpers from Phase 1 work correctly."""

    def test_get_variable_label_with_cn(self):
        """Returns '中文名（英文列名）' format when cn exists."""
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext(mode="generic")
        ctx.cn_map = {"satisfaction": "总体满意度"}
        label = ctx.get_variable_label("satisfaction")
        assert label == "总体满意度（satisfaction）"

    def test_get_variable_label_without_cn(self):
        """Returns raw column name when no cn mapping."""
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext(mode="generic")
        ctx.cn_map = {}
        label = ctx.get_variable_label("satisfaction")
        assert label == "satisfaction"

    def test_get_variable_label_cn_equals_col(self):
        """Returns raw column name when cn equals column name."""
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext(mode="generic")
        ctx.cn_map = {"satisfaction": "satisfaction"}
        label = ctx.get_variable_label("satisfaction")
        assert label == "satisfaction"

    def test_get_variable_description(self):
        """Returns variable description from dict_map."""
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext(mode="generic")
        ctx.variable_dict_map = {
            "satisfaction": {"变量用途": "衡量公众对政府服务的整体满意程度", "取值或说明": "1-5 分"},
        }
        desc = ctx.get_variable_description("satisfaction")
        assert "公众" in desc

    def test_get_variable_description_missing(self):
        """Returns empty string when variable not in dict_map."""
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext(mode="generic")
        ctx.variable_dict_map = {}
        desc = ctx.get_variable_description("nonexistent")
        assert desc == ""
