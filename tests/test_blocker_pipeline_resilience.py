"""Release blocker tests: pipeline status resilience and downstream_valid existence.

v0.1.0 Phase 5 Blocker Fix:
  1. AnalysisContext 默认实例必须包含 downstream_valid
  2. render_pipeline_status 在缺少字段时不报错
  3. _resolve_pipeline_statuses 在各种边界条件下不报错
  4. 加载示例数据后、无数据、采用 AI 方案后都不报错
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import types
import pytest
from unittest.mock import patch


# ================================================================
# 1. AnalysisContext 默认字段
# ================================================================


class TestAnalysisContextDefaults:
    """AnalysisContext must have downstream_valid and other key fields."""

    def test_default_has_downstream_valid(self):
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext()
        assert hasattr(ctx, "downstream_valid")
        assert ctx.downstream_valid is True

    def test_default_has_analysis_results(self):
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext()
        assert hasattr(ctx, "analysis_results")
        assert ctx.analysis_results == {}

    def test_default_has_dashboard_charts(self):
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext()
        assert hasattr(ctx, "dashboard_charts")
        assert ctx.dashboard_charts == []

    def test_default_has_analysis_payload(self):
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext()
        assert hasattr(ctx, "analysis_payload")
        assert ctx.analysis_payload is None

    def test_default_has_config_source(self):
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext()
        assert hasattr(ctx, "config_source")
        assert ctx.config_source == ""

    def test_default_has_warnings(self):
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext()
        assert hasattr(ctx, "warnings")
        assert ctx.warnings == []

    def test_default_has_invalidation_reason(self):
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext()
        assert hasattr(ctx, "invalidation_reason")
        assert ctx.invalidation_reason == ""

    def test_invalidate_sets_downstream_valid_false(self):
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext()
        ctx.invalidate_downstream("test reason")
        assert ctx.downstream_valid is False
        assert ctx.invalidation_reason == "test reason"

    def test_mark_valid_sets_downstream_valid_true(self):
        from src.analysis_context import AnalysisContext
        ctx = AnalysisContext()
        ctx.downstream_valid = False
        ctx.mark_downstream_valid()
        assert ctx.downstream_valid is True


# ================================================================
# 2. render_pipeline_status robustness
# ================================================================


class TestPipelineStatusRobustness:
    """render_pipeline_status should never crash, even with missing/incomplete ctx."""

    def test_none_ctx_no_crash(self):
        """None ctx → no crash."""
        from src.ui.components import render_pipeline_status
        try:
            render_pipeline_status(None)
        except Exception as e:
            pytest.fail(f"render_pipeline_status(None) raised: {e}")

    def test_empty_simplenamespace_no_crash(self):
        """SimpleNamespace with no fields → no crash."""
        from types import SimpleNamespace
        from src.ui.components import render_pipeline_status
        ctx = SimpleNamespace()
        try:
            render_pipeline_status(ctx)
        except Exception as e:
            pytest.fail(f"render_pipeline_status(empty ns) raised: {e}")

    def test_simplenamespace_missing_downstream_valid(self):
        """SimpleNamespace with df but no downstream_valid → no crash."""
        from types import SimpleNamespace
        from src.ui.components import _resolve_pipeline_statuses, DEFAULT_PIPELINE_STEPS
        import pandas as pd
        ctx = SimpleNamespace(
            df=pd.DataFrame({"a": [1, 2, 3]}),
            variable_schema=pd.DataFrame({"column": ["a"], "inferred_type": ["numeric"]}),
            user_analysis_config={"target_variable": "a"},
            # NO downstream_valid
        )
        try:
            statuses = _resolve_pipeline_statuses(ctx, DEFAULT_PIPELINE_STEPS)
            assert isinstance(statuses, dict)
            assert statuses["data"] == "done"
        except Exception as e:
            pytest.fail(f"Missing downstream_valid raised: {e}")

    def test_simplenamespace_missing_analysis_results(self):
        """SimpleNamespace without analysis_results → no crash."""
        from types import SimpleNamespace
        from src.ui.components import _resolve_pipeline_statuses, DEFAULT_PIPELINE_STEPS
        import pandas as pd
        ctx = SimpleNamespace(
            df=pd.DataFrame({"a": [1, 2, 3]}),
            variable_schema=pd.DataFrame({"column": ["a"], "inferred_type": ["numeric"]}),
            user_analysis_config={"target_variable": "a"},
            downstream_valid=True,
            # NO analysis_results
        )
        try:
            statuses = _resolve_pipeline_statuses(ctx, DEFAULT_PIPELINE_STEPS)
            assert isinstance(statuses, dict)
        except Exception as e:
            pytest.fail(f"Missing analysis_results raised: {e}")

    def test_simplenamespace_missing_df(self):
        """SimpleNamespace without df → no crash."""
        from types import SimpleNamespace
        from src.ui.components import _resolve_pipeline_statuses, DEFAULT_PIPELINE_STEPS
        ctx = SimpleNamespace()
        try:
            statuses = _resolve_pipeline_statuses(ctx, DEFAULT_PIPELINE_STEPS)
            assert isinstance(statuses, dict)
            assert statuses["data"] == "pending"
        except Exception as e:
            pytest.fail(f"Missing df raised: {e}")

    def test_data_loaded_no_config(self):
        """Data loaded but no config → pipeline shows correct pending states."""
        from types import SimpleNamespace
        from src.ui.components import _resolve_pipeline_statuses, DEFAULT_PIPELINE_STEPS
        import pandas as pd
        ctx = SimpleNamespace(
            df=pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}),
            variable_schema=pd.DataFrame({
                "column": ["x", "y"],
                "inferred_type": ["numeric", "numeric"],
            }),
            user_analysis_config={"target_variable": "", "group_variables": [], "explanatory_variables": []},
            downstream_valid=True,
            analysis_results={},
            target="",
        )
        statuses = _resolve_pipeline_statuses(ctx, DEFAULT_PIPELINE_STEPS)
        assert statuses["data"] == "done"
        assert statuses["vars"] == "done"
        assert statuses["config"] == "current"  # data loaded, can configure
        assert statuses["analysis"] == "pending"
        assert statuses["report"] == "pending"

    def test_config_set_no_analysis(self):
        """Config set but no analysis executed → analysis = current, report = pending."""
        from types import SimpleNamespace
        from src.ui.components import _resolve_pipeline_statuses, DEFAULT_PIPELINE_STEPS
        import pandas as pd
        ctx = SimpleNamespace(
            df=pd.DataFrame({"a": [1, 2, 3]}),
            variable_schema=pd.DataFrame({"column": ["a"], "inferred_type": ["numeric"]}),
            user_analysis_config={"target_variable": "a"},
            downstream_valid=True,
            analysis_results={},
            target="a",
        )
        statuses = _resolve_pipeline_statuses(ctx, DEFAULT_PIPELINE_STEPS)
        assert statuses["config"] == "done"
        assert statuses["analysis"] == "current"

    def test_analysis_done_downstream_valid(self):
        """Analysis completed and downstream_valid=True → analysis = done."""
        from types import SimpleNamespace
        from src.ui.components import _resolve_pipeline_statuses, DEFAULT_PIPELINE_STEPS
        import pandas as pd
        ctx = SimpleNamespace(
            df=pd.DataFrame({"a": [1, 2, 3]}),
            variable_schema=pd.DataFrame({"column": ["a"], "inferred_type": ["numeric"]}),
            user_analysis_config={"target_variable": "a"},
            downstream_valid=True,
            analysis_results={"univariate": {"a": {}}},
            target="a",
        )
        statuses = _resolve_pipeline_statuses(ctx, DEFAULT_PIPELINE_STEPS)
        assert statuses["analysis"] == "done"

    def test_analysis_done_downstream_invalid(self):
        """Analysis exists but downstream_valid=False → analysis = warning."""
        from types import SimpleNamespace
        from src.ui.components import _resolve_pipeline_statuses, DEFAULT_PIPELINE_STEPS
        import pandas as pd
        ctx = SimpleNamespace(
            df=pd.DataFrame({"a": [1, 2, 3]}),
            variable_schema=pd.DataFrame({"column": ["a"], "inferred_type": ["numeric"]}),
            user_analysis_config={"target_variable": "a"},
            downstream_valid=False,
            analysis_results={"univariate": {"a": {}}},
            target="a",
        )
        statuses = _resolve_pipeline_statuses(ctx, DEFAULT_PIPELINE_STEPS)
        assert statuses["analysis"] == "warning"

    def test_with_payload_report_ready(self):
        """With analysis_payload → report = done."""
        from types import SimpleNamespace
        from src.ui.components import _resolve_pipeline_statuses, DEFAULT_PIPELINE_STEPS
        import pandas as pd
        ctx = SimpleNamespace(
            df=pd.DataFrame({"a": [1, 2, 3]}),
            variable_schema=pd.DataFrame({"column": ["a"], "inferred_type": ["numeric"]}),
            user_analysis_config={"target_variable": "a"},
            downstream_valid=True,
            analysis_results={"univariate": {"a": {}}},
            analysis_payload={"variables": {"a": {}}},
            target="a",
        )
        statuses = _resolve_pipeline_statuses(ctx, DEFAULT_PIPELINE_STEPS)
        assert statuses["report"] == "done"


# ================================================================
# 3. session_state downstream sync in invalidate_downstream
# ================================================================


class TestDownstreamSessionStateSync:
    """invalidate_downstream should sync to st.session_state."""

    def test_invalidate_writes_session_state(self):
        """After invalidate, session_state keys should be set."""
        import streamlit as st
        from src.analysis_context import AnalysisContext

        # Ensure session_state keys exist
        from src.ui.state import init_session_state
        init_session_state()

        ctx = AnalysisContext()
        ctx.invalidate_downstream("config changed")

        assert st.session_state.get("_downstream_valid") is False
        assert st.session_state["_invalidation_reason"] == "config changed"
        assert st.session_state.get("_analysis_results") == {}
        assert st.session_state.get("_dashboard_charts") == []

    def test_mark_valid_writes_session_state(self):
        """After mark_downstream_valid, session_state should be true."""
        import streamlit as st
        from src.analysis_context import AnalysisContext
        from src.ui.state import init_session_state
        init_session_state()

        ctx = AnalysisContext()
        ctx.downstream_valid = False
        ctx.mark_downstream_valid()

        assert st.session_state.get("_downstream_valid") is True
        assert st.session_state["_invalidation_reason"] == ""


# ================================================================
# 4. apply_blueprint invalidates downstream
# ================================================================


class TestBlueprintDownstreamInvalidation:
    """Adopting AI blueprint should mark downstream as invalid."""

    @pytest.fixture
    def sample_ctx(self):
        import pandas as pd
        from src.analysis_context import AnalysisContext
        from src.schema_infer import infer_variable_schema

        df = pd.DataFrame({
            "satisfaction": [4, 5, 3, 4, 5],
            "region": ["A", "B", "A", "B", "A"],
            "age": [25, 30, 35, 40, 28],
        })
        schema = infer_variable_schema(df)
        ctx = AnalysisContext(
            mode="generic",
            df=df,
            variable_schema=schema,
        )
        ctx.build_type_maps()
        return ctx

    @pytest.fixture
    def sample_blueprint(self):
        return {
            "recommended_report_titles": ["满意度分析报告"],
            "target_variable_candidates": [
                {"variable": "satisfaction", "priority": "high", "display_name": "满意度", "reason": ""}
            ],
            "group_variable_candidates": [
                {"variable": "region", "priority": "high", "display_name": "区域", "reason": ""}
            ],
            "explanatory_variable_candidates": [
                {"variable": "age", "priority": "high", "display_name": "年龄", "reason": ""}
            ],
            "dataset_understanding": {
                "possible_research_subject": "满意度影响因素",
            },
        }

    def test_apply_blueprint_invalidates_downstream(self, sample_ctx, sample_blueprint):
        """After apply_blueprint_to_config, downstream_valid should be False."""
        assert sample_ctx.downstream_valid is True  # Initial state
        sample_ctx.apply_blueprint_to_config(sample_blueprint, schema_df=sample_ctx.variable_schema)
        assert sample_ctx.downstream_valid is False
        assert sample_ctx.config_source == "ai"

    def test_apply_blueprint_sets_config(self, sample_ctx, sample_blueprint):
        """After apply_blueprint_to_config, config should be populated."""
        sample_ctx.apply_blueprint_to_config(sample_blueprint, schema_df=sample_ctx.variable_schema)
        assert sample_ctx.user_analysis_config["target_variable"] == "satisfaction"
        assert "region" in sample_ctx.user_analysis_config["group_variables"]


# ================================================================
# 5. app.py render_pipeline_status doesn't crash (smoke via components)
# ================================================================


class TestAppPipelineSmoke:
    """Smoke-level: verify the pipeline status resolves for realistic states."""

    def test_example_data_state_resolves(self):
        """State like after loading example data but before analysis → no crash."""
        from types import SimpleNamespace
        from src.ui.components import _resolve_pipeline_statuses, DEFAULT_PIPELINE_STEPS
        import pandas as pd

        # Simulate gen_ctx after loading example data
        ctx = SimpleNamespace(
            mode="generic",
            df=pd.DataFrame({"satisfaction": [4, 5, 3], "region": ["A", "B", "A"]}),
            variable_schema=pd.DataFrame({
                "column": ["satisfaction", "region"],
                "inferred_type": ["numeric", "categorical"],
                "display_name": ["满意度", "区域"],
            }),
            user_analysis_config={
                "target_variable": "",
                "group_variables": [],
                "explanatory_variables": [],
            },
            downstream_valid=True,
            analysis_results={},
            dashboard_charts=[],
            analysis_payload=None,
            config_source="none",
            target="",
        )
        try:
            statuses = _resolve_pipeline_statuses(ctx, DEFAULT_PIPELINE_STEPS)
            assert statuses["data"] == "done"
            assert statuses["config"] == "current"
            assert statuses["analysis"] == "pending"
        except Exception as e:
            pytest.fail(f"Example-data state raised: {e}")

    def test_after_ai_blueprint_adoption_resolves(self):
        """State after adopting AI blueprint → downstream_valid=False, no crash."""
        from types import SimpleNamespace
        from src.ui.components import _resolve_pipeline_statuses, DEFAULT_PIPELINE_STEPS
        import pandas as pd

        ctx = SimpleNamespace(
            df=pd.DataFrame({"satisfaction": [4, 5, 3], "region": ["A", "B", "A"], "age": [25, 30, 35]}),
            variable_schema=pd.DataFrame({
                "column": ["satisfaction", "region", "age"],
                "inferred_type": ["numeric", "categorical", "numeric"],
            }),
            user_analysis_config={
                "target_variable": "satisfaction",
                "group_variables": ["region"],
                "explanatory_variables": ["age"],
            },
            downstream_valid=False,
            analysis_results={},
            dashboard_charts=[],
            analysis_payload=None,
            config_source="ai",
            target="satisfaction",
        )
        try:
            statuses = _resolve_pipeline_statuses(ctx, DEFAULT_PIPELINE_STEPS)
            assert statuses["config"] == "done"
            assert statuses["analysis"] == "current"  # config set, no analysis yet
        except Exception as e:
            pytest.fail(f"AI blueprint state raised: {e}")

    def test_after_analysis_executed_resolves(self):
        """State after executing analysis → all done."""
        from types import SimpleNamespace
        from src.ui.components import _resolve_pipeline_statuses, DEFAULT_PIPELINE_STEPS
        import pandas as pd

        ctx = SimpleNamespace(
            df=pd.DataFrame({"satisfaction": [4, 5, 3], "region": ["A", "B", "A"]}),
            variable_schema=pd.DataFrame({
                "column": ["satisfaction", "region"],
                "inferred_type": ["numeric", "categorical"],
            }),
            user_analysis_config={
                "target_variable": "satisfaction",
                "group_variables": ["region"],
                "explanatory_variables": [],
            },
            downstream_valid=True,
            analysis_results={"univariate": {"satisfaction": {}}, "bivariate_group": []},
            dashboard_charts=[("bar", "满意度分布", None)],
            analysis_payload={"variables": {"satisfaction": {}}},
            config_source="manual",
            target="satisfaction",
        )
        try:
            statuses = _resolve_pipeline_statuses(ctx, DEFAULT_PIPELINE_STEPS)
            assert statuses["data"] == "done"
            assert statuses["config"] == "done"
            assert statuses["analysis"] == "done"
            assert statuses["report"] == "done"
        except Exception as e:
            pytest.fail(f"After-analysis state raised: {e}")

    def test_bare_minimum_created_ctx(self):
        """Bare-minimum AnalysisContext() → no crash."""
        from src.analysis_context import AnalysisContext
        from src.ui.components import _resolve_pipeline_statuses, DEFAULT_PIPELINE_STEPS

        ctx = AnalysisContext()  # All defaults
        try:
            statuses = _resolve_pipeline_statuses(ctx, DEFAULT_PIPELINE_STEPS)
            assert statuses["data"] == "pending"
            assert statuses["vars"] == "pending"
        except Exception as e:
            pytest.fail(f"Bare-minimum ctx raised: {e}")
