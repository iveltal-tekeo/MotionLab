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


def main() -> int:
    setup_console()
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    url = sys.argv[1]
    preset = sys.argv[2] if len(sys.argv) > 2 else ""
    title, cmd = system.download_cmd(url, preset)
    i = cmd.index("--")                                   # extra fields printed after the file is in place
    cmd[i:i] = ["--print", f"after_move:{MARK}%(filepath)s|%(extractor_key)s|%(uploader)s|%(id)s|%(duration)s"]
    print(title, flush=True)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                            errors="replace", env=env, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    info = None
    for line in proc.stdout:
        line = line.rstrip("\r\n")
        if line.startswith(MARK):
            parts = line[len(MARK):].split("|")
            info = dict(zip(("path", "platform", "uploader", "id", "duration"), parts + [""] * 5))
            continue
        if line.strip() and not line.strip().lower().endswith((".mp4", ".mp3", ".mkv", ".webm", ".m4a", ".mov")):
            print(line, flush=True)
    rc = proc.wait()
    if rc != 0 or not info or not Path(info["path"]).is_file():
        print(f"download failed (yt-dlp exit code {rc})", flush=True)
        return rc or 1
    p = Path(info["path"])
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
