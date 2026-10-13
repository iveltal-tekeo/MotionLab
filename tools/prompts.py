"""The prompt library (0.4): proven prompts for video models (shots), image models (stills / start frames), hooks
and talking scripts, split into their structure, so `/write-prompt` can write new ones in a structure that worked.
Text only - no model, no API, no cost.

    .venv\\Scripts\\python tools\\prompts.py list [shot|image|hook|script]
    .venv\\Scripts\\python tools\\prompts.py show <id>                    e.g. shot-001
    .venv\\Scripts\\python tools\\prompts.py import <file>                any text (one prompt; --- lines separate several;
                                                                       `template` = the older format) or a JSON list
    .venv\\Scripts\\python tools\\prompts.py annotate <id> <file.json>    Claude's split: {title, structure, pattern, tags,
                                                                       model, review, workflow, step, notes}
    .venv\\Scripts\\python tools\\prompts.py kind <id> <kind>              a wrong (guessed) kind -> the right one (new id)
    .venv\\Scripts\\python tools\\prompts.py style <id> [<reference> ...] [--clear]   the style of analysed references
                                                                       (no names: what is linked + suggested)
    .venv\\Scripts\\python tools\\prompts.py rate <id> good|ok|bad|none [--note "..."]     the user's result
    .venv\\Scripts\\python tools\\prompts.py template                     print the paste format

Writes only knowledge\\local\\prompts\\<kind>\\<id>.json (private to this PC). A JSON import = a list of records
{kind, text, source: {type: tested|creator|written, creator?, link?, file?}, title?, model?, result?, structure?,
pattern?, tags?, made_from?, review?: {stars 0-5, why, fix}, workflow?, step?, notes?} - how Claude saves the prompts
it wrote (`written`, made_from = the examples used) or collected ones the user handed over (`creator`). Two ratings,
never mixed: `review` = Claude's reading of the text (will a model do what it asks?), `result` = what the user saw.
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
    a = sub.add_parser("annotate", help="set title / structure / pattern / tags / model / review / workflow / step / "
                                        "notes from a JSON file")
    a.add_argument("id")
    a.add_argument("file")
    r = sub.add_parser("rate", help="how the result turned out")
    r.add_argument("id")
    r.add_argument("rating", choices=[*P.RATINGS, "none"])
    r.add_argument("--note")
    k = sub.add_parser("kind", help="move a prompt saved under the wrong kind (it gets a new id)")
    k.add_argument("id")
    k.add_argument("kind", choices=list(P.KINDS))
    st = sub.add_parser("style", help="link analysed references as the prompt's style (no names: show linked + "
                                      "suggested)")
    st.add_argument("id")
    st.add_argument("names", nargs="*", help="analysis folder names (References)")
    st.add_argument("--clear", action="store_true", help="unlink every style reference")
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
        keys = ("title", "structure", "pattern", "tags", "model", "review", "workflow", "step", "notes")
        print(P.describe(P.update(args.id, **{k: ch.get(k) for k in keys}), full=True))
    elif args.cmd == "rate":
        print(P.describe(P.update(args.id, rating=None if args.rating == "none" else args.rating, note=args.note)))
    elif args.cmd == "kind":
        r = P.set_kind(args.id, args.kind)
        print(f"{args.id} -> {r['id']}")
        print(P.describe(r, full=True))
    elif args.cmd == "style":
        r = P.set_style(args.id, []) if args.clear else P.set_style(args.id, args.names) if args.names else P.get(args.id)
        print(f"{r['id']} style from: {', '.join(r.get('style_refs') or []) or 'nothing linked'}")
        print("\n".join(P.style_text(r)) or "  no analysed reference matches its words (References > analyse one)")
    elif args.cmd == "template":
        print(P.TEMPLATE)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
