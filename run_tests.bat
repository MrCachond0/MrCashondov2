@echo off
REM Test script for Mr. Cashondo Trading Bot

echo ========================================
echo    Mr. Cashondo Trading Bot Tests
echo ========================================
echo.

REM Check if virtual environment exists
if not exist venv (
    echo ERROR: Virtual environment not found.
    echo Please run setup.bat first.
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

echo Running tests...
echo.

REM Run tests with verbose output
pytest test_bot.py -v --tb=short

echo.
echo Tests completed.
pause
