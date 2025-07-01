@echo off
call "%~dp0env_for_icons.bat" %*
cd/D "%WINPYWORKDIR1%"
"%WINPYDIR%\scripts\jupyter-nbclassic.exe" %*
