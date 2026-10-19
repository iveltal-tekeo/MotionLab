@echo off
rem MotionLab app: double-click to open. Starts a small local server (127.0.0.1 only) and a window;
rem the server stops by itself after the window is closed. Problems: see .app\server.log
rem Not set up yet (no .venv): setup.bat first - on ONE line, as setup.bat may rewrite this file while it runs.
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" echo. & echo  MotionLab is not set up yet - the setup starts now. & call "%~dp0setup.bat" & exit /b
start "" ".venv\Scripts\pythonw.exe" "tools\app.py"
