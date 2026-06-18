"""Tests for project versioning (P3-5).

Verifies VERSION file, src.__version__, consistency, and version format.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestVersionFile:
    """VERSION file checks."""

    def test_version_file_exists(self):
        vf = os.path.join(ROOT, "VERSION")
        assert os.path.isfile(vf), "VERSION file is missing"

    def test_version_file_non_empty(self):
        vf = os.path.join(ROOT, "VERSION")
        with open(vf, encoding="utf-8") as f:
            content = f.read().strip()
        assert len(content) > 0, "VERSION file is empty"

    def test_version_file_format(self):
        vf = os.path.join(ROOT, "VERSION")
        with open(vf, encoding="utf-8") as f:
            version = f.read().strip()
        assert re.match(r"^\d+\.\d+\.\d+$", version), (
            f"VERSION format should be x.y.z, got: '{version}'"
        )


class TestSrcInitVersion:
    """src/__init__.py __version__ checks."""

    def test_init_file_exists(self):
        init_file = os.path.join(ROOT, "src", "__init__.py")
        assert os.path.isfile(init_file), "src/__init__.py is missing"

    def test_version_defined(self):
        import src
        assert hasattr(src, "__version__"), "src/__init__.py should define __version__"

    def test_version_format(self):
        import src
        version = src.__version__
        assert re.match(r"^\d+\.\d+\.\d+$", version), (
            f"__version__ format should be x.y.z, got: '{version}'"
        )

    def test_version_is_string(self):
        import src
        assert isinstance(src.__version__, str), (
            "__version__ should be a string"
        )


class TestVersionConsistency:
    """VERSION and src.__version__ must match."""

    def test_versions_match(self):
        vf = os.path.join(ROOT, "VERSION")
        with open(vf, encoding="utf-8") as f:
            file_version = f.read().strip()

        import src
        assert file_version == src.__version__, (
            f"VERSION ({file_version}) != src.__version__ ({src.__version__})"
        )

    def test_version_is_0_1_1(self):
        """Both should be 0.1.1 for this release."""
        vf = os.path.join(ROOT, "VERSION")
        with open(vf, encoding="utf-8") as f:
            file_version = f.read().strip()

        import src
        assert file_version == "0.1.1", f"VERSION should be 0.1.1, got {file_version}"
        assert src.__version__ == "0.1.1", (
            f"src.__version__ should be 0.1.1, got {src.__version__}"
        )
