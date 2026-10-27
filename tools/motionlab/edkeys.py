"""The Editor's keyframes (2026-10-26; the user: "how hard is to do that kind of effects with keyframes so i can give
more personalzied effects to my friends", then "lets continue with the keyframe thing for the minieditor"): a shot's
moves keyed the way CapCut / Premiere / Resolve / OpenCut do it - a ◆ per property in the selected shot's panel (its
value at the playhead; ◀ ▶ = the keys before / after it), and once a property has a key every change at the playhead
is a key (auto-key; without keys a change sets the whole shot's value); diamonds on the shot to drag (retime) or click
(the ease of the move after it: linear, ease in / out / both, hold, pop). Keys are the plan's own curves ({"keys":
[[f, v, ease]]} on the clip layer - compose plays them, so does the Editor's preview); their frames are the
timeline's, so a moved / trimmed / sped-up shot takes them along (miniedit's shifts). The effects lane's zoom chips
(motionlab\\edfx) are the same keys seen as moves.

    PROPS   prop -> (the layer's key, index in it, default, lowest, highest): zoom (1 = fills its box, under 1 =
            smaller), x / y (pixels), rotation (degrees, clockwise), opacity (0..1), ax / ay (the zoom point: 0..1
            across / down the picture)
    value(L, prop, f), keys(L, prop) -> [[f, v, ease, ...]] | None
    apply_op(P, S, o) -> a line for the record (frames as fN):
        kset   {"shot", "prop", "f", "value"}   a key at f when the property has keys, else the shot's value
        kadd   {"shot", "prop", "f"}            a key at f with the value it has there (the ◆)
        kdel   {"shot", "prop" | "props", "f"}  those keys go (a property's last one: its value stays as the shot's)
        kmove  {"shot", "f", "to", "props"}     the keys at f (all properties, or those named) to frame `to` - as far
                                                as they can go (never over the keys beside them, never off the shot)
        kease  {"shot", "f", "ease", "props"}   the move after the keys at f
        kreset {"shot", "prop"}                 the property back to its default, no keys (↺)
"""
from __future__ import annotations

from . import i18n as I18N

PROPS = {"zoom": ("zoom", None, 1.0, 0.1, 5.0), "x": ("dx", None, 0.0, -10000.0, 10000.0),
         "y": ("dy", None, 0.0, -10000.0, 10000.0), "rotation": ("rotation", None, 0.0, -3600.0, 3600.0),
         "opacity": ("opacity", None, 1.0, 0.0, 1.0), "ax": ("anchor", 0, 0.5, 0.0, 1.0),
         "ay": ("anchor", 1, 0.5, 0.0, 1.0)}
EASES = ("linear", "smooth", "in", "out", "hold", "pop", "easy", "strong", "glide", "launch")   # + "cubic(x1,y1,x2,y2)"
DEFAULT_EASE = "smooth"                         # (the research, 2026-10-26: motion keys ease in and out by default)


def ease_ok(e: str) -> bool:
    """A named ease, or the chart's own curve "cubic(x1,y1,x2,y2)" (handles: x in 0..1, y in -1..2)."""
    if e in EASES:
        return True
    if not (e.startswith("cubic(") and e.endswith(")")):
        return False
    try:
        x1, y1, x2, y2 = (float(v) for v in e[6:-1].split(","))
    except ValueError:
        return False
    return 0 <= x1 <= 1 and 0 <= x2 <= 1 and -1 <= y1 <= 2 and -1 <= y2 <= 2
KEY_OPS = ("kset", "kadd", "kdel", "kmove", "kease", "kreset")


class KeyError_(ValueError):
    pass


def _spec(L: dict, prop: str):
    key, idx, dflt = PROPS[prop][:3]
    v = L.get(key)
    if idx is not None:
        v = (v if isinstance(v, list) and len(v) == 2 else [0.5, 0.5])[idx]
    return dflt if v is None else v


def _set_spec(L: dict, prop: str, spec) -> None:
    key, idx, dflt = PROPS[prop][:3]
    plain = lambda v: isinstance(v, (int, float)) and abs(float(v) - dflt) < 1e-9     # noqa: E731
    if idx is None:
        if plain(spec):
            L.pop(key, None)
        else:
            L[key] = spec
        return
    an = list(L.get("anchor") if isinstance(L.get("anchor"), list) and len(L["anchor"]) == 2 else [0.5, 0.5])
    an[idx] = spec
    if all(isinstance(a, (int, float)) and abs(float(a) - 0.5) < 1e-9 for a in an):
        L.pop("anchor", None)
    else:
        L["anchor"] = an


def keys(L: dict, prop: str) -> list | None:
    s = _spec(L, prop)
    return s["keys"] if isinstance(s, dict) and s.get("keys") else None


def value(L: dict, prop: str, f: int, named: dict | None = None) -> float:
    from .compose import Curve
    try:
        return float(Curve(_spec(L, prop), named, PROPS[prop][2])(f))
    except (KeyError, ValueError, TypeError):
        return PROPS[prop][2]


def _keyable(L: dict, prop: str) -> None:
    s = _spec(L, prop)
    if isinstance(s, str) or (isinstance(s, dict) and (not s.get("keys") or "scale" in s or "offset" in s)):
        raise KeyError_(I18N.t("this shot's {prop} moves frame by frame here (a shake?) - remove that effect first",
                               prop=prop))


def _clampv(prop: str, v: float) -> float:
    lo, hi = PROPS[prop][3:5]
    return round(min(hi, max(lo, float(v))), 4)


def _put(ks: list, f: int, v: float, ease: str | None = None) -> None:
    for i, k in enumerate(ks):
        if int(k[0]) == f:
            ks[i] = [f, v, ease or (k[2] if len(k) > 2 else DEFAULT_EASE)]
            return
        if int(k[0]) > f:
            ks.insert(i, [f, v, ease or DEFAULT_EASE])
            return
    ks.append([f, v, ease or DEFAULT_EASE])


def _at(ks: list, f: int) -> int | None:
    return next((i for i, k in enumerate(ks) if int(k[0]) == f), None)


def apply_op(P: dict, S: dict, o: dict) -> str:
    """One keyframe op on shot S (in place)."""
    op = o.get("op")
    s, e = int(S["start"]), int(S["end"])
    named = P.get("curves") or {}
    props = [o["prop"]] if o.get("prop") is not None else list(o.get("props") or PROPS)
    for p in props:
        if p not in PROPS:
            raise KeyError_(I18N.t("no such property: {prop}", prop=str(p)))
    if op == "kreset":
        p = props[0]
        _set_spec(S, p, PROPS[p][2])
        return f"{S['id']}: {p} back to its default"
    f = int(o["f"])
    if op in ("kset", "kadd") and not s <= f <= e:
        raise KeyError_(I18N.t("the playhead is not on this shot ({range})", range=f"f{s}-f{e}"))
    if op == "kset":
        p = props[0]
        v = _clampv(p, o["value"])
        ks = keys(S, p)
        if ks is None:
            _keyable(S, p) if isinstance(_spec(S, p), dict) else None
            _set_spec(S, p, v)
            return f"{S['id']}: {p} = {v:g}"
        _put(ks, f, v)
        return f"{S['id']}: {p} = {v:g} at f{f} (a key)"
    if op == "kadd":
        p = props[0]
        v = _clampv(p, value(S, p, f, named))
        ks = keys(S, p)
        if ks is None:
            _keyable(S, p) if isinstance(_spec(S, p), dict) else None
            _set_spec(S, p, {"keys": [[f, v, DEFAULT_EASE]]})
        else:
            _put(ks, f, v)
        return f"{S['id']}: a {p} key at f{f} ({v:g})"
    if op == "kdel":                                    # (a diamond: every property with a key on its frame)
        gone = []
        for p in props:
            ks = keys(S, p)
            i = _at(ks or [], f)
            if i is None:
                continue
            v = float(ks[i][1])
            del ks[i]
            if not ks:
                _set_spec(S, p, round(v, 4))
            gone.append(p)
        if not gone:
            raise KeyError_(I18N.t("no key at {frame}", frame=f"f{f}"))
        return f"{S['id']}: the {', '.join(gone)} key{'s' if len(gone) > 1 else ''} at f{f} removed"
    if op == "kease":
        ease = str(o.get("ease")).replace(" ", "")
        if not ease_ok(ease):
            raise KeyError_(I18N.t("an ease from the list, or a curve with its two handles"))
        n = 0
        for p in props:
            ks = keys(S, p) or []
            i = _at(ks, f)
            if i is not None:
                ks[i] = [ks[i][0], ks[i][1], ease, *ks[i][3:]]
                n += 1
        if not n:
            raise KeyError_(I18N.t("no key at {frame}", frame=f"f{f}"))
        return f"{S['id']}: the keys at f{f} ease {ease}"
    if op == "kmove":
        to = int(o["to"])
        hit = [(p, keys(S, p)) for p in props if _at(keys(S, p) or [], f) is not None]
        if not hit:
            raise KeyError_(I18N.t("no key at {frame}", frame=f"f{f}"))
        lo, hi = s, e
        for _, ks in hit:                           # never over the keys beside it
            i = _at(ks, f)
            if i > 0:
                lo = max(lo, int(ks[i - 1][0]) + 1)
            if i + 1 < len(ks):
                hi = min(hi, int(ks[i + 1][0]) - 1)
        to = max(lo, min(hi, to))
        if to == f:
            raise KeyError_(I18N.t("the key cannot go further that way"))
        for _, ks in hit:
            i = _at(ks, f)
            ks[i] = [to, *ks[i][1:]]
        return f"{S['id']}: the keys at f{f} moved to f{to}"
    raise KeyError_(I18N.t("no such change: {op}", op=str(op)))


def key_frames(L: dict) -> dict[str, list[int]]:
    """prop -> the frames of its keys (the page's diamonds, merged by frame there)."""
    return {p: [int(k[0]) for k in ks] for p in PROPS if (ks := keys(L, p))}


# ------------------------------------------------------------------------------------------------ self-check
def selfcheck() -> dict:
    import time
    t0, lines, ok = time.time(), [], True

    def case(name, cond):
        nonlocal ok
        ok = ok and bool(cond)
        lines.append(f"{'PASS' if cond else 'FAIL'} {name}")

    P = {"fps": 25.0, "frames": 300, "layers": []}
    S = {"type": "clip", "id": "s01_A", "src": "A", "start": 100, "end": 199, "in": 0, "zoom": 1.2}
    apply_op(P, S, {"op": "kset", "prop": "zoom", "f": 120, "value": 1.5})
    case("no keys: a change is the whole shot's value", S["zoom"] == 1.5)
    apply_op(P, S, {"op": "kadd", "prop": "zoom", "f": 110})
    apply_op(P, S, {"op": "kset", "prop": "zoom", "f": 150, "value": 2.0})
    case("the key button keys the value it has, then a change elsewhere is a key (auto-key, eased in and out)",
         S["zoom"] == {"keys": [[110, 1.5, "smooth"], [150, 2.0, "smooth"]]} and abs(value(S, "zoom", 130) - 1.75) < 1e-6)
    apply_op(P, S, {"op": "kadd", "prop": "rotation", "f": 150})
    apply_op(P, S, {"op": "kset", "prop": "rotation", "f": 180, "value": 15})
    apply_op(P, S, {"op": "kmove", "f": 150, "to": 160})
    case("a diamond dragged moves every key on its frame", key_frames(S) == {"zoom": [110, 160], "rotation": [160, 180]})
    apply_op(P, S, {"op": "kmove", "f": 160, "to": 300})
    case("never over the next key, never off the shot", key_frames(S)["rotation"] == [179, 180]
         and key_frames(S)["zoom"] == [110, 179])
    apply_op(P, S, {"op": "kease", "f": 110, "ease": "pop"})
    case("an ease on the move after a key", S["zoom"]["keys"][0][2] == "pop")
    apply_op(P, S, {"op": "kease", "f": 110, "ease": "cubic(0.2, 0.9, 0.3, 1)"})
    from .compose import Curve
    c = Curve(S["zoom"])
    case("the chart's own curve (two handles): a glide - most of the move early, a soft landing",
         S["zoom"]["keys"][0][2] == "cubic(0.2,0.9,0.3,1)" and c(130) > 1.5 + 0.5 * 0.8 and abs(c(179) - 2.0) < 1e-3
         and not ease_ok("cubic(2,0,1,1)") and ease_ok("glide"))
    apply_op(P, S, {"op": "kset", "prop": "ax", "f": 120, "value": 0.3})
    case("the zoom point keeps the other half of the anchor", S["anchor"] == [0.3, 0.5])
    apply_op(P, S, {"op": "kdel", "prop": "rotation", "f": 179})
    apply_op(P, S, {"op": "kdel", "prop": "rotation", "f": 180})
    case("the last key removed: its value stays as the shot's", S["rotation"] == 15)
    apply_op(P, S, {"op": "kreset", "prop": "rotation"})
    apply_op(P, S, {"op": "kset", "prop": "opacity", "f": 120, "value": 7})
    case("reset = gone; values kept in range", "rotation" not in S and "opacity" not in S)
    bad = []
    sh = {"type": "clip", "id": "s02", "start": 0, "end": 50, "anchor": [{"start": 10, "values": [0.5, 0.52]}, 0.5]}
    for o in ({"op": "kadd", "prop": "ax", "f": 20}, {"op": "kset", "prop": "zoom", "f": 99, "value": 2},
              {"op": "kadd", "prop": "nope", "f": 5}, {"op": "kease", "f": 5, "ease": "wobble"},
              {"op": "kdel", "prop": "zoom", "f": 5}):
        try:
            apply_op(P, sh, o)
            bad.append(o)
        except KeyError_:
            pass
    case("refused: keys over a shake's frame-by-frame zoom point, the playhead off the shot, no such property / "
         "ease / key", not bad)
    return {"passed": ok, "seconds": round(time.time() - t0, 3), "lines": lines}
