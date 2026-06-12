"""Example data loader — load built-in sample data for quick demos.

Provides a helper to load the built-in example CSV and variable dictionary
from the `examples/` directory.  Returns None gracefully if files are
missing so the app never crashes.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd

# Relative to the project root (where app.py lives)
_EXAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "examples"
_MAIN_CSV = "government_service_satisfaction_sample.csv"
_VAR_DICT_CSV = "variable_dictionary_sample.csv"


def example_data_available() -> bool:
    """Check whether both example data files exist."""
    return (
        (_EXAMPLES_DIR / _MAIN_CSV).is_file()
        and (_EXAMPLES_DIR / _VAR_DICT_CSV).is_file()
    )


def load_example_data() -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Load the built-in example data files.

    Returns:
        A tuple of (main_df, var_dict_df).
        Each element is None if the corresponding file doesn't exist or
        cannot be read.
    """
    main_df = None
    var_dict_df = None

    main_path = _EXAMPLES_DIR / _MAIN_CSV
    var_dict_path = _EXAMPLES_DIR / _VAR_DICT_CSV

    if main_path.is_file():
        try:
            main_df = pd.read_csv(main_path, encoding="utf-8-sig")
        except Exception:
            main_df = None

    if var_dict_path.is_file():
        try:
            var_dict_df = pd.read_csv(var_dict_path, encoding="utf-8-sig")
        except Exception:
            var_dict_df = None

    return main_df, var_dict_df


def get_example_data_info() -> Dict[str, object]:
    """Return metadata about the example data files.

    Returns:
        Dict with keys: available (bool), main_path (str), main_size (int),
        var_dict_path (str), var_dict_size (int).
    """
    main_path = _EXAMPLES_DIR / _MAIN_CSV
    var_dict_path = _EXAMPLES_DIR / _VAR_DICT_CSV

    return {
        "available": example_data_available(),
        "main_path": str(main_path),
        "main_size": main_path.stat().st_size if main_path.is_file() else 0,
        "var_dict_path": str(var_dict_path),
        "var_dict_size": var_dict_path.stat().st_size if var_dict_path.is_file() else 0,
    }
