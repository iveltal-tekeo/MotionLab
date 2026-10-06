"""Frame compositor for MotionLab renders: a plan (layers on a timeline) -> RGB frames.

Coordinates are output pixels (x right, y down); frames are 0-based at plan["fps"]; ranges are inclusive.
Layer types: clip, solid, text, clock, mosaic, firework, streaks, strip.
Animated values ("curves") are a number, {"keys": [[f, v, ease], ...]}, {"start": f0, "values": [...]} or
"@name" for a curve defined once in plan["curves"]. Eases (for the segment after a key): hold, linear,
smooth (S-curve), in (accelerating / slow start), out (decelerating / slow end).
Clip sources are the grey frame caches written by tools/prep_footage.py (full range, cover-fit at 1x).
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np

from . import graphics as G

# ------------------------------------------------------------------------------------------------ curves
EASES = {
    "hold": lambda t: 0.0,
    "linear": lambda t: t,
    "smooth": lambda t: t * t * (3 - 2 * t),
    "in": lambda t: t * t,
    "out": lambda t: 1 - (1 - t) * (1 - t),
    "in3": lambda t: t * t * t,
    "out3": lambda t: 1 - (1 - t) ** 3,
}


class Curve:
    def __init__(self, spec, named: dict | None = None, default: float = 0.0):
        if isinstance(spec, str) and spec.startswith("@"):
            spec = (named or {})[spec[1:]]
        self.const = None
        self.keys = None
        self.vals = None
        if spec is None:
            self.const = float(default)
        elif isinstance(spec, (int, float)):
            self.const = float(spec)
        elif "keys" in spec:
            ks = sorted(spec["keys"], key=lambda k: k[0])
            self.kf = np.array([k[0] for k in ks], float)
            self.kv = np.array([k[1] for k in ks], float)
            self.ke = [k[2] if len(k) > 2 else "linear" for k in ks]
            self.keys = True
        elif "values" in spec:
            self.f0 = int(spec["start"])
            self.vals = np.asarray(spec["values"], float)
        else:
            raise ValueError(f"bad curve spec: {spec}")
        self.scale = float(spec.get("scale", 1.0)) if isinstance(spec, dict) else 1.0
        self.offset = float(spec.get("offset", 0.0)) if isinstance(spec, dict) else 0.0

    def __call__(self, f: float) -> float:
        if self.const is not None:
            return self.const
        if self.vals is not None:
            i = int(round(f)) - self.f0
            v = self.vals[min(max(i, 0), len(self.vals) - 1)]
        else:
            kf, kv = self.kf, self.kv
            if f <= kf[0]:
                v = kv[0]
            elif f >= kf[-1]:
                v = kv[-1]
            else:
                i = int(np.searchsorted(kf, f, side="right")) - 1
                t = (f - kf[i]) / max(1e-9, kf[i + 1] - kf[i])
                v = kv[i] + (kv[i + 1] - kv[i]) * EASES[self.ke[i]](t)
        return float(v) * self.scale + self.offset


# ------------------------------------------------------------------------------------------------ levels
TV_TO_FULL = np.clip((np.arange(256) - 16) * 255.0 / 219.0, 0, 255).round().astype(np.uint8)
FULL_TO_TV = np.clip(np.arange(256) * 219.0 / 255.0 + 16, 0, 255).round().astype(np.uint8)


def cache_levels(cache_path) -> str:
    """'single' for caches marked by prep_footage since 2026-10-06, else 'double' (older caches expanded video range
    a second time after ffmpeg's format=gray had already expanded it)."""
    import json
    meta = Path(cache_path).with_suffix(".json")
    try:
        return "single" if json.loads(meta.read_text(encoding="utf-8")).get("levels") == "single" else "double"
    except (OSError, ValueError):
        return "double"


def level_conversion(cache: str, plan: str):
    """256-entry table that turns cache values into the levels a plan expects (None = use as is)."""
    if cache == plan:
        return None
    return TV_TO_FULL if plan == "double" else FULL_TO_TV      # FULL_TO_TV only approximates (rounding)


# ------------------------------------------------------------------------------------------------ grading
def grade_lut(black=40, white=245, gamma=1.5, out_black=0.03, out_white=0.85) -> np.ndarray:
    """uint8 grey -> float32 0..1: levels (black/white input points), gamma (>1 darker mids), output range."""
    x = np.clip((np.arange(256, dtype=np.float32) - black) / max(1.0, white - black), 0, 1)
    return (out_black + (out_white - out_black) * x ** gamma).astype(np.float32)


def _cover(w: float, h: float, sw: int, sh: int) -> tuple[float, float]:
    ar = w / h
    return (sh * ar, float(sh)) if sw / sh > ar else (float(sw), sw / ar)


def sample_patch(src: np.ndarray, lut: np.ndarray, x: float, y: float, w: float, h: float, zoom: float,
                 ax: float, ay: float, W: int, H: int, mirror: bool = False):
    """Render the cover-fit crop of `src` (zoom >= 1 around anchor ax, ay in 0..1) into the output-pixel box
    (x, y, w, h). Returns (patch float32, coverage float32, X0, Y0) clipped to the W x H frame, or None."""
    Xa, Xb = max(0, int(math.floor(x))), min(W, int(math.ceil(x + w)))
    Ya, Yb = max(0, int(math.floor(y))), min(H, int(math.ceil(y + h)))
    if Xb <= Xa or Yb <= Ya:
        return None
    sh, sw = src.shape[:2]
    cw, ch = _cover(w, h, sw, sh)
    cw, ch = cw / zoom, ch / zoom
    cx = min(max(ax * sw, cw / 2), sw - cw / 2)
    cy = min(max(ay * sh, ch / 2), sh - ch / 2)
    sx, sy = cw / w, ch / h                                # source px per output px
    # source coordinates of the visible output columns / rows
    gx0 = cx - cw / 2 + ((Xa + 0.5 - x) / w) * cw - 0.5
    gx1 = cx - cw / 2 + ((Xb - 0.5 - x) / w) * cw - 0.5
    gy0 = cy - ch / 2 + ((Ya + 0.5 - y) / h) * ch - 0.5
    gy1 = cy - ch / 2 + ((Yb - 0.5 - y) / h) * ch - 0.5
    ox, oy = max(0, int(math.floor(min(gx0, gx1))) - 2), max(0, int(math.floor(gy0)) - 2)
    ex, ey = min(sw, int(math.ceil(max(gx0, gx1))) + 3), min(sh, int(math.ceil(gy1)) + 3)
    crop = lut[src[oy:ey, ox:ex]]
    q = 1.0
    if sx > 1.3 or sy > 1.3:                               # pre-reduce with area averaging (no aliasing)
        q = max(1.0, min(sx, sy) * 0.9)
        crop = cv2.resize(crop, (max(1, int(round(crop.shape[1] / q))), max(1, int(round(crop.shape[0] / q)))),
                          interpolation=cv2.INTER_AREA)
        qx, qy = (ex - ox) / crop.shape[1], (ey - oy) / crop.shape[0]
    else:
        qx = qy = 1.0
    A = sx / qx
    D = sy / qy
    B = (gx0 - ox + 0.5) / qx - 0.5
    E = (gy0 - oy + 0.5) / qy - 0.5
    if mirror:
        A, B = -A, (gx1 - ox + 0.5) / qx - 0.5
    M = np.array([[A, 0, B], [0, D, E]], np.float32)
    interp = cv2.INTER_CUBIC if max(A, D) < 0.8 else cv2.INTER_LINEAR
    patch = cv2.warpAffine(crop, M, (Xb - Xa, Yb - Ya), flags=interp | cv2.WARP_INVERSE_MAP,
                           borderMode=cv2.BORDER_REPLICATE)
    cov_x = np.clip(np.minimum(np.arange(Xa, Xb) + 1.0, x + w) - np.maximum(np.arange(Xa, Xb), x), 0, 1)
    cov_y = np.clip(np.minimum(np.arange(Ya, Yb) + 1.0, y + h) - np.maximum(np.arange(Ya, Yb), y), 0, 1)
    cov = np.outer(cov_y, cov_x).astype(np.float32)
    return np.clip(patch, 0, 1.5), cov, Xa, Ya


def blend(canvas: np.ndarray, patch: np.ndarray, alpha: np.ndarray, X0: int, Y0: int, mode: str = "normal",
          color=None):
    """Composite a grey (h, w) or RGB (h, w, 3) patch with per-pixel alpha into the float RGB canvas."""
    h, w = alpha.shape
    reg = canvas[Y0:Y0 + h, X0:X0 + w]
    p = patch if patch.ndim == 3 else patch[..., None]
    if color is not None:
        p = p * np.asarray(color, np.float32)
    a = alpha[..., None]
    if mode == "normal":
        reg *= (1 - a)
        reg += p * a
    elif mode == "screen":
        reg[:] = 1 - (1 - reg) * (1 - np.clip(p, 0, 1) * a)
    elif mode == "add":
        reg += p * a
    elif mode == "lighten":
        reg[:] = np.maximum(reg, reg * (1 - a) + p * a)
    else:
        raise ValueError(mode)


# ------------------------------------------------------------------------------------------------ layers
class Layer:
    def __init__(self, spec: dict, R: "Renderer"):
        self.spec = spec
        self.id = spec.get("id", spec["type"])
        self.start, self.end = int(spec["start"]), int(spec["end"])
        self.opacity = Curve(spec.get("opacity"), R.curves, 1.0)
        self.mode = spec.get("blend", "normal")

    def active(self, f: int) -> bool:
        return self.start <= f <= self.end

    def draw(self, canvas: np.ndarray, f: int, R: "Renderer"):
        raise NotImplementedError


class ClipLayer(Layer):
    """A video panel (or still with "hold") from a cached source, placed in rect [x, y, w, h]."""

    def __init__(self, spec, R):
        super().__init__(spec, R)
        self.src = spec["src"]
        self.rect = [float(v) for v in spec["rect"]]
        self.dx = Curve(spec.get("dx"), R.curves, 0.0)
        self.dy = Curve(spec.get("dy"), R.curves, 0.0)
        self.zoom = Curve(spec.get("zoom"), R.curves, 1.0)
        an = spec.get("anchor", [0.5, 0.5])
        self.ax = Curve(an[0], R.curves, 0.5)
        self.ay = Curve(an[1], R.curves, 0.5)
        self.gain = Curve(spec.get("gain"), R.curves, 1.0)
        g = {**R.grades.get(spec.get("grade", "default"), {}), **spec.get("grade_override", {})}
        self.lut = grade_lut(**g) if g else grade_lut()
        self.speed = float(spec.get("speed", 1.0))
        self.hold = bool(spec.get("hold", False))
        self.jumps = sorted([[int(a), int(b)] for a, b in spec.get("jumps", [[self.start, spec.get("in", 0)]])])
        self.flash_over = {int(k): float(v) for k, v in spec.get("flash_over", {}).items()}
        self.flash_white = set(int(v) for v in spec.get("flash_white", []))
        self.black = set(int(v) for v in spec.get("black", []))
        self.mirror = bool(spec.get("mirror", False))
        self.tint = spec.get("tint")

    def src_index(self, f: int) -> int:
        j = self.jumps[0]
        for jj in self.jumps:
            if jj[0] <= f:
                j = jj
        return j[1] if self.hold else j[1] + int(math.floor((f - j[0]) * self.speed + 1e-6))

    def draw(self, canvas, f, R):
        op = self.opacity(f)
        if op <= 0.002:
            return
        x, y, w, h = self.rect
        x += self.dx(f)
        y += self.dy(f)
        if f in self.black:
            out = sample_box(x, y, w, h, R.W, R.H)
            if out:
                cov, X0, Y0 = out
                blend(canvas, np.full(cov.shape, R.bg, np.float32), cov * op, X0, Y0)
            return
        src = R.frame(self.src, self.src_index(f))
        res = sample_patch(src, self.lut, x, y, w, h, self.zoom(f), self.ax(f), self.ay(f), R.W, R.H, self.mirror)
        if res is None:
            return
        patch, cov, X0, Y0 = res
        g = self.gain(f)
        if g != 1.0:
            patch = patch * g
        if f in self.flash_over:                                # over-exposed flash frame (image still visible)
            k = self.flash_over[f]
            patch = patch + k * (1.0 - np.clip(patch, 0, 1))
        if f in self.flash_white:                               # flat white frame (a trace of the image left)
            patch = 0.86 + 0.06 * patch
        blend(canvas, patch, cov * op, X0, Y0, self.mode, self.tint)


def sample_box(x, y, w, h, W, H):
    Xa, Xb = max(0, int(math.floor(x))), min(W, int(math.ceil(x + w)))
    Ya, Yb = max(0, int(math.floor(y))), min(H, int(math.ceil(y + h)))
    if Xb <= Xa or Yb <= Ya:
        return None
    cov_x = np.clip(np.minimum(np.arange(Xa, Xb) + 1.0, x + w) - np.maximum(np.arange(Xa, Xb), x), 0, 1)
    cov_y = np.clip(np.minimum(np.arange(Ya, Yb) + 1.0, y + h) - np.maximum(np.arange(Ya, Yb), y), 0, 1)
    return np.outer(cov_y, cov_x).astype(np.float32), Xa, Ya


class SolidLayer(Layer):
    """Flat colour rectangle or circle (white flash frames, black frames, black circles)."""

    def __init__(self, spec, R):
        super().__init__(spec, R)
        self.rect = [float(v) for v in spec.get("rect", [0, 0, R.W, R.H])]
        self.dx = Curve(spec.get("dx"), R.curves, 0.0)
        self.color = np.asarray(spec.get("color", [1, 1, 1]), np.float32).reshape(-1)
        if self.color.size == 1:
            self.color = np.repeat(self.color, 3)
        self.frames = set(int(v) for v in spec["frames"]) if "frames" in spec else None
        self.shape = spec.get("shape", "rect")

    def draw(self, canvas, f, R):
        if self.frames is not None and f not in self.frames:
            return
        op = self.opacity(f)
        if op <= 0.002:
            return
        x, y, w, h = self.rect
        x += self.dx(f)
        out = sample_box(x, y, w, h, R.W, R.H)
        if not out:
            return
        cov, X0, Y0 = out
        if self.shape == "circle":
            hh, ww = cov.shape
            yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
            cx, cy, r = x + w / 2 - X0, y + h / 2 - Y0, min(w, h) / 2
            d = np.sqrt((xx + 0.5 - cx) ** 2 + (yy + 0.5 - cy) ** 2)
            cov = cov * np.clip(r - d + 0.5, 0, 1)
        blend(canvas, np.ones(cov.shape, np.float32), cov * op, X0, Y0, self.mode, self.color)


def _glow_composite(canvas, mask, X0, Y0, color, glow, sigma, op, R, mode="normal"):
    pad = int(math.ceil(sigma * 3)) if glow > 0 else 0
    if pad:
        m = np.pad(mask, pad)
        g = cv2.GaussianBlur(m, (0, 0), sigma) * glow
        X, Y = X0 - pad, Y0 - pad
    else:
        m, g, X, Y = mask, None, X0, Y0
    h, w = m.shape
    xa, ya = max(0, -X), max(0, -Y)
    xb, yb = min(w, R.W - X), min(h, R.H - Y)
    if xb <= xa or yb <= ya:
        return
    sl = (slice(ya, yb), slice(xa, xb))
    col = np.asarray(color, np.float32)
    if g is not None:
        blend(canvas, g[sl], np.full((yb - ya, xb - xa), op, np.float32), X + xa, Y + ya, "add", col)
    blend(canvas, np.ones((yb - ya, xb - xa), np.float32), m[sl] * op, X + xa, Y + ya, mode, col)


class TextLayer(Layer):
    """Boxy pixel-font text (the title-card look), optional glow and a thin rectangle frame around it."""

    def __init__(self, spec, R):
        super().__init__(spec, R)
        self.mask = G.text_mask(spec["text"], float(spec.get("height", 34)), spec.get("stroke"),
                                float(spec.get("tracking", 0.55)), width_scale=float(spec.get("width_scale", 1.0)))
        self.cx = Curve(spec.get("cx", R.W / 2), R.curves)
        self.cy = Curve(spec.get("cy", R.H / 2), R.curves)
        self.color = spec.get("color", [0.85, 0.05, 0.05])
        self.glow = float(spec.get("glow", 0.0))
        self.sigma = float(spec.get("glow_sigma", spec.get("height", 34) * 0.18))
        self.box = spec.get("box")                             # {"pad": [px, py], "color": [...], "width": 2, "glow": 1}

    def draw(self, canvas, f, R):
        op = self.opacity(f)
        if op <= 0.002:
            return
        h, w = self.mask.shape
        X0, Y0 = int(round(self.cx(f) - w / 2)), int(round(self.cy(f) - h / 2))
        if self.box:
            px, py = self.box.get("pad", [60, 40])
            bw, bh = w + 2 * px, h + 2 * py
            bm = np.zeros((bh, bw), np.float32)
            lw = int(self.box.get("width", 2))
            cv2.rectangle(bm, (0, 0), (bw - 1, bh - 1), 1.0, lw)
            _glow_composite(canvas, bm * float(self.box.get("strength", 0.35)), X0 - px, Y0 - py,
                            self.box.get("color", self.color), float(self.box.get("glow", 1.2)),
                            float(self.box.get("sigma", 10)), op, R)
        _glow_composite(canvas, self.mask, X0, Y0, self.color, self.glow, self.sigma, op, R)


class ClockLayer(Layer):
    """Seven-segment clock. style "grey" (grainy, beveled) or "red" (LED, glow, red vignette)."""

    def __init__(self, spec, R):
        super().__init__(spec, R)
        self.texts = sorted([[int(a), b] for a, b in spec["texts"]])
        self.height = float(spec.get("height", 300))
        self.cx = Curve(spec.get("cx", R.W / 2), R.curves)
        self.cy = Curve(spec.get("cy", R.H / 2), R.curves)
        self.style = spec.get("style", "grey")
        self.color = spec.get("color", [0.74, 0.74, 0.74] if self.style == "grey" else [0.92, 0.05, 0.03])
        self.dim_frames = {int(k): v for k, v in spec.get("dim", {}).items()}   # f -> [[char, seg, level], ...]
        self.grain = float(spec.get("grain", 0.22 if self.style == "grey" else 0.04))
        self.glow = float(spec.get("glow", 0.0 if self.style == "grey" else 1.1))
        self.vignette = spec.get("vignette")                   # [r, g, b] centre colour of a soft background glow
        self.flash_over = {int(k): float(v) for k, v in spec.get("flash_over", {}).items()}
        self.width_ratio = float(spec.get("width_ratio", 0.56))
        self._cache = {}

    def text_at(self, f):
        t = self.texts[0][1]
        for a, b in self.texts:
            if a <= f:
                t = b
        return t

    def mask(self, f):
        text = self.text_at(f)
        dims = self.dim_frames.get(f)
        key = (text, tuple(tuple(d) for d in dims) if dims else None)
        if key not in self._cache:
            dim = {(int(c), s): float(l) for c, s, l in dims} if dims else None
            style = "bevel" if self.style == "grey" else "rect"
            th = 0.15 if self.style == "grey" else 0.13
            self._cache[key] = G.seg_mask(text, self.height, style, dim, thickness=th, width_ratio=self.width_ratio)
        return self._cache[key]

    def draw(self, canvas, f, R):
        op = self.opacity(f)
        if op <= 0.002:
            return
        m = self.mask(f)
        if self.grain:
            noise = R.rng.normal(1.0, self.grain, m.shape).astype(np.float32)
            noise = cv2.GaussianBlur(noise, (0, 0), 0.8)
            m = np.clip(m * noise, 0, 1.2)
        if f in self.flash_over:
            m = np.clip(m + self.flash_over[f] * (m > 0.05), 0, 1.6)
        h, w = m.shape
        X0, Y0 = int(round(self.cx(f) - w / 2)), int(round(self.cy(f) - h / 2))
        if self.vignette:
            vg = R.vignette(tuple(self.vignette))
            blend(canvas, vg, np.full(vg.shape[:2], op, np.float32), 0, 0, "add")
        _glow_composite(canvas, m, X0, Y0, self.color, self.glow, self.height * 0.07, op, R)


class FireworkLayer(Layer):
    def __init__(self, spec, R):
        super().__init__(spec, R)
        self.cx, self.cy = float(spec["center"][0]), float(spec["center"][1])
        self.dx = Curve(spec.get("dx"), R.curves, 0.0)
        self.size = int(spec.get("size", 520))
        self.life = int(spec.get("life", 45))
        self.seed = int(spec.get("seed", 1))
        self.gain = float(spec.get("gain", 1.0))

    def draw(self, canvas, f, R):
        t = (f - self.start) / self.life
        if t < 0 or t > 1:
            return
        img = np.clip(G.firework(self.size, t, self.seed) * self.gain * self.opacity(f), 0, 1)
        X0 = int(round(self.cx + self.dx(f) - self.size / 2))
        Y0 = int(round(self.cy - self.size / 2))
        xa, ya = max(0, -X0), max(0, -Y0)
        xb, yb = min(self.size, R.W - X0), min(self.size, R.H - Y0)
        if xb > xa and yb > ya:
            blend(canvas, img[ya:yb, xa:xb], np.ones((yb - ya, xb - xa), np.float32), X0 + xa, Y0 + ya, "screen")


class StreaksLayer(Layer):
    def __init__(self, spec, R):
        super().__init__(spec, R)
        self.seed = int(spec.get("seed", 5))
        self.strength = float(spec.get("strength", 0.6))

    def draw(self, canvas, f, R):
        img = G.streaks(R.W, R.H, self.seed + f, strength=self.strength * self.opacity(f))
        blend(canvas, img, np.ones(img.shape, np.float32), 0, 0, "screen")


class StripLayer(Layer):
    """A horizontal strip of small photo tiles (a graphic border), built once."""

    def __init__(self, spec, R):
        super().__init__(spec, R)
        self.rect = [float(v) for v in spec["rect"]]
        self.dx = Curve(spec.get("dx"), R.curves, 0.0)
        x, y, w, h = self.rect
        tw = float(spec.get("tile_w", h * 1.4))
        gap = float(spec.get("gap", 2))
        lut = grade_lut(**R.grades.get(spec.get("grade", "default"), {}))
        img = np.full((int(round(h)), int(round(w))), R.bg, np.float32)
        tiles = spec["tiles"]
        n = int(math.ceil(w / tw))
        for i in range(n):
            t = tiles[i % len(tiles)]
            src = R.frame(t["src"], int(t["frame"]))
            res = sample_patch(src, lut, i * tw, 0, tw - gap, h, float(t.get("zoom", 1.0)), t.get("ax", 0.5),
                               t.get("ay", 0.5), img.shape[1], img.shape[0])
            if res:
                p, cov, X0, Y0 = res
                reg = img[Y0:Y0 + p.shape[0], X0:X0 + p.shape[1]]
                reg[:] = reg * (1 - cov) + p * cov
        self.img = img * float(spec.get("gain", 1.0))

    def draw(self, canvas, f, R):
        x, y, w, h = self.rect
        x += self.dx(f)
        X0, Y0 = int(round(x)), int(round(y))
        hh, ww = self.img.shape
        xa, ya = max(0, -X0), max(0, -Y0)
        xb, yb = min(ww, R.W - X0), min(hh, R.H - Y0)
        if xb > xa and yb > ya:
            blend(canvas, self.img[ya:yb, xa:xb], np.full((yb - ya, xb - xa), self.opacity(f), np.float32),
                  X0 + xa, Y0 + ya)


class MosaicLayer(Layer):
    """A big picture made of tiles (photos + one clock tile) seen through a zoom: scale s(f) (screen px per
    mosaic px) about the anchor tile, whose centre sits at screen point (ax(f), ay(f)). Rendered from
    pre-built level canvases (sqrt(2) steps) so every frame is a smooth sub-pixel warp."""

    def __init__(self, spec, R):
        super().__init__(spec, R)
        self.tiles = spec["tiles"]
        self.tw, self.th = float(spec["tile_w"]), float(spec["tile_h"])
        self.gap = float(spec.get("gap", 4))
        self.scale = Curve(spec["scale"], R.curves, 1.0)
        self.sax = Curve(spec.get("screen_ax", R.W / 2), R.curves)
        self.say = Curve(spec.get("screen_ay", R.H / 2), R.curves)
        at = self.tiles[int(spec["anchor_tile"])]
        self.mc = (at["x"] + self.tw / 2, at["y"] + self.th / 2)
        self.lut = grade_lut(**R.grades.get(spec.get("grade", "default"), {}))
        self.tile_gain = float(spec.get("tile_gain", 1.0))
        self.clock = spec.get("clock", {"text": "4:00", "fit": 0.94, "color": [0.74, 0.74, 0.74]})
        self.twinkle = {int(k): int(v) for k, v in spec.get("twinkle", {}).items()}
        self.red = set(int(v) for v in spec.get("red", []))
        self.blackf = set(int(v) for v in spec.get("black", []))
        self.levels = {}
        self._build(R)

    def _visible(self, f, R):
        s = self.scale(f)
        ax, ay = self.sax(f), self.say(f)
        return s, (self.mc[0] - ax / s, self.mc[1] - ay / s, self.mc[0] + (R.W - ax) / s, self.mc[1] + (R.H - ay) / s)

    def _level_of(self, s):
        k = max(0, int(math.ceil(math.log(max(s, 1e-6), math.sqrt(2)) - 1e-9)))
        return k, math.sqrt(2) ** k

    def _build(self, R):
        bounds = {}
        for f in range(self.start, self.end + 1):
            s, (x0, y0, x1, y1) = self._visible(f, R)
            k, _ = self._level_of(s)
            b = bounds.get(k)
            bounds[k] = (x0, y0, x1, y1) if b is None else (min(b[0], x0), min(b[1], y0), max(b[2], x1), max(b[3], y1))
        for k, (x0, y0, x1, y1) in bounds.items():
            L = math.sqrt(2) ** k
            m = 2.0 / L
            x0, y0, x1, y1 = x0 - m, y0 - m, x1 + m, y1 + m
            cw, ch = int(math.ceil((x1 - x0) * L)), int(math.ceil((y1 - y0) * L))
            can = np.full((ch, cw), R.bg, np.float32)
            rects = []
            for i, t in enumerate(self.tiles):
                tx, ty = (t["x"] - x0) * L, (t["y"] - y0) * L
                tw, th = (self.tw - self.gap) * L, (self.th - self.gap) * L
                rects.append((tx, ty, tw, th))
                if tx > cw or ty > ch or tx + tw < 0 or ty + th < 0:
                    continue
                if t.get("clock"):
                    self._draw_clock(can, tx, ty, tw, th, R)
                    continue
                src = R.frame(t["src"], int(t["frame"]))
                res = sample_patch(src, self.lut, tx, ty, tw, th, float(t.get("zoom", 1.0)), t.get("ax", 0.5),
                                   t.get("ay", 0.5), cw, ch)
                if res:
                    p, cov, X0, Y0 = res
                    reg = can[Y0:Y0 + p.shape[0], X0:X0 + p.shape[1]]
                    reg[:] = reg * (1 - cov) + p * self.tile_gain * cov
            self.levels[k] = {"L": L, "origin": (x0, y0), "img": can}

    def _draw_clock(self, can, tx, ty, tw, th, R):
        c = self.clock
        wr = float(c.get("width_ratio", 0.56))
        _, Wm, Hm = G.seg_layout(c["text"], 100.0, "bevel", 0.15, wr, 0.16)
        hgt = min(tw * c.get("fit", 0.94) / Wm, th * 0.98 / Hm) * 100.0
        if hgt < 2:
            return
        m = G.seg_mask(c["text"], hgt, "bevel", thickness=0.15, width_ratio=wr)
        rng = np.random.default_rng(7)
        noise = cv2.GaussianBlur(rng.normal(1.0, c.get("grain", 0.22), m.shape).astype(np.float32), (0, 0), 0.8)
        m = np.clip(m * noise, 0, 1.2) * float(c.get("color", [0.74])[0])
        h, w = m.shape
        X0, Y0 = int(round(tx + tw / 2 - w / 2)), int(round(ty + th / 2 - h / 2))
        xa, ya = max(0, -X0), max(0, -Y0)
        xb, yb = min(w, can.shape[1] - X0), min(h, can.shape[0] - Y0)
        if xb > xa and yb > ya:
            reg = can[Y0 + ya:Y0 + yb, X0 + xa:X0 + xb]
            reg[:] = np.maximum(reg, m[ya:yb, xa:xb])

    def screen_rect(self, i, f, R):
        s = self.scale(f)
        t = self.tiles[i]
        x = self.sax(f) + s * (t["x"] - self.mc[0])
        y = self.say(f) + s * (t["y"] - self.mc[1])
        return x, y, (self.tw - self.gap) * s, (self.th - self.gap) * s

    def draw(self, canvas, f, R):
        if f in self.blackf:
            canvas[:] = R.bg
            return
        s, _ = self._visible(f, R)
        k, L = self._level_of(s)
        lv = self.levels[k]
        x0, y0 = lv["origin"]
        a = s / L
        tx = self.sax(f) + s * (x0 - self.mc[0]) + 0.5 * a - 0.5
        ty = self.say(f) + s * (y0 - self.mc[1]) + 0.5 * a - 0.5
        M = np.array([[a, 0, tx], [0, a, ty]], np.float32)
        img = cv2.warpAffine(lv["img"], M, (R.W, R.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                             borderValue=R.bg)
        if f in self.twinkle:
            out = sample_box(*self.screen_rect(self.twinkle[f], f, R), R.W, R.H)
            if out:
                cov, X0, Y0 = out
                reg = img[Y0:Y0 + cov.shape[0], X0:X0 + cov.shape[1]]
                reg[:] = reg + cov * 0.8 * (1 - reg)
        op = self.opacity(f)
        if f in self.red:
            rgb = np.stack([img * 1.15, img * 0.16, img * 0.13], axis=-1)
            canvas[:] = canvas * (1 - op) + np.clip(rgb, 0, 1) * op
        else:
            canvas[:] = canvas * (1 - op) + img[..., None] * op


LAYERS = {"clip": ClipLayer, "solid": SolidLayer, "text": TextLayer, "clock": ClockLayer, "mosaic": MosaicLayer,
          "firework": FireworkLayer, "streaks": StreaksLayer, "strip": StripLayer}


# ------------------------------------------------------------------------------------------------ renderer
class Renderer:
    def __init__(self, plan: dict):
        self.plan = plan
        self.W, self.H = int(plan["width"]), int(plan["height"])
        self.fps = float(plan["fps"])
        self.N = int(plan["frames"])
        self.bg = float(plan.get("background", 0.045))
        self.curves = plan.get("curves", {})
        self.grades = plan.get("grades", {})
        self.rng = np.random.default_rng(int(plan.get("seed", 1234)))
        self.grain_sigma = float(plan.get("grain", 0.0))
        self.master = Curve(plan.get("master_gain"), self.curves, 1.0)
        # levels: a plan says which cache levels its grades were designed on (see prep_footage.py); a cache of the
        # other kind is converted on read, so e.g. a rebuilt cache cannot change an approved plan's look
        self.levels = plan.get("levels", "single")
        self._src, self._conv = {}, {}
        for sid, s in plan["sources"].items():
            self._src[sid] = np.memmap(Path(s["cache"]), dtype=np.uint8, mode="r",
                                       shape=(int(s["frames"]), int(s["height"]), int(s["width"])))
            self._conv[sid] = level_conversion(cache_levels(s["cache"]), self.levels)
        self._vign = {}
        self.layers = [LAYERS[sp["type"]](sp, self) for sp in plan["layers"]]

    def frame(self, sid: str, i: int) -> np.ndarray:
        a = self._src[sid]
        fr = a[min(max(int(i), 0), a.shape[0] - 1)]
        conv = self._conv[sid]
        return fr if conv is None else conv[fr]

    def vignette(self, color) -> np.ndarray:
        if color not in self._vign:
            yy, xx = np.mgrid[0:self.H, 0:self.W].astype(np.float32)
            d = np.sqrt(((xx - self.W / 2) / (self.W * 0.6)) ** 2 + ((yy - self.H / 2) / (self.H * 0.6)) ** 2)
            v = np.clip(1 - d, 0, 1) ** 1.5
            self._vign[color] = v[..., None] * np.asarray(color, np.float32)
        return self._vign[color]

    def render(self, f: int) -> np.ndarray:
        canvas = np.full((self.H, self.W, 3), self.bg, np.float32)
        for L in self.layers:
            if L.active(f):
                L.draw(canvas, f, self)
        mg = self.master(f)
        if mg != 1.0:
            canvas = self.bg + (canvas - self.bg) * mg
        if self.grain_sigma:
            n = self.rng.normal(0.0, self.grain_sigma, (self.H // 2, self.W // 2)).astype(np.float32)
            n = cv2.resize(n, (self.W, self.H), interpolation=cv2.INTER_LINEAR)
            canvas += n[..., None]
        return (np.clip(canvas, 0, 1) * 255 + 0.5).astype(np.uint8)
