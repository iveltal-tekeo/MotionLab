"""The app's settings and the outside programs it works with: ffmpeg (required), yt-dlp (downloads), Claude Code
(the "Open in Claude" buttons: each asks for one task - TASKS - and shows a dialog with the model - MODELS, Opus
by default - and the task's recommended effort level, unless Settings fixes them), DaVinci Resolve and Microsoft
Edge. Everything is found automatically; paths can be set on the Settings
page. Settings live in settings.json in the lab folder (personal: not in the repo).

Nothing here installs anything: missing programs are reported with how to get them."""
from __future__ import annotations

import datetime
import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from motionlab import i18n as I18N
from motionlab.styles import CATEGORIES, DEFAULT as CATEGORY_DEFAULT, norm as norm_category
from motionlab.util import LAB, REFS

from . import data

SETTINGS = LAB / "settings.json"
APPDIR = LAB / ".app"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
NEW_CONSOLE = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
DEFAULTS = {"ytdlp_path": "", "download_preset": "mp4_1080", "download_name": "%(title).80s [%(id)s].%(ext)s",
            "claude_path": "", "default_category": CATEGORY_DEFAULT, "author": "", "update_mode": "ask",
            "claude_effort": "auto", "claude_model": "opus", "claude_ask": True, "default_focus": "both",
            "download_login": False, "download_browser": "firefox", "language": "en"}
# Settings > General > Language (2026-10-18, the user: "we need a spanish version of the entire app"; Spain, tú): the
# app's words and Claude's replies - what Claude writes into the lab stays English (motionlab\i18n.py)
LANGUAGES = I18N.LANGUAGES
# the first message of a Claude window opened from the app in Spanish ends with this line: ASCII (the same bytes in
# any console code page) and added AFTER the 600-character cut, so it is never lost; a free chat (no first message)
# stays empty. The skills read it (their first line: "If the first message says to reply in Spanish ...")
LANG_LINE = {"es": " - reply to the user in Spanish (Spain, tu); commands, ids, file names and the lab's formats stay as "
                   "they are; write the lab's own files (reviews, lessons, cards, memory) in English"}
# Settings > Downloads > "Use my browser's login for downloads" (0.4.2.1, off by default): yt-dlp reads the login
# (cookies) of this browser on this PC for each download. Firefox works best: Chrome / Edge lock their cookie file
# while they run and encrypt it, so yt-dlp often cannot read it.
BROWSERS = {"firefox": "Firefox (works best)", "chrome": "Google Chrome", "edge": "Microsoft Edge", "brave": "Brave"}
BOOL_KEYS = ("claude_ask", "download_login")
# a new version on GitHub: "ask" = the sidebar's Update button + what's new, one click installs it (since 0.3.0;
# 0.2.x installed by itself at start-up), "auto" = install it when MotionLab starts, "off" = never look
UPDATE_MODES = ("ask", "auto", "off")
EFFORTS = ("low", "medium", "high", "xhigh", "max")
# the model the app's Claude windows start on: "opus" = Claude Code's default model, on every plan (the default here
# too, so a friend on a Pro plan never meets a "requires usage credits" prompt), "fable" = Anthropic's strongest
# model (Max plans: its own weekly limit; elsewhere Claude Code asks before billing credits), "auto" = whatever the
# user chose in Claude Code (/model). Every button shows a dialog with the model + effort unless Settings says not to.
MODELS = ("opus", "fable", "auto")
# what the app's Claude buttons ask for -> (effort used when Settings says "recommended", session name,
# "Fable fits": long, ambiguous or image-heavy work where Fable is clearly stronger - the dialog says so)
TASKS = {
    "free": (None, "MotionLab", False),               # sidebar / Settings: Claude Code's own default
    "review": ("high", "MotionLab review", True),      # /analyze-reference: read every contact sheet, name each effect
    "feedback": ("high", "MotionLab feedback", False), # apply MOTIONLAB FEEDBACK: lessons, thresholds, re-check
    "lessons": ("high", "MotionLab lessons", False),   # review friends' incoming lessons
    "library": ("high", "MotionLab library", False),   # save library picks as Fusion macros (needs Resolve)
    "recreate": ("xhigh", "MotionLab recreate", True), # /recreate-video: a whole edit with your footage
    "generate": ("xhigh", "MotionLab generate", True), # /generate-video: a video from zero (graphics / AI prompts)
    "prompt": ("medium", "MotionLab prompt", False),   # /write-prompt: split examples, write new prompts (text only)
    "script": ("high", "MotionLab script", False),     # /write-script: check, improve or write what you say on camera
    "title": ("high", "MotionLab title", False),       # /write-title: titles, thumbnails, the package of a video (0.4.3)
    "plan": ("medium", "MotionLab next steps", False), # /whats-next: where the lab stands, options, a recommendation
}
# on Fable one level less is enough: Anthropic's guidance puts Fable at "high" where Opus needed "xhigh"
FABLE_EFFORT = {"xhigh": "high", "max": "xhigh"}
# preset id -> (label, yt-dlp arguments, folder inside the lab)
VIDEO_F = "bv*+ba/b[vcodec!=none]/bv*"       # never a sound-only file in refs\ (a SoundCloud link fails clearly)
PRESETS = {
    # -S res:1080 = the SHORT side up to 1080: a vertical 1080x1920 TikTok / Reel / Short is 1080p (0.3.2's height
    # filter took 576x1024 when 720x1280 was there); then the highest frame rate; then H.264 + AAC at the same size
    "mp4_1080": ("MP4 video, best up to 1080p (recommended)",
                 ["-f", VIDEO_F, "-S", "res:1080,fps,vcodec:h264,acodec:aac", "--merge-output-format", "mp4"], "refs"),
    "mp4_best": ("MP4 video, best quality (can be 4K)", ["-f", VIDEO_F, "--merge-output-format", "mp4"], "refs"),
    "mp3": ("MP3 audio only (e.g. the song)", ["-x", "--audio-format", "mp3", "--audio-quality", "0"], "refs/audio"),
}
DOWNLOAD_TITLE = "Download ({what}) from {site}"      # a download job's title (what = the preset's label before " (")
# how to get a missing program: setup.bat in the lab folder installs it (Install-MotionLab.cmd -Here, 2026-10-18 -
# the user: "its very hard for people to read the steps or install git or do all fo that throught the terminal")
HOW = {
    "ffmpeg": "required for every analysis - double-click setup.bat in the MotionLab folder: it installs what is "
              "missing (then restart MotionLab)",
    "yt-dlp": "optional, for 'Download from a link' - setup.bat in the MotionLab folder installs it, or put "
              "yt-dlp.exe anywhere and set its path here. TikTok and Instagram change often: keep it up to date",
    # yt-dlp's wiki "EJS" (checked 2026-10-15, page edited 2026-07-12): YouTube needs an external JavaScript
    # runtime; Deno (>= 2.3.0) is the recommended one and the only one on by default (node / quickjs / bun need
    # --js-runtimes); the yt-dlp.exe build bundles the yt-dlp-ejs scripts, pip installs need "yt-dlp[default]"
    "deno": "optional, for YouTube downloads: recent yt-dlp needs a JavaScript runtime for YouTube (Deno 2.3 or "
            "newer) - setup.bat in the MotionLab folder installs it, then restart MotionLab",
    "claude": "for the review and learning steps - double-click setup.bat in the MotionLab folder: it installs "
              "Claude Code and signs you in (your Claude Pro or Max plan)",
    "git": "for updates and sharing knowledge - double-click setup.bat in the MotionLab folder: it installs git "
           "(and connects a copy that came as a ZIP)",
    "resolve": "optional (rebuilding in DaVinci Resolve Studio)",
    "hyperframes": "optional, renders graphics written as HTML into transparent clips for rebuilds (tools\\overlay.py) "
                   "- needs Node.js; Install below or setup.bat (pinned version, about 130 MB + its Chrome 150 MB)",
    "node": "optional, for the motion graphics and graphics written as HTML (HyperFrames) - double-click setup.bat "
            "in the MotionLab folder and say yes to motion graphics: it installs Node.js and HyperFrames",
    "edge": "the app window (comes with Windows)",
    "speech": "optional, the words of your own videos for captions (faster-whisper on the CPU, ~60 MB + the model "
              "small 464 MB, or base 141 MB for slow laptops) - Install below",
}
_versions: dict[tuple, str | None] = {}


# ------------------------------------------------------------------------------------------------- settings
def load() -> dict:
    s = dict(DEFAULTS)
    raw = data.read_json(SETTINGS, {}) or {}
    if "default_style" in raw and "default_category" not in raw:              # v0.2.0 name
        raw["default_category"] = raw["default_style"]
    if "update_mode" not in raw:          # 0.2.x: update_check / update_auto; installing by itself was only the default
        raw["update_mode"] = "off" if raw.get("update_check") is False else "ask"
    s.update({k: v for k, v in raw.items() if k in DEFAULTS})
    s["default_category"] = norm_category(s["default_category"]) or CATEGORY_DEFAULT
    if s["update_mode"] not in UPDATE_MODES:
        s["update_mode"] = "ask"
    if s["language"] not in LANGUAGES:
        s["language"] = "en"
    return s


def save(body: dict) -> dict:
    s = load()
    for k, v in body.items():
        if k == "default_style":
            k = "default_category"
        if k not in DEFAULTS:
            continue
        if k in BOOL_KEYS:
            s[k] = v if isinstance(v, bool) else str(v).strip().lower() in ("1", "true", "on", "yes")
            continue
        v = str(v).strip().strip('"')
        if k == "download_browser" and v not in BROWSERS:
            raise ValueError(I18N.t("unknown browser {id}", id=v))
        if k == "update_mode" and v not in UPDATE_MODES:
            raise ValueError(I18N.t("unknown update mode {id}", id=v))
        if k == "author":
            v = re.sub(r"[^a-z0-9_-]", "", v.lower().replace(" ", "-"))[:24]
        if k.endswith("_path") and v and not Path(v).is_file():
            raise ValueError(I18N.t("{setting}: no such file: {file}", setting=k, file=v))
        if k == "download_preset" and v not in PRESETS:
            raise ValueError(I18N.t("unknown preset {id}", id=v))
        if k == "download_name":
            check_name(v)
        if k == "default_category":
            v = norm_category(v) or ""
            if v not in CATEGORIES:
                raise ValueError(I18N.t("unknown category"))
        if k == "claude_effort" and v not in ("auto", *EFFORTS):
            raise ValueError(I18N.t("unknown effort {id}", id=v))
        if k == "claude_model" and v not in MODELS:
            raise ValueError(I18N.t("unknown model {id}", id=v))
        if k == "default_focus" and v not in ("content", "cinematic", "both"):
            raise ValueError(I18N.t("unknown focus {id}", id=v))
        if k == "language" and v not in LANGUAGES:
            raise ValueError(I18N.t("unknown language {id}", id=v))
        s[k] = v
    data.write_json_atomic(SETTINGS, s)
    I18N.forget()                                         # the page reloads in the new language at once
    return s


def check_name(t: str) -> str:
    """A yt-dlp output name template that stays inside the target folder."""
    if not t or len(t) > 160 or not re.fullmatch(r"[\w\s%().,\[\]\-#+&'!]+", t) or "%(ext)s" not in t or ".." in t:
        raise ValueError(I18N.t("name template: letters, spaces, yt-dlp fields like %(title)s - no folders - and it "
                                "must end with .%(ext)s"))
    return t


# ------------------------------------------------------------------------------------------------- programs
def _which(*names: str) -> str | None:
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return None


def merge_registry_path() -> list[str]:
    """Add the PATH entries Windows keeps in the registry (the machine's, then the user's) that this process lacks, after
    its own ones: a program installed after Explorer read its PATH (the installer, setup.bat, winget) is found when
    MotionLab starts - without signing out first. tools\\app.py calls it at start; the jobs inherit it. Returns the
    entries added; never raises (a PC without the keys or not Windows = nothing to do)."""
    added: list[str] = []
    if os.name != "nt":
        return added
    try:
        import winreg
        have = [p for p in os.environ.get("PATH", "").split(os.pathsep) if p.strip()]
        seen = {os.path.normcase(p.strip().rstrip("\\/")) for p in have}
        for root, key in ((winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
                          (winreg.HKEY_CURRENT_USER, "Environment")):
            try:
                with winreg.OpenKey(root, key) as k:
                    val, _kind = winreg.QueryValueEx(k, "Path")
            except OSError:
                continue
            for p in winreg.ExpandEnvironmentStrings(str(val or "")).split(";"):
                n = os.path.normcase(p.strip().rstrip("\\/"))
                if n and n not in seen:
                    seen.add(n)
                    added.append(p.strip())
        if added:
            os.environ["PATH"] = os.pathsep.join(have + added)
    except Exception:                                   # noqa: BLE001 - the app must start whatever the registry says
        return []
    return added


def find(name: str, s: dict | None = None) -> str | None:
    s = s or load()
    if name == "ffmpeg":
        return _which("ffmpeg")
    if name == "yt-dlp":
        if s.get("ytdlp_path") and Path(s["ytdlp_path"]).is_file():
            return s["ytdlp_path"]
        local = LAB / "tools" / "bin" / "yt-dlp.exe"
        return _which("yt-dlp") or (str(local) if local.is_file() else None)
    if name == "claude":
        if s.get("claude_path") and Path(s["claude_path"]).is_file():
            return s["claude_path"]
        home = Path.home()
        for p in (home / ".local" / "bin" / "claude.exe", home / "AppData" / "Roaming" / "npm" / "claude.cmd"):
            if p.is_file():
                return _which("claude") or str(p)
        return _which("claude")
    if name == "git":
        return _which("git") or next((str(p) for p in (Path(r"C:\Program Files\Git\cmd\git.exe"),
                                                        Path(r"C:\Program Files (x86)\Git\cmd\git.exe"))
                                      if p.is_file()), None)
    if name == "node":
        return _which("node")
    if name == "deno":                         # on PATH, or where its installers put it (PATH not refreshed yet)
        home, local = Path.home(), Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        for p in (home / ".deno" / "bin" / "deno.exe", local / "Microsoft" / "WinGet" / "Links" / "deno.exe"):
            if p.is_file():
                return _which("deno") or str(p)
        pk = local / "Microsoft" / "WinGet" / "Packages"
        hits = sorted(pk.glob("DenoLand.Deno_*/deno.exe")) if pk.is_dir() else []
        return _which("deno") or (str(hits[-1]) if hits else None)
    if name == "hyperframes":
        p = LAB / "tools" / "overlays" / "node_modules" / "hyperframes" / "bin" / "hyperframes.mjs"
        return str(p) if p.is_file() else None
    if name == "speech":
        from motionlab import speech as SP
        spec = importlib.util.find_spec("faster_whisper") if SP.available() else None
        return str(Path(spec.origin).parent) if spec and spec.origin else None
    if name == "resolve":
        p = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Blackmagic Design" / "DaVinci Resolve" / "Resolve.exe"
        return str(p) if p.is_file() else None
    if name == "edge":
        for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles")):
            p = Path(base or "") / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            if base and p.is_file():
                return str(p)
        return None
    raise ValueError(name)


def version(exe: str | None, args=("--version",)) -> str | None:
    """First line of `exe --version` (cached until the file changes)."""
    if not exe:
        return None
    try:
        key = (exe, os.stat(exe).st_mtime_ns)
    except OSError:
        return None
    if key not in _versions:
        try:
            out = subprocess.run([exe, *args], capture_output=True, text=True, timeout=30, creationflags=NO_WINDOW,
                                 encoding="utf-8", errors="replace")
            _versions[key] = ((out.stdout or out.stderr).strip().splitlines() or [""])[0][:80] or None
        except (OSError, subprocess.TimeoutExpired):
            _versions[key] = None
    return _versions[key]


def age_words(days: int) -> str:
    """57 -> "2 months old" (yt-dlp's version is its release date)."""
    if days < 1:
        return "from today"
    if days < 14:
        return f"{days} day{'s' if days > 1 else ''} old"
    if days < 45:
        return f"{round(days / 7)} weeks old"
    m = round(days / 30.4)
    return f"{m} month{'s' if m > 1 else ''} old" if m < 12 else f"{days / 365:.1f} years old".replace(".0 ", " ")


def age_text(days: int) -> str:
    """age_words in the app's language - for the Settings page only (a job's log and the self-check keep the English
    age_words)."""
    if I18N.lang() == "en":
        return age_words(days)
    if days < 1:
        return I18N.t("from today")
    if days < 14:
        return I18N.tn(days, "{n} day old", "{n} days old")
    if days < 45:
        return I18N.tn(round(days / 7), "{n} week old", "{n} weeks old")
    m = round(days / 30.4)
    if m < 12:
        return I18N.tn(m, "{n} month old", "{n} months old")
    y = round(days / 365, 1)
    return I18N.tn(int(y) if y == int(y) else y, "{n} year old", "{n} years old")


YTDLP_OLD_DAYS = 30                     # older than this = amber in Settings (sites change faster than that)


def install_kind(exe: str) -> dict:
    """How this yt-dlp was installed -> {"kind": winget | pip | exe, "label", "cmd"}: winget's copy (its real path is
    under WinGet\\Packages, its Links folder points there) updates with winget, a copy inside a Python environment
    (a Scripts folder with python.exe and the environment's yt_dlp package) with pip, the stand-alone exe itself."""
    real = Path(os.path.realpath(exe))
    low = str(real).lower().replace("/", "\\")
    if "\\winget\\packages\\" in low or "\\winget\\links\\" in low:
        wg = _which("winget") or str(Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
                                     / "Microsoft" / "WindowsApps" / "winget.exe")
        # --skip-dependencies: winget's yt-dlp also pulls DenoLand.Deno and yt-dlp.FFmpeg (a second, untested ffmpeg
        # of 431 MB that can land on PATH); yt-dlp gets MotionLab's ffmpeg anyway (--ffmpeg-location, download_cmd)
        return {"kind": "winget", "label": "installed with winget",
                "cmd": [wg, "upgrade", "--id", "yt-dlp.yt-dlp", "--exact", "--silent", "--disable-interactivity",
                        "--accept-source-agreements", "--accept-package-agreements", "--skip-dependencies"]}
    if real.parent.name.lower() == "scripts":
        env = real.parent.parent
        for py in (real.parent / "python.exe", env / "python.exe"):
            if py.is_file() and ((env / "Lib" / "site-packages" / "yt_dlp").is_dir() or (env / "pyvenv.cfg").is_file()):
                return {"kind": "pip", "label": "installed with pip in a Python environment",
                        "cmd": [str(py), "-m", "pip", "install", "-U", "yt-dlp[default]"]}
    return {"kind": "exe", "label": "the stand-alone yt-dlp.exe", "cmd": [str(exe), "-U"]}


def ytdlp_info(s: dict | None = None) -> dict:
    """yt-dlp for Settings: found, version, its age in words (the version is a date: 2026.08.19), how it was installed
    (what *Update yt-dlp* runs) and whether a newer one is out: the newest release from the daily check
    (upstream.ytdlp_latest, PyPI) - "old" = a newer release exists; only when that is unknown (offline, never
    checked) the age decides (older than YTDLP_OLD_DAYS)."""
    from motionlab import upstream as UP
    exe = find("yt-dlp", s)
    if not exe:
        return {"found": False}
    v = version(exe) or ""
    out = {"found": True, "path": exe, "version": v or None, "age_days": None, "age": None, "old": False,
           "latest": None, "newest": None, "checked": None, **install_kind(exe)}
    m = re.search(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", v)
    if m:
        try:
            days = (datetime.date.today() - datetime.date(*map(int, m.groups()))).days
            out.update(age_days=days, age=age_words(max(0, days)), old=days > YTDLP_OLD_DAYS)
        except ValueError:
            pass
    L = UP.ytdlp_latest()
    if L and m:
        newest = UP.dkey(v) >= UP.dkey(L["latest"])
        out.update(latest=".".join(f"{x:02d}" if i else str(x) for i, x in enumerate(UP.dkey(L["latest"])[:3])),
                   newest=newest, old=not newest, checked=L.get("checked"))
    return out


DENO_MIN = (2, 3, 0)                    # yt-dlp's wiki "EJS", checked 2026-10-15


def deno_info(s: dict | None = None) -> dict:
    """Deno for YouTube downloads: found, version, new enough (>= DENO_MIN), on PATH (else yt-dlp is told where)."""
    exe = find("deno", s)
    if not exe:
        return {"found": False, "how": HOW["deno"]}
    v = version(exe) or ""
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", v)
    vt = tuple(map(int, m.groups())) if m else None
    return {"found": True, "path": exe, "version": ".".join(map(str, vt)) if vt else (v or None),
            "new_enough": vt is None or vt >= DENO_MIN, "on_path": bool(_which("deno")), "how": HOW["deno"]}


def resolve_mcp_state() -> dict:
    """The Resolve MCP for Claude Code (tools\\resolve_mcp.py): set up on this PC? (marker written by its install)"""
    mark = APPDIR / "resolve_mcp" / "registered.json"
    root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "davinci-resolve-mcp"
    info = data.read_json(mark, {}) if mark.exists() else {}
    return {"registered": bool(info), "installed": (root / "src" / "server.py").exists(),
            "version": info.get("version"), "when": info.get("when")}


def tools(full: bool = False) -> list[dict]:
    """Every outside program: found? where, version (full=True runs them once), what it is for / how to get it."""
    s = load()
    out = [{"name": "python", "label": "Python", "found": True, "path": sys.executable,
            "version": sys.version.split()[0], "need": "required", "how": "the lab's .venv"}]
    for n, label, need in (("ffmpeg", "ffmpeg", "required"), ("claude", "Claude Code", "recommended"),
                           ("git", "Git", "recommended"), ("yt-dlp", "yt-dlp", "optional"),
                           ("node", "Node.js (HTML overlays)", "optional"),
                           ("deno", "Deno (YouTube downloads)", "optional"),
                           ("hyperframes", "HyperFrames (HTML overlays)", "optional"),
                           ("resolve", "DaVinci Resolve", "optional"),
                           ("speech", "Speech to text (captions)", "optional"),
                           ("edge", "Microsoft Edge", "required")):
        p = find(n, s)
        v = None
        if full and p:
            v = version(p, ("-version",) if n == "ffmpeg" else ("--version",)) if n not in ("resolve", "edge",
                                                                                        "hyperframes") else None
            if n == "hyperframes":
                v = (data.read_json(Path(p).parents[1] / "package.json", {}) or {}).get("version")
                chrome = Path.home() / ".cache" / "hyperframes" / "chrome"
                v = f"{v}" + ("" if chrome.is_dir() and any(chrome.rglob("chrome-headless-shell.exe"))
                              else " (its Chrome not downloaded yet)")
            if n == "speech":
                from motionlab import speech as SP
                v = f"{SP.version()} - model small {'ready' if SP.model_ready('small') else 'not downloaded yet'}"
            if n == "ffmpeg" and v:
                v = v.replace("ffmpeg version ", "").split(" Copyright")[0]
            if n == "deno" and v:
                v = deno_info(s).get("version") or v
        row = {"name": n, "label": label, "found": bool(p), "path": p, "version": v, "need": need, "how": HOW[n]}
        if full and p and n == "yt-dlp":            # its age + how Update yt-dlp would update it (in the app's language:
            y = ytdlp_info(s)                       # this row is the Settings page's; ytdlp_info stays English for the job)
            row.update(age=age_text(max(0, y["age_days"])) if y.get("age_days") is not None else y.get("age"),
                       age_days=y.get("age_days"), old=y.get("old"),
                       install=I18N.t(y["label"]) if y.get("label") else y.get("label"),
                       latest=y.get("latest"), newest=y.get("newest"), checked=y.get("checked"))
        if full and p and n == "deno":
            row["old"] = not deno_info(s).get("new_enough", True)
        out.append(row)
    return out


# ------------------------------------------------------------------------------------------------- downloads
def download_cmd(url: str, preset: str) -> tuple[str, list[str]]:
    """(title, command) for the 'download' job: yt-dlp, one video (no playlists), into refs\\ (audio: refs\\audio\\);
    the final file path is printed last so the app can offer 'Analyse it'."""
    s = load()
    url = url.strip()
    if not re.fullmatch(r"https?://[^\s\"'<>|^`]{4,2000}", url):
        raise ValueError(I18N.t("paste a full link starting with https://"))
    preset = preset or s["download_preset"]
    if preset not in PRESETS:
        raise ValueError(I18N.t("unknown preset {id}", id=preset))
    exe = find("yt-dlp", s)
    if not exe:
        raise ValueError(I18N.t("yt-dlp not found - {how}", how=I18N.t(HOW["yt-dlp"])))
    label, args, folder = PRESETS[preset]
    out_dir = LAB / folder
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [exe, "--no-playlist", "--newline", "--progress", "--print", "after_move:filepath", "-P", str(out_dir),
           "-o", check_name(s["download_name"]), *args]
    ff = find("ffmpeg", s)
    if ff:
        cmd += ["--ffmpeg-location", str(Path(ff).parent)]
    if s.get("download_login"):                    # the user's own choice in Settings, off by default
        cmd += ["--cookies-from-browser", s.get("download_browser") if s.get("download_browser") in BROWSERS
                else "firefox"]
    deno = find("deno", s)
    yv = re.search(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", version(exe) or "")
    if deno and not _which("deno") and yv and tuple(map(int, yv.groups())) >= (2025, 11, 12):
        cmd += ["--js-runtimes", f"deno:{deno}"]    # Deno installed but not on PATH yet: tell yt-dlp where
    host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
    # the job's title: shown in the app's language, its English (.en) is what download.py prints into the job's log
    what = data.Words.of(I18N.t(label).split(" (")[0], label.split(" (")[0])
    return data.words(DOWNLOAD_TITLE, what=what, site=host), cmd + ["--", url]


# ------------------------------------------------------------------------------------------------- Claude Code
_flags: dict[tuple, str] = {}


def claude_flags(exe: str) -> str:
    """`claude --help` of this Claude Code (cached until the program changes): older versions lack --effort / --name."""
    try:
        key = (exe, os.stat(exe).st_mtime_ns)
    except OSError:
        return ""
    if key not in _flags:
        try:
            out = subprocess.run([exe, "--help"], capture_output=True, text=True, timeout=60, creationflags=NO_WINDOW,
                                 encoding="utf-8", errors="replace")
            _flags[key] = out.stdout + out.stderr
        except (OSError, subprocess.TimeoutExpired):
            _flags[key] = ""
    return _flags[key]


def _cmd_text(s: str, n: int) -> str:
    """Text that is safe inside "..." on a cmd line: double quotes become single ones (a quoted path stays one
    path), %, ^, &, |, <, >, backticks and line breaks become spaces."""
    return re.sub(r" {2,}", " ", re.sub(r'[%^&|<>\r\n`]', " ", str(s).replace('"', "'")))[:n].strip()


def claude_model(task: str, s: dict | None = None) -> str | None:
    """The model one of the app's Claude buttons starts on: Settings > Claude Code ("auto" = none = Claude Code's
    own choice). The task only changes the dialog's hint (TASKS "Fable fits"), never the default."""
    s = s or load()
    chosen = s.get("claude_model") or "opus"
    return chosen if chosen in MODELS and chosen != "auto" else None


def claude_effort(task: str, s: dict | None = None, model: str | None = None) -> str | None:
    """The effort level for one of the app's Claude buttons: Settings > Claude Code, or the task's recommendation
    (one level lower on Fable, FABLE_EFFORT)."""
    s = s or load()
    chosen = s.get("claude_effort") or "auto"
    if chosen in EFFORTS:
        return chosen
    rec = TASKS.get(task, TASKS["free"])[0]
    return FABLE_EFFORT.get(rec, rec) if model == "fable" and rec else rec


def claude_options(task: str = "free", s: dict | None = None) -> dict:
    """What the app's dialog shows before it opens Claude Code: the model and effort it would use, the choices, and
    whether the task is one where Fable is clearly stronger."""
    s = s or load()
    task = task if task in TASKS else "free"
    model = claude_model(task, s)
    return {"model": model or "auto", "effort": claude_effort(task, s, model), "models": list(MODELS),
            "efforts": list(EFFORTS), "fable_fits": TASKS[task][2], "ask": bool(s.get("claude_ask", True)),
            "recommended": {m: claude_effort(task, {**s, "claude_effort": "auto"}, m) for m in ("opus", "fable")}}


def claude_launcher(prompt: str = "", task: str = "free", label: str = "", model: str | None = None,
                    effort: str | None = None) -> tuple[str, str, str | None, str | None]:
    """(cleaned prompt, .cmd text, effort used, model used) that opens Claude Code in the lab folder with an optional
    first message, the model (--model) and effort level (--effort) - the dialog's choice, else Settings / the task's
    recommendation - and a session name (--name, shown by /resume). The prompt loses the characters cmd would
    interpret (quotes, %, ^, &, |, <, >) - so the user's own words go to Claude in a file and the prompt names it
    (e.g. /write-prompt request req-012). In Spanish (Settings > Language) LANG_LINE follows the cut prompt. Older
    Claude Codes without a flag get the command without it."""
    if task not in TASKS:
        raise ValueError(I18N.t("unknown task {id}", id=repr(task)))
    if model is not None and model not in MODELS:
        raise ValueError(I18N.t("unknown model {id}", id=repr(model)))
    if effort is not None and effort not in EFFORTS:
        raise ValueError(I18N.t("unknown effort {id}", id=repr(effort)))
    s = load()
    exe = find("claude", s)
    if not exe:
        raise FileNotFoundError("Claude Code (claude) - " + I18N.t(HOW["claude"]))
    clean = _cmd_text(prompt, 600)
    if clean and I18N.lang() in LANG_LINE:                # after the cut: the language line is never lost
        clean += LANG_LINE[I18N.lang()]
    help_text = claude_flags(exe)
    args = []
    model = claude_model(task, s) if model is None else (None if model == "auto" else model)
    if model and "--model" not in help_text:
        model = None
    if model:
        args.append(f"--model {model}")
    effort = (effort or claude_effort(task, s, model)) if "--effort" in help_text else None
    if effort:
        args.append(f"--effort {effort}")
    name = _cmd_text(f"{TASKS[task][1]} {label}", 60)
    if task != "free" and "--name" in help_text:
        args.append(f'--name "{name}"')
    # chcp 65001: the file is UTF-8 but cmd reads it in the OEM code page (850 ...), so a lab folder or claude.exe
    # under a Windows user name with an accent (José, María - common for Spanish friends) was "not found" (2026-10-18)
    lines = ["@echo off", "chcp 65001 >nul", "title MotionLab - Claude Code", f'cd /d "{LAB}"',
             f'call "{exe}"' + "".join(" " + a for a in args) + (f' "{clean}"' if clean else "")]
    return clean, "\r\n".join(lines) + "\r\n", effort, model


def open_claude(prompt: str = "", task: str = "free", label: str = "", model: str | None = None,
                effort: str | None = None) -> dict:
    """Open Claude Code in a new console in the lab folder, optionally with a first message (the app's fixed
    hand-off texts: /analyze-reference ..., apply the feedback in ...), the model and the effort level (the
    dialog's choice, else Settings / the task's recommendation)."""
    clean, text, effort, model = claude_launcher(prompt, task, label, model, effort)
    APPDIR.mkdir(exist_ok=True)
    launcher = APPDIR / "open_claude.cmd"
    launcher.write_text(text, encoding="utf-8")
    subprocess.Popen(["cmd", "/c", str(launcher)], cwd=str(LAB), creationflags=NEW_CONSOLE)
    return {"ok": True, "prompt": clean, "effort": effort, "model": model}


# ------------------------------------------------------------------------------------------------- shortcuts
def make_shortcut(where: str, folder: Path | None = None) -> dict:
    """A 'MotionLab' shortcut (the app icon, no console window) on the Desktop or in the Start menu - only when the
    user clicks the button for it (folder: tests only)."""
    if where not in ("desktop", "startmenu") and folder is None:
        raise ValueError(where)
    pyw = LAB / ".venv" / "Scripts" / "pythonw.exe"
    if not pyw.is_file():
        raise FileNotFoundError(str(pyw))
    icon = LAB / "MotionLab.ico"
    q = lambda x: "'" + str(x).replace("'", "''") + "'"                  # noqa: E731 - a PowerShell string
    where_ps = q(folder) if folder else f"[Environment]::GetFolderPath('{'Desktop' if where == 'desktop' else 'Programs'}')"
    ps = (f"$d = {where_ps}; "
          "$s = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d 'MotionLab.lnk')); "
          f"$s.TargetPath = {q(pyw)}; $s.Arguments = {q(chr(34) + str(LAB / 'tools' / 'app.py') + chr(34))}; "
          f"$s.WorkingDirectory = {q(LAB)}; "
          + (f"$s.IconLocation = {q(str(icon) + ',0')}; " if icon.is_file() else "")
          + "$s.Description = 'MotionLab'; $s.Save(); Join-Path $d 'MotionLab.lnk'")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=30,
                         creationflags=NO_WINDOW)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip()[-300:] or I18N.t("could not create the shortcut"))
    return {"ok": True, "path": out.stdout.strip().splitlines()[-1] if out.stdout.strip() else ""}


def downloads() -> list[dict]:
    """Recently downloaded files (refs\\ and refs\\audio\\), newest first; the files of one post (a carousel, a
    photo post: downloads.json "post") carry post / part / parts (data.post_of)."""
    out = []
    idx = data.read_json(REFS / "downloads.json", {}) or {}
    for d in (REFS, REFS / "audio"):
        if d.is_dir():
            for p in d.iterdir():
                post = data.post_of(idx.get(p.name))
                if p.is_file() and (p.suffix.lower() in data.VIDEO_EXT | {".mp3", ".m4a", ".wav"}
                                    or (p.suffix.lower() in data.IMAGE_EXT and post)):
                    out.append({"name": p.name, "path": str(p), "rel": data.rel(p), "size": p.stat().st_size,
                                "modified": data.stamp(p.stat().st_mtime), "audio": d.name == "audio",
                                "t": p.stat().st_mtime, **post})
    return sorted(out, key=lambda x: -x["t"])[:30]

