@echo off
REM Clean setup script for Mr. Cashondo Trading Bot

echo ========================================
echo    Mr. Cashondo Trading Bot Clean Setup
echo ========================================
echo.

REM Remove existing virtual environment if it exists
if exist venv (
    echo [1/6] Removing existing virtual environment...
    rmdir /s /q venv
    echo Virtual environment removed.
) else (
    echo [1/6] No existing virtual environment found.
)

REM Check if Python is installed
py --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python 3.10 or higher.
    pause
    exit /b 1
)

echo [2/6] Python detected...
py --version
echo.

REM Upgrade pip first
echo [3/6] Upgrading pip...
py -m pip install --upgrade pip
echo.

REM Create virtual environment
echo [4/6] Creating virtual environment...
py -m venv venv
if %errorlevel% neq 0 (
    echo ERROR: Failed to create virtual environment.
    pause
    exit /b 1
)

REM Activate virtual environment
echo [5/6] Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo [6/6] Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies.
    echo.
    echo Trying to install packages individually...
    pip install MetaTrader5
    pip install pyTelegramBotAPI
    pip install python-dotenv
    pip install pandas
    pip install numpy
    pip install schedule
    pip install pytest
    pip install black
    
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install some packages.
        pause
        exit /b 1
    )
)

REM Check if .env file exists
echo.
echo Checking configuration...
if not exist .env (
    echo WARNING: .env file not found.
    echo The .env file already exists with your credentials.
) else (
    echo .env file found.
)

echo.
echo ========================================
echo         Setup Complete!
echo ========================================
echo.
echo To run the bot:
echo   1. Activate virtual environment: venv\Scripts\activate
echo   2. Run: py main.py
echo.
echo To run tests:
echo   Run: pytest test_bot.py -v
echo.
echo To format code:
echo   Run: black .
echo.
pause
