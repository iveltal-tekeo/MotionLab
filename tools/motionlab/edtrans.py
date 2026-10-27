"""The Editor's transitions between two shots (2026-10-26, the user: "maybe add the posiblity of transitions between two
clips? ... i kinda want to have that good video editing look so can we look for comparisons in capcut, opencut,
premiere pro, davinci"): a transition is a block on a cut, the way CapCut / Premiere / Resolve show it - added from the
Add panel's *Transitions* (dragged onto a cut, or + = the cut nearest the playhead) or the ↔ on a cut, its length
dragged at its edges, its kind / length / direction in the panel, *Apply to all cuts*. Never refused for a clip with
no frames to spare (Kdenlive's refusal is the anti-pattern): the window moves to the side that has them, else the
edge frame holds (the renderer and the preview clamp a clip's frame) and the block is hatched (Premiere's frozen
frames).

Stored on the shot after the cut: S["trans"] = {"kind": k, "len": n, "dir": d}. build(P) turns every one into helper
layers over the cut - a black ground, copies of the two shots (their own look, the transition's move baked per frame
over their own curves: {"start", "values"}), or a colour layer - with ids tr_<shot>_<part> and "tr": <shot>, put right
above the main track (graphics and captions stay on top). strip(P) takes them out again: motionlab\\miniedit runs
strip first and build last on every change, and state() the same, so trims, moves, splits and speed never break a
transition - it is made again from the two shots as they are. A pair of shots that overlap (the quick draft's own
push / whip / crossfade) keeps what it has.

    KINDS                       kind -> (label, seconds, needs the clips' spare frames)
    OFFER                       the kinds the Editor offers (2026-10-27, the user: "few but higher quality ones");
                                the others still build where a plan has them
    strip(P) / build(P)         in place
    transitions(P) -> [{shot, from, kind, label, f, len, cut, dir, frozen}]   (after build: where each one is)
    apply_op(P, o)              {"op": "trans", "shot": id, "kind": k | null, "len": n, "dir": d} | {"op": "transall",
                                "kind": k | null, "len": n, "dir": d} -> a line for the record
"""
from __future__ import annotations

import copy
import random

from . import editlist as EL
from . import i18n as I18N

# kind -> (label, seconds, uses frames past the cut: the outgoing shot's after it, the incoming one's before it)
KINDS = {
    "mix": ("Mix", 0.5, True), "black": ("Dip to black", 0.6, False), "white": ("Dip to white", 0.5, False),
    "flash": ("White flash", 0.3, False), "zoom_in": ("Zoom in", 0.35, False), "zoom_out": ("Zoom out", 0.45, False),
    "slide": ("Slide", 0.4, True), "whip": ("Whip", 0.3, True), "spin": ("Spin", 0.5, False),
    "glitch": ("Glitch", 0.3, False), "leak": ("Light leak", 0.6, True),
}
# 2026-10-27 the review against CapCut / Premiere / Resolve: a dip to white = a longer flash, the zoom out left most of
# the frame black, the spin looked like a slide show, the glitch showed black / cyan strips, the light leak was a hard
# orange box - no longer offered. A slide, a whip and a zoom move with motion blur (compose "mblur").
OFFER = ("mix", "black", "flash", "slide", "whip", "zoom_in")
DIRS = ("left", "right", "up", "down")
DIRECTED = {"slide", "whip"}
MIN_LEN = 2
CLEAN = ("flash_over", "flash_white", "black", "trans", "sound_db", "tr")      # a copy shows the picture only


class TransError(ValueError):
    pass


_EASE = {"linear": lambda t: t, "smooth": lambda t: t * t * (3 - 2 * t), "in": lambda t: t * t,
         "out": lambda t: 1 - (1 - t) * (1 - t), "in3": lambda t: t ** 3, "out3": lambda t: 1 - (1 - t) ** 3}


def _whip(p: float) -> float:
    """A whip pan's travel: slow, very fast through the cut, slow."""
    return 0.5 * _EASE["in3"](2 * p) if p < 0.5 else 0.5 + 0.5 * _EASE["out3"](2 * p - 1)


def is_helper(L: dict) -> bool:
    return bool(L.get("tr")) and str(L.get("id", "")).startswith("tr_")


def strip(P: dict) -> dict:
    P["layers"] = [L for L in P.get("layers", []) if not is_helper(L)]
    return P


def _shots(P: dict) -> list[dict]:
    return EL.shots(P)


def _pairs(P: dict):
    S = _shots(P)
    for A, B in zip(S, S[1:]):
        if int(B["start"]) == int(A["end"]) + 1 and A.get("type") == "clip" and B.get("type") == "clip":
            yield A, B


def _src_frames(P: dict, L: dict) -> int:
    return int(((P.get("sources") or {}).get(L.get("src", "")) or {}).get("frames") or 0)


def _spare(P: dict, L: dict, side: str) -> int:
    """Timeline frames the shot's clip has before its first frame / after its last one (a held frame: none)."""
    if L.get("hold"):
        return 0
    n, sp = _src_frames(P, L), float(L.get("speed", 1.0))
    if side == "before":
        return max(0, int(EL._src_at(L, int(L["start"])) / sp + 1e-9))
    return max(0, int((n - 1 - EL._src_at(L, int(L["end"]))) / sp + 1e-9)) if n else 0


def _window(P: dict, A: dict, B: dict, kind: str, n: int) -> tuple[int, int, int]:
    """(a, b, frozen): the frames the transition covers and how many of them hold a clip's edge frame."""
    c, la, lb = int(B["start"]), int(A["end"]) - int(A["start"]) + 1, int(B["end"]) - int(B["start"]) + 1
    n = max(MIN_LEN, min(int(n), la, lb))
    a = c - n // 2                                          # centred on the cut
    if KINDS[kind][2]:
        tail, head = _spare(P, A, "after"), _spare(P, B, "before")
        if (c + n - (n // 2) - c) > tail or n // 2 > head:
            if head >= n and la >= n:                       # all before the cut (Resolve: "end on edit")
                a = c - n
            elif tail >= n and lb >= n:                     # all after it ("start on edit")
                a = c
        b = a + n - 1
        frozen = max(0, b - c + 1 - tail) + max(0, c - a - head)
        return a, b, frozen
    return a, a + n - 1, 0


def _curve(spec, named, default):
    from .compose import Curve
    try:
        return Curve(spec, named, default)
    except (KeyError, ValueError, TypeError):
        return lambda f: default


def _bake(spec, named, default, a: int, b: int, fn) -> dict:
    """The layer's own value at each frame a..b through fn(frame, value) -> {"start", "values"}."""
    cv = _curve(spec, named, default)
    return {"start": a, "values": [round(float(fn(f, cv(f))), 4) for f in range(a, b + 1)]}


def _copy(L: dict, a: int, b: int, hid: str, shot: str) -> dict:
    """The shot over a..b, showing the source frames the shot itself shows there (its in-point and jumps from a)."""
    c = EL._trim_front({k: copy.deepcopy(v) for k, v in L.items() if k not in CLEAN}, a)
    c.update(id=hid, end=b, tr=shot)
    return c


def _p(f: int, a: int, b: int) -> float:
    return 0.0 if b <= a else min(1.0, max(0.0, (f - a) / (b - a)))


def _helpers(P: dict, A: dict, B: dict, spec: dict) -> list[dict]:
    kind, sid = spec["kind"], str(B["id"])
    W, H = int(P.get("width", 1920)), int(P.get("height", 1080))
    named = P.get("curves") or {}
    a, b, _ = _window(P, A, B, kind, int(spec.get("len") or 0) or _default_len(P, kind))
    c = int(B["start"])
    out: list[dict] = []
    ground = {"type": "solid", "id": f"tr_{sid}_bg", "tr": sid, "start": a, "end": b, "rect": [0, 0, W, H],
              "color": [0, 0, 0], "cover": True}
    if kind in ("black", "white", "flash"):
        col = [0, 0, 0] if kind == "black" else [1, 1, 1]
        keys = ([[a, 0, "smooth"], [c, 1, "smooth"], [b, 0]] if kind != "flash" else
                [[a, 0, "in"], [c, 0.95, "out"], [b, 0]])
        return [{"type": "solid", "id": f"tr_{sid}_dip", "tr": sid, "start": a, "end": b, "rect": [0, 0, W, H],
                 "color": col, "opacity": {"keys": keys}, **({"blend": "screen"} if kind == "flash" else {})}]
    if kind in ("mix", "leak", "slide", "whip"):
        ca, cb = _copy(A, a, b, f"tr_{sid}_a", sid), _copy(B, a, b, f"tr_{sid}_b", sid)
        if kind in ("mix", "leak"):
            cb["opacity"] = _bake(B.get("opacity"), named, 1.0, a, b, lambda f, v: v * _EASE["smooth"](_p(f, a, b)))
            out = [ground, ca, cb]
            if kind == "leak":
                out.append({"type": "solid", "id": f"tr_{sid}_leak", "tr": sid, "start": a, "end": b,
                            "rect": [round(W * 0.3), 0, W - round(W * 0.3), H], "color": [1.0, 0.55, 0.2],
                            "blend": "screen", "opacity": {"keys": [[a, 0, "smooth"], [c, 0.6, "smooth"], [b, 0]]}})
            return out
        d = spec.get("dir") if spec.get("dir") in DIRS else "left"
        ca["mblur"] = cb["mblur"] = True
        ax, size = ("dx", W) if d in ("left", "right") else ("dy", H)
        sgn = -1 if d in ("left", "up") else 1              # where the outgoing picture goes
        ease = _whip if kind == "whip" else _EASE["smooth"]
        ca[ax] = _bake(A.get(ax), named, 0.0, a, b, lambda f, v: v + sgn * size * ease(_p(f, a, b)))
        cb[ax] = _bake(B.get(ax), named, 0.0, a, b, lambda f, v: v - sgn * size * (1 - ease(_p(f, a, b))))
        if kind == "whip":                                  # a little closer through the cut: no edge in sight
            for L, src in ((ca, A), (cb, B)):
                L["zoom"] = _bake(src.get("zoom"), named, 1.0, a, b,
                                  lambda f, v: v * (1 + 0.12 * (1 - abs(2 * _p(f, a, b) - 1))))
        return [ground, ca, cb]
    # the shots' own frames: the outgoing one up to the cut, the incoming one from it
    pa, pb = _copy(A, a, c - 1, f"tr_{sid}_a", sid), _copy(B, c, b, f"tr_{sid}_b", sid)
    ia = lambda f: _p(f, a, c - 1)                          # noqa: E731
    ib = lambda f: _p(f, c, b)                              # noqa: E731
    if kind == "zoom_in":
        pa["mblur"] = pb["mblur"] = True
        pa["zoom"] = _bake(A.get("zoom"), named, 1.0, a, c - 1, lambda f, v: v * (1 + 0.7 * _EASE["in"](ia(f))))
        pb["zoom"] = _bake(B.get("zoom"), named, 1.0, c, b, lambda f, v: v * (1.7 - 0.7 * _EASE["out"](ib(f))))
    elif kind == "zoom_out":
        pa["zoom"] = _bake(A.get("zoom"), named, 1.0, a, c - 1, lambda f, v: v * (1 - 0.35 * _EASE["in"](ia(f))))
        pb["zoom"] = _bake(B.get("zoom"), named, 1.0, c, b, lambda f, v: v * (1.35 - 0.35 * _EASE["out"](ib(f))))
    elif kind == "spin":
        pa["rotation"] = _bake(A.get("rotation"), named, 0.0, a, c - 1, lambda f, v: v + 180 * _EASE["in"](ia(f)))
        pa["zoom"] = _bake(A.get("zoom"), named, 1.0, a, c - 1, lambda f, v: v * (1 - 0.5 * _EASE["in"](ia(f))))
        pb["rotation"] = _bake(B.get("rotation"), named, 0.0, c, b, lambda f, v: v - 180 * (1 - _EASE["out"](ib(f))))
        pb["zoom"] = _bake(B.get("zoom"), named, 1.0, c, b, lambda f, v: v * (0.5 + 0.5 * _EASE["out"](ib(f))))
    elif kind == "glitch":                                   # the picture jumps and its red splits off
        rng = random.Random(c * 7919 + 13)
        out = [ground]
        for L, x0, x1, src, tag in ((pa, a, c - 1, A, "a"), (pb, c, b, B, "b")):
            jit = {f: rng.choice((-1, 1)) * rng.uniform(0.01, 0.04) * W for f in range(x0, x1 + 1)}
            L["dx"] = _bake(src.get("dx"), named, 0.0, x0, x1, lambda f, v: v + jit[f] * 0.5)
            L["tint"] = [0, 1, 1]
            red = _copy(src, x0, x1, f"tr_{sid}_{tag}r", sid)
            red.update(tint=[1, 0, 0], blend="add")
            red["dx"] = _bake(src.get("dx"), named, 0.0, x0, x1, lambda f, v: v + jit[f] * 1.6)
            out += [L, red]
        return out
    return [ground, pa, pb]


def _default_len(P: dict, kind: str) -> int:
    return max(MIN_LEN, int(round(KINDS[kind][1] * float(P.get("fps") or 25))))


def build(P: dict) -> dict:
    """Every shot's "trans" -> its helper layers, right above the main track. In place (strip first)."""
    strip(P)
    made: list[dict] = []
    top = -1
    for A, B in _pairs(P):
        spec = B.get("trans")
        if not isinstance(spec, dict) or spec.get("kind") not in KINDS:
            continue
        made += _helpers(P, A, B, spec)
        top = max(top, next(i for i, L in enumerate(P["layers"]) if L is A), next(i for i, L in enumerate(P["layers"]) if L is B))
    if made:
        P["layers"][top + 1:top + 1] = made
    return P


def transitions(P: dict) -> list[dict]:
    out = []
    for A, B in _pairs(P):
        spec = B.get("trans")
        if not isinstance(spec, dict) or spec.get("kind") not in KINDS:
            continue
        kind = spec["kind"]
        a, b, frozen = _window(P, A, B, kind, int(spec.get("len") or 0) or _default_len(P, kind))
        out.append({"shot": str(B["id"]), "from": str(A["id"]), "kind": kind, "label": KINDS[kind][0], "f": a,
                    "len": b - a + 1, "cut": int(B["start"]), "dir": spec.get("dir") if kind in DIRECTED else None,
                    "frozen": frozen, "max": min(int(A["end"]) - int(A["start"]) + 1, int(B["end"]) - int(B["start"]) + 1)})
    return out


def apply_op(P: dict, o: dict) -> str:
    """One of the Editor's transition ops on P (the helpers stripped; in place) -> a line for the record."""
    op = o.get("op")
    kind = o.get("kind")
    if kind is not None and kind not in KINDS:
        raise TransError(I18N.t("no such transition: {kind}", kind=str(kind)))
    if o.get("dir") is not None and o.get("dir") not in DIRS:
        raise TransError(I18N.t("a direction: left, right, up or down"))
    pairs = list(_pairs(P))
    if op == "transall":
        if not pairs:
            raise TransError(I18N.t("the video has no plain cut for a transition"))
        for _, B in pairs:
            _set(P, B, kind, o)
        return f"transition {kind or 'none'} on all {len(pairs)} cuts" + (f", {int(o['len'])} frames" if o.get("len") else "")
    if op != "trans":
        raise TransError(I18N.t("no such change: {op}", op=str(op)))
    B = next((B for _, B in pairs if str(B["id"]) == str(o.get("shot"))), None)
    if B is None:
        raise TransError(I18N.t("no plain cut before shot {shot}", shot=str(o.get("shot"))))
    old = (B.get("trans") or {}).get("kind")
    _set(P, B, kind if "kind" in o else old, o)
    now = B.get("trans")
    if not now:
        return f"transition into {B['id']} at f{int(B['start'])} removed"
    return (f"transition into {B['id']} at f{int(B['start'])}: {now['kind']}, {now.get('len') or 'default'} frames"
            + (f", {now['dir']}" if now.get("dir") else ""))


def _set(P: dict, B: dict, kind, o: dict) -> None:
    if not kind:
        B.pop("trans", None)
        return
    old = B.get("trans") or {}
    spec = {"kind": kind}
    n = o.get("len") if o.get("len") is not None else (old.get("len") if old.get("kind") == kind else None)
    if n is not None:                                       # (no longer than the shorter of its two shots: as drawn)
        A = next((A for A, BB in _pairs(P) if BB is B), None)
        top = min(int(A["end"]) - int(A["start"]) + 1, int(B["end"]) - int(B["start"]) + 1) if A else int(n)
        spec["len"] = max(MIN_LEN, min(int(n), top))
    if kind in DIRECTED:
        spec["dir"] = o.get("dir") or old.get("dir") or "left"
    B["trans"] = spec


# ------------------------------------------------------------------------------------------------ self-check
def selfcheck() -> dict:
    import time
    t0, lines, ok = time.time(), [], True

    def case(name, cond):
        nonlocal ok
        ok = ok and bool(cond)
        lines.append(f"{'PASS' if cond else 'FAIL'} {name}")

    def plan():
        return {"fps": 25.0, "frames": 300, "width": 1080, "height": 1920,
                "sources": {"A": {"frames": 2000}, "B": {"frames": 120}},
                "layers": [{"type": "clip", "id": "s01_A", "src": "A", "start": 0, "end": 99, "in": 100,
                            "rect": [0, 0, 1080, 1920], "zoom": 1.2},
                           {"type": "clip", "id": "s02_B", "src": "B", "start": 100, "end": 199, "in": 0,
                            "rect": [0, 0, 1080, 1920]},
                           {"type": "clip", "id": "s03_A", "src": "A", "start": 200, "end": 299, "in": 500,
                            "rect": [0, 0, 1080, 1920], "dx": {"keys": [[200, 0, "linear"], [299, 50]]}},
                           {"type": "overlay", "id": "captions", "file": "x/captions.mov", "start": 0, "end": 299}]}

    P = plan()
    apply_op(P, {"op": "trans", "shot": "s03_A", "kind": "slide", "dir": "up"})
    apply_op(P, {"op": "trans", "shot": "s02_B", "kind": "mix", "len": 12})
    build(P)
    ids = [L["id"] for L in P["layers"]]
    T = {t["shot"]: t for t in transitions(P)}
    case("two transitions: their helpers right above the shots, the captions still on top",
         ids[-1] == "captions" and ids[3:6] == ["tr_s02_B_bg", "tr_s02_B_a", "tr_s02_B_b"] and "tr_s03_A_b" in ids)
    case("a mix into a clip with no frames before its first one: all after the cut (no frozen frames)",
         T["s02_B"]["f"] == 100 and T["s02_B"]["len"] == 12 and T["s02_B"]["frozen"] == 0)
    sl = next(L for L in P["layers"] if L["id"] == "tr_s03_A_b")
    case("a slide up: the incoming copy comes from below over its own move (baked on its dx keys)",
         sl["dy"]["values"][0] == 1920 and sl["dy"]["values"][-1] == 0 and sl["dx"] == {"keys": [[200, 0, "linear"], [299, 50]]})
    mixb = next(L for L in P["layers"] if L["id"] == "tr_s02_B_b")
    case("a copy shows the picture only (no transition spec, no flash), the mix fades it in",
         "trans" not in mixb and mixb["opacity"]["values"][0] == 0 and mixb["opacity"]["values"][-1] == 1)
    Q = copy.deepcopy(P)
    strip(Q)
    Q["layers"][1]["start"] = 90                       # the incoming shot made longer at its front: the helpers follow
    Q["layers"][0]["end"] = 89
    build(Q)
    case("strip + build after a change: the transition follows the cut", {t["shot"]: t["cut"] for t in transitions(Q)}["s02_B"] == 90)
    R = plan()
    R["sources"]["A"]["frames"] = 200                  # the outgoing clip ends right at the cut
    R["layers"][0]["in"] = 100
    R["layers"][1]["in"] = 0
    apply_op(R, {"op": "trans", "shot": "s02_B", "kind": "slide", "len": 10})
    build(R)
    t = transitions(R)[0]
    case("no spare frames on either side: centred, the edge frames hold (hatched: 5 + 5)", t["f"] == 95 and t["frozen"] == 10)
    for k in KINDS:
        S = plan()
        apply_op(S, {"op": "transall", "kind": k})
        build(S)
        hs = [L for L in S["layers"] if is_helper(L)]
        if not hs or any(int(L["end"]) < int(L["start"]) for L in hs):
            case(f"{k}: helpers", False)
    case("every kind builds on every cut", True)
    off = []
    for k in KINDS:                                 # a copy shows its shot's own source frames (not from its first)
        S = plan()
        S["layers"][0]["jumps"] = [[0, 100], [60, 40]]
        apply_op(S, {"op": "transall", "kind": k})
        build(S)
        by = {L["id"]: L for L in S["layers"]}
        for A, B in _pairs(S):
            for L in S["layers"]:
                sh = A if str(L["id"]).startswith(f"tr_{B['id']}_a") else B if str(L["id"]).startswith(f"tr_{B['id']}_b") else None
                if sh is None or L.get("type") != "clip":
                    continue
                for f in (int(L["start"]), int(L["end"])):
                    if EL._src_at(L, f) != EL._src_at(by[sh["id"]], f):
                        off.append((k, L["id"], f))
    case("the copies show their shots' own frames on their first and last frame (a jump in the shot kept)", not off)
    bad = []
    for o in ({"op": "trans", "shot": "s01_A", "kind": "mix"}, {"op": "trans", "shot": "s02_B", "kind": "nope"},
              {"op": "trans", "shot": "s02_B", "kind": "slide", "dir": "sideways"}):
        try:
            apply_op(plan(), o)
            bad.append(o)
        except TransError:
            pass
    case("refused: no cut before the first shot, no such kind, no such direction", not bad)
    S = plan()
    apply_op(S, {"op": "trans", "shot": "s02_B", "kind": "mix"})
    apply_op(S, {"op": "trans", "shot": "s02_B", "kind": None})
    case("a transition removed", "trans" not in S["layers"][1] and not [L for L in build(S)["layers"] if is_helper(L)])
    return {"passed": ok, "seconds": round(time.time() - t0, 3), "lines": lines}
