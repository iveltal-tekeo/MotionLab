"""Updates from GitHub and sharing knowledge through it - plain git (Git for Windows), no GitHub API and no tokens in
the app: the repo this copy was cloned from ('origin') is the hub. Git asks for a login itself (Git Credential
Manager, in the browser) the first time something is pushed.

  check()   git fetch; how many commits behind / ahead, local changes, the new version and its changelog
  apply()   git pull --rebase --autostash (your knowledge commits and settings stay), pip install if
            requirements.txt changed; the caller restarts the app. A local change that clashes with the update
            (e.g. a threshold Claude tuned in config.json that the update changes too) is set aside in git's stash
            and the file gets the new version - the app never runs on a file with conflict markers
  share()   commit the staged knowledge files and push them (on failure everything is put back as it was)
  connect() turn a ZIP copy into a git checkout of a repo (so updates and sharing work)"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from motionlab.util import LAB

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
CACHE = LAB / ".app" / "update.json"
LAST = LAB / ".app" / "update_last.json"                 # the last apply(), shown by the restarted app
KNOWLEDGE_PATHS = ("knowledge/references", "knowledge/incoming", ".claude/skills/analyze-reference/lessons.md")


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
        raise GitError("git is not installed - winget install Git.Git (or https://git-scm.com)")
    r = subprocess.run([exe, *args], cwd=str(cwd), capture_output=True, text=True, timeout=timeout,
                       creationflags=NO_WINDOW, encoding="utf-8", errors="replace",
                       env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "auto"})
    if check and r.returncode != 0:
        raise GitError((r.stderr or r.stdout).strip()[-600:] or f"git {' '.join(args)} failed")
    return r.stdout.strip()


def is_repo(root: Path = LAB) -> bool:
    return (root / ".git").exists() and bool(git_exe())


def _branch() -> str:
    b = git("rev-parse", "--abbrev-ref", "HEAD")
    return "main" if b == "HEAD" else b


def _remote() -> str | None:
    try:
        return git("remote", "get-url", "origin") or None
    except GitError:
        return None


def _version_of(text: str) -> str | None:
    m = re.search(r'__version__\s*=\s*"([^"]+)"', text or "")
    return m.group(1) if m else None


def _whats_new(changelog: str) -> str:
    parts = re.split(r"(?m)^## ", changelog or "")
    return ("## " + parts[1]).strip()[:4000] if len(parts) > 1 else ""


def local_version() -> str:
    from motionlab import __version__
    return __version__


def check(fetch: bool = True) -> dict:
    """Where this copy stands against GitHub (cached in .app\\update.json)."""
    out = {"checked": time.strftime("%Y-%m-%d %H:%M"), "version": local_version(), "disk_version": disk_version(),
           "git": bool(git_exe()),
           "repo": is_repo(), "remote": None, "branch": None, "behind": 0, "ahead": 0, "dirty": [], "new_version": None,
           "changes": [], "whats_new": "", "error": None, "can_update": False}
    if not out["git"]:
        out["error"] = "git is not installed (needed for updates and sharing): winget install Git.Git"
    elif not out["repo"]:
        out["error"] = "this copy is not connected to GitHub (it was not installed with git clone)"
    else:
        try:
            out["remote"] = _remote()
            out["branch"] = br = _branch()
            if not out["remote"]:
                out["error"] = "no GitHub repo set for this copy (git remote 'origin')"
            else:
                if fetch:
                    git("fetch", "--quiet", "origin", timeout=60)
                up = f"origin/{br}"
                git("rev-parse", "--verify", up)
                out["behind"] = int(git("rev-list", "--count", f"HEAD..{up}") or 0)
                out["ahead"] = int(git("rev-list", "--count", f"{up}..HEAD") or 0)
                out["dirty"] = git("diff", "--name-only", "HEAD").splitlines()[:30]
                if out["behind"]:
                    out["new_version"] = _version_of(git("show", f"{up}:tools/motionlab/__init__.py", check=False))
                    out["changes"] = git("log", "--format=%s", f"HEAD..{up}", "-n", "30").splitlines()
                    out["whats_new"] = _whats_new(git("show", f"{up}:CHANGELOG.md", check=False))
                out["can_update"] = out["behind"] > 0
        except (GitError, subprocess.TimeoutExpired, ValueError) as e:
            out["error"] = f"could not check GitHub: {e}"
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
    return out


def apply() -> dict:
    """Pull the new version. Local knowledge commits and changed files are kept (rebase + autostash); if that
    cannot be done cleanly nothing changes. Installs Python packages when requirements.txt changed."""
    if not is_repo():
        raise GitError("this copy is not connected to GitHub")
    br = _branch()
    old = git("rev-parse", "HEAD")
    try:
        set_aside = _pull(br)
    except (GitError, subprocess.TimeoutExpired) as e:
        git("rebase", "--abort", check=False)
        raise GitError(f"the update could not be applied cleanly, nothing was changed: {e}")
    new = git("rev-parse", "HEAD")
    changed = git("diff", "--name-only", old, new).splitlines() if old != new else []
    pip = install_requirements() if "requirements.txt" in changed else None
    check(fetch=False)
    out = {"updated": old != new, "from": old[:7], "to": new[:7], "changed": changed[:80], "pip": pip,
           "set_aside": set_aside, "when": time.time(),
           "version": _version_of((LAB / "tools" / "motionlab" / "__init__.py").read_text(encoding="utf-8"))}
    if out["updated"]:
        LAST.parent.mkdir(exist_ok=True)
        LAST.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def _pull(br: str) -> list[str]:
    """git pull --rebase --autostash; returns the files whose local changes clashed with what came in. When the
    autostash cannot be put back cleanly git leaves conflict markers in those files (and keeps the changes in its
    stash, "autostash"): give them the version from GitHub, so the lab never runs on a half-merged file."""
    git("pull", "--rebase", "--autostash", "origin", br, timeout=300)
    clashed = git("diff", "--name-only", "--diff-filter=U").splitlines()
    if clashed:
        git("checkout", "HEAD", "--", *clashed)
    return clashed


def last_result(max_age: float = 900) -> dict | None:
    """The last update, for the window after the restart (shown for 15 minutes)."""
    try:
        r = json.loads(LAST.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return r if time.time() - float(r.get("when", 0)) < max_age else None


def install_requirements() -> str:
    """pip install -r requirements.txt into the lab's .venv (after an update changed it)."""
    py = LAB / ".venv" / "Scripts" / "python.exe"
    r = subprocess.run([str(py if py.exists() else sys.executable), "-m", "pip", "install", "--disable-pip-version-check",
                        "-q", "-r", str(LAB / "requirements.txt")], capture_output=True, text=True, timeout=1800,
                       creationflags=NO_WINDOW)
    return "ok" if r.returncode == 0 else (r.stderr or r.stdout)[-400:]


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
        raise GitError("this copy is not connected to GitHub")
    if not _remote():
        raise GitError("no GitHub repo set for this copy")
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
        raise GitError(f"this copy is not on GitHub yet (no origin/{br}) - push it first" if ahead < 0 else
                       f"this copy has {ahead} commit(s) that are not on GitHub yet (work in progress?) - push "
                       "them first, then share again (the pack file can be sent meanwhile)")
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
            LAST.parent.mkdir(exist_ok=True)
            LAST.write_text(json.dumps({"updated": True, "from": mine[:7], "to": out["commit"], "changed": pulled[:80],
                                        "pip": None, "set_aside": set_aside, "when": time.time(),
                                        "version": disk_version()}, indent=1), encoding="utf-8")
        return out
    except (GitError, subprocess.TimeoutExpired) as e:
        git("rebase", "--abort", check=False)
        if git("log", "-1", "--format=%s", check=False) == message:          # undo only this share's commit
            git("reset", "--mixed", "HEAD~1", check=False)
        for p in new_files:
            if p.exists():
                p.unlink()
        return {"pushed": False, "error": str(e)}


def connect(url: str) -> dict:
    """Make a ZIP copy a git checkout of `url` (updates + sharing). Only the app's own files (tracked in the repo)
    are replaced by the repo's version; your videos, analyses, settings and local knowledge are not touched."""
    url = url.strip()
    if not re.fullmatch(r"https://github\.com/[\w.-]+/[\w.-]+?(\.git)?/?", url):
        raise ValueError("paste the repo address, e.g. https://github.com/name/MotionLab")
    if is_repo():
        raise GitError("this copy is already connected to " + (_remote() or "a git repo"))
    git("init", "-q")
    git("remote", "add", "origin", url)
    git("fetch", "--quiet", "origin", timeout=300)
    head = git("ls-remote", "--symref", "origin", "HEAD", timeout=60)
    m = re.search(r"ref: refs/heads/(\S+)\s+HEAD", head)
    br = m.group(1) if m else "main"
    git("checkout", "-q", "-B", br, f"origin/{br}", "--force", timeout=120)
    git("branch", "--set-upstream-to", f"origin/{br}", check=False)
    return {"connected": True, "remote": url, "branch": br, "head": git("rev-parse", "--short", "HEAD")}
