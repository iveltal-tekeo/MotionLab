"""Graphics overlays: HTML / CSS / GSAP compositions rendered by HyperFrames (pinned in tools\\overlays\\) into
transparent ProRes 4444 clips that both the lab compositor (plan layer type "overlay") and the DaVinci Resolve build
(a plain clip on a video track - no Fusion) use. New graphics (titles, counters, lower thirds, shapes, glows,
particles) are written this way since 0.3.0.

    .venv\\Scripts\\python tools\\overlay.py new <folder> --frames 75 [--fps 25 --width 1520 --height 1080]
          a composition to edit: <folder>\\index.html (timing helpers in frames), gsap.min.js, overlay.json.
          <folder> = projects\\<project>\\build\\overlays\\<name> (size and fps = the plan's)
    .venv\\Scripts\\python tools\\overlay.py render <folder> [--workers N]
          -> <folder>\\<name>.mov (ProRes 4444 + alpha, exactly --frames frames) + its decoded cache; prints the plan
          layer to add: {"type": "overlay", "file": ..., "start": ..., "end": ...}; --mp4 = a stand-alone motion
          graphic that paints its own background -> <folder>\\<name>.mp4
    .venv\\Scripts\\python tools\\overlay.py stills <folder> 0,12,40     PNGs of rendered frames on a checkerboard,
          frame number + timecode burned in (look at these instead of the video)
    .venv\\Scripts\\python tools\\overlay.py check <folder>               HyperFrames lint
    .venv\\Scripts\\python tools\\overlay.py doctor                       Node.js, HyperFrames, its Chrome
    .venv\\Scripts\\python tools\\overlay.py install                      npm ci in tools\\overlays (the pinned versions) +
                                                                   HyperFrames' Chrome (Settings > Programs > Install)
Needs Node.js 22+ and `npm ci` in tools\\overlays (setup.bat does both). HyperFrames' anonymous telemetry is switched
off for every call (HYPERFRAMES_NO_TELEMETRY / DO_NOT_TRACK). Writes only inside projects\\<name>\\build\\ (or the
lab's .app\\ scratch); sources are never touched.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import overlays as OV  # noqa: E402
from motionlab.media import fonts  # noqa: E402
from motionlab.timecode import frame_to_tc  # noqa: E402
from motionlab.util import LAB, log, setup_console, tool  # noqa: E402

OVL = LAB / "tools" / "overlays"
HF = OVL / "node_modules" / "hyperframes" / "bin" / "hyperframes.mjs"
GSAP = OVL / "node_modules" / "gsap" / "dist" / "gsap.min.js"
RATIONAL = {23.976: "24000/1001", 29.97: "30000/1001", 59.94: "60000/1001", 47.952: "48000/1001"}

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=__W__, height=__H__">
<!-- MotionLab overlay "__NAME__": __FRAMES__ frames at __FPS__ fps, __W__ x __H__ px (the plan's frame). Render:
     .venv\\Scripts\\python tools\\overlay.py render <this folder>
     Rules: transparent background (never paint html / body / #root); everything absolutely positioned in output
     pixels; animate only on the paused GSAP timeline below (no CSS animations, timers, Date or Math.random -
     use rnd(seed) for noise); times in frames with F(n) / AT(n). -->
<script src="./gsap.min.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { width: __W__px; height: __H__px; overflow: hidden; background: transparent; }
  #root { position: relative; width: __W__px; height: __H__px; overflow: hidden; }
  .abs { position: absolute; }
  /* the graphic: */
  #box { left: 660px; top: 440px; width: 200px; height: 200px; background: #ffc400; opacity: 0; }
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="__SECS__" data-width="__W__"
     data-height="__H__">
  <div id="box" class="abs"></div>
</div>
<script>
  const FPS = __FPSJS__, FRAMES = __FRAMES__;
  const F = n => n / FPS;                 // frames -> seconds: tween positions and durations
  const AT = n => (n - 0.5) / FPS;        // a jump (tl.set) that shows from frame n on, never on frame n - 1
  const rnd = s => () => ((s = Math.imul(s ^ (s >>> 15), 2246822507) ^ Math.imul(s ^ (s >>> 13), 3266489909)) >>> 0) / 4294967296;
  const tl = gsap.timeline({ paused: true });
  // example (replace): pops in at frame 5, slides 120 px over 10 frames (slow end), gone from frame 60 on
  tl.set("#box", { opacity: 1 }, AT(5));
  tl.to("#box", { x: 120, duration: F(10), ease: "power2.out" }, F(5));
  tl.set("#box", { opacity: 0 }, AT(60));
  tl.set({}, {}, F(FRAMES));              // the timeline's length = the overlay's length
  window.__timelines = window.__timelines || {};
  window.__timelines["main"] = tl;
</script>
</body>
</html>
"""


def guard(folder: Path) -> Path:
    """Overlays live in a project's build folder (or the lab's .app scratch for tests) - never next to sources."""
    f = folder.resolve()
    projects, scratch = (LAB / "projects").resolve(), (LAB / ".app").resolve()
    ok = scratch in f.parents or (projects in f.parents and "build" in f.relative_to(projects).parts[1:2])
    if not ok:
        raise PermissionError(f"overlays go into projects\\<name>\\build\\overlays\\<overlay> (not {f})")
    return f


def fps_arg(fps: float) -> str:
    for k, v in RATIONAL.items():
        if abs(fps - k) < 2e-3:
            return v
    return f"{fps:g}"


def env() -> dict:
    return {**os.environ, "HYPERFRAMES_NO_TELEMETRY": "1", "DO_NOT_TRACK": "1", "HYPERFRAMES_SKIP_SKILLS": "1"}


def node() -> str:
    exe = shutil.which("node")
    if not exe:
        raise SystemExit("Node.js is not installed (needed for overlays): winget install OpenJS.NodeJS.LTS")
    return exe


def hf(*args: str, capture: bool = False, cwd: Path | None = None) -> subprocess.CompletedProcess:
    if not HF.exists():
        raise SystemExit(f"HyperFrames is not installed: cd tools\\overlays && npm ci   (expected {HF})")
    return subprocess.run([node(), str(HF), *args], cwd=str(cwd or OVL), env=env(), text=True,
                          capture_output=capture, encoding="utf-8", errors="replace")


def read_conf(folder: Path) -> dict:
    p = folder / "overlay.json"
    if not p.exists():
        raise SystemExit(f"no overlay.json in {folder} - make the folder with: overlay.py new {folder} --frames N")
    return json.loads(p.read_text(encoding="utf-8"))


def cmd_new(a) -> int:
    folder = guard(Path(a.folder))
    if (folder / "index.html").exists() and not a.force:
        raise SystemExit(f"{folder / 'index.html'} exists (--force replaces it)")
    folder.mkdir(parents=True, exist_ok=True)
    name = folder.name
    secs = a.frames / a.fps
    html = (TEMPLATE.replace("__NAME__", name).replace("__FRAMES__", str(a.frames)).replace("__FPSJS__", fps_arg(a.fps))
            .replace("__FPS__", f"{a.fps:g}").replace("__W__", str(a.width)).replace("__H__", str(a.height))
            .replace("__SECS__", f"{secs:.6f}".rstrip("0").rstrip(".")))
    (folder / "index.html").write_text(html, encoding="utf-8")
    shutil.copy2(GSAP, folder / "gsap.min.js")
    (folder / "hyperframes.json").write_text(json.dumps({"paths": {"assets": "assets"}}, indent=1), encoding="utf-8")
    (folder / "overlay.json").write_text(json.dumps({"name": name, "frames": a.frames, "fps": a.fps,
                                                     "width": a.width, "height": a.height}, indent=1),
                                         encoding="utf-8")
    print(folder / "index.html")
    return 0


def encode_prores(pattern: Path, fps: float, out: Path):
    """RGBA PNG frames -> ProRes 4444 with alpha, Rec.709 matrix and tags (what DaVinci Resolve expects; HyperFrames'
    own MOV output is converted with BT.601 and left untagged, so Resolve would shift its colours)."""
    r = subprocess.run([tool("ffmpeg"), "-v", "error", "-y", "-framerate", fps_arg(fps), "-start_number", "1",
                        "-i", str(pattern),
                        "-vf", f"scale=out_color_matrix=bt709:out_range=tv:flags={OV.ACCURATE},format=yuva444p10le",
                        "-c:v", "prores_ks", "-profile:v", "4444", "-alpha_bits", "16", "-vendor", "apl0",
                        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                        "-color_range", "tv", str(out)], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"ProRes encode failed: {r.stderr[-600:]}")


def cmd_render(a) -> int:
    folder = guard(Path(a.folder))
    c = read_conf(folder)
    W, H, fps = int(c["width"]), int(c["height"]), float(c["fps"])
    if a.mp4:                     # a stand-alone motion graphic (it paints its own background): just an MP4
        out = folder / f"{c['name']}.mp4"
        log(f"rendering {folder.name} as an MP4: {c['frames']} frames at {fps:g} fps, {W}x{H}")
        r = hf("render", str(folder), "--format", "mp4", "--fps", fps_arg(fps), "--output", str(out), "--quality",
               "delivery", "--quiet", "--workers", str(a.workers) if a.workers else "auto", "--strict",
               "--frames-cache-dir", "off")
        if r.returncode or not out.exists():
            raise SystemExit(f"HyperFrames render failed (exit {r.returncode}) - run: overlay.py check {folder}")
        info = OV.probe(out)
        log(f"{out.name}: {info['frames']} frames ({info['frames'] / fps:.2f} s)")
        print(out)
        return 0
    frames_dir = folder / "frames"
    shutil.rmtree(frames_dir, ignore_errors=True)
    log(f"rendering {folder.name}: {c['frames']} frames at {fps:g} fps, {W}x{H}")
    r = hf("render", str(folder), "--format", "png-sequence", "--fps", fps_arg(fps), "--output", str(frames_dir),
           "--quiet", "--workers", str(a.workers) if a.workers else "auto", "--strict", "--frames-cache-dir", "off")
    pngs = sorted(frames_dir.glob("frame_*.png"))
    if r.returncode or not pngs:
        raise SystemExit(f"HyperFrames render failed (exit {r.returncode}) - run: overlay.py check {folder}")
    if len(pngs) != c["frames"]:
        log(f"  WARNING: {len(pngs)} frames rendered, expected {c['frames']} - check data-duration in index.html")
    out = folder / f"{c['name']}.mov"
    tmp = folder / f"{c['name']}.part.mov"
    encode_prores(frames_dir / "frame_%06d.png", fps, tmp)
    os.replace(tmp, out)

    def frames():
        for p in pngs:
            im = Image.open(p)
            if im.size != (W, H):
                raise SystemExit(f"{p.name}: {im.size[0]}x{im.size[1]}, expected {W}x{H}")
            yield np.asarray(im.convert("RGBA"))
    m = OV.build_cache(out, frames, W, H, fps, "png")
    # the Resolve clip must hold the same pixels: decode a few frames back and compare with the PNGs
    worst = 0
    info = OV.probe(out)
    for i, fr in enumerate(OV._decoded(out, info)):
        if i in (0, len(pngs) // 2, len(pngs) - 1):
            png = np.asarray(Image.open(pngs[i]).convert("RGBA")).astype(np.int16)
            vis = png[..., 3] > 250
            if vis.any():
                worst = max(worst, int(np.abs(fr.astype(np.int16)[vis] - png[vis]).max()))
    shutil.rmtree(frames_dir, ignore_errors=True)
    x, y, w, h = m["crop"]
    log(f"{out.name}: {m['frames']} frames, visible area {w}x{h} at {x},{y}; ProRes 4444 vs the frames: max "
        f"{worst}/255 on opaque pixels")
    print(json.dumps({"type": "overlay", "id": c["name"], "start": 0, "end": m["frames"] - 1, "file": str(out),
                      "blend": "normal"}))
    print("(set start / end to the plan frames where it shows; end - start + 1 = its frames)")
    return 0


def checker(h: int, w: int, s: int = 16) -> np.ndarray:
    yy, xx = np.mgrid[0:h, 0:w]
    return np.where(((yy // s + xx // s) % 2)[..., None] == 0, 0.32, 0.22).astype(np.float32) * np.ones(3, np.float32)


def cmd_stills(a) -> int:
    folder = guard(Path(a.folder))
    c = read_conf(folder)
    mov = folder / f"{c['name']}.mov"
    m, arr = OV.load(mov)
    F = fonts(1.0)
    out = folder / "stills"
    out.mkdir(exist_ok=True)
    x, y, w, h = m["crop"]
    for f in [int(v) for v in a.frames.split(",")]:
        fr = np.asarray(arr[min(max(f, 0), m["frames"] - 1)], np.float32) / 255.0
        img = checker(m["height"], m["width"])
        reg = img[y:y + h, x:x + w]
        reg[:] = reg * (1 - fr[..., 3:]) + fr[..., :3] * fr[..., 3:]
        im = Image.fromarray((img * 255 + 0.5).astype(np.uint8))
        d = ImageDraw.Draw(im)
        d.text((12, 10), f"{c['name']}  f{f}  ({frame_to_tc(f, c['fps'])})", fill=(255, 196, 0), font=F["mono_b"])
        p = out / f"{c['name']}_f{f:04d}.png"
        im.save(p)
        print(p)
    return 0


def cmd_check(a) -> int:
    folder = guard(Path(a.folder))
    return hf("lint", str(folder)).returncode


def cmd_install(a) -> int:
    npm = shutil.which("npm")
    if not npm:
        raise SystemExit("Node.js / npm not found: winget install OpenJS.NodeJS.LTS, then restart MotionLab")
    log("installing HyperFrames (pinned in tools\\overlays\\package-lock.json) ...")
    r = subprocess.run([npm, "ci", "--no-fund", "--no-audit"], cwd=str(OVL), env=env())
    if r.returncode:
        raise SystemExit(f"npm ci failed (exit {r.returncode})")
    log("downloading HyperFrames' Chrome (about 150 MB, once) ...")
    if hf("browser", "ensure").returncode:
        raise SystemExit("could not download HyperFrames' Chrome - try again later")
    print("HyperFrames", hf("--version", capture=True).stdout.strip(), "installed - ready for overlays")
    return 0


def cmd_doctor(a) -> int:
    print("node:", shutil.which("node") or "NOT FOUND (winget install OpenJS.NodeJS.LTS)")
    if shutil.which("node"):
        print("  ", subprocess.run([node(), "--version"], capture_output=True, text=True).stdout.strip(),
              "(22 or newer needed)")
    print("HyperFrames:", HF if HF.exists() else "NOT INSTALLED (cd tools\\overlays && npm ci)")
    if HF.exists():
        print("  ", hf("--version", capture=True).stdout.strip())
        b = hf("browser", "path", capture=True)
        print("its Chrome:", b.stdout.strip().splitlines()[-1] if b.returncode == 0 and b.stdout.strip() else
              "not downloaded yet (overlay.py doctor --fix, or: npx hyperframes browser ensure in tools\\overlays)")
        if a.fix:
            hf("browser", "ensure")
    return 0


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("new")
    s.add_argument("folder")
    s.add_argument("--frames", type=int, required=True)
    s.add_argument("--fps", type=float, default=25.0)
    s.add_argument("--width", type=int, default=1520)
    s.add_argument("--height", type=int, default=1080)
    s.add_argument("--force", action="store_true")
    s = sub.add_parser("render")
    s.add_argument("folder")
    s.add_argument("--workers", type=int)
    s.add_argument("--mp4", action="store_true", help="an opaque MP4 (stand-alone motion graphic), no overlay clip")
    s = sub.add_parser("stills")
    s.add_argument("folder")
    s.add_argument("frames")
    s = sub.add_parser("check")
    s.add_argument("folder")
    sub.add_parser("install")
    s = sub.add_parser("doctor")
    s.add_argument("--fix", action="store_true", help="download HyperFrames' Chrome if missing")
    a = ap.parse_args()
    return {"new": cmd_new, "render": cmd_render, "stills": cmd_stills, "check": cmd_check,
            "doctor": cmd_doctor, "install": cmd_install}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
