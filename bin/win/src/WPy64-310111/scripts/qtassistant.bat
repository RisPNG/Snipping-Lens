@echo off
call "%~dp0env_for_icons.bat" %*
cd/D "%WINPYWORKDIR1%"
if "%QT_API%"=="" ( set QT_API=pyqt5 )
if "%QT_API%"=="pyqt5" (
    if exist "%WINPYDIR%\Scripts\assistant.exe" (
        "%WINPYDIR%\Scripts\assistant.exe" %*
    ) else if exist "%WINPYDIR%\Lib\site-packages\qt5_applications\Qt\bin\assistant.exe" (
        "%WINPYDIR%\Lib\site-packages\qt5_applications\Qt\bin\assistant.exe" %*
    ) else if exist "%WINPYDIR%\Lib\site-packages\pyqt5_tools\Qt\bin\assistant.exe" (
        "%WINPYDIR%\Lib\site-packages\pyqt5_tools\Qt\bin\assistant.exe" %*
    ) else if exist "%WINPYDIR%\Lib\site-packages\pyqt5-tools\assistant.exe" (
        "%WINPYDIR%\Lib\site-packages\pyqt5-tools\assistant.exe" %*
    ) else if exist "%WINPYDIR%\Lib\site-packages\PyQt5\assistant.exe" (
        "%WINPYDIR%\Lib\site-packages\PyQt5\assistant.exe" %*
    ) else if exist "%WINPYDIR%\Lib\site-packages\PySide2\assistant.exe" (
        "%WINPYDIR%\Lib\site-packages\PySide2\assistant.exe" %*
    ) else (
        "%WINPYDIR%\Lib\site-packages\PySide6\assistant.exe" %*
    )
) else (
    "%WINPYDIR%\Lib\site-packages\PySide6\assistant.exe" %*
)
