@echo off
REM v0.1.0 发布前检查 — Windows 启动脚本
REM 用法: run_release_check.bat          → 仅静态检查
REM       run_release_check.bat --run-tests → 包含 pytest + test_run4

cd /d "%~dp0"

echo.
echo ========================================
echo   v0.1.0 发布前检查
echo ========================================
echo.

REM 尝试激活 .venv（如果存在且未激活）
if exist ".venv\Scripts\python.exe" (
    if not defined VIRTUAL_ENV (
        echo 激活虚拟环境 .venv ...
        call .venv\Scripts\activate.bat
    )
)

python scripts/release_check.py %*
exit /b %ERRORLEVEL%
