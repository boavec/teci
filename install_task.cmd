@echo off
REM Register / check / remove the daily TECI update task.
REM Double-click to register for 09:30 daily.
REM For other options: install_task.cmd -At "21:15"  /  -Status  /  -Remove

setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "install_task.ps1" %*
set RC=%ERRORLEVEL%
echo.
pause
endlocal
exit /b %RC%
