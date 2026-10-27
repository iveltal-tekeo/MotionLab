"""Notes from videos (the Analyser's third way, 2026-10-27 - the user: "get the video and analyze the content so i know
and be able to get notes, download as markdown... kinda like a notion but not that big, i just want to be simple and
effective"; the design from the research in docs\\plans.md 0.6.5 *Notes - the research*): what a video SAYS and SHOWS
as notes a professional would keep - a TL;DR, 3-7 key takeaways, the sections (the creator's chapters or Claude's),
the steps of a how-to, what to apply, the resources it names and a context block for another AI - each point tied to
the video's own words or to a frame Claude saw, with frame + timecode; plus the user's own notes, all downloadable as
Markdown.

Not an effects analysis: one folder per video in analysis\\notes\\<name>\\ (like analysis\\thumbs and analysis\\texts,
never an analysis - no events.json):
    note.json      the video (path, SHA-256, fps, frames), the link, the user's question (ask) and tags, the chapters,
                   the *Most replayed* peaks and the sponsor ranges in frames, the actions ticked (done)
    content\\       transcript.json + .txt (tools\\content.py's format), stats.json, info.json, thumbnail.<ext>
    frames\\        sheet_NN.jpg (key frames where the screen changes, each labelled f480 (00:00:16:00)) + frames.json
    notes.json     Claude's notes, saved only through save_notes() (the gate below) - never written by hand
    notes.md       the same notes as Markdown (made by save_notes)
    mine.md        the user's own notes (the app's My notes; Claude never writes it)

The gate (anti-hallucination by tools, like prompts.verify_check): every takeaway, section point and step quotes the
transcript (whole words in order, pieces joined by ...) - the tool finds the words and sets the frame + timecode
itself, Claude's `at` only picks between repeats - or names a frame of the sheets it shows (`shown`); a quote inside a
sponsor read is refused; a resource's link must be in the video's description. The limits (7 takeaways, 5 points a
section, 5 actions) are the tool's, so the notes never get crowded. Nothing is written when one check fails.
Transcripts are other people's words: they stay on this PC.
"""
from __future__ import annotations

import hashlib
import os
import re
import threading
import time
from pathlib import Path

from .timecode import frame_to_tc, label
from .util import ANALYSIS, LAB, read_json, safe_name, write_json

ROOT = Path(os.environ.get("MOTIONLAB_NOTES_ROOT") or (ANALYSIS / "notes"))
SCHEMA = 1
KINDS = ("tutorial", "lecture", "interview", "list", "opinion", "story", "other")
MAX_TAKEAWAYS, MAX_SECTIONS, MAX_POINTS, MAX_STEPS, MAX_APPLY, MAX_RESOURCES = 7, 12, 5, 20, 5, 10
QUOTE_MIN_WORDS, QUOTE_MAX_CHARS = 3, 400
SKIP_KINDS = ("sponsor", "selfpromo", "interaction")      # SponsorBlock ranges a note never quotes
MINE_MAX = 200_000                                         # the user's own notes: ~40 pages of text
_LOCK = threading.RLock()


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M")


def note_dir(name: str) -> Path:
    n = safe_name(str(name or ""))
    if not n.strip(" ._") or ".." in n:
        raise ValueError(f"not a notes name: {name!r}")
    return ROOT / n


def _load(p: Path, default=None):
    try:
        return read_json(p)
    except (OSError, ValueError):
        return default


def need(name: str) -> tuple[Path, dict]:
    d = note_dir(name)
    n = _load(d / "note.json")
    if not isinstance(n, dict):
        raise FileNotFoundError(f"no notes called {name!r} (analysis\\notes\\{d.name})")
    return d, n


def rel(p: Path | str | None) -> str | None:
    """A path the page can open (/files/...): inside the lab, with / separators; None outside it."""
    if not p:
        return None
    try:
        return Path(p).resolve().relative_to(LAB.resolve()).as_posix()
    except (ValueError, OSError):
        return None


def unique_name(video: Path) -> str:
    """The folder for a video: its name, or name_<6 hex> when that folder belongs to another video."""
    base = safe_name(video.stem) or "video"
    old = _load(ROOT / base / "note.json") or {}
    if old.get("video") and Path(old["video"]).resolve() != video.resolve():
        base = f"{base}_{hashlib.sha1(str(video.resolve()).encode('utf-8')).hexdigest()[:6]}"
    return base


def label_of(n: dict) -> str:
    return (n.get("label") or n.get("title") or n.get("name") or "").strip()


def _clean(s, limit: int) -> str:
    return " ".join(str(s or "").split())[:limit]


# ------------------------------------------------------------------------------------------------ the transcript
TOKEN = re.compile(r"[\w']+", re.UNICODE)


def _tokens(text: str) -> list[str]:
    return TOKEN.findall(str(text or "").replace("’", "'").replace("‘", "'").lower())


def transcript(d: Path) -> dict | None:
    t = _load(d / "content" / "transcript.json")
    return t if isinstance(t, dict) and t.get("lines") is not None else None


def _index(tr: dict) -> list[tuple[str, int]]:
    """Every word of the transcript in order with the frame it is said on (the word's own frame when the platform /
    speech to text timed words, else its line's first frame)."""
    out = []
    for ln in tr.get("lines") or []:
        ws = ln.get("words") or []
        if ws:
            for w in ws:
                out += [(tok, int(w.get("f", ln["start"]))) for tok in _tokens(w.get("w", ""))]
        else:
            out += [(tok, int(ln["start"])) for tok in _tokens(ln.get("text", ""))]
    return out


def find_quote(idx: list[tuple[str, int]], quote: str, hint: int | None = None) -> tuple[int, int] | None:
    """(first frame, last frame) of a quote's words in the transcript - pieces split by ... / … must follow each
    other within 300 words; between repeats the one nearest the hint frame. None when it is not there."""
    pieces = [p for p in (_tokens(x) for x in re.split(r"\.\.\.|…", quote)) if p]
    if not pieces:
        return None
    toks = [t for t, _ in idx]
    first = pieces[0]
    hits = []
    for i in range(len(toks) - len(first) + 1):
        if toks[i:i + len(first)] != first:
            continue
        j, ok = i + len(first), True
        for p in pieces[1:]:
            k = next((k for k in range(j, min(len(toks) - len(p) + 1, j + 300)) if toks[k:k + len(p)] == p), None)
            if k is None:
                ok = False
                break
            j = k + len(p)
        if ok:
            hits.append((idx[i][1], idx[j - 1][1]))
    if not hits:
        return None
    return min(hits, key=lambda h: abs(h[0] - hint)) if hint is not None else hits[0]


# ------------------------------------------------------------------------------------------------ what yt-dlp knows
def chapters_of(info: dict, fps: float, frames: int) -> list[dict]:
    """The creator's chapters in frames: [{title, start, end}] (inclusive, the last one to the video's end)."""
    out = []
    for c in (info or {}).get("chapters") or []:
        try:
            a = max(0, min(frames - 1, int(round(float(c.get("start_time") or 0) * fps))))
            b = max(a, min(frames - 1, int(round(float(c.get("end_time") or 0) * fps)) - 1))
        except (TypeError, ValueError):
            continue
        out.append({"title": _clean(c.get("title"), 120), "start": a, "end": b})
    return out


def replayed_of(info: dict, fps: float, frames: int, top: int = 3) -> list[list[int]]:
    """YouTube's *Most replayed* peaks in frames: the up to `top` highest local maxima of the heatmap (value >= 0.5,
    not the very start - most videos peak in their first seconds when people skip in)."""
    hm = [h for h in (info or {}).get("heatmap") or [] if isinstance(h, dict) and h.get("value") is not None]
    peaks = []
    for i, h in enumerate(hm):
        v = float(h["value"])
        if v < 0.5 or float(h.get("start_time") or 0) < 3:
            continue
        if (i and float(hm[i - 1]["value"]) > v) or (i + 1 < len(hm) and float(hm[i + 1]["value"]) > v):
            continue
        a = int(round(float(h["start_time"]) * fps))
        b = int(round(float(h.get("end_time") or h["start_time"]) * fps))
        peaks.append((v, [max(0, min(frames - 1, a)), max(0, min(frames - 1, b))]))
    return [p for _, p in sorted(peaks, key=lambda x: -x[0])[:top]]


# ------------------------------------------------------------------------------------------------ the gate
def check_draft(name: str, draft: dict) -> tuple[dict, list[str]]:
    """Claude's draft -> (the notes as saved, problems). Problems = nothing may be saved."""
    d, n = need(name)
    fps, frames, drop = float(n["fps"]), int(n["frames"]), bool(n.get("drop_frame"))
    tr = transcript(d)
    idx = _index(tr) if tr else []
    sheet = {int(f["f"]) for f in (_load(d / "frames" / "frames.json") or {}).get("frames", [])}
    chapters = n.get("chapters") or []
    skips = [s for s in n.get("skip") or [] if s.get("category") in SKIP_KINDS]
    replayed = n.get("replayed") or []
    desc = str((_load(d / "content" / "info.json") or {}).get("description") or "")
    bad: list[str] = []
    if not isinstance(draft, dict):
        return {}, ["the draft is not a JSON object"]

    def evidence(where: str, it: dict, out: dict) -> None:
        """the item's quote (found -> at / end / at_label) or the frame it shows (shown)."""
        hint = it.get("at")
        hint = int(hint) if isinstance(hint, (int, float)) and not isinstance(hint, bool) else None
        q = " ".join(str(it.get("quote") or "").split())
        shown = it.get("shown")
        if q:
            if len(q) > QUOTE_MAX_CHARS:
                bad.append(f"{where}: the quote has {len(q)} characters - quote at most {QUOTE_MAX_CHARS}")
            elif len(_tokens(q)) < QUOTE_MIN_WORDS:
                bad.append(f"{where}: quote at least {QUOTE_MIN_WORDS} words, so it points at one place")
            elif not idx:
                bad.append(f"{where}: there is no transcript to quote - point at a frame of the sheets (shown) instead")
            else:
                hit = find_quote(idx, q, hint)
                if hit is None:
                    bad.append(f"{where}: the quote is not in the transcript, word for word: {q[:120]!r}")
                else:
                    a, b = hit
                    sk = next((s for s in skips if s["start"] <= a <= s["end"]), None)
                    if sk:
                        bad.append(f"{where}: the quote is inside a {sk['category']} part ("
                                   f"{label(sk['start'], fps, drop)} - {label(sk['end'], fps, drop)}) - leave it out")
                    out.update(quote=q, at=a, end=max(a, b), at_label=label(a, fps, drop))
        if shown is not None:
            sf = int(shown) if isinstance(shown, (int, float)) and not isinstance(shown, bool) else None
            if sf is None or sf not in sheet:
                bad.append(f"{where}: shown={shown!r} is not a frame of the sheets (frames\\frames.json)")
            else:
                out.update(shown=sf, shown_label=label(sf, fps, drop))
                if "at" not in out:
                    out.update(at=sf, end=sf, at_label=label(sf, fps, drop))
        if not q and shown is None:
            bad.append(f"{where}: neither a quote of the video's words nor a frame it shows (shown) - every point "
                       "comes from the video")
        if "at" in out and any(a <= out["at"] <= b for a, b in replayed):
            out["replayed"] = True

    def text_of(where: str, it: dict, limit: int) -> str:
        t = str(it.get("text") or "").strip()
        if not t:
            bad.append(f"{where}: no text")
        elif len(t) > limit:
            bad.append(f"{where}: {len(t)} characters - at most {limit} (one or two sentences)")
        return t[:limit]

    def objects(key: str, most: int, least: int = 0) -> list:
        v = draft.get(key)
        if v is None:
            v = []
        if not isinstance(v, list):
            bad.append(f"{key}: a list")
            return []
        if len(v) < least:
            bad.append(f"{key}: at least {least}")
        if len(v) > most:
            bad.append(f"{key}: {len(v)} - at most {most}; keep the ones that matter")
        return v[:most]

    kind = str(draft.get("kind") or "other").strip().lower()
    if kind not in KINDS:
        bad.append(f"kind: {kind!r} - one of {', '.join(KINDS)}")
    tldr = " ".join(str(draft.get("tldr") or "").split())
    if not tldr:
        bad.append("tldr: missing (one or two sentences: what the video is about and what it concludes)")
    elif len(tldr) > 400:
        bad.append(f"tldr: {len(tldr)} characters - at most 400 (one or two sentences)")

    takeaways = []
    for i, it in enumerate(objects("takeaways", MAX_TAKEAWAYS, 1)):
        w = f"takeaways[{i}]"
        if not isinstance(it, dict):
            bad.append(f"{w}: not an object")
            continue
        out = {"phrase": _clean(it.get("phrase"), 80), "text": text_of(w, it, 300)}
        if not out["phrase"]:
            bad.append(f"{w}: no phrase (the 2-6 words a reader keeps, shown in bold)")
        evidence(w, it, out)
        takeaways.append(out)

    sections = []
    for i, it in enumerate(objects("sections", MAX_SECTIONS)):
        w = f"sections[{i}]"
        if not isinstance(it, dict):
            bad.append(f"{w}: not an object")
            continue
        sec = {"title": _clean(it.get("title"), 100), "gist": _clean(it.get("gist"), 200), "points": []}
        if not sec["title"]:
            bad.append(f"{w}: no title")
        pts = it.get("points") or []
        if not isinstance(pts, list) or len(pts) > MAX_POINTS:
            bad.append(f"{w}.points: a list of at most {MAX_POINTS}")
            pts = pts[:MAX_POINTS] if isinstance(pts, list) else []
        for j, p in enumerate(pts):
            pw = f"{w}.points[{j}]"
            if not isinstance(p, dict):
                bad.append(f"{pw}: not an object")
                continue
            po = {"text": text_of(pw, p, 300)}
            evidence(pw, p, po)
            sec["points"].append(po)
        ch = it.get("chapter")
        if ch is not None:
            if not isinstance(ch, int) or isinstance(ch, bool) or not 0 <= ch < len(chapters):
                bad.append(f"{w}: chapter {ch!r} - the video has {len(chapters)} chapter(s), numbered from 0")
            else:
                sec.update(chapter=ch, at=chapters[ch]["start"])
        if "at" not in sec:
            ats = [p["at"] for p in sec["points"] if "at" in p]
            if ats:
                sec["at"] = min(ats)
            else:
                bad.append(f"{w}: neither a chapter nor a point with its place in the video")
        if "at" in sec:
            sec["at_label"] = label(sec["at"], fps, drop)
        sections.append(sec)
    sections.sort(key=lambda s: s.get("at", 0))

    steps = []
    for i, it in enumerate(objects("steps", MAX_STEPS)):
        w = f"steps[{i}]"
        if not isinstance(it, dict):
            bad.append(f"{w}: not an object")
            continue
        out = {"text": text_of(w, it, 300)}
        evidence(w, it, out)
        steps.append(out)

    apply_ = [str(a).strip() for a in objects("apply", MAX_APPLY, 1) if str(a).strip()]
    if any(len(a) > 300 for a in apply_):
        bad.append("apply: one action a line, at most 300 characters")

    resources = []
    for i, it in enumerate(objects("resources", MAX_RESOURCES)):
        w = f"resources[{i}]"
        url = str((it or {}).get("url") or "").strip() if isinstance(it, dict) else ""
        nm = _clean((it or {}).get("name"), 100) if isinstance(it, dict) else ""
        if not url or not nm:
            bad.append(f"{w}: a name and a url")
        elif not re.fullmatch(r"https?://\S+", url) or url not in desc:
            bad.append(f"{w}: {url[:80]!r} is not a link of the video's description - name only links it gives")
        else:
            resources.append({"name": nm, "url": url})

    ctx = str(draft.get("ai_context") or "").strip()
    if not ctx:
        bad.append("ai_context: missing (a block the user pastes into another AI)")
    elif len(ctx) > 4000:
        bad.append(f"ai_context: {len(ctx)} characters - at most 4000 (~600 words)")
    raw = draft.get("tags") if isinstance(draft.get("tags"), list) else []
    tags = [t for t in dict.fromkeys(_clean(t, 40).lower() for t in raw) if t][:8]
    out = {"schema": SCHEMA, "name": d.name, "made": _now(), "by": "Claude", "kind": kind,
           "lang": _clean(draft.get("lang"), 10) or None, "title": _clean(draft.get("title"), 160) or label_of(n),
           "tldr": tldr, "takeaways": takeaways, "sections": sections, "steps": steps,
           "apply": [a[:300] for a in apply_], "resources": resources, "ai_context": ctx[:4000], "tags": tags,
           "based_on": {"transcript": (tr or {}).get("source"), "words": (tr or {}).get("words"),
                        "sheets": len(sheet), "chapters": len(chapters)}}
    return out, bad


def save_notes(name: str, draft: dict) -> dict:
    """The gate's only way in: check the draft, then notes.json + notes.md. Raises ValueError with every problem.
    Claude writing the notes again clears the actions the user ticked (they belonged to the old ones)."""
    with _LOCK:
        notes, bad = check_draft(name, draft)
        if bad:
            raise ValueError("nothing saved - fix these and save again:\n- " + "\n- ".join(bad))
        d, n = need(name)
        write_json(d / "notes.json", notes)
        if n.get("done"):
            n["done"] = []
            write_json(d / "note.json", n)
        (d / "notes.md").write_text(render_md(n, notes), encoding="utf-8")
        return notes


# ------------------------------------------------------------------------------------------------ Markdown
def _src_line(n: dict) -> str:
    parts = [f"[{n.get('platform') or 'link'}]({n['url']})" if n.get("url") else Path(n.get("video") or "").name]
    if n.get("uploader"):
        parts.append(str(n["uploader"]))
    if n.get("duration_s"):
        s = int(round(n["duration_s"]))
        parts.append(f"{s // 3600}:{s // 60 % 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}")
    parts.append(f"{float(n['fps']):g} fps")
    return " · ".join(parts)


def render_md(n: dict, notes: dict) -> str:
    """The notes as Markdown, in the page's order: every time as f480 (00:00:16:00) at the video's own frame rate."""
    done = set(n.get("done") or [])
    L = [f"# {notes.get('title') or label_of(n)}", "", f"*{_src_line(n)}*  ",
         f"*Notes by Claude, {notes.get('made', '')}. Every time = frame + timecode, e.g. f480 (00:00:16:00).*", ""]
    if n.get("ask"):
        L += [f"> Asked for: {n['ask']}", ""]
    L += [f"> **TL;DR** {notes.get('tldr', '')}", ""]

    def when(it):
        if it.get("at_label"):
            return f" - {it['at_label']}" + (" (most replayed)" if it.get("replayed") else "")
        return ""
    if notes.get("takeaways"):
        L += ["## Key takeaways", ""] + [f"- **{t['phrase']}** - {t['text']}{when(t)}" for t in notes["takeaways"]] + [""]
    if notes.get("sections"):
        L += ["## Sections", ""]
    for s in notes.get("sections") or []:
        L += [f"### {s['title']}" + (f" - {s['at_label']}" if s.get("at_label") else ""), ""]
        if s.get("gist"):
            L += [f"*{s['gist']}*", ""]
        L += [f"- {p['text']}{when(p)}" for p in s["points"]] + [""]
    if notes.get("steps"):
        L += ["## Steps", ""] + [f"{i}. {s['text']}{when(s)}" for i, s in enumerate(notes["steps"], 1)] + [""]
    if notes.get("apply"):
        L += ["## Apply it", ""] + [f"- [{'x' if i in done else ' '}] {a}" for i, a in enumerate(notes["apply"])] + [""]
    if notes.get("resources"):
        L += ["## Resources", ""] + [f"- [{r['name']}]({r['url']})" for r in notes["resources"]] + [""]
    if notes.get("ai_context"):
        L += ["## Context for another AI", "", "```text", notes["ai_context"], "```", ""]
    if notes.get("tags"):
        L += ["Tags: " + ", ".join(notes["tags"]), ""]
    return "\n".join(L).rstrip() + "\n"


def export_md(name: str, transcript_too: bool = False) -> tuple[str, str]:
    """(file name, Markdown) of Download: Claude's notes + My notes (+ the transcript, frame + timecode per line)."""
    d, n = need(name)
    nt = _load(d / "notes.json")
    body = render_md(n, nt) if isinstance(nt, dict) else f"# {label_of(n)}\n\n*{_src_line(n)}*\n"
    mine = mine_text(name)
    if mine.strip():
        body += "\n## My notes\n\n" + mine.strip() + "\n"
    tr = transcript(d)
    if transcript_too and tr:
        fps, drop = float(n["fps"]), bool(n.get("drop_frame"))
        body += "\n## Transcript\n\n" + "\n".join(f"- {label(r['start'], fps, drop)} {r['text']}" for r in tr["lines"]) + "\n"
    fname = (safe_name(n.get("label") or (nt or {}).get("title") or label_of(n)) or d.name)[:80] + ".md"
    return fname, body


# ------------------------------------------------------------------------------------------------ the user's side
def mine_text(name: str) -> str:
    d, _ = need(name)
    try:
        return (d / "mine.md").read_text(encoding="utf-8")
    except OSError:
        return ""


def save_mine(name: str, text: str) -> dict:
    """My notes: the user's own text (Markdown), one file, saved whole."""
    text = str(text or "").replace("\r\n", "\n")
    if len(text) > MINE_MAX:
        raise ValueError(f"at most {MINE_MAX:,} characters")
    with _LOCK:
        d, _ = need(name)
        tmp = d / "mine.md.tmp"
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(d / "mine.md")
    return {"ok": True, "saved": _now(), "chars": len(text)}


def save_meta(name: str, label_: str | None = None, tags=None, done=None) -> dict:
    """The name the pages show, the tags and the actions ticked (the folder keeps its name)."""
    with _LOCK:
        d, n = need(name)
        if label_ is not None:
            n["label"] = _clean(label_, 120)
        if tags is not None:
            raw = tags.split(",") if isinstance(tags, str) else list(tags or [])
            n["tags"] = [t for t in dict.fromkeys(_clean(t, 40).lower() for t in raw) if t][:12]
        if done is not None:
            k = len((_load(d / "notes.json") or {}).get("apply") or [])
            n["done"] = sorted({int(i) for i in done if isinstance(i, int) and not isinstance(i, bool) and 0 <= i < k})
        write_json(d / "note.json", n)
        nt = _load(d / "notes.json")
        if done is not None and isinstance(nt, dict):        # the ticks show in the Markdown too
            (d / "notes.md").write_text(render_md(n, nt), encoding="utf-8")
        return {"label": label_of(n), "tags": n.get("tags") or [], "done": n.get("done") or []}


def _thumb(d: Path) -> str | None:
    for p in sorted((d / "content").glob("thumbnail.*")) if (d / "content").is_dir() else []:
        if p.suffix.lower() in (".jpg", ".png", ".webp"):
            return rel(p)
    f = d / "frames" / "cover.jpg"
    return rel(f) if f.exists() else None


def summary(d: Path, n: dict) -> dict:
    nt = _load(d / "notes.json")
    tr = transcript(d)
    has = isinstance(nt, dict)
    v = Path(n.get("video") or "")
    return {"name": d.name, "label": label_of(n), "title": n.get("title"), "url": n.get("url"),
            "platform": n.get("platform"), "uploader": n.get("uploader"), "duration_s": n.get("duration_s"),
            "fps": n.get("fps"), "frames": n.get("frames"), "created": n.get("created"), "tags": n.get("tags") or [],
            "ask": n.get("ask") or "", "thumb": _thumb(d), "issues": n.get("issues") or [],
            "video_there": bool(n.get("video")) and v.is_file(),
            "transcript": {"source": tr.get("source"), "words": tr.get("words"), "lang": tr.get("lang"),
                           "lines": len(tr.get("lines") or [])} if tr else None,
            "notes": {"made": nt.get("made"), "kind": nt.get("kind"), "title": nt.get("title"),
                      "takeaways": len(nt.get("takeaways") or []), "sections": len(nt.get("sections") or []),
                      "tldr": nt.get("tldr", "")} if has else None,
            "mine": (d / "mine.md").exists() and (d / "mine.md").stat().st_size > 0,
            "status": "ready" if has else ("claude" if (tr or (d / "frames" / "frames.json").exists()) else "empty")}


def list_notes() -> list[dict]:
    out = []
    for d in sorted(ROOT.iterdir()) if ROOT.is_dir() else []:
        n = _load(d / "note.json") if d.is_dir() else None
        if isinstance(n, dict) and n.get("fps") and n.get("frames"):
            out.append(summary(d, n))
    out.sort(key=lambda x: x.get("created") or "", reverse=True)
    return out


def pending() -> list[str]:
    """The notes Claude has not written yet (their words or key frames are ready)."""
    return [x["name"] for x in list_notes() if x["status"] == "claude"]


def get(name: str) -> dict:
    """Everything the notes page shows."""
    d, n = need(name)
    out = summary(d, n)
    tr = transcript(d)
    v = Path(n.get("video") or "")
    out.update(video=str(v) if n.get("video") else "", video_rel=rel(v) if out["video_there"] else None,
               drop_frame=bool(n.get("drop_frame")), width=n.get("width"), height=n.get("height"),
               lines=[{"start": r["start"], "end": r["end"], "text": r["text"]} for r in (tr or {}).get("lines") or []],
               stats=_load(d / "content" / "stats.json"), notes_full=_load(d / "notes.json"),
               chapters=n.get("chapters") or [], replayed=n.get("replayed") or [], skip=n.get("skip") or [],
               done=n.get("done") or [], mine_text=mine_text(name),
               sheets=[rel(p) for p in sorted((d / "frames").glob("sheet_*.jpg"))] if (d / "frames").is_dir() else [],
               folder=rel(d))
    return out


def users_of(video: Path) -> list[str]:
    """The notes made from this video file (the Delete dialog warns before the video goes)."""
    out = []
    for d in sorted(ROOT.iterdir()) if ROOT.is_dir() else []:
        n = _load(d / "note.json") if d.is_dir() else None
        if isinstance(n, dict) and n.get("video"):
            try:
                if Path(n["video"]).resolve() == Path(video).resolve():
                    out.append(d.name)
            except OSError:
                pass
    return out


def videos() -> set[str]:
    """The file names (lower case) of the videos notes were made from - not "waiting to be analysed"."""
    out = set()
    for d in ROOT.iterdir() if ROOT.is_dir() else []:
        n = _load(d / "note.json") if d.is_dir() else None
        if isinstance(n, dict) and n.get("video"):
            out.add(Path(n["video"]).name.lower())
    return out


def show_text(name: str) -> str:
    """What Claude reads first (notes.py show): the video, the user's question, what there is to read."""
    d, n = need(name)
    fps, drop = float(n["fps"]), bool(n.get("drop_frame"))
    tr = transcript(d)
    fr = (_load(d / "frames" / "frames.json") or {}).get("frames", [])
    L = [f"notes: {d.name}  ({label_of(n)})", f"video: {n.get('video')}",
         f"source: {n.get('url') or 'a file (no link)'} · {n.get('platform') or ''} · {n.get('uploader') or ''}",
         f"{fps:g} fps · {n['frames']} frames (f0-{int(n['frames']) - 1}, 00:00:00:00 - "
         f"{frame_to_tc(int(n['frames']) - 1, fps, drop)})",
         f"the user asks: {n['ask']}" if n.get("ask") else "the user asks: nothing in particular - the general notes",
         f"tags: {', '.join(n.get('tags') or []) or '-'}"]
    if tr:
        L.append(f"transcript: {tr.get('source')} ({tr.get('lang') or '?'}), {len(tr['lines'])} lines, "
                 f"{tr.get('words')} words -> {d / 'content' / 'transcript.txt'}")
    else:
        L.append("transcript: none - " + "; ".join(n.get("issues") or ["no words found"]))
    for i, c in enumerate(n.get("chapters") or []):
        L.append(f"chapter {i}: {c['title']}  {label(c['start'], fps, drop)} - {label(c['end'], fps, drop)}")
    for a, b in n.get("replayed") or []:
        L.append(f"most replayed: {label(a, fps, drop)} - {label(b, fps, drop)}")
    for s in n.get("skip") or []:
        L.append(f"SponsorBlock {s['category']}: {label(s['start'], fps, drop)} - {label(s['end'], fps, drop)}"
                 + (" (never quoted)" if s["category"] in SKIP_KINDS else ""))
    if (d / "content" / "info.json").exists():
        L.append(f"description, tags, language: {d / 'content' / 'info.json'} (resources = only links it gives)")
    if fr:
        L.append(f"key frames: {len(fr)} on {len(list((d / 'frames').glob('sheet_*.jpg')))} sheet(s) in {d / 'frames'}"
                 " - frames.json lists the frames a point can name as shown")
    st = _load(d / "content" / "stats.json")
    if isinstance(st, dict):
        L.append(f"numbers: {st.get('views')} views, {st.get('likes')} likes, {st.get('comments')} comments, "
                 f"{st.get('followers')} followers ({st.get('fetched')})")
    brand = LAB / "knowledge" / "local" / "brand.json"
    if brand.exists():
        L.append(f"My Brand (for Apply it): {brand}")
    L.append("notes: " + ("written " + str((_load(d / 'notes.json') or {}).get('made')) if (d / "notes.json").exists()
                          else "not written yet"))
    return "\n".join(L)
