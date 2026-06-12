"""Tab-specific UI components.

Each tab module exports a ``render_*`` function that renders the tab's
Streamlit widgets. The functions are called inside one of the 5 main tabs
defined in app.py (gt1–gt5):

  gt1 数据与变量     → tab_data_upload, tab_data_overview, tab_variable_config
  gt2 分析方案       → tab_quick_report, tab_analysis_config
  gt3 统计分析       → tab_univariate_analysis, tab_bivariate_analysis, tab_multivariate_analysis
  gt4 可视化仪表盘   → tab_visualization
  gt5 报告工作台     → tab_template_report, tab_ai_analysis

Internal tab modules:
- tab_data_upload:          data upload / preview
- tab_data_overview:        data quality overview
- tab_variable_config:      variable recognition + AI planning
- tab_quick_report:         current analysis config summary
- tab_analysis_config:      manual analysis configuration
- tab_univariate_analysis:  univariate statistics
- tab_bivariate_analysis:   bivariate (cross) analysis
- tab_multivariate_analysis: multivariate regression
- tab_visualization:        chart dashboard + explorer
- tab_template_report:      template-based report generation (non-AI)
- tab_ai_analysis:          AI-powered report generation
- api_config:               shared AI API configuration (sidebar)
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
