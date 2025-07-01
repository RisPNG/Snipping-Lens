@echo off
set winpython_ini=%~dp0..\\settings\winpython.ini
(
    echo [debug]
    echo state = disabled
    echo [environment]
    echo ## <?> Uncomment lines to override environment variables
    echo #HOME = %%HOMEDRIVE%%%%HOMEPATH%%\Documents\WinPython%%WINPYVER%%\settings
    echo USERPROFILE = %%HOME%%
    echo #JUPYTER_DATA_DIR = %%HOME%%
    echo #JUPYTERLAB_SETTINGS_DIR = %%HOME%%\.jupyter\lab
    echo #JUPYTERLAB_WORKSPACES_DIR = %%HOME%%\.jupyter\lab\workspaces
    echo #WINPYWORKDIR = %%HOMEDRIVE%%%%HOMEPATH%%\Documents\WinPython%%WINPYVER%%\Notebooks
) > "%winpython_ini%"
