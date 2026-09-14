@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set BASE_PATH=%~dp0
set LOGFILE=%BASE_PATH%logs\python.log
set VENV_PATH=%BASE_PATH%..\..\int\win\venv
set SCRIPT=%BASE_PATH%..\..\src\main.py
set ARCH=%PROCESSOR_ARCHITECTURE%
if /i "%PROCESSOR_ARCHITEW6432%"=="ARM64" set ARCH=ARM64
if /i "%ARCH%"=="ARM64" (
    set TEE_EXE=%BASE_PATH%..\..\etc\tee-a64.exe
) else (
    set TEE_EXE=%BASE_PATH%..\..\etc\tee-x64.exe
)
for %%I in ("%TEE_EXE%") do set TEE_EXE=%%~fI

"%VENV_PATH%\Scripts\python.exe" "%SCRIPT%"										| "%TEE_EXE%" -a "%LOGFILE%"

echo Output and errors logged to: %LOGFILE%										| "%TEE_EXE%" -a "%LOGFILE%"
exit /b
