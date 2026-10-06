"""Generate the synthetic self-test video with known effects at known frames (ffmpeg only).

    .venv\\Scripts\\python tools\\make_testvideo.py            -> tools\\selftest\\synthetic_test.mp4 + _truth.json

30 fps, 1280x720, 900 frames, 120 BPM click track (beat every 15 frames, accent every 4 beats),
noise build 12-16 s, drop at 16 s (frame 480). Effects: hard cuts (one off-beat), crossfade,
dip to black, white flash on a cut, freeze frame, zoom-in transition, stutter, wipe, RGB split.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from motionlab.util import run, tool, setup_console  # noqa: E402

HERE = Path(__file__).resolve().parent / "selftest"
PLATES = HERE / "plates"
FPS, W, H = 30, 1280, 720
CROP_W, CROP_H = 1920, 1080          # pan window inside the 2560x1440 plates

PLATE_CMDS = {
    "p1_mandel.png": ["-f", "lavfi", "-i", "mandelbrot=s=2560x1440:start_scale=0.012:end_scale=0.012:"
                      "start_x=-0.7436447860:start_y=0.1318252536:maxiter=600:inner=mincol:"
                      "outer=normalized_iteration_count", "-frames:v", "1"],
    "p2_mandel.png": ["-f", "lavfi", "-i", "mandelbrot=s=2560x1440:start_scale=0.25:end_scale=0.25:"
                      "start_x=-0.16:start_y=1.04:maxiter=300:inner=period:outer=iteration_count",
                      "-frames:v", "1"],
    "p3_cells.png": ["-f", "lavfi", "-i", "cellauto=s=2560x1440:rule=110:random_fill_ratio=0.5:"
                     "random_seed=7:full=1:scroll=0", "-frames:v", "1", "-vf",
                     "format=rgb24,lutrgb=r='val*0.15+20':g='val*0.55+40':b='val*0.75+60'"],
    "p4_sierp.png": ["-f", "lavfi", "-i", "sierpinski=s=2560x1440:type=carpet:seed=3:jump=1",
                     "-frames:v", "1", "-vf",
                     "format=rgb24,lutrgb=r='val*0.9+25':g='val*0.45+10':b='val*0.1+20'"],
    "p5_spectrum.png": ["-f", "lavfi", "-i", "colorspectrum=s=2560x1440:type=all", "-frames:v", "1",
                        "-vf", "format=rgb24,drawgrid=w=97:h=61:t=3:c=black@0.7,"
                               "drawgrid=w=31:h=23:t=1:c=white@0.4"],
    "p6_life.png": ["-f", "lavfi", "-i", "life=s=640x360:mold=25:ratio=0.12:seed=11:life_color=#ffd400:"
                    "death_color=#7a1fa2:mold_color=#1a0a40", "-frames:v", "1", "-vf",
                    "trim=start_frame=40:end_frame=41,scale=2560:1440:flags=neighbor"],
    "p8_grad.png": ["-f", "lavfi", "-i", "gradients=s=2560x1440:n=6:seed=5:speed=0:c0=0x0b3d91:"
                    "c1=0xf06292:c2=0x00c853:c3=0xffeb3b:c4=0x263238:c5=0xff6d00",
                    "-frames:v", "1", "-vf",
                    "format=rgb24,noise=alls=22:allf=u,drawgrid=w=160:h=90:t=2:c=white@0.25"],
}

# shot sources: plates are panned (simulated camera move), testsrc2 is animated in place
SHOTS = {
    "S1": {"plate": "p1_mandel.png", "x0": 120, "y0": 60, "vx": 3.0, "vy": 1.0},
    "S2": {"lavfi": "testsrc2=s=1280x720:r=30"},
    "S3": {"plate": "p3_cells.png", "x0": 300, "y0": 200, "vx": -2.5, "vy": 0.8},
    "S4": {"plate": "p4_sierp.png", "x0": 50, "y0": 100, "vx": 2.0, "vy": 1.5},
    "S5": {"plate": "p5_spectrum.png", "x0": 600, "y0": 50, "vx": -3.0, "vy": 1.0},
    "S6": {"plate": "p8_grad.png", "x0": 100, "y0": 150, "vx": 3.0, "vy": -0.6},
    "S7": {"plate": "p6_life.png", "x0": 200, "y0": 60, "vx": 2.0, "vy": 2.0},
    "S8": {"plate": "p2_mandel.png", "x0": 400, "y0": 200, "vx": -2.0, "vy": -1.0},
    "S9": {"lavfi": "testsrc2=s=1280x720:r=30,hue=h=150:s=1.3"},
}

ZOOM_IN_TAIL = [1.04, 1.12, 1.25, 1.42, 1.65, 2.0]       # ease-in (accelerating)
ZOOM_OUT_HEAD = [2.0, 1.65, 1.42, 1.25, 1.12, 1.04]      # ease-out (settling)

# (segment name, shot, output frames, effects) and joins between consecutive segments
TIMELINE = [
    ("A", "S1", 90, []),
    ("cut",),
    ("B", "S2", 105, [("rgb_split", 30, 8, 12)]),
    ("xfade", "fade", 15),
    ("C", "S3", 67, []),
    ("cut",),
    ("D", "S4", 133, []),
    ("xfade", "fadeblack", 20),
    ("E", "S5", 120, []),
    ("cut",),
    ("F", "S6", 90, [("flash_white", 3), ("freeze", 30, 19), ("zoom_tail", ZOOM_IN_TAIL)]),
    ("cut",),
    ("G", "S7", 105, [("stutter", 45, 4, 2), ("zoom_head", ZOOM_OUT_HEAD)]),
    ("xfade", "wipeleft", 15),
    ("H", "S8", 60, []),
    ("cut",),
    ("I", "S9", 180, []),
]

AUDIO_EXPR = (
    "0.5*("
    "0.45*sin(2*PI*1000*t)*exp(-60*mod(t,0.5))*lt(mod(t,0.5),0.04)"
    "+0.55*sin(2*PI*2000*t)*exp(-60*mod(t,2))*lt(mod(t,2),0.04)"
    "+gte(t,12)*lt(t,16)*0.35*pow((t-12)/4,2)*(2*random(0)-1)"
    "+gte(t,16)*(0.9*sin(2*PI*55*mod(t,0.5))*exp(-10*mod(t,0.5))+0.08*(2*random(1)-1))"
    ")"
)


def make_plates() -> None:
    PLATES.mkdir(parents=True, exist_ok=True)
    for name, args in PLATE_CMDS.items():
        if not (PLATES / name).exists():
            run([tool("ffmpeg"), "-y", "-v", "error", *args, str(PLATES / name)])


def zoom_expr(start: int, scales: list[float]) -> str:
    expr = "1"
    for i in reversed(range(len(scales))):
        expr = f"if(eq(in,{start + i}),{scales[i]},{expr})"
    return expr


def build_segment(name: str, shot: str, n_out: int, fx: list, workdir: Path) -> tuple[Path, dict]:
    """Render one segment losslessly. Returns path + local ground-truth notes."""
    s = SHOTS[shot]
    extra = sum((e[2] if e[0] == "freeze" else e[2] * e[3]) for e in fx if e[0] in ("freeze", "stutter"))
    n_src = n_out - extra
    if "plate" in s:
        inp = ["-loop", "1", "-framerate", str(FPS), "-i", str(PLATES / s["plate"])]
        base = (f"crop={CROP_W}:{CROP_H}:x='clip({s['x0']}+{s['vx']}*n,0,{2560 - CROP_W})':"
                f"y='clip({s['y0']}+{s['vy']}*n,0,{1440 - CROP_H})',scale={W}:{H}:flags=lanczos")
    else:
        inp = ["-f", "lavfi", "-i", s["lavfi"]]
        base = "null"
    chain = [base, "format=yuv444p", f"trim=start_frame=0:end_frame={n_src}", "setpts=N/(30*TB)"]
    notes = {}
    # NOTE: ffmpeg's loop filter repeats starting one frame BEFORE `start` (measured), hence +1.
    # The real positions are re-measured from the rendered segment below anyway.
    for e in fx:
        if e[0] == "freeze":
            chain += [f"loop=loop={e[2]}:size=1:start={e[1] + 1}", "setpts=N/(30*TB)"]
            notes["freeze"] = (e[1], e[1] + e[2])
        elif e[0] == "stutter":
            chain += [f"loop=loop={e[3]}:size={e[2]}:start={e[1] + 1}", "setpts=N/(30*TB)"]
            notes["stutter"] = (e[1], e[1] + e[2] * (e[3] + 1) - 1)
    for e in fx:
        if e[0] == "zoom_tail":
            st = n_out - len(e[1])
            chain += [f"zoompan=z='{zoom_expr(st, e[1])}':d=1:s={W}x{H}:fps={FPS}:"
                      f"x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2'",
                      f"gblur=sigma=2.5:enable='gte(n,{st})'"]
            notes["zoom_tail"] = (st, n_out - 1)
        elif e[0] == "zoom_head":
            chain += [f"zoompan=z='{zoom_expr(0, e[1])}':d=1:s={W}x{H}:fps={FPS}:"
                      f"x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2'",
                      f"gblur=sigma=2.5:enable='lt(n,{len(e[1])})'"]
            notes["zoom_head"] = (0, len(e[1]) - 1)
    for e in fx:
        if e[0] == "rgb_split":
            chain += [f"rgbashift=rh={-e[3]}:bh={e[3]}:enable='between(n,{e[1]},{e[1] + e[2] - 1})'",
                      "format=yuv444p"]
            notes["rgb_split"] = (e[1], e[1] + e[2] - 1)
        elif e[0] == "flash_white":
            chain += [f"fade=t=in:start_frame=0:nb_frames={e[1]}:color=white"]
            notes["flash_white"] = (0, e[1] - 1)
    out = workdir / f"seg_{name}.mkv"
    run([tool("ffmpeg"), "-y", "-v", "error", *inp, "-vf", ",".join(chain), "-frames:v", str(n_out),
         "-c:v", "ffv1", "-pix_fmt", "yuv444p", str(out)])
    # measure freeze / stutter positions in the rendered pixels (ground truth = what is really there)
    if any(e[0] in ("freeze", "stutter") for e in fx):
        fr = read_frames(out, 0, n_out - 1)
        for e in fx:
            if e[0] == "freeze":
                same = [t for t in range(1, n_out) if np.abs(fr[t] - fr[t - 1]).mean() < 0.01]
                notes["freeze"] = (min(same) - 1, max(same))
            elif e[0] == "stutter":
                k = e[2]
                rep = [t for t in range(k, n_out) if np.abs(fr[t] - fr[t - k]).mean() < 0.01
                       and np.abs(fr[t] - fr[t - 1]).mean() > 0.01]
                notes["stutter"] = (min(rep) - k, max(rep))
        for key in ("freeze", "stutter"):
            want = next((e for e in fx if e[0] == key), None)
            if want and notes[key][0] != want[1]:
                print(f"WARNING segment {name}: {key} measured at local {notes[key]}, intended start {want[1]}")
    return out, notes


def count_frames(p: Path) -> int:
    r = run([tool("ffprobe"), "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
             "stream=nb_read_frames", "-of", "csv=p=0", str(p)])
    return int(r.stdout.strip().split(",")[0])


def read_frames(p: Path, a: int, b: int) -> dict[int, np.ndarray]:
    cmd = [tool("ffmpeg"), "-v", "error", "-i", str(p), "-vf",
           f"select='between(n\\,{a}\\,{b})',scale=320:180:flags=area", "-fps_mode", "passthrough",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    n = len(raw) // (320 * 180 * 3)
    arr = np.frombuffer(raw[:n * 320 * 180 * 3], np.uint8).reshape(n, 180, 320, 3).astype(np.float32)
    return {a + i: arr[i] for i in range(n)}


XFADE_TYPES = {"fade": "crossfade", "fadeblack": "dip_black", "fadewhite": "dip_white", "wipeleft": "wipe",
               "circleopen": "mask_reveal", "slideleft": "push_slide"}


def join_timeline(entries: list, work: Path, tag: str):
    """entries: rendered segments {"name","path","n","notes":[(type,a,b,extra)]} and joins ("cut",) /
    ("xfade", transition, frames). Returns lossless path, frame count, cut frames, GT events."""
    segs, starts, gt_events, cuts = [], {}, [], []
    filt, cur, cur_len, k = [], None, 0, 0
    pending_join = None
    joins = []
    for item in entries:
        if isinstance(item, tuple):
            pending_join = item
            continue
        name, path, n_out = item["name"], item["path"], item["n"]
        got = count_frames(path)
        if got != n_out:
            raise SystemExit(f"segment {name}: expected {n_out} frames, got {got}")
        segs.append(path)
        filt.append(f"[{k}:v]settb=1/30,setpts=N,format=yuv444p[s{k}]")
        if cur is None:
            start = 0
            cur, cur_len = f"s{k}", n_out
        elif pending_join[0] == "cut":
            start = cur_len
            filt.append(f"[{cur}][s{k}]concat=n=2:v=1:a=0,settb=1/30,setpts=N[c{k}]")
            cuts.append(start)
            cur, cur_len = f"c{k}", cur_len + n_out
        else:
            _, trans, d = pending_join
            start = cur_len - d
            filt.append(f"[{cur}][s{k}]xfade=transition={trans}:duration={d / FPS:.6f}:"
                        f"offset={start / FPS:.6f},settb=1/30,setpts=N[c{k}]")
            joins.append((trans, start, d, segs[-2], starts[list(starts)[-1]], path, start))
            cur, cur_len = f"c{k}", cur_len + n_out - d
        starts[name] = start
        for typ, a, b, extra in item["notes"]:
            gt_events.append({"type": typ, "start": start + a, "end": start + b, **extra})
        k += 1

    lossless = work / f"joined_{tag}.mkv"
    run([tool("ffmpeg"), "-y", "-v", "error", *sum([["-i", str(p)] for p in segs], []),
         "-filter_complex", ";".join(filt), "-map", f"[{cur}]", "-c:v", "ffv1", "-pix_fmt", "yuv444p",
         str(lossless)])
    total = count_frames(lossless)
    if total != cur_len:
        raise SystemExit(f"joined video has {total} frames, expected {cur_len}")

    # measure the exact blended range of every xfade (first frame not pure A .. last not pure B)
    for trans, s, d, seg_a, start_a, seg_b, start_b in joins:
        F = read_frames(lossless, s - 2, s + d + 1)
        A = read_frames(seg_a, s - 2 - start_a, s + d + 1 - start_a)
        B = read_frames(seg_b, 0, d + 1)
        blended = []
        for t in range(s - 2, s + d + 2):
            fa = A.get(t - start_a)
            fb = B.get(t - start_b)
            # "affected" = a visible share of pixels differs from BOTH pure A and pure B (a small growing
            # iris or wipe strip counts from its first visible frame; a faint dissolve counts too)
            da = (np.abs(F[t] - fa).max(axis=2) > 6).mean() if fa is not None else 1.0
            db = (np.abs(F[t] - fb).max(axis=2) > 6).mean() if fb is not None else 1.0
            if da > 0.002 and db > 0.002:
                blended.append(t)
        gt_events.append({"type": XFADE_TYPES[trans], "start": min(blended), "end": max(blended),
                          "xfade_frames": [s, s + d - 1], "transition": trans})
    return lossless, total, cuts, gt_events


def encode_final(lossless: Path, total: int, out: Path) -> None:
    """Final delivery encode: H.264 + AAC click track (120 BPM, accent every 4 beats, build + drop at 16 s)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    run([tool("ffmpeg"), "-y", "-v", "error", "-i", str(lossless), "-f", "lavfi", "-i",
         f"aevalsrc=exprs='{AUDIO_EXPR}':s=48000:d={total / FPS}", "-map", "0:v", "-map", "1:a",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-g", "60",
         "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)])


def build_vfr(out: Path) -> dict:
    """Variable-frame-rate copy of the main test: every timestamp jittered by up to 1/4 frame (deterministic),
    so a correct CFR proxy keeps every frame in its slot and the main ground truth still applies."""
    src = HERE / "synthetic_test.mp4"
    if not src.exists():
        raise SystemExit("build the main test first (make_testvideo.py)")
    run([tool("ffmpeg"), "-y", "-v", "error", "-i", str(src), "-vf",
         "settb=1/90000,setpts='(N+0.25*sin(N*1.7))/30/TB'", "-fps_mode", "passthrough",
         "-enc_time_base", "1/90000", "-video_track_timescale", "90000", "-c:v", "libx264", "-crf", "16",
         "-preset", "fast", "-c:a", "copy", str(out)])
    truth = json.loads((HERE / "synthetic_test_truth.json").read_text(encoding="utf-8"))
    truth["video"] = out.name
    truth["notes"] = "VFR copy of synthetic_test (timestamps jittered +-1/4 frame); same frame-level truth"
    return truth


def build_negative(out: Path, work: Path) -> dict:
    import make_testvideo_ext as X
    import make_testvideo_neg as NEG
    entries = []
    for item in NEG.segments(PLATES):
        if isinstance(item, tuple):
            entries.append(item)
            continue
        path, notes = X.render_segment(item, work, read_frames)
        entries.append({"name": item["name"], "path": path, "n": item["n"], "notes": notes})
    lossless, total, cuts, _ = join_timeline(entries, work, "negative")
    encode_final(lossless, total, out)
    return {"video": out.name, "fps": FPS, "frames": total, "width": W, "height": H,
            "bpm": 120.0, "beat_period_frames": 15, "first_beat_frame": 0, "beats_per_bar": 4,
            "hard_cuts": cuts, "events": [],
            "notes": "negative test: handheld wobble, lens zoom, roll, lighting drift, grain - expect cuts only"}


def build_extended(out: Path, work: Path) -> dict:
    import make_testvideo_ext as X
    entries = []
    for item in X.segments(PLATES):
        if isinstance(item, tuple):
            entries.append(item)
            continue
        path, notes = X.render_segment(item, work, read_frames)
        entries.append({"name": item["name"], "path": path, "n": item["n"], "notes": notes})
    lossless, total, cuts, gt = join_timeline(entries, work, "extended")
    # whip transition = accelerating tail of X13 + cut + decelerating head of X14
    w_out = next(e for e in gt if e["type"] == "whip_out")
    w_in = next(e for e in gt if e["type"] == "whip_in")
    gt = [e for e in gt if e["type"] not in ("whip_out", "whip_in")]
    gt.append({"type": "whip_pan", "start": w_out["start"], "end": w_in["end"], "cut": w_in["start"]})
    plain = [c for c in cuts if c != w_in["start"]]
    gt.sort(key=lambda e: e["start"])
    encode_final(lossless, total, out)
    return {"video": out.name, "fps": FPS, "frames": total, "width": W, "height": H,
            "bpm": 120.0, "beat_period_frames": 15, "first_beat_frame": 0, "beats_per_bar": 4,
            "hard_cuts": plain, "events": gt,
            "notes": "extended effect set; frames 0-based, ranges inclusive; 'tol' = allowed boundary error"}


def main() -> None:
    setup_console()
    ap = argparse.ArgumentParser()
    ap.add_argument("--extended", action="store_true", help="build the extended effect-set video instead")
    ap.add_argument("--negative", action="store_true", help="build the no-effects (false positive) video instead")
    ap.add_argument("--vfr", action="store_true", help="build a variable-frame-rate copy of the main test")
    ap.add_argument("--out")
    args = ap.parse_args()
    work = HERE / "build"
    work.mkdir(parents=True, exist_ok=True)
    make_plates()
    if args.extended or args.negative or args.vfr:
        name = "synthetic_extended" if args.extended else ("synthetic_negative" if args.negative else "synthetic_vfr")
        out = Path(args.out or HERE / f"{name}.mp4")
        truth = (build_extended(out, work) if args.extended else
                 build_negative(out, work) if args.negative else build_vfr(out))
        tp = out.with_name(out.stem + "_truth.json")
        tp.write_text(json.dumps(truth, indent=2), encoding="utf-8")
        print(json.dumps(truth, indent=2))
        print(f"\nwrote {out} ({truth['frames']} frames) and {tp.name}")
        return
    out = Path(args.out or HERE / "synthetic_test.mp4")

    entries = []
    for item in TIMELINE:
        if item[0] in ("cut", "xfade"):
            entries.append(item)
            continue
        name, shot, n_out, fx = item
        path, notes = build_segment(name, shot, n_out, fx, work)
        entries.append({"name": name, "path": path, "n": n_out,
                        "notes": [(k, a, b, {}) for k, (a, b) in notes.items()]})
    lossless, total, cuts, gt_events = join_timeline(entries, work, "main")

    # zoom transition = tail zoom of F + cut + head zoom of G
    tail = next(e for e in gt_events if e["type"] == "zoom_tail")
    head = next(e for e in gt_events if e["type"] == "zoom_head")
    gt_events = [e for e in gt_events if e["type"] not in ("zoom_tail", "zoom_head")]
    gt_events.append({"type": "zoom_transition", "start": tail["start"], "end": head["end"],
                      "cut": head["start"], "direction": "in"})
    flash = next(e for e in gt_events if e["type"] == "flash_white")
    flash["cut"] = flash["start"]
    plain_cuts = [c for c in cuts if c not in (flash["start"], head["start"])]
    gt_events.sort(key=lambda e: e["start"])
    encode_final(lossless, total, out)

    truth = {
        "video": out.name, "fps": FPS, "frames": total, "width": W, "height": H,
        "bpm": 120.0, "beat_period_frames": 15, "first_beat_frame": 0, "beats_per_bar": 4,
        "drop_frame": 480, "build": {"start_frame": 360, "end_frame": 480},
        "hard_cuts": plain_cuts,
        "events": gt_events,
        "notes": "frames are 0-based; ranges inclusive. Transition ranges = frames that visibly mix A and B.",
    }
    tp = out.with_name(out.stem + "_truth.json")
    tp.write_text(json.dumps(truth, indent=2), encoding="utf-8")
    print(json.dumps(truth, indent=2))
    print(f"\nwrote {out} ({total} frames) and {tp.name}")


if __name__ == "__main__":
    main()
