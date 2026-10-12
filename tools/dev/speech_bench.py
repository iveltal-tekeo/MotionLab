"""Speech to text on a recording whose words are known (a read script): which engine should the lab use for the
words of your own videos (captions, 0.3.5 transcripts)? "Light and tested first": every engine is measured on this
PC at full speed and on 4 CPU threads (~ a laptop).

    .venv\\Scripts\\python tools\\dev\\speech_bench.py <video or audio> --script <script.txt> [--engines ...] [--threads 4]

Engines: fw-tiny / fw-base / fw-small = faster-whisper int8 on the CPU (in the scratch venv .app\\bench-venv:
`py -3.12 -m venv .app\\bench-venv && .app\\bench-venv\\Scripts\\python -m pip install numpy faster-whisper`; models in
.app\\models\\), parakeet = HyperFrames' `transcribe --engine parakeet` (`hyperframes models install parakeet`; its
whisper engine needs whisper.cpp built by hand on Windows, so it is left out). Each engine: model size, time, x real
time, peak memory (Python engines), word error rate against the script (numbers as words: "57" = "fifty seven"),
the words it got wrong, and how far its word times are from faster-whisper small's (median). Writes
<project>\\build\\speech\\bench.json and one transcript per engine (frame + timecode per word). Reads the video only.
"""
from __future__ import annotations

import argparse
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
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(LAB / "tools"))

from whisper_bench import wer  # noqa: E402

BENCH_PY = LAB / ".app" / "bench-venv" / "Scripts" / "python.exe"
HF = LAB / "tools" / "overlays" / "node_modules" / "hyperframes" / "bin" / "hyperframes.mjs"
ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
        "seventeen eighteen nineteen").split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def say(n: int) -> list[str]:
    if n < 20:
        return [ONES[n]]
    if n < 100:
        return [TENS[n // 10]] + ([ONES[n % 10]] if n % 10 else [])
    if n < 1000:
        return [ONES[n // 100], "hundred"] + (say(n % 100) if n % 100 else [])
    for div, word in ((10 ** 9, "billion"), (10 ** 6, "million"), (1000, "thousand")):
        if n >= div:
            return say(n // div) + [word] + (say(n % div) if n % div else [])
    return [str(n)]


def norm(text: str) -> list[str]:
    """Words to compare: lower case, no punctuation, numbers spelled out, a.m. = am, hyphens split."""
    t = text.lower().replace("’", "'").replace("%", " percent").replace("a.m.", "am").replace("p.m.", "pm")
    t = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", t)
    out = []
    for tok in re.findall(r"\d+(?:[.,]\d+)?|[a-z]+(?:'[a-z]+)?", t.replace("-", " ")):
        if tok[0].isdigit():
            whole, _, frac = tok.replace(",", "").partition(".")
            out += say(int(whole)) + (["point"] + [ONES[int(c)] for c in frac] if frac else [])
        else:
            out.append(tok)
    return out


def fw_one(model: str, wav: str, threads: int) -> dict:
    """In the bench venv: one faster-whisper model, its numbers and its words."""
    import ctypes
    import numpy as np
    from faster_whisper import WhisperModel

    class PMC(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong)] + [
            (n, ctypes.c_size_t) for n in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                                           "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
                                           "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", wav, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    audio = np.frombuffer(raw, dtype=np.float32)
    t = time.perf_counter()
    m = WhisperModel(model, device="cpu", compute_type="int8", cpu_threads=threads,
                     download_root=str(LAB / ".app" / "models"))
    load_s = time.perf_counter() - t
    t = time.perf_counter()
    segs, info = m.transcribe(audio, word_timestamps=True, vad_filter=True, beam_size=5, language="en")
    words = [{"t": round(w.start, 3), "t1": round(w.end, 3), "w": w.word.strip()} for s in segs for w in (s.words or [])]
    run_s = time.perf_counter() - t
    k32, psapi = ctypes.WinDLL("kernel32"), ctypes.WinDLL("psapi")
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(PMC), ctypes.c_ulong]
    c = PMC()
    c.cb = ctypes.sizeof(PMC)
    psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb)
    size = sum(p.stat().st_size for p in (LAB / ".app" / "models").rglob("*")
               if p.is_file() and f"faster-whisper-{model}" in str(p)) / 2 ** 20
    return {"load_s": round(load_s, 1), "run_s": round(run_s, 1), "audio_s": round(len(audio) / 16000, 1),
            "peak_mb": round(c.PeakWorkingSetSize / 2 ** 20), "size_mb": round(size), "words": words}


def run_fw(model: str, wav: Path, threads: int) -> dict:
    r = subprocess.run([str(BENCH_PY), __file__, str(wav), "--script", "-", "--fw-one", model, "--threads",
                        str(threads)], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, "HF_HUB_DISABLE_TELEMETRY": "1"})
    line = next((ln for ln in r.stdout.splitlines() if ln.startswith("RESULT ")), None)
    if not line:
        raise RuntimeError((r.stderr or r.stdout)[-1200:])
    return json.loads(line[7:])


def run_parakeet(wav: Path, work: Path) -> dict:
    work.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "HYPERFRAMES_NO_TELEMETRY": "1", "DO_NOT_TRACK": "1", "HYPERFRAMES_SKIP_SKILLS": "1"}
    t = time.perf_counter()
    r = subprocess.run(["node", str(HF), "transcribe", str(wav), "--engine", "parakeet", "-d", str(work), "--json"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
                       cwd=str(HF.parents[3]))
    run_s = time.perf_counter() - t
    res = json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else {}
    tj = next((Path(res[k]) for k in ("transcriptPath", "transcript", "path", "output") if isinstance(res.get(k), str)
               and Path(res[k]).exists()), None) or next(iter(sorted(work.rglob("*.json"))), None)
    if not tj:
        raise RuntimeError(f"no transcript: {r.stdout[-600:]} {r.stderr[-600:]}")
    data = json.loads(tj.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("words") or data.get("segments") or []
    words = []
    for it in items:
        txt = it.get("text") or it.get("word") or ""
        start = it.get("start", it.get("t"))
        end = it.get("end", start)
        if txt.strip():
            words.append({"t": round(float(start), 3), "t1": round(float(end), 3), "w": txt.strip()})
    import wave
    with wave.open(str(wav)) as w:
        audio_s = w.getnframes() / w.getframerate()
    return {"load_s": None, "run_s": round(run_s, 1), "audio_s": round(audio_s, 1), "peak_mb": None, "size_mb": None,
            "words": words, "raw": str(tj)}


def tc(t: float, fps: float) -> str:
    f = int(round(t * fps))
    nom = round(fps)
    s = f // nom
    return f"f{f} ({s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}:{f % nom:02d})"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("media")
    ap.add_argument("--script", required=True)
    ap.add_argument("--engines", default="fw-tiny,fw-base,fw-small,parakeet")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--fps", type=float, default=30.0, help="for frame + timecode in the transcripts")
    ap.add_argument("--fw-one", help=argparse.SUPPRESS)
    a = ap.parse_args()
    if a.fw_one:
        print("RESULT " + json.dumps(fw_one(a.fw_one, a.media, a.threads)), flush=True)
        return 0
    media = Path(a.media).resolve()
    out = media.parent / "build" / "speech" if media.parent.parent.name == "projects" else LAB / ".app" / "dev" / "speech"
    out.mkdir(parents=True, exist_ok=True)
    wav = out / "audio_16k.wav"
    if not wav.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(media), "-vn", "-ac", "1", "-ar", "16000", "-c:a",
                        "pcm_s16le", str(wav)], check=True)
    ref = norm(Path(a.script).read_text(encoding="utf-8"))
    print(f"{media.name}: {len(ref)} script words; {a.threads} CPU threads for faster-whisper", flush=True)
    rows = {}
    for eng in a.engines.split(","):
        try:
            res = run_fw(eng[3:], wav, a.threads) if eng.startswith("fw-") else run_parakeet(wav, out / "parakeet")
        except Exception as e:                                      # noqa: BLE001 - report and go on
            print(f"{eng}: failed - {str(e)[-400:]}", flush=True)
            continue
        hyp_tok = [(x, w["t"]) for w in res["words"] for x in norm(w["w"])]
        e, pairs = wer(ref, [x for x, _ in hyp_tok])
        matched_ref = {i for i, _ in pairs}
        missed = [ref[i] for i in range(len(ref)) if i not in matched_ref]
        res.update(engine=eng, wer=round(e, 3), words_out=len(hyp_tok), missed=missed[:30],
                   x_realtime=round(res["audio_s"] / max(res["run_s"], 0.01), 1), pairs=pairs, tok=hyp_tok)
        rows[eng] = res
        print(f"{eng:>9}: {res['size_mb'] if res['size_mb'] is not None else '?':>4} MB, load {res['load_s']} s, "
              f"run {res['run_s']} s for {res['audio_s']} s ({res['x_realtime']}x real time), peak "
              f"{res['peak_mb'] if res['peak_mb'] is not None else '?'} MB, WER {e:.1%} ({len(missed)} script words "
              f"missed or wrong: {' '.join(missed[:12])}{' …' if len(missed) > 12 else ''})", flush=True)
        (out / f"transcript_{eng}.txt").write_text("\n".join(f"{tc(w['t'], a.fps)}  {w['w']}" for w in res["words"]),
                                                    encoding="utf-8")
    base = rows.get("fw-small") or next(iter(rows.values()), None)
    if base:                                                        # timing agreement with fw-small, per script word
        bmap = {i: base["tok"][j][1] for i, j in base["pairs"]}
        for eng, res in rows.items():
            d = [abs(res["tok"][j][1] - bmap[i]) for i, j in res["pairs"] if i in bmap]
            res["timing_vs_small_median_s"] = round(statistics.median(d), 3) if d and res is not base else None
            if res["timing_vs_small_median_s"] is not None:
                print(f"{eng:>9}: word starts {res['timing_vs_small_median_s']} s from fw-small's (median, "
                      f"{len(d)} words)", flush=True)
    for res in rows.values():
        res.pop("pairs", None)
        res.pop("tok", None)
    (out / "bench.json").write_text(json.dumps({"media": str(media), "script": str(Path(a.script).resolve()),
                                                "threads": a.threads, "date": time.strftime("%Y-%m-%d %H:%M"),
                                                "rows": rows}, indent=1), encoding="utf-8")
    print(f"-> {out / 'bench.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
