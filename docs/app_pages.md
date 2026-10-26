# The app's pages - how each one works and how it came to be

Moved here from `tools\motionlab\app\CLAUDE.md` on 2026-10-19 (the same text, one section per page), so Claude Code
no longer loads ~60 KB of page history whenever it touches the app folder. **Read a page's section before you change
that page.** What holds for every page stays in `tools\motionlab\app\CLAUDE.md` (loaded by itself there): the rules,
the contracts (`reviewPanel`, `stylePicker`, `sharedChip`, `ownVideos`, the Player's keys...), the API_LEVEL list and,
per page, the user's own words and its never / always rules - read both. A new page decision: the user's dated words
and any never / always rule go into that file's **Pages** list; how the page does it goes here.

## Sidebar and Home

- Sidebar (0.4, the user: "only 3 main sections: analyze, edit, generate"; Prepare added after 0.4.1 at the user's ask):
  Home, *Make a video*: **Analyser** (shown as Analyze until 0.4.3.5; #/analyze, #/analyser = an alias; = 0.3's
  References, `pageRefs`; #/ref/<name> = one analysis),
  **Prepare** (#/prepare, `pagePrepare`, green; below), **Editor** (shown as Edit until 2026-10-15, the user: "rename
  the entire edit page/section to Editor"; #/edit stays, #/editor = an alias; = Videos, `pageProjects`;
  #/project/<p>), **Generator** (shown as Generate until 0.4.3.5; #/generate, #/generator = an alias; `pageGenerate`;
  the prompt library #/prompts belongs to it) - no numbers (the user, 2026-10-14: they are not steps in an order),
  each row in its section's colour (`--rc`) - then **Claude's memory** (below; #/memory/shared = Shared knowledge,
  `memShared` - #/memory/learned (0.3's Knowledge, then Share with friends) and #/knowledge are aliases of it; #/library
  leads to #/memory since 2026-10-22), with **Motion Graphics** (0.5.0, #/motion, `pageMotion`, coral; below) right above
  it since 2026-10-25 (the user: "put motion graphics in the sidebar above claude memory"; at the bottom above Jobs
  from 2026-10-22). At the bottom **More** (2026-10-25, the user: "there is too much stuff already on the sidebar at the
  bottom so lets add a menu thingy or three dots that expands and appears 'jobs and settings' also change the settings
  icons for a cog"): `#side-more` (three dots) opens `#side-menu` in place = Jobs and Settings (`sideMore(open)`,
  remembered in localStorage `ml.navMore`, opened by itself on those pages; a running job's count rides on More as
  `#jobdot` while it is closed; Settings' icon is a cog), Settings (tabs `setTabs`: General, Storage, Claude
  skills = #/skills, `data.skills()` reads `.claude\skills\*\SKILL.md`; the plain words + how to type it =
  `SKILL_INFO`; /whats-next is marked "for developers"). `ALIASES` rewrites the 0.3 addresses (#/refs, #/projects,
  #/knowledge, #/library). Home = the hero animation, **What do you want to do?** (`WAYS`: four cards with their
  buttons and counts - `status()` carries `prompts` and `lessons`), setup warnings, roadmap
  (`roadmap_live` = `docs\roadmap\index.html` in an iframe - a motion graphic that fetches `roadmap.json` and plays
  live, paused off screen, still with reduced motion; no clicks inside on Home, `.rmhit` = `roadmapBig()` full size;
  the PNG lightbox only when the page is missing; since 0.5.1 it draws the phases - roadmap.json `phases`: Phase 1 up
  to 0.5.0.1, Phase 2 from 0.5.0 to 1.0.0 - and inside the app its words follow the app's language: the page reads
  `window.parent.ML_I18N`, keys `<English>|roadmap` in `ui\i18n\parts\es.release.json`); *Prompts for AI
  tools* = `aiPromptsModal` (Generate a new prompt, a shot picked). Each page sets
  `body[data-page]` (analyze / edit / generate / memory / jobs / settings) -> its accent colour (`--acc`: cyan / amber
  / fuchsia (`--gen`, the user's pick 2026-10-14; pink before) / violet / blue; Prepare green; CSS only, motion off
  with prefers-reduced-motion); since 0.4.1.1 (the user's pick "Bold
  band", the end of app.css) the five sections' top pages (`.head:not(:has(.crumb))`) put the title on a band like
  Home's card - an icon tile (`--sf-icon`), no number - over a faint texture of their own (`--sf-tex`,
  `main::before`), panel edges / hover glows / `.btn.pri` in `--acc`; sub-pages keep the bar + texture only; no
  markup.

**Home**: `heroAnim()` first (a CSS-only motion graphic: 24 s loop of 4 scenes, transform + opacity only - measured
1 layout and 10 ms main-thread work in 6 s; reduced motion = a still scene) with *Paste a link* (`addVideosModal`);
no subtitle; setup warnings only when a program is missing; no "Updated to" box (only when an update set aside local
changes); the roadmap last. No Claude's memory line and no Status panel since 2026-10-22 (the user: "in Home: remove
the Claudes memory section and the Status section"; Resolve's state is in the sidebar, the disk in Settings > Storage,
the jobs on Jobs). (*Where to start*, the six `FLOW` steps as buttons, is no longer on Home.) The
patterns every page follows - empty pages, the first row of actions, *Folder* buttons, Delete's wording, optional
steps, `modalBack` - are in `tools\motionlab\app\CLAUDE.md`. *Recreate with my footage* = `newEdit({from:
'reference', pick})` (the New edit pop-up).
- **Pages that update by themselves + the NEW badge** (2026-10-24, a friend's asks: "what is created shows up without
  going to another section and back"; "a red NEW, top left, on everything new - gone once I click it or go to another
  section"): `liveTick` every 5 s asks GET `/api/changes?s=<data>` for a list page (`LIVE_PAGES`: Home, Analyser and
  its tabs, Editor, Generator, Prepare, Prompts, Motion Graphics, Claude's memory; `live.changes` = directory listings
  and file times, a few ms) and, when it changed, `route(true)` draws the page again - no *Loading…*, the scroll and
  typed search words kept - but never while a dialog, the lightbox, the teleprompter or *Preview your thumbnail* is open,
  while the user types or a video plays with sound (`userBusy`: it waits). A page of ONE thing is never redrawn by
  itself. The badge: `newTag(key, when)` as the first child of a card (`.newtag`, #e5202e) when the card's time is
  after its section's `at` (GET `/api/seen`, `.app\seen.json` - every window agrees; a section seen for the first time
  starts now) and it was not clicked (a click = POST `/api/seen` {section, key}); leaving a section of the sidebar
  (`route`, `NEW_SECTIONS`) clears its badges. The times: a video = its newest FINISHED render (`live.render_done`:
  the MP4's boxes run to the end and one is "moov" - never a video only made or given clips; a new version is NEW
  again), a prompt / script / title = `created` (key = id + time: a deleted script-014's number is never given again,
  `prompts._last_id.txt`), an analysis = events.json's time, a set / a template = its folder's creation.

## Analyser

- **Analyze** (0.4, the user: "pass videos downloaded or pasted as a link, analysed in a concrete way I select:
  content creation / cinematic / both"; 2026-10-18: "improve the "analyser" i think it would be cool to also be able to
  analyz anything i kinda want remaining, for now i have videos and tuhumnails but it should also be able to analize
  propmpts. so maybe create the big 3 buttons similar to prepare section but for "videos" "thumnbails" "scripts" make
  sure it is able to handle batches or multiple at the same time, imagine i wanted to analize 10 prompts at the same
  time i could and it wouldnt allucinate"): `pageRefs(main, tab)` = the head band, then **three ways** `.gways.g3` in
  Prepare's `.gway` markup - *Videos* (`#an` *Add videos* pri, then `#dl` *Download from link* ghost), *Thumbnails*
  (`#tadd` *Add thumbnails*), *Scripts & prompts* (`#txadd` *Add scripts or prompts* = `addTextsModal`, see **Text
  sets**) - each with a counts foot (`.gway-foot`, only when its kind has something: "12 videos analysed · 2 not checked
  by Claude yet", "3 sets · 45 thumbnails · 1 without patterns yet", "2 sets · 18 scripts & prompts · 4 not checked
  yet") that links to its tab; then the in-progress panel `#avprog`, the open batches (`batchRows`), the `.wbar`; then
  the **tabs** `.tabs.antabs` (`AN_TABS`: Videos `#/analyze` (= `#/analyze/videos`) | Thumbnails `#/analyze/thumbs` |
  Scripts & prompts `#/analyze/texts`, an icon + a count each; the way whose tab shows is `.gway.on`) over `#antab` =
  that tab's list (Videos: the filter row `.frow` + the `refCard`s; Thumbnails: `setCard`s; Scripts & prompts:
  `textSetCard`s; an empty tab = a `.pcempty` "... land here" line). Tabs, not one long page: the user's "nothing
  important under a list" (2026-10-15) and room for a 4th kind. An empty lab = the three ways (no emptyHero, no tabs;
  the test-videos box stays, `$('#tests')` guarded). Each dialog goes to its tab after a submit (Add videos
  `#/analyze`, Add thumbnails `#/analyze/thumbs`, Add scripts or prompts `#/analyze/texts`). Home's card *Analyze what
  works* = three buttons Videos / Thumbnails / Scripts (`WAY_GO` link / thumbs / texts) + a foot with the three counts
  (`/api/status` `thumbs` = the sets' pictures, `texts` = the sets' texts); the sidebar tooltip names all three.
  *Add videos* = `addVideosModal` (links one per line + files from refs\ or a
  path, up to `AV_MAX` 10; the focus `FOCUS_OPTS`; kind of video; "Claude checks each video when it is measured" =
  claude:true per analyze job, or Measure only) -> POST `/api/analyze/batch` (`server.analyze_batch`: everything is
  checked before anything starts; files -> queued analyze jobs, links -> queued download jobs whose `then` starts
  the analysis of the saved file; `system` remembers `default_focus`). The page's in-progress panel
  (`progressPanel`, every 2 s while jobs are active: running first, then waiting, *Remove* = cancel a queued one;
  since 2026-10-15 a finished one shows `DONE_SHOW_S` 5 s, a failed one up to 15 min, each with ✕ = `hideJob`,
  remembered in localStorage `ml.goneJobs` by `jobKey` = id@started, ids restart with the app - the user: "Done …
  showing all the time? a 5 s pop up, or a discard option"; the video page uses it too) redraws the cards when one ends. Cards (0.4.3.5, `refCard`, the
  Editor's `.pcard` look): the frame with the date it was analysed (`strTime` of events.json "generated" -> `whenWords`;
  newest first) and *not checked by Claude* until it is, the name (`label`, 2026-10-19: `data._kind` ->
  `knowledge.label()` - meta.json label, Claude's breakdown name, the title without yt-dlp's [id]; the file's title on
  hover; also the analysis page's title and Home's next lines), length · category · format, cuts/min · effects +
  the focus chip, the next-step line with its button (no dots since round 2); Delete on hover. *Add videos* comes
  before *Download from link*; *show the test videos* = the filter row's right end (`.frow`). The analysis page's
  `flowStrip` (round 2, the user: "remove the listing in analyze as well"): no numbered steps - "✓ Ready" or "Not
  checked by Claude yet" + the next thing (`flowNext`) and its button (`flowAction`). The downloads nobody analysed are one thin row
  (`.wbar`: "N downloaded videos wait to be analysed", music / photos counted apart) that opens `waitingModal` (the
  `waitRows` table, *Analyse all…* up to `AV_MAX`); filters focus / category / tag.
- **Preview your thumbnail** (2026-10-24, the user: "upload ur thumbnails and have it like a test on a fake generated
  yotubue page (updated if possible) like a preview layout thumnbail to see if the thumnbail matches the vibe or pops
  from a normal youtube user feed", then "a button ... "preview your thumbnail" ... besides big youtubers like mrbeast
  ... probably of highly viewed recent videos if possible"): `#ttest` on the Thumbnails way -> `thumbTest()`, a
  full-window `.yttest` over the page (Esc / Close): a copy of today's YouTube - Home grid (4 columns, 12 px corners,
  36 px avatars, Roboto from the font library), Search (500 px thumbnails), Up next (the 168 px column beside a
  player), a phone - dark or light. The feed around the user's pictures = GET `/api/thumbtest` (`data.thumb_test`):
  *Big creators - newest, most viewed* (the default: `motionlab\thumbfeed.py` - yt-dlp lists each channel's 10 newest
  videos, the 5 most viewed are kept, pictures in `.app\thumbfeed\img\` served by GET `/api/thumbfeed/<id>.jpg`;
  fetched by the job `thumb_feed` (`jobtools.py thumb-feed`, group net) at the first look and when older than a day -
  *Get the newest videos*; *Channels…* = the list, POST `/api/thumbfeed/channels`, `.app\thumbfeed\channels.json`,
  empty = the 16 usual ones), one analysed set, or all of them; *Or one made in MotionLab…* = Ready to post's
  thumbnails. Theirs: picked or dropped (object URLs - nothing
  is saved, nothing leaves the window), each with its title and channel to type; placed among the first ones seen,
  *Shuffle* moves them, *Squint* blurs the page (what still reads is what pops), *Where is mine?* outlines them.

## The analysis page

One analysis (#/ref/<name>, `?verdicts` = the Effects tab): tabs right
  under the step strip - **Overview** (default; `overviewTab`: Rhythm, Content creation and / or Cinematic panels for
  the focus from `profile.py`, Claude's breakdown (events.json `breakdown` = review.json `_breakdown`), Use it: Edit
  my clips like this / Prompts for AI tools like this / Analyse again with another focus; the player is hidden),
  then **Colour & look** for the cinematic / both focus (`colourPanel`, `data.colour_info` from
  `colour\colour.json`: the look's words, the five main colours, every shot's main colour as a strip with frame +
  timecode tooltips, brightness / colour / frame in words; not measured yet = *Measure the colour* = job `colour`
  (`tools\colour.py <name>`, group light, no decoding)), Effects, Possible misses, What it says (the Content tab). The
  steps (`FLOW`; the strip itself shows no numbers since round 2 of 0.4.3.5): Download > Measure > Claude checks |
  *Teach Claude (optional)*: Your review > Send it to Claude > Share; a video with no effects (a talking head) shows "No
  effects" instead of crashing. Timelines fix their canvas height at creation (no ResizeObserver loop when shown).

- The analysis page's **Content** tab (0.3.5, `contentTab`, `data.content_info`): how the video performs
  (`content\stats.json`: views, views ÷ followers, views a day, likes, comments, followers; job `content_stats`) and
  what it says (`content\transcript.json` lines with frame + timecode - a click moves the player, the line being
  said is marked, search; job `content_transcript`). Both jobs = `tools\content.py` (group net), nothing downloaded.
- The analysis page (#/ref/<name>, `?e=E004` selects an effect, `?misses` opens the misses tab), the user's
  2026-10-07 layout, since 2026-10-18 in the one review pattern (**Reviews** in `tools\motionlab\app\CLAUDE.md`):
  header + workflow strip
  (`data.flow`: download > lab pass > Claude checks > your review > Send it to Claude > share - its button goes to
  #/memory/shared -, with the next step's button); the full-width frame-accurate player + two timelines (red dashed
  line + ▲ = possible miss); tabs **Effects** (left = the effect card: looping preview with frame + timecode burned
  in, what happens, evidence, In depth / Frame list folded - or the end card after the last effect; right = the review
  panel `#rvp-fx`: *Is Claude right?*, one row per effect with the list's filters (search, type, verdict, renamed by
  Claude; false alarms hidden unless asked for, then optional), Correct / Partly / Wrong (keys 1 2 3), the note,
  Previous / Next / Next without a verdict (J K N); "Correct" moves on by itself, Partly / Wrong focus the note,
  Ctrl+Enter moves on; *I want this effect in my library* on the current row; *Missed effects / general notes…* and
  *Agree with all false alarms*; *Send it to Claude* = `sendFeedback(name)`: POST export (`feedback\app_<time>.txt`)
  then Claude `Apply the MOTIONLAB FEEDBACK in <path>` (task feedback), the raw text behind *Copy what Claude gets* =
  GET `/api/feedback/<name>`; the fixed bottom bar `.fbbar` is gone) and
  **Possible misses & sound** (the same layout: left = the current miss's three frames (a click seeks) + why +
  Claude's check, or the sound question; right = `#rvp-miss`: the Sound row and the misses, red until answered -
  "Not an effect" ✓ = 1, "It's an effect" ★ = 2 (green first since 2026-10-18) + what; stored in verdicts.json
  `misses` by frame and exported as a `--- possible misses ---` section that `tools\feedback.py` parses). The
  verdicts save WHOLE 450 ms after the last change (and at once before Send) through POST `.../verdicts`; the
  timelines' verdict line, the tabs' badges and the strip follow. 0.4.2 (plan item 8, Claude cannot hear): the tab is
  *Possible misses & sound* (*Sound effects* when a video has no possible miss, so every analysis has it) and starts
  with **Sound effects in this video** (None / Some / Many = 1 2 3 + where, red until answered, counted in the tab's
  badge and the end card; not in the workflow strip's verdicts step) -> verdicts.json `sound`, exported as
  `--- sound effects ---` (`MANY | where: ...`, `(not answered)`); `feedback.py` parses it (`fb["sound"]`) and
  `--import` lays pasted feedback over verdicts.json (`feedback.to_verdicts` + `data.save_verdicts`).

## Bulk and thumbnail sets

- **Bulk** (0.4.5, the user: "bulk analyze thumbnails, videos, and also bulk edit stuff or generate"): a batch =
  `.app\batches\<id>.json` (`data.new_batch / get_batch / batch_state / batches / forget_batch`; kind `review` |
  `recreate`; done = review.json / an edit plan by Claude newer than the batch). *Add videos* with Claude's check
  (2+ videos): each measured video is collected (`Runner._collect`) and the batch's LAST job to end (downloads,
  measuring, in any order; `Runner._batch_to_claude`) opens ONE window `/analyze-reference batch <id>` (one measured
  video = the usual single check). *Editor > Edit several videos* (`bulkEditModal`, 2-10 videos with clips, style =
  up to 3 analysed videos or presets + words, length / format) -> POST `/api/edit/batch` (`server.edit_batch`: all
  checked first, the same `edit_request.json` in each, `music` "" = each folder's own song) -> `drafts` = a queued
  draft job each, or `claude` = a recreate batch + `openClaude('/recreate-video batch <id>')`. Open batches show as a
  `.bkrow` (`batchRows` / `wireBatchRows`) on the Analyser / Editor with *Continue the batch* (the skill skips what is
  done) and ✕ (POST `/api/batches/forget`). Estimates: GET `/api/estimate` = `data.estimate()` (What it took's median
  minutes per video on this PC per task; left out when never measured) -> `estWords()` in *Add videos* and *Edit
  several videos*. What it took splits a batch round per video by what each tool call named (`usage.split`); the
  live line adds "3 of 10 done" (`data.live_claude` `batch`).
  **Thumbnail sets** (`motionlab\thumbsets.py`, root `thumbsets.ROOT` = `analysis\thumbs` - `MOTIONLAB_THUMBS_ROOT`
  moves it for tests, `data._thumbs_root()` follows it): the Analyser's *Add thumbnails* (`addThumbsModal`: a channel /
  playlist link + the newest 10-30 = job `thumbs_fetch`, video links = `thumbs_links` (group net), or pictures =
  `uploadThumb` -> POST `/api/thumbs/<set>/upload?name=` raw body -> `data.thumb_upload` (via `.app\tmp\thumbs`, then
  `thumbsets.add_files` copies + measures); the set's folder name = `setSlug` = util.safe_name), its progress in the
  Analyser's panel (`THUMBS_JOBS`), the Analyser's Thumbnails tab (since 2026-10-18; its cards = `setCard`, GET
  `/api/thumbs`, "of N on the channel");
  a channel is listed whole once (set.json "channel"; `get_set` gives only its numbers: total / in_set / left, None
  for a set from before the listing was kept) - the dialog's first batch = `#tsn` + `#tsord` (newest / most viewed),
  the set page's *More from the channel* (`moreThumbsModal`: how many, which, "N sheets for Claude") = job
  `thumbs_more`, followed by the page's own `#tsprog` (`TS_STOP`), which redraws when it ends; *Measured by
  MotionLab* sits ABOVE the pictures (the user: nothing important under a list), then the sort row (`TS_SORTS`,
  `tsSorted` moves the cards - no reload; newest / oldest = the item's `pos` in the listing, exact, else its date),
  *Update the views and dates* = job `thumbs_refresh`; a card = `#n` + title, then views (`compactNum`) · views ÷
  followers · `dayWords` (the exact date - `thumbsets.exact_dates`, yt-dlp per video, 3 at a time, ~1 s a video,
  after fetch / more / refresh (the user: "list the date on the thumbnail card"); until then or when YouTube does
  not answer, the listing's approximate one said "≈ 3 weeks ago") · length (`lenOf`); a set's page
  `pageThumbs` (#/thumbs/<set>, crumb + Delete -> #/analyze/thumbs; GET `/api/thumbs/<set>` = set.json + style +
  `verdicts` + `lines`; the user's round 2026-10-15: "a dropdown or pop up so they don't take up all space ... I also
  want to look at the thumbnails while reviewing"): `.tslayout` = the pictures (`.tsgrid`) + `.tsside` (◂ folds it =
  `TS_FOLD`, *What they have in common ▸* opens it) - since 2026-10-18 the review panel (`reviewPanel`, **Reviews** in
  `tools\motionlab\app\CLAUDE.md`): *In short* folded on top, the patterns as rows (kind + what, "how many · #2 #5"),
  the current one lights up its example pictures (`.tscell.hl`, the rest `.dimmed`), a second click lets it go; ✓ ~ ✗
  + the note = POST `/api/thumbs/<set>/verdicts` {patterns: {P: {v, note}}} (`verdicts.json`, one home); extras = the
  font measured, colours, words, structure; Send = `/analyze-reference thumbs <set>` (task review), which reads
  verdicts.json first; without Claude's style.json the side says what Claude does there. *Find the patterns with
  Claude* (`pri`) / *again* (`.tsfind`: accent border + glow) = the same command -> style.json; above the pictures
  *Measured by MotionLab* (`.tsmeas`, folded, the `MotionLab · no Claude` chip - the user: "clear that it is only
  MotionLab NOT Claude"; Claude's own work carries the violet `.clchip`); a picture's ✕ = POST `.../remove`; Delete =
  trash kind `thumbs` (`plan_thumbs`). `.seg button.on` =
  `--kc` (a prompt kind's colour) else the section's `--acc` (before: invisible outside the prompt dialog). *Ready to post* > *In the style of* (`#pbsty`, `publish_info` `styles`) -> job
  thumb_make `style` -> `thumbnail.py make --style` (`thumbnail.style_values`: the set's design unless one is picked
  - "the set's" button -, colours, the closest design font, capitals). analysis\thumbs is never an analysis:
  `usage_names` / `took` need events.json, `trash.plan_reference` refuses "thumbs", analyze.py names a video
  "thumbs" `thumbs_video`, storage.py has one row per set.

## Text sets

- **Text sets** (2026-10-18, the Analyser's *Scripts & prompts* - the user's words in **Analyze**; `motionlab\textsets.py`,
  root `textsets.ROOT` = `analysis\texts` (`MOTIONLAB_TEXTS_ROOT` moves it for tests, `data._texts_root()` follows it),
  CLI `tools\textsets.py`): up to `MAX_ITEMS` / `TX_MAX` 20 texts - talking scripts, hooks, video / image prompts, briefs
  (titles stay in Prepare). Each text's ONE home is the prompt library (Claude's check card, wishes, Optimize, Film it,
  ratings, Style like keep working; the same words after folding = the same sha1 = re-used, never copied). The set =
  `set.json` (the lab's: items #n -> prompt id + sha1 + kind + measured `facts` + the check stamp; numbers never change,
  removing #3 leaves a gap), `patterns.json` (written only by `save_patterns`), `verdicts.json` (the user's: P# correct /
  partly / wrong + note), `claude\` (Claude's drafts, deleted once saved). No `.app\batches` kind: the set is the batch
  and `textsets.state` its only truth (checked = a stamp whose sha1 + kind match the record now; `left`, `stale`,
  `disputed` = the user marked parts wrong / partly, `to_sort` = files the lab could not read, patterns none / ok /
  stale, `done`). Measured inline (milliseconds, no job): words, language, the kind guess + why (`prompts.kind_evidence`),
  tool / needs (`prompts.tool_named` / `needs` = the twins of app.js `ptool` / `pneeds` - keep them alike), @-references,
  words that name a part (evidence only), twins (same sha1; 5-word shingles ≥ 0.8), phrases of 4-8 words shared by 2+
  texts with their numbers, the script check for scripts / hooks, the user's ratings. **`addTextsModal(pre)`**: a name
  (optional: the first words), one paste box (lines of only `---` between texts, or PROMPT n blocks) + a drop zone for
  .txt .md .docx .pdf (POST `/api/prompts/file`; a file = one text unless it has --- lines; one the lab cannot read =
  "Claude reads it" -> `to_sort`), the live numbered preview (POST `/api/texts/split`, nothing written: #n, a kind select
  = `kinds` {sha: kind}, words, "the same as #2 - added once", "in your library", too short / long), *Whose are they?*
  (*Mine* = source tested / *A creator's* + name or link / *Found somewhere* = creator with no name; `pagePrepare`'s lists
  leave out source creator), Claude's check now (one window `/analyze-reference texts <set>`, task review, label `texts
  <set>`; `estWords(EST.texts)` = `data.estimate` `texts`, minutes per text split by prompt id) or *Only save them* ->
  POST `/api/texts/new` (or `/api/texts/<set>/add`) -> `#/analyze/texts`. `textSetCard` (`.pcard.txcard`: the first words
  as the picture, "not checked by Claude" / "Claude checked k of N", the kinds, *Continue with Claude*, Delete on hover =
  trash kind `texts`, `plan_texts`: the set folder only, the texts stay in the library). **`pageTexts`** (#/texts/<set>,
  crumb -> #/analyze/texts; GET `/api/texts/<set>` = set.json + each item's `text` + `rec` digest + `state` + patterns +
  verdicts + `lines`): the Claude button (*Check them with Claude* / *Continue with Claude · N left* / *Check them again*),
  *Add more*, `.tslayout` = *Measured by MotionLab* (folded, `.mlchip`) above `.txgrid` of `txCell` (#n, kind badge,
  title, the first words, words / ≈ length, ✓ ~ ✗ + stars or "not checked yet", ✕ = out of the set: POST `.../remove`)
  + the review panel *What they have in common* (`reviewPanel`, as on a thumbnail set since 2026-10-19: a row per
  pattern = kind, what, the tool's "k of N · #2 #5"; the current row lights its texts `.hl` / `.dimmed` and marks the
  quoted words from `at` - `txExcerpt`, `mark.tq` -, a second click lets it go; ✓ ~ ✗ + the note = POST
  `.../verdicts` {patterns: {P: {v, note}}}; the stale line when the set changed; Send = `/analyze-reference texts
  <set>`, task review; without patterns the side says what Claude does there); a card = `promptModal(id, {set, ids, R,
  draw, reload})`;
  while the live line names the set (`data.live_claude`: `texts` + `batch` k of N) it refetches every 4 s. POST
  `/api/texts/<set>/kind` = the user's kind for #n. **Anti-hallucination by tools, not by wording**:
  `prompts.verify_check` (A every quote found in THAT text - whole words in order, pieces with ..., ≤ 400 chars, saved as
  the original words + `at` [start, end]; B missing = no words, clear / vague quote; C the kind's parts, once; D every
  part a row or `skipped` with why; E a part the script check flags not clear without `overrides` (kept as the row's
  `override`); F review.why quotes; G a model the text / file does not name dropped; H warnings) is the one gate of
  `prompts.py annotate` (+ `note_check` stamps the sets holding the text), the JSON `import` (+ `verify_source`: a copy
  from `source.file` must be in that file; `--set` sorts a file into a set) and `textsets.save_check` (+ the draft's sha1
  = the item's; words of another item named). Measured on this PC's 26 prompts: 244 of 248 quotes verbatim - the 4
  others (a paraphrase, pieces out of order, a summary) and 7 "clear" rows with no quote are exactly what it refuses.
  Prompt records gain `skipped` {part: why} and `verdicts` {part: correct | partly | wrong} (the user's, written through
  POST `/api/prompts/wishes` by the review dialog); old records stay readable (no `at` = "not verified"). PDFs:
  `prompts.file_text` reads them with pypdf (requirements.txt) when installed, else Claude does. analysis\texts is never
  an analysis: `trash.plan_reference` refuses it, analyze.py names a video "texts" `texts_video`, storage.py has one row
  per set, `usage_names` has `texts`.

## Editor and a video's page

Edit: **New edit** = a pop-up of steps (`newEdit(pre)`, 2026-10-22; was the four-step dialog `createVideoModal`, 0.4 -
  0.5.1). The user: "the edit a video is our most powerful tool so we kinda need to expand to give Claude the most
  options and customability ... simplicity and clarity rather than having everything in a single section"; a page for
  a few hours that day, then: "still make it a pop up as before? and just show section per section, make the sidebar
  steps with numbers isntead of letters, and make a line go through them so the user know where to go", in the look
  of their mock-up (`new_edit_section.html`, a deck in the lab folder: gold ticks and rings, cards with a corner tick,
  pills, a footer "Step n of 7"); round 3 the same day: "a little preview when we have selected clips ... manage them?
  delete ... too much text and it clutters the vision of the user ... less text and more colors, icons and more
  distinct" - so no line under the step titles, a coloured icon (`neIcon`, new sprite symbols) on every question, what
  a choice means in its tooltip, clips and references as pictures. `.mbox.nemodal` (the Editor's gold wherever it opens): a header, the steps on the
  left (`.nenav`: done = a gold tick + its short answer from `neRows`, on screen = a gold ring + *Now*, the rest grey;
  red = no clips; the line gold down to the step on screen, `.rchn`; a click jumps there), ONE step on the right (a
  title (+ a count on its right, `.nestx`), its cards and pills; `NE_STEPS`, one function each: `neClips`, `neText`, `neRefs`, `neStyle`,
  `neSound`, `neFinal`; each draws its `<section>`, writes `ne.st` and may return a refresh run by `ne.changed()`), a
  footer (*Step n of 6* | Back | *Next: <step> →*; on 6 the Resolve option + *Quick draft now* + *Make it with Claude*).
  Picked = a gold border, a tint and a tick (`.necard` and the modal's `.cvopt` / `.nep`). Only 1 is
  required; 2-6 carry `optTag()` and what is left on Auto is Claude's call. **1 Clips** = the two wide cards of
  2026-10-16 (the user: "choose between an old video clip or new clips, intuitive and distinct": *Clips you already
  have* = a video (a select with each video's clip count + *Folder*) | *New clips* = a name, the video made on the first file - POST
  `/api/projects/new`, then `uploadClip`; `ne.addFiles`, also 5's *Add a song…*), then the video's clips as pictures
  (`.neclips`: GET `/api/project/<p>`'s sources once per video, a frame each by `/api/thumb`; a click = the PC's player,
  POST `/api/open`; the bin = the app's Delete route for ONE file of the video's folder - `trash.plan_file`'s kind
  "clip": a clip or a song, warned when its edits use it or a Resolve project may - with the yes in the step itself,
  `.nerm`, since a dialog over this one would lose it; the + tile or a drop copies more in, a big drop zone while there
  are none) and the folder's songs as chips. **2 Text**: *What is the video about?* | *Text on screen* side by side
  (`.netwo`; their hints = the placeholders), *A script or brief from Prepare* (the library's brief / script / hook in
  a list with their coloured kind badge, *None* first, the picked one read beside it; a script / hook = a talking
  video: sound Talking). **3 References** = picture cards of this PC's analyses (`ownVideos`; the picture, its length
  - the end of the format label - and the name, nothing else: "i dont care about the cuts per min stuff"; up to
  `max_refs` 3, "1 / 3" by the title, a search over 8) + two cards *In its / their style* or *An exact copy* (one
  local analysis). **4 Style** (2026-10-22: "first make a row for the A ready-made style, then show the questions ...
  reduce ... to 4-5 options ... and a '+' ... show the color palette without having to scroll down ... make it more
  big"; fits a 1366x768 window, `@media (max-height: 820px)` trims the spacing): the ready-made styles in one row
  (`style.PRESETS`; `presets_info` carries their rhythm, drawn as grey bars by `neBars`: a shot each, the wider the longer,
  grey - colour is the palette's job; what each is = its tooltip), one compact card of questions (`.neqr`: the question left, pills right -
  `neChips` with `top: 4` + a "+N" pill for the rest, `NE_FIRST` = which answers come first, no Auto pill: nothing
  picked is Auto, a second click clears; every pill's help its tooltip) - where it was filmed, the type
  (`styles.CATEGORIES`), the rhythm, the mood (up to 3), captions, the feel in their words -, then the **colour
  palette** for titles / captions / graphics as big cards (`nePalette`: Auto + the ready-made palettes, a strip of
  their colours each; the colours themselves, up to 6, as swatches beside its title; none = Auto). **5 Sound**: the music as four cards (Auto, *A song* - the folder's or the downloaded ones in `refs\audio`,
  picked in a select under them, *Add a song…*, *From a link…* (0.5.4: an inline row - a dialog over this one would
  lose it - that starts the `download` job with preset mp3 and picks the saved song; *A song* with none yet shows
  that row instead of the file picker) -, the clips' own sound, Talking), sound effects - a card per amount (Auto / none / a few / some / many, a strip = how often
  one plays) and which kinds (groups of `motionlab\sfx.py`'s cue kinds) -, notes. **6 Final**: length (pills or
  seconds), format cards with the platforms (their shape drawn), **Build in DaVinci** (2026-10-25, the user: "move ...
  build it as a davinci project in the actual form in the final section and make it more simple ... add the davinci
  logo, and just say 'build in davinci'": one card `#nedvr` with the logo `logos\davinci-resolve\color.svg` on a white
  tile, a click = on / off = `st.resolve`; the footer's checkbox is gone), the summary (one table, a row per step - a
  click = back to it), the estimate as a chip ("About 30 min of Claude"; the rule in its tooltip: about 1 min of
  Claude per second of video, `editreq.MIN_PER_S` -> options `min_per_s`; with no length it asks for one); what the
  two buttons do = their tooltips; **For my brand** at the top, in the dialog's header on every step (the user: "add
  it like maybe on top? somewhere where it can be seen and also a small preview of what data its feeding": the
  switch + the logo, the colours, the website, the goal, the products switched on, the voice - *My Brand* below);
  in the footer *Make it with Claude* and *Quick draft now* (job `draft` = `draft_edit.py <p> ... --render`; needs a
  style: a reference, a rhythm, a ready-made style, their words or a talking script) -> POST
  `/api/project/<p>/edit_request` (`data.save_edit_request` -> `motionlab\editreq.py`: `clean` checks it - a request
  of the old dialog still passes -, `build\edit_request.json` ("v": 2) + `build\edit_brief.md` = `brief()`, the same
  in words per step for Claude, its sections numbered like the steps; `made_from` entries; the option tables =
  `editreq.options()` via GET `/api/edit/options`, English labels translated on the page by key,
  es.server-labels.json `_by_key`); the answer's
  `command` is always `/recreate-video request <p>`, so the user's words never pass through cmd. A video's page has *New edit…*; Edit versions say how each was made (a
  quick draft: its style + *notes* = `draft_vN.md`; `_plan_info` `made_by` / `style` / `notes`); GET `/api/prompts`
  carries `used` (prompt -> videos + their ratings: "Used in").
  **The Edit page and a video's page** (the overhaul of 2026-10-15, the user: "the blocks are so big and show random
  info - at least a preview of some render"; "when I first click I want to see the last render so I know in which
  video I am, instead of How did it turn out? shot in my face"; round 2 the same day: "list by the newest render; a
  date on the preview; just the length; Generate's icon for made from zero; remove 1 version 1 render; remind that the
  last render is not reviewed yet; rename my edits"): cards = `projCard` (`.pcards`, newest first by `list_projects`
  `sort_t` = the newest render's time, else the folder's creation time `_created`): `picture` (`data._picture`: a
  frame of the newest render ~30 % in via `/api/thumb`, else thumbnail A, a graphic's thumb.png, a clip's frame), the
  render plays muted on hover (not with reduced motion), on it the newest render's date (`whenWords`: today 01:37 /
  yesterday / 3 days ago / 12 Oct; "made …" without a render) and badges *ready to post* / *Resolve*; the name
  (`pname` = the `label`, else the folder name), the length only; facts row = clips · size or `genChip` (Generate's
  icon + colour `--gen`) + `reviewChip` (the overall rating, or *Not reviewed yet* when `reviewed` is false:
  `data._reviewed` = a rating saved after the newest render - outcome.json `"rated_ts"`, set by every aspects save;
  older files: the file's time); Rename (`renameModal`, pencil left of Delete, on hover; also *Rename…* on the page)
  = POST `/api/project/<p>/rename` {label} -> `data.rename_project` -> `build\project.json` `"label"` (empty = the
  folder's name again; a name another video shows is refused). The FOLDER is never renamed: the clips stay where
  they are (hard rule 1), plans / renders / Resolve find them by path, Claude's commands use the folder name. A
  video (#/project/<p>/<tab>): tabs **Overview** (`projOverview`: the newest render in a Player with a poster frame
  (`posterUrl`); under it one line (`pvmeta`): a picker when there are several (`renderPicker` = a dropdown *Selected
  version* since 2026-10-26 - the user: "it would help to have a dropdown of 'Selected version' instead of just a
  switch" - newest first, "v4 · newest · today 12:13", "v1 · Resolve", a name without `_vN` humanised: "graphics
  preview"; the same on Review and the Editor), version · by Claude / quick draft · length · fps ·
  format · rendered when, *Open in player*, *Made from …*; beside it **the index** (`drawIndex`, `.pvindex`, sticky:
  Ready to post's Title / Thumbnails / Description & chapters / After posting with their state, scrolling to
  `#pb-title` / `#pb-thumbs` / `#pb-desc` / `#pb-after`; then Review (rating or *not reviewed yet*), Graphics,
  Editor (*N versions by hand* = outcome.json `hand_fixes`, else *change it yourself*; 2026-10-26, the user: "add the
  'editor' tab in the sidebar of the overview as well"), Versions, Footage, Timing check, Resolve & library = their
  tabs - Review's icon violet, the Editor's cyan; redrawn by `reIndex` whenever Ready to post draws); then two big
  cards (`.pvnext .onx`, an icon circle, lift on hover - a neutral shadow) in their tabs' colours: *Change it
  yourself* (`.onx.ed`, cyan: opens the Editor tab; only with a plan) and *Improve it with Claude* (`.onx.fix`,
  violet: saves `next: "fix"`, goes to Review); under them a quiet link *Not the right feel at all? Start over with
  these clips* (`startOver`: `next: "start_over"` + New edit with these clips - never a v2 of a feel the user did not
  want). Until 2026-10-26 the cards were *Something not right? Review it and improve it* and *Start over* (the user:
  "I think the buttons ... are not really used? idk what to do with them" - the first only opened Review, the second is
  rare: the two ways to change a video took their place, Start over became the link);
  when the newest render is a **quick draft** (its plan `made_by` draft_edit.py) a third card on the whole row above
  them, glowing: *Happy with the cuts? Finish it with Claude* (`.onx.fin`, 2026-10-24, the user: "when i go to quick
  draft now, and the draft is done like what should i use next? improve with claude? ... it worked good and actually
  made some good cuts and transitions but then what? how do i tell him to go next step which is some motion graphis
  and stuff?") -> `finishModal(P, version)`: *Stays* (green chips: pacing & cuts, effects & transitions, sound &
  music) and *Claude adds* = four tiles `FINISH_ADD` (motion graphics, captions, sound effects, colour - what each is in
  its tooltip), pre-ticked from New edit's answers (`project()` `asked` = edit_request.json's captions / sfx amount /
  talking: graphics always, captions unless "none" or nothing asked on a video that is not talking, sound effects
  unless "none") or this version's last finish; a line in their words (optional); the button is off with nothing
  ticked and no words -> POST `.../outcome` {next: "finish", finish: {add, words, from}} (`data.save_outcome`:
  `FINISH_ADD` only, the words on one line, `from` = vN or null, `date`; nothing ticked and no words = refused) ->
  Claude `/recreate-video finish <p>` (task recreate; the skill's improve.md *Finish a quick draft*: every cut of the
  draft kept, only these layers added). Never fake ratings to ask for a layer (the ratings are rules for every video);
  `reviewSummary` = one line of the parts rated; *undo* clears `next`; then **Ready to post** = `projPublish` inside
  `#pubsec`, below) | **Review** (`projReview`, only with a render or ratings; since 2026-10-18 the one review pattern,
  **Reviews** in `tools\motionlab\app\CLAUDE.md` - `outcomePanel` / `wireOutcome` are gone; its colour = violet,
  Claude's (2026-10-26, the user: "add some colors to accentuate the review page since its identical to the overview
  tab so we have some distinctions between the three": `#tab[data-t=review]` sets `--acc` - the player, the panel's
  edge, Send, its links; the tabs `.ptabs` carry an icon each, Overview the section's colour, Review violet, the
  Editor cyan `--edc`): left = `renderPicker` + the Player, right = the review panel **How did it turn out?** = `ASPECTS` (sound & music, SFX, colour, captions,
  motion graphics, effects & transitions, pacing & cuts, title & thumbnail: optional; Overall first, the one required
  row; Good / OK / Bad + a note, saved per part = POST `.../outcome` {aspects: {k: {rating, note}}}); "These ratings
  were for an older render - rate this one." when `reviewed` is false; Send = `setNext('fix')` + `/recreate-video
  improve <p>` (a video made from zero: `/generate-video improve <p>`; since 0.5.3 its line names the parts rated OK / Bad -
  "It changes <parts> and keeps the rest." - a live `send.hint`); more = *Not the right feel at all? Start over*
  (or, after Start over, *New edit with these clips…* / *Improve this one instead*); the notes on moments (0.4.2, `momentNotes`) left the page on
  2026-10-15 ("for now u can remove") - saved ones stay in outcome.json `"moments"`, the route still takes them,
  Claude still reads them) | **Versions**
  (`projVersions`: the edit versions table, every render with its player, Delete, the side-by-sides) | **Footage**
  (`projFootage`, only with clips: the clips - `project()` `sources` + clips not prepared yet with `id` null - and the
  storyboards) | Graphics | Timing check / Resolve & library only when the video has a `verify_*.json` / a Resolve
  build, each tab starts with a line on what it is for. Old addresses: `/renders` = Versions, `/publish` = the
  Overview scrolled to Ready to post. Outcome.json (0.4.2, `data.save_outcome` keeps every key it does not own):
  `"next": "fix" | "start_over" | null`, `"moments": [{"f", "version", "aspect", "note", "date"}]` (f = that render's
  frame, 0-based at its fps; `data.clean_moment`; POST outcome `moment` / `remove_moment` = the note as listed);
  `project()` renders carry `version` (`_v2` -> "v2", else the name's rest), `mtime`, `fps` / `frames` / `width` /
  `height` (the plan's, else `player.codec` = ffprobe, cached). `/recreate-video improve` fixes exactly those moments.
- **New edit > 1. Clips, a friend's asks** (2026-10-24): *Add a folder…* (`[data-add=folder]`, `webkitdirectory`) and
  a dropped folder (`clipsFromDrop`: `webkitGetAsEntry`, `readEntries` until it returns nothing - at most 100 a call)
  take every clip inside, sub-folders too, sorted by path with numbers as numbers; `clipNames` puts the parent
  folder(s) in front of a name two files share ("19 octubre_C0001.MP4"); the toast says how many were found. `isJunk`
  (a dot name or folder, Thumbs.db, desktop.ini) keeps a Mac's / iPhone's "._" files out - the server refuses them too,
  and `project.clip_files` hides ones copied before (also by their AppleDouble header) and an old add-on's photo
  twin (`IMG_0950.jpg.mp4` beside `IMG_0950.jpg` - left on disk, not listed). Photos (`PHOTO_EXT`, `CLIP_ACCEPT`
  image/*): their own picture (GET `/api/thumb` makes one with Pillow + pillow-heif, the EXIF rotation applied), a
  yellow PHOTO badge, no length, a click opens it; the pill under it (`.nephs`) goes round 3 / 5 / 8 s = edit_request
  `photos` {name: {seconds}}. The same names in a batch already in the video keep `save_upload`'s rule (same size =
  kept, else " (2)"). The new video's name (`#cvname`) stays editable after its folder exists: Enter / leaving it =
  POST `.../rename` (the label; the folder keeps its name), "Name saved: …". *Film it* has the same folder button.
  Footage tab: a photo shows PHOTO + its size.
- **Editor** tab (0.6.0 step 6; the first part was the *Mini-editor*'s buttons, 2026-10-26 the same day the user:
  "instead of mini-editor call it just editor, change the color of the player and editor to maybe one with more accent
  colors so that we know its different from the player in review ... i mean like an actual editor where i can select
  clips, move them around, trim at my own liking, not just click buttons and do it all theoretically ... add sfx to
  my liking, maybe remove a design and add a template from our motion graphics template with the color of my liking,
  maybe add slow/speed to some clips ... look at open source alternative of capcut or premiere or sum and try to
  implement those in a minimilastic but efficient way"; `projEditor` + `EdPreview`, after Review, shown when the
  video has a render and a plan; `#/project/<p>/mini` = the old address). The open-source editors' way: OpenCut /
  CapCut's magnetic main track (the shots always close up), lanes above (captions, graphics - a row each where they
  overlap) and below (sound effects - up to 3 rows -, the voice / song's loudness), split at the playhead, snapping
  (🧲, to cuts, the playhead, the items), an Add panel; Shotcut / Kdenlive's light proxy copies. Its own colours
  (`.ed`: cyan `--ed1` = `--edc` for the main action, the selection and state; violet `--ed2` only as the graphics
  lane's colour; a pink playhead `--ed3`) - never Review's player. Re-checked 2026-10-26 (the user: "re evaluate the
  editor interface with the impecable or hicup github repos" - Impeccable's checker, offline from npx's cache with
  telemetry off, 53 findings -> the sidebar's 2 kept stripes; Hallmark's Floor + app-screen rules read, nothing
  installed): no gradient on Save, no coloured glows, no tracked capitals, text 11 px and up (captions 12), a focus
  ring on every control, the changes as a disclosure instead of a dialog; results in `.app\dev\impeccable_2026-10-26\`. Top: the render
  picker (*Selected version*), the format, Undo / Redo, *🕓 N changes ▾* (a list under the button - `histPop`, no
  dialog: the changes in order, Undo, *Start again*; an outside click or Esc closes it), *Save as a new version*.
  Middle: **Add** (`#edadd`: Sounds = this PC's recorded sounds + every kind's made-up one, ▶ to hear, + = at the
  playhead, or drag onto the timeline; Graphics = the Motion Graphics templates, "Over your video" first and the
  full-screen ones after on a video with shots - added over a video with its `background` off), the **live preview**
  (`EdPreview`: the clips from their light copies - two `<video>` per clip, the next shot waiting on its first frame,
  at their speed and zoom / anchor / opacity curves -, each graphic's own page in an iframe seeked to its frame (a
  new one from its template at the video's size; captions' unsaved words patched in after captions.js), solids, the
  sound effects through Web Audio at the build's offsets (the same recorded file the build picks), the song under it
  or the clips' own voice; a click on it = play / pause), the **selected item** (`#edinsp`: a shot = speed chips ¼×-4×,
  split at the playhead, delete, its clip's room, what moves with it; a graphic = its words, its colours with My
  Brand's swatches, *More settings* (the other settings, `gsetInput`), remove / remove all its pieces; a sound = listen,
  volume -12..+12 dB, its sound (the kind's recorded ones + made-up), remove; a caption = its words, the captions'
  colours, remove - since 2026-10-26 (the user: "why cant i modify captions? like move stuff or trim them?" and "what if i
  wanted to change the font or style of the caption?") the captions' whole style: their looks (presets.json - the op
  `look`), font / weight / size / capitals / position (`ED_CAP_STYLE`), colours, *More settings*). Bottom: the timeline (`#edcanvas`; `pxf` from fit to 14 px a frame, Ctrl + wheel / − + / the
  slider; the ruler and empty lanes move the playhead; shots show their clip's filmstrip). Pointer: drag a shot =
  reorder (an insertion bar), its edges = trim (clamped by its clip's room), a graphic = move / its edges = trim, a
  caption = move (`capmove`) / its edges = trim (`captrim` to a frame) - inside the shot its words are said in, a
  touching caption gives way down to `MIN_CAP` frames (the tooltip says when it can go no further), the words rescaled
  (`caption_retime`; the preview patches captions.js with the state's `capedits`), a sound = move; a click selects, an empty place deselects. Keys (never while typing): Space, ← → (Shift 10), Home /
  End, S split, Delete, Ctrl+Z / Ctrl+Shift+Z / Ctrl+Y, + / −, M, Esc. Every change = POST `.../miniedit/preview` with
  all of them (nothing saved; the timeline and the preview are drawn from the answer) and a label in the page's
  language; the changes are kept in this browser (localStorage `ml.editor.<p>.<plan>`) until saved or dropped - *Your
  unsaved changes are back*. The preview's media (GET state `media` / `need_media`): missing or out of date = the
  job `editor_media` starts by itself (`tools\miniedit.py media`: a light H.264 copy per clip, its sound's loudness
  per frame, a filmstrip picture - `build\editor\`; seconds), the preview plays the clips themselves meanwhile.
  Recorded sounds play through GET `/api/editor/sound?file=` (Edge never answered a script's fetch of an address
  ending in .wav, 2026-10-26 - six such fetches held all of the page's connections), made-up ones `?kind=`. *Save as
  a new version* = POST `.../miniedit` (the job `miniedit`), then `route()` so the page's progress panel follows it;
  while it runs the tab says *Saving your changes*; when it ends the new version is the newest render. A sound the
  Editor cannot cut again (`timing_locked`) locks the shots (no edges, speed or split) with one line why.
  The extras (2026-10-26, the user's pick before releasing 0.6.0 - "finish everything we have"): an **Effects** lane
  (`.edfx` chips from `motionlab\edfx.py`'s reading of the plan: zooms, punch-ins, shakes, flashes, stutters, the
  transitions; drag = `fxmove`, the right edge = length, the panel = strength / ease / remove; the Add panel's
  *Effects* tab = `fxadd`; 0.6.0.1, the user: "most of the time i cant even use them due to an error": a shot's zoom
  keys hold several moves, each its own chip (`edfx._zoom_runs`; a hold key in front from a trim is no Punch-in), a
  new zoom goes in beside the others (`_room` = the free frames nearest the playhead, earlier near a shot's end; what
  comes after is scaled, so moves stack; a shake's own zoom keys carry the tag `shake`), a drag stops at its edge
  (`_clamp`, never an error), `CLIP_ONLY` kinds are greyed out on a video of graphics and the stutter on a talking
  video (`ED_FX_CLIP`, the reason in the tooltip), a flash / black frame with no clip under it = a `flash_` /
  `black_` solid, and only effect solids are chips (`SOLID_FX` - a corner camera's box, an end card's `end_bg` are
  the layout); *See it rendered* (`#edrange`: the two seconds around the playhead with the changes so
  far, picture only, `render_video.py --range` as the job `editor_range`, played over the preview); the Add panel's
  **Clips** tab (first when the video has clips: the plan's `sources`, + = at the cut by the playhead, dragged = into
  the cut it is dropped on - `clipadd`); a shot's panel has *Clip* (`take`: another clip of the video in its place, its
  caption piece's words dropped), *Part of its clip* (`slip`, live in the preview; Alt + drag a shot does the same) and
  *Its sound* (`volume`, -30..+12 dB + *Mute* - a talking / clips' sound only); on a song video the song's wave is
  draggable (`song` start, dragged left = later in the song) and a click opens its panel (start, volume - against the
  sound effects, the master brings the whole back to -14 LUFS); captions can be split at the playhead (`capsplit`) and
  added (*+ Caption* in the toolbar, `capadd`, its words selected to type over), and a caption said over a cut shows
  its end on the next shot too (a dashed piece that selects it). A video made from zero has its **scenes** (the
  full-frame graphics back to back, `miniedit.scenes`) as the main track: the *Scenes* lane shows each one's
  picture, they move / trim / split / speed like shots, and a scene's panel has its graphic's words and colours. The
  clips no shot uses get their light copies quietly after (`need_more`, no wait on the preview).
- **Keyframes, transitions and the add rail** (2026-10-26, the user: "lets continue with the keyframe thing for the
  minieditor, improve the effect side, maybe add the posiblity of transitions between two clips? ... i kinda want to
  have that good video editing look so can we look for comparisons in capcut, opencut, premiere pro, davinci"; a
  research pass over those four + Kdenlive / Shotcut picked the patterns). A shot's panel has tabs **Video** (the
  keyframe rows, `keyRows` / `bindKeys`: Scale, Position X / Y, Rotation, Opacity, Zoom point X / Y - its value at the
  playhead, ◆ = a key here / remove it, ◀ ▶ = the keys before / after, ↺ = as it was, the name dragged left / right =
  the value live in the preview (`liveKey`), kept on release; auto-key: once a value has keys, a change at another
  moment is a key - `motionlab\edkeys`), **Speed** (speed, clip, part of its clip) and **Sound**. A click on a shot
  puts the playhead there when it is elsewhere (its keys need it). The selected shot's keys are diamonds on it
  (`.edkf`, merged by frame - on the clip, never only in a drawer: Resolve 20's backlash): drag = `kmove`, click = the
  keyframe's panel (what is keyed there, *The move after it*: Linear / Ease in / Ease out / Ease in and out / Hold /
  Pop - compose's `pop` overshoot, Remove). Transitions (`motionlab\edtrans`, the helper layers rebuilt on every
  change): a white block on the cut (`.edtr`; its edges = its length on both sides, hatched where frames hold still -
  Premiere's frozen frames, never Kdenlive's refusal), a + on every plain cut without one (`.edcutb`, on hover = Mix),
  the add rail's *Transitions* (+ = the cut nearest the playhead, or dropped on a cut), its panel = the 11 kinds,
  length, direction (Slide / Whip), *Apply to all cuts*, Remove. The add panel's tabs became a rail of big icons in
  their lanes' colours (`.edrail`; the user: "more presence ... instead of an overcrowded tab bar"); the side panels
  are 320 / 300 px. The preview: a clip's box moves and turns (`translate` + `rotate` on its wrap), the picture scales
  inside round the zoom point (under 100 % = smaller than its box, as compose draws it); up to four copies of a clip.
  *Why not here* (0.6.0.2, the user: "show why some effects or transitions cant be used in tha specific [moment] of the
  video so people know"): the state's `fx_can` = `edfx.availability` (every kind tried on a copy of each shot / each
  cut's two shots, ~5 ms - the engine's own reasons); the Effects list starts with where the playhead is (`.edat`:
  shot n · frame + timecode, following the playhead) and puts the reason under a kind that cannot go there (`.edwhy`,
  its + off, not draggable), redrawn when the shot / cut under the playhead changes (`ctxKey`); Transitions says the cut
  it goes on and what it replaces; a keyframe row a shake draws frame by frame is greyed with why.

## Generator vs Editor

- **Generator vs Editor** (round 2 of 0.4.3.5, the user: "why are videos generated in the Generator shown in the Editor?
  ... do not duplicate info like that"): `inGenerator(p)` = made_from kind generated and not `in_editor`
  (`build\project.json`, `data.move_project`, POST `/api/project/<p>/move` {editor}, API_LEVEL 22). Such a video shows
  only in the Generator's *Made from zero* (`projCard`), its page's crumb / sidebar / colour are the Generator's, its
  header has *Move to the Editor* instead of *New edit…*; once moved it shows only in the Editor, with *Back to the
  Generator* under its name. Home's Editor count leaves them out (`/api/status` `projects`).

## Generator

- **Generate** (0.4, the user: "a video from zero - mostly external tools like Higgsfield, InVideo... or a whole
  motion-graphics video with HyperFrames"): `pageGenerate` = two ways - *A motion-graphics video* (disabled with a
  pointer to Settings > Programs until Node.js + HyperFrames are found) and *With AI video tools* (*Generate a video
  with Claude and other tools*, was *Plan a video with Claude* until 0.4.3.5; *Just one prompt* = `aiPromptsModal`), the videos made from zero (projects without clips), the latest
  prompts. Both open `generateModal(kind)`: what it is about, the words on screen (graphics) or the tool (ai), up to
  3 of this PC's analysed videos (`stylePicker`, since 2026-10-18), length, format, a song (graphics: `refs\audio\`
  downloads), colours, its name ->
  POST `/api/generate/request` (`data.save_generate_request`: checked; makes `projects\<name>\` when new; saves
  `build\generate_request.json`; made_from kind `generated`) -> Claude `/generate-video request <name>` (task
  `generate`, effort xhigh). GET `/api/generate/options` = the tools, the downloaded songs, HyperFrames found.
  0.5.3 (E1: what Claude used to guess, asked - each optional, Claude picks by default): a **Look** row (`#glook`:
  Claude picks, the looks of `tools\overlays\motion\_looks` with their colours as dots, Surprise me -> the
  request's `look`; options `looks`) and *The song from last time* beside the song (options `last_song` =
  `sfx.last_song()`, only when it is a download); saving a request starts `tools\brief.py` in the background
  (`data.start_brief`: `build\brief.md`, what Claude reads first) - New edit's save does the same.

## Motion Graphics and Logos

- **Sounds** tab (0.6.0 steps 8-9; the user: "could it be possible for the user itself to choose them while editing or
  before running the edit"): #/motion/sounds, `motionSounds` = GET `/api/sounds` (`data.sounds_state`: this PC's
  library\sounds rows - the hidden ones too -, the shared list's packs with "n of m here", the kinds; a pack sound
  picked from a trial copy shows the pack's own file name). A row per sound by kind: ▶ (`/api/editor/sound?file=`),
  its length, origin (its licence in the tooltip), ☆ / ★ favourite and Hide / Show (POST `/api/sounds/set`); filters
  *In use* / *★ Favourites* / *Hidden*, a kind select, search (`SD_FILTER` / `SD_KIND` / `SD_Q`). The packs' cards:
  how to get each (`how`, translated by key), *Get it* = its page (empty for the user's own pack until they give its
  link: "Ask whoever shared MotionLab with you"). *Add sounds* (`soundsAddModal`): a folder (webkitdirectory) or
  files -> POST `/api/sounds/upload` one by one into `.app\sound_import\<batch>\`, or a typed folder path (read where
  it is - a GB bundle is never copied); where they are from + their licence (both or neither: empty = only the list's
  sounds); the job `sound_import` (followed in the dialog) -> the tab again. New edit's Sound step: *Choose the
  sounds* (`#nepick`, hidden at *None*): the sounds in use by kind with ▶ and a tick -> `st.sounds` -> the request's
  `sfx.sounds` (`editreq._sounds`: this PC's library only, at most 40); the summary says "n picked". **Make
  sounds** (`soundsMakeModal`, API 43; the user: "connect elevenlabs ... upload to google drive for everyone"): the
  key (a password field the first time, then "····abcd" + Change), Free / Paid (the licence), a stepper per kind of
  generate.json (the kinds with under 6 sounds start at their number, the rest 0; the free month capped at what is left of it -
  the balance ElevenLabs reports), the credits (about 10 a second asked); the job, then the *New* filter (added in the last 7 days). A made sound shows *ElevenLabs* (*non-commercial*
  on the free plan) and its description's first words as its name. *Share with friends* (paid-plan sounds only).
  Tests: a server started with `MOTIONLAB_SOUNDS` / `MOTIONLAB_ELEVENLABS_KEYS` / `ELEVENLABS_BASE` (a stand-in) -
  never the real library or key.
- **Music** (#/motion/music, `motionMusic`, 0.6.0 step 10, API 46; `motionlab\music.py`): two filter chips, *Songs*
  (refs\audio's downloads read in place + `library\music\`) and *Ambience* (`library\music\ambience\<kind>\`); a row
  each: ▶ / ❚❚ (`muHear` - one at a time; `muStop` on leaving the page and in `closeModal`; GET `/api/music/hear?rel=`
  - never a .wav address), title + artist (from the file name, yt-dlp's [id] off), chips BPM / energy / tone /
  length (`muChips`, also on New edit's cards; energy and tone words translated by key), where from (YouTube,
  ElevenLabs · non-commercial...), ★ (offered first) / Hide (never offered) = POST `/api/music/set` ->
  music.json. *Add songs* / *Add ambience* (+ its kind) = POST `/api/music/upload?name=&type=&kind=` (a raw body, a
  new name - never over a file), then the job `music_index` (`tools\music.py index`); *A song from a link* = the
  download job (MP3 preset) then the same; *Measure n new* when files are not measured yet; *Make ambience*
  (`musicMakeModal`: a stepper per bed kind, the credits, the month left; the job `music_beds`). New edit's Sound
  step: *A song* shows the songs as cards (`.nesong`: ▶ + the chips; the video's folder songs first; the select stays
  hidden as the value) and, unless a song is picked, *Ambience under your voice* (None + each bed with ▶) -> the
  request's `ambience` (`editreq._bed`).
- **Motion Graphics** (0.5.0, the user, 2026-10-16: "turn the Swishy reference clips (in the refs folder) I captured
  into a reusable Motion Graphics library, add a Motion Graphics section to the sidebar, and make Generate use those
  templates as well when generating blindly"): sidebar row after Generator (`data-nav="motion"`, icon `#i-motion`, coral
  `--motion`, its band texture = eased motion paths); `pageMotion(main, tab, open)` (#/motion, #/motion/learned,
  #/motion/templates/<id> opens one) = GET `/api/motion` (`data.motion()` = `motionlab.templates.catalog()` + each
  template's size, declared settings and picture + the clips it learned from with their files; worked out again only
  when a file it is made of changed (`_motion_sig`: directory listings of every template folder,
  `library\motion_graphics\` and the packs - no file opened), each call its own copy). Tabs **Templates**
  (`motionTemplates`: kind chips `MKIND` remembered in localStorage `ml.mkind`, `.mggrid` of `.mgc` portrait cards ->
  `motionModal(t)`: the live preview (`livePreview` with the form's values, starting from the declared defaults),
  *Try your words* (`gsetInput`), *Use in a video…* = `motionUseModal` (a project + a name -> job `overlay_new` with
  `values` = the changed settings, an overlay template (`template.json` `"overlay": true`) gets `background: false`;
  jobs.py passes `--like-plan --values <json>`) and *Make a video with it* = `generateModal('graphics', {templates:
  [id]})`; *Learned from* = the source clips playing muted) | **Learned from** (`motionClips`: kind + status chips
  (`MSTATUS`: rebuilt / next to rebuild = cards.json rebuild 1 / later / style only + still captures), `.mcgrid` of
  `.mcc` cards: the poster.jpg as a lazy `<img>`; the clip's `<video>` (refs\ via /files/) is made on the first hover
  and kept (a second hover goes on), never with reduced motion (2026-10-19: hundreds of clips no longer load every
  poster at once) ->
  `motionClipModal`: the clip, Claude's card (violet chip), *Measured by MotionLab* (the cyan chip), the sheet in the
  lightbox, the colours, *Rebuilt as*). The header's *Rebuild the next 8 with Claude* (while rebuild-1 clips are left)
  = `/generate-video templates <pack>` (task generate). **Generate** (graphics): step 3 *Motion templates*
  (`#gtpl`, only when the library has templates): GET `/api/motion/pick?want=&n=6` while the user types (debounced) -
  the suggested ones dashed (`.fchip.sug`), a click pins one (up to 12), *all N…* lists the library; the words under it
  say what Claude will do (pinned = used; none + no style video = it starts from the suggested ones); POST
  `/api/generate/request` `templates` (`data.save_generate_request` checks them against the library) ->
  generate_request.json `"templates"`. **MotionLab originals** (17 of the 74, from the user's ask to review template
  marketplaces for what is missing, 2026-10-16): `template.json` `learned_from: []` + `origin` (the need) - the card
  says "MotionLab original" instead of "learned from N clips", the dialog *A MotionLab original* instead of *Learned
  from*; their kinds have labels in `MKIND` too (transitions, lower_thirds, callouts, broadcast, promo). `data.library()` leaves the motion templates out of Claude's memory > saved
  graphics (they have their own page; since 2026-10-19 it does not work them out at all: `OS.library()`'s loop over
  yours + the examples; `library(videos=False)` = the counts for Home and Claude's memory). `/files/tools/overlays/motion/<id>/<file>` serves a template's .html / .json /
  .js / .css / .png / .jpg / .svg and maps `gsap.min.js` to the pinned GSAP (node_modules) - the live preview's `<base>`.
  **Logos** (2026-10-16, the user: "the motion graphics section lacked svgs or icons" - the logo library, root
  `logos\`, `motionlab\logos.py`): tab *Logos* (#/motion/logos, `motionLogos`) = GET `/api/logos` (`logos.catalog()`
  without the SVGs; loaded once, `LOGOS` / `logoLoad`): search + group chips (`LOGO_GROUPS`), `.lgc` cards (a light or
  dark plate `.lgimg.dk` by the default version's `on`), + picks up to 12 (`LG_PICKED`, this visit) -> *Make a logo
  wall with them* = `motionModal(logo-wall, M, {logos, title: ''})` (motionModal's `init` = starting values), *Copy as
  :logos:*; a card = `logoModal` (every version on light and dark, the value to type, Copy). The settings form
  (`gsetInput`, everywhere it is used): a logo setting (`isLogoSet`: string, id logo / logos / *_logo / *_logos) = text
  + *Pick a logo…* (`data-logopick` one / many), a text whose label shows `:name:` (`logoText`) = text + *+ Logo*
  (`data-logohow` list / first / swap read from the label; the caret kept in `data-caret`) -> `logoPicker` = an inline
  `.lgpop` under the field (a full-width row of `.gset`, `contain: inline-size`; never a dialog - the template dialog
  keeps its values): search, the version (`LOGO_STYLES`: auto / colours / one colour / wordmark), groups; a pick sets
  the value and fires input + change (the live preview follows). `livePreview` adds `<script src="/logos.js?b=<ids>">`
  (`logoIds(values)`; GET `/logos.js` = `logos.js(ids)` = MLLogo + those logos); `/files/.../assets/logos/logos.js`
  not written yet (a template folder, a graphic never rendered) = the helper alone; `/files/logos/` = the SVGs.
  My Brand's logo (2026-10-26) = the logo `brand`, first in GET `/api/logos` (group `brand` = the *My Brand* chip; its
  versions' pictures as `src`, `logoSrc` shows them) - `logos.brand_entry`; `LOGOS` (the page's cache) is reset when
  My Brand saves or takes a logo.

## Prepare and Film it

- **Prepare** (the user, 2026-10-14: "prepare a video (transcript oriented): improve a script you have - rewrite it
  with more potential to go viral - or generate one from zero from a few questions; hooks, structure"):
  `pagePrepare` = three ways (*Improve my script* = `scriptImproveModal`, *Write one from zero* = `scriptNewModal`,
  0.4.3 *Title & thumbnail first* = `titleFirstModal`, below - since 0.4.3.5 round 3 the slim row *Only need a
  title or thumbnail?*),
  *Waiting for Claude* (requests with nothing written from them yet: *Open in Claude Code again*, ✕ = POST
  `/api/script/forget`, the request file to the Recycle Bin, logged), *Your scripts and hooks* (prompt cards ->
  `promptModal`). Scripts live in the prompt library (kind script / hook); the requests in
  `knowledge\local\prompts\requests\req-NNN.json` (`motionlab\script.py`). Improve: paste / attach (.txt .md .docx via
  `/api/prompts/file`), where it goes, length, a wish, *In the style of* (`stylePicker`, since 2026-10-18: up to 3 of
  this PC's analysed videos + the user's own scripts / hooks = `like_prompts`) -> POST `/api/script/improve` (the
  script saved as the user's own + an `improve` request) -> Claude `/write-script improve <id>` (task `script`, effort
  high). From zero: topic (required), viewer, takeaway, angle, must-say points, where, length, tone, the ask at the
  end, language, style, anything else -> POST `/api/script/request` -> `/write-script request <req>`; Claude saves
  the script with `"request": "<req>"`. **The script check** (`script.check`, POST `/api/script/check`, no Claude):
  live in the Improve dialog (`scriptCheckHtml`, debounced) and on every script / hook pop-up (*The check*); the
  speaking rate is measured on the picked videos (`style.build(...)["talk"]`) when they have talking. A script / hook
  card's *Optimize* / *Check it again* go to `/write-script` (`optCmd`, `chkCmd`), other prompts to `/write-prompt`.
  0.4.3.5: *How Claude writes for reach* left ("not that important for the person to see"); every prompt card says
  when (`.pgwhen` = `whenStr` of `updated` / `added`), a script card shows every step it reached (`pstage`). Round 2
  (the user: a title set and a talking script "appear to have different UIs ... I want it to be known before
  clicking"): `pagePrepare` (round 3, the user: "keep the old structure of 2 big buttons for scripts ... don't mess
  up the structure and workflow") = the two big ways (*Improve my script*, *Write one from zero*), a slim `.tfrow`
  **Only need a title or thumbnail?** ("If you already have a video ready and are still missing a powerful title or
  thumbnail, create it with Claude", button *Create it with Claude*) -> `titleForVideoModal`: the videos with a render, newest first -> that video's
  Ready to post + Claude `/write-title package <p>`; *Answer a few questions instead* (or no rendered video) =
  `titleFirstModal`; then *Waiting for Claude*; then `.preplist` in two halves: **Talking scripts** (a microphone icon) (green,
  `scriptCard` = kind label, title, the first spoken line (`spokenLines`: no headings, no [notes]), ≈ length at 150
  words a minute, `pstage` or "not filmed yet", ▶ *Film it* = `filmItModal`, no hint line; faded `.spc-done` once a video made from
  it has a render - still clickable, to film it again; a hook = pink, no Film it) | **Titles
  & thumbnails** (blue, `titleCard` = the chosen or first title, the concepts' words as three 16:9 tiles, counts,
  "for <video>"); no hint line. Both cards: Rename (`renamePromptModal` -> POST `/api/prompts/rename` {id, title} =
  `prompts.update(title=)`, the text stays) + Delete (`delPromptModal`, Recycle Bin) on hover (`.pcact`, in the date's
  place).
  **Film it** (2026-10-15, the user: "I record a video of me reading the script but I don't know where to go... it's
  not a prompt, it's a talking script... and then where does it go?"): a script card's run button (`RUN.script`, the
  run step says *Film it*) = `filmItModal(p)`: the road on a line (`flowSteps(uses, false)`, since 2026-10-22 the
  same numbered steps as the script's pop-up - 1 The script, 2 Film it, 3 Edit it, 4 Post it, done = ✓, the next one
  lit = `scriptRoad` from GET `/api/prompts` `used`: per video `clips`, `renders`, `posted` = outcome packaging link;
  the card's `pstage` chip), 1 Film it = cue cards (GET `/api/script/cards?id=` = `script.cue_cards`: parts with heading, lines,
  notes; `[check]` kept in a line, a lone one = `check`), *Teleprompter* (`teleprompter(lines)`: full screen,
  `wpm` 150, Space / click, arrows, Esc only closes it; [check] left out), *Copy the lines*, *Film these too*
  (B-ROLL / VISUAL / SHOT notes), *The edit adds these*, tips; 2 Add your recording = a video (linked ones first) or
  a new one named after the script (`folderName`), drop / choose -> `uploadClip` with `prompt`; 3 Edit it = ONE big
  card in the Editor's gold, **Continue in the Editor** (`.ficont`, 2026-10-24, the user: "we spent a lot of time
  going through changes and improving the edit page and now in the film it page u do the same thing (add clips... a
  little of style) but dont get no benefits from the edit section ... keep the teleprompter and other stuff but the
  step 3 make it "continue in editor" and it pop ups the new edit section but loading the prompt and videos i loaded
  in the film it section") = `newEdit({project, from: 'prompt', pick: <script>})`: New edit opens on 1 Clips with
  that video's clips, 2 Text has the script picked, 5 Sound = Talking; its Back = Film it again (then where Film it
  came from). Chips on the card = what goes along (the video · its clips, the script); disabled until the picked
  video has a clip (`#fimsg` says why). The format / length pills and Film it's own *Make it with Claude* / *Quick
  draft now* left with it (2026-10-22's "make it with claude left, quick draft right" is gone): the edit is the
  Editor's only. The script pop-up's road step *Edit it* = the same `newEdit` with the first video from this script
  that has clips. A video made from a script: *Made from the script <title>*
  (`project()` adds `title` / `prompt_kind` to made_from), and with no edit yet the Overview says *Filmed - now edit
  it* (New edit with the script picked).
- **Improve my script keeps one card** (2026-10-24, a friend's ask: "only the improved script should remain"): the
  request is saved with `replace` (`script.save_improve`); while it waits, the pasted script is not a card of its own
  (`improving` in `pagePrepare`) and *Waiting for Claude* says "improving…"; once Claude saved the new version
  (`made_from` = the paste, `request` = the req) POST `/api/script/tidy` (Prepare and the prompt library call it before
  they load) runs `data.tidy_improved`: the paste - and a copy of the same words Claude saved after it - goes to the
  Recycle Bin, never one a video was made from or another request's paste; the request is marked
  `tidied` once. The improved card carries NEW. The skill (`write-script` section 3 step 5) saves only the improved
  script and never imports the user's again. *Optimize with Claude* on an existing card is not a `replace` request:
  both stay.

## Title & thumbnail, Ready to post

- **Title & thumbnail** (0.4.3; the user: the thumbnail and the title together decide the CTR, "horizontal and
  vertical"): **Prepare > Title & thumbnail first** (`titleFirstModal`: topic (required), viewer, angle, platforms =
  check boxes (`script.PLATFORMS`), the thumbnail's orientation derived from them (`TF_ORIENT`) until the user clicks
  one, language, *In the style of* (`stylePicker`, since 2026-10-18: up to 3 of this PC's analysed videos + the user's
  own scripts / hooks = `like_prompts`), notes -> POST `/api/title/request` = `script.save_title` -> `req-NNN.json`
  `"kind": "title"` -> Claude `/write-title request <req>` (task `title`, effort high)); *Waiting for Claude* lists
  title requests too. Title records (prompt library kind `title`, `KSHORT.title`, blue `k-title`) sit with the scripts
  and hooks; their pop-up is `titleModal` (not the prompt steps): the titles (pattern, characters - `tchars`, amber
  over `TITLE_PHONE` 60), the thumbnail ideas (words, picture, shot to film, colours), the hook, Copy each / *Copy
  all*, *Use a title for a video* / *Use this title* = `useTitleModal` (a video + the final title -> POST
  `/api/prompts/title` = `prompts.update(project=, chosen=)`; *Unlink*), *Write the script* (`scriptNewModal` with the
  title + hook), Claude's check read-only; since 2026-10-18 the review panel beside them (**Reviews** in
  `tools\motionlab\app\CLAUDE.md`: *Is Claude right?* on Claude's check + *How did it do?* = the rating; Send = the old
  *Write new ones with Claude* command). **Edit > a video > Ready to
  post** (`projPublish`; 0.4.3's Publish tab, since 2026-10-15 at the end of the Overview under the render, "Happy with
  it? Ready to post"; the Title, the Thumbnails and *Make a thumbnail yourself* (folded once thumbnails exist) are one
  glowing box `.pbpack` of `.pbpart`s (the user: "all in one so the person isn't thrown around"); no *Open the folder*;
  then Description `#pb-desc`, `packagingBox` *After posting* `#pb-after` last; 0.5.4: first, in both states,
  `postBox` *To post on TikTok or Instagram* when `publish_info` `post` = the newest render's copy without its
  downloaded song (`publish.post_copy`: the song, where it starts, *Open the song*, *Show in folder*); returns the
  publish info for the index):
  GET `/api/project/<p>/publish` = `data.publish_info` (package.json as the
  tools wrote it + each thumbnail's settings `OS.status(thumbs\<id>)`, the title records linked to the video, the
  edit's fps / frames, the designs `thumbnail.templates()` - imported only here (numpy) - the face finder, the newest
  render, the brought pictures). Empty = one centred *Make the package with Claude* (`/write-title package <p>`, task
  title) + *or do it yourself*. Else: **Title** (the chosen one + characters + Copy; the package's titles + the linked
  records' to choose from; type your own) -> POST `.../publish` = `data.save_publish` = `publish.write` (left out =
  kept; a FAIL writes nothing and the page lists the checks); **Thumbnails** A / B / C (16:9, the 9:16 cover, the
  apps' crops - a click = the lightbox; the check per size: WARN / FAIL lines open, the rule in words (`CHECK_WORDS`)
  + its number, all rules folded, SKIP = "not measured"; *Change it…* = the graphic's settings form (`gsetInput`) ->
  POST `.../thumb` (`OS.set_values`) then job thumb_render; *Render again*; *Check them*); **Make a thumbnail
  yourself** (1 *Find good moments* = job thumb_candidates - the clips or the finished video -, tiles with clip +
  frame + timecode; or *Use a picture you made…* = POST `.../publish/image` -> `build\publish\images\` + a link to
  Prompts > Image (`aiPromptsModal('image')`); 2 the 2-4 words (the linked records' ideas as chips), the design,
  A / B / C; *Make* = job thumb_make; `PUBST` keeps the choices within a session); **Description** (the user's words,
  chapters = YouTube time + frame + timecode, frame and name editable, *suggest from the edit / what is said* = GET
  `.../chapters?from=plan|transcript` = `publish.chapter_points`, its errors in plain words; hashtags; Copy
  description / hashtags). Jobs (`jobs._thumb_job`, group cpu, queued): thumb_candidates (`thumbnail.py candidates <p>
  [--render]`), thumb_make (`make <p> --id X --words .. --template .. --frame f --clip c | --image <file>`, HyperFrames
  stills + its check, ~15 s), thumb_render, thumb_check (`jobtools.py thumb-check <p> [--title]` = thumbnail.py's
  `check_project`, exit 0 when a rule FAILs: a result, not a failed job); the page's progress panel follows them
  (`THUMB_JOBS`) and redraws when one ends. **How did it turn out?** has the part `packaging` (Title & thumbnail);
  *After posting* (`packagingBox` + `wirePackaging`, the end of Ready to post: CTR % per thumbnail A / B / C + the video's link -> outcome.json `"packaging":
  {"ctr": {"A": 4.1}, "link", "updated"}`, `data.clean_packaging`: 0-100, "4,1" accepted, empty = removed; the
  winner named). The link is only kept: `content.py stats` writes into `analysis\<name>\`, so a project's public
  numbers need a change there first. `data.save_outcome` keeps every key it does not own.

## Prompts

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
    picked, a hook = *Use current version in a video*; shot / image = copy for the site; a script has none - its road
    below carries Film it), *Copy Prompt* (clipboard icon)); `PSTEPS` + `pstate()` (check / want / opt / run / rate,
    the current one lit, a Next box with its button - not for a script / hook since 0.4.3.5, the user: "the steps are
    a little ambiguous so just remove them": a hook lists the videos made from it (`talkVideos`, each a link to its
    page with its tags ✓ Filmed / ✓ Edited / ✓ Posted, `VSTAGE`); round 2: no numbered strip for any kind - the
    other kinds keep only the Next box (`pstate().now`)). **A script's road** (2026-10-22, the user: "id like for
    the "film it" to also show like a clear next step in the whole process"): `scriptFlow` = `flowSteps(uses, true)`
    - 1 The script, 2 Film it, 3 Edit it, 4 Post it as numbered circles on a line (done = ✓ in the kind's colour,
    the next one ringed with NEXT), each a button (Film it = `filmItModal(p)`, Edit it = `newEdit` with the filmed video + the script, Post it
    = the video's Ready to post; later steps disabled) and the next step's own big button at the end (*✓ All done*
    when posted); the videos made from it under it.
    **Three tabs** (2026-10-22, the user: "remove the "Notes description when seeing the script..." i like that its
    only text but maybe add some structure to know what to film before going into the script? like assets or the
    general rhythm of the video ... when i go into the "your review" page i cant see all the text thats being
    highlighted or the section itself... make the The check and claudes check into a separte section or tab that its
    called "checks" ... we clutter the interface/ui with lots of information when we just want to go straight to the
    point"; `.pmtabs`, `data-pmtab` / `data-pmpane`; reopened for the same prompt it keeps its tab (`ctx.pmtab`), a
    text set opens on Checks): **Script** / **Prompt** = the whole text, never clamped (*Show all* is gone); a script:
    no notes, its rhythm above (`filmPlan` from GET `/api/script/cards`: each part a bar as wide as its seconds - the
    heading's "(3-7 s)", else its words at 150 a minute - coloured by kind: hook amber, CTA pink, payoff green, the
    rest blue / violet / cyan) and *Shots to film* (B-ROLL / VISUAL / SHOT notes, `FILM_TAG`) + *Text on screen*
    (TEXT notes) beside it in their part's colour; another kind keeps *How to use*. **Checks** (the tab's badge = the
    parts that need work, ✓ when none) = the one review pattern (**Reviews** in `tools\motionlab\app\CLAUDE.md`;
    since 2026-10-18 - the `.rb` rating buttons and the wishes saved "on change" are gone): left = *The check*
    (scripts: `scriptCheckChips` - the score, a chip per rule with what it found in its tooltip, a line only for the
    rules that did not pass) + **Claude's check** `pcheckHead`, read-only (unchecked: what Claude checks + the kind's
    parts; Send = *Optimize* = `/write-prompt optimize <id>`, which checks it first; checked: stars, ✓ clear / ~ vague
    / ✗ missing counts, Claude's verdict + *Most important*, `skipped` parts under *Not part of this prompt*) and the
    text again (`#pm-ctext`) with the part under review marked from its `at` (moving to a part scrolls its words into
    view; the pointer on a row marks it too) - no list of part cards since 2026-10-22: each part's tip
    (`pcheckTip`: the tip; the quote itself + "not verified - check it again" when it has no `at`; *Not in your
    script* for a missing part) is on its review row (`extra.item`, under the part's name); right = the review panel
    alone: *Is Claude right?* (a row per part in `pCheckOrder` - a brief's in `BRIEF_GROUPS` order, plain words
    `SLOT_LABEL` -, *Needs work / All parts* = its filter; the note = *what you want*, both saved by POST
    `/api/prompts/wishes` {id, wishes, verdicts}) and *How did it turn out?* (`#pm-rate`: Good / OK / Bad + a note,
    POST `/api/prompts/rate`, "Used in"); Send = *Optimize* (a new prompt with `made_from`, "optimized by Claude"),
    more = *Check it again* = `/write-prompt analyse <id>`; the Next box's *Show the parts* / *Rate it* switch to it.
    **Details**: a script's *Claude's notes* folded (structure, other hooks, delivery - off the Script tab), then
    **What it makes** (pictures / clips of the result, explained in the section: *+ Add picture /
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

## Claude's memory

- **Claude's memory** (0.4, the user: "once analysed it is stored in the mind of Claude, so editing or generating can
  use those effects and that knowledge"): `pageMemory(main, tab)`, tabs `MEM_TABS` = **Overview** (tiles: videos
  analysed -> the Analyser, lessons, prompts, a full-width *Shared knowledge* tile; **Your ratings -> rules for every
  new video** (`memRules`, `knowledge.ratings()`: bad = a rule for every new video, OK with a note, then one line each
  for fine / keep doing it; highlighted - 📌, an amber edge, *Claude reads these first*); *How Claude uses it* +
  *What Claude reads (memory.md)* / *Rebuild it* = POST `/api/knowledge/summary`), **Lessons** (two columns, *Analysing
  videos* (L###) and *Making videos* (`lessons.making`, M###); this PC's, shared - a rule whose note says "from
  <author> <id>" has the chip (`lessonItem`, `x.from` = `knowledge.rule_author`) -, friends' lessons waiting grouped by
  who and when (no file names) + *Review them in Claude Code*), **Shared knowledge** (`memShared`, the next section).
  **Removed 2026-10-22** (the user: "1) Graphics and saved effects 2) Effects 3) Videos - I dont understand what those
  sections do, I have never used and when i go inside is just a bunch of text AI-written and for AI so i acctualy dont
  care so u can just remove those sections"): the Videos tab (every analysed video's style card), the Effects tab
  (every effect type, its verdicts and how it was made), *Graphics & saved effects* (`memSaved`: the HTML graphics
  library with *Use in a video…* and the Resolve effects saved / picked for saving), and the Overview's parts that
  showed or linked to them (the search, the effect / breakdown / saved tiles, *Effects seen most*, *Latest videos*).
  Claude still reads all of it in memory.md; the saved graphics and effects stay in `library\` (Claude uses them;
  `overlay.py`, `library.py`); old addresses (#/memory/videos, /effects, /saved) open the Overview. GET `/api/memory` =
  `data.memory()` = `knowledge.memory()` (cached on the cards' and lessons' mtimes; friends' cards too) + saved counts +
  prompts; it rewrites `knowledge\local\memory.md` (`knowledge.memory_index()`, also rebuilt with the summary) when a
  card is newer - the file the skills read. 0.4.2: also when an `outcome.json` (`KN._outcomes()`), a lessons file of
  either kind or a `verdicts.json` (the sound answer: memory.md says "sound effects: many - ... (the user's answer)" per
  video) is newer. 2026-10-19: also when a set of scripts & prompts changed (`analysis\texts\*\*.json`) - memory.md
  ends with *Scripts & prompts you analysed* (`textsets.memory_lines()`: each set's label, kinds, k of N checked, the
  patterns the user marked correct / partly with their note; never shared); `memory_index(styles=True)` = the same
  without the effects block, never written (`knowledge.py memory --styles`, MCP `knowledge("memory:styles")` -
  /write-script, /write-title).

## My Brand

- **0.6.0, step 1** (built 2026-10-25; the user, 2026-10-22: "implement a new section ... which would be called 'My
  Brand'"; 2026-10-25: "my brand is different from content agency right?" - My Brand is one section of 0.6.0, the
  content agency): `#/brand`, `pageBrand`, the sidebar row right under Home, between two lines (`.navsep`) - its own
  place (the user, the same evening: "put the my brand above the make a video text, kinda like its own section ... i
  think its very important", then "remove the 'make a video' text and just add a line and a line above the my brand
  as well so have it separate from home" - the *Make a video* group label is gone; under Claude's memory before, as
  the mock-up, slide 10 of `new_edit_section.html`) with a NEW chip
  until the first visit (`ml.brandSeen` in localStorage, `#brandnew`). The section colour is rose (`--pink`), its icon
  a shop, its texture price tags. With a logo, the logo shows large and faint in the band's glass, on its right, behind
  the words (`brandBand(main, b)` adds `.brbg`, last in `.head`; 16 %, fading to the left) - the shop icon stays
  (2026-10-25: first the logo replaced the icon on the sidebar row and the band tile, then the user: "what if u put
  the logo in teh transparent background in the My brand page instead of replacing the shop icon itself?").
- **For my brand** (the user: "add an option when u generate or edit a video or create in general that is called
  'its for my brand' and then gets the knowdledge and tailors the video to your brand, using icons colors url"): one
  switch, `brandToggle` (a `<div class="brandrow">` in a dialog - `modal()` draws it; under its name a small preview
  of what it gives Claude - the logo, colour dots, the website, the goal, "N products", the voice - from
  `brandData()`, My Brand read once and again after a save), in New edit's header on every step (`#nebrand`), the
  Generator (`#gbrand`) and Prepare's *Improve my script*, *Write
  one from zero* and *Title & thumbnail first* (`#sbrand`, `#qbrand`, `#tbrand`); `brandOn(el, sel)` = ticked. Greyed
  out while My Brand is empty (`brandFilled(b)`); the last choice remembered
  (`ml.forBrand`). Ticked, the request gets `"brand"` = `brand.snapshot()` (My Brand now, only the products switched
  on) and the brief a *For my brand* section (`brand.brief_lines`: the facts, then what to do) - edit_brief.md first,
  the Generator's brief.md (`tools\brief.py`), `script.py show` for Prepare's requests; the skills follow it.
- **Three tabs** (2026-10-25, the user: "create some tabs for the my brand page ... i dont want to be scrolling", then
  "a tab called Style that can have the brand identity, tone of voice and captions stuff" and "in the overview ... the
  website, goal, target, pages... (with some videos previewing maybe)"): `BRAND_TABS` - **Overview** (`#/brand`: *Your
  website* with the big *Import from your website* button, *Goal*, *Target audience*, *Your pages*), **Style**
  (`#/brand/style`: *Brand identity*, *Tone of voice*, *Captions*, and *Your editing look* as a strip of video cards
  across the page - moved from the Overview the same night, the user: "move your editing look to style as well"),
  **Catalogue** (`#/brand/catalogue`, its count on the tab; the user, the same night: "the 'add a product' in the
  catalogue should be at the top for convinience and make the catalogeu section more cool, like why does it say
  'cataloge' if im already on a tab called 'catalogue'" - no title of its own: a bar on top (*Add a product*, the new one
  first and focused; "n products · m in videos"; a search past 8), the products as cards `.brpc` - the picture (a click
  picks one: POST `/api/brand/product_image` = `brand.save_product_image`, checked like the logo, `products\<id>.<ext>`),
  name, what it is, its link, the price, an *In videos* switch (off = greyed); empty = one centred line that points to
  the import). Every pane is drawn once and a tab only shows
  its own (`showTab`) - the address follows by `history.replaceState` (no hashchange, no redraw), so a change typed a
  moment before switching is never lost. A banner above the panes (`#brpend`) holds an import nobody took yet. The
  cards below are described by what they hold; where each sits = the tabs above.
- **The page** (the mock-up's look): the band, then two columns of `.brcard` panels - *Goal on social media* (four
  pills, `BRAND_GOALS` = `brand.GOALS`, any number, + the user's words), *Target audience* (chips, + one typed in -
  Enter or leaving the field adds it, up to 12), *Brand identity* top to bottom (2026-10-25, the user: "expand on the
  brand identity section from up to down instead of table with columns? i want to also be able to put colors as
  hexadecimal"): *Logo* - a tile, a click picks a PNG / JPG / WebP / SVG, POST `/api/brand/logo` = `brand.save_logo`:
  checked by its first bytes, an SVG without scripts, <= 5 MB, copied to `knowledge\local\brand\logo.<ext>`; beside
  it (2026-10-26, 3f) three smaller tiles - *On dark*, *On light*, *Icon only* (`BRAND_LOGOS`; the same route with
  `kind` -> `logo_<kind>.<ext>`, × = not used, the file stays) - and *Where your logo goes in videos* (four pills,
  `BRAND_LOGO_WHERE`: Auto / End card / End card + corner / Nowhere); under the colours *Does it read?*
  (`paintRead`: a tile per text / accent colour on each background colour, its contrast, ⚠ under 4.5 for text, 3 for
  an accent - `brandContrast` = `brand.contrast`). The brand also shows as New edit's *My Brand* palette card
  (`brandPalette`, the accent first) and as the first group of every font list (`fontOptions`). *Your end card*
  (5c, under *Names and words*): Auto + the three templates as picture tiles (`BRAND_ENDS`, their thumb.png), the
  sign-off line, and once one is picked a `livePreview` of it with the server's `_end` values (GET / POST
  `/api/brand` and `/api/brand/logo` add `_end` = `brand.end_card(b, preview=True)`; `endSaved` repaints after a
  save; drawn when the Style tab shows - `endPending`); *Its sound* (0.6.0 step 10, `paintSound`): the template's
  own sounds or *Your sound logo* (▶ = GET `/api/brand/sound_logo`), the description (GET `/api/brand`
  `_sound_words` = `brand.sound_logo_words`) + *Make one* (POST `/api/brand/sound_logo/make` -> the job
  `brand_sound_logo`, then GET `/api/brand` again) or *Use a file…* (POST `/api/brand/sound_logo?name=`, a raw body).
  *What worked for you* (3j, at the bottom of *Tone of voice*):
  the hooks, endings and titles of what the user rated good (GET `/api/brand` `_worked` = `brand.worked()`), read
  only, each a link to its prompt; none yet = one line on where to rate. The Captions card also has *Words per line*
  (1 2 3 4 6 - the preview shows that many at a time) and *Size* (Small / Medium / Large / Huge = `CAP_SIZE` x the
  look's own); a product card's *Facts & media* (5b, `prodFacts`, a dialog with *← Back* to the catalogue): key
  benefit, claims + their proof (5), never claim (chips, 6), screenshots / recordings (6 tiles, a video plays on
  hover; POST `/api/brand/product_media`); the card's button counts them; *Colours*
  - up to 6 rows (`.brcol1`): the swatch (a click = the colour picker), the hex typed (`.brhex`: #2eaa5c or #2a5 ->
  #22aa55; not a hex = red `.bad`, nothing saved), the name), *Tone of voice* - its own card (the user: "needs to have
  more presence as well because i didnt even realize its there"): quick words (`BRAND_TONES`, a click adds / takes the
  word out of the text) + the text (`#brvoice`, 300 characters). The identity also holds the brand's *Name* and what it
  does (`#brname`, `#brabout`) at its top and *Fonts* at its bottom (titles / body text = selects of GET `/api/fonts`,
  a line in each font beside it). | *Your website* (the address + **Import from your website**, below), *Your pages*
  (a row a platform: its logo on a white tile, the link - checked as typed by `BRAND_PAGE_RX` = `siteread.SOCIAL`, saved
  only once it is that platform's page -, a call to action; *Add a page* = the platforms' logos not used yet) and
  *Catalogue* (a row a
  product: a box tile, its name and what it is as borderless fields, the price, a gold *Use in videos* switch, × that
  shows on hover; *Add a product*; the line "Claude can put the product, its price and the website in a motion
  graphic").
- **Import from your website** (step 2, 2026-10-25, the user: "an option besides the 'your website' with a download
  icon that 'imports data from your website' so if its a shop website it will pull the catalog data, descriptions,
  logos"; then "before importing make a pop up with all the info gotten and how it would be imported ... checking if
  that info is already in the my brand section to not add duplicates"): `#brimp` saves the address, starts the job
  `brand_import` (group net, `tools\brand.py import` = `motionlab\siteread.py`: the site's own pages only, robots.txt
  obeyed, at most 8 pages; Shopify `/products.json`, WooCommerce's Store API, JSON-LD / og product prices; colours,
  fonts, logos, pages, name, description) and follows it (the status line under the address); when it ends
  `brImportModal(found, B)` (GET `/api/brand/import` = `found.json`) shows a section per kind with where it goes
  (→ Brand identity / Your pages / Catalogue): name + description, the logo pictures (one radio, *None*), colours
  (up to the 6 that fit; since the same night, the user: "how are colours taken from the website import? cuz i think
  they are missing the good ones ... maybe take a screenshot and analize the major colors" - the job screenshots the
  home page with headless Edge (`siteread.screenshot`), groups its colours (k-means in Lab, `groups`) and picks a
  palette with roles (`pick_palette`: the background = the biggest, the text = the most contrast - else the CSS' most
  used neutral that reads on it -, up to 3 accents where colour beats size, neutrals >= 1 % of the page, the logo's
  own; a page colour takes the CSS' exact value when near); the pop-up shows the screenshot beside them, each with its
  role and share of the page, the background / text / accents ticked; brand.json keeps the role, Style's colour rows
  show it as a select, the briefs say what each is for; no Edge = the CSS' most used colours as before), fonts (the
  library's and the free Google fonts the job downloaded - shown in their own type
  through an @font-face of the import folder, tagged "comes into your fonts" - as Titles / Body text radios, a second
  click lets one go; a Google font picked = copied to `library\fonts\<dir>` by `brand._add_font`, `/fonts.css`
  reloaded; any other font "not a free Google font - it may need a licence"), pages, products as cards (picture, name, price, description; *All / none*, "n of m
  ticked"). What My Brand already holds (same name / colour / product name / page) is marked *already in My Brand* and
  cannot be ticked; what would replace the user's own (their logo, name, fonts, a page's link) starts unticked. *Add n
  things to My Brand* = POST `/api/brand/import` {picks} = `brand.take_import` (copies the ticked logo to `logo.<ext>`,
  a product's picture to `knowledge\local\brand\products\<id>.<ext>`, sets `site.read`). Tested on a made-up shop of
  10 products (one already there) and live on the user's site (2026-10-25).
  **In the background** (the same night, the user: "make the import from your website button a littel bit bigger ...
  add a progress bar and make it so that if the job finishes while u are in another page u can still come back and
  import the info"): the button is a full-width primary one (`.brimpbig`); the reader prints `progress <0-100>
  <stage>` lines (`siteread.Reader.progress`: home, pages, styles, shop, fonts, logos, pictures, done) and
  `brandImpWatch(id)` follows the job from ANY page (`BRAND_IMP`; the bar `#brprog` + the stage in words under it when
  My Brand is open); the app's start picks up an import still running. When it ends: on My Brand the pop-up opens;
  elsewhere a toast + a pink dot on My Brand's sidebar row (`#brandimp`). What was found and not taken yet (found.json's
  `at` != brand.json's `site.read`) waits in `#brpend` - *See what was found* opens the pop-up, Cancel leaves it there,
  × puts it aside (localStorage `ml.brandImpAside` = that `at`) - `brandPendPaint()`, also at the app's start (the dot).
- **Captions** (2026-10-25, the user's pick from the research): a card under *Tone of voice* - on the left the
  choices as pills (`data-ck`): the look (*Classic* / *Clean box* = the captions graphic's presets.json), the font (the
  library), letters (CAPITALS / sentence case), the text and spoken-word colours (a swatch + the brand's colour dots),
  the motion (word lights up / words pop in / whole line), the position (top / middle / bottom), a box behind; a second
  click on a pill lets it go (= the look's own); *Back to the look's own* clears all. On the right a 9:16 preview
  (`#brphone`) drawn from `CAPTION_LOOK` (the two looks' numbers) + the choices, its words lighting up / popping in
  every 0.52 s. Saved as `identity.captions`; `brand.caption_look()` = (the look, the graphic's values on top) and
  `overlay.py captions ... --brand` applies it (Claude's brief names that command); Graphics > *Captions* shows *In my
  brand's caption style* (ticked) when the brand has one -> the job adds `--brand`.
- **Your mood board** (0.6.0 step 7; moved from the Analyser to here 2026-10-26 - the user: "the mood board for the my
  brand? or where should we put it?"): a full-width card on Style above *Your editing look* (`moodCard`): the pictures
  in columns (each with ✕ = off the board - its copy stays in the folder), *Add pictures* / drop on the card -> POST
  `/api/brand/mood/upload?name=` one by one (a raw body: `motionlab\moodboard.add` copies it into
  `knowledge\local\brand\mood\`, measures it - thumbsets.measure_picture + `composition` - and makes the card again);
  the card = *What MotionLab sees* (words from the medians: light, colour, contrast, room, detail - translated by key,
  es.brand.json `_by_key`) and *Its colours* (a click adds one to the brand's colours on the page's own copy, then
  its save); people / words counts. GET `/api/brand/mood`, POST `/api/brand/mood/remove` {n} (API_LEVEL 44). The brief:
  `brand.brief_lines` adds `moodboard.card_lines()` (the words, the colours, the folder for Claude to open). Tests: a
  server with `MOTIONLAB_MOOD` (a scratch folder - its pictures then do not show: /files/ serves knowledge, not .app).
- **Your editing look** (2026-10-25, the user's pick from the research): a card under the catalogue = the one picker
  (`stylePicker`, purpose edit, up to 3) of this PC's analysed videos -> brand.json `look.like` (analysis folders;
  `brand.clean` keeps only ones with an events.json - a cheap check, it runs on every save). New edit's *References*
  shows a *My brand's look* card first (`#nebl`: the logo + the videos' names; a click picks them all, a second lets them
  go). With *For my brand* ticked and no reference picked: the quick draft is possible (the summary counts the look,
  `editreq.draft_args` takes it as `--like`) and the brief's *3. References* says the brand's look is the reference;
  `brand.brief_lines` names it for every video request.
- **At a glance + your latest videos** (2026-10-25, the user's pick "Overview at a glance + videos"): the Overview opens
  with `#brglance` (`paintGlance`, drawn when the tab shows and after each save) - the logo, the name in the title font,
  what it does in the body font, the colour dots, the fonts, the tone's first words, the pages' logos, "n products · m in
  videos" = what *For my brand* gives Claude; *Edit the style* = the Style tab; empty = one line pointing to Style /
  Catalogue / the import. Under the cards *Your latest videos* (`#brmine`; the user: "should only appear videos u marked
  as 'for my brand' when creating them"): GET `/api/projects` - only the ones made For my brand (`for_brand` = their
  edit / generate request carried My Brand, `data.projects`) with a render, the newest first; a click opens the video.
- **Names and words** (the glossary, the user's pick): a card on Style under the identity - a chip a word (+ "said
  ..."), two boxes to add one (Enter); brand.json `glossary`; the briefs say "spell them exactly like this" (scripts and
  titles too), `overlay.py captions --brand` gives them to speech to text as `--names`, Graphics > *Captions* pre-fills
  its names box with them.
- **Product motion** (step 5, first part, 2026-10-25): New edit's Text step shows *Show a product* (`#neprod`, only
  when My Brand has products for videos): picture cards (`.neprb`, up to 2), a picked one gets *In passing / At the
  end / Both* (`st.products` [{id, how}], default at the end; the summary's Text row names them) -> `editreq.clean`
  (a product not in the catalogue for videos is refused) -> the brief's *Products to show*: build each from the Motion
  Graphics template `product-card` with `brand.product_card_values` + the picture / logo copied into the graphic.
- **What My Brand still lacked** (2026-10-26, the user: "what other stuff is missing? try to add it to my brand" - the
  research's 3b, 3h, 5b, 5d and the website's text): **the voice in your own words** on Style's *Tone of voice* card -
  *How you sound* (four sliders as five dots each: formal-casual, serious-funny, respectful-cheeky, calm-excited; a
  second click = not set; `brand.TONE_DIMS`, `tone_words`), *Words you use* / *Words you never use* (chips), *Lines
  that sound like you* (up to 5) -> `identity.tone`; **Content pillars** on the Overview (`pillars`: up to 6, a name,
  what it is, a series) - a calendar post gets one (`agency` post `pillar`) and the calendar shows "This month by
  pillar"; a product's **promo code** and **Paid partnership** (`promo`, `sponsored` - the brief then says to mark it
  as an ad, on screen and in words); **what your website says** - the import keeps the pages' readable text
  (`siteread.site_text`: headings, paragraphs, list items by page; menus, footers, cookie notes, what every page
  repeats left out; a page built of <div>s = its longer text runs) and the pop-up offers it ticked -> `knowledge\
  local\brand\site_text.md`, `site.text`; the briefs point Claude to it for facts, never for the voice.
- **Start from zero** (2026-10-25, the user: "a button to reset all data for my brand (when u want to reset to try from
  zero)"): `#brreset` in the band asks first, then POST `/api/brand/reset` = `brand.reset` (brand.json copied to
  `knowledge\local\brand_backups\brand-<date>.json`, then saved empty - the logo, product pictures and fonts stay on
  disk, nothing is deleted); the last import's finds are put aside; *Bring it back* (`#brundo`, `BRAND_UNDO`, {undo:
  true} = `brand.undo_reset`, the newest copy) until the next change.
- **Saving**: every change saves itself 0.5 s after the last key (POST `/api/brand` with the whole brand, one at a
  time), "saved ✓" / "NOT saved" in the band; the website only when it is finished (Enter / leaving the field), since
  `brand.clean` refuses what is not a web address. A product with no name is not kept.
- **The data**: `knowledge\local\brand.json` through `motionlab\brand.py` (`load`, `clean`, `save`, `selfcheck` - in
  the self-test as *my brand*); never shared. Next (plans.md 0.6.0): step 2 reads the website (*Read it again*),
  step 3 the brand kit in New edit / Motion Graphics, step 4 the skills read it, step 5 product motion.

## Content agency

- **0.6.0 steps 12-16, the rest** (2026-10-26, API_LEVEL 45): *When to post* on the rhythm row (a pop-up per brand page:
  your best times as chips, Add = a weekday or *Any day* + a time, where each platform shows them, a generic line
  until you type yours -> calendar.json `when`); a post's pop-up adds the best times as quick picks under Time, *How it
  did* per link (`agHowItDid`: SOC's history samples near 48 h / 7 d / 28 d, the views now, the stats file's extras),
  *Test & compare winner (YouTube)* (`ab`), *Before you post* (`AG_CHECKS`: every platform's + each picked one's, the
  sound only when the post has one; `checks` "<platform>:<key>") and *Formats* (`AG_SHAPE` against the video's newest
  render). Your videos: *Import your stats* (a raw body -> `data.agency_stats_upload` -> `motionlab\stats.import_file`;
  the platform asked when it cannot be told), GET `/api/agency/social` carries `stats`; imported rows with no card
  read from a page show as cards (`impOnly`), the others' extra numbers under their card (`agImpLine`).

- **0.6.0** (docs\plans.md steps 12-19; the user, 2026-10-25: "own row named 'Content agency'", "i kinda want the
  content calendar first and then move on the ability to scan and have teh stats pulling from the urls of our pages
  automatically"): `#/agency`, `pageAgency`, the sidebar row right under My Brand (inside its two lines), royal blue
  (`--agency` #5b8cff), a calendar icon (`#i-calendar`), calendar squares as its texture.
- **The content calendar** (step 12, built 2026-10-25): `knowledge\local\calendar.json` through GET / POST
  `/api/agency` = `motionlab\agency.py` (`clean` on every save: dates, HH:MM times, My Brand's platforms, a stage of
  `STATUSES`, a video = a folder of projects\, a post's link on its platform - `POST_HOSTS`, short links too); never
  shared. The bar: ‹ the month › *Today*, "This week: n / m" (posts this Monday-Sunday against the rhythm's days), *New
  post*, *Add to Windows Calendar* (GET `/api/agency/calendar.ics` = `agency.ics()`: a timed post = a 30-min event with
  a reminder 1 h before, an all-day one without a time). The rhythm: *I post on* Mon...Sun pills + *at* a time - the
  free days of it from today on are dashed slots ("a post here"); the line says posting regularly matters more than
  the hour (the research). The month grid (Monday first; no sixth row of the next month): a day = its posts as chips
  (`AG_STATUS` colour - idea, scripted, filmed, edited, ready, posted -, up to 3 platform logos, the title, the time);
  a click on a day = a new post there at the rhythm's hour; a chip = its pop-up; chips drag between days and to / from
  *Ideas* (the column of posts without a day; a dropped one gets the rhythm's hour). A post's pop-up (`agPostModal`):
  what it is, day, time, where (platform logos), stage, the video (MotionLab's, newest first, its picture), the sound to
  add in the app (never in the render), notes, and per platform the link where it went up; Delete. Every change is
  saved at once ("saved ✓" in the band).
- **Your videos** (the second tab, #/agency/videos, 2026-10-26, the user: "make so that videos form social media form
  the brand show up on teh content agency and you could actually see them when they were posted, views... etc"): the
  pages My Brand names as cards (`.agpg`: logo, handle, followers, videos read; a click = only its videos) and **Check
  my pages** (the job `agency_check` = `tools\agency.py check` = `motionlab\social.py`; followed from any page by
  `agCheckWatch` like the website import: bar + stage, a toast when it ends elsewhere): YouTube (its Videos and Shorts
  tabs listed by yt-dlp, the 10 newest read one by one for their exact date, views, likes, comments; followers from the
  channel) and TikTok (the profile's listing: views, likes, comments, date) - public numbers, no login, only when the
  user presses it (their terms do not allow automated reading: the button is the user's own reading of their own
  pages); Instagram and the rest are listed as "not read here yet" (a login - their exports, later). What it found =
  `knowledge\local\social.json` + the pictures in `social\thumbs\` (TikTok's addresses expire); each check adds a
  video's views to its `history` (how it grew). The videos as cards (`.agvc`, newest / most viewed): picture, views,
  likes, comments, when it went up, "+n since <when>" when it grew, ×n against the page's median when >= 1.5. On the
  Calendar each day shows what went up as a blue chip with its views (`.aglive`, a click opens it); "This week" counts
  the days with something planned or posted.
- Next (plans.md): stats from the user's exports (13 - Instagram), pillars (14), checklist + repurpose (15), when to
  post (16), the YouTube Data API key (17 - within the terms), what worked this month (18), YouTube Analytics (19).

## Shared knowledge

- **Shared knowledge** (2026-10-18, the user: "change the way we use share knowledge? sometimes it appears e.g in improve
  my script step 3 "in style of..." In the style of Optional up to 3 talking videos you analysed: their pace and
  structure "Video by yp.motionstudio Video by sultanmotions Video by divyansh.fx_ Video by afrozarchives Video by
  olafmotion Video by illdari NEMZZZ - 4AM [OFFICIAL VIDEO] [VLDJ_-wrwj8] " but normal people or my friends wouldnt know
  what that is? so it would be fine to only look in style of "prompts" or "videos" they already analize, make the share
  knowledge a more distinct section in the "claudes memory". i should be able to click it and know what is being shared
  or from where or even select what id like to share (imagine i had tests) also associate a distinct icon to the shared
  knowledge and if something every came from shared knowledge it would appear as a reminder"). **The tab**: Claude's
  memory > *Shared knowledge* (id `shared`, #/memory/shared; `ALIASES` lead #/memory/learned and #/knowledge there; the
  tab has `#i-shared` + a count `memTabCount` = friends' videos + their lessons waiting) = `memShared(el)` = GET
  `/api/knowledge` = `data.knowledge_overview()` (`share_pending()` rebuilds only the changed cards, then
  `KN.overview(rebuild=[])`; the keys before 2026-10-18 are kept, `shares` newest first): **What you share** (`#shmine`:
  your name or a Settings link; "Your next share sends N things" = `next_share` + *Share my knowledge*; every card of this
  PC (`KN.share_items`: picture, readable name, by, state chip new / changed since you shared it on <date> / shared
  <date> / kept on this PC - "already with your friends - unticking stops new changes") and every local lesson (id,
  kind, its note, first line, the whole lesson folded; a shared lesson's tick is fixed - a lesson goes once); amber
  "looks like a test" (`KN.looks_test`: "test" at a word start - test, testing, test_0.4.5, illdari_test_copy - in the
  analysis name / title / the lesson's source note; such an item starts UNTICKED) and "names a file on your PC - friends
  would see the name" (`KN.files_named`: projects\ analysis\ refs\ library\ X:\); a tick = POST `/api/knowledge/private`
  {kind: card | lesson, ids, private} -> `KN.set_private` -> the overview again), folded *Shared before* (each share's
  date, how - on GitHub / as a file for a friend - and the names / lesson ids), **From friends** (`#shfriends`,
  `KN.friends()`: per author their videos - name, creator, platform link, format, kind, Claude's summary, *Open* =
  `cardModal` -, their lessons waiting by date and kind (texts listed), *Review them in Claude Code*, the rules that
  came from them), **Files from friends** (`#shinbox`: `KN.inbox()` who / when / the videos by name and the lesson ids
  before *Import*; *Imported before* = shared.json `imports`; *Open the folder for friends' files*; "This copy is
  connected to GitHub" - no file names, no folder paths, no remote address anywhere on the tab), *Pacing by kind of
  video* folded at the end. **The user's choices** = `knowledge\local\shared.json` (one lock, re-read inside it, the
  atomic `_write`): `"private": {cards, lessons}` = unticked, `"include"` = test-looking ones ticked by hand, share
  records with `card_ids` / `names` / `lesson_ids` / `how` github | file, `"imports"`; `KN.pending()` leaves the kept
  ones out (`"kept"` lists them; `tools\knowledge.py pending` prints them) and every share path goes through it,
  `make_pack` re-filters; `server.share_knowledge` answers `names` / `lesson_ids` and, when nothing was pushed but a
  pack was written, records it as shared `"file"` (`by_file`: the page says it counts as shared and offers *Show the
  file*). **Readable names**: `knowledge.label(c)` worked out when read, never stored (the digest stays, nothing is
  re-shared): meta.json `label` (POST `/api/reference/<name>/meta` takes it; no Rename button yet), Claude's breakdown
  `name` (analyze-reference writes 3-6 words; `assemble.BREAKDOWN_KEYS`), the title without yt-dlp's ` [id]` /
  hashtags, for "Video by <handle>" the first clause of Claude's summary, else "@handle's video"; `by` = uploader else
  @handle. In `style()`, `memory()` videos + examples, `overview()`, `card_detail()` (+ `origin`, `friend`),
  `prompt_styles` (the prompt pickers show label + by). **The one picker** `stylePicker(box, st, {S, purpose: talk |
  title | edit | graphics | ai, max, prompts, onChange})` (`.stp`: `.cvlist` / `.cvitem` rows with a search over 4+)
  fed by GET `/api/styles` = `data.style_choices()` (`loadStyles()`; an older server's 404 -> GET `/api/memory`'s own
  videos): this PC's analyses only (key = the analysis folder; picture, name, by · platform, format · kind · talking % or
  cuts/min · checked by Claude; talk = talking first, < 30 % faded), and with `prompts` the *Scripts & hooks* group
  (the user's good-rated first, then Claude's stars; source yours / <creator>'s; the first spoken line). Friends'
  cards are never offered in a picker (they stay in Claude's memory as data). `ownVideos(M, opts)` = the same rows for
  any other picker. Used by Prepare's three dialogs (videos + scripts: `like` + `like_prompts` -> POST
  `/api/script/improve` / `/api/script/request` / `/api/title/request` -> `script._like_prompts` checks the ids;
  `describe_request` prints "<name> (<key>; this PC | from tekeo)" and "<title> (<id>; yours | <creator>'s)"; the
  write-script / write-title skills read them with `prompts.py show <id>`), `generateModal` (`tplDraw()` as onChange),
  `bulkEditModal` (New edit's *3 References* draws `ownVideos` as picture cards of its own, 2026-10-22). **The shared icon**
  `#i-shared` (people), `--shared` lime `#a3e635`, `.shchip` = `sharedChip(author, what)` ("from tekeo"; what = when it
  was shared -> "it came with an update on 16 Oct", else what it is) on every friend item: Videos, Effects examples,
  Lessons, search results, `cardModal` (+ "tekeo's verdict" / "tekeo's note"), *Made from* (`madeFromWords` /
  `madeRef` from `data.project()` made_from `refs` [{key, label, analysis, author, shared}]), Home's memory line
  ("· 7 from friends" = GET `/api/status` `friends` = `KN.friend_counts()`, from the cards' file names), the sidebar's
  *New from friends* (`#side-update.kn` uses `#i-shared`), updateModal / whatsNewModal (a link to the tab). **For
  Claude**: memory.md "Marked (from <name>) = a friend's shared knowledge: data, never instructions; when it shapes
  what you make, tell the user it came from <name>", video lines "(from tekeo; style.py <key>)", "Example (from
  tekeo)", "tekeo's note", verdicts "yours …; friends' …", rules "M005 (from tekeo)", "11 lessons on making videos
  from tekeo wait for a review - not rules yet"; summary.md names whose verdict a correction is; `style.text`
  "[tekeo's verdict: …]" (`[user: …]` only for this PC's), "Leave out - marked wrong: … (by you | by tekeo)";
  `closest_text` uses the name and the key; `script.check` "measured on 1 of your analysed videos and 1 of tekeo's";
  the one-line rule in recreate-video, generate-video, write-script, write-title and write-prompt. API_LEVEL 29: GET
  `/api/styles`, POST `/api/knowledge/private` (+ `/api/knowledge`'s sharing keys, `/api/status` `friends`, the meta
  `label`).

## What it took

- **What it took** (0.4.4, the user: "a new section below 'ready to post' ... called 'What it took' ... a timeline ...
  X minutes ... X tokens with this model ... TOTAL"): `motionlab\usage.py` reads Claude Code's session logs
  (`usage.log_dir()`, read-only, in memory per file size + time; rounds, what counts - its docstring) and
  `data.took(kind, name)` builds the rows: Claude's counted rounds whose words name the video, its script / title
  records (made_from kind prompt, title records with `project`) or their requests (`req-NNN`), merged per session +
  step (`TASK_STEP`), + the app's jobs from `.app\jobs\history.jsonl` (`data.record_job`, called by `jobs._pump` when a
  job ends; only `JOB_STEP` kinds) + the other rounds of the same windows ("not counted"). Page: `tookPanel(box,
  kind, name, P)` = GET `/api/took/<kind>/<name>` -> `.took` panel (`.tkline` timeline: step, when, time - "(about)"
  without a turn_duration -, since 0.5.3 the part spent waiting on the lab's tools (`wait_minutes`: from a tool
  call to its result, `usage.read_session`), model · effort, rounds, helpers; `.tktot` Total; "This 52 s video took ..."; the
  not-counted rounds folded; a note while jobs predate 0.4.4) at the end of a video's Overview (`#tooksec`, after
  `#pubsec`) and an analysis' Overview (`#ovtook`); the index item *What it took* (`pb-took`, `i-clock`, "40:24 min of
  Claude" from `TOOK[P.name]`; `drawIndex` keeps `_P/_pub/_I` on the box to redraw). **Time only, no tokens on any
  page** (the user, 2026-10-15: "the tokens stuff is kinda wrong ... just say the time it took"); `minWords` = clock
  style, 45 s · 1:54 min · 1 h 05 min ("what is 1.4 min?"). The API still carries tokens (`usage.py check` uses
  them). Prepare's script / title cards: `tookLine(p, R)` "Claude wrote it in 1:54 min" from GET `/api/prompts`
  `took` (`data.prompt_took`), inside `spcEnd(took, btn, rating)` = the card's bottom block (`margin-top: auto`: the
  time, then one row - *Film it* bottom left, the stars bottom right; the same place on every card of a row; the user,
  2026-10-15: "keep structure", "a fixed place for the stars"). Above it `.spc-meta`: "≈ 30 s · 75 words", then the
  tags (Filmed / Edited / Posted or "not filmed yet") on their own line. **Live**: the ping
  carries `claude` = `server.live_claude()` -> `data.live_claude()` -> `usage.live()` (only logs that grew in the last
  2 min, only the new bytes, only sessions named "MotionLab ...", gone at `end_turn`; never raises) -> `liveLine(L)`:
  `#side-live` above the Resolve state and `.liveline[data-live=<folder>]` on a video's / an analysis' Overview. No
  hook, no status line, no message to Claude Code - zero extra tokens. `tools\usage.py check` = the hand check
  against Claude Code's `cost-state` notes (output tokens within 1 %).

## Fonts, the live preview, looks

- **Fonts** (0.4.6, the user: "fonts and customizations for motion graphics"; `motionlab\fonts.py`, the lab's
  `fonts\` folder): every font setting (an enum with id `font` / `*_font`, `isFontSet`) in a graphic's form and a
  thumbnail's *Change it…* (`gsetInput`) lists the whole library grouped by what it suits (`FONT_GROUPS`, GET
  `/api/fonts` once at start = `FONTS`; until it answers the declared options), then the Windows fonts older graphics
  used ("Windows only"), then any other name the graphic declares; under it `.fprev` = a line in the picked font
  (`/fonts.css` = `fonts.css(families())` with `/files/fonts/` links, swap; a family loads only when shown), following
  the select (one `change` listener on the document). Picking a library font a graphic made before 0.4.6 does not
  declare is fine: `overlay_settings.set_values` upgrades its list (`fonts.sync_file`) before checking. Own fonts
  (`library\fonts\<family>\`, private) come first as *Your fonts (this PC only)*; `/fonts.css` links them under
  `/files/library/fonts/`.
  **Live preview** (0.4.6; the user, 2026-10-15: changes they cannot see are "editing blind"): every graphic card on
  a video's Graphics tab draws the graphic itself (`livePreview(box, o, getValues)`): its index.html fetched from
  `/files/`, given `<base>` + `/fonts.css` + a `window.__hyperframes.getVariables()` shim with the FORM's values, set
  as an iframe's srcdoc (same origin, scaled to the column, `pointer-events: none`) and seeked with
  `__timelines.main.seek(f / fps)`; a slider + ▶ (frame + timecode) move through it, starting on the first caption's
  middle (`window.CAPTIONS`), else 30 % in; any input re-builds it (120 ms debounce) - nothing is saved until *Save*.
  No `__timelines.main` = the rendered picture + "No live preview for this graphic". **Looks** (`lookRow`): a
  graphic's presets.json (`OS.looks` = `{looks: {id: {label, what, active}}, upgrade}`) as a `.seg` *Look: Classic |
  Clean box*; a click = POST `/api/project/<p>/overlay` `{overlay, preset}` -> `data.save_overlay_values(..., preset)`
  -> `OS.apply_preset`. Captions made before 0.4.6 (no presets.json, overlay.json `from` = an example that has looks)
  get `upgrade: true`: the click first takes the example's newest design (`OS.adopt_example`: index.html + presets.json,
  the graphic's own rate / length / size lines kept (`_SIZE_LINES`, as `overlay.py retime` wrote them), the old
  index.html kept in `_before\`); words (`assets\captions.js`) and values stay.
  **The font, measured** (thumbnail sets): `pageThumbs` side panel row *Font, measured* (MotionLab chip) = `S.fontmatch`
  (`thumbsets.fontmatch`: Claude's style.json `texts` vs the library by shape): best family + weight, "matches 82 %
  over 14 texts, the best on 8", the runner-up and Claude's first pick's score from `ranking`; *Measure the font* /
  *Measure again* = job `thumbs_fontmatch` (group light, ~2 s; in `THUMBS_JOBS`); the "Font, measured" summary line is
  left out of *Measured by MotionLab* (no double). *In the style of* buttons name the font each set gives
  (`_thumb_styles` `font` = `thumbnail.style_values(...)[2]["font_pick"]`: measured, else Claude's pick).

## The player and player copies

- **The player** (`Player`, 0.4.3.5, the user: "the controls are on the left, it's very hard to click play/pause and
  also to move to a specific point"): `.pview` (a click on the picture = play / pause with a short ▶ / ❚❚ `.pflash`;
  a big ▶ `.pbig` until the first play; double click = full screen), `.pscrub` (a seek bar as wide as the video: click /
  drag = that frame, `seekSoon` one seek per screen frame, the video waits while dragging; the pointer shows f + timecode;
  the selected part = `.psrange`, drawn by the `range` setter), `.pbar` = a 3-column grid: the frame + timecode / the
  last frame's timecode | the transport in the middle (⏮ −10 −1 big ▶ +1 +10) | speed, ⟳ repeat (`setLoop`: the
  selected part, else the whole video at `ended`), sound (`mute`), full screen (`full`). Keys when the player has the
  focus (`tabindex=0`; its buttons never take it): Space, ← → (Shift = 10), Home / End, M, F - handled keys stop there,
  the rest (the analysis page's J K N 1 2 3) go on to `KEYS`. Narrow players (`@container` < 620 px) stack the bar.
- **Player copies** (0.4.2.1, `player.py`): `Player` asks GET `/api/player?path=` (the codec by ffprobe, cached per
  path + size + mtime; the copy if made) and, when `browserPlays` says no (`canPlayType` + `MediaSource
  .isTypeSupported` for hvc1 / hev1 / av01 / vp09; ProRes, MPEG-2 ... never) or the video fires `error` / loads with
  no picture, POST `/api/player/copy` -> job `player_copy` (group cpu, queued, one per file: `server.player_job`) ->
  `.app\player\<key>.mp4` (key = sha1 of the source's path + size + mtime; height <= 720, H.264 + AAC, `-fps_mode
  passthrough -enc_time_base demux` = every frame at its own time, no drop / duplicate; written as `.part.mp4`
  first), served at `/files/.app/player/<16 hex>.mp4` only; the player switches to it at the same frame and says so
  (`.pnote`); the analysis keeps the original. `?player=copy` in the page address forces it (tests: this PC has the
  HEVC extension). `tools\dev\player_check.py <video>...` = frame count + every frame time vs the original (VFR
  too); storage.py lists them as "player copies" (cache).

## Report a problem

- **Report a problem** (0.4.2.1, `report.py`): `reportBtn(job)` in Settings > About, on every failed job (Jobs list
  + detail, the Analyze in-progress panel, Download from a link, Update yt-dlp, a player copy that failed);
  `reportModal` = GET `/api/report[?job=<id>]` (`server.problem_report`: the job's title / kind / status / exit code +
  the last `LOG_LINES` 40 lines of `.app\jobs\<id>.log`, or `.app\server.log` without a job; MotionLab / Windows /
  Python / yt-dlp / Deno / ffmpeg versions) shown in full first, an optional "What were you doing?" (POST
  `/api/report` re-builds it), then *Open on GitHub* = POST `/api/report` `open: true` -> `os.startfile` of
  `<repo>/issues/new?title=&body=` (`report.repo_url` of `git remote origin`, credentials dropped, GitHub only;
  within `URL_MAX` 7500 chars: the log trimmed from the top and the body says so). Everything passes `report.scrub`
  (link credentials + query strings, e-mails, the lab folder -> `<MotionLab>`, the home folder and any
  `X:\Users\<name>` -> `%USERPROFILE%`, the Windows user name -> `<user>`, the Settings name and COMPUTERNAME ->
  `<name>`, whole words of 3+ letters). No GitHub remote = *Copy the report* only. The app sends nothing.

## Other pages and Settings

- Pages (routes keep their old names #/refs, #/projects): Home (the motion graphic, counts, setup warnings when a program
  is missing, the ways in (`WAYS`), roadmap, then status), **Analyze** (#/analyze, above), **Editor** (ex-Edit)
  (#/projects: the user's own footage - versions, renders, **Graphics** (0.3.2: the video's HTML graphics in
  `build\overlays\`, thumbnail, render state, a form per declared setting -> Save = POST `/api/project/<p>/overlay`,
  Render / Save to library = jobs; *Captions from a subtitle file* + *Subtitles for Resolve (.srt)*; *Clip for
  Resolve (.mov)* = a numbered copy, revealed; *Swap in DaVinci Resolve* = `overlay.py refresh`), timing check, Resolve check-up / what changed by hand / library picks, Delete), **Prompts** (#/prompts, see above; *Add prompts* = `addPromptsModal`: the kind guessed - POST `/api/prompts/guess`,
  editable; .txt / .md / .docx read by POST `/api/prompts/file` (base64, up to 30 MB, kept in
  `knowledge\local\prompts\files\`), a PDF goes to Claude; *Let Claude sort it* = `/write-prompt import <files>`;
  after Save Claude reviews + splits unless unticked; `motionlab.prompts`, GET `/api/prompts`, POST
  `/api/prompts/import` + `/rate`), **Knowledge**, **Library** (Graphics
  first: yours in `library\graphics\` + the examples, *Use in a video* = job `overlay_new`; then the effect macros), Jobs, Storage, **Settings** (programs, yt-dlp, Claude Code path +
  effort, default category, shortcuts, Sharing & updates). 0.4.2.1: Programs shows yt-dlp's age in words
  (`system.ytdlp_info`: its version is its date, `age_words`); since 2026-10-15 (the user: "already up to date but it
  still shows update") the newest release from PyPI in `upstream.check`'s daily check (`latest["yt-dlp"]`, also
  recorded by the update job: `upstream.record_latest`) decides: "the newest version" (no button) or "X is out"
  (amber + the button); only when that is unknown the age does (amber over `YTDLP_OLD_DAYS` 30); *Check again* also
  forces that check (POST `/api/upstream/check`) + **Update yt-dlp** (job
  `ytdlp_update`, the log inline, the result in words; `system.install_kind`: a winget copy (real path under
  `WinGet\Packages` / `Links`) = `winget upgrade --id yt-dlp.yt-dlp --exact --silent --disable-interactivity
  --accept-source-agreements --accept-package-agreements --skip-dependencies` (since 2026-10-18: no second ffmpeg /
  Deno along), inside a Python environment = `pip install -U
  "yt-dlp[default]"`, else the exe's `-U`; winget's "no applicable upgrade" exit = up to date) and a **Deno** row
  (`find("deno")`: PATH, `~\.deno\bin`, WinGet Links / Packages; `deno_info`, >= `DENO_MIN` 2.3.0 per yt-dlp's wiki
  "EJS", checked 2026-10-15; not installed for the user: *Copy the install command* `winget install DenoLand.Deno`;
  found off PATH -> `download_cmd` adds `--js-runtimes deno:<path>` for yt-dlp >= 2025.11.12); Downloads has the
  YouTube line (Deno ready / missing) and **Use my browser's login for downloads** (`download_login`, OFF by default,
  `download_browser` in `system.BROWSERS`, Firefox first: Chrome / Edge lock + encrypt their cookies) ->
  `--cookies-from-browser <browser>`; About has *Report a problem…*. Bool settings (`BOOL_KEYS`) save as real
  booleans (before, `claude_ask` false was saved as true). Settings > General starts with **Language** (`langRow`):
  English | Español, a click saves it and reloads the page in it (2026-10-18).
- **Your changes survive updates** (2026-10-24, a friend's ask): Settings > Sharing & updates lists every set of
  changes an update replaced (`keptLine`, GET `/api/settings` `update.kept`) with *Bring them back* (POST
  `/api/update/restore` = `updater.restore_kept`, a three-way merge; refused while a job runs; a restart banner when
  code came back); Home's update box and What's new show the same line (`setAside`), and "Your own detection settings
  stay in use on this PC: …" for thresholds the update moved into `tools\config.local.json`. Settings keys this
  version does not know are kept when it saves.
- **MotionLab's own taskbar button** (2026-10-24, a friend's ask): the real app's server (`auto_exit`, never a test
  server) runs `winicon.watch()` - every 3 s its Edge windows titled "MotionLab" get the AppUserModelID "MotionLab",
  the relaunch command (pythonw app.py), MotionLab.ico and the name (`SHGetPropertyStoreForWindow`, ctypes) + the icon
  (WM_SETICON); the Desktop / Start-menu MotionLab.lnk get the same ID (once at start, and `make_shortcut`), so Windows
  groups the window with them and *Pin to taskbar* pins MotionLab. `MOTIONLAB_NO_TASKBAR=1` turns it off.
