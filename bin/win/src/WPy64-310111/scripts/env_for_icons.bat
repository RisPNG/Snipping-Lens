@echo off
call "%~dp0env.bat"
set WINPYWORKDIR=%WINPYDIRBASE%\Notebooks

rem default is as before: Winpython ..\Notebooks
set WINPYWORKDIR1=%WINPYWORKDIR%

rem if we have a file or directory in %1 parameter, we use that directory 
if not "%~1"=="" (
   if exist "%~1" (
      if exist "%~1\" (
         rem echo it is a directory %~1
	     set WINPYWORKDIR1=%~1
	  ) else (
	  rem echo  it is a file %~1, so we take the directory %~dp1
	  set WINPYWORKDIR1=%~dp1
	  )
   )
) else (
rem if it is launched from another directory , we keep it that one echo %__CD__%
if not "%__CD__%"=="%~dp0" set  WINPYWORKDIR1="%__CD__%"
)
rem remove potential doublequote
set WINPYWORKDIR1=%WINPYWORKDIR1:"=%
rem remove some potential last \
if "%WINPYWORKDIR1:~-1%"=="\" set WINPYWORKDIR1=%WINPYWORKDIR1:~0,-1%

FOR /F "delims=" %%i IN ('cscript /nologo "%~dp0WinpythonIni.vbs"') DO set winpythontoexec=%%i
%winpythontoexec%set winpythontoexec=

rem ******************
rem missing student directory part
rem ******************

if not exist "%WINPYWORKDIR%" mkdir "%WINPYWORKDIR%"

if not exist "%HOME%\.spyder-py%WINPYVER:~0,1%"  mkdir "%HOME%\.spyder-py%WINPYVER:~0,1%"
if not exist "%HOME%\.spyder-py%WINPYVER:~0,1%\workingdir" echo %HOME%\Notebooks>"%HOME%\.spyder-py%WINPYVER:~0,1%\workingdir"

rem ******* make cython use mingwpy part *******
if not exist "%WINPYDIRBASE%\settings\pydistutils.cfg" goto no_cython
if not exist "%HOME%\pydistutils.cfg" xcopy   "%WINPYDIRBASE%\settings\pydistutils.cfg" "%HOME%" 
:no_cython 
