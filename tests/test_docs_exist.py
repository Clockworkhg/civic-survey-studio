"""Tests for required documentation and project files."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Files that must exist
REQUIRED_DOCS = [
    "README.md",
    "docs/quickstart.md",
    "docs/deployment.md",
    "docs/release_checklist.md",
    "docs/security.md",
    "docs/roadmap.md",
    "docs/known_issues.md",
    "CHANGELOG.md",
]

REQUIRED_CONFIG_FILES = [
    ".env.example",
    "requirements.txt",
    ".gitignore",
]

REQUIRED_SCRIPTS = [
    "run_app.bat",
    "run_tests.bat",
    "run_release_check.bat",
]


def _exists(rel_path: str) -> bool:
    return os.path.isfile(os.path.join(ROOT, rel_path))


class TestDocsExist:
    """Verify required documentation files exist."""

    @pytest.mark.parametrize("doc_path", REQUIRED_DOCS)
    def test_doc_exists(self, doc_path):
        assert _exists(doc_path), f"Missing documentation file: {doc_path}"

    def test_readme_non_empty(self):
        path = os.path.join(ROOT, "README.md")
        assert _exists("README.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert len(content) > 500, f"README.md too short ({len(content)} chars), expected > 500"

    def test_quickstart_non_empty(self):
        path = os.path.join(ROOT, "docs", "quickstart.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert len(content) > 300, f"quickstart.md too short ({len(content)} chars), expected > 300"

    def test_deployment_non_empty(self):
        path = os.path.join(ROOT, "docs", "deployment.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert len(content) > 300, f"deployment.md too short ({len(content)} chars), expected > 300"

    def test_release_checklist_non_empty(self):
        path = os.path.join(ROOT, "docs", "release_checklist.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert len(content) > 500, f"release_checklist.md too short ({len(content)} chars), expected > 500"


class TestConfigFilesExist:
    """Verify required configuration files exist."""

    @pytest.mark.parametrize("file_path", REQUIRED_CONFIG_FILES)
    def test_config_file_exists(self, file_path):
        assert _exists(file_path), f"Missing config file: {file_path}"

    def test_env_example_has_no_real_keys(self):
        """.env.example should have empty values, not real API keys."""
        path = os.path.join(ROOT, ".env.example")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        # Check that no line has a value that looks like a real key (>20 chars after =)
        for line in content.splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                _, value = line.split("=", 1)
                value = value.strip()
                if value and len(value) > 20:
                    # Allow long placeholder descriptions but flag potential real keys
                    if value.startswith("sk-") or value.startswith("api-"):
                        pytest.fail(f".env.example contains a value that looks like a real API key: {line}")


class TestScriptsExist:
    """Verify required scripts exist."""

    @pytest.mark.parametrize("script_path", REQUIRED_SCRIPTS)
    def test_script_exists(self, script_path):
        assert _exists(script_path), f"Missing script: {script_path}"


class TestCIExists:
    """Verify GitHub Actions CI config exists."""

    def test_ci_workflow_exists(self):
        path = os.path.join(ROOT, ".github", "workflows", "tests.yml")
        assert os.path.isfile(path), f"Missing CI workflow: {path}"


class TestExamplesDir:
    """Verify examples directory and files."""

    def test_examples_dir_exists(self):
        path = os.path.join(ROOT, "examples")
        assert os.path.isdir(path), "Missing examples/ directory"

    def test_sample_csv_exists(self):
        path = os.path.join(ROOT, "examples", "government_service_satisfaction_sample.csv")
        assert os.path.isfile(path), f"Missing: {path}"

    def test_var_dict_csv_exists(self):
        path = os.path.join(ROOT, "examples", "variable_dictionary_sample.csv")
        assert os.path.isfile(path), f"Missing: {path}"


# ================================================================
# P3-3: New keyword checks for updated docs
# ================================================================

class TestReadmeP33Keywords:
    """Verify README contains P3-3 updated content."""

    @pytest.fixture(autouse=True)
    def setup(self):
        path = os.path.join(ROOT, "README.md")
        with open(path, encoding="utf-8") as f:
            self.content = f.read()

    def test_readme_has_no_api_key_section(self):
        assert "无 API Key" in self.content or "不需要任何 API Key" in self.content, (
            "README should mention '无 API Key 也能用'"
        )

    def test_readme_has_example_data_section(self):
        assert "内置示例数据" in self.content or "加载内置示例数据" in self.content, (
            "README should mention example data section"
        )

    def test_readme_has_privacy_note(self):
        assert "隐私" in self.content, "README should mention privacy"


class TestQuickstartP33Keywords:
    """Verify quickstart contains P3-3 updated content."""

    @pytest.fixture(autouse=True)
    def setup(self):
        path = os.path.join(ROOT, "docs", "quickstart.md")
        with open(path, encoding="utf-8") as f:
            self.content = f.read()

    def test_quickstart_has_no_api_key_section(self):
        assert "没有 API Key" in self.content, (
            "quickstart should have '没有 API Key 时如何体验' section"
        )

    def test_quickstart_has_export_section(self):
        assert "导出报告" in self.content, (
            "quickstart should have '导出报告' section"
        )

    def test_quickstart_has_example_button(self):
        assert "加载内置示例数据" in self.content, (
            "quickstart should mention the '加载内置示例数据' button"
        )


class TestReleaseChecklistP33Keywords:
    """Verify release checklist contains P3-3 updated content."""

    @pytest.fixture(autouse=True)
    def setup(self):
        path = os.path.join(ROOT, "docs", "release_checklist.md")
        with open(path, encoding="utf-8") as f:
            self.content = f.read()

    def test_checklist_has_experience_checks(self):
        assert "体验优化" in self.content, (
            "release checklist should have P3-3 experience checks section"
        )

    def test_checklist_has_example_data_check(self):
        assert "示例数据一键加载" in self.content or "加载内置示例数据" in self.content, (
            "release checklist should check example data button"
        )

    def test_checklist_has_no_api_key_check(self):
        assert "无 API Key 提示" in self.content, (
            "release checklist should check no-API-key prompt"
        )


# ================================================================
# P3-4: Security documentation and keyword checks
# ================================================================

class TestSecurityDoc:
    """Verify docs/security.md exists and has expected content."""

    def test_security_doc_exists(self):
        path = os.path.join(ROOT, "docs", "security.md")
        assert os.path.isfile(path), "Missing security documentation: docs/security.md"

    def test_security_doc_non_empty(self):
        path = os.path.join(ROOT, "docs", "security.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert len(content) > 500, f"security.md too short ({len(content)} chars), expected > 500"

    def test_security_doc_has_api_key_section(self):
        path = os.path.join(ROOT, "docs", "security.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "API Key" in content, "security.md should mention API Key usage"

    def test_security_doc_has_privacy_section(self):
        path = os.path.join(ROOT, "docs", "security.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "隐私" in content, "security.md should mention privacy"

    def test_security_doc_has_outputs_section(self):
        path = os.path.join(ROOT, "docs", "security.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "outputs" in content.lower(), "security.md should mention outputs/"


class TestReadmeP34Keywords:
    """Verify README links to security documentation."""

    def test_readme_links_security_doc(self):
        path = os.path.join(ROOT, "README.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "docs/security.md" in content or "安全说明" in content, (
            "README should link to docs/security.md"
        )

    def test_readme_has_p34_status(self):
        path = os.path.join(ROOT, "README.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "P3-4" in content, "README should have P3-4 status row"


# ================================================================
# P3-5: Versioning, CHANGELOG, roadmap, known_issues, release_check
# ================================================================

class TestVersionFile:
    """Verify VERSION file exists."""

    def test_version_file_exists(self):
        path = os.path.join(ROOT, "VERSION")
        assert os.path.isfile(path), "VERSION file is missing"


class TestReadmeP35Keywords:
    """Verify README contains P3-5 content."""

    @pytest.fixture(autouse=True)
    def setup(self):
        path = os.path.join(ROOT, "README.md")
        with open(path, encoding="utf-8") as f:
            self.content = f.read()

    def test_readme_has_version_badge(self):
        assert "v0.1.0" in self.content, "README should show v0.1.0"

    def test_readme_has_changelog_link(self):
        assert "CHANGELOG.md" in self.content, "README should link to CHANGELOG.md"

    def test_readme_has_roadmap_link(self):
        assert "roadmap.md" in self.content, "README should link to roadmap.md"

    def test_readme_has_known_issues_link(self):
        assert "known_issues.md" in self.content, "README should link to known_issues.md"

    def test_readme_has_release_check_section(self):
        assert "release_check.py" in self.content, (
            "README should mention release_check.py"
        )


class TestChangelogFile:
    """Verify CHANGELOG.md exists and has content."""

    def test_changelog_exists(self):
        path = os.path.join(ROOT, "CHANGELOG.md")
        assert os.path.isfile(path), "CHANGELOG.md is missing"

    def test_changelog_non_empty(self):
        path = os.path.join(ROOT, "CHANGELOG.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert len(content) > 500, (
            f"CHANGELOG.md too short ({len(content)} chars), expected > 500"
        )

    def test_changelog_has_0_1_0(self):
        path = os.path.join(ROOT, "CHANGELOG.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "[0.1.0]" in content, "CHANGELOG.md should contain [0.1.0]"


class TestReleaseChecklistP35Keywords:
    """Verify release checklist has v0.1.0 release flow."""

    @pytest.fixture(autouse=True)
    def setup(self):
        path = os.path.join(ROOT, "docs", "release_checklist.md")
        with open(path, encoding="utf-8") as f:
            self.content = f.read()

    def test_checklist_has_release_flow(self):
        assert "发布流程" in self.content, (
            "release checklist should have v0.1.0 发布流程 section"
        )

    def test_checklist_has_git_tag_instructions(self):
        assert "git tag" in self.content, (
            "release checklist should include git tag instructions"
        )

    def test_checklist_has_release_check_script_mention(self):
        assert "release_check.py" in self.content, (
            "release checklist should mention release_check.py"
        )


class TestReleaseChecklistP34Keywords:
    """Verify release checklist contains P3-4 security checks."""

    @pytest.fixture(autouse=True)
    def setup(self):
        path = os.path.join(ROOT, "docs", "release_checklist.md")
        with open(path, encoding="utf-8") as f:
            self.content = f.read()

    def test_checklist_has_security_section(self):
        assert "发布前安全检查" in self.content, (
            "release checklist should have security checks section"
        )

    def test_checklist_has_secrets_scan(self):
        assert "test_no_secrets_committed" in self.content, (
            "release checklist should mention secrets scan test"
        )

    def test_checklist_mentions_outputs_cleanup(self):
        assert "outputs" in self.content.lower(), (
            "release checklist should mention outputs cleanup"
        )
