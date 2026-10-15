"""Thumbnail sets (0.4.5): many thumbnails without their videos - a channel (listed whole, taken in batches), single video links or your own
pictures - measured together so their common patterns show (colours, light, faces, where the text sits); Claude names
the rest (the font's style, the structure, the emotion) from the sheets into the set's style.json. No Claude and no
video here; the logic is tools\\motionlab\\thumbsets.py.

    .venv\\Scripts\\python tools\\thumbsets.py fetch <set> <channel | playlist | channel tab link> [--n 15] [--order newest|views] [--label "..."]
          EVERY video of the channel / playlist listed (seconds: 246 in 3.5 s, 804 in 10.3 s - no video downloaded)
          and kept in set.json; the first n - the newest or the most viewed - get their thumbnails, titles, views and
          the channel's followers into the set, measured, numbered sheets. A bare YouTube channel link = its Videos tab
    .venv\\Scripts\\python tools\\thumbsets.py more <set> [--n 20] [--order newest|views] [--refresh]
          the next n of that channel that are not in the set yet (its listing asked for again when older than a day)
    .venv\\Scripts\\python tools\\thumbsets.py refresh <set>
          the channel listed again: the set's pictures get the newest views, their (approximate) dates and lengths
    .venv\\Scripts\\python tools\\thumbsets.py links <set> <video link> [<video link> ...]
          single videos' thumbnail + title, views, followers, added to the set
    .venv\\Scripts\\python tools\\thumbsets.py add <set> <picture | folder> [...] [--label "..."]
          your own pictures (.jpg .jpeg .png .webp; a folder = the pictures in it) COPIED in - the originals are only
          read; title = the file's name
    .venv\\Scripts\\python tools\\thumbsets.py measure <set> [--force]
          every picture: brightness, saturation, colourfulness, contrast, its 4 main colours, faces (how many, how big,
          which side; "not measured" without the face model), the text (an estimate: letter size, where it sits, how
          much it covers) - re-used while a picture is unchanged; then the set's summary (views / followers weighted
          first), the faces / text counts, the usual positions, the set's main colours, the best 3
    .venv\\Scripts\\python tools\\thumbsets.py sheet <set>          the contact sheets again (15 per sheet: "#n", views,
          views / followers and the title under each picture)
    .venv\\Scripts\\python tools\\thumbsets.py list                 the sets: pictures, measured, style, last change
    .venv\\Scripts\\python tools\\thumbsets.py show <set> [--json]  the summary in words + one line per picture
    .venv\\Scripts\\python tools\\thumbsets.py remove-item <set> <n>  drop picture #n (the later ones move up a number)
    .venv\\Scripts\\python tools\\thumbsets.py selfcheck            synthetic pictures with known answers (no network,
          a temp folder, a few seconds)

<set> = a short name, e.g. mrbeast (letters, digits, _ - . are kept). --root <folder> (or MOTIONLAB_THUMBS_ROOT) keeps
the sets somewhere else (tests). style.json in a set is Claude's (/write-title), never written here. Other people's
thumbnails stay on this PC: nothing is shared from here. yt-dlp is the one the app uses (Settings > Programs).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import thumbsets as TS  # noqa: E402
from motionlab.util import setup_console  # noqa: E402


def _show(name: str) -> None:
    S = TS.get_set(name)
    for line in TS.summary_lines(name):
        print(line)
    for it in S["items"]:
        print("  " + TS.item_line(it))
    for s in S["sheets"]:
        print(f"sheet: {s}")


def main() -> int:
    setup_console()
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0 if len(sys.argv) >= 2 else 2
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", help="the folder that holds the sets (default analysis\\thumbs)")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", parents=[common])
    f.add_argument("set")
    f.add_argument("url")
    f.add_argument("--n", type=int, default=15)
    f.add_argument("--order", choices=("newest", "views"), default="newest")
    f.add_argument("--label")
    mo = sub.add_parser("more", parents=[common])
    mo.add_argument("set")
    mo.add_argument("--n", type=int, default=20)
    mo.add_argument("--order", choices=("newest", "views"), default="newest")
    mo.add_argument("--refresh", action="store_true")
    rf = sub.add_parser("refresh", parents=[common])
    rf.add_argument("set")
    k = sub.add_parser("links", parents=[common])
    k.add_argument("set")
    k.add_argument("urls", nargs="+")
    k.add_argument("--label")
    a_ = sub.add_parser("add", parents=[common])
    a_.add_argument("set")
    a_.add_argument("paths", nargs="+")
    a_.add_argument("--label")
    m = sub.add_parser("measure", parents=[common])
    m.add_argument("set")
    m.add_argument("--force", action="store_true")
    s = sub.add_parser("sheet", parents=[common])
    s.add_argument("set")
    sub.add_parser("list", parents=[common])
    w = sub.add_parser("show", parents=[common])
    w.add_argument("set")
    w.add_argument("--json", action="store_true")
    r = sub.add_parser("remove-item", parents=[common])
    r.add_argument("set")
    r.add_argument("n", type=int)
    sub.add_parser("selfcheck")
    a = ap.parse_args()
    if getattr(a, "root", None):
        TS.ROOT = Path(a.root).resolve()

    try:
        if a.cmd in ("fetch", "links", "add", "more"):
            if a.cmd == "fetch":
                res = TS.fetch(a.set, a.url, a.n, a.label, log=lambda x: print(x, flush=True), order=a.order)
            elif a.cmd == "more":
                res = TS.more(a.set, a.n, a.order, a.refresh, log=lambda x: print(x, flush=True))
            elif a.cmd == "links":
                res = TS.add_links(a.set, a.urls, log=lambda x: print(x, flush=True), label=a.label)
            else:
                res = TS.add_files(a.set, a.paths, log=lambda x: print(x, flush=True), label=a.label)
            print(TS.set_dir(a.set))
            return 0 if res["added"] or not res["failed"] else 1
        if a.cmd == "refresh":
            TS.refresh(a.set, log=lambda x: print(x, flush=True))
            return 0
        if a.cmd == "measure":
            res = TS.measure(a.set, a.force)
            print(f"measured {res['measured']}, re-used {res['reused']} in {res['seconds']} s"
                  + "".join(f"\n  #{n}: {why}" for n, why in res["failed"]))
            for line in TS.summary_lines(a.set):
                print(line)
            return 1 if res["failed"] else 0
        if a.cmd == "sheet":
            for p in TS.make_sheets(a.set):
                print(p)
            return 0
        if a.cmd == "list":
            rows = TS.list_sets()
            if not rows:
                print(f"no thumbnail sets yet in {TS.ROOT} (thumbsets.py fetch <set> <channel link>)")
            for x in rows:
                print(f"{x['name']:24s} {x['label'][:30]:30s} {x['count']:3d} pictures, {x['measured']:3d} measured, "
                      f"style {'yes' if x['has_style'] else 'no '}  {x['updated'] or ''}")
            return 0
        if a.cmd == "show":
            if a.json:
                print(json.dumps(TS.get_set(a.set), indent=1, ensure_ascii=False))
            else:
                _show(a.set)
            return 0
        if a.cmd == "remove-item":
            res = TS.remove_item(a.set, a.n)
            print(f"#{res['removed']} removed, {res['count']} picture(s) left")
            return 0
        if a.cmd == "selfcheck":
            res = TS.selfcheck(verbose=True)
            print(f"{'PASS' if res['passed'] else 'FAIL'} thumbsets selfcheck in {res['seconds']} s")
            return 0 if res["passed"] else 1
    except (ValueError, FileNotFoundError) as e:
        print(f"error: {e}")
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
