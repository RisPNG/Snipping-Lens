@echo off
call "%~dp0env_for_icons.bat"  %*
cd/D "%WINPYDIR%"
"%WINPYDIR%\scripts\pyzo.exe" %*
