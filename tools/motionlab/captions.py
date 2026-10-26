"""Captions (0.3.2): timed words -> caption cues -> a styled HTML caption clip (tools\\overlay.py captions) and an SRT
for DaVinci Resolve's subtitle track. Standard library only.

Where the words come from: any SRT / WebVTT file (YouTube, CapCut, Resolve Studio's own "Create Subtitles from
Audio", ...), or a lab transcript (analysis\\<name>\\content\\transcript.json, tools\\content.py). The lab's own
speech-to-text for your recordings comes later (docs\\plans.md 0.3.5 / 0.4: the engine is chosen after measuring).
A cue without word timings (plain SRT) spreads its time over its words by their length - marked "estimated".
"""
from __future__ import annotations

import html
import json
import math
import re
from pathlib import Path

TIME = r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{3})"
CUE = re.compile(TIME + r"\s+-->\s+" + TIME)
WORD_TAG = re.compile(r"<(\d+:\d{2}:\d{2}\.\d{3}|\d{2}:\d{2}\.\d{3})>")
SENTENCE_END = re.compile(r"[.!?…]['\")\]]*$")
TAG = re.compile(r"^\[[^\]]*\]?$|^\([^)]*\)$|^[^\[]*\]$")   # [Music], (applause), a cut "[music": sounds


def _secs(h, m, s, ms) -> float:
    return round(int(h or 0) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000, 3)


def _tag_secs(t: str) -> float:
    parts = t.replace(",", ".").split(":")
    return sum(float(p) * 60 ** i for i, p in enumerate(reversed(parts)))


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)                       # <c>, <i>, <b>, voice tags
    text = html.unescape(text).replace("​", "")
    return re.sub(r"\s+", " ", text).strip()


def parse_captions(text: str) -> tuple[list[dict], bool]:
    """WebVTT or SRT -> (lines, has_word_timings). A line = {t0, t1, text, words: [{t, w}]}.
    YouTube's auto captions repeat the previous line in every cue and time each new word (<00:00:01.234><c> word</c>):
    only the timed lines are new speech. Uploaded subtitles are one cue = one line."""
    cues, cur = [], None
    for row in text.replace("﻿", "").splitlines():      # a cue ends at the first empty line after its text
        m = CUE.search(row)                                   # (YouTube's cues hold lines of one space, and an
        if m:                                                 # empty line may follow the timing line)
            cur = (_secs(*m.groups()[:4]), _secs(*m.groups()[4:]), [])
            cues.append(cur)
        elif cur is not None and not row.strip():
            if any(r.strip() for r in cur[2]):
                cur = None
        elif cur is not None:
            cur[2].append(row)
    word_mode = any(WORD_TAG.search(r) for _, _, rows in cues for r in rows)
    lines: list[dict] = []
    for t0, t1, rows in cues:
        if word_mode:
            for row in rows:
                if not WORD_TAG.search(row):
                    continue                                    # the repeated previous line
                words, t = [], t0
                for k, piece in enumerate(WORD_TAG.split(row)):
                    if k % 2:                                   # a timing tag: the next word starts here
                        t = _tag_secs(piece)
                        continue
                    for w in _clean(piece).split():
                        words.append({"t": round(t, 3), "w": w})
                if words:
                    lines.append({"t0": words[0]["t"], "t1": t1, "text": " ".join(w["w"] for w in words),
                                  "words": words})
        else:
            txt = _clean(" ".join(rows))
            if txt and not (lines and lines[-1]["text"] == txt and abs(lines[-1]["t1"] - t0) < 0.05):
                lines.append({"t0": t0, "t1": t1, "text": txt, "words": []})
            elif txt:
                lines[-1]["t1"] = t1                            # the same text continued
    lines.sort(key=lambda l: l["t0"])
    for a, b in zip(lines, lines[1:]):                          # rolling captions overlap: end at the next line
        if word_mode:
            a["t1"] = min(a["t1"], b["t0"]) if b["t0"] > a["t0"] else a["t1"]
    return lines, word_mode


def words_of(lines: list[dict]) -> tuple[list[dict], bool]:
    """Lines -> one list of words {w, t0, t1, est, first}; est = the time was spread over a cue, not measured;
    first = the first word of a line in the file (a plain SRT's line breaks are kept)."""
    out, estimated = [], False
    for ln in lines:
        t0, t1 = float(ln["t0"]), float(ln["t1"])
        ws = ln.get("words") or []
        ws = [w for w in ws if not TAG.match(w["w"])]
        if ws:
            for i, w in enumerate(ws):
                end = float(ws[i + 1]["t"]) if i + 1 < len(ws) else t1
                out.append({"w": w["w"], "t0": float(w["t"]), "t1": max(end, float(w["t"]) + 0.04), "est": False,
                            "first": i == 0})
        else:
            toks = re.sub(r"[\[(][^\])]*[\])]", " ", ln["text"]).split()
            weight = [len(t) + 1 for t in toks]
            total, acc = sum(weight) or 1, 0
            for k, (t, wt) in enumerate(zip(toks, weight)):
                a = t0 + (t1 - t0) * acc / total
                acc += wt
                out.append({"w": t, "t0": round(a, 3), "t1": round(t0 + (t1 - t0) * acc / total, 3), "est": True,
                            "first": k == 0})
                estimated = True
    out.sort(key=lambda w: w["t0"])
    return out, estimated


def load(path: str | Path) -> tuple[list[dict], bool, str]:
    """(words, estimated, what) from an .srt / .vtt or a lab transcript.json."""
    p = Path(path)
    if not p.is_file():
        raise ValueError(f"no such file: {p}")
    text = p.read_text(encoding="utf-8-sig", errors="replace")
    if p.suffix.lower() == ".json":
        d = json.loads(text)
        lines = [{"t0": l["t0"], "t1": l["t1"], "text": l["text"], "words": l.get("words") or []}
                 for l in d.get("lines", [])]
        what = f"lab transcript ({d.get('source', '?')}, {d.get('kind', '?')})"
    elif p.suffix.lower() in (".srt", ".vtt"):
        lines, _ = parse_captions(text)
        what = p.suffix.lower()[1:].upper() + " file"
    else:
        raise ValueError(f"{p.name}: captions come from an .srt, a .vtt or a lab transcript.json")
    if not lines:
        raise ValueError(f"{p.name}: no captions found in it")
    words, est = words_of(lines)
    return words, est, what


def group(words: list[dict], max_chars: int = 32, max_words: int = 6, max_gap: float = 0.6,
          max_secs: float = 3.0, min_secs: float = 0.5) -> list[dict]:
    """Words -> caption cues of a few words: a new cue after a sentence end, a pause, too many characters or words,
    or too long on screen. A file without word timings (a plain SRT) keeps its own lines - they are meant - and only
    a line much longer than max_chars is split, into even parts. A cue = {t0, t1, text, words}; it stays until the
    next one starts (max +min_secs)."""
    cues: list[dict] = []
    cur: list[dict] = []

    def close():
        if cur:
            cues.append({"t0": cur[0]["t0"], "t1": cur[-1]["t1"], "words": list(cur),
                         "text": " ".join(w["w"] for w in cur)})
            cur.clear()

    if words and all(w.get("est") for w in words):
        lines: list[list[dict]] = []
        for w in words:
            if w.get("first") or not lines:
                lines.append([])
            lines[-1].append(w)
        for ln in lines:
            chars = len(" ".join(w["w"] for w in ln))
            parts = max(1, math.ceil(chars / (max_chars * 1.5)), math.ceil(len(ln) / (max_words * 2)))
            pos, part = 0, 0
            for w in ln:
                k = min(parts - 1, int((pos + len(w["w"]) / 2) / max(chars, 1) * parts))   # where its middle falls
                if k != part:
                    close()
                    part = k
                cur.append(w)
                pos += len(w["w"]) + 1
            close()
    else:
        for w in words:
            if cur:
                chars = len(" ".join(x["w"] for x in cur)) + 1 + len(w["w"])
                if (chars > max_chars or len(cur) >= max_words or w["t0"] - cur[-1]["t1"] > max_gap
                        or w["t1"] - cur[0]["t0"] > max_secs or SENTENCE_END.search(cur[-1]["w"])):
                    close()
            cur.append(w)
        close()
    for a, b in zip(cues, cues[1:]):                 # hold each cue until the next (no flicker in short pauses)
        a["t1"] = max(a["t1"], min(b["t0"], a["t1"] + min_secs))
    if cues:
        cues[-1]["t1"] = max(cues[-1]["t1"], cues[-1]["t0"] + min_secs)
    return cues


def _tok(w: str) -> str:
    return re.sub(r"[^\w]+", "", w.lower())


def align_script(words: list[dict], lines: list[str], hold: float = 0.5, max_chars: int = 32,
                 max_words: int | None = None) -> tuple[list, list]:
    """0.5.3 (A8): captions that keep the SCRIPT's lines and wording, at the transcript's times - instead of group()'s
    own regrouping ("One:" joined its sentence, a 3-s cap split "take half the" / "time.", local-make-17) and speech to
    text's mis-heard names ("rebuilds" -> "repels", local-make-2). Each line's words are matched to the transcript's
    in order (difflib over the whole text); a line's cue runs from its first matched word to its last, held until the
    next one (+hold s at most); unmatched words get times spread inside the line; a line over 2 x max_chars (or, with
    max_words - My Brand's words per line, 2026-10-26 - over that many words) is split into even parts. Returns (cues
    as group() makes them, the lines not found in what was said)."""
    import difflib
    toks = [_tok(w["w"]) for w in words]
    script = [(i, w) for i, ln in enumerate(lines) for w in ln.split() if _tok(w)]
    sm = difflib.SequenceMatcher(None, [_tok(w) for _, w in script], toks, autojunk=False)
    hit = {}
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            hit[blk.a + k] = blk.b + k
    cues, missing, pos = [], [], 0
    for i, ln in enumerate(lines):
        idx = [k for k, (li, _) in enumerate(script) if li == i]
        if not idx:
            continue
        got = [hit[k] for k in idx if k in hit]
        if not got:
            missing.append(ln)
            pos += len(idx)
            continue
        t0, t1 = float(words[min(got)]["t0"]), float(words[max(got)]["t1"])
        ws = []
        for j, k in enumerate(idx):                         # the script's words; a matched one takes its time
            if k in hit:
                a, b = float(words[hit[k]]["t0"]), float(words[hit[k]]["t1"])
            else:
                a = t0 + (t1 - t0) * j / len(idx)
                b = t0 + (t1 - t0) * (j + 1) / len(idx)
            ws.append({"w": script[k][1], "t0": round(a, 3), "t1": round(max(b, a + 0.04), 3)})
        for j in range(1, len(ws)):                         # never back in time inside a line
            ws[j]["t0"] = max(ws[j]["t0"], ws[j - 1]["t0"])
        parts = max(1, math.ceil(len(ln) / (max_chars * 2)), math.ceil(len(ws) / max_words) if max_words else 1)
        size = math.ceil(len(ws) / parts)
        for p in range(0, len(ws), size):
            chunk = ws[p:p + size]
            cues.append({"t0": chunk[0]["t0"], "t1": chunk[-1]["t1"], "words": chunk,
                         "text": " ".join(w["w"] for w in chunk)})
        pos += len(idx)
    cues.sort(key=lambda c: c["t0"])
    for a, b in zip(cues, cues[1:]):
        a["t1"] = max(a["t1"], min(b["t0"], a["t1"] + hold))
    if cues:
        cues[-1]["t1"] = cues[-1]["t1"] + hold
    return cues, missing


def in_frames(cues: list[dict], fps: float, offset: int = 0) -> list[dict]:
    """Cues with frames: f0 = first frame shown, f1 = last (inclusive), per word too; offset moves everything."""
    out = []
    last = -1
    for c in cues:
        f0 = max(int(round(c["t0"] * fps)) + offset, last + 1, 0)
        f1 = max(int(round(c["t1"] * fps)) + offset - 1, f0)
        ws = []
        for w in c["words"]:
            a = min(max(int(round(w["t0"] * fps)) + offset, f0), f1)
            ws.append({"w": w["w"], "f0": a})
        for i, w in enumerate(ws):
            w["f1"] = (ws[i + 1]["f0"] - 1) if i + 1 < len(ws) else f1
            w["f1"] = max(w["f1"], w["f0"])
        out.append({"f0": f0, "f1": f1, "text": c["text"], "words": ws})
        last = f1
    return out


def srt_time(f: int, fps: float) -> str:
    ms = int(round(f / fps * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def srt(cues_f: list[dict], fps: float) -> str:
    """SRT text from frame cues (end = the first frame after the cue), e.g. for Resolve's subtitle track."""
    rows = []
    for i, c in enumerate(cues_f, 1):
        rows.append(f"{i}\n{srt_time(c['f0'], fps)} --> {srt_time(c['f1'] + 1, fps)}\n{c['text']}\n")
    return "\n".join(rows)


def captions_js(cues_f: list[dict], fps: float, source: str, estimated: bool) -> str:
    data = {"fps": fps, "source": source, "estimated": estimated,
            "cues": [{"f0": c["f0"], "f1": c["f1"], "words": [[w["w"], w["f0"], w["f1"]] for w in c["words"]]}
                     for c in cues_f]}
    return ("// MotionLab captions (tools\\overlay.py captions): cues with frames, words = [text, first frame, last "
            "frame]\nwindow.CAPTIONS = " + json.dumps(data, ensure_ascii=False) + ";\n")
