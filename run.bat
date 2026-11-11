@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%~dp0src"
py -m bisar %*
if errorlevel 1 exit /b %errorlevel%
echo.
pause
