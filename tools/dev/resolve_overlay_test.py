"""HTML overlays inside a real DaVinci Resolve (0.3.2, item 2). Renders three overlays with the pinned HyperFrames (4AM's
title and clock = tools\\overlays\\examples, and a colour check: colour patches at 100/75/50/25 % alpha, alpha ramps, a
soft glow, the frame number as 8 bits), places them in the throwaway project `motionlab_scratch` (deleted afterwards;
the project open before is saved and reopened) over a known gradient plate, renders every frame from Resolve as 16-bit
TIFF and compares each with the lab compositor's result from the same files. Also measured: alpha export, composite
modes Screen / Add, Resolve Color Management, whether Resolve locks the clip file, and refresh in place
(MediaPoolItem.ReplaceClip with a re-rendered overlay keeps the hand edits on the timeline).

    .venv\\Scripts\\python tools\\dev\\resolve_overlay_test.py [--keep-frames] [--no-quit]
Needs DaVinci Resolve Studio (external scripting = Local); starts it if it is not running and quits it afterwards
(only if this test started it). Writes .app\\dev\\resolve-overlay\\ (report.json, worst frame per case as PNG).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from motionlab import compose  # noqa: E402
from motionlab import overlays as OV  # noqa: E402
from motionlab.timecode import frame_to_tc  # noqa: E402
from motionlab.util import LAB, tool  # noqa: E402

PY = sys.executable
WORK = LAB / ".app" / "dev" / "resolve-overlay"
EX = LAB / "tools" / "overlays" / "examples"
GSAP = LAB / "tools" / "overlays" / "node_modules" / "gsap" / "dist" / "gsap.min.js"
RESOLVE_EXE = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Blackmagic Design" / "DaVinci Resolve" / "Resolve.exe"
W, H, FPS = 1520, 1080, 25
SCRATCH = "motionlab_scratch"
ACC = OV.ACCURATE

COLOURS = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (0, 255, 255), (255, 0, 255), (255, 255, 0), (255, 255, 255),
           (128, 128, 128), (255, 140, 20), (224, 172, 140), (20, 30, 70)]
ALPHAS = [1.0, 0.75, 0.5, 0.25]
BITS_Y, BITS_X0, BITS_STEP, BITS_SIZE = 940, 100, 50, 40

COLOUR_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1520, height=1080">
<!-- MotionLab Resolve test overlay "__NAME__": 12 frames at 25 fps, 1520 x 1080 px (tools/dev/resolve_overlay_test.py) -->
<script src="./gsap.min.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { width: 1520px; height: 1080px; overflow: hidden; background: transparent; }
  #root { position: relative; width: 1520px; height: 1080px; overflow: hidden; }
  .abs { position: absolute; }
  .bit { position: absolute; top: __BY__px; width: __BS__px; height: __BS__px; background: #fff; opacity: 0; }
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="0.48" data-width="1520" data-height="1080">
__PATCHES__
  <div class="abs" style="left:100px; top:780px; width:1320px; height:60px;
       background: linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,1));"></div>
  <div class="abs" style="left:100px; top:850px; width:1320px; height:60px;
       background: linear-gradient(90deg, rgba(255,40,0,0), rgba(255,40,0,1));"></div>
  <div class="abs" style="left:1200px; top:640px; width:240px; height:120px; border-radius:60px;
       background: radial-gradient(ellipse, rgba(80,200,255,1) 0%, rgba(80,200,255,0) 70%);"></div>
  <div class="abs" style="left:96px; top:936px; width:396px; height:48px; background:#000;"></div>
__BITS__
__MARK__
</div>
<script>
  const FPS = 25, FRAMES = 12;
  const F = n => n / FPS;
  const AT = n => (n - 0.5) / FPS;
  const tl = gsap.timeline({ paused: true });
  for (let n = 0; n < FRAMES; n++)
    for (let b = 0; b < 8; b++) tl.set("#b" + b, { opacity: (n >> b) & 1 }, n === 0 ? 0 : AT(n));
  tl.set({}, {}, F(FRAMES));
  window.__timelines = window.__timelines || {};
  window.__timelines["main"] = tl;
</script>
</body>
</html>
"""


def colour_html(name: str, version: int) -> str:
    cols = COLOURS[version - 1:] + COLOURS[:version - 1]          # v2 = every patch one colour further
    pat = []
    for r, a in enumerate(ALPHAS):
        for i, (cr, cg, cb) in enumerate(cols):
            pat.append(f'  <div class="abs" style="left:{100 + i * 120}px; top:{100 + r * 130}px; width:110px; '
                       f'height:110px; background: rgba({cr},{cg},{cb},{a});"></div>')
    bits = "\n".join(f'  <div id="b{b}" class="bit" style="left:{BITS_X0 + b * BITS_STEP}px"></div>' for b in range(8))
    mark = ('  <div class="abs" style="left:600px; top:640px; width:300px; height:100px; background: rgb(0,200,90);">'
            '</div>') if version == 2 else ""
    return (COLOUR_HTML.replace("__NAME__", name).replace("__PATCHES__", "\n".join(pat)).replace("__BITS__", bits)
            .replace("__MARK__", mark).replace("__BY__", str(BITS_Y)).replace("__BS__", str(BITS_SIZE)))


# ------------------------------------------------------------------------------------------------ lab side
def overlay_folder(name: str, frames: int, html: str) -> Path:
    d = WORK / "overlays" / name
    d.mkdir(parents=True, exist_ok=True)
    write_if_changed(d / "index.html", html)                     # unchanged -> the earlier render is kept
    if not (d / "gsap.min.js").exists():
        shutil.copy2(GSAP, d / "gsap.min.js")
    (d / "hyperframes.json").write_text(json.dumps({"paths": {"assets": "assets"}}, indent=1), encoding="utf-8")
    (d / "overlay.json").write_text(json.dumps({"name": name, "frames": frames, "fps": FPS, "width": W, "height": H},
                                               indent=1), encoding="utf-8")
    mov = d / f"{name}.mov"
    if not mov.exists() or mov.stat().st_mtime < (d / "index.html").stat().st_mtime - 1:
        print(f"rendering the overlay {name} ({frames} frames) with HyperFrames ...", flush=True)
        r = subprocess.run([PY, str(LAB / "tools" / "overlay.py"), "render", str(d)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode or not mov.exists():
            raise SystemExit(f"overlay render failed: {r.stdout[-800:]} {r.stderr[-800:]}")
        print("  " + "  ".join(ln for ln in r.stdout.splitlines() if "ProRes 4444" in ln), flush=True)
    return mov


def write_if_changed(p: Path, text: str):
    if not p.exists() or p.read_text(encoding="utf-8") != text:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


def make_plate(frames: int) -> tuple[Path, np.ndarray]:
    """A smooth colour gradient (ProRes 422 HQ, Rec.709, video levels) and the lab's decode of it (float RGB)."""
    mov = WORK / f"plate_{frames}.mov"
    if not mov.exists():
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        rgb = np.dstack([0.1 + 0.8 * xx / (W - 1), 0.1 + 0.8 * yy / (H - 1), 0.35 + 0.2 * (xx + yy) / (W + H)])
        png = WORK / "plate.png"
        cv2.imwrite(str(png), (rgb[..., ::-1] * 65535 + 0.5).astype(np.uint16))
        subprocess.run([tool("ffmpeg"), "-v", "error", "-y", "-loop", "1", "-framerate", str(FPS), "-i", str(png),
                        "-frames:v", str(frames),
                        "-vf", f"scale=out_color_matrix=bt709:out_range=tv:flags={ACC},format=yuv422p10le",
                        "-c:v", "prores_ks", "-profile:v", "3", "-vendor", "apl0", "-colorspace", "bt709",
                        "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv", str(mov)], check=True)
    r = subprocess.run([tool("ffmpeg"), "-v", "error", "-i", str(mov), "-frames:v", "1",
                        "-vf", f"scale=in_color_matrix=bt709:in_range=tv:flags={ACC},format=rgb48le",
                        "-f", "rawvideo", "-"], capture_output=True, check=True)
    return mov, np.frombuffer(r.stdout, "<u2").reshape(H, W, 3).astype(np.float32) / 65535.0


def lab_frame(plate: np.ndarray, seg: dict | None, k: int) -> np.ndarray:
    """The lab compositor's frame: the plate + the overlay layer (motionlab.compose.OverlayLayer, the real code)."""
    canvas = plate.copy()
    if seg:
        R = SimpleNamespace(curves={}, W=W, H=H)
        spec = {"type": "overlay", "id": seg["name"], "start": 0, "end": seg["n"] - 1, "file": str(seg["mov"]),
                "blend": seg.get("blend", "normal"), "opacity": seg.get("opacity", 1.0)}
        if seg.get("dx"):
            spec["rect"] = [seg["dx"], seg.get("dy", 0), W, H]
        compose.OverlayLayer(spec, R).draw(canvas, k, R)
    return np.clip(canvas, 0, 1)


def read_tif(p: Path) -> np.ndarray:
    im = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
    if im is None:
        raise RuntimeError(f"cannot read {p}")
    if im.ndim == 2:
        im = np.dstack([im] * 3)
    im = im[..., [2, 1, 0, 3]] if im.shape[2] == 4 else im[..., ::-1]
    return im.astype(np.float32) / (65535.0 if im.dtype == np.uint16 else 255.0)


def bits_of(img: np.ndarray) -> int:
    v = 0
    for b in range(8):
        cx, cy = BITS_X0 + b * BITS_STEP + BITS_SIZE // 2, BITS_Y + BITS_SIZE // 2
        if img[cy - 5:cy + 5, cx - 5:cx + 5, :3].mean() > 0.5:
            v |= 1 << b
    return v


def stats(d: np.ndarray, mask: np.ndarray | None = None) -> dict:
    x = d if mask is None else d[mask]
    if x.size == 0:
        return {"max": 0.0, "mean": 0.0, "p999": 0.0}
    return {"max": round(float(x.max()) * 255, 2), "mean": round(float(x.mean()) * 255, 3),
            "p999": round(float(np.percentile(x, 99.9)) * 255, 2)}


def side_by_side(a: np.ndarray, b: np.ndarray, out: Path, title: str):
    d = np.clip(np.abs(a - b) * 8, 0, 1)
    strip = np.hstack([a, b, d])
    im = Image.fromarray((strip * 255 + 0.5).astype(np.uint8)).resize((strip.shape[1] // 2, strip.shape[0] // 2))
    from PIL import ImageDraw
    ImageDraw.Draw(im).text((10, 8), f"{title}   lab | Resolve | difference x8", fill=(255, 196, 0))
    im.save(out)


# ------------------------------------------------------------------------------------------------ Resolve side
def connect(timeout: float):
    import resolve_build as rb
    return rb.connect(timeout)


def render(p, tl, a: int, b: int, folder: Path, name: str, alpha: bool = False) -> list[Path]:
    """Render timeline frames a..b as a 16-bit TIFF sequence; returns the files in frame order."""
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    p.SetCurrentTimeline(tl)
    p.SetCurrentRenderMode(1)
    codecs = p.GetRenderCodecs("tif") or {}
    c16 = [(d, c) for d, c in codecs.items() if "16" in d]
    codec = ([c for d, c in c16 if alpha and "RGBA" in d.upper()] or [c for d, c in c16] or list(codecs.values()))[0]
    if not p.SetCurrentRenderFormatAndCodec("tif", codec):
        raise SystemExit(f"Resolve refused TIFF / {codec} (codecs: {codecs})")
    p.SetRenderSettings({"SelectAllFrames": False})          # optional: Resolve 21.1 refuses it, MarkIn / Out suffice
    for k, v in (("MarkIn", a), ("MarkOut", b), ("TargetDir", str(folder)),
                 ("CustomName", name), ("ExportVideo", True), ("ExportAudio", False)):
        if not p.SetRenderSettings({k: v}):
            raise SystemExit(f"render setting refused: {k} = {v!r}")
    if alpha:
        ok = p.SetRenderSettings({"ExportAlpha": True})
        p.SetRenderSettings({"AlphaMode": 1})                 # straight, like the source clip
        if not ok:
            print("  note: Resolve refused ExportAlpha for TIFF", flush=True)
    jid = p.AddRenderJob()
    t0 = time.time()
    p.StartRendering([jid], False)
    r = None
    while True:
        time.sleep(1)
        try:
            busy = p.IsRenderingInProgress()
        except (TypeError, AttributeError):                    # scripting objects drop out while rendering: re-fetch
            time.sleep(4)
            r = connect(60)
            p = r.GetProjectManager().GetCurrentProject()
            continue
        if not busy:
            break
        if time.time() - t0 > 900:
            p.StopRendering()
            raise SystemExit("render took longer than 15 min - stopped")
    st = p.GetRenderJobStatus(jid) or {}
    p.DeleteRenderJob(jid)
    if st.get("JobStatus") != "Complete":
        raise SystemExit(f"Resolve render failed: {st}")
    files = sorted(folder.glob(f"{name}*.tif"))
    print(f"  Resolve rendered f{a}-{b} ({codec}{', alpha' if alpha else ''}) in {time.time() - t0:.0f}s: "
          f"{len(files)} files", flush=True)
    if len(files) != b - a + 1:
        raise SystemExit(f"expected {b - a + 1} TIFFs, got {len(files)}")
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keep-frames", action="store_true", help="keep Resolve's TIFFs (~10 MB each)")
    ap.add_argument("--no-quit", action="store_true", help="leave Resolve open even if this test started it")
    a = ap.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    report: dict = {"date": time.strftime("%Y-%m-%d %H:%M"), "cases": {}}

    # ---- overlays (pinned HyperFrames) + plate
    title = overlay_folder("title", 30, (EX / "pixel-title" / "index.html").read_text(encoding="utf-8"))
    clock = overlay_folder("clock", 62, (EX / "seven-segment-clock" / "index.html").read_text(encoding="utf-8"))
    col1 = overlay_folder("colour_v1", 12, colour_html("colour_v1", 1))
    col2 = overlay_folder("colour_v2", 12, colour_html("colour_v2", 2))
    segs = [dict(name="title", mov=title, a=0, n=30), dict(name="clock", mov=clock, a=30, n=62),
            dict(name="colour", mov=col1, a=92, n=12), dict(name="colour_screen", mov=col1, a=104, n=12,
                                                             blend="screen"),
            dict(name="colour_add", mov=col1, a=116, n=12, blend="add")]
    N = 133                                                       # f128-132: the plate alone (decode baseline)
    plate_mov, plate = make_plate(N)

    # ---- Resolve
    running = "Resolve.exe" in subprocess.run(["tasklist", "/FI", "IMAGENAME eq Resolve.exe"], capture_output=True,
                                               text=True).stdout
    started = False
    if not running:
        print("starting DaVinci Resolve ...", flush=True)
        subprocess.Popen([str(RESOLVE_EXE)])
        started = True
    r = connect(300)
    report["resolve"] = r.GetVersionString()
    print("Resolve", report["resolve"], flush=True)
    pm = r.GetProjectManager()
    cur = pm.GetCurrentProject()
    back = cur.GetName() if cur else None
    if back and back.startswith("Untitled Project"):
        back = None                      # Resolve's unsaved default: SaveProject would open a "name it" dialog that
    elif cur:                            # blocks scripting (seen 2026-10-12 with Resolve at the Project Manager)
        pm.SaveProject()
    if back == SCRATCH:
        back = None
    if SCRATCH in (pm.GetProjectListInCurrentFolder() or []):
        if cur and cur.GetName() == SCRATCH:
            pm.CloseProject(cur)
        pm.DeleteProject(SCRATCH)
    p = pm.CreateProject(SCRATCH)
    if not p:
        raise SystemExit(f"Resolve refused to create the scratch project '{SCRATCH}'")
    print(f"scratch project {SCRATCH} (the open project before: {back})", flush=True)
    frames_dirs = []
    try:
        for k, v in (("timelineResolutionWidth", str(W)), ("timelineResolutionHeight", str(H)),
                     ("timelineFrameRate", str(FPS))):
            p.SetSettings({k: v})
        report["colour_science"] = {k: (p.GetSettings() or {}).get(k) for k in ("colorScienceMode", "colorSpaceTimeline",
                                                                  "colorSpaceTimelineGamma", "colorSpaceOutput",
                                                                  "colorSpaceOutputGamma")}
        mp = p.GetMediaPool()
        items = {}
        for m in (plate_mov, title, clock, col1):
            res = mp.ImportMedia([str(m)])
            if not res:
                raise SystemExit(f"Resolve could not import {m}")
            items[m] = res[0]
        for m in (title, clock, col1):
            pr = items[m].GetClipProperty()
            report.setdefault("clip_properties", {})[m.stem] = {
                k: pr.get(k) for k in ("Alpha mode", "Format", "Video Codec", "Resolution", "Frames", "FPS",
                                       "Data Level", "Input Color Space", "Input Gamma")}
            if not items[m].SetClipProperty("Alpha mode", "Straight"):
                print(f"  note: Resolve did not take Alpha mode = Straight for {m.name}", flush=True)
        tl = mp.CreateEmptyTimeline("overlay_test")
        p.SetCurrentTimeline(tl)
        tl.SetStartTimecode("00:00:00:00")
        tl.AddTrack("video")

        def put(item, n, track, rec):
            res = mp.AppendToTimeline([{"mediaPoolItem": item, "startFrame": 0, "endFrame": n, "trackIndex": track,
                                        "recordFrame": rec, "mediaType": 1}])
            if not res:
                raise SystemExit(f"AppendToTimeline failed at f{rec} on V{track}")
            it = res[0]
            if it.GetStart() != rec or it.GetDuration() != n:
                raise SystemExit(f"placed at {it.GetStart()}+{it.GetDuration()}, wanted {rec}+{n}")
            return it

        put(items[plate_mov], N, 1, 0)
        modes = {"screen": r.COMPOSITE_SCREEN, "add": r.COMPOSITE_ADD}
        for s in segs:
            s["item"] = put(items[s["mov"]], s["n"], 2, s["a"])
            if s.get("blend") in modes and not s["item"].SetProperties({"CompositeMode": modes[s["blend"]]}):
                raise SystemExit(f"{s['name']}: composite mode refused")
        tla = mp.CreateEmptyTimeline("overlay_alpha")             # the overlays alone: alpha export
        p.SetCurrentTimeline(tla)
        tla.SetStartTimecode("00:00:00:00")
        for s in segs[:3]:
            put(items[s["mov"]], s["n"], 1, s["a"])

        # ---- 1. every frame over the plate (Resolve's default colour science)
        print("1. overlays over the plate, every frame ...", flush=True)
        d1 = WORK / "r_default"
        frames_dirs.append(d1)
        files = render(p, tl, 0, N - 1, d1, "ov")

        def compare(case: str, files: list[Path], f0: int, segs_: list[dict]):
            by = {}
            for i, fp in enumerate(files):
                f = f0 + i
                seg = next((s for s in segs_ if s["a"] <= f < s["a"] + s["n"]), None)
                key = seg["name"] if seg else "plate_only"
                k = f - seg["a"] if seg else 0
                exp = lab_frame(plate, seg, k)
                got = read_tif(fp)[..., :3]
                d = np.abs(got - exp).max(axis=2)
                e = by.setdefault(key, {"frames": 0, "max": 0.0, "mean_sum": 0.0, "p999": 0.0, "worst": None,
                                        "bits_wrong": []})
                st = stats(d)
                e["frames"] += 1
                e["mean_sum"] += st["mean"]
                e["p999"] = max(e["p999"], st["p999"])
                if st["max"] >= e["max"]:
                    e["max"], e["worst"] = st["max"], f
                    side_by_side(exp, got, WORK / f"{case}_{key}.png",
                                 f"{case} {key} f{f} ({frame_to_tc(f, FPS)})")
                if seg and seg["name"].startswith("colour") and seg.get("blend", "normal") == "normal" \
                        and not seg.get("dx"):
                    got_bits = bits_of(got)
                    if got_bits != k:
                        e["bits_wrong"].append([f, got_bits, k])
            for key, e in by.items():
                e["mean"] = round(e.pop("mean_sum") / max(e["frames"], 1), 3)
                w = e["worst"]
                e["worst"] = f"f{w} ({frame_to_tc(w, FPS)})"
                print(f"   {case:12s} {key:14s} {e['frames']:3d} frames  max {e['max']:6.2f}/255  p99.9 "
                      f"{e['p999']:6.2f}  mean {e['mean']:.3f}  worst {e['worst']}"
                      + (f"  FRAME CODE WRONG {e['bits_wrong'][:3]}" if e["bits_wrong"] else ""), flush=True)
            report["cases"][case] = by

        compare("default", files, 0, segs)

        # ---- 2. alpha export (the overlays alone)
        print("2. alpha export (overlays alone, TIFF RGBA) ...", flush=True)
        d2 = WORK / "r_alpha"
        frames_dirs.append(d2)
        try:
            fa = render(p, tla, 0, 103, d2, "al", alpha=True)
            res2 = {}
            for i, fp in enumerate(fa):
                seg = next(s for s in segs[:3] if s["a"] <= i < s["a"] + s["n"])
                m, arr = OV.load(seg["mov"])
                x, y, cw, ch = m["crop"]
                src = np.zeros((H, W, 4), np.float32)
                src[y:y + ch, x:x + cw] = np.asarray(arr[i - seg["a"]], np.float32) / 255.0
                got = read_tif(fp)
                e = res2.setdefault(seg["name"], {"channels": int(got.shape[2]), "alpha_max": 0.0,
                                                  "rgb_straight_max": 0.0, "rgb_premul_max": 0.0})
                if got.shape[2] == 4:
                    e["alpha_max"] = max(e["alpha_max"], round(float(np.abs(got[..., 3] - src[..., 3]).max()) * 255, 2))
                    vis = src[..., 3] > 0.5
                    if vis.any():
                        e["rgb_straight_max"] = max(e["rgb_straight_max"], round(float(
                            np.abs(got[..., :3] - src[..., :3])[vis].max()) * 255, 2))
                pm_ = src[..., :3] * src[..., 3:]
                e["rgb_premul_max"] = max(e["rgb_premul_max"], round(float(np.abs(got[..., :3] - pm_).max()) * 255, 2))
            for k_, e in res2.items():
                print(f"   alpha {k_:8s} {e}", flush=True)
            report["cases"]["alpha_export"] = res2
        except SystemExit as ex:
            print("   alpha export failed:", ex, flush=True)
            report["cases"]["alpha_export"] = {"error": str(ex)}

        # ---- 3. does Resolve lock the clip file? (a copy of the same bytes over it, so nothing changes)
        tmp = col1.with_name(col1.name + ".locktest")
        shutil.copy2(col1, tmp)
        try:
            os.replace(tmp, col1)
            lock = "not locked: a re-render can replace the file while Resolve has it"
        except PermissionError as ex:
            lock = f"LOCKED: {ex}"
            tmp.unlink(missing_ok=True)
        print("3. file lock:", lock, flush=True)
        report["file_lock"] = lock

        # ---- 4. refresh in place: hand edits, then ReplaceClip with the re-rendered overlay (colour_v2)
        print("4. refresh in place (ReplaceClip) ...", flush=True)
        n_, s_, a_ = segs[2]["item"], segs[3]["item"], segs[4]["item"]
        edits = {id(n_): {"Pan": 40.0, "Opacity": 80.0}, id(s_): {"Opacity": 60.0}, id(a_): {}}
        for it in (n_, s_, a_):
            for k, v in edits[id(it)].items():
                if not it.SetProperties({k: v}):
                    print(f"   note: SetProperty {k} refused", flush=True)
        keys = ("Pan", "Tilt", "ZoomX", "ZoomY", "Opacity", "CompositeMode", "CropLeft", "RotationAngle")
        before = [{k: (it.GetProperties() or {}).get(k) for k in keys} | {"start": it.GetStart(), "dur": it.GetDuration(),
                                                          "left": it.GetLeftOffset()} for it in (n_, s_, a_)]
        t0 = time.time()
        ok = items[col1].ReplaceClip(str(col2))
        after = [{k: (it.GetProperties() or {}).get(k) for k in keys} | {"start": it.GetStart(), "dur": it.GetDuration(),
                                                         "left": it.GetLeftOffset()} for it in (n_, s_, a_)]
        pr2 = items[col1].GetClipProperty()
        rep4 = {"replace_ok": bool(ok), "seconds": round(time.time() - t0, 2), "kept": before == after,
                "before": before, "after": after, "file_after": pr2.get("File Path"),
                "alpha_mode_after": pr2.get("Alpha mode")}
        print(f"   ReplaceClip {'ok' if ok else 'FAILED'}; hand edits kept: {before == after}; Alpha mode after: "
              f"{pr2.get('Alpha mode')}; file: {Path(str(pr2.get('File Path'))).name}", flush=True)
        if before != after:
            print("   before", before, "\n   after ", after, flush=True)
        report["refresh"] = rep4
        d4 = WORK / "r_refresh"
        frames_dirs.append(d4)
        fr4 = render(p, tl, 92, 127, d4, "rf")
        segs_v2 = [dict(segs[2], mov=col2, opacity=0.8, dx=40), dict(segs[3], mov=col2, opacity=0.6),
                   dict(segs[4], mov=col2)]
        compare("refreshed", fr4, 92, segs_v2)

        # ---- 4b. the same path: a re-render written over the file Resolve already has (only if it is not locked)
        if lock.startswith("not locked"):
            print("4b. a re-render over the same file ...", flush=True)

            def version_of(img):                       # the first patch: red in v1, green in v2
                c = img[150:160, 190:200, :3].mean(axis=(0, 1))
                return "v2 (the new render)" if c[1] > c[0] else "v1 (the old frames)"
            backup = col1.with_name(col1.name + ".v1")
            shutil.copy2(col1, backup)
            same = {}
            try:
                items[col1].ReplaceClip(str(col1))
                for k_, d_ in (("s0", "r_same0"), ("s1", "r_same1"), ("s2", "r_same2")):
                    frames_dirs.append(WORK / d_)
                same["before"] = version_of(read_tif(render(p, tl, 92, 92, WORK / "r_same0", "s0")[0]))
                tmp = col1.with_name(col1.name + ".part")
                shutil.copy2(col2, tmp)
                os.replace(tmp, col1)
                same["file_replaced_nothing_else"] = version_of(read_tif(render(p, tl, 92, 92, WORK / "r_same1",
                                                                                "s1")[0]))
                ok2 = items[col1].ReplaceClip(str(col1))
                same["then_ReplaceClip_same_path"] = (version_of(read_tif(render(p, tl, 92, 92, WORK / "r_same2",
                                                                                 "s2")[0]))
                                                      + ("" if ok2 else " (ReplaceClip refused)"))
            finally:
                os.replace(backup, col1)
            print("   ", same, flush=True)
            report["same_path"] = same

        # ---- 4c. the real flow: Resolve on the numbered copy, a setting changed, render (must not be locked),
        #          overlay.py refresh, the hand edits kept, Resolve shows the new graphic
        print("4c. overlay.py refresh: settings changed, render, refresh ...", flush=True)
        import overlay as OVL
        from motionlab import overlay_settings as OS
        rf = WORK / "overlays" / "refresh_title"
        shutil.rmtree(rf, ignore_errors=True)
        subprocess.run([PY, str(LAB / "tools" / "overlay.py"), "new", str(rf), "--from", "pixel-title", "--render"],
                       check=True, capture_output=True)
        first = OS.resolve_copy(rf)
        rmi = mp.ImportMedia([str(first)])[0]
        tlr = mp.CreateEmptyTimeline("refresh_test")
        p.SetCurrentTimeline(tlr)
        tlr.SetStartTimecode("00:00:00:00")
        tlr.AddTrack("video")
        put(items[plate_mov], 30, 1, 0)
        ti = put(rmi, 30, 2, 0)
        ti.SetProperties({"Pan": -30.0})
        ti.SetProperties({"Opacity": 70.0})
        props = lambda it: {k: (it.GetProperties() or {}).get(k) for k in keys} | {    # noqa: E731
            "start": it.GetStart(), "dur": it.GetDuration(), "left": it.GetLeftOffset()}
        before = props(ti)
        OS.set_values(rf, {"text": "REFRESHED", "color": "#22cc88"})
        rr = subprocess.run([PY, str(LAB / "tools" / "overlay.py"), "render", str(rf)], capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
        pname, newcopy, swaps = OVL.refresh(rf, r)
        after = props(ti)
        rep4c = {"render_ok": rr.returncode == 0, "render_tail": (rr.stdout + rr.stderr)[-300:], "project": pname,
                 "first_copy": first.name, "new_copy": newcopy.name, "swaps": swaps, "kept": before == after,
                 "before": before, "after": after}
        print(f"   render while Resolve uses the copy: {'ok' if rr.returncode == 0 else 'FAILED'}; refresh: "
              f"{sum(w['ok'] for w in swaps)}/{len(swaps)} swapped {first.name} -> {newcopy.name}; hand edits kept: "
              f"{before == after}", flush=True)
        report["refresh_tool"] = rep4c
        d4c = WORK / "r_refresh_tool"
        frames_dirs.append(d4c)
        compare("refresh_tool", render(p, tlr, 0, 29, d4c, "rt"), 0,
                [dict(name="refresh_title", mov=rf / "refresh_title.mov", a=0, n=30, dx=-30, opacity=0.7)])
        p.SetCurrentTimeline(tl)

        # ---- 5. Resolve Color Management (what a colour-managed project does to the overlay)
        print("5. Resolve Color Management (SDR Rec.709) ...", flush=True)
        items[col1].ReplaceClip(str(col1))
        n_.SetProperties({"Pan": 0.0})
        n_.SetProperties({"Opacity": 100.0})
        s_.SetProperties({"Opacity": 100.0})
        for k, v in (("colorScienceMode", "davinciYRGBColorManagedv2"), ("isAutoColorManage", "1"),
                     ("rcmPresetMode", "SDR")):
            if not p.SetSettings({k: v}):
                print(f"   note: {k} = {v} refused", flush=True)
        report["rcm_settings"] = {k: (p.GetSettings() or {}).get(k) for k in ("colorScienceMode", "isAutoColorManage",
                                                               "rcmPresetMode", "colorSpaceTimeline",
                                                               "colorSpaceTimelineGamma", "colorSpaceOutput",
                                                               "colorSpaceOutputGamma")}
        report["rcm_input"] = {m.stem: items[m].GetClipProperty("Input Color Space") for m in (plate_mov, col1)}
        print("   ", report["rcm_settings"], report["rcm_input"], flush=True)
        d5 = WORK / "r_rcm"
        frames_dirs.append(d5)
        fr5 = render(p, tl, 92, 103, d5, "cm")
        compare("rcm", fr5, 92, segs)
        fr5b = render(p, tl, 128, 128, WORK / "r_rcm_plate", "cp")
        frames_dirs.append(WORK / "r_rcm_plate")
        compare("rcm_plate", fr5b, 128, segs)

        # ---- 5b. which per-clip Input Color Space makes a colour-managed project show the files as they are
        print("5b. Color Management: per-clip Input Color Space ...", flush=True)
        report["rcm_fix"] = {}
        for cs in ("Rec.709 Gamma 2.4", "Rec.709-A", "sRGB", "Gamma 2.4", "Rec.709 (Scene)"):
            took = [bool(items[m].SetClipProperty("Input Color Space", cs)) for m in (plate_mov, col1)]
            got = items[col1].GetClipProperty("Input Color Space")
            if not all(took):
                print(f"   {cs!r}: refused (the clip says {got!r})", flush=True)
                report["rcm_fix"][cs] = {"refused": True, "now": got}
                continue
            key = "rcm_" + "".join(ch if ch.isalnum() else "_" for ch in cs).strip("_")
            dd = WORK / f"r_{key}"
            frames_dirs.append(dd)
            compare(key, render(p, tl, 92, 103, dd, "cs"), 92, segs)
            report["rcm_fix"][cs] = report["cases"][key]
    finally:
        try:
            pm.SaveProject()
            pm.CloseProject(pm.GetCurrentProject())
            pm.DeleteProject(SCRATCH)
        except Exception as ex:                    # noqa: BLE001
            print("note: could not delete the scratch project:", ex, flush=True)
        if back and back in (pm.GetProjectListInCurrentFolder() or []):
            pm.LoadProject(back)
        if started and not a.no_quit:
            try:
                r.Quit()
            except Exception:                      # noqa: BLE001
                pass
        if not a.keep_frames:
            for d in frames_dirs:
                shutil.rmtree(d, ignore_errors=True)
        (WORK / "report.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
        print("report:", WORK / "report.json", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
