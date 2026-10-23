"""Claude's long steps as the app's jobs (0.5.3): no polling loops, no detached launches by hand, no 10-minute wall.

    .venv\\Scripts\\python tools\\job.py start <kind> key=value ...     e.g. start build project=ae_50_test final=1
          the app running: the job goes into its queue - the Jobs page shows it, the server keeps it alive, What it
          took counts it as the lab's time - prints its id and returns at once. No app: the same command runs on
          its own (a detached runner, HYPERFRAMES_RENDER_DETACHED=1, log in .app\\jobs\\claude_<id>.log)
    .venv\\Scripts\\python tools\\job.py wait <id> [--max 540]
          blocks until the job ends - at most --max seconds, under Claude's 10-minute limit - then prints its last
          lines and the result. Exit 0 = done, 1 = failed or cancelled, 3 = still running: call wait again. Never
          poll in between (sleep / check loops cost turns; wait costs one)
    .venv\\Scripts\\python tools\\job.py list                        the app's jobs and this PC's own ones
Kinds = the app's fixed list (motionlab\\app\\jobs.py `make`): build (project, plan, final, sfx), overlay_render
(project, overlay), draft (project), analyze (video), ... - checked there; nothing else runs.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab.util import LAB, setup_console  # noqa: E402

LOGS = LAB / ".app" / "jobs"
DONE = ("done", "failed", "cancelled")


def server() -> dict | None:
    """The app's server on this PC (.app\\server.json), if it listens - a plain bind probe (app.py free())."""
    try:
        s = json.loads((LAB / ".app" / "server.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    import socket
    with socket.socket() as so:
        try:
            if os.name == "nt":
                so.bind(("127.0.0.1", int(s["port"])))
                return None                                   # nobody listens there
            if so.connect_ex(("127.0.0.1", int(s["port"]))) != 0:
                return None
        except OSError:
            pass
    return s


def call(s: dict, method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(f"http://127.0.0.1:{s['port']}{path}", method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"X-ML-Token": s["token"], "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode("utf-8")).get("error")
        except ValueError:
            msg = str(e)
        raise SystemExit(f"the app refused it: {msg}")


def parse_args(items: list[str]) -> dict:
    out = {}
    for it in items:
        if "=" not in it:
            raise SystemExit(f"key=value (not {it!r})")
        k, v = it.split("=", 1)
        out[k.strip()] = v
    return out


def local_state(jid: str) -> dict:
    return json.loads((LOGS / f"claude_{jid}.json").read_text(encoding="utf-8"))


def start(kind: str, args: dict) -> int:
    s = server()
    if s:
        j = call(s, "POST", "/api/jobs", {"kind": kind, "args": args, "queue": True})
        print(f"job {j['id']} {j['status']} in the app: {j['title']}" + (" (waits its turn)" if j["status"] ==
              "queued" else "") + f"\nwait for it: .venv\\Scripts\\python tools\\job.py wait {j['id']}")
        return 0
    from motionlab.app import jobs as J                     # the same fixed list and checks as the app
    try:
        title, cmd, _ = J.make(kind, args)
    except (J.JobError, ValueError, FileNotFoundError) as e:
        raise SystemExit(f"refused: {e}")
    LOGS.mkdir(parents=True, exist_ok=True)
    jid = f"L{int(time.time()) % 10_000_000}"
    st = {"id": jid, "kind": kind, "args": args, "title": getattr(title, "en", "") or str(title), "cmd": cmd,
          "status": "running", "started": time.time(), "log": str(LOGS / f"claude_{jid}.log")}
    (LOGS / f"claude_{jid}.json").write_text(json.dumps(st, indent=1), encoding="utf-8")
    flags = 0
    if os.name == "nt":            # its own group, no window, out of the shell's job object when Windows allows it
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    env = dict(os.environ, HYPERFRAMES_RENDER_DETACHED="1", MOTIONLAB_JOB=jid, PYTHONUNBUFFERED="1",
               PYTHONIOENCODING="utf-8")
    runner = [sys.executable, str(Path(__file__).resolve()), "_run", jid]
    proc, err = None, ""
    for extra in ((0x01000000,) if os.name == "nt" else ()) + (0,):          # CREATE_BREAKAWAY_FROM_JOB, then without
        try:
            proc = subprocess.Popen(runner, cwd=str(LAB), env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, creationflags=flags | extra, close_fds=True)
            break
        except OSError as e:
            err = str(e)
    if proc is None:                                        # never "running" for a runner that never started
        st.update(status="failed", rc=-1, ended=time.time(), error=f"the runner could not start: {err}")
        (LOGS / f"claude_{jid}.json").write_text(json.dumps(st, indent=1), encoding="utf-8")
        raise SystemExit(f"job {jid}: the runner could not start ({err})")
    st["pid"] = proc.pid
    (LOGS / f"claude_{jid}.json").write_text(json.dumps(st, indent=1), encoding="utf-8")
    print(f"job {jid} started on its own (the app is not running): {st['title']}\n"
          f"wait for it: .venv\\Scripts\\python tools\\job.py wait {jid}")
    return 0


def alive(pid: int | None) -> bool:
    """The runner's process still exists (Windows: OpenProcess + its exit code; never os.kill, which ends it there)."""
    if not pid:
        return False
    if os.name != "nt":
        try:
            os.kill(int(pid), 0)
            return True
        except OSError:
            return False
    import ctypes
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, int(pid))              # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    code = ctypes.c_ulong()
    ok = k.GetExitCodeProcess(h, ctypes.byref(code))
    k.CloseHandle(h)
    return bool(ok) and code.value == 259                   # STILL_ACTIVE


def run(jid: str) -> int:
    """The detached runner: the job's command, its log, its end recorded (What it took) - a final status whatever
    happens (the kind's exit codes that mean done: motionlab.app.jobs OK_RC, build.py's 2 = built with flags)."""
    st = local_state(jid)
    rc = -1
    try:
        with open(st["log"], "w", encoding="utf-8") as f:
            f.write(f"# {st['title']}\n# {' '.join(st['cmd'])}\n")
            f.flush()
            rc = subprocess.call(st["cmd"], cwd=str(LAB), stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    except Exception as e:                                  # noqa: BLE001 - written down, never left "running"
        st["error"] = str(e)
    try:
        from motionlab.app.jobs import OK_RC
    except Exception:                                       # noqa: BLE001
        OK_RC = {}
    st.update(rc=rc, ended=time.time(), status="done" if rc in OK_RC.get(st["kind"], (0,)) else "failed")
    (LOGS / f"claude_{jid}.json").write_text(json.dumps(st, indent=1), encoding="utf-8")
    try:
        from motionlab.app import data as D
        D.record_job(st["kind"], st["title"], st["args"], st["started"], st["ended"], st["status"])
    except Exception:                                       # noqa: BLE001 - the record never fails the job
        pass
    return rc


def wait(jid: str, most: float) -> int:
    t0 = time.time()
    if jid.startswith("L"):
        while True:
            st = local_state(jid)
            if st["status"] in DONE or time.time() - t0 > most:
                break
            if st.get("pid") and not alive(st["pid"]):       # the runner died (sleep, reboot, a killed tree)
                time.sleep(1)
                st = local_state(jid)                         # it may have written its end just now
                if st["status"] not in DONE:
                    st.update(status="failed", ended=time.time(), error="the runner stopped before the job ended")
                    (LOGS / f"claude_{jid}.json").write_text(json.dumps(st, indent=1), encoding="utf-8")
                break
            time.sleep(3)
        try:
            lines = Path(st["log"]).read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            lines = []
        status, secs = st["status"], (st.get("ended") or time.time()) - st["started"]
    else:
        s = server()
        if not s:
            raise SystemExit("the app is not running any more - its jobs ended with it (start the app, start again)")
        while True:
            j = call(s, "GET", f"/api/jobs/{jid}?since=0")
            if j["status"] in DONE or time.time() - t0 > most:
                break
            time.sleep(3)
        lines, status, secs = j.get("log") or [], j["status"], j["seconds"]
    for ln in lines[-14:]:
        print(ln)
    if status not in DONE:
        print(f"job {jid}: still running after {int(secs // 60)}:{int(secs % 60):02d} - "
              f".venv\\Scripts\\python tools\\job.py wait {jid}")
        return 3
    print(f"job {jid}: {status} in {int(secs // 60)}:{int(secs % 60):02d}")
    return 0 if status == "done" else 1


def main() -> int:
    setup_console()
    av = sys.argv[1:]
    if not av or av[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if av[0] == "start" and len(av) >= 2:
        return start(av[1], parse_args(av[2:]))
    if av[0] == "_run" and len(av) == 2:
        return run(av[1])
    if av[0] == "wait" and len(av) >= 2:
        most = float(av[av.index("--max") + 1]) if "--max" in av else 540.0
        return wait(av[1], min(most, 570.0))
    if av[0] == "list":
        s = server()
        for j in (call(s, "GET", "/api/jobs") if s else []):
            print(f"  {j['id']:>5}  {j['status']:9s} {j['seconds']:7.0f} s  {j['title']}")
        for p in sorted(LOGS.glob("claude_L*.json"))[-10:]:
            st = json.loads(p.read_text(encoding="utf-8"))
            print(f"  {st['id']:>5}  {st['status']:9s} {(st.get('ended') or time.time()) - st['started']:7.0f} s  "
                  f"{st['title']} (on its own)")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
