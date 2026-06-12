"""Tests for binary variable type inference."""

import pytest
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.schema_infer import infer_variable_schema, _detect_binary_pattern


class TestBinaryDetection:
    """Test _detect_binary_pattern function."""

    def test_numeric_01_is_binary(self):
        """0/1 numeric column should be detected as binary."""
        series = pd.Series([0, 1, 0, 1, 0])
        assert _detect_binary_pattern(series) is True

    def test_numeric_12_is_binary(self):
        """1/2 numeric column should be detected as binary (two unique values)."""
        series = pd.Series([1, 2, 1, 2, 1])
        assert _detect_binary_pattern(series) is True

    def test_numeric_two_values_but_non_binary_text(self):
        """Arbitrary two-value text like 'red'/'green' should NOT be binary."""
        series = pd.Series(["red", "green", "red", "green"])
        assert _detect_binary_pattern(series) is False

    def test_yes_no_text_is_binary(self):
        """是/否 text column should be detected as binary."""
        series = pd.Series(["是", "否", "是", "是", "否"])
        assert _detect_binary_pattern(series) is True

    def test_male_female_text_is_binary(self):
        """男/女 text column should be detected as binary."""
        series = pd.Series(["男", "女", "男", "男", "女"])
        assert _detect_binary_pattern(series) is True

    def test_three_values_not_binary(self):
        """Column with 3 unique values should not be binary."""
        series = pd.Series([0, 1, 2, 0, 1])
        assert _detect_binary_pattern(series) is False


class TestBinaryVariableInference:
    """Test infer_variable_schema returns 'binary' type correctly."""

    def test_01_returns_binary(self):
        """0/1 column should be inferred as 'binary'."""
        df = pd.DataFrame({
            "converted": [0, 1, 0, 1, 0, 1],
            "score": [3, 4, 5, 3, 4, 5],
        })
        result = infer_variable_schema(df)
        types = dict(zip(result["column"], result["inferred_type"]))
        assert types["converted"] == "binary"

    def test_yes_no_returns_binary(self):
        """是/否 column should be inferred as 'binary'."""
        df = pd.DataFrame({
            "是否推荐": ["是", "否", "是", "是", "否"],
            "评分": [3, 4, 5, 3, 4],
        })
        result = infer_variable_schema(df)
        types = dict(zip(result["column"], result["inferred_type"]))
        assert types["是否推荐"] == "binary"

    def test_binary_not_override_to_ordinal(self):
        """Column named '满意度' with 0/1 values should stay 'binary', not become 'ordinal'."""
        df = pd.DataFrame({
            "满意度": [0, 1, 0, 1, 0, 1, 0],
            "age": [25, 30, 35, 40, 45, 50, 55],
        })
        result = infer_variable_schema(df)
        types = dict(zip(result["column"], result["inferred_type"]))
        assert types["满意度"] == "binary", (
            f"满意度 with 0/1 should be binary, got {types['满意度']}"
        )

    def test_true_scale_still_ordinal(self):
        """Column with true scale (1-5) should still be 'ordinal'."""
        df = pd.DataFrame({
            "满意度": [1, 3, 5, 2, 4, 3, 5, 1],
            "age": [25, 30, 35, 40, 45, 50, 55, 60],
        })
        result = infer_variable_schema(df)
        types = dict(zip(result["column"], result["inferred_type"]))
        assert types["满意度"] == "ordinal", (
            f"满意度 with 1-5 scale should be ordinal, got {types['满意度']}"
        )
