"""Everything the app shows, read from the lab folders. Read-only, except the user's verdicts
(analysis\\<name>\\feedback\\verdicts.json + exported MOTIONLAB FEEDBACK files) and library picks
(projects\\<name>\\build\\library_picks.json). Deleting is trash.py (the user's Delete buttons)."""
from __future__ import annotations

import datetime
import json
import os
import re
import threading
import time
from pathlib import Path

from motionlab import taxonomy
from motionlab import knowledge as KN
from motionlab.styles import fmt as video_format, label as style_label
from motionlab.timecode import frame_to_tc
from motionlab.util import ANALYSIS, LAB

PROJECTS = LAB / "projects"
LIBRARY = LAB / "library"
DOCS = LAB / "docs"
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".m4v", ".avi", ".webm", ".mts", ".mxf"}
AUDIO_EXT = {".mp3", ".m4a", ".wav", ".aac", ".flac", ".ogg"}
_cache: dict[str, tuple[float, object]] = {}
_lock = threading.Lock()


def rel(p: Path | str) -> str | None:
    """Lab-relative path with forward slashes (what /files/ serves), or None if outside the lab."""
    try:
        return Path(p).resolve().relative_to(LAB).as_posix()
    except (ValueError, OSError):
        return None


def read_json(p: Path, default=None):
    """JSON file, cached by modification time (events.json is ~0.6 MB)."""
    try:
        m = p.stat().st_mtime
    except OSError:
        return default
    key = str(p)
    with _lock:
        hit = _cache.get(key)
        if hit and hit[0] == m:
            return hit[1]
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default
    with _lock:
        _cache[key] = (m, obj)
    return obj


def write_json_atomic(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, p)


def stamp(t: float | None = None) -> str:
    return datetime.datetime.fromtimestamp(t or time.time()).strftime("%Y-%m-%d %H:%M")


def human(n: float | None) -> str:
    """Bytes in decimal units, like the app shows them (1.2 GB)."""
    if n is None:
        return "-"
    units, i = ["B", "KB", "MB", "GB", "TB"], 0
    while n >= 1000 and i < 4:
        n /= 1000
        i += 1
    return f"{n:.0f} {units[i]}" if n >= 100 or i == 0 else f"{n:.1f} {units[i]}"


def safe_name(name: str) -> str:
    """A folder name from a URL: no separators, no '..'."""
    if not re.fullmatch(r"[\w.\- \[\]()&'+,]+", name or "") or ".." in name:
        raise ValueError(f"bad name: {name!r}")
    return name


# ================================================================================================= references
def verdicts_path(name: str) -> Path:
    return ANALYSIS / safe_name(name) / "feedback" / "verdicts.json"


def load_verdicts(name: str) -> dict:
    v = read_json(verdicts_path(name), None) or {}
    return {"events": v.get("events", {}), "cuts": v.get("cuts", {}), "misses": v.get("misses", {}),
            "missed": v.get("missed", ""), "updated": v.get("updated")}


def save_verdicts(name: str, body: dict, by_user: bool = False) -> dict:
    """Write verdicts.json. by_user = the app's own save (the user changed something): "changed" (epoch seconds) is
    when the user last changed it - an import of pasted feedback by Claude keeps it, so the workflow still knows the
    feedback was applied."""
    d = ANALYSIS / safe_name(name)
    if not (d / "events.json").exists():
        raise FileNotFoundError(name)
    old = read_json(verdicts_path(name), None) or {}
    clean = {"events": {}, "cuts": {}, "misses": {}, "missed": str(body.get("missed", ""))[:20000]}
    for sec in ("events", "cuts"):
        for k, s in (body.get(sec) or {}).items():
            if not re.fullmatch(r"[EC]\d{1,5}", k) or not isinstance(s, dict):
                continue
            v = s.get("v", "")
            v = v if v in ("correct", "partly", "wrong") else ""
            note = str(s.get("note", ""))[:4000]
            lib = bool(s.get("library"))
            if v or note.strip() or lib:
                clean[sec][k] = {"v": v, "note": note, **({"library": True} if lib else {})}
    # possible misses (events.json near_misses), by frame: the user's "it's an effect" / "not an effect"
    for k, s in (body.get("misses") or {}).items():
        if re.fullmatch(r"\d{1,7}", str(k)) and isinstance(s, dict):
            v = s.get("v", "") if s.get("v") in ("effect", "none") else ""
            note = str(s.get("note", ""))[:4000]
            if v or note.strip():
                clean["misses"][str(k)] = {"v": v, "note": note}
    ev = read_json(d / "events.json", {})
    clean.update(analysis_id=ev.get("analysis_id"), updated=stamp(),
                 changed=round(time.time(), 1) if by_user else old.get("changed"))
    write_json_atomic(verdicts_path(name), clean)
    return clean


def feedback_text(name: str) -> str:
    """The MOTIONLAB FEEDBACK text tools\\feedback.py parses (same format as report.html's button)."""
    d = ANALYSIS / safe_name(name)
    ev = read_json(d / "events.json", {})
    S = load_verdicts(name)
    fps = ev.get("video", {}).get("fps", 25)
    L = ["MOTIONLAB FEEDBACK v1",
         f"video: {Path(ev.get('source', {}).get('path', name)).name} | analysis: {ev.get('analysis_id')} | "
         f"fps: {fps:g} | frames are 0-based",
         f"report: {d / 'report.html'}", "--- events ---"]
    un = []
    for e in ev.get("events", []):
        st = S["events"].get(e["id"], {})
        note = (st.get("note") or "").strip()
        if st.get("library"):
            note = ("[save to library] " + note).strip()
        if not st.get("v") and not note:
            un.append(e["id"])
            continue
        fin = e.get("final") or {}
        s = (f"{(st.get('v') or 'note').upper()} | {e['id']} | {fin.get('type', e['type'])} | "
             f"f{e['start']}-{e['end']} ({e['tc_start']} - {e['tc_end']})")
        if note:
            s += " | note: " + re.sub(r"\s*\n\s*", " / ", note)
        L.append(s)
    if un:
        L.append("(no verdict: " + ", ".join(un) + ")")
    L.append("--- hard cuts ---")
    cl = []
    for c in ev.get("hard_cuts", []):
        st = S["cuts"].get(c["id"], {})
        note = (st.get("note") or "").strip()
        if st.get("v") or note:
            one = re.sub(r"\s*\n\s*", " / ", note)
            cl.append(f"{(st.get('v') or 'note').upper()} | {c['id']} | hard cut | f{c['frame']} ({c['tc']})"
                      + (f" | note: {one}" if note else ""))
    L.extend(cl or ["(all hard cuts accepted / not reviewed)"])
    ml = []
    for n in ev.get("near_misses") or []:
        st = S["misses"].get(str(n["frame"]), {})
        note = re.sub(r"\s*\n\s*", " / ", (st.get("note") or "").strip())
        if st.get("v") or note:
            ml.append(f"{({'effect': 'EFFECT', 'none': 'NOT AN EFFECT'}).get(st.get('v'), 'NOTE')} | "
                      f"f{n['frame']} ({n.get('tc') or frame_to_tc(n['frame'], fps)})" + (f" | note: {note}" if note else ""))
    if ev.get("near_misses"):
        L.append("--- possible misses ---")
        L.extend(ml or ["(none checked)"])
    L.append("--- missed effects / general notes ---")
    L.append(S["missed"].strip() or "(none)")
    L.append("END")
    return "\n".join(L)


def export_feedback(name: str) -> dict:
    text = feedback_text(name)
    p = ANALYSIS / safe_name(name) / "feedback" / f"app_{time.strftime('%Y-%m-%d_%H-%M-%S')}.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text + "\n", encoding="utf-8")
    return {"text": text, "path": str(p), "rel": rel(p)}


def review_prompt(video: str, analysis: str | None = None) -> str:
    """The hand-off for Claude's check of one reference (the /analyze-reference skill skips the lab pass when it is
    already done)."""
    return f'/analyze-reference "{video}"' + (f" - the lab pass is done: analysis\\{analysis}" if analysis else "")


# the workflow of one reference: download > lab pass > Claude checks > your verdicts > feedback to Claude > share
FLOW = ("download", "lab", "claude", "verdicts", "feedback", "share")
_pend: dict = {"sig": {}, "names": set(), "state": None}
_plock = threading.Lock()


def _mtimes(*files: Path) -> tuple:
    out = []
    for p in files:
        try:
            out.append(p.stat().st_mtime_ns)
        except OSError:
            out.append(None)
    return tuple(out)


def share_pending() -> set:
    """Analyses whose knowledge card is new or changed since the last Share. A card is rebuilt only when a file it is
    made of changed (its analysis' events / meta / verdicts, the lessons, refs\\downloads.json)."""
    common = _mtimes(KN.SHARED_LESSONS, KN.LOCAL_LESSONS, KN.DOWNLOADS)
    with _plock:
        changed = []
        for d in sorted(ANALYSIS.iterdir()) if ANALYSIS.exists() else []:
            sig = common + _mtimes(d / "events.json", d / "meta.json", d / "feedback" / "verdicts.json")
            if _pend["sig"].get(d.name) != sig:
                _pend["sig"][d.name] = sig
                changed.append(d.name)
        state = _mtimes(KN.SHARED_STATE, KN.LOCAL_REFS)
        if changed or state != _pend["state"]:
            _pend["names"] = {c.get("analysis") for c in KN.pending(changed)["cards"]}
            _pend["state"] = _mtimes(KN.SHARED_STATE, KN.LOCAL_REFS)
        return set(_pend["names"])


def flow(name: str, ev: dict, S: dict, pend: set) -> dict:
    """Where one reference stands in the workflow (FLOW) and its next step. Feedback counts as applied when Claude
    ran tools\\feedback.py (it archives feedback_<time>.txt) after the last change to the verdicts."""
    evs = ev.get("events", [])
    real = [e for e in evs if not (e.get("final") or {}).get("false_alarm")]
    reviewed = sum(1 for e in evs if e.get("review"))
    given = sum(1 for e in real if (S["events"].get(e["id"]) or {}).get("v"))
    misses = [str(n["frame"]) for n in ev.get("near_misses") or []]
    checked = sum(1 for k in misses if (S["misses"].get(k) or {}).get("v"))
    fb = ANALYSIS / name / "feedback"

    def newest(pattern: str) -> float:
        return max((p.stat().st_mtime for p in fb.glob(pattern)), default=0.0) if fb.exists() else 0.0

    vp = verdicts_path(name)                    # when the user last changed a verdict (older files: their time)
    vt = ((read_json(vp, None) or {}).get("changed") or vp.stat().st_mtime) if vp.exists() else 0.0
    applied, exported = newest("feedback_*.txt"), newest("app_*.txt")
    done = {"download": True, "lab": True, "claude": reviewed >= len(evs),
            "verdicts": given >= len(real) and checked >= len(misses),
            "feedback": applied >= vt if vt else not real, "share": name not in pend}
    return {"done": [k for k in FLOW if done[k]], "next": next((k for k in FLOW if not done[k]), None),
            "reviewed": reviewed, "events": len(evs), "real": len(real), "given": given,
            "misses": len(misses), "misses_checked": checked, "sent": bool(vt) and exported >= vt > applied}


def list_references(include_tests: bool = False) -> list[dict]:
    out = []
    if not ANALYSIS.exists():
        return out
    pend = share_pending()
    for d in sorted(ANALYSIS.iterdir(), key=lambda p: p.name.lower()):
        ev = read_json(d / "events.json", None) if d.is_dir() else None
        if not ev:
            continue
        test = d.name.startswith("synthetic_")
        if test and not include_tests:
            continue
        v = ev.get("video", {})
        evs = ev.get("events", [])
        S = load_verdicts(d.name)
        src = ev.get("source", {}).get("path", "")
        thumb = None                       # a real frame (an effect ~40 % in) is easier to recognise than a chart
        for e in sorted(evs, key=lambda e: abs(e.get("key", e["start"]) - 0.4 * (v.get("frames") or 0)))[:12]:
            p = d / "frames" / f"f{int(e.get('key', e['start'])):06d}.jpg"
            if p.exists():
                thumb = rel(p)
                break
        for name in ("overview_dark.png", "overview.png"):
            if not thumb and (d / name).exists():
                thumb = rel(d / name)
        out.append({
            "name": d.name, "title": Path(src).stem if src else d.name, "test": test,
            "fps": v.get("fps"), "frames": v.get("frames"), "duration_s": v.get("duration_s"),
            "width": v.get("width"), "height": v.get("height"), "bpm": (ev.get("audio") or {}).get("bpm"),
            "events": len(evs), "reviewed": sum(1 for e in evs if e.get("review")),
            "verdicts": sum(1 for s in S["events"].values() if s.get("v")),
            "cuts": len(ev.get("hard_cuts", [])), "generated": ev.get("generated"), "thumb": thumb,
            **_kind(d.name, ev, v),
            "report": rel(d / "report.html") if (d / "report.html").exists() else None,
            "feedback_files": sorted(p.name for p in (d / "feedback").glob("*.txt")) if (d / "feedback").exists() else [],
            "source": src, "flow": flow(d.name, ev, S, pend), "review_prompt": review_prompt(src or d.name, d.name),
        })
    return out


def _kind(name: str, ev: dict, v: dict) -> dict:
    """Category, tags, link, format and pacing of an analysis (for the cards, filters and the analysis page)."""
    m = KN.meta(name, ev)
    return {"category": m["category"], "category_label": style_label(m["category"]), "tags": m["tags"],
            "url": m["url"], "platform": m["platform"],
            "style": m["category"], "style_label": style_label(m["category"]),            # v0.2.0 names
            "format": video_format(v.get("display_width") or v.get("width"), v.get("display_height") or v.get("height"),
                                   v.get("duration_s")),
            "pacing": KN.pacing(ev)}


def reference(name: str) -> dict:
    d = ANALYSIS / safe_name(name)
    ev = read_json(d / "events.json", None)
    if not ev:
        raise FileNotFoundError(name)
    v = ev.get("video", {})
    fps = float(v.get("fps") or 25)
    src = ev.get("source", {}).get("path", "")
    proxy = d / "proxy_cfr.mp4"
    play = rel(proxy) if proxy.exists() else rel(src) if src and Path(src).exists() else None
    evs = []
    for e in ev.get("events", []):
        fin = e.get("final") or {}
        auto = e.get("auto") or {}
        rv = e.get("review") or {}
        t = fin.get("type", e.get("type"))
        evs.append({
            "id": e["id"], "type": t, "label": taxonomy.label(t), "family": taxonomy.family(t),
            "auto_type": auto.get("type", e.get("type")), "auto_label": taxonomy.label(auto.get("type", e.get("type"))),
            "relabelled": bool(rv) and rv.get("type") not in (None, auto.get("type")),
            "start": e["start"], "end": e["end"], "key": e.get("key", e["start"]),
            "tc_start": e.get("tc_start") or frame_to_tc(e["start"], fps),
            "tc_end": e.get("tc_end") or frame_to_tc(e["end"], fps),
            "what": fin.get("what") or auto.get("what", ""), "auto_what": auto.get("what", ""),
            "evidence": (fin.get("evidence") or auto.get("evidence") or [])[:8],
            "timing": fin.get("timing", ""), "on_beat": fin.get("on_beat"), "easing": fin.get("easing", ""),
            "origin": fin.get("origin", ""), "confidence": fin.get("confidence", ""),
            "rebuild": fin.get("rebuild", ""), "false_alarm": fin.get("false_alarm", False),
            "stacked": rv.get("stacked", []), "reviewed": bool(rv),
            "sheets": [rel(d / s) for s in e.get("sheets", [])],
            "preview": rel(d / e["preview"]) if e.get("preview") else None,
            "preview_range": e.get("preview_range"),
        })
    au = ev.get("audio") or {}
    return {
        "name": d.name, "title": Path(src).stem if src else d.name, "analysis_id": ev.get("analysis_id"),
        **_kind(d.name, ev, v),
        "generated": ev.get("generated"), "source": src, "source_unchanged": ev.get("source", {}).get("unchanged"),
        "video": {"fps": fps, "frames": v.get("frames"), "duration_s": v.get("duration_s"), "width": v.get("width"),
                  "height": v.get("height"), "vfr": v.get("vfr"), "play": play,
                  "end_tc": frame_to_tc(max(0, int(v.get("frames") or 1) - 1), fps)},
        "audio": {"bpm": au.get("bpm"), "beats": [round(b["frame"], 2) for b in au.get("beats", [])],
                  "downbeats": [round(b["frame"], 2) for b in au.get("beats", []) if b.get("downbeat")],
                  "drops": [{"frame": round(x["frame"]), "tc": x.get("tc")} for x in au.get("drops", [])]},
        "shots": [{"start": s["start"], "end": s["end"]} for s in ev.get("shots", [])],
        "cuts": [{"id": c["id"], "frame": c["frame"], "tc": c["tc"], "kind": c.get("kind"), "on_beat": c.get("on_beat"),
                  "thumb": rel(d / c["thumb"]) if c.get("thumb") else None} for c in ev.get("hard_cuts", [])],
        "events": evs, "families": taxonomy.FAMILIES,
        "near_misses": [{"frame": n["frame"], "tc": n["tc"], "why": n.get("why", ""), "checked": n.get("checked", ""),
                         "frames": [rel(d / f) for f in n.get("frames", []) if (d / f).exists()]}
                        for n in ev.get("near_misses") or []],
        "report": rel(d / "report.html") if (d / "report.html").exists() else None,
        "overview": rel(d / "overview.png") if (d / "overview.png").exists() else None,
        "verdicts": load_verdicts(name),
        "feedback_files": [rel(p) for p in sorted((d / "feedback").glob("*.txt"))] if (d / "feedback").exists() else [],
        "flow": flow(d.name, ev, load_verdicts(name), share_pending()),
        "review_prompt": review_prompt(src or d.name, d.name),
        "projects": [p["name"] for p in list_projects()],
    }


def candidate_videos() -> list[dict]:
    """Videos in refs\\ that have no analysis yet (the 'analyze' page offers them)."""
    done = {Path((read_json(d / "events.json", {}) or {}).get("source", {}).get("path", "")).name.lower()
            for d in ANALYSIS.glob("*") if d.is_dir()}
    out = []
    for p in sorted((LAB / "refs").glob("*")):
        if p.suffix.lower() in VIDEO_EXT:
            out.append({"path": str(p), "name": p.name, "size": p.stat().st_size, "analysed": p.name.lower() in done})
    return out


def waiting() -> list[dict]:
    """Downloads not analysed yet: videos in refs\\ without an analysis, and the audio in refs\\audio\\."""
    files = [Path(c["path"]) for c in candidate_videos() if not c["analysed"]]
    ad = LAB / "refs" / "audio"
    files += [p for p in sorted(ad.glob("*")) if p.is_file() and p.suffix.lower() in AUDIO_EXT] if ad.is_dir() else []
    out = []
    for p in files:
        st, dl = p.stat(), KN.download_info(p.name)
        out.append({"name": p.name, "path": str(p), "rel": rel(p), "size": st.st_size, "modified": stamp(st.st_mtime),
                    "audio": p.suffix.lower() in AUDIO_EXT, "title": dl.get("title"), "url": dl.get("url"),
                    "platform": dl.get("platform")})
    return out


# ================================================================================================= projects
def _plan_info(p: Path) -> dict:
    pl = read_json(p, {}) or {}
    return {"file": p.name, "rel": rel(p), "name": pl.get("name"), "version": p.stem.split("_")[-1],
            "frames": pl.get("frames"), "fps": pl.get("fps"), "width": pl.get("width"), "height": pl.get("height"),
            "layers": len(pl.get("layers", [])), "levels": pl.get("levels", "single"),
            "duration_tc": frame_to_tc(max(0, int(pl.get("frames") or 1) - 1), float(pl.get("fps") or 25)),
            "reference": rel(pl["reference"]) if pl.get("reference") and Path(pl["reference"]).exists() else None}


def _video(p: Path, kind: str) -> dict:
    st = p.stat()
    return {"name": p.name, "rel": rel(p), "size": st.st_size, "modified": stamp(st.st_mtime), "kind": kind}


def list_projects() -> list[dict]:
    out = []
    if not PROJECTS.exists():
        return out
    for d in sorted(PROJECTS.iterdir(), key=lambda p: p.name.lower()):
        if not d.is_dir():
            continue
        b = d / "build"
        clips = [p for p in d.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXT]
        plans = sorted(b.glob("plan_v*.json")) if b.exists() else []
        boards = sorted((b / "boards").glob("*.jpg")) if (b / "boards").exists() else []
        out.append({
            "name": d.name, "clips": len(clips), "footage_bytes": sum(p.stat().st_size for p in clips),
            "plans": [p.stem for p in plans],
            "renders": [p.name for p in sorted(b.glob("*.mp4"))] if b.exists() else [],
            "resolve": sorted(m.name[:-len("_build.json")] for m in (b / "resolve").glob("*_build.json"))
            if (b / "resolve").exists() else [],
            "thumb": rel(boards[0]) if boards else None,
        })
    return out


# rebuild units -> the effect they show (for library picks)
EFFECT_GROUPS = [
    (r"^title_", "Pixel-font title", "boxy red pixel title with glow (Fusion rectangles)"),
    (r"^clock_(intro|big)$", "Seven-segment clock", "grey grainy LED clock, 3:59 -> 4:00 (Fusion polygons)"),
    (r"^clock_logo$", "Strobing logo clock", "small clock in the logo slot, keyed strobe"),
    (r"^clock_red$", "Red LED card", "red LED 04:00 with glow and red vignette"),
    (r"^clock_exit_flash$", "Exit flash", "one-frame flash as a panel leaves"),
    (r"^board_", "Pan board", "panels on one wide board, ONE Transform keyed per frame from the measured pan"),
    (r"^firework", "Firework burst", "Fusion particles: sparks, drag, gravity, glow"),
    (r"^mosaic$", "Mosaic zoom-out", "photo wall zooming out 31.6x to one tile, twinkles + red/black strobes"),
    (r"^grain$", "Film grain", "luma grain as a Linear Light layer"),
    (r"^streaks$", "Light streaks", "thin light streaks, composite Screen"),
    (r"_fade$|^master_fade$", "Fade overlay", "fade to the background grey, keyed per frame"),
    (r"^night_drift$", "Drifting panel", "slow push / drift of one panel"),
    (r"^(c\d_|white_)", "Flash frame / solid", "white or black one-frame solid"),
]


def rebuild_effects(b: Path, timeline: str | None) -> list[dict]:
    if not timeline:
        return []
    man = read_json(b / "resolve" / f"{timeline}_build.json", {}) or {}
    fps = float((read_json(Path(man.get("plan", "")), {}) or {}).get("fps") or 25)
    groups: dict[str, dict] = {}
    for u in man.get("units", []):
        if u["kind"] != "comp":
            continue
        for rx, title, what in EFFECT_GROUPS:
            if re.search(rx, u["name"]):
                g = groups.setdefault(title, {"title": title, "what": what, "units": []})
                g["units"].append({"name": u["name"], "track": u["track"], "start": u["start"], "end": u["end"],
                                   "start_tc": u["start_tc"], "end_tc": u["end_tc"],
                                   "comp": rel(b / "resolve" / "comps" / f"{u['name']}.comp")})
                break
    clips = [c for u in man.get("units", []) if u["kind"] == "clip" for c in u.get("clips", [])]
    if clips:
        groups["Static panel"] = {"title": "Static panel", "what": "cover-fit panel: Edit-page Zoom/Pan/Tilt/Crop + a "
                                  "grade LUT; flash frames = 1-frame cuts with a flash LUT; holds = freeze frames",
                                  "units": [{"name": f"{len(clips)} Edit-page clips", "track": None,
                                             "start": min(c["start"] for c in clips),
                                             "end": max(c["end"] for c in clips),
                                             "start_tc": frame_to_tc(min(c["start"] for c in clips), fps),
                                             "end_tc": frame_to_tc(max(c["end"] for c in clips), fps), "comp": None}]}
    return list(groups.values())


def library_picks_path(name: str) -> Path:
    return PROJECTS / safe_name(name) / "build" / "library_picks.json"


def save_library_picks(name: str, body: dict) -> dict:
    if not (PROJECTS / safe_name(name) / "build").exists():
        raise FileNotFoundError(name)
    picks = {}
    for k, s in (body.get("picks") or {}).items():
        if isinstance(s, dict) and len(k) < 80 and (s.get("pick") or str(s.get("note", "")).strip()):
            picks[k] = {"pick": bool(s.get("pick")), "note": str(s.get("note", ""))[:4000]}
    out = {"picks": picks, "updated": stamp(),
           "how": "Effects the user wants saved to library\\ as a Fusion macro (.setting) + recipe .md. Claude does "
                  "the saving (it needs Resolve); this file is the user's list."}
    write_json_atomic(library_picks_path(name), out)
    return out


def project(name: str) -> dict:
    d = PROJECTS / safe_name(name)
    if not d.is_dir():
        raise FileNotFoundError(name)
    b = d / "build"
    srcs = (read_json(b / "sources.json", {}) or {}).get("sources", {})
    sources = []
    for sid, s in sorted(srcs.items()):
        meta = read_json(b / "cache" / f"{sid}.json", {}) or {}
        p = Path(s["path"])
        sources.append({"id": sid, "name": s["name"], "size": p.stat().st_size if p.exists() else None,
                        "exists": p.exists(), "fps": meta.get("src_fps"), "frames": meta.get("src_frames"),
                        "duration_s": (meta.get("src_frames") or 0) / (meta.get("src_fps") or 1) or None,
                        "resolution": f"{meta.get('src_width')}x{meta.get('src_height')}" if meta else None,
                        "cached": bool(meta.get("complete")), "board": rel(b / "boards" / f"{sid}_01.jpg")
                        if (b / "boards" / f"{sid}_01.jpg").exists() else None})
    plans = [_plan_info(p) for p in sorted(b.glob("plan_v*.json"))] if b.exists() else []
    renders = []
    for p in sorted(b.glob("*.mp4")) if b.exists() else []:
        renders.append(_video(p, "resolve" if "_resolve_" in p.stem else "lab"))
    compares = [_video(p, "compare") for p in sorted((b / "compare").glob("*.mp4"))] if (b / "compare").exists() else []
    verifies = []
    for p in sorted(b.glob("verify_*.json")) if b.exists() else []:
        vj = read_json(p, {}) or {}
        verifies.append({"name": p.stem[len("verify_"):], "render": Path(vj.get("render", "")).name,
                         "hits": vj.get("our_hits"), "keys": vj.get("key_frames"), "luma_corr": vj.get("luma_corr"),
                         "rows": vj.get("rows", [])})
    resolve = []
    for m in sorted((b / "resolve").glob("*_build.json")) if (b / "resolve").exists() else []:
        man = read_json(m, {}) or {}
        tl = man.get("timeline") or m.name[:-len("_build.json")]
        drift = read_json(b / "resolve" / "checks" / f"{tl}_drift.json", None)
        resolve.append({
            "timeline": tl, "project": man.get("project"), "tracks": man.get("tracks"),
            "units": len(man.get("units", [])), "comps": sum(1 for u in man.get("units", []) if u["kind"] == "comp"),
            "clips": sum(len(u.get("clips", [])) for u in man.get("units", [])), "luts": len(man.get("luts", [])),
            "drift": drift, "edits": [rel(p) for p in sorted((b / "resolve" / "edits" / "live").glob("*.comp"))],
            "report": rel(b / "resolve" / "option2_report.md") if (b / "resolve" / "option2_report.md").exists()
            else None, "drp": rel(b / "resolve" / f"{man.get('project')}.drp")
            if (b / "resolve" / f"{man.get('project')}.drp").exists() else None,
            "effects": rebuild_effects(b, tl),
        })
    sheets = [rel(p) for p in sorted((b / "resolve" / "checks").glob("*_sheet_*.jpg"))] \
        if (b / "resolve" / "checks").exists() else []
    picks = read_json(library_picks_path(name), {}) or {}
    return {"name": d.name, "sources": sources, "plans": plans, "renders": renders, "compares": compares,
            "verifies": verifies, "resolve": resolve, "check_sheets": sheets,
            "boards": [rel(p) for p in sorted((b / "boards").glob("*.jpg"))] if (b / "boards").exists() else [],
            "edit_scripts": [rel(p) for p in sorted(b.glob("edit_v*.py"))] if b.exists() else [],
            "library_picks": picks.get("picks", {}), "picks_updated": picks.get("updated")}


# ================================================================================================= library / docs
def library() -> dict:
    items = []
    if LIBRARY.exists():
        # library\<effect>\<effect>.md (+ .setting macros, check.png); README.md is the index, not an effect
        for p in sorted(LIBRARY.glob("*/*.md")):
            if p.stem != p.parent.name:
                continue
            first = next((ln.strip("# ").strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()),
                         p.stem)
            macros = [rel(m) for m in sorted(p.parent.glob("*.setting"))]
            chk = p.parent / "check.png"
            items.append({"name": p.stem, "title": first, "recipe": rel(p), "macros": macros,
                          "check": rel(chk) if chk.exists() else None, "modified": stamp(p.stat().st_mtime)})
    picks = []
    for pr in list_projects():
        pk = (read_json(library_picks_path(pr["name"]), {}) or {}).get("picks", {})
        picks += [{"project": pr["name"], "effect": k, **v} for k, v in pk.items() if v.get("pick")]
    return {"items": items, "picks": picks}


def text_file(relpath: str, limit: int = 400_000) -> str:
    p = (LAB / relpath).resolve()
    if LAB not in p.parents or p.suffix.lower() not in (".md", ".txt", ".json", ".comp", ".py", ".csv", ".setting"):
        raise PermissionError(relpath)
    return p.read_text(encoding="utf-8", errors="replace")[:limit]
