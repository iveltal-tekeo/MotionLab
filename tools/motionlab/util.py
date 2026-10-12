"""Shared helpers: lab paths, config, subprocess, logging, source-file protection."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path, PureWindowsPath

LAB = Path(__file__).resolve().parents[2]          # C:\MotionLab
TOOLS = LAB / "tools"
ANALYSIS = LAB / "analysis"
REFS = LAB / "refs"
CONFIG_PATH = TOOLS / "config.json"

_T0 = time.time()


def setup_console() -> None:
    """Make printing of non-ASCII file names safe on Windows consoles."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def log(msg: str) -> None:
    print(f"[{time.time() - _T0:7.1f}s] {msg}", flush=True)


def load_config(path: Path | None = None) -> dict:
    with open(path or CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return _strip_comments(cfg)


def _strip_comments(obj):
    if isinstance(obj, dict):
        return {k: _strip_comments(v) for k, v in obj.items() if not k.startswith("_")}
    if isinstance(obj, list):
        return [_strip_comments(v) for v in obj]
    return obj


def read_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj, indent: int = 2) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=indent, ensure_ascii=False, default=_json_default)
    os.replace(tmp, path)


def _json_default(o):
    try:
        import numpy as np
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return None if not np.isfinite(o) else float(o)
        if isinstance(o, np.bool_):
            return bool(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
    except ImportError:
        pass
    if isinstance(o, Path):
        return str(o)
    raise TypeError(f"not JSON serializable: {type(o)}")


def tool(name: str) -> str:
    exe = shutil.which(name)
    if not exe:
        raise SystemExit(f"'{name}' not found on PATH. Install it with: winget install Gyan.FFmpeg")
    return exe


def run(cmd: list, check: bool = True) -> subprocess.CompletedProcess:
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(f"command failed ({r.returncode}): {' '.join(map(str, cmd))}\n{r.stderr[-2000:]}")
    return r


def safe_name(stem: str) -> str:
    """An analysis folder name from a video's file name: letters, digits, _ - . only (no spaces, no emoji). Never
    ".." - yt-dlp keeps "..." where it shortens a title, and the app refuses any name with ".." (its path guard) - and
    no dot at the end (Windows drops it)."""
    s = re.sub(r"[^\w\-. ]+", "_", stem, flags=re.UNICODE).strip(" .")
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"\.{2,}", "_", s)
    s = re.sub(r"_{2,}", "_", s).strip("_")
    return s[:80].rstrip(".") or "video"


def _safe_name_032(stem: str) -> str:
    """safe_name of 0.3.2 and older (it kept "..."): tells which folder names fix_dotted_names() may re-derive."""
    s = re.sub(r"[^\w\-. ]+", "_", stem, flags=re.UNICODE).strip(" .")
    s = re.sub(r"_{2,}", "_", re.sub(r"\s+", "_", s)).strip("_")
    return s[:80] or "video"


def fix_dotted_names(analysis: Path = ANALYSIS, cards: Path | None = None, log=print) -> list[tuple[str, str]]:
    """Rename analysis folders made by 0.3.2 and older whose name has ".." (a title with "..."): the app could not
    open them. The new name is the one safe_name gives the video now, so a new analysis of it finds the folder. The
    old name is replaced where the lab wrote it - events.json (name, analysis id), review_todo.md, report.html, the
    feedback files and this PC's reference cards (`cards`, default knowledge\\local\\references) - but never inside
    the path of the video itself. A folder in use (a file open elsewhere) is left for the next start. -> [(old, new)]"""
    cards = cards or LAB / "knowledge" / "local" / "references"
    done = []
    for d in sorted(analysis.iterdir()) if analysis.is_dir() else []:
        if not d.is_dir() or ".." not in d.name:
            continue
        try:
            src = ((read_json(d / "events.json") or {}).get("source") or {}).get("path") or ""
        except (OSError, ValueError):
            src = ""
        stem = PureWindowsPath(src).stem
        base = safe_name(stem) if stem and _safe_name_032(stem) == d.name else safe_name(d.name)
        new, n = base, 2
        while (analysis / new).exists():
            new, n = f"{base}_{n}", n + 1
        try:
            d.rename(analysis / new)
        except OSError as e:
            log(f"could not rename analysis\\{d.name} -> {new} ({e}); trying again at the next start")
            continue
        old = d.name
        subs = [(re.compile(r"(?<![\w.\-])" + re.escape(o) + r"(?=-\d{8}-\d{6}|[^\w.\-]|$)"), n_)
                for o, n_ in {old: new, json.dumps(old)[1:-1]: json.dumps(new)[1:-1]}.items()]
        files = [p for p in (analysis / new).rglob("*") if p.suffix.lower() in (".json", ".md", ".html", ".txt")]
        files += sorted(cards.glob("*.json")) if cards.is_dir() else []
        for p in files:
            try:
                if p.stat().st_size > 50_000_000:
                    continue
                with open(p, encoding="utf-8", newline="") as f:       # newline="": line ends stay as they are
                    text = f.read()
            except (OSError, UnicodeDecodeError):
                continue
            new_text = text
            for rx, repl in subs:
                new_text = rx.sub(lambda _m, r=repl: r, new_text)
            if new_text != text:
                with open(p, "w", encoding="utf-8", newline="") as f:
                    f.write(new_text)
        log(f"renamed analysis\\{old} -> {new} (the app cannot open a name with '..')")
        done.append((old, new))
    return done


def sha256_file(path: Path, chunk: int = 8 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def file_fingerprint(path: Path) -> dict:
    st = Path(path).stat()
    return {"size": st.st_size, "mtime_ns": st.st_mtime_ns}


class SourceGuard:
    """Refuses any write that would touch the source video or land outside the analysis folder."""

    def __init__(self, source: Path, out_dir: Path):
        self.source = Path(source).resolve()
        self.out_dir = Path(out_dir).resolve()
        self.fingerprint = file_fingerprint(self.source)

    def check(self, target: Path) -> Path:
        t = Path(target).resolve()
        if t == self.source:
            raise PermissionError(f"refusing to write to the source video: {t}")
        if self.out_dir not in t.parents and t != self.out_dir:
            raise PermissionError(f"refusing to write outside the analysis folder: {t}")
        return t

    def verify_unchanged(self) -> bool:
        return file_fingerprint(self.source) == self.fingerprint


def fmt_pct(x, nd=0) -> str:
    return "n/a" if x is None else f"{x:.{nd}f}%"
