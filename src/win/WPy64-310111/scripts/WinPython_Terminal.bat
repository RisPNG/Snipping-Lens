@echo off
call "%~dp0env_for_icons.bat"  %*
if not "%WINPYWORKDIR%"=="%WINPYWORKDIR1%" cd %WINPYWORKDIR1%
%USERPROFILE%\AppData\Local\Microsoft\WindowsApps\wt.exe
exit
