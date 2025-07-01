@echo off
setlocal enabledelayedexpansion

:: Set paths
set PYTHON_EXE=%~dp0WPy64-310111\python-3.10.11.amd64\python.exe
set VENV_PATH=%~dp0.venv
set REQUIREMENTS=%~dp0requirements.txt
set SCRIPT=%~dp0tray_watchdog.py

:: Check if venv exists
if not exist "%VENV_PATH%" (
    :: Create virtual environment
    "%PYTHON_EXE%" -m venv "%VENV_PATH%"
    set NEW_VENV=1
) else (
    set NEW_VENV=0
)

:: Activate venv and run commands
if !NEW_VENV!==1 (
    :: New venv - install requirements and run script
    "%VENV_PATH%\Scripts\python.exe" -m pip install --upgrade pip
    "%VENV_PATH%\Scripts\python.exe" -m pip install -r "%REQUIREMENTS%"
)