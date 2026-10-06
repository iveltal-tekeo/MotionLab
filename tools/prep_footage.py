"""Decode a project's footage once into a frame cache for the renderer. The user's files are only read.

    .venv\\Scripts\\python tools\\prep_footage.py <project name or folder> [--fps 25] [--width 1520] [--height 1080]

For every video file directly inside projects\\<name>\\ it writes, into projects\\<name>\\build\\:
  sources.json             stable source IDs (A, B, ...) and the SHA-256 of every file
  cache\\<ID>.u8 + .json    grey frames at the target fps, scaled so one frame covers the output frame
  cache\\<ID>_stats.npz     per cache frame: luma mean/p05/p95, motion, sharpness, global shift (pan) in % of width
Re-running skips sources whose cache is complete and whose file is unchanged.
Levels: ffmpeg's format=gray already maps video range (16-235) to full range, so the cache is stored as decoded
("levels": "single" in <ID>.json). Caches written before 2026-10-06 expanded the range a second time; they carry no
"single" mark and count as "double" (plans made on them, like test_4am v1, declare "levels": "double").
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab.probe import probe  # noqa: E402
from motionlab.project import Project  # noqa: E402
from motionlab.util import log, read_json, setup_console, tool, write_json  # noqa: E402

def cache_size(w: int, h: int, ow: int, oh: int) -> tuple[int, int]:
    s = max(ow / w, oh / h)                       # cover-fit: one cached frame covers the output frame at 1x
    return int(round(w * s / 2)) * 2, int(round(h * s / 2)) * 2


def prep_source(prj: Project, sid: str, ent: dict, fps_out: float, ow: int, oh: int) -> dict:
    src = Path(ent["path"])
    meta_p = prj.cache / f"{sid}.json"
    if meta_p.exists():
        m = read_json(meta_p)
        if (m.get("fingerprint") == ent["fingerprint"] and m.get("fps") == fps_out and m.get("complete")
                and m.get("out_size") == [ow, oh] and (prj.cache / f"{sid}.u8").exists()):
            log(f"{sid} {src.name}: cache up to date ({m['frames']} frames)")
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
    vf = f"{pick}scale={cw}:{ch}:flags=area,format=gray"
    cmd = [tool("ffmpeg"), "-v", "error", "-nostdin", "-i", str(src), "-map", "0:v:0", "-vf", vf,
           "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    data_p = prj.check(prj.cache / f"{sid}.u8")
    prj.cache.mkdir(parents=True, exist_ok=True)
    out_f = open(data_p, "wb")
    sw, sh = cw // 4, ch // 4
    stats = {k_: np.zeros(expected, np.float32) for k_ in
             ("luma", "p05", "p95", "motion", "sharp", "tx", "ty", "shift_resp")}
    win = cv2.createHanningWindow((sw, sh), cv2.CV_32F)
    prev = None
    n = 0
    fsize = cw * ch
    log(f"{sid} {src.name}: {w}x{h} {fps_in:g} fps -> cache {cw}x{ch} @ {fps_out:g} fps "
        f"({'every %dth frame' % k if k else 'fps filter'}), ~{expected} frames")
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=fsize * 4)
    try:
        while n < expected:
            buf = p.stdout.read(fsize)
            if len(buf) < fsize:
                break
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
            "levels": "single", "levels_note": "full range as decoded by ffmpeg format=gray (video range expanded once)",
            "complete": True}
    write_json(prj.check(meta_p), meta)
    log(f"{sid}: {n} frames cached ({n / fps_out:.2f} s)")
    return meta


def load_cache(prj: Project, sid: str):
    m = read_json(prj.cache / f"{sid}.json")
    arr = np.memmap(prj.cache / f"{sid}.u8", dtype=np.uint8, mode="r", shape=(m["frames"], m["height"], m["width"]))
    st = dict(np.load(prj.cache / f"{sid}_stats.npz"))
    return m, arr, st


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
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
            prep_source(prj, sid, ent, a.fps, a.width, a.height)
    bad = prj.verify_sources()
    print("sources unchanged:", "yes" if not bad else f"NO - {bad}")
    for sid, ent in sorted(man["sources"].items()):
        print(f"  {sid} = {ent['name']}")
    return 0 if not bad else 3


if __name__ == "__main__":
    sys.exit(main())
