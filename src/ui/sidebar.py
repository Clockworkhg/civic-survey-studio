"""Sidebar rendering for the Streamlit app.

Encapsulates the entire sidebar widget tree into a single function
that returns a dict of collected values.
"""

from __future__ import annotations

from typing import Any, Dict

import streamlit as st

from src.data_loader import get_excel_sheets
from src.preset_profiles import list_profiles as list_preset_profiles
from src.ui.example_data import example_data_available
from src.ui.theme import COLORS


def _section_label(text: str) -> None:
    """Render a compact, muted sidebar section label (no emoji)."""
    st.markdown(
        f'<div style="font-size:10px;color:{COLORS.text_muted};'
        f'text-transform:uppercase;letter-spacing:1px;'
        f'margin-top:18px;margin-bottom:4px;font-weight:600;">{text}</div>',
        unsafe_allow_html=True,
    )


def render_sidebar() -> Dict[str, Any]:
    """Render the full sidebar and return widget values.

    Uses ``with st.sidebar:`` internally. Call once per app execution,
    after page config but before main content that references the
    sidebar values.

    Returns:
        {
            "generic_file": UploadedFile | None,
            "selected_sheet": str | None,
            "header_row": int,
            "var_table_file": UploadedFile | None,
            "gov_profile": dict | None,
            "profile_key": str,
            "load_example_clicked": bool,
        }
    """
    load_example_clicked = False

    with st.sidebar:
        # ═══════════════════════════════════════════
        # Brand header
        # ═══════════════════════════════════════════
        st.markdown(
            f'<div style="font-size:15px;font-weight:700;color:{COLORS.text_strong};'
            f'margin-bottom:2px;">问策 Insight</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="font-size:10px;color:{COLORS.text_muted};'
            f'text-transform:uppercase;letter-spacing:0.5px;'
            f'margin-bottom:14px;">CivicSurvey Studio</div>',
            unsafe_allow_html=True,
        )

        # ═══════════════════════════════════════════
        # Section 1: Data Source
        # ═══════════════════════════════════════════
        _section_label("数据源")

        generic_file = st.file_uploader(
            "问卷数据文件",
            type=["xlsx", "xls", "csv"],
            key="generic_data",
            help="支持 Excel（.xlsx/.xls）和 CSV（.csv）格式。",
        )

        # Sheet selector (Excel only)
        selected_sheet = None
        if generic_file and generic_file.name.endswith((".xlsx", ".xls")):
            sheets = get_excel_sheets(generic_file)
            if sheets:
                selected_sheet = st.selectbox(
                    "工作表（Sheet）",
                    sheets,
                    key="sheet_selector",
                )
            else:
                st.caption("未能读取工作表列表，将使用第一个工作表。")

        # Header row
        header_row = st.number_input(
            "表头所在行",
            min_value=0, max_value=10, value=0,
            help="0 = 第一行，1 = 第二行",
            key="header_row",
        )

        # Example data button (compact, only when no file)
        if not generic_file:
            if example_data_available():
                st.markdown(
                    f'<div style="font-size:11px;color:{COLORS.text_muted};'
                    f'margin-top:8px;margin-bottom:4px;">没有数据？可加载内置模拟数据体验</div>',
                    unsafe_allow_html=True,
                )
                if st.button("加载内置示例数据", key="load_example_btn",
                             help="加载政府服务满意度模拟数据（无真实个人信息）"):
                    load_example_clicked = True
            else:
                st.caption("示例数据文件未找到。")

        # ═══════════════════════════════════════════
        # Section 2: Variable Dictionary
        # ═══════════════════════════════════════════
        _section_label("变量说明表")
        st.caption("可选，用于增强变量类型推断精度。")

        var_table_file = st.file_uploader(
            "变量说明表文件",
            type=["xlsx", "xls", "csv"],
            key="generic_var_table",
            label_visibility="collapsed",
        )

        # ═══════════════════════════════════════════
        # Section 3: Preset Plans
        # ═══════════════════════════════════════════
        _section_label("预设方案")
        st.caption("选择预设方案后自动填充分析配置。")

        try:
            profile_list = list_preset_profiles()
            profile_options = {"— 无预设 —": None}
            for p in profile_list:
                profile_options[p.get("profile_name", p.get("profile_key", ""))] = p
            profile_names = list(profile_options.keys())
            selected_profile_name = st.selectbox(
                "预设方案",
                profile_names,
                key="preset_profile_selector",
                label_visibility="collapsed",
            )
            selected_profile = profile_options.get(selected_profile_name)
            if selected_profile:
                gov_profile = selected_profile
                profile_key = selected_profile.get("profile_key", "")
            else:
                gov_profile = None
                profile_key = ""
        except Exception:
            gov_profile = None
            profile_key = ""
            st.caption("无可用预设方案。")

        # ═══════════════════════════════════════════
        # Section 4: AI Settings
        # ═══════════════════════════════════════════
        from src.ui.api_config import render_api_config_section
        has_api_key = bool(st.session_state.get("_api_key", ""))
        with st.expander("AI 设置", expanded=not has_api_key):
            st.caption(
                "本地统计分析不需要 API Key。"
                "AI 报告需要配置 API Key。"
            )
            render_api_config_section(location="sidebar")

        # ═══════════════════════════════════════════
        # Section 5: Current Status
        # ═══════════════════════════════════════════
        _section_label("当前状态")
        _data_loaded = generic_file is not None or st.session_state.get("_use_example_data", False)
        _config_set = bool(st.session_state.get("generic_config", {}).get("target_variable", ""))
        _analysis_done = (
            st.session_state.get("_downstream_valid", False)
            and bool(st.session_state.get("_analysis_results", {}))
        )
        status_color = COLORS.success if has_api_key else COLORS.text_muted
        st.markdown(
            f'<div style="font-size:11px;line-height:1.8;color:{COLORS.text_muted};">'
            f'数据：{"✅ 已加载" if _data_loaded else "⏸ 未加载"}<br>'
            f'方案：{"✅ 已配置" if _config_set else "⏸ 未配置"}<br>'
            f'分析：{"✅ 已完成" if _analysis_done else "⏸ 未执行"}<br>'
            f'AI：{"✅ 已配置" if has_api_key else "⏸ 未配置"}'
            f'</div>',
            unsafe_allow_html=True,
        )

    return {
        "generic_file": generic_file,
        "selected_sheet": selected_sheet,
        "header_row": header_row,
        "var_table_file": var_table_file,
        "gov_profile": gov_profile,
        "profile_key": profile_key,
        "load_example_clicked": load_example_clicked,
    }


def render_api_sidebar_section() -> None:
    """No-op: AI config is now rendered inline by render_sidebar().

    Kept for backward compatibility with existing callers.
    """
    pass
