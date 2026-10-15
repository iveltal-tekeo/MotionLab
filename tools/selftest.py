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
First, without video: odd titles (emoji, "...") make folder names the app opens and downloads it finds (check_titles),
the quick draft's rules (check_draft), feel tests (check_feels), sound effects on known frames and levels (check_sfx),
the checks before the final render (check_precheck), ratings as rules and the two kinds of lessons
(check_lessons_ratings), carousels kept as one post and the scrubbed problem report (check_downloads_report), the
thumbnail check's rules (check_thumbnail), YouTube's chapter / hashtag rules and package.json (check_publish);
--extended also renders the starter graphic (check_template).
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
    # cinematic: no transcript (the test videos say nothing; a PC with speech to text would listen to click tracks)
    r = subprocess.run([PY, str(HERE / "analyze.py"), str(video), "--name", name, "--force", "--focus", "cinematic"])
    if r.returncode != 0:
        raise SystemExit("analysis failed")
    data = json.loads((ANALYSIS / name / "events.json").read_text(encoding="utf-8"))
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    res = score(truth, data)
    (ANALYSIS / name / "selftest_score.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print_score(name, res)
    return res


def check_titles() -> dict:
    """Odd titles, no video needed (two 0.3.2 bugs a friend reported): a folder name made from a title must open in the
    app (no "..": a title yt-dlp shortened with "..."), an old ".." folder is renamed everywhere the lab wrote its name,
    and a download whose title has an emoji is found (yt-dlp.exe dropped the emoji from the path it printed)."""
    import tempfile
    import download as DL
    from motionlab import util
    from motionlab.app import data as appdata
    passed = []

    def check(cond, what):
        print(("PASS  " if cond else "FAIL  ") + what)
        passed.append(bool(cond))

    def opens(name):
        try:
            return appdata.safe_name(name) == name
        except ValueError:
            return False

    sandwich = "#fyp #foryou #foryoupage #harleyquinn #birdsofprey #breakfast #sandwi... [6988538288978054401]"
    cooking = "Where cooking meets cinematography \U0001F3AC #filmmaking #cinema #cooking #pi... [7636117427524291861]"
    titles = [sandwich, cooking, "a....b", "\U0001F3AC\U0001F3AC", "..hidden", "a" * 79 + ".b",
              "Ünïcødé – test. "]
    names = [util.safe_name(t) for t in titles]
    check(all(opens(n) and ".." not in n and not n.endswith(".") for n in names)
          and not opens(util._safe_name_032(sandwich)),
          "titles: every folder name made from an odd title opens in the app (no '..', no dot at the end)")

    with tempfile.TemporaryDirectory() as tmp:
        ana, cards = Path(tmp) / "analysis", Path(tmp) / "cards"
        old, new = util._safe_name_032(sandwich), util.safe_name(sandwich)
        src = "C:\\MotionLab\\refs\\" + sandwich + ".mp4"
        (ana / old).mkdir(parents=True)
        cards.mkdir()
        (ana / old / "events.json").write_text(json.dumps({"name": old, "analysis_id": old + "-20261012-120000",
                                                           "source": {"path": src}}), encoding="utf-8")
        (ana / old / "report.html").write_text(f"<h1>{old}</h1><span>{old}-20261012-120000</span>", encoding="utf-8")
        (cards / "c.json").write_text(json.dumps({"analysis": old, "title": sandwich}), encoding="utf-8")
        moved = util.fix_dotted_names(ana, cards, log=lambda m: None)
        try:
            ev = json.loads((ana / new / "events.json").read_text(encoding="utf-8"))
            html = (ana / new / "report.html").read_text(encoding="utf-8")
            card = json.loads((cards / "c.json").read_text(encoding="utf-8"))
        except OSError:
            ev, html, card = {"source": {}}, old, {}
        check(moved == [(old, new)] and not (ana / old).exists() and ev.get("name") == new
              and ev.get("analysis_id") == new + "-20261012-120000" and ev["source"].get("path") == src
              and old not in html and html.count(new) == 2 and card == {"analysis": new, "title": sandwich},
              "titles: a 0.3.2 folder with '..' is renamed (events, report, card), the video's path is kept")

    cmd = DL.with_fields(["yt-dlp", "-P", "refs", "-o", "%(title)s [%(id)s].%(ext)s", "--", "https://x"])
    enc = cmd.index("--encoding") if "--encoding" in cmd else None
    utf8 = enc is not None and cmd[enc + 1] == "utf-8" and enc < cmd.index("--")
    # the saved-file line since 0.4.2.1: path | platform | id | duration | part | parts | uploader (DL.PRINT)
    info = DL.parse(DL.MARK + "C:\\refs\\a [1].mp4|TikTok|7636117427524291861|41.0|NA|NA|Name | with bar")
    check(utf8 and info["path"] == "C:\\refs\\a [1].mp4"
          and info["uploader"] == "Name | with bar" and info["duration"] == "41.0" and info["index"] == ""
          and DL.parse(DL.MARK + "p|NA|NA|NA|NA|NA|NA")["platform"] == "",
          "downloads: yt-dlp prints in UTF-8, the saved-file line parses (a '|' in the uploader too)")
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        real = folder / (cooking + ".mp4")
        for f in (real, folder / (cooking + ".mp4.part"), folder / "other [123].mp4"):
            f.write_bytes(b"x")
        printed = str(folder / (cooking.replace("\U0001F3AC", "") + ".mp4"))       # what 0.3.2 got from yt-dlp.exe
        got = DL.saved_file({"path": printed, "id": "7636117427524291861"}, folder)
        check(got == real and DL.saved_file({"path": str(real), "id": ""}, folder) == real
              and DL.saved_file({"path": printed, "id": "999"}, folder) is None,
              "downloads: an emoji lost from the printed path - the file is still found by its id")

    from motionlab.app import system
    f1080 = system.PRESETS["mp4_1080"][1]
    sort = f1080[f1080.index("-S") + 1] if "-S" in f1080 else ""
    check(sort.startswith("res:1080") and "height<=" not in " ".join(f1080) and "vcodec!=none" in system.VIDEO_F
          and system.VIDEO_F in system.PRESETS["mp4_best"][1],
          "downloads: 1080p = the short side (vertical TikToks / Reels / Shorts in full size), never sound only")
    errors = {  # yt-dlp 2026.08.19's own ERROR lines (2026-10-12) -> the hint's first words
        "ERROR: [soundcloud] 293: Requested format is not available. Use --list-formats": "this link has no video",
        "ERROR: [youtube] VLDJ_-wrwj8: Sign in to confirm you're not a bot. Use --cookies-from-browser or --cookies":
            "the site is blocking",
        "ERROR: [Instagram] C5Rq: Instagram sent an empty media response. ... --cookies ... yt-dlp -U":
            "the site wants you logged in",
        "ERROR: [vimeo] 76979871: The web client only works when logged-in. Use --cookies": "the site wants you",
        "ERROR: Unsupported URL: https://example.com/x": "yt-dlp does not know",
    }
    check(all(DL.hint(["[info] x", e]).startswith(h) for e, h in errors.items()) and DL.hint(["WARNING: login"]) == "",
          "downloads: yt-dlp's errors are explained in words (no video, blocked, login, unknown link)")
    return {"passed": all(passed)}


def check_draft() -> dict:
    """The quick draft's rules (0.4, tools\\draft_edit.py), no video needed: clip stats made up so the right answer is
    known - a blurry start and a cut inside clip A, a 120 BPM song (12.5 frames a beat at 25 fps) with a drop at f400
    (00:00:16:00) - and a talking clip whose spoken parts are known."""
    import numpy as np
    from motionlab import compose, draft as DR, style as ST
    passed = []

    def check(cond, what):
        print(("PASS  " if cond else "FAIL  ") + what)
        passed.append(bool(cond))

    rng = np.random.default_rng(7)

    def clip(cid, n, blur=(0, 0), spike=None, speech=None):
        sharp = 100 + rng.normal(0, 5, n)
        sharp[blur[0]:blur[1]] = 5
        motion = 3 + rng.normal(0, 0.3, n)
        if spike is not None:
            motion[spike] = 60
        return {"id": cid, "frames": n, "fps": 25.0, "speech": speech,
                "stats": {"sharp": sharp, "motion": motion, "luma": np.full(n, 50.0), "p95": np.full(n, 75.0)}}
    clips = [clip("A", 600, blur=(0, 100), spike=300), clip("B", 400), clip("C", 300)]
    beats = [12.5 * k for k in range(1, 60)]
    S = ST.presets(["beat_montage"])
    D = DR.make(S, clips, 25.0, 1080, 1920, 750, "music", beats, {int(b) for b in beats[::4]}, [400.0], seed=1)
    sh = D["shots"]
    cuts = [x["start"] for x in sh[1:]]
    contiguous = sh[0]["start"] == 0 and sh[-1]["end"] == 749 and all(a["end"] + 1 == b["start"] for a, b in zip(sh, sh[1:]))
    fits = all(x["in"] >= 0 and x["in"] + (x["end"] - x["start"]) < next(c["frames"] for c in clips if c["id"] == x["sid"])
               for x in sh)
    check(contiguous and fits and D["frames"] == 750,
          "draft: the shots cover the whole edit, one after another, each inside its clip")
    on_beat = sum(1 for c in cuts if min(abs(c - b) for b in beats) <= 1) / max(1, len(cuts))
    check(on_beat >= 0.9 and 400 in cuts and any(e["frame"] == 400 and e["type"] == "flash_white" for e in D["effects"])
          and sum(1 for c in cuts if c < 75) >= 2,
          f"draft: cuts on the beat ({on_beat:.0%}), a cut + flash on the drop f400 (00:00:16:00), the hook's cuts in 3 s")
    bad = [x for x in sh if x["sid"] == "A" and (min(x["in"] + x["end"] - x["start"], 99) - x["in"] > 0.2 * (
        x["end"] - x["start"] + 1) or x["in"] < 300 <= x["in"] + x["end"] - x["start"] and x["in"] != 300)]
    check(not bad, "draft: the blurry start of a clip and a cut inside it are not used")
    try:
        for L in D["layers"]:
            for k in ("zoom", "opacity", "dx", "dy"):
                if k in L:
                    compose.Curve(L[k])
            for a in L.get("anchor") or []:
                compose.Curve(a)
        curves_ok = True
    except Exception:                                          # noqa: BLE001 - reported as a FAIL
        curves_ok = False
    check(curves_ok and all(L["type"] in compose.LAYERS for L in D["layers"]),
          "draft: every layer and animated value is one the compositor reads")
    talk = [clip("T", 500, speech=[(0, 99), (130, 229), (260, 359)]), clip("R", 300)]
    T = DR.make(ST.presets(["talking"]), talk, 25.0, 1080, 1920, None, "talk", seed=1)
    check([(x["in"], x["end"] - x["start"] + 1) for x in T["shots"]] == [(0, 100), (130, 100), (260, 100)]
          and T["frames"] == 300 and T["sound"] == [("T", 0, 99), ("T", 130, 229), ("T", 260, 359)]
          and [L.get("zoom", 1.0) for L in T["layers"][:3]] == [1.0, 1.12, 1.0],
          "draft: talking - the spoken parts in order, pauses cut, the sound with them, a punch-in every other cut")
    W = ST.presets(["three_sec"], "fast paced, 2 s cuts, captions word by word")
    check(W["rhythm"]["median_shot_s"] == 2.0 and W.get("captions") and W["energy"] == "high",
          "draft: the user's words - '2 s cuts', 'fast paced', 'captions' - change the style")
    return {"passed": all(passed)}


def check_colour(analysed: bool) -> dict:
    """The colour and look (0.4, motionlab.colour): words from known numbers, a match LUT that brings footage nearer a
    warmer, lifted look, a .cube written and read back the same - and, when synthetic_test was analysed in this run
    (focus cinematic), that analyze.py wrote its colour.json with one entry per shot."""
    import tempfile
    import numpy as np
    from motionlab import colour as CO
    from motionlab.util import ANALYSIS
    passed = []

    def check(cond, what):
        print(("PASS  " if cond else "FAIL  ") + what)
        passed.append(bool(cond))

    w = CO.words({"warmth": 12, "tint": 0, "saturation": 12, "brightness": 22, "contrast": 85, "black": 12, "white": 95,
                  "shadows": [-3, -6], "highlights": [4, 12], "letterbox": "2.39:1"})
    check(w == ["warm", "teal & orange", "desaturated", "dark (low-key)", "high contrast", "lifted blacks",
                "letterbox 2.39:1"] and CO.words({"bw": True, "brightness": 50, "contrast": 60}) == ["black & white"],
          "colour: the look in words (warm, teal & orange, low-key, lifted blacks, letterbox; black & white)")
    rng = np.random.default_rng(3)
    foot = rng.integers(20, 236, (4000, 1, 3)).astype(np.uint8)
    lab = CO.to_lab(foot)
    lab[..., 0] = lab[..., 0] * 0.7 + 22                       # the reference: lifted, flatter and warmer
    lab[..., 2] += 14
    ref = CO.lab_stats((CO.from_lab(lab) * 255 + 0.5).astype(np.uint8))
    src = CO.lab_stats(foot)
    lut = CO.match_lut(src, ref, 33)
    after = CO.lab_stats(CO.apply_lut(foot, lut))
    b0, b1 = CO.closeness(src, ref), CO.closeness(after, ref)
    with tempfile.TemporaryDirectory() as tmp:
        back = CO.read_cube(CO.write_cube(Path(tmp) / "m.cube", lut, "test"))
    g = CO.grade({"black": 12, "white": 95, "brightness": 30, "saturation": 20, "warmth": 12, "tint": 0})
    check(b1 >= 90 and b1 > b0 + 10 and np.allclose(back, lut, atol=1e-5) and g["out_black"] > 0
          and g["saturation"] < 1 and g["tint"][0] > 1 > g["tint"][2],
          f"colour: a match LUT brings the footage nearer the look (closeness {b0:g} -> {b1:g}), .cube round trip, "
          "a starting grade")
    if analysed:
        cj = ANALYSIS / "synthetic_test" / "colour" / "colour.json"
        try:
            c = json.loads(cj.read_text(encoding="utf-8"))
            ev = json.loads((ANALYSIS / "synthetic_test" / "events.json").read_text(encoding="utf-8"))
            ok = len(c["shots"]) == len(ev.get("shots", [])) and c["summary"]["line"].startswith("look:")
        except (OSError, ValueError, KeyError):
            ok = False
        check(ok, "colour: analyze.py measured the look of synthetic_test (focus cinematic) - one entry per shot")
    return {"passed": all(passed)}


def check_sfx() -> dict:
    """Sound effects (0.5.0, tools\\sfx.py), no video: a synthetic song and cues at known frames - onsets, levels
    against the song, the ceiling, the same output twice, cues that follow a setting, a plan's effects as cues."""
    from motionlab import sfx as SFX
    print("\n=== sound effects ===")
    r = SFX.selfcheck()
    return {"passed": r["passed"], "seconds": r["seconds"]}


def check_usage() -> dict:
    """What it took (0.4.4), no real logs: Claude Code session logs in tools\\dev\\usage_samples -> rounds, minutes,
    tokens counted once per answer, what is counted for a video and what is not, a helper's tokens, the live line
    reading only new bytes."""
    from motionlab import usage as U
    print("\n=== what it took: Claude's time and tokens from its logs ===")
    return {"passed": U.selfcheck()["passed"]}


def check_thumbsets() -> dict:
    """Thumbnail sets (0.4.5), no network: synthetic pictures added to a temp set -> measured, text found / not
    found and where, the summary, the sheets, re-use, remove-item, the style read back."""
    from motionlab import thumbsets as TS
    print("\n=== thumbnail sets: pictures measured, sheets for Claude ===")
    return {"passed": TS.selfcheck()["passed"]}


def check_downloads_report() -> dict:
    """Downloads that keep working and Report a problem (0.4.2.1), no network: a fake carousel -> one post in a scratch
    downloads.json; the report's scrubbing and GitHub link (known answers, trimming); how yt-dlp was installed -> its
    update command."""
    import download as DL
    from motionlab.app import jobtools as JT
    print("\n=== downloads keep every file, Report a problem ===")
    bad = DL.selfcheck() + JT.selfcheck()
    for b in bad:
        print("FAIL  " + b)
    print(("PASS  " if not bad else "FAIL  ") + "a carousel -> one post; the report scrubbed, its link fits; install kinds")
    return {"passed": not bad}


def check_thumbnail() -> dict:
    """Thumbnails (0.4.3, motionlab.thumbnail), no video / HyperFrames / face model: every rule of the thumbnail check
    with a passing and a failing case of known answer, the platforms' crops."""
    from motionlab import thumbnail as TH
    print("\n=== the thumbnail check ===")
    r = TH.selfcheck(verbose=True)
    print(("PASS  " if r["passed"] else "FAIL  ") + f"thumbnail check: every rule's known answers ({r['seconds']} s)")
    return {"passed": r["passed"]}


def check_publish() -> dict:
    """The ready-to-post words (0.4.3, motionlab.publish), no video: YouTube's chapter / hashtag / title rules with
    known answers, chapter points from a synthetic plan and transcript, and the package.json merge that keeps
    thumbnail.py's keys - in a temp folder."""
    from motionlab import publish as PB
    print("\n=== publish: chapters, hashtags, package.json ===")
    r = PB.selfcheck()
    for line in r["lines"]:
        print(line)
    return {"passed": r["passed"]}


def check_feels() -> dict:
    """Feel tests when starting blind (0.4.2, motionlab.style): the default three feels, the words that pick one, and
    a raw hook that really is busy - no video."""
    from motionlab import style as ST
    print("\n=== feel tests ===")
    ok = (ST.pick_feels("") == ["slick", "raw", "cinematic"] and ST.pick_feels("slow moody")[0] == "cinematic"
          and ST.pick_feels("fast glitchy")[0] == "raw"
          and ST.feel_style("raw", hook=True)["effects"][0]["per_min"] >= 20)
    print(("PASS  " if ok else "FAIL  ") + "feels: slick / raw / cinematic by default, 'slow moody' -> cinematic, "
          "'fast glitchy' -> raw, a raw hook has >= 20 effects a minute")
    return {"passed": ok}


def check_precheck() -> dict:
    """Checks before the final render (0.4.2, motionlab.precheck), no video: synthetic frames with a known gap, a known
    speed, motion-blur copies vs a smear, a clean clip, and a sound report with one loud and one buried cue."""
    from motionlab import precheck as PC
    print("\n=== checks before the final render ===")
    r = PC.selfcheck()
    return {"passed": r["passed"], "seconds": r["seconds"]}


def check_lessons_ratings() -> dict:
    """Claude's memory (0.4.2): the user's ratings of every video as rules, and the two kinds of lessons (analysis L###,
    making videos M###) - in a temp folder, no video."""
    from motionlab import knowledge as KN
    print("\n=== ratings as rules, lessons on making videos ===")
    return {"passed": KN.selfcheck()["pass"]}


def check_template() -> dict:
    """The starter graphic (0.4.2, overlay.py new): a snapshot, a plain render and a motion-blur render agree where
    nothing moves (~45 s; needs Node.js + HyperFrames, else skipped)."""
    import overlay as OVL
    print("\n=== the starter graphic: snapshot = render ===")
    return {"passed": OVL.selfcheck_template()["pass"]}


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--extended", action="store_true")
    ap.add_argument("--only-extended", action="store_true")
    args = ap.parse_args()
    st = HERE / "selftest"
    results = {"titles": check_titles(), "draft": check_draft(), "feels": check_feels(), "sfx": check_sfx(),
               "precheck": check_precheck(), "memory": check_lessons_ratings(), "downloads": check_downloads_report(),
               "thumbnail": check_thumbnail(), "publish": check_publish(), "usage": check_usage(),
               "thumbsets": check_thumbsets()}
    if not args.only_extended:
        results["synthetic_test"] = run_one(st / "synthetic_test.mp4", st / "synthetic_test_truth.json",
                                            "synthetic_test", [PY, str(HERE / "make_testvideo.py")], args.rebuild)
    results["colour"] = check_colour(not args.only_extended)
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
        results["template"] = check_template()
    ok = all(r["passed"] for r in results.values())
    print("\nOVERALL:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
