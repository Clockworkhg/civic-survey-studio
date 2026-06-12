"""Tab-specific UI components.

Each tab module exports a ``render_*`` function that renders the tab's
Streamlit widgets. The functions are designed to be called inside a
``with gtN:`` context manager in app.py.

Tab modules:
- tab_data_upload:        Tab 1 — data upload / preview
- tab_data_overview:      Tab 2 — data quality overview
- tab_variable_config:    Tab 3 — variable recognition + AI planning
- tab_quick_report:       Tab 3 — current analysis config summary
- tab_analysis_config:    Tab 4 — analysis configuration
- tab_univariate_analysis: Tab 5 — univariate statistics
- tab_bivariate_analysis:  Tab 6 — bivariate (cross) analysis
- tab_multivariate_analysis: Tab 7 — multivariate regression
- tab_visualization:      Tab 8 — chart dashboard + explorer
- tab_template_report:   Tab 9 — template-based report generation (non-AI)
- tab_ai_analysis:       Tab 10 — AI intelligent analysis (full-featured report generation)
- api_config:             Shared AI API configuration (sidebar)
"""

from src.ui.tabs.tab_data_upload import render_tab_data_upload
from src.ui.tabs.tab_data_overview import render_tab_data_overview
from src.ui.tabs.tab_variable_config import render_tab_variable_config
from src.ui.tabs.tab_quick_report import render_tab_quick_report
from src.ui.tabs.tab_analysis_config import render_tab_analysis_config
from src.ui.tabs.tab_univariate_analysis import render_tab_univariate_analysis
from src.ui.tabs.tab_bivariate_analysis import render_tab_bivariate_analysis
from src.ui.tabs.tab_multivariate_analysis import render_tab_multivariate_analysis
from src.ui.tabs.tab_visualization import render_tab_visualization
from src.ui.tabs.tab_template_report import render_tab_template_report, render_tab_legacy_report
from src.ui.tabs.tab_ai_analysis import render_tab_ai_analysis

__all__ = [
    "render_tab_data_upload",
    "render_tab_data_overview",
    "render_tab_variable_config",
    "render_tab_quick_report",
    "render_tab_analysis_config",
    "render_tab_univariate_analysis",
    "render_tab_bivariate_analysis",
    "render_tab_multivariate_analysis",
    "render_tab_visualization",
    "render_tab_template_report",
    "render_tab_legacy_report",
    "render_tab_ai_analysis",
]
