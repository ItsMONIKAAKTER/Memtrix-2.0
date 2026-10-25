@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto ready
where py >nul 2>nul
if errorlevel 1 (
  python -m venv .venv
) else (
  py -3 -m venv .venv
)
if errorlevel 1 goto failed
:ready
.venv\Scripts\python.exe -c "import pygame" >nul 2>nul
if errorlevel 1 .venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
.venv\Scripts\python.exe main.py
if errorlevel 1 goto failed
exit /b 0
:failed
echo.
echo Startup failed. Install Python 3.11 or newer and check the message above.
pause
exit /b 1
