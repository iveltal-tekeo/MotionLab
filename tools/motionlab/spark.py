"""SPARK - why a video worked (the Analyser's second way, 2026-10-30; the plan: docs\\plans.md 0.6.5 *SPARK - why a
video worked*, the research: docs\\ideas.md *SPARK (why a video worked) - researched 2026-10-29*). Built the way Notes
is: the lab prepares (tools\\spark.py prepare), Claude writes (the /spark skill), a gate checks (save_spark), the page
shows.

One folder per video in analysis\\spark\\<name>\\ (never an analysis - no events.json):
    video.json     the video (path, SHA-256, fps, frames), the link, the user's question (ask) and tags, its format,
                   the creator's chapters and YouTube's *Most replayed* peaks in frames
    content\\       transcript.json + .txt, stats.json, info.json, thumbnail.<ext> + thumbnail.json (tools\\content.py)
    shots\\         sheet_NN.jpg (one key frame per shot), hook.jpg (the first 3 s), end.jpg (the last 3 s), every
                   tile labelled f480 (00:00:16:00); shots.json = the shots and every frame a point may show
    measures.json  the lab's numbers: shots, cuts / min, the first 3 s (cuts, words, text on screen), words / min, text
                   on screen - the analyser's own cut detector and text measure on a light read of the video
    numbers.json   the lookup the user started: the video's public numbers and the creator's usual (the median views of
                   the same creator's same-format videos around it, the video left out) -> the outlier score
    spark.json     Claude's write-up, saved only through save_spark() (the gate) - never by hand; spark.md the same

The rubric is fixed - one for every video, so videos compare (a builder of such a tool: free-form answers could not be
compared, a fixed list was his biggest gain): 12 points, each labelled measured / judgement / unknown with its evidence
(a quote of the video's words, a frame it shows, or a number of the table: the tool finds the words, sets the frame +
timecode and fills the number - Claude never writes a ratio of its own), the line *not explained*, and 3-5 take-aways
for the user's own videos. "Consistent with", never "caused" or "will go viral"; no simulated audience. The numbers
stay on this PC, never in shared cards (the user's data-rules choice (a), 2026-10-29: lookups the user starts).
"""
from __future__ import annotations

import os
import re
import statistics
import threading
import time
from pathlib import Path

from .notes import _index, _tokens, chapters_of, find_quote, quote_pieces_ok, replayed_of, transcript  # noqa: F401 (re-exported)
from .timecode import frame_to_tc, label
from .util import ANALYSIS, LAB, read_json, safe_name, write_json

ROOT = Path(os.environ.get("MOTIONLAB_SPARK_ROOT") or (ANALYSIS / "spark"))
SCHEMA = 1
HOOK_S = 3.0
RUBRIC = [("idea", "The idea and who it is for"), ("packaging", "The packaging promise"), ("hook", "The hook (0-3 s)"),
          ("payoff", "The promise kept"), ("loops", "Open loops and re-hooks"), ("pacing", "Structure and pacing"),
          ("emotion", "Emotion"), ("send", "Why people would send it"), ("comment", "Why people would comment"),
          ("craft", "Craft"), ("ending", "The ending"), ("context", "Context")]
RUBRIC_KEYS = [k for k, _ in RUBRIC]
LABELS = ("measured", "judgement", "unknown")
HOOK_TYPES = {"question": "A question", "bold_claim": "A bold or contrarian claim", "result_first": "The result first",
              "curiosity": "A curiosity gap", "story": "A story starts", "problem": "A problem or a pain",
              "promise": "A promise of how", "list": "A list or a number", "visual": "A picture or a mood first",
              "callout": "It calls out the viewer", "trend": "A trend or a sound", "other": "Other"}
TEXT_MAX, VERDICT_MAX, TITLE_MAX, NOT_EXPLAINED_MAX, TAKE_MAX = 500, 220, 160, 500, 300
MIN_TAKE, MAX_TAKE, MAX_EVIDENCE = 3, 5, 4
QUOTE_MIN_WORDS, QUOTE_MAX_CHARS = 3, 300
VIEW_RULE = "2026-08-24"            # YouTube counts a view the moment a video starts to play since this day (all formats)
OUTLIER, ABOVE, BELOW = 3.0, 1.5, 0.67     # views / the creator's usual: an outlier (3-4x - Paddy Galloway), above, below
USUAL_EACH_SIDE, USUAL_MIN = 10, 5         # the creator's usual: the videos around this one, at least 5
# claims of cause and promises of virality - the gate refuses them (English and Spanish: the write-up is in the video's
# language); "consistent with", "suggests", "likely" say what the evidence can carry
BANNED = [r"\bcaus(?:e|es|ed|ing)\b", r"\bwill go viral\b", r"\bguarantee", r"\bwent viral because\b", r"\bproves?\b",
          r"\bcaus[óo]\b", r"\bcausad[oa]\b", r"\bse (?:hizo|volvi[óo]) viral (?:por|porque)\b", r"\bgarantiz",
          r"\bse har[áa] viral\b", r"\bdemuestra\b"]
_LOCK = threading.RLock()

# the table: every number a point may cite (key -> English label, unit) - the page has its own words for them
NUMBERS = {
    "views": ("views", ""), "likes": ("likes", ""), "comments": ("comments", ""), "shares": ("shares", ""),
    "saves": ("saves", ""), "followers": ("followers", ""),
    "likes_per_1k": ("likes per 1,000 views", ""), "comments_per_1k": ("comments per 1,000 views", ""),
    "shares_per_1k": ("shares per 1,000 views", ""), "saves_per_1k": ("saves per 1,000 views", ""),
    "views_per_follower": ("views per follower", "x"), "usual_views": ("the creator's usual views (median)", ""),
    "outlier": ("views against the creator's usual", "x"), "days_online": ("days online", ""),
    "views_per_day": ("views per day", ""),
    "duration_s": ("length", "s"), "shots": ("shots", ""), "cuts_per_min": ("cuts per minute", ""),
    "median_shot_s": ("median shot", "s"), "first_cut_s": ("first cut", "s"), "hook_cuts": ("cuts in the first 3 s", ""),
    "hook_words": ("words in the first 3 s", ""), "hook_text": ("text on screen in the first 3 s", "yes/no"),
    "words_per_min": ("words per minute", ""), "talk_pct": ("of the video talked", "%"),
    "text_pct": ("of the video with text-like shapes on screen (rough: signs and textures count too)", "%"),
    "creator_cuts_per_min": ("the creator's usual cuts per minute (videos SPARK read here)", ""),
    "thumb_faces": ("faces on the thumbnail", ""), "thumb_face_pct": ("the face's height on the thumbnail", "%"),
    "thumb_text_pct": ("the letters' height on the thumbnail", "%"), "thumb_brightness": ("thumbnail brightness (0-100)", ""),
    "thumb_saturation": ("thumbnail saturation", "%"),
    # 2026-11-02 (plans.md *Learn from your own posts* R1): the user's OWN video - its retention graph, traced by the lab
    # from their screenshot (motionlab\retention.py); unknown for anyone else's video
    "ret_3s": ("still watching at 3 s (your retention graph)", "%"),
    "ret_10s": ("still watching at 10 s (your retention graph)", "%"),
    "ret_end": ("still watching at the end (your retention graph)", "%"),
    "ret_drop": ("the steepest 3-second drop: the share of those watching who left (your retention graph)", "%"),
    "ret_usual_3s": ("your usual at 3 s (the median of your other traced videos on this platform)", "%"),
    "ret_usual_10s": ("your usual at 10 s (the median of your other traced videos on this platform)", "%"),
}


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M")


def spark_dir(name: str) -> Path:
    n = safe_name(str(name or ""))
    if not n.strip(" ._") or ".." in n:
        raise ValueError(f"not a SPARK name: {name!r}")
    return ROOT / n


def _load(p: Path, default=None):
    try:
        return read_json(p)
    except (OSError, ValueError):
        return default


def need(name: str) -> tuple[Path, dict]:
    d = spark_dir(name)
    v = _load(d / "video.json")
    if not isinstance(v, dict):
        raise FileNotFoundError(f"no SPARK called {name!r} (analysis\\spark\\{d.name})")
    return d, v


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
    import hashlib
    base = safe_name(video.stem) or "video"
    old = _load(ROOT / base / "video.json") or {}
    if old.get("video") and Path(old["video"]).resolve() != video.resolve():
        base = f"{base}_{hashlib.sha1(str(video.resolve()).encode('utf-8')).hexdigest()[:6]}"
    return base


def label_of(v: dict) -> str:
    return (v.get("label") or v.get("title") or v.get("name") or "").strip()


def _clean(s, limit: int) -> str:
    return " ".join(str(s or "").split())[:limit]


def fmt_of(width, height, duration_s) -> dict:
    """The format, measured (the lab's conventions): vertical / horizontal / square + short <= 90 s / mid <= 600 s /
    long."""
    w, h, s = float(width or 0), float(height or 0), float(duration_s or 0)
    shape = "square" if w and h and abs(w - h) / max(w, h) < 0.05 else "vertical" if h > w else "horizontal"
    return {"shape": shape, "length": "short" if s <= 90 else "mid" if s <= 600 else "long"}


# ------------------------------------------------------------------------------------------------ the creator's usual
def _date_ts(d: str | None) -> float | None:
    try:
        return time.mktime(time.strptime(str(d)[:10], "%Y-%m-%d"))
    except (TypeError, ValueError):
        return None


def usual_from(entries: list[dict], this_id: str | None, this_date: str | None, each_side: int = USUAL_EACH_SIDE,
               least: int = USUAL_MIN) -> tuple[dict | None, str]:
    """The creator's usual from a channel's list (newest first; entries {id, views, ts (approx. upload, epoch) or None,
    duration}): the median views of the videos posted around this one - each_side before and after it in the list,
    else (not in the list) the ones nearest its upload date - the video itself left out, never across YouTube's
    view-count change (VIEW_RULE) when the dates are known. -> (usual, why there is none)."""
    rows = [e for e in entries if isinstance(e, dict) and isinstance(e.get("views"), (int, float))]
    i = next((k for k, e in enumerate(rows) if this_id and e.get("id") == this_id), None)
    this_ts, rule_ts = _date_ts(this_date), _date_ts(VIEW_RULE)
    caveats, left_out, near_rule = [], 0, False
    if i is not None:
        near = rows[max(0, i - each_side):i] + rows[i + 1:i + 1 + each_side]
        mode = "around"
        how = "the {n} videos posted just before and after it on the creator's list"
    elif this_ts is not None and any(e.get("ts") for e in rows):
        near = sorted((e for e in rows if e.get("ts") and e.get("id") != this_id),
                      key=lambda e: abs(float(e["ts"]) - this_ts))[:2 * each_side]
        mode = "dates"
        how = "the {n} videos posted nearest its upload date (approximate dates)"
    else:
        return None, (f"it is not among the creator's {len(rows)} newest videos on the list" if rows
                      else "the creator's list gave no view counts")
    if this_ts is not None and rule_ts is not None and any(e.get("ts") for e in near):
        after = this_ts >= rule_ts
        kept = [e for e in near if not e.get("ts") or (float(e["ts"]) >= rule_ts) == after]
        left_out = len(near) - len(kept)
        if left_out:
            caveats.append(f"{len(near) - len(kept)} left out: posted on the other side of {VIEW_RULE}, when YouTube "
                           "began counting a view the moment a video starts to play")
        near = kept
    elif this_ts is not None and rule_ts is not None and abs(this_ts - rule_ts) < 90 * 86400:
        near_rule = True
        caveats.append(f"posted within 90 days of {VIEW_RULE} (YouTube's new view count) and the list gives no dates - "
                       "some of the videos around it may count views the other way")
    if len(near) < least:
        return None, f"only {len(near)} comparable videos (at least {least} are needed)"
    how = how.format(n=len(near))
    med = statistics.median(float(e["views"]) for e in near)
    if med <= 0:
        return None, "the comparable videos have no views"
    return {"n": len(near), "median": int(round(med)), "how": how, "caveats": caveats, "mode": mode,
            "left_out": left_out, "near_rule": near_rule,
            "videos": [{"id": e.get("id"), "views": int(e["views"]), "title": _clean(e.get("title"), 90),
                        "when": time.strftime("%Y-%m", time.localtime(float(e["ts"]))) if e.get("ts") else None,
                        "duration": e.get("duration")} for e in near]}, ""


WHY_CODES = [("Instagram shows", "instagram"), ("the video names no", "no_channel"),
             ("the creator's list is not read on", "platform"), ("the creator's list could not be read", "failed"),
             ("the creator's list was empty", "empty"), ("the creator's list gave no view counts", "empty"),
             ("the comparable videos have no views", "empty"), ("it is not among", "not_in_list"), ("only ", "too_few"),
             ("no link known", "no_link")]


def why_code(why: str | None) -> str | None:
    """The reason there is no usual, as a code the page puts in words (instagram, no_channel, platform, failed, empty,
    not_in_list, too_few, no_link)."""
    return next((c for p, c in WHY_CODES if str(why or "").startswith(p)), "failed" if why else None)


def result_of(outlier: float | None) -> str:
    """outlier (>= 3x the creator's usual) / above (>= 1.5x) / usual / below (< 0.67x) / unknown - set by the tool."""
    if outlier is None:
        return "unknown"
    return "outlier" if outlier >= OUTLIER else "above" if outlier >= ABOVE else "below" if outlier < BELOW else "usual"


# ------------------------------------------------------------------------------------------------ your retention
def retention_of(v: dict) -> dict | None:
    """The user's own retention graph for this video (Content agency > Where people left, matched by the post's link):
    {key, entry, usual, mismatch} - mismatch = the graph's length is not this video's (another cut, or the end line
    misplaced): then its numbers are not used. None = no graph traced for this video."""
    from . import retention as RT
    key = RT.key_of(v.get("url"))
    e = RT.entry(key) if key else None
    if not e:
        return None
    dur, end_s = float(v.get("duration_s") or 0), float(e.get("end_s") or 0)
    return {"key": key, "entry": e, "usual": RT.usual(e.get("platform") or "", but=key),
            "mismatch": bool(dur and abs(end_s - dur) > max(1.5, 0.05 * dur))}


def own_post(key: str | None) -> bool:
    """One of the user's own posts: listed by Check my pages, or a retention graph traced for it."""
    if not key:
        return False
    from . import retention as RT
    from . import social as SO
    if RT.entry(key):
        return True
    plat, _, vid = key.partition(":")
    pg = ((SO.load().get("pages") or {}).get(plat) or {})
    return any(str(x.get("id")) == vid for x in pg.get("videos") or [])


def _words_in(tr: dict | None, f0: int, f1: int, limit: int = 160) -> str:
    """The words said between two frames (the transcript's timed words; a line without them counts when it overlaps)."""
    out = []
    for ln in (tr or {}).get("lines") or []:
        ws = ln.get("words") or []
        if ws:
            out += [w["w"] for w in ws if f0 <= int(w.get("f", -1)) <= f1]
        elif int(ln["start"]) <= f1 and int(ln["end"]) >= f0:
            out.append(ln["text"])
    s = " ".join(" ".join(out).split())
    return s if len(s) <= limit else s[:limit - 1].rsplit(" ", 1)[0] + "…"


def _shot_at(shots: list[dict], f: int) -> int | None:
    return next((int(s["n"]) for s in shots if int(s["start"]) <= f <= int(s["end"])), None)


def retention_view(d: Path, v: dict, tr: dict | None = None) -> dict | None:
    """What the page and Claude get of the user's retention: the curve, its numbers, the 3 steepest drops lined up
    with the frames (+ timecode), the words said and the shot on screen there, the user's usual."""
    R = retention_of(v)
    if not R:
        return None
    e, fps, n = R["entry"], float(v["fps"]), int(v["frames"])
    drop = bool(v.get("drop_frame"))
    tr = tr if tr is not None else transcript(d)
    shots = (_load(d / "shots" / "shots.json") or {}).get("shots") or []
    S = e.get("summary") or {}
    drops = []
    for w in S.get("drops") or []:
        f0 = min(n - 1, int(round(w["s"] * fps)))
        f1 = min(n - 1, int(round((w["s"] + 3) * fps)))
        drops.append({**w, "f": f0, "f2": f1, "at_label": label(f0, fps, drop), "end_label": label(f1, fps, drop),
                      "words": _words_in(tr, f0, f1), "shot": _shot_at(shots, f0)})
    return {"key": R["key"], "points": e.get("points") or [], "end_s": e.get("end_s"), "summary": {
                k: S.get(k) for k in ("start", "hold_3s", "hold_10s", "end", "seen", "total", "gaps")},
            "drops": drops, "usual": R["usual"], "traced": e.get("traced"), "image": e.get("image"),
            "axes": e.get("axes"), "colour": e.get("colour"),
            "platform": e.get("platform"), "mismatch": R["mismatch"], "duration_s": v.get("duration_s")}


# ------------------------------------------------------------------------------------------------ the table
def table(d: Path) -> dict[str, dict]:
    """Every number of the video a point may cite: key -> {v, label, unit}; v None = not known for this video."""
    num = _load(d / "numbers.json") or {}
    mea = _load(d / "measures.json") or {}
    th = _load(d / "content" / "thumbnail.json") or {}
    v = num.get("video") or {}
    us = num.get("usual") or {}
    views = v.get("views")

    def per1k(k):
        x = v.get(k)
        return round(1000.0 * x / views, 2) if isinstance(x, (int, float)) and views else None
    pc, hk, sp, tx = mea.get("pacing") or {}, mea.get("hook") or {}, mea.get("speech") or {}, mea.get("text") or {}
    out = {"views": views, "likes": v.get("likes"), "comments": v.get("comments"), "shares": v.get("shares"),
           "saves": v.get("saves"), "followers": v.get("followers"),
           "likes_per_1k": per1k("likes"), "comments_per_1k": per1k("comments"), "shares_per_1k": per1k("shares"),
           "saves_per_1k": per1k("saves"),
           "views_per_follower": round(views / v["followers"], 2) if views is not None and v.get("followers") else None,
           "usual_views": us.get("median"),
           "outlier": round(views / us["median"], 2) if views is not None and us.get("median") else None,
           "days_online": v.get("days_online"), "views_per_day": v.get("views_per_day"),
           "duration_s": mea.get("duration_s"), "shots": pc.get("shots"), "cuts_per_min": pc.get("cuts_per_min"),
           "median_shot_s": pc.get("median_shot_s"), "first_cut_s": pc.get("first_cut_s"),
           "hook_cuts": hk.get("cuts"), "hook_words": hk.get("words"), "hook_text": hk.get("text"),
           "words_per_min": sp.get("words_per_min"), "talk_pct": sp.get("talk_pct"), "text_pct": tx.get("visible_pct"),
           "creator_cuts_per_min": (mea.get("creator") or {}).get("cuts_per_min"),
           "thumb_faces": th.get("faces"),
           "thumb_face_pct": round(100 * th["face_share"], 1) if th.get("face_share") is not None else None,
           "thumb_text_pct": round(100 * th["text_estimate"]["letter_share"], 1) if th.get("text_estimate") else None,
           "thumb_brightness": th.get("brightness"), "thumb_saturation": th.get("saturation")}
    R = retention_of(_load(d / "video.json") or {})
    if R and not R["mismatch"]:
        S = R["entry"].get("summary") or {}
        U = R["usual"] or {}
        out.update(ret_3s=S.get("hold_3s"), ret_10s=S.get("hold_10s"), ret_end=S.get("end"),
                   ret_drop=(S.get("drops") or [{}])[0].get("loss"),
                   ret_usual_3s=U.get("hold_3s"), ret_usual_10s=U.get("hold_10s"))
    rows = {k: {"v": out.get(k), "label": NUMBERS[k][0], "unit": NUMBERS[k][1]} for k in NUMBERS}
    if hk.get("text_source") == "flux":
        rows["hook_text"]["label"] = "text on screen in the first 3 s (the FLUX analysis' text events)"
    elif hk.get("text") is not None:
        rows["hook_text"]["label"] = "text-like shapes in the first 3 s (rough: small text can be missed)"
    return rows


def num_str(x, unit: str = "") -> str:
    if x is None:
        return "unknown"
    if unit == "yes/no":
        return "yes" if x else "no"
    if isinstance(x, float) and not x.is_integer():
        s = f"{x:,.2f}".rstrip("0").rstrip(".")
    else:
        s = f"{int(x):,}"
    return s + ("x" if unit == "x" else " %" if unit == "%" else " s" if unit == "s" else "")


# ------------------------------------------------------------------------------------------------ the gate
_RATIO = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(x|×|%|per\s*(?:1,?000|1k|mil))", re.I)


def _ratio_ok(n: float, allowed: list[float]) -> bool:
    return any(abs(n - a) <= max(0.051, 0.05 * abs(a)) for a in allowed)


def _ctx(name: str) -> dict:
    d, v = need(name)
    tr = transcript(d)
    sh = _load(d / "shots" / "shots.json") or {}
    return {"d": d, "v": v, "tr": tr, "fps": float(v["fps"]), "frames": int(v["frames"]), "drop": bool(v.get("drop_frame")),
            "idx": _index(tr) if tr else [], "shown": {int(f["f"]) for f in sh.get("frames") or []},
            "table": table(d), "replayed": v.get("replayed") or []}


def _evidence(C: dict, where: str, ev, bad: list[str]) -> list[dict]:
    fps, drop, n = C["fps"], C["drop"], C["frames"]
    out = []
    if ev is None:
        ev = []
    if not isinstance(ev, list):
        bad.append(f"{where}.evidence: a list")
        return out
    if len(ev) > MAX_EVIDENCE:
        bad.append(f"{where}.evidence: {len(ev)} - at most {MAX_EVIDENCE}; keep the strongest")
    for j, it in enumerate(ev[:MAX_EVIDENCE]):
        w = f"{where}.evidence[{j}]"
        if not isinstance(it, dict):
            bad.append(f"{w}: an object with a quote, shown or number")
            continue
        kinds = [k for k in ("quote", "shown", "number") if it.get(k) not in (None, "")]
        if len(kinds) != 1:
            bad.append(f"{w}: exactly one of quote (the video's words), shown (a frame of the sheets) or number (a key of "
                       "the table)")
            continue
        k = kinds[0]
        if k == "quote":
            q = " ".join(str(it["quote"]).split())
            hint = it.get("at") if isinstance(it.get("at"), int) and not isinstance(it.get("at"), bool) else None
            if len(q) > QUOTE_MAX_CHARS:
                bad.append(f"{w}: the quote has {len(q)} characters - quote at most {QUOTE_MAX_CHARS}")
            elif len(_tokens(q)) < QUOTE_MIN_WORDS:
                bad.append(f"{w}: quote at least {QUOTE_MIN_WORDS} words, so it points at one place")
            elif not quote_pieces_ok(q):                    # (notes.quote_pieces_ok: single words joined by ...)
                bad.append(f"{w}: every piece of a quote cut with ... needs at least {QUOTE_MIN_WORDS} words of its "
                           f"own: {q[:120]!r}")
            elif not C["idx"]:
                bad.append(f"{w}: there is no transcript to quote - show a frame (shown) instead")
            else:
                hit = find_quote(C["idx"], q, hint)
                if hit is None:
                    bad.append(f"{w}: the quote is not in the transcript, word for word: {q[:120]!r}")
                else:
                    a, b = hit
                    out.append({"type": "quote", "quote": q, "at": a, "end": max(a, b), "at_label": label(a, fps, drop),
                                "share": round(100.0 * a / max(1, n - 1))})
        elif k == "shown":
            f = it["shown"]
            f = int(f) if isinstance(f, (int, float)) and not isinstance(f, bool) else None
            if f is None or f not in C["shown"]:
                bad.append(f"{w}: shown={it['shown']!r} is not a frame of the sheets (shots\\shots.json \"frames\")")
            else:
                out.append({"type": "shown", "f": f, "at": f, "end": f, "at_label": label(f, fps, drop),
                            "share": round(100.0 * f / max(1, n - 1))})
        else:
            key = str(it["number"]).strip()
            row = C["table"].get(key)
            if row is None:
                bad.append(f"{w}: number {key!r} is not in the table - one of {', '.join(NUMBERS)}")
            elif row["v"] is None:
                bad.append(f"{w}: number {key!r} is unknown for this video - use other evidence, or label the point "
                           "unknown")
            else:
                out.append({"type": "number", "key": key, "value": row["v"], "label": row["label"], "unit": row["unit"],
                            "text": num_str(row["v"], row["unit"])})
    for e in out:
        if "at" in e and any(a <= e["at"] <= b for a, b in C["replayed"]):
            e["replayed"] = True
    return out


def _banned(where: str, text: str, bad: list[str]) -> None:
    for pat in BANNED:
        m = re.search(pat, text, re.I)
        if m:
            bad.append(f"{where}: {m.group(0)!r} claims a cause or promises a result - the evidence can carry "
                       "\"consistent with\", \"suggests\", \"likely\", never more")
            return


def _ratios(where: str, text: str, allowed: list[float], bad: list[str]) -> None:
    for m in _RATIO.finditer(text):
        try:
            x = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        if not _ratio_ok(x, allowed):
            bad.append(f"{where}: {m.group(0)!r} is not a number of this point's evidence - cite it ({{\"number\": "
                       "<key>}}) and use the table's value; never a ratio of your own")


def check_draft(name: str, draft: dict) -> tuple[dict, list[str]]:
    """Claude's draft -> (the write-up as saved, problems). Problems = nothing may be saved."""
    C = _ctx(name)
    d, v, fps, frames = C["d"], C["v"], C["fps"], C["frames"]
    bad: list[str] = []
    if not isinstance(draft, dict):
        return {}, ["the draft is not a JSON object"]
    T = C["table"]
    every = [float(r["v"]) for r in T.values() if isinstance(r["v"], (int, float)) and not isinstance(r["v"], bool)]

    verdict = " ".join(str(draft.get("verdict") or "").split())
    if not verdict:
        bad.append("verdict: missing (one line: why this video did what it did, as far as the evidence goes)")
    elif len(verdict) > VERDICT_MAX:
        bad.append(f"verdict: {len(verdict)} characters - at most {VERDICT_MAX} (one line)")
    _banned("verdict", verdict, bad)
    _ratios("verdict", verdict, every, bad)
    hook_type = str(draft.get("hook_type") or "").strip()
    if hook_type not in HOOK_TYPES:
        bad.append(f"hook_type: {hook_type!r} - one of {', '.join(HOOK_TYPES)}")

    raw = draft.get("rubric")
    if not isinstance(raw, list):
        bad.append(f"rubric: a list of the {len(RUBRIC)} points ({', '.join(RUBRIC_KEYS)})")
        raw = []
    seen: dict[str, dict] = {}
    hook_f = int(round(HOOK_S * fps))
    for i, it in enumerate(raw):
        w = f"rubric[{i}]"
        if not isinstance(it, dict):
            bad.append(f"{w}: not an object")
            continue
        key = str(it.get("key") or "").strip()
        if key not in RUBRIC_KEYS:
            bad.append(f"{w}: key {key!r} - one of {', '.join(RUBRIC_KEYS)}")
            continue
        w = f"rubric.{key}"
        if key in seen:
            bad.append(f"{w}: twice - one point per key")
            continue
        lab = str(it.get("label") or "").strip()
        if lab not in LABELS:
            bad.append(f"{w}: label {lab!r} - measured, judgement or unknown")
        text = " ".join(str(it.get("text") or "").split())
        if not text:
            bad.append(f"{w}: no text")
        elif len(text) > TEXT_MAX:
            bad.append(f"{w}: {len(text)} characters - at most {TEXT_MAX}")
        _banned(w, text, bad)
        ev = _evidence(C, w, it.get("evidence"), bad)
        if lab == "measured" and not any(e["type"] == "number" for e in ev):
            bad.append(f"{w}: labelled measured but cites no number of the table - cite one, or label it judgement")
        if lab == "judgement" and not ev:
            bad.append(f"{w}: a judgement needs its evidence - a quote, a frame it shows or a number")
        if lab == "unknown" and ev:
            bad.append(f"{w}: labelled unknown but has evidence - label it judgement or measured")
        if key == "hook" and lab != "unknown" and ev and not any(
                e["type"] == "number" or e["at"] <= hook_f + int(round(0.5 * fps)) for e in ev):
            bad.append(f"{w}: the hook's evidence must be in the first {HOOK_S:g} s (up to f{hook_f}) or a number")
        if key == "payoff" and lab != "unknown" and not any(e["type"] != "number" for e in ev):
            bad.append(f"{w}: the promise kept needs the moment it lands - a quote or a frame (the tool says how far in)")
        _ratios(w, text, [float(e["value"]) for e in ev if e["type"] == "number" and not isinstance(e["value"], bool)]
                + [float(e["share"]) for e in ev if "share" in e], bad)
        seen[key] = {"key": key, "label": lab, "text": text[:TEXT_MAX], "evidence": ev}
    missing = [k for k in RUBRIC_KEYS if k not in seen]
    if missing:
        bad.append(f"rubric: missing {', '.join(missing)} - every point, unknown when the video cannot tell")

    nx = " ".join(str(draft.get("not_explained") or "").split())
    if not nx:
        bad.append("not_explained: missing - what the video itself cannot account for (social influence, timing, paid "
                   "views, the algorithm's test...)")
    elif len(nx) > NOT_EXPLAINED_MAX:
        bad.append(f"not_explained: {len(nx)} characters - at most {NOT_EXPLAINED_MAX}")
    _banned("not_explained", nx, bad)

    takes = draft.get("takeaways")
    if not isinstance(takes, list) or not MIN_TAKE <= len(takes) <= MAX_TAKE:
        bad.append(f"takeaways: {MIN_TAKE}-{MAX_TAKE} actions for the user's own videos")
        takes = takes[:MAX_TAKE] if isinstance(takes, list) else []
    out_t = []
    for i, it in enumerate(takes):
        w = f"takeaways[{i}]"
        t = " ".join(str((it or {}).get("text") if isinstance(it, dict) else it or "").split())
        frm = str((it or {}).get("from") or "").strip() if isinstance(it, dict) else ""
        if not t:
            bad.append(f"{w}: no text")
        elif len(t) > TAKE_MAX:
            bad.append(f"{w}: {len(t)} characters - at most {TAKE_MAX}")
        if frm and frm not in RUBRIC_KEYS:
            bad.append(f"{w}: from {frm!r} - a rubric key or nothing")
        _banned(w, t, bad)
        out_t.append({"text": t[:TAKE_MAX], **({"from": frm} if frm in RUBRIC_KEYS else {})})

    raw_tags = draft.get("tags") if isinstance(draft.get("tags"), list) else []
    tags = [t for t in dict.fromkeys(_clean(t, 40).lower() for t in raw_tags) if t][:8]
    o = T["outlier"]["v"]
    tr = C["tr"]
    out = {"schema": SCHEMA, "name": d.name, "made": _now(), "by": "Claude",
           "lang": _clean(draft.get("lang"), 10) or None, "title": _clean(draft.get("title"), TITLE_MAX) or label_of(v),
           "verdict": verdict[:VERDICT_MAX], "result": result_of(o), "hook_type": hook_type,
           "rubric": [seen[k] for k in RUBRIC_KEYS if k in seen], "not_explained": nx[:NOT_EXPLAINED_MAX],
           "takeaways": out_t, "tags": tags,
           "numbers": {k: r["v"] for k, r in T.items() if r["v"] is not None},
           "based_on": {"transcript": (tr or {}).get("source"), "words": (tr or {}).get("words"),
                        "frames_shown": len(C["shown"]), "numbers_fetched": (_load(d / "numbers.json") or {}).get("fetched")}}
    return out, bad


def save_spark(name: str, draft: dict) -> dict:
    """The gate's only way in: check the draft, then spark.json + spark.md. Raises ValueError with every problem."""
    with _LOCK:
        rep, bad = check_draft(name, draft)
        if bad:
            raise ValueError("nothing saved - fix these and save again:\n- " + "\n- ".join(bad))
        d, v = need(name)
        write_json(d / "spark.json", rep)
        (d / "spark.md").write_text(render_md(v, rep), encoding="utf-8")
        return rep


# ------------------------------------------------------------------------------------------------ Markdown
RESULT_WORDS = {"outlier": "an outlier for its creator", "above": "above its creator's usual", "usual": "about its "
                "creator's usual", "below": "below its creator's usual", "unknown": "its creator's usual is unknown"}


def _ev_md(e: dict) -> str:
    if e["type"] == "quote":
        return f"\"{e['quote']}\" {e['at_label']}"
    if e["type"] == "shown":
        return f"shown {e['at_label']}"
    return f"{e['label']}: {e['text']}"


def render_md(v: dict, rep: dict) -> str:
    T = {k: (rep.get("numbers") or {}).get(k) for k in NUMBERS}
    L = [f"# SPARK - {rep.get('title') or label_of(v)}", ""]
    src = [f"[{v.get('platform') or 'link'}]({v['url']})" if v.get("url") else Path(v.get("video") or "").name]
    if v.get("uploader"):
        src.append(str(v["uploader"]))
    L += [" · ".join(src), "", f"**{rep['verdict']}**", "",
          f"Result: {RESULT_WORDS.get(rep.get('result'), '')}"
          + (f" ({num_str(T['outlier'], 'x')} its usual {num_str(T['usual_views'])} views)" if T.get("outlier") else ""),
          f"Hook: {HOOK_TYPES.get(rep.get('hook_type'), '')}", ""]
    nums = [f"{NUMBERS[k][0]} {num_str(T[k], NUMBERS[k][1])}" for k in ("views", "likes_per_1k", "comments_per_1k",
                                                                        "shares_per_1k", "saves_per_1k", "views_per_follower")
            if T.get(k) is not None]
    if nums:
        L += ["Numbers: " + " · ".join(nums), ""]
    ret = [f"{NUMBERS[k][0].replace(' (your retention graph)', '')} {num_str(T[k], '%')}"
           for k in ("ret_3s", "ret_10s", "ret_end", "ret_drop") if T.get(k) is not None]
    if ret:
        L += ["Your retention: " + " · ".join(ret), ""]
    for p in rep.get("rubric") or []:
        L.append(f"## {dict(RUBRIC)[p['key']]} - {p['label']}")
        L.append(p["text"])
        L += [f"- {_ev_md(e)}" for e in p.get("evidence") or []]
        L.append("")
    L += ["## Not explained", rep.get("not_explained", ""), "", "## For your videos"]
    L += [f"- {t['text']}" for t in rep.get("takeaways") or []]
    L += ["", f"_Written by Claude {rep.get('made')} - measured = the lab's numbers, judgement = Claude's reading of the "
              "evidence, unknown = the video cannot tell._"]
    return "\n".join(L).rstrip() + "\n"


# ------------------------------------------------------------------------------------------------ the list
def _thumb(d: Path) -> str | None:
    for p in sorted((d / "content").glob("thumbnail.*")) if (d / "content").is_dir() else []:
        if p.suffix.lower() in (".jpg", ".png", ".webp"):
            return rel(p)
    f = d / "shots" / "cover.jpg"
    return rel(f) if f.exists() else None


def summary(d: Path, v: dict) -> dict:
    rep = _load(d / "spark.json")
    has = isinstance(rep, dict)
    num = _load(d / "numbers.json") or {}
    T = table(d)
    ready = (d / "shots" / "shots.json").exists() or transcript(d) is not None
    return {"name": d.name, "label": label_of(v), "title": v.get("title"), "url": v.get("url"),
            "platform": v.get("platform"), "uploader": v.get("uploader"), "duration_s": v.get("duration_s"),
            "fps": v.get("fps"), "frames": v.get("frames"), "created": v.get("created"), "tags": v.get("tags") or [],
            "ask": v.get("ask") or "", "format": v.get("format") or {}, "thumb": _thumb(d), "issues": v.get("issues") or [],
            "video_there": bool(v.get("video")) and Path(v.get("video") or "").is_file(),
            "views": T["views"]["v"], "outlier": T["outlier"]["v"], "result": result_of(T["outlier"]["v"]),
            "fetched": num.get("fetched"),
            "find": " ".join(str(b) for b in [v.get("title"), label_of(v), v.get("uploader"), v.get("platform"), v.get("ask"),
                                              " ".join(v.get("tags") or [])] + ([rep.get("title"), rep.get("verdict"),
                                              rep.get("hook_type")] + [x.get("text") for x in rep.get("takeaways") or []
                                                                       if isinstance(x, dict)] if has else []) if b).lower()[:6000],
            "spark": {"made": rep.get("made"), "verdict": rep.get("verdict"), "title": rep.get("title"),
                      "hook_type": rep.get("hook_type"), "result": rep.get("result")} if has else None,
            "status": "ready" if has else ("claude" if ready else "empty")}


def list_spark() -> list[dict]:
    out = []
    for d in sorted(ROOT.iterdir()) if ROOT.is_dir() else []:
        v = _load(d / "video.json") if d.is_dir() else None
        if isinstance(v, dict) and v.get("fps") and v.get("frames"):
            out.append(summary(d, v))
    out.sort(key=lambda x: x.get("created") or "", reverse=True)
    return out


def pending() -> list[str]:
    """The videos Claude has not written SPARK for yet (their words or shots are ready)."""
    return [x["name"] for x in list_spark() if x["status"] == "claude"]


def same_video(sha: str | None, path: str | None) -> dict:
    """The other ways that read the same video (one video, three ways): its FLUX analysis and its notes."""
    out = {"flux": None, "notes": None}
    if not sha and not path:
        return out
    for d in sorted(ANALYSIS.iterdir()) if ANALYSIS.is_dir() else []:
        if d.name in ("notes", "spark", "thumbs", "texts", "templates") or not (d / "events.json").exists():
            continue
        src = (_load(d / "events.json") or {}).get("source") or {}
        if (sha and src.get("sha256") == sha) or (path and src.get("path") and _same(src["path"], path)):
            out["flux"] = d.name
            break
    from . import notes as NT
    for d in sorted(NT.ROOT.iterdir()) if NT.ROOT.is_dir() else []:
        n = _load(d / "note.json") if d.is_dir() else None
        if isinstance(n, dict) and ((sha and n.get("sha256") == sha) or (path and n.get("video") and _same(n["video"], path))):
            out["notes"] = d.name
            break
    return out


def _same(a: str, b: str) -> bool:
    try:
        return Path(a).resolve() == Path(b).resolve()
    except OSError:
        return False


def of_video(sha: str | None = None, path: str | None = None) -> dict | None:
    """The SPARK of a video (by SHA-256 or path) - the analysis and notes pages link to it: {name, status}."""
    for d in sorted(ROOT.iterdir()) if ROOT.is_dir() else []:
        v = _load(d / "video.json") if d.is_dir() else None
        if isinstance(v, dict) and ((sha and v.get("sha256") == sha) or (path and v.get("video") and _same(v["video"], path))):
            return {"name": d.name, "status": "ready" if (d / "spark.json").exists() else "claude"}
    return None


def by_post() -> dict[str, dict]:
    """The SPARK of each post by its key (tiktok:<id>, youtube:<id>...) - Content agency's videos link to theirs."""
    from . import retention as RT
    out = {}
    for d in sorted(ROOT.iterdir()) if ROOT.is_dir() else []:
        v = _load(d / "video.json") if d.is_dir() else None
        k = RT.key_of(v.get("url")) if isinstance(v, dict) else None
        if k:
            out[k] = {"name": d.name, "status": "ready" if (d / "spark.json").exists() else "claude"}
    return out


def creator_pacing(name: str, uploader: str | None) -> dict | None:
    """The same creator's other videos SPARK read on this PC: the median of their cuts per minute (pacing against the
    creator's own videos, never against "more cuts = better")."""
    if not uploader:
        return None
    vals = []
    for d in sorted(ROOT.iterdir()) if ROOT.is_dir() else []:
        if d.name == name:
            continue
        v = _load(d / "video.json") if d.is_dir() else None
        if isinstance(v, dict) and (v.get("uploader") or "").lower() == uploader.lower():
            c = ((_load(d / "measures.json") or {}).get("pacing") or {}).get("cuts_per_min")
            if isinstance(c, (int, float)):
                vals.append(float(c))
    return {"n": len(vals), "cuts_per_min": round(statistics.median(vals), 1)} if vals else None


# ------------------------------------------------------------------------------------------------ a style reference
# 2026-11-03 (the user: "videos i analyzed as SPARK wont show up as references when i try to create a new edit", then
# "add Prepare's pickers too"): a finished SPARK is a style reference - New edit, Edit several videos and Prepare's *In
# the style of* - for its structure and pacing only: SPARK measures no effects, beat or colour. style.find takes it as
# REF + the folder name (never an analysis folder's name); a video with a FLUX analysis too keeps that key and its
# SPARK goes with it (structure_of).
REF = "spark:"
REF_POINTS = ("idea", "packaging", "hook", "loops", "payoff", "pacing", "ending", "craft")   # how the video is built
POINT_MAX = 320
TALK_WPM, TALK_PCT = 110, 40        # this fast for this long = someone talks; slower = a song's words or a few lines
_SUNG = re.compile(r"\b(?:music|lyrics?|songs?|rap|singing)\b", re.I)


def ref_name(key) -> str | None:
    """The SPARK folder a style key names (REF + the name), else None."""
    k = str(key or "")
    return k[len(REF):] if k.startswith(REF) and k[len(REF):].strip(" ._") else None


def _cut(s, n: int) -> str:
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0].rstrip(",;:-") + " …"


def talking(m: dict, tags) -> bool:
    """A talking video by SPARK's light read: at least TALK_WPM words a minute over TALK_PCT % of it, and no tag that
    says music (speech to text writes down a song's words too - the 4AM video: 177 "words/min" of lyrics)."""
    sp = (m or {}).get("speech") or {}
    if any(_SUNG.search(str(t)) for t in tags or []):
        return False
    return (sp.get("words_per_min") or 0) >= TALK_WPM and (sp.get("talk_pct") or 0) >= TALK_PCT


def structure(name: str) -> dict | None:
    """What a finished SPARK says about how the video is built (style.py's *Structure (SPARK)*): the verdict, the
    hook's type, the rubric's points on structure that it could judge, the take-aways, where the whole write-up is.
    No views and no result: an edit or a script copies a structure, never a result. None until Claude wrote it."""
    try:
        d = spark_dir(name)
    except ValueError:
        return None
    rep = _load(d / "spark.json")
    if not isinstance(rep, dict):
        return None
    m = _load(d / "measures.json") or {}
    pts = {r["key"]: r for r in rep.get("rubric") or [] if isinstance(r, dict) and r.get("key") in REF_POINTS}
    names = dict(RUBRIC)
    takes = [t.get("text") if isinstance(t, dict) else t for t in rep.get("takeaways") or []]
    return {"name": d.name, "verdict": _cut(rep.get("verdict"), VERDICT_MAX), "lang": rep.get("lang"),
            "hook_type": HOOK_TYPES.get(str(rep.get("hook_type") or ""), ""),
            "hook_text": (m.get("hook") or {}).get("text"), "text_pct": (m.get("text") or {}).get("visible_pct"),
            "points": [{"key": k, "label": names[k], "text": _cut(pts[k].get("text"), POINT_MAX)} for k in REF_POINTS
                       if k in pts and pts[k].get("label") != "unknown" and str(pts[k].get("text") or "").strip()],
            "takeaways": [_cut(t, TAKE_MAX) for t in takes if str(t or "").strip()],
            "file": f"analysis\\spark\\{d.name}\\spark.md"}


def ref_card(name: str) -> dict | None:
    """A finished SPARK as a style card (the shape style.find gives, origin "spark"): its format, the pacing of
    SPARK's light read (shots, cuts / min, the shot lengths from its shots, the first 3 s), its words when it is a
    talking video, and structure(). Effects, beat and colour stay None - not measured, never zero."""
    S = structure(name)
    if not S:
        return None
    d = spark_dir(name)
    v = _load(d / "video.json")
    if not isinstance(v, dict):
        return None
    from .styles import fmt
    m = _load(d / "measures.json") or {}
    rep = _load(d / "spark.json") or {}
    P, H, sp = m.get("pacing") or {}, m.get("hook") or {}, m.get("speech") or {}
    fps = float(v.get("fps") or m.get("fps") or 25)
    dur = v.get("duration_s") or m.get("duration_s")
    lens = sorted((s["end"] - s["start"] + 1) / fps for s in (_load(d / "shots" / "shots.json") or {}).get("shots") or []
                  if isinstance(s, dict) and isinstance(s.get("start"), int) and isinstance(s.get("end"), int))

    def q(p: float):
        return round(lens[min(len(lens) - 1, int(p * (len(lens) - 1) + 0.5))], 2) if lens else None
    tags = list(dict.fromkeys(str(t) for t in [*(v.get("tags") or []), *(rep.get("tags") or [])] if str(t).strip()))
    talk = talking(m, tags)
    content = {"hook": {"words": H.get("words")}, "speech": {"talk_pct": sp.get("talk_pct"),
                                                             "words_per_min": sp.get("words_per_min")}} if talk else {}
    return {"origin": "spark", "spark": S, "spark_name": d.name, "key": REF + d.name, "analysis": None,
            "video_id": str(v.get("sha256") or "")[:12] or None, "title": v.get("title") or d.name,
            "label": v.get("label") or "", "url": v.get("url"), "platform": v.get("platform"),
            "uploader": v.get("uploader"), "category": None, "category_label": None, "tags": tags, "focus": None,
            "format": fmt(v.get("width"), v.get("height"), dur), "thumb": _thumb(d), "made": rep.get("made"),
            "video": {"duration_s": dur, "fps": fps, "width": v.get("width"), "height": v.get("height"),
                      "frames": v.get("frames")},
            "pacing": {"duration_s": dur, "shots": P.get("shots"), "cuts_per_min": P.get("cuts_per_min"),
                       "avg_shot_s": P.get("avg_shot_s"), "median_shot_s": P.get("median_shot_s"),
                       "p10_shot_s": q(0.1), "p90_shot_s": q(0.9), "hook_cuts_3s": H.get("cuts"),
                       "first_cut_s": P.get("first_cut_s"), "cuts_on_beat_pct": None, "effects": None,
                       "effects_per_min": None, "families": {}, "bpm": None},
            "effects": [], "profile": {"content": content, "lines": {}}, "breakdown": None, "talking": talk}


def finished() -> list[dict]:
    """Every SPARK Claude has written: [{name, id}] - id = the video's card id (its SHA-256's first 12, as
    knowledge.card), so a video with a FLUX analysis too is known as one video."""
    out = []
    for d in sorted(ROOT.iterdir()) if ROOT.is_dir() else []:
        v = _load(d / "video.json") if d.is_dir() and (d / "spark.json").exists() else None
        if isinstance(v, dict):
            out.append({"name": d.name, "id": str(v.get("sha256") or "")[:12] or None})
    return out


def structure_of(video_id: str | None) -> dict | None:
    """structure() of a video's SPARK by its card id - a FLUX reference's SPARK goes with it."""
    hit = next((x["name"] for x in finished() if video_id and x["id"] == video_id), None)
    return structure(hit) if hit else None


def get(name: str) -> dict:
    """Everything a SPARK page shows."""
    d, v = need(name)
    out = summary(d, v)
    T = table(d)
    sh = _load(d / "shots" / "shots.json") or {}
    tr = transcript(d)
    out.update(video=str(v.get("video") or ""), video_rel=rel(v.get("video")) if out["video_there"] else None,
               lines=[{"start": r["start"], "end": r["end"], "text": r["text"]} for r in (tr or {}).get("lines") or []],
               drop_frame=bool(v.get("drop_frame")), width=v.get("width"), height=v.get("height"),
               numbers={k: r["v"] for k, r in T.items() if r["v"] is not None},
               usual=(_load(d / "numbers.json") or {}).get("usual"),
               usual_why=(_load(d / "numbers.json") or {}).get("usual_why"),
               usual_code=why_code((_load(d / "numbers.json") or {}).get("usual_why")) if v.get("url")
               else ("no_link" if not (_load(d / "numbers.json") or {}).get("usual") else None),
               measures=_load(d / "measures.json"), report=_load(d / "spark.json"),
               chapters=v.get("chapters") or [], replayed=v.get("replayed") or [],
               shots=sh.get("shots") or [], strips={k: rel(d / "shots" / f"{k}.jpg") for k in ("hook", "end")
                                                    if (d / "shots" / f"{k}.jpg").exists()},
               sheets=[rel(p) for p in sorted((d / "shots").glob("sheet_*.jpg"))] if (d / "shots").is_dir() else [],
               ways=same_video(v.get("sha256"), v.get("video")), folder=rel(d))
    from . import retention as RT
    key = RT.key_of(v.get("url"))
    out.update(retention=retention_view(d, v, tr), post_key=key, own=own_post(key))   # your own video's retention
    return out


def users_of(video: Path) -> list[str]:
    """The SPARK folders made from this video file (the Delete dialog warns before the video goes)."""
    out = []
    for d in sorted(ROOT.iterdir()) if ROOT.is_dir() else []:
        v = _load(d / "video.json") if d.is_dir() else None
        if isinstance(v, dict) and v.get("video") and _same(v["video"], str(video)):
            out.append(d.name)
    return out


def videos() -> set[str]:
    """The file names (lower case) of the videos SPARK read - not "waiting to be analysed"."""
    out = set()
    for d in ROOT.iterdir() if ROOT.is_dir() else []:
        v = _load(d / "video.json") if d.is_dir() else None
        if isinstance(v, dict) and v.get("video"):
            out.add(Path(v["video"]).name.lower())
    return out


def show_text(name: str) -> str:
    """What Claude reads first (spark.py show): the video, the user's question, the table, what there is to read."""
    d, v = need(name)
    fps, drop = float(v["fps"]), bool(v.get("drop_frame"))
    tr = transcript(d)
    T = table(d)
    num = _load(d / "numbers.json") or {}
    mea = _load(d / "measures.json") or {}
    fm = v.get("format") or {}
    L = [f"SPARK: {d.name}  ({label_of(v)})", f"video: {v.get('video')}",
         f"source: {v.get('url') or 'a file (no link)'} · {v.get('platform') or ''} · {v.get('uploader') or ''}",
         f"{fps:g} fps · {v['frames']} frames (f0-{int(v['frames']) - 1}, 00:00:00:00 - "
         f"{frame_to_tc(int(v['frames']) - 1, fps, drop)}) · {fm.get('shape', '?')} {fm.get('length', '?')}",
         f"the user asks: {v['ask']}" if v.get("ask") else "the user asks: nothing in particular - why it worked, in general",
         "", "the table (cite a number as {\"number\": \"<key>\"} - never write a ratio of your own):"]
    for k, r in T.items():
        if r["v"] is not None:
            L.append(f"  {k} = {num_str(r['v'], r['unit'])}   ({r['label']})")
    unknown = [k for k, r in T.items() if r["v"] is None]
    if unknown:
        L.append(f"  unknown here: {', '.join(unknown)}")
    us = num.get("usual")
    if us:
        L.append(f"the creator's usual: median {us['median']:,} views of {us['how']}"
                 + "".join(f"; NOTE {c}" for c in us.get("caveats") or []))
    else:
        L.append(f"the creator's usual: unknown - {num.get('usual_why') or 'no lookup yet'}")
    if num.get("fetched"):
        L.append(f"numbers fetched {num['fetched']} (views keep changing; YouTube's list rounds them)")
    RV = retention_view(d, v, tr)
    if RV and RV["mismatch"]:
        L.append(f"the user's retention graph is {RV['end_s']:g} s long, this video {float(v.get('duration_s') or 0):.1f} s "
                 "- NOT used (another cut, or its end line misplaced); say so if it matters")
    elif RV:
        S = RV["summary"]
        L.append(f"THE USER'S OWN VIDEO - their retention graph, traced by the lab from their screenshot ({RV['traced']}; "
                 f"{S['seen']} of {S['total']} seconds seen"
                 + (f", not seen: {', '.join(f'{a:g}-{b:g} s' for a, b in S['gaps'])}" if S.get("gaps") else "") + "):")
        L.append("  the steepest drops (the share of those watching who left in 3 s) - WHERE people left, never why:")
        for w in RV["drops"]:
            L.append(f"  {w['at_label']} - {w['end_label']}: {w['loss']:g} % left ({w['from']:g} -> {w['to']:g} % still "
                     f"watching)" + (f" · said: \"{w['words']}\"" if w["words"] else " · nothing said")
                     + (f" · shot #{w['shot']}" if w.get("shot") else ""))
        U = RV["usual"]
        L.append("  their usual: " + (f"{U['n']} other traced videos on {RV['platform']} (ret_usual_*)" if U else
                                      "fewer than 5 other traced videos - no usual yet; never compare with other creators"))
    hk = mea.get("hook") or {}
    if hk.get("first_words"):
        L.append(f"first words: \"{hk['first_words']}\"")
    if (mea.get("pacing") or {}).get("note"):
        L.append(f"pacing note: {mea['pacing']['note']}")
    L.append("")
    if tr:
        L.append(f"transcript: {tr.get('source')} ({tr.get('lang') or '?'}), {len(tr['lines'])} lines, "
                 f"{tr.get('words')} words -> {d / 'content' / 'transcript.txt'}")
    else:
        L.append("transcript: none - " + "; ".join(v.get("issues") or ["no words found"]))
    for i, c in enumerate(v.get("chapters") or []):
        L.append(f"chapter {i}: {c['title']}  {label(c['start'], fps, drop)} - {label(c['end'], fps, drop)}")
    for a, b in v.get("replayed") or []:
        L.append(f"most replayed: {label(a, fps, drop)} - {label(b, fps, drop)}")
    sh = d / "shots"
    if sh.is_dir():
        L.append(f"pictures: {sh / 'hook.jpg'} (the first 3 s), {sh / 'end.jpg'} (the last 3 s), "
                 f"{len(list(sh.glob('sheet_*.jpg')))} sheet(s) of one frame per shot in {sh} - shots.json lists the frames "
                 "a point may show")
    for p in sorted((d / "content").glob("thumbnail.*")) if (d / "content").is_dir() else []:
        if p.suffix.lower() in (".jpg", ".png", ".webp"):
            L.append(f"thumbnail / cover: {p}")
    if (d / "content" / "info.json").exists():
        L.append(f"title, description, tags, language: {d / 'content' / 'info.json'}")
    ways = same_video(v.get("sha256"), v.get("video"))
    if ways["flux"]:
        from .profile import profile
        pr = profile(ways["flux"]) or {}
        lines = pr.get("lines") or {}
        L.append(f"FLUX analysis of the same video: analysis\\{ways['flux']} - {lines.get('content') or ''} "
                 f"{lines.get('cinematic') or ''}".rstrip())
    if ways["notes"]:
        L.append(f"its notes (INDEX): analysis\\notes\\{ways['notes']}\\notes.md")
    brand = LAB / "knowledge" / "local" / "brand.json"
    if brand.exists():
        L.append(f"My Brand (for the take-aways): {brand}")
    L.append("spark: " + ("written " + str((_load(d / 'spark.json') or {}).get('made')) if (d / "spark.json").exists()
                          else "not written yet"))
    return "\n".join(L)


def selfcheck() -> int:
    """The gate and the creator's usual on a made-up folder (no network, no video)."""
    import tempfile
    global ROOT
    ok = True

    def check(cond, what):
        nonlocal ok
        print(("PASS  " if cond else "FAIL  ") + what)
        ok = ok and bool(cond)
    # the creator's usual
    ents = [{"id": f"v{i}", "views": 1000 * (i + 1), "ts": None} for i in range(30)]
    u, why = usual_from(ents, "v15", None)
    check(u and u["n"] == 20 and u["median"] == 16000 and all(x["id"] != "v15" for x in u["videos"]),
          f"the usual = the median of the 10 before and 10 after it, itself left out ({u and u['median']})")
    u, why = usual_from(ents[:3], "v1", None)
    check(u is None and "only 2" in why, f"too few to compare: none ({why})")
    rule = _date_ts(VIEW_RULE)
    ents2 = [{"id": f"w{i}", "views": 100 if i < 6 else 10_000, "ts": rule + (86400 * (30 - i * 5))} for i in range(12)]
    u, why = usual_from(ents2, "w3", time.strftime("%Y-%m-%d", time.localtime(rule + 86400 * 20)))
    check(u and u["median"] == 100 and u["caveats"], f"never across {VIEW_RULE}: the other side left out "
          f"({u and u['n']} kept)")
    check(result_of(3.2) == "outlier" and result_of(1.0) == "usual" and result_of(0.5) == "below"
          and result_of(None) == "unknown", "outlier / usual / below / unknown")
    # the gate on a made-up folder
    with tempfile.TemporaryDirectory() as tmp:
        old = ROOT
        ROOT = Path(tmp)
        try:
            d = ROOT / "x"
            (d / "content").mkdir(parents=True)
            (d / "shots").mkdir()
            write_json(d / "video.json", {"name": "x", "fps": 30, "frames": 900, "title": "T", "video": "", "format": {}})
            write_json(d / "content" / "transcript.json", {"source": "subtitles", "lines": [
                {"start": 10, "end": 80, "text": "nobody tells you this about money", "words": []},
                {"start": 500, "end": 560, "text": "so here is the real answer you wanted", "words": []}]})
            write_json(d / "shots" / "shots.json", {"frames": [{"f": 0}, {"f": 45}, {"f": 600}]})
            write_json(d / "numbers.json", {"fetched": "now", "video": {"views": 90000, "likes": 4500, "comments": 300,
                                                                        "followers": 10000},
                                            "usual": {"median": 30000, "n": 20, "how": "", "caveats": [], "videos": []}})
            write_json(d / "measures.json", {"duration_s": 30, "pacing": {"shots": 12, "cuts_per_min": 22.0},
                                             "hook": {"cuts": 1, "words": 6, "text": True}})
            T = table(d)
            check(T["outlier"]["v"] == 3.0 and T["likes_per_1k"]["v"] == 50.0 and T["views_per_follower"]["v"] == 9.0,
                  "the table: outlier 3x, 50 likes per 1,000 views, 9 views per follower")
            ev_n = [{"number": "outlier"}]
            good = {"verdict": "An outlier (3x its usual): the hook names a secret and the answer lands late.",
                    "hook_type": "curiosity", "not_explained": "Timing and the algorithm's first test.",
                    "takeaways": ["Open on the secret.", "Keep the answer late.", "Say it in 3 s."],
                    "rubric": [{"key": k, "label": "unknown", "text": "The video cannot tell."} for k in RUBRIC_KEYS]}
            good["rubric"][0] = {"key": "idea", "label": "measured", "text": "Views 3x the creator's usual.", "evidence": ev_n}
            good["rubric"][2] = {"key": "hook", "label": "judgement", "text": "A secret named at once.",
                                 "evidence": [{"quote": "nobody tells you this"}]}
            good["rubric"][3] = {"key": "payoff", "label": "judgement", "text": "The answer lands at 56 % of the video.",
                                 "evidence": [{"quote": "here is the real answer"}]}
            rep, bad = check_draft("x", good)
            check(not bad and rep["result"] == "outlier" and rep["rubric"][3]["evidence"][0]["share"] == 56,
                  f"a good draft passes; the tool sets the result and where the payoff lands (56 %) {bad[:2]}")
            worse = {**good, "verdict": "It went viral because the hook caused 5x more watching."}
            worse["rubric"] = [dict(p) for p in good["rubric"]]
            worse["rubric"][2] = {"key": "hook", "label": "judgement", "text": "A secret.",
                                  "evidence": [{"quote": "the real answer you wanted"}]}
            worse["rubric"][0] = {"key": "idea", "label": "measured", "text": "Liked 7x more.", "evidence": [{"shown": 7}]}
            worse["rubric"] = worse["rubric"][:-1]
            _, bad = check_draft("x", worse)
            msgs = " | ".join(bad)
            check(all(s in msgs for s in ("claims a cause", "5x", "first 3 s", "not a frame of the sheets",
                                          "missing context")),
                  f"a cause, a ratio of its own, a late hook, a frame not shown, a missing point: all refused ({len(bad)})")
            _, bad = check_draft("x", {**good, "rubric": good["rubric"][:2] + [
                {"key": "hook", "label": "judgement", "text": "x", "evidence": [{"quote": "this quote is not there"}]}]
                + good["rubric"][3:]})
            check(any("not in the transcript" in b for b in bad), "a quote not in the words is refused")
            try:
                save_spark("x", worse)
                check(False, "nothing is saved when a check fails")
            except ValueError:
                check(not (d / "spark.json").exists(), "nothing is saved when a check fails")
            save_spark("x", good)
            check((d / "spark.json").exists() and "## Not explained" in (d / "spark.md").read_text(encoding="utf-8"),
                  "a good draft is saved with its Markdown")
            check(pending() == [] and list_spark()[0]["status"] == "ready", "the list: ready once written")
            # 2026-11-03: a finished SPARK is a style reference (style.find "spark:x") - its pacing and structure,
            # never effects; the points it could not judge and the views stay out
            from . import style as ST
            c = ST.find(REF + "x")
            txt = ST.text(ST.merge([c])) if c else ""
            check(c and c["origin"] == "spark" and c["pacing"]["cuts_per_min"] == 22.0 and c["effects"] == []
                  and c["talking"] is False and "## Structure (SPARK" in txt and "A secret named at once." in txt
                  and "Open on the secret." in txt and "not measured: SPARK reads the structure" in txt
                  and "The video cannot tell." not in txt and "90000" not in txt,
                  "a SPARK as a style reference: its pacing, hook and take-aways; effects 'not measured', no views")
            check(ST.find(REF + "nope") is None and ref_name("x") is None and ref_name(REF) is None
                  and ref_name(REF + "x") == "x", "only a written SPARK, by its spark: key")
            sp = {"speech": {"words_per_min": 150, "talk_pct": 70}}
            check(talking(sp, ["tutorial"]) and not talking(sp, ["music video"])
                  and not talking({"speech": {"words_per_min": 77, "talk_pct": 67}}, []),
                  "a talking video: fast words over most of it, never a tagged song")
            # 2026-11-02: the user's own retention graph (motionlab\retention), matched by the post's link
            from . import retention as RT
            old_rt = RT.PATH
            RT.PATH = ROOT / "retention.json"
            try:
                pts = [[s, 100 - 3 * s if s < 10 else 70 - (s - 10)] for s in range(31)]
                write_json(RT.PATH, {"videos": {"tiktok:123456789": {
                    "platform": "tiktok", "id": "123456789", "end_s": 30, "points": pts,
                    "summary": RT.summarize(pts, 30), "traced": "now"}}})
                vj = {"name": "x", "fps": 30, "frames": 900, "title": "T", "video": "", "format": {}, "duration_s": 30.0,
                      "url": "https://www.tiktok.com/@me/video/123456789"}
                write_json(d / "video.json", vj)
                T, RV = table(d), retention_view(d, vj)
                w0 = (RV or {}).get("drops", [{}])[0]
                check(T["ret_3s"]["v"] == 91 and T["ret_drop"]["v"] == 11.4 and w0.get("s") == 7 and w0.get("f") == 210
                      and w0.get("at_label") == "f210 (00:00:07:00)",
                      f"your retention: 91 % at 3 s, the steepest drop 11.4 % at f210 (00:00:07:00) "
                      f"({T['ret_3s']['v']}, {T['ret_drop']['v']}, {w0.get('at_label')})")
                hook = {"key": "hook", "label": "measured", "text": "91 % still watching at 3 s.",
                        "evidence": [{"number": "ret_3s"}]}
                _, bad = check_draft("x", {**good, "rubric": good["rubric"][:2] + [hook] + good["rubric"][3:]})
                check(not bad, f"a point may cite it {bad[:1]}")
                write_json(d / "video.json", {**vj, "duration_s": 50.0})
                check(table(d)["ret_3s"]["v"] is None and retention_view(d, {**vj, "duration_s": 50.0})["mismatch"],
                      "a graph of another length is not used")
            finally:
                RT.PATH = old_rt
        finally:
            ROOT = old
    print("SPARK selfcheck: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1
