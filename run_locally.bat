@echo off
title MAWAQIT TV Runner
echo Checking for Python...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python from https://www.python.org/ and check "Add Python to PATH".
    pause
    exit /b
)

echo Installing dependencies (pywebview)...
pip install pywebview

echo Launching MAWAQIT TV Application...
python mawaqit.py

pause
