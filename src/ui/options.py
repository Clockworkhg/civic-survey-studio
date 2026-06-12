"""Re-export report option functions for UI consumption.

These are thin re-exports from src.report_options, the single source
of truth for report structure/style/length/theme options. Having a
single import target for app.py avoids duplicate inline imports and
provides a future hook for UI-specific filtering or label processing.
"""

from src.report_options import (
    get_structure_options,
    get_style_options,
    get_length_options,
    get_html_theme_options,
    is_structure_supports_background,
    is_structure_supports_literature,
)

__all__ = [
    "get_structure_options",
    "get_style_options",
    "get_length_options",
    "get_html_theme_options",
    "is_structure_supports_background",
    "is_structure_supports_literature",
]
