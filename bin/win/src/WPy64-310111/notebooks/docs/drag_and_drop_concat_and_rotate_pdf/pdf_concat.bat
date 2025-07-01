rem do the call in one place
call %~dp0pdf_envcall.bat

@echo on

rem otherwise do it here
rem call ....\WPy64-...\scripts\env.bat

%python% %~dp0pdf_concat.py %*
