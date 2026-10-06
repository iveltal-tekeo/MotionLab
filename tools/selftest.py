"""MotionLab self-test: run the full pipeline on synthetic videos with known effects and score it.

    .venv\\Scripts\\python tools\\selftest.py              main test (generates the video if missing)
    .venv\\Scripts\\python tools\\selftest.py --rebuild    regenerate the synthetic video first
    .venv\\Scripts\\python tools\\selftest.py --extended   also score the extended effect set

Scoring (automatic detector output only - blind to the ground truth):
  found       an event of a compatible type overlaps the ground-truth range
  frames      start and end within +-1 frame, cut frame exact
  type        the event's primary type is the expected type (or an accepted synonym)
  cuts        every plain hard cut found at the exact frame
  beats       BPM within 1 of truth; on-beat flags of events and cuts correct
  false pos.  detected events that match no ground-truth effect
PASS = every effect found with correct type and frames, every cut exact, BPM/beat checks pass, 0 false positives.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from motionlab.util import ANALYSIS, setup_console  # noqa: E402

PY = sys.executable
ACCEPT = {
    "flash_white": {"flash_white"},
    "crossfade": {"crossfade"},
    "dip_black": {"dip_black"},
    "dip_white": {"dip_white"},
    "wipe": {"wipe"},
    "zoom_transition": {"zoom_transition"},
    "freeze": {"freeze"},
    "stutter": {"stutter"},
    "rgb_split": {"rgb_split"},
    "glitch": {"glitch"},
    "whip_pan": {"whip_pan"},
    "spin": {"spin"},
    "shake": {"shake"},
    "blur": {"blur"},
    "invert": {"invert"},
    "sat_pop": {"sat_pop"},
    "flash_color": {"flash_color"},
    "mask_reveal": {"mask_reveal"},
    "mirror": {"mirror"},
    "split_screen": {"split_screen"},
    "text": {"text"},
    "light_leak": {"light_leak"},
    "speed_ramp": {"speed_ramp"},
    "zoom_in": {"zoom_in"},
    "zoom_out": {"zoom_out"},
    "strobe": {"strobe"},
    "frame_repeat": {"frame_repeat"},
    "push_slide": {"push_slide"},
}
TOL = 1


def overlap(a0, a1, b0, b1):
    return max(0, min(a1, b1) - max(a0, b0) + 1)


def score(truth: dict, data: dict, tol: int = TOL) -> dict:
    events = data["events"]
    used = set()
    rows = []
    for g in truth["events"]:
        ok_types = ACCEPT.get(g["type"], {g["type"]})
        cands = [e for e in events if overlap(e["start"], e["end"], g["start"], g["end"]) > 0]
        typed = [e for e in cands if e["type"] in ok_types or set(e["types"]) & ok_types]
        best = max(typed or cands, key=lambda e: overlap(e["start"], e["end"], g["start"], g["end"]), default=None)
        r = {"gt_type": g["type"], "gt": [g["start"], g["end"]], "found": best is not None}
        if best is not None:
            used.add(best["id"])
            comp = next((c for c in best["components"] if c["type"] in ok_types), None)
            s, e = (comp["start"], comp["end"]) if comp else (best["start"], best["end"])
            gt_tol = g.get("tol", tol)
            r.update(id=best["id"], det_type=best["type"], det=[s, e],
                     type_ok=best["type"] in ok_types,
                     frames_ok=abs(s - g["start"]) <= gt_tol and abs(e - g["end"]) <= gt_tol)
            if "cut" in g:
                cuts = best.get("cuts", [])
                r["cut_ok"] = g["cut"] in cuts
                r["det_cut"] = cuts
                r["frames_ok"] = r["frames_ok"] and r["cut_ok"]
            if "on_beat" in g:
                r["beat_ok"] = bool(best["auto"]["on_beat"]) == bool(g["on_beat"])
        rows.append(r)
    fp = [e for e in events if e["id"] not in used]
    det_cuts = [c["frame"] for c in data["hard_cuts"] if c["kind"] == "hard cut"]
    want_cuts = truth.get("hard_cuts", [])
    cut_rows = []
    for c in want_cuts:
        cut_rows.append({"frame": c, "found": c in det_cuts,
                         "near": min(det_cuts, key=lambda x: abs(x - c)) if det_cuts else None})
    extra_cuts = [c for c in det_cuts if c not in want_cuts]
    beat = {}
    aud = data.get("audio") or {}
    if "bpm" in truth:
        beat["bpm_true"] = truth["bpm"]
        beat["bpm_detected"] = aud.get("bpm")
        beat["bpm_ok"] = aud.get("bpm") is not None and abs(aud["bpm"] - truth["bpm"]) <= 1.0
        if aud.get("beats"):
            import numpy as np
            bf = np.array([b["frame"] for b in aud["beats"]])
            per = truth["beat_period_frames"]
            err = bf - np.round((bf - truth["first_beat_frame"]) / per) * per - truth["first_beat_frame"]
            beat["beat_err_mean_frames"] = round(float(np.mean(err)), 2)
            beat["beat_err_max_frames"] = round(float(np.max(np.abs(err[1:]))), 2) if len(err) > 1 else None
            beat["beats_within_1_frame"] = round(float(np.mean(np.abs(err[1:]) <= 1.0)), 3)
        if "drop_frame" in truth:
            drops = [d["frame"] for d in aud.get("drops", [])]
            beat["drop_true"] = truth["drop_frame"]
            beat["drop_detected"] = drops
            beat["drop_ok"] = any(abs(d - truth["drop_frame"]) <= 1 for d in drops)
        # cut on-beat flags: a cut is on beat when it sits within 1 frame of a beat (truth grid)
        per, f0 = truth["beat_period_frames"], truth["first_beat_frame"]
        # flags are only judged where the truth is unambiguous: within 0.5 frame of a beat (must be ON)
        # or 1.5+ frames away (must be OFF); exactly-one-frame-off cases depend on sub-frame beat error
        def truth_flag(f):
            d = abs(((f - f0 + per / 2) % per) - per / 2)
            return True if d <= 0.5 else (False if d >= 1.5 else None)
        flags_ok = []
        for c in data["hard_cuts"]:
            want = truth_flag(c["frame"])
            if want is not None:
                flags_ok.append(bool(c["on_beat"]) == want)
        beat["cut_beat_flags_ok"] = all(flags_ok) if flags_ok else True
        ev_flags = []
        for r in rows:
            if r.get("found"):
                ev = next(e for e in events if e["id"] == r["id"])
                wants = [truth_flag(x) for x in (ev["start"], ev["key"], ev["end"])]
                if any(w is True for w in wants):
                    ev_flags.append(bool(ev["auto"]["on_beat"]))
                elif all(w is False for w in wants):
                    ev_flags.append(not ev["auto"]["on_beat"])
        beat["event_beat_flags_ok"] = all(ev_flags) if ev_flags else True
    found = sum(r["found"] for r in rows)
    typed = sum(bool(r.get("type_ok")) for r in rows)
    framed = sum(bool(r.get("frames_ok")) for r in rows)
    passed = (found == len(rows) and typed == len(rows) and framed == len(rows)
              and all(c["found"] for c in cut_rows) and not extra_cuts and not fp
              and beat.get("bpm_ok", True) and beat.get("drop_ok", True)
              and beat.get("cut_beat_flags_ok", True) and beat.get("event_beat_flags_ok", True))
    return {"effects": rows, "cuts": cut_rows, "extra_cuts": extra_cuts,
            "false_positives": [{"id": e["id"], "type": e["type"], "frames": [e["start"], e["end"]]} for e in fp],
            "beat": beat, "summary": {"effects_total": len(rows), "found": found, "type_correct": typed,
                                      "frames_correct": framed, "cuts_total": len(cut_rows),
                                      "cuts_exact": sum(c["found"] for c in cut_rows),
                                      "false_positives": len(fp), "extra_cuts": len(extra_cuts)},
            "passed": bool(passed)}


def print_score(name: str, res: dict) -> None:
    s = res["summary"]
    print(f"\n=== SELF-TEST: {name} ===")
    print(f"{'effect':18s} {'truth frames':>14s}  {'detected':>14s}  {'type':6s} {'frames':6s} found-as")
    for r in res["effects"]:
        det = f"{r['det'][0]}-{r['det'][1]}" if r.get("det") else "-"
        extra = f" cut {r.get('det_cut')}" if "cut_ok" in r else ""
        print(f"{r['gt_type']:18s} {r['gt'][0]:>6d}-{r['gt'][1]:<7d}  {det:>14s}  "
              f"{'OK' if r.get('type_ok') else 'XX':6s} {'OK' if r.get('frames_ok') else 'XX':6s} "
              f"{r.get('id', 'MISSED')} {r.get('det_type', '')}{extra}")
    for c in res["cuts"]:
        print(f"{'hard_cut':18s} {c['frame']:>14d}  {(c['frame'] if c['found'] else c['near']) or '-':>14}  "
              f"{'OK':6s} {'OK' if c['found'] else 'XX':6s}")
    b = res["beat"]
    if b:
        print(f"tempo: {b.get('bpm_detected')} BPM (truth {b.get('bpm_true')})  beat error mean "
              f"{b.get('beat_err_mean_frames')} f, max {b.get('beat_err_max_frames')} f, "
              f"{100 * (b.get('beats_within_1_frame') or 0):.0f}% within 1 frame; drop {b.get('drop_detected')} "
              f"(truth {b.get('drop_true')}); on-beat flags cuts {b.get('cut_beat_flags_ok')} events "
              f"{b.get('event_beat_flags_ok')}")
    if res["false_positives"]:
        print("false positives:", res["false_positives"])
    if res["extra_cuts"]:
        print("extra cuts:", res["extra_cuts"])
    print(f"SCORE: effects found {s['found']}/{s['effects_total']}, right type {s['type_correct']}/{s['effects_total']}, "
          f"right frames {s['frames_correct']}/{s['effects_total']}, cuts exact {s['cuts_exact']}/{s['cuts_total']}, "
          f"false positives {s['false_positives']}  ->  {'PASS' if res['passed'] else 'FAIL'}")


def run_one(video: Path, truth_path: Path, name: str, gen_cmd: list[str], rebuild: bool) -> dict:
    if rebuild or not video.exists() or not truth_path.exists():
        print(f"generating {video.name} ...")
        subprocess.run(gen_cmd, check=True)
    r = subprocess.run([PY, str(HERE / "analyze.py"), str(video), "--name", name, "--force"])
    if r.returncode != 0:
        raise SystemExit("analysis failed")
    data = json.loads((ANALYSIS / name / "events.json").read_text(encoding="utf-8"))
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    res = score(truth, data)
    (ANALYSIS / name / "selftest_score.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print_score(name, res)
    return res


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--extended", action="store_true")
    ap.add_argument("--only-extended", action="store_true")
    args = ap.parse_args()
    st = HERE / "selftest"
    results = {}
    if not args.only_extended:
        results["synthetic_test"] = run_one(st / "synthetic_test.mp4", st / "synthetic_test_truth.json",
                                            "synthetic_test", [PY, str(HERE / "make_testvideo.py")], args.rebuild)
    if args.extended or args.only_extended:
        results["synthetic_extended"] = run_one(
            st / "synthetic_extended.mp4", st / "synthetic_extended_truth.json", "synthetic_extended",
            [PY, str(HERE / "make_testvideo.py"), "--extended"], args.rebuild)
        results["synthetic_negative"] = run_one(
            st / "synthetic_negative.mp4", st / "synthetic_negative_truth.json", "synthetic_negative",
            [PY, str(HERE / "make_testvideo.py"), "--negative"], args.rebuild)
        results["synthetic_vfr"] = run_one(
            st / "synthetic_vfr.mp4", st / "synthetic_vfr_truth.json", "synthetic_vfr",
            [PY, str(HERE / "make_testvideo.py"), "--vfr"], args.rebuild)
    ok = all(r["passed"] for r in results.values())
    print("\nOVERALL:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
