"""Captions clear of the face (0.6.0 step 21; docs\\plans.md - the user's lessons local-make-1, -23..25 moved captions
and graphics off the face by hand): in a video whose plan asks for it ("captions_fit": "chin" - the quick draft's
talking mode and Claude's talking edits set it), each shot's captions sit at least GAP px under the speaker's chin (a
punch-in moves the chin: measured per shot) and inside the safe height - upright: out of the platforms' bottom band
(precheck.SAFE_BANDS), wide: MARGIN px off the bottom (the lab's safe zone for 16:9). The
captions graphic is cut into a piece per shot (miniedit.attach_captions) and a piece that has to move gets a
"rect" offset - the graphic itself is never changed, so any captions page works. The caption's own height (its
style's "y" / "y_upright") stays when it is already clear; otherwise it moves under the chin, or
when that does not fit (a close-up), just under the mouth, over the chin - never over the eyes-to-mouth band, and
never moved up onto the forehead. Only a face its lines cross counts (a corner camera to the side does not). A shot
with no room under the mouth inside the safe height keeps its height (the build's face check then says so). A clip in
two stacked panels (0.6.1, reframe.py: two people, a screen over its face camera, a face camera over a game) has its
captions on the seam between them when that is inside the safe height and off every face's eyes-to-mouth band.

    fit_captions(plan, plan_dir) -> lines (what moved, frame + timecode); the plan is changed in place. A piece's
    "rect" set here carries "rect_fit": true and is worked out again on every build; a rect without it (set by hand)
    is left alone.
    fit_cards(plan, plan_dir) -> lines (0.6.1): the cards an edit by segments put in ("clear_face": true - a number,
    a section title, a list) moved the least way off the faces and the captions, measured once they are rendered.
    place(box, avoid, area, gap) = that move.
"""
from __future__ import annotations

import copy
import math
from pathlib import Path

from . import safezones as SZ

GAP = 40                        # px under the chin (on a 1080 short side; scaled)
BAND_TOP, BAND_BOTTOM = SZ.ZONES["all"]["top"], SZ.REF_H - SZ.ZONES["all"]["bottom"]   # an upright 1080x1920
#                                 video's safe height (motionlab\safezones: the strictest of the three apps)
MARGIN = 80                     # a wide video's safe margin at the top and the bottom (on 1080 high; scaled)
SAMPLES = 3                     # frames looked at per shot (its start, middle and end, a little in)
CHAR_W = {True: 0.62, False: 0.55}   # a character's width in em, capitals / not (a line's length, estimated)
PAD = 0.15                      # a face's box widened by this on each side (hair, chin; precheck.FACE_PAD)
KEEP_GAP = 12                   # px kept clear above and below a line of text burned into the picture (0.6.1)
CARD_ALPHA = 128                # fit_cards: a card's pixel = its renders over black and white within this (0-255)
CARD_AT = (0.35, 0.6, 0.85)     # ... measured at these shares of its length (in, held, before it goes)
EYES, MOUTH, CHIN = 0.3, 0.82, 1.0   # in a face's box (YuNet: hairline to chin, measured on the user's takes
                                     # 2026-10-26): the eyes-to-mouth band is never covered; the chin = the box's end


def _cue_size(cues: list[dict], vals: dict, W0: int) -> tuple[float, float]:
    """The tallest and the widest of these captions on the graphic (px), estimated: its lines (the words' width
    against the line width) x the text size x the line spacing, + the box's padding; the width up to the line's."""
    fs, lh = float(vals.get("font_size") or 72), float(vals.get("line_height") or 1.18)
    width = W0 * float(vals.get("max_width") or 80) / 100
    k = CHAR_W[bool(vals.get("uppercase", True))] * fs
    long = max([0] + [len(" ".join(w[0] for w in c["words"])) * k for c in cues])
    pad = vals.get("box")
    return (math.ceil(max(1.0, long) / max(1.0, width)) * fs * lh + (2 * float(vals.get("box_pad_y") or 0) if pad else 0),
            min(width, long) + (2 * float(vals.get("box_pad_x") or 0) if pad else 0))


def fit_captions(plan: dict, plan_dir: Path) -> list[str]:
    from . import miniedit as ME
    from . import overlay_settings as OS
    from .compose import Renderer, resolve_paths
    from .thumbnail import face_model, faces as find_faces
    from .timecode import frame_to_tc
    W, H, fps = int(plan.get("width") or 0), int(plan.get("height") or 0), float(plan.get("fps") or 25)
    if plan.get("captions_fit") != "chin" or not W or not H:
        return []
    if face_model() is None:
        return ["captions not fitted: no face detector (tools\\models)"]
    for L in plan.get("layers", []):                         # this fit's own offsets are worked out again
        if L.get("rect_fit"):
            L.pop("rect", None)
            L.pop("rect_fit", None)
    ME.attach_captions(plan)
    caps = [L for L in plan["layers"] if L.get("type") == "overlay" and L.get("file") and ME._is_captions(L)
            and not L.get("rect") and not L.get("over_face")]
    if not caps:
        return []
    R = resolve_paths(copy.deepcopy(plan), Path(plan_dir))
    bare = Renderer({**R, "layers": [L for L in R["layers"] if L.get("type") not in ("overlay", "text")]})
    folder_info: dict[str, tuple] = {}
    faces_at: dict[int, list] = {}
    lines = []
    for L in caps:
        folder = Path(R["layers"][plan["layers"].index(L)]["file"]).parent
        if str(folder) not in folder_info:
            try:
                st = OS.status(folder)
                folder_info[str(folder)] = (OS.values(folder), int(st.get("width") or W), int(st.get("height") or H),
                                            ME._caption_cues(folder))
            except (OSError, ValueError):
                folder_info[str(folder)] = None
        info = folder_info[str(folder)]
        if not info:
            continue
        vals, W0, H0, cues = info
        s, e, inn, sp = int(L["start"]), int(L["end"]), int(L.get("in", 0)), float(L.get("speed", 1.0))
        span = int((e - s) * sp + 1e-6)
        mine = [c for c in cues if int(c["f0"]) <= inn + span and int(c["f1"]) >= inn]
        if not mine:
            continue
        hgt, cw = _cue_size(mine, vals, W0)                     # (the graphic is drawn at its own size from 0, 0)
        boxes, n = [], e - s + 1
        for f in sorted({s + min(2, n - 1), (s + e) // 2, e - min(2, n - 1)})[:SAMPLES]:
            if f not in faces_at:
                faces_at[f] = [q for q in (find_faces(bare.render(f)) or []) if q[2] * q[3] >= 0.004 * W * H]
            boxes += [q[:4] for q in faces_at[f]]
        c0 = float(vals.get("y_upright" if H > W else "y", vals.get("y", 78)) or 78) / 100 * H0
        c, why = where(c0, hgt, cw, W0, boxes, W, H, _seam(plan, s, e, W), _burned(bare, s, e))
        if c is None:
            if why:
                lines.append(f"captions {_span(s, e, fps, frame_to_tc)}: {why} - left where they are")
            continue
        dy = int(round(c - c0))
        if abs(dy) < 2:
            continue
        L["rect"], L["rect_fit"] = [0, dy, W0, H0], True
        lines.append(f"captions {_span(s, e, fps, frame_to_tc)} {'up' if dy < 0 else 'down'} {abs(dy)} px, {why}")
    return lines


def _burned(R, s: int, e: int) -> list:
    """The text burned into the picture under frames s..e (a clip reframe.py fitted round it: its "reframe" "text"),
    in output px through the panel that shows it ([x0, y0, x1, y1]); R = the renderer of the clips."""
    from .compose import ClipLayer, to_out
    out = []
    for C in R.layers:
        tl = (C.spec.get("reframe") or {}).get("text") if isinstance(C, ClipLayer) else None
        if not tl or not (C.start <= s and C.end >= e):
            continue
        bx = C.boxes(s, R)
        if not bx:
            continue
        sw, sh = R.size(C.src)
        for b in tl:
            X0, Y0, _ = to_out(b[0], b[1], sw, sh, bx[0], C.mirror)
            X1, Y1, _ = to_out(b[2], b[3], sw, sh, bx[0], C.mirror)
            out.append([min(X0, X1), Y0, max(X0, X1), Y1])
    return out


def _seam(plan: dict, s: int, e: int, W: int) -> float | None:
    """The seam under frames s..e of a clip in two panels stacked across the whole frame (0.6.1, reframe.py: a split,
    a screen over its face camera, a face camera over a game), or None."""
    for L in plan.get("layers", []):
        ps = L.get("panels") or []
        if L.get("type") != "clip" or len(ps) != 2 or not (int(L["start"]) <= s and int(L["end"]) >= e):
            continue
        a, b = sorted(([float(v) for v in p["rect"]] for p in ps), key=lambda r: r[1])
        if a[0] == b[0] == 0 and a[2] == b[2] == W and abs(a[1] + a[3] - b[1]) < 2:
            return b[1]
    return None


def where(c0: float, hgt: float, cw: float, W0: float, boxes: list, W: int, H: int,
          seam: float | None = None, keep: list | None = None) -> tuple[float | None, str]:
    """Where a shot's captions go: their middle's height (c0 = their style's), their height and width (centred on a
    graphic W0 wide), the faces seen in the shot ([x, y, w, h]) on a W x H video -> (the new middle, why) or (None,
    why it stays: "" = already clear). seam = where two stacked panels meet (reframe.py): there first, when it
    is inside the safe height and off every face's eyes-to-mouth band. keep = text burned into the picture ([x0, y0,
    x1, y1] px, reframe.py's fit keeps it whole): kept clear like a face's eyes-to-mouth band."""
    upright = H > W
    gap = GAP * min(W, H) / 1080
    top_ok, bottom_ok = ((BAND_TOP * H / 1920, BAND_BOTTOM * H / 1920) if upright
                         else (MARGIN * H / 1080, H - MARGIN * H / 1080))
    lo, hi = top_ok + hgt / 2, bottom_ok - hgt / 2             # where its middle may be: the safe height
    x0, x1 = (W0 - cw) / 2, (W0 + cw) / 2                       # (its lines are centred)
    near = [(y + h * EYES, y + h * MOUTH, y + h * CHIN) for x, y, w, h in boxes   # the faces its lines cross (a
            if x + w * (1 + PAD) > x0 and x - w * PAD < x1]                         # corner camera to the side: no)
    texts = [(t0 + gap - KEEP_GAP, t1 - gap / 2 + KEEP_GAP, t1) for tx0, t0, tx1, t1 in keep or []
             if tx1 > x0 and tx0 < x1]                  # (a line of text: its own height, KEEP_GAP clear)
    near += texts
    if seam is not None and lo <= seam <= hi and not any(seam + hgt / 2 > e - gap and seam - hgt / 2 < m + gap / 2
                                                         for e, m, _ in near):
        return (None, "") if abs(seam - c0) < 2 else (seam, f"on the seam between the panels (y {int(seam)})")
    if not near:
        return (None, "") if c0 <= hi else (hi, "off the bottom band" if upright else "off the bottom edge")
    ey, mo, chin = min(q[0] for q in near), max(q[1] for q in near), max(q[2] for q in near)
    if (c0 - hgt / 2 >= mo + gap / 2 or c0 + hgt / 2 <= ey - gap) and lo <= c0 <= hi:
        return None, ""                                         # already off the eyes-to-mouth band
    if lo <= chin + gap + hgt / 2 <= hi:                        # under the chin first (the step's rule) ...
        what = "the text burned in" if texts and chin == max(q[2] for q in texts) else "the chin"
        return chin + gap + hgt / 2, f"under {what} (y {int(chin)})"
    if lo <= mo + gap / 2 + hgt / 2 <= hi:                      # ... a close-up: just under the mouth, over the chin
        return mo + gap / 2 + hgt / 2, f"under the mouth (y {int(mo)}; a close-up: no room under the chin)"
    if seam is not None and lo <= seam <= hi:                   # two panels (a face moving across the seam in one of
        over = lambda c: sum(max(0.0, min(c + hgt / 2, m + gap / 2) - max(c - hgt / 2, e - gap))   # noqa: E731
                             for e, m, _ in near)               # the samples): the seam when it covers the faces less
        if over(seam) < over(c0):                               # than staying would
            return seam, f"on the seam between the panels (y {int(seam)}; the least over a face)"
    return None, f"no room under the mouth (y {int(mo)}) inside the safe height"   # (never up onto the forehead)


def place(box: list, avoid: list, area: list, gap: float) -> tuple[float, float] | None:
    """A card's shift (dx, dy) to the nearest place inside `area` ([x0, y0, x1, y1]) where it covers none of `avoid`
    (boxes, gap px clear) - (0, 0) when it is clear already; None when nowhere is (a card bigger than the room). A
    move up or down costs less than one to a side (the card stays under the words it goes with)."""
    x0, y0, x1, y1 = box

    def clear(dx, dy):
        a, b, c, d = x0 + dx, y0 + dy, x1 + dx, y1 + dy
        return (a >= area[0] and b >= area[1] and c <= area[2] and d <= area[3]
                and not any(a < o[2] + gap and c > o[0] - gap and b < o[3] + gap and d > o[1] - gap for o in avoid))
    xs = {0.0, area[0] - x0, area[2] - x1} | {o[0] - gap - x1 for o in avoid} | {o[2] + gap - x0 for o in avoid}
    ys = {0.0, area[1] - y0, area[3] - y1} | {o[1] - gap - y1 for o in avoid} | {o[3] + gap - y0 for o in avoid}
    ok = [(abs(dy) + 1.5 * abs(dx), dx, dy) for dx in xs for dy in ys if clear(dx, dy)]
    return (min(ok)[1], min(ok)[2]) if ok else None


def fit_cards(plan: dict, plan_dir: Path) -> list[str]:
    """0.6.1 (Edit by segments): every overlay with "clear_face": true (the cards segments.py builds) moved off the
    faces, the captions and the cards before it, inside the safe area (upright: the platforms' bands and right rail;
    wide: MARGIN) - measured where it draws once rendered (over black and over white: its pixels at least half
    opaque, at CARD_AT of its length), the faces in the footage there (motionlab\\thumbnail.faces). Its "rect" offset
    carries "rect_fit": true (worked out again on every build); a hand-set rect is left alone. -> lines."""
    import numpy as np
    from . import miniedit as ME
    from . import overlay_settings as OS
    from .compose import Renderer, resolve_paths
    from .thumbnail import face_model, faces as find_faces
    from .timecode import frame_to_tc
    cards = [L for L in plan.get("layers", []) if L.get("type") == "overlay" and L.get("clear_face") and L.get("file")
             and not L.get("over_face") and (not L.get("rect") or L.get("rect_fit") or L.get("rect0"))]
    if not cards:
        return []
    if face_model() is None:
        return ["cards not fitted: no face detector (tools\\models)"]
    W, H, fps = int(plan["width"]), int(plan["height"]), float(plan.get("fps") or 25)
    for L in cards:                                 # (rect0 = its own place: a column card at the edge)
        L.pop("rect_fit", None)
        if L.get("rect0"):
            L["rect"] = list(L["rect0"])
        else:
            L.pop("rect", None)
    R = resolve_paths(copy.deepcopy(plan), Path(plan_dir))
    bare = Renderer({**R, "layers": [L for L in R["layers"] if L.get("type") not in ("overlay", "text")]})
    s = min(W, H) / 1080
    if H > W:                                       # upright: the platforms' bands; the right rail is in the way
        sx, sy = W / SZ.REF_W, H / SZ.REF_H
        z = SZ.ZONES["all"]
        area = [z["left"] * sx, z["top"] * sy, W - z["left"] * sx, H - z["bottom"] * sy]
        rail = [[W - z["right"] * sx, z["rail"][0] * sy, W, z["rail"][1] * sy]]
    else:
        area, rail = [MARGIN * s, MARGIN * s, W - MARGIN * s, H - MARGIN * s], []

    def drawn(layers, frames):                      # where these layers draw (half opaque or more), or None
        r0 = Renderer({**R, "background": 0.0, "layers": layers, "grain": 0})
        r1 = Renderer({**R, "background": 1.0, "layers": layers, "grain": 0})
        m = None
        for f in frames:
            k = np.abs(r0.render(f).astype(np.int16) - r1.render(f).astype(np.int16)).max(axis=2) < CARD_ALPHA
            m = k if m is None else m | k
        if m is None or not m.any():
            return None
        ys, xs = np.nonzero(m)
        return [float(xs.min()), float(ys.min()), float(xs.max() + 1), float(ys.max() + 1)]
    caps = [x for x in R["layers"] if x.get("type") == "overlay" and ME._is_captions(x)]
    placed, lines = [], []
    for L in cards:
        RL = R["layers"][plan["layers"].index(L)]
        a, e = int(L["start"]), int(L["end"])
        at = sorted({min(e, a + int(round(k * (e - a)))) for k in CARD_AT})
        box = drawn([RL], at)
        if box is None:
            continue
        avoid = list(rail) + [p for p, (pa, pe) in placed if pa <= e and pe >= a]
        for f in at:
            for x, y, w, h, *_ in [q for q in (find_faces(bare.render(f)) or []) if q[2] * q[3] >= 0.002 * W * H]:
                avoid.append([x - w * PAD, y - h * PAD, x + w * (1 + PAD), y + h * (1 + PAD)])
        cb = drawn([c for c in caps if int(c["start"]) <= e and int(c["end"]) >= a], at) if caps else None
        if cb:
            avoid.append(cb)
        mv = place(box, avoid, area, GAP * s / 2)
        span = _span(a, e, fps, frame_to_tc)
        if mv is None:
            lines.append(f"{L.get('id')} {span}: no room clear of the faces and captions - left where it is")
            placed.append((box, (a, e)))
            continue
        dx, dy = int(round(mv[0])), int(round(mv[1]))
        placed.append(([box[0] + dx, box[1] + dy, box[2] + dx, box[3] + dy], (a, e)))
        if dx or dy:
            st = OS.status(Path(RL["file"]).parent)
            b0 = L.get("rect0") or [0, 0, int(st.get("width") or W), int(st.get("height") or H)]
            L["rect"], L["rect_fit"] = [b0[0] + dx, b0[1] + dy, b0[2], b0[3]], True
            how = [f"{'up' if dy < 0 else 'down'} {abs(dy)} px"] * bool(dy) + \
                [f"{'left' if dx < 0 else 'right'} {abs(dx)} px"] * bool(dx)
            lines.append(f"{L.get('id')} {span}: moved {', '.join(how)} - clear of the face"
                         + (" and the captions" if cb else ""))
    return lines


def selfcheck() -> dict:
    """Known answers for `where` (no video): an upright talker, a wide close-up, a corner camera, no face."""
    import time
    t0, lines, ok = time.time(), [], True

    def case(name, cond):
        nonlocal ok
        ok &= bool(cond)
        lines.append(("PASS " if cond else "FAIL ") + name)
    c1 = where(0.78 * 1920, 85, 700, 1080, [[390, 500, 300, 400]], 1080, 1920)
    case(f"upright: captions in the bottom band move up under the chin (chin y 900 -> middle {c1[0]:.0f})",
         c1[0] == 900 + 40 + 42.5 and c1[1].startswith("under the chin"))
    c2 = where(0.78 * 1080, 85, 900, 1920, [[700, 300, 450, 640]], 1920, 1080)
    case(f"wide close-up: off the mouth (y 825), over the chin (middle {c2[0]:.0f}); never up on the forehead",
         c2[0] == 300 + 0.82 * 640 + 20 + 42.5 and c2[1].startswith("under the mouth"))
    c3 = where(0.78 * 1080, 85, 900, 1920, [[1500, 600, 300, 380]], 1920, 1080)
    c4 = where(0.5 * 1920, 85, 700, 1080, [], 1080, 1920)
    c5 = where(0.78 * 1080, 85, 900, 1920, [[700, 200, 500, 860]], 1920, 1080)
    case("a corner camera's face beside the lines: they stay; no face and clear: they stay; a face filling the frame: "
         "left (no room under the mouth)", c3 == (None, "") and c4 == (None, "") and c5[0] is None and "no room" in c5[1])
    c6 = where(0.78 * 1920, 85, 700, 1080, [[390, 250, 300, 400], [390, 1210, 300, 400]], 1080, 1920, seam=960)
    c7 = where(0.78 * 1920, 85, 700, 1080, [[390, 250, 300, 400], [390, 880, 300, 400]], 1080, 1920, seam=960)
    scr = {"layers": [{"type": "clip", "start": 0, "end": 99, "panels": [{"rect": [0, 0, 1080, 858]},
                                                                         {"rect": [0, 858, 1080, 622]}]}]}
    fit = {"layers": [{"type": "clip", "start": 0, "end": 99, "panels": [{"rect": [0, 555, 1080, 810]}]}]}
    case("two panels stacked (a split): the captions on the seam; a face's eyes too close to it: not there; a screen "
         "over its face camera has a seam too (y 858), a picture in a band has none",
         c6 == (960, "on the seam between the panels (y 960)") and c7[0] != 960 and _seam(scr, 10, 50, 1080) == 858
         and _seam(fit, 10, 50, 1080) is None)
    c8 = where(1347, 113, 696, 1080, [[305, 41, 457, 646], [297, 751, 420, 687], [295, 1012, 457, 594]], 1080, 1920,
               seam=960)
    case("two panels, the bottom face moving across the seam in one sample, no room anywhere else: the seam (it covers "
         "the faces least), not left over the bottom face's eyes", c8[0] == 960 and "least" in c8[1])
    c9 = where(1347, 113, 696, 1080, [[400, 640, 280, 360]], 1080, 1920, keep=[[270, 1268, 810, 1292]])
    case("a subtitle burned into the picture just over the captions (reframe's fit kept it whole): the captions move "
         f"clear under it (middle {c9[0]}), not over it", c9[0] is not None and c9[0] - 113 / 2 >= 1292 + KEEP_GAP)
    wide = [80, 80, 1840, 1000]
    p1 = place([660, 40, 1260, 200], [[650, 30, 1220, 780]], wide, 20)
    p2 = place([700, 120, 1200, 260], [[600, 0, 1300, 900]], wide, 20)
    p3 = place([100, 900, 400, 980], [[650, 30, 1220, 780]], wide, 20)
    case(f"a card: on the forehead of a wide shot -> down under the chin ({p1}); a face filling the height -> to a "
         f"side ({p2}); clear already -> stays ({p3}); bigger than the room -> None",
         p1 == (0, 780 + 20 - 40) and p2 is not None and p2[1] == 0 and abs(p2[0]) > 0 and p3 == (0, 0)
         and place([0, 0, 1920, 1080], [], wide, 20) is None)
    return {"passed": ok, "seconds": round(time.time() - t0, 3), "lines": lines}


def _span(a: int, b: int, fps: float, tc) -> str:
    return f"f{a}-f{b} ({tc(a, fps)}-{tc(b, fps)})"
