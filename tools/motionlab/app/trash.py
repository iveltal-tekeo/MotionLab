"""The app's Delete buttons. Nothing is erased: files go to the Windows Recycle Bin, where the user can restore them.

Deleting is always the user's click after a dialog that lists every item (plan_* below builds that list, with sizes
and warnings); delete() re-plans on the server and moves only the items the user ticked. Allowed: a reference
(its analysis folder + its video when that lies in refs\\), a download in refs\\ or refs\\audio\\ that no analysis
uses, a video project (projects\\<name>\\: the user's clips + build\\), one clip or song of a project (New edit's
clips) and single renders in a project's build\\.
Never: knowledge (cards, lessons), the library, tools, settings, or anything outside refs\\, analysis\\ and
projects\\. Claude never calls these routes: the hard rule "never delete a source video" stays Claude's rule."""
from __future__ import annotations

import ctypes
import os
import sys
import time
from pathlib import Path

from motionlab import i18n as I18N
from motionlab.util import ANALYSIS, LAB, REFS

from . import data

ROOTS = (ANALYSIS, REFS, data.PROJECTS)
RESOLVE_LUTS = Path(r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\MotionLab")
BIG = 10 * 1000 ** 3                     # above this the dialog says Windows may ask before deleting for good
# why a file stayed: deleted.log keeps this English, the page gets it in the app's language (recycle "why_shown")
WHY_LEFT = ("Windows could not move it (code {code}): a program may still have it open (DaVinci Resolve, a player, "
            "Explorer's preview) - close it and try again")


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
        raise PermissionError(I18N.t("only files inside refs, analysis or projects can be deleted: {file}", file=p))
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
    from motionlab import notes as NT                  # 2026-10-27: notes made from it (they stay without it)
    return {"analyses": ana, "projects": projs, "notes": NT.users_of(video)}


def _video_item(src: Path, skip_analysis: str | None, us: dict | None = None) -> dict:
    b, _ = size_of(src)
    us = us or users_of(src, skip_analysis)
    warn = []
    if us["analyses"]:
        warn.append(I18N.t("also analysed as {names} - that analysis keeps working only while the video is there",
                           names=", ".join(us["analyses"])))
    if us.get("notes"):
        warn.append(I18N.t("its notes stay, without the video to play"))
    if us["projects"]:
        warn.append(I18N.tn(len(us["projects"]), "used by your video(s) {names} (as the reference / soundtrack of an "
                                                 "edit or in its DaVinci Resolve timeline) - deleting it breaks their "
                                                 "renders and the Resolve timeline",
                            "used by your video(s) {names} (as the reference / soundtrack of an edit or in its DaVinci "
                            "Resolve timeline) - deleting it breaks their renders and the Resolve timeline",
                            names=", ".join(us["projects"])))
    return {"key": "video", "label": I18N.t("The video file"), "path": data.rel(src), "bytes": b, "files": 1,
            "what": src.name, "default": not warn, "warn": warn}


def _human(n: float | None) -> str:
    """data.human in the app's language: Spanish writes 1,2 GB."""
    h = data.human(n)
    return h.replace(".", ",") if I18N.lang() == "es" else h


def plan_reference(name: str) -> dict:
    d = ANALYSIS / data.safe_name(name)
    if not d.is_dir() or d.name.lower() in ("thumbs", "templates", "texts", "notes"):   # thumbnail sets (kind
        # "thumbs"), motion packs (0.5.0), sets of scripts & prompts (kind "texts", 2026-10-18), notes (kind "notes")
        raise FileNotFoundError(name)
    inside(d)
    ev = data.read_json(d / "events.json", {}) or {}
    src_s = (ev.get("source") or {}).get("path") or (data.read_json(d / "source.json", {}) or {}).get("path") or ""
    b, n = size_of(d)
    nv = sum(1 for s in data.load_verdicts(d.name)["events"].values() if s.get("v"))
    items = [{"key": "analysis", "label": I18N.t("The analysis"), "path": data.rel(d), "bytes": b, "files": n,
              "what": I18N.tn(nv, "frames, contact sheets, previews, report, Claude's review, your {n} verdict and notes",
                              "frames, contact sheets, previews, report, Claude's review, your {n} verdicts and notes")
              if nv else I18N.t("frames, contact sheets, previews, report, Claude's review"),
              "default": True, "warn": []}]
    notes = []
    src = Path(src_s).resolve() if src_s else None
    if src and src.is_file() and REFS in src.parents:
        items.append(_video_item(src, d.name))
    elif src and src.is_file():
        notes.append(I18N.t("The video stays where it is ({path}): only videos inside the lab's refs folder are "
                            "deleted here.", path=src))
    elif src_s:
        notes.append(I18N.t("The video file is not there any more."))
    keeps = [I18N.t("what the lab learned from it: its card in Claude's memory (pacing + every reviewed effect) and "
                    "the lessons")]
    try:                                        # the name the pages show (knowledge.label(), 2026-10-19)
        from motionlab import knowledge as KN
        shown = (KN.style(d.name) or {}).get("label") or ""
    except Exception:
        shown = ""
    return {"kind": "reference", "name": d.name, "title": shown or (Path(src_s).stem if src_s else d.name),
            "items": items,
            "notes": notes, "keeps": keeps}


def plan_project(name: str, resolve_state: str = "") -> dict:
    d = data.PROJECTS / data.safe_name(name)
    if not d.is_dir():
        raise FileNotFoundError(name)
    inside(d)
    clips = [p for p in d.iterdir() if p.is_file() and p.suffix.lower() in data.CLIP_EXT]     # videos + photos
    others = [p for p in d.iterdir() if p.is_file() and p not in clips]
    cb = sum(p.stat().st_size for p in clips)
    ob = sum(p.stat().st_size for p in others)
    bb, bn = size_of(d / "build") if (d / "build").is_dir() else (0, 0)
    parts = [I18N.tn(len(clips), "your {n} clip ({size})", "your {n} clips ({size})", size=_human(cb))]
    if others:
        parts.append(I18N.tn(len(others), "{n} other file of yours ({size})", "{n} other files of yours ({size})",
                             size=_human(ob)))
    parts.append(I18N.t("everything the lab made for it: edit versions, renders, caches, Resolve files ({size})",
                        size=_human(bb)))
    total, files = size_of(d)
    warn = []
    builds = sorted((d / "build" / "resolve").glob("*_build.json")) if (d / "build" / "resolve").is_dir() else []
    for m in builds:
        man = data.read_json(m, {}) or {}
        warn.append(I18N.t("The DaVinci Resolve project '{project}' (timeline {timeline}) uses these clips: it will "
                           "show them as offline. MotionLab does not touch the Resolve project; its LUTs in {folder} "
                           "stay.", project=man.get("project") or d.name,
                           timeline=man.get("timeline") or m.name[:-len("_build.json")], folder=RESOLVE_LUTS))
    if resolve_state in ("running", "not responding"):
        warn.append(I18N.t("DaVinci Resolve is running: close it first, it may keep the clips open."))
    items = [{"key": "project", "label": I18N.t("The whole folder"), "path": data.rel(d), "bytes": total,
              "files": files, "what": "; ".join(parts), "default": True, "warn": warn}]
    return {"kind": "project", "name": d.name, "title": d.name, "items": items, "notes": [],
            "keeps": [I18N.t("the references and everything learned")]}


def plan_file(relpath: str) -> dict:
    """A download in refs\\ (refs\\audio\\) that no analysis uses, a clip or song in a project's folder, or a render
    in a project's build folder."""
    p = inside(LAB / relpath)
    if not p.is_file():
        raise FileNotFoundError(relpath)
    parts = p.relative_to(LAB).parts
    ext = p.suffix.lower()
    if parts[0] == "refs" and (len(parts) == 2 or (len(parts) == 3 and parts[1] == "audio")) \
            and ext in data.VIDEO_EXT | data.AUDIO_EXT | data.IMAGE_EXT:     # a photo: a downloaded post's part
        us = users_of(p)
        if us["analyses"]:
            raise PermissionError(I18N.t("{file} has an analysis ({names}): delete the reference instead (References > "
                                         "the video > Delete)", file=p.name, names=", ".join(us["analyses"])))
        item = _video_item(p, None, us)
        item.update(key="file", label=I18N.t("The downloaded file"), default=True)
        kind = "download"
    elif parts[0] == "projects" and len(parts) == 3 and ext in data.CLIP_EXT | data.AUDIO_EXT:
        # one clip or song of a video (2026-10-22, New edit's clips, the user: "see which videos we have? or if we can
        # manage them? delete") - its edits and a Resolve project may use it: said before the yes
        b, _ = size_of(p)
        srcs = (data.read_json(p.parent / "build" / "sources.json", {}) or {}).get("sources", {})
        warn = [I18N.t("Its edits use it as clip {id}: a new render of them will miss it.", id=sid)
                for sid, s in sorted(srcs.items()) if _same(s.get("path", ""), p)][:1]
        if (p.parent / "build" / "resolve").is_dir() and any((p.parent / "build" / "resolve").glob("*_build.json")):
            warn.append(I18N.t("A DaVinci Resolve project of this video may use it: it will show it as offline."))
        item = {"key": "file", "label": I18N.t("The song") if ext in data.AUDIO_EXT else I18N.t("The photo")
                if ext in data.PHOTO_EXT else I18N.t("The clip"),
                "path": data.rel(p), "bytes": b, "files": 1, "default": True, "warn": warn,
                "what": I18N.t("in the folder of the video {name}", name=p.parent.name)}
        kind = "clip"
        twin = next((p.parent / (p.name + x) for x in (".mp4", ".mov") if (p.parent / (p.name + x)).is_file()), None)
        if ext in data.PHOTO_EXT and twin:                   # an add-on's still video of the photo goes with it
            tb, _ = size_of(twin)
            items = [item, {"key": "twin", "label": I18N.t("Its still-video copy"), "path": data.rel(twin),
                            "bytes": tb, "files": 1, "default": True, "warn": [],
                            "what": I18N.t("{file} - made from the photo before MotionLab took photos", file=twin.name)}]
            return {"kind": kind, "name": data.rel(p), "title": p.name, "items": items, "notes": [], "keeps": []}
    elif parts[0] == "projects" and len(parts) >= 4 and parts[2] == "build" and ext in (".mp4", ".mov") \
            and (len(parts) == 4 or (len(parts) == 5 and parts[3] in ("compare", "resolve"))):
        b, _ = size_of(p)
        item = {"key": "file", "label": I18N.t("The render"), "path": data.rel(p), "bytes": b, "files": 1,
                "what": p.name, "default": True, "warn": []}
        kind = "render"
    else:
        raise PermissionError(I18N.t("not something the app deletes: {file}", file=relpath))
    return {"kind": kind, "name": data.rel(p), "title": p.name, "items": [item], "notes": [], "keeps": []}


def plan_thumbs(name: str) -> dict:
    """A thumbnail set (0.4.5, analysis\\thumbs\\<set>): its pictures (downloaded, or copies of the user's - the
    originals stay where they were), the measures, Claude's patterns, the user's verdicts on them."""
    d = data._thumbs_root() / data.safe_name(name)
    if not d.is_dir():
        raise FileNotFoundError(name)
    inside(d)
    b, n = size_of(d)
    label = (data.read_json(d / "set.json", {}) or {}).get("label") or d.name
    return {"kind": "thumbs", "name": d.name, "title": label, "notes": [], "keeps": [],
            "items": [{"key": "set", "label": I18N.t("The thumbnail set"), "path": data.rel(d), "bytes": b, "files": n,
                       "what": I18N.t("the pictures (copies), their measures, Claude's patterns and your verdicts on "
                                      "them"), "default": True, "warn": []}]}


def plan_texts(name: str) -> dict:
    """A set of scripts & prompts (2026-10-18, analysis\\texts\\<set>): the set's own files only - its list, the
    measures, Claude's patterns, the user's verdicts on them. The texts themselves stay in the prompt library."""
    d = data._texts_root() / data.safe_name(name)
    if not d.is_dir():
        raise FileNotFoundError(name)
    inside(d)
    b, n = size_of(d)
    label = (data.read_json(d / "set.json", {}) or {}).get("label") or d.name
    return {"kind": "texts", "name": d.name, "title": label, "notes": [],
            "keeps": [I18N.t("the scripts and prompts stay in your prompt library")],
            "items": [{"key": "set", "label": I18N.t("The set of scripts & prompts"), "path": data.rel(d), "bytes": b,
                       "files": n, "what": I18N.t("the list of the texts, what MotionLab measured, Claude's patterns "
                                                  "and your verdicts on them"), "default": True, "warn": []}]}


def plan_notes(name: str, video_only: bool = False) -> dict:
    """Notes from a video (2026-10-27, analysis\\notes\\<name>): the notes (Claude's, the user's own, the words, the
    key frames) and the video when it lies in refs\\. video_only (kind "notes_video", the user: "option to delete the
    video afterwards but keep the notes") = the video alone - the notes stay, without the player."""
    from motionlab import notes as NT
    d, n = NT.need(name)
    inside(d)
    items, notes = [], []
    if not video_only:
        b, k = size_of(d)
        items.append({"key": "notes", "label": I18N.t("The notes"), "path": data.rel(d), "bytes": b, "files": k,
                      "what": I18N.t("Claude's notes, your own notes, the words and the key frames"),
                      "default": True, "warn": []})
    src = Path(n["video"]).resolve() if n.get("video") else None
    if src and src.is_file() and REFS in src.parents:
        us = users_of(src)
        us["notes"] = [x for x in us["notes"] if x != d.name]       # these notes: said by the dialog's keeps
        items.append(_video_item(src, None, us))
    elif src and src.is_file():
        notes.append(I18N.t("The video stays where it is ({path}): only videos inside the lab's refs folder are "
                            "deleted here.", path=src))
    elif video_only:
        raise FileNotFoundError(I18N.t("The video file is not there any more."))
    return {"kind": "notes_video" if video_only else "notes", "name": d.name, "title": NT.label_of(n),
            "items": items, "notes": notes,
            "keeps": [I18N.t("the notes, your own notes and the key frames")] if video_only else []}


def plan(kind: str, name: str, resolve_state: str = "") -> dict:
    if kind in ("notes", "notes_video"):
        out = plan_notes(name, kind == "notes_video")
    elif kind == "thumbs":
        out = plan_thumbs(name)
    elif kind == "texts":
        out = plan_texts(name)
    elif kind == "reference":
        out = plan_reference(name)
    elif kind == "project":
        out = plan_project(name, resolve_state)
    elif kind == "file":
        out = plan_file(name)
    else:
        raise ValueError(I18N.t("unknown kind {kind}", kind=repr(kind)))
    out["bytes"] = sum(i["bytes"] for i in out["items"] if i["default"])
    out["big"] = any(i["bytes"] > BIG for i in out["items"])
    return out


def delete(kind: str, name: str, keys: list, resolve_state: str = "") -> dict:
    """Move the ticked items of the plan to the Recycle Bin. Returns what moved, what did not, and the bytes."""
    pl = plan(kind, name, resolve_state)
    chosen = [i for i in pl["items"] if i["key"] in set(map(str, keys or []))]
    if not chosen:
        raise ValueError(I18N.t("nothing selected"))
    paths = [inside(LAB / i["path"]) for i in chosen]
    res = recycle(paths)
    data._cache.clear()
    moved = {Path(p) for p in res["moved"]}
    out = {"moved": [i["path"] for i, p in zip(chosen, paths) if p in moved],
           "failed": [{"path": i["path"], "why": res["why"]} for i, p in zip(chosen, paths) if p not in moved],
           "bytes": sum(i["bytes"] for i, p in zip(chosen, paths) if p in moved), "title": pl["title"]}
    if res.get("why_shown"):                     # the page's words (server.py swaps them in after deleted.log)
        out["why_shown"] = res["why_shown"]
    return out


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
        raise RuntimeError(I18N.t("deleting from the app works on Windows only for now"))
    left = [Path(p) for p in paths]
    code = 0
    for k in range(tries):
        code = _shell_delete(left)
        left = [p for p in left if p.exists()]
        if not left:
            break
        time.sleep(0.8)
    moved = [str(p) for p in paths if not Path(p).exists()]
    why = "" if not left else WHY_LEFT.format(code=f"{code:#x}")
    out = {"moved": moved, "left": [str(p) for p in left], "why": why}
    if left:                                     # in the app's language for the page; "why" stays English (the log)
        out["why_shown"] = I18N.t(WHY_LEFT, code=f"{code:#x}")
    return out
