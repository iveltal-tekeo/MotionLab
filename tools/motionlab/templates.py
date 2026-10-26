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

import hashlib
import json
import os
import re
from pathlib import Path

from .timecode import frame_to_tc
from .util import ANALYSIS, LAB, safe_name, sha256_file

ROOT = Path(os.environ.get("MOTIONLAB_TEMPLATES_ROOT") or (ANALYSIS / "templates"))
MOTION = LAB / "tools" / "overlays" / "motion"          # the rebuilt templates (MotionLab's own, in the repo)
MG = LAB / "library" / "motion_graphics"               # 2026-10-18: index.json (every template) + local\<pack>\<id>
LOCAL = MG / "local"                                   # = templates learned from the user's own captured clips
#                                                        - this PC only, gitignored, never shared
VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv", ".m4v", ".gif"}
STILL_FRAMES = 15        # a capture shorter than this is a picture, not a motion
DIFF_LEVEL = 12          # grey levels (0-255) a pixel must change by to count
MOVE_SHARE = 0.002       # a frame moves when over 0.2 % of the picture changed
CUT_SHARE = 0.45         # over 45 % at once = a scene change
GAP_FRAMES = 2           # still frames inside one move
HOLD_FRAMES = 6          # a hold = at least this many still frames
ALIVE_SHARE = 0.0002     # a "still" frame with this much change is a drift / pulse, not frozen
PAGE = 8                 # clips per overview page
RECENT_PROJECTS = 5      # pick(): the newest videos whose templates the next one steers away from (2026-10-26)
RECENT_COST = 2.0        # score a template loses per recent video that used it: a weak match rotates out, a strong
#                          one (review-stars for a review) stays on top
NEAR = 0.9               # pick() with a seed: matches less than this apart swap places from video to video


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
    found = [(p, None) for p in sorted(MOTION.glob("*/template.json"))] if MOTION.is_dir() else []
    found += [(p, p.parent.parent.name) for p in sorted(LOCAL.glob("*/*/template.json"))] if LOCAL.is_dir() else []
    for p, pack in found:
        try:
            t = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        idx = p.parent / "index.html"
        if not idx.exists():
            continue
        h = idx.read_text(encoding="utf-8", errors="replace")
        t["id"] = p.parent.name
        t["folder"] = rel(p.parent)
        t["logos"] = "assets/logos/logos.js" in h                    # draws library logos
        t["look_aware"] = "assets/looks/looks.js" in h               # takes the look tokens (motionlab\\looks.py)
        t["local"] = pack is not None                                # learned from the user's own clips: this PC only
        ms = measured(p.parent)                                      # 0.5.3: what the PC measured (tracks, sizes)
        if ms.get("tracks") and not t.get("tracks"):
            t["tracks"] = ms["tracks"]
        if "sizes" in ms:
            t["sizes_ok"] = sorted(s for s, r in ms["sizes"].items() if r.get("ok"))
            t["sizes_bad"] = sorted(s for s, r in ms["sizes"].items() if not r.get("ok"))
        if pack:
            t["pack"] = pack
            m = p.parent / "match.json"
            if m.exists():
                try:
                    mj = json.loads(m.read_text(encoding="utf-8"))
                    t["fidelity"] = {k: mj.get(k) for k in ("score", "status", "correlation", "duration_off")}
                except (OSError, ValueError):
                    pass
            t["preview"] = rel(p.parent / "preview.mp4") if (p.parent / "preview.mp4").exists() else None
        out.append(t)
    return out


# ------------------------------------------------------------------------- landing a move on a frame (0.5.3 A1)
def measured(folder: Path) -> dict:
    """<template>\\measured.json - what the PC measured on a template, never hand-written (templates.py tracks /
    sizes): {"tracks": [...] (from a plain render, for templates without hand-written tracks), "tracks_date",
    "sizes": {"1080x1920": {"ok", "flags": [...], "date"}}}. A file of its own so template.json stays as written."""
    p = Path(folder) / "measured.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except (OSError, ValueError):
        return {}


def save_measured(folder: Path, **kv) -> dict:
    d = measured(folder) | kv
    (Path(folder) / "measured.json").write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
    return d


def tracks_of(tid: str) -> tuple[list[dict], float]:
    """A template's moves (template.json "tracks": hand-written for the AE templates; else measured.json's, from a
    plain render - `templates.py tracks`) and its own frame rate. Each: name, what, start_f, length_f (+ fastest_f
    when measured)."""
    from . import overlay_settings as OS
    folder = OS.find_graphic(tid)
    t = json.loads((folder / "template.json").read_text(encoding="utf-8")) if (folder / "template.json").exists() else {}
    return t.get("tracks") or measured(folder).get("tracks") or [], float(OS.conf(folder)["fps"])


def find_track(tracks: list[dict], key: str) -> dict:
    """A track by its number (1 = first), its exact name or the first name containing the words."""
    if key.isdigit() and 1 <= int(key) <= len(tracks):
        return tracks[int(key) - 1]
    k = key.lower().strip()
    for tr in tracks:
        if (tr.get("name") or "").lower() == k:
            return tr
    for tr in tracks:
        if k in (tr.get("name") or "").lower() or k in (tr.get("what") or "").lower():
            return tr
    raise ValueError(f"no track '{key}' - the tracks: " + "; ".join(
        f"{i}. {tr.get('name')} f{tr['start_f']}+{tr['length_f']}" for i, tr in enumerate(tracks, 1)))


def land(tracks: list[dict], track: str, at: int, *, start: int | None = None, hit: str = "start", k: float = 1.0,
         shift: int = 0, frames: int | None = None) -> dict:
    """Where a template's layer starts and which of its frames it starts from (the plan layer's "in") so a move
    lands on plan frame `at`: hit = the move's start (default), its fastest frame (measured tracks) or its last
    frame. k = the copy's fps / the template's (a retimed copy), shift = frames a timing setting moved everything by
    (a "start" setting changed from its default). start = the layer's first plan frame (a cut); without it the
    layer starts so the template plays from its frame 0. Pure arithmetic: SMASH's hit at f80, a cut at f136, the beat
    f172 -> in 44."""
    tr = find_track(tracks, track)
    if hit == "end":
        h = tr["start_f"] + tr["length_f"] - 1
    elif hit == "peak":
        h = tr.get("fastest_f", tr["start_f"])
    else:
        h = tr["start_f"]
    h = round(h * k) + shift
    asked = start
    if start is None:
        start, inn = at - h, 0
    else:
        inn = h - (at - start)
    if start < 0:                    # the move comes too early in the template: skip its first frames instead
        inn, start = inn - start, 0
    if inn < 0:                      # the cut is before the template's frame 0 could reach the beat: start later
        start, inn = start - inn, 0
    out = {"track": tr.get("name"), "hit": hit, "template_frame": h, "at": at, "start": start, "in": inn,
           "moved_from": asked if asked is not None and asked != start else None}
    if frames:
        out["end"] = start + frames - inn - 1
    return out


def land_target(target: str, track: str, at: int, start: int | None = None, hit: str = "start") -> dict:
    """land() for a template id (its own rate and length) or a copy of one in a project (overlay.py new --from: the
    copy's rate, its length, its "start" setting's change from the default)."""
    from . import overlay_settings as OS
    p = Path(target)
    if (p / "overlay.json").exists():
        c = OS.conf(p)
        tid = c.get("from")
        if not tid:
            raise ValueError(f"{p.name} is not a copy of a template (overlay.json has no \"from\")")
        tracks, fps_t = tracks_of(tid)
        decl = {d["id"]: d for d in OS.declared(p)}
        shift = 0
        if "start" in decl:
            try:
                shift = round(float(OS.values(p).get("start", decl["start"].get("default", 0)))
                              - float(decl["start"].get("default", 0)))
            except (TypeError, ValueError):
                shift = 0
        k, frames = float(c["fps"]) / fps_t, int(c["frames"])
    else:
        tracks, fps_t = tracks_of(target)
        k, shift, frames = 1.0, 0, int(OS.conf(OS.find_graphic(target))["frames"])
        tid = target
    if not tracks:
        raise ValueError(f"{tid} has no tracks yet - measure them: templates.py tracks {tid}")
    return land(tracks, track, at, start=start, hit=hit, k=k, shift=shift, frames=frames) | {"template": tid}


def land_line(r: dict, fps: float) -> str:
    """One line for Claude: where the layer goes and what lands where, frame + timecode."""
    s = (f"'{r['track']}' ({r['hit']}, template f{r['template_frame']}) lands on f{r['at']} ({frame_to_tc(r['at'], fps)}): "
         f"layer start f{r['start']} ({frame_to_tc(r['start'], fps)}), in {r['in']}")
    if r.get("end") is not None:
        s += f", end f{r['end']} ({frame_to_tc(r['end'], fps)})"
    if r.get("moved_from") is not None:
        s += f" - starts {r['start'] - r['moved_from']} f after the cut f{r['moved_from']} (the move comes sooner than that)"
    return s


# ------------------------------------------------------------------- local templates: spec, progress, index (2026-10-18)
def local_folder(tid: str) -> Path | None:
    hits = sorted(LOCAL.glob(f"*/{tid}/template.json")) if LOCAL.is_dir() else []
    return hits[0].parent if hits else None


def spec(folder: Path) -> dict:
    """spec.json of a local template: what Generate and the user read - duration, canvas, tracks (start, length,
    easing), text slots, media slots, tags, category, fidelity, the reference clip. Made from template.json +
    overlay.json + the declared settings + match.json (one source each)."""
    from . import overlay_settings as OS
    folder = Path(folder)
    t = json.loads((folder / "template.json").read_text(encoding="utf-8"))
    c = OS.conf(folder)
    fps, n = float(c["fps"]), int(c["frames"])
    decl = {d["id"]: d for d in OS.declared(folder)}
    m = json.loads((folder / "match.json").read_text(encoding="utf-8")) if (folder / "match.json").exists() else {}
    tracks = [{"name": x.get("name"), "what": x.get("what", ""), "start_f": x["start_f"], "length_f": x["length_f"],
               "start": f"f{x['start_f']} ({frame_to_tc(x['start_f'], fps)})",
               "length_s": round(x["length_f"] / fps, 3), "easing": x.get("easing", "")} for x in t.get("tracks", [])]
    return {"id": folder.name, "name": t.get("name"), "category": t.get("category"), "kind": t.get("kind"),
            "what": t.get("what"), "use_for": t.get("use_for", []), "tags": t.get("tags", []),
            "duration_s": round(n / fps, 3), "frames": n, "fps": fps,
            "canvas": {"width": int(c["width"]), "height": int(c["height"]), "any_size": True},
            "tracks": tracks, "core_points": t.get("core_points"),
            "text_slots": [{"id": s, "label": decl.get(s, {}).get("label", s), "default": decl.get(s, {}).get("default")}
                           for s in t.get("text_slots", [])],
            "media_slots": t.get("media_slots", []),
            "look_aware": "assets/looks/looks.js" in (folder / "index.html").read_text(encoding="utf-8"),
            "fidelity": {k: m.get(k) for k in ("score", "status", "correlation", "duration_ref_s", "duration_render_s",
                                               "duration_off")} if m else None,
            "reference_clip": t.get("reference_clip"), "reference_partial": t.get("reference_partial", False),
            "learned_from": t.get("learned_from", []), "pack": folder.parent.name}


def progress_path(pack: str) -> Path:
    return LOCAL / pack / "progress.json"


def progress(pack: str) -> dict:
    p = progress_path(pack)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"pack": pack, "templates": {}}


def set_progress(pack: str, tid: str, **kv) -> dict:
    """progress.json: one row per template - clips (the reference clips it stands for), status (building / ok /
    needs-work), score, passes (improvement passes after the first verify), updated. Finished rows are never redone."""
    import datetime as _dt
    d = progress(pack)
    row = d["templates"].setdefault(tid, {})
    row.update(kv)
    row["updated"] = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    d["updated"] = row["updated"]
    progress_path(pack).parent.mkdir(parents=True, exist_ok=True)
    progress_path(pack).write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
    return row


def write_index() -> Path:
    """library\\motion_graphics\\index.json: every template (MotionLab's + this PC's local ones) in one list - id,
    name, kind, category, local, look-aware, slots, fidelity, folder."""
    rows = []
    for t in library():
        ms = t.get("media_slots", [])
        rows.append({"id": t["id"], "name": t.get("name"), "kind": t.get("kind"), "category": t.get("category"),
                     "local": t.get("local", False), "pack": t.get("pack"), "look_aware": t.get("look_aware", False),
                     "text_slots": t.get("text_slots"), "media_slots": len(ms), "needs_media": bool(ms),
                     "core_points": t.get("core_points"), "fidelity": t.get("fidelity"),
                     "tracks": len(t.get("tracks") or []), "sizes_ok": t.get("sizes_ok"), "sizes_bad": t.get("sizes_bad"),
                     "folder": t["folder"]})
    MG.mkdir(parents=True, exist_ok=True)
    p = MG / "index.json"
    p.write_text(json.dumps({"_comment": "Every Motion Graphics template (tools\templates.py index). local = learned "
                                         "from this PC's own clips (library\\motion_graphics\\local, never shared).",
                             "templates": rows}, indent=1, ensure_ascii=False), encoding="utf-8")
    return p


_WORD = re.compile(r"[a-z0-9]+")
_STOP = set("a an the and or of to in on for with my your our it its is be that this from by at as like want video "
            "videos make made about some "
            # 2026-10-26, words that matched by accident ("Wake up early" -> a bar chart that grows up, "a short about
            # discipline" -> every "short line"): fillers and formats, no picture of their own
            "up do does every everything one two three then than out into onto over while each another them they you "
            "we us me so very all just get can will now new first last short shorts reel reels what when who which "
            "where why how thing things".split())
_KEEP = {"news", "this", "plus", "bus", "status", "focus", "bonus", "canvas", "series"}
COMMON = 0.10            # pick(): a word in more than this share of the templates counts less (down to a quarter)


def _words(s: str) -> list[str]:
    return [w for w in _WORD.findall((s or "").lower()) if w not in _STOP and len(w) > 1]


def _stem(w: str) -> str:
    """A word without its ending (2026-10-26, in place of a 5-letter prefix that matched stream with streak): tips ->
    tip, counting / counts -> count, stories -> story, typed / typing / type -> typ, dropped -> drop."""
    if len(w) <= 3 or w in _KEEP or w.endswith(("ss", "us", "is")):
        return w
    for suf in ("ies", "ing", "ed", "es", "s"):
        b = w[:-len(suf)]
        if not w.endswith(suf) or len(b) < 3 or (suf == "es" and not b.endswith(("ch", "sh", "x", "z"))):
            continue
        if suf in ("ing", "ed") and (not re.search(r"[aeiouy]", b) or b.endswith("e")):
            continue                                   # string, spring, speed keep theirs
        w = b + "y" if suf == "ies" else b[:-1] if suf in ("ing", "ed") and len(b) >= 4 and b[-1] == b[-2] \
            and b[-1] in "bdgmnpt" else b
        break
    return w[:-1] if w.endswith("e") and len(w) > 3 else w


def jitter(seed: str, tid: str) -> float:
    """0-1, the same for the same seed and template: a video's own order among near-equal choices (no Math.random)."""
    return int(hashlib.md5(f"{seed}|{tid}".encode("utf-8")).hexdigest()[:8], 16) / 16 ** 8


def recent(projects: int = RECENT_PROJECTS, skip: str | None = None) -> dict[str, int]:
    """The templates the newest videos used (2026-10-26, so one video's picks are not the next one's): every
    project's build\\overlays\\*\\overlay.json "from" - of the newest `projects` projects (by their newest graphic), how
    many used each template. skip = the project being made (its own versions do not count)."""
    rows = []
    for ov in (LAB / "projects").glob("*/build/overlays"):
        if ov.parents[1].name == skip:
            continue
        used, newest = set(), 0.0
        for o in ov.glob("*/overlay.json"):
            try:
                c = json.loads(o.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(c.get("from"), str):
                used.add(c["from"])
                newest = max(newest, o.stat().st_mtime)
        if used:
            rows.append((newest, used))
    out: dict[str, int] = {}
    for _, used in sorted(rows, key=lambda r: -r[0])[:projects]:
        for tid in used:
            out[tid] = out.get(tid, 0) + 1
    return out


def pick(want: str, n: int = 6, kinds: list[str] | None = None, also: str = "", used: dict[str, int] | None = None,
         seed: str | None = None) -> list[dict]:
    """The rebuilt templates that fit the user's words best (Generate starting blind): each template's name, kind,
    what, use_for and tags against the words; the score is the matched words' weight. Always returns up to n - the
    best matches first, then the most general ones (use_for "any") so a blind start never has nothing. Words that name
    logos of the logo library ("Claude, Midjourney and Suno") lift the templates that can draw them (logos.py).
    2026-10-26, variety: `also` = words around these (the request around a scene's line) that count half; `used` =
    recent() - each recent video that used a template costs it RECENT_COST; `seed` (a video's name) = matches under
    NEAR apart and equally general fallbacks in that video's own order. Without them, the order is as before."""
    from . import logos as LG
    lib = [t for t in library() if not kinds or t.get("kind") in kinds]
    W = {_stem(w) for w in _words(want)}
    A = {_stem(w) for w in _words(also)} - W
    brands = [lg["name"] for lg in LG.find(f"{want} {also}", 12) if lg["score"] >= 6]   # a logo named by name or id
    hays, df = [], {}
    for t in lib:
        hay = {"name": _words(t.get("name", "")), "kind": _words(t.get("kind", "")),
               "use": _words(" ".join(t.get("use_for", []))), "tags": _words(" ".join(t.get("tags", []))),
               "what": _words(t.get("what", ""))}
        hays.append(hay)
        for st in {_stem(w) for ws in hay.values() for w in ws}:
            df[st] = df.get(st, 0) + 1
    many = max(1.0, COMMON * len(lib))                  # "title" is in 78 templates: it says little about which one
    scored = []
    for t, hay in zip(lib, hays):
        wt = {"name": 3, "kind": 2, "use": 3, "tags": 2, "what": 1}
        s, hits = 0.0, set()
        for k, ws in hay.items():
            for w in ws:
                st = _stem(w)
                if st in W or st in A:
                    s += wt[k] * (1 if st in W else 0.5) * max(0.25, min(1.0, many / df[st]))
                    hits.add(w)
        if brands and t.get("logos"):
            s += 3 + 2 * (t.get("kind") == "logo")
            hits.add("logos: " + ", ".join(brands[:4]))
        u = (used or {}).get(t["id"], 0)
        j = jitter(seed, t["id"]) if seed else 0.0
        scored.append((s - RECENT_COST * u + (NEAR * j if s > 0 else 0), t.get("general", 0) + 0.3 * j, t,
                       sorted(hits), s, u))
    scored.sort(key=lambda x: (-x[0], -x[1], x[2]["id"]))
    return [{**t, "score": round(s, 1), "matched": hits, **({"recent": u} if u else {})}
            for _, _, t, hits, s, u in scored[:n]]


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
