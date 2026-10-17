@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Local Python environment missing. Run Setup SoundPilot first.
  pause
  exit /b 1
)
start "SoundPilot" /min ".venv\Scripts\python.exe" -X utf8 app.py
