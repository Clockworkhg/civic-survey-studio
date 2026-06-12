"""Tests for payload_inspector — centralized payload checks."""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.payload_inspector import (
    payload_has_regression,
    payload_has_logistic_regression,
    payload_has_ols_regression,
    payload_has_significance,
    get_analysis_types,
    payload_has_target,
)


class TestPayloadInspector:
    """Test all payload inspector functions."""

    @pytest.fixture
    def empty_payload(self):
        return {"analysis_results": [], "user_analysis_config": {}}

    @pytest.fixture
    def ols_payload(self):
        return {
            "analysis_results": [
                {"analysis_type": "categorical_frequency", "p_value": None},
                {"analysis_type": "linear_regression",
                 "p_value": 0.001, "result": {"r_squared": 0.4}},
            ],
            "user_analysis_config": {"target_variable": "score"},
        }

    @pytest.fixture
    def logistic_payload(self):
        return {
            "analysis_results": [
                {"analysis_type": "categorical_frequency", "p_value": None},
                {"analysis_type": "logistic_regression",
                 "p_value": 0.002, "result": {"pseudo_r_squared": 0.25}},
            ],
            "user_analysis_config": {"target_variable": "converted"},
        }

    @pytest.fixture
    def mixed_payload(self):
        return {
            "analysis_results": [
                {"analysis_type": "categorical_frequency", "p_value": None},
                {"analysis_type": "linear_regression", "p_value": 0.001},
                {"analysis_type": "logistic_regression", "p_value": 0.002},
                {"analysis_type": "numeric_numeric_correlation", "p_value": 0.03},
                {"analysis_type": "categorical_categorical_chi_square", "p_value": 0.01},
            ],
            "user_analysis_config": {"target_variable": "score"},
        }

    def test_has_regression_empty(self, empty_payload):
        assert payload_has_regression(empty_payload) is False

    def test_has_regression_ols(self, ols_payload):
        assert payload_has_regression(ols_payload) is True

    def test_has_regression_logistic(self, logistic_payload):
        assert payload_has_regression(logistic_payload) is True

    def test_has_ols_empty(self, empty_payload):
        assert payload_has_ols_regression(empty_payload) is False

    def test_has_ols_present(self, ols_payload):
        assert payload_has_ols_regression(ols_payload) is True

    def test_has_logistic_absent_in_ols_only(self, ols_payload):
        assert payload_has_logistic_regression(ols_payload) is False

    def test_has_logistic_present(self, logistic_payload):
        assert payload_has_logistic_regression(logistic_payload) is True

    def test_has_significance_empty(self, empty_payload):
        assert payload_has_significance(empty_payload) is False

    def test_has_significance_present(self, ols_payload):
        assert payload_has_significance(ols_payload) is True

    def test_has_significance_logistic(self, logistic_payload):
        assert payload_has_significance(logistic_payload) is True

    def test_get_analysis_types(self, mixed_payload):
        types = get_analysis_types(mixed_payload)
        assert types == {
            "categorical_frequency", "linear_regression",
            "logistic_regression", "numeric_numeric_correlation",
            "categorical_categorical_chi_square",
        }

    def test_has_target_true(self, ols_payload):
        assert payload_has_target(ols_payload) is True

    def test_has_target_false(self, empty_payload):
        assert payload_has_target(empty_payload) is False
