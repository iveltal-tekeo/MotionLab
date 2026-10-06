"""Rebuild a MotionLab plan (plan_vN.json) as a native, editable DaVinci Resolve Studio project ("option 2").

    .venv\\Scripts\\python tools\\resolve_build.py projects\\test_4am\\build\\plan_v1.json --replace
    ... --sections S1,S2           build only these sections (development; default: all)
    ... --render 0 517             render that frame range from Resolve to build\\resolve\\<timeline>_<a>-<b>.mp4
    ... --render-full              render the whole timeline to build\\<project>_resolve_vN.mp4
    ... --no-build                 only render (the timeline must exist)
    ... --only firework1,firework2  re-import just these Fusion comps into the existing timeline (fast tuning)
    ... --doctor                   check Resolve, media, LUTs and the timeline against the build (read-only)
    ... --diff                     list what was changed by hand in Resolve since the build (read-only; edited
                                   comps are saved to build\\resolve\\edits\\<date time>\\ as .comp text)
    ... --overwrite-edits          let --only (or --replace --delete-old) replace things changed by hand (saved first)

Needs DaVinci Resolve Studio running with Preferences > System > General > External scripting = Local.
The user's footage and the reference are only read. Everything this tool makes goes into the plan's build folder
(build\\resolve\\: luts, comps, media, renders); the only exception is a copy of the grade LUTs in Resolve's LUT folder
(...\\Support\\LUT\\MotionLab\\<project>\\), because the Color page only applies LUTs it has discovered there.

How the plan maps to Resolve (docs\\option2_resolve.md, section 3):
  * Timeline 1520x1080, 25 fps, start 00:00:00:00: plan frame f = timeline frame f. A1 = the reference audio.
  * V1 = a grey 0.045 carrier clip (ProRes, generated into build\\resolve\\media) = the plan background.
  * Static panels = Edit-page clips of the original DJI files: in-point = 2 x cache frame, Edit-page
    Zoom / Pan / Tilt / Crop reproduce compose.sample_patch exactly, the grade is a Color-page LUT, flash frames
    are 1-frame cuts with a flash LUT, holds are freeze frames (speed 0).
  * Everything animated is a Fusion comp (.comp text in build\\resolve\\comps) on a carrier clip placed so that
    comp frame = timeline frame: each pan board (panels + one keyframed Transform), fades, titles, clocks,
    streaks, fireworks, the mosaic zoom and the grain.
Levels: Resolve decodes the DJI files correctly (video range). Plans designed on the old lab caches (which expanded
video range twice, e.g. test_4am v1: plan "levels": "double") get LUTs with that extra tv->full step, so Resolve
reproduces their look; plans on new caches ("single") get plain LUTs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import graphics as G  # noqa: E402
from motionlab.compose import Curve  # noqa: E402
from motionlab.fusion import (Comp, Conn, Expr, FuID, Path as FPath, Raw, Spline, media_in, parse_comp,  # noqa: E402
                              spline_at)
from motionlab.timecode import frame_to_tc  # noqa: E402
from motionlab.util import log, setup_console, tool  # noqa: E402

LAB = Path(__file__).resolve().parents[1]
RESOLVE_API = Path(r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting")
RESOLVE_LIB = Path(r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll")
RESOLVE_LUTS = Path(r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT")
SRC_W, SRC_H = 1520, 1140          # a 4:3 source cover-fitted to the 1520 x 1080 timeline (= the lab's cache frame)
# Fusion Gaussian Blur: measured sigma (px) for a given XBlurSize (calibrated on Resolve 21.1)
BLUR_CAL = [(1, 1.153), (2, 2.074), (3, 2.922), (4, 3.773), (6, 5.583), (8, 7.274), (10, 8.960), (12, 10.593),
            (15, 12.992), (18, 15.360), (22, 18.774), (26, 21.685), (30, 24.468), (35, 28.718), (40, 31.739),
            (50, 39.255)]
SECTIONS = {"S1": (0, 517, "intro, clocks, stepped fade-in"), "S2": (518, 1330, "collage 1 + pan 1"),
            "S3": (1331, 1492, "trio, flash, night drift"), "S4": (1493, 2265, "light flicker + pan 2"),
            "S5": (2266, 2582, "profile, split screen, collage 3"),
            "S6": (2583, 3180, "jump cuts, pan 3, photo strips, fireworks, fade"),
            "S7": (3181, 3895, "clock, mosaic zoom, red clock, end title")}


def resolve_state() -> str:
    """'running', 'not responding' or 'not running' (Windows' own flag, independent of the system language)."""
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "(Get-Process Resolve -ErrorAction SilentlyContinue | Select-Object -First 1).Responding"],
                         capture_output=True, text=True).stdout.strip()
    return {"True": "running", "False": "not responding"}.get(out, "not running")


class Watchdog:
    """A scripting call into a frozen Resolve never returns (seen twice on 21.1: a combined timeline SetSettings and
    a cancelled render). The main thread reports progress with beat(); if nothing happens for `stall` seconds this
    thread asks Windows whether Resolve still responds and, if not, explains and exits instead of hanging forever."""

    def __init__(self, stall: float = 120.0):
        self.t, self.what, self.stall = time.time(), "connecting", stall
        threading.Thread(target=self._run, daemon=True).start()

    def beat(self, what: str = ""):
        self.t = time.time()
        if what:
            self.what = what

    def _run(self):
        while True:
            time.sleep(10)
            if time.time() - self.t < self.stall:
                continue
            state = resolve_state()
            if state != "running":
                print(f"\nERROR: DaVinci Resolve is {state} (stuck {time.time() - self.t:.0f}s during: {self.what}).\n"
                      "Close Resolve (Task Manager if needed), start it again, then re-run this command; the project "
                      "was saved after the last successful build.", flush=True)
                os._exit(3)
            self.t = time.time() - self.stall / 2          # responsive but slow: look again a bit later


WD: Watchdog | None = None


def beat(what: str = ""):
    if WD:
        WD.beat(what)


TC_FPS = 25.0                      # the plan's frame rate (set in main); every frame number shown gets its timecode


def tc(f) -> str:
    return frame_to_tc(int(f), TC_FPS)


def blur_size(sigma: float) -> float:
    s, g = zip(*BLUR_CAL)
    return float(np.interp(sigma, g, s, left=sigma / 1.15, right=sigma / 0.785))


def section_of(f: int) -> str:
    for k, (a, b, _) in SECTIONS.items():
        if a <= f <= b:
            return k
    return "S7"


# ================================================================================================= geometry
def cover_crop(rect, zoom: float, ax: float, ay: float, sw: float = SRC_W, sh: float = SRC_H):
    """compose.sample_patch: the source crop (u0, v0, cw, ch) that is cover-fitted into rect, in source pixels."""
    x, y, w, h = rect
    ar = w / h
    cw, ch = (sh * ar, float(sh)) if sw / sh > ar else (float(sw), sw / ar)
    cw, ch = cw / zoom, ch / zoom
    cx = min(max(ax * sw, cw / 2), sw - cw / 2)
    cy = min(max(ay * sh, ch / 2), sh - ch / 2)
    return cx - cw / 2, cy - ch / 2, cw, ch


def edit_page_props(rect, zoom, ax, ay, W=1520, H=1080) -> dict:
    """Edit-page transform that shows the cover crop exactly in rect (measured on Resolve 21.1: zoom about the frame
    centre, Pan = +x px, Tilt = up in units of H/source-height, crop in input-scaled source pixels before zoom)."""
    x, y, w, h = rect
    u0, v0, cw, ch = cover_crop(rect, zoom, ax, ay)
    Z = w / cw
    ky = SRC_H / H
    return {"ZoomX": Z, "ZoomY": Z, "Pan": x - W / 2 + Z * (SRC_W / 2 - u0),
            "Tilt": -(y - H / 2 + Z * (SRC_H / 2 - v0)) / ky,
            "CropLeft": u0, "CropRight": SRC_W - u0 - cw, "CropTop": v0, "CropBottom": SRC_H - v0 - ch}


def fusion_place(rect, zoom, ax, ay, CW, CH, dx=0.0):
    """Merge Size / Center for a 1520 x 1140 source image cover-fitted into rect on a CW x CH canvas."""
    x, y, w, h = rect
    u0, v0, cw, ch = cover_crop(rect, zoom, ax, ay)
    Z = w / cw
    px = x + dx + (SRC_W / 2 - u0) * Z
    py = y + (SRC_H / 2 - v0) * Z
    return Z, (px / CW, 1 - py / CH)


def norm_center(x, y, w, h, CW, CH):
    return ((x + w / 2) / CW, 1 - (y + h / 2) / CH)


# ================================================================================================= LUTs
class Luts:
    """One 3D .cube per (grade, gain, flash) the edit needs: B&W from Rec.709 luma, the lab cache's extra
    tv->full step, levels / gamma / output range (compose.grade_lut), gain, flash. Masters go to build\\resolve\\luts;
    a copy goes to Resolve's LUT folder so the Color page can use them."""

    def __init__(self, grades: dict, out_dir: Path, resolve_sub: str, double_levels: bool = False):
        self.grades = grades
        self.double = double_levels
        self.dir = out_dir
        self.sub = resolve_sub
        self.rdir = RESOLVE_LUTS / resolve_sub
        self.made: dict[str, Path] = {}

    @staticmethod
    def key(grade: str, gain: float = 1.0, flash_over: float = 0.0, flash_white: bool = False) -> str:
        k = grade
        if abs(gain - 1.0) > 1e-9:
            k += f"_g{gain:g}"
        if flash_over:
            k += f"_fo{flash_over:g}"
        if flash_white:
            k += "_fw"
        return k

    def get(self, grade: str, gain: float = 1.0, flash_over: float = 0.0, flash_white: bool = False) -> str:
        k = self.key(grade, gain, flash_over, flash_white)
        if k not in self.made:
            g = {"black": 40, "white": 245, "gamma": 1.5, "out_black": 0.03, "out_white": 0.85, **self.grades[grade]}
            n = 65
            a = np.linspace(0.0, 1.0, n)
            B, Gg, R = np.meshgrid(a, a, a, indexing="ij")             # .cube order: red changes fastest
            Y = 0.2126 * R + 0.7152 * Gg + 0.0722 * B
            c = 255.0 * Y
            if self.double:                                            # the old lab cache's second tv->full step
                c = np.clip((c - 16.0) * 255.0 / 219.0, 0.0, 255.0)
            x = np.clip((c - g["black"]) / max(1.0, g["white"] - g["black"]), 0.0, 1.0)
            v = g["out_black"] + (g["out_white"] - g["out_black"]) * x ** g["gamma"]
            v = np.minimum(1.0, v * gain)
            if flash_over:
                v = v + flash_over * (1.0 - v)
            if flash_white:
                v = 0.86 + 0.06 * v
            p = self.dir / f"{k}.cube"
            self.dir.mkdir(parents=True, exist_ok=True)
            with open(p, "w", newline="\n") as f:
                f.write(f'TITLE "MotionLab {k}"\n# grade {grade} {json.dumps(g)} gain {gain:g} flash_over '
                        f'{flash_over:g} flash_white {flash_white}\nLUT_3D_SIZE {n}\nDOMAIN_MIN 0 0 0\n'
                        f'DOMAIN_MAX 1 1 1\n')
                f.write("\n".join(f"{t:.6f} {t:.6f} {t:.6f}" for t in v.ravel()))
                f.write("\n")
            self.made[k] = p
        return k

    def install(self):
        self.rdir.mkdir(parents=True, exist_ok=True)
        for k, p in self.made.items():
            shutil.copy2(p, self.rdir / p.name)

    def resolve_path(self, k: str) -> str:            # Color page (relative to the master LUT folder)
        return f"{self.sub}/{k}.cube"

    def file_path(self, k: str) -> str:               # Fusion FileLUT (absolute, the same installed copy)
        return str(self.rdir / f"{k}.cube")


# ================================================================================================= units
@dataclass
class Piece:                       # one Edit-page clip
    a: int
    b: int
    src: str
    frame: int                     # DJI frame shown at frame a (= 2 x cache frame)
    hold: bool
    lut: str
    props: dict
    label: str


@dataclass
class Unit:
    name: str
    order: float
    a: int
    b: int
    kind: str                      # "clip" (Edit-page pieces) or "comp" (Fusion comp on a carrier)
    pieces: list = field(default_factory=list)
    builder: tuple | None = None   # (function, args) that returns the Comp
    composite: str = "normal"
    color: str = ""
    note: str = ""
    track: int = 0
    comp: Comp | None = None
    comp_path: Path | None = None


class Ctx:
    """Everything the comp builders need: plan, curves, LUTs, sources (media IDs filled in once known)."""

    def __init__(self, plan: dict, luts: Luts):
        self.plan = plan
        self.W, self.H = int(plan["width"]), int(plan["height"])
        self.bg = float(plan.get("background", 0.045))
        self.curves = plan.get("curves", {})
        self.luts = luts
        self.media: dict[str, dict] = {}          # source ID -> {path, id, name, frames, width, height, fps}
        self.assets: dict[str, dict] = {}         # layer ID -> pre-rendered still image(s) (strips, mosaic wall)

    def curve(self, spec, default=0.0) -> Curve:
        return Curve(spec, self.curves, default)

    def dji(self, cache_frame: float) -> float:
        return 2.0 * cache_frame


# ------------------------------------------------------------------------------------------------- comp helpers
# Tools that generate images get Depth = 4 (float32). With 'Default' depth, Resolve 21.1 renders them in 8-bit right
# after ImportFusionComp but in float after the project is reopened (the comp prefs say float either way), so the
# same timeline rendered differently before and after a reload (measured: grain mean 10.35 vs 10.97, std 1.68 vs
# 1.58 on a flat background).
GEN_DEPTH = {"Background", "RectangleMask", "PolylineMask", "EllipseMask", "FastNoise", "pRender"}


class FB:
    """Builder for one Fusion comp: shared source MediaIns, solids, masks; frames are timeline frames."""

    def __init__(self, ctx: Ctx, name: str):
        self.ctx = ctx
        self.name = name
        self.c = Comp(fps=float(ctx.plan["fps"]), width=ctx.W, height=ctx.H)
        self.srcs: dict[str, str] = {}
        self.layer = 1

    def add(self, kind, name=None, **inputs) -> str:
        if kind in GEN_DEPTH:
            inputs.setdefault("Depth", 4)
        return self.c.add(kind, name, **inputs)

    def source(self, sid: str, tag: str) -> str:
        """MediaIn of the original clip (by media pool ID) resized to 1520 x 1140 with a box filter (the frame the
        lab's cache holds). One per panel / still (tag): each MediaIn keeps its own decoder, so a panel reads its
        clip sequentially and a still decodes its frame once (several elements sharing one MediaIn of a long-GOP
        HEVC clip force a keyframe seek for every request - a render then takes hours)."""
        key = (sid, tag)
        if key not in self.srcs:
            m = self.ctx.media[sid]
            mi = media_in(self.c, m["path"], m["id"], m["name"], m["frames"], m["width"], m["height"], m["fps"],
                          tool_name=f"Src{sid}_{tag}", layer=self.layer)
            self.layer += 1
            # keep the clip valid at every comp time (TimeStretchers ask for its frames from any time)
            self.c.tools[-1].inputs.update(HoldLastFrame=10000)
            rs = self.add("BetterResize", f"Src{sid}_{tag}_1520x1140", Input=Conn(mi), Width=SRC_W, Height=SRC_H,
                          UseFrameFormatSettings=0, FilterMethod=1)
            self.srcs[key] = rs
        return self.srcs[key]

    def bg(self, w, h, rgb=(0.0, 0.0, 0.0), alpha=0.0, name=None) -> str:
        return self.add("Background", name, Width=int(w), Height=int(h), UseFrameFormatSettings=0,
                        TopLeftRed=rgb[0], TopLeftGreen=rgb[1], TopLeftBlue=rgb[2], TopLeftAlpha=alpha)

    def rect(self, x, y, w, h, CW, CH, name=None, prev=None, angle=0.0, level=None) -> str:
        ins = dict(Center=norm_center(x, y, w, h, CW, CH), Width=w / CW, Height=h / CH, MaskWidth=int(CW),
                   MaskHeight=int(CH), UseFrameFormatSettings=0, ClippingMode=FuID("None"))
        if angle:
            ins["Angle"] = angle
        if level is not None:
            ins["Level"] = level
        if prev:
            ins["EffectMask"] = Conn(prev, "Mask")
        return self.add("RectangleMask", name, **ins)

    def polygon(self, pts, CW, CH, name=None, prev=None, level=None) -> str:
        """Closed polygon mask; pts in canvas pixels (x right, y down). Chained masks combine with Maximum: the
        default 'Merge' paints a shape OVER the incoming mask, so a shape keyed to level 0 would erase it."""
        cx, cy = CW / 2, CH / 2
        txt = ", ".join(f"{{ Linear = true, X = {(px - cx) / CW:.7f}, Y = {-(py - cy) / CH:.7f}, LX = 0, LY = 0, "
                        f"RX = 0, RY = 0 }}" for px, py in pts)
        ins = dict(Center=(0.5, 0.5), Polyline=Raw(f"Polyline {{ Closed = true, Points = {{ {txt} }} }}"),
                   MaskWidth=int(CW), MaskHeight=int(CH), UseFrameFormatSettings=0, ClippingMode=FuID("None"))
        if level is not None:
            ins["Level"] = level
        if prev:
            ins["EffectMask"] = Conn(prev, "Mask")
            ins["PaintMode"] = FuID("Maximum")
        return self.add("PolylineMask", name, **ins)

    def out(self, tool_name: str):
        self.add("Saver", "MediaOut1", Input=Conn(tool_name), Index="0")
        return self.c


def frames_spline(a: int, b: int, fn, pad: int = 1, step: bool = False) -> Spline:
    """Per-frame keys of fn(f) on [a, b], 0 one frame outside (linear keys are exact on every integer frame)."""
    keys = [(a - pad, 0.0)] if pad else []
    keys += [(f, float(fn(f))) for f in range(a, b + 1)]
    if pad:
        keys.append((b + pad, 0.0))
    return Spline(keys, step=step)


def source_time_keys(L: dict, ctx: Ctx) -> list:
    """TimeStretcher keys (timeline frame -> DJI frame) of a clip layer: jumps restart the source, speed s plays
    2*s DJI frames per timeline frame (s = 0.5 = every DJI frame, smooth slow motion as Resolve's clip speed),
    hold = freeze of DJI frame 2 x in."""
    a, b = int(L["start"]), int(L["end"])
    speed = float(L.get("speed", 1.0))
    hold = bool(L.get("hold", False))
    jumps = sorted([[int(j), int(i)] for j, i in L.get("jumps", [[a, L.get("in", 0)]])])
    last = ctx.media[L["src"]]["frames"] - 1 if L["src"] in ctx.media else 1e9
    keys = []
    for k, (j0, cin) in enumerate(jumps):
        j1 = jumps[k + 1][0] - 1 if k + 1 < len(jumps) else b
        s0 = ctx.dji(cin)
        # per frame, clamped to the source's last frame like the lab (Renderer.frame); the Spline drops the
        # keys a straight line reproduces
        vals = [(f, min(last, s0 if hold else s0 + 2.0 * speed * (f - j0))) for f in range(j0, j1 + 1)]
        if vals[-1][1] >= last and not hold:
            f_end = next(f for f, v in vals if v >= last)
            log(f"  note: {L['id']}: source {L['src']} ends at f{f_end} ({tc(f_end)}); its last frame "
                f"is held to f{j1} (as in the lab render)")
        keys += vals
    return keys


def panel(fb: FB, L: dict, bg: str, CW: int, CH: int, dx: float = 0.0, name: str | None = None) -> str:
    """A clip layer as a Fusion panel merged onto bg: source -> TimeStretcher -> grade LUT -> flash -> Merge with
    the cover-fit Size / Center and an exact rectangle mask; Blend = on / off (and the opacity curve)."""
    ctx = fb.ctx
    lid = name or L["id"]
    a, b = int(L["start"]), int(L["end"])
    src = fb.source(L["src"], lid)
    ts = fb.add("TimeStretcher", f"{lid}_time", Input=Conn(src), SourceTime=Spline(source_time_keys(L, ctx)),
                InterpolateBetweenFrames=0)
    gain = float(L.get("gain", 1.0))
    lut = ctx.luts.get(L.get("grade", "default"), gain)
    img = fb.add("FileLUT", f"{lid}_grade", Input=Conn(ts), LUTFile=ctx.luts.file_path(lut))
    fo = {int(k): float(v) for k, v in L.get("flash_over", {}).items()}
    fw = set(int(v) for v in L.get("flash_white", []))
    if fo or fw:
        if fo and fw:
            raise ValueError(f"{lid}: flash_over and flash_white on one layer are not supported")
        col, val = (1.0, None) if fo else (0.86 / 0.94, 0.94)
        keys = {f: (fo.get(f, 0.0) if fo else (val if f in fw else 0.0)) for f in range(a, b + 1)}
        white = fb.bg(SRC_W, SRC_H, (col, col, col), 1.0, name=f"{lid}_flash_white")
        img = fb.add("Merge", f"{lid}_flash", Background=Conn(img), Foreground=Conn(white),
                     Blend=Spline(sorted(keys.items()), step=True))
    zoom = float(L.get("zoom", 1.0))
    an = L.get("anchor", [0.5, 0.5])
    animated = isinstance(an[0], dict) or isinstance(an[1], dict) or isinstance(L.get("zoom"), (dict, str))
    x, y, w, h = [float(v) for v in L["rect"]]
    opac = ctx.curve(L.get("opacity"), 1.0)
    blend = frames_spline(a, b, lambda f: opac(f))
    if not animated:
        Z, center = fusion_place((x, y, w, h), zoom, float(an[0]), float(an[1]), CW, CH, dx)
        size = Z
        if Z < 0.77:                    # pre-reduce like compose.sample_patch (area filter), keep 4:3 exactly
            k = max(1, int(round(380 * Z * 1.111)))
            img = fb.add("BetterResize", f"{lid}_prereduce", Input=Conn(img), Width=4 * k, Height=3 * k,
                         UseFrameFormatSettings=0, FilterMethod=1)
            size = Z / (4 * k / SRC_W)
    else:
        za, aa, ab = ctx.curve(L.get("zoom"), 1.0), ctx.curve(an[0], 0.5), ctx.curve(an[1], 0.5)
        sk, ck = [], []
        for f in range(a, b + 1):
            Z, cen = fusion_place((x, y, w, h), za(f), aa(f), ab(f), CW, CH, dx)
            sk.append((f, Z))
            ck.append((f, cen[0], cen[1]))
        size, center = Spline(sk), FPath(ck)
    mask = fb.rect(x + dx, y, w, h, CW, CH, name=f"{lid}_box")
    return fb.add("Merge", lid, Background=Conn(bg), Foreground=Conn(img), Size=size, Center=center,
                  Blend=blend, EffectMask=Conn(mask, "Mask"), FilterMethod=2)


# ------------------------------------------------------------------------------------------------- graphics
def text_strokes(spec: dict) -> tuple:
    """graphics.text_mask geometry as rectangles in output pixels: [(x, y, w, h)], stroke, X0, Y0."""
    text = spec["text"].upper()
    height = float(spec.get("height", 34))
    ws = float(spec.get("width_scale", 1.0))
    tracking = float(spec.get("tracking", 0.55))
    u = height / 6.0
    ux = u * ws
    st = float(spec["stroke"]) if spec.get("stroke") is not None else max(1.0, height * 0.085)
    pad = st * 2
    widths = [2.2 * ux if ch == " " else (st if ch in G.NARROW else 4 * ux + st) for ch in text]
    total = sum(widths) + tracking * ux * 2 * max(0, len(text) - 1)
    Wm, Hm = int(math.ceil(total + 2 * pad)), int(math.ceil(height + st + 2 * pad))
    rects = []
    x = pad + st / 2
    for ch, w in zip(text, widths):
        for poly in G.GLYPHS.get(ch, []):
            pts = [(x + px * ux, pad + st / 2 + py * u) for px, py in poly]
            if len(pts) == 2 and abs(pts[0][0] - pts[1][0]) < 0.5 and abs(pts[0][1] - pts[1][1]) < 0.5:
                r = st * 0.6
                rects.append((pts[0][0] - r, pts[0][1] - r, 2 * r, 2 * r, 0.0))
                continue
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                length = math.hypot(x1 - x0, y1 - y0)
                if abs(y1 - y0) < 1e-6 or abs(x1 - x0) < 1e-6:        # axis-aligned: square caps / corners
                    rects.append((min(x0, x1) - st / 2, min(y0, y1) - st / 2, abs(x1 - x0) + st,
                                  abs(y1 - y0) + st, 0.0))
                else:
                    cxm, cym = (x0 + x1) / 2, (y0 + y1) / 2
                    ang = math.degrees(math.atan2(-(y1 - y0), x1 - x0))
                    rects.append((cxm - (length + st) / 2, cym - st / 2, length + st, st, ang))
        x += w + tracking * ux * 2
    X0 = int(round(float(spec.get("cx", 760)) - Wm / 2))
    Y0 = int(round(float(spec.get("cy", 540)) - Hm / 2))
    return [(X0 + rx, Y0 + ry, rw, rh, ang) for rx, ry, rw, rh, ang in rects], st, Wm, Hm, X0, Y0


def glow_shape(fb: FB, last: str, mask: str, color, glow: float, sigma: float, opacity, a: int, b: int,
               tag: str, level: float = 1.0) -> str:
    """compose._glow_composite: add blur(mask) * glow * color, then mask * color normally (premultiplied output:
    the glow has alpha 0, so on the Edit page it adds onto the tracks below)."""
    W, H = fb.ctx.W, fb.ctx.H
    op = fb.ctx.curve(opacity, 1.0)
    if glow > 0:
        white = fb.add("Merge", f"{tag}_maskimg", Background=Conn(fb.bg(W, H)),
                       Foreground=Conn(fb.bg(W, H, (1, 1, 1), 1.0)), EffectMask=Conn(mask, "Mask"))
        blur = fb.add("Blur", f"{tag}_glowblur", Input=Conn(white), XBlurSize=blur_size(sigma),
                      Filter=FuID("Gaussian"))
        last = fb.add("Merge", f"{tag}_glow", Background=Conn(last),
                      Foreground=Conn(fb.bg(W, H, color, 0.0, name=f"{tag}_glowcolor")),
                      Blend=frames_spline(a, b, lambda f: glow * level * op(f)), EffectMask=Conn(blur, "Output"))
    return fb.add("Merge", f"{tag}_body", Background=Conn(last),
                  Foreground=Conn(fb.bg(W, H, color, 1.0, name=f"{tag}_color")),
                  Blend=frames_spline(a, b, lambda f: level * op(f)), EffectMask=Conn(mask, "Mask"))


def comp_text(ctx: Ctx, L: dict) -> Comp:
    fb = FB(ctx, L["id"])
    W, H = ctx.W, ctx.H
    a, b = int(L["start"]), int(L["end"])
    last = fb.bg(W, H, name="Transparent")
    rects, st, Wm, Hm, X0, Y0 = text_strokes(L)
    color = L.get("color", [0.85, 0.05, 0.05])
    box = L.get("box")
    if box:                                                   # faint frame around the title (end card)
        px, py = box.get("pad", [60, 40])
        bw, bh, lw = Wm + 2 * px, Hm + 2 * py, float(box.get("width", 2))
        bx, by = X0 - px, Y0 - py
        m = None
        for i, (rx, ry, rw, rh) in enumerate(((bx, by, bw, lw), (bx, by + bh - lw, bw, lw), (bx, by, lw, bh),
                                              (bx + bw - lw, by, lw, bh))):
            m = fb.rect(rx, ry, rw, rh, W, H, name=f"Frame{i + 1}", prev=m)
        last = glow_shape(fb, last, m, box.get("color", color), float(box.get("glow", 1.2)),
                          float(box.get("sigma", 10)), L.get("opacity"), a, b, "Frame",
                          level=float(box.get("strength", 0.35)))
    m = None
    for i, (rx, ry, rw, rh, ang) in enumerate(rects):
        m = fb.rect(rx, ry, rw, rh, W, H, name=f"Stroke{i + 1}", prev=m, angle=ang)
    last = glow_shape(fb, last, m, color, float(L.get("glow", 0.0)),
                      float(L.get("glow_sigma", float(L.get("height", 34)) * 0.18)), L.get("opacity"), a, b, "Text")
    return fb.out(last)


def comp_clock(ctx: Ctx, L: dict) -> Comp:
    """Seven-segment clock: one polygon mask per segment (dims = keyed mask levels), grainy grey body or red LED
    with glow and a red vignette; text changes are keyed per segment set."""
    fb = FB(ctx, L["id"])
    W, H = ctx.W, ctx.H
    a, b = int(L["start"]), int(L["end"])
    style = L.get("style", "grey")
    height = float(L.get("height", 300))
    wr = float(L.get("width_ratio", 0.56))
    th = 0.15 if style == "grey" else 0.13
    shape = "bevel" if style == "grey" else "rect"
    color = L.get("color", [0.74, 0.74, 0.74] if style == "grey" else [0.92, 0.05, 0.03])
    glow = float(L.get("glow", 0.0 if style == "grey" else 1.1))
    grain = float(L.get("grain", 0.22 if style == "grey" else 0.04))
    cx, cy = float(L.get("cx", W / 2)), float(L.get("cy", H / 2))
    texts = sorted([[int(t0), s] for t0, s in L["texts"]])
    dims = {int(k): v for k, v in L.get("dim", {}).items()}
    fo = {int(k): float(v) for k, v in L.get("flash_over", {}).items()}
    last = fb.bg(W, H, name="Transparent")
    vign = L.get("vignette")
    op = ctx.curve(L.get("opacity"), 1.0)
    if vign:                                               # compose.Renderer.vignette, added (alpha 0)
        cu = fb.add("Custom", "Vignette", Image1=Conn(fb.bg(W, H, name="VignetteBase")), NumberIn1=float(vign[0]),
                    NumberIn2=float(vign[1]), NumberIn3=float(vign[2]),
                    # Fusion's Custom tool has no pow(): it silently returns 0; '^' works
                    Intermediate1="max(0, 1 - sqrt(((x - 0.5) / 0.6) ^ 2 + ((y - 0.5) / 0.6) ^ 2)) ^ 1.5",
                    RedExpression="i1 * n1", GreenExpression="i1 * n2", BlueExpression="i1 * n3",
                    AlphaExpression="1")
        # alpha 0 AFTER the colour is computed (a Custom tool's alpha-0 output is premultiplied to black): the
        # vignette then adds onto whatever is below on the Edit page
        cu = fb.add("ChannelBoolean", "VignetteAdditive", Background=Conn(cu), ToAlpha=15)
        last = fb.add("Merge", "VignetteAdd", Background=Conn(last), Foreground=Conn(cu),
                      Blend=frames_spline(a, b, lambda f: op(f)))
    # segment masks per text span
    spans = [(t0, (texts[i + 1][0] - 1 if i + 1 < len(texts) else b), s) for i, (t0, s) in enumerate(texts)]
    m = None
    for si, (t0, t1, s) in enumerate(spans):
        items, Wm, Hm = G.seg_layout(s, height, shape, th, wr, 0.16)
        X0, Y0 = int(round(cx - Wm / 2)), int(round(cy - Hm / 2))
        for ci, seg, poly in items:
            def lev(f, ci=ci, seg=seg, t0=t0, t1=t1):
                if not (t0 <= f <= t1):
                    return 0.0
                for c2, s2, lv in dims.get(f, []):
                    if int(c2) == ci and s2 == seg:
                        return float(lv)
                return 1.0
            keys = sorted({(f, lev(f)) for f in range(a - 1, b + 2)})
            m = fb.polygon([(X0 + px, Y0 + py) for px, py in poly], W, H, name=f"T{si + 1}_{ci}{seg}", prev=m,
                           level=Spline(keys, step=True))
    # body colour: grainy grey (animated noise, mean 1) or flat LED red
    body = fb.bg(W, H, color, 1.0, name="Color")
    if grain > 0:
        sd = grain * 0.35                                  # N(1, grain) blurred with sigma 0.8 px
        nz = fb.add("FastNoise", "Grain", Width=W, Height=H, UseFrameFormatSettings=0, Detail=10.0, Contrast=1.0,
                    XScale=180.0, SeetheRate=0.5, Color1Red=1 - 2.2 * sd, Color1Green=1 - 2.2 * sd,
                    Color1Blue=1 - 2.2 * sd, Color1Alpha=1.0, Color2Red=1 + 2.2 * sd, Color2Green=1 + 2.2 * sd,
                    Color2Blue=1 + 2.2 * sd, Color2Alpha=1.0)
        body = fb.add("Merge", "GrainyColor", Background=Conn(body), Foreground=Conn(nz), ApplyMode=FuID("Multiply"))
    if fo:                                                 # over-exposed exit flash: segments turn white
        body = fb.add("Merge", "ExitFlash", Background=Conn(body), Foreground=Conn(fb.bg(W, H, (1, 1, 1), 1.0)),
                      Blend=Spline(sorted({(f, (1.0 if f in fo else 0.0)) for f in range(a - 1, b + 2)}), step=True))
    if glow > 0:
        white = fb.add("Merge", "SegMaskImg", Background=Conn(fb.bg(W, H)), Foreground=Conn(fb.bg(W, H, (1, 1, 1), 1.0)),
                       EffectMask=Conn(m, "Mask"))
        blur = fb.add("Blur", "GlowBlur", Input=Conn(white), XBlurSize=blur_size(height * 0.07), Filter=FuID("Gaussian"))
        last = fb.add("Merge", "Glow", Background=Conn(last), Foreground=Conn(fb.bg(W, H, color, 0.0, name="GlowColor")),
                      Blend=frames_spline(a, b, lambda f: glow * op(f)), EffectMask=Conn(blur, "Output"))
    last = fb.add("Merge", "Segments", Background=Conn(last), Foreground=Conn(body),
                  Blend=frames_spline(a, b, lambda f: op(f)), EffectMask=Conn(m, "Mask"))
    return fb.out(last)


def comp_solid(ctx: Ctx, L: dict) -> Comp:
    fb = FB(ctx, L["id"])
    W, H = ctx.W, ctx.H
    a, b = int(L["start"]), int(L["end"])
    x, y, w, h = [float(v) for v in L.get("rect", [0, 0, W, H])]
    col = np.asarray(L.get("color", [1, 1, 1]), float).reshape(-1)
    col = np.repeat(col, 3) if col.size == 1 else col
    frames = set(int(v) for v in L.get("frames", range(a, b + 1)))
    op = ctx.curve(L.get("opacity"), 1.0)
    if L.get("shape") == "circle":
        r = min(w, h) / 2
        # EllipseMask Width AND Height are fractions of the mask WIDTH (measured 2026-10-06: 2r / H drew the circle
        # W / H times too tall; RectangleMask Height is a fraction of the height)
        mask = fb.add("EllipseMask", "Circle", Center=norm_center(x, y, w, h, W, H), Width=2 * r / W,
                      Height=2 * r / W, MaskWidth=W, MaskHeight=H, UseFrameFormatSettings=0,
                      ClippingMode=FuID("None"))
        mask = fb.rect(x, y, w, h, W, H, name="Box", prev=mask)
        fb.c.tools[-1].inputs["PaintMode"] = FuID("Multiply")
    else:
        mask = fb.rect(x, y, w, h, W, H, name="Box")
    last = fb.add("Merge", "Solid", Background=Conn(fb.bg(W, H, name="Transparent")),
                  Foreground=Conn(fb.bg(W, H, tuple(col), 1.0, name="Color")),
                  Blend=frames_spline(a, b, lambda f: op(f) if f in frames else 0.0), EffectMask=Conn(mask, "Mask"))
    return fb.out(last)


def comp_streaks(ctx: Ctx, L: dict) -> Comp:
    """graphics.streaks for every frame (same random lines), glow, strength; composited with Screen."""
    fb = FB(ctx, L["id"])
    W, H = ctx.W, ctx.H
    a, b = int(L["start"]), int(L["end"])
    seed, strength = int(L.get("seed", 5)), float(L.get("strength", 0.6))
    op = ctx.curve(L.get("opacity"), 1.0)
    m = None
    for f in range(a, b + 1):
        rng = np.random.default_rng(seed + f)
        for i in range(5):
            y = rng.uniform(0.1, 0.9) * H
            slope = rng.uniform(-0.12, 0.12)
            x0, x1 = rng.uniform(-0.1, 0.5) * W, rng.uniform(0.5, 1.1) * W
            p0 = (int(x0), int(y))
            p1 = (int(x1), int(y + slope * (x1 - x0)))
            val = float(rng.uniform(0.4, 1.0))
            thick = max(1, int(rng.uniform(1, 3)))
            length = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
            ang = math.degrees(math.atan2(-(p1[1] - p0[1]), p1[0] - p0[0]))
            cxm, cym = (p0[0] + p1[0]) / 2 + 0.5, (p0[1] + p1[1]) / 2 + 0.5
            m = fb.rect(cxm - length / 2, cym - thick / 2, length, thick, W, H, name=f"F{f}_line{i + 1}", prev=m,
                        angle=ang, level=Spline([(f - 1, 0.0), (f, val), (f + 1, 0.0)], step=True))
            fb.c.tools[-1].inputs["PaintMode"] = FuID("Maximum")
    lines = fb.add("Merge", "Lines", Background=Conn(fb.bg(W, H, (0, 0, 0), 1.0, name="Black")),
                   Foreground=Conn(fb.bg(W, H, (1, 1, 1), 1.0, name="White")), EffectMask=Conn(m, "Mask"))
    blur = fb.add("Blur", "Glow", Input=Conn(lines), XBlurSize=blur_size(6.0), Filter=FuID("Gaussian"))
    summed = fb.add("Merge", "LinesPlusGlow", Background=Conn(lines), Foreground=Conn(blur),
                    ApplyMode=FuID("LinearDodge"), Blend=0.6)
    out = fb.add("ColorGain", "Strength", Input=Conn(summed), ClippingMode=FuID("Frame"),
                 GainRed=frames_spline(a, b, lambda f: strength * op(f)),
                 GainGreen=frames_spline(a, b, lambda f: strength * op(f)),
                 GainBlue=frames_spline(a, b, lambda f: strength * op(f)))
    out = fb.add("BrightnessContrast", "Clip01", Input=Conn(out), ClipBlack=1, ClipWhite=1)
    return fb.out(out)


def comp_overlay(ctx: Ctx, name: str, a: int, b: int, alpha_fn) -> Comp:
    """Background-coloured solid whose alpha follows a curve: a fade to / from the background."""
    fb = FB(ctx, name)
    W, H = ctx.W, ctx.H
    last = fb.add("Merge", "Fade", Background=Conn(fb.bg(W, H, name="Transparent")),
                  Foreground=Conn(fb.bg(W, H, (ctx.bg,) * 3, 1.0, name="BackgroundGrey")),
                  Blend=frames_spline(a, b, alpha_fn))
    return fb.out(last)


def comp_panels(ctx: Ctx, name: str, layers: list, dx_curve: str | None = None) -> Comp:
    """One Fusion comp for a set of panels; with dx_curve they sit on a wide board moved by ONE keyframed Transform
    (the measured pan, one key per frame)."""
    fb = FB(ctx, name)
    W, H = ctx.W, ctx.H
    BW = W
    if dx_curve:
        BW = max(W, int(math.ceil(max(float(L["rect"][0]) + float(L["rect"][2]) for L in layers))) + 2)
    last = fb.bg(BW, H, name="Board" if dx_curve else "Transparent")
    for L in layers:
        if L["type"] == "clip":
            last = panel(fb, L, last, BW, H)
        elif L["type"] == "strip":
            last = strip(fb, L, last, BW, H)
        else:
            raise ValueError(f"{L['id']}: {L['type']} cannot sit on a board")
    if dx_curve:
        cv = ctx.curve(dx_curve, 0.0)
        a = min(int(L["start"]) for L in layers)
        b = max(int(L["end"]) for L in layers)
        keys = [(f, 0.5 + cv(f) / BW, 0.5) for f in range(a, b + 1)]
        last = fb.add("Transform", "Pan", Input=Conn(last), Center=FPath(keys), FilterMethod=5)
        last = fb.add("Crop", "Screen", Input=Conn(last), XOffset=0, YOffset=0, XSize=W, YSize=H)
    return fb.out(last)


def still_image(fb: FB, path: Path, name: str) -> str:
    """A pre-rendered still image (16-bit TIFF in build\\resolve\\media\\stills) as a Loader held at frame 0 - two
    light nodes, no video decoding."""
    p = str(path)
    ld = fb.add("Loader", name, extra=(f"\t\t\tClips = {{ Clip {{ ID = \"Clip1\", Filename = {json.dumps(p)}, "
                                      f"FormatID = \"TiffFormat\", StartFrame = -1, Length = 1, "
                                      f"LengthSetManually = true, TrimIn = 0, TrimOut = 0, ExtendFirst = 0, "
                                      f"ExtendLast = 0, Loop = 1, AspectMode = 0, Depth = 0, TimeCode = 0, "
                                      f"GlobalStart = 0, GlobalEnd = 0, }}, }},\n"),
                HoldLastFrame=100000)
    return fb.add("TimeStretcher", f"{name}_frame0", Input=Conn(ld), SourceTime=0.0, InterpolateBetweenFrames=0)


def strip(fb: FB, L: dict, bg: str, CW: int, CH: int) -> str:
    """compose.StripLayer: a static row of photo tiles on a background-grey band. The band is a still image the lab
    renders from the same frames (exactly v1's pixels; building it live took 18 extra 4K decoders and ~100 nodes);
    on a board it moves with the board's pan."""
    ctx = fb.ctx
    sid = L["id"]
    x, y, w, h = [float(v) for v in L["rect"]]
    a, b = int(L["start"]), int(L["end"])
    op = ctx.curve(L.get("opacity"), 1.0)
    st = ctx.assets[sid]
    img = still_image(fb, st["path"], f"{sid}_image")
    return fb.add("Merge", sid, Background=Conn(bg), Foreground=Conn(img),
                  Center=norm_center(x, y, st["w"], st["h"], CW, CH), Blend=frames_spline(a, b, lambda f: op(f)))


def lab_assets(plan: dict, out_dir: Path, refresh: bool = False) -> dict:
    """Still images the lab renders for the two pre-rendered parts: the photo strips (compose.StripLayer.img) and
    the mosaic wall (compose.MosaicLayer level canvases: the same wall at sqrt(2)-spaced resolutions, as v1 used).
    16-bit TIFF, values = display RGB 0..1. Returns {layer id: info}. Made once: they are re-used while the layers,
    grades and levels that shape them are unchanged (stills.json holds a key), so a Resolve rebuild does not need
    the lab's frame cache; --refresh-stills forces a new render."""
    import hashlib
    from motionlab.compose import MosaicLayer, Renderer, StripLayer
    need = [L for L in plan["layers"] if L["type"] in ("strip", "mosaic")]
    if not need:
        return {}
    out_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(json.dumps({"layers": need, "grades": plan.get("grades", {}),
                                   "levels": plan.get("levels", "single"), "bg": plan.get("background", 0.045),
                                   "size": [plan["width"], plan["height"]],
                                   "sources": {k: [s["frames"], s["width"], s["height"]]
                                               for k, s in plan["sources"].items()}},
                                  sort_keys=True).encode()).hexdigest()
    index = out_dir / "stills.json"
    if not refresh and index.exists():
        old = json.loads(index.read_text(encoding="utf-8"))
        files = [Path(a["path"]) for a in old["assets"].values() if "path" in a] + \
                [Path(lv["path"]) for a in old["assets"].values() for lv in a.get("levels", {}).values()]
        if old.get("key") == key and all(p.exists() for p in files):
            assets = old["assets"]
            for a in assets.values():
                if "path" in a:
                    a["path"] = Path(a["path"])
                if "levels" in a:
                    a["levels"] = {int(k): dict(v, path=Path(v["path"]), origin=tuple(v["origin"]))
                                   for k, v in a["levels"].items()}
                    a["mc"] = tuple(a["mc"])
            log(f"lab stills: re-used {len(files)} image(s) (unchanged since {old.get('made', '?')})")
            return assets
    sub = dict(plan, layers=need)                      # build only those layers (Renderer reads the frame cache)
    R = Renderer(sub)
    assets = {}

    def write(p: Path, img: np.ndarray):
        import cv2
        a16 = (np.clip(img, 0, 1) * 65535 + 0.5).astype(np.uint16)
        cv2.imwrite(str(p), np.dstack([a16, a16, a16]))

    for lay in R.layers:
        if isinstance(lay, StripLayer):
            p = out_dir / f"{lay.id}.tif"
            write(p, lay.img)
            assets[lay.id] = {"path": p, "w": lay.img.shape[1], "h": lay.img.shape[0]}
        elif isinstance(lay, MosaicLayer):
            lv = {}
            for k, d in sorted(lay.levels.items()):
                p = out_dir / f"{lay.id}_level{k:02d}.tif"
                write(p, d["img"])
                lv[k] = {"path": p, "L": float(d["L"]), "origin": tuple(float(v) for v in d["origin"]),
                         "w": d["img"].shape[1], "h": d["img"].shape[0]}
            assets[lay.id] = {"levels": lv, "mc": tuple(float(v) for v in lay.mc)}
    log("lab stills: " + ", ".join(f"{k} ({len(v['levels']) if 'levels' in v else 1} image(s))"
                                   for k, v in assets.items()))

    def plain(v):
        if isinstance(v, Path):
            return str(v)
        if isinstance(v, dict):
            return {str(k): plain(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)):
            return [plain(x) for x in v]
        return v
    index.write_text(json.dumps({"key": key, "made": time.strftime("%Y-%m-%d %H:%M"), "assets": plain(assets)},
                                indent=1), encoding="utf-8")
    return assets


PART_PX_PER_VEL = 152.0
# firework look (tuned against graphics.firework on Resolve 21.1); variances are +- around the mean
# (rounds 1-3 against the lab at 5 moments of the burst: brightness, lit area, mean radius; rounds 4-5 added the
# radial profile, which showed a hollow ring: wider speed spread + more gravity, profile score 8.79 -> 6.79).
# Still different: the lab's sparks are thin comet trails with a bright head that keep spreading and sink in the
# last ~20 frames; these are short dashes in a band (a head would need a second emitter).
FIREWORK = {"number": 260, "life_mean": 0.775, "life_var": 0.225, "speed_mean": 0.72, "speed_var": 0.40,
            "line_size": 0.8, "line_size_to_velocity": 1.6, "spark_gain": 4.0, "drag_end": 0.85, "gravity": 3.0,
            "fade": "Gradient { Colors = { [0] = { 1, 1, 1, 1 }, [0.6] = { 0.7, 0.7, 0.7, 0.7 }, [1] = { 0, 0, 0, 0 } } }"}


def comp_firework(ctx: Ctx, L: dict) -> Comp:
    """graphics.firework as a Fusion particle burst: 260 sparks emitted on the first frame in all directions,
    drag (ease-out expansion), gravity, line sparks fading over their life, ignition flash, glow; on black,
    composited with Screen. Random like the lab's, so the sparks differ in detail but match size, timing,
    brightness and fall."""
    fb = FB(ctx, L["id"])
    W, H = ctx.W, ctx.H
    a, b = int(L["start"]), int(L["end"])
    S, life, seed = float(L.get("size", 520)), float(L.get("life", 45)), int(L.get("seed", 1))
    gain = float(L.get("gain", 1.0))
    cx, cy = (float(v) for v in L["center"])
    op = ctx.curve(L.get("opacity"), 1.0)
    T = FIREWORK
    de = T["drag_end"]                                  # drag: this share of the travel is done at the end of life
    k = 1.0 - (1.0 - de) ** (1.0 / life)
    # pRender 2D units: positions 1 = image width; velocity 1 = 152 px per frame, friction v *= 1 - k per frame
    # (both measured on Resolve 21.1). A spark of speed spd travels 0.47 * S * spd px by the end of its life.
    reach = 0.47 * S / PART_PX_PER_VEL / de
    em = fb.add("pEmitter", "Sparks", RandomSeed=seed,
                Number=Spline([(a - 1, 0.0), (a, float(T["number"])), (a + 1, 0.0)], step=True),
                Lifespan=T["life_mean"] * life, LifespanVariance=T["life_var"] * life,
                Velocity=T["speed_mean"] * reach * k, VelocityVariance=T["speed_var"] * reach * k,
                Angle=0.0, AngleVariance=360.0,
                Style=FuID("ParticleStyleLine"), RotationControls=1, RotationMode=1,     # lines along the motion
                **{"SphereRgn.Size": 0.002, "SphereRgn.Translate.X": (cx - W / 2) / W,
                   "SphereRgn.Translate.Y": -(cy - H / 2) / W, "ParticleStyle.Size": T["line_size"],
                   "ParticleStyle.SizeToVelocity": T["line_size_to_velocity"],
                   "ParticleStyle.ColorOverLife": Raw(T["fade"])})
    drag = fb.add("pFriction", "Drag", Input=Conn(em), VelocityFriction=k)
    grav = fb.add("pDirectionalForce", "Gravity", Input=Conn(drag),
                  Strength=T["gravity"] * 0.36 * S / life ** 2 / PART_PX_PER_VEL, Direction=-90.0)  # x: drag damps it
    # no pre-roll: the burst starts at the comp's frame 0 (pre-roll would simulate from the clip's global start)
    rnd = fb.add("pRender", "Render", Input=Conn(grav), OutputMode=FuID("TwoD"), Width=W, Height=H,
                 UseFrameFormatSettings=0, AutomaticPreRoll=0, PreRoll=0)
    black = fb.bg(W, H, (0, 0, 0), 1.0, name="Black")
    # 1-px particle lines -> ~2-3 px sparks like the lab: a slight blur, then gain back the brightness
    soft = fb.add("Blur", "SparkWidth", Input=Conn(rnd), XBlurSize=blur_size(0.8), Filter=FuID("Gaussian"))
    thick = fb.add("BrightnessContrast", "SparkGain", Input=Conn(soft), Gain=T["spark_gain"], Alpha=1,
                   ClipWhite=1)
    last = fb.add("Merge", "SparksOnBlack", Background=Conn(black), Foreground=Conn(thick), ApplyMode=FuID("Screen"))
    # ignition flash: a bright core growing from 0.0075 S to 0.0225 S radius over the first 12 % of the life
    n0 = max(1, int(round(0.12 * life)))
    core = fb.add("EllipseMask", "IgnitionCore", Center=(cx / W, 1 - cy / H),
                  Width=Spline([(a + i, (0.015 + 0.03 * i / n0) * S / W) for i in range(n0 + 1)]),
                  Height=Spline([(a + i, (0.015 + 0.03 * i / n0) * S / W) for i in range(n0 + 1)]),  # / W: see Circle
                  MaskWidth=W, MaskHeight=H, UseFrameFormatSettings=0, ClippingMode=FuID("None"))
    last = fb.add("Merge", "Ignition", Background=Conn(last), Foreground=Conn(fb.bg(W, H, (1, 1, 1), 1.0,
                  name="White")), EffectMask=Conn(core, "Mask"), ApplyMode=FuID("Screen"),
                  Blend=Spline([(a + i, min(1.0, 1.2 * (1 - i / n0) + 0.3)) for i in range(n0)] + [(a + n0, 0.0)],
                               step=True))
    glow = fb.add("Blur", "GlowBlur", Input=Conn(last), XBlurSize=blur_size(0.02 * S), Filter=FuID("Gaussian"))
    last = fb.add("Merge", "Glow", Background=Conn(last), Foreground=Conn(glow), ApplyMode=FuID("LinearDodge"),
                  Blend=0.8)
    g = frames_spline(a, b, lambda f: gain * op(f))
    last = fb.add("ColorGain", "Strength", Input=Conn(last), GainRed=g, GainGreen=g, GainBlue=g)
    last = fb.add("BrightnessContrast", "Clip01", Input=Conn(last), ClipBlack=1, ClipWhite=1)
    return fb.out(last)


def comp_mosaic(ctx: Ctx, L: dict) -> Comp:
    """compose.MosaicLayer: a wall of 75 photo tiles + one clock tile, seen through ONE native zoom control
    ('MosaicZoom': Size = the measured scale s(f), Center = the clock tile's screen position, one key per frame).
    The wall itself is the lab's set of level images (the same wall rendered at sqrt(2)-spaced resolutions - a
    31.6x zoom needs ~46,000 px of detail; building it live needed 75 4K decoders and ~500 nodes). Each frame shows
    the level the lab used, placed by expression from MosaicZoom; twinkles, red and black strobe frames are keyed."""
    fb = FB(ctx, L["id"])
    W, H = ctx.W, ctx.H
    a, b = int(L["start"]), int(L["end"])
    tiles = L["tiles"]
    tw, th, gap = float(L["tile_w"]), float(L["tile_h"]), float(L.get("gap", 4))
    bw, bh = tw - gap, th - gap
    S = ctx.curve(L["scale"], 1.0)
    sax, say = ctx.curve(L.get("screen_ax", W / 2)), ctx.curve(L.get("screen_ay", H / 2))
    asset = ctx.assets[L["id"]]
    mcx, mcy = asset["mc"]
    fb.add("Transform", "MosaicZoom", Size=Spline([(f, S(f)) for f in range(a, b + 1)]),
           Center=FPath([(f, sax(f) / W, 1 - say(f) / H) for f in range(a, b + 1)]))
    Zs, Cx, Cy = "MosaicZoom.Size", "MosaicZoom.Center.X", "MosaicZoom.Center.Y"

    def pt(mx, my):                                     # mosaic px -> expression of the screen point
        return Expr(f"Point({Cx} + {Zs} * {(mx - mcx) / W:.9f}, {Cy} - {Zs} * {(my - mcy) / H:.9f})")

    def level_of(s):                                    # compose.MosaicLayer._level_of
        return max(0, int(math.ceil(math.log(max(s, 1e-6), math.sqrt(2)) - 1e-9)))

    last = fb.bg(W, H, (ctx.bg,) * 3, 1.0, name="Canvas")
    for k, lv in sorted(asset["levels"].items()):
        used = [f for f in range(a, b + 1) if level_of(S(f)) == k]
        if not used:
            continue
        x0, y0 = lv["origin"]
        Lk = lv["L"]
        img = still_image(fb, lv["path"], f"Wall_level{k:02d}")
        # level image pixel u -> mosaic x0 + u / L; its centre lands at s * (x0 + w / 2L - mc) from the anchor
        last = fb.add("Merge", f"Level{k:02d}", Background=Conn(last), Foreground=Conn(img),
                      Size=Expr(f"{Zs} / {Lk:.9f}"),
                      Center=pt(x0 + lv["w"] / (2 * Lk), y0 + lv["h"] / (2 * Lk)), FilterMethod=2,
                      Blend=Spline(sorted({(f, (1.0 if f in used else 0.0)) for f in range(a - 1, b + 2)}),
                                   step=True))

    def box_mask(t, name):
        return fb.add("RectangleMask", name, Center=pt(t["x"] + bw / 2, t["y"] + bh / 2),
                      Width=Expr(f"{Zs} * {bw / W:.9f}"), Height=Expr(f"{Zs} * {bh / H:.9f}"), MaskWidth=W,
                      MaskHeight=H, UseFrameFormatSettings=0, ClippingMode=FuID("None"))

    # twinkles: one tile flashes white (0.8) for one frame
    tw_ = {int(k): int(v) for k, v in L.get("twinkle", {}).items()}
    for f, ti in sorted(tw_.items()):
        last = fb.add("Merge", f"Twinkle{f}", Background=Conn(last), Foreground=Conn(fb.bg(W, H, (1, 1, 1), 1.0,
                      name=f"Twinkle{f}_white")), EffectMask=Conn(box_mask(tiles[ti], f"Twinkle{f}_box"), "Mask"),
                      Blend=Spline([(f - 1, 0.0), (f, 0.8), (f + 1, 0.0)], step=True))
    red = set(int(v) for v in L.get("red", []))
    blk = set(int(v) for v in L.get("black", []))
    if red:
        def rk(gv):
            return Spline(sorted({(f, (gv if f in red else 1.0)) for f in range(a - 1, b + 2)}), step=True)
        last = fb.add("ColorGain", "RedStrobe", Input=Conn(last), GainRed=rk(1.15), GainGreen=rk(0.16),
                      GainBlue=rk(0.13))
    if blk:
        last = fb.add("Merge", "BlackFrames", Background=Conn(last), Foreground=Conn(fb.bg(W, H, (ctx.bg,) * 3, 1.0,
                      name="BlackFrames_grey")),
                      Blend=Spline(sorted({(f, (1.0 if f in blk else 0.0)) for f in range(a - 1, b + 2)}), step=True))
    op = ctx.curve(L.get("opacity"), 1.0)
    last = fb.add("Merge", "MosaicOut", Background=Conn(fb.bg(W, H, name="Transparent")), Foreground=Conn(last),
                  Blend=frames_spline(a, b, lambda f: op(f)))
    return fb.out(last)


# ================================================================================================= plan -> units
def clip_is_static(L: dict) -> bool:
    an = L.get("anchor", [0.5, 0.5])
    return (L["type"] == "clip" and not L.get("dx") and not L.get("opacity") and not L.get("mirror")
            and not L.get("tint") and L.get("blend", "normal") == "normal" and not L.get("black")
            and not isinstance(an[0], dict) and not isinstance(an[1], dict)
            and not isinstance(L.get("zoom", 1.0), (dict, str)) and not isinstance(L.get("gain", 1.0), (dict, str))
            and (float(L.get("speed", 1.0)) == 1.0 or L.get("hold")))


def clip_pieces(L: dict, ctx: Ctx) -> list:
    """Edit-page pieces of a static clip layer: cuts at jumps and at flash frames (1-frame pieces with a flash LUT);
    holds become freeze frames."""
    a, b = int(L["start"]), int(L["end"])
    hold = bool(L.get("hold", False))
    jumps = sorted([[int(j), int(i)] for j, i in L.get("jumps", [[a, L.get("in", 0)]])])
    fo = {int(k): float(v) for k, v in L.get("flash_over", {}).items()}
    fw = set(int(v) for v in L.get("flash_white", []))
    gain = float(L.get("gain", 1.0))
    grade = L.get("grade", "default")
    an = L.get("anchor", [0.5, 0.5])
    props = edit_page_props([float(v) for v in L["rect"]], float(L.get("zoom", 1.0)), float(an[0]), float(an[1]),
                            ctx.W, ctx.H)

    def src_frame(f):
        j = jumps[0]
        for jj in jumps:
            if jj[0] <= f:
                j = jj
        return ctx.dji(j[1] if hold else j[1] + (f - j[0]))

    cuts = sorted({a, b + 1} | {j for j, _ in jumps if a < j <= b} | {f for f in fo if a <= f <= b}
                  | {f + 1 for f in fo if a <= f <= b} | {f for f in fw if a <= f <= b}
                  | {f + 1 for f in fw if a <= f <= b})
    out = []
    for p0, p1 in zip(cuts, cuts[1:]):
        p1 -= 1
        flash = p0 == p1 and (p0 in fo or p0 in fw)
        lut = ctx.luts.get(grade, gain, fo.get(p0, 0.0) if flash else 0.0, flash and p0 in fw)
        label = L["id"] + (f" flash f{p0}" if flash else "")
        out.append(Piece(p0, p1, L["src"], int(src_frame(p0)), hold and p1 > p0, lut, props, label))
    return out


def make_units(plan: dict, ctx: Ctx, sections: set) -> list:
    units: list[Unit] = []
    layers = plan["layers"]
    boards: dict[str, list] = {}
    for i, L in enumerate(layers):
        if L.get("dx") and isinstance(L["dx"], str):
            boards.setdefault(L["dx"], []).append((i, L))
    used = set()
    for name, members in boards.items():
        idx = [i for i, _ in members]
        ls = [L for _, L in members]
        a, b = min(int(L["start"]) for L in ls), max(int(L["end"]) for L in ls)
        nm = f"board_{name.lstrip('@')}"
        units.append(Unit(nm, min(idx), a, b, "comp", builder=(comp_panels, (nm, ls, name)), color="Orange",
                          note=f"{len(ls)} layers on one board; one Transform keyed per frame from {name}"))
        used |= set(idx)

    def comp_unit(L, i, fn, args, note, color="Purple", composite="normal"):
        units.append(Unit(L["id"], i, int(L["start"]), int(L["end"]), "comp", builder=(fn, args), color=color,
                          composite=composite, note=note))

    for i, L in enumerate(layers):
        if i in used:
            continue
        a, b, t = int(L["start"]), int(L["end"]), L["type"]
        if t == "clip" and clip_is_static(L):
            units.append(Unit(L["id"], i, a, b, "clip", pieces=clip_pieces(L, ctx)))
        elif t == "clip" and L.get("opacity") and clip_is_static({**L, "opacity": None}) and fade_ok(plan, i):
            # opacity curve over the background only: native clip + a background-grey fade overlay above it
            units.append(Unit(L["id"], i, a, b, "clip", pieces=clip_pieces(L, ctx)))
            op = ctx.curve(L["opacity"], 1.0)
            units.append(Unit(f"{L['id']}_fade", i + 0.5, a, b, "comp", color="Yellow",
                              builder=(comp_overlay, (f"{L['id']}_fade", a, b,
                                                      lambda f, op=op: 1.0 - min(1.0, op(f)))),
                              note="background-grey overlay, alpha = 1 - opacity curve (one key per frame)"))
        elif t == "clip":
            comp_unit(L, i, comp_panels, (L["id"], [L]), "animated panel (Fusion)", "Orange")
        elif t == "text":
            comp_unit(L, i, comp_text, (L,), "pixel-font title (Fusion rectangles + glow)")
        elif t == "clock":
            comp_unit(L, i, comp_clock, (L,), "seven-segment clock (Fusion polygons)")
        elif t == "solid":
            comp_unit(L, i, comp_solid, (L,), "solid / flash frame (Fusion)", "Yellow")
        elif t == "streaks":
            comp_unit(L, i, comp_streaks, (L,), "light streaks (Fusion), composite mode Screen", composite="screen")
        elif t == "firework":
            comp_unit(L, i, by_type, (t, L), "firework (Fusion particles), composite mode Screen",
                      composite="screen")
        else:
            comp_unit(L, i, by_type, (t, L), f"{t} (Fusion)")
    mg = plan.get("master_gain")
    if mg:
        cv = ctx.curve(mg, 1.0)
        a = int(mg["start"]) if isinstance(mg, dict) and "start" in mg else 0
        fr = [f for f in range(a, a + len(mg.get("values", []))) if cv(f) < 0.999]
        if fr:
            units.append(Unit("master_fade", len(layers) + 1, min(fr), max(fr), "comp", color="Yellow",
                              builder=(comp_overlay, ("master_fade", min(fr), max(fr), lambda f: 1.0 - cv(f))),
                              note="fade to the background grey, alpha = 1 - master gain (one key per frame)"))
    if plan.get("grain"):
        units.append(Unit("grain", len(layers) + 2, 0, int(plan["frames"]) - 1, "comp", color="Beige",
                          builder=(comp_grain, (float(plan["grain"]),)), composite="linear_light",
                          note=f"luma grain (sigma {plan['grain']} at half resolution), composite Linear Light"))
    units.sort(key=lambda u: u.order)
    if sections:
        units = [u for u in units if section_of(u.a) in sections]
    return units


def fade_ok(plan: dict, i: int) -> bool:
    """True if nothing but the background is below layer i while it is visible."""
    L = plan["layers"][i]
    a, b = int(L["start"]), int(L["end"])
    return not any(int(o["start"]) <= b and int(o["end"]) >= a for o in plan["layers"][:i])


def assign_tracks(units: list) -> int:
    """Draw order = plan order: a unit goes one track above every earlier unit it overlaps in time (V1 = bg)."""
    placed = []
    for u in units:
        below = [p.track for p in placed if p.a <= u.b and p.b >= u.a]
        u.track = (max(below) + 1) if below else 2
        placed.append(u)
    return max([u.track for u in units] + [1])


def comp_grain(ctx: Ctx, sigma: float) -> Comp:
    """compose.Renderer grain: zero-mean luma noise added to the final image (sigma at half resolution, bilinear
    upscaled = 0.625 x sigma per pixel). Resolve clips negative values of an added layer, so the grain is an opaque
    mid-grey layer 0.5 + n/2 composited with Linear Light (base + 2 * layer - 1 = base + n). Fusion Film Grain at
    size 1.0 has the lab grain's pixel correlation; std = 0.4005 x strength, no mean bias (measured in float32 on
    Resolve 21.1; the earlier "bias" was the 8-bit rounding of a Default-depth mid grey, see GEN_DEPTH)."""
    fb = FB(ctx, "grain")
    W, H = ctx.W, ctx.H
    strength = 0.5 * sigma * 0.625 / 0.4005
    mid = fb.bg(W, H, (0.5, 0.5, 0.5), 1.0, name="MidGrey")       # float32 (FB.add): exactly 0.5, no bias
    g = fb.add("FilmGrain", "Grain", Input=Conn(mid), Monochrome=1, LogProcessing=0, MasterStrength=strength,
               MasterXSize=1.0, MasterYSize=1.0, MasterRoughness=0.0, MasterOffset=0.0, Complexity=2)
    return fb.out(g)
BUILDERS = {}          # layer types built in later sections (firework, mosaic) register here


BUILDERS.update(firework=comp_firework, mosaic=comp_mosaic)


def by_type(ctx: Ctx, t: str, L: dict) -> Comp:
    if t not in BUILDERS:
        raise NotImplementedError(f"{L['id']}: no Resolve builder for layer type '{t}' yet")
    return BUILDERS[t](ctx, L)


# ================================================================================================= Resolve
def connect(timeout: float = 120.0):
    os.environ.setdefault("RESOLVE_SCRIPT_API", str(RESOLVE_API))
    os.environ.setdefault("RESOLVE_SCRIPT_LIB", str(RESOLVE_LIB))
    sys.path.append(str(RESOLVE_API / "Modules"))
    import DaVinciResolveScript as dvr  # noqa: E402
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = dvr.scriptapp("Resolve")
        if r:
            return r
        time.sleep(2)
    raise SystemExit("cannot connect to DaVinci Resolve: is Resolve Studio running with external scripting = Local?")


def make_carrier(path: Path, frames: int, W: int, H: int, fps: float, grey: float):
    """A grey ProRes 422 HQ clip (video levels, Y = 64 + 876 * grey, rounded): the background and the carrier of
    every Fusion comp (its frame f sits at timeline frame f, so comp frame = timeline frame)."""
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    yv = int(round(64 + 876 * grey))
    raw = path.with_suffix(".yuv")
    frame = np.concatenate([np.full(W * H, yv, np.uint16), np.full(W * H // 2, 512, np.uint16),     # 4:2:2
                            np.full(W * H // 2, 512, np.uint16)])
    raw.write_bytes(frame.astype("<u2").tobytes())
    cmd = [tool("ffmpeg"), "-v", "error", "-y", "-stream_loop", str(frames - 1), "-f", "rawvideo", "-pix_fmt",
           "yuv422p10le", "-s", f"{W}x{H}", "-r", f"{fps:g}", "-i", str(raw), "-frames:v", str(frames), "-c:v",
           "prores_ks", "-profile:v", "3", "-vendor", "apl0", "-color_primaries", "bt709", "-color_trc", "bt709",
           "-colorspace", "bt709", "-color_range", "tv", str(path)]
    subprocess.run(cmd, check=True)
    raw.unlink()
    log(f"carrier clip {path.name}: {frames} frames, grey {grey} (Y10 {yv})")


class Session:
    def __init__(self, r, plan: dict, plan_path: Path, project: str, timeline: str):
        self.r = r
        self.plan = plan
        self.build = plan_path.parent
        self.rdir = self.build / "resolve"
        self.pname = project
        self.tname = timeline
        self.pm = r.GetProjectManager()
        self.p = None
        self.mp = None
        self.tl = None
        self.pool: dict[str, object] = {}

    # ------------------------------------------------------------------------------------------ project
    def open_project(self):
        cur = self.pm.GetCurrentProject()
        if cur and cur.GetName() == self.pname:
            self.p = cur
        elif self.pname in self.pm.GetProjectListInCurrentFolder():
            self.p = self.pm.LoadProject(self.pname)
        else:
            self.p = self.pm.CreateProject(self.pname)
            if not self.p:
                raise SystemExit(f"cannot create project {self.pname}")
            # one key per call: a combined settings call froze Resolve 21.1 once
            ok = all(self.p.SetSettings({k: v}) for k, v in (
                ("timelineResolutionWidth", str(self.plan["width"])),
                ("timelineResolutionHeight", str(self.plan["height"])),
                ("timelineFrameRate", f"{float(self.plan['fps']):g}")))
            log(f"created project {self.pname} ({'settings ok' if ok else 'SETTINGS FAILED'})")
        beat("project settings")
        s = self.p.GetSettings()
        if (s.get("timelineResolutionWidth") != str(self.plan["width"]) or
                float(s.get("timelineFrameRate")) != float(self.plan["fps"])):
            raise SystemExit(f"project {self.pname} is {s.get('timelineResolutionWidth')}x"
                             f"{s.get('timelineResolutionHeight')} @ {s.get('timelineFrameRate')}: expected the plan's")
        for k, v in (("timelineInputResMismatchBehavior", "scaleToCrop"), ("imageRetimeInterpolation", "nearest")):
            self.p.SetSettings({k: v})
        self.mp = self.p.GetMediaPool()

    def folder(self, name: str):
        root = self.mp.GetRootFolder()
        for f in root.GetSubFolderList():
            if f.GetName() == name:
                return f
        return self.mp.AddSubFolder(root, name)

    def media(self, path: Path, folder: str):
        """Media pool item for a file (imported once, read-only)."""
        key = str(Path(path).resolve()).lower()
        if key in self.pool:
            return self.pool[key]
        fo = self.folder(folder)
        for c in fo.GetClipList():
            if str(c.GetClipProperty("File Path")).lower() == key:
                self.pool[key] = c
                return c
        self.mp.SetCurrentFolder(fo)
        items = self.mp.ImportMedia([str(path)])
        if not items:
            raise SystemExit(f"Resolve could not import {path}")
        self.pool[key] = items[0]
        return items[0]

    # ------------------------------------------------------------------------------------------ timeline
    def new_timeline(self, replace: bool, delete_old: bool = False):
        """--replace keeps the old timeline (renamed '<name> (replaced <date time>)'), so changes made by hand in
        Resolve are never lost; --delete-old deletes it instead."""
        for i in range(1, self.p.GetTimelineCount() + 1):
            t = self.p.GetTimelineByIndex(i)
            if t and t.GetName() == self.tname:
                if not replace:
                    raise SystemExit(f"timeline {self.tname} exists: use --replace to rebuild it (the old one is "
                                     f"kept, renamed) or --replace --delete-old")
                if delete_old:
                    if not self.mp.DeleteTimelines([t]):
                        raise SystemExit(f"cannot delete timeline {self.tname}")
                    log(f"deleted the old timeline {self.tname}")
                else:
                    old = f"{self.tname} (replaced {time.strftime('%Y-%m-%d %H-%M-%S')})"
                    if not t.SetName(old):
                        raise SystemExit(f"cannot rename the old timeline {self.tname}")
                    log(f"kept the old timeline as '{old}'")
                break
        self.mp.SetCurrentFolder(self.mp.GetRootFolder())
        self.tl = self.mp.CreateEmptyTimeline(self.tname)
        if not self.tl:
            raise SystemExit(f"cannot create timeline {self.tname}")
        self.p.SetCurrentTimeline(self.tl)
        if not self.tl.SetStartTimecode("00:00:00:00"):
            log("WARNING: start timecode stays 01:00:00:00 - add one hour to every timecode")

    def timeline(self):
        for i in range(1, self.p.GetTimelineCount() + 1):
            t = self.p.GetTimelineByIndex(i)
            if t and t.GetName() == self.tname:
                self.tl = t
                self.p.SetCurrentTimeline(t)
                return t
        raise SystemExit(f"timeline {self.tname} not found")

    def append(self, item, start: int, end_excl: int, track: int, record: int, media_type: int = 1):
        beat(f"placing a clip at f{record} on track {track}")
        res = self.mp.AppendToTimeline([{"mediaPoolItem": item, "startFrame": start, "endFrame": end_excl,
                                         "trackIndex": track, "recordFrame": record, "mediaType": media_type}])
        if not res:
            raise RuntimeError(f"AppendToTimeline failed: track {track} record {record} src {start}-{end_excl}")
        return res[0]

    def items(self):
        """Every video item of the timeline as (track, item)."""
        for t in range(1, self.tl.GetTrackCount("video") + 1):
            for it in self.tl.GetItemListInTrack("video", t) or []:
                yield t, it

    def find(self, name: str, start: int | None = None):
        for t, it in self.items():
            if it.GetName() == name and (start is None or int(it.GetStart()) == start):
                return t, it
        return None, None

    def save(self):
        self.pm.SaveProject()

    # ------------------------------------------------------------------------------------------ render
    def render(self, a: int, b: int, out: Path, audio: bool = True, timeout: float = 6 * 3600,
               stall: float = 900.0) -> Path:
        out = out.resolve()
        if self.build not in out.parents:
            raise PermissionError(f"refusing to render outside {self.build}: {out}")
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            out.unlink()
        self.p.SetCurrentTimeline(self.tl)
        self.p.SetCurrentRenderMode(1)
        if not self.p.SetCurrentRenderFormatAndCodec("mp4", "H264"):
            raise RuntimeError("cannot select MP4 / H.264")
        need = {"MarkIn": a, "MarkOut": b, "TargetDir": str(out.parent), "CustomName": out.stem,
                "ExportVideo": True, "ExportAudio": audio, "FormatWidth": int(self.plan["width"]),
                "FormatHeight": int(self.plan["height"]), "FrameRate": float(self.plan["fps"])}
        if audio:
            need.update({"AudioCodec": "aac", "AudioSampleRate": 48000})
        for k, v in need.items():          # one by one: Resolve rejects a whole dict if any key fails
            if not self.p.SetRenderSettings({k: v}):
                raise RuntimeError(f"render setting refused: {k} = {v!r}")
        # optional (Resolve 21.1 refuses VideoQuality for MP4 / H.264; the encoder then uses its own default)
        for k, v in (("EncodingProfile", "High"), ("VideoQuality", "Best")):
            self.p.SetRenderSettings({k: v})
        # leftover jobs of this timeline (from a crashed or cancelled run) clutter the queue: drop them
        for j in self.p.GetRenderJobList() or []:
            if j.get("TimelineName") == self.tname:
                self.p.DeleteRenderJob(j.get("JobId"))
        jid = self.p.AddRenderJob()
        t0 = time.time()
        self.p.StartRendering([jid], False)
        last = -1
        moved = (time.time(), -1)                      # (time the percentage last changed, percentage)
        while True:
            beat(f"rendering f{a}-{b}")
            # while Resolve renders, its scripting objects can drop out (a method turns into None): re-fetch the
            # project and retry instead of exiting - an exiting client makes Resolve abort the render
            try:
                st = self.p.GetRenderJobStatus(jid) or {}
                busy = self.p.IsRenderingInProgress()
            except (TypeError, AttributeError):
                time.sleep(5)
                try:
                    self.r = connect(60)
                    self.pm = self.r.GetProjectManager()
                    self.p = self.pm.GetCurrentProject()
                except SystemExit:
                    pass
                continue
            pc = int(st.get("CompletionPercentage", 0))
            if pc >= last + 10:
                log(f"  render {pc}%")
                last = pc
            if pc != moved[1]:
                moved = (time.time(), pc)
            if not busy and st.get("JobStatus") != "Rendering":
                break
            if time.time() - moved[0] > stall:
                # a frame that never finishes (seen: many requests to one long-GOP HEVC MediaIn) - stop, don't wait
                self.p.StopRendering()
                raise RuntimeError(f"render stalled at {pc}% for {stall:.0f}s (f{a}-{b}): a Fusion comp in that "
                                   f"range is too slow - check its node count / MediaIns")
            if time.time() - t0 > timeout:
                self.p.StopRendering()
                raise RuntimeError("render timeout")
            time.sleep(2)
        st = self.p.GetRenderJobStatus(jid)
        self.p.DeleteRenderJob(jid)
        if st.get("JobStatus") != "Complete":
            raise RuntimeError(f"render failed: {st}")
        if not out.exists():
            cand = sorted(out.parent.glob(out.stem + "*"), key=lambda p: p.stat().st_mtime)
            if not cand:
                raise RuntimeError(f"render output not found: {out}")
            cand[-1].rename(out)
        log(f"rendered f{a}-{b} ({tc(a)}-{tc(b)}) -> {out} in {time.time() - t0:.0f}s")
        return out


# ================================================================================================= build
def comp_sha1(p: Path) -> str:
    return hashlib.sha1(Path(p).read_bytes()).hexdigest()


def import_comp(it, u: Unit):
    """Load a unit's comp into its carrier item and name it after the unit (what the Fusion page shows)."""
    beat(f"importing the Fusion comp {u.name}")
    if not it.ImportFusionComp(str(u.comp_path)):
        raise RuntimeError(f"{u.name}: Fusion comp import failed ({u.comp_path})")
    names = it.GetFusionCompNameList() or []
    if names and names[-1] != u.name:
        it.RenameFusionCompByName(names[-1], u.name)


def write_comp(u: Unit):
    """comps\\<unit>.comp = the latest version; comps\\imported\\<sha1>.comp = every version ever imported (a
    timeline's manifest records the sha1 it holds, so --diff compares each timeline with what it really got)."""
    u.comp_path.parent.mkdir(parents=True, exist_ok=True)
    u.comp_path.write_text(u.comp.text(), encoding="utf-8")
    keep = u.comp_path.parent / "imported" / f"{comp_sha1(u.comp_path)}.comp"
    if not keep.exists():
        keep.parent.mkdir(exist_ok=True)
        shutil.copy2(u.comp_path, keep)


def imported_text(rdir: Path, unit: str, sha: str | None) -> tuple[str | None, str]:
    """The comp text a timeline imported for a unit: by the sha1 its manifest records, else (older manifests, or a
    timeline duplicated in Resolve) the latest comps\\<unit>.comp."""
    if sha:
        p = rdir / "comps" / "imported" / f"{sha}.comp"
        if p.exists():
            return p.read_text(encoding="utf-8"), "as imported"
    p = rdir / "comps" / f"{unit}.comp"
    return (p.read_text(encoding="utf-8"), "latest comp file") if p.exists() else (None, "missing")


def manifest_sha(rdir: Path, timeline: str) -> dict:
    mp = rdir / f"{timeline}_build.json"
    if not mp.exists():
        return {}
    return {u["name"]: u.get("comp_sha1") for u in json.loads(mp.read_text(encoding="utf-8"))["units"]}


def update_comps(sess: Session, units: list, only: set, overwrite_edits: bool = False):
    """--only: replace the Fusion comps of the named units in the existing timeline (fast iteration on one effect;
    Edit-page clips and track layout stay as they are). A comp that was changed by hand in Resolve (compared with
    the comp file imported last time) is only replaced with --overwrite-edits, after saving it to
    build\\resolve\\edits\\<date time>\\<unit>.comp."""
    sess.timeline()
    edits = {}
    shas = manifest_sha(sess.rdir, sess.tname)
    for u in units:
        if u.name in only and u.kind == "comp":
            text, base = imported_text(sess.rdir, u.name, shas.get(u.name))
            t, it = sess.find(u.name, u.a)
            if text and it and it.GetFusionCompCount():
                if base != "as imported":
                    log(f"  {u.name}: no import record for timeline {sess.tname} - comparing with the {base}")
                d = comp_drift(it.GetFusionCompByIndex(1), parse_comp(text))
                if d:
                    edits[u.name] = (it, d)
    if edits:
        for name, (_, d) in edits.items():
            log(f"  {name} was changed in Resolve: " + "; ".join(f"{w} {lab} -> {live}" for w, lab, live in d[:6])
                + (" ..." if len(d) > 6 else ""))
        if not overwrite_edits:
            raise SystemExit("not replacing comps edited by hand: add --overwrite-edits to replace them (the edited "
                             "comps are saved first), or rebuild with --replace (keeps the old timeline)")
        keep = sess.rdir / "edits" / time.strftime("%Y-%m-%d_%H-%M-%S")
        keep.mkdir(parents=True, exist_ok=True)
        for name, (it, _) in edits.items():
            if not it.ExportFusionComp(str(keep / f"{name}.comp"), 1):
                raise SystemExit(f"{name}: could not save the edited comp to {keep} - nothing replaced")
            log(f"  saved the edited comp {name} -> {keep / (name + '.comp')}")
    done = []
    for u in units:
        if u.name not in only:
            continue
        if u.kind != "comp":
            log(f"  {u.name}: an Edit-page clip unit - use a full rebuild (--replace) for it")
            continue
        t, it = sess.find(u.name, u.a)
        if not it:
            raise SystemExit(f"{u.name}: no item named so at f{u.a} ({tc(u.a)}) - run a full --replace")
        write_comp(u)
        for nm in list(it.GetFusionCompNameList() or []):
            it.DeleteFusionCompByName(nm)
        import_comp(it, u)
        done.append(u.name)
        log(f"  V{t} {u.name}: comp replaced (f{u.a}-{u.b}, {tc(u.a)}-{tc(u.b)})")
    missing = only - set(done) - {u.name for u in units if u.kind == "clip"}
    if missing:
        raise SystemExit(f"unknown unit(s): {', '.join(sorted(missing))}")
    sess.save()
    mp = sess.rdir / f"{sess.tname}_build.json"
    if mp.exists():                                    # the manifest records what is imported now
        man = json.loads(mp.read_text(encoding="utf-8"))
        for mu in man["units"]:
            u = next((x for x in units if x.name == mu["name"] and x.name in done), None)
            if u:
                mu.update(composite=u.composite, comp_sha1=comp_sha1(u.comp_path))
        mp.write_text(json.dumps(man, indent=1), encoding="utf-8")


def build(sess: Session, plan: dict, plan_path: Path, sections: set, replace: bool, delete_old: bool = False,
          only: set | None = None, refresh_stills: bool = False, overwrite_edits: bool = False):
    build_dir = plan_path.parent
    rdir = build_dir / "resolve"
    W, H, fps, N = int(plan["width"]), int(plan["height"]), float(plan["fps"]), int(plan["frames"])
    luts = Luts(plan.get("grades", {}), rdir / "luts", f"MotionLab/{sess.pname}",
                double_levels=plan.get("levels", "single") == "double")
    ctx = Ctx(plan, luts)
    # ------------------------------------------------------------------ media (originals, read-only)
    carrier = rdir / "media" / f"carrier_bg_{W}x{H}_{fps:g}fps.mov"
    make_carrier(carrier, N + 10, W, H, fps, ctx.bg)
    sess.open_project()
    for sid, s in sorted(plan["sources"].items()):
        it = sess.media(Path(s["source"]), "Footage")
        pr = it.GetClipProperty()
        w, h = (int(v) for v in pr["Resolution"].split("x"))
        ctx.media[sid] = {"path": str(Path(s["source"])), "id": it.GetMediaId(), "name": it.GetName(),
                          "frames": int(pr["Frames"]), "width": w, "height": h, "fps": float(pr["FPS"]), "item": it}
        if abs(w / h - SRC_W / SRC_H) > 1e-3:
            raise SystemExit(f"{sid}: {w}x{h} is not 4:3 - the geometry here assumes the 4:3 DJI clips")
    ref = sess.media(Path(plan["audio"]["path"]), "Reference") if plan.get("audio", {}).get("path") else None
    car = sess.media(carrier, "Carriers")
    # ------------------------------------------------------------------ units, LUTs, comps
    units = make_units(plan, ctx, sections)
    if any(L["type"] in ("strip", "mosaic") and (not sections or section_of(int(L["start"])) in sections)
           for L in plan["layers"]):
        ctx.assets = lab_assets(plan, rdir / "media" / "stills", refresh_stills)
    for u in units:
        if only and u.name not in only:
            continue
        beat(f"building the comp {u.name}")
        if u.kind == "comp":
            fn, args = u.builder
            u.comp = fn(ctx, *args)
            u.comp.render_range = (u.a, u.b)
            u.comp.t0 = u.a                # the comp's frame 0 = the carrier clip's first frame = timeline frame u.a
            u.comp_path = rdir / "comps" / f"{u.name}.comp"
            if not only:                   # --only writes them after checking the live comps for manual edits
                write_comp(u)
    luts.install()
    sess.p.RefreshLUTList()
    if only:
        update_comps(sess, units, only, overwrite_edits)
        return
    ntr = assign_tracks(units)
    log(f"{len(units)} units on {ntr} video tracks; {len(luts.made)} LUTs; "
        f"{sum(len(u.pieces) for u in units if u.kind == 'clip')} Edit-page clips, "
        f"{sum(1 for u in units if u.kind == 'comp')} Fusion comps")
    # ------------------------------------------------------------------ timeline
    names = [sess.p.GetTimelineByIndex(i).GetName() for i in range(1, sess.p.GetTimelineCount() + 1)]
    if replace and sess.tname in names and (rdir / f"{sess.tname}_build.json").exists():
        keep = rdir / "edits" / time.strftime("%Y-%m-%d_%H-%M-%S")
        rep = drift(sess, plan_path, export_dir=keep)
        if rep["findings"]:
            print_drift(rep)
            if delete_old and not overwrite_edits:
                raise SystemExit("the old timeline has changes made by hand: drop --delete-old (it is then kept, "
                                 "renamed) or add --overwrite-edits")
            keep.mkdir(parents=True, exist_ok=True)
            (keep / "drift.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
            log(f"  the changes made by hand are listed in {keep / 'drift.json'}")
    sess.new_timeline(replace, delete_old)
    tl = sess.tl
    while tl.GetTrackCount("video") < ntr:
        tl.AddTrack("video")
    tl.SetTrackName("video", 1, "Background")
    bg = sess.append(car, 0, N, 1, 0)
    bg.SetName("background 0.045")
    if ref:
        a1 = sess.append(ref, 0, N, 1, 0, media_type=2)
        log(f"A1: reference audio f0-{N - 1}")
    for k, (a, b, what) in SECTIONS.items():
        if not sections or k in sections:
            tl.AddMarker(a, "Blue", k, f"{what}: f{a}-{b} ({frame_to_tc(a, fps)}-{frame_to_tc(b, fps)})", 1)
    for u in units:
        if u.kind == "clip":
            for pc in u.pieces:
                n = pc.b - pc.a + 1
                srcitem = ctx.media[pc.src]["item"]
                it = sess.append(srcitem, pc.frame, pc.frame + 2 * n, u.track, pc.a)
                if it.GetStart() != pc.a or it.GetDuration() != n:
                    raise RuntimeError(f"{pc.label}: placed at {it.GetStart()}+{it.GetDuration()}, wanted {pc.a}+{n}")
                if pc.hold:
                    # Speed 0 freezes the first frame when the playhead is BEFORE the clip (after it: the last
                    # frame; inside it: Resolve splits the clip at the playhead) - measured on Resolve 21.1
                    if pc.a < 1 or not tl.SetCurrentTimecode(frame_to_tc(pc.a - 1, fps)):
                        raise RuntimeError(f"{pc.label}: cannot park the playhead before the hold")
                    if not it.SetSpeed({"Percentage": 0.0}):
                        raise RuntimeError(f"{pc.label}: freeze frame failed")
                    if (it.GetSourceStartFrame() != pc.frame or it.GetStart() != pc.a
                            or it.GetDuration() != n):
                        raise RuntimeError(f"{pc.label}: froze source {it.GetSourceStartFrame()} at "
                                           f"{it.GetStart()}+{it.GetDuration()}, wanted {pc.frame} at {pc.a}+{n}")
                if not it.SetProperties(pc.props):
                    raise RuntimeError(f"{pc.label}: transform refused {pc.props}")
                if not it.GetNodeGraph().SetLUT(1, luts.resolve_path(pc.lut)):
                    raise RuntimeError(f"{pc.label}: LUT {pc.lut} not found by Resolve")
                it.SetName(pc.label)
                if pc.label != u.name:
                    it.SetClipColor("Yellow")
        else:
            it = sess.append(car, u.a, u.b + 1, u.track, u.a)
            if it.GetStart() != u.a or it.GetDuration() != u.b - u.a + 1:
                raise RuntimeError(f"{u.name}: carrier placed at {it.GetStart()}+{it.GetDuration()}")
            import_comp(it, u)
            it.SetName(u.name)
            modes = {"screen": sess.r.COMPOSITE_SCREEN, "linear_light": sess.r.COMPOSITE_LINEAR_LIGHT}
            if u.composite in modes and not it.SetProperties({"CompositeMode": modes[u.composite]}):
                raise RuntimeError(f"{u.name}: composite mode {u.composite} refused")
            if u.color:
                it.SetClipColor(u.color)
        log(f"  V{u.track:<2} {u.kind:4s} f{u.a}-{u.b} ({frame_to_tc(u.a, fps)}-{frame_to_tc(u.b, fps)}) {u.name}"
            + (f" [{len(u.pieces)} clips]" if u.kind == "clip" else f" [{u.note}]"))
    for t in range(2, ntr + 1):
        tl.SetTrackName("video", t, f"Layer {t}")
    sess.save()
    manifest = {"project": sess.pname, "timeline": sess.tname, "plan": str(plan_path), "tracks": ntr,
                "units": [{"name": u.name, "kind": u.kind, "track": u.track, "start": u.a, "end": u.b,
                           "start_tc": frame_to_tc(u.a, fps), "end_tc": frame_to_tc(u.b, fps), "note": u.note,
                           **({"composite": u.composite, "comp_sha1": comp_sha1(u.comp_path)}
                              if u.kind == "comp" else {}),
                           "clips": [{"start": p.a, "end": p.b, "src": p.src, "dji_frame": p.frame, "hold": p.hold,
                                      "lut": p.lut, "transform": {k: round(v, 4) for k, v in p.props.items()}}
                                     for p in u.pieces]} for u in units],
                "luts": sorted(luts.made), "lut_folder": str(luts.rdir)}
    (rdir / f"{sess.tname}_build.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    log(f"saved project {sess.pname}, timeline {sess.tname}")


def doctor(sess: Session, plan: dict, plan_path: Path) -> int:
    """--doctor: check everything the Resolve project depends on and that the timeline still matches the build
    manifest (items, LUTs, comps). Read-only. Exit code 0 = all good."""
    rows = []

    def chk(name, ok, detail=""):
        rows.append((name, ok if ok is None else bool(ok), str(detail)))      # None = a note, not a problem
        beat(f"doctor: {name}")

    r = sess.r
    chk("Resolve Studio + scripting", r.IsStudio(), f"{r.GetProductName()} {r.GetVersionString()}")
    chk("Resolve responding", resolve_state() == "running", resolve_state())
    rdir = plan_path.parent / "resolve"
    for sid, s in sorted(plan["sources"].items()):
        p = Path(s["source"])
        chk(f"source {sid} on disk", p.exists(), p.name)
    names = sess.pm.GetProjectListInCurrentFolder() or []
    if sess.pname not in names:
        chk(f"project {sess.pname}", False, "not in the current project folder - run a build")
    else:
        sess.open_project()
        s = sess.p.GetSettings()
        chk(f"project {sess.pname} format", s.get("timelineResolutionWidth") == str(plan["width"]) and
            float(s.get("timelineFrameRate")) == float(plan["fps"]),
            f"{s.get('timelineResolutionWidth')}x{s.get('timelineResolutionHeight')} @ {s.get('timelineFrameRate')}")
        for fo in sess.mp.GetRootFolder().GetSubFolderList() or []:
            for c in fo.GetClipList() or []:
                fp = c.GetClipProperty("File Path")
                if fp:
                    chk(f"media online: {c.GetName()}", Path(fp).exists(), fo.GetName())
        try:
            sess.timeline()
        except SystemExit:
            chk(f"timeline {sess.tname}", False, "missing - run a build")
        else:
            tl = sess.tl
            chk(f"timeline {sess.tname}", tl.GetStartFrame() == 0,
                f"start {tl.GetStartTimecode()}, f0-{tl.GetEndFrame() - 1}, {tl.GetTrackCount('video')} video tracks")
            mp = rdir / f"{sess.tname}_build.json"
            if not mp.exists():
                chk("build manifest", False, f"{mp.name} missing")
            else:
                man = json.loads(mp.read_text(encoding="utf-8"))
                lut_dir = Path(man["lut_folder"])
                miss = [k for k in man["luts"] if not (lut_dir / f"{k}.cube").exists()]
                chk(f"{len(man['luts'])} grade LUTs in Resolve's LUT folder", not miss, ", ".join(miss) or lut_dir)
                at = {(t, int(it.GetStart())): it for t, it in sess.items()}
                bad = []
                for u in man["units"]:
                    if u["kind"] == "comp":
                        it = at.get((u["track"], u["start"]))
                        if not it or it.GetName() != u["name"] or (it.GetFusionCompCount() or 0) < 1:
                            bad.append(f"{u['name']} (f{u['start']} {u['start_tc']})")
                        if not (rdir / "comps" / f"{u['name']}.comp").exists():
                            bad.append(f"{u['name']}.comp file")
                    else:
                        for c in u["clips"]:
                            it = at.get((u["track"], c["start"]))
                            lut = it.GetNodeGraph().GetLUT(1) if it else ""
                            if not it or int(it.GetDuration()) != c["end"] - c["start"] + 1 or \
                                    not str(lut).replace("\\", "/").endswith(f"{c['lut']}.cube"):
                                bad.append(f"{u['name']} clip f{c['start']} ({tc(c['start'])})")
                chk(f"{len(man['units'])} units placed as built (items, durations, LUTs, comps)", not bad,
                    "; ".join(bad[:6]) + (" ..." if len(bad) > 6 else "") if bad else "all match")
                rep = drift(sess, plan_path)
                units = sorted({x["unit"] for x in rep["findings"]})
                chk("changes made by hand since the build", None if units else True,
                    f"{len(rep['findings'])} in {', '.join(units[:8])} (kept; --diff lists them)" if units else "none")
        stale = [j for j in (sess.p.GetRenderJobList() or []) if j.get("TimelineName") == sess.tname]
        chk("render queue", not stale, f"{len(stale)} leftover job(s) of this timeline" if stale else "clean")
    free = shutil.disk_usage(str(plan_path.anchor)).free / 1e9
    chk(f"free disk space on {plan_path.anchor}", free > 20, f"{free:.0f} GB")
    w = max(len(n) for n, _, _ in rows)
    for n, ok, d in rows:
        print(f"  {'NOTE' if ok is None else 'OK  ' if ok else 'BAD '}  {n:<{w}}  {d}")
    nbad = sum(ok is False for _, ok, _ in rows)
    nnote = sum(ok is None for _, ok, _ in rows)
    print(f"doctor: {len(rows) - nbad - nnote} OK, {nnote} NOTE, {nbad} BAD")
    return 0 if nbad == 0 else 1


# ================================================================================================= drift
# What changed in Resolve since the lab built the timeline (edits made by hand on the Edit / Color / Fusion pages).
# The lab's record = the build manifest + the .comp files it imported. Read-only; a rebuild (--replace) keeps the old
# timeline, --only refuses to replace an edited comp unless --overwrite-edits (and saves the edited comp first).
def _close(a, b, tol: float = 1e-5) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))
    except (TypeError, ValueError):
        return False


def _fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:.6g}"
    if isinstance(v, (tuple, list)):
        return "(" + ", ".join(_fmt(x) for x in v) + ")"
    return str(v)


# inputs Resolve rewrites when it turns the imported Loader into a MediaIn (not edits)
DRIFT_IGNORE = {"Loader": {"MediaSource", "Layer", "AudioTrack", "GlobalOut", "ClipTimeEnd", "HoldLastFrame"},
                "Saver": {"Index"}}
# modifiers Fusion creates by itself (keyed inputs, particle over-life curves, Custom tool LUT inputs); a key added
# by hand still shows up as a changed input value
DRIFT_AUTO_TOOLS = {"BezierSpline", "XYPath", "PolyPath", "LUTBezier"}


def comp_drift(comp, spec) -> list:
    """Differences between a live Fusion comp and the comp text the lab imported, as (what, lab, live). Static
    inputs are compared at the comp's first, middle and last frame (catches keys added by hand), keyed inputs at
    every key, connections and expressions as text; tools added or deleted by hand are listed."""
    out = []
    live = {t.GetAttrs()["TOOLS_Name"]: t for t in (comp.GetToolList(False) or {}).values()}
    a, b = spec.render_range or (0, 0)
    times = sorted({a, (a + b) // 2, b})
    for name, (kind, inputs) in spec.tools.items():
        tool = live.get(name)
        if tool is None:
            out.append((name, kind, "deleted"))
            continue
        objs = None
        for key, (form, v) in inputs.items():
            if key in DRIFT_IGNORE.get(kind, ()):
                continue
            what = f"{name}.{key}"
            if form == "num":
                for t in times:
                    lv = tool.GetInput(key, t)
                    if not _close(lv, v):
                        out.append((what, _fmt(v), _fmt(lv) + (f" at comp frame {t}" if len(times) > 1 else "")))
                        break
            elif form == "point":
                for t in times:
                    lv = tool.GetInput(key, t)
                    p = (lv.get(1), lv.get(2)) if isinstance(lv, dict) else (lv, None)
                    if not (_close(p[0], v[0]) and _close(p[1], v[1])):
                        out.append((what, _fmt(v), _fmt(p)))
                        break
            elif form in ("fuid", "str"):
                lv = tool.GetInput(key)
                if str(lv) != v and not _close(lv, v):
                    out.append((what, v, _fmt(lv)))
            elif form == "anim":
                # every frame of the comp (the lab's keys are exact on integer frames; a key added by hand between
                # two of them changes the frames around it), at most 2000 evenly spaced frames
                ts = range(a, b + 1) if b - a < 2000 else np.linspace(a, b, 2000).round().astype(int)
                if v in spec.splines:
                    sk = spec.splines[v]
                    exp = [(int(t), spline_at(sk, t)) for t in ts]
                    get = lambda t: tool.GetInput(key, t)                       # noqa: E731
                    ok = lambda lv, val: _close(lv, val)                         # noqa: E731
                else:
                    xs, ys = (spec.splines.get(n, []) for n in spec.paths.get(v, ("", "")))
                    if not xs or not ys:
                        continue
                    exp = [(int(t), (spline_at(xs, t), spline_at(ys, t))) for t in ts]

                    def get(t):
                        lv = tool.GetInput(key, t)
                        return (lv.get(1), lv.get(2)) if isinstance(lv, dict) else (lv, None)

                    def ok(lv, val):
                        return _close(lv[0], val[0]) and _close(lv[1], val[1])
                bad = []
                for t, val in exp:
                    lv = get(t)
                    if not ok(lv, val):
                        bad.append((t, val, lv))
                if bad:
                    t, val, lv = bad[0]
                    out.append((what, f"{_fmt(val)} at comp frame {t}",
                                f"{_fmt(lv)} ({len(bad)} of {len(exp)} frames differ)"))
            elif form in ("conn", "expr"):
                if objs is None:
                    objs = {i.GetAttrs()["INPS_ID"]: i for i in (tool.GetInputList() or {}).values()}
                inp = objs.get(key)
                if form == "conn":
                    o = inp.GetConnectedOutput() if inp else None
                    src = o.GetTool().GetAttrs()["TOOLS_Name"] if o else None
                    if src != v[0]:
                        out.append((what, f"<- {v[0]}", f"<- {src}" if src else "disconnected"))
                else:
                    e = (inp.GetExpression() if inp else None) or ""
                    if e != v:
                        out.append((what, f"= {v}", f"= {e}" if e else "no expression"))
    known = set(spec.tools) | set(spec.splines) | set(spec.paths)
    for name, t in live.items():
        if name not in known and t.GetAttrs()["TOOLS_RegID"] not in DRIFT_AUTO_TOOLS:
            out.append((name, "-", f"added ({t.GetAttrs()['TOOLS_RegID']})"))
    return out


def drift(sess: Session, plan_path: Path, export_dir: Path | None = None, units: set | None = None) -> dict:
    """Compare the live timeline with the build manifest and the comp files. Returns {"findings": [...], ...};
    each finding = {unit, track, start, end, what, lab, live}. With export_dir, the live comps of edited units are
    exported there (TimelineItem.ExportFusionComp) so hand-made changes are kept as text."""
    rdir = plan_path.parent / "resolve"
    man = json.loads((rdir / f"{sess.tname}_build.json").read_text(encoding="utf-8"))
    sess.timeline()
    tl = sess.tl
    at = {}
    for t, it in sess.items():
        at[(t, int(it.GetStart()))] = it
    found, seen, edited, src_fps = [], set(), {}, {}

    def add(u, a, b, track, what, lab, live):
        found.append({"unit": u, "track": track, "start": a, "end": b, "start_tc": tc(a),
                      "end_tc": tc(b), "what": what, "lab": lab, "live": live})

    def item_checks(u, it, track, a, b, composite=None):
        if int(it.GetDuration()) != b - a + 1:
            add(u, a, b, track, "duration", b - a + 1, int(it.GetDuration()))
        if not it.GetClipEnabled():
            add(u, a, b, track, "clip enabled", True, False)
        op = it.GetProperty("Opacity")
        if op is not None and not _close(op, 100.0):
            add(u, a, b, track, "opacity", 100, _fmt(float(op)))
        if composite is not None and it.GetProperty("CompositeMode") != composite:
            add(u, a, b, track, "composite mode", composite, it.GetProperty("CompositeMode"))

    modes = {"normal": 0, "screen": sess.r.COMPOSITE_SCREEN, "linear_light": sess.r.COMPOSITE_LINEAR_LIGHT}
    for u in man["units"]:
        if units and u["name"] not in units:
            continue
        beat(f"drift: {u['name']}")
        if u["kind"] == "comp":
            a, b, track = u["start"], u["end"], u["track"]
            it = at.get((track, a))
            seen.add((track, a))
            if not it or it.GetName() != u["name"]:
                hit = [(t, s) for (t, s), i in at.items() if i.GetName() == u["name"]]
                add(u["name"], a, b, track, "item", f"V{track} f{a}",
                    f"moved to V{hit[0][0]} f{hit[0][1]} ({tc(hit[0][1])})" if hit else "missing")
                if not hit:
                    continue
                track, a = hit[0]
                seen.add(hit[0])
                it = at[hit[0]]
            item_checks(u["name"], it, track, a, b, modes.get(u.get("composite")) if "composite" in u else None)
            names = it.GetFusionCompNameList() or []
            if len(names) != 1:
                add(u["name"], a, b, track, "Fusion comps on the item", 1, f"{len(names)}: {', '.join(names)}")
            text, base = imported_text(rdir, u["name"], u.get("comp_sha1"))
            if not text or not names:
                continue
            if u.get("comp_sha1") and base != "as imported":
                add(u["name"], a, b, track, "comp text", "as imported", f"not kept - compared with the {base}")
            comp = it.GetFusionCompByIndex(1)
            diffs = comp_drift(comp, parse_comp(text)) if comp else [("comp", "-", "unreadable")]
            for what, lab, live in diffs:
                add(u["name"], a, b, track, what, lab, live)
            if diffs:
                edited[u["name"]] = it
        else:
            for c in u["clips"]:
                a, b, track = c["start"], c["end"], u["track"]
                it = at.get((track, a))
                seen.add((track, a))
                if not it:
                    add(u["name"], a, b, track, "clip", f"V{track} f{a}", "missing (moved or deleted)")
                    continue
                item_checks(u["name"], it, track, a, b, 0)
                # in-point in source frames: GetSourceStartFrame floors start time x fps and reads one frame low on
                # some clips (seen on 21.1); GetLeftOffset (timeline frames) is exact - but meaningless on a freeze
                mpi = it.GetMediaPoolItem()
                k = mpi.GetMediaId() if mpi else ""
                if k not in src_fps:
                    src_fps[k] = float(mpi.GetClipProperty("FPS") or 0) if mpi else 0.0
                if c["hold"] or not src_fps[k]:
                    inp, tol = float(it.GetSourceStartFrame()), 1.0
                else:
                    inp, tol = float(it.GetLeftOffset()) * src_fps[k] / TC_FPS, 0.01
                if abs(inp - c["dji_frame"]) > tol:
                    add(u["name"], a, b, track, "source in-point (DJI frame)", c["dji_frame"], _fmt(inp))
                for k, v in c["transform"].items():
                    lv = it.GetProperty(k)
                    if not _close(lv, v, 1e-3):
                        add(u["name"], a, b, track, f"Edit page {k}", _fmt(float(v)), _fmt(lv))
                ng = it.GetNodeGraph()
                lut = str(ng.GetLUT(1) or "").replace("\\", "/")
                if not lut.endswith(f"{c['lut']}.cube"):
                    add(u["name"], a, b, track, "Color page LUT (node 1)", f"{c['lut']}.cube", lut or "none")
                if (ng.GetNumNodes() or 1) > 1:
                    add(u["name"], a, b, track, "Color page nodes", 1, f"{ng.GetNumNodes()} (grade added by hand)")
    if not units:
        for (t, s), it in sorted(at.items()):
            if (t, s) in seen or (t == 1 and s == 0 and it.GetName().startswith("background")):
                continue
            e = int(it.GetEnd()) - 1
            add(it.GetName(), s, e, t, "item", "-", "added by hand")
        if tl.GetTrackCount("video") != man["tracks"]:
            add("timeline", 0, 0, 0, "video tracks", man["tracks"], tl.GetTrackCount("video"))
    rep = {"project": sess.pname, "timeline": sess.tname, "checked": time.strftime("%Y-%m-%d %H:%M:%S"),
           "findings": found, "exported": {}}
    if export_dir and edited:
        export_dir.mkdir(parents=True, exist_ok=True)
        for name, it in edited.items():
            p = export_dir / f"{name}.comp"
            if it.ExportFusionComp(str(p), 1):
                rep["exported"][name] = str(p)
    return rep


def print_drift(rep: dict) -> None:
    f = rep["findings"]
    if not f:
        print(f"no manual changes: timeline {rep['timeline']} matches the lab's build")
        return
    by = {}
    for x in f:
        by.setdefault((x["unit"], x["track"], x["start"], x["end"]), []).append(x)
    print(f"{len(f)} change(s) in {len(by)} item(s) of {rep['timeline']} since the lab built it:")
    for (u, t, a, b), xs in by.items():
        print(f"  {u}  V{t}  f{a}-{b} ({tc(a)}-{tc(b)})")
        for x in xs[:12]:
            print(f"      {x['what']}: lab {x['lab']} -> now {x['live']}")
        if len(xs) > 12:
            print(f"      ... {len(xs) - 12} more")
    for u, p in rep.get("exported", {}).items():
        print(f"  saved the edited comp {u} -> {p}")


def save_drift(rep: dict, rdir: Path) -> Path:
    p = rdir / "checks" / f"{rep['timeline']}_drift.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    return p


def main() -> int:
    global WD
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--project", default=None, help="Resolve project (default: the plan's project folder name)")
    ap.add_argument("--timeline", default=None, help="timeline name (default: <project>_resolve_vN)")
    ap.add_argument("--sections", default="", help="comma list of S1..S7 (default: all)")
    ap.add_argument("--replace", action="store_true",
                    help="rebuild an existing timeline (the old one is kept, renamed '... (replaced <date>)')")
    ap.add_argument("--delete-old", action="store_true", help="with --replace: delete the old timeline instead")
    ap.add_argument("--only", default="", help="comma list of unit names: re-import just their Fusion comps")
    ap.add_argument("--refresh-stills", action="store_true", help="re-render the lab stills (strips, mosaic wall)")
    ap.add_argument("--doctor", action="store_true", help="check Resolve, media, LUTs and the timeline; change nothing")
    ap.add_argument("--diff", action="store_true",
                    help="list what was changed by hand in Resolve since the build (edited comps are saved as text)")
    ap.add_argument("--overwrite-edits", action="store_true",
                    help="with --only / --replace --delete-old: replace comps or a timeline changed by hand (saved "
                         "first to build\\resolve\\edits\\)")
    ap.add_argument("--no-build", action="store_true")
    ap.add_argument("--render", nargs=2, type=int, metavar=("A", "B"))
    ap.add_argument("--render-full", action="store_true")
    ap.add_argument("--no-audio", action="store_true")
    a = ap.parse_args()
    plan_path = Path(a.plan).resolve()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    global TC_FPS
    TC_FPS = float(plan["fps"])
    project = a.project or plan_path.parent.parent.name
    ver = plan.get("name", "v1").rsplit("_", 1)[-1]
    tname = a.timeline or f"{project}_resolve_{ver}"
    sections = {s.strip().upper() for s in a.sections.split(",") if s.strip()}
    only = {s.strip() for s in a.only.split(",") if s.strip()}
    WD = Watchdog()
    sess = Session(connect(), plan, plan_path, project, tname)
    if a.doctor:
        return doctor(sess, plan, plan_path)
    if a.diff:
        sess.open_project()
        live = plan_path.parent / "resolve" / "edits" / "live"        # the edited comps as they are now
        for old in live.glob("*.comp"):
            old.unlink()
        rep = drift(sess, plan_path, export_dir=live)
        print_drift(rep)
        log(f"report: {save_drift(rep, plan_path.parent / 'resolve')}")
        return 1 if rep["findings"] else 0
    if only:
        build(sess, plan, plan_path, sections, False, only=only, refresh_stills=a.refresh_stills,
              overwrite_edits=a.overwrite_edits)
    elif not a.no_build:
        build(sess, plan, plan_path, sections, a.replace, a.delete_old, refresh_stills=a.refresh_stills,
              overwrite_edits=a.overwrite_edits)
    else:
        sess.open_project()
        sess.timeline()
    if a.render:
        r0, r1 = a.render
        sess.render(r0, r1, plan_path.parent / "resolve" / f"{tname}_{r0}-{r1}.mp4", audio=not a.no_audio)
    if a.render_full:
        sess.render(0, int(plan["frames"]) - 1, plan_path.parent / f"{tname}.mp4", audio=not a.no_audio)
    return 0


if __name__ == "__main__":
    sys.exit(main())
