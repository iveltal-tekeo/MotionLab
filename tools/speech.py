"""Speech to text for your own videos: the words with frame + timecode, for captions (overlay.py captions --from a
video) and transcripts. faster-whisper on the CPU (motionlab\\speech.py; chosen 2026-10-12 after measuring on the
user's recording - docs\\plans.md 0.3.5). Optional: install it once (Settings > Programs > Speech to text, or below).

    .venv\\Scripts\\python tools\\speech.py install [--model small|base]   the pinned faster-whisper + the model
    .venv\\Scripts\\python tools\\speech.py status
    .venv\\Scripts\\python tools\\speech.py transcribe <video> [--model small] [--names "MotionLab, 4AM"] [--lang en]
          -> projects\\<project>\\build\\speech\\<video>.<model>.json (a video elsewhere: .app\\speech\\), the lines
          printed with frame + timecode. --names = words the video uses that a model cannot guess (names, brands):
          small gets them right then. Done before with the same settings: reused (--force does it again).
Reads the video only (never changes it).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import speech as SP  # noqa: E402
from motionlab.timecode import frame_to_tc  # noqa: E402
from motionlab.util import LAB, log, setup_console  # noqa: E402


def out_path(media: Path, model: str) -> Path:
    m = media.resolve()
    projects = (LAB / "projects").resolve()
    if projects in m.parents:
        p = projects / m.relative_to(projects).parts[0]
        return p / "build" / "speech" / f"{m.stem}.{model}.json"
    return LAB / ".app" / "speech" / f"{m.stem}.{model}.json"


def transcript(media: Path, model: str = "small", names: str = "", lang: str | None = None,
               force: bool = False) -> tuple[Path, dict]:
    """The cached transcript of a video (made when missing or when its settings / the video changed)."""
    if not SP.available():
        raise SystemExit("speech to text is not installed: Settings > Programs > Speech to text > Install "
                         "(or tools\\speech.py install)")
    st = media.stat()
    fp = {"size": st.st_size, "mtime_ns": st.st_mtime_ns, "model": model, "names": names.strip(), "lang": lang or ""}
    out = out_path(media, model)
    if out.exists() and not force:
        old = json.loads(out.read_text(encoding="utf-8"))
        if old.get("fingerprint") == fp:
            return out, old
    info = SP.probe(media)
    fps = info["fps"]
    log(f"{media.name}: listening ({model}, {info['duration_s']:.0f} s"
        + (f", names: {names.strip()}" if names.strip() else "") + ") ...")
    t0 = time.time()
    d = SP.transcribe(media, model, names, lang, log=log)
    for ln in d["lines"]:
        ln["start"], ln["end"] = int(round(ln["t0"] * fps)), max(int(round(ln["t1"] * fps)) - 1, int(round(ln["t0"] * fps)))
        ln["start_tc"], ln["end_tc"] = frame_to_tc(ln["start"], fps), frame_to_tc(ln["end"], fps)
        for w in ln["words"]:
            w["f"] = int(round(w["t"] * fps))
    d.update(name=media.stem, video=str(media.resolve()), fps=fps, frames=info["frames"], fingerprint=fp,
             made=time.strftime("%Y-%m-%d %H:%M"), seconds=round(time.time() - t0, 1))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
    log(f"{d['words']} words in {len(d['lines'])} lines, language {d['lang']} ({d['lang_prob']}), "
        f"{d['seconds']} s -> {out}")
    return out, d


def cmd_install(a) -> int:
    if not SP.available():
        log(f"installing {SP.PIN} into the lab's Python (about 60 MB) ...")
        r = subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", SP.PIN])
        if r.returncode:
            raise SystemExit("pip could not install it - see the lines above")
    log(f"faster-whisper {SP.version() or '?'} is installed")
    if SP.model_ready(a.model):
        log(f"the model '{a.model}' is there already")
        return 0
    log(f"downloading the model '{a.model}' ({SP.MODELS.get(a.model, '?')}) once into .app\\models ...")
    r = subprocess.run([sys.executable, "-c", "from faster_whisper import WhisperModel; "
                        f"WhisperModel({a.model!r}, device='cpu', compute_type='int8', "
                        f"download_root={str(SP.MODELS_DIR)!r})"])
    if r.returncode or not SP.model_ready(a.model):
        raise SystemExit("the model did not download - check the internet connection and try again")
    log(f"ready: speech to text with '{a.model}'")
    return 0


def cmd_status(a) -> int:
    print(f"faster-whisper: {SP.version() or 'not installed'}")
    for m, what in SP.MODELS.items():
        print(f"  model {m:6s} {'downloaded' if SP.model_ready(m) else 'not downloaded'} ({what})")
    return 0


def cmd_transcribe(a) -> int:
    media = Path(a.media)
    if not media.is_file():
        raise SystemExit(f"no such file: {media}")
    out, d = transcript(media, a.model, a.names or "", a.lang, a.force)
    for ln in d["lines"][: a.show]:
        print(f"  f{ln['start']} ({ln['start_tc']})  {ln['text']}")
    if len(d["lines"]) > a.show:
        print(f"  ... {len(d['lines']) - a.show} more lines")
    print(out)
    return 0


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("install")
    s.add_argument("--model", default="small", choices=sorted(SP.MODELS))
    sub.add_parser("status")
    s = sub.add_parser("transcribe")
    s.add_argument("media")
    s.add_argument("--model", default="small", choices=sorted(SP.MODELS))
    s.add_argument("--names", help="names / words the video uses, comma separated")
    s.add_argument("--lang", help="language code (default: detected)")
    s.add_argument("--force", action="store_true")
    s.add_argument("--show", type=int, default=12, help="lines to print")
    a = ap.parse_args()
    return {"install": cmd_install, "status": cmd_status, "transcribe": cmd_transcribe}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
