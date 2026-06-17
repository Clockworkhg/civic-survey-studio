@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "APP_PORT=%~1"
if "%APP_PORT%"=="" set "APP_PORT=8502"

echo.
echo ================================================
echo   CivicSurvey Studio (问策 Insight)
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
echo Open http://localhost:%APP_PORT% in your browser.
echo.

streamlit run app.py --server.port %APP_PORT% --server.address 0.0.0.0

pause
