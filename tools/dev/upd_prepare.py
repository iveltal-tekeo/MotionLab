"""Fake-GitHub update test (never the real remote), step 1. Everything lives in .app\\dev\\upd\\ (not in git).

    .venv\\Scripts\\python tools\\dev\\upd_prepare.py setup               hub.git = a bare clone of the last commit
                                                                     (the fake GitHub), friendA + work = clones
    .venv\\Scripts\\python tools\\dev\\upd_prepare.py <version>           the working copy's changes -> work, as
                                                                     <version> with a test CHANGELOG section, pushed
    .venv\\Scripts\\python tools\\dev\\upd_prepare.py x --knowledge       push only a new shared reference card
Then start the friend: .venv\\Scripts\\python .app\\dev\\upd\\friendA\\tools\\app.py --no-window --stay --port 8791
(WITH update checks: its origin is the local hub) and drive it with tools\\dev\\upd_test.py. Stop it afterwards.
"""
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

LAB = Path(__file__).resolve().parents[2]
D = LAB / ".app" / "dev" / "upd"                      # the fake GitHub: hub.git, work, friendA
WORK = D / "work"


def git(*a, cwd=WORK):
    r = subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"git {' '.join(a)}: {r.stderr}")
    return r.stdout.strip()


def main():
    v = sys.argv[1]
    if v == "setup":
        shutil.rmtree(D, ignore_errors=True)
        D.mkdir(parents=True)
        git("clone", "-q", "--bare", str(LAB), str(D / "hub.git"), cwd=D)
        for name in ("friendA", "work"):
            git("clone", "-q", str(D / "hub.git"), str(D / name), cwd=D)
        print(f"fake GitHub ready in {D} (friendA + work at {git('log', '--oneline', '-1', cwd=D / 'friendA')})")
        return
    if "--knowledge" in sys.argv:
        card = WORK / "knowledge" / "references" / f"zztest{int(time.time())}--friend.json"
        card.parent.mkdir(parents=True, exist_ok=True)
        card.write_text(json.dumps({"video_id": card.stem.split("--")[0], "title": "ZZ test card", "author": "friend",
                                    "category": "other", "effects": [], "pacing": {}}), encoding="utf-8")
        git("add", str(card.relative_to(WORK)))
        git("commit", "-q", "-m", "knowledge: friend shares 1 reference(s), 0 lesson(s)")
        git("push", "-q", "origin", "HEAD:main")
        print("pushed a knowledge-only commit")
        return
    changed = [ln[3:] for ln in git("status", "--porcelain", cwd=LAB).splitlines() if ln[:2].strip()]
    for rel in changed:
        src = LAB / rel
        if src.is_file():
            dst = WORK / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    init = WORK / "tools" / "motionlab" / "__init__.py"
    init.write_text(re.sub(r'__version__\s*=\s*"[^"]+"', f'__version__ = "{v}"', init.read_text(encoding="utf-8")),
                    encoding="utf-8")
    log = WORK / "CHANGELOG.md"
    text = log.read_text(encoding="utf-8")
    sec = (f"## {v} - 2026-10-09 - Test release {v}\n\n- **Update button** test entry for {v}: the sidebar shows "
           f"*Update available*, the dialog lists this section.\n- A second line with `code` and **bold**.\n\n")
    i = text.index("\n## ") + 1
    log.write_text(text[:i] + sec + text[i:], encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", f"MotionLab {v} (test)")
    git("push", "-q", "origin", "HEAD:main")
    print(f"pushed {v}: {len(changed)} changed files + version + changelog")


if __name__ == "__main__":
    main()
