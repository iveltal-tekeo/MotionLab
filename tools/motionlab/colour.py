"""The colour and look of an analysed video (0.4, the cinematic focus - the user: "heavy usage of effects, transitions
and colour grading"). Made from what the analysis already measured - per frame the brightness (luma p05 / mean /
p95), saturation, CIELab tint (a*, b*), black bars - and its colour thumbnails (cache\\thumbs.u8): no model, no new
decoding.

- per shot: brightness, black and white level, contrast, saturation, warmth (b*) and tint (a*), split toning
  (shadows vs highlights), vignette, its three main colours;
- for the video: the look in words ("warm, teal & orange, high contrast, lifted blacks, letterbox"), how consistent it
  is from shot to shot, a starting grade for the lab's renders (levels, gamma, saturation, a tint - the quick draft
  uses it), the Lab mean / spread a match LUT needs, five main colours
  -> analysis\\<name>\\colour\\colour.json (profile.py reads its "summary": cards, Claude's memory, styles).
- match_lut(): a 3D LUT that moves the user's footage toward a reference's look (Reinhard transfer in Lab: each
  channel's mean and spread), written as a .cube for DaVinci Resolve and read by the compositor (grade "lut3d");
  closeness() says how near two looks are (100 = the same mean colour and spread).
Thumbnails are BGR (the signal pass pipes bgr24). A pruned cache (no thumbs) still gives the per-frame numbers.
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np

from .util import ANALYSIS, read_json, write_json

SCHEMA = 1
TYPICAL = {"black": 3.0, "white": 92.0, "brightness": 45.0, "saturation": 32.0}   # footage as shot, roughly
HUES = [(20, "red"), (50, "orange"), (75, "yellow"), (165, "green"), (200, "teal"), (260, "blue"), (300, "purple"),
        (345, "magenta"), (360, "red")]


def _wmedian(vals, weights) -> float | None:
    v = np.asarray(vals, float)
    w = np.asarray(weights, float)
    ok = np.isfinite(v) & (w > 0)
    if not ok.any():
        return None
    v, w = v[ok], w[ok]
    o = np.argsort(v)
    c = np.cumsum(w[o])
    return float(v[o][np.searchsorted(c, c[-1] / 2)])


def _wstd(vals, weights) -> float | None:
    v = np.asarray(vals, float)
    w = np.asarray(weights, float)
    ok = np.isfinite(v) & (w > 0)
    if ok.sum() < 2:
        return None
    m = np.average(v[ok], weights=w[ok])
    return float(math.sqrt(np.average((v[ok] - m) ** 2, weights=w[ok])))


def to_lab(rgb_u8: np.ndarray) -> np.ndarray:
    """uint8 RGB (..., 3) -> float32 CIELab (L 0..100, a / b about -128..127), D65."""
    f = rgb_u8.reshape(-1, 1, 3).astype(np.float32) / 255.0
    return cv2.cvtColor(f, cv2.COLOR_RGB2LAB).reshape(rgb_u8.shape[:-1] + (3,))


def from_lab(lab: np.ndarray) -> np.ndarray:
    f = lab.reshape(-1, 1, 3).astype(np.float32)
    return np.clip(cv2.cvtColor(f, cv2.COLOR_LAB2RGB).reshape(lab.shape), 0, 1)


def hue_name(a: float, b: float) -> str:
    h = (math.degrees(math.atan2(b, a)) + 360) % 360
    return next(n for lim, n in HUES if h <= lim)


def lab_stats(rgb_u8: np.ndarray) -> dict:
    """Mean and spread of L, a, b over some pictures (uint8 RGB, any shape (..., 3))."""
    lab = to_lab(rgb_u8).reshape(-1, 3)
    return {"mean": [round(float(x), 3) for x in lab.mean(axis=0)],
            "std": [round(float(x), 3) for x in lab.std(axis=0)]}


def palette(rgb_u8: np.ndarray, k: int) -> list:
    """k main colours ["#rrggbb", share] (k-means on the pixels, largest first)."""
    px = rgb_u8.reshape(-1, 3).astype(np.float32)
    if len(px) > 20000:
        px = px[np.linspace(0, len(px) - 1, 20000).astype(int)]
    k = max(1, min(k, len(px)))
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    cv2.setRNGSeed(1)
    _, lab, cen = cv2.kmeans(px, k, None, crit, 2, cv2.KMEANS_PP_CENTERS)
    share = np.bincount(lab.ravel(), minlength=k) / len(px)
    out = sorted(((("#%02x%02x%02x" % tuple(int(round(c)) for c in cen[i])), round(float(share[i]), 3))
                  for i in range(k)), key=lambda x: -x[1])
    return [list(x) for x in out]


def _shot_look(T: np.ndarray | None) -> dict:
    """What the thumbnails of one shot (BGR uint8, (n, h, w, 3)) say: split toning, vignette, colourfulness, colours."""
    if T is None or not len(T):
        return {}
    rgb = T[..., ::-1]
    lab = to_lab(rgb)
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    out = {}
    for key, m in (("shadows", L < 30), ("highlights", L > 70)):
        if m.mean() > 0.04:
            out[key] = [round(float(a[m].mean()), 2), round(float(b[m].mean()), 2)]
    h, w = L.shape[1:3]
    ch, cw = max(1, h // 5), max(1, w // 5)
    corners = np.concatenate([L[:, :ch, :cw].ravel(), L[:, :ch, -cw:].ravel(), L[:, -ch:, :cw].ravel(),
                              L[:, -ch:, -cw:].ravel()])
    centre = L[:, h * 2 // 5:h * 3 // 5 + 1, w * 2 // 5:w * 3 // 5 + 1]
    if centre.mean() > 8:
        out["vignette"] = round(float(corners.mean() / centre.mean()), 3)
    rg, yb = rgb[..., 0].astype(float) - rgb[..., 1], 0.5 * (rgb[..., 0].astype(float) + rgb[..., 1]) - rgb[..., 2]
    out["colourfulness"] = round(float(math.hypot(rg.std(), yb.std()) + 0.3 * math.hypot(rg.mean(), yb.mean())), 2)
    out["chroma"] = round(float(np.hypot(a, b).mean()), 2)
    out["palette"] = palette(rgb, 3)
    return out


def words(S: dict) -> list[str]:
    """The look in words, from a shot's or the video's numbers (brightness etc. in %, a* / b* in Lab units)."""
    if S.get("bw"):
        w = ["black & white"]
    else:
        w = []
        b, a = S.get("warmth"), S.get("tint")
        if b is not None and b > 6:
            w.append("warm")
        elif b is not None and b < -4:
            w.append("cool")
        if a is not None and a > 5:
            w.append("magenta tint")
        elif a is not None and a < -5:
            w.append("green tint")
        sh, hi = S.get("shadows"), S.get("highlights")
        if sh and hi and sh[1] < -1.5 and sh[0] < 3 and hi[1] > 4 and hi[0] > -3:   # blue-green shadows, warm lights
            w.append("teal & orange")
        s = S.get("saturation")
        if s is not None and s < 18:
            w.append("desaturated")
        elif s is not None and s > 48:
            w.append("saturated")
    br, c = S.get("brightness"), S.get("contrast")
    if br is not None and br < 28:
        w.append("dark (low-key)")
    elif br is not None and br > 66:
        w.append("bright (high-key)")
    if c is not None and c > 78:
        w.append("high contrast")
    elif c is not None and c < 45:
        w.append("low contrast")
    if (S.get("black") or 0) > 9:
        w.append("lifted blacks")
    elif S.get("black") is not None and S["black"] < 1.0:
        w.append("crushed blacks")
    if S.get("white") is not None and S["white"] < 78:
        w.append("soft highlights")
    if S.get("vignette") is not None and S["vignette"] < 0.8:
        w.append("vignette")
    if S.get("letterbox"):
        w.append(f"letterbox {S['letterbox']}")
    return w


def grade(S: dict) -> dict:
    """A starting grade for the lab's compositor (compose.grade_lut + saturation, + a per-channel tint for clip
    layers): levels from the black / white level, gamma from the brightness, saturation relative to footage as shot,
    a tint from the warmth / tint. Rough by design - the match LUT (match_lut) is the exact one."""
    blk, wht = S.get("black") or TYPICAL["black"], S.get("white") or TYPICAL["white"]
    br = max(5.0, min(90.0, S.get("brightness") or TYPICAL["brightness"]))
    g = {"black": 0, "white": 255,
         "gamma": round(max(0.75, min(1.5, math.log(br / 100) / math.log(TYPICAL["brightness"] / 100))), 3),
         "out_black": round(max(0.0, min(0.15, (blk - TYPICAL["black"]) / 100)), 3),
         "out_white": round(max(0.78, min(1.0, wht / 100 + 0.05)), 3),
         "saturation": 0.0 if S.get("bw") else round(max(0.2, min(1.5, (S.get("saturation") or 32) / 32)), 3)}
    if (S.get("contrast") or 0) > 80:
        g["black"], g["white"] = 8, 245
    b, a = S.get("warmth") or 0.0, S.get("tint") or 0.0
    if not S.get("bw") and (abs(b) > 3 or abs(a) > 3):
        g["tint"] = [round(max(0.85, min(1.15, 1 + 0.006 * b + 0.003 * a)), 3),
                     round(max(0.85, min(1.15, 1 - 0.004 * a)), 3),
                     round(max(0.85, min(1.15, 1 - 0.008 * b)), 3)]
    return g


def line(S: dict) -> str:
    w = words(S)
    return ("look: " + ", ".join(w)) if w else "look: natural"


def analyse(name: str, log=None) -> dict | None:
    """Measure the colour of analysis\\<name> and write colour\\colour.json (None when there is nothing to measure)."""
    d = ANALYSIS / name
    evp = d / "events.json"
    if not evp.exists():
        return None
    ev = read_json(evp)
    v = ev.get("video") or {}
    fps = float(v.get("fps") or 25)
    try:
        z = np.load(d / "cache" / "metrics.npz")
        M = {k: np.asarray(z[k], float) for k in z.files}
    except (OSError, ValueError):
        M = _metrics_csv(d / "metrics.csv")
    if not M or "luma_mean" not in M:
        return None
    n = len(M["luma_mean"])
    thumbs = None
    meta = read_json(d / "cache" / "meta.json") if (d / "cache" / "meta.json").exists() else None
    if meta and (d / "cache" / "thumbs.u8").exists():
        try:
            thumbs = np.memmap(d / "cache" / "thumbs.u8", dtype=np.uint8, mode="r",
                               shape=(meta["n_frames"], meta["thumb_h"], meta["thumb_w"], 3))
        except (OSError, ValueError, KeyError):
            thumbs = None
    shots = ev.get("shots") or [{"start": 0, "frames": n}]
    get = lambda k, idx: float(np.nanmedian(M[k][idx])) if k in M and len(idx) else None  # noqa: E731
    out_shots, pooled = [], []
    for sh in shots:
        s, L = int(sh["start"]), int(sh.get("frames") or 0)
        e = min(n - 1, s + L - 1)
        if e < s:
            continue
        a0, a1 = (s + 2, e - 2) if e - s >= 8 else (s, e)
        idx = np.unique(np.linspace(a0, a1, min(5, a1 - a0 + 1)).round().astype(int))
        S = {"start": s, "end": e, "frames": e - s + 1,
             "brightness": get("luma_mean", idx), "black": get("luma_p05", idx), "white": get("luma_p95", idx),
             "saturation": get("sat_mean", idx), "tint": get("lab_a", idx), "warmth": get("lab_b", idx)}
        if S["black"] is not None and S["white"] is not None:
            S["contrast"] = round(S["white"] - S["black"], 2)
        bars = [get(k, idx) or 0.0 for k in ("bar_top", "bar_bottom")]
        S["bars"] = round(sum(bars), 3)
        if thumbs is not None and idx.max() < len(thumbs):
            T = np.asarray(thumbs[idx])
            if S["bars"] > 0.04:                           # measure the picture, not the black bars
                hh = T.shape[1]
                t0, t1 = int(round(bars[0] * hh)), hh - int(round(bars[1] * hh))
                if t1 - t0 >= 4:
                    T = T[:, t0:t1]
            S.update(_shot_look(T))
            pooled.append(T[..., ::-1].reshape(-1, 3))
        S["bw"] = bool((S.get("saturation") or 100) < 5 and (S.get("chroma") or 0) < 4)
        S = {k: (round(x, 2) if isinstance(x, float) else x) for k, x in S.items()}
        S["words"] = words(S)
        out_shots.append(S)
    if not out_shots:
        return None
    wts = [x["frames"] for x in out_shots]
    summ = {k: (round(_wmedian([x.get(k) for x in out_shots], wts), 2)
                if any(x.get(k) is not None for x in out_shots) else None)
            for k in ("brightness", "black", "white", "contrast", "saturation", "tint", "warmth", "vignette",
                      "colourfulness", "chroma")}
    for key in ("shadows", "highlights"):
        pts = [(x[key], x["frames"]) for x in out_shots if x.get(key)]
        if pts:
            summ[key] = [round(_wmedian([p[0][i] for p in pts], [p[1] for p in pts]), 2) for i in (0, 1)]
    summ["bw"] = sum(x["frames"] for x in out_shots if x["bw"]) > 0.7 * sum(wts)
    lb = sum(x["frames"] for x in out_shots if x["bars"] >= 0.08) / sum(wts)
    if lb >= 0.6:
        bars = _wmedian([x["bars"] for x in out_shots], wts) or 0
        W, H = v.get("display_width") or v.get("width") or 16, v.get("display_height") or v.get("height") or 9
        ar = W / max(1.0, H * (1 - bars))
        summ["letterbox"] = f"{ar:.2f}:1"
    summ["consistency"] = {"brightness_spread": _wstd([x.get("brightness") for x in out_shots], wts),
                           "warmth_spread": _wstd([x.get("warmth") for x in out_shots], wts)}
    sp = summ["consistency"]
    summ["consistent"] = bool((sp["brightness_spread"] or 0) < 12 and (sp["warmth_spread"] or 0) < 6)
    if pooled:
        allpx = np.concatenate(pooled)
        summ["lab"] = lab_stats(allpx)
        summ["palette"] = palette(allpx, 5)
    summ["words"] = words(summ)
    summ["line"] = line(summ) + ("" if summ["consistent"] or len(out_shots) < 3 else " · changes from shot to shot")
    summ["grade"] = grade(summ)
    data = {"schema": SCHEMA, "name": name, "fps": fps, "shots": out_shots, "summary": summ,
            "made_from": "metrics + thumbnails" if thumbs is not None else "metrics only (the cache was pruned)"}
    (d / "colour").mkdir(exist_ok=True)
    write_json(d / "colour" / "colour.json", data)
    if log:
        log(f"colour: {summ['line']}")
    return data


def _metrics_csv(p: Path) -> dict:
    import csv
    if not p.exists():
        return {}
    with open(p, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        cols: dict = {}
        for row in r:
            for k in ("luma_mean", "luma_p05", "luma_p95", "sat_mean", "lab_a", "lab_b", "bar_top", "bar_bottom"):
                try:
                    cols.setdefault(k, []).append(float(row.get(k) or "nan"))
                except ValueError:
                    cols.setdefault(k, []).append(float("nan"))
    return {k: np.asarray(v, float) for k, v in cols.items()}


# ------------------------------------------------------------------------------------------------ matching
def match_lut(src: dict, ref: dict, size: int = 33, strength: float = 1.0) -> np.ndarray:
    """(size, size, size, 3) float RGB 0..1, indexed [r, g, b]: Reinhard transfer in Lab from the footage's look
    (src = lab_stats) toward the reference's (ref); strength < 1 = part of the way."""
    g = np.linspace(0, 1, size, dtype=np.float32)
    R, G, B = np.meshgrid(g, g, g, indexing="ij")
    rgb = np.stack([R, G, B], axis=-1)
    lab = cv2.cvtColor(rgb.reshape(-1, 1, 3), cv2.COLOR_RGB2LAB).reshape(-1, 3)
    ms, ss = np.asarray(src["mean"], np.float32), np.maximum(np.asarray(src["std"], np.float32), 1e-3)
    mr, sr = np.asarray(ref["mean"], np.float32), np.asarray(ref["std"], np.float32)
    k = np.clip(sr / ss, 0.4, 2.5)                     # no extreme stretches from a near-flat channel
    moved = (lab - ms) * k + mr
    moved = lab + (moved - lab) * float(strength)
    moved[:, 0] = np.clip(moved[:, 0], 0, 100)
    out = cv2.cvtColor(moved.reshape(-1, 1, 3).astype(np.float32), cv2.COLOR_LAB2RGB).reshape(size, size, size, 3)
    return np.clip(out, 0, 1)


def apply_lut(rgb_u8: np.ndarray, lut: np.ndarray) -> np.ndarray:
    """A 3D LUT (match_lut) on uint8 RGB pictures, trilinear."""
    n = lut.shape[0] - 1
    x = rgb_u8.reshape(-1, 3).astype(np.float32) / 255.0 * n
    i0 = np.clip(np.floor(x).astype(int), 0, n - 1)
    f = x - i0
    out = np.zeros_like(x)
    for dr in (0, 1):
        for dg in (0, 1):
            for db in (0, 1):
                w = (f[:, 0] if dr else 1 - f[:, 0]) * (f[:, 1] if dg else 1 - f[:, 1]) * (f[:, 2] if db else 1 - f[:, 2])
                out += w[:, None] * lut[i0[:, 0] + dr, i0[:, 1] + dg, i0[:, 2] + db]
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8).reshape(rgb_u8.shape)


def closeness(a: dict, b: dict) -> float:
    """How near two looks are, 0..100: 100 - 2.5 x (the distance of their mean Lab colours + of their spreads)."""
    ma, mb = np.asarray(a["mean"], float), np.asarray(b["mean"], float)
    sa, sb = np.asarray(a["std"], float), np.asarray(b["std"], float)
    d = float(np.linalg.norm(ma - mb) + 0.5 * np.linalg.norm(sa - sb))
    return round(max(0.0, 100.0 - 2.5 * d), 1)


def write_cube(path: Path, lut: np.ndarray, title: str) -> Path:
    """A 3D LUT as a .cube file (DaVinci Resolve, most editors): red changes fastest."""
    n = lut.shape[0]
    lines = [f'TITLE "{title[:60]}"', f"LUT_3D_SIZE {n}", "DOMAIN_MIN 0 0 0", "DOMAIN_MAX 1 1 1"]
    for b in range(n):
        for g in range(n):
            for r in range(n):
                c = lut[r, g, b]
                lines.append(f"{c[0]:.6f} {c[1]:.6f} {c[2]:.6f}")
    path.write_text("\n".join(lines) + "\n", encoding="ascii")
    return path


def read_cube(path: Path) -> np.ndarray:
    """A .cube file -> (n, n, n, 3) indexed [r, g, b]."""
    n, vals = None, []
    for ln in Path(path).read_text(encoding="ascii", errors="replace").splitlines():
        ln = ln.strip()
        if ln.startswith("LUT_3D_SIZE"):
            n = int(ln.split()[1])
        elif ln and (ln[0].isdigit() or ln[0] in "-."):
            vals.append([float(x) for x in ln.split()[:3]])
    if not n or len(vals) != n ** 3:
        raise ValueError(f"not a 3D .cube: {path}")
    return np.asarray(vals, np.float32).reshape(n, n, n, 3).transpose(2, 1, 0, 3)
