@echo off
REM MP4 to HLS Video Converter - GUI Launcher
REM This batch file launches the GUI application

echo Starting MP4 to HLS Video Converter GUI...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7 or higher from https://www.python.org/
    echo.
    pause
    exit /b 1
)

REM Launch the GUI
python gui.py

REM If the GUI exits with an error, pause to show the error
if errorlevel 1 (
    echo.
    echo The application exited with an error.
    pause
)
