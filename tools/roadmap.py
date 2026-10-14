"""MotionLab's roadmap: ONE data file -> a motion graphic. The data is docs\\roadmap\\roadmap.json (versions, where
you are, the strong / weak lines, the numbers); docs\\roadmap\\index.html draws it in the 4AM look (majors x.y.0 = big
badges on the main line, every other number on its major's branch, "you are here", a 4.5 s build-up + a 7.5 s loop).
The app's Home plays that page live; README shows docs\\roadmap.png, rendered from the same page.

    .venv\\Scripts\\python tools\\roadmap.py [check]     the data is valid and agrees with docs\\plans.md (planned
          versions) and CHANGELOG.md (released ones); says when docs\\roadmap.png is older than the data. Exit 1 = errors
    .venv\\Scripts\\python tools\\roadmap.py sync [--dry-run]   brings the data in line with those two files: adds the
          versions it lacks (label = the heading's title, cut short - then write a better one), refreshes every
          "title", drops versions neither file has (unless "keep": true), "here" = the newest released version,
          today's date; writes one line per version
    .venv\\Scripts\\python tools\\roadmap.py show        the roadmap as text (whatsnext.py prints it)
    .venv\\Scripts\\python tools\\roadmap.py render [--video]   docs\\roadmap.png = the frame at 4.5 s (HyperFrames
          snapshot, ~10 s) and with --video docs\\roadmap.mp4 (12 s, ~1 min); needs Node.js + HyperFrames (Settings >
          Programs). The app needs neither: it reads roadmap.json live.

Usual change (a renumber, a release, a new plan): edit docs\\plans.md / CHANGELOG.md -> `roadmap.py sync` -> shorten
new labels, give a new major its icon + line in roadmap.json -> `roadmap.py check` -> `roadmap.py render`.
The keys are explained in roadmap.json's "_help". Writes only docs\\roadmap\\roadmap.json (sync), docs\\roadmap.png /
.mp4, docs\\roadmap\\gsap.min.js (the pinned GSAP, when it changed) and .app\\roadmap\\ (scratch).
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab.util import LAB, setup_console  # noqa: E402

DIR = LAB / "docs" / "roadmap"
DATA = DIR / "roadmap.json"
PAGE = DIR / "index.html"
PNG = LAB / "docs" / "roadmap.png"
MP4 = LAB / "docs" / "roadmap.mp4"
WORK = LAB / ".app" / "roadmap"
PLANS = LAB / "docs" / "plans.md"
CHANGELOG = LAB / "CHANGELOG.md"
FPS, SECONDS, STILL_AT = 30, 12, 4.5                 # the page's timeline: build-up to 4.5 s, then a loop to 12 s
ICONS = {"analyze", "prepare", "edit", "generate", "memory", "library", "knowledge", "home", "videos", "prompts",
         "claude", "update", "news", "settings"}       # = ICONS in index.html (the app's own icons)
STATUSES = ("done", "next", "planned", "later")
KEYS = ("v", "label", "icon", "line", "items", "status", "keep", "title")
LIMITS = {"label": 24, "line": 110, "item": 22, "items": 5}
VER = re.compile(r"^\d+\.\d+\.\d+(?:\.\d+)?$")
PLAN_HEAD = re.compile(r"^## +(\d+(?:\.\d+){2,3})\s+-\s+planned\s+-\s+(.+?)\s*$", re.M)
LOG_HEAD = re.compile(r"^## +(\d+(?:\.\d+){2,3})\s+-\s+(\S+)\s+-\s+(.+?)\s*$", re.M)


def vt(v: str) -> tuple[int, ...]:
    p = [int(x) for x in v.split(".")]
    return tuple(p + [0] * (4 - len(p)))


def is_major(v: str) -> bool:
    return bool(re.fullmatch(r"\d+\.\d+\.0", v))


def era(v: str) -> str:
    return ".".join(v.split(".")[:2])


def load() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def annotate(d: dict) -> list[dict]:
    """The versions sorted, each with its status as the page derives it (keep the two in step)."""
    vs = sorted((dict(x) for x in d.get("versions", []) if VER.match(str(x.get("v", "")))), key=lambda x: vt(x["v"]))
    here = vt(d.get("here", "0.0.0"))
    nxt = next((x for x in vs if vt(x["v"]) > here), None)
    nmaj = next((x for x in vs if vt(x["v"]) > here and is_major(x["v"])), None)
    for x in vs:
        derived = ("done" if vt(x["v"]) <= here else "next" if x is nxt
                   else "planned" if nmaj is None or vt(x["v"]) <= vt(nmaj["v"]) else "later")
        x["_status"] = x.get("status") or derived
        x["_major"] = is_major(x["v"])
        x["_next_major"] = x is nmaj
    return vs


def documented() -> tuple[dict[str, str], dict[str, str]]:
    """{version: title} from CHANGELOG.md (released) and docs\\plans.md (planned)."""
    rel = {m.group(1): m.group(3) for m in LOG_HEAD.finditer(CHANGELOG.read_text(encoding="utf-8"))} \
        if CHANGELOG.exists() else {}
    plan = {m.group(1): m.group(2) for m in PLAN_HEAD.finditer(PLANS.read_text(encoding="utf-8"))} if PLANS.exists() else {}
    return rel, plan


def short_label(title: str) -> str:
    s = re.split(r"[:(]| - ", title)[0].strip()
    return s if len(s) <= LIMITS["label"] else s[:LIMITS["label"] - 1].rstrip() + "…"


# ------------------------------------------------------------------------------------------------ check
def problems(d: dict) -> tuple[list[str], list[str]]:
    err, warn = [], []
    for k in ("date", "here", "versions"):
        if k not in d:
            err.append(f'"{k}" is missing')
    seen = set()
    for x in d.get("versions", []):
        v = str(x.get("v", ""))
        if not VER.match(v):
            err.append(f'version "{v}": not x.y.z or x.y.z.w')
            continue
        if v in seen:
            err.append(f"{v}: listed twice")
        seen.add(v)
        for k in x:
            if k not in KEYS:
                warn.append(f'{v}: unknown key "{k}" (known: {", ".join(KEYS)})')
        lab = str(x.get("label", ""))
        if not lab:
            err.append(f"{v}: no label")
        elif len(lab) > LIMITS["label"]:
            warn.append(f"{v}: label {len(lab)} characters (max {LIMITS['label']}, it gets cut): {lab}")
        if x.get("status") and x["status"] not in STATUSES:
            err.append(f'{v}: status "{x["status"]}" (one of {", ".join(STATUSES)}, or leave it out)')
        if is_major(v):
            if x.get("icon") not in ICONS:
                warn.append(f'{v}: a major needs an icon ({", ".join(sorted(ICONS))}) - has {x.get("icon")!r}')
            if not x.get("line"):
                warn.append(f"{v}: a major needs a line (one sentence)")
        elif x.get("icon") or x.get("line"):
            warn.append(f"{v}: icon / line only show on majors (x.y.0)")
        if len(str(x.get("line", ""))) > LIMITS["line"]:
            warn.append(f"{v}: line {len(x['line'])} characters (max {LIMITS['line']})")
        its = x.get("items") or []
        if len(its) > LIMITS["items"] or any(len(str(s)) > LIMITS["item"] for s in its):
            warn.append(f"{v}: items - at most {LIMITS['items']}, each <= {LIMITS['item']} characters")
    if d.get("here") and d["here"] not in seen:
        err.append(f'"here" = {d["here"]} is not one of the versions')
    rel, plan = documented()
    here = vt(d.get("here", "0.0.0"))
    for x in d.get("versions", []):
        v = str(x.get("v", ""))
        if not VER.match(v):
            continue
        if v in rel and vt(v) > here:
            err.append(f'{v} is released (CHANGELOG.md) but comes after "here" ({d.get("here")})')
        if v in plan and vt(v) <= here:
            err.append(f'{v} is planned (plans.md) but "here" ({d.get("here")}) says it is done')
        if v not in rel and v not in plan and not x.get("keep"):
            warn.append(f'{v} is in neither plans.md nor CHANGELOG.md (sync drops it; "keep": true keeps it)')
        t = rel.get(v) or plan.get(v)
        if t and x.get("title") != t:
            warn.append(f"{v}: title differs from its heading (sync refreshes it): {t}")
    for v in sorted(set(rel) | set(plan), key=vt):
        if v not in seen:
            err.append(f"{v} ({'released' if v in rel else 'planned'}: {(rel.get(v) or plan.get(v))}) is missing - "
                       f"roadmap.py sync adds it")
    if rel and d.get("here") and vt(max(rel, key=vt)) != here:
        warn.append(f'"here" = {d.get("here")}, the newest release in CHANGELOG.md is {max(rel, key=vt)}')
    newest = max(DATA.stat().st_mtime, PAGE.stat().st_mtime) if PAGE.exists() else DATA.stat().st_mtime
    if not PNG.exists() or PNG.stat().st_mtime < newest:
        warn.append("docs\\roadmap.png is older than the data - roadmap.py render")
    if MP4.exists() and MP4.stat().st_mtime < newest:
        warn.append("docs\\roadmap.mp4 is older than the data - roadmap.py render --video")
    return err, warn


def cmd_check(_a=None) -> int:
    d = load()
    err, warn = problems(d)
    vs = annotate(d)
    print(f"{DATA.relative_to(LAB)}: {len(vs)} versions ({sum(x['_major'] for x in vs)} majors), here {d.get('here')}, "
          f"next {next((x['v'] for x in vs if x['_status'] == 'next'), '-')}")
    for e in err:
        print("  ERROR  " + e)
    for w in warn:
        print("  note   " + w)
    if not err and not warn:
        print("  OK - agrees with plans.md and CHANGELOG.md, pictures up to date")
    return 1 if err else 0


# ------------------------------------------------------------------------------------------------ sync
def dump(d: dict) -> str:
    """Stable JSON: top-level keys one per line, versions and stats one line each (short diffs, easy edits)."""
    out = ["{"]
    keys = [k for k in ("_help", "date", "here", "versions", "stats", "strong", "weak", "risks") if k in d] + \
           [k for k in d if k not in ("_help", "date", "here", "versions", "stats", "strong", "weak", "risks")]
    for i, k in enumerate(keys):
        comma = "," if i < len(keys) - 1 else ""
        v = d[k]
        if k in ("_help", "versions", "stats") and isinstance(v, list):
            rows = [json.dumps({kk: x[kk] for kk in KEYS if kk in x} | {kk: x[kk] for kk in x if kk not in KEYS}
                               if k == "versions" else x, ensure_ascii=False) for x in v]
            out.append(f'  "{k}": [')
            out += [f"    {r}" + ("," if j < len(rows) - 1 else "") for j, r in enumerate(rows)]
            out.append(f"  ]{comma}")
        else:
            out.append(f'  "{k}": {json.dumps(v, ensure_ascii=False)}{comma}')
    return "\n".join(out + ["}"]) + "\n"


def cmd_sync(a) -> int:
    d = load()
    rel, plan = documented()
    have = {x["v"]: x for x in d.get("versions", []) if VER.match(str(x.get("v", "")))}
    changes = []
    for v in sorted(set(rel) | set(plan), key=vt):
        t = rel.get(v) or plan[v]
        if v not in have:
            have[v] = {"v": v, "label": short_label(t), "title": t}
            changes.append(f"added {v} ({'released' if v in rel else 'planned'}): label \"{have[v]['label']}\""
                           + (" - a major: give it an icon + line" if is_major(v) else ""))
        elif have[v].get("title") != t:
            have[v]["title"] = t
            changes.append(f"{v}: title -> {t}")
    for v in list(have):
        if v not in rel and v not in plan and not have[v].get("keep"):
            changes.append(f"dropped {v} ({have[v].get('label')}): in neither plans.md nor CHANGELOG.md")
            del have[v]
    if rel:
        newest = max(rel, key=vt)
        if d.get("here") != newest:
            changes.append(f"here: {d.get('here')} -> {newest}")
            d["here"] = newest
    d["versions"] = sorted(have.values(), key=lambda x: vt(x["v"]))
    today = datetime.date.today().isoformat()
    if changes and d.get("date") != today:
        d["date"] = today
    for c in changes:
        print("  " + c)
    if not changes:
        print("  nothing to change - the roadmap agrees with plans.md and CHANGELOG.md")
        return 0
    if a.dry_run:
        print("(dry run: nothing written)")
        return 0
    DATA.write_text(dump(d), encoding="utf-8", newline="\n")
    print(f"wrote {DATA.relative_to(LAB)} - check the new labels, then roadmap.py render")
    return 0


# ------------------------------------------------------------------------------------------------ show
def summary() -> list[str]:
    """The roadmap as text lines (whatsnext.py)."""
    d = load()
    vs = annotate(d)
    out = [f"## Roadmap ({DATA.relative_to(LAB)}, {d.get('date')}; docs\\roadmap.png) - here: {d.get('here')}"]
    last = None
    for x in vs:
        st = "NEXT MAJOR" if x["_next_major"] else x["_status"]
        if era(x["v"]) != last and not x["_major"]:
            out.append(f"- {era(x['v'])} (no {era(x['v'])}.0 - a branch off the main line)")
        last = era(x["v"])
        if x["_major"]:
            out.append(f"- **{x['v']} {x.get('label')}** (major, {st}): {x.get('line', '')}"
                       + (f" [{', '.join(x['items'])}]" if x.get("items") else ""))
        else:
            out.append(f"  - {x['v']} {x.get('label')} ({st})")
    for s in d.get("stats", []):
        out.append(f"- number: {s.get('value')} {s.get('label')}" + (" (weak)" if s.get("weak") else ""))
    for k in ("strong", "weak", "risks"):
        if d.get(k):
            out.append(f"- {k.upper()}: {d[k]}")
    return out


def cmd_show(_a=None) -> int:
    print("\n".join(summary()))
    return 0


# ------------------------------------------------------------------------------------------------ render
def stage(d: dict) -> Path:
    """A copy of the page with the data inlined (HyperFrames builds the timeline before anything could be fetched)."""
    import overlay as OVT                                        # tools\overlay.py: HyperFrames + the pinned GSAP
    if OVT.GSAP.exists() and (not (DIR / "gsap.min.js").exists()
                              or (DIR / "gsap.min.js").read_bytes() != OVT.GSAP.read_bytes()):
        shutil.copy2(OVT.GSAP, DIR / "gsap.min.js")              # the app plays the page with the same GSAP
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)
    page = PAGE.read_text(encoding="utf-8")
    data = json.dumps(d, ensure_ascii=False).replace("</", "<\\/")
    if "<!-- ROADMAP DATA -->" not in page:
        raise SystemExit("index.html lost its <!-- ROADMAP DATA --> marker")
    (WORK / "index.html").write_text(page.replace("<!-- ROADMAP DATA -->", f"<script>window.ROADMAP = {data};</script>"),
                                     encoding="utf-8")
    shutil.copy2(DIR / "gsap.min.js", WORK / "gsap.min.js")
    (WORK / "hyperframes.json").write_text(json.dumps({"paths": {"assets": "assets"}}), encoding="utf-8")
    return WORK


def cmd_render(a) -> int:
    import overlay as OVT
    d = load()
    err, _ = problems(d)
    if err:
        print("\n".join("  ERROR  " + e for e in err))
        raise SystemExit("fix the data first (roadmap.py check / sync)")
    work = stage(d)
    snap = work / "snap"
    r = OVT.hf("snapshot", str(work), "--at", f"{STILL_AT}", "--no-end", "--describe", "false", "-o", str(snap),
               capture=True)
    pngs = sorted(snap.glob("*.png")) if snap.exists() else []
    if r.returncode or not pngs:
        raise SystemExit(f"HyperFrames snapshot failed (exit {r.returncode}): {(r.stderr or r.stdout)[-800:]}")
    from PIL import Image
    im = Image.open(pngs[0]).convert("RGB")
    if im.size != (1920, 1080):
        im = im.resize((1920, 1080), Image.LANCZOS)
    im.save(PNG, optimize=True)
    print(f"{PNG.relative_to(LAB)}  ({PNG.stat().st_size // 1024} KB, the frame at {STILL_AT} s)")
    if a.video:
        r = OVT.hf("render", str(work), "--format", "mp4", "--fps", str(FPS), "--output", str(MP4), "--quality",
                   "standard", "--quiet", "--workers", "auto", "--frames-cache-dir", "off", capture=True)
        if r.returncode or not MP4.exists():
            raise SystemExit(f"HyperFrames render failed (exit {r.returncode}): {(r.stderr or r.stdout)[-800:]}")
        print(f"{MP4.relative_to(LAB)}  ({MP4.stat().st_size // 1024} KB, {SECONDS} s at {FPS} fps)")
    shutil.rmtree(work, ignore_errors=True)
    return 0


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("check")
    p = sub.add_parser("sync")
    p.add_argument("--dry-run", action="store_true")
    sub.add_parser("show")
    p = sub.add_parser("render")
    p.add_argument("--video", action="store_true", help="also docs\\roadmap.mp4 (the whole motion graphic)")
    a = ap.parse_args()
    return {"check": cmd_check, "sync": cmd_sync, "show": cmd_show, "render": cmd_render, None: cmd_check}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
