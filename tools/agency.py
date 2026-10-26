"""Content agency (0.6.0): the plan around the videos - the content calendar (`knowledge\\local\\calendar.json`,
tools\\motionlab\\agency.py) and your posted videos (`knowledge\\local\\social.json`, tools\\motionlab\\social.py).

    .venv\\Scripts\\python tools\\agency.py check        read the pages My Brand names (YouTube, TikTok - public numbers,
                                                       no login): their newest videos, when they were posted, views,
                                                       likes, comments, followers; each check kept (how a video grew).
                                                       The app's job "agency_check" - only when the user presses it
    .venv\\Scripts\\python tools\\agency.py ics          the calendar's dated posts as an .ics on the console
    .venv\\Scripts\\python tools\\agency.py selfcheck    known answers (no network)
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
        return 0
    if a[0] == "ics":
        print(AG.ics(), end="")
        return 0
    if a[0] == "selfcheck":
        ok = True
        for r in (AG.selfcheck(), SO.selfcheck()):
            print("\n".join(r["lines"]))
            ok = ok and r["passed"]
        print("PASS" if ok else "FAIL")
        return 0 if ok else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
