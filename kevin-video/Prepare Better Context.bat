@echo off
cd /d "%~dp0"
set /p TASK_TIMELINE=Timeline name (for example Timeline 13):
".venv\Scripts\python.exe" -X utf8 context_pipeline.py --project 0928 --timeline "%TASK_TIMELINE%"
echo Give Codex outputs/enhanced_brief.json to choose and place the sounds using files only.
pause
