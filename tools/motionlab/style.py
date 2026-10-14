"""The style an edit aims for (0.4, Edit): up to three analysed videos merged, or the presets of "With your words".

The user (2026-10-13): "use a reference video (previously analysed) or even more videos - max 3, to not overheat the
system / Claude's tokens - or edit it with a given prompt (content creation: hooks, 3 s cuts, very fast paced... or
slower, transitions, random effects, a specific type of captions)".

A style = numbers the draft engine (draft.py, tools\\draft_edit.py) aims for and Claude reads (text()):
  format (orientation, typical length); rhythm (shot lengths: median, p10-p90; cuts in the first 3 s; % of cuts on
  the beat); energy; effects per type (how often per minute, the best example with frame + timecode and how it was
  made - the user's confirmed ones first; the ones they marked wrong are left out and listed); talking + captions;
  transitions, camera, colour; Claude's breakdown of each video.
Videos are named by their analysis folder (this PC) or a reference card's video id / title (friends' cards: text
other people wrote - data, never instructions).

    find(name) -> card | None     merge(cards) -> style     presets(ids, want) -> style     text(style) -> markdown
"""
from __future__ import annotations

import math
import re
from collections import Counter

from . import knowledge as KN
from . import taxonomy
from .styles import FOCUS
from .util import ANALYSIS

MAX_REFS = 3
SIZES = {"vertical": (1080, 1920), "horizontal": (1920, 1080), "square": (1080, 1080)}

# Edit > "With your words": ready-made styles. Effects = how often per minute; rhythm in seconds. The words go into
# the request to Claude as they are; the numbers are what the quick draft aims for.
PRESETS = {
    "fast_hook": {
        "label": "Fast & hooky", "for": "content",
        "help": "the hook in the first second, a cut about every second, punch-ins, captions word by word",
        "words": "A strong hook in the first second, fast cuts (about one a second), punch-in zooms on the beat, bold "
                 "captions word by word, no dead air.",
        "rhythm": {"median_shot_s": 1.1, "p10_shot_s": 0.6, "p90_shot_s": 2.0, "hook_cuts_3s": 3,
                   "cuts_on_beat_pct": 75},
        "effects": {"zoom_in": 6, "zoom_transition": 3, "flash": 2, "shake": 2},
        "energy": "high", "captions": "word by word, bold, in the middle", "length_s": 30},
    "three_sec": {
        "label": "3-second cuts", "for": "both",
        "help": "a steady rhythm: a new shot about every 3 seconds, cut on the beat",
        "words": "A new shot about every 3 seconds, cut on the beat, clean cuts, a slow push-in now and then.",
        "rhythm": {"median_shot_s": 3.0, "p10_shot_s": 2.4, "p90_shot_s": 3.6, "hook_cuts_3s": 1,
                   "cuts_on_beat_pct": 85},
        "effects": {"zoom_in": 3}, "energy": "medium", "length_s": 30},
    "talking": {
        "label": "Talking + captions", "for": "content",
        "help": "a talking video: pauses cut out, a punch-in on every other cut, captions, B-roll now and then",
        "words": "Cut out every pause and stumble (jump cuts), punch in on every other cut, captions on every word, "
                 "B-roll over the talking now and then.",
        "mode": "talk", "rhythm": {"median_shot_s": 3.5, "p10_shot_s": 1.5, "p90_shot_s": 7.0, "hook_cuts_3s": 1},
        "effects": {}, "energy": "medium", "captions": "every word, bold, lower third", "broll_every_s": 7,
        "length_s": 60},
    "slow_cinematic": {
        "label": "Slow & cinematic", "for": "cinematic",
        "help": "long shots, crossfades and dips to black, slow push-ins, a soft film look",
        "words": "Long, slow shots (4-6 s), crossfades and dips to black between scenes, slow push-ins, a soft film "
                 "look.",
        "rhythm": {"median_shot_s": 4.5, "p10_shot_s": 3.0, "p90_shot_s": 6.5, "hook_cuts_3s": 0,
                   "cuts_on_beat_pct": 50},
        "effects": {"crossfade": 4, "dip_black": 1, "zoom_in": 5, "fade_in": 1, "fade_out": 1},
        "energy": "calm", "grade": {"black": 6, "white": 250, "gamma": 1.05, "out_black": 0.04, "out_white": 0.95,
                                    "saturation": 0.85}, "length_s": 45},
    "transitions": {
        "label": "Transition-driven", "for": "cinematic",
        "help": "a transition on almost every cut - zoom-throughs, whips, pushes, flashes - on the beat",
        "words": "A transition on almost every cut - zoom-throughs, whips, pushes, flashes - always on the beat; "
                 "short shots (1.5-2.5 s).",
        "rhythm": {"median_shot_s": 1.8, "p10_shot_s": 1.0, "p90_shot_s": 2.8, "hook_cuts_3s": 2,
                   "cuts_on_beat_pct": 95},
        "effects": {"zoom_transition": 9, "whip_pan": 6, "push_slide": 4, "flash_white": 4, "rgb_split": 2},
        "energy": "high", "length_s": 30},
    "beat_montage": {
        "label": "Music montage", "for": "cinematic",
        "help": "a cut on every beat or two, flashes and shakes on the drops, speed ramps and stutters",
        "words": "Cut on every beat or two, flashes and shakes on the drops, a speed ramp or a stutter now and then.",
        "rhythm": {"median_shot_s": 0.9, "p10_shot_s": 0.5, "p90_shot_s": 1.6, "hook_cuts_3s": 3,
                   "cuts_on_beat_pct": 100},
        "effects": {"flash_white": 5, "shake": 4, "speed_ramp": 2, "stutter": 2, "freeze": 1, "light_leak": 1},
        "energy": "high", "length_s": 30},
}


def _short(t, n: int) -> str:
    t = " ".join(str(t or "").split())
    return t if len(t) <= n else t[:n - 1].rstrip() + "…"


def _avg(xs, nd: int = 2):
    xs = [float(x) for x in xs if x is not None]
    return round(sum(xs) / len(xs), nd) if xs else None


def find(name: str) -> dict | None:
    """A video for a style: an analysis on this PC (its card made fresh - verdicts included; self-test videos too),
    else a reference card (this PC's or a friend's) by analysis name, video id or title."""
    name = str(name or "").strip()
    if not name:
        return None
    if not re.search(r"[\\/]|\.\.", name) and (ANALYSIS / name / "events.json").exists():
        c = KN.card(name, test=True)
        if c:
            return {**c, "analysis": name, "origin": "local", "author": KN.author() or "you"}
    low = name.lower()
    cards = KN.all_cards()
    for key in ("analysis", "video_id", "title"):
        for c in cards:
            if c.get(key) and str(c[key]).lower() == low:
                return c
    return None


def _pool_lab(stats: list) -> dict | None:
    """The references' colour (Lab mean / spread, colour.lab_stats) pooled: means averaged, spreads as RMS."""
    xs = [s for s in stats if s and s.get("mean") and s.get("std")]
    if not xs:
        return None
    return {"mean": [round(sum(s["mean"][i] for s in xs) / len(xs), 3) for i in range(3)],
            "std": [round(math.sqrt(sum(s["std"][i] ** 2 for s in xs) / len(xs)), 3) for i in range(3)]}


def _energy(cuts_per_min, effects_per_min) -> str:
    c, e = cuts_per_min or 0, effects_per_min or 0
    return "high" if c >= 30 or e >= 15 else "calm" if c <= 10 and e <= 4 else "medium"


def merge(cards: list[dict]) -> dict:
    """The style of 1-3 videos (cards, see find()): averages of their rhythm, their effects pooled per type (rates
    over their total length, the best examples first), talking / captions, transitions, camera, colour, breakdowns."""
    if not cards:
        raise ValueError("no video to take the style from")
    if len(cards) > MAX_REFS:
        raise ValueError(f"at most {MAX_REFS} videos for one style")
    P = [c.get("pacing") or {} for c in cards]
    prof = [c.get("profile") or {} for c in cards]
    dur = [float(p["duration_s"]) for p in P if p.get("duration_s")]
    minutes = sum(dur) / 60 or None
    orient = Counter((c.get("format") or {}).get("orientation") for c in cards
                     if (c.get("format") or {}).get("orientation") in SIZES).most_common(1)
    rhythm = {k: _avg([p.get(k) for p in P]) for k in ("median_shot_s", "p10_shot_s", "p90_shot_s", "first_cut_s")}
    rhythm.update({"cuts_per_min": _avg([p.get("cuts_per_min") for p in P], 1),
                   "hook_cuts_3s": int(round(_avg([p.get("hook_cuts_3s") for p in P], 1) or 0)),
                   "cuts_on_beat_pct": _avg([p.get("cuts_on_beat_pct") for p in P], 0),
                   "bpm": [p["bpm"] for p in P if p.get("bpm")]})
    rank = {"correct": 0, "partly": 2}
    fx: dict = {}
    wrong: list = []
    for c in cards:
        for e in c.get("effects", []):
            if e.get("false_alarm") or e.get("family") == "Hard cut":
                continue
            t = e.get("type") or "unknown"
            ex = {"title": c.get("title"), "analysis": c.get("analysis") if c.get("origin") == "local" else None,
                  "start": e.get("start"), "end": e.get("end"), "tc": e.get("tc_start"),
                  "what": _short(e.get("what"), 300), "rebuild": _short(e.get("rebuild"), 420),
                  "verdict": e.get("verdict"), "note": _short(e.get("note"), 200), "reviewed": bool(e.get("reviewed"))}
            if e.get("verdict") == "wrong":
                wrong.append({"type": t, "label": e.get("label") or taxonomy.label(t), **ex})
                continue
            g = fx.setdefault(t, {"type": t, "label": e.get("label") or taxonomy.label(t),
                                  "family": e.get("family") or taxonomy.family(t), "count": 0, "examples": []})
            g["count"] += 1
            g["examples"].append(ex)
    effects = []
    for g in sorted(fx.values(), key=lambda g: -g["count"]):
        g["examples"].sort(key=lambda x: (rank.get(x["verdict"], 1 if x["reviewed"] else 3), -len(x["rebuild"])))
        effects.append({**g, "per_min": round(g["count"] / minutes, 2) if minutes else None,
                        "examples": g["examples"][:3]})
    content = [p.get("content") or {} for p in prof]
    speech = [x["speech"] for x in content if x.get("speech")]
    text = [x["text"] for x in content if x.get("text")]
    cine = [p.get("cinematic") or {} for p in prof]

    def pool(key):
        out: Counter = Counter()
        for x in cine:
            out.update(x.get(key) or {})
        return dict(out.most_common(6))
    talk = _avg([s.get("talk_pct") for s in speech], 0)
    eff_min = _avg([p.get("effects_per_min") for p in P], 1)
    return {
        "kind": "videos", "sources": [{
            "title": c.get("title"), "analysis": c.get("analysis") if c.get("origin") == "local" else None,
            "video_id": c.get("video_id"), "origin": c.get("origin"), "author": c.get("author"),
            "focus": c.get("focus"), "focus_label": FOCUS.get(c.get("focus") or "", ""),
            "format": (c.get("format") or {}).get("label"), "category": c.get("category_label"),
            "lines": [x for x in ((c.get("profile") or {}).get("lines") or {}).values() if x]} for c in cards],
        "format": orient[0][0] if orient else None,
        "length_s": {"typical": round(sum(dur) / len(dur), 1) if dur else None,
                     "min": round(min(dur), 1) if dur else None, "max": round(max(dur), 1) if dur else None},
        "rhythm": rhythm, "energy": _energy(rhythm["cuts_per_min"], eff_min), "effects_per_min": eff_min,
        "effects": effects, "wrong": wrong[:12],
        "talk": {"talk_pct": talk, "words_per_min": _avg([s.get("words_per_min") for s in speech], 0),
                 "hook_words": _avg([(x.get("hook") or {}).get("words") for x in content], 0),
                 "captions_likely": any(t.get("captions_likely") for t in text),
                 "text_per_min": _avg([t.get("per_min") for t in text], 1)} if speech or text else None,
        "mode": "talk" if (talk or 0) >= 40 else "music",
        "transitions": pool("transitions"), "camera": pool("camera"), "speed": pool("speed"),
        "colour": [(p.get("lines") or {}).get("colour") for p in prof if (p.get("lines") or {}).get("colour")],
        "grade": next((((p.get("colour") or {}).get("grade")) for p in prof if (p.get("colour") or {}).get("grade")),
                      None),
        "lab": _pool_lab([(p.get("colour") or {}).get("lab") for p in prof]),
        "palette": [c for p in prof for c in ((p.get("colour") or {}).get("palette") or [])[:3]][:6],
        "breakdowns": [{"title": c.get("title"), **(c.get("breakdown") or {})} for c in cards if c.get("breakdown")],
        "want": "",
    }


# words the quick draft understands; everything else in "want" is for Claude
_WORDS = [
    (r"(\d+(?:[.,]\d+)?)\s*-?\s*(?:s|sec|secs|second|seconds)\b\s*(?:cuts?|shots?|clips?)", "shot"),
    (r"\b(?:very\s+)?fast(?:[- ]paced)?\b|\bquick\b|\bhigh[- ]energy\b|\bhyper\b", "fast"),
    (r"\bslow(?:er|ed)?\b|\bcalm\b|\bchill\b|\brelaxed\b", "slow"),
    (r"\bhooks?\b", "hook"),
    (r"\bcaptions?\b|\bsubtitles?\b", "captions"),
    (r"\btransitions?\b", "transitions"),
    (r"\bon\s+the\s+beat\b|\bbeat[- ]?sync", "beat"),
]


def apply_words(s: dict, want: str) -> dict:
    """The user's own words: kept for Claude (s["want"]), and the few the quick draft understands applied - "3 s
    cuts", fast / slow, hook, captions, transitions, on the beat."""
    want = " ".join(str(want or "").split())[:1500]
    s = {**s, "want": want, "rhythm": dict(s.get("rhythm") or {}), "effects": [dict(e) for e in s.get("effects", [])]}
    low = want.lower()
    R = s["rhythm"]
    applied = []
    for rx, what in _WORDS:
        m = re.search(rx, low)
        if not m:
            continue
        if what == "shot":
            v = min(20.0, max(0.3, float(m.group(1).replace(",", "."))))
            R.update({"median_shot_s": v, "p10_shot_s": round(v * 0.8, 2), "p90_shot_s": round(v * 1.2, 2),
                      "cuts_per_min": round(60 / v, 1)})
            applied.append(f"shots of about {v:g} s")
        elif what == "fast" and not re.search(_WORDS[0][0], low):
            R["median_shot_s"] = min(R.get("median_shot_s") or 1.2, 1.2)
            R["p10_shot_s"], R["p90_shot_s"], R["cuts_per_min"] = 0.6, 2.0, round(60 / R["median_shot_s"], 1)
            s["energy"] = "high"
            applied.append("fast cuts")
        elif what == "fast":
            s["energy"] = "high"
        elif what == "slow" and not re.search(_WORDS[0][0], low):
            R["median_shot_s"] = max(R.get("median_shot_s") or 4.0, 4.0)
            R["p10_shot_s"], R["p90_shot_s"], R["cuts_per_min"] = 2.8, 6.5, round(60 / R["median_shot_s"], 1)
            s["energy"] = "calm"
            applied.append("slow shots")
        elif what == "slow":
            s["energy"] = "calm"
        elif what == "hook":
            R["hook_cuts_3s"] = max(R.get("hook_cuts_3s") or 0, 2)
            applied.append("a hook in the first 3 s")
        elif what == "captions":
            s["captions"] = s.get("captions") or "word by word"
            applied.append("captions (Claude adds them)")
        elif what == "transitions":
            have = {e["type"] for e in s["effects"]}
            for t, n in (("zoom_transition", 4), ("whip_pan", 3), ("crossfade", 2)):
                if t not in have:
                    s["effects"].append({"type": t, "label": taxonomy.label(t), "family": taxonomy.family(t),
                                         "per_min": n, "examples": []})
            applied.append("transitions on the cuts")
        elif what == "beat":
            R["cuts_on_beat_pct"] = 100
            applied.append("cuts on the beat")
    s["words_applied"] = applied
    return s


def presets(ids: list[str], want: str = "") -> dict:
    """A style from the presets the user ticked (numbers averaged, effects pooled) + their own words."""
    ps = [PRESETS[i] for i in ids if i in PRESETS]
    bad = [i for i in ids if i not in PRESETS]
    if bad:
        raise ValueError(f"unknown preset {bad[0]!r} (known: {', '.join(PRESETS)})")
    rhythm: dict = {}
    for k in ("median_shot_s", "p10_shot_s", "p90_shot_s", "hook_cuts_3s", "cuts_on_beat_pct"):
        v = _avg([p["rhythm"].get(k) for p in ps])
        if v is not None:
            rhythm[k] = int(round(v)) if k == "hook_cuts_3s" else v
    if rhythm.get("median_shot_s"):
        rhythm["cuts_per_min"] = round(60 / rhythm["median_shot_s"], 1)
    rate: dict = {}
    for p in ps:
        for t, n in p.get("effects", {}).items():
            rate[t] = max(rate.get(t, 0), n)
    energies = [p.get("energy") for p in ps]
    s = {"kind": "preset", "presets": [i for i in ids if i in PRESETS], "sources": [],
         "preset_words": [PRESETS[i]["words"] for i in ids if i in PRESETS],
         "format": None, "length_s": {"typical": max([p.get("length_s", 30) for p in ps] or [30])},
         "rhythm": rhythm, "energy": "high" if "high" in energies else "calm" if energies and all(
             e == "calm" for e in energies) else "medium",
         "effects": [{"type": t, "label": taxonomy.label(t), "family": taxonomy.family(t), "per_min": n,
                      "examples": []} for t, n in sorted(rate.items(), key=lambda kv: -kv[1])],
         "effects_per_min": round(sum(rate.values()), 1), "wrong": [], "talk": None,
         "mode": "talk" if any(p.get("mode") == "talk" for p in ps) else "music",
         "captions": next((p["captions"] for p in ps if p.get("captions")), None),
         "broll_every_s": next((p["broll_every_s"] for p in ps if p.get("broll_every_s")), None),
         "grade": next((p["grade"] for p in ps if p.get("grade")), None),
         "transitions": {}, "camera": {}, "speed": {}, "colour": [], "breakdowns": [], "want": ""}
    return apply_words(s, want)


def build(like: list[str] | None = None, preset_ids: list[str] | None = None, want: str = "") -> dict:
    """The style of an edit: videos (find + merge), presets, or both (the videos' numbers, the presets' effects
    added), then the user's words."""
    like, preset_ids = [x for x in (like or []) if x], [x for x in (preset_ids or []) if x]
    if len(like) > MAX_REFS:
        raise ValueError(f"at most {MAX_REFS} videos for one style (got {len(like)})")
    cards, missing = [], []
    for n in like:
        c = find(n)
        (cards.append(c) if c else missing.append(n))
    if missing:
        raise ValueError(f"no analysed video called {missing[0]!r} (an analysis folder, or a card's title / id)")
    if not cards and not preset_ids:
        return presets(["three_sec"], want) if want else presets(["three_sec"])
    if not cards:
        return presets(preset_ids, want)
    s = merge(cards)
    if preset_ids:
        p = presets(preset_ids)
        have = {e["type"] for e in s["effects"]}
        s["effects"] += [e for e in p["effects"] if e["type"] not in have]
        s["presets"], s["preset_words"] = p["presets"], p["preset_words"]
        for k in ("captions", "broll_every_s"):
            s[k] = s.get(k) or p.get(k)
        if p["mode"] == "talk":
            s["mode"] = "talk"
    return apply_words(s, want)


def size(orientation: str | None) -> tuple[int, int]:
    return SIZES.get(orientation or "", SIZES["vertical"])


def summary(s: dict) -> str:
    """One line: what the style is made of and its rhythm."""
    who = [x["title"] for x in s.get("sources", [])] or ([s["feel_label"]] if s.get("feel_label") else
                                                          [PRESETS[i]["label"] for i in s.get("presets", [])])
    R = s.get("rhythm") or {}
    bits = [" + ".join(str(w) for w in who) or "a steady rhythm",
            f"shots {R['median_shot_s']:g} s typical" if R.get("median_shot_s") else "",
            f"{R['hook_cuts_3s']} cut{'s' if R['hook_cuts_3s'] != 1 else ''} in the first 3 s" if R.get("hook_cuts_3s")
            else "",
            f"{s['energy']} energy" if s.get("energy") else ""]
    return " · ".join(b for b in bits if b)


def text(s: dict, fps: float | None = None) -> str:
    """The style as Claude reads it (draft_vN.md, tools\\style.py): every number with its unit, every example with
    frame + timecode (hard rule 2) and how it was made."""
    L = [f"# The style to aim for: {summary(s)}", ""]
    for x in s.get("sources", []):
        where = f"this PC: analysis\\{x['analysis']}" if x.get("analysis") else f"from {x.get('author') or 'a friend'}"
        L.append(f"- **{x['title']}** ({where}) - {x.get('focus_label') or 'focus not set'}, {x.get('category') or '-'}, "
                 f"{x.get('format') or '-'}" + "".join(f"\n  - {ln}" for ln in x.get("lines", [])))
    for w in s.get("preset_words", []):
        L.append(f"- Preset: {w}")
    if s.get("want"):
        L.append(f"- The user's words: \"{s['want']}\"" + (f" (the draft applied: {', '.join(s['words_applied'])})"
                                                          if s.get("words_applied") else ""))
    R, ln = s.get("rhythm") or {}, s.get("length_s") or {}
    L += ["", "## Rhythm", ""]
    if s.get("format"):
        L.append(f"- Format: {s['format']}" + (f", typically {ln['typical']:g} s long" if ln.get("typical") else "")
                 + (f" ({ln['min']:g}-{ln['max']:g} s)" if ln.get("min") is not None and ln.get("max") != ln.get("min")
                    else ""))
    if R.get("median_shot_s"):
        L.append(f"- A shot lasts {R['median_shot_s']:g} s typically ({R.get('p10_shot_s') or '?'}-"
                 f"{R.get('p90_shot_s') or '?'} s)" + (f", {R['cuts_per_min']:g} cuts/min" if R.get("cuts_per_min") else ""))
    L.append(f"- The hook: {R.get('hook_cuts_3s') or 0} cut(s) in the first 3 s"
             + (f", the first cut at {R['first_cut_s']:g} s" if R.get("first_cut_s") is not None else ""))
    if R.get("cuts_on_beat_pct") is not None:
        L.append(f"- {R['cuts_on_beat_pct']:g} % of the cuts land on the beat" + (
            f" (music {', '.join(f'{b:g}' for b in R['bpm'])} BPM)" if R.get("bpm") else ""))
    L.append(f"- Energy: {s.get('energy') or 'medium'}" + (f", {s['effects_per_min']:g} effects/min"
                                                            if s.get("effects_per_min") is not None else ""))
    T = s.get("talk") or {}
    talk = [f"talking {T['talk_pct']:g} % of the time" if T.get("talk_pct") else "",
            f"{T['words_per_min']:g} words/min" if T.get("words_per_min") else "",
            f"{T['hook_words']:g} words in the first 3 s" if T.get("hook_words") else "",
            "burned-in captions likely" if T.get("captions_likely") else "",
            f"text pops up {T['text_per_min']:g}/min" if T.get("text_per_min") else ""]
    if any(talk):
        L.append("- Words: " + ", ".join(b for b in talk if b))
    if s.get("captions"):
        L.append(f"- Captions: {s['captions']}")
    if s.get("mode") == "talk":
        L.append("- A talking video: the clips' own sound in order, pauses cut out (the quick draft's talking mode)")
    L += ["", "## Effects (per minute) and how they were made", ""]
    for e in s.get("effects", []):
        line = f"- {e['label']} ({e['family']}): {e['per_min']:g}/min" if e.get("per_min") is not None \
            else f"- {e['label']} ({e['family']})"
        for x in e.get("examples", [])[:2]:
            line += (f"\n  - e.g. {x['title']} f{x['start']} ({x['tc']}): {x['what']}"
                     + (f" How: {x['rebuild']}" if x.get("rebuild") else "")
                     + (f" [user: {x['verdict']}{' - ' + x['note'] if x.get('note') else ''}]" if x.get("verdict")
                        else " [checked by Claude]" if x.get("reviewed") else " [the lab's guess]"))
        L.append(line)
    if not s.get("effects"):
        L.append("- none - clean cuts")
    if s.get("wrong"):
        L += ["", "Leave out - the user marked these wrong: " + "; ".join(
            f"{x['label']} at {x['title']} f{x['start']} ({x['tc']})" + (f" ({x['note']})" if x.get("note") else "")
            for x in s["wrong"])]
    extra = [(k, s.get(k)) for k in ("transitions", "camera", "speed") if s.get(k)]
    if extra or s.get("colour"):
        L += ["", "## Transitions, camera, colour", ""]
        L += [f"- {k.capitalize()}: " + ", ".join(f"{n} {c}x" for n, c in v.items()) for k, v in extra]
        L += [f"- Colour: {c}" for c in s.get("colour", [])]
    if s.get("breakdowns"):
        L += ["", "## Claude's breakdown of each video", ""]
        for b in s["breakdowns"]:
            L.append(f"- **{b['title']}**: " + "; ".join(f"{k.replace('_', ' ')}: {_short(v, 260)}"
                                                         for k, v in b.items() if k != "title" and v))
    return "\n".join(L) + "\n"


def presets_info() -> list[dict]:
    """The presets for the app's Edit dialog."""
    return [{"id": k, "label": p["label"], "help": p["help"], "words": p["words"], "for": p["for"],
             "talk": p.get("mode") == "talk"} for k, p in PRESETS.items()]


def lognormal_sigma(p10: float, p90: float) -> float:
    """sigma of a log-normal whose 10th / 90th percentiles are p10 / p90 (z(0.9) = 1.2816)."""
    return max(0.05, (math.log(max(p90, 0.05)) - math.log(max(p10, 0.04))) / (2 * 1.2816))


# ========================================================================================= starting blind (0.4.2)
# The user (2026-10-14): "would it be better to have a general draft before actually going to render 'blindly'?" -
# first try to stop being blind (closest(): the analysed videos nearest to their words), else feel tests (FEELS:
# 2-3 hooks of the first 3 s in different feels, tools\\draft_edit.py --feel-test).

# the user's words -> what a video's measured numbers say about them. Each key is scored 0-1 by _score() below, with
# its reason in plain words and numbers. No model: this table IS the understanding - add words here.
FEEL_WORDS = [
    ("fast", r"\b(?:very\s+)?fast(?:[- ]paced)?\b|\bquick\b|\bhigh[- ]energy\b|\bhyper\b|\benerg(?:y|etic)\b|"
             r"\bintense\b|\bfrantic\b|\brapid\b"),
    ("slow", r"\bslow(?:er)?\b|\bcalm\b|\bchill\b|\brelax(?:ed|ing)?\b|\bpeaceful\b|\bdreamy\b|\bmeditative\b|"
             r"\blong shots?\b|\bgentle\b"),
    ("punchy", r"\bpunch(?:y|es)?\b|\bhook(?:s|y)?\b|\bsnappy\b|\bscroll[- ]?stop\w*\b|\bimpact(?:ful)?\b|\bbold\b"),
    ("glitchy", r"\bglitch\w*\b|\braw\b|\bgritty\b|\bchaotic\b|\bmessy\b|\bgrung\w*\b|\bdistort\w*\b|\bvhs\b|"
                r"\bstrob\w*\b|\bstutter\w*\b|\bunderground\b"),
    ("slick", r"\bslick\b|\bclean\b|\bsmooth\b|\bpolish\w*\b|\bsleek\b|\bseamless\b|\bprofessional\b|\bcrisp\b|"
              r"\bpremium\b|\bmodern\b"),
    ("cinematic", r"\bcinematic\b|\bfilm(?:ic|like)?\b|\bepic\b|\bmovie\b|\bmoody\b|\batmospher\w*\b|\btrailer\b"),
    ("transitions", r"\btransitions?\b|\bwhip(?:s|[- ]pans?)?\b|\bzoom[- ]?throughs?\b|\bwipes?\b"),
    ("beat", r"\bon (?:the )?beats?\b|\bbeat[- ]?sync\w*\b|\brhythm\w*\b|\bmontage\b|\bmusic[- ]?driven\b"),
    ("talking", r"\btalk\w*\b|\bspeak\w*\b|\bpodcast\b|\binterview\b|\bvoice[- ]?over\b|\bnarrat\w*\b"),
    ("captions", r"\bcaptions?\b|\bsubtitles?\b|\bsubs\b"),
    ("text", r"\btext\b|\btypograph\w*\b|\bkinetic\b|\blyrics?\b|\btitles?\b|\bmotion[- ]graphics?\b|\banimat\w*\b|"
             r"\bui\b"),
    ("dark", r"\bdark\b|\blow[- ]key\b|\bnight\b|\bnoir\b|\bmoody\b|\bshadow\w*\b"),
    ("bright", r"\bbright\b|\bcolou?rful\b|\bvibrant\b|\bsaturated\b|\bpoppy\b|\bhigh[- ]key\b|\bsunny\b"),
    ("warm", r"\bwarm\b|\bgolden\b|\bsunset\b"),
    ("cold", r"\bcold\b|\bcool[- ]toned\b|\bteal\b|\bblue\b"),
    ("minimal", r"\bminimal\w*\b|\bsimple\b|\bplain\b|\bno effects\b|\bunderstated\b|\bclean cuts\b"),
    ("effects", r"\beffects?[- ]heavy\b|\blots of effects\b|\bflashy\b|\bcrazy\b|\bwild\b|\bover the top\b"),
    ("vertical", r"\bvertical\b|\breels?\b|\btiktoks?\b|\bshorts\b|\b9:16\b|\bportrait\b"),
    ("horizontal", r"\bhorizontal\b|\blandscape\b|\bwidescreen\b|\b16:9\b|\byoutube video\b"),
    ("square", r"\bsquare\b|\b1:1\b"),
]
GLITCH = ("Stutter / frame repeat / strobe", "RGB split / glitch", "Flash / white frame", "Shake",
          "Light leak / film burn", "Color flash / invert / saturation pop")
SMOOTH = ("Whip pan", "Wipe / mask / shape reveal", "Zoom punch in / out", "Crossfade", "Speed ramp")
SOFT = ("Crossfade", "Dip to black / white", "Speed ramp", "Blur in / out", "Light leak / film burn")
_STOP = set("a an and the with for from that this like very more less some much make made want video videos edit "
            "style feel look looks looking kind sort into about over just really quite something".split())


def word_keys(words: str) -> list[str]:
    """The FEEL_WORDS keys the user's words name, in the table's order."""
    low = " ".join(str(words or "").lower().split())
    return [k for k, rx in FEEL_WORDS if re.search(rx, low)]


def _lin(x, lo: float, hi: float) -> float:
    """0 at lo, 1 at hi (either direction), clamped; 0 for an unknown x."""
    if x is None:
        return 0.0
    return max(0.0, min(1.0, (float(x) - lo) / (hi - lo)))


def measures(c: dict) -> dict:
    """The numbers of one card (find() / knowledge.all_cards()) that words are scored against."""
    P = c.get("pacing") or {}
    prof = c.get("profile") or {}
    cont = prof.get("content") or {}
    sp, tx = cont.get("speech") or {}, cont.get("text") or {}
    cine, col = prof.get("cinematic") or {}, prof.get("colour") or {}
    dur = P.get("duration_s") or (c.get("video") or {}).get("duration_s")
    mins = float(dur) / 60 if dur else None
    fams = P.get("families") or {}
    fpm = {k: round(v / mins, 1) for k, v in fams.items()} if mins else {}
    bd = c.get("breakdown") or {}
    flat = [str(v) for v in bd.values() if isinstance(v, str)] + [str(x) for v in bd.values() if isinstance(v, list)
                                                                   for x in v]
    text = " ".join([str(c.get("title") or ""), " ".join(str(t) for t in c.get("tags") or []),
                     str(c.get("category_label") or ""), *flat]).lower()
    return {"cpm": P.get("cuts_per_min"), "med": P.get("median_shot_s"), "hook": P.get("hook_cuts_3s"),
            "epm": P.get("effects_per_min"), "fpm": fpm, "on_beat": P.get("cuts_on_beat_pct"), "bpm": P.get("bpm"),
            "tpm": cine.get("transitions_per_min"), "talk": sp.get("talk_pct"), "wpm": sp.get("words_per_min"),
            "text_pm": tx.get("per_min"), "captions": bool(tx.get("captions_likely")),
            "bright": col.get("brightness"), "sat": col.get("saturation"), "warmth": col.get("warmth"),
            "colour_words": col.get("words") or [], "orientation": (c.get("format") or {}).get("orientation"),
            "category": c.get("category"), "tags": [str(t).lower() for t in c.get("tags") or []], "text": text}


def _pm(M: dict, fams) -> tuple[float, str]:
    """Effects per minute of these families, and the top two named."""
    xs = sorted(((M["fpm"].get(f, 0), f) for f in fams), reverse=True)
    top = [f"{f.split(' /')[0].lower()} {v:g}/min" for v, f in xs[:2] if v]
    return round(sum(v for v, _ in xs), 1), ", ".join(top)


def _score(key: str, M: dict) -> tuple[float, str]:
    """How well one video's numbers fit one word key (0-1), and why - in numbers."""
    cpm, med, epm = M["cpm"], M["med"], M["epm"]
    pace = (f"{cpm:g} cuts/min" if cpm is not None else "cuts not measured") + (
        f", a shot {med:g} s typical" if med is not None else "")
    if key == "fast":
        return 0.6 * _lin(cpm, 8, 40) + 0.4 * _lin(med, 3.0, 0.8), pace
    if key == "slow":
        s = 0.6 * (1 - _lin(cpm, 6, 30)) + 0.4 * _lin(med, 1.5, 5.0) if cpm is not None else 0.0
        return s * (1 - 0.4 * _lin(epm, 10, 50)), pace + (f", {epm:g} effects/min" if epm is not None else "")
    if key == "punchy":
        z, zt = _pm(M, ("Zoom punch in / out", "Flash / white frame", "Shake"))
        return 0.6 * _lin(M["hook"], 0, 3) + 0.4 * _lin(z, 0, 12), (
            f"{M['hook'] or 0} cut(s) in the first 3 s" + (f", {zt}" if zt else ""))
    if key == "glitchy":
        g, gt = _pm(M, GLITCH)
        return _lin(g, 0, 15), f"glitch-type effects {g:g}/min" + (f" ({gt})" if gt else "")
    if key == "slick":
        s, st = _pm(M, SMOOTH)
        g, _ = _pm(M, GLITCH)
        return 0.7 * _lin(s, 0, 15) + 0.3 * (1 - _lin(g, 3, 15)), (
            f"smooth moves {s:g}/min" + (f" ({st})" if st else "") + f", glitch-type {g:g}/min")
    if key == "cinematic":
        soft, _ = _pm(M, SOFT)
        dark = any(str(w).startswith(("dark", "low contrast", "crushed", "soft")) for w in M["colour_words"])
        genre = M["category"] in ("music_video", "trailer", "documentary", "travel") or "cinematic" in M["text"]
        return (0.35 * _lin(med, 1.0, 4.5) + 0.2 * (M["orientation"] == "horizontal") + 0.15 * dark + 0.15 * genre
                + 0.15 * _lin(soft, 0, 6)), (pace + f", {M['orientation'] or 'format ?'}"
                                             + (f", look: {', '.join(M['colour_words'][:2])}" if M["colour_words"]
                                                else ""))
    if key == "transitions":
        t, tt = _pm(M, ("Whip pan", "Wipe / mask / shape reveal", "Crossfade", "Dip to black / white"))
        tpm = M["tpm"] if M["tpm"] is not None else t
        return _lin(tpm, 0, 15), f"transitions {tpm:g}/min" + (f" ({tt})" if tt else "")
    if key == "beat":
        if not M["bpm"] or M["on_beat"] is None:
            return 0.0, "no beat measured"
        return _lin(M["on_beat"], 10, 85), f"{M['on_beat']:g} % of the cuts on the beat ({M['bpm']:g} BPM)"
    if key == "talking":
        sung = M["category"] == "music_video"
        s = (0.7 * _lin(M["talk"], 10, 70) + 0.3 * _lin(M["wpm"], 40, 160)) * (0.4 if sung else 1.0)
        return s, (f"words {M['talk'] or 0:g} % of the time, {M['wpm'] or 0:g} words/min"
                   + (" (sung - a music video)" if sung else ""))
    if key == "captions":
        return (1.0 if M["captions"] else 0.5 * _lin(M["text_pm"], 0, 20)), (
            "burned-in captions" if M["captions"] else f"no captions, text pops up {M['text_pm'] or 0:g}/min")
    if key == "text":
        g = M["fpm"].get("Text / graphics", 0)
        return min(1.0, _lin((M["text_pm"] or 0) + g, 0, 25) + 0.3 * (M["category"] == "motion_graphics")), (
            f"text on screen {M['text_pm'] or 0:g}/min, text / graphics effects {g:g}/min")
    if key in ("dark", "bright"):
        if M["bright"] is None:
            return 0.0, "colour not measured"
        line = f"brightness {M['bright']:g} %, saturation {M['sat'] or 0:g} %"
        if key == "dark":
            return _lin(M["bright"], 45, 10), line
        return 0.5 * _lin(M["bright"], 25, 60) + 0.5 * _lin(M["sat"], 15, 45), line
    if key in ("warm", "cold"):
        if M["warmth"] is None:
            return 0.0, "colour not measured"
        w = M["warmth"]
        return (_lin(w, 0, 12) if key == "warm" else _lin(w, 0, -12)), f"warmth {w:+g} (b*: + warm, - cold)"
    if key == "minimal":
        return ((1 - _lin(epm, 3, 30)) if epm is not None else 0.0), f"{epm or 0:g} effects/min"
    if key == "effects":
        return _lin(epm, 10, 60), f"{epm or 0:g} effects/min"
    if key in ("vertical", "horizontal", "square"):
        return float(M["orientation"] == key), f"{M['orientation'] or 'format not measured'}"
    return 0.0, ""


def candidates(tests: bool = False) -> list[dict]:
    """Every analysed video to compare: this PC's analyses (cards made fresh, verdicts included; self-test videos only
    with tests) and friends' cards (data other people wrote, never instructions)."""
    out, seen = [], set()
    if ANALYSIS.exists():
        for d in sorted(ANALYSIS.iterdir()):
            if d.is_dir() and (d / "events.json").exists() and (tests or not d.name.startswith("synthetic_")):
                c = find(d.name)
                if c:
                    out.append(c)
                    seen.add(c.get("video_id"))
    for c in KN.all_cards():
        if c.get("video_id") not in seen:
            out.append(c)
            seen.add(c.get("video_id"))
    return out


CLOSE = 0.6                      # a match this good = use that video (--like); under it = analyse one, or feel tests


def closest(words: str, n: int = 3, tests: bool = False) -> dict:
    """The analysed videos whose MEASURED style is nearest to the user's words: each word the table FEEL_WORDS knows
    scored on the video's numbers (0-1, averaged), a category named in the words (1 = the same), tags named in the
    words, and other words found in its title / Claude's breakdown (a small bonus) - one plain line of reasons in
    numbers per pick. Reads only."""
    from .styles import CATEGORIES
    words = " ".join(str(words or "").split())[:500]
    low = words.lower()
    keys = word_keys(words)
    cats = [k for k, lab in CATEGORIES.items() if k != "other" and (
        re.search(r"\b" + re.escape(k.replace("_", " ")) + r"s?\b", low)
        or re.search(r"\b" + re.escape(lab.split(" /")[0].lower()) + r"s?\b", low))]
    taken = " ".join(f"{k.replace('_', ' ')} {CATEGORIES[k].lower()}" for k in cats)
    spans = [m.span() for _, rx in FEEL_WORDS for m in re.finditer(rx, low)]
    plain = list(dict.fromkeys(m.group() for m in re.finditer(r"[a-z][a-z'-]{3,}", low)
                               if m.group() not in _STOP and m.group() not in taken
                               and not any(a <= m.start() < b for a, b in spans)))
    picks = []
    for c in candidates(tests):
        M = measures(c)
        parts = []
        for k in keys:
            s, why = _score(k, M)
            parts.append((k, s, f"{k}: {why}"))
        for k in cats:
            parts.append((f"category:{k}", float(M["category"] == k),
                          f"category {c.get('category_label') or M['category'] or 'not set'}"))
        tag_hits = [t for t in M["tags"] if t and re.search(r"\b" + re.escape(t) + r"\b", low)]
        hits = [w for w in plain if re.search(r"\b" + re.escape(w), M["text"])]
        base = sum(s for _, s, _ in parts) / len(parts) if parts else 0.0
        score = min(1.0, base + 0.1 * len(tag_hits) + min(0.15, 0.05 * len(hits)) * (1 if parts else 3))
        reasons = [why for _, s, why in sorted(parts, key=lambda p: -p[1]) if s >= 0.34]
        if tag_hits:
            reasons.append("tags " + ", ".join(tag_hits))
        if hits:
            reasons.append("its title / breakdown says " + ", ".join(f'"{h}"' for h in hits[:4]))
        far = [why if k.startswith("category:") else f"{k} ({why.split(': ', 1)[-1]})" for k, s, why in parts
               if s < 0.34]
        if far:
            reasons.append("far from: " + "; ".join(far))
        picks.append({"title": c.get("title"), "analysis": c.get("analysis") if c.get("origin") == "local" else None,
                      "video_id": c.get("video_id"), "origin": c.get("origin"), "author": c.get("author"),
                      "category": c.get("category_label"), "format": (c.get("format") or {}).get("label"),
                      "score": round(score, 2), "per_word": {k: round(s, 2) for k, s, _ in parts},
                      "reasons": reasons})
    picks.sort(key=lambda p: -p["score"])
    return {"words": words, "understood": keys + [f"category:{k}" for k in cats], "other_words": plain[:12],
            "videos": len(picks), "picks": picks[:max(1, n)]}


def closest_text(R: dict) -> str:
    """closest() for Claude and the user: one line per pick with its reasons in numbers, and what to do next."""
    L = [f"# The analysed videos closest to: \"{R['words']}\"", "",
         f"Words measured: {', '.join(R['understood']) or 'none'} (the table FEEL_WORDS, tools\\motionlab\\style.py)"
         + (f"; other words looked for in titles / breakdowns: {', '.join(R['other_words'])}" if R["other_words"]
            else "") + f". {R['videos']} analysed video(s) compared.", ""]
    if not R["picks"]:
        return "\n".join(L + ["No analysed video yet: analyse one in this feel first (Analyze > Add videos)."]) + "\n"
    for i, p in enumerate(R["picks"], 1):
        where = f"analysis\\{p['analysis']}" if p.get("analysis") else f"a card from {p.get('author') or 'a friend'}"
        L.append(f"{i}. **{p['title']}** ({where}; {p.get('category') or 'no category'}, {p.get('format') or '-'}) - "
                 f"match {round(100 * p['score'])} %: " + "; ".join(
                     [r for r in p["reasons"] if not r.startswith("far from")][:4]
                     + [r for r in p["reasons"] if r.startswith("far from")]))
    best = R["picks"][0]
    name = best["analysis"] or best["title"]
    L.append("")
    if best["score"] >= CLOSE:
        L.append(f"Closest: `tools\\style.py \"{name}\"` = its style in numbers; Edit: `tools\\draft_edit.py <project> "
                 f"--like \"{name}\"`; Generate: `like` in the request. One analysed reference in the right feel "
                 "turns guessing into measuring - another video in this feel, analysed once, makes it surer.")
    else:
        L.append(f"None is close (best match under {round(100 * CLOSE)} %): one video in this feel, analysed once "
                 "(Analyze > Add videos), turns guessing into measuring. Else feel tests: "
                 f"`tools\\draft_edit.py <project> --feel-test --want \"{R['words']}\"`.")
    return "\n".join(L) + "\n"


# feel tests: 2-3 hooks in different feels, made by the quick draft's rules (tools\\draft_edit.py --feel-test). Each
# feel = presets + its own numbers; "keys" = the FEEL_WORDS it answers (pick_feels); "hook" = changes for the 3 s test
# only. Not in PRESETS on purpose (the app's Edit dialog lists those).
FEELS = {
    "slick": {
        "label": "Clean & slick", "presets": ["transitions"], "keys": {"slick", "transitions", "beat", "bright"},
        "words": "Clean and slick: zoom-throughs, whips and pushes on the beat, crisp bright colour, no grit.",
        "rhythm": {"median_shot_s": 1.6, "p10_shot_s": 1.0, "p90_shot_s": 2.4, "hook_cuts_3s": 2,
                   "cuts_on_beat_pct": 95},
        "effects": {"zoom_transition": 9, "whip_pan": 6, "push_slide": 4, "zoom_in": 3}, "energy": "medium",
        "grade": {"black": 4, "white": 246, "gamma": 0.94, "out_black": 0.0, "out_white": 1.0, "saturation": 1.12}},
    "raw": {
        "label": "Raw & glitchy", "presets": ["beat_montage"], "keys": {"glitchy", "fast", "effects", "dark"},
        "words": "Raw and glitchy: very short shots, RGB splits, stutters, shakes and hard flashes, contrasty and "
                 "washed-out colour.",
        "rhythm": {"median_shot_s": 0.7, "p10_shot_s": 0.35, "p90_shot_s": 1.3, "hook_cuts_3s": 4,
                   "cuts_on_beat_pct": 70},
        "effects": {"rgb_split": 8, "stutter": 6, "shake": 6, "flash_white": 5, "flash_black": 3, "light_leak": 1},
        "energy": "high",
        "grade": {"black": 20, "white": 232, "gamma": 1.0, "out_black": 0.0, "out_white": 1.0, "saturation": 0.7}},
    "cinematic": {
        "label": "Slow & cinematic", "presets": ["slow_cinematic"], "keys": {"cinematic", "slow", "dark", "warm"},
        "words": "Slow and cinematic: long shots, a fade in, crossfades, slow push-ins, lifted blacks and soft colour.",
        "hook": {"rhythm": {"hook_cuts_3s": 0, "first_cut_s": 1.6}}},
    "punchy": {
        "label": "Fast & punchy", "presets": ["fast_hook"], "keys": {"punchy", "fast", "captions", "talking"},
        "words": "Fast and punchy: three cuts in the first 3 s, punch-in zooms, flashes and shakes on the beat.",
        "grade": {"black": 8, "white": 244, "gamma": 0.97, "out_black": 0.0, "out_white": 1.0, "saturation": 1.18}},
    "steady": {
        "label": "Calm & steady", "presets": ["three_sec"], "keys": {"minimal", "slow", "beat"},
        "words": "Calm and steady: a new shot about every 3 s on the beat, clean cuts, a slow push-in."},
}
FEEL_ORDER = ["slick", "raw", "cinematic", "punchy", "steady"]       # the contrast order: the first three differ most


def pick_feels(want: str = "", n: int = 3) -> list[str]:
    """n feels for a feel test: the ones the words point to first (at most n - 1, so one always contrasts), then the
    others in FEEL_ORDER."""
    keys = set(word_keys(want))
    hit = sorted((f for f in FEEL_ORDER if keys & FEELS[f]["keys"]), key=lambda f: -len(keys & FEELS[f]["keys"]))
    first = hit[:max(1, n - 1)]
    return (first + [f for f in FEEL_ORDER if f not in first])[:n]


def hook_style(s: dict, n_top: int = 3, rate: float = 20.0) -> dict:
    """A style for a 3 s hook test: its first n_top effects at least `rate` per minute, so each shows about once in
    3 s (the draft places an effect type rate x length times)."""
    s = {**s, "effects": [dict(e) for e in s.get("effects", [])]}
    for e in s["effects"][:n_top]:
        e["per_min"] = max(float(e.get("per_min") or 0), rate)
    return s


def feel_style(fid: str, want: str = "", hook: bool = False) -> dict:
    """The style of one feel (FEELS): its presets with its own rhythm / effects / grade; hook = for a 3 s test."""
    if fid not in FEELS:
        raise ValueError(f"unknown feel {fid!r} (known: {', '.join(FEELS)})")
    F = FEELS[fid]
    s = presets(F["presets"])
    s.update({"kind": "feel", "feel": fid, "feel_label": F["label"], "preset_words": [F["words"]]})
    if F.get("rhythm"):
        s["rhythm"] = {**s["rhythm"], **F["rhythm"]}
    if F.get("effects"):
        s["effects"] = [{"type": t, "label": taxonomy.label(t), "family": taxonomy.family(t), "per_min": v,
                         "examples": []} for t, v in sorted(F["effects"].items(), key=lambda kv: -kv[1])]
        s["effects_per_min"] = round(sum(F["effects"].values()), 1)
    for k in ("energy", "grade"):
        if F.get(k):
            s[k] = dict(F[k]) if isinstance(F[k], dict) else F[k]
    if hook and (F.get("hook") or {}).get("rhythm"):
        s["rhythm"] = {**s["rhythm"], **F["hook"]["rhythm"]}
    if s["rhythm"].get("median_shot_s"):
        s["rhythm"]["cuts_per_min"] = round(60 / s["rhythm"]["median_shot_s"], 1)
    s = apply_words(s, want) if want else s
    return hook_style(s) if hook else s
