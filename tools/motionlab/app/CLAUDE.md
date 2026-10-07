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
  `knowledge\` (cards, summary, packs, imports), and - on a click - a Desktop / Start-menu shortcut, git pull
  (Update) / commit + push of `knowledge\` only (Share), and Delete (below).
- Delete (v0.2.5, `trash.py`): the user's Delete buttons on References (a reference = its analysis folder + its video
  when that lies in `refs\`; a download nobody analysed), Videos (a whole `projects\<name>\`) and Renders (one render
  / side-by-side in `build\`). GET `/api/delete?kind=&name=` = the plan the dialog shows (every item, size, warnings:
  a video used by a project's plan or Resolve build starts unticked; Resolve running; Resolve projects that use the
  clips); POST `/api/delete` re-plans and moves the ticked items to the Windows Recycle Bin (`SHFileOperationW`,
  FOF_ALLOWUNDO; Windows asks before deleting for good when something does not fit). Refused while a job runs; only
  paths inside refs / analysis / projects (links resolved); knowledge cards and lessons always stay; each delete is
  logged in `.app\deleted.log`. Claude never calls these routes (hard rule 1).
- Pages (routes keep their old names #/refs, #/projects): Home (status, update banner, next steps = each reference's
  next workflow step, setup warnings, roadmap), **References** (#/refs: the 6-step workflow, downloads not analysed
  yet, cards with the next step's button + Delete, filters by category / tag; then the analysis page), **Videos**
  (#/projects: the user's own footage - versions, renders, timing check, Resolve check-up / what changed by hand /
  library picks, Delete), **Knowledge**, Library, Jobs, Storage, **Settings** (programs, yt-dlp, Claude Code path +
  effort, default category, shortcuts, Sharing & updates).
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
  review / feedback / lessons / library / recreate / free) that picks `--effort` (Settings > Claude Code > Effort:
  "recommended" = review high, feedback high, lessons high, library high, recreate xhigh; or one level for all) and
  `--name "MotionLab <task> <video>"` (shown by /resume) - both only when `claude --help` lists them (older
  versions). "Analyse with Claude" = an analyze job with `claude: true`: when the lab pass ends well the job opens
  Claude with `/analyze-reference "<video>" - the lab pass is done: analysis\<name>` (`data.review_prompt`; the skill
  then skips the pipeline). "Lab pass only" = the job alone.
- Downloads = `tools\download.py` around yt-dlp (`system.PRESETS`: MP4 <=1080p / best / MP3; one video, no
  playlists; the final path is printed last so the dialog offers "Analyse it").
- Jobs = only the lab's own tools + yt-dlp downloads, a fixed list in `jobs.py` (analyze, report, Resolve doctor /
  diff, storage + prune, self-test, verify_timing, download), one per group (cpu / resolve / light / net). Claude's
  parts stay in Claude Code: reviewing sheets, applying feedback, reviewing incoming lessons, building in Resolve,
  saving library macros.
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
  server routes (3 since v0.2.5: delete, waiting downloads, Claude tasks).
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
  clones as friends (never the real remote). Then `selftest.py --extended`.
