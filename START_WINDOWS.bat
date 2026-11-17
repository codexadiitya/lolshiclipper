@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Not installed. Run setup_windows.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" dashboard.py
if errorlevel 1 pause
