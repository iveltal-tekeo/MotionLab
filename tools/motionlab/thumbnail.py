"""Thumbnails (0.4.3): the 16:9 YouTube thumbnail and the 9:16 cover (Shorts / Reels / TikTok), made from the user's
own frames with HTML templates (tools\\overlays\\thumbnails\\<name>\\, rendered as stills by HyperFrames' snapshot - the
0.3.2 graphics pipeline, no render) and checked without Claude. CLI: tools\\thumbnail.py.

- candidates(): frames worth a thumbnail from a project's clips (build\\sources.json), its newest render or one video:
  sharp (Laplacian variance), still (little change to the next frames), well lit (exposure, little clipping), not a cut
  or a transition, spread over the footage; a big face when the face detector is available (FACE_MODEL below).
  Only the frames needed are decoded (ffmpeg seeks); a project's frame-cache stats (cache\\<ID>_stats.npz) pre-pick
  them when they exist. -> build\\publish\\candidates\\ + candidates.png (frame + timecode per tile).
- make(): a template + a frame (or an image) + 2-4 words -> thumb_<id>_16x9.png (1280x720), thumb_<id>_9x16.png
  (1080x1920), thumb_<id>_9x16_crops.png (the platforms' grid crops and buttons drawn on the cover) and the editable
  graphic thumbs\\<id>\\ (index.html + overlay.json "values", like any graphic: overlay.py settings / set work on it;
  render() makes the PNGs again). Every template renders three frames: f0 = the thumbnail, f1 = without the words,
  f2 = the words' fill in the key colour #ff00ff (no outline / shadow) - the check measures the text from them.
- check(): PASS / WARN / FAIL per rule, with its number (RULES says each rule's thresholds and why).
- refs(): the analysed references' own thumbnails (analysis\\<name>\\content\\thumbnail.*, saved by content.py)
  measured, summarised per niche with the outperformers (views / followers) weighted first; packaging_lines() = the
  short block in Claude's memory.
package.json (build\\publish\\): this module owns "candidates" and "thumbnails" only; other keys (title, titles,
description, chapters, hashtags) belong to the packaging tool. Every write re-reads the file and replaces it
atomically. Writes go only into build\\publish\\ (and analysis\\<name>\\content\\ for references); sources are read.
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .timecode import frame_to_tc
from .util import ANALYSIS, LAB, tool

TEMPLATES = LAB / "tools" / "overlays" / "thumbnails"
SIZES = {"16x9": (1280, 720), "9x16": (1080, 1920)}
FPS = 30                                                   # the templates' rate (3 frames: f0, f1, f2)
MODEL_NAME = "face_detection_yunet_2023mar.onnx"           # OpenCV's YuNet (opencv_zoo, MIT), 227 KB
FACE_MODELS = [LAB / "tools" / "models" / MODEL_NAME, LAB / ".app" / "models" / MODEL_NAME]
FACE_SCORE = 0.88          # measured 2026-10-15: every false face scored <= 0.82, every big face >= 0.89
THREADS = 4
KEY = (255, 0, 255)          # frame f2 paints the letters' fill in this colour (the check finds them by it)

# ------------------------------------------------------------------------------------------ the platforms (checked)
PLATFORMS = {
    "checked": "2026-10-15",
    "youtube": "YouTube thumbnail: 16:9, JPG / PNG, minimum width 640 px; YouTube's help now recommends 3840x2160 "
               "(2160x3840 for Shorts); 1280x720 is the long-standing size and still accepted. File limit 2 MB when "
               "uploaded from the phone app, 50 MB from a computer (YouTube Studio). Shorts covers: 9:16, set in "
               "YouTube Studio on a computer; a 16:9 thumbnail on a vertical video is replaced by an automatic 4:5 one. "
               "Test & compare: up to 3 titles / thumbnails, computer only, not for Shorts; the winner = most watch "
               "time (support.google.com/youtube/answer/72431, /13861714).",
    "cover": "Shorts / Reels / TikTok cover: 1080x1920 (9:16).",
    "instagram": "Instagram profile grid: 3:4 tiles since January 2025 (was 1:1) - a 9:16 cover shows its middle "
                 "1080x1440; the home feed shows Reels up to 4:5 (1080x1350). Size guides, not Instagram's own page.",
    "tiktok": "TikTok profile grid: about 3:4 of the 9:16 cover (top and bottom trimmed), the view count over the "
              "bottom-left corner. Size guides only - check a live profile.",
    "title": "YouTube titles: 100 characters at most; a phone's home feed shows about 45-50 before '...' (third-party "
             "measurements; YouTube publishes no number - it depends on the screen and the letters).",
}
# drawn on the 9:16 cover (x, y, w, h in 1080x1920 pixels)
CROPS = [("Instagram + TikTok profile grid 3:4", (0, 240, 1080, 1440), (255, 196, 0)),
         ("Instagram feed 4:5", (0, 285, 1080, 1350), (80, 200, 255)),
         ("old square grid 1:1", (0, 420, 1080, 1080), (255, 90, 90))]
# where the apps draw over the picture while it plays / in the grid (text there gets covered or cropped)
UNSAFE = {"9x16": [("outside the 3:4 grid crop (top)", (0, 0, 1080, 240)),
                   ("outside the 3:4 grid crop (bottom) + caption / username", (0, 1500, 1080, 420)),
                   ("like / comment / share buttons", (930, 960, 150, 540))],
          "16x9": [("YouTube's length badge", (1075, 620, 205, 100))]}
# feed views: (name, width in px on the screen, PASS from, WARN from) - the letters' height there
VIEWS = {"16x9": [("phone feed", 360, 20, 12), ("sidebar", 168, 10, 7)],
         "9x16": [("Shorts shelf", 180, 14, 9), ("profile grid", 120, 10, 7)]}
RULES = {
    "readability": "the letters' height on the screen at feed size (px): 16:9 phone feed (360 px wide) PASS >= 20, "
                   "WARN >= 12; sidebar (168 px) PASS >= 10, WARN >= 7; 9:16 Shorts shelf (180 px) 14 / 9, profile grid "
                   "(120 px) 10 / 7",
    "words": "2-4 words PASS; 1 or 5-6 WARN; none or 7+ FAIL",
    "text_size": "the text block's height in % of the frame: PASS >= 20, WARN >= 12, else FAIL",
    "contrast": "WCAG contrast of the letters against what touches them (outline or picture), the value 80 % of the "
                "letters' edge reaches: PASS >= 4.5 (AAA for large text), WARN >= 3 (AA), else FAIL",
    "subject": "the biggest face's height in % of the frame: 16:9 PASS >= 25, WARN >= 12; 9:16 PASS >= 15, WARN >= 8; "
               "smaller FAIL; no face WARN; no detector SKIP",
    "look": "brightness (L*) and saturation within 12 of the niche's outperforming references: PASS, else WARN; SKIP "
            "without references",
    "safe_zone": "share of the text where the apps draw (grid crop, buttons, length badge): PASS <= 2 %, WARN <= 15 %, "
                 "else FAIL",
    "file_size": "PASS <= 2 MB (YouTube's phone upload), WARN <= 50 MB (computer upload), else FAIL",
    "title_length": "PASS <= 50 characters (shown whole on a phone), WARN <= 70, else FAIL (cut everywhere but the "
                    "watch page; 100 = YouTube's limit)",
    "title_repeat": "share of the thumbnail's words already in the title: PASS <= 34 %, WARN <= 67 %, else FAIL",
    "promise": "share of the title's key words said in the script's first 3 s: PASS >= 40 %, WARN > 0, FAIL = none",
}
STOP = set("""a an the and or but of to in on at for with by from as is are was were be been it its this that these those
i me my we our you your he she they them his her their what which who how why when where so if not no do does did
just very really all any some more most than then there here up down out over about into vs vs. am pm
el la los las un una unos unas y o de del al en con por para que es son fue era lo le les se mi mis tu tus su sus
yo tú nos como cuando donde muy más pero sin sobre este esta estos estas eso esa ese""".split())
_WORD = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.U)


def _words(s: str) -> list[str]:
    return _WORD.findall(s or "")


def _key(w: str) -> str:
    """A crude stem for comparing words (lower case, no accents' plural s, first 6 letters)."""
    w = w.lower()
    if len(w) > 3 and w.endswith("s"):
        w = w[:-1]
    return w[:6]


def keywords(s: str) -> list[str]:
    return [w for w in _words(s) if w.lower() not in STOP]


def tc(frame: int, fps: float) -> str:
    return f"f{frame} ({frame_to_tc(frame, fps)})"


# ------------------------------------------------------------------------------------------ the face detector
_DET: dict = {}
_DET_LOCK = __import__("threading").Lock()       # one detector, one picture at a time


def face_model() -> Path | None:
    env = os.environ.get("MOTIONLAB_FACE_MODEL")
    for p in ([Path(env)] if env else []) + FACE_MODELS:
        if p.is_file():
            return p
    return None


def faces(rgb: np.ndarray, min_score: float = FACE_SCORE) -> list[list[float]] | None:
    """Faces in an RGB picture: [x, y, w, h, score] in its pixels, biggest first; None when there is no detector
    (OpenCV 5 dropped the Haar cascades; YuNet needs FACE_MODEL's 227 KB file). Run at <= 640 px wide."""
    m = face_model()
    if not m:
        return None
    import cv2
    h, w = rgb.shape[:2]
    s = min(1.0, 640 / max(w, h))
    small = cv2.resize(rgb, (max(1, round(w * s)), max(1, round(h * s))), interpolation=cv2.INTER_AREA) if s < 1 else rgb
    with _DET_LOCK:
        det = _DET.get(str(m))
        if det is None:
            cv2.setNumThreads(THREADS)
            det = _DET[str(m)] = cv2.FaceDetectorYN.create(str(m), "", (320, 320), 0.6, 0.3, 5000)
        det.setInputSize((small.shape[1], small.shape[0]))
        _, out = det.detect(np.ascontiguousarray(small[..., ::-1]))
    res = []
    for f in ([] if out is None else out):
        if float(f[-1]) >= min_score:
            res.append([float(f[0]) / s, float(f[1]) / s, float(f[2]) / s, float(f[3]) / s, round(float(f[-1]), 3)])
    return sorted(res, key=lambda b: -b[2] * b[3])


# ------------------------------------------------------------------------------------------ videos and frames
_PROBES: dict = {}


def vinfo(path: Path) -> dict:
    """fps (nominal-ish, from the stream), frames, display size of a video (cached)."""
    key = str(Path(path).resolve())
    if key not in _PROBES:
        from .probe import probe, snap_rate
        info = probe(Path(path))
        v = info["video"]
        fps = snap_rate(v["r_fps"] or v["avg_fps"] or 25.0)
        n = v["nb_frames"] or int(round((info.get("duration_s") or 0) * fps))
        _PROBES[key] = {"fps": float(fps), "frames": int(n), "width": int(v["display_width"]),
                        "height": int(v["display_height"])}
    return _PROBES[key]


def grab(path: Path, frame: int, long_side: int | None = 1280, count: int = 1, threads: int = 1) -> list[np.ndarray]:
    """count frames from frame on (0-based, at the clip's own rate), RGB, scaled so the long side <= long_side.
    ffmpeg seeks (decodes from the keyframe before it); the file is only read."""
    v = vinfo(path)
    w, h = v["width"], v["height"]
    s = min(1.0, (long_side or max(w, h)) / max(w, h))
    ow, oh = max(2, int(round(w * s / 2)) * 2), max(2, int(round(h * s / 2)) * 2)
    t = max(0.0, (frame - 0.25) / v["fps"])
    r = subprocess.run([tool("ffmpeg"), "-v", "error", "-threads", str(threads), "-ss", f"{t:.4f}", "-i", str(path),
                        "-frames:v", str(count), "-vf", f"scale={ow}:{oh}:flags=area", "-f", "rawvideo",
                        "-pix_fmt", "rgb24", "-"], capture_output=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    size = ow * oh * 3
    n = len(r.stdout) // size
    if r.returncode or not n:
        raise RuntimeError(f"ffmpeg could not read frame {frame} of {Path(path).name}: {r.stderr.decode(errors='replace')[-300:]}")
    return [np.frombuffer(r.stdout[i * size:(i + 1) * size], np.uint8).reshape(oh, ow, 3) for i in range(n)]


def project_of(target: str) -> tuple[object, list[dict]]:
    """A project name / folder or a video file -> (Project, the videos to look at). A project = its clips (sources.json
    ids, else A, B, ... in name order, not written); a video file = that file (in a project's top level or build\\)."""
    from .project import PROJECTS, Project, _next_id
    p = Path(target)
    if p.suffix and p.is_file():
        f = p.resolve()
        top = f.parent if f.parent.parent == PROJECTS.resolve() else None
        if top is None and f.parent.name == "build" and f.parent.parent.parent == PROJECTS.resolve():
            top = f.parent.parent
        if top is None:
            raise SystemExit(f"{f} is not in a project: thumbnails go to projects\\<name>\\build\\publish\\ - put the "
                             "video in a project folder (the app's Edit > New) or pass the project")
        prj = Project(top)
        return prj, [s for s in sources(prj) if Path(s["path"]).resolve() == f] or [
            {"id": f.name, "file": f.name, "path": str(f), "kind": "render" if top != f.parent else "clip"}]
    prj = Project(target)
    return prj, sources(prj)


def sources(prj) -> list[dict]:
    from .project import _next_id
    man = prj.manifest().get("sources") or {}
    out, have = [], {}
    for k, e in man.items():
        if Path(e["path"]).exists():
            out.append({"id": k, "file": e["name"], "path": e["path"], "kind": "clip", "fingerprint": e.get("fingerprint")})
            have[str(Path(e["path"]).resolve())] = k
    ids = {k: 1 for k in man}
    for f in prj.footage_files():
        if str(f.resolve()) not in have:
            k = _next_id(ids)
            ids[k] = 1
            out.append({"id": k, "file": f.name, "path": str(f), "kind": "clip"})
    return sorted(out, key=lambda s: (len(s["id"]), s["id"]))


def newest_render(prj) -> dict | None:
    rs = sorted((f for f in prj.build.glob("*.mp4") if re.search(r"_v\d+\.mp4$", f.name)), key=lambda f: f.stat().st_mtime)
    return {"id": rs[-1].name, "file": rs[-1].name, "path": str(rs[-1]), "kind": "render"} if rs else None


def find_source(prj, clip: str | None) -> dict:
    """--clip: a source id (A, B ...), a file name in the project or its build folder, or 'render' (the newest)."""
    srcs = sources(prj)
    if clip in (None, ""):
        if len(srcs) == 1:
            return srcs[0]
        r = newest_render(prj)
        if not srcs and r:
            return r
        raise SystemExit(f"which clip? --clip one of {', '.join(s['id'] for s in srcs)} or render")
    if clip == "render":
        r = newest_render(prj)
        if not r:
            raise SystemExit("no render in the project's build folder yet")
        return r
    for s in srcs:
        if clip in (s["id"], s["file"]):
            return s
    for d in (prj.build, prj.dir):
        f = d / clip
        if f.is_file() and f.suffix.lower() in (".mp4", ".mov", ".mkv", ".m4v"):
            return {"id": f.name, "file": f.name, "path": str(f), "kind": "render" if d == prj.build else "clip"}
    raise SystemExit(f"no clip '{clip}' (ids: {', '.join(s['id'] for s in srcs)}, or render, or a file name)")


# ------------------------------------------------------------------------------------------ package.json
def publish_dir(prj) -> Path:
    d = prj.build / "publish"
    prj.check(d)
    return d


def read_package(prj) -> dict:
    p = publish_dir(prj) / "package.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except (OSError, ValueError):
        return {}


def update_package(prj, **keys) -> Path:
    """Re-read package.json, set only these keys (candidates / thumbnails), write a temp file and rename it."""
    d = publish_dir(prj)
    d.mkdir(parents=True, exist_ok=True)
    p = d / "package.json"
    for attempt in range(5):
        data = read_package(prj)
        data.update(keys)
        tmp = d / f".package.{os.getpid()}.{attempt}.tmp"
        tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
        try:
            os.replace(tmp, p)
            return p
        except PermissionError:                     # Windows: someone is reading it right now
            tmp.unlink(missing_ok=True)
            time.sleep(0.2)
    raise SystemExit(f"could not write {p} (open in another program?)")


def rel(p: Path) -> str:
    try:
        return Path(p).resolve().relative_to(LAB.resolve()).as_posix()
    except ValueError:
        return str(p)


# ------------------------------------------------------------------------------------------ measures of a frame
def grey(rgb: np.ndarray) -> np.ndarray:
    return (rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114).astype(np.float32)


def sharpness(g: np.ndarray) -> float:
    import cv2
    return float(cv2.Laplacian(g, cv2.CV_32F).var())


def frame_measures(frames: list[np.ndarray]) -> dict:
    """frames = 3 consecutive RGB frames (the candidate is the middle one) at ~640 px: sharpness, motion (mean change to
    the neighbours, 0-255), exposure (mean, clipped share), a cut / flash between them."""
    gs = [grey(f) for f in frames]
    mid = gs[len(gs) // 2]
    diffs = [float(np.abs(gs[i + 1] - gs[i]).mean()) for i in range(len(gs) - 1)]
    return {"sharp": round(sharpness(mid), 1), "motion": round(float(np.mean(diffs)) if diffs else 0.0, 2),
            "cut": bool(diffs and max(diffs) > 35), "luma": round(float(mid.mean()) / 2.55, 1),
            "clipped": round(float(((mid < 4) | (mid > 251)).mean()), 3)}


def exposure_score(luma: float, clipped: float) -> float:
    """1 = mid-bright and nothing clipped; dark / blown frames fall."""
    s = 1.0 - min(1.0, abs(luma - 52) / 45)
    return max(0.0, s - max(0.0, clipped - 0.05) * 3)


# ------------------------------------------------------------------------------------------ candidates
def _stats_for(prj, src: dict) -> dict | None:
    """The frame cache's per-frame stats of a clip (prep_footage), if they belong to this very file."""
    j, z = prj.cache / f"{src['id']}.json", prj.cache / f"{src['id']}_stats.npz"
    if src["kind"] != "clip" or not (j.exists() and z.exists()):
        return None
    try:
        meta = json.loads(j.read_text(encoding="utf-8"))
        if meta.get("fingerprint") and src.get("fingerprint") and meta["fingerprint"] != src["fingerprint"]:
            return None
        st = np.load(z)
        return {"step": int(meta.get("step") or 1), **{k: st[k] for k in st.files}}
    except (OSError, ValueError):
        return None


def _sample_points(prj, srcs: list[dict], n: int) -> list[tuple[dict, int, dict | None]]:
    """(source, frame, measures from the cache stats or None) to decode: from the stats the best ~3n moments, else an
    even spread (~4n samples over the footage, at least 2 per clip)."""
    infos = [(s, vinfo(Path(s["path"]))) for s in srcs]
    total = sum(v["frames"] / v["fps"] for _, v in infos) or 1.0
    budget = int(min(96, max(24, 4 * n)))
    pts = []
    for s, v in infos:
        dur = v["frames"] / v["fps"]
        k = max(2, int(round(budget * dur / total)))
        st = _stats_for(prj, s)
        if st is not None and len(st.get("sharp", [])) > 4:
            sh, mo, lu = st["sharp"], st["motion"], st["luma"]
            p05, p95 = st.get("p05", lu * 0), st.get("p95", lu * 0 + 50)
            rank = lambda a: np.argsort(np.argsort(a)) / max(1, len(a) - 1)     # noqa: E731
            still = 1 - np.clip(mo / max(1e-6, np.percentile(mo, 90) * 1.5), 0, 1)
            expo = np.array([exposure_score(float(l), 0.12 if (a < 0.5 or b > 99.5) else 0.0)
                             for l, a, b in zip(lu, p05, p95)])
            sc = 0.4 * rank(sh) + 0.35 * still + 0.25 * expo
            sc[:2] = sc[-2:] = -1                                             # first / last frames: cuts
            gap = max(2, len(sc) // (k * 2))
            order = np.argsort(-sc)
            chosen = []
            for i in order:
                if len(chosen) >= k:
                    break
                if all(abs(int(i) - c) >= gap for c in chosen):
                    chosen.append(int(i))
            for i in chosen:
                f = min(v["frames"] - 2, max(1, i * st["step"]))
                pts.append((s, f, {"stats": True}))
        else:
            for j in range(k):
                f = int((j + 0.5) / k * v["frames"])
                pts.append((s, min(max(1, f), max(1, v["frames"] - 2)), None))
    return pts


def candidates(target: str, n: int = 12, use_render: bool = False, threads: int = THREADS, log=print) -> dict:
    """Pick n frames worth a thumbnail -> build\\publish\\candidates\\c01_<src>_f<frame>.png (long side 1280),
    candidates.png (the sheet) and package.json "candidates". Returns the package entry + timings."""
    t0 = time.time()
    prj, srcs = project_of(target)
    if use_render:
        r = newest_render(prj)
        if not r:
            raise SystemExit("no render in the project's build folder yet (drop --render to use the clips)")
        srcs = [r]
    if not srcs:
        r = newest_render(prj)
        srcs = [r] if r else []
    if not srcs:
        raise SystemExit(f"{prj.name}: no video in the project folder")
    pts = _sample_points(prj, srcs, n)
    log(f"{prj.name}: {len(pts)} moments to look at in {len(srcs)} video(s) ({threads} at a time)")

    def one(p):
        s, f, pre = p
        try:
            fr = grab(Path(s["path"]), f - 1, 640, 3)
        except RuntimeError:
            return None
        m = frame_measures(fr if len(fr) == 3 else fr[:1])
        fc = faces(fr[len(fr) // 2])
        h = fr[0].shape[0]
        m["face"] = None if fc is None else round(fc[0][3] / h, 3) if fc else 0.0
        return {"src": s, "frame": f, "m": m}
    with ThreadPoolExecutor(max(1, threads)) as ex:
        got = [g for g in ex.map(one, pts) if g]
    t1 = time.time()
    if not got:
        raise SystemExit("could not read any frame")
    sh = np.array([g["m"]["sharp"] for g in got], float)
    rank = np.argsort(np.argsort(sh)) / max(1, len(sh) - 1)
    for g, r in zip(got, rank):
        m = g["m"]
        still = 1 - min(1.0, m["motion"] / 12)
        parts = [(0.3, float(r)), (0.25, still), (0.2, exposure_score(m["luma"], m["clipped"]))]
        if m["face"] is not None:                     # a big face: what a thumbnail is usually built on
            parts.append((0.3, min(1.0, m["face"] / 0.3)))
        g["score"] = round(sum(w * v for w, v in parts) / sum(w for w, _ in parts), 3) if not m["cut"] else -1
    # spread: a minimum gap within a clip, at most ceil(n / clips) per clip on the first pass
    per = math.ceil(n / len(srcs))
    picks, count = [], {}
    for g in sorted(got, key=lambda x: -x["score"]):
        if len(picks) >= n or g["score"] < 0:
            break
        v = vinfo(Path(g["src"]["path"]))
        gap = max(v["fps"], v["frames"] / (n * 1.5))
        if count.get(g["src"]["id"], 0) >= per:
            continue
        if any(p["src"]["id"] == g["src"]["id"] and abs(p["frame"] - g["frame"]) < gap for p in picks):
            continue
        picks.append(g)
        count[g["src"]["id"]] = count.get(g["src"]["id"], 0) + 1
    for g in sorted(got, key=lambda x: -x["score"]):              # fill up if the spread left too few
        if len(picks) >= n:
            break
        if g not in picks and g["score"] >= 0:
            picks.append(g)
    picks.sort(key=lambda g: (srcs.index(g["src"]) if g["src"] in srcs else 0, g["frame"]))
    out = publish_dir(prj) / "candidates"
    prj.check(out)
    if out.exists():
        for old in out.glob("c*_*.png"):
            old.unlink()
    out.mkdir(parents=True, exist_ok=True)

    def full(i_g):
        i, g = i_g
        img = grab(Path(g["src"]["path"]), g["frame"], 1280, 1, threads=1)[0]
        v = vinfo(Path(g["src"]["path"]))
        cid = f"c{i + 1:02d}"
        safe = re.sub(r"[^\w.-]", "_", g["src"]["id"])
        p = out / f"{cid}_{safe}_f{g['frame']:05d}.png"
        Image.fromarray(img).save(prj.check(p), compress_level=6)
        return {"id": cid, "clip": g["src"]["id"], "file": g["src"]["file"], "kind": g["src"]["kind"],
                "frame": g["frame"], "tc": frame_to_tc(g["frame"], v["fps"]), "fps": v["fps"], "png": rel(p),
                "score": g["score"], "sharp": g["m"]["sharp"], "motion": g["m"]["motion"], "luma": g["m"]["luma"],
                "clipped": g["m"]["clipped"], "face": g["m"]["face"]}, img
    with ThreadPoolExecutor(max(1, threads)) as ex:
        res = list(ex.map(full, enumerate(picks)))
    t2 = time.time()
    items = [r[0] for r in res]
    tiles = []
    for it, img in res:
        face = "" if it["face"] is None else f"  face {round(it['face'] * 100)}%"
        tiles.append((f"{it['id']} {it['clip'][:14]} f{it['frame']} ({it['tc']})",
                      f"score {it['score']:.2f}  sharp {it['sharp']:.0f}  motion {it['motion']:.1f}  light {it['luma']:.0f}%{face}",
                      Image.fromarray(img)))
    sheet_path = publish_dir(prj) / "candidates.png"
    sheet(tiles, prj.check(sheet_path))
    entry = {"made": time.strftime("%Y-%m-%d %H:%M"), "from": "render" if use_render else "clips",
             "sheet": rel(sheet_path), "face_detector": face_model() is not None, "items": items}
    update_package(prj, candidates=entry)
    entry["seconds"] = {"look": round(t1 - t0, 1), "save": round(t2 - t1, 1), "total": round(time.time() - t0, 1),
                        "decoded": len(pts) * 3 + len(picks)}
    return entry


def _label(d: ImageDraw.ImageDraw, xy, text: str, font, fg=(255, 196, 0)) -> None:
    x0, y0, x1, y1 = d.textbbox(xy, text, font=font)
    d.rectangle((x0 - 5, y0 - 3, x1 + 5, y1 + 3), fill=(0, 0, 0))
    d.text(xy, text, fill=fg, font=font)


def sheet(tiles: list[tuple[str, str, Image.Image]], path: Path, cols: int = 4, tw: int = 420, th: int = 316) -> None:
    """A contact sheet: every tile fitted into tw x th (letterboxed), two label lines (frame + timecode first)."""
    from .media import fonts
    F = fonts(1.0)
    rows = (len(tiles) + cols - 1) // cols
    page = Image.new("RGB", (cols * (tw + 8) + 8, rows * (th + 8) + 8), (16, 16, 16))
    for i, (a, b, im) in enumerate(tiles):
        t = im.copy()
        t.thumbnail((tw, th), Image.LANCZOS)
        cell = Image.new("RGB", (tw, th), (30, 30, 30))
        cell.paste(t, ((tw - t.width) // 2, (th - t.height) // 2))
        d = ImageDraw.Draw(cell)
        _label(d, (8, 6), a, F["mono_b"])
        _label(d, (8, th - 22), b, F["small"], (230, 230, 230))
        page.paste(cell, (8 + (i % cols) * (tw + 8), 8 + (i // cols) * (th + 8)))
    page.save(path)


# ------------------------------------------------------------------------------------------ templates
def _overlay():
    """tools\\overlay.py (HyperFrames, the pinned GSAP, retime + snapshots) - reused, not forked."""
    t = str(LAB / "tools")
    if t not in sys.path:
        sys.path.insert(0, t)
    import overlay
    return overlay


def templates() -> list[dict]:
    from . import overlay_settings as OS
    out = []
    for d in sorted(TEMPLATES.iterdir()) if TEMPLATES.is_dir() else []:
        if (d / "index.html").exists():
            html = (d / "index.html").read_text(encoding="utf-8")
            m = re.search(r'thumbnail template "[^"]+" \([^)]*\): (.*?)\n\s*Size-independent', html, re.S)
            out.append({"name": d.name, "what": " ".join(m[1].split()) if m else "", "settings": OS.declared(d)})
    return out


def _photo_js(folder: Path, photos: list[dict]) -> None:
    js = "".join(f"window.{'PHOTO' if i == 0 else 'PHOTO2'} = {json.dumps(p, ensure_ascii=True)};\n"
                 for i, p in enumerate(photos))
    (folder / "assets" / "photo.js").write_text(js, encoding="utf-8")


def _save_photo(img: np.ndarray, dest: Path) -> dict:
    """A frame / an image -> assets\\<name>.jpg (long side <= 2400) + its face box (fractions)."""
    im = Image.fromarray(img)
    im.thumbnail((2400, 2400), Image.LANCZOS)
    im.save(dest, quality=92)
    fc = faces(np.asarray(im))
    face = None
    if fc:
        x, y, w, h, _ = fc[0]
        face = [round(x / im.width, 4), round(y / im.height, 4), round(w / im.width, 4), round(h / im.height, 4)]
    return {"src": f"assets/{dest.name}", "w": im.width, "h": im.height, "face": face}


def _read_photo(prj, frame: int | None, clip: str | None, image: str | None) -> tuple[np.ndarray, dict]:
    if image:
        p = Path(image)
        if not p.is_file():
            raise SystemExit(f"no image {p}")
        return np.asarray(Image.open(p).convert("RGB")), {"image": str(p.resolve())}
    s = find_source(prj, clip)
    v = vinfo(Path(s["path"]))
    if frame is None or not 0 <= frame < v["frames"]:
        raise SystemExit(f"--frame between 0 and {v['frames'] - 1} for {s['file']} ({v['fps']:g} fps)")
    img = grab(Path(s["path"]), frame, None, 1, threads=THREADS)[0]
    return img, {"clip": s["id"], "file": s["file"], "kind": s["kind"], "frame": frame,
                 "tc": frame_to_tc(frame, v["fps"]), "fps": v["fps"]}


def make(project: str, tid: str, words: str, template: str = "outline", frame: int | None = None,
         clip: str | None = None, image: str | None = None, frame2: int | None = None, clip2: str | None = None,
         image2: str | None = None, values: dict | None = None, log=print) -> dict:
    """A thumbnail: thumbs\\<id>\\ (the editable graphic) + both PNGs + the crops preview + package.json."""
    from .project import Project
    from . import overlay_settings as OS
    OVT = _overlay()
    t0 = time.time()
    if not re.fullmatch(r"[A-Z]", tid or ""):
        raise SystemExit("--id is one capital letter: A, B or C")
    prj = Project(project)
    src = TEMPLATES / template
    if not (src / "index.html").exists():
        raise SystemExit(f"no template '{template}' (thumbnail.py templates: "
                         f"{', '.join(t['name'] for t in templates())})")
    folder = publish_dir(prj) / "thumbs" / tid
    new = folder.parent / f".new_{tid}"                         # built aside: a bad frame or setting keeps the old one
    prj.check(new)
    shutil.rmtree(new, ignore_errors=True)
    (new / "assets").mkdir(parents=True)
    try:
        shutil.copy2(src / "index.html", new / "index.html")
        shutil.copy2(OVT.GSAP, new / "gsap.min.js")
        (new / "hyperframes.json").write_text(json.dumps({"paths": {"assets": "assets"}}, indent=1), encoding="utf-8")
        img, origin = _read_photo(prj, frame, clip, image)
        photos = [_save_photo(img, new / "assets" / "photo.jpg")]
        origins = [origin]
        if frame2 is not None or image2:
            img2, o2 = _read_photo(prj, frame2, clip2 or clip, image2)
            photos.append(_save_photo(img2, new / "assets" / "photo2.jpg"))
            origins.append(o2)
        _photo_js(new, photos)
        W, H = SIZES["16x9"]
        conf = {"name": f"thumb_{tid}", "kind": "thumbnail", "template": template, "frames": 3, "fps": FPS,
                "width": W, "height": H, "photos": origins, "values": {}}
        (new / "overlay.json").write_text(json.dumps(conf, indent=1, ensure_ascii=False), encoding="utf-8")
        try:
            OS.set_values(new, {"words": words, **(values or {})})
        except ValueError as e:
            raise SystemExit(f"settings: {e} (thumbnail.py templates lists them)")
    except BaseException:
        shutil.rmtree(new, ignore_errors=True)
        raise
    shutil.rmtree(folder, ignore_errors=True)
    os.replace(new, folder)
    t1 = time.time()
    entry = render(prj, tid, log=log)
    entry["seconds"] = {"photo": round(t1 - t0, 1), **entry.get("seconds", {}), "total": round(time.time() - t0, 1)}
    return entry


def render(prj, tid: str, log=print) -> dict:
    """thumbs\\<id>\\ (with its overlay.json values) -> thumb_<id>_16x9.png, _9x16.png, _9x16_crops.png + the check's
    frames (thumbs\\<id>\\check_<size>_nowords.png / _fill.png); package.json "thumbnails" updated."""
    from .project import Project
    from . import overlay_settings as OS
    OVT = _overlay()
    if isinstance(prj, (str, Path)):
        prj = Project(prj)
    pub = publish_dir(prj)
    folder = pub / "thumbs" / tid
    if not (folder / "overlay.json").exists():
        raise SystemExit(f"no thumbnail {tid} yet: thumbnail.py make {prj.name} --id {tid} ...")
    conf = json.loads((folder / "overlay.json").read_text(encoding="utf-8"))
    files, secs = {}, {}
    for size, (W, H) in SIZES.items():
        t0 = time.time()
        work = pub / "thumbs" / f".work_{tid}_{size}"
        prj.check(work)
        shutil.rmtree(work, ignore_errors=True)
        comp = work / "src"
        comp.mkdir(parents=True)
        for f in OS.SOURCES:
            if (folder / f).exists():
                shutil.copy2(folder / f, comp / f)
        shutil.copytree(folder / "assets", comp / "assets")
        OVT.retime(comp, FPS, 3, W, H)
        c = json.loads((comp / "overlay.json").read_text(encoding="utf-8"))
        c.update(width=W, height=H, frames=3, fps=FPS)
        (comp / "overlay.json").write_text(json.dumps(c, indent=1, ensure_ascii=False), encoding="utf-8")
        try:
            arrs, _ = OVT.snapshots(comp, [0, 1, 2], work / "snap")
        finally:
            shutil.rmtree(work, ignore_errors=True)
        rgb = [a[..., :3] for a in arrs]
        out = pub / f"thumb_{tid}_{size}.png"
        Image.fromarray(rgb[0]).save(prj.check(out), optimize=True)
        Image.fromarray(rgb[1]).save(folder / f"check_{size}_nowords.png", compress_level=6)
        Image.fromarray(rgb[2]).save(folder / f"check_{size}_fill.png", compress_level=6)
        files[size] = rel(out)
        if size == "9x16":
            cp = pub / f"thumb_{tid}_9x16_crops.png"
            crops_preview(rgb[0], prj.check(cp))
            files["9x16_crops"] = rel(cp)
        secs[size] = round(time.time() - t0, 1)
    files["folder"] = rel(folder)
    vals = OS.values(folder)
    shown = " ".join(str(vals.get(k) or "").strip() for k in ("label_a", "words", "label_b") if str(vals.get(k) or "").strip())
    entry = {"id": tid, "template": conf.get("template"), "words": shown, "photos": conf.get("photos"),
             "values": conf.get("values") or {}, "files": files, "made": time.strftime("%Y-%m-%d %H:%M")}
    pk = read_package(prj)
    old = {t.get("id"): t for t in pk.get("thumbnails") or []}
    if tid in old and old[tid].get("check"):
        entry["check"] = {"stale": True, **{k: v for k, v in old[tid]["check"].items() if k == "date"}}
    old[tid] = entry
    update_package(prj, thumbnails=[old[k] for k in sorted(old)])
    entry["seconds"] = {"render_" + k: v for k, v in secs.items()}
    return entry


def crops_preview(cover: np.ndarray, path: Path) -> None:
    """The 9:16 cover with the platforms' crops (boxes) and the apps' buttons (shaded), and next to it each crop as
    the grid shows it."""
    from .media import fonts
    F = fonts(2.0)
    H, W = cover.shape[:2]
    base = Image.fromarray(cover).convert("RGBA")
    shade = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ds = ImageDraw.Draw(shade)
    for name, (x, y, w, h) in UNSAFE["9x16"]:
        ds.rectangle((x, y, x + w - 1, y + h - 1), fill=(255, 0, 0, 70))
    im = Image.alpha_composite(base, shade).convert("RGB")
    d = ImageDraw.Draw(im)
    for i, (name, (x, y, w, h), col) in enumerate(CROPS):
        d.rectangle((x + 3 + 8 * i, y, x + w - 4 - 8 * i, y + h - 1), outline=col, width=6)
    tiles = []
    for name, (x, y, w, h), col in CROPS:
        t = Image.fromarray(cover[y:y + h, x:x + w])
        t = t.resize((round(w * 640 / h), 640), Image.LANCZOS)
        tiles.append((name, t, col))
    sc = 1280 / H
    left = im.resize((round(W * sc), 1280), Image.LANCZOS)
    tw = sum(t.width for _, t, _ in tiles) + 16 * (len(tiles) - 1)
    page = Image.new("RGB", (left.width + 32 + max(tw, 600) + 16, 1280 + 16), (16, 16, 16))
    page.paste(left, (8, 8))
    x = left.width + 32
    F1 = fonts(1.3)
    dd = ImageDraw.Draw(page)
    dd.text((x, 16), "How the grids show it (" + PLATFORMS["checked"] + ")", fill=(230, 230, 230), font=F1["title"])
    x0 = x
    for name, t, col in tiles:
        page.paste(t, (x, 80))
        dd.rectangle((x, 80, x + t.width - 1, 80 + t.height - 1), outline=col, width=3)
        dd.text((x, 80 + t.height + 10), name, fill=col, font=F1["mono_b"])
        x += t.width + 16
    y = 80 + 640 + 60
    dd.text((x0, y), "On the cover (left): each box = the part that crop shows (same colours);", fill=(230, 230, 230),
            font=F1["body"])
    dd.text((x0, y + 30), "red = covered while it plays (caption, username, like / comment / share buttons) or cut "
            "off in the 3:4 grid.", fill=(255, 160, 160), font=F1["body"])
    dd.text((x0, y + 60), "Keep the words and the face inside the yellow box and out of the red.", fill=(230, 230, 230),
            font=F1["body"])
    page.save(path)


# ------------------------------------------------------------------------------------------ the check: measures
def rel_lum(rgb: np.ndarray) -> np.ndarray:
    c = rgb.astype(np.float32) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def wcag(l1, l2):
    hi, lo = np.maximum(l1, l2), np.minimum(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def text_masks(f0: np.ndarray, f1: np.ndarray, f2: np.ndarray, thr: int = 10) -> tuple[np.ndarray, np.ndarray]:
    """(all the text incl. outline / shadow, the letters' fill) from the template's three frames: f2 paints the fill in
    the key colour KEY, so a letter crossing a line of its own colour still counts whole."""
    a = np.abs(f0.astype(np.int16) - f1.astype(np.int16)).max(axis=2) > thr
    key = np.abs(f2.astype(np.int16) - np.array(KEY, np.int16)).max(axis=2) < 90
    fill = (np.abs(f2.astype(np.int16) - f1.astype(np.int16)).max(axis=2) > thr) & key
    return a, fill


def letters(fill: np.ndarray) -> dict:
    """The letters in a fill mask: their height (area-weighted median and the smallest 10 %), lines, block."""
    import cv2
    n, lab, st, _ = cv2.connectedComponentsWithStats(fill.astype(np.uint8), connectivity=8)
    if n <= 1:
        return {"found": False}
    comp = st[1:]
    area = comp[:, cv2.CC_STAT_AREA].astype(float)
    keep = area >= max(12, 0.004 * area.sum())
    comp, area = comp[keep], area[keep]
    if not len(comp):
        return {"found": False}
    hts = comp[:, cv2.CC_STAT_HEIGHT].astype(float)
    o = np.argsort(hts)
    cw = np.cumsum(area[o]) / area.sum()
    med = float(hts[o][np.searchsorted(cw, 0.5)])
    low = float(hts[o][np.searchsorted(cw, 0.1)])
    return {"found": True, "height": med, "smallest": low, "count": int(len(comp)),
            "ids": [i + 1 for i in np.flatnonzero(keep)], "labels": lab}


def block_share(mask: np.ndarray) -> float:
    rows = np.flatnonzero(mask.any(axis=1))
    return 0.0 if not len(rows) else float(rows[-1] - rows[0] + 1) / mask.shape[0]


def contrast(f0: np.ndarray, fill: np.ndarray, L: dict) -> dict:
    """WCAG ratio of each letter's fill against the ring of pixels around it in the finished thumbnail (outline,
    shadow or picture): the value that 80 % of the ring reaches, and the median."""
    import cv2
    if not L.get("found"):
        return {"found": False}
    lum = rel_lum(f0)
    lab = L["labels"]
    r = max(2, int(round(L["height"] * 0.05)))
    k1 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    k0 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    ratios = []
    H, W = fill.shape
    for i in L["ids"]:
        ys, xs = np.nonzero(lab == i)
        y0, y1, x0, x1 = max(0, ys.min() - 2 * r), min(H, ys.max() + 2 * r + 1), max(0, xs.min() - 2 * r), min(W, xs.max() + 2 * r + 1)
        m = (lab[y0:y1, x0:x1] == i).astype(np.uint8)
        core = cv2.erode(m, k0)
        if core.sum() < 4:
            core = m
        ring = cv2.dilate(m, k1).astype(bool) & ~cv2.dilate(m, k0).astype(bool) & ~fill[y0:y1, x0:x1]
        if ring.sum() < 4:
            continue
        lf = float(np.median(lum[y0:y1, x0:x1][core.astype(bool)]))
        ratios.append(wcag(lf, lum[y0:y1, x0:x1][ring]))
    if not ratios:
        return {"found": False}
    allr = np.concatenate(ratios)
    return {"found": True, "p20": round(float(np.percentile(allr, 20)), 2), "median": round(float(np.median(allr)), 2)}


def estimate_text(rgb: np.ndarray) -> dict:
    """No template frames (any picture): letters guessed as flat-coloured blobs with strong edges, sitting in rows.
    An estimate - it can take a logo or a sign for text, and miss thin or textured lettering."""
    import cv2
    H, W = rgb.shape[:2]
    s = 640 / max(W, H)
    small = cv2.resize(rgb, (round(W * s), round(H * s)), interpolation=cv2.INTER_AREA) if s < 1 else rgb.copy()
    s = small.shape[0] / H
    g = grey(small).astype(np.uint8)
    mask = np.zeros(g.shape, bool)
    for thr_img in (g, 255 - g):
        _, bw = cv2.threshold(thr_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        n, lab, st, _ = cv2.connectedComponentsWithStats(bw, connectivity=8)
        for i in range(1, n):
            x, y, w, h, a = st[i]
            if not (0.025 * g.shape[0] <= h <= 0.3 * g.shape[0] and 0.15 * h <= w <= 1.6 * h and 0.2 <= a / (w * h) <= 0.85):
                continue
            m = lab[y:y + h, x:x + w] == i
            ring = cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & ~m
            if float(np.abs(g[y:y + h, x:x + w][m].astype(float).mean() - g[y:y + h, x:x + w][ring].astype(float).mean())) < 60:
                continue
            core = cv2.erode(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
            if core.sum() < 10 or float(g[y:y + h, x:x + w][core].astype(float).std()) > 28:
                continue
            mask[y:y + h, x:x + w] |= m
    # keep blobs that share a row with two others (letters come in words; two lamps are no text)
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    keep = np.zeros(mask.shape, bool)
    for i in range(1, n):
        x, y, w, h, a = st[i]
        cy = y + h / 2
        mates = sum(1 for j in range(1, n) if j != i and abs((st[j][1] + st[j][3] / 2) - cy) < 0.3 * h
                    and 0.6 < st[j][3] / h < 1.6)
        if mates >= 2:                                  # three letters in a row at least
            keep |= lab == i
    if not keep.any():
        return {"found": False}
    full = cv2.resize(keep.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST).astype(bool)
    L = letters(full)
    return {**L, "mask": full, "estimated": True} if L.get("found") else {"found": False}


def look(rgb: np.ndarray) -> dict:
    """Brightness (L*, 0-100), saturation (HSV, %), colourfulness (Hasler & Suesstrunk), contrast (L* p95 - p5)."""
    import cv2
    from .colour import to_lab
    small = rgb if rgb.shape[1] <= 480 else cv2.resize(rgb, (480, round(rgb.shape[0] * 480 / rgb.shape[1])),
                                                         interpolation=cv2.INTER_AREA)
    L = to_lab(small)[..., 0]
    hsv = cv2.cvtColor(small, cv2.COLOR_RGB2HSV)
    f = small.astype(float)
    rg, yb = f[..., 0] - f[..., 1], 0.5 * (f[..., 0] + f[..., 1]) - f[..., 2]
    return {"brightness": round(float(L.mean()), 1), "saturation": round(float(hsv[..., 1].mean()) / 2.55, 1),
            "colourfulness": round(float(math.hypot(rg.std(), yb.std()) + 0.3 * math.hypot(rg.mean(), yb.mean())), 1),
            "contrast": round(float(np.percentile(L, 95) - np.percentile(L, 5)), 1)}


# ------------------------------------------------------------------------------------------ the check: rules
def _r(rule: str, status: str, text: str, value=None) -> dict:
    return {"rule": rule, "status": status, "text": text, **({"value": value} if value is not None else {})}


def rule_readability(letter_px: float | None, W: int, size: str, estimated: bool = False) -> dict:
    if not letter_px:
        return _r("readability", "SKIP", "no text found on the picture")
    parts, worst = [], "PASS"
    order = {"PASS": 0, "WARN": 1, "FAIL": 2}
    for name, width, ok, warn in VIEWS[size]:
        px = letter_px * width / W
        st = "PASS" if px >= ok else "WARN" if px >= warn else "FAIL"
        worst = max(worst, st, key=order.get)
        parts.append(f"{name} ({width} px wide): letters {px:.0f} px ({st}, wants {ok})")
    est = " (estimated from the picture)" if estimated else ""
    return _r("readability", worst, f"letters {letter_px:.0f} px tall{est} -> " + "; ".join(parts),
              round(letter_px * VIEWS[size][0][1] / W, 1))


def rule_words(words: str | None) -> dict:
    if words is None:
        return _r("words", "SKIP", "the words are not known (pass --words)")
    n = len(_words(words))
    st = "PASS" if 2 <= n <= 4 else "WARN" if n in (1, 5, 6) else "FAIL"
    return _r("words", st, f"{n} word(s) on the thumbnail: \"{words}\" (2-4 read at a glance)", n)


def rule_text_size(share: float | None) -> dict:
    if share is None:
        return _r("text_size", "SKIP", "no text found")
    st = "PASS" if share >= 0.20 else "WARN" if share >= 0.12 else "FAIL"
    return _r("text_size", st, f"the text block is {share * 100:.0f} % of the frame's height (wants >= 20 %)",
              round(share * 100, 1))


def rule_contrast(c: dict | None) -> dict:
    if not c or not c.get("found"):
        return _r("contrast", "SKIP", "no letters to measure")
    v = c["p20"]
    st = "PASS" if v >= 4.5 else "WARN" if v >= 3 else "FAIL"
    return _r("contrast", st, f"contrast {v:.1f}:1 around 80 % of the letters' edge (median {c['median']:.1f}:1; "
                              "wants 4.5, 3 at least)", v)


def rule_subject(fc: list | None, H: int, size: str) -> dict:
    if fc is None:
        return _r("subject", "SKIP", "no face detector on this PC (its 227 KB model file is missing) - look yourself")
    if not fc:
        return _r("subject", "WARN", "no face found - fine for an object or a place; a big face with an expression "
                                     "usually pulls more clicks")
    share = fc[0][3] / H
    ok, warn = (0.25, 0.12) if size == "16x9" else (0.15, 0.08)
    st = "PASS" if share >= ok else "WARN" if share >= warn else "FAIL"
    return _r("subject", st, f"the biggest face is {share * 100:.0f} % of the frame's height (wants >= {ok * 100:.0f} %)"
              + (f"; {len(fc)} faces" if len(fc) > 1 else ""), round(share * 100, 1))


def rule_look(lk: dict, ref: dict | None) -> dict:
    if not ref:
        return _r("look", "SKIP", f"brightness {lk['brightness']:.0f}, saturation {lk['saturation']:.0f} % - no "
                                  "analysed references with thumbnails for this niche (thumbnail.py refs)")
    dl, ds = lk["brightness"] - ref["brightness"], lk["saturation"] - ref["saturation"]
    st = "PASS" if abs(dl) <= 12 and abs(ds) <= 12 else "WARN"
    return _r("look", st, f"brightness {lk['brightness']:.0f} vs {ref['brightness']:.0f}, saturation "
                          f"{lk['saturation']:.0f} % vs {ref['saturation']:.0f} % in {ref['label']}", round(dl, 1))


def rule_safe(mask: np.ndarray | None, size: str) -> dict:
    if mask is None or not mask.any():
        return _r("safe_zone", "SKIP", "no text mask")
    H, W = mask.shape
    sx, sy = W / SIZES[size][0], H / SIZES[size][1]
    tot, hits = mask.sum(), []
    bad = np.zeros_like(mask)
    for name, (x, y, w, h) in UNSAFE[size]:
        m = np.zeros_like(mask)
        m[round(y * sy):round((y + h) * sy), round(x * sx):round((x + w) * sx)] = True
        part = (mask & m).sum() / tot
        if part > 0.005:
            hits.append(f"{part * 100:.0f} % {name}")
        bad |= m
    share = float((mask & bad).sum() / tot)
    st = "PASS" if share <= 0.02 else "WARN" if share <= 0.15 else "FAIL"
    return _r("safe_zone", st, f"{share * 100:.0f} % of the text where the apps draw or crop"
              + (": " + ", ".join(hits) if hits else ""), round(share * 100, 1))


def rule_file(nbytes: int) -> dict:
    mb = nbytes / 1e6
    st = "PASS" if mb <= 2 else "WARN" if mb <= 50 else "FAIL"
    return _r("file_size", st, f"{mb:.1f} MB" + (" - over 2 MB: upload it from a computer (YouTube's phone app takes "
                                                  "2 MB)" if st == "WARN" else ""), round(mb, 2))


def rule_title_length(title: str | None) -> dict:
    if not title:
        return _r("title_length", "SKIP", "no title (--title, or package.json \"title\")")
    n = len(title)
    st = "PASS" if n <= 50 else "WARN" if n <= 70 else "FAIL"
    return _r("title_length", st, f"title {n} characters (a phone shows ~45-50 before '...')"
              + (f"; cut after: \"{title[:48]}...\"" if n > 50 else ""), n)


def rule_repeat(words: str | None, title: str | None) -> dict:
    if not title or words is None:
        return _r("title_repeat", "SKIP", "needs the title and the thumbnail's words")
    tw = [w for w in keywords(words)] or _words(words)
    tk = {_key(w) for w in _words(title)}
    if not tw:
        return _r("title_repeat", "SKIP", "no words on the thumbnail")
    same = [w for w in tw if _key(w) in tk]
    share = len(same) / len(tw)
    st = "PASS" if share <= 0.34 else "WARN" if share <= 0.67 else "FAIL"
    return _r("title_repeat", st, f"{len(same)} of the thumbnail's {len(tw)} key words are in the title"
              + (f" ({', '.join(same)})" if same else "") + " - the thumbnail should add to the title", round(share * 100))


def script_text(script: str | None) -> tuple[str | None, str, float]:
    """(the script's spoken words, where from, words per minute): a prompt-library id (script-004 / hook-002), a
    text file, or the text itself."""
    if not script:
        return None, "", 150.0
    from . import script as SC
    wpm, src, text = float(getattr(SC, "WPM", 150)), "", None
    if re.fullmatch(r"(script|hook)-\d{3,}", script):
        from . import prompts as PR
        try:
            text = PR.get(script).get("text", "")
        except ValueError as e:
            raise SystemExit(str(e))
        src = f"prompt library {script}"
        try:
            req = SC.request_of(script) or {}
            tr = SC.talk_rate(req.get("like") or []) if req.get("like") else None
            if tr and tr.get("wpm"):
                wpm, src = float(tr["wpm"]), src + f", {round(tr['wpm'])} words/min measured on your references"
        except Exception:                                   # noqa: BLE001 - the rate is a nicety
            pass
    elif Path(script).is_file():
        text, src = Path(script).read_text(encoding="utf-8", errors="replace"), Path(script).name
    else:
        text, src = script, "text"
    try:
        said, _ = SC.spoken(text)
    except Exception:                                       # noqa: BLE001
        said = text
    return said, src, wpm


def rule_promise(title: str | None, said: str | None, src: str = "", wpm: float = 150.0) -> dict:
    if not title or not said:
        return _r("promise", "SKIP", "needs the title and the script (--script)")
    n3 = max(4, int(round(3 * wpm / 60)))
    first = _words(said)[:n3]
    fk = {_key(w) for w in first}
    keys = keywords(title)
    if not keys:
        return _r("promise", "SKIP", "the title has no key words")
    hit = [w for w in keys if _key(w) in fk]
    share = len(hit) / len(keys)
    st = "PASS" if share >= 0.4 else "WARN" if hit else "FAIL"
    return _r("promise", st, f"{len(hit)} of the title's {len(keys)} key words in the first 3 s ({n3} words at "
                             f"{round(wpm)} words/min{', ' + src if src else ''}): "
                             f"{', '.join(hit) or 'none'} - first words: \"{' '.join(first)}\"", round(share * 100))


def check_frames(f0: np.ndarray, f1: np.ndarray | None, f2: np.ndarray | None, size: str, words: str | None,
                 title: str | None, said: str | None, said_src: str, wpm: float, ref: dict | None,
                 nbytes: int) -> list[dict]:
    """All rules for one picture. f1 / f2 = the template's frames without words / with the fill only (None for any
    picture: the text is estimated)."""
    H, W = f0.shape[:2]
    if f1 is not None and f2 is not None:
        allm, fill = text_masks(f0, f1, f2)
        L = letters(fill) if fill.any() else {"found": False}
        est = False
        photo = f1
    else:
        L = estimate_text(f0)
        allm = fill = L.get("mask") if L.get("found") else None
        est = True
        photo = f0
    out = [rule_readability(L.get("height") if L.get("found") else None, W, size, est),
           rule_words(words),
           rule_text_size(block_share(allm) if allm is not None and allm.any() else None),
           rule_contrast(contrast(f0, fill, L) if L.get("found") else None),
           rule_subject(faces(photo), H, size),
           rule_look(look(f0), ref),
           rule_safe(allm, size),
           rule_file(nbytes),
           rule_title_length(title),
           rule_repeat(words, title),
           rule_promise(title, said, said_src, wpm)]
    return out


def overall(lines: list[dict]) -> str:
    sts = {x["status"] for x in lines}
    return "FAIL" if "FAIL" in sts else "WARN" if "WARN" in sts else "PASS"


def check_project(project: str, title: str | None = None, script: str | None = None, niche: str | None = None,
                  ids: list[str] | None = None) -> dict:
    from .project import Project
    prj = Project(project)
    pk = read_package(prj)
    title = title if title is not None else pk.get("title")
    said, src, wpm = script_text(script)
    ref = ref_norm(niche)
    res, thumbs = {}, pk.get("thumbnails") or []
    if not thumbs:
        raise SystemExit(f"{prj.name}: no thumbnails yet (thumbnail.py make {prj.name} --id A ...)")
    for t in thumbs:
        if ids and t["id"] not in ids:
            continue
        folder = LAB / t["files"]["folder"]
        per = {}
        for size in SIZES:
            p = LAB / t["files"][size]
            f0 = np.asarray(Image.open(p).convert("RGB"))
            f1p, f2p = folder / f"check_{size}_nowords.png", folder / f"check_{size}_fill.png"
            f1 = np.asarray(Image.open(f1p).convert("RGB")) if f1p.exists() else None
            f2 = np.asarray(Image.open(f2p).convert("RGB")) if f2p.exists() else None
            per[size] = check_frames(f0, f1, f2, size, t.get("words"), title, said, src, wpm, ref, p.stat().st_size)
        t["check"] = {"date": time.strftime("%Y-%m-%d %H:%M"), "title": title, "script": script, "niche": niche,
                      "result": overall(per["16x9"] + per["9x16"]), **per}
        res[t["id"]] = t["check"]
    pk2 = read_package(prj)                                  # merge into the newest file (only our key)
    cur = {x.get("id"): x for x in pk2.get("thumbnails") or []}
    for t in thumbs:
        if t["id"] in res and t["id"] in cur:
            cur[t["id"]]["check"] = t["check"]
    update_package(prj, thumbnails=[cur[k] for k in sorted(cur)])
    return res


def check_image(path: str, title: str | None = None, script: str | None = None, niche: str | None = None,
                words: str | None = None) -> dict:
    p = Path(path)
    im = np.asarray(Image.open(p).convert("RGB"))
    H, W = im.shape[:2]
    size = "9x16" if H > W else "16x9"
    said, src, wpm = script_text(script)
    lines = check_frames(im, None, None, size, words, title, said, src, wpm, ref_norm(niche), p.stat().st_size)
    return {"file": str(p), "size": f"{W}x{H}", "format": size, "result": overall(lines), "lines": lines}


# ------------------------------------------------------------------------------------------ references' thumbnails
def ref_thumb(name: str) -> Path | None:
    d = ANALYSIS / name / "content"
    hits = sorted(p for p in d.glob("thumbnail.*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))
    return hits[0] if hits else None


def measure_ref(name: str, force: bool = False) -> dict | None:
    """One reference's thumbnail measured -> analysis\\<name>\\content\\thumbnail.json (re-used while unchanged)."""
    p = ref_thumb(name)
    if not p:
        return None
    out = p.parent / "thumbnail.json"
    st = p.stat()
    sig = f"{p.name}:{st.st_size}:{st.st_mtime_ns}"
    if out.exists() and not force:
        try:
            old = json.loads(out.read_text(encoding="utf-8"))
            if old.get("sig") == sig and (old.get("face_detector") or face_model() is None):
                return old
        except (OSError, ValueError):
            pass
    from .colour import palette
    rgb = np.asarray(Image.open(p).convert("RGB"))
    H, W = rgb.shape[:2]
    fc = faces(rgb)
    est = estimate_text(rgb)
    m = {"sig": sig, "file": p.name, "size": [W, H], **look(rgb), "palette": palette(rgb, 4),
         "face_detector": fc is not None, "faces": None if fc is None else len(fc),
         "face_share": None if not fc else round(fc[0][3] / H, 3),
         "text_estimate": {"letter_share": round(est["height"] / H, 3), "blobs": est["count"]} if est.get("found") else None,
         "measured": time.strftime("%Y-%m-%d %H:%M")}
    out.write_text(json.dumps(m, indent=1), encoding="utf-8")
    return m


def _ref_rows() -> list[dict]:
    from .knowledge import meta
    rows = []
    for d in sorted(ANALYSIS.iterdir()) if ANALYSIS.exists() else []:
        if not (d / "events.json").exists() or not ref_thumb(d.name):
            continue
        m = measure_ref(d.name)
        if not m:
            continue
        mt = meta(d.name)
        try:
            stt = json.loads((d / "content" / "stats.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            stt = {}
        rows.append({"name": d.name, "title": stt.get("title") or mt.get("title") or d.name,
                     "category": mt.get("category") or "other", "tags": mt.get("tags") or [],
                     "outperformer": stt.get("outperformer"), "views": stt.get("views"), "likes": stt.get("likes"),
                     "platform": stt.get("platform"), **{k: m[k] for k in ("brightness", "saturation", "colourfulness",
                                                                           "contrast", "palette", "faces", "face_share",
                                                                           "text_estimate", "size")}})
    return rows


def _wmed(vals, ws) -> float | None:
    v = [(x, w) for x, w in zip(vals, ws) if x is not None]
    if not v:
        return None
    v.sort()
    tot, acc = sum(w for _, w in v), 0.0
    for x, w in v:
        acc += w
        if acc >= tot / 2:
            return x
    return v[-1][0]


def refs(niche: str | None = None) -> dict:
    """Every analysed reference with a thumbnail, measured; per niche (category, and each tag) a weighted summary:
    weight = the outperformer score (views / followers; 1 when unknown), so the videos that beat their channel count
    most."""
    rows = _ref_rows()
    if niche:
        rows = [r for r in rows if niche in (r["category"], *r["tags"])]
    groups: dict = {}
    for r in rows:
        for g in {r["category"], *r["tags"]}:
            groups.setdefault(g, []).append(r)
    summ = {}
    for g, rs in groups.items():
        rs = sorted(rs, key=lambda r: -(r["outperformer"] or 0))
        ws = [max(0.25, r["outperformer"] or 1.0) for r in rs]
        summ[g] = {"videos": len(rs), "label": f"{g} ({len(rs)} reference{'s' if len(rs) > 1 else ''})",
                   **{k: _wmed([r[k] for r in rs], ws) for k in ("brightness", "saturation", "colourfulness", "contrast")},
                   "faces": sum(1 for r in rs if r["faces"]), "face_known": sum(1 for r in rs if r["faces"] is not None),
                   "face_share": _wmed([r["face_share"] for r in rs], ws),
                   "colours": [c for r in rs[:2] for c, _ in r["palette"][:3]],
                   "best": [{"name": r["name"], "title": r["title"], "outperformer": r["outperformer"]} for r in rs[:3]]}
    return {"references": rows, "niches": summ}


def ref_norm(niche: str | None) -> dict | None:
    if not niche:
        return None
    try:
        s = refs(niche)["niches"].get(niche)
    except Exception:                                       # noqa: BLE001 - no references is no failure
        return None
    return s if s and s.get("brightness") is not None else None


def packaging_lines() -> list[str]:
    """Claude's memory: what the analysed references' thumbnails look like per niche (outperformers first) - a few
    lines, only when there are thumbnails. Reads the measurements (content\\thumbnail.json) and the numbers."""
    try:
        R = refs()
    except Exception:                                       # noqa: BLE001
        return []
    cats = {r["category"] for r in R["references"]}
    out = []
    for g in sorted(cats):
        s = R["niches"][g]
        best = "; ".join(f"{b['title'][:40]}" + (f" ({b['outperformer']}x its followers)" if b["outperformer"] else "")
                         for b in s["best"][:2])
        face = (f", a face in {s['faces']}/{s['face_known']}" + (f" ({round(s['face_share'] * 100)} % of the height)"
                                                                 if s.get("face_share") else "")) if s["face_known"] else ""
        out.append(f"- {g}: {s['videos']} thumbnail(s) - brightness {s['brightness']:.0f}, saturation "
                   f"{s['saturation']:.0f} %, colourfulness {s['colourfulness']:.0f}, contrast {s['contrast']:.0f}"
                   f"{face}; colours {' '.join(s['colours'][:4])}. Best: {best}")
    return out


# ------------------------------------------------------------------------------------------ self-check
def selfcheck(verbose: bool = False) -> dict:
    """Synthetic pictures and texts with known answers: one PASS case and one failing case per rule. No video, no
    HyperFrames, no face model (the subject rule is checked on given boxes)."""
    from PIL import ImageFont
    t0 = time.time()
    lines, ok = [], True

    def check(cond, msg):
        nonlocal ok
        ok &= bool(cond)
        lines.append(("PASS " if cond else "FAIL ") + msg)

    def font(px):
        for n in ("arialbd.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"):
            try:
                return ImageFont.truetype(n, px)
            except OSError:
                continue
        return ImageFont.load_default(px)

    def frames(W, H, text, px, xy, fg, bg, outline=0, oc=(0, 0, 0)):
        base = Image.new("RGB", (W, H), bg)
        d = ImageDraw.Draw(base)
        for i in range(0, W, 40):                           # some texture so the background is a picture
            d.line((i, 0, i - H, H), fill=tuple(max(0, c - 18) for c in bg), width=6)
        f1 = np.asarray(base).copy()
        im0, im2 = base.copy(), base.copy()
        ImageDraw.Draw(im0).text(xy, text, fill=fg, font=font(px), stroke_width=outline, stroke_fill=oc)
        ImageDraw.Draw(im2).text(xy, text, fill=KEY, font=font(px))
        return np.asarray(im0), f1, np.asarray(im2)

    big = frames(1280, 720, "BIG WORDS", 190, (60, 230), (255, 255, 255), (90, 110, 130), 10)
    small = frames(1280, 720, "tiny words", 26, (60, 330), (215, 215, 215), (250, 250, 250))
    a, fill = text_masks(*big)
    Lb = letters(fill)
    a2, fill2 = text_masks(*small)
    Ls = letters(fill2)
    check(Lb["found"] and 120 <= Lb["height"] <= 150, f"letter height measured from the frames: {Lb.get('height')} px "
                                                       "(190 px Arial Bold capitals = ~137)")
    r1, r2 = rule_readability(Lb["height"], 1280, "16x9"), rule_readability(Ls.get("height"), 1280, "16x9")
    check(r1["status"] == "PASS" and r2["status"] == "FAIL", f"readability: big {r1['status']} ({r1['value']} px in "
                                                             f"the phone feed), tiny {r2['status']} ({r2.get('value')} px)")
    w1, w2 = rule_words("BIG WORDS"), rule_words("this has far too many words on it")
    check(w1["status"] == "PASS" and w2["status"] == "FAIL", f"words: 2 {w1['status']}, 8 {w2['status']}")
    s1, s2 = rule_text_size(block_share(a)), rule_text_size(block_share(a2))
    check(s1["status"] == "PASS" and s2["status"] == "FAIL", f"text size: {s1['value']} % {s1['status']}, "
                                                             f"{s2['value']} % {s2['status']}")
    c1, c2 = rule_contrast(contrast(big[0], fill, Lb)), rule_contrast(contrast(small[0], fill2, Ls))
    check(c1["status"] == "PASS" and c2["status"] == "FAIL", f"contrast: white + black outline {c1['value']}:1 "
                                                             f"{c1['status']}, light grey on white {c2['value']}:1 {c2['status']}")
    check(abs(float(wcag(1.0, 0.0)) - 21) < 1e-6 and abs(float(wcag(rel_lum(np.array([[118, 118, 118]], np.uint8))[0], 1.0)) - 4.54) < 0.05,
          "WCAG formula: white / black 21:1, #767676 on white 4.54:1")
    f1, f2 = rule_subject([[0, 0, 200, 260, 0.9]], 720, "16x9"), rule_subject([[0, 0, 30, 40, 0.9]], 720, "16x9")
    check(f1["status"] == "PASS" and f2["status"] == "FAIL" and rule_subject(None, 720, "16x9")["status"] == "SKIP",
          f"subject: face 36 % {f1['status']}, 6 % {f2['status']}, no detector SKIP")
    ref = {"brightness": 55.0, "saturation": 40.0, "label": "test (2 references)"}
    l1 = rule_look({"brightness": 58.0, "saturation": 44.0}, ref)
    l2 = rule_look({"brightness": 22.0, "saturation": 40.0}, ref)
    check(l1["status"] == "PASS" and l2["status"] == "WARN" and rule_look({"brightness": 1, "saturation": 1}, None)["status"] == "SKIP",
          f"look vs the niche: close {l1['status']}, much darker {l2['status']}")
    lk = look(np.full((90, 160, 3), (255, 0, 0), np.uint8))
    check(abs(lk["saturation"] - 100) < 0.5 and abs(lk["brightness"] - 53.2) < 1.5, f"look of pure red: L* "
                                                                                  f"{lk['brightness']}, saturation {lk['saturation']} %")
    m_ok = np.zeros((1920, 1080), bool)
    m_ok[400:700, 100:980] = True
    m_bad = np.zeros((1920, 1080), bool)
    m_bad[1600:1850, 100:980] = True
    z1, z2 = rule_safe(m_ok, "9x16"), rule_safe(m_bad, "9x16")
    check(z1["status"] == "PASS" and z2["status"] == "FAIL", f"safe zone 9:16: upper third {z1['status']}, bottom "
                                                             f"{z2['status']} ({z2['value']} %)")
    b1, b2 = rule_file(1_200_000), rule_file(60_000_000)
    check(b1["status"] == "PASS" and b2["status"] == "FAIL", f"file size: 1.2 MB {b1['status']}, 60 MB {b2['status']}")
    t1 = rule_title_length("I filmed a music video in my room at 4AM")
    t2 = rule_title_length("I filmed a whole music video in my tiny bedroom at 4AM with no budget, no crew and no "
                           "lights and this happened")
    check(t1["status"] == "PASS" and t2["status"] == "FAIL", f"title length: {t1['value']} chars {t1['status']}, "
                                                             f"{t2['value']} chars {t2['status']}")
    title = "I filmed a music video in my room at 4AM"
    p1, p2 = rule_repeat("NO BUDGET", title), rule_repeat("MY ROOM AT 4AM", title)
    check(p1["status"] == "PASS" and p2["status"] == "FAIL", f"thumbnail vs title: new words {p1['status']}, "
                                                             f"repeated {p2['status']}")
    q1 = rule_promise(title, "At 4AM I filmed this music video in my room. Here's how.", "test")
    q2 = rule_promise(title, "Hey guys, welcome back to the channel, today is a great day and", "test")
    check(q1["status"] == "PASS" and q2["status"] == "FAIL", f"title's promise in the first 3 s: {q1['status']} "
                                                             f"({q1['value']} %), {q2['status']}")
    e = estimate_text(big[0])
    check(e.get("found") and abs(e["height"] - Lb["height"]) / Lb["height"] < 0.25,
          f"text estimate without the template's frames: {e.get('height')} px vs {Lb['height']} measured")
    g = CROPS[0][1]
    check(g[2] / g[3] == 0.75 and g[1] + g[3] / 2 == 960, "the 3:4 grid crop sits in the middle of the cover")
    secs = round(time.time() - t0, 2)
    if verbose:
        print("\n".join(lines))
    return {"passed": ok, "seconds": secs, "lines": lines}
