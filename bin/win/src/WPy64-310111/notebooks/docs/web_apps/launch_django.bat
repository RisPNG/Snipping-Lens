rem configure WinPython environment

cd/D %~dp0\django\todoapp
call ..\..\..\..\..\scripts\env.bat
@echo on
rem launch flask

rem provided per WinPYthon
if not exist  "%WINPYDIR%\Lib\site-packages\Django\" (

echo we are going to install Django suite, ok ?
echo if not CTRL-C or kill this
echo otherwise type on "SPACE BAR"
pause
if not exist  "%WINPYDIR%\Lib\site-packages\Django" pip install Django
)

rem when starting new  project if it was empty new project to create)
rem django-admin startproject todoapp


rem python manage.py startapp todolist

rem this prepare django in general
python manage.py migrate

rem  this just in case
python manage.py makemigrations todolist

rem  this create todolist.0001_initial TodoList table
python manage.py migrate todolist


rem not need to just run the server
rem python manage.py createsuperuser


rem to launch page at port 7000 (default django is 8000, like fastapi)
python -m webbrowser -t "http://127.0.0.1:7000/"

python manage.py runserver 7000

***


 

