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
    .venv\\Scripts\\python tools\\templates.py library                  the rebuilt templates (id, kind, size, settings)
    .venv\\Scripts\\python tools\\templates.py pick "<the user's words>" [--n 6] [--kinds text,overlays]
          the library templates that fit the words best (Generate starting blind) - one line each, best first
    .venv\\Scripts\\python tools\\templates.py todo <pack>              the clips not rebuilt yet, by Claude's rebuild
          priority (cards.json "rebuild" 1 first), with their sheet
    .venv\\Scripts\\python tools\\templates.py selfcheck                a synthetic clip with known moves (temp folder)

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
    sub.add_parser("library")
    s = sub.add_parser("pick")
    s.add_argument("want")
    s.add_argument("--n", type=int, default=6)
    s.add_argument("--kinds")
    s = sub.add_parser("todo")
    s.add_argument("pack")
    s = sub.add_parser("check")
    s.add_argument("ids", nargs="*")
    s.add_argument("--frames")
    s.add_argument("--size", help="e.g. 1920x1080@25: the template retimed to another size first (a fit test)")
    s.add_argument("--values", help='settings to try, JSON: {"look": "pastel"} (the picture is kept)')
    sub.add_parser("selfcheck")
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
            decl = OS.declared(LAB / t["folder"])
            print(f"  {t.get('kind', ''):10s} {t['id']:24s} {c['frames']:4d} f {float(c['fps']):g} fps "
                  f"{c['width']}x{c['height']}  {t.get('name', '')} - settings: {', '.join(d['id'] for d in decl)}")
        return 0
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
    return 2


def check(ids: list[str], frames: str | None, size: str | None, values: str | None = None) -> int:
    """Each template copied into .app\\dev\\motion\\<id> (scratch) and snapped at its check frames (template.json
    "check_frames") - no render; the sheet path is printed; the thumb_f snapshot becomes the template's thumb.png."""
    import re
    import shutil
    import subprocess
    from PIL import Image
    lib = {t["id"]: t for t in T.library()}
    ids = ids or sorted(lib)
    py, ov = sys.executable, str(LAB / "tools" / "overlay.py")
    bad = 0
    for tid in ids:
        if tid not in lib:
            print(f"{tid}: not in the library")
            bad += 1
            continue
        t = lib[tid]
        import hashlib
        tag = ("_v" + hashlib.sha1(values.encode("utf-8")).hexdigest()[:6]) if values else ""   # one folder per look tried
        dst = LAB / ".app" / "dev" / "motion" / (tid + (f"_{size.replace('@', '_')}" if size else "") + tag)
        shutil.rmtree(dst, ignore_errors=True)
        cmd = [py, ov, "new", str(dst), "--from", tid] + (["--values", values] if values else [])
        if size:
            m = re.fullmatch(r"(\d+)x(\d+)(?:@([\d.]+))?", size)
            if not m:
                raise SystemExit("--size like 1920x1080@25")
            cmd += ["--width", m[1], "--height", m[2]] + (["--fps", m[3]] if m[3] else [])
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode:
            print(f"{tid}: copy failed\n{r.stdout}{r.stderr}")
            bad += 1
            continue
        fr = frames or ",".join(str(f) for f in t.get("check_frames") or [0])
        if size and not frames:                       # the check frames at the new rate
            c = json.loads((dst / "overlay.json").read_text(encoding="utf-8"))
            k = float(c["fps"]) / float(OS.conf(LAB / t["folder"])["fps"])
            fr = ",".join(str(min(int(c["frames"]) - 1, round(int(f) * k))) for f in fr.split(","))
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
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
