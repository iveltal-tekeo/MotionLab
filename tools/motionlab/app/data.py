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
from motionlab import overlay_settings as OS
from motionlab import profile as PF
from motionlab import prompts as PR
from motionlab.styles import FOCUS, fmt as video_format, label as style_label
from motionlab.timecode import frame_to_tc
from motionlab.util import ANALYSIS, LAB

PROJECTS = LAB / "projects"
LIBRARY = LAB / "library"
DOCS = LAB / "docs"
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".m4v", ".avi", ".webm", ".mts", ".mxf"}
AUDIO_EXT = {".mp3", ".m4a", ".wav", ".aac", ".flac", ".ogg"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic"}     # the photos of a downloaded carousel / photo post
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
            "missed": v.get("missed", ""), "sound": v.get("sound"), "updated": v.get("updated")}


SOUND_AMOUNTS = ("none", "some", "many")           # 0.4.2: "sound effects in this video" (Claude cannot hear)


def clean_sound(s, old=None):
    """The user's answer on sound effects: {"amount": none|some|many, "where": text, "updated"} or None (not answered).
    "updated" moves only when the answer changed."""
    if not isinstance(s, dict):
        return None
    amount = s.get("amount") if s.get("amount") in SOUND_AMOUNTS else ""
    where = " ".join(str(s.get("where") or "").split())[:2000]
    if not amount and not where:
        return None
    same = isinstance(old, dict) and old.get("amount", "") == amount and old.get("where", "") == where
    return {"amount": amount, "where": where, "updated": old.get("updated") if same and old.get("updated") else stamp()}


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
    # sound effects (0.4.2): a page / import without the key keeps the old answer
    snd = clean_sound(body["sound"], old.get("sound")) if "sound" in body else old.get("sound")
    if snd:
        clean["sound"] = snd
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
    snd = S.get("sound") or {}                 # Claude cannot hear: the user's answer (NONE / SOME / MANY | where)
    L.append("--- sound effects ---")
    where = re.sub(r"\s*\n\s*", " / ", (snd.get("where") or "").strip())
    L.append(((snd.get("amount") or "note").upper() + (f" | where: {where}" if where else ""))
             if snd.get("amount") or where else "(not answered)")
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
        if not ev or ".." in d.name:        # a 0.3.2 ".." name still in use (renamed at the next start): skipped, so it
            continue                        # cannot break the whole list
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
            "lines": (PF.profile(d.name) or {}).get("lines", {}), "breakdown": bool(ev.get("breakdown")),
        })
    return out


def _kind(name: str, ev: dict, v: dict) -> dict:
    """Category, tags, link, format and pacing of an analysis (for the cards, filters and the analysis page)."""
    m = KN.meta(name, ev)
    return {"category": m["category"], "category_label": style_label(m["category"]), "tags": m["tags"],
            "focus": m["focus"], "focus_label": FOCUS.get(m["focus"] or "", ""),
            "url": m["url"], "platform": m["platform"],
            "style": m["category"], "style_label": style_label(m["category"]),            # v0.2.0 names
            "format": video_format(v.get("display_width") or v.get("width"), v.get("display_height") or v.get("height"),
                                   v.get("duration_s")),
            "pacing": KN.pacing(ev)}


def content_info(d: Path) -> dict:
    """The analysis page's Content tab (0.3.5): the transcript (tools\\content.py transcript) and the video's public
    numbers (content.py stats). Both stay on this PC."""
    tj = read_json(d / "content" / "transcript.json", None) or {}
    st = read_json(d / "content" / "stats.json", None)
    tr = None
    if tj.get("lines"):
        tr = {k: tj.get(k) for k in ("source", "kind", "lang", "fetched", "words", "word_timings", "title")}
        tr["lines"] = [{"start": ln["start"], "end": ln["end"], "text": ln["text"]} for ln in tj["lines"]]
    return {"transcript": tr, "stats": st}


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
        "content": content_info(d),
        "profile": PF.profile(d.name), "breakdown": ev.get("breakdown"), "colour": colour_info(d),
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


def post_of(entry: dict | None) -> dict:
    """A downloads.json entry's place in a post (0.4.2.1: download.py keeps every file of an Instagram carousel /
    TikTok photo post): {"post": link, "part": i, "parts": n}, or {} for a single download."""
    e = entry if isinstance(entry, dict) else {}
    if not e.get("post") or not isinstance(e.get("part"), int) or not isinstance(e.get("parts"), int):
        return {}
    return {"post": str(e["post"]), "part": e["part"], "parts": e["parts"]}


def waiting() -> list[dict]:
    """Downloads not analysed yet: videos in refs\\ without an analysis, the audio in refs\\audio\\, and the photos /
    sound of a post (downloads.json "post"). The parts of one post come together, in their order (the page shows
    them as one post)."""
    idx = read_json(LAB / "refs" / "downloads.json", {}) or {}
    files = [Path(c["path"]) for c in candidate_videos() if not c["analysed"]]
    ad = LAB / "refs" / "audio"
    files += [p for p in sorted(ad.glob("*")) if p.is_file() and p.suffix.lower() in AUDIO_EXT] if ad.is_dir() else []
    files += [p for p in sorted((LAB / "refs").glob("*")) if p.is_file() and post_of(idx.get(p.name))
              and (p.suffix.lower() in IMAGE_EXT or p.suffix.lower() in AUDIO_EXT)]
    out = []
    for p in files:
        st, dl = p.stat(), idx.get(p.name) or {}
        ext = p.suffix.lower()
        out.append({"name": p.name, "path": str(p), "rel": rel(p), "size": st.st_size, "modified": stamp(st.st_mtime),
                    "audio": ext in AUDIO_EXT, "photo": ext in IMAGE_EXT, "title": dl.get("title"),
                    "url": dl.get("url"), "platform": dl.get("platform"), **post_of(dl)})
    first: dict[str, int] = {}                         # a post sits where its first file would sit
    for i, w in enumerate(out):
        if w.get("post"):
            first.setdefault(w["post"], i)
    order = [((first[w["post"]], w["part"]) if w.get("post") else (i, 0), i) for i, w in enumerate(out)]
    return [out[i] for _, i in sorted(order)]


# ================================================================================================= projects
def _plan_info(p: Path) -> dict:
    pl = read_json(p, {}) or {}
    return {"file": p.name, "rel": rel(p), "name": pl.get("name"), "version": p.stem.split("_")[-1],
            "frames": pl.get("frames"), "fps": pl.get("fps"), "width": pl.get("width"), "height": pl.get("height"),
            "layers": len(pl.get("layers", [])), "levels": pl.get("levels", "single"),
            "duration_tc": frame_to_tc(max(0, int(pl.get("frames") or 1) - 1), float(pl.get("fps") or 25)),
            "reference": rel(pl["reference"]) if pl.get("reference") and Path(pl["reference"]).exists() else None,
            "made_by": (pl.get("made_by") or {}).get("tool"), "style": (pl.get("made_by") or {}).get("style"),
            "notes": rel(p.with_name(f"draft_{p.stem.split('_')[-1]}.md"))
            if p.with_name(f"draft_{p.stem.split('_')[-1]}.md").exists() else None}


def _video(p: Path, kind: str) -> dict:
    st = p.stat()
    return {"name": p.name, "rel": rel(p), "size": st.st_size, "modified": stamp(st.st_mtime), "mtime": st.st_mtime,
            "kind": kind}


def _render_version(d: Path, p: Path) -> str:
    """The edit version a render shows: name_v2.mp4 -> "v2", else the name's rest (notes on moments)."""
    m = re.search(r"_(v\d+)$", p.stem)
    return m[1] if m else (p.stem[len(d.name) + 1:] if p.stem.startswith(d.name + "_") else p.stem)[:80]


def _render_plan(plans: list[dict], d: Path, p: Path) -> dict:
    """The plan a render was made from (its fps / frames): the plan's "name" = the render's name, else its version."""
    v = _render_version(d, p)
    return next((x for x in plans if x.get("name") and x["name"] == p.stem), None) \
        or next((x for x in plans if x.get("version") == v), None) or {}


def _picture(d: Path, b: Path, newest: Path | None, plan: dict) -> dict | None:
    """A still that says which video this is (the user, 2026-10-15: "it should at least show a preview of some
    render"): a frame of the newest render about a third in, else thumbnail A of the package, else a graphic's
    picture, else a frame of the first clip one second in. {"video", "f", "fps"} (GET /api/thumb) or {"image"}."""
    if newest:
        fps = float(plan.get("fps") or 30)
        f = int(int(plan["frames"]) * 0.3) if plan.get("frames") else int(round(fps))
        return {"video": rel(newest), "f": f, "fps": fps}
    pub = sorted((b / "publish").glob("thumb_*_16x9.png")) if (b / "publish").is_dir() else []
    if pub:
        return {"image": rel(pub[0])}
    gr = sorted((b / "overlays").glob("*/thumb.png"), key=lambda q: -q.stat().st_mtime) if (b / "overlays").is_dir() else []
    if gr:
        return {"image": rel(gr[0])}
    clips = sorted(p for p in d.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXT)
    return {"video": rel(clips[0]), "f": 25, "fps": 25.0} if clips else None


def _label(b: Path) -> str | None:
    """The name the app shows for a video when the user renamed it (build\\project.json "label"; rename_project)."""
    return (read_json(b / "project.json", {}) or {}).get("label") or None


def _created(d: Path) -> float:
    """When the video's folder was made (Windows' creation time)."""
    st = d.stat()
    return getattr(st, "st_birthtime", None) or st.st_ctime


def _reviewed(b: Path, outcome: dict, newest: float | None) -> bool | None:
    """Is the newest render rated yet (How did it turn out?)? None = no render. A rating saved after the render counts:
    outcome.json "rated_ts" (2026-10-15), for an older file the file's own time when it holds a rating."""
    if newest is None:
        return None
    if not any((v or {}).get("rating") for v in (outcome.get("aspects") or {}).values() if isinstance(v, dict)):
        return False
    t = outcome.get("rated_ts")
    if t is None:
        p = b / "outcome.json"
        t = p.stat().st_mtime if p.exists() else 0
    return float(t) >= newest


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
        renders = sorted(b.glob("*.mp4"), key=lambda q: q.stat().st_mtime) if b.exists() else []
        infos = [_plan_info(p) for p in plans]
        newest = renders[-1] if renders else None
        plan = _render_plan(infos, d, newest) if newest else {}
        if newest and not plan.get("fps"):                # no plan for it: its rate and length by ffprobe (cached)
            try:
                from . import player
                plan = player.codec(newest)
            except Exception:                             # noqa: BLE001
                plan = {}
        outcome = read_json(b / "outcome.json", {}) or {}
        made = read_json(b / "made_from.json", []) or []
        pkg = read_json(b / "publish" / "package.json", {}) or {}
        nt = newest.stat().st_mtime if newest else None
        created = _created(d)
        out.append({
            "name": d.name, "label": _label(b), "clips": len(clips), "footage_bytes": sum(p.stat().st_size for p in clips),
            "songs": sorted(p.name for p in d.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXT),
            "plans": [p.stem for p in plans],
            "renders": [p.name for p in sorted(renders)],
            "resolve": sorted(m.name[:-len("_build.json")] for m in (b / "resolve").glob("*_build.json"))
            if (b / "resolve").exists() else [],
            "thumb": rel(boards[0]) if boards else None,
            # 2026-10-15 (the Edit page's cards): the newest render, a picture, when it last changed, how it was made
            "latest": {"rel": rel(newest), "version": _render_version(d, newest), "resolve": "_resolve_" in newest.stem,
                       "frames": plan.get("frames"), "fps": plan.get("fps"), "width": plan.get("width"),
                       "height": plan.get("height"), "modified": stamp(nt), "mtime": nt} if newest else None,
            "picture": _picture(d, b, newest, plan),
            # the list's order (the user, 2026-10-15: "by date of creation (new renders), the newest up"): the newest
            # render's time, else when the folder was made
            "created": created, "sort_t": nt or created,
            "generated": any(x.get("kind") == "generated" for x in made if isinstance(x, dict)),
            "rating": ((outcome.get("aspects") or {}).get("overall") or {}).get("rating"),
            "reviewed": _reviewed(b, outcome, nt),
            "next": outcome.get("next"), "title": pkg.get("title") or None,
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


def overlay_folder(project: str, overlay: str) -> Path:
    """projects\\<project>\\build\\overlays\\<overlay>\\ (an HTML graphic) - names checked, the folder must exist."""
    if not re.fullmatch(r"[\w.-]+", overlay or ""):
        raise ValueError(f"bad graphic name: {overlay!r}")
    f = PROJECTS / safe_name(project) / "build" / "overlays" / overlay
    if not (f / "index.html").exists():
        raise FileNotFoundError(f"{project}: no graphic {overlay}")
    return f


def save_overlay_values(project: str, overlay: str, values) -> dict:
    """The Graphics tab's Save: the user's settings into the overlay's overlay.json (validated against what its
    index.html declares); the render job then uses them."""
    return OS.set_values(overlay_folder(project, overlay), values if isinstance(values, dict) else {})


# ------------------------------------------------------------------ 0.4.3: Edit > a video > Publish
# build\publish\package.json belongs to the tools (thumbnail.py: candidates / thumbnails, publish.py: the words); the
# app reads it, runs the thumbnail jobs and calls publish.write - it never writes package.json itself. Its own writes:
# a thumbnail's settings (thumbs\<id>\overlay.json "values", validated like any graphic) and a picture the user brings
# (build\publish\images\, for make --image).
PUB_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def publish_dir(name: str) -> Path:
    d = PROJECTS / safe_name(name)
    if not d.is_dir():
        raise FileNotFoundError(name)
    return d / "build" / "publish"


def thumb_folder(name: str, tid: str) -> Path:
    if not re.fullmatch(r"[A-Z]", str(tid or "")):
        raise ValueError("a thumbnail is A, B or C")
    f = publish_dir(name) / "thumbs" / tid
    if not (f / "index.html").exists():
        raise FileNotFoundError(f"{name}: no thumbnail {tid} yet")
    return f


def publish_info(name: str) -> dict:
    """The Publish tab: package.json as the tools wrote it (each thumbnail + its settings for the form), the title
    records linked to this video (prompt library kind title, "project"), the edit's rate / length for the chapters,
    the designs, the pictures the user brought."""
    from motionlab import publish as PB
    pub = publish_dir(name)
    d = pub.parent.parent
    pkg = PB.read_package(pub) if (pub / "package.json").exists() else {}
    thumbs = []
    for t in pkg.get("thumbnails") or []:
        t = dict(t)
        files = t.get("files") or {}
        folder = LAB / files.get("folder", "_") if files.get("folder") else None
        t["settings"] = OS.status(folder)["settings"] if folder and (folder / "index.html").exists() else []
        p = LAB / files["16x9"] if files.get("16x9") else None
        t["v"] = int(p.stat().st_mtime) if p and p.exists() else 0
        thumbs.append(t)
    plan = PB.latest_plan(d.name)
    pl = (read_json(plan, {}) or {}) if plan else {}
    recs = [{k: r.get(k) for k in ("id", "title", "titles", "concepts", "hook", "chosen", "request", "updated")}
            for r in PR.load_all("title") if r.get("project") == d.name]
    try:
        from motionlab import thumbnail as T                   # numpy / Pillow: only when the tab is opened
        templates = [{"name": t["name"], "what": t["what"]} for t in T.templates()]
        face = T.face_model() is not None
    except Exception:                                           # noqa: BLE001 - the tab still shows the package
        templates, face = [], False
    imgs = pub / "images"
    renders = sorted((p for p in (d / "build").glob("*.mp4") if re.search(r"_v\d+\.mp4$", p.name)),
                     key=lambda p: p.stat().st_mtime) if (d / "build").exists() else []
    return {"name": d.name, "folder": rel(pub), "exists": (pub / "package.json").exists(), "package": {**pkg, "thumbnails": thumbs},
            "records": recs, "fps": pl.get("fps"), "frames": pl.get("frames"), "plan": plan.name if plan else None,
            "templates": templates, "face_detector": face, "render": renders[-1].name if renders else None,
            "clips": sum(1 for p in d.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXT),
            "images": [{"name": p.name, "path": str(p), "rel": rel(p)} for p in sorted(imgs.iterdir(), key=lambda q: -q.stat().st_mtime)
                       if p.suffix.lower() in PUB_IMAGE_EXT] if imgs.is_dir() else []}


def save_publish(name: str, body: dict) -> dict:
    """The Publish tab's words -> publish.write (title.txt, description.txt with the chapters, hashtags.txt, its keys
    in package.json). Left out = kept. Nothing is written when a check FAILs: {ok, checks, description}."""
    from motionlab import publish as PB
    publish_dir(name)
    title = " ".join(str(body.get("title") or "").split())
    chs = body.get("chapters")
    if chs is not None:
        if not isinstance(chs, list):
            raise ValueError("chapters: a list of [frame, name]")
        clean = []
        for c in chs:
            try:
                f, n = (c[0], c[1]) if isinstance(c, (list, tuple)) else (c.get("f"), c.get("name"))
                clean.append((int(f), " ".join(str(n or "").split())[:100]))
            except (TypeError, ValueError, IndexError, AttributeError):
                raise ValueError("each chapter needs a frame number and a name") from None
        chs = sorted(clean)
    tags = body.get("hashtags")
    tf = str(body.get("titles_from") or "")
    if tf and not re.fullmatch(r"title-\d{3,}", tf):
        raise ValueError(f"not a title record: {tf!r}")
    r = PB.write(name, title, chapters=chs, hashtags=None if tags is None else str(tags)[:3000],
                 body=None if body.get("body") is None else str(body["body"])[:6000], titles_from=tf)
    return {"ok": r["ok"], "checks": r["checks"], "description": r["description"]}


def save_thumb_values(name: str, tid: str, values) -> dict:
    """A thumbnail's settings (the Publish tab's form) -> thumbs\\<id>\\overlay.json "values" (validated against its
    template); *Render again* = the thumb_render job."""
    return OS.set_values(thumb_folder(name, tid), values if isinstance(values, dict) else {})


def save_publish_image(name: str, filename: str, raw: bytes) -> dict:
    """*Use a picture you made* (an AI image tool's): the user's picture -> build\\publish\\images\\ (a copy; the
    thumbnail is then made from it with make --image)."""
    ext = Path(str(filename or "")).suffix.lower()
    if ext not in PUB_IMAGE_EXT:
        raise ValueError("a picture: .jpg, .png or .webp")
    if len(raw) > 30_000_000:
        raise ValueError("pictures up to 30 MB")
    d = publish_dir(name) / "images"
    d.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^\w.-]+", "_", Path(filename).stem).strip("._")[:60] or "picture"
    p, i = d / f"{stem}{ext}", 2
    while p.exists():
        p, i = d / f"{stem}_{i}{ext}", i + 1
    tmp = p.with_name(p.name + ".part")
    tmp.write_bytes(raw)
    os.replace(tmp, p)
    return {"name": p.name, "path": str(p), "rel": rel(p)}


def _overlays_in_plans(plans: list[Path]) -> dict:
    """overlay .mov (lower-case path) -> where the edit versions show it, e.g. ["v1 f0-29"]."""
    used: dict[str, list[str]] = {}
    for p in plans:
        pl = read_json(p, {}) or {}
        for L in pl.get("layers", []):
            if L.get("type") == "overlay" and L.get("file"):
                key = str(Path(L["file"]).resolve()).lower()
                used.setdefault(key, []).append(f"{p.stem.split('_')[-1]} f{L.get('start')}-{L.get('end')}")
    return used


def project(name: str) -> dict:
    d = PROJECTS / safe_name(name)
    if not d.is_dir():
        raise FileNotFoundError(name)
    b = d / "build"
    srcs = (read_json(b / "sources.json", {}) or {}).get("sources", {})
    sources = []
    for sid, s in sorted(srcs.items()):
        meta = (read_json(b / "cache" / f"{sid}.color.json", {}) or read_json(b / "cache" / f"{sid}.json", {})
                or {})                                    # colour caches (0.3.0+) or grey ones
        p = Path(s["path"])
        sources.append({"id": sid, "name": s["name"], "size": p.stat().st_size if p.exists() else None,
                        "exists": p.exists(), "fps": meta.get("src_fps"), "frames": meta.get("src_frames"),
                        "duration_s": (meta.get("src_frames") or 0) / (meta.get("src_fps") or 1) or None,
                        "resolution": f"{meta.get('src_width')}x{meta.get('src_height')}" if meta else None,
                        "cached": bool(meta.get("complete")), "board": rel(b / "boards" / f"{sid}_01.jpg")
                        if (b / "boards" / f"{sid}_01.jpg").exists() else None})
    known = {Path(s["path"]).name.lower() for s in srcs.values() if s.get("path")}
    for p in sorted(d.iterdir()):                         # clips not prepared yet (no sources.json entry): listed too
        if p.is_file() and p.suffix.lower() in VIDEO_EXT and p.name.lower() not in known:
            sources.append({"id": None, "name": p.name, "size": p.stat().st_size, "exists": True, "fps": None,
                            "frames": None, "duration_s": None, "resolution": None, "cached": False, "board": None})
    plans = [_plan_info(p) for p in sorted(b.glob("plan_v*.json"))] if b.exists() else []
    renders = []
    for p in sorted(b.glob("*.mp4")) if b.exists() else []:
        r = _video(p, "resolve" if "_resolve_" in p.stem else "lab")
        r["version"] = _render_version(d, p)              # the edit version a render shows (notes on moments)
        pl = _render_plan(plans, d, p)
        if not pl.get("fps"):                             # a render without a plan (a graphics preview): ffprobe, cached
            try:
                from . import player
                pl = player.codec(p)
            except Exception:                             # noqa: BLE001 - no ffprobe / a broken file: no rate shown
                pl = {}
        r.update(fps=pl.get("fps"), frames=pl.get("frames"), width=pl.get("width"), height=pl.get("height"))
        renders.append(r)
    newest = max(renders, key=lambda r: r["mtime"]) if renders else None
    made = read_json(b / "made_from.json", []) or []
    for x in made:                                    # Film it: "From the script: <its title>"
        if isinstance(x, dict) and x.get("kind") == "prompt":
            try:
                pr = PR.get(str(x.get("id")))
                x.update(title=pr.get("title") or pr.get("title_auto") or "", prompt_kind=pr.get("kind"))
            except Exception:                         # noqa: BLE001 - deleted from the library: the id only
                pass
    compares =[_video(p, "compare") for p in sorted((b / "compare").glob("*.mp4"))] if (b / "compare").exists() else []
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
    overlays = OS.project_overlays(d.name)
    media = [{"label": f"render {p.name}", "path": str(p)} for p in sorted(b.glob("*.mp4"), key=lambda q: q.stat().st_mtime,
                                                                         reverse=True)] if b.exists() else []
    media += [{"label": f"your clip {p.name}", "path": str(p)} for p in sorted(d.iterdir())
              if p.is_file() and p.suffix.lower() in VIDEO_EXT]
    from motionlab import speech as SP
    used = _overlays_in_plans(sorted(b.glob("plan_v*.json"))) if b.exists() and overlays else {}
    for o in overlays:
        o["used_in"] = used.get(str((LAB / o["folder"] / f"{o['name']}.mov").resolve()).lower(), [])
    outcome = read_json(b / "outcome.json", {}) or {}
    return {"name": d.name, "label": _label(b), "sources": sources, "plans": plans, "renders": renders,
            "compares": compares, "overlays": overlays, "media": media,
            "speech": {"available": SP.available(), "small": SP.model_ready("small"), "base": SP.model_ready("base")},
            "verifies": verifies, "resolve": resolve, "check_sheets": sheets,
            "boards": [rel(p) for p in sorted((b / "boards").glob("*.jpg"))] if (b / "boards").exists() else [],
            "edit_scripts": [rel(p) for p in sorted(b.glob("edit_v*.py"))] if b.exists() else [],
            "library_picks": picks.get("picks", {}), "picks_updated": picks.get("updated"),
            "made_from": made, "outcome": outcome, "reviewed": _reviewed(b, outcome, newest["mtime"] if newest else None),
            "generated": any(x.get("kind") == "generated" for x in made if isinstance(x, dict)),
            "picture": _picture(d, b, LAB / newest["rel"] if newest else None, newest or {}),
            "publish": (b / "publish" / "package.json").exists()}


# ------------------------------------------------------------------ 0.3.3: create a video, and how it turned out
ASPECTS = ("sound", "sfx", "colour", "captions", "graphics", "effects", "pacing", "packaging", "overall")
OUTCOME_NEXT = ("fix", "start_over")          # 0.4.2: How did it turn out? - fix this version / start over
CTR_IDS = re.compile(r"[A-Z]")                # 0.4.3: a thumbnail variant (thumbnail.py make --id A / B / C)


def new_project(name: str) -> dict:
    """Videos > Create video: an empty projects\\<name>\\ for the user's clips (nothing else is written)."""
    name = safe_name(str(name).strip())
    if name.startswith((".", " ")) or name.endswith((".", " ")):
        raise ValueError("a name cannot start or end with a dot or a space")
    d = PROJECTS / name
    if d.exists():
        raise ValueError(f"projects\\{name} exists already - pick it in the list")
    d.mkdir(parents=True)
    return {"name": name, "folder": rel(d)}


def rename_project(name: str, label: str) -> dict:
    """The name the app shows for a video (2026-10-15, the user: "I can't rename my edits?") -> build\\project.json
    "label". The folder keeps its name: the clips are never moved (hard rule 1), the plans, renders and a Resolve
    project find them by that path, and Claude's commands name the folder. An empty label = the folder's name again."""
    d = PROJECTS / safe_name(name)
    if not d.is_dir():
        raise FileNotFoundError(name)
    label = " ".join(re.sub(r"[\x00-\x1f\x7f]", " ", str(label or "")).split())[:80]
    if label and label != d.name:
        for o in PROJECTS.iterdir():
            if o.is_dir() and o != d and label.lower() in (o.name.lower(), (_label(o / "build") or "").lower()):
                raise ValueError(f"another video is called “{label}” already")
    p = d / "build" / "project.json"
    out = {**(read_json(p, {}) or {}), "label": label if label and label != d.name else None, "updated": stamp()}
    write_json_atomic(p, out)
    return {"name": d.name, "label": out["label"]}


def add_made_from(name: str, kind: str, ref: str) -> list:
    """What a video is made from (New edit): a reference copied 1:1 (an analysis), up to three videos' style
    ("style": names joined by ", "), the user's words ("words": presets / their words) or a prompt -
    build\\made_from.json."""
    if kind not in ("reference", "prompt", "style", "words", "generated"):
        raise ValueError("made from a reference, videos' style, your words, a prompt or from zero")
    ref = safe_name(ref) if kind == "reference" else " ".join(str(ref).split())[:300]
    if kind == "prompt" and not re.fullmatch(r"(shot|image|hook|script|brief|title)-\d{3,}", ref):
        raise ValueError(f"not a prompt id: {ref!r}")
    d = PROJECTS / safe_name(name)
    if not d.is_dir():
        raise FileNotFoundError(name)
    p = d / "build" / "made_from.json"
    items = [x for x in (read_json(p, []) or []) if not (x.get("kind") == kind and x.get("id") == ref)]
    items.append({"kind": kind, "id": ref, "date": stamp()})
    write_json_atomic(p, items)
    return items


# ------------------------------------------------------------------ 0.4: New edit - what the user asked for
EDIT_HOW = ("copy", "style", "words", "prompt")
EDIT_SOUND = ("auto", "music", "clips", "talk")


def edit_options() -> dict:
    """The New edit dialog's choices: the presets of "With your words", how many videos a style may mix."""
    from motionlab import style as ST
    return {"presets": ST.presets_info(), "max_refs": ST.MAX_REFS, "formats": sorted(ST.SIZES)}


def edit_request(name: str) -> dict:
    p = PROJECTS / safe_name(name) / "build" / "edit_request.json"
    if not p.exists():
        raise FileNotFoundError(f"{name}: no edit request yet (Editor > New edit)")
    return read_json(p, {}) or {}


def save_edit_request(name: str, body: dict) -> dict:
    """New edit (0.4): what the user picked - copy one analysed video 1:1, mix the style of up to three, a preset
    or their own words, or a saved prompt; length, format, sound, Resolve or not - checked, then saved as
    build\\edit_request.json. Claude (/recreate-video request <p>) and the quick draft (job "draft") both read it, so
    the user's words never pass through a command line."""
    from motionlab import style as ST
    d = PROJECTS / safe_name(name)
    if not d.is_dir():
        raise FileNotFoundError(name)
    how = str(body.get("how") or "")
    if how not in EDIT_HOW:
        raise ValueError(f"how: one of {', '.join(EDIT_HOW)}")
    like = [" ".join(str(x).split()) for x in (body.get("like") or []) if str(x).strip()]
    if len(like) > ST.MAX_REFS:
        raise ValueError(f"at most {ST.MAX_REFS} videos for one edit")
    for x in like:
        if x.startswith("-") or len(x) > 160 or ST.find(x) is None:
            raise ValueError(f"no analysed video called {x!r}")
    if how in ("copy", "style") and not like:
        raise ValueError("pick at least one analysed video")
    if how == "copy" and (len(like) != 1 or not re.fullmatch(r"[\w.\- \[\]()&'+,]+", like[0]) or ".." in like[0]
                          or not (ANALYSIS / like[0] / "events.json").exists()):
        raise ValueError("an exact copy needs one video analysed on this PC")
    presets = [str(x) for x in (body.get("presets") or [])]
    bad = [x for x in presets if x not in ST.PRESETS]
    if bad:
        raise ValueError(f"unknown preset {bad[0]!r}")
    want = " ".join(str(body.get("want") or "").split())[:1500]
    if how == "words" and not presets and not want:
        raise ValueError("pick a style or write what you want")
    prompt = str(body.get("prompt") or "")
    if how == "prompt" and not re.fullmatch(r"(shot|image|hook|script|brief|title)-\d{3,}", prompt):
        raise ValueError(f"not a prompt id: {prompt!r}")
    length = body.get("length_s")
    if length not in (None, ""):
        length = float(length)
        if not 3 <= length <= 900:
            raise ValueError("length: 3 to 900 seconds")
    else:
        length = None
    fmt = body.get("format") or None
    if fmt is not None and fmt not in ST.SIZES:
        raise ValueError(f"format: one of {', '.join(ST.SIZES)}")
    music = str(body.get("music") or "")
    if music and music != "none":
        if Path(music).name != music or not (d / music).is_file() or (d / music).suffix.lower() not in AUDIO_EXT:
            raise ValueError(f"{music}: not a song in projects\\{d.name}")
    sound = str(body.get("sound") or "auto")
    if sound not in EDIT_SOUND:
        raise ValueError(f"sound: one of {', '.join(EDIT_SOUND)}")
    req = {"how": how, "like": like if how in ("copy", "style") else [], "presets": presets if how in (
        "words", "style") else [], "want": want if how != "prompt" else "", "prompt": prompt if how == "prompt" else None,
        "length_s": length, "format": fmt, "music": music or None, "sound": sound,
        "resolve": bool(body.get("resolve")), "date": stamp()}
    write_json_atomic(d / "build" / "edit_request.json", req)
    kind, ref = {"copy": ("reference", like[0] if like else ""), "style": ("style", ", ".join(like)),
                 "words": ("words", ", ".join(ST.PRESETS[x]["label"] for x in presets) or want[:120]),
                 "prompt": ("prompt", prompt)}[how]
    made = add_made_from(d.name, kind, ref)
    cmd = (f"/recreate-video {like[0]} {d.name}" if how == "copy" and " " not in like[0] + d.name
           else f"/recreate-video prompt:{prompt} {d.name}" if how == "prompt" and " " not in d.name
           else f"/recreate-video request {d.name}")
    return {"request": req, "made_from": made, "command": cmd}


# ------------------------------------------------------------------ 0.4: Generate - a video from zero
GEN_KINDS = ("graphics", "ai")
AI_TOOLS = ["Higgsfield", "Seedance", "Kling", "Runway", "Veo", "Sora", "Hailuo", "Pika", "Luma", "InVideo AI",
            "Pictory", "HeyGen", "Synthesia"]


def generate_options() -> dict:
    """Generate's dialogs: the AI tools offered, the songs downloaded (refs\\audio\\), HyperFrames ready or not."""
    from . import system
    songs = [{"name": p.name, "rel": rel(p)} for p in sorted((LAB / "refs" / "audio").glob("*"))
             if p.is_file() and p.suffix.lower() in AUDIO_EXT] if (LAB / "refs" / "audio").exists() else []
    return {"tools": AI_TOOLS, "songs": songs, "hyperframes": bool(system.find("hyperframes")),
            "node": bool(system.find("node"))}


def _song(d: Path, music: str) -> str | None:
    """A song for Generate: a file in the video's folder (a name) or a download in refs\\audio\\ (lab-relative)."""
    if not music or music == "none":
        return None
    if Path(music).name == music and (d / music).is_file() and (d / music).suffix.lower() in AUDIO_EXT:
        return str(d / music)
    p = (LAB / music).resolve()
    if p.parent == (LAB / "refs" / "audio").resolve() and p.is_file() and p.suffix.lower() in AUDIO_EXT:
        return str(p)
    raise ValueError(f"{music}: not a song in the video's folder or in refs\\audio")


def save_generate_request(body: dict) -> dict:
    """Generate (0.4): a video from zero - a motion-graphics video (HyperFrames) or the plan + every prompt for AI
    video tools. The video gets its folder (projects\\<name>\\, made empty when new: a song or a logo can go
    there) and the request, checked, is saved as build\\generate_request.json for /generate-video request <name>."""
    from motionlab import style as ST
    kind = str(body.get("kind") or "")
    if kind not in GEN_KINDS:
        raise ValueError("kind: graphics or ai")
    name = safe_name(" ".join(str(body.get("name") or "").split()))
    want = " ".join(str(body.get("want") or "").split())[:3000]
    if not want:
        raise ValueError("say what the video is about")
    text = "\n".join(" ".join(ln.split()) for ln in str(body.get("text") or "").splitlines() if ln.strip())[:3000]
    like = [" ".join(str(x).split()) for x in (body.get("like") or []) if str(x).strip()]
    if len(like) > ST.MAX_REFS:
        raise ValueError(f"at most {ST.MAX_REFS} videos for one style")
    for x in like:
        if len(x) > 160 or ST.find(x) is None:
            raise ValueError(f"no analysed video called {x!r}")
    length = body.get("length_s")
    length = float(length) if length not in (None, "") else None
    if length is not None and not 3 <= length <= 900:
        raise ValueError("length: 3 to 900 seconds")
    fmt = body.get("format") or None
    if fmt is not None and fmt not in ST.SIZES:
        raise ValueError(f"format: one of {', '.join(ST.SIZES)}")
    tool = " ".join(str(body.get("tool") or "").split())[:60]
    extra = {k: " ".join(str(body.get(k) or "").split())[:120] for k in ("colours", "font")}
    d = PROJECTS / name
    b = d / "build"
    if b.exists() and not body.get("reuse") and (any(b.glob("plan_v*.json")) or any(b.glob("*.mp4")) or any(
            (b / f).exists() for f in ("generate_request.json", "edit_request.json"))):
        raise ValueError(f"{name} is already a video - give this one another name")
    song = _song(d, str(body.get("music") or ""))         # checked before a new folder is made
    if not d.exists():
        new_project(name)
    req = {"kind": kind, "want": want, "text": text if kind == "graphics" else "", "like": like, "length_s": length,
           "format": fmt, "music": song, "tool": tool if kind == "ai" else "", **(extra if kind == "graphics" else {}),
           "date": stamp()}
    write_json_atomic(d / "build" / "generate_request.json", req)
    made = add_made_from(d.name, "generated", "a motion-graphics video" if kind == "graphics"
                         else f"AI video tools{': ' + tool if tool else ''}")
    return {"request": req, "project": d.name, "made_from": made, "command": f"/generate-video request {d.name}"}


def draft_args(req: dict) -> list[str]:
    """draft_edit.py's arguments for a saved edit request (the quick draft job). A script or hook (Film it,
    2026-10-15) = a talking video: the talking preset, its sound kept and the pauses cut."""
    talk = req.get("how") == "prompt" and re.fullmatch(r"(script|hook)-\d{3,}", str(req.get("prompt") or ""))
    if req.get("how") not in ("style", "words") and not talk:
        raise ValueError("a quick draft is made from videos' style, your words or a talking script "
                         "(an exact copy or another prompt: Claude)")
    out: list[str] = ["--preset", "talking"] if talk else []
    for x in req.get("like") or []:
        out += ["--like", x]
    for x in req.get("presets") or []:
        out += ["--preset", x]
    if req.get("want"):
        out += ["--want", req["want"]]
    if req.get("length_s"):
        out += ["--length", f"{float(req['length_s']):g}"]
    if req.get("format"):
        out += ["--format", req["format"]]
    if req.get("music"):
        out += ["--music", req["music"]]
    sound = req.get("sound") or "auto"
    if talk and sound == "auto":
        sound = "talk"
    if sound != "auto":
        out += ["--sound", sound]
    return out


def save_outcome(name: str, body: dict) -> dict:
    """How a finished video turned out, per part (sound, SFX, colour, captions, graphics, effects, pacing, overall):
    good / ok / bad + a note -> build\\outcome.json. Claude reads it (what worked); the prompts it was made from show
    it on their cards."""
    d = PROJECTS / safe_name(name)
    if not d.is_dir():
        raise FileNotFoundError(name)
    p = d / "build" / "outcome.json"
    cur = read_json(p, {}) or {}
    asp = dict(cur.get("aspects", {}))
    for k, v in (body.get("aspects") or {}).items():
        if k not in ASPECTS or not isinstance(v, dict):
            continue
        rating = v.get("rating") or None
        if rating not in (None, "good", "ok", "bad"):
            raise ValueError(f"rating: good, ok or bad (got {rating!r})")
        asp[k] = {"rating": rating, "note": str(v.get("note") or "").strip()[:500]}
    # 0.4.2: fix this version or start over (null = not answered); notes on moments of a render
    nxt = cur.get("next") if cur.get("next") in OUTCOME_NEXT else None
    if "next" in body:
        nxt = body["next"] or None
        if nxt not in (None, *OUTCOME_NEXT):
            raise ValueError(f"next: fix or start_over (got {nxt!r})")
    moments = [m for m in (cur.get("moments") or []) if isinstance(m, dict)]
    if body.get("moment") is not None:
        moments.append(clean_moment(body["moment"]))
    if body.get("remove_moment") is not None:
        r = body["remove_moment"] if isinstance(body["remove_moment"], dict) else {}
        hit = next((i for i, m in enumerate(moments) if all(m.get(k) == r.get(k) for k in ("f", "version", "note"))
                    and (not r.get("date") or m.get("date") == r.get("date"))), None)
        if hit is None:
            raise ValueError("that note is not there any more")
        moments.pop(hit)
    moments.sort(key=lambda m: (str(m.get("version", "")), int(m.get("f", 0))))
    out = {**cur, "aspects": {k: v for k, v in asp.items() if v.get("rating") or v.get("note")}, "updated": stamp(),
           "next": nxt, "moments": moments}                  # every other key (0.4.3 "packaging", newer ones) stays
    if body.get("aspects"):                   # when the ratings last changed: a newer render = "not reviewed yet"
        out["rated_ts"] = time.time()
    if body.get("packaging") is not None:
        out["packaging"] = clean_packaging(body["packaging"], cur.get("packaging"))
    write_json_atomic(p, out)
    return out


def clean_packaging(b, old=None) -> dict:
    """0.4.3, after posting: the click-through rate the user read in YouTube Studio per thumbnail variant (A / B / C,
    in %) and the video's link -> outcome.json "packaging": {"ctr": {"A": 4.1}, "link", "updated"}. A key left out
    keeps its old value; an empty CTR removes that variant."""
    if not isinstance(b, dict):
        raise ValueError("packaging: the click-through rates and the link")
    old = old if isinstance(old, dict) else {}
    ctr = dict(old.get("ctr") or {})
    for k, v in (b.get("ctr") or {}).items() if isinstance(b.get("ctr"), dict) else []:
        k = str(k).strip().upper()
        if not CTR_IDS.fullmatch(k):
            raise ValueError(f"a thumbnail is A, B or C (got {k!r})")
        if v in (None, ""):
            ctr.pop(k, None)
            continue
        try:
            x = float(str(v).replace(",", ".").replace("%", "").strip())
        except ValueError:
            raise ValueError(f"thumbnail {k}: the click-through rate is a number like 4.1") from None
        if not 0 <= x <= 100:
            raise ValueError(f"thumbnail {k}: the click-through rate is a percentage between 0 and 100")
        ctr[k] = round(x, 2)
    link = old.get("link") or ""
    if "link" in b:
        link = str(b.get("link") or "").strip()
        if link and (not re.fullmatch(r"https?://\S{3,500}", link)):
            raise ValueError("the video's link starts with https:// (copy it from the platform)")
    return {"ctr": dict(sorted(ctr.items())), "link": link, "updated": stamp()}



def clean_moment(m) -> dict:
    """A note on one moment of a render: {"f": frame of that render (0-based, its fps), "version": "v2", "aspect":
    one of ASPECTS, "note": text, "date"} - /recreate-video improve fixes exactly those moments."""
    if not isinstance(m, dict):
        raise ValueError("a note needs a frame, a version, a part and the text")
    try:
        f = int(m.get("f"))
    except (TypeError, ValueError):
        raise ValueError("a note needs the frame it is about") from None
    if not 0 <= f <= 10_000_000:
        raise ValueError(f"frame out of range: {f}")
    version = str(m.get("version") or "").strip()
    if not re.fullmatch(r"[\w.\- \[\]()&'+,]{1,80}", version):
        raise ValueError(f"which version is it about? (got {version!r})")
    aspect = str(m.get("aspect") or "")
    if aspect not in ASPECTS:
        raise ValueError(f"part: one of {', '.join(ASPECTS)}")
    note = " ".join(str(m.get("note") or "").split())[:500]
    if not note:
        raise ValueError("write what is wrong or right at that moment")
    return {"f": f, "version": version, "aspect": aspect, "note": note, "date": stamp()}


def prompt_styles(items: list[dict]) -> dict:
    """The prompt library's *Style like* (0.3.5): every analysed reference's measured style (a short line, its frame)
    and, per brief / script / hook, the references its words seem to mean (who made it, its title)."""
    st = PR.all_styles()
    keep = ("name", "title", "uploader", "category_label", "format", "line", "thumb", "reviewed", "effects",
            "verdicts", "transcript")
    styles = {s["name"]: {k: s.get(k) for k in keep} for s in st}
    for r in items:                                  # a linked self-test copy (zz tests) still shows
        for n in r.get("style_refs") or []:
            if n not in styles and (s := KN.style(n)):
                styles[n] = {k: s.get(k) for k in keep}
    sug = {r["id"]: x for r in items if r.get("kind") in PR.STYLE_KINDS
           and (x := PR.suggest_refs(r.get("text", ""), st, r.get("style_refs") or []))}
    return {"styles": styles, "suggest": sug}


def prompt_uses() -> dict:
    """prompt id -> the videos made from it and how they turned out (the prompt library's 'Used in')."""
    out: dict = {}
    for d in sorted(PROJECTS.iterdir()) if PROJECTS.exists() else []:
        b = d / "build"
        made = read_json(b / "made_from.json", []) if (b / "made_from.json").exists() else []
        if not made:
            continue
        outcome = read_json(b / "outcome.json", {}) or {}
        asp = outcome.get("aspects", {})
        # Film it (2026-10-15): a script's road - filmed (a clip in the folder), edited (a render), posted (the link)
        clips = sum(1 for p in d.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXT)
        renders = sum(1 for _ in b.glob("*.mp4"))
        posted = bool((outcome.get("packaging") or {}).get("link"))
        for x in made or []:
            if x.get("kind") == "prompt":
                out.setdefault(x.get("id"), []).append({"project": d.name, "label": _label(b), "aspects": asp,
                                                        "clips": clips, "renders": renders, "posted": posted})
    return out


def save_upload(name: str, filename: str, stream, size: int, prompt: str = "") -> dict:
    """Film it (2026-10-15, the user: "you click record it but don't actually record it... then you add it to
    motionlab"): a recording the user picks or drops in the app, copied into projects\\<name>\\ as a new clip. The
    original stays where it was (only read by the browser); a file of the same name is never overwritten - a copy
    that is already there (same size) is kept, another one gets " (2)". prompt = the script it was filmed from
    (made_from.json, so the script card shows "Filmed")."""
    d = PROJECTS / safe_name(name)
    if not d.is_dir():
        raise FileNotFoundError(name)
    stem, ext = os.path.splitext(Path(str(filename)).name)
    ext = ext.lower()
    if ext not in VIDEO_EXT | AUDIO_EXT:
        raise ValueError(f"{filename}: not a video or a song ({', '.join(sorted(VIDEO_EXT | AUDIO_EXT))})")
    stem = re.sub(r"[^\w.\- \[\]()&'+,]", "_", stem).replace("..", "_").strip(" .") or "recording"
    if not 0 < size <= 200 * 2**30:
        raise ValueError("the file is empty or bigger than 200 GB")
    dest, n = d / f"{stem}{ext}", 1
    while dest.exists():
        if dest.stat().st_size == size:                       # the same file added twice: keep the first copy
            _drain(stream, size)
            return {"file": dest.name, "kept": True, "made_from": add_made_from(d.name, "prompt", prompt) if prompt else None}
        n += 1
        dest = d / f"{stem} ({n}){ext}"
    part = d / "build" / "upload" / (dest.name + ".part")     # outside the clips until it is whole
    part.parent.mkdir(parents=True, exist_ok=True)
    left = size
    try:
        with open(part, "wb") as f:
            while left:
                buf = stream.read(min(left, 4 * 2**20))
                if not buf:
                    raise ConnectionAbortedError("the upload stopped")
                f.write(buf)
                left -= len(buf)
        os.replace(part, dest)
    finally:
        if part.exists():
            part.unlink()
        try:
            part.parent.rmdir()                               # only when empty (another copy may be running)
        except OSError:
            pass
    made = add_made_from(d.name, "prompt", prompt) if prompt else None
    return {"file": dest.name, "kept": False, "made_from": made}


def _drain(stream, size: int) -> None:
    while size:
        b = stream.read(min(size, 4 * 2**20))
        if not b:
            return
        size -= len(b)


# ================================================================================================= library / docs
def colour_info(d: Path) -> dict | None:
    """The Overview's Colour & look (0.4): colour\\colour.json's summary + per shot its frames, words, colours."""
    c = read_json(d / "colour" / "colour.json", None) if (d / "colour" / "colour.json").exists() else None
    if not c:
        return None
    fps = float(c.get("fps") or 25)
    return {"summary": c.get("summary") or {}, "made_from": c.get("made_from"),
            "shots": [{"start": x["start"], "end": x["end"], "tc": frame_to_tc(x["start"], fps),
                       "tc_end": frame_to_tc(x["end"], fps), "words": x.get("words") or [],
                       "palette": x.get("palette") or []} for x in c.get("shots", [])]}


def _mtime(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except OSError:
        return 0.0


def memory() -> dict:
    """Claude's memory page (0.4): knowledge.memory() (videos, effects, lessons) + what was saved (effects for
    DaVinci Resolve, graphics) and how many prompts there are. memory.md is rewritten when what it is made of changed."""
    M = dict(KN.memory())
    # memory.md is stale when a card, a rating (outcome.json), a lesson or an answer on sound effects is newer
    src = [p for d in (KN.LOCAL_REFS, KN.SHARED_REFS) if d.exists() for p in d.glob("*.json")] + KN._outcomes() + [
        p for p in (KN.MAKING_LESSONS, KN.LOCAL_MAKING, KN.SHARED_LESSONS, KN.LOCAL_LESSONS) if p.exists()] + (
        list(ANALYSIS.glob("*/feedback/verdicts.json")) if ANALYSIS.exists() else [])
    if not KN.MEMORY.exists() or KN.MEMORY.stat().st_mtime < max([_mtime(p) for p in src] or [0]):
        try:
            KN.memory_index()
        except OSError:
            pass
    lib = library()
    M["saved"] = {"effects": len(lib["items"]), "graphics": sum(1 for g in lib["graphics"] if g.get("kind") == "yours"),
                  "examples": sum(1 for g in lib["graphics"] if g.get("kind") != "yours"), "picks": len(lib["picks"])}
    M["prompts"] = PR.count()
    return M


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
    picks, videos = [], []
    for pr in list_projects():
        pk = (read_json(library_picks_path(pr["name"]), {}) or {}).get("picks", {})
        picks += [{"project": pr["name"], "effect": k, **v} for k, v in pk.items() if v.get("pick")]
        last = PROJECTS / pr["name"] / "build" / f"{pr['plans'][-1]}.json" if pr["plans"] else None
        pl = (read_json(last, {}) or {}) if last else {}
        videos.append({"name": pr["name"], "width": pl.get("width"), "height": pl.get("height"), "fps": pl.get("fps"),
                       "overlays": [s["name"] for s in OS.project_overlays(pr["name"])]})
    return {"items": items, "picks": picks, "graphics": OS.library(), "videos": videos}


# ================================================================================================= skills (Tools > Skills)
SKILLS = LAB / ".claude" / "skills"
# what each skill does in the app's words (the SKILL.md descriptions are written for Claude), how to type it, where the
# app runs it for you; a skill missing here shows the first sentence of its description
SKILL_INFO = {
    "analyze-reference": {"brief": "Claude checks a video you analysed: it looks at every effect and names it - and "
                                   "learns from your verdicts when you send feedback.",
                          "uses": ["/analyze-reference <video name or file>"], "task": "review",
                          "where": "Analyze - Send to Claude, Send feedback to Claude"},
    "write-script": {"brief": "Claude prepares what you say on camera: it checks a script you have against what makes "
                              "talking videos hold attention (hook, structure, re-hooks, call to action) and rewrites "
                              "it in your voice - or writes one from zero from your answers to a few questions.",
                     "uses": ["/write-script improve <script id>", "/write-script request <request id>",
                              "/write-script check <script id>", "/write-script hooks <script id>", "/write-script"],
                     "task": "script", "where": "Prepare - Improve my script, Write one from zero"},
    "write-title": {"brief": "Claude writes what makes people click - and what the video then keeps: about ten titles, "
                             "two or three thumbnail ideas with the words on them and the shot to film, the hook that "
                             "keeps the promise. For a finished video: the title, the description with chapters, "
                             "hashtags and thumbnails A / B / C, checked before you post.",
                    "uses": ["/write-title request <request id>", "/write-title package <your video>",
                             "/write-title ab <your video>", "/write-title"],
                    "task": "title", "where": "Prepare - Title & thumbnail first; Edit - a video's Publish tab"},
    "recreate-video": {"brief": "Claude edits your clips - an exact copy of a video you analysed, in the style of up "
                                "to three, from your words or one of your prompts - first as a preview, then in "
                                "DaVinci Resolve.",
                       "uses": ["/recreate-video <reference> <your video>", "/recreate-video feel:<video>,<video> <your video>",
                                "/recreate-video want:fast_hook <your video> - want: <your words>",
                                "/recreate-video prompt:<prompt id> <your video>", "/recreate-video improve <your video>"],
                       "task": "recreate",
                       "where": "Edit - New edit, How did it turn out?"},
    "generate-video": {"brief": "Claude makes a video from zero: a motion-graphics video written as HTML and rendered "
                                "to your song, or the plan of a video for AI video tools with every prompt.",
                       "uses": ["/generate-video graphics <name> - want: <what it is about>",
                                "/generate-video ai <name> - want: <your idea> - tool: Higgsfield"], "task": "generate",
                       "where": "Generate - A motion-graphics video, With AI video tools"},
    "write-prompt": {"brief": "Claude checks, improves or writes prompts: briefs, AI video and image prompts, hooks "
                              "and scripts.",
                     "uses": ["/write-prompt analyse <prompt id>", "/write-prompt optimize <prompt id>",
                              "/write-prompt brief - want: <what you want to make>"], "task": "prompt",
                     "where": "Generate - Prompts for AI tools; the prompt library: Optimize, Add prompts"},
    "whats-next": {"brief": "Where MotionLab stands and what to build next.", "uses": ["/whats-next"], "task": "plan",
                   "dev": True},
}
SKILL_ORDER = ["analyze-reference", "write-script", "write-title", "recreate-video", "generate-video", "write-prompt",
               "whats-next"]


def skills() -> list[dict]:
    """The project's Claude Code skills (.claude\\skills\\<name>\\SKILL.md): name, what it does, how to type it."""
    out = []
    for f in sorted(SKILLS.glob("*/SKILL.md")):
        meta: dict = {}
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        if lines and lines[0].strip() == "---":
            for ln in lines[1:]:
                if ln.strip() == "---":
                    break
                k, _, v = ln.partition(":")
                meta[k.strip()] = v.strip().strip('"')
        name = meta.get("name") or f.parent.name
        info = SKILL_INFO.get(name, {})
        desc = re.sub(r"^MotionLab\s*-\s*", "", meta.get("description", ""))
        out.append({"name": name, "brief": info.get("brief") or re.split(r"(?<=[.:])\s", desc, maxsplit=1)[0][:220],
                    "uses": info.get("uses") or [f"/{name} {meta.get('argument-hint', '')}".strip()],
                    "task": info.get("task", "free"), "where": info.get("where", ""), "dev": bool(info.get("dev"))})
    return sorted(out, key=lambda s: (s["dev"], SKILL_ORDER.index(s["name"]) if s["name"] in SKILL_ORDER else 99,
                                      s["name"]))


def text_file(relpath: str, limit: int = 400_000) -> str:
    p = (LAB / relpath).resolve()
    if LAB not in p.parents or p.suffix.lower() not in (".md", ".txt", ".json", ".comp", ".py", ".csv", ".setting"):
        raise PermissionError(relpath)
    return p.read_text(encoding="utf-8", errors="replace")[:limit]
