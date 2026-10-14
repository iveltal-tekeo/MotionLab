"""Compare tools\\sfx.py's rebuild of illdari_test_copy_1 v2 with the hand-written sfx_v2.py it came from
(0.5.0 step 4). Reads only: sfx_v2.py (imported, no bytecode written), its song and outputs in build\\audio\\,
and the tool's report + files in build\\sfx_tool\\. Prints the differences; writes nothing.

    .venv\\Scripts\\python tools\\dev\\sfx_compare_v2.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from motionlab import sfx as SFX  # noqa: E402
from motionlab.timecode import frame_to_tc  # noqa: E402
from motionlab.util import LAB, setup_console  # noqa: E402

BUILD = LAB / "projects" / "illdari_test_copy_1" / "build"
TOOL = BUILD / "sfx_tool"


def lab(f: int) -> str:
    return f"f{f} ({frame_to_tc(f, 30)})"


def main() -> int:
    setup_console()
    spec = importlib.util.spec_from_file_location("sfx_v2_example", BUILD / "sfx_v2.py")
    v2 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v2)
    q2 = sorted(v2.cues(), key=lambda c: c[0])
    song, sr = sf.read(v2.SONG, dtype="float64", always_2d=True)
    song = np.pad(song, ((0, max(0, v2.N - len(song))), (0, 0)))[:v2.N] * 10 ** (-2.5 / 20)
    mono = song.mean(1)
    g2 = [v2.level(f, x / (np.abs(x).max() + 1e-9), kind, mono) for f, x, kind, _, _ in q2]
    rep = json.loads((TOOL / "kidwild_top3_v2_sfx.json").read_text(encoding="utf-8"))
    mine = rep["cues"]
    # 1. the cue frames
    f1, f2 = sorted(r["f"] for r in mine), sorted(c[0] for c in q2)
    print(f"cues: sfx_v2.py {len(q2)}, the tool {len(mine)}; the same frames: {f1 == f2}")
    # 2. pair each v2 cue with the tool's cue on the same frame whose sound is the same, sample for sample
    used, pairs, worst = set(), [], 0.0
    for (f, x, kind, pan, what), g in zip(q2, g2):
        x = x / (np.abs(x).max() + 1e-9)
        hit = None
        for j, r in enumerate(mine):
            if j in used or r["f"] != f:
                continue
            y = SFX.synth(r["kind"], r.get("params"), r["seed"])
            if len(y) == len(x) and np.abs(y - x).max() < 1e-9:
                hit = j
                worst = max(worst, float(np.abs(y - x).max()))
                break
        if hit is None:
            print(f"  NO MATCH for {lab(f)} {what}")
            continue
        used.add(hit)
        pairs.append((f, what, kind, 20 * np.log10(g), mine[hit]))
    print(f"the same sound (sample for sample, max difference {worst:.1e}): {len(pairs)} of {len(q2)}")
    # 3. levels: both peak-normalise the same sound, so the gain difference is the level difference
    d = np.array([p[4]["gain_db"] - p[3] for p in pairs])
    print(f"level, the tool minus sfx_v2.py (dB): median {np.median(d):+.2f}, mean {d.mean():+.2f}, "
          f"min {d.min():+.2f}, max {d.max():+.2f}; within 1 dB: {int((np.abs(d) <= 1).sum())}, "
          f"within 3 dB: {int((np.abs(d) <= 3).sum())} of {len(d)}")
    by = {}
    for p, x in zip(pairs, d):
        by.setdefault(p[4]["rule"], []).append(x)
    for k, v in by.items():
        print(f"  rule {k:8s}: {len(v):3d} cues, median {np.median(v):+.2f} dB, min {min(v):+.2f}, max {max(v):+.2f}")
    print("the biggest differences:")
    for i in np.argsort(-np.abs(d))[:12]:
        f, what, kind, gdb, r = pairs[i]
        print(f"  {lab(f):18s} {r['kind']:8s} {kind:9s} v2 {gdb:6.1f}  tool {r['gain_db']:6.1f}  ({d[i]:+5.1f} dB)  "
              f"song in the tool's window {r['song_db']:6.1f}, rule {r['rule']:8s} {what}")
    # 4. the files
    for name, a, b in (("effects", BUILD / "audio" / "sfx_v2.wav", TOOL / "kidwild_top3_v2_sfx.wav"),
                       ("mix", BUILD / "audio" / "me_v_me_sfx_v2.wav", TOOL / "kidwild_top3_v2_mix.wav")):
        x, _ = sf.read(a, always_2d=True)
        y, _ = sf.read(b, always_2d=True)
        n = min(len(x), len(y))
        print(f"{name}: sfx_v2 {SFX.rms_db(x):.1f} dBFS RMS, peak {SFX.db(np.abs(x).max()):.1f}; the tool "
              f"{SFX.rms_db(y):.1f} dBFS RMS, peak {SFX.db(np.abs(y).max()):.1f}; lengths {len(x)} / {len(y)} samples; "
              f"difference {SFX.rms_db(x[:n] - y[:n]):.1f} dBFS RMS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
