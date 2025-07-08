@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
for /f "tokens=2-4 delims=/ " %%a in ("%DATE%") do (
    set dmonth=%%a
    set dday=%%b
    set dyear=%%c
)
for /f "tokens=1-3 delims=:." %%a in ("%TIME%") do (
    set dhour=%%a
    set dmin=%%b
    set dsec=%%c
)
set dhour=%dhour: =0%
set LOGFILE=..\..\logs\build_win_%dyear%-%dmonth%-%dday%_%dhour%%dmin%%dsec%.log
set TEE_EXE=%~dp0..\..\etc\tee-x64.exe
set BASE_PATH=%~dp0
set PYTHON_EXE=%BASE_PATH%..\..\int\WPy64-310111\python-3.10.11.amd64\python.exe
set PYTHON_DIR=%BASE_PATH%..\..\int\WPy64-310111
set PYTHON_DIST=%BASE_PATH%..\..\int\WPy64-310111.zip
set PYTHON_DOWNLOAD_URL=https://github.com/RisPNG/winpython-mini/releases/download/WinPython64m-3.10.11.1/WPy64-310111.zip
set VENV_PATH=%BASE_PATH%.venv
set REQUIREMENTS=%BASE_PATH%src\requirements.txt
set SCRIPT=%BASE_PATH%src\tray_watchdog.py

echo ========================================									| "%TEE_EXE%" -a "%LOGFILE%"
echo Script started: %DATE% %TIME%												| "%TEE_EXE%" -a "%LOGFILE%"
echo ========================================									| "%TEE_EXE%" -a "%LOGFILE%"

if not exist "%PYTHON_DIST%" (
    echo Downloading dependencies...											| "%TEE_EXE%" -a "%LOGFILE%"
    echo curl -L -o "%PYTHON_DIST%" "%PYTHON_DOWNLOAD_URL%"						| "%TEE_EXE%" -a "%LOGFILE%"
    curl -L -o "%PYTHON_DIST%" "%PYTHON_DOWNLOAD_URL%"							| "%TEE_EXE%" -a "%LOGFILE%"
    if not exist "%PYTHON_DIST%" (
        echo Download failed.													| "%TEE_EXE%" -a "%LOGFILE%"
        goto :end
    )
)

if not exist "%PYTHON_EXE%" (
    echo Installing...															| "%TEE_EXE%" -a "%LOGFILE%"
    tar -xf "%PYTHON_DIST%" -C "%BASE_PATH%..\..\int"							| "%TEE_EXE%" -a "%LOGFILE%"
    if not exist "%PYTHON_EXE%" (
        echo Installation failed, please run the setup again.					| "%TEE_EXE%" -a "%LOGFILE%"
        goto :end
    )
)

echo Setting up environment...													| "%TEE_EXE%" -a "%LOGFILE%"
if not exist "%VENV_PATH%" (
    "%PYTHON_EXE%" -m venv "%VENV_PATH%"										| "%TEE_EXE%" -a "%LOGFILE%"
    set NEW_VENV=1
) else (
    set NEW_VENV=0
)

if "%NEW_VENV%"=="1" (
    "%VENV_PATH%\Scripts\python.exe" -m pip install --upgrade pip				| "%TEE_EXE%" -a "%LOGFILE%"
    "%VENV_PATH%\Scripts\python.exe" -m pip install -r "%REQUIREMENTS%"			| "%TEE_EXE%" -a "%LOGFILE%"
)

echo ========================================									| "%TEE_EXE%" -a "%LOGFILE%"
echo Script ended: %DATE% %TIME%												| "%TEE_EXE%" -a "%LOGFILE%"
echo ========================================									| "%TEE_EXE%" -a "%LOGFILE%"

:end
exit /b