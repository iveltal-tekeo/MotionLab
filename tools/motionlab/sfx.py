"""Sound effects (0.5.0 step 4, from projects\\illdari_test_copy_1\\build\\sfx_v2.py): every sound is synthesised here
(no samples, nothing to license), seeded (the same cues give the same file, sample for sample) at 48 kHz, placed on a
graphic's or a plan's frames and levelled against the song under it - measured, since Claude cannot hear.
tools\\sfx.py is the command line.

**Cues** - a graphic lists them in its overlay.json next to its settings ("cues"; overlay.py keeps keys it does not
know, `new --from`, `save` and `set` copy the whole file, and a cue is not part of the render's inputs):
    "cues": [
      {"f": 5, "kind": "whoosh", "what": "logo swings up", "dur": 0.5, "from": 300, "to": 2200},
      {"f": "85 + round(i * min(1, 20 / n))", "repeat": "len(search_text)", "kind": "key", "what": "key"},
      {"f": "pop_in", "kind": "pop", "if": "show_badge", "pan": [-0.5, 0.5], "db": -2}
    ]
- f = the frame the sound starts on (the graphic's fps), a number or a formula of its settings; a riser's sound
  ends on f + dur, so give it the frame where it should start.
- A formula (any number field may be one) reads the settings by id (declared on <html>, the user's values on top),
  `i` / `n` (repeat: the cue's number from 0 and how many), `fps`, `frames`, and len min max abs floor ceil int round
  (round = JavaScript's Math.round, like the page). repeat = how many times (one cue per typed character...);
  if = the cue only when true; what = a note (" 1", " 2"... added for repeats).
- kind = one of KINDS (`sfx.py kinds`); level = another level class (LEVELS) than the kind's; db = more or less
  (-12..+12); pan = -1 (left) .. 1 or [from, to]; seed = another variant of the same sound; the sound's own numbers
  (dur in seconds, from / to in Hz, ...) override its defaults.
Why formulas and not cues the page computes: reading them from the page needs Node and Chrome (HyperFrames) for
every call; a formula is evaluated here in a millisecond and says in one line why the cue is where it is. The
timing rule is then written twice (the page's JavaScript and the cue), so `sfx.py cues` prints every cue with
frame + timecode to check against `overlay.py stills`.

**A plan** (`plan_cues`): the effects drawn in its layers become cues - fast zooms and slides (whoosh / whip, one per
move, the two halves of a zoom-through or a whip joined), flashes (impact / thump / click by strength), black frames,
speed-ups (a riser that lands on the change), stutter jumps (ticks), short colour / RGB flashes (zap), dips (air),
shakes (thump), light leaks (shimmer); plus the cues of every overlay graphic it shows (moved to where the layer
starts) and the plan's own "cues" list (the same format, no settings).

**Levels**: each kind has a level class = (dB against the song, the lowest level in dBFS) - stereo RMS, all TRIM_DB
lower (the user's ear). The song is measured where the effect sounds: the quieter of 400 ms centred on the effect's
loud part (EBU's momentary loudness window) and that loud part alone (at least 100 ms) - so an effect in a
short quiet gap before a loud line is levelled to the gap. An effect's own loud part =
where its 10 ms envelope is within 20 dB of its peak. Its peak stays at or under PEAK_DB; the mix (song + effects)
goes through a look-ahead limiter to CEILING_DB, so it never clips. Every cue's measured levels go into the report.
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
import re
import subprocess
import time
import zlib
from pathlib import Path

import numpy as np
from scipy.ndimage import minimum_filter1d, uniform_filter1d
from scipy.signal import butter, sosfilt

from .timecode import frame_to_tc
from .util import LAB, tool

SR = 48000
PEAK_DB = -6.0                       # an effect's own peak (its mono gain): sfx_v2's loudest (the user: -3 too loud)
CEILING_DB = -1.0                    # the mix (and the stem) never goes over this (sample peak)
SONG_DB = -2.5                       # the song is lowered this much to make room (sfx_v2)
FADE_S = 0.8                         # the mix fades out over the last 0.8 s (0 = off)
WINDOW_S, PRE_S = 0.4, 0.05          # the song window: centred on the effect's loud part, +50 ms each side, >= 0.4 s
NEAR_S = 0.1                         # ... and its loud part alone (>= 0.1 s): the quieter of the two counts
TRIM_DB = -3.0                       # every level (against the song and the lowest one): the user heard the first
                                     # version as "kinda too loud" (2026-10-14, illdari v2's rebuild)
# (dB against the song where the effect sounds, the lowest level in dBFS) - stereo RMS of the effect's loud part.
# sfx_v2's numbers, converted 2026-10-14: it measured only the samples within 13 dB of the sound's peak, which reads
# 4-8 dB louder than the whole loud part (14 dB for a click), so the same numbers here came out ~6 dB louder; minus
# each class's measured median difference on illdari's song (hit and click were always at the peak cap there: their
# sound's own difference). The song is quiet in illdari's intro (-25 dBFS) and loud after its drop (-8.5): a fixed
# level is lost there or too loud here.
LEVELS = {"hit": (-7, -25), "hit_small": (-11, -33), "click": (-20, -43), "pop": (-12, -35), "move": (-16, -38),
          "whip": (-19, -41), "key": (-20, -41), "tick": (-15, -38), "soft": (-21, -44)}
SPARSE_DB = 20.0                     # a sound's level never reads more than this under its peak (sparks: 29 dB)
FLOOR_VS_SONG_DB = -24.0             # 0.5.3 (A4): no effect is placed further under the song than this - the
                                     # precheck's "buried" line (-26) + 2 dB, so a cue's own "db" offset (templates'
                                     # -9..-13, set on a quiet reference) never lands it masked under a loud song


# ------------------------------------------------------------------------------------------------ the sounds
def _tt(dur: float) -> np.ndarray:
    return np.arange(int(dur * SR)) / SR


def _noise(dur: float, seed: int) -> np.ndarray:
    return np.random.default_rng(int(seed)).standard_normal(int(dur * SR))


def _hp(x, fc, order=2):
    return sosfilt(butter(order, fc, "highpass", fs=SR, output="sos"), x)


def _lp(x, fc, order=2):
    return sosfilt(butter(order, fc, "lowpass", fs=SR, output="sos"), x)


def _svf_bp(x: np.ndarray, fc: np.ndarray, q: float) -> np.ndarray:
    """A band-pass whose centre moves sample by sample (TPT state-variable filter); plain floats: ~3x numpy's
    per-sample speed, the same numbers."""
    g = np.tan(np.pi * np.clip(fc, 30, SR * 0.45) / SR)
    k = 1.0 / q
    a1 = 1.0 / (1.0 + g * (g + k))
    a2, a3 = g * a1, g * g * a1
    ic1 = ic2 = 0.0
    out = []
    put = out.append
    for xn, b1, b2, b3 in zip(x.tolist(), a1.tolist(), a2.tolist(), a3.tolist()):
        v3 = xn - ic2
        v1 = b1 * ic1 + b2 * v3
        v2 = ic2 + b2 * ic1 + b3 * v3
        ic1, ic2 = 2 * v1 - ic1, 2 * v2 - ic2
        put(v1)
    return np.asarray(out, float)


def _sweep(f0: float, f1: float, n: int) -> np.ndarray:
    return f0 * (f1 / f0) ** np.linspace(0, 1, n)


def _env_ad(n: int, peak: float, curve_in=2.0, decay=6.0) -> np.ndarray:
    """Rise to 1 at `peak` (0-1 of the length), then an exponential fall; 0 at both ends."""
    x = np.linspace(0, 1, n)
    rise = np.clip(x / max(peak, 1e-3), 0, 1) ** curve_in
    fall = np.exp(-decay * np.clip(x - peak, 0, None) / max(1 - peak, 1e-3))
    e = np.where(x <= peak, rise, fall)
    e[-min(64, n):] *= np.linspace(1, 0, min(64, n))
    return e


def s_whoosh(p, seed):
    n = int(p["dur"] * SR)
    x = _svf_bp(_noise(p["dur"], seed), _sweep(p["from"], p["to"], n), p["q"])
    return x * _env_ad(n, p["peak"], 2.0, p["decay"])


def s_riser(p, seed):
    n = int(p["dur"] * SR)
    x = _svf_bp(_noise(p["dur"], seed), _sweep(p["from"], p["to"], n), p["q"])
    e = np.linspace(0, 1, n) ** 3
    e[-48:] *= np.linspace(1, 0, 48)
    return x * e


def s_air(p, seed):
    n = int(p["dur"] * SR)
    return _lp(_hp(_noise(p["dur"], seed), 400), 2500) * _env_ad(n, 0.45, 1.5, 3.0)


def s_click(p, seed):
    def one(f, level, sd):
        n = int(0.012 * SR)
        t = np.arange(n) / SR
        body = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.0018)
        tick = _hp(_noise(0.012, sd), 2500) * np.exp(-t / 0.0007)
        return level * (0.7 * body + 0.5 * tick)
    out = np.zeros(int(0.08 * SR))
    a, b = one(2900, 1.0, 11), one(3600, 0.55, 12)
    out[:len(a)] += a
    out[int(0.055 * SR):int(0.055 * SR) + len(b)] += b
    return out


def s_key(p, seed):
    r = np.random.default_rng(int(seed))
    t = _tt(0.05)
    f = 220 + r.random() * 160
    thock = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.012)
    tick = _hp(_noise(0.05, seed + 100), 1800) * np.exp(-t / 0.002)
    return (0.8 + 0.3 * r.random()) * (0.55 * thock + 0.6 * tick)


def s_pop(p, seed):
    dur = p["dur"]
    t = _tt(dur)
    f = _sweep(p["from"], p["to"], len(t))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (dur / 4))
    x[:48] *= np.linspace(0, 1, 48)
    return x


def s_chime(p, seed):
    dur, gap, freqs = p["dur"], p["gap"], p["freqs"]
    out = np.zeros(int((dur + gap * len(freqs)) * SR))
    for i, f in enumerate(freqs):
        t = _tt(dur)
        x = (np.sin(2 * np.pi * f * t)
             + 0.25 * np.sin(2 * np.pi * 2.76 * f * t) * np.exp(-t / 0.05)) * np.exp(-t / 0.12)
        s = int(i * gap * SR)
        out[s:s + len(x)] += x
    return out


def s_impact(p, seed):
    dur = p["dur"]
    t = _tt(dur)
    f = 48 + 110 * np.exp(-t / 0.03)
    kick = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)
    body = _lp(_noise(dur, 21), 900) * np.exp(-t / 0.05) * 0.6
    snap = _hp(_noise(dur, 22), 3000) * np.exp(-t / 0.004) * 0.7
    return p["sub"] * kick + body + snap


def s_thump(p, seed):
    dur = p["dur"]
    t = _tt(dur)
    f = 60 + 70 * np.exp(-t / 0.02)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.08)
            + _lp(_noise(dur, 31), 500) * np.exp(-t / 0.03) * 0.4)


def s_zap(p, seed):
    t = _tt(0.13)
    f = _sweep(1800, 140, len(t))
    sq = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR))
    sq = np.repeat(sq[::8], 8)[:len(t)]                       # sample-and-hold = bit-crushed
    gate = (np.floor(t / 0.012) % 2 == 0).astype(float) * 0.7 + 0.3
    nz = _hp(_noise(0.13, seed), 1500) * 0.4
    return (0.6 * sq + nz) * gate * np.exp(-t / 0.05)


def s_ching(p, seed):
    out = np.zeros(int(0.8 * SR))
    for i, (fc, lev) in enumerate(((2637.0, 1.0), (3520.0, 0.8))):
        t = _tt(0.7)
        idx = 3.0 * np.exp(-t / 0.08)
        x = np.sin(2 * np.pi * fc * t + idx * np.sin(2 * np.pi * fc * 1.41 * t)) * np.exp(-t / 0.18) * lev
        s = int(i * 0.075 * SR)
        out[s:s + len(x)] += x
    return out


def s_chip(p, seed):
    out = []
    for f in p["notes"]:
        t = _tt(p["each"])
        out.append(np.sign(np.sin(2 * np.pi * f * t)) * 0.5 * np.exp(-t / 0.06))
    return np.concatenate(out)


def s_chip_hit(p, seed):
    t = _tt(0.12)
    f = _sweep(260, 70, len(t))
    sq = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.5
    nz = np.repeat(_noise(0.12, seed)[::6], 6)[:len(t)] * 0.5
    return (sq + nz) * np.exp(-t / 0.04)


def s_crackle(p, seed):
    dur = p["dur"]
    r = np.random.default_rng(int(seed))
    n = int(dur * SR)
    x = np.zeros(n)
    pos = (r.random(140) ** 1.8 * n).astype(int)
    for q in pos:
        k = r.integers(1, 4)
        x[q:q + k] += (r.random() * 2 - 1) * (0.4 + r.random())
    return _hp(x, p["cutoff"]) * np.exp(-np.arange(n) / SR / (dur / 2.5))


def s_lighter(p, seed):
    t = _tt(0.4)
    wheel = _svf_bp(_noise(0.4, 71), np.full(len(t), 3500.0), 3.0) * np.exp(-t / 0.02)
    flame = _lp(_noise(0.4, 72), 700) * _env_ad(len(t), 0.25, 1.5, 4.0) * 0.8
    return wheel + flame


def s_tick(p, seed):
    f, dur = p["freq"], p["dur"]
    t = _tt(dur)
    return np.sin(2 * np.pi * f * t) * np.exp(-t / 0.006) + _lp(_noise(dur, int(f)), 300) * np.exp(-t / 0.01) * 0.6


def s_shimmer(p, seed):
    r = np.random.default_rng(int(seed))
    t = _tt(p["dur"])
    x = sum(np.sin(2 * np.pi * (3000 + 3000 * r.random()) * t + r.random() * 6)
            * (0.5 + 0.5 * np.sin(2 * np.pi * (6 + r.random() * 10) * t)) for _ in range(6))
    return x * _env_ad(len(t), 0.12, 1.0, 4.0)


def s_buzz(p, seed):
    dur = p["dur"]
    t = _tt(dur)
    motor = np.sign(np.sin(2 * np.pi * 165 * t)) * 0.5 + np.sin(2 * np.pi * 82 * t) * 0.6
    rattle = (np.sin(2 * np.pi * 24 * t) > 0.2).astype(float) * 0.7 + 0.3
    pulses = (np.sin(2 * np.pi * (3 / dur) * t) > -0.3).astype(float)
    tick = _hp(_noise(dur, 91), 2200) * 0.3 * rattle
    x = (_lp(motor, 1200) + tick) * rattle * pulses
    x[-200:] *= np.linspace(1, 0, 200)
    return x


def s_cork(p, seed):
    t = _tt(0.25)
    f = 420 * np.exp(-t / 0.01) + 130
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.03)
    ring = np.sin(2 * np.pi * 560 * t) * np.exp(-t / 0.06) * 0.35
    snap = _hp(_noise(0.25, 92), 2000) * np.exp(-t / 0.003)
    return x + ring + 0.6 * snap


def s_flutter(p, seed):
    dur = p["dur"]
    t = _tt(dur)
    puffs = (np.sin(2 * np.pi * 14 * t) > 0.3).astype(float)
    return _lp(_hp(_noise(dur, seed), 300), 1800) * puffs * _env_ad(len(t), 0.3, 1.0, 3.0)


def s_ghost(p, seed):
    dur = p["dur"]
    t = _tt(dur)
    tone = np.sin(2 * np.pi * (330 + 12 * np.sin(2 * np.pi * 5.5 * t)) * t) * 0.5
    breath = _svf_bp(_noise(dur, seed), np.full(len(t), 900.0) * (1 + 0.6 * t / dur), 1.2)
    e = np.linspace(0, 1, len(t)) ** 2.5
    e[-400:] *= np.linspace(1, 0, 400)
    return (tone + breath) * e


# kind: (sound, its numbers, level class, what it sounds like). "seed" picks the variant where a sound has noise.
KINDS = {
    "whoosh": (s_whoosh, {"dur": 0.35, "from": 400, "to": 2600, "q": 1.3, "peak": 0.5, "decay": 5.0}, "move",
               "air rushing past: a noise band sweeping from / to Hz (to < from = falling), loudest at peak (0-1)"),
    "whip": (s_whoosh, {"dur": 0.17, "from": 700, "to": 3600, "q": 1.3, "peak": 0.35, "decay": 5.0}, "whip",
             "a short swish (a camera whip, a fast slide)"),
    "riser": (s_riser, {"dur": 0.4, "from": 500, "to": 4000, "q": 2.0}, "move",
              "grows until its last sample - starts at f, lands on f + dur"),
    "air": (s_air, {"dur": 0.5}, "soft", "soft airy noise (a cursor moving, a dip)"),
    "click": (s_click, {}, "click", "a mouse button: press + release 55 ms later"),
    "key": (s_key, {}, "key", "a keyboard key, a little different for every seed"),
    "pop": (s_pop, {"dur": 0.1, "from": 420, "to": 900}, "pop", "a bubble pop: a quick pitch glide"),
    "chime": (s_chime, {"dur": 0.45, "gap": 0.06, "freqs": [1318.5, 1975.5]}, "pop",
              "two bell notes (a search, a done)"),
    "impact": (s_impact, {"dur": 0.55, "sub": 1.0}, "hit", "a slam: a falling sub kick + a noise body + a snap"),
    "thump": (s_thump, {"dur": 0.3}, "hit_small", "a small low hit"),
    "zap": (s_zap, {}, "pop", "a crushed square chirp that stutters (inverted frames, glitches)"),
    "ching": (s_ching, {}, "pop", "money: two metallic bell strikes"),
    "chip": (s_chip, {"notes": [523, 659, 784], "each": 0.05}, "pop", "8-bit square notes one after another"),
    "chip_hit": (s_chip_hit, {}, "pop", "an 8-bit hit"),
    "crackle": (s_crackle, {"dur": 0.6, "cutoff": 2500}, "soft", "sparks / fizz: tiny clicks thinning out"),
    "lighter": (s_lighter, {}, "click", "a lighter: the wheel, then the flame"),
    "tick": (s_tick, {"freq": 1800, "dur": 0.04}, "tick", "a short tuned tick (blinds, grids, stutters)"),
    "shimmer": (s_shimmer, {"dur": 0.5}, "soft", "a glittering high shimmer (a glow, a light leak)"),
    "buzz": (s_buzz, {"dur": 0.42}, "pop", "a phone vibrating on a table"),
    "cork": (s_cork, {}, "pop", "a champagne cork"),
    "flutter": (s_flutter, {"dur": 0.5}, "soft", "wings: quick soft air puffs"),
    "ghost": (s_ghost, {"dur": 0.7}, "soft", "a breathy swell with a slow vibrato tone"),
}
ALIASES = {"hit": "impact", "swish": "whip", "type": "key", "keystroke": "key", "slam": "impact", "sparks": "crackle"}
SEEDED = {"whoosh", "whip", "riser", "air", "key", "zap", "chip_hit", "crackle", "shimmer", "flutter", "ghost"}
CUE_KEYS = {"f", "kind", "what", "repeat", "if", "level", "db", "pan", "seed"}
HITS = ("impact", "thump", "click")             # a plan's flashes, strongest first


def synth(kind: str, params: dict | None = None, seed: int = 1) -> np.ndarray:
    """One sound, mono, peak 1."""
    fn, dflt, _, _ = KINDS[kind]
    x = fn({**dflt, **(params or {})}, int(seed))
    return x / (np.abs(x).max() + 1e-9)


# ------------------------------------------------------------------------------------------------ cue formulas
_FUNCS = {"len": len, "min": min, "max": max, "abs": abs, "floor": math.floor, "ceil": math.ceil, "int": int,
          "round": lambda x: math.floor(x + 0.5),
          # how many items a "a|b|c" list setting holds (empty ones left out): one cue per item of a list
          "parts": lambda s, sep="|": len([x for x in str(s).split(sep) if x.strip()])}
_BIN = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b,
        ast.Div: lambda a, b: a / b, ast.FloorDiv: lambda a, b: a // b, ast.Mod: lambda a, b: a % b,
        ast.Pow: lambda a, b: a ** b}
_CMP = {ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b, ast.Lt: lambda a, b: a < b,
        ast.LtE: lambda a, b: a <= b, ast.Gt: lambda a, b: a > b, ast.GtE: lambda a, b: a >= b}


def formula(expr, names: dict):
    """A number, or a small formula of the settings: + - * / // % **, comparisons, and / or / not, x if c else y and
    the functions in _FUNCS. Nothing else runs (no attributes, no imports)."""
    if not isinstance(expr, str):
        return expr

    def ev(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float, str, bool)):
            return n.value
        if isinstance(n, ast.Name):
            if n.id in names:
                return names[n.id]
            if n.id in ("true", "false"):
                return n.id == "true"
            raise ValueError(f"unknown name '{n.id}' (settings: {', '.join(k for k in names if k not in _FUNCS)})")
        if isinstance(n, ast.BinOp) and type(n.op) in _BIN:
            return _BIN[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp):
            v = ev(n.operand)
            return -v if isinstance(n.op, ast.USub) else +v if isinstance(n.op, ast.UAdd) else not v
        if isinstance(n, ast.BoolOp):
            vals = [ev(v) for v in n.values]
            return all(vals) if isinstance(n.op, ast.And) else any(vals)
        if isinstance(n, ast.Compare):
            left = ev(n.left)
            for op, c in zip(n.ops, n.comparators):
                right = ev(c)
                if type(op) not in _CMP or not _CMP[type(op)](left, right):
                    return False
                left = right
            return True
        if isinstance(n, ast.IfExp):
            return ev(n.body) if ev(n.test) else ev(n.orelse)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUNCS and not n.keywords:
            return _FUNCS[n.func.id](*[ev(a) for a in n.args])
        raise ValueError(f"not allowed in a cue formula: {ast.unparse(n)}")
    try:
        return ev(ast.parse(expr.strip(), mode="eval").body)
    except SyntaxError:
        raise ValueError(f"not a formula: {expr!r}") from None


def _names(c: dict) -> set:
    """The names a cue's formulas read."""
    out = set()
    for v in c.values():
        for x in (v if isinstance(v, list) else [v]):
            if isinstance(x, str):
                try:
                    out |= {n.id for n in ast.walk(ast.parse(x.strip(), mode="eval")) if isinstance(n, ast.Name)}
                except SyntaxError:
                    pass
    return out


def _seed(kind: str, f: int, i: int) -> int:
    return zlib.crc32(f"{kind}:{f}:{i}".encode()) % 100000


def resolve(raw: list, values: dict, fps: float, frames: int, source: str = "") -> list[dict]:
    """The cues as written (numbers or formulas) -> cues with numbers: {f, kind, level, db, pan [a, b], seed, params,
    what, source}. ValueError names the cue that is wrong."""
    out = []
    for k, c in enumerate(raw or []):
        where = f"{source} cue {k + 1}" + (f" ({c.get('what')})" if isinstance(c, dict) and c.get("what") else "")
        try:
            if not isinstance(c, dict) or "f" not in c or "kind" not in c:
                raise ValueError('a cue needs "f" (frame) and "kind"')
            kind = ALIASES.get(c["kind"], c["kind"])
            if kind not in KINDS:
                raise ValueError(f"unknown kind '{c['kind']}' (kinds: {', '.join(KINDS)})")
            dflt = KINDS[kind][1]
            extra = set(c) - CUE_KEYS - set(dflt)
            if extra:
                raise ValueError(f"unknown field(s) {', '.join(sorted(extra))} for a {kind} "
                                 f"(its numbers: {', '.join(dflt) or 'none'})")
            base = {**values, **_FUNCS, "fps": fps, "frames": frames}
            n = int(formula(c.get("repeat", 1), {**base, "i": 0, "n": 1}))
            for i in range(max(n, 0)):
                names = {**base, "i": i, "n": n}
                if "if" in c and not formula(c["if"], names):
                    continue
                f = int(math.floor(float(formula(c["f"], names)) + 0.5))
                pan = c.get("pan", 0)
                pan = ([float(formula(p, names)) for p in pan] if isinstance(pan, list)
                       else [float(formula(pan, names))] * 2)
                if len(pan) != 2 or not all(-1 <= p <= 1 for p in pan):
                    raise ValueError("pan: -1..1 or [from, to]")
                level = c.get("level") or KINDS[kind][2]
                if level not in LEVELS:
                    raise ValueError(f"unknown level '{level}' ({', '.join(LEVELS)})")
                more = float(formula(c.get("db", 0), names))
                if not -12 <= more <= 12:
                    raise ValueError("db: -12..12")
                params = {}
                for p in dflt:
                    if p in c:
                        v = c[p]
                        params[p] = ([float(formula(x, names)) for x in v] if isinstance(v, list)
                                     else float(formula(v, names)))
                if params.get("dur", 1) <= 0 or params.get("each", 1) <= 0:
                    raise ValueError("dur: more than 0 seconds")
                seed = int(formula(c["seed"], names)) if "seed" in c else _seed(kind, f, i)
                what = str(c.get("what", kind)) + (f" {i + 1}" if n > 1 else "")
                out.append({"f": f, "kind": kind, "level": level, "db": more, "pan": pan, "seed": seed,
                            "params": params, "what": what, "source": source,
                            "uses": sorted(_names({k: v for k, v in c.items() if k != "what"}) & set(values))})
        except (ValueError, TypeError, ZeroDivisionError, KeyError) as e:
            raise ValueError(f"{where}: {e}") from None
    return out


# ------------------------------------------------------------------------------------------------ where cues come from
def graphic_cues(folder: Path, override: dict | None = None, raw: list | None = None) -> tuple[list, float, int, dict]:
    """A graphic's cues with its current settings (override = values to try without saving): (cues, fps, frames,
    values). raw = cues from elsewhere (a cues file) instead of overlay.json's."""
    from . import overlay_settings as OS
    folder = Path(folder)
    c = OS.conf(folder)
    vals = OS.values(folder)
    if override:
        clean, bad = OS.check(OS.declared(folder), override)
        if bad:
            raise ValueError("; ".join(bad))
        unknown = set(override) - set(clean)
        if unknown:
            raise ValueError(f"{folder.name} has no setting {', '.join(sorted(unknown))}")
        vals = {**vals, **clean}
    fps, frames = float(c.get("fps") or 25), int(c.get("frames") or 0)
    cues = resolve(c.get("cues") if raw is None else raw, vals, fps, frames, c.get("name", folder.name))
    return cues, fps, frames, vals


def cues_file(path: Path, override: dict | None = None) -> tuple[list, float, int, dict]:
    """A cues file: {"graphic": <folder, relative to the file>, "cues": [...]} (the graphic's settings, fps and
    length) or {"fps": 30, "frames": 750, "values": {...}, "cues": [...]}."""
    path = Path(path)
    d = json.loads(path.read_text(encoding="utf-8"))
    if d.get("graphic"):
        g = Path(d["graphic"])
        g = g if g.is_absolute() else (path.parent / g).resolve()
        return graphic_cues(g, override, d.get("cues") or [])
    if not d.get("fps") or not d.get("frames"):
        raise ValueError(f"{path.name}: needs \"graphic\", or \"fps\" and \"frames\"")
    vals = {**(d.get("values") or {}), **(override or {})}
    fps, frames = float(d["fps"]), int(d["frames"])
    return resolve(d.get("cues"), vals, fps, frames, path.stem), fps, frames, vals


def _runs(frames: list[int]) -> list[list[int]]:
    out: list[list[int]] = []
    for f in sorted(set(frames)):
        if out and f == out[-1][-1] + 1:
            out[-1].append(f)
        else:
            out.append([f])
    return out


def _animated(v) -> bool:
    return isinstance(v, (dict, str))


def plan_cues(plan: dict, notes: list | None = None) -> list[dict]:
    """A plan's effects (its layers) + its graphics' cues + its own "cues" -> cues at the plan's fps. A graphic whose
    cues do not resolve (a formula naming a setting its index.html no longer declares, local-make-13) loses its own
    cues, with a line in `notes` - the rest of the plan keeps its sound."""
    from .compose import Curve
    fps, N = float(plan["fps"]), int(plan["frames"])
    W, H = float(plan.get("width", 1920)), float(plan.get("height", 1080))
    named = plan.get("curves") or {}
    raw: list[dict] = []
    moves: list[dict] = []
    shown: list[dict] = []                                 # the graphics' cues (already resolved)

    def add(f, kind, what, **kw):
        if 0 <= f < N:
            raw.append({"f": int(f), "kind": kind, "what": what, **kw})
    for L in plan.get("layers", []):
        t, lid = L.get("type"), L.get("id", L.get("type"))
        s, e = int(L.get("start", 0)), int(L.get("end", N - 1))
        if t == "overlay" and L.get("file"):
            folder = Path(L["file"]).parent
            if (folder / "overlay.json").exists():
                try:
                    gc, gfps, _, _ = graphic_cues(folder)
                except ValueError as ex:
                    if notes is None:
                        raise
                    notes.append(f"{lid}: its own cues skipped - {ex} (fix its overlay.json \"cues\", or [] and "
                                 "plan-level cues)")
                    continue
                inn = int(L.get("in", 0))
                for q in gc:
                    f = s + math.floor((q["f"] - inn) * fps / gfps + 0.5)
                    if s <= f <= e:
                        shown.append({**q, "f": f, "what": f"{lid}: {q['what']}"})
            continue
        fo = {int(k): float(v) for k, v in (L.get("flash_over") or {}).items()}
        for run in _runs(list(fo)):
            st = max(fo[f] for f in run)
            kind = "impact" if st >= 0.8 else "thump" if st >= 0.5 else "click"
            add(run[0], kind, f"{lid}: flash ({st:g})" if st >= 0.5 else f"{lid}: a freeze / soft flash ({st:g})")
        for run in _runs([int(v) for v in L.get("flash_white", [])]):
            add(run[0], "impact", f"{lid}: white flash")
        for run in _runs([int(v) for v in L.get("black", [])]):
            add(run[0], "thump", f"{lid}: black frame")
        if t == "clip" and float(L.get("speed", 1.0)) > 1.01 and s > 0:
            d = max(2, int(round(0.3 * fps)))
            add(s - d, "riser", f"{lid}: speeds up to {float(L['speed']):g}x (lands on f{s})", dur=d / fps)
        for j in sorted(L.get("jumps") or [])[1:]:
            if s < int(j[0]) <= e:
                add(int(j[0]), "tick", f"{lid}: stutter")
        an = L.get("anchor")
        if isinstance(an, list) and any(_animated(a) for a in an):
            add(s, "thump", f"{lid}: shake")
        for key in ("zoom", "dx", "dy"):
            if not _animated(L.get(key)) or e <= s:
                continue
            cv = Curve(L[key], named, 1.0 if key == "zoom" else 0.0)
            v = np.array([cv(f) for f in range(s, e + 1)], float)
            if key == "zoom":
                sp = np.abs(np.diff(np.log(np.maximum(v, 1e-3)))) * fps          # e-folds a second
                fast = sp >= 0.6
            else:
                sp = np.abs(np.diff(v)) / (W if key == "dx" else H) * fps      # frame sizes a second
                fast = sp >= 1.0
            for run in _runs([s + i for i in np.flatnonzero(fast)]):
                a, b = run[0], run[-1] + 1                                     # frames a..b move
                sl = slice(a - s, b - s)
                grow = float(v[b - s] - v[a - s])
                moves.append({"a": a, "b": b, "axis": "zoom" if key == "zoom" else "slide", "id": lid,
                              "speed": float(sp[sl].max()), "dir": 1 if grow > 0 else -1, "key": key})
        if t in ("solid", "clip") and lid not in ("fade_in", "fade_out") and e >= s:
            op = L.get("opacity")
            if t == "clip" and L.get("tint") and e - s <= 4:
                add(s, "zap", f"{lid}: colour split")
            elif t == "solid" and L.get("blend") in ("screen", "add"):
                add(s, "zap" if e - s <= 4 else "shimmer", f"{lid}: colour flash" if e - s <= 4 else f"{lid}: light")
            elif t == "solid" and _animated(op) and e - s <= 24:
                cv = Curve(op, named, 1.0)
                vals = [cv(f) for f in range(s, e + 1)]
                k = int(np.argmax(vals))
                if vals[k] >= 0.9 and 0 < k < len(vals) - 1:
                    add(s, "air", f"{lid}: dip", dur=(e - s + 1) / fps)
    # the moves: the two halves of a zoom-through (out, then in) or of a whip (both shots slide) are one sound
    moves.sort(key=lambda m: (m["axis"], m["a"]))
    merged: list[dict] = []
    for m in moves:
        p = merged[-1] if merged else None
        if p and p["axis"] == m["axis"] and m["a"] <= p["b"] + 1:
            if m["a"] > p["a"] and "cut" not in p:
                p["cut"] = m["a"]
            p["b"] = max(p["b"], m["b"])
            p["speed"] = max(p["speed"], m["speed"])
        else:
            merged.append(dict(m))
    for m in merged:
        n = m["b"] - m["a"] + 1
        dur = max(n / fps, 0.15)
        peak = min(max(((m.get("cut", m["a"] + n / 2)) - m["a"]) / n, 0.15), 0.85)
        if m["axis"] == "slide" and m["speed"] >= 8:
            add(m["a"], "whip", f"{m['id']}: whip ({m['speed']:.0f} frame widths/s)", dur=dur, peak=peak)
        else:
            f0, f1 = (400, 2600) if m["dir"] > 0 or m["axis"] == "slide" else (2600, 400)
            what = (f"{m['id']}: zoom {'in' if m['dir'] > 0 else 'out'}" if m["axis"] == "zoom"
                    else f"{m['id']}: slide")
            add(m["a"], "whoosh", what + (f" to the cut f{m['cut']}" if m.get("cut") else ""), dur=dur, peak=peak,
                **{"from": f0, "to": f1})
    derived = sorted(resolve(raw, {}, fps, N, plan.get("name", "plan")), key=lambda q: (q["f"], q["kind"]))
    kept: list[dict] = []
    for q in derived:
        if q["kind"] in HITS:          # flashes on several layers at once (within 3 frames) = one hit, the strongest
            k = next((k for k in reversed(kept[-6:]) if k["kind"] in HITS and q["f"] - k["f"] <= 3), None)
            if k:
                if HITS.index(q["kind"]) < HITS.index(k["kind"]):
                    k.update(kind=q["kind"], level=q["level"], seed=q["seed"])
                k["what"] = k["what"].split(" (+")[0] + f" (+{q['what']})"
                continue
        if any(k["kind"] == q["kind"] and abs(k["f"] - q["f"]) <= 1 for k in kept[-6:]):
            continue                                       # the same sound twice within a frame = once
        kept.append(q)
    out = kept + shown + resolve(plan.get("cues") or [], {}, fps, N, "plan cues")
    return sorted(out, key=lambda q: q["f"])


# ------------------------------------------------------------------------------------------------ song, levels, mix
def load_audio(path: Path, start_s: float = 0.0, length_s: float | None = None) -> np.ndarray:
    """Any audio (or a video's sound) -> stereo float64 at 48 kHz, decoded by ffmpeg; the file is only read."""
    cmd = [tool("ffmpeg"), "-v", "error", "-nostdin"]
    if start_s:
        cmd += ["-ss", f"{start_s:.6f}"]
    cmd += ["-i", str(path), "-map", "0:a:0", "-vn"]
    if length_s:
        cmd += ["-t", f"{length_s:.6f}"]
    cmd += ["-ac", "2", "-ar", str(SR), "-f", "f32le", "-"]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode:
        raise ValueError(f"could not read the sound of {Path(path).name}: {r.stderr.decode(errors='replace')[-300:]}")
    return np.frombuffer(r.stdout, np.float32).reshape(-1, 2).astype(np.float64)


def db(x: float) -> float:
    return 20 * math.log10(max(x, 1e-12))


def rms_db(x: np.ndarray) -> float:
    """RMS in dBFS; a stereo array = the mean of both channels' power (what a meter shows)."""
    return 10 * math.log10(float(np.mean(np.square(x))) + 1e-24) if x.size else -240.0


def fx_level(x: np.ndarray, a: int, b: int) -> float:
    """An effect's level in dBFS: the RMS of its loud part (a..b), but never more than SPARSE_DB under its peak - a
    sparse sound (sparks: a few sharp ticks, 29 dB peak over RMS; every other kind <= 21) reads far quieter than it
    sounds, and went up to the peak cap, 7 dB over sfx_v2. Mono or stereo (the channels' mean power)."""
    sq = np.square(x) if x.ndim == 1 else np.square(x).mean(1)
    if not sq.size:
        return -240.0
    return max(rms_db(x[a:b]), 10 * math.log10(float(sq.max()) + 1e-24) - SPARSE_DB)


def loud_part(x: np.ndarray) -> tuple[int, int]:
    """(first, last + 1) sample where the sound's 10 ms envelope is within 20 dB of its peak."""
    e = np.sqrt(np.maximum(uniform_filter1d(np.square(x), max(1, int(0.01 * SR)), mode="constant"), 0.0))
    on = np.flatnonzero(e >= e.max() * 0.1)
    return (int(on[0]), int(on[-1]) + 1) if on.size else (0, len(x))


def song_window(start: int, a: int, b: int, n_total: int) -> tuple[int, int]:
    """The song around the effect's loud part (samples start + a .. start + b): centred on it, 50 ms wider on each
    side, at least WINDOW_S long."""
    mid = start + (a + b) / 2
    half = max((b - a) / 2 + PRE_S * SR, WINDOW_S * SR / 2)
    return max(0, int(mid - half)), min(n_total, int(mid + half))


def song_level(sg: np.ndarray, start: int, a: int, b: int) -> tuple[float, tuple[int, int]]:
    """The song's level where the effect sounds = the quieter of the WINDOW_S window (song_window) and the effect's
    loud part alone (at least NEAR_S): an effect in a short quiet gap right before a loud line is levelled
    to the gap, not to the line (the 0.4 s window alone made those up to 10 dB louder than sfx_v2's)."""
    w = song_window(start, a, b, len(sg))
    mid = start + (a + b) / 2
    half = max((b - a) / 2, NEAR_S * SR / 2)
    n = max(0, int(mid - half)), min(len(sg), int(mid + half))
    lw, ln = rms_db(sg[w[0]:w[1]]), rms_db(sg[n[0]:n[1]])
    return (lw, w) if lw <= ln else (ln, n)


def limit(x: np.ndarray, ceiling_db: float = CEILING_DB, hold_s: float = 0.02) -> tuple[np.ndarray, np.ndarray]:
    """A look-ahead peak limiter: the gain is the minimum of what each sample needs over +-hold_s, smoothed by an
    average over the same span - so it is never above what any sample needs (no peak gets through) and moves over
    ~40 ms (no clicks). Returns (the limited sound, the gain per sample)."""
    c = 10 ** (ceiling_db / 20)
    need = np.minimum(1.0, c / np.maximum(np.abs(x).max(1), 1e-12))
    if need.min() >= 1.0:
        return x, need
    L = 2 * int(hold_s * SR) + 1
    g = uniform_filter1d(minimum_filter1d(need, L, mode="nearest"), L, mode="nearest")
    y = x * g[:, None]
    return np.clip(y, -c, c), g                          # the clip only removes float rounding


def build(cues: list[dict], fps: float, frames: int, song: np.ndarray | None = None, song_db: float = SONG_DB,
          ceiling_db: float = CEILING_DB, fade_s: float = FADE_S, peak_db: float = PEAK_DB,
          floor_vs_song: float | None = FLOOR_VS_SONG_DB) -> dict:
    """The effects stem, the mix and a row per cue with its measured levels. song = stereo at SR from frame 0.
    floor_vs_song: an effect never sits further under the song where it sounds (rule "song floor"; None = off)."""
    N = int(round(frames / fps * SR))
    has_song = song is not None and len(song) > 0
    sg = np.zeros((N, 2))
    if has_song:
        k = min(N, len(song))
        sg[:k] = song[:k, :2] * 10 ** (song_db / 20)
    stem = np.zeros((N, 2))
    rows, cap = [], 10 ** (peak_db / 20)
    for q in sorted(cues, key=lambda c: c["f"]):
        s = int(round(q["f"] * SR / fps))
        if not 0 <= s < N:
            rows.append({**_row_base(q, fps), "skipped": "outside the video"})
            continue
        x = synth(q["kind"], q["params"], q["seed"])[:N - s]
        a, b = loud_part(x)
        fx_db = fx_level(x, a, b) - 10 * math.log10(2)     # placed with an equal-power pan: each channel 3 dB under
        rel, floor = (v + TRIM_DB for v in LEVELS[q["level"]])
        s_db, (w0, w1) = song_level(sg, s, a, b) if has_song else (None, song_window(s, a, b, N))
        want = max(s_db + rel, floor) if has_song else floor
        want += q["db"]
        rule = "floor" if (not has_song or s_db + rel < floor) else "song"
        if has_song and floor_vs_song is not None and want < s_db + floor_vs_song:
            want, rule = s_db + floor_vs_song, "song floor"
        gain = 10 ** ((want - fx_db) / 20)
        if gain > cap:
            gain, rule = cap, "peak cap"
        p = np.linspace(q["pan"][0], q["pan"][1], len(x))
        ang = (p + 1) * np.pi / 4
        y = x * gain
        stem[s:s + len(x), 0] += y * np.cos(ang)
        stem[s:s + len(x), 1] += y * np.sin(ang)
        got = fx_db + db(gain)
        rows.append({**_row_base(q, fps), "sample": s, "song_db": None if s_db is None else round(s_db, 2),
                     "target_db": round(want, 2), "fx_db": round(got, 2), "gain_db": round(db(gain), 2),
                     "vs_song_db": None if s_db is None else round(got - s_db, 2), "rule": rule,
                     "peak_dbfs": round(db(gain * max(float(np.abs(x * np.cos(ang)).max()),
                                                      float(np.abs(x * np.sin(ang)).max()))), 2),
                     "loud": [s + a, s + b], "window": [w0, w1]})
    mix = sg + stem
    if fade_s > 0:
        k = min(N, int(fade_s * SR))
        mix[N - k:] *= (np.linspace(1, 0, k) ** 2)[:, None]
    raw_peak = float(np.abs(mix).max()) if N else 0.0
    out, g = limit(mix, ceiling_db)
    stem_peak = float(np.abs(stem).max()) if N else 0.0
    stem_out, sgain = limit(stem, ceiling_db)
    for r in rows:
        if "sample" in r:
            w = g[r["loud"][0]:r["loud"][1]]
            r["limiter_db"] = round(db(float(w.min())), 2) if w.size else 0.0
    red = g < 10 ** (-0.5 / 20)
    return {"stem": stem_out, "mix": out, "rows": rows, "N": N,
            "mix_peak_before_db": round(db(raw_peak), 2), "mix_peak_db": round(db(float(np.abs(out).max())), 2),
            "limiter_max_db": round(db(float(g.min())), 2),
            "limiter_frames": [[int(r[0] * fps / SR), int(r[-1] * fps / SR)] for r in _sample_runs(red)],
            "stem_peak_before_db": round(db(stem_peak), 2), "stem_limited_db": round(db(float(sgain.min())), 2)}


def _sample_runs(mask: np.ndarray) -> list[list[int]]:
    idx = np.flatnonzero(mask)
    if not idx.size:
        return []
    cut = np.flatnonzero(np.diff(idx) > SR // 10) + 1
    return [[int(p[0]), int(p[-1])] for p in np.split(idx, cut)]


def _row_base(q: dict, fps: float) -> dict:
    return {"f": q["f"], "tc": frame_to_tc(q["f"], fps), "kind": q["kind"], "level": q["level"], "what": q["what"],
            "pan": q["pan"], "seed": q["seed"], **({"params": q["params"]} if q["params"] else {}),
            **({"db": q["db"]} if q["db"] else {})}


def write_wav(path: Path, x: np.ndarray) -> None:
    import soundfile as sf
    sf.write(str(path), np.clip(x, -1, 1), SR, subtype="PCM_24")


def cue_line(q: dict, fps: float) -> str:
    pan = q["pan"]
    pn = f"{pan[0]:+.2f}" if pan[0] == pan[1] else f"{pan[0]:+.2f}>{pan[1]:+.2f}"
    return f"  f{q['f']:<5d} ({frame_to_tc(q['f'], fps)})  {q['kind']:9s} {q['level']:9s} pan {pn:11s} {q['what']}"


def level_line(r: dict) -> str:
    if r.get("skipped"):
        return f"  f{r['f']:<5d} ({r['tc']})  {r['kind']:9s} skipped: {r['skipped']}  {r['what']}"
    song = f"song {r['song_db']:6.1f}" if r["song_db"] is not None else "no song   "
    vs = f"({r['vs_song_db']:+5.1f} vs song)" if r["vs_song_db"] is not None else "               "
    lim = f"  limiter {r['limiter_db']:.1f} dB" if r.get("limiter_db", 0) < -0.5 else ""
    return (f"  f{r['f']:<5d} ({r['tc']})  {r['kind']:9s} {song}  fx {r['fx_db']:6.1f} {vs}  peak "
            f"{r['peak_dbfs']:5.1f} dBFS  {r['rule']:8s}{lim}  {r['what']}")


# ------------------------------------------------------------------------------------------------ the check
def _synth_song(frames: int, fps: float) -> tuple[np.ndarray, int]:
    """A test song: a quiet tone bed (about -30 dBFS) for the first half, then a loud bed with a click on every
    half second (about -6 dBFS, its peaks over 0 dBFS: the limiter has work) - stereo, seeded."""
    N = int(round(frames / fps * SR))
    t = np.arange(N) / SR
    r = np.random.default_rng(7)
    bed = 0.5 * np.sin(2 * np.pi * 110 * t) + 0.3 * np.sin(2 * np.pi * 220 * t + 1.0)
    bed = bed + _lp(r.standard_normal(N), 3000) * 0.3
    half = N // 2
    lvl = np.where(np.arange(N) < half, 10 ** (-30 / 20), 10 ** (-6 / 20)) / 0.65
    y = bed * lvl
    clicks = np.zeros(N)
    for c in range(half, N, SR // 2):
        k = min(N - c, int(0.03 * SR))
        clicks[c:c + k] += np.sin(2 * np.pi * 1000 * np.arange(k) / SR) * np.exp(-np.arange(k) / SR / 0.006) * 0.75
    y = y + clicks
    return np.stack([y, np.roll(y, 24) * 0.97], axis=1), half


def selfcheck(verbose: bool = True) -> dict:
    """Known answers, no video: a synthetic song (quiet, then loud with clicks) and cues at known frames.
    PASS = every onset within 1 frame of its cue, every level within +-1 dB of its target (against the song window
    measured again from the files' samples), no sample over the ceiling, two runs identical, a setting that moves the
    timing moves the cues, a plan's effects become cues on their frames."""
    t0 = time.time()
    fps, frames = 30.0, 300
    lines, ok = [], True

    def check(cond, msg):
        nonlocal ok
        ok &= bool(cond)
        lines.append(("PASS " if cond else "FAIL ") + msg)
    song, half = _synth_song(frames, fps)
    raw = [{"f": f, "kind": k} for f, k in ((10, "key"), (30, "click"), (50, "pop"), (70, "whoosh"), (95, "tick"),
                                            (115, "impact"), (165, "key"), (185, "whoosh"), (210, "pop"),
                                            (230, "thump"), (250, "whip"), (270, "riser"))]
    cues = resolve(raw, {}, fps, frames, "selfcheck")
    res = build(cues, fps, frames, song)
    res2 = build(resolve(raw, {}, fps, frames, "selfcheck"), fps, frames, song)
    same = (hashlib.sha256(np.round(res["mix"] * 2 ** 23).astype(np.int32).tobytes()).digest()
            == hashlib.sha256(np.round(res2["mix"] * 2 ** 23).astype(np.int32).tobytes()).digest()
            and np.array_equal(res["stem"], res2["stem"]))
    sg = song * 10 ** (SONG_DB / 20)
    stem = res["stem"]
    worst_ms, worst_db = 0.0, 0.0
    for q, r in zip(sorted(cues, key=lambda c: c["f"]), res["rows"]):
        x = synth(q["kind"], q["params"], q["seed"])
        s = int(round(q["f"] * SR / fps))
        # onset: where the sound sits in the stem (cross-correlation over +-2 frames)
        m = int(2 * SR / fps)
        lo, hi = max(0, s - m), min(len(stem), s + m + len(x))
        seg = stem[lo:hi].sum(1)
        cc = np.correlate(seg, x, "valid")
        lag = lo + int(np.argmax(np.abs(cc))) - s
        ms = lag / SR * 1000
        worst_ms = max(worst_ms, abs(ms))
        # level: measured again from the stem's samples against the song's
        sx = stem[s:s + len(x)]
        a, b = loud_part(sx.sum(1))
        fx = fx_level(sx, a, b)
        w0, w1 = song_level(sg, s, a, b)[1]
        target = r["target_db"] if r["rule"] != "peak cap" else r["fx_db"]
        err = fx - target
        worst_db = max(worst_db, abs(err))
        check(abs(lag) <= SR / fps and abs(err) <= 1.0,
              f"f{q['f']} ({frame_to_tc(q['f'], fps)}) {q['kind']:7s} onset {ms:+.2f} ms, level {fx:6.1f} dBFS = "
              f"song {rms_db(sg[w0:w1]):6.1f} {fx - rms_db(sg[w0:w1]):+5.1f} (target {target:6.1f}, {r['rule']}, "
              f"off by {err:+.2f} dB)")
    ceiling = 10 ** (CEILING_DB / 20)
    check(np.abs(res["mix"]).max() <= ceiling + 1e-12 and np.abs(res["stem"]).max() <= ceiling + 1e-12,
          f"ceiling: mix peak {res['mix_peak_db']:.2f} dBFS (before the limiter {res['mix_peak_before_db']:.2f}, "
          f"limiter at most {res['limiter_max_db']:.2f} dB), ceiling {CEILING_DB:g} dBFS")
    check(res["mix_peak_before_db"] > CEILING_DB, "the test reaches the limiter (else the ceiling check means nothing)")
    check(same, "two runs give the same samples")
    # a setting moves the timing: one key per typed character
    rule = [{"f": "10 + round(i * min(1, 20 / n))", "repeat": "len(text)", "kind": "key", "seed": "200 + i",
             "what": "key"}, {"f": "at + 2", "kind": "pop", "if": "badge"}]
    a1 = [q["f"] for q in resolve(rule, {"text": "abcd", "at": 40, "badge": True}, fps, frames)]
    a2 = [q["f"] for q in resolve(rule, {"text": "a" * 40, "at": 60, "badge": False}, fps, frames)]
    check(a1 == [10, 11, 12, 13, 42] and len(a2) == 40 and a2[:4] == [10, 11, 11, 12] and a2[-1] == 30,
          f"settings move the cues: 'abcd' -> {a1}; 40 characters -> {len(a2)} keys f{a2[0]}..f{a2[-1]}, "
          f"the pop gone when badge is off")
    try:
        resolve([{"f": "__import__('os')", "kind": "pop"}], {}, fps, frames)
        check(False, "a formula cannot run code")
    except ValueError:
        check(True, "a formula cannot run code")
    # a plan's effects -> cues (the quick draft's own layers)
    from . import draft as DR
    shots = [(0, 59), (60, 119), (120, 179), (180, 239), (240, 299)]
    picks = [{"sid": "A", "in": 0}] * 5
    at_cut = {1: {"type": "zoom_transition"}, 2: {"type": "whip_pan"}, 3: {"type": "flash_white"},
              4: {"type": "dip_black"}}
    at_shot = {0: {"type": "flash", "beat": 30}, 2: {"type": "speed_ramp"}, 4: {"type": "flash_color", "beat": 270}}
    layers, placed = DR.build_layers(shots, picks, at_cut, at_shot, [], 1080, 1920, fps, np.random.default_rng(3))
    pc = plan_cues({"fps": fps, "frames": frames, "width": 1080, "height": 1920, "layers": layers})
    got = {(q["kind"], q["f"]) for q in pc}
    want = {("thump", 30): "flash f30", ("whoosh", 54): "zoom-through f54-f66 (cut f60)",
            ("whip", 117): "whip f117-f122 (cut f120)", ("impact", 180): "white flash f180",
            ("air", 232): "dip f232-f248", ("riser", 141): "speed ramp at f150", ("zap", 270): "colour flash f270"}
    miss = [w for k, w in want.items() if not any(g[0] == k[0] and abs(g[1] - k[1]) <= 1 for g in got)]
    extra = [f"{q['kind']} f{q['f']}" for q in pc
             if not any(q["kind"] == k[0] and abs(q["f"] - k[1]) <= 1 for k in want)]
    check(not miss and not extra, f"a plan's effects -> {len(pc)} cues: "
          + ", ".join(f"{q['kind']} f{q['f']} ({frame_to_tc(q['f'], fps)})" for q in pc)
          + (f"; missing {miss}" if miss else "") + (f"; not expected {extra}" if extra else ""))
    secs = time.time() - t0
    lines.append(f"{'PASS' if ok else 'FAIL'}: onsets within {worst_ms:.2f} ms (1 frame = {1000 / fps:.1f} ms), levels "
                 f"within {worst_db:.2f} dB, {len(cues)} cues on {frames / fps:g} s, {secs:.1f} s")
    if verbose:
        print("\n".join(lines))
    return {"ok": ok, "passed": ok, "lines": lines, "seconds": round(secs, 2)}


def rel(p: Path) -> str:
    try:
        return Path(p).resolve().relative_to(LAB.resolve()).as_posix().replace("/", "\\")
    except ValueError:
        return str(p)


def safe_out(folder: Path) -> Path:
    """Outputs go into a project's build folder or the lab's .app scratch - never next to sources."""
    f = Path(folder).resolve()
    projects, scratch = (LAB / "projects").resolve(), (LAB / ".app").resolve()
    ok = f == scratch or scratch in f.parents or (
        projects in f.parents and "build" in f.relative_to(projects).parts[1:2])
    if not ok:
        raise PermissionError(f"sound effects go into projects\\<name>\\build\\... (not {f})")
    return f


def last_song() -> tuple[str, float, str] | None:
    """0.5.3: the song of the newest video with a sound report (projects\\*\\build\\sfx\\*_sfx.json) - (path, start
    s, project): Generate's "the song from last time" and the brief's guess when a request names none."""
    best = None
    for rep in (LAB / "projects").glob("*/build/sfx/*_sfx.json"):
        try:
            s = json.loads(rep.read_text(encoding="utf-8")).get("song") or {}
        except (OSError, ValueError):
            continue
        if s.get("path") and Path(s["path"]).exists() and (best is None or rep.stat().st_mtime > best[0]):
            best = (rep.stat().st_mtime, s["path"], float(s.get("start_s") or 0), rep.parents[2].name)
    return best[1:] if best else None


def stem_name(text: str) -> str:
    return re.sub(r"[^\w.-]+", "_", text).strip("_") or "sfx"
