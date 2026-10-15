"""Player copies (0.4.2.1): a small H.264 copy of a video for the app's player, made only when this PC's browser
cannot play the original (HEVC - TikTok's best format - needs Windows' HEVC Video Extension; AV1 / ProRes and others
may not play either). The page decides (canPlayType / MediaSource.isTypeSupported + the video's error event); the
server only says which codec a file has (ffprobe) and makes the copy as an app job (`player_copy`, group cpu).

Into .app\\player\\<key>.mp4, key = the source's path + size + modification time (a changed source gets a new copy);
height <= 720, sound kept, and the SAME frames at the SAME times (`-fps_mode passthrough`: no frame dropped or
repeated, every timestamp kept), so the player's frame numbers still match the analysis. The analysis keeps reading
the original; nothing here writes anywhere else (hard rule 1: the source is only read)."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from motionlab.util import LAB, tool

PLAYER = LAB / ".app" / "player"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
MAX_HEIGHT = 720
_codecs: dict[tuple, dict] = {}


def _sig(src: Path) -> tuple:
    st = src.stat()
    return str(src.resolve()), st.st_size, st.st_mtime_ns


def key(src: Path) -> str:
    return hashlib.sha1("|".join(map(str, _sig(src))).encode("utf-8")).hexdigest()[:16]


def copy_path(src: Path) -> Path:
    return PLAYER / f"{key(src)}.mp4"


def codec(src: Path) -> dict:
    """{"codec": "hevc", "tag": "hvc1", "height": 1920, "frames": n | None} of the first video stream (cached until the
    file changes)."""
    sig = _sig(src)
    if sig not in _codecs:
        out = subprocess.run([tool("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
                              "stream=codec_name,codec_tag_string,height,nb_frames", "-of", "json", str(src)],
                             capture_output=True, text=True, timeout=60, creationflags=NO_WINDOW)
        st = ((json.loads(out.stdout or "{}") or {}).get("streams") or [{}])[0]
        nb = str(st.get("nb_frames") or "")
        _codecs[sig] = {"codec": st.get("codec_name"), "tag": st.get("codec_tag_string"), "height": st.get("height"),
                        "frames": int(nb) if nb.isdigit() else None}
    return _codecs[sig]


def info(src: Path) -> dict:
    """What the page needs: the codec, and the player copy when it exists (its lab-relative path)."""
    c = copy_path(src)
    return {**codec(src), "copy": c.relative_to(LAB).as_posix() if c.is_file() else None}


def command(src: Path, dst: Path) -> list[str]:
    """ffmpeg: H.264 + AAC, height <= MAX_HEIGHT (rotation applied like every player does), every frame at its own
    time (passthrough = no fps conversion: no drops, no duplicates), the index at the front so the player can seek
    at once."""
    return [tool("ffmpeg"), "-hide_banner", "-nostdin", "-v", "error", "-nostats", "-progress", "pipe:1", "-y",
            "-i", str(src), "-map", "0:v:0", "-map", "0:a:0?",
            "-vf", f"scale=-2:'min({MAX_HEIGHT},ih)':flags=bicubic", "-fps_mode", "passthrough", "-enc_time_base", "demux",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-f", "mp4", str(dst)]


def make(src: Path, out=print) -> Path:
    """Make the player copy of src (or say it is there). Written to a .part file first: a half-made copy never plays."""
    src = Path(src)
    if not src.is_file():
        raise FileNotFoundError(src)
    dst = copy_path(src)
    if dst.is_file():
        out(f"the player copy is already there: {dst.name}")
        return dst
    PLAYER.mkdir(parents=True, exist_ok=True)
    c = codec(src)
    out((f"{src.name}: {str(c['codec']).upper()} does not play in every browser" if c.get("codec") else
         f"{src.name}: its video format could not be read") +
        " - making a small H.264 copy for the player (same frames, same timing; the analysis keeps the original)")
    part = dst.with_name(dst.stem + ".part.mp4")
    total = c.get("frames")
    proc = subprocess.Popen(command(src, part), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
    last = -1
    for line in proc.stdout:
        line = line.strip()
        if line.startswith("frame=") and total:
            pct = min(100, int(100 * int(line[6:] or 0) / total)) // 10 * 10
            if pct != last:
                last = pct
                out(f"copy: {pct} %")
        elif line and "=" not in line:
            out(line)                                              # an ffmpeg error
    rc = proc.wait()
    if rc != 0 or not part.is_file():
        part.unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg could not make the copy (exit code {rc})")
    os.replace(part, dst)
    (dst.with_suffix(".json")).write_text(json.dumps({"source": str(src), "size": src.stat().st_size,
                                                      "mtime_ns": src.stat().st_mtime_ns}, indent=1), encoding="utf-8")
    out(f"the player copy is ready: {dst.name} ({dst.stat().st_size / 1e6:.1f} MB)")
    return dst


if __name__ == "__main__":                      # tools\motionlab\app\jobtools.py player-copy is the job's entry
    sys.exit("run tools\\motionlab\\app\\jobtools.py player-copy <video>")
