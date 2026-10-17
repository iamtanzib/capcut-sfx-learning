@echo off
cd /d "%~dp0"
set /p TASK_TIMELINE=Timeline name (for example Timeline 13):
".venv\Scripts\python.exe" -X utf8 context_pipeline.py --project 0928 --timeline "%TASK_TIMELINE%"
echo Tell Codex to read outputs/enhanced_brief.json and place the sound effects using files only.
pause
