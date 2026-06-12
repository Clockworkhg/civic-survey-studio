"""App-level CSS styles.

Provides the application's custom CSS stylesheet and a helper
to inject it into the Streamlit page.
"""

from __future__ import annotations

import streamlit as st

# ================================================================
# Application CSS
# ================================================================

APP_CSS = """
<style>
    [data-testid="metric-container"] {
        background-color: #F8F9FA;
        border: 1px solid #E8E8E8;
        border-radius: 6px;
        padding: 12px 16px;
    }
    [data-testid="metric-container"] label {
        color: #555 !important;
        font-size: 13px !important;
    }
    [data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #2B5F8A !important;
        font-size: 26px !important;
    }
    .main-title {
        font-size: 24px;
        font-weight: 700;
        color: #1A3A5C;
        margin-bottom: 2px;
    }
    .main-subtitle {
        font-size: 14px;
        color: #888;
        margin-bottom: 10px;
    }
    .section-divider {
        margin: 20px 0;
        border-top: 1px solid #E8E8E8;
    }
    .stPlotlyChart {
        margin-bottom: 20px;
    }
    section[data-testid="stSidebar"] {
        background-color: #FAFBFC;
    }
    .disclaimer {
        background-color: #FFF8E1;
        border-left: 4px solid #F5B041;
        padding: 10px 14px;
        font-size: 12px;
        color: #666;
        border-radius: 4px;
        margin: 12px 0;
    }
</style>
"""


def load_app_css() -> str:
    """Return the application CSS as a string."""
    return APP_CSS


def inject_app_css() -> None:
    """Inject the application CSS into the Streamlit page."""
    st.markdown(APP_CSS, unsafe_allow_html=True)
