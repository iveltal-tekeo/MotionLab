"""Motion-graphics templates (0.5.0): captured template clips measured with no Claude, Claude's cards on them, and the
Motion Graphics library - MotionLab's own HyperFrames rebuilds in tools\\overlays\\motion\\<id>\\ that a video or
Generate starts from. The logic is tools\\motionlab\\templates.py (its docstring says what is measured and how).

    .venv\\Scripts\\python tools\\templates.py read <folder of clips> [--pack swishy] [--force] [--only id,id]
          every clip measured (moves with frame + timecode, their ease, holds and what keeps them alive, scene changes,
          loops, colours) -> analysis\\templates\\<pack>\\pack.json + <id>\\sheet.png + poster.jpg + overview_N.png
          (8 clips a page, for Claude). The clips are only read; their SHA-256 is recorded and checked. Re-used while
          a clip is unchanged (~0.6 s a clip: 131 Swishy clips in 76 s, 2026-10-16)
    .venv\\Scripts\\python tools\\templates.py show <pack> [<id | n>]   the numbers in words (one clip: every move)
    .venv\\Scripts\\python tools\\templates.py verify <pack>            the clips' SHA-256 against the first read
    .venv\\Scripts\\python tools\\templates.py library [--brief]        the rebuilt templates (id, kind, size, settings);
          --brief = one short line each: its tracks and the sizes it is ok / NOT ok at
    .venv\\Scripts\\python tools\\templates.py tracks [<id> ...] [--measure [--force]]   (0.5.3) a template's moves
          with frame + timecode (hand-written in template.json, else measured.json); --measure = the templates with
          none rendered plain and their moves measured (+ FAST lines: moves over 60 px a frame that show copies with
          motion blur - smear() them)
    .venv\\Scripts\\python tools\\templates.py land <id | a copy's folder> <track> --at <plan frame> [--start <cut>]
          [--hit start|peak|end]   the layer's start and "in" so that move lands on that frame (a copy: its rate, length
          and "start" setting) - what overlay.py new --land does
    .venv\\Scripts\\python tools\\templates.py sizes [<id> ...] [--sizes 1080x1920,1080x1080] [--force]   (0.5.3, the PC in
          bulk) each template at other sizes, no render: the text-fit check against its own size and the ink it draws
          -> measured.json "sizes" (ok / NOT ok + why), shown by library --brief and the brief
    .venv\\Scripts\\python tools\\templates.py pick "<the user's words>" [--n 6] [--kinds text,overlays]
          the library templates that fit the words best (Generate starting blind) - one line each, best first
    .venv\\Scripts\\python tools\\templates.py todo <pack>              the clips not rebuilt yet, by Claude's rebuild
          priority (cards.json "rebuild" 1 first), with their sheet
    .venv\\Scripts\\python tools\\templates.py selfcheck                a synthetic clip with known moves (temp folder)
    .venv\\Scripts\\python tools\\templates.py finish <id> [<id> ...]    a local template (library\\motion_graphics\\local\\<pack>\\<id>,
          learned from the user's own clips) verified and stored: rendered (.app\\dev\\motion), its motion compared with
          the reference clip (motion energy correlation + duration, score 0-1, "ok" at 0.6 - motionlab\\template_match.py)
          -> match.json, compare.png (reference above, render below, frame + timecode), side_by_side.mp4, preview.mp4
          (720p), thumb.png, spec.json; progress.json + library\\motion_graphics\\index.json
    .venv\\Scripts\\python tools\\templates.py progress <pack>          the local templates of a pack: ok / needs-work / score
    .venv\\Scripts\\python tools\\templates.py index                    rewrite library\\motion_graphics\\index.json
    .venv\\Scripts\\python tools\\templates.py looks [sync]             the looks (tools\\overlays\\motion\\_looks); sync = after
          editing one: every look-aware template's defaults = the default look

`check <id> [--size WxH@fps] [--values JSON]` = snapshots at its check frames + the text-fit lines (FIT: text off the
frame, outside its box, overlapping).
A template is used like any graphic: `overlay.py new projects\\<p>\\build\\overlays\\<name> --from <template id>`, then
`overlay.py fit <folder> --like <video>` (any size / rate / length) or `overlay.py set`, `snap`, `render`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import overlay_settings as OS  # noqa: E402
from motionlab import templates as T  # noqa: E402
from motionlab import template_read as R  # noqa: E402
from motionlab.util import LAB, setup_console  # noqa: E402


def _item(d: dict, key: str) -> dict:
    for it in d["items"]:
        if it["id"] == key or str(it.get("n")) == key or it["slug"] == key:
            return it
    raise SystemExit(f"no clip '{key}' in {d['pack']}")


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("read")
    s.add_argument("folder")
    s.add_argument("--pack")
    s.add_argument("--force", action="store_true")
    s.add_argument("--only")
    s = sub.add_parser("show")
    s.add_argument("pack")
    s.add_argument("item", nargs="?")
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("verify")
    s.add_argument("pack")
    s = sub.add_parser("library")
    s.add_argument("--brief", action="store_true", help="one short line each: no settings, + tracks and sizes ok")
    s = sub.add_parser("pick")
    s.add_argument("want")
    s.add_argument("--n", type=int, default=6)
    s.add_argument("--kinds")
    s = sub.add_parser("todo")
    s.add_argument("pack")
    s = sub.add_parser("land")
    s.add_argument("target", help="a template id, or a copy of one (projects\\<p>\\build\\overlays\\<name>)")
    s.add_argument("track", help="the track's number, name or a word of it (templates.py tracks <id> lists them)")
    s.add_argument("--at", type=int, required=True, help="the plan frame the move must land on (a beat)")
    s.add_argument("--start", type=int, help="the layer's first plan frame (a cut); default: the template from f0")
    s.add_argument("--hit", choices=("start", "peak", "end"), default="start")
    s.add_argument("--fps", type=float, help="the plan's rate for the timecodes (default: the copy's / template's)")
    s = sub.add_parser("tracks")
    s.add_argument("ids", nargs="*")
    s.add_argument("--measure", action="store_true", help="render and measure the templates with no tracks yet")
    s.add_argument("--force", action="store_true", help="with --measure: measure again")
    s = sub.add_parser("sizes")
    s.add_argument("ids", nargs="*")
    s.add_argument("--sizes", default="1080x1920,1080x1080")
    s.add_argument("--force", action="store_true", help="check again sizes already checked")
    s = sub.add_parser("check")
    s.add_argument("ids", nargs="*")
    s.add_argument("--frames")
    s.add_argument("--size", help="e.g. 1920x1080@25: the template retimed to another size first (a fit test)")
    s.add_argument("--values", help='settings to try, JSON: {"look": "pastel"} (the picture is kept)')
    sub.add_parser("selfcheck")
    s = sub.add_parser("finish")
    s.add_argument("ids", nargs="+")
    s = sub.add_parser("progress")
    s.add_argument("pack")
    sub.add_parser("index")
    s = sub.add_parser("looks")
    s.add_argument("what", nargs="?", default="show")
    a = ap.parse_args()

    if a.cmd == "read":
        src = Path(a.folder)
        if not src.is_absolute():
            src = (LAB / src) if (LAB / src).exists() else src
        R.read_pack(src, a.pack, a.force, a.only.split(",") if a.only else None)
        return 0
    if a.cmd == "show":
        d = T.load_pack(a.pack)
        if not d:
            raise SystemExit(f"no pack '{a.pack}' (read it first: templates.py read <folder>)")
        if a.item:
            it = _item(d, a.item)
            if a.json:
                print(json.dumps({k: v for k, v in it.items() if k != "motion"} | {"motion": {
                    k: v for k, v in it["motion"].items() if k != "change"}}, indent=1, ensure_ascii=False))
                return 0
            for ln in T.describe(it):
                print(ln)
            card = T.load_cards(d["pack"]).get(it["id"])
            if card:
                print(f"  Claude's card: {card.get('what', '')}")
            print(f"  sheet: {T.root() / d['pack'] / it['id'] / 'sheet.png'}")
            return 0
        cards = T.load_cards(d["pack"])
        print(f"{d['pack']}: {len(d['items'])} clips from {d['source']} (read {d['read']}), "
              + ", ".join(f"{v} {k}" for k, v in sorted(d["kinds"].items())) + f"; Claude's cards: {len(cards)}")
        for it in d["items"]:
            mo = it["motion"]
            print(f"  #{it['n']:<3} {it['id']:58s} {it['frames']:5d} f {it['seconds']:6.2f} s  "
                  + ("still capture" if it["still"] else
                     f"{len(mo['moves']):2d} moves, moving {round(100 * mo['moving_share']):3d} %"
                     + (", loops" if mo["loops"] else "")))
        return 0
    if a.cmd == "verify":
        bad = T.verify(a.pack)
        print("all clips unchanged" if not bad else "CHANGED since the first read:\n  " + "\n  ".join(bad))
        return 1 if bad else 0
    if a.cmd == "library":
        lib = T.library()
        if not lib:
            print("no rebuilt templates yet (tools\\overlays\\motion\\)")
        for t in lib:
            c = OS.conf(LAB / t["folder"])
            head = (f"  {t.get('kind', ''):10s} {t['id']:24s} {c['frames']:4d} f {float(c['fps']):g} fps "
                    f"{c['width']}x{c['height']}  {t.get('name', '')}")
            if a.brief:
                print(head + f" - {len(t.get('tracks') or [])} tracks"
                      + (f", ok at {', '.join(t['sizes_ok'])}" if t.get("sizes_ok") else "")
                      + (f", NOT at {', '.join(t['sizes_bad'])}" if t.get("sizes_bad") else ""))
                continue
            decl = OS.declared(LAB / t["folder"])
            print(head + f" - settings: {', '.join(d['id'] for d in decl)}")
        return 0
    if a.cmd == "land":
        try:
            r = T.land_target(a.target, a.track, a.at, a.start, a.hit)
            fps = a.fps or float(OS.conf(Path(a.target) if (Path(a.target) / "overlay.json").exists()
                                         else OS.find_graphic(a.target))["fps"])
        except ValueError as e:
            raise SystemExit(str(e))
        print(T.land_line(r, fps))
        print(json.dumps({k: r[k] for k in ("start", "end", "in") if r.get(k) is not None}))
        return 0
    if a.cmd == "tracks":
        return tracks(a.ids, a.measure, a.force)
    if a.cmd == "sizes":
        return sizes(a.ids, a.sizes.split(","), a.force)
    if a.cmd == "pick":
        for t in T.pick(a.want, a.n, a.kinds.split(",") if a.kinds else None):
            print(f"  {t['score']:5.1f}  {t['id']:24s} {t.get('kind', ''):10s} {t.get('what', '')[:90]}"
                  + (f"  [{', '.join(t['matched'])}]" if t["matched"] else ""))
        return 0
    if a.cmd == "todo":
        d = T.load_pack(a.pack) or {"items": [], "pack": a.pack}
        cards = T.load_cards(d["pack"])
        built = {f"{f.get('pack')}/{f.get('clip')}" for t in T.library() for f in t.get("learned_from", [])}
        rows = [(cards.get(it["id"], {}).get("rebuild", 9), it) for it in d["items"]
                if f"{d['pack']}/{it['id']}" not in built and not it["still"]]
        rows.sort(key=lambda r: (r[0], r[1]["n"]))
        for pr, it in rows:
            print(f"  p{pr if pr != 9 else '-'}  #{it['n']:<3} {it['id']:58s} {cards.get(it['id'], {}).get('what', '')[:70]}")
        print(f"{len(rows)} not rebuilt yet")
        return 0
    if a.cmd == "check":
        return check(a.ids, a.frames, a.size, a.values)
    if a.cmd == "selfcheck":
        r = R.selfcheck()
        return 0 if all(r.values()) else 1
    if a.cmd == "finish":
        return max(finish(i) for i in a.ids)
    if a.cmd == "progress":
        rows = T.progress(a.pack)["templates"]
        for tid, r in sorted(rows.items()):
            print(f"  {r.get('status', ''):11s} {r.get('score', ''):>6}  {tid:34s} passes {r.get('passes', 0)}  "
                  f"{', '.join(r.get('clips', []))[:80]}")
        ok = sum(1 for r in rows.values() if r.get("status") == "ok")
        print(f"{len(rows)} templates: {ok} ok, {len(rows) - ok} needing work")
        return 0
    if a.cmd == "index":
        print(T.write_index())
        return 0
    if a.cmd == "looks":
        from motionlab import looks as LK
        if a.what == "sync":
            n = [p.parent.name for p in sorted(T.LOCAL.glob("*/*/index.html")) + sorted(T.MOTION.glob("*/index.html"))
                 if LK.is_look_aware(p.parent) and LK.sync_file(p)]
            print(f"defaults set from the look '{LK.index()['default']}' in: {', '.join(n) or 'none (all current)'}")
            return 0
        ix = LK.index()
        for i, lk in LK.all_looks().items():
            print(f"  {'*' if i == ix['default'] else ' '} {i:14s} {lk.get('name', '')}: {', '.join(lk['fonts'].values())}; "
                  f"{', '.join(f'{k} {v}' for k, v in lk['palette'].items())}; radius {lk.get('radius')}, "
                  f"shadow {lk.get('shadow')}, grain {lk.get('grain')} %")
        print("  * = the default (tools\\overlays\\motion\\_looks\\index.json)")
        return 0
    return 2


def finish(tid: str) -> int:
    """Render a local template, compare its motion with its reference clip and store everything next to it."""
    import shutil
    import subprocess
    from motionlab import template_match as M
    from motionlab.util import tool
    folder = T.local_folder(tid)
    if not folder:
        print(f"{tid}: not a local template (library\\motion_graphics\\local\\<pack>\\{tid})")
        return 1
    t = json.loads((folder / "template.json").read_text(encoding="utf-8"))
    ref = LAB / t["reference_clip"]
    if not ref.exists():
        print(f"{tid}: the reference clip is missing: {ref}")
        return 1
    py, ov = sys.executable, str(LAB / "tools" / "overlay.py")
    work = LAB / ".app" / "dev" / "motion" / f"{tid}_finish"
    shutil.rmtree(work, ignore_errors=True)
    # grain off for the check: it is the look's texture, not motion (its 12 steps a second would swamp subtle moves)
    grain = ["--values", json.dumps({"grain": 0})] if "grain" in {d["id"] for d in OS.declared(folder)} else []
    for cmd in ([py, ov, "new", str(work), "--from", tid] + grain, [py, ov, "render", str(work), "--mp4"]):
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode:
            print(f"{tid}: {' '.join(cmd[2:4])} failed\n{r.stdout[-1500:]}{r.stderr[-1500:]}")
            return 1
    mp4 = work / f"{work.name}.mp4"
    m = M.match(ref, mp4, folder, title=f"{t.get('name', tid)}: reference clip (top) vs MotionLab in your look (bottom)")
    ff = tool("ffmpeg")
    # preview.mp4: a light 720p copy for the app's grid; side_by_side.mp4: the reference beside the render, 540 high
    subprocess.run([ff, "-v", "error", "-y", "-i", str(mp4), "-vf",
                    "scale='if(gt(iw,ih),-2,720)':'if(gt(iw,ih),720,-2)'", "-c:v", "libx264", "-crf", "28",
                    "-preset", "slow", "-pix_fmt", "yuv420p", "-an", str(folder / "preview.mp4")], check=True)
    subprocess.run([ff, "-v", "error", "-y", "-i", str(ref), "-i", str(mp4), "-filter_complex",
                    "[0:v]scale=-2:540,setsar=1,fps=30[a];[1:v]scale=-2:540,setsar=1,fps=30[b];"
                    "[a][b]hstack=shortest=0[o]",              # the shorter one holds its last frame
                    "-map", "[o]", "-c:v", "libx264", "-crf", "24", "-pix_fmt", "yuv420p", "-an", str(folder / "side_by_side.mp4")], check=True)
    tf = int(t.get("thumb_f") or 0)
    c = OS.conf(folder)
    subprocess.run([ff, "-v", "error", "-y", "-ss", f"{tf / float(c['fps']):.4f}", "-i", str(mp4), "-frames:v", "1",
                    "-vf", "scale='if(gt(iw,ih),640,-2)':'if(gt(iw,ih),-2,640)'", str(folder / "thumb.png")],
                   check=True)
    (folder / "spec.json").write_text(json.dumps(T.spec(folder), indent=1, ensure_ascii=False), encoding="utf-8")
    pack = folder.parent.name
    prev = T.progress(pack)["templates"].get(tid, {})
    T.set_progress(pack, tid, clips=[f.get("clip") for f in t.get("learned_from", [])], status=m["status"],
                   score=m["score"], passes=prev.get("passes", -1) + 1, name=t.get("name"))
    fast = _fast_moves(mp4, folder)
    T.write_index()
    print(f"{tid}: {m['status']} - score {m['score']} (motion correlation {m['correlation']}, duration "
          f"{m['duration_render_s']} s vs {m['duration_ref_s']} s); {folder / 'compare.png'}")
    for ln in fast:
        print("  " + ln)
    return 0


def _fast_moves(mp4: Path, folder: Path) -> list[str]:
    """0.5.3 (A5): the moves of a template's plain render over 60 px a frame (precheck.py's rule) - with motion blur
    5 they show as copies over 12 px apart (ae_50_test's stepped stripes, local-make-11(4)), so they get a smear()
    in the template, once, here - not a look by Claude in every video. -> measured.json "fast_moves"."""
    from motionlab import precheck as PC
    res = PC.run(mp4, verbose=False, out=mp4.parent / "precheck")
    fl = [{"frames": f["frames"], "label": f.get("label", ""), "reason": f.get("reason", "")}
          for f in res["flags"] if f.get("check") == "move"]
    T.save_measured(folder, fast_moves=fl)
    return [f"FAST {f['label']}: {f['reason'][:110]} - smear() it in the template (copies with motion blur)"
            for f in fl[:6]] + ([f"  +{len(fl) - 6} more fast moves (measured.json)"] if len(fl) > 6 else [])


def _copy(tid: str, size: str | None = None, values: str | None = None, suffix: str = "") -> Path | str:
    """A scratch copy of a template in .app\\dev\\motion (overlay.py new --from), at another size when asked:
    its folder, or the error text."""
    import hashlib
    import re
    import shutil
    import subprocess
    tag = ("_v" + hashlib.sha1(values.encode("utf-8")).hexdigest()[:6]) if values else ""   # one folder per look tried
    dst = LAB / ".app" / "dev" / "motion" / (tid + (f"_{size.replace('@', '_')}" if size else "") + tag + suffix)
    shutil.rmtree(dst, ignore_errors=True)
    cmd = [sys.executable, str(LAB / "tools" / "overlay.py"), "new", str(dst), "--from", tid] + (
        ["--values", values] if values else [])
    if size:
        m = re.fullmatch(r"(\d+)x(\d+)(?:@([\d.]+))?", size)
        if not m:
            raise SystemExit("--size like 1920x1080@25")
        cmd += ["--width", m[1], "--height", m[2]] + (["--fps", m[3]] if m[3] else [])
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return f"{r.stdout}{r.stderr}" if r.returncode else dst


def _check_frames(t: dict, dst: Path, frames: str | None = None) -> str:
    """The frames to look at in a copy: --frames, else template.json "check_frames" (else 5 across it), at the
    copy's rate."""
    c = json.loads((dst / "overlay.json").read_text(encoding="utf-8"))
    if frames:
        return frames
    own = OS.conf(LAB / t["folder"])
    fr = t.get("check_frames") or [round(i * (int(own["frames"]) - 1) / 4) for i in range(5)]
    k = float(c["fps"]) / float(own["fps"])
    return ",".join(str(min(int(c["frames"]) - 1, round(int(f) * k))) for f in fr)


def check(ids: list[str], frames: str | None, size: str | None, values: str | None = None) -> int:
    """Each template copied into .app\\dev\\motion\\<id> (scratch) and snapped at its check frames (template.json
    "check_frames") - no render; the sheet path is printed, then the text-fit flags (0.5.3 A2); the thumb_f snapshot
    becomes the template's thumb.png."""
    import shutil
    from PIL import Image
    lib = {t["id"]: t for t in T.library()}
    ids = ids or sorted(lib)
    bad = 0
    for tid in ids:
        if tid not in lib:
            print(f"{tid}: not in the library")
            bad += 1
            continue
        t = lib[tid]
        dst = _copy(tid, size, values)
        if isinstance(dst, str):
            print(f"{tid}: copy failed\n{dst}")
            bad += 1
            continue
        fr = _check_frames(t, dst, frames)
        import overlay as OVL                        # tools\overlay.py: HyperFrames' snapshots, no render
        from motionlab.timecode import frame_to_tc
        c = OVL.read_conf(dst)
        want = OVL.parse_frames(fr, int(c["frames"]))
        tf = t.get("thumb_f")
        if tf is not None and not size and not values and int(tf) not in want:
            want = sorted(set(want) | {int(tf)})
        (dst / "snap").mkdir(exist_ok=True)
        try:
            arrs, secs = OVL.snapshots(dst, want, dst / "snap" / ".work")
        except SystemExit as e:
            print(f"{tid}: snapshot failed - {e}")
            bad += 1
            continue
        finally:
            shutil.rmtree(dst / "snap" / ".work", ignore_errors=True)
        tiles = [(f"f{f} ({frame_to_tc(f, float(c['fps']))})", OVL.on_checker(a)) for f, a in zip(want, arrs)]
        sheet = dst / "snap" / "sheet.png"
        OVL.sheet(tiles, sheet)
        if tf is not None and not size and not values:
            im = OVL.on_checker(arrs[want.index(int(tf))]).convert("RGB")      # no label on the template's picture
            im.thumbnail((360, 640) if im.height >= im.width else (640, 360), Image.LANCZOS)
            im.save(LAB / t["folder"] / "thumb.png", optimize=True)
        print(f"{tid}: {sheet}  ({len(want)} snapshots in {secs:.1f} s)")
        try:
            for f in OVL.fit_check(dst, want, dst / "snap" / ".work"):
                print("  " + f["line"])
        finally:
            shutil.rmtree(dst / "snap" / ".work", ignore_errors=True)
    return 1 if bad else 0


def tracks(ids: list[str], measure: bool, force: bool) -> int:
    """A template's tracks with frame + timecode (what `land` lands); --measure = the templates with no hand-written
    tracks rendered plain at their own size (.app\\dev\\motion, grain off) and their moves measured
    (motionlab\\template_read.py, the same reading as a captured clip) -> measured.json "tracks"."""
    import datetime
    import shutil
    import subprocess
    from motionlab.timecode import frame_to_tc
    lib = {t["id"]: t for t in T.library()}
    bad = 0
    for tid in ids or sorted(lib):
        t = lib.get(tid)
        if not t:
            print(f"{tid}: not in the library")
            bad += 1
            continue
        folder = LAB / t["folder"]
        own = json.loads((folder / "template.json").read_text(encoding="utf-8")).get("tracks")
        if measure and not own and (force or not T.measured(folder).get("tracks")):
            dst = _copy(tid, suffix="_tracks",
                        values=json.dumps({"grain": 0}) if "grain" in {d["id"] for d in OS.declared(folder)} else None)
            r = None if isinstance(dst, str) else subprocess.run(
                [sys.executable, str(LAB / "tools" / "overlay.py"), "render", str(dst), "--mp4"],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
            if isinstance(dst, str) or r.returncode:
                print(f"{tid}: render failed\n{(dst if isinstance(dst, str) else r.stdout + r.stderr)[-800:]}")
                bad += 1
                continue
            _, mo = R.measure(dst / f"{dst.name}.mp4")
            for ln in _fast_moves(dst / f"{dst.name}.mp4", folder):
                print("  " + ln)
            tr = []
            for i, m in enumerate(mo["moves"], 1):
                tr.append({"name": f"move {i}", "what": f"a move {_where(m.get('box_pct'))}", "start_f": m["start"],
                           "length_f": m["frames"], "fastest_f": m["fastest"],
                           "easing": f"{m['ease']} (measured from a render)"})
            T.save_measured(folder, tracks=tr, tracks_date=datetime.date.today().isoformat())
            shutil.rmtree(dst, ignore_errors=True)
            t["tracks"] = tr
        fps = float(OS.conf(folder)["fps"])
        rows = t.get("tracks") or []
        if ids or measure:
            src = "hand-written" if own else ("measured" if rows else "none yet (--measure)")
            print(f"{tid}: {len(rows)} tracks ({src})")
            if ids:
                for i, x in enumerate(rows, 1):
                    print(f"  {i}. {x.get('name', ''):22s} f{x['start_f']} ({frame_to_tc(x['start_f'], fps)}) "
                          f"+{x['length_f']} f  {x.get('what', '')[:70]}")
    if not ids and not measure:
        n = sum(1 for t in lib.values() if t.get("tracks"))
        print(f"{n} of {len(lib)} templates have tracks; the rest: templates.py tracks --measure")
    if measure:
        T.write_index()
    return 1 if bad else 0


def _where(box: list | None) -> str:
    """A measured move's box (% of the frame) in words."""
    if not box:
        return "somewhere small"
    x0, y0, x1, y1 = box
    if (x1 - x0) * (y1 - y0) > 6400:
        return "across the frame"
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return ("at the " + ("top" if cy < 34 else "bottom" if cy > 66 else "middle")
            + ("" if 34 <= cx <= 66 else " left" if cx < 34 else " right"))


def sizes(ids: list[str], want: list[str], force: bool) -> int:
    """0.5.3 (A3): every template at other sizes (default 1080x1920 and 1080x1080), no render: the text-fit check
    at its check frames against the same check at its own size (a flag that is new at the size = not ok) and the ink
    of its thumb frame (under 40 % of its own size's, by area = it drew much less: a word missing) -> measured.json
    "sizes"; sizes_ok / sizes_bad reach the index and `library --brief`. The bad ones keep their copy in
    .app\\dev\\motion\\<id>_<size> for a look (templates.py check <id> --size <size>). The PC in bulk (overnight
    for all ~190)."""
    import datetime
    import shutil
    import numpy as np
    import overlay as OVL
    lib = {t["id"]: t for t in T.library()}
    today = datetime.date.today().isoformat()
    bad = 0

    def ink(a: np.ndarray) -> float:
        """The share of the frame drawn: opaque pixels on a see-through graphic, else pixels away from the border's
        colour (a graphic that paints its own background)."""
        if a[..., 3].mean() < 250:
            return float((a[..., 3] > 32).mean())
        rgb = a[..., :3].astype(np.int16)
        edge = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
        return float((np.abs(rgb - np.median(edge, axis=0)).max(axis=2) > 40).mean())

    for tid in ids or sorted(lib):
        t = lib.get(tid)
        if not t:
            print(f"{tid}: not in the library")
            bad += 1
            continue
        folder = LAB / t["folder"]
        done = T.measured(folder).get("sizes", {})
        todo = [s for s in want if force or s not in done]
        if not todo:
            continue
        base = _copy(tid, suffix="_native")
        if isinstance(base, str):
            print(f"{tid}: copy failed\n{base[-600:]}")
            bad += 1
            continue
        try:
            fr = OVL.parse_frames(_check_frames(t, base))
            own_flags = {(f["selector"], f["code"]) for f in OVL.fit_check(base, fr, base / ".work")}
            tf = min(int(t.get("thumb_f") or fr[len(fr) // 2]), int(OVL.read_conf(base)["frames"]) - 1)
            own_ink = ink(OVL.snapshots(base, [tf], base / ".work")[0][0])
        except SystemExit as e:
            print(f"{tid}: {e}")
            bad += 1
            continue
        finally:
            shutil.rmtree(base, ignore_errors=True)
        for size in todo:
            dst = _copy(tid, size)
            if isinstance(dst, str):
                done[size] = {"ok": False, "flags": ["the copy at this size failed"], "date": today}
                continue
            try:
                frs = OVL.parse_frames(_check_frames(t, dst))
                flags = [f["line"] for f in OVL.fit_check(dst, frs, dst / ".work")
                         if (f["selector"], f["code"]) not in own_flags]
                c = OVL.read_conf(dst)
                k = float(c["fps"]) / float(OS.conf(folder)["fps"])
                got = ink(OVL.snapshots(dst, [min(round(tf * k), int(c["frames"]) - 1)], dst / ".work")[0][0])
                if own_ink > 0.002 and got < 0.4 * own_ink:
                    flags.append(f"draws {round(100 * got / own_ink)} % of the ink it draws at its own size "
                                 f"(f{tf}) - something is missing or tiny")
            except SystemExit as e:
                flags = [f"the check failed: {e}"]
            finally:
                shutil.rmtree(dst / ".work", ignore_errors=True)
            done[size] = {"ok": not flags, "flags": flags, "date": today}
            if not flags:
                shutil.rmtree(dst, ignore_errors=True)
            print(f"{tid} at {size}: " + ("ok" if not flags else "NOT ok - " + "; ".join(flags)[:300]))
        T.save_measured(folder, sizes=done)
    T.write_index()
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
