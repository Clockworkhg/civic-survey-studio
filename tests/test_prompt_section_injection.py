"""Tests for unified prompt section injection (P1.6: now uses PromptSection / inject_prompt_sections)."""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config_models import PromptSection, inject_prompt_sections


class TestInjectPromptSections:
    """Test the inject_prompt_sections() API that replaced _inject_section()."""

    def test_injects_when_content_provided(self):
        """Content should be injected into the base prompt."""
        base = "请写一份报告。"
        sections = [
            PromptSection(key="lit", title="⚠️ 预生成文献综述",
                          content="文献综述内容...",
                          instructions="请使用此内容。",
                          priority=10),
        ]
        result = inject_prompt_sections(base, sections)
        assert "⚠️ 预生成文献综述" in result
        assert "文献综述内容..." in result
        assert "请使用此内容。" in result
        assert result.startswith("请写一份报告。")

    def test_skips_when_content_empty(self):
        """Empty content should be silently skipped."""
        base = "请写一份报告。"
        sections = [
            PromptSection(key="lit", title="⚠️ 标题",
                          content="",
                          instructions="指令。",
                          priority=10),
        ]
        result = inject_prompt_sections(base, sections)
        assert result == base

    def test_skips_when_content_none(self):
        """None-ish content should be silently skipped."""
        base = "请写一份报告。"
        sections = [
            PromptSection(key="lit", title="⚠️ 标题",
                          content="",  # Empty string triggers is_empty()
                          instructions="指令。",
                          priority=10),
        ]
        result = inject_prompt_sections(base, sections)
        assert result == base

    def test_multiple_injections_appended_in_priority_order(self):
        """Higher priority sections should appear before lower priority ones."""
        base = "请写报告。"
        sections = [
            PromptSection(key="bg", title="背景", content="材料A",
                          instructions="使用背景。", priority=20),
            PromptSection(key="lit", title="文献", content="材料B",
                          instructions="使用文献。", priority=10),
        ]
        result = inject_prompt_sections(base, sections)
        idx_a = result.index("背景")
        idx_b = result.index("文献")
        assert idx_a < idx_b  # Higher priority (20) before lower (10)

    def test_preserves_original_prompt_structure(self):
        """Base prompt should be preserved as-is, sections appended after."""
        base = "## 分析结果\n\n{json_data}\n\n请开始撰写。"
        sections = [
            PromptSection(key="bg", title="⚠️ 背景", content="额外的背景。",
                          instructions="参考。", priority=10),
        ]
        result = inject_prompt_sections(base, sections)
        assert base in result  # Original prompt preserved
        assert result.endswith("---\n")

    def test_dedup_keeps_higher_priority(self):
        """Duplicate keys: only the highest priority section is kept."""
        base = "请写报告。"
        sections = [
            PromptSection(key="note", title="Low", content="low content",
                          priority=1),
            PromptSection(key="note", title="High", content="high content",
                          priority=99),
        ]
        result = inject_prompt_sections(base, sections)
        assert "high content" in result
        assert "low content" not in result

    def test_no_sections_returns_base_unchanged(self):
        """Empty section list should return base prompt unchanged."""
        base = "请写报告。"
        result = inject_prompt_sections(base, [])
        assert result == base


class TestPromptSectionDataclass:
    """Verify PromptSection dataclass behavior."""

    def test_is_empty_with_empty_content(self):
        s = PromptSection(key="k", title="T", content="")
        assert s.is_empty() is True

    def test_is_empty_with_content(self):
        s = PromptSection(key="k", title="T", content="hello")
        assert s.is_empty() is False

    def test_defaults(self):
        s = PromptSection(key="k", title="T")
        assert s.content == ""
        assert s.priority == 0
        assert s.instructions == ""
        assert s.is_empty() is True
