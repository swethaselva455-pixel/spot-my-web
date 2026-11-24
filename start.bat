@echo off
title SpotMyShoot - Local Booking Server
echo =================================================================
echo       Starting SpotMyShoot Booking Server (Local Mode)
echo =================================================================
echo.

python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not found in your system PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

echo Checking dependencies...
python -m pip install -q -r requirements.txt

echo.
echo Launching server and APScheduler background jobs...
python run.py

pause
