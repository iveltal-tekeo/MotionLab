@echo off
rem MotionLab setup. Double-click it = Install-MotionLab.cmd -Here: it lists what is missing, asks first, installs it
rem and repairs this folder (a ZIP copy gets connected to GitHub). Run it again any time - it only does what is missing.
rem "setup.bat /lab" = only the lab steps below; the installer runs them and passes ML_PY, ML_GRAPHICS, ML_AUTHOR,
rem ML_LANG (its window's language), ML_SHORTCUT_DIR (tests) and ML_INSTALLER. The dispatch stays ONE line: the
rem installer may rewrite this file while it runs (connecting a ZIP copy), and cmd reads nothing after it.
if not exist "%~dp0tools\motionlab\" goto :extract
if /i not "%~1"=="/lab" call "%~dp0Install-MotionLab.cmd" -Here %* & call exit /b %%errorlevel%%
setlocal EnableExtensions

rem ---- the words: English, or Spanish when the installer speaks it (ML_LANG=es, 2026-10-19). ASCII only: cmd reads
rem this file in the console's code page, so the Spanish needs no accents. No & | < > in them (^> = a plain >) and no
rem ) in MLW_HFFOUND (echoed inside brackets); the Python lines read MLW_NAME, MLW_NAMEBAD and MLW_SCOK
set "MLW_TITLE=MotionLab setup"
set "MLW_HEAD= MotionLab setup - the lab steps: Python packages, folders, Claude Code's access, shortcuts"
set "MLW_VENV=     making .venv (MotionLab's own Python, inside this folder) ..."
set "MLW_PIP=     installing MotionLab's Python packages (about 650 MB the first time, a few minutes) ..."
set "MLW_PIPOK=[ok] Python packages"
set "MLW_MCP=[ok] Claude Code may use MotionLab's MCP server (read-only lab data)"
set "MLW_HFFOUND=[ok] HyperFrames found"
set "MLW_HFCHROME=     downloading HyperFrames' Chrome (about 270 MB, once) ..."
set "MLW_HFREADY=[ok] HyperFrames ready"
set "MLW_HFINSTALL=     installing HyperFrames for the motion graphics (about 120 MB, then its Chrome, about 270 MB) ..."
set "MLW_HFOK=[ok] HyperFrames installed (tools\overlays, versions pinned in package-lock.json)"
set "MLW_HFFAIL=[ ]  HyperFrames could not be installed - the motion graphics need it: double-click setup.bat again later."
set "MLW_NAME=[ok] your name for sharing:"
set "MLW_NAMEBAD=- (letters a-z and numbers only)"
set "MLW_SCOK=[ok] shortcut:"
set "MLW_SCFAIL1=[ ]  the"
set "MLW_SCFAIL2=shortcut could not be made - Settings ^> Shortcuts in MotionLab can add it"
set "MLW_DONE=[ok] MotionLab is set up in"
set "MLW_START=     Start it with the MotionLab icon on the Desktop or in the Start menu (or MotionLab.bat)."
set "MLW_NOPY=[!]  Python 3.12 (64-bit) was not found - double-click setup.bat: it installs what is missing."
set "MLW_FAIL=[!]  Setup stopped - see the messages above."
if /i not "%ML_LANG%"=="es" goto :words
set "MLW_TITLE=Preparando MotionLab"
set "MLW_HEAD= Preparando MotionLab: paquetes de Python, carpetas, el acceso de Claude Code y los accesos directos"
set "MLW_VENV=     creando .venv (el Python propio de MotionLab, dentro de esta carpeta) ..."
set "MLW_PIP=     instalando los paquetes de Python de MotionLab (unos 650 MB la primera vez, unos minutos) ..."
set "MLW_PIPOK=[ok] Paquetes de Python"
set "MLW_MCP=[ok] Claude Code puede usar el servidor MCP de MotionLab (solo lee los datos)"
set "MLW_HFFOUND=[ok] HyperFrames encontrado"
set "MLW_HFCHROME=     descargando el Chrome de HyperFrames (unos 270 MB, una sola vez) ..."
set "MLW_HFREADY=[ok] HyperFrames listo"
set "MLW_HFINSTALL=     instalando HyperFrames para Motion Graphics (unos 120 MB y luego su Chrome, unos 270 MB) ..."
set "MLW_HFOK=[ok] HyperFrames instalado (tools\overlays, versiones fijadas en package-lock.json)"
set "MLW_HFFAIL=[ ]  No se pudo instalar HyperFrames, que Motion Graphics necesita: vuelve a hacer doble clic en setup.bat en otro momento."
set "MLW_NAME=[ok] tu nombre para compartir:"
set "MLW_NAMEBAD=- (solo letras a-z y cifras)"
set "MLW_SCOK=[ok] acceso directo:"
set "MLW_SCFAIL1=[ ]  no se pudo crear el acceso directo"
set "MLW_SCFAIL2=- en MotionLab puedes crearlo en Ajustes ^> Accesos directos"
set "MLW_DONE=[ok] MotionLab listo en"
set "MLW_START=     Para abrirlo: el icono de MotionLab en el escritorio o en Inicio (o MotionLab.bat)."
set "MLW_NOPY=[!]  No se ha encontrado Python 3.12 (64 bits): haz doble clic en setup.bat, que instala lo que falta."
set "MLW_FAIL=[!]  Algo ha fallado: mira los mensajes de arriba."
:words
title %MLW_TITLE%
cd /d "%~dp0"
echo.
echo %MLW_HEAD%

rem ---- 1. .venv = MotionLab's own Python (3.12, 64-bit): ML_PY from the installer, else the py launcher
if exist ".venv\Scripts\python.exe" goto :haveenv
echo %MLW_VENV%
if defined ML_PY goto :venvpy
where py >nul 2>nul || goto :nopython
py -3.12 -c "import sys; assert sys.maxsize > 2**32" >nul 2>nul || goto :nopython
py -3.12 -m venv .venv || goto :fail
goto :haveenv
:venvpy
"%ML_PY%" -m venv .venv || goto :fail
:haveenv

rem ---- 2. the Python packages - again only when requirements.txt changed (the stamp .venv\.requirements.sha256)
".venv\Scripts\python.exe" -c "import hashlib, pathlib, sys; s = pathlib.Path('.venv/.requirements.sha256'); sys.exit(0 if s.is_file() and s.read_text().strip() == hashlib.sha256(pathlib.Path('requirements.txt').read_bytes()).hexdigest() else 1)" && goto :pipok
echo %MLW_PIP%
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt || goto :fail
".venv\Scripts\python.exe" -c "import hashlib, pathlib; pathlib.Path('.venv/.requirements.sha256').write_text(hashlib.sha256(pathlib.Path('requirements.txt').read_bytes()).hexdigest())"
:pipok
echo %MLW_PIPOK%

rem ---- 3. your data folders (never uploaded)
if not exist refs mkdir refs
if not exist analysis mkdir analysis
if not exist projects mkdir projects

rem ---- 4. MotionLab's MCP server (read-only lab data, .mcp.json) approved once, so Claude windows start at once
".venv\Scripts\python.exe" tools\mcp_server.py --enable >nul && echo %MLW_MCP%

rem ---- 5. HyperFrames for the motion graphics (ML_GRAPHICS=1 = the installer's question answered yes)
if not "%ML_GRAPHICS%"=="1" goto :name
if not exist "tools\overlays\node_modules\hyperframes\bin\hyperframes.mjs" goto :hfinstall
dir /s /b "%USERPROFILE%\.cache\hyperframes\chrome\chrome-headless-shell.exe" >nul 2>nul && (echo %MLW_HFFOUND%) && goto :name
echo %MLW_HFCHROME%
".venv\Scripts\python.exe" tools\overlay.py doctor --fix >nul
dir /s /b "%USERPROFILE%\.cache\hyperframes\chrome\chrome-headless-shell.exe" >nul 2>nul || goto :hffail
echo %MLW_HFREADY%
goto :name
:hfinstall
echo %MLW_HFINSTALL%
".venv\Scripts\python.exe" tools\overlay.py install || goto :hffail
echo %MLW_HFOK%
goto :name
:hffail
echo %MLW_HFFAIL%

rem ---- 6. your name for sharing knowledge (the installer asks; Settings in the app can change it) and, into a NEW
rem settings.json only, the installer's language: ML_LANG=es = a Spanish friend's MotionLab starts in Spanish; an
rem existing settings.json keeps its language
:name
set "ML_NEWLANG="
if /i "%ML_LANG%"=="es" if not exist "settings.json" set "ML_NEWLANG=es"
if not defined ML_AUTHOR if not defined ML_NEWLANG goto :shortcuts
".venv\Scripts\python.exe" -c "import os, sys; sys.path.insert(0, 'tools'); from motionlab.app import system; e = os.environ.get; a = e('ML_AUTHOR', ''); s = system.save({k: v for k, v in (('author', a), ('language', e('ML_NEWLANG', ''))) if v}); a and print(e('MLW_NAME'), s['author'] or e('MLW_NAMEBAD'))"

rem ---- 7. the MotionLab icon on the Desktop and in the Start menu (ML_SHORTCUT_DIR = a test folder instead)
:shortcuts
for %%w in (desktop startmenu) do ".venv\Scripts\python.exe" -c "import os, sys; sys.path.insert(0, 'tools'); from pathlib import Path; from motionlab.app import system; t = os.environ.get('ML_SHORTCUT_DIR'); d = Path(t, sys.argv[1]) if t else None; d and d.mkdir(parents=True, exist_ok=True); print(os.environ['MLW_SCOK'], system.make_shortcut(sys.argv[1], d)['path'])" %%w 2>nul || echo %MLW_SCFAIL1% %%w %MLW_SCFAIL2%

echo.
echo %MLW_DONE% %CD%
if not defined ML_INSTALLER echo %MLW_START%
exit /b 0

:nopython
echo %MLW_NOPY%
if not defined ML_INSTALLER pause
exit /b 1

:fail
echo.
echo %MLW_FAIL%
if not defined ML_INSTALLER pause
exit /b 1

:extract
echo.
echo  This is not a whole MotionLab folder.
echo  Extract the ZIP first (right-click it ^> Extract All), then double-click setup.bat in the extracted folder.
echo.
pause
exit /b 1
