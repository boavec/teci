@echo off
REM One-click update for TECI. Double-click to run.
REM Uses -ExecutionPolicy Bypass for this single invocation only; system settings are not changed.

setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "run.ps1" %*
set RC=%ERRORLEVEL%
if not "%RC%"=="0" (
  echo.
  echo Failed with exit code %RC%
  pause
)
endlocal
exit /b %RC%
