"""The first-install tests (Install-MotionLab.cmd, setup.bat, MotionLab.bat): quick, on this PC, never touching it.

    .venv\\Scripts\\python tools\\dev\\install_test.py [--keep] [case ...]
        cases (default: all, in this order): parse header launcher merge extract dry fake again ask refused zip folder
        --keep = leave the scratch folder for a look (.app\\dev\\install\\)

Everything happens in .app\\dev\\install\\ of this copy (about 2 minutes, most of it pip installing numpy + Pillow
twice into scratch .venvs):
  - a fake winget first on PATH (winget.cmd -> this file's fake-winget): it logs every call, exits with the code
    ML_FAKE_WINGET_RC names for that package ("Git.Git=0x800704C7;...", default 0) and "installs" by adding a folder
    to the test PATH file - the installer's test mode (ML_TEST_PATHFILE), where programs are found only in that
    file's folders. Git and Python are this PC's real ones (the clone and the .venv need them); ffmpeg, Node.js,
    Deno, yt-dlp and the Visual C++ runtime are stubs.
  - a fake GitHub: hub.git = this copy's last commit + its working changes (the installer under test) with a small
    requirements.txt, as main and tested, then one more commit on main - so a clone must end on tested.
  - scratch MotionLab folders with spaces in their names, a scratch Desktop / Start menu, TEMP inside the scratch.
Never a real winget call, never Claude Code's installer (-NoClaude; test mode refuses it anyway), never the real
Desktop, never C:\\MotionLab: the real Desktop / Start-menu shortcuts, C:\\MotionLab's settings and the user PATH
are hashed before and after. The only cases on the real PC's programs are the dry runs (read-only).
The installer speaks English or Spanish (2026-10-19: Windows' language, -Lang en|es): the English cases pass
-Lang en (they hold on a Spanish Windows too); parse / header / dry / ask / zip also check the Spanish window - its
words (UTF-8, read through the console's code page), the language setup.bat writes into a NEW settings.json.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
import unicodedata
import winreg
import zipfile
from pathlib import Path

LAB = Path(__file__).resolve().parents[2]
TOOLS = LAB / "tools"
D = LAB / ".app" / "dev" / "install"
INSTALLER = LAB / "Install-MotionLab.cmd"
SYS32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
TEST_REQUIREMENTS = "numpy==2.5.3\npillow==12.3.0\n"     # what setup.bat /lab's own steps import (MCP approval, shortcuts)
WINGET_FLAGS = ["-e", "--source", "winget", "--silent", "--accept-source-agreements", "--accept-package-agreements",
                "--disable-interactivity"]
FAILED: list[str] = []
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
# a redirected PowerShell writes (and reads typed answers) in the console's code page: the Spanish words come back
# through it (850 on a Spanish or English-UK Windows, 437 US)
OEM = f"cp{ctypes.windll.kernel32.GetOEMCP()}"
EN, ES = ["-Lang", "en"], ["-Lang", "es"]


def ok(cond, what: str, detail: str = "") -> bool:
    print(("PASS " if cond else "FAIL ") + what + ("" if cond or not detail else f"\n     {detail[-1500:]}"), flush=True)
    if not cond:
        FAILED.append(what)
    return bool(cond)


def run(cmd: list[str], env: dict | None = None, cwd: Path | None = None, timeout: int = 420,
        enc: str = "utf-8", typed: str | None = None) -> subprocess.CompletedProcess:
    """enc = how the output is read (OEM for the installer's Spanish words); typed = answers, in that encoding."""
    return subprocess.run([str(c) for c in cmd], env=env, cwd=str(cwd) if cwd else None, capture_output=True,
                          text=True, encoding=enc, errors="replace", timeout=timeout, creationflags=NO_WINDOW,
                          **({"input": typed} if typed is not None else {"stdin": subprocess.DEVNULL}))


def git(*a, cwd: Path | None = None) -> str:
    r = run(["git", "-c", "user.name=installtest", "-c", "user.email=installtest@motionlab.local", *a], cwd=cwd)
    if r.returncode:
        raise SystemExit(f"git {' '.join(map(str, a))}: {r.stderr or r.stdout}")
    return r.stdout.strip()


def sha(p: Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def rmtree(p: Path) -> None:
    def fix(func, path, _exc):                                  # git's read-only object files
        os.chmod(path, stat.S_IWRITE)
        func(path)
    if p.exists():
        assert D in p.parents or p == D, p                      # only ever the scratch folder
        shutil.rmtree(p, onerror=fix)


# ------------------------------------------------------------------------------------------- the real PC (read-only)
def shell_folders() -> dict:
    out = run(["powershell", "-NoProfile", "-Command",
               "[Environment]::GetFolderPath('Desktop'); [Environment]::GetFolderPath('Programs')"]).stdout.splitlines()
    out = [x.strip() for x in out if x.strip()]
    return {"desktop": Path(out[0]) if out else None, "programs": Path(out[1]) if len(out) > 1 else None}


def real_state() -> dict:
    """Hashes of what a test must never change."""
    f = shell_folders()
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
        try:
            user_path = winreg.QueryValueEx(k, "Path")[0]
        except OSError:
            user_path = ""
    real = Path(r"C:\MotionLab")
    return {"desktop shortcut": sha(f["desktop"] / "MotionLab.lnk") if f["desktop"] else None,
            "start-menu shortcut": sha(f["programs"] / "MotionLab.lnk") if f["programs"] else None,
            "C:\\MotionLab\\settings.json": sha(real / "settings.json"),
            "C:\\MotionLab\\.claude\\settings.local.json": sha(real / ".claude" / "settings.local.json"),
            "user PATH": hashlib.sha256(user_path.encode("utf-8")).hexdigest()}


# ----------------------------------------------------------------------------------------- the fake winget + PATH
def fake_winget(argv: list[str]) -> int:
    """Called by the scratch winget.cmd: log the call, exit with its code, 'install' = a folder in the PATH file."""
    with open(os.environ["ML_FAKE_WINGET_LOG"], "a", encoding="utf-8") as f:
        f.write(json.dumps(argv) + "\n")
    if not argv or argv[0] != "install" or "--id" not in argv:
        return 0
    pid = argv[argv.index("--id") + 1]
    rcs = dict(x.split("=", 1) for x in os.environ.get("ML_FAKE_WINGET_RC", "").split(";") if "=" in x)
    rc = int(rcs.get(pid, "0"), 0)
    if rc in (0, 0x8A15002B, 3010):                              # done / already there / done + restart later
        folder = json.loads(os.environ["ML_FAKE_WINGET_DIRS"]).get(pid)
        if folder:
            with open(os.environ["ML_TEST_PATHFILE"], "a", encoding="utf-8") as f:
                f.write(folder + "\n")
    print(f"fake winget: {pid} -> 0x{rc:08X}")
    return rc - (1 << 32) if rc >= 1 << 31 else rc


def write_text_crlf(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(text.replace("\r\n", "\n").replace("\n", "\r\n").encode("ascii"))


def setup_fakes() -> dict:
    """The fake winget, the stub programs and the folders the fake winget 'installs' (real Git + Python)."""
    fake = D / "fakewinget"
    write_text_crlf(fake / "winget.cmd", f'@"{sys.executable}" "{Path(__file__).resolve()}" fake-winget %*\n'
                                         "@exit /b %errorlevel%\n")
    stubs = D / "stubs"
    write_text_crlf(stubs / "node" / "node.cmd", "@echo v24.20.0\n")
    write_text_crlf(stubs / "ffmpeg" / "ffmpeg.cmd", "@echo ffmpeg version 9.0.2-test\n")
    write_text_crlf(stubs / "deno" / "deno.cmd", "@echo deno 2.5.0\n")
    write_text_crlf(stubs / "ytdlp" / "yt-dlp.cmd", "@echo 2026.10.10\n")
    (stubs / "vc").mkdir(parents=True, exist_ok=True)
    (stubs / "vc" / "msvcp140.dll").write_bytes(b"")
    real_git = Path(r"C:\Program Files\Git\cmd")                 # what Git's installer puts on PATH (not mingw64\bin)
    if not (real_git / "git.exe").is_file():
        real_git = Path(shutil.which("git") or "git").parent
    real_py = Path(getattr(sys, "_base_executable", sys.executable)).parent
    dirs = {"Git.Git": str(real_git), "Python.Python.3.12": str(real_py), "Gyan.FFmpeg": str(stubs / "ffmpeg"),
            "OpenJS.NodeJS.LTS": str(stubs / "node"), "DenoLand.Deno": str(stubs / "deno"),
            "yt-dlp.yt-dlp": str(stubs / "ytdlp"), "Microsoft.VCRedist.2015+.x64": str(stubs / "vc")}
    return {"fake": fake, "dirs": dirs}


# set by Git Bash / a Claude Code shell, never by a double-click in Explorer (with them Git's mingw64 git.exe crashed)
SHELL_VARS = {"MSYS", "EXEPATH", "SHELL", "SHLVL", "TERM", "PWD", "OLDPWD", "_", "ORIGINAL_PATH", "ORIGINAL_TEMP",
              "ORIGINAL_TMP", "CHERE_INVOKING", "PLINK_PROTOCOL", "HOME", "GIT_EDITOR", "ACLOCAL_PATH", "PKG_CONFIG_PATH",
              "MANPATH", "INFOPATH", "CONFIG_SITE", "HOSTNAME", "DISPLAY"}


def clean_env() -> dict:
    """This process's environment as a double-click from Explorer would have it (no ML_*, no shell variables)."""
    return {k: v for k, v in os.environ.items()
            if not k.upper().startswith(("ML_", "MSYSTEM", "MINGW_")) and k.upper() not in SHELL_VARS}


def test_env(F: dict, pathfile: Path, log: Path, rc: str = "", ml_args: str = "") -> dict:
    """The installer's test mode: a PATH with only the fake winget + Windows itself, the PATH file, TEMP in the scratch."""
    env = {k: v for k, v in clean_env().items() if k.upper() != "PATH"}
    tmp = D / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    env.update(PATH=";".join(str(p) for p in (F["fake"], SYS32, SYS32 / "Wbem", SYS32 / "WindowsPowerShell" / "v1.0")),
               ML_TEST_PATHFILE=str(pathfile), ML_FAKE_WINGET_LOG=str(log), ML_FAKE_WINGET_DIRS=json.dumps(F["dirs"]),
               ML_FAKE_WINGET_RC=rc, TEMP=str(tmp), TMP=str(tmp))
    if ml_args:
        env["ML_ARGS"] = ml_args
    if not pathfile.exists():
        pathfile.write_text("", encoding="utf-8")
    log.touch()
    return env


def calls(log: Path) -> list[list[str]]:
    return [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()] if log.exists() else []


def ps_quote(p: Path | str) -> str:
    return "'" + str(p).replace("'", "''") + "'"


def head_info(repo: Path) -> dict:
    return {"head": git("rev-parse", "HEAD", cwd=repo), "branch": git("rev-parse", "--abbrev-ref", "HEAD", cwd=repo),
            "upstream": git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}", cwd=repo)}


def word_tables() -> tuple[dict, dict]:
    """The installer's two word tables ($Strings = English, $StringsEs = Spanish) as {key: text}."""
    t = INSTALLER.read_text(encoding="utf-8").replace("\r\n", "\n")

    def table(name: str) -> dict:
        m = re.search(r"^\$" + name + r" = @\{\n(.*?)^\}", t, re.S | re.M)
        return {k: v.replace("''", "'") for k, v in
                re.findall(r"^\s+(\w+)\s+= '((?:[^']|'')*)'\s*$", m.group(1) if m else "", re.M)}
    return table("Strings"), table("StringsEs")


def english_left(out: str) -> list[str]:
    """The keys whose English sentence (Spanish differs) still shows in a Spanish window's text."""
    en, es = word_tables()
    return [k for k, v in en.items() if es.get(k) != v and re.search(
        r"(?<!\w)" + r".*?".join(re.escape(p) for p in re.split(r"\{\d\}", v)) + r"(?!\w)", out)]


# ------------------------------------------------------------------------------------------------------- the cases
def case_parse(ctx):
    ps = (f"$t = [IO.File]::ReadAllText({ps_quote(INSTALLER)}); $e = $null; $k = $null; "
          "[void][System.Management.Automation.Language.Parser]::ParseInput($t, [ref]$k, [ref]$e); "
          "'errors=' + $e.Count; foreach ($x in $e) { 'line ' + $x.Extent.StartLineNumber + ': ' + $x.Message }")
    r = run(["powershell", "-NoProfile", "-Command", ps])
    ok("errors=0" in r.stdout, "the installer's PowerShell parses without errors", r.stdout + r.stderr)
    raw = INSTALLER.read_bytes()
    first = raw.split(b"\n")[:3]
    ok(first[0].startswith(b"<# :") and first[2].strip() == b"#>" and b"call exit /b %%errorlevel%%" in first[1],
       "the batch part is one line between <# and #>, ending in call exit /b %%errorlevel%%")
    # UTF-8 without a BOM since the Spanish words (2026-10-19): cmd reads only the ASCII batch line, PowerShell the
    # rest ([IO.File]::ReadAllText = UTF-8); every line but the Spanish table's stays ASCII
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        text = ""
        ok(False, "the installer is UTF-8", str(e))
    lines = text.replace("\r\n", "\n").split("\n")
    start = next((i for i, x in enumerate(lines) if x.startswith("$StringsEs = @{")), -1)
    end = next((i for i in range(start + 1, len(lines)) if lines[i] == "}"), -1) if start >= 0 else -1
    outside = [i + 1 for i, x in enumerate(lines) if not x.isascii() and not start < i < end]
    first_hi = next((i for i, b in enumerate(raw) if b >= 128), len(raw))
    ok(text and not raw.startswith(b"\xef\xbb\xbf") and start > 0 and not outside and b"\n".join(first).isascii(),
       f"the installer is UTF-8 without a BOM; non-ASCII only in the Spanish table (lines {start + 1}-{end + 1}, the "
       f"first such byte {first_hi:,} bytes in)", f"non-ASCII outside it: lines {outside}")
    ok(unicodedata.is_normalized("NFC", text) and not re.search("[‘-‟]", text),
       "its accents are precomposed (NFC), no curly quotes (PowerShell would read them as quotes)")
    en, es = word_tables()
    ph = lambda s: sorted(re.findall(r"\{\d\}", s))
    ok(en and set(en) == set(es) and all(ph(en[k]) == ph(es[k]) for k in en),
       f"the English and the Spanish table: the same {len(en)} keys, the same {{0}} {{1}} in each",
       f"only English {sorted(set(en) - set(es))}, only Spanish {sorted(set(es) - set(en))}, placeholders differ "
       f"{[k for k in en if k in es and ph(en[k]) != ph(es[k])]}")
    bat = (LAB / "setup.bat").read_bytes()
    halves = bat.decode("ascii", "replace").replace("\r\n", "\n").split('if /i not "%ML_LANG%"=="es" goto :words')
    sets = [dict(re.findall(r'^set "(MLW_\w+)=(.*)"$', h.split("\n:words\n")[0], re.M)) for h in halves]
    ok(bat.isascii() and len(sets) == 2 and sets[0] and set(sets[0]) == set(sets[1])
       and not any(re.search(r"[&|<]|(?<!\^)>", v) for s in sets for v in s.values()),
       f"setup.bat is ASCII (cmd reads it in the console's code page): its {len(sets[0]) if sets else 0} words in "
       "English and in Spanish, none with & | < >", json.dumps(sets)[:1500])


def case_header(ctx):
    """LF and CRLF copies in a folder with a space; a dry run on this PC reaches param() and the folder from ML_ARGS
    arrives whole; a bad parameter's exit code comes back through the batch line."""
    text = INSTALLER.read_bytes().replace(b"\r\n", b"\n")
    env = clean_env()
    env.update(TEMP=str(D / "tmp"), TMP=str(D / "tmp"))
    (D / "tmp").mkdir(parents=True, exist_ok=True)
    target = D / "header lab"
    for kind, data in (("LF", text), ("CRLF", text.replace(b"\n", b"\r\n"))):
        f = D / f"dir with space {kind}" / "Install-MotionLab.cmd"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)
        r = run(["cmd", "/c", f, "-DryRun", "-Yes", "-NoStart", "-NoClaude"],
                env={**env, "ML_ARGS": f"-Folder {ps_quote(target)}"})
        out = r.stdout + r.stderr
        ok(r.returncode == 0 and "MotionLab installer" in out and "Dry run" in out,
           f"{kind}: the header runs from a folder with a space and reaches the dry run (exit {r.returncode})", out)
        ok(str(target) in out, f"{kind}: -Folder with a space arrives whole through ML_ARGS", out)
        ok("would run: setup.bat /lab" in out and "Dry run finished" in out, f"{kind}: the dry run goes to the end", out)
        r2 = run(["cmd", "/c", f, "-DryRun", "-Graphics", "maybe"], env=env)
        ok(r2.returncode != 0, f"{kind}: a failing run's exit code comes back through the batch line "
                               f"(got {r2.returncode})", r2.stdout + r2.stderr)
    ok(not target.exists(), "the dry runs created nothing (no lab folder)")
    ok(not (D / "tmp" / "MotionLab-install.log").exists(), "the dry runs wrote no log")


def case_launcher(ctx):
    """Known answers from this copy's app code (nothing is opened or written)."""
    sys.path.insert(0, str(TOOLS))
    from motionlab.app import system, updater
    fake_find, fake_flags = system.find, system.claude_flags
    system.find = lambda name, s=None: r"C:\Users\José\.local\bin\claude.exe" if name == "claude" else None
    system.claude_flags = lambda exe: ""
    try:
        _clean, text, _e, _m = system.claude_launcher("hello", "free")
    finally:
        system.find, system.claude_flags = fake_find, fake_flags
    lines = text.split("\r\n")
    ok(lines[:2] == ["@echo off", "chcp 65001 >nul"], "the Claude launcher starts with @echo off + chcp 65001 >nul",
       repr(lines[:3]))
    wg = D / "kinds" / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages" / "yt-dlp.yt-dlp_x" / "yt-dlp.exe"
    wg.parent.mkdir(parents=True, exist_ok=True)
    wg.write_bytes(b"")
    cmd = system.install_kind(str(wg))["cmd"]
    ok("--skip-dependencies" in cmd and "upgrade" in cmd, "Update yt-dlp's winget command skips yt-dlp's dependencies",
       repr(cmd))
    ok(updater.HOME_REPO == "https://github.com/iveltal-tekeo/MotionLab", "updater.HOME_REPO is the home repo")
    for bad in (str(D), "https://example.com/x/MotionLab", "ext::sh -c x"):
        try:
            updater.connect(bad)
            ok(False, f"connect refuses {bad!r} from the Settings page")
        except ValueError:
            ok(True, f"connect refuses {bad!r} from the Settings page")
    ok("setup.bat" in system.HOW["git"] and "winget" not in " ".join(system.HOW.values()),
       "the 'how to get it' texts point to setup.bat, no terminal commands")


def case_merge(ctx):
    """merge_registry_path on a PATH of System32 only: the registry's entries come after it (read-only)."""
    code = (f"import os, sys; sys.path.insert(0, {str(TOOLS)!r}); from motionlab.app import system; "
            "a = system.merge_registry_path(); print(len(a)); print(os.environ['PATH'].split(';')[0]); "
            "print(len(system.merge_registry_path()))")
    env = {k: v for k, v in os.environ.items() if k.upper() != "PATH"}
    env["PATH"] = str(SYS32)
    r = run([sys.executable, "-c", code], env=env)
    out = r.stdout.split()
    ok(r.returncode == 0 and len(out) == 3 and int(out[0]) > 0 and out[1].lower() == str(SYS32).lower()
       and out[2] == "0", "merge_registry_path adds the registry's PATH after this process's own, once",
       r.stdout + r.stderr)


def case_extract(ctx):
    """setup.bat outside a MotionLab folder (run from inside a ZIP) says 'extract first'; MotionLab.bat before setup
    runs setup.bat."""
    d = D / "extract"
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(LAB / "setup.bat", d / "setup.bat")
    r = run(["cmd", "/c", d / "setup.bat"])
    ok(r.returncode == 1 and "Extract the ZIP first" in r.stdout, "setup.bat alone says: extract the ZIP first",
       r.stdout + r.stderr)
    m = D / "notsetup"
    m.mkdir(parents=True, exist_ok=True)
    shutil.copy2(LAB / "MotionLab.bat", m / "MotionLab.bat")
    write_text_crlf(m / "setup.bat", "@echo SETUP RAN\n")
    r = run(["cmd", "/c", m / "MotionLab.bat"])
    ok("not set up yet" in r.stdout and "SETUP RAN" in r.stdout, "MotionLab.bat without .venv says so and runs setup.bat",
       r.stdout + r.stderr)


def build_hub(ctx) -> None:
    """hub.git: main = tested = A (this copy + its working changes, small requirements), then main = B (one more)."""
    if ctx.get("A"):
        return
    work, hub = D / "work", D / "hub.git"
    git("clone", "-q", "--no-hardlinks", LAB, work)
    status = run(["git", "status", "--porcelain", "-uall"], cwd=LAB).stdout.splitlines()
    for ln in status:
        rel = ln[3:].strip().strip('"')
        if " -> " in rel:
            rel = rel.split(" -> ", 1)[1]
        src, dst = LAB / rel, work / rel
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        elif not src.exists() and dst.is_file():
            dst.unlink()
    (work / "requirements.txt").write_text(TEST_REQUIREMENTS, encoding="utf-8")
    git("add", "-A", cwd=work)
    git("commit", "-q", "-m", "installer under test", cwd=work)
    ctx["A"] = git("rev-parse", "HEAD", cwd=work)
    git("init", "-q", "--bare", hub, cwd=D)
    git("push", "-q", str(hub), "HEAD:refs/heads/main", "HEAD:refs/heads/tested", cwd=work)
    (work / "zz_after_tested.txt").write_text("a push that GitHub's tests have not passed yet\n", encoding="utf-8")
    git("add", "-A", cwd=work)
    git("commit", "-q", "-m", "newer, not tested", cwd=work)
    ctx["B"] = git("rev-parse", "HEAD", cwd=work)
    git("push", "-q", str(hub), "HEAD:refs/heads/main", cwd=work)
    git("--git-dir", str(hub), "symbolic-ref", "HEAD", "refs/heads/main", cwd=D)
    ctx["hub"] = hub
    print(f"     fake GitHub: tested = {ctx['A'][:7]}, main = {ctx['B'][:7]} (one commit newer)")


def case_dry(ctx):
    """Everything missing, dry run: every command in the planned order with its flags; nothing runs."""
    log, pf = D / "dry_winget.log", D / "dry_path.txt"
    env = test_env(ctx["F"], pf, log)
    lab = D / "dry lab"
    r = run(["cmd", "/c", INSTALLER, "-DryRun", "-Yes", "-NoStart", "-Repo", D / "hub.git"],
            env={**env, "ML_ARGS": f"-Folder {ps_quote(lab)} -ShortcutFolder {ps_quote(D / 'desk dry')}"})
    out = r.stdout + r.stderr
    lines = [x.split("would run: ", 1)[1] for x in out.splitlines() if "would run: " in x]
    ids = [x.split("--id ", 1)[1].split()[0] for x in lines if x.startswith("winget install")]
    want = ["Git.Git", "Microsoft.VCRedist.2015+.x64", "OpenJS.NodeJS.LTS", "Python.Python.3.12", "Gyan.FFmpeg",
            "DenoLand.Deno", "yt-dlp.yt-dlp"]
    ok(r.returncode == 0 and ids == want, "dry run, everything missing: winget in the planned order", f"{ids}\n{out}")
    marks = (("git", "winget install --id Git.Git"), ("clone", "git clone"), ("vc", "winget install --id Microsoft.VCRedist"),
             ("claude", "powershell"), ("python", "winget install --id Python"), ("lab", "setup.bat /lab"))
    seq = [m for x in lines for m, pre in marks if x.startswith(pre)]
    ok(seq == ["git", "clone", "vc", "claude", "python", "lab"],
       "Git, the clone, VC++, Claude Code, Python ... setup.bat /lab come in that order", f"{seq}\n" + "\n".join(lines))
    ok(all(all(fl in x.split() for fl in WINGET_FLAGS) for x in lines if x.startswith("winget install")),
       "every winget install has -e --source winget --silent --accept-* --disable-interactivity")
    yt = [x for x in lines if "--id yt-dlp.yt-dlp" in x]
    ok(yt and "--skip-dependencies" in yt[0].split(), "yt-dlp gets --skip-dependencies (no second ffmpeg)")
    ok(any("irm https://claude.ai/install.ps1 | iex" in x for x in lines),
       "Claude Code comes from Anthropic's official installer (shown, not run)")
    ok(not calls(log), "the dry run called winget 0 times")
    ok(not lab.exists() and not (D / "desk dry").exists(), "the dry run created nothing")


def case_fake(ctx):
    """The whole install against the fake winget + the fake GitHub, folders with spaces: from 'Downloads' to a lab."""
    build_hub(ctx)
    log, pf = D / "fake_winget.log", D / "fake_path.txt"
    lab, desk = D / "lab dir", D / "desk dir"
    env = test_env(ctx["F"], pf, log, ml_args=f"-Folder {ps_quote(lab)} -ShortcutFolder {ps_quote(desk)}")
    t = time.time()
    r = run(["cmd", "/c", INSTALLER, "-Yes", "-NoStart", "-NoClaude", "-Graphics", "no", "-Repo", ctx["hub"]], env=env)
    out = r.stdout + r.stderr
    ctx["fake_out"] = out
    ok(r.returncode == 0, f"install mode -> hand-over -> -Here finished (exit {r.returncode}, {time.time() - t:.0f} s)",
       out)
    got = calls(log)
    ids = [c[c.index("--id") + 1] for c in got if "--id" in c]
    want = ["Git.Git", "Microsoft.VCRedist.2015+.x64", "Python.Python.3.12", "Gyan.FFmpeg", "DenoLand.Deno",
            "yt-dlp.yt-dlp"]
    ok(ids == want, "the real (fake) winget calls in order; no Node.js (motion graphics: no), no Claude Code",
       f"{ids}")
    ok(all(c[0] == "install" and all(f in c for f in WINGET_FLAGS) for c in got), "every call has the flags",
       json.dumps(got))
    ok(any("--skip-dependencies" in c for c in got if "yt-dlp.yt-dlp" in c), "yt-dlp with --skip-dependencies")
    if not (lab / ".git").exists():
        ok(False, "the clone exists", out)
        return
    h = head_info(lab)
    ok(h["head"] == ctx["A"] and h["branch"] == "main" and h["upstream"] == "origin/main",
       "the clone ends on tested, as a local main that follows origin/main", json.dumps(h))
    py = lab / ".venv" / "Scripts" / "python.exe"
    stamp = lab / ".venv" / ".requirements.sha256"
    ok(py.is_file() and stamp.is_file() and stamp.read_text().strip() == sha(lab / "requirements.txt"),
       ".venv + the Python packages + the requirements stamp")
    mcp = lab / ".claude" / "settings.local.json"
    ok(mcp.is_file() and "motionlab" in json.loads(mcp.read_text(encoding="utf-8")).get("enabledMcpjsonServers", []),
       "MotionLab's MCP server approved (without Claude Code installed)")
    ok((desk / "desktop" / "MotionLab.lnk").is_file() and (desk / "startmenu" / "MotionLab.lnk").is_file(),
       "the Desktop + Start-menu shortcuts (in the scratch folder)")
    ok(all((lab / d).is_dir() for d in ("refs", "analysis", "projects")), "the data folders")
    ok((lab / ".app" / "install.log").is_file(), "the window's text saved in .app\\install.log")
    ok("Installed now:" in out and "MotionLab is in" in out, "the last screen says what was installed and where", out)


def case_again(ctx):
    """A second run changes nothing: zero winget calls, pip skipped, the same commit."""
    lab = D / "lab dir"
    if not (lab / ".venv").exists():
        return ok(False, "second run (needs the fake case first)")
    log, pf = D / "fake_winget.log", D / "fake_path.txt"
    before, head = len(calls(log)), head_info(lab)["head"]
    env = test_env(ctx["F"], pf, log, ml_args=f"-ShortcutFolder {ps_quote(D / 'desk dir')}")
    r = run(["cmd", "/c", lab / "Install-MotionLab.cmd", "-Here", "-Yes", "-NoStart", "-NoClaude", "-Graphics", "no"],
            env=env)
    out = r.stdout + r.stderr
    ok(r.returncode == 0 and len(calls(log)) == before, f"a second run: exit {r.returncode}, "
                                                        f"{len(calls(log)) - before} winget calls", out)
    ok("[ok] Python packages" in out and "installing MotionLab's Python packages" not in out,
       "a second run skips pip (requirements unchanged)", out)
    ok(head_info(lab)["head"] == head, "a second run never pulls or resets")


def case_ask(ctx):
    """The questions, answered by typing (no -Yes): N = nothing changes; Y, no motion graphics, a name = saved."""
    lab = D / "lab dir"
    if not (lab / ".venv").exists():
        return ok(False, "ask (needs the fake case first)")
    full = (D / "fake_path.txt").read_text(encoding="utf-8").splitlines()
    desk = f"-ShortcutFolder {ps_quote(D / 'desk dir')}"
    pf, log = D / "ask1_path.txt", D / "ask1_winget.log"
    pf.write_text("\n".join(x for x in full if x != ctx["F"]["dirs"]["DenoLand.Deno"]) + "\n", encoding="utf-8")
    env = test_env(ctx["F"], pf, log, ml_args=desk)
    cmd = ["cmd", "/c", lab / "Install-MotionLab.cmd", "-Here", "-NoStart", "-NoClaude"]
    r = subprocess.run([str(c) for c in cmd], env=env, input="n\n", capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300, creationflags=NO_WINDOW)
    out = r.stdout + r.stderr
    ok(r.returncode == 0 and "This is what happens" in out and "Deno" in out and "Nothing was changed" in out
       and not calls(log), "N at the plan: the plan is shown, nothing changes, no winget call", out)
    pf, log = D / "ask2_path.txt", D / "ask2_winget.log"
    shutil.copy2(D / "fake_path.txt", pf)
    env = test_env(ctx["F"], pf, log, ml_args=desk)
    r = subprocess.run([str(c) for c in cmd], env=env, input="y\nn\nZz Tést\n", capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=300, creationflags=NO_WINDOW)
    out = r.stdout + r.stderr
    s = lab / "settings.json"
    author = json.loads(s.read_text(encoding="utf-8")).get("author") if s.is_file() else None
    ok(r.returncode == 0 and not calls(log) and "Node.js *" in out and "Installing Node.js" not in out,
       "Y, then No to motion graphics: Node.js was in the plan and is left out, no winget call", out)
    ok(author and author.startswith("zz-t"), f"the name typed in is saved for sharing ({author!r})", out)


def case_refused(ctx):
    """A refused permission box: a required program stops the install in plain words, an optional one is left out;
    winget's 'already installed' counts as installed."""
    lab = D / "lab dir"
    if not (lab / ".venv").exists():
        return ok(False, "refused (needs the fake case first)")
    full = (D / "fake_path.txt").read_text(encoding="utf-8").splitlines()
    dirs = ctx["F"]["dirs"]
    desk = f"-ShortcutFolder {ps_quote(D / 'desk dir')}"
    # a required one: the Visual C++ runtime
    pf, log = D / "refused1_path.txt", D / "refused1_winget.log"
    pf.write_text("\n".join(x for x in full if x != dirs["Microsoft.VCRedist.2015+.x64"]) + "\n", encoding="utf-8")
    env = test_env(ctx["F"], pf, log, rc="Microsoft.VCRedist.2015+.x64=0x800704C7", ml_args=desk)
    r = run(["cmd", "/c", lab / "Install-MotionLab.cmd", "-Here", "-Yes", "-NoStart", "-NoClaude", "-Graphics", "no"],
            env=env)
    out = r.stdout + r.stderr
    ids = [c[c.index("--id") + 1] for c in calls(log) if "--id" in c]
    ok(r.returncode == 1 and "the answer was No" in out and "cannot work without Microsoft Visual C++ runtime" in out,
       "a refused permission box for a required program: stops, in plain words", out)
    ok(ids == ["Microsoft.VCRedist.2015+.x64"] and "the lab steps" not in out, "... and nothing runs after it",
       f"{ids}")
    # optional ones: Deno refused, Node.js refused (motion graphics: yes), yt-dlp 'already installed'
    pf, log = D / "refused2_path.txt", D / "refused2_winget.log"
    gone = {dirs["DenoLand.Deno"], dirs["OpenJS.NodeJS.LTS"], dirs["yt-dlp.yt-dlp"]}
    pf.write_text("\n".join(x for x in full if x not in gone) + "\n", encoding="utf-8")
    env = test_env(ctx["F"], pf, log, rc="DenoLand.Deno=0x800704C7;OpenJS.NodeJS.LTS=0x800704C7;yt-dlp.yt-dlp=0x8A15002B",
                   ml_args=desk)
    r = run(["cmd", "/c", lab / "Install-MotionLab.cmd", "-Here", "-Yes", "-NoStart", "-NoClaude", "-Graphics", "yes"],
            env=env)
    out = r.stdout + r.stderr
    ids = [c[c.index("--id") + 1] for c in calls(log) if "--id" in c]
    ok(r.returncode == 0 and ids == ["OpenJS.NodeJS.LTS", "DenoLand.Deno", "yt-dlp.yt-dlp"],
       f"optional programs refused: it carries on (exit {r.returncode}, calls {ids})", out)
    ok("Deno could not be installed: Windows asked for permission and the answer was No" in out
       and "Left out:" in out, "a refused optional program is named in plain words and left out", out)
    ok("motion graphics are left out" in out and "installing HyperFrames" not in out,
       "no Node.js = no HyperFrames attempt", out)
    ok("yt-dlp was installed already" in out, "winget's 'already installed' (0x8A15002B) counts as installed", out)


def case_zip(ctx):
    """A ZIP copy (git archive of tested) run through setup.bat: connected to tested on a local main, your files
    untouched."""
    build_hub(ctx)
    z, copy = D / "MotionLab-main.zip", D / "zip copy"
    git("archive", "--format=zip", "-o", z, ctx["A"], cwd=D / "work")
    with zipfile.ZipFile(z) as f:
        f.extractall(copy)
    mine = {copy / "refs" / "zz_my video.mp4": os.urandom(4096),
            copy / "analysis" / "zz_mine" / "events.json": b'{"mine": true}',
            copy / "settings.json": b'{"author": "zz"}'}
    for p, b in mine.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b)
    before = {p: sha(p) for p in mine}
    ok(b"\r\n" in (copy / "setup.bat").read_bytes(), "the ZIP's setup.bat has CRLF line endings (git archive)")
    full = D / "fake_path.txt"
    pf, log = D / "zip_path.txt", D / "zip_winget.log"
    shutil.copy2(full, pf)
    env = test_env(ctx["F"], pf, log, ml_args=f"-ShortcutFolder {ps_quote(D / 'desk zip')}")
    r = run(["cmd", "/c", copy / "setup.bat", "-Yes", "-NoStart", "-NoClaude", "-Graphics", "no", "-Repo", ctx["hub"]],
            env=env)
    out = r.stdout + r.stderr
    ok(r.returncode == 0 and (copy / ".git").exists(), f"setup.bat on a ZIP copy: exit {r.returncode}, connected", out)
    if (copy / ".git").exists():
        h = head_info(copy)
        ok(h["head"] == ctx["A"] and h["branch"] == "main" and h["upstream"] == "origin/main",
           "the ZIP copy is on tested, as a local main that follows origin/main", json.dumps(h))
    ok(all(sha(p) == before[p] for p in mine), "your videos, analyses and settings in the ZIP copy are untouched")
    ok((copy / ".venv" / "Scripts" / "python.exe").is_file(), "the ZIP copy got its .venv")
    ok(not calls(log), "nothing was missing: winget called 0 times")


def case_folder(ctx):
    """A folder that holds other files is never used - refused, unchanged."""
    busy = D / "busy folder"
    busy.mkdir(parents=True, exist_ok=True)
    (busy / "keep.txt").write_text("not MotionLab", encoding="utf-8")
    before = sorted(p.name for p in busy.iterdir()), sha(busy / "keep.txt")
    log, pf = D / "folder_winget.log", D / "folder_path.txt"
    env = test_env(ctx["F"], pf, log, ml_args=f"-Folder {ps_quote(busy)} -ShortcutFolder {ps_quote(D / 'desk x')}")
    r = run(["cmd", "/c", INSTALLER, "-Yes", "-NoStart", "-NoClaude"], env=env)
    out = r.stdout + r.stderr
    ok(r.returncode == 1 and "already holds other files" in out, "a folder with other files is refused", out)
    ok((sorted(p.name for p in busy.iterdir()), sha(busy / "keep.txt")) == before and not calls(log),
       "... and left exactly as it was (no winget call)")


CASES = {"parse": case_parse, "header": case_header, "launcher": case_launcher, "merge": case_merge,
         "extract": case_extract, "dry": case_dry, "fake": case_fake, "again": case_again, "ask": case_ask,
         "refused": case_refused, "zip": case_zip, "folder": case_folder}


def main() -> int:
    a = sys.argv[1:]
    if a[:1] == ["fake-winget"]:
        return fake_winget(a[1:])
    keep = "--keep" in a
    names = [x for x in a if x != "--keep"] or list(CASES)
    bad = [x for x in names if x not in CASES]
    if bad:
        raise SystemExit(f"unknown case(s) {bad} - {__doc__}")
    rmtree(D)
    D.mkdir(parents=True)
    real = real_state()
    ctx = {"F": setup_fakes()}
    t0 = time.time()
    try:
        for n in names:
            print(f"--- {n}", flush=True)
            t = time.time()
            CASES[n](ctx)
            print(f"     ({time.time() - t:.0f} s)", flush=True)
    finally:
        after = real_state()
        for k in real:
            ok(real[k] == after[k], f"this PC unchanged: {k}")
        if not keep:
            rmtree(D)
    print(f"\n{'ALL PASS' if not FAILED else f'{len(FAILED)} FAILED'} ({time.time() - t0:.0f} s)"
          + ("" if not FAILED else "\n  - " + "\n  - ".join(FAILED)))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
