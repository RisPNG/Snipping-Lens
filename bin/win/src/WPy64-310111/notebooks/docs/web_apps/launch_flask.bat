rem configur WinPython environment
cd/D %~dp0/flask
call ..\..\..\..\scripts\env.bat
@echo on
rem launch flask

rem provided per WinPython otherwise do it

goto not_needed
python -m venv venv
echo the commands will have to be manually typed after this
.\venv\Scripts\activate
:not_needed

if not exist  "%WINPYDIR%\Lib\site-packages\flask_sqlalchemy\" (

echo we are going to install Flask and Flask-SQLAlchemy suite, ok ?
echo if not CTRL-C or kill this
echo otherwise type on "SPACE BAR"
pause
if not exist  "%WINPYDIR%\Lib\site-packages\flask_sqlalchemy" pip install Flask Flask-SQLAlchemy
)


rem to launch page
python -m webbrowser -t "http://127.0.01:5000/"

set FLASK_APP=app.py
set FLASK_ENV=development
flask run