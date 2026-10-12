"""App smoke test (GitHub Actions, and after any change to the app or the MCP server): every Python file compiles,
every motionlab module imports, the app server answers its read-only routes, every page renders in headless Edge
without a script error, and MotionLab's MCP server starts and lists its tools.

    .venv\\Scripts\\python tools\\dev\\smoke.py [--port 8797] [--no-browser]

Read-only on the lab: a test server with --no-update (no update check), no clicks, only GET requests; the analysis
page is opened for a self-test analysis (synthetic_*) only, never for your own references; .app\\server.json is put
back afterwards. Exit code 0 = PASS. The workflow runs it after selftest.py, so the self-test analyses exist there.
"""
from __future__ import annotations

import argparse
import importlib
import json
import pkgutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
LAB = TOOLS.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(HERE))
PY = sys.executable
FAILED: list[str] = []
PAGES = ["#/", "#/refs", "#/projects", "#/prompts", "#/library", "#/knowledge", "#/jobs", "#/storage", "#/settings"]
ROUTES = ["/api/status", "/api/references", "/api/candidates", "/api/waiting", "/api/projects", "/api/library",
          "/api/storage", "/api/jobs", "/api/settings", "/api/downloads", "/api/update", "/api/knowledge",
          "/api/text?path=CHANGELOG.md", "/api/text?path=docs/plans.md", "/api/prompts"]


def ok(cond, what: str) -> bool:
    print(("PASS  " if cond else "FAIL  ") + what, flush=True)
    if not cond:
        FAILED.append(what)
    return bool(cond)


def compile_all() -> None:
    bad = []
    files = [p for p in TOOLS.rglob("*.py") if "node_modules" not in p.parts and "__pycache__" not in p.parts]
    for p in files:
        try:
            compile(p.read_text(encoding="utf-8"), str(p), "exec")
        except (SyntaxError, UnicodeDecodeError) as e:
            bad.append(f"{p.relative_to(LAB)}: {e}")
    ok(not bad, f"{len(files)} Python files compile" + "".join("\n      " + b for b in bad))


def import_all() -> None:
    import motionlab
    bad = []
    names = ["motionlab"] + [m.name for m in pkgutil.walk_packages(motionlab.__path__, "motionlab.")]
    for name in names:
        try:
            importlib.import_module(name)
        except Exception as e:                                  # noqa: BLE001 - report every broken module
            bad.append(f"{name}: {type(e).__name__}: {e}")
    ok(not bad, f"{len(names)} motionlab modules import" + "".join("\n      " + b for b in bad))


def check_prompts() -> None:
    """The prompt library's paste format, in memory only (nothing is saved)."""
    from motionlab import prompts as P
    try:
        recs = P.parse_paste(P.TEMPLATE + "\nPROMPT 3\nkind: script\nsource: creator: Someone https://example.com/v\n"
                                          "result: okay - too long\ntext:\nHook. Three points. Subscribe.")
        good = ([r["kind"] for r in recs] == ["shot", "hook", "script"] and recs[0]["result"]["rating"] == "good"
                and recs[2]["source"]["link"] == "https://example.com/v" and recs[2]["result"]["rating"] == "ok")
    except ValueError as e:
        good = False
        print("      ", e)
    try:
        P.parse_paste("PROMPT 1\nkind: poem\nsource: tested\ntext:\nx")
        refused = False
    except ValueError:
        refused = True
    ok(good and refused, "prompt library: the paste format parses (and refuses an unknown kind)")


def check_graphics() -> None:
    """Overlay settings (0.3.2): every example declares settings that parse, bad values are refused (read-only)."""
    from motionlab import overlay_settings as OS
    try:
        items = {g["name"]: g for g in OS.library() if g["kind"] == "example"}
        title = items["pixel-title"]
        decl = OS.declared(OS.EXAMPLES / "pixel-title")
        _, bad = OS.check(decl, {"color": "red", "letter_height": 1, "text": "OK"})
        clean, none = OS.check(decl, {"color": "#ABC", "text": "HI", "show_from": "3"})
        good = (len(title["settings"]) >= 5 and len(items["seven-segment-clock"]["settings"]) >= 5 and len(bad) == 2
                and not none and clean == {"color": "#aabbcc", "text": "HI", "show_from": 3}
                and all(g["thumb"] for g in items.values()))
    except (KeyError, ValueError, OSError) as e:
        good = False
        print("      ", type(e).__name__, e)
    ok(good, "graphics: the examples' settings parse, bad values are refused, thumbnails exist")
    from motionlab import captions as CAP
    try:
        lines, _ = CAP.parse_captions("1\n00:00:01,000 --> 00:00:03,000\n[Music] So here is the thing\n\n"
                                      "2\n00:00:03,200 --> 00:00:04,000\nnobody tells you.\n")
        words, est = CAP.words_of(lines)
        cues = CAP.in_frames(CAP.group(words), 25.0)
        srt = CAP.srt(cues, 25.0)
        good = (est and [c["text"] for c in cues] == ["So here is the thing", "nobody tells you."]
                and cues[0]["f0"] == 25 and "00:00:01,000 --> " in srt and cues[1]["words"][-1]["f1"] == cues[1]["f1"])
    except (ValueError, KeyError, IndexError) as e:
        good = False
        print("      ", type(e).__name__, e)
    ok(good, "captions: SRT -> words -> cues (sound tags dropped, the file's lines kept) -> SRT")


def get(base: str, path: str, timeout: float = 60):
    with urllib.request.urlopen(base + path, timeout=timeout) as r:
        return r.status, r.read()


def wait_port(port: int, timeout: float = 30) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:                      # not /api/ping: that is the window's heartbeat
        try:
            socket.create_connection(("127.0.0.1", port), timeout=1).close()
            return True
        except OSError:
            time.sleep(0.3)
    return False


def check_server(base: str) -> list[str]:
    from motionlab import __version__
    st, body = get(base, "/")
    html = body.decode("utf-8", "replace")
    ok(st == 200 and "{{TOKEN}}" not in html and __version__ in html, f"GET / (page of version {__version__})")
    refs: list[str] = []
    for path in ROUTES + ["/api/references?tests=1"]:          # tests=1: the self-test analyses are listed too
        try:
            st, body = get(base, path)
            data = json.loads(body)
            ok(st == 200, f"GET {path}")
            if path == "/api/references?tests=1":
                refs = [r.get("name") for r in data if isinstance(r, dict) and r.get("name")]
        except Exception as e:                                  # noqa: BLE001
            ok(False, f"GET {path}: {type(e).__name__}: {e}")
    test_refs = [r for r in refs if r.startswith("synthetic_")]
    for r in test_refs[:1]:
        try:
            st, body = get(base, "/api/reference/" + r)
            ok(st == 200 and json.loads(body).get("events") is not None, f"GET /api/reference/{r}")
        except Exception as e:                                  # noqa: BLE001
            ok(False, f"GET /api/reference/{r}: {type(e).__name__}: {e}")
    return test_refs[:1]


def check_pages(base: str, test_refs: list[str], cdp_port: int) -> None:
    from cdp import Browser
    b = Browser(port=cdp_port)
    try:
        b.goto(base, settle=2)
        ok(b.wait("document.querySelector('#side a[data-nav]')", timeout=30), "the page starts (sidebar)")
        for h in PAGES + [f"#/ref/{r}" for r in test_refs]:
            b.eval(f"location.hash = {json.dumps(h)}")
            done = b.wait("(() => { const m = document.querySelector('#main'); return m && m.innerText.trim() && "
                          "!m.querySelector('.loading'); })()", timeout=45)
            text = b.text("#main") or ""
            errs = b.eval("window.__errs.splice(0)") or []
            ok(done and "could not load" not in text and not errs,
               f"page {h}" + ("" if done else " (still loading after 45 s)") +
               ("".join("\n      " + str(e) for e in errs)) +
               ("\n      " + text[:300] if "could not load" in text else ""))
    finally:
        b.close()


def check_mcp() -> None:
    r = subprocess.run([PY, str(TOOLS / "mcp_server.py"), "--selftest"], cwd=str(LAB), capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=300)
    ok(r.returncode == 0, "mcp_server.py --selftest" + ("" if r.returncode == 0 else "\n" + (r.stderr or r.stdout)[-1500:]))
    p = subprocess.Popen([PY, str(TOOLS / "mcp_server.py")], cwd=str(LAB), stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
    replies: list[dict] = []

    def reader():
        for line in p.stdout:
            try:
                replies.append(json.loads(line))
            except ValueError:
                pass
    threading.Thread(target=reader, daemon=True).start()

    def send(msg):
        p.stdin.write(json.dumps(msg) + "\n")
        p.stdin.flush()

    def reply(i, timeout=30):
        t0 = time.time()
        while time.time() - t0 < timeout:
            for m in replies:
                if m.get("id") == i:
                    return m
            time.sleep(0.1)
        return None
    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "smoke", "version": "1"}}})
        init = reply(1)
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tools = ((reply(2) or {}).get("result") or {}).get("tools") or []
        ok(init and "result" in init and len(tools) >= 5,
           f"MCP server over stdio: initialize + tools/list ({len(tools)} tools)")
    finally:
        p.kill()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8797)
    ap.add_argument("--cdp-port", type=int, default=9337)
    ap.add_argument("--no-browser", action="store_true", help="skip the headless-Edge page checks")
    args = ap.parse_args()
    from motionlab.util import setup_console
    setup_console()
    compile_all()
    import_all()
    check_prompts()
    check_graphics()
    sj = LAB / ".app" / "server.json"                      # a test server writes it; the user's app reads it
    before = sj.read_bytes() if sj.exists() else None
    srv = subprocess.Popen([PY, str(TOOLS / "app.py"), "--no-window", "--stay", "--no-update", "--port", str(args.port)],
                           cwd=str(LAB))
    try:
        if ok(wait_port(args.port), f"app server listens on 127.0.0.1:{args.port}"):
            base = f"http://127.0.0.1:{args.port}"
            test_refs = check_server(base)
            if not args.no_browser:
                check_pages(base, test_refs, args.cdp_port)
    finally:
        srv.kill()
        srv.wait(timeout=10)
        if before is not None:
            sj.write_bytes(before)
    check_mcp()
    print("\nSMOKE " + ("PASS" if not FAILED else f"FAIL ({len(FAILED)})"))
    return 0 if not FAILED else 1


if __name__ == "__main__":
    sys.exit(main())
