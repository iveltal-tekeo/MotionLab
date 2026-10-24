"""The feed around *Preview your thumbnail* (2026-10-24, the user: "compare it in a youtube-like home page to see it like
"in real life" how it would look so we can see if its good besides big youtubers like mrbeast ... probably of highly
viewed recent videos if possible").

    refresh(log)   the newest videos of big channels (CHANNELS, or the user's list in .app\\thumbfeed\\channels.json):
                   yt-dlp lists each channel's Videos tab (titles and numbers only - no video is downloaded), the
                   NEWEST of each are kept, the most viewed of those win, their thumbnails are downloaded once into
                   .app\\thumbfeed\\img\\<id>.jpg; feed.json = {fetched, channels, items: [{id, img, title, channel, views,
                   duration, upload_date}]} most viewed first. A channel that fails is named and left out.
    load()         feed.json + "stale" (older than a day) - the app's preview reads it (GET /api/thumbtest)
    channels() / set_channels(lines)   the channels the feed is made of (the defaults until the user changes them)
The app runs refresh as its job "thumb_feed" (Analyser > Thumbnails > Preview your thumbnail > Get the newest videos).
Network: yt-dlp + the pictures from YouTube's own picture server, nothing sent."""
from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .util import LAB

HOME = LAB / ".app" / "thumbfeed"
IMG = HOME / "img"
FEED = HOME / "feed.json"
MINE = HOME / "channels.json"
NEWEST = 10                    # a channel's newest videos looked at ...
KEEP = 5                       # ... and its most viewed of those kept
MAX_AGE_S = 24 * 3600
# big channels many people watch, several kinds of video; the user can change the list in the preview
CHANNELS = ["@MrBeast", "@MarkRober", "@mkbhd", "@ryan", "@airrack", "@DudePerfect", "@veritasium", "@kurzgesagt",
            "@YesTheory", "@MichelleKhare", "@aliabdaal", "@ColinandSamir", "@luisitocomunica", "@HiClavero",
            "@TheGrefg", "@auronplay"]
HANDLE = re.compile(r"^@[\w.\-]{2,60}$")


def channels() -> list[str]:
    try:
        mine = json.loads(MINE.read_text(encoding="utf-8")).get("channels")
        if isinstance(mine, list) and mine:
            return [str(x) for x in mine]
    except (OSError, ValueError):
        pass
    return list(CHANNELS)


def _norm(line: str) -> str | None:
    """@handle, a channel link or a bare handle -> the channel's address (@handle or https://...); None = not one."""
    s = line.strip()
    if not s:
        return None
    m = re.match(r"^(?:https?://)?(?:www\.|m\.)?youtube\.com/(@[^/?#\s]+|channel/[^/?#\s]+|c/[^/?#\s]+)", s)
    if m:
        return m.group(1) if m.group(1).startswith("@") else f"https://www.youtube.com/{m.group(1)}"
    s = s if s.startswith("@") else "@" + s
    return s if HANDLE.match(s) else None


def set_channels(lines: list[str]) -> list[str]:
    """The user's own list (an empty list = back to the defaults). Raises ValueError naming a line that is no channel."""
    out = []
    for ln in lines[:40]:
        if not str(ln).strip():
            continue
        c = _norm(str(ln))
        if not c:
            raise ValueError(f"not a YouTube channel: {str(ln)[:80]}")
        if c not in out:
            out.append(c)
    HOME.mkdir(parents=True, exist_ok=True)
    MINE.write_text(json.dumps({"channels": out}, indent=1), encoding="utf-8")
    return channels()


def _url(c: str) -> str:
    return f"https://www.youtube.com/{c}/videos" if c.startswith("@") else c.rstrip("/") + "/videos"


def load() -> dict:
    try:
        f = json.loads(FEED.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        f = {"items": [], "fetched": None}
    f["items"] = [x for x in f.get("items") or [] if (IMG / f"{x.get('id')}.jpg").is_file()]
    f["stale"] = not f.get("fetched_t") or time.time() - float(f["fetched_t"]) > MAX_AGE_S
    f["channels"] = channels()
    return f


def refresh(log=print) -> dict:
    from . import thumbsets as TS
    chans = channels()
    rows, failed = [], []

    def one(c):
        try:
            info = TS.ytdlp_json(["--flat-playlist", "-J", "--playlist-end", str(NEWEST), "--extractor-args",
                                  "youtubetab:approximate_date", _url(c)], timeout=120)
            ents = TS._entries(info, NEWEST)
            who = info.get("channel") or info.get("uploader") or info.get("title") or c
            who = re.sub(r"\s*-\s*Videos$", "", str(who))
            got = [dict(TS._row(e, info.get("channel_follower_count"), "feed"), channel=who) for e in ents]
            got = [r for r in got if r.get("id") and r.get("title") and "/shorts/" not in str(r.get("url") or "")]
            return sorted(got, key=lambda r: -(r.get("views") or 0))[:KEEP], None
        except Exception as e:                            # noqa: BLE001 - one channel never stops the feed
            return [], f"{c}: {e}"
    log(f"listing the newest {NEWEST} videos of {len(chans)} channels (titles and numbers only - no video) ...")
    with ThreadPoolExecutor(4) as ex:
        for got, err in ex.map(one, chans):
            if err:
                failed.append(err)
                log(f"  left out - {err}")
            else:
                rows += got
                if got:
                    log(f"  {got[0]['channel']}: {len(got)} videos, the most viewed {TS.num(got[0].get('views'))} views")
    IMG.mkdir(parents=True, exist_ok=True)

    def pic(r):
        p = IMG / f"{r['id']}.jpg"
        if p.is_file():
            return r, None
        try:
            data, ext = TS.download(r["urls"])
        except Exception as e:                            # noqa: BLE001 - one picture never stops the feed
            return r, str(e)
        p.write_bytes(data)
        return r, None
    todo = [r for r in rows if re.fullmatch(r"[\w\-]{6,20}", str(r["id"]))]
    log(f"downloading {sum(1 for r in todo if not (IMG / (r['id'] + '.jpg')).is_file())} thumbnail(s) ...")
    items = []
    with ThreadPoolExecutor(6) as ex:
        for r, err in ex.map(pic, todo):
            if err:
                log(f"  no picture for {str(r.get('title'))[:60]}: {err}")
                continue
            items.append({"id": r["id"], "title": r["title"], "channel": r["channel"], "views": r.get("views") or 0,
                          "duration": r.get("duration"), "upload_date": r.get("upload_date")})
    items.sort(key=lambda x: -(x["views"] or 0))
    out = {"fetched": time.strftime("%Y-%m-%d %H:%M"), "fetched_t": time.time(), "channels": chans,
           "failed": failed, "items": items}
    HOME.mkdir(parents=True, exist_ok=True)
    FEED.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    log(f"the feed: {len(items)} videos of {len(chans) - len(failed)} channels" + (f" ({len(failed)} left out)"
                                                                                   if failed else ""))
    return out
