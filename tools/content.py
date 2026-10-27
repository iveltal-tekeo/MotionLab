"""Content analysis, step 1 (0.4): what a reference SAYS - its transcript, every line with frame + timecode.

Source: the platform's own subtitles through yt-dlp - uploaded ones first, else the auto-generated captions in the
video's own language (YouTube's carry word timings): no model, a few seconds per video. Without subtitles (or without
a known link) speech to text hears the analysis' audio when it is installed (Settings > Programs > Speech to text;
`auto()` = what analyze.py --focus content / both runs after the lab pass).

    .venv\\Scripts\\python tools\\content.py transcript <name | video> [--url <link>] [--lang en] [--force]
    .venv\\Scripts\\python tools\\content.py show <name> [<start frame> <end frame>]
    .venv\\Scripts\\python tools\\content.py stats <name | video> [--url <link>]
          how the video performs (0.3.5): views, likes, comments, the channel's followers, the upload date ->
          analysis\\<name>\\content\\stats.json; views / followers = the outperformer score; every fetch is kept
          in its history. The transcript fetch saves them too (the same request), and both save the video's
          thumbnail (0.4.3): analysis\\<name>\\content\\thumbnail.<jpg|webp|png> + thumbnail.json (its measures:
          brightness, saturation, colours, faces - tools\\thumbnail.py refs summarises them per niche)
    .venv\\Scripts\\python tools\\content.py thumbnail <name | video> [--url <link>]
          only the thumbnail, for analyses fetched before 0.4.3

<name> = the analysis folder (Analyze); a video that has no analysis yet works too (its frame rate is probed).
The link comes from refs\\downloads.json (the app's downloads), else from a YouTube id in the file name
("... [VLDJ_-wrwj8].mp4"), else --url. Writes only analysis\\<name>\\content\\: subs\\ (the caption file as
downloaded), transcript.json (lines + word timings), transcript.txt (one line per caption with
f480 (00:00:16:00)). The video is never touched. Transcripts are other people's words: they stay on this PC (never
in shared cards or the repo).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab.captions import parse_captions  # noqa: E402  (SRT / WebVTT, shared with overlay.py captions)
from motionlab.timecode import frame_to_tc, label  # noqa: E402
from motionlab.util import ANALYSIS, read_json, safe_name, setup_console  # noqa: E402


def _load(p: Path):
    """A JSON file, or None when it is missing or unreadable."""
    try:
        return read_json(p)
    except (OSError, ValueError):
        return None


SCHEMA = 1
YT_ID = re.compile(r"\[([A-Za-z0-9_-]{11})\]$")


# ------------------------------------------------------------------------------------------------ the reference
def resolve(arg: str) -> dict:
    """name / video -> {name, dir, fps, frames, video, drop}."""
    p = Path(arg)
    hits = [d.name for d in ANALYSIS.iterdir() if d.is_dir() and arg.lower() in d.name.lower()
            and (d / "events.json").exists()] if ANALYSIS.exists() and not p.suffix else []
    if (ANALYSIS / arg / "events.json").exists():
        name = arg
    elif len(hits) == 1:                                        # a unique part of the name, e.g. "4AM"
        name = hits[0]
    elif p.suffix and p.exists():
        name = safe_name(p.stem)
        sj = _load(ANALYSIS / name / "source.json") or {}
        if sj.get("path") and Path(sj["path"]).resolve() != p.resolve():
            raise SystemExit(f"analysis\\{name} belongs to another video ({sj['path']}) - pass its analysis name")
    else:
        raise SystemExit(f"no analysis called '{arg}' and no such video file"
                         + (f" - several match: {', '.join(hits)}" if hits else ""))
    d = ANALYSIS / name
    ev = _load(d / "events.json")
    if ev:
        v = ev["video"]
        drop = bool(((ev.get("config") or {}).get("timecode") or {}).get("drop_frame"))
        return {"name": name, "dir": d, "fps": float(v["fps"]), "frames": int(v["frames"]),
                "video": Path(ev.get("source", {}).get("path") or ""), "drop": drop}
    from motionlab.probe import probe
    info = probe(p)
    fps = float(info.get("fps") or 25)
    return {"name": name, "dir": d, "fps": fps, "frames": int(info.get("frames") or round((info.get("duration_s") or 0) * fps)),
            "video": p.resolve(), "drop": False}


def find_url(ref: dict, url: str | None) -> str:
    if url:
        return url
    from motionlab.knowledge import download_info
    info = download_info(ref["video"].name) if ref["video"].name else {}
    if info.get("url") or info.get("link"):
        return info.get("url") or info.get("link")
    m = YT_ID.search(ref["video"].stem)
    if m:
        return f"https://www.youtube.com/watch?v={m.group(1)}"
    raise SystemExit("where does this video come from? It is not in refs\\downloads.json and its name has no YouTube "
                     "id - pass --url <link>")


def ytdlp() -> str:
    from motionlab.app import system
    exe = system.find("yt-dlp")
    if not exe:
        raise SystemExit("yt-dlp not found - " + system.HOW["yt-dlp"])
    return exe


def run(cmd: list[str], timeout: float = 180) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if r.returncode:
        raise SystemExit(f"yt-dlp failed: {(r.stderr or r.stdout).strip()[-800:]}")
    return r.stdout


def choose_track(info: dict, want: str | None) -> tuple[str, str] | None:
    """('manual' | 'auto', language key): uploaded subtitles in the video's language first, then the auto captions
    of the original audio ('<lang>-orig' on YouTube; the other auto languages are machine translations)."""
    subs = {k: v for k, v in (info.get("subtitles") or {}).items() if k not in ("live_chat", "rechat")}
    auto = info.get("automatic_captions") or {}
    orig = next((k for k in auto if k.endswith("-orig")), None)
    lang = want or info.get("language") or (orig[:-5] if orig else None)

    def same(k):
        return lang and (k == lang or k.split("-")[0] == lang.split("-")[0])
    hit = next((k for k in subs if same(k)), None)
    if hit or (subs and not want and len(subs) == 1):
        return "manual", hit or next(iter(subs))
    if orig and (not want or same(orig[:-5])):
        return "auto", orig
    hit = next((k for k in auto if same(k)), None)
    return ("auto", hit) if hit else None


def save_info(ref: dict, info: dict) -> dict:
    """yt-dlp's info (-J) -> content\\info.json: what the video tells about itself beyond its numbers (2026-10-27,
    Analyser > Notes): the description (links, resources), the creator's chapters, YouTube's *Most replayed* graph
    (heatmap: start / end in seconds, value 0-1), tags, its language and the song a TikTok uses. No formats."""
    keep = ("id", "title", "description", "chapters", "heatmap", "tags", "categories", "language", "uploader",
            "channel", "channel_url", "duration", "upload_date", "webpage_url", "extractor_key", "track", "artist")
    out = {k: info[k] for k in keep if info.get(k) not in (None, "", [])}
    d = ref["dir"] / "content"
    d.mkdir(parents=True, exist_ok=True)
    (d / "info.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


def save_stats(ref: dict, info: dict, url: str) -> dict:
    """yt-dlp's info (-J) -> analysis\\<name>\\content\\stats.json: the public numbers, the outperformer score
    (views / the channel's followers) and the history of every fetch."""
    out = ref["dir"] / "content"
    out.mkdir(parents=True, exist_ok=True)
    p = out / "stats.json"
    old = _load(p) or {}
    num = lambda k: int(info[k]) if isinstance(info.get(k), (int, float)) else None      # noqa: E731
    up = str(info.get("upload_date") or "")
    now = time.strftime("%Y-%m-%d %H:%M")
    s = {"schema": 1, "url": url, "platform": info.get("extractor_key"), "id": info.get("id"),
         "title": info.get("title"), "uploader": info.get("uploader") or info.get("channel"),
         "channel_url": info.get("channel_url") or info.get("uploader_url"),
         "views": num("view_count"), "likes": num("like_count"), "comments": num("comment_count"),
         "shares": num("repost_count"), "saves": num("save_count"),            # TikTok gives both (2026-10-27)
         "followers": num("channel_follower_count"),
         "upload_date": f"{up[:4]}-{up[4:6]}-{up[6:8]}" if len(up) == 8 else None,
         "duration_s": info.get("duration"), "fetched": now}
    if s["views"] is not None and s["followers"]:
        s["outperformer"] = round(s["views"] / s["followers"], 2)
    if s["views"] is not None and s["upload_date"]:
        days = max(1.0, (time.time() - time.mktime(time.strptime(s["upload_date"], "%Y-%m-%d"))) / 86400)
        s["days_online"] = int(days)
        s["views_per_day"] = int(round(s["views"] / days))
    s["history"] = (old.get("history") or []) + [{k: s[k] for k in ("fetched", "views", "likes", "comments",
                                                                     "shares", "saves", "followers")}]
    p.write_text(json.dumps(s, indent=1, ensure_ascii=False), encoding="utf-8")
    return s


THUMB_EXT = {"image/jpeg": ".jpg", "image/jpg": ".jpg", "image/webp": ".webp", "image/png": ".png"}


def save_thumbnail(ref: dict, info: dict, measure: bool = True) -> Path:
    """yt-dlp's info (-J) -> the video's thumbnail as the platform shows it: analysis\\<name>\\content\\thumbnail.<ext>
    (the biggest one offered) + its measures (thumbnail.json). Raises on a network error."""
    import urllib.error
    import urllib.request
    cands = sorted((t for t in (info.get("thumbnails") or []) if t.get("url")),
                   key=lambda t: (-(t.get("width") or 0) * (t.get("height") or 0), -(t.get("preference") or -99)))
    urls = [u for u in [info.get("thumbnail"), *info.get("_urls", []), *(t["url"] for t in cands[:3])] if u]
    if not urls:
        raise SystemExit("the platform gives no thumbnail for this video")
    data, err = None, None
    for url in dict.fromkeys(urls):                             # yt-dlp's own pick first, then the biggest offered
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read(20_000_000)
                ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            break
        except urllib.error.HTTPError as e:                     # e.g. YouTube's maxresdefault missing: the next one
            err = e
    if data is None:
        raise err
    ext = THUMB_EXT.get(ctype) or next((e for e in (".jpg", ".webp", ".png") if e in url.lower().split("?")[0]), ".jpg")
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        ext = ".webp"
    elif data[:3] == b"\xff\xd8\xff":
        ext = ".jpg"
    elif data[:8] == b"\x89PNG\r\n\x1a\n":
        ext = ".png"
    out = ref["dir"] / "content"
    out.mkdir(parents=True, exist_ok=True)
    dest = out / f"thumbnail{ext}"
    tmp = out / f".thumbnail{ext}.part"
    tmp.write_bytes(data)
    tmp.replace(dest)
    for old in out.glob("thumbnail.*"):                         # one thumbnail: an older one in another format goes
        if old != dest and old.suffix.lower() in (".jpg", ".webp", ".png"):
            old.unlink()
    if not measure:                                             # a notes folder: no analysis to measure it for
        return dest
    try:
        from motionlab import thumbnail as TH
        TH.measure_ref(ref["name"], force=True)
    except Exception as e:                                      # noqa: BLE001 - the picture is saved; measures later
        print(f"(thumbnail saved, not measured: {type(e).__name__}: {e})")
    return dest


def _thumb_note(ref: dict, info: dict, measure: bool = True) -> None:
    try:
        p = save_thumbnail(ref, info, measure)
        print(f"thumbnail: {p}")
    except SystemExit as e:
        print(f"thumbnail: {e}")
    except Exception as e:                                      # noqa: BLE001 - a network hiccup is no failure
        print(f"thumbnail not saved: {type(e).__name__}: {e}")


def thumbnail(args) -> int:
    ref = resolve(args.target)
    url = find_url(ref, args.url)
    print(f"{ref['name']}: asking {url} for its thumbnail ...", flush=True)
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", url)
    try:
        info = json.loads(run([ytdlp(), "-J", "--skip-download", "--no-playlist", "--no-warnings", url]))
    except SystemExit as e:
        if not m:
            raise
        # YouTube asks yt-dlp to sign in now and then; its thumbnails sit at a fixed address anyway
        print(f"({str(e)[:90]}... - taking YouTube's thumbnail address directly)")
        info = {"_urls": [f"https://i.ytimg.com/vi/{m.group(1)}/{k}.jpg"
                          for k in ("maxresdefault", "sddefault", "hqdefault")]}
    p = save_thumbnail(ref, info)
    print(p)
    return 0


def stats_line(s: dict) -> str:
    n = lambda v: "-" if v is None else f"{v:,}"                                        # noqa: E731
    return (f"{n(s.get('views'))} views · {n(s.get('likes'))} likes · {n(s.get('comments'))} comments · "
            + (f"{n(s['shares'])} shares · " if s.get("shares") is not None else "")
            + (f"{n(s['saves'])} saves · " if s.get("saves") is not None else "")
            + f"{n(s.get('followers'))} followers"
            + (f" · {s['outperformer']}x its followers" if s.get("outperformer") is not None else "")
            + (f" · online since {s['upload_date']} ({s.get('views_per_day', 0):,} views/day)" if s.get("upload_date")
               else ""))


def stats(args) -> int:
    ref = resolve(args.target)
    url = find_url(ref, args.url)
    print(f"{ref['name']}: asking {url} for its numbers ...", flush=True)
    info = json.loads(run([ytdlp(), "-J", "--skip-download", "--no-playlist", "--no-warnings", url]))
    s = save_stats(ref, info, url)
    print(stats_line(s))
    print(ref["dir"] / "content" / "stats.json")
    _thumb_note(ref, info)
    return 0


def transcript(args) -> int:
    ref = resolve(args.target)
    tj = ref["dir"] / "content" / "transcript.json"
    if tj.exists() and not args.force:
        print(f"already done: {tj} (--force fetches again)")
        return show_lines(ref, _load(tj), None, None, limit=8)
    return show_lines(ref, fetch_subtitles(ref, find_url(ref, args.url), args.lang), None, None, limit=8)


def fetch_subtitles(ref: dict, url: str, lang: str | None = None, measure: bool = True) -> dict:
    """The platform's subtitles of ref's video -> ref["dir"]\\content\\transcript.json + .txt (and the numbers and the
    thumbnail from the same answer). ref = resolve()'s dict - or a notes folder's (Analyser > Notes, 2026-10-27).
    Raises SystemExit when the video has none."""
    out = ref["dir"] / "content"
    tj = out / "transcript.json"
    exe = ytdlp()
    print(f"{ref['name']}: asking {url} for subtitles ...", flush=True)
    info = json.loads(run([exe, "-J", "--skip-download", "--no-playlist", "--no-warnings", url]))
    print(stats_line(save_stats(ref, info, url)), flush=True)          # the same answer has the video's numbers
    save_info(ref, info)                                               # ... its chapters, description, Most replayed
    _thumb_note(ref, info, measure)                                    # ... and its thumbnail
    track = choose_track(info, lang)
    if not track:
        langs = sorted(set(info.get("subtitles") or {}) | {k for k in (info.get("automatic_captions") or {}) if k.endswith("-orig")})
        raise SystemExit("this video has no subtitles or captions" + (f" in '{lang}' (it has: {', '.join(langs)})"
                         if lang and langs else "") + " - speech to text can hear it instead (Settings > Programs)")
    kind, key = track
    dur = info.get("duration")
    vid_dur = ref["frames"] / ref["fps"]
    if dur and abs(float(dur) - vid_dur) > 2:
        print(f"WARNING: the online video lasts {float(dur):.1f} s, this one {vid_dur:.1f} s - a different cut? "
              "Timings may be off.", flush=True)
    subs_dir = out / "subs"
    subs_dir.mkdir(parents=True, exist_ok=True)
    for old in subs_dir.glob("*"):
        old.unlink()
    run([exe, "--skip-download", "--no-playlist", "--no-warnings", "--write-auto-subs" if kind == "auto" else "--write-subs",
         "--sub-langs", key, "--sub-format", "vtt/srt/best", "-o", str(subs_dir / "%(id)s.%(ext)s"), url])
    files = sorted(subs_dir.glob("*.vtt")) + sorted(subs_dir.glob("*.srt"))
    if not files:
        raise SystemExit(f"yt-dlp wrote no caption file into {subs_dir}")
    lines, has_words = parse_captions(files[0].read_text(encoding="utf-8", errors="replace"))
    fps, n, drop = ref["fps"], ref["frames"], ref["drop"]

    def fr(t):
        return max(0, min(n - 1, int(round(t * fps))))
    rows = []
    for l in lines:
        a, b = fr(l["t0"]), fr(max(l["t1"], l["t0"]))
        rows.append({"start": a, "end": max(a, b), "start_tc": frame_to_tc(a, fps, drop),
                     "end_tc": frame_to_tc(max(a, b), fps, drop), "t0": round(l["t0"], 3), "t1": round(l["t1"], 3),
                     "text": l["text"], "words": [{"f": fr(w["t"]), "t": w["t"], "w": w["w"]} for w in l["words"]]})
    data = {"schema": SCHEMA, "name": ref["name"], "source": "subtitles", "kind": kind, "lang": key.removesuffix("-orig"),
            "track": key, "word_timings": has_words, "url": url, "title": info.get("title"),
            "fetched": time.strftime("%Y-%m-%d %H:%M"), "fps": fps, "frames": n, "drop_frame": drop,
            "caption_file": files[0].name, "words": sum(len(r["text"].split()) for r in rows), "lines": rows}
    tj.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    txt = [f"# {ref['name']} - transcript ({'uploaded subtitles' if kind == 'manual' else 'auto captions'}, {key}), "
           f"{fps:g} fps, frame + timecode per line", ""]
    txt += [f"{label(r['start'], fps, drop)}  {r['text']}" for r in rows]
    (out / "transcript.txt").write_text("\n".join(txt) + "\n", encoding="utf-8")
    print(f"{len(rows)} lines, {data['words']} words ({'uploaded subtitles' if kind == 'manual' else 'auto captions'} "
          f"'{key}'{', word timings' if has_words else ''}) -> {tj}")
    return data


def speech_transcript(ref: dict, log=print, names: str = "") -> dict | None:
    """The transcript by speech to text (faster-whisper, when it is installed with its model - Settings > Programs >
    Speech to text): for a video whose platform has no subtitles, or that has no known link. The analysis' own
    audio.wav is heard (the source is never touched); the times follow the video (the audio's start offset added)."""
    from motionlab import speech as SP
    if not SP.available() or not SP.model_ready("small"):
        return None
    d = ref["dir"]
    ev = _load(d / "events.json") or {}
    off = float(((ev.get("audio") or {}).get("offset_s")) or 0.0)
    media = d / "audio.wav" if (d / "audio.wav").exists() else ref["video"]
    if not media or not Path(media).exists():
        return None
    log(f"{ref['name']}: no subtitles - listening (speech to text, small) ...")
    t0 = time.time()
    sp = SP.transcribe(media, "small", names=names, log=log)
    fps, n, drop = ref["fps"], ref["frames"], ref["drop"]

    def fr(t):
        return max(0, min(n - 1, int(round((t + off) * fps))))
    rows = []
    for l in sp["lines"]:
        a, b = fr(l["t0"]), fr(max(l["t1"], l["t0"]))
        rows.append({"start": a, "end": max(a, b), "start_tc": frame_to_tc(a, fps, drop),
                     "end_tc": frame_to_tc(max(a, b), fps, drop), "t0": round(l["t0"] + off, 3),
                     "t1": round(l["t1"] + off, 3), "text": l["text"],
                     "words": [{"f": fr(w["t"]), "t": round(w["t"] + off, 3), "w": w["w"]} for w in l["words"]]})
    data = {"schema": SCHEMA, "name": ref["name"], "source": "speech", "kind": sp.get("kind"), "lang": sp.get("lang"),
            "word_timings": True, "fetched": time.strftime("%Y-%m-%d %H:%M"), "fps": fps, "frames": n,
            "drop_frame": drop, "seconds": round(time.time() - t0, 1),
            "words": sum(len(r["text"].split()) for r in rows), "lines": rows}
    out = d / "content"
    out.mkdir(parents=True, exist_ok=True)
    (out / "transcript.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    txt = [f"# {ref['name']} - transcript (speech to text, {data['kind']}, {data['lang']}), {fps:g} fps, frame + timecode "
           "per line", ""] + [f"{label(r['start'], fps, drop)}  {r['text']}" for r in rows]
    (out / "transcript.txt").write_text("\n".join(txt) + "\n", encoding="utf-8")
    log(f"{len(rows)} lines, {data['words']} words by speech to text in {data['seconds']} s -> {out / 'transcript.json'}")
    return data


def auto(name: str, log=print) -> list[str]:
    """After a content-creation analysis (analyze.py --focus content / both): the transcript - the platform's
    subtitles when the video's link is known, else speech to text when it is installed - and the video's numbers
    (views, followers). Never raises and never fails the analysis: what could not be done comes back as notes."""
    notes = []
    try:
        ref = resolve(name)
    except SystemExit as e:
        return [str(e)]
    out = ref["dir"] / "content"
    try:
        url = find_url(ref, None)
    except SystemExit:
        url = None
    if not (out / "transcript.json").exists() and url:
        try:
            transcript(argparse.Namespace(target=name, url=url, lang=None, force=False))
        except SystemExit as e:
            notes.append(f"subtitles: {e}")
        except Exception as e:                                  # noqa: BLE001 - a network hiccup, an odd caption file
            notes.append(f"subtitles: {type(e).__name__}: {e}")
    if not (out / "transcript.json").exists():
        try:
            if speech_transcript(ref, log) is None:
                notes.append("no transcript: " + ("the platform has no subtitles for it" if url else "no link known")
                             + " and speech to text is not installed (Settings > Programs > Speech to text)")
        except Exception as e:                                  # noqa: BLE001
            notes.append(f"speech to text: {type(e).__name__}: {e}")
    if url and not (out / "stats.json").exists():
        try:
            stats(argparse.Namespace(target=name, url=url))
        except SystemExit as e:
            notes.append(f"views / followers: {e}")
        except Exception as e:                                  # noqa: BLE001
            notes.append(f"views / followers: {type(e).__name__}: {e}")
    return notes


def show_lines(ref: dict, data: dict, a: int | None, b: int | None, limit: int = 0) -> int:
    fps, drop = data["fps"], data.get("drop_frame", False)
    rows = [r for r in data["lines"] if (a is None or r["end"] >= a) and (b is None or r["start"] <= b)]
    for r in rows[:limit or None]:
        print(f"  {label(r['start'], fps, drop)}  {r['text']}")
    if limit and len(rows) > limit:
        print(f"  ... {len(rows) - limit} more (content.py show {ref['name']})")
    return 0


def main() -> int:
    setup_console()
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("transcript", help="fetch the subtitles and write the transcript")
    t.add_argument("target", help="analysis name or video file")
    t.add_argument("--url", help="the video's link, if the lab cannot tell")
    t.add_argument("--lang", help="language code, e.g. en (default: the video's own)")
    t.add_argument("--force", action="store_true", help="fetch again")
    st = sub.add_parser("stats", help="views, likes, comments, followers, upload date -> content\\stats.json")
    st.add_argument("target")
    st.add_argument("--url")
    th = sub.add_parser("thumbnail", help="the video's thumbnail -> content\\thumbnail.<ext> (+ its measures)")
    th.add_argument("target")
    th.add_argument("--url")
    s = sub.add_parser("show", help="print the transcript (or a frame range of it)")
    s.add_argument("target")
    s.add_argument("start", nargs="?", type=int)
    s.add_argument("end", nargs="?", type=int)
    args = ap.parse_args()
    if args.cmd == "transcript":
        return transcript(args)
    if args.cmd == "stats":
        return stats(args)
    if args.cmd == "thumbnail":
        return thumbnail(args)
    ref = resolve(args.target)
    data = _load(ref["dir"] / "content" / "transcript.json")
    if not data:
        raise SystemExit(f"no transcript yet - run: content.py transcript {ref['name']}")
    return show_lines(ref, data, args.start, args.end)


if __name__ == "__main__":
    sys.exit(main())
