@echo off
rem MotionLab app: double-click to open. Starts a small local server (127.0.0.1 only) and a window;
rem the server stops by itself after the window is closed. Problems: see .app\server.log
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" "tools\app.py"
