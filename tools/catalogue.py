"""The clip catalogue of a project (0.6.1 "quality over quantity" step 1): every clip looked at once, kept in
projects\\<name>\\build\\clips.json - motionlab\\catalogue.py explains it. The clips are only read.

    .venv\\Scripts\\python tools\\catalogue.py make <project>      the lab's part (no Claude): moments, usable / bad
          windows, motion, light, look-alikes, the day filmed, key frames - from the light cache (prep_footage.py first;
          lines already written are kept for moments that did not change)
    .venv\\Scripts\\python tools\\catalogue.py sheets <project> [--todo]   the key frames on sheets (moment + frame +
          timecode on each tile) -> build\\catalogue\\sheet_NN.jpg; --todo = only moments without a line
    .venv\\Scripts\\python tools\\catalogue.py say <project> <lines.json> [--by user]   Claude's lines (or the user's):
          {"A3": {"what": "a man walks to camera on a wet street at night", "size": "wide", "where": "city street",
          "tags": ["person", "street", "night"]}, ...}; size = wide | medium | close | detail
    .venv\\Scripts\\python tools\\catalogue.py show <project>      the catalogue in words (what the brief carries)
    .venv\\Scripts\\python tools\\catalogue.py selfcheck           a made-up clip with known moments
Writes only into projects\\<project>\\build\\ (clips.json, catalogue\\).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import catalogue as CT  # noqa: E402
from motionlab.project import Project  # noqa: E402
from motionlab.util import load_config, log, setup_console  # noqa: E402


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["make", "sheets", "say", "show", "selfcheck"])
    ap.add_argument("project", nargs="?")
    ap.add_argument("lines", nargs="?")
    ap.add_argument("--todo", action="store_true")
    ap.add_argument("--by", default="claude", choices=["claude", "user"])
    a = ap.parse_args()
    if a.cmd == "selfcheck":
        r = CT.selfcheck()
        print("\n".join(r["lines"]))
        return 0 if r["passed"] else 1
    if not a.project:
        ap.error("which project?")
    prj = Project(a.project)
    if a.cmd == "make":
        cat = CT.make(prj, load_config(), log=log)
        n = sum(len(c["moments"]) for c in cat["clips"])
        print(f"{len(cat['clips'])} clip(s), {n} moment(s), {len(cat['groups'])} look-alike group(s), filmed on "
              f"{len(cat['days'])} day(s), in {cat['seconds']} s -> {CT._rel(prj)}")
        if not cat["clips"]:
            print("no light caches yet - tools\\prep_footage.py <project> first")
            return 1
        return 0
    if a.cmd == "sheets":
        for p in CT.sheets(prj, todo=a.todo):
            print(p)
        return 0
    if a.cmd == "say":
        if not a.lines:
            ap.error("say needs a lines.json")
        r = CT.say(prj, json.loads(Path(a.lines).read_text(encoding="utf-8")), by=a.by)
        print(f"kept {len(r['kept'])}, refused {len(r['refused'])}, {r['left']} moment(s) still without a line")
        for m, why in r["refused"].items():
            print(f"  {m}: {why}")
        return 0 if not r["refused"] else 2
    cat = CT.load(prj)
    if not cat:
        print("no catalogue yet - tools\\catalogue.py make <project>")
        return 1
    print(CT.text(cat))
    return 0


if __name__ == "__main__":
    sys.exit(main())
