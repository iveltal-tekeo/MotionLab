"""Vertical framing (0.6.1, docs\\plans.md *Vertical framing for every edit*, steps 1-2 - the user, 2026-10-29:
"encuadre para redes (en vertical)"): a clip whose picture is wider than its place in the frame (a horizontal clip in
a vertical video) gets its crop and its layout decided per shot from where the faces are, with the whole shot known in
advance (AutoFlip's way; the numbers: docs\\ideas.md *Vertical framing - researched 2026-10-29*).

The crop (step 1), per subject:
  hold    one still crop: the subject fits inside it with MARGIN of the crop to spare on both sides in HOLD_SHARE of
          its samples (most talking shots); moved to the picture's middle only within SNAP of the crop
  follow  still crops joined by eased pans (an S-curve, at most PAN_MAX crop widths a second at its fastest,
          EASE_MIN_F frames or more; moves under MIN_MOVE of the picture skipped) - never a frame-by-frame wobble
  keep    left as it is: too few faces in the shot (the catalogue's subject point stays), a clip that follows the face
          by itself ("track": "face"), a shake's or someone's keyframes, a picture shown whole ("fit": "contain"), a
          layout or a point someone set by hand (the point: unless replace_static)

The layout (step 2), per shot - drawn by compose.py's clip "panels" over its "backdrop":
  fill    the crop above, on one face - or on two or more people while they fit in it together
  split   two people too far apart for one crop: stacked, the left one on top, each panel zoomed so the other face
          stays SPLIT_GAP outside it and both faces come out SPLIT_FACE of their panel wide (never past UPSCALE_MAX);
          the captions then sit on the seam (facefit.py)
  fit     the picture cropped to FIT_ASPECT in a band across the middle over its backdrop - a blurred, darker copy, or
          the colour of a plain background (PLAIN_STD): three or more people, two that do not split, someone moving
          too fast to follow
  screen  a face camera boxed into the picture (straight borders round a small face that stays put - a screen
          recording): the screen on top (SCREEN_SHARE of the height, cropped round where it changes), the face below
  game    the same when the picture round the camera keeps moving (STILL): the face on top (GAME_FACE), the game below

Written as the clip's "anchor" (the first panel's crop centre - the Editor's keys of Position and size; a curve for a
follow), "panels", "backdrop" and "reframe": {"mode", "layout", "v", "ax0", "ay0", ("bare"), ("text")} = written
here, so a later run may change them again (from the clip's own point before it: "ax0" / "ay0", "bare" = it had
none; "text" = the lines burned in that a fit keeps whole, [x0, y0, x1, y1] shares of the picture - facefit keeps
captions off them). A clip taller than its place (a vertical clip in a horizontal video) is not framed yet.

The limits (step 4): decided on the zoom a shot holds (HELD_Q of its frames - not a zoom-through's peak); a fill that
would blow the picture up past UPSCALE_MAX (a 720p clip: 2.7x) or cut text burned into it (subtitles, a chyron, a
title: TEXT_*, found on the light frames) is a fit, its band as wide as the text needs; a panel's face sits inside the
apps' safe area (safezones.py: the eyes under the top band, the chin over the bottom one) where the panel allows.

The faces: YuNet (thumbnail.faces) on the light cache (footage.py), about SAMPLE_FPS times a second, only on the
frames the shots show, kept beside the caches in <ID>.faces.json - every face of each sampled frame (centre x / y,
width / height as shares of the picture, score). The subject of a one-person shot = its biggest face, then the face
nearest to it from sample to sample (a second person passing does not steal the crop); the people of a shot = the
faces PERSON_SHARE of the biggest one's size or more; a two- (three-) person shot = two (three) of them TWO_SIZE of
the biggest or more in TWO_SHARE of its samples.

    apply(plan, replace_static=False) -> [one line per framed shot, frame + timecode]   (plan changed in place; the
        quick draft passes replace_static=True: its points are the catalogue's)
    summary(lines) -> "9 fill (7 held, 2 followed), 2 split, 1 fit, 14 kept"
    selfcheck() -> {"passed", "seconds", "lines"}   made-up faces and pictures, no video
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

import numpy as np

from . import footage as FC
from . import i18n as I18N
from .timecode import frame_to_tc

VERSION = 2                # the "reframe" mark (2 = with layouts)
FACES_V = 1                # <ID>.faces.json
SAMPLE_FPS = 5.0           # AutoFlip samples every 200 ms
FACE_SCORE = 0.7           # as the catalogue's subject
MARGIN = 0.08              # of the crop's width, each side
HOLD_SHARE = 0.95          # of the shot's samples with a face
SNAP = 0.03                # of the crop's width: closer to the picture's middle than this = the middle
MIN_MOVE = 0.04            # of the picture's width (ClipsAI merges smaller moves)
PAN_MAX = 0.5              # crop widths a second at the pan's fastest (an S-curve peaks at 1.5x its mean speed)
EASE_MIN_F = 12            # frames, the shortest pan
MIN_HOLD_S = 0.6           # a still stretch shorter than this joins its neighbour
FACE_SHARE_MIN = 0.3       # faces in fewer of the shot's samples than this: keep
FOLLOW_INSIDE = 0.9        # a follow that keeps the face in the crop in fewer samples than this: too fast (a fit)
CLOSE_UP = 0.5             # a face box counts at most this share of the crop wide (a close-up: keep its middle)
WIDER = 0.98               # a crop narrower than this share of the picture is framed; wider = the same shape
PERSON_SHARE = 0.35        # a face with this share of the sample's biggest face's area or more = a person in the shot
TWO_SIZE = 0.5             # a second (third) person counts for a two- (three-) person shot from this share of the
#                            biggest face's area (2026-10-29: a passer-by in a side view, 0.42 of it, turned a well
#                            framed music-video shot into a fit)
TWO_SHARE = 0.7            # ... in this share of the samples with a face (someone passing through does not)
FIT_ASPECT = 4 / 3         # fit: the band (the whole 16:9 picture fills only 32 % of a 9:16 frame's height)
SPLIT_FACE = 0.3           # split: each face this share of its panel's width (a medium close-up)
SPLIT_GAP = 0.02           # of the picture's width: the other person's face this far outside a panel's crop ...
SPLIT_INTRUDE = 0.05       # ... in all but this share of the samples that show both
UPSCALE_MAX = 2.2          # a panel blows the source's pixels up at most this much (docs\\plans.md step 4: ~2.0-2.2x)
FACE_Y = 0.4               # a panel's face (its box's middle) this far down the panel
PLAIN_STD = 6 / 255        # fit: the band's top and bottom rows this even = a plain background (its colour behind) ...
PLAIN_DIFF = 10 / 255      # ... and the two this close in colour
INSET_FACE = 0.16          # screen / game: a face camera's face at most this share of the picture's width, its middle
INSET_OFF = 0.2            # at least this far from the picture's middle (across or down), seen in INSET_SHARE of the
INSET_SHARE = 0.6          # samples within INSET_STILL of one place
INSET_STILL = 0.02
EDGE = 18.0                # an inset's border: a step of at least this much luma (of 255) between two pixels ...
RUN = 0.7                  # ... along this share of the inset's side (straight, unbroken)
INSET_PAD = 0.02           # the camera's crop this share of its box inside it (a soft border, a shadow, round corners)
STILL = 4.0                # mean luma change (of 255) between samples round the camera: under it a screen, else a game
SCREEN_SHARE = 0.58        # screen + face: the screen's share of the frame's height
GAME_FACE = 0.30           # game: the face camera's share of the height (the plan: the face 30 %, the game 70 %)
# step 4 - the limits
HELD_Q = 0.8               # the zoom a shot holds: this share of its frames at it or under (a zoom-through at a cut -
#                            a few frames at 1.7x - is not what it holds)
TEXT_EDGE = 40.0           # text burned in (subtitles, a chyron, a title): its strokes a step of this much luma (of 255),
TEXT_H = (0.015, 0.09)     # ... a line this share of the picture's height (16-100 px of 1080; a music video's small
#                            lyrics are ~4 px high on the light frame),
TEXT_W = 0.12              # ... at least this share of its width (a word on a poster is shorter),
TEXT_BANDS = (0.22, 0.65)  # ... its middle above the first or below the second share of the height (not the room's
#                            middle, where a poster or a T-shirt is),
TEXT_STROKES = 0.12        # ... with this many letter edges a pixel along it (a shelf's edge has few),
TEXT_SHARE = 0.4           # ... at one place in this share of the shot's samples
TEXT_PAD = 0.02            # of the picture: a line kept whole = this far inside the crop
SAFE_PAD = 10              # px: a panel's face - its eyes this far below the apps' top band, its mouth above the bottom
SAFE_ZOOM = 1.5            # one; a split's panels zoom in at most this much more for it (a low face), and only while
SPLIT_FACE_MAX = 0.45      # the faces stay this share of their panel's width or less (a close-up blown up to fill its
#                            panel looks worse than a mouth near the band)


CHOICES = ("auto", "fill", "fit", "split", "screen", "game")    # the user's (step 5)


class FrameError(ValueError):
    """A framing the shot cannot have (the user's words, translated)."""


class Faces:
    """A source's faces at sampled light frames - detected when first asked, kept in <ID>.faces.json - and its light
    frames themselves (the layouts look at the picture too)."""

    def __init__(self, cache_dir: str | Path, sid: str):
        d = Path(cache_dir)
        if "build" not in [p.lower() for p in d.parts] and "analysis" not in [p.lower() for p in d.parts]:
            raise PermissionError(f"{d}: faces are kept beside a project's caches (build\\cache) only")
        lp, lm = FC.light_paths(d, sid)
        self.meta = json.loads(lm.read_text(encoding="utf-8"))
        self.n, self.h, self.w = int(self.meta["frames"]), int(self.meta["height"]), int(self.meta["width"])
        self.la = np.memmap(lp, dtype=np.uint8, mode="r", shape=(self.n, self.h * 3 // 2, self.w))
        st = lp.stat()
        self.fp = [st.st_size, int(st.st_mtime)]
        self.path = d / f"{sid}.faces.json"
        self.data: dict[int, list] = {}
        self.made = 0
        try:
            j = json.loads(self.path.read_text(encoding="utf-8"))
            if j.get("v") == FACES_V and j.get("light") == self.fp:
                self.data = {int(k): v for k, v in j["faces"].items()}
        except (OSError, ValueError, KeyError):
            pass

    def _i(self, i: int) -> int:
        return min(max(int(i), 0), self.n - 1)

    def rgb(self, i: int) -> np.ndarray:
        return FC.decode(self.la[self._i(i)], "i420")

    def luma(self, i: int) -> np.ndarray:
        return np.asarray(self.la[self._i(i)][:self.h], np.float32)          # (I420: the Y plane first)

    def at(self, i: int) -> list:
        i = self._i(i)
        if i not in self.data:
            from .thumbnail import faces
            fs = faces(self.rgb(i), FACE_SCORE) or []
            self.data[i] = [[round((x + fw / 2) / self.w, 4), round((y + fh / 2) / self.h, 4), round(fw / self.w, 4),
                             round(fh / self.h, 4), s] for x, y, fw, fh, s in fs]
            self.made += 1
        return self.data[i]

    def save(self) -> None:
        if not self.made:
            return
        tmp = self.path.with_name(self.path.name + ".part")
        tmp.write_text(json.dumps({"v": FACES_V, "light": self.fp,
                                   "faces": {str(k): v for k, v in sorted(self.data.items())}}), encoding="utf-8")
        tmp.replace(self.path)
        self.made = 0


def src_index(L: dict, f: int) -> int:
    """The clip's own frame shown at plan frame f (compose.ClipLayer.src_index)."""
    jumps = sorted([[int(a), int(b)] for a, b in L.get("jumps", [[L["start"], L.get("in", 0)]])])
    j = jumps[0]
    for jj in jumps:
        if jj[0] <= f:
            j = jj
    return j[1] if L.get("hold") else j[1] + int(math.floor((f - j[0]) * float(L.get("speed", 1.0)) + 1e-6))


def crop_share(L: dict, sw: float, sh: float) -> float:
    """The crop's width as a share of the picture's at zoom 1 (cover-fit: a wider picture keeps its full height)."""
    _, _, w, h = [float(v) for v in L["rect"]]
    return min(1.0, (w / h) / (sw / sh))


def _zooms(L: dict) -> list[float]:
    z = L.get("zoom", 1.0)
    if isinstance(z, (int, float)):
        return [float(z)]
    if isinstance(z, dict):
        vals = [k[1] for k in z.get("keys", [])] + list(z.get("values", []))
        return [float(v) for v in vals if isinstance(v, (int, float))] or [1.0]
    return [1.0]


def zoom_max(L: dict) -> float:
    return max([1.0] + _zooms(L))


def held_zoom(L: dict, curves: dict | None = None) -> tuple[float, float]:
    """The zoom a shot holds (HELD_Q of its frames at it or under) and its lowest - at least 1 each, frame by frame
    as compose draws it (a number, keys, a curve of frames, a named curve)."""
    from .compose import Curve
    c = Curve(L.get("zoom"), curves or {}, 1.0)
    zs = np.array([max(1.0, float(c(f))) for f in range(int(L["start"]), int(L["end"]) + 1)] or [1.0])
    return round(float(np.quantile(zs, HELD_Q)), 4), round(float(zs.min()), 4)


def text_lines(lum: np.ndarray) -> list:
    """Lines of text burned into one light frame (its luma) - subtitles, a chyron, a title, not the room's own words:
    [[x0, y0, x1, y1]] as shares - the strokes joined into lines, wide, near the top or the bottom, letter edges all
    along (TEXT_*)."""
    import cv2
    h, w = lum.shape
    m = np.zeros((h, w), np.uint8)                     # the letters' sides: a step left to right (a floor's edge,
    m[:, 1:] = np.abs(np.diff(lum, axis=1)) >= TEXT_EDGE   # a shelf's, none)
    k = max(3, int(round(w * 0.012)))                  # (letters and words joined: 6 px on a 480 px light frame)
    j = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (k, 1)))
    run = max(6, int(TEXT_W * w / 3))                  # short runs dropped: the legs, hands or a door's side that touch
    j = cv2.morphologyEx(j, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (run, 1)))   # a line stay out
    n, _, st, _ = cv2.connectedComponentsWithStats(j, connectivity=8)
    out = []
    for i in range(1, n):
        x, y, bw, bh, area = (int(v) for v in st[i])
        if not (TEXT_H[0] * h <= bh <= TEXT_H[1] * h and bw >= TEXT_W * w and bw >= 3 * bh and area >= 0.45 * bw * bh):
            continue
        if TEXT_BANDS[0] <= (y + bh / 2) / h <= TEXT_BANDS[1]:
            continue
        mid = lum[y + bh // 3:y + bh - bh // 3, x:x + bw]                     # its middle third: the letters' sides
        step = (np.abs(np.diff(mid, axis=1)) >= TEXT_EDGE).astype(np.int8)    # (a step left to right, counted once)
        if (np.diff(step, axis=1) == 1).sum() / max(1, mid.shape[0]) / bw < TEXT_STROKES:
            continue
        out.append([round(x / w, 4), round(y / h, 4), round((x + bw) / w, 4), round((y + bh) / h, 4)])
    return out


def burned_text(F, idx: list, frames: list) -> list:
    """The text lines that stay at one place through a shot (TEXT_SHARE of its samples; idx = their source frames,
    frames = their plan frames): [{"box": [x0, y0, x1, y1] (the widest seen), "frames": [plan frames seen]}]."""
    groups: list[dict] = []
    for f, i in zip(frames, idx):
        for b in text_lines(F.luma(i)):
            cy = (b[1] + b[3]) / 2
            for g in groups:
                if abs(g["cy"] - cy) <= 0.03 and b[0] < g["box"][2] and g["box"][0] < b[2]:
                    g["box"] = [min(g["box"][0], b[0]), min(g["box"][1], b[1]), max(g["box"][2], b[2]),
                                max(g["box"][3], b[3])]
                    if g["frames"][-1] != f:
                        g["frames"].append(f)
                    break
            else:
                groups.append({"cy": cy, "box": list(b), "frames": [f]})
    return [g for g in groups if len(g["frames"]) >= TEXT_SHARE * len(frames)]


def text_cut(lines: list, crops) -> list:
    """The lines a framing cuts: crops(f) = [(crop centre x, width, centre y, height)] at plan frame f, shares - one
    per panel; a line is cut when no crop holds it whole (TEXT_PAD inside) in most of the frames it is seen in."""
    cut = []
    for g in lines:
        x0, y0 = max(0.0, g["box"][0] - TEXT_PAD), max(0.0, g["box"][1] - TEXT_PAD)
        x1, y1 = min(1.0, g["box"][2] + TEXT_PAD), min(1.0, g["box"][3] + TEXT_PAD)
        miss = sum(1 for f in g["frames"] if not any(
            cx - cw / 2 <= x0 + 1e-6 and x1 - 1e-6 <= cx + cw / 2 and cy - ch / 2 <= y0 + 1e-6 and y1 - 1e-6 <= cy + ch / 2
            for cx, cw, cy, ch in crops(f)))
        if miss > 0.5 * len(g["frames"]):
            cut.append(g)
    return cut


def panel_y(fc: float, fh: float, ch: float, py: float, ph: float, W: float, H: float, lo: float = 0.0,
            hi: float = 1.0, fy: float = FACE_Y) -> float:
    """A panel's crop centre down the picture (a share): its face (middle fc, height fh - shares of the picture) fy
    down the panel (py, ph: where the panel is, px), moved so its eyes are below the apps' top band and its mouth
    above their bottom one (safezones "all", an upright video; the chin may go under it, as captions may cover it)
    where the panel allows; the crop (ch high) inside lo..hi."""
    k = ph / ch                                        # output px per share of the picture, down the panel
    Y = py + fy * ph
    top, bottom = safe_band(W, H)
    hy = fh * k
    a, b = max(py, top + 0.2 * hy), min(py + ph, bottom - 0.32 * hy)        # (face_box: the eyes, the mouth)
    Y = min(max(Y, a), b) if a <= b else a
    return round(float(min(max(fc - (Y - py - 0.5 * ph) / k, lo + ch / 2), hi - ch / 2)), 4)


def pick(fs: list, prev: list | None) -> list | None:
    """The shot's subject in one sample: the biggest face, then the one nearest to the last pick among the big ones."""
    if not fs:
        return None
    big = max(f[2] * f[3] for f in fs)
    cand = [f for f in fs if f[2] * f[3] >= 0.5 * big]
    if prev is None:
        return max(cand, key=lambda f: f[2] * f[3])
    return min(cand, key=lambda f: abs(f[0] - prev[0]))


def people(fs: list) -> list:
    """The faces of one sample that count as people: PERSON_SHARE of its biggest face's area or more."""
    if not fs:
        return []
    big = max(q[2] * q[3] for q in fs)
    return [q for q in fs if q[2] * q[3] >= PERSON_SHARE * big]


def group(ps: list) -> tuple | None:
    """Several faces as one box for decide(): (its middle x, its width)."""
    if not ps:
        return None
    lo, hi = min(q[0] - q[2] / 2 for q in ps), max(q[0] + q[2] / 2 for q in ps)
    return (lo + hi) / 2, hi - lo


def two_tracks(ppl: list) -> tuple[list, list]:
    """[(frame, people)] -> the left and the right person per sample ([(frame, face | None)] each): the two biggest
    faces by x; a sample with one face gives it to the side it is nearest to (from the last two seen)."""
    left, right, last = [], [], None
    for f, p in ppl:
        two = sorted(sorted(p, key=lambda q: -q[2] * q[3])[:2], key=lambda q: q[0])
        if len(two) == 2:
            left.append((f, two[0]))
            right.append((f, two[1]))
            last = [two[0][0], two[1][0]]
        elif len(two) == 1 and last is not None:
            q = two[0]
            k = 0 if abs(q[0] - last[0]) <= abs(q[0] - last[1]) else 1
            left.append((f, q if k == 0 else None))
            right.append((f, q if k == 1 else None))
            last[k] = q[0]
        else:
            left.append((f, None))
            right.append((f, None))
    return left, right


def _ease(t: float) -> float:
    return t * t * (3 - 2 * t)


def value_at(keys: list, f: float) -> float:
    """A key list's value at frame f - "smooth" (S-curve) or flat / linear after a key (compose.Curve's way)."""
    if f <= keys[0][0]:
        return float(keys[0][1])
    for a, b in zip(keys, keys[1:]):
        if a[0] <= f <= b[0]:
            t = (f - a[0]) / max(1e-9, b[0] - a[0])
            t = _ease(t) if (a[2] if len(a) > 2 else "linear") == "smooth" else t
            return float(a[1]) + (float(b[1]) - float(a[1])) * t
    return float(keys[-1][1])


def x_at(d: dict, f: float) -> float:
    """A decision's crop centre at frame f."""
    return float(d["x"]) if d["mode"] == "hold" else value_at(d["keys"], f)


def decide(samples: list, cw: float, fps: float, close_up: bool = True) -> dict:
    """samples = [(plan frame, (face centre x, face width) | None)] of one shot; cw = the crop's width share ->
    {"mode": "hold", "x"} | {"mode": "follow", "keys", "pans", "inside"} | {"mode": "keep", "why"}. close_up=False for
    a group's box (several people: its width is real, not a close-up's)."""
    have = [(f, p) for f, p in samples if p is not None]
    if not have or len(have) < FACE_SHARE_MIN * len(samples):
        return {"mode": "keep", "why": "no face to frame on"}
    usable = cw * (1 - 2 * MARGIN)
    lo_c, hi_c = cw / 2, 1 - cw / 2
    clamp = lambda c: round(float(min(max(c, lo_c), hi_c)), 4)              # noqa: E731
    cx = np.array([p[0] for _, p in have], float)
    fw = np.array([p[1] for _, p in have], float)
    if len(cx) >= 3:                                   # one stray detection does not split a still stretch
        cx = np.array([np.median(cx[max(0, k - 1):k + 2]) for k in range(len(cx))])
        fw = np.array([np.median(fw[max(0, k - 1):k + 2]) for k in range(len(fw))])
    if close_up:
        fw = np.minimum(fw, CLOSE_UP * cw)             # a close-up wider than the crop: its middle is what to keep
    left, right = cx - fw / 2, cx + fw / 2
    q = (1 - HOLD_SHARE) / 2
    lo, hi = float(np.quantile(left, q)), float(np.quantile(right, 1 - q))
    if hi - lo <= usable:
        c = (lo + hi) / 2
        if abs(c - 0.5) <= SNAP * cw:
            c = 0.5
        return {"mode": "hold", "x": clamp(c)}
    # still stretches: grow while the faces' span fits the crop (with its margins), then start a new one
    segs, k0, slo, shi = [], 0, left[0], right[0]
    for k in range(1, len(have)):
        nlo, nhi = min(slo, left[k]), max(shi, right[k])
        if nhi - nlo <= usable:
            slo, shi = nlo, nhi
        else:
            segs.append([k0, k - 1, slo, shi])
            k0, slo, shi = k, left[k], right[k]
    segs.append([k0, len(have) - 1, slo, shi])
    short = max(1, int(round(MIN_HOLD_S * SAMPLE_FPS)))
    merged = True
    while merged and len(segs) > 1:                    # a short stretch joins the neighbour nearest to it
        merged = False
        for i, s in enumerate(segs):
            if s[1] - s[0] + 1 < short:
                c = (s[2] + s[3]) / 2
                nb = [j for j in (i - 1, i + 1) if 0 <= j < len(segs)]
                j = min(nb, key=lambda j: abs((segs[j][2] + segs[j][3]) / 2 - c))
                a, b = sorted((i, j))
                segs[a] = [segs[a][0], segs[b][1], min(segs[a][2], segs[b][2]), max(segs[a][3], segs[b][3])]
                del segs[b]
                merged = True
                break
    cs = [clamp((s[2] + s[3]) / 2) for s in segs]
    out_s, out_c = [segs[0]], [cs[0]]                  # neighbours closer than MIN_MOVE: one still crop
    for s, c in zip(segs[1:], cs[1:]):
        if abs(c - out_c[-1]) < MIN_MOVE:
            p = out_s[-1]
            out_s[-1] = [p[0], s[1], min(p[2], s[2]), max(p[3], s[3])]
            out_c[-1] = clamp((out_s[-1][2] + out_s[-1][3]) / 2)
        else:
            out_s.append(s)
            out_c.append(c)
    f0, f1 = samples[0][0], samples[-1][0]
    if len(out_c) == 1:
        return {"mode": "hold", "x": out_c[0], "wide": True}
    keys, last_end = [[f0, out_c[0], "linear"]], f0
    for i in range(1, len(out_c)):
        ca, cb = out_c[i - 1], out_c[i]
        fb = (have[out_s[i - 1][1]][0] + have[out_s[i][0]][0]) / 2
        dur = max(EASE_MIN_F, int(math.ceil(1.5 * abs(cb - ca) / (PAN_MAX * cw) * fps)))
        a = int(round(fb - dur / 2))
        a = max(a, last_end, f0)
        b = min(a + dur, f1)
        if b - a < 2:
            continue
        if a == keys[-1][0]:
            keys[-1] = [a, ca, "smooth"]
        else:
            keys.append([a, ca, "smooth"])
        keys.append([b, cb, "linear"])
        last_end = b
    if keys[-1][0] < f1:
        keys.append([f1, keys[-1][1], "linear"])

    def inside_of(ks):
        return sum(1 for (f, _), l, r in zip(have, left, right)
                   if value_at(ks, f) - cw / 2 <= l + 1e-6 and r - 1e-6 <= value_at(ks, f) + cw / 2) / len(have)
    # pans that touch (one ends where the next starts) = one longer eased pan - an S-curve stops at both ends, so
    # back to back they would stop and go; kept apart only when the long one would lose the face
    joined = [keys[0]]
    for k in keys[1:]:
        if len(joined) >= 2 and joined[-1][2] == "smooth" and joined[-2][2] == "smooth":
            joined.pop()                               # it ends one pan and starts the next: the stop goes
        joined.append(k)
    one = [list(k) for k in joined]
    for i in range(len(one) - 1):                      # a pan's speed check after joining
        if one[i][2] == "smooth":
            span = one[i + 1][0] - one[i][0]
            if 1.5 * abs(one[i + 1][1] - one[i][1]) / max(1, span) * fps > PAN_MAX * cw * 1.02:
                one = None
                break
    if one is not None and inside_of(one) >= min(FOLLOW_INSIDE, inside_of(keys)):
        keys = one
    return {"mode": "follow", "keys": keys, "pans": sum(1 for k in keys if k[2] == "smooth"),
            "inside": round(inside_of(keys), 3)}


def _ok(d: dict) -> bool:
    """A crop decision that keeps its subject: a hold, or a follow that is not too fast."""
    return d["mode"] == "hold" or (d["mode"] == "follow" and d["inside"] >= FOLLOW_INSIDE)


def _median_hold(samples: list, cw: float) -> dict:
    """One still crop on the subject's middle (when even a wider crop cannot follow it)."""
    xs = [p[0] for _, p in samples if p is not None]
    return {"mode": "hold", "x": round(float(min(max(np.median(xs), cw / 2), 1 - cw / 2)), 4)}


def split(left: list, right: list, cwp: float, zcap: float, zlo: float, zhi: float, fps: float, force: bool = False):
    """Two people in two stacked panels: left / right = [(frame, face | None)]; cwp = a panel's crop width share at
    zoom 1; zcap = the panels' highest zoom (UPSCALE_MAX); zlo / zhi = the clip's own lowest / highest zoom -> ((zoom,
    decision) for each) or None when no zoom up to zcap keeps the other face out of both (force = the user asked for a
    split: then the closest zcap gets)."""
    def med_w(t):
        ws = [q[2] for _, q in t if q is not None]
        return float(np.median(ws)) if ws else 0.0
    wl, wr = med_w(left), med_w(right)
    if not wl or not wr:
        return None
    base = [min(zcap, max(1.0, SPLIT_FACE * cwp / w)) for w in (wl, wr)]

    def intrudes(d, other, cw):
        both = [(f, q) for f, q in other if q is not None]
        if not both:
            return 0.0
        hit = 0
        for f, q in both:
            c = x_at(d, f)
            if q[0] + q[2] / 2 > c - cw / 2 - SPLIT_GAP and q[0] - q[2] / 2 < c + cw / 2 + SPLIT_GAP:
                hit += 1
        return hit / len(both)
    t = 1.0
    while True:
        zs = [min(zcap, b * t) for b in base]
        ds = [decide([(f, (q[0], q[2]) if q else None) for f, q in side], cwp / (z * zhi), fps)
              for side, z in zip((left, right), zs)]
        if any(d["mode"] == "keep" for d in ds) or not (force or all(_ok(d) for d in ds)):
            return None
        if (intrudes(ds[0], right, cwp / (zs[0] * zlo)) <= SPLIT_INTRUDE
                and intrudes(ds[1], left, cwp / (zs[1] * zlo)) <= SPLIT_INTRUDE):
            return list(zip(zs, ds))
        if all(z >= zcap - 1e-9 for z in zs):
            return list(zip(zs, ds)) if force else None
        t *= 1.06


def plain_colour(frames: list, cx: float, cw: float, cy: float = 0.5, ch: float = 1.0) -> str | None:
    """Fit's backdrop: the colour of a plain background - the band's top and bottom rows (6 % of it each, light RGB
    frames of the shot; the crop centred on cx, cy, cw x ch of the picture) even and alike - as "#RRGGBB", else None
    (a blurred copy)."""
    if not frames:
        return None
    h, w = frames[0].shape[:2]
    x0, x1 = int(max(0, (cx - cw / 2) * w)), int(min(w, math.ceil((cx + cw / 2) * w)))
    y0, y1 = int(max(0, round((cy - ch / 2) * h))), int(min(h, round((cy + ch / 2) * h)))
    k = max(1, int(round(0.06 * (y1 - y0))))
    if x1 - x0 < 2 or y1 - y0 < 2 * k:
        return None
    t = np.concatenate([im[y0:y0 + k, x0:x1].reshape(-1, 3) for im in frames]).astype(np.float32) / 255
    b = np.concatenate([im[y1 - k:y1, x0:x1].reshape(-1, 3) for im in frames]).astype(np.float32) / 255
    if max(float(t.std(0).max()), float(b.std(0).max())) > PLAIN_STD or float(np.abs(t.mean(0) - b.mean(0)).max()) > \
            PLAIN_DIFF:
        return None
    return "#" + "".join(f"{int(round(v * 255)):02x}" for v in np.concatenate([t, b]).mean(0))


def _run(mask: np.ndarray, gap: int = 2) -> int:
    """The longest run of True, with gaps of up to `gap` False inside it (noise along a border)."""
    best = cur = miss = 0
    for v in mask:
        if v:
            cur, miss = cur + 1 + miss, 0
            best = max(best, cur)
        elif cur and miss < gap:
            miss += 1
        else:
            cur = miss = 0
    return best


def inset_box(lum: np.ndarray, face: list) -> list | None:
    """A face camera's box round a face ([cx, cy, w, h], shares) in a picture's luma (still across the shot: a
    median) -> [x0, y0, x1, y1] (shares) or None. Its borders are the first straight lines out from the face on each
    side (a step of EDGE along 1.5 face sizes), else the picture's edge; at least one line across and one down must be
    found, each along RUN of the box's side, and the box an inset (half the picture or less, bigger than the face)."""
    h, w = lum.shape
    gx, gy = np.abs(np.diff(lum, axis=1)) >= EDGE, np.abs(np.diff(lum, axis=0)) >= EDGE
    fx0, fx1 = (face[0] - face[2] / 2) * w, (face[0] + face[2] / 2) * w
    fy0, fy1 = (face[1] - face[3] / 2) * h, (face[1] + face[3] / 2) * h
    fw, fh = max(2.0, fx1 - fx0), max(2.0, fy1 - fy0)
    rows = slice(max(0, int(fy0 - 2 * fh)), min(h, int(fy1 + 2 * fh)))
    cols = slice(max(0, int(fx0 - 2 * fw)), min(w, int(fx1 + 2 * fw)))

    def line(g, rng, part, need):
        for c in rng:
            m = g[part, c] if g is gx else g[c, part]
            if m.sum() >= need * 0.5 and _run(m) >= need:              # (most columns fail the count: no loop)
                return c
        return None
    left = line(gx, range(int(fx0) - 1, -1, -1), rows, 1.5 * fh)        # (gx[:, c] = the step from c to c + 1)
    right = line(gx, range(int(math.ceil(fx1)), w - 1), rows, 1.5 * fh)
    top = line(gy, range(int(fy0) - 1, -1, -1), cols, 1.5 * fw)
    bottom = line(gy, range(int(math.ceil(fy1)), h - 1), cols, 1.5 * fw)
    if (left is None and right is None) or (top is None and bottom is None):
        return None
    x0, x1 = (left + 1 if left is not None else 0), (right + 1 if right is not None else w)
    y0, y1 = (top + 1 if top is not None else 0), (bottom + 1 if bottom is not None else h)
    bw, bh = x1 - x0, y1 - y0
    if not (1.4 * fw <= bw <= 0.5 * w and 1.2 * fh <= bh <= 0.55 * h):
        return None
    for c in (left, right):                            # each line found: straight along the box's side
        if c is not None and _run(gx[y0:y1, c]) < RUN * bh:
            return None
    for c in (top, bottom):
        if c is not None and _run(gy[c, x0:x1]) < RUN * bw:
            return None
    return [round(x0 / w, 4), round(y0 / h, 4), round(x1 / w, 4), round(y1 / h, 4)]


def find_inset(F, idx: list, faces: list) -> dict | None:
    """A face camera boxed into the shot: idx = its sampled source frames, faces = their faces -> {"box", "face",
    "moving" (the mean luma change round it, of 255), "action" (where the rest changes most, x share)} or None."""
    cand = [q for fs in faces for q in fs
            if q[2] <= INSET_FACE and (abs(q[0] - 0.5) >= INSET_OFF or abs(q[1] - 0.5) >= INSET_OFF)]
    if not cand:
        return None
    mx, my = float(np.median([q[0] for q in cand])), float(np.median([q[1] for q in cand]))
    near = []
    for fs in faces:
        q = min(fs, key=lambda q: abs(q[0] - mx) + abs(q[1] - my), default=None)
        if q is not None and abs(q[0] - mx) <= 2 * INSET_STILL and abs(q[1] - my) <= 2 * INSET_STILL:
            near.append(q)
    if len(near) < INSET_SHARE * len(faces) or np.std([q[0] for q in near]) > INSET_STILL \
            or np.std([q[1] for q in near]) > INSET_STILL:
        return None
    face = [float(np.median([q[k] for q in near])) for k in range(4)]
    pick_i = idx[::max(1, len(idx) // 9)][:9]
    lums = [F.luma(i) for i in pick_i]
    box = inset_box(np.median(np.stack(lums), 0), face)
    if box is None:
        return None
    out = np.ones(lums[0].shape, bool)                 # the picture round the camera: how much it changes, and where
    out[int(box[1] * F.h):int(math.ceil(box[3] * F.h)), int(box[0] * F.w):int(math.ceil(box[2] * F.w))] = False
    diffs = [np.abs(b - a) for a, b in zip(lums, lums[1:])]
    moving = float(np.mean([d[out].mean() for d in diffs])) if diffs else 0.0
    act = 0.5
    if diffs:
        col = (np.mean(diffs, 0) * out).sum(0)
        if col.sum() > 1e-6:
            cs = np.cumsum(col)
            act = float((np.searchsorted(cs, cs[-1] / 2) + 0.5) / F.w)
    return {"box": box, "face": face, "moving": round(moving, 2), "action": round(act, 4)}


def face_box(fc: float, fh: float, ch: float, cy: float, py: float, ph: float) -> tuple[float, float]:
    """Where a panel shows its face (middle fc, height fh - shares of the picture; the crop ch high centred at cy):
    (its eyes' y, its mouth's y) in frame px (facefit: the eyes 0.3 and the mouth 0.82 down a face's box)."""
    k = ph / ch
    Y, hy = py + ph * 0.5 + (fc - cy) * k, fh * k
    return Y - 0.2 * hy, Y + 0.32 * hy


def safe_band(W: float, H: float) -> tuple[float, float]:
    """The height a face's eyes and chin keep inside (SAFE_PAD in from the apps' bands; the whole frame when the video
    is not upright)."""
    from . import safezones as SZ
    if not SZ.upright(W, H):
        return 0.0, H
    return SZ.ZONES["all"]["top"] * H / SZ.REF_H + SAFE_PAD, H - SZ.ZONES["all"]["bottom"] * H / SZ.REF_H - SAFE_PAD


def cam_view(box: list, face: list, pa: float, sa: float, place: tuple | None = None) -> tuple[float, float, float]:
    """A panel of aspect pa (width / height) on a face camera's box (shares) of a picture of aspect sa -> (zoom, crop
    centre x, y): the crop inside the box, the face FACE_Y down it - place = (the panel's y, its height, the video's
    W, H): placed by panel_y (inside the apps' safe area where the box allows)."""
    cw1, ch1 = min(1.0, pa / sa), min(1.0, sa / pa)
    bw, bh = box[2] - box[0], box[3] - box[1]
    box = [box[0] + INSET_PAD * bw, box[1] + INSET_PAD * bh, box[2] - INSET_PAD * bw, box[3] - INSET_PAD * bh]
    bw, bh = bw * (1 - 2 * INSET_PAD), bh * (1 - 2 * INSET_PAD)
    z = max(1.0, cw1 / bw, ch1 / bh)
    cw, ch = cw1 / z, ch1 / z
    cx = min(max(face[0], box[0] + cw / 2), box[2] - cw / 2)
    cy = (panel_y(face[1], face[3], ch, *place, lo=box[1], hi=box[3]) if place else
          min(max(face[1] + (0.5 - FACE_Y) * ch, box[1] + ch / 2), box[3] - ch / 2))
    return round(z, 4), round(cx, 4), round(cy, 4)


def _source(P: dict, L: dict):
    from .person import source_of
    spec = P.get("sources", {}).get(L.get("src"))
    return source_of(spec) if spec else None


def _ours(L: dict, replace_static: bool) -> str:
    """Why this clip's crop is not ours to change ("" = it is)."""
    if L.get("fit") == "contain":
        return "shown whole (contain)"
    if L.get("track") == "face":
        return "it follows the face by itself"
    if L.get("panels") and not L.get("reframe"):
        return "a layout set for it"
    if (L.get("reframe") or {}).get("by") == "user":
        return "framed by the user"
    an = L.get("anchor")
    if an is None or L.get("reframe"):
        return ""
    if isinstance(an, list) and len(an) == 2 and all(isinstance(a, (int, float)) for a in an):
        return "" if replace_static else "a point set for it (replace_static to change it)"
    return "its own moves (a shake or keyframes)"


def _undo(L: dict) -> None:
    """A clip framed by an earlier run back to how it was (its layout gone, its own crop height back)."""
    rf = L.pop("reframe", None) or {}
    for k in ("panels", "backdrop"):
        L.pop(k, None)
    an = L.get("anchor")
    if "ay0" in rf and isinstance(an, list) and len(an) == 2:
        an[1] = rf["ay0"]
        if "ax0" in rf:                                # (step 4: its own point back - a "keep" now leaves it as it was)
            an[0] = rf["ax0"]
            if an == [0.5, 0.5] and rf.get("bare"):
                L.pop("anchor")


def _x(d: dict):
    return d["x"] if d["mode"] == "hold" else {"keys": d["keys"]}


def _crop_words(d: dict, tc) -> str:
    if d["mode"] == "hold":
        return f"hold at x {d['x']:.3f}"
    return (f"follow - {d['pans']} pan(s) at " + ", ".join(f"f{k[0]} ({tc(k[0])})" for k in d["keys"]
                                                         if k[2] == "smooth"))


def layout(L: dict, F: Faces, samples: list, P: dict, fps: float, want: str | None = None) -> dict:
    """One shot's layout: samples = [(plan frame, its faces)] -> {"layout", "mode", "x", ("y"), ("panels"),
    ("backdrop"), "words"} or {"layout": "keep", "why"}. Step 4's limits: decided on the zoom the shot holds; a fill
    past UPSCALE_MAX, or one that would cut text burned into the picture, is a fit (its band wide enough for the text);
    a panel's face inside the apps' safe area. want = the layout the user chose (fill / fit / split / screen /
    game, step 5): that one, the limits aside - FrameError when the shot cannot have it."""
    from . import safezones as SZ
    W, H = float(P["width"]), float(P["height"])
    tc = lambda f: frame_to_tc(f, fps)                                      # noqa: E731
    sa = F.w / F.h
    sw = float((P.get("sources", {}).get(L.get("src")) or {}).get("width") or F.w * 4)
    zhi, zlo = held_zoom(L, P.get("curves"))
    frames = [f for f, _ in samples]
    idx = [src_index(L, f) for f in frames]
    faces = [fs for _, fs in samples]
    cw = crop_share(L, F.w, F.h)
    ch1 = min(1.0, sa / (W / H))                       # a fill's crop height at zoom 1 (a wider picture: all of it)
    cwf = min(1.0, FIT_ASPECT / sa)
    an = L.get("anchor")
    ay0 = an[1] if isinstance(an, list) and len(an) == 2 and isinstance(an[1], (int, float)) else 0.5
    x0 = an[0] if isinstance(an, list) and len(an) == 2 and isinstance(an[0], (int, float)) else 0.5
    found: list = []                                   # the text burned in, looked for once (only when it matters)

    def text() -> list:
        if not found:
            found.append(burned_text(F, idx, frames))
        return found[0]

    def mid_y(cy: float, ch: float) -> float:
        return min(max(cy, ch / 2), 1 - ch / 2)

    def fill_crops(d: dict, cy: float = ay0):          # a fill's crop at a plan frame, as text_cut takes it
        ch = ch1 / zhi
        return lambda f: [(x_at(d, f), cw / zhi, mid_y(cy, ch), ch)]

    def fit(subj: list, why: str, ppl: list | None = None) -> dict:
        """ppl = a group's people per sample: the band zoomed in on them (their widest span with its margins, the
        upscale at most UPSCALE_MAX) and their faces FACE_Y down it; a person on their own: the whole band. Text
        burned in: the band as wide as it needs (up to the whole picture) and the crop kept round it, no zoom in."""
        tl = text()
        need = max([g["box"][2] - g["box"][0] + 2 * TEXT_PAD for g in tl], default=0.0)
        cwt = min(1.0, max(cwf, need * zhi))           # (at the shot's own zoom)
        bh = round(W / (cwt * sa))
        band = [0, round((H - bh) / 2), round(W), bh]
        zb, y = 1.0, None
        if ppl and not tl:
            wid = [g[1] for _, g in subj if g is not None]
            zcap = max(1.0, UPSCALE_MAX * cwt * sw / W / zhi)
            zb = round(min(zcap, max(1.0, cwt * (1 - 2 * MARGIN) / max(1e-3, float(np.quantile(wid, HOLD_SHARE))))), 4)
            if zb > 1:
                ys = [float(np.mean([q[1] for q in p])) for _, p in ppl if len(p) >= 2]
                hs = [float(np.mean([q[3] for q in p])) for _, p in ppl if len(p) >= 2]
                y = panel_y(float(np.median(ys)), float(np.median(hs)), 1.0 / (zb * zhi), band[1], bh, W, H)
        if tl and zhi > 1:                             # zoomed: the crop's height kept round the text too
            ch = 1.0 / zhi
            a = max(g["box"][3] for g in tl) + TEXT_PAD - ch / 2
            b = min(g["box"][1] for g in tl) - TEXT_PAD + ch / 2
            y = round(mid_y(min(max(ay0, a), b) if a <= b else a, ch), 4)
        cwc = cwt / (zb * zhi)
        d = decide(subj, cwc, fps, close_up=not ppl)
        if d["mode"] == "keep":
            return {"layout": "keep", "why": d["why"]}
        if not _ok(d):
            d, why = _median_hold(subj, cwc), why + (" - wider than the band too: held on their middle" if ppl else
                                                     " - too fast even for a fit: held on its middle")
        if tl:                                         # the crop's centre where the text stays inside it
            a = max(g["box"][2] for g in tl) + TEXT_PAD - cwc / 2
            b = min(g["box"][0] for g in tl) - TEXT_PAD + cwc / 2
            if a <= b:
                hold = lambda v: round(float(min(max(v, a, cwc / 2), b, 1 - cwc / 2)), 4)   # noqa: E731
                d = ({**d, "x": hold(d["x"])} if d["mode"] == "hold" else
                     {**d, "keys": [[k[0], hold(k[1]), *k[2:]] for k in d["keys"]]})
            why += (f"; text burned in kept whole ({len(tl)} line(s))" if need * zhi <= 1 + 1e-6 else
                    f"; text burned in wider than the shot's own zoom (x{zhi:.2f}) lets it keep")
        mid = [x_at(d, f) for f in frames]
        c = plain_colour([F.rgb(i) for i in idx[::max(1, len(idx) // 8)][:8]], float(np.median(mid)), cwc,
                         y if y is not None else mid_y(ay0, 1.0 / (zb * zhi)), 1.0 / (zb * zhi))
        out = {"layout": "fit", "mode": d["mode"], "x": _x(d), "panels": [{"rect": band}], "backdrop": c or "blur",
               "words": f"fit (the picture in a {cwt * sa:.2f}:1 band{f' at zoom {zb:.2f}' if zb > 1 else ''} over "
                        f"{c or 'a blurred copy'}) - {_crop_words(d, tc)} - {why}"}
        if zb > 1:
            out["panels"][0]["zoom"] = zb
        if y is not None:
            out["y"] = y
        if tl:                                         # (facefit keeps the captions off it)
            out["text"] = [[round(v, 4) for v in g["box"]] for g in tl]
        return out

    def no_face(why: str) -> dict:
        """No face to frame on: kept as it was (the catalogue's point) - unless that crop cuts text burned in: then a
        fit, placed round the text."""
        x0 = an[0] if isinstance(an, list) and len(an) == 2 and isinstance(an[0], (int, float)) else 0.5
        here = {"mode": "hold", "x": round(min(max(x0, cw / zhi / 2), 1 - cw / zhi / 2), 4)}
        if not text_cut(text(), fill_crops(here)):
            return {"layout": "keep", "why": why}
        return fit([(f, (x0, 0.01)) for f in frames], f"{why}, and its crop would cut text burned in")

    def fill(d: dict, words: str, fallback) -> dict:
        """A fill - unless it blows the picture up past UPSCALE_MAX or cuts text burned in: then fallback(why) (a
        fill the user chose: a fill)."""
        if want == "fill":
            return {"layout": "fill", "mode": d["mode"], "x": _x(d), "words": words}
        up = W / (cw * sw) * zhi
        if up > UPSCALE_MAX + 1e-6:
            return fallback(f"a fill would blow the picture up {up:.1f}x (the cap {UPSCALE_MAX}x)")
        cut = text_cut(text(), fill_crops(d))
        if cut:
            return fallback(f"a fill would cut {len(cut)} line(s) of text burned in")
        return {"layout": "fill", "mode": d["mode"], "x": _x(d), "words": words}

    ins = find_inset(F, idx, faces) if want in (None, "screen", "game") else None
    if want in ("screen", "game") and ins is None:
        raise FrameError(I18N.t("no face camera boxed into this shot"))
    if ins is not None:                                # a face camera boxed in: a screen recording or a game
        game = want == "game" if want else ins["moving"] >= STILL
        bottom = round(H - SZ.ZONES["all"]["bottom"] * H / SZ.REF_H) if SZ.upright(W, H) else round(H)
        if game:                                       # the face on top, the game under it (under the apps' band too)
            cam_h = round(H * GAME_FACE)
            cam, rest = [0, 0, round(W), cam_h], [0, cam_h, round(W), round(H) - cam_h]
        else:                                          # both above the apps' bottom band, the backdrop under it
            hs = round(SCREEN_SHARE * bottom)
            rest, cam = [0, 0, round(W), hs], [0, hs, round(W), bottom - hs]
        zc, cx, cy = cam_view(ins["box"], ins["face"], W / cam[3], sa, (cam[1], cam[3], W, H))
        up = zc * zhi * W / (min(1.0, (W / cam[3]) / sa) * sw)
        cwr = min(1.0, (rest[2] / rest[3]) / sa)
        ax = round(min(max(0.5 if game else ins["action"], cwr / 2), 1 - cwr / 2), 4)
        b = ins["box"]
        words = (f"the face camera (its box x {b[0]:.2f}-{b[2]:.2f}, y {b[1]:.2f}-{b[3]:.2f}; zoom {zc:.2f}, an upscale "
                 f"of {up:.1f}x{' - soft' if up > UPSCALE_MAX else ''})")
        if game:                                       # (panel 0 = the clip's own crop centre)
            # its eyes under the apps' top band: the box leaves the crop no room, so the panel moves down instead (the
            # backdrop above it)
            eyes, _ = face_box(ins["face"][1], ins["face"][3], min(1.0, sa / (W / cam[3])) / zc, cy, 0, cam[3])
            dy = max(0, round(safe_band(W, H)[0] - eyes))
            out = {"layout": "game", "mode": "hold", "x": cx, "y": cy,
                   "panels": [{"rect": [0, dy, round(W), cam[3]], "zoom": zc},
                              {"rect": [0, dy + cam[3], round(W), round(H) - dy - cam[3]], "anchor": [ax, 0.5]}],
                   "words": f"game - {words} on top{f' (moved {dy} px down, under the top band)' if dy else ''}, the "
                            f"game below (it keeps moving: {ins['moving']:.1f} of 255)"}
            if dy:
                out["backdrop"] = "blur"
            return out
        out = {"layout": "screen", "mode": "hold", "x": ax, "y": 0.5,
               "panels": [{"rect": rest}, {"rect": cam, "zoom": zc, "anchor": [cx, cy]}],
               "words": f"screen + face - the screen on top (round x {ax:.2f}, where it changes), {words} below"}
        if bottom < round(H):
            out["backdrop"] = "blur"
        return out
    ppl = [(f, people(fs)) for f, fs in samples]
    seen = [p for _, p in ppl if p]
    if not seen or len(seen) < FACE_SHARE_MIN * len(ppl):
        if want == "split":
            raise FrameError(I18N.t("no one to split in this shot"))
        if want == "fit":                              # (the user's: round its own point)
            return fit([(f, (x0, 0.01)) for f in frames], "a fit chosen for it")
        if want == "fill":
            return {"layout": "fill", "mode": "hold", "x": round(min(max(x0, cw / zhi / 2), 1 - cw / zhi / 2), 4),
                    "words": "fill - its own point (no face to frame on)"}
        return no_face("no face to frame on")

    def many(p, k):                                    # k people of a size, the k-th biggest at least TWO_SIZE of it
        a = sorted((q[2] * q[3] for q in p), reverse=True)
        return len(a) >= k and a[k - 1] >= TWO_SIZE * a[0]
    n2, n3 = sum(many(p, 2) for p in seen), sum(many(p, 3) for p in seen)
    two = n2 >= (FACE_SHARE_MIN if want == "split" else TWO_SHARE) * len(seen)   # (asked for: two now and then)
    if want == "split" and not two:
        raise FrameError(I18N.t("only one person in this shot - a split needs two"))
    if two:
        grp = [(f, group(p) if len(p) >= 2 else None) for f, p in ppl]
        wid = [g[1] for _, g in grp if g is not None]
        usable = cw / zhi * (1 - 2 * MARGIN)
        some = "two" if n3 < TWO_SHARE * len(seen) else "group"
        if want == "fit":
            return fit(grp, "a fit chosen for it", ppl)
        if want != "split" and float(np.quantile(wid, HOLD_SHARE)) <= usable:   # they fit together: one crop
            d = decide(grp, cw / zhi, fps, close_up=False)
            if d["mode"] != "keep" and (_ok(d) or want == "fill"):
                return fill(d, f"fill - on the {some} together - {_crop_words(d, tc)}",
                            lambda why: fit(grp, f"the {some} together: {why}", ppl))
        if want is None and n3 >= TWO_SHARE * len(seen):
            return fit(grp, "three or more people, too wide for one crop", ppl)
    if two and want != "fill":                         # (a fill of people too wide for one crop: on the main one)
        left, right = two_tracks(ppl)
        half = round(H / 2)
        pa = W / half
        cwp, chp = min(1.0, pa / sa), min(1.0, sa / pa)
        zcap = max(1.0, UPSCALE_MAX * cwp * sw / W / zhi)
        sp = split(left, right, cwp, zcap, zlo, zhi, fps, force=want == "split")
        if sp is None and want == "split":
            raise FrameError(I18N.t("one of the two is in too few of its frames to split"))
        if sp is None:
            return fit(grp, f"two people too far apart for one crop and too close (or too small) for a split "
                            f"(the upscale capped at {UPSCALE_MAX}x)", ppl)
        (zl, dl), (zr, dr) = sp
        med = lambda side, k: float(np.median([q[k] for _, q in side if q is not None]))     # noqa: E731
        lo_s, hi_s = safe_band(W, H)

        def need(side, z, py, ph) -> float:
            """How much more a panel zooms in (4 % at a time, at most SAFE_ZOOM and zcap) for its face to sit inside
            the apps' safe area - a face low in the picture leaves its crop no room to move down."""
            fc, fh, t = med(side, 1), med(side, 3), 1.0
            most = max(1.0, min(SAFE_ZOOM, SPLIT_FACE_MAX * cwp / max(1e-3, med(side, 2) * z * zhi)))
            while True:
                ch = chp / (min(zcap, z * t) * zhi)
                eyes, mouth = face_box(fc, fh, ch, panel_y(fc, fh, ch, py, ph, W, H), py, ph)
                if (eyes >= lo_s - 1 and mouth <= hi_s + 1) or t >= most - 1e-9 or z * t >= zcap - 1e-9:
                    return t
                t = min(most, t * 1.04)
        t = max(need(left, zl, 0, half), need(right, zr, half, round(H) - half))   # (both: the faces stay alike)

        def at(side, z, d, py, ph):                    # the panel at that zoom, its crop decided again
            z2 = min(zcap, z * t)
            if z2 > z + 1e-9:
                d2 = decide([(f, (q[0], q[2]) if q else None) for f, q in side], cwp / (z2 * zhi), fps)
                if _ok(d2):
                    z, d = z2, d2
            return z, d, panel_y(med(side, 1), med(side, 3), chp / (z * zhi), py, ph, W, H)
        zl, dl, yl = at(left, zl, dl, 0, half)
        zr, dr, yr = at(right, zr, dr, half, round(H) - half)
        cut = text_cut(text(), lambda f: [(x_at(dl, f), cwp / (zl * zhi), yl, chp / (zl * zhi)),
                                          (x_at(dr, f), cwp / (zr * zhi), yr, chp / (zr * zhi))])
        if cut and want != "split":
            return fit(grp, f"a split would cut {len(cut)} line(s) of text burned in", ppl)
        return {"layout": "split", "mode": dl["mode"], "x": _x(dl), "y": yl,
                "panels": [{"rect": [0, 0, round(W), half], "zoom": round(zl, 4)},
                           {"rect": [0, half, round(W), round(H) - half], "zoom": round(zr, 4),
                            "anchor": [_x(dr), yr]}],
                "words": f"split - the left person on top (zoom {zl:.2f}, {_crop_words(dl, tc)}), the right one below "
                         f"(zoom {zr:.2f}, {_crop_words(dr, tc)})"}
    subj, prev = [], None                              # one person: step 1's crop - a fit when it cannot follow
    for f, fs in samples:
        p = pick(fs, prev)
        if p is not None:
            prev = p
        subj.append((f, (p[0], p[2]) if p else None))
    if want == "fit":
        return fit(subj, "a fit chosen for it")
    d = decide(subj, cw / zhi, fps)
    if d["mode"] == "keep":
        return no_face(d["why"]) if want is None else {"layout": "fill", "mode": "hold", "x": round(min(max(
            x0, cw / zhi / 2), 1 - cw / zhi / 2), 4), "words": "fill - its own point (no face to frame on)"}
    if not _ok(d) and want is None:
        return fit(subj, f"too fast to follow in a full-height crop (the face in it in {d['inside'] * 100:.0f} % of "
                         f"the samples)")
    return fill(d, "fill - " + _crop_words(d, tc) + (" (the subject moves, inside one crop)" if d.get("wide") else ""),
                lambda why: fit(subj, why))


def _frames(L: dict, fps: float) -> list[int]:
    """The plan frames a shot is sampled at (SAMPLE_FPS, its last frame too)."""
    s, e = int(L["start"]), int(L["end"])
    frames = list(range(s, e + 1, max(1, int(round(fps / SAMPLE_FPS)))))
    return frames if frames[-1] == e else frames + [e]


def _write(L: dict, d: dict, by: str | None = None) -> None:
    """A layout decision into the clip (its own point before it kept in the mark; undone first if one was there)."""
    an = L.get("anchor")
    ay0 = an[1] if isinstance(an, list) and len(an) == 2 and isinstance(an[1], (int, float)) else 0.5
    ax0 = an[0] if isinstance(an, list) and len(an) == 2 and isinstance(an[0], (int, float)) else 0.5
    L["anchor"] = [d["x"], d.get("y", ay0)]
    for k in ("panels", "backdrop"):
        if d.get(k):
            L[k] = d[k]
    L["reframe"] = {"mode": d["mode"], "layout": d["layout"], "v": VERSION, "ax0": ax0, "ay0": ay0,
                    **({"bare": True} if an is None else {}), **({"text": d["text"]} if d.get("text") else {}),
                    **({"by": by} if by else {})}


def _held(v, frames: list):
    """A crop centre (a number or {"keys"}) as one still point: a pan's time-weighted middle."""
    if not isinstance(v, dict):
        return v
    return round(float(np.mean([value_at(v["keys"], f) for f in range(frames[0], frames[-1] + 1)])), 4)


def apply(P: dict, replace_static: bool = False, prefer: str | None = None) -> list[str]:
    """Frame every clip of plan P whose picture is wider than its place (in place) -> one line per framed shot.
    prefer = New edit's framing for every shot ("fill" / "fit" / "split"; the rules where a shot cannot have it)."""
    fps, out, tracks = float(P["fps"]), [], {}
    tc = lambda f: frame_to_tc(f, fps)                                      # noqa: E731
    for L in P.get("layers", []):
        if L.get("type") != "clip" or not L.get("rect"):
            continue
        where = _source(P, L)
        if where is None:
            continue
        key = str(where)
        if key not in tracks:
            try:
                tracks[key] = Faces(*where)
            except (OSError, ValueError, KeyError) as e:
                tracks[key] = None
                out.append(f"{L.get('src')}: no light cache to find faces in ({type(e).__name__}) - not framed")
        F = tracks[key]
        if F is None:
            continue
        if crop_share(L, F.w, F.h) >= WIDER:
            continue
        s, e = int(L["start"]), int(L["end"])
        head = f"{L.get('id')} f{s}-f{e} ({tc(s)}-{tc(e)})"
        why = _ours(L, replace_static)
        if why:
            out.append(f"{head}: kept - {why}")
            continue
        if L.get("reframe"):
            _undo(L)
        samples = [(f, F.at(src_index(L, f))) for f in _frames(L, fps)]
        d = None
        if prefer and prefer != "auto":
            try:
                d = layout(L, F, samples, P, fps, want=prefer)
                d["words"] += f" (asked for: {prefer})"
            except FrameError as x:
                out.append(f"{head}: {prefer} asked for, not possible here ({x}) - framed by the rules")
        if d is None:
            d = layout(L, F, samples, P, fps)
        if d["layout"] == "keep":
            out.append(f"{head}: kept - {d['why']}")
            continue
        _write(L, d)
        out.append(f"{head}: {d['words']}")
    for F in tracks.values():
        if F is not None:
            F.save()
    return out


def frame_shot(P: dict, shot: str, layout_: str | None = None, mode: str | None = None, x: float | None = None,
               y: float | None = None, panel: int = 0, save: bool = False) -> str:
    """The user's framing of one shot (the Editor's Framing section, an edit list's `frame` line; step 5) - in place:
    layout_ = one of CHOICES ("auto" = the rules' again, the user's mark gone), mode = "hold" (one still crop) /
    "follow" (the rules' pans), x / y = the crop's centre where they dragged it (shares of the picture; panel = which
    panel) - marked as theirs ("by": "user"), so no automatic run changes it. save = keep the faces found (a tool's
    save; never the app's preview). -> a line with frame + timecode; FrameError (translated) when it cannot be."""
    fps = float(P["fps"])
    L = next((x_ for x_ in P.get("layers", []) if x_.get("type") == "clip" and str(x_.get("id")) == str(shot)), None)
    if L is None:
        raise FrameError(I18N.t("there is no shot {shot}", shot=shot))
    if layout_ is not None and layout_ not in CHOICES:
        raise FrameError(I18N.t("a framing is one of: {choices}", choices=", ".join(CHOICES)))
    if mode is not None and mode not in ("hold", "follow"):
        raise FrameError(I18N.t("a crop is still (hold) or follows (follow)"))
    if L.get("fit") == "contain":
        raise FrameError(I18N.t("this picture is shown whole - it has no crop to frame"))
    if L.get("track") == "face":
        raise FrameError(I18N.t("this shot follows the face by itself"))
    an = L.get("anchor")
    if isinstance(an, list) and any(isinstance(a, dict) and "values" in a for a in an):
        raise FrameError(I18N.t("this shot shakes - remove its shake first"))
    s, e = int(L["start"]), int(L["end"])
    head = f"{L.get('id')} f{s}-f{e} ({frame_to_tc(s, fps)}-{frame_to_tc(e, fps)})"
    rf = L.get("reframe") or {}
    if x is not None:                                  # the crop dragged: that point, still - the layout stays
        ps = L.get("panels") or []
        if panel and not 0 < panel < len(ps):
            raise FrameError(I18N.t("there is no panel {n} in this shot", n=panel + 1))
        x = round(min(max(float(x), 0.0), 1.0), 4)
        if panel:
            pa = ps[panel].get("anchor") or [0.5, 0.5]
            ps[panel]["anchor"] = [x, round(min(max(float(y), 0.0), 1.0), 4) if y is not None else pa[1]]
        else:
            a = an if isinstance(an, list) and len(an) == 2 else [0.5, 0.5]
            if not rf:                                 # (its own point first, for "auto" to bring back)
                rf = {"layout": "fill", "v": VERSION, "ax0": a[0] if isinstance(a[0], (int, float)) else 0.5,
                      "ay0": a[1] if isinstance(a[1], (int, float)) else 0.5, **({"bare": True} if an is None else {})}
            L["anchor"] = [x, round(min(max(float(y), 0.0), 1.0), 4) if y is not None else a[1]]
        L["reframe"] = {**rf, "mode": "hold", "by": "user"}
        return f"{head}: the crop moved by the user to x {x:.3f}" + (f" (panel {panel + 1})" if panel else "")
    where = _source(P, L)
    if where is None:
        raise FrameError(I18N.t("its clip has no light copy to find faces in"))
    F = Faces(*where)
    if crop_share(L, F.w, F.h) >= WIDER:
        raise FrameError(I18N.t("its clip already has the video's shape - there is nothing to frame"))
    want = layout_ or rf.get("layout") or ("fill" if not L.get("panels") else None)
    if rf:
        _undo(L)
    samples = [(f, F.at(src_index(L, f))) for f in _frames(L, fps)]
    try:
        d = layout(L, F, samples, P, fps, want=None if want == "auto" else want)
    finally:
        if save:
            F.save()
    if d["layout"] == "keep":                          # ("auto" on a shot the rules keep: as it was)
        return f"{head}: auto - kept as it was ({d['why']})"
    if mode == "hold" and d["mode"] == "follow":       # one still crop: the pan's middle (each panel's)
        d = {**d, "mode": "hold", "x": _held(d["x"], [f for f, _ in samples])}
        for p in d.get("panels") or []:
            if isinstance((p.get("anchor") or [None])[0], dict):
                p["anchor"] = [_held(p["anchor"][0], [f for f, _ in samples]), p["anchor"][1]]
        d["words"] += " - held still (the user's)"
    elif mode == "follow" and d["mode"] == "hold":
        d["words"] += " - nothing to follow: held"
    _write(L, d, by=None if want == "auto" else "user")
    return f"{head}: {d['words']}"


def summary(lines: list[str]) -> str:
    """apply()'s lines counted: "9 fill (7 held, 2 followed), 2 split, 1 fit, 14 kept"."""
    n: dict[str, int] = {}
    held = fol = 0
    for ln in lines:
        k = ln.split(": ", 1)[1].split(" ", 1)[0] if ": " in ln else "kept"
        k = k if k in ("fill", "split", "fit", "screen", "game") else "kept"
        n[k] = n.get(k, 0) + 1
        if k == "fill":
            held += " hold at " in ln
            fol += " follow - " in ln
    parts = [f"{n[k]} {k}" + (f" ({held} held, {fol} followed)" if k == "fill" else "")
             for k in ("fill", "split", "fit", "screen", "game", "kept") if n.get(k)]
    return ", ".join(parts) or "nothing to frame"


def selfcheck() -> dict:
    t0, lines, ok = time.time(), [], True

    def case(what, cond):
        nonlocal ok
        ok = ok and bool(cond)
        lines.append(("PASS " if cond else "FAIL ") + what)

    fps, cw = 30.0, 0.316                          # a 16:9 picture in a 9:16 place: the crop is 31.6 % of its width
    frames = list(range(0, 300, 6))
    still = decide([(f, (0.42 + 0.004 * math.sin(f / 9), 0.08)) for f in frames], cw, fps)
    case("a talking head that sways a little: one still crop on it (no pan)",
         still["mode"] == "hold" and abs(still["x"] - 0.42) < 0.01)
    mid = decide([(f, (0.505, 0.08)) for f in frames], cw, fps)
    case("a face 0.5 % off the middle: snapped to the middle", mid == {"mode": "hold", "x": 0.5})
    edge = decide([(f, (0.07, 0.06)) for f in frames], cw, fps)
    case("a face at the picture's edge: the crop stops at the edge (no black)", edge["x"] == round(cw / 2, 4))
    walk = [(f, (0.2 + 0.6 * min(1.0, max(0.0, (f - 60) / 150)), 0.08)) for f in frames]
    fol = decide(walk, cw, fps)
    ks = fol.get("keys", [])
    steps = [abs(value_at(ks, f + 1) - value_at(ks, f)) for f in range(0, 299)] if ks else [1]
    case("someone walking across the picture: a hold, ONE eased pan (pans that touch are joined - no stop and go), "
         "a hold; the face in the crop, no pan faster than PAN_MAX crop widths a second, none under EASE_MIN_F frames",
         fol["mode"] == "follow" and fol["pans"] == 1 and fol["inside"] >= FOLLOW_INSIDE
         and max(steps) * fps <= PAN_MAX * cw * 1.02
         and all(b[0] - a[0] >= EASE_MIN_F for a, b in zip(ks, ks[1:]) if a[2] == "smooth")
         and ks[0][0] == 0 and ks[-1][0] == frames[-1])
    close = decide([(f, (0.52 - 0.12 * f / 30, 0.34)) for f in range(0, 31, 6)], cw, fps)
    case("a close-up wider than the crop that drifts 12 % in a second: its middle stays in the crop (not flagged)",
         close["mode"] == "hold" or close["inside"] >= FOLLOW_INSIDE)
    hop = decide([(f, (0.30 if f < 150 else 0.33, 0.08)) for f in frames], cw, fps)
    case("a 3 % move: no pan for it (under MIN_MOVE)", hop["mode"] == "hold")
    blip = [(f, (0.42, 0.08)) for f in frames]
    blip[20] = (blip[20][0], (0.9, 0.05))           # one stray detection on a poster
    case("one stray face in one sample does not move the crop", decide(blip, cw, fps)["mode"] == "hold")
    none = decide([(f, None) for f in frames[:-3]] + [(f, (0.4, 0.08)) for f in frames[-3:]], cw, fps)
    case("a shot with almost no face: kept as it was", none["mode"] == "keep")
    P = {"fps": 30.0, "layers": [{"type": "clip", "id": "a", "start": 0, "end": 10, "rect": [0, 0, 1080, 1920],
                                  "anchor": [{"start": 0, "values": [0.5, 0.52]}, 0.5]},
                                 {"type": "clip", "id": "b", "start": 0, "end": 10, "rect": [0, 0, 1080, 1920],
                                  "track": "face"},
                                 {"type": "clip", "id": "c", "start": 0, "end": 10, "rect": [0, 0, 1080, 1920],
                                  "anchor": [0.3, 0.5]},
                                 {"type": "clip", "id": "d", "start": 0, "end": 10, "rect": [0, 0, 1080, 1920]},
                                 {"type": "clip", "id": "e", "start": 0, "end": 10, "rect": [0, 0, 1080, 1920],
                                  "anchor": [0.3, 0.5], "panels": [{"rect": [0, 0, 1080, 960]}]}]}
    case("never changed: a shake's moves, a clip that follows the face itself, a point set by hand (unless asked), a "
         "layout set by hand; free: a clip with no point",
         [bool(_ours(L, False)) for L in P["layers"]] == [True, True, True, False, True]
         and not _ours(P["layers"][2], True) and _ours(P["layers"][4], True))
    case("the shot's frames map to the clip's own (jumps, speed, a held photo)",
         src_index({"start": 10, "in": 100}, 15) == 105 and src_index({"start": 0, "jumps": [[0, 50], [20, 300]],
                                                                       "speed": 2.0}, 25) == 310
         and src_index({"start": 0, "in": 7, "hold": True}, 40) == 7)
    case("a 16:9 clip in a 9:16 place: the crop is 31.6 % of its width; a vertical clip there is the same shape",
         abs(crop_share({"rect": [0, 0, 1080, 1920]}, 1920, 1080) - 0.3164) < 1e-3
         and crop_share({"rect": [0, 0, 1080, 1920]}, 1080, 1920) >= WIDER)

    # step 2 - the layouts (made-up faces; a 1920 x 1080 cache in a 1080 x 1920 video)
    class Fake:                                    # a source's faces and light frames, made up
        def __init__(self, faces, lum=None, rgb=None):
            self.w, self.h, self.faces, self.lum, self.img = 480, 270, faces, lum, rgb

        def luma(self, i):
            return self.lum(i) if self.lum else np.full((self.h, self.w), 128.0, np.float32)

        def rgb(self, i):
            return self.img if self.img is not None else \
                np.random.default_rng(int(i)).integers(0, 255, (self.h, self.w, 3), dtype=np.uint8)

    PL = {"width": 1080, "height": 1920, "fps": 30.0, "sources": {"A": {"width": 1920, "height": 1080}}}

    def run(faces_at, fake=None):
        L = {"type": "clip", "id": "s01_A", "src": "A", "start": 0, "end": 299, "rect": [0, 0, 1080, 1920]}
        F = fake or Fake(None)
        return layout(L, F, [(f, faces_at(f)) for f in frames], PL, fps)

    two_far = run(lambda f: [[0.25, 0.5, 0.10, 0.17, 0.9], [0.75, 0.52, 0.10, 0.17, 0.9]])
    pz = [p.get("zoom", 1) for p in two_far.get("panels", [])]
    shown = []
    if two_far.get("layout") == "split":
        for k, (c, z) in enumerate(((two_far["x"], pz[0]), (two_far["panels"][1]["anchor"][0], pz[1]))):
            half = 0.6328 / z / 2                  # a 1080 x 960 panel's crop: 63 % of the picture's width at zoom 1
            other = 0.75 if k == 0 else 0.25
            shown.append(c - half <= (0.25 if k == 0 else 0.75) <= c + half and abs(other - c) - 0.05 > half)
    case("two people far apart (faces at 25 % and 75 %): a split - the left one on top, each panel shows its own face "
         "and not the other's, the same zoom for the same face size",
         two_far.get("layout") == "split" and shown == [True, True] and abs(pz[0] - pz[1]) < 1e-6
         and two_far["panels"][0]["rect"] == [0, 0, 1080, 960] and two_far["panels"][1]["rect"] == [0, 960, 1080, 960])
    pair = run(lambda f: [[0.45, 0.5, 0.06, 0.1, 0.9], [0.56, 0.5, 0.06, 0.1, 0.9]])
    case("two people side by side (their faces 11 % apart): one crop on both (fill)",
         pair.get("layout") == "fill" and pair["mode"] == "hold" and abs(pair["x"] - 0.505) < 0.02)
    near_two = run(lambda f: [[0.42, 0.5, 0.12, 0.2, 0.9], [0.60, 0.5, 0.12, 0.2, 0.9]])
    zb = near_two.get("panels", [{}])[0].get("zoom", 1)
    case("two big faces 18 % apart: too far for one crop, too close for a split without blowing it up past "
         f"{UPSCALE_MAX}x - a fit, its band zoomed in on the two (x{zb:.2f}: their span with its margins fills it)",
         near_two.get("layout") == "fit" and near_two["panels"][0]["rect"][2] == 1080
         and abs(0.30 * zb / 0.75 - (1 - 2 * MARGIN)) < 0.01)
    three = run(lambda f: [[0.2, 0.5, 0.07, 0.12, 0.9], [0.5, 0.5, 0.07, 0.12, 0.9], [0.8, 0.5, 0.07, 0.12, 0.9]])
    case("three people across the picture: a fit (a 4:3 band, 810 px high in the middle) over a blurred copy",
         three.get("layout") == "fit" and three["panels"] == [{"rect": [0, 555, 1080, 810]}]
         and three["backdrop"] == "blur")
    dash = run(lambda f: [[0.1 + 0.8 * min(1.0, f / 30), 0.5, 0.07, 0.12, 0.9]])
    case("someone crossing the whole picture in a second: too fast to follow - a fit",
         dash.get("layout") == "fit")
    one = run(lambda f: [[0.4, 0.45, 0.1, 0.17, 0.9], [0.8, 0.3, 0.02, 0.03, 0.8]])
    case("one person and a small face behind (a poster): the person filled, the small face is no second person",
         one.get("layout") == "fill" and one["mode"] == "hold" and abs(one["x"] - 0.4) < 0.01)
    by = run(lambda f: [[0.5, 0.38, 0.14, 0.32, 0.92]] + ([[0.2 + f / 1500, 0.4, 0.08, 0.23, 0.8]] if f >= 120 else []))
    case("someone passing behind for part of the shot, a side view of 0.4 of the face's size (zz_many_clips2 s22_I): "
         "the person filled, no two-person layout", by.get("layout") == "fill" and abs(by["x"] - 0.5) < 0.01)
    wall = np.full((270, 480, 3), [200, 190, 180], np.uint8)
    wall[60:200, 180:300] = [90, 60, 50]           # a person in front of a plain wall
    case("a fit in front of a plain wall: the wall's colour behind it (not a blur); a busy room: a blur",
         plain_colour([wall, wall], 0.5, 0.75) == "#c8beb4"
         and plain_colour([Fake(None).rgb(1), Fake(None).rgb(2)], 0.5, 0.75) is None)
    # a screen recording: a light screen, a face camera boxed bottom right (a 2 px border), the face in it
    scr = np.full((270, 480), 235.0, np.float32)
    rng = np.random.default_rng(3)
    for y in range(20, 250, 14):                   # lines of "text"
        scr[y:y + 5, 30:int(30 + rng.integers(120, 300))] = 60
    scr[178:270, 316:480] = 70                      # the camera's picture (dark), its border 2 px, white
    scr[176:178, 314:480] = 255
    scr[176:270, 314:316] = 255
    cam_face = [0.83, 0.82, 0.07, 0.12]
    box = inset_box(scr, cam_face)
    case("a face camera boxed into a screen recording: its box found from its straight borders",
         box is not None and abs(box[0] - 316 / 480) < 0.01 and abs(box[1] - 178 / 270) < 0.01 and box[2] == 1.0
         and box[3] == 1.0)
    room = np.full((270, 480), 120.0, np.float32)
    room[:, 300] = 230                             # a door frame beside a small face, nothing across
    case("a small face beside a door frame (no box round it): no camera found",
         inset_box(room, [0.8, 0.5, 0.07, 0.12]) is None)
    cam_faces = lambda f: [[0.83, 0.82, 0.07, 0.12, 0.9]]                  # noqa: E731
    sc = run(cam_faces, Fake(None, lum=lambda i: scr))
    gm = run(cam_faces, Fake(None, lum=lambda i: np.where(np.isin(scr, (70, 255)), scr,
                                                          rng.uniform(0, 255, scr.shape).astype(np.float32))))
    z_cam = sc.get("panels", [{}, {}])[1].get("zoom", 0) if sc.get("layout") == "screen" else 0
    case("that recording: the screen on top (58 % of the apps' safe height), the face camera below down to their "
         "bottom band (y 1480; the backdrop under it), zoomed to fill its panel from inside its box; the same round a "
         "moving picture: a game - the face camera on top (30 %)",
         sc.get("layout") == "screen" and sc["panels"][0]["rect"] == [0, 0, 1080, 858]
         and sc["panels"][1]["rect"] == [0, 858, 1080, 622] and z_cam > 1 and sc.get("backdrop") == "blur"
         and gm.get("layout") == "game" and gm["panels"][0]["rect"] == [0, 0, 1080, 576])
    # step 4 - the limits
    zt = {"type": "clip", "start": 0, "end": 99, "zoom": {"keys": [[0, 1.0, "linear"], [95, 1.0, "in"], [99, 1.7]]}}
    case("the zoom a shot holds: a zoom-through into the cut (4 frames up to 1.7x) is not it; a punch-in held for the "
         "last half is", held_zoom(zt)[0] == 1.0 and held_zoom({**zt, "zoom": {"keys": [[0, 1.0, "hold"],
                                                                                       [50, 1.15, "hold"]]}})[0] == 1.15)
    PL720 = {**PL, "sources": {"A": {"width": 1280, "height": 720}}}
    L720 = {"type": "clip", "id": "s01_A", "src": "A", "start": 0, "end": 299, "rect": [0, 0, 1080, 1920]}
    soft = layout(L720, Fake(None), [(f, [[0.45, 0.45, 0.1, 0.17, 0.9]]) for f in frames], PL720, fps)
    case("a 720p clip: a fill would blow it up 2.7x - a fit (its band 1.1x)",
         soft.get("layout") == "fit" and "2.7x" in soft["words"])
    import cv2
    pic = np.full((270, 480), 110, np.uint8)
    pic[150:158, 20:460] = 40                      # a shelf's front: a long dark bar, no letters
    cv2.putText(pic, "HERE", (300, 95), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 235, 2, cv2.LINE_AA)   # a poster, mid-room
    sub = pic.copy()
    for col, th in ((0, 3), (255, 1)):             # a subtitle: white with a black edge, near the bottom
        cv2.putText(sub, "THEY NEVER SHOWED ME LOVE", (96, 236), cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, th, cv2.LINE_AA)
    found = text_lines(sub.astype(np.float32))
    case("text burned in: a subtitle line found (x 0.20-0.69, near the bottom); the poster's word in the room and a "
         "shelf's edge are not text", len(found) == 1 and abs(found[0][0] - 0.2) < 0.01 and abs(found[0][2] - 0.69) < 0.01
         and found[0][1] > 0.8 and text_lines(pic.astype(np.float32)) == [])
    talk_sub = layout({**L720, "src": "A"}, Fake(None, lum=lambda i: sub.astype(np.float32)),
                      [(f, [[0.45, 0.45, 0.1, 0.17, 0.9]]) for f in frames], PL, fps)
    kept = talk_sub.get("x", 0) if talk_sub.get("layout") == "fit" else 0
    sb = found[0] if found else [0, 0, 1, 1]
    case("a talking head with a subtitle the fill would cut: a fit, the crop moved so the line stays whole",
         talk_sub.get("layout") == "fit" and "kept whole" in talk_sub["words"]
         and kept - 0.375 <= sb[0] - TEXT_PAD + 1e-6 and sb[2] + TEXT_PAD <= kept + 0.375 + 1e-6)
    bare = layout({**L720, "anchor": [0.2, 0.5]}, Fake(None, lum=lambda i: sub.astype(np.float32)),
                  [(f, []) for f in frames], PL, fps)
    plain = layout({**L720, "anchor": [0.2, 0.5]}, Fake(None), [(f, []) for f in frames], PL, fps)
    case("no face, its own point (x 0.2) cutting a subtitle: a fit round the line; without the subtitle: kept",
         bare.get("layout") == "fit" and bare["x"] - 0.375 <= sb[0] - TEXT_PAD + 1e-6
         and plain.get("layout") == "keep")
    zb2 = two_far["panels"][1]["zoom"]              # the split's bottom face: its mouth above the apps' bottom band
    mouth = face_box(0.52, 0.17, 1 / zb2, two_far["panels"][1]["anchor"][1], 960, 960)[1]   # (a panel's crop: the
    #                                                                                          picture's height / zoom)
    low = run(lambda f: [[0.25, 0.72, 0.10, 0.22, 0.9], [0.75, 0.72, 0.10, 0.22, 0.9]])   # faces low in the picture
    lz = [p.get("zoom", 1) for p in low.get("panels", [{}, {}])]
    lm = face_box(0.72, 0.22, 1 / lz[1], low["panels"][1]["anchor"][1], 960, 960)[1] if low.get("layout") == "split" \
        else 9999
    base = SPLIT_FACE * 0.6328 / 0.10
    case(f"a split's bottom face: its mouth above the apps' bottom band (y {mouth:.0f}; the band from 1480); two faces "
         f"low in the picture: both panels zoomed in a little alike (x{lz[1] / base:.2f}, at most x{SAFE_ZOOM}) to "
         f"lift the bottom one (y {lm:.0f})",
         mouth <= 1480 - SAFE_PAD + 1 and lm <= 1480 - SAFE_PAD + 1 and 1 < lz[1] / base <= SAFE_ZOOM + 1e-6
         and abs(lz[0] - lz[1]) < 1e-6)
    a = {"anchor": [{"keys": [[0, 0.2, "smooth"], [40, 0.6, "linear"]]}, 0.55], "panels": [{"rect": [0, 0, 1, 1]}],
         "backdrop": "blur", "reframe": {"mode": "follow", "layout": "fit", "v": VERSION, "ax0": 0.31, "ay0": 0.42}}
    b = {"anchor": [0.4, 0.5], "reframe": {"mode": "hold", "layout": "fill", "v": VERSION, "ax0": 0.5, "ay0": 0.5,
                                           "bare": True}}
    _undo(a)
    _undo(b)
    case("a framing undone before the next run: the clip's own point back, its layout gone (a clip that had no point: "
         "none again)", a == {"anchor": [0.31, 0.42]} and b == {})
    # step 5 - the user's framing
    one_f = [(f, [[0.45, 0.45, 0.1, 0.17, 0.9]]) for f in frames]
    asked = {}
    for want in ("fit", "fill", "split", "screen"):
        try:
            asked[want] = layout(L720, Fake(None), one_f, PL720, fps, want=want)["layout"]
        except FrameError as x:
            asked[want] = f"refused: {x}"
    case(f"a layout the user asks for: a fit / a fill (even a 720p one the rules would put in a band) as asked; a "
         f"split of one person and a screen layout with no face camera refused with why ({asked})",
         asked["fit"] == "fit" and asked["fill"] == "fill" and asked["split"].startswith("refused")
         and asked["screen"].startswith("refused"))
    DP = {"fps": 30.0, "layers": [{"type": "clip", "id": "s01_A", "src": "A", "start": 0, "end": 99,
                                   "rect": [0, 0, 1080, 1920], "anchor": [0.4, 0.42]}]}
    line = frame_shot(DP, "s01_A", x=0.31)
    dl = DP["layers"][0]
    case("the crop dragged in the Editor: that point, still, marked the user's - automatic runs leave it; its own point "
         "kept for Auto", dl["anchor"] == [0.31, 0.42] and dl["reframe"]["by"] == "user"
         and dl["reframe"]["ax0"] == 0.4 and _ours(dl, True) == "framed by the user" and "0.310" in line)
    try:
        frame_shot({"fps": 30.0, "layers": [{"type": "clip", "id": "s02", "start": 0, "end": 9,
                                              "anchor": [{"start": 0, "values": [0.5, 0.52]}, 0.5]}]}, "s02", "fit")
        shook = ""
    except FrameError as x:
        shook = str(x)
    case("a shot that shakes: its framing refused (remove the shake first), the shake kept", "shake" in shook)
    from . import editlist as EL
    ops = EL.parse("frame 4 split\nframe s04_A fit hold\nframe 3 follow\nframe 2 auto")
    try:
        EL.parse("frame 4")
        lone = False
    except EL.ListError:
        lone = True
    case("an edit list's frame lines: a layout, a layout + hold, a mode alone, auto; a bare 'frame 4' is not a line",
         [(o["shot"], o["layout"], o["mode"]) for o in ops] == [("4", "split", None), ("s04_A", "fit", "hold"),
                                                                 ("3", None, "follow"), ("2", "auto", None)] and lone)
    case("summary counts the layouts",
         summary(["a: fill - hold at x 0.4", "b: fill - follow - 1 pan(s) at f3", "c: split - x", "d: kept - no face"])
         == "2 fill (1 held, 1 followed), 1 split, 1 kept")
    return {"passed": ok, "seconds": round(time.time() - t0, 3), "lines": lines}
