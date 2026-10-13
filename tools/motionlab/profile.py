"""What an analysed video is like, in numbers (0.4) - per focus, the way the user asked to analyse it:

- content creation: the hook (first 3 s: cuts, words, text on screen), the talking (words per minute, how much of the
  video is talked), on-screen text / captions (how often text is visible, how often it changes);
- cinematic: the signature effects, the transitions, camera moves, speed effects (and the colour look, colour.py);
- both: everything.

Made only from the lab's own files (events.json, metrics.csv / cache, content\\transcript.json) - no model, cached per
file change. The analysis page's Overview, the cards in Claude's memory and the edit's style (style.py: up to three
videos merged) read it. Numbers, never the video or other people's words: the first spoken words stay on this PC.
"""
from __future__ import annotations

import csv
import threading
from pathlib import Path

import numpy as np

from . import taxonomy
from .knowledge import meta, pacing
from .styles import FOCUS, norm_focus
from .util import ANALYSIS, load_config, read_json

HOOK_S = 3.0
# effects that happen on a cut (the event spans a shot change) count as transitions - not the stepped / strobe kind
NOT_TRANSITION = {"strobe", "stutter", "frame_repeat", "hard_cut", "jump_cut"}
CAMERA = {"zoom_in", "zoom_out", "zoom_transition", "whip_pan", "spin", "shake"}
SPEED = {"speed_ramp", "freeze", "stutter", "frame_repeat", "strobe"}
_CACHE: dict = {}
_LOCK = threading.Lock()


def _mtime(p: Path):
    try:
        return p.stat().st_mtime_ns
    except OSError:
        return None


def _text_score(d: Path, n: int) -> np.ndarray | None:
    """The per-frame text-like area (signals: text_score) from the cache, else from metrics.csv (a pruned cache)."""
    try:
        z = np.load(d / "cache" / "metrics.npz")
        if "text_score" in z.files:
            return np.nan_to_num(np.asarray(z["text_score"], float))[:n]
    except (OSError, ValueError):
        pass
    try:
        with open(d / "metrics.csv", newline="", encoding="utf-8") as f:
            r = csv.reader(f)
            head = next(r)
            i = head.index("text_score")
            vals = []
            for row in r:
                try:
                    vals.append(float(row[i]) if row[i] not in ("", "nan") else 0.0)
                except (IndexError, ValueError):
                    vals.append(0.0)
        return np.asarray(vals[:n], float)
    except (OSError, ValueError, StopIteration):
        return None


def _runs(mask: np.ndarray, min_len: int) -> list[tuple[int, int]]:
    out, a = [], None
    for i, v in enumerate(list(mask) + [False]):
        if v and a is None:
            a = i
        elif not v and a is not None:
            if i - a >= min_len:
                out.append((a, i - 1))
            a = None
    return out


def _nwords(text: str) -> int:
    """Spoken words: tokens with a letter or a digit (a lone "-" or "..." in a caption is no word)."""
    return sum(1 for w in str(text).split() if any(ch.isalnum() for ch in w))


def _content(ev: dict, d: Path, fps: float, n: int, cfg: dict) -> dict:
    hook_f = int(round(HOOK_S * fps))
    tr = read_json(d / "content" / "transcript.json") if (d / "content" / "transcript.json").exists() else None
    out: dict = {"hook": {}, "speech": None, "text": None}
    cuts = [c["frame"] for c in ev.get("hard_cuts", [])]
    evs = [e for e in ev.get("events", []) if not (e.get("final") or {}).get("false_alarm")]
    out["hook"] = {"cuts": sum(1 for c in cuts if c < hook_f),
                   "effects": sum(1 for e in evs if e["start"] < hook_f),
                   "first_cut_s": round(min(cuts) / fps, 2) if cuts else None}
    if tr and tr.get("lines"):
        lines = tr["lines"]
        talk = np.zeros(n, bool)
        for ln in lines:
            talk[max(0, int(ln["start"])):min(n, int(ln["end"]) + 1)] = True
        words = sum(_nwords(ln["text"]) for ln in lines)
        hook_words = 0
        for ln in lines:
            if ln.get("words"):
                hook_words += sum(1 for w in ln["words"] if int(w.get("f", 0)) < hook_f and _nwords(w.get("w", "")))
            elif ln["start"] < hook_f:                             # no word timings: the share of the line inside 3 s
                span = max(1, ln["end"] - ln["start"] + 1)
                hook_words += round(_nwords(ln["text"]) * min(1.0, (hook_f - ln["start"]) / span))
        talked = float(talk.mean()) if n else 0.0
        out["speech"] = {"words": words, "lines": len(lines),
                         "words_per_min": round(words / (n / fps / 60.0), 1) if n else None,
                         "talk_pct": round(100 * talked, 1),
                         "talk_words_per_min": round(words / (talk.sum() / fps / 60.0), 1) if talk.sum() else None,
                         "source": tr.get("source"), "kind": tr.get("kind"), "lang": tr.get("lang")}
        out["hook"]["words"] = hook_words
        first = next((ln for ln in lines if ln["start"] < hook_f * 2), None)
        out["hook"]["first_line_frame"] = int(first["start"]) if first else None
    # text that APPEARS (the lab's text / graphics events - confirmed or renamed by Claude's check) is the reliable
    # count; the share of frames with text-like shapes is a rough extra (signs and textures count too)
    mins = n / fps / 60.0 if n else 0.0
    tev = sorted((e for e in evs if (e.get("final") or {}).get("type", e.get("type")) == "text"), key=lambda e: e["start"])
    ts = _text_score(d, n)
    if tev or ts is not None:
        out["text"] = {"appearances": len(tev), "per_min": round(len(tev) / mins, 1) if mins else None,
                       "avg_on_s": round(float(np.mean([(e["end"] - e["start"] + 1) / fps for e in tev])), 2) if tev else None,
                       "first_s": round(tev[0]["start"] / fps, 2) if tev else None, "visible_pct": None}
        if ts is not None and len(ts):
            thr = float(cfg.get("text", {}).get("score_min", 0.012))
            vis = ts >= thr
            runs = _runs(vis, int(cfg.get("text", {}).get("min_frames", 6)))
            on = np.zeros(len(ts), bool)
            for a, b in runs:
                on[a:b + 1] = True
            out["text"]["visible_pct"] = round(100 * float(on.mean()), 1)
        out["hook"]["text_on_screen"] = any(e["start"] < hook_f for e in tev)
        sp = out["speech"]
        # burned-in captions: someone talks, and text pops up every few seconds (Claude's check names it for sure)
        out["text"]["captions_likely"] = bool(sp and sp["talk_pct"] >= 30 and (out["text"]["per_min"] or 0) >= 6)
    return out


def _cinematic(ev: dict, fps: float, n: int) -> dict:
    fam: dict[str, int] = {}
    trans: dict[str, int] = {}
    camera: dict[str, int] = {}
    speed: dict[str, int] = {}
    for e in ev.get("events", []):
        fin = e.get("final") or {}
        if fin.get("false_alarm"):
            continue
        t = fin.get("type", e.get("type"))
        f = taxonomy.family(t)
        if f == "Hard cut":
            continue
        fam[f] = fam.get(f, 0) + 1
        lab = taxonomy.label(t)
        if e.get("cuts") and t not in NOT_TRANSITION:
            trans[lab] = trans.get(lab, 0) + 1
        if t in CAMERA:
            camera[lab] = camera.get(lab, 0) + 1
        if t in SPEED:
            speed[lab] = speed.get(lab, 0) + 1
    mins = n / fps / 60.0 if n else 0
    order = sorted(fam.items(), key=lambda kv: (-kv[1], kv[0]))
    return {"families": dict(order), "signature": [f for f, _ in order[:3]],
            "transitions": dict(sorted(trans.items(), key=lambda kv: -kv[1])),
            "transitions_per_min": round(sum(trans.values()) / mins, 1) if mins else None,
            "camera": camera, "speed": speed,
            "effects": sum(fam.values()), "effects_per_min": round(sum(fam.values()) / mins, 1) if mins else None}


def content_line(c: dict) -> str:
    """One line for a card: the hook, the talking, the text on screen."""
    if not c:
        return ""
    h, sp, tx = c.get("hook") or {}, c.get("speech"), c.get("text")
    hook = [f"{h.get('cuts', 0)} cut{'s' if h.get('cuts') != 1 else ''}"]
    if h.get("words"):
        hook.append(f"{h['words']} words")
    if h.get("text_on_screen"):
        hook.append("text")
    bits = [f"hook (3 s): {', '.join(hook)}"]
    if sp:
        bits.append(f"{sp['words_per_min']:g} words/min, talking {sp['talk_pct']:g} %")
    if tx and tx.get("appearances"):
        bits.append(f"text pops up {tx['appearances']}x ({tx['per_min']:g}/min)" + (" - captions" if tx.get("captions_likely") else ""))
    return " · ".join(bits)


def cinematic_line(c: dict) -> str:
    if not c:
        return ""
    bits = []
    if c.get("signature"):
        bits.append("signature: " + ", ".join(s.split(" / ")[0].lower() for s in c["signature"]))
    if c.get("transitions"):
        bits.append(f"{sum(c['transitions'].values())} transitions")
    if c.get("effects_per_min") is not None:
        bits.append(f"{c['effects_per_min']:g} effects/min")
    return " · ".join(bits)


def profile(name: str, focus: str | None = None) -> dict | None:
    """The profile of one analysis (cached until one of its files changes). focus: the meta.json one if not given."""
    d = ANALYSIS / name
    evp = d / "events.json"
    if not evp.exists():
        return None
    sig = (_mtime(evp), _mtime(d / "content" / "transcript.json"), _mtime(d / "metrics.csv"),
           _mtime(d / "cache" / "metrics.npz"), _mtime(d / "colour" / "colour.json"), _mtime(d / "meta.json"))
    with _LOCK:
        hit = _CACHE.get(name)
        if hit and hit[0] == sig and (focus is None or hit[1]["focus"] == focus):
            return hit[1]
    ev = read_json(evp)
    v = ev.get("video") or {}
    fps = float(v.get("fps") or 25)
    n = int(v.get("frames") or 0)
    cfg = load_config()
    f = norm_focus(focus) or norm_focus(meta(name, ev).get("focus")) or norm_focus(ev.get("focus"))
    content = _content(ev, d, fps, n, cfg)
    cine = _cinematic(ev, fps, n)
    colour = read_json(d / "colour" / "colour.json") if (d / "colour" / "colour.json").exists() else None
    out = {"schema": 1, "name": name, "focus": f, "focus_label": FOCUS.get(f or "", "not set"),
           "duration_s": round(n / fps, 2) if n else v.get("duration_s"), "fps": fps, "frames": n,
           "pacing": pacing(ev), "content": content, "cinematic": cine,
           "colour": (colour or {}).get("summary"),
           "lines": {"content": content_line(content), "cinematic": cinematic_line(cine),
                     "colour": ((colour or {}).get("summary") or {}).get("line", "")}}
    with _LOCK:
        _CACHE[name] = (sig, out)
    return out
