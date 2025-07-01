@echo off
call "%~dp0env_for_icons.bat" %*
cd/D "%WINPYWORKDIR1%"
if "%QT_API%"=="" ( set QT_API=pyqt5 )
if "%QT_API%"=="pyqt5" (
    if exist "%WINPYDIR%\Scripts\linguist.exe" (
        "%WINPYDIR%\Scripts\linguist.exe" %*
    ) else if exist "%WINPYDIR%\Lib\site-packages\qt5_applications\Qt\bin\linguist.exe" (
        "%WINPYDIR%\Lib\site-packages\qt5_applications\Qt\bin\linguist.exe" %*
    ) else if exist "%WINPYDIR%\Lib\site-packages\pyqt5_tools\Qt\bin\linguist.exe" (
        "%WINPYDIR%\Lib\site-packages\pyqt5_tools\Qt\bin\linguist.exe" %*
    ) else if exist "%WINPYDIR%\Lib\site-packages\pyqt5-tools\linguist.exe" (
        "%WINPYDIR%\Lib\site-packages\pyqt5-tools\linguist.exe" %*
    ) else if exist "%WINPYDIR%\Lib\site-packages\pyqt5_tools\linguist.exe" (
        "%WINPYDIR%\Lib\site-packages\pyqt5_tools\linguist.exe" %*
    ) else if exist "%WINPYDIR%\Lib\site-packages\PyQt5\linguist.exe" (
        cd/D "%WINPYDIR%\Lib\site-packages\PyQt5"
        "%WINPYDIR%\Lib\site-packages\PyQt5\linguist.exe" %*
        "%WINPYDIR%\Lib\site-packages\pyqt5_tools\linguist.exe" %*
    ) else if exist "%WINPYDIR%\Lib\site-packages\PySide2\linguist.exe" (
        "%%WINPYDIR%\Lib\site-packages\PySide2\linguist.exe" %*
    ) else (
        "%WINPYDIR%\Lib\site-packages\PySide6\linguist.exe" %*
    )
) else (
    "%WINPYDIR%\Lib\site-packages\PySide6\linguist.exe" %*
)

