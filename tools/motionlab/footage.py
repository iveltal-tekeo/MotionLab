"""Frame caches of a project's footage: written once by tools\\prep_footage.py, read by the compositor (compose.py),
the storyboards and the edit scripts. The user's clips are only read; caches live in projects\\<name>\\build\\cache\\.

  colour (default since 0.3.0)  <ID>.color.yuv + <ID>.color.json   YUV 4:2:0 (I420), frame = (height * 3/2, width)
                                bytes = 1.5 bytes per pixel, ~3.9 GB per minute at 1520x1140 / 25 fps; read back as
                                RGB (OpenCV's BT.601 pair: grey levels come back exact, colours within ~2/255 - the
                                final H.264 render is 4:2:0 anyway)
  grey (prep_footage --grey)    <ID>.u8 + <ID>.json                8-bit luma, frame = (height, width), ~2.6 GB per
                                minute - for black-and-white edits like test_4am
Both hold full-range values (ffmpeg's conversion from the source's video range: meta "levels": "single").
An edit script gets plan["sources"] from plan_sources(BUILD); each entry says which cache and "format" it uses.

Light caches (0.6.1, "quality over quantity" step 5 - many clips: a full cache is ~5.6 GB per minute of footage in a
vertical edit): <ID>.light.yuv + <ID>.light.json = every frame at a quarter of the cache's width and height (I420,
~0.35 GB per minute) - the stats, the storyboards, the clip catalogue read it; the full cache beside it is then
SPARSE (meta "segments": [[first frame, count, offset in the file], ...]) = only the frames a plan uses, filled by
prep_footage.ensure() before a render. A frame not filled is the light frame scaled up (never another picture), and
counted (SparseFrames.missing).
"""
from __future__ import annotations

import bisect
import json
from pathlib import Path

import cv2
import numpy as np


def paths(cache_dir: str | Path, sid: str, color: bool) -> tuple[Path, Path]:
    """(data file, meta file) of source `sid`'s colour or grey cache."""
    d = Path(cache_dir)
    return (d / f"{sid}.color.yuv", d / f"{sid}.color.json") if color else (d / f"{sid}.u8", d / f"{sid}.json")


def light_paths(cache_dir: str | Path, sid: str) -> tuple[Path, Path]:
    d = Path(cache_dir)
    return d / f"{sid}.light.yuv", d / f"{sid}.light.json"


def frame_bytes(width: int, height: int, color: bool) -> int:
    return width * height * 3 // 2 if color else width * height


def meta_of(path: str | Path) -> dict | None:
    """The meta beside a cache's data file (<ID>.color.yuv -> .color.json, <ID>.u8 -> .json), if any."""
    p = Path(path)
    m = p.with_name(p.name[:-4] + ".json") if p.name.endswith(".yuv") else p.with_suffix(".json")
    try:
        return json.loads(m.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


class SparseFrames:
    """A sparse full cache read like the memmap of a complete one: frames[i] = the stored frame (grey or I420 rows);
    a frame never filled = the light frame scaled up to the full size (counted in .missing)."""

    def __init__(self, path: Path, meta: dict, frames: int, width: int, height: int, fmt: str):
        self.fmt, self.w, self.h = fmt, int(width), int(height)
        rows = self.h * 3 // 2 if fmt == "i420" else self.h
        self.shape = (int(frames), rows, self.w)
        self.seg = sorted([int(a), int(n), int(o)] for a, n, o in meta.get("segments") or [] if int(n) > 0)
        self.starts = [s[0] for s in self.seg]
        total = max((o + n for _, n, o in self.seg), default=0)
        self.mm = np.memmap(path, dtype=np.uint8, mode="r", shape=(total, rows, self.w)) if total else None
        self.light = None
        lp = Path(path).with_name(f"{meta.get('id')}.light.yuv")
        lm = meta_of(lp)
        if lm and lp.exists():
            self.light = (lm, np.memmap(lp, dtype=np.uint8, mode="r",
                                         shape=(int(lm["frames"]), int(lm["height"]) * 3 // 2, int(lm["width"]))))
        self.missing = 0

    def __len__(self) -> int:
        return self.shape[0]

    def has(self, i: int) -> bool:
        k = bisect.bisect_right(self.starts, int(i)) - 1
        return k >= 0 and self.seg[k][0] <= int(i) < self.seg[k][0] + self.seg[k][1]

    def __getitem__(self, i):
        i = int(i)
        k = bisect.bisect_right(self.starts, i) - 1
        if k >= 0 and i < self.seg[k][0] + self.seg[k][1]:
            return self.mm[self.seg[k][2] + i - self.seg[k][0]]
        self.missing += 1
        if self.light is None:
            return np.zeros(self.shape[1:], np.uint8)
        lm, la = self.light
        rgb = cv2.resize(decode(la[min(max(i, 0), la.shape[0] - 1)], "i420"), (self.w, self.h),
                         interpolation=cv2.INTER_LINEAR)
        return encode(rgb) if self.fmt == "i420" else cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)


def open_memmap(path: str | Path, frames: int, width: int, height: int, fmt: str = "gray"):
    m = meta_of(path)
    if m and m.get("segments") is not None:                 # a sparse cache (0.6.1): only what the plans use
        return SparseFrames(Path(path), m, frames, width, height, fmt)
    rows = int(height) * 3 // 2 if fmt == "i420" else int(height)
    return np.memmap(Path(path), dtype=np.uint8, mode="r", shape=(int(frames), rows, int(width)))


def needed(plan: dict, a: int | None = None, b: int | None = None, handle: int = 0) -> dict[str, list[list[int]]]:
    """The cache frames each source's clip layers show over plan frames a..b (all when None) - merged ranges
    [first, last], each widened by `handle` frames (room for a trim without a refill)."""
    import math
    lo, hi = 0 if a is None else int(a), int(plan["frames"]) - 1 if b is None else int(b)
    want: dict[str, list[list[int]]] = {}
    for L in plan.get("layers", []):
        if L.get("type") != "clip" or not L.get("src"):
            continue
        s, e = max(lo, int(L["start"])), min(hi, int(L["end"]))
        if e < s:
            continue
        sp, hold = float(L.get("speed", 1.0)), bool(L.get("hold"))
        jumps = sorted([[int(x), int(y)] for x, y in L.get("jumps", [[L["start"], L.get("in", 0)]])])
        for k, (f0, i0) in enumerate(jumps):          # each jump's run: the source frames it shows on s..e
            f1 = jumps[k + 1][0] - 1 if k + 1 < len(jumps) else int(L["end"])
            x0, x1 = max(s, f0), min(e, f1)
            if x1 < x0 and not (k == 0 and s < f0):
                continue
            if k == 0 and s < f0:                       # (frames before the first jump show its frame)
                x0 = min(x0, s)
            if hold:
                r = [i0, i0]
            else:
                r = [i0 + int(math.floor((x0 - f0) * sp + 1e-6)), i0 + int(math.floor((max(x0, x1) - f0) * sp + 1e-6))]
            want.setdefault(str(L["src"]), []).append([max(0, r[0] - handle), r[1] + handle])
    out = {}
    for sid, rs in want.items():
        rs.sort()
        m = [rs[0]]
        for r in rs[1:]:
            if r[0] <= m[-1][1] + 1:
                m[-1][1] = max(m[-1][1], r[1])
            else:
                m.append(r)
        out[sid] = m
    return out


def encode(rgb: np.ndarray) -> np.ndarray:
    """(h, w, 3) uint8 RGB -> the (h * 3/2, w) I420 frame stored in a colour cache (h and w even)."""
    return cv2.cvtColor(np.ascontiguousarray(rgb), cv2.COLOR_RGB2YUV_I420)


def decode(frame: np.ndarray, fmt: str) -> np.ndarray:
    """A cached frame as an image: grey (h, w) as stored, I420 -> (h, w, 3) uint8 RGB."""
    if fmt == "i420":
        return cv2.cvtColor(np.ascontiguousarray(frame), cv2.COLOR_YUV2RGB_I420)
    return frame


def load(cache_dir: str | Path, sid: str, color: bool | None = None) -> tuple[dict, np.memmap]:
    """(meta, memmap) of a source's cache; color=None takes the colour cache when there is one, else the grey one."""
    if color is None:
        color = paths(cache_dir, sid, True)[1].exists()
    data, meta_p = paths(cache_dir, sid, color)
    m = json.loads(meta_p.read_text(encoding="utf-8"))
    return m, open_memmap(data, m["frames"], m["width"], m["height"], m.get("format", "gray"))


def image(m: dict, arr: np.ndarray, i: int) -> np.ndarray:
    """Frame i (clamped) of a cache opened with load(), as grey or RGB uint8."""
    return decode(arr[min(max(int(i), 0), arr.shape[0] - 1)], m.get("format", "gray"))


def plan_sources(build_dir: str | Path, color: bool = True) -> dict:
    """plan["sources"] for an edit script: every complete colour (or grey) cache of the project, by source ID."""
    from .project import is_junk, is_photo_twin
    cache = Path(build_dir) / "cache"
    out = {}
    for meta_p in sorted(cache.glob("*.json")):
        if meta_p.name.endswith(".color.json") != color:
            continue
        m = json.loads(meta_p.read_text(encoding="utf-8"))
        if "id" not in m or not m.get("complete"):
            continue
        src = Path(str(m.get("source") or ""))
        if src.name and (is_junk(src) or is_photo_twin(src)):   # cached by an older version (2026-10-24): not a clip
            continue
        out[m["id"]] = {"cache": str(paths(cache, m["id"], color)[0]), "format": m.get("format", "gray"),
                        "frames": m["frames"], "width": m["width"], "height": m["height"], "source": m["source"]}
    if not out:
        raise SystemExit(f"no {'colour' if color else 'grey'} frame caches in {cache} - run "
                         f"tools\\prep_footage.py <project>{'' if color else ' --grey'} first")
    return out
