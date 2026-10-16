"""Motion-graphics templates (0.5.0 "Motion graphics", steps 1-3 for packs that are only preview videos, + step 5's
first blocks): a pack of captured template clips is measured with no Claude (when things move, how long they hold, the
ease of each move from the change per frame, where on the frame it moves, the colours) and gets a contact sheet per
clip with frame + timecode on every tile; Claude names what each one is (cards.json); the best ones are rebuilt as
MotionLab's own HyperFrames graphics in tools\\overlays\\motion\\<id>\\ - the Motion Graphics library the app's
*Motion Graphics* page shows and Generate builds from. CLI: tools\\templates.py. This half (the catalogue, the library,
pick) is standard library only - the app imports it; the measuring is motionlab\\template_read.py (numpy / OpenCV).

Layout - one pack per folder under ROOT (analysis\\templates\\; MOTIONLAB_TEMPLATES_ROOT moves it, tests do):
    <ROOT>\\<pack>\\pack.json      {"pack", "source" (the clips' folder, lab-relative), "read" (date), "items": [{"id"
                                  ("text__good-mood": the file name without the pack prefix), "kind" ("text"), "slug",
                                  "name" ("Good mood"), "file" (lab-relative), "sha256", "sig", "frames", "fps",
                                  "width", "height", "seconds", "still" (true = a capture of under STILL_FRAMES frames:
                                  a picture, not a motion), "motion": {...}, "colours": {...}}], "kinds": {kind: n}}
                  <id>\\sheet.png    up to 16 tiles: frame 0, each move's start / fastest / end, the last frame - frame +
                                  timecode under each - and the change per frame drawn below them, moves shaded
                  <id>\\poster.jpg   the frame the most is on screen (the middle of the longest hold)
                  overview_N.png    8 clips a page, 6 tiles each with frame + timecode - what Claude reads in bulk
                  cards.json        Claude's (/generate-video templates <pack>), never written here: {"pack", "date",
                                  "cards": {id: {"what", "use_for": [...], "tags": [...], "family", "rebuild": 1-3
                                  (1 = rebuild first), "note"}}}
The clips are only read (hard rule 1): their SHA-256 is recorded on the first read and checked on every later one; a
changed clip is reported, never "fixed".

What counts (per clip, measured on a half-size grey copy, frame t compared with t - 1):
- change[t] = the share of pixels that changed by more than DIFF_LEVEL (0-1); a frame MOVES when change > MOVE_SHARE
- moves = runs of moving frames (gaps of up to GAP_FRAMES still frames joined): start / end / fastest frame, the
  ease from where the change peaks inside the move (CLAUDE.md's words: decelerating (slow end) = the change is
  front-loaded, accelerating (slow start) = back-loaded, S-curve = it peaks in the middle, linear = flat), where on the
  frame it moved (a box in % of the frame) - from the change per frame, less exact than keyframes
- holds = still runs of HOLD_FRAMES or more; "alive" = the share of hold frames with a small change (a drift, a pulse,
  a blinking cursor): what keeps a hold from looking frozen
- cuts = frames where over CUT_SHARE of the picture changed at once (a scene change, not a move)
- loops = the last frame is the first one again (change under DIFF_LEVEL on most pixels)
- colours: the background (the frame's border, median) and 5 main colours of three frames
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .timecode import frame_to_tc
from .util import ANALYSIS, LAB, safe_name, sha256_file

ROOT = Path(os.environ.get("MOTIONLAB_TEMPLATES_ROOT") or (ANALYSIS / "templates"))
MOTION = LAB / "tools" / "overlays" / "motion"          # the rebuilt templates (MotionLab's own, in the repo)
VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv", ".m4v", ".gif"}
STILL_FRAMES = 15        # a capture shorter than this is a picture, not a motion
DIFF_LEVEL = 12          # grey levels (0-255) a pixel must change by to count
MOVE_SHARE = 0.002       # a frame moves when over 0.2 % of the picture changed
CUT_SHARE = 0.45         # over 45 % at once = a scene change
GAP_FRAMES = 2           # still frames inside one move
HOLD_FRAMES = 6          # a hold = at least this many still frames
ALIVE_SHARE = 0.0002     # a "still" frame with this much change is a drift / pulse, not frozen
PAGE = 8                 # clips per overview page


def root() -> Path:
    return Path(os.environ.get("MOTIONLAB_TEMPLATES_ROOT") or ROOT)


def rel(p: Path) -> str:
    try:
        return Path(p).resolve().relative_to(LAB.resolve()).as_posix()
    except ValueError:
        return str(p)


def guard(p: Path) -> Path:
    """Every write stays inside the pack's folder under ROOT (never next to the clips)."""
    p, r = Path(p).resolve(), root().resolve()
    if r != p and r not in p.parents:
        raise PermissionError(f"templates write only inside {r} (not {p})")
    return p


def humanise(slug: str) -> str:
    s = re.sub(r"[-_]+", " ", slug).strip()
    return (s[:1].upper() + s[1:]) if s else slug


def split_name(stem: str, pack: str) -> tuple[str, str, str]:
    """'swishy__text__good-mood' -> id 'text__good-mood', kind 'text', slug 'good-mood' (no '__': kind 'other')."""
    parts = stem.split("__")
    if parts and parts[0].lower() == pack.lower():
        parts = parts[1:]
    if len(parts) >= 2:
        kind, slug = parts[0], "__".join(parts[1:])
    else:
        kind, slug = "other", parts[0] if parts else stem
    kind = safe_name(kind).lower() or "other"
    slug = safe_name(slug) or "clip"
    return f"{kind}__{slug}", kind, slug


def packs() -> list[str]:
    r = root()
    return sorted(p.parent.name for p in r.glob("*/pack.json")) if r.is_dir() else []


def load_pack(pack: str) -> dict | None:
    p = root() / safe_name(pack).lower() / "pack.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def load_cards(pack: str) -> dict:
    p = root() / safe_name(pack).lower() / "cards.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("cards", {}) if p.exists() else {}
    except (OSError, ValueError):
        return {}


def verify(pack: str) -> list[str]:
    """The clips whose SHA-256 differs from the one recorded on the first read (or that are gone)."""
    d = load_pack(pack) or {}
    bad = []
    for it in d.get("items", []):
        p = LAB / it["file"]
        if not p.exists():
            bad.append(f"{it['file']} (gone)")
        elif sha256_file(p) != it.get("sha256"):
            bad.append(it["file"])
    return bad


# ----------------------------------------------------------------------------- the library (rebuilt templates)
def library() -> list[dict]:
    """The Motion Graphics library: every rebuilt template (tools\\overlays\\motion\\<id>\\template.json + index.html)."""
    out = []
    for p in sorted(MOTION.glob("*/template.json")) if MOTION.is_dir() else []:
        try:
            t = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        idx = p.parent / "index.html"
        if not idx.exists():
            continue
        t["id"] = p.parent.name
        t["folder"] = rel(p.parent)
        t["logos"] = "assets/logos/logos.js" in idx.read_text(encoding="utf-8", errors="replace")   # draws library logos
        out.append(t)
    return out


_WORD = re.compile(r"[a-z0-9]+")
_STOP = set("a an the and or of to in on for with my your our it its is be that this from by at as like want video "
            "videos make made about some".split())


def _words(s: str) -> list[str]:
    return [w for w in _WORD.findall((s or "").lower()) if w not in _STOP and len(w) > 1]


def pick(want: str, n: int = 6, kinds: list[str] | None = None) -> list[dict]:
    """The rebuilt templates that fit the user's words best (Generate starting blind): each template's name, kind,
    what, use_for and tags against the words; the score is the matched words' weight. Always returns up to n - the
    best matches first, then the most general ones (use_for "any") so a blind start never has nothing. Words that name
    logos of the logo library ("Claude, Midjourney and Suno") lift the templates that can draw them (logos.py)."""
    from . import logos as LG
    lib = [t for t in library() if not kinds or t.get("kind") in kinds]
    W = set(_words(want))
    brands = [lg["name"] for lg in LG.find(want, 12) if lg["score"] >= 6]          # a logo named by its name or id
    stems = {w[:5] for w in W if len(w) >= 5}
    scored = []
    for t in lib:
        hay = {"name": _words(t.get("name", "")), "kind": _words(t.get("kind", "")),
               "use": _words(" ".join(t.get("use_for", []))), "tags": _words(" ".join(t.get("tags", []))),
               "what": _words(t.get("what", ""))}
        wt = {"name": 3, "kind": 2, "use": 3, "tags": 2, "what": 1}
        s, hits = 0.0, set()
        for k, ws in hay.items():
            for w in ws:
                if w in W or (len(w) >= 5 and w[:5] in stems):
                    s += wt[k]
                    hits.add(w)
        if brands and t.get("logos"):
            s += 3 + 2 * (t.get("kind") == "logo")
            hits.add("logos: " + ", ".join(brands[:4]))
        scored.append((s, t.get("general", 0), t, sorted(hits)))
    scored.sort(key=lambda x: (-x[0], -x[1], x[2]["id"]))
    return [{**t, "score": round(s, 1), "matched": hits} for s, _, t, hits in scored[:n]]


def catalog() -> dict:
    """What the app's Motion Graphics page shows: the library + every pack's clips with Claude's cards and which
    rebuilt template came from which clip."""
    lib = library()
    built_from = {}
    for t in lib:
        for f in t.get("learned_from", []):
            built_from.setdefault(f"{f.get('pack')}/{f.get('clip')}", []).append(t["id"])
    out = {"library": lib, "packs": []}
    for pk in packs():
        d = load_pack(pk) or {}
        cards = load_cards(pk)
        items = []
        for it in d.get("items", []):
            mo = it.get("motion", {})
            items.append({k: it.get(k) for k in ("n", "id", "kind", "slug", "name", "file", "frames", "fps", "width",
                                                 "height", "seconds", "still", "colours", "poster_f")}
                         | {"moves": len(mo.get("moves", [])), "loops": mo.get("loops"),
                            "moving_share": mo.get("moving_share"), "eases": mo.get("eases"),
                            "alive_in_holds": mo.get("alive_in_holds"),
                            "card": cards.get(it["id"]), "built": built_from.get(f"{pk}/{it['id']}", []),
                            "sheet": f"analysis/templates/{pk}/{it['id']}/sheet.png" if root() == ROOT else None,
                            "poster": f"analysis/templates/{pk}/{it['id']}/poster.jpg" if root() == ROOT else None})
        out["packs"].append({"pack": pk, "source": d.get("source"), "read": d.get("read"), "kinds": d.get("kinds", {}),
                             "items": items, "cards": len(cards), "changed": d.get("changed", [])})
    return out


def describe(it: dict) -> list[str]:
    """One clip's numbers in words, frame + timecode on every timestamp."""
    mo, fps = it["motion"], it["fps"]
    out = [f"#{it['n']} {it['id']} - {it['frames']} frames at {fps:g} fps ({it['seconds']:.2f} s), "
           f"{it['width']}x{it['height']}" + (" - a still capture" if it["still"] else "")]
    out.append(f"  moving {round(100 * mo['moving_share'])} % of the time, {len(mo['moves'])} moves "
               f"({mo['moves_per_s']}/s), median move {mo['median_move_frames']} f, longest hold "
               f"{mo['longest_hold_frames']} f, holds alive {mo['alive_in_holds']}, loops {mo['loops']}")
    for m in mo["moves"][:12]:
        b = m["box_pct"]
        out.append(f"  move f{m['start']}-f{m['end']} ({m['start_tc']}-{m['end_tc']}) {m['frames']} f, fastest "
                   f"f{m['fastest']} ({frame_to_tc(m['fastest'], fps)}), {m['ease']}"
                   + (f", area x {b[0]:.0f}-{b[2]:.0f} % y {b[1]:.0f}-{b[3]:.0f} %" if b else ""))
    if len(mo["moves"]) > 12:
        out.append(f"  ... {len(mo['moves']) - 12} more moves")
    for c in mo["cuts"]:
        out.append(f"  scene change f{c['f']} ({c['tc']})")
    cl = it.get("colours") or {}
    out.append(f"  background {cl.get('background')}, colours "
               + ", ".join(f"{h} {round(100 * s)} %" for h, s in cl.get("main", [])))
    return out
