"""Checks before the final render (0.4.2 item 9): measured on a plain render, a graphic's .mov or a folder of
snapshots, so nothing is guessed. tools\\precheck.py is the command line.

**Vanishing** - a part of the picture that disappears for 1-2 frames and comes back (illdari v1: the logo gone at
f38 (00:00:01:08) between its arcs and its badge). The picture is cut into a GRID x GRID grid; each region =
REGION x REGION neighbouring cells (overlapping), so an element that only moves to the next cell is not a loss.
A region's content = its alpha coverage (a .mov with a real alpha) or its edge energy (mean Sobel magnitude of the
luma after a light blur: flat backgrounds, glows and blurred photos read ~0, drawn things read high). Frame t (and
t+1 for a 2-frame gap) vanishes in a region when its content falls under VANISH_RATIO of BOTH the frame before
and the frame after the gap, and that reference holds enough content (MIN_EDGE / MIN_COVER, and MIN_SHARE of the
clip's busiest region); edge energy counts above the clip's noise floor (its 5th percentile region). The whole
picture is tested the same way ("most of the picture"). A part that drops while the picture turns into another
one (the frames on both sides differ by SCENE_MAD on 32 px thumbnails) is a transition: noted, not flagged.

**Fastest moves** - points on corners are tracked from frame t-1 to t (pyramidal Lucas-Kanade on a WORK px copy,
kept only when tracking back lands within FB_PX of the start; points that jump further than their own size are
tried again from the shifts a phase correlation of the changed parts finds), scaled back to the video's own
pixels. A frame's speed = the fastest move that at least MIN_POINTS points nearby agree on (one stray point is not
a move). Without motion blur a move over MOVE_PX px a frame shows as a jump (lesson M004: give it a smear). With N
motion-blur sub-frames the copies sit speed / N px apart: over STEP_PX (5 sub-frames cover up to 60 px a frame)
the frame is flagged only when the copies are measured (`copies`: the picture correlated with itself along the
move peaks again near the spacing; a smear or a soft picture does not) - else it is noted. Filmed footage (a plan
with "sources") moves with its camera: its fast moves are noted, not flagged.

**Sound** - the report tools\\sfx.py make writes (<name>_sfx.json, per cue: song_db, fx_db, target_db, vs_song_db,
rule, limiter_db): an effect more than LOUD_DB over the song under it, one more than BURIED_DB under it (masked) or
SHORT_DB under its own level (the peak cap stopped it), and the limiter taking LIMIT_DB or more.

Frames are 0-based; every frame in the output has its number + timecode at the input's rate.
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .timecode import frame_to_tc, label as tc_label, range_label
from .util import LAB, tool

WORK = 480              # working copy's long side (px)
GRID, REGION = 8, 3     # 8 x 8 cells, regions of 3 x 3 cells
VANISH_RATIO = 0.35     # content in the gap under 35 % of both neighbours
MIN_EDGE = 1.5          # a region's edge energy (mean Sobel magnitude, 0-255 luma) worth testing
MIN_COVER = 0.02        # ... or its alpha coverage
MIN_SHARE = 0.10        # ... and at least 10 % of the clip's busiest region (p95)
MOVE_PX = 60.0          # px a frame (the video's pixels) that show as a jump without motion blur
STEP_PX = 12.0          # px between motion-blur sub-frames before copies show
MIN_POINTS = 3          # tracked points that must agree on a move
FB_PX = 0.5             # forward-backward tracking error allowed (working px)
COPIES_PEAK, COPIES_RISE = 0.25, 0.4   # copies score: a correlation peak near the sub-frame spacing
SCENE_MAD = 12.0        # a part vanishing between two different pictures (32 px thumbnails differ this much, 0-255)
LOUD_DB, BURIED_DB, SHORT_DB, LIMIT_DB = 6.0, -26.0, 4.0, 3.0
SHEET_ROWS = 12
THREADS = 4

cv2.setNumThreads(THREADS)
LK = dict(winSize=(21, 21), maxLevel=4, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
LK_NEAR = dict(LK, maxLevel=1)       # from a phase-correlation guess: already close, coarse levels only blur it away


# ------------------------------------------------------------------------------------------------ inputs
def ffprobe(path: Path) -> dict:
    r = subprocess.run([tool("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,pix_fmt,r_frame_rate,avg_frame_rate,nb_frames", "-of", "json", str(path)],
                       capture_output=True, text=True)
    s = (json.loads(r.stdout or "{}").get("streams") or [None])[0]
    if not s:
        raise SystemExit(f"no video stream in {path}")

    def frac(v):
        try:
            a, _, b = str(v).partition("/")
            return float(a) / float(b or 1)
        except (ValueError, ZeroDivisionError):
            return 0.0
    fps = frac(s.get("r_frame_rate")) or frac(s.get("avg_frame_rate")) or 30.0
    pf = s.get("pix_fmt", "")
    return {"width": int(s["width"]), "height": int(s["height"]), "fps": fps, "pix_fmt": pf,
            "alpha": bool(re.match(r"(yuva|rgba|bgra|argb|abgr|gbrap|ya|pal8)", pf))}


def work_size(w: int, h: int, long_side: int = WORK) -> tuple[int, int]:
    """The working copy: long side WORK px, but the short side at least 3/4 of it (a 16:9 video keeps 360 rows)."""
    k = min(1.0, max(long_side / max(w, h), 0.75 * long_side / min(w, h)))
    return max(16, int(round(w * k / 2)) * 2), max(16, int(round(h * k / 2)) * 2)


def video_frames(path: Path, w: int, h: int, alpha: bool):
    """(frame number, RGBA uint8 at w x h) for every frame, one sequential ffmpeg decode."""
    cmd = [tool("ffmpeg"), "-v", "error", "-nostdin", "-threads", str(THREADS), "-i", str(path), "-map", "0:v:0",
           "-fps_mode", "passthrough", "-vf", f"scale={w}:{h}:flags=area", "-f", "rawvideo", "-pix_fmt",
           "rgba" if alpha else "rgb24", "-"]
    ch = 4 if alpha else 3
    size = w * h * ch
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=size * 4)
    i = 0
    try:
        while True:
            buf = proc.stdout.read(size)
            if not buf or len(buf) < size:
                break
            yield i, np.frombuffer(buf, np.uint8).reshape(h, w, ch)
            i += 1
    finally:
        proc.stdout.close()
        proc.wait()


FRAME_RE = re.compile(r"_f(\d+)\.png$", re.I)


def folder_frames(folder: Path) -> list[tuple[int, Path]]:
    """The snapshots / stills in a folder: <name>_fNNNN.png (overlay.py snap / stills), else every PNG in name
    order numbered from 0. sheet.png is skipped."""
    pngs = [p for p in sorted(folder.glob("*.png")) if p.name.lower() != "sheet.png"]
    numbered = [(int(m[1]), p) for p in pngs if (m := FRAME_RE.search(p.name))]
    if numbered and len(numbered) == len(pngs):
        return sorted(numbered)
    return list(enumerate(pngs))


CHECKER = (round(0.32 * 255), round(0.22 * 255))     # overlay.py's checker (16 px), under a snapshot's transparency


def png_rgba(path: Path, w: int, h: int, label_box: bool = True) -> np.ndarray:
    """A snapshot as RGBA at w x h: the checker overlay.py draws under transparency becomes alpha 0 again, the
    burned-in frame label (top left) is blanked."""
    im = Image.open(path)
    if im.mode == "RGBA":
        a = np.asarray(im).copy()
    else:
        rgb = np.asarray(im.convert("RGB"))
        H, W = rgb.shape[:2]
        yy, xx = np.mgrid[0:H, 0:W]
        chk = np.where(((yy // 16 + xx // 16) % 2) == 0, CHECKER[0], CHECKER[1]).astype(np.int16)
        bg = (np.abs(rgb.astype(np.int16) - chk[..., None]) <= 2).all(axis=2)
        a = np.dstack([rgb, np.where(bg, 0, 255).astype(np.uint8)])
        if bg.mean() < 0.02:                       # no checker showing: an opaque graphic
            a[..., 3] = 255
    if label_box:
        H, W = a.shape[:2]
        a[:max(1, round(H * 0.04)), :max(1, round(W * 0.5))] = (0, 0, 0, 255)
    return cv2.resize(a, (w, h), interpolation=cv2.INTER_AREA)


# ------------------------------------------------------------------------------------------------ measuring
def _grid_edges(n: int, cells: int) -> np.ndarray:
    return np.linspace(0, n, cells + 1).round().astype(int)


def cell_means(x: np.ndarray, cells: int = GRID) -> np.ndarray:
    """The mean of each of cells x cells cells (area average)."""
    return cv2.resize(x.astype(np.float32), (cells, cells), interpolation=cv2.INTER_AREA)


def regions(c: np.ndarray, k: int = REGION) -> np.ndarray:
    """k x k neighbouring cells summed (overlapping), from a GRID x GRID cell map -> (GRID-k+1)^2."""
    b = cv2.blur(c.astype(np.float32), (k, k), anchor=(0, 0), borderType=cv2.BORDER_CONSTANT)
    n = c.shape[0] - k + 1
    return np.ascontiguousarray(b[:n, :n])


LUMA = np.array([[0.2126, 0.7152, 0.0722]], np.float32)     # BT.709


def gray_of(rgba: np.ndarray) -> np.ndarray:
    """Luma (float32, 0-255) of an RGB or RGBA frame; RGBA = premultiplied by its alpha (transparent = black)."""
    lum = cv2.transform(np.ascontiguousarray(rgba[..., :3]).astype(np.float32), LUMA)
    lum = lum.reshape(rgba.shape[:2])
    if rgba.shape[2] == 4:
        lum *= rgba[..., 3].astype(np.float32) * (1 / 255.0)
    return lum


def as_rgba(a: np.ndarray) -> np.ndarray:
    return a if a.shape[2] == 4 else np.dstack([a, np.full(a.shape[:2], 255, np.uint8)])


def edge_energy(g: np.ndarray) -> np.ndarray:
    b = cv2.GaussianBlur(g, (3, 3), 0.8)
    gx = cv2.Sobel(b, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(b, cv2.CV_32F, 0, 1, ksize=3)
    # Sobel's 3x3 gain: a 0->255 step reads ~255 / 4 * 2 at its edge; np.sqrt, not cv2.magnitude (whose last bit
    # moves with the buffer's memory address)
    return np.sqrt(gx * gx + gy * gy) / 4.0


def shift_candidates(g0: np.ndarray, g1: np.ndarray, k: int = 4) -> list[tuple[float, float]]:
    """Big moves Lucas-Kanade alone can miss (an element jumping further than its own size): phase correlation of
    only the parts that changed (the static rest masked out) -> up to k shifts (dx, dy) in working px."""
    a, b = g0.astype(np.float32), g1.astype(np.float32)
    ch = cv2.GaussianBlur(np.abs(b - a), (5, 5), 0) > 6
    if ch.mean() < 0.0005:
        return []
    m = cv2.dilate(ch.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(np.float32)
    h, w = a.shape
    win = np.outer(np.hanning(h), np.hanning(w)).astype(np.float32)
    A, B = (a - a[m > 0].mean()) * m * win, (b - b[m > 0].mean()) * m * win
    FA, FB = np.fft.rfft2(A), np.fft.rfft2(B)
    R = FB * np.conj(FA)
    R /= np.abs(R) + 1e-6
    r = np.fft.fftshift(np.fft.irfft2(R, s=(h, w)))
    r = cv2.GaussianBlur(r.astype(np.float32), (3, 3), 0)
    peaks = (r == cv2.dilate(r, np.ones((7, 7), np.uint8))) & (r > 0.25 * float(r.max()))
    ys, xs = np.nonzero(peaks)
    order = np.argsort(-r[ys, xs])[:k]
    return [(float(xs[i] - w // 2), float(ys[i] - h // 2)) for i in order
            if abs(xs[i] - w // 2) + abs(ys[i] - h // 2) > 2]


def _ncc(g0: np.ndarray, g1: np.ndarray, p0: np.ndarray, p1: np.ndarray, r: int = 6) -> np.ndarray:
    out = np.zeros(len(p0), np.float32)
    size = (2 * r + 1, 2 * r + 1)
    for i, (a, b) in enumerate(zip(p0, p1)):
        x = cv2.getRectSubPix(g0, size, (float(a[0]), float(a[1]))).astype(np.float32).ravel()
        y = cv2.getRectSubPix(g1, size, (float(b[0]), float(b[1]))).astype(np.float32).ravel()
        x -= x.mean()
        y -= y.mean()
        den = math.sqrt(float(x @ x) * float(y @ y))
        out[i] = float(x @ y) / den if den > 1e-3 else 0.0
    return out


def track(g0: np.ndarray, g1: np.ndarray, mask: np.ndarray | None = None):
    """Corners of g0 tracked into g1 (uint8): (start points N x 2, displacement N x 2), forward-backward checked.
    Points that do not track from a standing start are tried again from each phase-correlation shift (and then
    must also look the same: patch correlation over 0.8)."""
    p0 = cv2.goodFeaturesToTrack(g0, maxCorners=500, qualityLevel=0.01, minDistance=5, blockSize=7, mask=mask)
    if p0 is None or len(p0) == 0:
        return np.zeros((0, 2), np.float32), np.zeros((0, 2), np.float32)
    p0 = p0.reshape(-1, 1, 2).astype(np.float32)

    def lk(init=None):
        if init is None:
            p1, st, _ = cv2.calcOpticalFlowPyrLK(g0, g1, p0, None, **LK)
        else:
            p1 = (p0 + np.float32(init)).astype(np.float32)
            p1, st, _ = cv2.calcOpticalFlowPyrLK(g0, g1, p0, p1, flags=cv2.OPTFLOW_USE_INITIAL_FLOW, **LK_NEAR)
        pb, st2, _ = cv2.calcOpticalFlowPyrLK(g1, g0, p1, p0.copy(), flags=cv2.OPTFLOW_USE_INITIAL_FLOW,
                                              **(LK if init is None else LK_NEAR))
        fb = np.linalg.norm((pb - p0).reshape(-1, 2), axis=1)
        return p1.reshape(-1, 2), (st.ravel() == 1) & (st2.ravel() == 1) & (fb < FB_PX)

    P1, ok = lk()
    for c in shift_candidates(g0, g1):
        if ok.all():
            break
        q1, okc = lk(c)
        new = okc & ~ok
        if new.any():
            idx = np.flatnonzero(new)
            good = _ncc(g0, g1, p0.reshape(-1, 2)[idx], q1[idx]) > 0.8
            idx = idx[good]
            P1[idx], ok[idx] = q1[idx], True
    q0 = p0.reshape(-1, 2)[ok]
    return q0, P1[ok] - q0


def fastest(p: np.ndarray, d: np.ndarray, radius: float) -> tuple[float, float, float, float, float, int]:
    """The fastest move MIN_POINTS points within radius agree on (displacement within 20 % / 1.5 px):
    (speed, x, y, dx, dy, points) in working px, x / y = where it starts. (0, ...) when none."""
    if len(p) < MIN_POINTS:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0
    sp = np.linalg.norm(d, axis=1)
    for i in np.argsort(-sp):
        if sp[i] < 0.5:
            break
        tol = max(1.5, 0.2 * sp[i])
        near = (np.linalg.norm(p - p[i], axis=1) < radius) & (np.linalg.norm(d - d[i], axis=1) < tol)
        if near.sum() >= MIN_POINTS:
            q, dd = p[near], d[near]
            return float(np.median(sp[near])), float(np.median(q[:, 0])), float(np.median(q[:, 1])), \
                float(np.median(dd[:, 0])), float(np.median(dd[:, 1])), int(near.sum())
    return 0.0, 0.0, 0.0, 0.0, 0.0, 0


def _profile(g: np.ndarray, x: float, y: float, dx: float, dy: float, n: int) -> list[float] | None:
    """The derivative of g along the move (x, y) -> (x + dx, y + dy), correlated with itself shifted 1 .. n px
    along the move, over the box the move crosses (working px)."""
    d = math.hypot(dx, dy)
    if d < 1:
        return None
    ux, uy = dx / d, dy / d
    cx, cy, R = x + dx / 2, y + dy / 2, d / 2 + 16
    h, w = g.shape
    x0, x1, y0, y1 = int(max(0, cx - R)), int(min(w, cx + R)), int(max(0, cy - R)), int(min(h, cy + R))
    if x1 - x0 < 8 or y1 - y0 < 8:
        return None
    gf = g.astype(np.float32)
    D = cv2.Sobel(gf, cv2.CV_32F, 1, 0) * ux + cv2.Sobel(gf, cv2.CV_32F, 0, 1) * uy
    a = D[y0:y1, x0:x1].ravel()
    na = float(a @ a)
    if na < 1e-3:
        return None
    cs = []
    for L in range(1, n + 1):
        S = cv2.warpAffine(D, np.float32([[1, 0, ux * L], [0, 1, uy * L]]), (w, h), flags=cv2.INTER_LINEAR)
        b = S[y0:y1, x0:x1].ravel()
        cs.append(float(a @ b) / (math.sqrt(na * float(b @ b)) + 1e-6))
    return cs


def copies(g: np.ndarray, x: float, y: float, dx: float, dy: float, spacing: float) -> float:
    """Copies of a moving element seen in frame g (working px). A smear or a soft picture decays smoothly along
    the move; separate sub-frame copies come back as a peak near their spacing. Returns the peak's rise over the
    dip before it (>= COPIES_RISE with a peak >= COPIES_PEAK = copies), 0 when it never rises. x, y = where the
    move starts."""
    if spacing < 1.5:
        return 0.0
    cs = _profile(g, x, y, dx, dy, max(3, int(2.2 * spacing)))
    if not cs:
        return 0.0
    best = 0.0
    for i in range(1, len(cs) - 1):
        L = i + 1
        if L < max(3, 0.5 * spacing) or not (cs[i] >= cs[i - 1] and cs[i] >= cs[i + 1]) or cs[i] < COPIES_PEAK:
            continue
        best = max(best, cs[i] - min(cs[:i]))
    return round(best, 3)


def measure(frames, scale: float, size: tuple[int, int], motion_blur: int = 0, workers: int = THREADS) -> dict:
    """frames = iterable of (frame number, RGBA at the working size); scale = video px per working px.
    Per frame: region content (edge energy, alpha coverage), the whole frame's, a 32 px thumbnail, and the
    fastest tracked move from the frame before (only when the frame before is its number - 1); with motion blur,
    a move over the sub-frame limit also gets its copies score."""
    w, h = size
    nums, edge_r, edge_t, cov_r, cov_t, moves, thumbs, edge_c, cov_c = [], [], [], [], [], [], [], [], []
    mb = max(0, int(motion_blur or 0))
    test_px = STEP_PX * mb / scale if mb > 1 else None

    def task(a, b):
        r = fastest(*track(a, b), radius)
        if test_px is None or r[0] <= test_px:
            return r + (np.nan, np.nan)
        # copies in this frame, and in the frame before along the same move (a jump from rest: the frame before
        # blends its copies over the sharp start and tracks badly, so it is tested with this frame's move)
        return r + (copies(b, r[1], r[2], r[3], r[4], r[0] / mb),
                    copies(a, r[1] - r[3], r[2] - r[4], r[3], r[4], r[0] / mb))
    prev = None
    radius = 0.15 * max(w, h)
    from concurrent.futures import ThreadPoolExecutor
    pool = ThreadPoolExecutor(max(1, workers))
    futs = []
    for n, rgba in frames:
        g = gray_of(rgba)
        e = edge_energy(g)
        ce = cell_means(e)
        if rgba.shape[2] == 4:
            al = rgba[..., 3].astype(np.float32) * (1 / 255.0)
            ca, at = cell_means(al), float(al.mean())
        else:
            ca, at = np.ones((GRID, GRID), np.float32), 1.0
        nums.append(n)
        edge_c.append(ce)
        cov_c.append(ca)
        thumbs.append(cv2.resize(g, (32, 32), interpolation=cv2.INTER_AREA))
        edge_r.append(regions(ce))
        edge_t.append(float(e.mean()))
        cov_r.append(regions(ca))
        cov_t.append(at)
        g8 = g.astype(np.uint8)
        if prev is not None and prev[0] == n - 1:
            futs.append(pool.submit(task, prev[1], g8))
        else:
            futs.append(None)
        prev = (n, g8)
    for f in futs:
        moves.append(f.result() if f is not None else None)
    pool.shutdown()
    mv = np.array([m if m is not None else (np.nan,) * 8 for m in moves], np.float64).reshape(-1, 8)
    mv[:, :5] *= scale
    return {"frames": np.array(nums, int), "edge_r": np.array(edge_r), "edge_t": np.array(edge_t),
            "cov_r": np.array(cov_r), "cov_t": np.array(cov_t), "edge_c": np.array(edge_c),
            "cov_c": np.array(cov_c), "thumbs": np.array(thumbs), "moves": mv, "scale": scale, "size": size,
            "motion_blur": mb}


# ------------------------------------------------------------------------------------------------ checks
def _region_box(i: int, j: int, size: tuple[int, int], scale: float) -> list[int]:
    w, h = size
    ys, xs = _grid_edges(h, GRID), _grid_edges(w, GRID)
    return [int(xs[j] * scale), int(ys[i] * scale), int(xs[j + REGION] * scale), int(ys[i + REGION] * scale)]


def _cell_box(cells: np.ndarray, size: tuple[int, int], scale: float) -> list[int] | None:
    if not cells.any():
        return None
    w, h = size
    ys, xs = _grid_edges(h, GRID), _grid_edges(w, GRID)
    ii, jj = np.nonzero(cells)
    return [int(xs[jj.min()] * scale), int(ys[ii.min()] * scale), int(xs[jj.max() + 1] * scale),
            int(ys[ii.max() + 1] * scale)]


def vanish_flags(m: dict, use_alpha: bool | None = None) -> tuple[list[dict], str, list[dict]]:
    """Gaps of 1-2 frames where a region's (or the whole picture's) content drops under VANISH_RATIO of the frames
    on both sides. use_alpha None = alpha when the clip has real transparency. A part that drops while the picture
    changes into another one (the frames on both sides differ by SCENE_MAD) is a transition, not a gap: it goes
    into the notes. Returns (flags, basis, notes)."""
    nums = m["frames"]
    if use_alpha is None:
        use_alpha = bool(len(nums)) and float(np.min(m["cov_t"])) < 0.97
    basis = "alpha" if use_alpha else "edges"
    R, T, C = (m["cov_r"], m["cov_t"], m["cov_c"]) if use_alpha else (m["edge_r"], m["edge_t"], m["edge_c"])
    floor = MIN_COVER if use_alpha else MIN_EDGE
    if not len(nums):
        return [], basis, []
    if not use_alpha:       # the clip's noise / grain floor (its quietest regions) is not content
        nf = float(np.percentile(R, 5))
        R, C, T = np.maximum(R - nf, 0), np.maximum(C - nf, 0), np.maximum(T - nf, 0)
    rmin = max(floor, MIN_SHARE * float(np.percentile(R, 95)))
    tmin = max(floor * 0.25, MIN_SHARE * float(np.percentile(T, 95)))
    pos = {int(n): k for k, n in enumerate(nums)}
    out, notes, taken = [], [], set()
    for L in (1, 2):
        for n in nums:
            n = int(n)
            a, b = pos.get(n - 1), pos.get(n + L)
            gap = [pos.get(n + q) for q in range(L)]
            if a is None or b is None or None in gap or any(n + q in taken for q in range(L)):
                continue
            ref_r = np.minimum(R[a], R[b])
            dur_r = np.max(np.stack([R[g] for g in gap]), axis=0)
            hit = (ref_r >= rmin) & (dur_r < VANISH_RATIO * ref_r)
            ref_t, dur_t = min(T[a], T[b]), max(T[g] for g in gap)
            whole = bool(ref_t >= tmin and dur_t < VANISH_RATIO * ref_t)
            if not hit.any() and not whole:
                continue
            mad = float(np.abs(m["thumbs"][a] - m["thumbs"][b]).mean())
            # the cells that lost their content, inside the regions that did
            inside = np.zeros(C[a].shape, bool)
            for i, j in np.argwhere(hit):
                inside[i:i + REGION, j:j + REGION] = True
            ref_c = np.minimum(C[a], C[b])
            dur_c = np.max(np.stack([C[g] for g in gap]), axis=0)
            cells = inside & (ref_c >= rmin) & (dur_c < VANISH_RATIO * ref_c)
            if not cells.any():
                cells = inside
            box = _cell_box(cells, m["size"], m["scale"])
            lost = float(1 - dur_t / ref_t) if ref_t > 0 else 0.0
            worst = float((dur_r[hit] / np.maximum(ref_r[hit], 1e-6)).min()) if hit.any() else None
            span = f"for {L} frame{'s' if L > 1 else ''} and comes back"
            rec = {"check": "vanish", "frames": [n, n + L - 1], "before": n - 1, "after": n + L, "whole": whole,
                   "box": box, "regions": int(hit.sum()), "content_left": round(1 - lost, 3),
                   "region_left": None if worst is None else round(worst, 3), "before_after_diff": round(mad, 1)}
            if not whole and mad > SCENE_MAD:
                rec["reason"] = (f"a part drops {span}, but the picture changes into another one around it "
                                 f"(before / after differ {mad:.0f} of 255): a transition")
                notes.append(rec)
                continue
            if whole:
                rec["reason"] = (f"most of the picture vanishes {span} ({round(100 * lost)} % of the content gone"
                                 + (", between two different pictures: a dip or a black frame?" if mad > SCENE_MAD
                                    else "") + ")")
            else:
                gone = round(100 * (1 - (worst or 0)))
                rec["reason"] = f"a part of the picture vanishes {span} ({gone} % of it gone)"
            out.append(rec)
            taken.update(n + q for q in range(L))
    out.sort(key=lambda f: f["frames"][0])
    notes.sort(key=lambda f: f["frames"][0])
    return out, basis, notes


def move_flags(m: dict, motion_blur: int = 0, footage: bool = False) -> tuple[list[dict], list[dict]]:
    """Runs of frames whose fastest move is over MOVE_PX (no motion blur), or whose motion-blur sub-frames sit
    over STEP_PX apart AND show as copies (the copies score; a smear or a soft picture hides them - those go into
    the notes). Returns (flags, notes)."""
    nums, mv = m["frames"], m["moves"]
    mb = max(0, int(motion_blur or 0))
    limit = MOVE_PX if mb <= 1 else STEP_PX * mb
    fast = [(int(n), mv[k]) for k, n in enumerate(nums) if np.isfinite(mv[k, 0]) and mv[k, 0] > limit]
    if mb > 1:      # the frame before a run, when its copies show along the run's first move
        have = {n for n, _ in fast}
        for n, v in list(fast):
            if n - 1 not in have and np.isfinite(v[7]) and v[7] >= COPIES_RISE:
                w = v.copy()
                w[1], w[2], w[6] = v[1] - v[3], v[2] - v[4], v[7]
                fast.append((n - 1, w))
                have.add(n - 1)
        fast.sort(key=lambda x: x[0])

    FW, FH = m["size"][0] * m["scale"], m["size"][1] * m["scale"]

    def cx(x):
        return int(min(max(x, 0), FW - 1))

    def cy(y):
        return int(min(max(y, 0), FH - 1))

    def item(n, v):
        d = {"frame": n, "label": None, "px": round(float(v[0]), 1), "at": [cx(v[1]), cy(v[2])],
             "to": [cx(v[1] + v[3]), cy(v[2] + v[4])], "points": int(v[5])}
        if mb > 1:
            d["copies"] = None if not np.isfinite(v[6]) else round(float(v[6]), 2)
        return d
    notes = []
    if mb <= 1 and footage:      # filmed footage: its moves are the camera's (and its own motion blur), listed only
        for n, v in fast:
            it = item(n, v)
            it["reason"] = f"moves {v[0]:.0f} px a frame - filmed footage: the camera's own move, not flagged"
            notes.append(it)
        fast = []
    if mb > 1:
        keep = []
        for n, v in fast:
            if not np.isfinite(v[6]) or v[6] >= COPIES_RISE:      # not measured (another motion blur): kept
                keep.append((n, v))
            else:
                it = item(n, v)
                it["reason"] = (f"moves {v[0]:.0f} px a frame ({mb} sub-frames {v[0] / mb:.0f} px apart) but no "
                                "copies show: smeared or soft")
                notes.append(it)
        fast = keep
    runs, cur = [], []
    for n, v in fast:
        if cur and n != cur[-1][0] + 1:
            runs.append(cur)
            cur = []
        cur.append((n, v))
    if cur:
        runs.append(cur)
    out = []
    for r in runs:
        top = max(r, key=lambda x: x[1][0])
        sp = float(top[1][0])
        per = [item(n, v) for n, v in r]
        if mb <= 1:
            why = (f"moves {sp:.0f} px a frame (over {MOVE_PX:.0f}) with no motion blur: it jumps - a smear or "
                   f"motion blur ({math.ceil(sp / STEP_PX)} sub-frames)")
        else:
            why = (f"moves {sp:.0f} px a frame: its {mb} motion-blur sub-frames show as copies {sp / mb:.0f} px "
                   f"apart (over {STEP_PX:.0f}) - {math.ceil(sp / STEP_PX)} sub-frames or a smear")
        out.append({"check": "move", "frames": [r[0][0], r[-1][0]], "fastest": top[0], "px": round(sp, 1),
                    "at": [cx(top[1][1]), cy(top[1][2])], "motion_blur": mb, "limit_px": limit,
                    "per_frame": per, "reason": why})
    return out, notes


def sound_flags(rep: dict) -> list[dict]:
    """An sfx.py report (<name>_sfx.json): effects too loud / buried against the song, the limiter working hard."""
    fps = float(rep.get("fps") or 30.0)
    out = []
    for r in rep.get("cues") or rep.get("rows") or []:
        if r.get("skipped") or r.get("fx_db") is None:
            continue
        f = int(r["f"])
        what = f"{r.get('kind', '?')} '{r.get('what', '')}'"
        vs = r.get("vs_song_db")
        if vs is not None and vs > LOUD_DB:
            out.append({"check": "sound", "kind": "loud", "frames": [f, f], "db": vs,
                        "reason": f"{what} sits {vs:+.1f} dB over the song under it (over {LOUD_DB:+.0f})"})
        elif vs is not None and vs < BURIED_DB:
            out.append({"check": "sound", "kind": "buried", "frames": [f, f], "db": vs,
                        "reason": f"{what} sits {vs:+.1f} dB under the song: masked (under {BURIED_DB:+.0f})"})
        elif r.get("target_db") is not None and r["target_db"] - r["fx_db"] >= SHORT_DB:
            short = r["target_db"] - r["fx_db"]
            out.append({"check": "sound", "kind": "buried", "frames": [f, f], "db": round(-short, 2),
                        "reason": f"{what} is {short:.1f} dB under its own level ({r.get('rule', '')}: its peak "
                                  f"stops it), {vs:+.1f} dB vs the song" if vs is not None else
                                  f"{what} is {short:.1f} dB under its own level ({r.get('rule', '')})"})
        lim = r.get("limiter_db")
        if lim is not None and lim <= -LIMIT_DB:
            out.append({"check": "sound", "kind": "limiter", "frames": [f, f], "db": lim,
                        "reason": f"the limiter takes {-lim:.1f} dB at {what} (over {LIMIT_DB:.0f} dB: the mix "
                                  "pumps there)"})
    lmax = rep.get("limiter_max_db")
    if lmax is not None and lmax <= -LIMIT_DB and not any(x["kind"] == "limiter" for x in out):
        runs = rep.get("limiter_frames") or [[0, 0]]
        a, b = runs[0]
        out.append({"check": "sound", "kind": "limiter", "frames": [int(a), int(b)], "db": lmax,
                    "reason": f"the limiter takes up to {-lmax:.1f} dB in the mix (over {LIMIT_DB:.0f} dB)"})
    for x in out:
        x["label"] = range_label(x["frames"][0], x["frames"][1], fps)
    out.sort(key=lambda x: x["frames"][0])
    return out


# ------------------------------------------------------------------------------------------------ sheet
def _font(size: int, bold: bool = False):
    import os
    d = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    for n in (["consolab.ttf", "consola.ttf"] if bold else ["consola.ttf", "cour.ttf"]):
        try:
            return ImageFont.truetype(str(d / n), size)
        except OSError:
            pass
    return ImageFont.load_default()


def _on_grey(rgba: np.ndarray) -> Image.Image:
    a = rgba[..., 3:4].astype(np.float32) / 255.0
    H, W = rgba.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    chk = np.where(((yy // 8 + xx // 8) % 2) == 0, 82, 56).astype(np.float32)[..., None]
    return Image.fromarray((rgba[..., :3] * a + chk * (1 - a)).astype(np.uint8))


def sheet_frames(flags: list[dict]) -> list[list[int]]:
    rows = []
    for f in flags:
        if f["check"] == "vanish":
            rows.append([f["before"]] + list(range(f["frames"][0], f["frames"][1] + 1)) + [f["after"]])
        elif f["check"] == "move":
            per = sorted(f["per_frame"], key=lambda p: -p["px"])[:3]
            fr = sorted(p["frame"] for p in per)
            rows.append([fr[0] - 1] + fr)
    return rows


def draw_sheet(path: Path, title: str, flags: list[dict], tiles: dict, fps: float, scale_tile: float,
               status: str) -> None:
    """One row per flag (the frames around it, each labelled with frame + timecode; a box where something vanished,
    an arrow on the fastest move), the reason under it; sound flags as lines at the end."""
    F, Fb, Fs = _font(14), _font(16, True), _font(13)
    vis = [f for f in flags if f["check"] in ("vanish", "move")][:SHEET_ROWS]
    snd = [f for f in flags if f["check"] == "sound"]
    tw = th = 0
    for im in tiles.values():
        th, tw = im.shape[:2]
        break
    rows = sheet_frames(vis)
    cols = max([len(r) for r in rows] + [1])
    pad, cap = 8, 46
    W = max(760, pad + cols * (tw + pad))
    H = 40 + len(rows) * (th + cap + pad + 4) + (22 * (len(snd) + 1) if snd else 0) + 30
    page = Image.new("RGB", (W, H), (18, 18, 18))
    d = ImageDraw.Draw(page)
    d.text((pad, 10), f"{title}   {status}", fill=(255, 196, 0) if status != "PASS" else (120, 220, 120), font=Fb)
    y = 40
    for f, fr in zip(vis, rows):
        for c, n in enumerate(fr):
            im = tiles.get(n)
            x = pad + c * (tw + pad)
            if im is None:
                continue
            t = _on_grey(im)
            td = ImageDraw.Draw(t)
            hot = f["frames"][0] <= n <= f["frames"][1]
            if f["check"] == "vanish" and f.get("box") and n == f["before"]:
                b = [v / scale_tile for v in f["box"]]
                td.rectangle(b, outline=(255, 64, 64), width=2)
            if f["check"] == "move" and hot:
                p = next((q for q in f["per_frame"] if q["frame"] == n), None)
                if p:
                    x0, y0 = p["at"][0] / scale_tile, p["at"][1] / scale_tile
                    x1, y1 = p["to"][0] / scale_tile, p["to"][1] / scale_tile
                    td.line([x0, y0, x1, y1], fill=(255, 64, 64), width=3)
                    td.ellipse([x1 - 4, y1 - 4, x1 + 4, y1 + 4], fill=(255, 64, 64))
                    td.text((x1 + 6, y1 - 8), f"{p['px']:.0f} px", fill=(255, 255, 255), font=Fs,
                            stroke_width=2, stroke_fill=(0, 0, 0))
            txt = tc_label(n, fps)
            bb = td.textbbox((6, 5), txt, font=F)
            td.rectangle((bb[0] - 3, bb[1] - 2, bb[2] + 3, bb[3] + 2), fill=(0, 0, 0))
            td.text((6, 5), txt, fill=(255, 196, 0) if hot else (200, 200, 200), font=F)
            page.paste(t, (x, y))
            if hot:
                d.rectangle((x - 2, y - 2, x + tw + 1, y + th + 1), outline=(255, 64, 64), width=2)
        import textwrap
        per_line = max(40, int((W - 2 * pad) / 8.4))
        lines = textwrap.wrap(f"{f['label']}  {f['check']}: {f['reason']}", per_line)[:2]
        for q, line in enumerate(lines):
            d.text((pad, y + th + 5 + 18 * q), line, fill=(235, 235, 235), font=F)
        y += th + cap + pad + 4
    more = len([f for f in flags if f["check"] in ("vanish", "move")]) - len(vis)
    if more > 0:
        d.text((pad, y), f"+ {more} more in the .json", fill=(200, 200, 200), font=F)
        y += 22
    if snd:
        d.text((pad, y), "sound (from the sfx report):", fill=(255, 196, 0), font=Fb)
        y += 22
        for f in snd:
            d.text((pad, y), f"{f['label']}  {f['kind']}: {f['reason']}"[:int((W - 2 * pad) / 8.4)],
                   fill=(235, 235, 235), font=F)
            y += 22
    if not flags:
        d.text((pad, y), "nothing flagged: no vanishing parts, no move over the limit, sound levels in range",
               fill=(200, 200, 200), font=F)
    page.save(path)


# ------------------------------------------------------------------------------------------------ the run
def out_dir_for(path: Path) -> Path:
    """<project>\\build\\checks\\ when the input sits in a project's build\\, else the lab's .app\\dev\\checks\\."""
    p = Path(path).resolve()
    projects = (LAB / "projects").resolve()
    for a in [p] + list(p.parents):
        if a.name.lower() == "build" and a.parent.parent == projects:
            return a / "checks"
    return (LAB / ".app" / "dev" / "checks").resolve()


def check_name(path: Path) -> str:
    p = Path(path)
    if p.is_dir():
        return f"{p.parent.name}_{p.name}" if p.name.lower() in ("snap", "stills", "frames") else p.name
    return p.stem


def find_motion_blur(path: Path) -> tuple[int, str, bool]:
    """The render's motion blur: a graphic's overlay.json "motion_blur" (next to its .mov); a plan render
    (<build>\\<name>_vN.mp4 = a plan_*.json's "output") = the smallest of its overlay layers' graphics; a snapshot
    folder has none. Also whether it is filmed footage: a plan with "sources" (the user's clips)."""
    p = Path(path).resolve()
    if p.is_dir():
        return 0, "a snapshot has no motion blur", False
    oj = p.parent / "overlay.json"
    if p.suffix.lower() == ".mov" and oj.exists():
        try:
            mb = int(json.loads(oj.read_text(encoding="utf-8")).get("motion_blur") or 0)
            return mb, f"overlay.json motion_blur {mb}", False
        except (ValueError, OSError):
            pass
    for plan in sorted(p.parent.glob("plan_*.json")):
        try:
            pl = json.loads(plan.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if Path(str(pl.get("output", ""))).name.lower() != p.name.lower():
            continue
        mbs = []
        for L in pl.get("layers", []):
            if L.get("type") == "overlay" and L.get("file"):
                oj = Path(L["file"]).parent / "overlay.json"
                try:
                    mbs.append(int(json.loads(oj.read_text(encoding="utf-8")).get("motion_blur") or 0))
                except (ValueError, OSError):
                    mbs.append(0)
        footage = bool(pl.get("sources"))
        if mbs:
            return min(mbs), f"{plan.name}: its graphics' motion_blur {min(mbs)}", footage
        return 0, f"{plan.name}: no graphics with motion blur", footage
    return 0, "none found (give --motion-blur N)", False


def run(path, sfx: str | None = None, motion_blur: int | None = None, fps: float | None = None,
        out: Path | None = None, verbose: bool = True, footage_arg: bool | None = None) -> dict:
    """footage_arg: True / False overrides whether the moves are a camera's (default: a plan with "sources")."""
    t0 = time.time()
    path = Path(path).resolve()
    log = print if verbose else (lambda *a, **k: None)
    mb_found, mb_where, footage = find_motion_blur(path)
    mb_src = "--motion-blur"
    if motion_blur is None:
        motion_blur, mb_src = mb_found, mb_where
    if footage_arg is not None:
        footage = bool(footage_arg)
    if path.is_dir():
        files = folder_frames(path)
        if not files:
            raise SystemExit(f"no PNGs in {path}")
        W, H = Image.open(files[0][1]).size
        if fps is None:
            for oj in (path / "overlay.json", path.parent / "overlay.json"):
                if oj.exists():
                    fps = float(json.loads(oj.read_text(encoding="utf-8")).get("fps") or 0) or None
                    break
        fps = fps or 30.0
        w, h = work_size(W, H)
        frames = ((n, png_rgba(p, w, h)) for n, p in files)
        kind, alpha = "snapshots", True
    else:
        info = ffprobe(path)
        W, H = info["width"], info["height"]
        fps = fps or info["fps"]
        w, h = work_size(W, H)
        frames = video_frames(path, w, h, info["alpha"])
        kind, alpha = ("graphic" if info["alpha"] else "video"), info["alpha"]
    scale = W / w
    m = measure(frames, scale, (w, h), motion_blur=motion_blur)
    t_measure = time.time() - t0
    n_frames = len(m["frames"])
    vflags, basis, vnotes = vanish_flags(m)
    mflags, mnotes = move_flags(m, motion_blur, footage=footage)
    sflags, sfx_info = [], None
    if sfx:
        rep = json.loads(Path(sfx).read_text(encoding="utf-8"))
        sflags = sound_flags(rep)
        sfx_info = {"report": str(Path(sfx).resolve()), "cues": len(rep.get("cues") or []),
                    "limiter_max_db": rep.get("limiter_max_db")}
    flags = vflags + mflags + sflags
    for f in flags:
        f.setdefault("label", range_label(f["frames"][0], f["frames"][1], fps))
        for p in f.get("per_frame", []):
            p["label"] = tc_label(p["frame"], fps)
        for k in ("before", "after", "fastest"):
            if k in f:
                f[k + "_label"] = tc_label(f[k], fps)
    flags.sort(key=lambda f: (f["frames"][0], f["check"]))
    notes = vnotes + mnotes
    for f in notes:
        f["label"] = (range_label(f["frames"][0], f["frames"][1], fps) if "frames" in f
                      else tc_label(f["frame"], fps))
    notes.sort(key=lambda f: f["frames"][0] if "frames" in f else f["frame"])
    mv = m["moves"]
    fin = np.isfinite(mv[:, 0])
    top = int(np.nanargmax(np.where(fin, mv[:, 0], -1))) if fin.any() else None
    name = check_name(path)
    od = Path(out) if out else out_dir_for(path)
    od.mkdir(parents=True, exist_ok=True)
    status = "PASS" if not flags else f"{len(flags)} to look at"
    res = {"input": str(path), "kind": kind, "name": name, "width": W, "height": H, "fps": fps,
           "frames": n_frames, "first_frame": int(m["frames"][0]) if n_frames else None,
           "motion_blur": int(motion_blur or 0), "motion_blur_from": mb_src, "vanish_basis": basis,
           "footage": footage,
           "limits": {"vanish_ratio": VANISH_RATIO, "move_px": MOVE_PX, "step_px": STEP_PX, "loud_db": LOUD_DB,
                      "buried_db": BURIED_DB, "short_db": SHORT_DB, "limiter_db": LIMIT_DB,
                      "copies_rise": COPIES_RISE, "scene_mad": SCENE_MAD},
           "fastest_move": None if top is None else {
               "frame": int(m["frames"][top]), "label": tc_label(int(m["frames"][top]), fps),
               "px": round(float(mv[top, 0]), 1), "at": [int(mv[top, 1]), int(mv[top, 2])]},
           "sfx": sfx_info, "status": "PASS" if not flags else "WARN", "flags": flags, "notes": notes,
           "counts": {c: sum(1 for f in flags if f["check"] == c) for c in ("vanish", "move", "sound")},
           "seconds": None, "seconds_per_minute": None}
    # the sheet: a second decode keeps only the frames it shows
    need = sorted({n for r in sheet_frames([f for f in flags if f["check"] in ("vanish", "move")][:SHEET_ROWS])
                   for n in r})
    tile_w = 300
    tw, th = (tile_w, max(16, round(tile_w * H / W))) if W >= H else (max(16, round(tile_w * W / H)), tile_w)
    tiles = {}
    if need:
        if path.is_dir():
            fmap = dict(files)
            for n in need:
                if n in fmap:
                    tiles[n] = png_rgba(fmap[n], tw, th, label_box=False)
        else:
            want = set(need)
            for n, fr in video_frames(path, tw, th, alpha):
                if n in want:
                    tiles[n] = as_rgba(fr.copy())
                if n >= need[-1]:
                    break
    png = od / f"{name}_precheck.png"
    draw_sheet(png, f"{name}  precheck  ({kind}, {W}x{H}, {fps:g} fps, motion blur {int(motion_blur or 0)})",
               flags, tiles, fps, W / tw, status)
    secs = time.time() - t0
    res["seconds"] = round(secs, 2)
    res["seconds_measure"] = round(t_measure, 2)
    dur_min = n_frames / fps / 60 if n_frames else 0
    res["seconds_per_minute"] = round(secs / dur_min, 1) if dur_min and kind != "snapshots" else None
    res["sheet"] = str(png)
    js = od / f"{name}_precheck.json"
    js.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    res["json"] = str(js)
    if verbose:
        log(f"{name}: {n_frames} frames ({kind}, {W}x{H}, {fps:g} fps), motion blur {res['motion_blur']} "
            f"({mb_src}), vanishing measured on {basis}"
            + (" - filmed footage: its moves are listed, not flagged" if footage else ""))
        if res["fastest_move"]:
            fm = res["fastest_move"]
            log(f"  fastest move: {fm['px']:.0f} px a frame at {fm['label']} (x {fm['at'][0]}, y {fm['at'][1]})")
        for f in flags:
            at = f" at x {f['at'][0]}, y {f['at'][1]}" if f.get("at") else (
                f" in x {f['box'][0]}-{f['box'][2]}, y {f['box'][1]}-{f['box'][3]}" if f.get("box") else "")
            log(f"  {f['check']:6s} {f['label']}: {f['reason']}{at}")
        if notes:
            log(f"  {len(notes)} measured and let through (notes in the .json): "
                + ", ".join(f"{x['label'].split(' ')[0]}" for x in notes[:12]) + (" ..." if len(notes) > 12 else ""))
        log(f"{res['status']}: {len(flags)} flagged ({res['counts']['vanish']} vanish, {res['counts']['move']} move, "
            f"{res['counts']['sound']} sound) in {secs:.1f} s"
            + (f" ({res['seconds_per_minute']:.0f} s per minute of video)" if res["seconds_per_minute"] else ""))
        log(f"  {js}\n  {png}")
    return res


# ------------------------------------------------------------------------------------------------ self-check
def _texture(rng, h: int, w: int) -> np.ndarray:
    t = rng.integers(0, 256, (h // 4 + 1, w // 4 + 1)).astype(np.uint8)
    t = cv2.resize(t, (w, h), interpolation=cv2.INTER_NEAREST)
    return np.dstack([t, 255 - t, t // 2 + 60])


def synth_clip(n: int = 72, W: int = 640, H: int = 360, seed: int = 7, vanish: bool = True, fast: bool = True,
               alpha: bool = False, sub: int = 1):
    """A synthetic clip, in memory: a slowly drifting grey gradient, a big textured block that never vanishes, a
    small textured badge, a moving textured square. Known answers (when enabled):
      vanish  - the badge is gone on f20 only (a part); everything is gone on f40-f41 (the whole picture)
      fast    - the square moves 90 px a frame on f60-f63 (from f59), else 6 px a frame
      clean   - (both off) slow moves, a 12-frame fade of the badge, sensor-like noise: nothing to flag
    alpha = a transparent background (the alpha channel carries the content); sub = motion blur rendered with
    that many sub-frames (the square drawn at sub positions between the frame before and this one, averaged;
    90 = a continuous smear for a 90 px move)."""
    rng = np.random.default_rng(seed)
    big, badge, sq = _texture(rng, 90, 200), _texture(rng, 40, 40), _texture(rng, 56, 56)
    pos = [20.0]
    for f in range(1, n):
        pos.append(pos[-1] + (-90.0 if fast and 60 <= f <= 63 else 6.0))
    yy, xx = np.mgrid[0:H, 0:W]
    for f in range(n):
        if alpha:
            fr = np.zeros((H, W, 4), np.uint8)
        else:
            base = (30 + 20 * np.sin(xx / W * 3 + f * 0.02) + 10 * yy / H).astype(np.uint8)
            fr = np.dstack([base, base, base, np.full((H, W), 255, np.uint8)])
        gone_all = vanish and f in (40, 41)
        if not gone_all:
            fr[20:110, 400:600, :3] = big
            fr[20:110, 400:600, 3] = 255
            fade = 1.0
            if not vanish and 30 <= f < 42:
                fade = max(0.0, 1 - (f - 30) / 12)
            if not (vanish and f == 20) and fade > 0 and not (not vanish and f >= 42):
                fr[260:300, 80:120, :3] = (badge * fade).astype(np.uint8)
                fr[260:300, 80:120, 3] = 255
            x0 = pos[f - 1] if f else pos[0]
            k = max(1, int(sub))
            acc = np.zeros((56, W, 4), np.float32)
            for q in range(1, k + 1):
                lay = fr[150:206].astype(np.float32).copy()
                x = int(round(x0 + (pos[f] - x0) * q / k))
                lay[:, x:x + 56, :3] = sq
                lay[:, x:x + 56, 3] = 255
                acc += lay / k
            fr[150:206] = np.clip(acc + 0.5, 0, 255).astype(np.uint8)
        if not alpha:
            noise = rng.normal(0, 2.0, (H, W, 3))
            fr[..., :3] = np.clip(fr[..., :3] + noise, 0, 255).astype(np.uint8)
        yield f, fr


def _measure_synth(motion_blur: int = 0, **kw) -> dict:
    W, H = 640, 360
    w, h = work_size(W, H)
    frames = ((n, cv2.resize(fr, (w, h), interpolation=cv2.INTER_AREA)) for n, fr in synth_clip(W=W, H=H, **kw))
    return measure(frames, W / w, (w, h), motion_blur=motion_blur)


def selfcheck(verbose: bool = True) -> dict:
    t0 = time.time()
    lines, ok = [], True

    def check(cond, msg):
        nonlocal ok
        ok &= bool(cond)
        lines.append(f"  {'ok ' if cond else 'BAD'} {msg}")

    fps = 30.0
    # 1. vanishing (opaque and alpha)
    for alpha in (False, True):
        m = _measure_synth(vanish=True, fast=False, alpha=alpha)
        vf, basis, _ = vanish_flags(m)
        got = [(f["frames"][0], f["frames"][1], f["whole"]) for f in vf]
        check(got == [(20, 20, False), (40, 41, True)],
              f"vanish ({basis}): {[range_label(a, b, fps) + (' whole' if w else ' part') for a, b, w in got]} "
              f"= f20 (00:00:00:20) part, f40-41 (00:00:01:10 - 00:00:01:11) whole")
        if got and got[0][:2] == (20, 20):
            b = vf[0]["box"]
            check(b[0] <= 80 and b[1] <= 260 and b[2] >= 120 and b[3] >= 300,
                  f"the f20 box {b} holds the badge (80-120, 260-300)")
        mf, _ = move_flags(m, 0)
        check(not mf, f"no move flags at 6 px a frame ({len(mf)})")
    # 2. a known speed
    m = _measure_synth(vanish=False, fast=True)
    mf, _ = move_flags(m, 0)
    got = [(f["frames"][0], f["frames"][1]) for f in mf]
    check(got == [(60, 63)], f"fast move: {[range_label(a, b, fps) for a, b in got]} = f60-63 "
                             "(00:00:02:00 - 00:00:02:03)")
    if mf:
        sp = [p["px"] for p in mf[0]["per_frame"]]
        check(all(abs(s - 90) <= 4.5 for s in sp), f"speeds {sp} px = 90 +-5 %")
    slow = [float(v) for v in m["moves"][1:55, 0] if np.isfinite(v)]
    check(slow and abs(float(np.median(slow)) - 6) <= 0.6, f"slow speed {np.median(slow):.2f} px = 6 +-10 %")
    check(not move_flags(m, 8)[0], "motion blur 8: 90 / 8 = 11 px apart, not flagged")
    vf, _, _ = vanish_flags(m)
    check(not vf, f"no vanish flags on the moving clip ({len(vf)})")
    m5 = _measure_synth(vanish=False, fast=True, sub=5, motion_blur=5)
    mf, notes = move_flags(m5, 5)
    sc = [p.get("copies") for f in mf for p in f["per_frame"]]
    got = [range_label(f["frames"][0], f["frames"][1], fps) for f in mf]
    check([(f["frames"][0], f["frames"][1]) for f in mf] == [(60, 63)],
          f"rendered with 5 sub-frames: copies 18 px apart on {got} (copies score {sc}) = f60-63 "
          "(00:00:02:00 - 00:00:02:03)")
    ms = _measure_synth(vanish=False, fast=True, sub=90, motion_blur=5)
    mf, notes = move_flags(ms, 5)
    check(not mf, f"the same move smeared (90 sub-frames = 1 px apart, read as 5): {len(mf)} flags (0), "
                  f"{len(notes)} let through")
    # the copies score itself, on the known move (x 374 -> 284 at y 178, f62's frames: 194 -> 104)
    fr5 = {n: gray_of(f) for n, f in synth_clip(vanish=False, fast=True, sub=5) if n == 62}
    fr40 = {n: gray_of(f) for n, f in synth_clip(vanish=False, fast=True, sub=90) if n == 62}
    c5, c40 = copies(fr5[62], 222, 178, -90, 0, 18), copies(fr40[62], 222, 178, -90, 0, 18)
    check(c5 >= COPIES_RISE > c40, f"copies score at f62 (00:00:02:02): 5 sub-frames {c5:.2f} (copies), "
                                   f"smeared {c40:.2f} (none); the line {COPIES_RISE}")
    fl, nt = move_flags(m, 0, footage=True)
    check(not fl and len(nt) == 4, f"filmed footage: the same move listed in the notes ({len(nt)}), not flagged")
    # 3. clean
    m = _measure_synth(vanish=False, fast=False)
    vf, _, _ = vanish_flags(m)
    mf, _ = move_flags(m, 0)
    check(not vf and not mf, f"clean clip with a 12-frame fade: {len(vf)} vanish, {len(mf)} move flags (0, 0)")
    # 4. sound
    rows = [{"f": 10 * i, "kind": "pop", "what": f"cue {i}", "song_db": -20.0, "target_db": -35.0,
             "fx_db": -35.0, "vs_song_db": -15.0, "rule": "song", "limiter_db": 0.0} for i in range(8)]
    rows[3].update(fx_db=-10.0, target_db=-10.0, vs_song_db=10.0, rule="floor")          # loud
    rows[5].update(fx_db=-50.0, target_db=-50.0, vs_song_db=-30.0)                       # buried
    rows[6].update(limiter_db=-1.2)                                                      # fine
    sf = sound_flags({"fps": fps, "cues": rows, "limiter_max_db": -1.2})
    got = [(f["frames"][0], f["kind"]) for f in sf]
    check(got == [(30, "loud"), (50, "buried")], f"sound: {[(tc_label(a, fps), k) for a, k in got]} = "
                                                  "f30 (00:00:01:00) loud, f50 (00:00:01:20) buried")
    rows[6].update(limiter_db=-4.0)
    sf = sound_flags({"fps": fps, "cues": rows, "limiter_max_db": -4.0})
    check([(f["frames"][0], f["kind"]) for f in sf] == [(30, "loud"), (50, "buried"), (60, "limiter")],
          "sound: the limiter taking 4 dB at f60 (00:00:02:00) flagged")
    secs = time.time() - t0
    lines.insert(0, f"{'PASS' if ok else 'FAIL'}: precheck selfcheck (vanish, speed, clean, sound) in {secs:.1f} s")
    if verbose:
        print("\n".join(lines))
    return {"ok": ok, "passed": ok, "lines": lines, "seconds": round(secs, 2)}
