"""Storyboard sheets: one sampled frame every N frames, each tile labelled with frame number + timecode.

    .venv\\Scripts\\python tools\\storyboard.py <project>                      every cached source of a project
    .venv\\Scripts\\python tools\\storyboard.py --video <file> --out <dir>     any video (read-only)
options: --every 25 (frames between samples), --start / --end (frame range), --cols 6, --tile 240 (px)
"""
from __future__ import annotations

import argparse
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import footage as FC  # noqa: E402
from motionlab.media import fonts  # noqa: E402
from motionlab.probe import probe  # noqa: E402
from motionlab.timecode import frame_to_tc  # noqa: E402
from motionlab.util import log, setup_console, tool  # noqa: E402


def make_sheets(tiles: list[tuple[np.ndarray, str]], out_dir: Path, prefix: str, title: str,
                cols: int = 6, tile_w: int = 240, rows: int = 6) -> list[Path]:
    F = fonts(0.9)
    h0, w0 = tiles[0][0].shape[:2]
    th = int(round(tile_w * h0 / w0))
    per = cols * rows
    out = []
    n_sheets = math.ceil(len(tiles) / per)
    for si in range(n_sheets):
        chunk = tiles[si * per:(si + 1) * per]
        r = math.ceil(len(chunk) / cols)
        W, H = cols * (tile_w + 6) + 6, 44 + r * (th + 26)
        sheet = Image.new("RGB", (W, H), (18, 18, 20))
        d = ImageDraw.Draw(sheet)
        d.text((8, 8), f"{title}   (sheet {si + 1}/{n_sheets})", fill=(235, 235, 235), font=F["title"])
        for i, (img, label) in enumerate(chunk):
            x, y = 6 + (i % cols) * (tile_w + 6), 44 + (i // cols) * (th + 26)
            im = Image.fromarray(img).convert("RGB").resize((tile_w, th), Image.LANCZOS)
            sheet.paste(im, (x, y))
            d.text((x + 2, y + th + 3), label, fill=(255, 196, 0), font=F["small"])
        p = out_dir / f"{prefix}_{si + 1:02d}.jpg"
        sheet.save(p, quality=88)
        out.append(p)
    return out


def video_tiles(path: Path, every: int, start: int, end: int | None, tile_w: int):
    info = probe(path)
    fps = info["video"]["avg_fps"] or info["video"]["r_fps"]
    w, h = info["video"]["display_width"], info["video"]["display_height"]
    tw = tile_w * 2
    th = int(round(tw * h / w / 2)) * 2
    vf = f"select='gte(n,{start})*not(mod(n-{start},{every}))',scale={tw}:{th}:flags=area"
    cmd = [tool("ffmpeg"), "-v", "error", "-nostdin", "-i", str(path), "-map", "0:v:0", "-vf", vf,
           "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    tiles, k = [], 0
    fs = tw * th * 3
    while True:
        buf = p.stdout.read(fs)
        if len(buf) < fs:
            break
        n = start + k * every
        if end is not None and n > end:
            break
        tiles.append((np.frombuffer(buf, np.uint8).reshape(th, tw, 3), f"f{n}  {frame_to_tc(n, fps)}"))
        k += 1
    p.stdout.close()
    p.kill()
    return tiles, fps


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project", nargs="?")
    ap.add_argument("--video")
    ap.add_argument("--out")
    ap.add_argument("--every", type=int, default=25)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int)
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--tile", type=int, default=240)
    a = ap.parse_args()
    if a.video:
        src = Path(a.video).resolve()
        out = Path(a.out).resolve()
        if out in (src, src.parent):
            raise SystemExit("--out must be a separate folder, not the source's own folder (sources are read-only)")
        out.mkdir(parents=True, exist_ok=True)
        tiles, fps = video_tiles(src, a.every, a.start, a.end, a.tile)
        for p in make_sheets(tiles, out, "story", f"{src.name}  every {a.every} f @ {fps:g} fps",
                             a.cols, a.tile):
            print(p)
        return 0
    from motionlab.project import Project
    from prep_footage import load_cache
    prj = Project(a.project)
    out = prj.check(prj.build / "boards")
    out.mkdir(parents=True, exist_ok=True)
    for sid in sorted(prj.manifest()["sources"]):
        if not any(FC.paths(prj.cache, sid, c)[1].exists() for c in (True, False)):
            continue
        m, arr, st = load_cache(prj, sid)                      # the colour cache when there is one
        end = m["frames"] - 1 if a.end is None else min(a.end, m["frames"] - 1)
        idx = list(range(a.start, end + 1, a.every))
        tiles = [(FC.image(m, arr, i), f"{sid} f{i}  {frame_to_tc(i, m['fps'])}") for i in idx]
        title = f"{sid} = {m['name']}  ({m['frames']} f @ {m['fps']:g} fps = {m['frames'] / m['fps']:.1f}s)"
        for p in make_sheets(tiles, out, f"{sid}", title, a.cols, a.tile):
            print(p)
        log(f"{sid}: {len(tiles)} tiles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
