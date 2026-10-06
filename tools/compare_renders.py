"""Compare two renders of the same timeline frame by frame (e.g. the lab's v1 and the Resolve rebuild).

    .venv\\Scripts\\python tools\\compare_renders.py <left.mp4> <right.mp4> --range 0 517 --out <dir>
        [--right-start 0]   frame number of the right video's first frame (default: A when the right video is a
                            section render of exactly B-A+1 frames, else 0)
        [--frames 30,86]    frames for the side-by-side sheet (default: every --every frames + the worst ones)
Writes <dir>\\<name>_diff.csv (per frame: mean |diff| and 99th percentile, 0-255, full RGB) and
<dir>\\<name>_sheet_NN.jpg (left | right | |difference| x 4 for chosen frames, each labelled f<n> HH:MM:SS:FF).
Both videos are only read.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab.media import fonts  # noqa: E402
from motionlab.timecode import frame_to_tc  # noqa: E402
from motionlab.util import log, setup_console, tool  # noqa: E402


def probe(path: Path) -> tuple[int, int, float, int]:
    out = subprocess.run([tool("ffprobe"), "-v", "error", "-select_streams", "v:0", "-count_packets",
                          "-show_entries", "stream=width,height,r_frame_rate,nb_read_packets", "-of", "json",
                          str(path)], capture_output=True, text=True, check=True).stdout
    s = json.loads(out)["streams"][0]
    n, d = (int(x) for x in s["r_frame_rate"].split("/"))
    return int(s["width"]), int(s["height"]), n / d, int(s["nb_read_packets"])


def reader(path: Path, first: int, count: int, fps: float, w: int, h: int):
    cmd = [tool("ffmpeg"), "-v", "error", "-nostdin"]
    if first > 0:
        cmd += ["-ss", f"{first / fps:.6f}"]
    cmd += ["-i", str(path), "-map", "0:v:0", "-frames:v", str(count), "-vf", f"scale={w}:{h}:flags=area",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    fs = w * h * 3
    for _ in range(count):
        buf = p.stdout.read(fs)
        if len(buf) < fs:
            break
        yield np.frombuffer(buf, np.uint8).reshape(h, w, 3)
    p.kill()


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("left")
    ap.add_argument("right")
    ap.add_argument("--range", nargs=2, type=int, required=True)
    ap.add_argument("--right-start", type=int)
    ap.add_argument("--out", required=True)
    ap.add_argument("--name")
    ap.add_argument("--frames", default="")
    ap.add_argument("--every", type=int, default=25)
    ap.add_argument("--worst", type=int, default=6)
    ap.add_argument("--labels", default="LEFT,RIGHT")
    a = ap.parse_args()
    L, R = Path(a.left).resolve(), Path(a.right).resolve()
    A, B = a.range
    wl, hl, fps, nl = probe(L)
    wr, hr, fpsr, nr = probe(R)
    rs = a.right_start if a.right_start is not None else (A if nr == B - A + 1 else 0)
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    name = a.name or f"{R.stem}_vs_{L.stem}_{A}-{B}"
    labl, labr = a.labels.split(",")
    n = B - A + 1
    rows = []
    for i, (fl, fr) in enumerate(zip(reader(L, A, n, fps, wl, hl), reader(R, A - rs, n, fpsr, wl, hl))):
        d = np.abs(fl.astype(np.int16) - fr.astype(np.int16))
        f = A + i
        rows.append({"frame": f, "tc": frame_to_tc(f, fps), "mae": round(float(d.mean()), 3),
                     "p99": round(float(np.percentile(d, 99)), 1), "left_mean": round(float(fl.mean()), 2),
                     "right_mean": round(float(fr.mean()), 2)})
    if not rows:
        raise SystemExit("no frames compared")
    with open(out / f"{name}_diff.csv", "w", newline="", encoding="utf-8") as fh:
        wtr = csv.DictWriter(fh, fieldnames=list(rows[0]))
        wtr.writeheader()
        wtr.writerows(rows)
    maes = np.array([r["mae"] for r in rows])
    worst = sorted(rows, key=lambda r: -r["mae"])[:a.worst]
    log(f"{name}: {len(rows)} frames f{A}-{A + len(rows) - 1}; mean |diff| {maes.mean():.2f}/255 (median "
        f"{np.median(maes):.2f}, max {maes.max():.2f} at f{rows[int(maes.argmax())]['frame']} "
        f"{rows[int(maes.argmax())]['tc']})")
    for r in worst:
        log(f"   worst f{r['frame']} {r['tc']}: mae {r['mae']}, p99 {r['p99']}, mean {r['left_mean']} vs "
            f"{r['right_mean']}")
    picks = sorted({int(v) for v in a.frames.split(",") if v.strip()} or
                   ({f for f in range(A, B + 1, max(1, a.every))} | {r["frame"] for r in worst}))
    picks = [f for f in picks if A <= f <= A + len(rows) - 1]
    # sheet: one row per frame, three 380 x 270 tiles
    tw, th, strip = 380, 270, 22
    F = fonts(1.0)
    imgs = {}
    for f in picks:
        fl = next(reader(L, f, 1, fps, tw, th))
        fr = next(reader(R, f - rs, 1, fpsr, tw, th))
        dd = np.clip(np.abs(fl.astype(np.int16) - fr.astype(np.int16)) * 4, 0, 255).astype(np.uint8)
        imgs[f] = (fl, fr, dd)
    per = 8
    sheets = []
    for s in range(0, len(picks), per):
        part = picks[s:s + per]
        sheet = Image.new("RGB", (3 * tw + 4 * 6, len(part) * (th + strip) + 30), (14, 14, 16))
        d = ImageDraw.Draw(sheet)
        d.text((8, 6), f"{labl} | {labr} | |difference| x4      {name}", fill=(220, 220, 220), font=F["mono"])
        for k, f in enumerate(part):
            y = 30 + k * (th + strip)
            r = next(x for x in rows if x["frame"] == f)
            d.text((8, y + 2), f"f{f}  {frame_to_tc(f, fps)}   mean |diff| {r['mae']:.2f}   p99 {r['p99']:.0f}",
                   fill=(255, 196, 0), font=F["mono_b"])
            for j, im in enumerate(imgs[f]):
                sheet.paste(Image.fromarray(im), (6 + j * (tw + 6), y + strip))
        p = out / f"{name}_sheet_{s // per + 1:02d}.jpg"
        sheet.save(p, quality=90)
        sheets.append(p)
    for p in sheets:
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
