"""Photos as still shots (2026-10-24, a friend's ask: "add photos and see them as photos" - never turned into video
files in the folder). Any common format the right way up: HEIC / HEIF (iPhone) through pillow-heif, AVIF through
Pillow, the EXIF rotation applied, a GIF's first frame, transparency on black. Used by the frame cache
(prep_footage.py: a photo = a cache of ONE frame, every frame of a shot shows it), the brief's sheet of the photos
(brief.py) and the app's thumbnails. The user's photo is only read.

In an edit a photo is a clip layer with "hold": true (compose.py ClipLayer) - by default SECONDS long with a slow
zoom (KEN_BURNS), silent, cover-fit like any clip; "fit": "contain" shows the whole photo over a blurred copy of
itself (a horizontal photo in a vertical video). Per photo the plan / New edit may change both (editreq "photos")."""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

SECONDS = 5.0                   # a photo's length in the edit when nobody says otherwise
KEN_BURNS = 1.06                # the slow zoom over a photo shot: 1.0 -> this (1 = no zoom)
_heif = None


def heif_ready() -> bool:
    """pillow-heif registered (HEIC / HEIF open like any picture); False when it is not installed."""
    global _heif
    if _heif is None:
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
            _heif = True
        except ImportError:
            _heif = False
    return _heif


def open_rgb(p: Path | str):
    """The photo as an RGB PIL image, the right way up (EXIF orientation applied)."""
    from PIL import Image, ImageOps
    p = Path(p)
    if p.suffix.lower() in (".heic", ".heif") and not heif_ready():
        raise RuntimeError(f"{p.name}: HEIC photos need pillow-heif - double-click setup.bat (it installs what is "
                           "missing) or run .venv\\Scripts\\python -m pip install -r requirements.txt")
    im = Image.open(p)
    try:
        im.seek(0)                                   # an animated GIF / WebP: its first frame
    except EOFError:
        pass
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (12, 12, 12))
        bg.paste(im, mask=im.getchannel("A"))
        return bg
    return im.convert("RGB")


def orientation(w: int, h: int) -> str:
    return "vertical" if h > w * 1.15 else "horizontal" if w > h * 1.15 else "square"


def info(p: Path | str) -> dict:
    """{width, height (as shown, after the rotation), orientation, taken (EXIF date, "" when none), format}."""
    from PIL import Image
    p = Path(p)
    heif_ready()
    with Image.open(p) as im:
        fmt = im.format or p.suffix.lstrip(".").upper()
        w, h = im.size
        taken = ""
        try:
            ex = im.getexif()
            if ex.get(0x0112, 1) in (5, 6, 7, 8):     # EXIF orientation: turned a quarter, shown the other way round
                w, h = h, w
            raw = ex.get_ifd(0x8769).get(0x9003) or ex.get(0x0132) or ""       # DateTimeOriginal, else DateTime
            taken = _dt.datetime.strptime(str(raw).strip()[:19], "%Y:%m:%d %H:%M:%S").strftime("%Y-%m-%d %H:%M") \
                if raw else ""
        except (ValueError, AttributeError, KeyError, OSError):
            taken = ""
    return {"width": w, "height": h, "orientation": orientation(w, h), "taken": taken, "format": fmt}


def thumbnail(p: Path | str, out: Path, size: int = 480) -> Path:
    """A small JPEG of the photo (the app's clips grid: HEIC / TIFF do not show in the browser)."""
    from PIL import Image
    im = open_rgb(p)
    im.thumbnail((size, size), Image.LANCZOS)
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, "JPEG", quality=82)
    return out


def sheet(photos: list[Path], out: Path, tile: int = 300, cols: int = 4) -> Path:
    """Every photo with its name under it, on one picture: Claude looks at this once to know what each photo shows
    (brief.py) instead of opening them one by one."""
    from PIL import Image, ImageDraw, ImageFont
    rows = (len(photos) + cols - 1) // cols
    W, H = cols * tile, rows * (tile + 26)
    can = Image.new("RGB", (W, max(H, 1)), (24, 24, 24))
    d = ImageDraw.Draw(can)
    try:
        font = ImageFont.truetype("segoeui.ttf", 15)
    except OSError:
        font = ImageFont.load_default()
    for i, p in enumerate(photos):
        x, y = (i % cols) * tile, (i // cols) * (tile + 26)
        try:
            im = open_rgb(p)
            im.thumbnail((tile - 8, tile - 8), Image.LANCZOS)
            can.paste(im, (x + (tile - im.width) // 2, y + 4 + (tile - 8 - im.height) // 2))
        except Exception as e:                       # noqa: BLE001 - a photo that does not open is named on the sheet
            d.text((x + 8, y + tile // 2), f"could not open: {type(e).__name__}", fill=(255, 120, 120), font=font)
        d.text((x + 6, y + tile), p.name[:38], fill=(235, 235, 235), font=font)
    out.parent.mkdir(parents=True, exist_ok=True)
    can.save(out, "JPEG", quality=85)
    return out
