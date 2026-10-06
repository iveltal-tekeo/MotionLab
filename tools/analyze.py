"""MotionLab - analyze a reference video (music video / vlog) and build a verifiable effect breakdown.

    .venv\\Scripts\\python tools\\analyze.py <video>              full analysis
    .venv\\Scripts\\python tools\\analyze.py <video> --redetect   reuse cached per-frame metrics (after config tweaks)
    .venv\\Scripts\\python tools\\analyze.py <video> --force      recompute everything

Writes everything to analysis\\<video name>\\ : report.html, events.json, metrics.csv, overview.png,
events\\<ID>\\sheet_NN.jpg + preview.mp4, frames\\, cuts\\, review_todo.md. The source video is only read.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import __version__  # noqa: E402
from motionlab import knowledge as KN  # noqa: E402
from motionlab.styles import CATEGORIES, DEFAULT as CATEGORY_DEFAULT, LEGACY, clean_tags, label as category_label  # noqa: E402
from motionlab import assemble as AS  # noqa: E402
from motionlab import audio as AU  # noqa: E402
from motionlab import describe as DE  # noqa: E402
from motionlab import detect as DT  # noqa: E402
from motionlab import media as ME  # noqa: E402
from motionlab import overview as OV  # noqa: E402
from motionlab import probe as PR  # noqa: E402
from motionlab import signals as SG  # noqa: E402
from motionlab.util import (ANALYSIS, SourceGuard, load_config, log, read_json, safe_name,  # noqa: E402
                            setup_console, sha256_file, write_json)


def pick_out_dir(src: Path, name: str | None) -> tuple[str, Path]:
    base = name or safe_name(src.stem)
    out = ANALYSIS / base
    sj = out / "source.json"
    if not name and sj.exists():
        prev = read_json(sj)
        if Path(prev.get("path", "")).resolve() != src:
            base = f"{base}_{hashlib.sha1(str(src).encode('utf-8')).hexdigest()[:6]}"
            out = ANALYSIS / base
    return base, out


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description="MotionLab video effect analysis")
    ap.add_argument("video")
    ap.add_argument("--name", help="analysis folder name (default: video file name)")
    ap.add_argument("--redetect", action="store_true", help="reuse cached per-frame metrics")
    ap.add_argument("--force", action="store_true", help="recompute everything, ignore caches")
    ap.add_argument("--no-media", action="store_true", help="skip frame extraction / sheets / previews")
    ap.add_argument("--category", "--style", dest="category", choices=list(CATEGORIES) + list(LEGACY),
                    help="what kind of video it is (default: the previous analysis of this video, else music_video)")
    ap.add_argument("--tags", help="comma-separated free tags, e.g. \"instagram, asmr\" (kept on re-runs)")
    args = ap.parse_args()

    cfg = load_config()
    drop_tc = bool(cfg["timecode"]["drop_frame"])
    src = Path(args.video).expanduser().resolve()
    if not src.is_file():
        print(f"ERROR: video not found: {src}")
        return 2
    name, out = pick_out_dir(src, args.name)
    out.mkdir(parents=True, exist_ok=True)
    guard = SourceGuard(src, out)
    log(f"MotionLab {__version__}: {src}")
    log(f"output folder: {out}")

    # ---- 0. fingerprint the source (read-only) -------------------------------------------------
    log("hashing source video (read-only)...")
    sha_before = sha256_file(src)
    source = {"path": str(src), "size": src.stat().st_size, "sha256": sha_before}
    write_json(guard.check(out / "source.json"), source)

    # ---- 1. probe ----------------------------------------------------------------------------------
    info = PR.probe(src)
    pts = PR.frame_timestamps(src)
    timing = PR.analyze_timing(pts, info["video"]["r_fps"], cfg["probe"])
    fps = PR.choose_analysis_fps(info, timing)
    v = info["video"]
    log(f"probe: {v['codec']} {v['display_width']}x{v['display_height']}, {fps:g} fps "
        f"({'VFR' if timing['vfr'] else 'CFR'}: {timing['reason']}), {info['duration_s'] or 0:.2f}s")
    analysis_video, info_a, proxy_fill = src, info, None
    if timing["vfr"]:
        proxy = guard.check(out / "proxy_cfr.mp4")
        if args.force or not proxy.exists():
            PR.make_cfr_proxy(src, proxy, fps, info, cfg["probe"])
        analysis_video = proxy
        info_a = PR.probe(proxy)
        n_est = int(round((info["duration_s"] or len(pts) / fps) * fps)) + 2
        proxy_fill = PR.proxy_fill_map(pts, fps, n_est)
    est_frames = info_a["video"]["nb_frames"] or int(round((info_a["duration_s"] or 0) * fps)) or None

    # ---- 2. per-frame signal pass (cached) -------------------------------------------------------------
    cache = out / "cache"
    meta_p = cache / "meta.json"
    sig = {"sha256": sha_before, "analysis_cfg": cfg["analysis"], "fps": fps, "video": str(analysis_video)}
    cached = meta_p.exists() and (cache / "metrics.npz").exists() and (cache / "thumbs.u8").exists()
    if cached and not args.force:
        meta = read_json(meta_p)
        if meta.get("sig") != sig and not args.redetect:
            cached = False
    if cached and not args.force:
        log("signal pass: using cached per-frame metrics")
        meta = read_json(meta_p)
        metrics = SG.load_metrics(out)
    else:
        metrics, meta = SG.run_signal_pass(analysis_video, info_a, cfg, out, fps, est_frames, proxy_fill)
        meta["sig"] = sig
        write_json(guard.check(meta_p), meta)
    N = meta["n_frames"]
    thumbs = SG.load_thumbs(out, meta)

    # ---- 3. audio ------------------------------------------------------------------------------------------
    audio = None
    if info_a.get("audio"):
        wav = guard.check(out / "audio.wav")
        if args.force or not wav.exists():
            ok = AU.extract_wav(analysis_video, wav, cfg["audio"]["sample_rate"])
        else:
            ok = True
        if ok:
            off = (info_a["audio"].get("start_time") or 0.0) - (info_a["video"].get("start_time") or 0.0)
            audio = AU.analyze(wav, fps, N, off, cfg["audio"])
            if audio.get("available"):
                pf = audio["per_frame"]
                metrics["audio_rms_db"] = np.asarray(pf["rms_db"], float)
                metrics["audio_onset"] = np.asarray(pf["onset"], float)
                metrics["beat"] = np.asarray(pf["beat"], float)
                metrics["downbeat"] = np.asarray(pf["downbeat"], float)
    else:
        log("no audio stream: skipping beats / drops")
        wav = None
    SG.save_metrics(metrics, out, fps, drop_tc)
    log("metrics.csv written")

    # ---- 4. events -----------------------------------------------------------------------------------------
    ctx = DT.Ctx(metrics, thumbs, fps, cfg, drop_tc)
    events, plain, shots = DT.run_detection(ctx)
    for ev in events:
        ev["auto"] = DE.draft(ev, metrics, audio, fps, cfg, drop_tc)
    log(f"detection: {len(plain)} plain cuts, {len(events)} events, {len(shots)} shots")
    near = DT.near_misses(ctx, events, [c["frame"] for c in plain])
    log(f"possible misses to check: {len(near)}")

    # ---- 5. frames, contact sheets, previews ---------------------------------------------------------------
    plans = ME.plan(events, N, fps, cfg)
    beat_frames = {int(round(b["frame"])) for b in (audio or {}).get("beats", [])} if audio and audio.get("available") else set()
    down_frames = {int(round(b["frame"])) for b in (audio or {}).get("beats", []) if b["downbeat"]} if beat_frames else set()
    drop_frames = {int(round(d["frame"])) for d in (audio or {}).get("drops", [])} if beat_frames else set()
    marks = {"beat": beat_frames, "downbeat": down_frames, "drop": drop_frames,
             "cuts": {c["frame"] for c in plain}}
    cut_thumb_map = {}
    if not args.no_media:
        for sub in ("events", "frames", "cuts"):
            d = guard.check(out / sub)
            if d.exists():
                shutil.rmtree(d)
        aoff = audio["offset_s"] if audio and audio.get("available") else 0.0
        ME.extract_and_render(analysis_video, info_a, events, plans, out, fps, wav if audio else None, aoff,
                              marks, cfg, drop_tc, guard,
                              extra_frames={n["frame"] + d for n in near for d in (-1, 0, 1)})
        aspect = info_a["video"]["display_aspect"]
        for ev in events:
            pl = plans[ev["id"]]
            ev["sheets"] = ME.build_sheets(ev, pl, out, fps, drop_tc, aspect, marks, cfg, guard)
            ev["preview"] = f"events/{ev['id']}/preview.mp4"
            ev["preview_range"] = pl["preview"]
            ev["sheet_frames"] = pl["sheet_frames"]
            ev["sheet_sampled"] = pl["sampled"]
        cut_thumb_map = ME.cut_thumbs(thumbs, [c["frame"] for c in plain], out, guard)
        log(f"contact sheets and previews written for {len(events)} events")

    # ---- 6. overview ---------------------------------------------------------------------------------------
    OV.render(metrics, audio, events, plain, fps, guard.check(out / "overview.png"), "light")
    OV.render(metrics, audio, events, plain, fps, guard.check(out / "overview_dark.png"), "dark")
    log("overview.png written")

    # ---- 7. events.json + report.html ----------------------------------------------------------------------
    analysis_id = f"{name}-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    vmeta = {"n_frames": N, "vfr": timing["vfr"], "timing": timing,
             "analysis_video": "source" if analysis_video == src else analysis_video.name}
    review_p = out / "review.json"
    if review_p.exists():
        unmatched = AS.merge_review(events, read_json(review_p))
        if unmatched:
            log(f"review.json entries that no longer match an event: {unmatched}")
    source["unchanged"] = None
    data = AS.build(name, analysis_id, source, info_a, vmeta, audio, events, plain, shots, cfg, fps, drop_tc,
                    cut_thumb_map)
    # category + tags live in meta.json (the app edits them; re-runs keep them); the download link is added too
    m = read_json(out / "meta.json") if (out / "meta.json").exists() else {}
    old = read_json(out / "events.json") if (out / "events.json").exists() else {}
    changes = {"category": args.category or m.get("category") or (old or {}).get("category")
               or (old or {}).get("style") or CATEGORY_DEFAULT}
    if args.tags is not None:
        changes["tags"] = clean_tags(args.tags)
    dl = KN.download_info(src.name)
    for k in ("url", "platform", "uploader", "title"):
        if dl.get(k) and not m.get(k):
            changes[k] = dl[k]
    m = KN.save_meta(name, **changes) if (out / "events.json").exists() else {**m, **changes}
    data["category"] = data["style"] = m.get("category") or CATEGORY_DEFAULT
    data["tags"] = clean_tags(m.get("tags") or [])
    log(f"category: {data['category']} ({category_label(data['category'])})"
        + (f", tags: {', '.join(data['tags'])}" if data["tags"] else ""))
    data["near_misses"] = [{**n, "frames": [f"frames/f{f:06d}.jpg" for f in (n["frame"] - 1, n["frame"], n["frame"] + 1)
                                            if not args.no_media]} for n in near]
    AS.attach_miss_checks(data, read_json(review_p) if review_p.exists() else {})

    # ---- 8. verify the source was not touched ---------------------------------------------------------------
    sha_after = sha256_file(src)
    data["source"]["unchanged"] = bool(sha_after == sha_before and guard.verify_unchanged())
    AS.write_all(out, data)
    if not (out / "meta.json").exists():
        KN.save_meta(name, **{k: v for k, v in m.items() if k in ("category", "tags", "url", "platform", "uploader",
                                                                   "title")})
    KN.build_local_cards([name])                     # the shareable reference card (knowledge\local\references)
    if not data["source"]["unchanged"]:
        log("WARNING: the source file changed during analysis!")
    else:
        log("source video verified unchanged (SHA-256 identical before and after)")
    log(f"done: {out / 'report.html'}")
    print(f"\nREPORT: {out / 'report.html'}\nEVENTS: {len(events)}  PLAIN CUTS: {len(plain)}  "
          f"SHOTS: {len(shots)}  BPM: {audio['bpm'] if audio and audio.get('available') else 'n/a'}")
    print(f"NEXT: review every contact sheet listed in {out / 'review_todo.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
