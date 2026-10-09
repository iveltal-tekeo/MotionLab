"""DaVinci Resolve for Claude Code over MCP: the community server samuelgursky/davinci-resolve-mcp (MIT, 37 compound
tools over Resolve's scripting API), pinned, set up on THIS PC only - Claude Code "local" scope = this lab folder and
this Windows user, never in the repo (its paths differ per PC). Optional; needs DaVinci Resolve Studio with
Preferences > System > General > External scripting using = Local.

    .venv\\Scripts\\python tools\\resolve_mcp.py install   npx davinci-resolve-mcp@<PINNED> setup --clients manual
                                                         (its own venv in %LOCALAPPDATA%\\davinci-resolve-mcp, no
                                                         self-updates), safe mode ON (high-risk actions are refused
                                                         unless explicitly allowed; JSONL audit log in .app\\), then
                                                         claude mcp add-json --scope local davinci-resolve ...
    .venv\\Scripts\\python tools\\resolve_mcp.py status    installed? registered with Claude Code? Resolve running?
    .venv\\Scripts\\python tools\\resolve_mcp.py remove    unregister from Claude Code (the managed copy stays; delete
                                                         %LOCALAPPDATA%\\davinci-resolve-mcp to remove it too)
How Claude uses it in MotionLab (look, don't rebuild): docs\\resolve_notes.md, section "Resolve MCP". Claude Code
loads it in the next chat started in this folder (approve it once if asked).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab.util import LAB, log, setup_console  # noqa: E402

PINNED = "4.9.2"                                   # davinci-resolve-mcp version (checked 2026-10-09)
NAME = "davinci-resolve"
ROOT = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "davinci-resolve-mcp"
APP = LAB / ".app" / "resolve_mcp"
API = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Blackmagic Design" / "DaVinci Resolve" / "Support" / \
    "Developer" / "Scripting"
LIB = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Blackmagic Design" / "DaVinci Resolve" / \
    "fusionscript.dll"
PREFS = {"destructive": {"safe_mode": True, "require_confirm_token": True, "audit_log": True,
                         "audit_log_path": str(APP / "security-audit.jsonl"), "operation_log": True,
                         "operation_log_path": str(APP / "operation-log.jsonl")}}


def base_python() -> str:
    """The Python the lab's .venv was made from (3.12) - the server's own venv is built on it."""
    exe = getattr(sys, "_base_executable", None) or sys.executable
    return str(Path(exe).resolve())


def which(name: str) -> str:
    exe = shutil.which(name)
    if not exe:
        raise SystemExit(f"{name} not found - " + {"npx": "install Node.js (winget install OpenJS.NodeJS.LTS)",
                                                    "claude": "install Claude Code"}.get(name, name))
    return exe


def server_entry() -> dict:
    py = ROOT / "venv" / "Scripts" / "python.exe"
    srv = ROOT / "src" / "server.py"
    if not py.exists() or not srv.exists():
        raise SystemExit(f"the server is not installed in {ROOT} - run: resolve_mcp.py install")
    home = subprocess.run([str(py), "-c", "import sys; print(sys.base_prefix)"], capture_output=True,
                          text=True).stdout.strip()
    env = {"RESOLVE_SCRIPT_API": str(API), "RESOLVE_SCRIPT_LIB": str(LIB), "PYTHONPATH": str(API / "Modules"),
           "PYTHONHOME": home, "DAVINCI_RESOLVE_MCP_MEDIA_ANALYSIS_PREFS": str(APP / "preferences.json"),
           "DAVINCI_RESOLVE_MCP_UPDATE_MODE": "never"}
    return {"type": "stdio", "command": str(py), "args": [str(srv)], "env": env}


def claude(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    r = subprocess.run([which("claude"), "mcp", *args], cwd=str(LAB), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and r.returncode:
        raise SystemExit(f"claude mcp {args[0]} failed: {(r.stderr or r.stdout).strip()[-500:]}")
    return r


def registered() -> bool:
    return claude("get", NAME, check=False).returncode == 0


def cmd_install(a) -> int:
    if not LIB.exists():
        raise SystemExit(f"DaVinci Resolve not found ({LIB}) - the Resolve MCP needs DaVinci Resolve Studio")
    log(f"installing davinci-resolve-mcp {PINNED} into {ROOT} (its own venv on {base_python()})")
    env = {**os.environ, "DAVINCI_RESOLVE_MCP_PYTHON": base_python(), "DAVINCI_RESOLVE_MCP_UPDATE_MODE": "never"}
    r = subprocess.run([which("npx"), "-y", f"davinci-resolve-mcp@{PINNED}", "setup", "--clients", "manual",
                        "--update-policy", "never"], cwd=str(APP.parent), env=env, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode:
        raise SystemExit(f"setup failed (exit {r.returncode}) - see above")
    APP.mkdir(parents=True, exist_ok=True)
    prefs = APP / "preferences.json"
    old = json.loads(prefs.read_text(encoding="utf-8")) if prefs.exists() else {}
    prefs.write_text(json.dumps({**old, **PREFS}, indent=1), encoding="utf-8")
    entry = server_entry()
    if registered():
        claude("remove", NAME, "--scope", "local", check=False)
    claude("add-json", NAME, json.dumps(entry), "--scope", "local")
    (APP / "registered.json").write_text(json.dumps({"name": NAME, "version": PINNED, "lab": str(LAB),
                                                     "when": time.strftime("%Y-%m-%d %H:%M")}, indent=1),
                                         encoding="utf-8")
    log(f"registered '{NAME}' with Claude Code for {LAB} (local scope); safe mode on ({prefs})")
    print("Start a NEW Claude Code chat in the lab folder to use it (approve the server if Claude Code asks).")
    return 0


def cmd_status(a) -> int:
    print(f"server   {'installed' if (ROOT / 'src' / 'server.py').exists() else 'not installed'} ({ROOT})")
    try:
        print(f"claude   {'registered (local scope)' if registered() else 'not registered'} as '{NAME}'")
    except SystemExit as e:
        print("claude  ", e)
    prefs = APP / "preferences.json"
    if prefs.exists():
        d = json.loads(prefs.read_text(encoding="utf-8")).get("destructive", {})
        print(f"safety   safe_mode={d.get('safe_mode')} confirm_token={d.get('require_confirm_token')} "
              f"audit_log={d.get('audit_log_path')}")
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "(Get-Process Resolve -ErrorAction SilentlyContinue | Select-Object -First 1).Responding"],
                         capture_output=True, text=True).stdout.strip()
    print("resolve ", {"True": "running", "False": "not responding"}.get(out, "not running"))
    return 0


def cmd_remove(a) -> int:
    if registered():
        claude("remove", NAME, "--scope", "local")
        print(f"unregistered '{NAME}' from Claude Code ({LAB}); the managed copy stays in {ROOT}")
    else:
        print("not registered")
    (APP / "registered.json").unlink(missing_ok=True)
    return 0


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["install", "status", "remove"])
    a = ap.parse_args()
    return {"install": cmd_install, "status": cmd_status, "remove": cmd_remove}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
