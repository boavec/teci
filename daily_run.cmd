@echo off
REM Entry point used by the Windows scheduled task.
REM Kept as a separate no-argument script so the task registration
REM never has to nest quotes around a path with options.

call "%~dp0run.cmd" -NoOpen
exit /b %ERRORLEVEL%
