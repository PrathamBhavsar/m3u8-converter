@echo off
REM MP4 to HLS Video Converter - GUI Launcher
REM Launches only the GUI control panel (no terminal window)

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7 or higher from https://www.python.org/
    pause
    exit /b 1
)

REM Launch GUI without showing this terminal (pythonw runs without console)
start "" pythonw gui.py
