"""The music library (0.6.0 step 10; the user, 2026-10-25: "a music library from the songs I download"): what a video
may play under it - the songs downloaded in the Analyser (refs\\audio: read where they are, never changed), songs the
user adds (library\\music\\) and ambience beds for under a talking video (library\\music\\ambience\\<kind>\\: added, or
made with ElevenLabs - `make_beds`, the described beds of tools\\sounds\\generate.json "beds"). Each file is measured
once - its length; a song's tempo, energy (onsets a second), tone (its spectral centroid) and drops - and
library\\music\\music.json keeps the measures (by the file's size + time) with the user's flags (★ = offered first,
hidden = never offered; the file stays). `bed_layer` = a bed under a voice: looped with a crossfade, BED_DB under the
voice's words, faded in and out (`sfx.py plan`, a plan's "sfx": {"bed": {"file", "db"}}).
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import tempfile
import time
from pathlib import Path

import numpy as np

from .util import LAB, load_config

ROOT = Path(os.environ.get("MOTIONLAB_MUSIC") or LAB / "library" / "music")      # (tests: a scratch folder)
SONGS = Path(os.environ.get("MOTIONLAB_SONGS") or LAB / "refs" / "audio")
DOWNLOADS = LAB / "refs" / "downloads.json"
AUDIO_EXT = (".mp3", ".m4a", ".wav", ".aac", ".flac", ".ogg", ".opus")
BEDS = ("room", "cafe", "city", "nature", "rain", "office")       # the kinds of bed (ambience\\<kind>\\)
BED_WORDS = {"room": ("room", "tone", "studio", "home"), "cafe": ("cafe", "café", "coffee", "restaurant", "bar"),
             "city": ("city", "street", "traffic", "urban"), "nature": ("nature", "forest", "bird", "wind", "park"),
             "rain": ("rain", "storm", "thunder"), "office": ("office", "work", "keyboard")}
BED_DB = -26.0           # a bed's loudness this far under the voice's words (dB; a room you hear, never a voice over it)
BED_FADE_S = 1.0         # its fade in and out
LOOP_XF_S = 0.5          # a bed shorter than the video: repeated, each join crossfaded (equal power)
ENERGY = ((1.5, "calm"), (4.0, "steady"), (math.inf, "energetic"))     # "busy" = the onset strength's mean (librosa's
#   spectral flux, in dB - the same at any volume) x onsets a second. Calibrated 2026-10-26: the user's 6 downloads
#   2.8-5.1 (flux 0.77-0.96, 2.9-6.1 onsets/s), a soft pad 0.31, a steady hum 0.08 - onsets/s alone called the hum
#   "energetic" (8.6 a second: the picker finds peaks in anything)
TONE = ((1600.0, "dark"), (2600.0, "warm"), (math.inf, "bright"))      # the spectral centroid in Hz (the 6: 2045-2277)
MEASURE_V = 2            # a measure older than this is made again


def rel(p: Path) -> str:
    try:
        return Path(p).resolve().relative_to(LAB.resolve()).as_posix()
    except ValueError:
        return str(Path(p).resolve())


def path_of(r: str) -> Path:
    p = Path(r)
    return p if p.is_absolute() else LAB / p


def _junk(p: Path) -> bool:
    from .project import is_junk
    return is_junk(p)


def bed_kind(p: Path) -> str:
    """A bed's kind: its folder under ambience\\ when that is a kind, else a word of its name, else room."""
    parts = [x.lower() for x in p.parts]
    for i, x in enumerate(parts[:-1]):
        if x == "ambience" and i + 1 < len(parts) - 1 and parts[i + 1] in BEDS:
            return parts[i + 1]
    name = p.stem.lower()
    return next((k for k, ws in BED_WORDS.items() if any(w in name for w in ws)), "room")


def scan() -> list[dict]:
    """Every file the library holds: the downloaded songs, the songs added, the beds - {path, type, kind}."""
    out = []
    if SONGS.is_dir():
        out += [{"path": p, "type": "song", "kind": ""} for p in sorted(SONGS.iterdir())
                if p.is_file() and p.suffix.lower() in AUDIO_EXT and not _junk(p)]
    if ROOT.is_dir():
        for p in sorted(ROOT.rglob("*")):
            if not p.is_file() or p.suffix.lower() not in AUDIO_EXT or _junk(p) or p.name.endswith(".part"):
                continue
            bed = p.relative_to(ROOT).parts[0].lower() == "ambience"
            out.append({"path": p, "type": "bed" if bed else "song", "kind": bed_kind(p) if bed else ""})
    return out


def _db() -> dict:
    try:
        d = json.loads((ROOT / "music.json").read_text(encoding="utf-8"))
        return d if isinstance(d.get("tracks"), dict) else {"tracks": {}}
    except (OSError, ValueError):
        return {"tracks": {}}


def _save(d: dict) -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    d["_comment"] = ("MotionLab's music library (motionlab\\music.py): per file (lab-relative) its measures - kept "
                     "while its size and time stay the same - and the user's flags (fav, off); made = an ElevenLabs "
                     "bed's description and licence. The files are never changed.")
    tmp = ROOT / "music.json.part"
    tmp.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(ROOT / "music.json")


def _stamp(p: Path) -> list:
    st = p.stat()
    return [st.st_size, int(st.st_mtime)]


def words(x: float, table) -> str:
    return next(w for lim, w in table if x < lim)


def measure(p: Path, typ: str = "song") -> dict:
    """One file, read only: its length; a song's tempo, onsets a second (-> energy), spectral centroid (-> tone) and
    drops (the lab's own beat analysis, motionlab\\audio.py)."""
    import soundfile as sf
    from . import audio as AU
    cfg = load_config()["audio"]
    sr = int(cfg["sample_rate"])
    tmp_root = LAB / ".app" / "tmp"
    tmp_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=tmp_root) as tmp:
        wav = Path(tmp) / "a.wav"
        if not AU.extract_wav(p, wav, sr):
            raise ValueError(f"no sound found in {p.name}")
        dur = float(sf.info(str(wav)).duration)
        out = {"v": MEASURE_V, "len_s": round(dur, 2)}
        if typ != "song":
            return out
        A = AU.analyze_core(wav, 30.0, 0.0, cfg)
        if not A.get("available"):
            return {**out, "why": A.get("reason", "no beats found")}
        import librosa
        y, s = sf.read(str(wav), dtype="float32", always_2d=False)
        y = y.mean(axis=1) if y.ndim > 1 else y
        cen = librosa.feature.spectral_centroid(y=y, sr=s, hop_length=512)[0]
        rms = librosa.feature.rms(y=y, hop_length=512)[0]
        n = min(len(cen), len(rms))
        w = rms[:n] ** 2
        centroid = float((cen[:n] * w).sum() / max(float(w.sum()), 1e-12))
    ons = len(A.get("onsets") or []) / max(dur, 1e-6)
    flux = float(np.mean(A["_series"]["oenv"]))
    return {**out, "bpm": round(float(A["bpm"]), 1), "onsets_s": round(ons, 2), "flux": round(flux, 3),
            "busy": round(flux * ons, 2), "centroid_hz": round(centroid), "drops": len(A.get("drops") or []),
            "energy": words(flux * ons, ENERGY), "tone": words(centroid, TONE)}


def index(log=print, only: list[str] | None = None) -> dict:
    """Measure every file not measured yet (or changed since) -> music.json. -> {"measured", "kept", "failed"}."""
    d = _db()
    T = d["tracks"]
    out = {"measured": [], "kept": 0, "failed": []}
    for it in scan():
        r = rel(it["path"])
        if only and r not in only:
            continue
        row = T.setdefault(r, {})
        if row.get("stamp") == _stamp(it["path"]) and (row.get("m") or {}).get("v") == MEASURE_V:
            out["kept"] += 1
            continue
        t0 = time.time()
        try:
            m = measure(it["path"], it["type"])
        except Exception as e:                           # one file that cannot be read never stops the rest
            out["failed"].append(f"{it['path'].name}: {e}")
            log(f"  {it['path'].name}: not measured - {e}")
            continue
        row.update(stamp=_stamp(it["path"]), m=m)
        out["measured"].append(r)
        log(f"  {it['path'].name}: " + (f"{m['bpm']:g} BPM, {m['energy']}, {m['tone']}, {m['len_s']:.0f} s"
                                         if "bpm" in m else f"{m['len_s']:.1f} s") + f"  ({time.time() - t0:.1f} s)")
        _save(d)                                         # each one kept as it is measured (a cancel keeps the rest)
    _save(d)
    return out


def _downloads() -> dict:
    try:
        d = json.loads(DOWNLOADS.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def name_of(p: Path) -> tuple[str, str]:
    """(title, artist) from a file name: "Artist - Title [id].mp3" - yt-dlp's [id] and other [tags] at the end off."""
    stem = re.sub(r"(\s*\[[^\]]*\])+$", "", p.stem).replace("_", " ").strip() or p.stem
    if " - " in stem:
        a, t = stem.split(" - ", 1)
        return t.strip(), a.strip()
    return stem, ""


def origin(p: Path, row: dict, dl: dict) -> tuple[str, str]:
    """(where it came from, its licence in words)."""
    made = row.get("made") or {}
    if made:
        return "ElevenLabs", made.get("licence", "")
    if p.parent.resolve() == SONGS.resolve():
        e = dl.get(p.name) or {}
        url = str(e.get("url") or "")
        site = e.get("platform") or (re.sub(r"^www\.", "", url.split("/")[2]) if url.count("/") >= 2 else "")
        site = {"youtube": "YouTube", "tiktok": "TikTok", "soundcloud": "SoundCloud"}.get(str(site).lower(), site)
        if "pixabay" in url:
            return "Pixabay", "Pixabay Content License: free to use, also in videos you post"
        return (site or "a download"), ("downloaded: not yours to post - the copy to post leaves it out, you add the "
                                        "song in the app")
    return "your file", "your own file"


def state() -> dict:
    """The page's library: every file with its measures, names, where it came from and the flags."""
    d, dl = _db(), _downloads()
    rows = []
    for it in scan():
        p, r = it["path"], rel(it["path"])
        row = d["tracks"].get(r) or {}
        m = row.get("m") if row.get("stamp") == _stamp(p) else None
        title, artist = name_of(p)
        made = row.get("made") or {}
        if made.get("text"):
            title = " ".join(made["text"].split()[:5]).rstrip(",:") + "…"
        frm, lic = origin(p, row, dl)
        rows.append({"rel": r, "type": it["type"], "kind": it["kind"], "title": title, "artist": artist,
                     "from": frm, "licence": lic, "fav": bool(row.get("fav")), "off": bool(row.get("off")),
                     "made": bool(made), "measured": bool(m), **({k: v for k, v in (m or {}).items() if k != "v"})})
    rows.sort(key=lambda x: (x["type"] != "song", not x["fav"], x["off"], x["title"].lower()))
    return {"tracks": rows, "unmeasured": sum(1 for x in rows if not x["measured"]), "beds": list(BEDS)}


def get(r: str) -> dict | None:
    return next((x for x in state()["tracks"] if x["rel"] == r), None)


def set_flags(r: str, off=None, fav=None) -> dict:
    """A favourite (offered first) / hidden (never offered; the file stays) - music.json only."""
    if not any(rel(it["path"]) == r for it in scan()):
        raise ValueError(f"no file {r[:80]} in the music library")
    d = _db()
    row = d["tracks"].setdefault(r, {})
    for k, v in (("off", off), ("fav", fav)):
        if v is None:
            continue
        if v:
            row[k] = True
        else:
            row.pop(k, None)
    _save(d)
    return {"rel": r, **{k: bool(row.get(k)) for k in ("off", "fav")}}


def free_name(folder: Path, name: str) -> Path:
    """A new file's place: the name as it is, or "name (2)" - never over a file."""
    base = re.sub(r"[^\w.\- ()&'+,\[\]]", "_", Path(name).name).strip(" .")[:120] or "music.mp3"
    p, j = folder / base, 2
    while p.exists() or p.with_name(p.name + ".part").exists():
        p, j = folder / f"{Path(base).stem} ({j}){Path(base).suffix}", j + 1
    return p


def target(typ: str = "song", kind: str = "") -> Path:
    """Where an added file goes: library\\music\\ (a song) or library\\music\\ambience\\<kind>\\ (a bed)."""
    if typ == "bed":
        if kind not in BEDS:
            raise ValueError(f"not a kind of bed: {kind!r} (kinds: {', '.join(BEDS)})")
        return ROOT / "ambience" / kind
    return ROOT


def add(src: Path, typ: str = "song", kind: str = "") -> Path:
    """A copy of a file the user adds (the original is only read) into the library - a new name, never over a file."""
    src = Path(src)
    if src.suffix.lower() not in AUDIO_EXT or _junk(src):
        raise ValueError(f"{src.name}: not a sound file ({', '.join(AUDIO_EXT)})")
    folder = target(typ, kind)
    folder.mkdir(parents=True, exist_ok=True)
    dst = free_name(folder, src.name)
    shutil.copyfile(src, dst)
    return dst


# ------------------------------------------------------------------------------------------- a bed under a voice
def _loop(x: np.ndarray, n: int, sr: int) -> np.ndarray:
    """x repeated to n samples, each join crossfaded over LOOP_XF_S (equal power)."""
    if len(x) >= n:
        return x[:n].copy()
    xf = max(1, min(int(LOOP_XF_S * sr), len(x) // 3))
    t = np.linspace(0, np.pi / 2, xf)[:, None]
    out = x.copy()
    while len(out) < n:
        a, b = out[-xf:] * np.cos(t), x[:xf] * np.sin(t)
        out = np.concatenate([out[:-xf], a + b, x[xf:]])
    return out[:n]


def bed_layer(voice: np.ndarray | None, bed: Path, n: int, db: float = BED_DB, fade_s: float = BED_FADE_S) -> tuple:
    """The bed for a video of n samples (stereo at sfx.SR): looped, its loudness `db` under the voice's words (the
    voice's speech steps, motionlab\\sfx.py; no words found = under the voice's own loudness), faded in and out.
    -> (the bed, {"db_vs_voice", "voice_db", "bed_db"})."""
    from . import sfx as SFX
    sr = SFX.SR
    x = SFX.load_audio(Path(bed))
    if not len(x):
        raise ValueError(f"{Path(bed).name}: no sound in it")
    y = _loop(x, n, sr)
    vdb = None
    if voice is not None and len(voice):
        sp, lvl = SFX.speech_steps(voice[:n])
        vdb = SFX.voice_level(sp, lvl, 0, len(sp)) if sp.any() else SFX.rms_db(voice[:n])
    vdb = -20.0 if vdb is None else vdb                  # (no voice: a talking level)
    bdb = SFX.rms_db(y)
    g = 10 ** ((vdb + db - bdb) / 20)
    y = y * g
    f = min(int(fade_s * sr), n // 3)
    if f > 1:
        ramp = np.linspace(0, 1, f)[:, None]
        y[:f] *= ramp
        y[-f:] *= ramp[::-1]
    return y, {"db_vs_voice": db, "voice_db": round(vdb, 2), "bed_db": round(SFX.rms_db(y), 2)}


# ------------------------------------------------------------------------------- beds made with ElevenLabs
def bed_prompts() -> dict:
    from . import sfxgen as GEN
    return GEN.prompts().get("beds") or {}


def make_beds(want: dict[str, int], log=print, dry: bool = False) -> dict:
    """want = {bed kind: how many}: each made from the kind's descriptions in turn (ElevenLabs' loop = no seam), the
    answer kept in .app\\sound_gen\\<time>\\beds\\ and copied into library\\music\\ambience\\<kind>\\ with the plan's
    licence (music.json "made"). -> {"made", "files", "credits"}."""
    from . import sfxgen as GEN
    s, B = GEN.settings(), bed_prompts()
    bad = [k for k in want if k not in B or k not in BEDS]
    if bad:
        raise GEN.GenError(f"no bed descriptions for {', '.join(bad)} (tools\\sounds\\generate.json \"beds\")")
    need = sum(GEN.cost(B[k].get("seconds", 15)) * max(0, int(v)) for k, v in want.items())
    out = {"made": 0, "files": [], "credits": need if dry else 0}
    if dry:
        return out
    if not s["key"]:
        raise GEN.GenError("no ElevenLabs key yet - add yours in Motion Graphics > Sounds > Make sounds")
    if s["plan"] == "free" and need > GEN.FREE_CREDITS:
        raise GEN.GenError(f"about {need} credits: the free plan has {GEN.FREE_CREDITS} a month - ask for fewer")
    P = GEN.prompts()
    infl = float(P.get("prompt_influence", 0.45))
    model, fmt = str(P.get("model") or ""), str(P.get("format") or "mp3_44100_128")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    d = _db()
    for kind, n in want.items():
        spec = B[kind]
        for i in range(max(0, int(n))):
            text = spec["prompts"][i % len(spec["prompts"])]
            log(f"{kind} bed {i + 1} of {n}: \"{text[:70]}\"")
            audio = GEN._post(s["key"], text, float(spec.get("seconds", 15)), infl, model, fmt, loop=True)
            out["credits"] += GEN.cost(spec.get("seconds", 15))
            ext = "wav" if fmt.startswith("wav") else "mp3"
            keep = GEN.OUT / stamp / "beds" / f"{kind}_el_{stamp[-6:]}_{i + 1:02d}.{ext}"
            keep.parent.mkdir(parents=True, exist_ok=True)
            keep.write_bytes(audio)
            dst = add(keep, "bed", kind)
            d["tracks"].setdefault(rel(dst), {})["made"] = {"text": text, "licence": GEN.LICENCE[s["plan"]],
                                                            "date": time.strftime("%Y-%m-%d")}
            _save(d)
            out["made"] += 1
            out["files"].append(rel(dst))
    out["balance"] = GEN.balance(s["key"])
    return out


# ---------------------------------------------------------------------------------------------------- self-check
def selfcheck(verbose: bool = True) -> dict:
    """A scratch library (no network): a 120 BPM click song with bright hats and a slow dark hum are measured apart;
    flags kept; an added file never over another; names from a download's file name; a bed under a voice sits
    BED_DB under the words and loops past its own length with no gap."""
    global ROOT, SONGS
    from . import sfx as SFX
    import soundfile as sf
    lines, ok = [], True

    def case(name, good, detail=""):
        nonlocal ok
        ok &= bool(good)
        lines.append(f"{'PASS' if good else 'FAIL'} {name}" + (f": {detail}" if detail else ""))
    old = ROOT, SONGS
    tmp_root = LAB / ".app" / "tmp"
    tmp_root.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(dir=tmp_root) as tmp:
            ROOT, SONGS = Path(tmp) / "music", Path(tmp) / "audio"
            SONGS.mkdir(parents=True)
            sr = 44100
            t = np.arange(int(12 * sr)) / sr
            rng = np.random.default_rng(3)
            song = np.zeros_like(t)                                    # kicks every 0.5 s + hats every 0.125 s
            for k in np.arange(0, 12, 0.5):
                i = int(k * sr)
                song[i:i + 4000] += np.sin(2 * np.pi * 60 * t[:4000]) * np.exp(-t[:4000] * 30)
            for k in np.arange(0.25, 12, 0.125):
                i = int(k * sr)
                song[i:i + 800] += rng.standard_normal(800) * np.exp(-np.arange(800) / 150) * 0.5
            sf.write(str(SONGS / "Some Artist - Bright Song [abcdefghijk].wav"), song * 0.5, sr)
            hum = (np.sin(2 * np.pi * 80 * t) + 0.3 * np.sin(2 * np.pi * 160 * t)) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.1 * t))
            sf.write(str(SONGS / "slow hum.wav"), hum * 0.3, sr)
            r = index(log=lambda *_: None)
            S = {x["title"]: x for x in state()["tracks"]}
            b, h = S.get("Bright Song", {}), S.get("slow hum", {})
            case("two songs measured: a 120 BPM click song is energetic and bright, a slow hum calm and dark",
                 len(r["measured"]) == 2 and abs(b.get("bpm", 0) - 120) < 3 and b.get("artist") == "Some Artist"
                 and b.get("energy") in ("steady", "energetic") and b.get("tone") == "bright"
                 and h.get("tone") == "dark" and h.get("energy") == "calm",
                 f"{b.get('bpm')} BPM {b.get('energy')} {b.get('tone')} {b.get('centroid_hz')} Hz | hum "
                 f"{h.get('energy')} {h.get('tone')} {h.get('centroid_hz')} Hz")
            r2 = index(log=lambda *_: None)
            set_flags(b["rel"], fav=True)
            set_flags(h["rel"], off=True)
            S2 = {x["title"]: x for x in state()["tracks"]}
            case("measured once (a second pass measures nothing); favourite and hidden kept, the favourite first",
                 not r2["measured"] and r2["kept"] == 2 and S2["Bright Song"]["fav"] and S2["slow hum"]["off"]
                 and state()["tracks"][0]["title"] == "Bright Song")
            one = add(SONGS / "slow hum.wav", "bed", "room")
            two = add(SONGS / "slow hum.wav", "bed", "room")
            case("an added bed is a copy under ambience\\room\\, a second one gets a new name",
                 one.parent == ROOT / "ambience" / "room" and two.name == "slow hum (2).wav"
                 and bed_kind(ROOT / "ambience" / "cafe" / "x.wav") == "cafe" and bed_kind(Path("rain_loop.wav")) == "rain")
            n = int(6 * SFX.SR)                                        # a voice: 0.4 s words, 0.3 s pauses
            v = np.zeros((n, 2))
            tt = np.arange(n) / SFX.SR
            on = (tt % 0.7) < 0.4
            v[on] = (np.sin(2 * np.pi * 220 * tt[on]) * 0.3)[:, None]
            bed = Path(tmp) / "bed.wav"
            sf.write(str(bed), rng.standard_normal((int(2 * SFX.SR), 2)) * 0.05, SFX.SR)   # 2 s, shorter than 6 s
            y, info = bed_layer(v, bed, n)
            mid = y[int(1.5 * SFX.SR):int(4.5 * SFX.SR)]
            sp, lvl = SFX.speech_steps(v)
            words_db = SFX.voice_level(sp, lvl, 0, len(sp))
            gap = np.convolve(np.abs(mid).mean(1), np.ones(480) / 480, "valid").min()
            case(f"a bed under a voice: {BED_DB:g} dB under its words, looped past its 2 s with no gap, faded in",
                 len(y) == n and abs((SFX.rms_db(y) - words_db) - BED_DB) < 1.5 and gap > 0.002 and abs(y[0]).max() < 1e-6,
                 f"{SFX.rms_db(y) - words_db:+.1f} dB vs the words; the quietest 10 ms in the middle {gap:.4f}")
    finally:
        ROOT, SONGS = old
    if verbose:
        for ln in lines:
            print(ln)
    return {"passed": ok, "lines": lines}
