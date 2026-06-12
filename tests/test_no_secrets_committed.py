"""Secrets scan: confirm no real API keys or tokens are committed to the repo.

This test walks all text files in the project, skipping vendored / generated /
cache directories, and checks that no line contains a pattern that looks like
a real API key or token.
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from src.ui.security import mask_api_key


ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Directories to skip entirely
SKIP_DIRS = {
    ".venv", ".venv-test", "venv", "env",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".git", ".vscode", ".idea",
    "outputs",  # generated reports — may contain sensitive content
    ".cache",
}

# File extensions to scan (text files only)
SCAN_EXTENSIONS = {
    ".py", ".md", ".yml", ".yaml", ".toml",
    ".txt", ".csv", ".json", ".bat", ".sh",
    ".cfg", ".ini", ".example",
}

# Patterns that indicate a potential REAL secret (not placeholder/template).
# These are stricter than src.ui.security._SECRET_PATTERNS — they only
# match what looks like an actual committed credential.
#
# We use negative lookaheads to exclude placeholder values.
REAL_SECRET_PATTERNS = [
    # sk-... with substantial entropy (≥28 chars total: "sk-" + 25 alphanum)
    re.compile(r'sk-[A-Za-z0-9_\-]{25,}'),
    # sk-or-... with substantial entropy
    re.compile(r'sk-or-[A-Za-z0-9_\-]{25,}'),
    # Bearer token — 30+ alphanumeric chars (appearing in a non-comment line)
    re.compile(r'Bearer\s+[A-Za-z0-9_\-.]{30,}'),
    # API_KEY=<value that looks like a real token: starts with sk- or is long hex/b64>
    re.compile(
        r'(?i)'
        r'(?:OPENAI_API_KEY|DEEPSEEK_API_KEY|MOONSHOT_API_KEY|SILICONFLOW_API_KEY|'
        r'ANTHROPIC_API_KEY|GOOGLE_API_KEY|CUSTOM_API_KEY)'
        r'\s*=\s*[\'"]?(sk-[A-Za-z0-9_\-]{8,}|\S{20,})[\'"]?'
    ),
]

# Allow-list: files that may contain "secrets-like" strings that are
# actually safe (test fixtures, example code, etc.).
# Paths are relative to project root.
ALLOW_FILES_WITH_SECRETS = {
    # Tests that deliberately use fake keys
    "tests/test_security_utils.py",
    "tests/test_no_secrets_committed.py",
    # Security module that defines patterns
    "src/ui/security.py",
    # Documentation showing placeholder keys as examples
    "AI_USAGE.md",
    "docs/security.md",
}


def _is_allowed(path: Path) -> bool:
    rel = str(path.relative_to(ROOT).as_posix())
    return rel in ALLOW_FILES_WITH_SECRETS


def _should_skip(path: Path) -> bool:
    """Check if a path should be skipped."""
    rel = path.relative_to(ROOT)
    parts = rel.parts
    for part in parts:
        if part in SKIP_DIRS:
            return True
    return False


def _collect_files() -> list:
    """Collect all scan-able text files in the repo."""
    files = []
    for root, dirs, filenames in os.walk(str(ROOT)):
        # Prune skipped directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        root_path = Path(root)
        for fname in filenames:
            fpath = root_path / fname
            if _should_skip(fpath):
                continue
            ext = fpath.suffix.lower()
            if ext in SCAN_EXTENSIONS or fname in SCAN_EXTENSIONS:
                files.append(fpath)
    return sorted(files)


class TestNoSecretsCommitted:
    """Scan the entire repo for committed API keys and tokens."""

    def test_no_sk_keys_in_source(self):
        """No source file should contain an 'sk-' prefixed key with ≥25 chars."""
        violations = []
        for fpath in _collect_files():
            if _is_allowed(fpath):
                continue
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for line_no, line in enumerate(content.splitlines(), 1):
                for pat in REAL_SECRET_PATTERNS:
                    match = pat.search(line)
                    if match:
                        matched = match.group(0).strip()
                        # Skip if it's in a comment
                        stripped = line.strip()
                        if stripped.startswith("#") or stripped.startswith("//"):
                            continue
                        # Mask for safe reporting
                        masked = mask_api_key(matched)
                        rel = fpath.relative_to(ROOT)
                        violations.append(f"{rel}:{line_no} → {masked}")
                        break  # one violation per line is enough

        if violations:
            pytest.fail(
                f"Found {len(violations)} potential secret(s) in source files:\n"
                + "\n".join(f"  • {v}" for v in violations[:20])
                + ("\n  … and more" if len(violations) > 20 else "")
            )

    def test_no_bearer_tokens_in_source(self):
        """No source file should contain a Bearer token with ≥30 chars."""
        this_file = Path(__file__).resolve()
        violations = []
        for fpath in _collect_files():
            if _is_allowed(fpath):
                continue
            # Skip the patterns defined in security.py (they contain regex-like patterns)
            if fpath.resolve() == this_file:
                continue
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            bearer_pat = re.compile(r'Bearer\s+([A-Za-z0-9_\-.]{30,})')
            for line_no, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith("//"):
                    continue
                match = bearer_pat.search(line)
                if match:
                    matched = match.group(0)
                    rel = fpath.relative_to(ROOT)
                    violations.append(f"{rel}:{line_no} → {mask_api_key(matched)}")

        if violations:
            pytest.fail(
                f"Found Bearer token(s) in source files:\n"
                + "\n".join(f"  • {v}" for v in violations)
            )

    def test_env_example_has_no_real_values(self):
        """.env.example should have empty values for API keys."""
        env_example = ROOT / ".env.example"
        if not env_example.exists():
            pytest.skip(".env.example not found")
            return

        content = env_example.read_text(encoding="utf-8")
        violations = []
        for line_no, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" in stripped:
                key, value = stripped.split("=", 1)
                value = value.strip()
                key_upper = key.strip().upper()
                # Check if this is a known API key env var with a real value
                known_key_vars = {
                    "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "MOONSHOT_API_KEY",
                    "SILICONFLOW_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY",
                    "CUSTOM_API_KEY",
                }
                if key_upper in known_key_vars and value:
                    if len(value) > 8:
                        violations.append(
                            f"Line {line_no}: {key}={mask_api_key(value)} (value too long for placeholder)"
                        )

        if violations:
            pytest.fail(
                ".env.example contains values that look like real API keys:\n"
                + "\n".join(f"  • {v}" for v in violations)
            )

    def test_no_env_file_committed(self):
        """The .env file should NOT exist in the repo (must be .gitignored)."""
        env_file = ROOT / ".env"
        if env_file.exists():
            # Check .gitignore covers it
            gitignore = ROOT / ".gitignore"
            if gitignore.exists():
                gi_content = gitignore.read_text(encoding="utf-8")
                if ".env" in gi_content:
                    # It's gitignored, but still warn
                    pytest.fail(
                        ".env file exists in the repository. "
                        "While it is gitignored, it should not be present in "
                        "the working tree. Consider deleting it and using "
                        ".env.example as a template."
                    )
                else:
                    pytest.fail(
                        "CRITICAL: .env file exists and is NOT gitignored! "
                        "This may expose your API keys."
                    )

    def test_streamlit_secrets_not_committed(self):
        """The .streamlit/secrets.toml file should NOT exist."""
        secrets_file = ROOT / ".streamlit" / "secrets.toml"
        if secrets_file.exists():
            pytest.fail(
                ".streamlit/secrets.toml exists. "
                "It is gitignored but may contain real API keys. "
                "Delete it before publishing."
            )

    def test_example_data_no_real_secrets(self):
        """Example CSV files should not contain real API keys."""
        examples_dir = ROOT / "examples"
        if not examples_dir.is_dir():
            return

        for csv_file in examples_dir.glob("*.csv"):
            content = csv_file.read_text(encoding="utf-8-sig", errors="replace")
            # Look for sk- patterns
            sk_pat = re.compile(r'sk-[A-Za-z0-9_\-]{20,}')
            match = sk_pat.search(content)
            if match:
                pytest.fail(
                    f"{csv_file.name} contains an sk- token: "
                    f"{mask_api_key(match.group(0))}"
                )

    def test_gitignore_covers_outputs(self):
        """Verify .gitignore still covers outputs/."""
        gitignore = ROOT / ".gitignore"
        assert gitignore.exists(), ".gitignore not found"
        content = gitignore.read_text(encoding="utf-8")
        assert "outputs/" in content or "outputs" in content.splitlines(), (
            ".gitignore should contain 'outputs/'"
        )

    def test_gitignore_covers_env(self):
        """Verify .gitignore covers .env."""
        gitignore = ROOT / ".gitignore"
        content = gitignore.read_text(encoding="utf-8")
        assert ".env" in content.splitlines() or any(
            ".env" in line for line in content.splitlines()
        ), ".gitignore should contain '.env'"
