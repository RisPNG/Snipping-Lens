set BASE_PATH=%~dp0
set VENV_PATH=%BASE_PATH%.venv
set SCRIPT=%BASE_PATH%tray_watchdog.py

:: Continue to run your script, if needed
"%VENV_PATH%\Scripts\python.exe" "%SCRIPT%"