"""Content agency (0.6.0, steps 12-19 in docs\\plans.md; its own sidebar row - the user's pick, 2026-10-25): the plan
around the videos. Step 12, the content calendar (the user: "i kinda want the content calendar first"): one file on
this PC, `knowledge\\local\\calendar.json`, never shared.

calendar.json:
  "rhythm": {"days": ["mon", "wed", "fri"], "time": "18:00"}      the weekly rhythm the user aims for (empty = none)
  "posts":  [{"id": "c12", "title": "Behind the scenes of the 4AM video", "date": "2026-10-28" | "" (an idea),
              "time": "18:00" | "", "platforms": ["tiktok", "instagram"], "status": idea|scripted|filmed|edited|ready|posted,
              "project": "<a MotionLab video's folder>" | "", "notes": "...", "sound": "the trending sound to add in the
              app when posting" (never in the render), "pillar": "one of My Brand's content pillars" | "",
              "links": {"tiktok": "https://..."} (where it went up),
              "ab": "B won - the red thumbnail, 54 %" (YouTube's Test & compare, step 12),
              "checks": {"youtube:package": true, ...} (the posting checklist ticked, step 15)}]
  "when":   {"youtube": ["tue 18:00", "thu 19:00"], ...}   (step 16: the user's own best times, typed from YouTube
             Studio's "When your viewers are on YouTube" / Instagram's "Most active times")
  "updated": "2026-10-25 23:50:12"
Every save is checked (`clean`): unknown keys dropped, dates YYYY-MM-DD, times HH:MM, platforms = My Brand's
(brand.PLATFORMS), a status of STATUSES, a project = a folder of projects\\ with that name, links on their platform.
`ics()` = the dated posts as an iCalendar file (Windows Calendar, Outlook, Google: a reminder 1 h before).
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path

from . import i18n as I18N
from .util import LAB

PATH = LAB / "knowledge" / "local" / "calendar.json"
STATUSES = ("idea", "scripted", "filmed", "edited", "ready", "posted")
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
MAX = {"title": 120, "notes": 1000, "sound": 200, "posts": 2000, "url": 300}
POST_HOSTS = {"youtube": r"(?:www\.|m\.)?youtube\.com|youtu\.be", "tiktok": r"(?:www\.|vm\.|m\.)?tiktok\.com",
              "instagram": r"(?:www\.)?instagram\.com", "x": r"(?:www\.)?(?:x|twitter)\.com",
              "linkedin": r"(?:[a-z]{2,3}\.)?linkedin\.com", "facebook": r"(?:www\.|m\.)?facebook\.com|fb\.watch",
              "threads": r"(?:www\.)?threads\.(?:net|com)", "twitch": r"(?:www\.|m\.|clips\.)?twitch\.tv"}  # a post's link


def empty() -> dict:
    return {"rhythm": {"days": [], "time": ""}, "posts": [], "when": {}, "updated": None}


def _s(v, n: int) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def _date(v) -> str:
    v = str(v or "").strip()
    try:
        return date.fromisoformat(v).isoformat() if v else ""
    except ValueError:
        raise ValueError(I18N.t("not a date: {value}", value=v[:20])) from None


def _time(v) -> str:
    v = str(v or "").strip()
    if v and not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", v):
        raise ValueError(I18N.t("not a time (HH:MM): {value}", value=v[:20]))
    return v


def clean(body: dict) -> dict:
    """The page's calendar -> a valid calendar.json (ValueError on a bad date, time or link)."""
    from . import brand as BR
    b, out = body or {}, empty()
    r = b.get("rhythm") or {}
    out["rhythm"] = {"days": [d for d in DAYS if d in (r.get("days") or [])], "time": _time(r.get("time"))}
    when = {}                                                   # step 16: the user's best times per platform
    for plat, ts in (b.get("when") or {}).items() if isinstance(b.get("when"), dict) else []:
        if plat in BR.PLATFORMS and isinstance(ts, list):
            ok = []
            for x in ts[:8]:
                m = re.fullmatch(r"(mon|tue|wed|thu|fri|sat|sun|any) (\d{2}:\d{2})", str(x).strip())
                if m and _time(m[2]) and m[0] not in ok:
                    ok.append(m[0])
            if ok:
                when[plat] = ok
    out["when"] = when
    posts, ids = [], set()
    for p in (b.get("posts") or [])[:MAX["posts"]]:
        p = p or {}
        title = _s(p.get("title"), MAX["title"])
        if not title:
            continue                                             # a post needs at least a title
        pid = str(p.get("id") or "")
        if not re.fullmatch(r"c\d{1,6}", pid) or pid in ids:
            pid = next(f"c{i}" for i in range(1, 10 ** 6) if f"c{i}" not in ids)
        ids.add(pid)
        proj = _s(p.get("project"), 160)
        if proj and (re.search(r"[\\/:]|\.\.", proj) or not (LAB / "projects" / proj).is_dir()):
            proj = ""                                            # a video that is gone (or not a folder name): none
        links = {}
        for plat, u in (p.get("links") or {}).items() if isinstance(p.get("links"), dict) else []:
            u = _s(u, MAX["url"])
            if plat in BR.PLATFORMS and u:
                if not re.match(r"https?://", u, re.I):
                    u = "https://" + u
                if not re.match(r"https?://(?:" + POST_HOSTS[plat] + r")(?:/|$)", u, re.I):
                    raise ValueError(I18N.t("not a {platform} address: {url}", platform=BR.PLATFORMS[plat], url=u))
                links[plat] = u
        posts.append({"id": pid, "title": title, "date": _date(p.get("date")), "time": _time(p.get("time")),
                      "platforms": [x for x in BR.PLATFORMS if x in (p.get("platforms") or [])],
                      "status": p.get("status") if p.get("status") in STATUSES else "idea",
                      "project": proj, "notes": _s(p.get("notes"), MAX["notes"]), "sound": _s(p.get("sound"), MAX["sound"]),
                      "pillar": _s(p.get("pillar"), 60), "links": links, "ab": _s(p.get("ab"), 120),
                      "checks": {k: True for k, v in (p.get("checks") or {}).items()
                                 if v is True and re.fullmatch(r"[a-z]{1,12}:[a-z_]{1,20}", str(k))} if isinstance(
                                     p.get("checks"), dict) else {}})
    out["posts"] = posts
    return out


def load(path: Path = PATH) -> dict:
    try:
        return {**empty(), **json.loads(Path(path).read_text(encoding="utf-8"))}
    except (OSError, ValueError):
        return empty()


def save(body: dict, path: Path = PATH) -> dict:
    """Check and write the calendar (a temp file + rename); returns what was saved."""
    data = clean(body)
    data["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, p)
    return data


def _ics_text(s: str) -> str:
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def ics(cal: dict | None = None, now: datetime | None = None) -> str:
    """The dated posts as an iCalendar file: a timed post = a 30-min event with a reminder 1 h before, a post without
    a time = an all-day event; the title says the platforms, the description the status, the video and the notes.
    Local times (no time zone: the calendar app places them in its own)."""
    from . import brand as BR
    cal = cal if cal is not None else load()
    stamp = (now or datetime.now()).strftime("%Y%m%dT%H%M%S")
    L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//MotionLab//Content calendar//EN", "CALSCALE:GREGORIAN",
         "X-WR-CALNAME:MotionLab content calendar"]
    for p in cal.get("posts") or []:
        if not p.get("date"):
            continue
        d = date.fromisoformat(p["date"])
        plats = ", ".join(BR.PLATFORMS.get(x, x) for x in p.get("platforms") or [])
        desc = "\n".join(x for x in (f"Status: {p.get('status', 'idea')}", f"Video: {p['project']}" if p.get("project") else "",
                                     f"Sound to add in the app: {p['sound']}" if p.get("sound") else "", p.get("notes") or "") if x)
        L += ["BEGIN:VEVENT", f"UID:{p['id']}-{p['date']}@motionlab", f"DTSTAMP:{stamp}",
              f"SUMMARY:{_ics_text(('Post: ' + p['title']) + (f' ({plats})' if plats else ''))}"]
        if p.get("time"):
            start = datetime.combine(d, datetime.strptime(p["time"], "%H:%M").time())
            L += [f"DTSTART:{start:%Y%m%dT%H%M%S}", f"DTEND:{start + timedelta(minutes=30):%Y%m%dT%H%M%S}",
                  "BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:Post it", "TRIGGER:-PT1H", "END:VALARM"]
        else:
            L += [f"DTSTART;VALUE=DATE:{d:%Y%m%d}", f"DTEND;VALUE=DATE:{d + timedelta(days=1):%Y%m%d}"]
        if desc:
            L.append(f"DESCRIPTION:{_ics_text(desc)}")
        L.append("END:VEVENT")
    L.append("END:VCALENDAR")
    return "\r\n".join(L) + "\r\n"


def selfcheck() -> dict:
    """Known answers for clean / save / load / ics, in a temp folder. {passed, seconds, lines}."""
    import tempfile
    t0, lines, ok = time.time(), [], True

    def case(name, cond):
        nonlocal ok
        ok = ok and bool(cond)
        lines.append(f"{'PASS' if cond else 'FAIL'} {name}")

    c = clean({"rhythm": {"days": ["fri", "mon", "funday"], "time": "18:00"},
               "posts": [{"title": "  Behind   the scenes ", "date": "2026-10-28", "time": "18:30", "platforms": ["tiktok", "myspace", "instagram"],
                          "pillar": " Behind the scenes ",
                          "status": "edited", "project": "no such video zz", "links": {"tiktok": "tiktok.com/@rift/video/1",
                                                                                         "youtube": "https://youtu.be/abc"}},
                         {"title": "An idea"}, {"title": ""}, {"id": "c1", "title": "Same id", "status": "viral"}],
               "secret": 1})
    case("clean: the rhythm's days in week order, unknown ones out", c["rhythm"] == {"days": ["mon", "fri"], "time": "18:00"})
    case("clean: a post needs a title; ids unique; unknown platforms / statuses / videos dropped; a link gets https",
         [(p["id"], p["title"], p["status"]) for p in c["posts"]] == [("c1", "Behind the scenes", "edited"), ("c2", "An idea", "idea"),
                                                                       ("c3", "Same id", "idea")]
         and c["posts"][0]["platforms"] == ["tiktok", "instagram"] and c["posts"][0]["project"] == ""
         and c["posts"][0]["pillar"] == "Behind the scenes"
         and c["posts"][0]["links"] == {"tiktok": "https://tiktok.com/@rift/video/1", "youtube": "https://youtu.be/abc"}
         and "secret" not in c)
    for bad, what in (({"posts": [{"title": "x", "date": "2026-13-40"}]}, "a date"), ({"posts": [{"title": "x", "time": "25:00"}]}, "a time"),
                      ({"posts": [{"title": "x", "links": {"youtube": "https://www.tiktok.com/@a"}}]}, "a link on another platform")):
        try:
            clean(bad)
            refused = False
        except ValueError:
            refused = True
        case(f"clean: not {what} is refused", refused)
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "calendar.json"
        s = save({"posts": [{"title": "Reel", "date": "2026-10-30"}]}, p)
        case("save + load: the same calendar back, with its date", load(p) == s and s["updated"])
        case("load: no file = an empty calendar", load(Path(td) / "none.json") == empty())
    txt = ics(c, datetime(2026, 10, 25, 12, 0, 0))
    case("ics: a timed post = a 30-min event with a reminder 1 h before, the platforms in its title; ideas left out",
         "DTSTART:20261028T183000" in txt and "DTEND:20261028T190000" in txt and "TRIGGER:-PT1H" in txt
         and "SUMMARY:Post: Behind the scenes (TikTok\\, Instagram)" in txt and "An idea" not in txt
         and txt.count("BEGIN:VEVENT") == 1 and txt.endswith("END:VCALENDAR\r\n"))
    return {"passed": ok, "seconds": round(time.time() - t0, 3), "lines": lines}
