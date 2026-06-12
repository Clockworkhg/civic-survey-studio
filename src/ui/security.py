"""Security utilities: API key masking, secrets scanning, outputs safety,
AI pre-generation privacy variable summary.

All functions are pure string / filesystem helpers — no Streamlit imports,
no business logic, no side effects (except clean_output_files when
dry_run=False).

Security note: These utilities help *detect* and *mask* potential secrets.
They do not replace good operational security practices: never commit .env,
never hardcode keys, and always review outputs/ before publishing.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

# ================================================================
# Paths
# ================================================================

_DEFAULT_OUTPUTS_DIR = Path(__file__).resolve().parent.parent.parent / "outputs"


# ================================================================
# API Key masking
# ================================================================

def mask_api_key(api_key: Optional[str]) -> str:
    """Return a masked version of *api_key*, safe for display in UI and logs.

    Rules (first match wins):
      - ``None`` or empty → ``"(未设置)"``
      - ``sk-...`` (≥12 chars) → ``sk-****abcd`` (last 4 chars preserved)
      - ``sk-or-...`` (≥16 chars) → ``sk-or-****abcd``
      - Anything ≥12 chars → ``****abcd`` (last 4 chars preserved)
      - Short values → ``****`` (fully masked)

    Examples:
        >>> mask_api_key("sk-abc123def456")
        'sk-****f456'
        >>> mask_api_key("sk-or-v1-abc123def456ghijk")
        'sk-or-****hijk'
        >>> mask_api_key("")
        '(未设置)'
    """
    if not api_key:
        return "(未设置)"

    key = str(api_key).strip()
    if not key:
        return "(未设置)"

    # sk-or-... pattern (e.g. OpenRouter)
    if key.startswith("sk-or-") and len(key) >= 16:
        return f"sk-or-****{key[-4:]}"

    # sk-... pattern (e.g. OpenAI, DeepSeek)
    if key.startswith("sk-") and len(key) >= 12:
        return f"sk-****{key[-4:]}"

    # Generic long key
    if len(key) >= 12:
        return f"****{key[-4:]}"

    # Short key — fully masked
    return "****"


# ================================================================
# Potential secret detection
# ================================================================

# Regex patterns for common secret / API key formats.
# These are deliberately broad to catch likely secrets, but they WILL
# match some false positives (long hex strings, UUIDs, etc.).
# Use `contains_potential_secret` for screening and `redact_potential_secrets`
# for sanitising text; always review results manually before publishing.

_SECRET_PATTERNS = [
    # sk-... (OpenAI, DeepSeek, OpenRouter, etc.) — 20+ alphanumeric/underscore/dash
    re.compile(r'sk-[A-Za-z0-9_\-]{20}[A-Za-z0-9_\-]*'),
    # Bearer token — 20+ alphanumeric/dash/dot/underscore
    re.compile(r'Bearer\s+[A-Za-z0-9_\-.]{20,}'),
    # API_KEY=... (any casing) — non-empty value that looks like a token (long)
    re.compile(r'(?i)API[_\s]?KEY[_\s]*=\s*[\'"]?([A-Za-z0-9_\-+/]{20,}={0,3})[\'"]?'),
    # Generic "key=long-alphanumeric-value"
    re.compile(r'(?i)(api_?key|secret|token|password)\s*[:=]\s*[\'"]?([^\s\'"]{20,})[\'"]?'),
]

# Safe patterns — common things that look like secrets but are not.
# When any of these match the *entire* potential match, skip it.
# IMPORTANT: Do NOT add generic words like "test" here — legitimate API keys
# sometimes contain "test" (e.g. sk-test-key...). Only match clear placeholder
# patterns.
_SAFE_OVERLAPS = [
    # Placeholder indicators at start of match
    re.compile(r'^(your[_\-]?|my[_\-]?|enter[_\-]?|<|\[|YOUR_)', re.IGNORECASE),
    re.compile(r'(placeholder|changeme|TODO|fill[_\-]?in)', re.IGNORECASE),
    # Environment variable references (${VAR} or %VAR%)
    re.compile(r'^\$\{[^}]+\}$'),
    re.compile(r'^%[^%]+%$'),
    # Relative paths or file references
    re.compile(r'^[./\\]'),
    # Short hex or numeric-only
    re.compile(r'^[0-9a-fA-F]{1,20}$'),
    # Common non-secret tokens in text — only when they are the dominant content
    re.compile(r'^(None|null|undefined|True|False)$'),
]


def contains_potential_secret(text: str) -> bool:
    """Check whether *text* contains a pattern that looks like an API key or token.

    Use for pre-flight checks before displaying or logging user input.
    Returns ``True`` if ANY of the secret patterns match.

    Args:
        text: Raw text to scan.

    Returns:
        ``True`` if a potential secret is detected.

    Examples:
        >>> contains_potential_secret("sk-abc123def456ghijk789012345")
        True
        >>> contains_potential_secret("Hello, world!")
        False
        >>> contains_potential_secret("API_KEY=sk-test-key-that-is-very-long-at-least-20-chars")
        True
    """
    if not text:
        return False

    for pat in _SECRET_PATTERNS:
        match = pat.search(text)
        if match:
            matched_str = match.group(0)
            # Check safety overlaps
            safe = False
            for safe_pat in _SAFE_OVERLAPS:
                if safe_pat.search(matched_str):
                    safe = True
                    break
            if not safe:
                return True

    return False


def redact_potential_secrets(text: str) -> str:
    """Replace potential secrets in *text* with masked placeholders.

    The redacted form is safe for logging, debugging, and error messages.
    Original surrounding text is preserved.

    Args:
        text: Text that may contain secrets.

    Returns:
        Same text with potential secrets replaced by ``sk-****...`` or similar.

    Examples:
        >>> redact_potential_secrets("Error from sk-abc123def456ghijk: timeout")
        'Error from sk-****hijk: timeout'
        >>> redact_potential_secrets("Normal text without secrets.")
        'Normal text without secrets.'
    """
    if not text:
        return text

    for pat in _SECRET_PATTERNS:
        def _replace(match: re.Match) -> str:
            full = match.group(0)
            # Check safety overlaps
            for safe_pat in _SAFE_OVERLAPS:
                if safe_pat.search(full):
                    return full  # keep as-is
            return _redact_match(full)
        text = pat.sub(_replace, text)

    return text


def _redact_match(matched: str) -> str:
    """Mask a single matched potential secret string."""
    # Bearer token
    if matched.lower().startswith("bearer "):
        rest = matched.split(" ", 1)[1] if " " in matched else matched[7:]
        if len(rest) >= 4:
            return f"Bearer ****{rest[-4:]}"
        return "Bearer ****"

    # API_KEY=... pattern
    if "=" in matched:
        parts = matched.split("=", 1)
        key_part = parts[0]
        val_part = parts[1].strip().strip("'\"")
        if len(val_part) >= 4:
            return f"{key_part}=****{val_part[-4:]}"
        return f"{key_part}=****"

    # api_key: pattern
    if ":" in matched:
        parts = matched.split(":", 1)
        key_part = parts[0]
        val_part = parts[1].strip().strip("'\"")
        if len(val_part) >= 4:
            return f"{key_part}: ****{val_part[-4:]}"
        return f"{key_part}: ****"

    # sk- / sk-or- pattern
    if matched.startswith("sk-or-") and len(matched) >= 16:
        return f"sk-or-****{matched[-4:]}"
    if matched.startswith("sk-") and len(matched) >= 12:
        return f"sk-****{matched[-4:]}"

    # Generic long value
    if len(matched) >= 12:
        return f"****{matched[-4:]}"

    return "****"


# ================================================================
# Outputs directory safety
# ================================================================

def list_output_files(outputs_dir: str = "") -> List[Path]:
    """List report / export files in the outputs directory.

    Args:
        outputs_dir: Path to outputs directory. Defaults to project ``outputs/``.

    Returns:
        Sorted list of ``Path`` objects (relative).  Returns empty list if the
        directory does not exist.
    """
    d = Path(outputs_dir) if outputs_dir else _DEFAULT_OUTPUTS_DIR
    d = d.resolve()
    if not d.is_dir():
        return []

    files: List[Path] = []
    for child in sorted(d.iterdir()):
        if child.is_file() and not child.name.startswith("."):
            files.append(child.relative_to(d))
    return files


def clean_output_files(
    outputs_dir: str = "",
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Delete files in the outputs directory.

    **This function deletes files.**  It always requires explicit ``dry_run=False``
    to perform actual deletion.  The default ``dry_run=True`` only lists what
    *would* be deleted.

    Safety guarantees:
      - Only deletes files inside the outputs directory (no recursive or parent traversal).
      - Skips dotfiles and directories.
      - Returns the list of files deleted (or would-be-deleted).

    Args:
        outputs_dir: Path to outputs directory.  Defaults to project ``outputs/``.
        dry_run: If ``True`` (default), only list files without deleting.

    Returns:
        ``{"dry_run": bool, "deleted": list[str], "total_size_kb": float}``
    """
    d = Path(outputs_dir) if outputs_dir else _DEFAULT_OUTPUTS_DIR
    d = d.resolve()

    result: Dict[str, Any] = {
        "dry_run": dry_run,
        "deleted": [],
        "total_size_kb": 0.0,
    }

    if not d.is_dir():
        return result

    files_to_delete = [
        child for child in sorted(d.iterdir())
        if child.is_file() and not child.name.startswith(".")
    ]

    total_bytes = 0
    for f in files_to_delete:
        try:
            total_bytes += f.stat().st_size
        except OSError:
            pass
        result["deleted"].append(f.name)

    result["total_size_kb"] = round(total_bytes / 1024, 1)

    if not dry_run:
        for f in files_to_delete:
            try:
                f.unlink()
            except OSError:
                pass

    return result


def get_outputs_safety_hint() -> str:
    """Return a UI-friendly safety hint about the outputs/ directory.

    Use in export areas, settings, or as a caption near download buttons.
    """
    files = list_output_files()
    file_count = len(files)

    hint = (
        "🔒 **数据安全提示**\n\n"
        "`outputs/` 目录中保存了生成的报告文件（Markdown / HTML / DOCX）。\n"
        "- 如果报告中包含真实隐私数据，**请勿将 `outputs/` 上传到公开仓库**。\n"
        "- 发布项目前建议检查并清理 `outputs/` 目录。\n"
        "- `outputs/` 已在 `.gitignore` 中被忽略，不会被 Git 跟踪。\n"
        "- 你可以在「设置」区域查看和清理 outputs/ 中的文件。"
    )

    if file_count > 0:
        total_kb = 0.0
        for f in files:
            try:
                full_path = (_DEFAULT_OUTPUTS_DIR / f)
                total_kb += full_path.stat().st_size / 1024
            except OSError:
                pass
        hint += (
            f"\n\n📂 当前 `outputs/` 中有 **{file_count}** 个文件 "
            f"（约 {total_kb:.0f} KB）"
        )

    return hint


# ================================================================
# AI pre-generation privacy variable summary
# ================================================================

def summarize_ai_variable_privacy(schema_df: pd.DataFrame) -> Dict[str, Any]:
    """Summarise the privacy profile of variables that will be sent to AI.

    Scans *schema_df* for ``privacy_risk``, ``privacy_category``,
    and ``allow_send_to_ai`` columns and returns a dict suitable for
    pre-generation UI display.

    Args:
        schema_df: Schema DataFrame with at minimum ``column``, and ideally
                   ``privacy_risk``, ``privacy_category``, ``allow_send_to_ai``.

    Returns:
        {
            "total_vars": int,
            "sent_to_ai": int,
            "high_risk": int,
            "high_risk_sent": int,
            "medium_risk": int,
            "medium_risk_sent": int,
            "free_text_vars": int,
            "free_text_sent": int,
            "has_high_risk_sent": bool,
            "is_all_safe": bool,
        }
    """
    result: Dict[str, Any] = {
        "total_vars": len(schema_df),
        "sent_to_ai": 0,
        "high_risk": 0,
        "high_risk_sent": 0,
        "medium_risk": 0,
        "medium_risk_sent": 0,
        "free_text_vars": 0,
        "free_text_sent": 0,
        "has_high_risk_sent": False,
        "is_all_safe": True,
    }

    if "column" not in schema_df.columns:
        result["total_vars"] = 0
        return result

    has_privacy = "privacy_risk" in schema_df.columns
    has_category = "privacy_category" in schema_df.columns
    has_allow_send = "allow_send_to_ai" in schema_df.columns

    for _, row in schema_df.iterrows():
        risk = row.get("privacy_risk", "none") if has_privacy else "none"
        cat = row.get("privacy_category", "none") if has_category else "none"
        allow = bool(row.get("allow_send_to_ai", True)) if has_allow_send else True

        if allow:
            result["sent_to_ai"] += 1

        if risk == "high":
            result["high_risk"] += 1
            if allow:
                result["high_risk_sent"] += 1
                result["has_high_risk_sent"] = True
        elif risk == "medium":
            result["medium_risk"] += 1
            if allow:
                result["medium_risk_sent"] += 1

        if cat == "free_text":
            result["free_text_vars"] += 1
            if allow:
                result["free_text_sent"] += 1

    if result["high_risk_sent"] > 0:
        result["is_all_safe"] = False

    return result


def get_ai_privacy_summary_message(privacy_summary: Dict[str, Any]) -> str:
    """Return a UI-friendly summary message from ``summarize_ai_variable_privacy``.

    Args:
        privacy_summary: The dict returned by ``summarize_ai_variable_privacy``.

    Returns:
        A Markdown-formatted string suitable for ``st.warning`` or ``st.success``.
    """
    total = privacy_summary.get("total_vars", 0)
    sent = privacy_summary.get("sent_to_ai", 0)
    high = privacy_summary.get("high_risk", 0)
    high_sent = privacy_summary.get("high_risk_sent", 0)
    med = privacy_summary.get("medium_risk", 0)
    med_sent = privacy_summary.get("medium_risk_sent", 0)
    free = privacy_summary.get("free_text_vars", 0)
    free_sent = privacy_summary.get("free_text_sent", 0)
    has_high_sent = privacy_summary.get("has_high_risk_sent", False)

    lines = [
        "#### 📤 发送给 AI 的变量确认",
        "",
        f"- 总变量：**{total}** 个",
        f"- 将发送给 AI：**{sent}** 个",
    ]

    if high > 0:
        lines.append(f"- 🔴 高风险变量：**{high}** 个（其中 {high_sent} 个将发送给 AI）")
    if med > 0:
        lines.append(f"- 🟡 中风险变量：**{med}** 个（其中 {med_sent} 个将发送给 AI）")
    if free > 0:
        lines.append(f"- 📝 自由文本变量：**{free}** 个（其中 {free_sent} 个将发送给 AI）")

    if has_high_sent:
        lines.extend([
            "",
            "⚠️ **检测到高风险字段将发送给 AI 服务商。**",
            "建议在上方「7. 🔒 隐私与变量使用设置」中取消高风险变量的「🤖 发送 AI」勾选，",
            "或将其发送方式设为「仅发送聚合统计」，以降低隐私风险。",
        ])
    else:
        lines.extend([
            "",
            "✅ **隐私检查通过** — 所有高风险变量均已排除，不会发送给 AI。",
            "你可以安全地生成报告。",
        ])

    return "\n".join(lines)
