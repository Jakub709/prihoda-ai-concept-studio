@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -X utf8 start.py
) else if exist "..\.venv\Scripts\python.exe" (
  "..\.venv\Scripts\python.exe" -X utf8 start.py
) else (
  py -3 -X utf8 start.py
)
if errorlevel 1 pause
