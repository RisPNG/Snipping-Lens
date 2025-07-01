@echo off
call "%~dp0env.bat"
set pydistutils_cfg=%WINPYDIRBASE%\settings\pydistutils.cfg
echo [config]>%pydistutils_cfg%
        