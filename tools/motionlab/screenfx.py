"""Effects on the whole picture drawn so far (0.6.1; the user, 2026-10-28: "build the rest of the effects from the
vibhas set"): a plan layer {"type": "fx", "kind": ..., "start", "end", "amount": curve} that compose.py draws in its
place in the layer list - what is under it changes, what comes after it (the graphics) is drawn on top. After the
designs in Vibha Ramprakash's claude-video-effects (MIT): the numbers below are hers unless a comment says otherwise.

    frame   the picture so far shrinks into a rectangle "to" [x, y, w, h] (shares of the frame), rounded "r" (a share of
            the shorter side), cropped round "focus" ("face" | "centre"); amount 0 = the full frame, 1 = in the
            rectangle; outside it a blurred, darker copy (a reel card, a grid tile, half the screen)
    grade   a colour look ("look": moody | bw | warm | cool | pop | red_film | editorial | lavender); amount = the mix
            (red_film: the room red, the person warm - it needs the person)
    glitch  slices shifted, an RGB split, the picture breaking into blocks past 0.82; amount = how broken
    tunnel  the room tunnels into itself, spinning ("ratio", "speed", "spin"), the person stays in front; amount = how
            far it is on
    dots    the picture built out of glowing dots ("color", "cell"), then the real picture; amount = progress 0 -> 1
    swipe   a before / after slider: "look" right of a line at "pos" (a curve, shares of the width), a handle and
            two labels ("labels"); amount = how far it is on
    push    the camera pushed "zoom" (a curve) into the point "px", "py" (curves, shares) - a corner push

Pure numpy / OpenCV on float RGB frames (0..1); the labels drawn once with Pillow. compose.FxLayer calls these and
moves the person mask and the face with the picture (frame, push), so the graphics drawn after it stay right.
"""
from __future__ import annotations

import math

import cv2
import numpy as np

LUMA = np.array([0.299, 0.587, 0.114], np.float32)
LOOKS = ("moody", "bw", "warm", "cool", "pop", "red_film", "editorial", "lavender")
KINDS = ("frame", "grade", "glitch", "tunnel", "dots", "swipe", "push")
_CACHE: dict = {}


def needs_person(spec: dict) -> bool:
    """A fx layer that reads the person (the tunnel keeps them in front, red film greys the room only, a frame keeps the
    face in) - person.wanted makes the tracks for the clips under it."""
    k = spec.get("kind")
    return k == "tunnel" or (k == "grade" and spec.get("look") == "red_film") or \
        (k == "frame" and spec.get("focus", "face") == "face")


# ------------------------------------------------------------------------------------------------ colour looks
def grade(img: np.ndarray, look: str, m: np.ndarray | None = None) -> np.ndarray:
    """img (h, w, 3) float -> the look; m = the person (0..1, (h, w)) for red_film (else the whole frame is red)."""
    img = np.clip(img, 0, 1)
    lum = (img @ LUMA)[..., None]
    if look == "bw":
        return np.repeat(np.clip((lum - 0.5) * 1.25 + 0.5, 0, 1), 3, axis=2)
    if look == "warm":
        return np.clip(img * np.float32([1.08, 1.0, 0.86]) + 0.02, 0, 1)
    if look == "cool":
        return np.clip(img * np.float32([0.9, 1.0, 1.1]), 0, 1)
    if look == "pop":
        o = lum + (img - lum) * 1.35
        return np.clip((o - 0.5) * 1.12 + 0.5, 0, 1)
    if look == "red_film":                       # the room a red monochrome, the person a little warm, a vignette
        bg = np.clip(lum * np.float32([1.05, 0.3, 0.27]) * 0.85, 0, 1)
        you = np.clip(img * np.float32([1.04, 0.86, 0.82]), 0, 1)
        mm = m[..., None] if m is not None else np.zeros_like(lum)
        return (you * mm + bg * (1 - mm)) * (1 - 0.5 * vignette(img.shape[1], img.shape[0]))[..., None]
    if look == "editorial":                      # a soft warm film: lifted, creamy, a bloom on the highlights
        soft = (img * 0.82 + lum * 0.18) * 0.9 + np.float32([252, 238, 228]) / 255 * 0.1
        h, w = img.shape[:2]
        bl = cv2.resize(np.clip(img[::4, ::4] - 0.62, 0, 1), (w, h), interpolation=cv2.INTER_LINEAR)
        return np.clip(soft + cv2.GaussianBlur(bl, (0, 0), w * 0.012) * 0.55, 0, 1)
    if look == "lavender":                       # ours: everything washed toward a soft lilac (her pastel room)
        return np.clip(lum * np.float32([0.93, 0.86, 1.08]) * 0.55 + np.float32([0.80, 0.74, 0.96]) * 0.45, 0, 1)
    # moody: a little darker, softer colour, teal shadows, warm highlights, gentle contrast
    o = lum + (img - lum) * 0.6
    o = np.power(np.clip(o, 0, 1), 1.3) * 0.88
    o = o + (1 - lum) * np.float32([-0.03, 0.035, 0.065]) + lum * np.float32([0.05, 0.015, -0.04])
    o = np.clip((o - 0.42) * 1.12 + 0.42, 0, 1)
    return o * (1 - 0.4 * vignette(img.shape[1], img.shape[0]))[..., None]


def vignette(W: int, H: int) -> np.ndarray:
    """0 in the middle -> 1 in the corners (her vignette's shape)."""
    if ("vig", W, H) not in _CACHE:
        yy, xx = np.ogrid[0:H, 0:W]
        d = ((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2
        _CACHE[("vig", W, H)] = np.clip(d, 0, 1).astype(np.float32)
    return _CACHE[("vig", W, H)]


def paper(W: int, H: int, color, pattern: str | None) -> np.ndarray:
    """A room painted one colour, or grid paper (her check-pills room: a line every 1/20 of the width)."""
    key = ("paper", W, H, tuple(round(float(c), 4) for c in color), pattern)
    if key not in _CACHE:
        g = np.ones((H, W, 3), np.float32) * np.asarray(color, np.float32)
        if pattern == "grid":
            st, lw = max(20, W // 20), max(1, W // 700)
            line = np.asarray(color, np.float32) * np.float32([0.92, 0.926, 0.937])
            for x in range(0, W, st):
                g[:, x:x + lw] = line
            for y in range(0, H, st):
                g[y:y + lw] = line
        _CACHE[key] = g
    return _CACHE[key]


# ------------------------------------------------------------------------------------------------ geometry
def rounded(W: int, H: int, x: float, y: float, w: float, h: float, r: float) -> np.ndarray:
    """A rounded rectangle's coverage over the frame (anti-aliased, float rect)."""
    out = np.zeros((H, W), np.float32)
    xa, xb = max(0, int(math.floor(x))), min(W, int(math.ceil(x + w)))
    ya, yb = max(0, int(math.floor(y))), min(H, int(math.ceil(y + h)))
    if xb <= xa or yb <= ya:
        return out
    r = max(0.0, min(r, w / 2, h / 2))
    yy, xx = np.ogrid[ya:yb, xa:xb]
    cx, cy = x + w / 2, y + h / 2
    qx = np.abs(xx + 0.5 - cx) - (w / 2 - r)                  # the signed distance to the rounded edge (< 0 inside)
    qy = np.abs(yy + 0.5 - cy) - (h / 2 - r)
    dx, dy = np.maximum(qx, 0), np.maximum(qy, 0)
    d = np.sqrt(dx * dx + dy * dy) + np.minimum(np.maximum(qx, qy), 0) - r
    # (the straight edges: coverage of the pixel by the rect, so a float edge moves smoothly)
    ex = np.clip(np.minimum(xx + 1.0, x + w) - np.maximum(xx, x), 0, 1)
    ey = np.clip(np.minimum(yy + 1.0, y + h) - np.maximum(yy, y), 0, 1)
    out[ya:yb, xa:xb] = np.minimum(np.clip(0.5 - d, 0, 1), ex * ey)
    return out


def warp(img: np.ndarray, M: np.ndarray, W: int, H: int, s: float, border=cv2.BORDER_REPLICATE) -> np.ndarray:
    """img through the affine M (scale s) onto a W x H frame: shrunk past 0.7 through an area resize first (no
    shimmer on fine detail), grown with a cubic."""
    if s < 0.7:
        p = min(1.0, s * 1.5)
        h0, w0 = img.shape[:2]
        small = cv2.resize(img, (max(1, round(w0 * p)), max(1, round(h0 * p))), interpolation=cv2.INTER_AREA)
        M = M.copy()
        M[:, :2] /= p
        img = small
    flags = cv2.INTER_CUBIC if s > 1.0 else cv2.INTER_LINEAR
    return cv2.warpAffine(img, M, (W, H), flags=flags, borderMode=border)


def frame_geo(W: int, H: int, to, focus, a: float):
    """Where frame() puts the picture at a: the rect (x, y, w, h), its scale s and the crop's corner (cx0, cy0) - a
    point P of the frame lands at (x + (P - cx0) * s)."""
    x = to[0] * a
    y = to[1] * a
    w = W + (to[2] - W) * a
    h = H + (to[3] - H) * a
    s = max(w / W, h / H)                                  # cover the rect, cropped round the focus
    cw, ch = w / s, h / s
    cx0 = min(max(focus[0] - cw / 2, 0.0), W - cw)
    cy0 = min(max(focus[1] - ch / 2, 0.0), H - ch)
    return x, y, w, h, s, cx0, cy0


def push_geo(W: int, H: int, z: float, px: float, py: float):
    """push()'s window: (z, x0, y0) - a point P lands at ((P - x0) * z)."""
    z = min(max(z, 1.0), 2.0)
    cw, ch = W / z, H / z
    return z, min(max(px - cw / 2, 0.0), W - cw), min(max(py - ch / 2, 0.0), H - ch)


def frame(canvas, matte, face, to, r, focus, a):
    """The picture shrunk into `to` (pixels x, y, w, h) by a (0..1): -> (canvas, matte, face) moved alike."""
    H, W = canvas.shape[:2]
    x, y, w, h, s, cx0, cy0 = frame_geo(W, H, to, focus, a)
    M = np.float32([[s, 0, x - cx0 * s], [0, s, y - cy0 * s]])
    inner = warp(canvas, M, W, H, s)
    small = cv2.resize(canvas, (max(1, W // 16), max(1, H // 16)), interpolation=cv2.INTER_AREA)
    bg = cv2.GaussianBlur(cv2.resize(small, (W, H), interpolation=cv2.INTER_LINEAR), (0, 0), 12) * (1 - 0.45 * a)
    al = rounded(W, H, x, y, w, h, r * a)[..., None]
    out = bg * (1 - al) + inner * al
    if matte is not None:
        matte = warp(matte, M, W, H, s, cv2.BORDER_CONSTANT) * al[..., 0]
    if face is not None:
        face = (x + (face[0] - cx0) * s, y + (face[1] - cy0) * s, face[2] * s)
    return out, matte, face


def push(canvas, matte, face, z, px, py):
    """Her camera(): the frame zoomed z (1..2) toward the point (px, py) in pixels, the window kept inside the frame."""
    H, W = canvas.shape[:2]
    z, x0, y0 = push_geo(W, H, z, px, py)
    if z <= 1.002:
        return canvas, matte, face
    M = np.float32([[z, 0, -x0 * z], [0, z, -y0 * z]])
    out = cv2.warpAffine(canvas, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    if matte is not None:
        matte = cv2.warpAffine(matte, M, (W, H), flags=cv2.INTER_LINEAR)
    if face is not None:
        face = ((face[0] - x0) * z, (face[1] - y0) * z, face[2] * z)
    return out, matte, face


# ------------------------------------------------------------------------------------------------ the others
def glitch(canvas: np.ndarray, g: float, rng: np.random.Generator) -> np.ndarray:
    """Her uninstall break: an RGB split, slices shifted sideways, past 0.82 the picture breaks into blocks and dims."""
    H, W = canvas.shape[:2]
    g = min(max(g, 0.0), 1.0)
    out = canvas.copy()
    sh = int(g * W * 0.025)
    if sh:
        out = np.stack([np.roll(out[..., 0], sh, 1), out[..., 1], np.roll(out[..., 2], -sh, 1)], -1)
    k = H / 1920
    for _ in range(int(2 + g * 10)):
        y0 = int(rng.uniform(0, H))
        hh = int(rng.uniform(8, 60) * k) + 1
        off = int(rng.uniform(-1, 1) * g * W * 0.08)
        out[y0:y0 + hh] = np.roll(out[y0:y0 + hh], off, 1)
    if g > 0.82:
        q = (g - 0.82) / 0.18
        f = 1 + int(q * 40)
        small = cv2.resize(out, (max(1, W // f), max(1, H // f)), interpolation=cv2.INTER_AREA)
        out = cv2.resize(small, (W, H), interpolation=cv2.INTER_NEAREST) * (1 - 0.6 * q)
    return out


def tunnel(canvas, matte, centre, k, t, ratio=0.62, speed=0.8, spin=10.0):
    """Her rabbit hole: the frame inside itself, level after level (each `ratio` smaller, turned `spin` degrees more),
    flowing inward with time t (seconds); a thin white edge on each level; the person in front (matte)."""
    H, W = canvas.shape[:2]
    if k <= 0:
        return canvas
    if ("tun", W, H) not in _CACHE:
        b = np.zeros((H, W), np.float32)
        th = max(4, W // 120)
        b[:th] = b[-th:] = 1
        b[:, :th] = b[:, -th:] = 1
        _CACHE[("tun", W, H)] = (np.ones((H, W), np.float32), b)
    ones, border = _CACHE[("tun", W, H)]
    z = (t * speed) % 1.0
    out = canvas.copy()
    for lev in range(1, 7):
        s = ratio ** (lev - z * k)
        if s < 0.03:
            break
        M = cv2.getRotationMatrix2D((float(centre[0]), float(centre[1])), (lev - z) * spin * k, s)
        L = cv2.warpAffine(canvas, M, (W, H), flags=cv2.INTER_LINEAR)
        a = cv2.warpAffine(ones, M, (W, H))[..., None] * k
        bd = cv2.warpAffine(border, M, (W, H))[..., None] * k
        out = out * (1 - a) + L * a
        out = out * (1 - bd) + bd
    if matte is not None:                       # you stay in front while the room tunnels behind you
        m = matte[..., None] * k
        out = out * (1 - m) + canvas * m
    return out


def dots(canvas, p, t, color=(1.0, 0.5, 0.31), cell_share=0.017, bg=(0.078, 0.078, 0.086)):
    """Her dot reveal at progress p (0..1): glowing dots light up at random, take the picture's colours, then the
    real picture comes through (from 0.6)."""
    H, W = canvas.shape[:2]
    cell = max(6, int(W * cell_share))
    gh, gw = H // cell + 1, W // cell + 1
    key = ("dots", W, H, cell)
    if key not in _CACHE:
        yy, xx = np.mgrid[0:gh * cell, 0:gw * cell].astype(np.float32)
        dist = np.sqrt((xx % cell - cell / 2 + 0.5) ** 2 + (yy % cell - cell / 2 + 0.5) ** 2)[:H, :W]
        _CACHE[key] = (dist, np.random.default_rng(5).random((gh, gw)).astype(np.float32))
    dist, thr = _CACHE[key]
    pad = np.pad(np.clip(canvas, 0, 1), ((0, gh * cell - H), (0, gw * cell - W), (0, 0)), mode="edge")
    small = cv2.resize(pad, (gw, gh), interpolation=cv2.INTER_AREA)
    lum = small @ LUMA
    on = np.clip((p * 1.7 - thr * 0.95) / 0.3, 0, 1)
    sparkle = 0.75 + 0.25 * np.sin(thr * 40 + t * 18)
    r = (0.18 + 0.32 * np.sqrt(np.clip(lum, 0, 1))) * cell * on
    q2 = min(max((p - 0.3) / 0.35, 0.0), 1.0)
    dc = (np.asarray(color, np.float32) * (0.55 + 0.6 * lum[..., None]) * sparkle[..., None] * (1 - q2)
          + np.clip(small * 1.15, 0, 1) * q2)
    R = np.repeat(np.repeat(r, cell, 0), cell, 1)[:H, :W]
    DC = np.repeat(np.repeat(dc, cell, 0), cell, 1)[:H, :W]
    dm = np.clip(R - dist + 0.5, 0, 1)[..., None]
    out = np.asarray(bg, np.float32) * (1 - dm) + DC * dm
    q = min(max((p - 0.6) / 0.4, 0.0), 1.0)
    q = q * q * (3 - 2 * q)
    return out * (1 - q) + canvas * q


def _label(text: str, px: int):
    """A white pill with the word in dark (RGBA float, premultiplied off) - Pillow, drawn once."""
    key = ("label", text, px)
    if key not in _CACHE:
        from PIL import Image, ImageDraw, ImageFont
        from .util import LAB
        try:
            f = ImageFont.truetype(str(LAB / "fonts" / "Inter.ttf"), px)
        except OSError:
            try:
                f = ImageFont.truetype("arial.ttf", px)
            except OSError:
                f = ImageFont.load_default()
        tw = int(f.getlength(text))
        h = int(px * 1.5)
        im = Image.new("RGBA", (tw + h, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, tw + h - 1, h - 1], h // 2, fill=(255, 255, 255, 228))
        d.text((h // 2, h // 2), text, font=f, fill=(20, 18, 15, 255), anchor="lm")
        _CACHE[key] = np.asarray(im, np.float32) / 255.0
    return _CACHE[key]


def _paste(out, rgba, cx, cy, op=1.0):
    H, W = out.shape[:2]
    h, w = rgba.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xb <= xa or yb <= ya:
        return
    a = rgba[ya - y0:yb - y0, xa - x0:xb - x0, 3:4] * op
    out[ya:yb, xa:xb] = out[ya:yb, xa:xb] * (1 - a) + rgba[ya - y0:yb - y0, xa - x0:xb - x0, :3] * a


def swipe(canvas, pos, k, look="moody", labels=("Before", "After"), m=None):
    """Her before / after slider: the look right of a slanted line at pos (share of the width), a white edge, a round
    handle with two arrows at 62 % of the height, a label pill under each side; k = how far it is on (0..1)."""
    H, W = canvas.shape[:2]
    if k <= 0:
        return canvas
    after = grade(canvas, look, m)
    yy, xx = np.ogrid[0:H, 0:W]
    line = pos * W + 0.22 * (yy - H / 2)
    a = (np.clip((xx - line) / 3 + 0.5, 0, 1) * k)[..., None]
    out = canvas * (1 - a) + after * a
    edge = (np.clip(1 - np.abs(xx - line) / 3.5, 0, 1) * k)[..., None]
    out = out * (1 - edge) + edge
    hy = H * 0.62
    hx = pos * W + 0.22 * (hy - H / 2)
    rr = W * 0.035
    ya, yb, xa, xb = max(0, int(hy - rr * 1.6)), min(H, int(hy + rr * 1.6)), max(0, int(hx - rr * 1.6)), min(W, int(hx + rr * 1.6))
    if yb > ya and xb > xa:
        gy, gx = np.ogrid[ya:yb, xa:xb]
        d = np.sqrt((gx + 0.5 - hx) ** 2 + (gy + 0.5 - hy) ** 2)
        sh = np.clip(1 - (d - rr * 0.9) / (rr * 0.5), 0, 1) * 0.35 * k              # a soft shadow round it
        disc = np.clip(rr - d + 0.5, 0, 1) * k
        reg = out[ya:yb, xa:xb]
        reg *= (1 - sh)[..., None]
        reg[:] = reg * (1 - disc[..., None]) + disc[..., None]
        for sgn in (-1, 1):                                                       # two arrows: < >
            u = (gx + 0.5 - (hx + sgn * rr * 0.18)) * sgn                         # 0 at the base -> 0.4 rr at the tip
            tri = np.clip((rr * 0.4 - u) * 0.6 - np.abs(gy + 0.5 - hy) + 0.5, 0, 1) * (u >= 0) * (u <= rr * 0.4) * k
            reg[:] = reg * (1 - tri[..., None]) + np.float32([0.08, 0.07, 0.06]) * tri[..., None]
    px = max(12, int(W * 0.03))
    for text, x in zip(labels, (0.14, 0.86)):
        if text:
            _paste(out, _label(str(text), px), W * x, H * 0.88, k)
    return out


def selfcheck() -> list[str]:
    """Each kind on a made-up frame: shapes, the right things move."""
    out = []
    H, W = 192, 108
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    img = np.dstack([xx / W, yy / H, np.full((H, W), 0.5, np.float32)]).astype(np.float32)
    for look in LOOKS:
        g = grade(img, look, np.zeros((H, W), np.float32))
        assert g.shape == img.shape and 0 <= g.min() and g.max() <= 1, look
    bw = grade(img, "bw")
    assert np.abs(bw[..., 0] - bw[..., 2]).max() < 1e-6, "bw has colour"
    out.append(f"grade: {len(LOOKS)} looks in range, bw grey")
    m = np.zeros((H, W), np.float32)
    m[40:80, 40:70] = 1
    to = (0.0, H * 0.5, float(W), H * 0.5)
    f1, m1, fc = frame(img, m, (55.0, 60.0, 20.0), to, 0.0, (55.0, 60.0), 1.0)
    assert abs(fc[1] - 144.0) < 1e-3, fc            # the crop round the face (y 12..108) lands at y 96: face 60 -> 144
    assert m1[:int(H * 0.5) - 1].max() < 1e-3 and m1.max() > 0.9, "the mask moved with the picture"
    f0, _, _ = frame(img, None, None, to, 0.0, (55.0, 60.0), 0.0)
    assert np.abs(f0 - img).max() < 0.02, "amount 0 = the frame as it was"
    out.append(f"frame: amount 0 = unchanged; 1 = in the bottom half, the face at y {fc[1]:.1f}, the mask with it")
    p2, _, fc2 = push(img, None, (54.0, 96.0, 10.0), 2.0, 0.0, 0.0)
    assert fc2[:2] == (108.0, 192.0) and abs(p2[0, 0, 0] - img[0, 0, 0]) < 0.02, fc2
    out.append("push: 2x into the top-left corner keeps the corner, doubles the rest")
    rng = np.random.default_rng(1)
    g0, g1 = glitch(img, 0.0, rng), glitch(img, 1.0, rng)
    assert np.abs(g1 - img).mean() > np.abs(g0 - img).mean() + 0.02, "glitch"
    t0 = tunnel(img, m, (54.0, 96.0), 1.0, 0.3)
    assert np.abs(t0[m > 0.5] - img[m > 0.5]).max() < 1e-5 and np.abs(t0 - img).mean() > 0.01, "tunnel"
    out.append("glitch grows with its amount; tunnel changes the room, leaves the person")
    d0, d1 = dots(img, 0.05, 0.0), dots(img, 1.0, 0.0)
    assert np.abs(d1 - img).max() < 1e-5 and d0.mean() < img.mean(), "dots"
    s1 = swipe(img, 0.5, 1.0, "bw", ("", ""))
    left, right = s1[96, 10], s1[96, 100]
    assert abs(left[0] - left[2]) > 0.05 and abs(right[0] - right[2]) < 1e-3, (left, right)
    out.append("dots end on the picture; swipe: the look right of the line only")
    return out


if __name__ == "__main__":
    for line in selfcheck():
        print("PASS", line)
