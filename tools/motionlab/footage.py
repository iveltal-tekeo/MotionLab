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
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np


def paths(cache_dir: str | Path, sid: str, color: bool) -> tuple[Path, Path]:
    """(data file, meta file) of source `sid`'s colour or grey cache."""
    d = Path(cache_dir)
    return (d / f"{sid}.color.yuv", d / f"{sid}.color.json") if color else (d / f"{sid}.u8", d / f"{sid}.json")


def frame_bytes(width: int, height: int, color: bool) -> int:
    return width * height * 3 // 2 if color else width * height


def open_memmap(path: str | Path, frames: int, width: int, height: int, fmt: str = "gray") -> np.memmap:
    rows = int(height) * 3 // 2 if fmt == "i420" else int(height)
    return np.memmap(Path(path), dtype=np.uint8, mode="r", shape=(int(frames), rows, int(width)))


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
    cache = Path(build_dir) / "cache"
    out = {}
    for meta_p in sorted(cache.glob("*.json")):
        if meta_p.name.endswith(".color.json") != color:
            continue
        m = json.loads(meta_p.read_text(encoding="utf-8"))
        if "id" not in m or not m.get("complete"):
            continue
        out[m["id"]] = {"cache": str(paths(cache, m["id"], color)[0]), "format": m.get("format", "gray"),
                        "frames": m["frames"], "width": m["width"], "height": m["height"], "source": m["source"]}
    if not out:
        raise SystemExit(f"no {'colour' if color else 'grey'} frame caches in {cache} - run "
                         f"tools\\prep_footage.py <project>{'' if color else ' --grey'} first")
    return out
