"""Generated graphics for the renderer: boxy pixel font, seven-segment digits, firework bursts, light streaks.

Every function returns float32 arrays in 0..1 at output-pixel size (masks / grey images); colour is applied by the
compositor. Shapes are drawn supersampled and reduced with area averaging, so edges are antialiased.
"""
from __future__ import annotations

import math
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw

# ----------------------------------------------------------------------------------------------- pixel font
# Boxy outline letters on a 4 x 6 grid (x right, y down), drawn as strokes - the "LOCKED IN" title look.
GLYPHS: dict[str, list[list[tuple[float, float]]]] = {
    "A": [[(0, 6), (0, 0), (4, 0), (4, 6)], [(0, 3), (4, 3)]],
    "B": [[(0, 0), (0, 6), (4, 6), (4, 3), (0, 3)], [(0, 0), (3, 0), (3, 3)]],
    "C": [[(4, 0), (0, 0), (0, 6), (4, 6)]],
    "D": [[(0, 0), (0, 6), (3, 6), (4, 5), (4, 1), (3, 0), (0, 0)]],
    "E": [[(4, 0), (0, 0), (0, 6), (4, 6)], [(0, 3), (3, 3)]],
    "F": [[(4, 0), (0, 0), (0, 6)], [(0, 3), (3, 3)]],
    "G": [[(4, 0), (0, 0), (0, 6), (4, 6), (4, 3), (2, 3)]],
    "H": [[(0, 0), (0, 6)], [(4, 0), (4, 6)], [(0, 3), (4, 3)]],
    "I": [[(0, 0), (0, 6)]],
    "J": [[(4, 0), (4, 6), (0, 6), (0, 4)]],
    "K": [[(0, 0), (0, 6)], [(0, 3), (3, 3)], [(3, 3), (4, 2), (4, 0)], [(3, 3), (4, 4), (4, 6)]],
    "L": [[(0, 0), (0, 6), (4, 6)]],
    "M": [[(0, 6), (0, 0), (4, 0), (4, 6)], [(2, 0), (2, 4)]],
    "N": [[(0, 6), (0, 0), (4, 0), (4, 6)]],
    "O": [[(0, 0), (4, 0), (4, 6), (0, 6), (0, 0)]],
    "P": [[(0, 6), (0, 0), (4, 0), (4, 3), (0, 3)]],
    "Q": [[(0, 0), (4, 0), (4, 6), (0, 6), (0, 0)], [(3, 5), (4.6, 6.6)]],
    "R": [[(0, 6), (0, 0), (4, 0), (4, 3), (0, 3)], [(2, 3), (4, 4), (4, 6)]],
    "S": [[(4, 0), (0, 0), (0, 3), (4, 3), (4, 6), (0, 6)]],
    "T": [[(0, 0), (4, 0)], [(2, 0), (2, 6)]],
    "U": [[(0, 0), (0, 6), (4, 6), (4, 0)]],
    "V": [[(0, 0), (0, 4), (2, 6), (4, 4), (4, 0)]],
    "W": [[(0, 0), (0, 6), (4, 6), (4, 0)], [(2, 2), (2, 6)]],
    "X": [[(0, 0), (4, 6)], [(4, 0), (0, 6)]],
    "Y": [[(0, 0), (0, 3), (4, 3)], [(4, 0), (4, 6), (0, 6)]],
    "Z": [[(0, 0), (4, 0), (0, 6), (4, 6)]],
    "0": [[(0, 0), (4, 0), (4, 6), (0, 6), (0, 0)]],
    "1": [[(1, 1), (2, 0), (2, 6)]],
    "2": [[(0, 0), (4, 0), (4, 3), (0, 3), (0, 6), (4, 6)]],
    "3": [[(0, 0), (4, 0), (4, 6), (0, 6)], [(1, 3), (4, 3)]],
    "4": [[(0, 0), (0, 3), (4, 3)], [(4, 0), (4, 6)]],
    "5": [[(4, 0), (0, 0), (0, 3), (4, 3), (4, 6), (0, 6)]],
    "6": [[(4, 0), (0, 0), (0, 6), (4, 6), (4, 3), (0, 3)]],
    "7": [[(0, 0), (4, 0), (4, 6)]],
    "8": [[(0, 0), (4, 0), (4, 6), (0, 6), (0, 0)], [(0, 3), (4, 3)]],
    "9": [[(4, 3), (0, 3), (0, 0), (4, 0), (4, 6), (0, 6)]],
    "-": [[(0, 3), (4, 3)]],
    ".": [[(0, 6), (0.01, 6)]],
    ":": [[(0, 1.6), (0.01, 1.6)], [(0, 4.4), (0.01, 4.4)]],
    "'": [[(0, 0), (0, 1.5)]],
    "!": [[(0, 0), (0, 4)], [(0, 6), (0.01, 6)]],
    "?": [[(0, 0), (4, 0), (4, 3), (2, 3), (2, 4)], [(2, 6), (2.01, 6)]],
}
NARROW = set("I1.:'!")


def text_mask(text: str, height: float, stroke: float | None = None, tracking: float = 0.55, ss: int = 4,
              width_scale: float = 1.0) -> np.ndarray:
    """Alpha mask of `text` in the boxy pixel font; `height` = letter height in output pixels,
    `width_scale` stretches letters horizontally (1.6 = the wide title look)."""
    text = text.upper()
    u = height / 6.0                                     # one grid unit (vertical)
    ux = u * width_scale                                 # horizontal grid unit
    st = stroke if stroke is not None else max(1.0, height * 0.085)
    pad = st * 2
    widths = []
    for ch in text:
        if ch == " ":
            widths.append(2.2 * ux)
        elif ch in NARROW:
            widths.append(0.0 + st)
        else:
            widths.append(4 * ux + st)
    total = sum(widths) + tracking * ux * 2 * max(0, len(text) - 1)
    W, H = int(math.ceil(total + 2 * pad)), int(math.ceil(height + st + 2 * pad))
    img = Image.new("L", (W * ss, H * ss), 0)
    d = ImageDraw.Draw(img)
    x = pad + st / 2
    for ch, w in zip(text, widths):
        for poly in GLYPHS.get(ch, []):
            pts = [((x + px * ux) * ss, (pad + st / 2 + py * u) * ss) for px, py in poly]
            if len(pts) == 2 and abs(pts[0][0] - pts[1][0]) < ss * 0.5 and abs(pts[0][1] - pts[1][1]) < ss * 0.5:
                r = st * ss * 0.6                       # a dot
                d.rectangle([pts[0][0] - r, pts[0][1] - r, pts[0][0] + r, pts[0][1] + r], fill=255)
                continue
            d.line(pts, fill=255, width=max(1, int(round(st * ss))), joint="curve")
            for p in (pts[0], pts[-1]):                 # square caps
                r = st * ss / 2
                d.rectangle([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=255)
        x += w + tracking * ux * 2
    a = np.asarray(img, np.float32) / 255.0
    return cv2.resize(a, (W, H), interpolation=cv2.INTER_AREA)


def text_layout(text: str, height: float, stroke: float | None = None, tracking: float = 0.55,
                width_scale: float = 1.0) -> tuple:
    """The geometry text_mask draws, for vector versions of the pixel font (SVG in HTML overlays): (polylines,
    dots, stroke width, W, H) in mask pixels - square caps, round joins; a dot = a square of 1.2 x stroke."""
    text = text.upper()
    u = height / 6.0
    ux = u * width_scale
    st = stroke if stroke is not None else max(1.0, height * 0.085)
    pad = st * 2
    widths = [2.2 * ux if ch == " " else (0.0 + st if ch in NARROW else 4 * ux + st) for ch in text]
    total = sum(widths) + tracking * ux * 2 * max(0, len(text) - 1)
    W, H = int(math.ceil(total + 2 * pad)), int(math.ceil(height + st + 2 * pad))
    lines, dots = [], []
    x = pad + st / 2
    for ch, w in zip(text, widths):
        for poly in GLYPHS.get(ch, []):
            pts = [(x + px * ux, pad + st / 2 + py * u) for px, py in poly]
            if len(pts) == 2 and abs(pts[0][0] - pts[1][0]) < 0.5 and abs(pts[0][1] - pts[1][1]) < 0.5:
                dots.append(pts[0])
            else:
                lines.append(pts)
        x += w + tracking * ux * 2
    return lines, dots, st, W, H


# ----------------------------------------------------------------------------------------------- seven segment
SEGMENTS = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc",
            "7": "abc", "8": "abcdefg", "9": "abcdfg", "-": "g", " ": ""}


def _seg_polys(seg: str, x: float, y: float, w: float, h: float, t: float, gap: float, style: str):
    """Polygon of one segment of a digit whose box is (x, y, w, h); t = thickness."""
    hh = h / 2
    if seg in "agd":
        yc = {"a": y + t / 2, "g": y + hh, "d": y + h - t / 2}[seg]
        x0, x1 = x + gap, x + w - gap
        if style == "rect":
            return [(x0 + t * 0.55, yc - t / 2), (x1 - t * 0.55, yc - t / 2), (x1 - t * 0.55, yc + t / 2),
                    (x0 + t * 0.55, yc + t / 2)]
        return [(x0, yc), (x0 + t / 2, yc - t / 2), (x1 - t / 2, yc - t / 2), (x1, yc), (x1 - t / 2, yc + t / 2),
                (x0 + t / 2, yc + t / 2)]
    xc = x + t / 2 if seg in "fe" else x + w - t / 2
    if seg in "fb":
        y0, y1 = y + t / 2 + gap, y + hh - gap
    else:
        y0, y1 = y + hh + gap, y + h - t / 2 - gap
    if style == "rect":
        return [(xc - t / 2, y0 + t * 0.05), (xc + t / 2, y0 + t * 0.05), (xc + t / 2, y1 - t * 0.05),
                (xc - t / 2, y1 - t * 0.05)]
    return [(xc, y0), (xc + t / 2, y0 + t / 2), (xc + t / 2, y1 - t / 2), (xc, y1), (xc - t / 2, y1 - t / 2),
            (xc - t / 2, y0 + t / 2)]


@lru_cache(maxsize=64)
def seg_layout(text: str, height: float, style: str = "bevel", thickness: float = 0.15, width_ratio: float = 0.56,
               spacing: float = 0.16) -> tuple:
    """Geometry of a seven-segment string: list of (char_index, seg, polygon) and the total size."""
    h = float(height)
    w = width_ratio * h
    t = thickness * h
    gap = 0.035 * h
    pad = 0.08 * h
    items = []
    x = pad
    for ci, ch in enumerate(text):
        if ch == ":":
            cw = t * 1.2
            for k, yy in enumerate((0.30, 0.70)):
                cx, cy = x + cw / 2, pad + yy * h
                items.append((ci, "colon%d" % k, [(cx - t / 2, cy - t / 2), (cx + t / 2, cy - t / 2),
                                                  (cx + t / 2, cy + t / 2), (cx - t / 2, cy + t / 2)]))
            x += cw + spacing * h
            continue
        for s in SEGMENTS.get(ch, ""):
            items.append((ci, s, _seg_polys(s, x, pad, w, h, t, gap, style)))
        x += w + spacing * h
    W = int(math.ceil(x - spacing * h + pad))
    H = int(math.ceil(h + 2 * pad))
    return tuple(items), W, H


def seg_mask(text: str, height: float, style: str = "bevel", dim: dict | None = None, ss: int = 3,
             thickness: float = 0.15, width_ratio: float = 0.56, spacing: float = 0.16) -> np.ndarray:
    """Mask of a seven-segment string. `dim` maps (char_index, seg) -> brightness (0..1) for flicker."""
    items, W, H = seg_layout(text, float(height), style, thickness, width_ratio, spacing)
    img = Image.new("L", (W * ss, H * ss), 0)
    d = ImageDraw.Draw(img)
    for ci, s, poly in items:
        v = 255 if not dim else int(255 * dim.get((ci, s), 1.0))
        d.polygon([(px * ss, py * ss) for px, py in poly], fill=v)
    a = np.asarray(img, np.float32) / 255.0
    return cv2.resize(a, (W, H), interpolation=cv2.INTER_AREA)


def seg_items(text: str, height: float, style: str = "bevel", **kw):
    items, W, H = seg_layout(text, float(height), style, **kw)
    return [(ci, s) for ci, s, _ in items]


# ----------------------------------------------------------------------------------------------- firework
def firework(size: int, t: float, seed: int = 1, n: int = 260) -> np.ndarray:
    """A spark burst `size` x `size`, t = 0 (ignition) .. 1 (faded). Sparks fly out with trails and slight gravity."""
    rng = np.random.default_rng(seed)
    ang = rng.uniform(0, 2 * np.pi, n)
    spd = rng.uniform(0.25, 1.0, n) ** 0.6
    life = rng.uniform(0.55, 1.0, n)
    flick = rng.uniform(0, 2 * np.pi, n)
    ss = 2
    S = size * ss
    img = np.zeros((S, S), np.float32)
    c = S / 2
    R = 0.47 * S
    ease = 1 - (1 - min(t, 1.0)) ** 2.2                   # fast start, slows down
    if t < 0.12:                                          # ignition flash
        core = (1 - t / 0.12)
        cv2.circle(img, (int(c), int(c)), int(0.015 * S + 0.03 * S * t / 0.12), float(1.2 * core + 0.3), -1,
                   cv2.LINE_AA)
    for i in range(n):
        if t > life[i]:
            continue
        r1 = R * spd[i] * ease
        r0 = R * spd[i] * max(0.0, 1 - (1 - max(t - 0.08, 0.0)) ** 2.2)
        g = 0.18 * S * t * t
        x1, y1 = c + r1 * math.cos(ang[i]), c + r1 * math.sin(ang[i]) + g
        x0, y0 = c + r0 * math.cos(ang[i]), c + r0 * math.sin(ang[i]) + g * 0.7
        fade = (1 - t / life[i]) ** 1.3 * (0.75 + 0.25 * math.sin(flick[i] + t * 40))
        cv2.line(img, (int(x0), int(y0)), (int(x1), int(y1)), float(fade), max(1, int(0.004 * S)), cv2.LINE_AA)
        cv2.circle(img, (int(x1), int(y1)), max(1, int(0.006 * S)), float(min(1.0, fade * 1.3)), -1, cv2.LINE_AA)
    img = cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA)
    glow = cv2.GaussianBlur(img, (0, 0), size * 0.02)
    return np.clip(img + 0.8 * glow, 0, 1.5)


# ----------------------------------------------------------------------------------------------- light streaks
def streaks(W: int, H: int, seed: int, n: int = 5, strength: float = 0.7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    img = np.zeros((H, W), np.float32)
    for _ in range(n):
        y = rng.uniform(0.1, 0.9) * H
        slope = rng.uniform(-0.12, 0.12)
        x0, x1 = rng.uniform(-0.1, 0.5) * W, rng.uniform(0.5, 1.1) * W
        cv2.line(img, (int(x0), int(y)), (int(x1), int(y + slope * (x1 - x0))), float(rng.uniform(0.4, 1.0)),
                 max(1, int(rng.uniform(1, 3))), cv2.LINE_AA)
    img = img + 0.6 * cv2.GaussianBlur(img, (0, 0), 6)
    return np.clip(img * strength, 0, 1)


def grain(shape, rng, sigma: float) -> np.ndarray:
    return rng.normal(0.0, sigma, shape).astype(np.float32)
