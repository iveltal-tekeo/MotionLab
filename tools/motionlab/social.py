"""Content agency - your posted videos (0.6.0, docs\\plans.md steps 13 / 17; the user, 2026-10-26: "make so that videos
form social media form the brand show up on teh content agency and you could actually see them when they were posted,
views... etc"): the brand's own pages (My Brand > Your pages) read when the user presses *Check my pages* - their
newest videos with when they were posted, their views, likes and comments, the page's followers; every check kept, so
the page shows how a video grew. knowledge\\local\\social.json + knowledge\\local\\social\\thumbs\\ (never shared).

    check(log)        read every page My Brand names (the ones this module can read), write social.json
    load()            what the last checks found
    selfcheck()       the parsers on made-up yt-dlp answers (no network)

The rules (the research of 2026-10-25): the user's own pages only, only when they ask (never on a timer), public
numbers only - no login, no cookies. YouTube and TikTok are read with yt-dlp; their terms do not allow automated
reading, which is why it is a button the user presses for their own pages (YouTube's free Data API key = the
within-the-terms route, planned). Instagram, X, LinkedIn, Facebook, Threads, Twitch: not read here - Instagram needs a
login; its numbers come from the user's export (planned, step 13).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from .util import LAB

PATH = LAB / "knowledge" / "local" / "social.json"
THUMBS = PATH.parent / "social" / "thumbs"
READABLE = ("youtube", "tiktok")
LIST_N = 24                     # the newest videos listed a page (a YouTube tab)
DETAIL_N = 10                   # YouTube: the newest ones read one by one (the date and views a listing lacks)
TIMEOUT = 90


def ytdlp() -> str | None:
    return shutil.which("yt-dlp")


def _run(args: list[str], runner=None) -> dict | None:
    """yt-dlp -J ... -> its JSON (None when it fails). runner = a stand-in for the self-check."""
    if runner:
        return runner(args)
    exe = ytdlp()
    if not exe:
        return None
    try:
        r = subprocess.run([exe, "-J", "--no-warnings", *args], capture_output=True, text=True, encoding="utf-8",
                           timeout=TIMEOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode:
        return None
    try:
        return json.loads(r.stdout)
    except ValueError:
        return None


def _video(e: dict, platform: str) -> dict:
    """One yt-dlp entry -> what the page shows."""
    ts = e.get("timestamp") or e.get("release_timestamp")
    date = datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else (
        f"{e['upload_date'][:4]}-{e['upload_date'][4:6]}-{e['upload_date'][6:8]}" if e.get("upload_date") else "")
    thumbs = sorted((t for t in e.get("thumbnails") or [] if t.get("url")), key=lambda t: (t.get("width") or 0) * (t.get("height") or 0))
    return {"id": str(e.get("id") or ""), "url": e.get("webpage_url") or e.get("url") or "", "title": str(e.get("title") or "")[:200],
            "date": date, "time": datetime.fromtimestamp(ts).strftime("%H:%M") if ts else "",
            "views": e.get("view_count"), "likes": e.get("like_count"), "comments": e.get("comment_count"),
            "duration": e.get("duration"), "short": "/shorts/" in str(e.get("url") or "") or platform == "tiktok",
            "thumb_url": (thumbs[-1]["url"] if thumbs else "")}


def read_page(platform: str, url: str, log=print, runner=None) -> dict:
    """A page's newest videos -> {followers, videos: [...], error}."""
    url = url.rstrip("/")
    if platform == "youtube":
        vids, followers = [], None
        for tab in ("videos", "shorts"):
            d = _run(["--flat-playlist", "--playlist-end", str(LIST_N), "--extractor-args", "youtubetab:approximate_date",
                      f"{url}/{tab}"], runner)
            if not d:
                continue
            followers = followers or d.get("channel_follower_count")
            vids += [_video(e, platform) for e in d.get("entries") or [] if e.get("id")]
        if not vids:
            return {"followers": followers, "videos": [], "error": "nothing could be read - is the page public and the address right?"}
        # the newest ones one by one: their exact date, views, likes, comments (a listing has some, not all)
        vids.sort(key=lambda v: v["date"] or "9999", reverse=True)
        need = [v for v in vids if v["views"] is None or not v["date"]][:DETAIL_N] or vids[:DETAIL_N]
        for i, v in enumerate(need):
            log(f"progress {30 + int(50 * i / max(1, len(need)))} details")
            d = _run(["--skip-download", "--no-playlist", v["url"]], runner)
            if d:
                full = _video(d, platform)
                v.update({k: full[k] for k in ("date", "time", "views", "likes", "comments", "duration") if full[k] not in (None, "")})
                followers = followers or d.get("channel_follower_count")
        return {"followers": followers, "videos": sorted(vids, key=lambda v: v["date"] or "0000", reverse=True), "error": ""}
    if platform == "tiktok":
        d = _run(["--flat-playlist", "--playlist-end", str(LIST_N), url], runner)
        if not d:
            return {"followers": None, "videos": [], "error": "nothing could be read - TikTok may be blocking it right now; try again later"}
        vids = [_video(e, platform) for e in d.get("entries") or [] if e.get("id")]
        followers = d.get("channel_follower_count")
        if vids and followers is None:                    # the newest video carries the account's followers
            one = _run(["--skip-download", "--no-playlist", vids[0]["url"]], runner)
            followers = (one or {}).get("channel_follower_count")
        return {"followers": followers, "videos": sorted(vids, key=lambda v: v["date"] or "0000", reverse=True), "error": ""}
    return {"followers": None, "videos": [], "error": "not readable here"}


def _thumb(v: dict, platform: str) -> str:
    """The video's picture saved on this PC (TikTok's addresses expire); its lab-relative path or ""."""
    if not v.get("thumb_url", "").startswith("https://"):
        return ""
    f = THUMBS / f"{platform}_{v['id']}.jpg"
    if f.is_file():
        return f.relative_to(LAB).as_posix()
    try:
        req = urllib.request.Request(v["thumb_url"], headers={"User-Agent": "Mozilla/5.0 MotionLab"})
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read(1_500_001)
        if len(raw) > 1_500_000 or not (raw[:3] == b"\xff\xd8\xff" or raw[:4] == b"\x89PNG" or raw[8:12] == b"WEBP"):
            return ""
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(raw)
        return f.relative_to(LAB).as_posix()
    except (OSError, ValueError):
        return ""


def load(path: Path = PATH) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"pages": {}, "history": {}, "checked": None}


def check(log=print, path: Path = PATH, brand: dict | None = None, runner=None, thumbs: bool = True) -> dict:
    """Read the pages My Brand names (YouTube, TikTok) and keep what was found + each video's views at this check."""
    from . import brand as BR
    b = brand if brand is not None else BR.load()
    pages = [(p["platform"], p["url"]) for p in b.get("pages") or [] if p.get("url")]
    if not pages:
        raise RuntimeError("no pages in My Brand - add yours in My Brand > Overview > Your pages")
    old = load(path)
    out = {"pages": {}, "history": old.get("history") or {}, "checked": time.strftime("%Y-%m-%d %H:%M:%S")}
    now = int(time.time())
    for i, (plat, url) in enumerate(pages):
        log(f"progress {5 + int(90 * i / len(pages))} {plat}")
        if plat not in READABLE:
            out["pages"][plat] = {"url": url, "readable": False, "videos": [], "followers": None, "error": ""}
            continue
        log(f"Reading {url}")
        r = read_page(plat, url, log, runner)
        if r["error"] and (old.get("pages") or {}).get(plat, {}).get("videos"):
            r["videos"] = old["pages"][plat]["videos"]          # a failed read keeps the last good one
        for v in r["videos"]:
            if thumbs:
                v["thumb"] = _thumb(v, plat)
            if v.get("views") is not None:
                h = out["history"].setdefault(f"{plat}:{v['id']}", [])
                if not h or h[-1][1] != v["views"]:
                    h.append([now, v["views"]])
            v.pop("thumb_url", None)
        out["pages"][plat] = {"url": url, "readable": True, "followers": r["followers"], "videos": r["videos"], "error": r["error"]}
        log(f"  {plat}: {len(r['videos'])} video(s)" + (f", {r['followers']} followers" if r["followers"] else "")
            + (f" - {r['error']}" if r["error"] else ""))
    log("progress 100 done")
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, p)
    return out


def selfcheck() -> dict:
    """read_page / check on made-up yt-dlp answers, in a temp folder (no network). {passed, seconds, lines}."""
    import tempfile
    t0, lines, ok = time.time(), [], True

    def case(name, cond):
        nonlocal ok
        ok = ok and bool(cond)
        lines.append(f"{'PASS' if cond else 'FAIL'} {name}")

    yt_list = {"channel_follower_count": 1200, "entries": [
        {"id": "aaa", "title": "Long one", "url": "https://www.youtube.com/watch?v=aaa", "timestamp": 1792454400, "duration": 300},
        {"id": "bbb", "title": "Older", "url": "https://www.youtube.com/watch?v=bbb", "timestamp": 1791158400, "view_count": 50}]}
    yt_shorts = {"entries": [{"id": "sss", "title": "A short", "url": "https://www.youtube.com/shorts/sss", "view_count": 9000}]}
    detail = {"aaa": {"id": "aaa", "timestamp": 1792454400, "view_count": 321, "like_count": 12, "comment_count": 3},
              "sss": {"id": "sss", "upload_date": "20261020", "view_count": 9100, "like_count": 400}}
    tt = {"entries": [{"id": "777", "title": "A tiktok", "url": "https://www.tiktok.com/@rift/video/777", "timestamp": 1792954380,
                       "view_count": 36200, "like_count": 744, "comment_count": 126, "duration": 74}]}
    calls = []

    def fake(args):
        calls.append(args[-1])
        u = args[-1]
        if u.endswith("/videos"):
            return yt_list
        if u.endswith("/shorts"):
            return yt_shorts
        if "tiktok.com/@rift/video" in u:
            return {"channel_follower_count": 880}
        if "tiktok.com/@rift" in u:
            return tt
        k = u.rsplit("=", 1)[-1].rsplit("/", 1)[-1]
        return detail.get(k)
    r = read_page("youtube", "https://www.youtube.com/@rift/", lambda s: None, fake)
    by = {v["id"]: v for v in r["videos"]}
    case("YouTube: both tabs listed, the newest read one by one for their date and views, followers from the channel",
         set(by) == {"aaa", "bbb", "sss"} and by["aaa"]["views"] == 321 and by["aaa"]["likes"] == 12 and by["sss"]["date"] == "2026-10-20"
         and by["sss"]["views"] == 9100 and by["sss"]["short"] and r["followers"] == 1200 and r["videos"][0]["id"] == "sss")
    r2 = read_page("tiktok", "https://www.tiktok.com/@rift", lambda s: None, fake)
    case("TikTok: the listing's numbers, followers from the newest video",
         r2["videos"][0]["views"] == 36200 and r2["videos"][0]["comments"] == 126 and r2["followers"] == 880 and r2["videos"][0]["date"])
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "social.json"
        brand = {"pages": [{"platform": "youtube", "url": "https://www.youtube.com/@rift"}, {"platform": "tiktok", "url": "https://www.tiktok.com/@rift"},
                           {"platform": "instagram", "url": "https://www.instagram.com/rift"}]}
        log = []
        s = check(log.append, p, brand, fake, thumbs=False)
        case("check: YouTube and TikTok read, Instagram listed as not readable here, every video's views kept with the time",
             s["pages"]["youtube"]["readable"] and not s["pages"]["instagram"]["readable"] and "youtube:aaa" in s["history"]
             and load(p) == s and any(x.startswith("progress 100") for x in log))
        detail["aaa"]["view_count"] = 400
        s2 = check(log.append, p, brand, fake, thumbs=False)
        case("a second check: the views it grew to are added to the video's history", [h[1] for h in s2["history"]["youtube:aaa"]] == [321, 400])
        try:
            check(log.append, p, {"pages": []}, fake)
            refused = False
        except RuntimeError:
            refused = True
        case("no pages in My Brand: a clear message", refused)
    return {"passed": ok, "seconds": round(time.time() - t0, 3), "lines": lines}
