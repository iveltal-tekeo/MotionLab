@echo off
rem MotionLab setup: Python packages into .venv + a check of the programs MotionLab uses.
rem Nothing is installed without asking first. Run it again any time (it only does what is missing).
setlocal EnableExtensions
title MotionLab setup
cd /d "%~dp0"
echo.
echo  MotionLab setup
echo  - installs the Python packages into .venv (inside this folder)
echo  - checks git, ffmpeg, yt-dlp and Claude Code, and offers to install what is missing (winget, you choose)
echo.

rem ---- 1. Python 3.12, 64-bit
set "PY="
where py >nul 2>nul && py -3.12 -c "import sys; assert sys.maxsize > 2**32" >nul 2>nul && set "PY=py -3.12"
if not defined PY goto :nopython
echo [ok] Python 3.12 found

rem ---- 2. .venv + packages
if exist ".venv\Scripts\python.exe" goto :haveenv
echo      creating .venv ...
%PY% -m venv .venv || goto :fail
:haveenv
echo      installing the Python packages from requirements.txt (a few minutes the first time) ...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt || goto :fail
echo [ok] Python packages installed

rem ---- 3. data folders (never uploaded)
if not exist refs mkdir refs
if not exist analysis mkdir analysis
if not exist projects mkdir projects

rem ---- 4. programs
where git >nul 2>nul && (echo [ok] git found) && goto :ffmpeg
if exist "C:\Program Files\Git\cmd\git.exe" (echo [ok] git found) && goto :ffmpeg
echo [ ]  git not found - needed for automatic updates and for sharing knowledge with your friends.
call :offer "Git.Git" "git"
:ffmpeg
where ffmpeg >nul 2>nul && (echo [ok] ffmpeg found) && goto :ytdlp
echo [!]  ffmpeg not found - it is REQUIRED for every analysis.
call :offer "Gyan.FFmpeg" "ffmpeg"
:ytdlp
where yt-dlp >nul 2>nul && (echo [ok] yt-dlp found) && goto :claude
echo [ ]  yt-dlp not found - optional, for "Download from a link" in the app.
call :offer "yt-dlp.yt-dlp" "yt-dlp"
:claude
where claude >nul 2>nul && (echo [ok] Claude Code found) && goto :shortcut
echo [ ]  Claude Code not found - needed for the review and learning steps.
echo      Install it from https://claude.com/claude-code and sign in once by typing: claude

rem ---- 5. your name for shared knowledge (Settings in the app can change it)
:shortcut
echo.
set "WHO="
set /p WHO="Your name for sharing knowledge with friends (letters/numbers, Enter = later): "
if not defined WHO goto :askshortcut
".venv\Scripts\python.exe" -c "import sys; sys.path.insert(0, 'tools'); from motionlab.app import system; print('[ok] name:', system.save({'author': sys.argv[1]})['author'])" "%WHO%"
:askshortcut
echo.
choice /C YN /M "Create a MotionLab shortcut on the Desktop"
if errorlevel 2 goto :done
".venv\Scripts\python.exe" -c "import sys; sys.path.insert(0, 'tools'); from motionlab.app import system; print('[ok] shortcut:', system.make_shortcut('desktop')['path'])"

:done
echo.
echo  Done. Start MotionLab with the shortcut or by double-clicking MotionLab.bat.
echo  The app's Settings page shows which programs it found; it updates itself from GitHub when it starts.
echo  Optional self-check (a few minutes, should end with PASS):  .venv\Scripts\python tools\selftest.py
echo.
pause
exit /b 0

rem ---- helpers
:offer
where winget >nul 2>nul || (echo      Install %~2 yourself, then run setup.bat again. & exit /b 0)
choice /C YN /M "     Install %~2 now with winget"
if errorlevel 2 exit /b 0
winget install --id %~1 -e --accept-source-agreements --accept-package-agreements
echo      Installed. Open a NEW window (or restart the PC) so Windows finds it, then run setup.bat again.
exit /b 0

:nopython
echo [!]  Python 3.12 64-bit not found.
where winget >nul 2>nul || goto :nopython2
choice /C YN /M "     Install Python 3.12 now with winget"
if errorlevel 2 goto :nopython2
winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
echo      Python installed: close this window and run setup.bat again.
pause
exit /b 1
:nopython2
echo      Install Python 3.12 64-bit from https://www.python.org/downloads/ - tick "Add python.exe to PATH" -
echo      then run setup.bat again.
pause
exit /b 1

:fail
echo.
echo [!]  Setup stopped - see the messages above.
pause
exit /b 1
