@echo off
setlocal
set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if exist "%PY_EXE%" goto run
set "PY_EXE=python"

:run
"%PY_EXE%" main.py %*
pause

