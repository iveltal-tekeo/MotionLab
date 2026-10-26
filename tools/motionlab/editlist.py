"""The edit as a list (0.5.3 D1): instead of a 10-15 KB edit_vN.py per talking video, Claude writes a few lines that
change the newest plan - `tools\\draft_edit.py <project> --apply <list>` applies them and saves plan_v<N+1>.json with
the list beside it (edit_v<N+1>.list). Every frame in a list is the frame of the plan it starts from (the frames of its
cut-sheet), whatever the lines before it do; cuts are applied last.

    # a comment
    cut f120-f188                       remove these frames: later layers move up, the talk sound is cut again
    punch-in 1.2 at f300                the shot under f300 zooms to 1.2 from f300 to its end (an instant punch)
    punch-in 1.15 at f300 ease 6        ... over 6 frames (S-curve)
    shot 4 zoom 1.15 | shot s04_A tight | shot 4 wide       a whole shot (its number or layer id): zoom, tight =
                                        1.15, wide = 1
    hold f380-f404                      the picture under f380 freezes until f404 (the sound goes on)
    caption clean_box [script script-005]   captions over the whole edit: the clips' words (speech.py) moved through
                                        the edit, one caption per script line in its own words when a script is named
    graphic <template> at f1524 for 48 [land <track>] [text="..." color=#ffd400 ...]   a template's copy as an overlay
    sfx whoosh at f300 | sfx pop on punch-ins | sfx whoosh on cuts      the plan's own sound cues
    layer {"type": "solid", ...}        any plan layer as JSON (the way out for a one-off)

Pure plan changes here; draft_edit.py runs the tools (overlay.py, speech) for caption / graphic lines and cuts the
talk sound again.
"""
from __future__ import annotations

import copy
import json
import re

TIGHT, WIDE = 1.15, 1.0
_F = r"f?(\d+)"


class ListError(ValueError):
    pass


def parse(text: str) -> list[dict]:
    """The list's lines -> operations (each with its line number); ListError names every line it cannot read."""
    ops, bad = [], []
    for n, raw in enumerate(text.splitlines(), 1):
        ln = raw.strip()
        if not ln or ln.startswith("#"):
            continue
        if not ln.startswith("layer "):
            ln = re.split(r"\s#\s", ln, maxsplit=1)[0].strip()      # " # a note" (colours like #ffd400 stay)
        try:
            if (m := re.fullmatch(rf"cut {_F}\s*-\s*{_F}", ln)):
                a, b = int(m[1]), int(m[2])
                ops.append({"op": "cut", "a": min(a, b), "b": max(a, b), "line": n})
            elif (m := re.fullmatch(rf"punch-in ([\d.]+) at {_F}(?: ease (\d+))?", ln)):
                ops.append({"op": "punch", "z": float(m[1]), "f": int(m[2]), "ease": int(m[3] or 0), "line": n})
            elif (m := re.fullmatch(r"shot (\S+) (?:zoom ([\d.]+)|(tight|wide))", ln)):
                z = float(m[2]) if m[2] else (TIGHT if m[3] == "tight" else WIDE)
                ops.append({"op": "shot", "shot": m[1], "z": z, "line": n})
            elif (m := re.fullmatch(rf"hold {_F}\s*-\s*{_F}", ln)):
                ops.append({"op": "hold", "a": int(m[1]), "b": int(m[2]), "line": n})
            elif (m := re.fullmatch(r"caption (\w+)(?: script (\S+))?", ln)):
                ops.append({"op": "caption", "preset": m[1], "script": m[2], "line": n})
            elif (m := re.fullmatch(rf"graphic ([\w.-]+) at {_F} for (\d+)(?: land (\S+))?(.*)", ln)):
                vals = dict(re.findall(r'(\w+)=("[^"]*"|\S+)', m[5] or ""))
                ops.append({"op": "graphic", "id": m[1], "f": int(m[2]), "len": int(m[3]), "land": m[4],
                            "values": {k: v.strip('"') for k, v in vals.items()}, "line": n})
            elif (m := re.fullmatch(rf"sfx (\w+) at {_F}", ln)):
                ops.append({"op": "sfx", "kind": m[1], "f": int(m[2]), "line": n})
            elif (m := re.fullmatch(r"sfx (\w+) on (punch-ins|cuts|graphics)", ln)):
                ops.append({"op": "sfx_on", "kind": m[1], "on": m[2], "line": n})
            elif ln.startswith("layer "):
                L = json.loads(ln[6:])
                if not isinstance(L, dict) or "type" not in L:
                    raise ValueError("a layer needs a \"type\"")
                ops.append({"op": "layer", "layer": L, "line": n})
            else:
                bad.append(f"line {n}: {raw.strip()[:80]} - not a list line (see editlist.py)")
        except (ValueError, json.JSONDecodeError) as e:
            bad.append(f"line {n}: {e}")
    if bad:
        raise ListError("\n".join(bad))
    return ops


def shots(plan: dict) -> list[dict]:
    """The talking / main shots in timeline order (the quick draft's sNN_<clip> layers; else every clip layer that
    is not B-roll or an effect)."""
    L = [x for x in plan["layers"] if x.get("type") == "clip" and re.match(r"s\d+_", str(x.get("id", "")))]
    if not L:                                       # (tr_: a transition's copies of two shots, motionlab\edtrans)
        L = [x for x in plan["layers"] if x.get("type") == "clip" and not str(x.get("id", "")).startswith(
            ("broll", "rgb_", "tr_"))]
    return sorted(L, key=lambda x: x["start"])


def shot_at(plan: dict, f: int) -> dict:
    for x in shots(plan):
        if x["start"] <= f <= x["end"]:
            return x
    raise ListError(f"no shot under f{f}")


def _src_at(L: dict, f: int) -> int:
    jumps = sorted([[int(a), int(b)] for a, b in L.get("jumps", [[L["start"], L.get("in", 0)]])])
    j = jumps[0]
    for jj in jumps:
        if jj[0] <= f:
            j = jj
    return j[1] if L.get("hold") else j[1] + int((f - j[0]) * float(L.get("speed", 1.0)) + 1e-6)


def cut(plan: dict, a: int, b: int) -> None:
    """Remove timeline frames a..b: layers inside go, layers across are trimmed (their "in" / keys move with them),
    later ones move up by b - a + 1. In place."""
    n = b - a + 1
    out = []
    for L in plan["layers"]:
        s, e = int(L.get("start", 0)), int(L.get("end", plan["frames"] - 1))
        if s >= a and e <= b:
            continue                                            # entirely inside the cut
        if e < a:
            out.append(L)
            continue
        if s > b:
            out.append(_shift(L, -n))
            continue
        if s < a and e > b:                                     # across the cut: the part after continues later in
            first, second = copy.deepcopy(L), copy.deepcopy(L)  # its source (split in two)
            first["end"] = a - 1
            second = _trim_front(second, b + 1)
            second["id"] = f"{L.get('id', L['type'])}_b"
            out += [first, _shift(second, -n)]
            continue
        if s < a:                                               # ends inside the cut
            L["end"] = a - 1
            out.append(L)
        else:                                                   # starts inside the cut
            out.append(_shift(_trim_front(L, b + 1), -n))
    plan["layers"] = out
    plan["frames"] = int(plan["frames"]) - n
    cues = [q for q in plan.get("cues", []) if not (isinstance(q.get("f"), int) and a <= q["f"] <= b)]
    for q in cues:                                  # dropped on their own frames first, then the later ones move up
        if isinstance(q.get("f"), int) and q["f"] > b:
            q["f"] -= n
    plan["cues"] = cues


def _trim_front(L: dict, f: int) -> dict:
    """The layer starting at f instead: its source / overlay in-point moves on by the frames dropped; a clip's jumps
    after f (a stutter, a ramp) stay, from the source frame it shows at f."""
    if L.get("type") == "clip":
        src = _src_at(L, f)
        later = [[int(j[0]), j[1]] for j in L.get("jumps") or [] if int(j[0]) > f]
        L["in"] = src
        if later:
            L["jumps"] = [[f, src]] + later
        else:
            L.pop("jumps", None)
    elif L.get("type") == "overlay":                # (at its speed: captions on a sped-up shot, 0.6.0 the Editor)
        L["in"] = int(L.get("in", 0)) + int((f - int(L["start"])) * float(L.get("speed", 1.0)) + 1e-6)
        L.pop("land", None)                         # its move no longer lands where it was landed: never re-landed
    L["start"] = f
    return L


CURVES = ("zoom", "dx", "dy", "opacity", "gain", "rotation")    # a layer's animated values on the timeline's frames


def move_curves(L: dict, fn) -> None:
    """Every animated value of L (its keys, a curve of frames' first frame, the zoom point's two) through fn(frame)."""
    def one(v):
        if isinstance(v, dict) and v.get("keys"):
            v["keys"] = [[fn(int(x[0])), *x[1:]] for x in v["keys"]]
        elif isinstance(v, dict) and "values" in v and "start" in v:
            v["start"] = fn(int(v["start"]))
    for k in CURVES:
        one(L.get(k))
    if isinstance(L.get("anchor"), list):           # (2026-10-26: a shake's frames stayed behind a moved shot)
        for a in L["anchor"]:
            one(a)


def _shift(L: dict, d: int) -> dict:
    L["start"] = int(L.get("start", 0)) + d
    if "end" in L:
        L["end"] = int(L["end"]) + d
    move_curves(L, lambda f: f + d)
    if L.get("jumps"):
        L["jumps"] = [[int(x[0]) + d, x[1]] for x in L["jumps"]]
    for key in ("flash_white", "black"):
        if L.get(key):
            L[key] = [int(x) + d for x in L[key]]
    if L.get("flash_over"):
        L["flash_over"] = {str(int(k) + d): v for k, v in L["flash_over"].items()}
    ld = L.get("land")
    if isinstance(ld, dict):                        # a landed graphic: its landing moves with it (build.py)
        for k in ("at", "asked", "start"):
            if isinstance(ld.get(k), int):
                ld[k] += d
    return L


def _zoom_keys(L: dict, curves: dict) -> list:
    """The layer's zoom as keys [[f, v, ease], ...] (a number, keys, a curve of frames or a named curve)."""
    z = L.get("zoom", 1.0)
    if isinstance(z, (int, float)):
        return [[int(L["start"]), float(z), "hold"]]
    if isinstance(z, dict) and z.get("keys"):
        return [list(k) for k in z["keys"]]
    from .compose import Curve                      # any other curve: sampled per frame
    c = Curve(z, curves, 1.0)
    return [[f, round(float(c(f)), 5), "linear"] for f in range(int(L["start"]), int(L["end"]) + 1)]


def apply(plan: dict, ops: list[dict]) -> tuple[dict, list[str], list[dict]]:
    """The list on a copy of the plan: (the new plan, a line per change with frame numbers, the tool steps still to
    run - captions / graphics - for draft_edit.py). Cuts last, from the end, so every frame refers to the plan given."""
    from . import edtrans as TR                     # (an Editor's transitions: made again from the shots after the list)
    P = TR.strip(copy.deepcopy(plan))
    P.setdefault("cues", [])
    done, steps, punches = [], [], []
    for o in ops:
        if o["op"] == "punch":                       # merged into the shot's zoom: earlier punches and keys stay
            from .compose import Curve
            L = shot_at(P, o["f"])
            f, end = o["f"], o["f"] + o["ease"]
            cur = Curve(L.get("zoom"), P.get("curves") or {}, 1.0)
            keys = [k for k in _zoom_keys(L, P.get("curves") or {}) if not (f - 1 <= int(k[0]) <= end)]
            if o["ease"]:
                new = [[f, round(float(cur(f)), 5), "smooth"], [end, o["z"], "hold"]]
            else:
                new = ([[f - 1, round(float(cur(f - 1)), 5), "hold"]] if f - 1 >= L["start"] else []) + [[f, o["z"], "hold"]]
            L["zoom"] = {"keys": sorted(keys + new, key=lambda k: int(k[0]))}
            L.setdefault("anchor", [0.5, 0.42])
            punches.append(o["f"])
            done.append(f"punch-in {o['z']:g} at f{o['f']} on {L['id']}")
        elif o["op"] == "shot":
            S = shots(P)
            L = next((x for x in S if x.get("id") == o["shot"]), None) or (
                S[int(o["shot"]) - 1] if o["shot"].isdigit() and 0 < int(o["shot"]) <= len(S) else None)
            if L is None:
                raise ListError(f"line {o['line']}: no shot {o['shot']} ({len(S)} shots)")
            L["zoom"] = o["z"]
            L.setdefault("anchor", [0.5, 0.42])
            done.append(f"{L['id']} f{L['start']}-f{L['end']}: zoom {o['z']:g}")
        elif o["op"] == "hold":
            L = shot_at(P, o["a"])
            P["layers"].append({**{k: v for k, v in L.items() if k not in ("jumps", "speed")},
                                "id": f"hold_{o['a']}", "start": o["a"], "end": o["b"], "in": _src_at(L, o["a"]),
                                "hold": True})
            done.append(f"hold f{o['a']}-f{o['b']} (the picture of {L['id']} at f{o['a']})")
        elif o["op"] == "sfx":
            P["cues"].append({"f": o["f"], "kind": o["kind"], "what": f"list line {o['line']}"})
            done.append(f"sfx {o['kind']} at f{o['f']}")
        elif o["op"] == "layer":
            P["layers"].append(o["layer"])
            done.append(f"layer {o['layer'].get('id', o['layer']['type'])} f{o['layer'].get('start')}-"
                        f"f{o['layer'].get('end')}")
        elif o["op"] in ("caption", "graphic"):
            steps.append(o)
    for o in ops:                                       # after the punches they may name
        if o["op"] == "sfx_on":
            at = (punches if o["on"] == "punch-ins" else [x["start"] for x in shots(P)][1:] if o["on"] == "cuts"
                  else [s["f"] for s in steps if s["op"] == "graphic"])
            P["cues"] += [{"f": f, "kind": o["kind"], "what": f"{o['on']} (list line {o['line']})"} for f in at]
            done.append(f"sfx {o['kind']} on {len(at)} {o['on']}")
    for o in sorted((o for o in ops if o["op"] == "cut"), key=lambda o: -o["a"]):
        cut(P, o["a"], o["b"])
        done.append(f"cut f{o['a']}-f{o['b']} ({o['b'] - o['a'] + 1} frames)")
    TR.build(P)
    return P, done, steps


def moved(plan_before: dict, ops: list[dict], f: int) -> int | None:
    """Where frame f of the plan before the list lands after its cuts (None = cut out) - for graphics placed by
    the list's frames."""
    d = 0
    for o in ops:
        if o["op"] == "cut":
            if o["a"] <= f <= o["b"]:
                return None
            if f > o["b"]:
                d += o["b"] - o["a"] + 1
    return f - d
