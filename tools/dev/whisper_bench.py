"""Measure local Whisper (faster-whisper on the CPU) against a reference's subtitles, before 0.4 adopts it as the
fallback for videos without subtitles (docs\\plans.md 0.4, "light and tested first").

    <venv>\\Scripts\\python tools\\dev\\whisper_bench.py <name> [--models tiny,base,small] [--threads 4]

Needs `content.py transcript <name>` first (the subtitles are the yardstick: uploaded ones are a fair reference,
auto captions are the platform's own speech recognition) and faster-whisper, which is NOT a lab requirement -
install it in a separate venv so the lab stays as it is:
    py -3.12 -m venv .app\\bench-venv && .app\\bench-venv\\Scripts\\python -m pip install -r requirements.txt faster-whisper
Models download once from Hugging Face into .app\\models\\ (tiny ~75 MB, base ~145 MB, small ~480 MB). Each model
runs in its own process (clean memory peak), on --threads CPU threads (4 = roughly a laptop). Prints per model:
download size, load time, transcription time, x real time, peak memory, word error rate against the subtitles and
the median word-timing difference. Saves analysis\\<name>\\content\\whisper_bench.json. Reads the analysis's
audio.wav only.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
MODELS_DIR = LAB / ".app" / "models"


def peak_mb() -> float:
    """This process's peak working set (Windows), in MB."""
    class PMC(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong), ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t)]
    k32, psapi = ctypes.WinDLL("kernel32"), ctypes.WinDLL("psapi")
    k32.GetCurrentProcess.restype = ctypes.c_void_p                  # a 64-bit pseudo handle, not an int
    psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(PMC), ctypes.c_ulong]
    c = PMC()
    c.cb = ctypes.sizeof(PMC)
    psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb)
    return c.PeakWorkingSetSize / 2**20


def norm_words(text: str) -> list[str]:
    text = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", text.lower())        # [music], (laughs)
    return re.findall(r"[\w']+", text.replace("’", "'"))


def wer(ref: list[str], hyp: list[str]) -> tuple[float, list[tuple[int, int]]]:
    """Word error rate (substitutions + deletions + insertions) / reference words, and the matched index pairs."""
    n, m = len(ref), len(hyp)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (ref[i - 1] != hyp[j - 1]))
    pairs, i, j = [], n, m
    while i and j:
        if ref[i - 1] == hyp[j - 1] and d[i][j] == d[i - 1][j - 1]:
            pairs.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif d[i][j] == d[i - 1][j - 1] + 1:
            i, j = i - 1, j - 1
        elif d[i][j] == d[i - 1][j] + 1:
            i -= 1
        else:
            j -= 1
    return (d[n][m] / n if n else 0.0), pairs[::-1]


def load_audio(wav: Path):
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(wav), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def one(model: str, wav: Path, threads: int) -> dict:
    """Run in a child process: one model, its numbers and its words."""
    from faster_whisper import WhisperModel
    audio = load_audio(wav)
    t = time.perf_counter()
    m = WhisperModel(model, device="cpu", compute_type="int8", cpu_threads=threads, download_root=str(MODELS_DIR))
    load_s = time.perf_counter() - t
    t = time.perf_counter()
    segs, info = m.transcribe(audio, word_timestamps=True, vad_filter=True, beam_size=5)
    words = [{"t": round(w.start, 3), "w": w.word.strip()} for s in segs for w in (s.words or [])]
    run_s = time.perf_counter() - t
    size = sum(p.stat().st_size for p in MODELS_DIR.rglob("*") if p.is_file() and model in str(p).lower()) / 2**20
    return {"model": model, "load_s": round(load_s, 1), "run_s": round(run_s, 1), "audio_s": round(len(audio) / 16000, 1),
            "peak_mb": round(peak_mb()), "size_mb": round(size), "language": info.language,
            "lang_prob": round(info.language_probability, 2), "words": words}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("name")
    ap.add_argument("--models", default="tiny,base,small")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--one", help=argparse.SUPPRESS)
    args = ap.parse_args()
    d = LAB / "analysis" / args.name
    wav = d / "audio.wav"
    if args.one:
        print("RESULT " + json.dumps(one(args.one, wav, args.threads)), flush=True)
        return 0
    tj = d / "content" / "transcript.json"
    if not tj.exists() or not wav.exists():
        raise SystemExit(f"needs {wav} (analyze.py) and {tj} (content.py transcript {args.name})")
    T = json.loads(tj.read_text(encoding="utf-8"))
    ref_words = [w for r in T["lines"] for w in (r["words"] or [{"t": r["t0"], "w": x} for x in r["text"].split()])]
    ref = [(x, w["t"]) for w in ref_words for x in norm_words(w["w"])]
    print(f"{args.name}: yardstick = {'uploaded subtitles' if T['kind'] == 'manual' else 'auto captions'} "
          f"'{T['track']}' ({len(ref)} words); {args.threads} CPU threads; models {args.models}", flush=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for model in args.models.split(","):
        r = subprocess.run([sys.executable, __file__, args.name, "--one", model, "--threads", str(args.threads)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env={**os.environ, "HF_HUB_DISABLE_TELEMETRY": "1"})
        line = next((l for l in r.stdout.splitlines() if l.startswith("RESULT ")), None)
        if not line:
            print(f"{model}: failed\n{(r.stderr or r.stdout)[-1500:]}")
            continue
        res = json.loads(line[7:])
        hyp = [(x, w["t"]) for w in res.pop("words") for x in norm_words(w["w"])]
        e, pairs = wer([w for w, _ in ref], [w for w, _ in hyp])
        dt = [abs(hyp[j][1] - ref[i][1]) for i, j in pairs] if T.get("word_timings") else []
        res.update(hyp_words=len(hyp), wer=round(e, 3), timing_median_s=round(statistics.median(dt), 3) if dt else None,
                   x_realtime=round(res["audio_s"] / max(res["run_s"], 0.01), 1))
        rows.append(res)
        print(f"{model:>6}: {res['size_mb']:>4} MB model, load {res['load_s']:>5} s, transcribe {res['run_s']:>6} s "
              f"for {res['audio_s']} s of audio ({res['x_realtime']}x real time), peak {res['peak_mb']} MB, "
              f"WER {res['wer']:.0%} vs the subtitles"
              + (f", words {res['timing_median_s']} s apart (median)" if dt else "")
              + f", language {res['language']} ({res['lang_prob']})", flush=True)
    out = d / "content" / "whisper_bench.json"
    out.write_text(json.dumps({"name": args.name, "threads": args.threads, "yardstick": T["track"],
                               "yardstick_kind": T["kind"], "date": time.strftime("%Y-%m-%d %H:%M"), "rows": rows},
                              indent=1), encoding="utf-8")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
