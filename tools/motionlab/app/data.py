"""Everything the app shows, read from the lab folders. Read-only, except the user's verdicts
(analysis\\<name>\\feedback\\verdicts.json + exported MOTIONLAB FEEDBACK files) and library picks
(projects\\<name>\\build\\library_picks.json). Deleting is trash.py (the user's Delete buttons)."""
from __future__ import annotations

import datetime
import functools
import json
import os
import re
import threading
import time
from pathlib import Path

from motionlab import i18n as I18N
from motionlab import taxonomy
from motionlab import knowledge as KN
from motionlab import overlay_settings as OS
from motionlab import profile as PF
from motionlab import prompts as PR
from motionlab import editreq as ER
from motionlab.app import live as LV
from motionlab.project import APPLE_DOUBLE, PHOTO_EXT, clip_files, is_junk
from motionlab.styles import FOCUS, fmt as video_format, label as style_label
from motionlab.timecode import frame_to_tc
from motionlab.util import ANALYSIS, LAB

PROJECTS = LAB / "projects"
LIBRARY = LAB / "library"
DOCS = LAB / "docs"
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".m4v", ".avi", ".webm", ".mts", ".mxf"}
AUDIO_EXT = {".mp3", ".m4a", ".wav", ".aac", ".flac", ".ogg"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic"}     # the photos of a downloaded carousel / photo post
# a video's clips (2026-10-24): videos and photos - a photo is a still shot of the edit (motionlab\photos.py)
CLIP_EXT = VIDEO_EXT | PHOTO_EXT
_cache: dict[str, tuple[float, object]] = {}
_lock = threading.Lock()


@functools.lru_cache(maxsize=1 << 16)
def _rel_existing(p: str) -> str | None:
    """rel() of an existing absolute path, remembered: resolve() opens the path on Windows (~0.3-0.5 ms), and the pages
    list the same sheets, frames and clips on every visit. A missing path raises here (so it is never remembered) and
    rel() resolves it as before."""
    r = Path(os.path.realpath(p, strict=True))                  # = resolve() of an existing path
    try:
        return r.relative_to(LAB).as_posix()
    except ValueError:
        return None


def rel(p: Path | str) -> str | None:
    """Lab-relative path with forward slashes (what /files/ serves), or None if outside the lab."""
    try:
        q = Path(p)
        if q.is_absolute():
            try:
                return _rel_existing(str(q))
            except OSError:
                pass
        return q.resolve().relative_to(LAB).as_posix()
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


def write_text_atomic(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
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


class Words(str):
    """Words in the app's language (Settings > Language) that keep their English (.en): a job's title shows in the
    language on the Jobs page, while its log, .app\\jobs\\history.jsonl and Report a problem keep the English (job
    logs never follow the language)."""
    en = ""

    @classmethod
    def of(cls, shown: str, en: str) -> Words:          # (annotations are not evaluated: __future__)
        w = cls(shown)
        w.en = en
        return w


def words(en: str, **v) -> Words:
    """I18N.t(en, **v) that keeps its English; a var that is Words itself goes into the English as its .en."""
    return Words.of(I18N.t(en, **v), I18N.fill(I18N.english(en), {k: getattr(x, "en", x) for k, x in v.items()}))


def safe_name(name: str) -> str:
    """A folder name from a URL: one name - no separators, no '..', nothing Windows refuses in a name, no control
    characters. (2026-10-27: it allowed only letters, digits and a few signs, so a friend's video folder with a #, a !
    or an emoji in its name was listed but never opened - the Editor "does not even open up".)"""
    if not (name or "").strip() or ".." in name or re.search(r'[\\/:*?"<>|\x00-\x1f\x7f]', name):
        raise ValueError(I18N.t("bad name: {name}", name=repr(name)))
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


def knowledge_overview() -> dict:
    """GET /api/knowledge = Claude's memory > Shared knowledge: share_pending() rebuilds only the cards whose analysis
    changed, then knowledge.overview() reads them as they are (the tab stays fast with many analyses)."""
    share_pending()
    return KN.overview(rebuild=[])


def style_choices() -> dict:
    """GET /api/styles - every "In the style of" picker (2026-10-18, the user: "normal people or my friends wouldnt
    know what that is? so it would be fine to only look in style of "prompts" or "videos" they already analize"):
    `videos` = this PC's analyses (key = the analysis folder, what style.find and the saved requests take; self-test
    videos left out) with their picture and readable name; `prompts` = the prompt library's scripts and hooks (the
    user's good-rated first, then Claude's stars). Friends' cards are left out on purpose: they stay in Claude's
    memory as data, marked as shared. Light: knowledge.style() and the profiles are cached per file change."""
    from motionlab import script as SC
    from motionlab import style as ST
    videos = []
    for s in PR.all_styles():
        sp = ((PF.profile(s["name"]) or {}).get("content") or {}).get("speech") or {}
        videos.append({"key": s["name"], "title": s["title"], "label": s.get("label") or s["title"],
                       "by": s.get("by") or "", "platform": s.get("platform") or "", "picture": s.get("thumb"),
                       "format": (s.get("format") or {}).get("label"), "category_label": s.get("category_label"),
                       "focus": s.get("focus"), "talk_pct": sp.get("talk_pct"),
                       "cuts_per_min": (s.get("pacing") or {}).get("cuts_per_min"),
                       "checked": bool(s.get("breakdown")) or bool(s["effects"]) and s["reviewed"] >= s["effects"],
                       "summary": (s.get("summary") or "")[:220], "line": s.get("line"), "analysed": s.get("analysed")})
    videos.sort(key=lambda v: str(v.get("analysed") or ""), reverse=True)
    prompts = []
    for r in PR.load_all("script") + PR.load_all("hook"):
        src, res = r.get("source") or {}, (r.get("result") or {}).get("rating")
        first = next((ln.strip() for ln in SC.spoken(r.get("text", ""))[0].split("\n") if ln.strip()), "")
        prompts.append({"id": r["id"], "kind": r["kind"],
                        "title": r.get("title") or PR.auto_title(r.get("text", ""), r["kind"]),
                        "first": first[:160], "rating": res, "stars": (r.get("review") or {}).get("stars"),
                        "source": (I18N.t("{creator}'s", creator=src["creator"]) if src.get("creator")
                                   else I18N.t("a creator's")) if src.get("type") == "creator" else I18N.t("yours"),
                        "updated": r.get("updated") or r.get("added") or ""})
    prompts.sort(key=lambda p: p["updated"], reverse=True)
    prompts.sort(key=lambda p: ({"good": 0, "bad": 2}.get(p["rating"], 1),
                                -(p["stars"] if p["stars"] is not None else -1)))
    return {"videos": videos, "prompts": prompts, "max": ST.MAX_REFS}


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
            "done_t": _mtime(d / "events.json"),               # the NEW badge (2026-10-24): when the analysis ended
            **_kind(d.name, ev, v),
            "report": rel(d / "report.html") if (d / "report.html").exists() else None,
            "feedback_files": sorted(p.name for p in (d / "feedback").glob("*.txt")) if (d / "feedback").exists() else [],
            "source": src, "flow": flow(d.name, ev, S, pend), "review_prompt": review_prompt(src or d.name, d.name),
            "lines": (PF.profile(d.name) or {}).get("lines", {}), "breakdown": bool(ev.get("breakdown")),
        })
    return out


def _kind(name: str, ev: dict, v: dict) -> dict:
    """Category, tags, link, format and pacing of an analysis (for the cards, filters and the analysis page) + its
    readable name (2026-10-19: knowledge.label() - the user's own name, Claude's, the title without yt-dlp's [id]);
    keys, links and commands keep the folder name."""
    m = KN.meta(name, ev)
    bd = ev.get("breakdown") if isinstance(ev.get("breakdown"), dict) else {}
    lab = KN.label({"title": m["title"], "uploader": m["uploader"], "platform": m["platform"], "url": m["url"],
                    "breakdown": bd}, user_label=m.get("label"))
    return {"label": lab["name"], "by": lab["by"],
            "category": m["category"], "category_label": style_label(m["category"]), "tags": m["tags"],
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
        # the names only - the same list as list_projects() gives, without working out every project (audit 2026-10-19)
        "projects": [p.name for p in sorted(PROJECTS.iterdir(), key=lambda p: p.name.lower()) if p.is_dir()]
        if PROJECTS.exists() else [],
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
    from motionlab import notes as NT                  # 2026-10-27: a video downloaded for its notes is not waiting
    noted = NT.videos()
    files = [Path(c["path"]) for c in candidate_videos() if not c["analysed"] and c["name"].lower() not in noted]
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
    made = pl.get("made_by") or {}
    if not isinstance(made, dict):  # hand-written plans note the tool as one string
        made = {"tool": str(made)}
    return {"file": p.name, "rel": rel(p), "name": pl.get("name"), "version": p.stem.split("_")[-1],
            "frames": pl.get("frames"), "fps": pl.get("fps"), "width": pl.get("width"), "height": pl.get("height"),
            "layers": len(pl.get("layers", [])), "levels": pl.get("levels", "single"),
            "duration_tc": frame_to_tc(max(0, int(pl.get("frames") or 1) - 1), float(pl.get("fps") or 25)),
            "reference": rel(pl["reference"]) if pl.get("reference") and Path(pl["reference"]).exists() else None,
            "made_by": made.get("tool"), "style": made.get("style"),
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
    clips = clip_files(d, VIDEO_EXT) or clip_files(d, PHOTO_EXT)     # a video's frame, else a photo (GET /api/thumb)
    return {"video": rel(clips[0]), "f": 25 if clips[0].suffix.lower() in VIDEO_EXT else 0, "fps": 25.0} \
        if clips else None


def _label(b: Path) -> str | None:
    """The name the app shows for a video when the user renamed it (build\\project.json "label"; rename_project)."""
    return (read_json(b / "project.json", {}) or {}).get("label") or None


def _in_editor(b: Path) -> bool:
    """A video made from zero lives in the Generator; the user can move it to the Editor (project.json "in_editor")."""
    return bool((read_json(b / "project.json", {}) or {}).get("in_editor"))


def move_project(name: str, to_editor: bool) -> dict:
    """0.4.3.5 (the user: "do not duplicate info like that"): a video made from zero shows in ONE section - the
    Generator, or the Editor once moved there (build\\project.json "in_editor"; nothing else moves)."""
    d = PROJECTS / safe_name(name)
    if not d.is_dir():
        raise FileNotFoundError(name)
    p = d / "build" / "project.json"
    out = {**(read_json(p, {}) or {}), "in_editor": bool(to_editor), "updated": stamp()}
    write_json_atomic(p, out)
    return {"name": d.name, "in_editor": out["in_editor"]}


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
        clips = clip_files(d)                             # videos + photos, never a Mac's ._ file
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
            "photos": sum(p.suffix.lower() in PHOTO_EXT for p in clips),
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
            "in_editor": _in_editor(b),
            "rating": ((outcome.get("aspects") or {}).get("overall") or {}).get("rating"),
            "reviewed": _reviewed(b, outcome, nt),
            "next": outcome.get("next"), "title": pkg.get("title") or None,
            # the NEW badge (2026-10-24): a finished render (whole file) - never a video only made or given clips
            "done_t": (lambda r: r[-1].stat().st_mtime if r else None)(LV.renders_done(b)),
            # 0.6.0: made For my brand (its edit / generate request carried My Brand) - My Brand's Overview shows them first
            "for_brand": any((read_json(b / n, {}) or {}).get("brand") for n in ("edit_request.json", "generate_request.json")),
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
                                  "units": [{"name": I18N.t("{n} Edit-page clips", n=len(clips)), "track": None,
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
        raise ValueError(I18N.t("bad graphic name: {name}", name=repr(overlay)))
    f = PROJECTS / safe_name(project) / "build" / "overlays" / overlay
    if not (f / "index.html").exists():
        raise FileNotFoundError(I18N.t("{video}: no graphic {name}", video=project, name=overlay))
    return f


def save_overlay_values(project: str, overlay: str, values, preset: str = "") -> dict:
    """The Graphics tab's Save: the user's settings into the overlay's overlay.json (validated against what its
    index.html declares); the render job then uses them. preset (0.4.6) = one of its looks (OS.looks): a graphic made
    before its example had looks takes the example's design first (OS.adopt_example)."""
    f = overlay_folder(project, overlay)
    if preset:
        if preset not in OS.looks(f)["looks"]:
            raise ValueError(I18N.t("{graphic} has no look '{look}'", graphic=overlay, look=preset))
        if OS.looks(f)["upgrade"]:
            OS.adopt_example(f)
        return OS.apply_preset(f, preset)
    return OS.set_values(f, values if isinstance(values, dict) else {})


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
        raise ValueError(I18N.t("a thumbnail is A, B or C"))
    f = publish_dir(name) / "thumbs" / tid
    if not (f / "index.html").exists():
        raise FileNotFoundError(I18N.t("{video}: no thumbnail {id} yet", video=name, id=tid))
    return f


def publish_info(name: str) -> dict:
    """The Publish tab: package.json as the tools wrote it (each thumbnail + its settings for the form), the title
    records linked to this video (prompt library kind title, "project"), the edit's rate / length for the chapters,
    the designs, the pictures the user brought; "post" = the newest render's copy without its downloaded song."""
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
    post = read_json(pub / PB.POST_FILE, {}) or {}     # 0.5.4: the newest render without its downloaded song
    post = {**post, "rel": rel(pub / post["video"])} if renders and post.get("from") == renders[-1].name and (
        pub / str(post.get("video"))).is_file() else None
    return {"name": d.name, "folder": rel(pub), "exists": (pub / "package.json").exists(), "package": {**pkg, "thumbnails": thumbs},
            "post": post,
            "records": recs, "fps": pl.get("fps"), "frames": pl.get("frames"), "plan": plan.name if plan else None,
            "templates": templates, "face_detector": face, "render": renders[-1].name if renders else None,
            "styles": _thumb_styles(),                       # 0.4.5: thumbnail sets whose patterns Claude found
            "clips": len(clip_files(d, VIDEO_EXT)),
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
            raise ValueError(I18N.t("chapters: a list of [frame, name]"))
        clean = []
        for c in chs:
            try:
                f, n = (c[0], c[1]) if isinstance(c, (list, tuple)) else (c.get("f"), c.get("name"))
                clean.append((int(f), " ".join(str(n or "").split())[:100]))
            except (TypeError, ValueError, IndexError, AttributeError):
                raise ValueError(I18N.t("each chapter needs a frame number and a name")) from None
        chs = sorted(clean)
    tags = body.get("hashtags")
    tf = str(body.get("titles_from") or "")
    if tf and not re.fullmatch(r"title-\d{3,}", tf):
        raise ValueError(I18N.t("not a title record: {id}", id=repr(tf)))
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
        raise ValueError(I18N.t("a picture: .jpg, .png or .webp"))
    if len(raw) > 30_000_000:
        raise ValueError(I18N.t("pictures up to 30 MB"))
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
    files = clip_files(d)                                 # videos + photos; never a Mac's ._ file or a photo's twin
    listed = {p.name.lower() for p in files}
    sources = []
    for sid, s in sorted(srcs.items()):
        if Path(s["path"]).name.lower() not in listed and Path(s["path"]).exists():
            continue                                      # junk an older version registered: not a clip
        meta = (read_json(b / "cache" / f"{sid}.color.json", {}) or read_json(b / "cache" / f"{sid}.json", {})
                or {})                                    # colour caches (0.3.0+) or grey ones
        p = Path(s["path"])
        photo = p.suffix.lower() in PHOTO_EXT
        sources.append({"id": sid, "name": s["name"], "size": p.stat().st_size if p.exists() else None,
                        "exists": p.exists(), "fps": meta.get("src_fps"), "frames": meta.get("src_frames"),
                        "duration_s": None if photo else (meta.get("src_frames") or 0) / (meta.get("src_fps") or 1) or None,
                        "resolution": f"{meta.get('src_width')}x{meta.get('src_height')}" if meta else None,
                        "cached": bool(meta.get("complete")), "photo": photo,
                        "board": rel(b / "boards" / f"{sid}_01.jpg") if (b / "boards" / f"{sid}_01.jpg").exists() else None})
    known = {Path(s["path"]).name.lower() for s in srcs.values() if s.get("path")}
    for p in files:                                       # clips not prepared yet (no sources.json entry): listed too
        if p.name.lower() not in known:
            sources.append({"id": None, "name": p.name, "size": p.stat().st_size, "exists": True, "fps": None,
                            "frames": None, "duration_s": None, "resolution": None, "cached": False, "board": None,
                            "photo": p.suffix.lower() in PHOTO_EXT})
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
        elif isinstance(x, dict) and x.get("kind") in ("style", "reference"):   # 2026-10-18: names, not keys
            x["refs"] = _made_refs(str(x.get("id") or ""))
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
    media = [{"label": I18N.t("render {name}", name=p.name), "path": str(p)}
             for p in sorted(b.glob("*.mp4"), key=lambda q: q.stat().st_mtime, reverse=True)] if b.exists() else []
    media += [{"label": I18N.t("your clip {name}", name=p.name), "path": str(p)} for p in files
              if p.suffix.lower() in VIDEO_EXT]
    from motionlab import speech as SP
    used = _overlays_in_plans(sorted(b.glob("plan_v*.json"))) if b.exists() and overlays else {}
    for o in overlays:
        o["used_in"] = used.get(str((LAB / o["folder"] / f"{o['name']}.mov").resolve()).lower(), [])
        o["looks"] = OS.looks(LAB / o["folder"])                         # 0.4.6: Classic | Clean box ...
    outcome = read_json(b / "outcome.json", {}) or {}
    return {"name": d.name, "label": _label(b), "sources": sources, "plans": plans, "renders": renders,
            "compares": compares, "overlays": overlays, "media": media,
            "speech": {"available": SP.available(), "small": SP.model_ready("small"), "base": SP.model_ready("base")},
            "verifies": verifies, "resolve": resolve, "check_sheets": sheets,
            "boards": [rel(p) for p in sorted((b / "boards").glob("*.jpg"))] if (b / "boards").exists() else [],
            "edit_scripts": [rel(p) for p in sorted(b.glob("edit_v*.py"))] if b.exists() else [],
            "library_picks": picks.get("picks", {}), "picks_updated": picks.get("updated"),
            "made_from": made, "outcome": outcome, "reviewed": _reviewed(b, outcome, newest["mtime"] if newest else None),
            "asked": _asked(b),
            "generated": any(x.get("kind") == "generated" for x in made if isinstance(x, dict)), "in_editor": _in_editor(b),
            "picture": _picture(d, b, LAB / newest["rel"] if newest else None, newest or {}),
            "publish": (b / "publish" / "package.json").exists()}


def _asked(b: Path) -> dict:
    """What New edit asked for the layers a quick draft leaves to Claude (captions, sound effects; a talking video) -
    *Finish it with Claude* starts from it (2026-10-24). {} = no request. `sfx_made` (0.5.4) = the newest plan has its
    sound effects already (a quick draft makes them): they stay, the dialog does not offer them again."""
    plans = sorted(b.glob("plan_v*.json"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 0)) if b.is_dir() else []
    made = bool(plans) and bool((read_json(plans[-1], {}) or {}).get("sfx"))
    req = read_json(b / "edit_request.json", {}) or {}
    if not isinstance(req, dict) or not req:
        return {"sfx_made": True} if made else {}
    return {"captions": (req.get("style") or {}).get("captions") or "", "sfx": (req.get("sfx") or {}).get("amount") or "",
            "talk": req.get("sound") == "talk" or bool(re.fullmatch(ER.TALK_ID, str(req.get("prompt") or ""))),
            "sfx_made": made}


# ------------------------------------------------------------------ 0.3.3: create a video, and how it turned out
ASPECTS = ("sound", "sfx", "colour", "captions", "graphics", "effects", "pacing", "packaging", "overall")
OUTCOME_NEXT = ("fix", "start_over", "finish")    # 0.4.2: How did it turn out? - fix this version / start over;
FINISH_ADD = ("graphics", "captions", "sfx", "colour")  # 2026-10-24: finish a quick draft = these layers on its cuts
CTR_IDS = re.compile(r"[A-Z]")                # 0.4.3: a thumbnail variant (thumbnail.py make --id A / B / C)


def new_project(name: str) -> dict:
    """Videos > Create video: an empty projects\\<name>\\ for the user's clips (nothing else is written)."""
    name = safe_name(str(name).strip())
    if name.startswith((".", " ")) or name.endswith((".", " ")):
        raise ValueError(I18N.t("a name cannot start or end with a dot or a space"))
    d = PROJECTS / name
    if d.exists():
        raise ValueError(I18N.t("projects\\{name} exists already - pick it in the list", name=name))
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
                raise ValueError(I18N.t("another video is called “{name}” already", name=label))
    p = d / "build" / "project.json"
    out = {**(read_json(p, {}) or {}), "label": label if label and label != d.name else None, "updated": stamp()}
    write_json_atomic(p, out)
    return {"name": d.name, "label": out["label"]}


def _made_refs(ids: str) -> list[dict]:
    """A made_from "style" / "reference" entry's videos by name (2026-10-18): this PC's analysis -> its readable
    name; a friend's card -> its name + who shared it (so *Made from* shows no folder name or 12-hex id). The entry
    holds the keys joined by ", " (save_edit_request) - a key may contain ", " itself, so the longest run of pieces
    that names a video wins."""
    cards = None

    def find(k: str) -> dict | None:
        nonlocal cards
        if k and ".." not in k and "/" not in k and "\\" not in k and (ANALYSIS / k / "events.json").exists():
            s = KN.style(k)
            return {"key": k, "label": (s or {}).get("label") or k, "analysis": k}
        if cards is None:
            cards = KN.all_cards()
        low = k.lower()
        c = next((c for c in cards if low in (str(c.get("analysis") or "").lower(), str(c.get("video_id")).lower(),
                                              str(c.get("title") or "").lower())), None)
        if not c:
            return None
        friend = c.get("origin") == "shared" and c.get("author") != KN.author()
        return {"key": k, "label": KN.label(c)["name"], "analysis": KN._analysis_here(c),
                "author": c.get("author") if friend else None,
                "shared": (c.get("made_with") or {}).get("carded") if friend else None}
    parts, out, i = ids.split(", "), [], 0
    while i < len(parts):
        for j in range(len(parts), i, -1):
            r = find(", ".join(parts[i:j]).strip())
            if r:
                out.append(r)
                i = j
                break
        else:
            out.append({"key": parts[i], "label": parts[i]})
            i += 1
    return out


def add_made_from(name: str, kind: str, ref: str) -> list:
    """What a video is made from (New edit): a reference copied 1:1 (an analysis), up to three videos' style
    ("style": names joined by ", "), the user's words ("words": presets / their words) or a prompt -
    build\\made_from.json."""
    if kind not in ("reference", "prompt", "style", "words", "generated"):
        raise ValueError(I18N.t("made from a reference, videos' style, your words, a prompt or from zero"))
    ref = safe_name(ref) if kind == "reference" else " ".join(str(ref).split())[:300]
    if kind == "prompt" and not re.fullmatch(r"(shot|image|hook|script|brief|title)-\d{3,}", ref):
        raise ValueError(I18N.t("not a prompt id: {id}", id=repr(ref)))
    d = PROJECTS / safe_name(name)
    if not d.is_dir():
        raise FileNotFoundError(name)
    p = d / "build" / "made_from.json"
    items = [x for x in (read_json(p, []) or []) if not (x.get("kind") == kind and x.get("id") == ref)]
    items.append({"kind": kind, "id": ref, "date": stamp()})
    write_json_atomic(p, items)
    return items


# ------------------------------------------------------------------ New edit - what the user asked for
def edit_options() -> dict:
    """New edit's choices (motionlab.editreq.options: the style questions, palettes, sound effects, presets,
    downloaded songs, how many videos a style may mix)."""
    return ER.options()


def edit_request(name: str) -> dict:
    p = PROJECTS / safe_name(name) / "build" / "edit_request.json"
    if not p.exists():
        raise FileNotFoundError(I18N.t("{video}: no edit request yet (Editor > New edit)", video=name))
    return read_json(p, {}) or {}


def save_edit_request(name: str, body: dict) -> dict:
    """New edit: what the user picked on the page's steps (clips, context, style, sound, final - motionlab.editreq),
    checked, saved as build\\edit_request.json (the data: the quick draft reads it) + build\\edit_brief.md (the same
    in words, step by step: what /recreate-video request <p> follows), and added to made_from.json. The user's words
    never pass through a command line."""
    d = PROJECTS / safe_name(name)
    if not d.is_dir():
        raise FileNotFoundError(name)
    req = ER.clean(body, d)
    req["date"] = stamp()
    write_json_atomic(d / "build" / "edit_request.json", req)
    write_text_atomic(d / "build" / "edit_brief.md", ER.brief(req, _brief_facts(d, req)))
    start_brief(d)
    made = []
    for kind, ref in ER.made_from(req):
        made = add_made_from(d.name, kind, ref)
    return {"request": req, "made_from": made, "command": f"/recreate-video request {d.name}"}


def start_brief(d: Path) -> None:
    """0.5.3 (C1/C2): tools\\brief.py <video> in the background - build\\brief.md is ready (a few seconds: the beats,
    the styles) by the time Claude's window opens; the skills make it themselves when it is missing or older than
    the request. Never fails the save."""
    import subprocess
    import sys
    try:
        py = Path(sys.executable)
        py = py.with_name("python.exe") if py.name.lower() == "pythonw.exe" else py
        subprocess.Popen([str(py), str(LAB / "tools" / "brief.py"), d.name], cwd=str(LAB), stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except OSError:
        pass


def _brief_facts(d: Path, req: dict) -> dict:
    """What the brief names besides the request: the video's readable name, its clips and songs, the references'
    readable names, the prompt's title."""
    from motionlab import style as ST
    files = [p for p in d.iterdir() if p.is_file()]
    refs = {}
    for k in req["like"]:
        c = ST.find(k)
        refs[k] = KN.label(c).get("name") if c else k
    try:
        pr = PR.get(req["prompt"]) if req["prompt"] else None
    except ValueError:
        pr = None
    clips = clip_files(d)
    return {"project": d.name, "label": _label(d / "build"), "clips": len(clips),
            "photos": [p.name for p in clips if p.suffix.lower() in PHOTO_EXT],
            "songs": sorted(p.name for p in files if p.suffix.lower() in AUDIO_EXT), "refs": refs,
            "prompt": {"title": pr.get("title") or pr.get("title_auto"), "kind": pr.get("kind")} if pr else None}


# ------------------------------------------------------------------ 0.4: Generate - a video from zero
GEN_KINDS = ("graphics", "ai")
AI_TOOLS = ["Higgsfield", "Seedance", "Kling", "Runway", "Veo", "Sora", "Hailuo", "Pika", "Luma", "InVideo AI",
            "Pictory", "HeyGen", "Synthesia"]


def generate_options() -> dict:
    """Generate's dialogs: the AI tools offered, the songs downloaded (refs\\audio\\), HyperFrames ready or not."""
    from . import system
    from motionlab import looks as LK
    from motionlab import sfx as SFX
    songs = [{"name": p.name, "rel": rel(p)} for p in sorted((LAB / "refs" / "audio").glob("*"))
             if p.is_file() and p.suffix.lower() in AUDIO_EXT] if (LAB / "refs" / "audio").exists() else []
    ls = SFX.last_song()                                # 0.5.3 (E1): what Claude would otherwise guess, asked
    last = rel(Path(ls[0])) if ls and any(s["rel"] == rel(Path(ls[0])) for s in songs) else None
    try:
        looks = [{"id": i, "name": lk.get("name", i), "palette": list((lk.get("palette") or {}).values())[:4]}
                 for i, lk in LK.all_looks().items()]
    except (OSError, ValueError, KeyError):
        looks = []
    return {"tools": AI_TOOLS, "songs": songs, "hyperframes": bool(system.find("hyperframes")),
            "node": bool(system.find("node")), "looks": looks, "last_song": last}


_MOTION: dict = {"sig": None, "json": None}
_MOTION_LOCK = threading.Lock()


def _motion_sig(TP) -> tuple:
    """What motion() is made of, as directory listings (each entry's name, time and size - no file is opened): every
    template folder of the library and of this PC's own templates (library\\motion_graphics\\local\\<pack>\\<id>\\,
    2026-10-18), the packs' folders (pack.json, cards.json). Any change there = the answer is worked out again."""
    out: list = [str(TP.root()), TP.root() == TP.ROOT]

    def listing(d: Path, depth: int) -> None:
        try:
            with os.scandir(d) as it:
                ents = sorted(it, key=lambda e: e.name)
        except OSError:
            out.append((str(d), None))
            return
        row = []
        for e in ents:
            try:
                if depth and e.is_dir():         # listed below, so its own entries show what changed in it (NTFS
                    row.append((e.name, True))   # updates a folder's time in its parent's listing a call late)
                    continue
                st = e.stat()
                row.append((e.name, e.is_dir(), st.st_mtime_ns, st.st_size))
            except OSError:
                row.append((e.name, None))
        out.append((str(d), tuple(row)))
        for e in ents:
            if depth and e.is_dir():
                listing(Path(e.path), depth - 1)

    listing(TP.MOTION, 1)
    listing(LAB / "library" / "motion_graphics", 3)
    listing(TP.root(), 1)
    return tuple(out)


def motion() -> dict:
    """The Motion Graphics page (0.5.0): the library of motion templates (tools\\overlays\\motion\\: their settings, size,
    picture, the clips they were learned from) + every pack of captured clips with Claude's cards (motionlab.templates).
    Worked out again only when a file it is made of changed (_motion_sig, ~0.15-0.3 s otherwise on every tab of the
    page and every Generate dialog); each call gets its own copy."""
    from motionlab import templates as TP
    sig = _motion_sig(TP)                      # before reading: a file changed meanwhile shows on the next call
    with _MOTION_LOCK:
        if _MOTION["sig"] == sig:
            return json.loads(_MOTION["json"])
    cat = TP.catalog()
    for t in cat["library"]:
        f = LAB / t["folder"]
        c = OS.conf(f)
        try:
            decl = OS.declared(f)
        except ValueError:
            decl = []
        th = f / "thumb.png"
        t.update(frames=int(c.get("frames") or 0), fps=float(c.get("fps") or 30), width=int(c.get("width") or 0),
                 height=int(c.get("height") or 0), settings=decl,
                 thumb=rel(th) if th.exists() else None, thumb_v=int(th.stat().st_mtime) if th.exists() else 0,
                 created=_created(f))                     # the NEW badge: when it came (a new folder, an update)
    clips = {f"{p['pack']}/{it['id']}": it for p in cat["packs"] for it in p["items"]}
    for t in cat["library"]:                          # the clips a template learned from, ready to play beside it
        t["sources"] = [{"pack": s.get("pack"), "clip": s.get("clip"), "what": s.get("what", ""),
                         "file": (clips.get(f"{s.get('pack')}/{s.get('clip')}") or {}).get("file")}
                        for s in t.get("learned_from", [])]
    cat["kinds"] = sorted({t.get("kind", "other") for t in cat["library"]})
    with _MOTION_LOCK:
        _MOTION["sig"], _MOTION["json"] = sig, json.dumps(cat, ensure_ascii=False, default=str)
    return cat


def motion_pick(want: str, n: int = 6) -> list[dict]:
    """The templates that fit the words best (Generate's dialog suggests them while the user types)."""
    from motionlab import templates as TP
    return [{k: t.get(k) for k in ("id", "name", "kind", "what", "score", "matched")}
            for t in TP.pick(" ".join(str(want or "").split())[:3000], max(1, min(int(n), 12)))]


def _song(d: Path, music: str) -> str | None:
    """A song for Generate: a file in the video's folder (a name) or a download in refs\\audio\\ (lab-relative)."""
    if not music or music == "none":
        return None
    if Path(music).name == music and (d / music).is_file() and (d / music).suffix.lower() in AUDIO_EXT:
        return str(d / music)
    p = (LAB / music).resolve()
    if p.parent == (LAB / "refs" / "audio").resolve() and p.is_file() and p.suffix.lower() in AUDIO_EXT:
        return str(p)
    raise ValueError(I18N.t("{file}: not a song in the video's folder or in refs\\audio", file=music))


def save_generate_request(body: dict) -> dict:
    """Generate (0.4): a video from zero - a motion-graphics video (HyperFrames) or the plan + every prompt for AI
    video tools. The video gets its folder (projects\\<name>\\, made empty when new: a song or a logo can go
    there) and the request, checked, is saved as build\\generate_request.json for /generate-video request <name>."""
    from motionlab import style as ST
    kind = str(body.get("kind") or "")
    if kind not in GEN_KINDS:
        raise ValueError(I18N.t("kind: graphics or ai"))
    name = safe_name(" ".join(str(body.get("name") or "").split()))
    want = " ".join(str(body.get("want") or "").split())[:3000]
    if not want:
        raise ValueError(I18N.t("say what the video is about"))
    text = "\n".join(" ".join(ln.split()) for ln in str(body.get("text") or "").splitlines() if ln.strip())[:3000]
    like = [" ".join(str(x).split()) for x in (body.get("like") or []) if str(x).strip()]
    if len(like) > ST.MAX_REFS:
        raise ValueError(I18N.t("at most {n} videos for one style", n=ST.MAX_REFS))
    for x in like:
        if len(x) > 160 or ST.find(x) is None:
            raise ValueError(I18N.t("no analysed video called {name}", name=repr(x)))
    length = body.get("length_s")
    length = float(length) if length not in (None, "") else None
    if length is not None and not 3 <= length <= 900:
        raise ValueError(I18N.t("length: 3 to 900 seconds"))
    fmt = body.get("format") or None
    if fmt is not None and fmt not in ST.SIZES:
        raise ValueError(I18N.t("format: one of {choices}", choices=", ".join(ST.SIZES)))
    tool = " ".join(str(body.get("tool") or "").split())[:60]
    extra = {k: " ".join(str(body.get(k) or "").split())[:120] for k in ("colours", "font")}
    look = str(body.get("look") or "")                 # 0.5.3 (E1): a look of the templates, "surprise" or Claude's
    if look and look != "surprise":
        from motionlab import looks as LK
        if look not in LK.all_looks():
            raise ValueError(I18N.t("no look {id}", id=repr(look)))
    extra["look"] = look
    templates = [str(x) for x in (body.get("templates") or []) if str(x).strip()]      # 0.5.0: the Motion Graphics
    if templates:                                                                   # library's templates to use
        from motionlab import templates as TP
        have = {t["id"] for t in TP.library()}
        bad = [x for x in templates if x not in have]
        if bad or len(templates) > 12:
            raise ValueError(I18N.t("not in the Motion Graphics library: {ids}", ids=", ".join(bad)) if bad
                             else I18N.t("at most 12 templates"))
    extra["templates"] = templates
    d = PROJECTS / name
    b = d / "build"
    if b.exists() and not body.get("reuse") and (any(b.glob("plan_v*.json")) or any(b.glob("*.mp4")) or any(
            (b / f).exists() for f in ("generate_request.json", "edit_request.json"))):
        raise ValueError(I18N.t("{name} is already a video - give this one another name", name=name))
    song = _song(d, str(body.get("music") or ""))         # checked before a new folder is made
    if not d.exists():
        new_project(name)
    from motionlab import brand as BR
    req = {"kind": kind, "want": want, "text": text if kind == "graphics" else "", "like": like, "length_s": length,
           "format": fmt, "music": song, "tool": tool if kind == "ai" else "", **(extra if kind == "graphics" else {}),
           "brand": BR.snapshot() if body.get("brand") else None,      # 0.6.0: For my brand - My Brand as it is now
           "date": stamp()}
    write_json_atomic(d / "build" / "generate_request.json", req)
    start_brief(d)
    made = add_made_from(d.name, "generated", "a motion-graphics video" if kind == "graphics"
                         else f"AI video tools{': ' + tool if tool else ''}")
    return {"request": req, "project": d.name, "made_from": made, "command": f"/generate-video request {d.name}"}


# ------------------------------------------------------------------ the Editor (0.6.0 step 6, motionlab\miniedit)
ME_MAX_OPS, ME_MAX_WORDS = 300, 300
ME_KEYS = {"op", "shot", "side", "by", "f", "kind", "to", "graphic", "key", "value", "cue", "text", "at", "speed",
           "layer", "all", "id", "template", "len", "values", "db", "sound", "look", "strength", "ease", "start", "src",
           "in", "prop", "props", "dir", "edits"}           # (prop / props: keyframes; dir: a transition's direction;
#                                                                 edits: many captions' words at once)
ME_MAX_EDITS = 3000
EDITOR_SOUNDS = LAB / ".app" / "editor" / "sounds"          # the made-up sound effects as the Editor plays them


def _me_plan(name: str, plan: str) -> tuple[Path, dict]:
    """(the build folder, the plan) - any plan_v*.json the video's page lists; its relative paths made absolute (a
    plan Claude wrote with paths next to it: else every clip is "missing" and the preview stays blank)."""
    from motionlab.compose import resolve_paths
    b = PROJECTS / safe_name(name) / "build"
    if not re.fullmatch(r"plan_v[\w\-]+\.json", str(plan or "")) or not (b / plan).is_file():
        raise ValueError(I18N.t("not a plan: {name}", name=repr(str(plan)[:40])))
    return b, resolve_paths(json.loads((b / plan).read_text(encoding="utf-8")), b)


def _me_ops(ops) -> list[dict]:
    """The page's changes, checked for shape (what each does is motionlab\\miniedit's to check)."""
    if not isinstance(ops, list) or not ops or len(ops) > ME_MAX_OPS:
        raise ValueError(I18N.t("no changes to save"))
    out = []
    for o in ops:
        if not isinstance(o, dict) or set(o) - ME_KEYS or any(isinstance(v, str) and len(v) > ME_MAX_WORDS
                                                              for v in o.values()):
            raise ValueError(I18N.t("a change the Editor does not know"))
        eds = o.get("edits")
        if eds is not None and (not isinstance(eds, list) or len(eds) > ME_MAX_EDITS or any(
                not isinstance(e, dict) or set(e) - {"graphic", "cue", "text"} or not isinstance(e.get("cue"), int)
                or not isinstance(e.get("graphic"), str) or not isinstance(e.get("text"), str)
                or len(e["text"]) > ME_MAX_WORDS for e in eds)):
            raise ValueError(I18N.t("a change the Editor does not know"))
        vals = o.get("values")
        if vals is not None and (not isinstance(vals, dict) or len(vals) > 60
                                 or any(not isinstance(k, str) or (isinstance(v, str) and len(v) > 500)
                                        or isinstance(v, (dict, list)) for k, v in vals.items())):
            raise ValueError(I18N.t("a change the Editor does not know"))
        out.append(o)
    return out


def _me_paths(st: dict) -> dict:
    """The engine's state with lab-relative paths (what /files/ serves) for the page."""
    for g in st.get("graphics", []):
        g["dir"] = rel(g["dir"])
    for s in st.get("shots", []):                           # (a video made from zero: its scenes' graphics)
        if s.get("scene"):
            s["scene"] = rel(s["scene"])
    st["folders"] = {rel(k): v for k, v in (st.get("folders") or {}).items()}
    st["capedits"] = {rel(k): v for k, v in (st.get("capedits") or {}).items()}
    for k in ("song", "audio_file"):
        if st.get(k):
            st[k] = rel(st[k])
    return st


def editor_media(b: Path, P: dict) -> tuple[dict, bool, bool]:
    """The live preview's media for a plan (tools\\miniedit.py media): per clip its light copy and its sound's
    loudness per frame, a photo itself; the song's loudness. (media, True when a shot's copy or the song's loudness is
    missing or out of date - the preview waits for it -, True when a clip no shot uses has none yet - made quietly)."""
    from motionlab import miniedit as ME
    d = b / "editor"
    idx = read_json(d / "media.json", {}) or {}
    fps = float(P.get("fps") or 25)
    used = {L.get("src") for L in P.get("layers", []) if L.get("type") == "clip"}
    out, need, more = {}, False, False
    for sid, s in (P.get("sources") or {}).items():         # (every clip: the ones no shot uses can be added; the
        src = Path(str(s.get("source") or ""))              # page waits only for the shots' own)
        if not src.is_file():
            out[sid] = {"missing": True}
            continue
        if src.suffix.lower() in PHOTO_EXT:
            out[sid] = {"photo": rel(src)}
            continue
        e = idx.get(sid) or {}
        ok = e.get("key") == ME.media_key(src, fps) and (d / str(e.get("proxy"))).is_file() \
            and (d / str(e.get("strip_file"))).is_file()
        out[sid] = {"proxy": rel(d / e["proxy"]), "wave": rel(d / e["wave"]) if (d / str(e.get("wave"))).is_file()
                    else None, "strip": {**(e.get("strip") or {}), "url": rel(d / e["strip_file"])}} if ok \
            else {"source": rel(src)}
        need = need or (not ok and sid in used)
        more = more or not ok
    song = ME.song_source(P)
    if ME.sound_mode(P) == "song" and song and song.is_file():
        e = idx.get("_song") or {}
        ok = e.get("key") == ME.media_key(song, fps) and str(e.get("wave")).endswith(".all.wave.json") \
            and (d / str(e.get("wave"))).is_file()                  # (the whole song: its start moves in the Editor)
        out["_song"] = {"wave": rel(d / e["wave"]) if ok else None}
        need = need or not ok
    return out, need, more


def editor_sounds() -> dict:
    """The sound effects the Editor offers: this PC's recorded sounds by kind (library\\sounds, never the ones set
    off) and every kind's made-up sound."""
    from motionlab import sfx as SFX
    try:
        lib = SFX.Library.load()
    except (OSError, ValueError):
        lib = None
    rec = []
    for kind, es in sorted((lib.by_kind if lib else {}).items()):
        for e in es:
            rec.append({"file": e["file"], "kind": kind, "len_s": e.get("len_s"),
                        "name": Path(str(e.get("original") or e["file"])).stem.replace("_", " ")})
    return {"recorded": rec, "kinds": list(SFX.KINDS)}


SOUND_IN = LAB / ".app" / "sound_import"                  # sounds the user adds: copied here, then imported (a job)


def agency_stats_upload(name: str, platform: str, stream, size: int) -> dict:
    """Content agency > Your videos > Import your stats (0.6.0 step 13): a file the user exported from YouTube Studio,
    TikTok Studio or Meta Business Suite (a raw body, <= 50 MB) -> read (motionlab\\stats) into
    knowledge\\local\\stats.json; the file itself is not kept."""
    import tempfile
    import zipfile
    from motionlab import stats as STS
    suf = Path(str(name)).suffix.lower()
    if suf not in (".csv", ".xlsx", ".zip", ".tsv", ".txt") or not 0 < size <= 50_000_000:
        _drain(stream, size)
        raise ValueError(I18N.t("a .csv, .xlsx or .zip file from YouTube Studio, TikTok Studio or Meta Business Suite"))
    with tempfile.TemporaryDirectory(prefix="ml_stats_") as td:
        f = Path(td) / f"export{suf}"
        f.write_bytes(stream.read(size))
        try:
            return STS.import_file(f, platform or None, Path(str(name)).name[:120])
        except (ValueError, zipfile.BadZipFile) as e:
            raise ValueError(I18N.t(str(e)) if str(e) else I18N.t("the file could not be read"))


def brand_mood_upload(name: str, stream, size: int) -> dict:
    """My Brand > Style > Your mood board (0.6.0 step 7): a picture the user picked (a raw body, <= 25 MB) -> copied
    into knowledge\\local\\brand\\mood\\ and measured (motionlab\\moodboard); -> the board."""
    from motionlab import moodboard as MB
    if not 0 < size <= MB.MAX_BYTES:
        _drain(stream, size)
        raise ValueError(I18N.t("the picture is empty or bigger than 25 MB"))
    data = stream.read(size)
    try:
        return _mood_paths(MB.add(str(name), data))
    except ValueError as e:
        raise ValueError(I18N.t(str(e)) if "not a picture" not in str(e) else
                         I18N.t("{file}: not a picture ({types})", file=str(name)[-80:], types=", ".join(MB.EXT)))


def _mood_paths(st: dict) -> dict:
    from motionlab import moodboard as MB
    for it in st["items"]:
        it["src"] = rel(MB.DIR / it["file"])
    return st


def brand_mood(n: int | None = None) -> dict:
    """The mood board (n = a picture taken off it first)."""
    from motionlab import moodboard as MB
    return _mood_paths(MB.remove(int(n)) if n is not None else MB.state())


def music_state() -> dict:
    """Motion Graphics > Music (0.6.0 step 10): the music library (motionlab\\music.py) - every song and bed with its
    measures and flags - + the ElevenLabs settings and the beds it can make (the credits each takes)."""
    from motionlab import music as MU
    from motionlab import sfxgen as GEN
    st = MU.state()
    try:
        beds = {k: {"n": int(v.get("n", 0)), "what": v["prompts"][0], "credits": GEN.cost(v.get("seconds", 15))}
                for k, v in MU.bed_prompts().items() if k in MU.BEDS}
    except (OSError, ValueError, KeyError):
        beds = {}
    return {**st, "elevenlabs": GEN.public(), "make": beds}


def music_set(r: str, off=None, fav=None) -> dict:
    """A song / bed hidden (never offered) or shown, a favourite (offered first) or not - library\\music\\music.json."""
    from motionlab import music as MU
    try:
        return MU.set_flags(str(r), off=off, fav=fav)
    except ValueError:
        raise ValueError(I18N.t("no file {file} in the music library", file=str(r)[-80:])) from None


def music_upload(name: str, typ: str, kind: str, stream, size: int) -> dict:
    """Motion Graphics > Music > Add: a song or an ambience bed the user picked (a raw body; the original is only
    read by the browser) -> a new file in library\\music\\ (a bed: ambience\\<kind>\\), never over one; then the page
    starts the job that measures it."""
    from motionlab import music as MU
    if Path(str(name)).suffix.lower() not in MU.AUDIO_EXT or is_junk(Path(str(name))):
        _drain(stream, size)
        raise ValueError(I18N.t("{file}: not a sound ({types})", file=str(name)[-80:], types=", ".join(MU.AUDIO_EXT)))
    if not 0 < size <= 300_000_000:
        _drain(stream, size)
        raise ValueError(I18N.t("the file is empty or bigger than 300 MB"))
    try:
        folder = MU.target("bed" if typ == "bed" else "song", kind)
    except ValueError:
        _drain(stream, size)
        raise ValueError(I18N.t("pick what kind of ambience it is")) from None
    folder.mkdir(parents=True, exist_ok=True)
    dest = MU.free_name(folder, str(name))
    part, left = dest.with_name(dest.name + ".part"), size
    with open(part, "wb") as f:
        while left > 0:
            chunk = stream.read(min(1 << 20, left))
            if not chunk:
                break
            f.write(chunk)
            left -= len(chunk)
    if left:
        part.unlink(missing_ok=True)
        raise ValueError(I18N.t("the upload stopped half way - try again"))
    part.replace(dest)
    return {"rel": MU.rel(dest)}


def music_file(r: str) -> Path:
    """A song or bed of the music library to hear - only a file the library holds."""
    from motionlab import music as MU
    hit = next((it["path"] for it in MU.scan() if MU.rel(it["path"]) == str(r)), None)
    if hit is None:
        raise FileNotFoundError(str(r)[-80:])
    return hit


def brand_sound_logo_upload(name: str, stream, size: int) -> dict:
    """My Brand > Your end card > Sound: a sound file the user picked (a raw body, <= 10 MB, a few seconds) as the
    brand's sound logo (motionlab\\brand.py save_sound_logo) -> My Brand."""
    if not 0 < size <= 10_000_000:
        _drain(stream, size)
        raise ValueError(I18N.t("the file is empty or bigger than 10 MB"))
    from motionlab import brand as BR
    raw = stream.read(size)
    b = BR.save_sound_logo(str(name), raw)          # (its errors are already in the app's language)
    return {**b, "_end": BR.end_card(b, preview=True)}


def brand_sound_logo_file() -> Path:
    from motionlab import brand as BR
    snd = (BR.load().get("identity") or {}).get("sound_logo") or ""
    if not snd or not (LAB / snd).is_file():
        raise FileNotFoundError("sound logo")
    return LAB / snd


def sounds_state() -> dict:
    """Motion Graphics > Sounds (0.6.0 step 9): this PC's recorded sounds (library\\sounds - the ones set off too),
    the packs MotionLab's shared list knows (tools\\sounds\\import_list.json: how many of each are on this PC, where
    to get them) and the kinds."""
    from motionlab import sfx as SFX
    from motionlab import sfxgen as GEN
    SFX.ensure_shipped()
    jp = SFX.SOUNDS / "sounds.json"
    rows = (read_json(jp, {}) or {}).get("sounds", []) if jp.exists() else []
    L = SFX.read_list()
    have = {e["file"] for e in rows}
    packs = [{"id": k, **{x: p.get(x, "") for x in ("name", "page", "how", "licence")},
              "listed": sum(1 for r in L["sounds"] if r["pack"] == k),
              "here": sum(1 for r in L["sounds"] if r["pack"] == k and r.get("file") in have)}
             for k, p in (L.get("packs") or {}).items()]
    def name(e: dict) -> str:                               # the pack's own name for it (a pick made from a trial
        src = str(e.get("source") or "")                    # copy names the pack's file in its "source")
        inner = re.sub(r" \((picked|trial)[^)]*\)$", "", src.split(": ", 1)[1]) if ": " in src else ""
        if src.startswith(GEN.SOURCE):                      # a sound made from a description: its first words
            words = inner.split()
            return " ".join(words[:6]) + ("…" if len(words) > 6 else "")
        return Path(inner.replace("\\", "/").split("/")[-1] or str(e.get("original") or e["file"])).stem.replace("_", " ")
    out = [{"file": e["file"], "kind": e["kind"], "len_s": e.get("len_s"), "name": name(e),
            "source": str(e.get("source", "")).split(":")[0].split(" (")[0], "licence": e.get("licence", ""),
            "off": bool(e.get("off")), "fav": bool(e.get("fav")), "added": e.get("added", ""),
            "made": str(e.get("source", "")).startswith(GEN.SOURCE)} for e in rows if (SFX.SOUNDS / e["file"]).exists()]
    try:
        gk = {k: {"n": int(v.get("n", 1)), "what": v["prompts"][0], "credits": GEN.cost(v.get("seconds", 1.0))}
              for k, v in GEN.prompts()["kinds"].items()}
    except (OSError, ValueError, KeyError):
        gk = {}
    return {"sounds": out, "packs": packs, "kinds": list(SFX.KINDS), "elevenlabs": GEN.public(), "generate": gk}


def sound_set(file: str, off=None, fav=None) -> dict:
    """A sound hidden (never used) / shown, a favourite (used first) or not - library\\sounds\\sounds.json."""
    from motionlab import sfx as SFX
    jp = SFX.SOUNDS / "sounds.json"
    if not jp.exists() or not any(e["file"] == file for e in (read_json(jp, {}) or {}).get("sounds", [])):
        raise ValueError(I18N.t("no sound {sound} in the library", sound=str(file)[:80]))
    flags = {k: bool(v) for k, v in (("off", off), ("fav", fav)) if v is not None}
    SFX.set_flags(SFX.SOUNDS, file, **flags)
    return {"file": file, **flags}


def sound_upload(batch: str, path: str, stream, size: int) -> dict:
    """A sound file the user picked (a raw body; the original is only read by the browser): into
    .app\\sound_import\\<batch>\\<its path in what was picked>, for the import job. Sound files only."""
    from motionlab import sfx as SFX
    if not re.fullmatch(r"\d{8}-\d{6}-[a-z0-9]{4}", str(batch)):
        raise ValueError(I18N.t("not an upload: {id}", id=repr(str(batch)[:40])))
    parts = [re.sub(r"[^\w.\- ()&'+,\[\]]", "_", x).strip(" .")[:120] for x in str(path).replace("\\", "/").split("/")]
    parts = [x for x in parts if x and x not in (".", "..")][-6:]
    if not parts or Path(parts[-1]).suffix.lower() not in SFX.AUDIO_EXT or is_junk(Path(parts[-1])):
        _drain(stream, size)
        raise ValueError(I18N.t("{file}: not a sound ({types})", file=str(path)[-80:], types=", ".join(SFX.AUDIO_EXT)))
    if not 0 < size <= 200_000_000:
        _drain(stream, size)
        raise ValueError(I18N.t("the file is empty or bigger than 200 MB"))
    dest = SOUND_IN / batch / Path(*parts)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part, left = dest.with_name(dest.name + ".part"), size
    with open(part, "wb") as f:
        while left > 0:
            chunk = stream.read(min(1 << 20, left))
            if not chunk:
                break
            f.write(chunk)
            left -= len(chunk)
    if left:
        part.unlink(missing_ok=True)
        raise ValueError(I18N.t("the upload stopped half way - try again"))
    part.replace(dest)
    return {"batch": batch, "file": "/".join(parts)}


def sounds_share() -> dict:
    """Sounds > Share with friends: the sounds made on a paid ElevenLabs plan as one zip (.app\\share\\), shown in
    Explorer for the user to put on Google Drive."""
    import subprocess
    from motionlab import sfxgen as GEN
    try:
        r = GEN.share_zip()
    except GEN.GenError as e:
        raise ValueError(I18N.t(str(e)))
    subprocess.Popen(["explorer", "/select,", r["zip"]])
    return {"count": r["count"], "name": Path(r["zip"]).name}


def sound_import_src(batch: str = "", folder: str = "") -> Path:
    """Where an import reads from: the sounds the user added (a batch) or a folder of theirs typed in (only read)."""
    if batch:
        if not re.fullmatch(r"\d{8}-\d{6}-[a-z0-9]{4}", str(batch)) or not (SOUND_IN / batch).is_dir():
            raise ValueError(I18N.t("not an upload: {id}", id=repr(str(batch)[:40])))
        return SOUND_IN / batch
    f = Path(str(folder).strip().strip('"'))
    if not str(folder).strip() or not f.is_absolute() or not f.is_dir():
        raise ValueError(I18N.t("no folder {folder}", folder=str(folder)[:200]))
    return f


def editor_sound(kind: str, file: str = "", dur: str = "") -> Path:
    """A sound effect the Editor's preview plays: a recorded one of the library by its file (sounds.json's name - an
    address that does not end in .wav: Edge never answered a script's fetch of a .wav, 2026-10-26), else a kind's
    made-up sound as a WAV (made once in .app\\editor\\sounds; `dur` = the cue's own length, seconds)."""
    from motionlab import sfx as SFX
    if file:
        lib = SFX.Library.load()
        e = lib.entry(file) if lib else None
        if not e or e.get("synth"):
            raise FileNotFoundError(file)
        return SFX.SOUNDS / e["file"]
    if kind not in SFX.KINDS:
        raise ValueError(I18N.t("no sound effect kind {kind}", kind=kind))
    try:
        d = round(min(8.0, max(0.03, float(dur))), 2) if dur and "dur" in SFX.KINDS[kind][1] else None
    except ValueError:
        d = None
    p = EDITOR_SOUNDS / (f"{kind}_{d:.2f}.wav" if d else f"{kind}.wav")
    if not p.exists():
        import soundfile as sf
        EDITOR_SOUNDS.mkdir(parents=True, exist_ok=True)
        x = SFX.synth(kind, {"dur": d} if d else {}, 1)
        sf.write(str(p), x, SFX.SR, subtype="PCM_16")
    return p


def miniedit_state(name: str, plan: str) -> dict:
    """What the Editor tab draws and plays for a plan: motionlab\\miniedit.state + the render it made (if any), the
    preview's media and the sound effects it offers."""
    from motionlab import miniedit as ME
    b, P = _me_plan(name, plan)
    out = b / str(P.get("output") or "-")
    media, need, more = editor_media(b, P)
    return {"plan": plan, "render": rel(out) if out.is_file() else None, "media": media, "need_media": need,
            "need_more": more,
            "library": editor_sounds(), **_me_paths(ME.state(P))}


def miniedit_preview(name: str, plan: str, ops) -> dict:
    """The changes so far on the plan, nothing saved: the state they make + a line each (frame + timecode)."""
    from motionlab import miniedit as ME
    _, P = _me_plan(name, plan)
    try:
        N, done, _ = ME.apply(P, _me_ops(ops), copies=False)
    except ME.EditError as e:
        raise ValueError(str(e))
    return {"done": done, **_me_paths(ME.state(N))}


ME_RANGE_MAX = 150                                         # the longest moment rendered exactly (frames)


def miniedit_range(name: str, plan: str, ops, a: int, b: int) -> dict:
    """A moment of the edit as it would be (the changes so far), for an exact render before Save: its plan -
    picture only (the sound is made on Save), graphics added in the Editor left out (they are made on Save) - as
    build\\editor\\range_<hash>.json -> {file, a, b, out, ready}; the job editor_range renders it (render_video.py
    --range); the same moment of the same changes is rendered once."""
    import copy
    import hashlib
    from motionlab import miniedit as ME
    bd, P = _me_plan(name, plan)
    try:
        N = ME.apply(P, _me_ops(ops), copies=False)[0] if ops else ME.unique_ids(copy.deepcopy(P))
    except ME.EditError as e:
        raise ValueError(str(e))
    N["layers"] = [L for L in N["layers"] if not L.get(ME.NEW_KEY)]
    N = ME.saved(N)
    N.pop("audio", None)
    a, b = max(0, min(int(a), int(b))), min(int(N["frames"]) - 1, max(int(a), int(b)))
    if b - a + 1 > ME_RANGE_MAX:
        a = max(0, b - ME_RANGE_MAX + 1)
    h = hashlib.sha1(json.dumps(N, sort_keys=True).encode("utf-8")).hexdigest()[:10]
    d = bd / "editor"
    d.mkdir(exist_ok=True)
    N["name"], N["output"] = f"range_{h}", f"range_{h}.mp4"
    f = d / f"range_{h}.json"
    if not f.exists():
        f.write_text(json.dumps(N, ensure_ascii=False), encoding="utf-8")
    out = d / f"range_{h}_{a}-{b}.mp4"
    return {"file": f.name, "a": a, "b": b, "out": rel(out), "ready": out.is_file()}


def miniedit_save(name: str, plan: str, ops) -> str:
    """The changes checked once more, then kept as build\\miniedit\\changes_<time>.json for the job (tools\\miniedit.py
    apply ... --build) -> that file's name."""
    from motionlab import miniedit as ME
    b, P = _me_plan(name, plan)
    ops = _me_ops(ops)
    try:
        ME.apply(P, ops, copies=False)
    except ME.EditError as e:
        raise ValueError(str(e))
    d = b / "miniedit"
    d.mkdir(exist_ok=True)
    f = d / f"changes_{time.strftime('%Y%m%d-%H%M%S')}.json"
    f.write_text(json.dumps(ops, ensure_ascii=False, indent=1), encoding="utf-8")
    return f.name


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
            raise ValueError(I18N.t("rating: good, ok or bad (got {value})", value=repr(rating)))
        asp[k] = {"rating": rating, "note": str(v.get("note") or "").strip()[:500]}
    # 0.4.2: fix this version or start over (null = not answered); notes on moments of a render
    nxt = cur.get("next") if cur.get("next") in OUTCOME_NEXT else None
    if "next" in body:
        nxt = body["next"] or None
        if nxt not in (None, *OUTCOME_NEXT):
            raise ValueError(I18N.t("next: fix, start_over or finish (got {value})", value=repr(nxt)))
    # 2026-10-24: *Finish it with Claude* on a quick draft - what to add on its cuts, the user's words, which version
    fin = cur.get("finish")
    if body.get("finish") is not None:
        fb = body["finish"] if isinstance(body["finish"], dict) else {}
        add = [k for k in FINISH_ADD if k in (fb.get("add") or [])]
        words = " ".join(str(fb.get("words") or "").split())[:600]
        if not add and not words:
            raise ValueError(I18N.t("finish: pick what to add ({choices}) or say it in your words",
                                    choices=", ".join(FINISH_ADD)))
        frm = str(fb.get("from") or "")
        fin = {"add": add, "words": words, "from": frm if re.fullmatch(r"v\d{1,4}", frm) else None, "date": stamp()}
    moments = [m for m in (cur.get("moments") or []) if isinstance(m, dict)]
    if body.get("moment") is not None:
        moments.append(clean_moment(body["moment"]))
    if body.get("remove_moment") is not None:
        r = body["remove_moment"] if isinstance(body["remove_moment"], dict) else {}
        hit = next((i for i, m in enumerate(moments) if all(m.get(k) == r.get(k) for k in ("f", "version", "note"))
                    and (not r.get("date") or m.get("date") == r.get("date"))), None)
        if hit is None:
            raise ValueError(I18N.t("that note is not there any more"))
        moments.pop(hit)
    moments.sort(key=lambda m: (str(m.get("version", "")), int(m.get("f", 0))))
    out = {**cur, "aspects": {k: v for k, v in asp.items() if v.get("rating") or v.get("note")}, "updated": stamp(),
           "next": nxt, "moments": moments}                  # every other key (0.4.3 "packaging", newer ones) stays
    if fin:
        out["finish"] = fin
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
        raise ValueError(I18N.t("packaging: the click-through rates and the link"))
    old = old if isinstance(old, dict) else {}
    ctr = dict(old.get("ctr") or {})
    for k, v in (b.get("ctr") or {}).items() if isinstance(b.get("ctr"), dict) else []:
        k = str(k).strip().upper()
        if not CTR_IDS.fullmatch(k):
            raise ValueError(I18N.t("a thumbnail is A, B or C (got {value})", value=repr(k)))
        if v in (None, ""):
            ctr.pop(k, None)
            continue
        try:
            x = float(str(v).replace(",", ".").replace("%", "").strip())
        except ValueError:
            raise ValueError(I18N.t("thumbnail {id}: the click-through rate is a number like 4.1", id=k)) from None
        if not 0 <= x <= 100:
            raise ValueError(I18N.t("thumbnail {id}: the click-through rate is a percentage between 0 and 100", id=k))
        ctr[k] = round(x, 2)
    link = old.get("link") or ""
    if "link" in b:
        link = str(b.get("link") or "").strip()
        if link and (not re.fullmatch(r"https?://\S{3,500}", link)):
            raise ValueError(I18N.t("the video's link starts with https:// (copy it from the platform)"))
    return {"ctr": dict(sorted(ctr.items())), "link": link, "updated": stamp()}



def clean_moment(m) -> dict:
    """A note on one moment of a render: {"f": frame of that render (0-based, its fps), "version": "v2", "aspect":
    one of ASPECTS, "note": text, "date"} - /recreate-video improve fixes exactly those moments."""
    if not isinstance(m, dict):
        raise ValueError(I18N.t("a note needs a frame, a version, a part and the text"))
    try:
        f = int(m.get("f"))
    except (TypeError, ValueError):
        raise ValueError(I18N.t("a note needs the frame it is about")) from None
    if not 0 <= f <= 10_000_000:
        raise ValueError(I18N.t("frame out of range: {frame}", frame=f))
    version = str(m.get("version") or "").strip()
    if not re.fullmatch(r"[\w.\- \[\]()&'+,]{1,80}", version):
        raise ValueError(I18N.t("which version is it about? (got {value})", value=repr(version)))
    aspect = str(m.get("aspect") or "")
    if aspect not in ASPECTS:
        raise ValueError(I18N.t("part: one of {choices}", choices=", ".join(ASPECTS)))
    note = " ".join(str(m.get("note") or "").split())[:500]
    if not note:
        raise ValueError(I18N.t("write what is wrong or right at that moment"))
    return {"f": f, "version": version, "aspect": aspect, "note": note, "date": stamp()}


def prompt_styles(items: list[dict]) -> dict:
    """The prompt library's *Style like* (0.3.5): every analysed reference's measured style (a short line, its frame)
    and, per brief / script / hook, the references its words seem to mean (who made it, its title)."""
    st = PR.all_styles()
    keep = ("name", "title", "uploader", "category_label", "format", "line", "thumb", "reviewed", "effects",
            "verdicts", "transcript", "label", "by")                     # label / by: readable names (2026-10-18)
    styles = {s["name"]: {k: s.get(k) for k in keep} for s in st}
    for r in items:                                  # a linked self-test copy (zz tests) still shows
        for n in r.get("style_refs") or []:
            if n not in styles and (s := KN.style(n)):
                styles[n] = {k: s.get(k) for k in keep}
    sug = {r["id"]: x for r in items if r.get("kind") in PR.STYLE_KINDS
           and (x := PR.suggest_refs(r.get("text", ""), st, r.get("style_refs") or []))}
    return {"styles": styles, "suggest": sug}


def tidy_improved() -> list[str]:
    """Prepare > Improve my script (2026-10-24, a friend's ask: "only the new version should remain"): when Claude has
    saved the improved script of a request marked "replace" (every request since then - older ones keep both), the
    pasted original goes to the Recycle Bin, with any copy of the same words Claude saved again - never a script a
    video was made from (filmed, edited, posted: made_from.json) or one that is not the user's paste. The request
    is marked "tidied" once, so a script brought back from the Recycle Bin stays. Logged in .app\\deleted.log.
    Returns the ids moved."""
    from motionlab import script as SC
    waiting = False                                       # cheap first: is any such request not tidied yet?
    for p in SC.REQUESTS.glob("req-*.json") if SC.REQUESTS.is_dir() else []:
        r0 = read_json(p, {}) or {}
        if r0.get("kind") == "improve" and r0.get("replace") and not r0.get("tidied"):
            waiting = True
            break
    if not waiting:
        return []
    every = [r for r in SC.requests() if r.get("kind") == "improve"]
    reqs = [r for r in every if r.get("replace") and not r.get("tidied") and r.get("made")]
    if not reqs:
        return []
    from . import trash
    uses = prompt_uses()
    items = {x["id"]: x for x in PR.load_all("script") + PR.load_all("hook")}
    pasted = {r.get("script") for r in every}             # each request's own paste is never another's "copy"
    moved: list[str] = []
    for r in reqs:
        orig, gone, left = items.get(r.get("script") or ""), [], []
        if orig and not uses.get(orig["id"]) and (orig.get("source") or {}).get("type") == "tested":
            sha = PR.text_sha(orig.get("text") or "")
            since = PR.created(orig)                      # a copy Claude saved for THIS request: made after the paste
            copies = [x for x in items.values() if x["id"] != orig["id"] and x["id"] not in pasted
                      and not uses.get(x["id"]) and PR.created(x) >= since and PR.text_sha(x.get("text") or "") == sha]
            if not [m for m in r["made"] if m not in {c["id"] for c in copies}]:
                continue                                  # only a copy of the paste so far: wait for the new version
            for x in [orig] + copies:
                try:
                    res = trash.recycle([PR.path_of(x["id"])])
                except (ValueError, RuntimeError, OSError):
                    left.append(x["id"])
                    continue
                (gone if res["moved"] else left).append(x["id"])
            with open(LAB / ".app" / "deleted.log", "a", encoding="utf-8") as f:
                f.write(f"{stamp()} improve {r['id']}: the pasted script {', '.join(gone) or '-'} moved to the "
                        f"Recycle Bin (replaced by {', '.join(r['made'])})"
                        + (f" - not moved: {', '.join(left)}" if left else "") + "\n")
        p = SC.request_path(r["id"])
        write_json_atomic(p, {**read_json(p, {}), "tidied": gone, "tidied_at": stamp()})
        moved += gone
    return moved


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
        clips = len(clip_files(d))
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
    (made_from.json, so the script card shows "Filmed"). 2026-10-24: photos too (copied as they are - a still shot
    of the edit), never the files a Mac / iPhone leaves next to clips (a "._" name, or the AppleDouble header
    00 05 16 07 under any name)."""
    d = PROJECTS / safe_name(name)
    if not d.is_dir():
        raise FileNotFoundError(name)
    stem, ext = os.path.splitext(Path(str(filename).replace("\\", "/")).name)
    ext = ext.lower()
    if is_junk(Path(f"{stem}{ext}")):                     # 2026-10-24: ._IMG_0912.mov, .DS_Store, Thumbs.db...
        _drain(stream, size)
        raise ValueError(I18N.t("{file}: a hidden file a Mac or an iPhone leaves next to clips - not a clip",
                                file=filename))
    if ext not in CLIP_EXT | AUDIO_EXT:
        raise ValueError(I18N.t("{file}: not a video, a photo or a song ({types})", file=filename,
                                types=", ".join(sorted(CLIP_EXT | AUDIO_EXT))))
    stem = re.sub(r"[^\w.\- \[\]()&'+,]", "_", stem).replace("..", "_").strip(" .") or "recording"
    if not 0 < size <= 200 * 2**30:
        raise ValueError(I18N.t("the file is empty or bigger than 200 GB"))
    head = stream.read(min(size, 4))                      # an AppleDouble file under another name: refused too
    if head == APPLE_DOUBLE:
        _drain(stream, size - len(head))
        raise ValueError(I18N.t("{file}: a hidden file a Mac or an iPhone leaves next to clips - not a clip",
                                file=filename))
    dest, n = d / f"{stem}{ext}", 1
    while dest.exists():
        if dest.stat().st_size == size:                       # the same file added twice: keep the first copy
            _drain(stream, size - len(head))
            return {"file": dest.name, "kept": True, "made_from": add_made_from(d.name, "prompt", prompt) if prompt
                    else None, "photo": ext in PHOTO_EXT}
        n += 1                                                # same name, another file (an iPhone's IMG_0986 again)
        dest = d / f"{stem} ({n}){ext}"
    part = d / "build" / "upload" / (dest.name + ".part")     # outside the clips until it is whole
    part.parent.mkdir(parents=True, exist_ok=True)
    left = size - len(head)
    try:
        with open(part, "wb") as f:
            f.write(head)
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
    return {"file": dest.name, "kept": False, "made_from": made, "photo": ext in PHOTO_EXT}


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
    # oldest analysis first (0.4.3.5: "Latest videos" showed the oldest one first) - the pages take the end as the newest
    M["videos"] = sorted(M.get("videos", []), key=lambda v: v.get("analysed") or "")
    # memory.md is stale when a card, a rating (outcome.json), a lesson, an answer on sound effects or a set of
    # scripts & prompts (2026-10-19: its block "Scripts & prompts you analysed") is newer
    tx = _texts_root()
    src = [p for d in (KN.LOCAL_REFS, KN.SHARED_REFS) if d.exists() for p in d.glob("*.json")] + KN._outcomes() + [
        p for p in (KN.MAKING_LESSONS, KN.LOCAL_MAKING, KN.SHARED_LESSONS, KN.LOCAL_LESSONS) if p.exists()] + (
        list(ANALYSIS.glob("*/feedback/verdicts.json")) if ANALYSIS.exists() else []) + (
        list(tx.glob("*/*.json")) if tx.is_dir() else [])
    if not KN.MEMORY.exists() or KN.MEMORY.stat().st_mtime < max([_mtime(p) for p in src] or [0]):
        try:
            KN.memory_index()
        except OSError:
            pass
    lib = library(videos=False)
    M["saved"] = {"effects": len(lib["items"]), "graphics": sum(1 for g in lib["graphics"] if g.get("kind") == "yours"),
                  "examples": sum(1 for g in lib["graphics"] if g.get("kind") != "yours"), "picks": len(lib["picks"])}
    M["prompts"] = PR.count()
    return M


def library(videos: bool = True) -> dict:
    """Saved effects (library\\), the library picks of every video, the graphics (yours + the examples) and, unless
    videos=False (Home and Claude's memory only count), every video with its size and graphics (GET /api/library)."""
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
    picks, vids = [], []
    # the counts need only the picks: the same folders in list_projects()' order, without working out each video
    prs = list_projects() if videos else [{"name": d.name} for d in (
        sorted(PROJECTS.iterdir(), key=lambda p: p.name.lower()) if PROJECTS.exists() else []) if d.is_dir()]
    for pr in prs:
        pk = (read_json(library_picks_path(pr["name"]), {}) or {}).get("picks", {})
        picks += [{"project": pr["name"], "effect": k, **v} for k, v in pk.items() if v.get("pick")]
        if not videos:
            continue
        last = PROJECTS / pr["name"] / "build" / f"{pr['plans'][-1]}.json" if pr["plans"] else None
        pl = (read_json(last, {}) or {}) if last else {}
        try:
            ovs = [s["name"] for s in OS.project_overlays(pr["name"])]
        except (OSError, ValueError):                     # (a graphic's settings broken by hand: the page still opens)
            ovs = []
        vids.append({"name": pr["name"], "width": pl.get("width"), "height": pl.get("height"), "fps": pl.get("fps"),
                     "overlays": ovs})
    # the motion templates (0.5.0) have their own page, Motion Graphics: not repeated in the saved graphics - and not
    # worked out at all (OS.library()'s loop without its 75 motion templates: the same list, ~20 ms instead of ~0.35 s)
    graphics = []
    for kind, root in (("yours", OS.LIBRARY), ("example", OS.EXAMPLES)):
        for p in sorted(root.glob("*/index.html")) if root.is_dir() else []:
            try:
                s = OS.status(p.parent)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            s["kind"] = kind
            graphics.append(s)
    return {"items": items, "picks": picks, "graphics": graphics, **({"videos": vids} if videos else {})}


# ================================================================================================= skills (Tools > Skills)
SKILLS = LAB / ".claude" / "skills"
# what each skill does in the app's words (the SKILL.md descriptions are written for Claude), how to type it, where the
# app runs it for you; a skill missing here shows the first sentence of its description
SKILL_INFO = {
    "analyze-reference": {"brief": "Claude checks a video you analysed: it looks at every effect and names it - and "
                                   "learns from your verdicts when you send it your review.",
                          "uses": ["/analyze-reference <video name or file>", "/analyze-reference thumbs <set>",
                                   "/analyze-reference texts <set>"], "task": "review",
                          "where": "Analyser - Send to Claude; after your review, Send it to Claude"},
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
                                "/recreate-video prompt:<prompt id> <your video>", "/recreate-video improve <your video>",
                                "/recreate-video finish <your video>"],
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


TEXT_ROOTS = {"analysis", "projects", "refs", "docs", "library", "knowledge", "fonts", "logos"}    # (server.FILE_ROOTS)
PRIVATE_FILES = {"knowledge/local/elevenlabs.json"}       # never served, never shown (its API key)


def private(p: Path) -> bool:
    return p.relative_to(LAB).as_posix().lower() in PRIVATE_FILES


def text_file(relpath: str, limit: int = 400_000) -> str:
    """A text the page shows (What's new, the plans, tips, a report): the top-level changelogs and README, or a file in
    the folders /files/ serves - never another part of the lab, never a private file (2026-10-26 review)."""
    p = (LAB / relpath).resolve()
    if LAB not in p.parents or p.suffix.lower() not in (".md", ".txt", ".json", ".comp", ".py", ".csv", ".setting"):
        raise PermissionError(relpath)
    rel = p.relative_to(LAB)
    top = len(rel.parts) == 1 and re.fullmatch(r"(CHANGELOG(\.[a-z]{2})?|README)\.md", rel.name, re.I)
    if not (top or rel.parts[0] in TEXT_ROOTS) or private(p):
        raise PermissionError(relpath)
    return p.read_text(encoding="utf-8", errors="replace")[:limit]


# ------------------------------------------------------------------------------------------------- What it took (0.4.4)
# Claude's minutes and tokens per step of a video / an analysis / a script, from Claude Code's own session logs
# (motionlab\usage.py, read-only) + the app's jobs (.app\jobs\history.jsonl, written when a job ends, since 0.4.4).
JOB_HISTORY = LAB / ".app" / "jobs" / "history.jsonl"
# a job kind -> the step in words (the jobs that make or measure something; player copies, updates... are left out)
JOB_STEP = {"draft": "Quick draft", "overlay_render": "Graphic rendered", "overlay_new": "Graphic added",
            "overlay_captions": "Captions made", "overlay_resolve_clip": "Graphic for Resolve",
            "thumb_candidates": "Good moments for a thumbnail", "thumb_make": "Thumbnail made",
            "thumb_render": "Thumbnail rendered", "thumb_check": "Thumbnails checked", "analyze": "Measured by the lab",
            "content_transcript": "Transcript", "content_stats": "Views and likes", "colour": "Colour measured",
            "verify_timing": "Timing check", "resolve_doctor": "Resolve check-up", "report": "Report rebuilt",
            "build": "Claude's build", "build_final": "Claude's final render"}
# a counted round's task (+ the command's first word) -> the step in words
TASK_STEP = {("script", "request"): "Prepare · the script written", ("script", "improve"): "Prepare · the script improved",
             ("script", ""): "Prepare · the script checked", ("title", "request"): "Prepare · titles and thumbnail ideas",
             ("title", "package"): "Ready to post · title, thumbnails, description",
             ("title", ""): "Titles and thumbnails", ("recreate", "improve"): "Review and improve",
             ("recreate", ""): "Edit with Claude", ("generate", ""): "Made with Claude",
             ("prompt", ""): "Prompt with Claude", ("review", ""): "Claude's check", ("feedback", ""): "Your feedback applied"}


def record_job(kind: str, title: str, args: dict, started: float, ended: float, status: str) -> None:
    """A job that ended -> one line in .app\\jobs\\history.jsonl (What it took's lab jobs). Never raises."""
    if kind not in JOB_STEP:
        return
    a = args or {}
    analysis = a.get("name")
    if kind == "analyze" and a.get("video"):
        from motionlab.util import safe_name as video_folder
        analysis = video_folder(Path(str(a["video"])).stem)
    line = {"kind": kind, "title": title, "project": a.get("project"), "analysis": analysis,
            "started": round(started, 1), "ended": round(ended, 1), "status": status}
    try:
        JOB_HISTORY.parent.mkdir(parents=True, exist_ok=True)
        with open(JOB_HISTORY, "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _job_history() -> list[dict]:
    out = []
    try:
        with open(JOB_HISTORY, encoding="utf-8") as f:
            for ln in f:
                try:
                    out.append(json.loads(ln))
                except ValueError:
                    continue
    except OSError:
        pass
    return out


def usage_names() -> dict:
    """The lab's objects a Claude session can name: projects, analyses, script / title requests, prompts."""
    def dirs(d: Path) -> set:
        return {p.name for p in d.iterdir() if p.is_dir()} if d.is_dir() else set()
    req = PR.HOME / "requests"
    return {"project": dirs(PROJECTS),
            "analysis": {p.name for p in ANALYSIS.iterdir() if (p / "events.json").exists()} if ANALYSIS.is_dir() else set(),
            "thumbs": dirs(_thumbs_root()),                     # 0.4.5: thumbnail sets (analysis\thumbs\<set>)
            "texts": dirs(_texts_root()),                       # 2026-10-18: text sets (analysis\texts\<set>)
            "request": {p.stem for p in req.glob("req-*.json")} if req.is_dir() else set(),
            "prompt": {p.stem for k in PR.KINDS for p in (PR.HOME / k).glob(f"{k}-*.json")}}


def _prompt_of_request(req: str) -> dict | None:
    for k in ("script", "hook", "title"):
        for p in (PR.HOME / k).glob(f"{k}-*.json") if (PR.HOME / k).is_dir() else []:
            d = read_json(p, {}) or {}
            if d.get("request") == req:
                return d
    return None


def _request_of(pid: str) -> str | None:
    try:
        return PR.get(pid).get("request")
    except (ValueError, OSError):
        return None


def took(kind: str, name: str) -> dict:
    """What it took for a video ("project"), an analysis ("analysis") or a script / title ("prompt"): a timeline of
    rows (Claude's steps, the lab's jobs) oldest first + the total + the other rounds in the same Claude windows
    (not counted). A video's steps include its script / title records and the requests that wrote them."""
    from motionlab import usage as U
    names = usage_names()
    want: set = set()
    if kind == "project":
        p = PROJECTS / safe_name(name)
        if not p.is_dir():
            raise FileNotFoundError(name)
        name = p.name
        want.add(("project", name))
        made = read_json(p / "build" / "made_from.json", []) or []
        pids = {str(x.get("id")) for x in made if x.get("kind") == "prompt"}
        for f in (PR.HOME / "title").glob("title-*.json") if (PR.HOME / "title").is_dir() else []:
            if (read_json(f, {}) or {}).get("project") == name:      # title records linked to it (Use this title)
                pids.add(f.stem)
        for pid in pids:
            want.add(("prompt", pid))
            req = _request_of(pid)
            if req:
                want.add(("request", req))
    elif kind == "analysis":
        if not (ANALYSIS / name / "events.json").exists():           # an analysis, not the thumbnail sets
            raise FileNotFoundError(name)
        want.add(("analysis", name))
    elif kind == "prompt":
        want.add(("prompt", name))
        req = _request_of(name)
        if req:
            want.add(("request", req))
    else:
        raise ValueError(I18N.t("what it took for {kind}?", kind=repr(kind)))
    sess = U.sessions()
    rows, used = [], set()
    for s, r, objs in U.counted(sess, names):
        part = None
        if r.get("mode") == "batch" and kind in ("analysis", "project"):   # 0.4.5: this video's share of a batch
            part = U.split(r, names, kind).get(name)
            if not part:
                continue
        elif not objs & want:
            continue
        used.add(s["id"])
        info = U.round_info(s, r)
        if part is not None:
            info.update(minutes=part, tokens={k: 0 for k in info["tokens"]}, total=0, helpers=[],
                        wait_minutes=min(info["wait_minutes"], part))
        step = TASK_STEP.get((r["task"], r.get("mode") or ""), TASK_STEP.get((r["task"], ""), r["task"]))
        if part is not None:
            step += " (in a batch)"
        what = ""
        if r["task"] in ("script", "title", "prompt"):
            reqs = [n for k, n in objs if k == "request"]
            pr = _prompt_of_request(reqs[0]) if reqs else None
            ps = [n for k, n in objs if k == "prompt"]
            if not pr and ps:
                try:
                    pr = PR.get(ps[0])
                except (ValueError, OSError):
                    pr = None
            what = (pr or {}).get("title") or (pr or {}).get("title_auto") or ""
        prev = rows[-1] if rows else None
        if prev and prev["session"] == s["id"] and prev["step"] == step:
            prev["minutes"] = round(prev["minutes"] + info["minutes"], 2)     # its continuation (a render finished)
            prev["t1"] = info["t1"]
            prev["rounds"] += 1
            for k, v in info["tokens"].items():
                prev["tokens"][k] += v
            prev["total"] += info["total"]
            prev["helpers"] += info["helpers"]
            prev["wait_minutes"] = round(prev.get("wait_minutes", 0) + info["wait_minutes"], 2)
            prev["tools"] = prev.get("tools", 0) + info["tools"]
            continue
        rows.append({"kind": "claude", "step": step, "what": what, "rounds": 1, **info})
    other = {"rounds": 0, "minutes": 0.0, "prompts": []}
    for s in sess:
        if s["id"] not in used:
            continue
        for r in s["rounds"]:
            if not r.get("clear") and not r.get("task") and r["answers"]:
                other["rounds"] += 1
                other["minutes"] = round(other["minutes"] + r["minutes"], 2)
                if len(other["prompts"]) < 6:
                    other["prompts"].append({"prompt": r["prompt"][:120], "minutes": r["minutes"]})
    jobs_since = None
    if kind in ("project", "analysis"):
        hist = _job_history()
        jobs_since = min((j.get("started", 0) for j in hist), default=None)
        for j in hist:
            if j.get(kind) == name and j.get("status") == "done":
                rows.append({"kind": "job", "step": JOB_STEP.get(j.get("kind"), j.get("title") or j.get("kind")),
                             "what": "", "t0": j["started"], "t1": j["ended"],
                             "minutes": round((j["ended"] - j["started"]) / 60, 2), "total": 0})
    rows.sort(key=lambda x: x["t0"] or 0)
    claude = [x for x in rows if x["kind"] == "claude"]
    split = {k: sum(x["tokens"][k] for x in claude) for k, _ in U.TOKEN_KEYS}
    return {"kind": kind, "name": name, "rows": rows, "other": other, "jobs_since": jobs_since,
            "logs": U.log_dir().is_dir(),
            "total": {"claude_minutes": round(sum(x["minutes"] for x in claude), 2),
                      "job_minutes": round(sum(x["minutes"] for x in rows if x["kind"] == "job"), 2),
                      "tokens": sum(split.values()), "split": split,
                      "models": sorted({x["model"] for x in claude if x.get("model")}),
                      "windows": len({x["session"] for x in claude})}}


def prompt_took(items: list[dict]) -> dict:
    """Prepare's cards: prompt id -> {minutes, tokens} Claude spent writing it (its request) or improving it."""
    from motionlab import usage as U
    by: dict = {}
    for _, r, objs in U.counted(U.sessions(), usage_names()):
        if r["task"] not in ("script", "title", "prompt"):
            continue
        t = U.total(r["tokens"]) + sum(U.total(h["tokens"]) for h in r["helpers"])
        for o in objs:
            a = by.setdefault(o, [0.0, 0])
            a[0] += r["minutes"]
            a[1] += t
    out = {}
    for p in items:
        if p.get("kind") not in ("script", "hook", "title"):
            continue
        m = t = 0
        for o in {("prompt", p.get("id")), ("request", p.get("request"))}:
            if o in by:
                m, t = m + by[o][0], t + by[o][1]
        if t:
            out[p["id"]] = {"minutes": round(m, 2)}
    return out


def live_claude() -> list[dict]:
    """The heartbeat's line (every 4 s while the window is open): Claude windows the app opened that work now, with
    the video / analysis they work on (the session name's words -> the lab's objects). Reads only new log bytes."""
    from motionlab import usage as U
    L = U.live()
    if not L:
        return []
    names = usage_names()
    for x in L:
        objs = sorted(U.objects(x.get("label", ""), names))
        x["project"] = next((n for k, n in objs if k == "project"), None)
        x["analysis"] = next((n for k, n in objs if k == "analysis"), None)
        if str(x.get("label", "")).startswith("batch"):                  # 0.4.5: "video 3 of 10"
            b = next((b for b in batches(open_only=False) if b["task"] == x.get("task")), None)
            if b:
                x["batch"] = {"done": len(b["done"]), "total": len(b["items"]), "kind": b["kind"]}
        m = re.match(r"texts\s+(\S+)", str(x.get("label", "")))         # 2026-10-18: a text set - "4 of 10 checked"
        if m and m[1] in names.get("texts", ()):
            from motionlab import textsets as TX
            try:
                st = TX.state(m[1])
                x["texts"], x["batch"] = m[1], {"done": st["checked"], "total": st["items"], "kind": "texts"}
            except (OSError, ValueError):
                pass
    return L


# ------------------------------------------------------------------------------------------------- Bulk (0.4.5)
# Many videos for Claude in ONE window (the user, 2026-10-15: "bulk analyze thumbnails, videos, and also bulk edit
# stuff"): a batch = .app\batches\<id>.json {id, kind: review | recreate, items, created, opened}; Claude's skill reads
# it and works item by item (/analyze-reference batch <id>, /recreate-video batch <id>); what is done is read from the
# lab's own files, so *Continue the batch* starts at the first item not done yet.
BATCHES = LAB / ".app" / "batches"
BATCH_KINDS = {"review": ("/analyze-reference", "review"), "recreate": ("/recreate-video", "recreate")}


def new_batch(kind: str, items: list[str], bid: str | None = None) -> dict:
    if kind not in BATCH_KINDS:
        raise ValueError(I18N.t("unknown batch kind {kind}", kind=repr(kind)))
    items = list(dict.fromkeys(str(x) for x in items if x))
    if not items:
        raise ValueError(I18N.t("an empty batch"))
    for x in items:
        if (ANALYSIS if kind == "review" else PROJECTS).joinpath(x).resolve().parent != \
                (ANALYSIS if kind == "review" else PROJECTS).resolve():
            raise ValueError(I18N.t("bad name: {name}", name=repr(x)))
    bid = bid or f"b{int(time.time() * 1000) % 10_000_000}"
    if not re.fullmatch(r"b\d{1,12}", bid):
        raise ValueError(I18N.t("bad batch id {id}", id=repr(bid)))
    b = {"id": bid, "kind": kind, "items": items, "created": stamp(), "created_t": time.time(), "opened": None}
    write_json_atomic(BATCHES / f"{bid}.json", b)
    return b


def get_batch(bid: str) -> dict:
    if not re.fullmatch(r"b\d{1,12}", str(bid)):
        raise ValueError(I18N.t("bad batch id {id}", id=repr(bid)))
    b = read_json(BATCHES / f"{bid}.json", None)
    if not b:
        raise FileNotFoundError(bid)
    return b


def _item_done(kind: str, name: str, since: float) -> bool:
    """review: Claude wrote the analysis' review.json; recreate: an edit plan by Claude newer than the batch."""
    if kind == "review":
        return (ANALYSIS / name / "review.json").exists()
    b = PROJECTS / name / "build"
    for p in sorted(b.glob("plan_v*.json"), key=lambda x: x.stat().st_mtime, reverse=True) if b.is_dir() else []:
        if p.stat().st_mtime < since:
            return False
        if (read_json(p, {}) or {}).get("made_by") != "draft_edit.py":
            return True
    return False


def batch_state(b: dict) -> dict:
    done = [x for x in b["items"] if _item_done(b["kind"], x, b.get("created_t") or 0)]
    return {**b, "done": done, "left": [x for x in b["items"] if x not in done],
            "prompt": batch_prompt(b), "task": BATCH_KINDS[b["kind"]][1]}


def batch_prompt(b: dict) -> str:
    return f"{BATCH_KINDS[b['kind']][0]} batch {b['id']}"


def batches(kind: str | None = None, open_only: bool = True) -> list[dict]:
    """The batches, newest first (with what is done); open_only = those with items left."""
    out = []
    for p in sorted(BATCHES.glob("b*.json"), key=lambda x: x.stat().st_mtime, reverse=True) if BATCHES.is_dir() else []:
        b = read_json(p, None)
        if not b or (kind and b.get("kind") != kind) or not b.get("items"):
            continue
        st = batch_state(b)
        if open_only and not st["left"]:
            continue
        out.append(st)
    return out


def mark_batch_opened(bid: str) -> None:
    b = get_batch(bid)
    b["opened"] = stamp()
    write_json_atomic(BATCHES / f"{bid}.json", b)


def estimate() -> dict:
    """What Claude usually takes per item on THIS PC (What it took's numbers): review = minutes per analysed video,
    recreate = per edit with Claude (not counting Review and improve), texts = per text of a text set (2026-10-18:
    its time split by the prompt each step named). {task: {"minutes": median, "n": how many}} - a task never
    measured here is left out ("not measured yet" on the page, never a guess)."""
    from motionlab import usage as U
    names = usage_names()
    per: dict = {"review": {}, "recreate": {}, "generate": {}, "script": {}, "texts": {}}
    kind_of = {"review": "analysis", "recreate": "project", "generate": "project", "script": "request"}
    for s, r, objs in U.counted(U.sessions(), names):
        t = r["task"]
        if t == "review" and r.get("mode") == "texts":                   # /analyze-reference texts <set>
            for n, m in U.split(r, names, "prompt").items():
                per["texts"][n] = per["texts"].get(n, 0.0) + m
            continue
        if t not in per or (t == "recreate" and r.get("mode") == "improve"):
            continue
        k = kind_of[t]
        if r.get("mode") == "batch":
            for n, m in U.split(r, names, k).items():
                per[t][n] = per[t].get(n, 0.0) + m
            continue
        mine = [n for kk, n in objs if kk == k]
        if len(mine) == 1:
            per[t][mine[0]] = per[t].get(mine[0], 0.0) + r["minutes"]
    out = {}
    for t, d in per.items():
        v = sorted(x for x in d.values() if x > 0.2)
        if v:
            mid = len(v) // 2
            out[t] = {"minutes": round(v[mid] if len(v) % 2 else (v[mid - 1] + v[mid]) / 2, 2), "n": len(v)}
    return out


def forget_batch(bid: str) -> dict:
    """A batch row's ✕: the batch file (the app's own, in .app) goes; the videos and what Claude made stay."""
    get_batch(bid)
    (BATCHES / f"{bid}.json").unlink()
    return {"ok": True}


# ------------------------------------------------------------------------------------------------- thumbnail sets (0.4.5)
# Analyser > Add thumbnails (the user, 2026-10-15: "15 thumbnails from mr beast ... common patterns like font, color,
# structure"): analysis\thumbs\<set>\ (motionlab\thumbsets.py: set.json, img\, sheets; style.json by Claude). The
# user's verdicts on Claude's patterns have their own file: verdicts.json {"patterns": {"P1": {"v", "note"}}}.
THUMB_IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def _thumbs_root() -> Path:
    """analysis\\thumbs = thumbsets.ROOT (MOTIONLAB_THUMBS_ROOT moves it for tests)."""
    from motionlab import thumbsets as TS
    return Path(TS.ROOT)


def _thumb_dir(name: str) -> Path:
    d = _thumbs_root() / safe_name(name)
    if not d.is_dir():
        raise FileNotFoundError(name)
    return d


def thumb_test() -> dict:
    """Preview your thumbnail (2026-10-24, the user: "upload ur thumbnails and have it like a test on a fake generated
    youtube page ... to see if the thumbnail matches the vibe or pops from a normal youtube user feed", then "besides
    big youtubers like mrbeast ... probably of highly viewed recent videos"): the feed around the user's pictures =
    big channels' newest, most viewed videos (motionlab.thumbfeed: "feed", refreshed by the job thumb_feed) and the
    thumbnails of the sets analysed on this PC (real ones: their title, channel, views, length), and the thumbnails
    made in MotionLab (Ready to post) to pick from. Read-only."""
    from motionlab import thumbfeed as TF
    from motionlab import thumbsets as TS
    F = TF.load()
    big = [{"src": f"/api/thumbfeed/{x['id']}.jpg", "title": x["title"], "channel": x["channel"], "views": x["views"],
            "duration": x.get("duration"), "set": "_big"} for x in F["items"]]
    pool, sets = list(big), []
    for s in TS.list_sets():
        d = Path(TS.ROOT) / s["name"]
        S = read_json(d / "set.json", {}) or {}
        src = S.get("source") or {}
        who = src.get("channel") or (S.get("channel") or {}).get("who") or ""
        dur = {e.get("id"): e.get("duration") for e in (S.get("channel") or {}).get("entries") or [] if e.get("id")}
        n = 0
        for it in S.get("items") or []:
            if not it.get("file") or not it.get("title") or not (d / it["file"]).is_file():
                continue                                  # the user's own pictures (no title) are not the feed
            try:
                views = int(float(it.get("views") or 0))
            except (TypeError, ValueError):
                views = 0
            pool.append({"img": rel(d / it["file"]), "title": it["title"], "channel": it.get("channel") or who or s["label"],
                         "views": views, "duration": dur.get(it.get("id")), "set": s["name"]})
            n += 1
        if n:
            sets.append({"name": s["name"], "label": s["label"], "count": n})
    made = []
    for d in sorted(PROJECTS.iterdir()) if PROJECTS.exists() else []:
        pub = d / "build" / "publish"
        if not pub.is_dir():
            continue
        title = ((read_json(pub / "package.json", {}) or {}).get("title") or _label(d / "build") or d.name)
        for p in sorted(pub.glob("thumb_*_16x9.png")):
            made.append({"img": rel(p), "title": title, "video": _label(d / "build") or d.name})
    return {"pool": pool, "sets": sets, "made": made,
            "big": {"count": len(big), "fetched": F.get("fetched"), "stale": F["stale"], "channels": F["channels"],
                    "failed": F.get("failed") or []}}


def thumb_sets() -> list[dict]:
    from motionlab import thumbsets as TS
    return [{**s, "created": _created(TS.ROOT / s["name"])} for s in TS.list_sets()]   # created: the NEW badge


def _thumb_styles() -> list[dict]:
    """Ready to post's *In the style of*: the sets with Claude's patterns (style.json) - name, label, how many."""
    try:
        from motionlab import thumbsets as TS
        out = [{"name": s["name"], "label": s["label"], "count": s["count"]} for s in TS.list_sets() if s["has_style"]]
    except Exception:                                        # noqa: BLE001 - no sets is no failure
        return []
    from motionlab import thumbnail as TH
    for s in out:                                            # 0.4.6: the font it gives - measured, else Claude's
        try:
            s["font"] = TH.style_values(s["name"])[2].get("font_pick")
        except (Exception, SystemExit):                      # noqa: BLE001 - the button works without the line
            s["font"] = None
    return out


def thumb_set(name: str) -> dict:
    from motionlab import thumbsets as TS
    d = _thumb_dir(name)
    return {**TS.get_set(d.name), "verdicts": (read_json(d / "verdicts.json", {}) or {}).get("patterns", {}),
            "lines": TS.summary_lines(d.name)[1:]}


def save_thumb_verdicts(name: str, patterns: dict) -> dict:
    """The user's verdict on each pattern Claude named: correct / partly / wrong (+ a note); empty = removed."""
    d = _thumb_dir(name)
    cur = (read_json(d / "verdicts.json", {}) or {}).get("patterns", {})
    for pid, x in (patterns or {}).items():
        if not re.fullmatch(r"P\d{1,3}", str(pid)):
            raise ValueError(I18N.t("not a pattern: {id}", id=repr(pid)))
        v = str((x or {}).get("v") or "")
        note = " ".join(str((x or {}).get("note") or "").split())[:500]
        if v not in ("", "correct", "partly", "wrong"):
            raise ValueError(I18N.t("a verdict is correct, partly or wrong - not {value}", value=repr(v)))
        if v or note:
            cur[pid] = {"v": v, "note": note, "date": stamp()}
        else:
            cur.pop(pid, None)
    write_json_atomic(d / "verdicts.json", {"patterns": cur, "updated": stamp()})
    return {"patterns": cur}


def thumb_remove(name: str, n: int) -> dict:
    from motionlab import thumbsets as TS
    d = _thumb_dir(name)
    TS.remove_item(d.name, int(n))
    return thumb_set(d.name)


def thumb_upload(name: str, filename: str, stream, size: int) -> dict:
    """A picture the user picked or dropped for a set (a new set when the name is new): received into .app\\tmp,
    then COPIED into the set by thumbsets.add_files (the user's original is only read by the browser)."""
    from motionlab import thumbsets as TS
    from motionlab.util import safe_name as folder_name
    set_name = folder_name(str(name))
    stem, ext = os.path.splitext(Path(str(filename)).name)
    if ext.lower() not in THUMB_IMG_EXT:
        raise ValueError(I18N.t("{file}: not a picture ({types})", file=filename, types=", ".join(sorted(THUMB_IMG_EXT))))
    if not 0 < size <= 25_000_000:
        raise ValueError(I18N.t("the picture is empty or bigger than 25 MB"))
    tmp = LAB / ".app" / "tmp" / "thumbs"
    tmp.mkdir(parents=True, exist_ok=True)
    clean = re.sub(r"[^\w.\- ]", "_", stem).strip(" .")[:80] or "picture"
    part = tmp / f"{clean}{ext.lower()}"
    left = size
    with open(part, "wb") as f:
        while left > 0:
            chunk = stream.read(min(1 << 20, left))
            if not chunk:
                break
            f.write(chunk)
            left -= len(chunk)
    try:
        if left:
            raise ValueError(I18N.t("the upload stopped half way - try again"))
        TS.add_files(set_name, [part], log=lambda *_: None)
    finally:
        part.unlink(missing_ok=True)
    return {"set": set_name}


# ------------------------------------------------------------------------------------------------- text sets (2026-10-18)
# Analyser > Scripts & prompts (the user: "imagine i wanted to analize 10 prompts at the same time i could and it
# wouldnt allucinate"): analysis\texts\<set>\ (motionlab\textsets.py) around texts that live in the prompt library -
# measured inline (milliseconds, no job); verdicts.json = the user's verdicts on Claude's patterns (one home).
def _texts_root() -> Path:
    """analysis\\texts = textsets.ROOT (MOTIONLAB_TEXTS_ROOT moves it for tests)."""
    from motionlab import textsets as TX
    return Path(TX.ROOT)


def _text_dir(name: str) -> Path:
    d = _texts_root() / safe_name(name)
    if not d.is_dir():
        raise FileNotFoundError(name)
    return d


def text_sets() -> list[dict]:
    from motionlab import textsets as TX
    return [{**s, "created": _created(Path(TX.ROOT) / s["name"])} for s in TX.list_sets()]


def text_set(name: str) -> dict:
    from motionlab import textsets as TX
    return TX.get_set(_text_dir(name).name)


def _text_body(body: dict) -> tuple[str, list, dict, dict | None, list]:
    """The add dialog's fields: the paste, the attached files (POST /api/prompts/file names), the kinds the user
    picked {sha: kind}, whose they are, tags."""
    text = str(body.get("text") or "")[:2_200_000]
    files = [str(f)[:300] for f in body.get("files") or [] if isinstance(f, str) and f.strip()][:30]
    kinds = {str(k)[:40]: str(v) for k, v in (body.get("kinds") or {}).items()} if isinstance(body.get("kinds"), dict) \
        else {}
    src = body.get("source") if isinstance(body.get("source"), dict) else None
    tags = [str(x).strip().lower()[:40] for x in body.get("tags") or [] if isinstance(x, str) and x.strip()][:12]
    return text, files, kinds, src, tags


def text_split(body: dict) -> dict:
    """The numbered preview while the user pastes / attaches (nothing is written)."""
    from motionlab import textsets as TX
    text, files, kinds, src, _ = _text_body(body)
    into = str(body.get("set") or "")
    return TX.split(text, files, kinds, src, into=_text_dir(into).name if into else "")


def text_new(body: dict) -> dict:
    """*Add scripts or prompts*: a new set, everything checked first -> {set, label, added, reused, to_sort, count,
    command} (the command = /analyze-reference texts <set>, opened by the page when the user ticked Claude's check)."""
    from motionlab import textsets as TX
    text, files, kinds, src, tags = _text_body(body)
    return TX.create("", " ".join(str(body.get("label") or "").split())[:80], text, files, kinds, src, tags)


def text_add(name: str, body: dict) -> dict:
    from motionlab import textsets as TX
    text, files, kinds, src, tags = _text_body(body)
    return TX.add_items(_text_dir(name).name, text, files, kinds, src, tags)


def save_text_verdicts(name: str, patterns: dict) -> dict:
    """The user's verdict on each pattern Claude named in a text set: correct / partly / wrong (+ a note)."""
    from motionlab import textsets as TX
    return TX.save_verdicts(_text_dir(name).name, patterns if isinstance(patterns, dict) else {})


def text_remove(name: str, n: int) -> dict:
    """#n out of the set - its prompt stays in the library."""
    from motionlab import textsets as TX
    d = _text_dir(name)
    TX.remove_item(d.name, int(n))
    return text_set(d.name)


def text_kind(name: str, n: int, kind: str) -> dict:
    """The user says #n is another kind (its prompt gets a new id of that kind)."""
    from motionlab import textsets as TX
    d = _text_dir(name)
    TX.set_item_kind(d.name, int(n), str(kind), "you picked it", by="you")
    return text_set(d.name)
