"""The logo library (2026-10-16): brand and app logos (YouTube, TikTok, Premiere Pro, DaVinci Resolve, Claude, Figma...)
as SVG that the motion graphics can show - sharp at any size, recoloured to a graphic's palette. The logic is
tools\\motionlab\\logos.py (its docstring: variants, how a graphic names a logo, the MLLogo helper in the page).

    .venv\\Scripts\\python tools\\logos.py import [<folder>]     the library again from the user's folder (default
          refs\\logos\\: <logo>\\<variant>.svg, only read) -> logos\\<logo>\\<variant>.svg cleaned + logos\\logos.json
    .venv\\Scripts\\python tools\\logos.py list [--group social|ai|creative|dev|work|web]   id, name, variants
    .venv\\Scripts\\python tools\\logos.py find "<words>" [--n 8]   the logos that fit the words ("my editing apps:
          premiere and after effects", "twitter") - one line each, best first
    .venv\\Scripts\\python tools\\logos.py show <id>               every variant: aspect, background, colours, tint
    .venv\\Scripts\\python tools\\logos.py check <graphic folder>  the logos its settings name -> assets\\logos\\logos.js
    .venv\\Scripts\\python tools\\logos.py selfcheck               known answers on temp folders (no render)

In a graphic: a logo setting (id logo / logos / *_logo / *_logos) = "youtube", "youtube/mono", "a|b|c"; any text
setting = ":youtube:" where a letter or an emoji goes. Renders and snapshots bundle the named logos by themselves.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import logos as LG  # noqa: E402
from motionlab import overlay_settings as OS  # noqa: E402
from motionlab.util import LAB, setup_console  # noqa: E402


def _line(lg: dict) -> str:
    vs = ", ".join(lg["variants"])
    return f"{lg['id']:16s} {lg['name']:17s} {lg['group']:9s} {vs}"


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("import")
    s.add_argument("folder", nargs="?")
    s = sub.add_parser("list")
    s.add_argument("--group")
    s = sub.add_parser("find")
    s.add_argument("words")
    s.add_argument("--n", type=int, default=8)
    s = sub.add_parser("show")
    s.add_argument("id")
    s = sub.add_parser("check")
    s.add_argument("folder")
    sub.add_parser("selfcheck")
    a = ap.parse_args()

    if a.cmd == "import":
        src = Path(a.folder) if a.folder else LG.SOURCE
        if not src.is_absolute():
            src = LAB / src if (LAB / src).exists() else src
        LG.import_folder(src)
        return 0
    if a.cmd == "list":
        cat = LG.catalog()
        L = [lg for lg in cat["logos"] if not a.group or lg["group"] == a.group]
        for g, words in cat.get("groups", {}).items():
            rows = [lg for lg in L if lg["group"] == g]
            if rows:
                print(f"\n{words} ({g}):")
                print("\n".join("  " + _line(lg) for lg in rows))
        print(f"\n{len(L)} logos in {LG.ROOT}  (variants: " + "; ".join(f"{k} = {v}" for k, v in LG.VARIANT_WORDS.items()) + ")")
        return 0
    if a.cmd == "find":
        hits = LG.find(a.words, a.n)
        for lg in hits:
            print(f"{lg['score']:4.0f}  " + _line(lg))
        if not hits:
            print("no logo fits those words - logos.py list shows them all")
        return 0
    if a.cmd == "show":
        lg = LG.by_id(a.id.strip(":").split("/")[0].lower())
        if not lg:
            print(f"no logo '{a.id}' - try: logos.py find \"{a.id}\"")
            return 1
        print(f"{lg['name']} ({lg['id']}), {LG.GROUP_WORDS.get(lg['group'], lg['group'])}; search words: {' '.join(lg['words'])}")
        for v, i in lg["variants"].items():
            on = {"light": "dark ink - for a light background", "dark": "light ink - for a dark background",
                  "any": "any background"}[i["on"]]
            tint = "takes any colour" if i["tint"] else f"one colour {i['one']} - a tint replaces it" if i["one"] else "keeps its colours"
            print(f"  {lg['id']}/{v:14s} aspect {i['aspect']:5.2f}  {on}; {tint}; colours {', '.join(i['colors']) or '-'}"
                  f"  ({LG.ROOT / lg['id'] / (v + '.svg')})")
        print(f"default = {lg['default']}; in a graphic: \"{lg['id']}\" (picks the variant for the background), "
              f"\"{lg['id']}/mono\" ..., or :{lg['id']}: inside a text")
        return 0
    if a.cmd == "check":
        folder = Path(a.folder)
        ids, unknown = LG.ensure(folder, OS.values(folder), OS.declared(folder))
        print(f"{folder.name}: " + (", ".join(ids) + " in assets\\logos\\logos.js" if ids else "names no library logo")
              + (f"; not in the library: {', '.join(unknown)} (logos.py find)" if unknown else ""))
        return 1 if unknown else 0
    if a.cmd == "selfcheck":
        return 0 if LG.selfcheck()["passed"] else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
