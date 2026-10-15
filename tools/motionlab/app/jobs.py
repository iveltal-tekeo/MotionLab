"""Long tasks started from the app. Each job is one of the lab's own tools (or yt-dlp for a download) run as a child
process (no console window), its output kept for the Jobs page and in .app\\jobs\\<id>.log. Only the kinds in `make`
exist: the app cannot run arbitrary commands. One job at a time per group (cpu / resolve / light / net); since 0.4 a
job can wait its turn ("queued", Analyze > Add videos: several videos at once) and a download can be followed by its
analysis (`then`: the saved video is analysed with those settings). "Analyse with Claude" = an analyze job with
claude=true: when the lab pass ends well, Claude Code opens with /analyze-reference for that video (the user's click
started it; Claude spends nothing while the pass runs)."""
from __future__ import annotations

import itertools
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

from motionlab import overlay_settings as OS
from motionlab.styles import CATEGORIES, FOCUS, LEGACY, clean_tags
from motionlab.util import ANALYSIS, LAB

from . import data, system

TOOLS = LAB / "tools"
LOGS = LAB / ".app" / "jobs"
JOBTOOLS = Path(__file__).resolve().parent / "jobtools.py"       # the app's own small jobs (yt-dlp update, player copy)
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
        focus = str(a.get("focus") or "")
        if focus:
            if focus not in FOCUS:
                raise JobError(f"unknown focus {focus} (content, cinematic or both)")
            extra += ["--focus", focus]
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
    if kind in ("content_transcript", "content_stats"):         # analysis page > Content (0.3.5)
        n = data.safe_name(str(a.get("name", "")))
        if not (ANALYSIS / n / "events.json").exists():
            raise JobError(f"no analysis {n}")
        if kind == "content_transcript":
            return (f"Transcript of {n}", [PY, str(TOOLS / "content.py"), "transcript", n]
                    + (["--force"] if a.get("again") else []), "net")
        return f"Views and followers of {n}", [PY, str(TOOLS / "content.py"), "stats", n], "net"
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
    if kind == "overlays_upgrade_test":            # Settings > Programs > HyperFrames > Test it (scratch install)
        return ("Test the newest HyperFrames + GSAP on the overlay examples",
                [PY, str(TOOLS / "overlay.py"), "upgrade-test", "--gsap", "latest"], "cpu")
    if kind in ("overlay_render", "overlay_save"):                 # Videos > Graphics: Render / Save to library
        f = data.overlay_folder(str(a.get("project", "")), str(a.get("overlay", "")))
        if kind == "overlay_render":
            return f"Render the graphic {f.name} ({a['project']})", [PY, str(TOOLS / "overlay.py"), "render", str(f)], "cpu"
        name = str(a.get("name") or f.name)
        if not re.fullmatch(r"[\w.-]+", name):
            raise JobError(f"not a usable name: {name!r} (letters, digits, - _ .)")
        return (f"Save the graphic {f.name} to the library as {name}",
                [PY, str(TOOLS / "overlay.py"), "save", str(f), "--name", name] + (["--force"] if a.get("replace") else []),
                "light")
    if kind in ("overlay_refresh", "overlay_resolve_clip"):    # Videos > Graphics > DaVinci Resolve
        f = data.overlay_folder(str(a.get("project", "")), str(a.get("overlay", "")))
        if kind == "overlay_refresh":
            return (f"Swap the graphic {f.name} in DaVinci Resolve", [PY, str(TOOLS / "overlay.py"), "refresh", str(f)],
                    "resolve")
        return f"A clip of {f.name} for DaVinci Resolve", [PY, str(TOOLS / "overlay.py"), "resolve-clip", str(f)], "light"
    if kind == "overlay_captions":           # Videos > Graphics > Captions (a subtitle file, or a video's words)
        p = data.safe_name(str(a.get("project", "")))
        src = Path(str(a.get("file", "")).strip().strip('"')).expanduser()
        speech = src.suffix.lower() in data.VIDEO_EXT or src.suffix.lower() in (".wav", ".mp3", ".m4a", ".aac")
        if not src.is_file() or not (speech or src.suffix.lower() in (".srt", ".vtt", ".json")):
            raise JobError(f"not a subtitle file (.srt / .vtt / a lab transcript.json) or a video: {src}")
        if speech:
            from motionlab import speech as SP
            if not SP.available():
                raise JobError("speech to text is not installed: Settings > Programs > Speech to text > Install")
        else:
            _latest_plan(p)                                         # rate / size / length come from the edit plan
        extra = []
        if speech:
            model = str(a.get("model") or "small")
            if model not in ("small", "base"):
                raise JobError(f"unknown model {model}")
            names = re.sub(r"[\r\n\"]", " ", str(a.get("names") or ""))[:300]
            extra = ["--model", model] + (["--names", names] if names.strip() else [])
        name = str(a.get("name") or "captions")
        if not re.fullmatch(r"[\w.-]+", name):
            raise JobError(f"not a usable name: {name!r} (letters, digits, - _ .)")
        dst = data.PROJECTS / p / "build" / "overlays" / name
        if dst.exists() and not (OS.conf(dst).get("captions")):
            raise JobError(f"{p} already has a graphic called {name} that is not captions: pick another name")
        return (f"Captions for {p} from {src.name}" + (" (speech to text)" if speech else ""),
                [PY, str(TOOLS / "overlay.py"), "captions", str(dst), "--from", str(src), "--render", *extra], "cpu")
    if kind == "speech_install":                               # Settings > Programs > Speech to text > Install
        return "Install speech to text (faster-whisper + the small model)", [PY, str(TOOLS / "speech.py"), "install"], "net"
    if kind == "overlay_new":                       # Library > Graphics > Use in a video: a copy, rendered right away
        p = data.safe_name(str(a.get("project", "")))
        if not (data.PROJECTS / p).is_dir():
            raise JobError(f"no video project {p}")
        graphic = str(a.get("graphic", ""))
        OS.find_graphic(graphic)                                    # ValueError when it does not exist
        name = str(a.get("name") or graphic)
        if not re.fullmatch(r"[\w.-]+", name):
            raise JobError(f"not a usable name: {name!r} (letters, digits, - _ .)")
        dst = data.PROJECTS / p / "build" / "overlays" / name
        if dst.exists():
            raise JobError(f"{p} already has a graphic called {name}: pick another name")
        return (f"Add the graphic {graphic} to {p} as {name}",
                [PY, str(TOOLS / "overlay.py"), "new", str(dst), "--from", graphic, "--render"], "cpu")
    if kind in ("resolve_mcp_install", "resolve_mcp_remove"):      # Settings > Claude Code > DaVinci Resolve (MCP)
        install = kind == "resolve_mcp_install"
        return ("Connect Claude Code to DaVinci Resolve (MCP)" if install else "Disconnect the Resolve MCP",
                [PY, str(TOOLS / "resolve_mcp.py"), "install" if install else "remove"], "net")
    if kind == "download":              # yt-dlp: one video into refs\ + its source in refs\downloads.json
        title, _ = system.download_cmd(str(a.get("url", "")), str(a.get("preset", "")))      # validates everything
        return title, [PY, str(TOOLS / "download.py"), str(a["url"]).strip(), str(a.get("preset", ""))], "net"
    if kind in ("thumbs_fetch", "thumbs_links", "thumbs_measure", "thumbs_more", "thumbs_refresh"):   # Analyser (0.4.5)
        s = data.safe_name(str(a.get("set", "")))
        if not s.strip(" ."):
            raise JobError("name the set")
        tool = [PY, str(TOOLS / "thumbsets.py")]
        order = str(a.get("order") or "newest")
        if order not in ("newest", "views"):
            raise JobError("the newest or the most viewed")
        if kind == "thumbs_refresh":                  # the set's page: the newest views, dates and lengths
            return f"The numbers of {s} again", tool + ["refresh", s], "net"
        if kind == "thumbs_more":                     # the set's page: the next batch of its channel
            n = int(a.get("n") or 20)
            if not 1 <= n <= 100:
                raise JobError("1 to 100 more thumbnails")
            return f"{n} more thumbnails for {s}", tool + ["more", s, "--n", str(n), "--order", order], "net"
        if kind == "thumbs_fetch":
            url, n, label = str(a.get("url", "")).strip(), int(a.get("n") or 15), " ".join(str(a.get("label") or "").split())[:80]
            if not re.fullmatch(r"https?://[^\s\"'<>|^`]{4,2000}", url):
                raise JobError("paste a full channel or playlist link starting with https://")
            if not 1 <= n <= 100:
                raise JobError("1 to 100 thumbnails")
            return (f"Thumbnails of {label or s}", tool + ["fetch", s, url, "--n", str(n), "--order", order]
                    + (["--label", label] if label else []), "net")
        if kind == "thumbs_links":
            urls = [str(u).strip() for u in a.get("urls") or [] if str(u).strip()]
            if not 1 <= len(urls) <= 60 or any(not re.fullmatch(r"https?://[^\s\"'<>|^`]{4,2000}", u) for u in urls):
                raise JobError("1 to 60 video links, each starting with https://")
            return f"Thumbnails for {s}", tool + ["links", s, *urls], "net"
        return f"Measure the thumbnails of {s}", tool + ["measure", s], "light"
    if kind == "colour":                         # an analysis' Overview > Measure the colour (0.4): no decoding
        n = data.safe_name(str(a.get("name", "")))
        if not (ANALYSIS / n / "events.json").exists():
            raise JobError(f"no analysis {n}")
        return f"Colour of {n}", [PY, str(TOOLS / "colour.py"), n], "light"
    if kind == "draft":             # Edit > New edit > Quick draft (0.4): build\\edit_request.json -> draft_edit.py
        p = data.safe_name(str(a.get("project", "")))
        if not (data.PROJECTS / p).is_dir():
            raise JobError(f"no project {p}")
        try:
            extra = data.draft_args(data.edit_request(p))
        except (FileNotFoundError, ValueError) as e:
            raise JobError(str(e))
        return f"Quick draft of {p}", [PY, str(TOOLS / "draft_edit.py"), p] + extra + ["--render"], "cpu"
    if kind == "verify_timing":
        p = data.safe_name(str(a.get("project", "")))
        b = data.PROJECTS / p / "build"
        render = data.safe_name(str(a.get("render", "")))
        if not (b / "verify_timing.py").exists() or not (b / f"{render}.mp4").exists():
            raise JobError(f"{p}: no verify_timing.py or no {render}.mp4")
        return f"Timing check {render}", [PY, str(b / "verify_timing.py"), render], "cpu"
    if kind == "ytdlp_update":          # Settings > Programs > Update yt-dlp (0.4.2.1); dry_run = print, run nothing
        if not system.find("yt-dlp"):
            raise JobError("yt-dlp not found - " + system.HOW["yt-dlp"])
        dry = bool(a.get("dry_run"))
        return (("Dry run: " if dry else "") + "Update yt-dlp",
                [PY, str(JOBTOOLS), "ytdlp-update"] + (["--dry-run"] if dry else []), "net")
    if kind == "player_copy":           # the player cannot play a video (HEVC / AV1 ...): an H.264 copy for it only
        rel = str(a.get("path", "")).replace("\\", "/").lstrip("/")
        src = (LAB / rel).resolve()
        if LAB not in src.parents or src.relative_to(LAB).parts[0] not in ("analysis", "projects", "refs") \
                or not src.is_file() or src.suffix.lower() not in data.VIDEO_EXT:
            raise JobError(f"not a video of the lab: {rel}")
        return f"A copy of {src.name} that plays here", [PY, str(JOBTOOLS), "player-copy", str(src)], "cpu"
    if kind.startswith("thumb_"):           # Edit > a video > Publish (0.4.3): tools\\thumbnail.py, build\\publish\\ only
        return _thumb_job(kind, a)
    raise JobError(f"unknown job kind {kind!r}")


THUMB_TEXT = re.compile(r"[^\r\n\"]{1,200}")


def _thumb_job(kind: str, a: dict) -> tuple[str, list[str], str]:
    """thumb_candidates (good moments: the clips, or the newest render), thumb_make (a template + a frame or a picture +
    2-4 words -> thumbnail A / B / C, HyperFrames stills, then its check), thumb_render (again after its settings
    changed), thumb_check (every thumbnail, with the title) - all group cpu, queued like the others."""
    p = data.safe_name(str(a.get("project", "")))
    if not (data.PROJECTS / p).is_dir():
        raise JobError(f"no video project {p}")
    T = [PY, str(TOOLS / "thumbnail.py")]
    if kind == "thumb_candidates":
        n = int(a.get("n") or 12)
        if not 4 <= n <= 24:
            raise JobError("between 4 and 24 moments")
        return (f"Good moments for a thumbnail ({p})", T + ["candidates", p, "--n", str(n)]
                + (["--render"] if a.get("render") else []), "cpu")
    tid = str(a.get("id") or "")
    if kind in ("thumb_make", "thumb_render") and not re.fullmatch(r"[A-Z]", tid):
        raise JobError("a thumbnail is A, B or C")
    if kind == "thumb_render":
        data.thumb_folder(p, tid)                                   # it must exist
        return f"Thumbnail {tid} again ({p})", T + ["render", p, "--id", tid], "cpu"
    if kind == "thumb_check":
        title = " ".join(str(a.get("title") or "").split())
        if title and not THUMB_TEXT.fullmatch(title):
            raise JobError("the title: one line, up to 200 characters")
        return (f"Check the thumbnails ({p})", [PY, str(JOBTOOLS), "thumb-check", p] + (["--title", title] if title else []),
                "cpu")
    if kind != "thumb_make":
        raise JobError(f"unknown job kind {kind!r}")
    words = " ".join(str(a.get("words") or "").split())
    if not words or not THUMB_TEXT.fullmatch(words) or len(words) > 80:
        raise JobError("type the 2-4 words for the thumbnail")
    style = str(a.get("style") or "")                   # 0.4.5: in the style of a thumbnail set
    if style and not (data._thumbs_root() / data.safe_name(style) / "style.json").exists():
        raise JobError(f"the set {style} has no style yet - Claude finds its patterns first")
    template = str(a.get("template") or ("" if style else "outline"))
    if template and (not re.fullmatch(r"[\w-]+", template)
                     or not (TOOLS / "overlays" / "thumbnails" / template / "index.html").exists()):
        raise JobError(f"no design called {template}")
    cmd = T + ["make", p, "--id", tid, "--words", words] + (["--template", template] if template else []) \
        + (["--style", style] if style else [])
    if a.get("image"):
        img = Path(str(a["image"]).strip().strip('"')).expanduser()
        if not img.is_file() or img.suffix.lower() not in data.PUB_IMAGE_EXT:
            raise JobError(f"not a picture (.jpg / .png / .webp): {img}")
        cmd += ["--image", str(img)]
    else:
        try:
            f = int(a.get("frame"))
        except (TypeError, ValueError):
            raise JobError("pick a moment (a frame) or a picture first") from None
        if f < 0:
            raise JobError("pick a moment (a frame) or a picture first")
        cmd += ["--frame", str(f)]
        clip = str(a.get("clip") or "")
        if clip:
            if not re.fullmatch(r"[\w .()\[\]&'+,-]{1,160}", clip):
                raise JobError(f"not a clip: {clip!r}")
            cmd += ["--clip", clip]
    return f"Thumbnail {tid}: {words} ({p})", cmd, "cpu"


def plural_videos(n: int) -> str:
    return f"{n} video{'' if n == 1 else 's'}"


def saved_file(lines: list[str]) -> Path | None:
    """The file a download saved: tools\\download.py prints its path as the last line."""
    for ln in reversed(lines[-40:]):
        p = Path(ln.strip().strip('"'))
        if p.suffix.lower() in data.VIDEO_EXT | data.AUDIO_EXT and p.is_file():
            return p
    return None


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
        self.then: dict | None = None          # a download followed by its analysis: the analyze job's settings
        self.batch: int | None = None          # the jobs of one Add videos share it

    def info(self, since: int | None = None) -> dict:
        d = {"id": self.id, "kind": self.kind, "args": self.args, "title": self.title, "group": self.group,
             "status": self.status, "rc": self.rc, "started": data.stamp(self.started),
             "seconds": round((self.ended or time.time()) - self.started, 1),
             "command": " ".join(Path(c).name if i < 2 else c for i, c in enumerate(self.cmd)),
             "lines": len(self.lines), "then_claude": self.then_claude, "claude": self.claude,
             "then": bool(self.then), "batch": self.batch,
             "ended_ago_s": round(time.time() - self.ended) if self.ended else None}
        if since is not None:
            d["log"] = self.lines[since:since + 5000]
            d["since"] = since
        return d


class Runner:
    def __init__(self):
        self.jobs: dict[int, Job] = {}
        self.ids = itertools.count(1)
        self.lock = threading.Lock()
        self.measured: dict[int, list[tuple[str, str]]] = {}     # batch -> (video, analysis) measured for Claude
        self.opened: set[int] = set()                             # batches whose Claude window is open

    def running(self) -> list[Job]:
        return [j for j in self.jobs.values() if j.status in ("running", "cancelling")]

    def queued(self) -> list[Job]:
        return sorted((j for j in self.jobs.values() if j.status == "queued"), key=lambda j: j.id)

    def active(self) -> list[Job]:
        """Running or waiting their turn: the server stays up, updates and deletes wait."""
        return self.running() + self.queued()

    def start(self, kind: str, args: dict, queue: bool = False, then: dict | None = None,
              batch: int | None = None) -> Job:
        """Start a job now; queue=True: it waits its turn when its group is busy (or has others waiting) instead of
        being refused. then (a download only): analyse the saved video with these settings when it ends well."""
        title, cmd, group = make(kind, args or {})
        if then is not None:                                  # checked now, not when the download has ended
            if kind != "download":
                raise JobError("only a download can be followed by an analysis")
            if str(then.get("focus") or "") not in ("", *FOCUS):
                raise JobError(f"unknown focus {then.get('focus')} (content, cinematic or both)")
            cat = str(then.get("category") or "")
            if cat and cat not in CATEGORIES and cat not in LEGACY:
                raise JobError(f"unknown category {cat}")
        with self.lock:
            busy = self.running()
            if group == "exclusive" and (busy or self.queued()):
                raise JobError("wait until the running jobs finish")
            clash = [j for j in busy if j.group in (group, "exclusive")]
            waiting = [j for j in self.queued() if j.group == group]
            if (clash or waiting) and not queue:
                raise JobError(f"'{(clash or waiting)[0].title}' is still running")
            job = Job(next(self.ids), kind, args or {}, title, cmd, group)
            job.then, job.batch = (dict(then) if then else None), batch
            self.jobs[job.id] = job
            if clash or waiting:
                job.status = "queued"
                return job
        try:
            self._launch(job)
        except Exception:                                       # noqa: BLE001 - not left "running" for ever
            job.status, job.ended, job.rc = "failed", time.time(), -1
            raise
        return job

    def _launch(self, job: Job) -> None:
        with self.lock:
            if job.status == "cancelling":                    # Remove clicked while _next was starting it
                job.status, job.ended = "cancelled", time.time()
                return
            job.status, job.started = "running", time.time()
        LOGS.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
        job.proc = subprocess.Popen(job.cmd, cwd=str(LAB), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
                                    env=env, creationflags=NO_WINDOW)
        if job.status == "cancelling":                        # Remove clicked while it was starting
            job.proc.terminate()
        threading.Thread(target=self._pump, args=(job,), daemon=True).start()

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
            data.record_job(job.kind, job.title, job.args, job.started, job.ended, job.status)   # What it took (0.4.4)
            if job.then_claude and job.status == "done":
                if self._mates(job):                          # 0.4.5: a batch - one Claude window for all of it
                    self._collect(job, f)
                else:
                    self._hand_to_claude(job, f)
            if job.then and job.status == "done":
                self._then_analyse(job, f)
            if job.batch is not None:
                self._batch_to_claude(job, f)
        self._next()

    def _mates(self, job: Job) -> list[Job]:
        with self.lock:
            return [j for j in self.jobs.values() if j.batch is not None and j.batch == job.batch and j is not job]

    def _analysis_of(self, job: Job) -> str | None:
        rep = next((ln.split("REPORT:", 1)[1].strip() for ln in reversed(job.lines) if ln.startswith("REPORT:")), "")
        return Path(rep).parent.name if rep else None

    def _collect(self, job: Job, f) -> None:
        """A measured video of a batch: Claude checks it with the others, in one window, when the batch is measured."""
        a = self._analysis_of(job)
        if not a:
            return
        with self.lock:
            self.measured.setdefault(job.batch, []).append((str(job.args.get("video", "")), a))
        msg = "Measured - Claude checks it with the rest of the batch, in one window, when the last video is measured"
        job.lines.append(msg)
        f.write(msg + "\n")

    def _batch_to_claude(self, job: Job, f) -> None:
        """The batch's last job ended (downloads, measuring - in any order): ONE Claude window for every video it
        measured (`/analyze-reference batch <id>`, .app\\batches\\<id>.json), or the usual one when only one was."""
        with self.lock:
            if job.batch in self.opened or any(j.status in ("running", "queued", "cancelling")
                                               for j in self.jobs.values() if j.batch == job.batch):
                return
            got = self.measured.pop(job.batch, [])
            if not got:
                return
            self.opened.add(job.batch)
        try:
            if len(got) == 1:
                video, a = got[0]
                job.claude = system.open_claude(data.review_prompt(video, a), "review", Path(video).stem)
            else:
                b = data.new_batch("review", [a for _, a in got], f"b{job.batch}")
                job.claude = system.open_claude(data.batch_prompt(b), "review", f"batch of {len(got)}")
                data.mark_batch_opened(b["id"])
            msg = f"Claude Code opened to check {plural_videos(len(got))} ({job.claude['prompt']})"
        except Exception as e:                                  # noqa: BLE001 - the measuring itself succeeded
            job.claude = {"ok": False, "error": str(e)}
            msg = f"Could not open Claude Code: {e} - the Analyser has *Continue the batch* / Send to Claude"
        job.lines.append(msg)
        f.write(msg + "\n")

    def _then_analyse(self, job: Job, f) -> None:
        """Add videos: the download ended well - its saved video is analysed next (queued behind the others)."""
        saved = saved_file(job.lines)
        try:
            if saved is None:
                msg = "the saved file was not found - analyse it from the Analyze page (Downloaded, not analysed yet)"
            elif saved.suffix.lower() not in data.VIDEO_EXT:
                msg = f"{saved.name} is audio only - it waits for an edit (Editor), nothing to analyse"
            else:
                nj = self.start("analyze", {**job.then, "video": str(saved)}, queue=True, batch=job.batch)
                msg = f"Next: analysing {saved.name} (job {nj.id}{', waiting its turn' if nj.status == 'queued' else ''})"
                if any(ln.startswith("saved ") and "from one post" in ln for ln in job.lines):     # a carousel
                    msg += " - the post's other files wait under Downloaded, not analysed yet"
        except Exception as e:                                  # noqa: BLE001 - the download itself succeeded
            msg = f"Could not start the analysis of {saved.name if saved else 'the video'}: {e}"
        job.lines.append(msg)
        f.write(msg + "\n")

    def _next(self) -> None:
        """Start the queued jobs whose group is free now (oldest first). One that cannot start fails and the next one
        of its group gets its turn at once (else the group would wait for ever and hold back updates / deletes)."""
        while True:
            with self.lock:
                busy = self.running()
                j = next((q for q in self.queued() if not any(b.group in (q.group, "exclusive") for b in busy)), None)
                if j is None:
                    return
                j.status = "running"                          # claimed: no other thread starts it
            try:
                self._launch(j)
            except Exception as e:                              # noqa: BLE001 - e.g. the program vanished
                j.status, j.ended, j.rc = "failed", time.time(), -1
                j.lines.append(f"could not start: {e}")

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
        with self.lock:
            if job.status == "queued":                        # never started: it just leaves the queue
                job.status, job.ended = "cancelled", time.time()
                return job
            if job.status == "running" and job.proc is None:  # claimed by _next, not started yet: _launch stops it
                job.status = "cancelling"
                return job
        if job.status == "running" and job.proc:
            job.status = "cancelling"
            job.proc.terminate()
        return job

    def list(self) -> list[dict]:
        return [j.info() for j in sorted(self.jobs.values(), key=lambda j: -j.id)]
