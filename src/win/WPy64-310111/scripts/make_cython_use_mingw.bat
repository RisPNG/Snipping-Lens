@echo off
call "%~dp0env.bat"

rem ******************
rem mingw part
rem ******************

set pydistutils_cfg=%WINPYDIRBASE%\settings\pydistutils.cfg

set tmp_blank=
(
    echo [config]
    echo compiler=mingw32
    echo.
    echo [build]
    echo compiler=mingw32
    echo.
    echo [build_ext]
    echo compiler=mingw32
) > "%pydistutils_cfg%"

echo cython has been set to use mingw32
echo to remove this, remove file "%pydistutils_cfg%"

rem pause

