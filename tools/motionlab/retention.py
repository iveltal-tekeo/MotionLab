"""Where people left (2026-11-02; docs\\plans.md *Learn from your own posts*, R1 - the user: "add them to plans and start
working on improving the SPARK and content agency secitons"): the audience retention of the user's OWN video, read from
a screenshot of the platform's own graph (TikTok Studio, YouTube Studio, Instagram's insights) - the user's numbers,
no login, no reading of the platforms. The lab traces the curve, not Claude (exact to a pixel, no Claude time): the user
puts four lines on the graph's axes (0 s, the end, the top and the bottom %), the tool finds the curve's colour (or the
user clicks the curve) and follows it column by column -> the share still watching at every second; a second where the
curve cannot be seen stays unknown, never filled in.

Then the windows (a creator's coaching guide the user brought, 2026-11-02): every 3-second window's relative loss =
1 - r(t+3) / r(t), when r(t) > 0 - the share of those still watching who left in those 3 seconds; the holds at 3 s,
10 s and the end; the user's usual = the median of their own traced videos on that platform (from USUAL_MIN). A drop
shows WHERE people left, never why.

knowledge\\local\\retention.json (never shared):
  "videos": {"<platform>:<id>": {platform, id, url, title, end_s, points: [[s, pct | null], ...], axes: {x0, x1, y_top,
             y_bot, top, bottom, end_s}, colour: [r, g, b], image: "knowledge/local/retention/<file>", found (0-1),
             summary: {...}, traced: "2026-11-02 14:05"}}
knowledge\\local\\retention\\ = the screenshots the user added (their own; a new one never replaces an old one).

    key_of(url)                    "tiktok:7699..." / "youtube:eiATPlSfVI0" / "instagram:DeZV..." (None = not a post)
    add_image(name, data)          a screenshot in -> {image, width, height, guess}
    guess(path)                    where the four lines probably go + the curve's colour (the user moves them)
    trace(path, axes, colour)      -> {points, colour, found, thickness}
    summarize(points, end_s)       -> {start, hold_3s, hold_10s, end, windows, drops (the 3 steepest), gaps}
    save(key, image, axes, ...)    traced again here (never the page's numbers) -> the entry
    load(), entry(key), of_url(url), remove(key) (the screenshot stays), usual(platform, but=key)
    selfcheck()                    made-up graphs drawn with Pillow: light, dark with a filled area, a grey band and a
                                   hover line, a hidden piece (unknown, never filled), the guess, save / load
"""
from __future__ import annotations

import io
import math
import os
import re
import statistics
import threading
import time
from pathlib import Path

import numpy as np

from .util import LAB, read_json, write_json

PATH = Path(os.environ.get("MOTIONLAB_RETENTION") or (LAB / "knowledge" / "local" / "retention.json"))
DIR = PATH.parent / "retention"
EXT = (".png", ".jpg", ".jpeg", ".webp")
MAX_BYTES = 15_000_000
MAX_SIDE = 8000
PLATFORMS = ("tiktok", "youtube", "instagram")
WINDOW_S = 3                 # the windows: relative loss over 3 seconds (the guide's measure)
HOLDS = (3, 10)              # still watching at 3 s and at 10 s
USUAL_MIN = 5                # the user's usual needs at least 5 traced videos on that platform
N_DROPS = 3
COLOUR_TOL = 60.0            # RGB distance to the curve's colour that still counts as the curve
_LOCK = threading.RLock()
_KEY = re.compile(r"^(tiktok|youtube|instagram):[\w-]{3,40}$")


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M")


def key_of(url: str | None) -> str | None:
    """A post's key from its link (the twin of app.js agVidId): youtube:<11>, tiktok:<digits>, instagram:<code>."""
    u = str(url or "")
    m = (re.search(r"youtu\.be/([\w-]{11})", u)
         or re.search(r"youtube\.com/\S*?(?:[?&]v=|shorts/|embed/|live/)([\w-]{11})", u))
    if m:
        return f"youtube:{m[1]}"
    m = re.search(r"tiktok\.com\S*?/video/(\d{8,})", u)
    if m:
        return f"tiktok:{m[1]}"
    m = re.search(r"instagram\.com\S*?/(?:reel|reels|p)/([\w-]+)", u)
    if m:
        return f"instagram:{m[1]}"
    return None


def key_ok(key: str) -> bool:
    return bool(_KEY.match(str(key or "")))


# ------------------------------------------------------------------------------------------------ the picture
def _image(path: Path) -> np.ndarray:
    from PIL import Image
    with Image.open(path) as im:
        if max(im.size) > MAX_SIDE:
            raise ValueError("the screenshot is too big - at most 8000 pixels a side")
        return np.asarray(im.convert("RGB"), dtype=np.float32)


def _hsv(a: np.ndarray):
    """(saturation 0-1, value 0-1, hue 0-360) of an RGB array, vectorised."""
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(-1), a.min(-1)
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    h = (np.degrees(np.arctan2(math.sqrt(3) * (g - b), 2 * r - g - b)) + 360.0) % 360.0
    return s, mx / 255.0, h


def _curve_colour(a: np.ndarray, x0: int, x1: int, y0: int, y1: int) -> list[int] | None:
    """The curve's colour inside a region: the saturated hue that covers the most columns with a top edge that moves
    (a coloured header or a button covers columns too, but its top is flat or it is short) - then the most saturated
    half of its pixels (a lighter fill under the curve has the same hue, less saturation)."""
    sub = a[y0:y1, x0:x1]
    if sub.size == 0:
        return None
    s, v, h = _hsv(sub)
    cand = (s > 0.30) & (v > 0.25)
    if int(cand.sum()) < 20:
        return None
    ys, xs = np.nonzero(cand)
    bins = (h[ys, xs] // 15).astype(int) % 24
    best, best_score = None, 0.0
    for b in np.unique(bins):
        sel = bins == b
        if int(sel.sum()) < 20:
            continue
        cx, cy = xs[sel], ys[sel]
        top = np.full(sub.shape[1], np.inf)
        np.minimum.at(top, cx, cy)
        covered = np.isfinite(top)
        n = int(covered.sum())
        if n < 20:
            continue
        moves = float(np.std(top[covered])) > 3.0
        score = n * (1.0 if moves else 0.2)
        if score > best_score:
            best, best_score = b, score
    if best is None:
        return None
    # the line sits on top: per column the most saturated pixel among the first rows of the hue (a fill below it, or
    # the soft edge above it, is less saturated), then the median over the columns
    sel = bins == best
    cx, cy = xs[sel], ys[sel]
    top = np.full(sub.shape[1], np.inf)
    np.minimum.at(top, cx, cy)
    near = cy <= top[cx] + 6
    cx, cy = cx[near], cy[near]
    sat = s[cy, cx]
    best_px: dict[int, tuple[float, int]] = {}
    for x, y, q in zip(cx.tolist(), cy.tolist(), sat.tolist()):
        if x not in best_px or q > best_px[x][0]:
            best_px[x] = (q, y)
    core = np.array([sub[y, x] for x, (_, y) in best_px.items()])
    return [int(round(x)) for x in np.median(core, axis=0)]


def _mask(a: np.ndarray, colour) -> np.ndarray:
    c = np.asarray(colour, dtype=np.float32).reshape(1, 1, 3)
    return np.sqrt(((a - c) ** 2).sum(-1)) < COLOUR_TOL


SKIP_COST = 14.0             # a column left out costs this much (a hover line, a label of the curve's colour)
OUT_COST = 3.0               # a column above the top line costs this much (only a curve over 100 % goes there)


def _runs(mask: np.ndarray, x0: int, x1: int, y0: int, y1: int):
    """Per column every run of curve pixels -> (candidate centre rows per column, the line's thickness). A long run
    (a fill of the same colour under the curve, a steep drop drawn upright) gives its top edge + half a line."""
    raw = []
    for x in range(x0, x1 + 1):
        rows = np.flatnonzero(mask[y0:y1, x])
        col, start, end = [], None, None
        for r in rows.tolist():
            if start is None:
                start = end = r
            elif r <= end + 2:
                end = r
            else:
                col.append((y0 + start, y0 + end))
                start = end = r
        if start is not None:
            col.append((y0 + start, y0 + end))
        raw.append(col)
    short = [b - a + 1 for col in raw for a, b in col if b - a + 1 <= 12]
    thick = float(statistics.median(short)) if short else 2.0
    cands = [[a + (min(b - a + 1, thick) - 1) / 2.0 for a, b in col] for col in raw]
    return cands, thick


def _track(cands: list[list[float]], y_top: float) -> np.ndarray:
    """The curve through the columns: the path of candidates that moves least from column to column (Viterbi), a
    column may be skipped (SKIP_COST, it keeps the last row) - so a button, a legend or a hover line of the curve's
    colour is not taken for the curve; above the top line costs OUT_COST a column."""
    n = len(cands)
    states: list[list[tuple[float, float | None, int]]] = []     # (cost, row (None = no row yet), back)
    prev: list[tuple[float, float | None, int]] | None = None
    for i in range(n):
        cur = []
        for y in cands[i]:
            pen = OUT_COST if y < y_top - 3 else 0.0
            if prev is None:
                cur.append((pen, y, -1))
            else:
                j, c = min(((j, pc + (abs(y - py) if py is not None else 0.0)) for j, (pc, py, _) in enumerate(prev)),
                           key=lambda t: t[1])
                cur.append((c + pen, y, j))
        if prev is None:
            cur.append((SKIP_COST, None, -1))
        else:
            j = min(range(len(prev)), key=lambda k: prev[k][0])
            cur.append((prev[j][0] + SKIP_COST, prev[j][1], j))
        states.append(cur)
        prev = cur
    ys = np.full(n, np.nan)
    if not states:
        return ys
    k = min(range(len(states[-1])), key=lambda q: states[-1][q][0])
    for i in range(n - 1, -1, -1):
        cost, y, back = states[i][k]
        if k < len(cands[i]):                       # a real row (the last state of a column is the skip)
            ys[i] = y
        k = back if back >= 0 else 0
    return ys


def _columns(mask: np.ndarray, x0: int, x1: int, y0: int, y1: int, y_top: float):
    cands, thick = _runs(mask, x0, x1, y0, y1)
    return _track(cands, y_top), thick


def _despike(ys: np.ndarray, tol: float) -> np.ndarray:
    """A column far from BOTH its left and its right neighbours (a hover line, a dot of a label) is not the curve; a
    steep drop stays (it is close to one side)."""
    out = ys.copy()
    n = len(ys)
    for i in range(n):
        if not np.isfinite(ys[i]):
            continue
        L = ys[max(0, i - 4):i]
        R = ys[i + 1:i + 5]
        L, R = L[np.isfinite(L)], R[np.isfinite(R)]
        near = [abs(ys[i] - float(np.median(side))) <= tol for side in (L, R) if side.size]
        if near and not any(near):
            out[i] = np.nan
    return out


# ------------------------------------------------------------------------------------------------ the guess
def _gridlines(a: np.ndarray, xa: int, xb: int, skip_colour) -> list[int]:
    """Rows that are long thin lines across the graph (gridlines, the axis): one colour over 70 % of the width."""
    seg = a[:, xa:xb + 1]
    if seg.shape[1] < 20:
        return []
    bg = np.median(seg.reshape(-1, 3), axis=0)
    med = np.median(seg, axis=1, keepdims=True)
    same = np.sqrt(((seg - med) ** 2).sum(-1)) < 25
    differs = np.sqrt(((med[:, 0, :] - bg) ** 2).sum(-1)) > 12
    if skip_colour is not None:
        differs &= np.sqrt(((med[:, 0, :] - np.asarray(skip_colour, dtype=np.float32)) ** 2).sum(-1)) >= COLOUR_TOL
    rows = np.flatnonzero((same.mean(1) > 0.7) & differs).tolist()
    blocks, start, last = [], None, None
    for r in rows:
        if start is None or r > last + 1:
            if start is not None:
                blocks.append((start, last))
            start = r
        last = r
    if start is not None:
        blocks.append((start, last))
    # a thin block = a gridline; a tall one = a fill under the curve - its bottom edge is the graph's base
    return [int(a) if b - a <= 4 else int(b) for a, b in blocks]


def _even(lines: list[int]) -> list[int]:
    """The longest evenly spaced run of gridlines (3 or more, within 3 px) - the graph's own scale."""
    best: list[int] = []
    n = len(lines)
    for i in range(n):
        for j in range(i + 1, n):
            step = lines[j] - lines[i]
            if step < 8:
                continue
            seq, nxt = [lines[i], lines[j]], lines[j] + step
            for k in range(j + 1, n):
                if abs(lines[k] - nxt) <= 3:
                    seq.append(lines[k])
                    nxt = lines[k] + step
            if len(seq) >= 3 and len(seq) > len(best):
                best = seq
    return best


def guess(path: Path) -> dict:
    """Where the four lines probably go: 0 s and the end where the curve starts and ends, the top line where it starts
    (100 % - a retention graph starts there) snapped to a gridline, the bottom line on the lowest of the evenly spaced
    gridlines. Only a start: the user moves them."""
    a = _image(Path(path))
    H, W = a.shape[:2]
    out = {"width": W, "height": H, "colour": None, "found": False, "x0": round(W * 0.1), "x1": round(W * 0.9),
           "y_top": round(H * 0.15), "y_bot": round(H * 0.85), "grid": []}
    col = _curve_colour(a, 0, W, 0, H)
    if col is None:
        return out
    import cv2
    m = _mask(a, col)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
    if n <= 1:
        return out
    W_, X_, Y_, H_ = cv2.CC_STAT_WIDTH, cv2.CC_STAT_LEFT, cv2.CC_STAT_TOP, cv2.CC_STAT_HEIGHT
    main = 1 + int(np.argmax(st[1:, W_]))          # the curve = the widest shape of its colour (+ its pieces)
    top, bot = st[main, Y_], st[main, Y_] + st[main, H_]
    keep = [i for i in range(1, n) if i == main or (st[i, W_] >= 0.03 * W and st[i, Y_] < bot and st[i, Y_] + st[i, H_] > top)]
    x0 = int(min(st[i, X_] for i in keep))
    x1 = int(max(st[i, X_] + st[i, W_] - 1 for i in keep))
    if x1 - x0 < 40:
        return out
    m = np.isin(lab, keep)
    ys, _ = _columns(m, x0, x1, 0, H, 0.0)
    ys = _despike(ys, max(4.0, H * 0.01))
    fin = np.flatnonzero(np.isfinite(ys))
    if fin.size < 10:
        return out
    y_start = float(np.median(ys[fin[:3]]))
    y_low = float(np.nanmax(ys))
    grid = _gridlines(a, x0, x1, col)
    even = _even(grid)
    y_top = next((g for g in grid if abs(g - y_start) <= 6), round(y_start))
    below = [g for g in (even or grid) if g >= y_low - 2]
    y_bot = max(below) if below else min(H - 1, round(y_top + (y_low - y_top) * 1.25 + 10))
    if y_bot - y_top < 30:
        y_bot = min(H - 1, y_top + 60)
    out.update(colour=col, found=True, x0=int(x0), x1=int(x1), y_top=int(y_top), y_bot=int(y_bot), grid=grid)
    return out


# ------------------------------------------------------------------------------------------------ the trace
def _axes(axes: dict) -> dict:
    try:
        A = {k: float(axes[k]) for k in ("x0", "x1", "y_top", "y_bot", "end_s")}
        A["top"] = float(axes.get("top", 100) if axes.get("top") not in (None, "") else 100)
        A["bottom"] = float(axes.get("bottom", 0) if axes.get("bottom") not in (None, "") else 0)
    except (KeyError, TypeError, ValueError):
        raise ValueError("put the four lines on the graph first") from None
    if not all(math.isfinite(v) for v in A.values()):
        raise ValueError("put the four lines on the graph first")
    if A["x1"] - A["x0"] < 40 or A["y_bot"] - A["y_top"] < 30:
        raise ValueError("the lines are too close together - 0 s left of the end, the top line above the bottom one")
    if not 1 <= A["end_s"] <= 7200:
        raise ValueError("the graph's end: the video's length in seconds")
    if A["top"] <= A["bottom"] or not (0 <= A["bottom"] < 1000 and 0 < A["top"] <= 1000):
        raise ValueError("the top line's % must be above the bottom line's")
    return A


def trace(path: Path, axes: dict, colour=None) -> dict:
    """The curve between the four lines -> per second the % still watching (None = not seen there). colour = the
    pixel the user clicked, else the curve's own colour found inside the lines."""
    a = _image(Path(path))
    H, W = a.shape[:2]
    A = _axes(axes)
    x0, x1 = int(round(A["x0"])), int(round(A["x1"]))
    if x0 < 0 or x1 >= W or A["y_top"] < 0 or A["y_bot"] >= H:
        raise ValueError("a line is outside the screenshot")
    span = A["y_bot"] - A["y_top"]
    y0 = max(0, int(A["y_top"] - 0.3 * span))           # a curve may go above its top line (rewatches: > 100 %)
    y1 = min(H, int(A["y_bot"] + 4))
    if colour is not None:
        try:
            col = [int(max(0, min(255, round(float(x))))) for x in list(colour)[:3]]
            assert len(col) == 3
        except (TypeError, ValueError, AssertionError):
            raise ValueError("the curve's colour is not a colour") from None
    else:
        col = _curve_colour(a, x0, x1 + 1, y0, y1)
        if col is None:
            raise ValueError("no coloured curve between the lines - click on the curve to show its colour")
    m = _mask(a, col)
    ys, thick = _columns(m, x0, x1, y0, y1, A["y_top"])
    ys = _despike(ys, max(4.0, 0.04 * span))
    end_s = A["end_s"]
    px_s = (x1 - x0) / end_s
    half = max(1.0, 0.35 * px_s)
    secs = list(range(0, int(math.floor(end_s)) + 1))
    if end_s - math.floor(end_s) >= 0.3:
        secs.append(round(end_s, 1))
    pts = []
    for s in secs:
        xs = x0 + s * px_s
        lo, hi = int(math.floor(xs - half)), int(math.ceil(xs + half))
        win = ys[max(0, lo - x0):max(0, min(len(ys), hi - x0 + 1))]
        win = win[np.isfinite(win)]
        if not win.size:
            pts.append([s, None])
            continue
        y = float(np.median(win))
        pct = A["bottom"] + (A["y_bot"] - y) / span * (A["top"] - A["bottom"])
        pts.append([s, round(pct, 1)])
    known = sum(1 for _, p in pts if p is not None)
    return {"points": pts, "colour": col, "found": round(known / max(1, len(pts)), 3), "thickness": thick,
            "axes": {k: round(v, 2) for k, v in A.items()}}


def summarize(points: list, end_s: float | None = None) -> dict:
    """The numbers of a curve: where it starts, the holds at 3 s / 10 s / the end, every 3-second window's relative
    loss (1 - r(t+3) / r(t), r(t) > 0; only where both ends were seen), the 3 steepest drops that do not overlap, the
    seconds not seen."""
    P = {}
    for s, p in points or []:
        if p is not None and float(s).is_integer():
            P[int(s)] = float(p)
    last_s = max((float(s) for s, p in points or [] if p is not None), default=None)
    end_s = float(end_s) if end_s else (max((float(s) for s, _ in points or []), default=0.0))
    end_pct = next((float(p) for s, p in sorted(points or [], key=lambda x: -float(x[0]))
                    if p is not None and float(s) >= end_s - 1.0), None)
    wins = []
    for t in range(0, int(math.floor(end_s)) - WINDOW_S + 1):
        a, b = P.get(t), P.get(t + WINDOW_S)
        if a is not None and b is not None and a > 0:
            wins.append({"s": t, "loss": round(100.0 * (1.0 - b / a), 1), "from": a, "to": b})
    drops = []
    for w in sorted(wins, key=lambda w: -w["loss"]):
        if w["loss"] <= 0 or len(drops) >= N_DROPS:
            break
        if all(abs(w["s"] - d["s"]) >= WINDOW_S for d in drops):
            drops.append(w)
    gaps, run = [], None
    for s, p in points or []:
        if p is None:
            run = [s, s] if run is None else [run[0], s]
        elif run is not None:
            gaps.append(run)
            run = None
    if run is not None:
        gaps.append(run)
    return {"start": P.get(0), "hold_3s": P.get(HOLDS[0]) if end_s >= HOLDS[0] else None,
            "hold_10s": P.get(HOLDS[1]) if end_s >= HOLDS[1] + 1 else None, "end": end_pct, "end_s": end_s,
            "last_seen_s": last_s, "windows": wins, "drops": drops, "gaps": gaps,
            "seen": sum(1 for _, p in points or [] if p is not None), "total": len(points or [])}


# ------------------------------------------------------------------------------------------------ the store
def load() -> dict:
    try:
        d = read_json(PATH)
    except (OSError, ValueError):
        d = {}
    if not isinstance(d, dict):
        d = {}
    d.setdefault("videos", {})
    return d


def entry(key: str) -> dict | None:
    return load()["videos"].get(str(key or ""))


def of_url(url: str | None) -> dict | None:
    k = key_of(url)
    return entry(k) if k else None


def _rel(p: Path) -> str:
    return p.resolve().relative_to(LAB.resolve()).as_posix()


def _image_path(image: str) -> Path:
    """A screenshot of the store - nothing else is ever read here."""
    p = (LAB / str(image or "")).resolve()
    try:
        p.relative_to(DIR.resolve())
    except ValueError:
        raise ValueError("not a screenshot added here") from None
    if p.suffix.lower() not in EXT or not p.is_file():
        raise ValueError("not a screenshot added here")
    return p


def add_image(name: str, data: bytes) -> dict:
    """A screenshot the user pasted or picked -> knowledge\\local\\retention\\<name>_<time>.<ext> (a new file every
    time) + its size and the guess for the four lines."""
    from PIL import Image, UnidentifiedImageError
    if not data or len(data) > MAX_BYTES:
        raise ValueError("the screenshot is empty or bigger than 15 MB")
    try:
        with Image.open(io.BytesIO(data)) as im:
            fmt = (im.format or "").lower()
            im.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise ValueError("not a picture - a .png, .jpg or .webp screenshot") from None
    ext = {"png": ".png", "jpeg": ".jpg", "webp": ".webp"}.get(fmt)
    if not ext:
        raise ValueError("not a picture - a .png, .jpg or .webp screenshot")
    stem = re.sub(r"[^\w-]+", "_", Path(str(name or "graph")).stem)[:40].strip("_") or "graph"
    DIR.mkdir(parents=True, exist_ok=True)
    p = DIR / f"{stem}_{time.strftime('%Y%m%d-%H%M%S')}{ext}"
    k = 2
    while p.exists():
        p = DIR / f"{stem}_{time.strftime('%Y%m%d-%H%M%S')}_{k}{ext}"
        k += 1
    p.write_bytes(data)
    g = guess(p)
    return {"image": _rel(p), "width": g["width"], "height": g["height"], "guess": g}


def trace_image(image: str, axes: dict, colour=None) -> dict:
    """The page's live preview: the trace + its numbers (nothing saved)."""
    r = trace(_image_path(image), axes, colour)
    r["summary"] = summarize(r["points"], r["axes"]["end_s"])
    return r


def save(key: str, image: str, axes: dict, colour=None, url: str = "", title: str = "") -> dict:
    """Traced again here from the stored screenshot (the page's numbers are never taken) -> the entry, saved."""
    key = str(key or "")
    if not key_ok(key):
        raise ValueError("not a post of TikTok, YouTube or Instagram")
    r = trace(_image_path(image), axes, colour)
    if r["found"] < 0.3:
        raise ValueError("the curve was not found between the lines - put them on the graph's axes, or click the curve")
    plat, vid = key.split(":", 1)
    e = {"platform": plat, "id": vid, "url": str(url or "")[:300], "title": " ".join(str(title or "").split())[:160],
         "end_s": r["axes"]["end_s"], "points": r["points"], "axes": r["axes"], "colour": r["colour"],
         "image": str(image), "found": r["found"], "summary": summarize(r["points"], r["axes"]["end_s"]),
         "traced": _now()}
    with _LOCK:
        d = load()
        d["videos"][key] = e
        d["updated"] = _now()
        write_json(PATH, d)
    return e


def remove(key: str) -> dict:
    """The traced curve goes; its screenshot stays in knowledge\\local\\retention\\ (nothing deleted)."""
    with _LOCK:
        d = load()
        d["videos"].pop(str(key or ""), None)
        d["updated"] = _now()
        write_json(PATH, d)
    return d


def usual(platform: str, but: str | None = None) -> dict | None:
    """The user's usual on a platform: the median hold at 3 s and at 10 s of their OTHER traced videos (from
    USUAL_MIN each) - their own videos only, never another creator's."""
    vids = [e for k, e in load()["videos"].items() if e.get("platform") == platform and k != but]
    out = {"n": len(vids)}
    for k in ("hold_3s", "hold_10s"):
        vals = [float((e.get("summary") or {}).get(k)) for e in vids if (e.get("summary") or {}).get(k) is not None]
        out[k] = round(statistics.median(vals), 1) if len(vals) >= USUAL_MIN else None
        out[k + "_n"] = len(vals)
    return out if out["hold_3s"] is not None or out["hold_10s"] is not None else None


# ------------------------------------------------------------------------------------------------ the self-check
def _draw(curve, *, W=900, H=420, box=(80, 60, 780, 360), end_s=33.0, top=100.0, bg=(255, 255, 255),
          grid=(225, 225, 225), line=(32, 110, 230), fill=None, band=None, hover_x=None, hide=None, ticks=5):
    """A made-up retention graph, drawn at 2x and scaled down (soft edges like a real screenshot)."""
    from PIL import Image, ImageDraw
    k = 2
    x0, y0, x1, y1 = box
    im = Image.new("RGB", (W * k, H * k), bg)
    dr = ImageDraw.Draw(im, "RGBA")
    for i in range(ticks):
        y = (y0 + (y1 - y0) * i / (ticks - 1)) * k
        dr.line([(x0 * k, y), (x1 * k, y)], fill=grid, width=k)
    px = lambda s: (x0 + (x1 - x0) * s / end_s) * k                                 # noqa: E731
    py = lambda p: (y1 - (y1 - y0) * p / top) * k                                    # noqa: E731
    pts = [(px(s / 4), py(curve(s / 4))) for s in range(int(end_s * 4) + 1)]
    if band:
        lo, hi = band
        dr.polygon([(px(s / 4), py(hi(s / 4))) for s in range(int(end_s * 4) + 1)]
                   + [(px(s / 4), py(lo(s / 4))) for s in range(int(end_s * 4), -1, -1)], fill=(200, 200, 200, 255))
    if fill:
        dr.polygon(pts + [(px(end_s), y1 * k), (px(0), y1 * k)], fill=fill)
    dr.line(pts, fill=line, width=3 * k, joint="curve")
    if hover_x is not None:
        dr.line([(hover_x * k, y0 * k), (hover_x * k, y1 * k)], fill=line, width=k)
    dr.rectangle([60 * k, 8 * k, 140 * k, 30 * k], fill=(230, 40, 90))               # a coloured button (not the curve)
    if hide:
        a, b = hide
        dr.rectangle([px(a) - 2, (y0 - 30) * k, px(b) + 2, (y1 + 2) * k], fill=bg)
    out = io.BytesIO()
    im.resize((W, H), Image.LANCZOS).save(out, "PNG")
    return out.getvalue()


def selfcheck() -> dict:
    import tempfile
    global PATH, DIR
    lines: list[str] = []
    ok = True

    def check(cond, what):
        nonlocal ok
        ok = ok and bool(cond)
        lines.append(("ok   " if cond else "FAIL ") + what)

    def truth(s):                                       # 100 % -> a drop between 4 and 6 s -> a slow slide
        r = 100 - 6 * min(s, 4)
        if s > 4:
            r -= 14 * min(1.0, (s - 4) / 2)
        if s > 6:
            r -= 1.1 * (s - 6)
        return r

    old = PATH, DIR
    scratch = LAB / ".app" / "dev"                     # inside the lab: the store keeps paths relative to it
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ml_ret_", dir=scratch) as td:
        PATH, DIR = Path(td) / "retention.json", Path(td) / "retention"
        try:
            box, end_s = (80, 60, 780, 360), 33.0
            axes = {"x0": 80, "x1": 780, "y_top": 60, "y_bot": 360, "top": 100, "bottom": 0, "end_s": end_s}
            cases = [("light", {}, axes),
                     ("dark + a fill under the curve", {"bg": (24, 24, 28), "grid": (60, 60, 66), "line": (255, 60, 120),
                                                        "fill": (255, 60, 120, 60)}, axes),
                     ("a grey band + a hover line", {"band": (lambda s: truth(s) - 15, lambda s: truth(s) - 5),
                                                     "hover_x": 400}, axes),
                     ("a top line at 120 %", {"top": 120.0}, {**axes, "top": 120})]
            for name, kw, ax in cases:
                f = Path(td) / f"{name.split()[0]}.png"
                f.write_bytes(_draw(truth, box=box, end_s=end_s, **kw))
                r = trace(f, ax)
                errs = [abs(p - truth(s)) for s, p in r["points"] if p is not None]
                worst = max(errs) if errs else 99
                check(r["found"] >= 0.95 and worst <= 1.5,
                      f"trace, {name}: {r['found'] * 100:.0f} % of the seconds seen, worst error {worst:.2f} points")
            # the windows: 4 -> 7 s holds the steepest drop
            f = Path(td) / "light.png"
            sm = summarize(trace(f, axes)["points"], end_s)
            d0 = sm["drops"][0] if sm["drops"] else {}
            exp = round(100 * (1 - truth(7) / truth(4)), 1)
            check(d0.get("s") in (3, 4) and abs(d0.get("loss", 0) - 100 * (1 - truth(d0.get("s", 4) + 3)
                                                                         / truth(d0.get("s", 4)))) <= 2.0,
                  f"the steepest 3-second drop starts at {d0.get('s')} s: {d0.get('loss')} % (4 -> 7 s: {exp} %)")
            check(sm["hold_3s"] is not None and abs(sm["hold_3s"] - truth(3)) <= 1.5
                  and abs(sm["hold_10s"] - truth(10)) <= 1.5 and abs(sm["end"] - truth(end_s)) <= 1.5,
                  f"holds: 3 s {sm['hold_3s']} ({truth(3):.1f}), 10 s {sm['hold_10s']} ({truth(10):.1f}), "
                  f"end {sm['end']} ({truth(end_s):.1f})")
            # a hidden piece stays unknown - never filled in
            f2 = Path(td) / "hidden.png"
            f2.write_bytes(_draw(truth, box=box, end_s=end_s, hide=(14, 18)))
            r2 = trace(f2, axes)
            unk = [s for s, p in r2["points"] if p is None]
            sm2 = summarize(r2["points"], end_s)
            check(set(range(15, 18)) <= set(unk) and not any(w["s"] in range(12, 18) for w in sm2["windows"])
                  and sm2["gaps"], f"a hidden piece (14-18 s) stays unknown: seconds {unk}, gaps {sm2['gaps']}")
            # the guess: the curve's ends, the start on the top line, the bottom on the evenly spaced gridlines
            g = guess(f)
            check(g["found"] and abs(g["x0"] - 80) <= 4 and abs(g["x1"] - 780) <= 4 and abs(g["y_top"] - 60) <= 4
                  and abs(g["y_bot"] - 360) <= 4,
                  f"the guess: x {g['x0']}-{g['x1']} (80-780), y {g['y_top']}-{g['y_bot']} (60-360), colour {g['colour']}")
            gd = guess(Path(td) / "dark.png")               # a pink button of the curve's own hue above the graph
            check(gd["found"] and abs(gd["x0"] - 80) <= 4 and abs(gd["x1"] - 780) <= 4 and abs(gd["y_top"] - 60) <= 4
                  and abs(gd["y_bot"] - 360) <= 4,
                  f"the guess on a dark graph: x {gd['x0']}-{gd['x1']}, y {gd['y_top']}-{gd['y_bot']}, colour {gd['colour']}")
            # a click on the curve's colour, the store
            r3 = trace(f, axes, colour=g["colour"])
            check(r3["found"] >= 0.95, f"a clicked colour traces too ({r3['found'] * 100:.0f} %)")
            im = add_image("TikTok graph.png", f.read_bytes())
            e = save("tiktok:7699968368249425155", im["image"], axes, url="https://www.tiktok.com/@a/video/7699968368249425155")
            check(entry("tiktok:7699968368249425155") is not None and e["summary"]["drops"]
                  and of_url("https://www.tiktok.com/@a/video/7699968368249425155?lang=es") is not None,
                  "saved, found again by its link")
            for i in range(USUAL_MIN):
                save(f"tiktok:10000000{i}", im["image"], axes)
            u = usual("tiktok", but="tiktok:7699968368249425155")
            check(u and u["n"] == USUAL_MIN and abs(u["hold_3s"] - e["summary"]["hold_3s"]) < 0.01,
                  f"the usual of {USUAL_MIN} other videos: 3 s {u and u['hold_3s']}")
            for bad, what in ((lambda: save("tiktok:1", im["image"], axes), "a key that is not a post"),
                              (lambda: trace_image("tools/config.json", axes), "a file outside the screenshots"),
                              (lambda: add_image("x.png", b"not a picture"), "bytes that are not a picture"),
                              (lambda: trace(f, {**axes, "x1": 90}), "lines too close together")):
                try:
                    bad()
                    check(False, f"refused: {what}")
                except ValueError:
                    check(True, f"refused: {what}")
            remove("tiktok:7699968368249425155")
            check(entry("tiktok:7699968368249425155") is None and (LAB / im["image"]).is_file(),
                  "removed - the screenshot stays")
            check(key_of("https://www.youtube.com/shorts/eiATPlSfVI0") == "youtube:eiATPlSfVI0"
                  and key_of("https://youtu.be/D8SQWHheo-g?t=3") == "youtube:D8SQWHheo-g"
                  and key_of("https://www.instagram.com/reel/DeZVKpSM6D-/") == "instagram:DeZVKpSM6D-"
                  and key_of("https://example.com/video/123456789") is None, "a post's key from its link")
        finally:
            PATH, DIR = old
    return {"passed": ok, "lines": lines}
