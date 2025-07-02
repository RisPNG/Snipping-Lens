@echo off
setlocal enabledelayedexpansion

:: Set paths
set BASE_PATH=%~dp0
set PYTHON_EXE=%BASE_PATH%WPy64-310111\python-3.10.11.amd64\python.exe
set PYTHON_DIR=%BASE_PATH%WPy64-310111
set PYTHON_DIST_EXE=%BASE_PATH%WPy64-310111.zip
set PYTHON_DOWNLOAD_URL=https://github.com/RisPNG/winpython-mini/releases/download/WinPython64m-3.10.11.1/WPy64-310111.zip

set VENV_PATH=%BASE_PATH%.venv
set REQUIREMENTS=%BASE_PATH%requirements.txt
set SCRIPT=%BASE_PATH%tray_watchdog.py

:: Skip download if .exe exists
if not exist "%PYTHON_DIST_EXE%" (
    echo Downloading dependencies...
    curl -L -o "%PYTHON_DIST_EXE%" "%PYTHON_DOWNLOAD_URL%"
    if not exist "%PYTHON_DIST_EXE%" (
        echo Download failed.
        exit /b 1
    )
)

:: Skip extraction if Python exe already exists
if not exist "%PYTHON_EXE%" (
    echo Installing...
    tar -xf "%PYTHON_DIST_EXE%" -C "%BASE_PATH:~0,-1%"
    if not exist "%PYTHON_EXE%" (
        echo Installation failed, please run the setup again.
        exit /b 1
    )
)

echo Setting up environment...
:: Setup virtual environment
if not exist "%VENV_PATH%" (
    "%PYTHON_EXE%" -m venv "%VENV_PATH%"
    set NEW_VENV=1
) else (
    set NEW_VENV=0
)

:: Install requirements
if !NEW_VENV!==1 (
    "%VENV_PATH%\Scripts\python.exe" -m pip install --upgrade pip
    "%VENV_PATH%\Scripts\python.exe" -m pip install -r "%REQUIREMENTS%"
)