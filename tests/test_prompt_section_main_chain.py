"""Verify that build_ai_report_prompt() correctly uses PromptSection/inject_prompt_sections().

Key checks:
1. Literature review content appears when applicable structure + content provided
2. Background context appears when applicable structure + content provided
3. Conditional notes appear when conditions are met
4. Empty content is silently skipped
5. Sections appear in priority order
6. Non-applicable structures suppress literature/background
7. Old _inject_section() is no longer used
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPromptSectionMainChain:
    """Verify PromptSection-based injection in build_ai_report_prompt()."""

    @pytest.fixture
    def minimal_payload(self):
        """Minimal payload with no regression or significance (triggers conditional notes)."""
        return {
            "project_meta": {
                "report_title": "测试报告",
                "variable_name_map": {},
            },
            "data_overview": {"sample_size": 100, "num_variables": 5},
            "variable_schema": [],
            "user_analysis_config": {
                "target_variable": "",
                "group_variables": [],
                "explanatory_variables": [],
                "excluded_sensitive_variables": [],
                "privacy_restricted_variables": [],
            },
            "analysis_plan": [],
            "analysis_results": [],
            "chart_summaries": None,
            "warnings": [],
        }

    @pytest.fixture
    def rich_payload(self):
        """Payload with logistic regression and significance (suppresses 'no regression' note)."""
        return {
            "project_meta": {
                "report_title": "测试报告",
                "variable_name_map": {},
            },
            "data_overview": {"sample_size": 100, "num_variables": 5},
            "variable_schema": [],
            "user_analysis_config": {
                "target_variable": "satisfied",
                "group_variables": ["region"],
                "explanatory_variables": ["score"],
                "excluded_sensitive_variables": [],
                "privacy_restricted_variables": [],
            },
            "analysis_plan": [],
            "analysis_results": [
                {
                    "analysis_id": "logit_1",
                    "analysis_type": "logistic_regression",
                    "variables": ["satisfied", "score"],
                    "result": {
                        "pseudo_r_squared": 0.3,
                        "coefficients": [
                            {"variable": "score", "p_value": 0.001, "significant": True,
                             "odds_ratio": 2.5, "or_ci_lower": 1.8, "or_ci_upper": 3.5}
                        ],
                    },
                    "p_value": 0.001,
                    "significant": True,
                },
                {
                    "analysis_id": "corr_1",
                    "analysis_type": "numeric_numeric_correlation",
                    "variables": ["score", "satisfied"],
                    "result": {"pearson_r": 0.5, "pearson_p_value": 0.001},
                    "p_value": 0.001,
                    "significant": True,
                },
            ],
            "chart_summaries": None,
            "warnings": [],
        }

    # ── Literature review injection ──

    def test_literature_injected_for_applicable_structure(self, minimal_payload):
        """Literature content appears when structure supports it."""
        from src.llm_prompts import build_ai_report_prompt
        _, user = build_ai_report_prompt(
            analysis_payload=minimal_payload,
            report_structure="学术论文式报告",
            literature_review_content="这是预生成的文献综述内容。参考文献：[1] Author (2020)...",
        )
        assert "预生成文献综述" in user
        assert "Author (2020)" in user

    def test_literature_suppressed_for_non_applicable_structure(self, minimal_payload):
        """Literature content should NOT appear for non-applicable structures."""
        from src.llm_prompts import build_ai_report_prompt
        _, user = build_ai_report_prompt(
            analysis_payload=minimal_payload,
            report_structure="通用调研报告",
            literature_review_content="文献综述内容...",
        )
        assert "预生成文献综述" not in user

    def test_literature_skipped_when_content_empty(self, minimal_payload):
        """Empty literature content should be silently skipped."""
        from src.llm_prompts import build_ai_report_prompt
        _, user = build_ai_report_prompt(
            analysis_payload=minimal_payload,
            report_structure="学术论文式报告",
            literature_review_content=None,
        )
        assert "预生成文献综述" not in user

    # ── Background context injection ──

    def test_background_injected_for_applicable_structure(self, minimal_payload):
        """Background content appears when structure supports it."""
        from src.llm_prompts import build_ai_report_prompt
        _, user = build_ai_report_prompt(
            analysis_payload=minimal_payload,
            report_structure="政务决策报告",
            background_context="## 政策背景\n\n根据2023年国务院...",
        )
        assert "预生成研究背景" in user
        assert "国务院" in user

    def test_background_injected_for_academic_structure(self, minimal_payload):
        """学术论文式报告 also supports background."""
        from src.llm_prompts import build_ai_report_prompt
        _, user = build_ai_report_prompt(
            analysis_payload=minimal_payload,
            report_structure="学术论文式报告",
            background_context="政策背景内容...",
        )
        assert "预生成研究背景" in user

    def test_background_suppressed_for_non_applicable_structure(self, minimal_payload):
        """Background should NOT appear for structures that don't support it."""
        from src.llm_prompts import build_ai_report_prompt
        _, user = build_ai_report_prompt(
            analysis_payload=minimal_payload,
            report_structure="课程作业报告",
            background_context="政策背景...",
        )
        assert "预生成研究背景" not in user

    def test_background_skipped_when_content_empty(self, minimal_payload):
        """Empty background content should be silently skipped."""
        from src.llm_prompts import build_ai_report_prompt
        _, user = build_ai_report_prompt(
            analysis_payload=minimal_payload,
            report_structure="学术论文式报告",
            background_context=None,
        )
        assert "预生成研究背景" not in user

    # ── Conditional notes ──

    def test_conditional_notes_appear_when_no_regression(self, minimal_payload):
        """When no regression, conditional note should warn about it."""
        from src.llm_prompts import build_ai_report_prompt
        _, user = build_ai_report_prompt(
            analysis_payload=minimal_payload,
            report_structure="通用调研报告",
        )
        assert "条件提示" in user
        # Should warn about no regression
        assert "回归分析" in user

    def test_conditional_notes_appear_when_no_target(self, minimal_payload):
        """When no target variable, conditional note should warn."""
        from src.llm_prompts import build_ai_report_prompt
        _, user = build_ai_report_prompt(
            analysis_payload=minimal_payload,
            report_structure="通用调研报告",
        )
        assert "未指定核心结果变量" in user or "探索性分析" in user

    def test_no_false_regression_warning_with_logistic(self, rich_payload):
        """With logistic regression present, should NOT warn about 'no regression'."""
        from src.llm_prompts import build_ai_report_prompt
        _, user = build_ai_report_prompt(
            analysis_payload=rich_payload,
            report_structure="学术论文式报告",
        )
        # Should NOT have the "no regression" warning
        assert "没有回归分析结果" not in user

    # ── Priority ordering ──

    def test_conditional_notes_appear_before_literature(self, minimal_payload):
        """Conditional notes (priority=100) should appear before literature (priority=50)."""
        from src.llm_prompts import build_ai_report_prompt
        _, user = build_ai_report_prompt(
            analysis_payload=minimal_payload,
            report_structure="学术论文式报告",
            literature_review_content="文献综述测试内容",
            background_context="背景测试内容",
        )
        cond_pos = user.index("条件提示")
        lit_pos = user.index("预生成文献综述")
        bg_pos = user.index("预生成研究背景")
        # Conditional notes first, then literature, then background
        assert cond_pos < lit_pos
        assert lit_pos < bg_pos

    # ── Both literature and background together ──

    def test_both_literature_and_background_injected(self, minimal_payload):
        """Both sections appear when both provided and structure supports both."""
        from src.llm_prompts import build_ai_report_prompt
        _, user = build_ai_report_prompt(
            analysis_payload=minimal_payload,
            report_structure="学术论文式报告",
            literature_review_content="文献综述内容 ABC",
            background_context="背景材料 XYZ",
        )
        assert "文献综述内容 ABC" in user
        assert "背景材料 XYZ" in user
        assert "预生成文献综述" in user
        assert "预生成研究背景" in user

    # ── Verify _inject_section is gone ──

    def test_inject_section_function_removed(self):
        """The old _inject_section() function should no longer exist."""
        from src import llm_prompts
        assert not hasattr(llm_prompts, '_inject_section'), (
            "_inject_section() should have been removed from llm_prompts"
        )

    # ── Separator formatting ──

    def test_separator_present_between_sections(self, minimal_payload):
        """Sections should be separated by ---."""
        from src.llm_prompts import build_ai_report_prompt
        _, user = build_ai_report_prompt(
            analysis_payload=minimal_payload,
            report_structure="学术论文式报告",
            literature_review_content="文献内容",
        )
        assert "---" in user


class TestInjectPromptSectionsEdgeCases:
    """Edge cases for inject_prompt_sections() at the main chain level."""

    @pytest.fixture
    def empty_payload(self):
        return {
            "project_meta": {"report_title": "T", "variable_name_map": {}},
            "data_overview": {"sample_size": 0},
            "variable_schema": [],
            "user_analysis_config": {},
            "analysis_plan": [],
            "analysis_results": [],
            "chart_summaries": None,
            "warnings": [],
        }

    def test_no_sections_does_not_break_prompt(self, empty_payload):
        """Prompt generation should work fine with no sections injected."""
        from src.llm_prompts import build_ai_report_prompt
        system, user = build_ai_report_prompt(
            analysis_payload=empty_payload,
            report_structure="通用调研报告",
            literature_review_content=None,
            background_context=None,
        )
        assert "请基于以下统计分析结果撰写数据分析报告" in user
        assert "Analysis Payload" in user

    def test_prompt_structure_intact_with_sections(self, empty_payload):
        """Even with sections injected, payload JSON should still be present."""
        from src.llm_prompts import build_ai_report_prompt
        _, user = build_ai_report_prompt(
            analysis_payload=empty_payload,
            report_structure="学术论文式报告",
            literature_review_content="测试文献",
        )
        assert "分析结果数据 (Analysis Payload)" in user
        assert "analysis_results" in user
        # Literature should be before payload
        lit_pos = user.index("预生成文献综述")
        payload_pos = user.index("分析结果数据")
        assert lit_pos < payload_pos
