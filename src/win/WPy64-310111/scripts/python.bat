@echo off
call "%~dp0env_for_icons.bat"  %*
rem backward compatibility for  python command-line users
if not "%WINPYWORKDIR%"=="%WINPYWORKDIR1%" cd %WINPYWORKDIR1%
"%WINPYDIR%\python.exe"  %*
