@echo off
REM Build Snipping Lens Windows executable using PyInstaller in a virtual environment

REM Set venv directory
set VENV_DIR=venv

REM Check if current directory is inside build or dist
for %%F in ("%cd%") do (
    set "CURDIR=%%~nxF"
)
if /I "%CURDIR%"=="build" (
    echo ERROR: Cannot run build script from inside the build directory.
    exit /b 1
)
if /I "%CURDIR%"=="dist" (
    echo ERROR: Cannot run build script from inside the dist directory.
    exit /b 1
)

REM Kill running Snipping Tool and SnippingLens processes
for %%P in (SnippingTool.exe ScreenClippingHost.exe ScreenSketch.exe SnippingLens.exe) do (
    taskkill /f /im %%P >nul 2>&1
)

REM Create virtual environment if it doesn't exist
if not exist %VENV_DIR% (
    python -m venv %VENV_DIR%
)

REM Activate the virtual environment
call %VENV_DIR%\Scripts\activate

REM Verify virtual environment activation
IF NOT DEFINED VIRTUAL_ENV (
    echo Failed to activate virtual environment!
    exit /b 1
)

REM Upgrade pip and install dependencies in the venv
python -m pip install --upgrade pip
python -m pip install pyinstaller pillow requests psutil pyqt5

REM Clean previous builds
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Build the executable using PyInstaller from the venv
pyinstaller --noconfirm --onefile --windowed --icon=my_icon.ico --add-data "my_icon.png;." --name SnippingLens snipping_lens.py

REM Notify user of output location
echo.
echo Build complete! The executable is located in the dist folder as SnippingLens.exe