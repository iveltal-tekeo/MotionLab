"""The quick draft (0.4, Edit > "In their style" / "With your words"): a first edit of the user's clips in a style
(style.py), made by rules in seconds - no model, no Claude. Claude starts from it for an edit by feel
(/recreate-video feel:...); the app runs it as a job. tools\\draft_edit.py does the files, the music and the render;
this module only plans.

- music mode: cut points from the style's shot lengths (a log-normal between its p10 and p90), its hook (cuts in the
  first 3 s), snapped to the music's beats as often as the style cuts on the beat, a cut on every drop; for each shot
  the best unused moment of the clips (sharp, well exposed, as much motion as the style's energy, no cut inside);
  the style's effects drawn with the compositor's layers at its rate per minute (FX), a flash on each drop.
- talk mode (a talking video): the clips' own sound in order with the pauses cut out (jump cuts), a punch-in on every
  other cut, B-roll (clips nobody talks in) over the talking now and then.
The result is a normal plan (compose.py): render_video.py renders it, Claude refines it, resolve_build builds it.
Frames are the plan's (the caches' fps); everything is seeded, so the same arguments give the same draft.
"""
from __future__ import annotations

import math

import numpy as np

from . import taxonomy
from .style import lognormal_sigma

NEUTRAL = {"black": 0, "white": 255, "gamma": 1.0, "out_black": 0.0, "out_white": 1.0, "saturation": 1.0}
HOOK_S = 3.0
# what the draft can draw: where it goes (a cut between two shots, a shot, the start / end) and the shortest shot
# (seconds) it needs. Other types (spin, blur, invert, split screen, text / graphics) are listed for Claude / Resolve.
FX = {
    "crossfade": ("cut", 0.6), "dip_black": ("cut", 0.6), "dip_white": ("cut", 0.6), "flash_white": ("cut", 0.12),
    "flash_black": ("cut", 0.2), "zoom_transition": ("cut", 0.35), "push_slide": ("cut", 0.4),
    "whip_pan": ("cut", 0.3),
    "zoom_in": ("shot", 1.0), "zoom_out": ("shot", 1.0), "shake": ("shot", 0.4), "freeze": ("shot", 0.8),
    "stutter": ("shot", 0.6), "speed_ramp": ("shot", 1.2), "flash": ("shot", 0.3), "flash_color": ("shot", 0.3),
    "rgb_split": ("shot", 0.35), "light_leak": ("shot", 0.8), "mirror": ("shot", 0.2),
    "fade_in": ("edge", 0), "fade_out": ("edge", 0),
}
ALIAS = {"wipe": "push_slide", "mask_reveal": "push_slide", "luma_fade": "crossfade", "frame_repeat": "stutter",
         "strobe": "stutter", "glitch": "rgb_split", "sat_pop": "flash_color", "hard_cut": None, "jump_cut": None}
TALK_OK = {"flash_white", "flash_black", "dip_black", "dip_white", "zoom_transition", "flash", "flash_color",
           "rgb_split", "light_leak", "fade_in", "fade_out"}       # nothing that shifts the picture against the sound
ZOOMY = {"zoom_in", "zoom_out", "shake", "zoom_transition"}
SLIDE = {"push_slide", "whip_pan", "crossfade"}                  # the two shots overlap: both need spare frames
# what moves the whole picture: each reads as a jolt. At most one this often, and never between two shots of the same
# take (the same face lurching and snapping back) - the user, 2026-10-23, of a talking edit with a zoom-through at
# every sentence: "it makes too many whip pans or zooms ... it's very weird"
MOVES = ZOOMY | {"whip_pan", "push_slide"}
MOVE_GAP_S = {"talk": 8.0, "other": 3.0}
HOW = {
    "crossfade": "the next shot fades in over the last one", "dip_black": "a dip through black",
    "dip_white": "a dip through white", "flash_white": "an over-exposed flash into the next shot (L001)",
    "flash_black": "one black frame before the cut", "zoom_transition": "zoom-through: punch in to the cut, out of it",
    "push_slide": "the next shot pushes the last one out", "whip_pan": "a fast whip into the next shot",
    "zoom_in": "a slow push-in", "zoom_out": "a slow pull-out", "shake": "a short camera shake",
    "freeze": "the end of the shot freezes", "stutter": "a few frames repeat (stutter)",
    "speed_ramp": "the second half changes speed", "flash": "a bright flash on the beat",
    "flash_color": "a colour flash on the beat", "rgb_split": "the red channel splits off for a few frames",
    "light_leak": "a warm light leak", "mirror": "the shot is mirrored", "fade_in": "fades in from black",
    "fade_out": "fades out to black",
}


def _f(sec: float, fps: float, lo: int = 1) -> int:
    return max(lo, int(round(sec * fps)))


# ------------------------------------------------------------------------------------------------ cut points
def cut_points(N: int, fps: float, rhythm: dict, beats: list[float], drops: list[float], rng) -> list[int]:
    """Cut frames (each = the first frame of a new shot) for a timeline of N frames."""
    R = rhythm or {}
    med = float(R.get("median_shot_s") or 2.0)
    p10 = float(R.get("p10_shot_s") or med * 0.6)
    p90 = float(R.get("p90_shot_s") or med * 1.6)
    p10, p90 = min(p10, med), max(p90, med)
    mu, sg = math.log(max(med, 0.1)), lognormal_sigma(p10, p90)
    lo, hi = max(0.24, 0.8 * p10), max(1.25 * p90, 0.5)
    T = N / fps
    t, cuts = 0.0, []
    k = int(R.get("hook_cuts_3s") or 0)
    if k > 0:
        step = HOOK_S / (k + 0.4)
        for _ in range(k):
            t += step * (0.85 + 0.3 * rng.random())
            cuts.append(t)
    elif R.get("first_cut_s"):
        t = float(R["first_cut_s"])
        cuts.append(t)
    while True:
        t += min(hi, max(lo, float(rng.lognormal(mu, sg))))
        if t >= T - max(lo, 0.4):
            break
        cuts.append(t)
    bt = sorted(b / fps for b in beats if 0 < b < N)
    pct = R.get("cuts_on_beat_pct")
    if len(bt) >= 2 and pct is not None:
        period = float(np.median(np.diff(bt)))
        arr = np.asarray(bt)
        for i, c in enumerate(cuts):
            if rng.random() < float(pct) / 100:
                j = int(np.argmin(np.abs(arr - c)))
                if abs(arr[j] - c) <= 0.55 * period:
                    cuts[i] = float(arr[j])
    for d in drops:
        dt = d / fps
        if not 0.5 < dt < T - 0.5:
            continue
        near = [i for i, c in enumerate(cuts) if abs(c - dt) <= 0.4]
        if near:
            cuts[min(near, key=lambda i: abs(cuts[i] - dt))] = dt
        else:
            cuts.append(dt)
    gap = max(6, _f(0.24, fps))
    out, last = [], 0
    for f in sorted({int(round(c * fps)) for c in cuts}):
        if f - last >= gap and N - f >= gap:
            out.append(f)
            last = f
    return out


def fit_to_clips(cuts: list[int], N: int, longest: int) -> list[int]:
    """Extra cuts so no shot is longer than the longest clip can give."""
    out, prev = [], 0
    for c in cuts + [N]:
        while c - prev > longest:
            prev += longest
            out.append(prev)
        if c < N:
            out.append(c)
        prev = c
    return out


# ------------------------------------------------------------------------------------------------ effects
def _budget(style: dict, minutes: float, talk: bool, rng) -> tuple[list, list]:
    want, skipped = [], []
    effects = style.get("effects", [])
    for i, e in enumerate(effects):
        t = ALIAS.get(e["type"], e["type"])
        if t is None:
            continue
        if t not in FX or (talk and t not in TALK_OK):
            skipped.append({"type": e["type"], "label": e.get("label") or taxonomy.label(e["type"]),
                            "per_min": e.get("per_min"),
                            "why": "the clips' sound must stay in sync" if t in FX else "not drawn by the quick draft"})
            continue
        exp = float(e.get("per_min") or 0) * minutes
        n = int(exp) + (1 if rng.random() < exp - int(exp) else 0)
        if n == 0 and i < 3 and minutes >= 0.2 and (e.get("per_min") or 0) > 0:
            n = 1                                       # the style's signature effects show up at least once
        if n:
            want.append([t, n, e])
    return want, skipped


def place_effects(shots: list[tuple[int, int]], style: dict, fps: float, beats: list[float], downbeats: set,
                  drops: list[float], rng, talk: bool = False,
                  max_src: int | None = None, same: set | None = None) -> tuple[dict, dict, list, list]:
    """(effects per cut index, per shot index, at the edges, skipped types). A cut i = shots[i][0] (i >= 1).
    max_src = the longest clip: a speed ramp only where the clip can give the frames it reads. same = the cuts whose
    two shots come from the same take (no move there). Moves (MOVES) keep MOVE_GAP_S between them."""
    N = shots[-1][1] + 1
    want, skipped = _budget(style, N / fps / 60, talk, rng)
    at_cut: dict[int, dict] = {}
    at_shot: dict[int, dict] = {}
    edges: list[str] = []
    same = same or set()
    gap = _f(MOVE_GAP_S["talk" if talk else "other"], fps)
    moved: list[int] = []                                    # frames of the moves placed so far

    def crowded(f: int) -> bool:
        return any(abs(f - m) < gap for m in moved)
    lens = [e - s + 1 for s, e in shots]
    drop_f = [int(round(d)) for d in drops]
    beat_f = [int(round(b)) for b in beats]
    hook_f = _f(HOOK_S, fps)

    def on_drop(f):
        return any(abs(f - d) <= 1 for d in drop_f)
    if drop_f and not talk and (style.get("energy") == "high" or any(w[0] in ("flash_white", "flash") for w in want)):
        for i in range(1, len(shots)):
            if on_drop(shots[i][0]):
                at_cut[i] = {"type": "flash_white", "why": "on a drop of the music"}
                for w in want:
                    if w[0] == "flash_white" and w[1] > 0:
                        w[1] -= 1
                        break
    order = sorted(want, key=lambda w: (FX[w[0]][0] != "edge", -FX[w[0]][1]))       # long-shot needs first
    for t, n, e in order:
        where, need_s = FX[t]
        need = _f(need_s, fps)
        if where == "edge":
            edges.append(t)
            continue
        for _ in range(n):
            best, best_s = None, -1e9
            if where == "cut":
                for i in range(1, len(shots)):
                    c = shots[i][0]
                    a, b = lens[i - 1], lens[i]
                    if i in at_cut or min(a, b) < need:
                        continue
                    if t in MOVES and (i in same or crowded(c)):
                        continue
                    if t in ZOOMY and ((at_shot.get(i - 1) or {}).get("type") in ZOOMY
                                       or (at_shot.get(i) or {}).get("type") in ZOOMY):
                        continue
                    sc = rng.random() * 0.5
                    if t in ("flash_white", "zoom_transition", "whip_pan", "flash_black"):
                        sc += 1.0 * on_drop(c) + 0.5 * (c in downbeats)
                    if t in ("crossfade", "dip_black", "dip_white"):
                        sc += 0.6 * (min(a, b) / fps >= 1.5) - 2.0 * (c < hook_f)
                    if sc > best_s:
                        best, best_s = i, sc
                if best is not None:
                    at_cut[best] = {"type": t, "why": e.get("label") or t}
                    if t in MOVES:
                        moved.append(shots[best][0])
            else:
                for i, (s, en) in enumerate(shots):
                    if i in at_shot or lens[i] < need:
                        continue
                    if t == "speed_ramp" and max_src and lens[i] + (lens[i] - lens[i] // 2) + 16 > max_src:
                        continue
                    if t in ZOOMY and any((at_cut.get(j) or {}).get("type") in ZOOMY for j in (i, i + 1)):
                        continue
                    if t in MOVES and crowded(s):
                        continue
                    if t == "shake" and any((at_cut.get(j) or {}).get("type") in SLIDE for j in (i, i + 1)):
                        continue
                    sc = rng.random() * 0.5
                    if t in ("shake", "flash", "flash_color", "rgb_split"):
                        sc += 1.0 * on_drop(s) + 0.5 * (s in downbeats)
                    if t in ("freeze", "speed_ramp", "light_leak", "zoom_in", "zoom_out"):
                        sc += 0.3 * lens[i] / fps
                    if sc > best_s:
                        best, best_s = i, sc
                if best is not None:
                    s, en = shots[best]
                    inner = [b for b in beat_f if s + 3 <= b <= en - 4]
                    at_shot[best] = {"type": t, "why": e.get("label") or t,
                                     "beat": inner[len(inner) // 2] if inner else None}
                    if t in MOVES:
                        moved.append(s)
    return at_cut, at_shot, edges, skipped


def source_need(shots, at_cut, at_shot, fps) -> list[tuple[int, int, int]]:
    """Per shot (frames before its first frame, frames it shows, frames after) the clip must have: the overlapping
    transitions borrow frames on both sides, a speed-up reads more."""
    out = []
    for i, (s, e) in enumerate(shots):
        L = e - s + 1
        pre = _ovl(at_cut.get(i), fps) // 2 if i in at_cut else 0
        post = (_ovl(at_cut.get(i + 1), fps) + 1) // 2 if (i + 1) in at_cut else 0
        fx = (at_shot.get(i) or {}).get("type")
        if fx == "speed_ramp":
            L += (L - L // 2)                           # the second half at 2x reads twice as many frames
        out.append((pre, L, post))
    return out


def _ovl(cut: dict | None, fps: float) -> int:
    t = (cut or {}).get("type")
    if t == "crossfade":
        return min(14, max(6, _f(0.4, fps)))
    if t == "push_slide":
        return min(10, max(6, _f(0.33, fps)))
    if t == "whip_pan":
        return min(6, max(4, _f(0.2, fps)))
    return 0


# ------------------------------------------------------------------------------------------------ the clips
DIP_SHARE, DIP_WIN = 0.6, 15     # a frame under 60 % of the luma median of the 15 frames each side = a dip


def luma_dips(luma) -> list[int]:
    """0.5.3 (A7): the 1-2 frame luma dips of a clip - a screen recording repaints BLACK for one frame at every page /
    tab change (luma 6.5 against 11.4 around it, local-make-15), too small for the brightness jump test of a cut on a
    dark recording. Frames whose luma is under DIP_SHARE of the median around them, the frames on both sides not."""
    y = np.asarray(luma, float)
    n = len(y)
    out = []
    for f in range(1, n - 1):
        lo, hi = max(0, f - DIP_WIN), min(n, f + DIP_WIN + 1)
        med = float(np.median(y[lo:hi]))
        if med > 2 and y[f] < DIP_SHARE * med and (y[f - 1] >= DIP_SHARE * med or y[f + 1] >= DIP_SHARE * med):
            out.append(f)
    return out


def quality(clip: dict, energy: str) -> tuple[np.ndarray, np.ndarray]:
    """Per frame: a quality score (sharp, well exposed, the right amount of motion) and 1 where the clip itself cuts
    (a jump in motion or brightness - a window should not contain one)."""
    st = clip["stats"]
    n = clip["frames"]
    sharp = np.asarray(st.get("sharp", np.ones(n)), float)[:n]
    pos = sharp[sharp > 0]
    sh = np.log(np.clip(sharp / (float(np.median(pos)) if len(pos) else 1.0), 0.05, 4.0))
    luma = np.asarray(st.get("luma", np.full(n, 50.0)), float)[:n]
    p95 = np.asarray(st.get("p95", np.full(n, 80.0)), float)[:n]
    expo = np.clip((12 - luma) / 12, 0, None) + np.clip((luma - 90) / 10, 0, None) + np.clip((25 - p95) / 25, 0, None)
    mot = np.asarray(st.get("motion", np.zeros(n)), float)[:n]
    ref = float(np.percentile(mot, 90)) if n > 5 else 1.0
    mn = np.clip(mot / max(ref, 1e-3), 0, 1.5)
    em = 0.35 * mn if energy == "high" else -0.35 * np.clip(mn - 0.5, 0, None) if energy == "calm" else 0.0
    q = 0.8 * sh - 1.5 * expo + em
    med = float(np.median(mot)) if n else 0.0
    spike = (mot > max(5 * med, 12.0)) | (np.abs(np.diff(luma, prepend=luma[:1])) > 15)
    spike[luma_dips(luma)] = True                       # a screen recording's black repaint: no shot across it
    spike[:1] = False
    return q, spike.astype(float)


def pick_windows(needs, clips, energy, fps, rng) -> list[dict]:
    """For each shot the best unused moment of the clips (one pass, in timeline order)."""
    prep = {}
    for c in clips:
        q, sp = quality(c, energy)
        prep[c["id"]] = (np.concatenate([[0.0], np.cumsum(q)]), np.concatenate([[0.0], np.cumsum(sp)]), q)
    used = {c["id"]: np.zeros(c["frames"], bool) for c in clips}
    picks, prev = [], None
    for pre, L, post in needs:
        need = pre + L + post
        best = None
        for c in clips:
            n, cid = c["frames"], c["id"]
            if n < need:
                continue
            edge = min(_f(0.3, fps, 0), (n - need) // 2)
            A = np.arange(edge, n - need - edge + 1, max(1, min(L // 3, 12)))
            if not len(A):
                A = np.array([max(0, (n - need) // 2)])
            cq, cs, _ = prep[cid]
            q = (cq[A + pre + L] - cq[A + pre]) / max(1, L)
            spikes = cs[A + need] - cs[A + 1]
            cu = np.concatenate([[0], np.cumsum(used[cid])])
            over = (cu[A + need] - cu[A]) / need
            score = q - 3.0 * np.minimum(spikes, 1) - 2.5 * over + rng.normal(0, 0.12, len(A))
            if prev == cid and len(clips) > 1:
                score = score - 0.6
            j = int(np.argmax(score))
            if best is None or score[j] > best[0]:
                best = (float(score[j]), c, int(A[j]))
        if best is None:                     # no clip is long enough: the longest one from its start, its end holds
            c = max(clips, key=lambda c: c["frames"])
            best = (0.0, c, 0)
        _, c, a = best
        used[c["id"]][a:a + need] = True
        if c.get("photo"):                   # a photo is one picture: once used, every window of it counts as seen
            used[c["id"]][:] = True
        why = _why(c, a + pre, L) if c["frames"] >= need else "the longest clip - shorter than the shot, its end holds"
        picks.append({"sid": c["id"], "in": a + pre, "why": why})
        prev = c["id"]
    return picks


def _why(c: dict, a: int, L: int) -> str:
    st, n = c["stats"], c["frames"]
    seg = slice(a, min(n, a + L))
    sharp = np.asarray(st.get("sharp", np.ones(n)), float)
    mot = np.asarray(st.get("motion", np.zeros(n)), float)
    s_rel = float(np.mean(sharp[seg]) / max(1e-6, np.median(sharp[sharp > 0]) if (sharp > 0).any() else 1.0))
    m_rel = float(np.mean(mot[seg]) / max(1e-6, np.percentile(mot, 90) if n > 5 else 1.0))
    bits = ["sharp" if s_rel >= 1.05 else "soft" if s_rel < 0.7 else "in focus",
            "lots of motion" if m_rel >= 0.8 else "calm" if m_rel < 0.25 else "some motion"]
    lu = float(np.mean(np.asarray(st.get("luma", np.full(n, 50.0)), float)[seg]))
    if lu < 18:
        bits.append("dark")
    elif lu > 85:
        bits.append("bright")
    return ", ".join(bits)


# ------------------------------------------------------------------------------------------------ layers
def _zoom_at(layer: dict, f: int) -> float:
    z = layer.get("zoom", 1.0)
    if isinstance(z, (int, float)):
        return float(z)
    ks = z["keys"]
    if f <= ks[0][0]:
        return ks[0][1]
    if f >= ks[-1][0]:
        return ks[-1][1]
    for (fa, va, *_), (fb, vb, *_) in zip(ks, ks[1:]):
        if fa <= f <= fb:
            return va + (vb - va) * (f - fa) / max(1, fb - fa)
    return 1.0


def _src_at(layer: dict, f: int) -> int:
    if layer.get("hold"):
        return int(layer["in"])
    if "jumps" in layer:
        j = [x for x in layer["jumps"] if x[0] <= f][-1]
        return j[1] + int(math.floor((f - j[0]) * float(layer.get("speed", 1.0)) + 1e-6))
    return int(layer["in"]) + int(math.floor((f - layer["start"]) * float(layer.get("speed", 1.0)) + 1e-6))


def _move_start(layer: dict, new_start: int):
    d = layer["start"] - new_start
    if "jumps" in layer:
        layer["jumps"][0] = [new_start, layer["jumps"][0][1] - d]
    else:
        layer["in"] = int(layer["in"]) - d
    layer["start"] = new_start


def build_layers(shots, picks, at_cut, at_shot, edges, W, H, fps, rng, talk_zoom: bool = False,
                 broll: list | None = None) -> tuple[list, list]:
    """The plan's layers + the effects as placed (frame, type, how) for the notes."""
    segs: list[list[dict]] = []
    over: list[dict] = []
    placed: list[dict] = []
    for i, ((s, e), p) in enumerate(zip(shots, picks)):
        base = {"type": "clip", "id": f"s{i + 1:02d}_{p['sid']}", "src": p["sid"], "start": s, "end": e,
                "rect": [0, 0, W, H], "in": int(p["in"])}
        if talk_zoom and i % 2:
            base["zoom"], base["anchor"] = 1.12, [0.5, 0.42]          # a punch-in on every other jump cut
        segs.append([base])
    for i, fx in sorted(at_shot.items()):
        t, layer = fx["type"], segs[i][0]
        s, e = shots[i]
        L = e - s + 1
        f = fx.get("beat") or s + L // 2
        z0 = float(layer.get("zoom", 1.0)) if isinstance(layer.get("zoom", 1.0), (int, float)) else 1.0
        if t == "zoom_in":
            layer["zoom"] = {"keys": [[s, z0, "linear"], [e, round(z0 * 1.08, 4)]]}
            f = s
        elif t == "zoom_out":
            layer["zoom"] = {"keys": [[s, round(z0 * 1.08, 4), "linear"], [e, z0]]}
            f = s
        elif t == "shake":
            f = s
            n = min(10, L - 1)
            amp = 0.025 / max(z0 * 1.06, 1.0)
            jit = [(1 - k / n) * amp for k in range(n)]
            layer["zoom"] = round(z0 * 1.06, 4)
            ax0, ay0 = (layer.get("anchor") or [0.5, 0.5])
            layer["anchor"] = [{"start": s, "values": [round(ax0 + j * rng.uniform(-1, 1), 4) for j in jit] + [ax0]},
                               {"start": s, "values": [round(ay0 + j * rng.uniform(-1, 1), 4) for j in jit] + [ay0]}]
        elif t == "freeze":
            f = s + max(1, int(L * 0.6))
            layer["end"] = f - 1
            segs[i].append({**{k: v for k, v in layer.items() if k not in ("jumps", "speed")},
                            "id": layer["id"] + "_freeze", "start": f, "end": e, "hold": True,
                            "in": _src_at(layer, f), "flash_over": {str(f): 0.3}})
        elif t == "stutter":
            f = s + max(1, L // 3)
            k = 3 if L >= _f(0.8, fps) else 2
            i0 = _src_at(layer, f)
            layer["jumps"] = [[s, int(layer.pop("in"))], [f, i0], [f + k, i0], [f + 2 * k, i0], [f + 3 * k, i0 + k]]
        elif t == "speed_ramp":
            f = s + L // 2
            layer["end"] = f - 1
            segs[i].append({**{k: v for k, v in layer.items() if k not in ("jumps",)}, "id": layer["id"] + "_ramp",
                            "start": f, "end": e, "in": _src_at(layer, f), "speed": 2.0})
        elif t == "flash":
            layer.setdefault("flash_over", {}).update({str(f): 0.6, str(f + 1): 0.3})
        elif t == "flash_color":
            col = [[1.0, 0.25, 0.6], [0.2, 0.8, 1.0], [1.0, 0.6, 0.15]][int(rng.integers(0, 3))]
            over.append({"type": "solid", "id": f"colorflash_{i + 1:02d}", "start": f, "end": f + 2,
                         "rect": [0, 0, W, H], "color": col, "blend": "screen",
                         "opacity": {"start": f, "values": [0.65, 0.35, 0.12]}})
        elif t == "rgb_split":
            f = min(max(s + 3, fx.get("beat") or s + L // 3), max(s + 1, e - 10))     # clear of the next transition
            for k, (tint, blend, dx) in enumerate((([0, 1, 1], "normal", 0), ([1, 0, 0], "add", round(0.012 * W)))):
                over.append({"type": "clip", "id": f"rgb_{i + 1:02d}_{k}", "src": layer["src"], "start": f,
                             "end": f + 2, "rect": [0, 0, W, H], "in": _src_at(layer, f), "tint": tint,
                             "blend": blend, "dx": dx, "zoom": round(_zoom_at(layer, f), 4),
                             **({"anchor": layer["anchor"]} if isinstance(layer.get("anchor"), list)
                                and all(isinstance(a, (int, float)) for a in layer["anchor"]) else {})})
        elif t == "light_leak":
            n = min(L - 1, _f(0.6, fps))
            f = s + (L - n) // 2
            over.append({"type": "solid", "id": f"leak_{i + 1:02d}", "start": f, "end": f + n - 1,
                         "rect": [round(W * 0.35), 0, W - round(W * 0.35), H], "color": [1.0, 0.55, 0.2],
                         "blend": "screen", "opacity": {"keys": [[f, 0, "smooth"], [f + n // 2, 0.55, "smooth"],
                                                                 [f + n - 1, 0]]}})
        elif t == "mirror":
            layer["mirror"] = True
            f = s
        placed.append({"frame": int(f), "type": t, "shot": i + 1, "how": HOW.get(t, t), "why": fx.get("why")})
    for i, fx in sorted(at_cut.items()):
        t, c = fx["type"], shots[i][0]
        out, inn = segs[i - 1][-1], segs[i][0]
        d = _ovl(fx, fps)
        a = c - d // 2
        if t == "crossfade":
            out["end"] = a + d - 1
            _move_start(inn, a)
            inn["opacity"] = {"keys": [[a, 0, "linear"], [a + d - 1, 1]]}
        elif t in ("push_slide", "whip_pan"):
            out["end"] = a + d - 1
            _move_start(inn, a)
            vertical = H > W and rng.random() < 0.5
            ax, size = ("dy", H) if vertical else ("dx", W)
            sgn = -1 if rng.random() < 0.5 else 1
            e_out, e_in = ("in3", "out3") if t == "whip_pan" else ("smooth", "smooth")
            out[ax] = {"keys": [[a, 0, e_out], [a + d - 1, sgn * size]]}
            inn[ax] = {"keys": [[a, -sgn * size, e_in], [a + d - 1, 0]]}
        elif t in ("dip_black", "dip_white"):
            h = min(8, max(4, _f(0.25, fps)))
            over.append({"type": "solid", "id": f"dip_{i:02d}", "start": c - h, "end": c + h,
                         "rect": [0, 0, W, H], "color": [0, 0, 0] if t == "dip_black" else [1, 1, 1],
                         "opacity": {"keys": [[c - h, 0, "smooth"], [c, 1, "smooth"], [c + h, 0]]}})
        elif t == "flash_white":
            inn.setdefault("flash_over", {}).update({str(c): 0.9, str(c + 1): 0.55, str(c + 2): 0.25})
        elif t == "flash_black":
            out.setdefault("black", []).append(c - 1)
        elif t == "zoom_transition":
            k = min(8, max(4, _f(0.24, fps)))
            zo = _zoom_at(out, c - k)
            zi = float(inn.get("zoom", 1.0)) if isinstance(inn.get("zoom", 1.0), (int, float)) else 1.0
            out["zoom"] = {"keys": [[c - k, round(zo, 4), "in"], [c - 1, round(zo * 1.7, 4)]]}
            inn["zoom"] = {"keys": [[c, round(zi * 1.7, 4), "out"], [c + k - 1, zi]]}
        placed.append({"frame": int(c), "type": t, "shot": i + 1, "how": HOW.get(t, t), "why": fx.get("why")})
    N = shots[-1][1] + 1
    for t in edges:
        k = min(N // 4, _f(0.6, fps))
        if t == "fade_in":
            over.append({"type": "solid", "id": "fade_in", "start": 0, "end": k - 1, "rect": [0, 0, W, H],
                         "color": [0, 0, 0], "opacity": {"keys": [[0, 1, "smooth"], [k - 1, 0]]}})
            placed.append({"frame": 0, "type": t, "shot": 1, "how": HOW[t], "why": "the style starts this way"})
        else:
            over.append({"type": "solid", "id": "fade_out", "start": N - k, "end": N - 1, "rect": [0, 0, W, H],
                         "color": [0, 0, 0], "opacity": {"keys": [[N - k, 0, "smooth"], [N - 1, 1]]}})
            placed.append({"frame": N - k, "type": t, "shot": len(shots), "how": HOW[t], "why": "the style ends this way"})
    layers = [L for seg in segs for L in seg] + list(broll or []) + over
    for L in layers:                                  # keep the plan readable: drop default values
        if isinstance(L.get("zoom"), (int, float)) and L["zoom"] == 1.0:
            L.pop("zoom")
    return layers, sorted(placed, key=lambda x: x["frame"])


def photo_shots(layers: list, clips: list[dict]) -> int:
    """Photos are still shots (2026-10-24): every clip layer of a photo holds its one frame ("hold", in 0) with a slow
    zoom (Ken Burns: in, then out, by turns) unless an effect already zooms it, and the photo's "fit" ("contain" =
    the whole photo over a blurred copy of itself). In place; returns how many layers are photos."""
    ph = {c["id"]: c for c in clips if c.get("photo")}
    n = 0
    for L in layers:
        c = ph.get(L.get("src")) if L.get("type") == "clip" else None
        if not c:
            continue
        L["hold"], L["in"] = True, 0
        L.pop("jumps", None)
        L.pop("speed", None)
        z = float(c.get("zoom") or 1.0)
        if "zoom" not in L and z > 1.0 and L["end"] > L["start"]:
            L["zoom"] = {"keys": [[L["start"], 1.0, "linear"], [L["end"], z]] if n % 2 == 0
                         else [[L["start"], z, "linear"], [L["end"], 1.0]]}
        if c.get("fit") == "contain":
            L["fit"] = "contain"
        n += 1
    return n


# ------------------------------------------------------------------------------------------------ talk mode
def talk_shots(clips: list[dict], fps: float, max_frames: int | None) -> tuple[list, list]:
    """Talking clips in order (by ID), each spoken part a shot - the pauses between them are cut out. Returns the
    shots (timeline frames) and their picks (clip + in-point)."""
    shots, picks, t = [], [], 0
    for c in sorted((c for c in clips if c.get("speech")), key=lambda c: (len(c["id"]), c["id"])):
        for a, b in c["speech"]:
            L = b - a + 1
            if max_frames and t + L > max_frames:
                L = max_frames - t
                if L < _f(1.0, fps):
                    return shots, picks
            shots.append((t, t + L - 1))
            picks.append({"sid": c["id"], "in": int(a), "why": "spoken part"})
            t += L
            if max_frames and t >= max_frames:
                return shots, picks
    return shots, picks


def broll_layers(shots, clips, every_s: float, fps, W, H, energy, rng) -> tuple[list, list]:
    """B-roll over the talking: every `every_s` seconds (after the first 3 s) the picture switches to a clip nobody
    talks in for 1.5-2.5 s; the sound goes on."""
    pool = [c for c in clips if not c.get("speech")]
    N = shots[-1][1] + 1 if shots else 0
    if not pool or not every_s or N < _f(HOOK_S + every_s, fps):
        return [], []
    longest = max(c["frames"] for c in pool) - 2
    if longest < _f(1.0, fps):                        # cutaways under a second: none rather than a flicker
        return [], []
    starts = list(range(_f(HOOK_S + every_s * 0.5, fps), N - _f(2.0, fps), _f(every_s, fps)))
    needs = [(0, min(_f(rng.uniform(1.5, 2.5), fps), N - f - 1, longest), 0) for f in starts]
    picks = pick_windows(needs, pool, energy, fps, rng)
    layers, notes = [], []
    for k, (f, (_, L, _), p) in enumerate(zip(starts, needs, picks)):
        layers.append({"type": "clip", "id": f"broll_{k + 1:02d}_{p['sid']}", "src": p["sid"], "start": f,
                       "end": f + L - 1, "rect": [0, 0, W, H], "in": p["in"]})
        notes.append({"frame": f, "end": f + L - 1, "sid": p["sid"], "in": p["in"], "why": p["why"]})
    return layers, notes


# ------------------------------------------------------------------------------------------------ the draft
def make(style: dict, clips: list[dict], fps: float, W: int, H: int, N: int | None, mode: str,
         beats: list[float] | None = None, downbeats: set | None = None, drops: list[float] | None = None,
         seed: int = 1) -> dict:
    """The whole draft: shots, picks, effects, layers. N = frames (music mode: required; talk mode: at most)."""
    rng = np.random.default_rng(seed)
    beats, downbeats, drops = beats or [], downbeats or set(), drops or []
    energy = style.get("energy") or "medium"
    usable = [c for c in clips if c["frames"] >= _f(0.5, fps)]
    if not usable:
        raise ValueError("no clip is long enough (at least half a second)")
    broll, broll_notes = [], []
    if mode == "talk":
        shots, picks = talk_shots(usable, fps, N)
        if not shots:
            raise ValueError("nobody talks in the clips (no speech found) - use a music edit instead")
        same = {i for i in range(1, len(picks)) if picks[i]["sid"] == picks[i - 1]["sid"]}     # jump cuts of one take
        at_cut, at_shot, edges, skipped = place_effects(shots, style, fps, [], set(), [], rng, talk=True, same=same)
        broll, broll_notes = broll_layers(shots, usable, float(style.get("broll_every_s") or 0), fps, W, H, energy,
                                          rng)
    else:
        if not N:
            raise ValueError("a music edit needs a length")
        cuts = cut_points(N, fps, style.get("rhythm") or {}, beats, drops, rng)
        longest = max(c["frames"] for c in usable) - 2 * _f(0.3, fps, 0) - 16
        cuts = fit_to_clips(cuts, N, max(_f(0.5, fps), longest))
        bounds = [0] + cuts + [N]
        shots = [(bounds[k], bounds[k + 1] - 1) for k in range(len(bounds) - 1)]
        at_cut, at_shot, edges, skipped = place_effects(shots, style, fps, beats, downbeats, drops, rng,
                                                        max_src=max(c["frames"] for c in usable))
        needs = source_need(shots, at_cut, at_shot, fps)
        picks = pick_windows(needs, usable, energy, fps, rng)
    layers, placed = build_layers(shots, picks, at_cut, at_shot, edges, W, H, fps, rng,
                                  talk_zoom=mode == "talk", broll=broll)
    photo_shots(layers, clips)
    N = shots[-1][1] + 1
    sound = [(p["sid"], int(p["in"]), int(p["in"]) + (e - s)) for (s, e), p in zip(shots, picks)]
    if style.get("wrong"):
        skipped.append({"type": "-", "label": "what you marked wrong", "per_min": None,
                        "why": ", ".join(sorted({w["label"] for w in style["wrong"]})) + " - left out"})
    return {"frames": N, "shots": [{"n": k + 1, "start": s, "end": e, "sid": p["sid"], "in": int(p["in"]),
                                    "why": p["why"]} for k, ((s, e), p) in enumerate(zip(shots, picks))],
            "layers": layers, "effects": placed, "skipped": skipped, "broll": broll_notes, "sound": sound,
            "grade": dict(style.get("grade") or NEUTRAL)}
