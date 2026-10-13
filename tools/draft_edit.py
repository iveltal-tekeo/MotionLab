"""A quick first edit of a project's clips in a style - by rules, in minutes, no Claude needed (0.4, Edit > Quick
draft). Claude starts from it for an edit by feel (/recreate-video feel:...); the app runs it as a job.

    .venv\\Scripts\\python tools\\draft_edit.py <project> --like <video> [<video> <video>]   the style of up to 3
                                                                                         analysed videos
    .venv\\Scripts\\python tools\\draft_edit.py <project> --preset fast_hook [--want "3 s cuts, captions"]
    .venv\\Scripts\\python tools\\draft_edit.py --presets                                 the presets
  --length 30         seconds (default: the style's typical length; at most the music / what is said)
  --format vertical   vertical | horizontal | square (default: the style's, else the clips')
  --music <file>      an audio file in the project folder (a name, or a path; "none" = no music; default: the only
                      or first one there)
  --music-start auto  seconds into the song (auto: the strongest part - a drop - comes right after the hook)
  --sound auto        music | clips (the clips' own sound, shot by shot) | talk (the clips' own sound in order, the
                      pauses cut out); auto = talk for a talking style, else music when there is a song, else clips
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

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import audio as AU  # noqa: E402
from motionlab import draft as DR  # noqa: E402
from motionlab import footage as FC  # noqa: E402
from motionlab import style as ST  # noqa: E402
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
    None when nobody talks (B-roll)."""
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


def cut_sound(segs: list, clips: dict, fps: float, d: Path) -> np.ndarray:
    """The clips' own sound for the shots, frame-exact, 8 ms fades at each cut (silence where a clip has none)."""
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
    return np.concatenate(out) if out else np.zeros((0, 2), np.float32)


def write_sound(prj: Project, d: Path, v: int, y: np.ndarray) -> Path:
    import soundfile as sf
    wav, m4a = prj.check(d / f"v{v}_sound.wav"), prj.check(d / f"v{v}_sound.m4a")
    sf.write(str(wav), np.clip(y, -1, 1), SR, subtype="PCM_16")
    r = subprocess.run([tool("ffmpeg"), "-y", "-v", "error", "-nostdin", "-i", str(wav), "-c:a", "aac", "-b:a", "192k",
                        str(m4a)], capture_output=True, text=True)
    wav.unlink(missing_ok=True)
    if r.returncode:
        raise SystemExit(f"could not encode the sound: {r.stderr[-400:]}")
    return m4a


def notes(prj, v, style, D, clips, fps, W, H, orient, sound_line, music_note, args_line) -> str:
    tc = lambda f: frame_to_tc(f, fps)  # noqa: E731
    N = D["frames"]
    L = [f"# Draft v{v} of {prj.name} - {ST.summary(style)}", "",
         f"Made by `tools\\draft_edit.py` ({time.strftime('%Y-%m-%d %H:%M')}) by rules, no Claude: {N} frames = "
         f"{N / fps:.1f} s at {fps:g} fps, {W}x{H} ({orient}), {len(D['shots'])} shots, {len(D['effects'])} effects. "
         f"Frames are 0-based (f0 = 00:00:00:00); a Resolve timeline starts at 01:00:00:00.", "",
         f"- Sound: {sound_line}"] + ([f"- {music_note}"] if music_note else []) + [
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
          "## Next", "", "- Watch it; in the app: Edit > this video > *How did it turn out?*",
          f"- Claude refines it: `/recreate-video feel:{','.join(x['analysis'] or x['title'] for x in style['sources'])} "
          f"{prj.name}`" if style.get("sources") else f"- Claude refines it: `/recreate-video want:"
          f"{','.join(style.get('presets', [])) or 'words'} {prj.name}`", "", ST.text(style, fps)]
    return "\n".join(L) + "\n"


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
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--presets", action="store_true", help="list the presets")
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
    try:
        style = ST.build(a.like, a.preset, a.want)
    except ValueError as e:
        raise SystemExit(str(e))
    log(f"style: {ST.summary(style)}")
    clip_files = prj.footage_files()
    if not clip_files:
        raise SystemExit(f"no clips in {prj.dir} - copy your videos into that folder first")
    if a.format:
        orient = a.format
    elif style.get("format"):
        orient = style["format"]
    else:
        shapes = Counter()
        for f in clip_files[:12]:
            vv = probe(f)["video"]
            shapes[orientation(vv["display_width"], vv["display_height"])] += 1
        orient = shapes.most_common(1)[0][0]
    W, H = ST.size(orient)
    ensure_caches(prj, W, H)
    srcs, clips, color = load_clips(prj)
    fps = Counter(c["fps"] for c in clips).most_common(1)[0][0]
    odd = [c for c in clips if c["fps"] != fps]
    clips = [c for c in clips if c["fps"] == fps]
    if odd:
        log(f"left out (cached at another frame rate): {', '.join(c['id'] for c in odd)}")
    d = prj.build / "draft"
    d.mkdir(parents=True, exist_ok=True)
    music, music_note = find_music(prj, a.music)
    mode = a.sound
    if mode == "auto":
        mode = "talk" if style.get("mode") == "talk" and not a.music else "music" if music else "clips"
    if mode == "music" and not music:
        raise SystemExit("no song: put an audio file (.mp3, .m4a, .wav) into the project folder or give --music")
    if mode in ("talk", "clips"):
        for c in clips:                                   # the clips' own sound (48 kHz stereo, once per clip)
            wav = prj.check(d / f"clip_{c['id']}_{_key(Path(c['source']))}.wav")
            c["wav"] = str(wav) if decode(Path(c["source"]), wav) else None
            info = probe(Path(c["source"]))
            c["offset_s"] = float(info["video"].get("start_time") or 0) - float((info["audio"] or {}).get("start_time")
                                                                                or 0)
            if mode == "talk" and c["wav"]:
                c["speech"] = speech(Path(c["wav"]), fps, c["frames"], -c["offset_s"])
            log(f"{c['id']} {c['name']}: " + ("no sound" if not c["wav"] else
                                             f"{len(c['speech'])} spoken part(s)" if c.get("speech") else
                                             "nobody talks (B-roll)" if mode == "talk" else "sound kept"))
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
        sound = write_sound(prj, d, v, cut_sound(D["sound"], by_id, fps, d))
        sound_line = ("the clips' own sound in order, pauses cut out" if mode == "talk"
                      else "the clips' own sound, shot by shot (no song in the project folder)")
    plan = {"name": f"{prj.name}_v{v}", "width": W, "height": H, "fps": fps, "frames": D["frames"],
            "background": 0.0, "levels": "single", "seed": a.seed, "sources": srcs,
            "grades": {"default": D["grade"]}, "layers": D["layers"], "audio": {"path": str(sound)},
            "output": f"{prj.name}_v{v}.mp4",
            "made_by": {"tool": "draft_edit.py", "like": a.like, "presets": a.preset, "want": a.want,
                        "sound": mode, "music": str(music) if music else None, "music_start_s": start,
                        "seed": a.seed, "date": time.strftime("%Y-%m-%d %H:%M"), "style": ST.summary(style)}}
    plan_p = prj.check(prj.build / f"plan_v{v}.json")
    write_json(plan_p, plan)
    args_line = " ".join(sys.argv[1:])
    md = notes(prj, v, style, D, by_id, fps, W, H, orient, sound_line, music_note, args_line)
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
