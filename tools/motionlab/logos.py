"""The logo library (2026-10-16): brand and app logos as SVG that the motion graphics can show - YouTube, TikTok,
Premiere Pro, DaVinci Resolve, Claude, Figma... - drawn sharp at any size and recoloured to a graphic's palette.
Standard library only: the app and overlay.py import it.

    logos\\<id>\\<variant>.svg      one folder per logo (the id = the folder name: youtube, premiere-pro, x...), cleaned
                                  copies of the user's refs\\logos\\ (2026-10-16: 92 logos, 234 files) - that folder is
                                  only read, `logos.py import` makes the library from it again after a logo is added
    logos\\logos.json              the index: name, group, search words, every variant's aspect, the background it
                                  is drawn for, its colours - Claude picks a logo from it without opening an SVG

Variants: color (the brand's own colours), mono (one colour, takes any colour), wordmark (the name written out), and
color-dark / wordmark-dark (the light version for a dark background). Not every logo has every variant (index).

A graphic names a logo by its id, a variant after a slash: "youtube", "youtube/mono", "openai/wordmark".
"brand" (2026-10-26) = My Brand's own logo (brand_entry: its versions as variants, this PC only, never in logos\\).
  - a logo setting = a string setting whose id is "logo" / "logos" or ends in "_logo" / "_logos" (several: "a|b|c");
    its value may also be a picture file in the graphic's assets folder (the user's own logo, "mylogo.png")
  - any text setting may carry ":youtube:" where a letter or an emoji goes (a node, a notification's icon, a badge)
  - code-only uses: overlay.json "logos": ["youtube", ...]
Before HyperFrames renders or snapshots a graphic, ensure() writes <graphic>\\assets\\logos\\logos.js = the logos it
names (every variant of each) + the window.MLLogo helper, and links it from index.html - nothing outside the graphic
is loaded. In the page: MLLogo.el(value, {tint, dark}) -> an inline <svg> (or an <img> for a picture file) filling its
box; MLLogo.fill(box, value, opts) -> a logo setting's logo (or picture) in the box; MLLogo.text(box, text, opts) -> a
text setting: ":youtube:" alone = the logo, anything else = the text (so the letter "X" stays a letter); MLLogo.lead(
":slack: New message") -> ["slack", "New message"] (an icon first, like an emoji); MLLogo.token(text) -> the logo or null;
MLLogo.split("a|b"), .name(v), .aspect(v), .isDark("#101010"). Options: dark = drawn on a dark background (the
-dark variant, or mono in white, when the logo is dark ink); tint = the colour of a mono logo (asked for as "x/mono",
or picked for contrast); mono = the template wants one colour: the mono variant, else a one-colour logo recoloured -
full-colour logos keep their colours. Inline SVG: no loading, ids and classes made unique per drawing (two logos on
one page never share a gradient).

The logos are trademarks of their owners; MotionLab shows them to name their products ("edited in Premiere Pro"), not
to suggest an endorsement (logos\\README.md).

    .venv\\Scripts\\python tools\\logos.py import [<folder>] | list [--group g] | find "<words>" | show <id> |
                                         check <graphic folder> | selfcheck
"""
from __future__ import annotations

import base64
import json
import re
import shutil
import struct
from pathlib import Path

from .util import LAB

ROOT = LAB / "logos"
BRAND_ID = "brand"            # 2026-10-26: My Brand's own logo as a logo of the library - this PC only (brand_entry)
_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".svg": "image/svg+xml"}
SOURCE = LAB / "refs" / "logos"                     # the user's folder (read only)
INDEX = "logos.json"
SCRIPT = '<script src="assets/logos/logos.js"></script>'
ORDER = ("color", "mono", "wordmark", "color-dark", "wordmark-dark")      # the default = the first one a logo has
VARIANT_WORDS = {"color": "its own colours", "mono": "one colour - takes any colour", "wordmark": "the name written out",
                 "color-dark": "its colours, for a dark background", "wordmark-dark": "the name, for a dark background"}
GROUP_WORDS = {"social": "Social and video platforms", "ai": "AI tools", "creative": "Creative apps (edit, design, 3D, audio)",
               "dev": "Code and developer tools", "work": "Work, notes, files, money", "web": "Browsers and systems",
               "other": "Other"}
# the 92 logos of 2026-10-16: the name people write, the group, words people use for them (a logo added later and not
# listed here gets the name from its <title>, else from its folder; group "other")
NAMES = {
    "affinity-photo": ("Affinity Photo", "creative", "photo editor serif"),
    "after-effects": ("After Effects", "creative", "adobe ae motion graphics compositing vfx"),
    "anthropic": ("Anthropic", "ai", "claude company"),
    "apple": ("Apple", "web", "mac macos ios iphone ipad"),
    "audacity": ("Audacity", "creative", "audio recording podcast sound editor"),
    "audition": ("Audition", "creative", "adobe au audio sound podcast"),
    "blender": ("Blender", "creative", "3d modelling render animation"),
    "bluesky": ("Bluesky", "social", "bsky social network"),
    "bytedance": ("ByteDance", "social", "tiktok company capcut"),
    "canva": ("Canva", "creative", "design templates thumbnails"),
    "chrome": ("Chrome", "web", "google browser"),
    "cinema-4d": ("Cinema 4D", "creative", "c4d maxon 3d motion"),
    "claude": ("Claude", "ai", "anthropic assistant chatbot llm"),
    "copilot": ("Copilot", "ai", "microsoft assistant chatbot"),
    "cursor": ("Cursor", "ai", "code editor ai coding"),
    "davinci-resolve": ("DaVinci Resolve", "creative", "resolve blackmagic davinci video editor colour grading"),
    "deepseek": ("DeepSeek", "ai", "chatbot llm"),
    "discord": ("Discord", "social", "community chat server voice"),
    "docker": ("Docker", "dev", "containers devops"),
    "dropbox": ("Dropbox", "work", "files cloud storage"),
    "edge": ("Edge", "web", "microsoft browser"),
    "elevenlabs": ("ElevenLabs", "ai", "voice tts text to speech dubbing audio"),
    "facebook": ("Facebook", "social", "fb meta social network"),
    "figma": ("Figma", "creative", "design ui prototype"),
    "firefox": ("Firefox", "web", "mozilla browser"),
    "flux": ("Flux", "ai", "black forest labs image generator"),
    "framer": ("Framer", "creative", "website builder design no code"),
    "gemini": ("Gemini", "ai", "google bard assistant chatbot llm"),
    "github": ("GitHub", "dev", "git code repository open source"),
    "github-copilot": ("GitHub Copilot", "ai", "copilot code ai coding"),
    "gmail": ("Gmail", "work", "google email mail inbox"),
    "google": ("Google", "web", "search"),
    "google-drive": ("Google Drive", "work", "drive files cloud storage"),
    "grok": ("Grok", "ai", "xai x chatbot llm"),
    "gumroad": ("Gumroad", "work", "creator store sell digital products"),
    "hugging-face": ("Hugging Face", "ai", "huggingface models open source"),
    "ideogram": ("Ideogram", "ai", "image generator text"),
    "illustrator": ("Illustrator", "creative", "adobe vector design"),
    "instagram": ("Instagram", "social", "ig insta reels stories meta"),
    "kick": ("Kick", "social", "live streaming stream"),
    "kimi": ("Kimi", "ai", "moonshot chatbot llm"),
    "kling": ("Kling", "ai", "kuaishou ai video generator"),
    "lightroom": ("Lightroom", "creative", "adobe lr photo editing presets colour"),
    "linkedin": ("LinkedIn", "social", "jobs business professional network"),
    "linux": ("Linux", "web", "tux open source system"),
    "luma": ("Luma", "ai", "dream machine ai video generator"),
    "meta": ("Meta", "social", "facebook instagram company ai"),
    "midjourney": ("Midjourney", "ai", "mj image generator art"),
    "mistral": ("Mistral", "ai", "le chat llm"),
    "nano-banana": ("Nano Banana", "ai", "google gemini image editor generator"),
    "nodejs": ("Node.js", "dev", "node javascript js"),
    "notebooklm": ("NotebookLM", "ai", "google notes research podcast"),
    "notion": ("Notion", "work", "notes docs planner workspace"),
    "npm": ("npm", "dev", "javascript packages node"),
    "obs-studio": ("OBS Studio", "creative", "obs screen recording live streaming"),
    "obsidian": ("Obsidian", "work", "notes markdown second brain"),
    "openai": ("OpenAI", "ai", "chatgpt gpt chatbot llm"),
    "patreon": ("Patreon", "social", "membership creators support"),
    "perplexity": ("Perplexity", "ai", "search answers chatbot"),
    "photoshop": ("Photoshop", "creative", "adobe ps photo editing"),
    "pika": ("Pika", "ai", "ai video generator"),
    "pinterest": ("Pinterest", "social", "pins ideas boards"),
    "premiere-pro": ("Premiere Pro", "creative", "adobe premiere pr video editor editing"),
    "python": ("Python", "dev", "code programming"),
    "qwen": ("Qwen", "ai", "alibaba chatbot llm"),
    "react": ("React", "dev", "javascript ui web"),
    "reddit": ("Reddit", "social", "forum community subreddit"),
    "runway": ("Runway", "ai", "gen ai video generator"),
    "safari": ("Safari", "web", "apple browser"),
    "shopify": ("Shopify", "work", "store shop ecommerce"),
    "slack": ("Slack", "work", "team chat messages"),
    "snapchat": ("Snapchat", "social", "snap stories"),
    "sora": ("Sora", "ai", "openai ai video generator"),
    "spotify": ("Spotify", "social", "music streaming podcast songs"),
    "stability-ai": ("Stability AI", "ai", "stable diffusion image generator"),
    "stripe": ("Stripe", "work", "payments money checkout"),
    "suno": ("Suno", "ai", "ai music song generator"),
    "telegram": ("Telegram", "social", "chat messages channel"),
    "threads": ("Threads", "social", "meta instagram posts"),
    "tiktok": ("TikTok", "social", "tik tok short video fyp"),
    "twitch": ("Twitch", "social", "live streaming stream gaming"),
    "unity": ("Unity", "creative", "game engine 3d"),
    "unreal-engine": ("Unreal Engine", "creative", "ue5 unreal epic game engine 3d"),
    "vercel": ("Vercel", "dev", "hosting nextjs deploy"),
    "vscode": ("VS Code", "dev", "visual studio code editor microsoft"),
    "whatsapp": ("WhatsApp", "social", "chat messages meta"),
    "windows": ("Windows", "web", "microsoft pc"),
    "windsurf": ("Windsurf", "ai", "codeium code editor ai coding"),
    "x": ("X", "social", "twitter tweet posts"),
    "youtube": ("YouTube", "social", "yt video channel subscribe shorts"),
    "youtube-music": ("YouTube Music", "social", "yt music songs streaming"),
    "zoom": ("Zoom", "work", "video call meeting"),
}
ON_FIX = {"kimi/color": "dark"}        # a white mark with a coloured dot: its colours alone don't say (checked by eye)
_NAMED = {"black": "#000000", "white": "#ffffff", "red": "#ff0000", "blue": "#0000ff", "green": "#008000",
          "yellow": "#ffff00", "gray": "#808080", "grey": "#808080", "orange": "#ffa500"}
_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_BAD = [(re.compile(p, re.I), w) for p, w in (
    (r"<script", "a script"), (r"\son[a-z]+\s*=", "an event handler"), (r"javascript:", "a javascript: link"),
    (r"<!ENTITY|<!DOCTYPE", "a DOCTYPE / entity"), (r"<foreignObject", "HTML inside (foreignObject)"),
    (r"<image\b", "a picture inside (only drawn shapes are kept)"), (r"@import", "a CSS import"),
    (r"(?:xlink:)?href\s*=\s*[\"'](?!#)", "a link outside the file"), (r"url\(\s*(?![\"']?#)", "a CSS url outside the file"))]
_ROOT_KEEP = ("fill", "fill-rule", "clip-rule", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "style")


# ------------------------------------------------------------------------------------------------- cleaning one SVG
def _hex(c: str) -> str | None:
    c = c.strip().lower()
    c = _NAMED.get(c, c)
    if re.fullmatch(r"#[0-9a-f]{3}", c):
        c = "#" + "".join(ch * 2 for ch in c[1:])
    return c if re.fullmatch(r"#[0-9a-f]{6}", c) else None


def _lum(c: str) -> float:
    r, g, b = (int(c[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def clean(text: str) -> tuple[str, dict]:
    """One SVG -> (the cleaned SVG, what it is). ValueError when it carries something a graphic must not load
    (scripts, event handlers, links outside the file, pictures inside). Cleaned = no XML declaration / comments /
    <title> / metadata, a root with a viewBox and no fixed size, every id renamed mlid-N and every CSS class mlc-N
    (MLLogo makes them unique per drawing), named colours as #rrggbb in lower case."""
    t = text.lstrip("﻿")
    for rx, what in _BAD:
        if rx.search(t):
            raise ValueError(f"it has {what}")
    t = re.sub(r"<\?xml[^>]*\?>|<!--.*?-->", "", t, flags=re.S)
    t = re.sub(r"<(title|desc|metadata)\b[^>]*>.*?</\1>|<(title|desc|metadata)\b[^>]*/>", "", t, flags=re.S | re.I)
    m = re.search(r"<svg\b([^>]*)>", t, re.I)
    if not m or "</svg>" not in t.lower():
        raise ValueError("not an SVG")
    attrs = dict((k.lower(), v) for k, v in re.findall(r'([\w:-]+)\s*=\s*"([^"]*)"', m.group(1)))
    attrs.update((k.lower(), v) for k, v in re.findall(r"([\w:-]+)\s*=\s*'([^']*)'", m.group(1)))
    vb = attrs.get("viewbox")
    if not vb:
        w, h = (re.match(r"[\d.]+", attrs.get(k, "") or "") for k in ("width", "height"))
        if not (w and h):
            raise ValueError("no viewBox and no width / height")
        vb = f"0 0 {w.group(0)} {h.group(0)}"
    nums = [float(x) for x in re.split(r"[\s,]+", vb.strip()) if x]
    if len(nums) != 4 or nums[2] <= 0 or nums[3] <= 0:
        raise ValueError(f"a broken viewBox ({vb})")
    body = t[m.end():t.lower().rindex("</svg>")]
    root = ['xmlns="http://www.w3.org/2000/svg"'] + (['xmlns:xlink="http://www.w3.org/1999/xlink"'] if "xlink:" in body else [])
    root += [f'{k}="{(_hex(attrs[k]) or attrs[k]) if k in ("fill", "stroke") else attrs[k]}"' for k in _ROOT_KEEP if k in attrs]
    root.append('viewBox="' + " ".join(f"{x:g}" for x in nums) + '"')
    # ids -> mlid-N, classes -> mlc-N (in the order they first appear)
    ids = list(dict.fromkeys(re.findall(r'\sid\s*=\s*"([^"]+)"', body)))
    idmap = {old: f"mlid-{i}" for i, old in enumerate(ids)}
    if idmap:
        body = re.sub(r'(\sid\s*=\s*")([^"]+)(")', lambda x: x[1] + idmap.get(x[2], x[2]) + x[3], body)
        body = re.sub(r"url\(\s*['\"]?#([^)'\"\s]+)['\"]?\s*\)", lambda x: f"url(#{idmap.get(x[1], x[1])})", body)
        body = re.sub(r'((?:xlink:)?href\s*=\s*")#([^"]+)(")', lambda x: x[1] + "#" + idmap.get(x[2], x[2]) + x[3], body)
    classes = list(dict.fromkeys(c for v in re.findall(r'\sclass\s*=\s*"([^"]*)"', body) for c in v.split()))
    for css in re.findall(r"<style\b[^>]*>(.*?)</style>", body, re.S | re.I):
        classes += [c for c in re.findall(r"\.(-?[_a-zA-Z][\w-]*)", css) if c not in classes]
    cmap = {old: f"mlc-{i}" for i, old in enumerate(dict.fromkeys(classes))}
    if cmap:
        body = re.sub(r'(\sclass\s*=\s*")([^"]*)(")', lambda x: x[1] + " ".join(cmap.get(c, c) for c in x[2].split()) + x[3], body)
        body = re.sub(r"(<style\b[^>]*>)(.*?)(</style>)", lambda x: x[1] + re.sub(
            r"\.(-?[_a-zA-Z][\w-]*)", lambda y: "." + cmap.get(y[1], y[1]), x[2]) + x[3], body, flags=re.S | re.I)
    # colours: named -> hex, all lower case (MLLogo swaps a one-colour logo's colour for a tint by its text)
    body = re.sub(r'((?:fill|stroke|stop-color)\s*=\s*")([^"]+)(")', lambda x: x[1] + (_hex(x[2]) or x[2]) + x[3], body)
    body = re.sub(r"((?:fill|stroke|stop-color)\s*:\s*)([#\w]+)", lambda x: x[1] + (_hex(x[2]) or x[2]), body)
    out = "<svg " + " ".join(root) + ">" + re.sub(r">\s+<", "><", body.strip()) + "</svg>"
    cols = [c for c in (_hex(x) for x in re.findall(r"(?:fill|stroke|stop-color)\s*[=:]\s*\"?([#\w]+)", out)) if c]
    current = "currentcolor" in out.lower()
    # a shape with no fill of its own, under no group or root fill, draws black (clip paths / masks / defs aside)
    drawn = re.sub(r"<(defs|clipPath|mask|linearGradient|radialGradient)\b.*?</\1>", "", out, flags=re.S | re.I)
    unfilled = re.search(r"<(?:path|circle|rect|ellipse|polygon|polyline)\b(?![^>]*\bfill\s*=)(?![^>]*style=\"[^\"]*fill)"
                         r"(?![^>]*\sclass=)[^>]*>", drawn)
    inherited = "fill" in attrs or re.search(r"<g\b[^>]*(?:\bfill\s*=|style=\"[^\"]*fill|\sclass=)", drawn)
    default_black = not current and bool(unfilled) and not inherited
    if default_black:
        cols.append("#000000")
    distinct = list(dict.fromkeys(cols))
    gradient = bool(re.search(r"Gradient", out))
    if current and not distinct:
        on = "any"
    elif distinct:
        L = [_lum(c) for c in cols]
        on = "dark" if min(L) > 0.75 else "light" if max(L) < 0.25 else "any"
    else:
        on = "any"
    counts = {c: cols.count(c) for c in distinct}
    info = {"w": round(nums[2], 3), "h": round(nums[3], 3), "aspect": round(nums[2] / nums[3], 3), "on": on,
            "tint": current and not distinct,
            "one": distinct[0] if len(distinct) == 1 and not gradient and not current and not default_black else None,
            "colors": [c for c in sorted(distinct, key=lambda c: -counts[c]) if 0.04 < _lum(c) < 0.96
                       or len(distinct) == 1][:5],
            "bytes": len(out.encode())}
    return out, info


# ------------------------------------------------------------------------------------------------- the library
def import_folder(src: Path | None = None, root: Path | None = None, verbose: bool = True) -> dict:
    """<src>\\<id>\\<variant>.svg (the user's folder, only read) -> <root>\\<id>\\<variant>.svg cleaned + logos.json.
    A folder name that is not an id (lower case, digits, -) or a file clean() refuses is skipped and said; a logo no
    longer in src leaves the library. -> the index."""
    src, root = Path(src or SOURCE), Path(root or ROOT)
    if not src.is_dir():
        raise SystemExit(f"no folder {src}")
    root.mkdir(parents=True, exist_ok=True)
    logos, skipped = [], []
    for d in sorted(p for p in src.iterdir() if p.is_dir()):
        lid = d.name.lower()
        if not _ID.match(lid):
            skipped.append(f"{d.name}\\: a folder name in lower case, digits and - only (e.g. premiere-pro)")
            continue
        variants, title = {}, None
        for f in sorted(d.glob("*.svg")):
            var = f.stem.lower()
            if not _ID.match(var):
                skipped.append(f"{d.name}\\{f.name}: a file name in lower case, digits and - only")
                continue
            raw = f.read_text(encoding="utf-8", errors="replace")
            title = title or (re.search(r"<title>([^<]+)</title>", raw) or [None, None])[1]
            try:
                svg, info = clean(raw)
            except ValueError as e:
                skipped.append(f"{d.name}\\{f.name}: {e}")
                continue
            (root / lid).mkdir(exist_ok=True)
            out = root / lid / f"{var}.svg"
            if not out.exists() or out.read_text(encoding="utf-8") != svg:
                out.write_text(svg, encoding="utf-8", newline="\n")
            if var.endswith("-dark"):                           # made for a dark background, by its name
                info["on"] = "dark"
            info["on"] = ON_FIX.get(f"{lid}/{var}", info["on"])
            variants[var] = info
        if not variants:
            continue
        for var, info in variants.items():                      # a -dark twin = this one is for a light background
            if info["on"] == "any" and var + "-dark" in variants:
                info["on"] = "light"
        for p in (root / lid).glob("*.svg"):                    # a variant the source no longer has
            if p.stem not in variants:
                p.unlink()
        name, group, words = NAMES.get(lid, (title or lid.replace("-", " ").title(), "other", ""))
        order = sorted(variants, key=lambda v: (ORDER.index(v) if v in ORDER else 99, v))
        logos.append({"id": lid, "name": name, "group": group, "words": words.split(),
                      "default": order[0], "variants": {v: variants[v] for v in order}})
    keep = {lg["id"] for lg in logos}
    for p in root.iterdir():                                    # a logo the source no longer has (lab-made copies)
        if p.is_dir() and p.name not in keep and all(f.suffix == ".svg" for f in p.iterdir()):
            shutil.rmtree(p)
    idx = {"_comment": "Made by tools\\logos.py import from the user's folder (only read). Per variant: w / h / aspect "
                       "of its viewBox, on = the background it is drawn for (light = dark ink, dark = light ink, any), "
                       "tint = takes any colour (mono), one = its single colour (a tint replaces it), colors = its "
                       "main colours, bytes. Trademarks of their owners - see README.md.",
           "source": src.resolve().relative_to(LAB.resolve()).as_posix() if LAB.resolve() in src.resolve().parents else str(src),
           "count": len(logos), "files": sum(len(lg["variants"]) for lg in logos),
           "groups": {g: GROUP_WORDS[g] for g in GROUP_WORDS if any(lg["group"] == g for lg in logos)},
           "logos": logos}
    text = json.dumps(idx, indent=1, ensure_ascii=False) + "\n"
    p = root / INDEX
    if not p.exists() or p.read_text(encoding="utf-8") != text:
        p.write_text(text, encoding="utf-8", newline="\n")
    _CACHE.clear()
    if verbose:
        kb = sum(v["bytes"] for lg in logos for v in lg["variants"].values()) / 1024
        print(f"{len(logos)} logos, {idx['files']} files, {kb:.0f} KB -> {root}")
        for s in skipped:
            print("  skipped " + s)
    idx["skipped"] = skipped
    return idx


_CACHE: dict = {}


def catalog(root: Path | None = None) -> dict:
    """logos.json (cached on its time) - {"logos": []} when the library is missing."""
    p = Path(root or ROOT) / INDEX
    try:
        mt = p.stat().st_mtime_ns
    except OSError:
        return {"count": 0, "logos": [], "groups": {}}
    hit = _CACHE.get(str(p))
    if hit and hit[0] == mt:
        return hit[1]
    d = json.loads(p.read_text(encoding="utf-8"))
    _CACHE[str(p)] = (mt, d)
    return d


def by_id(lid: str, root: Path | None = None) -> dict | None:
    if lid == BRAND_ID:
        return brand_entry()
    return next((lg for lg in catalog(root)["logos"] if lg["id"] == lid), None)


def _pic_size(raw: bytes, ext: str) -> tuple[float, float]:
    """A picture's width and height from its first bytes (PNG, JPEG, WebP, an SVG's viewBox); (1, 1) when unknown."""
    try:
        if raw[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", raw[16:24])
        if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
            k = raw[12:16]
            if k == b"VP8X":
                return 1 + int.from_bytes(raw[24:27], "little"), 1 + int.from_bytes(raw[27:30], "little")
            if k == b"VP8 ":
                w, h = struct.unpack("<HH", raw[26:30])
                return w & 0x3FFF, h & 0x3FFF
            if k == b"VP8L":
                bits = int.from_bytes(raw[21:25], "little")
                return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
        if raw[:2] == b"\xff\xd8":
            i = 2
            while i < len(raw) - 9:
                if raw[i] != 0xFF:
                    i += 1
                    continue
                if raw[i + 1] in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    h, w = struct.unpack(">HH", raw[i + 5:i + 9])
                    return w, h
                i += 2 + int.from_bytes(raw[i + 2:i + 4], "big")
        if ext == ".svg":
            m = re.search(rb'viewBox\s*=\s*"\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)', raw)
            if m:
                return float(m[1]), float(m[2])
    except (struct.error, ValueError, IndexError):
        pass
    return 1, 1


_BCACHE: dict = {}


def brand_entry() -> dict | None:
    """My Brand's logo as a logo of the library (2026-10-26), id BRAND_ID: "brand" in a logo setting, ":brand:" in a
    text. Its versions are the variants - color = the main logo (else the dark version), color-dark = the light one
    (MLLogo takes it on a dark background by itself), dark, icon ("brand/icon") - pictures, never tinted. Read from
    knowledge\\local\\brand.json each time (cached on the files' times); None when My Brand has no logo. This PC only:
    it never goes into logos\\ (the shared library); a graphic's logos.js carries it like any logo."""
    try:
        b = json.loads((LAB / "knowledge" / "local" / "brand.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    idt, name = b.get("identity") or {}, str(b.get("name") or "")
    lv = idt.get("logos") or {}
    files = {"color": idt.get("logo") or lv.get("dark") or lv.get("light") or lv.get("icon"), "color-dark": lv.get("light"),
             "dark": lv.get("dark"), "icon": lv.get("icon")}
    files = {k: str(f) for k, f in files.items()
             if f and re.fullmatch(r"knowledge/local/brand/logo(_\w+)?\.(png|jpe?g|webp|svg)", str(f)) and (LAB / f).is_file()}
    if "color" not in files:
        return None
    key = (name, tuple(sorted((k, f, (LAB / f).stat().st_mtime_ns) for k, f in files.items())))
    if _BCACHE.get("key") == key:
        return _BCACHE["entry"]
    variants = {}
    for k, f in files.items():
        raw = (LAB / f).read_bytes()
        w, h = _pic_size(raw, Path(f).suffix.lower())
        variants[k] = {"w": w, "h": h, "aspect": round(w / h, 3) if h else 1.0, "tint": False, "one": None,
                       "on": {"color-dark": "dark", "dark": "light"}.get(k, "light" if k == "color" and "color-dark" in files
                                                                        else "any"), "file": f}
    entry = {"id": BRAND_ID, "name": name or "My brand", "group": "brand", "default": "color", "variants": variants,
             "words": ["brand", "my", "logo", "mine"] + [w for w in re.findall(r"[a-z0-9]+", name.lower()) if len(w) > 1]}
    _BCACHE.update(key=key, entry=entry)
    return entry


def _brand_svg(v: dict) -> str:
    """A brand logo picture as an <svg> MLLogo draws like any logo: the picture inside as a data: address."""
    f = LAB / v["file"]
    data = base64.b64encode(f.read_bytes()).decode("ascii")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {v["w"]:g} {v["h"]:g}"><image href="data:'
            f'{_MIME.get(f.suffix.lower(), "image/png")};base64,{data}" width="{v["w"]:g}" height="{v["h"]:g}"/></svg>')


def parse(value: str, root: Path | None = None) -> tuple[dict, str | None] | None:
    """"youtube" / "youtube/mono" / ":youtube:" -> (the logo, the variant asked or None); None when it is no logo of
    the library (a variant it does not have counts as none asked)."""
    m = re.fullmatch(r":?([a-z0-9][a-z0-9-]*)(?:/([a-z0-9-]+))?:?", str(value or "").strip().lower())
    lg = by_id(m[1], root) if m else None
    if not lg:
        return None
    return lg, (m[2] if m[2] in lg["variants"] else None)


def find(words: str, n: int = 8, root: Path | None = None) -> list[dict]:
    """The logos that fit the words best: id / name / search words / group, best first (a whole name = most)."""
    W = [w for w in re.findall(r"[a-z0-9.]+", (words or "").lower()) if len(w) > 1 or w == "x"]
    text = " " + " ".join(W) + " "
    out = []
    for lg in catalog(root)["logos"]:
        s = 0.0
        name = lg["name"].lower()
        if f" {name} " in text or f" {lg['id'].replace('-', ' ')} " in text:
            s += 10
        for w in W:
            if w == lg["id"] or w == name.replace(" ", "").replace(".", ""):
                s += 6
            elif w in name.split() or w in lg["id"].split("-"):
                s += 3
            elif w in lg["words"]:
                s += 2
            elif w == lg["group"] or (len(w) >= 4 and any(x.startswith(w) for x in [*name.split(), *lg["words"]])):
                s += 1
        if s:
            out.append((s, lg))
    out.sort(key=lambda x: (-x[0], x[1]["id"]))
    return [{**lg, "score": s} for s, lg in out[:n]]


# ------------------------------------------------------------------------------------------------- a graphic's logos
def is_logo_setting(decl: dict) -> bool:
    i = str(decl.get("id", ""))
    return decl.get("type") == "string" and (i in ("logo", "logos") or i.endswith("_logo") or i.endswith("_logos"))


_TOKEN = re.compile(r":([a-z0-9][a-z0-9-]*)(?:/[a-z0-9-]+)?:", re.I)


def named(values: dict, decl: list[dict], extra=None, root: Path | None = None) -> tuple[list[str], list[str]]:
    """The library logos a graphic's values name (logo settings: "a|b/mono|c"; any text: ":a:"; overlay.json "logos")
    -> (ids, unknown names in logo settings - not a logo and not a picture file)."""
    ids, unknown = [], []
    for d in decl:
        v = values.get(d["id"], d.get("default", ""))
        if d.get("type") != "string" or not isinstance(v, str):
            continue
        if is_logo_setting(d):
            for tok in (x.strip() for x in v.split("|")):
                if not tok:
                    continue
                p = parse(tok, root)
                if p:
                    ids.append(p[0]["id"])
                elif not re.search(r"\.(svg|png|jpe?g|webp|gif)$", tok, re.I):
                    unknown.append(tok)
        for m in _TOKEN.finditer(v):
            p = parse(m[1], root)
            if p:
                ids.append(p[0]["id"])
    for tok in extra or []:
        p = parse(str(tok), root)
        if p:
            ids.append(p[0]["id"])
        else:
            unknown.append(str(tok))
    return list(dict.fromkeys(ids)), list(dict.fromkeys(unknown))


HELPER = r"""(function () {
  window.ML_LOGOS = Object.assign(window.ML_LOGOS || {}, DATA);
  if (window.MLLogo) return;
  let n = 0;
  const parse = v => {
    const m = /^:?([a-z0-9][a-z0-9-]*)(?:\/([a-z0-9-]+))?:?$/.exec(String(v == null ? "" : v).trim().toLowerCase());
    const b = m && window.ML_LOGOS[m[1]];
    return b ? { id: m[1], b, v: m[2] && b.v[m[2]] ? m[2] : "" } : null;
  };
  const isDark = c => {
    let x = String(c || "").trim().toLowerCase();
    if (/^#[0-9a-f]{3}$/.test(x)) x = "#" + x.slice(1).split("").map(h => h + h).join("");
    if (!/^#[0-9a-f]{6}$/.test(x)) return false;
    const [r, g, b] = [1, 3, 5].map(i => parseInt(x.slice(i, i + 2), 16) / 255);
    return 0.2126 * r + 0.7152 * g + 0.0722 * b < 0.45;
  };
  function pick(p, o) {
    const V = p.b.v;
    let k = p.v;
    if (k) return o.dark && V[k + "-dark"] ? k + "-dark" : k;        // asked for: its -dark twin on a dark background
    if (o.mono && V.mono) return "mono";
    k = V.color ? "color" : V.mono ? "mono" : Object.keys(V)[0];
    if (o.dark && V[k].on === "light") return V[k + "-dark"] ? k + "-dark" : V.mono ? "mono" : k;
    if (!o.dark && V[k].on === "dark" && V.mono) return "mono";
    return k;
  }
  function el(v, o) {
    o = o || {};
    const p = parse(v);
    if (!p) {
      const s = String(v == null ? "" : v).trim();
      if (!/\.(svg|png|jpe?g|webp|gif)$/i.test(s)) return null;          // a picture in the graphic's assets folder
      const im = document.createElement("img");
      im.src = s;
      Object.assign(im.style, { width: "100%", height: "100%", objectFit: "contain", display: "block" });
      return im;
    }
    const k = pick(p, o), V = p.b.v[k], i = ++n;
    let svg = V.svg.replace(/mlid-/g, "mlid" + i + "-").replace(/mlc-/g, "mlc" + i + "-");
    if (o.mono && o.tint && !V.t && V.one) svg = svg.split(V.one).join(o.tint);
    const box = document.createElement("div");
    box.innerHTML = svg;
    const e = box.firstElementChild;
    e.setAttribute("preserveAspectRatio", "xMidYMid meet");
    Object.assign(e.style, { width: "100%", height: "100%", display: "block", overflow: "visible" });
    if (V.t) e.style.color = o.tint || (o.dark ? "#ffffff" : "#111111");
    e.setAttribute("data-logo", p.id + "/" + k);
    return e;
  }
  function fill(box, v, o) {                  // a logo setting: a library logo or a picture file, else its text
    const e = el(v, o);
    if (!e) { box.textContent = String(v == null ? "" : v); return false; }
    const s = o && o.scale != null ? o.scale : 1;
    Object.assign(e.style, { width: s * 100 + "%", height: s * 100 + "%", flex: "none" });
    box.textContent = "";
    box.appendChild(e);
    return true;
  }
  const token = t => {                        // a text setting names a logo only as ":id:" or ":id/variant:"
    const m = /^\s*:([a-z0-9][a-z0-9-]*(?:\/[a-z0-9-]+)?):\s*$/i.exec(String(t == null ? "" : t));
    return m && parse(m[1]) ? m[1] : null;
  };
  window.MLLogo = {
    el, isDark,
    is: v => !!parse(v),
    name: v => { const p = parse(v); return p ? p.b.n : ""; },
    aspect: (v, o) => { const p = parse(v); return p ? p.b.v[pick(p, o || {})].a : 1; },
    variant: (v, o) => { const p = parse(v); return p ? p.id + "/" + pick(p, o || {}) : ""; },
    split: v => String(v == null ? "" : v).split("|").map(s => s.trim()).filter(Boolean),
    lead: t => {
      const s = String(t == null ? "" : t), m = /^\s*:([a-z0-9][a-z0-9-]*(?:\/[a-z0-9-]+)?):\s*/i.exec(s);
      return m && parse(m[1]) ? [m[1], s.slice(m[0].length)] : [null, s];
    },
    fill, token,
    text: (box, t, o) => { const k = token(t); if (k) return fill(box, k, o); box.textContent = String(t == null ? "" : t); return false; },
  };
})();
"""


def js(ids: list[str], root: Path | None = None) -> str:
    """logos.js: these logos (every variant: MLLogo picks one for a background or a tint) + the MLLogo helper."""
    root = Path(root or ROOT)
    data = {}
    for lid in ids:
        lg = by_id(lid, root)
        if not lg:
            continue
        vs = {}
        for var, info in lg["variants"].items():
            if lid == BRAND_ID:                          # My Brand's pictures, inside an <svg> each
                vs[var] = {"a": info["aspect"], "on": info["on"], "t": 0, "one": None, "svg": _brand_svg(info)}
                continue
            f = root / lid / f"{var}.svg"
            if f.exists():
                vs[var] = {"a": info["aspect"], "on": info["on"], "t": 1 if info["tint"] else 0, "one": info["one"],
                           "svg": f.read_text(encoding="utf-8")}
        if vs:
            data[lid] = {"n": lg["name"], "v": vs}
    body = json.dumps(data, ensure_ascii=True, separators=(",", ":")).replace("</", "<\\/")
    return ("/* MotionLab logos (tools\\logos.py): the library logos this graphic names + window.MLLogo. The logos are "
            "trademarks of their owners. */\n" + HELPER.replace("DATA", body, 1))


def ensure(folder: Path, values: dict, decl: list[dict], extra=None, root: Path | None = None,
           link: bool = True) -> tuple[list[str], list[str]]:
    """<folder>\\assets\\logos\\logos.js = the logos the graphic names + MLLogo (written only when it changes - a
    render's inputs hash reads the assets' times), and a <script> to it in index.html's <head> when there is none.
    Nothing is written for a graphic that declares no logo setting, names no logo and does not load logos.js.
    -> (ids, unknown names)."""
    folder = Path(folder)
    if extra is None:
        try:
            extra = json.loads((folder / "overlay.json").read_text(encoding="utf-8")).get("logos") or []
        except (OSError, ValueError):
            extra = []
    ids, unknown = named(values, decl, extra, root)
    idx = folder / "index.html"
    h = idx.read_text(encoding="utf-8") if idx.exists() else ""
    uses = "assets/logos/logos.js" in h
    if not ids and not uses and not any(is_logo_setting(d) for d in decl):
        return ids, unknown
    dst = folder / "assets" / "logos" / "logos.js"
    text = js(ids, root)
    if not dst.exists() or dst.read_text(encoding="utf-8") != text:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding="utf-8", newline="\n")
    if link and h and not uses:
        m = re.search(r"<head[^>]*>", h, re.I)
        if m:
            idx.write_text(h[:m.end()] + "\n" + SCRIPT + h[m.end():], encoding="utf-8")
    return ids, unknown


# ------------------------------------------------------------------------------------------------- self-check
def selfcheck(verbose: bool = True) -> dict:
    """Known answers, no render, on temp folders: clean() renames ids / classes and keeps the references, refuses a
    script / an outside link / a picture inside, reads the background and the tint; import_folder() builds the index
    from a made-up source (and leaves the source as it was); parse / find / named; ensure() writes only the named
    logos, links index.html once and does not rewrite an unchanged logos.js; the shipped library is complete."""
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

    g = ('<?xml version="1.0"?><svg id="Layer_1" xmlns="http://www.w3.org/2000/svg" width="48" height="24" '
         'viewBox="0 0 48 24"><title>Demo</title><defs><linearGradient id="a"><stop stop-color="#F00"/></linearGradient>'
         '<style>.st0{fill:url(#a)}.st1{fill:White}</style></defs><path class="st0" d="M0 0h24v24H0z"/>'
         '<path class="st1" d="M24 0h24v24H24z"/><use xlink:href="#a"/></svg>')
    svg, info = clean(g)
    ok('id="mlid-0"' in svg and "url(#mlid-0)" in svg and 'href="#mlid-0"' in svg and 'id="a"' not in svg
       and "Layer_1" not in svg, "ids renamed mlid-N, every reference follows (url(#), href)")
    ok('class="mlc-0"' in svg and ".mlc-0{" in svg and ".st0" not in svg, "CSS classes renamed mlc-N in <style> and class=")
    ok("<title>" not in svg and "<?xml" not in svg and 'width="48"' not in svg and 'viewBox="0 0 48 24"' in svg
       and "fill:#ffffff" in svg, "title / declaration / fixed size gone, viewBox kept, named colours as hex")
    ok(info["aspect"] == 2.0 and not info["tint"] and info["one"] is None, f"aspect 2.0, not a one-colour logo: {info}")
    _, mono = clean('<svg viewBox="0 0 24 24" fill="currentColor"><path d="M0 0h24v24z"/></svg>')
    _, one = clean('<svg viewBox="0 0 24 24"><path fill="#635BFF" d="M0 0h24v24z"/></svg>')
    _, black = clean('<svg viewBox="0 0 10 10"><path d="M0 0h9v9z"/></svg>')
    _, white = clean('<svg viewBox="0 0 10 10"><path fill="#fff" d="M0 0h9v9z"/></svg>')
    ok(mono["tint"] and mono["on"] == "any" and one["one"] == "#635bff" and black["on"] == "light"
       and white["on"] == "dark", "mono = takes a tint; one colour found; no fill = black ink (light background); "
       "white ink = for a dark background")
    refused = 0
    for b in ('<svg viewBox="0 0 1 1"><script>alert(1)</script></svg>', '<svg viewBox="0 0 1 1" onload="x()"></svg>',
              '<svg viewBox="0 0 1 1"><use href="http://x/y.svg#a"/></svg>', '<svg viewBox="0 0 1 1"><image href="a.png"/></svg>',
              '<svg viewBox="0 0 1 1"><style>@import url(http://x)</style></svg>'):
        try:
            clean(b)
        except ValueError:
            refused += 1
    ok(refused == 5, f"refused: a script, an event handler, an outside link, a picture inside, a CSS import ({refused} of 5)")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        src, lib = tmp / "src", tmp / "lib"
        for lid, files in {"youtube": {"color": g, "mono": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M0 0h1z"/></svg>'},
                           "acme-tool": {"color": '<svg viewBox="0 0 10 10"><path d="M0 0h9z"/></svg>'},
                           "Bad Name": {"color": g}, "evil": {"color": '<svg viewBox="0 0 1 1"><script/></svg>'}}.items():
            (src / lid).mkdir(parents=True)
            for var, text in files.items():
                (src / lid / f"{var}.svg").write_text(text, encoding="utf-8")
        before = {p.relative_to(src).as_posix(): p.read_bytes() for p in src.rglob("*") if p.is_file()}
        idx = import_folder(src, lib, verbose=False)
        after = {p.relative_to(src).as_posix(): p.read_bytes() for p in src.rglob("*") if p.is_file()}
        ok(before == after, "the source folder is only read")
        ids = [lg["id"] for lg in idx["logos"]]
        ok(ids == ["acme-tool", "youtube"] and len(idx["skipped"]) == 2,
           f"index: {ids}, skipped a bad folder name and a file with a script ({len(idx['skipped'])})")
        yt = by_id("youtube", lib)
        ok(yt and yt["name"] == "YouTube" and yt["group"] == "social" and list(yt["variants"]) == ["color", "mono"]
           and by_id("acme-tool", lib)["name"] == "Acme Tool", "names from the list, else from the folder; variants in order")
        ok(parse("youtube/mono", lib)[1] == "mono" and parse(":youtube:", lib)[0]["id"] == "youtube"
           and parse("youtube/wordmark", lib)[1] is None and parse("nope", lib) is None,
           "parse: id, id/variant, :id:, a variant it lacks = the default, unknown = none")
        ok(find("a youtube video", 3, lib)[0]["id"] == "youtube" and find("shorts", 3, lib)[0]["id"] == "youtube",
           "find: by name and by a search word")
        decl = [{"id": "logo", "type": "string", "default": ""}, {"id": "nodes", "type": "string", "default": ""},
                {"id": "font", "type": "enum", "default": "Inter"}]
        ids, unk = named({"logo": "youtube/mono|mine.png|nope", "nodes": "AI|:acme-tool:|:zzz:"}, decl, ["youtube"], lib)
        ok(ids == ["youtube", "acme-tool"] and unk == ["nope"], f"named: {ids}, unknown {unk} (a picture file is fine)")
        gr = tmp / "graphic"
        gr.mkdir()
        (gr / "index.html").write_text("<html><head><meta charset='utf-8'></head><body></body></html>", encoding="utf-8")
        ensure(gr, {"logo": "youtube"}, decl, [], lib)
        f = gr / "assets" / "logos" / "logos.js"
        text = f.read_text(encoding="utf-8")
        ok('"youtube"' in text and "acme-tool" not in text and "window.MLLogo" in text and "</svg" not in text,
           "logos.js: only the named logo, the helper, no raw </ in the script")
        h = (gr / "index.html").read_text(encoding="utf-8")
        mt = f.stat().st_mtime_ns
        time.sleep(0.02)
        ensure(gr, {"logo": "youtube"}, decl, [], lib)
        ok(h.count(SCRIPT) == 1 and (gr / "index.html").read_text(encoding="utf-8").count(SCRIPT) == 1
           and f.stat().st_mtime_ns == mt, "index.html linked once; an unchanged logos.js is not rewritten")
        ensure(gr, {"logo": ""}, decl, [], lib)
        ok('"youtube"' not in f.read_text(encoding="utf-8"), "a logo no longer named leaves logos.js")
        plain = tmp / "plain"
        plain.mkdir()
        (plain / "index.html").write_text("<html><head></head></html>", encoding="utf-8")
        ensure(plain, {}, [{"id": "text", "type": "string", "default": "hi"}], [], lib)
        ok(not (plain / "assets").exists(), "a graphic with no logo gets nothing")
        # My Brand's logo as "brand" (2026-10-26), on a made-up lab: a 4x2 PNG main logo + a light version
        global LAB
        real, LAB = LAB, Path(tmp) / "lab"
        try:
            png = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", 4, 2) + b"\x08\x06\x00\x00\x00"
            bd = LAB / "knowledge" / "local" / "brand"
            bd.mkdir(parents=True)
            (bd / "logo.png").write_bytes(png)
            (bd / "logo_light.png").write_bytes(png)
            bj = LAB / "knowledge" / "local" / "brand.json"
            bj.write_text(json.dumps({"name": "RIFT", "identity": {"logo": "knowledge/local/brand/logo.png",
                                                                   "logos": {"light": "knowledge/local/brand/logo_light.png"}}}))
            e = brand_entry()
            ok(e and e["name"] == "RIFT" and set(e["variants"]) == {"color", "color-dark"}
               and e["variants"]["color"]["aspect"] == 2.0 and e["variants"]["color"]["on"] == "light"
               and parse("brand")[0]["id"] == BRAND_ID and named({"logo": "brand"}, [{"id": "logo", "type": "string"}])[0] == ["brand"]
               and "data:image/png;base64" in js(["brand"]),
               "My Brand's logo = the logo 'brand': its versions as variants (the light one for dark backgrounds), its "
               "size from the picture, inside logos.js")
            bj.write_text(json.dumps({"identity": {"logo": "C:/elsewhere/logo.png"}}))
            ok(brand_entry() is None and _pic_size(b"nothing", ".png") == (1, 1),
               "no logo of My Brand's own folder = no 'brand'; an unknown picture = 1 x 1")
        finally:
            LAB = real

    cat = catalog()
    files = [ROOT / lg["id"] / f"{v}.svg" for lg in cat["logos"] for v in lg["variants"]]
    ok(cat["count"] > 0 and all(f.exists() for f in files) and (ROOT / "README.md").exists(),
       f"the shipped library: {cat['count']} logos, {len(files)} files, all present, README")
    if verbose:
        print(f"{n - len(bad)} of {n} passed in {time.time() - t0:.1f} s")
    return {"passed": not bad, "bad": bad}
