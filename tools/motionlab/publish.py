"""Publish (0.4.3): the ready-to-post folder of a finished video, `projects\\<p>\\build\\publish\\`.

This module writes the words: the title, the description with YouTube chapters, the hashtags. The thumbnails come
from tools\\thumbnail.py (another module); both share `package.json` and each one updates only its own keys:
- thumbnail.py owns "candidates" and "thumbnails";
- this module owns "title", "titles", "description", "chapters", "hashtags" (MY_KEYS).
Every write reads the file, changes only those keys, and replaces it atomically (a temp file + rename, retried when
another process holds it for a moment).

package.json, this module's part:
  "title":       "the final title"                                   (a plain string)
  "titles":      [{"text", "pattern", "chars", "from"}]               the candidates (from a title record), "chosen": true on the final one
  "description": {"text", "body", "chars", "file": "description.txt", "checks": [{part, rule, status, detail}], "updated"}
                 text = description.txt as posted (body + chapters + hashtags); checks = title / description / chapters /
                 hashtags against the rules below, status PASS / WARN / FAIL
  "chapters":    {"fps", "frames", "from", "items": [{"f", "tc", "s", "yt", "name"}]}
                 f = the frame in the final video (0-based), tc = its HH:MM:SS:FF, s = seconds, yt = what YouTube
                 reads ("1:05": the whole second the frame falls in)
  "hashtags":    {"items": ["#a", ...], "shown": [the first 3], "line": "#a #b"}

Platform rules (checked on the web on 2026-10-15; they change - check again when they look wrong):
- YouTube chapters (support.google.com/youtube/answer/9884579): the first timestamp is 0:00, at least three in
  ascending order, each chapter at least 10 s long. Timestamps in the description override automatic chapters.
- YouTube hashtags (answer/6390658): up to three of the description's hashtags show by the title; more than 60
  hashtags on a video = all of them are ignored.
- YouTube title / description (answer/57404): a title up to 100 characters, a description up to 5,000, no invalid
  characters (Studio refuses < and >).
- Rule of thumb, not a platform rule: a phone shows about 50-60 characters of a title before it is cut;
  3-5 relevant hashtags.
"""
from __future__ import annotations

import datetime as _dt
import json
import math
import os
import re
import threading
import time
from pathlib import Path

from .timecode import frame_to_tc
from .util import LAB, read_json

PROJECTS = LAB / "projects"
MY_KEYS = ("title", "titles", "description", "chapters", "hashtags")
OTHER_KEYS = ("candidates", "thumbnails")              # thumbnail.py's - read, never written here
CHECKED = "2026-10-15"                                  # when the platform rules above were checked
CHAPTER_MIN_S = 10
CHAPTERS_MIN = 3
HASHTAGS_IGNORED_OVER = 60
HASHTAGS_SHOWN = 3
TITLE_MAX = 100
TITLE_PHONE = 60                                        # rule of thumb: a phone cuts a title after ~50-60 characters
DESCRIPTION_MAX = 5000
DECOR = ("firework", "streaks", "strip")                # plan layers drawn over the picture, not a picture of their own
_LOCK = threading.RLock()


# ------------------------------------------------------------------------------------------------ the project
def project_dir(project: str | Path) -> Path:
    """A project name (or a path like projects\\test_4am) -> projects\\<name>, which must exist."""
    name = Path(str(project).replace("\\", "/").rstrip("/")).name
    # the names the app gives a video's folder (data.safe_name): Film it names it after the script, so spaces and
    # apostrophes are normal ("What's new in MotionLab 0.4.3") - only separators and ".." are refused
    if not name or not re.fullmatch(r"[\w.\- \[\]()&'+,]+", name) or ".." in name:
        raise ValueError(f"not a video folder name: {project!r}")
    d = PROJECTS / name
    if not d.is_dir():
        raise ValueError(f"no video called {name!r} in projects")
    return d


def publish_dir(project: str | Path) -> Path:
    d = (project_dir(project) / "build" / "publish").resolve()
    if PROJECTS.resolve() not in d.parents or d.parent.name != "build":
        raise ValueError("publish writes only into projects\\<name>\\build\\publish")
    return d


def latest_plan(project: str | Path) -> Path | None:
    """The newest edit plan build\\plan_vN.json (the version the final video is)."""
    b = project_dir(project) / "build"
    plans = [(int(m[1]), p) for p in b.glob("plan_v*.json") if (m := re.fullmatch(r"plan_v(\d+)\.json", p.name))]
    return max(plans)[1] if plans else None


# ------------------------------------------------------------------------------------------------ time on YouTube
def yt_seconds(f: int, fps: float) -> int:
    """The whole second a frame falls in (YouTube's timestamps have no frames)."""
    return int(math.floor(f / fps + 1e-9))


def yt_time(seconds: float, total_s: float = 0) -> str:
    """0:00 / 1:05 / 1:02:03 - with hours on every line when the video is an hour or longer."""
    s = int(math.floor(seconds + 1e-9))
    h, m, sec = s // 3600, (s // 60) % 60, s % 60
    if h or total_s >= 3600:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"


def _item(f: int, fps: float, name: str = "", total_s: float = 0) -> dict:
    return {"f": int(f), "tc": frame_to_tc(int(f), fps), "s": round(f / fps, 3),
            "yt": yt_time(yt_seconds(int(f), fps), total_s), "name": name}


# ------------------------------------------------------------------------------------------------ chapter points
def _curve(spec, named: dict, f: int) -> float:
    """A plan's animated value at frame f (compose.Curve's formats; eases read as linear - enough for an area)."""
    if isinstance(spec, str) and spec.startswith("@"):
        spec = named.get(spec[1:])
    if spec is None:
        return 0.0
    if isinstance(spec, (int, float)):
        return float(spec)
    sc, off = float(spec.get("scale", 1.0)), float(spec.get("offset", 0.0))
    if "values" in spec and spec["values"]:
        vals = spec["values"]
        v = vals[min(max(int(f) - int(spec.get("start", 0)), 0), len(vals) - 1)]
    elif spec.get("keys"):
        ks = sorted(spec["keys"], key=lambda k: k[0])
        if f <= ks[0][0]:
            v = ks[0][1]
        elif f >= ks[-1][0]:
            v = ks[-1][1]
        else:
            a, b = next((ks[i], ks[i + 1]) for i in range(len(ks) - 1) if ks[i][0] <= f < ks[i + 1][0])
            hold = len(a) > 2 and a[2] == "hold"
            v = a[1] if hold else a[1] + (b[1] - a[1]) * (f - a[0]) / max(1e-9, b[0] - a[0])
    else:
        return 0.0
    return float(v) * sc + off


def _area(layer: dict, w: int, h: int, named: dict | None = None, f: int = 0) -> float:
    """The share of the canvas a layer covers at frame f (its rect moved by dx / dy, clipped to the canvas; no
    rect = the whole frame)."""
    r = layer.get("rect")
    if not r:
        return 1.0
    dx = _curve(layer.get("dx"), named or {}, f) if layer.get("dx") is not None else 0.0
    dy = _curve(layer.get("dy"), named or {}, f) if layer.get("dy") is not None else 0.0
    x0, y0 = float(r[0]) + dx, float(r[1]) + dy
    x1, y1 = x0 + float(r[2]), y0 + float(r[3])
    x0, y0, x1, y1 = max(0.0, x0), max(0.0, y0), min(float(w), x1), min(float(h), y1)
    return max(0.0, x1 - x0) * max(0.0, y1 - y0) / float(w * h)


def plan_points(plan: dict, min_strength: float = 0.6) -> list[dict]:
    """Candidate chapter points from an edit plan: the frames where the picture changes - most of what is on screen
    (layers of at least 1 s, clipped to the canvas) is new there. strength = the share of that picture that is new
    (1 = a clean change). A change right after a flash (layers of 1-3 frames) starts at the flash. Frame 0 is always
    one."""
    fps, n = float(plan.get("fps") or 30), int(plan.get("frames") or 0)
    w, h = int(plan.get("width") or 1920), int(plan.get("height") or 1080)
    named = plan.get("curves") or {}
    layers = [dict(x) for x in plan.get("layers") or [] if isinstance(x.get("start"), (int, float))]
    for x in layers:
        x["_end"] = int(x.get("end", x["start"]))
        x["_len"] = x["_end"] - int(x["start"]) + 1
    n = n or max((x["_end"] + 1 for x in layers), default=0)

    def on(f, pool):
        return [x for x in pool if int(x["start"]) <= f <= x["_end"]]

    def seen(f):                                        # the picture at f: layers of >= 1 s, > 1 % of it (decorations
        return {id(x): a for x in on(f, layers)         # on top - fireworks, streaks, border strips - left out)
                if x["_len"] >= fps and x.get("type") not in DECOR and (a := _area(x, w, h, named, f)) > 0.01}

    first = [x for x in on(0, layers) if id(x) in seen(0)]
    out = [{"f": 0, "strength": 1.0, "starts": [x.get("id") or x.get("type") for x in first][:6],
            "text": next((x.get("text") for x in on(0, layers) if x.get("text")), "")}]
    for f in sorted({int(x["start"]) for x in layers
                     if x["_len"] >= fps and x.get("type") not in DECOR and int(x["start"]) > 0}):
        now, before = seen(f), seen(f - 1)
        total = sum(now.values())
        if total <= 0:
            continue
        kept = sum(a for k, a in now.items() if k in before)
        st = round(max(0.0, 1 - kept / total), 2)
        if st < min_strength:
            continue
        g = f                                            # back over a flash right before the change
        while g > 0 and f - g < 6:
            prev = on(g - 1, layers)
            if prev and all(x["_len"] <= 3 for x in prev):
                g -= 1
            else:
                break
        new = [x for x in on(f, layers) if id(x) in now and id(x) not in before]
        out.append({"f": g, "strength": st, "starts": [x.get("id") or x.get("type") for x in new][:6],
                    "text": next((x.get("text") for x in on(f, layers) if x.get("text")), "")})
    out = sorted({p["f"]: p for p in out}.values(), key=lambda p: p["f"])
    for i, p in enumerate(out):                         # how long until the next change (bigger = a better chapter)
        p["until_next_s"] = round(((out[i + 1]["f"] if i + 1 < len(out) else n) - p["f"]) / fps, 2)
    return out


_STOP = set("""the and that this with have from your just what when then they there were about would could into
like really going gonna know because very also been them than more some only over here want even make made back
porque pero como para esto este esta todo cuando donde está estoy tengo tiene vamos hacer entonces bueno pues
también muy más nada algo""".split())


def transcript_points(lines: list[dict], fps: float, pause_s: float = 1.2, window_s: float = 20.0) -> list[dict]:
    """Candidate chapter points from what the video says (speech.py's lines: t0 / t1 in seconds): a pause before a
    line, and a topic shift (the content words of the next window_s seconds share little with the last window_s).
    strength = half the pause (full at 3 s), half the shift."""
    lines = [x for x in lines or [] if x.get("text") and x.get("t0") is not None]
    words = [(float(x["t0"]), {w for w in re.findall(r"[^\W\d_]{4,}", str(x["text"]).lower()) if w not in _STOP})
             for x in lines]
    out = [{"f": 0, "strength": 1.0, "text": lines[0]["text"][:80] if lines else "", "pause_s": 0, "shift": 0}]
    for i in range(1, len(lines)):
        t = float(lines[i]["t0"])
        gap = t - float(lines[i - 1].get("t1") or lines[i - 1]["t0"])
        before = set().union(*[w for (tt, w) in words if t - window_s <= tt < t] or [set()])
        after = set().union(*[w for (tt, w) in words if t <= tt < t + window_s] or [set()])
        shift = 1 - len(before & after) / len(before | after) if before and after else 0.0
        st = round(0.5 * min(1.0, gap / 3.0) + 0.5 * shift, 2)
        if gap >= pause_s or shift >= 0.9:
            out.append({"f": int(round(t * fps)), "strength": st, "text": str(lines[i]["text"])[:80],
                        "pause_s": round(gap, 2), "shift": round(shift, 2)})
    return out


def suggest(points: list[dict], fps: float, frames: int, most: int | None = None) -> list[int]:
    """A set of points that keeps YouTube's rules: 0 first, every chapter >= 10 s on the whole seconds YouTube
    reads (the last one too, up to the end); best first = strength x how long the new picture lasts (up to 30 s),
    so a clean change into a long section beats a burst of quick cuts; at most `most` (default: one per ~20 s, at
    least 3)."""
    total = frames / fps if frames else 0
    most = most or (max(CHAPTERS_MIN, int(total // 20)) if total else 8)
    picked = [0]
    for p in sorted(points, key=lambda p: (-p["strength"] * min(30.0, p.get("until_next_s") or 10.0), p["f"])):
        s = yt_seconds(p["f"], fps)
        if p["f"] == 0 or len(picked) >= most:
            continue
        if total and math.floor(total) - s < CHAPTER_MIN_S:
            continue
        if all(abs(s - yt_seconds(q, fps)) >= CHAPTER_MIN_S for q in picked):
            picked.append(p["f"])
    return sorted(picked)


def _speech_file(project: str | Path) -> tuple[Path | None, str]:
    """build\\speech\\: a transcript of the final video (a render's name) first, else any (with a warning)."""
    d = project_dir(project)
    files = sorted((d / "build" / "speech").glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    files = [p for p in files if p.name != "bench.json"]
    renders = re.compile(rf"{re.escape(d.name)}(_resolve)?_v\d+\.")
    for p in files:
        if renders.match(p.name):
            return p, ""
    if files:
        return files[0], (f"{files[0].name} is the words of a clip, not of the final video - its times may not "
                          "match the edit; transcribe the final render (speech.py transcribe <render>) for exact ones")
    return None, ""


def chapter_points(project: str | Path, source: str = "plan", speech: str | Path | None = None) -> dict:
    """What `publish.py chapters` prints and the app shows: {from, fps, frames, points: [{f, tc, s, yt, strength,
    hint}], suggested: [f, ...], warnings}. source = plan (the newest edit plan's picture changes) or transcript
    (pauses and topic shifts in build\\speech\\)."""
    warn = []
    plan_p = latest_plan(project)
    plan = read_json(plan_p) if plan_p else {}
    fps, frames = float(plan.get("fps") or 0), int(plan.get("frames") or 0)
    if source == "plan":
        if not plan_p:
            raise ValueError("no edit plan yet (build\\plan_vN.json) - make the edit first, or use --from transcript")
        pts, src = plan_points(plan), plan_p.name
        for p in pts:
            p["hint"] = ("starts: " + ", ".join(str(x) for x in p.pop("starts") if x)) + (
                f" | text on screen: {p['text']}" if p.get("text") else "")
            p.pop("text", None)
    elif source == "transcript":
        sp, w = (Path(speech), "") if speech else _speech_file(project)
        if not sp or not sp.exists():
            raise ValueError("no words of this video yet (build\\speech\\) - speech.py transcribe <the final render>")
        if w:
            warn.append(w)
        T = read_json(sp)
        if not fps:
            fps = 30.0
            warn.append("no edit plan: frames counted at 30 fps")
        if not frames:
            frames = int(round(float(T.get("audio_s") or 0) * fps))
        pts, src = transcript_points(T.get("lines") or [], fps), sp.name
        for p in pts:
            p["hint"] = f"says: {p.pop('text')}" + (f" | pause {p['pause_s']:g} s before" if p.get("pause_s") else "")
    else:
        raise ValueError("--from plan or --from transcript")
    total = frames / fps if frames else 0
    for i, p in enumerate(pts):
        p.update({k: v for k, v in _item(p["f"], fps, total_s=total).items() if k != "name"})
        p.setdefault("until_next_s", round(((pts[i + 1]["f"] if i + 1 < len(pts) else frames) - p["f"]) / fps, 2))
    return {"from": src, "fps": fps, "frames": frames, "seconds": round(total, 2), "points": pts,
            "suggested": suggest(pts, fps, frames), "warnings": warn}


# ------------------------------------------------------------------------------------------------ the checks
def _c(part, rule, status, detail):
    return {"part": part, "rule": rule, "status": status, "detail": detail}


def parse_chapters(text: str) -> list[tuple[int, str]]:
    """"f|name;f|name" (f = a frame number, "f480" works too) -> [(480, "name")]."""
    out = []
    for part in [x for x in re.split(r"[;\n]", str(text or "")) if x.strip()]:
        if "|" not in part:
            raise ValueError(f"a chapter is 'frame|name' (got {part.strip()!r})")
        f, name = part.split("|", 1)
        f = f.strip().lower().lstrip("f")
        if not f.isdigit():
            raise ValueError(f"a chapter's frame is a number like 480 or f480 (got {part.strip()!r})")
        out.append((int(f), " ".join(name.split())))
    return out


def check_chapters(chs: list[tuple[int, str]], fps: float, frames: int = 0) -> list[dict]:
    """YouTube's chapter rules on the whole seconds it reads: the first at 0:00, at least 3, ascending, each >= 10 s
    (the last up to the end when the length is known), every one named."""
    if not chs:
        return []
    out, secs = [], [yt_seconds(f, fps) for f, _ in chs]
    out.append(_c("chapters", "the first at 0:00", "PASS" if secs[0] == 0 else "FAIL",
                  "starts at 0:00" if secs[0] == 0 else f"the first is at {yt_time(secs[0])} - YouTube needs 0:00"))
    out.append(_c("chapters", f"at least {CHAPTERS_MIN}", "PASS" if len(chs) >= CHAPTERS_MIN else "FAIL",
                  f"{len(chs)} chapter{'s' if len(chs) != 1 else ''}"))
    if any(b <= a for a, b in zip([f for f, _ in chs], [f for f, _ in chs][1:])):
        out.append(_c("chapters", "in order", "FAIL", "the frames must go up, one chapter after another"))
    total = int(math.floor(frames / fps + 1e-9)) if frames else None
    ends = secs[1:] + ([total] if total is not None else [])
    short = [(chs[i][1] or f"#{i + 1}", e - secs[i]) for i, e in enumerate(ends) if e - secs[i] < CHAPTER_MIN_S]
    out.append(_c("chapters", f"each at least {CHAPTER_MIN_S} s", "FAIL" if short else "PASS",
                  "; ".join(f"'{n}' is {d} s" for n, d in short) if short else
                  f"the shortest is {min(e - s for s, e in zip(secs, ends))} s" if ends else "-"))
    if frames and chs[-1][0] >= frames:
        out.append(_c("chapters", "inside the video", "FAIL", f"f{chs[-1][0]} is past the end (f{frames - 1})"))
    unnamed = [i + 1 for i, (_, n) in enumerate(chs) if not n]
    if unnamed:
        out.append(_c("chapters", "every chapter named", "FAIL", f"chapter {', '.join(map(str, unnamed))} has no name"))
    return out


_TAG_OK = re.compile(r"#[^\W_][\w]*", re.U)


def parse_hashtags(text: str) -> list[str]:
    """"#a #b c" -> ["#a", "#b", "#c"] (one per word, # added, duplicates dropped - case does not matter)."""
    out, seen = [], set()
    for w in str(text or "").replace(",", " ").split():
        t = "#" + w.lstrip("#")
        if len(t) > 1 and t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out


def check_hashtags(tags: list[str], title: str = "") -> list[dict]:
    out = []
    if not tags:
        return [_c("hashtags", "some hashtags", "WARN", "none - 3-5 relevant ones help people find it (rule of thumb)")]
    n = len(tags)
    out.append(_c("hashtags", f"at most {HASHTAGS_IGNORED_OVER} (YouTube ignores all of them above)",
                  "FAIL" if n > HASHTAGS_IGNORED_OVER else "PASS", f"{n} hashtag{'s' if n != 1 else ''}"))
    if 5 < n <= HASHTAGS_IGNORED_OVER:
        out.append(_c("hashtags", "3-5 relevant ones (rule of thumb)", "WARN", f"{n} - more dilutes them"))
    broken = [t for t in tags if not _TAG_OK.fullmatch(t)]
    if broken:
        out.append(_c("hashtags", "letters, digits and _ only", "WARN",
                      ", ".join(broken) + " - a hashtag stops at the first other character"))
    shown = tags[:HASHTAGS_SHOWN]
    out.append(_c("hashtags", f"the {HASHTAGS_SHOWN} shown by the title", "PASS",
                  " ".join(shown) + " (the first ones in the description; put the best first)"))
    if "#" in (title or ""):
        out.append(_c("hashtags", "no hashtags in the title (rule of thumb)", "WARN",
                      "they take characters a phone shows of the title"))
    return out


def check_title(title: str) -> list[dict]:
    t = " ".join(str(title or "").split())
    out = [_c("title", f"at most {TITLE_MAX} characters", "PASS" if 0 < len(t) <= TITLE_MAX else "FAIL",
              f"{len(t)} characters" if t else "no title")]
    if t and len(t) > TITLE_PHONE:
        out.append(_c("title", f"about {TITLE_PHONE} characters on a phone (rule of thumb)", "WARN",
                      f"{len(t)} - a phone may cut it after “{t[:TITLE_PHONE].rstrip()}…”: the key words go first"))
    elif t:
        out.append(_c("title", f"about {TITLE_PHONE} characters on a phone (rule of thumb)", "PASS", f"{len(t)} characters"))
    if re.search(r"[<>]", t):
        out.append(_c("title", "no < or >", "FAIL", "YouTube Studio refuses < and > in a title"))
    return out


def check_description(text: str) -> list[dict]:
    out = [_c("description", f"at most {DESCRIPTION_MAX} characters", "PASS" if len(text) <= DESCRIPTION_MAX else "FAIL",
              f"{len(text)} characters")]
    if re.search(r"[<>]", text):
        out.append(_c("description", "no < or >", "FAIL", "YouTube Studio refuses < and > in a description"))
    return out


def description_text(body: str, chapters: list[dict], hashtags: list[str]) -> str:
    """description.txt: the user's words, then the chapters (YouTube's `0:00 Name`, one a line), then the hashtags."""
    parts = [str(body or "").strip()]
    if chapters:
        parts.append("\n".join(f"{c['yt']} {c['name']}" for c in chapters))
    if hashtags:
        parts.append(" ".join(hashtags))
    return "\n\n".join(p for p in parts if p) + "\n"


# ------------------------------------------------------------------------------------------------ package.json
def read_package(folder: Path) -> dict:
    p = Path(folder) / "package.json"
    for _ in range(5):
        try:
            return read_json(p) if p.exists() else {}
        except ValueError:                              # caught mid-write by the other tool: try again
            time.sleep(0.1)
        except OSError:
            time.sleep(0.1)
    return read_json(p)


def update_package(folder: Path, changes: dict) -> dict:
    """Read package.json, set only MY_KEYS from changes, write it back atomically (temp + rename); every other key
    (thumbnail.py's "candidates" / "thumbnails", anything newer) stays as it was."""
    bad = [k for k in changes if k not in MY_KEYS]
    if bad:
        raise ValueError(f"publish owns only {', '.join(MY_KEYS)} in package.json (not {', '.join(bad)})")
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / "package.json"
    with _LOCK:
        for attempt in range(20):
            pkg = read_package(folder)
            pkg.update(changes)
            tmp = folder / f"package.json.{os.getpid()}.{threading.get_ident()}.tmp"
            tmp.write_text(json.dumps(pkg, indent=1, ensure_ascii=False), encoding="utf-8")
            try:
                os.replace(tmp, p)
                return pkg
            except PermissionError:                     # the other tool has it open for a moment (Windows)
                tmp.unlink(missing_ok=True)
                time.sleep(0.05 * (attempt + 1))
        raise OSError(f"could not replace {p} (another program keeps it open)")


def _write_text(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


# ------------------------------------------------------------------------------------------------ write / show
def write(project: str | Path, title: str, chapters: str | list | None = None, hashtags: str | list | None = None,
          body: str | None = None, titles_from: str = "") -> dict:
    """The words of the package -> build\\publish\\title.txt, description.txt, hashtags.txt + package.json.
    chapters = "f|name;..." or [(f, name)]; hashtags = "#a #b" or a list; body = the description's own words
    (None = keep the last ones); titles_from = a title record (title-NNN) whose titles go into "titles".
    What is left out (None) keeps its last value in package.json. Nothing is written when a check FAILs:
    {ok, checks, package, files}."""
    out_dir = publish_dir(project)
    pkg = read_package(out_dir)
    plan_p = latest_plan(project)
    plan = read_json(plan_p) if plan_p else {}
    old_ch = pkg.get("chapters") or {}
    fps = float(plan.get("fps") or old_ch.get("fps") or 30)
    frames = int(plan.get("frames") or old_ch.get("frames") or 0)
    total = frames / fps if frames else 0
    title = " ".join(str(title or "").split())

    if chapters is None:
        chs = [(c["f"], c["name"]) for c in old_ch.get("items") or []]
    else:
        chs = parse_chapters(chapters) if isinstance(chapters, str) else [(int(f), str(n)) for f, n in chapters]
    items = [_item(f, fps, n, total) for f, n in chs]
    tags = (parse_hashtags(hashtags) if isinstance(hashtags, str) else parse_hashtags(" ".join(hashtags))) \
        if hashtags is not None else list((pkg.get("hashtags") or {}).get("items") or [])
    old_d = pkg.get("description") or {}
    body = (old_d.get("body") or "") if body is None else str(body).replace("\r", "").strip()
    text = description_text(body, items, tags)

    checks = check_title(title) + check_description(text) + check_chapters(chs, fps, frames) + check_hashtags(tags, title)
    ok = not any(c["status"] == "FAIL" for c in checks)
    res = {"ok": ok, "checks": checks, "files": [], "description": text}
    if not ok:
        return res

    titles = pkg.get("titles") or []
    if titles_from:
        from . import prompts as PR
        rec = PR.get(titles_from)
        titles = [{**t, "from": rec["id"]} for t in rec.get("titles") or []]
    titles = [{**t, "chosen": t.get("text") == title} for t in titles]
    if title and not any(t["chosen"] for t in titles):
        titles.append({"text": title, "pattern": "", "chars": len(title), "from": "", "chosen": True})
    now = _dt.datetime.now().isoformat(timespec="seconds")
    out_dir.mkdir(parents=True, exist_ok=True)
    changes = {"title": title, "titles": titles,
               "description": {"text": text, "body": body, "chars": len(text), "file": "description.txt",
                               "checks": checks, "updated": now},
               "chapters": {"fps": fps, "frames": frames, "from": (plan_p.name if plan_p else ""), "items": items},
               "hashtags": {"items": tags, "shown": tags[:HASHTAGS_SHOWN], "line": " ".join(tags)}}
    for name, t in (("title.txt", title + "\n"), ("description.txt", text), ("hashtags.txt", " ".join(tags) + "\n")):
        _write_text(out_dir / name, t)
        res["files"].append(str(out_dir / name))
    res["package"] = update_package(out_dir, changes)
    res["files"].append(str(out_dir / "package.json"))
    return res


def checks_text(checks: list[dict]) -> str:
    return "\n".join(f"  {c['status']:4} {c['part']}: {c['rule']} - {c['detail']}" for c in checks)


def show(project: str | Path) -> str:
    d = publish_dir(project)
    pkg = read_package(d)
    if not pkg:
        return f"nothing in {d} yet - publish.py write {project_dir(project).name} --title \"...\""
    ch = pkg.get("chapters") or {}
    fps = ch.get("fps") or 30
    L = [f"{d}", f"title: {pkg.get('title') or '-'} ({len(pkg.get('title') or '')} characters)"]
    if pkg.get("titles"):
        L.append("titles:")
        L += [f"  {'*' if t.get('chosen') else ' '} {t['text']} [{t.get('pattern') or '-'} | {t.get('chars')} chars]"
              + (f" from {t['from']}" if t.get("from") else "") for t in pkg["titles"]]
    if ch.get("items"):
        L.append(f"chapters ({ch.get('from') or '?'}, {fps:g} fps):")
        L += [f"  {c['yt']:>7} {c['name']}  = f{c['f']} ({c['tc']})" for c in ch["items"]]
    if pkg.get("hashtags"):
        L.append(f"hashtags: {pkg['hashtags'].get('line') or '-'} (shown by the title: "
                 f"{' '.join(pkg['hashtags'].get('shown') or []) or '-'})")
    th = pkg.get("thumbnails")
    if th:
        L.append(f"thumbnails (thumbnail.py): {', '.join(th) if isinstance(th, dict) else len(th)}")
    if pkg.get("candidates"):
        L.append("thumbnail candidates (thumbnail.py): yes")
    desc = pkg.get("description") or {}
    if desc.get("checks"):
        L.append(f"checks ({desc.get('updated', '')[:16]}):\n" + checks_text(desc["checks"]))
    if desc.get("text"):
        L.append("description.txt:\n" + "\n".join("  | " + x for x in desc["text"].rstrip("\n").split("\n")))
    return "\n".join(L)


# ------------------------------------------------------------------------------------------------ self-check
def selfcheck() -> dict:
    """Known answers: YouTube time format, chapter rules, the description's layout, hashtag rules, the plan /
    transcript points, and the package.json merge that keeps thumbnail.py's keys. {passed, seconds, lines}."""
    import tempfile
    t0, lines, ok = time.time(), [], True

    def case(name, cond):
        nonlocal ok
        ok = ok and bool(cond)
        lines.append(f"{'PASS' if cond else 'FAIL'} {name}")

    st = lambda cs, rule: next((c["status"] for c in cs if c["rule"].startswith(rule)), None)  # noqa: E731
    case("yt_time 0 / 65.4 / 3723 / hours on every line",
         (yt_time(0), yt_time(65.4), yt_time(3723), yt_time(5, 4000)) == ("0:00", "1:05", "1:02:03", "0:00:05"))
    case("a frame's whole second: f487 at 25 fps = 0:19, f480 at 29.97 = 0:16",
         _item(487, 25)["yt"] == "0:19" and _item(480, 29.97)["yt"] == "0:16" and _item(480, 30)["tc"] == "00:00:16:00")
    case("parse 'f|name;...' (f480 works)", parse_chapters("0|Intro; f250|Two;500|Three") ==
         [(0, "Intro"), (250, "Two"), (500, "Three")])
    good = [(0, "A"), (250, "B"), (500, "C")]
    cs = check_chapters(good, 25, 1000)
    case("3 chapters of 10 s + 20 s at 25 fps: PASS", not any(c["status"] == "FAIL" for c in cs))
    case("the first not at 0:00: FAIL", st(check_chapters([(25, "A"), (275, "B"), (525, "C")], 25, 1000),
                                           "the first") == "FAIL")
    case("f24 at 25 fps still reads 0:00: PASS", st(check_chapters([(24, "A"), (275, "B"), (525, "C")], 25, 1000),
                                                    "the first") == "PASS")
    case("only 2: FAIL", st(check_chapters(good[:2], 25, 1000), "at least") == "FAIL")
    case("9 s apart on YouTube's seconds: FAIL", st(check_chapters([(0, "A"), (249, "B"), (500, "C")], 25, 1000),
                                                    "each at least") == "FAIL")
    case("the last one 9 s before the end: FAIL", st(check_chapters(good, 25, 749), "each at least") == "FAIL")
    case("out of order: FAIL", st(check_chapters([(0, "A"), (500, "B"), (250, "C")], 25, 1000), "in order") == "FAIL")
    case("a chapter without a name: FAIL", st(check_chapters([(0, "A"), (250, ""), (500, "C")], 25, 1000),
                                              "every chapter") == "FAIL")
    items = [_item(f, 25, n, 40) for f, n in good]
    case("description layout: body, chapters, hashtags",
         description_text("Words.", items, ["#a", "#b"]) == "Words.\n\n0:00 A\n0:10 B\n0:20 C\n\n#a #b\n")
    case("hashtags parsed: # added, duplicates (any case) dropped",
         parse_hashtags("#MusicVideo, musicvideo #4AM  vlog") == ["#MusicVideo", "#4AM", "#vlog"])
    case("61 hashtags: FAIL (all ignored); 60: PASS",
         st(check_hashtags([f"#t{i}" for i in range(61)]), "at most") == "FAIL"
         and st(check_hashtags([f"#t{i}" for i in range(60)]), "at most") == "PASS")
    hs = check_hashtags(["#a", "#b", "#c", "#d"])
    case("4 hashtags: the first 3 are the ones shown", "#a #b #c (" in next(c["detail"] for c in hs if "shown" in c["rule"]))
    case("#lo-fi: WARN (stops at '-')", st(check_hashtags(["#lo-fi"]), "letters") == "WARN")
    case("title 101 chars: FAIL; 61: WARN on a phone; '<': FAIL",
         st(check_title("x" * 101), "at most") == "FAIL" and st(check_title("x" * 61), "about") == "WARN"
         and st(check_title("a <b>"), "no <") == "FAIL")
    case("description 5001 chars: FAIL", st(check_description("x" * 5001), "at most") == "FAIL")
    plan = {"fps": 25, "frames": 900, "width": 100, "height": 100, "curves": {"pan": {"keys": [[400, 0], [440, -150]]}},
            "layers": [
        {"type": "clip", "id": "a", "start": 0, "end": 299},
        {"type": "clip", "id": "b", "start": 300, "end": 599},
        {"type": "clip", "id": "off", "start": 400, "end": 599, "rect": [150, 0, 50, 100],    # off the canvas, then
         "dx": "@pan"},                                                                     # it pans in: no change
        {"type": "clip", "id": "small", "start": 450, "end": 599, "rect": [0, 0, 20, 20]},    # 4 % new: no change
        {"type": "solid", "id": "flash", "start": 600, "end": 601},
        {"type": "clip", "id": "c", "start": 602, "end": 899}]}
    pts = plan_points(plan)
    case("plan points: 0, 300, the flash at 600 (not 602); a layer that pans in / a small one are none; "
         "the pan's x at f420 = -75", [p["f"] for p in pts] == [0, 300, 600]
         and _curve("@pan", plan["curves"], 420) == -75.0 and _area(plan["layers"][2], 100, 100, plan["curves"], 440) == 0.5)
    case("suggested set keeps >= 10 s", suggest(pts, 25, 900) == [0, 300, 600])
    tl = [{"t0": 0.0, "t1": 4.0, "text": "cameras lenses tripods gear"},
          {"t0": 4.2, "t1": 8.0, "text": "cameras lenses again"},
          {"t0": 11.0, "t1": 15.0, "text": "cooking pasta tomato sauce"}]
    tp = transcript_points(tl, 25)
    case("transcript points: a 3 s pause + a new topic at 11 s = f275", [p["f"] for p in tp] == [0, 275]
         and tp[1]["strength"] == 1.0)
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "package.json").write_text(json.dumps({"candidates": {"sheet": "candidates.png"},
                                                    "thumbnails": {"A": {"file": "thumb_A.png"}}, "title": "old"}),
                                        encoding="utf-8")
        pkg = update_package(d, {"title": "new", "hashtags": {"items": ["#a"]}})
        again = read_json(d / "package.json")
        try:
            update_package(d, {"thumbnails": {}})
            refused = False
        except ValueError:
            refused = True
        case("package.json merge: thumbnail.py's keys kept, ours set, theirs refused",
             again == pkg and again["candidates"] == {"sheet": "candidates.png"} and again["thumbnails"]["A"]
             and again["title"] == "new" and refused and not list(d.glob("*.tmp")))
    return {"passed": ok, "seconds": round(time.time() - t0, 3), "lines": lines}
