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
from src.ui.messages import get_example_data_loaded_message, get_example_data_not_found_message


def render_sidebar() -> Dict[str, Any]:
    """Render the full sidebar and return widget values.

    Uses ``with st.sidebar:`` internally. Call once per app execution,
    after page config but before main content that references the
    sidebar values.

    Widget keys are preserved exactly as they were when the sidebar
    was inline in app.py.

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
        st.markdown("## 📁 数据上传")

        generic_file = st.file_uploader(
            "问卷数据文件",
            type=["xlsx", "xls", "csv"],
            key="generic_data",
            help="支持 Excel（.xlsx/.xls）和 CSV（.csv）格式。",
        )

        # Sheet 选择（仅 Excel）
        selected_sheet = None
        if generic_file and generic_file.name.endswith((".xlsx", ".xls")):
            sheets = get_excel_sheets(generic_file)
            if sheets:
                selected_sheet = st.selectbox(
                    "选择工作表（Sheet）：",
                    sheets,
                    key="sheet_selector",
                )
            else:
                st.caption("未能读取工作表列表，将使用第一个工作表。")

        # 表头行
        header_row = st.number_input(
            "表头所在行",
            min_value=0, max_value=10, value=0,
            help="0 表示第一行，1 表示第二行，以此类推。",
            key="header_row",
        )

        # ── 示例数据入口 ──
        if not generic_file:
            st.markdown("---")
            st.markdown("## 📦 示例数据")
            st.caption("没有数据？加载内置模拟数据快速体验完整流程。")
            if example_data_available():
                if st.button("📥 加载内置示例数据", key="load_example_btn",
                             help="加载政府服务满意度模拟数据（150 条，无真实个人信息）"):
                    load_example_clicked = True
            else:
                st.caption("⚠️ 示例数据文件未找到。你仍然可以上传自己的数据文件。")

        st.markdown("---")
        st.markdown("## 📖 变量说明表（可选）")

        var_table_file = st.file_uploader(
            "变量说明表（可选）",
            type=["xlsx", "xls", "csv"],
            key="generic_var_table",
            help="包含变量名、中文含义、类型等信息的说明表。如不上传，系统将自动推断变量类型。",
        )

        st.markdown("---")
        st.markdown("## 🎯 预设方案（可选）")
        st.caption("选择预设分析方案可自动填充分析配置。")

        try:
            profile_list = list_preset_profiles()
            profile_options = {"— 无预设 —": None}
            for p in profile_list:
                profile_options[p.get("profile_name", p.get("profile_key", ""))] = p
            profile_names = list(profile_options.keys())
            selected_profile_name = st.selectbox(
                "预设方案：", profile_names,
                key="preset_profile_selector",
            )
            selected_profile = profile_options.get(selected_profile_name)
            if selected_profile:
                st.success(f"✅ 已加载「{selected_profile_name}」预设方案")
                gov_profile = selected_profile
                profile_key = selected_profile.get("profile_key", "")
            else:
                gov_profile = None
                profile_key = ""
        except Exception:
            gov_profile = None
            profile_key = ""
            st.caption("（无可用预设方案）")

        st.markdown("---")
        st.markdown("## ⚙️ 分析配置")
        st.caption("上传数据后在此配置分析参数。")

        st.markdown("---")
        st.caption("通用问卷数据 AI 分析平台 v3.0")

    return {
        "generic_file": generic_file,
        "selected_sheet": selected_sheet,
        "header_row": header_row,
        "var_table_file": var_table_file,
        "gov_profile": gov_profile,
        "profile_key": profile_key,
        "load_example_clicked": load_example_clicked,
    }
