"""Sound effects for a graphic or an edit (0.5.0): recorded sounds from this PC's library (0.5.4, library\\sounds)
where a kind has them, else made up (synthesised); the same every run, 48 kHz, each one levelled against the song
under it - measured, since Claude cannot hear (motionlab\\sfx.py).

    .venv\\Scripts\\python tools\\sfx.py cues <graphic folder | cues.json | plan.json> [--set search_text="Hi"]
          the cues with frame + timecode, kind and level class - no sound made. A graphic's cues are in its
          overlay.json ("cues", next to its settings; format in motionlab\\sfx.py); --set tries a setting unsaved
    .venv\\Scripts\\python tools\\sfx.py make <graphic folder | cues.json | plan.json> --song <audio | none>
          [--song-start 0] [--song-db -2.5] [--ceiling -1] [--fade 0.8] [--out <folder>] [--name N] [--set id=value]
          [--floor-vs-song -24 | off] [--all] [--voice]   (0.5.3: no effect sits further under the song than -24 dB -
          the precheck's "buried" line + 2 - so the levels pass first time; the output is a summary + the cues the
          precheck would flag, --all = every cue). --voice (0.6.0; a plan's "sfx": {"voice": true}, or a talking
          draft's "song_db": 0) = the song is a voice: not lowered, the words found in it, an effect over a word very
          subtle (at least 22 dB under it), one in a pause levelled against the voice around it
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
          make / plan --synth = made-up sounds only (the report's "sound" per cue: a library file or made-up)
    .venv\\Scripts\\python tools\\sfx.py kinds        the sounds and their level classes (+ the library's counts)
    .venv\\Scripts\\python tools\\sfx.py library [--synth-too whoosh,whip] [--off tick/a.wav,...] [--on ...]   the
          recorded library per kind, sources, licences; --synth-too = kinds that keep the made-up sound among their
          recorded ones; --off = sounds never used (the user did not pick them; the file stays), --on = used again;
          --fav / --unfav (0.6.0) = favourites, used first (a kind with any uses only them); --export-list (0.6.0) =
          tools\\sounds\\import_list.json, what the repo shares: which sound of which pack is which kind, off or a
          favourite, each pack's page and licence - never the sounds, but the CC0 ones copied into tools\\sounds\\cc0\\
          (every PC gets those by itself)
    .venv\\Scripts\\python tools\\sfx.py import <folder | file> --from "<pack / site>" --licence "<what it allows>"
          [--kind K] [--skip "apple*,*demo*"] [--dry-run]   recorded sounds into library\\sounds (never shared): the
          kind from each folder + file name (or --kind), cut to the sound, its anchor measured, a 24-bit copy + its
          row in sounds.json (source, licence, SHA-256); the files are only read. Check the licence first.
          --listed (0.6.0, no --from / --licence) = a pack the shared list knows: only its listed sounds, as their
          kinds (matched by SHA-256, else their path in the pack), off / favourite as listed; with --from / --licence
          too, the rest by their names. A sounds zip or an https / Google Drive link to one = sorted by its list.json
    .venv\\Scripts\\python tools\\sfx.py generate [--want pop:6,whoosh:4] [--dry-run]   (0.6.0) sounds made with
          ElevenLabs (the user's key: knowledge\\local\\elevenlabs.json; descriptions per kind in
          tools\\sounds\\generate.json; about 10 credits a second asked, the free plan 10,000 a month and NO commercial
          licence) into the library with the plan's licence - the user listens and keeps (Motion Graphics > Sounds)
    .venv\\Scripts\\python tools\\sfx.py share     (0.6.0) the sounds made on a paid plan as one zip for Google Drive
          (.app\\share\\); a friend: import <the link>
    .venv\\Scripts\\python tools\\sfx.py selfcheck    known answers, no video (onsets, levels, ceiling, same twice)
Songs, videos and sound packs are only read; files are written only into projects\\<name>\\build\\ (or the lab's
.app\\), and import into library\\sounds\\.
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
from motionlab.util import LAB, setup_console, write_json  # noqa: E402


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


def song_of_plan(plan: dict) -> tuple[Path | None, float, float | None, str, bool]:
    """The plan's sound; when it is a mix made here, the song it was made from (no effects twice) and whether it
    was a voice."""
    a = (plan.get("audio") or {}).get("path")
    if not a:
        return None, 0.0, None, "the plan has no sound", False
    p = Path(a)
    if p.name.endswith(("_mix.wav", "_sfx.wav")):          # (the effects alone are a video's sound when it has no song)
        rep = p.with_name(p.name[:-len("_mix.wav")] + "_sfx.json")
        if rep.exists():
            r = json.loads(rep.read_text(encoding="utf-8"))
            s = r.get("song") or {}
            if s.get("path"):
                return Path(s["path"]), float(s.get("start_s") or 0), s.get("db"), (
                    f"the plan's sound is a mix made by sfx.py - its song instead: {Path(s['path']).name}"), \
                    bool(s.get("voice"))
            return None, 0.0, None, "the plan's sound is effects made by sfx.py, no song - made again", False
    return p, 0.0, None, "the plan's sound", False


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
    song_note, song_db, voice = "", a.song_db, a.voice
    psfx = (plan or {}).get("sfx") if isinstance((plan or {}).get("sfx"), dict) else {}
    voice = voice or bool(psfx.get("voice")) or psfx.get("song_db") == 0     # 0.6.0: a talking video's voice
    if a.song and a.song.lower() == "none":
        song_path, start = None, 0.0
    elif a.song:
        song_path, start = Path(a.song), a.song_start
    elif what == "plan":
        song_path, start, rec_db, song_note, was_voice = song_of_plan(plan)
        voice = voice or was_voice
        if rec_db is None and psfx:                                     # 0.5.4: a talking draft's voice = 0 dB
            rec_db = psfx.get("song_db")
        if rec_db is not None and a.song_db == SFX.SONG_DB:
            song_db = float(rec_db)
    else:
        raise SystemExit("--song <audio file> (or --song none: each effect at its kind's lowest level)")
    if voice and a.song_db == SFX.SONG_DB:
        song_db = 0.0                                                   # a voice is never lowered
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
    lib = None if a.synth else SFX.Library.load()
    if lib is not None and psfx.get("sounds"):                          # 0.6.0: the sounds picked for this edit
        lib = lib.only(psfx["sounds"])
    res = SFX.build(cues, fps, frames, song, song_db, a.ceiling, a.fade,
                    floor_vs_song=None if a.floor_vs_song.lower() == "off" else float(a.floor_vs_song), sounds=lib,
                    voice=voice)
    bed, bed_info = psfx.get("bed") if isinstance(psfx.get("bed"), dict) else None, None
    if bed and bed.get("file"):                          # 0.6.0 step 10: an ambience bed under the voice (music.py)
        from motionlab import music as MU
        bp = Path(bed["file"]) if Path(bed["file"]).is_absolute() else MU.path_of(bed["file"])
        if not bp.is_file():
            raise SystemExit(f"ERROR: the bed {bed['file']} is not there (Motion Graphics > Music)")
        if song is None:
            print(f"NOTE the bed {bp.name} is left out: it goes under a voice or a song, and this plan has none")
        else:
            under = song[:res["N"]] * 10 ** (song_db / 20)
            y, bed_info = MU.bed_layer(under, bp, res["N"], float(bed.get("db", MU.BED_DB)))
            res["mix"], _ = SFX.limit(res["mix"] + y, a.ceiling)
            res["mix_peak_db"] = round(SFX.db(float(abs(res["mix"]).max())), 2)
            bed_info = {"file": str(bp.resolve()), **bed_info}
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
    if bed_info:
        print(f"bed: {Path(bed_info['file']).name} looped under the {'voice' if voice else 'song'}, "
              f"{bed_info['db_vs_voice']:+g} dB under its words ({bed_info['bed_db']:.1f} dBFS)")
    rows = [r for r in res["rows"] if "sample" in r]
    if voice and song is not None:
        ow = [r for r in rows if r.get("on_word")]
        print(f"voice: {len(ow)} cue(s) on a word (very subtle, {SFX.ON_WORD_DB:+g} dB under it at most), "
              f"{sum(1 for r in rows if r.get('on_word') is False)} in a pause (levelled to the voice around it)"
              if any("on_word" in r for r in rows) else "voice: no words found in it - levelled as against a song")
    rec = [r for r in rows if r.get("sound", "made-up") != "made-up"]
    print(f"sounds: {len(rec)} recorded, {len(rows) - len(rec)} made-up" + (
        " (--synth)" if a.synth else "" if lib else f" (no recorded sounds: {SFX.rel(SFX.SOUNDS)}\\sounds.json - "
                                                    "sfx.py import)"))
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
        "song": ({"path": str(song_path.resolve()), "start_s": start, "db": song_db, **({"voice": True} if voice else {})}
                 if song_path else None),
        "ceiling_db": a.ceiling, "fade_s": a.fade, "levels": SFX.LEVELS, "peak_db": SFX.PEAK_DB,
        "sounds": "made-up only (--synth)" if a.synth or not lib else SFX.rel(SFX.SOUNDS),
        "stem": SFX.rel(files["stem"]), "mix": SFX.rel(files["mix"]) if song is not None else None,
        **({"bed": bed_info} if bed_info else {}),
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
    lib = SFX.Library.load()
    if lib:
        print("recorded: " + ", ".join(f"{k} {len(v)}" for k, v in sorted(lib.by_kind.items()))
              + (f"; with the made-up sound too: {', '.join(sorted(lib.synth_too))}" if lib.synth_too else ""))
    return 0


def cmd_library(a) -> int:
    jp = SFX.SOUNDS / "sounds.json"
    data = json.loads(jp.read_text(encoding="utf-8")) if jp.exists() else None
    if (a.synth_too is not None or a.off or a.on or a.fav or a.unfav or a.export_list) and data is None:
        raise SystemExit(f"no library yet ({SFX.rel(jp)}): sfx.py import first")
    if a.synth_too is not None:
        bad = [k for k in a.synth_too.split(",") if k.strip() and k.strip() not in SFX.KINDS]
        if bad:
            raise SystemExit(f"unknown kind(s) {', '.join(bad)}")
        data["synth_too"] = sorted({k.strip() for k in a.synth_too.split(",") if k.strip()})
    for names, key, on in ((a.off, "off", True), (a.on, "off", False), (a.fav, "fav", True), (a.unfav, "fav", False)):
        for n in [x.strip().replace("\\", "/") for x in (names or "").split(",") if x.strip()]:   # 0.5.4 off / on,
            e = next((e for e in data["sounds"] if e["file"] == n), None)                     # 0.6.0 a favourite
            if e is None:
                raise SystemExit(f"no sound {n} in {SFX.rel(jp)} (its \"file\", e.g. tick/tick__sonniss_2.wav)")
            if on:
                e[key] = True
            else:
                e.pop(key, None)
    if a.synth_too is not None or a.off or a.on or a.fav or a.unfav:
        jp.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    if a.export_list:                                       # 0.6.0: what the repo shares (never the sounds but CC0)
        out = SFX.export_list()
        from collections import Counter
        n = Counter(r["pack"] for r in out["sounds"])
        print(f"{SFX.rel(SFX.SOUND_LIST)}: " + ", ".join(f"{out['packs'][k]['name']} {v}" for k, v in n.most_common())
              + f"; the CC0 ones copied into {SFX.rel(SFX.SHIPPED / 'cc0')}")
        miss = [k for k, pk in out["packs"].items() if not pk.get("page")]
        if miss:
            print("no page yet (where a friend downloads it - type it into the list): "
                  + ", ".join(out["packs"][k]["name"] for k in miss))
    if data is None:
        print(f"no recorded sounds yet ({SFX.rel(jp)}) - every effect is made up; add some: sfx.py import <folder>")
        return 0
    from collections import Counter
    rows = data.get("sounds", [])
    missing = [e["file"] for e in rows if not (SFX.SOUNDS / e["file"]).exists()]
    print(f"{SFX.rel(SFX.SOUNDS)}: {len(rows)} recorded sounds" + (f", {len(missing)} files missing" if missing else "")
          + (f"; favourites (used first): {', '.join(e['file'] for e in rows if e.get('fav'))}"
             if any(e.get("fav") for e in rows) else ""))
    by, offs = Counter(e["kind"] for e in rows if not e.get("off")), Counter(e["kind"] for e in rows if e.get("off"))
    for k in SFX.KINDS:
        extra = (" + the made-up one" if k in data.get("synth_too", []) and by.get(k) else "") + (
            f"  ({offs[k]} off)" if offs.get(k) else "")
        print(f"  {k:9s} {by.get(k, 0):3d}{extra}" if by.get(k) else f"  {k:9s}   - made-up{extra}")
    for src, n in Counter(e["source"].split(": ")[0] for e in rows).most_common():
        lic = next(e["licence"] for e in rows if e["source"].split(": ")[0] == src)
        print(f"  from {src}: {n}  (licence: {lic})")
    return 0


def cmd_import(a) -> int:
    from motionlab import sfxgen as GEN
    src, listing = a.source, None
    try:
        if src.startswith("https://") or src.lower().endswith(".zip"):   # 0.6.0: a friend's shared sounds (a zip with
            d = LAB / ".app" / "sound_import" / time.strftime("%Y%m%d-%H%M%S-link")   # its list.json), by a link or as
            z = GEN.fetch_link(src, d, log=lambda m: print(m, flush=True)) if src.startswith("https://") else Path(src)
            listing = GEN.unpack(z, d / "sounds")                               # the file
            src = str(d / "sounds")
            print(f"{len(listing['sounds'])} sound(s) in the zip, sorted by its list", flush=True)
    except GEN.GenError as e:
        raise SystemExit(f"ERROR: {e}")
    if not (a.listed or listing) and not (a.from_ and a.licence):
        raise SystemExit("--from and --licence (or --listed: a pack MotionLab's list knows)")
    try:
        if a.listed or listing:                             # the list's sounds as listed; with --from / --licence the
            r = SFX.import_listed(Path(src), dry=a.dry_run, listing=listing)    # rest too, their kind from their name
            if a.from_ and a.licence and r["unknown"]:
                r2 = SFX.import_sounds(Path(src), a.from_, a.licence, kind=a.kind, dry=a.dry_run,
                                       skip=[x for x in (a.skip or "").split(",") if x.strip()])
                r = {**r, "added": r["added"] + r2["added"], "skipped": r["skipped"] + r2["skipped"],
                     "unknown": r2["unknown"]}
        else:
            r = SFX.import_sounds(Path(src), a.from_, a.licence, kind=a.kind,
                                  skip=[x for x in (a.skip or "").split(",") if x.strip()], dry=a.dry_run)
    except (ValueError, PermissionError, FileNotFoundError) as e:
        raise SystemExit(f"ERROR: {e}")
    for row in r["added"]:
        print(f"  {'would add' if a.dry_run else 'added'} {row['kind']:8s} {row['len_s']:5.2f} s, anchor "
              f"{row['anchor_s']:.3f} s  {row['original']}")
    for k in ("skipped", "same", "unknown"):
        if r[k]:
            print(f"{k} ({len(r[k])}): " + "; ".join(r[k][:40]) + (f" +{len(r[k]) - 40} more" if len(r[k]) > 40 else "")
                  + (" - not on MotionLab's list: left out" if k == "unknown" and a.listed
                     else " - give --kind, or rename the folder" if k == "unknown" else ""))
    print(f"{len(r['added'])} sound(s) {'to add' if a.dry_run else 'added to ' + SFX.rel(SFX.SOUNDS)}")
    return 0


def cmd_generate(a) -> int:
    """0.6.0: sounds made with ElevenLabs (motionlab\\sfxgen.py) into the library."""
    from motionlab import sfxgen as GEN
    want = {}
    for part in [x.strip() for x in (a.want or "").split(",") if x.strip()]:
        k, _, n = part.partition(":")
        want[k.strip()] = int(n or 1)
    if not want:                                            # the list's own numbers
        want = {k: int(v.get("n", 1)) for k, v in GEN.prompts()["kinds"].items()}
    try:
        r = GEN.generate(want, log=lambda m: print(m, flush=True), dry=a.dry_run)
    except GEN.GenError as e:
        raise SystemExit(f"ERROR: {e}")
    n = sum(want.values())
    if a.dry_run:
        print(f"{n} sound(s) = {r['credits']} ElevenLabs credits (plan: {GEN.settings()['plan']}; the free plan has "
              f"{GEN.FREE_CREDITS} a month): " + ", ".join(f"{k} {v}" for k, v in want.items()))
        return 0
    print(f"{r['made']} made ({r['credits']} credits), {len(r['added'])} added to {SFX.rel(SFX.SOUNDS)}"
          + (f"; {len(r['skipped'])} left out (silent)" if r["skipped"] else "") + " - listen to them in Motion "
          "Graphics > Sounds (New)")
    for f in r["added"]:
        print("  " + f)
    return 0


def cmd_share(a) -> int:
    from motionlab import sfxgen as GEN
    try:
        r = GEN.share_zip()
    except GEN.GenError as e:
        raise SystemExit(f"ERROR: {e}")
    print(f"{r['count']} sound(s) made on a paid ElevenLabs plan -> {r['zip']}")
    print("put it on Google Drive (share: anyone with the link) and send the link: Motion Graphics > Sounds > Add "
          "sounds > a link")
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
        s.add_argument("--synth", action="store_true", help="made-up sounds only (not the recorded library)")
        s.add_argument("--voice", action="store_true", help="the song is a voice (a talking video): not lowered, "
                                                            "effects very subtle over words, levelled to the voice "
                                                            "in pauses")
    sub.add_parser("kinds")
    s = sub.add_parser("library")
    s.add_argument("--synth-too", metavar="KINDS", help="kinds that keep the made-up sound among the recorded ones")
    s.add_argument("--off", metavar="FILES", help="sounds never to use (their \"file\", comma-separated) - kept on disk")
    s.add_argument("--on", metavar="FILES", help="sounds set off before, used again")
    s.add_argument("--fav", metavar="FILES", help="favourites: a kind with any uses only them (0.6.0)")
    s.add_argument("--unfav", metavar="FILES", help="no longer favourites")
    s.add_argument("--export-list", action="store_true", help="write tools\\sounds\\import_list.json (shared): "
                                                               "which pack sound is which kind; the CC0 ones copied")
    s = sub.add_parser("import")
    s.add_argument("source", help="a sound file or a folder of them (only read); 0.6.0: a shared sounds zip, or a "
                                   "Google Drive / https link to one (sorted by its list.json)")
    s.add_argument("--from", dest="from_", help="where they came from (pack / site / author)")
    s.add_argument("--licence", help="what the licence allows (recorded with every file)")
    s.add_argument("--listed", action="store_true", help="a pack MotionLab's list knows (tools\\sounds\\"
                                                         "import_list.json): its listed sounds as their kinds")
    s.add_argument("--kind", help="one kind for all (default: from each folder + file name)")
    s.add_argument("--skip", help="file name patterns to leave out, comma-separated (\"apple*,*demo*\")")
    s.add_argument("--dry-run", action="store_true", help="show what would be added, write nothing")
    s = sub.add_parser("generate")
    s.add_argument("--want", help="kind:count, comma-separated (pop:6,whoosh:4); default: tools\\sounds\\generate.json's")
    s.add_argument("--dry-run", action="store_true", help="the credits it would take, nothing sent")
    sub.add_parser("share")
    sub.add_parser("selfcheck")
    a = ap.parse_args()
    if a.cmd == "cues":
        return cmd_cues(a)
    if a.cmd in ("make", "plan"):
        if not -12 <= a.ceiling <= 0:
            raise SystemExit("--ceiling: -12..0 dBFS")
        return cmd_make(a, plan_only=a.cmd == "plan")
    if a.cmd == "generate":
        return cmd_generate(a)
    if a.cmd == "share":
        return cmd_share(a)
    if a.cmd == "kinds":
        return cmd_kinds(a)
    if a.cmd == "library":
        return cmd_library(a)
    if a.cmd == "import":
        return cmd_import(a)
    if a.cmd == "selfcheck":
        return 0 if SFX.selfcheck()["ok"] else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
