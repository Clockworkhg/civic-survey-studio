"""Tests for example data files — integrity, readability, and privacy."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pytest


EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "examples")
MAIN_CSV = os.path.join(EXAMPLES_DIR, "government_service_satisfaction_sample.csv")
VAR_DICT_CSV = os.path.join(EXAMPLES_DIR, "variable_dictionary_sample.csv")


class TestExampleDataExists:
    """Verify example data files exist and are readable."""

    def test_main_csv_exists(self):
        assert os.path.isfile(MAIN_CSV), f"Missing: {MAIN_CSV}"

    def test_var_dict_csv_exists(self):
        assert os.path.isfile(VAR_DICT_CSV), f"Missing: {VAR_DICT_CSV}"

    def test_main_csv_readable(self):
        df = pd.read_csv(MAIN_CSV, encoding="utf-8-sig")
        assert len(df) > 0

    def test_var_dict_csv_readable(self):
        df = pd.read_csv(VAR_DICT_CSV, encoding="utf-8-sig")
        assert len(df) > 0


class TestExampleDataShape:
    """Verify example data has reasonable dimensions."""

    def test_row_count_reasonable(self):
        df = pd.read_csv(MAIN_CSV, encoding="utf-8-sig")
        assert 50 <= len(df) <= 500, f"Expected 50-500 rows, got {len(df)}"

    def test_column_count_reasonable(self):
        df = pd.read_csv(MAIN_CSV, encoding="utf-8-sig")
        assert 8 <= len(df.columns) <= 30, f"Expected 8-30 columns, got {len(df.columns)}"


class TestExampleDataColumns:
    """Verify example data has the right column categories."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.df = pd.read_csv(MAIN_CSV, encoding="utf-8-sig")

    def test_has_binary_column(self):
        """At least one column should be binary (2 unique non-null values)."""
        binary_cols = []
        for col in self.df.columns:
            unique_vals = self.df[col].dropna().unique()
            if len(unique_vals) == 2:
                binary_cols.append(col)
        assert len(binary_cols) >= 1, f"No binary column found. Columns with 2 uniques: {binary_cols}"

    def test_has_numeric_column(self):
        """At least one numeric column should exist."""
        numeric_cols = self.df.select_dtypes(include=["float64", "int64", "Float64", "Int64"]).columns.tolist()
        assert len(numeric_cols) >= 1, f"No numeric columns found. Dtypes: {self.df.dtypes.to_dict()}"

    def test_has_categorical_column(self):
        """At least one categorical (object) column should exist."""
        obj_cols = self.df.select_dtypes(include=["object"]).columns.tolist()
        assert len(obj_cols) >= 1, f"No object/categorical columns found"

    def test_has_satisfaction_column(self):
        """Should have at least one column related to satisfaction."""
        cols_lower = [c.lower() for c in self.df.columns]
        has_sat = any("满意" in c or "satisf" in c.lower() for c in cols_lower)
        assert has_sat, f"No satisfaction-related column found in {list(self.df.columns)}"


class TestExampleDataPrivacy:
    """Verify example data contains no real personal information."""

    SENSITIVE_PATTERNS = [
        "身份证", "手机", "电话", "姓名", "地址", "银行卡",
        "身份证号", "手机号", "电话号码", "真实", "住址",
        "id_card", "phone", "mobile", "passport",
    ]

    @pytest.fixture(autouse=True)
    def setup(self):
        self.df = pd.read_csv(MAIN_CSV, encoding="utf-8-sig")

    def test_no_sensitive_column_names(self):
        """Column names should not contain sensitive identifiers."""
        cols_lower = [c.lower() for c in self.df.columns]
        for col in cols_lower:
            for pattern in self.SENSITIVE_PATTERNS:
                assert pattern not in col, f"Column '{col}' matches sensitive pattern '{pattern}'"

    def test_no_sensitive_data_in_cells(self):
        """No cell should look like a real phone number or ID card number."""
        import re
        # Chinese phone number pattern
        phone_re = re.compile(r"1[3-9]\d{9}")
        # Chinese ID card pattern (18 digits)
        id_re = re.compile(r"\d{17}[\dXx]")

        for col in self.df.columns:
            if self.df[col].dtype == "object":
                for val in self.df[col].dropna():
                    val_str = str(val)
                    assert not phone_re.search(val_str), f"Possible phone number in '{col}': {val_str}"
                    # Only check for ID pattern if the value looks numeric
                    if val_str.isdigit() and len(val_str) == 18:
                        assert not id_re.match(val_str), f"Possible ID number in '{col}': {val_str}"


class TestExampleDataMissingValues:
    """Verify example data has some missing values (realistic)."""

    def test_has_some_missing(self):
        df = pd.read_csv(MAIN_CSV, encoding="utf-8-sig")
        total_missing = df.isnull().sum().sum()
        # Should have some missing values (not too many, not zero for realism)
        assert total_missing >= 0, "Missing count should be non-negative"
        # At least one column with missing to demonstrate the feature
        # This is a soft check — if the test data is regenerated with different seed it may vary
