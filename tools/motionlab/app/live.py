"""Pages that update by themselves and the NEW badge (2026-10-24, a friend's asks: "what is created shows up without
going to another section and back"; "a red NEW on everything new - gone once I click it or go to another section").

  changes(section)  a cheap fingerprint of what a list page shows (directory listings and file times - nothing is
                    parsed): the page asks every few seconds (GET /api/changes?s=<section>) and redraws its list when
                    it changed. Sections: home, analyze, projects (Editor, Generator), prompts (Prepare, the prompt
                    library), motion, memory.
  seen()            per section of the sidebar (edit, generate, prepare, analyze, motion, memory): "at" = when the
                    user last left it + the cards clicked since (.app\\seen.json, on this PC - not in the browser,
                    so every window agrees). A card is NEW when its own time (a render finished, a script saved, an
                    analysis done) is after "at" and it was not clicked. A section seen for the first time starts
                    "now": nothing that was there before the update is NEW.
  mark(section, leave, key)  leave = the user went to another section (every badge of it goes); key = a card clicked
                    (the key carries its creation time, so a reused id - script-014 deleted, a new script-014 - is a
                    new card).
  render_done(p)    an MP4 that is whole: ffmpeg wrote its "moov" and the boxes run to the end of the file (a render
                    still being written is not "finished" - the Editor's NEW waits for it).
Standard library only."""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path

from motionlab.util import ANALYSIS, LAB

SEEN = LAB / ".app" / "seen.json"
SECTIONS = ("home", "analyze", "edit", "generate", "prepare", "motion", "memory")
_lock = threading.Lock()
_done: dict[tuple, bool] = {}


# ------------------------------------------------------------------------------------------------ finished renders
def render_done(p: Path) -> bool:
    """A whole MP4 (see the module's text); remembered per (file, size, time) - a render being written changes both."""
    try:
        st = p.stat()
    except OSError:
        return False
    key = (str(p), st.st_size, st.st_mtime_ns)
    if key in _done:
        return _done[key]
    ok = False
    if time.time() - st.st_mtime > 1.5:                   # still being written a moment ago: look again next time
        try:
            with open(p, "rb") as f:
                pos, moov = 0, False
                while pos < st.st_size:
                    f.seek(pos)
                    h = f.read(16)
                    if len(h) < 8:
                        break
                    n, typ = int.from_bytes(h[:4], "big"), h[4:8]
                    if n == 1 and len(h) == 16:
                        n = int.from_bytes(h[8:16], "big")
                    elif n == 0:
                        n = st.st_size - pos
                    if n < 8:
                        break
                    moov = moov or typ == b"moov"
                    pos += n
                ok = moov and pos == st.st_size
        except OSError:
            ok = False
        if len(_done) > 4000:
            _done.clear()
        _done[key] = ok
    return ok


def renders_done(b: Path) -> list[Path]:
    """A video's finished renders (build\\*.mp4), oldest first."""
    try:
        ps = [p for p in b.glob("*.mp4") if p.is_file()]
    except OSError:
        return []
    return sorted((p for p in ps if render_done(p)), key=lambda q: q.stat().st_mtime)


# ------------------------------------------------------------------------------------------------ what changed
def _ent(p: Path) -> tuple:
    try:
        st = p.stat()
        return p.name, st.st_mtime_ns, st.st_size
    except OSError:
        return p.name, None, None


def _listing(d: Path, files: tuple = ()) -> list:
    """d's entries (name, time, size) + the named files inside each sub-folder."""
    out = []
    try:
        with os.scandir(d) as it:
            ents = sorted(it, key=lambda e: e.name)
    except OSError:
        return [(str(d), None)]
    for e in ents:
        try:
            st = e.stat()
            out.append((e.name, st.st_mtime_ns, st.st_size if e.is_file() else 0))
            if files and e.is_dir():
                out += [_ent(Path(e.path) / f) for f in files]
        except OSError:
            continue
    return out


def _projects() -> list:
    out = []
    root = LAB / "projects"
    try:
        dirs = sorted((d for d in root.iterdir() if d.is_dir()), key=lambda d: d.name)
    except OSError:
        return []
    for d in dirs:
        b = d / "build"
        out.append((d.name, _ent(d)[1], [_ent(b / f) for f in ("project.json", "outcome.json", "made_from.json")],
                    _ent(b / "publish" / "package.json"), [(p.name, p.stat().st_mtime_ns) for p in renders_done(b)]))
    return out


def _prompts() -> list:
    home = LAB / "knowledge" / "local" / "prompts"
    out = []
    try:
        kinds = sorted(d for d in home.iterdir() if d.is_dir())
    except OSError:
        return []
    for k in kinds:
        out.append((k.name, _listing(k)))
    return out


def _analyses() -> list:
    out = [_listing(ANALYSIS, ("events.json", "review.json", "meta.json")), _ent(LAB / "refs" / "downloads.json")]
    for sub in ("thumbs", "texts"):
        out.append(_listing(ANALYSIS / sub, ("set.json", "style.json", "patterns.json", "verdicts.json")))
    out.append(_listing(ANALYSIS / "notes", ("note.json", "notes.json")))          # 2026-10-27: Notes
    return out


def _memory() -> list:
    k = LAB / "knowledge"
    return [_listing(k / "local"), _listing(k / "references"), _listing(k / "incoming"),
            _ent(LAB / ".claude" / "skills" / "analyze-reference" / "lessons.md"),
            _ent(LAB / ".claude" / "skills" / "recreate-video" / "lessons.md")]


def _motion() -> list:
    return [_listing(LAB / "tools" / "overlays" / "motion", ("index.html", "thumb.png")),
            _listing(LAB / "library" / "motion_graphics"), _listing(LAB / "library" / "motion_graphics" / "local"),
            _listing(LAB / "logos")]


PARTS = {"home": (_projects, _analyses, _prompts), "analyze": (_analyses,), "projects": (_projects,),
         "generate": (_projects, _prompts), "prompts": (_prompts,), "motion": (_motion,), "memory": (_memory,)}


def changes(section: str) -> dict:
    fns = PARTS.get(section)
    if not fns:
        raise ValueError(f"section: one of {', '.join(PARTS)}")
    raw = json.dumps([f() for f in fns], default=str)
    return {"section": section, "sig": hashlib.sha1(raw.encode()).hexdigest()[:16]}


# ------------------------------------------------------------------------------------------------ the NEW badge
def _read() -> dict:
    try:
        d = json.loads(SEEN.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(d: dict) -> None:
    SEEN.parent.mkdir(exist_ok=True)
    tmp = SEEN.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, indent=1), encoding="utf-8")
    os.replace(tmp, SEEN)


def seen() -> dict:
    """{section: {"at": seconds, "clicked": [keys]}} - a section never seen starts now."""
    with _lock:
        d, now, changed = _read(), time.time(), False
        for s in SECTIONS:
            if not isinstance(d.get(s), dict) or "at" not in d[s]:
                d[s], changed = {"at": now, "clicked": []}, True
        if changed:
            _write(d)
        return {s: {"at": d[s]["at"], "clicked": list(d[s].get("clicked") or [])} for s in SECTIONS}


def mark(section: str, leave: bool = False, key: str = "") -> dict:
    if section not in SECTIONS:
        raise ValueError(f"section: one of {', '.join(SECTIONS)}")
    with _lock:
        d = _read()
        s = d.get(section) if isinstance(d.get(section), dict) else {"at": time.time(), "clicked": []}
        if leave:
            s = {"at": time.time(), "clicked": []}
        elif key:
            s["clicked"] = (list(s.get("clicked") or []) + [str(key)[:200]])[-500:]
        d[section] = s
        _write(d)
    return seen()
