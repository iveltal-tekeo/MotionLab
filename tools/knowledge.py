"""MotionLab shared knowledge from the command line (the app's Claude's memory page does the same).

    .venv\\Scripts\\python tools\\knowledge.py cards              (re)build the reference cards of this PC's analyses
    .venv\\Scripts\\python tools\\knowledge.py summary            rebuild knowledge\\local\\summary.md (what Claude reads)
    .venv\\Scripts\\python tools\\knowledge.py memory             rebuild + print knowledge\\local\\memory.md: Claude's memory
                                                               (your ratings of all your videos as rules, every video's
                                                               style, the effects seen and how they were made) - read
                                                               it before an edit or a prompt
    .venv\\Scripts\\python tools\\knowledge.py memory --styles    the same, printed without the effects and how they
                                                               were made (most of the file) - for scripts and titles
    .venv\\Scripts\\python tools\\knowledge.py memory --rules     only your ratings as rules (~1.5 KB) - what a video
                                                               made by feel or from zero needs (0.5.3)
    .venv\\Scripts\\python tools\\knowledge.py lessons --kind <talking|generate|templates|all>
                                                               the lessons on making videos for that kind of work
                                                               (+ those for all), in full; the ones the lab's tools
                                                               do now as one line each (0.5.3)
    .venv\\Scripts\\python tools\\knowledge.py pending            what "Share my knowledge" would send now - and what
                                                               stays on this PC (unticked in Claude's memory > Shared
                                                               knowledge, or looks like a test and not ticked)
    .venv\\Scripts\\python tools\\knowledge.py next-lesson-id     the id for a new local lesson (local-N)
    .venv\\Scripts\\python tools\\knowledge.py next-lesson-id --kind making    ... on making videos (local-make-N, in
                                                               knowledge\\local\\lessons_making.md; reviewed = M###)
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
    if len(sys.argv) < 2 or sys.argv[1] not in ("cards", "summary", "memory", "lessons", "pending", "next-lesson-id", "share",
                                                  "export", "import"):
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
    elif cmd == "memory":
        text = KN.memory_index()                            # memory.md stays the whole memory, rebuilt
        print(KN.memory_rules() if "--rules" in sys.argv[2:] else
              KN.memory_index(write=False, styles=True) if "--styles" in sys.argv[2:] else text)
    elif cmd == "lessons":
        kind = sys.argv[sys.argv.index("--kind") + 1] if "--kind" in sys.argv[:-1] else "all"
        try:
            print(KN.lessons_for(kind))
        except ValueError as e:
            raise SystemExit(f"--kind: {e}")
    elif cmd == "pending":
        p = KN.pending()
        print(f"{len(p['cards'])} card(s): " + ", ".join(KN.label(c)["name"] for c in p["cards"]))
        for k in KN.KINDS:
            ids = [i for i, _ in p["lessons"] if KN.lesson_kind(i) == k]
            print(f"{len(ids)} lesson(s) on {'making videos' if k == 'making' else 'analysis'}: " + ", ".join(ids))
        kept = p["kept"]
        print(f"kept on this PC (not shared): {len(kept['cards'])} card(s)"
              + (": " + ", ".join(KN.label(c)["name"] + (" (looks like a test)" if KN.looks_test(c.get("analysis"),
                                                                                                   c.get("title")) else "")
                                  for c in kept["cards"]) if kept["cards"] else "")
              + f"; {len(kept['lessons'])} lesson(s)" + (": " + ", ".join(i for i, _ in kept["lessons"])
                                                        if kept["lessons"] else ""))
    elif cmd == "next-lesson-id":
        kind = sys.argv[sys.argv.index("--kind") + 1] if "--kind" in sys.argv[:-1] else "analysis"
        if kind not in KN.KINDS:
            raise SystemExit(f"--kind: {' or '.join(KN.KINDS)}")
        print(KN.next_lesson_id(kind))
    elif cmd == "export":
        pack = KN.make_pack()
        print(KN.write_pack(pack))
        if pack["cards"] or pack["lessons"]:
            KN.mark_shared(pack, "file")                  # a share by file: not sent again, listed in Shared before
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
            elif pack["cards"] or pack["lessons"]:
                KN.mark_shared(pack, "file")              # not uploaded: the pack file is the share
        else:
            print("not a git checkout: send the pack file instead")
            if pack["cards"] or pack["lessons"]:
                KN.mark_shared(pack, "file")
        KN.summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
