"""The app's local web server (Python standard library only).

Listens on 127.0.0.1 only and answers only requests addressed to it (Host check). Pages come from ui\\; lab files
are served read-only from /files/<lab-relative path> (analysis, projects, refs, docs, library) with byte ranges
so videos can seek; /api/ returns JSON. Every request that changes something (verdicts, picks, jobs) must carry the
session token embedded in the page, so other web pages cannot use the server. The only writes: the user's
verdicts / exported feedback (analysis\\<name>\\feedback\\), library picks (projects\\<name>\\build\\), and the app's
own .app\\ folder (logs, job logs, video thumbnails), settings.json (Settings page), downloads into refs\\
(yt-dlp, started from the Analyze page) and the prompt library (knowledge\\local\\prompts\\: added and rated in
Generate > Prompt library). Deleting = the user's Delete buttons only (trash.py): after a dialog
listing every item, references / downloads / video projects / renders go to the Windows Recycle Bin. Programs it
can start: Claude Code in a new console ("Open in Claude", or when a lab pass started with "Analyse with Claude"
ends), Explorer / the default viewer for lab files, and the shortcut maker - each only on a click."""
from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import traceback
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from motionlab import __version__
from motionlab import fonts as FL
from motionlab import i18n as I18N
from motionlab import knowledge as KN
from motionlab import logos as LGO
from motionlab import looks as LK
from motionlab import overlay_settings as OS
from motionlab import prompts as PR
from motionlab import publish as PB
from motionlab import script as SC
from motionlab import upstream as UP
from motionlab.styles import CATEGORIES
from motionlab.util import LAB, fix_dotted_names, tool

from . import data, jobs, live, player, report, system, trash, updater

VERSION = __version__                               # one version: tools/motionlab/__init__.py
API_LEVEL = 31                                     # app.js API_LEVEL: the functions the page needs
UI = Path(__file__).resolve().parent / "ui"
OV_GSAP = LAB / "tools" / "overlays" / "node_modules" / "gsap" / "dist" / "gsap.min.js"   # the motion templates' previews
APPDIR = LAB / ".app"
THUMBS = APPDIR / "thumbs"
FILE_ROOTS = {"analysis", "projects", "refs", "docs", "library", "knowledge", "fonts",      # fonts: 0.4.6, the library
              "logos"}                                                                     # the logo library (2026-10-16)
OPENABLE = {".html", ".md", ".txt", ".png", ".jpg", ".jpeg", ".mp4", ".mov", ".json", ".csv"}
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
for ext, typ in ((".js", "text/javascript"), (".css", "text/css"), (".md", "text/plain"), (".comp", "text/plain"),
                 (".mp4", "video/mp4"), (".json", "application/json"), (".csv", "text/plain"), (".py", "text/plain"),
                 (".ttf", "font/ttf"), (".otf", "font/otf")):
    mimetypes.add_type(typ, ext)


def log_error(msg: str) -> None:
    APPDIR.mkdir(exist_ok=True)
    with open(APPDIR / "server.log", "a", encoding="utf-8") as f:
        f.write(f"{data.stamp()} {msg}\n")


def _image_running(image: str) -> bool | None:
    """Is a process with this image name (e.g. "resolve.exe", any case) running? Windows' process list (a Toolhelp
    snapshot, ~5 ms); None = could not tell (not Windows, the call failed)."""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    class Entry(ctypes.Structure):                               # PROCESSENTRY32W
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wintypes.DWORD),
                    ("cntThreads", wintypes.DWORD), ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", wintypes.LONG), ("dwFlags", wintypes.DWORD),
                    ("szExeFile", wintypes.WCHAR * 260)]
    try:
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        k.CreateToolhelp32Snapshot.argtypes, k.CreateToolhelp32Snapshot.restype = [wintypes.DWORD, wintypes.DWORD], \
            wintypes.HANDLE
        for fn in (k.Process32FirstW, k.Process32NextW):
            fn.argtypes, fn.restype = [wintypes.HANDLE, ctypes.POINTER(Entry)], wintypes.BOOL
        k.CloseHandle.argtypes, k.CloseHandle.restype = [wintypes.HANDLE], wintypes.BOOL
        h = k.CreateToolhelp32Snapshot(0x2, 0)                   # TH32CS_SNAPPROCESS
        if not h or h == ctypes.c_void_p(-1).value:              # INVALID_HANDLE_VALUE
            return None
        try:
            e = Entry()
            e.dwSize = ctypes.sizeof(Entry)
            more = k.Process32FirstW(h, ctypes.byref(e))
            while more:
                if e.szExeFile.lower() == image.lower():
                    return True
                more = k.Process32NextW(h, ctypes.byref(e))
            return False if ctypes.get_last_error() == 18 else None      # 18 = ERROR_NO_MORE_FILES: the whole list
        finally:
            k.CloseHandle(h)
    except (OSError, AttributeError, ValueError):
        return None


def resolve_state() -> str:
    """'running' / 'not responding' / 'not running' (Windows' own flag; same as resolve_build.resolve_state). The
    watcher asks every 20 s: with no Resolve.exe in the process list (the usual case) the answer comes without
    starting PowerShell (~0.7 s of CPU each time) - Get-Process Resolve finds exactly the Resolve.exe processes."""
    if _image_running("resolve.exe") is False:
        return "not running"
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command",
                              "(Get-Process Resolve -ErrorAction SilentlyContinue | Select-Object -First 1).Responding"],
                             capture_output=True, text=True, timeout=20, creationflags=NO_WINDOW).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    return {"True": "running", "False": "not responding"}.get(out, "not running")


class State:
    def __init__(self, port: int, auto_exit: bool):
        self.token = secrets.token_urlsafe(24)
        self.port = port
        self.auto_exit = auto_exit
        self.started = time.time()
        self.last_ping: float | None = None
        self.bye: float | None = None
        self.runner = jobs.Runner()
        self.resolve = {"state": "checking", "checked": None}
        self.server = None
        self.phase = "ready"               # ready / updating / restarting (the window shows it and reloads after)
        self.check_updates = True          # False: app.py --no-update (test servers)
        self.update = updater.cached()
        self.update_result = updater.last_result()


S: State | None = None


def live_claude() -> list[dict]:
    """The heartbeat's 'Claude is working' line (0.4.4): read-only, only new log bytes - and never in the heartbeat's
    way (a log it cannot read = no line)."""
    try:
        return data.live_claude()
    except Exception:                                    # noqa: BLE001 - the heartbeat must answer
        return []


def status() -> dict:
    refs = data.list_references()
    projs = data.list_projects()
    lib = data.library(videos=False)                  # counts only (2026-10-19)
    du = shutil.disk_usage(str(LAB))
    verdicts = sum(r["verdicts"] for r in refs)
    nxt = []
    for r in refs:                                      # each reference's next step of the workflow (data.FLOW)
        fl, go, nm = r["flow"], f"#/ref/{urllib.parse.quote(r['name'])}", r.get("label") or r["title"]   # readable name
        if fl["next"] == "claude":
            nxt.append({"text": I18N.tn(fl["events"] - fl["reviewed"],
                                        "Send {name} to Claude: {n} effect(s) not checked yet (until then their names "
                                        "are the lab's guesses)",
                                        "Send {name} to Claude: {n} effect(s) not checked yet (until then their names "
                                        "are the lab's guesses)", name=nm), "go": go,
                        "claude": r["review_prompt"], "task": "review",
                        "label": r["title"]})
        elif fl["next"] == "verdicts":                  # the one review pattern (2026-10-18): "Is Claude right?"
            nxt.append({"text": I18N.t("Review {name} - is Claude right? {given} of {real} effects, {checked} of "
                                       "{misses} possible misses", name=nm, given=fl["given"], real=fl["real"],
                                       checked=fl["misses_checked"], misses=fl["misses"]) if fl["misses"] else
                        I18N.t("Review {name} - is Claude right? {given} of {real} effects", name=nm,
                               given=fl["given"], real=fl["real"]), "go": go})
        elif fl["next"] == "feedback":
            nxt.append({"text": I18N.t("Send your review of {name} to Claude (Send it to Claude): it turns your verdicts "
                                       "into lessons - sent, waiting for Claude", name=nm) if fl["sent"] else
                        I18N.t("Send your review of {name} to Claude (Send it to Claude): it turns your verdicts into "
                               "lessons", name=nm), "go": go})
    if projs and not lib["items"]:
        nxt.append({"text": I18N.t("Pick the effects to save in the library (Editor > your video > Resolve & library)"),
                    "go": f"#/project/{projs[0]['name']}/resolve"})
    progs = system.tools()                              # once: "claude" below is its row (audit 2026-10-19)
    setup = [t for t in progs if not t["found"] and t["need"] in ("required", "recommended")]
    if not refs:
        nxt.insert(0, {"text": I18N.t("Start here: analyse a video you like (Analyze > Download from a link) or drop "
                                      "one into the refs folder, then click Analyse a video"), "go": "#/analyze"})
    return {"version": VERSION, "lab": str(LAB), "references": len(refs), "events": sum(r["events"] for r in refs),
            "thumbs": set_count(data.thumb_sets), "texts": set_count(data.text_sets),    # 2026-10-18: Home's Analyser
            "reviewed": sum(r["reviewed"] for r in refs), "verdicts": verdicts, "projects": sum(1 for p in projs if not (p.get("generated") and not p.get("in_editor"))),
            "library": len(lib["items"]), "picks": len(lib["picks"]), "free_bytes": du.free, "total_bytes": du.total,
            "resolve": S.resolve, "jobs_running": [j.info() for j in S.runner.active()],
            "roadmap": "docs/roadmap.png" if (LAB / "docs" / "roadmap.png").exists() else None, "next": nxt,
            "roadmap_live": "docs/roadmap/index.html" if (LAB / "docs" / "roadmap" / "index.html").exists() else None,
            "projects_list": projs, "setup": setup,                 # no references_list: no page read it (2026-10-19)
            "claude": any(t["name"] == "claude" and t["found"] for t in progs), "update": S.update,
            "update_result": S.update_result,
            "author": KN.author(), "prompts": PR.count(), "scripts": PR.count(("script", "hook")),
            "lessons": KN.lesson_count()}


def set_count(sets) -> int:
    """How many thumbnails / scripts & prompts the Analyser's sets hold (Home's card); 0 when they cannot be read."""
    try:
        return sum(s.get("count") or 0 for s in sets())
    except Exception:                                    # noqa: BLE001 - Home must draw
        return 0


def storage_summary() -> dict:
    if str(LAB / "tools") not in sys.path:
        sys.path.insert(0, str(LAB / "tools"))
    import storage                                              # tools\storage.py (same rules as the CLI)
    files = storage.scan()
    units: dict[str, dict] = {}
    whats: dict[str, int] = {}
    for rel, size, cat, what in files:
        u = units.setdefault(storage.unit_of(rel), dict.fromkeys(storage.CATS, 0))
        u[cat] += size
        if cat in storage.PRUNABLE:
            whats[what] = whats.get(what, 0) + size
    du = shutil.disk_usage(str(LAB))
    return {"units": [{"name": k, **v, "total": sum(v.values())} for k, v in
                      sorted(units.items(), key=lambda kv: -sum(kv[1].values()))],
            "cats": list(storage.CATS), "prunable": list(storage.PRUNABLE),
            "freeable": [{"what": w, "bytes": b, "how": storage.HOW.get(w, "")} for w, b in
                         sorted(whats.items(), key=lambda kv: -kv[1])],
            "free_bytes": du.free, "total_bytes": du.total}


def thumb(video: Path, frame: int, fps: float) -> Path:
    """One frame of a lab video as a small JPEG (cached in .app\\thumbs\\)."""
    st = video.stat()
    key = hashlib.sha1(f"{video}|{st.st_mtime_ns}|{st.st_size}".encode()).hexdigest()[:12]
    out = THUMBS / f"{key}_{frame:06d}.jpg"
    if not out.exists():
        THUMBS.mkdir(parents=True, exist_ok=True)
        subprocess.run([tool("ffmpeg"), "-v", "error", "-y", "-ss", f"{(frame + 0.5) / fps:.4f}", "-i", str(video),
                        "-frames:v", "1", "-vf", "scale=480:-2", "-q:v", "4", str(out)],
                       capture_output=True, timeout=60, creationflags=NO_WINDOW)
        if not out.exists():
            raise FileNotFoundError(I18N.t("frame {frame} of {file}", frame=frame, file=video.name))
    return out


def photo_thumb(photo: Path) -> Path:
    """A photo as a small JPEG the right way up (cached in .app\\thumbs\\): Pillow + pillow-heif when the lab's
    packages are there (imported only here - the app itself needs none), else ffmpeg."""
    st = photo.stat()
    out = THUMBS / f"{hashlib.sha1(f'{photo}|{st.st_mtime_ns}|{st.st_size}'.encode()).hexdigest()[:12]}_photo.jpg"
    if not out.exists():
        THUMBS.mkdir(parents=True, exist_ok=True)
        try:
            from motionlab import photos as PH
            PH.thumbnail(photo, out)
        except Exception:                                 # noqa: BLE001 - no Pillow / a format it cannot read
            subprocess.run([tool("ffmpeg"), "-v", "error", "-y", "-i", str(photo), "-frames:v", "1", "-vf",
                            "scale=480:-2", "-q:v", "4", str(out)], capture_output=True, timeout=60,
                           creationflags=NO_WINDOW)
        if not out.exists():
            raise FileNotFoundError(I18N.t("frame {frame} of {file}", frame=0, file=photo.name))
    return out


def lab_file(relpath: str, roots=FILE_ROOTS) -> Path:
    p = (LAB / urllib.parse.unquote(relpath)).resolve()
    if LAB not in p.parents or p.relative_to(LAB).parts[0] not in roots:
        raise PermissionError(relpath)
    if not p.exists():
        raise FileNotFoundError(relpath)
    return p


class NoRoute(FileNotFoundError):
    """A route this server does not have: its 404 stays "not found: <path>" in every language - a newer page tells an
    older server by it (app.js tests /not found|404/)."""


class Handler(BaseHTTPRequestHandler):
    server_version = f"MotionLab/{VERSION}"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):                       # quiet: errors go to .app\server.log
        pass

    # ------------------------------------------------------------------------------------------ helpers
    def _host_ok(self) -> bool:
        return self.headers.get("Host", "") in (f"127.0.0.1:{S.port}", f"localhost:{S.port}")

    def _send(self, code: int, body: bytes, ctype: str, headers: dict | None = None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, obj, code: int = 200):
        self._send(code, json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"),
                   "application/json; charset=utf-8")

    def _err(self, code: int, msg: str):
        self._json({"error": msg}, code)

    def _body(self, limit: int = 5_000_000) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if n > limit:
            raise ValueError(I18N.t("request too large"))
        raw = self.rfile.read(n) if n else b""
        obj = json.loads(raw.decode("utf-8") or "{}")
        if not isinstance(obj, dict):
            raise ValueError(I18N.t("expected a JSON object"))
        return obj

    def _file(self, p: Path):
        if not p.is_file():
            raise FileNotFoundError(p.name)
        st = p.stat()
        etag = f'"{st.st_mtime_ns:x}-{st.st_size:x}"'
        ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype == "application/json":
            ctype += "; charset=utf-8"
        if self.headers.get("If-None-Match") == etag and not self.headers.get("Range"):
            self.send_response(304)
            self.send_header("ETag", etag)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        size, start, end = st.st_size, 0, st.st_size - 1
        m = re.fullmatch(r"bytes=(\d*)-(\d*)", (self.headers.get("Range") or "").strip())
        partial = bool(m and (m.group(1) or m.group(2)))
        if partial:
            if m.group(1):
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else size - 1
            else:
                start = max(0, size - int(m.group(2)))
            end = min(end, size - 1)
            if start > end:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
        self.send_response(206 if partial else 200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("ETag", etag)
        self.send_header("Cache-Control", "no-cache")
        if partial:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        if self.command == "HEAD":
            return
        with open(p, "rb") as f:
            f.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = f.read(min(1 << 20, left))
                if not chunk:
                    break
                self.wfile.write(chunk)
                left -= len(chunk)

    def _index(self):
        # Settings > Language (2026-10-18): <html lang>, index.html's {{t:...}} texts and the page's words, inlined
        # before app.js so its label tables are translated as they load (English: {} - the page as before)
        lg = I18N.lang()
        html = (UI / "index.html").read_text(encoding="utf-8").replace("{{TOKEN}}", S.token) \
            .replace("{{VERSION}}", VERSION).replace("{{LANG}}", lg)
        html = I18N.fill_html(html, lg).replace("{{I18N}}", I18N.page_script(lg))
        self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")

    def _guard(self, fn):
        try:
            fn()
        except jobs.JobError as e:
            self._err(409, str(e))
        except NoRoute as e:
            self._err(404, "not found: " + str(e))
        except FileNotFoundError as e:
            self._err(404, I18N.t("not found: {what}", what=e))
        except PermissionError as e:
            self._err(403, I18N.t("not allowed: {what}", what=e))
        except RuntimeError as e:
            self._err(500, str(e))
        except (ValueError, KeyError, TypeError) as e:
            self._err(400, str(e))
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass
        except Exception:                                       # noqa: BLE001 - report, keep serving
            log_error(f"{self.command} {self.path}\n{traceback.format_exc()}")
            try:
                self._err(500, I18N.t("internal error (details in .app\\server.log)"))
            except OSError:
                pass

    # ------------------------------------------------------------------------------------------ GET
    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        if not self._host_ok():
            return self._err(403, "wrong host")
        self._guard(self._get)

    def _get(self):
        u = urllib.parse.urlsplit(self.path)
        path, q = u.path, urllib.parse.parse_qs(u.query)
        arg = lambda k, d=None: q.get(k, [d])[0]                       # noqa: E731
        if path in ("/", "/index.html"):
            return self._index()
        if path.startswith("/ui/"):
            p = (UI / urllib.parse.unquote(path[4:])).resolve()
            if UI not in p.parents:
                raise PermissionError(path)
            return self._file(p)
        if path.startswith("/files/"):
            rp = path[len("/files/"):]
            if urllib.parse.unquote(rp).endswith("/assets/logos/logos.js"):         # a graphic's logos (logos.py): the
                p = (LAB / urllib.parse.unquote(rp)).resolve()                      # file once a render wrote it, else
                if LAB not in p.parents or not (p.relative_to(LAB).parts[0] in FILE_ROOTS    # the helper alone (the
                                                or OS.MOTION.resolve() in p.parents):          # preview adds /logos.js)
                    raise PermissionError(rp)
                if p.is_file():
                    return self._file(p)
                return self._send(200, LGO.js([]).encode("utf-8"), "text/javascript; charset=utf-8")
            if urllib.parse.unquote(rp).endswith(("/assets/looks/look.css", "/assets/looks/looks.js")):  # 2026-10-25:
                p = (LAB / urllib.parse.unquote(rp)).resolve()                      # a look-aware graphic's shared files:
                if LAB not in p.parents or not (p.relative_to(LAB).parts[0] in FILE_ROOTS    # the file once a render
                                                or OS.MOTION.resolve() in p.parents):          # wrote it, else the
                    raise PermissionError(rp)                                                 # look system's own
                if p.is_file():
                    return self._file(p)
                css = p.name == "look.css"
                return self._send(200, (LK.css() if css else LK.js()).encode("utf-8"),
                                  ("text/css" if css else "text/javascript") + "; charset=utf-8")
            if urllib.parse.unquote(rp).startswith("tools/overlays/examples/"):    # the examples' thumbnails only
                p = lab_file(rp, {"tools"})
                if OS.EXAMPLES.resolve() not in p.parents or p.suffix.lower() != ".png":
                    raise PermissionError(rp)
                return self._file(p)
            if urllib.parse.unquote(rp).startswith("tools/overlays/motion/"):      # 0.5.0: a motion template's files
                parts = urllib.parse.unquote(rp).split("/")                         # for its picture + live preview
                if len(parts) == 5 and parts[4] == "gsap.min.js":                   # the pinned GSAP (not in the repo)
                    return self._file(OV_GSAP)
                p = lab_file(rp, {"tools"})
                if OS.MOTION.resolve() not in p.parents or p.suffix.lower() not in (".png", ".html", ".json", ".js",
                                                                                     ".css", ".svg", ".jpg"):
                    raise PermissionError(rp)
                return self._file(p)
            if re.fullmatch(r"\.app/player/[0-9a-f]{16}\.mp4", urllib.parse.unquote(rp)):    # player copies only
                return self._file(player.PLAYER / Path(urllib.parse.unquote(rp)).name)
            return self._file(lab_file(rp))
        if path == "/api/ping":
            S.last_ping = time.time()
            u = S.update or {}
            return self._json({"app": "motionlab", "version": VERSION, "running": len(S.runner.active()),
                               "resolve": S.resolve, "phase": S.phase, "api": API_LEVEL,
                               "update": bool(u.get("can_update")), "update_kind": u.get("kind"),
                               "update_version": u.get("new_version"), "update_cards": u.get("new_cards", 0),
                               "update_lessons": u.get("new_lessons", 0), "update_checked": u.get("checked"),
                               "update_testing": u.get("testing", 0), "update_error": u.get("error"),
                               "claude": live_claude()})              # 0.4.4: Claude windows at work, one line
        if path == "/api/status":                         # + Home's "· 7 from friends" (2026-10-18)
            return self._json({**status(), "friends": KN.friend_counts()})
        if path == "/api/fonts":                         # 0.4.6: the font library - the font settings' lists + previews
            return self._json({"families": [{"family": f["family"], "group": f["group"], "licence": f["licence"],
                                             "own": f["own"]} for f in FL.families()], "windows": list(FL.SYSTEM)})
        if path == "/fonts.css":                         # the same library as @font-face, for the previews
            css = FL.css(FL.families(), base=lambda f: "/files/library/fonts/" if f["own"] else "/files/fonts/")
            return self._send(200, css.replace("font-display:block", "font-display:swap").encode("utf-8"),
                              "text/css; charset=utf-8")
        if path == "/api/logos":                         # the logo library (logos.py): the pickers + Motion > Logos
            cat = LGO.catalog()
            return self._json({"groups": cat.get("groups", {}), "logos": [
                {k: lg[k] for k in ("id", "name", "group", "words", "default")}
                | {"variants": {v: {k: i[k] for k in ("aspect", "on", "tint")} for v, i in lg["variants"].items()}}
                for lg in cat["logos"]]})
        if path == "/logos.js":                          # a live preview's logos: ?b=youtube,figma -> MLLogo + those
            return self._send(200, LGO.js([x for x in (arg("b", "") or "").split(",")[:200] if x]).encode("utf-8"),
                              "text/javascript; charset=utf-8")
        if path == "/api/references":
            return self._json(data.list_references(arg("tests") == "1"))
        if path == "/api/candidates":
            return self._json(data.candidate_videos())
        if path == "/api/waiting":
            return self._json(data.waiting())
        if path == "/api/delete":                        # what a Delete button would move to the Recycle Bin
            return self._json(trash.plan(arg("kind", ""), arg("name", ""), S.resolve.get("state", "")))
        if path == "/api/projects":
            return self._json(data.list_projects())
        if path == "/api/edit/options":                  # New edit (0.4): presets, how many videos a style mixes
            return self._json(data.edit_options())
        if path == "/api/motion":                        # 0.5.0: the Motion Graphics library + the captured clips
            return self._json(data.motion())
        if path == "/api/motion/pick":                   # the templates that fit Generate's words
            return self._json({"picks": data.motion_pick(arg("want", ""), int(arg("n", "6") or 6))})
        if path == "/api/generate/options":              # Generate (0.4): AI tools, downloaded songs, HyperFrames
            return self._json(data.generate_options())
        if path == "/api/library":
            return self._json(data.library())
        if path == "/api/storage":
            return self._json(storage_summary())
        if path == "/api/jobs":
            return self._json(S.runner.list())
        if path == "/api/settings":
            return self._json({"settings": system.load(), "tools": system.tools(full=True), "lab": str(LAB),
                               "version": VERSION, "presets": [{"id": k, "label": v[0], "folder": v[2]}
                                                               for k, v in system.PRESETS.items()],
                               "categories": [{"id": k, "label": v} for k, v in CATEGORIES.items()],
                               "styles": [{"id": k, "label": v} for k, v in CATEGORIES.items()],
                               "efforts": list(system.EFFORTS), "models": list(system.MODELS), "upstream": UP.state(),
                               "tasks": {k: v[0] for k, v in system.TASKS.items()},
                               "resolve_mcp": system.resolve_mcp_state(),
                               "ytdlp": system.ytdlp_info(), "deno": system.deno_info(),       # 0.4.2.1
                               "browsers": [{"id": k, "label": v} for k, v in system.BROWSERS.items()],
                               "languages": [{"id": k, "label": I18N.NAMES[k]} for k in system.LANGUAGES],
                               # Connect to GitHub (2026-10-18): pre-filled; git / repo found now - a ZIP copy is
                               # never checked at start-up, so the cached check may not exist yet
                               "home_repo": updater.HOME_REPO,
                               "update": {**(S.update or {}), "git": bool(updater.git_exe()),
                                          "repo": updater.is_repo(), "phase": S.phase,
                                          "kept": updater.kept_list()}})        # 2026-10-24: changes an update replaced
        if path == "/api/player":                         # the player: the file's codec + its player copy (0.4.2.1)
            v = lab_file(arg("path", ""))
            if v.suffix.lower() not in data.VIDEO_EXT:
                raise PermissionError(v.name)
            return self._json({**player.info(v), "job": player_job(data.rel(v))})
        if path == "/api/report":                         # Report a problem: the scrubbed report, before anything
            return self._json(problem_report(arg("job"), ""))
        if path == "/api/downloads":
            return self._json(system.downloads())
        if path == "/api/update":
            return self._json({**(S.update or {}), "version": VERSION, "phase": S.phase, "result": S.update_result})
        if path == "/api/skills":                         # Tools > Skills: the project's Claude Code commands
            return self._json(data.skills())
        if path == "/api/memory":                         # Claude's memory (0.4): videos, effects, lessons, saved
            return self._json(data.memory())
        if path == "/api/changes":                       # 2026-10-24: a list page redraws itself when this changes
            return self._json(live.changes(arg("s", "")))
        if path == "/api/seen":                          # 2026-10-24: the NEW badge - what each section has seen
            return self._json(live.seen())
        if path == "/api/thumbtest":                     # 2026-10-24: Preview your thumbnail - the feed around yours
            return self._json(data.thumb_test())
        m = re.fullmatch(r"/api/thumbfeed/([\w\-]{6,20})\.jpg", path)     # its big channels' pictures (.app\thumbfeed)
        if m:
            from motionlab import thumbfeed as TF
            p = TF.IMG / f"{m[1]}.jpg"
            if not p.is_file():
                raise FileNotFoundError(path)
            return self._file(p)
        if path == "/api/styles":                         # 2026-10-18: every "In the style of" picker - this PC's
            return self._json(data.style_choices())      # analysed videos + the scripts and hooks, never friends'
        if path == "/api/knowledge":                      # Claude's memory > Shared knowledge
            return self._json(data.knowledge_overview())
        if path == "/api/knowledge/card":
            return self._json(KN.card_detail(arg("id", "")))
        if path == "/api/prompts":
            ov = PR.overview()
            return self._json({**ov, "used": data.prompt_uses(), **data.prompt_styles(ov["items"]),
                               "took": data.prompt_took(ov["items"])})
        if path == "/api/script/cards":                  # Film it (2026-10-15): a script / hook as cue cards
            pid = arg("id", "")
            if not re.fullmatch(r"(script|hook)-\d{3,}", pid):
                raise ValueError(I18N.t("not a script: {id}", id=repr(pid)))
            return self._json({"parts": SC.cue_cards(PR.get(pid).get("text", ""))})
        if path == "/api/script/requests":               # Prepare (0.4.x): what the two dialogs asked Claude for
            return self._json({"items": SC.requests(), "where": SC.WHERE, "tones": SC.TONES, "ctas": SC.CTAS,
                               "langs": SC.LANGS, "platforms": SC.PLATFORMS,
                               "orientations": SC.ORIENTATIONS})
        if path == "/api/text":
            text, lg = data.text_file(arg("path", "")), I18N.lang()
            if lg != "en" and arg("path", "").replace("\\", "/").strip("/").lower() == "changelog.md":
                text = updater.translated(text, updater.local_changelog(lg))      # What's new: CHANGELOG.es.md's words
            return self._json({"path": arg("path"), "text": text})
        if path == "/api/thumb":
            v = lab_file(arg("video", ""))
            if v.suffix.lower() in data.PHOTO_EXT:          # 2026-10-24: a photo of a video's clips (HEIC included)
                return self._file(photo_thumb(v))
            if v.suffix.lower() not in data.VIDEO_EXT:
                raise PermissionError(v.name)
            return self._file(thumb(v, int(arg("f", "0")), float(arg("fps", "25"))))
        m = re.fullmatch(r"/api/reference/([^/]+)", path)
        if m:
            return self._json(data.reference(urllib.parse.unquote(m[1])))
        m = re.fullmatch(r"/api/feedback/([^/]+)", path)
        if m:
            return self._json({"text": data.feedback_text(urllib.parse.unquote(m[1]))})
        m = re.fullmatch(r"/api/project/([^/]+)", path)
        if m:
            return self._json(data.project(urllib.parse.unquote(m[1])))
        m = re.fullmatch(r"/api/project/([^/]+)/publish", path)        # Edit > a video > Publish (0.4.3)
        if m:
            return self._json(data.publish_info(urllib.parse.unquote(m[1])))
        m = re.fullmatch(r"/api/took/(project|analysis|prompt)/([^/]+)", path)   # What it took (0.4.4)
        if m:
            return self._json(data.took(m[1], urllib.parse.unquote(m[2])))
        if path == "/api/estimate":                      # 0.4.5: Claude's usual minutes per video on this PC
            return self._json(data.estimate())
        if path == "/api/thumbs":                        # 0.4.5: the thumbnail sets (Analyser)
            return self._json(data.thumb_sets())
        m = re.fullmatch(r"/api/thumbs/([^/]+)", path)
        if m:
            return self._json(data.thumb_set(urllib.parse.unquote(m[1])))
        if path == "/api/texts":                         # 2026-10-18: the sets of scripts & prompts (Analyser)
            return self._json(data.text_sets())
        m = re.fullmatch(r"/api/texts/([^/]+)", path)
        if m:
            return self._json(data.text_set(urllib.parse.unquote(m[1])))
        if path == "/api/batches":                       # 0.4.5: batches with videos left (Continue the batch)
            kind = arg("kind")
            if kind not in (None, "review", "recreate"):
                raise ValueError(I18N.t("unknown batch kind {kind}", kind=repr(kind)))
            return self._json(data.batches(kind))
        m = re.fullmatch(r"/api/project/([^/]+)/chapters", path)       # Publish: chapter points (plan / its words)
        if m:
            data.publish_dir(urllib.parse.unquote(m[1]))
            src = arg("from", "plan")
            if src not in ("plan", "transcript"):
                raise ValueError(I18N.t("chapters from the edit (plan) or from the words (transcript)"))
            try:
                return self._json(PB.chapter_points(data.safe_name(urllib.parse.unquote(m[1])), src))
            except ValueError:                            # the tool's words name files: the page says it plainly
                raise ValueError(I18N.t("no edit of this video yet - make one first") if src == "plan" else
                                 I18N.t("MotionLab has not heard this video's words yet - make captions from the "
                                        "finished video first (Graphics > Captions), then try again")) from None
        m = re.fullmatch(r"/api/jobs/(\d+)", path)
        if m:
            job = S.runner.jobs.get(int(m[1]))
            if not job:
                raise FileNotFoundError(I18N.t("job {id}", id=m[1]))
            return self._json(job.info(int(arg("since", "0"))))
        raise NoRoute(path)

    # ------------------------------------------------------------------------------------------ POST
    def do_POST(self):
        if not self._host_ok():
            return self._err(403, "wrong host")
        self._guard(self._post)

    def _post(self):
        path = urllib.parse.urlsplit(self.path).path
        m = re.fullmatch(r"/api/thumbs/([^/]+)/upload", path)
        if m:                                     # 0.4.5: a picture for a thumbnail set - a raw body (<= 25 MB)
            if not secrets.compare_digest(str(self.headers.get("X-ML-Token") or ""), S.token):
                raise PermissionError(I18N.t("missing or wrong session token"))
            q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            return self._json(data.thumb_upload(urllib.parse.unquote(m[1]), (q.get("name") or [""])[0], self.rfile,
                                                int(self.headers.get("Content-Length") or 0)))
        m = re.fullmatch(r"/api/project/([^/]+)/upload", path)
        if m:                                     # Film it (2026-10-15): a recording copied in - a raw body, streamed
            if not secrets.compare_digest(str(self.headers.get("X-ML-Token") or ""), S.token):
                raise PermissionError(I18N.t("missing or wrong session token"))
            q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            prompt = (q.get("prompt") or [""])[0]
            if prompt and not re.fullmatch(r"(script|hook|brief)-\d{3,}", prompt):
                raise ValueError(I18N.t("not a script: {id}", id=repr(prompt)))
            return self._json(data.save_upload(urllib.parse.unquote(m[1]), (q.get("name") or [""])[0], self.rfile,
                                               int(self.headers.get("Content-Length") or 0), prompt))
        body = self._body(45_000_000 if path in ("/api/prompts/file", "/api/prompts/example")
                          or path.endswith("/publish/image") else 5_000_000)   # a file = base64 (+1/3)
        tok = self.headers.get("X-ML-Token") or body.get("token") or ""
        if not secrets.compare_digest(str(tok), S.token):
            raise PermissionError(I18N.t("missing or wrong session token"))
        if path == "/api/bye":
            S.bye = time.time()
            return self._json({"ok": True})
        m = re.fullmatch(r"/api/reference/([^/]+)/(verdicts|export)", path)
        if m:
            name = urllib.parse.unquote(m[1])
            if m[2] == "verdicts":
                return self._json(data.save_verdicts(name, body, by_user=True))
            return self._json(data.export_feedback(name))
        m = re.fullmatch(r"/api/project/([^/]+)/picks", path)
        if m:
            return self._json(data.save_library_picks(urllib.parse.unquote(m[1]), body))
        if path == "/api/script/tidy":                   # Improve my script: the paste replaced by its new version
            try:                                          # (Prepare / Prompts call it before they load)
                return self._json({"moved": data.tidy_improved()})
            except Exception as e:                        # noqa: BLE001 - never at the cost of the page
                log_error(f"tidy_improved: {e!r}")
                return self._json({"moved": []})
        if path == "/api/thumbfeed/channels":            # Preview your thumbnail: the channels its feed is made of
            from motionlab import thumbfeed as TF
            try:
                return self._json({"channels": TF.set_channels([str(x) for x in body.get("channels") or []])})
            except ValueError as e:
                raise ValueError(I18N.t("not a YouTube channel: {line}", line=str(e).split(": ", 1)[-1])) from None
        if path == "/api/seen":                          # the NEW badge: a section left, or a card clicked
            return self._json(live.mark(str(body.get("section", "")), bool(body.get("leave")),
                                        str(body.get("key", ""))))
        if path == "/api/projects/new":                   # Videos > Create video: an empty folder for the clips
            return self._json(data.new_project(str(body.get("name", ""))))
        if path == "/api/script/check":                   # Prepare: the script check while you type (no Claude)
            like = [str(x)[:160] for x in body.get("like") or [] if isinstance(x, str)][:3]
            ln = body.get("length_s")
            return self._json(SC.check(str(body.get("text", ""))[:200_000], float(ln) if ln not in (None, "") else None,
                                       like))
        if path == "/api/script/improve":                 # Prepare > Improve my script: saved + what you want
            r = SC.save_improve(body)
            return self._json({**r, "command": f"/write-script improve {r['script']['id']}"})
        if path == "/api/script/request":                 # Prepare > Write one from zero: the answers
            r = SC.save_new(body)
            return self._json({"request": r, "command": f"/write-script request {r['id']}"})
        if path == "/api/title/request":                  # Prepare > Title & thumbnail first (0.4.3): the answers
            r = SC.save_title(body)
            return self._json({"request": r, "command": f"/write-title request {r['id']}"})
        if path == "/api/prompts/request":                # 2026-10-19: Generate a new prompt / Use it, change... - the
            r = SC.save_prompt(body)                      # user's words reach Claude whole, in a file (never through cmd)
            return self._json({"request": r, "command": f"/write-prompt request {r['id']}"})
        if path == "/api/prompts/title":                  # a title record: Use this title -> a video (+ its final title)
            pid = str(body.get("id", ""))
            if not re.fullmatch(r"title-\d{3,}", pid):
                raise ValueError(I18N.t("not a title record: {id}", id=repr(pid)))
            proj = str(body.get("project") or "")
            if proj:
                data.publish_dir(proj)                    # the video must exist (FileNotFoundError)
            ch = " ".join(str(body.get("chosen") or "").split())
            if len(ch) > PR.TITLE_MAX:
                raise ValueError(I18N.t("a title has at most {n} characters", n=PR.TITLE_MAX))
            return self._json(PR.update(pid, project=data.safe_name(proj) if proj else "",
                                        **({"chosen": ch} if "chosen" in body else {})))
        m = re.fullmatch(r"/api/project/([^/]+)/publish", path)         # Publish: title, description, chapters, tags
        if m:
            return self._json(data.save_publish(urllib.parse.unquote(m[1]), body))
        m = re.fullmatch(r"/api/project/([^/]+)/thumb", path)           # Publish: a thumbnail's settings (form)
        if m:
            return self._json(data.save_thumb_values(urllib.parse.unquote(m[1]), str(body.get("id", "")),
                                                     body.get("values")))
        m = re.fullmatch(r"/api/project/([^/]+)/publish/image", path)   # Publish: a picture you made (AI image)
        if m:
            try:
                raw = base64.b64decode(str(body.get("data", "")), validate=True)
            except ValueError:
                raise ValueError(I18N.t("the picture did not arrive whole - add it again")) from None
            return self._json(data.save_publish_image(urllib.parse.unquote(m[1]), str(body.get("name", "")), raw))
        if path == "/api/script/forget":                  # a request nobody wants any more (Recycle Bin, logged)
            rid = str(body.get("id", ""))
            r = trash.recycle([SC.request_path(rid)])
            with open(APPDIR / "deleted.log", "a", encoding="utf-8") as f:
                f.write(f"{data.stamp()} script request {rid} moved to the Recycle Bin: {r['moved']}\n")
            if r["left"]:
                raise ValueError(r.get("why_shown") or I18N.t("the request could not be moved to the Recycle Bin"))
            return self._json({"forgotten": rid})
        if path == "/api/generate/request":              # Generate (0.4): a video from zero -> its folder + request
            return self._json(data.save_generate_request(body))
        m = re.fullmatch(r"/api/project/([^/]+)/edit_request", path)       # New edit (0.4): what the user picked
        if m:
            return self._json(data.save_edit_request(urllib.parse.unquote(m[1]), body))
        m = re.fullmatch(r"/api/project/([^/]+)/rename", path)   # the name the app shows (the folder keeps its own)
        if m:
            return self._json(data.rename_project(urllib.parse.unquote(m[1]), str(body.get("label", ""))))
        m = re.fullmatch(r"/api/project/([^/]+)/move", path)     # 0.4.3.5: a video from zero -> the Editor (or back)
        if m:
            return self._json(data.move_project(urllib.parse.unquote(m[1]), bool(body.get("editor"))))
        # how it turned out (0.4.2 also: "next" fix / start_over, "moment" / "remove_moment" = notes on moments of a
        # render) / what it is made from
        m = re.fullmatch(r"/api/project/([^/]+)/(outcome|made_from)", path)
        if m:
            name = urllib.parse.unquote(m[1])
            if m[2] == "outcome":
                return self._json(data.save_outcome(name, body))
            return self._json({"made_from": data.add_made_from(name, str(body.get("kind", "")), str(body.get("id", "")))})
        m = re.fullmatch(r"/api/project/([^/]+)/overlay", path)            # Videos > Graphics: Save settings
        if m:
            return self._json(data.save_overlay_values(urllib.parse.unquote(m[1]), str(body.get("overlay", "")),
                                                       body.get("values"), str(body.get("preset") or "")))
        if path == "/api/jobs":                          # queue: true = wait its turn (0.4.1: the quick draft)
            return self._json(S.runner.start(str(body.get("kind", "")), body.get("args") or {},
                                             queue=bool(body.get("queue"))).info(0))
        if path == "/api/analyze/batch":                # Analyze > Add videos (0.4): links + files, one focus
            return self._json(analyze_batch(body))
        if path == "/api/edit/batch":                   # 0.4.5: several videos edited the same way
            return self._json(edit_batch(body))
        if path == "/api/batches/forget":               # 0.4.5: a batch row's ✕ (the videos stay as they are)
            return self._json(data.forget_batch(str(body.get("id", ""))))
        m = re.fullmatch(r"/api/thumbs/([^/]+)/(verdicts|remove)", path)   # 0.4.5: a thumbnail set
        if m:
            name = urllib.parse.unquote(m[1])
            if m[2] == "verdicts":
                return self._json(data.save_thumb_verdicts(name, body.get("patterns") or {}))
            return self._json(data.thumb_remove(name, int(body.get("n") or 0)))
        if path == "/api/texts/split":                   # 2026-10-18: Add scripts & prompts - the numbered preview
            return self._json(data.text_split(body))
        if path == "/api/texts/new":                     # ... saved word for word, numbered, measured (no Claude yet)
            return self._json(data.text_new(body))
        m = re.fullmatch(r"/api/texts/([^/]+)/(add|verdicts|remove|kind)", path)   # one set of scripts & prompts
        if m:
            name = urllib.parse.unquote(m[1])
            if m[2] == "add":
                return self._json(data.text_add(name, body))
            if m[2] == "verdicts":
                return self._json(data.save_text_verdicts(name, body.get("patterns") or {}))
            if m[2] == "remove":
                return self._json(data.text_remove(name, int(body.get("n") or 0)))
            return self._json(data.text_kind(name, int(body.get("n") or 0), str(body.get("kind") or "")))
        m = re.fullmatch(r"/api/jobs/(\d+)/cancel", path)
        if m:
            return self._json(S.runner.cancel(int(m[1])).info())
        if path == "/api/settings":
            lg = I18N.lang()
            saved = system.save(body.get("settings") or {})
            if I18N.lang() != lg:                        # Settings > Language: the update notes follow it too
                S.update, S.update_result = updater.in_language(S.update), updater.in_language(S.update_result)
            return self._json({"settings": saved})
        if path == "/api/quit":
            if S.runner.active() and not body.get("force"):
                raise jobs.JobError(I18N.t("a job is still running"))
            threading.Timer(0.4, S.server.shutdown).start()
            return self._json({"ok": True})
        if path == "/api/restart":
            if S.runner.active():
                raise jobs.JobError(I18N.t("wait until the running jobs finish"))
            restart_soon()
            return self._json({"ok": True, "phase": S.phase})
        if path == "/api/update/check":
            S.update = updater.check(fetch=True)
            return self._json(S.update)
        if path == "/api/update/apply":
            return self._json(apply_update())
        if path == "/api/update/seen":                   # the window showed "What's new" after an update
            updater.mark_seen()
            if S.update_result:
                S.update_result["seen"] = True
            return self._json({"ok": True})
        if path == "/api/update/restore":                # 2026-10-24: bring back the user's changes an update replaced
            if S.runner.active():
                raise ValueError(I18N.t("A job is running - try again when it has finished (Jobs)."))
            r = updater.restore_kept(str(body.get("name", "")))
            if r["restored"]:
                updater.mark_kept_restored()
                S.update_result = updater.last_result()
            return self._json({**r, "restart": any(not f.startswith(("knowledge/", "docs/")) for f in r["files"])})
        if path == "/api/update/connect":
            r = updater.connect(str(body.get("url", "")))
            S.update = updater.check(fetch=False)
            return self._json(r)
        if path == "/api/knowledge/share":
            return self._json(share_knowledge())
        if path == "/api/knowledge/private":              # 2026-10-18: a tick on Shared knowledge (kept on this PC)
            ids = [str(x)[:40] for x in body.get("ids") or [] if isinstance(x, str)]
            KN.set_private(str(body.get("kind", "")), ids, bool(body.get("private")))
            return self._json(data.knowledge_overview())
        if path == "/api/knowledge/import":
            name = Path(str(body.get("file", ""))).name
            r = KN.import_pack(KN.INBOX / name)
            return self._json(r)
        if path == "/api/knowledge/summary":
            KN.summary()
            return self._json({"ok": True, "summary": str(KN.SUMMARY.relative_to(LAB))})
        m = re.fullmatch(r"/api/reference/([^/]+)/meta", path)
        if m:
            name = data.safe_name(urllib.parse.unquote(m[1]))
            r = KN.save_meta(name, **{k: body[k] for k in ("category", "tags", "label") if k in body})
            KN.build_local_cards([name])
            return self._json(r)
        if path == "/api/upstream/check":                 # Settings > Programs: newer HyperFrames / GSAP now
            return self._json(UP.check(force=True))
        if path == "/api/prompts/import":                 # the prompt library's Add dialog: any text (0.3.3)
            src = body.get("source") if isinstance(body.get("source"), dict) else None
            if src:
                src = {k: str(src.get(k) or "").strip()[:500] for k in ("type", "creator", "link")
                       if src.get(k) or k == "type" or src.get("type") == "creator"}
            tags = [str(x)[:40] for x in body.get("tags") or [] if isinstance(x, str)]
            return self._json({"saved": PR.import_paste(str(body.get("text", "")), str(body.get("kind") or ""), src,
                                                         str(body.get("file") or "")[:200], tags)})
        if path == "/api/prompts/tags":                   # a card's "for": what the prompt is for (vlog, SFX, ...)
            tags = [str(x).strip().lower()[:40] for x in body.get("tags") or [] if isinstance(x, str) and x.strip()]
            return self._json(PR.update(str(body.get("id", "")), tags=tags[:12]))
        if path == "/api/prompts/wishes":                 # Claude's check: what the user wants per item (then Optimize)
            w = body.get("wishes") if isinstance(body.get("wishes"), dict) else {}
            w = {str(k)[:40]: str(v).strip()[:1000] for k, v in list(w.items())[:30] if str(v).strip()}
            # 2026-10-18 (one review pattern): the user's verdict on Claude's check of each part - correct / partly /
            # wrong (the record's "verdicts"); a body without it keeps the saved ones
            vd = body.get("verdicts") if isinstance(body.get("verdicts"), dict) else None
            if vd is not None:
                vd = {str(k)[:40]: str(v) for k, v in list(vd.items())[:30] if str(v) in ("correct", "partly", "wrong")}
            return self._json(PR.update(str(body.get("id", "")), wishes=w, verdicts=vd))
        if path == "/api/prompts/style":                  # a card's Style like: analysed references (0.3.5)
            refs = [str(x)[:200] for x in body.get("refs") or [] if isinstance(x, str)]
            return self._json(PR.set_style(str(body.get("id", "")), refs[:5]))
        if path == "/api/prompts/example":                # the pop-up's "What it makes": add / remove a picture or clip
            pid = str(body.get("id", ""))
            if body.get("remove"):
                r, f = PR.remove_example(pid, str(body["remove"]))
                if f:
                    t = trash.recycle([f])
                    with open(APPDIR / "deleted.log", "a", encoding="utf-8") as lf:
                        lf.write(f"{data.stamp()} prompt {pid} example moved to the Recycle Bin: {t['moved']}\n")
                return self._json(r)
            try:
                raw = base64.b64decode(str(body.get("data", "")), validate=True)
            except ValueError:
                raise ValueError(I18N.t("the file did not arrive whole - add it again")) from None
            if len(raw) > 30_000_000:
                raise ValueError(I18N.t("pictures and clips up to 30 MB"))
            return self._json(PR.add_example(pid, str(body.get("name", "")), raw))
        if path == "/api/prompts/rename":                 # 0.4.3.5: Prepare's cards - the name shown (empty = automatic)
            name = " ".join(re.sub(r"[\x00-\x1f\x7f]", " ", str(body.get("title") or "")).split())[:120]
            r = PR.update(str(body.get("id", "")), title=name)
            return self._json({"id": r["id"], "title": r.get("title")})
        if path == "/api/prompts/kind":                   # a card's kind, changed by the user (a new id of that kind)
            return self._json(PR.set_kind(str(body.get("id", "")), str(body.get("kind", ""))))
        if path == "/api/prompts/delete":                 # a card's Delete (the user's click, after a confirm)
            pid = str(body.get("id", ""))
            r = trash.recycle([PR.path_of(pid)])
            with open(APPDIR / "deleted.log", "a", encoding="utf-8") as f:
                f.write(f"{data.stamp()} prompt {pid} moved to the Recycle Bin: {r['moved']}"
                        + (f" - not moved: {r['left']}" if r["left"] else "") + "\n")
            if r["left"]:
                raise ValueError(r.get("why_shown") or I18N.t("the prompt could not be moved to the Recycle Bin"))
            return self._json({"deleted": pid})
        if path == "/api/prompts/guess":                  # the Add dialog's kind, while the user types
            return self._json({"kind": PR.guess_kind(str(body.get("text", ""))[:200_000])})
        if path == "/api/prompts/file":                   # an attached .txt / .md / .docx / .pdf -> its text
            try:
                raw = base64.b64decode(str(body.get("data", "")), validate=True)
            except ValueError:
                raise ValueError(I18N.t("the file did not arrive whole - attach it again")) from None
            if len(raw) > 30_000_000:
                raise ValueError(I18N.t("files up to 30 MB"))
            return self._json(PR.save_file(str(body.get("name", "")), raw))
        if path == "/api/prompts/rate":
            return self._json(PR.update(str(body.get("id", "")), rating=body.get("rating") or None,
                                        note=body.get("note")))
        if path == "/api/claude":                        # options = the dialog's choices (nothing opens)
            task = str(body.get("task") or "free")
            if body.get("options"):
                return self._json(system.claude_options(task))
            model, effort = body.get("model") or None, body.get("effort") or None
            if body.get("remember"):                     # "Don't ask again": the dialog's choice becomes Settings
                system.save({"claude_model": model or "auto", "claude_effort": effort or "auto", "claude_ask": False})
            return self._json(system.open_claude(str(body.get("prompt", "")), task, str(body.get("label", "")),
                                                 model, effort))
        if path == "/api/player/copy":                   # the browser cannot play it: queue its player copy
            v = lab_file(str(body.get("path", "")))
            rel = data.rel(v)
            info = player.info(v)
            if info["copy"]:
                return self._json(info)
            jid = player_job(rel)
            job = S.runner.jobs[jid] if jid else S.runner.start("player_copy", {"path": rel}, queue=True)
            return self._json({**info, "job": job.id, "status": job.status})
        if path == "/api/report":                         # the dialog's note; open = the GitHub page in the browser
            r = problem_report(body.get("job"), str(body.get("note") or ""))
            if body.get("open"):
                if not r["url"]:
                    raise ValueError(I18N.t("this copy has no GitHub repo - copy the report instead"))
                os.startfile(r["url"])                    # noqa: S606 - the user's click; GitHub shows it, nothing sent
                r["opened"] = True
            return self._json(r)
        if path == "/api/delete":                        # the user's Delete button, after the dialog
            if S.runner.active():
                raise jobs.JobError(I18N.t("wait until the running jobs finish, then delete"))
            r = trash.delete(str(body.get("kind", "")), str(body.get("name", "")), body.get("keys") or [],
                             S.resolve.get("state", ""))
            with open(APPDIR / "deleted.log", "a", encoding="utf-8") as f:      # what went to the Recycle Bin, when
                f.write(f"{data.stamp()} moved to the Recycle Bin: {r['moved']}"
                        + (f" - not moved: {r['failed']}" if r["failed"] else "") + "\n")
            shown = r.pop("why_shown", "")               # why in the app's language for the page (the log: English)
            for x in r["failed"] if shown else []:
                x["why"] = shown
            return self._json(r)
        if path == "/api/shortcut":
            return self._json(system.make_shortcut(str(body.get("where", ""))))
        if path == "/api/open":
            if str(body.get("path", "")) in ("", "."):
                subprocess.Popen(["explorer", str(LAB)])
                return self._json({"ok": True})
            p = lab_file(str(body.get("path", "")), FILE_ROOTS | {"tools"})
            if body.get("reveal") or p.is_dir() or p.suffix.lower() not in OPENABLE:
                subprocess.Popen(["explorer", str(p)] if p.is_dir() else ["explorer", "/select,", str(p)])
            else:
                os.startfile(str(p))                                   # noqa: S606 - a viewer for a lab file
            return self._json({"ok": True})
        raise NoRoute(path)



def player_job(rel: str | None) -> int | None:
    """The player-copy job of this file that is still running or waiting, if any (one copy per file)."""
    return next((j.id for j in S.runner.active() if j.kind == "player_copy" and j.args.get("path") == rel), None)


def problem_report(job_id, note: str) -> dict:
    """Report a problem (report.py): a failed job's report (its log's last lines) or, without a job, the app's
    (server.log's last lines); scrubbed; the GitHub link of the repo this copy updates from."""
    job = S.runner.jobs.get(int(job_id)) if str(job_id or "").isdigit() else None
    if job_id and not job:
        raise FileNotFoundError(I18N.t("job {id} (jobs of an earlier session are gone - use Settings > Report a problem)",
                                       id=job_id))
    if job:
        log = report.tail(job.log) if job.log.exists() else job.lines[-report.LOG_LINES:]
    else:
        log = report.tail(report.SERVER_LOG)
    s = system.load()
    progs = {"yt-dlp": system.version(system.find("yt-dlp", s)), "deno": system.deno_info(s).get("version"),
             "ffmpeg": (system.version(system.find("ffmpeg", s), ("-version",)) or "").replace("ffmpeg version ", "")
             .split(" Copyright")[0] or None}
    names = tuple(n for n in (s.get("author"), os.environ.get("COMPUTERNAME")) if n)
    remote = updater._remote() if updater.is_repo() else None
    # Report a problem stays English: the job's English title (Job.title_en), not the one the page shows
    return {**report.build({**job.info(), "title": job.title_en} if job else None, log, note, remote, progs, names),
            "job": job.id if job else None}


BATCH_MAX = 10                                     # videos per Add videos (each one is a lab pass, maybe a Claude check)


def analyze_batch(body: dict) -> dict:
    """Analyze > Add videos: every link is downloaded and then analysed, every file analysed - one after another
    (queued jobs), all with the same focus / category / tags / Claude check. Nothing starts if anything is wrong."""
    links = [str(u).strip() for u in body.get("links") or [] if str(u).strip()]
    files = [str(f).strip().strip('"') for f in body.get("files") or [] if str(f).strip()]
    if not links and not files:
        raise ValueError(I18N.t("paste a link or pick a video first"))
    if len(links) + len(files) > BATCH_MAX:
        raise ValueError(I18N.t("at most {n} videos at a time - add the rest when these are done", n=BATCH_MAX))
    focus = str(body.get("focus") or "both")
    if focus not in ("content", "cinematic", "both"):
        raise ValueError(I18N.t("unknown focus {id}", id=focus))
    opts = {"focus": focus, "claude": bool(body.get("claude"))}
    if body.get("category"):
        opts["category"] = str(body["category"])
    if body.get("tags"):
        opts["tags"] = str(body["tags"])
    st = system.load()
    preset = st.get("download_preset") if st.get("download_preset") in ("mp4_1080", "mp4_best") else "mp4_1080"
    for u in links:                                     # check everything before anything starts
        if not re.match(r"https?://\S+$", u):
            raise ValueError(I18N.t("not a link: {link} (a full link starts with https://)", link=u))
        system.download_cmd(u, preset)
    for f in files:
        jobs.make("analyze", {**opts, "video": f, "redetect": bool(body.get("redetect"))})
    system.save({"default_focus": focus})
    batch = int(time.time() * 1000) % 10_000_000
    started = []
    for f in files:
        started.append(S.runner.start("analyze", {**opts, "video": f, "redetect": bool(body.get("redetect"))},
                                      queue=True, batch=batch))
    for u in links:
        started.append(S.runner.start("download", {"url": u, "preset": preset}, queue=True, then=opts, batch=batch))
    return {"batch": batch, "jobs": [j.info() for j in started]}


def edit_batch(body: dict) -> dict:
    """Editor > Edit several videos (0.4.5): one style for 2-10 of the user's videos. Everything is checked first;
    each video gets the same request (build\\edit_request.json, its own song if its folder has one), then either a
    quick draft each (queued jobs, no Claude) or one Claude window for all (/recreate-video batch <id>)."""
    names = list(dict.fromkeys(str(p) for p in body.get("projects") or [] if str(p).strip()))
    if not 2 <= len(names) <= BATCH_MAX:
        raise ValueError(I18N.t("pick 2 to {n} videos", n=BATCH_MAX))
    req = dict(body.get("request") or {})
    if req.get("how") not in ("style", "words"):
        raise ValueError(I18N.t("several videos are edited in a style or the way you say (not a 1:1 copy)"))
    req["music"] = ""                                   # each video: the song in its own folder, if any
    mode = body.get("mode")
    if mode not in ("drafts", "claude"):
        raise ValueError(I18N.t("mode: drafts or claude"))
    folders = []
    for n in names:
        d = data.PROJECTS / data.safe_name(n)
        if not d.is_dir():
            raise FileNotFoundError(n)
        if not data.clip_files(d):                    # videos or photos
            raise ValueError(I18N.t("{video}: no clips in its folder yet", video=data._label(d / "build") or d.name))
        folders.append(d.name)
    for n in folders:
        data.save_edit_request(n, req)
    if mode == "drafts":
        batch = int(time.time() * 1000) % 10_000_000
        return {"jobs": [S.runner.start("draft", {"project": n}, queue=True, batch=batch).info() for n in folders]}
    b = data.new_batch("recreate", folders)
    return {"batch": b, "prompt": data.batch_prompt(b), "label": f"batch of {len(folders)}"}


def restart_soon() -> None:
    """Start a new app server for the same port (it waits until this one has let go of it), then stop this one.
    The window keeps polling /api/ping and reloads when the new server answers."""
    S.phase = "restarting"
    pyw = Path(sys.executable).with_name("pythonw.exe")
    exe = pyw if pyw.exists() else Path(sys.executable)
    args = [str(exe), str(LAB / "tools" / "app.py"), "--no-window", "--wait-port", "--port", str(S.port)]
    if not S.auto_exit:
        args.append("--stay")
    if not S.check_updates:
        args.append("--no-update")
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen(args, cwd=str(LAB), creationflags=flags | NO_WINDOW, close_fds=True)
    threading.Timer(0.8, S.server.shutdown).start()


def apply_update() -> dict:
    if S.runner.active():
        raise jobs.JobError(I18N.t("wait until the running jobs finish, then update"))
    S.phase = "updating"
    try:
        r = updater.apply()
    except Exception:
        S.phase = "ready"
        raise
    S.update_result = r
    S.update = updater.cached()
    if r.get("updated"):
        try:
            KN.summary()                                     # friends' cards that came in, for Claude
        except Exception:                                    # noqa: BLE001 - the update itself worked
            log_error("knowledge summary after the update failed\n" + traceback.format_exc())
    r["restart"] = bool(r.get("updated") and r.get("code_changed", True))
    if r["restart"]:
        restart_soon()
    else:                                                    # only knowledge came in: no restart needed
        S.phase = "ready"
    return r


def share_knowledge() -> dict:
    """'Share my knowledge': new / changed reference cards + unreviewed local lessons -> the repo (commit + push), or
    a pack file in knowledge\\outbox\\ to send when this copy cannot push. What the user keeps on this PC (unticked,
    or looks like a test) is never in the pack (KN.pending). A pack that was not uploaded counts as shared by file
    (2026-10-18): it is the share, so it is not sent twice; the answer names what went."""
    who = KN.author()
    if not who:
        raise ValueError(I18N.t("set your name for sharing first (Settings > Sharing & updates)"))
    pack = KN.make_pack(who)
    out = {"author": who, "cards": len(pack["cards"]), "lessons": len(pack["lessons"]), "pushed": False,
           "names": [KN.label(c)["name"] for c in pack["cards"]], "lesson_ids": [i for i, _ in pack["lessons"]]}
    if pack["cards"] or pack["lessons"]:
        out["pack"] = str(KN.write_pack(pack).relative_to(LAB)).replace("\\", "/")
    if updater.is_repo():
        try:
            files = KN.stage(pack) if (pack["cards"] or pack["lessons"]) else []
            r = updater.share(files, who, f"knowledge: {who} shares {len(pack['cards'])} reference(s), "
                                          f"{len(pack['lessons'])} lesson(s)")
            out.update(r)
            if r.get("pushed"):
                KN.mark_shared(pack, "github")
                S.update = updater.check(fetch=False)
                if r.get("code_updated") and not S.runner.active():      # sharing pulled in a new version
                    KN.summary()
                    out["restarting"] = True
                    restart_soon()
        except updater.GitError as e:
            out["error"] = str(e)
    else:
        out["error"] = I18N.t("this copy is not connected to GitHub - send the pack file instead")
    if out.get("pack") and not out.get("pushed"):          # the file is the share: recorded, not sent again
        KN.mark_shared(pack, "file")
        out["by_file"] = True
    if not pack["cards"] and not pack["lessons"] and not out.get("pushed"):
        out["nothing"] = not out.get("error")
    KN.summary()
    return out


def startup_update() -> None:
    """Shortly after start: look for a new version on GitHub. Settings' update_mode: "ask" (default) = the window's
    Update button appears; "auto" = install it right away (only now, before work starts); "off" = don't look."""
    time.sleep(3)
    try:
        mode = system.load().get("update_mode", "ask")
        if mode == "off":
            return
        threading.Thread(target=UP.check, daemon=True).start()  # newer HyperFrames / GSAP (at most once a day)
        if not updater.is_repo():
            return
        S.update = updater.check(fetch=True)
        if (mode == "auto" and S.update.get("can_update") and not S.runner.active()
                and time.time() - S.started < 180):
            apply_update()
    except Exception:                                           # noqa: BLE001 - never break the app over an update
        S.phase = "ready"
        log_error("update check failed\n" + traceback.format_exc())


def watcher(server: ThreadingHTTPServer):
    """Resolve status every ~20 s; when the window has been closed (no ping) and no job runs, stop the server."""
    n = 0
    while True:
        if n % 4 == 0:
            S.resolve = {"state": resolve_state(), "checked": data.stamp()}
        if (n and n % 720 == 0 and S.check_updates                      # hourly: the Update button only
                and system.load().get("update_mode", "ask") != "off"):
            try:
                S.update = updater.check(fetch=True)
            except Exception:                                   # noqa: BLE001
                pass
            UP.check()                                          # newer HyperFrames / GSAP: asks npm once a day
        n += 1
        time.sleep(5)
        if not S.auto_exit or S.runner.active():
            continue
        now, last = time.time(), (S.last_ping or S.started)
        if (S.bye and S.bye >= last and now - S.bye > 10) or now - last > (180 if S.last_ping else 300):
            break
    server.shutdown()


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        """A browser dropping a kept-alive connection is normal; anything else goes to .app\\server.log."""
        if isinstance(sys.exc_info()[1], (ConnectionAbortedError, ConnectionResetError, BrokenPipeError)):
            return
        log_error(f"request from {client_address[0]}\n{traceback.format_exc()}")


def make(port: int, auto_exit: bool, check_updates: bool = True) -> ThreadingHTTPServer:
    """check_updates=False (app.py --no-update): no update check at all - a test server on a working copy with
    unsaved changes must never pull an update into it."""
    global S
    srv = Server(("127.0.0.1", port), Handler)
    # the app's words follow Settings > Language (MOTIONLAB_LANG overrides) - before State, whose update records
    # (What's new) are read in that language
    I18N.follow_settings()
    S = State(srv.server_address[1], auto_exit)
    S.server = srv
    S.check_updates = check_updates
    APPDIR.mkdir(exist_ok=True)
    try:                                    # analyses named by 0.3.2 with ".." (a title with "..."): no page opens them
        fix_dotted_names(log=log_error)
    except OSError as e:
        log_error(f"renaming analyses with '..' in their name: {e}")
    # for tools\\app.py: which server runs here (version, token) - it replaces an older one after an update
    (APPDIR / "server.json").write_text(json.dumps({"port": S.port, "pid": os.getpid(), "token": S.token,
                                                    "version": VERSION, "started": data.stamp()}), encoding="utf-8")
    threading.Thread(target=watcher, args=(srv,), daemon=True).start()
    if check_updates:
        threading.Thread(target=startup_update, daemon=True).start()
    if auto_exit:                           # the real app (a test server --stay leaves the windows alone): MotionLab's
        from . import winicon               # own taskbar button and icon on its Edge windows (2026-10-24)
        winicon.watch()
    return srv
