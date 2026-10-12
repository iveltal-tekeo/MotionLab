"""Download one video (or its audio) with yt-dlp into refs\\ and remember where it came from in refs\\downloads.json
(link, platform, uploader, title), so the analysis and its shared reference card can name the source.

    .venv\\Scripts\\python tools\\download.py "<link>" [mp4_1080 | mp4_best | mp3]

Prints yt-dlp's progress and, as the last line, the saved file's path (the app's 'Download from a link' uses it).
yt-dlp is found automatically or set in the app's Settings; nothing is installed."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab.app import system  # noqa: E402
from motionlab.util import REFS, setup_console  # noqa: E402

MARK = "MLDL|"
FIELDS = ("path", "platform", "id", "duration", "uploader")   # free text last: an uploader may contain "|"
PRINT = f"after_move:{MARK}%(filepath)s|%(extractor_key)s|%(id)s|%(duration)s|%(uploader)s"
MEDIA = (".mp4", ".mp3", ".mkv", ".webm", ".m4a", ".mov")
# yt-dlp's ERROR line -> what it means, in words (the first match wins; measured 2026-10-12 with yt-dlp 2026.08.19)
HINTS = [
    (("requested format is not available",),
     "this link has no video picture (a SoundCloud track, a photo post?) - pick 'MP3 audio only' to keep its sound"),
    (("not a bot", "http error 429", "too many requests", "rate-limit", "rate limit"),
     "the site is blocking downloads from this PC for a while (bot check / too many requests) - try again later, "
     "or save the video from your browser and drop it into refs\\"),
    (("login", "logged-in", "empty media response", "registered users", "private", "cookies"),
     "the site wants you logged in for this video, and MotionLab cannot pass your browser's login to yt-dlp - "
     "save the video from your browser and drop it into refs\\"),
    (("unsupported url",), "yt-dlp does not know this kind of link - paste the video's own page link"),
    (("video unavailable", "has been removed", "not available in your country", "no longer available"),
     "the video was removed or is not available here"),
    (("ffmpeg not found", "ffmpeg is not installed"), "ffmpeg is missing (Settings > Programs): yt-dlp needs it to join picture and sound"),
    (("unable to extract", "yt-dlp -u", "latest version"),
     "yt-dlp is probably out of date for this site - update it (yt-dlp -U, or: winget upgrade yt-dlp.yt-dlp)"),
]


def hint(lines: list[str]) -> str:
    """Why yt-dlp failed, in words: from its last ERROR line ("" when nothing known matches)."""
    err = next((ln for ln in reversed(lines) if ln.startswith("ERROR")), "").lower()
    return next((h for words, h in HINTS if err and any(w in err for w in words)), "")


def with_fields(cmd: list[str]) -> list[str]:
    """yt-dlp's command + the line that reports the saved file. `--encoding utf-8`: yt-dlp.exe otherwise prints in the
    console's code page and drops what it cannot show - an emoji in a title vanished from the path (0.3.2 said
    "download failed" for a video that was saved)."""
    i = cmd.index("--")
    return cmd[:i] + ["--encoding", "utf-8", "--print", PRINT] + cmd[i:]


def parse(line: str) -> dict | None:
    """The MARK line -> {path, platform, id, duration, uploader} ("" where yt-dlp has none: it prints "NA");
    None for any other line."""
    if not line.startswith(MARK):
        return None
    parts = line[len(MARK):].split("|", len(FIELDS) - 1) + [""] * len(FIELDS)
    return {k: "" if v == "NA" else v for k, v in zip(FIELDS, parts)}


def saved_file(info: dict | None, folder: Path) -> Path | None:
    """The downloaded file: the printed path, else the newest file in the download folder whose name ends with
    "[<id>].<ext>" (the name template ends with the video's id) - in case a character still got lost in printing."""
    if not info:
        return None
    p = Path(info["path"]) if info["path"] else None
    if p and p.is_file():
        return p
    if not info["id"] or not folder.is_dir():
        return None
    tail = f"[{info['id']}]"
    hits = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in MEDIA and f.stem.endswith(tail)]
    return max(hits, key=lambda f: f.stat().st_mtime) if hits else None


def main() -> int:
    setup_console()
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    url = sys.argv[1]
    preset = sys.argv[2] if len(sys.argv) > 2 else ""
    title, cmd = system.download_cmd(url, preset)
    cmd = with_fields(cmd)                                # extra fields printed after the file is in place
    folder = Path(cmd[cmd.index("-P") + 1])
    print(title, flush=True)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                            errors="replace", env=env, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    info, lines = None, []
    for line in proc.stdout:
        line = line.rstrip("\r\n")
        if line.startswith(MARK):
            info = parse(line)
            continue
        if line.strip() and not line.strip().lower().endswith(MEDIA):
            print(line, flush=True)
            lines.append(line)
    rc = proc.wait()
    p = saved_file(info, folder) if rc == 0 else None
    if p is None:
        why = hint(lines)
        print((f"download failed (yt-dlp exit code {rc})" + (f": {why}" if why else "")) if rc else
              "download failed: yt-dlp ended well, but the saved file was not found in " + str(folder), flush=True)
        return rc or 1
    idx_path = REFS / "downloads.json"
    try:
        idx = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else {}
    except ValueError:
        idx = {}
    idx[p.name] = {"url": url, "platform": info["platform"] or None, "uploader": info["uploader"] or None,
                   "id": info["id"] or None, "title": p.stem.rsplit(" [", 1)[0],
                   "duration_s": float(info["duration"]) if info["duration"].replace(".", "", 1).isdigit() else None,
                   "folder": str(p.parent.relative_to(REFS.parent)) if REFS.parent in p.parents else str(p.parent),
                   "downloaded": time.strftime("%Y-%m-%d %H:%M")}
    REFS.mkdir(exist_ok=True)
    idx_path.write_text(json.dumps(idx, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"saved from {info['platform'] or 'the web'}: {p.name}", flush=True)
    print(str(p), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
