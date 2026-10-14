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
- Sidebar (0.4, the user: "only 3 main sections: analyze, edit, generate"; Prepare added after 0.4.1 at the user's ask):
  Home, *Make a video*: **Analyze** (#/analyze = 0.3's References, `pageRefs`; #/ref/<name> = one analysis),
  **Prepare** (#/prepare, `pagePrepare`, green; below), **Edit** (#/edit = Videos, `pageProjects`;
  #/project/<p>), **Generate** (#/generate, `pageGenerate`; the prompt library #/prompts belongs to it) - no
  numbers (the user, 2026-10-14: they are not steps in an order), each row in its section's colour (`--rc`) - then
  **Claude's memory** (below; #/memory/learned = 0.3's Knowledge, `memLearned`;
  #/memory/saved = Library, `memSaved`), at the bottom Jobs and Settings (tabs `setTabs`: General, Storage, Claude
  skills = #/skills, `data.skills()` reads `.claude\skills\*\SKILL.md`; the plain words + how to type it =
  `SKILL_INFO`; /whats-next is marked "for developers"). `ALIASES` rewrites the 0.3 addresses (#/refs, #/projects,
  #/knowledge, #/library). Home = the hero animation, **What do you want to do?** (`WAYS`: three cards with their
  buttons and counts - `status()` carries `prompts` and `lessons`), the Claude's memory line, setup warnings, roadmap
  (`roadmap_live` = `docs\roadmap\index.html` in an iframe - a motion graphic that fetches `roadmap.json` and plays
  live, paused off screen, still with reduced motion; no clicks inside on Home, `.rmhit` = `roadmapBig()` full size;
  the PNG lightbox only when the page is missing), status; *Prompts for AI tools* = `aiPromptsModal` (Generate a new prompt, a shot picked). Each page sets
  `body[data-page]` (analyze / edit / generate / memory / jobs / settings) -> its accent colour (`--acc`: cyan / amber
  / fuchsia (`--gen`, the user's pick 2026-10-14; pink before) / violet / blue; Prepare green; CSS only, motion off
  with prefers-reduced-motion); since 0.4.1.1 (the user's pick "Bold
  band", the end of app.css) the five sections' top pages (`.head:not(:has(.crumb))`) put the title on a band like
  Home's card - an icon tile (`--sf-icon`), no number - over a faint texture of their own (`--sf-tex`,
  `main::before`), panel edges / hover glows / `.btn.pri` in `--acc`; sub-pages keep the bar + texture only; no
  markup. Edit: **New edit** (0.4, `createVideoModal`,
  four steps in one dialog: 1 your clips (a project, or *+ a new video* = POST `/api/projects/new`; its songs =
  `list_projects` `songs`), 2 how (`NE_HOW`: *Like videos you analysed* = up to `max_refs` 3 from Claude's memory -
  this PC's analyses and friends' cards - then *In its / their style* or *An exact copy* (one local analysis) |
  *With your words* = the presets of `style.PRESETS` (GET `/api/edit/options`) + a text | *From a saved prompt*),
  3 length / format / sound (style and words only), 4 *Quick draft now* (job `draft` = `draft_edit.py <p> ...
  --render`; the video's page follows it with `progressPanel(el, onEnd, ['draft'], match)`) or *Make it with Claude*
  (+ "then a DaVinci Resolve project") -> POST `/api/project/<p>/edit_request` (`data.save_edit_request`: checked,
  saved as `build\edit_request.json`, appended to `made_from.json` - kinds reference / style / words / prompt; the
  answer's `command` = `/recreate-video <ref> <p>` for a copy, `prompt:<id>`, else `/recreate-video request <p>`, so
  the user's words never pass through cmd). A video's page has *New edit…*; Edit versions say how each was made (a
  quick draft: its style + *notes* = `draft_vN.md`; `_plan_info` `made_by` / `style` / `notes`); a video's
  Overview starts with **How did it turn out?** (sound, SFX, colour, captions, motion graphics, effects, pacing,
  overall: Good / OK / Bad + a note -> POST `/api/project/<p>/outcome`; *Improve it with Claude* =
  `/recreate-video improve <p>`); GET `/api/prompts` carries `used` (prompt -> videos + their ratings: "Used in").
  **Prompts** - the current state (the user's wishes, 0.3.4: "more user friendly", "too crowded", "3 per row, just
  the title, the rating, if I need Higgsfield / clips, the category - the tags are noise", "too ambiguous, hard on
  the eye"; 2026-10-13: "tell the user it reviews and improves"):
  - List: search + `PFILTERS` (All / Needs another tool = `ptool(p)`: a known paid / separate tool in the model or
    text, every shot / image / No other tool / Not checked yet + *Check these with Claude*, one prompt = *Optimize
    with Claude*), newest first; `.pgrid` of `.pgc` cards, 3 per row = kind badge + one category (`pcategory`: the
    first purpose tag), the title (`title` or `title_auto` = `prompts.auto_title`, also saved on paste), what it
    needs (`pneeds`: tool / model + your clips / photo / you on camera / text only; `ptoolChip` amber), the rating
    (the user's, else Claude's ★), the first example as its picture. Kind `brief` (Brief for Claude: how to make /
    edit a whole video) comes first; brief parts in `prompts.SLOTS`.
  - A click (or `#/prompts/<id>`) = `promptModal`: `.pm2` header in the kind's colour (`--kc`: kind badge =
    `kindModal` / POST `/api/prompts/kind`, title, needs, *Run it* (`RUN`: brief / script = Create video with it
    picked, a hook = *Use current version in a video*; shot / image = copy for the site), *Copy Prompt* (clipboard
    icon)); `PSTEPS` + `pstate()` (check / want / opt / run / rate, the current one lit, a Next box with its
    button); `.pmgrid` two columns: the prompt (`.ptext2`) + **Claude's check** `pcheckBlock` (unchecked: *Optimize
    with Claude* = `/write-prompt optimize <id>`, which checks it first; checked: a `.cpart` card per part coloured
    by status - ✓ clear / ~ vague / ✗ missing, plain words `SLOT_LABEL`, a brief's grouped by `BRIEF_GROUPS`: the
    plan / the edit / sound / look & text / finish - with the tip and *what you want* (POST `/api/prompts/wishes` on
    change), `.seg` Needs work / All parts; *Optimize with Claude* = a new prompt with `made_from`, "optimized by
    Claude"; *Check it again* = `/write-prompt analyse <id>`) | rating (`.rb` Good / OK / Bad, a note saved on
    change, "Used in"), **What it makes** (pictures / clips of the result, explained in the section: *+ Add picture /
    clip* = POST `/api/prompts/example` add (base64) / remove (Recycle Bin); `knowledge\local\prompts\examples\`,
    record `examples`; the first = the card's picture), **Style like** `pstyleBlock` (brief / script / hook: linked
    references `style_refs`, POST `/api/prompts/style`, each with its measured line `knowledge.style()` - format,
    cuts/min, typical shot, first 3 s, effects/min per family, BPM, words, cached per file change; "Found in your
    references: ... *Use its style*" = `prompts.suggest_refs`: who made it named in the prompt, else a distinctive
    title word; GET `/api/prompts` carries `styles` + `suggest`; *+ pick from your references* = `styleModal`),
    Details (source, model, *For: Edit* = POST `/api/prompts/tags`, better versions, *Use it, change…* =
    `/write-prompt <kind> like <id> - change: ...`, Delete). `modalBack(fn)` after `modal()` = a *← Back* button;
    Esc / ✕ / a click outside go back too (`dismissModal`; a plain `closeModal()` does not) - the dialogs opened
    from the pop-up and Add prompts' second screen use it.
  - *Add prompts*, two screens: 1) I have a prompt (paste / file form; Claude checks it after Save) 2) Generate a new
    prompt from zero (kind, what you want, for, model, *In the style of* -> `/write-prompt <kind> - want: ... -
    style: <name>`). Create video's prompt list shows each prompt's style.
  **Home**: `heroAnim()` first (a CSS-only motion graphic: 24 s loop of 4 scenes, transform + opacity only - measured
  1 layout and 10 ms main-thread work in 6 s; reduced motion = a still scene) with *Paste a link* (`downloadModal`);
  no subtitle; **Where to start** = the six `FLOW` steps as buttons (`flowHow` + `wireFlowHow`: download / measure
  open their dialogs, the rest go to References / Knowledge); setup warnings only when a program is missing; no "Updated
  to" box (only when an update set aside local changes); Status below the roadmap. Empty References / Videos / Prompts
  = `emptyHero` (icon, title, one line, the page's add button in the middle; the header buttons hide). Analyze and
  Edit (the user, 2026-10-14) put their actions in a first row under the title, on the left (`.toprow`: *Download from
  link* + *Add videos*; *New edit* + *Folder*), not in the header's corner. **Optional steps** (the user,
  2026-10-14: numbered like the required ones they look obligatory): a grey dashed number + a bold OPTIONAL tag
  (`optTag(hint)`; `.nestep.opt` in the dialogs, `.fstep.opt` = a video's *Teach Claude* steps, `PSTEP_OPT` = a
  prompt's *You say what you want* / *Rate the result*); required steps keep the solid number in the section colour.
  A new step that can be skipped (or has a default) gets the same. *Recreate with
  my footage* = `createVideoModal({from: 'reference', pick})`. User-facing words: no paths, versions, SHA-256, effort
  levels; "lab pass" = Measure. UI changes are tested with a second test server on an empty copy of the app code.
- **Analyze** (0.4, the user: "pass videos downloaded or pasted as a link, analysed in a concrete way I select:
  content creation / cinematic / both"): *Add videos* = `addVideosModal` (links one per line + files from refs\ or a
  path, up to `AV_MAX` 10; the focus `FOCUS_OPTS`; kind of video; "Claude checks each video when it is measured" =
  claude:true per analyze job, or Measure only) -> POST `/api/analyze/batch` (`server.analyze_batch`: everything is
  checked before anything starts; files -> queued analyze jobs, links -> queued download jobs whose `then` starts
  the analysis of the saved file; `system` remembers `default_focus`). The page's in-progress panel
  (`progressPanel`, every 2 s while jobs are active: running first, then waiting, *Remove* = cancel a queued one,
  finished ones for 15 min) redraws the cards when one ends. Cards: focus chip, the profile's lines (`focusLines`),
  the flow; filters focus / category / tag. One analysis (#/ref/<name>, `?verdicts` = the Effects tab): tabs right
  under the step strip - **Overview** (default; `overviewTab`: Rhythm, Content creation and / or Cinematic panels for
  the focus from `profile.py`, Claude's breakdown (events.json `breakdown` = review.json `_breakdown`), Use it: Edit
  my clips like this / Prompts for AI tools like this / Analyse again with another focus; the player is hidden),
  then **Colour & look** for the cinematic / both focus (`colourPanel`, `data.colour_info` from
  `colour\colour.json`: the look's words, the five main colours, every shot's main colour as a strip with frame +
  timecode tooltips, brightness / colour / frame in words; not measured yet = *Measure the colour* = job `colour`
  (`tools\colour.py <name>`, group light, no decoding)), Effects, Possible misses, What it says (the Content tab). The step strip: Download > Measure > Claude checks |
  *Teach Claude (optional)*: Your verdicts > Feedback > Share; a video with no effects (a talking head) shows "No
  effects" instead of crashing. Timelines fix their canvas height at creation (no ResizeObserver loop when shown).
- **Generate** (0.4, the user: "a video from zero - mostly external tools like Higgsfield, InVideo... or a whole
  motion-graphics video with HyperFrames"): `pageGenerate` = two ways - *A motion-graphics video* (disabled with a
  pointer to Settings > Programs until Node.js + HyperFrames are found) and *With AI video tools* (*Plan a video with
  Claude*; *Just one prompt* = `aiPromptsModal`), the videos made from zero (projects without clips), the latest
  prompts. Both open `generateModal(kind)`: what it is about, the words on screen (graphics) or the tool (ai), up to
  3 analysed videos as style chips, length, format, a song (graphics: `refs\audio\` downloads), colours, its name ->
  POST `/api/generate/request` (`data.save_generate_request`: checked; makes `projects\<name>\` when new; saves
  `build\generate_request.json`; made_from kind `generated`) -> Claude `/generate-video request <name>` (task
  `generate`, effort xhigh). GET `/api/generate/options` = the tools, the downloaded songs, HyperFrames found.
- **Prepare** (the user, 2026-10-14: "prepare a video (transcript oriented): improve a script you have - rewrite it
  with more potential to go viral - or generate one from zero from a few questions; hooks, structure"):
  `pagePrepare` = two ways (*Improve my script* = `scriptImproveModal`, *Write one from zero* = `scriptNewModal`),
  *How Claude writes for reach* (`SP_RULES`: the six rules of `.claude\skills\write-script\guidelines.md`),
  *Waiting for Claude* (requests with nothing written from them yet: *Open in Claude Code again*, ✕ = POST
  `/api/script/forget`, the request file to the Recycle Bin, logged), *Your scripts and hooks* (prompt cards ->
  `promptModal`). Scripts live in the prompt library (kind script / hook); the requests in
  `knowledge\local\prompts\requests\req-NNN.json` (`motionlab\script.py`). Improve: paste / attach (.txt .md .docx via
  `/api/prompts/file`), where it goes, length, a wish, up to 3 analysed videos -> POST `/api/script/improve` (the
  script saved as the user's own + an `improve` request) -> Claude `/write-script improve <id>` (task `script`, effort
  high). From zero: topic (required), viewer, takeaway, angle, must-say points, where, length, tone, the ask at the
  end, language, style, anything else -> POST `/api/script/request` -> `/write-script request <req>`; Claude saves
  the script with `"request": "<req>"`. **The script check** (`script.check`, POST `/api/script/check`, no Claude):
  live in the Improve dialog (`scriptCheckHtml`, debounced) and on every script / hook pop-up (*The check*); the
  speaking rate is measured on the picked videos (`style.build(...)["talk"]`) when they have talking. A script / hook
  card's *Optimize* / *Check it again* go to `/write-script` (`optCmd`, `chkCmd`), other prompts to `/write-prompt`.
- **Claude's memory** (0.4, the user: "once analysed it is stored in the mind of Claude, so editing or generating can
  use those effects and that knowledge"): `pageMemory(main, tab)`, tabs `MEM_TABS` = Overview (one search `#mq` over
  videos / effects / lessons, counts that link to their tab, *How Claude uses it* + *What Claude reads (memory.md)* /
  *Rebuild it* = POST `/api/knowledge/summary`, effects seen most, the latest videos), Videos (`memVideoCard`: focus,
  kind, rhythm, the profile's lines, Claude's breakdown summary, *Open* / *Edit like this*; filters focus / kind /
  yours-friends'), Effects (`memEffectRow`: per type how often, in how many videos, a bar of the user's verdicts, the
  best examples - correct first - with what happens and how it was made, f<frame> links to the effect), Lessons
  (this PC's, shared, incoming + *Review them in Claude Code*), Graphics & saved effects (`memSaved`), Share with
  friends (`memLearned`). GET `/api/memory` = `data.memory()` = `knowledge.memory()` (cached on the cards' and lessons'
  mtimes; friends' cards too) + saved counts + prompts; it rewrites `knowledge\local\memory.md`
  (`knowledge.memory_index()`, also rebuilt with the summary) when a card is newer - the file the skills read.
- Pages (routes keep their old names #/refs, #/projects): Home (the motion graphic, counts, setup warnings when a program
  is missing, the three ways in, roadmap, then status), **Analyze** (#/analyze, above), **Edit**
  (#/projects: the user's own footage - versions, renders, **Graphics** (0.3.2: the video's HTML graphics in
  `build\overlays\`, thumbnail, render state, a form per declared setting -> Save = POST `/api/project/<p>/overlay`,
  Render / Save to library = jobs; *Captions from a subtitle file* + *Subtitles for Resolve (.srt)*; *Clip for
  Resolve (.mov)* = a numbered copy, revealed; *Swap in DaVinci Resolve* = `overlay.py refresh`), timing check, Resolve check-up / what changed by hand / library picks, Delete), **Prompts** (#/prompts, see above; *Add prompts* = `addPromptsModal`: the kind guessed - POST `/api/prompts/guess`,
  editable; .txt / .md / .docx read by POST `/api/prompts/file` (base64, up to 30 MB, kept in
  `knowledge\local\prompts\files\`), a PDF goes to Claude; *Let Claude sort it* = `/write-prompt import <files>`;
  after Save Claude reviews + splits unless unticked; `motionlab.prompts`, GET `/api/prompts`, POST
  `/api/prompts/import` + `/rate`), **Knowledge**, **Library** (Graphics
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
  review / feedback / lessons / library / recreate / prompt / plan / free). First a dialog (`openClaude`, unless
  Settings `claude_ask` is off: then straight away): the model (`system.MODELS`: opus = the default on every plan,
  fable = the strongest for long / open-ended work - the dialog marks it "stronger for this task" for review /
  recreate / generate (`TASKS[..][2]`), auto = Claude Code's own `/model`) and the effort, pre-filled from Settings
  (`claude_model`, `claude_effort` "recommended" = review high, feedback high, lessons high, library high, recreate
  xhigh, generate xhigh, prompt medium, script high, plan (Home > Roadmap > What next? = /whats-next) medium; one
  level less on Fable, `FABLE_EFFORT`; or one level for all); *Don't ask again* saves the choice (POST `/api/claude`
  `remember`; `options: true` = the dialog's data, nothing opens). The launcher adds `--model` / `--effort` only
  when this Claude Code's `--help` lists them, and
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
  it), one per group (cpu / resolve / light / net); since 0.4 a job may wait its turn (`Runner.start(queue=True)`,
  status "queued", `_next` starts it when its group is free, `active()` = running + queued keeps the server up and
  holds back updates / deletes) and a download may carry `then` (analyse the saved video: `_then_analyse`,
  `saved_file` = download.py's last line). Claude's
  parts stay in Claude Code: reviewing sheets, applying feedback, reviewing incoming lessons, building in Resolve,
  saving library macros.
- Updates (`updater.py`, git only - no GitHub API, no tokens in the lab): `check` = `git fetch` + behind / ahead /
  local changes + the new version (read from `origin:tools/motionlab/__init__.py`) + `kind` ("version" = newer
  MotionLab, "knowledge" = only friends' cards / lessons, "changes") + every CHANGELOG section newer than this copy
  (`updater.whats_new`: `## x.y.z - date - title` headings). Since 0.3.1 updates come from `origin/tested` when the
  repo has it (`updater._upstream`; GitHub's tests move it to each passing push to main, docs\organization.md "Tests
  on GitHub"): `behind` / the new version / What's new are read from there, `ahead` and Share stay on
  `origin/<branch>`, `testing` = pushes on main not tested yet (the page says "not released yet": since 0.3.5 the tests run only for x.y.0, by hand or with `[tests]`). Tested
  2026-10-09 against a fake GitHub with the workflow's own bash steps. `apply` = `git pull --rebase --autostash`, `pip install
  -r requirements.txt` if it changed, then the server restarts itself when code changed (`restart_soon`: a new
  `app.py --wait-port`, the window shows "Updating..." and reloads; knowledge-only updates need no restart).
  Settings `update_mode` (0.3.0; 0.2.x had update_check / update_auto, migrated to "ask"): "ask" (default) = the
  sidebar's bright **Update available** button (calmer "New from friends" for knowledge) -> a dialog with the new
  CHANGELOG sections -> Update now; bottom left, always there (any mode): **Check for updates** (`#side-check`,
  `checkUpdates`) = POST `/api/update/check` now -> the same dialog, or "up to date · 14:05 · N not released yet" / "can't
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
  6 since 0.3.2: graphics; 7: the Content tab's jobs; 8 since 0.3.3: the prompt dialog's guess / file routes; 11: Style like; 12: prompt examples; 13: skills; 14 since 0.4: analyze batch, memory, edit options / request, generate options / request; 15: Prepare - script
  check / improve / request / requests / forget; 16 since 0.4.1.1: `/api/claude` `options` = the model dialog's data). `/files/` also serves `tools\overlays\examples\*\*.png` (the examples' thumbnails), nothing
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
