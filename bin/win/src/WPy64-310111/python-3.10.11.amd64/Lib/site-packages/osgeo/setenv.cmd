@echo off
echo Setting environment variables for GDAL
set GDAL_DATA=%~dp0data\gdal
set GDAL_DRIVER_PATH=%~dp0gdalplugins
set PROJ_LIB=%~dp0data\proj
set PATH=%~dp0;%PATH%
set INCLUDE=%INCLUDE%;%~dp0include\gdal
set LIB=%LIB%;%~dp0lib
