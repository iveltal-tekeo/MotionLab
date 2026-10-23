"""How close a rebuilt template moves to the clip it was learned from (2026-10-18). The content is a placeholder,
so this compares MOTION, not pixels:

- motion energy per frame = the mean absolute difference of a small grey copy of each frame and the one before
  (0-255), for the reference clip and the template's render; a brief flash at the start of the reference (a few
  frames much brighter / darker than what follows, then gone) is left out (the user's rule);
- both curves on one time axis (each clip's own length, 0..1) at 200 points, smoothed over ~3 frames, each scaled
  to its own peak; correlation = Pearson's r, the best within +-4 % of the length (a small offset in when things
  happen is not a different motion);
- duration: the render's length against the reference's (within 10 % = full marks).

score = 0.7 * max(0, r) + 0.3 * duration score (1 within 10 %, falling to 0 at 50 % off). 0.6 or more = "ok".
match() writes <out>\\match.json and <out>\\compare.png (reference above, render below at the same moments, frame +
timecode on every tile, both curves under them).
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .timecode import frame_to_tc

OK = 0.6
N = 200


def energy(video: Path, max_frames: int = 3000) -> tuple[np.ndarray, float, list[np.ndarray]]:
    """-> (energy per frame, fps, small RGB frames for the strip)."""
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    e, prev, small, lum = [], None, [], []
    while len(e) < max_frames:
        ok, fr = cap.read()
        if not ok:
            break
        h, w = fr.shape[:2]
        g = cv2.cvtColor(cv2.resize(fr, (160, max(1, int(160 * h / w)))), cv2.COLOR_BGR2GRAY).astype(np.float32)
        e.append(0.0 if prev is None else float(np.mean(np.abs(g - prev))))
        lum.append(float(g.mean()))
        prev = g
        small.append(cv2.cvtColor(cv2.resize(fr, (320, max(1, int(320 * h / w)))), cv2.COLOR_BGR2RGB))
    cap.release()
    e = np.array(e, dtype=np.float64)
    # a brief flash at the start: within the first ~0.5 s, frames whose brightness is far from the frame after the
    # flash (> 40 levels) - their energy (and that of the frame after) does not count
    k = int(round(fps * 0.5))
    if len(lum) > k + 2:
        ref = lum[k + 1]
        fl = [i for i in range(min(k, len(lum))) if abs(lum[i] - ref) > 40]
        if fl and fl[-1] < k:
            e[: fl[-1] + 2] = 0.0
    # the capture cut short: the last 1-3 frames jump to an empty frame (black / white, a preview ending) - dropped
    sd = [float(cv2.cvtColor(cv2.resize(cv2.cvtColor(s, cv2.COLOR_RGB2BGR), (80, 45)), cv2.COLOR_BGR2GRAY).std())
          for s in small[-4:]] if len(small) > 8 else []
    for j in range(1, min(4, len(sd))):
        if sd[-j] < 2.0 and sd[-j - 1] >= 2.0 and e[-j] > 3 * (np.median(e) + 1e-6):
            e, small = e[:-j], small[:-j]
            break
    return e, float(fps), small


def _curve(e: np.ndarray) -> np.ndarray:
    if len(e) < 2:
        return np.zeros(N)
    x = np.linspace(0, 1, len(e))
    c = np.interp(np.linspace(0, 1, N), x, e)
    c = np.convolve(c, np.ones(3) / 3, mode="same")
    m = c.max()
    return c / m if m > 1e-9 else c


def score(ref: Path, render: Path) -> dict:
    er, fr, _ = energy(ref)
    eo, fo, _ = energy(render)
    a, b = _curve(er), _curve(eo)
    best, lag = -1.0, 0
    w = max(1, int(N * 0.04))
    for s in range(-w, w + 1):
        x, y = (a[s:], b[: N - s]) if s >= 0 else (a[: N + s], b[-s:])
        if x.std() < 1e-9 or y.std() < 1e-9:
            continue
        r = float(np.corrcoef(x, y)[0, 1])
        if r > best:
            best, lag = r, s
    dr, do = len(er) / fr, len(eo) / fo
    off = abs(do - dr) / dr if dr else 1.0
    ds = 1.0 if off <= 0.10 else max(0.0, 1.0 - (off - 0.10) / 0.40)
    sc = round(0.7 * max(0.0, best) + 0.3 * ds, 3)
    return {"score": sc, "status": "ok" if sc >= OK else "needs-work", "correlation": round(best, 3),
            "lag_share": round(lag / N, 3), "duration_ref_s": round(dr, 3), "duration_render_s": round(do, 3),
            "duration_off": round(off, 3), "duration_ok": off <= 0.10, "frames_ref": len(er), "fps_ref": fr,
            "frames_render": len(eo), "fps_render": fo, "curve_ref": [round(v, 3) for v in a[::4]],
            "curve_render": [round(v, 3) for v in b[::4]]}


def strip(ref: Path, render: Path, out: Path, cols: int = 8, title: str = "") -> Path:
    er, fr, sr = energy(ref)
    eo, fo, so = energy(render)
    # tiles where the reference moves: the first and last frame + the quantiles of its accumulated motion energy
    cum = np.cumsum(er)
    ts = [0.0, 1.0]
    if len(er) > 2 and cum[-1] > 0:
        ts += [float(np.searchsorted(cum, cum[-1] * (i + 0.5) / (cols - 2)) / (len(er) - 1)) for i in range(cols - 2)]
    ts = sorted(set(round(t, 4) for t in ts))
    while len(ts) < cols:                                   # a clip with little motion: fill evenly
        ts = sorted(set(ts) | {round(len(ts) / cols, 4)})
    tw = 240
    th_r = int(tw * sr[0].shape[0] / sr[0].shape[1]) if sr else 135
    th_o = int(tw * so[0].shape[0] / so[0].shape[1]) if so else 135
    lab, H_curve = 18, 110
    W = cols * tw
    img = Image.new("RGB", (W, 26 + 2 * lab + th_r + th_o + H_curve + 12), (22, 22, 22))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 12)
    except OSError:
        font = ImageFont.load_default()
    d.text((6, 6), title or f"reference (top) vs MotionLab render (bottom) - the same moment of each clip's length",
           fill=(230, 230, 230), font=font)
    y0 = 26
    for i, t in enumerate(ts):
        x = i * tw
        for row, (frames, fps, th, yy, col) in enumerate(((sr, fr, th_r, y0, (255, 214, 90)),
                                                          (so, fo, th_o, y0 + lab + th_r, (120, 210, 255)))):
            if not frames:
                continue
            f = min(len(frames) - 1, int(round(t * (len(frames) - 1))))
            im = Image.fromarray(frames[f]).resize((tw - 2, th))
            img.paste(im, (x + 1, yy + lab))
            d.text((x + 4, yy + 3), f"{'ref' if row == 0 else 'new'} f{f} ({frame_to_tc(f, fps)})", fill=col, font=font)
    cy = y0 + 2 * lab + th_r + th_o + 6
    for e, col in ((_curve(er), (255, 214, 90)), (_curve(eo), (120, 210, 255))):
        pts = [(int(i * (W - 1) / (N - 1)), int(cy + H_curve - 8 - (H_curve - 20) * v)) for i, v in enumerate(e)]
        d.line(pts, fill=col, width=2)
    d.text((6, cy), "motion energy (each scaled to its peak): yellow = reference, blue = render", fill=(200, 200, 200),
           font=font)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


def match(ref: Path, render: Path, out_dir: Path, title: str = "") -> dict:
    r = score(ref, render)
    strip(ref, render, out_dir / "compare.png", title=title)
    r["compare"] = str(out_dir / "compare.png")
    (out_dir / "match.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    return r
