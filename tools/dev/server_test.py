"""The app server's own guards, checked from outside (2026-11-02; docs\\design_brain_and_hardening.md section 5, the
user's pick "do 1"): a test server of its own (English, no window, no update check, a free port) and plain HTTP - no
browser, nothing written. Each refusal has a positive control beside it, so a server that refuses everything fails.

    .venv\\Scripts\\python tools\\dev\\server_test.py [--port N]

  - the Host header: a page for another host (a DNS rebinding) gets 403 on GET and POST
  - the session token: a POST without it or with a wrong one gets 403; with it, the route's own answer
  - the body's size: over the cap = refused before it is read
  - paths: /ui/ and /files/ never leave their folders (.., %2e%2e, a drive), /files/ never serves .app or tools
  - /api/text: never .app\\server.json (the token), settings.json, .claude\\settings.json, the code or a private
    file (data.PRIVATE_FILES: the ElevenLabs key) - the user's own data stays readable by the page, which only the
    right Host reaches and no other site can read (no CORS)
smoke.py runs the same checks (one gate before a release); PASS / FAIL lines, exit 1 on a FAIL. .app\\server.json
(which a test server overwrites) is put back afterwards.
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
LAB = TOOLS.parent
PY = sys.executable
FAILS: list[str] = []


def ok(cond, what: str) -> bool:
    print(("PASS  " if cond else "FAIL  ") + what)
    if not cond:
        FAILS.append(what)
    return bool(cond)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_port(port: int, timeout: float = 30) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=1).close()
            return True
        except OSError:
            time.sleep(0.3)
    return False


def call(port: int, method: str, path: str, body: bytes | None = None, headers: dict | None = None,
         length: int | None = None) -> tuple[int, str]:
    """One raw request (the path is sent as written - no client-side clean-up of .. or %2e)."""
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    try:
        c.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
        h = {"Host": f"127.0.0.1:{port}", **(headers or {})}
        if body is not None or length is not None:
            h["Content-Length"] = str(length if length is not None else len(body or b""))
            h.setdefault("Content-Type", "application/json")
        for k, v in h.items():
            c.putheader(k, v)
        c.endheaders()
        if body:
            c.send(body)
        r = c.getresponse()
        return r.status, r.read().decode("utf-8", "replace")
    finally:
        c.close()


def run(port: int) -> None:
    get = lambda p, **kw: call(port, "GET", p, **kw)                                       # noqa: E731
    post = lambda p, obj, **kw: call(port, "POST", p, json.dumps(obj).encode(), **kw)     # noqa: E731

    st, html = get("/")
    m = re.search(r'<meta name="ml-token" content="([^"]+)"', html)
    if not ok(st == 200 and m, "GET / with the right host: the page and its session token"):
        return
    tok = {"X-ML-Token": m[1]}

    # the Host header (a page on another site that points its own name at 127.0.0.1)
    ok(get("/", headers={"Host": f"evil.example:{port}"})[0] == 403, "GET with another host: 403")
    ok(post("/api/agency/month", {"action": "x"}, headers={**tok, "Host": f"evil.example:{port}"})[0] == 403,
       "POST with another host, even with the token: 403")

    # the session token (a harmless route: an unknown action is refused after the token check, nothing written)
    st, txt = post("/api/agency/month", {"action": "x"}, headers=tok)
    ok(st == 400 and "plan a next test" in txt, f"POST with the token reaches the route ({st})")
    ok(post("/api/agency/month", {"action": "x"})[0] == 403, "POST without the token: 403")
    ok(post("/api/agency/month", {"action": "x"}, headers={"X-ML-Token": "0" * len(m[1])})[0] == 403,
       "POST with a wrong token: 403")
    ok(call(port, "POST", "/api/agency/retention/upload?name=x.png", b"x", headers={"Content-Type":
       "application/octet-stream"})[0] == 403, "a raw upload without the token: 403")

    # the body's size: Content-Length over the 5 MB cap is refused before anything is read
    st, txt = call(port, "POST", "/api/agency/month", b"{}", headers=tok, length=6_000_000)
    ok(st in (400, 413) and "too large" in txt, f"a body over the cap: refused ({st})")

    # paths
    ok(get("/ui/app.css")[0] == 200, "GET /ui/app.css (control): 200")
    for p in ("/ui/../server.py", "/ui/%2e%2e/server.py", "/ui/..%2fserver.py", "/ui/%2e%2e%2f%2e%2e%2fdata.py"):
        ok(get(p)[0] in (403, 404), f"GET {p}: refused")
    ok(get("/files/docs/plans.md")[0] == 200, "GET /files/docs/plans.md (control): 200")
    for p in ("/files/../../Windows/win.ini", "/files/%2e%2e/%2e%2e/Windows/win.ini", "/files/C:/Windows/win.ini",
              "/files/.app/server.json", "/files/tools/app.py", "/files/.claude/settings.json", "/files/settings.json",
              "/files/knowledge/local/elevenlabs.json"):
        ok(get(p)[0] in (403, 404), f"GET {p}: refused")

    # /api/text: what the page reads, never a private or code file
    for p in ("CHANGELOG.md", "docs/plans.md"):
        ok(get(f"/api/text?path={p}")[0] == 200, f"/api/text {p} (control): 200")
    for p in (".app/server.json", "settings.json", ".claude/settings.json", "tools/app.py",
              "tools/motionlab/app/server.py", "../Windows/win.ini", "knowledge/local/elevenlabs.json"):
        st, _ = get(f"/api/text?path={p}")
        ok(st in (403, 404), f"/api/text {p}: refused ({st})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=0)
    a = ap.parse_args()
    port = a.port or free_port()
    sj = LAB / ".app" / "server.json"                      # a test server writes it; the user's app reads it
    before = sj.read_bytes() if sj.exists() else None
    srv = subprocess.Popen([PY, str(TOOLS / "app.py"), "--no-window", "--stay", "--no-update", "--port", str(port)],
                           cwd=str(LAB), env={**os.environ, "MOTIONLAB_LANG": "en"},
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if ok(wait_port(port), f"test server listens on 127.0.0.1:{port}"):
            run(port)
    finally:
        srv.kill()
        srv.wait(timeout=10)
        if before is not None:
            sj.write_bytes(before)
    print(f"\nSERVER TEST {'PASS' if not FAILS else 'FAIL - ' + str(len(FAILS))}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
