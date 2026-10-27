"""Decode a project's footage once into a frame cache for the renderer. The user's files are only read.

    .venv\\Scripts\\python tools\\prep_footage.py <project name or folder> [--grey] [--fps 25] [--width 1520] [--height 1080]
                                                [--full]

Since 0.6.1 (many clips: a full cache was ~5 GB per minute of footage in a vertical edit - 36 clips / 6.5 min: 33 GB
in 131 s, now 2.1 GB in 35 s) every clip is read ONCE into a light cache - every frame at a quarter of the cache's
width and height (cache\\<ID>.light.yuv + .json: the stats below, the storyboards, the clip catalogue) - and its full
cache starts empty (SPARSE, meta "segments"): render_video.py fills the full frames a plan shows (+ HANDLE frames)
right before it renders (ensure() / fill(), the same frame grid: ffmpeg's fps filter anchored at the clip's first
frame). A full cache made before stays as it is; --full = every frame full size as before.

For every video file and photo directly inside projects\\<name>\\ (never the "._" files a Mac / iPhone leaves there:
motionlab\\project.py clip_files) it writes, into projects\\<name>\\build\\:
  sources.json                     stable source IDs (A, B, ...) and the SHA-256 of every file
  cache\\<ID>.light.yuv + .json     every frame, small (I420, ~0.35 GB per minute) - the default
  cache\\<ID>.color.yuv + .json     colour frames (YUV 4:2:0, ~3.9 GB per minute of footage at 1520x1140 when full) at
                                   the target fps, scaled so one frame covers the output frame (never above the clip's
                                   own size) - sparse by default (only what plans show), all with --full
  cache\\<ID>.u8 + .json            --grey: grey frames (~2.6 GB per minute) for black-and-white edits (test_4am)
  cache\\<ID>_stats.npz             per cache frame: luma mean/p05/p95, motion, sharpness, global shift (pan) in % of
                                   width
A photo (2026-10-24: .jpg .png .webp .heic .heif .avif .bmp .tif .gif) is a cache of ONE frame, the right way up
(motionlab\\photos.py) - a clip layer shows it on every frame of its shot (meta "photo": true, no sound, no motion).
Formats and readers: tools\\motionlab\\footage.py (edit scripts take plan["sources"] from footage.plan_sources).
Re-running skips sources whose cache is complete and whose file is unchanged. It refuses to start a cache that would
leave less than 2 GB free on the disk.
Colour: decoded with the clip's own colour matrix and range (Rec.709 when untagged and HD); HDR clips (PQ / HLG) are
converted without tone mapping, so they look flat - a warning says so.
Levels: both caches hold full-range values ("levels": "single"). Grey caches written before 2026-10-06 expanded the
range a second time; they carry no "single" mark and count as "double" (plans made on them, like test_4am v1,
declare "levels": "double").
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import footage as FC  # noqa: E402
from motionlab.probe import probe  # noqa: E402
from motionlab.project import Project  # noqa: E402
from motionlab.signals import StderrTail  # noqa: E402
from motionlab.util import log, read_json, setup_console, tool, write_json  # noqa: E402

KEEP_FREE = 2e9                                   # bytes that must stay free on the disk after a cache


def cache_size(w: int, h: int, ow: int, oh: int) -> tuple[int, int]:
    """Cover-fit: one cached frame covers the output frame at 1x - but never above the clip's own size (0.4: a
    horizontal clip in a vertical edit would be cached 1.8x up, ~3x the disk, for no detail; the compositor scales
    up when it draws)."""
    s = min(1.0, max(ow / w, oh / h))
    return int(round(w * s / 2)) * 2, int(round(h * s / 2)) * 2


def color_args(v: dict) -> str:
    """scale-filter options so ffmpeg converts YUV -> RGB with the clip's own matrix and range."""
    cs = (v.get("color_space") or "").lower()
    if cs == "bt709":
        mat = "bt709"
    elif cs.startswith("bt2020"):
        mat = "bt2020"
    elif cs in ("smpte170m", "bt470bg", "bt601", "fcc"):
        mat = "bt601"
    else:                                          # untagged: HD and larger are Rec.709 by convention
        mat = "bt709" if (v.get("height") or 0) >= 720 else "bt601"
    rng = "pc" if v.get("color_range") == "pc" else "tv"
    return f":in_color_matrix={mat}:in_range={rng}"


def prep_photo(prj: Project, sid: str, ent: dict, fps_out: float, ow: int, oh: int, color: bool = True) -> dict:
    """A photo's cache: one frame, cover-fit like a clip's (never above the photo's own size), the stats of that
    frame (no motion)."""
    from motionlab import photos as PH
    src = Path(ent["path"])
    data_rel, meta_rel = FC.paths(prj.cache, sid, color)
    if meta_rel.exists():
        m = read_json(meta_rel)
        if (m.get("fingerprint") == ent["fingerprint"] and m.get("fps") == fps_out and m.get("complete")
                and m.get("out_size") == [ow, oh] and data_rel.exists()):
            log(f"{sid} {src.name}: photo cache up to date")
            return m
    im = PH.open_rgb(src)
    w, h = im.size
    cw, ch = cache_size(w, h, ow, oh)
    from PIL import Image
    rgb = np.asarray(im.resize((cw, ch), Image.LANCZOS) if (cw, ch) != (w, h) else im)
    prj.cache.mkdir(parents=True, exist_ok=True)
    fr = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    with open(prj.check(data_rel), "wb") as f:
        f.write((FC.encode(rgb) if color else fr).tobytes())
    sm = cv2.resize(fr, (cw // 4, ch // 4), interpolation=cv2.INTER_AREA).astype(np.float32)
    p05, p95 = np.percentile(sm, [5, 95]) / 2.55
    np.savez(prj.check(prj.cache / f"{sid}_stats.npz"),
             **{"luma": np.array([sm.mean() / 2.55], np.float32), "p05": np.array([p05], np.float32),
                "p95": np.array([p95], np.float32), "sharp": np.array([cv2.Laplacian(sm, cv2.CV_32F).var()], np.float32),
                **{k_: np.zeros(1, np.float32) for k_ in ("motion", "tx", "ty", "shift_resp")}})
    meta = {"id": sid, "source": str(src), "name": src.name, "fingerprint": ent["fingerprint"], "photo": True,
            "src_width": w, "src_height": h, "src_fps": None, "src_frames": 1,
            "fps": fps_out, "step": None, "frames": 1, "width": cw, "height": ch, "out_size": [ow, oh],
            "format": "i420" if color else "gray", "levels": "single",
            "levels_note": "a photo, decoded by Pillow (full range, EXIF rotation applied)", "complete": True}
    write_json(prj.check(meta_rel), meta)
    log(f"{sid} {src.name}: photo {w}x{h} -> {'colour' if color else 'grey'} cache {cw}x{ch} (one frame)")
    return meta


def prep_source(prj: Project, sid: str, ent: dict, fps_out: float, ow: int, oh: int, color: bool = True) -> dict:
    src = Path(ent["path"])
    if ent.get("photo"):
        return prep_photo(prj, sid, ent, fps_out, ow, oh, color)
    data_rel, meta_rel = FC.paths(prj.cache, sid, color)
    if meta_rel.exists():
        m = read_json(meta_rel)
        if (m.get("fingerprint") == ent["fingerprint"] and m.get("fps") == fps_out and m.get("complete")
                and m.get("out_size") == [ow, oh] and data_rel.exists()):
            log(f"{sid} {src.name}: {'colour' if color else 'grey'} cache up to date ({m['frames']} frames)")
            return m
    info = probe(src)
    v = info["video"]
    w, h = v["display_width"], v["display_height"]
    fps_in = v["avg_fps"] or v["r_fps"]
    cw, ch = cache_size(w, h, ow, oh)
    ratio = fps_in / fps_out
    if abs(ratio - round(ratio)) < 1e-3 and round(ratio) >= 1:
        k = int(round(ratio))
        pick = f"select='not(mod(n,{k}))'," if k > 1 else ""
        expected = int(np.ceil((v["nb_frames"] or round(info["duration_s"] * fps_in)) / k))
    else:
        k = None
        pick = f"fps={fps_out},"
        expected = int(np.ceil(info["duration_s"] * fps_out)) + 2
    prj.cache.mkdir(parents=True, exist_ok=True)
    need = expected * FC.frame_bytes(cw, ch, color)
    free = shutil.disk_usage(prj.cache).free + (data_rel.stat().st_size if data_rel.exists() else 0)
    if need > free - KEEP_FREE:
        raise SystemExit(f"{sid} {src.name}: the {'colour' if color else 'grey'} cache needs {need / 1e9:.1f} GB but "
                         f"only {free / 1e9:.1f} GB are free (2 GB must stay free) - make room (the app's Storage "
                         f"page / tools\\storage.py)" + ("" if not color else ", or use --grey for a black-and-white "
                                                         "edit (2/3 of the size)"))
    if v.get("hdr") and color:
        log(f"  WARNING {sid}: HDR source ({v.get('color_transfer')}) - converted without tone mapping, it will "
            f"look flat; export an SDR (Rec.709) version for exact colours")
    if color:                     # accurate rounding: 10-bit clips otherwise come out ~2/255 too dark
        vf = f"{pick}scale={cw}:{ch}:flags=area+accurate_rnd+full_chroma_int{color_args(v)},format=rgb24"
        pix, fsize = "rgb24", cw * ch * 3
    else:
        vf = f"{pick}scale={cw}:{ch}:flags=area,format=gray"
        pix, fsize = "gray", cw * ch
    cmd = [tool("ffmpeg"), "-v", "error", "-nostdin", "-i", str(src), "-map", "0:v:0", "-vf", vf,
           "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", pix, "-"]
    data_p = prj.check(data_rel)
    out_f = open(data_p, "wb")
    sw, sh = cw // 4, ch // 4
    stats = {k_: np.zeros(expected, np.float32) for k_ in
             ("luma", "p05", "p95", "motion", "sharp", "tx", "ty", "shift_resp")}
    win = cv2.createHanningWindow((sw, sh), cv2.CV_32F)
    prev = None
    n = 0
    log(f"{sid} {src.name}: {w}x{h} {fps_in:g} fps -> {'colour' if color else 'grey'} cache {cw}x{ch} @ "
        f"{fps_out:g} fps ({'1 of every %d frames' % k if k and k > 1 else 'every frame' if k else 'fps filter'}), "
        f"~{expected} frames, "
        f"~{need / 1e9:.1f} GB")
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=fsize * 4)
    tail = StderrTail(p.stderr)            # read while decoding: a full stderr pipe would stall ffmpeg for ever
    try:
        while n < expected:
            buf = p.stdout.read(fsize)
            if len(buf) < fsize:
                break
            if color:
                rgb = np.frombuffer(buf, np.uint8).reshape(ch, cw, 3)
                out_f.write(FC.encode(rgb).tobytes())
                fr = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)                 # the stats are measured on luma
            else:
                fr = np.frombuffer(buf, np.uint8).reshape(ch, cw)          # already full range (format=gray)
                out_f.write(fr.tobytes())
            sm = cv2.resize(fr, (sw, sh), interpolation=cv2.INTER_AREA)
            smf = sm.astype(np.float32)
            stats["luma"][n] = smf.mean() / 2.55
            stats["p05"][n], stats["p95"][n] = np.percentile(smf, [5, 95]) / 2.55
            stats["sharp"][n] = cv2.Laplacian(smf, cv2.CV_32F).var()
            if prev is not None:
                stats["motion"][n] = np.abs(smf - prev).mean()
                (dx, dy), resp = cv2.phaseCorrelate(prev, smf, win)
                stats["tx"][n], stats["ty"][n] = 100.0 * dx / sw, 100.0 * dy / sw
                stats["shift_resp"][n] = resp
            prev = smf
            n += 1
            if n % 250 == 0:
                log(f"  {sid}: {n} frames")
    finally:
        out_f.close()
        p.stdout.close()
        p.wait()
        err = tail.text()
    if p.returncode not in (0, None) and n == 0:
        raise RuntimeError(f"ffmpeg failed on {src}: {err[-1500:]}")
    np.savez(prj.check(prj.cache / f"{sid}_stats.npz"), **{k_: a[:n] for k_, a in stats.items()})
    meta = {"id": sid, "source": str(src), "name": src.name, "fingerprint": ent["fingerprint"],
            "src_width": w, "src_height": h, "src_fps": fps_in, "src_frames": v["nb_frames"],
            "fps": fps_out, "step": k, "frames": n, "width": cw, "height": ch, "out_size": [ow, oh],
            "format": "i420" if color else "gray", "levels": "single",
            "levels_note": ("full-range RGB as decoded by ffmpeg (video range expanded once), stored as I420"
                            if color else "full range as decoded by ffmpeg format=gray (video range expanded once)"),
            "complete": True}
    write_json(prj.check(meta_rel), meta)
    log(f"{sid}: {n} frames cached ({n / fps_out:.2f} s)")
    return meta


# ------------------------------------------------------------------------------------------------ light + sparse
# 0.6.1 (the user: "quality over quantity ... u are having a bad time editing videos when i give u lots of b-rolls"):
# a full cache is ~5 GB per minute of footage in a vertical edit (zz_many_clips, 36 clips / 6.5 min: 33 GB, 131 s).
# Now every frame is read once into a LIGHT cache (a quarter of the cache's width and height: the stats, the
# storyboards, the clip catalogue) and the full cache is SPARSE - only the frames a plan shows, decoded by ensure()
# right before a render (render_video.py). Both reads put the clip on one grid of frames: ffmpeg's fps filter
# anchored at the clip's first frame time (-copyts), so a frame filled later is the very frame the light cache has.
LIGHT_DIV = 4                                   # the light cache = the full cache's size / 4 (the stats' size)
HANDLE = 15                                     # frames filled around what a plan shows (a trim needs no refill)


def _grid(fps_out: float, t0: float) -> str:
    return f"fps=fps={fps_out:g}:start_time={t0:.6f}:round=near"


def _frames(cmd: list[str], w: int, h: int, n_max: int):
    """RGB frames of one ffmpeg read (rawvideo rgb24 on stdout) - at most n_max."""
    size = w * h * 3
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=size * 4)
    tail = StderrTail(p.stderr)
    n = 0
    try:
        while n < n_max:
            buf = p.stdout.read(size)
            if len(buf) < size:
                break
            n += 1
            yield np.frombuffer(buf, np.uint8).reshape(h, w, 3)
    finally:
        p.stdout.close()
        p.kill() if n >= n_max else None
        p.wait()
        if p.returncode not in (0, None) and n == 0 and p.returncode != 1 and n_max:
            raise RuntimeError(f"ffmpeg failed: {tail.text()[-1500:]}")


def prep_light(prj: Project, sid: str, ent: dict, fps_out: float, ow: int, oh: int, color: bool = True) -> dict:
    """A clip read once: its light cache (every frame, small), its stats and an empty sparse full cache."""
    src = Path(ent["path"])
    if ent.get("photo"):
        return prep_photo(prj, sid, ent, fps_out, ow, oh, color)
    data_rel, meta_rel = FC.paths(prj.cache, sid, color)
    lp, lmp = FC.light_paths(prj.cache, sid)
    if meta_rel.exists() and lmp.exists():
        m = read_json(meta_rel)
        if (m.get("fingerprint") == ent["fingerprint"] and m.get("fps") == fps_out and m.get("complete")
                and m.get("out_size") == [ow, oh] and data_rel.exists() and lp.exists()):
            log(f"{sid} {src.name}: light cache up to date ({m['frames']} frames, {len(m.get('segments') or [])} "
                f"filled run(s))")
            return m
    info = probe(src)
    v = info["video"]
    w, h = v["display_width"], v["display_height"]
    fps_in = v["avg_fps"] or v["r_fps"]
    t0 = float(v.get("start_time") or 0.0)
    cw, ch = cache_size(w, h, ow, oh)
    lw, lh = max(2, cw // LIGHT_DIV // 2 * 2), max(2, ch // LIGHT_DIV // 2 * 2)
    expected = int(np.ceil(info["duration_s"] * fps_out)) + 2
    prj.cache.mkdir(parents=True, exist_ok=True)
    need = expected * FC.frame_bytes(lw, lh, True)
    if need > shutil.disk_usage(prj.cache).free - KEEP_FREE:
        raise SystemExit(f"{sid} {src.name}: the light cache needs {need / 1e9:.1f} GB - make room (Storage)")
    if v.get("hdr") and color:
        log(f"  WARNING {sid}: HDR source ({v.get('color_transfer')}) - converted without tone mapping, it will "
            f"look flat; export an SDR (Rec.709) version for exact colours")
    vf = f"{_grid(fps_out, t0)},scale={lw}:{lh}:flags=area+accurate_rnd+full_chroma_int{color_args(v)},format=rgb24"
    cmd = [tool("ffmpeg"), "-v", "error", "-nostdin", "-copyts", "-i", str(src), "-map", "0:v:0", "-vf", vf,
           "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    log(f"{sid} {src.name}: {w}x{h} {fps_in:g} fps -> light cache {lw}x{lh} @ {fps_out:g} fps, ~{expected} frames, "
        f"~{need / 1e9:.2f} GB (full {cw}x{ch} frames only for what a plan shows)")
    stats = {k_: np.zeros(expected, np.float32) for k_ in
             ("luma", "p05", "p95", "motion", "sharp", "tx", "ty", "shift_resp")}
    win = cv2.createHanningWindow((lw, lh), cv2.CV_32F)
    prev, n = None, 0
    with open(prj.check(lp), "wb") as out_f:
        for rgb in _frames(cmd, lw, lh, expected):
            out_f.write(FC.encode(rgb).tobytes())
            smf = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
            stats["luma"][n] = smf.mean() / 2.55
            stats["p05"][n], stats["p95"][n] = np.percentile(smf, [5, 95]) / 2.55
            stats["sharp"][n] = cv2.Laplacian(smf, cv2.CV_32F).var()
            if prev is not None:
                stats["motion"][n] = np.abs(smf - prev).mean()
                (dx, dy), resp = cv2.phaseCorrelate(prev, smf.copy(), win)      # (copies: the window is applied
                stats["tx"][n], stats["ty"][n] = 100.0 * dx / lw, 100.0 * dy / lw    # in place on some sizes)
                stats["shift_resp"][n] = resp
            prev = smf
            n += 1
            if n % 500 == 0:
                log(f"  {sid}: {n} frames")
    if n == 0:
        raise RuntimeError(f"ffmpeg read no frame of {src}")
    np.savez(prj.check(prj.cache / f"{sid}_stats.npz"), **{k_: a[:n] for k_, a in stats.items()})
    write_json(prj.check(lmp), {"id": sid, "fingerprint": ent["fingerprint"], "frames": n, "width": lw, "height": lh,
                                "fps": fps_out, "format": "i420"})
    open(prj.check(data_rel), "wb").close()                 # the sparse full cache: nothing filled yet
    meta = {"id": sid, "source": str(src), "name": src.name, "fingerprint": ent["fingerprint"],
            "src_width": w, "src_height": h, "src_fps": fps_in, "src_frames": v["nb_frames"], "t0": t0,
            "fps": fps_out, "step": None, "frames": n, "width": cw, "height": ch, "out_size": [ow, oh],
            "format": "i420" if color else "gray", "levels": "single", "color_args": color_args(v),
            "levels_note": "full-range RGB as decoded by ffmpeg (video range expanded once)", "complete": True,
            "segments": []}
    write_json(prj.check(meta_rel), meta)
    log(f"{sid}: {n} frames read ({n / fps_out:.2f} s); light cache {lp.stat().st_size / 1e6:.0f} MB")
    return meta


def fill(cache: Path, sid: str, ranges: list[list[int]], log=log) -> int:
    """The full frames of `ranges` ([[first, last], ...] cache frames) into a sparse cache - only what is not there
    yet; -> frames decoded. A complete (old) cache needs nothing."""
    color = FC.paths(cache, sid, True)[1].exists()
    data, mp = FC.paths(cache, sid, color)
    m = read_json(mp)
    if m.get("segments") is None:
        return 0
    N, fps, t0, cw, ch = int(m["frames"]), float(m["fps"]), float(m.get("t0") or 0.0), int(m["width"]), int(m["height"])
    have = sorted([int(a), int(a) + int(c) - 1] for a, c, _ in m["segments"])
    todo = []
    for a, b in sorted([max(0, int(a)), min(N - 1, int(b))] for a, b in ranges):
        x = a
        for ha, hb in have:                          # the parts of a..b not filled yet
            if hb < x or ha > b:
                continue
            if ha > x:
                todo.append([x, ha - 1])
            x = max(x, hb + 1)
        if x <= b:
            todo.append([x, b])
    if not todo:
        return 0
    if shutil.disk_usage(cache).free - KEEP_FREE < sum(b - a + 1 for a, b in todo) * FC.frame_bytes(cw, ch, color):
        raise SystemExit(f"{sid}: not enough free disk for its frames - make room (Storage)")
    off = data.stat().st_size // FC.frame_bytes(cw, ch, color) if data.exists() else 0
    got_all = 0
    with open(data, "ab") as out_f:
        for a, b in todo:                               # (the fps filter pads from the clip's first tick after a seek, so
            vf = (f"{_grid(fps, t0)},trim=start_frame={a}:end_frame={b + 1},"     # its frame k is tick k - a trim by
                  f"scale={cw}:{ch}:flags=area+accurate_rnd+full_chroma_int{m.get('color_args', '')},format=rgb24")
            cmd = [tool("ffmpeg"), "-v", "error", "-nostdin", "-ss", f"{max(0.0, a / fps - 1.0):.6f}", "-copyts", "-i",   # time kept one frame too many)
                   m["source"], "-map", "0:v:0", "-vf", vf, "-fps_mode", "passthrough", "-f", "rawvideo",
                   "-pix_fmt", "rgb24", "-"]
            got = 0
            for rgb in _frames(cmd, cw, ch, b - a + 1):
                out_f.write((FC.encode(rgb) if color else cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)).tobytes())
                got += 1
            if got:
                m["segments"].append([a, got, off])
                off += got
                got_all += got
            if got < b - a + 1:
                log(f"  {sid}: f{a}-f{b} gave {got} frames (the clip's end?)")
    write_json(mp, m)
    log(f"{sid}: {got_all} full frame(s) filled in {len(todo)} run(s)")
    return got_all


def ensure(plan: dict, a: int | None = None, b: int | None = None, log=log) -> int:
    """Before a render: every sparse cache a plan reads holds the frames it shows over plan frames a..b (+ HANDLE)."""
    total = 0
    for sid, rs in FC.needed(plan, a, b, HANDLE).items():
        s = (plan.get("sources") or {}).get(sid)
        if not s or not s.get("cache"):
            continue
        total += fill(Path(s["cache"]).parent, sid, rs, log=log)
    return total


def _full_up_to_date(prj: Project, sid: str, ent: dict, fps: float, ow: int, oh: int, color: bool) -> bool:
    """A complete full cache made before 0.6.1 for this very file and size: kept as it is (never thrown away)."""
    data, mp = FC.paths(prj.cache, sid, color)
    if not (mp.exists() and data.exists()):
        return False
    m = read_json(mp)
    return (m.get("segments") is None and m.get("fingerprint") == ent["fingerprint"] and m.get("fps") == fps
            and m.get("complete") and m.get("out_size") == [ow, oh])


def load_cache(prj: Project, sid: str, color: bool | None = None):
    """(meta, frames memmap, stats) - color None = the colour cache if there is one (frames: footage.image)."""
    m, arr = FC.load(prj.cache, sid, color)
    st = dict(np.load(prj.cache / f"{sid}_stats.npz"))
    return m, arr, st


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--grey", "--gray", action="store_true", help="grey caches (black-and-white edits)")
    ap.add_argument("--fps", type=float, default=25.0)
    ap.add_argument("--width", type=int, default=1520)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--full", action="store_true", help="every frame full size (before 0.6.1); default: a light cache "
                    "of every frame + full frames only for what a plan shows (filled by render_video.py)")
    a = ap.parse_args()
    prj = Project(a.project)
    files = prj.footage_files()
    if not files:
        print(f"no videos or photos in {prj.dir}")
        return 1
    log(f"project {prj.name}: {len(files)} source file(s); hashing (read-only)")
    man = prj.register_sources()
    current = {str(f) for f in files}               # a junk file listed by an older version is never cached
    for sid, ent in sorted(man["sources"].items()):
        if Path(ent["path"]).exists() and ent["path"] in current:
            if a.full or _full_up_to_date(prj, sid, ent, a.fps, a.width, a.height, not a.grey):
                prep_source(prj, sid, ent, a.fps, a.width, a.height, color=not a.grey)
            else:
                prep_light(prj, sid, ent, a.fps, a.width, a.height, color=not a.grey)
    bad = prj.verify_sources()
    print("sources unchanged:", "yes" if not bad else f"NO - {bad}")
    from motionlab.draft import luma_dips
    for sid, ent in sorted(man["sources"].items()):
        st = prj.cache / f"{sid}_stats.npz"
        dips = luma_dips(np.load(st)["luma"]) if st.exists() else []
        ent["dips"] = dips                  # 0.5.3 (A7): cache frames that dip for 1-2 frames (a screen repaint)
        print(f"  {sid} = {ent['name']}" + (f" - {len(dips)} one-frame dip(s) (a screen recording's repaint?) at cache "
                                            f"f{', f'.join(map(str, dips[:8]))}" + (" ..." if len(dips) > 8 else "")
                                            + ": keep shots inside the clean runs" if dips else ""))
    write_json(prj.check(prj.manifest_path), man)
    return 0 if not bad else 3


if __name__ == "__main__":
    sys.exit(main())
