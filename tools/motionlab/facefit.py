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
with no room under the mouth inside the safe height keeps its height (the build's face check then says so).

    fit_captions(plan, plan_dir) -> lines (what moved, frame + timecode); the plan is changed in place. A piece's
    "rect" set here carries "rect_fit": true and is worked out again on every build; a rect without it (set by hand)
    is left alone.
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
        c, why = where(c0, hgt, cw, W0, boxes, W, H)
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


def where(c0: float, hgt: float, cw: float, W0: float, boxes: list, W: int, H: int) -> tuple[float | None, str]:
    """Where a shot's captions go: their middle's height (c0 = their style's), their height and width (centred on a
    graphic W0 wide), the faces seen in the shot ([x, y, w, h]) on a W x H video -> (the new middle, why) or (None,
    why it stays: "" = already clear)."""
    upright = H > W
    gap = GAP * min(W, H) / 1080
    top_ok, bottom_ok = ((BAND_TOP * H / 1920, BAND_BOTTOM * H / 1920) if upright
                         else (MARGIN * H / 1080, H - MARGIN * H / 1080))
    lo, hi = top_ok + hgt / 2, bottom_ok - hgt / 2             # where its middle may be: the safe height
    x0, x1 = (W0 - cw) / 2, (W0 + cw) / 2                       # (its lines are centred)
    near = [(y + h * EYES, y + h * MOUTH, y + h * CHIN) for x, y, w, h in boxes   # the faces its lines cross (a
            if x + w * (1 + PAD) > x0 and x - w * PAD < x1]                         # corner camera to the side: no)
    if not near:
        return (None, "") if c0 <= hi else (hi, "off the bottom band" if upright else "off the bottom edge")
    ey, mo, chin = min(q[0] for q in near), max(q[1] for q in near), max(q[2] for q in near)
    if (c0 - hgt / 2 >= mo + gap / 2 or c0 + hgt / 2 <= ey - gap) and lo <= c0 <= hi:
        return None, ""                                         # already off the eyes-to-mouth band
    if lo <= chin + gap + hgt / 2 <= hi:                        # under the chin first (the step's rule) ...
        return chin + gap + hgt / 2, f"under the chin (y {int(chin)})"
    if lo <= mo + gap / 2 + hgt / 2 <= hi:                      # ... a close-up: just under the mouth, over the chin
        return mo + gap / 2 + hgt / 2, f"under the mouth (y {int(mo)}; a close-up: no room under the chin)"
    return None, f"no room under the mouth (y {int(mo)}) inside the safe height"   # (never up onto the forehead)


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
    return {"passed": ok, "seconds": round(time.time() - t0, 3), "lines": lines}


def _span(a: int, b: int, fps: float, tc) -> str:
    return f"f{a}-f{b} ({tc(a, fps)}-{tc(b, fps)})"
