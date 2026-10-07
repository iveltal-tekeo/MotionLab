"""What MotionLab learns, kept so it can be shared between installs - you and your friends, each with your own Claude
plan and your own footage. Nothing here is a video, a frame or a local path: only text and numbers.

  knowledge\\references\\<video id>--<author>.json   SHARED reference cards (in the repo): one per analysed video and
                                                    author - category, format, link, pacing, every reviewed effect
                                                    with the verdict it got
  knowledge\\incoming\\<author>-<when>.md            SHARED lessons waiting for review (in the repo)
  .claude\\skills\\analyze-reference\\lessons.md       SHARED reviewed lessons (in the repo; the skill applies them)
  knowledge\\local\\                                 THIS PC only: cards of your analyses (references\\), your new
                                                    lessons not reviewed yet (lessons.md, ids local-N), what was
                                                    shared already (shared.json), summary.md (short: norms,
                                                    corrections and references per category - what Claude reads
                                                    first) + summary\\<category>.md (every reviewed effect per
                                                    reference, read for the category being worked on)
  knowledge\\outbox\\ , inbox\\                       knowledge packs (*.mlpack.json) for friends without GitHub access

Sharing: pending() = local cards that are new or changed + local lessons not shared yet; stage() copies them into
references\\ and incoming\\ (app.updater commits + pushes them; or make_pack() writes a file to send). Updating
(git pull) brings everybody's shared cards; summary() rebuilds summary.md from all of them."""
from __future__ import annotations

import hashlib
import json
import os
import re
import statistics
import threading
import time
from pathlib import Path

from . import __version__, taxonomy
from .styles import CATEGORIES, clean_tags, fmt, label as category_label, norm as norm_category
from .util import ANALYSIS, LAB, REFS, read_json

KDIR = LAB / "knowledge"
SHARED_REFS = KDIR / "references"
INCOMING = KDIR / "incoming"
LOCAL = KDIR / "local"
LOCAL_REFS = LOCAL / "references"
LOCAL_LESSONS = LOCAL / "lessons.md"
SHARED_STATE = LOCAL / "shared.json"
SUMMARY = LOCAL / "summary.md"
SUMMARY_DIR = LOCAL / "summary"                          # summary\<category>.md: every reviewed effect per reference
OUTBOX = KDIR / "outbox"
INBOX = KDIR / "inbox"
SHARED_LESSONS = LAB / ".claude" / "skills" / "analyze-reference" / "lessons.md"
DOWNLOADS = REFS / "downloads.json"
SCHEMA = 1
_CARDS_LOCK = threading.RLock()
LESSON_HEAD = """# Lessons learned on this PC (not reviewed / shared yet)

<!--
Claude adds new rules here when it applies your feedback (ids local-1, local-2 ...), in the format of the shared
lessons.md (.claude\\skills\\analyze-reference\\lessons.md). They apply right away on this PC. "Share my knowledge"
in the app sends them to knowledge\\incoming\\ in the repo, where they are reviewed into the shared lessons.md.
-->
"""


def _write(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, p)


def settings() -> dict:
    return read_json(LAB / "settings.json") if (LAB / "settings.json").exists() else {}


def author() -> str | None:
    """The name this PC shares knowledge under (Settings > Sharing); None until it is set."""
    a = re.sub(r"[^a-z0-9_-]", "", str(settings().get("author", "")).strip().lower().replace(" ", "-"))[:24]
    return a or None


# ================================================================================================= meta + pacing
def meta(name: str, ev: dict | None = None) -> dict:
    """analysis\\<name>\\meta.json (category, tags, link) with fallbacks to events.json and refs\\downloads.json."""
    d = ANALYSIS / name
    m = read_json(d / "meta.json") if (d / "meta.json").exists() else {}
    ev = ev if ev is not None else (read_json(d / "events.json") if (d / "events.json").exists() else {})
    cat = norm_category(m.get("category") or ev.get("category") or ev.get("style"))
    src = Path(((ev or {}).get("source") or {}).get("path", ""))
    dl = download_info(src.name) if src.name else {}
    return {"category": cat, "tags": clean_tags(m.get("tags") or ev.get("tags") or []),
            "url": m.get("url") or dl.get("url"), "platform": m.get("platform") or dl.get("platform"),
            "uploader": m.get("uploader") or dl.get("uploader"),
            "title": m.get("title") or (dl.get("title") if dl else None) or (src.stem if src.name else name)}


def save_meta(name: str, **changes) -> dict:
    d = ANALYSIS / name
    if not (d / "events.json").exists():
        raise FileNotFoundError(name)
    m = read_json(d / "meta.json") if (d / "meta.json").exists() else {}
    if "category" in changes:
        c = norm_category(changes["category"])
        if changes["category"] and not c:
            raise ValueError(f"unknown category {changes['category']}")
        m["category"] = c
    if "tags" in changes:
        m["tags"] = clean_tags(changes["tags"])
    for k in ("url", "platform", "uploader", "title"):
        if changes.get(k):
            m[k] = str(changes[k])[:500]
    m["updated"] = time.strftime("%Y-%m-%d %H:%M")
    _write(d / "meta.json", m)
    return m


def download_info(file_name: str) -> dict:
    """What refs\\downloads.json (written by tools\\download.py) knows about a downloaded file."""
    if not DOWNLOADS.exists():
        return {}
    return (read_json(DOWNLOADS) or {}).get(file_name, {})


def pacing(ev: dict) -> dict:
    """How the video is cut: shot lengths, cuts per minute, the hook (first 3 s), cuts on the beat, effects/min."""
    v = ev.get("video") or {}
    fps = float(v.get("fps") or 25)
    dur = float(v.get("duration_s") or (v.get("frames") or 0) / fps or 0)
    shots = [s["frames"] / fps for s in ev.get("shots", []) if s.get("frames")]
    cuts_at = sorted(s["start"] / fps for s in ev.get("shots", [])[1:])
    evs = [e for e in ev.get("events", []) if not (e.get("final") or {}).get("false_alarm")]
    real = [e for e in evs if taxonomy.family((e.get("final") or {}).get("type", e.get("type"))) != "Hard cut"]
    plain = ev.get("hard_cuts", [])
    on_beat = [c for c in plain if c.get("on_beat") is not None]
    fams: dict[str, int] = {}
    for e in real:
        f = taxonomy.family((e.get("final") or {}).get("type", e.get("type")))
        fams[f] = fams.get(f, 0) + 1
    q = (lambda xs, p: round(sorted(xs)[min(len(xs) - 1, int(p * (len(xs) - 1) + 0.5))], 2) if xs else None)
    mins = dur / 60 if dur else 0
    return {
        "duration_s": round(dur, 2), "shots": len(shots),
        "cuts_per_min": round((len(shots) - 1) / mins, 1) if mins and shots else None,
        "avg_shot_s": round(sum(shots) / len(shots), 2) if shots else None,
        "median_shot_s": round(statistics.median(shots), 2) if shots else None,
        "p10_shot_s": q(shots, 0.1), "p90_shot_s": q(shots, 0.9),
        "hook_cuts_3s": sum(1 for t in cuts_at if t < 3.0), "first_cut_s": round(cuts_at[0], 2) if cuts_at else None,
        "cuts_on_beat_pct": round(100 * sum(1 for c in on_beat if c["on_beat"]) / len(on_beat)) if on_beat else None,
        "effects": len(real), "effects_per_min": round(len(real) / mins, 1) if mins else None,
        "families": dict(sorted(fams.items(), key=lambda kv: -kv[1])),
        "bpm": round(float((ev.get("audio") or {}).get("bpm") or 0), 1) or None,
    }


# ================================================================================================= cards
def _verdicts(name: str) -> dict:
    p = ANALYSIS / name / "feedback" / "verdicts.json"
    return read_json(p) if p.exists() else {}


def _lesson_ids_for(title: str) -> list[str]:
    ids = []
    key = (title or "").split(" [")[0].strip().lower()[:24]
    for path in (SHARED_LESSONS, LOCAL_LESSONS):
        if key and path.exists():
            for lid, text in parse_lessons(path.read_text(encoding="utf-8")):
                if key in text.lower():
                    ids.append(lid)
    return ids


def card(name: str) -> dict | None:
    """The shareable card of one analysis (None for self-test videos or broken analyses)."""
    d = ANALYSIS / name
    if name.startswith("synthetic_") or not (d / "events.json").exists():
        return None
    ev = read_json(d / "events.json")
    src = ev.get("source") or {}
    sha = src.get("sha256") or hashlib.sha256(name.encode()).hexdigest()
    m = meta(name, ev)
    v = ev.get("video") or {}
    fps = float(v.get("fps") or 25)
    w, h = v.get("display_width") or v.get("width"), v.get("display_height") or v.get("height")
    vd = _verdicts(name)
    S = vd.get("events", {})
    effects = []
    for e in ev.get("events", []):
        fin = e.get("final") or {}
        t = fin.get("type", e.get("type"))
        s = S.get(e["id"]) or {}
        effects.append({
            "id": e["id"], "type": t, "label": taxonomy.label(t), "family": taxonomy.family(t),
            "start": e["start"], "end": e["end"], "tc_start": e.get("tc_start"), "tc_end": e.get("tc_end"),
            "what": (fin.get("what") or "")[:1500], "timing": (fin.get("timing") or "")[:300],
            "easing": (fin.get("easing") or "")[:200], "origin": fin.get("origin") or "",
            "confidence": fin.get("confidence") or "", "rebuild": (fin.get("rebuild") or "")[:1200],
            "false_alarm": bool(fin.get("false_alarm")), "reviewed": bool(e.get("review")),
            "verdict": s.get("v"), "note": (s.get("note") or "")[:800],
        })
    given = [x for x in effects if x["verdict"]]
    return {
        "schema": SCHEMA, "video_id": sha[:12], "title": m["title"], "url": m["url"], "platform": m["platform"],
        "uploader": m["uploader"], "category": m["category"], "category_label": category_label(m["category"]),
        "tags": m["tags"], "format": fmt(w, h, v.get("duration_s")),
        "video": {"duration_s": v.get("duration_s"), "fps": fps, "width": w, "height": h, "frames": v.get("frames")},
        "pacing": pacing(ev), "effects": effects,
        "verdicts": {"given": len(given), "events": len(effects),
                     **{k: sum(1 for x in given if x["verdict"] == k) for k in ("correct", "partly", "wrong")}},
        "missed": (vd.get("missed") or "")[:3000], "lessons": _lesson_ids_for(m["title"]),
        "made_with": {"motionlab": __version__, "analysed": ev.get("generated"),
                      "carded": time.strftime("%Y-%m-%d %H:%M")},
    }


RUNTIME = ("made_with", "author", "shared", "origin", "pending", "shared_digest")   # not part of what was shared


def _digest(c: dict) -> str:
    keep = {k: v for k, v in c.items() if k not in RUNTIME and not k.startswith("_")}
    return hashlib.sha1(json.dumps(keep, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:12]


def build_local_cards(names: list[str] | None = None) -> list[dict]:
    """(Re)write knowledge\\local\\references\\<video id>.json for this PC's analyses (one writer at a time: the app
    asks for cards from several requests at once)."""
    out = []
    names = names or ([p.name for p in sorted(ANALYSIS.iterdir()) if p.is_dir()] if ANALYSIS.exists() else [])
    with _CARDS_LOCK:
        for n in names:
            c = card(n)
            if c:
                c["analysis"] = n
                _write(LOCAL_REFS / f"{c['video_id']}.json", c)
                out.append(c)
    return out


def _load_dir(d: Path) -> list[dict]:
    out = []
    for p in sorted(d.glob("*.json")) if d.exists() else []:
        try:
            c = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(c, dict) and c.get("schema") == SCHEMA and c.get("video_id"):
            c["_file"] = p.name
            out.append(c)
    return out


def all_cards() -> list[dict]:
    """Every card on this PC: shared ones (from everyone, via the repo) and this PC's own (marked local)."""
    me = author()
    shared = _load_dir(SHARED_REFS)
    for c in shared:
        c["origin"] = "shared"
        c["category"] = norm_category(c.get("category"))         # unknown / odd values -> None ("No category")
    local = _load_dir(LOCAL_REFS)
    st = _state()
    for c in local:
        c["origin"] = "local"
        c["author"] = me or "you"
        c["shared_digest"] = st.get("cards", {}).get(c["video_id"])
        c["pending"] = c["shared_digest"] != _digest(c)
    local_ids = {x["video_id"] for x in local}
    # your own card is listed once (the local copy is the newest); friends' cards of the same video stay
    return local + [c for c in shared if not (me and c.get("author") == me and c["video_id"] in local_ids)]


# ================================================================================================= lessons
def parse_lessons(text: str) -> list[tuple[str, str]]:
    """[(id, full text)] of '- [ID] ...' entries with their indented continuation lines."""
    out, cur = [], None
    for ln in text.splitlines():
        m = re.match(r"^- \[([A-Za-z0-9_.-]+)\]\s", ln)
        if m:
            if cur:
                out.append(cur)
            cur = [m.group(1), ln]
        elif cur and (ln.startswith("  ") or not ln.strip()):
            if ln.strip():
                cur[1] += "\n" + ln
        elif cur:
            out.append(cur)
            cur = None
    if cur:
        out.append(cur)
    return [(i, t) for i, t in out]


def local_lessons() -> list[tuple[str, str]]:
    return parse_lessons(LOCAL_LESSONS.read_text(encoding="utf-8")) if LOCAL_LESSONS.exists() else []


def ensure_local_lessons() -> Path:
    if not LOCAL_LESSONS.exists():
        LOCAL_LESSONS.parent.mkdir(parents=True, exist_ok=True)
        LOCAL_LESSONS.write_text(LESSON_HEAD, encoding="utf-8")
    return LOCAL_LESSONS


def next_lesson_id() -> str:
    ensure_local_lessons()
    n = [int(m.group(1)) for i, _ in local_lessons() for m in [re.fullmatch(r"local-(\d+)", i)] if m]
    return f"local-{max(n, default=0) + 1}"


def incoming() -> list[dict]:
    """Shared lessons waiting for review (knowledge\\incoming\\*.md)."""
    out = []
    for p in sorted(INCOMING.glob("*.md")) if INCOMING.exists() else []:
        out.append({"file": p.name, "lessons": len(parse_lessons(p.read_text(encoding="utf-8")))})
    return out


# ================================================================================================= sharing
def _state() -> dict:
    return read_json(SHARED_STATE) if SHARED_STATE.exists() else {"cards": {}, "lessons": [], "shares": []}


def pending(rebuild: list[str] | None = None) -> dict:
    """What 'Share my knowledge' would send now: new / changed cards of this PC and unshared local lessons.
    rebuild = the analyses whose cards are rebuilt first (None = all of them)."""
    if rebuild is None:
        build_local_cards()
    elif rebuild:
        build_local_cards(rebuild)
    st = _state()
    cards = [c for c in _load_dir(LOCAL_REFS) if st.get("cards", {}).get(c["video_id"]) != _digest(c)]
    lessons = [(i, t) for i, t in local_lessons() if i not in st.get("lessons", [])]
    return {"cards": cards, "lessons": lessons}


def _clean_card(c: dict, who: str) -> dict:
    c = {k: v for k, v in c.items() if not k.startswith("_") and k not in ("analysis", "origin", "pending",
                                                                            "shared_digest")}
    c["author"] = who
    return c


def stage(pack: dict) -> list[Path]:
    """Write a pack's cards into knowledge\\references\\ and its lessons into knowledge\\incoming\\ (the shared,
    tracked folders). Returns the files written."""
    who = re.sub(r"[^a-z0-9_-]", "", str(pack.get("author", "")).lower())[:24]
    if not who:
        raise ValueError("the pack has no author")
    written = []
    for c in pack.get("cards", []):
        if not re.fullmatch(r"[0-9a-f]{12}", str(c.get("video_id", ""))) or c.get("schema") != SCHEMA:
            continue
        p = SHARED_REFS / f"{c['video_id']}--{who}.json"
        _write(p, _clean_card(c, who))
        written.append(p)
    if pack.get("lessons"):
        INCOMING.mkdir(parents=True, exist_ok=True)
        p = INCOMING / f"{who}-{pack.get('made', time.strftime('%Y%m%d-%H%M')).replace(':', '').replace(' ', '-')}.md"
        body = [f"# Lessons from {who} ({pack.get('made')}, MotionLab {pack.get('motionlab')}) - waiting for review", "",
                "Review: keep the ones that are concrete, checkable and general; give each the next L number in the "
                "shared lessons.md (with `from <author> <id>` in its source note); then delete this file.", ""]
        body += [str(t) for _, t in pack["lessons"]]
        p.write_text("\n".join(body) + "\n", encoding="utf-8")
        written.append(p)
    return written


def make_pack(who: str | None = None) -> dict:
    who = who or author()
    if not who:
        raise ValueError("set your name for sharing first (Settings > Sharing)")
    pend = pending()
    return {"motionlab_pack": SCHEMA, "author": who, "made": time.strftime("%Y-%m-%d %H:%M"),
            "motionlab": __version__, "cards": [_clean_card(c, who) for c in pend["cards"]],
            "lessons": [[i, t] for i, t in pend["lessons"]]}


def write_pack(pack: dict) -> Path:
    OUTBOX.mkdir(parents=True, exist_ok=True)
    p = OUTBOX / f"{pack['author']}-{time.strftime('%Y%m%d-%H%M')}.mlpack.json"
    _write(p, pack)
    return p


def mark_shared(pack: dict, how: str) -> None:
    st = _state()
    st.setdefault("cards", {})
    for c in pack.get("cards", []):
        local = LOCAL_REFS / f"{c['video_id']}.json"
        if local.exists():
            st["cards"][c["video_id"]] = _digest(json.loads(local.read_text(encoding="utf-8")))
    st["lessons"] = sorted(set(st.get("lessons", [])) | {i for i, _ in pack.get("lessons", [])})
    st.setdefault("shares", []).append({"when": pack.get("made"), "how": how, "cards": len(pack.get("cards", [])),
                                        "lessons": len(pack.get("lessons", []))})
    _write(SHARED_STATE, st)


def read_pack(path: Path) -> dict:
    if path.stat().st_size > 50_000_000:
        raise ValueError("pack too large")
    pack = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(pack, dict) or pack.get("motionlab_pack") != SCHEMA:
        raise ValueError(f"{path.name} is not a MotionLab knowledge pack")
    pack["cards"] = [c for c in pack.get("cards", []) if isinstance(c, dict)][:2000]
    pack["lessons"] = [[str(i)[:40], str(t)[:6000]] for i, t in pack.get("lessons", [])][:500]
    return pack


def import_pack(path: Path) -> dict:
    """A friend's pack (from knowledge\\inbox\\): its cards and lessons go into the shared folders, so the next
    'Share my knowledge' (or a commit) puts them in the repo for everyone."""
    pack = read_pack(path)
    written = stage(pack)
    done = INBOX / "imported"
    done.mkdir(parents=True, exist_ok=True)
    os.replace(path, done / path.name)
    summary()
    return {"author": pack.get("author"), "cards": len(pack["cards"]), "lessons": len(pack["lessons"]),
            "files": [str(p.relative_to(LAB)) for p in written]}


def inbox() -> list[dict]:
    INBOX.mkdir(parents=True, exist_ok=True)
    out = []
    for p in sorted(INBOX.glob("*.json")):
        try:
            pk = read_pack(p)
            out.append({"file": p.name, "author": pk.get("author"), "made": pk.get("made"),
                        "cards": len(pk["cards"]), "lessons": len(pk["lessons"])})
        except (OSError, ValueError) as e:
            out.append({"file": p.name, "error": str(e)})
    return out


# ================================================================================================= summary
def _med(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 1) if xs else None


def category_stats(cards: list[dict] | None = None) -> list[dict]:
    cards = cards if cards is not None else all_cards()
    by: dict[str, list] = {}
    for c in cards:
        by.setdefault(c.get("category") or "unset", []).append(c)
    out = []
    for cat, cs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        fams: dict[str, int] = {}
        for c in cs:
            for f, n in (c.get("pacing") or {}).get("families", {}).items():
                fams[f] = fams.get(f, 0) + n
        P = [c.get("pacing") or {} for c in cs]
        out.append({"category": cat, "label": category_label(cat) if cat != "unset" else "No category",
                    "references": len(cs), "authors": sorted({c.get("author") or "?" for c in cs}),
                    "cuts_per_min": _med([p.get("cuts_per_min") for p in P]),
                    "avg_shot_s": _med([p.get("avg_shot_s") for p in P]),
                    "hook_cuts_3s": _med([p.get("hook_cuts_3s") for p in P]),
                    "effects_per_min": _med([p.get("effects_per_min") for p in P]),
                    "cuts_on_beat_pct": _med([p.get("cuts_on_beat_pct") for p in P]),
                    "duration_s": _med([p.get("duration_s") for p in P]),
                    "verdicts": sum((c.get("verdicts") or {}).get("given", 0) for c in cs),
                    "families": dict(sorted(fams.items(), key=lambda kv: -kv[1])[:8])})
    return out


def _range(xs) -> str:
    xs = [x for x in xs if x is not None]
    return f"{min(xs)}-{max(xs)}" if len(xs) > 1 else (str(xs[0]) if xs else "?")


def summary() -> str:
    """What Claude reads, in two levels so it stays small with many references:
    knowledge\\local\\summary.md - per category the pacing norms (median + range), the effects seen, the corrections
    people gave (partly / wrong + note) and the list of references; a few KB however many cards there are.
    knowledge\\local\\summary\\<category>.md - every reviewed effect of every reference in that category (read only
    for the category being analysed or rebuilt)."""
    cards = all_cards()
    stats = category_stats(cards)
    L = ["# MotionLab shared knowledge - summary", "",
         f"Built {time.strftime('%Y-%m-%d %H:%M')} from {len(cards)} reference cards "
         f"({sum(1 for c in cards if c.get('origin') == 'local')} from this PC, the rest shared by others) by "
         "tools\\motionlab\\knowledge.py. Numbers are medians (ranges in brackets) per category. Frames are 0-based; "
         "times in seconds. Every reviewed effect per reference: knowledge\\local\\summary\\<category>.md - read the "
         "one for the category you work on.", ""]
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    written = set()
    for st in stats:
        cs = [c for c in cards if (c.get("category") or "unset") == st["category"]]
        P = [c.get("pacing") or {} for c in cs]
        L += [f"## {st['label']} (`{st['category']}`) - {st['references']} reference(s) by {', '.join(st['authors'])}",
              "",
              f"- Pacing: {st['cuts_per_min']} cuts/min [{_range([p.get('cuts_per_min') for p in P])}], average shot "
              f"{st['avg_shot_s']} s [{_range([p.get('avg_shot_s') for p in P])}], {st['hook_cuts_3s']} cuts in the "
              f"first 3 s [{_range([p.get('hook_cuts_3s') for p in P])}], {st['effects_per_min']} effects/min "
              f"[{_range([p.get('effects_per_min') for p in P])}], {st['cuts_on_beat_pct']} % of cuts on the beat, "
              f"length {st['duration_s']} s [{_range([p.get('duration_s') for p in P])}]; {st['verdicts']} verdicts "
              "given.",
              "- Effects seen: " + (", ".join(f"{f} {n}" for f, n in st["families"].items()) or "none")]
        fixes = [(c, e) for c in cs for e in c.get("effects", [])
                 if e.get("verdict") in ("partly", "wrong") and e.get("note")]
        if fixes:
            L.append(f"- Corrections people gave ({len(fixes)}; the newest lessons come from these):")
            for c, e in fixes[-12:]:
                L.append(f"  - {e['label']} [{e['verdict']}] in {c.get('title', '?')[:50]} f{e['start']} "
                         f"({e.get('tc_start')}): {e['note'][:200]}")
        L.append("- References: " + "; ".join(
            f"{c.get('title', '?')[:60]} ({c.get('author') or '?'}, {(c.get('format') or {}).get('label', '')}, "
            f"{(c.get('pacing') or {}).get('cuts_per_min')} cuts/min)" for c in cs[:60]))
        L += [f"- Details: knowledge\\local\\summary\\{st['category']}.md", ""]

        D = [f"# {st['label']} - every reviewed effect per reference", "",
             f"Built {time.strftime('%Y-%m-%d %H:%M')} from {len(cs)} card(s); the norms are in ..\\summary.md. "
             "[correct] / [partly] / [WRONG] = the verdict the reference's author gave; 'user:' = their note.", ""]
        for c in cs:
            p, V = c.get("pacing") or {}, c.get("verdicts") or {}
            D.append(f"## {c.get('title')} ({c.get('author') or '?'}; {(c.get('format') or {}).get('label', '')}; "
                     f"{p.get('duration_s')} s{'; ' + c['url'] if c.get('url') else ''})")
            D.append(f"pacing {p.get('cuts_per_min')} cuts/min, shots avg {p.get('avg_shot_s')} s (p10 "
                     f"{p.get('p10_shot_s')} / p90 {p.get('p90_shot_s')}), hook {p.get('hook_cuts_3s')} cuts in 3 s, "
                     f"bpm {p.get('bpm')}; verdicts {V.get('correct', 0)} correct / {V.get('partly', 0)} partly / "
                     f"{V.get('wrong', 0)} wrong of {V.get('events', 0)}" + (f"; tags {', '.join(c['tags'])}"
                                                                             if c.get("tags") else ""))
            for e in [e for e in c.get("effects", []) if not e.get("false_alarm") and e.get("family") != "Hard cut"]:
                tag = {"correct": " [correct]", "partly": " [partly]", "wrong": " [WRONG]"}.get(e.get("verdict"), "")
                note = f" - user: {e['note'][:300]}" if e.get("note") else ""
                D.append(f"- {e['label']} f{e['start']}-{e['end']} ({e.get('tc_start')}){tag}: "
                         f"{(e.get('what') or '')[:300]}{note}")
            D.append("")
        f = SUMMARY_DIR / f"{st['category']}.md"
        f.write_text("\n".join(D) + "\n", encoding="utf-8")
        written.add(f.name)
    for old in SUMMARY_DIR.glob("*.md"):                       # categories that have no cards any more
        if old.name not in written:
            old.unlink()
    SUMMARY.write_text("\n".join(L) + "\n", encoding="utf-8")
    return "\n".join(L)


def overview() -> dict:
    """Everything the app's Knowledge page shows."""
    cards = all_cards()
    pend = pending()
    st = _state()
    lite = []
    for c in cards:
        lite.append({**{k: c.get(k) for k in ("video_id", "title", "url", "platform", "category", "category_label",
                                              "tags", "format", "pacing", "verdicts", "author", "origin", "pending",
                                              "_file")}, "analysis": _analysis_here(c)})
    return {"author": author(), "cards": lite, "categories": category_stats(cards),
            "pending": {"cards": len(pend["cards"]), "lessons": len(pend["lessons"]),
                        "card_titles": [c.get("title") for c in pend["cards"]][:20]},
            "incoming": incoming(), "inbox": inbox(), "shares": st.get("shares", [])[-10:],
            "summary": str(SUMMARY.relative_to(LAB)) if SUMMARY.exists() else None,
            "all_categories": [{"id": k, "label": v} for k, v in CATEGORIES.items()]}


def _analysis_here(c: dict) -> str | None:
    """The analysis folder of a card if it is still on this PC (the app can delete a reference; its card stays)."""
    a = c.get("analysis")
    return a if a and (ANALYSIS / a / "events.json").exists() else None


def card_detail(file_or_id: str) -> dict:
    for d in (LOCAL_REFS, SHARED_REFS):
        for c in _load_dir(d):
            if file_or_id in (c["_file"], c["video_id"]):
                c["analysis"] = _analysis_here(c)
                return c
    raise FileNotFoundError(file_or_id)
