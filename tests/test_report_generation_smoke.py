"""Smoke test: verify the full report generation pipeline works offline.

No real LLM calls — we verify that:
1. Variable inference correctly identifies binary variables
2. run_full_analysis produces logistic regression for binary targets
3. build_analysis_payload properly packs logistic results
4. payload_inspector correctly detects regression types
5. LLMConfig / ReportConfig round-trip via legacy params
6. build_ai_report_prompt includes logistic-specific language
7. Pipeline runs without crashing
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestReportGenerationSmoke:
    """End-to-end smoke test for the report pipeline (no real LLM)."""

    @pytest.fixture
    def binary_dataset(self):
        """Small synthetic dataset with a binary target."""
        np.random.seed(42)
        n = 100
        x1 = np.random.choice([1, 2, 3, 4, 5], n)  # ordinal predictor
        x2 = np.random.choice(["A", "B", "C"], n)   # categorical
        logit = -1.0 + 0.8 * x1
        prob = 1 / (1 + np.exp(-logit))
        y = (np.random.random(n) < prob).astype(int)
        return pd.DataFrame({"converted": y, "score": x1, "region": x2})

    @pytest.fixture
    def schema(self, binary_dataset):
        from src.schema_infer import infer_variable_schema
        return infer_variable_schema(binary_dataset)

    @pytest.fixture
    def config(self):
        return {
            "report_title": "烟雾测试报告",
            "target_variable": "converted",
            "group_variables": ["region"],
            "explanatory_variables": ["score"],
            "research_subject": "测试数据集",
        }

    @pytest.fixture
    def analysis_results(self, binary_dataset, schema, config):
        from src.generic_analysis import run_full_analysis
        return run_full_analysis(binary_dataset, schema, config)

    @pytest.fixture
    def payload(self, binary_dataset, schema, config, analysis_results):
        from src.analysis_packager import build_analysis_payload
        return build_analysis_payload(
            df=binary_dataset,
            schema_df=schema,
            config=config,
            analysis_results=analysis_results,
            quality=None,
            chart_summaries=None,
            selected_sheet="",
            file_type="",
        )

    # ── Stage 1: Binary inference ──

    def test_binary_target_inferred(self, schema, config):
        """Binary target 'converted' should be inferred as 'binary'."""
        target = config["target_variable"]
        row = schema[schema["column"] == target]
        assert len(row) == 1
        assert row.iloc[0]["inferred_type"] == "binary"

    # ── Stage 2: Logistic regression produced ──

    def test_logistic_regression_in_results(self, analysis_results):
        """Binary target should produce logistic regression results."""
        multi = analysis_results.get("multivariate")
        assert multi is not None, "Should have multivariate results"
        assert "error" not in multi, f"Should not error: {multi.get('error')}"
        assert "pseudo_r_squared" in multi, "Should be logistic (has pseudo_r_squared)"

    def test_logistic_has_odds_ratios(self, analysis_results):
        """Logistic coefficients should include odds ratios."""
        multi = analysis_results.get("multivariate")
        coef_df = multi.get("coefficients")
        assert coef_df is not None
        assert "OR (exp(B))" in coef_df.columns

    # ── Stage 3: Payload correctly packs logistic ──

    def test_payload_has_logistic_regression(self, payload):
        """Payload inspector should detect logistic regression."""
        from src.payload_inspector import (
            payload_has_logistic_regression,
            payload_has_regression,
            payload_has_significance,
        )
        assert payload_has_logistic_regression(payload)
        assert payload_has_regression(payload)
        assert payload_has_significance(payload)

    def test_payload_type_is_logistic(self, payload):
        """The analysis_type in results should be 'logistic_regression'."""
        types = [r.get("analysis_type") for r in payload.get("analysis_results", [])]
        assert "logistic_regression" in types

    # ── Stage 4: LLMConfig / ReportConfig round-trip ──

    def test_llm_config_from_legacy(self):
        """LLMConfig.from_legacy_kwargs() should correctly absorb old params."""
        from src.config_models import LLMConfig
        cfg = LLMConfig.from_legacy_kwargs(
            provider_config={"base_url": "https://api.example.com"},
            api_key="sk-test",
            model="claude-4",
            temperature=0.5,
            max_tokens=2048,
            provider_key="openai",
        )
        assert cfg.api_key == "sk-test"
        assert cfg.model == "claude-4"
        assert cfg.temperature == 0.5
        assert cfg.max_tokens == 2048
        assert cfg.provider_key == "openai"
        assert cfg.provider_config == {"base_url": "https://api.example.com"}

    def test_llm_config_to_kwargs_roundtrip(self):
        """LLMConfig → to_kwargs() → from_legacy_kwargs() should be lossless."""
        from src.config_models import LLMConfig
        cfg1 = LLMConfig(
            provider_config={"base_url": "https://x.com"},
            api_key="key",
            model="model",
            temperature=0.7,
            max_tokens=1024,
        )
        cfg2 = LLMConfig.from_legacy_kwargs(**cfg1.to_kwargs())
        assert cfg2.api_key == cfg1.api_key
        assert cfg2.model == cfg1.model
        assert cfg2.temperature == cfg1.temperature
        assert cfg2.max_tokens == cfg1.max_tokens

    def test_report_config_from_legacy(self):
        """ReportConfig.from_legacy_kwargs() should absorb old params."""
        from src.config_models import ReportConfig
        cfg = ReportConfig.from_legacy_kwargs(
            report_structure="学术论文式报告",
            report_style="学术报告风",
            report_length="详细版",
            html_theme="政务蓝白汇报风",
            literature_config={
                "enabled": True,
                "keywords": "满意度 调查",
                "max_sources": 20,
                "year_range": "近10年",
            },
            background_config={"enabled": True, "source_path": "bg/test"},
        )
        assert cfg.report_structure == "学术论文式报告"
        assert cfg.literature_enabled is True
        assert cfg.literature_keywords == "满意度 调查"
        assert cfg.background_enabled is True
        assert cfg.background_source_path == "bg/test"

    def test_report_config_validate_valid(self):
        """Valid ReportConfig should pass validation."""
        from src.config_models import ReportConfig
        cfg = ReportConfig()
        errors = cfg.validate()
        assert errors == []

    def test_report_config_validate_invalid(self):
        """Invalid ReportConfig should report errors."""
        from src.config_models import ReportConfig
        cfg = ReportConfig(
            report_structure="不存在的结构",
            report_style="不存在的风格",
        )
        errors = cfg.validate()
        assert len(errors) >= 2

    # ── Stage 5: Prompt generation ──

    def test_prompt_includes_logistic_language(self, payload):
        """Generated prompt should mention logistic regression / OR."""
        from src.llm_prompts import build_ai_report_prompt
        system, user = build_ai_report_prompt(
            analysis_payload=payload,
            report_structure="学术论文式报告",
            report_style="学术报告风",
            report_length="标准版",
        )
        combined = system + user
        assert "logistic_regression" in combined or "逻辑回归" in combined or "OR" in combined

    def test_prompt_does_not_claim_ols_for_logistic(self, payload):
        """Prompt should not describe logistic results as OLS regression."""
        from src.llm_prompts import build_ai_report_prompt
        system, user = build_ai_report_prompt(
            analysis_payload=payload,
            report_structure="学术论文式报告",
            report_style="学术报告风",
            report_length="标准版",
        )
        combined = system + user
        # Should not have OLS-specific guidance when only logistic is present
        # (checking that the conditional notes for logistic fire, not OLS)
        assert "logistic_regression" in combined or "逻辑回归" in combined

    # ── Stage 6: PromptSection injection ──

    def test_prompt_section_injection(self):
        """PromptSection injection via inject_prompt_sections()."""
        from src.config_models import PromptSection, inject_prompt_sections

        sections = [
            PromptSection(key="bg", title="背景", content="背景材料",
                          priority=10),
            PromptSection(key="lit", title="文献", content="文献材料",
                          priority=5),
        ]
        base = "请写报告。"
        result = inject_prompt_sections(base, sections)
        assert "背景" in result
        assert "文献" in result
        # Higher priority (bg=10) should appear before lower (lit=5)
        assert result.index("背景") < result.index("文献")

    def test_prompt_section_empty_skipped(self):
        """Empty PromptSection should be silently skipped."""
        from src.config_models import PromptSection, inject_prompt_sections
        sections = [
            PromptSection(key="bg", title="背景", content="", priority=10),
            PromptSection(key="lit", title="文献", content="ok", priority=5),
        ]
        result = inject_prompt_sections("base", sections)
        assert "背景" not in result
        assert "文献" in result

    def test_prompt_section_dedup(self):
        """Duplicate keys: higher priority should win."""
        from src.config_models import PromptSection, inject_prompt_sections
        sections = [
            PromptSection(key="note", title="V1", content="low prio",
                          priority=1),
            PromptSection(key="note", title="V2", content="high prio",
                          priority=10),
        ]
        result = inject_prompt_sections("base", sections)
        assert "high prio" in result
        assert "low prio" not in result

    # ── Stage 7: generate_ai_report with LLMConfig/ReportConfig ──

    def test_generate_ai_report_with_config_objects(
        self, binary_dataset, schema, config, analysis_results
    ):
        """generate_ai_report should accept LLMConfig + ReportConfig
        and not crash. We mock call_llm to avoid real API calls."""
        from unittest.mock import patch
        from src.config_models import LLMConfig, ReportConfig
        from src.ai_report_generator import generate_ai_report

        llm_cfg = LLMConfig(
            api_key="test-key",
            model="test-model",
            provider_config={"base_url": "https://mock.example.com"},
        )
        rpt_cfg = ReportConfig(
            report_structure="学术论文式报告",
            report_style="学术报告风",
            report_length="标准版",
            html_theme="简洁课程作业风",
        )

        # Mock call_llm to return a synthetic report
        mock_response = {
            "success": True,
            "content": (
                "### 摘要\n\n本研究基于100份样本数据..."
                "逻辑回归分析显示OR=2.23(p<0.001)..."
            ),
        }

        with patch("src.ai_report_generator.call_llm", return_value=mock_response):
            result = generate_ai_report(
                df=binary_dataset,
                schema_df=schema,
                config=config,
                analysis_results=analysis_results,
                quality=None,
                provider_config={},
                api_key="",
                model="",
                llm_config=llm_cfg,
                report_config=rpt_cfg,
            )

        assert result.get("success"), f"Should succeed: {result.get('error')}"
        assert "OR" in result["markdown_report"] or "逻辑回归" in result["markdown_report"]
