"""MotionLab shared knowledge from the command line (the app's Knowledge page does the same).

    .venv\\Scripts\\python tools\\knowledge.py cards              (re)build the reference cards of this PC's analyses
    .venv\\Scripts\\python tools\\knowledge.py summary            rebuild knowledge\\local\\summary.md (what Claude reads)
    .venv\\Scripts\\python tools\\knowledge.py pending            what "Share my knowledge" would send now
    .venv\\Scripts\\python tools\\knowledge.py next-lesson-id     the id for a new local lesson (local-N)
    .venv\\Scripts\\python tools\\knowledge.py share              share: commit + push to GitHub (or write a pack)
    .venv\\Scripts\\python tools\\knowledge.py export             only write a pack to knowledge\\outbox\\
    .venv\\Scripts\\python tools\\knowledge.py import <pack>      import a friend's pack (cards + lessons to review)

Layout and rules: tools\\motionlab\\knowledge.py and docs\\knowledge_sharing.md."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import knowledge as KN  # noqa: E402
from motionlab.app import updater  # noqa: E402
from motionlab.util import LAB, setup_console  # noqa: E402


def main() -> int:
    setup_console()
    if len(sys.argv) < 2 or sys.argv[1] not in ("cards", "summary", "pending", "next-lesson-id", "share", "export",
                                                  "import"):
        print(__doc__)
        return 2
    cmd = sys.argv[1]
    if cmd == "cards":
        for c in KN.build_local_cards():
            P = c["pacing"]
            print(f"{c['video_id']}  {c['category'] or '-':16s} {P['cuts_per_min']} cuts/min  {c['title']}")
    elif cmd == "summary":
        KN.summary()
        print(KN.SUMMARY)
    elif cmd == "pending":
        p = KN.pending()
        print(f"{len(p['cards'])} card(s): " + ", ".join(c["title"] for c in p["cards"]))
        print(f"{len(p['lessons'])} lesson(s): " + ", ".join(i for i, _ in p["lessons"]))
    elif cmd == "next-lesson-id":
        print(KN.next_lesson_id())
    elif cmd == "export":
        pack = KN.make_pack()
        print(KN.write_pack(pack))
    elif cmd == "import":
        if len(sys.argv) < 3:
            raise SystemExit("give the pack file")
        print(json.dumps(KN.import_pack(Path(sys.argv[2])), indent=1))
    elif cmd == "share":
        who = KN.author()
        if not who:
            raise SystemExit("set your name for sharing first (app: Settings > Sharing & updates)")
        pack = KN.make_pack(who)
        print(f"sharing {len(pack['cards'])} card(s), {len(pack['lessons'])} lesson(s) as {who}")
        if pack["cards"] or pack["lessons"]:
            print("pack:", KN.write_pack(pack).relative_to(LAB))
        if updater.is_repo():
            try:
                r = updater.share(KN.stage(pack) if (pack["cards"] or pack["lessons"]) else [], who,
                                  f"knowledge: {who} shares {len(pack['cards'])} reference(s), "
                                  f"{len(pack['lessons'])} lesson(s)")
            except updater.GitError as e:
                r = {"pushed": False, "error": str(e)}
            print(json.dumps(r, indent=1))
            if r.get("pushed"):
                KN.mark_shared(pack, "github")
        else:
            print("not a git checkout: send the pack file instead")
        KN.summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
