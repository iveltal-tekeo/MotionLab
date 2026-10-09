"""The app's local web server (Python standard library only).

Listens on 127.0.0.1 only and answers only requests addressed to it (Host check). Pages come from ui\\; lab files
are served read-only from /files/<lab-relative path> (analysis, projects, refs, docs, library) with byte ranges
so videos can seek; /api/ returns JSON. Every request that changes something (verdicts, picks, jobs) must carry the
session token embedded in the page, so other web pages cannot use the server. The only writes: the user's
verdicts / exported feedback (analysis\\<name>\\feedback\\), library picks (projects\\<name>\\build\\), and the app's
own .app\\ folder (logs, job logs, video thumbnails), settings.json (Settings page) and downloads into refs\\
(yt-dlp, started from the References page). Deleting = the user's Delete buttons only (trash.py): after a dialog
listing every item, references / downloads / video projects / renders go to the Windows Recycle Bin. Programs it
can start: Claude Code in a new console ("Open in Claude", or when a lab pass started with "Analyse with Claude"
ends), Explorer / the default viewer for lab files, and the shortcut maker - each only on a click."""
from __future__ import annotations

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
from motionlab import knowledge as KN
from motionlab.styles import CATEGORIES
from motionlab.util import LAB, tool

from . import data, jobs, system, trash, updater

VERSION = __version__                               # one version: tools/motionlab/__init__.py
API_LEVEL = 4                                       # app.js API_LEVEL: the functions the page needs
UI = Path(__file__).resolve().parent / "ui"
APPDIR = LAB / ".app"
THUMBS = APPDIR / "thumbs"
FILE_ROOTS = {"analysis", "projects", "refs", "docs", "library", "knowledge"}
OPENABLE = {".html", ".md", ".txt", ".png", ".jpg", ".jpeg", ".mp4", ".mov", ".json", ".csv"}
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
for ext, typ in ((".js", "text/javascript"), (".css", "text/css"), (".md", "text/plain"), (".comp", "text/plain"),
                 (".mp4", "video/mp4"), (".json", "application/json"), (".csv", "text/plain"), (".py", "text/plain")):
    mimetypes.add_type(typ, ext)


def log_error(msg: str) -> None:
    APPDIR.mkdir(exist_ok=True)
    with open(APPDIR / "server.log", "a", encoding="utf-8") as f:
        f.write(f"{data.stamp()} {msg}\n")


def resolve_state() -> str:
    """'running' / 'not responding' / 'not running' (Windows' own flag; same as resolve_build.resolve_state)."""
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


def status() -> dict:
    refs = data.list_references()
    projs = data.list_projects()
    lib = data.library()
    du = shutil.disk_usage(str(LAB))
    verdicts = sum(r["verdicts"] for r in refs)
    nxt = []
    for r in refs:                                      # each reference's next step of the workflow (data.FLOW)
        fl, go = r["flow"], f"#/ref/{urllib.parse.quote(r['name'])}"
        if fl["next"] == "claude":
            nxt.append({"text": f"Send {r['title']} to Claude: {fl['events'] - fl['reviewed']} effect(s) not checked "
                                f"yet (until then their names are the lab's guesses)", "go": go,
                        "claude": r["review_prompt"], "task": "review",
                        "label": r["title"]})
        elif fl["next"] == "verdicts":
            nxt.append({"text": f"Give your verdicts on {r['title']}: {fl['given']} of {fl['real']} effects"
                                + (f", {fl['misses_checked']} of {fl['misses']} possible misses" if fl["misses"] else ""),
                        "go": go})
        elif fl["next"] == "feedback":
            nxt.append({"text": f"Send your verdicts on {r['title']} to Claude (Send feedback to Claude): it turns them "
                                f"into lessons" + (" - exported, waiting for Claude" if fl["sent"] else ""), "go": go})
    if projs and not lib["items"]:
        nxt.append({"text": "Pick the effects to save in the library (your video's page, Resolve tab)",
                    "go": f"#/project/{projs[0]['name']}/resolve"})
    setup = [t for t in system.tools() if not t["found"] and t["need"] in ("required", "recommended")]
    if not refs:
        nxt.insert(0, {"text": "Start here: download a reference video (References > Download from a link) or drop "
                               "one into the refs folder, then click Analyse a video", "go": "#/refs"})
    return {"version": VERSION, "lab": str(LAB), "references": len(refs), "events": sum(r["events"] for r in refs),
            "reviewed": sum(r["reviewed"] for r in refs), "verdicts": verdicts, "projects": len(projs),
            "library": len(lib["items"]), "picks": len(lib["picks"]), "free_bytes": du.free, "total_bytes": du.total,
            "resolve": S.resolve, "jobs_running": [j.info() for j in S.runner.running()],
            "roadmap": "docs/roadmap.png" if (LAB / "docs" / "roadmap.png").exists() else None, "next": nxt,
            "projects_list": projs, "references_list": refs, "setup": setup,
            "claude": bool(system.find("claude")), "update": S.update, "update_result": S.update_result,
            "author": KN.author()}


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
            raise FileNotFoundError(f"frame {frame} of {video.name}")
    return out


def lab_file(relpath: str, roots=FILE_ROOTS) -> Path:
    p = (LAB / urllib.parse.unquote(relpath)).resolve()
    if LAB not in p.parents or p.relative_to(LAB).parts[0] not in roots:
        raise PermissionError(relpath)
    if not p.exists():
        raise FileNotFoundError(relpath)
    return p


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

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if n > 5_000_000:
            raise ValueError("request too large")
        raw = self.rfile.read(n) if n else b""
        obj = json.loads(raw.decode("utf-8") or "{}")
        if not isinstance(obj, dict):
            raise ValueError("expected a JSON object")
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
        html = (UI / "index.html").read_text(encoding="utf-8").replace("{{TOKEN}}", S.token) \
            .replace("{{VERSION}}", VERSION)
        self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")

    def _guard(self, fn):
        try:
            fn()
        except jobs.JobError as e:
            self._err(409, str(e))
        except FileNotFoundError as e:
            self._err(404, f"not found: {e}")
        except PermissionError as e:
            self._err(403, f"not allowed: {e}")
        except RuntimeError as e:
            self._err(500, str(e))
        except (ValueError, KeyError, TypeError) as e:
            self._err(400, str(e))
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass
        except Exception:                                       # noqa: BLE001 - report, keep serving
            log_error(f"{self.command} {self.path}\n{traceback.format_exc()}")
            try:
                self._err(500, "internal error (details in .app\\server.log)")
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
            return self._file(lab_file(path[len("/files/"):]))
        if path == "/api/ping":
            S.last_ping = time.time()
            u = S.update or {}
            return self._json({"app": "motionlab", "version": VERSION, "running": len(S.runner.running()),
                               "resolve": S.resolve, "phase": S.phase, "api": API_LEVEL,
                               "update": bool(u.get("can_update")), "update_kind": u.get("kind"),
                               "update_version": u.get("new_version"), "update_cards": u.get("new_cards", 0),
                               "update_lessons": u.get("new_lessons", 0)})
        if path == "/api/status":
            return self._json(status())
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
                               "efforts": list(system.EFFORTS),
                               "tasks": {k: v[0] for k, v in system.TASKS.items()},
                               "resolve_mcp": system.resolve_mcp_state(),
                               "update": {**(S.update or {}), "phase": S.phase}})
        if path == "/api/downloads":
            return self._json(system.downloads())
        if path == "/api/update":
            return self._json({**(S.update or {}), "version": VERSION, "phase": S.phase, "result": S.update_result})
        if path == "/api/knowledge":
            return self._json(KN.overview())
        if path == "/api/knowledge/card":
            return self._json(KN.card_detail(arg("id", "")))
        if path == "/api/text":
            return self._json({"path": arg("path"), "text": data.text_file(arg("path", ""))})
        if path == "/api/thumb":
            v = lab_file(arg("video", ""))
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
        m = re.fullmatch(r"/api/jobs/(\d+)", path)
        if m:
            job = S.runner.jobs.get(int(m[1]))
            if not job:
                raise FileNotFoundError(f"job {m[1]}")
            return self._json(job.info(int(arg("since", "0"))))
        raise FileNotFoundError(path)

    # ------------------------------------------------------------------------------------------ POST
    def do_POST(self):
        if not self._host_ok():
            return self._err(403, "wrong host")
        self._guard(self._post)

    def _post(self):
        path = urllib.parse.urlsplit(self.path).path
        body = self._body()
        tok = self.headers.get("X-ML-Token") or body.get("token") or ""
        if not secrets.compare_digest(str(tok), S.token):
            raise PermissionError("missing or wrong session token")
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
        if path == "/api/jobs":
            return self._json(S.runner.start(str(body.get("kind", "")), body.get("args") or {}).info(0))
        m = re.fullmatch(r"/api/jobs/(\d+)/cancel", path)
        if m:
            return self._json(S.runner.cancel(int(m[1])).info())
        if path == "/api/settings":
            return self._json({"settings": system.save(body.get("settings") or {})})
        if path == "/api/quit":
            if S.runner.running() and not body.get("force"):
                raise jobs.JobError("a job is still running")
            threading.Timer(0.4, S.server.shutdown).start()
            return self._json({"ok": True})
        if path == "/api/restart":
            if S.runner.running():
                raise jobs.JobError("wait until the running jobs finish")
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
        if path == "/api/update/connect":
            r = updater.connect(str(body.get("url", "")))
            S.update = updater.check(fetch=False)
            return self._json(r)
        if path == "/api/knowledge/share":
            return self._json(share_knowledge())
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
            r = KN.save_meta(name, **{k: body[k] for k in ("category", "tags") if k in body})
            KN.build_local_cards([name])
            return self._json(r)
        if path == "/api/claude":
            return self._json(system.open_claude(str(body.get("prompt", "")), str(body.get("task") or "free"),
                                                 str(body.get("label", ""))))
        if path == "/api/delete":                        # the user's Delete button, after the dialog
            if S.runner.running():
                raise jobs.JobError("wait until the running jobs finish, then delete")
            r = trash.delete(str(body.get("kind", "")), str(body.get("name", "")), body.get("keys") or [],
                             S.resolve.get("state", ""))
            with open(APPDIR / "deleted.log", "a", encoding="utf-8") as f:      # what went to the Recycle Bin, when
                f.write(f"{data.stamp()} moved to the Recycle Bin: {r['moved']}"
                        + (f" - not moved: {r['failed']}" if r["failed"] else "") + "\n")
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
        raise FileNotFoundError(path)



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
    if S.runner.running():
        raise jobs.JobError("wait until the running jobs finish, then update")
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
    a pack file in knowledge\\outbox\\ to send when this copy cannot push."""
    who = KN.author()
    if not who:
        raise ValueError("set your name for sharing first (Settings > Sharing & updates)")
    pack = KN.make_pack(who)
    out = {"author": who, "cards": len(pack["cards"]), "lessons": len(pack["lessons"]), "pushed": False}
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
                if r.get("code_updated") and not S.runner.running():      # sharing pulled in a new version
                    KN.summary()
                    out["restarting"] = True
                    restart_soon()
        except updater.GitError as e:
            out["error"] = str(e)
    else:
        out["error"] = "this copy is not connected to GitHub - send the pack file instead"
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
        if mode == "off" or not updater.is_repo():
            return
        S.update = updater.check(fetch=True)
        if (mode == "auto" and S.update.get("can_update") and not S.runner.running()
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
        n += 1
        time.sleep(5)
        if not S.auto_exit or S.runner.running():
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
    S = State(srv.server_address[1], auto_exit)
    S.server = srv
    S.check_updates = check_updates
    APPDIR.mkdir(exist_ok=True)
    # for tools\\app.py: which server runs here (version, token) - it replaces an older one after an update
    (APPDIR / "server.json").write_text(json.dumps({"port": S.port, "pid": os.getpid(), "token": S.token,
                                                    "version": VERSION, "started": data.stamp()}), encoding="utf-8")
    threading.Thread(target=watcher, args=(srv,), daemon=True).start()
    if check_updates:
        threading.Thread(target=startup_update, daemon=True).start()
    return srv
