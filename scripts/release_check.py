"""v0.1.0 发布前检查脚本

用法:
    python scripts/release_check.py            # 仅静态检查（快速）
    python scripts/release_check.py --run-tests  # 包含 pytest + test_run4

静态检查包括:
    1. 必要文件存在性（VERSION, README, CHANGELOG, docs, examples）
    2. 不应提交的文件检查（.env, .streamlit/secrets.toml, config/user_settings.json）
    3. outputs/ 目录文件提醒
    4. 版本一致性检查

不依赖第三方包，仅使用 Python 标准库。
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Force UTF-8 output on Windows (avoids GBK encoding errors with special chars)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parent.parent

# ── 检查结果输出 ──

_pass_count = 0
_warn_count = 0
_fail_count = 0


def _ok(msg: str) -> None:
    global _pass_count
    _pass_count += 1
    print(f"  ✅ {msg}")


def _warn(msg: str) -> None:
    global _warn_count
    _warn_count += 1
    print(f"  ⚠️  {msg}")


def _fail(msg: str) -> None:
    global _fail_count
    _fail_count += 1
    print(f"  ❌ {msg}")


# ── 检查函数 ──


def check_version_file() -> bool:
    """检查 VERSION 文件是否存在且内容为有效版本号。"""
    print("\n📌 一、版本号检查")
    vf = ROOT / "VERSION"
    if not vf.is_file():
        _fail("VERSION 文件不存在")
        return False
    version = vf.read_text(encoding="utf-8").strip()
    parts = version.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        _fail(f"VERSION 格式不正确: '{version}'（期望 x.y.z）")
        return False
    _ok(f"VERSION = {version}")
    return True


def check_src_version() -> bool:
    """检查 src/__init__.py 中是否定义了 __version__。"""
    init_file = ROOT / "src" / "__init__.py"
    if not init_file.is_file():
        _fail("src/__init__.py 不存在")
        return False

    content = init_file.read_text(encoding="utf-8")
    if "__version__" not in content:
        _fail("src/__init__.py 中缺少 __version__")
        return False

    # Extract version string
    import re
    m = re.search(r'''__version__\s*=\s*["']([^"']+)["']''', content)
    if not m:
        _fail("无法解析 src/__init__.py 中的 __version__")
        return False

    _ok(f"src.__version__ = {m.group(1)}")
    return True


def check_version_consistency() -> bool:
    """检查 VERSION 与 src.__version__ 是否一致。"""
    vf = ROOT / "VERSION"
    init_file = ROOT / "src" / "__init__.py"

    if not vf.is_file() or not init_file.is_file():
        _fail("无法检查版本一致性：文件缺失")
        return False

    file_ver = vf.read_text(encoding="utf-8").strip()
    import re
    content = init_file.read_text(encoding="utf-8")
    m = re.search(r'''__version__\s*=\s*["']([^"']+)["']''', content)
    src_ver = m.group(1) if m else ""

    if file_ver != src_ver:
        _fail(f"版本不一致: VERSION={file_ver}, src.__version__={src_ver}")
        return False
    _ok(f"VERSION 与 src.__version__ 一致 ({file_ver})")
    return True


# ── 二、必要文件检查 ──

REQUIRED_FILES = [
    ("README.md", "README 文档"),
    ("CHANGELOG.md", "变更日志"),
    (".env.example", "环境变量模板"),
    ("requirements.txt", "依赖清单"),
    (".gitignore", "Git 忽略规则"),
]

REQUIRED_DOCS = [
    ("docs/quickstart.md", "快速开始"),
    ("docs/deployment.md", "部署说明"),
    ("docs/security.md", "安全说明"),
    ("docs/release_checklist.md", "发布检查清单"),
    ("docs/known_issues.md", "已知问题"),
    ("docs/roadmap.md", "路线图"),
]

REQUIRED_EXAMPLES = [
    ("examples/government_service_satisfaction_sample.csv", "示例数据 CSV"),
    ("examples/variable_dictionary_sample.csv", "变量说明表 CSV"),
]

REQUIRED_SCRIPTS = [
    ("scripts/release_check.py", "发布检查脚本"),
    ("run_release_check.bat", "Windows 发布检查启动脚本"),
]


def check_required_files() -> None:
    """检查必要文件存在性。"""
    print("\n📌 二、必要文件检查")

    for path, desc in REQUIRED_FILES:
        if (ROOT / path).is_file():
            _ok(f"{desc} ({path})")
        else:
            _fail(f"{desc} 缺失 ({path})")

    for path, desc in REQUIRED_DOCS:
        if (ROOT / path).is_file():
            _ok(f"{desc} ({path})")
        else:
            _fail(f"{desc} 缺失 ({path})")

    for path, desc in REQUIRED_EXAMPLES:
        if (ROOT / path).is_file():
            _ok(f"{desc} ({path})")
        else:
            _fail(f"{desc} 缺失 ({path})")

    for path, desc in REQUIRED_SCRIPTS:
        if (ROOT / path).is_file():
            _ok(f"{desc} ({path})")
        else:
            _fail(f"{desc} 缺失 ({path})")


# ── 三、不应提交的文件 ──

FORBIDDEN_FILES = [
    (".env", "本地环境变量文件（可能含真实 API Key）"),
    (".streamlit/secrets.toml", "Streamlit Secrets（可能含真实 API Key）"),
    ("config/user_settings.json", "用户设置文件（可能含真实 API Key）"),
]


def check_forbidden_files() -> None:
    """检查是否存在不应提交的文件。"""
    print("\n📌 三、不应提交的文件检查")

    for path, desc in FORBIDDEN_FILES:
        full = ROOT / path
        if full.exists():
            _warn(f"{desc} 存在 ({path}) — 请确认已在 .gitignore 中忽略")
        else:
            _ok(f"无 {path}")


# ── 四、outputs 目录 ──


def check_outputs() -> None:
    """检查 outputs/ 目录。"""
    print("\n📌 四、outputs/ 目录检查")

    outputs_dir = ROOT / "outputs"
    if not outputs_dir.is_dir():
        _ok("outputs/ 目录不存在（无报告输出）")
        return

    files = [f for f in outputs_dir.iterdir() if f.is_file() and not f.name.startswith(".")]
    if not files:
        _ok("outputs/ 目录为空")
        return

    total_size_kb = sum(
        f.stat().st_size for f in files if f.is_file()
    ) / 1024

    _warn(
        f"outputs/ 中有 {len(files)} 个文件（约 {total_size_kb:.0f} KB）。\n"
        f"     发布前建议清理: python -c \"from src.ui.security import clean_output_files; "
        f"print(clean_output_files(dry_run=False))\""
    )
    for f in sorted(files):
        size_kb = f.stat().st_size / 1024
        print(f"      📄 {f.name} ({size_kb:.1f} KB)")


# ── 五、README 版本提及 ──


def check_readme_version() -> None:
    """检查 README 是否提及当前版本。"""
    print("\n📌 五、README 版本检查")

    readme = ROOT / "README.md"
    if not readme.is_file():
        _fail("README.md 不存在")
        return

    content = readme.read_text(encoding="utf-8")
    if "v0.1.0" in content:
        _ok("README 提及 v0.1.0")
    else:
        _warn("README 未提及 v0.1.0")

    if "release_check.py" in content:
        _ok("README 提及 release_check.py")
    else:
        _warn("README 未提及 release_check.py")

    if "CHANGELOG.md" in content:
        _ok("README 提及 CHANGELOG.md")
    else:
        _warn("README 未提及 CHANGELOG.md")


# ── 六、测试运行 ──


def run_tests() -> None:
    """运行 pytest 和 test_run4（仅当 --run-tests 时调用）。"""
    print("\n📌 六、运行测试")

    # pytest
    print("\n  运行 pytest ...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            _ok("pytest 全部通过")
        else:
            _fail(f"pytest 存在失败（退出码 {result.returncode}）")
            # Print last 30 lines for diagnosis
            lines = result.stdout.strip().splitlines()
            for line in lines[-30:]:
                print(f"      {line}")
    except FileNotFoundError:
        _fail("pytest 未安装或不在 PATH 中")
    except subprocess.TimeoutExpired:
        _fail("pytest 超时（> 5 分钟）")

    # test_run4
    print("\n  运行 test_run4.py ...")
    try:
        result = subprocess.run(
            [sys.executable, "test_run4.py"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            _ok("test_run4.py 全部通过")
        else:
            _fail(f"test_run4.py 存在失败（退出码 {result.returncode}）")
            lines = result.stdout.strip().splitlines()
            for line in lines[-20:]:
                print(f"      {line}")
    except subprocess.TimeoutExpired:
        _fail("test_run4.py 超时（> 5 分钟）")


# ── 七、CHANGELOG 检查 ──


def check_changelog() -> None:
    """检查 CHANGELOG 是否包含当前版本。"""
    print("\n📌 七、CHANGELOG 检查")

    cl = ROOT / "CHANGELOG.md"
    if not cl.is_file():
        _fail("CHANGELOG.md 不存在")
        return

    content = cl.read_text(encoding="utf-8")
    if "[0.1.0]" in content:
        _ok("CHANGELOG 包含 [0.1.0]")
    else:
        _fail("CHANGELOG 未包含 [0.1.0]")

    # Check sections exist
    for section in ["### Added", "### Fixed", "### Security"]:
        if section in content:
            _ok(f"CHANGELOG 包含 {section} 章节")
        else:
            _warn(f"CHANGELOG 缺少 {section} 章节")


# ── 主入口 ──


def main() -> int:
    parser = argparse.ArgumentParser(
        description="v0.1.0 发布前检查脚本",
    )
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="同时运行 pytest 和 test_run4.py（默认仅静态检查）",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  v0.1.0 发布前检查")
    print("=" * 60)

    # 版本
    check_version_file()
    check_src_version()
    check_version_consistency()

    # 文件
    check_required_files()

    # 安全
    check_forbidden_files()
    check_outputs()

    # README
    check_readme_version()

    # CHANGELOG
    check_changelog()

    # 测试（可选）
    if args.run_tests:
        run_tests()
    else:
        print("\n📌 六、测试（跳过）")
        print("  ℹ️  使用 --run-tests 参数可自动运行 pytest + test_run4.py")

    # 汇总
    print("\n" + "=" * 60)
    print("  检查结果汇总")
    print("=" * 60)
    print(f"  通过: {_pass_count}  |  警告: {_warn_count}  |  失败: {_fail_count}")

    if _fail_count > 0:
        print(f"\n  ❌ 存在 {_fail_count} 个失败项，请在发布前修复。")
        return 1
    elif _warn_count > 0:
        print(f"\n  ⚠️  全部必要检查通过，但有 {_warn_count} 个提醒项。")
        print("  请人工确认后即可发布。")
        return 0
    else:
        print("\n  ✅ 全部检查通过！可以打 tag 发布了。")
        return 0


if __name__ == "__main__":
    sys.exit(main())
