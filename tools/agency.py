"""Content agency (0.6.0): the plan around the videos - the content calendar (`knowledge\\local\\calendar.json`,
tools\\motionlab\\agency.py) and your posted videos (`knowledge\\local\\social.json`, tools\\motionlab\\social.py).

    .venv\\Scripts\\python tools\\agency.py check        read the pages My Brand names (YouTube, TikTok - public numbers,
                                                       no login): their newest videos, when they were posted, views,
                                                       likes, comments, followers; each check kept (how a video grew).
                                                       The app's job "agency_check" - only when the user presses it
    .venv\\Scripts\\python tools\\agency.py ics          the calendar's dated posts as an .ics on the console
    .venv\\Scripts\\python tools\\agency.py selfcheck    known answers (no network) - with where people left
                                                       (motionlab\\retention.py: made-up retention graphs traced)
                                                       and tests of one idea (motionlab\\experiments.py) and the
                                                       lessons from your posts (motionlab\\findings.py) and the
                                                       monthly review's gate (motionlab\\monthly.py)
    (check also tests the lessons again on the new numbers - tools\\findings.py)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import agency as AG  # noqa: E402
from motionlab import social as SO  # noqa: E402
from motionlab.util import setup_console  # noqa: E402


def main() -> int:
    setup_console()
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if a[0] == "check":
        if not SO.ytdlp():
            print("ERROR: yt-dlp not found - Settings > Programs > yt-dlp")
            return 1
        try:
            SO.check(lambda s: print(s, flush=True))
        except RuntimeError as e:
            print(f"ERROR: {e}")
            return 1
        try:                                    # R3 (2026-11-02): new numbers = the lessons tested again (no network)
            from motionlab import findings as FD
            for r in FD.retest_all():
                print(f"lesson {r['id']}: {r['change']} - {r['claim']}", flush=True)
        except Exception as e:                  # noqa: BLE001 - the check itself went well
            print(f"the lessons could not be tested again: {e}", flush=True)
        return 0
    if a[0] == "ics":
        print(AG.ics(), end="")
        return 0
    if a[0] == "selfcheck":
        from motionlab import experiments as EX
        from motionlab import findings as FD
        from motionlab import monthly as MO
        from motionlab import retention as RT
        ok = True
        for r in (AG.selfcheck(), SO.selfcheck(), RT.selfcheck(), EX.selfcheck(), FD.selfcheck(), MO.selfcheck()):
            print("\n".join(r["lines"]))
            ok = ok and r["passed"]
        print("PASS" if ok else "FAIL")
        return 0 if ok else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
