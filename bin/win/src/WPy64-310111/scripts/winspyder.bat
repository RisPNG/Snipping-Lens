@echo off
call "%~dp0env_for_icons.bat" %*
rem cd/D "%WINPYWORKDIR%"
if exist "%WINPYDIR%\scripts\spyder3.exe" (
   "%WINPYDIR%\scripts\spyder3.exe" %* -w "%WINPYWORKDIR1%"
) else (
   "%WINPYDIR%\scripts\spyder.exe" %* -w "%WINPYWORKDIR1%"
)  
