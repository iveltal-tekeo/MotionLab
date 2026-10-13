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
PAGES = ["#/", "#/analyze", "#/edit", "#/generate", "#/prompts", "#/memory", "#/memory/saved", "#/jobs", "#/skills",
         "#/storage", "#/settings",
         "#/refs", "#/projects", "#/library", "#/knowledge"]              # 0.3 addresses: still work (rewritten)
ROUTES = ["/api/status", "/api/references", "/api/candidates", "/api/waiting", "/api/projects", "/api/library",
          "/api/storage", "/api/jobs", "/api/skills", "/api/settings", "/api/downloads", "/api/update", "/api/knowledge",
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
    # 0.3.3: any text, no format (0.3.2 said "prompt 1: no 'text:' line"); the kind is guessed; .docx files are read
    import tempfile
    import zipfile
    try:
        one = P.parse_paste("Nobody tells you this about editing.")
        two = P.parse_paste("A chef in slow motion, the camera dollies in, 50mm\n---\nPortrait photo, studio light, 8k")
        old = P.parse_paste("PROMPT 1\nkind: hook\nsource: tested by me\nNobody tells you this.")
        creator = P.parse_paste("x y z", "script", {"type": "creator", "creator": "Ana", "link": ""}, "guide.pdf")
        good = ([(r["kind"], r["source"]) for r in one] == [("hook", {"type": "tested"})]
                and [r["kind"] for r in two] == ["shot", "image"] and old[0]["text"] == "Nobody tells you this."
                and creator[0]["kind"] == "script" and creator[0]["source"]["file"] == "guide.pdf"
                and P.guess_kind("Hey guys, today I show you why most people quit editing. " * 8) == "script")
        W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "guide.docx"
            with zipfile.ZipFile(d, "w") as z:
                z.writestr("word/document.xml", f"<w:document {W}><w:body><w:p><w:r><w:t>Line one</w:t></w:r></w:p>"
                                                "<w:p><w:r><w:t>Line</w:t><w:tab/><w:t>two</w:t></w:r></w:p></w:body></w:document>")
            good = good and P.file_text(d) == "Line one\nLine\ttwo"
    except ValueError as e:
        good = False
        print("      ", e)
    try:
        P.parse_paste(" \n---\n ")
        refused = False
    except ValueError:
        refused = True
    ok(good and refused, "prompt library: any pasted text saves (kind guessed, --- separates), .docx text is read")
    # 0.3.4: a brief for Claude (make / edit a whole video) is its own kind; Claude's check = slots with a status
    brief_es = ("Quiero que crees una linea de tiempo en da vinci resolve y edites el video al estilo vlog con un mismo "
                "lut, elimina silencios, añade b-roll, efectos de sonido y música, cortes dinámicos, 10-15 minutos")
    brief_en = "Edit my Paris vlog in DaVinci Resolve: 8 minutes, fast cuts, a warm LUT, whoosh SFX, captions, music."
    rec = {"kind": "brief", "text": "x", "source": {"type": "tested"}, "result": {},
           "structure": [{"slot": "colour", "text": "one LUT", "status": "vague", "tip": "pick one"},
                         {"slot": "sfx", "text": "", "status": "missing"}], "wishes": {"colour": "one warm LUT"}}
    try:
        P._check(rec)
        P._check({**rec, "structure": [{"slot": "sfx", "text": "", "status": "maybe"}]})
        statuses = False
    except ValueError:
        statuses = True
    try:
        P._check({**rec, "wishes": ["not", "a", "map"]})
        wishes = False
    except ValueError:
        wishes = True
    ok(P.guess_kind(brief_es) == "brief" and P.guess_kind(brief_en) == "brief" and "brief" in P.KINDS
       and len(P.SLOTS["brief"]) >= 12 and statuses and wishes,
       "prompt library: briefs for Claude are their own kind; the check's clear / vague / missing and wishes validate")
    # 0.3.5: "al estilo vlog de Clavero" finds the Clavero video the user analysed (creator first, accents ignored);
    # its measured style reaches Claude with the check and the wishes (MCP prompts(id) / prompts.py show)
    from motionlab import knowledge as KN
    fake = [{"name": "Clavero_Londres", "title": "UN DÍA EN LONDRES | Clavero", "uploader": "Jaime Clavero"},
            {"name": "Osmo_review", "title": "Osmo Pocket 3 review", "uploader": "TechGuy"},
            {"name": "NEMZZZ_4AM", "title": "NEMZZZ - 4AM [OFFICIAL VIDEO]", "uploader": None}]
    sug = P.suggest_refs("Edita Londres Día 1 al estilo vlog de CLAVERO con la Osmo Pocket 3", fake)
    title_only = P.suggest_refs("a music video like nemzzz", fake)
    bad_refs = 0
    for refs in (["../x"], ["a b"], [f"r{i}" for i in range(6)], "Clavero"):
        try:
            P._check({**rec, "style_refs": refs})
        except ValueError:
            bad_refs += 1
    txt = P.describe({**rec, "id": "brief-999", "style_refs": []}, full=True)
    st = KN.style("synthetic_test") if (KN.ANALYSIS / "synthetic_test" / "events.json").exists() else {"line": "cuts/min"}
    ok([x["name"] for x in sug] == ["Clavero_Londres"] and sug[0]["why"] == "made by Jaime Clavero"
       and [x["name"] for x in title_only] == ["NEMZZZ_4AM"] and not P.suggest_refs("a cooking talking head", fake)
       and bad_refs == 4 and "colour: vague - one LUT - tip: pick one" in txt and "colour: one warm LUT" in txt
       and st and "cuts/min" in st["line"] and KN.style("../analysis") is None,
       "prompt library: a style reference - the analysed video a prompt names is found, measured and handed to Claude")
    # 0.3.4 navigation: cards show only the title -> a readable automatic one until Claude's check titles it; the
    # pictures / clips of what a prompt makes are plain file names in examples\
    bad_ex = 0
    for ex in (["../x.jpg"], ["a\\b.jpg"], "x.jpg"):
        try:
            P._check({**rec, "examples": ex})
        except ValueError:
            bad_ex += 1
    london = ("Quiero que Londres\\Día 1 crees una linea de tiempo en da vinci resolve y edites el video al estilo vlog de "
              "clavero, con un mismo lut")
    ok(P.auto_title(london, "brief") == "Londres Día 1 · vlog · estilo Clavero"
       and P.auto_title("I want you to create a slow dolly-in on a chef at night: 50mm, neon", "shot") == "A slow dolly-in on a chef at night"
       and P.auto_title("@video1: ", "shot") == "Untitled prompt" and bad_ex == 3
       and "brief" in P.SLOTS and {"effects", "voice & audio", "ending"} <= set(P.SLOTS["brief"]),
       "prompt library: automatic titles name the prompt; a brief's check covers effects, voice & audio, the ending")


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
