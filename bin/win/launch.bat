@echo off
setlocal
cd /d "%~dp0"

set BASE_PATH=%~dp0
set LOGFILE=%BASE_PATH%logs\python.log
set VENV_PATH=%BASE_PATH%..\..\int\win\venv
set SCRIPT=%BASE_PATH%..\..\src\main.py

rem run.vbs starts this with no window, so there is no console to mirror output
rem to and the log is the only reader
>>"%LOGFILE%" echo [%DATE% %TIME%] launching
"%VENV_PATH%\Scripts\python.exe" "%SCRIPT%" >>"%LOGFILE%" 2>&1
