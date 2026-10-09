"""Long tasks started from the app. Each job is one of the lab's own tools (or yt-dlp for a download) run as a child
process (no console window), its output kept for the Jobs page and in .app\\jobs\\<id>.log. Only the kinds in `make`
exist: the app cannot run arbitrary commands. One job at a time per group (cpu / resolve / light / net).
"Analyse with Claude" = an analyze job with claude=true: when the lab pass ends well, Claude Code opens with
/analyze-reference for that video (the user's click started it; Claude spends nothing while the pass runs)."""
from __future__ import annotations

import itertools
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from motionlab.styles import CATEGORIES, LEGACY, clean_tags
from motionlab.util import ANALYSIS, LAB

from . import data, system

TOOLS = LAB / "tools"
LOGS = LAB / ".app" / "jobs"
_PY = Path(sys.executable)
PY = str(_PY.with_name("python.exe")) if _PY.name.lower() == "pythonw.exe" else str(_PY)
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class JobError(ValueError):
    pass


def _latest_plan(project: str) -> Path:
    b = data.PROJECTS / data.safe_name(project) / "build"
    plans = sorted(b.glob("plan_v*.json"), key=lambda p: int(p.stem.split("_v")[-1]) if p.stem.split("_v")[-1].isdigit()
                   else 0)
    if not plans:
        raise JobError(f"project {project} has no plan_vN.json")
    return plans[-1]


def make(kind: str, a: dict) -> tuple[str, list[str], str]:
    """(title, command, group) for a job kind; validates every argument."""
    if kind == "analyze":
        v = Path(str(a.get("video", ""))).expanduser()
        if not v.is_file() or v.suffix.lower() not in data.VIDEO_EXT:
            raise JobError(f"not a video file: {v}")
        if LAB in v.resolve().parents and v.resolve().parts[len(LAB.parts)] in ("analysis", ".app", "tools"):
            raise JobError("pick the original video, not a file the lab made")
        cat = str(a.get("category") or a.get("style") or "")
        extra = []
        if cat:
            if cat not in CATEGORIES and cat not in LEGACY:
                raise JobError(f"unknown category {cat}")
            system.save({"default_category": cat})          # the dialog offers it again next time
            extra += ["--category", cat]
        if "tags" in a:
            extra += ["--tags", ", ".join(clean_tags(a.get("tags") or ""))]
        return f"Analyse {v.name}", [PY, str(TOOLS / "analyze.py"), str(v)] + (
            ["--redetect"] if a.get("redetect") else []) + extra, "cpu"
    if kind == "report":
        n = data.safe_name(str(a.get("name", "")))
        if not (ANALYSIS / n / "events.json").exists():
            raise JobError(f"no analysis {n}")
        return f"Rebuild report {n}", [PY, str(TOOLS / "report.py"), n], "light"
    if kind in ("resolve_doctor", "resolve_diff"):
        plan = _latest_plan(str(a.get("project", "")))
        flag = "--doctor" if kind == "resolve_doctor" else "--diff"
        what = "Resolve check-up" if kind == "resolve_doctor" else "Resolve: what changed by hand"
        return f"{what} ({a['project']})", [PY, str(TOOLS / "resolve_build.py"), str(plan), flag], "resolve"
    if kind == "storage":
        return "Storage report", [PY, str(TOOLS / "storage.py")], "light"
    if kind == "prune":
        target = str(a.get("target", ""))
        if target not in ("all", "selftest"):
            data.safe_name(target)
        what = [w for w in a.get("what", ["cache"]) if w in ("cache", "checks", "finals")] or ["cache"]
        yes = bool(a.get("yes"))
        return (f"{'Free space' if yes else 'Dry run: free space'} ({target}: {', '.join(what)})",
                [PY, str(TOOLS / "storage.py"), "--prune", target, "--what", ",".join(what)] + (["--yes"] if yes else []),
                "exclusive" if yes else "light")
    if kind == "selftest":
        return "Self-test (extended)", [PY, str(TOOLS / "selftest.py"), "--extended"], "cpu"
    if kind == "overlays_install":                                 # Settings > Programs > HyperFrames > Install
        return "Install HyperFrames (HTML overlays)", [PY, str(TOOLS / "overlay.py"), "install"], "net"
    if kind in ("resolve_mcp_install", "resolve_mcp_remove"):      # Settings > Claude Code > DaVinci Resolve (MCP)
        install = kind == "resolve_mcp_install"
        return ("Connect Claude Code to DaVinci Resolve (MCP)" if install else "Disconnect the Resolve MCP",
                [PY, str(TOOLS / "resolve_mcp.py"), "install" if install else "remove"], "net")
    if kind == "download":              # yt-dlp: one video into refs\ + its source in refs\downloads.json
        title, _ = system.download_cmd(str(a.get("url", "")), str(a.get("preset", "")))      # validates everything
        return title, [PY, str(TOOLS / "download.py"), str(a["url"]).strip(), str(a.get("preset", ""))], "net"
    if kind == "verify_timing":
        p = data.safe_name(str(a.get("project", "")))
        b = data.PROJECTS / p / "build"
        render = data.safe_name(str(a.get("render", "")))
        if not (b / "verify_timing.py").exists() or not (b / f"{render}.mp4").exists():
            raise JobError(f"{p}: no verify_timing.py or no {render}.mp4")
        return f"Timing check {render}", [PY, str(b / "verify_timing.py"), render], "cpu"
    raise JobError(f"unknown job kind {kind!r}")


class Job:
    def __init__(self, jid: int, kind: str, args: dict, title: str, cmd: list[str], group: str):
        self.id, self.kind, self.args, self.title, self.cmd, self.group = jid, kind, args, title, cmd, group
        self.status, self.rc = "running", None
        self.started, self.ended = time.time(), None
        self.lines: list[str] = []
        self.proc: subprocess.Popen | None = None
        self.log = LOGS / f"{jid:04d}_{kind}.log"
        self.then_claude = kind == "analyze" and bool(args.get("claude"))      # open Claude when it ends well
        self.claude: dict | None = None                                         # what was opened afterwards

    def info(self, since: int | None = None) -> dict:
        d = {"id": self.id, "kind": self.kind, "args": self.args, "title": self.title, "group": self.group,
             "status": self.status, "rc": self.rc, "started": data.stamp(self.started),
             "seconds": round((self.ended or time.time()) - self.started, 1),
             "command": " ".join(Path(c).name if i < 2 else c for i, c in enumerate(self.cmd)),
             "lines": len(self.lines), "then_claude": self.then_claude, "claude": self.claude}
        if since is not None:
            d["log"] = self.lines[since:since + 5000]
            d["since"] = since
        return d


class Runner:
    def __init__(self):
        self.jobs: dict[int, Job] = {}
        self.ids = itertools.count(1)
        self.lock = threading.Lock()

    def running(self) -> list[Job]:
        return [j for j in self.jobs.values() if j.status in ("running", "cancelling")]

    def start(self, kind: str, args: dict) -> Job:
        title, cmd, group = make(kind, args or {})
        with self.lock:
            busy = self.running()
            if group == "exclusive" and busy:
                raise JobError("wait until the running jobs finish")
            clash = [j for j in busy if j.group in (group, "exclusive")]
            if clash:
                raise JobError(f"'{clash[0].title}' is still running")
            job = Job(next(self.ids), kind, args or {}, title, cmd, group)
            self.jobs[job.id] = job
        LOGS.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
        job.proc = subprocess.Popen(cmd, cwd=str(LAB), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
                                    env=env, creationflags=NO_WINDOW)
        threading.Thread(target=self._pump, args=(job,), daemon=True).start()
        return job

    def _pump(self, job: Job):
        with open(job.log, "w", encoding="utf-8") as f:
            f.write(f"# {job.title}\n# {' '.join(job.cmd)}\n")
            for line in job.proc.stdout:
                line = line.rstrip("\r\n")
                job.lines.append(line)
                if len(job.lines) > 20000:
                    del job.lines[:5000]
                f.write(line + "\n")
                f.flush()
            job.rc = job.proc.wait()
            job.ended = time.time()
            job.status = "cancelled" if job.status == "cancelling" else ("done" if job.rc == 0 else "failed")
            if job.then_claude and job.status == "done":
                self._hand_to_claude(job, f)

    @staticmethod
    def _hand_to_claude(job: Job, f) -> None:
        """'Analyse with Claude': the lab pass is done - open Claude Code to check every effect of it."""
        rep = next((ln.split("REPORT:", 1)[1].strip() for ln in reversed(job.lines) if ln.startswith("REPORT:")), "")
        analysis = Path(rep).parent.name if rep else None
        video = str(Path(str(job.args.get("video", ""))).expanduser())
        try:
            job.claude = system.open_claude(data.review_prompt(video, analysis), "review", Path(video).stem)
            msg = f"Claude Code opened to check every effect ({job.claude['prompt']})"
        except Exception as e:                                  # noqa: BLE001 - the pass itself succeeded
            job.claude = {"ok": False, "error": str(e)}
            msg = f"Could not open Claude Code: {e} - open it from the reference's page (Send to Claude)"
        job.lines.append(msg)
        f.write(msg + "\n")

    def cancel(self, jid: int) -> Job:
        job = self.jobs.get(jid)
        if not job:
            raise JobError(f"no job {jid}")
        if job.status == "running" and job.proc:
            job.status = "cancelling"
            job.proc.terminate()
        return job

    def list(self) -> list[dict]:
        return [j.info() for j in sorted(self.jobs.values(), key=lambda j: -j.id)]
