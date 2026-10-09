# MotionLab

Local lab for analyzing music videos and vlogs: detect every edit/effect, show a frame-accurate visual breakdown
the user can verify, and rebuild approved effects with the user's own footage (lab renders, DaVinci Resolve). A
Windows app (`MotionLab.bat`) + Python tools, shared with friends through GitHub.

## Hard rules
1. **NEVER modify a source video** the user gives you (in `refs\`, in `projects\<name>\` or anywhere else): no
   re-encoding in place, renaming, moving, trimming or deleting. Only read it. All copies, CFR proxies, extracted
   frames, sheets and previews go into `analysis\<video name>\` (analysis) or `projects\<name>\build\` (renders).
   `tools\analyze.py` and `tools\prep_footage.py` refuse writes outside those folders and record/verify the source
   SHA-256; tell the user if a check ever reports a change. The app's Delete buttons are the user's own clicks (a
   dialog, then the Windows Recycle Bin); Claude never deletes sources, not through those routes either.
2. **Every timestamp shown to the user must include the frame number AND the timecode** `HH:MM:SS:FF` at the
   video's real frame rate, e.g. `f480 (00:00:16:00)`, so the user can verify it. Reports, contact sheets,
   previews, chat and notes all follow this.
3. Read `.claude\skills\analyze-reference\lessons.md` before every analysis and apply it.

## Read only what the task needs
This file is loaded into every chat; the rest is read when a task needs it. Start from the matching entry and do not
explore the whole lab:

| task | read first |
|---|---|
| analyse / review a reference, apply `MOTIONLAB FEEDBACK`, review incoming lessons | the `/analyze-reference` skill |
| recreate a reference with the user's footage (lab render, then Resolve) | the `/recreate-video` skill |
| anything in DaVinci Resolve (resolve_build.py, Fusion comps, library.py test / install) | `docs\resolve_notes.md` |
| the app (`tools\app.py`, `tools\motionlab\app\`) | `tools\motionlab\app\CLAUDE.md` (loads by itself there) |
| knowledge sharing (cards, lessons, packs) | `docs\knowledge_sharing.md`, `knowledge\README.md` |
| questions about working with Claude, effort levels, tokens | `docs\claude_tips.md` |
| what comes next (planned versions and their design notes) | `docs\plans.md` (the app's What's new shows it) |

Every tool starts with a usage docstring: read its first lines (or run it without arguments), not the whole file.

## Layout
- `refs\` reference videos the user drops in or downloads (read-only); `refs\audio\` = MP3 downloads;
  `refs\downloads.json` = where each download came from (link, platform, uploader, id, duration)
- `analysis\<video name>\` one per analyzed video: `events.json` (all data), `report.html`, `review.json` (Claude's
  reviews), `review_todo.md`, `events\<ID>\sheet_NN.jpg + preview.mp4`, `frames\`, `cuts\`, `metrics.csv`,
  `overview.png`, `audio.wav`, `proxy_cfr.mp4` (only for VFR sources), `cache\` (re-usable metrics), `inspect\`,
  `meta.json` (category, tags, link - the user's choice, kept across re-runs), `feedback\` (`verdicts.json` = the
  user's verdicts, their ONE home; `app_<date>.txt` = exports from the app; `feedback_<date>.txt/.json` = archived by
  `feedback.py` when Claude applied them)
- `knowledge\` what installs share: `references\` = SHARED reference cards `<video id>--<author>.json`, `incoming\` =
  SHARED lessons waiting for review; private: `local\` (this PC's cards, `lessons.md` = new lessons `local-N`,
  `shared.json`, `summary.md` + `summary\<category>.md` - Claude reads both before a review), `inbox\` / `outbox\`
  (`*.mlpack.json` packs for friends without push access)
- `projects\<name>\` the user's footage (read-only, top level); everything we make goes to `build\`: `sources.json`
  (IDs A, B, ... + SHA-256), `cache\` (grey frame caches), `boards\`, `edit_vN.py` -> `plan_vN.json` (the edit),
  `<name>_vN.mp4`, `compare\`, `stills\`, `sheets\`, `resolve\` (option 2), `<name>_resolve_vN.mp4`,
  `library_picks.json` (the user's picks in the app), `pruned.json`
- `library\` approved effects only (made by `tools\library.py`): `README.md` + per effect `<effect>.md` recipe,
  `<stem>.setting` Fusion macro(s), `ref_fNNNNN.jpg`, `check.png`
- `tools\` the pipeline (Python 3.12 venv at `.venv\`, `requirements.txt`; ffmpeg on PATH); `tools\motionlab\` the
  package (`compose.py` compositor, `graphics.py` pixel font / seven-segment / firework / streaks, `fusion.py` Fusion
  .comp text, `knowledge.py`, `app\` the app); `tools\config.json` every detection threshold (`_comment` keys
  explain units)
- `docs\` hand-offs: `resolve_notes.md`, `option2_resolve.md`, `claude_tips.md`, `knowledge_sharing.md`,
  `organization.md` (repo/versioning plan), `roadmap.png` (`tools\roadmap.py` redraws it)
- `.app\` the app's cache and logs (`server.log`, `deleted.log`, `jobs\`, `open_claude.cmd`, `server.json`);
  `settings.json` = the user's app settings; `.claude\skills\` = `analyze-reference\` (+ `lessons.md`),
  `recreate-video\`
- Repo files (v0.3.0): `README.md`, `setup.bat`, `LICENSE` (MIT), `CHANGELOG.md` (the Update button's dialog shows
  it), `.mcp.json` (MotionLab's MCP server),
  `.gitignore` (refs, analysis, projects, library, settings.json, .app, .venv, knowledge\local|inbox|outbox and the
  self-test videos stay private), `.gitattributes` (LF in the repo, `.bat` always CRLF), `MotionLab.ico`. The
  version is `tools\motionlab\__init__.py` `__version__`. The USER creates and uploads the repo - never `git init` /
  `git push` / create the GitHub repo unasked (the app's own Share / Update buttons are the user's clicks).

## Tools (run from C:\MotionLab as `.venv\Scripts\python tools\<tool>.py`)
- `analyze.py "<video>"` full pipeline (`--redetect` re-uses cached metrics after config changes, `--force` redo all,
  `--category <id>` (alias `--style`; ids in `tools\motionlab\styles.py`) and `--tags "a, b"` - both kept on re-runs
  in `meta.json`; afterwards it refreshes this video's reference card in `knowledge\local\references\`)
- `report.py <name>` merge `review.json` into `events.json` and re-render `report.html`
- `feedback.py <name> <file>` parse feedback text, archive it, map verdicts (and possible-miss answers) to events
- `sheet.py <name> <start> <end>` contact sheet + preview for any frame range (missed effects)
- `selftest.py [--extended]` regenerate-if-needed and score the synthetic test videos (must PASS after any change);
  `make_testvideo.py [--extended|--negative|--vfr]` builds them with ground truth
- `knowledge.py cards | summary | pending | next-lesson-id | share | export | import <pack>`
- `download.py <url> <preset>` the yt-dlp wrapper the app's download job runs
- Rebuilding (see `/recreate-video`): `prep_footage.py <project>`, `storyboard.py <project>`,
  `render_video.py <plan.json>`, `compare_renders.py`, `overlay.py new | render | stills` (graphics as HTML via
  HyperFrames, pinned in `tools\overlays\`); Resolve (see `docs\resolve_notes.md`): `resolve_build.py`,
  `library.py build | test | title | install`, `resolve_mcp.py install | status | remove` (optional Resolve MCP for
  Claude Code, this PC only)
- `storage.py` disk report by category; `--prune <name|all> --what cache,checks,finals --yes` deletes only what the
  lab can rebuild (dry run without `--yes`), never sources, knowledge or media a Resolve project uses. Footage
  caches are the big item: ~3.9 GB per minute of footage in colour (2.6 grey).
- `mcp_server.py` MotionLab's MCP server (`.mcp.json`; read-only: events, sheets, frames, verdicts, projects,
  stills - prefer its tools to reading events.json)
- `app.py` the app (`--no-window --stay --no-update --port N` = a test server); `roadmap.py` redraws `docs\roadmap.png`
  (edit its STAGES / VERDICT when the state changes)

## The app (details: `tools\motionlab\app\CLAUDE.md`)
`MotionLab.bat` = a local server + an Edge app window: Home, References (download, analyse, the review page with
verdicts and possible misses, Delete), Videos (the user's edits, renders, Resolve check-up, library picks), Library,
Knowledge (Share), Jobs, Storage, Settings. The app runs the lab's own tools as jobs; Claude's parts run in Claude
Code windows the app opens with a fixed first message and an effort level per task (Settings > Claude Code).

## Conventions
- Frames are 0-based (frame 0 = first frame of the analyzed video); ranges are inclusive.
- Timecode = non-drop `HH:MM:SS:FF` counting the nominal rate (23.976 -> 24, 29.97 -> 30), frame 0 = 00:00:00:00
  (`timecode.drop_frame` in config switches 29.97/59.94 to drop-frame `;`). A Resolve timeline usually starts at
  01:00:00:00, so add one hour when placing things on a timeline.
- Hard cut at frame c = c is the first frame of the new shot. Transition range = frames that visibly mix both
  shots. Motion effect range = frames that moved relative to the previous one.
- On beat = within +-1 frame of a detected beat (`audio.on_beat_tolerance_frames`); beat times are refined to the
  attack (~5 ms accuracy on the click-track self-test).
- Easing words are unambiguous: "accelerating (slow start)", "decelerating (slow end)", "S-curve", "linear".
- Categories: every analysis has one (`styles.CATEGORIES`: music_video, ad, motion_graphics, documentary, vlog,
  tutorial, cooking, podcast, gaming, sports, travel, fashion, comedy, trailer, edit, other; the old "short" = other
  + format) + free tags; `events.json` "category" (and "style" as an alias for old readers). The format is measured
  (vertical / horizontal / square + short <=90 s / mid <=600 s / long). Lessons apply to all categories unless
  tagged `category: <id>`. Pacing per video (`knowledge.pacing`): cuts/min, average / median / p10 / p90 shot,
  cuts in the first 3 s, first cut, % of plain cuts on the beat, effects/min, effect families, BPM.
- Shared knowledge = text and numbers through the repo: cards (`knowledge\references\`), lessons waiting for review
  (`knowledge\incoming\`), reviewed rules (`lessons.md`); never videos, frames, sheets or local paths
  (docs\knowledge_sharing.md). Cards carry the author name from Settings, never an email.

## Workflow
- A reference goes through six steps (the app shows them): download > lab pass (`analyze.py`) > Claude checks
  (`/analyze-reference`: read EVERY contact sheet, write `review.json`, `report.py`; auto-detected types are drafts
  until reviewed) > the user's verdicts (app) > feedback to Claude > Share (Knowledge page).
- When the user pastes text starting with `MOTIONLAB FEEDBACK` (or says they gave feedback in the app: newest
  `analysis\<name>\feedback\app_*.txt`), follow "Applying feedback" in the skill: new lessons go to
  `knowledge\local\lessons.md` (id from `tools\knowledge.py next-lesson-id`), threshold changes in `config.json`,
  re-check the WRONG/PARTLY events and the possible misses marked EFFECT, run the self-test, and report exactly what
  changed. Also import pasted feedback into verdicts.json (`feedback.parse` + `motionlab.app.data.save_verdicts`).
  Afterwards remind the user of Knowledge > Share my knowledge.
- Reviewing incoming lessons (`knowledge\incoming\*.md`): skill section "Reviewing incoming lessons"; each becomes a
  shared `L###` rule in `lessons.md` or is dropped with a reason; delete the reviewed incoming file.
- Measured help for reviews (evidence only, never changes events): every flash gets a "flash look" line
  (`flash.look_*`), and each analysis lists "possible misses" (`near_miss`). Record a verdict per possible miss in
  review.json `"_near_misses"` (lessons L001, L006); the user answers them in the app (verdicts.json `misses`).
- Report and app layout follow the user's notes (2026-10-06/07): per effect the preview, "What happens" and
  "Measured evidence" are open; timing / origin / rebuild ("In depth") and the contact sheets ("Frame list") are
  folded; false alarms are folded (verdict optional); possible misses are red until answered.
- Recreating a reference 1:1 with the user's footage: the `/recreate-video` skill (option 1 = lab render, option 2 =
  the same edit as a DaVinci Resolve Studio project). "By feel" (a template, not 1:1) is planned for v0.5.
- Saving library effects: start from `projects\<name>\build\library_picks.json` and `[save to library]` notes; add a
  builder + `META` entry + test `CASES` in `tools\library.py`, then `library.py build` and `library.py test` (every
  macro must render in Resolve; `docs\resolve_notes.md`).
- Any change to `config.json` or `tools\motionlab\` must be followed by `selftest.py --extended` (all PASS).
- Publishing a new version (the repo owner = the user, with Claude's help): self-test `--extended` all PASS, raise
  `__version__` in `tools\motionlab\__init__.py`, add a `## x.y.z - date - title` section to `CHANGELOG.md` (the
  update banner shows it), raise `API_LEVEL` in `server.py` + `app.js` if the page needs new routes; the user commits
  and pushes. Installs pick it up at their next start.

## Environment gotchas (learned while building the lab)
- ffmpeg's `drawtext` filter segfaults on this Gyan build (no fontconfig file): draw labels with Pillow.
- ffmpeg's `loop` filter starts repeating one frame BEFORE `start`; `xfade`'s first transition frame is still
  100% of the outgoing clip. The test generator measures its ground truth from the rendered pixels for this reason.
- In the Bash tool, heredocs can swallow backslashes: write patch scripts with the Write tool, then run them.
- Pass paths to ffmpeg / Python as argument lists (no shell quoting); Windows paths with spaces are common.
