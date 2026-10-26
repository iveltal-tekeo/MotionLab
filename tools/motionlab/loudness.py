"""The finished sound (0.6.0 step 22, docs\\plans.md): every render's sound brought to one loudness - EBU R128
integrated loudness (LUFS) - with its true peak measured AFTER the AAC encode, the way a platform hears it. Before
this the lab had no loudness step: a talking video's voice was levelled to -26 dBFS RMS (about -23 LUFS) and a
song went out as loud as its master.

    master(video, audio, a0_s, frames, fps)   the render's sound made again from the plan's audio (never the MP4's
          AAC - one encode): gain to the target, a limiter at 4x the sample rate (it catches the peaks between
          samples that the AAC encode brings out), AAC, then the true peak measured on the MP4; over the ceiling =
          the limiter lowered and done again, off the target by more than the tolerance = the gain moved (config
          "master": rounds). The gain comes from the WHOLE sound (frames 0..N), so a part rendered with --range
          sounds as it will in the full render.
    measure(path)   {"lufs", "true_peak_db", "lra"} of a file's first sound stream (ffmpeg's ebur128 filter).

Numbers in tools\\config.json "master" (target_lufs, true_peak_db, aac_kbps, rounds, tolerance_lu, on); a PC's own
target goes into config.local.json. Writes only the render it is given (in its build folder) and a temp file
beside it; the plan's audio is only read.
"""
from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path

from .util import load_config, tool

DEFAULTS = {"on": True, "target_lufs": -14.0, "true_peak_db": -1.0, "aac_kbps": 256, "rounds": 4,
            "tolerance_lu": 0.5}
SILENT_LUFS = -60.0                  # quieter than this = no sound to master (ebur128 says -70 for silence)
OVERSAMPLE = 192000                  # the limiter's rate: 4x 48 kHz


def settings() -> dict:
    try:
        return {**DEFAULTS, **(load_config().get("master") or {})}
    except (OSError, ValueError):
        return dict(DEFAULTS)


_NUM = r"(-?(?:\d+(?:\.\d+)?|inf))"


def _ebur128(cmd_in: list[str]) -> dict:
    """ffmpeg <cmd_in> -af ebur128=peak=true -> the summary's numbers (None where ffmpeg printed none)."""
    r = subprocess.run([tool("ffmpeg"), "-hide_banner", "-nostats", "-nostdin", *cmd_in, "-map", "0:a:0", "-af",
                        "ebur128=peak=true:framelog=quiet", "-f", "null", "-"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    tail = r.stderr[r.stderr.rfind("Summary:"):] if "Summary:" in r.stderr else ""
    if not tail:
        return {"lufs": None, "true_peak_db": None, "lra": None,
                "error": (r.stderr.strip().splitlines() or ["no sound"])[-1][:200]}

    def num(label: str, block: str = ""):
        part = tail[tail.find(block):] if block and block in tail else tail
        m = re.search(label + r"\s*" + _NUM, part)
        if not m:
            return None
        v = float(m.group(1).replace("inf", "1e9"))
        return None if abs(v) >= 1e8 else round(v, 2)
    return {"lufs": num(r"I:"), "true_peak_db": num(r"Peak:", "True peak"), "lra": num(r"LRA:")}


def measure(path: Path, start_s: float = 0.0, dur_s: float | None = None) -> dict:
    """A file's loudness: integrated LUFS, true peak (dBTP, 4x oversampled) and loudness range (LU)."""
    cmd = (["-ss", f"{start_s:.6f}"] if start_s > 0 else []) + (["-t", f"{dur_s:.6f}"] if dur_s else []) \
        + ["-i", str(path)]
    return _ebur128(cmd)


def _chain(gain_db: float, ceiling_db: float) -> str:
    lim = max(0.0625, min(1.0, 10 ** (ceiling_db / 20)))
    return (f"volume={gain_db:.2f}dB,aresample={OVERSAMPLE},"
            f"alimiter=limit={lim:.5f}:attack=1:release=60:level=false,aresample=48000")


def master(video: Path, audio: dict, a0_s: float, frames: int, fps: float, log=print, part: bool = False) -> dict:
    """The render `video` (its sound from `audio` = the plan's {"path", "trim_to_video"} at a0_s seconds) mastered in
    place; `frames` = the whole plan's length (the gain comes from all of it), part = the render is a --range part.
    Returns what was done: {"done", "whole" (the whole sound's numbers), "lufs" / "true_peak_db" (this render's),
    "gain_db", "rounds", "target_lufs", "ok", ...}."""
    cfg = settings()
    out = {"target_lufs": cfg["target_lufs"], "ceiling_db": cfg["true_peak_db"], "done": False}
    if not cfg.get("on", True):
        return {**out, "why": "off in config (master.on)"}
    src = Path(str((audio or {}).get("path") or ""))
    if not src.is_file():
        return {**out, "why": "no sound"}
    t0 = time.time()
    total = measure(src, 0.0, frames / fps)                       # the whole program decides the gain
    if total["lufs"] is None or total["lufs"] < SILENT_LUFS:
        return {**out, "why": f"no sound to master ({total.get('lufs')} LUFS)", "before": total}
    gain, ceil = cfg["target_lufs"] - total["lufs"], cfg["true_peak_db"] - 0.3
    video = Path(video)
    tmp_a = video.with_name(video.stem + "_master_tmp.m4a")
    tmp = video.with_name(video.stem + "_master_tmp" + video.suffix)
    aac = ["-c:a", "aac", "-b:a", f"{int(cfg['aac_kbps'])}k", "-ar", "48000"]

    def ff(cmd: list, dst: Path) -> str | None:
        r = subprocess.run([tool("ffmpeg"), "-v", "error", "-y", "-nostdin", *cmd, str(dst)], capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        return None if r.returncode == 0 else r.stderr.strip()[-300:]
    # 1. the gain and the ceiling settled on the WHOLE sound (frames 0..N), alone: a part sounds as the full render
    whole, n = {}, 0
    for n in range(1, int(cfg["rounds"]) + 1):
        err = ff(["-t", f"{frames / fps:.6f}", "-i", str(src), "-map", "0:a:0", "-af", _chain(gain, ceil), *aac], tmp_a)
        if err:
            tmp_a.unlink(missing_ok=True)
            return {**out, "why": f"ffmpeg failed: {err}", "before": total}
        whole = measure(tmp_a)
        if whole["lufs"] is None or whole["true_peak_db"] is None:
            break
        over = whole["true_peak_db"] - cfg["true_peak_db"]
        off = cfg["target_lufs"] - whole["lufs"]
        if over <= 0 and abs(off) <= cfg["tolerance_lu"]:
            break
        if over > 0:
            ceil -= over + 0.1                                    # the AAC raised the peaks: a lower ceiling
        if abs(off) > cfg["tolerance_lu"]:
            gain += off                                           # the limiter took loudness away (or AAC moved it)
    tmp_a.unlink(missing_ok=True)
    # 2. into the render (its own range of the sound); its true peak measured again - over = the ceiling lowered
    trim = (audio or {}).get("trim_to_video", True)
    got = {}
    for _ in range(3):
        err = ff(["-i", str(video), *(["-ss", f"{a0_s:.6f}"] if a0_s > 0 else []), "-i", str(src), "-map", "0:v",
                  "-map", "1:a:0", "-c:v", "copy", "-af", _chain(gain, ceil), *aac, *(["-shortest"] if trim else []),
                  "-movflags", "+faststart"], tmp)
        if err:
            tmp.unlink(missing_ok=True)
            return {**out, "why": f"ffmpeg failed: {err}", "before": total}
        got = measure(tmp)
        over = (got.get("true_peak_db") or -99.0) - cfg["true_peak_db"]
        if over <= 0:
            break
        ceil -= over + 0.1
    os.replace(tmp, video)
    res = {**out, "done": True, "before": total, "whole": whole, "lufs": got.get("lufs"),
           "true_peak_db": got.get("true_peak_db"), "lra": got.get("lra"), "gain_db": round(gain, 2),
           "limiter_ceiling_db": round(ceil, 2), "rounds": n, "seconds": round(time.time() - t0, 1)}
    ok = (got.get("true_peak_db") is not None and got["true_peak_db"] <= cfg["true_peak_db"] + 0.05
          and whole.get("lufs") is not None and abs(whole["lufs"] - cfg["target_lufs"]) <= cfg["tolerance_lu"] + 0.05)
    res["ok"] = ok
    log(f"sound mastered: {total['lufs']:.1f} -> {whole.get('lufs')} LUFS over the whole sound (target "
        f"{cfg['target_lufs']:g})" + (f", {got.get('lufs')} LUFS in this part" if part else "")
        + f", true peak {got.get('true_peak_db')} dBTP after AAC (ceiling {cfg['true_peak_db']:g}), gain {gain:+.1f} "
        f"dB, {n} round(s), {res['seconds']:.1f} s" + ("" if ok else " - NOT within the target: look at it"))
    return res


# 0.6.0 step 23 (docs\\plans.md; measure first - an A/B on the user's recording decides if it is on by default): a
# talking take's voice cleaned with ffmpeg only, before the cuts - brought to VOICE_IN_LUFS first so the compressors'
# thresholds mean the same on every take, then a 70 Hz high pass, a light noise reduction, a speaker's EQ (+1.5 dB
# 120 Hz body, -3 dB 250 Hz mud, -1.5 dB 600 Hz box, +3.5 dB 3.5 kHz presence, +3 dB shelf from 9 kHz air), a
# de-esser and two compressors (slow: levels the sentences; fast: density). Filters only - no sample moves, so the
# voice stays on the lips. The master (above) sets the final loudness.
VOICE_IN_LUFS = -23.0
AFFTDN_DELAY = 1200                  # ffmpeg's afftdn delays the sound by 1200 samples at 48 kHz (25 ms, measured
                                     # 2026-10-26) and keeps its length: padded and trimmed back, so nothing moves
VOICE_CHAIN = (f"aresample=48000,highpass=f=70,apad=pad_len={AFFTDN_DELAY},afftdn=nf=-50:nr=10:tn=1,"
               f"atrim=start_sample={AFFTDN_DELAY},asetpts=PTS-STARTPTS,"
               "equalizer=f=120:t=q:w=0.9:g=1.5,equalizer=f=250:t=q:w=1.1:g=-3,equalizer=f=600:t=q:w=1.4:g=-1.5,"
               "equalizer=f=3500:t=q:w=1.0:g=3.5,highshelf=f=9000:g=3,deesser=i=0.45:m=0.5:f=0.5,"
               "acompressor=threshold=-26dB:ratio=2.5:attack=25:release=250:makeup=2dB,"
               "acompressor=threshold=-18dB:ratio=4:attack=3:release=60:makeup=3dB")


def clean_voice(src: Path, dst: Path, start_s: float = 0.0, dur_s: float | None = None) -> dict:
    """A take's sound (any audio / video file) -> dst (WAV, 48 kHz stereo, the same length and timing) through
    VOICE_CHAIN. Returns {"before": LUFS, "gain_db"} or {"error"}."""
    m = measure(Path(src), start_s, dur_s)
    if m.get("lufs") is None or m["lufs"] < SILENT_LUFS:
        return {"error": f"no voice to clean ({m.get('lufs')} LUFS)"}
    g = VOICE_IN_LUFS - m["lufs"]
    r = subprocess.run([tool("ffmpeg"), "-v", "error", "-y", "-nostdin",
                        *(["-ss", f"{start_s:.6f}"] if start_s > 0 else []), *(["-t", f"{dur_s:.6f}"] if dur_s else []),
                        "-i", str(src), "-map", "0:a:0", "-af", f"volume={g:.2f}dB,{VOICE_CHAIN}", "-ar", "48000",
                        "-ac", "2", "-c:a", "pcm_s24le", str(dst)], capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return {"before": m["lufs"], "gain_db": round(g, 2)} if r.returncode == 0 else {"error": r.stderr.strip()[-300:]}


def selfcheck(verbose: bool = True) -> dict:
    """Known answers, no project: a stereo 1 kHz tone at -20 dBFS measured (-20 LUFS, EBU Tech 3341's test signal),
    then a quiet talking-like sound with loud clicks mastered into a still video: within the tolerance of the target,
    its true peak at or under the ceiling after AAC, a --range part given the whole's gain."""
    import tempfile

    import numpy as np
    import soundfile as sf
    t0 = time.time()
    lines, ok = [], True

    def check(cond, msg):
        nonlocal ok
        ok &= bool(cond)
        lines.append(("PASS " if cond else "FAIL ") + msg)
    cfg = settings()
    with tempfile.TemporaryDirectory(prefix="ml_loud_") as td:
        d = Path(td)
        sr, n = 48000, 48000 * 6
        t = np.arange(n) / sr
        tone = 10 ** (-20 / 20) * np.sin(2 * np.pi * 1000 * t)
        sf.write(str(d / "tone.wav"), np.stack([tone, tone], 1), sr, subtype="PCM_24")
        m = measure(d / "tone.wav")
        check(m["lufs"] is not None and abs(m["lufs"] - (-20.0)) <= 0.3 and m["true_peak_db"] is not None
              and abs(m["true_peak_db"] - (-20.0)) <= 0.3,
              f"measure: a 1 kHz sine at -20 dBFS in both channels = {m['lufs']} LUFS (EBU Tech 3341: -20.0), true "
              f"peak {m['true_peak_db']} dBTP")
        rng = np.random.default_rng(3)
        talk = rng.standard_normal(n) * 10 ** (-32 / 20) * (0.6 + 0.4 * np.sin(2 * np.pi * 4 * t)) * ((t % 1.5) < 1.0)
        for c in range(sr // 2, n, sr):                           # a sharp click every second: peaks to limit
            talk[c:c + 200] += 0.5 * np.exp(-np.arange(200) / 30) * np.sin(np.arange(200) * 1.9)
        sf.write(str(d / "talk.wav"), np.stack([talk, talk], 1), sr, subtype="PCM_24")
        fps, frames = 30.0, 180
        vid = d / "v.mp4"
        r = subprocess.run([tool("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=gray:s=320x180:r=30",
                            "-frames:v", str(frames), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(vid)],
                           capture_output=True)
        check(r.returncode == 0, "a still test video")
        before = measure(d / "talk.wav")
        res = master(vid, {"path": str(d / "talk.wav")}, 0.0, frames, fps, log=lambda *_: None)
        check(res.get("done") and res.get("ok"),
              f"master: {before['lufs']} LUFS -> {res.get('lufs')} LUFS (target {cfg['target_lufs']:g} "
              f"+-{cfg['tolerance_lu']:g}), true peak {res.get('true_peak_db')} dBTP after AAC (ceiling "
              f"{cfg['true_peak_db']:g}), gain {res.get('gain_db')} dB in {res.get('rounds')} round(s)")
        part = d / "part.mp4"
        subprocess.run([tool("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=gray:s=320x180:r=30",
                        "-frames:v", "60", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(part)], capture_output=True)
        rp = master(part, {"path": str(d / "talk.wav")}, 2.0, frames, fps, log=lambda *_: None, part=True)
        check(rp.get("done") and abs((rp.get("gain_db") or 0) - (res.get("gain_db") or 0)) <= 0.01,
              f"a part (f60-f119) gets the whole's gain: {rp.get('gain_db')} dB vs {res.get('gain_db')} dB")
        silent = d / "silent.wav"
        sf.write(str(silent), np.zeros((sr * 2, 2)), sr, subtype="PCM_16")
        rs = master(vid, {"path": str(silent)}, 0.0, 60, fps, log=lambda *_: None)
        check(not rs.get("done"), f"silence is left alone ({rs.get('why')})")
        from scipy.signal import correlate
        rc = clean_voice(d / "talk.wav", d / "clean.wav")
        y, _ = sf.read(str(d / "clean.wav"), always_2d=True)
        k = 2400                                             # +-50 ms of lags
        lag = int(np.argmax(correlate(y.mean(1)[k:-k], talk[:len(y)], mode="valid"))) - k
        check("error" not in rc and abs(len(y) - n) <= 1 and lag == 0,
              f"the voice cleaned (noise, EQ, de-esser, compressors): {len(y)} samples for {n}, moved {lag} samples "
              f"(afftdn's own 25 ms delay taken back) - stays on the lips ({rc})")
    secs = time.time() - t0
    lines.append(f"{'PASS' if ok else 'FAIL'}: loudness, {secs:.1f} s")
    if verbose:
        print("\n".join(lines))
    return {"ok": ok, "passed": ok, "lines": lines, "seconds": round(secs, 2)}
