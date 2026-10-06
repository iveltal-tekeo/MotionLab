"""MotionLab effect library: every approved effect as a DaVinci Resolve Fusion macro (.setting) + a recipe (.md).

    .venv\\Scripts\\python tools\\library.py build                 write library\\<effect>\\<effect>.setting + .md
    .venv\\Scripts\\python tools\\library.py test [effect ...]     render each macro in a throwaway Resolve project
                                                                 (motionlab_scratch) -> library\\<effect>\\check.png
    .venv\\Scripts\\python tools\\library.py title "MY TEXT"       a pixel-font title macro for any text
    .venv\\Scripts\\python tools\\library.py install [effect ...]  copy the macros into DaVinci Resolve (Fusion
                                                                 Templates\\Edit\\Titles|Effects\\MotionLab, Macros\\
                                                                 MotionLab), names "ML ...", thumbnails; record in
                                                                 library\\installed.json; then restart Resolve
    .venv\\Scripts\\python tools\\library.py uninstall             remove exactly what install copied
    .venv\\Scripts\\python tools\\library.py verify-install        insert each installed title by name in a
                                                                 throwaway Resolve project and render it

Macros: "effect" = goes on a clip (input MainInput1), "title" = makes its own picture (Edit page titles /
generators). Graphics are drawn on a fixed 1920x1080 canvas and placed at native size, so they never stretch on
timelines of another aspect (4AM: 1520x1080); Position / Size move them. Everything starts at the clip's first
frame. Lean on purpose (Resolve crashed on heavy Fusion work): 4-45 tools each, no MediaIn, no Loader.
Values come from the 4AM analysis (reviews corrected by the user's feedback, lessons L001-L006) and the test_4am
Resolve rebuild (verified 1.83/255 against the lab render).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import graphics as G  # noqa: E402
from motionlab.fusion import Comp, Conn, Expr, FuID, Raw, Spline  # noqa: E402
from motionlab.signals import iter_frames  # noqa: E402
from motionlab.timecode import frame_to_tc  # noqa: E402
from motionlab.util import LAB, setup_console  # noqa: E402
from resolve_build import FIREWORK, PART_PX_PER_VEL, blur_size, text_strokes  # noqa: E402  (verified in Resolve)

LIB = LAB / "library"
REF = LAB / "analysis" / "NEMZZZ_-_4AM_OFFICIAL_VIDEO_VLDJ_-wrwj8"
REF_NAME = "NEMZZZ - 4AM (official video), 25 fps"
CW, CH = 1920, 1080                 # graphics canvas
FPS = 25.0
DEPTH = 4                           # float32 for every generator (Resolve renders 'Default' in 8-bit after an import)


def tc(f: int) -> str:
    return frame_to_tc(int(f), FPS)


def ftc(a: int, b: int | None = None) -> str:
    return f"f{a} ({tc(a)})" if b is None or b == a else f"f{a}-{b} ({tc(a)} - {tc(b)})"


class Fx:
    """One library effect: a comp of tools + what the macro exposes."""

    def __init__(self, slug: str, name: str, kind: str):
        self.slug, self.name, self.kind = slug, name, kind
        self.c = Comp(fps=FPS, width=CW, height=CH)
        self.inputs: list = []            # (id, tool, input, label, extra)
        self.tail: list = []              # Position / Size / Opacity: listed after the effect's own controls
        self.first = None                 # tool that takes MainInput1 (effects)
        self.first_input = "Input"
        self.last = None

    def add(self, kind, name, **ins) -> str:
        if kind in ("Background", "RectangleMask", "PolylineMask", "EllipseMask", "FastNoise", "pRender"):
            ins.setdefault("Depth", DEPTH)
        return self.c.add(kind, name, **ins)

    def expose(self, iid, tool, inp, label=None, **extra):
        self.inputs.append((iid, tool, inp, label, extra or None))

    def bg(self, name, rgb=(0, 0, 0), alpha=0.0, frame=False, w=CW, h=CH) -> str:
        ins = dict(TopLeftRed=rgb[0], TopLeftGreen=rgb[1], TopLeftBlue=rgb[2], TopLeftAlpha=alpha)
        if frame:
            ins["UseFrameFormatSettings"] = 1
        else:
            ins.update(Width=w, Height=h, UseFrameFormatSettings=0)
        return self.add("Background", name, **ins)

    def place(self, canvas: str, additive: bool = False) -> str:
        """Put a 1920x1080 graphic on a frame-sized transparent background (native size, no stretch); exposes
        Position / Size / Opacity. additive: alpha 0 afterwards, so on the Edit page it adds light onto the
        clips below (no composite mode needed)."""
        frame = self.bg("Frame", frame=True)
        m = self.add("Merge", "Place", Background=Conn(frame), Foreground=Conn(canvas), Center=(0.5, 0.5), Size=1.0)
        self.tail += [("Position", "Place", "Center", "Position", None),
                      ("Size", "Place", "Size", "Size", {"MinScale": 0.1, "MaxScale": 4.0, "Default": 1.0}),
                      ("Opacity", "Place", "Blend", "Opacity", {"Default": 1.0})]
        if additive:
            m = self.add("ChannelBoolean", "Additive", Background=Conn(m), ToAlpha=15)
        return m

    @property
    def macro_name(self) -> str:
        return f"ML_{self.name.replace(' ', '')}"

    def exposed(self, main: bool = True) -> list:
        """The macro's inputs in Inspector order (MainInput1 first for effects)."""
        ins = list(self.inputs) + list(self.tail)
        if main and self.kind == "effect":
            ins.insert(0, ("MainInput1", self.first, self.first_input, None, None))
        return ins

    def setting(self) -> str:
        return self.c.setting_text(self.macro_name, self.exposed(), [("MainOutput1", self.last, "Output")],
                                   help_text=f"MotionLab library: {self.slug}.md")


# ================================================================================================= effects
def fx_exposure_flash() -> Fx:
    """L001: flashes are over-exposed pictures that keep their texture (56-81 %), or flat light grey at the video's
    brightest level (85-89 %) - never a 100 % white solid unless the video really has one."""
    fx = Fx("exposure-flash", "Exposure Flash", "effect")
    # measured on 4AM (frame before -> flash frame, lit area): out = v + k (1 - v) fits every flash - E034 k 0.58,
    # E039 0.65, E016 0.79, E011 0.83 - the lift of Brightness/Contrast (gain first, then lift); gain > 1 adds an
    # exposure push on top (clips the highlights)
    e = fx.add("BrightnessContrast", "Expo", Gain=Expr("1 + (Expo.FlashGain - 1) * Expo.Amount"),
               Lift=Expr("Expo.FlashLift * Expo.Amount"))
    fx.c.control("Expo", "Amount", "Amount (key 0 -> 1 -> 0)", 1.0, 0, 1)
    fx.c.control("Expo", "FlashGain", "Exposure push (gain, 1 = none)", 1.0, 1, 6)
    fx.c.control("Expo", "FlashLift", "Flash strength (4AM 0.58-0.83)", 0.62, 0, 1)
    fx.c.control("Expo", "Softness", "Softness (blur px)", 2.0, 0, 30)
    fx.c.control("Expo", "Flat", "Flat (0 = keeps texture, 1 = solid)", 0.0, 0, 1)
    fx.c.control("Expo", "Level", "Flat level (4AM: 0.88)", 0.88, 0, 1)
    fx.first, fx.first_input = e, "Input"
    soft = fx.add("Blur", "Soft", Input=Conn(e), XBlurSize=Expr("Expo.Softness * Expo.Amount"),
                  Filter=FuID("Gaussian"))
    flat = fx.bg("FlatGrey", frame=True)
    for ch in ("TopLeftRed", "TopLeftGreen", "TopLeftBlue"):
        fx.c.tools[-1].inputs[ch] = Expr("Expo.Level")
    fx.c.tools[-1].inputs["TopLeftAlpha"] = 1.0
    fx.last = fx.add("Merge", "FlatMix", Background=Conn(soft), Foreground=Conn(flat),
                     Blend=Expr("Expo.Flat * Expo.Amount"))
    for cid, label in (("Amount", "Amount (key 0 -> 1 -> 0)"), ("FlashLift", "Flash strength"),
                       ("FlashGain", "Exposure push"), ("Softness", "Softness (blur px)"),
                       ("Flat", "Flat (0 = texture, 1 = solid)"), ("Level", "Flat level")):
        fx.expose(cid, "Expo", cid, label)
    return fx


SEG_ON = {s: {d for d, segs in G.SEGMENTS.items() if d.isdigit() and s in segs} for s in "abcdefg"}


CLOCK_H = 300.0                     # clock digit height on the canvas; Size = wanted height / 300
# measured on 4AM (full-size frames, tools\library.py test): segment thickness / digit width / spacing as a share of
# the digit height, colour, glow (amplitude, sigma in px at the 4AM size)
CLOCKS = {"grey": dict(th=0.117, wr=0.71, sp=0.117, color=(0.63, 0.63, 0.63), grain=0.22, glow=0.0, sigma=21.0,
                       vignette=0.0, digits=(10, 3, 5, 9), round_colon=True),       # f3200: 514 px digits
          "led": dict(th=0.155, wr=0.66, sp=0.184, color=(0.652, 0.012, 0.018), grain=0.03, glow=1.05,
                      sigma=30.0 * CLOCK_H / 336, vignette=1.0, digits=(0, 4, 0, 0), round_colon=False)}  # f3560


def led_layout(text: str, h: float, th: float, wr: float, sp: float) -> tuple:
    """4AM's red LED digits: plain rectangles, verticals continuous over the full height (the '0' is a closed
    rectangle ring, measured at f3560); same (char index, segment, polygon) items as graphics.seg_layout."""
    w, t, pad = wr * h, th * h, 0.08 * h
    rects = {"a": (0, 0, w, t), "d": (0, h - t, w, t), "g": (0, h / 2 - t / 2, w, t),
             "f": (0, 0, t, h / 2 + t / 2), "e": (0, h / 2 - t / 2, t, h / 2 + t / 2),
             "b": (w - t, 0, t, h / 2 + t / 2), "c": (w - t, h / 2 - t / 2, t, h / 2 + t / 2)}
    items, x = [], pad
    for ci, ch in enumerate(text):
        if ch == ":":
            cw = t * 1.2
            for k, yy in enumerate((0.30, 0.70)):
                cx, cy = x + cw / 2, pad + yy * h
                items.append((ci, f"colon{k}", [(cx - t / 2, cy - t / 2), (cx + t / 2, cy - t / 2),
                                                (cx + t / 2, cy + t / 2), (cx - t / 2, cy + t / 2)]))
            x += cw + sp * h
            continue
        for s in G.SEGMENTS.get(ch, ""):
            rx, ry, rw, rh = rects[s]
            items.append((ci, s, [(x + rx, pad + ry), (x + rx + rw, pad + ry), (x + rx + rw, pad + ry + rh),
                                  (x + rx, pad + ry + rh)]))
        x += w + sp * h
    return tuple(items), int(math.ceil(x - sp * h + pad)), int(math.ceil(h + 2 * pad))


def fx_seven_segment_clock(variant: str = "grey") -> Fx:
    """4AM's clocks: 4 digit slots + colon, each segment a polygon whose level is an expression of the digit
    controls (10 = blank). grey = the bevelled grainy grey clocks with round colon dots (f270 intro '3:59', f3181 big
    clock); led = the red LED card (f3536-3619): plain rectangles, wider spacing, strong red glow, red vignette.
    With digit 1 blank the visible three digits are centred (as 4AM centres '3:59')."""
    led = variant == "led"
    V = CLOCKS[variant]
    fx = Fx("seven-segment-clock", "Seven Segment Clock LED" if led else "Seven Segment Clock", "title")
    if led:
        items, Wm, Hm = led_layout("88:88", CLOCK_H, V["th"], V["wr"], V["sp"])
    else:
        items, Wm, Hm = G.seg_layout("88:88", CLOCK_H, "bevel", V["th"], V["wr"], V["sp"])
    X0, Y0 = (CW - Wm) / 2, (CH - Hm) / 2
    body = fx.bg("Clock", V["color"], 1.0)
    for (cid, label), d in zip((("D1", "Digit 1 (10 = blank)"), ("D2", "Digit 2"), ("D3", "Digit 3"),
                                ("D4", "Digit 4")), V["digits"]):
        fx.c.control(body, cid, label, d, 0, 10, integer=True)
    fx.c.control(body, "ColonOn", "Colon", 1.0, kind="CheckboxControl", integer=True)
    fx.c.control(body, "Grain", f"Grain (4AM {V['grain']:g})", V["grain"], 0, 1)
    fx.c.control(body, "Glow", f"Glow (4AM {V['glow']:g})", V["glow"], 0, 3)
    fx.c.control(body, "Vignette", "Red vignette (LED card 1)", V["vignette"], 0, 1)
    slot = {0: "D1", 1: "D2", 3: "D3", 4: "D4"}
    t = V["th"] * CLOCK_H
    m = None
    for ci, seg, poly in items:
        if seg.startswith("colon"):
            lvl = Expr("Clock.ColonOn")
        else:
            d = slot[ci]
            off = sorted(set(range(11)) - {int(x) for x in SEG_ON[seg]})
            expr = "1"
            for v in reversed(off):                     # nested iif: no reliance on and / or in expressions
                expr = f"iif(Clock.{d} == {v}, 0, {expr})"
            lvl = Expr(expr)
        chain = dict(EffectMask=Conn(m, "Mask"), PaintMode=FuID("Maximum")) if m else {}
        if seg.startswith("colon") and V["round_colon"]:
            cx = sum(p[0] for p in poly) / len(poly)
            cy = sum(p[1] for p in poly) / len(poly)
            # EllipseMask Width AND Height are fractions of the mask WIDTH (measured: t / CH drew 1.78x tall dots)
            m = fx.add("EllipseMask", f"S{ci}{seg}", Center=((X0 + cx) / CW, 1 - (Y0 + cy) / CH), Width=t / CW,
                       Height=t / CW, MaskWidth=CW, MaskHeight=CH, UseFrameFormatSettings=0,
                       ClippingMode=FuID("None"), Level=lvl, **chain)
            continue
        txt = ", ".join(f"{{ Linear = true, X = {(X0 + px - CW / 2) / CW:.6f}, Y = {-(Y0 + py - CH / 2) / CH:.6f}, "
                        f"LX = 0, LY = 0, RX = 0, RY = 0 }}" for px, py in poly)
        m = fx.add("PolylineMask", f"S{ci}{seg}", Center=(0.5, 0.5),
                   Polyline=Raw(f"Polyline {{ Closed = true, Points = {{ {txt} }} }}"), MaskWidth=CW, MaskHeight=CH,
                   UseFrameFormatSettings=0, ClippingMode=FuID("None"), Level=lvl, **chain)
    sd = 0.35                                            # N(1, grain) blurred = resolve_build.comp_clock
    nz = fx.add("FastNoise", "Grainy", Width=CW, Height=CH, UseFrameFormatSettings=0, Detail=10.0, Contrast=1.0,
                XScale=180.0, SeetheRate=0.5,
                **{f"Color1{c}": Expr(f"1 - 2.2 * {sd} * Clock.Grain") for c in ("Red", "Green", "Blue")},
                **{f"Color2{c}": Expr(f"1 + 2.2 * {sd} * Clock.Grain") for c in ("Red", "Green", "Blue")},
                Color1Alpha=1.0, Color2Alpha=1.0)
    grainy = fx.add("Merge", "GrainyBody", Background=Conn(body), Foreground=Conn(nz), ApplyMode=FuID("Multiply"))
    canvas = fx.bg("Canvas")
    white = fx.add("Merge", "SegImage", Background=Conn(fx.bg("SegBlack")),
                   Foreground=Conn(fx.bg("SegWhite", (1, 1, 1), 1.0)), EffectMask=Conn(m, "Mask"))
    blur = fx.add("Blur", "GlowBlur", Input=Conn(white), XBlurSize=blur_size(V["sigma"]), Filter=FuID("Gaussian"))
    fx.bg("GlowColor")                                   # alpha 0: the glow adds light (also on the Edit page)
    for ch in ("Red", "Green", "Blue"):
        fx.c.tools[-1].inputs[f"TopLeft{ch}"] = Expr(f"Clock.TopLeft{ch}")
    canvas = fx.add("Merge", "Glow", Background=Conn(canvas), Foreground=Conn("GlowColor"), Blend=Expr("Clock.Glow"),
                    EffectMask=Conn(blur, "Output"))
    canvas = fx.add("Merge", "Segments", Background=Conn(canvas), Foreground=Conn(grainy),
                    EffectMask=Conn(m, "Mask"))
    # digit 1 blank: centre the three visible characters (shift by half a digit slot)
    shift = (V["wr"] + V["sp"]) * CLOCK_H / 2 / CW
    canvas = fx.add("Transform", "Align", Input=Conn(canvas), FilterMethod=2,
                    Center=Expr(f"Point(0.5 - iif(Clock.D1 == 10, {shift:.6f}, 0), 0.5)"))
    placed = fx.place(canvas)
    # the red vignette belongs to the frame, not to the clock (independent of Position / Size) and lies UNDER the
    # digits like test_4am's (on top it lifted the LED digits from 64 to 69 %)
    vbase = fx.bg("VignetteBase", frame=True)
    vig = fx.add("Custom", "VignetteShape", Image1=Conn(vbase), NumberIn1=Expr("0.11 * Clock.Vignette"),
                 NumberIn2=0.0, NumberIn3=0.0,
                 Intermediate1="max(0, 1 - sqrt(((x - 0.5) / 0.6) ^ 2 + ((y - 0.5) / 0.6) ^ 2)) ^ 1.5",
                 RedExpression="i1 * n1", GreenExpression="i1 * n2", BlueExpression="i1 * n3", AlphaExpression="1")
    # alpha 0 only after the colour exists (a Custom tool's alpha-0 output is premultiplied to black): it then adds
    vig = fx.add("ChannelBoolean", "VignetteAdditive", Background=Conn(vig), ToAlpha=15)
    fx.last = fx.add("Merge", "OverVignette", Background=Conn(vig), Foreground=Conn(placed))
    for cid in ("D1", "D2", "D3", "D4", "ColonOn"):
        fx.expose(cid, "Clock", cid)
    fx.expose("ColorRed", "Clock", "TopLeftRed", "Colour red")
    fx.expose("ColorGreen", "Clock", "TopLeftGreen", "Colour green")
    fx.expose("ColorBlue", "Clock", "TopLeftBlue", "Colour blue")
    for cid in ("Grain", "Glow", "Vignette"):
        fx.expose(cid, "Clock", cid)
    return fx


# 4AM's title (fitted to f10 at full size: IoU 0.75 of the stroke cores; colour and glow measured)
TITLE = dict(height=32, width_scale=3.8, stroke=13.0, tracking=0.05, color=(0.663, 0.010, 0.017), glow=1.15,
             sigma=23.0)


def fx_pixel_title(text: str = "LOCKED IN", slug: str = "pixel-title") -> Fx:
    """4AM's heavy, wide pixel-font title (E001 'LOCKED IN' f0-29, the same card at the end f3620-3674): the lab's
    glyph strokes as rectangle masks, deep red with a wide glow halo. Text is baked: `library.py title "TEXT"`."""
    fx = Fx(slug, "Pixel Title", "title")
    spec = {"text": text, "cx": CW / 2, "cy": CH / 2, **{k: TITLE[k] for k in ("height", "width_scale", "stroke",
                                                                              "tracking")}}
    rects, st, Wm, Hm, X0, Y0 = text_strokes(spec)              # the rebuild's stroke geometry, 4AM's proportions
    m = None
    for i, (rx, ry, rw, rh, ang) in enumerate(rects):
        ins = dict(Center=((rx + rw / 2) / CW, 1 - (ry + rh / 2) / CH), Width=rw / CW, Height=rh / CH,
                   MaskWidth=CW, MaskHeight=CH, UseFrameFormatSettings=0, ClippingMode=FuID("None"))
        if ang:
            ins["Angle"] = ang
        if m:
            ins.update(EffectMask=Conn(m, "Mask"), PaintMode=FuID("Maximum"))
        m = fx.add("RectangleMask", f"Stroke{i + 1}", **ins)
    col = fx.bg("Title", TITLE["color"], 1.0)
    fx.c.control(col, "Glow", "Glow (4AM 1.15)", TITLE["glow"], 0, 3)
    canvas = fx.bg("Canvas")
    # resolve_build.glow_shape: blur(mask) * glow * colour added (alpha 0), then the letters in their colour
    white = fx.add("Merge", "TextImage", Background=Conn(fx.bg("TextBlack")),
                   Foreground=Conn(fx.bg("TextWhite", (1, 1, 1), 1.0)), EffectMask=Conn(m, "Mask"))
    blur = fx.add("Blur", "GlowBlur", Input=Conn(white), XBlurSize=blur_size(TITLE["sigma"]), Filter=FuID("Gaussian"))
    fx.bg("GlowColor")
    for ch in ("Red", "Green", "Blue"):
        fx.c.tools[-1].inputs[f"TopLeft{ch}"] = Expr(f"Title.TopLeft{ch}")
    canvas = fx.add("Merge", "Glow", Background=Conn(canvas), Foreground=Conn("GlowColor"), Blend=Expr("Title.Glow"),
                    EffectMask=Conn(blur, "Output"))
    canvas = fx.add("Merge", "Text", Background=Conn(canvas), Foreground=Conn(col), EffectMask=Conn(m, "Mask"))
    fx.last = fx.place(canvas)
    fx.expose("ColorRed", "Title", "TopLeftRed", "Colour red")
    fx.expose("ColorGreen", "Title", "TopLeftGreen", "Colour green")
    fx.expose("ColorBlue", "Title", "TopLeftBlue", "Colour blue")
    fx.expose("Glow", "Title", "Glow")
    fx.text = text
    return fx


def fx_firework() -> Fx:
    """The rebuild's tuned particle burst (rounds 1-5 against the lab's graphics.firework): bursts on the clip's
    first frame (Burst frame moves it), 260 line sparks with drag and gravity, ignition flash, glow; additive."""
    T = FIREWORK
    fx = Fx("firework-burst", "Firework Burst", "title")
    W, H = 1520, 1080          # the particle canvas the rebuild tuned on (velocity 1 = 152 px / frame at this width)
    de = T["drag_end"]
    # 4AM firework 1 (f3076): 600 px, life 64 frames; firework 2 (f3137): 680 px, 75 frames - the physics follows
    # from these two controls exactly as resolve_build.comp_firework computes it
    k = f"(1 - {1 - de:.6f} ^ (1 / Sparks.Life))"                        # drag per frame
    reach = f"(0.47 * Sparks.SizePx / {PART_PX_PER_VEL} / {de})"
    em = fx.add("pEmitter", "Sparks", RandomSeed=3,
                Number=Expr("iif(time == Sparks.Burst, Sparks.Count, 0)"),
                Lifespan=Expr(f"{T['life_mean']} * Sparks.Life"), LifespanVariance=Expr(f"{T['life_var']} * Sparks.Life"),
                Velocity=Expr(f"{T['speed_mean']} * {reach} * {k}"),
                VelocityVariance=Expr(f"{T['speed_var']} * {reach} * {k}"),
                Angle=0.0, AngleVariance=360.0, Style=FuID("ParticleStyleLine"), RotationControls=1, RotationMode=1,
                **{"SphereRgn.Size": 0.002, "ParticleStyle.Size": T["line_size"],
                   "ParticleStyle.SizeToVelocity": T["line_size_to_velocity"],
                   "ParticleStyle.ColorOverLife": Raw(T["fade"])})
    fx.c.control(em, "Burst", "Burst frame (from the clip start)", 0, 0, 100, integer=True)
    fx.c.control(em, "SizePx", "Size (px across, 4AM 600 / 680)", 600.0, 100, 1400)
    fx.c.control(em, "Life", "Life (frames, 4AM 64 / 75)", 64.0, 10, 200, integer=True)
    fx.c.control(em, "Count", "Sparks", float(T["number"]), 20, 600, integer=True)
    drag = fx.add("pFriction", "Drag", Input=Conn(em), VelocityFriction=Expr(k))
    grav = fx.add("pDirectionalForce", "Gravity", Input=Conn(drag), Direction=-90.0,
                  Strength=Expr(f"{T['gravity']} * 0.36 * Sparks.SizePx / (Sparks.Life * Sparks.Life) / {PART_PX_PER_VEL}"))
    rnd = fx.add("pRender", "Render", Input=Conn(grav), OutputMode=FuID("TwoD"), Width=W, Height=H,
                 UseFrameFormatSettings=0, AutomaticPreRoll=0, PreRoll=0)
    soft = fx.add("Blur", "SparkWidth", Input=Conn(rnd), XBlurSize=blur_size(0.8), Filter=FuID("Gaussian"))
    thick = fx.add("BrightnessContrast", "SparkGain", Input=Conn(soft), Gain=T["spark_gain"], Alpha=1, ClipWhite=1)
    last = fx.add("Merge", "SparksOnBlack", Background=Conn(fx.bg("Black", alpha=1.0, w=W, h=H)),
                  Foreground=Conn(thick), ApplyMode=FuID("Screen"))
    # ignition flash: a core growing from 0.0075 S to 0.0225 S radius over the first 12 % of the life
    n0 = "max(1, floor(0.12 * Sparks.Life + 0.5))"
    age = "(time - Sparks.Burst)"
    grow = f"iif({age} >= 0, iif({age} <= {n0}, 0.015 + 0.03 * {age} / {n0}, 0), 0) * Sparks.SizePx"
    core = fx.add("EllipseMask", "IgnitionCore", Center=(0.5, 0.5), Width=Expr(f"{grow} / {W}"),
                  Height=Expr(f"{grow} / {W}"), MaskWidth=W, MaskHeight=H, UseFrameFormatSettings=0,   # both / width
                  ClippingMode=FuID("None"))
    last = fx.add("Merge", "Ignition", Background=Conn(last), Foreground=Conn(fx.bg("White", (1, 1, 1), 1.0, w=W, h=H)),
                  EffectMask=Conn(core, "Mask"), ApplyMode=FuID("Screen"),
                  Blend=Expr(f"iif({age} >= 0, iif({age} < {n0}, min(1, 1.2 * (1 - {age} / {n0}) + 0.3), 0), 0)"))
    # glow sigma 0.02 S: blur_size() is linear (x 1.147) between sigma 10.6 and 15.4 (S = 530-770 px)
    glow = fx.add("Blur", "GlowBlur", Input=Conn(last), XBlurSize=Expr(f"{blur_size(12.0) / 12.0:.5f} * 0.02 * Sparks.SizePx"),
                  Filter=FuID("Gaussian"))
    last = fx.add("Merge", "GlowAdd", Background=Conn(last), Foreground=Conn(glow), ApplyMode=FuID("LinearDodge"),
                  Blend=0.8)
    last = fx.add("ColorGain", "Brightness", Input=Conn(last), GainRed=1.0, GainGreen=1.0, GainBlue=1.0)
    last = fx.add("BrightnessContrast", "Clip01", Input=Conn(last), ClipBlack=1, ClipWhite=1)
    fx.last = fx.place(last, additive=True)
    fx.expose("Burst", "Sparks", "Burst")
    fx.expose("SizePx", "Sparks", "SizePx")
    fx.expose("Life", "Sparks", "Life")
    fx.expose("Count", "Sparks", "Count")
    fx.expose("Seed", "Sparks", "RandomSeed", "Random seed")
    fx.expose("BrightR", "Brightness", "GainRed", "Brightness (red)")
    fx.expose("BrightG", "Brightness", "GainGreen", "Brightness (green)")
    fx.expose("BrightB", "Brightness", "GainBlue", "Brightness (blue)")
    return fx


def fx_film_grain() -> Fx:
    """test_4am's grain: Film Grain on a 0.5 grey, added around zero in float (Out = In + 2 (grain - 0.5)).
    Defaults = the lab's grain (sigma 0.01 at half res); the user's own Resolve tweak is a preset in the recipe."""
    fx = Fx("film-grain", "Film Grain", "effect")
    mid = fx.bg("MidGrey", (0.5, 0.5, 0.5), 1.0, frame=True)
    g = fx.add("FilmGrain", "Grain", Input=Conn(mid), Monochrome=1, LogProcessing=0, MasterStrength=0.007726,
               MasterXSize=1.0, MasterYSize=1.0, MasterRoughness=0.0, MasterOffset=0.0, Complexity=2)
    add = fx.add("Custom", "AddGrain", Image2=Conn(g), NumberIn1=1.0,
                 RedExpression="r1 + (r2 - 0.5) * 2 * n1", GreenExpression="g1 + (g2 - 0.5) * 2 * n1",
                 BlueExpression="b1 + (b2 - 0.5) * 2 * n1", AlphaExpression="a1")
    fx.first, fx.first_input, fx.last = add, "Image1", add
    fx.expose("Strength", "Grain", "MasterStrength", "Strength (4AM 0.0077)")
    fx.expose("GrainSize", "Grain", "MasterXSize", "Grain size")
    fx.expose("Roughness", "Grain", "MasterRoughness", "Roughness")
    fx.expose("Complexity", "Grain", "Complexity", "Complexity")
    fx.expose("Amount", "AddGrain", "NumberIn1", "Amount", Default=1.0)
    return fx


EASE = "(Ctl.T * Ctl.T * (3 - 2 * Ctl.T))"            # smoothstep of the normalised time


def fx_pan_board() -> Fx:
    """test_4am's pan boards (f518-1328, f1493-2265, f2583-3180): panels on a board wider than the frame, ONE
    Transform moving it (slowly, eased). Fusion-page macro: 4 panel inputs placed by Position / Size."""
    fx = Fx("pan-board", "Pan Board", "fusion")
    board = fx.add("Background", "Board", Width=3040, Height=1080, UseFrameFormatSettings=0, TopLeftRed=0.045,
                   TopLeftGreen=0.045, TopLeftBlue=0.045, TopLeftAlpha=1.0, Depth=DEPTH)
    last = board
    for i, (cx, sz) in enumerate(((0.16, 0.30), (0.40, 0.30), (0.64, 0.30), (0.86, 0.30)), 1):
        last = fx.add("Merge", f"Panel{i}", Background=Conn(last), Center=(cx, 0.5), Size=sz)
        fx.expose(f"Panel{i}In", f"Panel{i}", "Foreground", f"Panel {i}")
        fx.expose(f"Panel{i}Pos", f"Panel{i}", "Center", f"Panel {i} position (on the board)")
        fx.expose(f"Panel{i}Size", f"Panel{i}", "Size", f"Panel {i} size")
    ctl = fx.add("Transform", "Ctl", Input=Conn(last), FilterMethod=5,
                 Center=Expr("Point(0.5 - (Ctl.From + (Ctl.To - Ctl.From) * " + EASE.replace("Ctl.T", "Ctl.Tn")
                             + "), 0.5)"))
    fx.c.control(ctl, "From", "Pan from (board widths)", 0.0, -1, 1)
    fx.c.control(ctl, "To", "Pan to (board widths)", 0.5, -1, 1)
    fx.c.control(ctl, "Frames", "Pan duration (frames)", 600, 1, 2000, integer=True)
    fx.c.control(ctl, "Tn", "(internal) normalised time", 0, 0, 1)
    fx.c.tools[-1].inputs["Tn"] = Expr("min(1, max(0, time / Ctl.Frames))")
    crop = fx.add("Crop", "Window", Input=Conn(ctl), XOffset=0, YOffset=0, XSize=1520, YSize=1080)
    fx.last = crop
    fx.expose("From", "Ctl", "From")
    fx.expose("To", "Ctl", "To")
    fx.expose("Frames", "Ctl", "Frames")
    fx.expose("WindowW", "Window", "XSize", "Frame width (px)")
    fx.expose("WindowH", "Window", "YSize", "Frame height (px)")
    fx.expose("BoardW", "Board", "Width", "Board width (px)")
    return fx


def fx_mosaic_zoom() -> Fx:
    """E051-E052 (f3234-3521): a wall of tiles zooms out from one tile (31.6x) to the whole wall - log-linear
    scale (constant perceived speed), eased at both ends; the tiles are moving clips (L005)."""
    fx = Fx("mosaic-zoom", "Mosaic Zoom", "effect")
    # measured on 4AM (log of the scale): 50 % done at 25 % of the time, 80 % at 50 % -> decelerating, power 2.3
    e = "(1 - (1 - Zoom.Tn) ^ Zoom.Decel)"
    # one fixed point A on the wall: the tile T fills the centre at the start, the whole wall is in place at 1x at
    # the end - a plain camera zoom-out about A = (T s0 - 0.5) / (s0 - 1)
    s0 = "max(1.0001, Zoom.ZoomFrom)"
    z = fx.add("Transform", "Zoom", FilterMethod=5, Center=(0.5, 0.5),
               Pivot=Expr(f"Point((Zoom.TileX * {s0} - 0.5) / ({s0} - 1), (Zoom.TileY * {s0} - 0.5) / ({s0} - 1))"),
               Size=Expr(f"Zoom.ZoomFrom ^ (1 - {e}) * Zoom.ZoomTo ^ {e}"))     # log-linear: constant perceived speed
    fx.c.control(z, "ZoomFrom", "Zoom from (4AM 31.6)", 31.58, 1, 60)
    fx.c.control(z, "Decel", "Slow end (4AM 2.3, 1 = linear)", 2.3, 1, 5)
    fx.c.control(z, "ZoomTo", "Zoom to", 1.0, 0.1, 10)
    fx.c.control(z, "Frames", "Duration (frames, 4AM 308)", 308, 1, 2000, integer=True)
    fx.c.control(z, "TileX", "Tile x (0 = left, 1 = right)", 0.5, 0, 1)
    fx.c.control(z, "TileY", "Tile y (0 = bottom, 1 = top; 4AM 0.567)", 0.5667, 0, 1)
    fx.c.control(z, "Tn", "(internal) normalised time", 0, 0, 1)
    fx.c.tools[-1].inputs["Tn"] = Expr("min(1, max(0, time / Zoom.Frames))")
    fx.first, fx.last = z, z
    for cid in ("ZoomFrom", "ZoomTo", "Frames", "Decel", "TileX", "TileY"):
        fx.expose(cid, "Zoom", cid)
    return fx


def flicker_curve() -> dict | None:
    """test_4am's measured 4AM hall light level per frame (plan_v1 curves.flicker: start f1485, 216 values)."""
    plan = LAB / "projects" / "test_4am" / "build" / "plan_v1.json"
    if not plan.exists():
        return None
    c = json.loads(plan.read_text(encoding="utf-8")).get("curves", {}).get("flicker")
    return c if c and c.get("values") else None


def fx_flashlight_flicker() -> Fx:
    """L003 plan B: 4AM's hall flicker (E019-E027, f1493-1693) is a real flashlight. In Resolve: the frame darkened
    to an ambient level, a soft hotspot that flickers on random holds (deterministic hash of the hold number)."""
    fx = Fx("flashlight-flicker", "Flashlight Flicker", "effect")
    src = fx.add("BrightnessContrast", "In")                    # the clip, shared by the dark and the lit version
    # the room darkened to an ambient level; highlights above the threshold are kept (4AM's dark frames keep the
    # windows - they are lit from outside, not by the flashlight)
    dark = fx.add("Custom", "Ambient", Image1=Conn(src), NumberIn1=0.15, NumberIn2=0.7,
                  RedExpression="r1 * n1 + max(0, r1 - n2) * (1 - n1) / max(0.001, 1 - n2)",
                  GreenExpression="g1 * n1 + max(0, g1 - n2) * (1 - n1) / max(0.001, 1 - n2)",
                  BlueExpression="b1 * n1 + max(0, b1 - n2) * (1 - n1) / max(0.001, 1 - n2)", AlphaExpression="a1")
    fx.c.control(dark, "Hold", "Frames per flicker step", 2, 1, 12, integer=True)
    fx.c.control(dark, "Duty", "Light on (share of steps)", 0.6, 0, 1)
    fx.c.control(dark, "Seed", "Random seed", 7, 0, 100, integer=True)
    fx.c.control(dark, "Floor", "Light level when off", 0.0, 0, 1)
    fx.c.control(dark, "Pattern", "Pattern", 0, kind="ComboControl", integer=True,
                 choices=["Random holds", "4AM hall (216 f)"])
    fx.first, fx.first_input = src, "Input"
    # the measured 4AM hall flicker (light level per frame, 0-1.13) as a spline on a hidden control
    curve = flicker_curve()
    fx.c.control(dark, "P4AM", "(4AM curve)", 1.0, 0, 2)
    if curve:
        fx.c.tools[-1].inputs["P4AM"] = Spline([(i, float(v)) for i, v in enumerate(curve["values"])])
    rnd = ("(sin((floor(time / Ambient.Hold) + Ambient.Seed * 17.1) * 12.9898) * 43758.5453 - "
           "floor(sin((floor(time / Ambient.Hold) + Ambient.Seed * 17.1) * 12.9898) * 43758.5453))")
    lit = fx.add("BrightnessContrast", "Lit", Input=Conn(src),
                 Gain=Expr(f"iif(Ambient.Pattern == 1, Ambient.P4AM, "
                           f"iif({rnd} < Ambient.Duty, 0.6 + 0.4 * {rnd} / max(0.01, Ambient.Duty), Ambient.Floor))"))
    # Width / Height as fractions of the frame WIDTH: 0.45 x 0.5 = 684 x 760 px on a 1520 x 1080 frame
    spot = fx.add("EllipseMask", "Hotspot", Center=(0.5, 0.55), Width=0.45, Height=0.5, SoftEdge=0.25,
                  UseFrameFormatSettings=1, ClippingMode=FuID("None"))
    fx.last = fx.add("Merge", "Light", Background=Conn(dark), Foreground=Conn(lit), EffectMask=Conn(spot, "Mask"))
    fx.expose("AmbientLevel", "Ambient", "NumberIn1", "Ambient (room) level", Default=0.15)
    fx.expose("KeepHighlights", "Ambient", "NumberIn2", "Keep highlights above (1 = off)", Default=0.7)
    fx.expose("Hold", "Ambient", "Hold")
    fx.expose("Duty", "Ambient", "Duty")
    fx.expose("Seed", "Ambient", "Seed")
    fx.expose("Floor", "Ambient", "Floor")
    fx.expose("Pattern", "Ambient", "Pattern")
    fx.expose("SpotCenter", "Hotspot", "Center", "Hotspot position")
    fx.expose("SpotW", "Hotspot", "Width", "Hotspot width")
    fx.expose("SpotH", "Hotspot", "Height", "Hotspot height")
    fx.expose("SpotSoft", "Hotspot", "SoftEdge", "Hotspot softness")
    return fx


def fx_slow_drift() -> Fx:
    """test_4am night_drift (f1424-1450): a digital camera move on a shot that has none - the shot zoomed 1.25x,
    its crop window slides (compose 'anchor' 0.62 -> 0.45, ease 'out' = 1 - (1 - t)^2) so the picture moves right
    by 18.75 % of the frame width (from -12.5 % to +6.25 %), then holds. Positions in % of the frame width/height."""
    fx = Fx("slow-drift", "Slow Drift", "effect")
    ease = "(1 - (1 - Drift.Tn) ^ 2)"
    t = fx.add("Transform", "Drift", FilterMethod=5,
               Center=Expr(f"Point(0.5 + (Drift.StartX + Drift.DistX * {ease}) / 100, "
                           f"0.5 + (Drift.StartY + Drift.DistY * {ease}) / 100)"),
               Size=Expr("Drift.Zoom"))
    fx.c.control(t, "StartX", "Start x (% of the width, test_4am -12.5)", -12.5, -100, 100)
    fx.c.control(t, "DistX", "Move x (% of the width, test_4am 18.75)", 18.75, -100, 100)
    fx.c.control(t, "StartY", "Start y (% of the height)", 0.0, -100, 100)
    fx.c.control(t, "DistY", "Move y (% of the height)", 0.0, -100, 100)
    fx.c.control(t, "Frames", "Duration (frames, test_4am 26)", 26, 1, 500, integer=True)
    fx.c.control(t, "Zoom", "Zoom (test_4am 1.25; keep the frame covered)", 1.25, 1, 3)
    fx.c.control(t, "Tn", "(internal) normalised time", 0, 0, 1)
    fx.c.tools[-1].inputs["Tn"] = Expr("min(1, max(0, time / Drift.Frames))")
    fx.first, fx.last = t, t
    for cid in ("StartX", "DistX", "StartY", "DistY", "Frames", "Zoom"):
        fx.expose(cid, "Drift", cid)
    return fx


# macro file stem -> (library folder, builder)
MACROS = {"exposure-flash": ("exposure-flash", fx_exposure_flash),
          "seven-segment-clock": ("seven-segment-clock", lambda: fx_seven_segment_clock("grey")),
          "seven-segment-clock-led": ("seven-segment-clock", lambda: fx_seven_segment_clock("led")),
          "pixel-title": ("pixel-title", fx_pixel_title),
          "firework-burst": ("firework-burst", fx_firework),
          "film-grain": ("film-grain", fx_film_grain),
          "pan-board": ("pan-board", fx_pan_board),
          "mosaic-zoom": ("mosaic-zoom", fx_mosaic_zoom),
          "flashlight-flicker": ("flashlight-flicker", fx_flashlight_flicker),
          "slow-drift": ("slow-drift", fx_slow_drift)}
MACRO_KIND = {"exposure-flash": "effect", "seven-segment-clock": "title", "seven-segment-clock-led": "title",
              "pixel-title": "title", "firework-burst": "title", "film-grain": "effect",
              "pan-board": "Fusion page", "mosaic-zoom": "effect", "flashlight-flicker": "effect",
              "slow-drift": "effect"}

KIND_TEXT = {"effect": "Edit-page **effect**: drag it onto a clip (Effects > Fusion Effects once installed).",
             "title": "Edit-page **title**: drag it onto a track above the clips (Titles > Fusion Titles once installed); "
                      "it starts on the clip's first frame.",
             "fusion": "**Fusion-page macro** (several image inputs): add it in the Fusion page of a Fusion clip and "
                       "connect the panels."}

# recipe content: 4AM events it comes from, measured values, presets, how to do it without the macro, lessons
META = {
    "exposure-flash": dict(
        title="Exposure flash", events=["E002", "E004", "E011", "E014", "E016", "E030", "E033", "E034", "E037", "E039"],
        quote=["E004", "E011", "E039"], refs=[329, 706, 1329, 2616], lessons=["L001"],
        measured=["1-2 frames, almost always hiding a cut or a panel change, often on a beat: f329 on the bar line "
                  "(f328.6), f706 on the beat (f706.1), f2160 on the beat (f2159.8).",
                  "Two kinds (the 'flash look' line every analysed flash now gets: level of the lit area + texture, "
                  "flat = texture below 2.5): **over-exposed pictures that keep their texture** - E034 f2266 63 % "
                  "(texture 3.6), E039 f2616 72 % (23), E016 f1423 81 % (4.0), the E004 panel exits 56-66 % (6.5-10) - "
                  "and **flat light-grey frames** - E014 f1329 88 % (0.4), E033 f2161 88 % (0.1), E011 f706 87 % "
                  "(0.6, with the new shot faintly showing at the bottom), E037 f2533 85 % (1.2). Nothing in 4AM "
                  "reaches pure white.",
                  "E030 f1982-1983 is not an added flash: a white sleeve in the shot catches the light (81 %, "
                  "texture 11.7) - in camera.",
                  "The model: every 4AM flash frame is the frame lifted toward white, out = v + k (1 - v) (v = the "
                  "picture, 0-1). Fitted on the lit area: E034 k 0.58, E039 0.65, E016 0.79, E011 0.83, E014 0.87 "
                  "(that one is flat). The macro's Flash strength is k; test_4am used the same model as one LUT per "
                  "flash frame (k 0.45-0.8) and solids at 0.86-0.88 grey for the flat ones."],
        presets=[("Over-exposed picture", "as installed: Flash strength 0.62, Exposure push 1, Softness 2, Flat 0"),
                 ("E034 f2266 (63 %)", "Flash strength 0.58"), ("E039 f2616 (72 %)", "Flash strength 0.65"),
                 ("E016 f1423 (81 %)", "Flash strength 0.79"),
                 ("E011 f706 washed first frame of a new shot (87 %)", "Flash strength 0.83, Softness 0"),
                 ("Flat light grey (E014, E033, E037)", "Flat 1, Flat level 0.88 (E037: 0.85)"),
                 ("One panel only (E011, E033, E037)", "put the effect on that panel's clip only"),
                 ("Decay frame after it (E039: f2617 at 25 %)", "key Amount 1 on the flash frame and about 0.15 on the "
                                                                 "next frame")],
        without=["Blade the clip at the flash frame; on that 1-frame piece (Color page) raise Lift until the blacks sit "
                 "at k (0.6 for 60 %), keep Gain at 1; for the flat kind put a Solid Color at 0.88 grey (not 1.0) on the "
                 "track above.",
                 "Or a 1D LUT out = v + k (1 - v) on that frame (what test_4am does) - the picture stays visible."]),
    "seven-segment-clock": dict(
        title="Seven-segment clock", events=["E047", "E048", "E050", "E055"], quote=["E048", "E050", "E055"],
        refs=[300, 3200, 3221, 3560], lessons=["L006"],
        measured=["f270 (00:00:10:20) a grey '3:59' pops into the bottom-left slot of the collage (missed by the "
                  "pipeline, found with the possible-misses list); '4:00' from f320; it leaves with an over-exposed "
                  "exit frame at f331. Measured at f300: digits 217 px high, the three characters centred at 382 / "
                  "891 px.",
                  "Big grey clock f3181-3222: digits 514 px high, centred (765 / 540 px); fades in after the dip to "
                  "black (test_4am opacity f3181-3200: 0.05, 0.10, 0.13, 0.21, 0.25, 0.27, 0.36, 0.38, 0.43, 0.51, "
                  "0.49, 0.62, 0.67, 0.62, 0.78, 0.80, 0.79, 0.93, 0.87, 1.0); single segments dim to 50-55 % for one "
                  "frame about every 3 frames (f3202, 3205, 3210, 3213, 3216, 3218); '3:59' -> '4:00' at f3221 "
                  "(00:02:08:21) in one frame, then the mosaic zoom starts at f3223.",
                  "Grey clocks (measured at f3200 / f300): grey 0.63, bevelled segments 0.117 x the digit height "
                  "thick, digit width 0.71 x height, spacing 0.117 x height, round colon dots, animated grain.",
                  "Red LED card f3536-3619 (84 frames, still), measured at f3560: digits 336 px high, centred (764 / "
                  "540 px); plain rectangular segments 0.155 x height thick, the verticals continuous (the 0 is a "
                  "closed ring), digit width 0.66, spacing 0.18; deep red 0.65 / 0.01 / 0.02, glow 1.05 with sigma "
                  "30 px, a faint red vignette.",
                  "test_4am used brighter, thicker digits (grey 0.74, red 0.92, segments 0.13-0.15) - the macros use "
                  "the 4AM measurements; check.png compares them with the real frames."],
        presets=[("Intro clock (f270)", "seven-segment-clock as installed (blank, 3, 5, 9); Size 0.723; Position 0.251 "
                                        "/ 0.175; colour 0.57 (measured 56 %); key D2-D4 to 4 / 0 / 0 at f320"),
                 ("Big clock (f3181)", "seven-segment-clock: Size 1.713, Position 0.503 / 0.5; key Opacity with the fade "
                                       "above; a dimmed segment = key that digit for one frame"),
                 ("Red LED card (f3536)", "seven-segment-clock-led as installed (04:00): Size 1.12, Position 0.503 / 0.5"),
                 ("Small logo clock (test_4am f336-358)", "Size 0.233 + the opacity keys of the faulty-light-strobe "
                                                          "recipe")],
        without=["Text+ with a seven-segment font (e.g. DSEG7, free) in grey 0.74 plus a Film Grain / Fast Noise "
                 "texture; for the red card add Glow and a red circular Power Window vignette."]),
    "pixel-title": dict(
        title="Pixel-font title", events=["E001", "E056"], quote=["E001", "E056"], refs=[10, 3640], lessons=[],
        measured=["Opening title f0-29 (30 frames) and the same card at the end f3620-3674 (55 frames): heavy, "
                  "wide pixel letters - fitted at f10: letter height 32 px + 13 px strokes (46 px in all), width x3.8, "
                  "736 px for 'LOCKED IN', centred at 760 / 536 px; deep red 0.66 / 0.01 / 0.02; a wide glow halo "
                  "(1.15, sigma 23 px) that reads as a soft red rectangle.",
                  "The end card is the same picture: f3640 minus f10 is under 5 levels everywhere (the 'faint frame' "
                  "in the E056 review is that glow halo).",
                  "Cut out under a one-frame grey photo flash at f30; cut to black at f3675."],
        presets=[("Opening title / end card", "as installed (LOCKED IN), Position 0.5 / 0.504"),
                 ("Your own text", "`.venv\\Scripts\\python tools\\library.py title \"YOUR TEXT\"` writes "
                                   "library\\pixel-title\\variants\\<text>.setting (letters A-Z, 0-9 and basic "
                                   "punctuation of the lab's pixel font)")],
        without=["Text+ with a pixel / LED font in red, Shading element 2 as an outline, then a Glow."]),
    "firework-burst": dict(
        title="Firework burst", events=["E044", "E045", "E046"], quote=["E044", "E046"],
        refs=[3077, 3082, 3090, 3140], lessons=["L004"],
        note="In 4AM the firework is FOOTAGE of a real firework display (the reviewed origin of E044-E046), "
             "screened into the black middle of the collage. This macro is test_4am's particle stand-in for when you "
             "have no such footage.",
        measured=["4AM, the black middle of the collage (measured per frame): a spark at f3076 (00:02:03:01), a bright "
                  "flash burst f3077-3081 (bright area 59-84 k px, median spark radius ~130 px from the first frame), "
                  "sparks spreading to ~170 px and fading by f3090; more bursts in the distance at f3092-3098 and "
                  "f3101-3107; firework 2 at the left from f3137.",
                  "The hooded-man panel is lit BY the bursts: panel 5 -> 8 % (the man 5 -> 11 %) on the burst frame "
                  "f3077, again 5 -> 9 % at f3138, then it dims with the light (lesson L004).",
                  "test_4am's particle burst (this macro): 600 px across at the end of a 64-frame life, tuned in 5 "
                  "rounds against the lab's firework graphic - slower and smoother than the real footage, which "
                  "bursts in 1-2 frames."],
        presets=[("Firework 1 (f3076)", "as installed; Position 0.349 / 0.565"),
                 ("Firework 2 (f3137)", "Size 680, Life 75, Random seed 8; Position 0.237 / 0.602"),
                 ("Light a panel with it (L004)", "on that clip key Gain (or Opacity) up on the burst frame and fade "
                                                  "it out with the sparks (about 60 frames)")],
        without=["Best (what 4AM does): stock or filmed firework footage on a track above, Composite Mode Screen "
                 "(its black sky disappears), keyed to the beat.",
                 "Fusion pEmitter (one burst of ~260 line particles, random directions) -> pFriction -> "
                 "pDirectionalForce (gravity) -> pRender; Blur + glow; composite Add / Screen."]),
    "film-grain": dict(
        title="Film grain", events=[], quote=[], refs=[], lessons=[],
        note="Not a 4AM event: the grain test_4am puts over the whole edit (the lab's renderer grain), so the "
             "rebuild matches the reference's texture.",
        measured=["test_4am: zero-mean luma grain, sigma 0.010 at half resolution, bilinear-upscaled = about 1.6 "
                  "levels per pixel in 8-bit, the same on every frame; matched in Resolve with Film Grain strength "
                  "0.0077, size 1, roughness 0, complexity 2 on a 0.5 grey, added around zero (float, no bias).",
                  "Your hand tweak in the Resolve timeline (2026-10-06): strength 0.0157, size 1.63, roughness 0.016, "
                  "complexity 8 - about twice as strong and coarser."],
        presets=[("Lab / test_4am", "as installed (Strength 0.0077, Grain size 1, Roughness 0, Complexity 2)"),
                 ("Your Resolve tweak", "Strength 0.0157, Grain size 1.63, Roughness 0.016, Complexity 8")],
        without=["Resolve Studio's Film Grain (Color page) at a low strength, or Fusion Film Grain on a 0.5 grey clip "
                 "on the top track composited Linear Light (what test_4am does)."]),
    "pan-board": dict(
        title="Pan board", events=["E010", "E013", "E028", "E029", "E032"], quote=["E013", "E032"],
        refs=[1080, 1108, 2121, 2160], lessons=[],
        measured=["The collages sit on a board wider than the frame that slides left: pan 1 moves 3008 px in 396 "
                  "frames (f790-1185), pan 2 2980 px in 541 frames (f1650-2190), pan 3 1536 px in 261 frames "
                  "(f2890-3150).",
                  "S-curve: of the move, 2 / 15 / 51 / 85 / 98 % is done at 10 / 25 / 50 / 75 / 90 % of the time "
                  "(pan 1; pan 2 5 / 17 / 51 / 84 / 97, pan 3 2 / 14 / 49 / 85 / 98) - a smoothstep (3 / 16 / 50 / "
                  "84 / 97), the macro's curve.",
                  "Panels pop in / out in one frame while the board moves; their own footage keeps playing."],
        presets=[("Pan 1", "Board width 4528 (1520 + 3008), From 0, To 0.664, Pan duration 396"),
                 ("Pan 2", "Board width 4500, From 0, To 0.662, Pan duration 541"),
                 ("Pan 3", "Board width 3056, From 0, To 0.503, Pan duration 261")],
        without=["Build the board as one wide Fusion comp (panels merged on a Background wider than the frame), then "
                 "ONE Transform with Center keyed start -> end, both keys Ease In / Out (Spline editor)."]),
    "mosaic-zoom": dict(
        title="Mosaic zoom-out", events=["E050", "E051", "E052", "E053", "E054"], quote=["E051", "E052", "E054"],
        refs=[3223, 3300, 3430, 3530], lessons=["L005"],
        measured=["f3223-3530 (308 frames, 12.3 s): from the clock tile at 31.6x to the whole '04:00' wall at 1x. In "
                  "log scale 19 / 51 / 80 / 94 / 99 % of the zoom is done at 10 / 25 / 50 / 75 / 90 % of the time "
                  "(decelerating; the macro's 'slow end' 2.3 gives 22 / 48 / 80 / 96 / 99).",
                  "The clock tile ends at 760 / 468 px in the wall (f3530, template match 0.93). The move is a "
                  "plain camera zoom-out about one fixed point: the macro's tile position matches the real one within "
                  "1 px at f3263 (00:02:10:13), f3300, f3377 and f3454; its scale curve within about 8 %.",
                  "Wall: 76 tiles of 52 x 42 px with 5 px gaps; the tiles are short moving clips (L005), not stills.",
                  "Single tiles twinkle white for one frame at f3498, f3519, f3530; then red frames f3531, f3533, "
                  "f3534 and black f3532, f3535 lead into the red LED card at f3536."],
        presets=[("4AM", "as installed: Zoom from 31.58 to 1, Duration 308, Slow end 2.3; Tile x 0.5, Tile y 0.567 "
                         "(the tile at 760 / 468 px)")],
        without=["A Transform on the wall with Size keyed 31.6 -> 1; in the Spline editor make the curve fall fast "
                 "first and settle slowly (ease out). Build the wall at a high resolution (or put the clock tile's "
                 "own full-size clip on top at the start): 31.6x of a 52 px tile is soft."]),
    "flashlight-flicker": dict(
        title="Flashlight flicker", events=["E019", "E020", "E021", "E022", "E023", "E024", "E025", "E026",
                                            "E027"], quote=["E024"], refs=[1493, 1539, 1615, 1645], lessons=["L003"],
        note="Your note: the hall flicker was done while shooting, with a real flashlight - hard to mimic in "
             "Resolve. Best: shoot it. This macro is plan B.",
        measured=["f1493-1693 in the dark pillared hall: the background and floor go dark before the man, he keeps "
                  "moving with no ghosting (a practical light). Dark holds of 4-16 frames, fades of about 10 frames; "
                  "his pose jumps between bursts (cuts hidden in the dark frames). The windows stay bright in the dark "
                  "frames (lit from outside): the macro keeps highlights above 0.7.",
                  "The measured light level per frame (test_4am 'flicker': f1485-1700, 216 values) ships in the "
                  "macro as Pattern '4AM hall'."],
        presets=[("Random flicker", "Pattern Random holds, Frames per step 2, Light on 0.6"),
                 ("4AM hall", "Pattern 4AM hall: frame 0 of the clip = 4AM f1485 (00:00:59:10)")],
        without=["Best: shoot it - a flashlight in the dark, cut between takes in the dark frames. Plan B: Color "
                 "page Gain keyed from the light curve plus a soft circular Power Window as the hotspot."]),
    "slow-drift": dict(
        title="Slow drift (digital camera move)", events=["E017"], quote=["E017"], refs=[1425, 1428], lessons=[],
        note="Not a 4AM effect: E017 is a real camera move (you agreed: a false alarm). test_4am fakes such a move "
             "on footage that has none (layer 'night_drift').",
        measured=["test_4am night_drift f1424-1450 (00:00:56:24 - 00:00:58:00): the night shot zoomed 1.25x, its crop "
                  "slides so the picture moves right by 18.75 % of the frame width (285 px, from -12.5 % to +6.25 %), "
                  "decelerating (1 - (1 - t)^2), then holds to f1472.",
                  "4AM E017 (f1425-1429): the night shot itself pans left about 3.3 % of the width per frame."],
        presets=[("test_4am", "as installed (Start x -12.5, Move x 18.75, Duration 26, Zoom 1.25)")],
        without=["Edit page: Zoom 1.25 and Position X keyed with Ease Out over 26 frames."]),
}

RECIPE_ONLY = {
    "collage-panels": dict(
        title="Collage panels (static)", events=["E003", "E010", "E015", "E035"], quote=["E010", "E035"],
        refs=[173, 518, 1392, 2449],
        text=["Panels pop in in one frame (no transition), often on a beat; each panel is a cover-fit crop of a shot "
              "on black (the video's black level, about 0.045).",
              "In Resolve (test_4am, exact to the pixel): one Edit-page clip per panel with Zoom / Position / Crop. For "
              "a panel rectangle (x, y, w, h) and the crop window (u0, v0, cw, ch) of a 1520 x 1140 source: Zoom = "
              "w / cw, Pan = x - W/2 + Zoom (760 - u0), Tilt = -(y - H/2 + Zoom (570 - v0)) / (1140 / 1080), Crop "
              "Left / Right / Top / Bottom = the window edges in source pixels (tools\\resolve_build.py "
              "edit_page_props)."]),
    "stepped-fade-in": dict(
        title="Stepped fade-in", events=["E007", "E008"], quote=["E008"], refs=[358, 361, 392, 409],
        text=["The hall shot starts under the 'DON PROD' logo at f358 (00:00:14:08): only its brightest practical "
              "lights show at first - a thin vertical light at x 358 px rising 20 / 40 / 60 / 80 % over f358-361, the "
              "ceiling lamp from f361 (measured; this is what the first review called light streaks, lesson L007).",
              "After the drop (f361.7) the room comes up from black in holds, not smoothly: test_4am opacity f362-365 0, "
              "f366 0.01, f367-389 0.02, f390-396 0.05, f397 0.06, f398-403 0.35-0.38, f404 0.63, f405-408 0.72, f409 1.",
              "In Resolve: start the clip at f358 under the logo; Opacity (or Color page Gain) keyframes with Hold "
              "(static) interpolation on those frames. To show only the lights first, key a high Lift-down / "
              "Gamma-down (or a Luma key on the brightest parts) for f358-361."]),
    "dip-to-black": dict(
        title="Dip to black", events=["E047"], quote=["E047"], refs=[3168, 3175, 3180, 3190],
        text=["f3168-3180 (00:02:06:18 - 00:02:07:05): the whole firework collage darkens at one steady rate (linear) "
              "to the video's black level (4.9 % luma) at f3180; the face panel drops out at f3173 on the beat.",
              "Then the grey clock fades in f3181-3200 (seven-segment clock recipe: opacity per frame).",
              "In Resolve: a Solid Color at the black level (0.045 grey) on the top track with Opacity keyed linearly "
              "0 -> 100 % over f3168-3180, or the Dip to Color Dissolve (13 frames) for a quick version."]),
    "jump-cut-on-beat": dict(
        title="Jump cuts on the beat", events=["E039", "E040", "E041"], quote=["E040", "E041"],
        refs=[2665, 2666, 2710, 2711],
        text=["Same framing, the subject jumps to a new pose: f2616 under an exposure flash, f2666 on a beat, f2711 "
              "on the bar line.",
              "In Resolve: blade the take where the pose changes on the beat marker and remove the frames between; "
              "hide a rough one with the exposure-flash macro."]),
    "faulty-light-strobe": dict(
        title="Faulty-light strobe", events=["E005", "E007"], quote=["E005", "E007"], refs=[347, 348, 349, 352],
        text=["The 'DON PROD' logo flickers like a faulty light, 1-2 frames per state (E007, visual): f347 dim, f348 "
              "off, f349 on, f350 half, f351 on, f352 dim, f353-354 on, f355 off, f356 dim, f357 on, f358 dim.",
              "Measured brightness of the logo (test_4am 'logo_strobe', 1 = normal): f340-342 0.98, f343-344 1.02, "
              "f345-346 1.1, f347 0.44, f348 0.16, f349 1.1, f350 0.94, f351 1.1, f352 0.51, f353 1.1, f354 1.09, "
              "f355 0.48, f356 0.95, f357 0.77, f358 0.32, f359 0.58, f360 0.05, f361 0.",
              "In Resolve: Opacity keyframes with Hold interpolation (values above 1 = a Gain boost on the Color page)."]),
}


# ================================================================================================= reference frames
REF_SRC = LAB / "refs" / "NEMZZZ - 4AM [OFFICIAL VIDEO] [VLDJ_-wrwj8].mp4"
WORK = REF / "inspect" / "library_test"         # test plates, frame cache, render scratch (not part of the library)


def ref_sha_ok() -> bool:
    """The reference is only read; its SHA-256 must still be the one the analysis recorded."""
    from motionlab.util import sha256_file
    want = json.loads((REF / "events.json").read_text(encoding="utf-8"))["source"]["sha256"]
    return sha256_file(REF_SRC) == want


def grab(frames) -> dict:
    """Exact frames of the 4AM reference at 1520 x 1080 (BGR), decoded once in display order (frame index = decode
    order, like the analysis) and cached as PNG in WORK\\frames."""
    import cv2
    cache = WORK / "frames"
    cache.mkdir(parents=True, exist_ok=True)
    out, need = {}, set()
    for f in sorted(set(int(x) for x in frames)):
        p = cache / f"f{f:05d}.png"
        if p.exists():
            out[f] = cv2.imread(str(p), cv2.IMREAD_COLOR)
        else:
            need.add(f)
    if need:
        if not ref_sha_ok():
            raise SystemExit(f"STOP: {REF_SRC.name} changed since the analysis (SHA-256 differs) - not reading it")
        print(f"  decoding {len(need)} frame(s) of the reference (read-only) ...", flush=True)
        last = max(need)
        for i, fr in iter_frames(REF_SRC, 1520, 1080):
            if i in need:
                out[i] = fr.copy()
                cv2.imwrite(str(cache / f"f{i:05d}.png"), fr)
            if i >= last:
                break
        if not ref_sha_ok():
            print(f"WARNING: {REF_SRC.name} SHA-256 changed during the read - tell the user", flush=True)
    return out


def copy_refs(slug: str, frames: list) -> list:
    """Reference frames for the recipe: library\\<slug>\\ref_fNNNNN.jpg, 960 px wide, labelled frame + timecode."""
    import cv2
    out, todo = [], []
    for f in frames:
        dst = LIB / slug / f"ref_f{f:05d}.jpg"
        out.append((f, dst.name))
        if not dst.exists():
            todo.append(f)
    if todo:
        got = grab(todo)
        for f in todo:
            im = cv2.resize(got[f], (960, 682), interpolation=cv2.INTER_AREA)
            cv2.rectangle(im, (0, 0), (300, 26), (18, 18, 20), -1)
            cv2.putText(im, f"4AM f{f} ({tc(f)})", (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 196, 255), 1,
                        cv2.LINE_AA)
            cv2.imwrite(str(LIB / slug / f"ref_f{f:05d}.jpg"), im, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return out


# ================================================================================================= recipes
def _events() -> dict:
    p = REF / "events.json"
    return {e["id"]: e for e in json.loads(p.read_text(encoding="utf-8"))["events"]} if p.exists() else {}


def _verdicts() -> dict:
    p = REF / "feedback" / "verdicts.json"
    return json.loads(p.read_text(encoding="utf-8")).get("events", {}) if p.exists() else {}


def _lessons() -> dict:
    p = LAB / ".claude" / "skills" / "analyze-reference" / "lessons.md"
    out = {}
    if p.exists():
        cur = None
        for ln in p.read_text(encoding="utf-8").splitlines():
            if ln.startswith("- [L"):
                cur = ln[3:7]
                out[cur] = ln.split(") ", 1)[-1].strip()
            elif ln.strip().startswith(("Why:", "Config:")):
                cur = None
            elif cur and ln.startswith("  "):
                out[cur] += " " + ln.strip()
    return out


VERDICT = {"correct": "you marked it Correct", "partly": "you marked it Partly - corrected with your note",
           "wrong": "you marked it Wrong"}


def recipe(slug: str, meta: dict, macros: list, evs: dict, verdicts: dict, lessons: dict, check: dict) -> str:
    L = [f"# {meta['title']}", "",
         f"MotionLab library, version 1 ({time.strftime('%Y-%m-%d')}), learned from {REF_NAME}. Frames are 0-based "
         "at 25 fps, timecode HH:MM:SS:FF with f0 = 00:00:00:00 (a Resolve timeline starting at 01:00:00:00 adds an "
         "hour).", ""]
    if meta.get("note"):
        L += [f"> {meta['note']}", ""]
    if macros:
        for fx in macros:
            L.append(f"**Macro `{fx.slug_file}.setting`** ({fx.macro_name}, {len(fx.c.tools)} nodes) - "
                     f"{KIND_TEXT[fx.kind]}")
        L += ["", "Install: copy the .setting into `%APPDATA%\\Blackmagic Design\\DaVinci Resolve\\Support\\Fusion\\"
              "Templates\\Edit\\" + ("Titles" if macros[0].kind == "title" else "Effects") + "` and restart Resolve"
              + (" (a Fusion-page macro: `...\\Fusion\\Macros`)" if macros[0].kind == "fusion" else "")
              + ", or paste the file's text into the Fusion page (Ctrl+V).", ""]
    else:
        L += ["**No macro** - Resolve's own tools do this; the steps are below.", ""]
    ids = meta.get("events", [])
    if ids:
        L += ["## Where it comes from (4AM)", ""]
        for eid in ids:
            e = evs.get(eid)
            if not e:
                continue
            f = e["final"]
            v = (verdicts.get(eid) or {}).get("v")
            tag = "false alarm in the analysis, part of the context" if f.get("false_alarm") else f.get("type", "")
            L.append(f"- **{eid}** {tag}: {f.get('duration_text') or ftc(e['start'], e['end'])}"
                     + (f" - {VERDICT[v]}" if v in VERDICT else ""))
        for eid in meta.get("quote", []):
            e = evs.get(eid)
            if e:
                L += ["", f"> **{eid}** (the reviewed description): {e['final']['what']}"]
        L.append("")
    if meta.get("measured"):
        L += ["## Measured", ""] + [f"- {x}" for x in meta["measured"]] + [""]
    if meta.get("text"):
        L += ["## How", ""] + [f"- {x}" for x in meta["text"]] + [""]
    for fx in macros:
        L += [f"## Controls ({fx.slug_file}.setting)", "", "| Control | Default |", "|---|---|"]
        for iid, tool, inp, label, extra in fx.exposed(main=False):
            t = next(t for t in fx.c.tools if t.name == tool)
            name = label or (t.controls.get(inp, {}).get("LINKS_Name")) or iid
            v = (extra or {}).get("Default", t.inputs.get(inp))
            if isinstance(v, tuple):
                v = " / ".join(f"{x:g}" for x in v)
            elif isinstance(v, float):
                v = f"{v:g}"
            elif not isinstance(v, (int, str)):
                v = "(image input)" if inp in ("Foreground", "Background", "Input") else "-"
            L.append(f"| {name} | {v} |")
        L.append("")
    if meta.get("presets"):
        L += ["## Presets (4AM values)", ""] + [f"- **{n}:** {v}" for n, v in meta["presets"]] + [""]
    if meta.get("without"):
        L += ["## Without the macro", ""] + [f"- {x}" for x in meta["without"]] + [""]
    if meta.get("lessons"):
        L += ["## Learned from your feedback", ""] + [f"- **{k}:** {lessons.get(k, '')}" for k in meta["lessons"]]
        L.append("")
    refs = meta.get("_refs", [])
    if refs:
        L += ["## Reference frames (4AM)", ""] + [f"![f{f} ({tc(f)})]({name})" for f, name in refs] + [""]
    if macros:
        L += ["## Check in DaVinci Resolve", ""]
        if check:
            L += [f"Rendered in DaVinci Resolve {check.get('resolve', '')} on {check.get('date', '')} by "
                  "`tools\\library.py test` (a throwaway project, deleted afterwards). Left of each pair: the macro "
                  "(test frame + timecode from the clip start); right: the real 4AM frame where there is one.", ""]
            L += [f"- {x}" for x in check.get("notes", [])] + ["", "![check](check.png)", ""]
        else:
            L += ["Not rendered yet: run `.venv\\Scripts\\python tools\\library.py test` with DaVinci Resolve Studio "
                  "open.", ""]
    return "\n".join(L)


def build(only: list | None = None) -> list:
    evs, verdicts, lessons = _events(), _verdicts(), _lessons()
    LIB.mkdir(exist_ok=True)
    checks = _load_checks()
    done = []
    todo = {f for s, m in {**META, **RECIPE_ONLY}.items() if not only or s in only for f in m.get("refs", [])
            if not (LIB / s / f"ref_f{f:05d}.jpg").exists()}
    if todo:
        grab(todo)                                   # one decode pass for every missing reference frame
    for slug, meta in {**META, **RECIPE_ONLY}.items():
        if only and slug not in only:
            continue
        (LIB / slug).mkdir(exist_ok=True)
        macros = []
        for stem, (folder, builder) in MACROS.items():
            if folder == slug:
                fx = builder()
                fx.slug_file = stem
                (LIB / slug / f"{stem}.setting").write_text(fx.setting(), encoding="utf-8")
                macros.append(fx)
        meta["_refs"] = copy_refs(slug, meta.get("refs", []))
        (LIB / slug / f"{slug}.md").write_text(recipe(slug, meta, macros, evs, verdicts, lessons,
                                                      checks.get(slug, {})), encoding="utf-8")
        done.append(slug)
        print(f"  {slug:22s} " + (", ".join(f"{fx.slug_file}.setting ({len(fx.c.tools)} nodes)" for fx in macros)
                                  or "recipe only"))
    index = ["# MotionLab effect library", "",
             f"Built {time.strftime('%Y-%m-%d %H:%M')} by `tools\\library.py build` from {REF_NAME} (the reviewed "
             "analysis + your feedback) and the test_4am rebuild. One folder per effect: the recipe (.md: where it "
             "comes from with frame numbers, measured values, controls, presets, how to do it without the macro), the "
             "Fusion macro (.setting) where a macro helps, 4AM reference frames, and check.png (the macro rendered "
             "in DaVinci Resolve next to the real 4AM frame).", "",
             "| Effect | Macro | Kind | Checked in Resolve |", "|---|---|---|---|"]
    for slug, meta in {**META, **RECIPE_ONLY}.items():
        stems = [s for s, (folder, _) in MACROS.items() if folder == slug]
        kinds = {MACRO_KIND.get(s, "") for s in stems}
        ck = checks.get(slug, {})
        index.append(f"| [{meta['title']}]({slug}/{slug}.md) | "
                     + (", ".join(f"[{s}.setting]({slug}/{s}.setting)" for s in stems) or "- (recipe)") + " | "
                     + (", ".join(sorted(kinds)) or "-") + " | "
                     + (("yes, " + ck.get("date", "")) if ck.get("ok") else ("FAILED - see the recipe" if ck else
                                                                            ("-" if not stems else "not yet")))
                     + " |")
    index += ["", "**Install the macros** (Resolve must be restarted afterwards): titles go to "
              "`%APPDATA%\\Blackmagic Design\\DaVinci Resolve\\Support\\Fusion\\Templates\\Edit\\Titles`, effects to "
              "`...\\Templates\\Edit\\Effects`, the Fusion-page macro (pan board) to `...\\Support\\Fusion\\Macros`. "
              "Claude asks before writing there.", "",
              "Rebuild this folder: `.venv\\Scripts\\python tools\\library.py build`; check every macro in Resolve: "
              "`... library.py test`; a pixel title with your own text: `... library.py title \"YOUR TEXT\"`."]
    (LIB / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    return done


def _load_checks() -> dict:
    p = WORK / "checks.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


# ================================================================================================= Resolve test
def loader(c: Comp, path: Path, name: str) -> str:
    """A still image as a Loader held at frame 0 (= resolve_build.still_image, verified on Resolve 21.1)."""
    ld = c.add("Loader", name, extra=(f"\t\t\tClips = {{ Clip {{ ID = \"Clip1\", Filename = {json.dumps(str(path))}, "
                                      f"FormatID = \"TiffFormat\", StartFrame = -1, Length = 1, "
                                      f"LengthSetManually = true, TrimIn = 0, TrimOut = 0, ExtendFirst = 0, "
                                      f"ExtendLast = 0, Loop = 1, AspectMode = 0, Depth = 0, TimeCode = 0, "
                                      f"GlobalStart = 0, GlobalEnd = 0, }}, }},\n"),
               HoldLastFrame=100000)
    return c.add("TimeStretcher", f"{name}_frame0", Input=Conn(ld), SourceTime=0.0, InterpolateBetweenFrames=0)


def plate(f) -> Path:
    """A 16-bit TIFF of 4AM frame f (or 'grey' = the video's black level 0.045) for the Loader."""
    import cv2
    d = WORK / "plates"
    d.mkdir(parents=True, exist_ok=True)
    p = d / (f"plate_f{f:05d}.tif" if f != "grey" else "plate_grey.tif")
    if not p.exists():
        im = np.full((1080, 1520, 3), 11, np.uint8) if f == "grey" else grab([f])[f]
        cv2.imwrite(str(p), im.astype(np.uint16) * 257)
    return p


# (macro, label, test frames from the clip start, control overrides {tool: {input: value}}, plate frame,
#  real 4AM frames to show next to the test frames, history = render as one contiguous range (particles))
CASES = [
    ("exposure-flash", "E039 k 0.65, input f2615", [0], {"Expo": {"FlashLift": 0.65}}, 2615, [2616], False),
    ("exposure-flash", "E034 k 0.58, input f2265", [0], {"Expo": {"FlashLift": 0.58}}, 2265, [2266], False),
    ("exposure-flash", "E016 k 0.79, input f1422", [0], {"Expo": {"FlashLift": 0.79}}, 1422, [1423], False),
    ("exposure-flash", "E014 flat 0.88, input f1328", [0], {"Expo": {"Flat": 1.0}}, 1328, [1329], False),
    ("exposure-flash", "E011 k 0.83, input f707", [0], {"Expo": {"FlashLift": 0.83, "Softness": 0.0}}, 707, [706],
     False),
    ("seven-segment-clock", "big clock 3:59, Size 1.71", [0], {"Place": {"Size": 1.713, "Center": (765 / 1520, 0.5)}},
     None, [3200], False),
    ("seven-segment-clock", "intro clock 3:59, Size 0.72", [0],
     {"Place": {"Size": 0.723, "Center": (382 / 1520, 1 - 891 / 1080)}}, None, [300], False),
    ("seven-segment-clock-led", "red LED card 04:00, Size 1.12", [0],
     {"Place": {"Size": 1.12, "Center": (764 / 1520, 0.5)}}, None, [3560], False),
    ("pixel-title", "LOCKED IN", [0], {"Place": {"Center": (0.5, 1 - 536 / 1080)}}, None, [10], False),
    ("firework-burst", "firework 1", [1, 6, 14, 30], {"Place": {"Center": (530 / 1520, 1 - 470 / 1080)}}, None,
     [3077, 3082, 3090, 3106], True),
    ("film-grain", "grain on black level", [0], {}, "grey", None, False),
    ("film-grain", "grain on f2615", [0], {}, 2615, None, False),
    ("pan-board", "pan 1 (396 f)", [0, 99, 198, 297, 395], {"Board": {"Width": 4528}, "Ctl": {"To": 0.664,
                                                                                              "Frames": 396}},
     None, None, False),
    ("mosaic-zoom", "4AM zoom (308 f), input f3530", [0, 40, 77, 154, 231, 307],
     {"Zoom": {"TileX": 0.5, "TileY": 1 - 468 / 1080}}, 3530, [3223, 3263, 3300, 3377, 3454, 3530], False),
    ("flashlight-flicker", "random holds", [0, 2, 4, 6, 8, 10], {}, 1613, None, False),
    ("flashlight-flicker", "4AM hall pattern", [8, 30, 54, 70, 130, 160], {"Ambient": {"Pattern": 1}}, 1613,
     [1493, 1515, 1539, 1555, 1615, 1645], False),
    ("slow-drift", "test_4am drift, input f1424", [0, 13, 26], {}, 1424, None, False),
]
PANEL_PLATES = (520, 1400, 2430, 3090)


def test_comp(stem: str, overrides: dict, plate_path: Path | None) -> tuple:
    folder, builder = MACROS[stem]
    fx = builder()
    for tool, ins in overrides.items():
        t = next(x for x in fx.c.tools if x.name == tool)
        t.inputs.update(ins)
    harness = Comp(fps=FPS, width=1520, height=1080)
    if fx.kind == "effect":
        src = loader(harness, plate_path, "Plate")
        next(x for x in fx.c.tools if x.name == fx.first).inputs[fx.first_input] = Conn(src)
    if fx.kind == "fusion":                          # pan board: four panels
        for i, f in enumerate(PANEL_PLATES, 1):
            src = loader(harness, plate(f), f"Panel{i}Plate")
            next(x for x in fx.c.tools if x.name == f"Panel{i}").inputs["Foreground"] = Conn(src)
    block = fx.c.macro_block(fx.macro_name, fx.exposed(), [("MainOutput1", fx.last, "Output")])
    # Fusion stores connections across a group / macro boundary between the real tools (the plate -> the macro's
    # first tool above; the macro's last tool -> MediaOut1 here). A reference to the macro's own output
    # ("ML_x.MainOutput1") is dropped on import (measured on Resolve 21.1): MediaOut1 had no input, the job failed.
    text = ("Composition {\n\tTools = ordered() {\n" + harness.tools_text() + block
            + f"\t\tMediaOut1 = Saver {{\n\t\t\tInputs = {{\n\t\t\t\tInput = Input {{ SourceOp = "
              f"\"{fx.last}\", Source = \"Output\", }},\n\t\t\t\tIndex = Input {{ Value = \"0\", }},\n"
              "\t\t\t},\n\t\t},\n"
            + "\t},\n\tPrefs = { Comp = { FrameFormat = { Rate = 25, Width = 1520, Height = 1080, }, }, },\n}\n")
    return fx, text


def look(cur, before) -> dict | None:
    """media.flash_look at the analysis size (640 px wide), so the numbers compare with the 4AM evidence."""
    import cv2
    from motionlab.media import flash_look
    from motionlab.util import load_config
    g = [cv2.resize(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), (640, 454), interpolation=cv2.INTER_AREA).astype(np.float32)
         for x in (cur, before)]
    return flash_look(g[0], g[1], load_config()["flash"])


def test(only: list | None = None) -> int:
    import cv2
    import resolve_build as rb
    cases = [c for c in CASES if not only or c[0] in only or MACROS[c[0]][0] in only]
    if not cases:
        raise SystemExit(f"no test for {only}; macros: {', '.join(MACROS)}")
    run = WORK / "run"
    shutil.rmtree(run, ignore_errors=True)
    (run / "frames").mkdir(parents=True)
    reals = sorted({f for c in cases for f in (c[5] or [])} | {c[4] for c in cases if isinstance(c[4], int)}
                   | {c[5][0] - 1 for c in cases if c[0] == "exposure-flash"} | set(PANEL_PLATES))
    real = grab(reals)
    print("connecting to DaVinci Resolve ...", flush=True)
    r = rb.connect(120)
    ver = r.GetVersionString()
    pm = r.GetProjectManager()
    cur = pm.GetCurrentProject()
    back = cur.GetName() if cur else None
    if cur:
        pm.SaveProject()
    if back == "motionlab_scratch":
        back = "test_4am"
    if "motionlab_scratch" in (pm.GetProjectListInCurrentFolder() or []):
        if cur and cur.GetName() == "motionlab_scratch":
            pm.CloseProject(cur)
        pm.DeleteProject("motionlab_scratch")
    p = pm.CreateProject("motionlab_scratch")
    if not p:
        raise SystemExit("Resolve refused to create the scratch project 'motionlab_scratch'")
    results, slots = {}, []
    try:
        for k, v in (("timelineResolutionWidth", "1520"), ("timelineResolutionHeight", "1080"),
                     ("timelineFrameRate", "25")):
            p.SetSettings({k: v})                    # one key per call (a combined call froze Resolve 21.1)
        mp = p.GetMediaPool()
        carrier = LAB / "projects" / "test_4am" / "build" / "resolve" / "media" / "carrier_bg_1520x1080_25fps.mov"
        car = mp.ImportMedia([str(carrier)])[0]
        tl = mp.CreateEmptyTimeline("library_test")
        p.SetCurrentTimeline(tl)
        tl.SetStartTimecode("00:00:00:00")
        at = 0
        for i, (stem, label, frames, ov, pf, rf, hist) in enumerate(cases):
            fx, text = test_comp(stem, ov, plate(pf) if pf is not None else None)
            n = max(frames) + 1
            cp = run / f"case{i:02d}_{stem}.comp"
            cp.write_text(text, encoding="utf-8")
            it = mp.AppendToTimeline([{"mediaPoolItem": car, "startFrame": at, "endFrame": at + n, "trackIndex": 1,
                                       "recordFrame": at, "mediaType": 1}])[0]
            ok = bool(it.ImportFusionComp(str(cp)))
            slots.append(dict(i=i, stem=stem, label=label, frames=frames, at=at, ok=ok, pf=pf, rf=rf, hist=hist))
            print(f"  case {i:2d} {stem:24s} {label:30s} timeline f{at}-{at + n - 1}: import "
                  f"{'ok' if ok else 'FAILED'}", flush=True)
            at += n
        p.SetCurrentRenderMode(1)
        codecs = p.GetRenderCodecs("tif") or {}
        codec = next((c for d, c in codecs.items() if "16" in d or "16" in c), None) or next(iter(codecs.values()))
        if not p.SetCurrentRenderFormatAndCodec("tif", codec):
            raise SystemExit(f"Resolve refused TIFF / {codec}")
        jobs = []
        for s in slots:
            spans = [(min(s["frames"]), max(s["frames"]))] if s["hist"] else [(f, f) for f in s["frames"]]
            for a, b in spans:
                name = f"c{s['i']:02d}_{a:04d}"
                for k, v in (("MarkIn", s["at"] + a), ("MarkOut", s["at"] + b), ("TargetDir", str(run / "frames")),
                             ("CustomName", name), ("ExportVideo", True), ("ExportAudio", False)):
                    p.SetRenderSettings({k: v})
                jobs.append((p.AddRenderJob(), s, a, name))
        print(f"rendering {len(jobs)} job(s) ({codec}) ...", flush=True)
        t0 = time.time()
        p.StartRendering([j for j, *_ in jobs], False)
        while True:
            time.sleep(1)
            # scripting objects can drop out while Resolve renders: re-fetch instead of exiting (an exiting client
            # makes Resolve abort the render) - the same as resolve_build.Session.render
            try:
                busy = p.IsRenderingInProgress()
            except (TypeError, AttributeError):
                time.sleep(4)
                r = rb.connect(60)
                pm = r.GetProjectManager()
                p = pm.GetCurrentProject()
                continue
            if not busy:
                break
            if time.time() - t0 > 1800:
                p.StopRendering()
                raise SystemExit("render took longer than 30 min - stopped")
        print(f"render done in {time.time() - t0:.0f}s", flush=True)
        for jid, s, a, name in jobs:
            st = p.GetRenderJobStatus(jid) or {}
            if st.get("JobStatus") != "Complete":
                # a failed comp still leaves files: Resolve writes stale frames of other comps (seen on 21.1)
                s.setdefault("status", []).append(f"{st.get('JobStatus', '?')}: {st.get('Error', '')}".strip(": "))
                continue
            files = sorted((run / "frames").glob(f"{name}*.tif"))
            for k, fp in enumerate(files):
                im = cv2.imread(str(fp), cv2.IMREAD_UNCHANGED)
                if im is None:
                    continue
                if im.dtype == np.uint16:
                    im = np.round(im.astype(np.float32) / 257.0).clip(0, 255).astype(np.uint8)
                im = im[..., :3]
                f = a + k
                if f in s["frames"]:
                    s.setdefault("out", {})[f] = im
            s.setdefault("status", []).append(st.get("JobStatus", "?"))
    finally:
        try:
            pm.SaveProject()
            pm.CloseProject(p)
            pm.DeleteProject("motionlab_scratch")
        except Exception as e:                      # noqa: BLE001
            print("note: could not delete the scratch project:", e)
        if back and back in (pm.GetProjectListInCurrentFolder() or []):
            pm.LoadProject(back)
    # ---- sheets + numbers per library folder
    checks = _load_checks()
    by_folder: dict[str, list] = {}
    for s in slots:
        by_folder.setdefault(MACROS[s["stem"]][0], []).append(s)
    date = time.strftime("%Y-%m-%d")
    for folder, ss in by_folder.items():
        tiles, notes, ok_all = [], [], True
        for s in ss:
            outs = s.get("out", {})
            ok = s["ok"] and len(outs) == len(s["frames"]) and all(x == "Complete" for x in s.get("status", []))
            ok_all &= ok
            if not ok:
                notes.append(f"{s['stem']} '{s['label']}': FAILED (import {'ok' if s['ok'] else 'failed'}, "
                             f"{len(outs)}/{len(s['frames'])} frames rendered; "
                             f"{'; '.join(sorted(set(s.get('status', []))))})")
            for j, f in enumerate(s["frames"]):
                if f not in outs:
                    continue
                pair = [(outs[f], f"{s['label']}: f{f} ({tc(f)})")]
                rf = (s["rf"] or [None] * len(s["frames"]))[j]
                if rf is not None:
                    pair.append((real[rf], f"4AM f{rf} ({tc(rf)})"))
                tiles.append(pair)
            note = measure(s, real)
            if note:
                notes.append(note)
        if tiles:
            cv2.imwrite(str(LIB / folder / "check.png"), sheet(tiles))
        checks[folder] = {"ok": ok_all, "date": date, "resolve": ver, "notes": notes}
        print(f"  {folder:22s} {'OK' if ok_all else 'FAILED'}  " + " | ".join(notes))
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "checks.json").write_text(json.dumps(checks, indent=1), encoding="utf-8")
    shutil.rmtree(run / "frames", ignore_errors=True)
    build([f for f in by_folder])                    # recipes now show the check
    return 0 if all(c.get("ok") for f, c in checks.items() if f in by_folder) else 1


ROI = {"intro clock 3:59, Size 0.72": (0, 700, 760, 1080)}     # x0, y0, x1, y1 compared (the clock's panel)


def measure(s: dict, real: dict) -> str:
    """One line of numbers per test case (what the user can verify on check.png)."""
    outs = s.get("out", {})
    if not outs:
        return ""
    stem, label = s["stem"], s["label"]
    f0 = s["frames"][0]
    o = outs.get(f0)
    if stem == "exposure-flash" and o is not None:
        rf = s["rf"][0]
        a, b = look(o, real[s["pf"]]), look(real[rf], real[rf - 1])      # each against the frame before its flash
        fmt = (lambda lk: f"{lk['level_pct']}% texture {lk['texture']}" if lk else "no flash measured")
        return f"{label}: macro {fmt(a)} / real 4AM {fmt(b)}"
    if stem == "film-grain" and o is not None:
        import cv2
        g = cv2.cvtColor(o, cv2.COLOR_BGR2GRAY).astype(np.float32)
        if s["pf"] == "grey":
            return (f"{label}: noise std {g[100:980, 100:1420].std():.2f} levels (lab grain at full size: "
                    f"{0.010 * 0.625 * 255:.2f})")
        base = cv2.cvtColor(real[s["pf"]], cv2.COLOR_BGR2GRAY).astype(np.float32)
        return f"{label}: mean change {float((g - base).mean()):+.2f} levels, std of the change {float((g - base).std()):.2f}"
    if stem == "flashlight-flicker":
        import cv2
        lv = []
        for f in s["frames"]:
            if f in outs:
                lv.append(f"f{f} {cv2.cvtColor(outs[f], cv2.COLOR_BGR2GRAY).mean() * 100 / 255:.1f}%")
        return f"{label}: luma " + ", ".join(lv)
    if stem in ("seven-segment-clock", "seven-segment-clock-led", "pixel-title") and o is not None and s["rf"]:
        import cv2
        r = real[s["rf"][0]]
        x0, y0, x1, y1 = ROI.get(label, (0, 0, 1520, 1080))       # the intro clock shares its frame with panels
        # strokes = the brightest channel above 100 (grey digits and red LED / title letters alike)
        core = (lambda x: x[y0:y1, x0:x1].max(axis=2).astype(np.float32))
        gm, gr = core(o), core(r)
        bo, br = np.argwhere(gm > 100), np.argwhere(gr > 100)
        if len(bo) and len(br):
            ho, hr = int(np.ptp(bo[:, 0])) + 1, int(np.ptp(br[:, 0])) + 1
            wo, wr = int(np.ptp(bo[:, 1])) + 1, int(np.ptp(br[:, 1])) + 1
            return (f"{label}: strokes {wo}x{ho} px (4AM {wr}x{hr}), stroke level {gm[gm > 100].mean() * 100 / 255:.0f}% "
                    f"(4AM {gr[gr > 100].mean() * 100 / 255:.0f}%)")
    return ""


def sheet(tiles: list):
    """Rows of [macro | real] pairs, 2 pairs per row, labelled."""
    import cv2
    tw, th = 456, 324
    cells = []
    for pair in tiles:
        row = []
        for im, lab in pair:
            t = cv2.resize(im, (tw, th), interpolation=cv2.INTER_AREA)
            t = cv2.copyMakeBorder(t, 24, 2, 2, 2, cv2.BORDER_CONSTANT, value=(18, 18, 20))
            cv2.putText(t, lab[:58], (5, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                        (0, 196, 255) if not lab.startswith("4AM") else (200, 200, 200), 1, cv2.LINE_AA)
            row.append(t)
        if len(row) == 1:
            row.append(np.full_like(row[0], 18))
        cells.append(np.hstack(row))
    blank = np.full_like(cells[0], 40)
    rows = [np.hstack([cells[i], np.full((cells[0].shape[0], 12, 3), 40, np.uint8),
                       cells[i + 1] if i + 1 < len(cells) else blank]) for i in range(0, len(cells), 2)]
    return np.vstack(rows)


def title_variant(text: str) -> Path:
    fx = fx_pixel_title(text, "pixel-title")
    d = LIB / "pixel-title" / "variants"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{''.join(ch if ch.isalnum() else '_' for ch in text.strip())}.setting"
    p.write_text(fx.setting(), encoding="utf-8")
    return p


# ================================================================================================= install into Resolve
# Resolve reads Edit-page templates from Support\Fusion\Templates\Edit\{Titles,Effects} (subfolders = categories) and
# Fusion-page macros from Support\Fusion\Macros, at start-up. Everything goes into MotionLab subfolders, with readable
# names ("ML ..."), so the user's own templates and macros are never touched; library\installed.json records each
# file (sha1) and the folders this created - `uninstall` removes exactly those.
FUSION_USER = Path(os.environ.get("APPDATA", "")) / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Fusion"
INSTALL_DIRS = {"title": ("Templates", "Edit", "Titles", "MotionLab"),
                "effect": ("Templates", "Edit", "Effects", "MotionLab"),
                "fusion": ("Macros", "MotionLab")}
INSTALLED = LIB / "installed.json"
RESOLVE_EXE = Path(r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe")


def display_name(fx: Fx) -> str:
    return f"ML {fx.name}"


def thumbnail(folder: str, dst: Path) -> bool:
    """A 16:9 thumbnail (320 x 180) of the macro as Resolve rendered it: the first macro tile of check.png."""
    import cv2
    chk = LIB / folder / "check.png"
    if not chk.exists():
        return False
    tile = cv2.imread(str(chk))[24:24 + 324, 2:2 + 456]            # sheet(): [macro | real], macro first
    h = 456 * 9 // 16
    y0 = (324 - h) // 2
    cv2.imwrite(str(dst), cv2.resize(tile[y0:y0 + h], (320, 180), interpolation=cv2.INTER_AREA))
    return True


def install(only: list | None = None) -> list:
    import hashlib
    if not FUSION_USER.exists():
        raise SystemExit(f"DaVinci Resolve's Fusion folder not found: {FUSION_USER}")
    rec = json.loads(INSTALLED.read_text(encoding="utf-8")) if INSTALLED.exists() else {}
    files = {f["dst"]: f for f in rec.get("files", [])}
    created = list(rec.get("created_dirs", []))
    items = [(stem, folder, builder, LIB / folder / f"{stem}.setting", None) for stem, (folder, builder) in MACROS.items()]
    for v in sorted((LIB / "pixel-title" / "variants").glob("*.setting")):         # library.py title "TEXT"
        items.append(("pixel-title", "pixel-title", fx_pixel_title, v, f"ML Pixel Title - {v.stem}"))
    done = []
    for stem, folder, builder, src, name in items:
        if only and stem not in only and folder not in only:
            continue
        if not src.exists():
            raise SystemExit(f"{src} is missing - run library.py build first")
        fx = builder()
        d = FUSION_USER.joinpath(*INSTALL_DIRS[fx.kind])
        for k in range(len(INSTALL_DIRS[fx.kind]), 0, -1):          # remember the folders this creates
            p = FUSION_USER.joinpath(*INSTALL_DIRS[fx.kind][:k])
            if not p.exists() and str(p) not in created:
                created.append(str(p))
        d.mkdir(parents=True, exist_ok=True)
        dst = d / f"{name or display_name(fx)}.setting"
        shutil.copy2(src, dst)
        png = dst.with_suffix(".png")
        files[str(dst)] = {"stem": stem, "kind": fx.kind, "src": str(src), "dst": str(dst),
                           "sha1": hashlib.sha1(dst.read_bytes()).hexdigest(),
                           "png": str(png) if thumbnail(folder, png) else None}
        done.append(dst)
        print(f"  {fx.kind:6s} {dst}")
    INSTALLED.write_text(json.dumps({"installed": time.strftime("%Y-%m-%d %H:%M"), "fusion_root": str(FUSION_USER),
                                     "files": sorted(files.values(), key=lambda f: f["dst"]),
                                     "created_dirs": sorted(created, key=len, reverse=True),
                                     "how": "library.py uninstall removes exactly these files and, when empty, "
                                            "the folders this created"}, indent=1), encoding="utf-8")
    return done


def uninstall() -> int:
    import hashlib
    if not INSTALLED.exists():
        print("nothing installed (no library\\installed.json)")
        return 0
    rec = json.loads(INSTALLED.read_text(encoding="utf-8"))
    kept = []
    for f in rec.get("files", []):
        p = Path(f["dst"])
        if p.exists() and hashlib.sha1(p.read_bytes()).hexdigest() != f["sha1"]:
            kept.append(str(p))                                     # changed since: the user's now
            continue
        for q in (p, Path(f["png"]) if f.get("png") else None):
            if q and q.exists() and "MotionLab" in q.parts:
                q.unlink()
                print("  removed", q)
    for d in rec.get("created_dirs", []):                         # deepest first
        p = Path(d)
        if p.exists() and not any(p.iterdir()):
            p.rmdir()
            print("  removed empty folder", p)
    if kept:
        print("kept (changed since the install):", *kept, sep="\n  ")
    INSTALLED.unlink()
    return 0


def verify_install() -> int:
    """End-to-end check in DaVinci Resolve: each installed TITLE template is inserted by name into a throwaway
    timeline (Timeline.InsertFusionTitleIntoTimeline) and one frame rendered; effects and the Fusion macro have no
    scripting entry point - their folders are checked against Fusion's own path map instead."""
    import subprocess
    import cv2
    import resolve_build as rb
    rec = json.loads(INSTALLED.read_text(encoding="utf-8"))
    started = False
    if not any("Resolve.exe" in ln for ln in subprocess.run(["tasklist", "/FI", "IMAGENAME eq Resolve.exe"],
                                                            capture_output=True, text=True).stdout.splitlines()):
        print("starting DaVinci Resolve (it reads templates at start-up) ...", flush=True)
        subprocess.Popen([str(RESOLVE_EXE)])
        started = True
    r = rb.connect(300)
    fu = r.Fusion()
    paths = {k: fu.MapPath(k) for k in ("Templates:", "Macros:")} if fu else {}
    print("Fusion path map:", paths)
    pm = r.GetProjectManager()
    cur = pm.GetCurrentProject()
    back = cur.GetName() if cur else None
    if cur:
        pm.SaveProject()
    if back == "motionlab_scratch":
        back = None
    if "motionlab_scratch" in (pm.GetProjectListInCurrentFolder() or []):
        pm.DeleteProject("motionlab_scratch")
    p = pm.CreateProject("motionlab_scratch")
    out = WORK / "verify_install"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    results = {}
    try:
        for k, v in (("timelineResolutionWidth", "1520"), ("timelineResolutionHeight", "1080"),
                     ("timelineFrameRate", "25")):
            p.SetSettings({k: v})
        tl = p.GetMediaPool().CreateEmptyTimeline("verify_install")
        p.SetCurrentTimeline(tl)
        tl.SetStartTimecode("00:00:00:00")
        p.SetCurrentRenderMode(1)
        p.SetCurrentRenderFormatAndCodec("tif", "RGB16")
        for f in rec["files"]:
            if f["kind"] != "title":
                continue
            name = Path(f["dst"]).stem
            for it in tl.GetItemListInTrack("video", 1) or []:
                tl.DeleteClips([it])
            it = tl.InsertFusionTitleIntoTimeline(name)
            if not it:
                results[name] = "NOT FOUND by name (Resolve did not load the template)"
                print(f"  {name}: NOT FOUND", flush=True)
                continue
            fr = int(it.GetStart()) + (6 if f["stem"] == "firework-burst" else 0)
            for k, v in (("MarkIn", fr), ("MarkOut", fr), ("TargetDir", str(out)), ("CustomName", f["stem"]),
                         ("ExportVideo", True), ("ExportAudio", False)):
                p.SetRenderSettings({k: v})
            jid = p.AddRenderJob()
            p.StartRendering([jid], False)
            while p.IsRenderingInProgress():
                time.sleep(0.5)
            st = (p.GetRenderJobStatus(jid) or {}).get("JobStatus")
            files = sorted(out.glob(f"{f['stem']}*.tif"))
            if st != "Complete" or not files:
                results[name] = f"render {st}"
            else:
                im = cv2.imread(str(files[-1]), cv2.IMREAD_UNCHANGED)
                im = (im.astype(np.float32) / 257).round().clip(0, 255).astype(np.uint8)[..., :3]
                lit = (im.max(axis=2) > 100).mean() * 100
                results[name] = f"inserted by name and rendered: {lit:.2f} % of the frame lit (frame {fr - int(it.GetStart())})"
                cv2.imwrite(str(out / f"{f['stem']}.png"), im)
            print(f"  {name}: {results[name]}", flush=True)
    finally:
        pm.CloseProject(p)
        pm.DeleteProject("motionlab_scratch")
        if back:
            pm.LoadProject(back)
        if started:
            pm.SaveProject()
            r.Quit()
    for f in rec["files"]:
        if f["kind"] != "title":
            d = Path(f["dst"]).parent
            results[Path(f["dst"]).stem] = f"file in place ({d.relative_to(FUSION_USER)})"
    (WORK / "verify_install.json").write_text(json.dumps({"date": time.strftime("%Y-%m-%d %H:%M"), "paths": paths,
                                                          "results": results}, indent=1), encoding="utf-8")
    return 0 if all(("rendered" in v or "file in place" in v) for v in results.values()) else 1


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["build", "test", "title", "install", "uninstall", "verify-install"])
    ap.add_argument("args", nargs="*")
    a = ap.parse_args()
    if a.cmd in ("build", "test") and not (REF / "events.json").exists():
        raise SystemExit(f"library.py builds the library from the analysis of {REF_NAME} ({REF.name}), which is not on "
                         "this PC - analyse that reference first, or point REF / META at your own reference.")
    if a.cmd == "build":
        done = build(a.args or None)
        print(f"{len(done)} effects in {LIB}")
        return 0
    if a.cmd == "test":
        return test(a.args or None)
    if a.cmd == "install":
        done = install(a.args or None)
        print(f"{len(done)} macro(s) installed - restart DaVinci Resolve to see them (Titles / Effects > MotionLab)")
        return 0
    if a.cmd == "uninstall":
        return uninstall()
    if a.cmd == "verify-install":
        return verify_install()
    if not a.args:
        raise SystemExit('give the text: library.py title "MY TEXT"')
    print(title_variant(" ".join(a.args)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
