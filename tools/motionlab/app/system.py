"""The app's settings and the outside programs it works with: ffmpeg (required), yt-dlp (downloads), Claude Code
(the "Open in Claude" buttons), DaVinci Resolve and Microsoft Edge. Everything is found automatically; paths can be
set on the Settings page. Settings live in settings.json in the lab folder (personal: not in the repo).

Nothing here installs anything: missing programs are reported with how to get them."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from motionlab.styles import CATEGORIES, DEFAULT as CATEGORY_DEFAULT, norm as norm_category
from motionlab.util import LAB, REFS

from . import data

SETTINGS = LAB / "settings.json"
APPDIR = LAB / ".app"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
NEW_CONSOLE = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
DEFAULTS = {"ytdlp_path": "", "download_preset": "mp4_1080", "download_name": "%(title).80s [%(id)s].%(ext)s",
            "claude_path": "", "default_category": CATEGORY_DEFAULT, "author": "", "update_check": True,
            "update_auto": True}
BOOLS = {"update_check", "update_auto"}
# preset id -> (label, yt-dlp arguments, folder inside the lab)
PRESETS = {
    "mp4_1080": ("MP4 video, best up to 1080p (recommended)",
                 ["-f", "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]/bv*[height<=1080]+ba/"
                        "b[height<=1080]", "--merge-output-format", "mp4"], "refs"),
    "mp4_best": ("MP4 video, best quality (can be 4K)", ["-f", "bv*+ba/b", "--merge-output-format", "mp4"], "refs"),
    "mp3": ("MP3 audio only (e.g. the song)", ["-x", "--audio-format", "mp3", "--audio-quality", "0"], "refs/audio"),
}
HOW = {
    "ffmpeg": "required for every analysis - install: winget install Gyan.FFmpeg (then restart the app)",
    "yt-dlp": "optional, for 'Download from a link' - install: winget install yt-dlp.yt-dlp, or put yt-dlp.exe "
              "anywhere and set its path here",
    "claude": "for the review and learning steps - install Claude Code: https://claude.com/claude-code",
    "git": "for automatic updates and sharing knowledge - install: winget install Git.Git (or https://git-scm.com)",
    "resolve": "optional (rebuilding in DaVinci Resolve Studio)",
    "edge": "the app window (comes with Windows)",
}
_versions: dict[tuple, str | None] = {}


# ------------------------------------------------------------------------------------------------- settings
def load() -> dict:
    s = dict(DEFAULTS)
    raw = data.read_json(SETTINGS, {}) or {}
    if "default_style" in raw and "default_category" not in raw:              # v0.2.0 name
        raw["default_category"] = raw["default_style"]
    s.update({k: v for k, v in raw.items() if k in DEFAULTS})
    s["default_category"] = norm_category(s["default_category"]) or CATEGORY_DEFAULT
    return s


def save(body: dict) -> dict:
    s = load()
    for k, v in body.items():
        if k == "default_style":
            k = "default_category"
        if k not in DEFAULTS:
            continue
        if k in BOOLS:
            s[k] = v in (True, "true", "1", 1, "on")
            continue
        v = str(v).strip().strip('"')
        if k == "author":
            v = re.sub(r"[^a-z0-9_-]", "", v.lower().replace(" ", "-"))[:24]
        if k.endswith("_path") and v and not Path(v).is_file():
            raise ValueError(f"{k}: no such file: {v}")
        if k == "download_preset" and v not in PRESETS:
            raise ValueError(f"unknown preset {v}")
        if k == "download_name":
            check_name(v)
        if k == "default_category":
            v = norm_category(v) or ""
            if v not in CATEGORIES:
                raise ValueError("unknown category")
        s[k] = v
    data.write_json_atomic(SETTINGS, s)
    return s


def check_name(t: str) -> str:
    """A yt-dlp output name template that stays inside the target folder."""
    if not t or len(t) > 160 or not re.fullmatch(r"[\w\s%().,\[\]\-#+&'!]+", t) or "%(ext)s" not in t or ".." in t:
        raise ValueError("name template: letters, spaces, yt-dlp fields like %(title)s - no folders - and it must "
                         "end with .%(ext)s")
    return t


# ------------------------------------------------------------------------------------------------- programs
def _which(*names: str) -> str | None:
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return None


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


def tools(full: bool = False) -> list[dict]:
    """Every outside program: found? where, version (full=True runs them once), what it is for / how to get it."""
    s = load()
    out = [{"name": "python", "label": "Python", "found": True, "path": sys.executable,
            "version": sys.version.split()[0], "need": "required", "how": "the lab's .venv"}]
    for n, label, need in (("ffmpeg", "ffmpeg", "required"), ("claude", "Claude Code", "recommended"),
                           ("git", "Git", "recommended"), ("yt-dlp", "yt-dlp", "optional"),
                           ("resolve", "DaVinci Resolve", "optional"),
                           ("edge", "Microsoft Edge", "required")):
        p = find(n, s)
        v = None
        if full and p:
            v = version(p, ("-version",) if n == "ffmpeg" else ("--version",)) if n not in ("resolve", "edge") else None
            if n == "ffmpeg" and v:
                v = v.replace("ffmpeg version ", "").split(" Copyright")[0]
        out.append({"name": n, "label": label, "found": bool(p), "path": p, "version": v, "need": need,
                    "how": HOW[n]})
    return out


# ------------------------------------------------------------------------------------------------- downloads
def download_cmd(url: str, preset: str) -> tuple[str, list[str]]:
    """(title, command) for the 'download' job: yt-dlp, one video (no playlists), into refs\\ (audio: refs\\audio\\);
    the final file path is printed last so the app can offer 'Analyse it'."""
    s = load()
    url = url.strip()
    if not re.fullmatch(r"https?://[^\s\"'<>|^`]{4,2000}", url):
        raise ValueError("paste a full link starting with https://")
    preset = preset or s["download_preset"]
    if preset not in PRESETS:
        raise ValueError(f"unknown preset {preset}")
    exe = find("yt-dlp", s)
    if not exe:
        raise ValueError("yt-dlp not found - " + HOW["yt-dlp"])
    label, args, folder = PRESETS[preset]
    out_dir = LAB / folder
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [exe, "--no-playlist", "--newline", "--progress", "--print", "after_move:filepath", "-P", str(out_dir),
           "-o", check_name(s["download_name"]), *args]
    ff = find("ffmpeg", s)
    if ff:
        cmd += ["--ffmpeg-location", str(Path(ff).parent)]
    host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
    return f"Download ({label.split(' (')[0]}) from {host}", cmd + ["--", url]


# ------------------------------------------------------------------------------------------------- Claude Code
def claude_launcher(prompt: str = "") -> tuple[str, str]:
    """(cleaned prompt, .cmd text) that opens Claude Code in the lab folder with an optional first message. The
    prompt loses the characters cmd would interpret (quotes, %, ^, &, |, <, >)."""
    exe = find("claude")
    if not exe:
        raise FileNotFoundError("Claude Code (claude) - " + HOW["claude"])
    clean = re.sub(r'["%^&|<>\r\n`]', " ", str(prompt))
    clean = re.sub(r" {2,}", " ", clean)[:600].strip()
    lines = ["@echo off", "title MotionLab - Claude Code", f'cd /d "{LAB}"',
             f'call "{exe}"' + (f' "{clean}"' if clean else "")]
    return clean, "\r\n".join(lines) + "\r\n"


def open_claude(prompt: str = "") -> dict:
    """Open Claude Code in a new console in the lab folder, optionally with a first message (the app's fixed
    hand-off texts: /analyze-reference ..., apply the feedback in ...)."""
    clean, text = claude_launcher(prompt)
    APPDIR.mkdir(exist_ok=True)
    launcher = APPDIR / "open_claude.cmd"
    launcher.write_text(text, encoding="utf-8")
    subprocess.Popen(["cmd", "/c", str(launcher)], cwd=str(LAB), creationflags=NEW_CONSOLE)
    return {"ok": True, "prompt": clean}


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
        raise RuntimeError(out.stderr.strip()[-300:] or "could not create the shortcut")
    return {"ok": True, "path": out.stdout.strip().splitlines()[-1] if out.stdout.strip() else ""}


def downloads() -> list[dict]:
    """Recently downloaded files (refs\\ and refs\\audio\\), newest first."""
    out = []
    for d in (REFS, REFS / "audio"):
        if d.is_dir():
            for p in d.iterdir():
                if p.is_file() and p.suffix.lower() in data.VIDEO_EXT | {".mp3", ".m4a", ".wav"}:
                    out.append({"name": p.name, "path": str(p), "rel": data.rel(p), "size": p.stat().st_size,
                                "modified": data.stamp(p.stat().st_mtime), "audio": d.name == "audio",
                                "t": p.stat().st_mtime})
    return sorted(out, key=lambda x: -x["t"])[:30]

