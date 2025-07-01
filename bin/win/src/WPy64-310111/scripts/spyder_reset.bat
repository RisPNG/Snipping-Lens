@echo off
call "%~dp0env_for_icons.bat" %*
cd/D "%WINPYWORKDIR1%"
if exist "%WINPYDIR%\scripts\spyder3.exe" (
    "%WINPYDIR%\scripts\spyder3.exe" --reset %*
) else (
    "%WINPYDIR%\scripts\spyder.exe" --reset %*
)
