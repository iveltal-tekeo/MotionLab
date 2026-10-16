"""The font library (0.4.6): the free fonts in the lab's fonts\\ folder that every graphic, caption and thumbnail can use
- the same render on every PC. The logic is tools\\motionlab\\fonts.py.

    .venv\\Scripts\\python tools\\fonts.py list           every family: group, licence, weights (variable ranges), size
    .venv\\Scripts\\python tools\\fonts.py sync           the examples' and thumbnail designs' font settings get the library
                                                        (their Windows defaults move to Archivo Black / Anton)
    .venv\\Scripts\\python tools\\fonts.py check <graphic folder>   the fonts its settings name, copied into its assets
    .venv\\Scripts\\python tools\\fonts.py selfcheck      known answers on a temp copy of two families (no network)

A family = a folder in fonts\\ with its .ttf files and its licence file (SIL OFL 1.1 or Apache 2.0, read from the file).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import fonts as F  # noqa: E402
from motionlab import overlay_settings as OS  # noqa: E402
from motionlab.util import setup_console  # noqa: E402


def main() -> int:
    setup_console()
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if a[0] == "list":
        L = F.families()
        for f in L:
            ws = ", ".join(f"{x['wght'][0]}-{x['wght'][1]}" if x["wght"] else str(x["weight"]) + (" italic" if x["italic"] else "")
                           for x in f["files"])
            print(f"{f['group']:21s} {f['family']:20s} {f['licence']:10s} {ws:34s} {f['kb']:5d} KB")
        print(f"{len(L)} families, {sum(f['kb'] for f in L) / 1024:.1f} MB in {F.ROOT}")
        return 0
    if a[0] == "sync":
        ch = F.sync()
        print("\n".join(ch) if ch else "nothing to change: every font setting already offers the library")
        return 0
    if a[0] == "check" and len(a) > 1:
        folder = Path(a[1])
        got = F.ensure(folder, OS.values(folder), OS.declared(folder))
        print(f"{folder.name}: " + (", ".join(got) + " copied into assets\\fonts" if got else "no bundled font in its settings"))
        return 0
    if a[0] == "selfcheck":
        return 0 if F.selfcheck()["passed"] else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
