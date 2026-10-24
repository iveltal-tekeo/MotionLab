"""Production projects (projects\\<name>\\): the user's footage is read-only, everything we make goes to build\\."""
from __future__ import annotations

from pathlib import Path

from .util import LAB, file_fingerprint, read_json, sha256_file, write_json

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".mxf", ".avi", ".m4v", ".mts", ".webm"}     # = the app's (a .webm recording too)
# photos (2026-10-24, a friend's ask): a still shot of the edit, never turned into a video file in the folder; HEIC /
# HEIF (iPhone) read through pillow-heif, AVIF through Pillow itself
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".avif", ".bmp", ".tif", ".tiff", ".gif"}
APPLE_DOUBLE = b"\x00\x05\x16\x07"             # the first bytes of a Mac's "._" file (Finder info, no picture)
JUNK_NAMES = {"thumbs.db", "desktop.ini"}
PROJECTS = LAB / "projects"


def is_junk(p: Path) -> bool:
    """A file a Mac, an iPhone or Windows leaves beside the clips, never a clip: a hidden name (._IMG_0912.mov - an
    AppleDouble file of ~4 KB that showed as a black clip -, .DS_Store, .Trashes), Thumbs.db, desktop.ini, and an
    AppleDouble file under any name (one copied in before 2026-10-24 lost its dot: _IMG_0912.mov)."""
    n = p.name
    if n.startswith(".") or n.lower() in JUNK_NAMES:
        return True
    try:
        if p.stat().st_size <= 1 << 20:
            with open(p, "rb") as f:
                return f.read(4) == APPLE_DOUBLE
    except OSError:
        pass
    return False


def is_photo_twin(p: Path) -> bool:
    """IMG_0950.jpg.mp4 beside IMG_0950.jpg: the still video a local add-on made so photos worked before MotionLab
    took them (2026-10-24) - the photo is the clip, the twin is left alone and not listed."""
    stem = p.name[:-len(p.suffix)] if p.suffix else p.name
    return p.suffix.lower() in VIDEO_EXT and Path(stem).suffix.lower() in PHOTO_EXT \
        and (p.parent / stem).is_file()


def is_photo(p: Path | str) -> bool:
    return Path(p).suffix.lower() in PHOTO_EXT


def clip_files(d: Path, exts=VIDEO_EXT | PHOTO_EXT) -> list[Path]:
    """The user's clips directly in a video's folder - videos and photos (exts), sorted by name - without the junk a
    Mac / iPhone / Windows leaves there and without a photo's still-video twin."""
    try:
        files = [f for f in Path(d).iterdir() if f.is_file() and f.suffix.lower() in exts]
    except OSError:
        return []
    return sorted(f for f in files if not is_junk(f) and not is_photo_twin(f))


class Project:
    def __init__(self, name_or_path: str | Path):
        p = Path(name_or_path)
        self.dir = (p if p.is_dir() else PROJECTS / str(name_or_path)).resolve()
        if not self.dir.is_dir():
            raise SystemExit(f"project folder not found: {self.dir}")
        self.name = self.dir.name
        self.build = self.dir / "build"
        self.cache = self.build / "cache"
        self.manifest_path = self.build / "sources.json"

    # ------------------------------------------------------------------ the user's files (read-only)
    def footage_files(self) -> list[Path]:
        """The clips: videos and photos (a photo is a still shot), never Mac / iPhone junk (clip_files)."""
        return clip_files(self.dir)

    def check(self, target: str | Path) -> Path:
        """Every write goes through here: only inside build\\, never onto a source file."""
        t = Path(target).resolve()
        if self.build != t and self.build not in t.parents:
            raise PermissionError(f"refusing to write outside {self.build}: {t}")
        if any(t == s.resolve() for s in self.footage_files()):
            raise PermissionError(f"refusing to write to a source file: {t}")
        return t

    # ------------------------------------------------------------------ manifest: stable IDs + checksums
    def manifest(self) -> dict:
        return read_json(self.manifest_path) if self.manifest_path.exists() else {"sources": {}}

    def register_sources(self, with_hash: bool = True) -> dict:
        """Give every footage file a stable letter ID (A, B, ...) and record its SHA-256."""
        m = self.manifest()
        by_path = {v["path"]: k for k, v in m["sources"].items()}
        for f in self.footage_files():
            key = by_path.get(str(f))
            if key is None:
                key = _next_id(m["sources"])
                m["sources"][key] = {"path": str(f), "name": f.name}
            ent = m["sources"][key]
            if is_photo(f):
                ent["photo"] = True
            fp = file_fingerprint(f)
            if with_hash and (ent.get("fingerprint") != fp or not ent.get("sha256")):
                ent["sha256"] = sha256_file(f)
            ent["fingerprint"] = fp
        self.build.mkdir(parents=True, exist_ok=True)
        write_json(self.check(self.manifest_path), m)
        return m

    def verify_sources(self) -> list[str]:
        """Names of sources whose SHA-256 differs from the manifest (should always be empty)."""
        bad = []
        for k, ent in self.manifest()["sources"].items():
            p = Path(ent["path"])
            if not p.exists() or (ent.get("sha256") and sha256_file(p) != ent["sha256"]):
                bad.append(f"{k} {ent['name']}")
        return bad


def _next_id(existing: dict) -> str:
    i = 0
    while True:
        s, n = "", i
        while True:
            s = chr(65 + n % 26) + s
            n = n // 26 - 1
            if n < 0:
                break
        if s not in existing:
            return s
        i += 1
