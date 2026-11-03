"""The monthly review (2026-11-02; docs\\plans.md 0.6.5 step 18 + *Learn from your own posts* R4;
motionlab\\monthly.py): what worked in a month of the user's own posts (Content agency > Monthly review - the lab's
numbers, no Claude), ending in Claude's three next tests - saved only through the gate. A picked next test becomes an
idea on the calendar (the app's button).

    .venv\\Scripts\\python tools\\monthly.py show [YYYY-MM]            what Claude reads first: the month's posts against
                                                                     the user's usual, the groups, tests, lessons, last
                                                                     month's next tests (no month = the page's default)
    .venv\\Scripts\\python tools\\monthly.py review <YYYY-MM> <draft>  Claude's summary + three next tests (JSON) through
                                                                     the gate - nothing saved when a check fails
    .venv\\Scripts\\python tools\\monthly.py selfcheck                 known answers (no network, temp stores)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import monthly as MO  # noqa: E402
from motionlab.util import setup_console  # noqa: E402


def main() -> int:
    setup_console()
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if a[0] == "show" and len(a) <= 2:
        try:
            print(MO.show_text(a[1] if len(a) == 2 else None))
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
            rep = MO.save_review(a[1], draft)
        except ValueError as e:
            print(str(e))
            return 1
        print(f"saved: the review of {rep['month']} - next tests: "
              + " | ".join(f"{x['n']}. {x['try']}" for x in rep["next_tests"]))
        return 0
    if a[0] == "selfcheck":
        r = MO.selfcheck()
        print("\n".join(r["lines"]))
        print("PASS" if r["passed"] else "FAIL")
        return 0 if r["passed"] else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
