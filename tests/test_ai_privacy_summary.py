"""Tests for AI pre-generation privacy variable summary (P3-4).

Verifies that the privacy summary helper correctly counts variables
by risk level and returns appropriate warnings.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pytest

from src.ui.security import (
    summarize_ai_variable_privacy,
    get_ai_privacy_summary_message,
)


# ================================================================
# Tests
# ================================================================

class TestPrivacySummaryEmpty:
    """Edge cases with empty or minimal schema."""

    def test_empty_schema(self):
        df = pd.DataFrame()
        result = summarize_ai_variable_privacy(df)
        assert result["total_vars"] == 0
        assert result["sent_to_ai"] == 0
        assert result["is_all_safe"] is True

    def test_missing_privacy_columns(self):
        df = pd.DataFrame({"column": ["a", "b", "c"]})
        result = summarize_ai_variable_privacy(df)
        assert result["total_vars"] == 3
        assert result["high_risk"] == 0
        assert result["is_all_safe"] is True

    def test_no_column_column(self):
        df = pd.DataFrame({"some_other": [1, 2, 3]})
        result = summarize_ai_variable_privacy(df)
        assert result["total_vars"] == 0


class TestPrivacySummarySafe:
    """No high-risk variables."""

    def test_all_low_risk(self):
        df = pd.DataFrame({
            "column": ["q1", "q2", "q3"],
            "privacy_risk": ["low", "low", "low"],
            "privacy_category": ["demographic_attribute", "demographic_attribute", "demographic_attribute"],
            "allow_send_to_ai": [True, True, True],
        })
        result = summarize_ai_variable_privacy(df)
        assert result["high_risk"] == 0
        assert result["medium_risk"] == 0
        assert result["is_all_safe"] is True
        assert result["sent_to_ai"] == 3

    def test_mixed_low_and_none(self):
        df = pd.DataFrame({
            "column": ["q1", "q2"],
            "privacy_risk": ["low", "none"],
            "allow_send_to_ai": [True, True],
        })
        result = summarize_ai_variable_privacy(df)
        assert result["high_risk"] == 0
        assert result["medium_risk"] == 0
        assert result["is_all_safe"] is True


class TestPrivacySummaryHighRisk:
    """Scenarios with high-risk variables."""

    def test_one_high_risk_sent_to_ai(self):
        df = pd.DataFrame({
            "column": ["name", "age", "score"],
            "privacy_risk": ["high", "low", "low"],
            "privacy_category": ["direct_identifier", "demographic_attribute", "demographic_attribute"],
            "allow_send_to_ai": [True, True, True],
        })
        result = summarize_ai_variable_privacy(df)
        assert result["high_risk"] == 1
        assert result["high_risk_sent"] == 1
        assert result["has_high_risk_sent"] is True
        assert result["is_all_safe"] is False

    def test_one_high_risk_excluded_from_ai(self):
        df = pd.DataFrame({
            "column": ["name", "age", "score"],
            "privacy_risk": ["high", "low", "low"],
            "allow_send_to_ai": [False, True, True],
        })
        result = summarize_ai_variable_privacy(df)
        assert result["high_risk"] == 1
        assert result["high_risk_sent"] == 0
        assert result["has_high_risk_sent"] is False
        assert result["is_all_safe"] is True

    def test_multiple_high_risk(self):
        df = pd.DataFrame({
            "column": ["phone", "id_card", "address"],
            "privacy_risk": ["high", "high", "high"],
            "privacy_category": ["contact_info", "direct_identifier", "location_info"],
            "allow_send_to_ai": [False, False, False],
        })
        result = summarize_ai_variable_privacy(df)
        assert result["high_risk"] == 3
        assert result["high_risk_sent"] == 0
        assert result["is_all_safe"] is True


class TestPrivacySummaryFreeText:
    """Free text variable handling."""

    def test_free_text_vars_counted(self):
        df = pd.DataFrame({
            "column": ["comments", "rating"],
            "privacy_risk": ["medium", "low"],
            "privacy_category": ["free_text", "demographic_attribute"],
            "allow_send_to_ai": [True, True],
        })
        result = summarize_ai_variable_privacy(df)
        assert result["free_text_vars"] == 1
        assert result["free_text_sent"] == 1

    def test_free_text_excluded(self):
        df = pd.DataFrame({
            "column": ["comments"],
            "privacy_risk": ["medium"],
            "privacy_category": ["free_text"],
            "allow_send_to_ai": [False],
        })
        result = summarize_ai_variable_privacy(df)
        assert result["free_text_vars"] == 1
        assert result["free_text_sent"] == 0


class TestPrivacySummaryUnknown:
    """Unknown risk category handling."""

    def test_unknown_category(self):
        df = pd.DataFrame({
            "column": ["mystery_col"],
            "privacy_risk": ["unknown"],
            "privacy_category": ["unknown"],
            "allow_send_to_ai": [True],
        })
        result = summarize_ai_variable_privacy(df)
        assert result["high_risk"] == 0
        assert result["medium_risk"] == 0
        # unknown defaults to safe
        assert result["is_all_safe"] is True
        assert result["sent_to_ai"] == 1

    def test_unknown_risk_allowed_by_default(self):
        df = pd.DataFrame({
            "column": ["x"],
            "privacy_risk": ["unknown"],
            # no allow_send_to_ai column → default True
        })
        result = summarize_ai_variable_privacy(df)
        assert result["sent_to_ai"] == 1


# ================================================================
# Privacy summary message
# ================================================================

class TestPrivacySummaryMessage:
    """Tests for get_ai_privacy_summary_message."""

    def test_message_returns_string(self):
        summary = {"total_vars": 5, "sent_to_ai": 5, "high_risk": 0, "high_risk_sent": 0,
                   "medium_risk": 0, "medium_risk_sent": 0, "free_text_vars": 0,
                   "free_text_sent": 0, "has_high_risk_sent": False, "is_all_safe": True}
        msg = get_ai_privacy_summary_message(summary)
        assert isinstance(msg, str)
        assert "5" in msg

    def test_safe_message_has_checkmark(self):
        summary = {"total_vars": 3, "sent_to_ai": 3, "high_risk": 0, "high_risk_sent": 0,
                   "medium_risk": 0, "medium_risk_sent": 0, "free_text_vars": 0,
                   "free_text_sent": 0, "has_high_risk_sent": False, "is_all_safe": True}
        msg = get_ai_privacy_summary_message(summary)
        assert "✅" in msg
        assert "隐私检查通过" in msg

    def test_high_risk_message_has_warning(self):
        summary = {"total_vars": 3, "sent_to_ai": 3, "high_risk": 2, "high_risk_sent": 2,
                   "medium_risk": 0, "medium_risk_sent": 0, "free_text_vars": 0,
                   "free_text_sent": 0, "has_high_risk_sent": True, "is_all_safe": False}
        msg = get_ai_privacy_summary_message(summary)
        assert "⚠️" in msg
        assert "高风险" in msg

    def test_free_text_mentioned(self):
        summary = {"total_vars": 5, "sent_to_ai": 5, "high_risk": 0, "high_risk_sent": 0,
                   "medium_risk": 2, "medium_risk_sent": 2, "free_text_vars": 2,
                   "free_text_sent": 2, "has_high_risk_sent": False, "is_all_safe": True}
        msg = get_ai_privacy_summary_message(summary)
        assert "自由文本" in msg
        assert "2" in msg
