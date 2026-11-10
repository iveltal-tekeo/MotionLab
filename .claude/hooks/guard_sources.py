"""Hard rule 1, enforced by Claude Code itself (2026-10-29, the user's pick from docs\\ideas.md): a PreToolUse hook
(.claude\\settings.json -> guard-sources.sh -> this file) that stops Claude from changing the user's sources -
anything in refs\\ and the files at the top of projects\\<name>\\ (the footage; everything Claude makes goes to
projects\\<name>\\build\\, which stays free). Standard library only; reads the hook's JSON on stdin.

  Edit / Write / NotebookEdit   refused when the file is in refs\\ or directly in projects\\<name>\\ (not build\\)
  Bash / PowerShell             refused when one command (split at && || ; and new lines)
                                - deletes, moves, renames or redirects (>) AND names refs\\, projects\\ or a project's
                                  own folder / top-level file
                                - copies or encodes INTO one of them (cp / copy / Copy-Item / xcopy / robocopy / rsync:
                                  every path after the first; ffmpeg: its last path) - reading from them stays free
                                - edits or writes one in place (sed -i, perl -i, tee, touch, dd of=, Set-Content,
                                  Add-Content, Out-File, New-Item; Python's open(..., "w") and Path(...).write_*)
                                - does any of that while the shell STANDS in one of them (the hook's "cwd", or a cd /
                                  pushd / Set-Location earlier in the command): `cd refs && rm a.mp4`

2026-11-10 (the code review: 14 of 16 ways to overwrite a source passed - only the delete / move words and > were seen):
the copy, encode, in-place and cwd rules above. And paths are read from the lab's own folder on: a lab that lives in a
folder called "projects" (D:\\projects\\MotionLab) had every delete inside it refused and CLAUDE.md taken for footage.

Exit 2 + a line on stderr = refused (Claude sees the reason); exit 0 = allowed. NOT seen here: a path held in a
variable (d=refs; rm $d/a.mp4), git checkout / restore of a file in refs, a script that opens a file itself - the
lab's own tools keep their SHA-256 checks for those.

    python .claude\\hooks\\guard_sources.py --selfcheck
"""
import json
import os
import re
import sys
from pathlib import Path, PurePath

LAB = os.environ.get("CLAUDE_PROJECT_DIR") or str(Path(__file__).resolve().parents[2])
HOME = "@LAB@"                                      # the lab's folder in a command or a path, however it was spelled

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
# the first word of a command (one stage of a pipe) that writes what it names
COPY = {"cp", "copy", "copy-item", "cpi", "xcopy", "robocopy", "rsync"}       # into every path after the first
WRITE = {"tee", "touch", "set-content", "add-content", "out-file", "new-item"}  # any path it names
INPLACE = re.compile(r"(?i)^(?:sed|perl)\b.*\s-[a-z]*i")
CD = re.compile(r"(?i)^\s*(?:cd|chdir|pushd|set-location|sl)\s+(?:/d\s+)?(.+?)\s*$")
TOKEN = re.compile(r"\"[^\"]*\"|'[^']*'|\S+")
SKIP = re.compile(r"(?i)^(?:&|sudo|command|time|\w+=.*)$")                    # before the command's own first word
# Python in a one-liner: open(<path>, "w" / "a" / "x" / "+"), Path(<path>).write_text / write_bytes
PYOPEN = re.compile(r"open\(\s*[rRbBfFuU]{0,2}[\"']([^\"']+)[\"']\s*,\s*[\"'][^\"']*[wax+]")
PYWRITE = re.compile(r"Path\(\s*[rR]?[\"']([^\"']+)[\"']\s*\)\s*\.write_(?:text|bytes)\s*\(")


def norm(text: str) -> str:
    """The text with the lab's folder as HOME, whichever way it was written (C:\\MotionLab, C:/MotionLab, /c/MotionLab):
    what follows is read from the lab on, never from a folder above it that happens to be called projects or refs."""
    p = PurePath(LAB)
    forms = {str(p), str(p).replace("\\", "/")}
    if p.drive:                                     # Git Bash's /c/MotionLab
        forms.add("/" + p.drive[0].lower() + str(p)[len(p.drive):].replace("\\", "/"))
    for s in sorted(forms, key=len, reverse=True):
        text = re.sub(re.escape(s.rstrip("\\/")) + r"(?![\w.-])", HOME, text, flags=re.I)
    return text


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


def _parts(path: str) -> list[str]:
    parts = [p.lower() for p in PurePath(norm(path).replace("\\", "/")).parts]
    return parts[parts.index(HOME.lower()) + 1:] if HOME.lower() in parts else parts


def file_protected(path: str) -> str:
    """For a file tool: refs\\... at any depth, or a file directly in projects\\<name>\\."""
    parts = _parts(path)
    for i, p in enumerate(parts):
        if p == "refs":
            return "refs\\"
        if p == "projects" and len(parts) - i == 3:          # projects / <name> / <file>
            return "projects\\<name>\\ (its top level - write into its build\\ folder)"
    return ""


def dir_protected(path: str) -> str:
    """For a working folder: refs\\ (any depth), projects\\ itself, a project's folder or a folder of its footage."""
    parts = [p for p in _parts(path) if p not in (".", "/", "\\")]
    for i, p in enumerate(parts):
        if p == "refs":
            return "refs\\"
        if p == "projects" and (len(parts) - i < 3 or parts[i + 2] != "build"):
            return "\\".join(["projects", *parts[i + 1:i + 2]]) + "\\"
    return ""


def _relative(t: str) -> bool:
    return not (t.startswith((HOME, "/", "\\", "~", "$", "%")) or re.match(r"[A-Za-z]:", t))


def _words(stage: str) -> list[str]:
    """One command's words, quotes off, from its own first word on, up to a redirect."""
    toks = [t.strip("\"'") for t in TOKEN.findall(re.split(r"\s\d?>", stage)[0])]
    while toks and SKIP.match(toks[0]):
        toks.pop(0)
    return toks


def written_in(stage: str, here: str) -> str:
    """The protected place one command (a stage of a pipe) writes into, by copying, encoding or editing in place."""
    toks = _words(stage)
    if not toks:
        return ""
    cmd = re.sub(r"(?i)\.exe$", "", toks[0].replace("\\", "/").rsplit("/", 1)[-1]).lower()
    into: list[str] = []
    if cmd in COPY:
        opt = r"/[A-Za-z]{1,8}(:\S*)?$" if cmd in ("xcopy", "robocopy") else r"-"
        args = [t for t in toks[1:] if not re.match(opt, t)]
        into = args[1:2] if cmd == "robocopy" else args[1:]
    elif cmd == "ffmpeg":
        into = [t for t in toks[-1:] if t != "-" and not t.startswith("-")]
    elif cmd in WRITE or INPLACE.match(" ".join(toks)):
        return protected_in(stage) or here
    elif cmd == "dd":
        into = [t[3:] for t in toks[1:] if t.lower().startswith("of=")]
    for t in into:
        hit = protected_in(t) or (here if _relative(t) else "")
        if hit:
            return hit
    return ""


def check(payload: dict) -> str:
    tool, inp = payload.get("tool_name", ""), payload.get("tool_input") or {}
    if tool in ("Edit", "Write", "NotebookEdit", "MultiEdit"):
        hit = file_protected(str(inp.get("file_path") or inp.get("notebook_path") or ""))
        return f"{tool} into {hit}" if hit else ""
    if tool in ("Bash", "PowerShell"):
        here = dir_protected(str(payload.get("cwd") or ""))          # where the shell stands
        for seg in SPLIT.split(norm(str(inp.get("command") or ""))):
            m = CD.match(seg)
            if m:                                                    # it moves: a folder below stays what it was
                t = m.group(1).strip().strip("\"'")
                if not (here and _relative(t) and ".." not in t):
                    here = dir_protected(t)
                continue
            hit = ""
            if VERB.search(seg):
                hit = protected_in(seg) or here
            for target in REDIRECT.findall(seg):
                hit = hit or protected_in(target) or (here if _relative(target) else "")
            for path in PYOPEN.findall(seg) + PYWRITE.findall(seg):
                hit = hit or protected_in(path) or (here if _relative(path) else "")
            for stage in seg.split("|"):
                hit = hit or written_in(stage, here)
            if hit:
                where = f"{hit} (the shell stands in it)" if hit == here and not protected_in(seg) else hit
                return f"a delete / move / rename / overwrite aimed at {where}: {seg.strip()[:160]}"
    return ""


def selfcheck() -> int:
    global LAB
    no = [("Bash", "ls refs"), ("Bash", "ffmpeg -i refs/a.mp4 -y analysis/a/x.mp4 && rm analysis/a/tmp.txt"),
          ("Bash", "rm -rf projects/zz/build/overlays/v1"), ("PowerShell", "Remove-Item 'C:\\MotionLab\\projects\\zz\\build\\x.png'"),
          ("Bash", "git ls-remote origin refs/tags/v0.6.0.7"), ("Bash", ".venv/Scripts/python tools/analyze.py refs/a.mp4"),
          ("Bash", "cat refs/downloads.json | head -3"), ("Bash", "mv analysis/a/x.json analysis/a/y.json"),
          ("Bash", "echo 2>&1 projects/zz/clip.mp4"), ("Edit", "C:\\MotionLab\\projects\\zz\\build\\plan_v2.json"),
          ("Write", "C:/MotionLab/analysis/a/review.json"), ("Write", "C:/MotionLab/docs/plans.md"),
          ("Bash", "grep x refs/downloads.json > /tmp/out.txt"), ("Bash", "ls refs >/dev/null 2>&1"),
          ("Bash", "git push --delete origin v0"), ("Bash", "echo 'plan_v1 -> projects/zz/clip.mp4'"),
          # 2026-11-10: reading a source stays free, and so does work in build\
          ("Bash", "cp refs/a.mp4 analysis/a/copy.mp4"), ("PowerShell", "Copy-Item refs\\a.mp4 projects\\zz\\build\\ref.mp4"),
          ("Bash", "ffmpeg -i refs/a.mp4 -c copy -y analysis/a/x.mp4 2>&1 | tail -3"),
          ("PowerShell", "Get-Content refs\\downloads.json | Set-Content analysis\\a\\d.json"),
          ("Bash", "python -c \"print(open('refs/downloads.json').read()[:10])\""),
          ("Bash", "sed -n '1,5p' refs/downloads.json"), ("Bash", "cd projects/zz/build && rm -rf overlays/v1"),
          ("Bash", "cd refs && ls && cd C:/MotionLab && rm analysis/a/tmp.txt"),
          ("Bash", "rm notes.txt", "C:/MotionLab/projects/zz/build/checks"),
          ("Bash", "ffprobe -v error refs/a.mp4"), ("Bash", "ffmpeg -i refs/a.mp4 -f null -")]
    yes = [("Bash", "rm refs/a.mp4"), ("Bash", "rm -rf refs"), ("Bash", "mv \"projects/My Video/clip 1.mp4\" x.mp4"),
           ("PowerShell", "Remove-Item C:\\MotionLab\\refs\\a.mp4"), ("PowerShell", "Get-ChildItem refs | Remove-Item"),
           ("Bash", "rm -rf \"projects/My Video\""), ("Bash", "git rm projects/zz/clip.mov"),
           ("Bash", "python -c \"import os; os.remove('refs/a.mp4')\""), ("Bash", "echo x > refs/downloads.json"),
           ("PowerShell", "Rename-Item projects\\zz\\IMG_1.MOV IMG_2.MOV"), ("Bash", "rm -rf projects"),
           ("Edit", "C:\\MotionLab\\refs\\downloads.json"), ("Write", "C:/MotionLab/projects/zz/notes.txt"),
           ("Write", "/home/user/MotionLab/refs/x.mp4"), ("Bash", "find refs -name '*.part' -delete"),
           ("Bash", "cat a.txt >> \"projects/My Video/notes.txt\""),
           # 2026-11-10: the ways round it the review found
           ("Bash", "cd refs && rm a.mp4"), ("Bash", "cd projects/zz && mv clip.mp4 old.mp4"),
           ("Bash", "cp other.mp4 refs/a.mp4"), ("Bash", "ffmpeg -y -i refs/a.mp4 -c copy refs/a.mp4"),
           ("Bash", "ffmpeg -i x.mp4 -y \"projects/zz/clip.mp4\""), ("Bash", "sed -i s/a/b/ refs/downloads.json"),
           ("PowerShell", "Copy-Item x.mp4 refs\\a.mp4 -Force"), ("PowerShell", "Set-Content refs\\downloads.json \"{}\""),
           ("PowerShell", "\"{}\" | Out-File refs\\downloads.json"), ("Bash", "tee refs/x.txt < a.txt"),
           ("Bash", "python -c \"open('refs/a.mp4','wb').write(b'')\""),
           ("Bash", "python -c \"from pathlib import Path; Path('refs/a.mp4').write_bytes(b'')\""),
           ("Bash", "rm a.mp4", "C:/MotionLab/refs"), ("Bash", "echo x > notes.txt", "C:\\MotionLab\\projects\\zz"),
           ("Bash", "cp /tmp/new.mp4 .", "C:/MotionLab/refs/audio"), ("Bash", "robocopy C:/x refs /MIR"),
           ("Bash", "pushd refs; touch a.mp4")]
    # a lab that lives in a folder called "projects": read from the lab's own folder on
    deep_no = [("Write", "D:/projects/MotionLab/docs/plans.md"), ("Bash", "rm D:/projects/MotionLab/analysis/a/tmp.txt"),
               ("Bash", "rm tmp.txt", "D:\\projects\\MotionLab\\tools"), ("Write", "D:\\projects\\MotionLab\\CLAUDE.md")]
    deep_yes = [("Bash", "rm D:/projects/MotionLab/refs/a.mp4"), ("Write", "D:/projects/MotionLab/projects/zz/a.txt"),
                ("Bash", "rm clip.mp4", "D:/projects/MotionLab/projects/zz")]
    bad, n = 0, 0
    for lab, want, cases in (("C:\\MotionLab", False, no), ("C:\\MotionLab", True, yes),
                             ("D:\\projects\\MotionLab", False, deep_no), ("D:\\projects\\MotionLab", True, deep_yes)):
        LAB = lab
        for tool, arg, *cwd in cases:
            key = "command" if tool in ("Bash", "PowerShell") else "file_path"
            got = bool(check({"tool_name": tool, "tool_input": {key: arg}, "cwd": cwd[0] if cwd else lab}))
            n += 1
            if got != want:
                bad += 1
                print(f"FAIL {'refused' if got else 'allowed'}: {tool} {arg}" + (f"  (in {cwd[0]})" if cwd else ""))
    print(f"guard_sources selfcheck: {n - bad}/{n} PASS")
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
