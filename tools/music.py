"""The music library (0.6.0 step 10, motionlab\\music.py): the songs downloaded in the Analyser (refs\\audio - read where
they are, never changed), songs added (library\\music\\) and ambience beds for under a talking video
(library\\music\\ambience\\<kind>\\), each measured once: length; a song's tempo, energy (calm / steady / energetic) and
tone (dark / warm / bright), drops. The app's Motion Graphics > Music shows it; New edit offers it.

    .venv\\Scripts\\python tools\\music.py index            measure what is new or changed -> library\\music\\music.json
    .venv\\Scripts\\python tools\\music.py list [--json]    every song and bed with its measures and flags
    .venv\\Scripts\\python tools\\music.py add <file> [--bed room|cafe|city|nature|rain|office]
          a copy into the library (the file is only read; a new name, never over a file), then measured
    .venv\\Scripts\\python tools\\music.py beds [--want room:1,cafe:1] [--dry-run]
          ambience beds made with ElevenLabs (the key of Motion Graphics > Sounds; descriptions in
          tools\\sounds\\generate.json "beds"; loop = no seam; about 10 credits a second asked) -> ambience\\<kind>\\
    .venv\\Scripts\\python tools\\music.py selfcheck        a scratch library: measures, flags, a bed under a voice

A bed in an edit: a plan's "sfx": {"bed": {"file": "<path>", "db": -26}} - `sfx.py plan` loops it under the voice,
26 dB under its words (motionlab\\music.py BED_DB), faded in and out.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import music as MU  # noqa: E402
from motionlab.util import setup_console  # noqa: E402


def mmss(s: float | None) -> str:
    return "" if s is None else f"{int(s) // 60}:{int(round(s)) % 60:02d}"


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("index")
    s = sub.add_parser("list")
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("add")
    s.add_argument("file")
    s.add_argument("--bed", choices=MU.BEDS, help="an ambience bed of this kind (default: a song)")
    s = sub.add_parser("beds")
    s.add_argument("--want", help="kind:how many, comma-separated (default: the list's own numbers)")
    s.add_argument("--dry-run", action="store_true", help="the credits it would take - nothing made")
    sub.add_parser("selfcheck")
    a = ap.parse_args()
    if a.cmd == "index":
        r = MU.index(log=lambda m: print(m, flush=True))
        print(f"{len(r['measured'])} measured, {r['kept']} already measured"
              + (f", {len(r['failed'])} not readable" if r["failed"] else "") + f" -> {MU.rel(MU.ROOT / 'music.json')}")
        return 1 if r["failed"] and not r["measured"] and not r["kept"] else 0
    if a.cmd == "list":
        st = MU.state()
        if a.json:
            print(json.dumps(st, indent=1, ensure_ascii=False))
            return 0
        for x in st["tracks"]:
            m = (f"{x['bpm']:g} BPM, {x['energy']}, {x['tone']}, {x.get('drops', 0)} drops" if x.get("bpm")
                 else "not measured yet" if not x["measured"] else "")
            print(f"{'*' if x['fav'] else ' '}{'-' if x['off'] else ' '} {x['type']:4s} {x['kind'] or '':6s} "
                  f"{mmss(x.get('len_s')):>5s}  {(x['artist'] + ' - ' if x['artist'] else '') + x['title']}"
                  f"  [{x['from']}]  {m}")
        print(f"{len(st['tracks'])} file(s), {st['unmeasured']} not measured yet (* = favourite, - = hidden)")
        return 0
    if a.cmd == "add":
        try:
            p = MU.add(Path(a.file), "bed" if a.bed else "song", a.bed or "")
        except (OSError, ValueError) as e:
            raise SystemExit(f"ERROR: {e}")
        print(f"added: {MU.rel(p)}")
        MU.index(log=lambda m: print(m, flush=True), only=[MU.rel(p)])
        return 0
    if a.cmd == "beds":
        from motionlab import sfxgen as GEN
        want = {}
        for part in [x.strip() for x in (a.want or "").split(",") if x.strip()]:
            k, _, n = part.partition(":")
            want[k.strip()] = int(n or 1)
        if not want:
            want = {k: int(v.get("n", 0)) for k, v in MU.bed_prompts().items()}
        want = {k: n for k, n in want.items() if n > 0}
        if not want:
            raise SystemExit("ERROR: nothing to make - --want room:1,cafe:1")
        try:
            r = MU.make_beds(want, log=lambda m: print(m, flush=True), dry=a.dry_run)
        except GEN.GenError as e:
            raise SystemExit(f"ERROR: {e}")
        if a.dry_run:
            print(f"{sum(want.values())} bed(s) = about {r['credits']} ElevenLabs credits (plan: "
                  f"{GEN.settings()['plan']}): " + ", ".join(f"{k} {v}" for k, v in want.items()))
            return 0
        print(f"{r['made']} bed(s) made ({r['credits']} credits) - Motion Graphics > Music > Ambience")
        for f in r["files"]:
            print("  " + f)
        MU.index(log=lambda m: print(m, flush=True), only=r["files"])
        return 0
    if a.cmd == "selfcheck":
        return 0 if MU.selfcheck()["passed"] else 1
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
