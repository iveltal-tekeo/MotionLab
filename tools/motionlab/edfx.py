"""The Editor's effects (0.6.0 step 6; the user, 2026-10-25: "so if we do the mini editor on the version we can maybe
choose some effects, edit them?"): every effect of a plan as one chip - found in its layers the way the quick draft
(motionlab\\draft.py build_layers) and Claude write them - and what the Editor changes on one: move it, its length,
its strength, its ease, remove it; new ones at a frame. Pure plan changes, in place; motionlab\\miniedit.apply runs
them as the ops fxmove / fxset / fxremove / fxadd. The sound effects follow by themselves (sfx.plan_cues reads the
effects from the layers on every build).

    effects(plan) -> [{id, kind, label, f, len, strength, ease, layer, can}]   frames are the plan's; id = kind:layer:f
        (the same plan gives the same ids); can = what the chip offers: move, len, strength, ease, remove
    move(P, fx, by) / set_len(P, fx, n) / set_strength(P, fx, x) / set_ease(P, fx, ease) / remove(P, fx)
    add(P, kind, f) -> the new effect's id; ADD = the kinds the Editor offers

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

EASES = ("linear", "smooth", "in", "out", "hold")
ADD = ("punch_in", "push_in", "pull_out", "zoom_through", "shake", "flash", "white_flash", "black_frame",
       "colour_flash", "light_leak", "rgb_split", "dip_black", "dip_white", "stutter")
CUT_KINDS = {"zoom_through", "white_flash", "dip_black", "dip_white"}       # placed on the cut nearest the frame
MOVES_PICTURE = {"stutter"}                         # shifts the picture against its sound: not on a talking video


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
        if t == "clip" and lid.startswith("rgb_"):
            rgb.setdefault(lid.rsplit("_", 1)[0], []).append(L)
            continue
        if t == "solid":
            out.append(_solid_fx(L))
            continue
        if t != "clip":
            continue
        an = L.get("anchor")
        shaky = isinstance(an, list) and any(isinstance(a, dict) and "values" in a for a in an)
        zk = _keys(L.get("zoom"))
        if zk and len({round(float(k[1]), 4) for k in zk}) > 1:
            vals = [float(k[1]) for k in zk]
            step = any((k[2] if len(k) > 2 else "linear") == "hold" for k in zk[:-1])
            f0, f1 = int(zk[0][0]), int(zk[-1][0])
            if step:                                        # a punch-in: the value jumps at the key after "hold"
                at = next(int(zk[i + 1][0]) for i, k in enumerate(zk[:-1]) if (k[2] if len(k) > 2 else "") == "hold")
                out.append(_fx("punch", "Punch-in", lid, max(s, at), e - max(s, at) + 1, ["move", "strength", "remove"],
                               round(max(vals) / max(min(vals), 1e-6), 3)))
            else:
                out.append(_fx("zoom", "Zoom in" if vals[-1] >= vals[0] else "Zoom out", lid, f0, f1 - f0 + 1,
                               ["move", "len", "strength", "ease", "remove"], round(max(vals) / max(min(vals), 1e-6), 3),
                               zk[0][2] if len(zk[0]) > 2 else "linear"))
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


# ------------------------------------------------------------------------------------------------ changing one
def move(P: dict, fx: dict, by: int) -> None:
    if by == 0:
        return
    k, a, b = fx["kind"], fx["f"] + by, fx["f"] + fx["len"] - 1 + by
    N = int(P["frames"])
    if not (0 <= a and b < N):
        raise FxError(I18N.t("{frame} is outside the video", frame=f"f{a if a < 0 else b}"))
    if k in ("rgb",):
        for L in _group(P, fx["layer"]):
            EL._shift(L, by)
        return
    L = _layer(P, fx["layer"])
    if L.get("type") == "solid":
        EL._shift(L, by)
        return
    if not _inside(L, a, b) and k not in ("zoom",):
        raise FxError(I18N.t("the effect stays on its shot ({range})", range=f"f{L['start']}-f{L['end']}"))
    if k in ("zoom", "punch"):
        L["zoom"]["keys"] = [[int(x[0]) + by, *x[1:]] for x in L["zoom"]["keys"]]
    elif k == "shake":
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


def set_len(P: dict, fx: dict, n: int) -> None:
    n = max(2, int(n))
    k, f0, old = fx["kind"], fx["f"], fx["len"]
    if k == "rgb":
        for L in _group(P, fx["layer"]):
            L["end"] = min(int(P["frames"]) - 1, int(L["start"]) + n - 1)
        return
    L = _layer(P, fx["layer"])
    if k == "zoom":
        sc = (n - 1) / max(1, old - 1)
        L["zoom"]["keys"] = [[f0 + int(round((int(x[0]) - f0) * sc)), *x[1:]] for x in L["zoom"]["keys"]]
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
        x = min(3.0, max(1.01, float(x)))
        ks = L["zoom"]["keys"]
        vals = [float(v[1]) for v in ks]
        lo, r = min(vals), max(vals) / max(min(vals), 1e-6)
        if r <= 1.0001:
            return
        for v in ks:
            v[1] = round(lo + (float(v[1]) - lo) * (x - 1) / (r - 1), 4)
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
    if ease not in EASES:
        raise FxError(I18N.t("an ease: linear, smooth, in, out or hold"))
    L = _layer(P, fx["layer"])
    curve = L.get("zoom") if fx["kind"] == "zoom" else L.get("opacity") if L.get("type") == "solid" else None
    if not _keys(curve):
        raise FxError(I18N.t("this effect has no ease to change"))
    curve["keys"] = [[v[0], v[1], ease] for v in curve["keys"][:-1]] + [curve["keys"][-1]]


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
        lo = min(float(v[1]) for v in L["zoom"]["keys"])
        if abs(lo - 1.0) < 1e-4:
            L.pop("zoom")
        else:
            L["zoom"] = round(lo, 4)
    elif k == "framing":
        L.pop("zoom", None)
    elif k == "shake":
        L["anchor"] = [float(a["values"][-1]) if isinstance(a, dict) and "values" in a else a for a in L["anchor"]]
        if L["anchor"] == [0.5, 0.5]:
            L.pop("anchor")
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
def _shot_at(P: dict, f: int) -> dict:
    S = next((x for x in _shots(P) if int(x["start"]) <= f <= int(x["end"])), None)
    if S is None:
        raise FxError(I18N.t("no shot under {frame}", frame=f"f{f}"))
    return S


def _cut_near(P: dict, f: int) -> tuple[dict, dict, int]:
    S = _shots(P)
    pairs = [(A, B) for A, B in zip(S, S[1:]) if int(B["start"]) == int(A["end"]) + 1]
    if not pairs:
        raise FxError(I18N.t("this effect goes on a cut - the video has no plain cut"))
    A, B = min(pairs, key=lambda p: abs(int(p[1]["start"]) - f))
    return A, B, int(B["start"])


def _zoom_now(L: dict) -> float | None:
    z = L.get("zoom", 1.0)
    return float(z) if isinstance(z, (int, float)) else None


def add(P: dict, kind: str, f: int, seed: int = 1, talk: bool = False) -> str:
    """A new effect of `kind` (ADD) at frame f (on the shot under it, or the cut nearest it); its id."""
    import random
    if kind not in ADD:
        raise FxError(I18N.t("no such effect: {effect}", effect=kind))
    if talk and kind in MOVES_PICTURE:
        raise FxError(I18N.t("a stutter would pull the picture away from the voice - not on a talking video"))
    W, H, fps, N = int(P.get("width", 1920)), int(P.get("height", 1080)), float(P["fps"]), int(P["frames"])
    rng = random.Random(seed * 7919 + f)
    sec = lambda s: max(1, int(round(s * fps)))           # noqa: E731
    if kind in CUT_KINDS:
        A, B, c = _cut_near(P, f)
        if kind == "zoom_through":
            za, zb = _zoom_now(A), _zoom_now(B)
            if za is None or zb is None:
                raise FxError(I18N.t("one of the two shots already has a zoom - change that one"))
            k = min(8, max(4, sec(0.24)), int(A["end"]) - int(A["start"]), int(B["end"]) - int(B["start"]))
            A["zoom"] = {"keys": [[c - k, round(za, 4), "in"], [c - 1, round(za * 1.7, 4)]]}
            B["zoom"] = {"keys": [[c, round(zb * 1.7, 4), "out"], [c + k - 1, zb]]}
            return f"zoom:{A['id']}:{c - k}"
        if kind == "white_flash":
            B.setdefault("flash_over", {}).update({str(c): 0.9, str(c + 1): 0.55, str(c + 2): 0.25})
            return f"flash:{B['id']}:{c}"
        h = min(8, max(4, sec(0.25)))
        lid = _free_id(P, "dip_")
        P["layers"].append({"type": "solid", "id": lid, "start": max(0, c - h), "end": min(N - 1, c + h),
                            "rect": [0, 0, W, H], "color": [0, 0, 0] if kind == "dip_black" else [1, 1, 1],
                            "opacity": {"keys": [[c - h, 0, "smooth"], [c, 1, "smooth"], [c + h, 0]]}})
        return f"dip:{lid}:{max(0, c - h)}"
    if kind in ("colour_flash", "light_leak"):
        if kind == "colour_flash":
            lid = _free_id(P, "colorflash_")
            col = [[1.0, 0.25, 0.6], [0.2, 0.8, 1.0], [1.0, 0.6, 0.15]][rng.randrange(3)]
            P["layers"].append({"type": "solid", "id": lid, "start": f, "end": min(N - 1, f + 2), "rect": [0, 0, W, H],
                                "color": col, "blend": "screen", "opacity": {"start": f, "values": [0.65, 0.35, 0.12]}})
            return f"colour_flash:{lid}:{f}"
        n = min(N - f, sec(0.6))
        lid = _free_id(P, "leak_")
        P["layers"].append({"type": "solid", "id": lid, "start": f, "end": f + n - 1,
                            "rect": [round(W * 0.35), 0, W - round(W * 0.35), H], "color": [1.0, 0.55, 0.2],
                            "blend": "screen", "opacity": {"keys": [[f, 0, "smooth"], [f + n // 2, 0.55, "smooth"],
                                                                    [f + n - 1, 0]]}})
        return f"light_leak:{lid}:{f}"
    S = _shot_at(P, f)
    s, e = int(S["start"]), int(S["end"])
    if kind == "rgb_split":
        f = min(f, max(s, e - 2))
        base = _free_id(P, "rgb_", rgb=True)
        z = _zoom_now(S) or 1.0
        for k, (tint, blend, dx) in enumerate((([0, 1, 1], "normal", 0), ([1, 0, 0], "add", round(0.012 * W)))):
            P["layers"].append({"type": "clip", "id": f"{base}_{k}", "src": S["src"], "start": f, "end": min(e, f + 2),
                                "rect": S.get("rect") or [0, 0, W, H], "in": EL._src_at(S, f), "tint": tint,
                                "blend": blend, "dx": dx, "zoom": round(z, 4)})
        return f"rgb:{base}:{f}"
    if kind in ("flash", "black_frame"):
        if kind == "flash":
            S.setdefault("flash_over", {}).update({str(f): 0.6, **({str(f + 1): 0.3} if f + 1 <= e else {})})
            return f"flash:{S['id']}:{f}"
        S["black"] = sorted(set(int(v) for v in S.get("black") or []) | {f})
        return f"black:{S['id']}:{f}"
    if kind == "stutter":
        if S.get("jumps") or S.get("hold"):
            raise FxError(I18N.t("this shot already has a stutter or a held frame"))
        if e - f < 6:
            raise FxError(I18N.t("too close to the shot's end for a stutter"))
        i0, k = EL._src_at(S, f), 3 if e - s + 1 >= sec(0.8) else 2
        S["jumps"] = [[s, int(S.get("in", 0))], [f, i0], [f + k, i0], [f + 2 * k, i0], [f + 3 * k, i0 + k]]
        S.pop("in", None)
        S["in"] = S["jumps"][0][1]
        return f"stutter:{S['id']}:{f}"
    z0 = _zoom_now(S)
    if z0 is None:
        raise FxError(I18N.t("this shot already has a zoom - change that one"))
    if kind == "shake":
        if any(isinstance(a, dict) for a in (S.get("anchor") or [])):
            raise FxError(I18N.t("this shot already shakes"))
        n = min(10, e - f)
        if n < 3:
            raise FxError(I18N.t("too close to the shot's end for a shake"))
        amp = 0.025 / max(z0 * 1.06, 1.0)
        jit = [(1 - i / n) * amp for i in range(n)]
        S["zoom"] = round(z0 * 1.06, 4)
        ax0, ay0 = [float(a) for a in (S.get("anchor") or [0.5, 0.5])]
        S["anchor"] = [{"start": f, "values": [round(ax0 + j * rng.uniform(-1, 1), 4) for j in jit] + [ax0]},
                       {"start": f, "values": [round(ay0 + j * rng.uniform(-1, 1), 4) for j in jit] + [ay0]}]
        return f"shake:{S['id']}:{f}"
    if kind == "punch_in":
        if f <= s:
            S["zoom"] = round(z0 * 1.15, 4)
            return f"framing:{S['id']}:{s}"
        S["zoom"] = {"keys": [[s, z0, "hold"], [f, round(z0 * 1.15, 4)]]}
        return f"punch:{S['id']}:{f}"
    n = min(e - f, sec(1.5))
    if n < 3:
        raise FxError(I18N.t("too close to the shot's end for a zoom"))
    z1 = round(z0 * 1.08, 4)
    S["zoom"] = {"keys": [[f, z0, "linear"], [f + n, z1]] if kind == "push_in" else [[f, z1, "linear"], [f + n, z0]]}
    return f"zoom:{S['id']}:{f}"


def _free_id(P: dict, prefix: str, rgb: bool = False) -> str:
    ids = {str(x.get("id")) for x in P["layers"]}
    k = 1
    while (f"{prefix}e{k:02d}" in ids if not rgb else any(i.startswith(f"rgb_e{k:02d}_") for i in ids)):
        k += 1
    return f"{prefix}e{k:02d}"


def apply_op(P: dict, o: dict, talk: bool = False) -> str:
    """One of the Editor's effect ops on P (in place) -> a line for the record (frame + timecode by the caller)."""
    op = o.get("op")
    if op == "fxadd":
        fid = add(P, str(o.get("kind")), int(o["f"]), talk=talk)
        return f"effect {o.get('kind')} added at f{int(o['f'])} ({fid})"
    fx = find(P, str(o.get("id")))
    if op == "fxmove":
        move(P, fx, int(o["by"]))
        return f"{fx['label']} at f{fx['f']} moved {int(o['by']):+d} frames"
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
    for o in ({"op": "fxmove", "id": "black:s02_A:150", "by": 80}, {"op": "fxadd", "kind": "stutter", "f": 120},
              {"op": "fxset", "id": "black:s02_A:150", "strength": 2}, {"op": "fxadd", "kind": "nope", "f": 1}):
        try:
            apply_op(copy.deepcopy(P), o, talk=True)
            bad.append(o)
        except FxError:
            pass
    case("what cannot be done is refused (off its shot, a stutter on a talking video, no strength, no such kind)", not bad)
    Q = plan()
    for kind, f in (("shake", 260), ("rgb_split", 40), ("colour_flash", 60), ("dip_black", 98), ("white_flash", 150),
                    ("punch_in", 250)):
        apply_op(Q, {"op": "fxadd", "kind": kind, "f": f})
    E = {(x["kind"], x["f"]) for x in effects(Q)}
    case("new effects at the playhead: a shake, an RGB split, a colour flash, a dip on the nearest cut, a white flash "
         "into the next shot, a punch-in", {("shake", 260), ("rgb", 40), ("colour_flash", 60), ("dip", 94),
                                            ("flash", 100), ("punch", 250)} <= E)
    Q2 = plan()
    try:
        apply_op(Q2, {"op": "fxadd", "kind": "zoom_through", "f": 101})
        refused = False
    except FxError:
        refused = True
    case("a zoom-through on a cut whose shots already zoom is refused (change those)", refused)
    return {"passed": ok, "seconds": round(time.time() - t0, 3), "lines": lines}
