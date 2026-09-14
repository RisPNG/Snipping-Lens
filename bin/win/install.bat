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
set LOGFILE=%~dp0..\..\logs\build_win_%dyear%-%dmonth%-%dday%_%dhour%%dmin%%dsec%.log
set BASE_PATH=%~dp0
set ARCH=%PROCESSOR_ARCHITECTURE%
if /i "%PROCESSOR_ARCHITEW6432%"=="ARM64" set ARCH=ARM64

if /i "%ARCH%"=="ARM64" (
    set TEE_EXE=%BASE_PATH%..\..\etc\tee-a64.exe
    set PYTHON_EXE=%BASE_PATH%..\..\int\win\MsPy-3_11_15\python.exe
    set PYTHON_HOME=%BASE_PATH%..\..\int\win\MsPy-3_11_15
    set PYTHON_DIST=%BASE_PATH%..\..\int\win\MsPy-3_11_15.zip
    set PYTHON_DOWNLOAD_URL=https://github.com/RisPNG/MsPy/releases/download/3.11.15/MsPy-3_11_15-Windows-ARM64.zip
) else (
    set TEE_EXE=%BASE_PATH%..\..\etc\tee-x64.exe
    set PYTHON_EXE=%BASE_PATH%..\..\int\win\MsPy-3_11_14\python.exe
    set PYTHON_HOME=%BASE_PATH%..\..\int\win\MsPy-3_11_14
    set PYTHON_DIST=%BASE_PATH%..\..\int\win\MsPy-3_11_14.zip
    set PYTHON_DOWNLOAD_URL=https://github.com/RisPNG/MsPy/releases/download/3.11.14/MsPy-3_11_14-win.zip
)
for %%I in ("%TEE_EXE%") do set TEE_EXE=%%~fI
for %%I in ("%PYTHON_EXE%") do set PYTHON_EXE=%%~fI
for %%I in ("%PYTHON_HOME%") do set PYTHON_HOME=%%~fI
for %%I in ("%PYTHON_DIST%") do set PYTHON_DIST=%%~fI
for %%I in ("%BASE_PATH%..\..\int\win") do set INT_WIN_PATH=%%~fI
set VENV_PATH=%BASE_PATH%..\..\int\win\venv
set REQUIREMENTS=%BASE_PATH%..\..\src\requirements.txt
set REQUIREMENTS_WIN=%BASE_PATH%..\..\src\requirements-win.txt
set REQ_HASH_FILE=%VENV_PATH%\.requirements.sha256

echo ========================================									| "%TEE_EXE%" -a "%LOGFILE%"
echo Script started: %DATE% %TIME%												| "%TEE_EXE%" -a "%LOGFILE%"
echo Architecture: %ARCH%														| "%TEE_EXE%" -a "%LOGFILE%"
echo ========================================									| "%TEE_EXE%" -a "%LOGFILE%"

if not exist "%INT_WIN_PATH%" mkdir "%INT_WIN_PATH%"

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
    tar -xf "%PYTHON_DIST%" -C "%INT_WIN_PATH%"									| "%TEE_EXE%" -a "%LOGFILE%"
    if not exist "%PYTHON_EXE%" (
        echo Installation failed, please run the setup again.					| "%TEE_EXE%" -a "%LOGFILE%"
        goto :end
    )
)

echo Setting up environment...													| "%TEE_EXE%" -a "%LOGFILE%"
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
    "%PYTHON_EXE%" -m venv "%VENV_PATH%"										| "%TEE_EXE%" -a "%LOGFILE%"
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
    echo Dependencies are up to date ^(skipping pip install^)						| "%TEE_EXE%" -a "%LOGFILE%"
    goto :end
)

:install_deps
echo Installing/updating dependencies...										| "%TEE_EXE%" -a "%LOGFILE%"
"%VENV_PATH%\Scripts\python.exe" -m pip install --upgrade pip					| "%TEE_EXE%" -a "%LOGFILE%"
"%VENV_PATH%\Scripts\python.exe" -m pip install -r "%REQUIREMENTS%" -r "%REQUIREMENTS_WIN%"	| "%TEE_EXE%" -a "%LOGFILE%"
echo %NEW_REQ_HASH%> "%REQ_HASH_FILE%"

echo ========================================									| "%TEE_EXE%" -a "%LOGFILE%"
echo Script ended: %DATE% %TIME%												| "%TEE_EXE%" -a "%LOGFILE%"
echo ========================================									| "%TEE_EXE%" -a "%LOGFILE%"

:end
exit /b
