"""Overlay clips for the compositor: the transparent graphics tools\\overlay.py renders with HyperFrames (HTML / CSS /
GSAP -> RGBA PNG frames -> a Rec.709-tagged ProRes 4444 clip for DaVinci Resolve). The lab reads a straight-RGBA raw
cache next to the clip, cropped to the area that is ever visible (<clip>.rgba + <clip>.rgba.json): overlay.py writes
it from the PNG frames (exact pixels); any other transparent clip (e.g. a ProRes 4444 from another program) is
decoded into it on first use. The renderer (also each parallel worker) then reads any frame directly.
A plan layer: {"type": "overlay", "id": "title", "start": 0, "end": 29, "file": "<absolute path of the .mov>",
"in": 0, "rect": [x, y, w, h] (default: where and how big it was authored), "blend": "normal" | "add" | "screen"}.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

from .util import tool

ACCURATE = "accurate_rnd+full_chroma_int"         # exact 10/12-bit <-> 8-bit conversion (fast rounding is ~2/255 off)


def paths(mov: str | Path) -> tuple[Path, Path]:
    m = Path(mov)
    return m.with_name(m.name + ".rgba"), m.with_name(m.name + ".rgba.json")


def fingerprint(mov: str | Path) -> dict:
    st = Path(mov).stat()
    return {"size": st.st_size, "mtime_ns": st.st_mtime_ns}


def probe(mov: str | Path) -> dict:
    r = subprocess.run([tool("ffprobe"), "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                        "stream=width,height,pix_fmt,nb_read_packets,r_frame_rate,color_space,color_range",
                        "-of", "json", str(mov)], capture_output=True, text=True)
    s = json.loads(r.stdout or "{}").get("streams", [{}])[0]
    if not s.get("width"):
        raise RuntimeError(f"not a readable video: {mov}")
    num, _, den = str(s.get("r_frame_rate", "25/1")).partition("/")
    pix = s.get("pix_fmt") or ""
    return {"width": int(s["width"]), "height": int(s["height"]), "frames": int(s.get("nb_read_packets") or 0),
            "fps": float(num) / float(den or 1), "pix_fmt": pix,
            "alpha": pix.startswith(("yuva", "rgba", "bgra", "argb", "abgr", "gbrap", "ya")) or pix == "pal8",
            "color_space": s.get("color_space"), "color_range": s.get("color_range")}


def build_cache(mov: str | Path, frames: Callable[[], Iterable[np.ndarray]], width: int, height: int, fps: float,
                source: str = "") -> dict:
    """Write the RGBA crop cache of `mov` from its frames ((h, w, 4) uint8 straight RGBA; `frames()` is called twice:
    the first pass finds the union of the visible area, the second writes it)."""
    x0, y0, x1, y1 = width, height, -1, -1
    for fr in frames():
        a = fr[..., 3]
        ys, xs = np.nonzero(a.max(axis=1))[0], np.nonzero(a.max(axis=0))[0]
        if len(ys):
            x0, x1 = min(x0, int(xs[0])), max(x1, int(xs[-1]))
            y0, y1 = min(y0, int(ys[0])), max(y1, int(ys[-1]))
    if x1 < 0:                                    # nothing visible: keep one pixel
        x0 = y0 = x1 = y1 = 0
    raw, meta_p = paths(mov)
    tmp = raw.with_name(raw.name + ".part")
    n = 0
    with open(tmp, "wb") as f:
        for fr in frames():
            f.write(np.ascontiguousarray(fr[y0:y1 + 1, x0:x1 + 1]).tobytes())
            n += 1
    os.replace(tmp, raw)
    m = {"clip": str(mov), "fingerprint": fingerprint(mov), "width": int(width), "height": int(height), "fps": fps,
         "frames": n, "crop": [x0, y0, x1 - x0 + 1, y1 - y0 + 1], "source": source, "complete": True}
    meta_p.write_text(json.dumps(m, indent=1), encoding="utf-8")
    return m


def _decoded(mov: Path, info: dict):
    """Frames of any clip as straight RGBA (opaque clips get alpha 255: light for add / screen layers)."""
    W, H = info["width"], info["height"]
    mat = "bt601" if info.get("color_space") in ("smpte170m", "bt470bg") else "bt709"    # untagged: Rec.709
    rng = "pc" if info.get("color_range") == "pc" else "tv"
    vf = f"scale=in_color_matrix={mat}:in_range={rng}:flags={ACCURATE},format=rgba"
    fb = W * H * 4
    p = subprocess.Popen([tool("ffmpeg"), "-v", "error", "-nostdin", "-i", str(mov), "-map", "0:v:0", "-vf", vf,
                          "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
                         stdout=subprocess.PIPE, bufsize=fb * 2)
    try:
        while True:
            buf = p.stdout.read(fb)
            if len(buf) < fb:
                break
            yield np.frombuffer(buf, np.uint8).reshape(H, W, 4)
    finally:
        p.stdout.close()
        p.wait()


def prepare(mov: str | Path, force: bool = False) -> dict:
    """The cache's meta; decodes the clip into the cache first unless an up-to-date one exists."""
    mov = Path(mov)
    raw, meta_p = paths(mov)
    if not force and meta_p.exists() and raw.exists():
        m = json.loads(meta_p.read_text(encoding="utf-8"))
        if m.get("fingerprint") == fingerprint(mov) and m.get("complete"):
            return m
    info = probe(mov)
    return build_cache(mov, lambda: _decoded(mov, info), info["width"], info["height"], info["fps"], "decoded")


def load(mov: str | Path) -> tuple[dict, np.memmap]:
    """(meta, frames (n, h, w, 4) straight RGBA of the visible crop) - prepares the cache first if needed."""
    m = prepare(mov)
    raw, _ = paths(mov)
    cw, ch = m["crop"][2], m["crop"][3]
    return m, np.memmap(raw, dtype=np.uint8, mode="r", shape=(m["frames"], ch, cw, 4))
