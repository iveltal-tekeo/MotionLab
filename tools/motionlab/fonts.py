"""The font library (0.4.6): the lab's fonts\\ folder = free fonts (SIL Open Font License 1.1 / Apache 2.0) that ship with
MotionLab, so a graphic, a caption or a thumbnail renders the same on every PC (before 0.4.6 the graphics offered five
Windows fonts - another PC, or the Mac version, could draw them differently). Standard library only: the app and
overlay_settings import it.

    fonts\\<family-dir>\\<files>.ttf + LICENSE.txt     one folder per family (the user's own folder, 2026-10-15: 25
                                                    families checked - licence file + the font's own licence field)
    fonts\\fonts.css                                 @font-face for every family (pages and HTML outside a graphic)
    library\\fonts\\<family-dir>\\<files>.ttf           the user's own fonts (a bought font's licence is theirs): private -
                                                    library\\ never goes to GitHub; listed first ("Your fonts")

A graphic's font setting is an enum whose id is "font" or ends in "_font". HyperFrames checks a render's values against
the options its index.html declares (--strict-variables), so the options are WRITTEN into the declaration: sync() puts
the library's families (then the Windows fonts graphics used before) into the examples and thumbnail designs, and
overlay_settings.set_values() upgrades a project graphic's list when a library font is picked there. Before HyperFrames
renders or snapshots a graphic, ensure() copies the families its font settings name into <graphic>\\assets\\fonts\\
(with their licence files), writes assets\\fonts\\fonts.css and links it from index.html - nothing outside the graphic
is loaded, nothing is installed in Windows.

    .venv\\Scripts\\python tools\\fonts.py list | sync | check <graphic folder> | selfcheck
"""
from __future__ import annotations

import json
import re
import shutil
import struct
from pathlib import Path

from .util import LAB

ROOT = LAB / "fonts"
LOCAL = LAB / "library" / "fonts"                   # the user's own fonts, this PC only
EXAMPLES = LAB / "tools" / "overlays" / "examples"
THUMB_TEMPLATES = LAB / "tools" / "overlays" / "thumbnails"
MOTION = LAB / "tools" / "overlays" / "motion"             # 0.5.0: the Motion Graphics library
SYSTEM = ("Arial Black", "Impact", "Bahnschrift", "Segoe UI", "Verdana", "Georgia")    # Windows only - not bundled, kept for old graphics
LINK = '<link rel="stylesheet" href="assets/fonts/fonts.css">'
FONT_EXT = (".ttf", ".otf")
# what each family is good for (the 0.4.6 choices, 2026-10-15); a family not listed = "other"
GROUPS = {
    "heavy condensed": ("Anton", "Bebas Neue", "Oswald", "Barlow Condensed", "League Gothic", "Big Shoulders Display"),
    "heavy wide": ("Archivo Black", "Montserrat", "Poppins", "Inter", "League Spartan", "Unbounded", "Kanit"),
    "friendly / rounded": ("Nunito", "Rubik", "Fredoka", "Baloo 2"),
    "playful display": ("Bangers", "Luckiest Guy", "Lilita One", "Bagel Fat One", "Titan One", "Chewy"),
    "handwritten / marker": ("Permanent Marker", "Pacifico", "Caveat Brush", "Rock Salt"),
    "serif display": ("DM Serif Display", "Playfair Display", "Fraunces", "Instrument Serif", "Abril Fatface"),
    "clean text": ("Lato", "Raleway", "Roboto", "Hanken Grotesk", "Lexend", "Outfit"),
    "tech / mono": ("Space Grotesk", "Space Mono", "JetBrains Mono", "Orbitron"),
}
_WEIGHT_WORDS = {"thin": 100, "extralight": 200, "light": 300, "regular": 400, "medium": 500, "semibold": 600,
                 "bold": 700, "extrabold": 800, "black": 900, "heavy": 900}


# ------------------------------------------------------------------------------------------------- reading a font
def _tables(data: bytes) -> dict[bytes, tuple[int, int]]:
    n = struct.unpack(">H", data[4:6])[0]
    out = {}
    for i in range(n):
        tag, _cs, off, ln = struct.unpack(">4sIII", data[12 + 16 * i: 28 + 16 * i])
        out[tag] = (off, ln)
    return out


def _name(data: bytes, t: dict, ids=(16, 1)) -> str | None:
    if b"name" not in t:
        return None
    off, _ = t[b"name"]
    _fmt, count, soff = struct.unpack(">HHH", data[off:off + 6])
    best: dict = {}
    for i in range(count):
        pid, eid, lid, nid, ln, so = struct.unpack(">HHHHHH", data[off + 6 + 12 * i: off + 18 + 12 * i])
        if nid not in ids:
            continue
        raw = data[off + soff + so: off + soff + so + ln]
        try:
            s = raw.decode("utf-16-be") if pid in (0, 3) else raw.decode("latin-1")
        except UnicodeDecodeError:
            continue
        rank = (ids.index(nid), 0 if (pid == 3 and lid == 0x409) else 1)
        if s and (nid not in best or rank < best[nid][0]):
            best[nid] = (rank, s)
    for nid in ids:
        if nid in best:
            return best[nid][1]
    return None


def read_font(path: Path) -> dict:
    """family, weight (OS/2), italic, variable weight range (fvar 'wght') - from the file itself."""
    data = Path(path).read_bytes()
    t = _tables(data)
    weight, italic = 400, False
    if b"OS/2" in t:
        off, _ = t[b"OS/2"]
        weight = struct.unpack(">H", data[off + 4:off + 6])[0]
        italic = bool(struct.unpack(">H", data[off + 62:off + 64])[0] & 1)
    wrange = None
    if b"fvar" in t:
        off, _ = t[b"fvar"]
        aoff, _r, count, size = struct.unpack(">HHHH", data[off + 4:off + 12])
        for i in range(count):
            a = off + aoff + i * size
            tag, mn, _df, mx = struct.unpack(">4siii", data[a:a + 16])
            if tag == b"wght":
                wrange = (round(mn / 65536), round(mx / 65536))
    stem = Path(path).stem.lower().replace("-", "").replace("_", "")
    italic = italic or "italic" in stem
    return {"file": Path(path).name, "family": _name(data, t), "weight": weight, "italic": italic, "wght": wrange,
            "variable": b"fvar" in t}


def _licence(d: Path) -> tuple[str, str | None]:
    f = next((p for p in sorted(d.iterdir()) if p.is_file() and p.name.upper().startswith(("LICENSE", "LICENCE", "OFL"))),
             None)
    if not f:
        return "no licence file", None
    t = f.read_text(encoding="utf-8", errors="replace").upper()
    kind = ("OFL 1.1" if "SIL OPEN FONT LICENSE" in t and "VERSION 1.1" in t else "OFL" if "SIL OPEN FONT LICENSE" in t
            else "Apache 2.0" if "APACHE LICENSE" in t else "unknown")
    return kind, f.name


_CACHE: dict = {"sig": None, "fams": []}


def families(root: Path | None = None) -> list[dict]:
    """The library: one entry per family folder, ordered by group then name - family, dir, src (its folder), own (the
    user's, library\\fonts), group ("yours" for own fonts), licence, files (weight / italic / variable range), single
    (one upright file = any weight uses it, no fake bold), kb. root = that folder only (tests, the shipped list)."""
    roots = [(Path(root), False)] if root else [(LOCAL, True), (ROOT, False)]
    roots = [(r, own) for r, own in roots if r.is_dir()]
    files = sorted(p for r, _ in roots for p in r.rglob("*") if p.suffix.lower() in FONT_EXT)
    sig = (tuple(str(r) for r, _ in roots), tuple((str(p), p.stat().st_size, p.stat().st_mtime_ns) for p in files))
    if _CACHE["sig"] == sig:
        return _CACHE["fams"]
    out = []
    for d, own in ((d, own) for r, own in roots for d in sorted(p for p in r.iterdir() if p.is_dir())):
        fs = []
        for f in sorted(p for p in d.iterdir() if p.suffix.lower() in FONT_EXT):
            try:
                fs.append(read_font(f))
            except (OSError, struct.error, IndexError):
                continue
        if not fs:
            continue
        fam = next((f["family"] for f in fs if f["family"] and not f["italic"]), fs[0]["family"]) or d.name
        if any(x["family"] == fam for x in out):           # an own font named like a shipped one: the own one wins
            continue
        kind, lic = _licence(d)
        group = "yours" if own else next((g for g, names in GROUPS.items() if fam in names), "other")
        upright = [f for f in fs if not f["italic"]]
        out.append({"family": fam, "dir": d.name, "src": str(d), "own": own, "group": group, "licence": kind,
                    "licence_file": lic, "files": fs, "single": len(upright) == 1 and not upright[0]["variable"],
                    "kb": round(sum((d / f["file"]).stat().st_size for f in fs) / 1024)})
    order = ["yours"] + list(GROUPS) + ["other"]
    out.sort(key=lambda f: (order.index(f["group"]), f["family"].lower()))
    _CACHE.update(sig=sig, fams=out)
    return out


def by_family(name: str, root: Path | None = None) -> dict | None:
    return next((f for f in families(root) if f["family"] == name), None)


def options(root: Path | None = None) -> list[dict]:
    """A font setting's choices: the library (by group), then the Windows fonts graphics used before 0.4.6."""
    return ([{"value": f["family"], "label": f["family"]} for f in families(root)]
            + [{"value": s, "label": f"{s} (Windows only)"} for s in SYSTEM])


def is_font_setting(decl: dict) -> bool:
    return decl.get("type") == "enum" and (decl.get("id") == "font" or str(decl.get("id", "")).endswith("_font"))


# ------------------------------------------------------------------------------------------------- a graphic's fonts
def _face(fam: dict, f: dict) -> str:
    if f["variable"] and f["wght"]:
        w = f"{f['wght'][0]} {f['wght'][1]}"
    elif fam["single"]:
        w = "1 1000"                                    # the one weight there is, for any weight asked: never a fake bold
    else:
        w = str(f["weight"])
    return (f'@font-face{{font-family:"{fam["family"]}";src:url("{fam["dir"]}/{f["file"]}") format("truetype");'
            f'font-weight:{w};font-style:{"italic" if f["italic"] else "normal"};font-display:block}}')


def css(fams: list[dict], base=None) -> str:
    """@font-face lines; base(fam) = the link's start (a graphic: "" = its own assets\\fonts copy; the app: the lab's
    folders)."""
    lines = [_face(fam, f).replace('url("', 'url("' + (base(fam) if base else ""), 1)
             for fam in fams for f in fam["files"]]
    return "/* MotionLab fonts (fonts.css) */\n" + "\n".join(lines) + "\n"


def ensure(folder: Path, values: dict, decl: list[dict], root: Path | None = None, link: bool = True) -> list[str]:
    """The library families this graphic's font settings name -> <folder>\\assets\\fonts\\<dir>\\ (font files + licence,
    copied only when missing or changed; families it no longer uses removed), assets\\fonts\\fonts.css, and a <link>
    to it in index.html when there is none. A Windows font or an unknown name needs nothing. -> the families."""
    folder = Path(folder)
    want = []
    for d in decl:
        if is_font_setting(d):
            fam = by_family(str(values.get(d["id"], d.get("default", ""))), root)
            if fam and fam not in want:
                want.append(fam)
    dst = folder / "assets" / "fonts"
    if not want and not dst.exists():
        return []
    dst.mkdir(parents=True, exist_ok=True)
    keep = {fam["dir"] for fam in want}
    for p in dst.iterdir():                             # lab-made copies only (this folder is MotionLab's)
        if p.is_dir() and p.name not in keep:
            shutil.rmtree(p, ignore_errors=True)
    for fam in want:
        names = [f["file"] for f in fam["files"]] + ([fam["licence_file"]] if fam["licence_file"] else [])
        (dst / fam["dir"]).mkdir(exist_ok=True)
        for n in names:
            s, t = Path(fam["src"]) / n, dst / fam["dir"] / n
            if not t.exists() or t.stat().st_size != s.stat().st_size:
                shutil.copy2(s, t)
    text = css(want)
    c = dst / "fonts.css"
    if not c.exists() or c.read_text(encoding="utf-8") != text:
        c.write_text(text, encoding="utf-8")
    idx = folder / "index.html"
    if link and idx.exists():
        h = idx.read_text(encoding="utf-8")
        if "assets/fonts/fonts.css" not in h:
            m = re.search(r"<head[^>]*>", h, re.I)
            if m:
                idx.write_text(h[:m.end()] + "\n" + LINK + h[m.end():], encoding="utf-8")
    return [f["family"] for f in want]


# ------------------------------------------------------------------------------------------------- the font lists
_FONT_DECL = re.compile(r'(\{\s*"id"\s*:\s*"(?:font|[\w-]+_font)"\s*,\s*"type"\s*:\s*"enum"[^{}]*?"options"\s*:\s*)\[[^\]]*\]', re.S)


def sync_file(index: Path, root: Path | None = None, default: dict | None = None) -> bool:
    """index.html's font settings get the library's options (the declaration's other text stays as it is); default =
    {old: new} to move a Windows default to a bundled family. Returns whether the file changed."""
    p = Path(index)
    h = p.read_text(encoding="utf-8")
    opts = json.dumps(options(root), ensure_ascii=False)
    new = _FONT_DECL.sub(lambda m: m.group(1) + opts, h)
    for old, nw in (default or {}).items():
        new = re.sub(r'("id"\s*:\s*"(?:font|[\w-]+_font)"\s*,\s*"type"\s*:\s*"enum"\s*,\s*"label"\s*:\s*"[^"]*"\s*,\s*'
                     r'"default"\s*:\s*)"' + re.escape(old) + '"', lambda m: m.group(1) + json.dumps(nw), new)
    if LINK not in new and "assets/fonts/fonts.css" not in new:
        m = re.search(r"<head[^>]*>", new, re.I)
        if m:
            new = new[:m.end()] + "\n" + LINK + new[m.end():]
    if new != h:
        p.write_text(new, encoding="utf-8")
        return True
    return False


def sync(root: Path | None = None) -> list[str]:
    """The examples, the thumbnail designs and the motion templates that come with MotionLab: their font settings offer the shipped library
    (never the user's own fonts: these files go to GitHub), their defaults are bundled families (Arial Black ->
    Archivo Black, Impact -> Anton: the closest free ones), they link assets/fonts/fonts.css. -> the files changed."""
    root = root or ROOT
    moved = {"Arial Black": "Archivo Black", "Impact": "Anton"}
    out = []
    for idx in sorted(list(EXAMPLES.glob("*/index.html")) + list(THUMB_TEMPLATES.glob("*/index.html"))
                      + list(MOTION.glob("*/index.html"))):
        if '"id": "font"' in idx.read_text(encoding="utf-8") or "_font\"" in idx.read_text(encoding="utf-8"):
            if sync_file(idx, root, moved):
                out.append(idx.relative_to(LAB).as_posix())
    return out


# ------------------------------------------------------------------------------------------------- self-check
def selfcheck(verbose: bool = True) -> dict:
    """Known answers on a temp library made from two of the real fonts (no network): families read from the files
    (name, weights, the variable range), the licence kind, the options, ensure() copying only what a graphic uses
    (+ licence, css, the <link>; a font changed = the old one removed), a declaration's font list replaced."""
    global ROOT, LOCAL
    import tempfile
    import time
    t0 = time.time()
    bad, n = [], 0

    def ok(c, what):
        nonlocal n
        n += 1
        if not c:
            bad.append(what)
        if verbose:
            print(("PASS  " if c else "FAIL  ") + what)

    lib = families(ROOT)
    ok(len(lib) >= 2 and all(f["licence"] in ("OFL 1.1", "Apache 2.0") for f in lib),
       f"the shipped library: {len(lib)} families, every one OFL 1.1 / Apache 2.0 by its licence file")
    single = next((f for f in lib if f["single"]), None)
    var = next((f for f in lib if any(x["variable"] for x in f["files"])), None)
    ok(single is not None and var is not None, "one-weight and variable families told apart")
    if not (single and var):
        return {"passed": False, "checks": n, "failed": bad, "seconds": round(time.time() - t0, 2)}
    tmp = Path(tempfile.mkdtemp(prefix="ml_fonts_"))
    try:
        root = tmp / "fonts"
        for fam in (single, var):
            shutil.copytree(ROOT / fam["dir"], root / fam["dir"])
        L = families(root)
        ok({f["family"] for f in L} == {single["family"], var["family"]}, "a temp library of two read back")
        vf = next(x for x in by_family(var["family"], root)["files"] if x["variable"])
        ok(vf["wght"] and vf["wght"][0] < vf["wght"][1], f"the variable font's weight range read from fvar ({vf['wght']})")
        ok(options(root)[-1]["value"] == "Georgia" and options(root)[0]["value"] in (single["family"], var["family"]),
           "the options: the library first, the Windows fonts last")
        g = tmp / "graphic"
        g.mkdir()
        (g / "index.html").write_text(
            "<html lang='en' data-composition-variables='[{\"id\": \"font\", \"type\": \"enum\", \"label\": \"Font\", "
            "\"default\": \"Arial Black\", \"options\": [{\"value\": \"Arial Black\", \"label\": \"Arial Black\"}]}]'>"
            "<head><meta charset='utf-8'></head><body></body></html>", encoding="utf-8")
        ok(sync_file(g / "index.html", root, {"Arial Black": single["family"]}), "a declaration's font list replaced")
        h = (g / "index.html").read_text(encoding="utf-8")
        ok(f'"default": "{single["family"]}"' in h and f'"value": "{var["family"]}"' in h and LINK in h,
           "its default moved to a bundled family, the library offered, the css linked")
        decl = [{"id": "font", "type": "enum"}]
        got = ensure(g, {"font": single["family"]}, decl, root)
        files = sorted(p.name for p in (g / "assets" / "fonts").rglob("*") if p.is_file())
        ok(got == [single["family"]] and "fonts.css" in files and single["licence_file"] in files,
           f"ensure: only the family used, its licence, the css (got {files})")
        cssx = (g / "assets" / "fonts" / "fonts.css").read_text(encoding="utf-8")
        ok("font-weight:1 1000" in cssx, "a one-weight family answers every weight (no fake bold)")
        ensure(g, {"font": var["family"]}, decl, root)
        dirs = sorted(p.name for p in (g / "assets" / "fonts").iterdir() if p.is_dir())
        cssx = (g / "assets" / "fonts" / "fonts.css").read_text(encoding="utf-8")
        ok(dirs == [var["dir"]] and f"font-weight:{vf['wght'][0]} {vf['wght'][1]}" in cssx,
           "another font picked: the old copy removed, the variable range in the css")
        ok(ensure(g, {"font": "Impact"}, decl, root) == [] and not any(p.is_dir() for p in (g / "assets" / "fonts").iterdir()),
           "a Windows font: nothing to copy, the old copies removed")
        keep = (ROOT, LOCAL)                               # the user's own fonts beside the shipped ones
        try:
            ROOT, LOCAL = root, tmp / "own"
            shutil.copytree(root / single["dir"], LOCAL / "mine")
            _CACHE.update(sig=None, fams=[])
            L = families()
            ok(L[0]["own"] and L[0]["group"] == "yours" and L[0]["family"] == single["family"] and len(L) == 2
               and Path(L[0]["src"]) == LOCAL / "mine", "an own font: listed first as yours, wins over the shipped copy")
            ensure(g, {"font": single["family"]}, decl)
            ok((g / "assets" / "fonts" / "mine").is_dir(), "a graphic gets a copy of the own font")
            c2 = css(L, base=lambda f: "/files/library/fonts/" if f["own"] else "/files/fonts/")
            ok('url("/files/library/fonts/mine/' in c2 and f'url("/files/fonts/{var["dir"]}/' in c2,
               "the app's css links each family where it lives")
        finally:
            ROOT, LOCAL = keep
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        _CACHE.update(sig=None, fams=[])
    if verbose:
        print(f"{n - len(bad)}/{n} checks pass ({time.time() - t0:.2f} s)")
    return {"passed": not bad, "checks": n, "failed": bad, "seconds": round(time.time() - t0, 2)}
