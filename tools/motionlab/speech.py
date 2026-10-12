"""Speech to text for the user's own videos (captions, transcripts): faster-whisper on the CPU, picked by the user on
2026-10-12 after measuring on their own recording (docs\\plans.md 0.3.5: small = 21 % off the read script with the
video's names as a prompt, base 28 %, Parakeet 26 % without names). Optional: `tools\\speech.py install` (Settings >
Programs > Speech to text) puts the pinned package into the lab's venv; models download once into .app\\models\\.
This module imports faster-whisper only when it transcribes - the app (standard library only) just asks
`available()`.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path

from .util import LAB, tool

PIN = "faster-whisper==1.2.1"
MODELS = {"small": "464 MB, the most accurate (with names)", "base": "141 MB, light - for slow laptops"}
MODELS_DIR = LAB / ".app" / "models"
RATES = (23.976, 24.0, 25.0, 29.97, 30.0, 48.0, 50.0, 59.94, 60.0)


def available() -> bool:
    return importlib.util.find_spec("faster_whisper") is not None


def version() -> str | None:
    try:
        from importlib.metadata import version as v
        return v("faster-whisper")
    except Exception:                                   # noqa: BLE001 - not installed
        return None


def model_ready(model: str) -> bool:
    d = MODELS_DIR / f"models--Systran--faster-whisper-{model}" / "snapshots"
    return d.is_dir() and any(d.rglob("model.bin"))


def probe(media: str | Path) -> dict:
    """Size, a nominal frame rate (phones record a variable one: snapped to the nearest usual rate) and duration."""
    r = subprocess.run([tool("ffprobe"), "-v", "error", "-show_entries",
                        "stream=codec_type,width,height,avg_frame_rate:stream_side_data=rotation:stream_tags=rotate:"
                        "format=duration", "-of", "json", str(media)], capture_output=True, text=True)
    d = json.loads(r.stdout or "{}")
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    rot = next((sd.get("rotation") for sd in v.get("side_data_list", []) if "rotation" in sd), None)
    rot = rot if rot is not None else (v.get("tags") or {}).get("rotate", 0)
    if int(float(rot or 0)) % 180:                      # a phone video filmed upright: stored lying, shown upright
        v["width"], v["height"] = v.get("height"), v.get("width")
    num, _, den = str(v.get("avg_frame_rate") or "0/1").partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 0.0
    fps = min(RATES, key=lambda r_: abs(r_ - fps)) if fps else 30.0
    dur = float((d.get("format") or {}).get("duration") or 0)
    return {"width": v.get("width"), "height": v.get("height"), "fps": fps, "duration_s": dur,
            "frames": int(round(dur * fps)), "has_video": bool(v)}


def transcribe(media: str | Path, model: str = "small", names: str = "", language: str | None = None,
               threads: int = 0, log=print) -> dict:
    """The words of a video or audio file: {lines: [{t0, t1, text, words: [{t, t1, w}]}], language, ...} - the same
    lines / words shape as tools\\content.py's transcript.json, so captions and the Content tab read both."""
    import numpy as np                                   # noqa: PLC0415 - heavy, only here
    from faster_whisper import WhisperModel             # noqa: PLC0415

    raw = subprocess.run([tool("ffmpeg"), "-v", "error", "-nostdin", "-i", str(media), "-vn", "-ac", "1", "-ar",
                          "16000", "-f", "f32le", "-"], capture_output=True, check=True).stdout
    audio = np.frombuffer(raw, dtype=np.float32)
    threads = threads or max(1, min(8, (os.cpu_count() or 4)))
    if not model_ready(model):
        log(f"downloading the speech model '{model}' once ({MODELS.get(model, '?')}) into .app\\models ...")
    m = WhisperModel(model, device="cpu", compute_type="int8", cpu_threads=threads, download_root=str(MODELS_DIR))
    # the names prompt helps small (MotionLab, 4AM, Nemzzz right); base with a prompt skipped a whole paragraph
    prompt = names.strip() if names.strip() and model != "base" else None
    segs, info = m.transcribe(audio, word_timestamps=True, vad_filter=True, beam_size=5, language=language or None,
                              initial_prompt=prompt)
    lines = []
    for s in segs:
        words = []
        for w in s.words or []:
            txt = w.word.strip()
            if not txt:
                continue
            if words and txt[0] in ".,%" and words[-1]["w"][-1:].isdigit() and len(txt) > 1:
                words[-1]["w"] += txt                    # "3" ".4" -> "3.4" (Whisper splits numbers)
                words[-1]["t1"] = round(w.end, 3)
                continue
            words.append({"t": round(w.start, 3), "t1": round(w.end, 3), "w": txt})
        if words:
            lines.append({"t0": words[0]["t"], "t1": words[-1]["t1"], "text": " ".join(w["w"] for w in words),
                          "words": words})
    return {"schema": 1, "source": "speech", "kind": f"faster-whisper {model}", "engine": PIN, "model": model,
            "lang": info.language, "lang_prob": round(info.language_probability, 2), "names": names.strip(),
            "word_timings": True, "audio_s": round(len(audio) / 16000, 2), "lines": lines,
            "words": sum(len(ln["words"]) for ln in lines)}
