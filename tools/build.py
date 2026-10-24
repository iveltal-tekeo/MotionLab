"""One build (0.5.3): everything a plan needs in one command and a 10-line summary - what took Claude 5-8 turns
(render each graphic, the sound, the composite, the precheck, a stills sheet) and the waits between them.

    .venv\\Scripts\\python tools\\build.py <project> [plan_vN.json] [--final] [--motion-blur 5] [--jobs N] [--sfx]
          [--force]
          1. every composition the plan shows (its overlay layers' build\\overlays\\<name>\\<name>.mov) rendered when
             it changed since its last render (index.html, settings, size, assets, motion blur - overlay_settings
             .inputs_hash): a version that changed one graphic's settings renders one graphic; --jobs N at a time
             (default by the CPU: 1-3); plain, or with --final motion blur (--motion-blur, default 5; a graphic
             that hardly moves keeps its plain render, captions are always rendered plain - nothing in them travels)
          2. the sound: with --sfx, a plan "sfx": true, or when the plan's audio is already a mix sfx.py made:
             sfx.py plan -> build\\sfx\\<name>_mix.wav becomes the plan's "audio" (made from the same song)
          3. the composite (render_video.py; skipped when nothing it reads changed and the video exists)
          4. precheck.py on it (+ the sound report): vanishing parts, fast moves without blur, buried / loud cues;
             and the plan's camera moves (2026-10-24, precheck.plan_moves): too many, or one between two shots of
             the same take
          5. plain builds: the cut-sheet (render_video.py --cuts): every cut and cue on one page - the one look
          -> the summary + build\\checks\\<name>_build.json. Exit 0 = built, nothing flagged; 2 = built, the
          precheck flags something to look at; 1 = a step failed (STOPPED); 3 = too long for Claude's shell (a job)
          The newest plan_vN.json when none is named. A build longer than ~9 minutes (a --final with motion blur,
          a long video) refuses to run in Claude's shell: start it as a job - tools\\job.py start build
          project=<project> [final=1] - and wait with tools\\job.py wait <id>.
Writes only into projects\\<project>\\build\\ (the tools it runs keep their own guards); sources are only read.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import overlay_settings as OS  # noqa: E402
from motionlab import sfx as SFX  # noqa: E402
from motionlab.timecode import frame_to_tc  # noqa: E402
from motionlab.util import LAB, setup_console  # noqa: E402

PY, TOOLS = sys.executable, LAB / "tools"
SUB_S = 0.12            # HyperFrames' seconds a (sub-)frame on this kind of PC (2026-10-23: 0.10-0.13, i5 + RTX 4070)
LIMIT_S = 540           # Claude's shell stops a command at 10 min: longer = a job
STILL_PX = 6            # a graphic whose fastest move is under this (px a frame) keeps its plain render in a final:
                        # its blur would be under ~5 px (HyperFrames renders a whole graphic, never a frame range)


def newest_plan(build: Path) -> Path:
    plans = sorted(build.glob("plan_v*.json"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 0))
    if not plans:
        raise SystemExit(f"no plan_vN.json in {build}")
    return plans[-1]


def compositions(plan: dict, build: Path) -> list[Path]:
    """The graphics' folders the plan's overlay layers show (build\\overlays\\<name>\\<name>.mov), in plan order."""
    out = []
    for L in plan.get("layers", []):
        if L.get("type") != "overlay" or not L.get("file"):
            continue
        f = Path(L["file"])
        f = f if f.is_absolute() else build / f
        if (f.parent / "index.html").exists() and f.parent not in out:
            out.append(f.parent)
    return out


def stale(folder: Path, blur: int, force: bool) -> bool:
    if force:
        return True
    s = OS.status(folder)
    rj = folder / "render.json"
    got = json.loads(rj.read_text(encoding="utf-8")).get("motion_blur", 1) if rj.exists() else None
    return not (s["current"] and int(got or 1) == blur)


def render_one(folder: Path, blur: int, workers: int | None) -> tuple[Path, int, float, str]:
    t0 = time.time()
    cmd = [PY, str(TOOLS / "overlay.py"), "render", str(folder), "--motion-blur", str(blur)]
    if workers:
        cmd += ["--workers", str(workers)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(LAB))
    return folder, r.returncode, time.time() - t0, (r.stdout + r.stderr)[-1200:]


def inputs_key(plan_path: Path, plan: dict, build: Path) -> str:
    """What the composite reads: the plan, every layer's file and the audio (size + time)."""
    h = hashlib.sha1(plan_path.read_bytes())
    files = [L.get("file") for L in plan.get("layers", []) if L.get("file")]
    files += [s.get("source") for s in (plan.get("sources") or {}).values() if isinstance(s, dict)]
    files.append((plan.get("audio") or {}).get("path"))
    for f in files:
        if not f:
            continue
        p = Path(f) if Path(f).is_absolute() else build / f
        if p.exists():
            st = p.stat()
            h.update(f"{p}:{st.st_size}:{st.st_mtime_ns}".encode())
    return h.hexdigest()[:16]


def mins(s: float) -> str:
    return f"{int(s // 60)}:{int(s % 60):02d}"


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("plan", nargs="?")
    ap.add_argument("--final", action="store_true", help="the graphics with motion blur, then the video")
    ap.add_argument("--motion-blur", type=int, default=5)
    ap.add_argument("--jobs", type=int, help="graphics rendered at the same time (default 1-3 by the CPU)")
    ap.add_argument("--sfx", action="store_true", help="make the sound effects + mix (then kept on every build)")
    ap.add_argument("--force", action="store_true", help="render every graphic again")
    a = ap.parse_args()
    t0 = time.time()
    proj = Path(a.project)
    proj = (proj if proj.is_dir() else LAB / "projects" / a.project).resolve()
    build = proj / "build"
    if not build.is_dir():
        raise SystemExit(f"no build folder: {build}")
    plan_path = (build / a.plan if a.plan and not Path(a.plan).is_absolute() else Path(a.plan)) if a.plan \
        else newest_plan(build)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    name, fps, N = plan.get("name", plan_path.stem), float(plan["fps"]), int(plan["frames"])
    blur = a.motion_blur if a.final else 1
    cpus = os.cpu_count() or 4
    jobs = a.jobs or (1 if cpus < 8 else min(3, cpus // 6))
    comps = compositions(plan, build)
    # captions' lines appear and fade, nothing travels: no blur to see, so a final renders them plain anyway (the
    # What's new 0.5.3 final, 2026-10-23: 8 of its 11.5 minutes were 1502 caption frames x 5 sub-frames)
    blur_of = {c: (1 if OS.conf(c).get("from") == "captions" else blur) for c in comps}
    todo = [c for c in comps if stale(c, blur_of[c], a.force)]
    still, plain = [], [c.name for c in todo if blur > 1 and blur_of[c] == 1]
    if a.final:                 # B2: a graphic that hardly moves gains nothing from motion blur - it stays plain
        from motionlab import precheck as PC
        for c in list(todo):
            if blur_of[c] == 1:
                continue
            mov = c / f"{OS.conf(c)['name']}.mov"
            if not stale(c, 1, False) and mov.exists():
                fm = PC.run(mov, verbose=False, out=c / "precheck").get("fastest_move") or {}
                if float(fm.get("px") or 0) < STILL_PX:
                    todo.remove(c)
                    still.append(f"{c.name} ({float(fm.get('px') or 0):.0f} px a frame at most)")
    est = sum(int(OS.conf(c)["frames"]) * blur_of[c] for c in todo) * SUB_S / max(1, min(jobs, len(todo) or 1)) + N * 0.05
    if est > LIMIT_S and not os.environ.get("MOTIONLAB_JOB"):
        print(f"{name}: about {mins(est)} of rendering ({len(todo)} graphics" + (f", motion blur {blur}" if a.final
              else "") + ") - longer than Claude's shell allows. Run it as a job:\n  .venv\\Scripts\\python "
              f"tools\\job.py start build project={proj.name} plan={plan_path.name}" + (" final=1" if a.final else "")
              + "\n  .venv\\Scripts\\python tools\\job.py wait <id>")
        return 3
    lines, report = [], {"plan": plan_path.name, "final": a.final, "motion_blur": blur, "started":
                         time.strftime("%Y-%m-%d %H:%M")}
    # 1. the graphics
    t1 = time.time()
    failed = []
    if todo:
        print(f"rendering {len(todo)} of {len(comps)} graphics, {min(jobs, len(todo))} at a time" + (f", motion blur {blur}" if
              blur > 1 else "") + " ...", flush=True)
        workers = max(1, cpus // 2 // jobs) if jobs > 1 else None
        with ThreadPoolExecutor(jobs) as ex:
            for folder, rc, secs, tail in ex.map(lambda c: render_one(c, blur_of[c], workers), todo):
                print(f"  {folder.name}: {'done' if rc == 0 else 'FAILED'} in {mins(secs)}", flush=True)
                if rc:
                    failed.append(folder.name)
                    print("    " + tail.strip().replace("\n", "\n    "))
    lines.append(f"graphics: {len(todo) - len(failed)} rendered" + (f" ({', '.join(c.name for c in todo)})"
                 if 0 < len(todo) <= 6 else "") + f", {len(comps) - len(todo)} up to date" +
                 (f", motion blur {blur}" if blur > 1 else "") + f" - {mins(time.time() - t1)}")
    if still:
        lines.append(f"kept plain (hardly move, no blur to see): {', '.join(still)}")
    if plain:
        lines.append(f"rendered plain (captions: the lines appear, nothing travels): {', '.join(plain)}")
    lines += [s for s in (OS.too_short(c) for c in comps) if s]
    report["graphics"] = {"rendered": [c.name for c in todo], "failed": failed, "up_to_date": len(comps) - len(todo),
                          "kept_plain": still, "plain_captions": plain}
    if failed:
        print("\n".join(lines) + f"\nSTOPPED: {', '.join(failed)} did not render - fix it, then build again")
        return 1
    # a landed graphic (the layer's own "land": overlay.py render prints it, an edit list's cuts move it): landed
    # again only when its settings moved the landing AND the layer still sits where it was landed - a layer moved by
    # hand stays; a landing that no longer resolves (a re-measured template) is a warning, never a failed build
    from motionlab import templates as TM
    moved, bad = [], []
    for L in plan.get("layers", []):
        ld, f = L.get("land"), Path(L.get("file") or "")
        if L.get("type") != "overlay" or not isinstance(ld, dict):
            continue
        if (L.get("start"), L.get("in", 0)) != (ld.get("start"), ld.get("in", 0)):
            continue
        try:
            r = TM.land_target(str(f.parent), ld["track"], ld["at"], ld.get("asked"))
        except (ValueError, KeyError, OSError) as e:
            bad.append(f"{f.parent.name}: {e}")
            continue
        if (r["start"], r["in"]) != (L.get("start"), L.get("in", 0)):
            L.update(start=r["start"], end=r["end"], **{"in": r["in"]})
            ld.update(start=r["start"], **{"in": r["in"]})
            moved.append(f"{f.parent.name} start f{r['start']} in {r['in']}")
    if moved:
        plan_path.write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")
        lines.append(f"landed again (its settings moved the move; plan layers set): {'; '.join(moved)}")
    lines += [f"NOT landed again (left where it is): {b}" for b in bad]
    # 2. the sound
    audio = (plan.get("audio") or {}).get("path") or ""
    made_mix = Path(audio).parent.name == "sfx" and Path(audio).stem.endswith("_mix")
    if a.sfx or plan.get("sfx") or made_mix:
        r = subprocess.run([PY, str(TOOLS / "sfx.py"), "plan", str(plan_path)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=str(LAB))
        if r.returncode:
            print(r.stdout[-1500:] + r.stderr[-800:])
            return 1
        stem = SFX.stem_name(plan.get("name") or plan_path.stem)
        mix, rep = build / "sfx" / f"{stem}_mix.wav", build / "sfx" / f"{stem}_sfx.json"
        cues = next((ln for ln in r.stdout.splitlines() if ln.startswith("cues:")), "")
        new_audio = mix.exists() and str(mix.resolve()) != str(Path(audio).resolve() if audio else "")
        if new_audio or not plan.get("sfx"):          # "sfx": true = kept on every build of this plan and its copies
            if new_audio:
                plan["audio"] = {**(plan.get("audio") or {}), "path": str(mix.resolve())}
            plan["sfx"] = True
            plan_path.write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")
        lines.append(f"sound: {cues[6:] or 'made'} -> {mix.name} (the plan's audio)")
        report["sfx"] = str(rep)
    else:
        rep = None
        lines.append("sound: the plan's audio as it is (no sound effects; --sfx makes them)")
    # 3. the composite
    t3 = time.time()
    out = Path(plan.get("output", f"{name}.mp4"))
    out = out if out.is_absolute() else build / out
    key = inputs_key(plan_path, plan, build)
    prev_p = build / "checks" / f"{name}_build.json"
    prev = json.loads(prev_p.read_text(encoding="utf-8")) if prev_p.exists() else {}
    if out.exists() and prev.get("composite_key") == key and not a.force:
        lines.append(f"video: {out.name} unchanged (nothing it reads changed)")
    else:
        r = subprocess.run([PY, str(TOOLS / "render_video.py"), str(plan_path)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=str(LAB))
        if r.returncode:
            print("\n".join(lines) + "\nSTOPPED: the video did not render\n" + (r.stdout + r.stderr)[-1500:])
            return 1
        lines.append(f"video: {out} ({N} frames, {N / fps:.1f} s) in {mins(time.time() - t3)}")
    report["composite_key"], report["video"] = key, str(out)
    # 4. the precheck
    from motionlab import precheck as PC
    res = PC.run(out, sfx=str(rep) if rep else None, verbose=False)
    fl = res["flags"]
    lines.append("precheck: PASS" if not fl else f"precheck: {len(fl)} to look at ({', '.join(f'{v} {k}' for k, v in res['counts'].items() if v)}) - {res['sheet']}")
    for f in fl[:5]:
        lines.append(f"  {f.get('label', '')}: {f.get('reason', '')}"[:150])
    if len(fl) > 5:
        lines.append(f"  +{len(fl) - 5} more in {Path(res['json']).name}")
    report["precheck"] = {"status": res["status"], "flags": len(fl), "json": res["json"]}
    mv = PC.plan_moves(plan)                    # 2026-10-24: too many camera moves / one inside a take (the plan)
    if mv["flags"]:
        lines.append(f"camera moves: {len(mv['flags'])} to look at ({len(mv['moves'])} moves in the plan)")
        lines += [f"  {f['label']}: {f['reason']}"[:220] for f in mv["flags"][:6]]
        fl = fl + mv["flags"]
    report["moves"] = {"count": len(mv["moves"]), "flags": len(mv["flags"])}
    # 5. the cut-sheet (plain builds: the one look before the final)
    if not a.final:
        r = subprocess.run([PY, str(TOOLS / "render_video.py"), str(plan_path), "--cuts"], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", cwd=str(LAB))
        sheets = [ln.strip() for ln in r.stdout.splitlines() if ln.strip().endswith(".jpg")]
        lines.append(f"cut-sheet: {sheets[0] if sheets else 'not made - ' + (r.stdout + r.stderr)[-300:]}")
        report["cut_sheet"] = sheets
        nxt = (f"next: look at the cut-sheet; then the final: tools\\job.py start build project={proj.name} "
               f"plan={plan_path.name} final=1")
    else:
        nxt = "done: the final is ready for the user's Review tab"
    total = time.time() - t0
    report["seconds"] = round(total, 1)
    prev_p.parent.mkdir(parents=True, exist_ok=True)
    prev_p.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{name} ({'final' if a.final else 'plain'} build, {mins(total)}; {N} frames {frame_to_tc(0, fps)}-"
          f"{frame_to_tc(N - 1, fps)}):")
    print("\n".join(lines))
    print(nxt)
    return 0 if not fl else 2                   # 2 = built, with precheck flags to look at


if __name__ == "__main__":
    sys.exit(main())
