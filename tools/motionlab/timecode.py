"""Frame <-> timecode conversion.

Frames are 0-based (frame 0 = first frame of the analyzed video). Timecode counts frames at the
video's nominal rate (23.976 -> 24, 29.97 -> 30, 59.94 -> 60), non-drop by default, which is what
DaVinci Resolve shows for a clip that starts at 00:00:00:00. Drop-frame (';' separator) is
available for 29.97/59.94 via config timecode.drop_frame.
"""
from __future__ import annotations

import re


def nominal_rate(fps: float) -> int:
    return max(1, int(round(fps)))


def is_drop_rate(fps: float) -> bool:
    return abs(fps - 29.97) < 0.01 or abs(fps - 59.94) < 0.02


def frame_to_tc(n: int, fps: float, drop: bool = False) -> str:
    n = int(n)
    neg = n < 0
    n = abs(n)
    nom = nominal_rate(fps)
    sep = ":"
    if drop and is_drop_rate(fps):
        d = 2 if nom == 30 else 4
        per10 = nom * 600 - 9 * d
        per1 = nom * 60 - d
        tens, rem = divmod(n, per10)
        adj = 9 * d * tens + (d * ((rem - d) // per1) if rem >= d else 0)
        n = n + adj
        sep = ";"
    ff = n % nom
    total_s = n // nom
    ss = total_s % 60
    mm = (total_s // 60) % 60
    hh = total_s // 3600
    return f"{'-' if neg else ''}{hh:02d}:{mm:02d}:{ss:02d}{sep}{ff:02d}"


def tc_to_frame(tc: str, fps: float) -> int:
    m = re.fullmatch(r"\s*(\d+):(\d{2}):(\d{2})([:;.])(\d{2})\s*", tc)
    if not m:
        raise ValueError(f"bad timecode: {tc!r}")
    hh, mm, ss, sep, ff = int(m[1]), int(m[2]), int(m[3]), m[4], int(m[5])
    nom = nominal_rate(fps)
    n = ((hh * 60 + mm) * 60 + ss) * nom + ff
    if sep == ";" and is_drop_rate(fps):
        d = 2 if nom == 30 else 4
        total_min = hh * 60 + mm
        n -= d * (total_min - total_min // 10)
    return n


def frame_to_seconds(n: float, fps: float) -> float:
    return float(n) / fps


def label(n: int, fps: float, drop: bool = False) -> str:
    """Canonical human label: 'f123 (00:00:04:03)'."""
    return f"f{int(n)} ({frame_to_tc(n, fps, drop)})"


def range_label(a: int, b: int, fps: float, drop: bool = False) -> str:
    if a == b:
        return label(a, fps, drop)
    return f"f{int(a)}-{int(b)} ({frame_to_tc(a, fps, drop)} - {frame_to_tc(b, fps, drop)})"
