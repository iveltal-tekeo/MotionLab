"""Thumbnails (0.4.3): the 16:9 YouTube thumbnail and the 9:16 cover from your own frames, and the check that tells
whether they read at feed size. No Claude, no render (HTML templates as stills); the logic is
tools\\motionlab\\thumbnail.py.

    .venv\\Scripts\\python tools\\thumbnail.py candidates <project | video file> [--n 12] [--render] [--threads 4]
          frames worth a thumbnail (sharp, still, well lit, not a cut, spread out; a big face when the face detector
          is there) from the project's clips (--render: its newest render) -> build\\publish\\candidates\\ (a PNG per
          frame) + candidates.png (the sheet: clip, frame + timecode per tile) + package.json "candidates"
    .venv\\Scripts\\python tools\\thumbnail.py make <project> --id A (--frame <f> [--clip <id>] | --image <file>)
          --words "TWO TO FOUR" [--template outline|block|split] [--set key=value ...]
          [--frame2 <f> [--clip2 <id>] | --image2 <file>]      (the split template's "after" picture)
          -> build\\publish\\thumb_A_16x9.png (1280x720) + thumb_A_9x16.png (1080x1920) + thumb_A_9x16_crops.png (the
          cover with the platforms' grid crops and buttons drawn on it) + thumbs\\A\\ (the editable graphic: index.html
          + overlay.json "values"; overlay.py settings / set work on it) + package.json "thumbnails"; --frame is the
          clip's own frame number (0-based, at its own rate; candidates.png shows them), --clip a source id (A, B ...),
          a file name or "render"; --image = a picture (an AI image tool's) instead of a frame
    .venv\\Scripts\\python tools\\thumbnail.py render <project> --id A     the PNGs again after overlay.py set
    .venv\\Scripts\\python tools\\thumbnail.py check <image | project> [--title "..."] [--script <script-004 | file |
          text>] [--niche <category or tag>] [--words "..."] [--id A] [--json]
          a PASS / WARN / FAIL (or SKIP) line per rule with its number: readability at feed size, 2-4 words, text
          size, contrast (WCAG), the face's share, brightness / saturation vs the niche's outperformers, the apps'
          crops and buttons, file size, the title's length, the thumbnail repeating the title, the title's promise in
          the script's first 3 s. A project = every thumbnail in package.json (both sizes; the title defaults to
          package.json "title"), results saved there. Exit 1 when a rule FAILs
    .venv\\Scripts\\python tools\\thumbnail.py refs [--niche <category or tag>]
          the analysed references' thumbnails (content.py saves them) measured; a summary per niche, outperformers
          (views / followers) weighted first
    .venv\\Scripts\\python tools\\thumbnail.py templates        the designs and their settings
    .venv\\Scripts\\python tools\\thumbnail.py platforms        the sizes and crops used, with the date they were checked
    .venv\\Scripts\\python tools\\thumbnail.py selfcheck        synthetic cases with known answers (no video)

Every frame is named with its frame number and timecode, e.g. B f452 (00:00:09:02). The face detector is OpenCV's
YuNet; it needs its 227 KB model file (tools\\models\\face_detection_yunet_2023mar.onnx, or MOTIONLAB_FACE_MODEL);
without it the face parts are skipped and said so. Writes only build\\publish\\ (sources are only read).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import thumbnail as T  # noqa: E402
from motionlab.util import setup_console  # noqa: E402


def _vals(pairs: list[str]) -> dict:
    out = {}
    for kv in pairs or []:
        k, sep, v = kv.partition("=")
        if not sep:
            raise SystemExit(f"'{kv}': use key=value (thumbnail.py templates lists the keys)")
        out[k.strip()] = v
    return out


def _print_check(name: str, lines: list[dict], res: str) -> None:
    print(f"{name}: {res}")
    for x in lines:
        print(f"  {x['status']:4s} {x['rule']:13s} {x['text']}")


def main() -> int:
    setup_console()
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("candidates")
    c.add_argument("target")
    c.add_argument("--n", type=int, default=12)
    c.add_argument("--render", action="store_true", help="the project's newest render instead of its clips")
    c.add_argument("--threads", type=int, default=T.THREADS)
    m = sub.add_parser("make")
    m.add_argument("project")
    m.add_argument("--id", required=True)
    m.add_argument("--frame", type=int)
    m.add_argument("--clip")
    m.add_argument("--image")
    m.add_argument("--frame2", type=int)
    m.add_argument("--clip2")
    m.add_argument("--image2")
    m.add_argument("--words", required=True)
    m.add_argument("--template", default="outline")
    m.add_argument("--set", nargs="*", default=[], dest="values")
    m.add_argument("--no-check", action="store_true")
    r = sub.add_parser("render")
    r.add_argument("project")
    r.add_argument("--id", required=True)
    k = sub.add_parser("check")
    k.add_argument("target")
    k.add_argument("--title")
    k.add_argument("--script")
    k.add_argument("--niche")
    k.add_argument("--words")
    k.add_argument("--id", action="append")
    k.add_argument("--json", action="store_true")
    f = sub.add_parser("refs")
    f.add_argument("--niche")
    f.add_argument("--json", action="store_true")
    sub.add_parser("templates")
    sub.add_parser("platforms")
    sub.add_parser("selfcheck")
    a = ap.parse_args()

    if a.cmd == "candidates":
        e = T.candidates(a.target, a.n, a.render, a.threads)
        for it in e["items"]:
            face = "" if it["face"] is None else f"  face {round(it['face'] * 100)} %"
            print(f"  {it['id']}  {it['clip']} f{it['frame']} ({it['tc']})  score {it['score']:.2f}  sharp "
                  f"{it['sharp']:.0f}  motion {it['motion']:.1f}  light {it['luma']:.0f} %{face}")
        s = e["seconds"]
        print(f"{len(e['items'])} candidates in {s['total']} s (looked at {s['decoded']} frames: {s['look']} s; saved "
              f"in {s['save']} s); face detector: {'on' if e['face_detector'] else 'off (no model file)'}")
        print(T.LAB / e["sheet"])
        return 0
    if a.cmd == "make":
        if (a.frame is None) == (a.image is None):
            raise SystemExit("give --frame <f> (with --clip) or --image <file>")
        e = T.make(a.project, a.id, a.words, a.template, a.frame, a.clip, a.image, a.frame2, a.clip2, a.image2,
                   _vals(a.values))
        for k_, v in e["files"].items():
            print(f"  {k_:11s} {T.LAB / v}")
        print("  seconds: " + ", ".join(f"{k_} {v}" for k_, v in e["seconds"].items()))
        if not a.no_check:
            res = T.check_project(a.project, ids=[a.id])
            for size in T.SIZES:
                _print_check(f"{a.id} {size}", res[a.id][size], T.overall(res[a.id][size]))
        return 0
    if a.cmd == "render":
        e = T.render(a.project, a.id)
        for k_, v in e["files"].items():
            print(f"  {k_:11s} {T.LAB / v}")
        return 0
    if a.cmd == "check":
        p = Path(a.target)
        if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp") and p.is_file():
            res = T.check_image(str(p), a.title, a.script, a.niche, a.words)
            if a.json:
                print(json.dumps(res, indent=1, ensure_ascii=False))
            else:
                _print_check(f"{p.name} ({res['size']})", res["lines"], res["result"])
            return 1 if res["result"] == "FAIL" else 0
        res = T.check_project(a.target, a.title, a.script, a.niche, a.id)
        if a.json:
            print(json.dumps(res, indent=1, ensure_ascii=False))
        else:
            for tid, r_ in res.items():
                for size in T.SIZES:
                    _print_check(f"{tid} {size}", r_[size], T.overall(r_[size]))
        return 1 if any(r_["result"] == "FAIL" for r_ in res.values()) else 0
    if a.cmd == "refs":
        R = T.refs(a.niche)
        if a.json:
            print(json.dumps(R, indent=1, ensure_ascii=False))
            return 0
        if not R["references"]:
            print("no analysed reference has a thumbnail yet: content.py thumbnail <name>")
            return 0
        for r_ in sorted(R["references"], key=lambda x: -(x["outperformer"] or 0)):
            face = "-" if r_["faces"] is None else f"{r_['faces']} face(s)" + (
                f", {round(r_['face_share'] * 100)} % of the height" if r_["face_share"] else "")
            print(f"  {r_['title'][:48]:48s} {r_['category']:15s} {r_['size'][0]}x{r_['size'][1]}  "
                  f"{'%sx followers' % r_['outperformer'] if r_['outperformer'] else 'views/followers unknown'}")
            print(f"      brightness {r_['brightness']:.0f}  saturation {r_['saturation']:.0f} %  colourfulness "
                  f"{r_['colourfulness']:.0f}  contrast {r_['contrast']:.0f}  {face}  colours "
                  f"{' '.join(c for c, _ in r_['palette'])}")
        print("per niche (outperformers weighted first):")
        for line in T.packaging_lines() if not a.niche else []:
            print("  " + line)
        if a.niche and a.niche in R["niches"]:
            s = R["niches"][a.niche]
            print(f"  {s['label']}: brightness {s['brightness']:.0f}, saturation {s['saturation']:.0f} %, "
                  f"colourfulness {s['colourfulness']:.0f}, contrast {s['contrast']:.0f}")
        return 0
    if a.cmd == "templates":
        for t in T.templates():
            print(f"{t['name']}: {t['what']}")
            for d in t["settings"]:
                extra = f" (one of {', '.join(str(o['value']) for o in d['options'])})" if d["type"] == "enum" else ""
                print(f"    {d['id']:14s} {d['type']:7s} {d.get('label', ''):42s} default {d.get('default')!r}{extra}")
        return 0
    if a.cmd == "platforms":
        for k_, v in T.PLATFORMS.items():
            print(f"{k_}: {v}")
        print("crops drawn on the 9:16 cover: " + "; ".join(f"{n} {w}x{h} at y {y}" for n, (x, y, w, h), _ in T.CROPS))
        print("rules: ")
        for k_, v in T.RULES.items():
            print(f"  {k_}: {v}")
        return 0
    if a.cmd == "selfcheck":
        r_ = T.selfcheck(verbose=True)
        print(f"{'PASS' if r_['passed'] else 'FAIL'} thumbnail selfcheck in {r_['seconds']} s")
        return 0 if r_["passed"] else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
