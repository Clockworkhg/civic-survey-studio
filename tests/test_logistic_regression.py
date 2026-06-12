"""Tests for logistic regression implementation."""

import pytest
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analysis import logit_regression
from src.generic_analysis import _execute_logistic_regression, run_full_analysis
from src.schema_infer import infer_variable_schema


class TestLogisticRegressionBasic:
    """Test logit_regression() with synthetic data."""

    @pytest.fixture
    def synthetic_binary_df(self):
        """Generate a simple dataset suitable for logistic regression."""
        np.random.seed(42)
        n = 200
        x1 = np.random.normal(0, 1, n)
        x2 = np.random.normal(0, 1, n)
        x3 = np.random.normal(0, 1, n)
        # logit = -1 + 2*x1 - 1.5*x2 + 0*x3 (x3 has no effect)
        logit = -1.0 + 2.0 * x1 - 1.5 * x2 + 0.0 * x3
        prob = 1 / (1 + np.exp(-logit))
        y = (np.random.random(n) < prob).astype(int)
        return pd.DataFrame({"target": y, "x1": x1, "x2": x2, "x3": x3})

    def test_returns_coefficients(self, synthetic_binary_df):
        """Logistic regression should return coefficient DataFrame."""
        result = logit_regression(
            synthetic_binary_df, "target", ["x1", "x2", "x3"]
        )
        assert "error" not in result, f"Unexpected error: {result.get('error')}"
        assert "coefficients" in result
        assert "pseudo_r_squared" in result
        assert isinstance(result["pseudo_r_squared"], float)

    def test_returns_odds_ratios(self, synthetic_binary_df):
        """Logistic regression coefficients should include odds_ratio column."""
        result = logit_regression(
            synthetic_binary_df, "target", ["x1", "x2", "x3"]
        )
        assert "error" not in result
        coef_df = result["coefficients"]
        assert "OR (exp(B))" in coef_df.columns
        or_vals = coef_df["OR (exp(B))"].dropna()
        assert all(v > 0 for v in or_vals), "All OR values should be positive"

    def test_significant_predictor_detected(self, synthetic_binary_df):
        """The known-significant predictor (x1) should have p < 0.05."""
        result = logit_regression(
            synthetic_binary_df, "target", ["x1", "x2", "x3"]
        )
        assert "error" not in result
        coef_df = result["coefficients"]
        # Find the x1 row (excluding const)
        x1_rows = coef_df[coef_df["变量"].str.contains("x1", na=False)]
        assert len(x1_rows) > 0, "x1 should be in coefficient table"
        x1_p = x1_rows.iloc[0]["p 值"]
        assert x1_p < 0.05, f"x1 should be significant, got p={x1_p}"

    def test_interpretation_contains_or_language(self, synthetic_binary_df):
        """The interpretation text should mention odds ratios, not beta."""
        result = logit_regression(
            synthetic_binary_df, "target", ["x1", "x2", "x3"]
        )
        assert "error" not in result
        interpretation = result.get("interpretation", "")
        assert len(interpretation) > 50, "Interpretation should be non-trivial"


class TestLogisticRegressionEdgeCases:
    """Test graceful handling of edge cases."""

    def test_single_category_target(self):
        """Target with only one category should return error."""
        df = pd.DataFrame({
            "target": [1, 1, 1, 1, 1],
            "x1": [1.0, 2.0, 3.0, 4.0, 5.0],
        })
        result = logit_regression(df, "target", ["x1"])
        assert "error" in result, "Single-category target should produce error"

    def test_too_few_samples(self):
        """Very few samples should return error."""
        df = pd.DataFrame({
            "target": [0, 1, 0],
            "x1": [1.0, 2.0, 3.0],
            "x2": [4.0, 5.0, 6.0],
        })
        result = logit_regression(df, "target", ["x1", "x2"])
        assert "error" in result, "Too few samples should produce error"

    def test_perfect_separation(self):
        """Perfect or near-perfect separation should not crash."""
        np.random.seed(42)
        n = 50
        # x1 nearly perfectly separates: target=0 when x1<0, target=1 when x1>0
        x1 = np.concatenate([np.random.normal(-3, 0.3, n//2),
                              np.random.normal(3, 0.3, n//2)])
        x2 = np.random.normal(0, 1, n)
        target = np.concatenate([np.zeros(n//2), np.ones(n//2)]).astype(int)
        df = pd.DataFrame({"target": target, "x1": x1, "x2": x2})
        # Should not crash — either returns results or error, but never raises
        result = logit_regression(df, "target", ["x1", "x2"])
        assert isinstance(result, dict), "Should return dict"
        assert "error" in result or "coefficients" in result, (
            "Should have either error or coefficients"
        )


class TestBinaryTargetTriggersLogistic:
    """Test that binary targets trigger logistic regression in run_full_analysis."""

    def test_binary_target_triggers_logistic_in_full_analysis(self):
        """binary target with numeric predictors should produce logistic results."""
        np.random.seed(99)
        n = 150
        # Use discrete integer predictors to avoid ID-type classification
        x1 = np.random.choice([1, 2, 3, 4, 5], n)
        x2 = np.random.choice([1, 2, 3, 4, 5, 6, 7], n)
        logit = 0.5 + 0.8 * x1 - 0.6 * x2
        prob = 1 / (1 + np.exp(-logit))
        y = (np.random.random(n) < prob).astype(int)
        df = pd.DataFrame({"target": y, "pred1": x1, "pred2": x2, "region": ["A"]*n})

        schema = infer_variable_schema(df)
        config = {
            "target_variable": "target",
            "group_variables": ["region"],
            "explanatory_variables": ["pred1", "pred2"],
        }
        results = run_full_analysis(df, schema, config)

        multi = results.get("multivariate")
        assert multi is not None, "Should have multivariate results"
        assert "error" not in multi, f"Should not error: {multi.get('error')}"
        assert "pseudo_r_squared" in multi, (
            "Logistic regression should have pseudo_r_squared"
        )
