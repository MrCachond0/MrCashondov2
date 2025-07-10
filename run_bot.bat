@echo off
REM Run script for Mr. Cashondo Trading Bot

echo ========================================
echo    Mr. Cashondo Trading Bot
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

REM Check if .env file exists
if not exist .env (
    echo ERROR: .env file not found.
    echo Please copy .env.example to .env and configure your credentials.
    pause
    exit /b 1
)

echo Starting Mr. Cashondo Trading Bot...
echo Press Ctrl+C to stop the bot
echo.

REM Run the bot
python main.py

echo.
echo Bot stopped.
pause
