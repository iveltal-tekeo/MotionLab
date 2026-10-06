"""Production projects (projects\\<name>\\): the user's footage is read-only, everything we make goes to build\\."""
from __future__ import annotations

from pathlib import Path

from .util import LAB, file_fingerprint, read_json, sha256_file, write_json

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".mxf", ".avi", ".m4v", ".mts"}
PROJECTS = LAB / "projects"


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
        return sorted(f for f in self.dir.iterdir() if f.is_file() and f.suffix.lower() in VIDEO_EXT)

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
