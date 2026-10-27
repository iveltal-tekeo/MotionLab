"""Notes from videos (the Analyser's third way, 2026-10-27): what a video says and shows, as notes - a TL;DR, the key
takeaways, the sections, the steps, what to apply, the resources and a context block for another AI, each point with
frame + timecode (the design: tools\\motionlab\\notes.py and docs\\plans.md 0.6.5 *Notes - the research*).

    .venv\\Scripts\\python tools\\notes.py prepare <video> [--url <link>] [--ask "<what you want from it>"]
          [--tags "a, b"] [--label "<name>"] [--force]
          MotionLab's part (no Claude): -> analysis\\notes\\<name>\\ - the words (the platform's subtitles when the
          link is known, else speech to text when it is installed), what yt-dlp knows (the chapters, the description,
          YouTube's Most replayed, the numbers, the thumbnail), the key frames where the screen changes on sheets of
          12 (each labelled f480 (00:00:16:00)), the sponsor parts (SponsorBlock, YouTube). Ends with NOTES: <name>.
    .venv\\Scripts\\python tools\\notes.py show <name>       what Claude reads first (then the transcript / sheets)
    .venv\\Scripts\\python tools\\notes.py save <name> <draft.json>
          Claude's notes through the gate (every quote found in the transcript, the frame + timecode set by the tool,
          the limits) -> notes.json + notes.md; nothing is written when a check fails (exit 1, every problem listed)
    .venv\\Scripts\\python tools\\notes.py pending           the notes waiting for Claude
    .venv\\Scripts\\python tools\\notes.py list

<name> = the folder in analysis\\notes\\. The video is only read (hard rule 1: SHA-256 recorded and checked, every
write inside the notes folder). The /take-notes skill is Claude's side.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import content as C  # noqa: E402  (the subtitles, speech to text and the numbers - the same files as an analysis)
from motionlab import notes as N  # noqa: E402
from motionlab.timecode import frame_to_tc, label  # noqa: E402
from motionlab.util import LAB, SourceGuard, safe_name, setup_console, sha256_file, tool, write_json  # noqa: E402

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".m4v", ".avi", ".webm", ".mts", ".mxf"}
MAX_FRAMES, MIN_FRAMES, SCENE = 36, 8, 0.3          # key frames: at most 36, at least 8 spread out, a change = 0.3
PER_SHEET, COLS = 12, 4
YT = re.compile(r"(?:v=|youtu\.be/|shorts/|live/)([A-Za-z0-9_-]{11})")


def _fps(v: dict) -> float:
    from motionlab.probe import snap_rate
    r, a = v.get("r_fps"), v.get("avg_fps")
    base = a if (r and a and abs(r - a) / a > 0.01) else (r or a or 30.0)     # a phone's variable rate: its average
    return snap_rate(float(base))


# ------------------------------------------------------------------------------------------------ the key frames
def _keyframe_times(video: Path, scores: Path) -> list[tuple[float, float]]:
    """(pts seconds, scene score) of every keyframe: ffmpeg decodes only the keyframes (-skip_frame nokey) at 64 px -
    seconds even for an hour of video."""
    subprocess.run([tool("ffmpeg"), "-v", "error", "-nostdin", "-skip_frame", "nokey", "-i", str(video), "-an", "-sn",
                    "-vf", f"scale=64:-2,select='gte(scene\\,0)',metadata=mode=print:file={scores.name}",
                    "-fps_mode", "passthrough", "-f", "null", "-"], check=True, capture_output=True, cwd=str(scores.parent))
    out, t = [], None
    for ln in scores.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.search(r"pts_time:([-\d.]+)", ln)
        if m:
            t = float(m.group(1))
            continue
        m = re.match(r"lavfi\.scene_score=([\d.]+)", ln.strip())
        if m and t is not None:
            out.append((t, float(m.group(1))))
            t = None
    return out


def _pick(keys: list[tuple[float, float]], start: float, dur: float) -> list[float]:
    """The keyframes where the screen changes (score >= SCENE, the first one always), at most MAX_FRAMES spread over
    the video; at least MIN_FRAMES spread evenly when it hardly changes (a talking head)."""
    if not keys:
        return []
    change = [keys[0][0]] + [t for t, s in keys[1:] if s >= SCENE]
    if len(change) > MAX_FRAMES:
        step = len(change) / MAX_FRAMES
        change = [change[int(i * step)] for i in range(MAX_FRAMES)]
    want = min(MIN_FRAMES, len(keys))
    if len(change) < want:
        times = [t for t, _ in keys]
        for i in range(want):
            goal = start + dur * (i + 0.5) / want
            near = min(times, key=lambda x: abs(x - goal))
            if near not in change:
                change.append(near)
    return sorted(set(change))


def _font(size: int):
    from PIL import ImageFont
    import os
    d = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    for p in [d / "consola.ttf", d / "arial.ttf", Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")]:
        try:
            return ImageFont.truetype(str(p), size)
        except OSError:
            pass
    return ImageFont.load_default()


def key_frames(ref: dict, info: dict, guard: SourceGuard, log=print) -> list[dict]:
    """frames\\sheet_NN.jpg (12 key frames each, labelled with frame + timecode) + frames.json + cover.jpg."""
    from PIL import Image, ImageDraw
    d = ref["dir"] / "frames"
    d.mkdir(parents=True, exist_ok=True)
    for old in list(d.glob("sheet_*.jpg")) + [d / "cover.jpg", d / "frames.json"]:
        if old.exists():
            guard.check(old).unlink()
    v = info["video"]
    start, fps, n, drop = float(v.get("start_time") or 0), ref["fps"], ref["frames"], ref["drop"]
    dur = n / fps
    vertical = (v.get("display_height") or 1) > (v.get("display_width") or 1)
    tw = 240 if vertical else 400
    with tempfile.TemporaryDirectory(dir=str(d)) as tmp:
        tmp = Path(guard.check(Path(tmp)))
        keys = _keyframe_times(ref["video"], tmp / "scores.txt")
        times = _pick(keys, start, dur)
        log(f"key frames: {len(keys)} keyframes read, {len(times)} kept (where the screen changes)")
        tiles = []
        for i, t in enumerate(times):
            f = max(0, min(n - 1, int(round((t - start) * fps))))
            out = tmp / f"k{i:03d}.jpg"
            subprocess.run([tool("ffmpeg"), "-v", "error", "-nostdin", "-ss", f"{max(0.0, t - start):.3f}", "-i",
                            str(ref["video"]), "-frames:v", "1", "-vf", f"scale={tw}:-2", "-q:v", "3", str(out)],
                           capture_output=True)
            if out.exists():
                tiles.append((f, out))
        frames = []
        font = _font(15)
        for s in range(0, len(tiles), PER_SHEET):
            part = tiles[s:s + PER_SHEET]
            ims = [Image.open(p).convert("RGB") for _, p in part]
            th = max(im.height for im in ims)
            rows = (len(part) + COLS - 1) // COLS
            sheet = Image.new("RGB", (COLS * (tw + 8) + 8, rows * (th + 34) + 8), (18, 18, 22))
            dr = ImageDraw.Draw(sheet)
            name = f"sheet_{s // PER_SHEET + 1:02d}.jpg"
            for k, ((f, _), im) in enumerate(zip(part, ims)):
                x, y = 8 + (k % COLS) * (tw + 8), 8 + (k // COLS) * (th + 34)
                sheet.paste(im, (x, y))
                dr.text((x + 2, y + th + 6), label(f, fps, drop), fill=(255, 196, 0), font=font)
                frames.append({"f": f, "tc": frame_to_tc(f, fps, drop), "sheet": name, "tile": k + 1})
            sheet.save(guard.check(d / name), quality=85)
        if tiles:
            pick = min(tiles, key=lambda x: abs(x[0] - n * 0.1))[1]
            Image.open(pick).convert("RGB").save(guard.check(d / "cover.jpg"), quality=85)
    write_json(guard.check(d / "frames.json"), {"fps": fps, "made": time.strftime("%Y-%m-%d %H:%M"), "frames": frames})
    return frames


# ------------------------------------------------------------------------------------------------ SponsorBlock
def sponsor_parts(url: str, fps: float, frames: int) -> list[dict]:
    """SponsorBlock's ranges of a YouTube video in frames (the sponsor read, self-promotion, "like and subscribe",
    intro / outro, the highlight) - asked like yt-dlp does, with the first 4 characters of the id's SHA-256, so the
    video is not named. [] for other platforms."""
    m = YT.search(url or "")
    if not m:
        return []
    vid = m.group(1)
    cats = ["sponsor", "selfpromo", "interaction", "intro", "outro", "poi_highlight"]
    q = urllib.parse.urlencode({"categories": json.dumps(cats), "actionTypes": json.dumps(["skip", "poi"])})
    req = urllib.request.Request(f"https://sponsor.ajay.app/api/skipSegments/"
                                 f"{hashlib.sha256(vid.encode('ascii')).hexdigest()[:4]}?{q}",
                                 headers={"User-Agent": "MotionLab"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read(2_000_000).decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:                                  # nobody marked anything for these 4 characters
            return []
        raise
    out = []
    for v in data if isinstance(data, list) else []:
        if v.get("videoID") != vid:
            continue
        for s in v.get("segments") or []:
            a, b = (s.get("segment") or [0, 0])[:2]
            fa = max(0, min(frames - 1, int(round(float(a) * fps))))
            out.append({"category": s.get("category"), "start": fa,
                        "end": max(fa, min(frames - 1, int(round(float(b) * fps))))})
    return sorted(out, key=lambda s: s["start"])


# ------------------------------------------------------------------------------------------------ prepare
def prepare(a) -> int:
    from motionlab.knowledge import download_info
    from motionlab.probe import probe
    video = Path(a.video).expanduser().resolve()
    if not video.is_file() or video.suffix.lower() not in VIDEO_EXT:
        raise SystemExit(f"not a video file: {video}")
    if LAB.resolve() in video.parents and video.parts[len(LAB.resolve().parts)] in ("analysis", ".app", "tools"):
        raise SystemExit("pick the original video, not a file the lab made")
    name = N.unique_name(video)
    d = N.ROOT / name
    d.mkdir(parents=True, exist_ok=True)
    guard = SourceGuard(video, d)
    old = N._load(d / "note.json") or {}
    print(f"notes: {video.name} -> {d}", flush=True)
    pi = probe(video)
    fps = _fps(pi["video"])
    frames = int(pi["video"].get("nb_frames") or round(float(pi.get("duration_s") or 0) * fps))
    if frames < 1:
        raise SystemExit("this video has no frames")
    sha = sha256_file(video)
    if old.get("sha256") and old["sha256"] != sha:
        print("NOTE: this file changed since its notes were made (another version of the video?)")
    dl = download_info(video.name) or {}
    url = a.url or dl.get("url") or dl.get("link") or ""
    if not url and (m := C.YT_ID.search(video.stem)):
        url = f"https://www.youtube.com/watch?v={m.group(1)}"
    title = dl.get("title") or re.sub(r"\s*\[[A-Za-z0-9_-]{6,}\]$", "", video.stem)
    n = {**old, "schema": N.SCHEMA, "name": name, "video": str(video), "sha256": sha, "fps": fps, "frames": frames,
         "duration_s": round(frames / fps, 3), "drop_frame": False, "width": pi["video"].get("display_width"),
         "height": pi["video"].get("display_height"), "url": url or None, "platform": dl.get("platform"),
         "uploader": dl.get("uploader"), "title": old.get("title") or title,
         "created": old.get("created") or time.strftime("%Y-%m-%d %H:%M"), "issues": []}
    if a.label:
        n["label"] = " ".join(a.label.split())[:120]
    if a.ask is not None:
        n["ask"] = " ".join(a.ask.split())[:1000]
    if a.tags is not None:
        n["tags"] = [t for t in dict.fromkeys(" ".join(x.split()).lower()[:40] for x in a.tags.split(",")) if t][:12]
    write_json(guard.check(d / "note.json"), n)
    ref = {"name": name, "dir": d, "fps": fps, "frames": frames, "video": video, "drop": False}
    issues = []
    # 1. the words: the platform's subtitles (+ its numbers, chapters, description, Most replayed), else speech to text
    have = N.transcript(d) is not None and not a.force
    if url and not have:
        try:
            C.fetch_subtitles(ref, url, measure=False)
        except SystemExit as e:
            issues.append(f"subtitles: {e}")
            print(f"subtitles: {e}", flush=True)
        except Exception as e:                                  # noqa: BLE001 - a network hiccup, an odd caption file
            issues.append(f"subtitles: {type(e).__name__}: {e}")
            print(f"subtitles: {type(e).__name__}: {e}", flush=True)
    info = N._load(d / "content" / "info.json") or {}
    n["title"] = info.get("title") or n["title"]
    n["uploader"] = info.get("uploader") or info.get("channel") or n.get("uploader")
    n["platform"] = n.get("platform") or info.get("extractor_key")
    if N.transcript(d) is None:
        names = " ".join(x for x in [n.get("title"), n.get("uploader")] + [c.get("title") for c in info.get("chapters") or []]
                         if x)[:220]
        try:
            if C.speech_transcript(ref, print, names) is None:
                issues.append("no words: " + ("the platform has no subtitles for it" if url else "no link known")
                              + " and speech to text is not installed (Settings > Programs > Speech to text)")
        except Exception as e:                                  # noqa: BLE001
            issues.append(f"speech to text: {type(e).__name__}: {e}")
    # 2. the creator's chapters, YouTube's Most replayed, the sponsor parts
    n["chapters"] = N.chapters_of(info, fps, frames)
    n["replayed"] = N.replayed_of(info, fps, frames)
    try:
        n["skip"] = sponsor_parts(url, fps, frames)
    except Exception as e:                                      # noqa: BLE001 - optional: never stops the notes
        n["skip"] = old.get("skip") or []
        print(f"SponsorBlock: {type(e).__name__}: {e}", flush=True)
    # 3. what is shown
    try:
        fr = key_frames(ref, pi, guard)
    except Exception as e:                                      # noqa: BLE001 - the words alone still make notes
        fr = []
        issues.append(f"key frames: {type(e).__name__}: {e}")
    n["issues"] = issues
    write_json(guard.check(d / "note.json"), n)
    if not guard.verify_unchanged():
        raise SystemExit(f"WARNING: the source video changed while the notes were prepared: {video}")
    tr = N.transcript(d)
    print(f"words: {tr['source']} ({tr.get('lang')}), {len(tr['lines'])} lines, {tr.get('words')} words" if tr
          else "words: none")
    print(f"chapters: {len(n['chapters'])} · most replayed: {len(n['replayed'])} · sponsor parts: {len(n['skip'])} · "
          f"key frames: {len(fr)}")
    for x in issues:
        print(f"NOTE: {x}")
    print(f"source unchanged (SHA-256 {sha[:12]}...)")
    if tr is None and not fr:
        raise SystemExit("nothing to take notes from: no words and no frames")
    print(f"NOTES: {name}")
    return 0


def save(a) -> int:
    p = Path(a.draft)
    try:
        draft = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SystemExit(f"cannot read {p}: {e}") from None
    try:
        notes = N.save_notes(a.name, draft)
    except ValueError as e:
        print(e)
        return 1
    d = N.note_dir(a.name)
    print(f"saved: {len(notes['takeaways'])} takeaways, {len(notes['sections'])} sections, {len(notes['steps'])} steps, "
          f"{len(notes['apply'])} actions, {len(notes['resources'])} resources -> {d / 'notes.json'}, {d / 'notes.md'}")
    return 0


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("video")
    p.add_argument("--url")
    p.add_argument("--ask")
    p.add_argument("--tags")
    p.add_argument("--label")
    p.add_argument("--force", action="store_true", help="fetch / hear the words again")
    s = sub.add_parser("show")
    s.add_argument("name")
    s = sub.add_parser("save")
    s.add_argument("name")
    s.add_argument("draft")
    sub.add_parser("pending")
    sub.add_parser("list")
    a = ap.parse_args()
    if a.cmd == "prepare":
        return prepare(a)
    if a.cmd == "show":
        print(N.show_text(safe_name(a.name)))
        return 0
    if a.cmd == "save":
        return save(a)
    if a.cmd == "pending":
        print("\n".join(N.pending()) or "none")
        return 0
    for x in N.list_notes():
        print(f"{x['name']}  [{x['status']}]  {x['label']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
