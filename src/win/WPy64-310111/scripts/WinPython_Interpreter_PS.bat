@echo off
rem no safe bet (for comparisons)
Powershell.exe -Command "& {Start-Process PowerShell.exe -ArgumentList '-ExecutionPolicy RemoteSigned -noexit -File ""%~dp0WinPython_PS_Prompt.ps1""'}"
exit
