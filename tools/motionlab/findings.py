"""Lessons that earn their confidence (2026-11-02; docs\\plans.md *Learn from your own posts* R3 - the user: "continue
with R3"): patterns across the user's OWN posts, each a hunch until later posts confirm it. From a creator's coaching
guide the user brought (2026-11-02): features labelled before the numbers are looked at (here: measured by the lab -
nothing is judged, so nothing is labelled after seeing a number), at least 8 videos on each side, "can't tell" as an
answer, a pattern that must survive leaving its strongest video out, confidence earned only by separate later runs
with new videos, lost when untested, and a refuted lesson kept with why it failed.

knowledge\\local\\findings.json (never shared):
  "findings": [{"id": "f2", "platform", "feature": {"key", "op": "<=" | "yes" | "==", "value"}, "metric",
                "direction": "higher" | "lower", "claim" (English, built here), "level": 0 hunch | 1 likely | 2 settled,
                "confirmations", "weakened", "status": "active" | "refuted", "why_refuted", "created", "last_tested",
                "runs": [{date, verdict, why, n_yes, n_no, med_yes, med_no, new, counted, yes: [keys], no: [keys]}]}]

The confidence (worked out on every run, never typed): the run that found it = confirmation 1 (a hunch); a later run
that supports it with at least NEW_MIN videos no earlier counted run used = one more (2 = likely, 3 = settled); the
same videos again count nothing; a run with enough new videos that cannot tell = weakened (one step down); a run that
goes the other way = refuted (the claim stays, with the numbers that refuted it). Shown one step lower after DECAY_DAYS
untested, stale after STALE_DAYS. A pattern across videos is never the cause of one video's result.

    posts()                 every own post: its numbers (experiments.numbers_of) + its measured features
    run(f, posts)           one test of a finding -> {verdict: supports | contradicts | cant_tell, why, ...}
    scan(posts)             patterns that stand out now (hunches only) + how many were tried
    keep(spec), retest_all(), forget(id), view() (the page), memory_lines() (Claude's memory), selfcheck()
"""
from __future__ import annotations

import os
import re
import statistics
import threading
import time
from datetime import date, datetime
from pathlib import Path

from . import i18n as I18N
from .util import LAB, read_json, write_json

PATH = Path(os.environ.get("MOTIONLAB_FINDINGS") or (LAB / "knowledge" / "local" / "findings.json"))
MIN_SIDE = 8                 # videos on each side before a pattern counts (the guide's bar)
NEW_MIN = 3                  # new videos a later run needs to count as separate evidence
DECAY_DAYS, STALE_DAYS = 30, 90
WINDOW_DAYS = 120            # posts older than this are left out (another era of the account)
RATIO_MIN_VIEWS = 1000       # per-1,000 numbers only from videos with this many views
METRIC_ORDER = ["hold_3s", "hold_10s", "end", "views_7d", "likes_per_1k", "comments_per_1k", "avg_pct"]  # retention first
LEVELS = ("hunch", "likely", "settled")
# the measured features (key -> English words, kind, unit) - the lab's, never Claude's: nothing labelled after the numbers
FEATURES = {"length_s": ("length", "num", "s"), "posted_hour": ("the hour it went up", "num", "h"),
            "weekday": ("the day it went up", "cat", ""), "pillar": ("the content pillar", "cat", ""),
            "hook_text": ("text on screen in the first 3 s", "bool", ""),
            "hook_cuts": ("cuts in the first 3 s", "num", ""), "hook_words": ("words in the first 3 s", "num", ""),
            "first_cut_s": ("the first cut", "num", "s"), "cuts_per_min": ("cuts per minute", "num", ""),
            "words_per_min": ("words per minute", "num", "")}
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_LOCK = threading.RLock()


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M")


def _load_json(p: Path, default):
    try:
        d = read_json(p)
        return d if isinstance(d, type(default)) else default
    except (OSError, ValueError):
        return default


# ------------------------------------------------------------------------------------------------ the posts
def posts(soc=None, ret=None, sts=None, cal=None, sparks=None, today: date | None = None) -> list[dict]:
    """Every own post the lab knows (Check my pages + the traced retention graphs): {key, platform, title, thumb, date,
    url, m: {metric: value}, f: {feature: value}, measured (read by SPARK)}."""
    from . import experiments as EX
    from .retention import key_of
    if soc is None:
        from . import social as SO
        soc = SO.load()
    if ret is None:
        from . import retention as RT
        ret = RT.load()["videos"]
    if sts is None:
        from . import stats as STS
        sts = STS.load()
    if cal is None:
        from . import agency as AG
        cal = AG.load()
    if sparks is None:
        from . import spark as SP
        sparks = SP.by_post()
    today = today or date.today()
    pillar_of = {}
    for p in cal.get("posts") or []:
        for u in (p.get("links") or {}).values():
            k = key_of(u)
            if k and p.get("pillar"):
                pillar_of[k] = p["pillar"]
    rows, seen = [], set()
    for plat, pg in (soc.get("pages") or {}).items():
        for v in pg.get("videos") or []:
            if not v.get("id"):
                continue
            key = f"{plat}:{v['id']}"
            seen.add(key)
            rows.append((key, plat, v.get("url") or "", v))
    for key, e in (ret or {}).items():                       # a traced graph of a post no check lists (Instagram)
        if key not in seen and ":" in key:
            rows.append((key, key.split(":", 1)[0], e.get("url") or "", {"duration": e.get("end_s"), "title": e.get("title")}))
    out = []
    for key, plat, url, v in rows:
        n = EX.numbers_of(url or _url_of(key), soc, ret, sts)
        d = None
        try:
            d = date.fromisoformat(str(v.get("date") or "")[:10])
        except ValueError:
            pass
        if d and (today - d).days > WINDOW_DAYS:
            continue
        f = {k: None for k in FEATURES}
        f["length_s"] = round(float(v["duration"])) if v.get("duration") else None
        if v.get("time") and re.match(r"\d{2}:\d{2}", str(v["time"])):
            f["posted_hour"] = int(str(v["time"])[:2])
        if d:
            f["weekday"] = DAYS[d.weekday()]
        f["pillar"] = pillar_of.get(key)
        sp = (sparks or {}).get(key)
        if sp:
            from . import spark as SP
            mea = _load_json(SP.ROOT / sp["name"] / "measures.json", {})
            hk, pc, sc = mea.get("hook") or {}, mea.get("pacing") or {}, mea.get("speech") or {}
            f.update(hook_text=hk.get("text"), hook_cuts=hk.get("cuts"), hook_words=hk.get("words"),
                     first_cut_s=pc.get("first_cut_s"), cuts_per_min=pc.get("cuts_per_min"),
                     words_per_min=sc.get("words_per_min"))
        m = {k: n.get(k) for k in METRIC_ORDER}
        if (n.get("views") or 0) < RATIO_MIN_VIEWS:
            m["likes_per_1k"] = m["comments_per_1k"] = None
        out.append({"key": key, "platform": plat, "title": v.get("title") or n.get("title"), "thumb": v.get("thumb"),
                    "date": v.get("date"), "url": url, "views": n.get("views"), "m": m, "f": f, "measured": bool(sp)})
    return out


def _url_of(key: str) -> str:
    plat, vid = key.split(":", 1)
    return {"tiktok": f"https://www.tiktok.com/@x/video/{vid}", "youtube": f"https://www.youtube.com/shorts/{vid}",
            "instagram": f"https://www.instagram.com/reel/{vid}/"}.get(plat, "")


# ------------------------------------------------------------------------------------------------ one run
def _side(p: dict, feat: dict) -> bool | None:
    """True = the pattern's side, False = the rest, None = the feature is not known for this post."""
    x = p["f"].get(feat["key"])
    if x is None:
        return None
    kind = FEATURES[feat["key"]][1]
    if kind == "num":
        return float(x) <= float(feat["value"])
    if kind == "bool":
        return bool(x) == (feat["op"] == "yes")
    return str(x) == str(feat["value"])


def _kind(metric: str) -> str:
    from . import experiments as EX
    return EX.METRICS[metric][1]


def _beats(a: float, b: float, kind: str) -> bool:
    from . import experiments as EX
    return (a >= b * EX.MARGIN[kind] and a > b) if kind in ("views", "ratio") else (a - b >= EX.MARGIN[kind])


def run(f: dict, all_posts: list[dict]) -> dict:
    """One test of a finding on the posts there are now: the medians of both sides and the verdict - supports (beats
    the rest by the margin, at least MIN_SIDE videos a side, and still does with its strongest video left out),
    contradicts (the rest beats it by the margin), or cant_tell (and why)."""
    metric, kind = f["metric"], _kind(f["metric"])
    el = [p for p in all_posts if p["platform"] == f["platform"] and p["m"].get(metric) is not None]
    yes = [p for p in el if _side(p, f["feature"]) is True]
    no = [p for p in el if _side(p, f["feature"]) is False]
    out = {"date": _now(), "n_yes": len(yes), "n_no": len(no), "yes": [p["key"] for p in yes],
           "no": [p["key"] for p in no], "med_yes": None, "med_no": None}
    if len(yes) < MIN_SIDE or len(no) < MIN_SIDE:
        return {**out, "verdict": "cant_tell", "why": "few"}
    vy = [float(p["m"][metric]) for p in yes]
    vn = [float(p["m"][metric]) for p in no]
    my, mn = statistics.median(vy), statistics.median(vn)
    out.update(med_yes=round(my, 1), med_no=round(mn, 1))
    hi = f["direction"] == "higher"
    good, other = (my, mn) if hi else (mn, my)            # "lower": the rest must beat this side
    if _beats(good, other, kind):
        strongest = max(vy) if hi else min(vy)            # leave the side's strongest video out: still there?
        rest = list(vy)
        rest.remove(strongest)
        my2 = statistics.median(rest)
        if not _beats(*((my2, mn) if hi else (mn, my2)), kind):
            return {**out, "verdict": "cant_tell", "why": "one_video"}
        return {**out, "verdict": "supports", "why": ""}
    if _beats(other, good, kind):
        return {**out, "verdict": "contradicts", "why": ""}
    return {**out, "verdict": "cant_tell", "why": "close"}


def claim_of(f: dict) -> str:
    """The finding in plain English (the page builds its own words from the same parts)."""
    from . import experiments as EX
    from . import brand as BR
    k = f["feature"]["key"]
    words, kind, unit = FEATURES[k]
    if kind == "num":
        side = f"{words} {f['feature']['value']:g}{' ' + unit if unit else ''} or less"
    elif kind == "bool":
        side = f"{words}: {f['feature']['op']}"
    else:
        side = f"{words}: {f['feature']['value']}"
    return (f"{BR.PLATFORMS.get(f['platform'], f['platform'])}: videos with {side} - {EX.METRICS[f['metric']][0]} is "
            f"{f['direction']} than the rest")


# ------------------------------------------------------------------------------------------------ the scan
def _splits(ps: list[dict]) -> list[dict]:
    """The ways to split one platform's posts: a number at its median, yes / no, one value against the rest."""
    out = []
    for k, (_, kind, _u) in FEATURES.items():
        vals = [p["f"][k] for p in ps if p["f"].get(k) is not None]
        if len(vals) < 2 * MIN_SIDE:
            continue
        if kind == "num":
            med = statistics.median(float(x) for x in vals)
            out.append({"key": k, "op": "<=", "value": round(med, 1) if med % 1 else int(med)})
        elif kind == "bool":
            out.append({"key": k, "op": "yes", "value": True})
        else:
            for v in sorted(set(map(str, vals))):
                if sum(1 for x in vals if str(x) == v) >= MIN_SIDE:
                    out.append({"key": k, "op": "==", "value": v})
    return out


def scan(all_posts: list[dict] | None = None) -> dict:
    """The patterns that stand out now, per platform - hunches only (many patterns are tried: some will be chance;
    only later posts can confirm one). Those already kept are left out."""
    all_posts = posts() if all_posts is None else all_posts
    kept = {(f["platform"], f["feature"]["key"], str(f["feature"].get("value")), f["metric"])
            for f in load()["findings"]}
    cands, tried = [], 0
    for plat in sorted({p["platform"] for p in all_posts}):
        ps = [p for p in all_posts if p["platform"] == plat]
        for sp in _splits(ps):
            for metric in METRIC_ORDER:
                tried += 1
                if (plat, sp["key"], str(sp.get("value")), metric) in kept:
                    continue
                for direction in ("higher", "lower"):
                    f = {"platform": plat, "feature": sp, "metric": metric, "direction": direction}
                    r = run(f, all_posts)
                    if r["verdict"] == "supports":
                        k = _kind(metric)
                        effect = (r["med_yes"] / r["med_no"] if r["med_no"] else 99) if k in ("views", "ratio") \
                            else abs(r["med_yes"] - r["med_no"])
                        cands.append({**f, "claim": claim_of(f), "run": r, "effect": round(effect, 2)})
                        break
    cands.sort(key=lambda c: (METRIC_ORDER.index(c["metric"]), -c["effect"]))
    # how far each platform is from a pattern: per metric, the videos that have it
    bars = {}
    for plat in sorted({p["platform"] for p in all_posts}):
        ps = [p for p in all_posts if p["platform"] == plat]
        bars[plat] = {"posts": len(ps), "measured": sum(1 for p in ps if p["measured"]),
                      "metrics": {m: sum(1 for p in ps if p["m"].get(m) is not None) for m in METRIC_ORDER}}
    return {"candidates": cands[:12], "tried": tried, "bars": bars, "min_side": MIN_SIDE}


# ------------------------------------------------------------------------------------------------ the store
def load() -> dict:
    d = _load_json(PATH, {})
    d.setdefault("findings", [])
    return d


def _write(d: dict) -> None:
    d["updated"] = _now()
    write_json(PATH, d)


def _clean_spec(spec: dict) -> dict:
    from . import experiments as EX
    spec = spec if isinstance(spec, dict) else {}
    ft = spec.get("feature") if isinstance(spec.get("feature"), dict) else {}
    if ft.get("key") not in FEATURES or spec.get("metric") not in EX.METRICS or spec.get("direction") not in (
            "higher", "lower") or spec.get("platform") not in ("tiktok", "youtube", "instagram"):
        raise ValueError(I18N.t("not a pattern MotionLab can test"))
    kind = FEATURES[ft["key"]][1]
    if kind == "num":
        try:
            feat = {"key": ft["key"], "op": "<=", "value": float(ft.get("value"))}
        except (TypeError, ValueError):
            raise ValueError(I18N.t("not a pattern MotionLab can test")) from None
        if feat["value"].is_integer():
            feat["value"] = int(feat["value"])
    elif kind == "bool":
        feat = {"key": ft["key"], "op": "yes" if ft.get("op") != "no" else "no", "value": ft.get("op") != "no"}
    else:
        feat = {"key": ft["key"], "op": "==", "value": str(ft.get("value") or "")[:60]}
    return {"platform": spec["platform"], "feature": feat, "metric": spec["metric"], "direction": spec["direction"]}


def keep(spec: dict, all_posts: list[dict] | None = None) -> dict:
    """A pattern kept as a lesson: tested now - it must stand out today - and saved as a hunch (confirmation 1)."""
    f = _clean_spec(spec)
    all_posts = posts() if all_posts is None else all_posts
    r = run(f, all_posts)
    if r["verdict"] != "supports":
        raise ValueError(I18N.t("this pattern does not stand out in your posts now - nothing kept"))
    with _LOCK:
        d = load()
        if any((x["platform"], x["feature"], x["metric"]) == (f["platform"], f["feature"], f["metric"])
               for x in d["findings"]):
            raise ValueError(I18N.t("this lesson is kept already"))
        n = max([int(x["id"][1:]) for x in d["findings"] if re.fullmatch(r"f\d+", str(x.get("id") or ""))] or [0])
        new = {"id": f"f{n + 1}", **f, "claim": claim_of(f), "level": 0, "confirmations": 1, "weakened": False,
               "status": "active", "why_refuted": "", "created": _now(), "last_tested": _now(),
               "runs": [{**r, "new": r["n_yes"] + r["n_no"], "counted": True}]}
        d["findings"].append(new)
        _write(d)
        return new


def record(f: dict, r: dict) -> str:
    """One run into a finding (in place) -> what changed: confirmed | weakened | refuted | same | few."""
    used = set()
    for x in f["runs"]:
        if x.get("counted"):
            used |= set(x.get("yes") or []) | set(x.get("no") or [])
    new = len((set(r["yes"]) | set(r["no"])) - used)
    r = {**r, "new": new, "counted": False}
    change = "same"
    if r["verdict"] == "contradicts":
        f["status"] = "refuted"
        f["why_refuted"] = (f"{r['date']}: {r['med_yes']:g} against {r['med_no']:g} for the rest "
                            f"({r['n_yes']} / {r['n_no']} videos)")
        change = "refuted"
    elif r["verdict"] == "supports" and new >= NEW_MIN:
        f["confirmations"] = int(f.get("confirmations") or 1) + 1
        f["level"] = 2 if f["confirmations"] >= 3 else 1 if f["confirmations"] >= 2 else 0
        f["weakened"] = False
        r["counted"] = True
        change = "confirmed"
    elif r["verdict"] == "cant_tell" and r["why"] != "few" and new >= NEW_MIN:
        f["level"] = max(0, int(f.get("level") or 0) - 1)
        f["weakened"] = True
        r["counted"] = True
        change = "weakened"
    elif r["verdict"] == "cant_tell" and r["why"] == "few":
        change = "few"
    f["last_tested"] = r["date"]
    f["runs"] = (f.get("runs") or [])[-19:] + [r]
    return change


def retest_all(all_posts: list[dict] | None = None) -> list[dict]:
    """Every active lesson tested again on the posts there are now (after Check my pages, a traced graph, or the
    user's click) -> [{id, claim, change, verdict}]."""
    all_posts = posts() if all_posts is None else all_posts
    out = []
    with _LOCK:
        d = load()
        for f in d["findings"]:
            if f.get("status") != "active":
                continue
            r = run(f, all_posts)
            out.append({"id": f["id"], "claim": f["claim"], "change": record(f, r), "verdict": r["verdict"]})
        if d["findings"]:
            _write(d)
    return out


def forget(fid: str) -> None:
    with _LOCK:
        d = load()
        d["findings"] = [x for x in d["findings"] if x.get("id") != fid]
        _write(d)


def status_of(f: dict, today: datetime | None = None) -> dict:
    """What a lesson is worth today: refuted, stale (untested STALE_DAYS), or its level - one step lower after
    DECAY_DAYS untested."""
    if f.get("status") == "refuted":
        return {"status": "refuted", "level": None, "days": None}
    try:
        days = ((today or datetime.now()) - datetime.strptime(f["last_tested"], "%Y-%m-%d %H:%M")).days
    except (KeyError, ValueError):
        days = 0
    if days > STALE_DAYS:
        return {"status": "stale", "level": None, "days": days}
    lvl = max(0, int(f.get("level") or 0) - (1 if days > DECAY_DAYS else 0))
    return {"status": LEVELS[lvl], "level": lvl, "days": days, "decayed": days > DECAY_DAYS,
            "weakened": bool(f.get("weakened"))}


def view() -> dict:
    """The page: the lessons (their worth today, the last run, the videos on each side), the patterns that stand out
    now, and how far each platform is from the bar."""
    ps = posts()
    by_key = {p["key"]: p for p in ps}

    def side(keys, metric):
        rows = [by_key[k] for k in keys if k in by_key]
        rows.sort(key=lambda p: -(p["m"].get(metric) or 0))
        return [{"key": p["key"], "title": p["title"], "thumb": p["thumb"], "url": p["url"], "date": p["date"],
                 "value": p["m"].get(metric)} for p in rows]
    fs = []
    for f in load()["findings"]:
        last = (f.get("runs") or [{}])[-1]
        fs.append({**{k: v for k, v in f.items() if k != "runs"}, **status_of(f),
                   "runs": [{k: v for k, v in r.items() if k not in ("yes", "no")} for r in f.get("runs") or []],
                   "yes": side(last.get("yes") or [], f["metric"]), "no": side(last.get("no") or [], f["metric"])})
    order = {"settled": 0, "likely": 1, "hunch": 2, "stale": 3, "refuted": 4}
    fs.sort(key=lambda x: (order.get(x["status"], 9), x.get("created") or ""))
    sc = scan(ps)
    return {"findings": fs, **sc, "new_min": NEW_MIN, "decay_days": DECAY_DAYS, "stale_days": STALE_DAYS,
            "features": list(FEATURES), "metrics": METRIC_ORDER}


def memory_lines() -> list[str]:
    """For Claude's memory (knowledge.py memory): the lessons likely or settled today, with their numbers - patterns
    across the user's posts, never the cause of one video's result; the hunches only counted."""
    rows, hunches = [], 0
    for f in load()["findings"]:
        st = status_of(f)
        if st["status"] in ("likely", "settled"):
            last = next((r for r in reversed(f.get("runs") or []) if r.get("med_yes") is not None), {})
            rows.append(f"- [{st['status']}, {f['confirmations']} confirmations, tested {f['last_tested'][:10]}] "
                        f"{f['claim']} ({last.get('med_yes', '?'):g} against {last.get('med_no', '?'):g}; "
                        f"{last.get('n_yes')} / {last.get('n_no')} videos)" if last else
                        f"- [{st['status']}] {f['claim']}")
        elif st["status"] == "hunch":
            hunches += 1
    if not rows and not hunches:
        return []
    L = ["## What the user's own posts taught (Content agency > What works; patterns, never one video's cause)", ""]
    L += rows or ["- nothing confirmed yet"]
    if hunches:
        L.append(f"- {hunches} hunch(es) not confirmed yet - not rules; never build on them as facts")
    return L + [""]


# ------------------------------------------------------------------------------------------------ the self-check
def selfcheck() -> dict:
    import tempfile
    global PATH
    lines: list[str] = []
    ok = True

    def check(cond, what):
        nonlocal ok
        ok = ok and bool(cond)
        lines.append(("ok   " if cond else "FAIL ") + what)

    def mk(i, length, hold, plat="tiktok"):
        return {"key": f"{plat}:{1000 + i}", "platform": plat, "title": f"v{i}", "thumb": None, "date": "2026-10-01",
                "url": "", "views": 5000, "m": {"hold_3s": hold, "views_7d": 5000, "likes_per_1k": 40.0},
                "f": {**{k: None for k in FEATURES}, "length_s": length}, "measured": False}

    old = PATH
    with tempfile.TemporaryDirectory(prefix="ml_find_") as td:
        PATH = Path(td) / "findings.json"
        try:
            short = [mk(i, 20 + i % 5, 80 + i % 3) for i in range(9)]                # <= 30 s: ~81 % at 3 s
            long_ = [mk(20 + i, 50 + i, 68 + i % 4) for i in range(9)]               # > 30 s: ~69 %
            ps = short + long_
            sc = scan(ps)
            c = next((x for x in sc["candidates"] if x["feature"]["key"] == "length_s" and x["metric"] == "hold_3s"), None)
            check(c and c["direction"] == "higher" and c["run"]["n_yes"] == 9,
                  f"the scan finds short videos holding more at 3 s ({c and c['claim']}; {sc['tried']} tried)")
            check(run({"platform": "tiktok", "feature": {"key": "length_s", "op": "<=", "value": 30}, "metric": "hold_3s",
                       "direction": "higher"}, ps[:7] + long_)["why"] == "few", "fewer than 8 a side: can't tell")
            f = keep({"platform": "tiktok", "feature": {"key": "length_s", "value": 30}, "metric": "hold_3s",
                      "direction": "higher"}, ps)
            check(f["id"] == "f1" and status_of(f)["status"] == "hunch", "kept as a hunch (confirmation 1)")
            try:
                keep({"platform": "tiktok", "feature": {"key": "length_s", "value": 30}, "metric": "views_7d",
                      "direction": "higher"}, ps)
                check(False, "refused: a pattern that does not stand out")
            except ValueError:
                check(True, "refused: a pattern that does not stand out")
            ch = retest_all(ps)
            check(ch[0]["change"] == "same" and load()["findings"][0]["confirmations"] == 1,
                  "the same videos again: nothing earned")
            ps2 = ps + [mk(40 + i, 22, 82) for i in range(2)] + [mk(50 + i, 60, 66) for i in range(2)]
            ch = retest_all(ps2)
            f1 = load()["findings"][0]
            check(ch[0]["change"] == "confirmed" and f1["confirmations"] == 2 and status_of(f1)["status"] == "likely",
                  f"4 new videos that agree: likely ({ch[0]['change']})")
            ps3 = ps2 + [mk(60 + i, 25, 83) for i in range(3)]
            retest_all(ps3)
            f1 = load()["findings"][0]
            check(status_of(f1)["status"] == "settled", "3 more: settled")
            ml = memory_lines()
            check(any(x.startswith("- [settled, 3 confirmations") for x in ml), f"Claude's memory carries it: {ml[2:3]}")
            later = datetime.strptime(f1["last_tested"], "%Y-%m-%d %H:%M")
            from datetime import timedelta
            check(status_of(f1, later + timedelta(days=40))["status"] == "likely"
                  and status_of(f1, later + timedelta(days=100))["status"] == "stale", "untested 40 days: likely; 100: stale")
            # the median moved by one strong video: can't tell; no difference: can't tell
            spec = {"platform": "tiktok", "feature": {"key": "length_s", "op": "<=", "value": 30}, "metric": "hold_3s",
                    "direction": "higher"}
            lone = [mk(i, 20, h) for i, h in enumerate((70, 70, 70, 70, 75, 90, 90, 90, 90))] + \
                [mk(20 + i, 60, 71) for i in range(9)]
            r = run(spec, lone)
            check(r["verdict"] == "cant_tell" and r["why"] == "one_video",
                  f"75 against 71, but 72.5 with its strongest video left out: can't tell ({r['why']})")
            r = run(spec, [mk(i, 20, 70) for i in range(9)] + [mk(20 + i, 60, 71) for i in range(9)])
            check(r["verdict"] == "cant_tell" and r["why"] == "close", f"70 against 71: can't tell ({r['why']})")
            # new videos that go the other way: refuted, the claim kept
            flip = ps3 + [mk(80 + i, 21, 50) for i in range(20)]
            ch = retest_all(flip)
            f1 = load()["findings"][0]
            check(f1["status"] == "refuted" and f1["claim"].startswith("TikTok: videos with length 30 s or less")
                  and f1["why_refuted"], f"new videos the other way: refuted, the claim kept ({f1['why_refuted']})")
            check(retest_all(flip) == [], "a refuted lesson is not tested again")
            check(memory_lines() == [], "Claude's memory: nothing while nothing is likely or settled")
            forget("f1")
            check(load()["findings"] == [], "forgotten")
        finally:
            PATH = old
    return {"passed": ok, "lines": lines}
