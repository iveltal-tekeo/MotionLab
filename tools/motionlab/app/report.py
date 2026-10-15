"""Report a problem (0.4.2.1): a GitHub issue the user reads and sends themselves. Settings and every failed job have
the button; the dialog first shows the report - what happened (the job's title and kind), MotionLab's version,
Windows / Python and the programs' versions, the last LOG_LINES lines of the job's log (.app\\jobs\\<id>.log) or of
.app\\server.log - scrubbed (`scrub`: the home folder -> %USERPROFILE%, the lab folder -> <MotionLab>, the Windows
user name, this PC's name and the Settings name, e-mail addresses, link credentials and query strings). Then the
browser opens `<repo>/issues/new?title=...&body=...` for the repo this copy updates from (git remote origin, so a
friend's copy points at the right repo), within GitHub's link length (the log is trimmed from the top, and the report
says so). Nothing is sent by the app; no GitHub remote -> the dialog offers "Copy the report" instead."""
from __future__ import annotations

import os
import platform
import re
import urllib.parse
from pathlib import Path

from motionlab import __version__
from motionlab.util import LAB

LOG_LINES = 40
URL_MAX = 7500                     # GitHub answers 414 (URI too long) a little above 8 KB: stay well below
SERVER_LOG = LAB / ".app" / "server.log"
FOOT = "_Written by MotionLab's Report a problem: names and folders were taken out, and nothing was sent until " \
       "Submit was pressed._"


def _path_rx(path: str) -> str:
    """A folder in any spelling a log has: C:\\Users\\x, C:/Users/x, C:\\\\Users\\\\x (JSON), any case."""
    parts = [re.escape(p) for p in re.split(r"[\\/]+", str(path).rstrip("\\/")) if p]
    return r"[\\/]+".join(parts) + r"(?![\w.-])"


def scrub(text: str, home: str | None = None, lab: str | None = None, user: str | None = None,
          names: tuple = ()) -> str:
    """The report without what points at the user: link credentials + query strings (tokens), e-mail addresses,
    the lab folder (<MotionLab>), the home folder and any C:\\Users\\<name> (%USERPROFILE%), then the Windows user
    name (<user>) and other names (this PC, the Settings name: <name>) as whole words of 3+ letters."""
    home = str(home if home is not None else Path.home())
    lab = str(lab if lab is not None else LAB)
    user = user if user is not None else (os.environ.get("USERNAME") or Path.home().name)
    t = str(text)
    t = re.sub(r"(?i)\b(https?://)[^\s/@\"'<>]+@", r"\1", t)                         # https://user:token@host
    t = re.sub(r"(?i)\b(https?://[^\s?#\"'<>]+)\?[^\s#\"'<>]*", r"\1?<removed>", t)  # ?token=...
    t = re.sub(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", "<email>", t)
    for path, word in sorted(((lab, "<MotionLab>"), (home, "%USERPROFILE%")), key=lambda pw: -len(pw[0])):
        if len(path) > 3:
            t = re.sub("(?i)" + _path_rx(path), lambda m: word, t)
    t = re.sub(r"(?i)\b[a-z]:[\\/]+users[\\/]+(?!public\b)[^\\/\s\"'<>|:*?]+", lambda m: "%USERPROFILE%", t)
    for n, word in [(user, "<user>")] + [(x, "<name>") for x in names]:
        if n and len(n) >= 3:
            t = re.sub(r"(?i)(?<![\w%<])" + re.escape(n) + r"(?![\w%>])", word, t)
    return t


def repo_url(remote: str | None) -> str | None:
    """git remote origin -> https://github.com/<owner>/<repo> (https or ssh, credentials dropped); None if not GitHub."""
    m = re.match(r"^\s*(?:https?://(?:[^@/\s]+@)?|ssh://git@|git@)(?:www\.)?github\.com[:/]+([\w.-]+)/([\w.-]+?)"
                 r"(?:\.git)?/?\s*$", remote or "", re.I)
    return f"https://github.com/{m[1]}/{m[2]}" if m else None


def windows() -> str:
    if platform.system() != "Windows":
        return platform.platform()
    ver = platform.version()                                   # 10.0.19045
    build = int(ver.split(".")[-1]) if ver.split(".")[-1].isdigit() else 0
    return f"Windows {'11' if build >= 22000 else platform.release()} ({ver})"


def tail(p: Path, n: int = LOG_LINES) -> list[str]:
    try:
        return p.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]
    except OSError:
        return []


def _head(what: str, kind: str, note: str, programs: dict) -> str:
    progs = " · ".join(f"{k} {v}" for k, v in programs.items() if v)
    return "\n".join([f"**What happened:** {what}", f"**Kind:** {kind}", ""]
                     + ([f"**What I was doing:** {note}", ""] if note else [])
                     + [f"**MotionLab:** {__version__}", f"**Windows:** {windows()}",
                        f"**Python:** {platform.python_version()}"] + ([f"**Programs:** {progs}"] if progs else []))


def body_of(head: str, log: list[str], source: str, dropped: int = 0) -> str:
    lines = [head, "", (f"**The last {len(log)} lines of {source}**" if len(log) > 1 else f"**The last line of {source}**")
             + " (names and folders taken out):", "```text", *log, "```"]
    if dropped:
        lines.append(f"_The log was trimmed by {dropped} line(s) at the top to fit GitHub's link - MotionLab's "
                     f"Copy the report has all of it._")
    return "\n".join(lines + ["", FOOT])


def issue_url(repo: str, title: str, head: str, log: list[str], source: str) -> tuple[str, int]:
    """(the new-issue link, how many log lines were dropped from the top so it fits URL_MAX)."""
    q = lambda s: urllib.parse.quote(s, safe="")                                   # noqa: E731
    for dropped in range(len(log) + 1):
        url = f"{repo}/issues/new?title={q(title)}&body={q(body_of(head, log[dropped:], source, dropped))}"
        if len(url) <= URL_MAX:
            return url, dropped
    while head and len(url) > URL_MAX:                                     # a very long note: cut it too
        head = head[:-200]
        url = f"{repo}/issues/new?title={q(title)}&body={q(body_of(head + ' …', [], source, len(log)))}"
    return url, len(log)


def build(job: dict | None, log: list[str], note: str = "", remote: str | None = None, programs: dict | None = None,
          names: tuple = ()) -> dict:
    """The report for one failed job (job = its info: title, kind, status, rc) or, without a job, for MotionLab in
    general (log = server.log's last lines). Everything scrubbed; url = the GitHub link (None: no GitHub remote)."""
    s = lambda x: scrub(x, names=names)                                            # noqa: E731
    if job:
        what = f"{job.get('title')} - {job.get('status')}" + (f" (exit code {job['rc']})" if job.get("rc") not in (None, 0) else "")
        kind, source = f"job '{job.get('kind')}'", "the job's log"
        title = f"{job.get('title')} {'failed' if job.get('status') == 'failed' else job.get('status')}"
    else:
        what, kind, source = "a problem in MotionLab (from Settings)", "general", "the app's error log"
        title = "Problem: " + (note.strip().splitlines()[0][:80] if note.strip() else "something does not work")
    note = s(str(note or "").strip()[:2000])
    head = s(_head(what, kind, note, programs or {}))
    log = [s(ln)[:400] for ln in log[-LOG_LINES:]] or ["(nothing logged)"]
    title = s(title)[:120]
    repo = repo_url(remote)
    url, dropped = issue_url(repo, title, head, log, source) if repo else (None, 0)
    return {"title": title, "body": body_of(head, log, source), "repo": repo, "url": url, "dropped": dropped,
            "lines": len(log)}


def selfcheck() -> list[str]:
    """Known answers (no network, nothing written): the scrubbing, the repo link, the trimming. Returns what failed."""
    bad = []
    home, lab, user = r"C:\Users\Alex", r"C:\MotionLab", "alex"
    cases = [
        (r"C:\Users\Alex\Downloads\YTDLP\yt-dlp.exe", r"%USERPROFILE%\Downloads\YTDLP\yt-dlp.exe"),
        ("c:/users/alex/AppData/Local/x.log", "%USERPROFILE%/AppData/Local/x.log"),
        (r'"path": "C:\\Users\\alex\\Videos\\a.mp4"', r'"path": "%USERPROFILE%\\Videos\\a.mp4"'),
        (r"File C:\MotionLab\tools\download.py, line 3", r"File <MotionLab>\tools\download.py, line 3"),
        (r"C:\MotionLabX\a", r"C:\MotionLabX\a"),                        # another folder that only starts the same
        (r"C:\Users\ALEXAN~1\AppData\Temp", r"%USERPROFILE%\AppData\Temp"),
        (r"D:\Users\maria\clip.mov", r"%USERPROFILE%\clip.mov"),
        ("hello alex, Alexander and ALEX", "hello <user>, Alexander and <user>"),
        ("mail me: sam.x+ml@example.com.", "mail me: <email>."),
        ("https://www.tiktok.com/@ana/video/123?is_from_webapp=1&sender_device=pc&token=abc",
         "https://www.tiktok.com/@ana/video/123?<removed>"),
        ("https://bob:ghp_SECRET@github.com/bob/MotionLab.git", "https://github.com/bob/MotionLab.git"),
        ("ERROR: [Instagram] C1a: login required", "ERROR: [Instagram] C1a: login required"),
        ("by sam on DESKTOP-AB12", "by <name> on <name>"),
    ]
    for raw, want in cases:
        got = scrub(raw, home, lab, user, names=("sam", "DESKTOP-AB12"))
        if got != want:
            bad.append(f"scrub {raw!r}: got {got!r}, want {want!r}")
    for remote, want in (("https://github.com/iveltal-tekeo/MotionLab.git", "https://github.com/iveltal-tekeo/MotionLab"),
                         ("git@github.com:ana/MotionLab.git", "https://github.com/ana/MotionLab"),
                         ("https://x:tok@github.com/ana/Motion.Lab/", "https://github.com/ana/Motion.Lab"),
                         ("https://gitlab.com/ana/MotionLab.git", None), ("", None), (r"C:\fake\bare.git", None)):
        if repo_url(remote) != want:
            bad.append(f"repo_url {remote!r}: got {repo_url(remote)!r}, want {want!r}")
    log = [f"line {i} " + "x" * 300 for i in range(40)]
    r = build({"title": "Download from www.tiktok.com", "kind": "download", "status": "failed", "rc": 1}, log,
              note="I pasted a link", remote="git@github.com:ana/MotionLab.git")
    q = urllib.parse.urlsplit(r["url"] or "")
    body = urllib.parse.parse_qs(q.query).get("body", [""])[0]
    if not (r["url"] and r["url"].startswith("https://github.com/ana/MotionLab/issues/new?title=Download%20from")
            and len(r["url"]) <= URL_MAX and r["dropped"] > 0 and "line 39 " in body and "line 0 " not in body
            and f"trimmed by {r['dropped']} line" in body and "line 0 " in r["body"] and __version__ in body
            and "I pasted a link" in body and urllib.parse.parse_qs(q.query)["title"] == ["Download from www.tiktok.com failed"]):
        bad.append(f"issue link: trimmed to fit, newest lines kept, says so (dropped {r['dropped']}, {len(r['url'] or '')} chars)")
    short = build(None, ["one error"], remote="https://gitlab.com/x/y")
    if short["url"] is not None or "one error" not in short["body"]:
        bad.append("no GitHub remote: no link (Copy the report instead)")
    return bad
