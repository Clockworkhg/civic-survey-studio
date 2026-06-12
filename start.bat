@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ================================================
echo   Survey Data AI Analysis Platform
echo ================================================
echo.

if not exist ".venv" (
    echo [1/3] Creating virtual environment...
    python -m venv .venv
    echo Done.
) else (
    echo [1/3] Virtual environment found.
)

echo [2/3] Activating virtual environment...
call .venv\Scripts\activate.bat

echo [3/3] Installing dependencies...
pip install -r requirements.txt -q

echo.
echo Starting Streamlit app...
echo Open http://localhost:8501 in your browser.
echo.

streamlit run app.py --server.port 8501 --server.address 0.0.0.0

pause
