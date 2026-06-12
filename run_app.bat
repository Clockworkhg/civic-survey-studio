@echo off
REM ================================================================
REM  政府服务满意度问卷 AI 辅助统计分析与报告生成平台
REM  One-click launcher for Windows
REM ================================================================

cd /d "%~dp0"

REM --- Activate virtual environment if present ---
if exist ".venv\Scripts\activate.bat" (
    echo [*] Activating virtual environment .venv ...
    call .venv\Scripts\activate.bat
) else (
    echo [!] No .venv found, using system Python.
    echo     To create a venv: python -m venv .venv
    echo     Then install:    pip install -r requirements.txt
    echo.
)

echo [*] Starting Streamlit app ...
streamlit run app.py

pause
