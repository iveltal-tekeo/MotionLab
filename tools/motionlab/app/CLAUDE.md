# The MotionLab app (tools\app.py + tools\motionlab\app\)

Loaded by Claude Code only when you work in this folder (the root CLAUDE.md stays short).

- Files: `server.py` (routes, security, update/restart), `data.py` (everything the pages show, verdicts, the workflow
  state of a reference), `jobs.py` (the fixed list of jobs), `system.py` (settings, program detection, downloads, the
  Claude launcher, shortcuts), `trash.py` (Delete = Recycle Bin), `updater.py` (git), `ui\` (plain HTML/CSS/JS, no
  build step).
- Python standard library only (nothing installed): a server on 127.0.0.1:8765 + Microsoft Edge in app mode (its
  own window, 1600x1000). It stops ~10 s after the window closes (3 min without heartbeat), unless a job runs.
  Security: Host header check, a session token on every POST, `/files/` serves read-only from analysis, projects,
  refs, docs, library, knowledge only. Writes only: verdicts / feedback exports, library picks, `.app\`,
  `settings.json`, downloads into `refs\` (+ `refs\audio\`), `analysis\<name>\meta.json` (category / tags),
  `knowledge\` (cards, summary, packs, imports; the prompt library `local\prompts\`: Add / rate), a graphic's settings
  (`projects\<p>\build\overlays\<o>\overlay.json` "values", validated against its index.html), since 0.3.3 an empty
  `projects\<name>\` (*Create video*), `projects\<p>\build\made_from.json` + `outcome.json`, and - on a click - a Desktop / Start-menu shortcut, git pull
  (Update) / commit + push of `knowledge\` only (Share), and Delete (below; a prompt card's Delete = POST
  `/api/prompts/delete`, the one file to the Recycle Bin, logged).
- Delete (v0.2.5, `trash.py`): the user's Delete buttons on References (a reference = its analysis folder + its video
  when that lies in `refs\`; a download nobody analysed), Videos (a whole `projects\<name>\`) and Renders (one render
  / side-by-side in `build\`). GET `/api/delete?kind=&name=` = the plan the dialog shows (every item, size, warnings:
  a video used by a project's plan or Resolve build starts unticked; Resolve running; Resolve projects that use the
  clips); POST `/api/delete` re-plans and moves the ticked items to the Windows Recycle Bin (`SHFileOperationW`,
  FOF_ALLOWUNDO; Windows asks before deleting for good when something does not fit). Refused while a job runs; only
  paths inside refs / analysis / projects (links resolved); knowledge cards and lessons always stay; each delete is
  logged in `.app\deleted.log`. Claude never calls these routes (hard rule 1).
- Sidebar (the user's order, 0.3.3): Home, Videos | Media: References, Prompts | Additional: Library, Knowledge |
  Tools: Jobs, Settings (Storage = Settings' second tab, `setTabs`; #/storage still works). Each page sets
  `body[data-page]` -> its accent colour (`--acc`, app.css "0.3.3: a livelier look": CSS only, no images / scripts,
  motion off with prefers-reduced-motion). Videos: **Create video** (`createVideoModal`: Use a reference | Use a
  prompt -> your clips (a project, or *+ a new video* = POST `/api/projects/new`, an empty folder) -> POST
  `/api/project/<p>/made_from` + Claude `/recreate-video <ref> <p>` or `/recreate-video prompt:<id> <p>`); a video's
  Overview starts with **How did it turn out?** (sound, SFX, colour, captions, motion graphics, effects, pacing,
  overall: Good / OK / Bad + a note -> POST `/api/project/<p>/outcome`; *Improve it with Claude* =
  `/recreate-video improve <p>`); GET `/api/prompts` carries `used` (prompt -> videos + their ratings: "Used in").
  Prompts: what each is for (its tags; *For: Edit* = POST
  `/api/prompts/tags`), *Use it, change…* = `/write-prompt <kind> like <id> - change: ...`, Delete.
  0.3.4 (the user: "make it more user friendly"): kind `brief` (Brief for Claude: how to make / edit a whole video)
  first; the card = kind badge (click = `kindModal`, POST `/api/prompts/kind`) + title, the text folded (Show all),
  **Claude's check** folded with counts (✓ clear / ~ vague / ✗ missing): a row per part in plain words
  (`SLOT_LABEL`) - what the prompt says, Claude's tip, *what you want* (POST `/api/prompts/wishes` on change) -
  then *Optimize with Claude* = `/write-prompt optimize <id>` (a new prompt, `made_from`; the card shows
  "Optimized: ..."), *Check it again* = `/write-prompt analyse <id>`; *Run it* (brief / script / hook = Create video
  with it picked; shot / image = copy for the site). *Add prompts* = 1) I have a prompt (the paste / file form;
  Claude checks it after Save) 2) Generate a new prompt from zero (kind, what you want, for, model ->
  `/write-prompt <kind> - want: ...`). API_LEVEL 10.
  After 0.3.4 (the user: "the optimized prompt asks for a link to a Clavero vlog - what if I analysed one?"): brief /
  script / hook cards have **Style like** (`styleBlock`): linked references (`style_refs`, POST `/api/prompts/style`)
  with their measured line (`knowledge.style()`: format, cuts/min, typical shot, first 3 s, effects/min per family,
  BPM, words; cached per file change), "Found in your references: ... *Use its style*" (`prompts.suggest_refs`: who
  made it named in the prompt, else a distinctive title word; GET `/api/prompts` carries `styles` + `suggest`), *+ pick
  from your references* (`styleModal`); Generate from zero has *In the style of* (`- style: <name>`); Create video's
  prompt list shows it. API_LEVEL 11.
  Then (the user, still 0.3.4: "too crowded - remove the filters; a click on a prompt = a pop-up; Add prompts should
  go forward, with back"): no kind / purpose chips (search only), one `.prow` per prompt, newest first; a click =
  `promptModal` (`.mbox.wide`: text, Style like `pstyleBlock`, the check `pcheckBlock` - a brief's rows grouped by
  `BRIEF_GROUPS`: the plan / the edit / sound / look & text / finish - wishes, Optimize, Run it, rating);
  `#/prompts/<id>` opens one. `modalBack(fn)` after `modal()` = a *← Back* button, and Esc / ✕ / a click outside go
  back too (`dismissModal`; a plain `closeModal()` does not): the dialogs opened from the pop-up, and Add prompts'
  second screen (1 / 2 = its own screen). Brief parts + effects, voice & audio, ending (`prompts.SLOTS`).
  Then ("3 per row, just the title, the rating, if I need Higgsfield / clips, the category - the tags are noise"):
  `.pgrid` of `.pgc` cards = kind badge + one category (`pcategory`: the first purpose tag), the title (`title` or
  `title_auto` = `prompts.auto_title`, also saved on paste), what it needs (`pneeds`: tool / model + your clips /
  photo / you on camera / text only), the rating (the user's, else Claude's ★); *What it makes* in the pop-up =
  pictures / clips of the result (POST `/api/prompts/example` add (base64) / remove (Recycle Bin);
  `knowledge\local\prompts\examples\`, record `examples`), the first one = the card's picture. API_LEVEL 12.
  Home (same day): no Next steps, no "Updated to" box (kept only when an update set aside local changes), Setup
  warnings only when a program is missing, Status below the roadmap.
  Then ("let's start becoming a real app"): Home has no subtitle and a **Where to start** panel = the six `FLOW`
  steps as buttons (`flowHow` + `wireFlowHow`: download / measure open their dialogs, the rest go to References /
  Knowledge) - References no longer shows them; empty References / Videos / Prompts = `emptyHero` (icon, title,
  one line, the page's add button in the middle; the header buttons hide); `recreateModal` is gone - *Recreate with
  my footage* = `createVideoModal({from: 'reference', pick})`; prompt filters `PFILTERS` (All / Needs another tool
  = `ptool(p)`: a known paid / separate tool in the model or text, every shot / image / No other tool / Not checked
  yet + *Check these with Claude*), `ptoolChip` (amber). User-facing words: no paths, versions, SHA-256, effort
  levels; "lab pass" = Measure. Tested with a second test server on an empty copy of the app code (no user data).
- Pages (routes keep their old names #/refs, #/projects): Home (update banner, counts, setup warnings when a program
  is missing, Where to start = the 6 steps, roadmap, then status), **References** (#/refs: downloads not analysed
  yet, cards with the next step's button + Delete, filters by category / tag; then the analysis page), **Videos**
  (#/projects: the user's own footage - versions, renders, **Graphics** (0.3.2: the video's HTML graphics in
  `build\overlays\`, thumbnail, render state, a form per declared setting -> Save = POST `/api/project/<p>/overlay`,
  Render / Save to library = jobs; *Captions from a subtitle file* + *Subtitles for Resolve (.srt)*; *Clip for
  Resolve (.mov)* = a numbered copy, revealed; *Swap in DaVinci Resolve* = `overlay.py refresh`), timing check, Resolve check-up / what changed by hand / library picks, Delete), **Prompts** (#/prompts, 0.4; one list of every kind since 0.3.3, a row per prompt, a click opens it - see above; cards with source, model,
  structure slots, Good / OK / Bad + a note, Copy, *Write one like this* and *Add prompts* = any text or attached
  files since 0.3.3 (`addPromptsModal`: the kind guessed - POST `/api/prompts/guess`, editable; .txt / .md / .docx
  read by POST `/api/prompts/file` (base64, up to 30 MB, kept in `knowledge\local\prompts\files\`), a PDF goes to
  Claude; *Let Claude sort it* = `/write-prompt import <files>`; after Save Claude reviews + splits unless unticked);
  `motionlab.prompts`, GET `/api/prompts`, POST `/api/prompts/import` + `/rate`), **Knowledge**, **Library** (Graphics
  first: yours in `library\graphics\` + the examples, *Use in a video* = job `overlay_new`; then the effect macros), Jobs, Storage, **Settings** (programs, yt-dlp, Claude Code path +
  effort, default category, shortcuts, Sharing & updates).
- The analysis page's **Content** tab (0.3.5, `contentTab`, `data.content_info`): how the video performs
  (`content\stats.json`: views, views ÷ followers, views a day, likes, comments, followers; job `content_stats`) and
  what it says (`content\transcript.json` lines with frame + timecode - a click moves the player, the line being
  said is marked, search; job `content_transcript`). Both jobs = `tools\content.py` (group net), nothing downloaded.
- The analysis page (#/ref/<name>, `?e=E004` selects an effect, `?misses` opens the misses tab), the user's
  2026-10-07 layout: header + workflow strip (`data.flow`: download > lab pass > Claude checks > your verdicts >
  feedback > share, with the next step's button); the full-width frame-accurate player + two timelines (red dashed
  line + ▲ = possible miss); tabs **Review effects** (list | effect card: looping preview with frame + timecode
  burned in, what happens, evidence, In depth / Frame list folded; a bottom bar with Correct / Partly / Wrong (keys
  1 2 3), note, Previous / Next / Next without a verdict (J K N); "Correct" moves on by itself, Partly / Wrong focus
  the note, Ctrl+Enter moves on; an end card after the last effect) and **Possible misses** (red until answered:
  "It's an effect" + what / "Not an effect"; stored in verdicts.json `misses` by frame and exported as a
  `--- possible misses ---` section that `tools\feedback.py` parses). False alarms stay hidden unless asked for.
- "Claude" buttons start Claude Code in a new console in the lab folder (`.app\open_claude.cmd`; characters cmd would
  interpret are stripped, double quotes become single ones) with a fixed first message, a task (`system.TASKS`:
  review / feedback / lessons / library / recreate / prompt / plan / free) that picks `--effort` (Settings > Claude Code >
  Effort: "recommended" = review high, feedback high, lessons high, library high, recreate xhigh, prompt medium, plan (Home > Roadmap > What next? = /whats-next) high; or
  one level for all) and
  `--name "MotionLab <task> <video>"` (shown by /resume) - both only when `claude --help` lists them (older
  versions). "Analyse with Claude" = an analyze job with `claude: true`: when the lab pass ends well the job opens
  Claude with `/analyze-reference "<video>" - the lab pass is done: analysis\<name>` (`data.review_prompt`; the skill
  then skips the pipeline). "Lab pass only" = the job alone.
- Downloads = `tools\download.py` around yt-dlp (`system.PRESETS`: MP4 <=1080p / best / MP3; one video, no
  playlists; the final path is printed last so the dialog offers "Analyse it"). Since 0.3.3: `-S res:1080` = the
  short side (vertical videos in full size), video presets never take sound only (`VIDEO_F`), `--encoding utf-8`
  (emoji in titles), the file found by `[<id>]` if the printed path is off, `download.HINTS` = yt-dlp's errors in
  words. Tested 2026-10-12 on TikTok, YouTube, SoundCloud (refused: no video), Vimeo / Instagram (login wanted).
- Jobs = only the lab's own tools + yt-dlp downloads, a fixed list in `jobs.py` (analyze, report, Resolve doctor /
  diff, storage + prune, self-test, verify_timing, download, resolve_mcp_install / _remove = Settings > Claude Code >
  DaVinci Resolve, overlays_install / overlays_upgrade_test = Settings > Programs, overlay_render / overlay_save /
  overlay_new / overlay_captions (a subtitle file, or a video's words = speech to text) / overlay_refresh (group
  resolve) / overlay_resolve_clip = Graphics; speech_install = Settings > Programs > Speech to text; captions read the user's .srt / .vtt / transcript.json, never change
  it), one per group (cpu / resolve / light / net). Claude's
  parts stay in Claude Code: reviewing sheets, applying feedback, reviewing incoming lessons, building in Resolve,
  saving library macros.
- Updates (`updater.py`, git only - no GitHub API, no tokens in the lab): `check` = `git fetch` + behind / ahead /
  local changes + the new version (read from `origin:tools/motionlab/__init__.py`) + `kind` ("version" = newer
  MotionLab, "knowledge" = only friends' cards / lessons, "changes") + every CHANGELOG section newer than this copy
  (`updater.whats_new`: `## x.y.z - date - title` headings). Since 0.3.1 updates come from `origin/tested` when the
  repo has it (`updater._upstream`; GitHub's tests move it to each passing push to main, docs\organization.md "Tests
  on GitHub"): `behind` / the new version / What's new are read from there, `ahead` and Share stay on
  `origin/<branch>`, `testing` = pushes on main not tested yet (the page says "waiting for GitHub's tests"). Tested
  2026-10-09 against a fake GitHub with the workflow's own bash steps. `apply` = `git pull --rebase --autostash`, `pip install
  -r requirements.txt` if it changed, then the server restarts itself when code changed (`restart_soon`: a new
  `app.py --wait-port`, the window shows "Updating..." and reloads; knowledge-only updates need no restart).
  Settings `update_mode` (0.3.0; 0.2.x had update_check / update_auto, migrated to "ask"): "ask" (default) = the
  sidebar's bright **Update available** button (calmer "New from friends" for knowledge) -> a dialog with the new
  CHANGELOG sections -> Update now; bottom left, always there (any mode): **Check for updates** (`#side-check`,
  `checkUpdates`) = POST `/api/update/check` now -> the same dialog, or "up to date · 14:05 · N in tests" / "can't
  check" (reason in its tooltip; ping carries `update_checked / _testing / _error`); amber "Update available" once found; "auto" = installs at start-up (3 s in, only within 180 s and with no job);
  "off". Checks at start-up and hourly. After an update `.app\update_last.json` (`from_version`, `whats_new`,
  `seen`) makes the window show "What's new" once (POST `/api/update/seen`; records written by 0.2.x are completed
  from git). The sidebar's What's new button (`newsModal`) shows CHANGELOG.md (`/api/text`) as a timeline. Tested 2026-10-09 against a fake GitHub incl. a real 0.2.5 copy updating itself to 0.3. A local change that clashes with an update (e.g. a threshold tuned in
  `config.json` that the update changes too) is set aside: the file gets the new version, the change stays in git's
  stash ("autostash"), and the restarted app says so (`.app\update_last.json`) - bring it back with
  `git stash show -p` if it is still wanted. `share` commits only the knowledge paths and refuses while the copy
  has commits that are not on GitHub (a push would publish them); a rejected push pulls (rebase) and pushes again;
  on failure our commit and new files are undone and the pack remains. If sharing pulled new code the server
  restarts too.
- Versions: `server.VERSION` = `__version__`; the page carries `<meta name="ml-version">` and `API_LEVEL` (app.js)
  and the ping returns version / api / phase / update: a newer page on an older server shows "Restart now", a new
  server version reloads the page. Raise `API_LEVEL` in BOTH `server.py` and `app.js` when the page needs new
  server routes (3 since v0.2.5: delete, waiting downloads, Claude tasks; 4 since v0.3.0: update seen; 5 since 0.4: prompts;
  6 since 0.3.2: graphics; 7: the Content tab's jobs; 8 since 0.3.3: the prompt dialog's guess / file routes; 11: Style like; 12: prompt examples). `/files/` also serves `tools\overlays\examples\*\*.png` (the examples' thumbnails), nothing
  else under tools.
- The user's verdicts have ONE home: `analysis\<name>\feedback\verdicts.json` (`events`, `cuts`, `misses`, `missed`;
  report.html starts from it and keeps local changes in the browser under the video name).
- Testing after a change: start `app.py --no-window --stay --no-update --port 879x` (NOT 8765: the user's own app
  may run there and a different version would be replaced; `--no-update`: without it the test server checks GitHub
  at start like the real app and, with automatic updates on, could pull an update into a working copy with unsaved
  changes), check every page with headless Edge (`msedge --headless=new`, own
  `--user-data-dir`; clicks via the DevTools protocol - a tiny stdlib websocket client is enough), stop that server.
  Liveness checks must not use `/api/ping` (it is the heartbeat and keeps the server alive). Never click a verdict on
  the user's real references (that writes their verdicts.json) and never a Claude button (it starts Claude): use a
  copy of a self-test analysis (`analysis\synthetic_zz_*`, no knowledge card is made for synthetic_ names) and zz
  test files for delete tests. Updates / sharing are tested against a local bare repo as a fake GitHub with two
  clones as friends (never the real remote; helpers in `tools\dev\`: `cdp.py` drives headless Edge, `upd_prepare.py`
  (setup / push a test version) + `upd_test.py` the update paths; scratch in `.app\dev\`). Close every headless Edge
  you start (a forgotten one on an old test port reconnects to the next test server there). Then
  `selftest.py --extended` and `tools\dev\smoke.py` (read-only: every module, every GET route, every page in headless
  Edge, the MCP server - GitHub's tests run it on every push too).
