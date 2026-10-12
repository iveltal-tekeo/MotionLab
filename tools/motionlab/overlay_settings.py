"""Editable overlay settings and the graphics library (0.3.2). Standard library only: the app imports it.

An overlay folder (projects\\<project>\\build\\overlays\\<name>\\, made by tools\\overlay.py new) = index.html (HTML / CSS /
GSAP that HyperFrames renders) + overlay.json {name, frames, fps, width, height, values} + gsap.min.js (+ assets\\).
What the user can change is declared on the composition's <html> tag in HyperFrames' own format:
    <html lang="en" data-composition-variables='[{"id": "text", "type": "string", "label": "Text", "default": "4AM"}]'>
types: string, color (#rrggbb), number (optional min / max / step; times in frames), boolean, enum (options =
[{"value": .., "label": ..}]); the page reads them with window.__hyperframes.getVariables(). overlay.json "values" =
the user's choices (the app's Graphics tab writes them, `overlay.py set` too); `overlay.py render` passes them with
--variables-file --strict-variables and writes render.json (what was rendered, `inputs` = the hash below) and
thumb.png. An overlay is "current" when render.json's inputs equal inputs_hash() now.
The graphics library: library\\graphics\\<name>\\ = overlays the user approved (`overlay.py save`, a rendered .mov
included - drag it into a Resolve Power Bin, Resolve's scripting has no Power Bin calls) and
tools\\overlays\\examples\\<name>\\ (come with MotionLab). `overlay.py new <folder> --from <name>` starts a project's
overlay from either.
"""
from __future__ import annotations

import hashlib
import html
import json
import math
import os
import re
import shutil
from pathlib import Path

from .timecode import frame_to_tc
from .util import LAB

LIBRARY = LAB / "library" / "graphics"
EXAMPLES = LAB / "tools" / "overlays" / "examples"
SOURCES = ("index.html", "overlay.json", "gsap.min.js", "hyperframes.json")      # + assets\ (what new / save copy)
TYPES = ("string", "color", "number", "boolean", "enum")
_DECL = re.compile(r"<html\b[^>]*?\bdata-composition-variables\s*=\s*(?:'([^']*)'|\"([^\"]*)\")", re.S | re.I)
_COLOR = re.compile(r"^#(?:[0-9a-f]{3}|[0-9a-f]{6})$", re.I)


def rel(p: Path) -> str:
    try:
        return Path(p).resolve().relative_to(LAB.resolve()).as_posix()
    except ValueError:
        return str(p)


def declared(folder: Path) -> list[dict]:
    """The settings the composition declares (data-composition-variables on <html>), in page order."""
    p = Path(folder) / "index.html"
    if not p.exists():
        return []
    m = _DECL.search(p.read_text(encoding="utf-8", errors="replace"))
    if not m:
        return []
    raw = m.group(1) if m.group(1) is not None else m.group(2)
    try:
        decl = json.loads(html.unescape(raw))                # an attribute: &quot; / &amp; / &#39; allowed
    except json.JSONDecodeError as e:
        raise ValueError(f"{p}: data-composition-variables is not valid JSON ({e})") from None
    out = []
    for d in decl if isinstance(decl, list) else []:
        if isinstance(d, dict) and d.get("id") and d.get("type") in TYPES:
            if d["type"] == "enum":
                d["options"] = [o if isinstance(o, dict) else {"value": o, "label": str(o)}
                                for o in d.get("options", [])]
            out.append(d)
    return out


def conf(folder: Path) -> dict:
    """overlay.json, or for an example without one: name / fps / frames / size from its index.html."""
    folder = Path(folder)
    p = folder / "overlay.json"
    if p.exists():
        c = json.loads(p.read_text(encoding="utf-8"))
        c.setdefault("name", folder.name)
        return c
    t = (folder / "index.html").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"FPS\s*=\s*([\d.]+)\s*,\s*FRAMES\s*=\s*(\d+)", t)
    w = re.search(r'data-width="(\d+)"', t)
    h = re.search(r'data-height="(\d+)"', t)
    return {"name": folder.name, "fps": float(m[1]) if m else 25.0, "frames": int(m[2]) if m else 0,
            "width": int(w[1]) if w else 1920, "height": int(h[1]) if h else 1080}


def defaults(decl: list[dict]) -> dict:
    return {d["id"]: d.get("default") for d in decl}


def check(decl: list[dict], values: dict) -> tuple[dict, list[str]]:
    """(cleaned values for the declared ids, problems). Unknown ids are dropped; wrong ones keep the default."""
    by = {d["id"]: d for d in decl}
    out, bad = {}, []
    for k, v in (values or {}).items():
        d = by.get(k)
        if not d:
            continue
        t, label = d["type"], d.get("label", k)
        if t == "string":
            if not isinstance(v, str) or len(v) > 500:
                bad.append(f"{label}: text up to 500 characters")
                continue
            out[k] = "".join(c for c in v if c == "\n" or c >= " ")
        elif t == "color":
            if not isinstance(v, str) or not _COLOR.match(v.strip()):
                bad.append(f"{label}: a colour like #ff8800")
                continue
            c = v.strip().lower()
            out[k] = "#" + "".join(ch * 2 for ch in c[1:]) if len(c) == 4 else c
        elif t == "number":
            try:
                x = float(v)
            except (TypeError, ValueError):
                bad.append(f"{label}: a number")
                continue
            if not math.isfinite(x):
                bad.append(f"{label}: a number")
                continue
            lo, hi = d.get("min"), d.get("max")
            if (lo is not None and x < lo) or (hi is not None and x > hi):
                bad.append(f"{label}: between {lo} and {hi}")
                continue
            out[k] = int(x) if x.is_integer() else x
        elif t == "boolean":
            if isinstance(v, str):
                v = v.strip().lower() in ("1", "true", "yes", "on")
            out[k] = bool(v)
        elif t == "enum":
            ok = [o["value"] for o in d.get("options", [])]
            if v not in ok:
                bad.append(f"{label}: one of {', '.join(map(str, ok))}")
                continue
            out[k] = v
    return out, bad


def values(folder: Path) -> dict:
    """What a render uses: the declared defaults with overlay.json's values on top (declared ids only)."""
    decl = declared(folder)
    v, _ = check(decl, conf(folder).get("values") or {})
    return {**defaults(decl), **v}


def _write_json(p: Path, data: dict) -> None:
    tmp = p.with_name(p.name + ".part")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, p)


def set_values(folder: Path, new: dict) -> dict:
    """Validate and store the user's values in overlay.json (merged over the ones there); ValueError on a bad value."""
    folder = Path(folder)
    decl = declared(folder)
    if not decl:
        raise ValueError(f"{folder.name} declares no settings (data-composition-variables in its index.html)")
    clean, bad = check(decl, new)
    if bad:
        raise ValueError("; ".join(bad))
    p = folder / "overlay.json"
    c = conf(folder)
    old, _ = check(decl, c.get("values") or {})
    c["values"] = {**old, **clean}
    _write_json(p, c)
    return status(folder)


def inputs_hash(folder: Path) -> str:
    """What decides the rendered pixels: index.html, the values, length / rate / size and the assets."""
    folder = Path(folder)
    c = conf(folder)
    h = hashlib.sha1()
    h.update((folder / "index.html").read_bytes())
    h.update(json.dumps({"values": values(folder), **{k: c.get(k) for k in ("frames", "fps", "width", "height")}},
                        sort_keys=True).encode())
    a = folder / "assets"
    if a.is_dir():
        for f in sorted(a.rglob("*")):
            if f.is_file():
                st = f.stat()
                h.update(f"{f.relative_to(a).as_posix()}:{st.st_size}:{st.st_mtime_ns}".encode())
    return h.hexdigest()[:16]


def status(folder: Path) -> dict:
    """An overlay as the app shows it: size, length, its settings with the current values, render state."""
    folder = Path(folder)
    c = conf(folder)
    fps = float(c.get("fps") or 25)
    frames = int(c.get("frames") or 0)
    try:
        decl = declared(folder)
        problem = ""
    except ValueError as e:
        decl, problem = [], str(e)
    vals = values(folder) if decl else {}
    rj = folder / "render.json"
    rinfo = json.loads(rj.read_text(encoding="utf-8")) if rj.exists() else {}
    mov = folder / f"{c['name']}.mov"
    thumb = folder / "thumb.png"
    rendered = mov.exists()
    try:
        current = rendered and rinfo.get("inputs") == inputs_hash(folder)
    except OSError:
        current = False
    return {"name": c["name"], "folder": rel(folder), "frames": frames, "fps": fps,
            "width": int(c.get("width") or 0), "height": int(c.get("height") or 0),
            "range_tc": f"{frame_to_tc(0, fps)} - {frame_to_tc(max(frames - 1, 0), fps)}",
            "settings": [{**d, "value": vals.get(d["id"])} for d in decl], "note": c.get("note", ""),
            "rendered": rendered, "current": bool(current), "rendered_at": rinfo.get("date", ""),
            "mov": rel(mov) if rendered else None,
            "thumb": rel(thumb) if thumb.exists() else None,
            "thumb_v": int(thumb.stat().st_mtime) if thumb.exists() else 0, "problem": problem,
            "captions": c.get("captions"),
            "resolve_clips": [rel(p) for p in resolve_copies(folder)[:3]],
            "srt": rel(folder / f"{c['name']}.srt") if (folder / f"{c['name']}.srt").exists() else None}


def resolve_copy(folder: Path) -> Path:
    """The clip DaVinci Resolve gets: a numbered copy of the current render, <folder>\\resolve\\<name>_<id>.mov.
    Resolve keeps the files it uses open and Windows then refuses to replace them (measured 2026-10-12), so the lab's
    own <name>.mov must stay free for the next render; `overlay.py refresh` moves Resolve onto the newest copy."""
    folder = Path(folder)
    c = conf(folder)
    mov = folder / f"{c['name']}.mov"
    if not mov.exists():
        raise ValueError(f"{c['name']}: not rendered yet")
    st = mov.stat()
    rid = hashlib.sha1(f"{st.st_size}:{st.st_mtime_ns}".encode()).hexdigest()[:8]     # one per render
    dst = folder / "resolve" / f"{c['name']}_{rid}.mov"
    if not dst.exists():
        dst.parent.mkdir(exist_ok=True)
        tmp = dst.with_name(dst.name + ".part")
        shutil.copy2(mov, tmp)
        os.replace(tmp, dst)
    return dst


def resolve_copies(folder: Path) -> list[Path]:
    """The copies made for Resolve, newest first."""
    d = Path(folder) / "resolve"
    return sorted(d.glob("*.mov"), key=lambda p: p.stat().st_mtime, reverse=True) if d.is_dir() else []


def project_overlays(project: str) -> list[dict]:
    root = LAB / "projects" / project / "build" / "overlays"
    return [status(p.parent) for p in sorted(root.glob("*/index.html"))] if root.is_dir() else []


def library() -> list[dict]:
    """The graphics library: the user's approved graphics first, then the examples that come with MotionLab."""
    out = []
    for kind, root in (("yours", LIBRARY), ("example", EXAMPLES)):
        for p in sorted(root.glob("*/index.html")) if root.is_dir() else []:
            try:
                s = status(p.parent)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            s["kind"] = kind
            out.append(s)
    return out


def find_graphic(name: str) -> Path:
    """A library graphic or an example by folder name (the user's own first)."""
    if not re.fullmatch(r"[\w.-]+", name or ""):
        raise ValueError(f"not a graphic name: {name!r}")
    for root in (LIBRARY, EXAMPLES):
        if (root / name / "index.html").exists():
            return root / name
    raise ValueError(f"no graphic '{name}' in library\\graphics or tools\\overlays\\examples")
