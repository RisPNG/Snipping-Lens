@echo off
call "%~dp0env_for_icons.bat" %*
cd/D "%WINPYWORKDIR1%"
if exist "%WINPYDIR%\Lib\site-packages\PyQt5\examples\qtdemo\qtdemo.py" (
    "%WINPYDIR%\python.exe" "%WINPYDIR%\Lib\site-packages\PyQt5\examples\qtdemo\qtdemo.py"
)  
if exist "%WINPYDIR%\Lib\site-packages\PySide2\examples\datavisualization\bars3d.py" (
    "%WINPYDIR%\python.exe" "%WINPYDIR%\Lib\site-packages\PySide2\examples\datavisualization\bars3d.py"
)
