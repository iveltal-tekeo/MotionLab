"""Download one video (or its audio) with yt-dlp into refs\\ and remember where it came from in refs\\downloads.json
(link, platform, uploader, title), so the analysis and its shared reference card can name the source.

    .venv\\Scripts\\python tools\\download.py "<link>" [mp4_1080 | mp4_best | mp3]
    .venv\\Scripts\\python tools\\download.py selfcheck        known answers, no network (a fake carousel)

Prints yt-dlp's progress and, as the last line, the saved file's path (the app's 'Download from a link' uses it).
A post that saves several files (an Instagram carousel, a TikTok photo post with its sound) keeps every file: each
one gets its own entry in downloads.json with "post" (the link), "part" (1..n) and "parts" (n); the last line is
then the post's first video (else its first file).
yt-dlp is found automatically or set in the app's Settings; nothing is installed. Settings > Downloads > "Use my
browser's login" (off by default) adds --cookies-from-browser (system.download_cmd)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab.app import system  # noqa: E402
from motionlab.util import REFS, setup_console  # noqa: E402

MARK = "MLDL|"
# free text last: an uploader may contain "|" (a Windows path cannot)
FIELDS = ("path", "platform", "id", "duration", "index", "count", "uploader")
PRINT = (f"after_move:{MARK}%(filepath)s|%(extractor_key)s|%(id)s|%(duration)s|%(playlist_index)s|%(n_entries)s|"
         "%(uploader)s")
VIDEOS = (".mp4", ".mkv", ".webm", ".mov")
MEDIA = VIDEOS + (".mp3", ".m4a")
IMAGES = (".jpg", ".jpeg", ".png", ".webp", ".heic")          # the photos of a carousel / photo post
LOGIN_HINT = ("the site wants you logged in for this video - turn on Settings > Downloads > \"Use my browser's "
              "login for downloads\" (Firefox works best), or save the video from your browser and drop it into refs\\")
# yt-dlp's ERROR line -> what it means, in words (the first match wins; measured 2026-10-12 with yt-dlp 2026.08.19)
HINTS = [
    (("requested format is not available",),
     "this link has no video picture (a SoundCloud track, a photo post?) - pick 'MP3 audio only' to keep its sound"),
    (("not a bot", "http error 429", "too many requests", "rate-limit", "rate limit"),
     "the site is blocking downloads from this PC for a while (bot check / too many requests) - try again later, "
     "turn on Settings > Downloads > \"Use my browser's login for downloads\", or save the video from your browser "
     "and drop it into refs\\"),
    # 0.4.2.1: reading the browser's login failed (Chrome / Edge lock their cookie file while open and encrypt it)
    (("could not copy", "cookie database", "dpapi", "failed to decrypt", "could not find firefox", "could not find "
      "chrome", "could not find edge", "unsupported browser"),
     "yt-dlp could not read your browser's login - Chrome and Edge lock and encrypt it: close that browser and try "
     "again, or pick Firefox in Settings > Downloads (log in to the site in Firefox first)"),
    (("login", "logged-in", "empty media response", "registered users", "private", "cookies"), LOGIN_HINT),
    (("unsupported url",), "yt-dlp does not know this kind of link - paste the video's own page link"),
    (("video unavailable", "has been removed", "not available in your country", "no longer available"),
     "the video was removed or is not available here"),
    (("ffmpeg not found", "ffmpeg is not installed"), "ffmpeg is missing (Settings > Programs): yt-dlp needs it to join picture and sound"),
    (("unable to extract", "yt-dlp -u", "latest version", "javascript runtime", "js runtime"),
     "yt-dlp is probably out of date for this site - Settings > Programs > Update yt-dlp (YouTube also needs Deno, "
     "see the same page)"),
]


def hint(lines: list[str], login_on: bool = False) -> str:
    """Why yt-dlp failed, in words: from its last ERROR line ("" when nothing known matches). login_on: the login
    setting is on already, so a login hint says to log in to the site in that browser instead."""
    err = next((ln for ln in reversed(lines) if ln.startswith("ERROR")), "").lower()
    h = next((h for words, h in HINTS if err and any(w in err for w in words)), "")
    if h == LOGIN_HINT and login_on:
        return ("the site wants you logged in, and your browser's login did not work - log in to the site in the "
                "browser picked in Settings > Downloads, then try again")
    return h


def with_fields(cmd: list[str]) -> list[str]:
    """yt-dlp's command + the line that reports the saved file. `--encoding utf-8`: yt-dlp.exe otherwise prints in the
    console's code page and drops what it cannot show - an emoji in a title vanished from the path (0.3.2 said
    "download failed" for a video that was saved)."""
    i = cmd.index("--")
    return cmd[:i] + ["--encoding", "utf-8", "--print", PRINT] + cmd[i:]


def parse(line: str) -> dict | None:
    """The MARK line -> {path, platform, id, duration, index, count, uploader} ("" where yt-dlp has none: it prints
    "NA"); None for any other line."""
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
    hits = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in MEDIA + IMAGES and f.stem.endswith(tail)]
    return max(hits, key=lambda f: f.stat().st_mtime) if hits else None


def collect(lines) -> tuple[list[dict], list[str]]:
    """yt-dlp's output lines -> (every MARK line's fields, in order, one per file; the lines worth showing)."""
    infos, shown = [], []
    for line in lines:
        line = line.rstrip("\r\n")
        if line.startswith(MARK):
            info = parse(line)
            if info and not any(i["path"] == info["path"] and i["id"] == info["id"] for i in infos):
                infos.append(info)
            continue
        if line.strip() and not line.strip().lower().endswith(MEDIA + IMAGES):   # after_move:filepath = noise
            shown.append(line)
    return infos, shown


def _entry(url: str, info: dict, p: Path) -> dict:
    dur = info["duration"]
    return {"url": url, "platform": info["platform"] or None, "uploader": info["uploader"] or None,
            "id": info["id"] or None, "title": p.stem.rsplit(" [", 1)[0],
            "duration_s": float(dur) if dur.replace(".", "", 1).isdigit() else None,
            "folder": str(p.parent.relative_to(REFS.parent)) if REFS.parent in p.parents else str(p.parent),
            "downloaded": time.strftime("%Y-%m-%d %H:%M")}


def record(url: str, files: list[tuple[dict, Path]], idx_path: Path) -> dict:
    """Write every saved file into downloads.json (the existing keys + post / part / parts when a post saved several
    files). Returns {file name: entry}."""
    try:
        idx = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else {}
    except ValueError:
        idx = {}
    new = {}
    for i, (info, p) in enumerate(files, 1):
        e = _entry(url, info, p)
        if len(files) > 1:
            e.update(post=url, part=i, parts=len(files))
        new[p.name] = e
    idx.update(new)
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    idx_path.write_text(json.dumps(idx, indent=1, ensure_ascii=False), encoding="utf-8")
    return new


def finish(url: str, infos: list[dict], lines: list[str], rc: int, folder: Path, idx_path: Path,
           login_on: bool = False, out=print) -> int:
    """After yt-dlp: record every saved file, say what happened, print the main file's path last."""
    files, seen = [], set()
    for info in infos:
        p = saved_file(info, folder)
        if p is not None and p not in seen:
            seen.add(p)
            files.append((info, p))
    if not files:
        why = hint(lines, login_on)
        out((f"download failed (yt-dlp exit code {rc})" + (f": {why}" if why else "")) if rc else
            "download failed: yt-dlp ended well, but the saved file was not found in " + str(folder))
        return rc or 1
    record(url, files, idx_path)
    platform = files[0][0]["platform"] or "the web"
    if rc:                                         # some parts saved, yt-dlp failed on others: keep what came
        why = hint(lines, login_on)
        out(f"yt-dlp reported an error (exit code {rc}) but saved {len(files)} file(s)" + (f": {why}" if why else ""))
    if len(files) == 1:
        out(f"saved from {platform}: {files[0][1].name}")
    else:
        kinds = {"video": 0, "photo": 0, "sound": 0}
        for _, p in files:
            kinds["video" if p.suffix.lower() in VIDEOS else "photo" if p.suffix.lower() in IMAGES else "sound"] += 1
        what = ", ".join(f"{n} {k}{'s' if n > 1 else ''}" for k, n in kinds.items() if n)
        out(f"saved {len(files)} files from one post on {platform} ({what}) - kept together as one post:")
        for i, (_, p) in enumerate(files, 1):
            out(f"  part {i}: {p.name}")
    main_file = next((p for _, p in files if p.suffix.lower() in VIDEOS), files[0][1])
    out(str(main_file))
    return 0


def main() -> int:
    setup_console()
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    if sys.argv[1] == "selfcheck":
        bad = selfcheck()
        print("\n".join(bad) if bad else "download selfcheck: PASS (a fake carousel of 3 files -> one post)")
        return 1 if bad else 0
    url = sys.argv[1]
    preset = sys.argv[2] if len(sys.argv) > 2 else ""
    title, cmd = system.download_cmd(url, preset)
    cmd = with_fields(cmd)                                # extra fields printed after the file is in place
    folder = Path(cmd[cmd.index("-P") + 1])
    print(getattr(title, "en", "") or title, flush=True)      # the job's log stays English (the page shows the title)
    if "--cookies-from-browser" in cmd:
        print(f"using your {cmd[cmd.index('--cookies-from-browser') + 1]} login for this download (Settings)", flush=True)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                            errors="replace", env=env, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

    def live():
        for line in proc.stdout:
            infos, shown = collect([line])
            for s in shown:
                print(s, flush=True)
            yield line
    infos, lines = collect(live())
    rc = proc.wait()
    return finish(url, infos, lines, rc, folder, REFS / "downloads.json", "--cookies-from-browser" in cmd,
                  out=lambda s: print(s, flush=True))


def selfcheck() -> list[str]:
    """Known answers without the network: yt-dlp's output for an Instagram carousel (2 videos + 1 photo, MARK lines
    between progress lines) -> three files in one post in a scratch downloads.json, the first video printed last; a
    single video keeps the 0.4.2 entry (no post keys); the login hint points to the setting. Returns what failed."""
    bad: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        names = ["Trip day 1 [C1a].mp4", "Trip day 1 [C1b].jpg", "Trip day 1 [C1c].mp4"]
        for n in names:
            (d / n).write_bytes(b"x")
        url = "https://www.instagram.com/p/FAKE123/"
        fake = ["[instagram] Extracting URL: " + url, "[download] Downloading playlist: Trip day 1",
                *[ln for i, n in enumerate(names, 1) for ln in (
                    f"[download] Downloading item {i} of 3", "[download] 100% of 1.00MiB", str(d / n),
                    f"{MARK}{d / n}|Instagram|C1{'abc'[i - 1]}|{'12.5' if n.endswith('.mp4') else 'NA'}|{i}|3|"
                    "Ana | travels")]]
        infos, shown = collect(fake)
        printed: list[str] = []
        rc = finish(url, infos, shown, 0, d, d / "downloads.json", out=printed.append)
        idx = json.loads((d / "downloads.json").read_text(encoding="utf-8"))
        if rc != 0 or sorted(idx) != sorted(names):
            bad.append(f"carousel: every file recorded (got {sorted(idx)}, rc {rc})")
        elif [(idx[n].get("post"), idx[n].get("part"), idx[n].get("parts")) for n in names] != [(url, i, 3) for i in (1, 2, 3)]:
            bad.append("carousel: post / part / parts")
        elif idx[names[0]]["uploader"] != "Ana | travels" or idx[names[0]]["duration_s"] != 12.5 \
                or idx[names[1]]["duration_s"] is not None or idx[names[0]]["title"] != "Trip day 1":
            bad.append("carousel: the existing keys (uploader with '|', duration, title)")
        if not printed or printed[-1] != str(d / names[0]) or any(str(d / n) in shown for n in names):
            bad.append(f"carousel: the first video is printed last (got {printed[-1:]})")
        one = d / "Solo [V1].mp4"
        one.write_bytes(b"x")
        infos, shown = collect([f"{MARK}{one}|TikTok|V1|9|NA|NA|Bo"])
        finish("https://www.tiktok.com/@bo/video/1", infos, shown, 0, d, d / "downloads.json", out=printed.append)
        e = json.loads((d / "downloads.json").read_text(encoding="utf-8"))[one.name]
        if "post" in e or e["platform"] != "TikTok" or e["duration_s"] != 9.0 or len(e) != 8:
            bad.append(f"single video: the 0.4.2 entry, no post keys (got {e})")
        if "Settings > Downloads" not in hint(["ERROR: [vimeo] 123: This video is only available for registered users"]) \
                or "Settings > Downloads" not in hint(["ERROR: [instagram] x: Requested content is not available, "
                                                       "rate-limit reached or login required"]):
            bad.append("login hint: points to Settings > Downloads")
        if "close that browser" not in hint(["ERROR: Could not copy Chrome cookie database"]):
            bad.append("cookie hint: Chrome / Edge lock their cookies")
    return bad


if __name__ == "__main__":
    sys.exit(main())
