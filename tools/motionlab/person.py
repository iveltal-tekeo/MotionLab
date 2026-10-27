"""The person in a clip (0.6.1, 2026-10-27 - the user: graphics with "talking heads or people is where it gets kinda
AI-ish"): per frame of a source's LIGHT cache (footage.py), the person's mask and the face, so the compositor can put
a graphic BEHIND the person, keep it off the face, or pin it to the face (compose.py: a layer's "behind", "guard",
"follow"). Made once per clip, beside its caches, only for plans that use those keys (ensure(), before a render):

    <ID>.person.u8    the masks: frame = (light height, light width) uint8, 255 = the person
    <ID>.person.json  frames, size, fps, the light cache it was made from, the face track: [cx, cy, w] per frame as
                      shares of the frame (smoothed both ways - no lag), null where no face was ever found

The mask: Google MediaPipe's Selfie Segmenter (tools\\models\\selfie_segmenter.tflite, Apache-2.0) read by OpenCV's
own TFLite reader - no MediaPipe install (it pulls jax and a second OpenCV) - then a guided filter on the frame's
grey (edges follow hair), a contrast step and a 0.65 / 0.35 blend with the frame before (no flicker). The face:
YuNet (thumbnail.faces, already shipped), the biggest face; without one, the top of the mask. Those numbers and the
two-way smoothing come from Vibha Ramprakash's claude-video-effects skill (MIT, 2026), rewritten here. Measured
2026-10-27 on the user's webcam take: ~19 ms a frame at 540 px, clean round hair and headphones.

    make(cache_dir, sid) -> meta     load(cache_dir, sid) -> Track | None     ensure(plan) -> the sources made
"""
from __future__ import annotations

import json
import math
import os
import threading
from pathlib import Path

import cv2
import numpy as np

from . import footage as FC
from .util import LAB

VERSION = 1
MODEL = LAB / "tools" / "models" / "selfie_segmenter.tflite"
INPUT = 256                       # the model's square input
FACE_SCORE = 0.6                  # a tracking face (thumbnail.FACE_SCORE 0.88 is for picking stills)
SMOOTH_S = 0.18                   # the face track's time constant, applied forwards then backwards
KEYS = ("behind", "guard", "follow", "glass", "shadow", "match")     # the layer keys compose.py integrates with
NEEDS_PERSON = ("behind", "guard", "follow")                        # ... and those that need this module's track

_NET: dict = {}
_LOCK = threading.Lock()


def paths(cache_dir: str | Path, sid: str) -> tuple[Path, Path]:
    d = Path(cache_dir)
    return d / f"{sid}.person.u8", d / f"{sid}.person.json"


def _net():
    key = (os.getpid(), threading.get_ident())
    if key not in _NET:
        if not MODEL.exists():
            raise FileNotFoundError(f"the person model is missing: {MODEL}")
        _NET[key] = cv2.dnn.readNetFromTFLite(str(MODEL))
    return _NET[key]


def guided(I: np.ndarray, p: np.ndarray, r: int, eps: float = 2e-3) -> np.ndarray:
    """He et al.'s guided filter: p's edges moved onto I's (both float32, same size)."""
    k = (2 * r + 1, 2 * r + 1)
    mI, mp = cv2.boxFilter(I, -1, k), cv2.boxFilter(p, -1, k)
    a = (cv2.boxFilter(I * p, -1, k) - mI * mp) / (cv2.boxFilter(I * I, -1, k) - mI * mI + eps)
    b = mp - a * mI
    return np.clip(cv2.boxFilter(a, -1, k) * I + cv2.boxFilter(b, -1, k), 0, 1)


def mask_of(rgb: np.ndarray) -> np.ndarray:
    """The person's mask of one RGB uint8 frame, its size, float32 0..1."""
    net = _net()
    net.setInput(cv2.dnn.blobFromImage(rgb, 1 / 255.0, (INPUT, INPUT)))
    m = np.squeeze(net.forward()).astype(np.float32)
    if m.ndim == 3:
        m = m[..., -1]
    h, w = rgb.shape[:2]
    m = cv2.resize(m, (w, h), interpolation=cv2.INTER_LINEAR)
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    m = guided(g, m, max(2, int(round(8 * min(w, h) / 540))))
    return np.clip((m - 0.5) * 1.6 + 0.5, 0, 1)


def smooth(track: list, fps: float, tau: float = SMOOTH_S) -> np.ndarray | None:
    """Per-frame (cx, cy, w) or None -> the gaps filled in, smoothed forwards then backwards (no lag)."""
    good = [i for i, v in enumerate(track) if v is not None]
    if not good:
        return None
    arr = np.array([v if v is not None else (np.nan,) * 3 for v in track], np.float64)
    idx = np.arange(len(arr))
    for k in range(3):
        ok = ~np.isnan(arr[:, k])
        arr[:, k] = np.interp(idx, idx[ok], arr[ok, k])
    a = 1 - math.exp(-1 / (max(fps, 1.0) * tau))
    for i in range(1, len(arr)):
        arr[i] = arr[i - 1] + a * (arr[i] - arr[i - 1])
    for i in range(len(arr) - 2, -1, -1):
        arr[i] = arr[i + 1] + a * (arr[i] - arr[i + 1])
    return arr


def _face(rgb: np.ndarray, m: np.ndarray):
    from .thumbnail import faces
    h, w = rgb.shape[:2]
    fs = faces(rgb, FACE_SCORE)
    if fs:
        x, y, fw, fh, _ = fs[0]
        return (x + fw / 2) / w, (y + fh / 2) / h, fw / w
    rows = np.where((m > 0.5).sum(1) > w * 0.01)[0]              # no face: the top of the person
    if not len(rows):
        return None
    top = rows[0]
    xs = np.where((m[top:top + max(4, int(h * 0.06))] > 0.5).any(0))[0]
    fw = max(8.0, (xs.max() - xs.min()) * 0.8)
    return float(xs.mean()) / w, (top + fw * 0.7) / h, fw / w


def _light(cache_dir, sid):
    lp, lm = FC.light_paths(cache_dir, sid)
    if not lm.exists():
        return None, None, None
    m = json.loads(lm.read_text(encoding="utf-8"))
    arr = np.memmap(lp, dtype=np.uint8, mode="r", shape=(int(m["frames"]), int(m["height"]) * 3 // 2, int(m["width"])))
    st = lp.stat()
    return m, arr, [st.st_size, int(st.st_mtime)]


def make(cache_dir: str | Path, sid: str, log=None) -> dict:
    """The masks and the face track of source `sid` from its light cache -> <ID>.person.u8 / .json."""
    m, arr, fp = _light(cache_dir, sid)
    if m is None:
        raise FileNotFoundError(f"{sid}: no light cache in {cache_dir} (prep_footage.py makes it)")
    n, h, w = int(m["frames"]), int(m["height"]), int(m["width"])
    fps = float(m.get("fps") or 25.0)
    du, dj = paths(cache_dir, sid)
    tmp = du.with_suffix(".u8.part")
    out = np.memmap(tmp, dtype=np.uint8, mode="w+", shape=(n, h, w))
    prev, track, person = None, [], 0.0
    import time
    t0 = time.time()
    for i in range(n):
        rgb = FC.decode(np.asarray(arr[i]), "i420")
        mk = mask_of(rgb)
        if prev is not None:
            mk = 0.65 * mk + 0.35 * prev
        prev = mk
        out[i] = (mk * 255 + 0.5).astype(np.uint8)
        person += float(mk.mean())
        track.append(_face(rgb, mk))
        if log and i and i % 300 == 0:
            log(f"  {sid}: person {i}/{n} frames ({(time.time() - t0) / i * 1000:.0f} ms a frame)")
    out.flush()
    del out
    os.replace(tmp, du)
    sm = smooth(track, fps)
    meta = {"version": VERSION, "frames": n, "width": w, "height": h, "fps": fps, "light": fp,
            "faces_found": round(sum(v is not None for v in track) / max(1, n), 3),
            "person": round(person / max(1, n), 3),
            "faces": None if sm is None else [[round(float(v), 4) for v in r] for r in sm],
            "ms_a_frame": round((time.time() - t0) / max(1, n) * 1000, 1)}
    dj.write_text(json.dumps(meta, separators=(",", ":")), encoding="utf-8")
    if log:
        log(f"  {sid}: person track made - {n} frames, a face in {meta['faces_found']:.0%}, "
            f"{meta['ms_a_frame']} ms a frame")
    return meta


def fresh(cache_dir: str | Path, sid: str) -> bool:
    du, dj = paths(cache_dir, sid)
    if not (du.exists() and dj.exists()):
        return False
    try:
        meta = json.loads(dj.read_text(encoding="utf-8"))
    except ValueError:
        return False
    _, _, fp = _light(cache_dir, sid)
    return meta.get("version") == VERSION and fp is not None and meta.get("light") == fp


class Track:
    """A source's masks (memmap) and face track, read by the compositor."""

    def __init__(self, cache_dir: str | Path, sid: str):
        du, dj = paths(cache_dir, sid)
        self.meta = json.loads(dj.read_text(encoding="utf-8"))
        n, h, w = self.meta["frames"], self.meta["height"], self.meta["width"]
        self.masks = np.memmap(du, dtype=np.uint8, mode="r", shape=(n, h, w))
        self.faces = None if self.meta.get("faces") is None else np.asarray(self.meta["faces"], np.float32)

    def mask(self, i: int) -> np.ndarray:
        return self.masks[min(max(int(i), 0), self.masks.shape[0] - 1)]

    def face(self, i: int):
        if self.faces is None:
            return None
        return self.faces[min(max(int(i), 0), len(self.faces) - 1)]


def load(cache_dir: str | Path, sid: str) -> Track | None:
    return Track(cache_dir, sid) if fresh(cache_dir, sid) else None


def source_of(spec: dict) -> tuple[Path, str] | None:
    """A plan source -> (its cache folder, its cache ID), from the cache file's name ("<ID>.color.yuv" / "<ID>.u8")."""
    c = spec.get("cache") if isinstance(spec, dict) else None
    if not c:
        return None
    p = Path(c)
    return p.parent, p.name.split(".")[0]


def wanted(plan: dict) -> list[str]:
    """The plan sources a render needs a person track for: a clip with "track": "face" or a "room", and the clips shown
    while a layer asks for behind / guard / follow."""
    out = []
    for L in plan.get("layers", []):                   # a clip whose zoom follows the face / whose room changes
        if L.get("type") == "clip" and L.get("src") in plan.get("sources", {}) and L["src"] not in out \
                and (L.get("track") == "face" or L.get("room")):
            out.append(L["src"])
    asks = [(int(L["start"]), int(L["end"])) for L in plan.get("layers", []) if any(L.get(k) for k in NEEDS_PERSON)]
    if not asks:
        return out
    for L in plan.get("layers", []):
        if L.get("type") == "clip" and L.get("src") in plan.get("sources", {}) and L["src"] not in out:
            if any(int(L["start"]) <= b and a <= int(L["end"]) for a, b in asks):
                out.append(L["src"])
    return out


def ensure(plan: dict, log=print) -> list[str]:
    """Person tracks for every source wanted() that has none yet (or an outdated one) - before a render."""
    made = []
    for sid in wanted(plan):
        where = source_of(plan["sources"][sid])
        if where is None or fresh(*where):
            continue
        lp, _ = FC.light_paths(*where)
        if not lp.exists():
            log(f"  {sid}: no light cache - no person track (graphics stay in front)")
            continue
        with _LOCK:
            make(*where, log=log)
        made.append(sid)
    return made


COVER_MAX = 0.12                  # a graphic over more of the face than this = flagged (Vibha's rule: never the face)
GUARD_MAX = 0.03                  # ... one kept off the face: this much of it under the face's oval = a visible bite


def face_issues(plan: dict, log=print) -> list[dict]:
    """Graphics on the face, before any render: every overlay that is not behind the person, sampled every half second
    over its frames - the share of the face box (from the face track) its alpha covers. Over the face = flagged; one
    that keeps off the face ("guard") is flagged too, since the face then cuts a hole in it (its words clipped - the
    2026-10-27 demo: cards beside a webcam close-up's big face). -> [{"id", "f", "share", "guard"}], the first frame
    per graphic. Overlays not rendered yet are skipped."""
    from .compose import Renderer, OverlayLayer
    from .overlays import paths as ov_paths
    P = json.loads(json.dumps(plan))
    keep = []
    for L in P.get("layers", []):
        if L.get("type") == "overlay" and not ov_paths(L.get("file", ""))[1].exists():
            continue
        keep.append(L)
    P["layers"] = keep
    gl = [L for L in keep if L.get("type") == "overlay" and not L.get("behind") and L.get("blend", "normal") == "normal"]
    if not gl:
        return []
    asks = [(int(L["start"]), int(L["end"])) for L in gl]
    for L in keep:                                     # the clips under them need a person track
        if L.get("type") == "clip" and any(int(L["start"]) <= b and a <= int(L["end"]) for a, b in asks):
            where = source_of(P["sources"].get(L.get("src"), {}))
            if where and not fresh(*where) and FC.light_paths(*where)[0].exists():
                make(*where, log=log)
    R = Renderer(P)
    step = max(1, int(round(float(P["fps"]) / 2)))
    out = []
    for L in R.layers:                                 # (a guarded one is never over the face - but the face cuts a
        if not isinstance(L, OverlayLayer) or L.spec.get("behind") or L.mode != "normal":     # hole in it: move it)
            continue
        for f in range(L.start, L.end + 1, step):
            face = R.face_at(f)
            if face is None:
                continue
            fx, fy, fw = face
            if L.follow:
                continue                                # (pinned / camera-led: placed by the face itself)
            d = f - L.start
            i = min(max(L.inn + (d if L.speed == 1.0 else int(math.floor(d * L.speed))), 0), L.arr.shape[0] - 1)
            a = L.arr[i][..., 3]
            g = bool(L.spec.get("guard"))
            if g:                                       # the oval guard hides (compose.Renderer.integrate)
                x0, x1, y0, y1 = fx - 0.63 * fw, fx + 0.63 * fw, fy - 0.89 * fw, fy + 0.69 * fw
            else:
                x0, x1, y0, y1 = fx - 0.45 * fw, fx + 0.45 * fw, fy - 0.55 * fw, fy + 0.6 * fw
            u0, u1 = int(max(0, (x0 - L.X) / L.sx)), int(min(a.shape[1], (x1 - L.X) / L.sx))
            v0, v1 = int(max(0, (y0 - L.Y) / L.sy)), int(min(a.shape[0], (y1 - L.Y) / L.sy))
            if u1 <= u0 or v1 <= v0:
                continue
            box = ((x1 - x0) / L.sx) * ((y1 - y0) / L.sy)
            share = float(np.asarray(a[v0:v1, u0:u1], np.float32).sum() / 255.0 / max(box, 1.0))
            if share > (GUARD_MAX if g else COVER_MAX):
                out.append({"id": L.id, "f": f, "share": round(share, 2), "guard": g})
                break
    return out


def selfcheck() -> bool:
    """The model runs through OpenCV on a drawn frame (a mask in 0..1 of the frame's size - how good it is, only real
    footage shows: the render self-test); the face track's smoothing has no lag on a step and fills gaps."""
    ok = True
    if not MODEL.exists():
        print("FAIL  person: the model file is missing")
        return False
    img = np.full((480, 270, 3), 40, np.uint8)
    cv2.ellipse(img, (135, 300), (70, 150), 0, 0, 360, (200, 170, 150), -1)
    cv2.circle(img, (135, 140), 45, (210, 180, 160), -1)
    m = mask_of(img)
    ok &= m.shape == (480, 270) and 0 <= float(m.min()) and float(m.max()) <= 1
    tr = [(0.2, 0.3, 0.1)] * 30 + [None] * 5 + [(0.6, 0.3, 0.1)] * 30
    sm = smooth(tr, 30)
    ok &= sm is not None and abs(sm[0, 0] - 0.2) < 0.02 and abs(sm[-1, 0] - 0.6) < 0.02 and abs(sm[32, 0] - 0.4) < 0.05
    ok &= smooth([None, None], 30) is None
    print(("PASS  " if ok else "FAIL  ") + "person: the mask model runs through OpenCV (no MediaPipe), a mask in 0..1 "
          "of the frame's size; the face track smoothed both ways (no lag), gaps filled")
    return bool(ok)
