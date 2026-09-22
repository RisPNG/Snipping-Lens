@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
rem inherited from a PowerShell 7 session, the module path makes Windows
rem PowerShell miss Get-FileHash; unset, it falls back to its own
set PSModulePath=
for /f %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HHmmss"') do set LOGSTAMP=%%T
set LOGFILE=%~dp0..\..\logs\build_win_%LOGSTAMP%.log
rem exported so PowerShell reads the path from the environment instead of
rem having it pasted into a command line it would have to re-quote
set "SNIPLENS_LOG=%LOGFILE%"
set BASE_PATH=%~dp0
set ARCH=%PROCESSOR_ARCHITECTURE%
if /i "%PROCESSOR_ARCHITEW6432%"=="ARM64" set ARCH=ARM64

if /i "%ARCH%"=="ARM64" (
    set PYTHON_EXE=%BASE_PATH%..\..\int\win\MsPy-3_11_15\python.exe
    set PYTHON_HOME=%BASE_PATH%..\..\int\win\MsPy-3_11_15
    set PYTHON_DIST=%BASE_PATH%..\..\int\win\MsPy-3_11_15.zip
    set PYTHON_DOWNLOAD_URL=https://github.com/RisPNG/MsPy/releases/download/3.11.15/MsPy-3_11_15-Windows-ARM64.zip
) else (
    set PYTHON_EXE=%BASE_PATH%..\..\int\win\MsPy-3_11_14\python.exe
    set PYTHON_HOME=%BASE_PATH%..\..\int\win\MsPy-3_11_14
    set PYTHON_DIST=%BASE_PATH%..\..\int\win\MsPy-3_11_14.zip
    set PYTHON_DOWNLOAD_URL=https://github.com/RisPNG/MsPy/releases/download/3.11.14/MsPy-3_11_14-win.zip
)
for %%I in ("%PYTHON_EXE%") do set PYTHON_EXE=%%~fI
for %%I in ("%PYTHON_HOME%") do set PYTHON_HOME=%%~fI
for %%I in ("%PYTHON_DIST%") do set PYTHON_DIST=%%~fI
for %%I in ("%BASE_PATH%..\..\int\win") do set INT_WIN_PATH=%%~fI
set VENV_PATH=%BASE_PATH%..\..\int\win\venv
set REQUIREMENTS=%BASE_PATH%..\..\src\requirements.txt
set REQUIREMENTS_WIN=%BASE_PATH%..\..\src\requirements-win.txt
set REQ_HASH_FILE=%VENV_PATH%\.requirements.sha256

call :log "========================================"
call :log "Script started: %DATE% %TIME%"
call :log "Architecture: %ARCH%"
call :log "========================================"

if not exist "%INT_WIN_PATH%" mkdir "%INT_WIN_PATH%"

if not exist "%PYTHON_DIST%" (
    call :log "Downloading dependencies..."
    call :log "curl -L -o %PYTHON_DIST% %PYTHON_DOWNLOAD_URL%"
    curl -L -o "%PYTHON_DIST%" "%PYTHON_DOWNLOAD_URL%"
    if not exist "%PYTHON_DIST%" (
        call :log "Download failed."
        goto :end
    )
)

if not exist "%PYTHON_EXE%" (
    call :log "Installing..."
    tar -xf "%PYTHON_DIST%" -C "%INT_WIN_PATH%"
    if not exist "%PYTHON_EXE%" (
        call :log "Installation failed, please run the setup again."
        goto :end
    )
)

call :log "Setting up environment..."
set NEW_VENV=0
if not exist "%VENV_PATH%\Scripts\python.exe" (
    set NEW_VENV=1
) else if exist "%VENV_PATH%\pyvenv.cfg" (
    findstr /i /c:"home = %PYTHON_HOME%" "%VENV_PATH%\pyvenv.cfg" >nul
    if errorlevel 1 set NEW_VENV=1
) else (
    set NEW_VENV=1
)

if "%NEW_VENV%"=="1" (
    if exist "%VENV_PATH%" rmdir /s /q "%VENV_PATH%"
    "%PYTHON_EXE%" -m venv "%VENV_PATH%"
)

set NEW_REQ_HASH=0
if exist "%REQ_HASH_FILE%" (
    for /f "usebackq delims=" %%H in ("%REQ_HASH_FILE%") do set OLD_REQ_HASH=%%H
) else (
    set OLD_REQ_HASH=none
)
powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 '%REQUIREMENTS%').Hash + '-' + (Get-FileHash -Algorithm SHA256 '%REQUIREMENTS_WIN%').Hash" > "%TEMP%\sniplens_req_hash.txt"
set /p NEW_REQ_HASH=<"%TEMP%\sniplens_req_hash.txt"
del "%TEMP%\sniplens_req_hash.txt"

if "%NEW_VENV%"=="1" goto :install_deps
if "%OLD_REQ_HASH%"=="%NEW_REQ_HASH%" (
    call :log "Dependencies are up to date, skipping pip install"
    goto :end
)

:install_deps
call :log "Installing/updating dependencies..."
"%VENV_PATH%\Scripts\python.exe" -m pip install --upgrade pip 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath $env:SNIPLENS_LOG -Append"
"%VENV_PATH%\Scripts\python.exe" -m pip install -r "%REQUIREMENTS%" -r "%REQUIREMENTS_WIN%" 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath $env:SNIPLENS_LOG -Append"
echo %NEW_REQ_HASH%> "%REQ_HASH_FILE%"

call :log "========================================"
call :log "Script ended: %DATE% %TIME%"
call :log "========================================"

:end
exit /b

rem shows the line and appends it to the build log, which is what the bundled
rem tee binaries used to do
:log
echo %~1
>>"%LOGFILE%" echo %~1
exit /b
