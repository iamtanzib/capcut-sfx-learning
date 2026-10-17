@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0INSTALL_CLAUDE_CODE.ps1" %*
if errorlevel 1 (echo Setup stopped. Read the error above. & pause & exit /b 1)
pause
