# MotionLab - how the plans got their numbers

The history behind [plans.md](plans.md): renumbers, where each plan came from, and measurements that are finished.
plans.md keeps only what is planned now. Older notes, chats and code comments use the old numbers: look them up in
the table below.

## Which plan an old number means

| Plan (number now) | Earlier numbers |
|---|---|
| Each section its own feel (0.4.1.1) | none (added 2026-10-14) |
| Check before you render (0.4.2) | 0.4.6 (2026-10-14) |
| Downloads that keep working + Report a problem (0.4.2.1) | none (added 2026-10-14 evening; its download items were "carried over from 0.3.3" inside describe video, *Report a problem* was in ideas.md) |
| Title + thumbnail (0.4.3) | 0.4.2 (2026-10-14) |
| Prompt generator (0.4.4) | 0.4.1 (until 2026-10-13), 0.4.5 (2026-10-13), 0.4.3 (2026-10-14) |
| Yapping mode (0.4.5) | 0.4.0 (until 2026-10-13), 0.4.4 (2026-10-13 to 2026-10-14) |
| Colour (0.4.6) | 0.3.7 (2026-10-12), 0.4.3 (2026-10-13), 0.4.5 (2026-10-14) |
| Content generation (0.5.0) | none (2026-10-14); "0.5" before that meant templates by feel + macOS |
| Templates by feel (0.6.5) | 0.5 (with macOS, 2026-10-07 to 2026-10-14) |
| AI B-roll and cinematics (0.7.0) | 0.7 |
| macOS (0.7.5) | 0.5 (with templates by feel, 2026-10-07 to 2026-10-14) |
| Describe video (0.8.0) | 0.4 (2026-10-09), 0.6 (2026-10-11), 0.3.5 (2026-10-12), 0.4.2 (2026-10-13), 0.4.7 (2026-10-14) |

## Renumbers

- **2026-10-09**: plans written from the user's notes; re-planned 2026-10-11 and, from the user's notes, 2026-10-12.
- **2026-10-13**, when 0.4.0 shipped the user's overhaul (Analyze / Edit / Generate, Claude's memory, quick drafts,
  colour): the plans that were 0.3.5, 0.3.7, 0.4.0 and 0.4.1 became 0.4.2, 0.4.3, 0.4.4 and 0.4.5 - the same order -
  and 0.4.1 became the fixes after 0.4.0.
- **2026-10-14, morning**: 0.4.6 (check before you render) added, from the rebuild of the first generated video.
  **Prepare** built the same day (Unreleased), the user's ask: improve a script or write one from zero for reach
  (`/write-script` + its guidelines.md, `tools\script.py` = the script check) - yapping mode's step "Topic + script"
  done early.
- **2026-10-14, from the user's notes**: title + thumbnail (horizontal and vertical) and each section its own feel
  added. Renumbered the same day (the user): title + thumbnail up to 0.4.2 and describe video down to 0.4.7; the
  prompt generator up to 0.4.3 and colour down to 0.4.5; each section its own feel = 0.4.1.1, a small step to do
  right away (a four-part number: the updater and What's new read up to x.y.z.w; GitHub's tests run for it by hand or
  with [tests], like 0.4.1).
- **2026-10-14, again** (the user): 0.5.0 = content generation - videos from zero (*Generate*: Claude, HyperFrames,
  AI video tools) made better; gathered from every plan and idea: 0.4.6's sound effects tool, live preview, faster
  motion blur and templates, two ideas (voice-over, music) and new steps. Templates by feel -> 0.6.5, macOS -> 0.7.5
  (its own plan; both were 0.5 together), describe video -> 0.8.0 (was 0.4.7).
- **2026-10-14, evening** (the user picked Claude's review of the plans): check before you render 0.4.6 -> **0.4.2**
  (it saves time on every later video and 0.5.0 builds on it); title + thumbnail 0.4.2 -> 0.4.3; prompt generator
  0.4.3 -> 0.4.4; yapping mode 0.4.4 -> 0.4.5; colour 0.4.5 -> 0.4.6. New: **0.4.2.1** downloads that keep working +
  *Report a problem*. Describe video's foundations (text on screen, shots described, topics) moved into yapping mode
  as its first step, which settles the order conflict between them. plans.md got a status table, a *Ships when* line
  per plan, and this file for the history. 0.5.0's sound effects tool (step 4) was built early the same evening.
- **2026-10-14, released 0.4.1.1**: each section its own feel (the user picked variant B "Bold band" of three shot on
  a test server, then asked for no section numbers, each sidebar row in its section's colour, and Generate in
  fuchsia `#e05cff` instead of pink - picked from tangerine / fuchsia / lime / a sunset gradient), plus everything
  built since 0.4.1: Prepare, the model dialog, check before you render's items 1, 5, 6, 7, and the sound effects
  tool (made 3 dB quieter after the user's listen). Its plan section left plans.md; CHANGELOG.md has it.

## Where some plans came from

- **Describe video**: planned as 0.4 (2026-10-09), then 0.6 (2026-10-11), 0.3.5 since the user's notes of
  2026-10-12, 0.4.2 since 0.4.0 shipped (2026-10-13), 0.4.7 since 2026-10-14 (the user moved title + thumbnail
  ahead), 0.8.0 since later that day (the user made 0.5.0 the content generation version). It was planned as the
  base tool of yapping mode, which comes long before it now - so yapping mode builds the foundations itself.
- **Colour**: the user's note of 2026-10-12 ("a color correction focused version since i think it kinda weak in that
  point"). Placed then after describe video and before yapping mode, because talking videos need it too (phone
  footage: white balance, exposure, skin); the order changed since.
- **Templates by feel / macOS**: planned together as 0.5 since the user's roadmap of 2026-10-07; split 2026-10-14.
- **Yapping mode**: planned as 0.4.0 until 2026-10-13, when 0.4.0 became the Analyze / Edit / Generate overhaul. The
  user's notes of 2026-10-12 say "v0.3.5" for describe video.
- **Prompt generator**: planned as 0.4.1 until 2026-10-13 (0.4.1 became the fixes after 0.4.0), then 0.4.5, then
  0.4.3, now 0.4.4.

## Speech to text: measured and decided (2026-10-12, shipped in 0.3.3 and 0.4.0)

Carried over from 0.3.2 (released 2026-10-12; its Resolve measurements: docs\resolve_notes.md): captions from the
user's own recordings. Captions from any .srt / .vtt worked since 0.3.2; for a recording without one the lab needed
speech to text: the engines were measured on the user's talking video (script `.app\dev\whisper\script_v1.txt`, the
recording in `projects\talk_test\`; HyperFrames' `transcribe` = local whisper.cpp / Parakeet with `--to srt`, and
faster-whisper `tools\dev\whisper_bench.py`, tiny / base / small, also on a laptop setting).

**Measured 2026-10-12** on the user's recording (72 s, phone, read from the script with own changes - so every
engine's error rate below includes those; `tools\dev\speech_bench.py`, report `projects\talk_test\build\speech\`):
faster-whisper int8 on 4 threads: tiny 39.9 % (2 s, 75 MB), base 28.4 % (3.4 s, 141 MB, 360 MB RAM), small 26.1 %
(12.9 s + 5 s load, 464 MB, 730 MB RAM) and **21.1 % with the video's names as a prompt** (MotionLab, 4AM, Nemzzz
right - base with a prompt dropped a whole paragraph); Parakeet (HyperFrames, `models install parakeet`: 640 MB,
5 s here, ~20 CPU-seconds, 1.15 GB RAM, 25 European languages, no names prompt) 26.1 %. HyperFrames' whisper
engine needs whisper.cpp built by hand on Windows - out. Word starts agree within 0.02-0.12 s (median) between
engines. Names are what every engine gets wrong without help.

**Decided + built 2026-10-12** (the user picked faster-whisper small, base as the light option; released in 0.3.3):
`motionlab\speech.py` + `tools\speech.py install | status | transcribe` (optional: Settings > Programs > Speech to
text > Install = the pinned faster-whisper 1.2.1 in the lab's venv + the small model; names via --names / the
dialog, ignored by base); `overlay.py captions --from <a video>` (size / rate / length from the plan or the video -
phone videos stored lying with a 90 deg flag count as upright); App: Graphics > *Captions...* = from the words in a
video (a render of the edit or a clip) or from a subtitle file. Measured on the user's recording: 214 words in
14.5 s, captions at 1080 x 1920, 30 fps, 2159 frames (UI test 9/9). References without subtitles fall back to speech
since 0.4.0 (`content.py auto`). Parakeet stays a possible later option. Small leftovers: the HTML clock's grain tuned
to the lab's texture.

**Earlier measurements** (describe video's "measured so far"):
- **Transcripts (0.3.1)**: `tools\content.py transcript <name>` (yt-dlp: uploaded subtitles in the video's language,
  else YouTube's auto captions of the original audio, which carry word timings) -> `analysis\<name>\content\
  transcript.json / .txt`, frame + timecode per line and per word; `content.py show`; MCP `transcript(reference,
  start, end, words)`. 4AM: 72 lines / 463 words in ~7 s. Timings are the platform's, not measured by the lab.
- **Measuring Whisper**: `tools\dev\whisper_bench.py <name>` (faster-whisper int8 on the CPU in a separate venv, each
  model in its own process, `--threads 4` ~ a laptop; WER and word-timing difference against the subtitles). First
  run, mechanics only (4AM is rap over a beat, so its WER says nothing about talking videos): tiny = 75 MB model,
  318 MB RAM, 27x real time on 4 threads of the RTX 4070 PC's CPU (a laptop core is slower).
- Other engines seen 2026-10-09: HyperFrames (in `tools\overlays\`, optional, needs Node) has a whisper.cpp
  `transcribe` command; ffmpeg's `whisper` filter is in BtbN builds but NOT in Gyan's essentials build (CI's;
  winget's full build: unchecked).

## Released plans (their text when they shipped)

### 0.4.2.1 - released 2026-10-15 - Downloads that keep working, and Report a problem

**Ships when**: on a fresh install, an out-of-date yt-dlp is shown in Settings and updated with one click; a TikTok
(HEVC) reference plays in the app on a PC without the HEVC extension; a carousel keeps every file; *Report a
problem* opens a pre-filled GitHub issue the user reads and sends themselves.

Friends meet these first, and with no usage data sent anywhere, a report is the only way to hear about their
problems. Found in the download review of 0.3.3 (kept until now inside describe video) and in ideas.md.
**Started 2026-10-15** (the user: "continue until 0.4.3, step by step"): all five items, one part (the app,
download.py and the jobs are one area).

- **yt-dlp out of date** breaks TikTok / Instagram first: its age in Settings + an *Update yt-dlp* button (`yt-dlp
  -U`; winget copies: `winget upgrade yt-dlp.yt-dlp`). Recent yt-dlp uses a JavaScript runtime (deno) for YouTube -
  Settings checks for it.
- **HEVC** (TikTok's best format) plays in the app only where Windows has the HEVC Video Extension: a small H.264
  copy for the player when it is missing (the analysis keeps reading the original).
- **Instagram carousels / TikTok photo posts** give several files or sound only; the app records only the last file
  - keep every file and show them as one post.
- **Logins**: Instagram (often), Vimeo (now always) and YouTube's bot check (seen once: HTTP 429 + "Sign in to
  confirm you're not a bot") need the user's browser login. yt-dlp can read it (`--cookies-from-browser firefox`;
  Chrome / Edge lock and encrypt their cookies). It is the user's login: a setting, off by default, only with their
  OK, explained in plain words.
- **Report a problem** (from ideas.md): a button in Settings and on a failed job -> a GitHub issue pre-filled in the
  browser (what happened, the version, the last lines of the job's log with the user's paths and names taken out);
  nothing leaves the PC until the user reads it and presses Submit on GitHub.
**Built 2026-10-15** (released the same day): yt-dlp's age + *Update yt-dlp* (winget / pip / `-U`, tested in a
dry run), the Deno check (yt-dlp's wiki 'EJS' checked 2026-10-15: Deno >= 2.3.0), player copies for HEVC / AV1
(`.app\player\`, the same frames: 120 = 120, VFR frame times within 0.00 ms), carousels kept as one post
(downloads.json `post` / `part` / `parts`), the browser login (off by default, Firefox first), *Report a problem*
(scrubbed, a GitHub link <= 7500 characters, nothing sent by the app). Not tried yet: the real yt-dlp update (the
user's click), a real carousel, a PC without the HEVC extension. The full self-test caught one break before the
release (a 0.3.x download check fed the old 5-field saved-file line) - the check now uses the 7-field line.

### 0.4.2 - released 2026-10-14 - Check before you render

**Ships when**: snapshots match the render at the checked frames (the difference measured and stated); a new graphic
from the starter renders the same with and without motion blur; Claude's memory states every part the user rated bad
as a default for later videos; the first lessons on making videos (M###) are reviewed; the next generated video needs
one final render (illdari v1: three motion-blur renders, two thrown away).

**The user's words (2026-10-14)**, after rating the first generated video (illdari_test_copy_1) and its rebuild:
"it took too much time to recreate a 'simple' motion graphics 25 second video (with a full reference to 1:1 copy)",
"would it be better to have a general draft before actually going to render 'blindly'?", and "learn from this
analyze / recreation / re-recreation ... applied to the entire workflow for future videos where we go blind or have
a totally different feeling".

**What happened (measured 2026-10-14)**: v1 was rated graphics OK "motion graphics feel too clunky", sound effects
bad "no sfx at all". All three causes could be checked before building: the app drawn ~40 % smaller than in
illdari's reel, no sound effects, no motion blur. The rebuild rendered 79 s (a speed test) + 2 min (a plain check) +
7.9 + 7.6 + 9.2 min (three renders with motion blur) = ~29 min, of which only the last 9 min were needed: the first
two motion-blur renders found a bug a 1-second snapshot shows (the logo's badge missing at f38 (00:00:01:08)) and
copies on moves too fast for 5 sub-frames (f113-f116 (00:00:03:23-00:00:03:26)), which a speed calculation predicts.
Claude sees stills and cannot hear: every guess (one fixed volume for all effects, 5 sub-frames being enough) cost a
round; every measurement (each effect against the song under it, pixels moved per frame) worked first time.
**Shipped in 0.4.1.1** (2026-10-14): real motion blur, `overlay.py render --motion-blur N` (kept in overlay.json);
a note in `/generate-video` (size, camera, motion blur, sound effects); the worked example
`projects\illdari_test_copy_1\build\` (`sfx_v2.py`, `overlays\kidwild_top3_v2`, on the user's PC only).
**Shipped in 0.4.1.1** (2026-10-14): items 1, 7, 5, 6. `overlay.py snap <folder> <frames>` = HyperFrames'
snapshot with the user's values, frame + timecode burned in, no render (~3 s for 1 frame, ~7 s for 10; v1's f38
(00:00:01:08) shows the missing badge in 3.3 s); the cheapest-check-first order in `/recreate-video` and
`/generate-video`; the `new` template's helpers (`set` / `to` / `ft` / `bump` / `smear`) - a snapshot = a plain
render on all 75 frames of the test graphic, motion blur = plain wherever nothing moves - with sound cues for
`tools\sfx.py`; Claude's memory starts with the user's ratings of all their videos as rules (`knowledge.ratings()`);
lessons on making videos (`.claude\skills\recreate-video\lessons.md`, M001-M004; `next-lesson-id --kind making`;
shared as `incoming\*-making.md`, released like cards). Measured: snapshots and renders differ only in edge
anti-aliasing after a jump (<= 0.5 % of pixels), as much as two renders with different worker counts do. Open: items
2, 3, 4, 8, 9; the app's memory page doesn't show the rules / M lessons yet; the next generated video is the test of
*Ships when* (illdari_test_copy_2_fable_high still went straight to a motion-blur render, ~26 min).

1. **Cheapest check first** (Edit and Generate): (1) the plan in words and numbers - the scenes with frame +
   timecode, the feel as numbers ("a cut every 0.5 s, moves over 4-6 frames, a whoosh on each") - seconds;
   (2) a sheet of stills at every scene change - seconds; (3) the motion: a quick draft (Edit already has one) or a
   plain render (~2 min for 25 s); (4) the final with the polish (motion blur, sound
   mix, Resolve) - once. The user approves each step in plain words; no polish before step 3 is approved. Needs
   `overlay.py snap <folder> <frames>`: HyperFrames' `snapshot` at those frames' times, frame + timecode burned in,
   no render (stills today come from a finished render). Snapshots seek straight to a time, so they match the render
   only with the helpers of item 7. (0.5.0 adds an animatic and the live preview to step 3.)
2. **Feel tests when starting blind** (no reference, only words): first try to stop being blind - Claude suggests the
   analysed videos closest to the words (Claude's memory, `style.py`); one analysed reference in the right feel
   turns guessing into measuring. Otherwise 2-3 hooks (the first 3 s) in different feels, e.g. clean and slick / raw
   and glitchy / slow and cinematic: Edit = quick drafts with different presets or seeds and `--length 3` (made by
   rules, no Claude tokens); Generate = the hook as stills in 2-3 looks (costs Claude tokens: only when there is no
   reference and the words are vague). The user picks or mixes ("B's pacing with A's colours") - that is the plan.
3. **Fix this version, or start over**: *How did it turn out?* asks which one. Fix = a new version with the notes
   (the feel is right, details are wrong); start over = back to step 1 or to feel tests - never a v2 of a feel the
   user did not want.
4. **Notes on moments**: a render's page takes a note on any moment, like the review page takes verdicts (frame +
   timecode, saved with the ratings in `build\outcome.json`); `/recreate-video improve` fixes exactly those moments
   instead of interpreting one word per part.
5. **Your ratings as rules**: Claude's memory (`knowledge.py memory`, read before every edit and generated video)
   gets what the user rated in all their videos; a part rated bad becomes a default for every later video (no sound
   effects rated bad -> sound effects always). Today only the ratings of videos from the same reference are read.
6. **Lessons on making videos**: a shared, reviewed file of their own (`.claude\skills\recreate-video\lessons.md`,
   ids M###), read by `/recreate-video` and `/generate-video` - not the analysis lessons file, which the analysis
   reads whole every time. Same flow as the analysis lessons (local -> incoming -> reviewed; `knowledge.py share`
   and `next-lesson-id` learn the second kind). First entries from this rebuild: draw at the reference's measured
   size; sound effects levelled against the song under each; with motion blur, tweens end half a frame early and
   their start pose is set at AT(n); moves over ~60 px a frame need a smear.
7. **A starter graphic that is safe by default**: `overlay.py new`'s template gets the helpers of
   `kidwild_top3_v2` (tweens end half a frame early, start pose set early, a vertical smear, a camera bump), so a
   new graphic renders the same with or without motion blur and in snapshots.
8. **Ask about sound in the review**: Claude cannot hear, so an analysis asks the user "sound effects: none / some /
   many - where?" like a possible miss; the rebuild reads the answer.
9. **Checks before the final render** (scripts on a plain render or snapshots, no guessing): frames where most of
   the picture vanishes for 1-2 frames (the f38 badge), the fastest moves in pixels per frame (a smear above ~60),
   every sound effect's level against the song. Sizes against the reference stay Claude's check on its frames.

**Moved to 0.5.0** (2026-10-14, the content generation version): sound effects as a lab tool (`tools\sfx.py`, was
item 8 - shipped early in 0.4.1.1, see 0.5.0 step 4), the live preview in the app (11), faster motion blur (12) and the
templates (13, now *formats*). What stays here is the check-first way of working for every video, Edit and Generate
alike; 0.5.0 builds on it.

**Order** (the user decides): 1, 7, 5, 6 first (rules and small changes - shipped in 0.4.1.1); then 3, 4, 8 (the
app); 9. **Built 2026-10-14** (night, Unreleased; the user: "plan the next version for 3 sub-agents"): every item.
The app (API 17): notes on moments under every render (outcome.json `moments`, frame + timecode, click to seek),
*What next?* fix / start over (outcome.json `next`), the sound question on every analysis (verdicts.json `sound`,
exported and parsed by feedback.py, `--import`, a line per video in Claude's memory, MCP `verdicts()`), the memory
page's rating rules and M lessons. `tools\precheck.py`: illdari v1's f38 (00:00:01:08) gap flagged, the f113-f116
move at its fastest frames f115-f116 (00:00:03:25-00:00:03:26), 90-121 px a frame, on plain snapshots; on v2's
motion-blur render 7 move runs, 6 real copies, 1 false alarm (a repeating pattern, f547-f549), the drop hit f157
(00:00:05:07) 7 dB under its level; 16-17 s per minute (41 s on 4 logical CPUs). Feel tests: `style.py closest
"<words>"` (analysed videos ranked by measured style, reasons in numbers) and `draft_edit.py --feel-test` (2-3 hooks
of 3 s side by side, test_4am 9.7 s cold / 5.2 s warm, no Claude), `--feel <id>`. Both skills teach starting blind,
notes on moments, fix or start over, the sound answer and precheck. Self-test: feels, precheck. Open for *Ships
when*: the next generated video made this way (one final render).
