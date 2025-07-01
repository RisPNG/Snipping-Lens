rem configur WinPython environment
cd/D %~dp0/fastapi
call ..\..\..\..\scripts\env.bat
@echo on

rem provided per WinPython

if not exist  "%WINPYDIR%\Lib\site-packages\fastapi" (
echo we are going to install fastapi and uvicorn suite, ok ?
echo if not CTRL-C or kill this
echo otherwise type on "SPACE BAR"
pause
if not exist  "%WINPYDIR%\Lib\site-packages\fastapi"  pip install fastapi "uvicorn[standard]" python-multipart sqlalchemy jinja2
)
 


rem to launch page
python -m webbrowser -t "http://127.0.0.1:8000/"
python -m webbrowser -t "http://127.0.0.1:8000/docs"

uvicorn app:app --reload

