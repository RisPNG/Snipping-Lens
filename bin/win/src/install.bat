@echo off
setlocal enabledelayedexpansion

:: Set paths
set BASE_PATH=%~dp0
set PYTHON_EXE=%BASE_PATH%WPy64-310111\python-3.10.11.amd64\python.exe
set PYTHON_DIR=%BASE_PATH%WPy64-310111
set PYTHON_DIST_EXE=%BASE_PATH%Winpython64-3.10.11.1.exe
set PYTHON_DOWNLOAD_URL=https://github.com/winpython/winpython/releases/download/6.1.20230527/Winpython64-3.10.11.1.exe

set VENV_PATH=%BASE_PATH%.venv
set REQUIREMENTS=%BASE_PATH%requirements.txt
set SCRIPT=%BASE_PATH%tray_watchdog.py

:: Check if Python exists
if not exist "%PYTHON_EXE%" (
    echo Python not found, downloading and extracting WinPython...

    :: Download WinPython if not present
    if not exist "%PYTHON_DIST_EXE%" (
        powershell -Command "Invoke-WebRequest -Uri '%PYTHON_DOWNLOAD_URL%' -OutFile '%PYTHON_DIST_EXE%'"
        if %ERRORLEVEL% NEQ 0 (
            echo Failed to download WinPython.
            exit /b 1
        )
    )
    :: Extract WinPython portable distribution
    echo Extracting WinPython...
    powershell -Command "Start-Process -FilePath '%PYTHON_DIST_EXE%' -ArgumentList '/VERYSILENT','/DIR=%PYTHON_DIR%' -Wait"
    if not exist "%PYTHON_EXE%" (
        echo Extraction failed, Python still not found.
        exit /b 1
    )
)

:: Check if venv exists
if not exist "%VENV_PATH%" (
    "%PYTHON_EXE%" -m venv "%VENV_PATH%"
    set NEW_VENV=1
) else (
    set NEW_VENV=0
)

:: Activate venv and run commands
if !NEW_VENV!==1 (
    "%VENV_PATH%\Scripts\python.exe" -m pip install --upgrade pip
    "%VENV_PATH%\Scripts\python.exe" -m pip install -r "%REQUIREMENTS%"
)