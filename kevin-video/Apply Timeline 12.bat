@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -X utf8 soundpilot.py install --project 0928 --timeline "Timeline 12"
if errorlevel 1 (
  echo Close CapCut first, then run this again. Existing edited timelines will not be overwritten.
) else (
  echo Done. Open 0928 in CapCut and select Timeline 12.
)
pause
