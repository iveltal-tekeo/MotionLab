# The lab's map - every folder, tool and workflow step in detail

The root `CLAUDE.md` keeps the short version and the rules (it is read on every turn, 0.5.3: back to ~13 KB);
this is the whole text it had, for a task that needs a folder's or a tool's detail. Each tool's own usage is
its docstring (run it without arguments).

## Layout
- `refs\` reference videos the user drops in or downloads (read-only); `refs\audio\` = MP3 downloads;
  `refs\downloads.json` = where each download came from (link, platform, uploader, id, duration)
- `analysis\thumbs\<set>\` = a thumbnail set (0.4.5: `set.json`, `img\`, `sheet_N.png`, Claude's `style.json`, the
  user's `verdicts.json`) - not a video analysis
- `analysis\texts\<set>\` = a set of scripts & prompts (2026-10-18; `textsets.py`): `set.json` (the lab's: #n -> prompt
  id + sha1 + facts + the stamp of Claude's verified check), `patterns.json` (written only by textsets.py from Claude's
  draft), `verdicts.json` (the user's), `claude\` (drafts) - not a video analysis; the texts themselves live in the
  prompt library
- `analysis\notes\<name>\` = a video's notes (2026-10-27, the Analyser's Notes; `tools\notes.py`,
  `motionlab\notes.py`, Claude = `/take-notes`): `note.json` (the video, SHA-256, fps, link, ask, tags, chapters, Most
  replayed, sponsor parts, `done`), `content\` (transcript, stats, info.json, thumbnail), `frames\` (key-frame sheets),
  `notes.json` + `notes.md` (only through `notes.py save`, the quote gate), `mine.md` (the user's own notes) - not a
  video analysis
- `analysis\templates\<pack>\` = a pack of captured motion-graphics clips (0.5.0, e.g. `refs\swishy\`; measured by
  `templates.py read`, Claude's `cards.json`) - not a video analysis; `tools\overlays\motion\<id>\` = the Motion
  Graphics library (MotionLab's own templates rebuilt from them, in the repo)
- `analysis\<video name>\` one per analyzed video: `events.json` (all data), `report.html`, `review.json` (Claude's
  reviews), `review_todo.md`, `events\<ID>\sheet_NN.jpg + preview.mp4`, `frames\`, `cuts\`, `metrics.csv`,
  `overview.png`, `audio.wav`, `proxy_cfr.mp4` (only for VFR sources), `cache\` (re-usable metrics), `inspect\`,
  `meta.json` (category, tags, focus, link, `label` = the user's own name for it - the user's choice, kept across
  re-runs), `content\` (transcript, stats), `colour\colour.json` (0.4: the look per shot + summary,
  `motionlab\colour.py`), `feedback\` (`verdicts.json` = the user's verdicts, their ONE home; `app_<date>.txt` =
  exports from the app; `feedback_<date>.txt/.json` = archived by `feedback.py` when Claude applied them)
- `knowledge\` what installs share: `references\` = SHARED reference cards `<video id>--<author>.json`, `incoming\` =
  SHARED lessons waiting for review; private: `local\` (this PC's cards, `brand.json` = My Brand (0.6.0) + `brand\`
  (its logo, `products\` pictures, `import\` = what Import from your website last found) + `brand_backups\` (Start from
  zero's copies), `calendar.json` = the Content agency's content calendar (0.6.0), `social.json` + `social\thumbs\` = your
  posted videos (Check my pages), `lessons.md` = new lessons `local-N`,
  `lessons_making.md` = lessons on making videos `local-make-N`, `shared.json` = what was shared + what the user keeps
  on this PC (private / include) + imports, `summary.md` + `summary\<category>.md` - Claude reads both before a
  review, `memory.md` = Claude's memory (0.4: every video's style in one line, the effects seen and how they were
  made, since 2026-10-19 the sets of scripts & prompts the user analysed - read before an edit or a prompt;
  `knowledge.py memory` rebuilds + prints it), `prompts\<kind>\<id>.json` =
  the prompt library, ratings included; `prompts\requests\req-NNN.json` = Prepare's script requests), `inbox\` /
  `outbox\` (`*.mlpack.json` packs for friends without push access)
- `projects\<name>\` the user's footage (read-only, top level); everything we make goes to `build\` (each tool's
  docstring names what it writes there; `boards\` = storyboard.py, `stills\` / `sheets\` = render_video.py):
  `sources.json` (IDs A, B, ... + SHA-256), `edit_vN.py` -> `plan_vN.json`
  (the edit) -> `<name>_vN.mp4`, `resolve\` (option 2), `library_picks.json` (the user's picks in the app),
  `edit_request.json` + `edit_brief.md` (what *New edit* asked for: the data + the same in words, step by step,
  for Claude - `motionlab\editreq.py`), `generate_request.json` (0.4: a video from zero) +
  `ai_plan.md` (the shots for AI tools), `made_from.json`, `outcome.json` (the user's review of the newest render:
  per-part ratings + notes, `next`, `moments`, `packaging`), `project.json` (`label` = the name the app shows; the
  folder keeps its name), `draft_vN.md` (the quick draft's notes), `publish\` (0.4.3: the ready-to-post package -
  `publish.py` and `thumbnail.py` write it; `images\` = pictures the user brought, e.g. from an AI image tool)
- `fonts\` the font library (0.4.6, in the repo): one folder per family (.ttf + its licence: SIL OFL 1.1 / Apache 2.0)
  + `fonts.css`; graphics, captions and thumbnails pick from it (`motionlab\fonts.py`), each render gets copies of the
  fonts it uses in its own `assets\fonts\`
- `logos\` the logo library (2026-10-16, in the repo): `<logo>\<variant>.svg` (color / mono / wordmark / -dark) cleaned
  from the user's `refs\logos\` (only read) + `logos.json`; a graphic names one in a logo setting or as `:youtube:` in
  a text (`logos.py`)
- `library\` approved effects only (made by `tools\library.py`): `README.md` + per effect `<effect>.md` recipe,
  `<stem>.setting` Fusion macro(s), `ref_fNNNNN.jpg`, `check.png`; `library\graphics\<name>\` = approved HTML
  graphics with their settings + rendered .mov (`overlay.py save`; `motionlab\overlay_settings.py`)
- `tools\` the pipeline (Python 3.12 venv at `.venv\`, `requirements.txt`; ffmpeg on PATH); `tools\motionlab\` the
  package (`compose.py` compositor - 0.6.1: a graphic `behind` the person, `guard` off the face, `follow` the face /
  the camera, `glass`, `shadow`, `match` the footage; `person.py` the person mask + face track per clip from its light
  cache, `<ID>.person.u8` / `.json` beside the caches, `tools\models\selfie_segmenter.tflite` read by OpenCV; `graphics.py` pixel font / seven-segment / firework / streaks, `fusion.py` Fusion
  .comp text, `knowledge.py`, `photos.py` photos as still shots (2026-10-24: any format the right way up, HEIC through
  pillow-heif, the brief's sheet), `app\` the app); `tools\config.json` every detection threshold (`_comment` keys
  explain units) + `tools\config.local.json` (2026-10-24, not in git: this PC's own values laid over it by
  `util.load_config` - an update never touches it; the updater moves a clashing tuning there by itself)
- `projects\<name>\` may hold photos beside the clips (2026-10-24): `project.clip_files` = videos + photos, never a
  Mac's / iPhone's "._" files or an old add-on's `<photo>.jpg.mp4` twin; `prep_footage.py` caches a photo as ONE frame
  (meta "photo": true), the quick draft makes it a still shot with a slow zoom (`draft.photo_shots`), compose.py's
  clip layer `"fit": "contain"` shows a whole photo over a blurred copy; `resolve_build.py` refuses a plan with photos
  (not placed in Resolve yet)
- `docs\` hand-offs: `resolve_notes.md`, `option2_resolve.md`, `claude_tips.md`, `knowledge_sharing.md`,
  `organization.md` (repo/versioning plan), `app_pages.md` (the app's pages - read a page's section before changing
  it), `roadmap\` (`roadmap.json` = the roadmap's ONE data file, `index.html` = the motion graphic drawn from it,
  played live on the app's Home) -> `roadmap.png` (README; `roadmap.mp4` stays local)
- `.app\` the app's cache and logs (`server.log`, `deleted.log`, `install.log`, `jobs\` + `jobs\history.jsonl` (0.4.4:
  jobs ended), `batches\` (0.4.5: bulk Claude work - `/analyze-reference batch <id>`, `/recreate-video batch <id>`),
  `player\` (player copies), `open_claude.cmd`, `server.json`);
  `settings.json` = the user's app settings; `.claude\skills\` = `analyze-reference\` (+ `lessons.md`),
  `write-script\` (+ `guidelines.md`), `write-title\` (+ `guidelines.md`), `recreate-video\`, `generate-video\`,
  `write-prompt\`, `whats-next\`
- Repo files (v0.4.1): `README.md`, `setup.bat`, `Install-MotionLab.cmd` (the installer: download + double-click;
  `-Here` = setup.bat's repair run; docs\organization.md *Install*), `LICENSE` (MIT), `CHANGELOG.md` (the Update
  button's dialog shows it) + `CHANGELOG.es.md` (the same sections in Spanish from 0.5.1 on - the app in Spanish shows
  them, a version missing there in English), `.mcp.json` (MotionLab's MCP server), `.claude\settings.json` (a
  SessionStart hook: cloud sessions only, docs\cloud.md), `.github\workflows\tests.yml` (GitHub's tests, see Publishing),
  `.gitignore` (refs, analysis, projects, library, settings.json, .app, .venv, knowledge\local|inbox|outbox and the
  self-test videos stay private), `.gitattributes` (LF in the repo, `.bat` always CRLF), `MotionLab.ico`. The
  version is `tools\motionlab\__init__.py` `__version__`.

## Tools (run from C:\MotionLab as `.venv\Scripts\python tools\<tool>.py`)
The usage of each is its docstring and the skills say when to use which; beside a name only what its docstring does
not say, or a rule.
- Analysing: `analyze.py "<video>"` (the full pipeline; `--category` / `--tags` / `--focus` are kept in meta.json; it
  refreshes the video's reference card; a video replaced under the same name is measured again, even with
  `--redetect`), `report.py`, `feedback.py` (`--import` = also into verdicts.json),
  `sheet.py` (any frame range), `content.py` (what a video says and how it performs; MCP `transcript`), `colour.py`,
  `download.py` (yt-dlp); `motionlab\profile.py` = the video in numbers per focus
- Notes from a video (2026-10-27): `notes.py prepare <video>` (MotionLab's part: words, key frames, chapters, Most
  replayed, sponsor parts) and `notes.py save <name> <draft.json>` (Claude's notes through the gate: every quote found
  in the transcript, the frame + timecode set by the tool, the limits)
- Sets that are not a video: `thumbsets.py` (thumbnail sets; Claude's patterns = `/analyze-reference thumbs <set>`,
  used by `thumbnail.py make / check --style <set>`), `textsets.py` (scripts & prompts, 2026-10-18: Claude's check of
  a text is saved only when every quote is found in THAT text - `prompts.verify_check`, also behind `prompts.py
  annotate` / a JSON `import`), `templates.py` (captured template clips + the Motion Graphics library: 189 templates in
  `tools\overlays\motion\`, 57 rebuilt from the Swishy clips, 18 MotionLab originals and 114 MotionLab builds in the
  Editorial warm look)
- Making: `prep_footage.py` (0.6.1: every clip read once into a light cache - `build\cache\<ID>.light.yuv`, the
  stats - and a sparse full cache that `render_video.py` fills with only the frames a plan shows: 36 clips / 6.5 min
  of footage 2.1 GB in 35 s instead of 33 GB in 131 s; `--full` = the old way), `catalogue.py` (0.6.1: the clip
  catalogue `build\clips.json` - each clip's moments by the analyser's cut detector on the light frames, usable / bad
  windows, motion, light, look-alike groups, the day filmed, key frames on sheets, Claude's line per moment via
  `say`, the user's line wins; the brief carries it, `motionlab\catalogue.py`), `storyboard.py`,
  `render_video.py` (0.6.0: masters every render's sound -
  `motionlab\loudness.py`, config "master": -14 LUFS, true peak <= -1 dBTP after AAC; `--no-master`),
  `compare_renders.py`, `miniedit.py` (0.6.0: the app's Editor tab - `state` = the shots, graphics, captions,
  sound effects of a plan; `apply <changes.json> --build` = the user's changes in order (trims, moves, splits, speed,
  graphics moved / added from a template / set, sound effects added / moved / louder / swapped, captions) -> the next
  plan, the clips' sound cut again (a sped-up shot's stretched, the pitch kept), the graphics' copies and new ones,
  outcome.json "hand_fixes", one build; `media` = the preview's light copies, loudness and filmstrip in
  `build\editor\`; the engine is `motionlab\miniedit.py` + its effects `edfx.py`, keyframes `edkeys.py` and
  transitions `edtrans.py`), `draft_edit.py` (the quick
  draft by rules; `--feel-test`; talk mode cuts the stumbles too - `--keep-stumbles`), `style.py` (the style of up to
  3 analysed videos; `closest "<words>"`), `overlay.py`
  (graphics as HTML via HyperFrames, pinned in `tools\overlays\`; `snap` = stills straight from the HTML, the cheapest
  check; `fit <folder> --like <video>`), `fonts.py` (`sync` after adding a family), `logos.py` (92 logos), `sfx.py`
  (sound effects - never guess a volume; `--voice` / a plan's `"sfx": {"voice": true}` = a talking video: very subtle
  over words, levelled to the voice in pauses; 0.6.0: `library --export-list` writes `tools\sounds\import_list.json`
  - the shared list of which pack sound is which kind, never the sounds - and `tools\sounds\cc0\` + `made\` (the CC0
  ones and the ElevenLabs ones the user kept) every PC gets; `import <pack> --listed` sorts a friend's download by it; `--fav`, a plan's `"sfx": {"sounds"}`;
  `generate` = sounds made with ElevenLabs from `tools\sounds\generate.json`, `share` = the paid-plan ones as a zip,
  `import <link | zip>` = a friend's; 0.6.0: a plan's `"sfx"` `"bed"` = an ambience bed looped under the voice,
  `"logo"` = My Brand's sound logo on the end card), `music.py` (0.6.0 step 10, `motionlab\music.py`: the music
  library - refs\audio's downloads read in place, songs and ambience beds added in `library\music\` (+ `ambience\<kind>\`),
  each measured once into `library\music\music.json` - tempo, energy, tone, drops; `beds` = ElevenLabs loops; the
  app's Motion Graphics > Music, New edit's song cards and *Ambience under your voice*), `beats.py`, `precheck.py`
  (checks before the final render; exit 1 =
  look; a video's loudness and true peak too; build.py adds `precheck.face_cover`: a caption / graphic over the
  face, upright safe zones = `motionlab\safezones.py`, TikTok / Reels / Shorts and "all" = the strictest, the same
  numbers in facefit, the Editor's guides and brief.py's *The safe area*; `precheck.talk_checks`: a talking video's tail after its last word, whooshes per 30 s;
  and, for a plan with `"captions_fit": "chin"`, `motionlab\facefit.py` places each shot's captions off the face),
  `speech.py` (speech to text, optional install; `--verbatim` keeps the fillers; `stumbles <take>` =
  `motionlab\stumbles.py`: fillers, repeats, retakes, "cut / again")
- Prepare and posting: `script.py` (the script check; the app's requests - kinds new / improve / title / prompt,
  `show <req-NNN>`), `prompts.py` (the prompt library; MCP
  `prompts`), `thumbnail.py`, `publish.py` (YouTube's rules checked first, nothing written on a FAIL), `brand.py`
  (My Brand, 0.6.0: `import [url]` = read the user's own website - `motionlab\siteread.py`, the app's job
  `brand_import`; `show` = the *For my brand* brief; `selfcheck`)
- The lab: `knowledge.py` (`memory` = Claude's memory, also MCP `knowledge(category="memory")`; `memory --styles` /
  `knowledge(category="memory:styles")` = without the effects - for scripts and titles; `next-lesson-id [--kind
  making]`; `pending` also lists what stays on this PC), `usage.py` (What it took; the app shows time only -
  the user's call), `whatsnext.py`, `roadmap.py`, `storage.py` (`--prune` deletes only what the lab can rebuild -
  never sources, knowledge or media a Resolve project uses), `mcp_server.py` (MotionLab's MCP server, read-only -
  prefer its tools to reading events.json), `app.py` (`--no-window --stay --no-update --port N` = a test server)
- DaVinci Resolve (`docs\resolve_notes.md`): `resolve_build.py`, `library.py build | test | title | install`,
  `resolve_mcp.py install | status | remove` (optional, this PC only)
- Tests: `selftest.py [--extended]` (the synthetic test videos scored - must PASS after any change;
  `make_testvideo.py [--extended|--negative|--vfr]` builds them), `tools\dev\install_test.py` (the installer's tests,
  ~2 min, never touches this PC; `setup.bat /lab` = the lab steps alone), `tools\dev\smoke.py` (every module, GET
  route and page, the MCP server, the Spanish catalogue, Home once in Spanish), `tools\dev\i18n_check.py check | todo
  <area> | scan | areas | merge` (the app's Spanish, 0.5.1: `check` must PASS - every key has its Spanish with the same
  {placeholders} and tags, no unused keys; `todo` = an area's texts not wrapped yet, `tools\dev\i18n_areas.json`;
  `merge` = the part files -> `ui\i18n\es.json`)

## Workflow
- A reference: download > lab pass (`analyze.py`, with the user's focus) > Claude checks (`/analyze-reference`) = ready
  for edits; then, optional ("Teach Claude" in the app): the user's verdicts > Send it to Claude > Share (Claude's
  memory > Shared knowledge).
- When the user pastes text starting with `MOTIONLAB FEEDBACK`, or a window starts with "Apply the MOTIONLAB FEEDBACK
  in <file>" (the app's *Send it to Claude*: the newest `analysis\<name>\feedback\app_*.txt`), follow "Applying
  feedback" in the `/analyze-reference` skill and report exactly what changed; pasted feedback also goes into
  verdicts.json (`feedback.py <name> <file> --import`). Afterwards remind the user of Claude's memory > Shared
  knowledge > Share my knowledge.
- Measured help for reviews (evidence only, never changes events): every flash gets a "flash look" line
  (`flash.look_*`), and each analysis lists "possible misses" (`near_miss`). Record a verdict per possible miss in
  review.json `"_near_misses"` (lessons L001, L006); the user answers them in the app (verdicts.json `misses`).
- Report and app layout follow the user's notes (2026-10-06/07): per effect the preview, "What happens" and
  "Measured evidence" are open; timing / origin / rebuild ("In depth") and the contact sheets ("Frame list") are
  folded; false alarms are folded (verdict optional); possible misses are red until answered. Since 2026-10-18 every
  review is one pattern (app CLAUDE.md "Reviews"): the thing on the left, the review panel on the right - Correct /
  Partly / Wrong (keys 1 2 3), J K N, the note, Send it to Claude.
- Saving library effects: start from `projects\<name>\build\library_picks.json` and `[save to library]` notes; add a
  builder + `META` entry + test `CASES` in `tools\library.py`, then `library.py build` and `library.py test` (every
  macro must render in Resolve; `docs\resolve_notes.md`).
- Any change to `config.json` or `tools\motionlab\` must be followed by `selftest.py --extended` (all PASS).
- Publishing a new version (the repo owner = the user, with Claude's help): self-test `--extended` all PASS, raise
  `__version__` in `tools\motionlab\__init__.py`, add a `## x.y.z - date - title` section to `CHANGELOG.md` (the
  update banner shows it; it takes in the `## Unreleased` lines - the app shows only version sections) and the same
  section in Spain Spanish (tú) to `CHANGELOG.es.md`, raise `API_LEVEL` in `server.py` + `app.js` if the page needs
  new routes; the user commits and pushes (the roadmap's "here" too: `roadmap.py sync`; a new roadmap label's Spanish
  goes into `tools\motionlab\app\ui\i18n\parts\es.release.json` as `<English>|roadmap`, listed in its `_by_key`). GitHub's full tests (self-test + `tools\dev\smoke.py`,
  ~15 min) run only for a new `x.y.0` or by hand (Actions > Run workflow); any other new version (0.4.2.1, 0.4.3...)
  gets a ~1 min release check (every file compiles, its CHANGELOG section, the roadmap's "here") - the user's choice
  2026-10-15, so the local `--extended` + smoke before a release are the real gate. A green run moves the `tested`
  branch, which is what the Update button installs, and tags `v<version>` (docs\organization.md "Tests on GitHub").
  A change to `Install-MotionLab.cmd` / `setup.bat`: `tools\dev\install_test.py` all PASS, then a clean Windows run
  before telling friends.
