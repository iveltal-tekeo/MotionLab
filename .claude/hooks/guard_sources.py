"""Hard rule 1, enforced by Claude Code itself (2026-10-29, the user's pick from docs\\ideas.md): a PreToolUse hook
(.claude\\settings.json -> guard-sources.sh -> this file) that stops Claude from changing the user's sources -
anything in refs\\ and the files at the top of projects\\<name>\\ (the footage; everything Claude makes goes to
projects\\<name>\\build\\, which stays free). Standard library only; reads the hook's JSON on stdin.

  Edit / Write / NotebookEdit   refused when the file is in refs\\ or directly in projects\\<name>\\ (not build\\)
  Bash / PowerShell             refused when one command (split at && || ; and new lines) deletes, moves, renames or
                                redirects (>) AND names refs\\, projects\\ or a project's own folder / top-level file

Exit 2 + a line on stderr = refused (Claude sees the reason); exit 0 = allowed. The lab's own tools keep their
SHA-256 checks - a script that opens a file itself is not seen here.

    python .claude\\hooks\\guard_sources.py --selfcheck
"""
import json
import re
import sys
from pathlib import PurePath

# a command word that deletes, moves, renames or overwrites (bash, cmd, PowerShell and their aliases, git, Python)
VERB = re.compile(r"(?i)(?:(?<![\w.-])(?:rm|rmdir|unlink|shred|truncate|mv|del|erase|rd|move|ren|rename|"
                  r"remove-item|move-item|rename-item|clear-content|ri|mi|rni)(?![\w-])|"
                  r"\bgit\s+(?:rm|mv|clean)\b|(?<![\w-])-delete\b|"
                  r"\b(?:os\.(?:remove|unlink|rename|replace|rmdir|removedirs)|shutil\.(?:rmtree|move)|"
                  r"send2trash)\s*\(|\.(?:unlink|rmdir|rename)\s*\()")
# a redirect (> or >>) - only its TARGET matters (reading refs\ and writing elsewhere is fine); not 2>&1, ->, =>
REDIRECT = re.compile(r"(?<![<>&\d=-])>>?\s*[\"']?([^\s\"'|;&<>]+)")
REFS = re.compile(r"(?i)(?<![\w.-])refs(?=[\\/\s\"')]|$)")
PROJECTS = re.compile(r"(?i)(?<![\w.-])projects(?:(?=[\s\"')]|$)|[\\/]([^\\/\n\"']+)(?:[\\/]([^\\/\s\"'\n]*))?)")
SPLIT = re.compile(r"&&|\|\||;|\n")


def protected_in(text: str) -> str:
    """The first protected path a command names: refs, the projects folder, a project's folder or a file at its top."""
    if REFS.search(text):
        return "refs\\"
    for m in PROJECTS.finditer(text):
        name, top = m.group(1), m.group(2)
        if name is None:
            return "projects\\"
        if top is None or top == "":
            return f"projects\\{name.strip()}\\"
        if top.lower() != "build":
            return f"projects\\{name.strip()}\\{top}"
    return ""


def file_protected(path: str) -> str:
    """For a file tool: refs\\... at any depth, or a file directly in projects\\<name>\\."""
    parts = [p.lower() for p in PurePath(path.replace("\\", "/")).parts]
    for i, p in enumerate(parts):
        if p == "refs":
            return "refs\\"
        if p == "projects" and len(parts) - i == 3:          # projects / <name> / <file>
            return "projects\\<name>\\ (its top level - write into its build\\ folder)"
    return ""


def check(payload: dict) -> str:
    tool, inp = payload.get("tool_name", ""), payload.get("tool_input") or {}
    if tool in ("Edit", "Write", "NotebookEdit", "MultiEdit"):
        hit = file_protected(str(inp.get("file_path") or inp.get("notebook_path") or ""))
        return f"{tool} into {hit}" if hit else ""
    if tool in ("Bash", "PowerShell"):
        for seg in SPLIT.split(str(inp.get("command") or "")):
            hit = protected_in(seg) if VERB.search(seg) else ""
            for target in REDIRECT.findall(seg):
                hit = hit or protected_in(target)
            if hit:
                return f"a delete / move / rename / overwrite aimed at {hit}: {seg.strip()[:160]}"
    return ""


def selfcheck() -> int:
    no = [("Bash", "ls refs"), ("Bash", "ffmpeg -i refs/a.mp4 -y analysis/a/x.mp4 && rm analysis/a/tmp.txt"),
          ("Bash", "rm -rf projects/zz/build/overlays/v1"), ("PowerShell", "Remove-Item 'C:\\MotionLab\\projects\\zz\\build\\x.png'"),
          ("Bash", "git ls-remote origin refs/tags/v0.6.0.7"), ("Bash", ".venv/Scripts/python tools/analyze.py refs/a.mp4"),
          ("Bash", "cat refs/downloads.json | head -3"), ("Bash", "mv analysis/a/x.json analysis/a/y.json"),
          ("Bash", "echo 2>&1 projects/zz/clip.mp4"), ("Edit", "C:\\MotionLab\\projects\\zz\\build\\plan_v2.json"),
          ("Write", "C:/MotionLab/analysis/a/review.json"), ("Write", "C:/MotionLab/docs/plans.md"),
          ("Bash", "grep x refs/downloads.json > /tmp/out.txt"), ("Bash", "ls refs >/dev/null 2>&1"),
          ("Bash", "git push --delete origin v0"), ("Bash", "echo 'plan_v1 -> projects/zz/clip.mp4'")]
    yes = [("Bash", "rm refs/a.mp4"), ("Bash", "rm -rf refs"), ("Bash", "mv \"projects/My Video/clip 1.mp4\" x.mp4"),
           ("PowerShell", "Remove-Item C:\\MotionLab\\refs\\a.mp4"), ("PowerShell", "Get-ChildItem refs | Remove-Item"),
           ("Bash", "rm -rf \"projects/My Video\""), ("Bash", "git rm projects/zz/clip.mov"),
           ("Bash", "python -c \"import os; os.remove('refs/a.mp4')\""), ("Bash", "echo x > refs/downloads.json"),
           ("PowerShell", "Rename-Item projects\\zz\\IMG_1.MOV IMG_2.MOV"), ("Bash", "rm -rf projects"),
           ("Edit", "C:\\MotionLab\\refs\\downloads.json"), ("Write", "C:/MotionLab/projects/zz/notes.txt"),
           ("Write", "/home/user/MotionLab/refs/x.mp4"), ("Bash", "find refs -name '*.part' -delete"),
           ("Bash", "cat a.txt >> \"projects/My Video/notes.txt\"")]
    bad = 0
    for want, cases in ((False, no), (True, yes)):
        for tool, arg in cases:
            key = "command" if tool in ("Bash", "PowerShell") else "file_path"
            got = bool(check({"tool_name": tool, "tool_input": {key: arg}}))
            if got != want:
                bad += 1
                print(f"FAIL {'refused' if got else 'allowed'}: {tool} {arg}")
    print(f"guard_sources selfcheck: {len(no) + len(yes) - bad}/{len(no) + len(yes)} PASS")
    return 1 if bad else 0


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        sys.exit(selfcheck())
    try:
        why = check(json.loads(sys.stdin.read() or "{}"))
    except (ValueError, TypeError):
        sys.exit(0)                                   # not a hook payload: never block on our own error
    if why:
        print(f"MotionLab hard rule 1 (never change a source): refused {why}. Read sources only; write copies into "
              "analysis\\<video>\\ or projects\\<name>\\build\\.", file=sys.stderr)
        sys.exit(2)
    sys.exit(0)
