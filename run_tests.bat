@echo off
REM ================================================================
REM  Run all tests (pytest + integration)
REM ================================================================

cd /d "%~dp0"

REM --- Activate virtual environment if present ---
if exist ".venv\Scripts\activate.bat" (
    echo [*] Activating virtual environment .venv ...
    call .venv\Scripts\activate.bat
)

echo.
echo ================================================================
echo  Running pytest (unit + integration)
echo ================================================================
python -m pytest tests/ -v
if errorlevel 1 (
    echo [!] pytest FAILED
    pause
    exit /b 1
)

echo.
echo ================================================================
echo  Running integration test suite (test_run4.py)
echo ================================================================
python test_run4.py
if errorlevel 1 (
    echo [!] test_run4.py FAILED
    pause
    exit /b 1
)

echo.
echo ================================================================
echo  All tests passed!
echo ================================================================
pause
