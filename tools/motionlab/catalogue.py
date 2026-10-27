"""The clip catalogue (0.6.1 "quality over quantity", step 1; the user, 2026-10-26: "feedback i got that u are having a
bad time editing videos when i give u lots of b-rolls, how could we improve that?"): every clip of a project looked
at ONCE and kept in build\\clips.json, so no window edits blind or looks again.

The lab's part (no Claude, from the light cache - prep_footage.py): each clip split into its MOMENTS (a new shot
inside a clip: the analyser's own cut detector, motionlab\\detect.detect_cuts on motionlab\\signals.FrameMetrics of
the light frames), each moment's USABLE windows (sharp, exposed, steady or one clean move) and BAD ones (blurry,
shaky, too dark / bright, flat, frozen) with why, its camera motion (still / steady / pan / tilt / zoom / moving /
shaky) and light, look-alike moments GROUPED across clips, the day it was filmed (the file's own creation date, like a
photo's date taken), one KEY frame. Claude's part: one line per moment from the key frames' sheets (what it shows,
shot size, where, a few tags) - `say()`; a line the user corrects wins over Claude's ("by": "user").

    make(prj, cfg) -> the catalogue (written to build\\clips.json; lines kept for moments that stay the same)
    sheets(prj, todo=False) -> the key frames' sheets (build\\catalogue\\sheet_NN.jpg, frame + timecode on each)
    say(prj, lines, by) -> what was kept / refused        lines = {moment id: {what, size, where, tags}}
    text(cat) -> the catalogue in words (the brief's *The clips*, Claude's reading)
"""
from __future__ import annotations

import datetime as _dt
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np

from . import footage as FC
from .timecode import frame_to_tc

VERSION = 1
SIZES = ("wide", "medium", "close", "detail")
MIN_MOMENT_S = 0.25                             # a moment shorter than this is folded into its neighbour (a flash)
MIN_WINDOW_S = 0.4                              # a usable window at least this long
SPLIT_LONG_S = 8.0                              # a moment longer than this is split where its picture has changed
BLOCK = 64


def _rel(prj) -> Path:
    return prj.build / "clips.json"


# ------------------------------------------------------------------------------------------------ measuring
def _light(cache: Path, sid: str):
    lp, lm = FC.light_paths(cache, sid)
    m = json.loads(lm.read_text(encoding="utf-8"))
    return m, np.memmap(lp, dtype=np.uint8, mode="r", shape=(int(m["frames"]), int(m["height"]) * 3 // 2, int(m["width"])))


def _metrics(la: np.ndarray, cfg: dict) -> tuple[dict, np.ndarray]:
    """The analyser's per-frame numbers for a clip's light frames (motionlab\\signals: the same as an analysis)."""
    from .signals import FrameMetrics, fit_long_side
    acfg = cfg["analysis"]
    lh, lw = la.shape[1] * 2 // 3, la.shape[2]
    w, h = fit_long_side(lw / lh, acfg["long_side_px"])
    tw, th = fit_long_side(lw / lh, acfg["thumb_long_side_px"])

    def frame(i):
        bgr = cv2.cvtColor(np.ascontiguousarray(la[i]), cv2.COLOR_YUV2BGR_I420)
        return bgr if (bgr.shape[1], bgr.shape[0]) == (w, h) else cv2.resize(bgr, (w, h), interpolation=cv2.INTER_AREA)

    def block(i0, i1):
        fm = FrameMetrics(w, h, tw, th, lw, acfg)
        fm.warm([frame(i) for i in range(max(0, i0 - int(acfg["repeat_search_frames"])), i0)])
        return [fm.compute(frame(i)) for i in range(i0, i1)]
    n = la.shape[0]
    rows: dict[str, list] = {}
    thumbs = []
    threads = cv2.getNumThreads()
    cv2.setNumThreads(1)
    try:
        with ThreadPoolExecutor(max(1, min(6, (__import__("os").cpu_count() or 2) - 1))) as ex:
            for res in ex.map(lambda a: block(a, min(n, a + BLOCK)), range(0, n, BLOCK)):
                for m, thumb in res:
                    for k, v in m.items():
                        rows.setdefault(k, []).append(v)
                    thumbs.append(thumb)
    finally:
        cv2.setNumThreads(threads)
    met = {k: np.asarray(v, np.float64) for k, v in rows.items() if len(v) == n}
    met["frame"] = np.arange(n, dtype=np.float64)
    return met, np.stack(thumbs)


def _runs(mask: np.ndarray, min_len: int) -> list[list[int]]:
    out, s = [], None
    for i, v in enumerate(list(mask) + [False]):
        if v and s is None:
            s = i
        elif not v and s is not None:
            if i - s >= min_len:
                out.append([s, i - 1])
            s = None
    return out


def _desc(img: np.ndarray):
    """A look-alike descriptor of a (BGR) key frame: its shape, colours, layout of light and dark, and edges."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1, 2], None, [12, 4, 4], [0, 180, 0, 256, 0, 256]).ravel()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    def z(v):
        v = v.astype(np.float32).ravel()
        return (v - v.mean()) / (v.std() + 1e-6) / np.sqrt(len(v))
    h, w = gray.shape
    ew, eh = (160, max(2, int(160 * h / w))) if w >= h else (max(2, int(160 * w / h)), 160)
    edges = cv2.GaussianBlur(cv2.Canny(cv2.resize(gray, (ew, eh)), 50, 150).astype(np.float32), (0, 0), 3)
    return (round(w / h, 2), np.sqrt(hist / (hist.sum() + 1e-9)),
            z(cv2.resize(gray, (16, max(2, int(16 * h / w))), interpolation=cv2.INTER_AREA)), z(edges))


def _alike(a, b) -> bool:
    """The same scene (measured 2026-10-26 on zz_many_clips: the same shot from two clips scored colour <= 0.035,
    layout >= 0.74, edges >= 0.65; different scenes layout <= 0.62, edges <= 0.42 - dark and black-and-white ones
    included, which colour alone lumped together)."""
    if abs(a[0] - b[0]) > 0.05 or len(a[2]) != len(b[2]) or len(a[3]) != len(b[3]):
        return False
    return (1.0 - float(np.dot(a[1], b[1])) < 0.06 and float(np.dot(a[2], b[2])) > 0.7
            and float(np.dot(a[3], b[3])) > 0.5)


def _moments(met: dict, thumbs: np.ndarray, fps: float, cfg: dict) -> list[list[int]]:
    from .detect import Ctx, detect_cuts
    n = len(met["frame"])
    ctx = Ctx(met, thumbs, fps, cfg)
    cuts, _ = detect_cuts(ctx)
    edges = [0] + sorted({int(c["frame"]) for c in cuts if 0 < int(c["frame"]) < n}) + [n]
    segs = [[a, b - 1] for a, b in zip(edges[:-1], edges[1:]) if b - 1 >= a]
    short = max(2, int(round(MIN_MOMENT_S * fps)))
    merged: list[list[int]] = []
    for s in segs:                                          # a flash / glitch of a few frames joins its neighbour
        if merged and (s[1] - s[0] + 1 < short or merged[-1][1] - merged[-1][0] + 1 < short):
            merged[-1][1] = s[1]
        else:
            merged.append(s)
    out = []
    for a, b in merged:                                     # a long take whose picture has turned into another
        while (b - a + 1) / fps > SPLIT_LONG_S:
            d0 = _desc(thumbs[a])
            far = next((i for i in range(a + int(2 * fps), b - int(2 * fps), max(1, int(fps / 2)))
                        if not _alike(d0, _desc(thumbs[i]))), None)
            if far is None:
                break
            out.append([a, far - 1])
            a = far
        out.append([a, b])
    return out


def _quality(met: dict, a: int, b: int, fps: float, sharp_ref: float) -> tuple[list, list, dict]:
    """A moment's usable windows, its bad ones with why, and its motion / light in words."""
    sl = slice(a, b + 1)
    sharp = np.nan_to_num(met.get("sharp_med", met["sharpness"])[sl], nan=0.0)
    luma, p05, p95 = met["luma_mean"][sl], met["luma_p05"][sl], met["luma_p95"][sl]
    lstd = met["luma_std"][sl]
    tx = np.nan_to_num(met.get("tx_pct", np.zeros(len(met["frame"])))[sl])
    ty = np.nan_to_num(met.get("ty_pct", np.zeros(len(met["frame"])))[sl])
    sc = np.nan_to_num(met.get("scale", np.ones(len(met["frame"])))[sl], nan=1.0)
    dup = np.nan_to_num(met.get("dup", np.zeros(len(met["frame"])))[sl])
    n = b - a + 1
    k = max(3, int(round(fps * 0.3)) | 1)
    sm = lambda x: np.convolve(np.pad(x, k // 2, mode="edge"), np.ones(k) / k, mode="valid")   # noqa: E731
    jit = np.sqrt(sm((tx - sm(tx)) ** 2) + sm((ty - sm(ty)) ** 2))   # (the shake: motion that keeps reversing)
    top = float(np.percentile(sharp, 80)) if n else 0.0
    speed = np.hypot(sm(tx), sm(ty))
    # (2026-10-26, zz_many_clips: dark grades are a look, not a fault - "too dark" = almost nothing reaches mid-grey;
    # motion blur inside a camera move is part of a clean move; a still picture is described, never "bad")
    why = {
        "blurry": ((sharp < 0.35 * top) & (speed < 0.5)) | (sharp < 0.2 * top) | (sharp < 0.2 * sharp_ref),
        "too dark": (p95 < 12) & (luma < 6),
        "too bright": (p05 > 88) | (luma > 94),
        "flat": lstd < 3.0,
        "shaky": (jit > 1.2) & (lstd >= 6),                     # (a dark, flat picture makes the tracker jitter)
    }
    bad_any = np.zeros(n, bool)
    bad = []
    for word, mask in why.items():
        for r0, r1 in _runs(mask, max(2, int(round(fps * 0.2)))):
            bad.append([a + r0, a + r1, word])
            bad_any[r0:r1 + 1] = True
    usable = [[a + r0, a + r1] for r0, r1 in _runs(~bad_any, max(2, min(n, int(round(MIN_WINDOW_S * fps)))))]
    # (a clean fast-cut moment shorter than MIN_WINDOW_S is usable whole)
    zoom = float(np.prod(np.clip(sc, 0.8, 1.25)))
    if np.mean(dup) > 0.8:
        motion = "a still picture"
    elif np.median(jit) > 1.2 and np.median(lstd) >= 6:
        motion = "shaky"
    elif abs(zoom - 1) > 0.12:
        motion = "zoom in" if zoom > 1 else "zoom out"
    elif np.median(speed) < 0.08:
        motion = "still"
    elif np.median(np.abs(sm(tx))) > 2 * np.median(np.abs(sm(ty))) and abs(np.median(sm(tx))) > 0.12:
        motion = "pan " + ("left" if np.median(sm(tx)) > 0 else "right")      # (the picture moves the other way)
    elif abs(np.median(sm(ty))) > 0.12:
        motion = "tilt " + ("up" if np.median(sm(ty)) > 0 else "down")
    elif np.median(speed) < 0.35:
        motion = "steady"
    else:
        motion = "moving"
    lm = float(np.median(luma))
    light = "dark" if lm < 18 else "dim" if lm < 32 else "bright" if lm > 72 else "normal"
    return usable, sorted(bad), {"motion": motion, "light": light, "luma": round(lm, 1)}


def _key(met: dict, usable: list, a: int, b: int) -> int:
    sharp = np.nan_to_num(met.get("sharp_med", met["sharpness"]), nan=0.0)
    if usable:
        u0, u1 = max(usable, key=lambda r: r[1] - r[0])
    else:
        u0, u1 = a, b
    idx = np.arange(u0, u1 + 1)
    c = (u0 + u1) / 2
    score = sharp[u0:u1 + 1] * (1.0 - 0.6 * np.abs(idx - c) / max(1.0, (u1 - u0) / 2))
    return int(idx[int(np.argmax(score))])


def _salient(rgb: np.ndarray) -> tuple[float, float]:
    """Where the eye goes in a picture (0..1 across / down): the spectral residual (Hou & Zhang 2007) on a small grey
    copy, a mild pull to the middle, the weighted centre of its strongest tenth."""
    h, w = rgb.shape[:2]
    gw, gh = (64, max(8, int(64 * h / w))) if w >= h else (max(8, int(64 * w / h)), 64)
    g = cv2.resize(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), (gw, gh), interpolation=cv2.INTER_AREA).astype(np.float32)
    F = np.fft.fft2(g)
    amp = np.log(np.abs(F) + 1e-6)
    S = np.abs(np.fft.ifft2(np.exp(amp - cv2.blur(amp, (3, 3)) + 1j * np.angle(F)))) ** 2
    S = cv2.GaussianBlur(S.astype(np.float32), (0, 0), 2.0)
    yy, xx = np.mgrid[0:gh, 0:gw]
    S *= np.exp(-(((xx - gw / 2) / (0.6 * gw)) ** 2 + ((yy - gh / 2) / (0.6 * gh)) ** 2))
    m = S >= np.percentile(S, 90)
    wts = S[m]
    return float((xx[m] * wts).sum() / wts.sum() + 0.5) / gw, float((yy[m] * wts).sum() / wts.sum() + 0.5) / gh


def _subject(la: np.ndarray, frames: list[int]) -> dict | None:
    """A moment's subject in its usable frames: the biggest face (the middle of its eyes-to-mouth), else where the eye
    goes - {"x", "y" (0..1 of the picture), "by": "face" | "look"}; the crop of a clip whose shape is not the
    video's (a horizontal clip in a vertical video) and a punch-in centre on it."""
    from .thumbnail import faces
    pts, by = [], "look"
    for i in frames:
        rgb = FC.decode(la[min(i, la.shape[0] - 1)], "i420")
        h, w = rgb.shape[:2]
        f = faces(rgb, 0.7)
        if f:
            x, y, fw, fh, _ = f[0]
            pts.append(((x + fw / 2) / w, (y + 0.5 * fh) / h))
            by = "face"
    if by != "face":
        pts = [_salient(FC.decode(la[min(i, la.shape[0] - 1)], "i420")) for i in frames]
    if not pts:
        return None
    return {"x": round(float(np.median([p[0] for p in pts])), 3), "y": round(float(np.median([p[1] for p in pts])), 3),
            "by": by}


def filmed(path: Path) -> str | None:
    """When the clip was filmed: the file's own creation date (a phone's), else its modified time."""
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format_tags:stream_tags", "-of", "json",
                            str(path)], capture_output=True, text=True, timeout=30)
        d = json.loads(r.stdout or "{}")
        tags = {**{k.lower(): v for s in d.get("streams", []) for k, v in (s.get("tags") or {}).items()},
                **{k.lower(): v for k, v in ((d.get("format") or {}).get("tags") or {}).items()}}
        for k in ("com.apple.quicktime.creationdate", "creation_time", "date"):
            if tags.get(k):
                return str(tags[k])[:19].replace("Z", "")
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    try:
        return _dt.datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
    except OSError:
        return None


# ------------------------------------------------------------------------------------------------ the catalogue
def make(prj, cfg: dict, log=print) -> dict:
    """The lab's part for every clip with a light cache; Claude's / the user's lines kept for moments that stay."""
    man = json.loads(prj.manifest_path.read_text(encoding="utf-8"))
    old = load(prj) or {}
    old_say = {}
    for c in old.get("clips", []):
        for mo in c.get("moments", []):
            if mo.get("say"):
                old_say[(json.dumps(c.get("fingerprint"), sort_keys=True), mo["a"], mo["b"])] = mo["say"]
    clips, descs = [], []
    t0 = time.time()
    for sid, ent in sorted(man["sources"].items(), key=lambda kv: (len(kv[0]), kv[0])):
        if ent.get("photo") or not FC.light_paths(prj.cache, sid)[1].exists():
            continue
        lm, la = _light(prj.cache, sid)
        fps = float(lm["fps"])
        met, thumbs = _metrics(la, cfg)
        sharp_ref = float(np.nanmedian(met.get("sharp_med", met["sharpness"])))
        moments = []
        for k, (a, b) in enumerate(_moments(met, thumbs, fps, cfg), 1):
            usable, bad, words = _quality(met, a, b, fps, sharp_ref)
            key = _key(met, usable, a, b)
            subj = _subject(la, [key])                      # (one frame: the face finder is the slow part)
            mo = {"m": f"{sid}{k}", "a": a, "b": b, "key": key, **words, "usable": usable, "bad": bad,
                  **({"subject": subj} if subj else {})}
            say = old_say.get((json.dumps(ent.get("fingerprint"), sort_keys=True), a, b))
            if say:
                mo["say"] = say
            moments.append(mo)
            descs.append((mo["m"], _desc(cv2.cvtColor(np.ascontiguousarray(la[key]), cv2.COLOR_YUV2BGR_I420))))
        info = json.loads(FC.paths(prj.cache, sid, True)[1].read_text(encoding="utf-8")) \
            if FC.paths(prj.cache, sid, True)[1].exists() else {}
        w, h = int(info.get("src_width") or 0), int(info.get("src_height") or 0)
        clips.append({"id": sid, "name": ent["name"], "fingerprint": ent.get("fingerprint"), "frames": int(lm["frames"]),
                      "fps": fps, "seconds": round(lm["frames"] / fps, 2), "filmed": filmed(Path(ent["path"])),
                      "size": [w, h], "orientation": "vertical" if h > w else "square" if h == w else "horizontal",
                      "moments": moments})
        log(f"{sid} {ent['name']}: {len(moments)} moment(s), {sum(len(m['usable']) for m in moments)} usable window(s)")
    parent = {m: m for m, _ in descs}                      # look-alike moments: one group (union-find)

    def root(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for i, (m1, d1) in enumerate(descs):
        for m2, d2 in descs[i + 1:]:
            if _alike(d1, d2):
                parent[root(m2)] = root(m1)
    groups: dict[str, list[str]] = {}
    for m, _ in descs:
        groups.setdefault(root(m), []).append(m)
    gid = {}
    for k, members in enumerate(sorted((g for g in groups.values() if len(g) > 1), key=lambda g: g[0]), 1):
        for m in members:
            gid[m] = k
    for c in clips:
        for mo in c["moments"]:
            if mo["m"] in gid:
                mo["group"] = gid[mo["m"]]
    days = sorted({(c["filmed"] or "")[:10] for c in clips if c.get("filmed")})
    cat = {"version": VERSION, "made": _dt.datetime.now().isoformat(timespec="seconds"), "clips": clips,
           "groups": {str(k): [m for m in gid if gid[m] == k] for k in sorted(set(gid.values()))}, "days": days,
           "seconds": round(time.time() - t0, 1)}
    prj.check(_rel(prj)).write_text(json.dumps(cat, ensure_ascii=False, indent=1), encoding="utf-8")
    return cat


def load(prj) -> dict | None:
    try:
        return json.loads(_rel(prj).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def moments(cat: dict):
    for c in cat.get("clips", []):
        for mo in c.get("moments", []):
            yield c, mo


def sheets(prj, todo: bool = False, per: int = 20) -> list[Path]:
    """The key frames on sheets (5 x 4), each tile "A3 f40 00:00:01:10" - for Claude's lines (todo = only the
    moments without one)."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from storyboard import make_sheets
    cat = load(prj)
    if not cat:
        raise SystemExit("no catalogue yet - tools\\catalogue.py make <project> first")
    tiles = []
    cache = {}
    for c, mo in moments(cat):
        if todo and mo.get("say"):
            continue
        if c["id"] not in cache:
            cache[c["id"]] = _light(prj.cache, c["id"])
        lm, la = cache[c["id"]]
        rgb = FC.decode(la[min(mo["key"], la.shape[0] - 1)], "i420")
        tiles.append((_square(rgb), f"{mo['m']} f{mo['key']} {frame_to_tc(mo['key'], c['fps'])}"))
    if not tiles:
        return []
    out = prj.check(prj.build / "catalogue")
    out.mkdir(parents=True, exist_ok=True)
    return make_sheets(tiles, out, "sheet", f"{prj.name}: each moment's key frame (moment, frame, timecode) - "
                       f"{len(tiles)} moment(s)", 5, 240, rows=per // 5)


def _square(rgb: np.ndarray, size: int = 360) -> np.ndarray:
    """A key frame whole in a square tile (vertical and horizontal clips side by side, nothing stretched)."""
    h, w = rgb.shape[:2]
    k = size / max(h, w)
    im = cv2.resize(rgb, (max(1, int(round(w * k))), max(1, int(round(h * k)))), interpolation=cv2.INTER_AREA)
    out = np.full((size, size, 3), 24, np.uint8)
    y, x = (size - im.shape[0]) // 2, (size - im.shape[1]) // 2
    out[y:y + im.shape[0], x:x + im.shape[1]] = im
    return out


def say(prj, lines: dict, by: str = "claude") -> dict:
    """Lines for moments: {moment: {"what": words, "size": wide|medium|close|detail, "where": words, "tags": [..]}};
    a user's line is never replaced by Claude's. -> {"kept": [...], "refused": {moment: why}}."""
    cat = load(prj)
    if not cat:
        raise SystemExit("no catalogue yet - tools\\catalogue.py make <project> first")
    by_id = {mo["m"]: mo for _, mo in moments(cat)}
    kept, refused = [], {}
    for m, ln in (lines or {}).items():
        mo = by_id.get(str(m))
        if mo is None:
            refused[m] = "no such moment"
            continue
        if not isinstance(ln, dict) or not str(ln.get("what") or "").strip():
            refused[m] = "a line needs its words (what the moment shows)"
            continue
        if ln.get("size") and ln["size"] not in SIZES:
            refused[m] = f"size: one of {', '.join(SIZES)}"
            continue
        if by != "user" and (mo.get("say") or {}).get("by") == "user":
            refused[m] = "the user's own line stays"
            continue
        mo["say"] = {"what": " ".join(str(ln["what"]).split())[:200], "size": ln.get("size") or "",
                     "where": " ".join(str(ln.get("where") or "").split())[:80],
                     "tags": [str(t).strip().lower()[:24] for t in (ln.get("tags") or []) if str(t).strip()][:8], "by": by}
        kept.append(m)
    prj.check(_rel(prj)).write_text(json.dumps(cat, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"kept": kept, "refused": refused, "left": sum(1 for _, mo in moments(cat) if not mo.get("say"))}


def text(cat: dict, limit: int = 400) -> str:
    """The catalogue in words, by the day filmed - a line per moment: frames + timecodes, motion, light, its line when
    it has one, the usable part, what to leave out, the moments it looks like."""
    L = []
    n = 0
    by_day: dict[str, list] = {}
    alike: dict[int, list[str]] = {}
    for c, mo in moments(cat):
        if mo.get("group"):
            alike.setdefault(mo["group"], []).append(mo["m"])
    for c in cat.get("clips", []):
        by_day.setdefault((c.get("filmed") or "")[:10] or "?", []).append(c)
    for day in sorted(by_day):
        L.append(f"Filmed {day}:" if day != "?" else "Date unknown:")
        for c in sorted(by_day[day], key=lambda c: c.get("filmed") or ""):
            L.append(f"  {c['id']} = {c['name']}: {c['orientation']}, {c['seconds']} s, {len(c['moments'])} moment(s)")
            for mo in c["moments"]:
                n += 1
                if n > limit:
                    L.append("  ... (more in build\\clips.json)")
                    return "\n".join(L)
                s = mo.get("say") or {}
                said = (f"{s['size'] + ' · ' if s.get('size') else ''}{s['what']}"
                        + (f" [{', '.join(s['tags'])}]" if s.get("tags") else "")) if s else "no line yet"
                use = ", ".join(f"f{u0}-f{u1}" for u0, u1 in mo["usable"][:3]) or "none"
                out = ", ".join(f"f{b0}-f{b1} {w}" for b0, b1, w in mo["bad"][:3])
                like = [m for m in alike.get(mo.get("group"), []) if m != mo["m"]]
                L.append(f"    {mo['m']} f{mo['a']}-f{mo['b']} ({frame_to_tc(mo['a'], c['fps'])}-"
                         f"{frame_to_tc(mo['b'], c['fps'])}) {mo['motion']}, {mo['light']}: {said} | use {use}"
                         + (f" | out {out}" if out else "") + (f" | like {', '.join(like[:4])}" if like else ""))
    return "\n".join(L)


# ------------------------------------------------------------------------------------------------ a plan's shots
def _moment_at(c: dict, i: int) -> dict | None:
    return next((mo for mo in c["moments"] if mo["a"] <= i <= mo["b"]), None)


def shots(prj, plan: dict, name: str = "plan") -> tuple[list[Path], list[str], list[dict]]:
    """A plan's shots BEFORE any render (0.6.1 steps 3 and 7): each one as it will look - its clip's light frame at
    the shot's middle, cropped, zoomed and centred like the plan says - on sheets with frame + timecode, a line per
    shot with what it shows (the catalogue's line), and what is wrong with it: outside its clip's usable parts, across
    a cut inside its clip, like the shot before, a moment used twice, its subject cut off by the crop.
    -> (sheets, lines, issues)."""
    import sys
    from .compose import Curve, sample_patch
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from storyboard import make_sheets
    cat = load(prj) or {"clips": []}
    by = {c["id"]: c for c in cat["clips"]}
    W, H, fps = int(plan["width"]), int(plan["height"]), float(plan["fps"])
    tw = 160 if H > W else 240
    th = int(round(tw * H / W))
    lut = np.arange(256, dtype=np.float32) / 255.0
    named = plan.get("curves") or {}
    layers = sorted((L for L in plan.get("layers", []) if L.get("type") == "clip" and L.get("src")
                     and not L.get("tr") and not str(L.get("id", "")).startswith("rgb_")), key=lambda L: L["start"])
    tiles, lines, issues, cache, prev_grp, seen = [], [], [], {}, None, {}
    takes = ({L["src"] for L in layers if not str(L.get("id", "")).startswith("broll_")}    # a talking video's takes:
             if (plan.get("made_by") or {}).get("sound") == "talk" else set())          # in the order said, by design
    for k, L in enumerate(layers, 1):
        s, e = int(L["start"]), int(L["end"])
        f = (s + e) // 2
        sp = float(L.get("speed", 1.0))
        jumps = sorted([[int(x), int(y)] for x, y in L.get("jumps", [[s, L.get("in", 0)]])])
        j = max((jj for jj in jumps if jj[0] <= f), default=jumps[0])
        src_at = (lambda g: j[1] if L.get("hold") else j[1] + int(np.floor((g - j[0]) * sp + 1e-6)))
        i_mid, i0, i1 = src_at(f), src_at(s), src_at(e)
        c = by.get(L["src"])
        sid = L["src"]
        if sid not in cache:
            try:
                cache[sid] = _light(prj.cache, sid)
            except (OSError, ValueError):
                cache[sid] = None
        img = np.zeros((th, tw, 3), np.uint8)
        if cache[sid]:
            lm, la = cache[sid]
            rgb = FC.decode(la[min(max(i_mid, 0), la.shape[0] - 1)], "i420")
            z = Curve(L.get("zoom"), named, 1.0)(f)
            an = L.get("anchor") or [0.5, 0.5]
            ax, ay = Curve(an[0], named, 0.5)(f), Curve(an[1], named, 0.5)(f)
            r = L.get("rect") or [0, 0, W, H]
            k_ = tw / W
            res = sample_patch(rgb, lut, r[0] * k_, r[1] * k_, r[2] * k_, r[3] * k_, max(1.0, z), ax, ay, tw, th,
                               bool(L.get("mirror")))
            if res is not None:
                patch, cov, X0, Y0 = res
                img[Y0:Y0 + patch.shape[0], X0:X0 + patch.shape[1]] = np.clip(patch * 255 * cov[..., None], 0, 255)
        mo = _moment_at(c, i_mid) if c else None
        tc = f"f{s} ({frame_to_tc(s, fps)}) - f{e} ({frame_to_tc(e, fps)})"
        what = ((mo.get("say") or {}).get("what") or "no line yet") if mo else "not in the catalogue"
        bad = []
        if c and mo:
            if sid in takes:                          # (a take's jump cuts: the same take again, on purpose)
                what += " (the talking take)"
            else:
                n_out = sum(1 for i in range(max(0, i0), i1 + 1) if not any(u0 <= i <= u1 for u0, u1 in mo["usable"]))
                if n_out > 0.2 * max(1, i1 - i0 + 1):
                    why = sorted({w for b0, b1, w in mo["bad"] if b0 <= i1 and i0 <= b1}) or ["not in a usable part"]
                    bad.append(f"{n_out} of its frames outside the usable part ({', '.join(why)})")
                m1 = _moment_at(c, i1)
                if m1 is not None and m1["m"] != mo["m"]:
                    bad.append(f"crosses a cut inside its clip ({mo['m']} -> {m1['m']})")
                if mo.get("group") and mo.get("group") == prev_grp:
                    bad.append("looks like the shot before")
                if mo["m"] in seen:
                    bad.append(f"{mo['m']} again (shot {seen[mo['m']]})")
            sj = mo.get("subject")
            w0, h0 = (c.get("size") or [0, 0])
            if sj and w0 and h0 and abs(w0 / h0 - r_aspect(L, W, H)) > 0.1:
                vis = max(1.0, Curve(L.get("zoom"), named, 1.0)(f))
                frac = min(1.0, r_aspect(L, W, H) / (w0 / h0)) / vis if w0 / h0 > r_aspect(L, W, H) else 1.0 / vis
                an = L.get("anchor") or [0.5, 0.5]
                cx = min(max(Curve(an[0], named, 0.5)(f), frac / 2), 1 - frac / 2)
                if abs(sj["x"] - cx) > frac / 2 * 0.9:
                    bad.append(f"its subject ({sj['by']}) is cut off by the crop")
            seen.setdefault(mo["m"], k)
            prev_grp = mo.get("group")
        else:
            prev_grp = None
        lines.append(f"{k}. {tc} {sid}{'/' + mo['m'] if mo else ''}: {what}" + (" - " + "; ".join(bad) if bad else ""))
        if bad:
            issues.append({"shot": k, "id": L["id"], "f": s, "moment": mo["m"] if mo else None, "issues": bad})
        tiles.append((img, f"{k} f{s} {frame_to_tc(s, fps)}{' !' if bad else ''}"))
    from . import person as PS                        # 0.6.1: graphics over the face (Vibha's rule: never the face)
    try:
        for g in PS.face_issues(plan, log=lambda *_: None):
            at = f"from f{g['f']} ({frame_to_tc(g['f'], fps)})"
            why = (f"the face cuts into it ({int(g['share'] * 100)} % of the face box) {at} - its words get clipped: move "
                   f"it off the face or make it smaller" if g.get("guard") else
                   f"covers the face ({int(g['share'] * 100)} % of it) {at} - move it, or give it guard / behind")
            lines.append(f"graphic {g['id']}: {why}")
            issues.append({"graphic": g["id"], "f": g["f"], "issues": [why]})
    except (OSError, ValueError, KeyError) as e:
        lines.append(f"(graphics over the face not checked: {e})")
    out = prj.check(prj.build / "catalogue")
    out.mkdir(parents=True, exist_ok=True)
    sheets = make_sheets(tiles, out, f"shots_{name}", f"{name}: the shots before the render (! = something to fix)",
                         8 if H > W else 6, tw, rows=6) if tiles else []
    return sheets, lines, issues


def r_aspect(L: dict, W: int, H: int) -> float:
    r = L.get("rect") or [0, 0, W, H]
    return float(r[2]) / max(1.0, float(r[3]))


# ------------------------------------------------------------------------------------------------ self-check
def selfcheck() -> dict:
    """A made-up clip with known moments: test pattern 2 s, colour bars 1.5 s, black 1 s, the test pattern blurred
    1 s, the colour bars again 1.5 s (filmed 2026-10-20) -> five moments, the black one with no usable window, the
    two colour-bar moments one look-alike group, the date read, Claude's lines kept / refused."""
    import sys
    import tempfile
    import types
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import prep_footage as PF
    from .util import load_config, tool
    t0, lines, ok = time.time(), [], True

    def case(name, cond):
        nonlocal ok
        ok = ok and bool(cond)
        lines.append(f"{'PASS' if cond else 'FAIL'} {name}")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        td = Path(td)
        src = td / "clip.mp4"
        parts = ["testsrc=size=640x360:rate=25:duration=2", "smptebars=size=640x360:rate=25:duration=1.5",
                 "color=c=black:size=640x360:rate=25:duration=1", "testsrc=size=640x360:rate=25:duration=1",
                 "smptebars=size=640x360:rate=25:duration=1.5"]
        args = []
        for p in parts:
            args += ["-f", "lavfi", "-i", p]
        fc = "[3:v]boxblur=8:2[b];[0:v][1:v][2:v][b][4:v]concat=n=5:v=1:a=0[v]"
        subprocess.run([tool("ffmpeg"), "-v", "error", *args, "-filter_complex", fc, "-map", "[v]", "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-metadata", "creation_time=2026-10-20T10:00:00Z", str(src)], check=True)
        build = td / "build"
        prj = types.SimpleNamespace(name="selfcheck", build=build, cache=build / "cache",
                                    manifest_path=build / "sources.json", check=lambda p: p)
        build.mkdir()
        ent = {"path": str(src), "name": src.name, "fingerprint": {"sha256": "x"}}
        prj.manifest_path.write_text(json.dumps({"sources": {"A": ent}}), encoding="utf-8")
        PF.prep_light(prj, "A", ent, 25.0, 640, 360)
        cat = make(prj, load_config(), log=lambda *a: None)
        mo = cat["clips"][0]["moments"]
        starts = [m["a"] for m in mo]
        case(f"five moments where the picture changes (f0, f50, f88, f113, f138): {starts}",
             len(mo) == 5 and all(abs(a - b) <= 1 for a, b in zip(starts, [0, 50, 88, 113, 138])))
        case("the black moment has no usable window (too dark / flat)",
             len(mo) == 5 and not mo[2]["usable"] and {w for *_, w in mo[2]["bad"]} & {"too dark", "flat"})
        case("the colour bars twice = one look-alike group; the test pattern and its blur apart",
             len(mo) == 5 and mo[1].get("group") and mo[1].get("group") == mo[4].get("group")
             and mo[0].get("group") != mo[1].get("group"))
        case("filmed: the file's own date", cat["clips"][0]["filmed"].startswith("2026-10-20"))
        r = say(prj, {"A2": {"what": "colour bars", "size": "wide", "tags": ["test"]}, "A9": {"what": "x"},
                      "A3": {"what": "black", "size": "huge"}})
        case("lines kept for real moments, refused for no such moment / a size not in the list",
             r["kept"] == ["A2"] and set(r["refused"]) == {"A9", "A3"})
        say(prj, {"A4": {"what": "a soft test pattern", "size": "medium"}}, by="user")
        r = say(prj, {"A4": {"what": "something else"}})
        case("the user's own line stays", "A4" in r["refused"])
        cat = make(prj, load_config(), log=lambda *a: None)
        case("lines kept when the catalogue is made again", (cat["clips"][0]["moments"][1].get("say") or {}).get("what") == "colour bars")
        case("the catalogue in words: frame + timecode, its line", "A2 f50-f87 (00:00:02:00-00:00:03:12)" in text(cat)
             and "wide · colour bars [test]" in text(cat))
        plan = {"width": 360, "height": 640, "fps": 25.0, "layers": [
            {"type": "clip", "id": "s01_A", "src": "A", "start": 0, "end": 19, "in": 55, "rect": [0, 0, 360, 640]},
            {"type": "clip", "id": "s02_A", "src": "A", "start": 20, "end": 39, "in": 90, "rect": [0, 0, 360, 640]},
            {"type": "clip", "id": "s03_A", "src": "A", "start": 40, "end": 59, "in": 60, "rect": [0, 0, 360, 640]}]}
        sh, ln, iss = shots(prj, plan, "test")
        found = {x["shot"]: " ".join(x["issues"]) for x in iss}
        case(f"a plan's shots before the render: the black one outside its usable part, the colour bars twice "
             f"({found})", sh and len(ln) == 3 and "outside the usable part" in found.get(2, "")
             and "A2 again" in found.get(3, "") and 1 not in found and "colour bars" in ln[0])
    return {"passed": ok, "seconds": round(time.time() - t0, 2), "lines": lines}
