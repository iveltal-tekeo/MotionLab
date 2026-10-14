"""Checks before the final render (0.4.2): measured on a plain render, a graphic's .mov or snapshots - no guessing
(motionlab\\precheck.py has the measures and their limits).

    .venv\\Scripts\\python tools\\precheck.py <render.mp4 | graphic .mov | a folder of snapshot PNGs>
          [--sfx <name>_sfx.json] [--motion-blur N] [--fps F]
          vanishing  - a part of the picture (or all of it) gone for 1-2 frames that comes back (illdari v1's logo at
                       f38 (00:00:01:08))
          moves      - the fastest move per frame in the video's own pixels: over 60 px a frame with no motion blur
                       (it jumps: a smear), or motion-blur sub-frames over 12 px apart where the copies are
                       measured in the frame (smeared or soft ones are noted only); filmed footage (a plan with
                       "sources"): its moves are noted, not flagged
          sound      - with --sfx (the report tools\\sfx.py make writes): effects far over the song under them,
                       buried under it or under their own level, the limiter taking 3 dB or more
          --motion-blur N  the render's sub-frames; default: the graphic's overlay.json "motion_blur", a plan
                       render's graphics, 0 for snapshots
          --fps F    the rate for a snapshot folder (default: the graphic's overlay.json, else 30)
          -> <build>\\checks\\<name>_precheck.json  every flag with frame + timecode, where, how much, why;
                                                "notes" = what was measured and let through (transitions,
                                                smeared moves, footage moves)
             <build>\\checks\\<name>_precheck.png   the flagged frames (with the frames around them), each labelled
          (<build> = the project's build\\ the input is in; else .app\\dev\\checks\\). Exit code 0 = PASS,
          1 = warnings to look at.
    .venv\\Scripts\\python tools\\precheck.py selfcheck
          known answers on synthetic frames (vanish, speed, copies, clean, sound)
Inputs are only read. A snapshot folder = overlay.py snap / stills (<name>_fNNNN.png; their burned-in label is
ignored); moves and gaps are measured only between consecutive frame numbers.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import precheck as PC  # noqa: E402
from motionlab.util import setup_console  # noqa: E402


def main(argv=None) -> int:
    setup_console()
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "selfcheck":
        return 0 if PC.selfcheck()["ok"] else 1
    ap = argparse.ArgumentParser(prog="precheck.py", description="checks before the final render")
    ap.add_argument("input")
    ap.add_argument("--sfx", default=None, help="<name>_sfx.json from tools\\sfx.py make")
    ap.add_argument("--motion-blur", type=int, default=None, help="the render's motion-blur sub-frames")
    ap.add_argument("--fps", type=float, default=None)
    a = ap.parse_args(argv)
    p = Path(a.input)
    if not p.exists():
        print(f"not found: {p}")
        return 2
    if a.sfx and not Path(a.sfx).exists():
        print(f"not found: {a.sfx}")
        return 2
    res = PC.run(p, sfx=a.sfx, motion_blur=a.motion_blur, fps=a.fps)
    return 0 if res["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
