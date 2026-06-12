"""Configuration data classes for LLM and Report settings.

Reduces parameter threading across generate_ai_report → generate_literature_review
→ call_llm by bundling settings into typed objects.

Backward-compatible: existing functions with flat parameter lists continue to work;
new code can pass LLMConfig/ReportConfig instead.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ================================================================
# LLM Config
# ================================================================

@dataclass
class LLMConfig:
    """LLM provider and request configuration.

    Bundles the 8+ parameters that were previously threaded through
    multiple function signatures.
    """

    provider_config: Dict[str, str] = field(default_factory=dict)
    api_key: str = ""
    model: str = ""
    provider_key: str = ""
    chat_path: str = "/chat/completions"
    temperature: float = 0.3
    max_tokens: int = 4096
    extra_headers: Optional[Dict[str, str]] = None

    @classmethod
    def from_legacy_kwargs(cls, **kwargs) -> "LLMConfig":
        """Build LLMConfig from old-style flat parameter names.

        Handles both the 'provider_config/api_key/model/...' naming
        and the 'llm_provider_config/llm_api_key/llm_model/...' naming
        used in generate_literature_review().
        """
        return cls(
            provider_config=kwargs.get("provider_config")
            or kwargs.get("llm_provider_config", {}),
            api_key=kwargs.get("api_key")
            or kwargs.get("llm_api_key", ""),
            model=kwargs.get("model")
            or kwargs.get("llm_model", ""),
            provider_key=kwargs.get("provider_key")
            or kwargs.get("llm_provider_key", ""),
            chat_path=kwargs.get("chat_path")
            or kwargs.get("llm_chat_path", "/chat/completions"),
            temperature=kwargs.get("temperature")
            or kwargs.get("llm_temperature", 0.3),
            max_tokens=kwargs.get("max_tokens")
            or kwargs.get("llm_max_tokens", 4096),
            extra_headers=kwargs.get("extra_headers"),
        )

    def to_kwargs(self) -> Dict[str, Any]:
        """Convert to flat kwargs dict for call_llm / test_connection."""
        return {
            "provider_config": self.provider_config,
            "api_key": self.api_key,
            "model": self.model,
            "provider_key": self.provider_key,
            "chat_path": self.chat_path,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "extra_headers": self.extra_headers,
        }

    def to_legacy_kwargs(self) -> Dict[str, Any]:
        """Convert to old-style flat kwargs (provider_config, api_key, model, ...)."""
        return self.to_kwargs()

    def to_lit_review_kwargs(self) -> Dict[str, Any]:
        """Convert to generate_literature_review parameter names."""
        return {
            "llm_provider_config": self.provider_config,
            "llm_api_key": self.api_key,
            "llm_model": self.model,
            "llm_provider_key": self.provider_key,
            "llm_chat_path": self.chat_path,
            "llm_temperature": self.temperature,
            "llm_max_tokens": self.max_tokens,
            "extra_headers": self.extra_headers,
        }

    def merge_with(self, overrides: Dict[str, Any]) -> "LLMConfig":
        """Return a new LLMConfig with specified fields overridden."""
        d = {
            "provider_config": self.provider_config,
            "api_key": self.api_key,
            "model": self.model,
            "provider_key": self.provider_key,
            "chat_path": self.chat_path,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "extra_headers": self.extra_headers,
        }
        d.update({k: v for k, v in overrides.items() if v})
        return LLMConfig(**d)


# ================================================================
# Report Config
# ================================================================

@dataclass
class ReportConfig:
    """Report generation configuration.

    Bundles structure, style, length, and enrichment settings that
    were previously scattered across individual parameters.
    """

    report_structure: str = "通用调研报告"
    report_style: str = "学术报告风"
    report_length: str = "标准版"
    html_theme: str = "简洁课程作业风"

    # Enrichment flags
    literature_enabled: bool = False
    background_enabled: bool = False

    # Enrichment details (set separately when enabled)
    literature_keywords: str = ""
    literature_max_sources: int = 15
    literature_year_range: str = "不限"
    background_source_path: str = ""

    @classmethod
    def from_legacy_kwargs(cls, **kwargs) -> "ReportConfig":
        """Build ReportConfig from old-style flat parameters."""
        return cls(
            report_structure=kwargs.get("report_structure", "通用调研报告"),
            report_style=kwargs.get("report_style", "学术报告风"),
            report_length=kwargs.get("report_length", "标准版"),
            html_theme=kwargs.get("html_theme", "简洁课程作业风"),
            literature_enabled=kwargs.get("literature_config", {}).get("enabled", False)
            if isinstance(kwargs.get("literature_config"), dict) else False,
            background_enabled=kwargs.get("background_config", {}).get("enabled", False)
            if isinstance(kwargs.get("background_config"), dict) else False,
            literature_keywords=kwargs.get("literature_config", {}).get("keywords", "")
            if isinstance(kwargs.get("literature_config"), dict) else "",
            literature_max_sources=kwargs.get("literature_config", {}).get("max_sources", 15)
            if isinstance(kwargs.get("literature_config"), dict) else 15,
            literature_year_range=kwargs.get("literature_config", {}).get("year_range", "不限")
            if isinstance(kwargs.get("literature_config"), dict) else "不限",
            background_source_path=kwargs.get("background_config", {}).get("source_path", "")
            if isinstance(kwargs.get("background_config"), dict) else "",
        )

    def validate(self) -> List[str]:
        """Validate against report_options. Returns list of error messages."""
        from src.report_options import (
            REPORT_STRUCTURE_KEYS, REPORT_STYLE_KEYS,
            REPORT_LENGTH_KEYS, HTML_THEME_KEYS,
        )
        errors = []
        if self.report_structure not in REPORT_STRUCTURE_KEYS:
            errors.append(
                f"无效的报告结构「{self.report_structure}」，"
                f"可选: {REPORT_STRUCTURE_KEYS}"
            )
        if self.report_style not in REPORT_STYLE_KEYS:
            errors.append(
                f"无效的写作风格「{self.report_style}」，"
                f"可选: {REPORT_STYLE_KEYS}"
            )
        if self.report_length not in REPORT_LENGTH_KEYS:
            errors.append(
                f"无效的报告长度「{self.report_length}」，"
                f"可选: {REPORT_LENGTH_KEYS}"
            )
        if self.html_theme not in HTML_THEME_KEYS:
            errors.append(
                f"无效的 HTML 主题「{self.html_theme}」，"
                f"可选: {HTML_THEME_KEYS}"
            )
        return errors

    def to_literature_config(self) -> Dict[str, Any]:
        """Build literature_config dict for generate_ai_report."""
        if not self.literature_enabled:
            return {"enabled": False}
        return {
            "enabled": True,
            "keywords": self.literature_keywords,
            "max_sources": self.literature_max_sources,
            "year_range": self.literature_year_range,
        }

    def to_background_config(self) -> Dict[str, Any]:
        """Build background_config dict for generate_ai_report."""
        if not self.background_enabled:
            return {"enabled": False}
        return {
            "enabled": True,
            "source_path": self.background_source_path,
        }


# ================================================================
# Prompt Section (for unified context injection)
# ================================================================

@dataclass
class PromptSection:
    """A section of content to inject into an LLM prompt.

    Supports priority ordering: higher priority sections appear first.
    Skip injection: set content to empty string or None.

    Sections with the same key are deduplicated (highest priority kept).
    """

    key: str                          # unique key (dedup: higher priority wins)
    title: str                        # section heading (e.g. "⚠️ 条件提示")
    content: str = ""                 # body content (empty → skip injection)
    priority: int = 0                 # higher = injected earlier in prompt
    instructions: str = ""            # optional inline instructions for the LLM

    def is_empty(self) -> bool:
        return not bool(self.content)


def inject_prompt_sections(
    base_prompt: str,
    sections: List[PromptSection],
    separator: str = "\n---\n",
) -> str:
    """Inject PromptSection list into a base prompt, sorted by priority desc.

    Deduplication: if multiple sections share the same key, only the one
    with the highest priority is kept.

    Empty-content sections are silently skipped.

    Args:
        base_prompt: The prompt text to inject into.
        sections: Ordered list of PromptSection objects.
        separator: Separator between injected sections.

    Returns:
        The base prompt with sections appended in priority order.
    """
    if not sections:
        return base_prompt

    # Deduplicate by key: keep highest priority
    seen: Dict[str, PromptSection] = {}
    for sec in sections:
        if sec.is_empty():
            continue
        existing = seen.get(sec.key)
        if existing is None or sec.priority > existing.priority:
            seen[sec.key] = sec

    # Sort by priority descending
    ordered = sorted(seen.values(), key=lambda s: -s.priority)

    parts = [base_prompt]
    for sec in ordered:
        block = f"\n## {sec.title}\n\n"
        if sec.instructions:
            block += f"{sec.instructions}\n\n"
        block += f"{sec.content}\n"
        block += separator
        parts.append(block)

    return "".join(parts)
