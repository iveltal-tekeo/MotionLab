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
    .venv\\Scripts\\python tools\\overlay.py new <folder> --from <graphic>   a copy of a library graphic or an example
    .venv\\Scripts\\python tools\\overlay.py settings <folder>           what the user can change (declared on <html>,
          data-composition-variables; render passes overlay.json's "values"; render.json + thumb.png record it)
    .venv\\Scripts\\python tools\\overlay.py set <folder> text="NEW" color=#ff0000     then render again
    .venv\\Scripts\\python tools\\overlay.py save <folder> [--name N]     a rendered, approved overlay -> library\\graphics\\
    .venv\\Scripts\\python tools\\overlay.py graphics                    the graphics library (yours + the examples)
    .venv\\Scripts\\python tools\\overlay.py refresh <folder>        swap it in the project open in DaVinci Resolve
          (MediaPoolItem.ReplaceClip; position, length, transform, opacity, composite mode stay). Resolve locks the
          files it uses, so it always gets a numbered copy <folder>\\resolve\\<name>_<id>.mov (resolve-clip <folder>
          makes one to drag in by hand); <name>.mov stays free to render again
    .venv\\Scripts\\python tools\\overlay.py captions <folder> --from <file.srt | .vtt | transcript.json | a video>
          [--names "MotionLab, 4AM"] [--model small|base] [--render]   (a video = its words by speech to text)
          captions timed to the words (styles + settings like any graphic) + <name>.srt for Resolve's subtitle track;
          rate / size / length from the project's newest edit plan (or --fps --width --height --frames)
    .venv\\Scripts\\python tools\\overlay.py stills <folder> 0,12,40     PNGs of rendered frames on a checkerboard,
          frame number + timecode burned in (look at these instead of the video)
    .venv\\Scripts\\python tools\\overlay.py check <folder>               HyperFrames lint
    .venv\\Scripts\\python tools\\overlay.py doctor                       Node.js, HyperFrames, its Chrome
    .venv\\Scripts\\python tools\\overlay.py install                      npm ci in tools\\overlays (the pinned versions) +
                                                                   HyperFrames' Chrome (Settings > Programs > Install)
    .venv\\Scripts\\python tools\\overlay.py versions                     pinned / installed / newest HyperFrames + GSAP
    .venv\\Scripts\\python tools\\overlay.py upgrade-test [<ver>] [--gsap <ver>|latest] [--quick]
          installs a newer HyperFrames in .app\\dev\\hf-upgrade (scratch), renders tools\\overlays\\examples with it
          and with the pinned one, compares every frame (max 4/255) and the render time; PASS -> pin
    .venv\\Scripts\\python tools\\overlay.py pin <ver> [--gsap <ver>]    adopt a tested version (package.json + lock)
Needs Node.js 22+ and `npm ci` in tools\\overlays (setup.bat does both). HyperFrames' anonymous telemetry is switched
off for every call (HYPERFRAMES_NO_TELEMETRY / DO_NOT_TRACK). Writes only inside projects\\<name>\\build\\ (or the
lab's .app\\ scratch); sources are never touched.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import overlay_settings as OS  # noqa: E402
from motionlab import overlays as OV  # noqa: E402
from motionlab.media import fonts  # noqa: E402
from motionlab.timecode import frame_to_tc  # noqa: E402
from motionlab.util import LAB, log, setup_console, tool  # noqa: E402

OVL = LAB / "tools" / "overlays"
HF = OVL / "node_modules" / "hyperframes" / "bin" / "hyperframes.mjs"
GSAP = OVL / "node_modules" / "gsap" / "dist" / "gsap.min.js"
RATIONAL = {23.976: "24000/1001", 29.97: "30000/1001", 59.94: "60000/1001", 47.952: "48000/1001"}

TEMPLATE = """<!doctype html>
<html lang="en" data-composition-variables='[
  {"id": "color", "type": "color", "label": "Colour", "default": "#ffc400"},
  {"id": "pop_in", "type": "number", "label": "Pops in at frame", "default": 5, "min": 0, "max": __LAST__, "step": 1}
]'>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=__W__, height=__H__">
<!-- MotionLab overlay "__NAME__": __FRAMES__ frames at __FPS__ fps, __W__ x __H__ px (the plan's frame). Render:
     .venv\\Scripts\\python tools\\overlay.py render <this folder>
     Rules: transparent background (never paint html / body / #root); everything absolutely positioned in output
     pixels; animate only on the paused GSAP timeline below (no CSS animations, timers, Date or Math.random -
     use rnd(seed) for noise); times in frames with F(n) / AT(n).
     Settings the user can change in the app (Videos > Graphics): declare them on <html> above
     (data-composition-variables: string / color / number / boolean / enum; times in frames) and read them from V. -->
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
  const V = window.__hyperframes.getVariables();   // the settings (declared defaults + the user's values)
  const tl = gsap.timeline({ paused: true });
  // example (replace): pops in at frame V.pop_in, slides 120 px over 10 frames (slow end), gone from frame 60 on
  document.getElementById("box").style.background = V.color;
  tl.set("#box", { opacity: 1 }, AT(V.pop_in));
  tl.to("#box", { x: 120, duration: F(10), ease: "power2.out" }, F(V.pop_in));
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


def copy_sources(src: Path, dst: Path, name: str, extra: dict | None = None) -> dict:
    """An overlay's sources (index.html, hyperframes.json, assets\\ + the pinned GSAP) and its overlay.json -> dst."""
    c = OS.conf(src)
    dst.mkdir(parents=True, exist_ok=True)
    for f in OS.SOURCES:
        if f != "overlay.json" and (src / f).exists():
            shutil.copy2(src / f, dst / f)
    if GSAP.exists():
        shutil.copy2(GSAP, dst / "gsap.min.js")
    if (src / "assets").is_dir():
        shutil.copytree(src / "assets", dst / "assets", dirs_exist_ok=True)
    if not (dst / "hyperframes.json").exists():
        (dst / "hyperframes.json").write_text(json.dumps({"paths": {"assets": "assets"}}, indent=1), encoding="utf-8")
    c = {**c, "name": name, **(extra or {})}
    (dst / "overlay.json").write_text(json.dumps(c, indent=1, ensure_ascii=False), encoding="utf-8")
    return c


def cmd_new(a) -> int:
    folder = guard(Path(a.folder))
    if (folder / "index.html").exists() and not a.force:
        raise SystemExit(f"{folder / 'index.html'} exists (--force replaces it)")
    if a.from_:
        try:
            src = OS.find_graphic(a.from_)
        except ValueError as e:
            raise SystemExit(str(e))
        c = copy_sources(src, folder, folder.name, {"from": a.from_})
        log(f"{folder.name}: a copy of the graphic '{a.from_}' ({c['frames']} frames at {float(c['fps']):g} fps, "
            f"{c['width']}x{c['height']}); change its settings in the app or with overlay.py set, then render")
        print(folder / "index.html")
        if a.render:
            return cmd_render(argparse.Namespace(folder=str(folder), workers=None, mp4=False))
        return 0
    if not a.frames:
        raise SystemExit("--frames N is needed (or --from <graphic>)")
    folder.mkdir(parents=True, exist_ok=True)
    name = folder.name
    secs = a.frames / a.fps
    html = (TEMPLATE.replace("__NAME__", name).replace("__FRAMES__", str(a.frames)).replace("__FPSJS__", fps_arg(a.fps))
            .replace("__FPS__", f"{a.fps:g}").replace("__W__", str(a.width)).replace("__H__", str(a.height))
            .replace("__SECS__", f"{secs:.6f}".rstrip("0").rstrip(".")).replace("__LAST__", str(a.frames - 1)))
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


def variables_args(folder: Path) -> tuple[list[str], dict, Path | None]:
    """--variables-file for HyperFrames when the composition declares settings: (args, values, temp file)."""
    try:
        decl = OS.declared(folder)
    except ValueError as e:
        raise SystemExit(str(e))
    if not decl:
        return [], {}, None
    vals = OS.values(folder)
    _, bad = OS.check(decl, read_conf(folder).get("values") or {})
    if bad:
        log("  WARNING: overlay.json values not used: " + "; ".join(bad))
    vf = folder / ".values.json"
    vf.write_text(json.dumps(vals, ensure_ascii=False), encoding="utf-8")
    return ["--variables-file", str(vf), "--strict-variables"], vals, vf


def write_thumb(folder: Path, png: Path, crop: list[int], box=(480, 270)) -> None:
    """thumb.png: one rendered frame on a checkerboard, cut to the area that is ever visible (+ a margin)."""
    im = np.asarray(Image.open(png).convert("RGBA"), np.float32) / 255.0
    x, y, w, h = crop
    m = 24
    x0, y0 = max(0, x - m), max(0, y - m)
    x1, y1 = min(im.shape[1], x + w + m), min(im.shape[0], y + h + m)
    fr = im[y0:y1, x0:x1]
    bg = checker(fr.shape[0], fr.shape[1])
    out = bg * (1 - fr[..., 3:]) + fr[..., :3] * fr[..., 3:]
    t = Image.fromarray((out * 255 + 0.5).astype(np.uint8))
    t.thumbnail(box, Image.LANCZOS)
    t.save(folder / "thumb.png")


def write_render_info(folder: Path, vals: dict, frames: int) -> None:
    from motionlab import upstream as UP
    pins = UP.pinned()
    (folder / "render.json").write_text(json.dumps({
        "inputs": OS.inputs_hash(folder), "values": vals, "frames": frames, "date": time.strftime("%Y-%m-%d %H:%M"),
        "hyperframes": pins.get("hyperframes"), "gsap": pins.get("gsap")}, indent=1, ensure_ascii=False),
        encoding="utf-8")


def cmd_render(a) -> int:
    folder = guard(Path(a.folder))
    c = read_conf(folder)
    W, H, fps = int(c["width"]), int(c["height"]), float(c["fps"])
    vargs, vals, vfile = variables_args(folder)
    if vals:
        log("settings: " + ", ".join(f"{k} = {v!r}" for k, v in vals.items()))
    if a.mp4:                     # a stand-alone motion graphic (it paints its own background): just an MP4
        out = folder / f"{c['name']}.mp4"
        log(f"rendering {folder.name} as an MP4: {c['frames']} frames at {fps:g} fps, {W}x{H}")
        r = hf("render", str(folder), "--format", "mp4", "--fps", fps_arg(fps), "--output", str(out), "--quality",
               "delivery", "--quiet", "--workers", str(a.workers) if a.workers else "auto", "--strict",
               "--frames-cache-dir", "off", *vargs)
        if vfile:
            vfile.unlink(missing_ok=True)
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
           "--quiet", "--workers", str(a.workers) if a.workers else "auto", "--strict", "--frames-cache-dir", "off",
           *vargs)
    if vfile:
        vfile.unlink(missing_ok=True)
    pngs = sorted(frames_dir.glob("frame_*.png"))
    if r.returncode or not pngs:
        raise SystemExit(f"HyperFrames render failed (exit {r.returncode}) - run: overlay.py check {folder}")
    if len(pngs) != c["frames"]:
        log(f"  WARNING: {len(pngs)} frames rendered, expected {c['frames']} - check data-duration in index.html")
    out = folder / f"{c['name']}.mov"
    tmp = folder / f"{c['name']}.part.mov"
    encode_prores(frames_dir / "frame_%06d.png", fps, tmp)
    try:
        os.replace(tmp, out)
    except PermissionError:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"{out.name} is open in another program - DaVinci Resolve keeps the clips it uses open, so it "
                         f"cannot be replaced. Run `overlay.py refresh {folder}` (or the Graphics tab's Swap in "
                         f"DaVinci Resolve): Resolve moves to a numbered copy and {out.name} is free; then render again.")

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
    write_thumb(folder, pngs[len(pngs) // 2], m["crop"])
    write_render_info(folder, vals, len(pngs))
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


def cmd_settings(a) -> int:
    folder = guard(Path(a.folder))
    s = OS.status(folder)
    if not s["settings"]:
        print(f"{s['name']}: no settings declared (data-composition-variables on <html> in index.html)")
    for d in s["settings"]:
        extra = f"  (one of {', '.join(str(o['value']) for o in d['options'])})" if d["type"] == "enum" else ""
        dflt = "" if d["value"] == d.get("default") else f"   (default {d.get('default')!r})"
        print(f"  {d['id']:16s} {d['type']:8s} {d.get('label', ''):28s} = {d['value']!r}{dflt}{extra}")
    state = "up to date" if s["current"] else ("needs a re-render" if s["rendered"] else "not rendered yet")
    print(f"render: {state}")
    return 0


def cmd_set(a) -> int:
    folder = guard(Path(a.folder))
    decl = {d["id"]: d for d in OS.declared(folder)}
    new = {}
    for kv in a.values:
        k, sep, v = kv.partition("=")
        if not sep or k not in decl:
            raise SystemExit(f"'{kv}': use id=value with one of: {', '.join(decl) or '(none declared)'}")
        new[k] = v
    try:
        s = OS.set_values(folder, new)
    except ValueError as e:
        raise SystemExit(str(e))
    print(f"{s['name']}: saved {', '.join(f'{k}={v}' for k, v in new.items())} - render it again "
          f"(overlay.py render {folder})")
    return 0


def cmd_save(a) -> int:
    """An approved overlay -> library\\graphics\\<name>\\ (sources + the rendered .mov + thumb)."""
    folder = guard(Path(a.folder))
    s = OS.status(folder)
    if not s["current"]:
        raise SystemExit(f"{s['name']}: render it first (overlay.py render {folder}) - the library keeps the "
                         "rendered clip next to its sources")
    name = a.name or s["name"]
    if not re.fullmatch(r"[\w.-]+", name):
        raise SystemExit(f"not a usable name: {name!r} (letters, digits, - _ .)")
    dst = OS.LIBRARY / name
    if dst.exists() and not a.force:
        raise SystemExit(f"library\\graphics\\{name} exists (--force replaces it, or --name another)")
    tmp = OS.LIBRARY / f".{name}.part"
    shutil.rmtree(tmp, ignore_errors=True)
    c = read_conf(folder)
    copy_sources(folder, tmp, name, {"saved_from": OS.rel(folder), "saved": time.strftime("%Y-%m-%d %H:%M")})
    shutil.copy2(folder / f"{c['name']}.mov", tmp / f"{name}.mov")
    for f in ("thumb.png", "render.json"):
        if (folder / f).exists():
            shutil.copy2(folder / f, tmp / f)
    if (tmp / "render.json").exists():              # the copy is current: the same inputs under its new name
        rj = json.loads((tmp / "render.json").read_text(encoding="utf-8"))
        rj["inputs"] = OS.inputs_hash(tmp)
        (tmp / "render.json").write_text(json.dumps(rj, indent=1, ensure_ascii=False), encoding="utf-8")
    shutil.rmtree(dst, ignore_errors=True)
    os.replace(tmp, dst)
    log(f"saved to the graphics library: {dst} ({s['frames']} frames, {s['width']}x{s['height']} at {s['fps']:g} fps)")
    print(f"In DaVinci Resolve: drag {dst / (name + '.mov')} into a Power Bin to have it in every project.")
    return 0


def retime(folder: Path, fps: float, frames: int, width: int, height: int) -> None:
    """Set a size-independent composition's rate, length and size (the captions graphic): its FPS / FRAMES and W / H
    constants, data-duration / -width / -height, the viewport and the page size."""
    import re as _re
    p = folder / "index.html"
    t = p.read_text(encoding="utf-8")
    secs = f"{frames / fps:.6f}".rstrip("0").rstrip(".")
    subs = [(r"const FPS = [\d./]+, FRAMES = \d+;", f"const FPS = {fps_arg(fps)}, FRAMES = {frames};"),
            (r"const W = \d+, H = \d+;", f"const W = {width}, H = {height};"),
            (r'data-duration="[\d.]+"', f'data-duration="{secs}"'),
            (r'data-width="\d+"', f'data-width="{width}"'), (r'data-height="\d+"', f'data-height="{height}"'),
            (r'content="width=\d+, height=\d+"', f'content="width={width}, height={height}"'),
            (r"width: \d+px; height: \d+px;", f"width: {width}px; height: {height}px;")]
    for pat, new in subs:
        t, n = _re.subn(pat, new, t)
        if not n:
            raise SystemExit(f"{p}: no '{pat}' to set - not a size-independent graphic (start from --from captions)")
    p.write_text(t, encoding="utf-8")


def _plan_of(folder: Path) -> dict:
    """The newest edit plan of the project an overlay folder belongs to (projects\\<p>\\build\\overlays\\<o>)."""
    build = folder.parent.parent
    plans = sorted(build.glob("plan_v*.json"), key=lambda q: int(q.stem.split("_v")[-1])
                   if q.stem.split("_v")[-1].isdigit() else 0)
    return json.loads(plans[-1].read_text(encoding="utf-8")) if plans else {}


def cmd_captions(a) -> int:
    """Captions timed to the words: <folder> becomes (or stays) a copy of the captions graphic, its words come from
    an SRT / WebVTT / lab transcript.json; writes assets\\captions.js, <name>.srt (for Resolve's subtitle track) and
    sets the rate, size and length (default: the project's newest edit plan - captions over the whole edit)."""
    from motionlab import captions as CAP
    from motionlab import speech as SP
    folder = guard(Path(a.folder))
    plan = _plan_of(folder)
    src = Path(a.from_)
    vid = {}
    if src.suffix.lower() not in (".srt", ".vtt", ".json"):           # a video / audio: its words, by speech to text
        if not src.is_file():
            raise SystemExit(f"no such file: {src}")
        import speech as SPT                                            # tools\speech.py (cached per settings)
        tj, _ = SPT.transcript(src, a.model, a.names or "", a.lang)
        vid = SP.probe(src)
        src = tj
    new = not (folder / "index.html").exists()
    if new:
        copy_sources(OS.EXAMPLES / "captions", folder, folder.name, {"from": "captions"})
    c = read_conf(folder)
    if "captions" not in c and not new:
        raise SystemExit(f"{folder.name} is not a captions graphic (make a new folder for the captions)")
    fps = float(a.fps or plan.get("fps") or vid.get("fps") or c.get("fps") or 25)
    W = int(a.width or plan.get("width") or (vid.get("width") if vid.get("has_video") else 0) or c.get("width") or 1920)
    H = int(a.height or plan.get("height") or (vid.get("height") if vid.get("has_video") else 0) or c.get("height")
            or 1080)
    try:
        words, est, what = CAP.load(src)
    except ValueError as e:
        raise SystemExit(str(e))
    cues = CAP.in_frames(CAP.group(words, max_chars=a.max_chars, max_words=a.max_words), fps, a.offset)
    if not cues:
        raise SystemExit("no words to show")
    frames = int(a.frames or plan.get("frames") or vid.get("frames") or cues[-1]["f1"] + 1)
    cues = [q for q in cues if q["f0"] < frames]
    if cues and cues[-1]["f1"] >= frames:
        cues[-1]["f1"] = frames - 1
        for w in cues[-1]["words"]:
            w["f0"], w["f1"] = min(w["f0"], frames - 1), min(w["f1"], frames - 1)
    (folder / "assets").mkdir(exist_ok=True)
    (folder / "assets" / "captions.js").write_text(CAP.captions_js(cues, fps, Path(a.from_).name, est),
                                                   encoding="utf-8", newline="\n")
    srt = folder / f"{c['name']}.srt"
    srt.write_text(CAP.srt(cues, fps), encoding="utf-8")
    retime(folder, fps, frames, W, H)
    c.update({"fps": fps, "frames": frames, "width": W, "height": H,
              "captions": {"from": str(Path(a.from_).resolve()), "what": what, "words": sum(len(q["words"]) for q in cues),
                           "cues": len(cues), "estimated": est, "offset": a.offset,
                           **({"speech": {"model": a.model, "names": a.names or ""}} if vid else {})}})
    (folder / "overlay.json").write_text(json.dumps(c, indent=1, ensure_ascii=False), encoding="utf-8")
    log(f"{folder.name}: {len(cues)} captions, {c['captions']['words']} words from the {what}"
        + (" (word times ESTIMATED: the file has one time per line)" if est else "")
        + f"; {frames} frames at {fps:g} fps, {W}x{H}")
    for q in cues[:4]:
        print(f"  f{q['f0']}-{q['f1']} ({frame_to_tc(q['f0'], fps)} - {frame_to_tc(q['f1'], fps)})  "
              + " ".join(w["w"] for w in q["words"]))
    if len(cues) > 4:
        print(f"  ... {len(cues) - 4} more")
    print(f"for DaVinci Resolve's subtitle track: {srt}")
    if a.render:
        return cmd_render(argparse.Namespace(folder=str(folder), workers=None, mp4=False))
    return 0


def refresh(folder: Path, r=None) -> tuple[str, Path, list[dict]]:
    """Swap every clip of this overlay in the project open in DaVinci Resolve for a numbered copy of its newest
    render (MediaPoolItem.ReplaceClip): the timeline items keep position, length, transform, opacity and composite
    mode (measured 2026-10-12). Acts on the open project only; any clip whose file lies in <folder> counts."""
    import resolve_build as rb
    new = OS.resolve_copy(folder)
    r = r or rb.connect(20)
    p = r.GetProjectManager().GetCurrentProject()
    if not p:
        raise SystemExit("no project is open in DaVinci Resolve")
    key, newkey = str(folder.resolve()).lower() + os.sep, str(new.resolve()).lower()

    def walk(fo):
        for it in fo.GetClipList() or []:
            fp = str(it.GetClipProperty("File Path") or "")
            if fp.lower().startswith(key) and fp.lower() != newkey:
                yield it, fp
        for sub in fo.GetSubFolderList() or []:
            yield from walk(sub)

    new_frames = OV.probe(new)["frames"]
    out = []
    for it, fp in list(walk(p.GetMediaPool().GetRootFolder())):
        old_frames = int(it.GetClipProperty("Frames") or 0)
        ok = bool(it.ReplaceClip(str(new)))
        if ok and it.GetClipProperty("Alpha mode") != "Straight":
            it.SetClipProperty("Alpha mode", "Straight")
        out.append({"clip": it.GetName(), "was": fp, "ok": ok, "used": it.GetClipProperty("Usage"),
                    "frames": [old_frames, new_frames]})
    return p.GetName(), new, out


def cmd_refresh(a) -> int:
    folder = guard(Path(a.folder))
    s = OS.status(folder)
    if not s["rendered"]:
        raise SystemExit(f"{s['name']}: not rendered yet")
    if not s["current"]:
        log(f"  note: the settings changed since the last render - Resolve gets the last render ({s['rendered_at']})")
    name, new, swaps = refresh(folder)
    if not swaps:
        print(f"DaVinci Resolve's open project '{name}' has no clip of {s['name']} (or already the newest: {new.name}). "
              f"To add it, drag {new} into its media pool.")
        return 0
    for w in swaps:
        print(f"  {'swapped' if w['ok'] else 'FAILED  '} {w['clip']}: {Path(w['was']).name} -> {new.name}"
              + (f" (used {w['used']}x)" if w["used"] else ""))
        if w["ok"] and w["frames"][1] < w["frames"][0]:
            print(f"    NOTE: the new render has {w['frames'][1]} frames, the old {w['frames'][0]}: timeline clips "
                  "longer than that now run past its end")
    print(f"project '{name}': {sum(w['ok'] for w in swaps)} of {len(swaps)} clip(s) now use {new.name}; the timeline "
          "keeps position, length, transform, opacity and composite mode")
    return 0 if all(w["ok"] for w in swaps) else 1


def cmd_resolve_clip(a) -> int:
    folder = guard(Path(a.folder))
    try:
        print(OS.resolve_copy(folder))
    except ValueError as e:
        raise SystemExit(str(e))
    return 0


def cmd_graphics(a) -> int:
    items = OS.library()
    if not items:
        print("no graphics yet")
    for g in items:
        print(f"  {g['kind']:8s} {g['name']:24s} {g['frames']:4d} frames  {g['fps']:g} fps  {g['width']}x{g['height']}"
              f"  settings: {', '.join(d['id'] for d in g['settings']) or '-'}")
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


# ------------------------------------------------------------------------------------------- upgrades (0.3.2)
UPG = LAB / ".app" / "dev" / "hf-upgrade"
EXAMPLES = OVL / "examples"
TOL = 4                                           # max difference per channel (/255), the 0.3.0 overlay check's bar


def _example_conf(folder: Path) -> tuple[float, int]:
    """(fps, frames) from an example's index.html (`const FPS = 25, FRAMES = 30`)."""
    t = (folder / "index.html").read_text(encoding="utf-8")
    m = re.search(r"FPS\s*=\s*([\d.]+)\s*,\s*FRAMES\s*=\s*(\d+)", t)
    if not m:
        raise SystemExit(f"{folder.name}: no 'const FPS = .., FRAMES = ..' line in index.html")
    return float(m[1]), int(m[2])


def _render_pngs(hf_bin: Path, gsap_js: Path, example: Path, work: Path) -> tuple[list[Path], float]:
    """Render one example to PNG frames with a given HyperFrames + GSAP; returns (frames, seconds)."""
    src = work / "comp"
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(example, src, ignore=shutil.ignore_patterns("thumb.png", "*.mov", "*.rgba*", "render.json"))
    shutil.copy2(gsap_js, src / "gsap.min.js")
    fps, _ = _example_conf(example)
    t0 = time.time()
    r = subprocess.run([node(), str(hf_bin), "render", str(src), "--format", "png-sequence", "--fps", fps_arg(fps),
                        "--output", str(work / "frames"), "--quiet", "--workers", "auto", "--strict",
                        "--frames-cache-dir", "off"], cwd=str(hf_bin.parents[3]), env=env(), text=True,
                       capture_output=True, encoding="utf-8", errors="replace")
    secs = time.time() - t0
    pngs = sorted((work / "frames").glob("frame_*.png"))
    if r.returncode or not pngs:
        raise RuntimeError(f"render failed (exit {r.returncode}): {(r.stderr or r.stdout)[-500:]}")
    return pngs, secs


def _premul(p: Path) -> np.ndarray:
    a = np.asarray(Image.open(p).convert("RGBA")).astype(np.int32)
    out = a.copy()
    out[..., :3] = (a[..., :3] * a[..., 3:] + 127) // 255           # invisible pixels don't count
    return out


def _side_by_side(pa: Path, pb: Path, out: Path) -> None:
    """pinned | candidate | difference x8 (on a checkerboard), for the worst frame."""
    imgs = []
    for p in (pa, pb):
        a = np.asarray(Image.open(p).convert("RGBA")).astype(np.float32) / 255
        bg = checker(a.shape[0], a.shape[1])                       # already 0..1
        imgs.append(((a[..., :3] * a[..., 3:] + bg * (1 - a[..., 3:])) * 255 + 0.5).astype(np.uint8))
    d = np.clip(np.abs(_premul(pa) - _premul(pb))[..., :3] * 8, 0, 255).astype(np.uint8)
    Image.fromarray(np.hstack([imgs[0], imgs[1], d])).save(out)


def cmd_upgrade_test(a) -> int:
    from motionlab import upstream as UP
    npm = shutil.which("npm")
    if not npm or not HF.exists():
        raise SystemExit("needs Node.js and the pinned HyperFrames (overlay.py install)")
    pin = UP.pinned()
    ver = a.version or UP.latest("hyperframes")
    gver = (UP.latest("gsap") if a.gsap == "latest" else a.gsap) if a.gsap else pin["gsap"]
    if ver == pin["hyperframes"] and gver == pin["gsap"]:
        print(f"HyperFrames {ver} + GSAP {gver} is what MotionLab pins already - nothing to test")
        return 0
    root = UPG / f"hyperframes-{ver}"
    pkg = root / "pkg"
    shutil.rmtree(root, ignore_errors=True)
    pkg.mkdir(parents=True)
    (pkg / "package.json").write_text(json.dumps({"name": "motionlab-overlays-candidate", "private": True,
                                                  "dependencies": {"hyperframes": ver, "gsap": gver}}, indent=1),
                                      encoding="utf-8")
    log(f"installing the candidate HyperFrames {ver} + GSAP {gver} into {pkg} (scratch) ...")
    r = subprocess.run([npm, "install", "--no-fund", "--no-audit"], cwd=str(pkg), env=env(), capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    cand = pkg / "node_modules" / "hyperframes" / "bin" / "hyperframes.mjs"
    if r.returncode or not cand.exists():
        raise SystemExit(f"npm install failed (exit {r.returncode}): {(r.stderr or r.stdout)[-600:]}")
    if subprocess.run([node(), str(cand), "browser", "ensure"], cwd=str(pkg), env=env(), capture_output=True).returncode:
        raise SystemExit("the candidate could not get its Chrome")
    sides = {"pinned": (HF, GSAP), "candidate": (cand, pkg / "node_modules" / "gsap" / "dist" / "gsap.min.js")}
    examples = sorted(p for p in EXAMPLES.iterdir() if (p / "index.html").exists())
    if a.quick:
        examples = [p for p in examples if _example_conf(p)[1] <= 100]
    rows, ok = [], True
    for ex in examples:
        res = {"example": ex.name}
        try:
            got = {}
            for side, (hb, gj) in sides.items():
                got[side] = _render_pngs(hb, gj, ex, root / side / ex.name)
                res[f"seconds_{side}"] = round(got[side][1], 1)
            pa, pb = got["pinned"][0], got["candidate"][0]
            res["frames"] = [len(pa), len(pb)]
            worst, wf, over = 0, 0, 0
            for i, (x, y) in enumerate(zip(pa, pb)):
                d = np.abs(_premul(x) - _premul(y))
                m = int(d.max())
                over += int((d.max(axis=2) > 1).sum())
                if m > worst:
                    worst, wf = m, i
            px = len(pa) * np.asarray(Image.open(pa[0])).shape[0] * np.asarray(Image.open(pa[0])).shape[1]
            fps, _ = _example_conf(ex)
            res.update({"max_diff": worst, "worst_frame": wf, "worst_tc": frame_to_tc(wf, fps),
                        "pixels_over_1_pct": round(100 * over / max(px, 1), 3),
                        "pass": len(pa) == len(pb) and worst <= TOL})
            if worst:
                shot = root / f"{ex.name}_f{wf}.png"
                _side_by_side(pa[wf], pb[wf], shot)
                res["worst_image"] = str(shot.relative_to(LAB))
        except RuntimeError as e:
            res.update({"pass": False, "error": str(e)})
        ok = ok and res["pass"]
        rows.append(res)
        log(f"  {ex.name}: " + (f"ERROR {res['error']}" if "error" in res else
            f"{'PASS' if res['pass'] else 'FAIL'}  frames {res['frames'][0]}/{res['frames'][1]}, max difference "
            f"{res['max_diff']}/255 (worst f{res['worst_frame']} ({res['worst_tc']})), "
            f"{res['pixels_over_1_pct']} % pixels > 1/255; render {res['seconds_pinned']} s -> "
            f"{res['seconds_candidate']} s"))
        for side in sides:                                          # frames are big; keep the report + worst frames
            shutil.rmtree(root / side / ex.name, ignore_errors=True)
    if not a.keep:
        shutil.rmtree(pkg, ignore_errors=True)
    result = {"hyperframes": ver, "gsap": gver, "from": pin, "pass": ok, "examples": rows}
    (root / "report.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    UP.record_test(ver, result)
    print(f"\nUPGRADE TEST {'PASS' if ok else 'FAIL'}: HyperFrames {pin['hyperframes']} -> {ver}, GSAP {pin['gsap']} -> "
          f"{gver} ({len(rows)} examples, max {TOL}/255). Report: {(root / 'report.json').relative_to(LAB)}")
    if ok:
        print(f"To adopt it (the repo owner): .venv\\Scripts\\python tools\\overlay.py pin {ver}"
              + (f" --gsap {gver}" if gver != pin["gsap"] else ""))
    return 0 if ok else 1


def cmd_versions(a) -> int:
    from motionlab import upstream as UP
    s = UP.check(force=True)
    for k, p in s["packages"].items():
        print(f"{k}: pinned {p['pinned']}, installed {p['installed']}, newest on npm {p['latest']}"
              + ("  <- newer" if p["newer"] else "") + ("  (installed != pinned: overlay.py install)"
                                                        if p["out_of_date"] else "") + f"   notes: {p['notes']}")
    for v, t in sorted(s["tests"].items(), key=lambda kv: UP.vkey(kv[0])):
        print(f"upgrade test {v} (+ GSAP {t.get('gsap')}): {'PASS' if t.get('pass') else 'FAIL'} on {t.get('when')}")
    if s["error"]:
        print("npm check:", s["error"])
    return 0


def cmd_pin(a) -> int:
    """Adopt a tested version: npm install --save-exact in tools\\overlays (package.json + lock), its Chrome."""
    from motionlab import upstream as UP
    t = UP.state()["tests"].get(a.version)
    if not (t and t.get("pass")) and not a.force:
        raise SystemExit(f"no passing upgrade test for HyperFrames {a.version} - run: overlay.py upgrade-test "
                         f"{a.version}" + (f" --gsap {a.gsap}" if a.gsap else "") + "  (or --force)")
    if t and a.gsap and t.get("gsap") != a.gsap and not a.force:
        raise SystemExit(f"the test used GSAP {t.get('gsap')}, not {a.gsap}")
    npm = shutil.which("npm")
    specs = [f"hyperframes@{a.version}"] + ([f"gsap@{a.gsap}"] if a.gsap else [])
    log(f"pinning {' '.join(specs)} in tools\\overlays ...")
    if subprocess.run([npm, "install", "--save-exact", "--no-fund", "--no-audit", *specs], cwd=str(OVL),
                      env=env()).returncode:
        raise SystemExit("npm install failed - tools\\overlays\\package.json may be half changed: git diff it")
    hf("browser", "ensure")
    print(f"pinned: {UP.pinned()}\nNext: selftest.py --extended, tools\\dev\\smoke.py, a CHANGELOG line, then commit + "
          "push - friends get it through GitHub's tests and the Update button (setup.bat / Install run npm ci).")
    return 0


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("new")
    s.add_argument("folder")
    s.add_argument("--frames", type=int)
    s.add_argument("--from", dest="from_", metavar="GRAPHIC", help="start from a library graphic or an example")
    s.add_argument("--render", action="store_true", help="with --from: render it right away")
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
    s = sub.add_parser("settings", help="the settings an overlay declares and their values")
    s.add_argument("folder")
    s = sub.add_parser("set", help="change settings: id=value ... (then render again)")
    s.add_argument("folder")
    s.add_argument("values", nargs="+")
    s = sub.add_parser("save", help="an approved, rendered overlay -> library\\graphics\\<name>")
    s.add_argument("folder")
    s.add_argument("--name")
    s.add_argument("--force", action="store_true")
    sub.add_parser("graphics", help="the graphics library (yours + the examples)")
    s = sub.add_parser("refresh", help="swap this graphic in the project open in DaVinci Resolve (keeps your edits)")
    s.add_argument("folder")
    s = sub.add_parser("resolve-clip", help="the numbered copy to drag into DaVinci Resolve (it locks what it uses)")
    s.add_argument("folder")
    s = sub.add_parser("captions", help="captions timed to the words from an .srt / .vtt / transcript.json")
    s.add_argument("folder")
    s.add_argument("--from", dest="from_", required=True, metavar="FILE",
                   help=".srt / .vtt / transcript.json, or a video / audio file (speech to text: tools\\speech.py)")
    s.add_argument("--model", default="small", choices=("small", "base"), help="speech to text model (a video)")
    s.add_argument("--names", help="names / words in the video, comma separated (speech to text gets them right)")
    s.add_argument("--lang", help="the video's language code (default: detected)")
    s.add_argument("--fps", type=float)
    s.add_argument("--width", type=int)
    s.add_argument("--height", type=int)
    s.add_argument("--frames", type=int, help="the clip's length (default: the edit plan's, else the last caption)")
    s.add_argument("--offset", type=int, default=0, help="frames to move every caption by")
    s.add_argument("--max-chars", type=int, default=32)
    s.add_argument("--max-words", type=int, default=6)
    s.add_argument("--render", action="store_true")
    sub.add_parser("install")
    s = sub.add_parser("doctor")
    s.add_argument("--fix", action="store_true", help="download HyperFrames' Chrome if missing")
    s = sub.add_parser("versions", help="pinned / installed / newest HyperFrames + GSAP (asks npm)")
    s = sub.add_parser("upgrade-test", help="render the examples with a newer HyperFrames and compare every frame")
    s.add_argument("version", nargs="?", help="default: the newest on npm")
    s.add_argument("--gsap", help="a GSAP version to test too ('latest'); default: the pinned one")
    s.add_argument("--quick", action="store_true", help="only the short examples (skip the 10 s clip)")
    s.add_argument("--keep", action="store_true", help="keep the scratch install in .app\\dev\\hf-upgrade")
    s = sub.add_parser("pin", help="adopt a version that passed upgrade-test (changes tools\\overlays\\package.json)")
    s.add_argument("version")
    s.add_argument("--gsap")
    s.add_argument("--force", action="store_true")
    a = ap.parse_args()
    return {"new": cmd_new, "render": cmd_render, "stills": cmd_stills, "check": cmd_check, "settings": cmd_settings,
            "set": cmd_set, "save": cmd_save, "graphics": cmd_graphics, "captions": cmd_captions,
            "refresh": cmd_refresh, "resolve-clip": cmd_resolve_clip,
            "doctor": cmd_doctor, "install": cmd_install, "versions": cmd_versions, "upgrade-test": cmd_upgrade_test,
            "pin": cmd_pin}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
