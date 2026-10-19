# How to organise MotionLab for a repo, versions and sharing (plan, 2026-10-06)

Status (2026-10-06, v0.2): the repo is prepared **in place** - `C:\MotionLab` with `.gitignore` (code, the skill +
lessons, docs, setup go in; refs, analysis, projects, library, settings.json, caches, local knowledge stay out),
`.gitattributes`, `README.md` (incl. the owner's first-upload commands), `setup.bat`, `LICENSE`, `CHANGELOG.md`;
machine settings are in `settings.json` (Settings page). The user uploads it. Versions: `__version__` in
`tools\motionlab\__init__.py` + a CHANGELOG section; installs update themselves with git at start-up. Shared
knowledge lives in `knowledge\` (reference cards, lessons waiting for review) and the shared `lessons.md`
(docs\knowledge_sharing.md). The bigger restructure below (package at the top, a separate data folder) is still a
plan - do it only when it pays off (friends contributing code), not for the MVP.

## 1. Three kinds of things, three homes

| kind | examples today | size | where it should live |
|---|---|---|---|
| **code** | `tools\` (pipeline, compositor, Resolve builder), `.claude\skills\` | ~1 MB | the git repo |
| **knowledge** | `config.json` thresholds, `lessons.md`, `library\` recipes + Fusion macros, future style profiles, self-test truths | < 10 MB | the git repo, versioned like code |
| **data** | `refs\`, `analysis\`, `projects\` (footage, caches, renders) | 10.7 GB now, grows ~0.6 GB per reference and ~2.6 GB per minute of project footage | never in git; stays on the PC (back it up separately) |

Knowledge is what MotionLab learns. It must be versioned: when a lesson or threshold changes, the commit says why
(which feedback, which reference). Data is per-user and huge, so it stays out.

## 2. Proposed layout (when the repo is created)

```
MotionLab\                      <- the git repo (code + knowledge)
  motionlab\                    package (today tools\motionlab\)
    resolve\                    today's resolve_build.py split up: session.py, comps.py, luts.py, drift.py
    app\                        the desktop app (exists since 2026-10-06: stdlib server + Edge app window; later an
                                .exe via PyInstaller/pywebview - needs installing those, ask first)
  tools\                        thin command-line entry points (analyze.py, resolve_build.py, storage.py ...)
  knowledge\
    config.json                 detection thresholds
    lessons.md                  learned from feedback (today .claude\skills\analyze-reference\lessons.md)
    profiles\<style>.json       later: music video / reels / documentary
    library\<effect>\           recipe.md + <effect>.setting (Fusion macro) + reference frames
  tests\                        self-test generators + truths (+ a Resolve scratch-project test)
  docs\                         roadmap, option 2 guide, this file
  .claude\skills\               the /analyze-reference skill
  settings.example.json         machine paths (lab data folder, Resolve install, LUT folder)
  CHANGELOG.md
D:\MotionLabData\ (or C:\MotionLab\data\, git-ignored)
  refs\  analysis\  projects\
```

`settings.json` (not in git) holds the paths that differ per PC: where the data lives, Resolve's scripting folder,
Resolve's LUT folder. Today these are hard-coded in `resolve_build.py`, `storage.py`, and `LAB = C:\MotionLab` in
`projects\test_4am\build\*.py`; `plan_v1.json` stores absolute footage paths.

## 3. Versions

- **The lab**: semantic versions in `CHANGELOG.md` (`0.4.0` = Analyze / Edit / Generate; the same notes in Spanish in
  `CHANGELOG.es.md` from 0.5.1 on). Minor = new capability, patch = fix. Tag a release when the self-tests (and the
  Resolve test) pass. **Phases** (the user, 2026-10-18): Phase 1 = everything up to 0.5.0.1; Phase 2 = the path from
  0.5.0 to 1.0.0, "deployment" (opened by 0.5.1; docs\plans.md).
- **Edits**: already versioned: `edit_vN.py` -> `plan_vN.json` -> `<name>_vN.mp4` / `<name>_resolve_vN`.
  Keep that; record in each plan which lab version made it (`"lab_version"`), so a render can be reproduced.
- **Knowledge**: every lesson / threshold change is a commit that names its source (feedback file, reference,
  frame + timecode). Profiles get their own version number inside the file.
- **Library effects**: `library\<effect>\` with `version` in the recipe; a changed macro gets a new version, old
  ones stay so finished projects still open.
- **Resolve projects**: the build manifest (`<timeline>_build.json`) + `comps\imported\` already record exactly what
  was imported; `--diff` shows what you changed by hand. Hand edits worth keeping become knowledge (a lesson, a
  profile value or a library macro).

### Tests on GitHub (since 0.3.1)

- `.github\workflows\tests.yml`, on GitHub's Windows machine: Python 3.12 + `requirements.txt` + Gyan's ffmpeg
  (`FFMPEG_VERSION`, the build `setup.bat` installs through winget - raise it when winget's moves), then
  `selftest.py --extended` (the synthetic videos are generated there) and `tools\dev\smoke.py` (every file compiles,
  every module imports, the app server's read-only routes, every page in headless Edge, the MCP server). ~15 minutes.
- **When it runs (since 0.4.2.1 - the full tests for the big versions only)**: a few-second Linux job ("scope")
  decides per push to main. The full run (~15 min) happens only when `__version__` is a new `x.y.0` (0.5.0,
  0.6.0...) without its `v<version>` tag yet - that repeats on every push until the version passes and is tagged -
  or when it is started by hand (GitHub > Actions > tests > **Run workflow**, any branch). Any other new version
  (0.4.2.1, 0.4.3... - no tag yet) gets the "release" job instead: ~1 minute on Linux - every Python file compiles,
  CHANGELOG.md has its `## <version> - ` section, the roadmap's `here` is that version, the shared knowledge reads -
  then it is marked tested and tagged. The user's choice (2026-10-15: "i just need to run the tests on major versions
  ... to develop more smoothly"): the full self-test + smoke test on the developer's PC before every release are the
  gate for the small versions. Anything else runs nothing. Pull requests run nothing by themselves.
- **The `tested` branch is the gate**: when a run on main passes (the full tests, the release check or the knowledge
  check), `tested` moves to it, and the app's Update button installs only what is on `tested`
  (`updater._upstream`). So code pushed between versions reaches friends with the next version; until then Settings
  > Sharing & updates says those changes are "not released yet". Share still pushes to main. A push that only touches shared knowledge (`knowledge\references`,
  `knowledge\incoming`, `lessons.md`) since the last tested commit needs no Windows machine: the "knowledge" job
  checks that every card / lesson reads (JSON, UTF-8) and moves `tested` within a minute. (If untested code sits on
  main in between, friends' cards wait for the next tested run too.) Runs on main go one after another in order; a
  re-run of an old commit never moves `tested` back. Moving `tested` / tagging = `.github\scripts\mark_tested.sh`.
- **Tags**: the first passing run of a new `__version__` tags that commit `v<version>`. Older releases, once, by
  hand: `git tag v0.2.0 cee5485`, `git tag v0.2.5 9334caa`, `git tag v0.3.0 82642a1`, `git push origin --tags`.
- **When a run is red**: the Actions tab shows the failing step; a failed run keeps the scores and logs as the
  artifact "test-results", and copies the important + last lines of `selftest.log` / `smoke.log` into public error
  notes (annotations) - job logs need repo-admin rights, the notes don't: `api.github.com/repos/<owner>/MotionLab/
  check-runs/<job id>/annotations` (the job id from `actions/runs/<run id>/jobs`). Fix and push again - friends keep the last tested version meanwhile. Only if the
  workflow itself is broken (not the lab) and an update must go out anyway: `git push origin main:tested`.

### Install (since 2026-10-18)

The user: "its very hard for people to read the steps or install git or do all fo that throught the terminal ... its
just the setup that need a "idiot-proof" imporvment".
- **One file, two modes**: `Install-MotionLab.cmd` (repo root, ASCII; its batch part is ONE line that hands the file
  to PowerShell - so LF or CRLF endings and a rewrite while it runs are both fine; all its words in one table at the
  top). Double-clicked from Downloads (install mode) it asks everything first - the folder (`C:\MotionLab`, Enter;
  never a folder that holds other files; warnings for Downloads / Desktop / OneDrive / Temp / accents / long paths),
  the plan (every program, what for, size, whether Windows asks permission), motion graphics (yes by default), the
  name - then installs Git, clones and hands over to the CLONED copy's installer (`-Here -Yes` + the answers), so an
  old download finishes with the newest tested steps. `-Here` (= double-clicking `setup.bat`) finishes / repairs the
  folder it sits in: winget for what is missing (exit codes in plain words, "installed" only when found afterwards,
  PATH re-read from the registry after each - no new window, no second run), Claude Code with Anthropic's own
  installer + `claude auth login`, a ZIP copy connected through `updater.connect`, then `setup.bat /lab` (.venv, pip
  only when requirements.txt changed - `.venv\.requirements.sha256` -, folders, the MCP approval, HyperFrames,
  shortcuts). It refuses a "Run as administrator" start; a second run changes nothing; it never pulls, resets or
  deletes; the window's text is kept in `.app\install.log`.
- **The tested commit on a local main**: a new clone and *Connect to GitHub* check out `origin/tested` as a LOCAL
  branch `main` that follows `origin/main` - the Update button's gate (`updater._upstream` follows tested only from a
  branch called main; Share pushes `HEAD:main`).
- **The download**: README links the file's page on the `tested` branch (*Download raw file*; that copy has LF
  endings, which the one-line header handles). Optional later, the user's call: a GitHub Release per tagged version
  with the file attached - one click, `releases/latest/download/Install-MotionLab.cmd` - a few lines in
  `.github\scripts\mark_tested.sh --tag` (`gh release create`, the workflow already has `contents: write`).
- **Tests**: `tools\dev\install_test.py` (about 2 minutes; never touches this PC: a fake winget + a test PATH file =
  `ML_TEST_PATHFILE`, a fake GitHub with main + tested, scratch folders with spaces; the real shortcuts, settings and
  user PATH are hashed before and after). Still needed by hand when it changes: one clean Windows 10 and 11 (Sandbox
  or a VM) from the download to MotionLab open, with Settings > Programs all found.

## 4. Fix before a repo or before friends use it (judgement)

1. Paths: move machine paths to `settings.json`; store footage paths in plans relative to the project folder.
2. `resolve_build.py` (~1,960 lines) mixes geometry, LUTs, comp builders, the Resolve session, drift and doctor:
   split it into `motionlab\resolve\`. The test_4am sections (`SECTIONS`, S1-S7) belong in the plan, not the tool.
3. `verify_timing.py` / `ref_timing.py` live in the project and hard-code 4AM's key frames: make one generic tool
   that reads the key frames from the reference's `events.json`.
4. Resolve has no automatic test: turn today's scratch-project checks (build a section, edit it by script, check
   `--diff` finds every edit, reload and compare renders) into `tests\resolve_test.py` (needs Resolve running).
5. Storage: the footage cache is raw 8-bit grey (2.6 GB per minute). Compress it or keep only half resolution for
   layout work before projects get long.
6. Friends' PCs: Python 3.12 + ffmpeg + Resolve Studio (paid) are requirements; option 2 needs Studio's scripting.
   An installer or a `setup.py doctor` that checks all three would save them an afternoon. Done 2026-10-18:
   `Install-MotionLab.cmd` (section 3, *Install*) - Resolve Studio stays the user's own install.

## 5. What `.gitignore` will need

```
/data/   /refs/   /analysis/   /projects/
.venv/   __pycache__/   *.pyc
settings.json
tests/selftest/*.mp4   tests/selftest/plates/
```
