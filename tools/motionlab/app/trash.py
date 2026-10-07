"""The app's Delete buttons. Nothing is erased: files go to the Windows Recycle Bin, where the user can restore them.

Deleting is always the user's click after a dialog that lists every item (plan_* below builds that list, with sizes
and warnings); delete() re-plans on the server and moves only the items the user ticked. Allowed: a reference
(its analysis folder + its video when that lies in refs\\), a download in refs\\ or refs\\audio\\ that no analysis
uses, a video project (projects\\<name>\\: the user's clips + build\\) and single renders in a project's build\\.
Never: knowledge (cards, lessons), the library, tools, settings, or anything outside refs\\, analysis\\ and
projects\\. Claude never calls these routes: the hard rule "never delete a source video" stays Claude's rule."""
from __future__ import annotations

import ctypes
import os
import sys
import time
from pathlib import Path

from motionlab.util import ANALYSIS, LAB, REFS

from . import data

ROOTS = (ANALYSIS, REFS, data.PROJECTS)
RESOLVE_LUTS = Path(r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\MotionLab")
BIG = 10 * 1000 ** 3                     # above this the dialog says Windows may ask before deleting for good


def size_of(p: Path) -> tuple[int, int]:
    """(bytes, files) of a file or a folder (links are not followed)."""
    if p.is_file():
        return p.stat().st_size, 1
    total = n = 0
    for root, _dirs, files in os.walk(p):
        for f in files:
            try:
                total += os.lstat(os.path.join(root, f)).st_size
                n += 1
            except OSError:
                pass
    return total, n


def inside(p: Path | str) -> Path:
    """The real path, which must lie INSIDE refs\\, analysis\\ or projects\\ (never one of those folders itself; links
    and junctions are resolved first, so one pointing elsewhere is refused)."""
    r = Path(p).resolve()
    if not any(root in r.parents for root in ROOTS):
        raise PermissionError(f"only files inside refs, analysis or projects can be deleted: {p}")
    return r


def _same(a: str, b: Path) -> bool:
    try:
        return Path(a).resolve() == b
    except (OSError, ValueError):
        return False


def _mentions(obj, needle: str) -> bool:
    """Does any string in a JSON object name this path? (case-insensitive, either slash)"""
    if isinstance(obj, str):
        return obj.replace("/", "\\").lower() == needle
    if isinstance(obj, dict):
        return any(_mentions(v, needle) for v in obj.values())
    if isinstance(obj, list):
        return any(_mentions(v, needle) for v in obj)
    return False


def users_of(video: Path, skip_analysis: str | None = None) -> dict:
    """Which analyses analysed this file, and which of the user's videos (plans, Resolve builds) use it."""
    needle = str(video).replace("/", "\\").lower()
    ana = []
    for d in sorted(ANALYSIS.iterdir()) if ANALYSIS.exists() else []:
        if d.name == skip_analysis or not d.is_dir():
            continue
        src = ((data.read_json(d / "events.json", {}) or {}).get("source") or {}).get("path") \
            or (data.read_json(d / "source.json", {}) or {}).get("path")
        if src and _same(src, video):
            ana.append(d.name)
    projs = []
    for d in sorted(data.PROJECTS.iterdir()) if data.PROJECTS.exists() else []:
        b = d / "build"
        if not b.is_dir():
            continue
        files = list(b.glob("plan_v*.json")) + list((b / "resolve").glob("*_build.json"))
        if any(_mentions(data.read_json(f, {}), needle) for f in files):
            projs.append(d.name)
    return {"analyses": ana, "projects": projs}


def _video_item(src: Path, skip_analysis: str | None, us: dict | None = None) -> dict:
    b, _ = size_of(src)
    us = us or users_of(src, skip_analysis)
    warn = []
    if us["analyses"]:
        warn.append("also analysed as " + ", ".join(us["analyses"]) + " - that analysis keeps working only while the "
                    "video is there")
    if us["projects"]:
        warn.append("used by your video(s) " + ", ".join(us["projects"]) + " (as the reference / soundtrack of an edit "
                    "or in its DaVinci Resolve timeline) - deleting it breaks their renders and the Resolve timeline")
    return {"key": "video", "label": "The video file", "path": data.rel(src), "bytes": b, "files": 1,
            "what": src.name, "default": not warn, "warn": warn}


def plan_reference(name: str) -> dict:
    d = ANALYSIS / data.safe_name(name)
    if not d.is_dir():
        raise FileNotFoundError(name)
    inside(d)
    ev = data.read_json(d / "events.json", {}) or {}
    src_s = (ev.get("source") or {}).get("path") or (data.read_json(d / "source.json", {}) or {}).get("path") or ""
    b, n = size_of(d)
    nv = sum(1 for s in data.load_verdicts(d.name)["events"].values() if s.get("v"))
    items = [{"key": "analysis", "label": "The analysis", "path": data.rel(d), "bytes": b, "files": n,
              "what": "frames, contact sheets, previews, report, Claude's review"
                      + (f", your {nv} verdict{'s' if nv != 1 else ''} and notes" if nv else ""),
              "default": True, "warn": []}]
    notes = []
    src = Path(src_s).resolve() if src_s else None
    if src and src.is_file() and REFS in src.parents:
        items.append(_video_item(src, d.name))
    elif src and src.is_file():
        notes.append(f"The video stays where it is ({src}): only videos inside the lab's refs folder are deleted here.")
    elif src_s:
        notes.append("The video file is not there any more.")
    keeps = ["what the lab learned from it: its card on the Knowledge page (pacing + every reviewed effect) and "
             "the lessons"]
    return {"kind": "reference", "name": d.name, "title": Path(src_s).stem if src_s else d.name, "items": items,
            "notes": notes, "keeps": keeps}


def plan_project(name: str, resolve_state: str = "") -> dict:
    d = data.PROJECTS / data.safe_name(name)
    if not d.is_dir():
        raise FileNotFoundError(name)
    inside(d)
    clips = [p for p in d.iterdir() if p.is_file() and p.suffix.lower() in data.VIDEO_EXT]
    others = [p for p in d.iterdir() if p.is_file() and p not in clips]
    cb = sum(p.stat().st_size for p in clips)
    ob = sum(p.stat().st_size for p in others)
    bb, bn = size_of(d / "build") if (d / "build").is_dir() else (0, 0)
    parts = [f"your {len(clips)} clip{'s' if len(clips) != 1 else ''} ({data.human(cb)})"]
    if others:
        parts.append(f"{len(others)} other file{'s' if len(others) != 1 else ''} of yours ({data.human(ob)})")
    parts.append(f"everything the lab made for it: edit versions, renders, caches, Resolve files ({data.human(bb)})")
    total, files = size_of(d)
    warn = []
    builds = sorted((d / "build" / "resolve").glob("*_build.json")) if (d / "build" / "resolve").is_dir() else []
    for m in builds:
        man = data.read_json(m, {}) or {}
        warn.append(f"The DaVinci Resolve project '{man.get('project') or d.name}' (timeline "
                    f"{man.get('timeline') or m.name[:-len('_build.json')]}) uses these clips: it will show them as "
                    f"offline. MotionLab does not touch the Resolve project; its LUTs in {RESOLVE_LUTS} stay.")
    if resolve_state in ("running", "not responding"):
        warn.append("DaVinci Resolve is running: close it first, it may keep the clips open.")
    items = [{"key": "project", "label": "The whole folder", "path": data.rel(d), "bytes": total, "files": files,
              "what": "; ".join(parts), "default": True, "warn": warn}]
    return {"kind": "project", "name": d.name, "title": d.name, "items": items, "notes": [],
            "keeps": ["the references and everything learned"]}


def plan_file(relpath: str) -> dict:
    """A download in refs\\ (refs\\audio\\) that no analysis uses, or a render in a project's build folder."""
    p = inside(LAB / relpath)
    if not p.is_file():
        raise FileNotFoundError(relpath)
    parts = p.relative_to(LAB).parts
    ext = p.suffix.lower()
    if parts[0] == "refs" and (len(parts) == 2 or (len(parts) == 3 and parts[1] == "audio")) \
            and ext in data.VIDEO_EXT | data.AUDIO_EXT:
        us = users_of(p)
        if us["analyses"]:
            raise PermissionError(f"{p.name} has an analysis ({', '.join(us['analyses'])}): delete the reference "
                                  f"instead (References > the video > Delete)")
        item = _video_item(p, None, us)
        item.update(key="file", label="The downloaded file", default=True)
        kind = "download"
    elif parts[0] == "projects" and len(parts) >= 4 and parts[2] == "build" and ext in (".mp4", ".mov") \
            and (len(parts) == 4 or (len(parts) == 5 and parts[3] in ("compare", "resolve"))):
        b, _ = size_of(p)
        item = {"key": "file", "label": "The render", "path": data.rel(p), "bytes": b, "files": 1, "what": p.name,
                "default": True, "warn": []}
        kind = "render"
    else:
        raise PermissionError(f"not something the app deletes: {relpath}")
    return {"kind": kind, "name": data.rel(p), "title": p.name, "items": [item], "notes": [], "keeps": []}


def plan(kind: str, name: str, resolve_state: str = "") -> dict:
    if kind == "reference":
        out = plan_reference(name)
    elif kind == "project":
        out = plan_project(name, resolve_state)
    elif kind == "file":
        out = plan_file(name)
    else:
        raise ValueError(f"unknown kind {kind!r}")
    out["bytes"] = sum(i["bytes"] for i in out["items"] if i["default"])
    out["big"] = any(i["bytes"] > BIG for i in out["items"])
    return out


def delete(kind: str, name: str, keys: list, resolve_state: str = "") -> dict:
    """Move the ticked items of the plan to the Recycle Bin. Returns what moved, what did not, and the bytes."""
    pl = plan(kind, name, resolve_state)
    chosen = [i for i in pl["items"] if i["key"] in set(map(str, keys or []))]
    if not chosen:
        raise ValueError("nothing selected")
    paths = [inside(LAB / i["path"]) for i in chosen]
    res = recycle(paths)
    data._cache.clear()
    moved = {Path(p) for p in res["moved"]}
    return {"moved": [i["path"] for i, p in zip(chosen, paths) if p in moved],
            "failed": [{"path": i["path"], "why": res["why"]} for i, p in zip(chosen, paths) if p not in moved],
            "bytes": sum(i["bytes"] for i, p in zip(chosen, paths) if p in moved), "title": pl["title"]}


# ------------------------------------------------------------------------------------------------- Recycle Bin
FO_DELETE = 3
FOF_SILENT, FOF_NOCONFIRMATION, FOF_ALLOWUNDO, FOF_NOERRORUI, FOF_WANTNUKEWARNING = 0x4, 0x10, 0x40, 0x400, 0x4000


def _shell_delete(paths: list[Path]) -> int:
    from ctypes import wintypes

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT), ("pFrom", wintypes.LPCWSTR),
                    ("pTo", wintypes.LPCWSTR), ("fFlags", ctypes.c_ushort), ("fAnyOperationsAborted", wintypes.BOOL),
                    ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", wintypes.LPCWSTR)]

    buf = ctypes.create_unicode_buffer("\0".join(str(p) for p in paths) + "\0\0")
    op = SHFILEOPSTRUCTW()
    # owner = the window the user just clicked in (the app): if Windows has to ask (too big for the Recycle Bin, so
    # it would be deleted for good) the question shows on top of it instead of behind it
    op.hwnd = ctypes.windll.user32.GetForegroundWindow()
    op.wFunc = FO_DELETE
    op.pFrom = ctypes.cast(buf, wintypes.LPCWSTR)
    op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI | FOF_WANTNUKEWARNING
    return ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))


def recycle(paths: list[Path], tries: int = 3) -> dict:
    """Move files / folders to the Recycle Bin. A file that is still open (a video the window was just playing)
    gets a few more tries. Returns {"moved": [...], "left": [...], "why": ...}."""
    if sys.platform != "win32":
        raise RuntimeError("deleting from the app works on Windows only for now")
    left = [Path(p) for p in paths]
    code = 0
    for k in range(tries):
        code = _shell_delete(left)
        left = [p for p in left if p.exists()]
        if not left:
            break
        time.sleep(0.8)
    moved = [str(p) for p in paths if not Path(p).exists()]
    why = "" if not left else (f"Windows could not move it (code {code:#x}): a program may still have it open "
                               "(DaVinci Resolve, a player, Explorer's preview) - close it and try again")
    return {"moved": moved, "left": [str(p) for p in left], "why": why}
