"""Check that a player copy (motionlab.app.player, 0.4.2.1) keeps every frame at its time: makes the copy of each
video into a scratch folder with the app's own ffmpeg command and compares the frame count and every frame's
presentation time with the original's (VFR samples included). Read-only on the videos.

    .venv\\Scripts\\python tools\\dev\\player_check.py <video> [<video> ...]

Exit 0 = PASS (same number of frames, every frame time within 1 ms, height <= 720, H.264 + sound)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from motionlab.app import player  # noqa: E402
from motionlab.util import tool  # noqa: E402


def frames(p: Path) -> list[float]:
    """Every decoded video frame's presentation time (s), in display order."""
    out = subprocess.run([tool("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "frame=best_effort_timestamp_time", "-of", "csv=p=0", str(p)],
                         capture_output=True, text=True, timeout=600).stdout
    return [float(x.strip().rstrip(",")) for x in out.splitlines() if x.strip().rstrip(",") not in ("", "N/A")]


def streams(p: Path) -> dict:
    out = subprocess.run([tool("ffprobe"), "-v", "error", "-show_entries", "stream=codec_type,codec_name,height",
                          "-of", "json", str(p)], capture_output=True, text=True, timeout=60).stdout
    return {s["codec_type"]: s for s in json.loads(out).get("streams", [])}


def check(src: Path, tmp: Path) -> bool:
    dst = tmp / (src.stem + "_player.mp4")
    r = subprocess.run(player.command(src, dst), capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL  {src.name}: ffmpeg {r.returncode}: {r.stdout[-400:]}")
        return False
    a, b = frames(src), frames(dst)
    d = max((abs((x - a[0]) - (y - b[0])) for x, y in zip(a, b)), default=0.0)
    gaps = len({round(y - x, 4) for x, y in zip(a, a[1:])})
    s = streams(dst)
    good = (len(a) == len(b) and d <= 0.001 and abs(a[0] - b[0]) <= 0.001 and s.get("video", {}).get("codec_name") == "h264"
            and int(s["video"]["height"]) <= player.MAX_HEIGHT and ("audio" in s) == ("audio" in streams(src)))
    print(f"{'PASS' if good else 'FAIL'}  {src.name} ({player.codec(src)['codec']}): {len(a)} frames -> {len(b)}, "
          f"first frame at {a[0]:.4f} s -> {b[0]:.4f} s, largest time difference {d * 1000:.2f} ms, "
          f"{gaps} different frame intervals ({'VFR' if gaps >= 2 else 'CFR'}), copy {s['video']['codec_name']} "
          f"height {s['video']['height']}, sound {'kept' if 'audio' in s else 'none'}")
    return good


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    with tempfile.TemporaryDirectory() as t:
        ok = all([check(Path(v), Path(t)) for v in sys.argv[1:]])
    print("player copy check: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
