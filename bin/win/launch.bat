@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set BASE_PATH=%~dp0
set LOGFILE=%BASE_PATH%logs\python.log
set VENV_PATH=%BASE_PATH%.venv
set SCRIPT=%BASE_PATH%src\tray_watchdog.py
set TEE_EXE=%BASE_PATH%..\..\etc\tee-x64.exe

"%VENV_PATH%\Scripts\python.exe" "%SCRIPT%"										| "%TEE_EXE%" -a "%LOGFILE%"

echo Output and errors logged to: %LOGFILE%										| "%TEE_EXE%" -a "%LOGFILE%"
exit /b