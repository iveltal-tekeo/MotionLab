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
| edit the user's footage like references (1:1 or by feel, a quick draft) or from their words; then Resolve | the `/recreate-video` skill |
| a script to say on camera: improve one for reach or write one from zero (Prepare), hooks | the `/write-script` skill |
| titles, thumbnails, a video's package (description, chapters, hashtags), YouTube's A/B test | the `/write-title` skill |
| prompts: the user pastes / asks for video-model shots (Seedance...), briefs, image prompts | the `/write-prompt` skill |
| a video from zero: a motion-graphics video (HyperFrames), a plan + prompts for AI video tools | the `/generate-video` skill |
| what to do next: status, unreleased changes, roadmap, plans, ideas, what waits on the user | the `/whats-next` skill |
| anything in DaVinci Resolve (resolve_build.py, Fusion comps, library.py test / install) | `docs\resolve_notes.md` |
| the app (`tools\app.py`, `tools\motionlab\app\`) | `tools\motionlab\app\CLAUDE.md` (loads by itself there) |
| knowledge sharing (cards, lessons, packs) | `docs\knowledge_sharing.md`, `knowledge\README.md` |
| questions about working with Claude, effort levels, tokens | `docs\claude_tips.md` |
| a Claude Code cloud session (Linux, no videos): what works, the setup hook | `docs\cloud.md` |
| what comes next (planned versions and their design notes) | `docs\plans.md` (the app's What's new shows it); ideas not picked yet: `docs\ideas.md` |

Every tool starts with a usage docstring: read its first lines (or run it without arguments), not the whole file.

## Layout
- `refs\` reference videos the user drops in or downloads (read-only); `refs\audio\` = MP3 downloads;
  `refs\downloads.json` = where each download came from (link, platform, uploader, id, duration)
- `analysis\thumbs\<set>\` = a thumbnail set (0.4.5: `set.json`, `img\`, `sheet_N.png`, Claude's `style.json`, the
  user's `verdicts.json`) - not a video analysis
- `analysis\<video name>\` one per analyzed video: `events.json` (all data), `report.html`, `review.json` (Claude's
  reviews), `review_todo.md`, `events\<ID>\sheet_NN.jpg + preview.mp4`, `frames\`, `cuts\`, `metrics.csv`,
  `overview.png`, `audio.wav`, `proxy_cfr.mp4` (only for VFR sources), `cache\` (re-usable metrics), `inspect\`,
  `meta.json` (category, tags, focus, link - the user's choice, kept across re-runs), `content\` (transcript, stats),
  `colour\colour.json` (0.4: the look per shot + summary, `motionlab\colour.py`),
  `feedback\` (`verdicts.json` = the
  user's verdicts, their ONE home; `app_<date>.txt` = exports from the app; `feedback_<date>.txt/.json` = archived by
  `feedback.py` when Claude applied them)
- `knowledge\` what installs share: `references\` = SHARED reference cards `<video id>--<author>.json`, `incoming\` =
  SHARED lessons waiting for review; private: `local\` (this PC's cards, `lessons.md` = new lessons `local-N`, `lessons_making.md` = lessons on making
  videos `local-make-N`,
  `shared.json`, `summary.md` + `summary\<category>.md` - Claude reads both before a review, `memory.md` = Claude's
  memory (0.4: every video's style in one line, the effects seen and how they were made - read before an edit or a
  prompt; `knowledge.py memory` rebuilds + prints it), `prompts\<kind>\<id>.json`
  = the prompt library, ratings included; `prompts\requests\req-NNN.json` = Prepare's script requests), `inbox\` / `outbox\`
  (`*.mlpack.json` packs for friends without push access)
- `projects\<name>\` the user's footage (read-only, top level); everything we make goes to `build\`: `sources.json`
  (IDs A, B, ... + SHA-256), `cache\` (grey frame caches), `boards\`, `edit_vN.py` -> `plan_vN.json` (the edit),
  `<name>_vN.mp4`, `compare\`, `stills\`, `sheets\`, `resolve\` (option 2), `<name>_resolve_vN.mp4`,
  `library_picks.json` (the user's picks in the app), `pruned.json`, `edit_request.json` (0.4: what *New edit*
  asked for), `made_from.json`, `draft_vN.md` + `draft\` (the quick draft's notes, beats, sound), `colour\`
  (match LUTs `match_*.cube`),
  `generate_request.json` (0.4: a video from zero, Generate) + `ai_plan.md` (the shots for AI tools), `publish\`
  (0.4.3: the ready-to-post package - `package.json`, title / description / hashtags .txt, `thumb_<A|B|C>_16x9 /
  _9x16 / _9x16_crops.png`, `thumbs\<id>\` = each thumbnail as an editable graphic, `candidates\`, `images\` =
  pictures the user brought, e.g. from an AI image tool)
- `fonts\` the font library (0.4.6, in the repo): one folder per family (.ttf + its licence: SIL OFL 1.1 / Apache 2.0)
  + `fonts.css`; graphics, captions and thumbnails pick from it (`motionlab\fonts.py`), each render gets copies of the
  fonts it uses in its own `assets\fonts\`
- `library\` approved effects only (made by `tools\library.py`): `README.md` + per effect `<effect>.md` recipe,
  `<stem>.setting` Fusion macro(s), `ref_fNNNNN.jpg`, `check.png`; `library\graphics\<name>\` = approved HTML
  graphics with their settings + rendered .mov (`overlay.py save`; `motionlab\overlay_settings.py`)
- `tools\` the pipeline (Python 3.12 venv at `.venv\`, `requirements.txt`; ffmpeg on PATH); `tools\motionlab\` the
  package (`compose.py` compositor, `graphics.py` pixel font / seven-segment / firework / streaks, `fusion.py` Fusion
  .comp text, `knowledge.py`, `app\` the app); `tools\config.json` every detection threshold (`_comment` keys
  explain units)
- `docs\` hand-offs: `resolve_notes.md`, `option2_resolve.md`, `claude_tips.md`, `knowledge_sharing.md`,
  `organization.md` (repo/versioning plan), `roadmap\` (`roadmap.json` = the roadmap's ONE data file, `index.html` =
  the motion graphic drawn from it, played live on the app's Home) -> `roadmap.png` (README; `roadmap.mp4` stays local)
- `.app\` the app's cache and logs (`server.log`, `deleted.log`, `jobs\` + `jobs\history.jsonl` (0.4.4: jobs ended),
  `batches\` (0.4.5: bulk Claude work), `open_claude.cmd`, `server.json`);
  `settings.json` = the user's app settings; `.claude\skills\` = `analyze-reference\` (+ `lessons.md`),
  `write-script\` (+ `guidelines.md`), `write-title\` (+ `guidelines.md`), `recreate-video\`, `generate-video\`,
  `write-prompt\`, `whats-next\`
- Repo files (v0.4.1): `README.md`, `setup.bat`, `LICENSE` (MIT), `CHANGELOG.md` (the Update button's dialog shows
  it), `.mcp.json` (MotionLab's MCP server), `.claude\settings.json` (a SessionStart hook: cloud sessions only, docs\cloud.md), `.github\workflows\tests.yml` (GitHub's tests, see Publishing),
  `.gitignore` (refs, analysis, projects, library, settings.json, .app, .venv, knowledge\local|inbox|outbox and the
  self-test videos stay private), `.gitattributes` (LF in the repo, `.bat` always CRLF), `MotionLab.ico`. The
  version is `tools\motionlab\__init__.py` `__version__`. The USER creates and uploads the repo - never `git init` /
  `git push` / create the GitHub repo unasked (the app's own Share / Update buttons are the user's clicks).

## Tools (run from C:\MotionLab as `.venv\Scripts\python tools\<tool>.py`)
- `analyze.py "<video>"` full pipeline (`--redetect` re-uses cached metrics after config changes, `--force` redo all,
  `--category <id>` (alias `--style`; ids in `tools\motionlab\styles.py`), `--tags "a, b"` and `--focus
  content|cinematic|both` (0.4: what the user asked to look at; content adds the transcript + views via
  `content.py auto`) - all kept on re-runs in `meta.json`; afterwards it refreshes this video's reference card in
  `knowledge\local\references\`). `motionlab\profile.py` = the video in numbers per focus (rhythm, hook, talking,
  text on screen, signature effects, transitions) - the app's Overview, the cards and `review_todo.md` use it
- `report.py <name>` merge `review.json` into `events.json` and re-render `report.html`
- `feedback.py <name> <file> [--import]` parse feedback text, archive it, map verdicts (and possible-miss and
  sound-effects answers) to events; `--import` also writes them into verdicts.json
- `sheet.py <name> <start> <end>` contact sheet + preview for any frame range (missed effects)
- `content.py transcript <name> | show <name> [a b] | stats <name>` what a video says (0.3.5): the platform's subtitles
  -> `analysis\<name>\content\transcript.json`, frame + timecode per line / word (MCP `transcript`); `stats.json` =
  views, likes, comments, followers, upload date, views / followers (+ history); both stay local (app: What it says
  tab); no subtitles or no link -> speech to text of the analysis' audio when installed (`auto` / `speech_transcript`);
  `thumbnail <name>` (0.4.3; `stats` / `transcript` do it too) = the video's own thumbnail -> `content\thumbnail.*`
- `thumbnail.py candidates <project|video> [--n 12] | make <project> --id A (--frame f [--clip id] | --image file)
  --words "..." [--template outline|block|split] [--set k=v] | render <project> --id A | check <image|project>
  [--title] [--script id|file] [--niche] | refs | templates | platforms | selfcheck` thumbnails (0.4.3): candidate
  frames (sheet with frame + timecode), HTML templates (`tools\overlays\thumbnails\`) as stills at 1280x720 + 1080x1920
  + the grid-crops preview, the check (PASS / WARN / FAIL per rule with its number; owns package.json "candidates" /
  "thumbnails"); faces = OpenCV's YuNet model shipped in `tools\models\` (227 KB, MIT; README there)
- `publish.py chapters <project> [--from plan|transcript] | write <project> --title "..." [--chapters "f|name;..."]
  [--hashtags "#a #b"] [--titles title-NNN] | show | selfcheck` the ready-to-post words (0.4.3): chapter points with
  frame + timecode, then title / description (YouTube `0:00` chapters) / hashtags + package.json (its keys only);
  YouTube's rules checked first (dated in `.claude\skills\write-title\guidelines.md`), nothing written on a FAIL
- `script.py check <file|script id> [--length s] [--like ...] | show <id|req-NNN> | requests` Prepare's script check
  (no Claude: hook, length at a measured speaking rate, flat stretches, fillers, CTA...; rules in
  `.claude\skills\write-script\guidelines.md`) and the app's requests, for `/write-script`
- `prompts.py list | show | import | annotate | kind | style | rate | template` the prompt library (0.4; MCP
  `prompts`; kinds brief (a brief for Claude to make a video) / shot / image / hook / script / title (0.4.3: titles +
  thumbnail concepts + hook, from a title request `script.save_title`, kind "title"); annotate = Claude's
  check per part; style = analysed references whose measured style a prompt follows, `knowledge.style()`)
- `speech.py install | status | transcribe <video> [--names "..."] [--model small|base]` speech to text for your
  own videos (faster-whisper on the CPU, optional install; chosen 2026-10-12 after measuring) -> words with frame +
  timecode in `projects\<p>\build\speech\`; `overlay.py captions --from <video>` uses it
- `style.py <video> [<video> <video>] [--preset id] [--want "..."]` the style of up to 3 analysed videos merged (0.4):
  rhythm, hook, effects per minute with examples (frame + timecode, how made, verdicts), talking / captions, colour;
  `closest "<words>" [--n 3]` (0.4.2) = the analysed videos (this PC's + friends' cards) whose measured style is
  nearest the user's words, one line of numbers each (`FEEL_WORDS` in `motionlab\style.py`); `--feels` = the feels
- `draft_edit.py <project> --like <videos> | --preset <id> | --feel <id> [--want "..."] [--length s] [--format ...]
  [--music f] [--sound talk|clips|music] [--render]` a quick first edit by rules (0.4, the app's *Quick draft now*):
  beat-cut shots, the best moments, the style's effects; talking mode cuts the pauses -> `build\plan_vN.json` +
  `draft_vN.md`; Claude refines it (`/recreate-video` section 6). `--feel-test [--want ...] [--feels a,b,c]`
  (0.4.2, starting blind) = 2-3 hooks of the first 3 s in different feels, small, side by side ->
  `build\feel\feel_N\compare.mp4` + `sheet.png` + `feel.md` (~5-10 s, no Claude)
- `colour.py <analysis> | match <project> --like <videos> [--strength 0.8]` the colour and look (0.4): per shot and for
  the video in words + numbers -> `analysis\<name>\colour\colour.json` (analyze.py does it for the cinematic / both
  focus); `match` = a .cube that moves the footage toward the videos' look (`build\colour\`, Resolve's Color page, a
  plan grade `"lut3d"`) + how close (0-100)
- `fonts.py list | sync | check <graphic> | selfcheck` the font library (0.4.6): families with group, licence,
  weights; `sync` after adding a family = every shipped design's font setting offers the whole library (HyperFrames
  checks a value against the declared options); renders / snapshots copy the used fonts into the graphic by themselves
- `beats.py <song> [--fps 30] [--start s] [--length s]` a song's beats, downbeats and drops as frame + timecode (0.4: timing
  a motion-graphics video, `/generate-video`)
- `precheck.py <render.mp4 | graphic .mov | snapshot folder> [--sfx <name>_sfx.json] [--motion-blur N]` checks before
  the final render (0.4.2): parts that vanish for 1-2 frames, moves over 60 px a frame without motion blur (or with
  copies measured between its sub-frames), sound effects too loud / buried / limited -> `<build>\checks\<name>_precheck
  .json` + `.png` (frame + timecode per tile); exit 1 = look; footage moves only noted; `selfcheck`
- `sfx.py cues <graphic|cues.json|plan.json> [--set id=v] | make <...> --song <audio|none> | plan <plan.json> | kinds |
  selfcheck` sound effects (built 2026-10-14 for 0.5.0): synthesised, seeded; a graphic's cues = overlay.json "cues"
  (formulas of its settings), a plan's zooms / whips / flashes become cues; each effect levelled against the song where
  it sounds -> `build\sfx\<name>_sfx.wav` (Resolve track), `_mix.wav` (the plan's "audio"), `_sfx.json`; never guess a
  volume
- `whatsnext.py [--fetch]` one digest of where the lab stands (version, unreleased commits, plans' status lines,
  roadmap, ideas, what waits on the user) - the `/whats-next` skill starts from it
- `thumbsets.py fetch <set> <channel link> [--n 15] [--order newest|views] | more <set> [--n 20] [--order ...] |
  refresh <set> | links <set> <urls> | add <set> <pictures> | measure | sheet | fontmatch <set> | list | show | remove-item |
  selfcheck` thumbnail sets
  (0.4.5): only the pictures (no video; the channel listed whole, taken in batches) -> `analysis\thumbs\<set>\`
  measured + numbered sheets; Claude's patterns = `/analyze-reference thumbs <set>` -> style.json; used by
  `thumbnail.py make / check --style <set>`; `fontmatch` (0.4.6, ~2 s) = the words Claude listed in style.json
  "texts" compared by shape with the font library -> `fontmatch.json`, the font *In the style of* uses. Bulk Claude work = `.app\batches\<id>.json` (`/analyze-reference batch
  <id>`, `/recreate-video batch <id>`)
- `usage.py sessions | project <p> | analysis <name> | check | selfcheck` What it took (0.4.4): Claude's time per
  step, read-only from Claude Code's session logs (`motionlab\usage.py`: per round, what counts for a video) + the
  app's jobs (`.app\jobs\history.jsonl`); the app shows time only (the user's call); `check` = the tokens against
  Claude Code's own cost notes, proving the logs are read right
- `selftest.py [--extended]` regenerate-if-needed and score the synthetic test videos (must PASS after any change);
  `make_testvideo.py [--extended|--negative|--vfr]` builds them with ground truth
- `knowledge.py cards | summary | memory | pending | next-lesson-id [--kind making] | share | export | import <pack>`
  (`memory` = Claude's memory, also MCP `knowledge(category="memory")`; it starts with the user's ratings of all their
  videos (`build\outcome.json`) as rules; lessons on making videos: `local-make-N` -> M### in
  `.claude\skills\recreate-video\lessons.md`, shared as `knowledge\incoming\*-making.md`)
- `download.py <url> <preset> | selfcheck` the yt-dlp wrapper the app's download job runs; a post's files are all
  kept (downloads.json `post` / `part` / `parts`, 0.4.2.1); the user's browser login only when Settings has it on.
  `.app\player\` = player copies (H.264, same frames, when the browser can't play a video; `tools\dev\player_check.py`)
- Rebuilding (see `/recreate-video`): `prep_footage.py <project>`, `storyboard.py <project>`,
  `render_video.py <plan.json>`, `compare_renders.py`, `overlay.py new [--from <graphic>] | render | stills | snap
  <folder> 0,38,113-116` (snap = stills straight from the HTML, no render, ~3 s for 1, ~7 s for 10 - the cheapest
  check; `new`'s helpers set / to / ft / bump / smear keep a motion-blur render and a snapshot = a plain render) (graphics
  as HTML via HyperFrames, pinned in `tools\overlays\`; `settings | set` = the values the user can change, `save |
  graphics` = the graphics library; `fit <folder> --like <video>` = a size-independent graphic takes a video's size; `captions <folder> --from
  <.srt|.vtt|transcript.json|video> [--preset clean_box]` = styled captions + an
  .srt for Resolve; `preset <folder> [id]` = a graphic's ready-made looks (presets.json: captions Classic / Clean box); `refresh` = swap it in the open Resolve project (Resolve gets numbered copies: it locks files); `versions | upgrade-test | pin` = adopt a newer one only after its frames match); Resolve (see `docs\resolve_notes.md`): `resolve_build.py`,
  `library.py build | test | title | install`, `resolve_mcp.py install | status | remove` (optional Resolve MCP for
  Claude Code, this PC only)
- `storage.py` disk report by category; `--prune <name|all> --what cache,checks,finals --yes` deletes only what the
  lab can rebuild (dry run without `--yes`), never sources, knowledge or media a Resolve project uses. Footage
  caches are the big item: ~3.9 GB per minute of footage in colour (2.6 grey).
- `mcp_server.py` MotionLab's MCP server (`.mcp.json`; read-only: events, sheets, frames, verdicts, projects,
  stills - prefer its tools to reading events.json)
- `app.py` the app (`--no-window --stay --no-update --port N` = a test server); `roadmap.py check | sync | show |
  render [--video]` = the roadmap: after plans.md / CHANGELOG.md change, `sync` (adds / drops versions, "here"), edit
  labels / a new major's icon + line in `docs\roadmap\roadmap.json`, `check`, `render` (majors = x.y.0)

## The app (details: `tools\motionlab\app\CLAUDE.md`)
`MotionLab.bat` = a local server + an Edge app window. Sidebar since 0.4 = the user's ways in: Home ("What do
you want to do?"), **Analyser** (#/analyze, shown as Analyze until 0.4.3.5: download / pick videos, analyse, the review page with verdicts and possible
misses, Delete), **Prepare** (#/prepare: the script before filming - *Improve my
script* / *Write one from zero* -> `/write-script`, *Title & thumbnail first* -> `/write-title request`; scripts and
titles live in the prompt library), **Editor** (#/edit, called Edit until 2026-10-15: the user's clips - a new edit from analysed videos or a prompt, renders, graphics +
their settings, Resolve check-up, library picks; a video opens on its newest render, then *Review it and improve it*
/ *Start over* and **Ready to post** (0.4.3, under the render since the 2026-10-15 overhaul: title, thumbnails A / B / C,
description, chapters, hashtags - `/write-title package` or by hand), its Review tab = "How did it turn out?" beside
the render -> `build\outcome.json` (+ `"packaging"`: CTR per thumbnail variant + the link, typed in after posting;
older notes on moments stay in `"moments"`); *Rename* = the name the app shows, `build\project.json` "label" - the
folder keeps its name, so commands use the folder name), **Generator**
(#/generate, shown as Generate until 0.4.3.5: a motion-graphics video or a plan + prompts for AI video tools - `/generate-video`; the prompt library
#/prompts), **Claude's memory**
(#/memory: one search over what Claude learned - videos and their style, effects and how they were made, lessons,
saved graphics + effects, Share with friends), then Jobs and Settings
(General, Storage, Claude skills). The 0.3 addresses (#/refs, #/projects, #/knowledge, #/library) still work. The app
runs the lab's own tools as jobs; Claude's parts run in Claude Code windows the app opens with a fixed first message, a
model (Opus by default, Fable for the long tasks when the user picks it) and an effort level per task - a dialog on
every button, or fixed in Settings > Claude Code.

## Working style (Fable and Opus)
- You get the outcome and the constraints, not the steps. The skills describe what a good result is; decide the
  order and the tools yourself. When you have enough information to act, act: don't re-derive what the lab already
  measured or re-open a decision the user made.
- Before reporting progress, check each claim against a tool result from this chat. If the self-test fails, say so
  with its output; if a step was skipped, say that.
- Do the task, not the tidying: no refactors, helpers or extra checks beyond what the task needs.
- Verify your own work; nobody asks you to and you don't need a subagent for it. Delegate only when several
  independent, sizeable pieces can run in parallel (many sheets, many clips), never to split one small job.
- A question or a description of a problem gets an assessment, not a fix.

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
- A reference: download > lab pass (`analyze.py`, with the user's focus) > Claude checks (`/analyze-reference`: read
  EVERY contact sheet, write `review.json` incl. the `_breakdown` for the focus, `report.py`; auto-detected types are
  drafts until reviewed) = ready for edits; then, optional ("Teach Claude" in the app): the user's verdicts > feedback
  to Claude > Share (Claude's memory). The app's Add videos queues up to 10 videos (links download first).
- When the user pastes text starting with `MOTIONLAB FEEDBACK` (or says they gave feedback in the app: newest
  `analysis\<name>\feedback\app_*.txt`), follow "Applying feedback" in the skill: new lessons go to
  `knowledge\local\lessons.md` (id from `tools\knowledge.py next-lesson-id`), threshold changes in `config.json`,
  re-check the WRONG/PARTLY events and the possible misses marked EFFECT, run the self-test, and report exactly what
  changed. Also import pasted feedback into verdicts.json (`feedback.parse` + `motionlab.app.data.save_verdicts`).
  Afterwards remind the user of Claude's memory > Share my knowledge.
- Reviewing incoming lessons (`knowledge\incoming\*.md`): skill section "Reviewing incoming lessons"; each becomes a
  shared `L###` rule in `lessons.md` or is dropped with a reason; delete the reviewed incoming file.
- Measured help for reviews (evidence only, never changes events): every flash gets a "flash look" line
  (`flash.look_*`), and each analysis lists "possible misses" (`near_miss`). Record a verdict per possible miss in
  review.json `"_near_misses"` (lessons L001, L006); the user answers them in the app (verdicts.json `misses`).
- Report and app layout follow the user's notes (2026-10-06/07): per effect the preview, "What happens" and
  "Measured evidence" are open; timing / origin / rebuild ("In depth") and the contact sheets ("Frame list") are
  folded; false alarms are folded (verdict optional); possible misses are red until answered.
- Editing the user's footage like a reference: the `/recreate-video` skill - 1:1 (option 1 = lab render, option 2 =
  the same edit as a DaVinci Resolve Studio project) or, since 0.4, by feel (the style of up to 3 videos or the
  user's words; `style.py` + the quick draft `draft_edit.py`, then Claude refines). The app's *New edit* saves the
  request in `build\edit_request.json` (`/recreate-video request <project>`).
- Saving library effects: start from `projects\<name>\build\library_picks.json` and `[save to library]` notes; add a
  builder + `META` entry + test `CASES` in `tools\library.py`, then `library.py build` and `library.py test` (every
  macro must render in Resolve; `docs\resolve_notes.md`).
- Any change to `config.json` or `tools\motionlab\` must be followed by `selftest.py --extended` (all PASS).
- Publishing a new version (the repo owner = the user, with Claude's help): self-test `--extended` all PASS, raise
  `__version__` in `tools\motionlab\__init__.py`, add a `## x.y.z - date - title` section to `CHANGELOG.md` (the
  update banner shows it; it takes in the `## Unreleased` lines - the app shows only version sections), raise `API_LEVEL` in `server.py` + `app.js` if the page needs new routes; the user commits
  and pushes (the roadmap's "here" too: `roadmap.py sync`). GitHub's full tests (self-test + `tools\dev\smoke.py`,
  ~15 min) run only for a new `x.y.0` or by hand (Actions > Run workflow); any other new version (0.4.2.1, 0.4.3...)
  gets a ~1 min release check (every file compiles, its CHANGELOG section, the roadmap's "here") - the user's choice
  2026-10-15, so the local `--extended` + smoke before a release are the real gate. A green run moves the `tested`
  branch, which is what the Update button installs, and tags `v<version>` (docs\organization.md "Tests on GitHub").

## Environment gotchas (learned while building the lab)
- ffmpeg's `drawtext` filter segfaults on this Gyan build (no fontconfig file): draw labels with Pillow.
- ffmpeg's `loop` filter starts repeating one frame BEFORE `start`; `xfade`'s first transition frame is still
  100% of the outgoing clip. The test generator measures its ground truth from the rendered pixels for this reason.
- In the Bash tool, heredocs can swallow backslashes: write patch scripts with the Write tool, then run them.
- Pass paths to ffmpeg / Python as argument lists (no shell quoting); Windows paths with spaces are common.
