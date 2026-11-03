"""What worked this month, ending in three next tests (2026-11-02; docs\\plans.md 0.6.5 step 18 + *Learn from your own
posts* R4 - the user: "continue with R4"): Content agency > *Monthly review*. The lab's part needs no Claude: the
month's own posts against the user's usual (the median of their posts of the last 120 days), the ones that did best
by views and by retention, the month's posts grouped by pillar / length / text in the first 3 s (a hint - a month is a
few posts; What works tests the patterns), the tests of one idea and the lessons with what changed in them. Claude's
part (`/spark month <YYYY-MM>`, through the gate) is one line of summary and exactly three next tests - what to try,
what stays the same, the number that decides it and the evidence (posts, lessons, tests the lab knows). A picked one
becomes an idea on the calendar; next month's review shows where it got to.

knowledge\\local\\monthly.json (never shared):
  "months": {"2026-10": {"review": {"made", "by": "Claude", "summary", "next_tests": [{"n": 1, "platform", "try",
                                     "same", "metric", "why", "evidence": [{"type": post|lesson|test, "id", "label",
                                     "thumb", "url"}]}], "posts", "checked"} (only through save_review(), the gate),
                         "picked": [{"n", "try", "same", "metric", "platform", "calendar": "c12", "date"}]}}

    data(month)          the lab's month (no Claude): its posts, the platforms' usual, the top ones, the groups, the
                         tests, the lessons (default month: this one when it has posts, else the one before)
    view(month)          the page: data + Claude's review + the picks + last month's picks and where they are now
    show_text(month)     what Claude reads first; check_review / save_review (the gate); plan(month, n) = next test n
                         as an idea on the calendar (Content agency's calendar.json); selfcheck()
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

PATH = Path(os.environ.get("MOTIONLAB_MONTHLY") or (LAB / "knowledge" / "local" / "monthly.json"))
TESTS_N = 3                  # the review ends in exactly three next tests
TRY_MAX, WHY_MAX, SUMMARY_MAX, EVIDENCE_MAX = 200, 300, 220, 6
USUAL_MIN = 5                # the user's usual on a platform: the median of at least 5 of their posts
YOUNG_DAYS = 7               # a post younger than this at its last check is still growing: listed, never ranked
TOP_N, HOLD_N = 5, 3
# the length groups: up to 30 s, 31-60 s, 1-3 min (still a short on YouTube), longer (a long video - another format)
LENGTHS = ((30, "to_30s"), (60, "to_60s"), (180, "to_3min"), (None, "over_3min"))
_LOCK = threading.RLock()


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M")


def _s(v, n: int) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def month_of(v) -> str:
    v = str(v or "").strip()
    if not re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", v):
        raise ValueError(I18N.t("not a month (YYYY-MM): {value}", value=v[:20]))
    return v


def shift(month: str, k: int) -> str:
    y, m = map(int, month.split("-"))
    m += k
    y += (m - 1) // 12
    return f"{y:04d}-{(m - 1) % 12 + 1:02d}"


def _day(v) -> date | None:
    try:
        return date.fromisoformat(str(v or "")[:10])
    except ValueError:
        return None


def _ts(v) -> float | None:
    try:
        return datetime.strptime(str(v or "")[:19], "%Y-%m-%d %H:%M:%S").timestamp()
    except ValueError:
        return None


def default_month(ps: list[dict], today: date) -> str:
    cur = today.strftime("%Y-%m")
    return cur if any(str(p.get("date") or "").startswith(cur) for p in ps) else shift(cur, -1)


def _med(vals: list, n_min: int = 1):
    vals = [float(x) for x in vals if x is not None]
    return round(statistics.median(vals), 1) if len(vals) >= n_min else None


def _length_group(s) -> str | None:
    if s is None:
        return None
    return next(name for top, name in LENGTHS if top is None or float(s) <= top)


# ------------------------------------------------------------------------------------------------ the lab's month
def _sources(src: dict | None, today: date) -> dict:
    """Everything the month is made of - injected by the self-check, read from the lab's stores otherwise."""
    src = dict(src or {})
    if "soc" not in src:
        from . import social as SO
        src["soc"] = SO.load()
    if "ps" not in src:
        from . import findings as FD
        src["ps"] = FD.posts(soc=src["soc"], today=today)
    if "finds" not in src:
        from . import findings as FD
        src["finds"] = FD.load()["findings"]
    if "tests" not in src:
        src["tests"] = _test_rows(src["soc"])
    return src


def _test_rows(soc: dict) -> list[dict]:
    from . import experiments as EX
    from . import retention as RT
    from . import stats as STS
    ret, sts = RT.load()["videos"], STS.load()
    out = []
    for t in EX.load()["tests"]:
        c = EX.compare(t, soc, ret, sts)
        R = c["result"]
        vals = {k: v for k, v in (R.get("values") or {}).items() if v is not None}
        lead = None
        if R.get("state") == "winner" and len(vals) >= 2:
            w = vals[R["winner"]]
            second = max(v for k, v in vals.items() if k != R["winner"])
            lead = round(w - second, 1) if R["kind"] == "pct" else (round(w / second, 2) if second else None)
        out.append({"id": t["id"], "title": t["title"], "platform": t["platform"], "change": t.get("change") or "",
                    "state": EX.state_of(t, R), "metric": R["metric"], "kind": R["kind"], "result": R.get("state"),
                    "winner": R.get("winner"), "values": vals, "lead": lead, "created": t.get("created") or "",
                    "decided": (t.get("decision") or {}).get("date") or "", "pick": (t.get("decision") or {}).get("pick"),
                    "dates": [n.get("date") for n in c["numbers"].values() if n.get("date")],
                    "next_test": (t.get("review") or {}).get("next_test")})
    return out


def _gather(month: str | None, src: dict | None = None, today: date | None = None) -> tuple[dict, dict, dict]:
    """-> (the month as the page and Claude see it, the window's posts by key, the sources)."""
    from . import experiments as EX
    from . import findings as FD
    today = today or date.today()
    S = _sources(src, today)
    soc, ps = S["soc"], S["ps"]
    month = month_of(month) if month else default_month(ps, today)
    checked = _ts(soc.get("checked"))
    rows = []
    for p in ps:
        d = _day(p.get("date"))
        hist = (soc.get("history") or {}).get(p["key"]) or []
        at = max([float(h[0]) for h in hist if h] or [checked or 0]) or None
        age = (datetime.fromtimestamp(at).date() - d).days if d and at else None
        rows.append({**p, "age_days": age, "young": age is not None and age < YOUNG_DAYS})
    plats = sorted({p["platform"] for p in rows})
    usual = {}
    for pl in plats:
        grown = [p["views"] for p in rows if p["platform"] == pl and p.get("views") is not None and not p["young"]]
        holds = [p["m"].get("hold_3s") for p in rows if p["platform"] == pl and p["m"].get("hold_3s") is not None]
        usual[pl] = {"views": _med(grown, USUAL_MIN), "views_n": len(grown), "hold_3s": _med(holds, USUAL_MIN),
                     "hold_3s_n": len(holds)}
    for p in rows:
        u = usual[p["platform"]]["views"]
        p["x_usual"] = round(p["views"] / u, 2) if u and p.get("views") is not None and not p["young"] else None
    mine = sorted([p for p in rows if str(p.get("date") or "").startswith(month)],
                  key=lambda p: (p.get("date") or "", p["key"]))
    pf = {}
    for pl in plats:
        mp = [p for p in mine if p["platform"] == pl]
        if not mp:
            continue
        pf[pl] = {"posts": len(mp), "young": sum(1 for p in mp if p["young"]), **{f"usual_{k}": v for k, v in usual[pl].items()},
                  "median_x": _med([p["x_usual"] for p in mp]), "median_views": _med([p["views"] for p in mp if not p["young"]]),
                  "median_hold_3s": _med([p["m"].get("hold_3s") for p in mp]),
                  "traced": sum(1 for p in mp if p["m"].get("hold_3s") is not None)}
    ranked = sorted([p for p in mine if not p["young"] and p.get("views") is not None],
                    key=lambda p: (p["x_usual"] or 0, p["views"] or 0), reverse=True)
    held = sorted([p for p in mine if p["m"].get("hold_3s") is not None], key=lambda p: -p["m"]["hold_3s"])
    groups = []
    for gk, value_of in (("pillar", lambda p: p["f"].get("pillar") or None),
                         ("length", lambda p: _length_group(p["f"].get("length_s"))),
                         ("hook_text", lambda p: None if p["f"].get("hook_text") is None else bool(p["f"]["hook_text"]))):
        by: dict = {}
        for p in mine:
            v = value_of(p)
            if v is not None and p["x_usual"] is not None:
                by.setdefault(v, []).append(p)
        if len(by) >= 2:
            g = [{"value": v, "n": len(xs), "median_x": _med([p["x_usual"] for p in xs]), "keys": [p["key"] for p in xs]}
                 for v, xs in by.items()]
            g.sort(key=lambda r: -(r["median_x"] or 0))
            groups.append({"key": gk, "rows": g})
    tests = [t for t in S["tests"] if t["created"][:7] == month or t["decided"][:7] == month
             or any(str(x)[:7] == month for x in t["dates"])]
    lessons = []
    for f in S["finds"]:
        st = FD.status_of(f)
        last = next((r for r in reversed(f.get("runs") or []) if r.get("med_yes") is not None), {})
        kind = EX.METRICS[f["metric"]][1] if f.get("metric") in EX.METRICS else "views"
        x = None
        if last.get("med_no"):
            x = round(last["med_yes"] - last["med_no"], 1) if kind == "pct" else round(last["med_yes"] / last["med_no"], 2)
        lessons.append({"id": f["id"], "claim": f.get("claim") or "", "platform": f.get("platform"),
                        "feature": f.get("feature"), "metric": f.get("metric"), "direction": f.get("direction"),
                        "status": st["status"], "confirmations": f.get("confirmations") or 1,
                        "kept_now": str(f.get("created") or "")[:7] == month,
                        "runs": [{"date": r.get("date"), "verdict": r.get("verdict"), "why": r.get("why"),
                                  "new": r.get("new")} for r in f.get("runs") or [] if str(r.get("date") or "")[:7] == month],
                        "med_yes": last.get("med_yes"), "med_no": last.get("med_no"), "n_yes": last.get("n_yes"),
                        "n_no": last.get("n_no"), "x": x})
    slim = lambda p: {k: p.get(k) for k in ("key", "platform", "title", "thumb", "url", "date", "views", "age_days",  # noqa: E731
                                            "young", "x_usual", "m", "f", "measured")}
    D = {"month": month, "prev": shift(month, -1), "next": shift(month, 1) if shift(month, 1) <= today.strftime("%Y-%m") else None,
         "checked": soc.get("checked"), "posts": [slim(p) for p in mine], "platforms": pf,
         "top_views": [p["key"] for p in ranked[:TOP_N]], "top_hold": [p["key"] for p in held[:HOLD_N]], "groups": groups,
         "tests": tests, "lessons": lessons, "young_days": YOUNG_DAYS, "usual_min": USUAL_MIN,
         "window": len(rows), "platforms_known": plats}
    return D, {p["key"]: p for p in rows}, S


def data(month: str | None = None, src: dict | None = None, today: date | None = None) -> dict:
    return _gather(month, src, today)[0]


# ------------------------------------------------------------------------------------------------ the store
def load() -> dict:
    try:
        d = read_json(PATH)
    except (OSError, ValueError):
        d = {}
    if not isinstance(d, dict):
        d = {}
    d.setdefault("months", {})
    return d


def _write(d: dict) -> None:
    d["updated"] = _now()
    write_json(PATH, d)


def _cal_status(picked: list[dict], cal: dict) -> list[dict]:
    by = {p["id"]: p for p in cal.get("posts") or []}
    out = []
    for x in picked or []:
        c = by.get(x.get("calendar"))
        out.append({**x, "status": c["status"] if c else "removed", "when": (c or {}).get("date") or "",
                    "links": (c or {}).get("links") or {}})
    return out


def view(month: str | None = None, src: dict | None = None, today: date | None = None) -> dict:
    """The page: the lab's month + Claude's review, the picks, and last month's picks with where they got to."""
    from . import agency as AG
    D = data(month, src, today)
    cal = (src or {}).get("cal") or AG.load(AG.PATH)
    st = load()["months"]
    M = st.get(D["month"]) or {}
    before = _cal_status((st.get(D["prev"]) or {}).get("picked") or [], cal)
    return {**D, "review": M.get("review"), "picked": _cal_status(M.get("picked") or [], cal), "before": before,
            "reviewed": sorted(k for k, v in st.items() if v.get("review"))}


# ------------------------------------------------------------------------------------------------ what Claude reads
def _num(x) -> str:
    return "-" if x is None else f"{x:,.0f}" if isinstance(x, (int, float)) and abs(x) >= 100 else f"{x:g}"


def show_text(month: str | None = None, src: dict | None = None, today: date | None = None) -> str:
    from . import experiments as EX
    from . import findings as FD
    D = _gather(month, src, today)[0]
    m = D["month"]
    L = [f"MONTH {m} - what worked (Content agency > Monthly review); the numbers: Check my pages (last {D['checked'] or 'never'}),"
         " the retention graphs the user traced, their stats files",
         "A MONTH IS A FEW POSTS: never what CAUSED a result - say what to TEST next (What works tests patterns over 120 days)",
         f"x usual = views at the last check / the platform's usual (the median of the user's posts of the last 120 days "
         f"that were {YOUNG_DAYS}+ days old at their check, from {USUAL_MIN}); a post under {YOUNG_DAYS} days at its check is"
         " young (still growing): never ranked", ""]
    if not D["posts"]:
        L.append(f"no posts went up in {m} - nothing to review (the window has {D['window']} posts)")
        return "\n".join(L)
    for pl, s in D["platforms"].items():
        L.append(f"{pl}: {s['posts']} posts ({s['young']} young) · usual views {_num(s['usual_views'])} (of {s['usual_views_n']})"
                 f" · this month's median {_num(s['median_x'])}x usual · held at 3 s: month median {_num(s['median_hold_3s'])} %"
                 f" ({s['traced']} traced), usual {_num(s['usual_hold_3s'])} % (of {s['usual_hold_3s_n']})")
    L += ["", "POSTS (evidence keys):"]
    for p in D["posts"]:
        n = " · ".join(f"{k} {_num(v)}" for k, v in p["m"].items() if v is not None)
        f = " · ".join(f"{k} {v}" for k, v in p["f"].items() if v is not None)
        L.append(f"  {p['key']}  {p['date']}  \"{_s(p['title'], 80)}\"  {_num(p['views'])} views at {p['age_days']} days"
                 + (" (young)" if p["young"] else f" = {_num(p['x_usual'])}x usual" if p["x_usual"] is not None else "")
                 + (f" · {n}" if n else "") + (f" · features: {f}" if f else "") + ("" if p["measured"] else " · not read by SPARK"))
    L.append(f"best by views: {', '.join(D['top_views']) or '-'} · held best at 3 s: {', '.join(D['top_hold']) or '- (no graph traced)'}")
    for g in D["groups"]:
        L.append(f"by {g['key']} (a hint, {sum(r['n'] for r in g['rows'])} posts): "
                 + "; ".join(f"{r['value']}: {r['n']} posts, median {_num(r['median_x'])}x usual" for r in g["rows"]))
    L += ["", "TESTS OF ONE IDEA this month (ids for evidence):" if D["tests"] else "TESTS OF ONE IDEA: none this month"]
    for t in D["tests"]:
        vals = " · ".join(f"{k} {_num(v)}" for k, v in t["values"].items())
        L.append(f"  {t['id']} [{t['state']}] {t['platform']} \"{t['title']}\" - what differs: {t['change'] or '-'} - "
                 f"by {t['metric']}: {vals or 'no numbers'} -> {t['result']}"
                 + (f" {t['winner']} (by {_num(t['lead'])}{' points' if t['kind'] == 'pct' else 'x'})" if t["winner"] else "")
                 + (f" · the user went on with {t['pick']}" if t["pick"] else "")
                 + (f" · Claude's next test there: try {t['next_test']['try']}" if t.get("next_test") else ""))
    L += ["", "LESSONS (What works; ids for evidence):" if D["lessons"] else "LESSONS: none kept yet (What works)"]
    for x in D["lessons"]:
        L.append(f"  {x['id']} [{x['status']}, {x['confirmations']} confirmations] {x['claim']}"
                 + (f" ({_num(x['med_yes'])} against {_num(x['med_no'])} for the rest, {x['n_yes']} / {x['n_no']} videos"
                    + (f", {_num(x['x'])}{' points' if EX.METRICS.get(x['metric'], ('', 'views'))[1] == 'pct' else 'x'}" if x["x"] is not None else "")
                    + ")" if x["med_yes"] is not None else "")
                 + ("".join(f" · {r['date'][:10]}: {r['verdict']}" for r in x["runs"])))
    V = view(m, src, today) if src is None or "cal" in src else None
    if V and V["before"]:
        L += ["", f"LAST MONTH'S NEXT TESTS ({D['prev']}), where they are now:"]
        for x in V["before"]:
            L.append(f"  {x['n']}. {x['platform']} try {x['try']} (decided by {x['metric']}) -> calendar {x['calendar']}: "
                     f"{x['status']}" + (" · " + ", ".join(x["links"].values()) if x["links"] else ""))
    L += ["", f"metrics a next test can be decided by: {', '.join(EX.METRICS)} (Instagram: views and likes are not read "
          "here - hold_3s, hold_10s, end or avg_pct)", f"platforms: {', '.join(D['platforms_known'])}",
          f"features What works measures: {', '.join(FD.FEATURES)}"]
    return "\n".join(L)


# ------------------------------------------------------------------------------------------------ the gate
def _allowed(D: dict, every: dict) -> dict[str, list[float]]:
    """The numbers a text may carry, by unit - an x must be an x of show (a post or a group against the usual, a
    lesson's or a test's lead), a % one of its shares (retention, average viewed, the 25 % margin), a "per 1,000" one
    of its ratios: never a number of another kind that happens to be near."""
    from . import experiments as EX
    out = {"x": [], "pct": [0.0, 100.0, 25.0], "k": []}
    kind_of = lambda m: EX.METRICS.get(m, ("", "views"))[1]             # noqa: E731
    for p in every.values():
        if p.get("x_usual") is not None:
            out["x"].append(float(p["x_usual"]))
        for k, v in p["m"].items():
            u = {"pct": "pct", "ratio": "k"}.get(kind_of(k))
            if v is not None and u:
                out[u].append(float(v))
    for s in D["platforms"].values():
        out["x"] += [float(s[k]) for k in ("median_x",) if s.get(k) is not None]
        out["pct"] += [float(s[k]) for k in ("median_hold_3s", "usual_hold_3s") if s.get(k) is not None]
    for g in D["groups"]:
        out["x"] += [float(r["median_x"]) for r in g["rows"] if r["median_x"] is not None]
    for x in D["lessons"]:
        u = {"pct": "pct", "ratio": "k"}.get(kind_of(x["metric"]))
        if u:
            out[u] += [float(v) for v in (x["med_yes"], x["med_no"]) if v is not None]
        if x["x"] is not None and kind_of(x["metric"]) != "pct":
            out["x"].append(float(x["x"]))
    for t in D["tests"]:
        u = {"pct": "pct", "ratio": "k"}.get(t["kind"])
        if u:
            out[u] += [float(v) for v in t["values"].values()]
        if t["lead"] is not None and t["kind"] != "pct":
            out["x"].append(float(t["lead"]))
    return out


def _numbers(where: str, text: str, allowed: dict, bad: list[str]) -> None:
    """Every "N x", "N %" and "N per 1,000" in a text must be one of show's numbers of that unit."""
    from . import spark as SP
    for m in SP._RATIO.finditer(text):
        try:
            n = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        unit = m.group(2).lower()
        u = "x" if unit in ("x", "×") else "pct" if unit == "%" else "k"
        if not SP._ratio_ok(n, allowed[u]):
            bad.append(f"{where}: {m.group(0)!r} is not one of show's numbers "
                       + {"x": "against the usual (x usual, a group's or a lesson's / test's lead)",
                          "pct": "in % (retention, average viewed)", "k": "per 1,000 views"}[u]
                       + " - use show's value; never a number of your own")


def check_review(month: str, draft: dict, src: dict | None = None, today: date | None = None) -> tuple[dict, list[str]]:
    """Claude's review -> (the review as saved, problems). Problems = nothing may be saved."""
    from . import experiments as EX
    from . import spark as SP
    try:
        month = month_of(month)
    except ValueError as e:
        return {}, [str(e)]
    D, every, S = _gather(month, src, today)
    if not D["posts"]:
        return {}, [f"no posts went up in {month} - nothing to review"]
    if not isinstance(draft, dict):
        return {}, ["the draft is not a JSON object"]
    bad: list[str] = []
    allowed = _allowed(D, every)
    summary = " ".join(str(draft.get("summary") or "").split())
    if not summary:
        bad.append("summary: missing (one line: what this month's posts say, as far as they go)")
    elif len(summary) > SUMMARY_MAX:
        bad.append(f"summary: {len(summary)} characters - at most {SUMMARY_MAX}")
    SP._banned("summary", summary, bad)
    _numbers("summary", summary, allowed, bad)
    lessons = {x["id"]: x for x in D["lessons"]}
    tests = {t["id"]: t for t in S["tests"]}
    month_keys = {p["key"] for p in D["posts"]}
    raw = draft.get("next_tests")
    if not isinstance(raw, list) or len(raw) != TESTS_N:
        bad.append(f"next_tests: exactly {TESTS_N} - what to try next, each decided by one number")
        raw = raw[:TESTS_N] if isinstance(raw, list) else []
    out, tries, cites_month = [], set(), False
    for i, nt in enumerate(raw):
        w = f"next_tests[{i}]"
        if not isinstance(nt, dict):
            bad.append(f"{w}: not an object")
            continue
        plat, metric = str(nt.get("platform") or ""), str(nt.get("metric") or "")
        if plat not in D["platforms_known"]:
            bad.append(f"{w}: platform {plat!r} - one the user posts on: {', '.join(D['platforms_known'])}")
        if metric not in EX.METRICS:
            bad.append(f"{w}: metric {metric!r} - one of {', '.join(EX.METRICS)}")
        elif plat == "instagram" and EX.METRICS[metric][1] in ("views", "ratio"):
            bad.append(f"{w}: Instagram's views and likes are not read here - decide it by hold_3s, hold_10s, end or avg_pct")
        txt = {}
        for k, n in (("try", TRY_MAX), ("same", TRY_MAX), ("why", WHY_MAX)):
            v = " ".join(str(nt.get(k) or "").split())
            if not v:
                bad.append(f"{w}.{k}: missing" + {"try": " (the one change to test)", "same": " (what stays the same)",
                                                   "why": " (the evidence in words, with its numbers)"}[k])
            elif len(v) > n:
                bad.append(f"{w}.{k}: {len(v)} characters - at most {n}")
            SP._banned(f"{w}.{k}", v, bad)
            _numbers(f"{w}.{k}", v, allowed, bad)
            txt[k] = v[:n]
        norm = re.sub(r"[^a-z0-9]+", " ", txt["try"].lower()).strip()
        if norm and norm in tries:
            bad.append(f"{w}.try: the same as another next test - three different things to try")
        tries.add(norm)
        ev_raw = nt.get("evidence")
        if not isinstance(ev_raw, list) or not 1 <= len(ev_raw) <= EVIDENCE_MAX:
            bad.append(f"{w}.evidence: 1-{EVIDENCE_MAX} items - {{\"post\": <key>}}, {{\"lesson\": <id>}} or {{\"test\": <id>}}")
            ev_raw = ev_raw[:EVIDENCE_MAX] if isinstance(ev_raw, list) else []
        ev = []
        for j, e in enumerate(ev_raw):
            we = f"{w}.evidence[{j}]"
            e = e if isinstance(e, dict) else {}
            if e.get("post"):
                p = every.get(str(e["post"]))
                if not p:
                    bad.append(f"{we}: post {e['post']!r} is not one of the user's posts of the last 120 days (keys in show)")
                    continue
                cites_month = cites_month or p["key"] in month_keys
                ev.append({"type": "post", "id": p["key"], "label": _s(p.get("title") or p["key"], 100),
                           "thumb": p.get("thumb"), "url": p.get("url"), "date": p.get("date")})
            elif e.get("lesson"):
                x = lessons.get(str(e["lesson"]))
                if not x:
                    bad.append(f"{we}: lesson {e['lesson']!r} - one of {', '.join(lessons) or '(none kept)'}")
                    continue
                ev.append({"type": "lesson", "id": x["id"], "label": x["claim"], "status": x["status"]})
            elif e.get("test"):
                t = tests.get(str(e["test"]))
                if not t:
                    bad.append(f"{we}: test {e['test']!r} - one of {', '.join(tests) or '(no tests)'}")
                    continue
                ev.append({"type": "test", "id": t["id"], "label": t["title"], "state": t["state"]})
            else:
                bad.append(f"{we}: one of {{\"post\": <key>}}, {{\"lesson\": <id>}}, {{\"test\": <id>}}")
        out.append({"n": i + 1, "platform": plat, "metric": metric, **txt, "evidence": ev})
    if out and not cites_month:
        bad.append(f"evidence: cite at least one post of {month} - the review is of that month")
    rep = {"made": _now(), "by": "Claude", "month": month, "summary": summary[:SUMMARY_MAX], "next_tests": out,
           "posts": len(D["posts"]), "checked": D["checked"]}
    return rep, bad


def save_review(month: str, draft: dict, src: dict | None = None, today: date | None = None) -> dict:
    """The gate's only way in: ValueError with every problem. A new review replaces the month's last one; the next
    tests already put on the calendar stay picked."""
    with _LOCK:
        rep, bad = check_review(month, draft, src, today)
        if bad:
            raise ValueError("nothing saved - fix these and save again:\n- " + "\n- ".join(bad))
        d = load()
        d["months"].setdefault(rep["month"], {})["review"] = rep
        _write(d)
        return rep


def _metric_words(k: str) -> str:
    """The page's short words for a number (the same keys as Content agency's)."""
    return {"views_48h": I18N.t("views at 48 h"), "views_7d": I18N.t("views at 7 days"),
            "views_28d": I18N.t("views at 28 days"), "hold_3s": I18N.t("still watching at 3 s"),
            "hold_10s": I18N.t("still watching at 10 s"), "end": I18N.t("still watching at the end"),
            "likes_per_1k": I18N.t("likes per 1,000 views"), "comments_per_1k": I18N.t("comments per 1,000 views"),
            "avg_pct": I18N.t("average % viewed")}.get(k, k)


def plan(month: str, n: int, cal_path: Path | None = None) -> dict:
    """Next test n of the month's review as an idea on the content calendar (once): its words as the idea's title,
    the rest in its notes, linked back ("next": "<month>:<n>")."""
    from . import agency as AG
    from . import brand as BR
    month = month_of(month)
    cal_path = cal_path or AG.PATH
    with _LOCK:
        d = load()
        M = d["months"].get(month) or {}
        R = M.get("review")
        if not R:
            raise ValueError(I18N.t("this month has no review yet"))
        try:
            nt = R["next_tests"][int(n) - 1]
        except (TypeError, ValueError, IndexError):
            raise ValueError(I18N.t("no next test {n}", n=str(n)[:4])) from None
        cal = AG.load(cal_path)
        ids = {p.get("id") for p in cal.get("posts") or []}
        if any(x.get("try") == nt["try"] and x.get("calendar") in ids for x in M.get("picked") or []):
            raise ValueError(I18N.t("this next test is on your calendar already"))
        y, mo = month.split("-")
        idea = {"title": nt["try"], "date": "", "time": "", "status": "idea",
                "platforms": [nt["platform"]] if nt["platform"] in BR.PLATFORMS else [],
                "notes": I18N.t("Next test from the monthly review ({month}). The same: {same}. Decided by: {metric}.",
                                month=f"{mo}/{y}", same=nt["same"], metric=_metric_words(nt["metric"])),
                "next": f"{month}:{nt['n']}"}
        before = {p.get("id") for p in cal.get("posts") or []}
        saved = AG.save({**cal, "posts": (cal.get("posts") or []) + [idea]}, cal_path)
        new = next(p for p in saved["posts"] if p["id"] not in before)
        M.setdefault("picked", []).append({"n": nt["n"], "try": nt["try"], "same": nt["same"], "metric": nt["metric"],
                                           "platform": nt["platform"], "calendar": new["id"], "date": _now()})
        d["months"][month] = M
        _write(d)
        return new


# ------------------------------------------------------------------------------------------------ the self-check
def selfcheck() -> dict:
    import copy
    import tempfile
    from . import agency as AG
    global PATH
    lines: list[str] = []
    ok = True

    def check(cond, what):
        nonlocal ok
        ok = ok and bool(cond)
        lines.append(("ok   " if cond else "FAIL ") + what)

    today = date(2026, 11, 2)
    checked = "2026-10-30 12:00:00"

    def mk(i, day, views, plat="tiktok", hold=None, length=30, pillar=None, text=None):
        f = {"length_s": length, "posted_hour": 18, "weekday": "mon", "pillar": pillar, "hook_text": text,
             "hook_cuts": None, "hook_words": None, "first_cut_s": None, "cuts_per_min": None, "words_per_min": None}
        return {"key": f"{plat}:{100 + i}", "platform": plat, "title": f"post {i}", "thumb": None, "date": day,
                "url": f"https://www.tiktok.com/@x/video/{100 + i}", "views": views,
                "m": {"hold_3s": hold, "hold_10s": None, "end": None, "views_7d": None, "likes_per_1k": None,
                      "comments_per_1k": None, "avg_pct": None}, "f": f, "measured": text is not None}

    older = [mk(i, f"2026-09-{10 + i:02d}", 1000 + 100 * i) for i in range(6)]          # usual: 1,250 views
    octo = [mk(10, "2026-10-03", 5000, hold=82.0, length=22, pillar="Tips", text=True),
            mk(11, "2026-10-08", 1250, hold=70.0, length=48, pillar="Tips", text=False),
            mk(12, "2026-10-15", 625, hold=64.0, length=75, pillar="Behind", text=False),
            mk(13, "2026-10-28", 400, length=20)]                                          # 2 days at the check: young
    src = {"soc": {"checked": checked, "history": {}}, "ps": older + octo, "finds": [], "tests": [
        {"id": "t1", "title": "question hook", "platform": "tiktok", "change": "B asks a question", "state": "compared",
         "metric": "views_7d", "kind": "views", "result": "winner", "winner": "B", "values": {"A": 1000, "B": 2000},
         "lead": 2.0, "created": "2026-10-05 10:00", "decided": "", "pick": None, "dates": ["2026-10-05"], "next_test": None}]}
    old_path, old_cal = PATH, AG.PATH
    with tempfile.TemporaryDirectory(prefix="ml_month_") as td:
        PATH = Path(td) / "monthly.json"
        cal_path = Path(td) / "calendar.json"
        AG.PATH = cal_path
        src["cal"] = AG.empty()
        try:
            D = data(None, src, today)
            check(D["month"] == "2026-10", f"no posts in November yet: the review opens on October ({D['month']})")
            s = D["platforms"]["tiktok"]
            check(s["usual_views"] == 1250.0 and s["posts"] == 4 and s["young"] == 1,
                  f"the usual = the median of grown posts ({s['usual_views']}); 4 posts, 1 young")
            p10 = next(p for p in D["posts"] if p["key"] == "tiktok:110")
            check(p10["x_usual"] == 4.0 and D["top_views"][0] == "tiktok:110" and "tiktok:113" not in D["top_views"],
                  f"5,000 views = 4x the usual, ranked first; the young post is not ranked ({D['top_views']})")
            check(D["top_hold"] == ["tiktok:110", "tiktok:111", "tiktok:112"], "held best at 3 s: 82, 70, 64 %")
            gk = {g["key"]: g for g in D["groups"]}
            check("pillar" in gk and gk["pillar"]["rows"][0]["value"] == "Tips" and gk["pillar"]["rows"][0]["median_x"] == 2.5
                  and "length" in gk and "hook_text" in gk, f"groups: pillar (Tips 2.5x), length, text in the first 3 s")
            check([t["id"] for t in D["tests"]] == ["t1"], "the month's test is listed")
            good = {"summary": "One post did 4x the usual; the rest sat near it - a hint, not a pattern.",
                    "next_tests": [
                        {"platform": "tiktok", "try": "Open with the result on screen", "same": "length, pillar, hour",
                         "metric": "hold_3s", "why": "The 82 % post opened with text; the 64 % one did not.",
                         "evidence": [{"post": "tiktok:110"}, {"post": "tiktok:112"}]},
                        {"platform": "tiktok", "try": "A question as the hook", "same": "everything else",
                         "metric": "views_7d", "why": "In t1 the question version led by 2x.", "evidence": [{"test": "t1"}]},
                        {"platform": "tiktok", "try": "Under 30 s", "same": "the topic", "metric": "hold_3s",
                         "why": "The short post held best.", "evidence": [{"post": "tiktok:110"}]}]}
            rep, bad = check_review("2026-10", good, src, today)
            check(not bad and len(rep["next_tests"]) == 3 and rep["next_tests"][0]["evidence"][0]["label"] == "post 10",
                  f"a good review passes ({bad[:2]})")
            b = copy.deepcopy(good)
            b["next_tests"] = b["next_tests"][:2]
            check(any("exactly 3" in x for x in check_review("2026-10", b, src, today)[1]), "two next tests: refused")
            b = copy.deepcopy(good)
            b["next_tests"][0]["why"] = "The text caused the 82 % hold."
            check(any("claims a cause" in x for x in check_review("2026-10", b, src, today)[1]), "a cause claimed: refused")
            b = copy.deepcopy(good)
            b["next_tests"][0]["why"] = "It held 91 % at 3 s."
            check(any("91 %" in x for x in check_review("2026-10", b, src, today)[1]), "a number not in the evidence: refused")
            b["next_tests"][0]["why"] = "It did 82x the usual."
            check(any("82x" in x for x in check_review("2026-10", b, src, today)[1]),
                  "82 is a % of show, not an x against the usual: refused")
            b = copy.deepcopy(good)
            b["next_tests"][1]["evidence"] = [{"test": "t9"}]
            b["next_tests"][2]["evidence"] = [{"post": "tiktok:999"}]
            bb = check_review("2026-10", b, src, today)[1]
            check(any("t9" in x for x in bb) and any("tiktok:999" in x for x in bb), "unknown test / post as evidence: refused")
            b = copy.deepcopy(good)
            for nt in b["next_tests"]:
                nt["evidence"] = [{"post": "tiktok:100"}] if nt["evidence"][0].get("post") else nt["evidence"]
            check(any("cite at least one post of 2026-10" in x for x in check_review("2026-10", b, src, today)[1]),
                  "no post of the month cited: refused")
            b = copy.deepcopy(good)
            b["next_tests"][2]["try"] = "open with the RESULT on screen!"
            b["next_tests"][1]["platform"], b["next_tests"][1]["metric"] = "instagram", "views_7d"
            bb = check_review("2026-10", b, src, today)[1]
            check(any("the same as another" in x for x in bb) and any("platform 'instagram'" in x for x in bb),
                  "the same try twice / a platform the user does not post on: refused")
            check(check_review("2026-12", good, src, today)[1] == ["no posts went up in 2026-12 - nothing to review"],
                  "a month without posts: nothing to review")
            save_review("2026-10", good, src, today)
            new = plan("2026-10", 1, cal_path)
            cal = AG.load(cal_path)
            check(new["status"] == "idea" and new["title"] == "Open with the result on screen" and new.get("next") == "2026-10:1"
                  and new["platforms"] == ["tiktok"] and len(cal["posts"]) == 1, f"next test 1 is an idea on the calendar ({new['id']})")
            try:
                plan("2026-10", 1, cal_path)
                check(False, "the same next test twice: refused")
            except ValueError:
                check(True, "the same next test twice: refused")
            src["cal"] = AG.load(cal_path)
            V = view("2026-10", src, today)
            check(V["picked"][0]["status"] == "idea" and V["review"]["summary"].startswith("One post"),
                  "the page: the review and the pick with its calendar status")
            V2 = view("2026-11", {**src, "ps": src["ps"] + [mk(20, "2026-11-01", 900)]}, today)
            check(V2["before"] and V2["before"][0]["calendar"] == new["id"], "next month shows last month's picks")
            save_review("2026-10", good, src, today)
            check(load()["months"]["2026-10"]["picked"][0]["calendar"] == new["id"], "a new review keeps the picks")
            txt = show_text("2026-10", src, today)
            check("tiktok:110" in txt and "4x usual" in txt and "(young)" in txt and "t1 [compared]" in txt,
                  "what Claude reads: posts, x usual, young, tests")
            check(shift("2026-01", -1) == "2025-12" and shift("2026-12", 1) == "2027-01", "months roll over the year")
        finally:
            PATH, AG.PATH = old_path, old_cal
    return {"passed": ok, "lines": lines}
