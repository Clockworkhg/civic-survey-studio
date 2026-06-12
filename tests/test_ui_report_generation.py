"""Tests for src/ui/report_generation.py — config builders and run helper."""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBuildLLMConfigFromUI:
    """Test build_llm_config_from_ui()."""

    def test_defaults(self):
        from src.ui.report_generation import build_llm_config_from_ui
        cfg = build_llm_config_from_ui(
            provider_config={"base_url": "https://api.example.com"},
            api_key="sk-test",
            model="test-model",
        )
        assert cfg.api_key == "sk-test"
        assert cfg.model == "test-model"
        assert cfg.provider_config == {"base_url": "https://api.example.com"}
        assert cfg.temperature == 0.3
        assert cfg.max_tokens == 4096
        assert cfg.provider_key == ""
        assert cfg.chat_path == "/chat/completions"

    def test_full_params(self):
        from src.ui.report_generation import build_llm_config_from_ui
        cfg = build_llm_config_from_ui(
            provider_config={"base_url": "https://custom.api.com", "protocol": "custom_openai_compatible"},
            api_key="sk-custom",
            model="custom-model",
            provider_key="custom_provider",
            temperature=0.7,
            max_tokens=2048,
            chat_path="/custom/chat",
        )
        assert cfg.api_key == "sk-custom"
        assert cfg.model == "custom-model"
        assert cfg.provider_key == "custom_provider"
        assert cfg.temperature == 0.7
        assert cfg.max_tokens == 2048
        assert cfg.chat_path == "/custom/chat"

    def test_to_kwargs_roundtrip(self):
        """LLMConfig built from UI should produce valid call_llm kwargs."""
        from src.ui.report_generation import build_llm_config_from_ui
        cfg = build_llm_config_from_ui(
            provider_config={"base_url": "https://api.example.com"},
            api_key="sk-kw",
            model="kw-model",
        )
        kwargs = cfg.to_kwargs()
        assert kwargs["provider_config"] == {"base_url": "https://api.example.com"}
        assert kwargs["api_key"] == "sk-kw"
        assert kwargs["model"] == "kw-model"
        assert kwargs["temperature"] == 0.3
        assert kwargs["max_tokens"] == 4096


class TestBuildReportConfigFromUI:
    """Test build_report_config_from_ui()."""

    def test_defaults(self):
        from src.ui.report_generation import build_report_config_from_ui
        cfg = build_report_config_from_ui()
        assert cfg.report_structure == "通用调研报告"
        assert cfg.report_style == "学术报告风"
        assert cfg.report_length == "标准版"
        assert cfg.html_theme == "简洁课程作业风"
        assert cfg.literature_enabled is False
        assert cfg.background_enabled is False

    def test_full_params_with_literature_and_background(self):
        from src.ui.report_generation import build_report_config_from_ui
        cfg = build_report_config_from_ui(
            report_structure="学术论文式报告",
            report_style="学术报告风",
            report_length="详细版",
            html_theme="政务蓝白汇报风",
            literature_enabled=True,
            literature_keywords="满意度 调查",
            literature_max_sources=20,
            literature_year_range="近10年",
            background_enabled=True,
            background_source_path="bg/test",
        )
        assert cfg.report_structure == "学术论文式报告"
        assert cfg.literature_enabled is True
        assert cfg.literature_keywords == "满意度 调查"
        assert cfg.literature_max_sources == 20
        assert cfg.literature_year_range == "近10年"
        assert cfg.background_enabled is True
        assert cfg.background_source_path == "bg/test"

    def test_validate_valid_config(self):
        """Valid config should pass validate() with no errors."""
        from src.ui.report_generation import build_report_config_from_ui
        cfg = build_report_config_from_ui(
            report_structure="学术论文式报告",
            report_style="学术报告风",
            report_length="标准版",
            html_theme="简洁课程作业风",
        )
        errors = cfg.validate()
        assert errors == []

    def test_validate_invalid_structure(self):
        """Invalid structure should be caught by validate()."""
        from src.ui.report_generation import build_report_config_from_ui
        cfg = build_report_config_from_ui(
            report_structure="不存在的结构",
        )
        errors = cfg.validate()
        assert len(errors) >= 1

    def test_to_literature_config_disabled(self):
        """When literature is disabled, to_literature_config returns disabled."""
        from src.ui.report_generation import build_report_config_from_ui
        cfg = build_report_config_from_ui(literature_enabled=False)
        lit = cfg.to_literature_config()
        assert lit == {"enabled": False}

    def test_to_literature_config_enabled(self):
        """When literature is enabled, to_literature_config returns full config."""
        from src.ui.report_generation import build_report_config_from_ui
        cfg = build_report_config_from_ui(
            literature_enabled=True,
            literature_keywords="测试",
            literature_max_sources=10,
            literature_year_range="近5年",
        )
        lit = cfg.to_literature_config()
        assert lit["enabled"] is True
        assert lit["keywords"] == "测试"
        assert lit["max_sources"] == 10
        assert lit["year_range"] == "近5年"


class TestRunReportGenerationFromUI:
    """Test run_report_generation_from_ui()."""

    def test_passes_llm_config_and_report_config(self):
        """Should call generate_ai_report with the provided config objects."""
        import pandas as pd
        from src.config_models import LLMConfig, ReportConfig

        llm_cfg = LLMConfig(
            provider_config={"base_url": "https://test.api.com"},
            api_key="sk",
            model="m",
        )
        rpt_cfg = ReportConfig(report_structure="通用调研报告")

        df = pd.DataFrame({"a": [1, 2, 3]})
        schema = pd.DataFrame([{"column": "a", "inferred_type": "numeric"}])
        config = {"report_title": "T", "target_variable": "a"}
        analysis = {"univariate": [], "bivariate": [], "multivariate": None}
        quality = {"样本量": 3}

        mock_response = {
            "success": True,
            "markdown_report": "report",
            "html_report": "<html>",
            "docx_report": b"",
            "llm_response": {},
            "error": "",
            "warnings": [],
        }

        with patch("src.ui.report_generation.generate_ai_report") as mock_gen:
            mock_gen.return_value = mock_response
            from src.ui.report_generation import run_report_generation_from_ui
            result = run_report_generation_from_ui(
                df=df,
                schema_df=schema,
                config=config,
                analysis_results=analysis,
                quality=quality,
                llm_config=llm_cfg,
                report_config=rpt_cfg,
            )

        assert result["success"] is True
        # Verify generate_ai_report was called with config objects
        call_kwargs = mock_gen.call_args[1]
        assert call_kwargs["llm_config"] is llm_cfg
        assert call_kwargs["report_config"] is rpt_cfg
        assert call_kwargs["df"] is df
        assert call_kwargs["schema_df"] is schema

    def test_does_not_call_run_full_analysis(self):
        """run_report_generation_from_ui should NOT run full_analysis."""
        import pandas as pd
        from src.config_models import LLMConfig, ReportConfig

        llm_cfg = LLMConfig(
            provider_config={"base_url": "https://test.api.com"},
            api_key="sk",
            model="m",
        )
        rpt_cfg = ReportConfig()

        df = pd.DataFrame({"a": [1, 2]})
        schema = pd.DataFrame([{"column": "a", "inferred_type": "numeric"}])
        config = {"report_title": "T"}

        with patch("src.ui.report_generation.generate_ai_report") as mock_gen:
            mock_gen.return_value = {"success": True, "markdown_report": "x"}
            from src.ui.report_generation import run_report_generation_from_ui
            run_report_generation_from_ui(
                df=df, schema_df=schema, config=config,
                analysis_results={}, quality=None,
                llm_config=llm_cfg, report_config=rpt_cfg,
            )
            # Should have called generate_ai_report exactly once
            mock_gen.assert_called_once()
