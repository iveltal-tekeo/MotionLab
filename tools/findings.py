"""Lessons that earn their confidence (2026-11-02; docs\\plans.md *Learn from your own posts* R3;
motionlab\\findings.py): patterns across the user's own posts (Content agency > What works), each a hunch until later
posts confirm it - tested again after every Check my pages.

    .venv\\Scripts\\python tools\\findings.py show        the lessons (their worth today, the last run), the patterns
                                                        that stand out now, how far each platform is from the bar
    .venv\\Scripts\\python tools\\findings.py retest      every active lesson tested again on the posts there are now
    .venv\\Scripts\\python tools\\findings.py selfcheck   known answers (made-up posts, a temp store)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import findings as FD  # noqa: E402
from motionlab.util import setup_console  # noqa: E402


def main() -> int:
    setup_console()
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if a[0] == "show":
        V = FD.view()
        print(f"lessons ({len(V['findings'])}):")
        for f in V["findings"]:
            last = f["runs"][-1] if f["runs"] else {}
            print(f"  {f['id']} [{f['status']}{', weakened' if f.get('weakened') else ''}] {f['claim']} - last run "
                  f"{last.get('date')}: {last.get('verdict')} {last.get('med_yes')} vs {last.get('med_no')} "
                  f"({last.get('n_yes')} / {last.get('n_no')} videos){' - ' + f['why_refuted'] if f.get('why_refuted') else ''}")
        print(f"patterns that stand out now ({len(V['candidates'])} of {V['tried']} tried - hunches only):")
        for c in V["candidates"]:
            print(f"  {c['claim']}: {c['run']['med_yes']} vs {c['run']['med_no']} ({c['run']['n_yes']} / {c['run']['n_no']})")
        for plat, b in V["bars"].items():
            print(f"{plat}: {b['posts']} posts in the last {FD.WINDOW_DAYS} days, {b['measured']} read by SPARK; with "
                  + ", ".join(f"{m} {n}" for m, n in b["metrics"].items()) + f" (a pattern needs {2 * FD.MIN_SIDE})")
        return 0
    if a[0] == "retest":
        for r in FD.retest_all():
            print(f"{r['id']}: {r['change']} ({r['verdict']}) - {r['claim']}")
        return 0
    if a[0] == "selfcheck":
        r = FD.selfcheck()
        print("\n".join(r["lines"]))
        print("PASS" if r["passed"] else "FAIL")
        return 0 if r["passed"] else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
