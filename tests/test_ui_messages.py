"""Tests for src.ui.messages — centralized UI prompt helper."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from src.ui.messages import (
    get_no_api_key_message,
    get_no_api_key_short_message,
    get_literature_empty_message,
    get_literature_error_message,
    get_literature_keywords_hint,
    get_privacy_warning_message,
    get_sensitive_field_explanations,
    get_sensitive_field_data_explanation,
    get_export_success_message,
    get_export_error_message,
    get_export_directory_hint,
    format_user_friendly_error,
    get_ai_report_error_message,
    get_beginner_flow_guide,
    get_example_data_loaded_message,
    get_example_data_not_found_message,
)


# ================================================================
# No API Key messages
# ================================================================

class TestNoApiKeyMessage:
    def test_returns_non_empty_string(self):
        msg = get_no_api_key_message()
        assert isinstance(msg, str)
        assert len(msg) > 50

    def test_mentions_no_api_key(self):
        msg = get_no_api_key_message()
        assert "API Key" in msg

    def test_mentions_available_features(self):
        msg = get_no_api_key_message()
        assert "数据上传" in msg or "统计分析" in msg or "统计" in msg

    def test_mentions_ai_report_requires_key(self):
        msg = get_no_api_key_message()
        assert "AI" in msg

    def test_includes_env_var_when_provided(self):
        msg = get_no_api_key_message(api_key_env="DEEPSEEK_API_KEY")
        assert "DEEPSEEK_API_KEY" in msg

    def test_short_message_is_concise(self):
        msg = get_no_api_key_short_message()
        assert len(msg) < 200
        assert "API Key" in msg


# ================================================================
# Literature messages
# ================================================================

class TestLiteratureMessages:
    def test_empty_message_mentions_english_databases(self):
        msg = get_literature_empty_message()
        assert "英文" in msg

    def test_empty_message_with_chinese_keywords_suggests_english(self):
        msg = get_literature_empty_message("满意度 政务服务")
        assert "government service satisfaction" in msg or "public service" in msg

    def test_empty_message_mentions_auxiliary(self):
        msg = get_literature_empty_message()
        assert "不影响" in msg or "辅助" in msg

    def test_error_message_is_actionable(self):
        msg = get_literature_error_message()
        assert "稍后重试" in msg or "跳过" in msg or "网络" in msg

    def test_error_message_includes_original_error(self):
        msg = get_literature_error_message("Connection timed out")
        assert "Connection timed out" in msg

    def test_keywords_hint_mentions_english(self):
        msg = get_literature_keywords_hint()
        assert "英文" in msg


# ================================================================
# Privacy messages
# ================================================================

class TestPrivacyMessages:
    def test_high_risk_warning_detailed(self):
        msg = get_privacy_warning_message(high_risk_count=2, medium_risk_count=1)
        assert "2" in msg
        assert "1" in msg

    def test_high_risk_warning_mentions_examples(self):
        msg = get_privacy_warning_message(high_risk_count=1)
        assert "手机号" in msg or "身份证" in msg or "自由文本" in msg

    def test_only_medium_risk_returns_string(self):
        msg = get_privacy_warning_message(high_risk_count=0, medium_risk_count=3)
        assert isinstance(msg, str)
        assert len(msg) > 20

    def test_no_risk_returns_success_message(self):
        msg = get_privacy_warning_message(high_risk_count=0, medium_risk_count=0)
        assert "✅" in msg or "未检测到" in msg

    def test_sensitive_explanations_has_all_categories(self):
        explanations = get_sensitive_field_explanations()
        expected_categories = [
            "direct_identifier", "contact_info", "free_text",
            "financial", "location_info", "demographic_attribute",
            "sensitive_attribute", "unknown",
        ]
        for cat in expected_categories:
            assert cat in explanations, f"Missing category: {cat}"

    def test_get_explanation_for_known_category(self):
        expl = get_sensitive_field_data_explanation("direct_identifier")
        assert "直接身份标识" in expl or "身份证" in expl or "手机号" in expl

    def test_get_explanation_for_unknown_category(self):
        expl = get_sensitive_field_data_explanation("nonexistent")
        assert isinstance(expl, str)
        assert len(expl) > 0


# ================================================================
# Export messages
# ================================================================

class TestExportMessages:
    def test_success_message_lists_formats(self):
        msg = get_export_success_message(["HTML", "DOCX"])
        assert "HTML" in msg
        assert "DOCX" in msg

    def test_success_message_has_download_hint(self):
        msg = get_export_success_message(["HTML"])
        assert "下载" in msg

    def test_error_message_has_actionable_suggestions(self):
        msg = get_export_error_message("DOCX")
        assert "outputs" in msg.lower() or "权限" in msg or "占用" in msg or "python-docx" in msg

    def test_error_message_includes_format_name(self):
        msg = get_export_error_message("HTML")
        assert "HTML" in msg

    def test_directory_hint_mentions_outputs(self):
        msg = get_export_directory_hint()
        assert "outputs" in msg.lower()


# ================================================================
# AI Report error messages
# ================================================================

class TestAiReportErrorMessages:
    def test_ai_report_error_is_alias(self):
        msg1 = get_ai_report_error_message("unauthorized")
        msg2 = format_user_friendly_error("unauthorized", context="AI 报告生成")
        assert msg1 == msg2

    def test_error_context_included(self):
        msg = get_ai_report_error_message("test error")
        assert "AI 报告生成" in msg


# ================================================================
# Beginner guide
# ================================================================

class TestBeginnerGuide:
    def test_guide_has_six_steps(self):
        guide = get_beginner_flow_guide()
        assert "**1**" in guide
        assert "**2**" in guide
        assert "**3**" in guide
        assert "**4**" in guide
        assert "**5**" in guide
        assert "**6**" in guide

    def test_guide_mentions_no_api_key(self):
        guide = get_beginner_flow_guide()
        assert "API Key" in guide

    def test_guide_mentions_example_data(self):
        guide = get_beginner_flow_guide()
        assert "示例数据" in guide


# ================================================================
# Example data messages
# ================================================================

class TestExampleDataMessages:
    def test_loaded_message_mentions_simulated(self):
        msg = get_example_data_loaded_message()
        assert "模拟" in msg or "不包含真实" in msg

    def test_loaded_message_mentions_next_steps(self):
        msg = get_example_data_loaded_message()
        assert "变量识别" in msg or "分析配置" in msg

    def test_not_found_message_mentions_file_paths(self):
        msg = get_example_data_not_found_message()
        assert "examples/" in msg

    def test_not_found_message_mentions_own_data(self):
        msg = get_example_data_not_found_message()
        assert "自己的数据" in msg or "上传" in msg
