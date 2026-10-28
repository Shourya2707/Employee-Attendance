@echo off
setlocal
set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if exist "%PY_EXE%" goto run
set "PY_EXE=python"

:run
echo Starting Employee Attendance Management Web Dashboard...
echo URL: http://127.0.0.1:5000
start http://127.0.0.1:5000
"%PY_EXE%" server.py
pause

