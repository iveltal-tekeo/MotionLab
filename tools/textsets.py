"""Text sets (2026-10-18, the Analyser's *Scripts & prompts*): up to 20 talking scripts, hooks, prompts for AI video /
image tools and briefs checked together - MotionLab numbers and measures them (no Claude), Claude checks ONE text at a
time and this tool saves a check only when every quote is found in THAT text. The texts live in the prompt library
(knowledge\\local\\prompts\\); the set is analysis\\texts\\<set>\\. The logic is tools\\motionlab\\textsets.py.

    .venv\\Scripts\\python tools\\textsets.py new <set> [--paste <file>] [--files <file> ...] [--kind <kind>]
          [--source tested|creator|found] [--creator "<name>"] [--link <url>] [--label "..."]
          a new set: the paste split on lines of only --- (or PROMPT n blocks), each file one text unless it has ---
          lines (.txt .md .docx; a PDF when the PDF reader is installed - else Claude sorts it in); each text saved word
          for word in the prompt library (one the library has already is re-used), numbered #1..#N, measured
    .venv\\Scripts\\python tools\\textsets.py add <set> [--paste <file>] [--files ...] [--kind <kind>]      more texts
    .venv\\Scripts\\python tools\\textsets.py list                     the sets: texts, checked by Claude, patterns
    .venv\\Scripts\\python tools\\textsets.py show <set> [<n>] [--json]
          the set in lines + one line per text; with <n>: ONE text for Claude - its prompt id, kind and why, sha1, what
          MotionLab measured (evidence), the parts of its kind, the script check, Claude's check so far + the user's
          verdicts on it, the text with line numbers, and the draft to write
    .venv\\Scripts\\python tools\\textsets.py state <set>              what is left: checked k of N, left, stale (checked as
          another kind), disputed (the user marked parts wrong / partly), files to sort, patterns none / ok / stale
    .venv\\Scripts\\python tools\\textsets.py check <set> <n|prompt id> <draft.json>
          Claude's check of #n -> its prompt record, ONLY when it holds (prompts.verify_check: every quote found in #n's
          text, every part a row or "skipped" with why, "missing" quotes nothing, a part the script check flags is not
          "clear" without "overrides"); the draft's "sha1" must be #n's (show prints it). Refused = exit 2, nothing
          saved, every problem with the closest real passage. A draft inside the set's claude\\ folder is deleted once
          saved
    .venv\\Scripts\\python tools\\textsets.py kind <set> <n> <kind> --why "..."   #n is another kind (a new prompt id)
    .venv\\Scripts\\python tools\\textsets.py patterns <set> <draft.json>
          what they have in common -> patterns.json: {"summary", "patterns": [{"id": "P1", "kind": hook|structure|
          wording|camera|look|length|cta|voice|format|other, "what": "<words, no counts>", "examples": [{"n": 2,
          "quote": "<#2's own words>"}], "except": [n], "measure": "<fact>=<value>" (optional)}]} - every quote found in
          its own text, 2+ different texts (twins once); "how_many" is counted here, never typed
    .venv\\Scripts\\python tools\\textsets.py remove-item <set> <n>    #n out of the set (it stays in the prompt library;
          nothing is renumbered)
    .venv\\Scripts\\python tools\\textsets.py selfcheck                known answers in temp folders (a few seconds)

<set> = a short name (letters, digits, _ - . are kept). --root <folder> (or MOTIONLAB_TEXTS_ROOT) keeps the sets
somewhere else (tests). Kinds: shot (a video prompt), image, hook, script (talking), brief. Other people's texts stay
on this PC.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import prompts as PR  # noqa: E402
from motionlab import textsets as TX  # noqa: E402
from motionlab.util import read_json, setup_console  # noqa: E402


def _inputs(a) -> tuple[str, list[str], dict, dict]:
    """--paste / --files / --kind / --source -> (text, attached file names, kinds by sha, source)."""
    text = Path(a.paste).read_text(encoding="utf-8-sig") if getattr(a, "paste", None) else ""
    names = []
    for f in getattr(a, "files", None) or []:                # copied in like the app's attachments (the file stays)
        p = Path(f)
        names.append(PR.save_file(p.name, p.read_bytes())["file"])
    src = None
    if getattr(a, "source", None):
        src = {"type": a.source, "creator": a.creator or "", "link": a.link or ""}
    kinds = {}
    if getattr(a, "kind", None):
        kinds = {x["sha"]: a.kind for x in TX.split(text, names, source=src)["items"]}
    return text, names, kinds, src


def main() -> int:
    setup_console()
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0 if len(sys.argv) >= 2 else 2
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", help="the folder that holds the sets (default analysis\\texts)")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for cmd in ("new", "add"):
        x = sub.add_parser(cmd, parents=[common])
        x.add_argument("set")
        x.add_argument("--paste", help="a text file with the paste (--- lines between the texts)")
        x.add_argument("--files", nargs="+")
        x.add_argument("--kind", choices=list(TX.KINDS))
        x.add_argument("--source", choices=("tested", "creator", "found"))
        x.add_argument("--creator")
        x.add_argument("--link")
        x.add_argument("--tags", default="")
        if cmd == "new":
            x.add_argument("--label")
    sub.add_parser("list", parents=[common])
    s = sub.add_parser("show", parents=[common])
    s.add_argument("set")
    s.add_argument("n", nargs="?")
    s.add_argument("--json", action="store_true")
    st = sub.add_parser("state", parents=[common])
    st.add_argument("set")
    c = sub.add_parser("check", parents=[common])
    c.add_argument("set")
    c.add_argument("ref", help="the text's number (3) or its prompt id (shot-024)")
    c.add_argument("file")
    k = sub.add_parser("kind", parents=[common])
    k.add_argument("set")
    k.add_argument("n")
    k.add_argument("kind", choices=list(TX.KINDS))
    k.add_argument("--why", default="")
    p = sub.add_parser("patterns", parents=[common])
    p.add_argument("set")
    p.add_argument("file")
    r = sub.add_parser("remove-item", parents=[common])
    r.add_argument("set")
    r.add_argument("n", type=int)
    sub.add_parser("selfcheck")
    a = ap.parse_args()
    if getattr(a, "root", None):
        TX.ROOT = Path(a.root).resolve()

    try:
        if a.cmd in ("new", "add"):
            text, names, kinds, src = _inputs(a)
            tags = [t.strip() for t in a.tags.split(",") if t.strip()]
            res = (TX.create(a.set, a.label or "", text, names, kinds, src, tags) if a.cmd == "new"
                   else TX.add_items(a.set, text, names, kinds, src, tags))
            print(f"{res['set']}: {res['added']} saved, {res['reused']} re-used from the prompt library"
                  + (f", {res['to_sort']} file(s) for Claude to sort in" if res["to_sort"] else "")
                  + f" - {res['count']} in the set. Next: {res['command']}")
            return 0
        if a.cmd == "list":
            rows = TX.list_sets()
            if not rows:
                print(f"no text sets yet in {TX.ROOT} (textsets.py new <set> --paste <file>)")
            for x in rows:
                print(f"{x['name']:28s} {x['label'][:30]:30s} {x['count']:3d} texts, {x['checked']:3d} checked, "
                      f"patterns {x['patterns']:5s} {x['updated'] or ''}")
            return 0
        if a.cmd == "show":
            if a.json:
                print(json.dumps(TX.get_set(a.set), indent=1, ensure_ascii=False))
            else:
                print("\n".join(TX.show(a.set, a.n)))
            return 0
        if a.cmd == "state":
            print(json.dumps(TX.state(a.set), indent=1, ensure_ascii=False))
            return 0
        if a.cmd == "check":
            f = Path(a.file)
            res = TX.save_check(a.set, a.ref, read_json(f))
            print(res["line"])
            for w in res["warnings"]:
                print(f"note: {w}")
            claude = (TX.set_dir(a.set) / "claude").resolve()
            if claude in f.resolve().parents:                 # Claude's draft, now in the record: it goes
                f.unlink(missing_ok=True)
            return 0
        if a.cmd == "kind":
            print(TX.set_item_kind(a.set, a.n, a.kind, a.why, by="claude")["line"])
            return 0
        if a.cmd == "patterns":
            f = Path(a.file)
            print(TX.save_patterns(a.set, read_json(f))["line"])
            if (TX.set_dir(a.set) / "claude").resolve() in f.resolve().parents:
                f.unlink(missing_ok=True)
            return 0
        if a.cmd == "remove-item":
            res = TX.remove_item(a.set, a.n)
            print(f"#{res['removed']} out of the set (it stays in the prompt library), {res['count']} left")
            return 0
        if a.cmd == "selfcheck":
            res = TX.selfcheck(verbose=True)
            print(f"{'PASS' if res['passed'] else 'FAIL'} textsets selfcheck in {res['seconds']} s")
            return 0 if res["passed"] else 1
    except ValueError as e:                                  # a check / patterns refused: say what, nothing saved
        print(f"REFUSED: {e}" if a.cmd in ("check", "patterns") else f"error: {e}")
        return 2 if a.cmd in ("check", "patterns") else 1
    except FileNotFoundError as e:
        print(f"error: {e}")
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
