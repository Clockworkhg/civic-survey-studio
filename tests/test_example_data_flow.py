"""Tests for example data loading flow — file existence, loadability, privacy."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pytest

from src.ui.example_data import (
    example_data_available,
    load_example_data,
    get_example_data_info,
)
from src.ui.messages import (
    get_example_data_loaded_message,
    get_example_data_not_found_message,
)


# ================================================================
# Example data availability
# ================================================================

class TestExampleDataAvailability:
    def test_example_data_is_available(self):
        """Built-in example data files should exist in the project."""
        assert example_data_available(), (
            "Example data files not found. "
            "Ensure examples/government_service_satisfaction_sample.csv "
            "and examples/variable_dictionary_sample.csv exist."
        )

    def test_get_info_returns_available_true(self):
        info = get_example_data_info()
        assert info["available"] is True
        assert info["main_size"] > 0
        assert info["var_dict_size"] > 0


# ================================================================
# Example data loading
# ================================================================

class TestExampleDataLoading:
    def test_load_returns_dataframes(self):
        main_df, var_dict_df = load_example_data()
        assert main_df is not None, "Main example CSV failed to load"
        assert var_dict_df is not None, "Var dict CSV failed to load"

    def test_main_df_is_dataframe(self):
        main_df, _ = load_example_data()
        assert isinstance(main_df, pd.DataFrame)

    def test_main_df_has_rows(self):
        main_df, _ = load_example_data()
        assert len(main_df) >= 50, f"Expected >= 50 rows, got {len(main_df)}"

    def test_main_df_has_columns(self):
        main_df, _ = load_example_data()
        assert len(main_df.columns) >= 8, f"Expected >= 8 columns, got {len(main_df.columns)}"

    def test_var_dict_df_is_dataframe(self):
        _, var_dict_df = load_example_data()
        assert isinstance(var_dict_df, pd.DataFrame)


# ================================================================
# Example data privacy
# ================================================================

class TestExampleDataPrivacy:
    SENSITIVE_COL_KEYWORDS = [
        "身份证", "手机", "电话", "姓名", "地址", "银行卡",
        "真实姓名", "住址", "passport", "id_card",
    ]

    @pytest.fixture(autouse=True)
    def setup(self):
        self.df, _ = load_example_data()

    def test_no_sensitive_column_names(self):
        cols_lower = [c.lower() for c in self.df.columns]
        for col in cols_lower:
            for kw in self.SENSITIVE_COL_KEYWORDS:
                assert kw not in col, f"Column '{col}' matches sensitive keyword '{kw}'"

    def test_no_phone_numbers_in_cells(self):
        import re
        phone_re = re.compile(r"1[3-9]\d{9}")
        for col in self.df.columns:
            if self.df[col].dtype == "object":
                for val in self.df[col].dropna():
                    assert not phone_re.search(str(val)), (
                        f"Possible phone number in '{col}': {str(val)[:20]}"
                    )

    def test_no_id_numbers_in_cells(self):
        import re
        id_re = re.compile(r"\d{17}[\dXx]")
        for col in self.df.columns:
            if self.df[col].dtype == "object":
                for val in self.df[col].dropna():
                    val_str = str(val)
                    if val_str.isdigit() and len(val_str) == 18:
                        assert not id_re.match(val_str), (
                            f"Possible ID number in '{col}': {val_str}"
                        )


# ================================================================
# Example data loading function behavior
# ================================================================

class TestExampleDataLoadFunction:
    def test_load_is_repeatable(self):
        """Loading twice should return same-shaped data."""
        df1, _ = load_example_data()
        df2, _ = load_example_data()
        assert df1.shape == df2.shape

    def test_load_handles_utf8_encoding(self):
        """Example CSV should be readable with utf-8-sig encoding."""
        df, _ = load_example_data()
        # Chinese column names should display correctly
        cn_cols = [c for c in df.columns if any('一' <= ch <= '鿿' for ch in c)]
        assert len(cn_cols) >= 1, "No Chinese column names found"


# ================================================================
# Messages for example data flow
# ================================================================

class TestExampleDataMessages:
    def test_loaded_message_is_string(self):
        msg = get_example_data_loaded_message()
        assert isinstance(msg, str)
        assert len(msg) > 20

    def test_not_found_message_is_string(self):
        msg = get_example_data_not_found_message()
        assert isinstance(msg, str)
        assert len(msg) > 20
