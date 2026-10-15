"""Publish (0.4.3): the words of a finished video's ready-to-post folder - title, description with YouTube chapters,
hashtags - in projects\\<p>\\build\\publish\\ (the thumbnails: tools\\thumbnail.py, same folder, same package.json).
Text only, no Claude, no account: the user posts it.

    .venv\\Scripts\\python tools\\publish.py chapters <project> [--from plan|transcript] [--speech <file>] [--json]
          candidate chapter points with frame + timecode: the newest edit plan's picture changes (plan), or pauses
          and topic shifts in the video's words (transcript: build\\speech\\ from speech.py, a transcript of the
          final render first). Each with its strength and a hint of what starts there; "suggested" = a set that
          keeps YouTube's rules. Claude picks and names them.
    .venv\\Scripts\\python tools\\publish.py write <project> --title "..." [--chapters "f|name;f|name;..."]
          [--hashtags "#a #b"] [--description-file <txt>] [--titles title-NNN]
          -> build\\publish\\title.txt, description.txt (the words + chapters as `0:00 Name` + hashtags),
          hashtags.txt + package.json (only its own keys). f = a frame of the final video (0-based). Checked first:
          YouTube's chapter rules (0:00 first, at least 3, each >= 10 s), hashtags (more than 60 = all ignored; the
          first 3 show by the title), title <= 100 and description <= 5000 characters; on a FAIL nothing is
          written (exit 1). Left out = kept from the last write. --titles = a title record's titles into
          package.json.
    .venv\\Scripts\\python tools\\publish.py show <project>
    .venv\\Scripts\\python tools\\publish.py selfcheck

<project> = a name in projects\\ (projects\\test_4am works too). Writes only build\\publish\\ - never the footage.
The rules and the date they were checked: tools\\motionlab\\publish.py.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import publish as PB  # noqa: E402
from motionlab.util import setup_console  # noqa: E402


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("chapters", help="candidate chapter points with frame + timecode")
    c.add_argument("project")
    c.add_argument("--from", dest="src", choices=["plan", "transcript"], default="plan")
    c.add_argument("--speech", help="a speech.py transcript (.json) instead of the newest in build\\speech")
    c.add_argument("--json", action="store_true")
    w = sub.add_parser("write", help="title.txt, description.txt, hashtags.txt + package.json")
    w.add_argument("project")
    w.add_argument("--title", required=True)
    w.add_argument("--chapters", help='"f|name;f|name;..." - frames of the final video')
    w.add_argument("--hashtags", help='"#a #b #c"')
    w.add_argument("--description-file", help="a .txt with the description's own words (chapters + hashtags are added)")
    w.add_argument("--titles", default="", help="a title record (title-NNN): its titles go into package.json")
    s = sub.add_parser("show", help="what the publish folder holds")
    s.add_argument("project")
    sub.add_parser("selfcheck", help="known answers for the rules and the package.json merge")
    a = ap.parse_args()

    if a.cmd == "selfcheck":
        r = PB.selfcheck()
        print("\n".join(r["lines"]))
        print(f"{'PASS' if r['passed'] else 'FAIL'} publish selfcheck ({r['seconds']} s)")
        return 0 if r["passed"] else 1
    if a.cmd == "chapters":
        r = PB.chapter_points(a.project, a.src, a.speech)
        if a.json:
            print(json.dumps(r, ensure_ascii=False, indent=1))
            return 0
        print(f"chapter points from {r['from']} ({r['fps']:g} fps, {r['frames']} frames = {r['seconds']:g} s)")
        for x in r["warnings"]:
            print(f"  note: {x}")
        for p in r["points"]:
            mark = "*" if p["f"] in r["suggested"] else " "
            print(f" {mark} f{p['f']} ({p['tc']})  YouTube {p['yt']:>5}  strength {p['strength']:.2f}  "
                  f"{p['until_next_s']:5.1f} s to the next" + (f"  | {p['hint']}" if p.get("hint") else ""))
        print("* suggested (keeps YouTube's rules): " + ";".join(f"{f}|<name>" for f in r["suggested"]))
        return 0
    if a.cmd == "write":
        body = Path(a.description_file).read_text(encoding="utf-8-sig") if a.description_file else None
        r = PB.write(a.project, a.title, a.chapters, a.hashtags, body, a.titles)
        print(PB.checks_text(r["checks"]))
        if not r["ok"]:
            print("FAIL - nothing written; fix the lines marked FAIL", file=sys.stderr)
            return 1
        print("wrote:\n" + "\n".join(f"  {f}" for f in r["files"]))
        print("description.txt:\n" + "\n".join("  | " + x for x in r["description"].rstrip("\n").split("\n")))
        return 0
    print(PB.show(a.project))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
