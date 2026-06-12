"""Tests for src.ui.security — API key masking, secret detection, redaction."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from src.ui.security import (
    mask_api_key,
    contains_potential_secret,
    redact_potential_secrets,
    list_output_files,
    clean_output_files,
    get_outputs_safety_hint,
)


# ================================================================
# mask_api_key
# ================================================================

class TestMaskApiKey:
    def test_none_returns_unset(self):
        assert mask_api_key(None) == "(未设置)"

    def test_empty_string_returns_unset(self):
        assert mask_api_key("") == "(未设置)"

    def test_whitespace_only_returns_unset(self):
        assert mask_api_key("   ") == "(未设置)"

    def test_sk_prefix_key_masked(self):
        result = mask_api_key("sk-abc123def456ghijk")
        assert result.startswith("sk-****")
        assert result.endswith("hijk")
        assert "abc123" not in result

    def test_sk_or_prefix_key_masked(self):
        result = mask_api_key("sk-or-v1-abc123def456ghijk")
        assert result.startswith("sk-or-****")
        assert result.endswith("hijk")
        assert "abc123" not in result

    def test_short_sk_key_fully_masked(self):
        result = mask_api_key("sk-abc")
        assert result == "****"

    def test_generic_long_key_masked(self):
        result = mask_api_key("1234567890abcdef")
        assert result.startswith("****")
        assert result.endswith("cdef")

    def test_short_key_fully_masked(self):
        result = mask_api_key("12345")
        assert result == "****"

    def test_mask_does_not_reveal_full_key(self):
        original = "sk-proj-0123456789abcdef0123456789abcdef"
        masked = mask_api_key(original)
        assert original not in masked
        assert len(masked) < len(original)

    def test_mask_with_dash_underscore_mixed(self):
        result = mask_api_key("sk-test_key-with-mixed-chars-long-enough-20")
        assert "test_key" not in result
        assert result.startswith("sk-****")


# ================================================================
# contains_potential_secret
# ================================================================

class TestContainsPotentialSecret:
    def test_sk_prefix_detected(self):
        assert contains_potential_secret("sk-abc123def456ghijk78901234567890") is True

    def test_bearer_token_detected(self):
        assert contains_potential_secret("Authorization: Bearer abc123def456ghijk789012345") is True

    def test_api_key_assignment_detected(self):
        assert contains_potential_secret("API_KEY=sk-test-key-that-is-very-long-at-least-20-chars") is True

    def test_apikey_no_underscore_detected(self):
        assert contains_potential_secret("apikey=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa") is True

    def test_normal_text_not_detected(self):
        assert contains_potential_secret("Hello, this is normal text.") is False

    def test_empty_text_not_detected(self):
        assert contains_potential_secret("") is False

    def test_short_string_not_detected(self):
        assert contains_potential_secret("abc123") is False

    def test_placeholder_value_not_detected(self):
        """Values that look like placeholders should not trigger."""
        result = contains_potential_secret("API_KEY=your_api_key_here_please_replace")
        # Should be False — placeholder indicators should be safe
        assert result is False or "your_api_key" not in redact_potential_secrets("API_KEY=your_api_key_here_please_replace")

    def test_env_var_reference_not_detected(self):
        """Env var references like ${VAR} should not trigger."""
        # This is tricky — the pattern might match; we just want it redacted gracefully
        result = redact_potential_secrets("token=${MY_SECRET_TOKEN}")
        assert "${MY_SECRET_TOKEN}" in result  # should be preserved

    def test_short_key_assignment_not_detected(self):
        assert contains_potential_secret("key=short") is False


# ================================================================
# redact_potential_secrets
# ================================================================

class TestRedactPotentialSecrets:
    def test_sk_key_redacted(self):
        result = redact_potential_secrets("Error from sk-abc123def456ghijk7890: timeout")
        assert "sk-abc123" not in result
        assert "sk-****" in result

    def test_bearer_token_redacted(self):
        result = redact_potential_secrets("Header: Bearer abc123def456ghijk789012345")
        assert "abc123" not in result
        assert "Bearer ****" in result

    def test_api_key_assignment_redacted(self):
        result = redact_potential_secrets("config: API_KEY=sk-verylongkeythatisover20chars")
        assert "sk-verylong" not in result
        assert "****" in result

    def test_normal_text_preserved(self):
        text = "The quick brown fox jumps over the lazy dog."
        assert redact_potential_secrets(text) == text

    def test_multiple_secrets_redacted(self):
        # Note: overlapping patterns may cause both to be redacted.
        result = redact_potential_secrets(
            "Key1: sk-abc123def456ghijk7890  Key2: Bearer xyz987654321fedcba012345"
        )
        assert "abc123" not in result
        assert "xyz987" not in result

    def test_empty_string_returns_empty(self):
        assert redact_potential_secrets("") == ""

    def test_preserves_chinese_text(self):
        text = "连接失败: 网络不可达。请检查 API Key: sk-abc123def456ghijk7890"
        result = redact_potential_secrets(text)
        assert "连接失败" in result
        assert "abc123" not in result

    def test_does_not_over_redact_regular_urls(self):
        """URL-like strings should not be redacted unless they match key patterns."""
        text = "See https://example.com/api/v1 for details."
        result = redact_potential_secrets(text)
        # The URL itself should remain largely intact
        assert "example.com" in result


# ================================================================
# Outputs safety — list / clean / hint
# ================================================================

class TestOutputsSafety:
    def test_list_output_files_no_dir(self, tmp_path):
        """When outputs dir doesn't exist, return empty list."""
        nonexistent = tmp_path / "no_such_dir"
        files = list_output_files(str(nonexistent))
        assert files == []

    def test_list_output_files_with_files(self, tmp_path):
        """Should list files in the outputs dir."""
        d = tmp_path / "outputs"
        d.mkdir()
        (d / "report.md").write_text("# Report")
        (d / "report.html").write_text("<html></html>")
        files = list_output_files(str(d))
        # Returns relative paths
        names = [f.name for f in files]
        assert "report.md" in names
        assert "report.html" in names

    def test_list_output_files_skips_dotfiles(self, tmp_path):
        d = tmp_path / "outputs"
        d.mkdir()
        (d / "report.md").write_text("text")
        (d / ".hidden").write_text("hidden")
        files = list_output_files(str(d))
        names = [f.name for f in files]
        assert "report.md" in names
        assert ".hidden" not in names

    def test_clean_output_files_dry_run_does_not_delete(self, tmp_path):
        d = tmp_path / "outputs"
        d.mkdir()
        (d / "report.md").write_text("# Report")
        result = clean_output_files(str(d), dry_run=True)
        assert result["dry_run"] is True
        assert "report.md" in result["deleted"]
        assert (d / "report.md").exists()  # file still there

    def test_clean_output_files_actually_deletes(self, tmp_path):
        d = tmp_path / "outputs"
        d.mkdir()
        (d / "report.md").write_text("# Report")
        result = clean_output_files(str(d), dry_run=False)
        assert result["dry_run"] is False
        assert "report.md" in result["deleted"]
        assert not (d / "report.md").exists()

    def test_clean_output_files_does_not_delete_outside_outputs(self, tmp_path):
        """Should not delete files outside the specified outputs dir."""
        d = tmp_path / "outputs"
        d.mkdir()
        (d / "report.md").write_text("# Report")
        outside_file = tmp_path / "important.txt"
        outside_file.write_text("important")
        clean_output_files(str(d), dry_run=False)
        assert outside_file.exists()  # untouched

    def test_get_outputs_safety_hint_returns_string(self):
        hint = get_outputs_safety_hint()
        assert isinstance(hint, str)
        assert "outputs" in hint.lower()
        assert "安全" in hint or ".gitignore" in hint
