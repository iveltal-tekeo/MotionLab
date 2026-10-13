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
    who = [x["title"] for x in s.get("sources", [])] or [PRESETS[i]["label"] for i in s.get("presets", [])]
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
