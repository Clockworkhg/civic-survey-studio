"""Tests for the release check script (P3-5).

Verifies scripts/release_check.py exists, compiles, and runs successfully.
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import py_compile
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "release_check.py")

# Ensure UTF-8 encoding for subprocess output on Windows
_ENV = os.environ.copy()
_ENV["PYTHONIOENCODING"] = "utf-8"


class TestReleaseCheckScriptExists:
    """Verify the script exists and compiles."""

    def test_script_exists(self):
        assert os.path.isfile(SCRIPT), (
            f"scripts/release_check.py is missing at {SCRIPT}"
        )

    def test_script_compiles(self):
        """Script should pass py_compile without errors."""
        py_compile.compile(SCRIPT, doraise=True)

    def test_script_has_shebang_or_main(self):
        """Script should have a __main__ guard."""
        with open(SCRIPT, encoding="utf-8") as f:
            content = f.read()
        assert '__name__ == "__main__"' in content or "__main__" in content, (
            "release_check.py should have a __main__ guard"
        )


class TestReleaseCheckScriptRuns:
    """Verify the script can run and produce output."""

    @staticmethod
    def _run(*extra_args, timeout=60):
        """Run release_check.py with consistent UTF-8 encoding."""
        return subprocess.run(
            [sys.executable, SCRIPT, *extra_args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=_ENV,
            timeout=timeout,
        )

    def test_runs_without_errors(self):
        """Script should exit 0 (or 1 if there are failures, not crash)."""
        try:
            result = self._run()
        except subprocess.TimeoutExpired:
            pytest.fail("release_check.py timed out (> 60s)")
        except Exception as e:
            pytest.fail(f"release_check.py failed to start: {e}")

        # Should NOT crash with a traceback
        assert "Traceback" not in result.stderr, (
            f"release_check.py crashed:\n{result.stderr}"
        )

    def test_output_contains_chinese(self):
        """Output should contain Chinese result labels."""
        result = self._run()
        output = result.stdout + result.stderr
        assert "检查" in output, (
            f"Output should contain Chinese '检查', got:\n{output[:500]}"
        )

    def test_output_contains_summary(self):
        """Output should contain a summary section."""
        result = self._run()
        output = result.stdout + result.stderr
        assert "汇总" in output or "通过" in output, (
            f"Output should contain summary, got:\n{output[:500]}"
        )

    def test_help_flag_works(self):
        """--help should show usage."""
        result = self._run("--help", timeout=30)
        assert result.returncode == 0, "--help should exit 0"
        assert "usage" in result.stdout.lower() or "用法" in result.stdout.lower() or "--run-tests" in result.stdout, (
            f"--help output missing usage info:\n{result.stdout[:500]}"
        )

    def test_run_tests_flag_accepted(self):
        """--run-tests should be recognized by argparse (check --help)."""
        result = self._run("--help", timeout=30)
        assert result.returncode == 0, "--help should exit 0"
        assert "--run-tests" in result.stdout, (
            f"--help should list --run-tests flag:\n{result.stdout[:500]}"
        )

    def test_run_tests_flag_in_source(self):
        """The --run-tests argument should be defined in the script source."""
        with open(SCRIPT, encoding="utf-8") as f:
            content = f.read()
        assert "--run-tests" in content, (
            "release_check.py should define --run-tests argument"
        )
        assert "add_argument" in content, (
            "release_check.py should use argparse"
        )
