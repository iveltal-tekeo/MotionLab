# MotionLab

Local lab for analyzing music videos and vlogs: detect every edit/effect, show a frame-accurate visual breakdown
the user can verify, and later rebuild approved effects in DaVinci Resolve.

## Hard rules
1. **NEVER modify a source video** the user gives you (in `refs\`, in `projects\<name>\` or anywhere else): no
   re-encoding in place, renaming, moving, trimming or deleting. Only read it. All copies, CFR proxies, extracted
   frames, sheets and previews go into `analysis\<video name>\` (analysis) or `projects\<name>\build\` (renders).
   `tools\analyze.py` and `tools\prep_footage.py` refuse writes outside those folders and record/verify the source
   SHA-256; tell the user if a check ever reports a change.
2. **Every timestamp shown to the user must include the frame number AND the timecode** `HH:MM:SS:FF` at the
   video's real frame rate, e.g. `f480 (00:00:16:00)`, so the user can verify it. Reports, contact sheets,
   previews, chat and notes all follow this.
3. Read `.claude\skills\analyze-reference\lessons.md` before every analysis and apply it.

## Layout
- `refs\`       reference videos the user drops in or downloads (read-only); `refs\audio\` = MP3 downloads;
                `refs\downloads.json` = where each download came from (link, platform, uploader, id, duration)
- `analysis\`   one folder per analyzed video: `report.html` (open in a browser), `events.json` (all data),
                `metrics.csv` (per-frame signals), `overview.png`, `review.json` (Claude's reviews),
                `review_todo.md`, `events\<ID>\sheet_NN.jpg + preview.mp4`, `frames\`, `cuts\`, `audio.wav`,
                `proxy_cfr.mp4` (only for VFR sources), `cache\` (re-usable metrics), `feedback\`, `inspect\`,
                `meta.json` (category, tags, link - the user's choice, kept across re-runs)
- `knowledge\`  what installs share (`knowledge\README.md`, `tools\motionlab\knowledge.py`): `references\` = SHARED
                reference cards `<video id>--<author>.json` (category, format, link, pacing, every reviewed effect +
                verdict + note), `incoming\` = SHARED lessons waiting for review; private: `local\` (this PC's cards,
                `lessons.md` = new lessons `local-N`, `shared.json`, `summary.md` = short: norms / effects / corrections per
                category + `summary\<category>.md` = every reviewed effect; Claude reads both before a review),
                `inbox\` / `outbox\` (`*.mlpack.json` packs for friends without push access)
- `projects\`   production work (option 1 = renders made by the lab): `projects\<name>\` holds the user's footage
                (read-only, top level); everything we make goes to `projects\<name>\build\`: `sources.json`
                (IDs A, B, ... + SHA-256), `cache\` (grey 25 fps frame caches), `boards\` (storyboards),
                `edit_vN.py` -> `plan_vN.json` (the edit), `<name>_vN.mp4`, `compare\` (side-by-sides), `stills\`, `sheets\`,
                `resolve\` (option 2: LUTs, Fusion comps, carrier + stills, section renders, `checks\`, `edits\`),
                `<name>_resolve_vN.mp4` (the full render from Resolve), `pruned.json` (what storage.py deleted)
- `library\`    approved effects only (made by `tools\library.py`): `README.md` (index) + one folder per effect:
                `<effect>.md` recipe (source events with frames + verdicts, measured values, controls, presets, steps
                without the macro, lessons), `<stem>.setting` Fusion macro(s), `ref_fNNNNN.jpg` (reference frames),
                `check.png` (the macro rendered in Resolve | the real reference frame); test scratch (plates, frame
                cache, `checks.json`) lives in `analysis\<ref>\inspect\library_test\`
- `tools\`      the pipeline (Python 3.12 venv at `.venv\`, packages in `requirements.txt`; ffmpeg 9 on PATH)
- `MotionLab.bat` double-click = the MotionLab app (see "The app"); `.app\` = its cache (thumbnails, job logs,
                `server.log`, `open_claude.cmd`, `server.json` = port / pid / token / version of the running server);
                `settings.json` = the user's app settings (programs, downloads, default category, author name for
                sharing, update_check / update_auto); the user's app verdicts:
                `analysis\<name>\feedback\verdicts.json` + `app_<date>.txt` exports; library picks:
                `projects\<name>\build\library_picks.json`
- `docs\`       hand-off documents: `option2_resolve.md` (rebuild a project in DaVinci Resolve Studio),
                `roadmap.png` (where the lab stands; `tools\roadmap.py` redraws it), `organization.md` (repo/versioning
                plan), `knowledge_sharing.md` (how installs share what they learn: cards + reviewed lessons through the
                repo, packs as a fallback - no cloud DB)
- Repo files (v0.2, 2026-10-06): `README.md`, `setup.bat` (friends' install: .venv + program check incl. git, asks
                before each winget install, asks the name for sharing, shortcut), `LICENSE` (MIT), `CHANGELOG.md`
                (what's new - the app's update banner shows it), `.gitignore` (refs, analysis, projects, library,
                settings.json, .app, .venv, knowledge\local|inbox|outbox, selftest videos stay private),
                `.gitattributes` (LF in the repo, `.bat` always CRLF on disk: cmd misreads LF batch files),
                `MotionLab.ico` (`tools\app_icons.py` draws it). The version is `tools\motionlab\__init__.py`
                `__version__`. The repo is ready; the USER creates and uploads it - never `git init` / `git push` /
                create the GitHub repo unasked (the app's own Share / Update buttons are the user's clicks).
- `.claude\skills\analyze-reference\` the `/analyze-reference` skill (`SKILL.md`) and `lessons.md`

## Tools (run from C:\MotionLab as `.venv\Scripts\python tools\<tool>.py`)
- `analyze.py "<video>"` full pipeline (`--redetect` re-uses cached metrics after config changes, `--force` redo all,
  `--category <id>` (alias `--style`; ids in `tools\motionlab\styles.py`) and `--tags "a, b"` - both kept on re-runs
  in `meta.json`; afterwards it refreshes this video's reference card in `knowledge\local\references\`)
- `download.py <url> <preset>` yt-dlp wrapper the app's download job runs (presets `system.PRESETS`): prints
  progress, records the source in `refs\downloads.json`, prints the final file path last
- `knowledge.py cards | summary | pending | next-lesson-id | share | export | import <pack>` the Knowledge page from
  the command line (`share` = commit + push the pending cards / lessons, or a pack when that fails)
- `report.py <name>` merge `review.json` into `events.json` and re-render `report.html`
- `feedback.py <name> <file>` parse pasted report feedback, archive it, map verdicts to current events
- `sheet.py <name> <start> <end>` contact sheet + preview for any frame range (missed effects)
- `selftest.py [--extended]` regenerate-if-needed and score the synthetic test videos (must PASS after any change)
- `make_testvideo.py [--extended|--negative|--vfr]` build the synthetic test videos with ground truth
- `prep_footage.py <project>` decode a project's clips once into `build\cache\` (+ per-frame luma/motion stats)
- `storyboard.py <project>` / `storyboard.py --video <file> --out <dir>` 1-frame-per-second sheets (frame + timecode)
- `render_video.py <plan.json>` render a plan to MP4 with the song (`--stills`, `--sheet a:b:step`, `--range`,
  `--compare` = reference | render side by side with frame numbers; `--compare --left a --right b --range A B`
  compares frames A..B when b is a section render that starts at A)
- `resolve_build.py <plan.json> --replace` option 2: rebuild a plan as a native DaVinci Resolve Studio project
  (project = the project folder name, timeline `<project>_resolve_vN`; Resolve Studio must be running with
  external scripting = Local). `--sections S1,S2` builds part of it (sections in `SECTIONS`), `--render A B` renders
  frames A..B to `build\resolve\<timeline>_A-B.mp4`, `--render-full` to `build\<timeline>.mp4`, `--no-build` only
  renders, `--only u1,u2` re-imports just those Fusion comps (fast tuning), `--timeline X` works on another
  timeline, `--doctor` checks Resolve/media/LUTs/timeline (read-only), `--diff` lists what the user changed by
  hand in Resolve since the build. `--replace` keeps the old timeline (renamed `... (replaced <date time>)`);
  `--delete-old` deletes it; `--only` refuses to replace a hand-edited comp unless `--overwrite-edits` (saved
  first to `edits\<date time>\`). Writes `build\resolve\`: `luts\` (one .cube per grade/gain/flash), `comps\`
  (latest .comp per Fusion unit; `comps\imported\<sha1>.comp` = every version ever imported), `media\` (grey
  carrier clip, `stills\` = lab-rendered photo strips + mosaic wall levels), `<timeline>_build.json` (manifest:
  units, clips, LUTs, comp sha1 per unit), `edits\live\` (hand-edited comps as text, from `--diff`), `checks\`
- `compare_renders.py <left> <right> --range A B --out <dir>` per-frame |difference| (CSV) + left|right|diff sheets
  labelled with frame + timecode (`--right-start`: frame of the right video's first frame)
- `storage.py` disk report by category (source / keep / cache / checks / finals); `--prune <name|all> --what
  cache,checks,finals --yes` deletes only what the lab can rebuild (dry run without `--yes`), never sources,
  knowledge or media a Resolve project uses. Footage caches are the big item: ~2.6 GB per minute of footage.
- `app.py` the MotionLab app (`MotionLab.bat` starts it without a console): `--no-window --stay` = server only
  (testing), `--port N`, `--wait-port` (used by its own restart after an update); an OLDER server on the port is
  replaced (polite `/api/quit` with the token from `.app\server.json`, else `taskkill` of the listening python PID),
  only when it runs no job; `roadmap.py` redraws `docs\roadmap.png` (edit its STAGES / VERDICT when the state changes)
- `library.py build [effect ...]` writes `library\` (macros from the `fx_*` builders + recipes from `META` /
  `RECIPE_ONLY`; reference frames decoded read-only with a SHA-256 check); `library.py test [effect ...]` renders
  every macro (`CASES`) in a throwaway Resolve project `motionlab_scratch` (deleted afterwards; the open project is
  saved and reopened), measures it against the real reference frames and writes `check.png` + the numbers into the
  recipe; `library.py title "TEXT"` = a pixel-font title macro for any text (`library\pixel-title\variants\`).
  Macros: effects = MainInput1 -> MainOutput1; titles draw on a 1920x1080 canvas placed at native size (Position /
  Size / Opacity); additive light = alpha 0 after the colour (ChannelBoolean ToAlpha=15). Values only from the
  reviewed analysis, the user's feedback and the verified test_4am rebuild (`resolve_build` FIREWORK, blur_size,
  text_strokes). `library.py install | uninstall | verify-install` (Resolve Templates\Edit\{Titles,Effects}\MotionLab,
  Macros\MotionLab; recorded in library\installed.json) writes outside the lab: only when the user asks (on the
  roadmap for later; 2026-10-06 the user postponed it).

## The app (tools\app.py + tools\motionlab\app\: server.py, data.py, jobs.py, ui\ = plain HTML/CSS/JS)
- Python standard library only (nothing installed): a server on 127.0.0.1:8765 + Microsoft Edge in app mode (its
  own window). It stops ~10 s after the window closes (3 min without heartbeat), unless a job runs. Security: Host
  header check, a session token on every POST, `/files/` serves read-only from analysis, projects, refs, docs,
  library, knowledge only. Writes only: verdicts / feedback exports, library picks, `.app\`, `settings.json`,
  downloads into `refs\` (+ `refs\audio\`), `analysis\<name>\meta.json` (category / tags), `knowledge\` (cards,
  summary, packs, imports), and - on a click - a Desktop / Start-menu shortcut, git pull (Update) / commit + push
  of `knowledge\` only (Share).
- Pages (renamed 2026-10-06 at the user's request; routes keep their old names #/refs, #/projects): Home (status,
  update banner, next steps, setup warnings, roadmap), **References** (#/refs: other people's videos - Download from
  a link, Analyse a video with its category + tags, filters by category / tag, cards with format + pacing, then the
  analysis page: frame-accurate player with frame + timecode, timelines, every effect with sheets / preview / rebuild
  notes, verdicts Correct / Partly / Wrong + notes, missed effects, "Send feedback to Claude", edit category / tags),
  **Videos** (#/projects: the user's own footage - versions, renders, timing check, Resolve check-up / what changed by
  hand / library picks), **Knowledge** (#/knowledge: Share my knowledge, packs in `knowledge\inbox\` to import,
  incoming lessons to review in Claude Code, pacing + effects per category, every card), Library, Jobs, Storage,
  **Settings** (programs found + versions + how to install, yt-dlp path / format / file name, Claude Code path,
  default category, shortcuts, Sharing & updates: name, GitHub remote, check / auto-install updates, Check now,
  Update now, Connect to GitHub for ZIP installs). `tools\motionlab\app\system.py` = settings, program detection,
  the download command, the Claude launcher, shortcuts; `updater.py` = git (check / apply / share / connect).
- Updates (`updater.py`, git only - no GitHub API, no tokens in the lab): `check` = `git fetch` + behind / ahead /
  local changes + the new version (read from `origin:tools/motionlab/__init__.py`) + its CHANGELOG section;
  `apply` = `git pull --rebase --autostash`, `pip install -r requirements.txt` if it changed, then the server
  restarts itself (`restart_soon`: a new `app.py --wait-port`, the window shows "Updating..." and reloads). At
  start-up (3 s in, only within 180 s and with no job) a found update installs itself if `update_auto`; later checks
  (every 6 h) only show the banner. A local change that clashes with an update (e.g. a threshold tuned in
  `config.json` that the update changes too) is set aside: the file gets the new version, the change stays in git's
  stash ("autostash"), and the restarted app says so (`.app\update_last.json`) - bring it back with
  `git stash show -p` if it is still wanted. `share` commits only the knowledge paths and refuses while the copy
  has commits that are not on GitHub (a push would publish them); a rejected push pulls (rebase) and pushes again;
  on failure our commit and new files are undone and the pack remains. If sharing pulled new code the server
  restarts too.
- Versions: `server.VERSION` = `__version__`; the page carries `<meta name="ml-version">` and `API_LEVEL` (app.js)
  and the ping returns version / api / phase / update: a newer page on an older server shows "Restart now", a new
  server version reloads the page. Raise `API_LEVEL` in BOTH `server.py` and `app.js` when the page needs new
  server routes.
- "Open in Claude Code" buttons (sidebar, next steps, analyse dialog, feedback, library, incoming lessons) start
  Claude Code in a new console in the lab folder with the app's fixed hand-off text (`.app\open_claude.cmd`;
  characters cmd would interpret are stripped). Downloads = `tools\download.py` around yt-dlp (`system.PRESETS`:
  MP4 <=1080p / best / MP3; one video, no playlists; the final path is printed last so the dialog offers
  "Analyse it", which opens the analyse dialog with the file).
- Jobs = only the lab's own tools + yt-dlp downloads, a fixed list in `jobs.py` (analyze, report, Resolve doctor /
  diff, storage + prune, self-test, verify_timing, download), one per group (cpu / resolve / light / net). Claude's
  parts stay in Claude Code: reviewing sheets, applying feedback, reviewing incoming lessons, building in Resolve,
  saving library macros.
- After changing the app: start `app.py --no-window --stay --port 879x` (NOT 8765: the user's own app may run there
  and a different version would be replaced), check every page with headless Edge (`msedge --headless=new
  --dump-dom` / `--screenshot`, own `--user-data-dir`; clicks via the DevTools protocol), stop that server. Liveness
  checks must not use `/api/ping` (it is the heartbeat and keeps the server alive). Updates / sharing are tested
  against a local bare repo as a fake GitHub with two clones as friends (never the real remote).
- `config.json` every detection threshold (`_comment` keys explain units); `motionlab\` the package
  (`compose.py` = the compositor, `graphics.py` = pixel font / seven-segment / firework / streaks,
  `fusion.py` = writes Fusion .comp text: tools, keyframes (`Spline`, `Path`), expressions, MediaIn by media ID)

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
- Levels: `prep_footage.py` caches expand video range once (cache meta `"levels": "single"`). Plans say which
  caches they were designed on: `"levels": "double"` = the old caches that expanded twice (test_4am v1: keeps its
  contrast); default "single". The compositor and the Resolve LUTs both convert accordingly.
- Hand edits in Resolve are the user's: never overwrite them silently (`--diff` first); good ones become knowledge.

## Workflow
- `/analyze-reference <path>` runs everything (see the skill): pipeline, then Claude reads EVERY contact sheet and
  writes `review.json`, then `report.py`. The auto-detected types are drafts until reviewed.
- When the user pastes text starting with `MOTIONLAB FEEDBACK` (or says they gave feedback in the app: newest
  `analysis\<name>\feedback\app_*.txt`), follow "Applying feedback" in the skill: new lessons go to
  `knowledge\local\lessons.md` (id from `tools\knowledge.py next-lesson-id`; they apply on this PC at once and are
  shared for review), threshold changes in `config.json`, re-check the WRONG/PARTLY events, run the self-test, and
  report exactly what changed. Afterwards remind the user of Knowledge > Share my knowledge.
- Reviewing incoming lessons (`knowledge\incoming\*.md`, from friends' Share; skill section "Reviewing incoming
  lessons"): each becomes a shared `L###` rule in `lessons.md` (merged / reworded / tagged with a category) or is
  dropped with a reason; delete the reviewed incoming file. Config / code changes suggested by a lesson go through
  the self-test like any change. Share commits `knowledge\references`, `knowledge\incoming` (incl. deletions) and
  the shared `lessons.md` (`updater.KNOWLEDGE_PATHS`), so the user's next Share publishes the review.
- Publishing a new version (the repo owner = the user, with Claude's help): self-test `--extended` all PASS, raise
  `__version__` in `tools\motionlab\__init__.py`, add a `## x.y.z - date - title` section to `CHANGELOG.md` (the
  update banner shows it), raise `API_LEVEL` in `server.py` + `app.js` if the page needs new routes; the user commits
  and pushes. Installs pick it up at their next start.
- Saving library effects: start from `projects\<name>\build\library_picks.json` (the user's ticks + notes in the
  app) and `[save to library]` notes in app feedback; add a builder + `META` entry + test `CASES` in
  `tools\library.py`, then `library.py build` and `library.py test` (every macro must render in Resolve).
- The user's verdicts have ONE home: `analysis\<name>\feedback\verdicts.json` (the app writes it; report.html starts
  from it and keeps local changes in the browser under the video name, so a re-run does not hide them). When feedback
  is pasted, also import it there (`feedback.parse` + `motionlab.app.data.save_verdicts`).
- Measured help for reviews (evidence only, never changes events): every flash gets a "flash look" line (lit area,
  level, texture: flat solid vs over-exposed picture; `flash.look_*`), and each analysis lists "possible misses"
  (`near_miss`: sudden changes no event or cut explains; in review_todo.md, report.html and the app). Record a
  verdict per possible miss in review.json `"_near_misses"` (lessons L001, L006).
- Report and app layout follow the user's 2026-10-06 notes: per effect only the preview, "What happens" and
  "Measured evidence" are open; timing / origin / rebuild ("In depth") and the contact sheets ("Frame list") are
  folded; false alarms are folded to one line (verdict optional, "Agree with all false alarms"); rows alternate.
- Any change to `config.json` or `tools\motionlab\` must be followed by `selftest.py --extended` (all PASS).
- Rebuilding a reference's style with the user's footage (option 1): prep + storyboard the footage, measure the
  reference's timing (`build\ref_timing.py`: panel cuts and per-frame pan / flicker / fade / zoom curves), write
  `edit_vN.py` (frame numbers = the reference's when the song is the same), check `--sheet` stills, render,
  `--compare`, then `verify_timing.py` (does the render change on the reference's key frames). Option 2 = the same
  edit as a DaVinci Resolve Studio project: `resolve_build.py <plan> --replace`, then per section `--render A B` +
  `compare_renders.py` against the lab render, then `--render-full` + `verify_timing.py <timeline>`.
- Before changing a Resolve project the user may have touched: `--doctor` (a NOTE line counts hand edits) and
  `--diff`. To verify the lab's version without touching their edits, duplicate the timeline
  (`Timeline.DuplicateTimeline`) or build a separate one with `--timeline X`, render that, then delete it.

## Option 2: how resolve_build.py maps a plan to Resolve (details: docs\option2_resolve.md, code comments)
- Timeline 1520x1080 25 fps starting at 00:00:00:00 (plan frame f = timeline frame f), A1 = reference audio, V1 = a
  grey 0.045 ProRes carrier clip = the background; every Fusion comp sits on a piece of that carrier.
- Static panels = Edit-page clips of the original DJI files (in-point 2 x cache frame) with Edit-page Zoom/Pan/
  Tilt/Crop reproducing `compose.sample_patch` exactly; grades = Color-page LUTs; flash frames = 1-frame cuts with a
  flash LUT; holds = freeze frames. Animated layers = Fusion: pan boards (panels + ONE Transform keyed per frame),
  fades (grey overlay keyed per frame), titles (rectangles), clocks (polygons), streaks, fireworks (particles),
  mosaic (ONE `MosaicZoom` control keyed per frame; the wall = lab-rendered level images), grain (Linear Light).
- LUTs: Resolve's Color page only applies LUTs from its LUT folders, so the build copies them to
  `C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\MotionLab\<project>\` (outside the lab: ask the user
  once before the first build on a PC - the original user approved it on theirs).
  For `"levels": "double"` plans they include the old caches' extra tv->full step (Resolve decodes correctly).
- Drift check: the manifest + `comps\imported\<sha1>.comp` record exactly what each timeline got; `--diff` compares
  every comp input (static ones at first/middle/last frame, keyed ones on every frame), connections, expressions,
  added/deleted tools, Edit-page transform, in-point, LUT, extra Color nodes, opacity/composite/enabled, missing or
  added clips. Tested on scripted edits in a scratch project (all caught). test_4am: the user's grain edit (strength
  0.0077 -> 0.0157, size 1 -> 1.63) is kept in the timeline; `build\test_4am_resolve_v1.mp4` used the lab grain.
- Verified 2026-10-06: full render vs v1 1.83/255 mean |difference|, 53/54 key frames (v1 51/54); the same timeline
  renders identically before and after reopening the project.

## Resolve 21.1 scripting gotchas (measured on PC 2, 2026-10-05)
- `ImportMedia([path])` (list form) works, the documented dict form returns None. `AppendToTimeline` endFrame is
  exclusive, in source frames (50 fps for DJI). `SetSettings`: one key per call for timeline settings (a combined
  call froze Resolve); render settings one key per call too (H.264 refuses `VideoQuality`).
- Speed 0 freezes the FIRST frame only when the playhead is before the clip (after it: last frame; inside it:
  Resolve splits the clip). Edit page: Tilt is in units of 1080/1140 px for 4:3 sources; crop is in input-scaled
  source px before zoom.
- A clip's Fusion comp starts at frame 0 on the clip's first frame (keys must be offset by the clip start); on a DJI
  clip it runs in 50 fps source frames at 3840x2880, so comps go on the 25 fps carrier.
- Never `comp.AddTool("Loader")` in a live Resolve: it opens a file dialog that blocks scripting (the user saw it);
  write comps as text and `ImportFusionComp`. Fusion's Loader cannot read the DJI HEVC files; `MediaIn` by media ID
  can. Give every panel / still its OWN MediaIn: many TimeStretchers on one long-GOP HEVC MediaIn = a keyframe seek
  per request (a 600-frame section estimated 100 h, and cancelling it hung Resolve).
- Keep comps lean (the user saw Resolve crash on heavy Fusion work): ~40-90 tools per comp is fine; the first mosaic
  (499 tools, 75 live 4K decodes) and live photo strips were replaced by lab-rendered stills + native animation.
- Fusion: chained masks need PaintMode Maximum (Merge paints a level-0 shape OVER the mask = erases it); Custom tool
  has no `pow()` (returns 0, use `^`); a Custom tool's alpha-0 output is premultiplied to black (use ChannelBoolean
  ToAlpha=15 afterwards); output with alpha 0 adds onto the tracks below; Resolve clips negative added values (grain
  = Linear Light layer 0.5 + n/2); Gaussian Blur size -> sigma is non-linear (table `BLUR_CAL`); particles: velocity
  1 = 152 px/frame, drag v *= 1 - k per frame, disable pre-roll, Line style needs RotationMode 1; ErodeDilate amount
  is NOT pixels (1.0 whitened the frame).
- A script that exits while Resolve renders makes Resolve abort the render: `Session.render` re-fetches the project
  when a scripting object drops out instead of exiting.
- Macros (MacroOperator) in an imported comp: connections across the macro boundary must name the REAL tools (the
  plate -> the macro's first tool, the macro's last tool -> MediaOut1); a link to the macro's own output
  (`SourceOp = "ML_x", Source = "MainOutput1"`) is silently dropped on import, MediaOut1 has no input and the job
  fails ("The Fusion composition at ... could not be processed successfully"). A failed comp still leaves output
  files - stale frames of OTHER comps - so always check `GetRenderJobStatus(...)["JobStatus"] == "Complete"`.
  Resolve turns a Loader of a still into a media-pool Loader (MEDIA_ID) on import; UserControls + expressions on
  tools inside a macro survive.
- EllipseMask Width AND Height are fractions of the mask WIDTH (a circle of d px: Width = Height = d / W); measured
  2026-10-06 (round colon dots came out 1.78x tall with d / H). RectangleMask Height is a fraction of the HEIGHT
  (pixel-exact in the test_4am rebuild). test_4am v1's f705 circle and firework cores were drawn with d / H (fixed in
  resolve_build for the next build; the existing timeline is unchanged).
- Fusion Transform: Size scales about Pivot, Center only translates (out = P + (X - P) s + Center - 0.5); verified
  against 4AM's mosaic zoom (tile path within 1 px).
- (2026-10-06) Fusion tools that generate images (Background, Rectangle/Polyline/Ellipse masks, FastNoise, pRender)
  with Depth = Default render in 8-bit right after `ImportFusionComp` and in float after the project is reopened
  (the comp prefs say float both times): the same timeline rendered differently before/after a reload. The builder
  sets Depth = 4 (float32) on them (`GEN_DEPTH`); Film Grain in float has no mean bias (the old "bias" was 8-bit
  rounding of the mid grey). Always compare renders, not just input values, when testing persistence.
- `GetSourceStartFrame()` floors start time x fps and reads one source frame low on some clips; `GetLeftOffset()`
  (timeline frames) is exact. `SetInput(id, v)` without a time on a keyed input changes nothing - pass the frame.
  `TimelineItem.ExportFusionComp(path, 1)` and `Timeline.DuplicateTimeline(name)` work. Fusion auto-creates
  `LUTBezier` modifiers (particle over-life curves, Custom tool LUTs): not user edits.
- Throwaway tests go in a scratch project (`motionlab_scratch`, deleted afterwards), never in the user's project;
  scripts that switch projects must end with `LoadProject("<the user's project>")`.

## Environment gotchas (learned while building the lab)
- ffmpeg's `drawtext` filter segfaults on this Gyan build (no fontconfig file): draw labels with Pillow.
- ffmpeg's `loop` filter starts repeating one frame BEFORE `start`; `xfade`'s first transition frame is still
  100% of the outgoing clip. The test generator measures its ground truth from the rendered pixels for this reason.
- In the Bash tool, heredocs can swallow backslashes: write patch scripts with the Write tool, then run them.
- Pass paths to ffmpeg / Python as argument lists (no shell quoting); Windows paths with spaces are common.
