"""A quick draft for Generate (0.5.3): a motion-graphics video from the request by rules, no Claude - so Claude edits a
scene table instead of writing a build. Always shown as a draft; the user's rating of the result decides.

    .venv\\Scripts\\python tools\\gen_draft.py <project> [--length 30] [--format vertical|horizontal|square]
          [--song <file> --start 21.4] [--build]
          1. the timeline: the request's length at 30 fps; with a song, its beats (beats.py) from --start - a scene
             changes on a downbeat, the first drop gets a cut (the biggest change); no song = a cut every ~2.5 s
          2. the scenes: one per line of the request's words (its "text"; none = ~one per 2.5 s with the templates'
             own words), the first is the hook, the last (3 scenes or more) the end card
          3. a template per scene (templates.py pick on the scene's words + the request; the user's picks first;
             never the same one twice in a row; one NOT ok at the size is left out; a number -> a counter, the end ->
             an end card), its main words set to the line, the request's look (a look-aware template) and size
          4. build\\plan_vN.json (overlay layers back to back, the song from --start cut into build\\ as a copy) +
             build\\gen_draft_vN.md (the scene table: frames + timecodes, template, words, why); --build = one plain
             build (tools\\build.py --sfx: the graphics, the sound, the video, the precheck, the cut-sheet)
Writes only into projects\\<project>\\build\\; the song is only read.
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

from motionlab import looks as LK  # noqa: E402
from motionlab import overlay_settings as OS  # noqa: E402
from motionlab import templates as TM  # noqa: E402
from motionlab.style import SIZES  # noqa: E402
from motionlab.timecode import frame_to_tc  # noqa: E402
from motionlab.util import LAB, setup_console, tool  # noqa: E402

FPS = 30
PY, TOOLS = sys.executable, LAB / "tools"
SCENE_S = 2.5                                   # a scene without words to time it: ~one per 2.5 s (local-make-9 holds)
END_IDS = ("end-screen", "subscribe-cta", "logo-reveal", "title-card")
NOT_SCENES = {"transitions", "background", "lower_thirds"}     # over a scene, never one by itself
TEXT_IDS = ("text", "title", "words", "headline", "line", "caption", "label", "quote")


def run(*args: str) -> str:
    r = subprocess.run([PY, str(TOOLS / args[0]), *args[1:]], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=str(LAB))
    if r.returncode:
        raise SystemExit(f"{args[0]} {args[1] if len(args) > 1 else ''} failed:\n{(r.stdout + r.stderr)[-1200:]}")
    return r.stdout


def cuts_for(N: int, k: int, beats: list[dict], drops: list[int]) -> list[int]:
    """k scenes over N frames: k - 1 cuts at even places, each moved to the nearest downbeat (else beat), the first
    drop a cut; never a scene under 1 s."""
    cand = [b["frame"] for b in beats if b["downbeat"]] or [b["frame"] for b in beats]
    out = []
    for i in range(1, k):
        want = round(i * N / k)
        f = min(cand, key=lambda c: abs(c - want)) if cand and min(abs(c - want) for c in cand) < N / k / 2 else want
        if (not out or f - out[-1] >= FPS) and FPS <= f <= N - FPS:
            out.append(f)
    d = next((x for x in drops if FPS < x < N - 2 * FPS), None)
    if d is not None and out and d not in out:
        j = min(range(len(out)), key=lambda i: abs(out[i] - d))
        if (j == 0 or d - out[j - 1] >= FPS) and (j == len(out) - 1 or out[j + 1] - d >= FPS):
            out[j] = d
    return sorted(set(out))


def main_text(decl: list[dict], t: dict) -> str | None:
    slots = [s["id"] if isinstance(s, dict) else s for s in t.get("text_slots") or []]
    ids = [d["id"] for d in decl if d["type"] == "string"]
    for k in slots + [i for i in TEXT_IDS if i in ids] + ids:
        if k in ids and not any(w in k for w in ("media", "focus", "logo", "image", "photo", "video", "emoji")):
            return k
    return None


def choose(words: str, want: str, role: str, used_last: str | None, user: list[str], i: int, size: str,
           lib: dict) -> tuple[dict, str]:
    if user:
        tid = user[i % len(user)]
        return lib[tid], "your pick"
    num = re.search(r"\d", words or "")
    pref = END_IDS if role == "end" else (("big-counter", "stat-cards") if num else ())
    for tid in pref:
        if tid in lib and tid != used_last and size not in (lib[tid].get("sizes_bad") or []):
            return lib[tid], "the end card" if role == "end" else "a number in the words"
    for t in TM.pick(f"{words} {want}".strip() or want, 16):
        T = lib.get(t["id"])
        if not T or T["id"] == used_last or T.get("kind") in NOT_SCENES or T.get("needs_media") or T.get("media_slots"):
            continue
        if size in (T.get("sizes_bad") or []):
            continue
        if T.get("local") and size not in (T.get("sizes_ok") or []):
            c = OS.conf(LAB / T["folder"])
            if f"{c['width']}x{c['height']}" != size:      # this PC's templates: only at a size checked ok
                continue
        why = f"fits the words ({', '.join(t['matched'][:3])})" if t.get("matched") else "a general one"
        return T, ("the hook: " if role == "hook" else "") + why
    T = lib.get("kinetic-stack") or next(iter(lib.values()))
    return T, "the fallback"


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--length", type=float)
    ap.add_argument("--format", choices=sorted(SIZES))
    ap.add_argument("--song")
    ap.add_argument("--start", type=float, default=0.0, help="seconds into the song = frame 0")
    ap.add_argument("--build", action="store_true", help="one plain build after (tools\\build.py --sfx)")
    a = ap.parse_args()
    p = Path(a.project)
    p = (p if p.is_dir() else LAB / "projects" / a.project).resolve()
    b = p / "build"
    rq = b / "generate_request.json"
    if not rq.exists():
        raise SystemExit(f"{p.name}: no build\\generate_request.json (the Generator's request)")
    req = json.loads(rq.read_text(encoding="utf-8"))
    if req.get("kind") != "graphics":
        raise SystemExit("a quick draft is for a motion-graphics request (kind graphics)")
    length = float(a.length or req.get("length_s") or 30)
    fmt = a.format or req.get("format") or "vertical"
    W, H = SIZES[fmt]
    size, N = f"{W}x{H}", int(round(length * FPS))
    song = a.song or req.get("music")
    beats, drops = [], []
    if song:
        txt = run("beats.py", str(song), "--fps", str(FPS), "--start", f"{a.start}", "--length", f"{length}", "--json")
        out = json.loads(txt[txt.index("\n{") + 1 if not txt.startswith("{") else 0:])     # after its log lines
        beats, drops = out["beats"], [d["frame"] for d in out["drops"]]
    lines = [ln.strip() for ln in str(req.get("text") or "").splitlines() if ln.strip()]
    k = len(lines) if lines else max(3, round(length / SCENE_S))
    k = max(1, min(k, N // FPS))                       # a scene lasts 1 s at least
    cuts = cuts_for(N, k, beats, drops)
    bounds = [0] + cuts + [N]
    scenes = len(bounds) - 1
    if len(lines) > scenes:                            # more lines than the length holds: lines share scenes, in
        groups = [lines[round(j * len(lines) / scenes):round((j + 1) * len(lines) / scenes)]   # order (never dropped)
                  for j in range(scenes)]
        print(f"NOTE: {len(lines)} lines of words in {scenes} scenes ({length:g} s, 1 s a scene at least): "
              "lines share a scene - more length, or fewer lines, gives each its own")
        lines = [" / ".join(g) for g in groups]
    lib = {t["id"]: t for t in TM.library()}
    user = [x for x in req.get("templates") or [] if x in lib]
    look = req.get("look") if req.get("look") and req.get("look") != "surprise" else None
    look_vals = LK.values(LK.all_looks()[look]) if look and look in LK.all_looks() else {}
    v = 1 + max([int(re.sub(r"\D", "", q.stem) or 0) for q in b.glob("plan_v*.json")] or [0])
    rows, layers, last = [], [], None
    for i, (s, e) in enumerate(zip(bounds, bounds[1:])):
        words = lines[i] if i < len(lines) else ""
        role = "hook" if i == 0 else "end" if i == len(bounds) - 2 and len(bounds) > 3 else "scene"
        T, why = choose(words, req.get("want", ""), role, last, user, i, size, lib)
        last = T["id"]
        decl = OS.declared(LAB / T["folder"])
        ids = {d["id"] for d in decl}
        vals = {kk: vv for kk, vv in look_vals.items() if kk in ids}
        txt = main_text(decl, T)
        num = re.search(r"(\d+(?:\.\d+)?)", words)
        if num and "to" in ids:                         # a counter: the number counts, the rest is its caption
            vals["to"] = float(num[1]) if "." in num[1] else int(num[1])
            rest = " ".join(words.replace(num[1], " ").replace("%", " ").replace("$", " ").split())
            vals.update({k: v for k, v in (("suffix", "%" if "%" in words else ""), ("prefix", "$" if "$" in words
                         else ""), ("label", ""), ("caption", rest)) if k in ids})
        elif words and txt:
            vals[txt] = words
        if "background" in ids:
            vals["background"] = True
        folder = b / "overlays" / f"d{v}_{i + 1:02d}_{T['id']}"
        args = ["overlay.py", "new", str(folder), "--from", T["id"], "--frames", str(e - s), "--fps", str(FPS),
                "--width", str(W), "--height", str(H), "--force"]
        if vals:
            args += ["--values", json.dumps(vals, ensure_ascii=False)]
        got = run(*args)
        short = next((ln for ln in got.splitlines() if ln.startswith("TOO SHORT")), "")
        layers.append({"type": "overlay", "id": folder.name, "file": str(folder / f"{folder.name}.mov"),
                       "start": s, "end": e - 1, "blend": "normal"})
        rows.append((s, e - 1, T["id"], words or f"(the template's own words{' - set ' + txt if txt else ''})",
                     why + ("; " + short.split(" - ")[0] if short else "")))
    audio = None
    if song:
        src = Path(song) if Path(song).is_absolute() else LAB / song
        cut = b / f"song_from_{a.start:g}s.wav" if a.start else None
        if cut:                                         # the part of the song the video uses: a copy in build\
            subprocess.run([tool("ffmpeg"), "-v", "error", "-y", "-ss", f"{a.start}", "-t", f"{length + 1}", "-i",
                            str(src), str(cut)], check=True)
        audio = {"path": str(cut or src)}
    plan = {"name": f"{p.name}_v{v}", "width": W, "height": H, "fps": FPS, "frames": N, "sources": {}, "grades": {},
            "layers": layers, **({"audio": audio} if audio else {}), "output": f"{p.name}_v{v}.mp4", "sfx": True,
            "made_by": {"tool": "gen_draft.py", "song": song, "start_s": a.start, "format": fmt, "look": look,
                        "date": time.strftime("%Y-%m-%d %H:%M")}}
    (b / f"plan_v{v}.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")
    md = [f"# Quick draft v{v} of {p.name} - by rules, no Claude (tools\\gen_draft.py)", "",
          f"{length:g} s, {size} at {FPS} fps" + (f", {Path(song).name} from {a.start:g} s" if song else ", no song")
          + (f", the look '{look}'" if look else "") + f"; {len(rows)} scenes" + (
              f", cuts on downbeats{', a cut on the drop f' + str(drops[0]) if drops else ''}" if beats else ""), "",
          "| scene | frames | timecode | template | words | why |", "|---|---|---|---|---|---|"]
    md += [f"| {i} | f{s}-f{e} | {frame_to_tc(s, FPS)}-{frame_to_tc(e, FPS)} | {tid} | {w} | {why} |"
           for i, (s, e, tid, w, why) in enumerate(rows, 1)]
    md += ["", "Claude: change this table (the words, which template says what, the rhythm against the song), not a "
               "build - the settings of each scene: `overlay.py settings <folder>` / `set`; a move on a beat: "
               "`overlay.py new <folder> --from <id> --land \"<track>@<frame>\"`; then `tools\\build.py <project>`."]
    (b / f"gen_draft_v{v}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md[:2 + len(rows) + 4]))
    print(b / f"plan_v{v}.json")
    if a.build:                                         # its exit 1 = precheck flags to look at, not a failure here
        r = subprocess.run([PY, str(TOOLS / "build.py"), str(p), f"plan_v{v}.json", "--sfx"], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", cwd=str(LAB))
        print((r.stdout + r.stderr)[-3000:])
        return 0 if r.returncode in (0, 2) else r.returncode      # 2 = built with flags
    return 0


if __name__ == "__main__":
    sys.exit(main())
