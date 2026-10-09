"""Render a MotionLab plan (plan.json) to video, stills or contact sheets; build side-by-side comparisons.

    .venv\\Scripts\\python tools\\render_video.py <plan.json>                       full render -> plan["output"]
    .venv\\Scripts\\python tools\\render_video.py <plan.json> --range 300 420       part of the timeline
    ... --workers N   parallel processes for a render (default: half the CPUs, at most 8; 1 = one process)
    .venv\\Scripts\\python tools\\render_video.py <plan.json> --sheet 0:3895:25     contact sheet of rendered frames
    .venv\\Scripts\\python tools\\render_video.py <plan.json> --stills 480,1633     PNG stills
    .venv\\Scripts\\python tools\\render_video.py <plan.json> --compare             reference | render side by side
    .venv\\Scripts\\python tools\\render_video.py <plan.json> --compare --left <a.mp4> --right <b.mp4>  any two
Every output goes next to the plan (its build folder; side-by-sides in build\\compare\\); sources and the
reference are only read.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab.compose import Renderer  # noqa: E402
from motionlab.media import fonts  # noqa: E402
from motionlab.timecode import frame_to_tc  # noqa: E402
from motionlab.util import log, setup_console, tool  # noqa: E402


def _guard(out: Path, plan_path: Path, plan: dict) -> Path:
    out = out.resolve()
    build = plan_path.resolve().parent
    if build != out.parent and build not in out.parents:
        raise PermissionError(f"refusing to write outside {build}: {out}")
    protected = [Path(s.get("source", "")).resolve() for s in plan["sources"].values() if s.get("source")]
    if plan.get("audio", {}).get("path"):
        protected.append(Path(plan["audio"]["path"]).resolve())
    if out in protected:
        raise PermissionError(f"refusing to overwrite a source: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


def encoder(out: Path, W: int, H: int, fps: float, audio: dict | None, a0: int, crf: int, preset: str,
            threads: int | None = None):
    cmd = [tool("ffmpeg"), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", f"{fps:g}", "-i", "-"]
    if audio and audio.get("path"):
        cmd += ["-ss", f"{a0 / fps:.6f}", "-i", str(audio["path"]), "-map", "0:v", "-map", "1:a:0"]
    cmd += ["-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p", "-c:v", "libx264", "-preset", preset,
            "-crf", str(crf), "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-color_range", "tv", "-movflags", "+faststart"]
    if audio and audio.get("path"):
        cmd += ["-c:a", "copy", "-shortest"] if audio.get("trim_to_video", True) else ["-c:a", "copy"]
    if threads:
        cmd += ["-threads", str(threads)]
    cmd += [str(out)]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def render_range(R: Renderer, plan: dict, out: Path, a: int, b: int, crf: int, preset: str):
    p = encoder(out, R.W, R.H, R.fps, plan.get("audio"), a, crf, preset)
    t0 = time.time()
    try:
        for f in range(a, b + 1):
            p.stdin.write(R.render(f).tobytes())
            if (f - a + 1) % 200 == 0:
                el = time.time() - t0
                rate = (f - a + 1) / el
                log(f"  f{f} {frame_to_tc(f, R.fps)}  {rate:.1f} fps, ~{(b - f) / rate:.0f}s left")
    finally:
        p.stdin.close()
        p.wait()
    log(f"wrote {out} ({b - a + 1} frames in {time.time() - t0:.0f}s)")


def default_workers() -> int:
    """Parallel render processes: half the logical CPUs (each also runs an encoder), at most 8."""
    return max(1, min(8, (os.cpu_count() or 2) // 2))


def _render_part(plan_path: str, s0: int, s1: int, seg: str, crf: int, preset: str) -> tuple[int, int, float]:
    """One worker process: frames s0..s1 of the plan -> a video-only segment (only the layers that touch them)."""
    import cv2
    cv2.setNumThreads(1)                                   # the parallelism is the processes
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    plan["layers"] = [L for L in plan["layers"] if int(L["end"]) >= s0 and int(L["start"]) <= s1]
    t0 = time.time()
    R = Renderer(plan)
    p = encoder(Path(seg), R.W, R.H, R.fps, None, s0, crf, preset, threads=2)
    try:
        for f in range(s0, s1 + 1):
            p.stdin.write(R.render(f).tobytes())
    finally:
        p.stdin.close()
        p.wait()
    if p.returncode:
        raise RuntimeError(f"ffmpeg failed on the segment f{s0}-{s1}")
    return s0, s1, time.time() - t0


def render_parallel(plan_path: Path, plan: dict, out: Path, a: int, b: int, crf: int, preset: str, workers: int):
    """Frames a..b in `workers` processes, each encoding its own chunk; the chunks are joined without re-encoding
    (every chunk starts on a keyframe) and the soundtrack is added once. Same frames as a single-process render:
    the compositor is deterministic per frame (noise is seeded by plan seed + frame)."""
    from concurrent.futures import ProcessPoolExecutor, as_completed
    n = b - a + 1
    k = max(1, min(workers, n // 40))                      # at least ~40 frames per chunk
    edges = [a + round(i * n / k) for i in range(k + 1)]
    parts = [(edges[i], edges[i + 1] - 1) for i in range(k)]
    tmp = _guard(out.parent / f"{out.stem}_parts", plan_path, plan)
    tmp.mkdir(parents=True, exist_ok=True)
    segs = [tmp / f"part_{i:03d}_{s0}-{s1}.mp4" for i, (s0, s1) in enumerate(parts)]
    fps = float(plan["fps"])
    log(f"rendering f{a}-f{b} ({n} frames) in {k} parallel parts")
    t0 = time.time()
    done = 0
    with ProcessPoolExecutor(max_workers=k) as ex:
        futs = [ex.submit(_render_part, str(plan_path), s0, s1, str(seg), crf, preset)
                for (s0, s1), seg in zip(parts, segs)]
        for fu in as_completed(futs):
            s0, s1, sec = fu.result()
            done += s1 - s0 + 1
            el = time.time() - t0
            log(f"  part f{s0}-f{s1} {frame_to_tc(s0, fps)} done ({sec:.0f}s) - {done}/{n} frames, "
                f"{done / el:.1f} fps overall, ~{(n - done) / max(done / el, 1e-6):.0f}s left")
    lst = tmp / "parts.txt"
    lst.write_text("".join(f"file '{s.name}'\n" for s in segs), encoding="utf-8")
    audio = plan.get("audio") or {}
    cmd = [tool("ffmpeg"), "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst)]
    if audio.get("path"):
        cmd += ["-ss", f"{a / fps:.6f}", "-i", str(audio["path"]), "-map", "0:v", "-map", "1:a:0", "-c:v", "copy",
                "-c:a", "copy"] + (["-shortest"] if audio.get("trim_to_video", True) else [])
    else:
        cmd += ["-map", "0:v", "-c:v", "copy"]
    cmd += ["-movflags", "+faststart", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"joining the parts failed: {r.stderr[-800:]}")
    for s in segs + [lst]:
        s.unlink(missing_ok=True)
    tmp.rmdir()
    el = time.time() - t0
    log(f"wrote {out} ({n} frames in {el:.0f}s = {n / el:.1f} fps with {k} parts)")


def sheet(R: Renderer, frames: list[int], out: Path, title: str, cols: int = 6, tile_w: int = 240):
    from storyboard import make_sheets
    tiles = [(R.render(f), f"f{f}  {frame_to_tc(f, R.fps)}") for f in frames]
    return make_sheets(tiles, out.parent, out.stem, title, cols, tile_w)


def compare(ref: Path, ours: Path, out: Path, fps: float, n: int, label_l: str, label_r: str, crf: int = 20,
            first: int = 0, ours_first: int = 0):
    """reference | render, each 760 px wide, with a strip showing frame number + timecode on every frame.
    first = timeline frame of the first compared frame: the left video is read from there, the right one from its
    frame `first - ours_first` (a section render starting at `first` has ours_first = first)."""
    w, h, strip = 760, 540, 34

    def seek(v, f0):
        return ["-ss", f"{f0 / fps:.6f}"] if f0 > 0 else []

    dec = [subprocess.Popen([tool("ffmpeg"), "-v", "error", "-nostdin", *seek(v, f0), "-i", str(v), "-map", "0:v:0",
                             "-vf", f"scale={w}:{h}:flags=area", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                            stdout=subprocess.PIPE) for v, f0 in ((ref, first), (ours, first - ours_first))]
    enc = subprocess.Popen([tool("ffmpeg"), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                            f"{2 * w}x{h + strip}", "-r", f"{fps:g}", "-i", "-", *seek(ref, first), "-i", str(ref),
                            "-map", "0:v", "-map", "1:a:0?", "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
                            "-pix_fmt", "yuv420p", *(["-c:a", "copy"] if first == 0 else ["-c:a", "aac", "-b:a", "192k"]),
                            "-shortest", "-movflags", "+faststart", str(out)],
                           stdin=subprocess.PIPE)
    F = fonts(1.0)
    fs = w * h * 3
    try:
        for f in range(n):
            bufs = [d.stdout.read(fs) for d in dec]
            if any(len(b) < fs for b in bufs):
                break
            img = Image.new("RGB", (2 * w, h + strip), (14, 14, 16))
            img.paste(Image.frombuffer("RGB", (w, h), bufs[0]), (0, strip))
            img.paste(Image.frombuffer("RGB", (w, h), bufs[1]), (w, strip))
            d = ImageDraw.Draw(img)
            d.text((10, 8), label_l, fill=(200, 200, 200), font=F["mono"])
            d.text((w + 10, 8), label_r, fill=(200, 200, 200), font=F["mono"])
            lab = f"f{first + f}  {frame_to_tc(first + f, fps)}"
            lw = d.textlength(lab, font=F["mono_b"])
            d.text((w - lw - 12, 8), lab, fill=(255, 196, 0), font=F["mono_b"])
            d.text((2 * w - lw - 12, 8), lab, fill=(255, 196, 0), font=F["mono_b"])
            enc.stdin.write(img.tobytes())
    finally:
        enc.stdin.close()
        enc.wait()
        for d in dec:
            d.kill()
    log(f"wrote {out}")


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--range", nargs=2, type=int)
    ap.add_argument("--sheet")
    ap.add_argument("--stills")
    ap.add_argument("--compare", action="store_true")
    ap.add_argument("--left", help="--compare: left video (default: the plan's reference)")
    ap.add_argument("--right", help="--compare: right video (default: the plan's render)")
    ap.add_argument("--out")
    ap.add_argument("--crf", type=int, default=16)
    ap.add_argument("--preset", default="medium")
    ap.add_argument("--workers", type=int, default=default_workers(), help="parallel render processes")
    a = ap.parse_args()
    plan_path = Path(a.plan).resolve()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    build = plan_path.parent
    name = plan.get("name", plan_path.stem)
    if a.compare:
        if a.right:
            ours = Path(a.right).resolve()
        else:
            ours = Path(plan.get("output", build / f"{name}.mp4"))
            if not ours.is_absolute():
                ours = build / ours
        left = Path(a.left).resolve() if a.left else Path(plan["reference"])
        for v in (left, ours):
            if not v.exists():
                raise SystemExit(f"video not found: {v}")
        # --range A B: compare frames A..B only; a --right video is then a section render starting at frame A
        first, n = (a.range[0], a.range[1] - a.range[0] + 1) if a.range else (0, int(plan["frames"]))
        rng = f"_{a.range[0]}-{a.range[1]}" if a.range else ""
        if a.left or a.right:
            out = _guard(build / "compare" / f"{ours.stem}_vs_{left.stem[:24]}{rng}.mp4", plan_path, plan)
            ll, rl = f"LEFT  {left.stem[:30]}", f"RIGHT  {ours.stem[:30]}"
        else:
            out = _guard(build / "compare" / f"{name}_compare{rng}.mp4", plan_path, plan)
            ll, rl = f"REFERENCE  {left.stem[:28]}", f"RENDER  {name}"
        compare(left, ours, out, float(plan["fps"]), n, ll, rl, first=first,
                ours_first=first if (a.range and a.right) else 0)
        return 0
    t0 = time.time()
    R = Renderer(plan)
    log(f"plan {name}: {len(R.layers)} layers, {R.N} frames, set-up {time.time() - t0:.1f}s")
    if a.stills:
        frames = [int(v) for v in a.stills.split(",")]
        for f in frames:
            p = _guard(build / "stills" / f"{name}_f{f:05d}.png", plan_path, plan)
            Image.fromarray(R.render(f)).save(p)
            print(p)
        return 0
    if a.sheet:
        s0, s1, st = (int(v) for v in a.sheet.split(":"))
        out = _guard(build / "sheets" / f"{name}_{s0}-{s1}", plan_path, plan)
        for p in sheet(R, list(range(s0, s1 + 1, st)), out, f"{name}  f{s0}-{s1} every {st}"):
            print(p)
        return 0
    s0, s1 = (a.range if a.range else (0, R.N - 1))
    out = Path(a.out) if a.out else Path(plan.get("output", f"{name}.mp4"))
    if not out.is_absolute():
        out = build / out
    if a.range:
        out = out.with_name(f"{out.stem}_{s0}-{s1}{out.suffix}")
    out = _guard(out, plan_path, plan)
    if a.workers > 1 and s1 - s0 + 1 >= 80:
        del R                                              # the workers build their own renderers
        render_parallel(plan_path, plan, out, s0, s1, a.crf, a.preset, a.workers)
    else:
        render_range(R, plan, out, s0, s1, a.crf, a.preset)
    return 0


if __name__ == "__main__":
    sys.exit(main())
