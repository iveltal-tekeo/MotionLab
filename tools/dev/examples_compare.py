"""Render the overlay examples (tools\\overlays\\examples) with the pinned HyperFrames and compare them with an earlier
render: proves that a rewrite of an example (e.g. hard-coded geometry -> settings) gives the same pixels at its
default settings. Scratch in .app\\dev\\examples-compare\\.

    .venv\\Scripts\\python tools\\dev\\examples_compare.py baseline [name ...]   render and keep as the reference
    .venv\\Scripts\\python tools\\dev\\examples_compare.py compare [name ...]    render again, compare every frame (max 4/255)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import overlay as O  # noqa: E402
from motionlab.timecode import frame_to_tc  # noqa: E402
from motionlab.util import LAB, setup_console  # noqa: E402

WORK = LAB / ".app" / "dev" / "examples-compare"


def main() -> int:
    setup_console()
    if len(sys.argv) < 2 or sys.argv[1] not in ("baseline", "compare"):
        print(__doc__)
        return 2
    mode, names = sys.argv[1], sys.argv[2:] or sorted(p.name for p in O.EXAMPLES.iterdir() if p.is_dir())
    worst_all = 0
    for name in names:
        ex = O.EXAMPLES / name
        fps, frames = O._example_conf(ex)
        dst = WORK / name / ("base" if mode == "baseline" else "new")
        pngs, secs = O._render_pngs(O.HF, O.GSAP, ex, dst)
        print(f"{name}: {len(pngs)} frames rendered in {secs:.1f}s", flush=True)
        if mode == "baseline":
            continue
        base = sorted((WORK / name / "base" / "frames").glob("frame_*.png"))
        if len(base) != len(pngs):
            print(f"  FAIL: {len(pngs)} frames, the baseline has {len(base)}")
            worst_all = 255
            continue
        worst, wf = 0, 0
        for i, (a, b) in enumerate(zip(base, pngs)):
            d = int(np.abs(O._premul(a) - O._premul(b)).max())
            if d > worst:
                worst, wf = d, i
        if worst:
            O._side_by_side(base[wf], pngs[wf], WORK / name / "worst.png")
        print(f"  max difference {worst}/255 at f{wf} ({frame_to_tc(wf, fps)}) -> {'PASS' if worst <= O.TOL else 'FAIL'}")
        worst_all = max(worst_all, worst)
    if mode == "compare":
        print("OVERALL:", "PASS" if worst_all <= O.TOL else "FAIL")
    return 0 if worst_all <= O.TOL else 1


if __name__ == "__main__":
    sys.exit(main())
