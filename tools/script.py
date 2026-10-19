"""Prepare a video (0.4.x): the words you say on camera - the script check and the app's script requests, for
`/write-script`. Text only: no model, no Claude, no cost.

    .venv\\Scripts\\python tools\\script.py check <file | script id> [--length 30] [--like <reference> ...] [--json]
          the script check: the hook (first line, the words of the first 3 s, its pattern, a greeting first), the
          length at a speaking rate (150 words/min, or the rate measured on --like analysed videos), short sentences,
          filler words, the longest stretch with nothing new, "you" vs "I", numbers, the call to action, the last
          line, the notes for what is on screen; n of 11 checks pass. A script id (script-003) takes its record's
          style references and its request's length unless given.
    .venv\\Scripts\\python tools\\script.py show <script id | req-NNN>
          everything Claude needs: the script (or the request = the user's answers), what the user wants from the
          rewrite, the scripts made from it, and the check
    .venv\\Scripts\\python tools\\script.py requests     every request of the app's Prepare page, newest first
          (kinds: new / improve = a script, title = *Title & thumbnail first*, prompt = a new prompt)

Requests: knowledge\\local\\prompts\\requests\\req-NNN.json (the app writes them: *Improve my script* = the script
saved in the prompt library + what the user wants; *Write one from zero* = the answers; *Title & thumbnail first* =
the answers for `/write-title request`, motionlab.script.save_title; the prompt library's *Generate a new prompt* /
*Use it, change…* = kind prompt for `/write-prompt request`, motionlab.script.save_prompt). Scripts themselves live in
the prompt library (tools\\prompts.py: kind script / hook). Script times are estimates in seconds - there is no video
yet. Rules behind the check: .claude\\skills\\write-script\\guidelines.md.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import prompts as PR  # noqa: E402
from motionlab import script as SC  # noqa: E402
from motionlab.util import setup_console  # noqa: E402


def _check_args(rec: dict | None, length, like) -> tuple:
    req = SC.request_of(rec["id"]) if rec else None
    if length is None and req and req.get("length_s"):
        length = req["length_s"]
    if not like and rec:
        like = rec.get("style_refs") or (req or {}).get("like") or []
    return length, like


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="the script check")
    c.add_argument("what", help="a text file or a script id (script-003)")
    c.add_argument("--length", type=float, default=None, help="the length you want, in seconds")
    c.add_argument("--like", nargs="*", default=None, help="analysed videos whose speaking rate to use")
    c.add_argument("--json", action="store_true")
    s = sub.add_parser("show", help="a script or a request, with the check")
    s.add_argument("id")
    sub.add_parser("requests", help="the Prepare page's requests")
    a = ap.parse_args()

    if a.cmd == "check":
        rec = None
        if re.fullmatch(r"(script|hook)-\d{3,}", a.what):
            rec = PR.get(a.what)
            text = rec["text"]
        else:
            text = Path(a.what).read_text(encoding="utf-8", errors="replace")
        length, like = _check_args(rec, a.length, a.like)
        res = SC.check(text, length, like)
        print(json.dumps(res, ensure_ascii=False, indent=1) if a.json else SC.text_report(res))
        return 0

    if a.cmd == "requests":
        for r in SC.requests():
            what = " ".join(str(r.get("topic") or r.get("script") or r.get("want") or r.get("change") or "").split())
            print(f"{r['id']}  {r.get('kind'):8} {str(r.get('date', ''))[:16]}  {what[:70]}"
                  f"  -> {', '.join(r.get('made') or []) or 'nothing written yet'}")
        return 0

    if a.id.startswith("req-"):
        r = SC.get_request(a.id)
        print(SC.describe_request(r))
        made = next((x.get("made") for x in SC.requests() if x["id"] == a.id), [])
        print(f"  written from it: {', '.join(made) if made else 'nothing yet'}")
        if r.get("kind") == "improve" and r.get("script"):
            rec = PR.get(r["script"])
            print("\n" + PR.describe(rec, full=True))
            length, like = _check_args(rec, None, None)
            print("\nThe check:\n" + SC.text_report(SC.check(rec["text"], length, like)))
        return 0
    rec = PR.get(a.id)
    print(PR.describe(rec, full=True))
    req = SC.request_of(rec["id"]) or (SC.get_request(rec["request"]) if rec.get("request") else None)
    if req:
        print("\nThe request:\n" + SC.describe_request(req))
    if rec["kind"] in ("script", "hook"):
        length, like = _check_args(rec, None, None)
        print("\nThe check:\n" + SC.text_report(SC.check(rec["text"], length, like)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
