"""Tests of one idea (2026-11-02; docs\\plans.md *Learn from your own posts* R2; motionlab\\experiments.py): two or three
versions of one idea posted on the same platform, compared by the number the user picked (Content agency > Tests),
then Claude's keep / change / cut for the next version - saved only through the gate.

    .venv\\Scripts\\python tools\\experiments.py list                   every test: id, state, result
    .venv\\Scripts\\python tools\\experiments.py show <id>              what Claude reads first: the rule, the result,
                                                                       each version's numbers and its SPARK
    .venv\\Scripts\\python tools\\experiments.py review <id> <draft>    Claude's keep / change / cut (JSON) through the
                                                                       gate - nothing saved when a check fails
    .venv\\Scripts\\python tools\\experiments.py selfcheck              known answers (no network, a temp store)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import experiments as EX  # noqa: E402
from motionlab.util import setup_console  # noqa: E402


def main() -> int:
    setup_console()
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if a[0] == "list":
        for t in EX.views()["tests"]:
            r = t["result"]
            print(f"{t['id']}  [{t['state']}]  {t['platform']}  {t['title']}  -> {r['state']}"
                  + (f" {r.get('winner')}" if r.get("winner") else ""))
        return 0
    if a[0] == "show" and len(a) == 2:
        try:
            print(EX.show_text(a[1]))
        except ValueError as e:
            print(f"ERROR: {e}")
            return 1
        return 0
    if a[0] == "review" and len(a) == 3:
        try:
            draft = json.loads(Path(a[2]).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"ERROR: the draft could not be read: {e}")
            return 1
        try:
            rep = EX.save_review(a[1], draft)
        except ValueError as e:
            print(str(e))
            return 1
        print(f"saved: test {a[1]} - {len(rep['items'])} items; next test: {rep['next_test']['try']}")
        return 0
    if a[0] == "selfcheck":
        r = EX.selfcheck()
        print("\n".join(r["lines"]))
        print("PASS" if r["passed"] else "FAIL")
        return 0 if r["passed"] else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
