@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0VERIFY.ps1" %*
if errorlevel 1 (echo Verification failed. & pause & exit /b 1)
pause
