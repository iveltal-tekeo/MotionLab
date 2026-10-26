"""The Editor's save (0.6.0 step 6; the Mini-editor until 2026-10-26): changes to a made video by hand - the app's
*Editor* tab runs `apply` as a job, and `media` for its live preview; the changes themselves are motionlab\\miniedit.py
(its docstring lists them and what moves with a shot).

    .venv\\Scripts\\python tools\\miniedit.py state <project> [plan_vN.json]     what the Editor sees: the shots with
          frame + timecode, their speed and the room their clips have, the graphics, the captions, the sound effects,
          the sound's mode (the newest plan when none is named)
    .venv\\Scripts\\python tools\\miniedit.py apply <project> <changes.json> [--plan plan_vN.json] [--build]
          the changes (a JSON list, in order) on that plan -> plan_v<N+1>.json (the old one stays) +
          edit_v<N+1>.list (a record of what the user changed, for Claude) + outcome.json "hand_fixes"; a graphic
          whose settings changed is a copy (<folder>_m<N+1>; the older versions keep theirs), a template added is a
          new graphic (overlays\\n<N+1>_<k>_<template>); the clips' own sound is cut again to the shots when it
          follows them (a sped-up / slowed shot's sound stretched, the pitch kept); --build = one plain build
          (tools\\build.py) after
    .venv\\Scripts\\python tools\\miniedit.py media <project> [--plan plan_vN.json]   the live preview's light copies:
          each clip of the video (the plan's "sources": the shots' first, then the ones the Editor can add) as a small
          H.264 at the plan's rate (short side 540, a key frame every 12 frames, its own sound) + its sound's loudness
          per frame (aligned like the save cuts it) + its filmstrip, the whole song's loudness ->
          build\\editor\\ (+ media.json); made once per clip, again only when the clip changes
    .venv\\Scripts\\python tools\\miniedit.py selfcheck                           known answers (motionlab\\miniedit)
Writes only into projects\\<project>\\build\\; the clips and the song are only read (hard rule 1).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import miniedit as M  # noqa: E402
from motionlab import overlay_settings as OS  # noqa: E402
from motionlab.project import PHOTO_EXT, Project  # noqa: E402
from motionlab.timecode import frame_to_tc  # noqa: E402
from motionlab.util import LAB, setup_console, tool  # noqa: E402

PY, TOOLS = sys.executable, LAB / "tools"
WAVE_SR = 8000                                    # the loudness per frame is read from the sound at this rate
STRIP_H, STRIP_COLS, STRIP_EVERY = 90, 10, 1.0    # the timeline's filmstrip: px high, pictures a row, seconds apart
media_key = M.media_key


def plans(b: Path) -> list[Path]:
    return sorted(b.glob("plan_v*.json"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 0))


def base_plan(prj: Project, name: str | None) -> Path:
    if name:
        if not re.fullmatch(r"plan_v\d+\.json", name) or not (prj.build / name).is_file():
            raise SystemExit(f"no plan {name} in {prj.build}")
        return prj.build / name
    ps = plans(prj.build)
    if not ps:
        raise SystemExit(f"no plan_vN.json in {prj.build}")
    return ps[-1]


def cmd_state(a) -> int:
    prj = Project(a.project)
    bp = base_plan(prj, a.plan)
    s = M.state(json.loads(bp.read_text(encoding="utf-8")))
    if a.json:
        print(json.dumps({"plan": bp.name, **s}, ensure_ascii=False, indent=1))
        return 0
    fps = s["fps"]
    tc = lambda f: f"f{f} ({frame_to_tc(f, fps)})"        # noqa: E731
    print(f"{prj.name} {bp.name}: {s['frames']} frames at {fps:g} fps, {s['width']}x{s['height']}; the sound "
          + {"follows": "follows the shots (cut again on save)", "song": "a song (it stays)", "none": "none",
             "fixed": "made some other way - the shots' timing is locked"}[s["sound"]])
    for x in s["shots"]:
        print(f"  {'scene' if x['scene'] else 'shot'} {x['n']} {x['id']}: {tc(x['start'])}-{tc(x['end'])}, "
              + (f"its graphic from frame {x['in']}" if x["scene"] else f"clip {x['src']} from frame {x['in']}")
              + (f" at {x['speed']:g}x" if x["speed"] != 1 else "")
              + f" - room {x['room_start']} before / {x['room_end']} after" + (" (held / stutter: cannot grow)"
                                                                            if x["special"] else "")
              + (f"; with it: {', '.join(x['attached'])}" if x["attached"] else ""))
    for g in s["graphics"]:
        if g["captions"]:
            continue
        print(f"  graphic {g['id']} ({g['folder']}) {tc(g['start'])}-{tc(g['end'])}: "
              + ("; ".join(f"{w['key']}=\"{w['value']}\"" for w in g["words"]) or "(no words)"))
    for c in s["captions"]:
        print(f"  caption {c['cue'] + 1} at {tc(c['f'])}: \"{c['text']}\"" + (" (its end, said over a cut)" if c.get("tail")
                                                                              else ""))
    for q in s["sfx"]:
        print(f"  sound {q['kind']} at {tc(q['f'])} - {q['what']} ({q['sound'] or 'made-up'}"
              + (f", {q['db']:+g} dB" if q["db"] else "") + ")")
    return 0


def _run(args: list[str], what: str) -> str:
    r = subprocess.run([PY, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(LAB))
    if r.returncode:
        raise SystemExit(f"{what} failed:\n{(r.stdout + r.stderr)[-800:]}")
    return r.stdout


def _captions(folder: Path, cues: list[dict]) -> None:
    """A captions graphic's captions (assets\\captions.js) written whole: the list the Editor's changes made (the
    engine's step "capfile" - new words, other frames, split, added, removed)."""
    from motionlab import captions as CAP
    js = folder / "assets" / "captions.js"
    txt = js.read_text(encoding="utf-8")
    i = txt.index("window.CAPTIONS")
    data = json.loads(txt[txt.index("=", i) + 1:].strip().rstrip(";"))
    cues_f = [{"f0": int(c["f0"]), "f1": int(c["f1"]), "words": [{"w": w[0], "f0": int(w[1]), "f1": int(w[2])}
                                                                  for w in c["words"]]} for c in cues]
    js.write_text(CAP.captions_js(cues_f, float(data.get("fps", 25)), str(data.get("source", "")),
                                  bool(data.get("estimated"))), encoding="utf-8")


def _sound_again(prj: Project, P: dict, base: dict, v: int) -> str:
    """The clips' own sound cut to the new shots (draft_edit.py's own steps; a shot's speed stretches its part): the
    new "audio" path."""
    import draft_edit as DE
    talk = (base.get("made_by") or {}).get("sound") == "talk"          # a talking video's voice is levelled again
    _, clips, _, _ = DE.footage(prj, int(P["width"]), int(P["height"]))
    d = prj.check(prj.build / "draft")
    segs = M.sound_segments(P)
    DE.clip_sound(prj, clips, d, float(P["fps"]), "clips", only={s[0] for s in segs}, reuse=d)
    by_id = {c["id"]: c for c in clips}
    y = DE.cut_sound(segs, by_id, float(P["fps"]), d, level="take" if talk else None)
    return str(DE.write_sound(prj, d, v, y))


def _song_cut(prj: Project, s: dict, v: int, dur_s: float) -> str:
    """The song from s["start_s"] for the video's length (+ 1 s), s["db"] louder / softer -> build\\song_from_editor_vN.m4a
    (a "song" to the Editor next time: motionlab\\miniedit.sound_mode). The song itself is only read."""
    src = Path(s["from"])
    if not src.is_file():
        raise SystemExit(f"the song is not there any more: {src}")
    out = prj.check(prj.build / f"song_from_editor_v{v}.m4a")
    r = subprocess.run([tool("ffmpeg"), "-y", "-v", "error", "-nostdin", "-ss", f"{float(s['start_s']):.3f}", "-i",
                        str(src), "-t", f"{dur_s + 1:.3f}", "-map", "0:a:0", "-af", f"volume={float(s['db']):g}dB",
                        "-c:a", "aac", "-b:a", "192k", str(out)], capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    if r.returncode or not out.exists():
        raise SystemExit(f"could not cut the song: {r.stderr[-400:]}")
    return str(out)


def cmd_apply(a) -> int:
    t0 = time.time()
    prj = Project(a.project)
    bp = base_plan(prj, a.plan)
    base = json.loads(bp.read_text(encoding="utf-8"))
    ops = json.loads(Path(a.changes).read_text(encoding="utf-8"))
    if not isinstance(ops, list) or not ops:
        raise SystemExit("the changes file holds no changes (a JSON list)")
    import draft_edit as DE
    v = DE.next_version(prj.build, prj.name)
    try:
        P, done, steps = M.apply(base, ops, tag=f"m{v}", build=prj.build)
    except M.EditError as e:
        raise SystemExit(str(e))
    fps = float(P["fps"])
    for s in steps:                                         # the graphics' copies and new ones, their settings
        if s["op"] == "copy":
            _run([str(TOOLS / "overlay.py"), "new", str(prj.check(Path(s["to"]))), "--from", s["from"]],
                 f"copying {Path(s['from']).name}")
        elif s["op"] == "new":
            _run([str(TOOLS / "overlay.py"), "new", str(prj.check(Path(s["to"]))), "--from", s["template"],
                  "--frames", str(s["frames"]), "--fps", f"{fps:g}", "--width", str(int(P["width"])),
                  "--height", str(int(P["height"])), "--force"]
                 + (["--values", json.dumps(s["values"], ensure_ascii=False)] if s["values"] else []),
                 f"the template {s['template']}")
        elif s["op"] in ("set", "values"):                 # a setting, or a look's values at once
            try:
                OS.set_values(prj.check(Path(s["folder"])), s["values"] if s["op"] == "values" else {s["key"]: s["value"]})
            except ValueError as e:
                raise SystemExit(f"{Path(s['folder']).name}: {e}")
        elif s["op"] == "capfile":                         # (after its copy: the engine lists it last)
            _captions(prj.check(Path(s["folder"])), s["cues"])
        elif s["op"] == "songcut":                         # the song from its new start, louder / softer
            P["audio"] = {**P["audio"], "path": _song_cut(prj, s, v, int(P["frames"]) / fps)}
            done.append(f"sound: the song cut again -> song_from_editor_v{v}.m4a")
    mode = M.sound_mode(base)
    base_audio = Path(str((base.get("audio") or {}).get("path") or ""))
    mixed = base_audio.parent.name == "sfx" and base_audio.stem.endswith(("_mix", "_sfx"))
    if (mixed or P.get("cues")) and not P.get("sfx"):
        P["sfx"] = True                                     # it has sound effects: build.py makes them (again)
    if mode == "follows" and any(o.get("op") in M.SHOT_OPS + M.FX_OPS for o in ops):
        P["audio"] = {**(P.get("audio") or {}), "path": _sound_again(prj, P, base, v)}
        done.append("sound: the clips' own sound cut again to the shots")
    P["name"], P["output"] = f"{prj.name}_v{v}", f"{prj.name}_v{v}.mp4"
    P["made_by"] = {"tool": "miniedit.py", "list": f"edit_v{v}.list", "from": bp.name,
                    "sound": (base.get("made_by") or {}).get("sound"), "date": time.strftime("%Y-%m-%d %H:%M")}
    out = prj.check(prj.build / f"plan_v{v}.json")
    out.write_text(json.dumps(M.saved(P), indent=1, ensure_ascii=False), encoding="utf-8")
    prj.check(prj.build / f"edit_v{v}.list").write_text(M.record(bp.name, ops, done), encoding="utf-8")
    oc = prj.check(prj.build / "outcome.json")              # what the user fixed by hand: Claude reads it next time
    try:
        o = json.loads(oc.read_text(encoding="utf-8")) if oc.exists() else {}
    except ValueError:
        o = {}
    o["hand_fixes"] = ([*(o.get("hand_fixes") or []), {"date": time.strftime("%Y-%m-%d %H:%M"), "from": bp.name,
                                                        "to": out.name, "changes": done}])[-20:]
    oc.write_text(json.dumps(o, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{bp.name} + {len(ops)} change(s) -> {out.name} ({int(P['frames'])} frames, last "
          f"{frame_to_tc(int(P['frames']) - 1, fps)}) in {time.time() - t0:.1f} s:")
    for ln in done:
        print("  " + ln)
    if not a.build:
        print(f"next: .venv\\Scripts\\python tools\\build.py {prj.name} {out.name}")
        print(out)
        return 0
    r = subprocess.run([PY, str(TOOLS / "build.py"), str(prj.dir), out.name], cwd=str(LAB))
    print(out)
    return 0 if r.returncode in (0, 2) else r.returncode


# ------------------------------------------------------------------------------------------- the preview's media
def _wave(src: Path, fps: float, offset_s: float, frames: int | None = None) -> list[int]:
    """A sound's loudness per frame, 0 (-60 dBFS or under) .. 100 (0 dBFS): frame i = the sound at i / fps + offset_s
    (the save's own alignment of a clip's sound, draft_edit.cut_sound)."""
    import numpy as np
    r = subprocess.run([tool("ffmpeg"), "-v", "error", "-nostdin", "-i", str(src), "-map", "0:a:0", "-ac", "1", "-ar",
                        str(WAVE_SR), "-f", "s16le", "pipe:1"], capture_output=True)
    y = np.frombuffer(r.stdout, np.int16).astype(np.float32) / 32768.0 if r.returncode == 0 else np.zeros(0, np.float32)
    per = WAVE_SR / fps
    n = frames if frames is not None else int(len(y) / per - offset_s * fps)
    out = []
    for i in range(max(0, n)):
        a = int(round((i / fps + offset_s) * WAVE_SR))
        seg = y[max(0, a):max(0, int(a + per))]
        pk = float(np.abs(seg).max()) if seg.size else 0.0
        out.append(int(max(0.0, min(100.0, (20 * np.log10(max(pk, 1e-6)) + 60) / 60 * 100))))
    return out


def _proxy(src: Path, dst: Path, fps: float) -> None:
    part = dst.with_name(dst.stem + ".part.mp4")
    s, g = M.PROXY_SHORT, str(M.PROXY_GOP)
    vf = (f"fps={fps:g},scale='if(gt(iw,ih),-2,{s})':'if(gt(iw,ih),{s},-2)':flags=bilinear,format=yuv420p")
    r = subprocess.run([tool("ffmpeg"), "-v", "error", "-nostdin", "-y", "-i", str(src), "-map", "0:v:0", "-map",
                        "0:a:0?", "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "27", "-g", g,
                        "-keyint_min", g, "-sc_threshold", "0", "-bf", "0", "-c:a", "aac", "-b:a", "128k",
                        "-ac", "2", "-movflags", "+faststart", str(part)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode or not part.exists():
        raise SystemExit(f"the preview copy of {src.name} failed: {r.stderr[-500:]}")
    part.replace(dst)


def _strip(proxy: Path, dst: Path) -> dict:
    """The timeline's filmstrip of a clip: one picture every STRIP_EVERY s, STRIP_H px high, in a grid of STRIP_COLS
    (one ffmpeg run on the light copy; the page shows its cells with CSS - no request per picture)."""
    import math
    from motionlab.probe import probe
    info = probe(proxy)
    v, dur = info["video"], float(info.get("duration_s") or 0)
    w, h = int(v.get("display_width") or v.get("width") or 16), int(v.get("display_height") or v.get("height") or 9)
    tw = max(2, int(round(STRIP_H * w / max(1, h) / 2)) * 2)
    n = max(1, int(math.ceil(dur / STRIP_EVERY)))
    rows = max(1, int(math.ceil(n / STRIP_COLS)))
    part = dst.with_name(dst.stem + ".part.jpg")
    r = subprocess.run([tool("ffmpeg"), "-v", "error", "-nostdin", "-y", "-i", str(proxy), "-vf",
                        f"fps=1/{STRIP_EVERY:g},scale={tw}:{STRIP_H},tile={STRIP_COLS}x{rows}", "-frames:v", "1",
                        "-q:v", "5", str(part)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode or not part.exists():
        raise SystemExit(f"the filmstrip of {proxy.name} failed: {r.stderr[-400:]}")
    part.replace(dst)
    return {"every": STRIP_EVERY, "cols": STRIP_COLS, "rows": rows, "n": n, "tw": tw, "th": STRIP_H}


def cmd_media(a) -> int:
    t0 = time.time()
    prj = Project(a.project)
    bp = base_plan(prj, a.plan)
    P = json.loads(bp.read_text(encoding="utf-8"))
    fps = float(P["fps"])
    d = prj.check(prj.build / "editor")
    d.mkdir(parents=True, exist_ok=True)
    idx_p = d / "media.json"
    try:
        idx = json.loads(idx_p.read_text(encoding="utf-8")) if idx_p.exists() else {}
    except ValueError:
        idx = {}
    from motionlab.probe import probe
    used = {L.get("src") for L in P.get("layers", []) if L.get("type") == "clip"}
    for sid, s in sorted((P.get("sources") or {}).items(), key=lambda kv: kv[0] not in used):   # (the shots' clips
        src = Path(str(s.get("source") or ""))                                     # first; the rest can be added)
        if not src.is_file() or src.suffix.lower() in PHOTO_EXT:
            continue
        key = media_key(src, fps)
        mp4, wav, jpg = d / f"{sid}_{key}.mp4", d / f"{sid}_{key}.wave.json", d / f"{sid}_{key}.strip.jpg"
        if not mp4.exists():
            print(f"{sid} {src.name}: the preview copy ...", flush=True)
            t1 = time.time()
            _proxy(src, prj.check(mp4), fps)
            print(f"  {mp4.name} ({mp4.stat().st_size / 1e6:.1f} MB) in {time.time() - t1:.1f} s", flush=True)
        strip = (idx.get(sid) or {}).get("strip") if (idx.get(sid) or {}).get("key") == key else None
        if not jpg.exists() or not strip:
            strip = _strip(mp4, prj.check(jpg))
            print(f"{sid}: its filmstrip, {strip['n']} pictures", flush=True)
        if not wav.exists():
            info = probe(src)
            off = float(info["video"].get("start_time") or 0) - float((info["audio"] or {}).get("start_time") or 0)
            w = _wave(src, fps, off) if info.get("audio") else []
            prj.check(wav).write_text(json.dumps({"fps": fps, "offset_s": off, "peaks": w}), encoding="utf-8")
            print(f"{sid}: its sound, {len(w)} frames", flush=True)
        idx[sid] = {"source": str(src), "key": key, "proxy": mp4.name, "wave": wav.name, "strip_file": jpg.name,
                    "strip": strip}
        prj.check(idx_p).write_text(json.dumps(idx, indent=1), encoding="utf-8")     # (the page can start on these)
    song = M.song_source(P)                                 # (a song the Editor cut: the song itself, played from its start)
    if M.sound_mode(P) == "song" and song and song.is_file():
        key = media_key(song, fps)
        wav = d / f"song_{key}.all.wave.json"               # the whole song: its start can move in the Editor
        if not wav.exists():
            w = _wave(song, fps, 0.0)
            prj.check(wav).write_text(json.dumps({"fps": fps, "offset_s": 0.0, "peaks": w}), encoding="utf-8")
            print(f"the song: {len(w)} frames", flush=True)
        idx["_song"] = {"source": str(song), "key": key, "wave": wav.name}
    prj.check(idx_p).write_text(json.dumps(idx, indent=1), encoding="utf-8")
    print(f"the Editor's media for {bp.name}: {len([k for k in idx if not k.startswith('_')])} clip(s) in "
          f"{time.time() - t0:.1f} s")
    print(idx_p)
    return 0


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("state")
    s.add_argument("project")
    s.add_argument("plan", nargs="?")
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("apply")
    s.add_argument("project")
    s.add_argument("changes")
    s.add_argument("--plan")
    s.add_argument("--build", action="store_true")
    s = sub.add_parser("media")
    s.add_argument("project")
    s.add_argument("--plan")
    sub.add_parser("selfcheck")
    a = ap.parse_args()
    if a.cmd == "selfcheck":
        r = M.selfcheck()
        print("\n".join(r["lines"]))
        print("PASS" if r["passed"] else "FAIL")
        return 0 if r["passed"] else 1
    return {"state": cmd_state, "apply": cmd_apply, "media": cmd_media}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
