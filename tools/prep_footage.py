"""Decode a project's footage once into a frame cache for the renderer. The user's files are only read.

    .venv\\Scripts\\python tools\\prep_footage.py <project name or folder> [--grey] [--fps 25] [--width 1520] [--height 1080]

For every video file directly inside projects\\<name>\\ it writes, into projects\\<name>\\build\\:
  sources.json                     stable source IDs (A, B, ...) and the SHA-256 of every file
  cache\\<ID>.color.yuv + .json     colour frames (YUV 4:2:0, ~3.9 GB per minute of footage at 1520x1140) at the
                                   target fps, scaled so one frame covers the output frame - the default since 0.3.0
  cache\\<ID>.u8 + .json            --grey: grey frames (~2.6 GB per minute) for black-and-white edits (test_4am)
  cache\\<ID>_stats.npz             per cache frame: luma mean/p05/p95, motion, sharpness, global shift (pan) in % of
                                   width
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
from motionlab.util import log, read_json, setup_console, tool, write_json  # noqa: E402

KEEP_FREE = 2e9                                   # bytes that must stay free on the disk after a cache


def cache_size(w: int, h: int, ow: int, oh: int) -> tuple[int, int]:
    s = max(ow / w, oh / h)                       # cover-fit: one cached frame covers the output frame at 1x
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


def prep_source(prj: Project, sid: str, ent: dict, fps_out: float, ow: int, oh: int, color: bool = True) -> dict:
    src = Path(ent["path"])
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
        err = p.stderr.read().decode("utf-8", "replace")
        p.wait()
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
    a = ap.parse_args()
    prj = Project(a.project)
    files = prj.footage_files()
    if not files:
        print(f"no video files in {prj.dir}")
        return 1
    log(f"project {prj.name}: {len(files)} source file(s); hashing (read-only)")
    man = prj.register_sources()
    for sid, ent in sorted(man["sources"].items()):
        if Path(ent["path"]).exists():
            prep_source(prj, sid, ent, a.fps, a.width, a.height, color=not a.grey)
    bad = prj.verify_sources()
    print("sources unchanged:", "yes" if not bad else f"NO - {bad}")
    for sid, ent in sorted(man["sources"].items()):
        print(f"  {sid} = {ent['name']}")
    return 0 if not bad else 3


if __name__ == "__main__":
    sys.exit(main())
