#!/usr/bin/env bash
# v0.1.0 发布前检查 — Linux/macOS 启动脚本
# 用法: ./run_release_check.sh          → 仅静态检查
#       ./run_release_check.sh --run-tests → 包含 pytest + test_run4

set -euo pipefail
cd "$(dirname "$0")"

echo ""
echo "========================================"
echo "  v0.1.0 发布前检查"
echo "========================================"
echo ""

# 尝试激活 .venv（如果存在且未激活）
if [ -f ".venv/bin/python" ] && [ -z "${VIRTUAL_ENV:-}" ]; then
    echo "激活虚拟环境 .venv ..."
    source .venv/bin/activate
fi

python scripts/release_check.py "$@"
exit $?
