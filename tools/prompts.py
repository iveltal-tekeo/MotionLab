"""The prompt library (0.4): proven prompts for video models (shots), hooks and talking scripts, split into their
structure, so `/write-prompt` can write new ones in a structure that worked. Text only - no model, no API, no cost.

    .venv\\Scripts\\python tools\\prompts.py list [shot|hook|script]
    .venv\\Scripts\\python tools\\prompts.py show <id>                    e.g. shot-001
    .venv\\Scripts\\python tools\\prompts.py import <file>                the paste format (`template`) or a JSON list
    .venv\\Scripts\\python tools\\prompts.py annotate <id> <file.json>    Claude's split: {title, structure, pattern, tags, model}
    .venv\\Scripts\\python tools\\prompts.py rate <id> good|ok|bad|none [--note "..."]
    .venv\\Scripts\\python tools\\prompts.py template                     print the paste format

Writes only knowledge\\local\\prompts\\<kind>\\<id>.json (private to this PC). A JSON import = a list of records
{kind, text, source: {type: tested|creator|written, creator?, link?}, title?, model?, result?, structure?,
pattern?, tags?, made_from?} - how Claude saves the prompts it wrote (`written`, made_from = the examples used).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import prompts as P  # noqa: E402
from motionlab.util import read_json, setup_console  # noqa: E402


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="every prompt, best examples first").add_argument("kind", nargs="?", default="",
                                                                                  choices=["", *P.KINDS])
    sub.add_parser("show", help="one prompt in full").add_argument("id")
    sub.add_parser("import", help="save prompts from a paste (.txt) or a JSON list").add_argument("file")
    a = sub.add_parser("annotate", help="set title / structure / pattern / tags / model from a JSON file")
    a.add_argument("id")
    a.add_argument("file")
    r = sub.add_parser("rate", help="how the result turned out")
    r.add_argument("id")
    r.add_argument("rating", choices=[*P.RATINGS, "none"])
    r.add_argument("--note")
    sub.add_parser("template", help="print the paste format")
    args = ap.parse_args()

    if args.cmd == "list":
        items = P.load_all(args.kind)
        print(f"{len(items)} prompt(s) in {P.HOME}" + ("" if items else " - add some: prompts.py template"))
        for x in items:
            print(P.describe(x))
    elif args.cmd == "show":
        print(P.describe(P.get(args.id), full=True))
    elif args.cmd == "import":
        f = Path(args.file)
        if f.suffix.lower() == ".json":
            recs = read_json(f)
            recs = recs if isinstance(recs, list) else [recs]
            for x in recs:                                           # check them all before saving any
                P._check({"result": {}, **x})
            saved = [P.add(x) for x in recs]
        else:
            saved = P.import_paste(f.read_text(encoding="utf-8"))
        print(f"saved {len(saved)} prompt(s):")
        for x in saved:
            print(P.describe(x))
        todo = [x["id"] for x in saved if not x.get("structure")]
        if todo:
            print(f"not split into structure yet: {', '.join(todo)} (annotate)")
    elif args.cmd == "annotate":
        ch = read_json(Path(args.file))
        print(P.describe(P.update(args.id, **{k: ch.get(k) for k in ("title", "structure", "pattern", "tags", "model")}),
                         full=True))
    elif args.cmd == "rate":
        print(P.describe(P.update(args.id, rating=None if args.rating == "none" else args.rating, note=args.note)))
    elif args.cmd == "template":
        print(P.TEMPLATE)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
