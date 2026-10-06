"""Contact sheet + looping preview for ANY frame range of an analyzed video (to check missed effects).

    .venv\\Scripts\\python tools\\sheet.py <analysis name or folder> <start frame> <end frame> [label]

Writes analysis\\<name>\\inspect\\<start>-<end>\\sheet_NN.jpg and preview.mp4, labelled with frame numbers,
timecodes and the per-frame metrics most likely to matter (luma, scale, motion, RGB offset, sharpness).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import media as ME  # noqa: E402
from motionlab.signals import load_metrics  # noqa: E402
from motionlab.util import ANALYSIS, SourceGuard, read_json, setup_console  # noqa: E402


def main() -> int:
    setup_console()
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    arg = Path(sys.argv[1])
    out = arg if arg.is_dir() else ANALYSIS / sys.argv[1]
    a, b = int(sys.argv[2]), int(sys.argv[3])
    label = sys.argv[4] if len(sys.argv) > 4 else "inspect"
    data = read_json(out / "events.json")
    meta = read_json(out / "cache" / "meta.json")
    from motionlab.util import load_config
    cfg = load_config()
    N, fps = meta["n_frames"], data["video"]["fps"]
    a, b = max(0, min(a, b)), min(N - 1, max(a, b))
    src = Path(data["source"]["path"])
    video = src if data["video"]["analysis_video"] == "source" else out / data["video"]["analysis_video"]
    m = load_metrics(out)
    labels = {}
    for i in range(max(0, a - 3), min(N, b + 4)):
        sc = m["scale"][i]
        parts = [f"L{m['luma_mean'][i]:.0f}%"]
        if np.isfinite(sc) and abs(sc - 1) > 0.01:
            parts.append(f"x{sc:.2f}")
        sp = np.hypot(np.nan_to_num(m["tx_pct"][i]), np.nan_to_num(m["ty_pct"][i]))
        if sp > 1:
            parts.append(f"{sp:.0f}%/f")
        if np.nan_to_num(m["rgb_shift_px"][i]) >= 2:
            parts.append(f"rgb{m['rgb_shift_px'][i]:.0f}")
        labels[i] = " ".join(parts)
    ev = {"id": f"{a}-{b}", "type": "inspect", "type_label": label, "sub": "", "start": a, "end": b,
          "duration_frames": b - a + 1, "cuts": [], "labels": labels}
    insp = out / "inspect"
    plans = ME.plan([ev], N, fps, cfg)
    beats = {int(round(x["frame"])) for x in (data.get("audio") or {}).get("beats", [])}
    marks = {"beat": beats, "downbeat": set(), "drop": {int(round(x["frame"])) for x in (data.get("audio") or {}).get("drops", [])},
             "cuts": {c["frame"] for c in data["hard_cuts"]}}
    # render into inspect/<range>/ by pointing the media helpers at a sub-folder
    sub = insp / ev["id"]
    sub.mkdir(parents=True, exist_ok=True)
    wav = out / "audio.wav"
    aoff = (data.get("audio") or {}).get("offset_s", 0.0) or 0.0
    ME.extract_and_render(video, {"video": {**data["video"], "display_aspect": data["video"]["display_width"] /
                                            data["video"]["display_height"]}}, [ev], plans, sub, fps,
                          wav if wav.exists() else None, aoff, marks, cfg, False, SourceGuard(src, sub))
    sheets = ME.build_sheets(ev, plans[ev["id"]], sub, fps, False,
                             data["video"]["display_width"] / data["video"]["display_height"], marks, cfg,
                             SourceGuard(src, sub))
    print("sheets:")
    for s in sheets:
        print("  ", sub / s)
    print("preview:", sub / "events" / ev["id"] / "preview.mp4")
    return 0


if __name__ == "__main__":
    sys.exit(main())
