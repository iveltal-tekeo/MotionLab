"""Tests of one idea (2026-11-02; docs\\plans.md *Learn from your own posts* R2 - the user: "continue with R2"): two or
three versions of one idea posted on the SAME platform, compared by one number the user picks, then Claude's keep /
change / cut for the next version. From a creator's coaching guide the user brought (2026-11-02): a fixed id per
version (never told apart by their caption), a rule set before the numbers are in, a closed test stays closed and a
follow-up is a new test linked to its parent, every change a hypothesis to test - "do not claim a controlled A/B test".

knowledge\\local\\experiments.json (never shared):
  "tests": [{"id": "t3", "title", "change" (the one thing that differs), "platform": tiktok | youtube | instagram,
             "parent": "t1" | "", "rule": {"metric": "views_7d", "min_views": 1000},
             "versions": [{"id": "A", "label", "link", "project": "<a MotionLab video>" | "", "render": "<file>" | "",
                           "note"}, {"id": "B", ...}],
             "review": {...} (Claude's keep / change / cut - only through save_review(), the gate),
             "decision": {"pick": "A" | "B" | "C" | "none", "note", "date"} (closed), "created", "updated"}]

The numbers come from what the lab already has - nothing is read from the platforms here: Check my pages (views at
a check near 48 h / 7 days / 28 days after the post went up, likes and comments; social.json), the retention graphs
traced from the user's screenshots (retention.json: still watching at 3 s / 10 s / the end) and the stats files the
user imported (stats.json: the average % viewed). One post each is never a controlled test (other days, other
audiences): a winner needs a clear margin, and the page always says to repeat it.

    load(), get(id), save(test) (checked; a closed test only takes its note), close(id, pick, note), again(id),
    remove(id), view(id) / views() (+ each version's numbers, the result, the state, its SPARK), compare(test, ...),
    show_text(id) (what Claude reads first), check_review(id, draft) / save_review(id, draft) (the gate)
    selfcheck()
"""
from __future__ import annotations

import os
import re
import threading
import time
from datetime import datetime
from pathlib import Path

from . import i18n as I18N
from .util import LAB, read_json, write_json

PATH = Path(os.environ.get("MOTIONLAB_EXPERIMENTS") or (LAB / "knowledge" / "local" / "experiments.json"))
PLATFORMS = ("tiktok", "youtube", "instagram")
VERSION_IDS = ("A", "B", "C")
# the numbers a test can be decided by (key -> English words, kind): views at an age, a share still watching, a ratio
METRICS = {"views_48h": ("views about 48 hours after it went up", "views", 48),
           "views_7d": ("views about 7 days after it went up", "views", 168),
           "views_28d": ("views about 28 days after it went up", "views", 672),
           "hold_3s": ("still watching at 3 s (the retention graph)", "pct", None),
           "hold_10s": ("still watching at 10 s (the retention graph)", "pct", None),
           "end": ("still watching at the end (the retention graph)", "pct", None),
           "likes_per_1k": ("likes per 1,000 views (the last check)", "ratio", None),
           "comments_per_1k": ("comments per 1,000 views (the last check)", "ratio", None),
           "avg_pct": ("average % viewed (your stats file)", "pct", None)}
MARGIN = {"views": 1.25, "ratio": 1.25, "pct": 3.0}   # a winner beats every other version by 25 % / by 3 points
MIN_VIEWS = 1000
KINDS = ("keep", "change", "cut")
HOWS = ("edit_only", "re_record")
ITEMS_MIN, ITEMS_MAX, TEXT_MAX, SUMMARY_MAX = 2, 12, 300, 220
_LOCK = threading.RLock()


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M")


def _s(v, n: int) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


# ------------------------------------------------------------------------------------------------ the store
def load() -> dict:
    try:
        d = read_json(PATH)
    except (OSError, ValueError):
        d = {}
    if not isinstance(d, dict):
        d = {}
    d.setdefault("tests", [])
    return d


def _write(d: dict) -> None:
    d["updated"] = _now()
    write_json(PATH, d)


def get(tid: str) -> dict | None:
    return next((t for t in load()["tests"] if t.get("id") == tid), None)


def _next_id(tests: list[dict]) -> str:
    n = max([int(t["id"][1:]) for t in tests if re.fullmatch(r"t\d+", str(t.get("id") or ""))] or [0])
    return f"t{n + 1}"


def _link(u, platform: str) -> str:
    from . import brand as BR
    from .agency import POST_HOSTS
    u = _s(u, 300)
    if not u:
        return ""
    if not re.match(r"https?://", u, re.I):
        u = "https://" + u
    if not re.match(r"https?://(?:" + POST_HOSTS[platform] + r")(?:/|$)", u, re.I):
        raise ValueError(I18N.t("not a {platform} address: {url}", platform=BR.PLATFORMS[platform], url=u))
    return u


def _project(p: str, render: str) -> tuple[str, str]:
    p = _s(p, 160)
    if not p or re.search(r"[\\/:]|\.\.", p) or not (LAB / "projects" / p).is_dir():
        return "", ""
    r = _s(render, 200)
    if r and (re.search(r"[\\/:]|\.\.", r) or not (LAB / "projects" / p / "build" / r).is_file()):
        r = ""
    return p, r


def clean(t: dict, old: dict | None = None) -> dict:
    """The page's test -> a valid one (ValueError on what cannot be kept). The review and the decision never come
    from the page: the review only through the gate, the decision through close()."""
    t = t if isinstance(t, dict) else {}
    plat = t.get("platform")
    if plat not in PLATFORMS:
        raise ValueError(I18N.t("pick the platform both versions went up on"))
    title = _s(t.get("title"), 120)
    if not title:
        raise ValueError(I18N.t("say what the test is first"))
    vs, seen_links = [], set()
    for i, v in enumerate((t.get("versions") or [])[:len(VERSION_IDS)]):
        v = v if isinstance(v, dict) else {}
        link = _link(v.get("link"), plat)
        from .retention import key_of
        if link and not key_of(link):
            raise ValueError(I18N.t("that link is not one post: {url}", url=link))
        if link and key_of(link) in seen_links:
            raise ValueError(I18N.t("two versions have the same post - each version is its own post"))
        if link:
            seen_links.add(key_of(link))
        proj, render = _project(v.get("project"), v.get("render"))
        vs.append({"id": VERSION_IDS[i], "label": _s(v.get("label"), 60), "link": link, "project": proj,
                   "render": render, "note": _s(v.get("note"), 300)})
    if len(vs) < 2:
        raise ValueError(I18N.t("a test needs two versions at least"))
    r = t.get("rule") if isinstance(t.get("rule"), dict) else {}
    metric = r.get("metric") if r.get("metric") in METRICS else ("hold_3s" if plat == "instagram" else "views_7d")
    try:
        mv = max(0, min(10_000_000, int(r.get("min_views", MIN_VIEWS))))
    except (TypeError, ValueError):
        mv = MIN_VIEWS
    out = {"id": str((old or {}).get("id") or t.get("id") or ""), "title": title, "change": _s(t.get("change"), 300),
           "platform": plat, "parent": _s(t.get("parent") if not old else old.get("parent"), 10),
           "rule": {"metric": metric, "min_views": mv}, "versions": vs,
           "created": (old or {}).get("created") or _now(), "updated": _now()}
    if old and old.get("review"):
        out["review"] = old["review"]
    return out


def save(t: dict) -> dict:
    """A new test (no id) or a change to one; a closed test keeps everything but its decision's note."""
    with _LOCK:
        d = load()
        tid = str((t or {}).get("id") or "")
        old = next((x for x in d["tests"] if x.get("id") == tid), None) if tid else None
        if old and old.get("decision"):
            old["decision"]["note"] = _s(((t or {}).get("decision") or {}).get("note", old["decision"].get("note")), 500)
            old["updated"] = _now()
            _write(d)
            return old
        new = clean(t, old)
        if old:
            if [v["link"] for v in new["versions"]] != [v["link"] for v in old["versions"]] or \
                    new["rule"] != old["rule"]:
                new.pop("review", None)                # Claude's review was of other posts or another rule
            d["tests"][d["tests"].index(old)] = new
        else:
            new["id"] = _next_id(d["tests"])
            d["tests"].append(new)
        _write(d)
        return new


def close(tid: str, pick: str, note: str = "") -> dict:
    """The user's decision: the version they go on with (or none) - the test is closed for good."""
    with _LOCK:
        d = load()
        t = next((x for x in d["tests"] if x.get("id") == tid), None)
        if not t:
            raise ValueError(I18N.t("no test {id}", id=tid))
        if t.get("decision"):
            raise ValueError(I18N.t("this test is closed - start a new one with Test again"))
        if pick not in [v["id"] for v in t["versions"]] + ["none"]:
            raise ValueError(I18N.t("pick the version you go on with, or none"))
        t["decision"] = {"pick": pick, "note": _s(note, 500), "date": _now(),
                         "result": (compare(t).get("result") or {}).get("state")}
        t["updated"] = _now()
        _write(d)
        return t


def again(tid: str) -> dict:
    """A follow-up of a closed test: a new test linked to its parent, the version picked as the control (A) and a
    new version B to make and post."""
    with _LOCK:
        d = load()
        t = next((x for x in d["tests"] if x.get("id") == tid), None)
        if not t:
            raise ValueError(I18N.t("no test {id}", id=tid))
        if not t.get("decision"):
            raise ValueError(I18N.t("close the test first - pick the version you go on with"))
        pick = (t["decision"] or {}).get("pick")
        ctrl = next((v for v in t["versions"] if v["id"] == pick), t["versions"][0])
        new = {"id": _next_id(d["tests"]), "title": _s(t["title"], 110) + " (2)", "change": "",
               "platform": t["platform"], "parent": t["id"], "rule": dict(t["rule"]),
               "versions": [{**ctrl, "id": "A", "label": _s(ctrl.get("label") or I18N.t("the one you kept"), 60)},
                            {"id": "B", "label": "", "link": "", "project": ctrl.get("project") or "", "render": "",
                             "note": ""}],
               "created": _now(), "updated": _now()}
        d["tests"].append(new)
        _write(d)
        return new


def remove(tid: str) -> None:
    with _LOCK:
        d = load()
        d["tests"] = [x for x in d["tests"] if x.get("id") != tid]
        _write(d)


# ------------------------------------------------------------------------------------------------ the numbers
def _posted_ts(v: dict) -> float | None:
    try:
        return datetime.strptime(f"{v['date']} {v.get('time') or '12:00'}", "%Y-%m-%d %H:%M").timestamp()
    except (KeyError, TypeError, ValueError):
        return None


def _near(hist: list, t0: float | None, hrs: float):
    """The check nearest an age (between half and twice it) -> (ts, views) or None."""
    if t0 is None:
        return None
    best = None
    for ts, n in hist or []:
        age = (ts - t0) / 3600.0
        if hrs * 0.5 <= age <= hrs * 2 and (best is None or abs(ts - t0 - hrs * 3600) < abs(best[0] - t0 - hrs * 3600)):
            best = (ts, n)
    return best


def numbers_of(link: str, soc: dict, ret: dict, sts: dict) -> dict:
    """Every number the lab has of one post: {metric: value | None}, + views now, its date, its picture, why a
    number is missing."""
    from .retention import key_of
    key = key_of(link) if link else None
    out = {k: None for k in METRICS}
    out.update(key=key, views=None, date=None, time=None, title=None, thumb=None, duration=None, missing={})
    if not key:
        return out
    plat, vid = key.split(":", 1)
    pv = next((x for x in ((soc.get("pages") or {}).get(plat) or {}).get("videos") or [] if str(x.get("id")) == vid), None)
    if pv:
        out.update(views=pv.get("views"), date=pv.get("date"), time=pv.get("time"), title=pv.get("title"),
                   thumb=pv.get("thumb"), duration=pv.get("duration"))
        t0 = _posted_ts(pv)
        hist = (soc.get("history") or {}).get(key) or []
        for k, (_, kind, hrs) in METRICS.items():
            if kind == "views":
                b = _near(hist, t0, hrs)
                out[k] = b[1] if b else None
                if not b:
                    out["missing"][k] = "no_check"
        if pv.get("views"):
            for k, src in (("likes_per_1k", "likes"), ("comments_per_1k", "comments")):
                if pv.get(src) is not None:
                    out[k] = round(1000.0 * pv[src] / pv["views"], 1)
    else:
        for k, (_, kind, _h) in METRICS.items():
            if kind == "views" or k.endswith("_per_1k"):
                out["missing"][k] = "not_read" if plat == "instagram" else "not_checked"
    e = (ret or {}).get(key)
    S = (e or {}).get("summary") or {}
    for k in ("hold_3s", "hold_10s", "end"):
        out[k] = S.get(k)
        if out[k] is None:
            out["missing"][k] = "no_graph" if not e else "not_seen"
    row = (((sts or {}).get("videos") or {}).get(plat) or {}).get(vid)
    out["avg_pct"] = (row or {}).get("avg_pct")
    if out["avg_pct"] is None:
        out["missing"]["avg_pct"] = "no_stats"
    return out


def compare(t: dict, soc: dict | None = None, ret: dict | None = None, sts: dict | None = None) -> dict:
    """The test's numbers and its result by its own rule: waiting (and why), too close to call, or a winner that beats
    every other version by the margin. Never more: one post each is not a controlled test."""
    if soc is None:
        from . import social as SO
        soc = SO.load()
    if ret is None:
        from . import retention as RT
        ret = RT.load()["videos"]
    if sts is None:
        from . import stats as STS
        sts = STS.load()
    metric, mv = t["rule"]["metric"], int(t["rule"].get("min_views") or 0)
    label, kind, _ = METRICS[metric]
    nums = {v["id"]: numbers_of(v.get("link") or "", soc, ret, sts) for v in t["versions"]}
    waiting, unchecked = [], []
    for v in t["versions"]:
        n = nums[v["id"]]
        seen = n[metric] if kind == "views" else n["views"]          # the views the minimum is checked on
        if not v.get("link"):
            waiting.append({"version": v["id"], "why": "not_posted"})
        elif n[metric] is None:
            waiting.append({"version": v["id"], "why": n["missing"].get(metric) or "unknown"})
        elif mv and seen is None:
            unchecked.append(v["id"])                                 # Instagram: its views are not read here
        elif mv and seen < mv:
            waiting.append({"version": v["id"], "why": "few_views", "views": seen})
    res = {"metric": metric, "label": label, "values": {k: n[metric] for k, n in nums.items()}, "margin": MARGIN[kind],
           "kind": kind, "min_unchecked": unchecked}
    if waiting:
        res.update(state="waiting", waiting=waiting)
        return {"numbers": nums, "result": res}
    vals = res["values"]
    best = max(vals, key=lambda k: vals[k])
    others = [vals[k] for k in vals if k != best]

    def beats(a, b):
        return (a >= b * MARGIN[kind] and a > b) if kind in ("views", "ratio") else (a - b >= MARGIN[kind])
    if all(beats(vals[best], o) for o in others):
        res.update(state="winner", winner=best)
    else:
        res.update(state="too_close", tied=[k for k in vals if not beats(vals[best], vals[k])])
    return {"numbers": nums, "result": res}


def state_of(t: dict, result: dict) -> str:
    """planned (a version not posted yet) -> testing (the numbers are not in) -> compared -> reviewed (Claude's keep /
    change / cut) -> closed (the user's decision). Worked out, never stored."""
    if t.get("decision"):
        return "closed"
    if t.get("review"):
        return "reviewed"
    if any(not v.get("link") for v in t["versions"]):
        return "planned"
    return "compared" if result.get("state") in ("winner", "too_close") else "testing"


def view(t: dict, soc=None, ret=None, sts=None, sparks: dict | None = None) -> dict:
    """A test as the page and Claude see it: + numbers per version, the result, the state, each version's SPARK."""
    if sparks is None:
        from . import spark as SP
        sparks = SP.by_post()
    c = compare(t, soc, ret, sts)
    vs = []
    for v in t["versions"]:
        n = c["numbers"][v["id"]]
        vs.append({**v, "numbers": {k: n[k] for k in METRICS}, "missing": n["missing"], "views": n["views"],
                   "date": n["date"], "time": n["time"], "title": n["title"], "thumb": n["thumb"],
                   "duration": n["duration"], "key": n["key"], "spark": sparks.get(n["key"]) if n["key"] else None})
    return {**t, "versions": vs, "result": c["result"], "state": state_of(t, c["result"])}


def views() -> dict:
    from . import retention as RT
    from . import social as SO
    from . import spark as SP
    from . import stats as STS
    soc, ret, sts, sp = SO.load(), RT.load()["videos"], STS.load(), SP.by_post()
    num = lambda t: int(t["id"][1:]) if re.fullmatch(r"t\d+", str(t.get("id") or "")) else 0    # noqa: E731
    tests = sorted(load()["tests"], key=lambda t: (t.get("created") or "", num(t)), reverse=True)  # newest first
    return {"tests": [view(t, soc, ret, sts, sp) for t in tests], "metrics": list(METRICS), "min_views": MIN_VIEWS}


# ------------------------------------------------------------------------------------------------ Claude's review
def _versions_read(t: dict) -> dict:
    """Each version's SPARK folder (its words, frames, fps): {id: {name, d, v, tr, idx, fps, frames, drop, ret}}."""
    from . import retention as RT
    from . import spark as SP
    sp = SP.by_post()
    out = {}
    for v in t["versions"]:
        k = RT.key_of(v.get("link"))
        s = sp.get(k) if k else None
        if not s:
            continue
        d, vj = SP.need(s["name"])
        tr = SP.transcript(d)
        out[v["id"]] = {"name": s["name"], "d": d, "v": vj, "tr": tr, "idx": SP._index(tr) if tr else [],
                        "fps": float(vj["fps"]), "frames": int(vj["frames"]), "drop": bool(vj.get("drop_frame")),
                        "ret": SP.retention_view(d, vj, tr)}
    return out


def _r_at(points: list, s: float):
    best = None
    for x, p in points or []:
        if p is not None and (best is None or abs(float(x) - s) < abs(best[0] - s)) and abs(float(x) - s) <= 1.0:
            best = (float(x), float(p))
    return best[1] if best else None


def check_review(tid: str, draft: dict) -> tuple[dict, list[str]]:
    """Claude's keep / change / cut -> (the review as saved, problems). Problems = nothing may be saved."""
    from . import spark as SP
    from .timecode import label
    t = get(tid)
    if not t:
        return {}, [f"no test {tid!r}"]
    bad: list[str] = []
    if any(not v.get("link") for v in t["versions"]):
        return {}, ["every version must be posted (its link) before a review"]
    R = _versions_read(t)
    miss = [v["id"] for v in t["versions"] if v["id"] not in R]
    if miss:
        return {}, [f"version(s) {', '.join(miss)} have no SPARK yet - read every version with SPARK first (the test's "
                    "Read them with SPARK button, or spark.py prepare with --url)"]
    if not isinstance(draft, dict):
        return {}, ["the draft is not a JSON object"]
    c = compare(t)
    allowed = [float(x) for x in c["result"]["values"].values() if isinstance(x, (int, float))]
    for v in c["numbers"].values():
        allowed += [float(x) for k, x in v.items() if k in METRICS and isinstance(x, (int, float))]
    summary = " ".join(str(draft.get("summary") or "").split())
    if not summary:
        bad.append("summary: missing (one line: what the versions' numbers and words say, as far as they go)")
    elif len(summary) > SUMMARY_MAX:
        bad.append(f"summary: {len(summary)} characters - at most {SUMMARY_MAX}")
    SP._banned("summary", summary, bad)
    SP._ratios("summary", summary, allowed, bad)
    raw = draft.get("items")
    if not isinstance(raw, list) or not ITEMS_MIN <= len(raw) <= ITEMS_MAX:
        bad.append(f"items: {ITEMS_MIN}-{ITEMS_MAX} keep / change / cut items")
        raw = raw[:ITEMS_MAX] if isinstance(raw, list) else []
    items = []
    for i, it in enumerate(raw):
        w = f"items[{i}]"
        if not isinstance(it, dict):
            bad.append(f"{w}: not an object")
            continue
        vid, kind = str(it.get("version") or ""), str(it.get("kind") or "")
        if vid not in R:
            bad.append(f"{w}: version {vid!r} - one of {', '.join(R)}")
            continue
        if kind not in KINDS:
            bad.append(f"{w}: kind {kind!r} - keep, change or cut")
            continue
        V = R[vid]
        f0, f1 = it.get("from"), it.get("to")
        if not all(isinstance(x, int) and not isinstance(x, bool) for x in (f0, f1)) or not 0 <= f0 <= f1 < V["frames"]:
            bad.append(f"{w}: from / to = frames of version {vid}'s video, 0-{V['frames'] - 1}, from <= to")
            continue
        text = " ".join(str(it.get("text") or "").split())
        if not text:
            bad.append(f"{w}: no text")
        elif len(text) > TEXT_MAX:
            bad.append(f"{w}: {len(text)} characters - at most {TEXT_MAX}")
        SP._banned(w, text, bad)
        rp = (V["ret"] or {}).get("points") if V["ret"] and not V["ret"].get("mismatch") else None
        r0, r1 = (_r_at(rp, f0 / V["fps"]), _r_at(rp, f1 / V["fps"])) if rp else (None, None)
        loss = round(100.0 * (1.0 - r1 / r0), 1) if r0 and r1 is not None and r0 > 0 else None
        SP._ratios(w, text, allowed + [x for x in (r0, r1, loss) if x is not None], bad)
        q = " ".join(str(it.get("quote") or "").split())
        quote = None
        if q:
            hit = SP.find_quote(V["idx"], q, f0) if V["idx"] else None
            pad = int(round(V["fps"]))
            if not V["idx"]:
                bad.append(f"{w}: version {vid} has no transcript to quote")
            elif hit is None:
                bad.append(f"{w}: the quote is not in version {vid}'s words, word for word: {q[:100]!r}")
            elif not f0 - pad <= hit[0] <= f1 + pad:
                bad.append(f"{w}: the quote is said at {label(hit[0], V['fps'], V['drop'])}, outside "
                           f"{label(f0, V['fps'], V['drop'])} - {label(f1, V['fps'], V['drop'])}")
            else:
                quote = {"text": q, "at": hit[0], "at_label": label(hit[0], V["fps"], V["drop"])}
        how = str(it.get("how") or "")
        metric = str(it.get("metric") or "")
        if kind == "change" and how not in HOWS:
            bad.append(f"{w}: how = edit_only (the footage has it) or re_record (it must be filmed or said again)")
        if kind == "cut":
            how = "edit_only"
        if kind == "keep":
            how = ""
        if kind != "keep" and metric not in METRICS:
            bad.append(f"{w}: metric = the number this change should move - one of {', '.join(METRICS)}")
        items.append({"version": vid, "kind": kind, "from": f0, "to": f1,
                      "at_label": label(f0, V["fps"], V["drop"]), "end_label": label(f1, V["fps"], V["drop"]),
                      "text": text[:TEXT_MAX], "how": how, "metric": metric if metric in METRICS else "",
                      "to_test": kind != "keep", "quote": quote,
                      "retention": {"from": r0, "to": r1, "loss": loss} if r0 is not None else None})
    if items and not any(x["kind"] == "keep" for x in items):
        bad.append("items: at least one keep - what already works stays in the next version")
    if items and not any(x["kind"] != "keep" for x in items):
        bad.append("items: at least one change or cut - what the next version tries")
    nt = draft.get("next_test") if isinstance(draft.get("next_test"), dict) else {}
    nt_out = {"try": " ".join(str(nt.get("try") or "").split())[:200],
              "same": " ".join(str(nt.get("same") or "").split())[:200], "metric": str(nt.get("metric") or "")}
    if not nt_out["try"] or not nt_out["same"] or nt_out["metric"] not in METRICS:
        bad.append("next_test: {try: the one change to test next, same: what stays the same, metric: the number that "
                   f"decides - one of {', '.join(METRICS)}}}")
    for k in ("try", "same"):
        SP._banned(f"next_test.{k}", nt_out[k], bad)
    rep = {"made": _now(), "by": "Claude", "summary": summary[:SUMMARY_MAX], "items": items, "next_test": nt_out,
           "result": c["result"].get("state"), "winner": c["result"].get("winner"),
           "sparks": {k: R[k]["name"] for k in R}}
    return rep, bad


def save_review(tid: str, draft: dict) -> dict:
    """The gate's only way in. Raises ValueError with every problem; a closed test takes no review."""
    with _LOCK:
        t = get(tid)
        if t and t.get("decision"):
            raise ValueError("nothing saved - this test is closed")
        rep, bad = check_review(tid, draft)
        if bad:
            raise ValueError("nothing saved - fix these and save again:\n- " + "\n- ".join(bad))
        d = load()
        t = next(x for x in d["tests"] if x.get("id") == tid)
        t["review"] = rep
        t["updated"] = _now()
        _write(d)
        return rep


def show_text(tid: str) -> str:
    """What Claude reads first (experiments.py show <id>)."""
    from . import spark as SP
    t = get(tid)
    if not t:
        raise ValueError(f"no test {tid!r}")
    V = view(t)
    R = V["result"]
    L = [f"TEST {t['id']}: {t['title']}  ({t['platform']}; state: {V['state']})",
         f"what differs: {t.get('change') or '(not said)'}",
         f"the rule: {METRICS[R['metric']][0]}; at least {t['rule']['min_views']:,} views each; a winner beats every "
         f"other version by {'25 %' if R['kind'] != 'pct' else '3 points'}",
         "result: " + {"winner": f"version {R.get('winner')} wins", "too_close": "too close to call ("
                       + ", ".join(R.get("tied") or []) + ")", "waiting": "waiting - " + "; ".join(
                           f"{w['version']}: {w['why']}" for w in R.get("waiting") or [])}[R["state"]]
         + " - ONE POST EACH IS NOT A CONTROLLED TEST (other days, other audiences): never claim it proves anything",
         ""]
    if t.get("parent"):
        L.insert(1, f"a follow-up of {t['parent']}")
    for v in V["versions"]:
        n = v["numbers"]
        L.append(f"version {v['id']}{' - ' + v['label'] if v.get('label') else ''}: {v.get('link') or 'not posted'}"
                 + (f" · made in MotionLab: projects\\{v['project']}" + (f"\\build\\{v['render']}" if v.get("render") else "")
                    if v.get("project") else ""))
        L.append("  numbers: " + " · ".join(f"{k} {x:g}" for k, x in n.items() if isinstance(x, (int, float)))
                 if any(isinstance(x, (int, float)) for x in n.values()) else "  numbers: none yet")
        if v.get("spark"):
            d, vj = SP.need(v["spark"]["name"])
            L.append(f"  SPARK: analysis\\spark\\{v['spark']['name']} - read it with `tools\\spark.py show "
                     f"{v['spark']['name']}` (its words, frames, fps; frames below are ITS frames)")
            rv = SP.retention_view(d, vj)
            for w in (rv or {}).get("drops") or []:
                L.append(f"  a steep drop: {w['at_label']} - {w['end_label']}: {w['loss']:g} % left"
                         + (f" · said: \"{w['words']}\"" if w["words"] else ""))
        else:
            L.append("  SPARK: none yet - the review needs every version read with SPARK")
    if t.get("review"):
        L += ["", f"reviewed {t['review']['made']} - a new review replaces it"]
    return "\n".join(L)


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

    old = PATH
    with tempfile.TemporaryDirectory(prefix="ml_exp_") as td:
        PATH = Path(td) / "experiments.json"
        try:
            ua, ub = "https://www.tiktok.com/@me/video/111111111", "https://www.tiktok.com/@me/video/222222222"
            t = save({"title": "Hook test", "change": "the first line", "platform": "tiktok",
                      "versions": [{"label": "control", "link": ua}, {"label": "question hook", "link": ""}],
                      "rule": {"metric": "views_7d", "min_views": 1000}})
            check(t["id"] == "t1" and t["versions"][1]["id"] == "B" and state_of(t, compare(t, {}, {}, {})["result"])
                  == "planned", "a new test: t1, versions A / B, planned while B is not posted")
            for bad, what in (({"title": "x", "platform": "tiktok", "versions": [{"link": ua}]}, "one version"),
                              ({"title": "x", "platform": "tiktok", "versions": [{"link": ua}, {"link": ua}]}, "the same post twice"),
                              ({"title": "x", "platform": "tiktok", "versions": [{"link": ua},
                                {"link": "https://youtu.be/abcdefghijk"}]}, "a link of another platform"),
                              ({"title": "", "platform": "tiktok", "versions": [{}, {}]}, "no title")):
                try:
                    save(bad)
                    check(False, f"refused: {what}")
                except ValueError:
                    check(True, f"refused: {what}")
            t = save({**t, "versions": [t["versions"][0], {**t["versions"][1], "link": ub}]})
            day = 86400
            t0 = datetime.strptime("2026-10-01 18:00", "%Y-%m-%d %H:%M").timestamp()
            soc = {"pages": {"tiktok": {"videos": [
                {"id": "111111111", "date": "2026-10-01", "time": "18:00", "views": 4000, "likes": 200, "comments": 8},
                {"id": "222222222", "date": "2026-10-03", "time": "18:00", "views": 9000, "likes": 300, "comments": 30}]}},
                "history": {"tiktok:111111111": [[t0 + 2 * day, 1500], [t0 + 7 * day, 3000]],
                            "tiktok:222222222": [[t0 + 2 * day + 2 * day, 4000]]}}
            c = compare(t, soc, {}, {})
            check(c["result"]["state"] == "waiting" and c["result"]["waiting"][0]["why"] == "no_check",
                  f"waiting: B has no check near 7 days yet ({c['result'].get('waiting')})")
            soc["history"]["tiktok:222222222"].append([t0 + 2 * day + 7 * day, 7000])
            c = compare(t, soc, {}, {})
            check(c["result"]["state"] == "winner" and c["result"]["winner"] == "B"
                  and c["result"]["values"] == {"A": 3000, "B": 7000}, f"views at 7 days: B wins 7000 to 3000")
            soc["history"]["tiktok:222222222"][-1][1] = 3300
            c = compare(t, soc, {}, {})
            check(c["result"]["state"] == "too_close", "3300 against 3000: too close to call (a 25 % margin)")
            t2 = {**t, "rule": {"metric": "hold_3s", "min_views": 1000}}
            ret = {"tiktok:111111111": {"summary": {"hold_3s": 71.0}}, "tiktok:222222222": {"summary": {"hold_3s": 76.5}}}
            c = compare(t2, soc, ret, {})
            check(c["result"]["state"] == "winner" and c["result"]["winner"] == "B", "held at 3 s: 76.5 against 71: B (3 points)")
            ret["tiktok:111111111"]["summary"]["hold_3s"] = 75.0
            check(compare(t2, soc, ret, {})["result"]["state"] == "too_close", "76.5 against 75: too close")
            soc["pages"]["tiktok"]["videos"][0]["views"] = 400
            c = compare(t2, soc, ret, {})
            check(c["result"]["state"] == "waiting" and c["result"]["waiting"][0]["why"] == "few_views",
                  "fewer views than the rule's minimum: waiting")
            try:
                close(t["id"], "D")
                check(False, "refused: a version that is not there")
            except ValueError:
                check(True, "refused: a version that is not there")
            cl = close(t["id"], "B", "the question hook")
            check(get(t["id"])["decision"]["pick"] == "B", "closed: B picked")
            s2 = save({**cl, "title": "changed", "decision": {"note": "a note"}})
            check(s2["title"] == "Hook test" and s2["decision"]["note"] == "a note", "a closed test keeps all but its note")
            try:
                close(t["id"], "A")
                check(False, "refused: closing twice")
            except ValueError:
                check(True, "refused: closing twice")
            n = again(t["id"])
            check(n["id"] == "t2" and n["parent"] == "t1" and n["versions"][0]["link"] == ub and not n["versions"][1]["link"],
                  "Test again: t2, linked to t1, the picked B as the control, a new B to post")
            _, bad = check_review("t2", {})
            check(bad and "posted" in bad[0], "a review needs every version posted")
            remove("t2")
            check(get("t2") is None and get("t1") is not None, "removed")
            # the gate, on two made-up SPARK folders (the versions' words and frames)
            from . import spark as SP
            old_sp = SP.ROOT
            SP.ROOT = Path(td) / "spark"
            try:
                _, bad = check_review("t1", {})
                check(bad and "SPARK" in bad[0], "a review needs every version read with SPARK")
                for name, url, words in (("va", ua, "nobody tells you this about money"),
                                         ("vb", ub, "do you know the one thing nobody tells you")):
                    d = SP.ROOT / name
                    (d / "content").mkdir(parents=True)
                    write_json(d / "video.json", {"name": name, "fps": 30, "frames": 900, "url": url, "video": "",
                                                  "duration_s": 30.0})
                    write_json(d / "content" / "transcript.json", {"source": "subtitles", "lines": [
                        {"start": 10, "end": 80, "text": words, "words": []},
                        {"start": 300, "end": 360, "text": "so here is the real answer", "words": []}]})
                good = {"summary": "B's question hook held more viewers on its first check; one post each.",
                        "items": [{"version": "B", "kind": "keep", "from": 0, "to": 89, "text": "The question opens it.",
                                   "quote": "do you know the one thing"},
                                  {"version": "A", "kind": "change", "from": 280, "to": 380, "how": "edit_only",
                                   "metric": "hold_10s", "text": "The answer comes late - move it before 10 s.",
                                   "quote": "here is the real answer"},
                                  {"version": "A", "kind": "cut", "from": 381, "to": 500, "metric": "end",
                                   "text": "A pause after the answer."}],
                        "next_test": {"try": "the answer before 10 s", "same": "the question hook", "metric": "hold_10s"}}
                rep, bad = check_review("t1", good)
                check(not bad and rep["items"][1]["at_label"] == "f280 (00:00:09:10)" and rep["items"][2]["how"] == "edit_only"
                      and rep["items"][1]["to_test"] and not rep["items"][0]["to_test"],
                      f"a good review passes; frames + timecode set by the tool, every change to test {bad[:2]}")
                worse = {**good, "summary": "The question hook caused 3x more views.",
                         "items": [{**good["items"][1], "how": "", "quote": "nobody tells you this about money"},
                                   {**good["items"][2], "metric": ""}]}
                _, bad = check_review("t1", worse)
                msgs = " | ".join(bad)
                check(all(s in msgs for s in ("claims a cause", "3x", "how = edit_only", "outside", "metric =",
                                              "at least one keep")),
                      f"a cause, a ratio of its own, no how, a quote outside its frames, no metric, no keep: refused "
                      f"({len(bad)})")
                try:
                    save_review("t1", good)
                    check(False, "a closed test takes no review")
                except ValueError:
                    check(get("t1").get("review") is None, "a closed test takes no review")
            finally:
                SP.ROOT = old_sp
        finally:
            PATH = old
    return {"passed": ok, "lines": lines}
