rem do the call in one place
call %~dp0pdf_envcall.bat

rem otherwise do it here
rem call ....\WPy64-...\scripts\env.bat

rem see https://github.com/pmaupin/pdfrw/blob/master/examples/rotate.py
rem usage:   rotate.py my.pdf rotation [page[range] ...]
rem          eg. rotate.py 270 1-3 5 7-9
rem          Rotation must be multiple of 90 degrees, clockwise.

%python% %~dp0pdf_rotate.py %1 90
