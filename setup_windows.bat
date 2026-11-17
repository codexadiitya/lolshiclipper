@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher not found. Install Python 3.11 or 3.12 from python.org and check Add Python to PATH.
  pause
  exit /b 1
)
where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo FFmpeg is not installed or not on PATH.
  echo Install using: winget install --id Gyan.FFmpeg -e
  echo Reopen your terminal after installation.
  pause
  exit /b 1
)
py -3 -m venv .venv
if errorlevel 1 goto failed
call .venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto failed
call .venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
call .venv\Scripts\python.exe -m pip install faster-whisper
if errorlevel 1 (
  echo Whisper could not be installed. Basic audio-only clipping still works.
)
echo.
echo Setup completed. Double-click START_WINDOWS.bat
pause
exit /b 0
:failed
echo Installation failed. Check your Python / Internet connection, then try again.
pause
exit /b 1
