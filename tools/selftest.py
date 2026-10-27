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
the quick draft's rules (check_draft), feel tests (check_feels), sound effects on known frames and levels and the
finished sound's loudness (check_sfx), stumbles in a talking take (check_stumbles),
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
from motionlab.util import ANALYSIS, LAB, setup_console  # noqa: E402

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
    # 2026-10-27: B-roll lands on the word its catalogue line says, picture only, never a moment under 1.5 s
    tk = clip("T", 600, speech=[(0, 149), (170, 319), (340, 489)])
    tk["words"] = [(10, "Your"), (200, "guitars"), (380, "today")]
    r1, r2 = clip("R1", 300), clip("R2", 300)
    r1["cat"] = DR.catalogue_arrays({"frames": 300, "moments": [
        {"a": 0, "b": 149, "usable": [[0, 149]], "say": {"what": "a guitar on a stand"}},
        {"a": 150, "b": 179, "usable": [[150, 179]], "say": {"what": "a guitar close up"}},
        {"a": 180, "b": 299, "usable": [[180, 299]], "say": {"what": "a city street"}}]})
    B = DR.make(ST.presets(["talking"]), [tk, r1, r2], 25.0, 1080, 1920, None, "talk", seed=1)
    br = [L for L in B["layers"] if L["id"].startswith("broll_")]
    first = next((n for n in B["broll"] if n["frame"] == 186), None)
    check(first is not None and first["sid"] == "R1" and 0 <= first["in"] and first["in"] + first["end"] - 186 <= 149
          and 'on "guitar"' in first["why"] and all(not 150 <= L["in"] <= 179 for L in br if L["src"] == "R1")
          and all(67 <= L["start"] and L["end"] < 405 and 37 <= L["end"] - L["start"] + 1 <= 100 for L in br)
          and sum(L["end"] - L["start"] + 1 for L in br) <= 0.4 * B["frames"]
          and B["sound"] == [("T", 0, 149), ("T", 170, 319), ("T", 340, 489)],
          "draft: B-roll on the words - 'guitars' said at f180 (00:00:07:05) -> R1's guitar from f186 (00:00:07:11), "
          "not its 1.2 s close-up; 1.5-4 s inserts, the hook and the end on the face, at most 40 %, the voice unchanged")
    import tempfile
    import soundfile as sf
    import draft_edit as DE
    sr, t = 48000, np.arange(48000 * 6) / 48000
    noise = np.random.default_rng(3).normal(0, 0.1, t.size).astype(np.float32)
    talky = noise * ((t % 0.8) < 0.5) + noise * 0.003            # phrases of 0.5 s, 0.3 s pauses
    song = noise * (1 + 0.3 * np.sin(2 * np.pi * 2 * t)).astype(np.float32)    # loud all through
    pz = {}
    with tempfile.TemporaryDirectory() as tmp:
        for k_, y in (("talk", talky), ("song", song)):
            sf.write(str(Path(tmp) / f"{k_}.wav"), y, sr)
            inf = {}
            DE.speech(Path(tmp) / f"{k_}.wav", 25.0, 150, 0.0, inf)
            pz[k_] = inf.get("pauses", -1)
    check(pz["talk"] >= DE.TALK_PAUSES > pz["song"] >= 0,
          f"draft: a take has pauses ({pz['talk']:.0%} quiet), a song under B-roll hardly any ({pz['song']:.0%}) - "
          "music next to a real take is B-roll, not talking")
    from motionlab import sfx as SFX                          # 0.5.4: the draft's own sound effects (--sfx)
    P = {"fps": 25.0, "frames": D["frames"], "width": 1080, "height": 1920, "layers": D["layers"]}
    by = {amt: [q["f"] for q in SFX.plan_cues({**P, "sfx": {"amount": amt, "first": [400]}})]
          for amt in ("few", "some", "many", "none")}
    spaced = all(b - a >= 125 for a, b in zip(by["few"], by["few"][1:])) and all(
        b - a >= 50 for a, b in zip(by["some"], by["some"][1:]))
    only = {q["kind"] for q in SFX.plan_cues({**P, "sfx": {"amount": "many", "kinds": ["impact"]}})}
    PT = {"fps": 25.0, "frames": T["frames"], "width": 1080, "height": 1920, "layers": T["layers"]}
    pt = [(q["f"], q["kind"]) for q in SFX.plan_cues({**PT, "sfx": {"amount": "few"}})]
    own = [(q["f"], q["kind"]) for q in SFX.plan_cues({**PT, "cues": [{"f": 200, "kind": "pop"}]})]
    check(by["many"] == [q["f"] for q in SFX.plan_cues(P)] and len(by["few"]) < len(by["some"]) < len(by["many"])
          and spaced and 400 in by["few"] and not by["none"] and only == {"impact"} and pt == [(199, "whip")]
          and own == [(200, "pop")],
          f"draft: sound effects - many {len(by['many'])}, some {len(by['some'])} (2 s apart), few {len(by['few'])} "
          "(5 s apart, the drop's hit f400 (00:00:16:00) first), only the kinds asked; a talking draft's punch-out at "
          "f200 (00:00:08:00) = a whip peaking on the cut (its punch-in at f100 hides under B-roll: none), a cue placed "
          "there wins")
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
    against the song, the ceiling, the same output twice, cues that follow a setting, a plan's effects as cues; over
    a voice (0.6.0) very subtle on a word, levelled to the voice in a pause. The finished sound (0.6.0,
    motionlab\\loudness.py): EBU R128's test tone measured, a quiet talk with clicks mastered to the target with its
    true peak under the ceiling after AAC."""
    from motionlab import loudness as LD
    from motionlab import sfx as SFX
    print("\n=== sound effects ===")
    r = SFX.selfcheck()
    print("\n=== the finished sound: loudness and true peak ===")
    ld = LD.selfcheck()
    from motionlab import sfxgen as GEN                     # 0.6.0: sounds made with ElevenLabs (a test server)
    print("\n=== sounds made with ElevenLabs (a test server, no key) ===")
    g = GEN.selfcheck()
    for line in g["lines"]:
        print(line)
    from motionlab import music as MU                       # 0.6.0 step 10: the music library, a bed under a voice
    print("\n=== the music library (a scratch library) ===")
    import time
    t0 = time.time()
    mu = MU.selfcheck()
    return {"passed": r["passed"] and ld["passed"] and g["passed"] and mu["passed"],
            "seconds": round(r["seconds"] + ld["seconds"] + g["seconds"] + time.time() - t0, 2)}


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


def check_textsets() -> dict:
    """Sets of scripts & prompts (2026-10-18), no Claude: temp folders - splitting, measuring, and Claude's check saved
    only when every quote is in THAT text (pieces out of order, paraphrases, words of another text refused), every
    part a row or skipped, patterns counted by the tool (motionlab.textsets.selfcheck)."""
    from motionlab import textsets as TX
    print("\n=== text sets: scripts & prompts, Claude's quotes checked ===")
    return {"passed": TX.selfcheck()["passed"]}


def check_fonts() -> dict:
    """The font library (0.4.6), no render: the families read from the lab's fonts folder (licences, weights,
    variable ranges), a graphic gets only the fonts it uses, and every example / thumbnail design that has a font
    setting offers the whole library (fonts.py sync was run after a font was added)."""
    from motionlab import fonts as FL
    from motionlab import overlay_settings as OSX
    print("\n=== fonts: the library, a graphic's copies, the designs' lists ===")
    r = FL.selfcheck()
    want = [o["value"] for o in FL.options(FL.ROOT)]           # the shipped library (never the user's own fonts)
    stale = []
    for idx in sorted(list(FL.EXAMPLES.glob("*/index.html")) + list(FL.THUMB_TEMPLATES.glob("*/index.html"))
                      + list(FL.MOTION.glob("*/index.html"))):
        for d in OSX.declared(idx.parent):
            if FL.is_font_setting(d) and [o["value"] for o in d.get("options", [])] != want:
                stale.append(f"{idx.parent.name}:{d['id']}")
    print(("PASS  " if not stale else "FAIL  ") + "every shipped design offers the whole library"
          + (f" - run tools\\fonts.py sync: {', '.join(stale)}" if stale else ""))
    return {"passed": r["passed"] and not stale}


def check_logos() -> dict:
    """The logo library (2026-10-16), no render: an SVG cleaned (ids / classes renamed, scripts and outside links
    refused), a library imported from a made-up folder that stays untouched, find / parse, a graphic's logos.js with
    only the logos it names (motionlab.logos.selfcheck)."""
    from motionlab import logos as LG
    print("\n=== logos: the library, a graphic's logos.js ===")
    return {"passed": LG.selfcheck()["passed"]}


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


def check_brand() -> dict:
    """My Brand (0.6.0, motionlab.brand), no app: what a save keeps and refuses, save + load in a temp folder; Import
    from your website (motionlab.siteread) on made-up pages, no network."""
    from motionlab import agency as AG
    from motionlab import brand as BR
    from motionlab import siteread as SR
    from motionlab import social as SO
    print("\n=== my brand: brand.json checked on every save, Import from your website; the content calendar, your videos ===")
    from motionlab import moodboard as MB                  # (0.6.0 step 7: the mood board; 13: your stats files)
    from motionlab import stats as STS
    r, s, a, o, m, x = BR.selfcheck(), SR.selfcheck(), AG.selfcheck(), SO.selfcheck(), MB.selfcheck(), STS.selfcheck()
    for line in r["lines"] + s["lines"] + a["lines"] + o["lines"] + m["lines"] + x["lines"]:
        print(line)
    return {"passed": r["passed"] and s["passed"] and a["passed"] and o["passed"] and m["passed"] and x["passed"]}


def check_light_cache() -> dict:
    """Light + sparse frame caches (0.6.1 step 5, prep_footage.prep_light / fill / ensure, footage.SparseFrames): a
    test clip (ffmpeg testsrc, every frame different) read once small, then full frames filled for a range - each on
    exactly the light cache's frame (30 -> 30 fps), a 25 fps clip on a 30 fps grid too; a frame not filled = the light
    frame scaled up, counted; a plan's needed frames."""
    import tempfile
    import types
    import cv2
    import numpy as np
    import prep_footage as PF
    from motionlab import footage as FC
    from motionlab.util import tool
    print("\n=== light caches: every frame small, full frames only for what a plan shows ===")
    passed = []

    def check(cond, what):
        print(("PASS  " if cond else "FAIL  ") + what)
        passed.append(bool(cond))
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:     # (Windows: a memmap holds its file)
        td = Path(td)
        prj = types.SimpleNamespace(cache=td / "cache", check=lambda p: p)
        for rate, sid in ((30, "A"), (25, "B")):
            src = td / f"clip{rate}.mp4"
            subprocess.run([tool("ffmpeg"), "-v", "error", "-f", "lavfi", "-i", f"testsrc=size=320x240:rate={rate}:duration=4",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-g", "50", str(src)], check=True)
            ent = {"path": str(src), "fingerprint": f"t{rate}"}
            m = PF.prep_light(prj, sid, ent, 30.0, 320, 240)
            lm = json.loads(FC.light_paths(prj.cache, sid)[1].read_text(encoding="utf-8"))
            la = np.memmap(FC.light_paths(prj.cache, sid)[0], dtype=np.uint8, mode="r",
                           shape=(lm["frames"], lm["height"] * 3 // 2, lm["width"]))
            check(m["segments"] == [] and lm["frames"] == m["frames"] in (120, 121) and lm["width"] == 80,
                  f"{rate} fps clip: read once - {m['frames']} light frames at 80 px, nothing full yet")
            PF.fill(prj.cache, sid, [[40, 60]], log=lambda *x: None)
            mm, arr = FC.load(prj.cache, sid)
            off = 0
            for i in range(40, 61, 5):
                full = cv2.resize(FC.image(mm, arr, i), (lm["width"], lm["height"]), interpolation=cv2.INTER_AREA).astype(int)
                d = [np.abs(full - FC.decode(la[j], "i420").astype(int)).mean() for j in (i - 1, i, i + 1)]
                off += int(d[1] > min(d) + 0.5)
            check(off == 0 and arr.missing == 0, f"{rate} fps clip: full frames f40-f60 filled, each the light cache's own "
                                                  "frame (a seek lands on the same grid)")
            FC.image(mm, arr, 5)
            check(arr.missing == 1 and not arr.has(5) and arr.has(50), "a frame not filled = the light one scaled up, counted")
        plan = {"frames": 30, "layers": [{"type": "clip", "id": "s01", "src": "A", "start": 0, "end": 29, "in": 70},
                                         {"type": "clip", "id": "s02", "src": "B", "start": 10, "end": 19, "in": 5,
                                          "hold": True}],
                "sources": {"A": {"cache": str(FC.paths(prj.cache, "A", True)[0])},
                            "B": {"cache": str(FC.paths(prj.cache, "B", True)[0])}}}
        need = FC.needed(plan, handle=PF.HANDLE)
        check(need == {"A": [[55, 114]], "B": [[0, 20]]}, f"a plan's frames per source, with handles: {need}")
        PF.ensure(plan, log=lambda *x: None)
        mm, arr = FC.load(prj.cache, "A")
        check(all(arr.has(i) for i in range(55, 115)), "ensure() before a render fills what the plan shows")
        hdr = td / "hdr.mp4"                            # an HDR (PQ) clip like an iPhone's: tone-mapped, not flat
        subprocess.run([tool("ffmpeg"), "-v", "error", "-i", str(td / "clip30.mp4"), "-vf",
                        "zscale=tin=bt709:min=bt709:pin=bt709:t=smpte2084:m=bt2020nc:p=bt2020:r=tv:npl=203,"
                        "format=yuv420p10le", "-c:v", "libx264", "-pix_fmt", "yuv420p10le", "-color_primaries", "bt2020",
                        "-color_trc", "smpte2084", "-colorspace", "bt2020nc", str(hdr)], check=True)
        m = PF.prep_light(prj, "H", {"path": str(hdr), "fingerprint": "h"}, 30.0, 320, 240)
        lh = json.loads(FC.light_paths(prj.cache, "H")[1].read_text(encoding="utf-8"))
        lha = np.memmap(FC.light_paths(prj.cache, "H")[0], dtype=np.uint8, mode="r",
                        shape=(lh["frames"], lh["height"] * 3 // 2, lh["width"]))
        rgb = FC.decode(lha[30], "i420").astype(float)
        sat = float((rgb.max(axis=2) - rgb.min(axis=2)).mean())
        check(bool(m.get("tonemap")) and rgb.std() > 60 and sat > 120,
              f"an HDR (PQ) clip is tone-mapped to Rec.709, not flat (contrast {rgb.std():.0f}, colour {sat:.0f}; "
              "untone-mapped it was ~32 / ~59)")
        del lha
        del arr, mm, la
        import gc
        gc.collect()
    return {"passed": all(passed)}


def check_person() -> dict:
    """Graphics made part of the shot (0.6.1, motionlab.person + compose's behind / guard / follow / glass): the mask
    model runs through OpenCV; then, with a made-up person track (a known block of person, a known face) on a
    checkerboard room - a band "behind" is hidden on the person and shown beside it, "guard" hides a graphic on the
    face but not on the body, "glass" frosts the room under a faint card, a spotlight ("room" dim) darkens the room
    only, "track": "face" puts a 2x zoom on the face, the shot check flags a graphic over the face (not one beside it,
    not one that keeps off it), "follow": "camera" moves and grows a graphic with a 1.5x punch-in like the room does."""
    import tempfile
    import cv2
    import numpy as np
    from motionlab import compose as C, footage as FC, overlays as OV, person as P
    print("\n=== graphics made part of the shot: behind the person, off the face, glass, with the camera ===")
    passed = [P.selfcheck()]

    def check(cond, what):
        print(("PASS  " if cond else "FAIL  ") + what)
        passed.append(bool(cond))
    W, H, n = 320, 184, 6
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        td = Path(td)
        yy, xx = np.mgrid[0:H, 0:W]
        room = np.where(((xx // 8) + (yy // 8)) % 2 == 0, 70, 190).astype(np.uint8)
        rgb = np.repeat(room[..., None], 3, 2)
        with open(td / "S.color.yuv", "wb") as f:
            for _ in range(n):
                f.write(FC.encode(rgb).tobytes())
        lw, lh = W // 4, H // 4                             # the light cache (what a person track is made from)
        lp, lm = FC.light_paths(td, "S")
        with open(lp, "wb") as f:
            for _ in range(n):
                f.write(FC.encode(cv2.resize(rgb, (lw, lh), interpolation=cv2.INTER_AREA)).tobytes())
        lm.write_text(json.dumps({"id": "S", "frames": n, "width": lw, "height": lh, "fps": 30.0, "format": "i420"}),
                      encoding="utf-8")
        mask = np.zeros((lh, lw), np.uint8)
        mask[2:, 30:50] = 255                                # the person: output x 120..199, y 8..179
        du, dj = P.paths(td, "S")
        np.repeat(mask[None], n, 0).tofile(du)
        st = lp.stat()
        dj.write_text(json.dumps({"version": P.VERSION, "frames": n, "width": lw, "height": lh, "fps": 30.0,
                                  "light": [st.st_size, int(st.st_mtime)], "faces": [[0.5, 0.42, 0.12]] * n}),
                      encoding="utf-8")

        def overlay(name, paint):
            mov = td / f"{name}.mov"
            mov.write_bytes(b"test overlay")
            fr = np.zeros((H, W, 4), np.uint8)
            paint(fr)
            OV.build_cache(mov, lambda: (fr for _ in range(n)), W, H, 30.0, "test")
            return str(mov)
        band = overlay("band", lambda fr: fr.__setitem__((slice(20, 36), slice(0, W)), (255, 214, 10, 255)))
        dot = overlay("dot", lambda fr: fr.__setitem__((slice(70, 82), slice(150, 170)), (255, 0, 0, 255)))
        body = overlay("body", lambda fr: fr.__setitem__((slice(150, 162), slice(150, 170)), (0, 0, 255, 255)))
        card = overlay("card", lambda fr: fr.__setitem__((slice(110, 170), slice(10, 100)), (255, 255, 255, 40)))
        mark = overlay("mark", lambda fr: fr.__setitem__((slice(56, 64), slice(216, 224)), (0, 255, 0, 255)))

        def plan(extra: dict, zoom=1.0):
            ly = [{"type": "clip", "id": "c", "src": "S", "start": 0, "end": n - 1, "rect": [0, 0, W, H], "in": 0,
                   "zoom": zoom},
                  {"type": "overlay", "id": "band", "file": band, "start": 0, "end": n - 1, **extra.get("band", {})},
                  {"type": "overlay", "id": "dot", "file": dot, "start": 0, "end": n - 1, **extra.get("dot", {})},
                  {"type": "overlay", "id": "body", "file": body, "start": 0, "end": n - 1, **extra.get("dot", {})},
                  {"type": "overlay", "id": "card", "file": card, "start": 0, "end": n - 1, **extra.get("card", {})},
                  {"type": "overlay", "id": "mark", "file": mark, "start": 0, "end": n - 1, **extra.get("mark", {})}]
            return {"width": W, "height": H, "fps": 30.0, "frames": n, "background": 0.0, "levels": "single",
                    "sources": {"S": {"cache": str(td / "S.color.yuv"), "format": "i420", "frames": n, "width": W,
                                      "height": H}}, "grades": {}, "layers": ly}
        plain = C.Renderer(plan({})).render(0).astype(np.float32)
        R = C.Renderer(plan({"band": {"behind": True}, "dot": {"guard": True}, "card": {"glass": True}}))
        made = R.render(0).astype(np.float32)
        yellow = np.array([255, 214, 10], np.float32)
        bare = plan({})
        bare["layers"] = bare["layers"][:1]                  # the room alone, as the renderer draws it
        room = C.Renderer(bare).render(0).astype(np.float32)
        room_px = lambda y, x: room[y, x]
        check(np.abs(plain[28, 160] - yellow).max() < 3 and np.abs(made[28, 60] - yellow).max() < 3
              and np.abs(made[28, 160] - room_px(28, 160)).max() < 12,
              "person: a band behind the person - hidden on it, shown beside it (without the key: on top)")
        check(np.abs(made[76, 160] - room_px(76, 160)).max() < 12 and made[156, 160][2] > 200 and made[156, 160][0] < 60,
              "person: guard - a graphic on the face hidden, one on the body (well below the face) shown")
        card_box = (slice(115, 165), slice(15, 95))
        sharp = float(np.std(cv2.Laplacian(plain[card_box].mean(2), cv2.CV_32F)))
        frosted = float(np.std(cv2.Laplacian(made[card_box].mean(2), cv2.CV_32F)))
        check(frosted < sharp * 0.5,
              f"person: glass frosts the room under a faint card (its detail {sharp:.0f} -> {frosted:.0f})")
        rp = plan({})                                    # the room look (a spotlight) and the zoom point on the face
        rp["layers"] = rp["layers"][:1]
        rp["layers"][0]["room"] = {"look": "spotlight", "dim": 0.7}
        lit = C.Renderer(rp).render(0).astype(np.float32)
        tp = plan({}, zoom=2.0)
        tp["layers"] = tp["layers"][:1]
        f_plain = C.Renderer(tp).face_at(0)
        tp["layers"][0]["track"] = "face"
        f_track = C.Renderer(tp).face_at(0)
        check(abs(float(lit[28, 60].mean()) - 0.3 * float(room[28, 60].mean())) < 6
              and np.abs(lit[100, 160] - room[100, 160]).max() < 12
              and f_plain and f_track and abs(f_track[0] - 160) < 1 and abs(f_track[1] - 73.6) < 2
              and abs(f_plain[1] - 62.6) < 2 and abs(f_track[2] - 76.8) < 1,
              f"person: a spotlight dims the room to 30 % and leaves the person; a 2x zoom on the face puts it at "
              f"({f_track[0]:.0f}, {f_track[1]:.0f}) (the frame's middle: {f_plain[1]:.0f} without)" if f_track and f_plain
              else "person: the face under a zoom")
        flagged = [(g["id"], g["guard"]) for g in P.face_issues(plan({}), log=lambda *_: None)]
        guarded = [(g["id"], g["guard"]) for g in P.face_issues(plan({"dot": {"guard": True}}), log=lambda *_: None)]
        behind = P.face_issues(plan({"dot": {"behind": True}}), log=lambda *_: None)
        check(flagged == [("dot", False)] and guarded == [("dot", True)] and not behind,
              f"person: the shot check flags a graphic over the face (the dot), not one beside it; kept off the face, "
              f"the face cuts into it - flagged as that ({guarded}); behind the person - not flagged")
        cam = C.Renderer(plan({"mark": {"follow": "camera"}}, zoom={"keys": [[0, 1.0, "hold"], [5, 1.5, "hold"]]}))
        f0, f5 = cam.render(0).astype(np.float32), cam.render(5).astype(np.float32)
        g0, g5 = (f0[..., 1] > 200) & (f0[..., 0] < 60), (f5[..., 1] > 200) & (f5[..., 0] < 60)
        c0 = np.argwhere(g0).mean(0) if g0.any() else np.zeros(2)
        c5 = np.argwhere(g5).mean(0) if g5.any() else np.zeros(2)
        want = (H / 2 + (59.5 - H / 2) * 1.5, 160 + (219.5 - 160) * 1.5)    # the room point under it after a 1.5x punch-in
        grow = g5.sum() / max(1, g0.sum())
        check(abs(c0[0] - 59.5) < 1.5 and abs(c0[1] - 219.5) < 1.5 and abs(c5[0] - want[0]) < 2.5
              and abs(c5[1] - want[1]) < 2.5 and 1.8 < grow < 2.8,
              f"person: follow camera - a mark at (220, 60) moves to ({c5[1]:.0f}, {c5[0]:.0f}) in a 1.5x punch-in "
              f"(the room point: ({want[1]:.0f}, {want[0]:.0f})) and grows {grow:.2f}x in area (1.5 x 1.5 = 2.25)")
        del R, cam
        import gc
        gc.collect()
    return {"passed": all(passed)}


def check_catalogue() -> dict:
    """The clip catalogue (0.6.1 step 1, motionlab.catalogue): a made-up clip with known moments - five shots, the
    black one unusable, the colour bars twice one look-alike group, the filmed date, lines kept / refused."""
    from motionlab import catalogue as CT
    print("\n=== the clip catalogue: moments, usable parts, look-alikes, lines ===")
    r = CT.selfcheck()
    for line in r["lines"]:
        print(line)
    return {"passed": r["passed"]}


def check_miniedit() -> dict:
    """The Editor (0.6.0 step 6, motionlab.miniedit), no video: trims, deletes, a moved cut, moves, splits, speed, graphics, sound effect edits and
    words on a made-up plan - what moves with a shot, what is refused, a sound it cannot cut again locking the shots;
    its effects (edfx), keyframes (edkeys) and transitions (edtrans)."""
    from motionlab import edfx as FX
    from motionlab import edkeys as KF
    from motionlab import edtrans as TR
    from motionlab import miniedit as ME
    print("\n=== the Editor: a made video changed by hand ===")
    R = [ME.selfcheck(), FX.selfcheck(), KF.selfcheck(), TR.selfcheck()]    # (+ its effects, keyframes, transitions)
    for line in [x for r in R for x in r["lines"]]:
        print(line)
    return {"passed": all(r["passed"] for r in R)}


def check_facefit() -> dict:
    """Captions off the speaker's face (0.6.0 step 21, motionlab.facefit): where a shot's captions go - under the
    chin, under the mouth in a close-up, never up on the forehead, a face beside them ignored - and the platforms' safe
    zones they keep inside (motionlab.safezones, 2026-10-27) - no video."""
    from motionlab import facefit as FF
    from motionlab import safezones as SZ
    print("\n=== captions off the face, the platforms' safe zones ===")
    R = [FF.selfcheck(), SZ.selfcheck()]
    for line in [x for r in R for x in r["lines"]]:
        print(line)
    return {"passed": all(r["passed"] for r in R)}


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


def check_stumbles() -> dict:
    """Stumbles in a talking take (0.6.0, motionlab.stumbles), no video: made-up takes with times - fillers, a phrase
    twice, half a word, retakes, "cut / again" said to the edit, English and Spanish; emphasis, rhetoric and a question
    kept; a cut never reaches into a kept word."""
    from motionlab import stumbles as STM
    print("\n=== stumbles in a talking take ===")
    return {"passed": STM.selfcheck()["passed"]}


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


def check_motion(extended: bool) -> dict:
    """The Motion Graphics library (0.5.0): reading a pack of clips measures a synthetic clip right (its two moves,
    the hold, the files); every template is complete (index.html declaring its settings + the size lines overlay.py
    retime needs, overlay.json whose cues resolve inside its frames, template.json, its picture) and pick() finds
    templates for words. --extended: every template snapshotted at its picture's frame (HyperFrames, no render) - an
    empty frame fails (the hide + show trap of local-make-8)."""
    import re as _re
    import shutil as _sh
    import numpy as _np
    from motionlab import overlay_settings as OSX
    from motionlab import sfx as SFX
    from motionlab import template_read as TR
    from motionlab import templates as TP
    print("\n=== motion templates: a pack read, the library complete, picks ===")
    ok = all(TR.selfcheck(verbose=False).values())
    print(("PASS  " if ok else "FAIL  ") + "a synthetic clip read: 2 moves and the hold found within 2 frames, sheets written")
    lib, bad = TP.library(), []
    need = ("name", "kind", "what", "use_for", "thumb_f", "check_frames")     # + the clips it learned from, or its origin
    for t in lib:
        f = LAB / t["folder"]
        try:
            html = (f / "index.html").read_text(encoding="utf-8")
            miss = [k for k in need if not t.get(k)] + ([] if t.get("learned_from") or t.get("origin") else ["learned_from / origin"])
            sizes = [p for p in OSX._SIZE_LINES[:5] if not _re.search(p, html)]
            cues, fps, frames, _ = SFX.graphic_cues(f)
            out = [c["f"] for c in cues if not 0 <= c["f"] < frames]
            if miss or sizes or out or not OSX.declared(f) or not (f / "thumb.png").exists():
                bad.append(f"{t['id']}: {'missing ' + ', '.join(miss) if miss else ''}{' no size line ' + ', '.join(sizes) if sizes else ''}"
                           f"{' cues outside the frames ' + str(out) if out else ''}")
        except (OSError, ValueError, KeyError) as e:
            bad.append(f"{t['id']}: {e}")
    print(("PASS  " if lib and not bad else "FAIL  ") + f"{len(lib)} templates complete (settings, size lines, cues, card, picture)"
          + ("" if not bad else ": " + "; ".join(bad)))
    picks = TP.pick("a bold hook title, a number counting up, then a list of tips", 5)
    good_pick = len(picks) == min(5, len(lib)) and picks and picks[0]["score"] > 0
    print(("PASS  " if good_pick else "FAIL  ") + "pick() finds templates for words: " + ", ".join(p["id"] for p in picks))
    passed = ok and bool(lib) and not bad and bool(good_pick)
    if extended:
        import overlay as OVL
        if not OVL.HF.exists():
            print("SKIP  snapshots: HyperFrames is not installed")
        else:
            work = LAB / ".app" / "dev" / "selftest_motion"
            alone = work.with_name(work.name + "_alone")
            for w in (work, alone):
                _sh.rmtree(w, ignore_errors=True)
            import os as _os
            import time as _t
            from concurrent.futures import ThreadPoolExecutor
            t0 = _t.time()

            def snap(t: dict, w: Path = work) -> str | None:      # None = it draws, else what to report
                dst = w / t["id"]
                OVL.copy_sources(LAB / t["folder"], dst, t["id"])
                try:
                    arrs, _ = OVL.snapshots(dst, [int(t["thumb_f"])], w / f"{t['id']}_snap")
                    rgb = _np.asarray(OVL.on_checker(arrs[0]).convert("L"), _np.float32)
                    return t["id"] if rgb.std() < 4 else None
                except SystemExit as e:
                    return f"{t['id']} ({e})"
            # each template has its own copy, work folder and HyperFrames process (+ Chrome): up to 4 at a time
            # (~cpu / 3); one that comes out empty under that load counts only when it is empty on its own too
            with ThreadPoolExecutor(min(4, max(1, (_os.cpu_count() or 2) // 3))) as ex:
                got = list(ex.map(snap, lib))
            empty = []
            for t, r in zip(lib, got):
                r = r and snap(t, alone)
                if r:
                    empty.append(r)
            for w in (work, alone):
                _sh.rmtree(w, ignore_errors=True)
            print(("PASS  " if not empty else "FAIL  ") + f"every template draws something at its picture's frame "
                  f"({len(lib)} snapshots in {_t.time() - t0:.0f} s)" + (": empty " + ", ".join(empty) if empty else ""))
            passed = passed and not empty
    return {"passed": passed}


def check_template() -> dict:
    """The starter graphic (0.4.2, overlay.py new): a snapshot, a plain render and a motion-blur render agree where
    nothing moves (~45 s; needs Node.js + HyperFrames, else skipped)."""
    import overlay as OVL
    print("\n=== the starter graphic: snapshot = render ===")
    return {"passed": OVL.selfcheck_template()["pass"]}


def main() -> int:
    setup_console()
    import os
    os.environ["MOTIONLAB_NO_LOCAL_CONFIG"] = "1"     # the shipped thresholds, never this PC's config.local.json
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--extended", action="store_true")
    ap.add_argument("--only-extended", action="store_true")
    args = ap.parse_args()
    st = HERE / "selftest"
    results = {"titles": check_titles(), "draft": check_draft(), "feels": check_feels(), "sfx": check_sfx(),
               "stumbles": check_stumbles(),
               "precheck": check_precheck(), "memory": check_lessons_ratings(), "downloads": check_downloads_report(),
               "thumbnail": check_thumbnail(), "publish": check_publish(), "brand": check_brand(), "miniedit": check_miniedit(),
               "facefit": check_facefit(), "light_cache": check_light_cache(), "catalogue": check_catalogue(),
               "person": check_person(),
               "usage": check_usage(),
               "thumbsets": check_thumbsets(), "textsets": check_textsets(), "fonts": check_fonts(), "logos": check_logos(),
               "motion": check_motion(args.extended or args.only_extended)}
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
