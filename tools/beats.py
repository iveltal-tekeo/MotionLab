"""The beats of a song as frames + timecodes - for timing a motion-graphics video or an edit to music (0.4,
/generate-video section 2). The song is only read; its sound is decoded into .app\\tmp\\ and deleted afterwards.

    .venv\\Scripts\\python tools\\beats.py <song> [--fps 30] [--start 12.5] [--length 30] [--json]
Prints the tempo, then every beat (downbeats marked) and the drops as frame + timecode at --fps, counted from
--start seconds into the song (the edit's frame 0). --json = the same as JSON.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import audio as AU  # noqa: E402
from motionlab.timecode import frame_to_tc  # noqa: E402
from motionlab.util import LAB, load_config, setup_console  # noqa: E402


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("song")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--start", type=float, default=0.0, help="seconds into the song = the edit's frame 0")
    ap.add_argument("--length", type=float, help="seconds of the edit (default: to the end of the song)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    song = Path(a.song)
    if not song.is_file():
        print(f"ERROR: no such file: {song}")
        return 2
    cfg = load_config()
    tmp_root = LAB / ".app" / "tmp"
    tmp_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=tmp_root) as tmp:
        wav = Path(tmp) / "song.wav"
        if not AU.extract_wav(song, wav, int(cfg["audio"]["sample_rate"])):
            print(f"ERROR: no sound found in {song.name}")
            return 2
        import soundfile as sf
        dur = float(sf.info(str(wav)).duration)
        try:
            A = AU.analyze(wav, a.fps, int(dur * a.fps) + 1, 0.0, cfg["audio"])
        except AU.VCRedistMissing as e:
            print(f"ERROR: {e}")
            return 1
    if not A.get("available"):
        print(f"ERROR: {A.get('reason', 'no beats found')}")
        return 1
    s0 = a.start * a.fps
    end = (a.start + a.length) * a.fps if a.length else dur * a.fps
    beats = [{"frame": int(round(b["frame"] - s0)), "downbeat": b["downbeat"]} for b in A["beats"]
             if s0 <= b["frame"] < end]
    drops = [int(round(d["frame"] - s0)) for d in A["drops"] if s0 <= d["frame"] < end]
    for b in beats:
        b["tc"] = frame_to_tc(b["frame"], a.fps)
    out = {"song": str(song), "duration_s": round(dur, 2), "fps": a.fps, "start_s": a.start, "bpm": A["bpm"],
           "beat_frames": A.get("beat_period_frames"), "beats": beats,
           "drops": [{"frame": f, "tc": frame_to_tc(f, a.fps)} for f in drops]}
    if a.json:
        print(json.dumps(out, indent=1))
        return 0
    print(f"{song.name}: {dur:.1f} s, {A['bpm']:g} BPM (a beat every {A.get('beat_period_frames') or 0:g} frames at "
          f"{a.fps:g} fps), frame 0 = {a.start:g} s into the song")
    print("drops: " + (", ".join(f"f{d['frame']} ({d['tc']})" for d in out["drops"]) or "none"))
    for i in range(0, len(beats), 8):
        print("  " + "  ".join(f"{'*' if b['downbeat'] else ' '}f{b['frame']} ({b['tc']})" for b in beats[i:i + 8]))
    print("(* = a downbeat, the first beat of a bar)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
