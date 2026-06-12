"""Tests for src.ui.analysis_helpers — auto_suggest_config_from_dict."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pytest

from src.analysis_context import AnalysisContext
from src.ui.analysis_helpers import auto_suggest_config_from_dict


def _make_ctx(var_dict=None, columns=None, type_map=None, config=None):
    """Build a minimal AnalysisContext for testing."""
    ctx = AnalysisContext(
        mode="generic",
        variable_dict_map=var_dict or {},
        user_analysis_config=config or {},
    )
    ctx.type_map = type_map or {}
    # Override columns property by mocking what build_type_maps would set
    if columns:
        # We need to make ctx.columns return the columns list
        # Since columns is a property derived from df, we set a minimal df
        ctx.df = pd.DataFrame({c: [] for c in columns})
    return ctx


class TestAutoSuggestConfigFromDict:
    """Verify auto_suggest_config_from_dict behaviour."""

    def test_empty_var_dict_returns_safely(self):
        """No var_dict — no crash, no config changes."""
        ctx = _make_ctx(var_dict={}, columns=["a", "b"], config={})
        cfg_before = dict(ctx.user_analysis_config)
        auto_suggest_config_from_dict(ctx)
        assert ctx.user_analysis_config == cfg_before  # unchanged

    def test_no_detected_usage_returns_safely(self):
        """Entries without detected_usage should not trigger any fill."""
        ctx = _make_ctx(
            var_dict={"col_a": {"中文含义": "A", "变量用途": ""}},
            columns=["col_a"],
            type_map={"col_a": "numeric"},
            config={},
        )
        auto_suggest_config_from_dict(ctx)
        assert ctx.user_analysis_config.get("target_variable", "") == ""

    def test_suggests_target_from_detected_usage(self):
        """A column with detected_usage='target' should become target_variable."""
        ctx = _make_ctx(
            var_dict={"score": {"detected_usage": "target"}},
            columns=["score"],
            type_map={"score": "numeric"},
            config={},
        )
        auto_suggest_config_from_dict(ctx)
        assert ctx.user_analysis_config["target_variable"] == "score"

    def test_suggests_groups_from_detected_usage(self):
        """Columns with detected_usage='group' should become group_variables."""
        ctx = _make_ctx(
            var_dict={
                "region": {"detected_usage": "group"},
                "gender": {"detected_usage": "group"},
            },
            columns=["region", "gender", "score"],
            type_map={"region": "categorical", "gender": "categorical", "score": "numeric"},
            config={},
        )
        auto_suggest_config_from_dict(ctx)
        assert "region" in ctx.user_analysis_config["group_variables"]
        assert "gender" in ctx.user_analysis_config["group_variables"]

    def test_suggests_explanatory_from_detected_usage(self):
        """Columns with detected_usage='predictor' should become explanatory_variables."""
        ctx = _make_ctx(
            var_dict={
                "age": {"detected_usage": "predictor"},
                "income": {"detected_usage": "predictor"},
            },
            columns=["age", "income"],
            type_map={"age": "numeric", "income": "numeric"},
            config={},
        )
        auto_suggest_config_from_dict(ctx)
        assert "age" in ctx.user_analysis_config["explanatory_variables"]
        assert "income" in ctx.user_analysis_config["explanatory_variables"]

    def test_binary_variable_can_be_target(self):
        """A binary variable with detected_usage='target' should be included."""
        ctx = _make_ctx(
            var_dict={"converted": {"detected_usage": "target"}},
            columns=["converted"],
            type_map={"converted": "binary"},
            config={},
        )
        auto_suggest_config_from_dict(ctx)
        assert ctx.user_analysis_config["target_variable"] == "converted"

    def test_does_not_overwrite_existing_user_config(self):
        """If user already set target_variable, auto-suggest should NOT overwrite."""
        ctx = _make_ctx(
            var_dict={"other_score": {"detected_usage": "target"}},
            columns=["other_score", "my_score"],
            type_map={"other_score": "numeric", "my_score": "numeric"},
            config={"target_variable": "my_score"},
        )
        auto_suggest_config_from_dict(ctx)
        assert ctx.user_analysis_config["target_variable"] == "my_score"  # unchanged

    def test_group_filters_to_categorical_ordinal_only(self):
        """Only categorical/ordinal columns should be selected as groups."""
        ctx = _make_ctx(
            var_dict={
                "region": {"detected_usage": "group"},
                "score_num": {"detected_usage": "group"},  # numeric — should be filtered out
            },
            columns=["region", "score_num"],
            type_map={"region": "categorical", "score_num": "numeric"},
            config={},
        )
        auto_suggest_config_from_dict(ctx)
        assert "region" in ctx.user_analysis_config["group_variables"]
        assert "score_num" not in ctx.user_analysis_config["group_variables"]

    def test_explanatory_filters_to_numeric_ordinal_only(self):
        """Only numeric/ordinal columns should be selected as explanatory."""
        ctx = _make_ctx(
            var_dict={
                "age": {"detected_usage": "predictor"},
                "region": {"detected_usage": "predictor"},  # categorical — should be filtered out
            },
            columns=["age", "region"],
            type_map={"age": "numeric", "region": "categorical"},
            config={},
        )
        auto_suggest_config_from_dict(ctx)
        assert "age" in ctx.user_analysis_config["explanatory_variables"]
        assert "region" not in ctx.user_analysis_config["explanatory_variables"]

    def test_does_not_mutate_input_var_dict(self):
        """The var_dict passed in should not be modified."""
        var_dict = {"x": {"detected_usage": "target"}}
        var_dict_copy = dict(var_dict)
        ctx = _make_ctx(
            var_dict=var_dict,
            columns=["x"],
            type_map={"x": "numeric"},
            config={},
        )
        auto_suggest_config_from_dict(ctx)
        assert var_dict == var_dict_copy

    def test_group_limited_to_five(self):
        """At most 5 group variables should be selected."""
        var_dict = {}
        type_map = {}
        cols = []
        for i in range(10):
            c = f"group_{i}"
            cols.append(c)
            var_dict[c] = {"detected_usage": "group"}
            type_map[c] = "categorical"

        ctx = _make_ctx(
            var_dict=var_dict,
            columns=cols,
            type_map=type_map,
            config={},
        )
        auto_suggest_config_from_dict(ctx)
        assert len(ctx.user_analysis_config["group_variables"]) <= 5

    def test_explanatory_limited_to_ten(self):
        """At most 10 explanatory variables should be selected."""
        var_dict = {}
        type_map = {}
        cols = []
        for i in range(15):
            c = f"pred_{i}"
            cols.append(c)
            var_dict[c] = {"detected_usage": "predictor"}
            type_map[c] = "numeric"

        ctx = _make_ctx(
            var_dict=var_dict,
            columns=cols,
            type_map=type_map,
            config={},
        )
        auto_suggest_config_from_dict(ctx)
        assert len(ctx.user_analysis_config["explanatory_variables"]) <= 10


class TestAutoSuggestImport:
    """Verify the function is importable both directly and from the module."""

    def test_importable_from_analysis_helpers(self):
        from src.ui.analysis_helpers import auto_suggest_config_from_dict
        assert callable(auto_suggest_config_from_dict)
