"""Newer versions of the outside packages MotionLab pins (HyperFrames and GSAP for the HTML overlays, 0.3.2).

HyperFrames releases several times a day, so MotionLab never upgrades by itself: the app asks npm at most once a day
(one small request per package, registry.npmjs.org; nothing is sent about you) and Settings > Programs shows the
pinned, the installed and the newest version. `overlay.py upgrade-test` renders the examples with a newer version and
compares every frame; `overlay.py pin` adopts it (the repo owner, then GitHub's tests). The answer is kept in
.app\\upstream.json (the last check + the upgrade tests' results).
yt-dlp too (the user, 2026-10-15: "already up to date (2026.08.19) but it still shows update"): its newest release
from PyPI in the same daily check (latest["yt-dlp"]), so Settings says "the newest" instead of judging by age only;
*Update yt-dlp* records what yt-dlp itself answered (record_latest).
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import threading
import urllib.request

from .util import LAB, read_json, write_json

OVL = LAB / "tools" / "overlays"
STATE = LAB / ".app" / "upstream.json"
PACKAGES = {"hyperframes": "https://github.com/heygen-com/hyperframes/releases",
            "gsap": "https://github.com/greensock/GSAP/releases"}
REGISTRY = "https://registry.npmjs.org/-/package/{}/dist-tags"
PYPI_YTDLP = "https://pypi.org/pypi/yt-dlp/json"           # info.version = the newest stable release, "2026.8.19"
EVERY_S = 24 * 3600
_LOCK = threading.Lock()


def _now() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def vkey(v: str | None) -> tuple:
    """'0.8.149' -> (0, 8, 149); pre-releases ('0.7.67-alpha.0') sort below their release."""
    m = re.match(r"(\d+)\.(\d+)\.(\d+)(-.+)?$", str(v or ""))
    return (int(m[1]), int(m[2]), int(m[3]), 0 if m[4] else 1) if m else (-1,)


def pinned() -> dict:
    """{package: version} from tools\\overlays\\package.json (what setup.bat / Install puts on every PC)."""
    try:
        deps = read_json(OVL / "package.json").get("dependencies", {})
    except (OSError, ValueError):
        return {}
    return {k: str(v).lstrip("^~=") for k, v in deps.items() if k in PACKAGES}


def installed() -> dict:
    out = {}
    for k in PACKAGES:
        try:
            out[k] = read_json(OVL / "node_modules" / k / "package.json").get("version")
        except (OSError, ValueError):
            out[k] = None
    return out


def latest(package: str, timeout: float = 10) -> str:
    req = urllib.request.Request(REGISTRY.format(package), headers={"Accept": "application/json",
                                                                     "User-Agent": "MotionLab"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        tags = json.loads(r.read().decode("utf-8"))
    v = tags.get("latest")
    if not v or vkey(v) == (-1,):
        raise ValueError(f"npm gave no usable 'latest' for {package}: {tags}")
    return v


def dkey(v: str | None) -> tuple:
    """yt-dlp's versions are dates: '2026.08.19' and PyPI's '2026.8.19' -> (2026, 8, 19); a nightly's 4th part counts."""
    return tuple(int(x) for x in re.findall(r"\d+", str(v or ""))[:4])


def latest_ytdlp(timeout: float = 10) -> str:
    req = urllib.request.Request(PYPI_YTDLP, headers={"Accept": "application/json", "User-Agent": "MotionLab"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        v = (json.loads(r.read().decode("utf-8")).get("info") or {}).get("version")
    if len(dkey(v)) < 3:
        raise ValueError(f"PyPI gave no usable version for yt-dlp: {v!r}")
    return v


def ytdlp_latest() -> dict:
    """What the last check knows about yt-dlp (no network): {"latest", "checked"} or {}."""
    s = _load()
    v = (s.get("latest") or {}).get("yt-dlp")
    return {"latest": v, "checked": (s.get("ytdlp_checked") or s.get("checked"))} if v else {}


def record_latest(version: str) -> None:
    """*Update yt-dlp* ended "up to date" or "updated to X": X is the newest yt-dlp knows of (kept until the next check
    finds a newer one)."""
    if len(dkey(version)) < 3:
        return
    with _LOCK:
        s = _load()
        old = (s.get("latest") or {}).get("yt-dlp")
        if not old or dkey(version) >= dkey(old):
            s.setdefault("latest", {})["yt-dlp"] = version
            s["ytdlp_checked"] = _now()
            write_json(STATE, s, indent=1)


def _load() -> dict:
    try:
        return read_json(STATE)
    except (OSError, ValueError):
        return {}


def state() -> dict:
    """What Settings shows (no network): per package pinned / installed / latest / newer / notes + the last check +
    upgrade tests."""
    s = _load()
    pin, inst, lat = pinned(), installed(), s.get("latest", {})
    pk = {}
    for k, notes in PACKAGES.items():
        p = pin.get(k)
        pk[k] = {"pinned": p, "installed": inst.get(k), "latest": lat.get(k), "notes": notes,
                 "newer": bool(p and lat.get(k) and vkey(lat[k]) > vkey(p)),
                 "out_of_date": bool(p and inst.get(k) and inst[k] != p)}     # the pin changed, npm ci not run
    return {"checked": s.get("checked"), "error": s.get("error"), "packages": pk, "tests": s.get("tests", {})}


def check(force: bool = False) -> dict:
    """Ask npm (and PyPI for yt-dlp) for the newest versions - at most once a day unless force, or when a package was
    never asked (yt-dlp, added 2026-10-15). Never raises: errors go into the state."""
    with _LOCK:
        s = _load()
        last = s.get("checked")
        if not force and last and all(k in (s.get("latest") or {}) for k in (*PACKAGES, "yt-dlp")):
            try:
                if (_dt.datetime.now() - _dt.datetime.fromisoformat(last)).total_seconds() < EVERY_S:
                    return state()
            except ValueError:
                pass
        lat, err = dict(s.get("latest", {})), None
        for k in PACKAGES:
            try:
                lat[k] = latest(k)
            except Exception as e:                                  # noqa: BLE001 - offline, proxy, npm down
                err = f"{k}: {type(e).__name__}: {e}"
        try:
            v = latest_ytdlp()
            if not lat.get("yt-dlp") or dkey(v) >= dkey(lat["yt-dlp"]):   # never below what yt-dlp -U itself said
                lat["yt-dlp"] = v
            s["ytdlp_checked"] = _now()
        except Exception as e:                                      # noqa: BLE001
            err = (err + " · " if err else "") + f"yt-dlp: {type(e).__name__}: {e}"
        s.update({"checked": _now(), "latest": lat, "error": err})
        write_json(STATE, s, indent=1)
    return state()


def record_test(version: str, result: dict) -> None:
    """Keep an upgrade test's result (overlay.py upgrade-test) so Settings and `overlay.py pin` can show it."""
    with _LOCK:
        s = _load()
        s.setdefault("tests", {})[version] = {**result, "when": _now()}
        write_json(STATE, s, indent=1)
