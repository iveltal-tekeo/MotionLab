"""The app's own small jobs (0.4.2.1) that are not a lab tool: run by jobs.py as a child process like the others.

    .venv\\Scripts\\python tools\\motionlab\\app\\jobtools.py ytdlp-update [--dry-run]
    .venv\\Scripts\\python tools\\motionlab\\app\\jobtools.py player-copy <video>
    .venv\\Scripts\\python tools\\motionlab\\app\\jobtools.py thumb-check <project> [--title "..."]
    .venv\\Scripts\\python tools\\motionlab\\app\\jobtools.py selfcheck

ytdlp-update = Settings > Programs > *Update yt-dlp*: the way that fits how it was installed (system.install_kind:
winget / pip / the exe's own -U), then the result in words ("updated: 2026.08.19 -> 2026.10.10" or "already up to
date"); --dry-run prints the command and runs nothing (the tests). player-copy = a small H.264 copy for the player
when the browser cannot play a video (player.py). thumb-check (0.4.3) = Edit > a video > Publish > *Check*: the
thumbnail check of every thumbnail (tools\\thumbnail.py's rules; it saves the results in package.json) - a rule that
FAILs is a result to show, not a failed job (thumbnail.py check exits 1 then). selfcheck = known answers without network (the report's scrubbing
and link, how yt-dlp was installed)."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))         # tools\

from motionlab.app import player, report, system  # noqa: E402
from motionlab.util import setup_console  # noqa: E402

WINGET_NO_UPDATE = (0x8A15002B, 0x8A15002B - (1 << 32))       # "no applicable upgrade found" (unsigned / signed)


def ytdlp_update(dry: bool) -> int:
    y = system.ytdlp_info()
    if not y.get("found"):
        print("yt-dlp was not found - " + system.HOW["yt-dlp"])
        return 1
    before = y.get("version") or "?"
    print(f"yt-dlp {before}" + (f" ({y['age']})" if y.get("age") else "") + f": {y['label']}, at {y['path']}")
    cmd = y["cmd"]
    print("command: " + subprocess.list2cmdline(cmd))
    if dry:
        print("dry run: nothing was run")
        return 0
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True,
                            encoding="utf-8", errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    out = []
    for line in proc.stdout:
        line = line.rstrip("\r\n")
        if line.strip() and not set(line.strip()) <= set("-\\|/ █▒"):         # winget's spinner
            print(line, flush=True)
            out.append(line)
    rc = proc.wait()
    system._versions.clear()                                  # ask the (maybe new) program again
    after = system.version(y["path"]) or "?"
    text = "\n".join(out).lower()
    if rc != 0 and not (y["kind"] == "winget" and (rc in WINGET_NO_UPDATE or "no available upgrade" in text
                                                   or "no newer package" in text or "no applicable" in text)):
        print(f"the update did not work (exit code {rc}) - yt-dlp stays at {before}"
              + (" - a pip copy: run the command above in a console" if y["kind"] == "pip" else ""))
        return rc or 1
    if after != before:
        print(f"yt-dlp updated: {before} -> {after}")
    else:
        print(f"yt-dlp is already up to date ({after})")
    return 0


def thumb_check(project: str, title: str | None) -> int:
    """thumbnail.py's check of every thumbnail of a video (it writes package.json "thumbnails"[i]["check"])."""
    from motionlab import thumbnail as T
    try:
        res = T.check_project(project, title or None)
    except SystemExit as e:                                   # its plain message (no thumbnails yet, ...)
        print(e)
        return 1
    for tid, r in res.items():
        for size in T.SIZES:
            print(f"{tid} {size.replace('x', ':')}: {T.overall(r[size])}")
            for x in r[size]:
                print(f"  {x['status']:4s} {x['rule']:13s} {x['text']}", flush=True)
    print("checked: " + ", ".join(f"{k} {v['result']}" for k, v in res.items())
          + (" - the FAIL lines say what to change" if any(v["result"] == "FAIL" for v in res.values()) else ""))
    return 0


def selfcheck() -> list[str]:
    bad = report.selfcheck()
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        wg = t / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages" / "yt-dlp.yt-dlp_Microsoft.Winget.Source_8w" / "yt-dlp.exe"
        venv = t / "venv" / "Scripts" / "yt-dlp.exe"
        alone = t / "Downloads" / "yt-dlp.exe"
        for p in (wg, venv, alone, t / "venv" / "Scripts" / "python.exe"):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"")
        (t / "venv" / "pyvenv.cfg").write_text("home = x", encoding="utf-8")
        got = {k: system.install_kind(str(p)) for k, p in (("winget", wg), ("pip", venv), ("exe", alone))}
        if [g["kind"] for g in got.values()] != ["winget", "pip", "exe"]:
            bad.append(f"install_kind: {[g['kind'] for g in got.values()]}")
        elif not ({"upgrade", "--id", "yt-dlp.yt-dlp", "--silent", "--accept-source-agreements",
                   "--accept-package-agreements", "--disable-interactivity"} <= set(got["winget"]["cmd"])
                  and got["pip"]["cmd"][1:] == ["-m", "pip", "install", "-U", "yt-dlp[default]"]
                  and got["exe"]["cmd"] == [str(alone), "-U"]):
            bad.append(f"install_kind commands: {[g['cmd'] for g in got.values()]}")
    for d, want in ((0, "from today"), (5, "5 days old"), (21, "3 weeks old"), (57, "2 months old")):
        if system.age_words(d) != want:
            bad.append(f"age_words({d}) = {system.age_words(d)!r}, want {want!r}")
    return bad


def main() -> int:
    setup_console()
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    if a[0] == "ytdlp-update":
        return ytdlp_update("--dry-run" in a)
    if a[0] == "player-copy" and len(a) > 1:
        try:
            player.make(Path(a[1]), out=lambda s: print(s, flush=True))
        except (OSError, RuntimeError) as e:
            print(f"could not make the player copy: {e}")
            return 1
        return 0
    if a[0] == "thumb-check" and len(a) > 1:
        return thumb_check(a[1], a[a.index("--title") + 1] if "--title" in a[:-1] else None)
    if a[0] == "selfcheck":
        bad = selfcheck()
        print("\n".join(bad) if bad else "jobtools selfcheck: PASS (scrubbing, the issue link, yt-dlp install kinds)")
        return 1 if bad else 0
    raise SystemExit(__doc__)


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.exit(main())
