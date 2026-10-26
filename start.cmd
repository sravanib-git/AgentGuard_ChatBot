@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run setup.cmd first to prepare Python.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -B run.py
if errorlevel 1 pause
