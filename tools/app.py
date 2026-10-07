"""MotionLab app: a local web interface over the lab, in its own window (Microsoft Edge in app mode).

    double-click C:\\MotionLab\\MotionLab.bat                        (normal use: no console window)
    .venv\\Scripts\\python tools\\app.py [--port 8765]                 the same, with a console
    .venv\\Scripts\\python tools\\app.py --no-window [--stay]          server only: open http://127.0.0.1:8765/
    .venv\\Scripts\\python tools\\app.py --no-window --stay --no-update --port 8791     a test server (no update check)

The window talks to a small server on 127.0.0.1 that only this PC can reach. The only network traffic: downloads
from a link (yt-dlp), the update check / update (git fetch / pull from the GitHub repo, if this copy is connected)
and "Share my knowledge" (git push of knowledge\\ text). The server stops by itself a little after the last window is
closed (or 5 minutes after start if no window ever connects), unless a job (analysis, Resolve check, ...) is still
running - then when it finishes. --stay keeps it running.
Starting it again while it runs just opens another window - unless the running server is an older version (after an
update): then it is replaced (only when no job is running). Errors: C:\\MotionLab\\.app\\server.log.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab.app import server  # noqa: E402

EDGE = [Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Microsoft/Edge/Application/msedge.exe"]


def open_window(url: str) -> None:
    edge = next((p for p in EDGE if p.exists()), None)
    if edge:
        subprocess.Popen([str(edge), f"--app={url}", "--window-size=1600,1000", "--window-position=60,30"])
    else:
        webbrowser.open(url)


def say(msg: str) -> None:
    if sys.stdout:                                              # pythonw (double-click) has no console
        print(msg, flush=True)


def ping(port: int) -> dict | None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ping", timeout=1.5) as r:
            d = json.load(r)
            return d if d.get("app") == "motionlab" else None
    except (OSError, ValueError):
        return None


def running_app(port: int) -> bool:
    return ping(port) is not None


def stop_old(port: int) -> bool:
    """Stop an older MotionLab server on this port (the window then says so; it is opened again on the new one).
    Asks it politely with its token (.app\\server.json); a v0.1 server has no quit command - its process is ended."""
    info = {}
    try:
        info = json.loads((server.APPDIR / "server.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    asked = False
    if info.get("port") == port and info.get("token"):
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/api/quit", method="POST",
                                         data=json.dumps({"token": info["token"]}).encode(),
                                         headers={"Content-Type": "application/json", "X-ML-Token": info["token"]})
            urllib.request.urlopen(req, timeout=3).read()
            asked = True
        except OSError:
            pass
    for _ in range(20 if asked else 0):
        if free(port):
            return True
        time.sleep(0.25)
    pid = _listening_pid(port)                                   # an old server without /api/quit
    if pid and _is_python(pid):
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    for _ in range(20):
        if free(port):
            return True
        time.sleep(0.25)
    return False


def _listening_pid(port: int) -> int | None:
    try:
        out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True, timeout=10,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    for ln in out.splitlines():
        parts = ln.split()
        if len(parts) >= 5 and parts[1] == f"127.0.0.1:{port}" and parts[3].upper() == "LISTENING":
            return int(parts[4])
    return None


def _is_python(pid: int) -> bool:
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"], capture_output=True, text=True,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout.lower()
    return "python" in out


def free(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-window", action="store_true", help="only start the server")
    ap.add_argument("--stay", action="store_true", help="keep the server running when no window is open")
    ap.add_argument("--wait-port", action="store_true", help="wait until the port is free (restart after an update)")
    ap.add_argument("--no-update", action="store_true",
                    help="no update check at start (a test server on a working copy must not pull an update into it)")
    a = ap.parse_args()
    if a.wait_port:
        for _ in range(80):                                      # the old server lets go within a second or two
            if free(a.port):
                break
            time.sleep(0.25)
    run = ping(a.port)
    if run and run.get("version") != server.VERSION and not run.get("running"):
        say(f"replacing MotionLab {run.get('version')} with {server.VERSION} on port {a.port}")
        stop_old(a.port)
        run = ping(a.port)
    if run:
        if not a.no_window:
            open_window(f"http://127.0.0.1:{a.port}/")
        say(f"MotionLab {run.get('version')} already runs on http://127.0.0.1:{a.port}/")
        return 0
    port = a.port if free(a.port) else 0                       # 0 = any free port
    srv = server.make(port, auto_exit=not a.stay, check_updates=not a.no_update)
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    say(f"MotionLab app on {url}")
    if not a.no_window:
        threading.Timer(0.2, open_window, [url]).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                                           # noqa: BLE001 - pythonw has no console: keep the error
        server.log_error("app.py crashed\n" + traceback.format_exc())
        raise
