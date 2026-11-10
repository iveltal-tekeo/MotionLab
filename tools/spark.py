"""SPARK - why a video worked (the Analyser's second way, 2026-10-30): the lab prepares what Claude needs to explain a
video's result - the words, the first and last 3 s, a frame per shot, the pacing, the numbers and the creator's usual -
then Claude writes one fixed rubric through a gate (the design: tools\\motionlab\\spark.py, docs\\plans.md 0.6.5 *SPARK -
why a video worked*).

    .venv\\Scripts\\python tools\\spark.py prepare <video> [--url <link>] [--ask "<what you want to know>"]
          [--tags "a, b"] [--label "<name>"] [--force] [--no-lookup]
          MotionLab's part (no Claude): -> analysis\\spark\\<name>\\ - the words (the platform's subtitles when the link
          is known, else the words of the same video's notes or analysis, else speech to text when it is installed),
          the numbers (one lookup of the video and one of the creator's list - started by the user, kept on this PC;
          --no-lookup = none), a light read of the video (the analyser's cut detector and text measure: shots, cuts /
          min, the first 3 s), hook.jpg / end.jpg (the first and last 3 s) and sheets of one frame per shot (each
          labelled f480 (00:00:16:00)). Ends with SPARK: <name>.
    .venv\\Scripts\\python tools\\spark.py numbers <name>     the lookup again (views keep changing)
    .venv\\Scripts\\python tools\\spark.py show <name>        what Claude reads first (the table of numbers, the paths)
    .venv\\Scripts\\python tools\\spark.py save <name> <draft.json>
          Claude's write-up through the gate (the 12 rubric points labelled, every quote found in the words, every
          frame one of the sheets', every number cited from the table, no claim of cause) -> spark.json + spark.md;
          nothing is written when a check fails (exit 1, every problem listed)
    .venv\\Scripts\\python tools\\spark.py pending | list | selfcheck

<name> = the folder in analysis\\spark\\. The video is only read (hard rule 1: SHA-256 recorded and checked, every write
inside the SPARK folder). The /spark skill is Claude's side.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import content as C  # noqa: E402  (the subtitles, speech to text and the numbers - the same files as an analysis)
from motionlab import spark as S  # noqa: E402
from motionlab.timecode import frame_to_tc, label  # noqa: E402
from motionlab.util import LAB, SourceGuard, load_config, safe_name, setup_console, sha256_file, tool, write_json  # noqa: E402

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".m4v", ".avi", ".webm", ".mts", ".mxf"}
SHEET_MAX, PER_SHEET, COLS = 48, 12, 4          # one frame per shot: at most 48 on sheets of 12
HOOK_AT = (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 2.95)   # the first 3 s (the glance, then the hook)
END_N = 6                                        # the last 3 s (a loop, a call to action)
LIST_MAX = 200                                   # the creator's list: its newest videos read at most
SHORT_MAX_S = 180                                # a YouTube Short: vertical and up to 3 minutes
FLASH_S = 0.25                                   # shorter than this between two cuts: a flash, not a shot


def _fps(v: dict) -> float:
    from motionlab.probe import snap_rate
    r, a = v.get("r_fps"), v.get("avg_fps")
    base = a if (r and a and abs(r - a) / a > 0.01) else (r or a or 30.0)     # a phone's variable rate: its average
    return snap_rate(float(base))


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


# ------------------------------------------------------------------------------------------------ the light read
def _frames_cfr(video: Path, w: int, h: int, rate: str, hdr: bool):
    """Every frame at the video's own rate on a fixed grid (frame f = f / fps seconds: the same numbers as its words),
    at the analyser's size - a phone's variable rate gives the same frame numbers as the transcript."""
    from motionlab.signals import StderrTail
    vf = []
    if hdr:
        vf.append("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
                  "tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
    vf.append(f"fps={rate},scale={w}:{h}:flags=area,setsar=1")
    cmd = [tool("ffmpeg"), "-v", "error", "-nostdin", "-i", str(video), "-map", "0:v:0", "-vf", ",".join(vf),
           "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=w * h * 3 * 8)
    err = StderrTail(proc.stderr)
    size, i = w * h * 3, 0
    try:
        while True:
            buf = proc.stdout.read(size)
            if not buf or len(buf) < size:
                break
            yield i, np.frombuffer(buf, np.uint8).reshape(h, w, 3)
            i += 1
    finally:
        proc.stdout.close()
        proc.wait()
        msg = err.text()
        if proc.returncode not in (0, None) and i == 0:
            raise RuntimeError(f"ffmpeg could not read {video}:\n{msg[-800:]}")


def light_read(video: Path, pi: dict, fps: float, tmp: Path, log=print) -> tuple[dict, list[int], list[int]]:
    """The analyser's per-frame numbers on every frame (FrameMetrics, in blocks on a few threads) -> its cut detector:
    (metrics, hard cuts, jump cuts). The small thumbnails the detector compares go to a file in tmp, not memory."""
    import cv2
    from motionlab.detect import Ctx, detect_cuts
    from motionlab.probe import rate_fraction
    from motionlab.signals import BLOCK, FrameMetrics, fit_long_side
    cfg = load_config()
    acfg = cfg["analysis"]
    v = pi["video"]
    w, h = fit_long_side(v["display_aspect"], acfg["long_side_px"])
    tw, th = fit_long_side(v["display_aspect"], acfg["thumb_long_side_px"])
    K = int(acfg["repeat_search_frames"])
    rows: dict[str, list] = {}
    t0, n = time.time(), 0

    def block(before, frames):
        fm = FrameMetrics(w, h, tw, th, v["display_width"], acfg)
        fm.warm(before)
        return [fm.compute(f) for f in frames]
    from collections import deque
    import os
    workers = max(1, min(5, (os.cpu_count() or 2) - 1))
    threads = cv2.getNumThreads()
    cv2.setNumThreads(1)
    tpath = tmp / "thumbs.u8"
    try:
        with open(tpath, "wb") as tf, ThreadPoolExecutor(workers) as ex:
            def collect(fut):
                nonlocal n
                for m, thumb in fut.result():
                    for k, val in m.items():
                        rows.setdefault(k, []).append(val)
                    tf.write(thumb.tobytes())
                    n += 1
                    if n % 1500 == 0:
                        log(f"light read: frame {n} ({n / max(1e-6, time.time() - t0):.0f} fps)")
            pending, cur, last = deque(), [], deque(maxlen=K)
            for _, frame in _frames_cfr(video, w, h, rate_fraction(fps), bool(v.get("hdr"))):
                cur.append(frame)
                if len(cur) == BLOCK:
                    pending.append(ex.submit(block, list(last), cur))
                    last.extend(cur)
                    cur = []
                    while len(pending) > 2 * workers:
                        collect(pending.popleft())
            if cur:
                pending.append(ex.submit(block, list(last), cur))
            while pending:
                collect(pending.popleft())
    finally:
        cv2.setNumThreads(threads)
    if n == 0:
        raise RuntimeError("no frames decoded")
    log(f"light read: {n} frames in {time.time() - t0:.1f} s at {w}x{h}")
    met = {k: np.asarray(val, np.float64) for k, val in rows.items() if len(val) == n}
    met["frame"] = np.arange(n, dtype=np.float64)
    thumbs = np.memmap(tpath, dtype=np.uint8, mode="r", shape=(n, th, tw, 3))
    cuts, jumps = detect_cuts(Ctx(met, thumbs, fps, cfg))
    hard = sorted({int(c["frame"]) for c in cuts if 0 < int(c["frame"]) < n})
    jump = sorted({int(j["frame"]) for j in jumps if 0 < int(j["frame"]) < n} - set(hard))
    del thumbs
    return met, hard, jump


def _runs(mask: np.ndarray, min_len: int) -> list[tuple[int, int]]:
    out, a = [], None
    for i, val in enumerate(list(mask) + [False]):
        if val and a is None:
            a = i
        elif not val and a is not None:
            if i - a >= min_len:
                out.append((a, i - 1))
            a = None
    return out


def _nwords(text: str) -> int:
    return sum(1 for w in str(text).split() if any(ch.isalnum() for ch in w))


def measures(met: dict, hard: list[int], jump: list[int], n: int, fps: float, tr: dict | None) -> tuple[dict, list, list]:
    """The lab's numbers (measures.json), the pieces between every cut found [[first, last]] (the sheets show them all,
    flashes too) and the shots the numbers count (a flash joined to its neighbour)."""
    cfg = load_config()
    edges = [0] + sorted(set(hard) | set(jump)) + [n]
    shots = [[a, b - 1] for a, b in zip(edges[:-1], edges[1:]) if b - 1 >= a]
    short = max(2, int(round(FLASH_S * fps)))       # a flash / glitch of a few frames is no shot: joined to its neighbour
    merged: list[list[int]] = []
    for sg in shots:
        if merged and (sg[1] - sg[0] + 1 < short or merged[-1][1] - merged[-1][0] + 1 < short):
            merged[-1][1] = sg[1]
        else:
            merged.append(list(sg))
    lens = [(b - a + 1) / fps for a, b in merged]
    mins = n / fps / 60.0
    hook_f = int(round(S.HOOK_S * fps))
    cuts_at = [a for a, _ in merged[1:]]
    pacing = {"shots": len(merged), "cuts": sum(1 for c in cuts_at if c in set(hard)),
              "jump_cuts": sum(1 for c in cuts_at if c not in set(hard)),
              "cuts_per_min": round(len(cuts_at) / mins, 1) if mins else None,
              "avg_shot_s": round(sum(lens) / len(lens), 2) if lens else None,
              "median_shot_s": round(statistics.median(lens), 2) if lens else None,
              "first_cut_s": round(cuts_at[0] / fps, 2) if cuts_at else None,
              "note": "hard cuts and jump cuts (a take cut together); a flash of a few frames is no shot; dissolves and "
                      "other transitions are not counted"}
    hook = {"cuts": sum(1 for c in cuts_at if c < hook_f), "words": None, "text": None, "text_source": "rough",
            "first_words": None}
    ts = np.nan_to_num(np.asarray(met.get("text_score", np.zeros(n)), float))[:n]
    tcfg = cfg.get("text", {})
    runs = _runs(ts >= float(tcfg.get("score_min", 0.012)), int(tcfg.get("min_frames", 6)))
    on = np.zeros(len(ts), bool)
    for a, b in runs:
        on[a:b + 1] = True
    hook["text"] = bool(on[:hook_f].any()) if len(on) else None
    text = {"visible_pct": round(100 * float(on.mean()), 1) if len(on) else None,
            "note": "text-like shapes on screen - signs and textures count too (rough)"}
    speech = None
    if tr and tr.get("lines"):
        lines = tr["lines"]
        talk = np.zeros(n, bool)
        for ln in lines:
            talk[max(0, int(ln["start"])):min(n, int(ln["end"]) + 1)] = True
        words = sum(_nwords(ln["text"]) for ln in lines)
        speech = {"words": words, "words_per_min": round(words / mins, 1) if mins else None,
                  "talk_pct": round(100 * float(talk.mean()), 1)}
        hw, first = 0, []
        for ln in lines:
            if ln.get("words"):
                for w in ln["words"]:
                    if int(w.get("f", 0)) < hook_f and _nwords(w.get("w", "")):
                        hw += 1
                        first.append(str(w.get("w", "")).strip())
            elif ln["start"] < hook_f:
                span = max(1, ln["end"] - ln["start"] + 1)
                k = round(_nwords(ln["text"]) * min(1.0, (hook_f - ln["start"]) / span))
                hw += k
                first += ln["text"].split()[:k]
        hook["words"] = hw
        hook["first_words"] = " ".join(first)[:300] or None
    return {"schema": 1, "made": time.strftime("%Y-%m-%d %H:%M"), "fps": fps, "frames": n,
            "duration_s": round(n / fps, 2), "pacing": pacing, "hook": hook, "speech": speech, "text": text}, shots, merged


# ------------------------------------------------------------------------------------------------ the pictures
def _grab(video: Path, t: float, width: int, out: Path) -> bool:
    subprocess.run([tool("ffmpeg"), "-v", "error", "-nostdin", "-ss", f"{max(0.0, t):.3f}", "-i", str(video),
                    "-frames:v", "1", "-vf", f"scale={width}:-2", "-q:v", "3", str(out)], capture_output=True)
    return out.exists()


def pictures(d: Path, video: Path, pi: dict, fps: float, n: int, pieces: list[list[int]], shots: list[list[int]],
             guard: SourceGuard, log=print) -> dict:
    """shots\\hook.jpg (the first 3 s), end.jpg (the last 3 s), sheet_NN.jpg (the middle frame of each shot, at most
    SHEET_MAX - the first shots always) + shots.json: the shots and every frame on them (the ones a point may show)."""
    from PIL import Image, ImageDraw
    out = d / "shots"
    out.mkdir(parents=True, exist_ok=True)
    for old in list(out.glob("sheet_*.jpg")) + [out / "hook.jpg", out / "end.jpg", out / "shots.json"]:
        if old.exists():
            guard.check(old).unlink()
    v = pi["video"]
    vertical = (v.get("display_height") or 1) > (v.get("display_width") or 1)
    tw = 240 if vertical else 400
    start = float(v.get("start_time") or 0)
    keys = [(i, (a + b) // 2) for i, (a, b) in enumerate(pieces)]
    if len(keys) > SHEET_MAX:                       # the first 8 shots (the hook), then spread over the rest
        head, rest = keys[:8], keys[8:]
        step = len(rest) / (SHEET_MAX - 8)
        keys = head + [rest[int(i * step)] for i in range(SHEET_MAX - 8)]
    hook = sorted({min(n - 1, int(round(t * fps))) for t in HOOK_AT if t * fps < n})
    end = sorted({max(0, n - 1 - int(round(k * 3.0 * fps / (END_N - 1)))) for k in range(END_N)})
    want = sorted({f for _, f in keys} | set(hook) | set(end))
    font = _font(15)
    with tempfile.TemporaryDirectory(dir=str(out)) as tmp:
        tmp = Path(guard.check(Path(tmp)))
        with ThreadPoolExecutor(4) as ex:
            got = dict(zip(want, ex.map(lambda f: (tmp / f"k{f:07d}.jpg") if _grab(video, start + f / fps, tw,
                                                                                    tmp / f"k{f:07d}.jpg") else None,
                                        want)))
        frames = []

        def sheet(tiles: list[tuple[int, str]], name: str, cols: int, kind: str) -> None:
            ims = [(f, cap, Image.open(got[f]).convert("RGB")) for f, cap in tiles if got.get(f)]
            if not ims:
                return
            th_ = max(im.height for _, _, im in ims)
            rows = (len(ims) + cols - 1) // cols
            sh = Image.new("RGB", (cols * (tw + 8) + 8, rows * (th_ + 34) + 8), (18, 18, 22))
            dr = ImageDraw.Draw(sh)
            for k, (f, cap, im) in enumerate(ims):
                x, y = 8 + (k % cols) * (tw + 8), 8 + (k // cols) * (th_ + 34)
                sh.paste(im, (x, y))
                dr.text((x + 2, y + th_ + 6), f"{cap}{label(f, fps, False)}", fill=(255, 196, 0), font=font)
                frames.append({"f": f, "tc": frame_to_tc(f, fps, False), "sheet": name, "tile": k + 1, "kind": kind})
            sh.save(guard.check(out / name), quality=85)
        sheet([(f, "") for f in hook], "hook.jpg", 4 if not vertical else 7, "hook")
        sheet([(f, "") for f in end], "end.jpg", 3 if not vertical else 6, "end")
        for s in range(0, len(keys), PER_SHEET):
            sheet([(f, f"#{i + 1} ") for i, f in keys[s:s + PER_SHEET]], f"sheet_{s // PER_SHEET + 1:02d}.jpg", COLS, "shot")
        if got.get(0):
            Image.open(got[0]).convert("RGB").save(guard.check(out / "cover.jpg"), quality=85)
    shot_rows = [{"n": i + 1, "start": a, "end": b, "key": (a + b) // 2} for i, (a, b) in enumerate(shots)]
    write_json(guard.check(out / "shots.json"), {"fps": fps, "made": time.strftime("%Y-%m-%d %H:%M"),
                                                 "shots": shot_rows, "frames": frames})
    log(f"pictures: the first 3 s ({len(hook)}), the last 3 s ({len(end)}), {len(keys)} of {len(pieces)} pieces on "
        f"{(len(keys) + PER_SHEET - 1) // PER_SHEET} sheet(s)")
    return {"shots": len(shots), "shown": len(frames)}



# ------------------------------------------------------------------------------------------------ the numbers
def _short(url: str, v: dict, info: dict) -> bool:
    dur = float(info.get("duration") or v.get("duration_s") or 0)
    vert = (v.get("height") or 0) > (v.get("width") or 0)
    return "/shorts/" in (url or "") or (vert and 0 < dur <= SHORT_MAX_S)


def creator_list(info: dict, url: str, v: dict, log=print) -> tuple[list[dict], str, str]:
    """The creator's list of videos (one yt-dlp request, no download): (entries, which list, why none)."""
    plat = str(info.get("extractor_key") or v.get("platform") or "").lower()
    if "instagram" in plat:
        return [], "", ("Instagram shows other videos' numbers only to a signed-in account and its terms bar "
                        "automated collection - unknown")
    if "youtube" in plat:
        ch = info.get("channel_url") or (f"https://www.youtube.com/channel/{info['channel_id']}" if info.get("channel_id")
                                         else None)
        if not ch:
            return [], "", "the video names no channel"
        which = "shorts" if _short(url, v, info) else "videos"
        src = f"{ch.rstrip('/')}/{which}"
        extra = ["--extractor-args", "youtubetab:approximate_date"]
    elif "tiktok" in plat:
        src, which, extra = info.get("uploader_url") or info.get("channel_url"), "user", []
        if not src:
            return [], "", "the video names no creator page"
    else:
        return [], "", f"the creator's list is not read on {info.get('extractor_key') or 'this platform'}"
    log(f"the creator's usual: reading {src} (the newest {LIST_MAX}, no download) ...")
    try:
        raw = json.loads(C.run([C.ytdlp(), "--flat-playlist", "-J", "--playlist-end", str(LIST_MAX), "--no-warnings",
                                *extra, src], timeout=240))
    except SystemExit as e:
        return [], which, f"the creator's list could not be read: {str(e)[-200:]}"
    except (ValueError, subprocess.TimeoutExpired) as e:
        return [], which, f"the creator's list could not be read: {type(e).__name__}"
    out = []
    for e in raw.get("entries") or []:
        if not isinstance(e, dict) or not e.get("id"):
            continue
        ts = e.get("timestamp") or e.get("release_timestamp")
        if not ts and e.get("upload_date"):
            ts = S._date_ts(f"{e['upload_date'][:4]}-{e['upload_date'][4:6]}-{e['upload_date'][6:8]}")
        out.append({"id": e["id"], "views": e.get("view_count"), "ts": ts, "duration": e.get("duration"),
                    "title": e.get("title")})
    return out, which, "" if out else "the creator's list was empty"


def lookup(d: Path, ref: dict, url: str, v: dict, fresh_info: bool, log=print) -> dict:
    """The numbers the user's click asked for -> numbers.json: the video's (stats.json, from yt-dlp -J - fetched now
    unless the subtitles' request just did) and the creator's usual from their list."""
    if fresh_info:
        info = json.loads(C.run([C.ytdlp(), "-J", "--skip-download", "--no-playlist", "--no-warnings", url]))
        log(C.stats_line(C.save_stats(ref, info, url)))
        C.save_info(ref, info)
        C._thumb_note(ref, info, measure=False)
    info = S._load(d / "content" / "info.json") or {}
    st = S._load(d / "content" / "stats.json") or {}
    ents, which, why = creator_list(info, url, v, log)
    usual = None
    if ents:
        usual, why = S.usual_from(ents, st.get("id") or info.get("id"), st.get("upload_date"))
        if usual:
            usual["list"] = which
            if which != "user" and any(e.get("ts") for e in ents):
                usual["caveats"] = list(usual.get("caveats") or []) + ["YouTube's list rounds views (149K) and gives "
                                                                       "approximate upload months"]
            elif which == "shorts":
                usual["caveats"] = list(usual.get("caveats") or []) + ["YouTube's Shorts list rounds views and gives no "
                                                                       "dates - the videos around it are its era"]
            usual["rounded"] = which in ("videos", "shorts")
    num = {"schema": 1, "fetched": time.strftime("%Y-%m-%d %H:%M"), "url": url, "platform": st.get("platform"),
           "id": st.get("id"),
           "video": {k: st.get(k) for k in ("views", "likes", "comments", "shares", "saves", "followers", "upload_date",
                                            "days_online", "views_per_day", "duration_s")},
           "usual": usual, "usual_why": None if usual else why}
    write_json(d / "numbers.json", num)
    T = S.table(d)
    log(f"numbers: {S.num_str(T['views']['v'])} views · usual {S.num_str(T['usual_views']['v'])} · "
        f"{S.num_str(T['outlier']['v'], 'x')} its usual" + (f" ({why})" if not usual else ""))
    return num


# ------------------------------------------------------------------------------------------------ prepare
def _reuse_words(d: Path, sha: str, fps: float) -> str | None:
    """The same video's words from its notes or its analysis (the same file, the same frame rate): no second fetch or
    listening. -> where they came from."""
    from motionlab import notes as NT
    from motionlab.util import ANALYSIS
    cands = []
    for nd in sorted(NT.ROOT.iterdir()) if NT.ROOT.is_dir() else []:
        n = S._load(nd / "note.json") if nd.is_dir() else None
        if isinstance(n, dict) and n.get("sha256") == sha and abs(float(n.get("fps") or 0) - fps) < 0.01:
            cands.append(nd / "content")
    for ad in sorted(ANALYSIS.iterdir()) if ANALYSIS.is_dir() else []:
        ev = S._load(ad / "events.json") if (ad / "events.json").exists() else None
        if isinstance(ev, dict) and (ev.get("source") or {}).get("sha256") == sha \
                and abs(float((ev.get("video") or {}).get("fps") or 0) - fps) < 0.01:
            cands.append(ad / "content")
    for c in cands:
        if (c / "transcript.json").exists() and (c / "transcript.txt").exists():
            (d / "content").mkdir(parents=True, exist_ok=True)
            for f in ("transcript.json", "transcript.txt"):
                shutil.copy2(c / f, d / "content" / f)
            return str(c.parent)
    return None


def prepare(a) -> int:
    from motionlab.knowledge import download_info
    from motionlab.probe import probe
    video = Path(a.video).expanduser().resolve()
    if not video.is_file() or video.suffix.lower() not in VIDEO_EXT:
        raise SystemExit(f"not a video file: {video}")
    if LAB.resolve() in video.parents and video.parts[len(LAB.resolve().parts)] in ("analysis", ".app", "tools"):
        raise SystemExit("pick the original video, not a file the lab made")
    name = S.unique_name(video)
    d = S.ROOT / name
    d.mkdir(parents=True, exist_ok=True)
    guard = SourceGuard(video, d)
    old = S._load(d / "video.json") or {}
    print(f"SPARK: {video.name} -> {d}", flush=True)
    pi = probe(video)
    fps = _fps(pi["video"])
    n_est = int(pi["video"].get("nb_frames") or round(float(pi.get("duration_s") or 0) * fps))
    if n_est < 1:
        raise SystemExit("this video has no frames")
    sha = sha256_file(video)
    if old.get("sha256") and old["sha256"] != sha:
        print("NOTE: this file changed since SPARK read it (another version of the video?)")
    dl = download_info(video.name) or {}
    url = a.url or dl.get("url") or dl.get("link") or ""
    if not url and (m := C.YT_ID.search(video.stem)):
        url = f"https://www.youtube.com/watch?v={m.group(1)}"
    title = dl.get("title") or re.sub(r"\s*\[[A-Za-z0-9_-]{6,}\]$", "", video.stem)
    issues: list[str] = []
    # 1. the light read first: its frame count is the one every number below uses
    print("STEP 1/4: every frame", flush=True)      # the app's progress bar (jobs.STEP)
    with tempfile.TemporaryDirectory(dir=str(d), ignore_cleanup_errors=True) as tmp:
        met, hard, jump = light_read(video, pi, fps, Path(guard.check(Path(tmp))))
    n = len(met["frame"])
    W, H = pi["video"].get("display_width"), pi["video"].get("display_height")
    v = {**old, "schema": S.SCHEMA, "name": name, "video": str(video), "sha256": sha, "fps": fps, "frames": n,
         "duration_s": round(n / fps, 3), "drop_frame": False, "width": W, "height": H,
         "format": S.fmt_of(W, H, n / fps), "url": url or None, "platform": dl.get("platform") or old.get("platform"),
         "uploader": dl.get("uploader") or old.get("uploader"), "title": old.get("title") or title,
         "created": old.get("created") or time.strftime("%Y-%m-%d %H:%M"), "issues": []}
    if a.label:
        v["label"] = " ".join(a.label.split())[:120]
    if a.ask is not None:
        v["ask"] = " ".join(a.ask.split())[:1000]
    if a.tags is not None:
        v["tags"] = [t for t in dict.fromkeys(" ".join(x.split()).lower()[:40] for x in a.tags.split(",")) if t][:12]
    write_json(guard.check(d / "video.json"), v)
    ref = {"name": name, "dir": d, "fps": fps, "frames": n, "video": video, "drop": False}
    # 2. the words: kept / the same video's notes or analysis / the platform's subtitles / speech to text
    print("STEP 2/4: the words", flush=True)
    fetched = False
    if a.force or S.transcript(d) is None:
        src = None if a.force else _reuse_words(d, sha, fps)
        if src:
            print(f"words: taken from {src} (the same video)", flush=True)
        elif url and not a.no_lookup:
            try:
                C.fetch_subtitles(ref, url, measure=False)
            except SystemExit as e:
                issues.append(f"subtitles: {e}")
                print(f"subtitles: {e}", flush=True)
            except Exception as e:                              # noqa: BLE001 - a network hiccup, an odd caption file
                issues.append(f"subtitles: {type(e).__name__}: {e}")
                print(f"subtitles: {type(e).__name__}: {e}", flush=True)
            fetched = (d / "content" / "stats.json").exists()
    info = S._load(d / "content" / "info.json") or {}
    if S.transcript(d) is None:
        names = " ".join(x for x in [v.get("title"), v.get("uploader")] + [c.get("title") for c in info.get("chapters") or []]
                         if x)[:220]
        try:
            if C.speech_transcript(ref, print, names) is None:
                issues.append("no words: " + ("the platform has no subtitles for it" if url else "no link known")
                              + " and speech to text is not installed (Settings > Programs > Speech to text)")
        except Exception as e:                                  # noqa: BLE001
            issues.append(f"speech to text: {type(e).__name__}: {e}")
    tr0 = S.transcript(d)
    said, own = str((tr0 or {}).get("lang") or ""), str(info.get("language") or "")
    if tr0 and tr0.get("source") == "subtitles" and said and own and said.split("-")[0] != own.split("-")[0]:
        issues.append(f"the words are in '{said}' but the video says it is in '{own}' - a dubbed or translated track?")
    # 3. the numbers - the lookup the user started (the video's numbers and the creator's list)
    print("STEP 3/4: the numbers", flush=True)
    if url and not a.no_lookup:
        try:
            lookup(d, ref, url, v, fresh_info=not fetched)
        except SystemExit as e:
            issues.append(f"numbers: {e}")
            print(f"numbers: {e}", flush=True)
        except Exception as e:                                  # noqa: BLE001 - the numbers are optional
            issues.append(f"numbers: {type(e).__name__}: {e}")
            print(f"numbers: {type(e).__name__}: {e}", flush=True)
    elif not url:
        issues.append("numbers: no link known - the video's numbers and its creator's usual are unknown (add the link: "
                      "--url)")
    info = S._load(d / "content" / "info.json") or {}
    for p in sorted((d / "content").glob("thumbnail.*")) if (d / "content").is_dir() else []:
        if p.suffix.lower() in (".jpg", ".png", ".webp"):
            try:
                from motionlab import thumbnail as TH
                TH.measure_file(p, force=True)
            except Exception as e:                              # noqa: BLE001 - the picture is there; no measures
                print(f"thumbnail not measured: {type(e).__name__}: {e}")
            break
    v["title"] = info.get("title") or v["title"]
    v["uploader"] = info.get("uploader") or info.get("channel") or v.get("uploader")
    v["platform"] = v.get("platform") or info.get("extractor_key")
    v["chapters"] = S.chapters_of(info, fps, n)
    v["replayed"] = S.replayed_of(info, fps, n)
    # 4. the lab's numbers and the pictures
    print("STEP 4/4: measures and pictures", flush=True)
    mea, pieces, shots = measures(met, hard, jump, n, fps, S.transcript(d))
    flux = S.same_video(sha, str(video))["flux"]
    if flux:                                     # its analysis' text events (checked by Claude) beat the rough measure
        from motionlab.profile import profile
        ph = ((profile(flux) or {}).get("content") or {}).get("hook") or {}
        if "text_on_screen" in ph:
            mea["hook"].update(text=bool(ph["text_on_screen"]), text_source="flux")
    cp = S.creator_pacing(name, v.get("uploader"))
    if cp:
        mea["creator"] = cp
    write_json(guard.check(d / "measures.json"), mea)
    try:
        pictures(d, video, pi, fps, n, pieces, shots, guard)
    except Exception as e:                                      # noqa: BLE001 - the words and numbers still explain
        issues.append(f"pictures: {type(e).__name__}: {e}")
    v["issues"] = issues
    write_json(guard.check(d / "video.json"), v)
    if not guard.verify_unchanged():
        raise SystemExit(f"WARNING: the source video changed while SPARK read it: {video}")
    tr = S.transcript(d)
    pc = mea["pacing"]
    print(f"words: {tr['source']} ({tr.get('lang')}), {len(tr['lines'])} lines, {tr.get('words')} words" if tr
          else "words: none")
    print(f"shots: {pc['shots']} ({pc['cuts']} cuts, {pc['jump_cuts']} jump cuts) · {pc['cuts_per_min']} cuts/min · "
          f"first 3 s: {mea['hook']['cuts']} cuts, {mea['hook']['words']} words, text {mea['hook']['text']}")
    for x in issues:
        print(f"NOTE: {x}")
    print(f"source unchanged (SHA-256 {sha[:12]}...)")
    print(f"SPARK: {name}")
    return 0


def numbers(a) -> int:
    d, v = S.need(safe_name(a.name))
    if not v.get("url"):
        raise SystemExit("no link known for this video - prepare it again with --url <link>")
    ref = {"name": d.name, "dir": d, "fps": float(v["fps"]), "frames": int(v["frames"]),
           "video": Path(v.get("video") or ""), "drop": False}
    lookup(d, ref, v["url"], v, fresh_info=True)
    return 0


def save(a) -> int:
    p = Path(a.draft)
    try:
        draft = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SystemExit(f"cannot read {p}: {e}") from None
    try:
        rep = S.save_spark(safe_name(a.name), draft)
    except ValueError as e:
        print(e)
        return 1
    d = S.spark_dir(a.name)
    known = sum(1 for p in rep["rubric"] if p["label"] != "unknown")
    print(f"saved: {rep['result']} · {known} of {len(rep['rubric'])} points explained · {len(rep['takeaways'])} "
          f"take-aways -> {d / 'spark.json'}, {d / 'spark.md'}")
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
    p.add_argument("--no-lookup", action="store_true", help="no numbers and no subtitles from the platform")
    for c in ("show", "numbers"):
        sub.add_parser(c).add_argument("name")
    s = sub.add_parser("save")
    s.add_argument("name")
    s.add_argument("draft")
    for c in ("pending", "list", "selfcheck"):
        sub.add_parser(c)
    a = ap.parse_args()
    if a.cmd == "prepare":
        return prepare(a)
    if a.cmd == "numbers":
        return numbers(a)
    if a.cmd == "show":
        print(S.show_text(safe_name(a.name)))
        return 0
    if a.cmd == "save":
        return save(a)
    if a.cmd == "selfcheck":
        return S.selfcheck()
    if a.cmd == "pending":
        print("\n".join(S.pending()) or "none")
        return 0
    for x in S.list_spark():
        print(f"{x['name']}  [{x['status']}]  {x['label']}  {S.num_str(x['outlier'], 'x')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
