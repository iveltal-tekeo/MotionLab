"""The Editor's effects (0.6.0 step 6; the user, 2026-10-25: "so if we do the mini editor on the version we can maybe
choose some effects, edit them?"): every effect of a plan as one chip - found in its layers the way the quick draft
(motionlab\\draft.py build_layers) and Claude write them - and what the Editor changes on one: move it, its length,
its strength, its ease, remove it; new ones at a frame. Pure plan changes, in place; motionlab\\miniedit.apply runs
them as the ops fxmove / fxset / fxremove / fxadd. The sound effects follow by themselves (sfx.plan_cues reads the
effects from the layers on every build).

    effects(plan) -> [{id, kind, label, f, len, strength, ease, layer, can}]   frames are the plan's; id = kind:layer:f
        (the same plan gives the same ids); can = what the chip offers: move, len, strength, ease, remove
    move(P, fx, by) / set_len(P, fx, n) / set_strength(P, fx, x) / set_ease(P, fx, ease) / remove(P, fx)
    add(P, kind, f) -> the new effect's id; ADD = the kinds the Editor offers (2026-10-27, the user: "few but higher
        quality ones" - the review against CapCut / Premiere / Resolve kept these; the rest stay editable where a plan
        has them: a zoom-through / pull-out, colour flash, light leak, dips, white flash, spotlight)

Where each kind lives (draft.py writes them so): a zoom move = a shot's "zoom" keys (Zoom in / out; a "hold" key =
a punch-in step); a shot's constant "zoom" = tight framing; a shake = "anchor" value lists (+ a 6 % zoom); a flash =
"flash_over" {frame: strength}; a white frame = "flash_white"; a black frame = "black"; a stutter = "jumps"; a push /
whip / crossfade = two shots overlapping at a cut ("dx" / "dy" keys, the incoming shot's "opacity" keys); a colour
flash, a light leak, a dip, a fade = a "solid" layer (colorflash_ / leak_ / dip_ / fade_); an RGB split = two
"rgb_<n>_<k>" clip layers; "mirror" on a shot.
"""
from __future__ import annotations

import copy
import math

from . import editlist as EL
from . import i18n as I18N

EASES = ("linear", "smooth", "in", "out", "hold", "easy", "strong", "glide", "launch")    # 2026-10-27: + designers'
ADD = ("punch_in", "lean_in", "slow_push", "shake", "flash", "black_frame", "stutter", "rgb_split")
MOVES_PICTURE = {"stutter"}                         # shifts the picture against its sound: not on a talking video
CLIP_ONLY = {"punch_in", "lean_in", "slow_push", "shake", "rgb_split", "stutter"}                 # a clip's picture
FLASH = (0.9, 0.55, 0.3, 0.12)                      # a flash's frames: bright, then a quick decay (compose: exposure)
RGB_SPLIT = (0.022, 0.011, 0.004, 0.0015)           # an RGB split's red / blue offset per frame, a share of the width
RGB_DROP = ("id", "flash_over", "flash_white", "black", "trans", "sound_db", "tr", "room", "tint", "blend", "mblur",
            "cover")                                # (a copy of the shot for the split: its picture and move only)
# 2026-10-27, the face-led ones (after Vibha Ramprakash's claude-video-effects, MIT; the user: "maybe u zoom in too
# much? try some ease-in ease-out"): small and eased - a lean-in 15 % on a word (glides in, eases out), a slow push
# 12 % over ~3 s (the same day: the push-in merged into it, the room no longer melts - a halo round the hair); each
# turns the shot's "track": "face" on (compose: the zoom point follows the face). A "room" = curves for the room only
# (an older plan's spotlight / melt: still found, moved, changed).
ROOM_LOOKS = {"spotlight": ("dim", "Spotlight"), "melt": ("blur", "Room out of focus"), "grey": ("grey", "Grey room")}
SOLID_FX = ("colorflash_", "leak_", "dip_", "fade_in", "fade_out", "flash_", "black_")     # solids that are effects


class FxError(ValueError):
    pass


def _keys(v):
    return v.get("keys") if isinstance(v, dict) and v.get("keys") else None


def _runs(frames: list[int]) -> list[list[int]]:
    out: list[list[int]] = []
    for f in sorted(frames):
        if out and f == out[-1][-1] + 1:
            out[-1].append(f)
        else:
            out.append([f])
    return out


def _fx(kind: str, label: str, layer: str, f: int, n: int, can: list[str], strength=None, ease=None) -> dict:
    return {"id": f"{kind}:{layer}:{int(f)}", "kind": kind, "label": label, "layer": layer, "f": int(f),
            "len": max(1, int(n)), "strength": strength, "ease": ease, "can": can}


def _shots(P: dict) -> list[dict]:
    return EL.shots(P)


def effects(P: dict) -> list[dict]:
    out: list[dict] = []
    shot_ids = {x["id"] for x in _shots(P)}
    rgb: dict[str, list[dict]] = {}
    for L in P.get("layers", []):
        t, lid = L.get("type"), str(L.get("id"))
        s, e = int(L.get("start", 0)), int(L.get("end", 0))
        if L.get("tr"):                                     # a transition's own layers (motionlab\edtrans)
            continue
        if t == "clip" and lid.startswith("rgb_"):
            rgb.setdefault(lid.rsplit("_", 1)[0], []).append(L)
            continue
        if t == "solid":
            if lid.startswith(SOLID_FX):                    # (a corner camera's frame, an end card's background:
                out.append(_solid_fx(L))                    # the layout, not an effect)
            continue
        if t != "clip":
            continue
        an = L.get("anchor")
        shaky = isinstance(an, list) and any(isinstance(a, dict) and "values" in a for a in an)
        zk = _keys(L.get("zoom"))
        if zk and not any(k in L["zoom"] for k in ("scale", "offset")):
            for m in _zoom_moves(sorted(zk, key=lambda k: k[0]), s, e):     # every move of the shot its own chip
                can = ["move", "len", "strength", "ease", "remove"] if m["kind"] == "zoom" else ["move", "strength", "remove"]
                out.append(_fx(m["kind"], m["label"], lid, m["f"], m["len"], can, m["strength"], m["ease"]))
        elif isinstance(L.get("zoom"), (int, float)) and abs(float(L["zoom"]) - 1) > 1e-3 and not shaky and lid in shot_ids:
            out.append(_fx("framing", "Tight framing", lid, s, e - s + 1, ["strength", "remove"], round(float(L["zoom"]), 3)))
        if shaky:
            d = next(a for a in an if isinstance(a, dict) and "values" in a)
            dev = max((abs(float(v) - float(a["values"][-1])) for a in an if isinstance(a, dict) for v in a["values"]),
                      default=0.0)
            out.append(_fx("shake", "Shake", lid, int(d["start"]), len(d["values"]), ["move", "strength", "remove"],
                           round(dev, 4)))
        for run in _runs([int(k) for k in (L.get("flash_over") or {})]):
            peak = max(float(L["flash_over"][str(f)]) for f in run)
            out.append(_fx("flash", "Flash", lid, run[0], len(run), ["move", "strength", "remove"], round(peak, 3)))
        for key, kind, label in (("flash_white", "white", "White frame"), ("black", "black", "Black frame")):
            for run in _runs([int(v) for v in L.get(key) or []]):
                out.append(_fx(kind, label, lid, run[0], len(run), ["move", "remove"]))
        J = L.get("jumps") or []
        if len(J) > 1:
            out.append(_fx("stutter", "Stutter", lid, int(J[1][0]), int(J[-1][0]) - int(J[1][0]) + 1, ["move", "remove"]))
        if L.get("mirror"):
            out.append(_fx("mirror", "Mirror", lid, s, e - s + 1, ["remove"]))
        rm = L.get("room") if isinstance(L.get("room"), dict) else None
        if rm and rm.get("look") in ROOM_LOOKS and _keys(rm.get(ROOM_LOOKS[rm["look"]][0])):
            ch, label = ROOM_LOOKS[rm["look"]]
            rk = sorted(_keys(rm[ch]), key=lambda k: k[0])
            out.append(_fx("room", label, lid, int(rk[0][0]), int(rk[-1][0]) - int(rk[0][0]) + 1,
                           ["move", "len", "strength", "remove"], round(max(float(k[1]) for k in rk), 3)))
    S = _shots(P)
    for A, B in zip(S, S[1:]):                          # a transition: the two shots overlap at the cut
        a, b = int(B["start"]), int(A["end"])
        if b < a:
            continue
        ax = "dx" if _keys(B.get("dx")) else "dy" if _keys(B.get("dy")) else None
        if ax:
            k0 = _keys(B[ax])[0]
            kind, label = ("whip", "Whip") if (k0[2] if len(k0) > 2 else "") in ("out3", "in3") else ("push", "Push")
        elif _keys(B.get("opacity")):
            kind, label = "crossfade", "Crossfade"
        else:
            kind, label = "overlap", "Overlap"
        out.append(_fx(kind, label, str(B["id"]), a, b - a + 1, ["remove"]))
    for base, Ls in sorted(rgb.items()):
        f = min(int(x["start"]) for x in Ls)
        out.append(_fx("rgb", "RGB split", base, f, max(int(x["end"]) for x in Ls) - f + 1, ["move", "len", "remove"]))
    return sorted(out, key=lambda x: (x["f"], x["id"]))


def _solid_fx(L: dict) -> dict:
    lid, s, e = str(L["id"]), int(L["start"]), int(L["end"])
    col = L.get("color") or [0, 0, 0]
    if lid.startswith("colorflash_"):
        kind, label = "colour_flash", "Colour flash"
    elif lid.startswith("leak_"):
        kind, label = "light_leak", "Light leak"
    elif lid.startswith("dip_"):
        kind, label = "dip", "Dip to white" if sum(col) > 1.5 else "Dip to black"
    elif lid == "fade_in":
        kind, label = "fade", "Fade in"
    elif lid == "fade_out":
        kind, label = "fade", "Fade out"
    elif lid.startswith("flash_"):                          # a flash / black frame where no clip is under it
        kind, label = "solid_flash", "Flash"
    elif lid.startswith("black_"):
        kind, label = "solid_black", "Black frame"
    else:
        kind, label = "solid", "Colour layer"
    op = L.get("opacity")
    peak = (max(float(k[1]) for k in op["keys"]) if _keys(op) else max(float(v) for v in op["values"])
            if isinstance(op, dict) and op.get("values") else float(op if isinstance(op, (int, float)) else 1.0))
    can = ["move", "len", "strength", "remove"] + (["ease"] if _keys(op) else [])
    ease = (_keys(op)[0][2] if len(_keys(op)[0]) > 2 else "linear") if _keys(op) else None
    return _fx(kind, label, lid, s, e - s + 1, can, round(peak, 3), ease)


def find(P: dict, fid: str) -> dict:
    fx = next((x for x in effects(P) if x["id"] == fid), None)
    if fx is None:
        raise FxError(I18N.t("no effect {effect}", effect=fid))
    return fx


def _layer(P: dict, lid: str) -> dict:
    L = next((x for x in P["layers"] if x.get("id") == lid), None)
    if L is None:
        raise FxError(I18N.t("no effect {effect}", effect=lid))
    return L


def _group(P: dict, base: str) -> list[dict]:
    return [x for x in P["layers"] if str(x.get("id", "")).rsplit("_", 1)[0] == base and str(x["id"]).startswith("rgb_")]


def _inside(L: dict, a: int, b: int) -> bool:
    return int(L["start"]) <= a and b <= int(L["end"])


def _clamp(by: int, lo: int, hi: int) -> int:
    """A move as far as it can go that way (the Editor drags to the edge, never an error for going too far)."""
    by = max(lo, min(hi, int(by)))
    if by == 0:
        raise FxError(I18N.t("the effect cannot go further that way"))
    return by


# ------------------------------------------------------------------------------------------------ a shot's zoom
# A shot's "zoom" keys may hold several moves (a zoom in, a punch-in later, a shake's bump - 2026-10-26: one zoom per
# shot left most shots refusing every zoom effect): each move is its own chip = a run of keys whose value changes; a
# "hold" key before a change = a step at the next key (a punch). A shake's own keys carry the tag "shake" (a 4th
# element: shifts, speed and splits keep it) and are never a zoom chip. A zoom added later scales what comes after it
# (a push-in stays in), so moves stack like layers.
SHAKE = "shake"
_EASE = {"hold": lambda t: 0.0, "linear": lambda t: t, "smooth": lambda t: t * t * (3 - 2 * t), "in": lambda t: t * t,
         "out": lambda t: 1 - (1 - t) * (1 - t), "in3": lambda t: t ** 3, "out3": lambda t: 1 - (1 - t) ** 3}


def _ez(k) -> str:
    return k[2] if len(k) > 2 else "linear"


def _tag(k):
    return k[3] if len(k) > 3 else None


def _val(ks: list, f: float) -> float:
    """compose.Curve on sorted keys."""
    if f <= ks[0][0]:
        return float(ks[0][1])
    if f >= ks[-1][0]:
        return float(ks[-1][1])
    i = max(j for j in range(len(ks)) if ks[j][0] <= f)
    t = (f - ks[i][0]) / max(1e-9, ks[i + 1][0] - ks[i][0])
    e = _ez(ks[i])
    fn = _EASE.get(e)
    if fn is None:                                          # the new curves and the chart's own (compose's tables)
        from .compose import ease_fn
        fn = ease_fn(e)
    return float(ks[i][1]) + (float(ks[i + 1][1]) - float(ks[i][1])) * fn(t)


def _changes(ks: list, i: int) -> bool:
    return abs(float(ks[i][1]) - float(ks[i + 1][1])) > 1e-6


def _zoom_runs(ks: list) -> list[tuple[int, int, str]]:
    """(i0, i1, kind) per move of sorted keys: "zoom" = keys i0..i1 change (a hold step at its front belongs to it - a
    pull-out jumps in, then glides out), "punch" = a lone step at key i1 (i0 = the hold key before it)."""
    out, i, n = [], 0, len(ks)

    def free(j):
        return _tag(ks[j]) != SHAKE and _tag(ks[j + 1]) != SHAKE

    def glide(j):
        return j < n - 1 and _changes(ks, j) and _ez(ks[j]) != "hold" and free(j)

    while i < n - 1:
        if not (_changes(ks, i) and free(i)):
            i += 1
            continue
        if _ez(ks[i]) == "hold" and not glide(i + 1):
            out.append((i, i + 1, "punch"))
            i += 1
            continue
        j = i + 1 if _ez(ks[i]) == "hold" else i
        while glide(j):
            j += 1
        out.append((i, j, "zoom"))
        i = j
    return out


def _zoom_moves(ks: list, s: int, e: int) -> list[dict]:
    """The moves a shot over frames s..e shows of its sorted zoom keys: kind, label, f, len, strength, ease + the keys
    (i0, i1, lead = a step at its front)."""
    out = []
    for i0, i1, kind in _zoom_runs(ks):
        if kind == "punch":
            a = int(ks[i1][0])
            if not s <= a <= e:
                continue
            b = min(e, int(ks[i1 + 1][0]) - 1) if i1 + 1 < len(ks) else e
            v0, v1 = float(ks[i0][1]), float(ks[i1][1])
            out.append({"kind": "punch", "label": "Punch-in" if v1 > v0 else "Punch-out", "f": a, "len": b - a + 1,
                        "strength": round(max(v0, v1) / max(min(v0, v1), 1e-6), 3), "ease": None,
                        "i0": i0, "i1": i1, "lead": False})
            continue
        lead = _ez(ks[i0]) == "hold"
        j0 = i0 + 1 if lead else i0
        a0, a1 = int(ks[j0][0]), int(ks[i1][0])
        if a1 < s or a0 > e:
            continue
        vals = [float(ks[k][1]) for k in range(i0, i1 + 1)]
        v0, v1, span = float(ks[j0][1]), vals[-1], max(vals) - min(vals)
        f = max(s, a0)
        out.append({"kind": "zoom", "label": "Zoom pulse" if abs(v1 - v0) < 0.25 * span else
                    "Zoom in" if v1 > v0 else "Zoom out", "f": f, "len": min(e, a1) - f + 1,
                    "strength": round(max(vals) / max(min(vals), 1e-6), 3), "ease": _ez(ks[j0]),
                    "i0": i0, "i1": i1, "lead": lead})
    return out


def _tidy(ks: list) -> None:
    """Keys that change no frame go. In place."""
    i = 0
    while len(ks) > 1 and i < len(ks):
        if i in (0, len(ks) - 1):
            drop = abs(float(ks[i][1]) - float(ks[1 if i == 0 else i - 1][1])) <= 1e-6
        else:
            trial = ks[:i] + ks[i + 1:]
            drop = all(abs(_val(trial, f) - _val(ks, f)) <= 1e-6 for f in range(int(ks[i - 1][0]), int(ks[i + 1][0]) + 1))
        if drop:
            del ks[i]
            i = max(0, i - 1)
        else:
            i += 1


def _keys_of(L: dict) -> list:
    """L's zoom as keys to change, in place (a number = one key at its start; a hold step's hold key right before the
    step - the same picture; keys that change nothing gone)."""
    z = L.get("zoom", 1.0)
    if isinstance(z, dict) and (not _keys(z) or "scale" in z or "offset" in z):
        raise FxError(I18N.t("this shot already has a zoom - change that one"))
    if not _keys(z):
        z = L["zoom"] = {"keys": [[int(L["start"]), float(z) if isinstance(z, (int, float)) else 1.0, "linear"]]}
    ks = sorted(([int(k[0]), float(k[1]), *k[2:]] for k in z["keys"]), key=lambda k: k[0])
    i = 0
    while i < len(ks) - 1:
        if _ez(ks[i]) == "hold" and _changes(ks, i) and ks[i + 1][0] - ks[i][0] > 1:
            ks.insert(i + 1, [ks[i + 1][0] - 1, ks[i][1], "hold", *ks[i][3:]])
            ks[i] = [ks[i][0], ks[i][1], "linear", *ks[i][3:]]
            i += 1
        i += 1
    _tidy(ks)
    z["keys"] = ks
    return ks


def _done(L: dict) -> None:
    """After a change: keys that change nothing go; a zoom that no longer moves is a number again (1 = none)."""
    ks = L["zoom"]["keys"]
    _tidy(ks)
    if len({round(float(k[1]), 6) for k in ks}) == 1:
        v = round(float(ks[0][1]), 4)
        if abs(v - 1) < 1e-6:
            L.pop("zoom")
        else:
            L["zoom"] = v
        return
    for k in ks:
        k[1] = round(float(k[1]), 4)


def _busy(ks: list) -> list[tuple[int, int]]:
    """Where the zoom already changes (a move's frames, a step's two)."""
    return [(int(ks[i][0]), int(ks[i + 1][0])) for i in range(len(ks) - 1) if _changes(ks, i)]


def _room(ks: list, s: int, e: int, f: int, n: int, nmin: int) -> tuple[int, int]:
    """(a, m): the free frames nearest f for a change over a..a+m (m from n down to nmin when the shot is short or busy):
    on the shot, a-1..a+m clear of the other moves - an effect near a shot's end starts earlier instead of failing."""
    busy = _busy(ks)
    for m in range(min(n, e - s), nmin - 1, -1):
        for d in range(0, e - s + 1):
            for a in ((f + d, f - d) if d else (f,)):
                if s <= a and a + m <= e and not any(x <= a + m and a - 1 <= y for x, y in busy):
                    return a, m
    raise FxError(I18N.t("no room left on this shot for another zoom - remove or shorten one"))


def _put(ks: list, f: int, v: float, ease: str, tag=None) -> None:
    k = [int(f), float(v), ease] + ([tag] if tag else [])
    for i, x in enumerate(ks):
        if x[0] == f:
            ks[i] = k
            return
        if x[0] > f:
            ks.insert(i, k)
            return
    ks.append(k)


def _ease_at(ks: list, f: int) -> str:
    k = [x for x in ks if x[0] <= f]
    return _ez(k[-1]) if k else "linear"


def _clear(ks: list, a: int, b: int) -> None:
    ks[:] = [k for k in ks if not a <= k[0] <= b]          # (a free window: only keys that change nothing)


def _scale_after(ks: list, f: int, x: float) -> None:
    for k in ks:
        if k[0] > f:
            k[1] = float(k[1]) * x


def _find_move(L: dict, fx: dict) -> tuple[list, dict]:
    ks = _keys_of(L)
    mv = next((m for m in _zoom_moves(ks, int(L["start"]), int(L["end"])) if m["kind"] == fx["kind"]
               and m["f"] == fx["f"]), None)
    if mv is None:
        raise FxError(I18N.t("no effect {effect}", effect=fx["id"]))
    return ks, mv


def _zoom_move(L: dict, fx: dict, by: int) -> int:
    ks, mv = _find_move(L, fx)
    s, e, i0, i1 = int(L["start"]), int(L["end"]), mv["i0"], mv["i1"]
    lo = ks[i0 - 1][0] + 1 - ks[i0][0] if i0 > 0 else -10 ** 9          # never over the moves beside it
    hi = ks[i1 + 1][0] - 1 - ks[i1][0] if i1 + 1 < len(ks) else 10 ** 9
    by = _clamp(by, max(lo, min(0, s - mv["f"])), min(hi, max(0, e - ks[i1][0])))
    for j in range(i0, i1 + 1):
        ks[j][0] += by
    _done(L)
    return by


def _zoom_len(L: dict, fx: dict, n: int) -> None:
    ks, mv = _find_move(L, fx)
    if mv["kind"] != "zoom":
        raise FxError(I18N.t("this effect's length stays"))
    j0, i1 = mv["i0"] + (1 if mv["lead"] else 0), mv["i1"]
    a0, a1 = ks[j0][0], ks[i1][0]
    cap = min(ks[i1 + 1][0] - 1 if i1 + 1 < len(ks) else 10 ** 9, max(int(L["end"]), a1)) - a0
    want = min(cap, max(i1 - j0, (a1 - a0) + (int(n) - fx["len"])))
    sc, prev = want / max(1, a1 - a0), None
    for j in range(j0, i1 + 1):
        fr = a0 + int(round((ks[j][0] - a0) * sc))
        fr = prev + 1 if prev is not None and fr <= prev else fr
        ks[j][0] = prev = fr
    _done(L)


def _zoom_strength(L: dict, fx: dict, x: float) -> None:
    ks, mv = _find_move(L, fx)
    i0, i1 = mv["i0"], mv["i1"]
    x = min(3.0, max(1.01, float(x)))
    if mv["kind"] == "punch":                       # the step and everything after it
        v0, v1 = ks[i0][1], ks[i1][1]
        r = (v0 * x if v1 > v0 else v0 / x) / v1
        for k in ks[i1:]:
            k[1] *= r
    else:
        vals = [ks[j][1] for j in range(i0, i1 + 1)]
        lo, r = min(vals), max(vals) / max(min(vals), 1e-6)
        if r <= 1.0001:
            return
        first, last = ks[i0][1], ks[i1][1]
        for j in range(i0, i1 + 1):
            ks[j][1] = lo + (ks[j][1] - lo) * (x - 1) / (r - 1)
        _follow(ks, i0, i1, first, last)
    _done(L)


def _follow(ks: list, i0: int, i1: int, first: float, last: float) -> None:
    """After a move's values changed: what comes after it keeps its size relative to the move's end; the still keys
    before it that held its old start take the new one."""
    r = ks[i1][1] / max(last, 1e-6)
    for k in ks[i1 + 1:]:
        k[1] *= r
    j = i0 - 1
    while j >= 0 and abs(ks[j][1] - first) <= 1e-6:
        ks[j][1] = ks[i0][1]
        j -= 1


def _zoom_ease(L: dict, fx: dict, ease: str) -> None:
    ks, mv = _find_move(L, fx)
    if mv["kind"] != "zoom":
        raise FxError(I18N.t("this effect has no ease to change"))
    for j in range(mv["i0"] + (1 if mv["lead"] else 0), mv["i1"]):
        ks[j] = [ks[j][0], ks[j][1], ease, *ks[j][3:]]
    _done(L)


def _zoom_remove(L: dict, fx: dict) -> None:
    """The shot keeps its resting size (the move's smaller one); what came after keeps its size relative to it."""
    ks, mv = _find_move(L, fx)
    i0, i1 = mv["i0"], mv["i1"]
    if mv["kind"] == "punch":
        r = ks[i0][1] / ks[i1][1]
        for k in ks[i1:]:
            k[1] *= r
    else:
        first, last = ks[i0][1], ks[i1][1]
        lo = min(ks[j][1] for j in range(i0, i1 + 1))
        for j in range(i0, i1 + 1):
            ks[j][1] = lo
        _follow(ks, i0, i1, first, last)
    _done(L)


def _shake_keys(L: dict) -> list:
    return [k for k in (_keys(L.get("zoom")) or []) if _tag(k) == SHAKE]


def _shake_bump(L: dict, a: int, n: int) -> None:
    """A shake's own zoom: 6 % closer on its first frame, back over its n frames (room for the picture to move)."""
    ks = _keys_of(L)
    v, tail = _val(ks, a), _ease_at(ks, a + n)
    _clear(ks, a - 1, a + n)
    _put(ks, a - 1, v, "hold", SHAKE)
    _put(ks, a, v * 1.06, "out", SHAKE)
    _put(ks, a + n, v, tail, SHAKE)
    _done(L)


def _unshake(L: dict) -> None:
    if _shake_keys(L):
        L["zoom"]["keys"] = [k for k in L["zoom"]["keys"] if _tag(k) != SHAKE]
        _done(L)


# ------------------------------------------------------------------------------------------------ changing one
def move(P: dict, fx: dict, by: int) -> int:
    """fx `by` frames later (< 0 = earlier) - as far as it can go that way (the video's ends, its shot's edges, the
    zoom moves beside it); the frames it moved."""
    by = int(by)
    if by == 0:
        return 0
    k, f0, f1 = fx["kind"], fx["f"], fx["f"] + fx["len"] - 1
    N = int(P["frames"])
    if k in ("rgb",):                                  # made again where it goes: its copies show the shot's frames
        by = _clamp(by, -f0, N - 1 - f1)                # there
        remove(P, fx)
        nid = add(P, "rgb_split", f0 + by)
        if fx["len"] != 3:
            set_len(P, find(P, nid), fx["len"])
        return by
    L = _layer(P, fx["layer"])
    if L.get("type") == "solid":
        by = _clamp(by, -int(L["start"]), N - 1 - int(L["end"]))
        EL._shift(L, by)
        return by
    if k in ("zoom", "punch"):
        return _zoom_move(L, fx, by)
    if k == "room":
        by = _clamp(by, int(L["start"]) - f0, int(L["end"]) - f1)
        for c in _room_curves(L):
            c["keys"] = [[int(x[0]) + by, *x[1:]] for x in c["keys"]]
        return by
    s, e = int(L["start"]), int(L["end"])
    by = _clamp(by, (s + 1 if k == "stutter" else s) - f0, e - f1)
    if k == "shake":
        bump = _shake_keys(L)
        if bump:                                        # its own zoom goes with it, where the shot's zoom is still
            n = int(bump[-1][0]) - int(bump[1][0])
            _unshake(L)
            try:
                _room(_keys_of(L), f0 + by, f0 + by + n, f0 + by, n, n)
            except FxError:
                raise FxError(I18N.t("the shot zooms there - move that zoom first")) from None
            _shake_bump(L, f0 + by, n)
        for d in L["anchor"]:
            if isinstance(d, dict) and "start" in d:
                d["start"] = int(d["start"]) + by
    elif k == "flash":
        fo = L["flash_over"]
        run = [str(f) for f in range(fx["f"], fx["f"] + fx["len"])]
        vals = {f: fo.pop(f) for f in run if f in fo}
        fo.update({str(int(f) + by): v for f, v in vals.items()})
    elif k in ("white", "black"):
        key = "flash_white" if k == "white" else "black"
        run = set(range(fx["f"], fx["f"] + fx["len"]))
        L[key] = sorted({int(v) + by if int(v) in run else int(v) for v in L[key]})
    elif k == "stutter":
        L["jumps"] = [L["jumps"][0]] + [[int(j[0]) + by, j[1]] for j in L["jumps"][1:]]
    else:
        raise FxError(I18N.t("this effect cannot move"))
    return by


def set_len(P: dict, fx: dict, n: int) -> None:
    n = max(2, int(n))
    k, f0, old = fx["kind"], fx["f"], fx["len"]
    if k == "rgb":
        for L in _group(P, fx["layer"]):
            L["end"] = min(int(P["frames"]) - 1, int(L["start"]) + n - 1)
        return
    L = _layer(P, fx["layer"])
    if k == "zoom":
        _zoom_len(L, fx, n)
    elif k == "room":
        n = min(n, int(L["end"]) - f0 + 1)
        sc = (n - 1) / max(1, old - 1)
        for c in _room_curves(L):
            c["keys"] = [[f0 + int(round((int(x[0]) - f0) * sc)), *x[1:]] for x in c["keys"]]
    elif L.get("type") == "solid":
        s = int(L["start"])
        sc = (n - 1) / max(1, old - 1)
        op = L.get("opacity")
        if _keys(op):
            op["keys"] = [[s + int(round((int(x[0]) - s) * sc)), *x[1:]] for x in op["keys"]]
        elif isinstance(op, dict) and op.get("values"):
            v = op["values"]
            op["values"] = [v[min(len(v) - 1, int(i * len(v) / n))] for i in range(n)]
        L["end"] = min(int(P["frames"]) - 1, s + n - 1)
    else:
        raise FxError(I18N.t("this effect's length stays"))


def set_strength(P: dict, fx: dict, x: float) -> None:
    k = fx["kind"]
    L = _layer(P, fx["layer"])
    if k in ("zoom", "punch"):
        _zoom_strength(L, fx, x)
    elif k == "room":
        ch = ROOM_LOOKS[L["room"]["look"]][0]
        top = {"dim": 0.95, "blur": 40.0, "grey": 1.0}[ch]
        x = min(top, max(0.02, float(x)))
        peak = fx["strength"] or 1.0
        c = L["room"][ch]
        c["keys"] = [[v[0], round(min(top, float(v[1]) * x / peak), 4), *v[2:]] for v in c["keys"]]
    elif k == "framing":
        L["zoom"] = round(min(3.0, max(1.01, float(x))), 4)
    elif k == "shake":
        x = min(0.15, max(0.002, float(x)))
        dev = fx["strength"] or 1e-6
        for a in L["anchor"]:
            if isinstance(a, dict) and "values" in a:
                base = float(a["values"][-1])
                a["values"] = [round(base + (float(v) - base) * x / dev, 4) for v in a["values"]]
    elif k == "flash":
        x = min(1.0, max(0.05, float(x)))
        peak = fx["strength"] or 1.0
        for f in range(fx["f"], fx["f"] + fx["len"]):
            if str(f) in L["flash_over"]:
                L["flash_over"][str(f)] = round(min(1.0, float(L["flash_over"][str(f)]) * x / peak), 3)
    elif L.get("type") == "solid":
        x = min(1.0, max(0.02, float(x)))
        peak = fx["strength"] or 1.0
        op = L.get("opacity")
        if _keys(op):
            op["keys"] = [[v[0], round(min(1.0, float(v[1]) * x / peak), 4), *v[2:]] for v in op["keys"]]
        elif isinstance(op, dict) and op.get("values"):
            op["values"] = [round(min(1.0, float(v) * x / peak), 4) for v in op["values"]]
        else:
            L["opacity"] = round(x, 4)
    else:
        raise FxError(I18N.t("this effect has no strength to change"))


def set_ease(P: dict, fx: dict, ease: str) -> None:
    from .edkeys import ease_ok
    ease = ease.replace(" ", "")
    if ease not in EASES and not (ease.startswith("cubic(") and ease_ok(ease)):
        raise FxError(I18N.t("an ease from the list, or a curve with its two handles"))
    L = _layer(P, fx["layer"])
    if fx["kind"] == "zoom":
        _zoom_ease(L, fx, ease)
        return
    curve = L.get("opacity") if L.get("type") == "solid" else None
    if not _keys(curve):
        raise FxError(I18N.t("this effect has no ease to change"))
    curve["keys"] = [[v[0], v[1], ease, *v[3:]] for v in curve["keys"][:-1]] + [curve["keys"][-1]]


def remove(P: dict, fx: dict) -> None:
    k = fx["kind"]
    if k == "rgb":
        gone = _group(P, fx["layer"])
        P["layers"] = [x for x in P["layers"] if not any(x is g for g in gone)]
        return
    L = _layer(P, fx["layer"])
    if L.get("type") == "solid":
        P["layers"] = [x for x in P["layers"] if x is not L]
    elif k in ("zoom", "punch"):
        _zoom_remove(L, fx)
    elif k == "framing":
        L.pop("zoom", None)
    elif k == "shake":
        L["anchor"] = [float(a["values"][-1]) if isinstance(a, dict) and "values" in a else a for a in L["anchor"]]
        if L["anchor"] == [0.5, 0.5]:
            L.pop("anchor")
        _unshake(L)
    elif k == "flash":
        for f in range(fx["f"], fx["f"] + fx["len"]):
            L["flash_over"].pop(str(f), None)
        if not L["flash_over"]:
            L.pop("flash_over")
    elif k in ("white", "black"):
        key = "flash_white" if k == "white" else "black"
        run = set(range(fx["f"], fx["f"] + fx["len"]))
        L[key] = [int(v) for v in L[key] if int(v) not in run]
        if not L[key]:
            L.pop(key)
    elif k == "stutter":
        L["in"] = int(L["jumps"][0][1])
        L.pop("jumps")
    elif k == "mirror":
        L.pop("mirror", None)
    elif k == "room":
        L.pop("room", None)
    elif k in ("push", "whip", "crossfade", "overlap"):
        _hard_cut(P, L, fx)
    else:
        raise FxError(I18N.t("this effect cannot be removed here"))


def _hard_cut(P: dict, B: dict, fx: dict) -> None:
    """A transition becomes a plain cut in the middle of the overlap: the shot before ends there, the one after starts
    there (its picture from the same moment of its clip), their moves / fades gone."""
    S = _shots(P)
    i = next(i for i, x in enumerate(S) if x is B)
    A = S[i - 1]
    c = fx["f"] + fx["len"] // 2
    A["end"] = c - 1
    for k in ("dx", "dy"):
        if _keys(A.get(k)):
            A.pop(k)
    EL._trim_front(B, c)
    for k in ("dx", "dy", "opacity"):
        if _keys(B.get(k)):
            B.pop(k)


# ------------------------------------------------------------------------------------------------ new ones
def _shot_at(P: dict, f: int) -> dict | None:
    return next((x for x in _shots(P) if int(x["start"]) <= f <= int(x["end"])), None)


def _room_curves(L: dict) -> list[dict]:
    return [c for c in ((L.get("room") or {}).get(k) for k in ("dim", "blur", "grey")) if _keys(c)]


def _zoom_now(L: dict) -> float | None:
    z = L.get("zoom", 1.0)
    return float(z) if isinstance(z, (int, float)) else None


def _solid(P: dict, prefix: str, f: int, n: int, color: list, blend: str, opacity) -> str:
    W, H, N = int(P.get("width", 1920)), int(P.get("height", 1080)), int(P["frames"])
    lid = _free_id(P, prefix)
    P["layers"].append({"type": "solid", "id": lid, "start": f, "end": min(N - 1, f + n - 1), "rect": [0, 0, W, H],
                        "color": color, "blend": blend, "opacity": opacity})
    return lid


def add(P: dict, kind: str, f: int, seed: int = 1, talk: bool = False) -> str:
    """A new effect of `kind` (ADD) at frame f (on the shot under it, or the cut nearest it); its id. A zoom on a shot
    that already zooms goes in beside its other moves, near a shot's end it starts earlier; a flash / black frame where
    no clip is under f (an end card, a video made from zero) is a colour layer over everything."""
    import random
    if kind not in ADD:
        raise FxError(I18N.t("no such effect: {effect}", effect=kind))
    if talk and kind in MOVES_PICTURE:
        raise FxError(I18N.t("a stutter would pull the picture away from the voice - not on a talking video"))
    W, H, fps, N = int(P.get("width", 1920)), int(P.get("height", 1080)), float(P["fps"]), int(P["frames"])
    f = max(0, min(N - 1, int(f)))
    rng = random.Random(seed * 7919 + f)
    sec = lambda s: max(1, int(round(s * fps)))           # noqa: E731
    S = _shot_at(P, f)
    if S is None:
        if kind == "flash":
            n = min(len(FLASH), N - f)
            return f"solid_flash:{_solid(P, 'flash_', f, n, [1, 1, 1], 'screen', {'start': f, 'values': list(FLASH[:n])})}:{f}"
        if kind == "black_frame":
            return f"solid_black:{_solid(P, 'black_', f, 1, [0, 0, 0], 'normal', 1.0)}:{f}"
        raise FxError(I18N.t("this effect works on a clip - there is no clip under {frame}", frame=f"f{f}"))
    s, e = int(S["start"]), int(S["end"])
    if kind == "rgb_split":
        return _rgb_split(P, S, f, W)
    if kind in ("flash", "black_frame"):
        if kind == "flash":                             # bright, then a quick decay (compose: an exposure flash)
            S.setdefault("flash_over", {}).update({str(f + i): v for i, v in enumerate(FLASH) if f + i <= e})
            return f"flash:{S['id']}:{f}"
        S["black"] = sorted(set(int(v) for v in S.get("black") or []) | {f})
        return f"black:{S['id']}:{f}"
    if kind == "stutter":
        if S.get("jumps") or S.get("hold"):
            raise FxError(I18N.t("this shot already has a stutter or a held frame"))
        if e - s < 7:
            raise FxError(I18N.t("this shot is too short for that effect"))
        f = max(s + 1, min(f, e - 6))                      # (near the end: it starts earlier)
        i0, k = EL._src_at(S, f), 3 if e - s + 1 >= sec(0.8) else 2
        S["jumps"] = [[s, int(S.get("in", 0))], [f, i0], [f + k, i0], [f + 2 * k, i0], [f + 3 * k, i0 + k]]
        S.pop("in", None)
        S["in"] = S["jumps"][0][1]
        return f"stutter:{S['id']}:{f}"
    if kind == "shake":                                  # a handheld jolt: smooth, decaying, inside its own 6 % zoom
        if any(isinstance(a, dict) for a in (S.get("anchor") or [])):
            raise FxError(I18N.t("this shot already shakes"))
        if e - s < 6:
            raise FxError(I18N.t("this shot is too short for that effect"))
        a, n = _room(_keys_of(S), s, e, f, max(8, min(18, sec(0.5))), 6)
        z = _val(S["zoom"]["keys"], a)
        _shake_bump(S, a, n)
        ax0, ay0 = [float(v) for v in (S.get("anchor") or [0.5, 0.5])]
        step = max(2, int(round(fps / 16)))             # a new direction every ~1/16 s: about 8 swings a second
        S["anchor"] = [{"start": a, "values": [round(c0 + v, 5) for v in _swing(rng, n, step, z)] + [c0]}
                       for c0 in (ax0, ay0)]
        return f"shake:{S['id']}:{a}"
    if kind == "punch_in" and f <= s and not _keys(S.get("zoom")):
        S["zoom"] = round((_zoom_now(S) or 1.0) * 1.15, 4)
        return f"framing:{S['id']}:{s}"
    if e - s < 4:
        raise FxError(I18N.t("this shot is too short for that effect"))
    ks = _keys_of(S)
    if kind == "lean_in":                                # 15 % closer on a word: glides in, holds, eases back out
        if e - s < sec(0.6):
            raise FxError(I18N.t("this shot is too short for that effect"))
        a, n = _room(ks, s, e, f, sec(1.6), sec(0.6))
        v, tail = _val(ks, a), _ease_at(ks, a + n)
        _clear(ks, a - 1, a + n)
        k_in, k_out = max(2, min(sec(0.2), n // 3)), max(2, min(sec(0.4), n // 3))
        _put(ks, a, v, "glide")
        _put(ks, a + k_in, v * 1.15, "linear")
        _put(ks, a + n - k_out, v * 1.15, "easy")
        _put(ks, a + n, v, tail)
        S["track"] = "face"
        _done(S)
        return f"zoom:{S['id']}:{a}"
    if kind == "slow_push":                              # 12 % closer over ~3 s, eased both ends; it stays in
        if e - s < sec(1.2):
            raise FxError(I18N.t("this shot is too short for that effect"))
        a, n = _room(ks, s, e, f, sec(3.0), sec(1.2))
        v, tail = _val(ks, a), _ease_at(ks, a + n)
        _clear(ks, a - 1, a + n)
        _scale_after(ks, a + n, 1.12)
        _put(ks, a, v, "easy")
        _put(ks, a + n, v * 1.12, tail)
        S["track"] = "face"
        _done(S)
        return f"zoom:{S['id']}:{a}"
    a, _ = _room(ks, s, e, f, 0, 0)                      # a punch-in: a step closer from here on (15 %)
    v, tail = _val(ks, a), _ease_at(ks, a)
    _scale_after(ks, a, 1.15)
    _put(ks, a - 1, v, "hold")
    _put(ks, a, v * 1.15, tail)
    _done(S)
    return f"punch:{S['id']}:{a}"


def _swing(rng, n: int, step: int, z: float) -> list[float]:
    """A shake's zoom-point offsets over its n frames: a new direction every `step` frames (alternating, eased between
    them - no frame-to-frame jitter), dying away inside the room its 6 % zoom leaves (about 26 px at 1080 wide)."""
    sgn = rng.choice((-1, 1))
    pts = [sgn * (1 if j % 2 == 0 else -1) * rng.uniform(0.55, 1.0) for j in range(n // step + 2)]
    out = []
    for i in range(n):
        j, t = divmod(i, step)
        u = t / step
        u = u * u * (3 - 2 * u)
        zoom = z * (1 + 0.06 * (1 - i / n) ** 2)        # (its own zoom, easing back: compose crops inside it)
        out.append(0.024 * (1 - i / n) ** 2 / zoom * (pts[j] + (pts[j + 1] - pts[j]) * u))
    return out


def _rgb_split(P: dict, S: dict, f: int, W: int, n: int = 3) -> str:
    """Three copies of the shot over n frames - green as it is, red and blue added, pushed apart in opposite directions
    and closing (24 -> 12 -> 4 px at 1080 wide) - a little larger (5 %) so no edge shows; they follow the shot's own
    move, zoom and face. Right above the shot (graphics stay on top)."""
    from .compose import Curve
    s, e = int(S["start"]), int(S["end"])
    f = min(f, max(s, e - n + 1))
    n = max(1, min(n, e - f + 1))
    base = _free_id(P, "rgb_", rgb=True)
    x, y, w, h = [float(v) for v in (S.get("rect") or [0, 0, W, int(P.get("height", 1080))])]
    big = [round(x - 0.025 * w, 2), round(y - 0.025 * h, 2), round(w * 1.05, 2), round(h * 1.05, 2)]
    try:
        dx = Curve(S.get("dx"), P.get("curves") or {}, 0.0)
    except (KeyError, ValueError, TypeError):
        dx = lambda _f: 0.0                             # noqa: E731
    at = next(i for i, L in enumerate(P["layers"]) if L is S) + 1
    for k, (tint, blend, sgn) in enumerate((([0, 1, 0], "normal", 0), ([1, 0, 0], "add", 1), ([0, 0, 1], "add", -1))):
        L = EL._trim_front({kk: copy.deepcopy(v) for kk, v in S.items() if kk not in RGB_DROP}, f)
        L.update(id=f"{base}_{k}", end=f + n - 1, rect=big, tint=tint, blend=blend,
                 dx={"start": f, "values": [round(dx(f + i) + sgn * RGB_SPLIT[min(i, len(RGB_SPLIT) - 1)] * W, 2)
                                            for i in range(n)]})
        P["layers"].insert(at + k, L)
    return f"rgb:{base}:{f}"


def _free_id(P: dict, prefix: str, rgb: bool = False) -> str:
    ids = {str(x.get("id")) for x in P["layers"]}
    k = 1
    while (f"{prefix}e{k:02d}" in ids if not rgb else any(i.startswith(f"rgb_e{k:02d}_") for i in ids)):
        k += 1
    return f"{prefix}e{k:02d}"


def availability(P: dict, talk: bool = False) -> dict:
    """Why a kind cannot go where the playhead is - before the click, never an error after it (the user, 2026-10-26:
    "show why some effects or transitions cant be used in that specific [moment] of the video so people know"): each
    kind tried on a copy of the shot -> {"shots": {shot id: {kind: why}}, "cuts": {} (no effect of a cut is offered any
    more), "none": {kind: why} (no clip under the playhead)}; "" = it can."""
    def tried(kind: str, f: int, sh: dict) -> str:
        Q = {**P, "layers": [copy.deepcopy(sh)]}
        try:
            add(Q, kind, f, talk=talk)
            return ""
        except FxError as e:
            return str(e)
    out = {"shots": {}, "cuts": {}, "none": {}}
    for sh in _shots(P):                                # (each tried on its shot alone: a long video stays quick)
        mid = (int(sh["start"]) + int(sh["end"])) // 2
        out["shots"][str(sh["id"])] = {k: tried(k, mid, sh) for k in ADD}
    for k in ADD:
        out["none"][k] = "" if k in ("flash", "black_frame") else I18N.t(
            "no clip under the playhead - this effect changes a clip's picture")
    return out


def apply_op(P: dict, o: dict, talk: bool = False) -> str:
    """One of the Editor's effect ops on P (in place) -> a line for the record (frame + timecode by the caller)."""
    op = o.get("op")
    if op == "fxadd":
        fid = add(P, str(o.get("kind")), int(o["f"]), talk=talk)
        return f"effect {o.get('kind')} added at f{int(o['f'])} ({fid})"
    fx = find(P, str(o.get("id")))
    if op == "fxmove":
        by = move(P, fx, int(o["by"]))
        return f"{fx['label']} at f{fx['f']} moved {by:+d} frames"
    if op == "fxremove":
        remove(P, fx)
        return f"{fx['label']} at f{fx['f']} removed"
    if op == "fxset":
        bits = []
        if o.get("len") is not None:
            set_len(P, fx, int(o["len"]))
            bits.append(f"{int(o['len'])} frames long")
        if o.get("strength") is not None:
            set_strength(P, fx, float(o["strength"]))
            bits.append(f"strength {float(o['strength']):g}")
        if o.get("ease"):
            set_ease(P, fx, str(o["ease"]))
            bits.append(f"ease {o['ease']}")
        return f"{fx['label']} at f{fx['f']}: " + ", ".join(bits)
    raise FxError(I18N.t("no such change: {op}", op=str(op)))


# ------------------------------------------------------------------------------------------------ self-check
def selfcheck() -> dict:
    import time
    t0, lines, ok = time.time(), [], True

    def case(name, cond):
        nonlocal ok
        ok = ok and bool(cond)
        lines.append(f"{'PASS' if cond else 'FAIL'} {name}")

    def plan():
        return {"fps": 25.0, "frames": 300, "width": 1080, "height": 1920, "sources": {"A": {"frames": 2000}},
                "layers": [{"type": "clip", "id": "s01_A", "src": "A", "start": 0, "end": 99, "in": 100,
                            "zoom": {"keys": [[90, 1.0, "in"], [99, 1.7]]}, "flash_over": {"10": 0.9, "11": 0.55}},
                           {"type": "clip", "id": "s02_A", "src": "A", "start": 100, "end": 199, "in": 300,
                            "zoom": {"keys": [[100, 1.7, "out"], [109, 1.0]]}, "black": [150]},
                           {"type": "clip", "id": "s03_A", "src": "A", "start": 190, "end": 299, "in": 500,
                            "dx": {"keys": [[190, -1080, "out3"], [199, 0]]}, "zoom": 1.12},
                           {"type": "solid", "id": "leak_03", "start": 220, "end": 234, "color": [1, .55, .2],
                            "blend": "screen", "opacity": {"keys": [[220, 0, "smooth"], [227, 0.55, "smooth"], [234, 0]]}}]}
    P = plan()
    E = effects(P)
    kinds = [(x["kind"], x["f"]) for x in E]
    case("the effects are found: a zoom into the cut, a flash, a zoom out of it, a black frame, the whip, the framing, "
         "a light leak", kinds == [("flash", 10), ("zoom", 90), ("zoom", 100), ("whip", 190), ("framing", 190),
                                   ("light_leak", 220), ("black", 150)] or sorted(kinds) == sorted(
             [("flash", 10), ("zoom", 90), ("zoom", 100), ("whip", 190), ("framing", 190), ("light_leak", 220),
              ("black", 150)]))
    z = next(x for x in E if x["id"] == "zoom:s01_A:90")
    case("a zoom chip: label, length, strength (its peak), ease", z["label"] == "Zoom in" and z["len"] == 10
         and z["strength"] == 1.7 and z["ease"] == "in")
    apply_op(P, {"op": "fxset", "id": "zoom:s01_A:90", "len": 5, "strength": 1.3, "ease": "smooth"})
    k = P["layers"][0]["zoom"]["keys"]
    case("its length, strength and ease changed", k == [[90, 1.0, "smooth"], [94, 1.3]])
    apply_op(P, {"op": "fxmove", "id": "zoom:s01_A:90", "by": -10})
    case("moved 10 frames earlier", P["layers"][0]["zoom"]["keys"][0][0] == 80)
    apply_op(P, {"op": "fxmove", "id": "flash:s01_A:10", "by": 5})
    case("a flash moved", P["layers"][0]["flash_over"] == {"15": 0.9, "16": 0.55})
    apply_op(P, {"op": "fxset", "id": "flash:s01_A:15", "strength": 0.45})
    case("a flash softer (its frames in proportion)", P["layers"][0]["flash_over"] == {"15": 0.45, "16": 0.275})
    apply_op(P, {"op": "fxremove", "id": "whip:s03_A:190"})
    case("the whip removed = a plain cut in the middle of the overlap", P["layers"][1]["end"] == 194
         and P["layers"][2]["start"] == 195 and "dx" not in P["layers"][2] and P["layers"][2]["in"] == 505)
    apply_op(P, {"op": "fxset", "id": "light_leak:leak_03:220", "len": 8, "strength": 0.3})
    lk = next(x for x in P["layers"] if x["id"] == "leak_03")
    case("a light leak shorter and fainter", lk["end"] == 227 and max(v[1] for v in lk["opacity"]["keys"]) == 0.3)
    apply_op(P, {"op": "fxremove", "id": "zoom:s02_A:100"})
    case("a zoom removed: the shot keeps its resting size", "zoom" not in P["layers"][1])
    bad = []
    for o in ({"op": "fxadd", "kind": "stutter", "f": 120}, {"op": "fxset", "id": "black:s02_A:150", "strength": 2},
              {"op": "fxadd", "kind": "nope", "f": 1}):
        try:
            apply_op(copy.deepcopy(P), o, talk=True)
            bad.append(o)
        except FxError:
            pass
    case("what cannot be done is refused (a stutter on a talking video, no strength, no such kind)", not bad)
    Q = copy.deepcopy(P)
    line = apply_op(Q, {"op": "fxmove", "id": "black:s02_A:150", "by": 80})
    case("dragged past its shot's end, an effect stops at the edge (no error)", Q["layers"][1]["black"] == [194]
         and "+44" in line)
    Q = plan()
    for kind, f in (("shake", 260), ("rgb_split", 40), ("flash", 60), ("black_frame", 160), ("punch_in", 250)):
        apply_op(Q, {"op": "fxadd", "kind": kind, "f": f})
    E = {(x["kind"], x["f"]) for x in effects(Q)}
    case("new effects at the playhead: a shake, an RGB split, a flash, a black frame, a punch-in",
         {("shake", 260), ("rgb", 40), ("flash", 60), ("black", 160), ("punch", 250)} <= E)
    s3 = Q["layers"][next(i for i, L in enumerate(Q["layers"]) if L["id"] == "s03_A")]
    xs = s3["anchor"][0]["values"][:-1]
    flips = sum(1 for u, v, w in zip(xs, xs[1:], xs[2:]) if (v - u) * (w - v) < 0)
    case("a shake swings smoothly (no frame-to-frame jitter) and dies away inside its own zoom",
         flips <= len(xs) // 2 and abs(xs[-1] - 0.5) < abs(max(xs[:4], key=lambda v: abs(v - 0.5)) - 0.5)
         and max(abs(v - 0.5) for v in xs) < (1 - 1 / 1.06) / 2 and s3["anchor"][0]["values"][-1] == 0.5)
    rg = [L for L in Q["layers"] if str(L["id"]).startswith("rgb_")]
    s1i = next(i for i, L in enumerate(Q["layers"]) if L["id"] == "s01_A")
    case("an RGB split: three copies right above the shot (green, red and blue apart in opposite directions, closing), "
         "5 % larger, showing the shot's own frames, its zoom kept",
         [L["tint"] for L in rg] == [[0, 1, 0], [1, 0, 0], [0, 0, 1]] and Q["layers"][s1i + 1] is rg[0]
         and rg[1]["dx"]["values"][0] > rg[1]["dx"]["values"][-1] > 0 > rg[2]["dx"]["values"][0]
         and rg[0]["rect"][2] == 1080 * 1.05 and all(EL._src_at(L, 40) == 140 for L in rg)
         and rg[0]["zoom"] == plan()["layers"][0]["zoom"])
    fo = {k: v for k, v in Q["layers"][s1i]["flash_over"].items() if int(k) >= 60}
    case("a flash: bright, then a quick decay over 4 frames", list(fo.values()) == list(FLASH))
    apply_op(Q, {"op": "fxmove", "id": "rgb:rgb_e01:40", "by": 10})
    rg = [L for L in Q["layers"] if str(L["id"]).startswith("rgb_")]
    case("an RGB split moved: made again there (its frames follow)", len(rg) == 3 and all(EL._src_at(L, 50) == 150 for L in rg))
    F = plan()                                           # 2026-10-27: the face-led ones
    apply_op(F, {"op": "fxadd", "kind": "lean_in", "f": 120})
    apply_op(F, {"op": "fxadd", "kind": "slow_push", "f": 220})
    s1, s2, s3 = F["layers"][0], F["layers"][1], F["layers"][2]
    lz = [k for k in (s2["zoom"]["keys"] if isinstance(s2.get("zoom"), dict) else []) if k[0] >= 120]
    pz = [k for k in s3["zoom"]["keys"] if k[0] >= 220]
    case("face-led: a lean-in 15 % that glides in and eases out, a slow push 12 % eased (no room look) - each on the face",
         max(float(k[1]) for k in lz) == 1.15 and lz[0][2] == "glide" and s2["track"] == "face"
         and abs(max(float(k[1]) for k in pz) - 1.12 * 1.12) < 1e-6 and pz[0][2] == "easy" and "room" not in s3
         and s3["track"] == "face")
    s1["room"] = {"look": "spotlight", "dim": {"keys": [[20, 0, "easy"], [28, 0.7, "linear"], [51, 0.7, "easy"], [59, 0]]}}
    sp = {x["id"]: x for x in effects(F)}.get("room:s01_A:20")
    case("an older plan's spotlight is still its own chip", sp is not None and sp["label"] == "Spotlight"
         and sp["strength"] == 0.7)
    apply_op(F, {"op": "fxmove", "id": "room:s01_A:20", "by": 10})
    apply_op(F, {"op": "fxset", "id": "room:s01_A:30", "strength": 0.5, "len": 30})
    rk = s1["room"]["dim"]["keys"]
    case("a spotlight moved, softer, shorter - then removed", rk[0][0] == 30 and rk[-1][0] == 59
         and max(v[1] for v in rk) == 0.5)
    apply_op(F, {"op": "fxremove", "id": "room:s01_A:30"})
    case("...gone", "room" not in s1)
    gone = []
    for k in ("push_in", "pull_out", "zoom_through", "white_flash", "colour_flash", "light_leak", "dip_black",
              "spotlight"):
        try:
            add(plan(), k, 50)
            gone.append(k)
        except FxError:
            pass
    case("the kinds no longer offered are refused as new ones", not gone)
    # 2026-10-26 (the user: "most of the time i cant even use them due to an error"): the quick draft's first shot
    # zooms in slowly (a hold key from a trim in front), shots that zoom took no other zoom, a punch-in never moved
    R = {"fps": 25.0, "frames": 400, "width": 1920, "height": 1080, "sources": {"A": {"frames": 2000}},
         "layers": [{"type": "clip", "id": "s01_A", "src": "A", "start": 0, "end": 199, "in": 0,
                     "zoom": {"keys": [[-440, 1.0, "hold"], [2, 1.0, "smooth"], [10, 1.08, "hold"]]}},
                    {"type": "clip", "id": "s02_A", "src": "A", "start": 200, "end": 299, "in": 500, "zoom": 1.15},
                    {"type": "solid", "id": "box03", "start": 300, "end": 349, "rect": [1372, 732, 496, 286]},
                    {"type": "clip", "id": "s03_A", "src": "A", "start": 300, "end": 349, "in": 800, "zoom": 1.3,
                     "rect": [1380, 740, 480, 270]},
                    {"type": "solid", "id": "end_bg", "start": 350, "end": 399}]}
    E = effects(R)
    case("a slow zoom after a trimmed hold is a Zoom in (not a Punch-in); layout boxes are no effects",
         [(x["kind"], x["label"], x["f"], x["len"]) for x in E if x["kind"] in ("zoom", "punch")] == [("zoom", "Zoom in", 2, 9)]
         and not any(x["layer"] in ("box03", "end_bg") for x in E))
    apply_op(R, {"op": "fxmove", "id": "zoom:s01_A:2", "by": 5})
    for kind, f in (("slow_push", 30), ("punch_in", 150), ("shake", 120)):
        apply_op(R, {"op": "fxadd", "kind": kind, "f": f})
    E = {x["id"]: x for x in effects(R)}
    zs = sorted((x["kind"], x["label"], x["f"]) for x in E.values() if x["layer"] == "s01_A" and x["kind"] != "shake")
    case("one shot, many zooms: its zoom in moved, a slow push, a punch-in and a shake - each its own chip",
         zs == [("punch", "Punch-in", 150), ("zoom", "Zoom in", 7), ("zoom", "Zoom in", 30)] and "shake:s01_A:120" in E)
    ks = R["layers"][0]["zoom"]["keys"]
    z = lambda f: _val(sorted(ks, key=lambda k: k[0]), f)          # noqa: E731
    case("the zooms stack: after the slow push and the punch-in the shot is as close as both left it",
         abs(z(20) - 1.08) < 1e-3 and abs(z(110) - 1.08 * 1.12) < 1e-3 and abs(z(155) - 1.08 * 1.12 * 1.15) < 1e-3)
    apply_op(R, {"op": "fxmove", "id": "punch:s01_A:150", "by": -6})
    apply_op(R, {"op": "fxmove", "id": "punch:s01_A:144", "by": 9})
    case("a punch-in moves both ways", "punch:s01_A:153" in {x["id"] for x in effects(R)})
    apply_op(R, {"op": "fxmove", "id": "zoom:s01_A:30", "by": -200})
    case("a zoom dragged into the one before it stops beside it", "zoom:s01_A:16" in {x["id"] for x in effects(R)})
    apply_op(R, {"op": "fxremove", "id": "shake:s01_A:120"})
    apply_op(R, {"op": "fxremove", "id": "zoom:s01_A:16"})
    case("removing the shake and the slow push leaves the rest as it was (the punch-in 15 % over the zoom in)",
         "anchor" not in R["layers"][0] and abs(_val(R["layers"][0]["zoom"]["keys"], 100) - 1.08) < 1e-3
         and abs(_val(R["layers"][0]["zoom"]["keys"], 156) - 1.08 * 1.15) < 1e-3)
    apply_op(R, {"op": "fxadd", "kind": "flash", "f": 380})
    apply_op(R, {"op": "fxadd", "kind": "black_frame", "f": 390})
    E = {x["kind"] for x in effects(R)}
    case("a flash and a black frame on an end card (no clip under them) are colour layers", {"solid_flash", "solid_black"} <= E)
    return {"passed": ok, "seconds": round(time.time() - t0, 3), "lines": lines}
