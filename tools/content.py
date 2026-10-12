"""Content analysis, step 1 (0.4): what a reference SAYS - its transcript, every line with frame + timecode.

Source: the platform's own subtitles through yt-dlp - uploaded ones first, else the auto-generated captions in the
video's own language (YouTube's carry word timings). No model, nothing heavy, a few seconds per video. Local
Whisper for videos without subtitles comes later, only after it is measured (docs\\plans.md 0.4).

    .venv\\Scripts\\python tools\\content.py transcript <name | video> [--url <link>] [--lang en] [--force]
    .venv\\Scripts\\python tools\\content.py show <name> [<start frame> <end frame>]
    .venv\\Scripts\\python tools\\content.py stats <name | video> [--url <link>]
          how the video performs (0.3.5): views, likes, comments, the channel's followers, the upload date ->
          analysis\\<name>\\content\\stats.json; views / followers = the outperformer score; every fetch is kept
          in its history. The transcript fetch saves them too (the same request).

<name> = the analysis folder (References); a video that has no analysis yet works too (its frame rate is probed).
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
                                                                     "followers")}]
    p.write_text(json.dumps(s, indent=1, ensure_ascii=False), encoding="utf-8")
    return s


def stats_line(s: dict) -> str:
    n = lambda v: "-" if v is None else f"{v:,}"                                        # noqa: E731
    return (f"{n(s.get('views'))} views · {n(s.get('likes'))} likes · {n(s.get('comments'))} comments · "
            f"{n(s.get('followers'))} followers"
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
    return 0


def transcript(args) -> int:
    ref = resolve(args.target)
    out = ref["dir"] / "content"
    tj = out / "transcript.json"
    if tj.exists() and not args.force:
        print(f"already done: {tj} (--force fetches again)")
        return show_lines(ref, _load(tj), None, None, limit=8)
    url = find_url(ref, args.url)
    exe = ytdlp()
    print(f"{ref['name']}: asking {url} for subtitles ...", flush=True)
    info = json.loads(run([exe, "-J", "--skip-download", "--no-playlist", "--no-warnings", url]))
    print(stats_line(save_stats(ref, info, url)), flush=True)          # the same answer has the video's numbers
    track = choose_track(info, args.lang)
    if not track:
        langs = sorted(set(info.get("subtitles") or {}) | {k for k in (info.get("automatic_captions") or {}) if k.endswith("-orig")})
        raise SystemExit("this video has no subtitles or captions" + (f" in '{args.lang}' (it has: {', '.join(langs)})"
                         if args.lang and langs else "") + " - a local transcription (Whisper) comes later in 0.4")
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
    return show_lines(ref, data, None, None, limit=8)


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
    s = sub.add_parser("show", help="print the transcript (or a frame range of it)")
    s.add_argument("target")
    s.add_argument("start", nargs="?", type=int)
    s.add_argument("end", nargs="?", type=int)
    args = ap.parse_args()
    if args.cmd == "transcript":
        return transcript(args)
    if args.cmd == "stats":
        return stats(args)
    ref = resolve(args.target)
    data = _load(ref["dir"] / "content" / "transcript.json")
    if not data:
        raise SystemExit(f"no transcript yet - run: content.py transcript {ref['name']}")
    return show_lines(ref, data, args.start, args.end)


if __name__ == "__main__":
    sys.exit(main())
