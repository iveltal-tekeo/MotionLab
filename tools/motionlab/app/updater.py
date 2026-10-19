"""Updates from GitHub and sharing knowledge through it - plain git (Git for Windows), no GitHub API and no tokens in
the app: the repo this copy was cloned from ('origin') is the hub. Git asks for a login itself (Git Credential
Manager, in the browser) the first time something is pushed.

  check()   git fetch; how many commits behind / ahead, local changes, the new version, what kind of update it is
            ("version" = a newer MotionLab, "knowledge" = only friends' cards / lessons, "changes" = anything else)
            and every CHANGELOG section newer than this copy (the Update button's dialog shows them)
            Updates come from the branch "tested" when the repo has it: GitHub's tests (.github/workflows/tests.yml)
            move it to each push to main that passed, so a broken push never reaches the Update button. Without it
            (a repo without the workflow, another branch) they come from origin/<branch> as before.
  apply()   git pull --rebase --autostash (your knowledge commits and settings stay), pip install if
            requirements.txt changed; the caller restarts the app when code changed. A local change that clashes
            with the update (e.g. a threshold Claude tuned in config.json that the update changes too) is set aside in
            git's stash and the file gets the new version - the app never runs on a file with conflict markers.
            The result (.app\\update_last.json) carries the CHANGELOG sections that came in: the restarted window
            shows them once ("What's new"), then mark_seen()
  share()   commit the staged knowledge files and push them (on failure everything is put back as it was)
  connect() turn a ZIP copy into a git checkout of a repo (so updates and sharing work): the tested commit on a local
            main when the repo has the branch "tested" - what the Update button would install (Install-MotionLab.cmd
            does the same for a new clone and calls connect() for a ZIP copy; Settings > Connect to GitHub too)
In Spanish (Settings > Language, 0.5.1) What's new comes from CHANGELOG.es.md: a version that file has shows in its
words, the others in English (whats_new / translated / in_language); its own messages follow the language too."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from motionlab import i18n as I18N
from motionlab.util import LAB

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
CACHE = LAB / ".app" / "update.json"
LAST = LAB / ".app" / "update_last.json"                 # the last apply(), shown by the restarted app
KNOWLEDGE_PATHS = ("knowledge/references", "knowledge/incoming", ".claude/skills/analyze-reference/lessons.md",
                   ".claude/skills/recreate-video/lessons.md")    # analysis lessons L###, lessons on making videos M###
GATE = "tested"                                          # the branch GitHub's tests move forward (tests.yml)
HOME_REPO = "https://github.com/iveltal-tekeo/MotionLab"  # Settings > Connect to GitHub starts with it (2026-10-18)
NO_GIT = "git is not installed (needed for updates and sharing) - double-click setup.bat in the MotionLab folder: " \
         "it installs git and connects this copy"


class GitError(RuntimeError):
    pass


def git_exe() -> str | None:
    exe = shutil.which("git")
    if exe:
        return exe
    for p in (Path(r"C:\Program Files\Git\cmd\git.exe"), Path(r"C:\Program Files (x86)\Git\cmd\git.exe")):
        if p.is_file():
            return str(p)
    return None


def git(*args: str, timeout: float = 60, check: bool = True, cwd: Path = LAB) -> str:
    exe = git_exe()
    if not exe:
        raise GitError(I18N.t(NO_GIT))
    r = subprocess.run([exe, *args], cwd=str(cwd), capture_output=True, text=True, timeout=timeout,
                       creationflags=NO_WINDOW, encoding="utf-8", errors="replace",
                       env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "auto"})
    if check and r.returncode != 0:
        raise GitError((r.stderr or r.stdout).strip()[-600:] or I18N.t("git {args} failed", args=" ".join(args)))
    return r.stdout.strip()


def is_repo(root: Path = LAB) -> bool:
    return (root / ".git").exists() and bool(git_exe())


def _branch() -> str:
    b = git("rev-parse", "--abbrev-ref", "HEAD")
    return "main" if b == "HEAD" else b


def _upstream(br: str) -> str:
    """Where updates come from: origin/tested (the newest push to main that passed GitHub's tests) when the repo has
    that branch and this copy follows main, else origin/<branch>. Pushes (Share) always go to origin/<branch>."""
    if br == "main" and git("rev-parse", "-q", "--verify", f"refs/remotes/origin/{GATE}", check=False):
        return f"origin/{GATE}"
    return f"origin/{br}"


def _remote() -> str | None:
    try:
        return git("remote", "get-url", "origin") or None
    except GitError:
        return None


def _version_of(text: str) -> str | None:
    m = re.search(r'__version__\s*=\s*"([^"]+)"', text or "")
    return m.group(1) if m else None


def vtuple(v: str | None) -> tuple[int, ...]:
    """'0.2.5' -> (0, 2, 5) for comparing versions (missing parts count as 0)."""
    t = [int(x) for x in re.findall(r"\d+", v or "")[:4]]
    return tuple(t + [0] * (4 - len(t)))


def releases(changelog: str) -> list[dict]:
    """The CHANGELOG's version sections, newest first: `## 0.2.5 - 2026-10-07 - title` -> version, heading, body."""
    text = (changelog or "").replace("\r", "")
    heads = list(re.finditer(r"(?m)^## +(\d+(?:\.\d+){1,3})\b.*$", text))
    return [{"version": m.group(1), "heading": m.group(0)[3:].strip(),
             "body": text[m.end():heads[i + 1].start() if i + 1 < len(heads) else len(text)].strip()}
            for i, m in enumerate(heads)]


def whats_new(changelog: str, after: str | None, upto: str | None = None, local: str | None = None) -> str:
    """Markdown of every CHANGELOG section newer than version `after` (and not newer than `upto`), newest first.
    local = the same CHANGELOG in the app's language (CHANGELOG.es.md): a version it has comes in its words, the
    others in English - the versions and their order are always CHANGELOG.md's."""
    tr = {r["version"]: r for r in releases(local)} if local else {}
    keep = [tr.get(r["version"], r) for r in releases(changelog) if vtuple(r["version"]) > vtuple(after)
            and (upto is None or vtuple(r["version"]) <= vtuple(upto))]
    return "\n\n".join(f"## {r['heading']}\n\n{r['body']}" for r in keep)[:30000]


def changelog_name(lg: str) -> str:
    """CHANGELOG.md, or its translation (CHANGELOG.es.md since 0.5.1: the same `## x.y.z - date - title` headings in
    that language, from 0.5.1 on - the older notes stay in CHANGELOG.md)."""
    return "CHANGELOG.md" if lg == "en" else f"CHANGELOG.{lg}.md"


def local_changelog(lg: str) -> str | None:
    """This copy's CHANGELOG in language lg ("" when there is none); None for English (nothing to lay over it)."""
    return None if lg == "en" else _read(LAB / changelog_name(lg))


def _changelog_at(ref: str, lg: str) -> str | None:
    """The same at a git ref - the update's source (a missing file = "")."""
    return None if lg == "en" else git("show", f"{ref}:{changelog_name(lg)}", check=False)


def translated(changelog: str, local: str | None) -> str:
    """CHANGELOG.md for the sidebar's What's new in the app's language: each version section the translation has, in
    its words (heading and body); the other versions, the opening lines and ## Unreleased as they are."""
    tr = {r["version"]: r for r in releases(local)} if local else {}
    if not tr:
        return changelog
    text = (changelog or "").replace("\r", "")
    heads = list(re.finditer(r"(?m)^## +(\d+(?:\.\d+){1,3})\b.*$", text))
    out, at = [], 0
    for i, m in enumerate(heads):
        r = tr.get(m.group(1))
        if r:
            out += [text[at:m.start()], f"## {r['heading']}\n\n{r['body']}\n\n"]
            at = heads[i + 1].start() if i + 1 < len(heads) else len(text)
    return "".join(out) + text[at:]


def in_language(rec: dict | None) -> dict | None:
    """A check() or update record with its What's new in the app's language when it was written in another one
    (Settings > Language changed since, or Claude's knowledge.py share wrote it in English): made again from the same
    CHANGELOG sections - a check from the update's source (git show, no fetch), an update / a share from this copy."""
    lg = I18N.lang()
    if not rec or not rec.get("whats_new") or rec.get("lang", "en") == lg:
        return rec
    try:
        if rec.get("source") and "behind" in rec:
            text = whats_new(git("show", f"{rec['source']}:CHANGELOG.md", check=False), rec.get("version"),
                             local=_changelog_at(rec["source"], lg))
        elif rec.get("from_version") and rec.get("version"):
            text = whats_new(_read(LAB / "CHANGELOG.md"), rec["from_version"], rec["version"],
                             local=local_changelog(lg))
        else:
            return rec
    except (GitError, subprocess.TimeoutExpired, OSError):
        return rec
    return {**rec, "whats_new": text, "lang": lg}


def _is_knowledge(path: str) -> bool:
    return any(path == k or path.startswith(k + "/") for k in KNOWLEDGE_PATHS)


def _incoming(a: str, b: str) -> dict:
    """What commits a..b bring: changed files, whether only knowledge changed, new cards / lessons waiting for review."""
    files = git("diff", "--name-only", a, b, check=False).splitlines()
    added = git("diff", "--name-only", "--diff-filter=A", a, b, check=False).splitlines()
    return {"files": files, "knowledge_only": bool(files) and all(_is_knowledge(f) for f in files),
            "new_cards": sum(f.startswith("knowledge/references/") and f.endswith(".json") for f in added),
            "new_lessons": sum(f.startswith("knowledge/incoming/") and f.endswith(".md") for f in added),
            "lessons_changed": any(f in files for f in KNOWLEDGE_PATHS[2:])}


def local_version() -> str:
    from motionlab import __version__
    return __version__


def check(fetch: bool = True) -> dict:
    """Where this copy stands against GitHub (cached in .app\\update.json); its words in the app's language."""
    lg = I18N.lang()
    out = {"checked": time.strftime("%Y-%m-%d %H:%M"), "version": local_version(), "disk_version": disk_version(),
           "git": bool(git_exe()),
           "repo": is_repo(), "remote": None, "branch": None, "behind": 0, "ahead": 0, "dirty": [], "new_version": None,
           "source": None, "testing": 0,
           "changes": [], "whats_new": "", "kind": None, "files": 0, "new_cards": 0, "new_lessons": 0,
           "error": None, "can_update": False, "lang": lg}
    if not out["git"]:
        out["error"] = I18N.t(NO_GIT)
    elif not out["repo"]:
        out["error"] = I18N.t("this copy is not connected to GitHub (it was not installed with git clone)")
    else:
        try:
            out["remote"] = _remote()
            out["branch"] = br = _branch()
            if not out["remote"]:
                out["error"] = I18N.t("no GitHub repo set for this copy (git remote 'origin')")
            else:
                if fetch:
                    git("fetch", "--quiet", "origin", timeout=60)
                git("rev-parse", "--verify", f"origin/{br}")
                out["source"] = up = _upstream(br)
                out["behind"] = int(git("rev-list", "--count", f"HEAD..{up}") or 0)
                out["ahead"] = int(git("rev-list", "--count", f"origin/{br}..HEAD") or 0)     # not on GitHub yet
                if up != f"origin/{br}":                     # newer pushes that have not passed the tests (yet)
                    out["testing"] = int(git("rev-list", "--count", f"{up}..origin/{br}") or 0)
                out["dirty"] = git("diff", "--name-only", "HEAD").splitlines()[:30]
                if out["behind"]:
                    nv = out["new_version"] = _version_of(git("show", f"{up}:tools/motionlab/__init__.py", check=False))
                    out["changes"] = git("log", "--format=%s", f"HEAD..{up}", "-n", "30").splitlines()
                    out["whats_new"] = whats_new(git("show", f"{up}:CHANGELOG.md", check=False), out["version"],
                                                 local=_changelog_at(up, lg))
                    inc = _incoming(git("merge-base", "HEAD", up), up)          # what the update brings
                    out.update(files=len(inc["files"]), new_cards=inc["new_cards"], new_lessons=inc["new_lessons"])
                    out["kind"] = ("version" if nv and vtuple(nv) > vtuple(out["version"]) else
                                   "knowledge" if inc["knowledge_only"] else "changes")
                out["can_update"] = out["behind"] > 0
        except (GitError, subprocess.TimeoutExpired, ValueError) as e:
            out["error"] = I18N.t("could not check GitHub: {error}", error=e)
    out["restart_needed"] = bool(out["disk_version"] and out["disk_version"] != out["version"])
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def cached() -> dict:
    """The last check, re-judged for THIS process (another process may have written it before or after an update)."""
    try:
        out = json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out["version"], out["disk_version"] = local_version(), disk_version()
    out["restart_needed"] = bool(out["disk_version"] and out["disk_version"] != out["version"])
    return in_language(out)


def apply() -> dict:
    """Pull the new version. Local knowledge commits and changed files are kept (rebase + autostash); if that
    cannot be done cleanly nothing changes. Installs Python packages when requirements.txt changed."""
    if not is_repo():
        raise GitError(I18N.t("this copy is not connected to GitHub"))
    br = _branch()
    old = git("rev-parse", "HEAD")
    old_version = disk_version()
    try:
        set_aside = _pull(_upstream(br).removeprefix("origin/"))
    except (GitError, subprocess.TimeoutExpired) as e:
        git("rebase", "--abort", check=False)
        raise GitError(I18N.t("the update could not be applied cleanly, nothing was changed: {error}", error=e))
    new = git("rev-parse", "HEAD")
    changed = git("diff", "--name-only", old, new).splitlines() if old != new else []
    pip = install_requirements() if "requirements.txt" in changed else None
    npm = install_overlays() if "tools/overlays/package-lock.json" in changed else None
    check(fetch=False)
    version = disk_version()
    inc = _incoming(old, new) if old != new else {"new_cards": 0, "new_lessons": 0}
    lg = I18N.lang()
    out = {"updated": old != new, "from": old[:7], "to": new[:7], "changed": changed[:80], "pip": pip, "npm": npm,
           "set_aside": set_aside, "when": time.time(), "version": version, "from_version": old_version,
           "code_changed": any(not _is_knowledge(f) for f in changed),
           "new_cards": inc["new_cards"], "new_lessons": inc["new_lessons"], "seen": False, "lang": lg,
           "whats_new": whats_new(_read(LAB / "CHANGELOG.md"), old_version, version, local=local_changelog(lg))
           if version != old_version else ""}
    if out["updated"]:
        LAST.parent.mkdir(exist_ok=True)
        LAST.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


def _pull(br: str) -> list[str]:
    """git pull --rebase --autostash from origin's branch `br`; returns the files whose local changes clashed with
    what came in. When the autostash cannot be put back cleanly git leaves conflict markers in those files (and
    keeps the changes in its stash, "autostash"): give them the version from GitHub, so the lab never runs on a
    half-merged file."""
    git("pull", "--rebase", "--autostash", "origin", br, timeout=300)
    clashed = git("diff", "--name-only", "--diff-filter=U").splitlines()
    if clashed:
        git("checkout", "HEAD", "--", *clashed)
    return clashed


def last_result(max_age: float = 900) -> dict | None:
    """The last update, for the window after the restart: the Home banner for 15 minutes, the "What's new" dialog
    until the user has seen it (at most a week)."""
    try:
        r = json.loads(LAST.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    age = time.time() - float(r.get("when", 0))
    if "seen" not in r:                  # written by MotionLab 0.2.x while updating itself to this version
        return in_language(_complete_old(r)) if age < max_age else None
    return in_language(r) if age < max_age or (not r["seen"] and age < 7 * 86400) else None


def _complete_old(r: dict) -> dict:
    """A 0.2.x record lacks the version it came from and the changelog: add both (from git and CHANGELOG.md)."""
    try:
        frm = _version_of(git("show", f"{r['from']}:tools/motionlab/__init__.py", check=False)) if r.get("from") else None
    except (GitError, subprocess.TimeoutExpired, OSError):
        frm = None
    ver = r.get("version") or disk_version()
    lg = I18N.lang()
    return {**r, "from_version": frm, "version": ver, "seen": False, "code_changed": True, "lang": lg,
            "whats_new": whats_new(_read(LAB / "CHANGELOG.md"), frm, ver, local=local_changelog(lg))
            if frm and ver and frm != ver else ""}


def mark_seen() -> None:
    """The window has shown "What's new": don't show it again."""
    try:
        r = json.loads(LAST.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if "seen" not in r:
        r = _complete_old(r)
    r["seen"] = True
    LAST.write_text(json.dumps(r, indent=1), encoding="utf-8")


def install_requirements() -> str:
    """pip install -r requirements.txt into the lab's .venv (after an update changed it)."""
    py = LAB / ".venv" / "Scripts" / "python.exe"
    r = subprocess.run([str(py if py.exists() else sys.executable), "-m", "pip", "install", "--disable-pip-version-check",
                        "-q", "-r", str(LAB / "requirements.txt")], capture_output=True, text=True, timeout=1800,
                       creationflags=NO_WINDOW)
    return "ok" if r.returncode == 0 else (r.stderr or r.stdout)[-400:]


def install_overlays() -> str | None:
    """npm ci in tools\\overlays after an update changed the pinned HyperFrames / GSAP versions - only where they are
    installed (setup.bat's optional step); None = not installed here."""
    d = LAB / "tools" / "overlays"
    npm = shutil.which("npm")
    if not npm or not (d / "node_modules").exists():
        return None
    env = {**os.environ, "HYPERFRAMES_NO_TELEMETRY": "1", "DO_NOT_TRACK": "1", "HYPERFRAMES_SKIP_SKILLS": "1"}
    r = subprocess.run([npm, "ci", "--no-fund", "--no-audit"], cwd=str(d), capture_output=True, text=True,
                       timeout=1800, creationflags=NO_WINDOW, encoding="utf-8", errors="replace", env=env)
    if r.returncode:
        return (r.stderr or r.stdout)[-400:]
    hf, node = d / "node_modules" / "hyperframes" / "bin" / "hyperframes.mjs", shutil.which("node")
    if hf.exists() and node:                     # a newer HyperFrames may want a newer Chrome (no-op when present)
        b = subprocess.run([node, str(hf), "browser", "ensure"], cwd=str(d), capture_output=True, text=True,
                           timeout=1800, creationflags=NO_WINDOW, encoding="utf-8", errors="replace", env=env)
        if b.returncode:
            return "npm ci ok, but HyperFrames' Chrome: " + (b.stderr or b.stdout)[-300:]
    return "ok"


def disk_version() -> str | None:
    """The version of the files on disk - newer than the running app after an update that has not restarted yet."""
    try:
        return _version_of((LAB / "tools" / "motionlab" / "__init__.py").read_text(encoding="utf-8"))
    except OSError:
        return None


def _identity(who: str) -> None:
    """Commits need a name: set it for this repo only if git has none."""
    if not git("config", "user.name", check=False):
        git("config", "user.name", who)
    if not git("config", "user.email", check=False):
        git("config", "user.email", f"{who}@motionlab.local")


def share(files: list[Path], who: str, message: str) -> dict:
    """Commit the given knowledge files (+ changes to the shared knowledge paths) and push them to origin. If the
    push fails (no access, offline), the commit is undone and the new files are removed again, so nothing is left
    half-shared; the caller then offers the pack file instead."""
    if not is_repo():
        raise GitError(I18N.t("this copy is not connected to GitHub"))
    if not _remote():
        raise GitError(I18N.t("no GitHub repo set for this copy"))
    _identity(who)
    br = _branch()
    rels = [str(p.relative_to(LAB)).replace("\\", "/") for p in files]
    new_files = [p for p in files if not git("ls-files", str(p.relative_to(LAB)), check=False)]
    try:                                                     # a push sends every local commit: only share alone
        ahead = int(git("rev-list", "--count", f"origin/{br}..HEAD") or 0)
    except (GitError, ValueError):
        ahead = -1
    if ahead:
        for p in new_files:
            if p.exists():
                p.unlink()
        raise GitError(I18N.t("this copy is not on GitHub yet (no origin/{branch}) - push it first", branch=br)
                       if ahead < 0 else
                       I18N.tn(ahead, "this copy has {n} commit(s) that are not on GitHub yet (work in progress?) - "
                                      "push them first, then share again (the pack file can be sent meanwhile)",
                               "this copy has {n} commit(s) that are not on GitHub yet (work in progress?) - push them "
                               "first, then share again (the pack file can be sent meanwhile)"))
    paths = rels + [k for k in KNOWLEDGE_PATHS if (LAB / k).exists()]
    git("add", "--", *paths)
    if not git("diff", "--cached", "--name-only", "--", *paths):
        return {"pushed": False, "nothing": True}
    git("commit", "-m", message, "--", *paths)
    pulled: list[str] = []
    set_aside: list[str] = []
    try:
        try:
            git("push", "origin", f"HEAD:{br}", timeout=600)
        except GitError as e:
            if not re.search(r"rejected|fetch first|non-fast-forward", str(e)):
                raise
            mine = git("rev-parse", "HEAD")
            set_aside = _pull(br)                                                # others shared first: go on top
            pulled = git("diff", "--name-only", mine, "HEAD").splitlines()       # what came in from GitHub
            git("push", "origin", f"HEAD:{br}", timeout=600)
        if "requirements.txt" in pulled:
            install_requirements()
        out = {"pushed": True, "commit": git("rev-parse", "--short", "HEAD"), "branch": br, "remote": _remote(),
               "pulled": pulled, "set_aside": set_aside,
               "code_updated": any(not f.startswith(("knowledge/", ".claude/skills/")) for f in pulled)}
        if out["code_updated"]:
            frm = _version_of(git("show", f"{mine}:tools/motionlab/__init__.py", check=False))
            ver = disk_version()
            lg = I18N.lang()
            LAST.parent.mkdir(exist_ok=True)
            LAST.write_text(json.dumps({"updated": True, "from": mine[:7], "to": out["commit"], "changed": pulled[:80],
                                        "pip": None, "set_aside": set_aside, "when": time.time(), "version": ver,
                                        "from_version": frm, "code_changed": True, "new_cards": 0, "new_lessons": 0,
                                        "seen": False, "lang": lg,
                                        "whats_new": whats_new(_read(LAB / "CHANGELOG.md"), frm, ver,
                                                               local=local_changelog(lg))
                                        if frm and ver and frm != ver else ""}, indent=1), encoding="utf-8")
        return out
    except (GitError, subprocess.TimeoutExpired) as e:
        git("rebase", "--abort", check=False)
        if git("log", "-1", "--format=%s", check=False) == message:          # undo only this share's commit
            git("reset", "--mixed", "HEAD~1", check=False)
        for p in new_files:
            if p.exists():
                p.unlink()
        return {"pushed": False, "error": str(e)}


def connect(url: str, local: bool = False) -> dict:
    """Make a ZIP copy a git checkout of `url` (updates + sharing). Only the app's own files (tracked in the repo)
    are replaced by the repo's version; your videos, analyses, settings and local knowledge are not touched.
    It starts from what the Update button installs (`_upstream`): the branch "tested" checked out as a LOCAL main
    that follows origin/main (so updates keep coming from tested and Share pushes to main), else the default branch.
    local=True (the installer's tests only, never the Settings page): `url` may also be a local repo folder."""
    url = url.strip()
    if not (re.fullmatch(r"https://github\.com/[\w.-]+/[\w.-]+?(\.git)?/?", url) or (local and Path(url).is_dir())):
        raise ValueError(I18N.t("paste the repo address, e.g. {example}", example=HOME_REPO))
    if is_repo():
        raise GitError(I18N.t("this copy is already connected to {remote}", remote=_remote() or I18N.t("a git repo")))
    git("init", "-q")
    git("remote", "add", "origin", url)
    git("fetch", "--quiet", "origin", timeout=300)
    head = git("ls-remote", "--symref", "origin", "HEAD", timeout=60)
    m = re.search(r"ref: refs/heads/(\S+)\s+HEAD", head)
    br = m.group(1) if m else "main"
    start = _upstream(br)                                    # origin/tested when the repo has it (br == main)
    git("checkout", "-q", "-B", br, start, "--force", timeout=120)
    git("branch", "--set-upstream-to", f"origin/{br}", check=False)
    return {"connected": True, "remote": url, "branch": br, "source": start,
            "head": git("rev-parse", "--short", "HEAD")}


def selfcheck() -> list[str]:
    """Known answers without git (jobtools selfcheck - the self-test - runs it): What's new takes a version's section
    from the translation when it has that version and the English one otherwise; the sidebar's What's new likewise."""
    en = ("# Changelog\n\n## Unreleased\n\n- soon\n\n## 0.5.2 - 2026-11-01 - Two\n\n- two\n\n"
          "## 0.5.1 - 2026-10-19 - One\n\n- one\n")
    es = "Las notas anteriores están en CHANGELOG.md.\n\n## 0.5.1 - 2026-10-19 - Uno\n\n- uno\n"
    bad = []
    if whats_new(en, "0.5.0", local=es) != "## 0.5.2 - 2026-11-01 - Two\n\n- two\n\n## 0.5.1 - 2026-10-19 - Uno\n\n- uno":
        bad.append("whats_new: 0.5.1 from the translation, 0.5.2 (not in it) in English")
    if whats_new(en, "0.5.0", local="") != whats_new(en, "0.5.0") or not whats_new(en, "0.5.0").endswith("- one"):
        bad.append("whats_new: without a translation the English sections")
    t = translated(en, es)
    if [r["heading"] for r in releases(t)] != ["0.5.2 - 2026-11-01 - Two", "0.5.1 - 2026-10-19 - Uno"] \
            or "- soon" not in t or translated(en, None) != en:
        bad.append("translated: CHANGELOG.md with the translation's sections, the rest as it is")
    return bad
