"""Disk use of the lab, and freeing space safely (only data the lab can rebuild).

    .venv\\Scripts\\python tools\\storage.py                         report: every analysis / project by category
    .venv\\Scripts\\python tools\\storage.py --prune <name> [--yes]  delete <name>'s regenerable caches
    .venv\\Scripts\\python tools\\storage.py --prune all --what cache,checks [--yes]

<name> = an analysis folder, a project, "selftest" or "all". Without --yes nothing is deleted (dry run).
--what (comma list, default "cache"):
  cache    data the lab rebuilds by itself: analysis\\<v>\\cache\\ (analyze.py redoes the signal pass),
           projects\\<p>\\build\\cache\\ (prep_footage.py), build\\resolve\\luts\\ masters (resolve_build.py; Resolve
           uses the copies in its own LUT folder), comp versions no timeline uses (build\\resolve\\comps\\imported),
           the self-test videos and their analyses (selftest.py), __pycache__
  checks   comparison videos and section renders (build\\compare\\, build\\resolve\\<timeline>_<a>-<b>.mp4)
  finals   the full renders build\\<name>_vN.mp4 / <name>_resolve_vN.mp4 (re-render: render_video.py, resolve_build.py)
Never touched: your videos (refs\\, projects\\<p>\\ top level), knowledge (events, reviews, feedback, plans, edit
scripts, manifests, comps, edits, reports, sheets) and media the Resolve project uses (carrier clip, stills).
Each prune writes <folder>\\pruned.json: what went, when, and how to rebuild it.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab.util import LAB, setup_console  # noqa: E402

RESOLVE_LUTS = Path(r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\MotionLab")
CATS = ("source", "keep", "cache", "checks", "finals", "env")
PRUNABLE = ("cache", "checks", "finals")
HOW = {"analysis cache": "analyze.py \"<video>\" redoes the signal pass (minutes); --redetect needs it",
       "footage cache": "prep_footage.py <project> rebuilds it (needed by render_video.py and resolve_build.py "
                        "--refresh-stills)",
       "LUT masters": "any resolve_build.py build rewrites them",
       "unused comp versions": "old Fusion comp texts no timeline manifest refers to",
       "self-test": "selftest.py regenerates the synthetic videos and their analyses",
       "python cache": "Python rebuilds it",
       "app cache": "the app's thumbnails and job logs (made again when needed)",
       "check videos": "render_video.py --compare / resolve_build.py --render A B",
       "full renders": "render_video.py <plan> / resolve_build.py <plan> --render-full"}


def used_comp_versions(resolve_dir: Path) -> set:
    used = set()
    for m in resolve_dir.glob("*_build.json"):
        try:
            used |= {u.get("comp_sha1") for u in json.loads(m.read_text(encoding="utf-8"))["units"]}
        except (OSError, ValueError, KeyError):
            pass
    return used


def classify(rel: Path, used: dict) -> tuple[str, str]:
    """(category, what) for a file path relative to the lab folder."""
    p = rel.parts
    if p[0] == ".venv":
        return "env", "python environment"
    if p[0] == ".app":
        return "cache", "app cache"
    if "__pycache__" in p:
        return "cache", "python cache"
    if p[0] == "refs":
        return "source", "reference videos"
    if p[0] == "tools":
        return ("cache", "self-test") if len(p) > 2 and p[1] == "selftest" else ("keep", "code")
    if p[0] == "analysis" and len(p) >= 3:
        if p[1].startswith("synthetic_"):
            return "cache", "self-test"
        if p[2] == "cache" or p[2] == "proxy_cfr.mp4":
            return "cache", "analysis cache"
        return "keep", "analysis results"
    if p[0] == "projects" and len(p) >= 3:
        if len(p) == 3 or p[2] != "build":
            return "source", "your footage"
        b = p[3:]
        if b[0] == "cache":
            return "cache", "footage cache"
        if b[0] == "compare":
            return "checks", "check videos"
        if len(b) == 1 and rel.suffix.lower() == ".mp4":
            return "finals", "full renders"
        if b[0] == "resolve" and len(b) >= 2:
            if len(b) == 2 and rel.suffix.lower() == ".mp4":
                return "checks", "check videos"
            if b[1] == "luts":
                return "cache", "LUT masters"
            if b[1] == "comps" and len(b) == 4 and b[2] == "imported" and rel.stem not in used.get(p[1], set()):
                return "cache", "unused comp versions"
            if b[1] == "media":
                return "keep", "media the Resolve project uses"
        return "keep", "project results"
    return "keep", "lab files"


def unit_of(rel: Path) -> str:
    p = rel.parts
    if p[0] in ("analysis", "projects") and len(p) >= 3:
        return f"{p[0]}\\{p[1]}"
    if p[0] == "tools" and len(p) > 2 and p[1] == "selftest":
        return "tools\\selftest"
    return p[0] if len(p) > 1 else "(top level)"


def scan():
    used = {d.name: used_comp_versions(d / "build" / "resolve") for d in (LAB / "projects").glob("*") if d.is_dir()}
    files = []
    for root, dirs, names in os.walk(LAB):
        for n in names:
            fp = Path(root) / n
            if fp.is_symlink():
                continue
            rel = fp.relative_to(LAB)
            cat, what = classify(rel, used)
            files.append((rel, fp.stat().st_size, cat, what))
    return files


def gb(n: float) -> str:
    return f"{n / 1e9:6.2f} GB" if n >= 1e8 else f"{n / 1e6:6.0f} MB"


def report(files) -> None:
    units: dict[str, dict] = {}
    for rel, size, cat, _ in files:
        u = units.setdefault(unit_of(rel), dict.fromkeys(CATS, 0))
        u[cat] += size
    print(f"{'folder':58s}" + "".join(f"{c:>10s}" for c in CATS) + f"{'total':>10s}")
    for name, u in sorted(units.items(), key=lambda kv: -sum(kv[1].values())):
        print(f"{name[:58]:58s}" + "".join(f"{gb(u[c]) if u[c] else '-':>10s}" for c in CATS)
              + f"{gb(sum(u.values())):>10s}")
    tot = {c: sum(s for _, s, cc, _ in files if cc == c) for c in CATS}
    print(f"{'TOTAL':58s}" + "".join(f"{gb(tot[c]):>10s}" for c in CATS) + f"{gb(sum(tot.values())):>10s}")
    if RESOLVE_LUTS.exists():
        lut = sum(f.stat().st_size for f in RESOLVE_LUTS.rglob("*") if f.is_file())
        print(f"outside the lab: Resolve LUT copies {RESOLVE_LUTS} {gb(lut).strip()} (keep while the Resolve "
              f"projects exist)")
    free = shutil.disk_usage(str(LAB)).free
    print(f"free on {LAB.anchor}: {gb(free).strip()}")
    whats: dict[str, int] = {}
    for _, size, cat, what in files:
        if cat in PRUNABLE:
            whats[what] = whats.get(what, 0) + size
    if whats:
        print("\nfreeable (storage.py --prune <name> --what ...):")
        for what, size in sorted(whats.items(), key=lambda kv: -kv[1]):
            print(f"  {gb(size)}  {what}: {HOW.get(what, '')}")


def prune(files, target: str, what: set, yes: bool) -> int:
    def match(rel):
        u = unit_of(rel)
        return target == "all" or u.split("\\")[-1] == target or u == target or \
            (target == "selftest" and (u == "tools\\selftest" or "synthetic_" in u))
    sel = [(rel, size, cat, w) for rel, size, cat, w in files if cat in what and match(rel)]
    if not sel:
        print(f"nothing to prune for '{target}' ({', '.join(sorted(what))})")
        return 0
    by: dict[tuple, list] = {}
    for rel, size, cat, w in sel:
        by.setdefault((unit_of(rel), w), []).append((rel, size))
    for (u, w), items in sorted(by.items()):
        print(f"  {gb(sum(s for _, s in items))}  {u}: {w} ({len(items)} files) - rebuild: {HOW.get(w, '')}")
    total = sum(s for _, s, _, _ in sel)
    if not yes:
        print(f"dry run: {gb(total).strip()} would be freed; add --yes to delete")
        return 0
    roots = [LAB / "analysis", LAB / "projects", LAB / "tools" / "selftest", LAB / ".app"]
    notes: dict[Path, list] = {}
    for rel, size, cat, w in sel:
        fp = (LAB / rel).resolve()
        # last line of defence: only below the lab's own output folders, never a source
        if cat not in PRUNABLE or (not any(r in fp.parents for r in roots) and "__pycache__" not in fp.parts):
            raise SystemExit(f"refusing to delete {fp}")
        if rel.parts[0] == "projects" and (len(rel.parts) < 4 or rel.parts[2] != "build"):
            raise SystemExit(f"refusing to delete {fp} (project footage)")
        fp.unlink()
        u = unit_of(rel)
        home = LAB / u if u.startswith(("analysis", "projects")) else None
        if home is not None and u.startswith("projects"):
            home = home / "build"
        if home is not None:
            notes.setdefault(home, []).append({"path": str(rel), "bytes": size, "what": w})
    for home, items in notes.items():
        p = home / "pruned.json"
        log_ = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
        log_.append({"date": time.strftime("%Y-%m-%d %H:%M:%S"), "freed_bytes": sum(i["bytes"] for i in items),
                     "rebuild": {w: HOW.get(w, "") for w in {i["what"] for i in items}}, "files": items})
        p.write_text(json.dumps(log_, indent=1), encoding="utf-8")
    for d in sorted({(LAB / rel).parent for rel, _, _, _ in sel}, key=lambda d: -len(d.parts)):
        try:
            d.rmdir()                                  # remove folders the prune emptied
        except OSError:
            pass
    print(f"freed {gb(total).strip()}")
    return 0


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prune", metavar="NAME")
    ap.add_argument("--what", default="cache", help="comma list of: cache, checks, finals")
    ap.add_argument("--yes", action="store_true", help="really delete (default: dry run)")
    a = ap.parse_args()
    files = scan()
    if not a.prune:
        report(files)
        return 0
    what = {w.strip() for w in a.what.split(",") if w.strip()}
    bad = what - set(PRUNABLE)
    if bad:
        raise SystemExit(f"--what: unknown {', '.join(sorted(bad))} (use {', '.join(PRUNABLE)})")
    return prune(files, a.prune, what, a.yes)


if __name__ == "__main__":
    sys.exit(main())
