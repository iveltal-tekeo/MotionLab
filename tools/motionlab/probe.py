"""ffprobe wrapper: stream info, CFR/VFR detection, CFR proxy creation."""
from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

import numpy as np

from .util import log, run, tool

STANDARD_RATES = [23.976, 24.0, 25.0, 29.97, 30.0, 47.952, 48.0, 50.0, 59.94, 60.0, 100.0, 119.88, 120.0]


def _frac(s: str | None) -> float | None:
    if not s or s in ("0/0", "N/A"):
        return None
    try:
        v = float(Fraction(s))
        return v if v > 0 else None
    except (ValueError, ZeroDivisionError):
        return None


def _float(s) -> float | None:
    try:
        v = float(s)
        return v if np.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def snap_rate(fps: float) -> float:
    best = min(STANDARD_RATES, key=lambda r: abs(r - fps))
    return best if abs(best - fps) / fps < 0.004 else round(fps, 3)


def rate_fraction(fps: float) -> str:
    """ffmpeg-friendly exact rate string (30000/1001 for 29.97 etc.)."""
    for r, s in ((23.976, "24000/1001"), (29.97, "30000/1001"), (47.952, "48000/1001"),
                 (59.94, "60000/1001"), (119.88, "120000/1001")):
        if abs(fps - r) < 0.002:
            return s
    f = Fraction(fps).limit_denominator(1001)
    return f"{f.numerator}/{f.denominator}"


def probe(path: Path) -> dict:
    out = run([tool("ffprobe"), "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]).stdout
    data = json.loads(out)
    streams = data.get("streams", [])
    vids = [s for s in streams if s.get("codec_type") == "video"
            and not s.get("disposition", {}).get("attached_pic")]
    if not vids:
        raise SystemExit(f"no video stream in {path}")
    v = vids[0]
    auds = [s for s in streams if s.get("codec_type") == "audio"]
    a = auds[0] if auds else None
    fmt = data.get("format", {})

    rotation = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rotation = int(round(_float(sd["rotation"]) or 0))
    if not rotation and "rotate" in (v.get("tags") or {}):
        rotation = int(v["tags"]["rotate"])
    rotation %= 360

    w, h = int(v["width"]), int(v["height"])
    sar = _frac(v.get("sample_aspect_ratio")) or 1.0
    disp_w, disp_h = (h, w) if rotation in (90, 270) else (w, h)
    if rotation in (90, 270):
        sar = 1.0 / sar
    disp_aspect = disp_w * sar / disp_h

    r_fps = _frac(v.get("r_frame_rate"))
    avg_fps = _frac(v.get("avg_frame_rate"))
    duration = _float(v.get("duration")) or _float(fmt.get("duration"))
    nb = v.get("nb_frames")
    nb = int(nb) if nb and str(nb).isdigit() else None
    v_start = _float(v.get("start_time")) or 0.0
    a_start = (_float(a.get("start_time")) or 0.0) if a else None

    hdr = (v.get("color_transfer") in ("smpte2084", "arib-std-b67"))
    return {
        "path": str(path),
        "container": fmt.get("format_name"),
        "size_bytes": int(fmt.get("size", 0) or 0),
        "duration_s": duration,
        "video": {
            "codec": v.get("codec_name"), "profile": v.get("profile"), "pix_fmt": v.get("pix_fmt"),
            "width": w, "height": h, "rotation": rotation, "sar": sar,
            "display_width": int(round(disp_w * sar)),
            "display_height": int(disp_h),
            "display_aspect": disp_aspect,
            "r_frame_rate": v.get("r_frame_rate"), "avg_frame_rate": v.get("avg_frame_rate"),
            "r_fps": r_fps, "avg_fps": avg_fps, "nb_frames": nb, "start_time": v_start,
            "bit_rate": _float(v.get("bit_rate")), "field_order": v.get("field_order"),
            "color_transfer": v.get("color_transfer"), "color_primaries": v.get("color_primaries"),
            "hdr": hdr,
        },
        "audio": None if not a else {
            "codec": a.get("codec_name"), "sample_rate": int(a.get("sample_rate", 0) or 0),
            "channels": a.get("channels"), "start_time": a_start,
            "duration_s": _float(a.get("duration")),
        },
    }


def frame_timestamps(path: Path) -> np.ndarray:
    """Presentation timestamps (s) of every video packet, sorted."""
    out = run([tool("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
               "packet=pts_time", "-of", "csv=p=0", str(path)]).stdout
    ts = []
    for line in out.splitlines():
        line = line.strip().rstrip(",")
        if line and line != "N/A":
            try:
                ts.append(float(line))
            except ValueError:
                pass
    return np.sort(np.array(ts, dtype=np.float64))


def analyze_timing(pts: np.ndarray, nominal_fps: float | None, cfg: dict) -> dict:
    """Decide CFR vs VFR from packet timestamps."""
    if len(pts) < 3:
        return {"vfr": False, "reason": "too few frames to judge", "n": int(len(pts))}
    dt = np.diff(pts)
    dt = dt[dt > 0]
    med = float(np.median(dt))
    # timebase-rounding tolerance: ms-based containers alternate 33/34 ms at 29.97 fps
    tol = max(cfg["vfr_tolerance_frames"] * med, 0.0015)
    irregular = np.abs(dt - med) > tol
    frac = float(irregular.mean())
    gaps = int((dt > 1.5 * med).sum())
    vfr = frac > cfg["vfr_min_irregular_fraction"] or gaps > 0
    est_fps = 1.0 / med
    if nominal_fps and abs(nominal_fps - est_fps) / est_fps < 0.01:
        est_fps = nominal_fps
    return {
        "vfr": bool(vfr), "n": int(len(pts)), "median_dt": med, "min_dt": float(dt.min()),
        "max_dt": float(dt.max()), "irregular_fraction": frac, "gaps": gaps,
        "fps_from_timestamps": est_fps,
        "reason": (f"{frac:.1%} of frame intervals deviate > {tol*1000:.1f} ms, {gaps} gaps"
                   if vfr else "all frame intervals equal within tolerance"),
    }


def choose_analysis_fps(info: dict, timing: dict) -> float:
    v = info["video"]
    cands = [x for x in (v["r_fps"], v["avg_fps"], timing.get("fps_from_timestamps")) if x]
    if timing.get("vfr"):
        # VFR: prefer the average rate snapped to a standard rate
        base = v["avg_fps"] or timing.get("fps_from_timestamps") or v["r_fps"]
    else:
        base = v["r_fps"] or v["avg_fps"] or timing.get("fps_from_timestamps")
    if not base:
        base = cands[0] if cands else 30.0
    return snap_rate(base)


def proxy_fill_map(pts: np.ndarray, fps: float, n_out: int) -> np.ndarray:
    """For a CFR proxy made with the fps filter: 1 where a proxy frame had no source frame of its own
    (i.e. the fps filter duplicated the previous frame to fill a VFR gap)."""
    if len(pts) == 0:
        return np.zeros(n_out, dtype=np.int8)
    slots = np.round((pts - pts[0]) * fps).astype(np.int64)
    filled = np.ones(n_out, dtype=np.int8)
    valid = slots[(slots >= 0) & (slots < n_out)]
    filled[valid] = 0
    return filled


def make_cfr_proxy(src: Path, dst: Path, fps: float, info: dict, cfg: dict) -> None:
    v = info["video"]
    vf = [f"fps={rate_fraction(fps)}"]
    if v["display_width"] > cfg["proxy_max_width"]:
        vf.append(f"scale={cfg['proxy_max_width']}:-2:flags=lanczos")
    cmd = [tool("ffmpeg"), "-y", "-v", "error", "-i", str(src), "-map", "0:v:0", "-map", "0:a:0?",
           "-vf", ",".join(vf), "-c:v", "libx264", "-preset", "fast", "-crf", str(cfg["proxy_crf"]),
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", str(dst)]
    log(f"VFR source -> making CFR proxy at {fps} fps: {dst.name}")
    run(cmd)
