"""Tests for release documentation (P3-5).

Verifies CHANGELOG, roadmap, known_issues, and README mention v0.1.0.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel_path):
    path = os.path.join(ROOT, rel_path)
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestChangelog:
    """CHANGELOG.md checks."""

    def test_changelog_exists(self):
        assert os.path.isfile(os.path.join(ROOT, "CHANGELOG.md")), (
            "CHANGELOG.md is missing"
        )

    def test_changelog_non_empty(self):
        content = _read("CHANGELOG.md")
        assert len(content) > 300, (
            f"CHANGELOG.md too short ({len(content)} chars), expected > 300"
        )

    def test_changelog_contains_0_1_0(self):
        content = _read("CHANGELOG.md")
        assert "[0.1.0]" in content, "CHANGELOG should contain [0.1.0]"

    def test_changelog_has_added_section(self):
        content = _read("CHANGELOG.md")
        assert "### Added" in content, "CHANGELOG should have '### Added' section"

    def test_changelog_has_fixed_section(self):
        content = _read("CHANGELOG.md")
        assert "### Fixed" in content, "CHANGELOG should have '### Fixed' section"

    def test_changelog_has_security_section(self):
        content = _read("CHANGELOG.md")
        assert "### Security" in content, "CHANGELOG should have '### Security' section"


class TestRoadmap:
    """docs/roadmap.md checks."""

    def test_roadmap_exists(self):
        assert os.path.isfile(os.path.join(ROOT, "docs", "roadmap.md")), (
            "docs/roadmap.md is missing"
        )

    def test_roadmap_non_empty(self):
        content = _read("docs/roadmap.md")
        assert len(content) > 300, (
            f"roadmap.md too short ({len(content)} chars), expected > 300"
        )

    def test_roadmap_mentions_v0_2_0(self):
        content = _read("docs/roadmap.md")
        assert "v0.2.0" in content, "roadmap should mention v0.2.0"

    def test_roadmap_mentions_v0_3_0(self):
        content = _read("docs/roadmap.md")
        assert "v0.3.0" in content, "roadmap should mention v0.3.0"

    def test_roadmap_mentions_v1_0_0(self):
        content = _read("docs/roadmap.md")
        assert "v1.0.0" in content, "roadmap should mention v1.0.0"

    def test_roadmap_has_planning_disclaimer(self):
        """Roadmap should state these are plans, not current features."""
        content = _read("docs/roadmap.md")
        assert "不代表当前版本已支持" in content or "当前版本" in content, (
            "roadmap should clarify these are future plans"
        )


class TestKnownIssues:
    """docs/known_issues.md checks."""

    def test_known_issues_exists(self):
        assert os.path.isfile(os.path.join(ROOT, "docs", "known_issues.md")), (
            "docs/known_issues.md is missing"
        )

    def test_known_issues_non_empty(self):
        content = _read("docs/known_issues.md")
        assert len(content) > 500, (
            f"known_issues.md too short ({len(content)} chars), expected > 500"
        )

    def test_mentions_cnki(self):
        content = _read("docs/known_issues.md")
        assert "CNKI" in content or "知网" in content, (
            "known_issues should mention CNKI/知网 limitation"
        )

    def test_mentions_authentication(self):
        content = _read("docs/known_issues.md")
        assert "认证" in content or "登录" in content, (
            "known_issues should mention lack of authentication"
        )

    def test_mentions_persistence(self):
        content = _read("docs/known_issues.md")
        assert "持久化" in content or "数据库" in content or "session_state" in content, (
            "known_issues should mention no database persistence"
        )

    def test_mentions_ai_auxiliary(self):
        content = _read("docs/known_issues.md")
        assert "辅助" in content or "AI 报告" in content or "不能替代" in content, (
            "known_issues should mention AI report is auxiliary only"
        )


class TestReadmeV010:
    """README should reference v0.1.0 and release_check.py."""

    def test_readme_mentions_v0_1_0(self):
        content = _read("README.md")
        assert "v0.1.0" in content, "README should mention v0.1.0"

    def test_readme_mentions_release_check(self):
        content = _read("README.md")
        assert "release_check.py" in content, (
            "README should mention release_check.py"
        )

    def test_readme_mentions_changelog(self):
        content = _read("README.md")
        assert "CHANGELOG.md" in content or "变更日志" in content, (
            "README should link to CHANGELOG.md"
        )

    def test_readme_mentions_roadmap(self):
        content = _read("README.md")
        assert "roadmap.md" in content or "路线图" in content, (
            "README should link to docs/roadmap.md"
        )

    def test_readme_mentions_known_issues(self):
        content = _read("README.md")
        assert "known_issues.md" in content or "已知问题" in content, (
            "README should link to docs/known_issues.md"
        )

    def test_readme_has_p35_status(self):
        content = _read("README.md")
        assert "P3-5" in content, "README should have P3-5 status row"
