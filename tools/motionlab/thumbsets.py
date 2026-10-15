"""Thumbnail sets (0.4.5 Bulk, step 1 "Thumbnails only"): many thumbnails without their videos - a channel's or a
playlist's newest N (yt-dlp lists them; no video is downloaded), single video links, or the user's own image files -
measured together so their common patterns show. No Claude here: Claude reads the sheets and names what only eyes see
(the font's style, the structure, the emotion) into style.json. CLI: tools\\thumbsets.py.

Layout - one set per folder under ROOT (analysis\\thumbs\\; MOTIONLAB_THUMBS_ROOT or the CLI's --root moves it, tests do):
    <ROOT>\\<set>\\set.json       {"name", "label", "created", "updated", "source": {"kind": "channel|playlist|links|files",
                                  "url", "channel", "followers", "fetched"}, "items": [{"n", "file" ("img/01_<id>.jpg"),
                                  "id", "title", "url", "views", "followers", "outperformer" (views / followers, 2
                                  decimals, null when unknown), "upload_date", "from" (channel|playlist|link|file),
                                  "sha1", "measures"}], "summary"}
                  img\\NN_<id>.<ext>  the pictures: downloaded, or COPIED from the user's files (the originals are only
                                  read, never moved or changed)
                  sheet_1.png ...   15 tiles per sheet (5 x 3): "#n", views and views / followers, the title cut short
                                  under each picture (never over it) - Claude names patterns per number from one sheet
                  style.json        written by Claude (a skill), never by this module; load_style() reads it
<set> = util.safe_name of the name given ("mrbeast"). A set's files are all lab-made: remove_item() deletes only them.

What counts (measure, at <= 640 px; re-used while the file's name / size / time stays the same - "sig" - and the
face detector has not appeared since):
- look: brightness (L*, 0-100), saturation (HSV, %), colourfulness, contrast (thumbnail.look); 4 main colours with
  their share (colour.palette). YouTube's 4:3 fallback pictures (sddefault / hqdefault) carry black bands above and
  below the 16:9 picture: they are cut off before measuring ("bars": true).
- faces (OpenCV's YuNet, thumbnail.faces): how many, the biggest one's height in % of the picture, its centre's side
  (left / centre / right thirds). Without the model file: None everywhere = "not measured", never a guess.
- text (thumbnail.estimate_text - an ESTIMATE: flat-coloured letter blobs with strong edges, three in a row at least;
  it can take a logo for text and miss thin or textured letters): found, the letters' height in % of the picture, the
  blob count, where the text's centre sits (top / middle / bottom + left / centre / right) and the share of the picture
  the text covers (letters grown by about half a letter, so words count as blocks).
- summary: n; medians of brightness / saturation / colourfulness / contrast / face size / letter size weighted by the
  outperformer score (weight = max(0.25, views / followers or 1), as thumbnail.refs: the videos that beat their
  channel count most); faces in k of n; the usual face side and text position (most common + count); the set's main
  colours (every picture's palette clustered in Lab into <= 6 colours, near ones merged (MERGE_DE), with how many
  pictures use each and a word for each); the best 3 by
  views / followers; horizontal / vertical pictures.

style.json (Claude's, after reading the sheets; the shape load_style() returns):
    {"set": "mrbeast", "date": "2026-10-15", "summary": "2-3 sentences",
     "patterns": [{"id": "P1", "kind": "text|font|colour|structure|face|emotion|title", "what": "...",
                   "how_many": "12 of 15", "examples": [1, 4, 9]}],
     "font": {"style": "heavy condensed sans, white, black outline", "closest": ["Anton", "Bebas Neue", "Impact"],
              "sure": false},
     "colours": ["#ffcc00", ...], "words": {"median": 3, "max": 4, "case": "upper"},
     "structures": [{"name": "face + big text", "count": 8}],
     "for_make": {"template": "outline|block|split", "text_colour": "#ffffff", "outline_colour": "#000000",
                  "font": "Anton", "words": 3}}
Other people's thumbnails stay on this PC: nothing here writes to knowledge\\ (the app decides what is shared - only a
style's words and numbers, never the pictures). Network only in fetch() / add_links().
"""
from __future__ import annotations

import colorsys
import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .util import ANALYSIS, LAB, read_json, safe_name, write_json

ROOT = Path(os.environ.get("MOTIONLAB_THUMBS_ROOT") or (ANALYSIS / "thumbs"))
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")
PER_SHEET, COLS = 15, 5
MEASURE_PX = 640
MERGE_DE = 15              # the set's main colours: clusters nearer than this in Lab (delta E 76) are one colour
THREADS = 4
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_LOCKS: dict[str, threading.RLock] = {}
_LOCKS_LOCK = threading.Lock()


# ------------------------------------------------------------------------------------------ small helpers
def rel(p) -> str:
    """Lab-relative path with forward slashes (what the app serves); the full path when outside the lab (tests)."""
    try:
        return Path(p).resolve().relative_to(LAB.resolve()).as_posix()
    except (ValueError, OSError):
        return Path(p).as_posix()


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M")


def set_name(name: str) -> str:
    """The folder name for a set (letters, digits, _ - . only); refuses an empty one."""
    if not re.search(r"\w", str(name or ""), re.U):
        raise ValueError("give the set a short name, e.g. mrbeast")
    return safe_name(str(name))


def set_dir(name: str) -> Path:
    return Path(ROOT) / set_name(name)


def _lock(name: str) -> threading.RLock:
    key = str(set_dir(name)).lower()
    with _LOCKS_LOCK:
        return _LOCKS.setdefault(key, threading.RLock())


def _load(name: str) -> dict | None:
    try:
        S = read_json(set_dir(name) / "set.json")
    except (OSError, ValueError):
        return None
    return S if isinstance(S, dict) else None


def _need(name: str) -> dict:
    S = _load(name)
    if S is None:
        raise FileNotFoundError(f"no thumbnail set called '{name}' (thumbsets.py list shows them)")
    S.setdefault("items", [])
    return S


def _new(name: str, label: str | None, source: dict) -> dict:
    return {"name": set_name(name), "label": (label or str(name)).strip()[:80], "created": _now(), "updated": _now(),
            "source": source, "items": [], "summary": {}}


def _save(name: str, S: dict) -> None:
    S["updated"] = _now()
    write_json(set_dir(name) / "set.json", S, indent=1)


def _sig(p: Path) -> str:
    st = p.stat()
    return f"{p.name}:{st.st_size}:{st.st_mtime_ns}"


def _outperformer(views, followers) -> float | None:
    return round(views / followers, 2) if isinstance(views, (int, float)) and followers else None


def _date(s) -> str | None:
    s = str(s or "")
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if re.fullmatch(r"\d{8}", s) else None


def num(v) -> str:
    """1234567 -> 1.2M (views in labels)."""
    if not isinstance(v, (int, float)):
        return "-"
    for d, u in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if v >= d:
            return f"{v / d:.1f}".rstrip("0").rstrip(".") + u
    return str(int(v))


def _ext_of(data: bytes) -> str | None:
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return None


def colour_word(hexs: str) -> str:
    """#ffcc00 -> 'yellow' (HSV hue; black / white / grey for the dull ones; dark / pale)."""
    r, g, b = (int(hexs[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if v < 0.18:
        return "black"
    if s < 0.18:
        return "white" if v > 0.85 else "light grey" if v > 0.65 else "grey" if v > 0.35 else "dark grey"
    d = h * 360
    w = ("red" if d < 15 or d >= 345 else "orange" if d < 40 else "yellow" if d < 70 else "green" if d < 160
         else "cyan" if d < 195 else "blue" if d < 255 else "purple" if d < 290 else "pink")
    if w in ("red", "orange", "yellow") and v < 0.55 and (w != "red" or s < 0.6):
        return "brown"
    if w == "orange" and s < 0.6:
        return "tan"                                         # skin, sand, wood
    if s < 0.3:
        return "muted " + w
    if v < 0.4:
        return "dark " + w
    if s < 0.4 and v > 0.8:
        return "pale " + w
    return w


# ------------------------------------------------------------------------------------------ measuring one picture
def _small(rgb: np.ndarray, px: int = MEASURE_PX) -> np.ndarray:
    import cv2
    H, W = rgb.shape[:2]
    s = px / max(W, H)
    if s >= 1:
        return rgb
    return cv2.resize(rgb, (max(1, round(W * s)), max(1, round(H * s))), interpolation=cv2.INTER_AREA)


def trim_bars(rgb: np.ndarray) -> tuple[np.ndarray, bool]:
    """Black bands above and below (YouTube's 4:3 sddefault / hqdefault around a 16:9 picture) cut off - only when both
    bands are there, about as tall, and what stays is about 16:9."""
    g = rgb.astype(np.float32).mean(axis=2)
    H, W = g.shape
    flat = (g.mean(axis=1) < 16) & (g.std(axis=1) < 8)
    top = int(np.argmin(flat)) if not flat.all() else H
    bot = int(np.argmin(flat[::-1])) if not flat.all() else H
    if top >= 0.04 * H and bot >= 0.04 * H and abs(top - bot) <= 0.03 * H and top + bot < H:
        inner = rgb[top:H - bot]
        if 1.5 <= W / inner.shape[0] <= 2.0:
            return inner, True
    return rgb, False


def _third(x: float, words: tuple[str, str, str]) -> str:
    return words[0] if x < 1 / 3 else words[2] if x > 2 / 3 else words[1]


def where(v: str, h: str) -> str:
    return "centre" if (v, h) == ("middle", "centre") else f"{v} {h}"


def measure_picture(path: Path) -> dict:
    """One picture's measures (see the module's docstring). Reads the file only."""
    import cv2
    from .colour import palette
    from .thumbnail import estimate_text, face_model, faces, look
    with Image.open(path) as im:
        W, H = im.size
        rgb = np.asarray(im.convert("RGB"))
    small, bars = trim_bars(_small(rgb))
    h, w = small.shape[:2]
    fc = faces(small)
    est = estimate_text(small)
    text = {"found": False}
    if est.get("found"):
        mask = est["mask"]
        ys, xs = np.nonzero(mask)
        cy, cx = float(ys.mean()) / h, float(xs.mean()) / w
        v, hh = _third(cy, ("top", "middle", "bottom")), _third(cx, ("left", "centre", "right"))
        k = max(3, int(est["height"] * 0.6)) | 1
        grown = cv2.dilate(mask.astype(np.uint8), np.ones((k, k), np.uint8))
        text = {"found": True, "letter_share": round(est["height"] / h, 3), "blobs": int(est["count"]),
                "v": v, "h": hh, "where": where(v, hh), "centre": [round(cx, 3), round(cy, 3)],
                "area": round(float(grown.mean()), 3)}
    return {"sig": _sig(Path(path)), "size": [W, H], "aspect": round(W / H, 3), "bars": bars, **look(small),
            "palette": palette(small, 4), "face_detector": fc is not None or face_model() is not None,
            "faces": None if fc is None else len(fc),
            "face_share": round(fc[0][3] / h, 3) if fc else None,
            "face_side": _third((fc[0][0] + fc[0][2] / 2) / w, ("left", "centre", "right")) if fc else None,
            "text": text, "measured": _now()}


# ------------------------------------------------------------------------------------------ the set's summary
def _wmed(vals, ws) -> float | None:
    from .thumbnail import _wmed as wm
    v = wm(vals, ws)
    return None if v is None else round(float(v), 3 if v < 1 else 1)


def main_colours(rows: list[tuple[int, list]], k: int = 6) -> list[dict]:
    """rows = (n, palette) per picture -> the set's ~k main colours: each picture's colours (share >= 8 %) clustered in
    Lab; per colour the pictures that use it and its mean share in them. Most-used first."""
    import cv2
    from .colour import from_lab, to_lab
    ent = [(n, c, s) for n, pal in rows for c, s in (pal or []) if s >= 0.08]
    if not ent:
        return []
    rgb = np.array([[int(c[i:i + 2], 16) for i in (1, 3, 5)] for _, c, _ in ent], np.uint8)
    lab = to_lab(rgb).reshape(-1, 3).astype(np.float32)
    k = max(1, min(k, len({c for _, c, _ in ent})))
    reps = [max(1, int(round(s * 10))) for _, _, s in ent]          # a colour's share counts, kmeans has no weights
    pts = np.repeat(lab, reps, axis=0)
    owner = np.repeat(np.arange(len(ent)), reps)
    cv2.setRNGSeed(1)
    _, lbl, cen = cv2.kmeans(pts, k, None, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5), 3,
                             cv2.KMEANS_PP_CENTERS)
    lbl = lbl.ravel()
    groups: list[list] = []                                  # [Lab centre, entry indexes, points]: near ones merged
    for j in sorted(range(k), key=lambda j: -int((lbl == j).sum())):
        idx = set(owner[lbl == j].tolist())
        if not idx:
            continue
        cnt = int((lbl == j).sum())
        g = next((g for g in groups if float(np.linalg.norm(g[0] - cen[j])) < MERGE_DE), None)
        if g:
            g[0] = (g[0] * g[2] + cen[j] * cnt) / (g[2] + cnt)
            g[1] |= idx
            g[2] += cnt
        else:
            groups.append([cen[j].astype(np.float32), idx, cnt])
    out = []
    for cl, idx, _ in groups:
        c = (from_lab(cl.reshape(1, 1, 3)).reshape(3) * 255).round().astype(int)
        hexs = "#%02x%02x%02x" % tuple(int(x) for x in c)
        pics = {ent[i][0] for i in idx}
        out.append({"hex": hexs, "word": colour_word(hexs), "pictures": len(pics),
                    "share": round(float(np.mean([ent[i][2] for i in idx])), 3), "examples": sorted(pics)[:6]})
    return sorted(out, key=lambda x: (-x["pictures"], -x["share"]))


def _most(vals: list) -> dict | None:
    vals = [v for v in vals if v]
    if not vals:
        return None
    v, c = Counter(vals).most_common(1)[0]
    return {"most": v, "count": c, "of": len(vals)}


def summarise(items: list[dict]) -> dict:
    rows = [it for it in items if it.get("measures")]
    out = {"n": len(items), "measured": len(rows), "made": _now()}
    if not rows:
        return out
    M = [it["measures"] for it in rows]
    ws = [max(0.25, it.get("outperformer") or 1.0) for it in rows]
    for k in ("brightness", "saturation", "colourfulness", "contrast"):
        out[k] = _wmed([m.get(k) for m in M], ws)
    out["weights"] = sum(1 for it in rows if it.get("outperformer") is not None)   # pictures with views / followers
    known = [m for m in M if m.get("faces") is not None]
    if known:
        with_f = [(m, w) for m, w in zip(M, ws) if m.get("faces")]
        out["faces"] = {"with": len(with_f), "known": len(known),
                        "share": _wmed([m["face_share"] for m, _ in with_f], [w for _, w in with_f]),
                        "side": _most([m.get("face_side") for m, _ in with_f])}
    else:
        out["faces"] = None                                 # no face detector: not measured
    with_t = [(m["text"], w) for m, w in zip(M, ws) if (m.get("text") or {}).get("found")]
    out["text"] = {"with": len(with_t), "of": len(rows),
                   "letter_share": _wmed([t["letter_share"] for t, _ in with_t], [w for _, w in with_t]),
                   "area": _wmed([t["area"] for t, _ in with_t], [w for _, w in with_t]),
                   "where": _most([t["where"] for t, _ in with_t])}
    out["orientation"] = {"horizontal": sum(1 for m in M if m["aspect"] >= 1.05),
                          "vertical": sum(1 for m in M if m["aspect"] <= 0.95),
                          "square": sum(1 for m in M if 0.95 < m["aspect"] < 1.05)}
    out["colours"] = main_colours([(it["n"], it["measures"].get("palette")) for it in rows])
    best = sorted((it for it in rows if it.get("outperformer") is not None), key=lambda it: -it["outperformer"])[:3]
    out["best"] = [{"n": it["n"], "title": it.get("title"), "outperformer": it["outperformer"],
                    "views": it.get("views")} for it in best]
    return out


# ------------------------------------------------------------------------------------------ public: read
def load_style(name: str) -> dict | None:
    """Claude's style.json for the set (shape in the module's docstring), or None."""
    try:
        s = read_json(set_dir(name) / "style.json")
    except (OSError, ValueError):
        return None
    return s if isinstance(s, dict) else None


def sheets_of(name: str) -> list[Path]:
    d = set_dir(name)
    return sorted(d.glob("sheet_*.png"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 0)) if d.exists() else []


def list_sets() -> list[dict]:
    """Every set, newest change first: name, label, count, measured, has_style, updated, cover (lab-relative)."""
    out = []
    root = Path(ROOT)
    for d in root.iterdir() if root.exists() else []:
        if not d.is_dir():
            continue
        try:
            S = read_json(d / "set.json")
        except (OSError, ValueError):
            continue
        if not isinstance(S, dict):
            continue
        items = S.get("items") or []
        out.append({"name": d.name, "label": S.get("label") or d.name, "count": len(items),
                    "measured": sum(1 for it in items if it.get("measures")),
                    "has_style": (d / "style.json").is_file(), "updated": S.get("updated"),
                    "source": (S.get("source") or {}).get("kind"),
                    "channel_total": (S.get("channel") or {}).get("total"),
                    "cover": rel(d / items[0]["file"]) if items else None})
    return sorted(out, key=lambda s: s["updated"] or "", reverse=True)


def get_set(name: str) -> dict:
    """set.json + "style" (Claude's, or None) + "sheets" + "dir" + every item's "path" (all lab-relative)."""
    S = _need(name)
    d = set_dir(name)
    for it in S["items"]:
        it["path"] = rel(d / it["file"])
    cat = S.pop("channel", None)
    if cat:                                             # the listing's numbers (More from the channel)
        ids = {e["id"] for e in cat.get("entries") or []}
        inset = len({it.get("id") for it in S["items"]} & ids)
        S["channel"] = {"url": cat.get("url"), "who": cat.get("who"), "total": cat.get("total"), "in_set": inset,
                        "left": (cat.get("total") or 0) - inset, "listed": cat.get("listed")}
    elif (S.get("source") or {}).get("kind") in ("channel", "playlist") and (S.get("source") or {}).get("url"):
        src = S["source"]                               # a set from before the listing was kept: more() lists it first
        S["channel"] = {"url": src["url"], "who": src.get("channel"), "total": None, "in_set": len(S["items"]),
                        "left": None, "listed": None}
    return {**S, "name": d.name, "dir": rel(d), "style": load_style(name), "sheets": [rel(p) for p in sheets_of(name)]}


# ------------------------------------------------------------------------------------------ public: measure + sheets
def measure(name: str, force: bool = False) -> dict:
    """Every picture measured (re-used while unchanged), then the summary -> set.json.
    Returns {"measured", "reused", "failed": [[n, why]], "seconds", "summary"}."""
    from .thumbnail import face_model
    t0 = time.time()
    with _lock(name):
        S = _need(name)
        d = set_dir(name)
        det = face_model() is not None
        new = reused = 0
        failed = []
        for it in S["items"]:
            p = d / it["file"]
            if not p.is_file():
                failed.append([it["n"], "the picture file is missing"])
                continue
            m = it.get("measures") or {}
            if not force and m.get("sig") == _sig(p) and (m.get("face_detector") or not det):
                reused += 1
                continue
            try:
                it["measures"] = measure_picture(p)
                new += 1
            except Exception as e:                          # noqa: BLE001 - one bad picture never stops the set
                failed.append([it["n"], f"could not read the picture ({type(e).__name__}: {e})"])
        S["summary"] = summarise(S["items"])
        _save(name, S)
    return {"measured": new, "reused": reused, "failed": failed, "seconds": round(time.time() - t0, 2),
            "summary": S["summary"]}


def _fit(d: ImageDraw.ImageDraw, text: str, font, width: int) -> str:
    text = " ".join(str(text or "").split())
    if d.textlength(text, font=font) <= width:
        return text
    while text and d.textlength(text + "…", font=font) > width:
        text = text[:-1]
    return text.rstrip() + "…"


def make_sheets(name: str) -> list[str]:
    """The contact sheets: 15 pictures per sheet (5 x 3), the caption under each picture ("#n", views, views /
    followers, the title cut short). Old extra sheets are removed. Returns their lab-relative paths."""
    from .media import fonts
    with _lock(name):
        S = _need(name)
        d = set_dir(name)
        items = S["items"]
        asp = [(it.get("measures") or {}).get("aspect") for it in items]
        asp = [a for a in asp if a]
        tw, th = (240, 427) if asp and float(np.median(asp)) < 0.9 else (400, 225)
        F = fonts(1.1)
        cap, head, gap = 46, 44, 8
        pages = [items[i:i + PER_SHEET] for i in range(0, len(items), PER_SHEET)]
        out = []
        for pi, page in enumerate(pages, 1):
            rows = (len(page) + COLS - 1) // COLS
            W = COLS * (tw + gap) + gap
            sheet = Image.new("RGB", (W, head + rows * (th + cap + gap) + gap), (16, 16, 16))
            dr = ImageDraw.Draw(sheet)
            dr.text((gap, 8), _fit(dr, f"{S.get('label') or d.name}  ·  sheet {pi} of {len(pages)}  ·  #{page[0]['n']}"
                                       f"-#{page[-1]['n']} of {len(items)}  ·  'x' = views / the channel's followers",
                                   F["title"], W - 2 * gap), fill=(235, 235, 235), font=F["title"])
            for i, it in enumerate(page):
                x, y = gap + (i % COLS) * (tw + gap), head + (i // COLS) * (th + cap + gap)
                cell = Image.new("RGB", (tw, th), (34, 34, 34))
                try:
                    with Image.open(d / it["file"]) as im:
                        t = im.convert("RGB")
                    t.thumbnail((tw, th), Image.LANCZOS)
                    cell.paste(t, ((tw - t.width) // 2, (th - t.height) // 2))
                except (OSError, ValueError):
                    ImageDraw.Draw(cell).text((10, th // 2 - 8), "picture unreadable", fill=(255, 90, 90), font=F["body"])
                sheet.paste(cell, (x, y))
                tag = f"#{it['n']}"
                dr.text((x, y + th + 3), tag, fill=(255, 196, 0), font=F["mono_b"])
                tx = x + int(dr.textlength(tag + " ", font=F["mono_b"]))
                bits = ([f"{num(it.get('views'))} views"] if it.get("views") is not None else []) + (
                    [f"{it['outperformer']}x"] if it.get("outperformer") is not None else [])
                if bits:
                    dr.text((tx, y + th + 3), "  ·  ".join(bits), fill=(200, 200, 200), font=F["mono"])
                dr.text((x, y + th + 22), _fit(dr, it.get("title") or it.get("id") or "", F["body"], tw),
                        fill=(235, 235, 235), font=F["body"])
            p = d / f"sheet_{pi}.png"
            sheet.save(p)
            out.append(rel(p))
        for p in sheets_of(name):                            # fewer pictures than before: the extra sheets go
            if int(re.sub(r"\D", "", p.stem) or 0) > len(pages):
                p.unlink()
    return out


# ------------------------------------------------------------------------------------------ public: add pictures
def _add_bytes(name: str, S: dict, row: dict, data: bytes, ext: str) -> dict | None:
    """One picture into the set (None = the same picture is already in it)."""
    sha = hashlib.sha1(data).hexdigest()[:16]
    if any(it.get("sha1") == sha for it in S["items"]):
        return None
    n = len(S["items"]) + 1
    stem = safe_name(str(row.get("id") or "picture"))[:40]
    d = set_dir(name)
    (d / "img").mkdir(parents=True, exist_ok=True)
    f = f"img/{n:02d}_{stem}{ext}"
    tmp = d / (f + ".part")
    tmp.write_bytes(data)
    tmp.replace(d / f)
    it = {"n": n, "file": f, "id": row.get("id"), "title": row.get("title"), "url": row.get("url"),
          "views": row.get("views"), "followers": row.get("followers"),
          "outperformer": _outperformer(row.get("views"), row.get("followers")),
          "upload_date": row.get("upload_date"), "date_approx": bool(row.get("date_approx")),
          "duration": row.get("duration"), "from": row.get("from"), "sha1": sha, "measures": None}
    S["items"].append(it)
    return it


def _finish(name: str, added: list, skipped: list, failed: list, log) -> dict:
    d = set_dir(name)
    res = {"name": d.name, "dir": rel(d), "added": len(added), "skipped": skipped, "failed": failed}
    if added:
        log(f"measuring {len(added)} new picture(s) ...")
        m = measure(name)
        res["measure"] = {k: m[k] for k in ("measured", "reused", "failed", "seconds")}
        log(f"measured {m['measured']} (re-used {m['reused']}) in {m['seconds']} s"
            + "".join(f"\n  #{n}: {why}" for n, why in m["failed"]))
    sheets = make_sheets(name)
    res["sheets"] = sheets
    for s in sheets:
        log(f"sheet: {s}")
    log(f"{len(added)} added" + (f", {len(skipped)} already in the set" if skipped else "")
        + (f", {len(failed)} failed" if failed else ""))
    return res


def add_files(name: str, paths: list, log=print, label: str | None = None) -> dict:
    """The user's own pictures (.jpg .jpeg .png .webp; a folder = the pictures in it, not its sub-folders) COPIED into
    the set - the originals are only read. Title = the file's name without its extension."""
    files = []
    for p in map(Path, paths):
        if p.is_dir():
            files += sorted(q for q in p.iterdir() if q.is_file() and q.suffix.lower() in IMG_EXT)
        elif p.is_file():
            files.append(p)
        else:
            log(f"skipped {p}: no such file or folder")
    if not files:
        raise ValueError("no pictures found (.jpg .jpeg .png .webp)")
    added, skipped, failed = [], [], []
    with _lock(name):
        S = _load(name) or _new(name, label, {"kind": "files"})
        d = set_dir(name).resolve()
        for p in files:
            if d in p.resolve().parents:
                skipped.append(p.name)                       # already one of the set's own files
                continue
            if p.suffix.lower() not in IMG_EXT:
                failed.append([p.name, "not a .jpg / .jpeg / .png / .webp picture"])
                log(f"skipped {p.name}: not a .jpg / .jpeg / .png / .webp picture")
                continue
            try:
                data = p.read_bytes()                        # read only; the original is never touched
                with Image.open(p) as im:
                    im.verify()
            except Exception as e:                           # noqa: BLE001
                failed.append([p.name, f"not a readable picture ({type(e).__name__})"])
                log(f"skipped {p.name}: not a readable picture")
                continue
            ext = _ext_of(data) or (".jpg" if p.suffix.lower() == ".jpeg" else p.suffix.lower())
            it = _add_bytes(name, S, {"id": p.stem, "title": p.stem, "from": "file"}, data, ext)
            if it is None:
                skipped.append(p.name)
                log(f"skipped {p.name}: the same picture is already in the set")
                continue
            added.append(it)
            log(f"#{it['n']} {p.name}")
        _save(name, S)
    return _finish(name, added, skipped, failed, log)


# ------------------------------------------------------------------------------------------ network: yt-dlp + pictures
HINTS = [
    (("private",), "this video or playlist is private"),
    (("not a bot", "sign in to confirm", "http error 429", "too many requests"),
     "the site is blocking requests from this PC for a while (a bot check) - try again later"),
    (("unsupported url",), "yt-dlp does not know this kind of link - paste a channel, playlist or video link"),
    (("does not exist", "http error 404", "not found", "this channel does not have", "no videos"),
     "nothing found at this link - check it in the browser"),
    (("video unavailable", "has been removed", "not available in your country", "no longer available"),
     "the video was removed or is not available here"),
    (("getaddrinfo", "timed out", "connection", "network is unreachable", "unable to download webpage"),
     "no connection to the site - check the internet"),
    (("unable to extract", "javascript runtime", "js runtime", "latest version"),
     "yt-dlp is probably out of date for this site - Settings > Programs > Update yt-dlp"),
]


def why(text: str) -> str:
    """yt-dlp's error in plain words (the hint; its own last line when nothing known matches)."""
    lines = [ln.strip() for ln in str(text or "").splitlines() if ln.strip()]
    err = next((ln for ln in reversed(lines) if ln.startswith("ERROR")), lines[-1] if lines else "")
    low = err.lower()
    h = next((h for words, h in HINTS if any(w in low for w in words)), None)
    return h or ("yt-dlp failed: " + re.sub(r"^ERROR:\s*", "", err)[:200] if err else "yt-dlp failed without a message")


_YTDLP: dict = {}


def ytdlp_cmd() -> list[str]:
    """The user's yt-dlp (it is not in the venv: Settings' path, PATH or tools\\bin) + Deno when it is installed but
    not on PATH yet (as the app's downloads do)."""
    from .app import system
    exe = system.find("yt-dlp")
    if not exe:
        raise ValueError("yt-dlp not found - " + system.HOW["yt-dlp"])
    if exe not in _YTDLP:
        cmd = [exe, "--no-warnings"]
        deno = system.find("deno")
        v = re.search(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", system.version(exe) or "") if deno and not shutil.which("deno") else None
        if v and tuple(map(int, v.groups())) >= (2025, 11, 12):
            cmd += ["--js-runtimes", f"deno:{deno}"]
        _YTDLP[exe] = cmd
    return list(_YTDLP[exe])


def ytdlp_json(args: list[str], timeout: float = 180) -> dict:
    try:
        r = subprocess.run(ytdlp_cmd() + args, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        raise ValueError(f"the site did not answer in {int(timeout)} s - try again later") from None
    if r.returncode:
        raise ValueError(why(r.stderr or r.stdout))
    try:
        return json.loads(r.stdout)
    except ValueError:
        raise ValueError("yt-dlp gave no answer for this link") from None


def listing_url(url: str) -> tuple[str, str | None]:
    """A bare YouTube channel link lists its tabs, not videos: -> its Videos tab (and a note saying so)."""
    u = url.strip()
    m = re.match(r"^https?://(?:www\.|m\.)?youtube\.com/(@[^/?#]+|channel/[^/?#]+|c/[^/?#]+|user/[^/?#]+)/?(?:[?#].*)?$", u)
    if m:
        return (f"https://www.youtube.com/{m.group(1)}/videos",
                "a channel link: listing its Videos tab (put /shorts at the end of the link for its Shorts)")
    return u, None


def _yt_id(e: dict) -> str | None:
    vid = str(e.get("id") or "")
    u = str(e.get("url") or e.get("webpage_url") or "")
    yt = (e.get("ie_key") or e.get("extractor_key") or "").lower().startswith("youtube") or "youtu" in u
    return vid if yt and YT_ID.match(vid) else None


def pic_urls(e: dict, shorts: bool = False) -> list[str]:
    """Where an entry's thumbnail can be fetched, best first: YouTube = maxresdefault (1280x720), the entry's own
    biggest (hq720, no bands), then sddefault / hqdefault (4:3 with bands); a Short = its own (vertical) first; other
    sites = yt-dlp's pick, then the biggest offered."""
    own = [t["url"] for t in sorted((t for t in (e.get("thumbnails") or []) if t.get("url")),
                                    key=lambda t: -(t.get("width") or 0) * (t.get("height") or 0))]
    vid = _yt_id(e)
    if vid:
        shorts = shorts or "/shorts/" in str(e.get("url") or e.get("webpage_url") or "")
        yt = [f"https://i.ytimg.com/vi/{vid}/{k}.jpg" for k in ("maxresdefault", "sddefault", "hqdefault")]
        urls = own[:3] + yt if shorts else yt[:1] + [u for u in own if "vi_webp" not in u][:2] + yt[1:]
    else:
        urls = ([e["thumbnail"]] if e.get("thumbnail") else []) + own[:4]
    return list(dict.fromkeys(urls))


def download(urls: list[str]) -> tuple[bytes, str]:
    """The first of urls that answers with a picture -> (bytes, extension). Raises ValueError in plain words."""
    import urllib.error
    import urllib.request
    last = "no picture address"
    for u in urls:
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=20) as r:
                data = r.read(20_000_000)
        except urllib.error.HTTPError as e:
            last = f"the site answered {e.code}"
            continue
        except (urllib.error.URLError, OSError) as e:
            last = f"no connection ({getattr(e, 'reason', e)})"
            continue
        ext = _ext_of(data)
        if ext:
            return data, ext
        last = "the answer was not a picture"
    raise ValueError(last)


def _entries(info: dict, n: int) -> list[dict]:
    """yt-dlp's --flat-playlist JSON -> its first n videos (a channel's tabs are no videos)."""
    if "entries" not in info:
        return [info] if info.get("id") else []          # one video's link
    out, tabs = [], 0
    for e in info.get("entries") or []:
        if not isinstance(e, dict):
            continue
        if e.get("_type") == "playlist" or (e.get("ie_key") or "").endswith("Tab"):
            tabs += 1
            continue
        if e.get("id"):
            out.append(e)
        if len(out) >= n:
            break
    if not out and tabs:
        raise ValueError("this link lists a channel's tabs, not its videos - put /videos or /shorts at its end")
    return out


def _row(e: dict, followers, kind: str, shorts: bool = False) -> dict:
    vid = _yt_id(e)
    url = e.get("webpage_url") or e.get("url") or (f"https://www.youtube.com/watch?v={vid}" if vid else None)
    views = e.get("view_count") if isinstance(e.get("view_count"), (int, float)) else None
    fol = e.get("channel_follower_count") if isinstance(e.get("channel_follower_count"), (int, float)) else followers
    return {"id": e.get("id"), "title": e.get("title"), "url": url, "views": views, "followers": fol,
            "upload_date": _date(e.get("upload_date")) or _ts_date(e.get("timestamp")),
            "date_approx": bool(e.get("_approx")) or (not _date(e.get("upload_date")) and bool(e.get("timestamp"))),
            "duration": e.get("duration") if isinstance(e.get("duration"), (int, float)) else None,
            "from": kind, "urls": pic_urls(e, shorts)}


def _add_rows(name: str, rows: list[dict], source: dict, label: str | None, log) -> dict:
    added, skipped, failed = [], [], []
    with _lock(name):
        S = _load(name) or _new(name, label, source)
        have = {it.get("id") for it in S["items"] if it.get("id")}
        todo = []
        for r in rows:
            if r["id"] in have:
                skipped.append(r["id"])
                log(f"skipped {r.get('title') or r['id']}: already in the set")
            else:
                have.add(r["id"])
                todo.append(r)
        if todo:
            log(f"downloading {len(todo)} thumbnail(s) ...")

        def get(r):
            try:
                return download(r["urls"]), None
            except ValueError as e:
                return None, str(e)
        with ThreadPoolExecutor(THREADS) as ex:
            got = list(ex.map(get, todo))
        for r, (pic, err) in zip(todo, got):
            title = (r.get("title") or r["id"] or "")[:70]
            if pic is None:
                failed.append([r["id"], err])
                log(f"skipped {title}: no picture ({err})")
                continue
            it = _add_bytes(name, S, r, *pic)
            if it is None:
                skipped.append(r["id"])
                log(f"skipped {title}: the same picture is already in the set")
                continue
            added.append(it)
            nums = (f" - {num(it['views'])} views" if it["views"] is not None else "") + (
                f" ({it['outperformer']}x the followers)" if it["outperformer"] is not None else "")
            log(f"#{it['n']} {title}{nums}")
        if S["items"] or added:
            _save(name, S)
    if not S["items"]:
        raise ValueError("no thumbnail could be saved: " + "; ".join(f"{i}: {w}" for i, w in failed[:3]))
    return _finish(name, added, skipped, failed, log)


ORDERS = {"newest": "the newest", "views": "the most viewed"}
LISTING_MAX_AGE_S = 24 * 3600           # a channel's listing older than a day is asked for again before a batch


def _listing(url: str, log) -> tuple[dict, list[dict]]:
    """The WHOLE channel tab / playlist, flat (titles, views, ids - no video): measured 2026-10-15 at 3.5 s for 246
    videos (Clavero) and 10.3 s for 804 (MrBeast)."""
    log(f"listing every video of {url} (only titles and numbers - no video is downloaded) ...")
    # approximate_date: YouTube's "3 weeks ago" as a date for every video, at the same speed (measured 2026-10-15:
    # 246 videos dated in 3.8 s vs 3.6 s without) - shown as approximate
    info = ytdlp_json(["--flat-playlist", "-J", "--extractor-args", "youtubetab:approximate_date", url], timeout=300)
    entries = _entries(info, 100_000)
    if not entries:
        raise ValueError("nothing found at this link - is it a channel, a playlist or a channel's Videos / Shorts tab?")
    return info, entries


def _catalogue(info: dict, entries: list[dict], url: str) -> dict:
    """What set.json keeps of the listing: per video id, title, views, length, its place in the listing (0 = newest)
    and, off YouTube, its picture addresses (YouTube's are made from the id)."""
    followers = info.get("channel_follower_count") if isinstance(info.get("channel_follower_count"), (int, float)) else None
    rows = []
    for i, e in enumerate(entries):
        r = {"id": e.get("id"), "title": (e.get("title") or "")[:200], "pos": i,
             "views": e.get("view_count") if isinstance(e.get("view_count"), (int, float)) else None,
             "duration": e.get("duration") if isinstance(e.get("duration"), (int, float)) else None,
             "date": _date(e.get("upload_date")) or _ts_date(e.get("timestamp")),
             "approx": not _date(e.get("upload_date")),
             "url": e.get("webpage_url") or e.get("url")}
        if not _yt_id(e):
            r["pics"] = pic_urls(e)[:4]
        rows.append(r)
    return {"url": url, "who": info.get("channel") or info.get("uploader"), "followers": followers,
            "listed": _now(), "listed_t": time.time(), "total": len(rows), "entries": rows}


def _ts_date(ts) -> str | None:
    return time.strftime("%Y-%m-%d", time.gmtime(ts)) if isinstance(ts, (int, float)) and ts > 0 else None


def _backfill(S: dict, cat: dict) -> int:
    """The set's pictures from this listing get its newest numbers: views (and views ÷ followers), the date and the
    length when they had none. Returns how many changed."""
    by = {e["id"]: e for e in cat.get("entries") or [] if e.get("id")}
    fol = cat.get("followers")
    changed = 0
    for it in S["items"]:
        e = by.get(it.get("id"))
        if not e:
            continue
        before = (it.get("views"), it.get("upload_date"), it.get("duration"))
        if e.get("views") is not None:
            it["views"] = e["views"]
        if fol:
            it["followers"] = fol
        it["outperformer"] = _outperformer(it.get("views"), it.get("followers"))
        if not it.get("upload_date") and e.get("date"):
            it["upload_date"], it["date_approx"] = e["date"], bool(e.get("approx"))
        if it.get("duration") is None and e.get("duration") is not None:
            it["duration"] = e["duration"]
        it["pos"] = e.get("pos")                       # its place in the listing (0 = the newest): sorts exactly
        changed += before != (it.get("views"), it.get("upload_date"), it.get("duration"))
    return changed


def _pick(cat: dict, have: set, n: int, order: str) -> list[dict]:
    pool = [e for e in cat["entries"] if e.get("id") and e["id"] not in have]
    if order == "views":
        pool.sort(key=lambda e: (-(e["views"] if e.get("views") is not None else -1), e["pos"]))
    return pool[:n]


def _cat_rows(cat: dict, picked: list[dict], kind: str) -> list[dict]:
    shorts = str(cat.get("url") or "").rstrip("/").endswith("/shorts")
    out = []
    for e in picked:
        ent = {"id": e["id"], "title": e.get("title"), "url": e.get("url"), "view_count": e.get("views"),
               "ie_key": "Youtube" if YT_ID.match(str(e["id"])) and "pics" not in e else None,
               "upload_date": (e.get("date") or "").replace("-", "") or None, "duration": e.get("duration"),
               "_approx": bool(e.get("approx"))}
        if "pics" in e:
            ent["thumbnails"] = [{"url": u} for u in e["pics"]]
        out.append(_row(ent, cat.get("followers"), kind, shorts))
    return out


def fetch(name: str, url: str, n: int = 15, label: str | None = None, log=print, order: str = "newest") -> dict:
    """A channel / playlist / channel tab link: EVERY video listed by yt-dlp (seconds, no video downloaded) and kept in
    set.json "channel"; the first n - the newest or the most viewed - get their thumbnails, titles, views and the
    channel's followers into the set; then measured + sheets. More later with more() (the user, 2026-10-15: "why stop
    at the newest? ... I could choose to download other 20/30 batch").
    Returns {"name", "dir", "added", "skipped", "failed", "measure", "sheets", "channel"}."""
    url = str(url or "").strip()
    if not re.match(r"https?://\S+$", url):
        raise ValueError("paste a full link starting with https:// (a channel, a playlist or a channel's Videos tab)")
    if order not in ORDERS:
        raise ValueError(f"order: {' or '.join(ORDERS)}")
    n = max(1, min(int(n or 15), 200))
    url, note = listing_url(url)
    if note:
        log(note)
    info, entries = _listing(url, log)
    cat = _catalogue(info, entries, url)
    kind = "playlist" if re.search(r"[?&]list=|/playlist\b", url) else "channel"
    log(f"found {cat['total']} video(s)" + (f" from {cat['who']}" if cat["who"] else "")
        + (f" ({cat['followers']:,} followers)" if cat["followers"] else " (followers not given)")
        + f" - taking {ORDERS[order]} {min(n, cat['total'])} now")
    have = {it.get("id") for it in (_load(name) or {}).get("items", [])}
    rows = _cat_rows(cat, _pick(cat, have, n, order), kind)
    source = {"kind": kind, "url": url, "channel": cat["who"], "followers": cat["followers"], "fetched": _now()}
    res = _add_rows(name, rows, source, label or cat["who"] or str(name), log) if rows else _finish(name, [], [], [], log)
    with _lock(name):
        S = _need(name)
        S["channel"] = cat
        _backfill(S, cat)
        _save(name, S)
    left = cat["total"] - len({it.get("id") for it in S["items"]} & {e["id"] for e in cat["entries"]})
    exact_dates(name, log)
    log(f"{len(S['items'])} in the set, {left} more on the {kind} (thumbsets.py more {S['name']} --n 20)")
    return {**res, "channel": {"total": cat["total"], "left": left}}


def more(name: str, n: int = 20, order: str = "newest", refresh: bool = False, log=print) -> dict:
    """The next n of the set's channel / playlist that are not in the set yet - the newest or the most viewed - from
    the listing set.json keeps (asked for again when it is older than a day, or refresh=True)."""
    if order not in ORDERS:
        raise ValueError(f"order: {' or '.join(ORDERS)}")
    n = max(1, min(int(n or 20), 200))
    S = _need(name)
    cat = S.get("channel")
    if not cat:
        url = (S.get("source") or {}).get("url")
        if (S.get("source") or {}).get("kind") not in ("channel", "playlist") or not url:
            raise ValueError("this set was made from single links or your own pictures - there is no channel to take more "
                             "from (Add more > a channel link starts one)")
        cat = None
    if refresh or not cat or time.time() - float(cat.get("listed_t") or 0) > LISTING_MAX_AGE_S:
        url = (cat or {}).get("url") or S["source"]["url"]
        info, entries = _listing(url, log)
        cat = _catalogue(info, entries, url)
    kind = (S.get("source") or {}).get("kind") or "channel"
    have = {it.get("id") for it in S["items"] if it.get("id")}
    picked = _pick(cat, have, n, order)
    log(f"{cat['total']} video(s) on the {kind}, {len(have & {e['id'] for e in cat['entries']})} in the set - "
        f"taking {ORDERS[order]} {len(picked)} of the rest")
    res = _add_rows(name, _cat_rows(cat, picked, kind), S.get("source") or {}, S.get("label"), log) if picked \
        else _finish(name, [], [], [], log)
    with _lock(name):
        S = _need(name)
        S["channel"] = cat
        _backfill(S, cat)
        _save(name, S)
    left = cat["total"] - len({it.get("id") for it in S["items"]} & {e["id"] for e in cat["entries"]})
    exact_dates(name, log)
    log(f"{len(S['items'])} in the set, {left} more on the {kind}")
    return {**res, "channel": {"total": cat["total"], "left": left}}


DATE_THREADS = 3                         # yt-dlp per video, 3 at a time (10 videos in 9.7 s; one by one 22.1 s)


def _video_date(vid: str) -> str | None:
    """One YouTube video's exact upload date (YYYYMMDD) - its own page through yt-dlp, nothing downloaded; None when
    YouTube does not answer (it asks yt-dlp to sign in now and then)."""
    try:
        r = subprocess.run(ytdlp_cmd() + ["--skip-download", "--no-playlist", "--print", "%(upload_date)s",
                                          f"https://www.youtube.com/watch?v={vid}"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return None
    d = (r.stdout or "").strip().splitlines()
    return d[-1] if d and re.fullmatch(r"\d{8}", d[-1]) else None


def exact_dates(name: str, log=print) -> int:
    """The set's YouTube videos whose date is only approximate (or missing) get their exact upload date. -> how many."""
    S = _need(name)
    todo = [it for it in S["items"] if it.get("id") and YT_ID.match(str(it["id"]))
            and (not it.get("upload_date") or it.get("date_approx"))]
    if not todo:
        return 0
    log(f"exact dates for {len(todo)} video(s) - about {max(1, round(len(todo) * 1.0))} s ...")
    with ThreadPoolExecutor(DATE_THREADS) as ex:
        got = dict(zip([it["id"] for it in todo], ex.map(lambda it: _video_date(it["id"]), todo)))
    done = 0
    with _lock(name):
        S = _need(name)
        for it in S["items"]:
            d = _date(got.get(it.get("id")))
            if d:
                it["upload_date"], it["date_approx"] = d, False
                done += 1
        if done:
            _save(name, S)
    log(f"{done} exact date(s)" + (f"; {len(todo) - done} stay approximate (YouTube did not say)" if done < len(todo) else ""))
    return done


def refresh(name: str, log=print) -> dict:
    """The set's channel / playlist listed again (seconds, nothing downloaded): every picture of it gets the newest
    views, views ÷ followers, its (approximate) date and its length. -> {"changed", "total"}."""
    S = _need(name)
    url = (S.get("channel") or {}).get("url") or (S.get("source") or {}).get("url")
    if (S.get("source") or {}).get("kind") not in ("channel", "playlist") or not url:
        raise ValueError("this set was made from single links or your own pictures - no channel to ask")
    info, entries = _listing(url, log)
    cat = _catalogue(info, entries, url)
    with _lock(name):
        S = _need(name)
        S["channel"] = cat
        changed = _backfill(S, cat)
        _save(name, S)
    log(f"{changed} of {len(S['items'])} picture(s) got newer numbers; the channel has {cat['total']} video(s)")
    exact = exact_dates(name, log)
    return {"changed": changed, "total": cat["total"], "exact": exact}


def add_links(name: str, urls: list[str], log=print, label: str | None = None) -> dict:
    """Single video links: yt-dlp -J --skip-download --no-playlist each (3 at a time) -> title, views, the channel's
    followers, the thumbnail. YouTube asking yt-dlp to sign in: the picture is taken from YouTube's fixed address and
    the numbers stay unknown (said so)."""
    urls = [str(u).strip() for u in urls if str(u or "").strip()]
    if not urls:
        raise ValueError("paste at least one video link")
    bad = [u for u in urls if not re.match(r"https?://\S+$", u)]
    if bad:
        raise ValueError(f"not a full link: {bad[0][:80]} (it should start with https://)")
    log(f"asking for {len(urls)} video(s)' thumbnail and numbers (no video is downloaded) ...")

    def info_of(u):
        try:
            return ytdlp_json(["-J", "--skip-download", "--no-playlist", u]), None
        except ValueError as e:
            m = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", u)
            if m:
                return {"id": m.group(1), "webpage_url": u, "extractor_key": "Youtube",
                        "_note": f"{e} - the picture taken from YouTube's address, title and numbers unknown"}, None
            return None, str(e)
    with ThreadPoolExecutor(3) as ex:
        got = list(ex.map(info_of, urls))
    rows, failed = [], []
    for u, (info, err) in zip(urls, got):
        if info is None:
            failed.append([u, err])
            log(f"skipped {u}: {err}")
            continue
        if info.get("_note"):
            log(f"{u}: {info['_note']}")
        r = _row(info, None, "link")
        r["url"] = info.get("webpage_url") or u
        r["title"] = r["title"] or info.get("id")
        rows.append(r)
    if not rows:
        raise ValueError("no link worked: " + "; ".join(w for _, w in failed[:3]))
    res = _add_rows(name, rows, {"kind": "links"}, label, log)
    res["failed"] = failed + res["failed"]
    return res


# ------------------------------------------------------------------------------------------ public: change a set
def remove_item(name: str, n: int) -> dict:
    """Picture #n out of the set (its lab-made copy deleted); the later ones move up a number (their files renamed,
    their measures kept). Returns {"removed", "count"}."""
    with _lock(name):
        S = _need(name)
        d = set_dir(name)
        items = S["items"]
        i = next((k for k, it in enumerate(items) if it.get("n") == int(n)), None)
        if i is None:
            raise ValueError(f"the set has no picture #{n}")
        img = (d / "img").resolve()
        p = (d / items[i]["file"]).resolve()
        if img not in p.parents:
            raise ValueError(f"refusing to delete {p}: not one of the set's own pictures")
        p.unlink(missing_ok=True)
        del items[i]
        for it in items[i:]:
            old = d / it["file"]
            it["n"] -= 1
            rest = Path(it["file"]).name.split("_", 1)[-1]
            it["file"] = f"img/{it['n']:02d}_{rest}"
            new = d / it["file"]
            m = it.get("measures") or {}
            same = old.is_file() and m.get("sig") == _sig(old)
            if old.is_file():
                old.replace(new)
            if same:
                m["sig"] = _sig(new)                         # the same picture: its measures stay valid
        S["summary"] = summarise(items)
        _save(name, S)
        make_sheets(name)
    return {"removed": int(n), "count": len(items)}


# ------------------------------------------------------------------------------------------ in words
def _pct(x) -> str:
    return "-" if x is None else f"{round(x * 100)} %"


def item_line(it: dict) -> str:
    m = it.get("measures") or {}
    head = f"#{it['n']:<3} " + (f"{num(it.get('views'))} views" if it.get("views") is not None else "views ?") + (
        f" {it['outperformer']}x" if it.get("outperformer") is not None else "")
    if not m:
        return f"{head} | not measured | {it.get('title') or it.get('id')}"
    f = ("faces not measured" if m.get("faces") is None else "no face" if not m["faces"] else
         f"{m['faces']} face(s), biggest {_pct(m['face_share'])} of the height, {m['face_side']}")
    t = m.get("text") or {}
    tx = (f"text {t['where']} (letters {_pct(t['letter_share'])}, covers {_pct(t['area'])})" if t.get("found")
          else "no text found")
    return (f"{head} | {m['size'][0]}x{m['size'][1]} | brightness {m['brightness']:.0f} sat {m['saturation']:.0f} % "
            f"colourful {m['colourfulness']:.0f} contrast {m['contrast']:.0f} | {f} | {tx} | "
            f"{' '.join(c for c, _ in m.get('palette') or [])} | {(it.get('title') or it.get('id') or '')[:60]}")


def summary_lines(name: str) -> list[str]:
    """The set in a few plain lines (for Claude and Claude's memory): the look, faces, text, colours, the best ones,
    Claude's style when there is one."""
    S = _need(name)
    s = S.get("summary") or {}
    label = S.get("label") or set_name(name)
    src = S.get("source") or {}
    n = len(S["items"])
    if not s.get("measured"):
        return [f"Thumbnail set {set_name(name)} ({label}): {n} picture(s), not measured yet"]
    L = [f"Thumbnail set {set_name(name)} ({label}): {n} thumbnail(s)" + (f" from {src['url']}" if src.get("url") else "")
         + f", measured {s.get('made', '')}" + (f"; {s['weights']} with views / followers (they weigh more)"
                                                  if s.get("weights") else "") + "."]
    L.append(f"Look (medians): brightness {s['brightness']:.0f}/100, saturation {s['saturation']:.0f} %, "
             f"colourfulness {s['colourfulness']:.0f}, contrast {s['contrast']:.0f}.")
    fc = s.get("faces")
    if fc is None:
        L.append("Faces: not measured (no face detector on this PC).")
    else:
        side = fc.get("side")
        L.append(f"Faces in {fc['with']} of {fc['known']}" + (
            f", the biggest {_pct(fc['share'])} of the height" if fc.get("share") is not None else "") + (
            f", mostly {side['most']} ({side['count']} of {side['of']})" if side else "") + ".")
    t = s.get("text") or {}
    w = t.get("where")
    L.append(f"Text (an estimate) in {t.get('with', 0)} of {t.get('of', 0)}" + (
        f", letters {_pct(t['letter_share'])} of the height, covering {_pct(t['area'])}" if t.get("with") else "") + (
        f", mostly {w['most']} ({w['count']} of {w['of']})" if w else "") + ".")
    if s.get("colours"):
        L.append("Main colours: " + ", ".join(f"{c['hex']} {c['word']} ({c['pictures']} pictures)"
                                             for c in s["colours"][:6]) + ".")
    if s.get("best"):
        L.append("Best (views / followers): " + "; ".join(f"#{b['n']} \"{(b['title'] or '')[:50]}\" {b['outperformer']}x"
                                                          for b in s["best"]) + ".")
    st = load_style(name)
    if st:
        f = st.get("font") or {}
        wd = st.get("words") or {}
        L.append(f"Claude's style ({st.get('date', '?')}): {st.get('summary', '')}".strip()
                 + (f" Font: {f['style']}" + (f" (closest: {', '.join(f.get('closest') or [])}"
                                              + (")" if f.get("sure") else ", a guess)") if f.get("closest") else "")
                    + "." if f.get("style") else "")
                 + (f" Words: median {wd['median']}, max {wd.get('max')}, {wd.get('case', '')} case." if wd.get("median")
                    else "")
                 + (" Structures: " + ", ".join(f"{x['name']} ({x.get('count')})" for x in st["structures"][:3]) + "."
                    if st.get("structures") else ""))
    return L


# ------------------------------------------------------------------------------------------ self-check
def selfcheck(verbose: bool = True) -> dict:
    """Known answers with no network and no real data: synthetic pictures made here in a temp root - a bright yellow
    one with big black letters top left, a dark blue one with white letters bottom right, a grey one without text -
    added (the originals unchanged), measured, sheets; re-measure re-uses; the outperformer weighs; remove_item
    renumbers; a folder of 14 more = 2 sheets; load_style; the link helpers on canned yt-dlp answers.
    Returns {"passed", "checks", "failed", "seconds"}."""
    import tempfile
    from PIL import ImageFont
    from .thumbnail import face_model
    global ROOT
    t_start = time.time()
    bad, n_ok = [], 0

    def ok(cond, what):
        nonlocal n_ok
        n_ok += 1
        if not cond:
            bad.append(what)
        if verbose:
            print(("PASS  " if cond else "FAIL  ") + what)

    def font(px):
        for f in ("arialbd.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"):
            try:
                return ImageFont.truetype(f, px)
            except OSError:
                continue
        return ImageFont.load_default(px)

    def picture(bg, text=None, fg=(0, 0, 0), xy=(0, 0), px=130, size=(1280, 720), grad=False):
        im = Image.new("RGB", size, bg)
        d = ImageDraw.Draw(im)
        if grad:
            for y in range(size[1]):
                c = tuple(int(v * (0.75 + 0.5 * y / size[1])) for v in bg)
                d.line((0, y, size[0], y), fill=tuple(min(255, x) for x in c))
        if text:
            d.text(xy, text, fill=fg, font=font(px))
        return im

    old_root, quiet = ROOT, (lambda *a, **k: None)
    tmp = Path(tempfile.mkdtemp(prefix="ml_thumbsets_"))
    try:
        ROOT = tmp / "thumbs"
        src = tmp / "src"
        src.mkdir()
        picture((255, 210, 0), "WOW BIG", (0, 0, 0), (40, 40)).save(src / "yellow_text.png")
        picture((20, 30, 90), "NEW WAY", (255, 255, 255), (1280 - 600, 720 - 170), 110).save(src / "blue_text.jpg",
                                                                                              quality=95)
        picture((128, 128, 128), grad=True).save(src / "grey_plain.png")
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in src.iterdir()}
        r = add_files("Demo set", [src / "yellow_text.png", src / "blue_text.jpg", src / "grey_plain.png"], log=quiet)
        after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in src.iterdir()}
        ok(r["added"] == 3 and r["name"] == "Demo_set", f"3 pictures added to set Demo_set (got {r['added']}, {r['name']})")
        ok(before == after, "the original files are unchanged and still there (copied, not moved)")
        S = get_set("Demo set")
        it = {i["title"]: i for i in S["items"]}
        files_ok = all((ROOT / "Demo_set" / i["file"]).is_file() for i in S["items"])
        ok(files_ok and [i["file"] for i in S["items"]][0] == "img/01_yellow_text.png", "copies in img\\NN_<name>.<ext>")
        y, b, g = (it[k]["measures"] for k in ("yellow_text", "blue_text", "grey_plain"))
        ok(y["brightness"] > g["brightness"] > b["brightness"],
           f"brightness: yellow {y['brightness']} > grey {g['brightness']} > dark blue {b['brightness']}")
        ok(y["text"]["found"] and b["text"]["found"] and not g["text"]["found"],
           "text found on the two lettered pictures, none on the grey one")
        ok(y["text"].get("where") == "top left" and b["text"].get("where") == "bottom right",
           f"text position: yellow {y['text'].get('where')}, blue {b['text'].get('where')}")
        ok(0.08 <= (y["text"].get("letter_share") or 0) <= 0.2,
           f"letter height share ~0.13 for 130 px Arial Bold on 720 px (got {y['text'].get('letter_share')})")
        det = face_model() is not None
        ok(all((m["faces"] is None) == (not det) for m in (y, b, g)) and (not det or all(m["faces"] == 0 for m in (y, b, g))),
           "faces: " + ("0 on the synthetic pictures (detector on)" if det else "not measured (no detector) - None, not 0"))
        s = S["summary"]
        ok(s["n"] == 3 and s["measured"] == 3 and s["text"]["with"] == 2 and s["text"]["of"] == 3,
           f"summary: 3 pictures, text in {s['text']['with']} of {s['text']['of']}")
        ok((s["faces"] is None) == (not det), "summary faces: " + ("counted" if det else "None = not measured"))
        words = [c["word"] for c in s["colours"]]
        ok(any("yellow" in w for w in words) and any("blue" in w for w in words) and all(c["pictures"] >= 1 for c in s["colours"])
           and words.count("grey") <= 1, f"main colours named, near ones merged: {', '.join(words)}")
        sh = ROOT / "Demo_set" / "sheet_1.png"
        sw = 0
        if sh.is_file():
            with Image.open(sh) as im:
                sw = im.size[0]
        ok(sw == COLS * (400 + 8) + 8 and len(S["sheets"]) == 1, "sheet_1.png made, 5 tiles wide")
        m2 = measure("Demo set")
        ok(m2["measured"] == 0 and m2["reused"] == 3, f"re-measure re-uses (measured {m2['measured']}, re-used {m2['reused']})")
        raw = json.loads((ROOT / "Demo_set" / "set.json").read_text(encoding="utf-8"))
        raw["items"][0].update(views=500, followers=100, outperformer=5.0)
        (ROOT / "Demo_set" / "set.json").write_text(json.dumps(raw), encoding="utf-8")
        s3 = measure("Demo set")["summary"]
        ok(s3["brightness"] == y["brightness"] and s3["best"][0]["n"] == 1,
           f"an outperformer (5x) weighs most: median brightness {s3['brightness']} = #1's {y['brightness']} "
           f"(unweighted = grey's {g['brightness']})")
        rm = remove_item("Demo set", 2)
        S = get_set("Demo set")
        d = ROOT / "Demo_set"
        ok(rm["count"] == 2 and [i["n"] for i in S["items"]] == [1, 2] and S["items"][1]["title"] == "grey_plain"
           and (d / "img" / "02_grey_plain.png").is_file() and not (d / "img" / "03_grey_plain.png").exists()
           and not (d / "img" / "02_blue_text.jpg").exists(), "remove-item 2: the grey picture is #2 now, file renamed")
        ok(measure("Demo set")["measured"] == 0, "its measures carried over (nothing re-measured)")
        try:
            remove_item("Demo set", 9)
            ok(False, "remove-item of a missing number refused")
        except ValueError:
            ok(True, "remove-item of a missing number refused")
        more = tmp / "more"
        more.mkdir()
        for k in range(14):
            picture(tuple(int(v) for v in (np.array(colorsys.hsv_to_rgb(k / 14, 0.8, 0.9)) * 255)),
                    size=(320, 180)).save(more / f"m{k:02d}.png")
        (more / "notes.txt").write_text("not a picture")
        r2 = add_files("Demo set", [more], log=quiet)
        r3 = add_files("Demo set", [src / "yellow_text.png"], log=quiet)
        S = get_set("Demo set")
        ok(r2["added"] == 14 and r3["added"] == 0 and len(S["items"]) == 16, "a folder adds its 14 pictures (the .txt "
           "ignored); the same picture again is skipped")
        ok(len(S["sheets"]) == 2 and (d / "sheet_2.png").is_file(), "16 pictures = 2 sheets (15 per sheet)")
        L = list_sets()
        ok(len(L) == 1 and L[0]["count"] == 16 and L[0]["measured"] == 16 and L[0]["cover"].endswith("01_yellow_text.png")
           and not L[0]["has_style"], "list_sets: count, measured, cover, no style yet")
        ok(load_style("Demo set") is None, "load_style: None before Claude writes one")
        st = {"set": "Demo_set", "date": "2026-10-15", "summary": "Yellow and blue, big letters.",
              "patterns": [{"id": "P1", "kind": "text", "what": "2 words, upper case", "how_many": "2 of 3",
                            "examples": [1, 2]}],
              "font": {"style": "heavy sans", "closest": ["Anton"], "sure": False}, "words": {"median": 2, "max": 2,
                                                                                              "case": "upper"}}
        (d / "style.json").write_text(json.dumps(st), encoding="utf-8")
        ok((load_style("Demo set") or {}).get("patterns", [{}])[0].get("id") == "P1" and get_set("Demo set")["style"]
           and list_sets()[0]["has_style"], "load_style: the dict after style.json is written")
        sl = summary_lines("Demo set")
        ok(len(sl) >= 5 and any(x.startswith("Text") for x in sl) and any("Claude's style" in x for x in sl),
           f"summary_lines: {len(sl)} lines with the text and Claude's style")
        # the whole channel listed once, then batches (no network: a canned listing, pictures made here)
        canned = {"channel": "Canned", "channel_follower_count": 1000, "entries": [
            {"id": f"vid{i:08d}", "ie_key": "Youtube", "title": f"video {i}", "view_count": v, "url": f"https://youtu.be/vid{i:08d}",
             "timestamp": 1791676800 - i * 86400 * 30, "duration": 600 + i}
            for i, v in enumerate([50, 900, 10, 700, 300, 5])]}
        real_json, real_dl, real_vd = globals()["ytdlp_json"], globals()["download"], globals()["_video_date"]
        globals()["_video_date"] = lambda vid: None                     # YouTube silent: the dates stay approximate
        more_ = globals()["more"]                 # this function has a local "more" (a folder)
        buf = __import__("io").BytesIO()
        picture((30, 90, 200), "AB", (255, 255, 255), (40, 40)).save(buf, "JPEG")
        jpg = buf.getvalue()
        globals()["ytdlp_json"] = lambda args, timeout=180: canned
        cnt = iter(range(1000))
        globals()["download"] = lambda urls: (jpg + bytes([next(cnt) % 250]), ".jpg")   # a new file each (a byte after the end)
        try:
            r1 = fetch("canned", "https://www.youtube.com/@canned", n=2, log=lambda *_: None)
            S1 = get_set("canned")
            ok([it["id"] for it in S1["items"]] == ["vid00000000", "vid00000001"] and r1["channel"] == {"total": 6, "left": 4},
               f"the whole channel listed once, the newest 2 taken (got {[it['id'] for it in S1['items']]}, {r1['channel']})")
            ok(S1["channel"]["total"] == 6 and S1["channel"]["in_set"] == 2 and "entries" not in S1["channel"],
               "the page gets the channel's numbers, not its listing")
            it0 = S1["items"][0]
            ok(it0.get("upload_date") == "2026-10-11" and it0.get("date_approx") is True and it0.get("duration") == 600
               and it0.get("pos") == 0,
               f"each picture: its approximate date and its length (got {it0.get('upload_date')}, {it0.get('duration')})")
            r2 = more_("canned", n=2, order="views", log=lambda *_: None)
            ok([it["id"] for it in get_set("canned")["items"]][2:] == ["vid00000003", "vid00000004"] and r2["channel"]["left"] == 2,
               "more: the 2 most viewed NOT in the set yet (700, 300 - not 900 again)")
            r3 = more_("canned", n=10, log=lambda *_: None)
            ok(len(get_set("canned")["items"]) == 6 and r3["channel"]["left"] == 0, "more: the rest, never one twice")
            canned["entries"][0]["view_count"] = 5000
            rr = refresh("canned", log=lambda *_: None)
            it0 = get_set("canned")["items"][0]
            ok(rr["changed"] >= 1 and it0["views"] == 5000 and it0["outperformer"] == 5.0,
               f"refresh: the newest views and views / followers, nothing downloaded (got {it0['views']}, {it0['outperformer']})")
            globals()["_video_date"] = lambda vid: "20241206" if vid == "vid00000000" else None
            nx = exact_dates("canned", log=lambda *_: None)
            its = get_set("canned")["items"]
            ok(nx == 1 and its[0]["upload_date"] == "2024-12-06" and its[0]["date_approx"] is False
               and its[1]["date_approx"] is True, "exact dates where YouTube answers, approximate where it does not")
            try:
                more_("Demo set", n=5, log=lambda *_: None)
                ok(False, "a set of your own pictures has no channel to take more from")
            except (ValueError, FileNotFoundError):
                ok(True, "a set of your own pictures has no channel to take more from")
        finally:
            globals()["ytdlp_json"], globals()["download"], globals()["_video_date"] = real_json, real_dl, real_vd

        # the link helpers on canned yt-dlp answers (no network)
        ok(listing_url("https://www.youtube.com/@MrBeast")[0] == "https://www.youtube.com/@MrBeast/videos"
           and listing_url("https://www.youtube.com/playlist?list=PL123")[1] is None
           and listing_url("https://youtube.com/@MrBeast/shorts")[1] is None, "a bare channel link -> its Videos tab")
        flat = {"_type": "playlist", "channel": "Chan", "channel_follower_count": 1000, "entries": [
            {"_type": "url", "ie_key": "Youtube", "id": "abcdefghijk", "title": "One", "view_count": 2500,
             "url": "https://www.youtube.com/watch?v=abcdefghijk",
             "thumbnails": [{"url": "https://i.ytimg.com/vi/abcdefghijk/hq720.jpg?x=1", "width": 720, "height": 404}]},
            {"_type": "url", "ie_key": "Youtube", "id": "bcdefghijkl", "title": "Two", "view_count": None,
             "url": "https://www.youtube.com/watch?v=bcdefghijkl"},
            {"_type": "url", "ie_key": "Youtube", "id": "cdefghijklm", "title": "Three"}]}
        rows = [_row(e, 1000, "channel") for e in _entries(flat, 2)]
        ok(len(rows) == 2 and rows[0]["views"] == 2500 and rows[1]["views"] is None
           and _outperformer(rows[0]["views"], rows[0]["followers"]) == 2.5,
           "a flat listing -> the first N videos, views, views / followers 2.5")
        ok(rows[0]["urls"][0].endswith("/abcdefghijk/maxresdefault.jpg") and "hq720" in rows[0]["urls"][1]
           and rows[0]["urls"][-1].endswith("hqdefault.jpg"), "YouTube pictures: maxresdefault, hq720, then the 4:3 ones")
        try:
            _entries({"entries": [{"_type": "url", "ie_key": "YoutubeTab", "id": "UCx", "url": "x/videos"}]}, 5)
            ok(False, "a list of tabs is refused in words")
        except ValueError as e:
            ok("/videos" in str(e), "a list of tabs is refused in words")
        ok("private" in why("ERROR: [youtube] abc: Private video. Sign in if you've been granted access")
           and "blocking" in why("ERROR: Sign in to confirm you're not a bot"), "yt-dlp errors in plain words")
        bars = np.zeros((480, 640, 3), np.uint8)
        bars[60:420] = (200, 120, 40)
        inner, cut = trim_bars(bars)
        ok(cut and inner.shape[0] == 360, f"YouTube's 4:3 bands cut off (360 rows kept, got {inner.shape[0]})")
        ok(colour_word("#ffcc00") == "yellow" and colour_word("#14205a").endswith("blue") and colour_word("#000000")
           == "black" and colour_word("#ffffff") == "white", "colour words")
    except Exception as e:                                   # noqa: BLE001 - a crash is a failed check, said so
        import traceback
        ok(False, f"crashed: {type(e).__name__}: {e}\n{traceback.format_exc()}")
    finally:
        ROOT = old_root
        shutil.rmtree(tmp, ignore_errors=True)
    secs = round(time.time() - t_start, 2)
    if verbose:
        print(f"{n_ok - len(bad)}/{n_ok} checks pass ({secs} s)")
    return {"passed": not bad, "checks": n_ok, "failed": bad, "seconds": secs}
