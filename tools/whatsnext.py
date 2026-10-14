"""Where MotionLab stands, in one short digest for deciding what to do next (the /whats-next skill reads it):
the version and what changed since the last release, GitHub's tested state, every planned version's status lines
(docs\\plans.md), the roadmap (docs\\roadmap\\roadmap.json via tools\\roadmap.py), ideas not picked yet (docs\\ideas.md), the lab's own state
(references and their next workflow step, videos, prompts, friends' lessons, library picks) and the last self-test.

    .venv\\Scripts\\python tools\\whatsnext.py [--fetch] [--section version|plans|roadmap|ideas|lab]

--fetch asks GitHub first (git fetch) so "tested" and "main" are current. Read-only: changes nothing in the lab.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import __version__  # noqa: E402
from motionlab.util import ANALYSIS, LAB, setup_console  # noqa: E402

STATUS = re.compile(r"\*\*(Built|Done|Status|Still open|Started|Not yet|Blocked|Measured|Shipped)\b[^*]{0,70}\*\*", re.I)
ITEM = re.compile(r"^(?:\d+\.|-)\s+\*\*(.+?)\*\*", re.M)
SECTION = re.compile(r"^## +(\d+(?:\.\d+)+)\s*-\s*([^-\n]+?)\s*-\s*(.+)$", re.M)


def git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=str(LAB), capture_output=True, text=True, encoding="utf-8",
                       errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return r.stdout.strip() if r.returncode == 0 else ""


def short(text: str, n: int = 240) -> str:
    t = re.sub(r"\s+", " ", text).strip()
    return t if len(t) <= n else t[:n - 1].rstrip() + "…"


# ------------------------------------------------------------------------------------------------ version / git
def version(fetch: bool) -> list[str]:
    out = [f"## Version and changes", f"- this copy: MotionLab {__version__}"]
    if not git("rev-parse", "--git-dir"):
        return out + ["- not a git copy: no history"]
    if fetch:
        git("fetch", "-q", "origin")
    tag = git("describe", "--tags", "--abbrev=0")
    cl = (LAB / "CHANGELOG.md").read_text(encoding="utf-8") if (LAB / "CHANGELOG.md").exists() else ""
    m = re.search(r"^## +(\d[^\n]*)$", cl, re.M)
    out.append(f"- last release: {m.group(1).strip() if m else '?'} (git tag {tag or 'none'})")
    since = git("log", "--format=%h %ad %s", "--date=short", f"{tag}..HEAD") if tag else ""
    rows = [r for r in since.splitlines() if r.strip()]
    out.append(f"- since {tag or 'the start'}: {len(rows)} commit(s) not in a release yet (they need a CHANGELOG "
               "section when the next version is published)")
    out += [f"  - {r}" for r in rows[:25]] + (["  - …"] if len(rows) > 25 else [])
    head = git("rev-parse", "--short", "HEAD")
    main, tested = git("rev-parse", "--short", "origin/main"), git("rev-parse", "--short", "origin/tested")
    ahead = git("rev-list", "--count", "origin/main..HEAD") if main else ""
    out.append(f"- GitHub{' (just fetched)' if fetch else ' (as last fetched)'}: main {main or '?'}, tested "
               f"{tested or '?'} (= what friends' Update installs), this copy {head}"
               + (f", {ahead} commit(s) not pushed" if ahead and ahead != "0" else ""))
    if main and tested and main != tested:
        n = git("rev-list", "--count", "origin/tested..origin/main")
        out.append(f"  - {n} pushed commit(s) not tested yet (or their run failed - see the Actions tab)")
    dirty = [re.sub(r"^\s*\S+\s+", "", ln) for ln in git("status", "--porcelain").splitlines() if ln.strip()]
    out.append(f"- uncommitted: {len(dirty)} file(s)" + (": " + ", ".join(dirty[:8]) + (" …" if len(dirty) > 8 else "")
                                                         if dirty else ""))
    return out


# ------------------------------------------------------------------------------------------------ plans
def plans() -> list[str]:
    p = LAB / "docs" / "plans.md"
    if not p.exists():
        return ["## Plans", "- docs\\plans.md is missing"]
    text = p.read_text(encoding="utf-8")
    heads = list(SECTION.finditer(text))
    out = ["## Planned versions (docs\\plans.md, newest plan first; status lines only - read a section for details)"]
    for i, h in enumerate(heads):
        body = text[h.end():heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        out.append(f"### {h.group(1)} - {h.group(2)} - {h.group(3)}")
        items = [(m.start(), m.group(1).rstrip(":")) for m in ITEM.finditer(body)]
        seen = set()
        for m in STATUS.finditer(body):
            stop = len(body)
            for pat in (r"\n\s*\n", r"\n(?:\d+\.|-)\s+\*\*", r"\n\s+- \*\*"):
                n = re.compile(pat).search(body, m.end())
                if n:
                    stop = min(stop, n.start())
            snippet = short(body[m.start():stop])
            item = next((t for s, t in reversed(items) if s <= m.start()), "")
            if item and item.lower() in snippet.lower()[:len(item) + 6]:
                item = ""
            key = snippet[:80]
            if key in seen:
                continue
            seen.add(key)
            out.append(f"- {item + ': ' if item else ''}{snippet}")
        if len(out) and out[-1].startswith("###"):
            out.append("- (no status lines: not started)")
    return out


# ------------------------------------------------------------------------------------------------ roadmap / ideas
def roadmap() -> list[str]:
    try:
        import roadmap as RM
        out = RM.summary()
        err, warn = RM.problems(RM.load())
    except Exception as e:                                      # noqa: BLE001 - the digest must still print
        return ["## Roadmap", f"- docs\\roadmap\\roadmap.json not readable (tools\\roadmap.py): {e}"]
    return out + [f"- roadmap.py check: {short(m, 200)}" for m in err + warn]


def ideas() -> list[str]:
    p = LAB / "docs" / "ideas.md"
    if not p.exists():
        return ["## Ideas", "- docs\\ideas.md is missing"]
    text = p.read_text(encoding="utf-8")
    out = ["## Ideas not picked yet (docs\\ideas.md - not plans until the user picks one)"]
    for sec in re.split(r"^## ", text, flags=re.M)[1:]:
        name, _, body = sec.partition("\n")
        names = [m.group(1) for m in re.finditer(r"^\|\s*\*\*(.+?)\*\*", body, re.M)]
        names += [m.group(1) for m in re.finditer(r"^- \*\*(.+?)\*\*", body, re.M)]
        if names:
            out.append(f"- {name.strip()}: " + "; ".join(names))
    return out


# ------------------------------------------------------------------------------------------------ the lab
def lab() -> list[str]:
    from motionlab import overlay_settings as OS
    from motionlab import prompts as PR
    from motionlab.app import data
    out = ["## The lab now (what waits on the user or on Claude)"]
    steps = {"claude": "Claude's review (/analyze-reference)", "verdicts": "your verdicts in the app",
             "feedback": "feedback to Claude", "share": "Share (Claude's memory)", None: "all steps done"}
    refs = data.list_references()
    for r in refs:
        fl = r["flow"]
        extra = ""
        if fl["next"] == "verdicts":
            extra = f" ({fl['given']}/{fl['real']} effects" + (f", {fl['misses_checked']}/{fl['misses']} possible "
                                                                  f"misses" if fl["misses"] else "") + ")"
        content = [k for k in ("transcript", "stats") if (ANALYSIS / r["name"] / "content" / f"{k}.json").exists()]
        out.append(f"- reference {r['title']}: next = {steps.get(fl['next'], fl['next'])}{extra}"
                   + (f"; content: {', '.join(content)}" if content else "; no transcript / numbers yet"))
    if not refs:
        out.append("- no references analysed yet")
    for pr in data.list_projects():
        ov = OS.project_overlays(pr["name"])
        out.append(f"- video {pr['name']}: {len(pr['plans'])} edit version(s), {len(pr['renders'])} render(s), "
                   f"{len(ov)} graphic(s), Resolve timelines: {', '.join(pr['resolve']) or 'none'}")
    lib = data.library()
    out.append(f"- library: {len(lib['items'])} effect(s), {len(lib.get('graphics') or [])} graphic(s) "
               f"(incl. examples), {len(lib['picks'])} pick(s) waiting to be saved")
    items = PR.load_all()
    rated = sum(1 for r in items if (r.get("result") or {}).get("rating"))
    mine = sum(1 for r in items if (r.get("source") or {}).get("type") == "tested")
    kinds = ", ".join(f"{k} {sum(1 for r in items if r['kind'] == k)}" for k in PR.KINDS)
    out.append(f"- prompts: {len(items)} ({kinds}); rated by the user {rated}; the user's own tested {mine}")
    inc = sorted((LAB / "knowledge" / "incoming").glob("*.md")) if (LAB / "knowledge" / "incoming").exists() else []
    out.append(f"- friends' lessons waiting for review: {len(inc)}")
    scores = sorted(ANALYSIS.glob("synthetic_*/selftest_score.json"))
    if scores:
        ok = all(json.loads(s.read_text(encoding="utf-8")).get("passed") for s in scores)
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(max(s.stat().st_mtime for s in scores)))
        out.append(f"- last self-test on this PC: {'PASS' if ok else 'FAIL'} ({len(scores)} videos, {when})")
    return out


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fetch", action="store_true", help="git fetch first (GitHub's main / tested now)")
    ap.add_argument("--section", choices=("version", "plans", "roadmap", "ideas", "lab"))
    a = ap.parse_args()
    parts = {"version": lambda: version(a.fetch), "plans": plans, "roadmap": roadmap, "ideas": ideas, "lab": lab}
    print(f"# MotionLab - where it stands ({time.strftime('%Y-%m-%d %H:%M')})\n")
    for k, fn in parts.items():
        if a.section and a.section != k:
            continue
        print("\n".join(fn()) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
