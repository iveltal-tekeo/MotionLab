"""A quick first edit of a project's clips in a style - by rules, in minutes, no Claude needed (0.4, Edit > Quick
draft). Claude starts from it for an edit by feel (/recreate-video feel:...); the app runs it as a job.

    .venv\\Scripts\\python tools\\draft_edit.py <project> --like <video> [<video> <video>]   the style of up to 3
                                                                                         analysed videos
    .venv\\Scripts\\python tools\\draft_edit.py <project> --preset fast_hook [--want "3 s cuts, captions"]
    .venv\\Scripts\\python tools\\draft_edit.py <project> --feel raw [--want "..."]       a feel (style.py --feels)
    .venv\\Scripts\\python tools\\draft_edit.py --presets                                 the presets
    .venv\\Scripts\\python tools\\draft_edit.py <project> --feel-test [--want "..."] [--like <video>] [--preset id]
                        [--feels slick,raw,cinematic] [--length 3] [--size 360]
                      starting blind (0.4.2): 2-3 hooks (the first 3 s) in DIFFERENT feels - Clean & slick / Raw &
                      glitchy / Slow & cinematic / Fast & punchy / Calm & steady (the words pick which; --like and
                      each --preset take a place too) - by the same rules, no Claude, rendered small into
                      build\\feel\\feel_N\\: A_<feel>.mp4 ..., compare.mp4 (A | B | C side by side) + sheet.png, every
                      tile labelled with its feel and frame + timecode; feel.md (each hook's shots and effects with
                      frame + timecode, the full-length command). The user picks or mixes ("B's pacing with A's
                      colours") - that is the plan. ~10-20 s once the frame caches exist.
  --length 30         seconds (default: the style's typical length; at most the music / what is said)
  --format vertical   vertical | horizontal | square (default: the style's, else the clips')
  --music <file>      an audio file in the project folder (a name, or a path; "none" = no music; default: the only
                      or first one there)
  --music-start auto  seconds into the song (auto: the strongest part - a drop - comes right after the hook)
  --sound auto        music | clips (the clips' own sound, shot by shot) | talk (the clips' own sound in order, the
                      pauses cut out; 0.5.3: the voice levelled to -26 dBFS RMS, one gain per take, peaks under
                      -1 dBFS - `--per-shot` = per shot); auto = talk for a talking style, else music when there is a
                      song, else clips
  --colour match      match: the footage moved toward the references' colour (a .cube, build\\colour\\match_vN.cube -
                      also for DaVinci Resolve) | grade: the style's starting grade only | none
  --seed 1            another seed = another draft from the same rules
  --render            render <project>_vN.mp4 too; the frame caches (prep_footage.py) are made first when missing
Writes only into projects\\<project>\\build\\: plan_vN.json (a normal plan: render_video.py renders it, Claude refines
it, resolve_build builds it), draft_vN.md (the style aimed for; every shot with frame + timecode, its clip and where
in it, why that moment; the effects; what the draft cannot draw), draft\\ (the music's beats, the edit's sound). The
clips and the music are only read (hard rule 1); the last line printed is the render (or the plan).
"""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import audio as AU  # noqa: E402
from motionlab import draft as DR  # noqa: E402
from motionlab import footage as FC  # noqa: E402
from motionlab import style as ST  # noqa: E402
from motionlab import taxonomy  # noqa: E402
from motionlab.probe import probe  # noqa: E402
from motionlab.project import Project  # noqa: E402
from motionlab.timecode import frame_to_tc  # noqa: E402
from motionlab.util import LAB, load_config, log, read_json, setup_console, tool, write_json  # noqa: E402

TOOLS = Path(__file__).resolve().parent
AUDIO_EXT = {".mp3", ".m4a", ".wav", ".aac", ".flac", ".ogg"}
SR = 48000


def next_version(b: Path, name: str) -> int:
    ns = [0]
    for p in [*b.glob("plan_v*.json"), *b.glob("edit_v*.py"), *b.glob("draft_v*.md"), *b.glob(f"{name}_v*.mp4")]:
        m = re.search(r"_v(\d+)", p.stem)
        if m:
            ns.append(int(m.group(1)))
    return max(ns) + 1


def find_music(prj: Project, arg: str | None) -> tuple[Path | None, str | None]:
    if arg and arg.lower() == "none":
        return None, None
    if arg:
        p = Path(arg)
        if not p.is_absolute():
            p = next((c for c in (prj.dir / arg, LAB / "refs" / "audio" / arg, Path.cwd() / arg) if c.is_file()), p)
        if not p.is_file():
            raise SystemExit(f"music not found: {arg} (put the song into {prj.dir} or give its path)")
        return p.resolve(), None
    found = sorted(f for f in prj.dir.iterdir() if f.is_file() and f.suffix.lower() in AUDIO_EXT)
    if not found:
        return None, None
    return found[0], (f"{len(found)} songs in the folder - took {found[0].name} (another one: --music <name>)"
                      if len(found) > 1 else None)


def _key(p: Path, *extra) -> str:
    st = p.stat()
    return hashlib.sha1(f"{p.resolve()}|{st.st_size}|{st.st_mtime_ns}|{extra}".encode()).hexdigest()[:10]


def decode(src: Path, dst: Path) -> bool:
    """The sound of a file as 48 kHz stereo 16-bit WAV (False when it has none)."""
    if dst.exists():
        return True
    r = subprocess.run([tool("ffmpeg"), "-y", "-v", "error", "-nostdin", "-i", str(src), "-map", "0:a:0", "-vn",
                        "-ac", "2", "-ar", str(SR), "-c:a", "pcm_s16le", str(dst)], capture_output=True)
    if r.returncode or not dst.exists() or dst.stat().st_size < 1000:
        dst.unlink(missing_ok=True)
        return False
    return True


def music_info(prj: Project, d: Path, m: Path, fps: float, cfg: dict) -> dict:
    """Beats, downbeats and drops of the song (timeline frames from the song's start), cached in build\\draft\\."""
    k = _key(m, fps)
    js = d / f"music_{k}.json"
    if js.exists():
        return read_json(js)
    wav = prj.check(d / f"music_{k}.wav")
    if not decode(m, wav):
        raise SystemExit(f"{m.name}: no sound found")
    import soundfile as sf
    dur = float(sf.info(str(wav)).duration)
    info = {"file": str(m), "wav": str(wav), "duration_s": round(dur, 3), "bpm": None, "beats": [], "downbeats": [],
            "drops": [], "note": None}
    mono = prj.check(d / f"music_{k}_mono.wav")
    try:
        if AU.extract_wav(m, mono, int(cfg["audio"]["sample_rate"])):
            A = AU.analyze(mono, fps, int(dur * fps) + 1, 0.0, cfg["audio"])
            if A.get("available"):
                info.update({"bpm": A["bpm"], "beats": [b["frame"] for b in A["beats"]],
                             "downbeats": [b["frame"] for b in A["beats"] if b.get("downbeat")],
                             "drops": [x["frame"] for x in A.get("drops", [])]})
    except AU.VCRedistMissing as e:
        info["note"] = f"no beats: {e}"
    finally:
        mono.unlink(missing_ok=True)
    write_json(prj.check(js), info)
    return info


def music_start(info: dict, T: float, fps: float, arg: str | None) -> float:
    if arg not in (None, "", "auto"):
        return max(0.0, float(arg))
    if info["duration_s"] <= T * 1.5 or not info["drops"]:
        return 0.0
    beats = [b / fps for b in info["beats"]]
    for dfr in info["drops"]:
        s0 = dfr / fps - min(4.0, T / 4)                 # the drop lands right after the hook
        if s0 >= 4.0 and s0 + T <= info["duration_s"]:
            return round(min(beats, key=lambda b: abs(b - s0)) if beats else s0, 3)
    return 0.0


def speech(wav: Path, fps: float, n: int, offset_s: float) -> list[tuple[int, int]] | None:
    """Spoken parts of a clip (cache frames): loud 10 ms windows, pauses under 0.25 s kept, 0.08 s around each part;
    None when nobody talks (B-roll). offset_s = the video's start minus the sound's (video time = wav time - it)."""
    import soundfile as sf
    y, sr = sf.read(str(wav), dtype="float32", always_2d=True)
    y = y.mean(axis=1)
    hop = sr // 100
    m = len(y) // hop
    if m < 20:
        return None
    rms = np.sqrt(np.mean(y[:m * hop].reshape(m, hop) ** 2, axis=1))
    db = 20 * np.log10(rms + 1e-9)
    if float(np.percentile(db, 95)) < -45:
        return None
    v = db > max(float(np.percentile(db, 90)) - 22, -48)
    runs, i = [], 0
    while i < m:                                          # runs of voiced windows
        if v[i]:
            j = i
            while j < m and v[j]:
                j += 1
            runs.append([i, j])
            i = j
        else:
            i += 1
    merged = []
    for a, b in runs:                                     # a pause under 0.25 s is part of the sentence
        if merged and a - merged[-1][1] < 25:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    out = []
    for a, b in merged:
        if b - a < 20:
            continue
        t0, t1 = max(0.0, a / 100 - 0.08) - offset_s, b / 100 + 0.08 - offset_s
        f0, f1 = max(0, int(np.floor(t0 * fps))), min(n - 1, int(np.ceil(t1 * fps)) - 1)
        if out and f0 <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], f1))
        elif f1 - f0 + 1 >= int(0.4 * fps):
            out.append((f0, f1))
    total = sum(b - a + 1 for a, b in out)
    return out if total >= min(0.2 * n, 3 * fps) else None


def ensure_caches(prj: Project, W: int, H: int) -> None:
    files = prj.footage_files()
    if not files:
        raise SystemExit(f"no clips in {prj.dir} - copy your videos into that folder first")
    metas = []
    for p in prj.cache.glob("*.json") if prj.cache.exists() else []:
        m = read_json(p) or {}
        if m.get("id") and m.get("complete"):
            metas.append(m)
    done = {str(Path(m["source"]).resolve()).lower() for m in metas}
    missing = [f for f in files if str(f.resolve()).lower() not in done]
    if not missing:
        return
    size = next((m["out_size"] for m in metas if m.get("out_size")), [W, H])
    fps = next((m["fps"] for m in metas if m.get("fps")), 25.0)
    log(f"frame caches first ({len(missing)} clip(s); made once, later edits reuse them)")
    r = subprocess.run([sys.executable, str(TOOLS / "prep_footage.py"), str(prj.dir), "--width", str(size[0]),
                        "--height", str(size[1]), "--fps", f"{fps:g}"])
    if r.returncode:
        raise SystemExit("prep_footage.py failed (see above)")


def load_clips(prj: Project) -> tuple[dict, list[dict], bool]:
    try:
        srcs, color = FC.plan_sources(prj.build, True), True
    except SystemExit:
        srcs, color = FC.plan_sources(prj.build, False), False
    clips = []
    for sid, s in srcs.items():
        meta = read_json(FC.paths(prj.cache, sid, color)[1])
        st = dict(np.load(prj.cache / f"{sid}_stats.npz"))
        clips.append({"id": sid, "name": Path(s["source"]).name, "source": s["source"], "frames": int(s["frames"]),
                      "fps": float(meta["fps"]), "src_fps": float(meta.get("src_fps") or meta["fps"]),
                      "w": meta.get("src_width"), "h": meta.get("src_height"), "stats": st})
    return srcs, clips, color


def orientation(w, h) -> str:
    return "vertical" if h > w * 1.15 else "horizontal" if w > h * 1.15 else "square"


VOICE_DB, VOICE_PEAK_DB = -26.0, -1.0     # a talking video's voice: RMS target, the highest a peak may go


def level_voice(out: list, segs: list, per_shot: bool = False) -> list[str]:
    """0.5.3 (A9): a talking video's voice at one level before the sound effects (local-make-3: a hook from one take
    at -28 dBFS and the rest from another at -35 to -40 - a 9-12 dB jump at the first cut, and sfx.py levels every
    effect against the voice under it). One gain per take (clip) - the user's rule, 2026-10-16 - or per shot: its
    RMS brought to VOICE_DB, never a peak over VOICE_PEAK_DB. In place; returns a line per take / shot."""
    groups: dict = {}
    for k, (sid, a, b) in enumerate(segs):
        groups.setdefault(k if per_shot else sid, []).append(k)
    lines = []
    for key, ks in groups.items():
        y = np.concatenate([out[k] for k in ks]) if ks else np.zeros((0, 2), np.float32)
        if not len(y) or float(np.abs(y).max()) < 1e-4:
            continue
        rms = 20 * np.log10(max(float(np.sqrt(np.mean(y.astype(np.float64) ** 2))), 1e-9))
        peak = 20 * np.log10(float(np.abs(y).max()))
        g = min(VOICE_DB - rms, VOICE_PEAK_DB - peak)
        for k in ks:
            out[k] *= np.float32(10 ** (g / 20))
        sid, a, b = segs[ks[0]]
        lines.append(f"{'shot ' + str(key) + ' (' + sid + ')' if per_shot else 'take ' + sid}: {rms:.1f} dBFS -> "
                     f"{rms + g:.1f} ({g:+.1f} dB{', held by its peak' if g < VOICE_DB - rms - 0.05 else ''})")
    return lines


def cut_sound(segs: list, clips: dict, fps: float, d: Path, level: str | None = None) -> np.ndarray:
    """The clips' own sound for the shots, frame-exact, 8 ms fades at each cut (silence where a clip has none).
    level "take" / "shot" = a talking video's voice levelled (level_voice) - the levels are printed."""
    import soundfile as sf
    out, fade = [], int(0.008 * SR)
    ramp = np.linspace(0, 1, fade, dtype=np.float32)[:, None]
    cache: dict = {}
    for sid, a, b in segs:
        c = clips[sid]
        n = int(round((b - a + 1) / fps * SR))
        seg = np.zeros((n, 2), np.float32)
        if c.get("wav"):
            if sid not in cache:
                cache[sid] = sf.read(c["wav"], dtype="float32", always_2d=True)[0]
            y = cache[sid]
            s0 = int(round((a / fps + c["offset_s"]) * SR))
            lo, hi = max(0, s0), min(len(y), s0 + n)
            if hi > lo:
                seg[lo - s0:hi - s0] = y[lo:hi, :2] if y.shape[1] >= 2 else np.repeat(y[lo:hi], 2, axis=1)
        if n > 2 * fade:
            seg[:fade] *= ramp
            seg[-fade:] *= ramp[::-1]
        out.append(seg)
    if level and out:
        for ln in level_voice(out, segs, per_shot=level == "shot"):
            log(f"voice levelled: {ln}")
    return np.concatenate(out) if out else np.zeros((0, 2), np.float32)


def write_sound(prj: Project, d: Path, v, y: np.ndarray, stem: str | None = None) -> Path:
    import soundfile as sf
    stem = stem or f"v{v}_sound"
    wav, m4a = prj.check(d / f"{stem}.wav"), prj.check(d / f"{stem}.m4a")
    sf.write(str(wav), np.clip(y, -1, 1), SR, subtype="PCM_16")
    r = subprocess.run([tool("ffmpeg"), "-y", "-v", "error", "-nostdin", "-i", str(wav), "-c:a", "aac", "-b:a", "192k",
                        str(m4a)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    wav.unlink(missing_ok=True)
    if r.returncode:
        raise SystemExit(f"could not encode the sound: {r.stderr[-400:]}")
    return m4a


def match_colour(prj: Project, v: int, clips: list[dict], style: dict, strength: float) -> tuple[dict, str]:
    """The footage's colour (6 frames a clip) moved toward the references' (style "lab") - a match LUT for the plan's
    grade and for DaVinci Resolve, with how close the looks are before / after (colour.closeness, 0-100)."""
    from motionlab import colour as CO
    px = []
    for c in clips:
        m, arr = FC.load(prj.cache, c["id"])
        for i in np.linspace(c["frames"] * 0.1, c["frames"] * 0.9, 6).astype(int):
            im = FC.image(m, arr, int(i))
            im = im if im.ndim == 3 else np.repeat(im[..., None], 3, axis=2)
            px.append(cv2.resize(im, (160, max(1, int(160 * im.shape[0] / im.shape[1]))),
                                 interpolation=cv2.INTER_AREA).reshape(-1, 3))
    px = np.concatenate(px)
    src, ref = CO.lab_stats(px), style["lab"]
    lut = CO.match_lut(src, ref, 33, strength)
    out = prj.check(prj.build / "colour" / f"match_v{v}.cube")
    out.parent.mkdir(parents=True, exist_ok=True)
    CO.write_cube(out, lut, f"MotionLab match {prj.name} v{v}")
    after = CO.lab_stats(CO.apply_lut(px.reshape(-1, 1, 3), lut))
    return ({**DR.NEUTRAL, "lut3d": str(out)},
            f"matched to the references' colour - closeness {CO.closeness(src, ref):g} -> {CO.closeness(after, ref):g} "
            f"of 100 (build\\colour\\match_v{v}.cube, also for DaVinci Resolve's Color page)")


def notes(prj, v, style, D, clips, fps, W, H, orient, sound_line, music_note, args_line, colour_line=None) -> str:
    tc = lambda f: frame_to_tc(f, fps)  # noqa: E731
    N = D["frames"]
    L = [f"# Draft v{v} of {prj.name} - {ST.summary(style)}", "",
         f"Made by `tools\\draft_edit.py` ({time.strftime('%Y-%m-%d %H:%M')}) by rules, no Claude: {N} frames = "
         f"{N / fps:.1f} s at {fps:g} fps, {W}x{H} ({orient}), {len(D['shots'])} shots, {len(D['effects'])} effects. "
         f"Frames are 0-based (f0 = 00:00:00:00); a Resolve timeline starts at 01:00:00:00.", "",
         f"- Sound: {sound_line}"] + ([f"- {music_note}"] if music_note else []) + (
         [f"- Colour: {colour_line}"] if colour_line else []) + [
         f"- Arguments: `{args_line}`", f"- The plan: `build\\plan_v{v}.json`; render: "
         f"`.venv\\Scripts\\python tools\\render_video.py projects\\{prj.name}\\build\\plan_v{v}.json`", "",
         "## Shots", "", "| # | in the edit | clip | from the clip | why this moment |", "|---|---|---|---|---|"]
    for sh in D["shots"]:
        c = clips[sh["sid"]]
        k = int(round(sh["in"] / c["fps"] * c["src_fps"]))
        L.append(f"| {sh['n']} | f{sh['start']}-{sh['end']} ({tc(sh['start'])}-{tc(sh['end'])}) | {sh['sid']} "
                 f"{c['name']} | f{k} ({frame_to_tc(k, c['src_fps'])}) | {sh['why']} |")
    if D["broll"]:
        L += ["", "## B-roll over the talking", ""]
        for b in D["broll"]:
            c = clips[b["sid"]]
            k = int(round(b["in"] / c["fps"] * c["src_fps"]))
            L.append(f"- f{b['frame']}-{b['end']} ({tc(b['frame'])}-{tc(b['end'])}): {b['sid']} {c['name']} from "
                     f"f{k} ({frame_to_tc(k, c['src_fps'])}) - {b['why']}")
    L += ["", "## Effects", ""]
    L += [f"- f{e['frame']} ({tc(e['frame'])}), shot {e['shot']}: {e['how']} (the style: {e['why']})"
          for e in D["effects"]] or ["- none - clean cuts"]
    L += ["", "## Not in this draft (Claude adds them, or DaVinci Resolve)", ""]
    L += [f"- {x['label']}" + (f" ({x['per_min']:g}/min)" if x.get("per_min") else "") + f": {x['why']}"
          for x in D["skipped"]]
    if style.get("captions") or (style.get("talk") or {}).get("captions_likely"):
        L.append(f"- Captions ({style.get('captions') or 'like the reference'}): speech to text "
                 f"(`tools\\speech.py transcribe`) + `tools\\overlay.py captions`")
    if any(b.get("text_graphics") for b in style.get("breakdowns", [])):
        L.append("- Text / graphics like the reference: HTML graphics (`tools\\overlay.py new`)")
    L += ["- A story: the draft picks moments by how they look; the order of what happens is Claude's job", "",
          "## Next", "", "- Watch it; in the app: Editor > this video > Review > *How did it turn out?*",
          f"- Claude refines it: `/recreate-video feel:{','.join(x['analysis'] or x['title'] for x in style['sources'])} "
          f"{prj.name}`" if style.get("sources") else f"- Claude refines it: `/recreate-video want:"
          f"{','.join(style.get('presets', [])) or 'words'} {prj.name}`", "", ST.text(style, fps)]
    return "\n".join(L) + "\n"


def pick_orientation(prj: Project, fmt: str | None, style: dict | None) -> str:
    """--format, else the style's, else the clips' most common shape."""
    files = prj.footage_files()
    if not files:
        raise SystemExit(f"no clips in {prj.dir} - copy your videos into that folder first")
    if fmt:
        return fmt
    if style and style.get("format"):
        return style["format"]
    shapes = Counter()
    for f in files[:12]:
        vv = probe(f)["video"]
        shapes[orientation(vv["display_width"], vv["display_height"])] += 1
    return shapes.most_common(1)[0][0]


def footage(prj: Project, W: int, H: int) -> tuple[dict, list[dict], bool, float]:
    """The frame caches (made first when missing) as the draft's clips, at their most common frame rate."""
    ensure_caches(prj, W, H)
    srcs, clips, color = load_clips(prj)
    fps = Counter(c["fps"] for c in clips).most_common(1)[0][0]
    odd = [c for c in clips if c["fps"] != fps]
    if odd:
        log(f"left out (cached at another frame rate): {', '.join(c['id'] for c in odd)}")
    return srcs, [c for c in clips if c["fps"] == fps], color, fps


def clip_sound(prj: Project, clips: list[dict], d: Path, fps: float, mode: str, only: set | None = None,
               reuse: Path | None = None) -> None:
    """The clips' own sound (48 kHz stereo, decoded once per clip into d; one already in `reuse` is read from there)
    and, in talk mode, their spoken parts. only = just these clip IDs."""
    for c in clips:
        if only is not None and c["id"] not in only:
            continue
        name = f"clip_{c['id']}_{_key(Path(c['source']))}.wav"
        if reuse is not None and (reuse / name).exists():
            c["wav"] = str(reuse / name)
        else:
            wav = prj.check(d / name)
            c["wav"] = str(wav) if decode(Path(c["source"]), wav) else None
        info = probe(Path(c["source"]))
        c["offset_s"] = float(info["video"].get("start_time") or 0) - float((info["audio"] or {}).get("start_time")
                                                                            or 0)
        if mode == "talk" and c["wav"]:
            c["speech"] = speech(Path(c["wav"]), fps, c["frames"], c["offset_s"])    # video t = wav t - offset
        log(f"{c['id']} {c['name']}: " + ("no sound" if not c["wav"] else
                                         f"{len(c['speech'])} spoken part(s)" if c.get("speech") else
                                         "nobody talks (B-roll)" if mode == "talk" else "sound kept"))


# ------------------------------------------------------------------------------------------------ feel test (0.4.2)
FEEL_MAX_S = 6.0          # a feel test is about the hook; its frames stay in memory (3 x 6 s x 640x360 = ~0.3 GB)


def feel_slots(a) -> list[dict]:
    """The 2-3 hooks of a feel test: --like (the videos' style), each --preset, then feels (--feel / --feels, else
    picked from the user's words: style.pick_feels), at most three, each with the arguments of its full-length draft."""
    slots = []
    try:
        if a.like:
            s = ST.build(a.like, [], "")
            slots.append({"id": "like", "label": "Like " + " + ".join(str(x["title"]).split(" [")[0][:22]
                                                                    for x in s["sources"]),
                          "style": ST.hook_style(s), "args": "--like " + " ".join(f'"{x}"' for x in a.like)})
        for p in a.preset:
            if p not in ST.PRESETS:
                raise ValueError(f"unknown preset {p!r} (known: {', '.join(ST.PRESETS)})")
            slots.append({"id": p, "label": ST.PRESETS[p]["label"], "style": ST.hook_style(ST.presets([p])),
                          "args": f"--preset {p}"})
        ids = [x.strip() for x in (a.feels or "").split(",") if x.strip()]
        if a.feel and a.feel not in ids:
            ids.insert(0, a.feel)
        if not ids:
            ids = ST.pick_feels(a.want, max(0, 3 - len(slots)))
        for f in ids:
            slots.append({"id": f, "label": ST.FEELS[f]["label"] if f in ST.FEELS else f,
                          "style": ST.feel_style(f, hook=True), "args": f"--feel {f}"})
    except ValueError as e:
        raise SystemExit(str(e))
    slots = slots[:3]
    if len(slots) < 2:
        raise SystemExit("a feel test needs 2-3 different feels (--feels slick,raw,cinematic)")
    for letter, s in zip("ABC", slots):
        s["letter"] = letter
        s["key"] = f"{letter}_{re.sub(r'[^A-Za-z0-9]+', '_', s['id'])[:20]}"
    return slots


def _encode(frames, fps: float, out: Path, sound: Path | None, size: tuple[int, int]) -> None:
    """RGB frames (any iterable, streamed) -> an H.264 MP4 with the sound (AAC), small and quick."""
    w, h = size
    cmd = [tool("ffmpeg"), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r",
           f"{fps:g}", "-i", "-"]
    if sound:
        cmd += ["-i", str(sound), "-map", "0:v", "-map", "1:a:0", "-c:a", "aac", "-b:a", "160k", "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for fr in frames:
            p.stdin.write(np.ascontiguousarray(fr).tobytes())
    finally:
        p.stdin.close()
        p.wait()
    if p.returncode:
        raise SystemExit(f"ffmpeg could not write {out.name}")


def _events(D: dict) -> dict[int, list[str]]:
    """Frame -> what starts there in a hook (a cut, an effect's name) for the labels."""
    ev: dict[int, list[str]] = {}
    for sh in D["shots"][1:]:
        ev.setdefault(int(sh["start"]), []).append("cut")
    for e in D["effects"]:
        ev.setdefault(int(e["frame"]), []).append(taxonomy.label(e["type"]).lower())
    return ev


def _status(D: dict, ev: dict, f: int) -> str:
    k = sum(1 for sh in D["shots"] if sh["start"] <= f)
    recent = [", ".join(v) for g, v in sorted(ev.items()) if 0 <= f - g < 8]
    return f"shot {k}/{len(D['shots'])}" + (f" · {recent[-1]}" if recent else "")


def compare_video(slots: list[dict], fps: float, out: Path, sound: Path | None) -> None:
    """A | B | C side by side, each tile headed by its letter + feel, the frame + timecode and what happens there."""
    from PIL import Image, ImageDraw
    from motionlab.media import fonts
    F = fonts(1.0)
    n = min(len(s["frames"]) for s in slots)
    h, w = slots[0]["frames"][0].shape[:2]
    gap, head = 8, 64
    Wc = len(slots) * w + (len(slots) + 1) * gap
    Hc = head + h + gap
    Wc, Hc = Wc + Wc % 2, Hc + Hc % 2

    def frames():
        for f in range(n):
            yield np.asarray(tile(f))

    def tile(f):
        img = Image.new("RGB", (Wc, Hc), (14, 14, 16))
        d = ImageDraw.Draw(img)
        for i, s in enumerate(slots):
            x = gap + i * (w + gap)
            img.paste(Image.fromarray(s["frames"][f]), (x, head))
            d.text((x + 2, 4), f"{s['letter']}  {s['label']}", fill=(255, 255, 255), font=F["title"])
            d.text((x + 2, 30), f"f{f} ({frame_to_tc(f, fps)})", fill=(255, 196, 0), font=F["mono_b"])
            d.text((x + 2, 47), _status(s["D"], s["ev"], f), fill=(170, 200, 230), font=F["small"])
        return img
    _encode(frames(), fps, out, sound, (Wc, Hc))


def compare_sheet(slots: list[dict], fps: float, out: Path, title: str, cols: int = 8) -> None:
    """One row per hook, `cols` frames across (evenly spaced), each captioned with frame + timecode (a cut in red)."""
    from PIL import Image, ImageDraw
    from motionlab.media import fonts
    F = fonts(1.0)
    n = min(len(s["frames"]) for s in slots)
    fr = sorted({int(round(x)) for x in np.linspace(0, n - 1, cols)})
    h, w = slots[0]["frames"][0].shape[:2]
    tw = 200 if w >= h else 120
    th = int(round(tw * h / w))
    left, top, cap, pad = 210, 44, 20, 6
    img = Image.new("RGB", (left + len(fr) * (tw + pad) + pad, top + len(slots) * (th + cap + 12) + 4),
                    (20, 20, 24))
    d = ImageDraw.Draw(img)
    d.text((10, 10), title, fill=(255, 255, 255), font=F["body"])
    for r, s in enumerate(slots):
        y = top + r * (th + cap + 12)
        D = s["D"]
        d.text((10, y + 2), f"{s['letter']}  {s['label']}", fill=(255, 255, 255), font=F["title"])
        d.text((10, y + 32), f"{len(D['shots'])} shots, {len(D['effects'])} effects", fill=(190, 190, 190),
               font=F["small"])
        cuts = [sh["start"] for sh in D["shots"][1:]]
        d.text((10, y + 50), "cuts: " + (", ".join(f"f{c}" for c in cuts[:5]) or "none"), fill=(190, 190, 190),
               font=F["small"])
        for c, f in enumerate(fr):
            x = left + pad + c * (tw + pad)
            img.paste(Image.fromarray(s["frames"][f]).resize((tw, th), Image.LANCZOS), (x, y))
            near_cut = any(0 <= f - k < 3 for k in cuts)
            d.text((x, y + th + 3), f"f{f} {frame_to_tc(f, fps)}", font=F["small"],
                   fill=(255, 110, 110) if near_cut else (255, 196, 0))
    img.save(out)


def _sources_unchanged(prj: Project) -> list[str]:
    """Footage whose size / modified time differs from build\\sources.json (cheap; the render checks SHA-256)."""
    bad = []
    for k, ent in prj.manifest().get("sources", {}).items():
        p, fp = Path(ent["path"]), ent.get("fingerprint") or {}
        try:
            st = p.stat()
        except OSError:
            bad.append(f"{k} {ent.get('name')} (missing)")
            continue
        if fp and (st.st_size != fp.get("size") or st.st_mtime_ns != fp.get("mtime_ns")):
            bad.append(f"{k} {ent.get('name')}")
    return bad


def feel_notes(prj, run, k, slots, fps, N, w, h, color, sound_line, want, timings) -> str:
    tc = lambda f: frame_to_tc(f, fps)  # noqa: E731
    rel = f"build\\feel\\{run.name}"
    L = [f"# Feel test {k} of {prj.name}: {len(slots)} hooks of {N} frames ({N / fps:.1f} s) at {fps:g} fps", "",
         f"Made by `tools\\draft_edit.py --feel-test` ({time.strftime('%Y-%m-%d %H:%M')}) by rules, no Claude; "
         f"{w}x{h} each (a small preview). Frames are 0-based (f0 = 00:00:00:00).",
         f"- Compare: `{rel}\\compare.mp4` ({' | '.join(s['letter'] for s in slots)} side by side) and "
         f"`{rel}\\sheet.png`.",
         f"- Sound: {sound_line}"] + ([f"- The user's words: \"{want}\" (they picked the feels)"] if want else []) + (
        [] if color else ["- The frame caches are black and white (prep_footage --grey): the hooks differ in contrast "
                          "and levels here, not in colour."]) + [
        "- The user picks one, or mixes (\"B's pacing with A's colours\"): that is the plan. Pacing = a hook's rhythm "
        "line, colours = its grade, effects = its list. A mix = the full-length draft of the pacing's feel, then the "
        "other hook's grade / effects in the plan (`/recreate-video` by_feel.md).", ""]
    for s in slots:
        D, st = s["D"], s["style"]
        R = st.get("rhythm") or {}
        cuts = [sh["start"] for sh in D["shots"][1:]]
        g = D["grade"]
        L += [f"## {s['letter']} - {s['label']}", ""]
        L += [f"- The feel: {w_}" for w_ in st.get("preset_words", [])[:1]]
        L += [f"- The style of: {x['title']}" for x in st.get("sources", [])]
        L.append(f"- Rhythm aimed for: a shot {R.get('median_shot_s', '?'):g} s typical ({R.get('p10_shot_s', '?')}-"
                 f"{R.get('p90_shot_s', '?')} s), {R.get('hook_cuts_3s') or 0} cut(s) in the first 3 s"
                 + (f" (the first at {R['first_cut_s']:g} s)" if R.get("first_cut_s") and not R.get("hook_cuts_3s")
                    else "")
                 + (f", {R['cuts_on_beat_pct']:g} % on the beat" if R.get("cuts_on_beat_pct") is not None else "")
                 if isinstance(R.get("median_shot_s"), (int, float)) else "- Rhythm: the style's")
        L.append(f"- Here: {len(D['shots'])} shots, cuts at " + (", ".join(f"f{c} ({tc(c)})" for c in cuts)
                                                               or "none (one shot)"))
        L.append("- Effects: " + ("; ".join(f"f{e['frame']} ({tc(e['frame'])}) {e['how']}" for e in D["effects"])
                                  or "none - clean cuts"))
        L.append(f"- Colour: levels {g.get('black', 0)}-{g.get('white', 255)}, gamma {g.get('gamma', 1.0):g}, "
                 f"saturation {g.get('saturation', 1.0):g}")
        L.append(f"- Files: `{rel}\\{s['key']}.mp4`, plan `{rel}\\plan_{s['key']}.json`")
        L.append(f"- Full length in this feel: `.venv\\Scripts\\python tools\\draft_edit.py {prj.name} {s['args']} "
                 f"--length 30 --render` (the hook test showed each signature effect at least once in 3 s; the full "
                 f"draft uses the style's own rates)")
        L.append("")
    L += ["## Timings", ""] + [f"- {k_}: {v:.1f} s" for k_, v in timings.items()]
    return "\n".join(L) + "\n"


def edit_words(prj: Project, plan: dict, fps: float) -> dict:
    """The words said in the edit (0.5.3 D2): each talking shot's words from its clip's transcript (tools\\speech.py,
    made when missing), moved to the shot's place on the timeline -> a lab transcript (lines of words with times)."""
    import speech as SPT                                        # tools\speech.py (cached per clip)
    from motionlab import editlist as EL
    lines = []
    for L in EL.shots(plan):
        if L.get("hold") or float(L.get("speed", 1.0)) != 1.0:
            continue
        src = Path(str((plan["sources"].get(L["src"]) or {}).get("source", "")))
        if not src.is_file():
            continue
        _, tr = SPT.transcript(src)
        a = int(L.get("in", 0)) / fps
        b = a + (int(L["end"]) - int(L["start"]) + 1) / fps
        off = int(L["start"]) / fps - a
        for ln in tr.get("lines", []):
            ws = [{"t": round(float(w["t"]) + off, 3), "w": w["w"]} for w in ln.get("words") or []
                  if a <= float(w["t"]) < b]
            if ws:
                lines.append({"t0": ws[0]["t"], "t1": min(float(ln["t1"]) + off, b + off), "text":
                              " ".join(w["w"] for w in ws), "words": ws})
    lines.sort(key=lambda x: x["t0"])
    return {"source": "the edit's shots", "kind": "speech, moved through the edit", "lines": lines}


def apply_list(a, prj: Project) -> int:
    """0.5.3 (D1): draft_edit.py <project> --apply <list> - the edit list on the newest plan -> plan_v<N+1>.json +
    edit_v<N+1>.list; captions / graphics through overlay.py; a talking edit's sound cut again after cuts."""
    import json as _json
    import shutil
    from motionlab import editlist as EL
    from motionlab import templates as TM
    src = Path(a.apply)
    if not src.is_file():
        raise SystemExit(f"--apply: no such list file: {src}")
    plans = sorted(prj.build.glob("plan_v*.json"), key=lambda q: int(re.sub(r"\D", "", q.stem) or 0))
    if not plans:
        raise SystemExit(f"no plan in {prj.build} - a quick draft first (draft_edit.py {prj.name} ...)")
    base_p = plans[-1]
    base = _json.loads(base_p.read_text(encoding="utf-8"))
    try:
        ops = EL.parse(src.read_text(encoding="utf-8"))
        P, done, steps = EL.apply(base, ops)
    except EL.ListError as e:
        raise SystemExit(f"{src.name}:\n{e}")
    fps, v = float(P["fps"]), next_version(prj.build, prj.name)
    py, ov = sys.executable, str(LAB / "tools" / "overlay.py")

    def run(cmd: list[str]) -> str:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(LAB))
        if r.returncode:
            raise SystemExit(f"{' '.join(Path(c).name for c in cmd[1:4])} failed:\n{(r.stdout + r.stderr)[-1200:]}")
        return r.stdout
    for k, o in enumerate(steps, 1):
        if o["op"] == "graphic":
            at = EL.moved(base, ops, o["f"])
            if at is None:
                done.append(f"graphic {o['id']} at f{o['f']}: LEFT OUT - that frame was cut")
                continue
            folder = prj.build / "overlays" / f"v{v}_{k:02d}_{o['id']}"
            cmd = [py, ov, "new", str(folder), "--from", o["id"], "--frames", str(o["len"]), "--like-plan", "--force"]
            if o["values"]:
                cmd += ["--values", _json.dumps(o["values"], ensure_ascii=False)]
            if o.get("land"):
                cmd += ["--land", f"{o['land']}@{at}", "--start", str(at)]
            run(cmd)
            L = {"type": "overlay", "id": folder.name, "file": str(folder / f"{folder.name}.mov"), "start": at,
                 "end": min(at + o["len"] - 1, int(P["frames"]) - 1), "blend": "normal"}
            if o.get("land"):
                r = TM.land_target(str(folder), o["land"], at, at)
                L.update(start=r["start"], end=min(r["end"], int(P["frames"]) - 1), **{"in": r["in"]})
                L["land"] = {"track": r["track"], "at": at, "asked": at, "start": r["start"], "in": r["in"]}
            P["layers"].append(L)
            done.append(f"graphic {o['id']} f{L['start']}-f{L['end']} ({frame_to_tc(L['start'], fps)})"
                        + (f", '{o['land']}' landed on f{at}" if o.get("land") else ""))
        elif o["op"] == "caption":
            words = prj.check(prj.build / f"captions_v{v}.json")
            write_json(words, edit_words(prj, P, fps))
            folder = prj.build / "overlays" / f"captions_v{v}"
            if folder.exists():
                shutil.rmtree(folder)
            out = run([py, ov, "captions", str(folder), "--from", str(words), "--preset", o["preset"], "--fps",
                       f"{fps:g}", "--width", str(P["width"]), "--height", str(P["height"]), "--frames",
                       str(P["frames"])] + (["--script", o["script"]] if o.get("script") else []))
            P["layers"].append({"type": "overlay", "id": folder.name, "file": str(folder / f"{folder.name}.mov"),
                                "start": 0, "end": int(P["frames"]) - 1, "blend": "normal"})
            missing = [ln for ln in out.splitlines() if ln.startswith("NOT SAID")]
            done.append(f"captions ({o['preset']}" + (f", script {o['script']}" if o.get("script") else "")
                        + f") over f0-f{int(P['frames']) - 1}" + (f"; {len(missing)} script line(s) not said" if missing
                                                                    else ""))
            done += ["  " + m for m in missing]
    made = base.get("made_by") or {}
    talk = made.get("sound") in ("talk", "clips") and any(o["op"] == "cut" for o in ops)
    base_audio = Path(str((base.get("audio") or {}).get("path") or ""))
    if base_audio.parent.name == "sfx" and base_audio.stem.endswith("_mix"):
        P["sfx"] = True                                 # the base had sound effects: build.py makes them again
    if talk:                                            # the clips' own sound follows the shots again
        _, clips, _, cfps = footage(prj, int(P["width"]), int(P["height"]))
        d = prj.check(prj.build / "draft")
        clip_sound(prj, clips, d, cfps, "clips", only={L["src"] for L in EL.shots(P)}, reuse=d)
        by_id = {c["id"]: c for c in clips}
        segs = [(L["src"], EL._src_at(L, L["start"]), EL._src_at(L, L["start"]) + L["end"] - L["start"])
                for L in EL.shots(P)]
        P["audio"] = {**(P.get("audio") or {}), "path": str(write_sound(prj, d, v, cut_sound(
            segs, by_id, fps, d, level="take" if made.get("sound") == "talk" else None)))}
        done.append("sound: the clips' own sound cut again to the shots" + (" (voice levelled per take)"
                                                                            if made.get("sound") == "talk" else ""))
    P["name"], P["output"] = f"{prj.name}_v{v}", f"{prj.name}_v{v}.mp4"
    P["made_by"] = {"tool": "draft_edit.py --apply", "list": f"edit_v{v}.list", "from": base_p.name,
                    "sound": made.get("sound"), "date": time.strftime("%Y-%m-%d %H:%M")}
    out = prj.check(prj.build / f"plan_v{v}.json")
    write_json(out, P)
    keep = prj.build / f"edit_v{v}.list"
    if src.resolve() != keep.resolve():
        shutil.copyfile(src, prj.check(keep))
    print(f"{base_p.name} + {src.name} -> {out.name} ({int(P['frames'])} frames, "
          f"{frame_to_tc(int(P['frames']) - 1, fps)} last):")
    for ln in done:
        print("  " + ln)
    print(f"next: .venv\\Scripts\\python tools\\build.py {prj.name} {out.name}")
    print(out)
    return 0


def feel_test(a, prj: Project, cfg: dict) -> int:
    """2-3 hooks in different feels, rendered small, side by side (see the docstring)."""
    from motionlab.compose import Renderer
    t0 = time.time()
    timings: dict[str, float] = {}
    slots = feel_slots(a)
    log("feel test: " + " | ".join(f"{s['letter']} {s['label']}" for s in slots))
    like_style = next((s["style"] for s in slots if s["id"] == "like"), None)
    orient = pick_orientation(prj, a.format, like_style)
    W, H = ST.size(orient)
    srcs, clips, color, fps = footage(prj, W, H)
    k = max(120, int(a.size)) / min(W, H)
    w, h = int(round(W * k / 2)) * 2, int(round(H * k / 2)) * 2
    timings["frame caches + clips"] = time.time() - t0
    base = prj.check(prj.build / "feel")
    aud = prj.check(base / "audio")
    aud.mkdir(parents=True, exist_ok=True)
    nums = [int(m.group(1)) for p in base.glob("feel_*") if (m := re.fullmatch(r"feel_(\d+)", p.name))]
    k_run = max(nums or [0]) + 1
    run = prj.check(base / f"feel_{k_run}")
    run.mkdir(parents=True, exist_ok=False)
    t1 = time.time()
    music, music_note = find_music(prj, a.music)
    mode = a.sound if a.sound != "auto" else "music" if music else "clips"
    if mode == "music" and not music:
        raise SystemExit("no song: put an audio file (.mp3, .m4a, .wav) into the project folder or give --music")
    length = min(FEEL_MAX_S, a.length or 3.0)
    beats, downbeats, drops, start, info = [], set(), [], 0.0, None
    if mode == "music":
        info = music_info(prj, aud, music, fps, cfg)
        length = min(length, info["duration_s"])
        start = music_start(info, length, fps, a.music_start)
        length = min(length, info["duration_s"] - start)
        sf0 = start * fps
        beats = [b - sf0 for b in info["beats"] if b - sf0 > 0]
        downbeats = {int(round(b - sf0)) for b in info["downbeats"]}
        drops = [x - sf0 for x in info["drops"] if 0 < x - sf0 < length * fps]
    elif mode == "talk":
        clip_sound(prj, clips, aud, fps, "talk", reuse=prj.build / "draft")
    N = int(round(length * fps))
    for s in slots:
        try:
            s["D"] = DR.make(s["style"], clips, fps, w, h, N, "talk" if mode == "talk" else "music", beats, downbeats,
                             drops, a.seed)
        except ValueError as e:
            raise SystemExit(f"{s['label']}: {e}")
        s["ev"] = _events(s["D"])
    by_id = {c["id"]: c for c in clips}
    shared = None
    if mode == "music":
        import soundfile as sf
        y, _ = sf.read(info["wav"], dtype="float32", always_2d=True)
        s0, n = int(round(start * SR)), int(round(N / fps * SR))
        y = y[s0:s0 + n, :2] if y.shape[1] >= 2 else np.repeat(y[s0:s0 + n], 2, axis=1)
        shared = write_sound(prj, run, 0, y.copy(), stem="music")
        sound_line = (f"{music.name} from {start:g} s" + (f", {info['bpm']:g} BPM" if info.get("bpm") else "")
                      + f" - the same under every hook ({len(drops)} drop(s) in it)")
    else:
        if mode == "clips":
            clip_sound(prj, clips, aud, fps, "clips", only={x[0] for s in slots for x in s["D"]["sound"]},
                       reuse=prj.build / "draft")
        sound_line = ("the clips' own sound in order, pauses cut out - the same under every hook" if mode == "talk"
                      else "each hook's own clip sound (no song in the project folder); the side by side is silent")
    timings["sound + plans"] = time.time() - t1
    for s in slots:
        t2 = time.time()
        D = s["D"]
        snd = shared or write_sound(prj, run, 0, cut_sound(D["sound"], by_id, fps, run), stem=f"{s['key']}_sound")
        plan = {"name": f"{prj.name}_feel{k_run}_{s['key']}", "width": w, "height": h, "fps": fps,
                "frames": D["frames"], "background": 0.0, "levels": "single", "seed": a.seed, "sources": srcs,
                "grades": {"default": D["grade"]}, "layers": D["layers"], "audio": {"path": str(snd)},
                "output": f"{s['key']}.mp4",
                "made_by": {"tool": "draft_edit.py --feel-test", "feel": s["id"], "label": s["label"],
                            "args": s["args"], "want": a.want, "sound": mode, "music": str(music) if music else None,
                            "music_start_s": start, "seed": a.seed, "date": time.strftime("%Y-%m-%d %H:%M")}}
        write_json(prj.check(run / f"plan_{s['key']}.json"), plan)
        R = Renderer(plan)
        s["frames"] = [R.render(f) for f in range(plan["frames"])]
        _encode(s["frames"], fps, prj.check(run / plan["output"]), snd, (w, h))
        if mode == "talk" and not shared:
            shared = snd                                  # what is said is the same in every hook: the first's sound
        timings[f"{s['letter']} {s['label']}: {plan['frames']} frames"] = time.time() - t2
        log(f"{s['letter']} {s['label']}: {len(D['shots'])} shots, {len(D['effects'])} effects - "
            f"{time.time() - t2:.1f} s")
    t3 = time.time()
    cmp_p = prj.check(run / "compare.mp4")
    compare_video(slots, fps, cmp_p, shared)
    sheet_p = prj.check(run / "sheet.png")
    names = " | ".join(f"{s['letter']} {s['label']}" for s in slots)
    compare_sheet(slots, fps, sheet_p, f"{prj.name} - feel test {k_run}: {names} - {N} frames ({N / fps:.1f} s) "
                                       f"at {fps:g} fps")
    timings["side by side + sheet"] = time.time() - t3
    timings["total"] = time.time() - t0
    bad = _sources_unchanged(prj)
    md = feel_notes(prj, run, k_run, slots, fps, N, w, h, color, sound_line, a.want, timings)
    prj.check(run / "feel.md").write_text(md, encoding="utf-8")
    write_json(prj.check(run / "feel.json"), {
        "project": prj.name, "run": run.name, "fps": fps, "frames": N, "size": [w, h], "sound": sound_line,
        "want": a.want, "colour_caches": color, "timings_s": {k_: round(v, 2) for k_, v in timings.items()},
        "hooks": [{"letter": s["letter"], "id": s["id"], "label": s["label"], "args": s["args"],
                   "video": f"{s['key']}.mp4", "plan": f"plan_{s['key']}.json",
                   "rhythm": s["style"].get("rhythm"), "grade": s["D"]["grade"],
                   "shots": s["D"]["shots"], "effects": s["D"]["effects"]} for s in slots],
        "compare": cmp_p.name, "sheet": sheet_p.name})
    log(f"feel test {k_run}: {time.time() - t0:.1f} s - notes {run / 'feel.md'}")
    log("sources unchanged (size + time): " + ("yes" if not bad else f"NO - {bad}"))
    print(sheet_p)
    print(cmp_p)
    return 0


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project", nargs="?")
    ap.add_argument("--like", nargs="+", action="extend", default=[],
                    help="up to 3 analysed videos (analysis folder, a card's title or id)")
    ap.add_argument("--preset", action="append", default=[], help=f"one of: {', '.join(ST.PRESETS)}")
    ap.add_argument("--want", default="", help="the user's own words (the draft understands a few)")
    ap.add_argument("--length", type=float)
    ap.add_argument("--format", choices=sorted(ST.SIZES))
    ap.add_argument("--music")
    ap.add_argument("--music-start")
    ap.add_argument("--sound", choices=["auto", "music", "clips", "talk"], default="auto")
    ap.add_argument("--apply", metavar="LIST", help="0.5.3: an edit list (motionlab\\editlist.py) on the newest plan "
                    "-> plan_v<N+1>.json")
    ap.add_argument("--per-shot", action="store_true", help="talk: level the voice per shot (default: one gain per take)")
    ap.add_argument("--colour", choices=["match", "grade", "none"], default="match")
    ap.add_argument("--colour-strength", type=float, default=0.8, help="how far toward the references' colour (0-1)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--presets", action="store_true", help="list the presets")
    ap.add_argument("--feel", help=f"a feel instead of presets: {', '.join(ST.FEEL_ORDER)}")
    ap.add_argument("--feel-test", action="store_true", help="2-3 hooks in different feels, side by side")
    ap.add_argument("--feels", help="feel test: which feels, e.g. slick,raw,cinematic (default: from --want)")
    ap.add_argument("--size", type=int, default=360, help="feel test: the short side of each hook in pixels")
    a = ap.parse_args()
    if a.presets:
        for p in ST.presets_info():
            print(f"{p['id']:15s} {p['label']}: {p['help']}")
        return 0
    if not a.project:
        ap.error("the project is missing")
    t0 = time.time()
    prj = Project(a.project)
    cfg = load_config()
    if a.apply:
        return apply_list(a, prj)
    if a.feel_test:
        return feel_test(a, prj, cfg)
    try:
        if a.feel:
            if a.like or a.preset:
                raise ValueError("--feel is a style of its own (for starting without a reference): leave out --like / "
                                 "--preset")
            style = ST.feel_style(a.feel, a.want)
        else:
            style = ST.build(a.like, a.preset, a.want)
    except ValueError as e:
        raise SystemExit(str(e))
    log(f"style: {ST.summary(style)}")
    orient = pick_orientation(prj, a.format, style)
    W, H = ST.size(orient)
    srcs, clips, color, fps = footage(prj, W, H)
    d = prj.build / "draft"
    d.mkdir(parents=True, exist_ok=True)
    music, music_note = find_music(prj, a.music)
    mode = a.sound
    if mode == "auto":
        mode = "talk" if style.get("mode") == "talk" and not a.music else "music" if music else "clips"
    if mode == "music" and not music:
        raise SystemExit("no song: put an audio file (.mp3, .m4a, .wav) into the project folder or give --music")
    if mode in ("talk", "clips"):
        clip_sound(prj, clips, d, fps, mode)
    beats, downbeats, drops, start, info = [], set(), [], 0.0, None
    length = a.length or (style.get("length_s") or {}).get("typical") or 30.0
    if mode == "music":
        info = music_info(prj, d, music, fps, cfg)
        length = min(length, info["duration_s"])
        start = music_start(info, length, fps, a.music_start)
        length = min(length, info["duration_s"] - start)
        sf0 = start * fps
        beats = [b - sf0 for b in info["beats"] if b - sf0 > 0]
        downbeats = {int(round(b - sf0)) for b in info["downbeats"]}
        drops = [x - sf0 for x in info["drops"] if 0 < x - sf0 < length * fps]
    N = int(round(length * fps)) if (mode != "talk" or a.length) else None
    try:
        D = DR.make(style, clips, fps, W, H, N, "talk" if mode == "talk" else "music", beats, downbeats, drops, a.seed)
    except ValueError as e:
        raise SystemExit(str(e))
    v = next_version(prj.build, prj.name)
    by_id = {c["id"]: c for c in clips}
    if mode == "music":
        import soundfile as sf
        y, _ = sf.read(info["wav"], dtype="float32", always_2d=True)
        s0, n = int(round(start * SR)), int(round(D["frames"] / fps * SR))
        y = y[s0:s0 + n, :2] if y.shape[1] >= 2 else np.repeat(y[s0:s0 + n], 2, axis=1)
        k = min(len(y), int(1.2 * SR))
        y = y.copy()
        y[len(y) - k:] *= np.linspace(1, 0, k, dtype=np.float32)[:, None]
        sound = write_sound(prj, d, v, y)
        sound_line = (f"{music.name} from {start:g} s" + (f", {info['bpm']:g} BPM" if info.get("bpm") else "")
                      + f", {len(beats)} beats, {len(drops)} drop(s) in the edit" + (f" ({info['note']})" if info.get("note")
                                                                                     else ""))
    else:
        lvl = ("shot" if a.per_shot else "take") if mode == "talk" else None
        sound = write_sound(prj, d, v, cut_sound(D["sound"], by_id, fps, d, level=lvl))
        sound_line = ((f"the clips' own sound in order, pauses cut out, the voice levelled to {VOICE_DB:g} dBFS "
                       f"(one gain per {lvl})") if mode == "talk"
                      else "the clips' own sound, shot by shot (no song in the project folder)")
    grade, colour_line = (D["grade"] if a.colour != "none" else dict(DR.NEUTRAL)), None
    if a.colour == "match" and style.get("lab") and color:
        try:
            grade, colour_line = match_colour(prj, v, clips, style, max(0.0, min(1.0, a.colour_strength)))
        except (OSError, ValueError) as e:
            colour_line = f"not matched ({e}) - the style's starting grade instead"
    elif a.colour != "none" and style.get("grade"):
        colour_line = "the style's starting grade (levels, saturation, a tint)"
    if colour_line:
        log(f"colour: {colour_line}")
    plan = {"name": f"{prj.name}_v{v}", "width": W, "height": H, "fps": fps, "frames": D["frames"],
            "background": 0.0, "levels": "single", "seed": a.seed, "sources": srcs,
            "grades": {"default": grade}, "layers": D["layers"], "audio": {"path": str(sound)},
            "output": f"{prj.name}_v{v}.mp4",
            "made_by": {"tool": "draft_edit.py", "like": a.like, "presets": a.preset, "want": a.want,
                        "sound": mode, "music": str(music) if music else None, "music_start_s": start,
                        "feel": a.feel, "seed": a.seed, "date": time.strftime("%Y-%m-%d %H:%M"),
                        "style": ST.summary(style)}}
    plan_p = prj.check(prj.build / f"plan_v{v}.json")
    write_json(plan_p, plan)
    args_line = " ".join(sys.argv[1:])
    md = notes(prj, v, style, D, by_id, fps, W, H, orient, sound_line, music_note, args_line, colour_line)
    prj.check(prj.build / f"draft_v{v}.md").write_text(md, encoding="utf-8")
    write_json(prj.check(d / f"draft_v{v}.json"), {k: D[k] for k in ("frames", "shots", "effects", "skipped", "broll")}
               | {"style": style, "sound": sound_line, "mode": mode})
    log(f"draft v{v}: {D['frames']} frames ({D['frames'] / fps:.1f} s), {len(D['shots'])} shots, "
        f"{len(D['effects'])} effects, {len(D['skipped'])} kinds left for Claude - {time.time() - t0:.1f} s")
    log(f"notes: {prj.build / f'draft_v{v}.md'}")
    if not a.render:
        print(plan_p)
        return 0
    r = subprocess.run([sys.executable, str(TOOLS / "render_video.py"), str(plan_p)])
    if r.returncode:
        raise SystemExit("render_video.py failed (see above)")
    out = prj.build / plan["output"]
    bad = prj.verify_sources() if (prj.build / "sources.json").exists() else []
    log("sources unchanged: " + ("yes" if not bad else f"NO - {bad}"))
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
