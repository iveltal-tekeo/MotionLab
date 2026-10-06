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

- **The lab**: semantic versions in `CHANGELOG.md` (`0.4.0` = Resolve rebuild + drift check). Minor = new
  capability, patch = fix. Tag a release when the self-tests (and the Resolve test) pass.
- **Edits**: already versioned: `edit_vN.py` -> `plan_vN.json` -> `<name>_vN.mp4` / `<name>_resolve_vN`.
  Keep that; record in each plan which lab version made it (`"lab_version"`), so a render can be reproduced.
- **Knowledge**: every lesson / threshold change is a commit that names its source (feedback file, reference,
  frame + timecode). Profiles get their own version number inside the file.
- **Library effects**: `library\<effect>\` with `version` in the recipe; a changed macro gets a new version, old
  ones stay so finished projects still open.
- **Resolve projects**: the build manifest (`<timeline>_build.json`) + `comps\imported\` already record exactly what
  was imported; `--diff` shows what you changed by hand. Hand edits worth keeping become knowledge (a lesson, a
  profile value or a library macro).

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
   An installer or a `setup.py doctor` that checks all three would save them an afternoon.

## 5. What `.gitignore` will need

```
/data/   /refs/   /analysis/   /projects/
.venv/   __pycache__/   *.pyc
settings.json
tests/selftest/*.mp4   tests/selftest/plates/
```
