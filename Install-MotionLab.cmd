<# : MotionLab installer - double-click it (cmd runs the next line; PowerShell skips this block)
@echo off & set "ML_SELF=%~f0" & powershell -NoProfile -ExecutionPolicy Bypass -Command "& ([scriptblock]::Create([IO.File]::ReadAllText($env:ML_SELF))) %* %ML_ARGS%" & call exit /b %%errorlevel%%
#>
# MotionLab's installer (2026-10-18; the user: "we also kinda need to improve the first installation process, since
# its very hard for people to read the steps or install git or do all fo that throught the terminal ... its just the
# setup that need a "idiot-proof" imporvment"). One file, UTF-8 without a BOM: ASCII except the Spanish words
# ($StringsEs), which only PowerShell reads ([IO.File]::ReadAllText = UTF-8; cmd never reads past line 2). The line
# above is its only batch part: one line, no labels, so it runs with LF or CRLF line endings and stays safe when the
# file is rewritten while it runs; cmd hands the whole file to PowerShell, which skips that block as a comment and
# keeps the text in memory.
#
#   Double-click it (install mode, e.g. from Downloads): every question first (the folder, the plan, motion graphics,
#   your name), then Git, then MotionLab cloned from GitHub - the last tested version on a local main, what the Update
#   button installs - then the CLONED copy's own installer goes on (-Here -Yes + the answers), so an old download still
#   finishes with the newest tested steps.
#   -Here (setup.bat runs it): finish or repair the MotionLab folder this file sits in - the missing programs (winget;
#   Claude Code with Anthropic's own installer + the sign-in), a ZIP copy connected to GitHub (updater.connect), then
#   setup.bat /lab (Python packages, folders, the MCP approval, HyperFrames, shortcuts). Run it again any time: it only
#   does what is missing. It never touches videos and never pulls, resets or deletes anything.
#
# Developers and tests (tools\dev\install_test.py): -DryRun = every command printed, nothing changed; -Yes = the
# default answers; -NoStart; -NoClaude; -Folder / -Repo / -ShortcutFolder / -Graphics; -Lang en|es = the window's
# language (without it: Get-Language below). A value with spaces goes in the ML_ARGS environment variable in
# PowerShell syntax (set ML_ARGS=-Folder 'D:\My Lab'): cmd splits %* at spaces.
# ML_TEST_PATHFILE = test mode: that file's folders stand in for the registry's PATH, programs are found only there
# (a fake winget first on PATH adds them), and the Claude installer, the start and Windows' broadcast never run.
# Keep the parameters below in later versions: an older downloaded copy hands its answers over with them.
param([switch]$Here, [switch]$DryRun, [switch]$Yes, [switch]$NoStart, [switch]$NoClaude, [string]$Folder = 'C:\MotionLab',
      [string]$Repo = 'https://github.com/iveltal-tekeo/MotionLab.git', [string]$ShortcutFolder,
      [ValidateSet('ask', 'yes', 'no')][string]$Graphics = 'ask', [ValidateSet('en', 'es')][string]$Lang)

# ---------------------------------------------------------------------------------------------------------------------
# Every word the installer says, in one table ({0} {1} = filled in); $StringsEs below = the same keys in Spanish.
$Strings = @{
    title            = 'MotionLab installer'
    intro            = 'MotionLab takes apart the editing of videos you like and helps you rebuild it with your own clips - on your own PC.'
    dry              = 'Dry run: nothing is installed or changed, the commands are only shown.'
    would            = 'would run: {0}'
    admin            = 'Please close this window and double-click the installer normally, not with "Run as administrator": MotionLab and its programs belong to your own Windows account. Windows asks for permission by itself where a program needs it.'
    test_desk        = 'Test mode needs -ShortcutFolder: a test never touches the real Desktop or Start menu.'
    not_lab          = 'This is not a MotionLab folder: {0}'
    folder_ask       = 'Where should MotionLab go? Press Enter for {0}, or type another folder'
    folder_full      = 'Type a whole folder, for example D:\MotionLab.'
    folder_file      = 'That is a file, not a folder.'
    folder_other     = 'This folder already holds other files. MotionLab only goes into a new or empty folder (or its own), so nothing of yours is ever mixed in. Pick another folder.'
    folder_protected = 'Windows protects this folder. Pick another one, for example C:\MotionLab.'
    folder_bad       = 'Not a good place for MotionLab: {0}.'
    folder_anyway    = 'Use it anyway?'
    place_downloads  = 'the Downloads folder (Windows can empty it by itself)'
    place_desktop    = 'the Desktop'
    place_documents  = 'the Documents folder (often kept on OneDrive)'
    place_onedrive   = 'a OneDrive folder (it would upload gigabytes and keep files online only)'
    place_temp       = 'a temporary folder (Windows empties it)'
    place_accents    = 'accents or other special letters in the folder name (some programs fail on them)'
    place_long       = 'a long folder name (some programs fail on very long paths)'
    found_copy       = 'MotionLab is already in {0}: the installer finishes or repairs that copy.'
    old_copy         = 'The MotionLab copy in {0} is older than this installer. Open MotionLab and click Update, or double-click setup.bat in that folder - or pick another folder.'
    old_clone        = 'This version of MotionLab finishes with its own setup.bat.'
    plan_head        = 'This is what happens - nothing starts before you answer:'
    plan_none        = 'Every program MotionLab needs is on this PC already.'
    plan_have        = 'Already on this PC: {0}'
    plan_lab         = 'MotionLab goes to {0} (about 730 MB with its Python packages), with a MotionLab icon on the Desktop and in the Start menu.'
    plan_lab_here    = 'MotionLab in {0} is checked and completed: Python packages, folders, shortcuts.'
    plan_graphics    = '* only if you want the motion graphics (the next question)'
    plan_claude      = 'Your browser opens once for the Claude sign-in (your Claude Pro or Max plan) - you can also sign in later.'
    plan_never       = 'It never touches your videos, uploads nothing, and changes nothing else on your PC.'
    plan_time        = 'The first time takes about 20 minutes and about 3 GB. After the questions you can leave it alone.'
    col_program      = 'Program'
    col_what         = 'What for'
    col_size         = 'Size'
    col_admin        = 'Windows asks permission'
    admin_yes        = 'yes'
    admin_maybe      = 'maybe'
    admin_no         = 'no'
    why_git          = 'updates and sharing with friends'
    why_vc           = 'the sound part of every analysis'
    why_node         = 'the motion graphics'
    why_node_old     = 'the motion graphics (yours is too old)'
    why_claude       = 'Claude: reviews, learning, edits'
    why_python       = 'MotionLab itself'
    why_ffmpeg       = 'reading and making videos'
    why_deno         = 'YouTube downloads'
    why_ytdlp        = 'downloads from a link'
    hf_name          = 'HyperFrames (in the MotionLab folder)'
    go               = 'Go ahead?'
    yn_yes           = '[Y/n]'
    yn_no            = '[y/N]'
    stopped          = 'Nothing was changed. Double-click the installer again any time.'
    graphics_ask     = 'Motion graphics - the animated templates and the motion-graphics videos - need Node.js and HyperFrames (about 500 MB; Windows asks permission once). Install them?'
    name_ask         = 'Your name for sharing what MotionLab learns with friends (letters and numbers; Enter = later)'
    name_saved       = 'Your name for sharing: {0}'
    next_steps       = 'Next: {0}.'
    lab_short        = 'MotionLab''s own setup'
    handover         = 'Continuing with the copy in {0} ...'
    step_programs    = 'Programs'
    step_download    = 'MotionLab'
    step_signin      = 'Claude sign-in'
    step_connect     = 'Updates from GitHub'
    step_lab         = 'MotionLab itself'
    step_done        = 'Done'
    installing       = 'Installing {0} ({1}) ...'
    installed        = '{0} installed'
    already          = '{0} was installed already'
    reboot           = '{0} installed - restart the PC once MotionLab is set up'
    hidden           = 'installed, but Windows does not show it to MotionLab yet - restart the PC, then double-click setup.bat in the MotionLab folder'
    failed           = '{0} could not be installed: {1}.'
    required         = 'MotionLab cannot work without {0}.'
    stop_again       = 'Double-click the installer again once that is solved - it only does what is missing.'
    winget_none      = 'The Windows Package Manager (the "App Installer" app) is missing or too old, so programs cannot be installed by themselves. The Microsoft Store opens it for you: install or update "App Installer", then double-click the installer again. (Store page: https://apps.microsoft.com/detail/9NBLGGH4NNS1)'
    winget_stop      = 'Without the App Installer the programs MotionLab needs cannot be installed.'
    w_cancelled      = 'Windows asked for permission and the answer was No (or the box was closed)'
    w_network        = 'the download did not work - check the internet connection'
    w_disk           = 'the disk is full'
    w_inuse          = 'the program is open right now - close it and try again'
    w_busy           = 'another installation is running - wait until it finishes'
    w_restartfirst   = 'Windows wants a restart first'
    w_policy         = 'the settings of this PC do not allow it (a work or school PC?)'
    w_notfound       = 'the Package Manager did not find it - update "App Installer" in the Microsoft Store'
    w_noinstaller    = 'there is no version of it for this PC'
    w_oldwinget      = 'the Package Manager is too old - update "App Installer" in the Microsoft Store'
    w_nowinget       = 'the App Installer is missing'
    w_other          = 'the Package Manager stopped with code {0}'
    claude_installing = 'Installing Claude Code with Anthropic''s official installer (about 280 MB; it shows no progress - a minute or two) ...'
    claude_winget    = 'Trying the Windows Package Manager for Claude Code instead ...'
    claude_failed    = 'Anthropic''s installer did not work (code {0})'
    claude_skip_test = 'test mode: the Claude Code installer is never run'
    signin_now       = 'Your browser opens: sign in with your Claude account (Pro or Max plan). A small window shows the sign-in and closes by itself when you are done. Later instead? Close that window - MotionLab measures videos without Claude.'
    signin_dry       = 'claude auth status --json, then claude auth login in its own small window when not signed in'
    signed_in        = 'Signed in to Claude'
    signin_later     = 'Not signed in to Claude yet: the first time a MotionLab button opens Claude, it asks you to sign in.'
    graphics_skipped = 'The motion graphics are left out for now: Node.js is missing. Double-click setup.bat later to add them.'
    connecting       = 'Connecting this copy to GitHub, so it gets updates ...'
    connected        = 'Connected to GitHub - updates come from the last tested version'
    connect_failed   = 'This copy could not be connected to GitHub ({0}). MotionLab works; Settings > Sharing & updates can connect it later.'
    connect_nogit    = 'Without Git this copy gets no updates - double-click setup.bat again later.'
    no_python        = 'no Python 3.12'
    cloning          = 'Downloading MotionLab into {0} ...'
    clone_failed     = 'MotionLab could not be downloaded from GitHub (git stopped with code {0}) - check the internet connection.'
    tested           = 'Starting from the last tested version (the one the Update button installs)'
    tested_short     = 'the last tested version on a local main'
    lab_what         = 'Python packages (about 650 MB the first time), your folders, Claude Code''s access to MotionLab''s data, the shortcuts'
    lab_what_hf      = 'Python packages (about 650 MB the first time), your folders, Claude Code''s access to MotionLab''s data, HyperFrames, the shortcuts'
    lang_new         = 'MotionLab starts in Spanish (Settings > General > Language changes it)'
    lab_failed       = 'MotionLab''s own setup stopped - see the messages above.'
    done_installed   = 'Installed now: {0}'
    done_had         = 'Already on this PC: {0}'
    done_skipped     = 'Left out: {0}. Settings > Programs in MotionLab shows what is missing; double-click setup.bat to try again.'
    done_reboot      = 'Restart the PC once, when it suits you (a program asked for it).'
    done_where       = 'MotionLab is in {0}. Next time: the MotionLab icon on your Desktop or in the Start menu.'
    done_opening     = 'MotionLab opens now. The first time a button opens Claude, it asks whether you trust the MotionLab folder: answer Yes.'
    done_dry         = 'Dry run finished: nothing was changed.'
    done_log         = 'This window''s text is saved in {0}'
    close_soon       = 'This window closes by itself in a minute (or press any key).'
    press_key        = 'Press any key to close this window.'
    crash            = 'Something went wrong: {0}'
    crash_help       = 'Double-click the installer again - it only does what is missing. Still stuck? In MotionLab: Settings > About > Report a problem (or send this window''s text to whoever shared MotionLab with you).'
}

# The same words in Spanish (Spain, tu; 2026-10-19, the owner: the whole app in Spanish, "All of it in this release"):
# a Windows in Spanish or -Lang es picks them (Get-Language). The only non-ASCII text in this file - keep it after the
# English table, plain ' and " (PowerShell reads curly quotes as quotes), {0} {1} as in English; a key missing here
# shows in English. Names of the app's places as its Spanish pages say them (Ajustes > Programas ...).
$StringsEs = @{
    title            = 'Instalador de MotionLab'
    intro            = 'MotionLab desmonta la edición de los vídeos que te gustan y te ayuda a rehacerla con tus propios clips, en tu propio PC.'
    dry              = 'Simulación: no se instala ni se cambia nada, solo se muestran los comandos.'
    would            = 'se ejecutaría: {0}'
    admin            = 'Cierra esta ventana y haz doble clic en el instalador como siempre, no con "Ejecutar como administrador": MotionLab y sus programas son de tu propia cuenta de Windows. Windows ya pide permiso por sí solo cuando un programa lo necesita.'
    test_desk        = 'El modo de prueba necesita -ShortcutFolder: una prueba nunca toca el escritorio ni el menú Inicio de verdad.'
    not_lab          = 'Esta no es una carpeta de MotionLab: {0}'
    folder_ask       = '¿Dónde instalo MotionLab? Pulsa Enter para usar {0} o escribe otra carpeta'
    folder_full      = 'Escribe la ruta completa de una carpeta, por ejemplo D:\MotionLab.'
    folder_file      = 'Eso es un archivo, no una carpeta.'
    folder_other     = 'Esta carpeta ya tiene otros archivos. MotionLab solo va en una carpeta nueva o vacía (o en la suya), para no mezclarse nunca con lo tuyo. Elige otra carpeta.'
    folder_protected = 'Windows protege esta carpeta. Elige otra, por ejemplo C:\MotionLab.'
    folder_bad       = 'No es un buen sitio para MotionLab: {0}.'
    folder_anyway    = '¿La uso de todos modos?'
    place_downloads  = 'la carpeta Descargas (Windows puede vaciarla por su cuenta)'
    place_desktop    = 'el escritorio'
    place_documents  = 'la carpeta Documentos (a menudo se guarda en OneDrive)'
    place_onedrive   = 'una carpeta de OneDrive (subiría gigas de datos y dejaría archivos solo en la nube)'
    place_temp       = 'una carpeta temporal (Windows la vacía)'
    place_accents    = 'tildes, ñ u otras letras especiales en el nombre de la carpeta (algunos programas fallan con ellas)'
    place_long       = 'un nombre de carpeta largo (algunos programas fallan con rutas muy largas)'
    found_copy       = 'MotionLab ya está en {0}: el instalador termina o repara esa copia.'
    old_copy         = 'La copia de MotionLab de {0} es más antigua que este instalador. Abre MotionLab y haz clic en Actualizar, o haz doble clic en setup.bat en esa carpeta, o elige otra carpeta.'
    old_clone        = 'Esta versión de MotionLab termina con su propio setup.bat.'
    plan_head        = 'Esto es lo que va a pasar (nada empieza hasta que respondas):'
    plan_none        = 'Todos los programas que necesita MotionLab ya están en este PC.'
    plan_have        = 'Ya en este PC: {0}'
    plan_lab         = 'MotionLab se instala en {0} (unos 730 MB con sus paquetes de Python), con un icono de MotionLab en el escritorio y en el menú Inicio.'
    plan_lab_here    = 'Se revisa y se completa MotionLab en {0}: paquetes de Python, carpetas, accesos directos.'
    plan_graphics    = '* solo si quieres los gráficos animados (la siguiente pregunta)'
    plan_claude      = 'El navegador se abre una vez para iniciar sesión en Claude (tu plan Claude Pro o Max); también puedes hacerlo más tarde.'
    plan_never       = 'Nunca toca tus vídeos, no sube nada y no cambia nada más de tu PC.'
    plan_time        = 'La primera vez tarda unos 20 minutos y ocupa unos 3 GB. Después de las preguntas puedes dejarlo solo.'
    col_program      = 'Programa'
    col_what         = 'Para qué'
    col_size         = 'Tamaño'
    col_admin        = 'Windows pide permiso'
    admin_yes        = 'sí'
    admin_maybe      = 'quizá'
    admin_no         = 'no'
    why_git          = 'actualizar y compartir con amigos'
    why_vc           = 'el sonido de cada análisis'
    why_node         = 'gráficos animados'
    why_node_old     = 'gráficos animados (versión vieja)'
    why_claude       = 'Claude: revisa, aprende, edita'
    why_python       = 'el propio MotionLab'
    why_ffmpeg       = 'leer y crear vídeos'
    why_deno         = 'descargas de YouTube'
    why_ytdlp        = 'descargas desde un enlace'
    hf_name          = 'HyperFrames (dentro de MotionLab)'
    go               = '¿Adelante?'
    yn_yes           = '[S/n]'
    yn_no            = '[s/N]'
    stopped          = 'No se ha cambiado nada. Vuelve a hacer doble clic en el instalador cuando quieras.'
    graphics_ask     = 'Los gráficos animados (las plantillas de Motion Graphics y los vídeos animados del Generador) necesitan Node.js y HyperFrames (unos 500 MB; Windows pide permiso una vez). ¿Los instalo?'
    name_ask         = 'Tu nombre para compartir con tus amigos lo que aprende MotionLab (letras y números; Enter = más tarde)'
    name_saved       = 'Tu nombre para compartir: {0}'
    next_steps       = 'A continuación: {0}.'
    lab_short        = 'la configuración de MotionLab'
    handover         = 'Seguimos con la copia de {0} ...'
    step_programs    = 'Programas'
    step_download    = 'MotionLab'
    step_signin      = 'Inicio de sesión en Claude'
    step_connect     = 'Actualizaciones desde GitHub'
    step_lab         = 'El propio MotionLab'
    step_done        = 'Listo'
    installing       = 'Instalando {0} ({1}) ...'
    installed        = '{0} instalado'
    already          = '{0} ya estaba instalado'
    reboot           = '{0} instalado: reinicia el PC cuando MotionLab esté listo'
    hidden           = 'se ha instalado, pero Windows aún no se lo muestra a MotionLab: reinicia el PC y luego haz doble clic en setup.bat en la carpeta de MotionLab'
    failed           = 'No se ha podido instalar {0}: {1}.'
    required         = 'MotionLab no puede funcionar sin {0}.'
    stop_again       = 'Cuando lo hayas resuelto, vuelve a hacer doble clic en el instalador: solo hace lo que falta.'
    winget_none      = 'Falta el Administrador de paquetes de Windows (la aplicación "Instalador de aplicación") o es demasiado antiguo, así que los programas no se pueden instalar solos. Se abre Microsoft Store: instala o actualiza "Instalador de aplicación" y vuelve a hacer doble clic en el instalador. (Página de la tienda: https://apps.microsoft.com/detail/9NBLGGH4NNS1)'
    winget_stop      = 'Sin el Instalador de aplicación no se pueden instalar los programas que necesita MotionLab.'
    w_cancelled      = 'Windows pidió permiso y la respuesta fue No (o se cerró el cuadro)'
    w_network        = 'la descarga no ha funcionado: revisa la conexión a internet'
    w_disk           = 'el disco está lleno'
    w_inuse          = 'el programa está abierto ahora mismo: ciérralo y vuelve a intentarlo'
    w_busy           = 'hay otra instalación en marcha: espera a que termine'
    w_restartfirst   = 'Windows quiere que reinicies primero'
    w_policy         = 'la configuración de este PC no lo permite (¿un PC del trabajo o de clase?)'
    w_notfound       = 'el Administrador de paquetes no lo encuentra: actualiza "Instalador de aplicación" en Microsoft Store'
    w_noinstaller    = 'no hay ninguna versión para este PC'
    w_oldwinget      = 'el Administrador de paquetes es demasiado antiguo: actualiza "Instalador de aplicación" en Microsoft Store'
    w_nowinget       = 'falta el Instalador de aplicación'
    w_other          = 'el Administrador de paquetes se ha parado con el código {0}'
    claude_installing = 'Instalando Claude Code con el instalador oficial de Anthropic (unos 280 MB; no muestra el progreso, tarda un minuto o dos) ...'
    claude_winget    = 'Probando con el Administrador de paquetes de Windows para Claude Code ...'
    claude_failed    = 'el instalador de Anthropic no ha funcionado (código {0})'
    claude_skip_test = 'modo de prueba: el instalador de Claude Code nunca se ejecuta'
    signin_now       = 'Se abre el navegador: inicia sesión con tu cuenta de Claude (plan Pro o Max). Una ventanita muestra el inicio de sesión y se cierra sola cuando termines. ¿Prefieres hacerlo más tarde? Cierra esa ventana: MotionLab mide los vídeos sin Claude.'
    signin_dry       = 'claude auth status --json y, si no has iniciado sesión, claude auth login en su propia ventanita'
    signed_in        = 'Sesión iniciada en Claude'
    signin_later     = 'Aún no has iniciado sesión en Claude: la primera vez que un botón de MotionLab abra Claude, te pedirá que inicies sesión.'
    graphics_skipped = 'Los gráficos animados se quedan fuera por ahora: falta Node.js. Haz doble clic en setup.bat más tarde para añadirlos.'
    connecting       = 'Conectando esta copia con GitHub para que reciba actualizaciones ...'
    connected        = 'Copia conectada con GitHub: las actualizaciones llegan desde la última versión probada'
    connect_failed   = 'No se ha podido conectar esta copia con GitHub ({0}). MotionLab funciona; puedes conectarla más tarde en Ajustes > Compartir y actualizaciones.'
    connect_nogit    = 'Sin Git esta copia no recibe actualizaciones: vuelve a hacer doble clic en setup.bat más tarde.'
    no_python        = 'falta Python 3.12'
    cloning          = 'Descargando MotionLab en {0} ...'
    clone_failed     = 'No se ha podido descargar MotionLab de GitHub (git se paró con el código {0}): revisa la conexión a internet.'
    tested           = 'Empiezas desde la última versión probada (la que instala el botón Actualizar)'
    tested_short     = 'la última versión probada, en un main local'
    lab_what         = 'Paquetes de Python (unos 650 MB la primera vez), tus carpetas, el acceso de Claude Code a los datos de MotionLab y los accesos directos'
    lab_what_hf      = 'Paquetes de Python (unos 650 MB la primera vez), tus carpetas, el acceso de Claude Code a los datos de MotionLab, HyperFrames y los accesos directos'
    lang_new         = 'MotionLab empieza en español (lo cambias en Ajustes > General > Idioma)'
    lab_failed       = 'La configuración de MotionLab se ha parado: mira los mensajes de arriba.'
    done_installed   = 'Instalado ahora: {0}'
    done_had         = 'Ya en este PC: {0}'
    done_skipped     = 'Fuera por ahora: {0}. En MotionLab, Ajustes > Programas muestra lo que falta; haz doble clic en setup.bat para volver a intentarlo.'
    done_reboot      = 'Reinicia el PC una vez, cuando te venga bien (un programa lo ha pedido).'
    done_where       = 'MotionLab está en {0}. La próxima vez: el icono de MotionLab en el escritorio o en el menú Inicio.'
    done_opening     = 'MotionLab se abre ahora. La primera vez que un botón abra Claude, te preguntará si confías en la carpeta de MotionLab: responde Yes (sí).'
    done_dry         = 'Simulación terminada: no se ha cambiado nada.'
    done_log         = 'El texto de esta ventana se ha guardado en {0}'
    close_soon       = 'Esta ventana se cierra sola en un minuto (o pulsa cualquier tecla).'
    press_key        = 'Pulsa cualquier tecla para cerrar esta ventana.'
    crash            = 'Algo ha fallado: {0}'
    crash_help       = 'Vuelve a hacer doble clic en el instalador: solo hace lo que falta. ¿Sigue sin funcionar? En MotionLab: Ajustes > Acerca de > Informar de un problema (o envía el texto de esta ventana a quien te pasó MotionLab).'
}

$ErrorActionPreference = 'Stop'
# this run's state (a hand-over runs the cloned copy's text inside this process: it makes its own $S)
$S = @{ PathFile = $env:ML_TEST_PATHFILE; Lab = $null; Winget = $null; Reboot = $false; LogCopy = $null; Graphics = $null;
        Banner = $false; Handover = [bool]$env:ML_HANDOVER; Done = @()
        Before = @(([string]$env:ML_INSTALLED) -split ',' | Where-Object { $_ -and $env:ML_HANDOVER }) }  # installed before the hand-over
$S.TestMode = [bool]$S.PathFile
$S.Self = $env:ML_SELF

function Get-Language {
    # the window's language (2026-10-19: a Spanish friend's installer speaks Spanish): -Lang; else the one the first
    # window chose (a hand-over: ML_LANG); else, finishing a MotionLab folder (-Here), the one picked in its app
    # (settings.json); else Windows' own. setup.bat /lab gets it as ML_LANG: a NEW settings.json starts the app in it
    if ($Lang) { return $Lang }
    if ($S.Handover -and $env:ML_LANG -in 'en', 'es') { return $env:ML_LANG }
    if ($Here -and $S.Self) {
        try {
            $v = (Get-Content -LiteralPath (Join-Path (Split-Path -Parent $S.Self) 'settings.json') -Raw -Encoding UTF8 | ConvertFrom-Json).language
            if ($v -in 'en', 'es') { return $v }
        } catch { }
    }
    try { if ((Get-UICulture).TwoLetterISOLanguageName -eq 'es') { return 'es' } } catch { }
    return 'en'
}
$S.Lang = Get-Language
if ($S.Lang -eq 'es') { foreach ($wordKey in @($StringsEs.Keys)) { $Strings[$wordKey] = $StringsEs[$wordKey] } }
if (-not $env:ML_HANDOVER) { Remove-Item Env:ML_LOG -ErrorAction SilentlyContinue }
Remove-Item Env:ML_HANDOVER, Env:ML_ARGS, Env:ML_INSTALLED, Env:ML_LANG -ErrorAction SilentlyContinue

# ---------------------------------------------------------------------------------------------------- the window
function Write-Out([string]$t, [string]$c = '') { if ($c) { Write-Host $t -ForegroundColor $c } else { Write-Host $t } }
function Out-Line([string]$prefix, [string]$text, [string]$c = '') {
    # long sentences wrap at a word in the window; into a file or pipe (a log, the tests) one line stays one line
    try { if ([Console]::IsOutputRedirected) { Write-Out ($prefix + $text) $c; return } } catch { }
    $width = 100
    try { $width = [Math]::Max(50, [Math]::Min(116, $Host.UI.RawUI.WindowSize.Width - 2)) } catch { }
    $cur = ''; $lead = $prefix
    foreach ($word in ($text -split ' ')) {
        if ($cur -and ($lead.Length + $cur.Length + 1 + $word.Length) -gt $width) {
            Write-Out ($lead + $cur) $c; $cur = $word; $lead = ' ' * $prefix.Length
        } elseif ($cur) { $cur += ' ' + $word } else { $cur = $word }
    }
    Write-Out ($lead + $cur) $c
}
function Say([string]$t = '', [string]$c = '') { if ($t) { Out-Line '  ' $t $c } else { Write-Host '' } }
function Ok([string]$t) { Out-Line '  [ok] ' $t 'Green' }
function Warn([string]$t) { Out-Line '  [!]  ' $t 'Yellow' }
function Note([string]$t) { Out-Line '  ' $t 'DarkGray' }
function Step([string]$t) { Write-Host ''; Write-Host ('== ' + $t) -ForegroundColor Cyan }
function Show-Banner {
    if ($S.Banner -or $S.Handover) { return }              # once per window
    $S.Banner = $true
    try { $Host.UI.RawUI.WindowTitle = $Strings.title } catch { }
    Write-Host ''
    Write-Host ('  ' + $Strings.title) -ForegroundColor Cyan
    Write-Host ('  ' + ('=' * $Strings.title.Length)) -ForegroundColor Cyan
    if ($DryRun) { Note $Strings.dry }
}
function Read-Answer([string]$q) {
    if ($Yes) { return '' }
    $a = Read-Host ('  ' + $q)
    if ($null -eq $a) { return '' }
    return $a.Trim().Trim('"').Trim()
}
function Ask-YesNo([string]$q, [bool]$default = $true) {
    if ($Yes) { return $default }
    $hint = ' ' + $Strings.yn_no; if ($default) { $hint = ' ' + $Strings.yn_yes }
    for ($i = 0; $i -lt 20; $i++) {
        Write-Host ''
        $a = Read-Host ('  ' + $q + $hint)
        if ($null -eq $a) { return $default }
        $a = ($a.Trim().Normalize([Text.NormalizationForm]::FormD) -replace '\p{Mn}', '').ToLowerInvariant()   # "si" with or without its accent
        if (-not $a) { return $default }
        if ($a -in 'y', 'yes', 's', 'si') { return $true }
        if ($a -in 'n', 'no') { return $false }
    }
    return $default
}
function Wait-Close([int]$seconds) {
    try { if ([Console]::IsInputRedirected) { return } } catch { return }
    Write-Host ''
    if ($seconds -gt 0) { Note $Strings.close_soon } else { Note $Strings.press_key }
    $end = (Get-Date).AddSeconds($seconds)
    while ($seconds -le 0 -or (Get-Date) -lt $end) {
        try { if ([Console]::KeyAvailable) { [void][Console]::ReadKey($true); return } } catch { return }
        Start-Sleep -Milliseconds 200
    }
}
function Start-Log {
    if ($DryRun -or $env:ML_LOG) { return }
    $p = Join-Path ([IO.Path]::GetTempPath()) 'MotionLab-install.log'
    try { Start-Transcript -Path $p -Force | Out-Null; $env:ML_LOG = $p } catch { }
}
function Save-Log {
    if (-not $env:ML_LOG) { return }
    $p = $env:ML_LOG
    Remove-Item Env:ML_LOG -ErrorAction SilentlyContinue
    try { Stop-Transcript | Out-Null } catch { }
    if ($S.Lab -and (Test-File (Join-Path $S.Lab 'tools\motionlab'))) {
        try {
            $app = Join-Path $S.Lab '.app'
            if (-not (Test-Path -LiteralPath $app)) { New-Item -ItemType Directory -Path $app | Out-Null }
            Copy-Item -LiteralPath $p -Destination (Join-Path $app 'install.log') -Force
            $S.LogCopy = Join-Path $app 'install.log'
        } catch { }
    }
}
function Stop-Install([string]$why) {
    Write-Host ''
    Out-Line '  [!]  ' $why 'Red'
    Say $Strings.stop_again
    Save-Log
    Wait-Close 0
    exit 1
}

# --------------------------------------------------------------------------------------------- running programs
function Test-File([string]$p) { return [bool]($p -and (Test-Path -LiteralPath $p)) }
function Invoke-Quiet([string]$exe, [string[]]$a, [switch]$Merge) {
    # output captured, never shown; stderr dropped unless -Merge (native stderr must not become a stopping error)
    $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try {
        if ($Merge) { $o = & $exe @a 2>&1 } else { $o = & $exe @a 2>$null }
        return [pscustomobject]@{ Code = $LASTEXITCODE; Out = (@($o | ForEach-Object { "$_" }) -join "`n") }
    } catch { return [pscustomobject]@{ Code = -1; Out = "$_" } }
    finally { $ErrorActionPreference = $old }
}
function Invoke-Visible([string]$exe, [string[]]$a, [string]$dir = '') {
    # the program writes straight into this window (winget's and pip's progress); tests read it through this output
    if ($S.TestMode) {
        $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
        if ($dir) { Push-Location -LiteralPath $dir }
        try { & $exe @a 2>&1 | ForEach-Object { Write-Host "$_" }; return $LASTEXITCODE }
        finally { if ($dir) { Pop-Location }; $ErrorActionPreference = $old }
    }
    $line = ($a | ForEach-Object { if ($_ -match '[\s"]') { '"' + ($_ -replace '"', '\"') + '"' } else { $_ } }) -join ' '
    $sp = @{ FilePath = $exe; ArgumentList = $line; NoNewWindow = $true; PassThru = $true }
    if ($dir) { $sp.WorkingDirectory = $dir }
    $proc = Start-Process @sp
    $null = $proc.Handle
    $proc.WaitForExit()
    return $proc.ExitCode
}
function Test-Admin {
    # an elevated run would put per-user programs and the lab under the wrong account; UAC off = always elevated
    $p = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { return $false }
    $lua = (Get-ItemProperty -LiteralPath 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System' -ErrorAction SilentlyContinue).EnableLUA
    return ($lua -ne 0)
}
function Test-Ready {
    if (Test-Admin) { Stop-Install $Strings.admin }
    if ($S.TestMode -and -not $DryRun -and -not $ShortcutFolder) { Stop-Install $Strings.test_desk }
}

# ------------------------------------------------------------------------------- PATH: no new window, no second run
function Get-RegistryPath {
    if ($S.TestMode) {
        if (Test-File $S.PathFile) { return @(Get-Content -LiteralPath $S.PathFile -Encoding UTF8 | Where-Object { $_.Trim() }) }
        return @()
    }
    $m = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $u = [Environment]::GetEnvironmentVariable('Path', 'User')
    return @((([string]$m) + ';' + ([string]$u)) -split ';' | Where-Object { $_.Trim() })
}
function Update-SessionPath {
    # this window's PATH = the entries only it has (a test's fake winget) + the registry's, read again after every
    # install - so a program installed a minute ago is found without opening a new window
    $reg = @(Get-RegistryPath)
    $key = { param($p) $p.Trim().TrimEnd('\').ToLowerInvariant() }
    $inReg = @{}
    foreach ($p in $reg) { $inReg[(& $key $p)] = $true }
    $all = New-Object System.Collections.Generic.List[string]
    $seen = @{}
    $own = @(([string]$env:Path) -split ';' | Where-Object { $_.Trim() -and -not $inReg.ContainsKey((& $key $_)) })
    foreach ($p in ($own + $reg)) { $k = & $key $p; if (-not $seen.ContainsKey($k)) { $seen[$k] = $true; $all.Add($p.Trim()) } }
    $env:Path = $all -join ';'
}
function Send-EnvironmentChange {
    # tell Explorer (and so the Desktop shortcut) that PATH changed - the app also reads it at start (system.py)
    if ($DryRun -or $S.TestMode) { return }
    try {
        Add-Type -Namespace MotionLab -Name Env -MemberDefinition '[DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint Msg, UIntPtr wParam, string lParam, uint fuFlags, uint uTimeout, out UIntPtr lpdwResult);'
        $r = [UIntPtr]::Zero
        [void][MotionLab.Env]::SendMessageTimeout([IntPtr]0xffff, 0x1A, [UIntPtr]::Zero, 'Environment', 2, 5000, [ref]$r)
    } catch { }
}

# --------------------------------------------------------------------------------------------- finding programs
function Find-Exe([string]$name) {
    $c = Get-Command $name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($c) { return $c.Source }
    return $null
}
function Find-Git {
    $g = Find-Exe 'git'
    if ($g -or $S.TestMode) { return $g }
    foreach ($p in @("$env:ProgramFiles\Git\cmd\git.exe", "${env:ProgramFiles(x86)}\Git\cmd\git.exe", "$env:LOCALAPPDATA\Programs\Git\cmd\git.exe")) {
        if (Test-File $p) { return $p }
    }
    return $null
}
function Test-Python312([string]$exe) {
    if (-not (Test-File $exe)) { return $false }
    $r = Invoke-Quiet $exe @('-c', 'import sys; print(sys.version_info[:2] == (3, 12) and sys.maxsize > 2**32)')
    return ($r.Code -eq 0 -and $r.Out -match 'True')
}
function Find-Python312 {
    # MotionLab needs exactly 3.12, 64-bit: its registry entry first (no PATH needed), then the usual folders, then py
    if ($S.TestMode) { $p = Find-Exe 'python'; if (Test-Python312 $p) { return $p }; return $null }
    foreach ($root in 'HKCU:', 'HKLM:') {
        $k = Get-ItemProperty -LiteralPath "$root\Software\Python\PythonCore\3.12\InstallPath" -ErrorAction SilentlyContinue
        if ($k) {
            $exe = $k.ExecutablePath
            if (-not $exe -and $k.'(default)') { $exe = Join-Path $k.'(default)' 'python.exe' }
            if (Test-Python312 $exe) { return $exe }
        }
    }
    foreach ($p in @("$env:LOCALAPPDATA\Programs\Python\Python312\python.exe", "$env:ProgramFiles\Python312\python.exe")) {
        if (Test-Python312 $p) { return $p }
    }
    # never "py -3.12": the newer Python install manager may ask to install a missing version - an unseen prompt here
    return $null
}
function Find-Claude {
    if (-not $S.TestMode) {
        foreach ($p in @("$env:USERPROFILE\.local\bin\claude.exe", "$env:APPDATA\npm\claude.cmd")) { if (Test-File $p) { return $p } }
    }
    return (Find-Exe 'claude')
}
function Get-NodeMajor([string]$n) {
    $r = Invoke-Quiet $n @('--version')
    if ($r.Out -match 'v?(\d+)\.') { return [int]$Matches[1] }
    return 0
}
function Find-Node {
    # the motion graphics need Node.js 22 or newer (HyperFrames)
    $c = @()
    if (-not $S.TestMode) { $c += "$env:ProgramFiles\nodejs\node.exe" }
    $c += Find-Exe 'node'
    foreach ($n in $c) { if ((Test-File $n) -and (Get-NodeMajor $n) -ge 22) { return $n } }
    return $null
}
function Test-VCRuntime {
    # the Visual C++ runtime the audio analysis needs (librosa / numba): msvcp140.dll; tests: in a test PATH folder
    if ($S.TestMode) {
        foreach ($d in @(Get-RegistryPath)) { if (Test-File (Join-Path $d 'msvcp140.dll')) { return (Join-Path $d 'msvcp140.dll') } }
        return $null
    }
    $f = "$env:SystemRoot\System32\msvcp140.dll"
    if (Test-File $f) { return $f }
    return $null
}
function Find-InWinget([string]$pattern) {
    $pk = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages"
    if ($S.TestMode -or -not (Test-Path -LiteralPath $pk)) { return $null }
    $hit = Get-ChildItem -Path (Join-Path $pk $pattern) -ErrorAction SilentlyContinue | Select-Object -Last 1
    if ($hit) { return $hit.FullName }
    return $null
}
function Find-Deno {
    $d = Find-Exe 'deno'
    if ($d -or $S.TestMode) { return $d }
    foreach ($p in @("$env:USERPROFILE\.deno\bin\deno.exe", "$env:LOCALAPPDATA\Microsoft\WinGet\Links\deno.exe")) { if (Test-File $p) { return $p } }
    return (Find-InWinget 'DenoLand.Deno_*\deno.exe')
}
function Find-YtDlp {
    $y = Find-Exe 'yt-dlp'
    if ($y -or $S.TestMode) { return $y }
    if ($S.Lab -and (Test-File (Join-Path $S.Lab 'tools\bin\yt-dlp.exe'))) { return (Join-Path $S.Lab 'tools\bin\yt-dlp.exe') }
    return (Find-InWinget 'yt-dlp.yt-dlp_*\yt-dlp.exe')
}
function Test-HyperFrames([string]$lab) {
    if (-not $lab -or -not (Test-File (Join-Path $lab 'tools\overlays\node_modules\hyperframes\bin\hyperframes.mjs'))) { return $false }
    $c = "$env:USERPROFILE\.cache\hyperframes\chrome"
    return [bool](Get-ChildItem -LiteralPath $c -Recurse -Filter 'chrome-headless-shell.exe' -ErrorAction SilentlyContinue | Select-Object -First 1)
}
function Get-Winget {
    $w = Find-Exe 'winget'
    if ($w -or $S.TestMode) { return $w }
    $p = "$env:LOCALAPPDATA\Microsoft\WindowsApps\winget.exe"
    if (Test-File $p) { return $p }
    if (-not $DryRun) {          # a new Windows registers the App Installer late: ask for it once
        try { Add-AppxPackage -RegisterByFamilyName -MainPackage 'Microsoft.DesktopAppInstaller_8wekyb3d8bbwe' -ErrorAction Stop } catch { }
        if (Test-File $p) { return $p }
    }
    return $null
}
function Open-AppInstallerPage {
    if ($DryRun -or $S.TestMode) { return }
    try { Start-Process 'ms-windows-store://pdp/?ProductId=9NBLGGH4NNS1' } catch { }
}

# ---------------------------------------------------------------------------------------- what MotionLab installs
function New-Program($key, $name, $id, $why, $size, $admin, $required, $find, $extra) {
    return [pscustomobject]@{ Key = $key; Name = $name; Id = $id; Why = $why; Size = $size; Admin = $admin;
                              Required = $required; Find = $find; Extra = @($extra); Path = $null; Result = $null; Words = '' }
}
function Get-Programs([bool]$installMode) {
    # in this order: the ones that need the friend (Windows' permission boxes, the sign-in) first, then it runs alone;
    # Gyan's ffmpeg before yt-dlp, which gets --skip-dependencies (winget's yt-dlp would add a second ffmpeg)
    $list = @(
        (New-Program 'git' 'Git' 'Git.Git' $Strings.why_git '360 MB' 'yes' $installMode { Find-Git } @()),
        (New-Program 'vc' 'Microsoft Visual C++ runtime' 'Microsoft.VCRedist.2015+.x64' $Strings.why_vc '15 MB' 'yes' $true { Test-VCRuntime } @()),
        (New-Program 'node' 'Node.js' 'OpenJS.NodeJS.LTS' $Strings.why_node '110 MB' 'yes' $false { Find-Node } @()),
        (New-Program 'claude' 'Claude Code' 'Anthropic.ClaudeCode' $Strings.why_claude '280 MB' 'no' $false { Find-Claude } @()),
        (New-Program 'python' 'Python 3.12' 'Python.Python.3.12' $Strings.why_python '270 MB' 'maybe' $true { Find-Python312 } @()),
        (New-Program 'ffmpeg' 'ffmpeg' 'Gyan.FFmpeg' $Strings.why_ffmpeg '670 MB' 'no' $true { Find-Exe 'ffmpeg' } @()),
        (New-Program 'deno' 'Deno' 'DenoLand.Deno' $Strings.why_deno '95 MB' 'no' $false { Find-Deno } @()),
        (New-Program 'ytdlp' 'yt-dlp' 'yt-dlp.yt-dlp' $Strings.why_ytdlp '20 MB' 'no' $false { Find-YtDlp } @('--skip-dependencies'))
    )
    foreach ($p in $list) { $p.Path = & $p.Find }
    $node = $list | Where-Object { $_.Key -eq 'node' }
    if (-not $node.Path -and (Find-Exe 'node')) { $node.Why = $Strings.why_node_old }
    return $list
}
function Get-WingetKind([int64]$rc) {
    $hex = '0x{0:X8}' -f ($rc -band 0xFFFFFFFFL)
    $kinds = @{
        '0x00000000' = 'ok'; '0x8A15002B' = 'already'; '0x8A150061' = 'already'; '0x8A15010D' = 'already'
        '0x00000BC2' = 'reboot'; '0x8A150109' = 'reboot'; '0x8A15010B' = 'reboot'
        '0x800704C7' = 'cancelled'; '0x000004C7' = 'cancelled'; '0x8A15010C' = 'cancelled'; '0x00000642' = 'cancelled'
        '0x8A150107' = 'network'; '0x8A150008' = 'network'; '0x8A150105' = 'disk'
        '0x8A150101' = 'inuse'; '0x8A150103' = 'inuse'; '0x8A150111' = 'inuse'
        '0x8A150102' = 'busy'; '0x00000652' = 'busy'; '0x8A15010A' = 'restartfirst'
        '0x8A15010F' = 'policy'; '0x8A15001B' = 'policy'; '0x8A15001C' = 'policy'
        '0x8A150014' = 'notfound'; '0x8A150010' = 'noinstaller'; '0x8A150002' = 'oldwinget'; '0x8A15000F' = 'network'
    }
    if ($kinds.ContainsKey($hex)) { return @($kinds[$hex], $hex) }
    return @('other', $hex)
}
function Install-Package($p) {
    $wa = @('install', '--id', $p.Id, '-e', '--source', 'winget', '--silent', '--accept-source-agreements',
            '--accept-package-agreements', '--disable-interactivity') + $p.Extra
    if ($DryRun) { Say ($Strings.would -f ('winget ' + ($wa -join ' '))); $p.Result = 'dry'; return }
    Write-Host ''
    Say ($Strings.installing -f $p.Name, $p.Size)
    $rc = Invoke-Visible $S.Winget $wa
    Update-SessionPath
    $p.Path = & $p.Find
    $kind, $hex = Get-WingetKind $rc
    if ($p.Path) {
        if ($kind -eq 'already') { $p.Result = 'already'; Ok ($Strings.already -f $p.Name) }
        elseif ($kind -eq 'reboot') { $p.Result = 'installed'; $S.Reboot = $true; Ok ($Strings.reboot -f $p.Name) }
        else { $p.Result = 'installed'; Ok ($Strings.installed -f $p.Name) }
        return
    }
    $p.Result = 'failed'
    if ($kind -in 'ok', 'already', 'reboot') { $p.Words = $Strings.hidden }
    elseif ($kind -eq 'other') { $p.Words = $Strings.w_other -f $hex }
    else { $p.Words = $Strings['w_' + $kind] }
    if ($p.Required) { Stop-Install (($Strings.failed -f $p.Name, $p.Words) + ' ' + ($Strings.required -f $p.Name)) }
    Warn ($Strings.failed -f $p.Name, $p.Words)
}
function Install-ClaudeCode($p) {
    # Anthropic's official native installer (https://code.claude.com/docs/en/setup, checked 2026-10-18): no
    # administrator, updates itself, claude.exe in %USERPROFILE%\.local\bin; winget's Anthropic.ClaudeCode if it fails
    $cmd = '[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor 3072; irm https://claude.ai/install.ps1 | iex'
    if ($DryRun) { Say ($Strings.would -f ('powershell -NoProfile -ExecutionPolicy Bypass -Command "' + $cmd + '"')); $p.Result = 'dry'; return }
    if ($S.TestMode) { $p.Result = 'failed'; $p.Words = $Strings.claude_skip_test; Warn $Strings.claude_skip_test; return }
    Write-Host ''
    Say $Strings.claude_installing
    $rc = Invoke-Visible "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $cmd)
    Update-SessionPath
    $p.Path = Find-Claude
    if ($p.Path) { $p.Result = 'installed'; Ok ($Strings.installed -f $p.Name); return }
    if (-not $S.Winget) { $S.Winget = Get-Winget }
    if ($S.Winget) { Say $Strings.claude_winget; Install-Package $p; return }
    $p.Result = 'failed'; $p.Words = $Strings.claude_failed -f $rc
    Warn ($Strings.failed -f $p.Name, $p.Words)
}
function Test-ClaudeLogin([string]$claude) {
    $r = Invoke-Quiet $claude @('auth', 'status', '--json')
    try { return [bool](($r.Out | ConvertFrom-Json).loggedIn) } catch { return $false }
}
function Confirm-ClaudeLogin([string]$claude) {
    if ($DryRun) { Say ($Strings.would -f $Strings.signin_dry); return }
    if (-not $claude) { return }
    if ((Invoke-Quiet $claude @('auth', '--help') -Merge).Out -notmatch 'login') { Note $Strings.signin_later; return }
    if (Test-ClaudeLogin $claude) { Ok $Strings.signed_in; return }
    Say $Strings.signin_now
    try { $proc = Start-Process -FilePath $claude -ArgumentList 'auth login' -PassThru; $null = $proc.Handle; $proc.WaitForExit() } catch { }
    if (Test-ClaudeLogin $claude) { Ok $Strings.signed_in } else { Warn $Strings.signin_later }
}

# ---------------------------------------------------------------------------------------------- the lab folder
function Resolve-Folder([string]$f) {
    $f = [Environment]::ExpandEnvironmentVariables($f.Trim().Trim('"').Trim())
    if ($f -notmatch '^[A-Za-z]:\\') { return $null }       # a whole folder on a drive (not a network share)
    $f = [IO.Path]::GetFullPath($f)
    if ($f.Length -gt 3) { $f = $f.TrimEnd('\') }
    return $f
}
function Get-FolderKind([string]$f) {
    if (-not (Test-Path -LiteralPath $f)) { return 'new' }
    if (-not (Test-Path -LiteralPath $f -PathType Container)) { return 'file' }
    if (-not @(Get-ChildItem -LiteralPath $f -Force -ErrorAction SilentlyContinue).Count) { return 'empty' }
    if (Test-File (Join-Path $f 'tools\motionlab\__init__.py')) {
        if (Test-Path -LiteralPath (Join-Path $f '.git')) { return 'git' }
        return 'zip'
    }
    return 'other'
}
function Test-Under([string]$f, [string]$base) {
    if (-not $base) { return $false }
    return ($f.TrimEnd('\') + '\').StartsWith($base.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)
}
function Get-FolderWarnings([string]$f) {
    $dl = $null
    try {
        $dl = (Get-ItemProperty -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders' -ErrorAction Stop).'{374DE290-123F-4565-9164-39C4925E467B}'
        if ($dl) { $dl = [Environment]::ExpandEnvironmentVariables($dl) }
    } catch { }
    $places = @(
        @($dl, $Strings.place_downloads), @("$env:USERPROFILE\Downloads", $Strings.place_downloads),
        @([Environment]::GetFolderPath('Desktop'), $Strings.place_desktop),
        @([Environment]::GetFolderPath('MyDocuments'), $Strings.place_documents),
        @($env:OneDrive, $Strings.place_onedrive), @($env:OneDriveConsumer, $Strings.place_onedrive), @($env:OneDriveCommercial, $Strings.place_onedrive),
        @($env:TEMP, $Strings.place_temp), @($env:TMP, $Strings.place_temp), @("$env:SystemRoot\Temp", $Strings.place_temp)
    )
    $w = @()
    foreach ($pl in $places) { if ((Test-Under $f $pl[0]) -and ($w -notcontains $pl[1])) { $w += $pl[1] } }
    if ($f -match '[^\x20-\x7E]') { $w += $Strings.place_accents }
    if ($f.Length -gt 60) { $w += $Strings.place_long }
    return $w
}
function Test-Protected([string]$f) {
    foreach ($b in @($env:ProgramFiles, ${env:ProgramFiles(x86)}, $env:ProgramW6432, $env:SystemRoot)) { if (Test-Under $f $b) { return $true } }
    return $false
}
function Select-LabFolder {
    $f = $Folder
    for ($i = 0; $i -lt 50; $i++) {
        $a = Read-Answer ($Strings.folder_ask -f $Folder)
        if ($a) { $f = $a } else { $f = $Folder }
        $full = Resolve-Folder $f
        $problem = $null
        if (-not $full) { $problem = $Strings.folder_full }
        else {
            $kind = Get-FolderKind $full
            if ($kind -eq 'file') { $problem = $Strings.folder_file }
            elseif ($kind -eq 'other') { $problem = $Strings.folder_other }
            elseif (Test-Protected $full) { $problem = $Strings.folder_protected }
        }
        if ($problem) { if ($Yes) { Stop-Install $problem }; Warn $problem; continue }
        $warn = @(Get-FolderWarnings $full)
        foreach ($x in $warn) { Warn ($Strings.folder_bad -f $x) }
        if ($warn.Count -and -not (Ask-YesNo $Strings.folder_anyway $false) -and -not $Yes) { continue }
        return $full
    }
    Stop-Install $Strings.folder_full
}
function Get-MotionLab([string]$into, [string]$git) {
    # a real clone (no Mark of the Web, updates and sharing work), then a LOCAL main on origin/tested: the Update
    # button follows tested only from a branch called main (updater._upstream), and Share pushes HEAD:main
    if ($DryRun) {
        Say ($Strings.would -f ('git clone ' + $Repo + ' "' + $into + '"'))
        Say ($Strings.would -f ('git checkout -B main origin/tested; git branch --set-upstream-to=origin/main main (' + $Strings.tested_short + ')'))
        return
    }
    $parent = Split-Path -Parent $into
    if ($parent -and -not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    Say ($Strings.cloning -f $into)
    $rc = Invoke-Visible $git @('clone', $Repo, $into)
    if ($rc -ne 0 -or -not (Test-File (Join-Path $into 'tools\motionlab'))) { Stop-Install ($Strings.clone_failed -f $rc) }
    $tst = Invoke-Quiet $git @('-C', $into, 'rev-parse', '-q', '--verify', 'refs/remotes/origin/tested')
    $m = Invoke-Quiet $git @('-C', $into, 'rev-parse', '-q', '--verify', 'refs/remotes/origin/main')
    if ($tst.Code -eq 0 -and $tst.Out -and $m.Code -eq 0) {
        $c = Invoke-Quiet $git @('-C', $into, 'checkout', '-q', '-B', 'main', 'origin/tested') -Merge
        $null = Invoke-Quiet $git @('-C', $into, 'branch', '-q', '--set-upstream-to=origin/main', 'main') -Merge
        if ($c.Code -eq 0) { Ok $Strings.tested } else { Warn $c.Out }
    }
}
function Connect-ZipCopy([string]$lab, [string]$py) {
    # a ZIP copy becomes a git checkout through the app's own code (updater.connect: the tested commit on a local main)
    if (-not (Find-Git)) { Warn $Strings.connect_nogit; return }
    if ($DryRun) { Say ($Strings.would -f ('updater.connect ' + $Repo + ' (' + $Strings.tested_short + ')')); return }
    if (-not $py) { Warn ($Strings.connect_failed -f $Strings.no_python); return }
    Say $Strings.connecting
    $local = '0'; if ($Repo -notmatch '^https://') { $local = '1' }
    $code = "import sys; sys.path.insert(0, sys.argv[1]); from motionlab.app import updater; r = updater.connect(sys.argv[2], local=sys.argv[3] == '1'); print(r['branch'], r['head'], r['source'])"
    $r = Invoke-Quiet $py @('-c', $code, (Join-Path $lab 'tools'), $Repo, $local) -Merge
    if ($r.Code -eq 0) { Ok $Strings.connected; return }
    Warn ($Strings.connect_failed -f (($r.Out -split "`n" | Where-Object { $_.Trim() } | Select-Object -Last 1)))
}
function Invoke-LabSetup([string]$lab, [string]$py, [bool]$graphics) {
    $what = $Strings.lab_what; if ($graphics) { $what = $Strings.lab_what_hf }
    # setup.bat /lab writes the window's language into a NEW settings.json (ML_LANG); an existing one keeps its own
    if ($S.Lang -eq 'es' -and -not (Test-File (Join-Path $lab 'settings.json'))) { $what += '; ' + $Strings.lang_new }
    if ($DryRun) { Say ($Strings.would -f ('setup.bat /lab - ' + $what)); return 0 }
    Say $what
    $env:ML_INSTALLER = '1'
    $env:ML_LANG = $S.Lang
    if ($py) { $env:ML_PY = $py }
    $env:ML_GRAPHICS = '0'; if ($graphics) { $env:ML_GRAPHICS = '1' }
    if ($ShortcutFolder) { $env:ML_SHORTCUT_DIR = $ShortcutFolder }
    $cmd = $env:ComSpec; if (-not $cmd) { $cmd = 'cmd.exe' }
    # .\ = this folder's setup.bat even where cmd skips the current folder (NoDefaultCurrentDirectoryInExePath)
    return (Invoke-Visible $cmd @('/d', '/c', '.\setup.bat', '/lab') $lab)
}
function Start-MotionLab([string]$lab) {
    # from this window, so MotionLab starts with the fresh PATH
    $pyw = Join-Path $lab '.venv\Scripts\pythonw.exe'
    if ($NoStart -or $DryRun -or $S.TestMode -or -not (Test-File $pyw)) { return $false }
    Start-Process -FilePath $pyw -ArgumentList ('"' + (Join-Path $lab 'tools\app.py') + '"') -WorkingDirectory $lab
    return $true
}
function Ask-Name([string]$lab) {
    if ($Yes -or $env:ML_AUTHOR) { return }
    if ($lab -and (Test-File (Join-Path $lab 'settings.json'))) {
        try { if ((Get-Content -LiteralPath (Join-Path $lab 'settings.json') -Raw -Encoding UTF8 | ConvertFrom-Json).author) { return } } catch { }
    }
    Write-Host ''
    $a = Read-Answer $Strings.name_ask
    # like the app (system.save): a-z, 0-9, _ and -; accents become plain letters first (Jose, Maria)
    $a = ($a.Normalize([Text.NormalizationForm]::FormD) -replace '\p{Mn}', '').ToLowerInvariant().Replace(' ', '-')
    $a = $a -replace '[^a-z0-9_-]', ''
    if ($a.Length -gt 24) { $a = $a.Substring(0, 24) }
    if ($a) { $env:ML_AUTHOR = $a; Note ($Strings.name_saved -f $a) }
}

# ------------------------------------------------------------------------------------------------- the plan screen
function Show-Plan($todo, $have, [string]$where, [bool]$hf, [bool]$newLab) {
    Write-Host ''
    Say $Strings.plan_head 'White'
    Write-Host ''
    $graphicsRow = $false
    if (-not @($todo).Count -and -not $hf) { Say $Strings.plan_none }
    else {
        $fmt = '  {0,-40} {1,-34} {2,7}   {3}'
        Write-Out ($fmt -f $Strings.col_program, $Strings.col_what, $Strings.col_size, $Strings.col_admin) 'DarkGray'
        foreach ($p in $todo) {
            $n = $p.Name; if ($p.Key -eq 'node') { $n += ' *'; $graphicsRow = $true }
            Write-Out ($fmt -f $n, $p.Why, $p.Size, $Strings[('admin_' + $p.Admin)])
        }
        if ($hf) { Write-Out ($fmt -f ($Strings.hf_name + ' *'), $Strings.why_node, '390 MB', $Strings.admin_no); $graphicsRow = $true }
        if ($graphicsRow -and $Graphics -eq 'ask') { Note $Strings.plan_graphics }
    }
    if (@($have).Count) { Note ($Strings.plan_have -f ((@($have) | ForEach-Object { $_.Name }) -join ', ')) }
    Write-Host ''
    if ($newLab) { Say ($Strings.plan_lab -f $where) } else { Say ($Strings.plan_lab_here -f $where) }
    if (-not $NoClaude) { Say $Strings.plan_claude }
    Say $Strings.plan_never
    if ($newLab) { Say $Strings.plan_time }
}

# --------------------------------------------------------------------------- -Here: finish / repair this folder
function Invoke-Here([string]$lab, [bool]$simulated) {
    # $simulated = a dry run of install mode: the clone does not exist, the questions are answered already
    $S.Lab = $lab
    if (-not $simulated) {
        Start-Log
        Show-Banner
        if (-not $DryRun -and -not (Test-File (Join-Path $lab 'tools\motionlab'))) { Stop-Install ($Strings.not_lab -f $lab) }
        Test-Ready
        Update-SessionPath
    }
    $progs = Get-Programs $false
    $node = $progs | Where-Object { $_.Key -eq 'node' }
    $hfOk = Test-HyperFrames $lab
    $todo = @($progs | Where-Object { -not $_.Path -and -not ($NoClaude -and $_.Key -eq 'claude') -and $S.Done -notcontains $_.Key })
    $have = @($progs | Where-Object { $_.Path })
    $want = $null                                           # the motion graphics: Node.js + HyperFrames
    if ($node.Path -and $hfOk) { $want = $true }
    elseif ($null -ne $S.Graphics) { $want = $S.Graphics }
    elseif ($Graphics -ne 'ask') { $want = ($Graphics -eq 'yes') }
    elseif ($Yes) { $want = $true }
    if ($simulated -or $Yes) {
        $names = @($todo | Where-Object { $_.Key -ne 'node' -or $want } | ForEach-Object { $_.Name })
        if ($want -and -not $hfOk) { $names += 'HyperFrames' }
        Write-Host ''
        Say ($Strings.next_steps -f (($names + $Strings.lab_short) -join ', '))
    } else {
        $planned = @($todo | Where-Object { $_.Key -ne 'node' -or $want -ne $false })
        $hfPlanned = (-not $hfOk) -and $want -ne $false
        Show-Plan $planned $have $lab $hfPlanned $false
        if (($planned.Count -or $hfPlanned) -and -not (Ask-YesNo $Strings.go $true)) { Say $Strings.stopped; Save-Log; Wait-Close 0; exit 0 }
        if ($null -eq $want) { $want = Ask-YesNo $Strings.graphics_ask $true }
        Ask-Name $lab
    }
    if (-not $want) { $todo = @($todo | Where-Object { $_.Key -ne 'node' }) }

    # ---- the programs (winget; Claude Code has its own installer)
    $viaWinget = @($todo | Where-Object { $_.Key -ne 'claude' })
    if ($viaWinget.Count) {
        $S.Winget = Get-Winget
        if (-not $S.Winget -and -not $DryRun) {
            Warn $Strings.winget_none
            Open-AppInstallerPage
            if (@($viaWinget | Where-Object { $_.Required }).Count) { Stop-Install $Strings.winget_stop }
            foreach ($p in $viaWinget) { $p.Result = 'failed'; $p.Words = $Strings.w_nowinget }
            $todo = @($todo | Where-Object { $_.Key -eq 'claude' })
        }
    }
    if ($todo.Count) { Step $Strings.step_programs }
    foreach ($p in $todo) { if ($p.Key -eq 'claude') { Install-ClaudeCode $p } else { Install-Package $p } }
    if ($want -and -not $node.Path -and -not $DryRun) { $want = $false; Warn $Strings.graphics_skipped }

    # ---- Claude sign-in
    $claude = $progs | Where-Object { $_.Key -eq 'claude' }
    if (-not $NoClaude -and ($claude.Path -or $DryRun)) { Step $Strings.step_signin; Confirm-ClaudeLogin $claude.Path }

    # ---- a ZIP copy gets connected to GitHub (a clone already is)
    $py = ($progs | Where-Object { $_.Key -eq 'python' }).Path
    if (-not $simulated -and -not (Test-Path -LiteralPath (Join-Path $lab '.git'))) { Step $Strings.step_connect; Connect-ZipCopy $lab $py }

    # ---- MotionLab itself: setup.bat /lab
    Step $Strings.step_lab
    $rc = Invoke-LabSetup $lab $py ([bool]$want)
    if ($rc -ne 0) { Stop-Install $Strings.lab_failed }
    Send-EnvironmentChange

    # ---- what happened
    Step $Strings.step_done
    if ($DryRun) { Say $Strings.done_dry; exit 0 }
    $now = @($S.Before) + @($progs | Where-Object { $_.Result -eq 'installed' } | ForEach-Object { $_.Name })
    $had = @($progs | Where-Object { $_.Path -and $_.Result -ne 'installed' -and $S.Before -notcontains $_.Name } | ForEach-Object { $_.Name })
    $left = @($progs | Where-Object { $_.Result -eq 'failed' } | ForEach-Object { $_.Name + ' (' + $_.Words + ')' })
    if ($now.Count) { Ok ($Strings.done_installed -f ($now -join ', ')) }
    if ($had.Count) { Note ($Strings.done_had -f ($had -join ', ')) }
    if ($left.Count) { Warn ($Strings.done_skipped -f ($left -join '; ')) }
    if ($S.Reboot) { Warn $Strings.done_reboot }
    Say ($Strings.done_where -f $lab)
    Save-Log
    if ($S.LogCopy) { Note ($Strings.done_log -f $S.LogCopy) }
    if (Start-MotionLab $lab) { Say $Strings.done_opening }
    Wait-Close 60
    exit 0
}

# ------------------------------------------------------------------- install mode: from Downloads to a running lab
function Invoke-Handover([string]$inst, [hashtable]$a) {
    # the cloned copy's own installer goes on, in this window, with the answers (its text is read into memory first)
    Write-Host ''
    Say ($Strings.handover -f (Split-Path -Parent $inst))
    $sb = [scriptblock]::Create([IO.File]::ReadAllText($inst))
    $env:ML_SELF = $inst
    $env:ML_HANDOVER = '1'
    $env:ML_LANG = $S.Lang                                 # the same language (a variable: older copies ignore it)
    & $sb @a
    exit 0
}
function Invoke-Install {
    Start-Log
    Show-Banner
    Say $Strings.intro
    Test-Ready
    Update-SessionPath
    Write-Host ''
    $into = Select-LabFolder
    $pass = @{ Here = $true; Repo = $Repo }
    if ($NoStart) { $pass.NoStart = $true }
    if ($NoClaude) { $pass.NoClaude = $true }
    if ($ShortcutFolder) { $pass.ShortcutFolder = $ShortcutFolder }
    $kind = Get-FolderKind $into
    if ($kind -in 'git', 'zip') {                          # MotionLab is there already: finish / repair it
        Say ($Strings.found_copy -f $into)
        if ($DryRun) { Invoke-Here $into $false }
        $inst = Join-Path $into 'Install-MotionLab.cmd'
        if (-not (Test-File $inst)) { Stop-Install ($Strings.old_copy -f $into) }
        if ($Yes) { $pass.Yes = $true }
        if ($Graphics -ne 'ask') { $pass.Graphics = $Graphics }
        Invoke-Handover $inst $pass
    }
    # a new or empty folder: every question now, then it runs alone
    $progs = Get-Programs $true
    $todo = @($progs | Where-Object { -not $_.Path -and -not ($NoClaude -and $_.Key -eq 'claude') -and -not ($Graphics -eq 'no' -and $_.Key -eq 'node') })
    $have = @($progs | Where-Object { $_.Path })
    Show-Plan $todo $have $into ($Graphics -ne 'no') $true
    if (-not (Ask-YesNo $Strings.go $true)) { Say $Strings.stopped; Save-Log; Wait-Close 0; exit 0 }
    $want = $true
    if ($Graphics -ne 'ask') { $want = ($Graphics -eq 'yes') }
    elseif (-not $Yes) { $want = Ask-YesNo $Strings.graphics_ask $true }
    Ask-Name $null
    $git = $progs | Where-Object { $_.Key -eq 'git' }
    if (-not $git.Path) {
        $S.Winget = Get-Winget
        if (-not $S.Winget -and -not $DryRun) { Warn $Strings.winget_none; Open-AppInstallerPage; Stop-Install $Strings.winget_stop }
        Step $Strings.step_programs
        Install-Package $git
        $S.Done += 'git'                                   # a dry run's -Here part must not list it again
        if ($git.Result -eq 'installed') { $env:ML_INSTALLED = $git.Name }     # the clone's summary names it
    }
    Step $Strings.step_download
    Get-MotionLab $into $git.Path
    if ($DryRun) { $S.Graphics = $want; Invoke-Here $into $true }
    $S.Lab = $into
    $inst = Join-Path $into 'Install-MotionLab.cmd'
    if (-not (Test-File $inst)) {                          # a tested version from before the installer
        Say $Strings.old_clone
        $cmd = $env:ComSpec; if (-not $cmd) { $cmd = 'cmd.exe' }
        $rc = Invoke-Visible $cmd @('/d', '/c', '.\setup.bat') $into
        Save-Log
        exit $rc
    }
    $pass.Yes = $true
    $pass.Graphics = 'no'; if ($want) { $pass.Graphics = 'yes' }
    Invoke-Handover $inst $pass
}

# --------------------------------------------------------------------------------------------------------- start
try {
    if ($Here) {
        if (-not $S.Self) { throw 'start it with the .cmd file (ML_SELF is not set)' }
        Invoke-Here (Split-Path -Parent $S.Self) $false
    } else { Invoke-Install }
    exit 0
} catch {
    Write-Host ''
    Out-Line '  [!]  ' ($Strings.crash -f $_.Exception.Message) 'Red'
    Say $Strings.crash_help
    Save-Log
    Wait-Close 0
    exit 1
}
