"""Sound effects made with ElevenLabs (0.6.0; the user, 2026-10-26: "the sound effects ... seem very repetitive and
AI-made ... connect elevenlabs free key and start generating and we just upload to google drive for everyone to
download"): the described sounds of tools\\sounds\\generate.json (per kind) sent to ElevenLabs' text-to-sound
(`POST /v1/sound-generation`, the user's own key), each answer imported into this PC's library like any recorded
sound (motionlab\\sfx.py import_sounds: cut to its sound, its anchor measured) with the plan's licence; the user
listens in Motion Graphics > Sounds and keeps the best (★ / Hide). The free plan has NO commercial licence (ElevenLabs'
pricing page: "Commercial License" starts at Starter) - its sounds are marked so, and only the ones made on a paid plan
go into the zip for friends (`share_zip` -> Google Drive; a friend: Add sounds > a link -> `fetch_link`).

The key: knowledge\\local\\elevenlabs.json (never shared, never sent to the page) or ELEVENLABS_API_KEY.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from .util import LAB

KEYS = Path(os.environ.get("MOTIONLAB_ELEVENLABS_KEYS") or LAB / "knowledge" / "local" / "elevenlabs.json")  # (tests)
LIST = LAB / "tools" / "sounds" / "generate.json"
OUT = LAB / ".app" / "sound_gen"                      # each answer as ElevenLabs sent it (the library keeps a copy)
SHARE = LAB / ".app" / "share"
API = os.environ.get("ELEVENLABS_BASE", "https://api.elevenlabs.io")     # (a test server in the self-check)
CREDITS = 200                                         # a sound with no length asked (ElevenLabs' pricing page)
MIN_S = 0.5                                           # the shortest length the API takes (it said so, 2026-10-26)
PER_S = 10                                            # a length asked: credits a second (measured 2026-10-26: 41
FREE_CREDITS = 10_000                                 # credits for 4.1 s) | the free plan's month
SOURCE = "ElevenLabs sound effects"
LICENCE = {"free": "ElevenLabs free plan: non-commercial use only, and a video you post credits elevenlabs.io (a paid "
                   "plan: commercial use, no credit)",                 # ElevenLabs' help centre, read 2026-10-26
           "paid": "ElevenLabs paid plan: commercial licence (the account holder's) - may be shared with friends"}


class GenError(RuntimeError):
    pass


def settings() -> dict:
    """{"key": ..., "plan": "free" | "paid"} - ELEVENLABS_API_KEY over the file."""
    try:
        s = json.loads(KEYS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        s = {}
    key = os.environ.get("ELEVENLABS_API_KEY") or s.get("key") or ""
    return {"key": key, "plan": s.get("plan") if s.get("plan") in LICENCE else "free"}


def save_settings(key: str | None = None, plan: str | None = None) -> dict:
    """The key (None = keep it, "" = forget it) and the plan; -> what the page may see (never the key)."""
    s = {}
    try:
        s = json.loads(KEYS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    if key is not None:
        key = key.strip()
        if key and not re.fullmatch(r"[A-Za-z0-9_\-]{20,200}", key):
            raise ValueError("that does not look like an ElevenLabs API key")
        s["key"] = key
    if plan is not None:
        if plan not in LICENCE:
            raise ValueError("plan: free or paid")
        s["plan"] = plan
    KEYS.parent.mkdir(parents=True, exist_ok=True)
    KEYS.write_text(json.dumps(s, indent=1), encoding="utf-8")
    return public()


def public() -> dict:
    s = settings()
    try:
        bal = json.loads(KEYS.read_text(encoding="utf-8")).get("balance")
    except (OSError, ValueError):
        bal = None
    return {"key_set": bool(s["key"]), "key_end": s["key"][-4:] if s["key"] else "", "plan": s["plan"],
            "credits": CREDITS, "per_s": PER_S, "free_credits": FREE_CREDITS, "balance": bal}


def cost(seconds: float) -> int:
    """A sound's credits with its length asked (PER_S a second, at least 1)."""
    return max(1, int(round(max(MIN_S, float(seconds)) * PER_S)))


def balance(key: str | None = None) -> dict | None:
    """The account's credits this month (GET /v1/user/subscription - costs nothing) -> {used, limit, tier, when},
    kept in the key file for the page; None when it cannot be read."""
    key = key or settings()["key"]
    if not key:
        return None
    req = urllib.request.Request(f"{API}/v1/user/subscription", headers={"xi-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
    except (urllib.error.URLError, ValueError, OSError):
        return None
    b = {"used": d.get("character_count"), "limit": d.get("character_limit"), "tier": d.get("tier"),
         "when": time.strftime("%Y-%m-%d %H:%M")}
    try:
        s = json.loads(KEYS.read_text(encoding="utf-8"))
        s["balance"] = b
        KEYS.write_text(json.dumps(s, indent=1), encoding="utf-8")
    except (OSError, ValueError):
        pass
    return b


def prompts() -> dict:
    return json.loads(LIST.read_text(encoding="utf-8"))


def _post(key: str, text: str, seconds: float, influence: float, model: str = "", fmt: str = "mp3_44100_128",
          loop: bool = False) -> bytes:
    body = json.dumps({"text": text, "duration_seconds": max(MIN_S, min(30.0, float(seconds))),
                       "prompt_influence": influence, **({"model_id": model} if model else {}),
                       **({"loop": True} if loop else {})}).encode("utf-8")    # loop = it repeats with no seam (beds)
    req = urllib.request.Request(f"{API}/v1/sound-generation?output_format={fmt}", data=body, method="POST",
                                 headers={"xi-api-key": key, "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:300]
            if e.code == 429 and attempt < 2:                  # too many at once: wait, then again
                time.sleep(5 * (attempt + 1))
                continue
            if e.code == 401:
                raise GenError("ElevenLabs refused the key (401) - check it in Motion Graphics > Sounds") from None
            if e.code in (402, 403) or "quota" in msg.lower() or "credits" in msg.lower():
                raise GenError(f"ElevenLabs: no credits left this month ({e.code}) - {msg}") from None
            raise GenError(f"ElevenLabs answered {e.code}: {msg}") from None
        except urllib.error.URLError as e:
            if attempt < 2:
                time.sleep(3)
                continue
            raise GenError(f"ElevenLabs could not be reached: {e.reason}") from None
    raise GenError("ElevenLabs: too many requests - try again in a minute")


def generate(want: dict[str, int], log=print, root: Path | None = None, dry: bool = False) -> dict:
    """want = {kind: how many}; each made from the kind's descriptions in turn, saved under .app\\sound_gen\\<time>\\
    <kind>\\, then imported into the library (`root`, default library\\sounds) as that kind with the plan's licence.
    -> {"made", "added" (library files), "credits", "folder", "skipped"}."""
    from . import sfx as SFX
    s, P = settings(), prompts()
    if not s["key"] and not dry:
        raise GenError("no ElevenLabs key yet - add yours in Motion Graphics > Sounds > Make sounds")
    kinds = P["kinds"]
    bad = [k for k in want if k not in kinds or k not in SFX.KINDS]
    if bad:
        raise GenError(f"no descriptions for {', '.join(bad)} (tools\\sounds\\generate.json)")
    n_all = sum(max(0, int(v)) for v in want.values())
    need = sum(cost(kinds[k].get("seconds", 1.0)) * max(0, int(v)) for k, v in want.items())
    if s["plan"] == "free" and need > FREE_CREDITS:
        raise GenError(f"{n_all} sounds = about {need} credits: the free plan has {FREE_CREDITS} a month - ask for fewer")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    folder = OUT / stamp
    out = {"made": 0, "added": [], "credits": 0, "folder": str(folder), "skipped": []}
    if dry:
        out["credits"] = need
        return out
    infl = float(P.get("prompt_influence", 0.45))
    model, fmt = str(P.get("model") or ""), str(P.get("format") or "mp3_44100_128")
    for kind, n in want.items():
        spec = kinds[kind]
        for i in range(max(0, int(n))):
            text = spec["prompts"][i % len(spec["prompts"])]
            log(f"{kind} {i + 1} of {n}: \"{text[:70]}\"")
            try:
                audio = _post(s["key"], text, float(spec.get("seconds", 1.0)), infl, model, fmt)
            except GenError as e:                               # a format / model this plan does not get: MP3, default
                if fmt == "mp3_44100_128" or not re.search(r"answered (400|403|422).*(format|model|tier|subscription|plan)",
                                                           str(e), re.I):
                    raise
                log(f"  ({fmt} / {model or 'the default model'} refused - MP3 and the default model from now on)")
                fmt, model = "mp3_44100_128", ""
                audio = _post(s["key"], text, float(spec.get("seconds", 1.0)), infl, model, fmt)
            out["credits"] += cost(spec.get("seconds", 1.0))
            f = folder / kind / f"{kind}_el_{stamp[-6:]}_{i + 1:02d}.{'wav' if fmt.startswith('wav') else 'mp3'}"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(audio)
            out["made"] += 1
            got = SFX.import_sounds(f, f"{SOURCE}: {text}", LICENCE[s["plan"]], kind=kind,
                                    **({"root": root} if root else {}))
            out["added"] += [r["file"] for r in got["added"]]
            out["skipped"] += got["skipped"]
    out["balance"] = balance(s["key"])                           # (what the month has left, for the page)
    return out


def share_zip(root: Path | None = None) -> dict:
    """The sounds made on a paid plan (commercial licence: they may be passed on) as one zip for Google Drive:
    the library's own cut copies + list.json (each one's kind, anchor and licence) - a friend's *Add sounds* > a link
    sorts them the same way. -> {"zip", "count"}; the free plan's sounds are never in it."""
    from . import sfx as SFX
    root = Path(root or SFX.SOUNDS)
    rows = [e for e in json.loads((root / "sounds.json").read_text(encoding="utf-8")).get("sounds", [])
            if str(e.get("source", "")).startswith(SOURCE) and e.get("licence") == LICENCE["paid"]
            and (root / e["file"]).exists()]
    if not rows:
        raise GenError("no sounds made on a paid ElevenLabs plan yet - the free plan's have no commercial licence, so "
                       "they stay on this PC")
    SHARE.mkdir(parents=True, exist_ok=True)
    z = SHARE / f"motionlab_sounds_{time.strftime('%Y-%m-%d')}.zip"
    listing = {"_comment": "MotionLab sounds made with ElevenLabs on a paid plan - import with Motion Graphics > "
                           "Sounds > Add sounds (a link to this zip, or the zip itself)",
               "packs": {"elevenlabs": {"name": SOURCE, "licence": LICENCE["paid"], "page": "", "how": ""}},
               "sounds": []}
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for e in rows:
            data = (root / e["file"]).read_bytes()
            zf.writestr(e["file"], data)
            listing["sounds"].append({"pack": "elevenlabs", "kind": e["kind"], "path": e["file"],
                                      "sha256": hashlib.sha256(data).hexdigest(), **({"fav": True} if e.get("fav") else {})})
        zf.writestr("list.json", json.dumps(listing, indent=1, ensure_ascii=False))
    return {"zip": str(z), "count": len(rows)}


def drive_url(link: str) -> str:
    """A Google Drive share link -> its direct download (a big file's "can't scan" page skipped); another https link
    as it is."""
    link = link.strip()
    m = re.search(r"drive\.google\.com/(?:file/d/|open\?id=|uc\?(?:export=download&)?id=)([\w-]{20,})", link)
    if m:
        return f"https://drive.usercontent.google.com/download?id={m[1]}&export=download&confirm=t"
    if not re.match(r"https://", link):
        raise GenError("a link starting with https:// (a Google Drive share link)")
    return link


def unpack(zpath: Path, dest: Path) -> dict:
    """A shared sounds zip into dest: only its sound files and list.json (no other files, no path outside dest).
    -> the zip's listing."""
    from . import sfx as SFX
    dest.mkdir(parents=True, exist_ok=True)
    root = dest.resolve()
    listing = None
    with zipfile.ZipFile(zpath) as zf:
        for info in zf.infolist():
            name = info.filename.replace("\\", "/")
            if info.is_dir() or name.startswith("/") or ".." in name.split("/"):
                continue
            if name == "list.json":
                listing = json.loads(zf.read(info).decode("utf-8"))
                continue
            if Path(name).suffix.lower() not in SFX.AUDIO_EXT or info.file_size > 50_000_000:
                continue
            p = (dest / name).resolve()                    # (2026-10-26 review: "C:/Users/x.wav" escaped dest - a
            if not p.is_relative_to(root) or p == root:   # drive letter, a drive-relative "C:x.wav", a link: refused)
                continue
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(zf.read(info))
    if not listing or not isinstance(listing.get("sounds"), list):
        raise GenError("not a MotionLab sounds zip (no list.json in it)")
    return listing


def fetch_link(link: str, dest: Path, log=print) -> Path:
    """Downloads a shared zip (Google Drive or any https link) to dest\\sounds.zip (<= 500 MB)."""
    url = drive_url(link)
    dest.mkdir(parents=True, exist_ok=True)
    z = dest / "sounds.zip"
    req = urllib.request.Request(url, headers={"User-Agent": "MotionLab"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r, open(z, "wb") as f:
            got = 0
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                got += len(chunk)
                if got > 500_000_000:
                    raise GenError("the file is bigger than 500 MB - not a sounds zip")
                f.write(chunk)
    except urllib.error.URLError as e:
        raise GenError(f"the link could not be downloaded: {getattr(e, 'reason', e)}") from None
    if not zipfile.is_zipfile(z):
        raise GenError("the link did not give a zip - share the file as 'Anyone with the link' on Google Drive")
    log(f"downloaded {z.stat().st_size / 1e6:.1f} MB")
    return z


def selfcheck() -> dict:
    """No network, no key: a test server in place of ElevenLabs (a click as its answer) -> two sounds generated into a
    temporary library with the free plan's licence; the free plan's cap; the share zip refused for free-plan sounds,
    made for paid ones and imported back by its list; a Drive link turned into its download address."""
    import http.server
    import tempfile
    import threading
    import numpy as np
    import soundfile as sf
    from . import sfx as SFX
    global API, KEYS, OUT, SHARE
    t0, lines, ok = time.time(), [], True

    def case(name, cond):
        nonlocal ok
        ok &= bool(cond)
        lines.append(("PASS " if cond else "FAIL ") + name)
    tmp = tempfile.TemporaryDirectory(prefix="ml_sfxgen_")
    td = Path(tmp.name)
    tb = np.arange(int(0.08 * 48000)) / 48000
    answers, seen = [], []                                  # (ElevenLabs makes another sound each time)
    for k, hz in enumerate((1800, 2300, 1400, 900)):
        x = np.concatenate([np.zeros(2400), np.sin(2 * np.pi * hz * tb) * np.exp(-tb / 0.01), np.zeros(4800)])
        sf.write(str(td / f"answer{k}.wav"), np.stack([x, x], 1), 48000, subtype="PCM_16")
        answers.append((td / f"answer{k}.wav").read_bytes())

    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):          # noqa: N802
            seen.append((self.path, self.headers.get("xi-api-key"),
                         json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)))))
            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.end_headers()
            self.wfile.write(answers[(len(seen) - 1) % len(answers)])

        def do_GET(self):           # noqa: N802 - the balance
            body = json.dumps({"character_count": 40 * len(seen), "character_limit": 10000, "tier": "free"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    old = API, KEYS, OUT, SHARE
    API, KEYS, OUT, SHARE = f"http://127.0.0.1:{srv.server_port}", td / "keys.json", td / "gen", td / "share"
    try:
        lib = td / "lib"
        save_settings("sk_test_0123456789abcdefghij", "free")
        r = generate({"pop": 2}, log=lambda *a, **k: None, root=lib)
        rows = json.loads((lib / "sounds.json").read_text(encoding="utf-8"))["sounds"]
        case("two pops made: the description, its length and the key sent; imported as pop with the free plan's "
             "licence", r["made"] == 2 and len(rows) == 2 and all(e["kind"] == "pop" for e in rows)
             and rows[0]["licence"] == LICENCE["free"] and seen[0][1] == "sk_test_0123456789abcdefghij"
             and seen[0][2]["duration_seconds"] == prompts()["kinds"]["pop"]["seconds"]
             and seen[0][0].startswith("/v1/sound-generation") and r["balance"]["used"] == 80
             and public()["balance"]["limit"] == 10000)
        try:
            generate({"riser": 600}, log=lambda *a, **k: None, root=lib)
            case("600 two-second risers refused on the free plan (12,000 credits)", False)
        except GenError:
            case("600 two-second risers refused on the free plan (12,000 credits)", True)
        try:
            share_zip(lib)
            case("the free plan's sounds never go into the zip for friends", False)
        except GenError:
            case("the free plan's sounds never go into the zip for friends", True)
        save_settings(plan="paid")
        generate({"whoosh": 1}, log=lambda *a, **k: None, root=lib)
        z = share_zip(lib)
        listing = unpack(Path(z["zip"]), td / "in")
        lib2 = td / "lib2"
        got = SFX.import_listed(td / "in", root=lib2, listing=listing)
        rows2 = json.loads((lib2 / "sounds.json").read_text(encoding="utf-8"))["sounds"]
        case("a paid-plan sound zipped for friends and imported back by its list: the same kind and licence, nothing "
             "else", z["count"] == 1 and len(got["added"]) == 1 and rows2[0]["kind"] == "whoosh"
             and rows2[0]["licence"] == LICENCE["paid"] and public()["key_end"] == "ghij" and "key" not in public())
        bad = td / "bad.zip"                                # (2026-10-26 review: names that point out of the folder)
        outside = (td / "outside.wav").resolve()
        with zipfile.ZipFile(bad, "w") as zf:
            zf.writestr("list.json", json.dumps({"sounds": []}))
            for nm in (outside.as_posix(), f"{outside.drive}outside2.wav", "../outside3.wav", "ok/inside.wav"):
                zf.writestr(nm, b"RIFF0000WAVE")
        unpack(bad, td / "in2")
        case("a zip's names with a drive letter, a drive-relative or a .. path never write outside its folder",
             not outside.exists() and not (td / "outside3.wav").exists() and (td / "in2" / "ok" / "inside.wav").exists())
        case("a Drive share link -> its direct download", drive_url(
            "https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrStUvWxYz012345/view?usp=sharing")
             == "https://drive.usercontent.google.com/download?id=1AbCdEfGhIjKlMnOpQrStUvWxYz012345&export=download"
                "&confirm=t")
    finally:
        srv.shutdown()
        API, KEYS, OUT, SHARE = old
        tmp.cleanup()
    return {"passed": ok, "seconds": round(time.time() - t0, 2), "lines": lines}
