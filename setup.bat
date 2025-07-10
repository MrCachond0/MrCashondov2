@echo off
REM Setup script for Mr. Cashondo Trading Bot

echo ========================================
echo    Mr. Cashondo Trading Bot Setup
echo ========================================
echo.

REM Check if Python is installed
py --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python 3.10 or higher.
    pause
    exit /b 1
)

echo [1/5] Python detected...
echo.

REM Create virtual environment
echo [2/5] Creating virtual environment...
py -m venv venv
if %errorlevel% neq 0 (
    echo ERROR: Failed to create virtual environment.
    pause
    exit /b 1
)

REM Activate virtual environment
echo [3/5] Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo [4/5] Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

REM Check if .env file exists
echo [5/5] Checking configuration...
if not exist .env (
    echo WARNING: .env file not found.
    echo Please copy .env.example to .env and configure your credentials.
    copy .env.example .env
    echo.
    echo .env file created from template.
    echo Please edit .env with your actual credentials before running the bot.
    pause
) else (
    echo .env file found.
)

echo.
echo ========================================
echo         Setup Complete!
echo ========================================
echo.
echo To run the bot:
echo   1. Edit .env with your credentials
echo   2. Run: py main.py
echo.
echo To run tests:
echo   Run: pytest test_bot.py -v
echo.
echo To format code:
echo   Run: black .
echo.
pause
