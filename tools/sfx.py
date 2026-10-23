"""Sound effects for a graphic or an edit (0.5.0): synthesised (no samples, nothing to license), the same every run,
48 kHz, each one levelled against the song under it - measured, since Claude cannot hear (motionlab\\sfx.py).

    .venv\\Scripts\\python tools\\sfx.py cues <graphic folder | cues.json | plan.json> [--set search_text="Hi"]
          the cues with frame + timecode, kind and level class - no sound made. A graphic's cues are in its
          overlay.json ("cues", next to its settings; format in motionlab\\sfx.py); --set tries a setting unsaved
    .venv\\Scripts\\python tools\\sfx.py make <graphic folder | cues.json | plan.json> --song <audio | none>
          [--song-start 0] [--song-db -2.5] [--ceiling -1] [--fade 0.8] [--out <folder>] [--name N] [--set id=value]
          [--floor-vs-song -24 | off] [--all]   (0.5.3: no effect sits further under the song than -24 dB - the
          precheck's "buried" line + 2 - so the levels pass first time; the output is a summary + the cues the
          precheck would flag, --all = every cue)
          -> <out>\\<name>_sfx.wav   the effects alone, 24-bit 48 kHz from frame 0 (DaVinci Resolve: its own audio
                                    track at the timeline's start, 01:00:00:00)
             <out>\\<name>_mix.wav   the song (--song-db lower) + the effects, a peak limiter at --ceiling dBFS, a
                                    --fade s fade at the end (the lab render: the plan's "audio")
             <out>\\<name>_sfx.json  every cue with its measured levels (the song where it sounds, the effect, the
                                    rule that set it: song / floor / peak cap; the limiter)
          prints the plan change to make. <out> = the project's build\\sfx\\ (a cues file: its folder)
    .venv\\Scripts\\python tools\\sfx.py plan <plan.json> [--song <audio>] [...]   = make for an edit: its effects
          (fast zooms, whips and slides, flashes, black frames, speed-ups, stutters, colour flashes, dips, shakes)
          + the cues of the graphics it shows + its own "cues"; the song = the plan's "audio" (a mix made here before:
          the song it was made from)
    .venv\\Scripts\\python tools\\sfx.py kinds        the sounds and their level classes
    .venv\\Scripts\\python tools\\sfx.py selfcheck    known answers, no video (onsets, levels, ceiling, same twice)
Songs and videos are only read; files are written only into projects\\<name>\\build\\ (or the lab's .app\\).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import sfx as SFX  # noqa: E402
from motionlab.timecode import frame_to_tc  # noqa: E402
from motionlab.util import setup_console, write_json  # noqa: E402


def settings_arg(items: list[str] | None) -> dict:
    out = {}
    for it in items or []:
        if "=" not in it:
            raise SystemExit(f"--set id=value (not {it!r})")
        k, v = it.split("=", 1)
        out[k.strip()] = v
    return out


def load_source(src: Path, override: dict) -> tuple[str, list, float, int, dict, dict | None]:
    """(what it is, cues, fps, frames, settings, the plan)."""
    try:
        if src.is_dir():
            if not (src / "overlay.json").exists():
                raise SystemExit(f"{src} has no overlay.json (a graphic folder: overlay.py new)")
            cues, fps, frames, vals = SFX.graphic_cues(src, override)
            return "graphic", cues, fps, frames, vals, None
        d = json.loads(src.read_text(encoding="utf-8"))
        if isinstance(d, dict) and "layers" in d:
            if override:
                raise SystemExit("--set is for a graphic's settings, not a plan")
            from motionlab.compose import resolve_paths
            resolve_paths(d, src.resolve().parent)
            notes: list[str] = []
            cues = SFX.plan_cues(d, notes)
            for n in notes:
                print(f"NOTE {n}")
            return "plan", cues, float(d["fps"]), int(d["frames"]), {}, d
        cues, fps, frames, vals = SFX.cues_file(src, override)
        return "cues", cues, fps, frames, vals, None
    except ValueError as e:
        raise SystemExit(f"ERROR: {e}")


def default_out(src: Path, what: str) -> Path:
    src = src.resolve()
    if what == "plan":
        return src.parent / "sfx"
    if what == "graphic":
        return (src.parents[1] / "sfx") if src.parent.name == "overlays" else src / "sfx"
    return src.parent


def song_of_plan(plan: dict) -> tuple[Path | None, float, float | None, str]:
    """The plan's sound; when it is a mix made here, the song it was made from (no effects twice)."""
    a = (plan.get("audio") or {}).get("path")
    if not a:
        return None, 0.0, None, "the plan has no sound"
    p = Path(a)
    if p.name.endswith("_mix.wav"):
        rep = p.with_name(p.name[:-len("_mix.wav")] + "_sfx.json")
        if rep.exists():
            r = json.loads(rep.read_text(encoding="utf-8"))
            s = r.get("song") or {}
            if s.get("path"):
                return Path(s["path"]), float(s.get("start_s") or 0), s.get("db"), (
                    f"the plan's sound is a mix made by sfx.py - its song instead: {Path(s['path']).name}")
    return p, 0.0, None, "the plan's sound"


def cmd_cues(a) -> int:
    src = Path(a.source)
    what, cues, fps, frames, vals, _ = load_source(src, settings_arg(a.set))
    used = sorted({u for q in cues for u in q.get("uses", []) if u in vals})
    print(f"{src.name}: {len(cues)} cues, {frames} frames at {fps:g} fps (f0 = 00:00:00:00, last "
          f"f{frames - 1} ({frame_to_tc(frames - 1, fps)}))"
          + ("; settings that move cues: " + ", ".join(f"{k} = {vals[k]!r}" for k in used) if used else ""))
    for q in sorted(cues, key=lambda c: c["f"]):
        print(SFX.cue_line(q, fps))
    late = [q for q in cues if not 0 <= q["f"] < frames]
    if late:
        print(f"WARNING: {len(late)} cue(s) outside f0-f{frames - 1}: " + ", ".join(f"f{q['f']}" for q in late))
    return 0


def graphic_of(cues_json: Path) -> Path | None:
    g = json.loads(cues_json.read_text(encoding="utf-8")).get("graphic")
    return None if not g else Path(g) if Path(g).is_absolute() else (cues_json.parent / g).resolve()


def plans_using(folder: Path) -> list[Path]:
    """The project's plans that show this graphic (newest first)."""
    build = folder.resolve().parents[1] if folder.resolve().parent.name == "overlays" else None
    out = []
    for p in sorted(build.glob("plan_v*.json"), key=lambda x: x.stat().st_mtime, reverse=True) if build else []:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if any(L.get("type") == "overlay" and Path(str(L.get("file", ""))).parent.resolve() == folder.resolve()
               for L in d.get("layers", [])):
            out.append(p)
    return out


def cmd_make(a, plan_only: bool = False) -> int:
    t0 = time.time()
    src = Path(a.source)
    what, cues, fps, frames, vals, plan = load_source(src, settings_arg(a.set))
    if plan_only and what != "plan":
        raise SystemExit(f"{src.name} is not a plan (a plan has \"layers\"); use: sfx.py make {src}")
    song_note, song_db = "", a.song_db
    if a.song and a.song.lower() == "none":
        song_path, start = None, 0.0
    elif a.song:
        song_path, start = Path(a.song), a.song_start
    elif what == "plan":
        song_path, start, rec_db, song_note = song_of_plan(plan)
        if rec_db is not None and a.song_db == SFX.SONG_DB:
            song_db = float(rec_db)
    else:
        raise SystemExit("--song <audio file> (or --song none: each effect at its kind's lowest level)")
    if song_path is not None and not song_path.is_file():
        raise SystemExit(f"ERROR: no such file: {song_path}")
    try:
        out = SFX.safe_out(Path(a.out) if a.out else default_out(src, what))
    except PermissionError as e:
        raise SystemExit(f"ERROR: {e}")
    name = SFX.stem_name(a.name or (plan or {}).get("name") or (src.name if src.is_dir() else src.stem))
    files = {"stem": out / f"{name}_sfx.wav", "mix": out / f"{name}_mix.wav", "report": out / f"{name}_sfx.json"}
    if song_path is not None and any(f.resolve() == song_path.resolve() for f in files.values()):
        raise SystemExit(f"ERROR: {song_path.name} is the song - choose another --name or --out")
    song = None
    if song_path is not None:
        try:
            song = SFX.load_audio(song_path, start, frames / fps + 0.1)
        except ValueError as e:
            raise SystemExit(f"ERROR: {e}")
    t1 = time.time()
    res = SFX.build(cues, fps, frames, song, song_db, a.ceiling, a.fade,
                    floor_vs_song=None if a.floor_vs_song.lower() == "off" else float(a.floor_vs_song))
    t2 = time.time()
    out.mkdir(parents=True, exist_ok=True)
    SFX.write_wav(files["stem"], res["stem"])
    if song is not None:
        SFX.write_wav(files["mix"], res["mix"])
    sec = frames / fps
    used = sorted({u for q in cues for u in q.get("uses", []) if u in vals})
    print(f"{src.name}: {len(cues)} cues, {frames} frames at {fps:g} fps ({sec:.1f} s)"
          + ("; settings that move cues: " + ", ".join(f"{k} = {vals[k]!r}" for k in used) if used else ""))
    if song is not None:
        sg = song[:res["N"]]
        print(f"song: {song_path.name} from {start:g} s, {song_db:+g} dB" + (f" ({song_note})" if song_note else "")
              + f" - {SFX.rms_db(sg) + song_db:.1f} dBFS RMS over the video" + (
                  f" (only {len(sg) / SFX.SR:.1f} s long: silence after)" if len(sg) < res["N"] else ""))
    else:
        print("no song: every effect at its kind's lowest level")
    rows = [r for r in res["rows"] if "sample" in r]
    if a.all or len(res["rows"]) <= 12:
        print("  frame (timecode)     kind      song dBFS  effect dBFS (vs song)   peak         rule")
        for r in res["rows"]:
            print(SFX.level_line(r))
    else:                                             # 0.5.3 (C5): a summary; --all = every cue as before
        from collections import Counter
        from motionlab import precheck as PC
        kinds, rules = Counter(r["kind"] for r in rows), Counter(r["rule"] for r in rows)
        vs = [r["vs_song_db"] for r in rows if r.get("vs_song_db") is not None]
        print(f"cues: {', '.join(f'{n} {k}' for k, n in kinds.most_common())}; levels set by "
              + ", ".join(f"{k} {n}" for k, n in rules.most_common())
              + (f"; vs the song {min(vs):+.1f} to {max(vs):+.1f} dB" if vs else "")
              + (f"; {len(res['rows']) - len(rows)} outside the video" if len(res["rows"]) > len(rows) else ""))
        flagged = {f["frames"][0] for f in PC.sound_flags({"fps": fps, "cues": rows})}
        for r in rows:
            if r["f"] in flagged:
                print("  FLAG " + SFX.level_line(r).strip())
        print(f"  {len(flagged)} cue(s) the precheck would flag" + ("" if flagged else " - none")
              + "; every cue: --all, or the report below")
    lim = res["limiter_frames"]
    print(f"mix: peak {res['mix_peak_before_db']:.1f} dBFS before the limiter, {res['mix_peak_db']:.1f} after (ceiling "
          f"{a.ceiling:g}); the limiter took up to {-res['limiter_max_db']:.1f} dB"
          + (" at " + ", ".join(f"f{x}-{y} ({frame_to_tc(x, fps)}-{frame_to_tc(y, fps)})" for x, y in lim[:6])
             + (f" +{len(lim) - 6} more" if len(lim) > 6 else "") if lim else ""))
    if res["stem_limited_db"] < -0.01:
        print(f"effects stem: overlapping effects peaked at {res['stem_peak_before_db']:.1f} dBFS - limited by "
              f"{-res['stem_limited_db']:.1f} dB to the ceiling")
    write_json(files["report"], {
        "source": SFX.rel(src), "kind": what, "fps": fps, "frames": frames, "settings": vals,
        "song": ({"path": str(song_path.resolve()), "start_s": start, "db": song_db} if song_path else None),
        "ceiling_db": a.ceiling, "fade_s": a.fade, "levels": SFX.LEVELS, "peak_db": SFX.PEAK_DB,
        "stem": SFX.rel(files["stem"]), "mix": SFX.rel(files["mix"]) if song is not None else None,
        **{k: res[k] for k in ("mix_peak_before_db", "mix_peak_db", "limiter_max_db", "limiter_frames",
                               "stem_peak_before_db", "stem_limited_db")},
        "cues": [{k: v for k, v in r.items() if k not in ("loud", "window", "sample")} for r in res["rows"]],
        "date": time.strftime("%Y-%m-%d %H:%M"), "seconds": round(time.time() - t0, 2)})
    el = time.time() - t0
    print(f"{len(cues)} sound effects in {el:.1f} s ({el / max(sec / 60, 1e-9):.1f} s per minute of video; the sounds "
          f"and the mix {t2 - t1:.1f} s)")
    print(f"  {files['stem']}   (the effects alone - DaVinci Resolve: its own track at 01:00:00:00)")
    if song is not None:
        print(f"  {files['mix']}   (song + effects)")
    print(f"  {files['report']}")
    if song is not None:
        audio = {"path": str(files["mix"].resolve())}
        if plan and (plan.get("audio") or {}).get("trim_to_video") is not None:
            audio["trim_to_video"] = plan["audio"]["trim_to_video"]
        g = src if what == "graphic" else graphic_of(src) if what == "cues" else None
        target = [src] if what == "plan" else plans_using(g) if g else []
        where = f"in {target[0].name}" if target else "in the plan that shows it"
        print(f"the plan change ({where}; the mix starts at the plan's frame 0):\n  \"audio\": "
              + json.dumps(audio, ensure_ascii=False))
    return 0


def cmd_kinds(a) -> int:
    print("level classes (stereo RMS): dB against the song where the effect sounds, the lowest level in dBFS")
    for k, (rel, floor) in SFX.LEVELS.items():
        print(f"  {k:10s} {rel:+4d} dB, at least {floor} dBFS")
    print(f"an effect's peak at most {SFX.PEAK_DB:g} dBFS; the mix at most {SFX.CEILING_DB:g} dBFS")
    print("kinds (numbers = the cue fields that change them, with their defaults):")
    for k, (_, d, lvl, what) in SFX.KINDS.items():
        nums = ", ".join(f"{p}={v}" for p, v in d.items())
        print(f"  {k:9s} {lvl:9s} {what}" + (f"  [{nums}]" if nums else ""))
    print("also: " + ", ".join(f"{a} = {b}" for a, b in SFX.ALIASES.items()))
    return 0


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("cues")
    s.add_argument("source")
    s.add_argument("--set", action="append", metavar="ID=VALUE")
    for nm in ("make", "plan"):
        s = sub.add_parser(nm)
        s.add_argument("source")
        s.add_argument("--song", help="the song (any audio or video file), or none")
        s.add_argument("--song-start", type=float, default=0.0, help="seconds into the song = frame 0")
        s.add_argument("--song-db", type=float, default=SFX.SONG_DB, help="the song lowered by this (dB)")
        s.add_argument("--ceiling", type=float, default=SFX.CEILING_DB, help="the mix's highest sample (dBFS)")
        s.add_argument("--fade", type=float, default=SFX.FADE_S, help="fade-out at the end (seconds, 0 = none)")
        s.add_argument("--out", help="the folder (default: the project's build\\sfx\\)")
        s.add_argument("--name", help="the files' name (default: the graphic's / plan's)")
        s.add_argument("--set", action="append", metavar="ID=VALUE", help="a graphic's setting, not saved")
        s.add_argument("--floor-vs-song", default=str(SFX.FLOOR_VS_SONG_DB), metavar="DB",
                       help="no effect further under the song than this (dB; the precheck's buried line + 2; off)")
        s.add_argument("--all", action="store_true", help="print every cue's levels (default: a summary + flags)")
    sub.add_parser("kinds")
    sub.add_parser("selfcheck")
    a = ap.parse_args()
    if a.cmd == "cues":
        return cmd_cues(a)
    if a.cmd in ("make", "plan"):
        if not -12 <= a.ceiling <= 0:
            raise SystemExit("--ceiling: -12..0 dBFS")
        return cmd_make(a, plan_only=a.cmd == "plan")
    if a.cmd == "kinds":
        return cmd_kinds(a)
    if a.cmd == "selfcheck":
        return 0 if SFX.selfcheck()["ok"] else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
