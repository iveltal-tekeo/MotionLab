"""Frame compositor for MotionLab renders: a plan (layers on a timeline) -> RGB frames.

Coordinates are output pixels (x right, y down); frames are 0-based at plan["fps"]; ranges are inclusive.
Layer types: clip, solid, text, clock, mosaic, firework, streaks, strip, overlay (an HTML graphic rendered by
tools/overlay.py with HyperFrames - the way to make new graphics since 0.3.0).
Animated values ("curves") are a number, {"keys": [[f, v, ease], ...]}, {"start": f0, "values": [...]} or
"@name" for a curve defined once in plan["curves"]. Eases (for the segment after a key): hold, linear,
smooth (S-curve), in (accelerating / slow start), out (decelerating / slow end), in3 / out3 (stronger), pop (a slow
end that overshoots a little). A clip's "rotation" (degrees, clockwise) turns its box round its centre; a "zoom"
under 1 shrinks the box round its zoom point (the anchor) - what is under it shows round it.
Clip sources are the frame caches written by tools/prep_footage.py (full range, cover-fit at 1x): colour (plan
source "format": "i420", the default since 0.3.0) or grey ("gray"; test_4am) - see motionlab/footage.py. Grades
(plan["grades"]) are levels / gamma / output range per channel (grade_lut) plus "saturation" (1 = as shot, 0 = grey;
colour sources only); since 0.4 also "lut3d" (a .cube applied first - colour.match_lut: the footage moved toward a
reference's look) and "tint" (per-channel multipliers, applied last like a layer's own "tint").
A graphic made apart from the footage looks pasted on (the user, 2026-10-27: "combining it with talking heads or people
is where it gets kinda AI-ish"), so an overlay can be made part of the shot (0.6.1; the person track: person.py):
"behind": true = hidden where the person is (the clip under it); "guard": true = hidden only over the face;
"follow": "face" = moved and scaled with the face (as it is at the layer's first frame - a label, brackets) - with
"snap": w | {"w", "dx", "dy"} its centre ON the face every frame, w face widths wide (dx / dy in face widths);
"follow": "camera" = part of the room (a word behind the person): moved and scaled with the clip's punch-ins / pans;
"glass": true (GLASS_BLUR) | blur px = the footage under the graphic frosted (its own fill gives the tint); "shadow": true |
{"blur", "dy", "opacity"} = a soft shadow on the footage; "match": true | {"soft", "grain"} = the footage's own
softness and grain on the graphic. Sizes are at 1080 px (scaled with the frame).
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np

from . import footage as FC
from . import graphics as G
from . import person as P

REC709 = np.array([0.2126, 0.7152, 0.0722], np.float32)       # luma weights (saturation, colour -> grey)
IDLUT = np.arange(256, dtype=np.float32) / 255.0              # a mask (uint8) sampled like a picture
GLASS_BLUR = 44.0      # "glass": true's frost (px at 1080): 18 left a brown smudge where a card covered skin (the user's
#                        neck, 2026-10-27 - 60 washed it out); real frosted glass diffuses that much

# ------------------------------------------------------------------------------------------------ curves
EASES = {
    "hold": lambda t: 0.0,
    "linear": lambda t: t,
    "smooth": lambda t: t * t * (3 - 2 * t),
    "in": lambda t: t * t,
    "out": lambda t: 1 - (1 - t) * (1 - t),
    "in3": lambda t: t * t * t,
    "out3": lambda t: 1 - (1 - t) ** 3,
    # 2026-10-26, the Editor's keyframes: "pop" = a slow end that overshoots a little and settles (CSS / CapCut's
    # "back out")
    "pop": lambda t: 1 + 2.70158 * (t - 1) ** 3 + 1.70158 * (t - 1) ** 2,
}
# 2026-10-27, the user: "try some ease-in ease-out stuff ... basic flow keyframe charts": the curves motion designers
# use (After Effects' handles / the Flow plugin's presets), as cubic Beziers - a key's ease may also be written
# "cubic(x1,y1,x2,y2)" (the two handles, like CSS cubic-bezier) and the Editor's chart drags them
BEZIERS = {
    "easy": (0.33, 0.0, 0.67, 1.0),            # After Effects' Easy Ease (33 % influence): a gentle start and end
    "strong": (0.7, 0.0, 0.3, 1.0),            # 70 % influence: slow away, quick through the middle, slow landing
    "glide": (0.16, 1.0, 0.3, 1.0),            # expo out: off at once, a long soft landing (punch-ins, pushes)
    "launch": (0.7, 0.0, 0.84, 0.0),           # expo in: a long wind-up, then away (exits)
}
_BZ: dict = {}


def bezier(x1: float, y1: float, x2: float, y2: float):
    """A cubic Bezier ease (handles x1, y1, x2, y2 with ends 0, 0 and 1, 1) as t -> value, tabled once."""
    key = (round(x1, 4), round(y1, 4), round(x2, 4), round(y2, 4))
    if key not in _BZ:
        s = np.linspace(0, 1, 2049)
        bx = 3 * (1 - s) ** 2 * s * x1 + 3 * (1 - s) * s * s * x2 + s ** 3
        by = 3 * (1 - s) ** 2 * s * y1 + 3 * (1 - s) * s * s * y2 + s ** 3
        xs = np.linspace(0, 1, 1025)
        ys = np.interp(xs, np.maximum.accumulate(bx), by)
        _BZ[key] = lambda t, xs=xs, ys=ys: float(np.interp(t, xs, ys))
    return _BZ[key]


def ease_fn(name: str):
    """An ease by name: EASES, BEZIERS or "cubic(x1,y1,x2,y2)" (x1, x2 kept in 0..1); an unknown one = linear."""
    if name in EASES:
        return EASES[name]
    if name in BEZIERS:
        return bezier(*BEZIERS[name])
    if isinstance(name, str) and name.startswith("cubic(") and name.endswith(")"):
        try:
            x1, y1, x2, y2 = (float(v) for v in name[6:-1].split(","))
            return bezier(min(max(x1, 0.0), 1.0), y1, min(max(x2, 0.0), 1.0), y2)
        except ValueError:
            pass
    return EASES["linear"]


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
            self.fn = [ease_fn(e) for e in self.ke]
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
            x = min(max(float(f) - self.f0, 0.0), len(self.vals) - 1.0)
            i = int(x)                                      # (between two frames - a motion blur's samples: in between)
            v = self.vals[i] if x == i else self.vals[i] + (self.vals[i + 1] - self.vals[i]) * (x - i)
        else:
            kf, kv = self.kf, self.kv
            if f <= kf[0]:
                v = kv[0]
            elif f >= kf[-1]:
                v = kv[-1]
            else:
                i = int(np.searchsorted(kf, f, side="right")) - 1
                t = (f - kf[i]) / max(1e-9, kf[i + 1] - kf[i])
                v = kv[i] + (kv[i + 1] - kv[i]) * self.fn[i](t)
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


LEVELS = ("black", "white", "gamma", "out_black", "out_white")


def grade_parts(g: dict) -> tuple[np.ndarray, float]:
    """A plan grade -> (the levels LUT, saturation); "lut3d" / "tint" are read by the clip layer."""
    g = dict(g or {})
    return grade_lut(**{k: g[k] for k in LEVELS if k in g}), float(g.get("saturation", 1.0))


def lut3d_table(path: str) -> np.ndarray:
    """A .cube as a (128, 128, 128, 3) uint8 table indexed [r >> 1, g >> 1, b >> 1] (6 MB; within 1/255 of the
    trilinear result) - fast enough to grade every cached frame."""
    from . import colour as CO
    lut = CO.read_cube(Path(path))
    v = np.arange(0, 256, 2, dtype=np.uint8)
    R, G, B = np.meshgrid(v, v, v, indexing="ij")
    return CO.apply_lut(np.stack([R, G, B], axis=-1), lut)


def saturate(patch: np.ndarray, sat: float) -> np.ndarray:
    """Saturation about Rec.709 luma (RGB patches only; grey ones stay as they are)."""
    if sat == 1.0 or patch.ndim != 3:
        return patch
    y = (patch @ REC709)[..., None]
    return y + (patch - y) * sat


def as_rgb(img: np.ndarray) -> np.ndarray:
    return img if img.ndim == 3 else np.repeat(img[..., None], 3, axis=2)


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
    """A video panel (or still with "hold" - a photo is a one-frame source) from a cached source, placed in rect
    [x, y, w, h]; "fit": "cover" (default) | "contain"."""

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
        # a zoom point given frame by frame (a shake, the Editor's RGB split): its swing round its last value also
        # moves a face-tracked one (zoom_point) - (axis, first frame, frames, its resting value)
        self._swing = [(k, int(a["start"]), len(a["values"]), float(a["values"][-1])) for k, a in enumerate(an[:2])
                       if isinstance(a, dict) and a.get("values")]
        # 2026-10-27 (the Editor's transitions): "mblur" = motion blur - the picture's moves sampled over half a frame
        # (a 180 degree shutter) and averaged, as a camera blurs a slide, a whip or a zoom
        self.mblur = bool(spec.get("mblur"))
        self.gain = Curve(spec.get("gain"), R.curves, 1.0)
        self.rot = Curve(spec.get("rotation"), R.curves, 0.0)      # degrees, clockwise, round the rect's centre
        g = {**R.grades.get(spec.get("grade", "default"), {}), **spec.get("grade_override", {})}
        self.lut, self.sat = grade_parts(g)
        self.lut3d = R.lut3d(g["lut3d"]) if g.get("lut3d") else None
        self.speed = float(spec.get("speed", 1.0))
        self.hold = bool(spec.get("hold", False))
        self.jumps = sorted([[int(a), int(b)] for a, b in spec.get("jumps", [[self.start, spec.get("in", 0)]])])
        self.flash_over = {int(k): float(v) for k, v in spec.get("flash_over", {}).items()}
        self.flash_white = set(int(v) for v in spec.get("flash_white", []))
        self.black = set(int(v) for v in spec.get("black", []))
        self.mirror = bool(spec.get("mirror", False))
        t1, t2 = spec.get("tint"), g.get("tint")                # the layer's own tint (RGB split) x the grade's
        self.tint = [a * b for a, b in zip(t1, t2)] if t1 and t2 else (t1 or t2)
        # "cover" (default) fills the rect and crops; "contain" (2026-10-24, photos: a horizontal photo in a vertical
        # video) = the whole picture in the rect (zoom / anchor inside its own box), over a blurred, darker cover copy
        self.fit = spec.get("fit", "cover")
        self._bg = None
        # 0.6.1 (the face-led effects): "track": "face" = the zoom point on the face (person.py's track - a punch-in or
        # a push lands on the person as they move); "room": {"dim", "blur", "grey"} = curves for the room around the
        # person only (a spotlight, a room melting out of focus, a grey room)
        self.track = spec.get("track") == "face"
        rm = spec.get("room") if isinstance(spec.get("room"), dict) else {}
        self.room = {k: Curve(rm[k], R.curves, 0.0) for k in ("dim", "blur", "grey") if rm.get(k) is not None}

    def zoom_point(self, f: int, R: "Renderer") -> tuple[float, float]:
        if self.track:
            T = R.person(self.src)
            fc = T.face(self.src_index(f)) if T is not None else None
            if fc is not None:
                p = [float(fc[0]), float(fc[1]) + 0.05]         # (the face a little above the middle)
                for k, s0, n, rest in self._swing:
                    if s0 <= f < s0 + n:
                        p[k] += (self.ax if k == 0 else self.ay)(f) - rest
                return p[0], p[1]
        return self.ax(f), self.ay(f)

    def src_index(self, f: int) -> int:
        j = self.jumps[0]
        for jj in self.jumps:
            if jj[0] <= f:
                j = jj
        return j[1] if self.hold else j[1] + int(math.floor((f - j[0]) * self.speed + 1e-6))

    def _geom(self, f: float, R: "Renderer"):
        """(x, y, w, h, zoom, zoom point x, y, rotation, the rotation's centre x, y) at frame f (a fraction: a motion
        blur's sample)."""
        x, y, w, h = self.rect
        x += self.dx(f)
        y += self.dy(f)
        z, rot = self.zoom(f), self.rot(f)
        cx0, cy0 = x + w / 2, y + h / 2                         # (what a rotation turns round)
        zax, zay = self.zoom_point(f, R)
        if z < 1.0:                                             # smaller than its box: the box shrinks round the
            ax, ay = zax, zay                                   # zoom point (the Editor's preview does the same)
            x, y, w, h, z = x + ax * w * (1 - z), y + ay * h * (1 - z), w * z, h * z, 1.0
            cx0, cy0 = x + w / 2, y + h / 2
        return x, y, w, h, z, zax, zay, rot, cx0, cy0

    def _blurred(self, src: np.ndarray, f: int, R: "Renderer"):
        """sample_patch's result averaged over the picture's moves from f - 1/4 to f + 1/4 (a 180 degree shutter) -
        one sample when it barely moves, up to 16 (about one every 6 px of travel) - or None (nothing left to see)."""
        a, b = self._geom(f - 0.25, R), self._geom(f + 0.25, R)
        travel = max(abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2]), abs(a[3] - b[3]),
                     abs(a[4] - b[4]) / max(1e-6, min(a[4], b[4])) * max(a[2], a[3]) / 2,
                     abs(a[5] - b[5]) * a[2] * a[4], abs(a[6] - b[6]) * a[3] * a[4])
        n = int(min(16, max(1, math.ceil(travel / 6))))
        if n == 1:
            g = self._geom(f, R)
            return sample_patch(src, self.lut, *g[:7], R.W, R.H, self.mirror)
        acc = cov = None
        for j in range(n):
            g = self._geom(f - 0.25 + 0.5 * (j + 0.5) / n, R)
            res = sample_patch(src, self.lut, *g[:7], R.W, R.H, self.mirror)
            if res is None:
                continue
            p, c, X0, Y0 = res
            if acc is None:
                acc = np.zeros((R.H, R.W) + p.shape[2:], np.float32)
                cov = np.zeros((R.H, R.W), np.float32)
            hh, ww = c.shape
            acc[Y0:Y0 + hh, X0:X0 + ww] += p * (c[..., None] if p.ndim == 3 else c)
            cov[Y0:Y0 + hh, X0:X0 + ww] += c
        if acc is None:
            return None
        ys, xs = np.nonzero(cov)
        Ya, Yb, Xa, Xb = int(ys.min()), int(ys.max()) + 1, int(xs.min()), int(xs.max()) + 1
        c = cov[Ya:Yb, Xa:Xb]
        p = acc[Ya:Yb, Xa:Xb] / np.maximum(c, 1e-6)[(...,) + ((None,) if acc.ndim == 3 else ())]
        return p, c / n, Xa, Ya

    def draw(self, canvas, f, R):
        op = self.opacity(f)
        if op <= 0.002:
            return
        x, y, w, h, z, zax, zay, rot, cx0, cy0 = self._geom(f, R)
        if f in self.black:
            out = sample_box(x, y, w, h, R.W, R.H)
            if out:
                cov, X0, Y0 = out
                blend(canvas, np.full(cov.shape, R.bg, np.float32), cov * op, X0, Y0)
            return
        i = self.src_index(f)
        src = R.frame(self.src, i)
        if self.lut3d is not None and src.ndim == 3:
            src = self.lut3d[src[..., 0] >> 1, src[..., 1] >> 1, src[..., 2] >> 1]
        parts = []                                              # (sample_patch result, brightness, the picture's box)
        if self.fit == "contain":
            sh, sw = src.shape[:2]
            if self._bg is None or self._bg[0] != i:            # the blurred copy behind, once per source frame
                small = cv2.resize(src, (max(8, sw // 10), max(8, sh // 10)), interpolation=cv2.INTER_AREA)
                self._bg = (i, cv2.GaussianBlur(small, (0, 0), 2.5))
            parts.append((sample_patch(self._bg[1], self.lut, x, y, w, h, 1.0, 0.5, 0.5, R.W, R.H, self.mirror), 0.55,
                          None))
            ar = sw / sh                                         # the whole picture in the rect; the zoom (and its
            cw, ch = (h * ar, float(h)) if w / h > ar else (float(w), w / ar)   # anchor) works inside that box
            box = (x + (w - cw) / 2, y + (h - ch) / 2, cw, ch, z, zax, zay)
            parts.append((sample_patch(src, self.lut, *box, R.W, R.H, self.mirror), 1.0, box))
        elif self.mblur and abs(rot) <= 1e-3:                   # (its box changes over the shutter: none for the room)
            parts.append((self._blurred(src, f, R), 1.0, None))
        else:
            box = (x, y, w, h, z, zax, zay)
            parts.append((sample_patch(src, self.lut, *box, R.W, R.H, self.mirror), 1.0, box))
        for res, k_dim, box in parts:
            if res is not None and abs(rot) > 1e-3:
                res = rotate_patch(*res, cx0, cy0, rot, R.W, R.H)
            if res is None:
                continue
            patch, cov, X0, Y0 = res
            patch = saturate(patch, self.sat)
            g = self.gain(f)
            if g != 1.0:
                patch = patch * g
            if f in self.flash_over:                            # over-exposed flash frame (image still visible):
                k = self.flash_over[f]                          # 2026-10-27 an exposure flash - brighter in linear
                lin = np.clip(patch, 0, 1) ** 2.2 * (1 + 4 * k)     # light, clipped, a little white over it (the old
                patch = np.minimum(lin, 1.0) ** (1 / 2.2)       # white mix made the blacks a milky grey)
                patch = patch + 0.25 * k * (1.0 - patch)
            if f in self.flash_white:                           # flat white frame (a trace of the image left)
                patch = 0.86 + 0.06 * patch
            if self.room and box is not None and abs(rot) <= 1e-3:    # the room around the person only
                vals = {k: c(f) for k, c in self.room.items()}
                if any(v > 1e-3 for v in vals.values()):
                    m = R.person_patch(self, i, box, patch)
                    if m is not None:
                        patch = room_look(patch, m, vals, min(R.W, R.H) / 1080.0)
            blend(canvas, patch * k_dim if k_dim != 1.0 else patch, cov * op, X0, Y0, self.mode, self.tint)
            if R.matte is not None:                             # the person under the graphics to come
                R.person_into(self, i, box if abs(rot) <= 1e-3 else None, patch, cov * op, X0, Y0)

    def box(self, f: int, R: "Renderer"):
        """The picture's box at frame f as draw() samples it - (x, y, w, h, zoom, ax, ay) - or None (a black or a
        turned frame): where the face lands (Renderer.face_at)."""
        if f in self.black or abs(self.rot(f)) > 1e-3:
            return None
        x, y, w, h = self.rect
        x += self.dx(f)
        y += self.dy(f)
        z = self.zoom(f)
        if z < 1.0:
            ax, ay = self.ax(f), self.ay(f)
            x, y, w, h, z = x + ax * w * (1 - z), y + ay * h * (1 - z), w * z, h * z, 1.0
        zax, zay = self.zoom_point(f, R)
        if self.fit == "contain":
            sw, sh = R.size(self.src)
            ar = sw / sh
            cw, ch = (h * ar, float(h)) if w / h > ar else (float(w), w / ar)
            return x + (w - cw) / 2, y + (h - ch) / 2, cw, ch, z, zax, zay
        return x, y, w, h, z, zax, zay


def room_look(patch: np.ndarray, m: np.ndarray, vals: dict, k: float) -> np.ndarray:
    """The room around the person (m = the person, 0..1) greyed, blurred (weighted by the room only, so the person does
    not smear into it), dimmed - the person as it was."""
    p3 = patch if patch.ndim == 3 else np.repeat(patch[..., None], 3, 2)
    bg = p3
    g = vals.get("grey", 0.0)
    if g > 1e-3:
        bg = bg * (1 - g) + (bg @ REC709)[..., None] * g
    b = vals.get("blur", 0.0) * k
    if b > 0.3:
        wgt = (1 - m).astype(np.float32)
        num = cv2.GaussianBlur(bg * wgt[..., None], (0, 0), b)
        den = cv2.GaussianBlur(wgt, (0, 0), b)
        bg = num / np.maximum(den, 1e-3)[..., None]
    d = vals.get("dim", 0.0)
    if d > 1e-3:
        bg = bg * (1 - min(d, 1.0))
    mm = m[..., None]
    out = p3 * mm + bg * (1 - mm)
    return out if patch.ndim == 3 else out @ REC709


def to_out(nx: float, ny: float, sw: int, sh: int, box, mirror: bool = False) -> tuple[float, float, float]:
    """A point of a source frame (shares of its width / height) -> output pixels, through the box sample_patch draws
    it in; and the output pixels per source pixel."""
    x, y, w, h, z, ax, ay = box
    cw, ch = _cover(w, h, sw, sh)
    cw, ch = cw / z, ch / z
    cx = min(max(ax * sw, cw / 2), sw - cw / 2)
    cy = min(max(ay * sh, ch / 2), sh - ch / 2)
    u, v = (nx * sw - (cx - cw / 2)) / cw, (ny * sh - (cy - ch / 2)) / ch
    if mirror:
        u = 1 - u
    return x + u * w, y + v * h, w / cw


def from_out(X: float, Y: float, sw: int, sh: int, box, mirror: bool = False) -> tuple[float, float]:
    """to_out() backwards: an output pixel -> the source point under it (shares of the source frame)."""
    x, y, w, h, z, ax, ay = box
    cw, ch = _cover(w, h, sw, sh)
    cw, ch = cw / z, ch / z
    cx = min(max(ax * sw, cw / 2), sw - cw / 2)
    cy = min(max(ay * sh, ch / 2), sh - ch / 2)
    u, v = (X - x) / w, (Y - y) / h
    if mirror:
        u = 1 - u
    return (cx - cw / 2 + u * cw) / sw, (cy - ch / 2 + v * ch) / sh


def rotate_patch(patch, cov, X0, Y0, cx, cy, deg, W, H):
    """A drawn patch (and its coverage) turned `deg` degrees clockwise round the frame point (cx, cy) -> the same kind
    of tuple over the frame pixels it now covers, or None."""
    h, w = cov.shape
    th = math.radians(deg)
    co, si = math.cos(th), math.sin(th)
    cxi, cyi = cx - 0.5, cy - 0.5                          # (pixel-index space: centres at integers)
    xs, ys = [], []
    for px, py in ((X0 - 0.5, Y0 - 0.5), (X0 + w - 0.5, Y0 - 0.5), (X0 - 0.5, Y0 + h - 0.5), (X0 + w - 0.5, Y0 + h - 0.5)):
        xs.append(cxi + co * (px - cxi) - si * (py - cyi))
        ys.append(cyi + si * (px - cxi) + co * (py - cyi))
    Xa, Xb = max(0, int(math.floor(min(xs)))), min(W, int(math.ceil(max(xs))) + 1)
    Ya, Yb = max(0, int(math.floor(min(ys)))), min(H, int(math.ceil(max(ys))) + 1)
    if Xb <= Xa or Yb <= Ya:
        return None
    # output (i, j) = frame (Xa + i, Ya + j) <- patch (u, v): the inverse turn
    M = np.array([[co, si, co * (Xa - cxi) + si * (Ya - cyi) + cxi - X0],
                  [-si, co, -si * (Xa - cxi) + co * (Ya - cyi) + cyi - Y0]], np.float32)
    pm = patch * (cov[..., None] if patch.ndim == 3 else cov)
    flags = cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP
    a = cv2.warpAffine(cov, M, (Xb - Xa, Yb - Ya), flags=flags, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    col = cv2.warpAffine(pm, M, (Xb - Xa, Yb - Ya), flags=flags, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    col = col / (np.maximum(a, 1e-6)[..., None] if col.ndim == 3 else np.maximum(a, 1e-6))
    return col.astype(np.float32), np.clip(a, 0, 1).astype(np.float32), Xa, Ya


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
        lut, sat = grade_parts(R.grades.get(spec.get("grade", "default"), {}))
        tiles = spec["tiles"]
        color = any(R.is_color(t["src"]) for t in tiles)
        img = np.full((int(round(h)), int(round(w))) + ((3,) if color else ()), R.bg, np.float32)
        n = int(math.ceil(w / tw))
        for i in range(n):
            t = tiles[i % len(tiles)]
            src = R.frame(t["src"], int(t["frame"]))
            res = sample_patch(src, lut, i * tw, 0, tw - gap, h, float(t.get("zoom", 1.0)), t.get("ax", 0.5),
                               t.get("ay", 0.5), img.shape[1], img.shape[0])
            if res:
                p, cov, X0, Y0 = res
                p = saturate(p, sat)
                if color:
                    p, cov = as_rgb(p), cov[..., None]
                reg = img[Y0:Y0 + p.shape[0], X0:X0 + p.shape[1]]
                reg[:] = reg * (1 - cov) + p * cov
        self.img = img * float(spec.get("gain", 1.0))

    def draw(self, canvas, f, R):
        x, y, w, h = self.rect
        x += self.dx(f)
        X0, Y0 = int(round(x)), int(round(y))
        hh, ww = self.img.shape[:2]
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
        self.lut, self.sat = grade_parts(R.grades.get(spec.get("grade", "default"), {}))
        self.color = any(R.is_color(t["src"]) for t in self.tiles if not t.get("clock"))
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
            can = np.full((ch, cw) + ((3,) if self.color else ()), R.bg, np.float32)
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
                    p = saturate(p, self.sat)
                    if self.color:
                        p, cov = as_rgb(p), cov[..., None]
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
            mm = m[ya:yb, xa:xb]
            reg[:] = np.maximum(reg, mm[..., None] if reg.ndim == 3 else mm)

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
                             borderValue=(R.bg,) * 3)
        if f in self.twinkle:
            out = sample_box(*self.screen_rect(self.twinkle[f], f, R), R.W, R.H)
            if out:
                cov, X0, Y0 = out
                reg = img[Y0:Y0 + cov.shape[0], X0:X0 + cov.shape[1]]
                cv = cov[..., None] if reg.ndim == 3 else cov
                reg[:] = reg + cv * 0.8 * (1 - reg)
        op = self.opacity(f)
        if f in self.red:
            y = img @ REC709 if img.ndim == 3 else img
            rgb = np.stack([y * 1.15, y * 0.16, y * 0.13], axis=-1)
            canvas[:] = canvas * (1 - op) + np.clip(rgb, 0, 1) * op
        else:
            canvas[:] = canvas * (1 - op) + as_rgb(img) * op


class OverlayLayer(Layer):
    """A clip made by tools/overlay.py (HyperFrames: HTML / CSS / GSAP -> ProRes 4444 + alpha; motionlab/overlays.py):
    plan frame f shows clip frame in + (f - start) (its last frame holds; "speed" x, 0.6.0 the Editor: in +
    floor((f - start) * x) - captions on a sped-up shot). "rect" [x, y, w, h] places and scales the clip (default: at
    0, 0 at the size it was authored). blend "normal" composites with its alpha; "add" / "screen" add its light
    (colour x alpha) like the lab's glows and fireworks."""

    def __init__(self, spec, R):
        super().__init__(spec, R)
        from . import overlays as OV
        self.meta, self.arr = OV.load(spec["file"])
        self.inn = int(spec.get("in", 0))
        self.speed = float(spec.get("speed", 1.0))
        W0, H0 = self.meta["width"], self.meta["height"]
        x, y, w, h = [float(v) for v in spec.get("rect", [0, 0, W0, H0])]
        self.sx, self.sy = w / W0, h / H0
        cx, cy, cw, ch = self.meta["crop"]
        self.X, self.Y = x + cx * self.sx, y + cy * self.sy              # where the visible crop lands
        self.cw, self.ch = cw, ch
        self.exact = (abs(self.sx - 1) < 1e-9 and abs(self.sy - 1) < 1e-9 and float(self.X).is_integer()
                      and float(self.Y).is_integer())
        self.integ = any(spec.get(k) for k in P.KEYS)
        self.follow = spec.get("follow") if spec.get("follow") in ("face", "camera") else None
        self._ref = False                       # the face / the room point at the layer's first frame (looked up once)
        sn = spec.get("snap")                   # with "follow": "face": its centre ON the face, its width = w face
        self.snap = ({"w": float(sn)} if isinstance(sn, (int, float)) else dict(sn) if isinstance(sn, dict) else None)

    def draw(self, canvas, f, R):
        op = self.opacity(f)
        if op <= 0.002:
            return
        d = f - self.start if self.speed == 1.0 else int(math.floor((f - self.start) * self.speed + 1e-6))
        i = min(max(self.inn + d, 0), self.arr.shape[0] - 1)
        fr = np.asarray(self.arr[i], np.float32) * (1.0 / 255.0)
        rgb, a = fr[..., :3], fr[..., 3]
        light = self.mode in ("add", "screen")
        X, Y, sx, sy, exact = self.X, self.Y, self.sx, self.sy, self.exact
        moved = None                            # (the point it moves with: at the start, now; the scale since)
        if self.follow == "face" and self.snap and R.face is not None:     # on the face: brackets, an arrow, a halo
            fx, fy, fw = R.face                 # (dx / dy = an offset in face widths: above the head, beside it)
            sxn = float(self.snap.get("w", 1.0)) * fw / max(self.cw, 1)
            syn = sy * sxn / max(sx, 1e-9)
            y0, y1 = (0.0, float(R.H)) if R.W >= R.H else (220 / 1920 * R.H, 1500 / 1920 * R.H)   # upright: clear of
            fit = min(1.0, 0.96 * R.W / max(self.cw * sxn, 1), (y1 - y0) / max(self.ch * syn, 1))   # the apps' top /
            sxn, syn = sxn * fit, syn * fit             # bottom bands (precheck.SAFE_BANDS); a close-up's big face:
            X = fx + float(self.snap.get("dx", 0.0)) * fw - self.cw * sxn / 2           # never past the frame's edges
            Y = fy + float(self.snap.get("dy", 0.0)) * fw - self.ch * syn / 2
            if float(self.snap.get("dy", 0.0)) < 0:     # above the head: it shrinks into the room there is between
                top = fy - 0.8 * fw                     # the band and the hair (never onto the head)
                room = top - y0
                if self.ch * syn > room > 0:
                    k = max(0.5, room / (self.ch * syn))
                    X += self.cw * sxn * (1 - k) / 2
                    sxn, syn = sxn * k, syn * k
                Y = min(Y, top - self.ch * syn)
            X = min(max(X, 0.0), R.W - self.cw * sxn)
            Y = min(max(Y, y0), max(y0, y1 - self.ch * syn))
            sx, sy, exact = sxn, syn, False
        elif self.follow == "face":             # pinned to the face (a label, brackets): moves and scales with it
            if self._ref is False:
                self._ref = R.face_at(self.start)
            if self._ref is not None and R.face is not None:
                moved = (self._ref[:2], R.face[:2], R.face[2] / max(self._ref[2], 1e-6))
        elif self.follow == "camera":           # part of the room (a word behind you): moves with punch-ins / pans
            if self._ref is False:
                self._ref = R.room_ref(self.start, X + self.cw * sx / 2, Y + self.ch * sy / 2)
            now = R.room_at(f, self._ref) if self._ref is not None else None
            if now is not None:
                moved = (self._ref[3], now[:2], now[2])
        if moved is not None:
            (x0, y0), (x1, y1), k = moved
            X, Y = x1 + (X - x0) * k, y1 + (Y - y0) * k
            sx, sy, exact = sx * k, sy * k, False
            vw, vh = self.cw * sx, self.ch * sy                 # a graphic that was inside the frame stays inside
            if self.X >= 0 and self.X + self.cw * self.sx <= R.W and vw <= R.W:
                X = min(max(X, 0.0), R.W - vw)
            if self.Y >= 0 and self.Y + self.ch * self.sy <= R.H and vh <= R.H:
                Y = min(max(Y, 0.0), R.H - vh)
        if exact:
            X0, Y0 = int(X), int(Y)
            col = rgb * a[..., None] if light else rgb
        else:                                   # resample premultiplied (no dark fringes at soft edges)
            X0, Y0 = int(math.floor(X)), int(math.floor(Y))
            ow, oh = int(math.ceil(X + self.cw * sx)) - X0, int(math.ceil(Y + self.ch * sy)) - Y0
            M = np.array([[sx, 0, X - X0 + 0.5 * sx - 0.5],
                          [0, sy, Y - Y0 + 0.5 * sy - 0.5]], np.float32)
            pm = cv2.warpAffine(np.dstack([rgb * a[..., None], a]), M, (ow, oh), flags=cv2.INTER_LINEAR,
                                borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
            a = pm[..., 3]
            col = pm[..., :3] if light else pm[..., :3] / np.maximum(a, 1e-6)[..., None]
        h, w = a.shape
        xa, ya = max(0, -X0), max(0, -Y0)
        xb, yb = min(w, R.W - X0), min(h, R.H - Y0)
        if xb <= xa or yb <= ya:
            return
        sl = (slice(ya, yb), slice(xa, xb))
        alpha = np.full((yb - ya, xb - xa), op, np.float32) if light else a[sl] * op
        col = col[sl]
        if self.integ:
            col, alpha = R.integrate(self.spec, canvas, col, alpha, X0 + xa, Y0 + ya)
        blend(canvas, col, alpha, X0 + xa, Y0 + ya, self.mode)


LAYERS = {"clip": ClipLayer, "solid": SolidLayer, "text": TextLayer, "clock": ClockLayer, "mosaic": MosaicLayer,
          "firework": FireworkLayer, "streaks": StreaksLayer, "strip": StripLayer, "overlay": OverlayLayer}


# ------------------------------------------------------------------------------------------------ renderer
def resolve_paths(plan: dict, base: Path) -> dict:
    """A plan's relative paths (a layer's "file", a source's "source", the audio) made absolute: next to the plan
    (its build folder) first, else from the lab's folder - so the plan reads the same from any working folder
    (0.5.3; before, sfx.py found no graphic cues in a plan with relative paths, local-make-11(3)). In place."""
    from .util import LAB

    def fix(p):
        if not p or Path(p).is_absolute():
            return p
        for root in (Path(base), LAB):
            if (root / p).exists():
                return str((root / p).resolve())
        return p
    for L in plan.get("layers", []):
        if L.get("file"):
            L["file"] = fix(L["file"])
    for s in (plan.get("sources") or {}).values():
        if isinstance(s, dict) and s.get("source"):
            s["source"] = fix(s["source"])
    if isinstance(plan.get("audio"), dict) and plan["audio"].get("path"):
        plan["audio"]["path"] = fix(plan["audio"]["path"])
    return plan


class Renderer:
    def __init__(self, plan: dict):
        self.plan = plan
        self.W, self.H = int(plan["width"]), int(plan["height"])
        self.fps = float(plan["fps"])
        self.N = int(plan["frames"])
        self.bg = float(plan.get("background", 0.045))
        self.curves = plan.get("curves", {})
        self.grades = plan.get("grades", {})
        self.seed = int(plan.get("seed", 1234))
        self.rng = np.random.default_rng(self.seed)            # re-seeded per frame in render(): see there
        self.grain_sigma = float(plan.get("grain", 0.0))
        self.master = Curve(plan.get("master_gain"), self.curves, 1.0)
        # levels: a plan says which cache levels its grades were designed on (see prep_footage.py); a cache of the
        # other kind is converted on read, so e.g. a rebuilt cache cannot change an approved plan's look
        self.levels = plan.get("levels", "single")
        self._src, self._conv, self._fmt = {}, {}, {}
        for sid, s in plan["sources"].items():
            self._fmt[sid] = fmt = s.get("format", "gray")                  # "i420" = colour cache
            self._src[sid] = FC.open_memmap(s["cache"], s["frames"], s["width"], s["height"], fmt)
            self._conv[sid] = level_conversion(cache_levels(s["cache"]), self.levels)
        self._vign = {}
        self._lut3d: dict = {}
        # graphics made part of the shot (0.6.1): the person under them, per frame (person.py's tracks)
        self.integrate_any = any(sp.get(k) for sp in plan["layers"] for k in P.KEYS)
        self._people: dict = {}
        self.matte = None            # this frame: the person in output pixels (0..1), when a layer asks behind / guard
        self.face = None             # this frame: the face (x, y, width) in output pixels, when one asks follow / guard
        self.layers = [LAYERS[sp["type"]](sp, self) for sp in plan["layers"]]

    def lut3d(self, path: str) -> np.ndarray:
        """A grade's match LUT, built once per render process."""
        if path not in self._lut3d:
            self._lut3d[path] = lut3d_table(path)
        return self._lut3d[path]

    def is_color(self, sid: str) -> bool:
        return self._fmt.get(sid) == "i420"

    def frame(self, sid: str, i: int) -> np.ndarray:
        """Cached frame i (clamped) of source sid: grey (h, w) or RGB (h, w, 3) uint8, in the plan's levels."""
        a = self._src[sid]
        fr = FC.decode(a[min(max(int(i), 0), a.shape[0] - 1)], self._fmt[sid])
        conv = self._conv[sid]
        return fr if conv is None else conv[fr]

    def size(self, sid: str) -> tuple[int, int]:
        s = self.plan["sources"][sid]
        return int(s["width"]), int(s["height"])

    def person(self, sid: str):
        """Source sid's person track (person.Track) or None (none made, or made from another light cache)."""
        if sid not in self._people:
            where = P.source_of(self.plan["sources"].get(sid) or {})
            self._people[sid] = P.load(*where) if where else None
        return self._people[sid]

    def face_at(self, f: int):
        """The face (x, y, width) in output pixels at frame f: the last clip drawn that shows one; a later clip that
        covers it (B-roll) hides it. Geometry only - the same whichever frames a render process draws."""
        face = None
        for L in self.layers:
            if not (isinstance(L, ClipLayer) and L.active(f)) or L.opacity(f) < 0.5:
                continue
            box = L.box(f, self)
            if box is None:
                continue
            T = self.person(L.src)
            fc = T.face(L.src_index(f)) if T is not None else None
            if fc is not None:
                sw, sh = self.size(L.src)
                X, Y, s = to_out(float(fc[0]), float(fc[1]), sw, sh, box, L.mirror)
                if box[0] <= X <= box[0] + box[2] and box[1] <= Y <= box[1] + box[3] and 0 <= X < self.W \
                        and 0 <= Y < self.H:
                    face = (X, Y, float(fc[2]) * sw * s)
                    continue
            if face is not None and box[0] <= face[0] <= box[0] + box[2] and box[1] <= face[1] <= box[1] + box[3]:
                face = None
        return face

    def room_ref(self, f: int, X: float, Y: float):
        """The room point under output pixel (X, Y) at frame f: (the clip layer, its source point x, y, (X, Y), its
        scale) from the top clip showing there - or None."""
        for L in reversed(self.layers):
            if isinstance(L, ClipLayer) and L.active(f) and L.opacity(f) >= 0.5:
                box = L.box(f, self)
                if box is not None and box[0] <= X <= box[0] + box[2] and box[1] <= Y <= box[1] + box[3]:
                    sw, sh = self.size(L.src)
                    nx, ny = from_out(X, Y, sw, sh, box, L.mirror)
                    return L, nx, ny, (X, Y), to_out(nx, ny, sw, sh, box, L.mirror)[2]
        return None

    def room_at(self, f: int, ref):
        """Where room_ref's point is at frame f (x, y, its scale against the start) - None once its clip is gone."""
        L, nx, ny, _, s0 = ref
        if not L.active(f):
            return None
        box = L.box(f, self)
        if box is None:
            return None
        sw, sh = self.size(L.src)
        X, Y, s = to_out(nx, ny, sw, sh, box, L.mirror)
        return X, Y, s / max(s0, 1e-9)

    def person_into(self, L: "ClipLayer", i: int, box, patch: np.ndarray, a: np.ndarray, X0: int, Y0: int):
        """A clip just drawn -> the frame's person mask: its person where it has a track (sampled through the same
        box, its edges moved onto the full-size picture by a guided filter), else it covers what was there."""
        h, w = a.shape
        reg = self.matte[Y0:Y0 + h, X0:X0 + w]
        m = self.person_patch(L, i, box, patch) if box is not None else None
        reg *= (1 - a)
        if m is not None and m.shape == (h, w):
            reg += m * a

    def person_patch(self, L: "ClipLayer", i: int, box, patch: np.ndarray):
        """The person over a clip's drawn patch (0..1, its shape) - sampled through the same box from the light-size
        mask, its edges moved onto the full-size picture by a guided filter - or None (no track)."""
        T = self.person(L.src)
        res = sample_patch(T.mask(i), IDLUT, *box, self.W, self.H, L.mirror) if T is not None else None
        if res is None or res[0].shape[:2] != patch.shape[:2]:
            return None
        sw, sh = self.size(L.src)                     # output pixels per mask pixel: the edge clean-up's reach
        up = to_out(0.5, 0.5, sw, sh, box)[2] * sh / T.masks.shape[1]
        g = np.clip(patch if patch.ndim == 2 else patch @ REC709, 0, 1).astype(np.float32)
        m = P.guided(g, res[0].astype(np.float32), int(np.clip(round(2.5 * up), 3, 24)), 1e-3)
        return np.clip((m - 0.5) * 1.6 + 0.5, 0, 1)

    def integrate(self, spec: dict, canvas: np.ndarray, col: np.ndarray, alpha: np.ndarray, X0: int, Y0: int):
        """A graphic (colour, alpha at X0, Y0) made part of the shot before it is blended: the footage's softness and
        grain, behind the person / off the face, a shadow and frosted glass on the footage under it."""
        h, w = alpha.shape
        k = min(self.W, self.H) / 1080.0
        mt = self.matte[Y0:Y0 + h, X0:X0 + w] if self.matte is not None else None
        if spec.get("match"):
            o = spec["match"] if isinstance(spec["match"], dict) else {}
            if o.get("grain", "auto") == "auto":           # the footage's own grain, measured under the graphic
                g = canvas[Y0:Y0 + h, X0:X0 + w] @ REC709
                grain = float(np.clip(np.median(np.abs(g - cv2.GaussianBlur(g, (0, 0), 1.5))) * 1.4826, 0.002, 0.03))
            else:
                grain = float(o["grain"])
            s = float(o.get("soft", 0.6)) * k
            if s > 0.05:                                    # premultiplied, so the edges do not darken
                pm = cv2.GaussianBlur(np.dstack([col * alpha[..., None], alpha]), (0, 0), s)
                alpha = pm[..., 3]
                col = pm[..., :3] / np.maximum(alpha, 1e-6)[..., None]
            n = self.rng.normal(0.0, grain, (h // 2 + 1, w // 2 + 1)).astype(np.float32)
            col = col + cv2.resize(n, (w, h), interpolation=cv2.INTER_LINEAR)[..., None]
        if spec.get("behind") and mt is not None:
            alpha = alpha * (1 - mt)
        if spec.get("guard") and mt is not None and self.face is not None:
            fx, fy, fw = self.face                         # the face itself (forehead to chin), not the body
            yy, xx = np.ogrid[Y0:Y0 + h, X0:X0 + w]
            e = ((xx - fx) / (fw * 0.6)) ** 2 + ((yy - fy + fw * 0.1) / (fw * 0.75)) ** 2
            alpha = alpha * (1 - np.clip((1.1 - e) / 0.25, 0, 1) * mt)
        if spec.get("shadow"):
            o = spec["shadow"] if isinstance(spec["shadow"], dict) else {}
            sg, dy, so = float(o.get("blur", 16)) * k, float(o.get("dy", 10)) * k, float(o.get("opacity", 0.35))
            pad = int(math.ceil(3 * sg + abs(dy))) + 1
            xa, ya, xb, yb = max(0, X0 - pad), max(0, Y0 - pad), min(self.W, X0 + w + pad), min(self.H, Y0 + h + pad)
            buf = np.zeros((yb - ya, xb - xa), np.float32)
            oy = int(round(dy))
            ty0, ty1 = max(0, Y0 - ya + oy), min(yb - ya, Y0 - ya + oy + h)
            if ty1 > ty0:
                buf[ty0:ty1, X0 - xa:X0 - xa + w] = alpha[ty0 - (Y0 - ya + oy):ty1 - (Y0 - ya + oy)]
                buf = cv2.GaussianBlur(buf, (0, 0), sg) * so
                if spec.get("behind") and self.matte is not None:
                    buf *= 1 - self.matte[ya:yb, xa:xb]
                canvas[ya:yb, xa:xb] *= (1 - buf[..., None])
        if spec.get("glass"):
            gs = (GLASS_BLUR if spec["glass"] is True else float(spec["glass"])) * k
            pad = int(math.ceil(3 * gs)) + 1
            xa, ya, xb, yb = max(0, X0 - pad), max(0, Y0 - pad), min(self.W, X0 + w + pad), min(self.H, Y0 + h + pad)
            bl = cv2.GaussianBlur(canvas[ya:yb, xa:xb], (0, 0), gs)[Y0 - ya:Y0 - ya + h, X0 - xa:X0 - xa + w]
            ga = np.clip((alpha - 0.04) / 0.08, 0, 1)[..., None]     # the graphic's body, not its faint glows
            reg = canvas[Y0:Y0 + h, X0:X0 + w]
            reg *= (1 - ga)
            reg += bl * ga
        return col, alpha

    def vignette(self, color) -> np.ndarray:
        if color not in self._vign:
            yy, xx = np.mgrid[0:self.H, 0:self.W].astype(np.float32)
            d = np.sqrt(((xx - self.W / 2) / (self.W * 0.6)) ** 2 + ((yy - self.H / 2) / (self.H * 0.6)) ** 2)
            v = np.clip(1 - d, 0, 1) ** 1.5
            self._vign[color] = v[..., None] * np.asarray(color, np.float32)
        return self._vign[color]

    def render(self, f: int) -> np.ndarray:
        # noise (grain, grainy clocks) is seeded by (plan seed, frame): a frame looks the same whether it is rendered
        # alone (--stills), in a range or in a parallel chunk (since 0.3.0; before, it depended on the render order)
        self.rng = np.random.default_rng([self.seed, int(f)])
        canvas = np.full((self.H, self.W, 3), self.bg, np.float32)
        if self.integrate_any:
            act = [L.spec for L in self.layers if L.active(f)]
            self.matte = (np.zeros((self.H, self.W), np.float32)
                          if any(s.get("behind") or s.get("guard") for s in act) else None)
            self.face = self.face_at(f) if any(s.get("follow") or s.get("guard") for s in act) else None
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
