@echo off
call "%~dp0env_for_icons.bat" %*
cd/D "%WINPYWORKDIR1%"
if "%QT_API%"=="" ( set QT_API=pyqt5 )
if "%QT_API%"=="pyqt5" (
    if exist "%WINPYDIR%\Scripts\designer.exe" (
        "%WINPYDIR%\Scripts\designer.exe" %*
    ) else if exist "%WINPYDIR%\Lib\site-packages\qt5_applications\Qt\bin\designer.exe" (
        "%WINPYDIR%\Lib\site-packages\qt5_applications\Qt\bin\designer.exe" %*
    ) else if exist "%WINPYDIR%\Lib\site-packages\pyqt5_tools\Qt\bin\designer.exe" (
        "%WINPYDIR%\Lib\site-packages\pyqt5_tools\Qt\bin\designer.exe" %*
    ) else if exist "%WINPYDIR%\Lib\site-packages\pyqt5-tools\designer.exe" (
        "%WINPYDIR%\Lib\site-packages\pyqt5-tools\designer.exe" %*
    ) else if exist "%WINPYDIR%\Lib\site-packages\PyQt5\designer.exe" (
        "%WINPYDIR%\Lib\site-packages\PyQt5\designer.exe" %*
    ) else if exist "%WINPYDIR%\Lib\site-packages\PySide2\designer.exe" (
        "%WINPYDIR%\Lib\site-packages\PySide2\designer.exe" %*
    ) else (
        "%WINPYDIR%\Lib\site-packages\PySide6\designer.exe" %*
    )
) else (
    "%WINPYDIR%\Lib\site-packages\PySide6\designer.exe" %*
)
