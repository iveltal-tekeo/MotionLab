"""The prompt library (0.4): proven prompts for video models (shots), image models (stills / start frames), hooks
and talking scripts, split into their structure, so `/write-prompt` can write new ones in a structure that worked.
Text only - no model, no API, no cost.

    .venv\\Scripts\\python tools\\prompts.py list [brief|shot|image|hook|script|title]
    .venv\\Scripts\\python tools\\prompts.py show <id>                    e.g. shot-001
    .venv\\Scripts\\python tools\\prompts.py import <file> [--set <set>]  any text (one prompt; --- lines separate several;
                                                                       `template` = the older format) or a JSON list;
                                                                       --set = a text set's file sorted into the set
    .venv\\Scripts\\python tools\\prompts.py annotate <id> <file.json>    Claude's check: {title, structure, skipped,
                                                                       overrides, pattern, tags, model, review, workflow,
                                                                       step, notes}
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
A title & thumbnail record (kind `title`, 0.4.3, `/write-title`) has no text of its own: {kind: title, source,
titles: [{text, pattern}], concepts: [{id: A, sketch, words, shot, colours}], hook, chosen?, request? (req-NNN),
project? (the video it packages)} - its text is written from them; `show` prints it readably; `annotate` also takes
titles / concepts / hook / chosen / project.

Checked by the tool, not trusted (2026-10-18, motionlab\\prompts.verify_check): `annotate` and a JSON `import` save
Claude's check only when every quoted part is found in THAT prompt's text (whole words in its order, pieces left out
with ...; the saved quote = the text's own words + `at`, their character positions), every part of the kind is a
row or in `skipped` {part: why it is not part of this prompt}, "missing" quotes nothing, a script part the measured
check flags is not "clear" without `overrides` {part: why}, and quotes in review.why are the text's. A JSON import
with `source.file` must also be in that file (verify_source). Refused = exit 2, nothing saved, every problem listed
with the closest real passage - fix what it names; never re-word a quote to get past it.
"""
from __future__ import annotations

import argparse
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
    im = sub.add_parser("import", help="save prompts from a paste (.txt) or a JSON list")
    im.add_argument("file")
    im.add_argument("--set", help="a text set (Analyser > Scripts & prompts): the saved prompts join it, their file "
                                  "counts as sorted")
    a = sub.add_parser("annotate", help="set title / structure / skipped / pattern / tags / model / review / workflow "
                                        "/ step / notes from a JSON file (Claude's check, verified)")
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
        notes: list[str] = []
        TX = None
        if args.set:                                                 # a text set's file to sort (2026-10-18)
            from motionlab import textsets as TX
            TX.get_set(args.set)                                     # it must exist (FileNotFoundError otherwise)
        if f.suffix.lower() == ".json":
            recs = read_json(f)
            recs = recs if isinstance(recs, list) else [recs]
            ready, problems = [], []
            for i, x in enumerate(recs, 1):                          # check them all before saving any
                if not isinstance(x, dict):
                    raise ValueError(f"record {i}: not a JSON object")
                if TX:                                               # the set's "whose" for what Claude leaves out
                    x["source"] = {**TX.source_of(args.set), **(x.get("source") or {})}
                P._check({"result": {}, **x})
                who = f"record {i} ({x.get('kind')}: {P._snip(x.get('title') or x.get('text') or '', 40)})"
                w: list[str] = []
                clean, pr = P.verify_check({"kind": x.get("kind"), "text": x.get("text") or "",
                                            "source": x.get("source") or {}}, x, warnings=w)
                pr += P.verify_source(x, notes)
                problems += [f"{who}: {p}" for p in pr]
                notes += [f"{who}: {p}" for p in w]
                ready.append(clean)
            if problems:
                raise ValueError("nothing saved - fix these and import again:\n  " + "\n  ".join(problems))
            if TX:
                TX.room(args.set, len(ready))                        # refuses before anything is saved
                saved = [TX.known(x["text"]) or P.add(x) for x in ready]
            else:
                saved = [P.add(x) for x in ready]
        else:
            if TX:
                raise ValueError("--set takes a JSON list (each text copied exactly from its file, with source.file)")
            saved = P.import_paste(f.read_text(encoding="utf-8"))
        print(f"saved {len(saved)} prompt(s):")
        for x in saved:
            print(P.describe(x))
        for x in notes:
            print(f"note: {x}")
        if TX:
            files = sorted({str((x.get("source") or {}).get("file") or "") for x in ready} - {""})
            print(TX.add_records(args.set, [x["id"] for x in saved], files)["line"])
        todo = [x["id"] for x in saved if not x.get("structure")]
        if todo:
            print(f"not split into structure yet: {', '.join(todo)} (annotate)")
    elif args.cmd == "annotate":
        ch = read_json(Path(args.file))
        keys = ("title", "structure", "skipped", "overrides", "pattern", "tags", "model", "review", "workflow", "step",
                "notes", "titles", "concepts", "hook", "chosen", "project")   # the last five: a title record (0.4.3)
        ch = {k: ch[k] for k in keys if ch.get(k) is not None}
        w = []
        clean, problems = P.verify_check(P.get(args.id), ch, warnings=w)     # 2026-10-18: quotes checked by the tool
        if problems:
            raise ValueError(f"nothing saved - {len(problems)} problem(s) in the check of {args.id}:\n  "
                             + "\n  ".join(problems))
        r = P.update(args.id, **clean)
        print(P.describe(r, full=True))
        for x in w:
            print(f"note: {x}")
        from motionlab import textsets as TX
        for line in TX.note_check(r):                                # a text set it belongs to counts it as checked
            print(line)
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
