"""The colour and look of analysed videos, and matching your footage to them (0.4, the cinematic focus).

    .venv\\Scripts\\python tools\\colour.py <analysis>              measure (again) -> analysis\\<name>\\colour\\colour.json:
                                                                the look in words and numbers, per shot with frame +
                                                                timecode (analyze.py does it for cinematic / both)
    .venv\\Scripts\\python tools\\colour.py match <project> --like <video> [<video> <video>] [--strength 0.8]
          a match LUT that moves the project's footage toward the videos' look -> projects\\<p>\\build\\colour\\
          match_<name>.cube (DaVinci Resolve: Color page > LUTs; a plan grade: {"lut3d": "<the .cube>"}), with how
          close the looks are before / after (0-100). The footage needs its frame caches (tools\\prep_footage.py).
Reads the analysis' own metrics and thumbnails (no new decoding); the user's files are only read.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import colour as CO  # noqa: E402
from motionlab import footage as FC  # noqa: E402
from motionlab import style as ST  # noqa: E402
from motionlab.project import Project  # noqa: E402
from motionlab.timecode import frame_to_tc  # noqa: E402
from motionlab.util import ANALYSIS, log, setup_console  # noqa: E402


def measure(name: str) -> int:
    if not (ANALYSIS / name / "events.json").exists():
        print(f"ERROR: no analysis called {name}")
        return 2
    d = CO.analyse(name, log)
    if not d:
        print(f"ERROR: {name}: nothing to measure (no per-frame metrics)")
        return 1
    S, fps = d["summary"], d["fps"]
    print(f"{name}: {S['line']}")
    print(f"  brightness {S.get('brightness')} %, blacks {S.get('black')} %, whites {S.get('white')} %, contrast "
          f"{S.get('contrast')}, saturation {S.get('saturation')} %, warmth (b*) {S.get('warmth')}, tint (a*) "
          f"{S.get('tint')}" + (f", letterbox {S['letterbox']}" if S.get("letterbox") else ""))
    if S.get("palette"):
        print("  main colours: " + ", ".join(f"{c} {round(100 * w)} %" for c, w in S["palette"]))
    print(f"  starting grade for the lab: {S['grade']}")
    for x in d["shots"]:
        print(f"  f{x['start']}-{x['end']} ({frame_to_tc(x['start'], fps)}-{frame_to_tc(x['end'], fps)}): "
              f"{', '.join(x['words']) or 'natural'}" + (f" - {x['palette'][0][0]}" if x.get("palette") else ""))
    print(f"(made from {d['made_from']})")
    return 0


def match(project: str, like: list[str], strength: float) -> int:
    prj = Project(project)
    try:
        style = ST.build(like)
    except ValueError as e:
        print(f"ERROR: {e}")
        return 2
    if not style.get("lab"):
        print("ERROR: the videos have no colour measured yet - run tools\\colour.py <analysis> first "
              "(friends' cards carry it from 0.4 on)")
        return 1
    try:
        srcs = FC.plan_sources(prj.build, True)
    except SystemExit as e:
        print(f"ERROR: {e}")
        return 1
    px = []
    for sid, s in srcs.items():
        m, arr = FC.load(prj.cache, sid, True)
        for i in np.linspace(s["frames"] * 0.1, s["frames"] * 0.9, 6).astype(int):
            im = FC.image(m, arr, int(i))
            px.append(cv2.resize(im, (160, max(1, int(160 * im.shape[0] / im.shape[1]))),
                                 interpolation=cv2.INTER_AREA).reshape(-1, 3))
    px = np.concatenate(px)
    src = CO.lab_stats(px)
    lut = CO.match_lut(src, style["lab"], 33, max(0.0, min(1.0, strength)))
    slug = re.sub(r"[^\w-]+", "_", "_".join(like))[:60].strip("_") or "match"
    out = prj.check(prj.build / "colour" / f"match_{slug}.cube")
    out.parent.mkdir(parents=True, exist_ok=True)
    CO.write_cube(out, lut, f"MotionLab {prj.name} like {slug}")
    after = CO.lab_stats(CO.apply_lut(px.reshape(-1, 1, 3), lut))
    print(f"closeness to {', '.join(x['title'] for x in style['sources'])}: {CO.closeness(src, style['lab']):g} -> "
          f"{CO.closeness(after, style['lab']):g} of 100 (strength {strength:g})")
    print(out)
    return 0


def main() -> int:
    setup_console()
    if len(sys.argv) >= 2 and sys.argv[1] == "match":
        ap = argparse.ArgumentParser(prog="colour.py match")
        ap.add_argument("project")
        ap.add_argument("--like", nargs="+", action="extend", required=True)
        ap.add_argument("--strength", type=float, default=0.8)
        a = ap.parse_args(sys.argv[2:])
        return match(a.project, a.like, a.strength)
    if len(sys.argv) != 2 or sys.argv[1].startswith("-"):
        print(__doc__)
        return 1
    return measure(sys.argv[1])


if __name__ == "__main__":
    sys.exit(main())
