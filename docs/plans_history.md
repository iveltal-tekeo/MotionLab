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
| The interface overhaul (0.4.3.5) | none (released 2026-10-15: the Editor overhaul, Film it, simpler Analyser / Prepare / Generator pages, a new player) |
| What it took - Claude's time (0.4.4) | 0.4.5.5 for a few hours (2026-10-15 evening); its measuring was 0.5.0's step 0 |
| Bulk - thumbnails, videos, edits at once (0.4.5) | none (added 2026-10-15 night; 0.4.5 was *Trending sounds* that evening - scrapped) |
| Fonts and customizations (0.4.6) | none (added 2026-10-15 night; released 2026-10-16) |
| Yapping mode (0.4.7) | 0.4.0 (until 2026-10-13), 0.4.4 (2026-10-13 to 2026-10-14), 0.4.5 (2026-10-14 to 2026-10-15) |
| Faster videos (0.4.8) | none (added 2026-10-15 night; earlier that day 0.4.8 was colour's number) |
| Prompt generator (0.4.9) | 0.4.1 (until 2026-10-13), 0.4.5 (2026-10-13), 0.4.3 (2026-10-14), 0.4.4 (2026-10-14 to 2026-10-15), 0.4.6 (2026-10-15) |
| Motion graphics (0.5.0) | none (added 2026-10-15 night; it took 0.5.0's number and content generation's graphics steps) |
| Colour (0.5.1) | 0.3.7 (2026-10-12), 0.4.3 (2026-10-13), 0.4.5 (2026-10-14), 0.4.6 (2026-10-14 to 2026-10-15), 0.4.8 (2026-10-15) |
| Content generation (0.5.2) | 0.5.0 (2026-10-14 to 2026-10-15); "0.5" before that meant templates by feel + macOS |
| Describe video + courses (0.6.0) | 0.4 (2026-10-09), 0.6 (2026-10-11), 0.3.5 (2026-10-12), 0.4.2 (2026-10-13), 0.4.7 (2026-10-14), 0.8.0 (2026-10-14 to 2026-10-15) |
| Templates by feel (0.6.5) | 0.5 (with macOS, 2026-10-07 to 2026-10-14) |
| AI B-roll and cinematics (0.7.0) | 0.7 |
| macOS (0.7.5) | 0.5 (with templates by feel, 2026-10-07 to 2026-10-14) |

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
- **2026-10-15** (the user, after 0.4.3): the Editor overhaul, Film it and a simpler Analyser / Prepare / Generator
  (renamed from Analyze / Generate) with a new video player ship as **0.4.3.5**; a new **0.4.4** = *What it took*
  (Claude's minutes and tokens per step of a video, a live panel while Claude works; 0.5.0's step 0 *Measure first*
  moved into it); every 0.4.x plan two up: prompt generator 0.4.4 -> **0.4.6**, yapping mode 0.4.5 -> **0.4.7**,
  colour 0.4.6 -> **0.4.8**. **0.4.5 stays free** - the user's choice (Claude offered splitting the live panel into
  it).
- **2026-10-15, evening** (the user): **0.4.5 = Trending sounds** - the user's `trending_sounds.py` (TikTok's song
  chart) reviewed and planned into the Editor; What it took 0.4.4 -> **0.4.5.5** (right after it); colour 0.4.8 ->
  **0.5.1** (after content generation). 0.4.4 is free now. 0.5.0 gained step 12, *the clips a script needs*, from the
  user's first talking video made from a Prepare script.
- **2026-10-15, later that evening** (the user: "while i think about the 0.4.5 tik tok thing ... go ahead with the
  claude usage version"): What it took is built first, so it went back to **0.4.4** - the updater installs versions
  in number order, and a 0.4.5.5 released before 0.4.5 would make 0.4.5 look older. Trending sounds stays 0.4.5.
- **2026-10-15, night** (the user, after What it took was built): **Trending sounds scrapped** ("forget about 0.4.5
  trending sounds, scrap that version entirely"). It had been planned that evening from the user's
  `trending_sounds.py` (Playwright on TikTok Creative Center's song chart with a TikTok Business login, YouTube MP3s
  through yt-dlp, a Windows scheduled task); Claude's review found, among others: a response filter on "music" that
  may miss the chart's `popular_trend/sound` request, `networkidle` timeouts without the debug screenshot, `python -m
  yt_dlp` failing inside the lab's Python, unchecked YouTube matches (covers, sped-up versions), history mixing
  countries and periods, a scheduled task downloading songs nobody asked for. The file stays at the repo root,
  untracked. New **0.4.5 = Bulk** (thumbnails analysed on their own as sets, videos and edits in bulk, the time known
  first - "now that we have the cost/usage of claude"); prompt generator 0.4.6 -> **0.4.9**; new **0.4.6 = Fonts and
  customizations** for motion graphics and captions; describe video 0.8.0 -> **0.6.0**, with courses added (the user:
  bulk-analysed courses are "a similar idea" - Claude agreed: a course is a collection of long videos analysed for
  what they teach). ideas.md's *background analyses* moved into 0.4.5.
- **2026-10-15, night** (the user, after Claude's review of what a video costs: ~1 min of Claude per second of video,
  the goal 10 min per minute): new **0.4.8 = Faster videos** in the free slot - brief -> plan -> build -> one look;
  the from-zero part stays in 0.5.0's blocks and formats. The user kept the two apart (asked whether to merge them);
  0.5.0's step 7 (faster renders) moved into 0.4.8's step 3, and 0.5.0 builds on 0.4.8's brief and build command.
- **2026-10-15, night, again** (the user asked where a motion-graphics version would fit - "a lot of free templates
  from some courses ... the motion graphics by default are very dull" - then, to Claude's proposal, "yeah go ahead"):
  **0.5.0 = Motion graphics: learned from pro templates** - new steps 1-4 (template packs in, read exactly, motion
  cards and rules, templates used as they are) and 10 (the motion check); its benchmark stays illdari's "top 3
  tracks" reel, now rated *good*. The rest of content generation -> new **0.5.2**; colour stays 0.5.1. 0.5.0's old
  step numbers: 1 building blocks -> 5, 2 formats -> 6, 3 quick draft for Generate -> 7, 4 sound effects -> 8 (code
  comments say "0.5.0 step 4"), 5 voice and music -> 0.5.2's 1, 6 preview -> 9, 7 faster renders -> 0.4.8's step 3,
  8 AI clips back into the lab -> 0.5.2's 2, 9 three sizes -> 12, 10 other tools -> Lottie in step 4 and image tools
  in 0.5.2's 3, 11 the made video's page -> 11 (kept in 0.5.0: it shows the scene table and the animatic), 12 the
  clips a script needs -> 0.4.7 (*Make*'s step 3 B-roll slots are that list).

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
  0.4.3, then 0.4.4, now 0.4.6.

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

### 0.4.6 - released 2026-10-16 - Fonts and customizations for motion graphics and captions

**Ships when**: a graphic's or the captions' font can be any of ~30 curated free fonts shipped with MotionLab (the
same render on every PC) or a font file the user adds; a caption style (font, size, colours, outline / shadow, the
word being said highlighted, position in each platform's safe area, the animation) is saved as a preset and used in a
new video in one click; the same fonts work in thumbnails and in DaVinci Resolve.

**The user's words (2026-10-15)**: "make 0.4.6 motion graphics/captions oriented -> 'fonts and customizations for
motion graphics'".

**Where it stands**: graphics, captions and thumbnails are HTML (HyperFrames) with settings the user can change
(*Editor > a video > Graphics*, *Ready to post*'s thumbnails); their font is one of five Windows fonts (Arial Black,
Impact, Segoe UI, Verdana, Georgia) - nothing bundled, so another PC (or the Mac version, 0.7.5) can render
differently, and there is no caption style to keep between videos.

Claude's proposal (the user picks):
1. **A font library**: ~30 free fonts under the SIL Open Font License (Google Fonts - e.g. Anton, Bebas Neue,
   Montserrat, Poppins, Inter, Oswald, Archivo Black, Bangers, Permanent Marker; picked by what analysed videos and
   0.4.5's thumbnail sets use) shipped in `tools\overlays\fonts\` with their licences and loaded by every graphic with
   `@font-face` (a render never depends on what Windows has); the user's own font files in `library\fonts\` (private:
   a bought font's licence is the user's); a preview of each with the user's own words.
2. **Caption styles**: the captions example's settings grown into presets - font, weight, size, capitals, colours
   (text, the word being said, outline, shadow, box), the highlight (colour / size / pop per word), words per line,
   the position and the platforms' safe areas (TikTok / Reels / Shorts buttons), the entrance - saved, previewed as
   stills in seconds (`overlay.py snap`), shared through the repo like the examples.
3. **Like a reference**: an analysed video's captions and text on screen measured (0.4.7's text on screen: size,
   position, capitals, colours) and the font's style named by Claude with the closest library fonts -> "captions like
   <video>"; the same for 0.4.5's thumbnail styles.
4. **Everywhere**: one font and preset across graphics, captions, thumbnails and the DaVinci Resolve build (Fusion
   text needs the font installed in Windows - measured first; installed only on the user's click).
**Decided 2026-10-15 (the user, after the choices made while 0.4.5 was tested)**:
- **The fonts** = the user's own `fonts\` folder at the lab's root (25 families, 10.5 MB, with a `fonts.css`; checked:
  24 SIL OFL 1.1 + Luckiest Guy Apache 2.0, the licence file and the font's own licence field agree, embedding
  unrestricted, each with its licence file) + from the suggested first 12 the three it lacks: Nunito, Permanent
  Marker, Space Grotesk (the helper's verified OFL copies). The candidates and specimen sheets of 32 fonts stayed on
  this PC (Claude's scratch). Open: 11 of the 25 are variable fonts only - whether DaVinci Resolve's text tool uses
  every weight of a variable font is to be measured before the Resolve part relies on them.
- **The first caption preset** = *Clean box* (sentence case on a rounded dark box, the word being said in an accent
  colour, a fade; Poppins 600 in the mock-up) - the box fits its longest line. Mock-ups of six styles on the user's
  talking video (f2 (00:00:00:02) of testing_entire_workflow_v3) showed: presets need their own position per
  orientation (today's captions sit in the 9:16 apps' bottom zone), ads need a higher position than ordinary posts,
  and the face detector the thumbnail check has can keep captions off the face.
- **Added: a measured font match for thumbnail sets** - the words on a set's thumbnails compared by shape with the
  bundled fonts; the best one (with its score) is what *In the style of* uses instead of Claude's guess. Measured on
  the Clavero set: Claude guessed Montserrat, the best match is Inter (0.89 vs 0.71 in the first try; the built
  tool, 14 texts read off 10 pictures: Inter 800 0.82, Rubik 0.77, Montserrat 0.74).

**Built 2026-10-15, released 2026-10-16**:
- The font library: `fonts\` (28 families: the user's 25 + Nunito, Permanent Marker, Space Grotesk) + the user's own
  fonts in `library\fonts\` (private, listed first); `motionlab\fonts.py` + `tools\fonts.py`; every font setting of
  the shipped designs (captions, talking-head pack, thumbnails outline / block / split) offers the library, the
  Windows defaults moved to Archivo Black / Anton; a render / snapshot copies the fonts it uses into the graphic.
- The app: every font setting lists the library by what it suits with a line in the picked font; **a live preview**
  of every graphic on a video's Graphics tab (its own HTML in the page: a change shows at once, before Save / Render;
  frame slider + play); **looks** *Classic | Clean box* in one click, captions made before 0.4.6 take the new design
  (words and settings kept, the old design kept in `_before\`).
- Captions: *Clean box* (`--preset clean_box`; the box fits the longest line, sentence case, cyan word, fade, its own
  height for upright videos) + *Classic* (today's look, pixel-identical: 0 differing pixels at 5 frames x 2 sizes);
  new settings: entrance (fade), weight, capital at the line start, box corners / padding, line spacing, even lines,
  height for upright videos.
- Thumbnail sets: `thumbsets.py fontmatch <set>` (~2 s; Claude lists the added words + boxes in style.json "texts",
  `/analyze-reference thumbs` runs it), *In the style of* uses the measured font, the set page shows it.

**Still open when it shipped** (kept in ideas.md, *Left from 0.4.6*): (1) DaVinci Resolve - Fusion's text needs the font installed in Windows, and 11 of the 25 families
are variable fonts only: measure what Resolve does with them before the Resolve part relies on them (plan item 4);
(2) a caption look the user saves from their own settings (only the shipped looks exist) and more looks from the
six mock-ups; position by platform / keeping captions off the face; (3) "like a reference" (item 3) - waits for
0.4.7's text on screen; (4) Clean box in a full render - checked before the release (2026-10-16: a
90-frame render, the box fits each line in the render too, the said word cyan); (5) the real Clavero set has no "texts" yet - Claude adds them when it finds the patterns again.

**Needs first**: nothing (0.4.5's thumbnail styles name their fonts from this library once it exists). **Size**: M.

### 0.4.5 - released 2026-10-15 - Bulk: many thumbnails, videos and edits at once

**Ships when**: 15 thumbnails from a channel link (no video downloaded) are measured and their common patterns named
by Claude in one window (colours, the text's words, size and font style, faces, layout) and saved as a *thumbnail
style* that *Ready to post* and `/write-title` use for the user's own thumbnails; a batch of ~10 videos gets Claude's
check in ONE Claude window instead of ten; before any batch starts the app says how long it should take (0.4.4's
measured time per step), and a batch that stopped half way continues where it stopped.

**The user's words (2026-10-15)**: "lets make the 0.4.5 about working in 'bulk' now that we have the cost/usage of
claude tokens and pacing ... 1) i want to be able to analyze only thumbnails, like I give 15 thumbnails from mr beast,
it analyzes them and then sees common patterns like font, color, structure etc etc. and then that information can be
used when im generating a thumbnails for my videos as well. 2) id also like to bulk analyze thumbnails, videos, and
also bulk edit stuff or generate. 3) and maybe in the future maybe bulk analyze courses? ..." (courses -> 0.6.0,
describe video; built on this plan's batch runner).

**Built 2026-10-15 (Unreleased)**, steps 1-4 and 6 (the user: "go ahead with the planning 0.4.4 to 0.4.5, I will
release and test when I see fit"):
- **Thumbnail sets** - `motionlab\thumbsets.py` + `tools\thumbsets.py fetch | links | add | measure | sheet | list | show
  | remove-item | selfcheck` (30 checks, no network): a channel link -> its newest N videos' thumbnails, titles, views
  and the channel's followers (yt-dlp `--flat-playlist`, no video), measured with the thumbnail check's own parts
  (look, YuNet faces, the text estimate, palette; 4:3 bands cut off) -> `analysis\thumbs\<set>\` (set.json, img\,
  numbered sheets of 15). Measured on this PC: MrBeast, 15 thumbnails in 4.1 s (measuring 0.7 s). The same night (the user: "why stop at
  the newest? ... I could choose to download other 20/30 batch"): the WHOLE channel is listed once and kept in
  set.json (Clavero 246 videos in 3.5 s, MrBeast 804 in 10.3 s, views included); the first batch is the newest or the
  most viewed, then `thumbsets.py more <set> --n 20 --order newest|views` / *More from the channel* (job thumbs_more;
  10 more in 1.9 s from the kept listing, listed again when a day old). Not all at once by default: Claude reads 15
  pictures a sheet, so a set's size is Claude's time - the dialog says the sheets first. Each picture: views, views ÷
  followers, its length and its EXACT date (yt-dlp per video in the set, 3 at a time: 30 videos in ~35 s; the
  listing's approximate dates, "≈ 3 weeks ago", until then). Claude:
  `/analyze-reference thumbs <set>` (skill section *Thumbnail sets*) writes `style.json` (patterns with how many and
  the picture numbers, the font's style + closest fonts + "sure", colours, words, structures, `for_make`). App: the
  Analyser's *Add thumbnails* + *Thumbnail sets* cards, a set's page (#/thumbs/<set>: the patterns with Correct /
  Partly / Wrong -> `verdicts.json`, the measures, every picture), Delete = Recycle Bin. **Use the style**: *Ready
  to post* > *In the style of <set>* -> `thumbnail.py make --style <set>` (the set's design, colours, the closest of
  today's five fonts, capitals) and `check --style <set>` (the look against the set).
- **Videos in bulk** - *Add videos* (2+ videos, Claude's check) opens ONE window when the batch's last job ends
  (`/analyze-reference batch <id>`, `.app\batches\<id>.json`, skill section *Batch*); the estimate first (GET
  `/api/estimate`: the median minutes per video of What it took on this PC - 16:33 min for Claude's check now);
  *Continue the batch* rows; What it took splits a batch window per video by the folder each tool call named
  (`usage.split`, a sample with known answers in the self-check).
- **Edits in bulk** - *Editor > Edit several videos* (2-10 videos, one style): quick drafts (queued, no Claude) or
  one window `/recreate-video batch <id>` (skill section 7). Bulk generation waits for 0.5.0's formats.
- **Not built**: step 5 (Claude Code without a window) - it spends the plan unwatched, so it waits for a measured test
  and the user's go; the font names stay among today's five design fonts until 0.4.6's library.

**Before it was built**: *Add videos* queues up to 10 videos (links download first) and "Claude checks each video" opens
one Claude window per video when its measuring ends - ten windows for ten videos. Thumbnails: `content.py thumbnail`
saves an analysed video's own thumbnail, `thumbnail.py refs` measures them per niche (brightness, saturation,
faces...) and `thumbnail.py check` judges the user's against the niche's outperformers - but only for videos analysed
in full, one at a time, and without what only eyes see (the font's style, the structure, the story of the picture).
0.4.4 measures Claude's time per step on this PC (the illdari check: 7:00 min). ideas.md's *background analyses* (Claude
Code without a window, a limit per batch) moved here.

1. **Thumbnails only** (point 1): *Analyser > Add thumbnails* - a channel or playlist link (yt-dlp lists its newest N
   videos and saves only their thumbnails, titles and numbers - views, the channel's followers; no video
   downloaded), single links, or image files. One set per folder (`analysis\thumbs\<set>\`, e.g. "mrbeast"). The lab
   measures every picture (no Claude, seconds): the main colours, brightness / contrast / saturation, faces (how many,
   how big, where, looking at the camera - the YuNet model the thumbnail check has), where the text sits and how much
   of the picture it takes, the layout (thirds, a left / right split), views ÷ followers when known. Then Claude
   reads one sheet of the set (15 per picture) and names what repeats: the text (words, capitals, outline / box, the
   font's style - "heavy condensed sans, white with a black outline" - with the closest fonts of 0.4.6's library; an
   exact font name from a picture is a guess and is said so), the colours, the structure (face + text, before /
   after split, an object and an arrow, a big number), the emotion, what the title adds to the picture. -> a
   **thumbnail style** (`style.json` + the sheet), reviewed by the user Correct / Partly / Wrong, kept in Claude's
   memory (only its numbers and words in shared cards, never the pictures).
2. **Use the style**: *Ready to post* and *Title & thumbnail first* get "in the style of <set>"; `thumbnail.py make`
   takes its colours, font, word count and layout (a template per structure: outline / block / split today, the
   structures the sets show most added); `thumbnail.py check` judges against the set as well as the niche;
   `/write-title` reads the style when it writes the concepts.
3. **Videos in bulk** (point 2): *Add videos* keeps queuing the measuring as today; Claude's check of the whole batch
   runs in ONE window (`/analyze-reference batch <videos>`: video by video, each review.json written before the
   next) with the estimate first ("10 videos ≈ 1 h 10 min of Claude - your plan's limit may pause it") and progress
   per video on the live line (0.4.4: "video 3 of 10"). If the window stops (a limit, closed), *Continue the batch*
   starts at the first video without a review.
4. **Edits and videos in bulk** (point 2): one style for several of your videos (a quick draft for each - no Claude,
   minutes - then one Claude window refines them in turn); several videos from one format (0.5.0's formats: five
   "top 3" reels = five sets of settings) - the batch runner is built here, 0.5.0 fills it.
5. **Without a window, measured first** (from ideas.md): Claude Code without a window (`claude -p`) for long batches,
   only if a test shows it is reliable on Windows and keeps to a limit the user sets per batch; a window stays the
   default (you see it work and can stop it).
6. **The time first, the time after**: every bulk button shows the estimate from 0.4.4's own numbers (the median
   time of the same step on this PC; "not measured yet" until there is one); after the batch, *What it took* for it.
**Order**: 1-2 (thumbnails) first, then 3, then 4-6. **Needs first**: 0.4.4 (released). **Size**: L, ships in parts.
**Rules**: other people's thumbnails and videos stay on this PC - only a style's numbers and words are shared; copy a
style, never a design, a logo or a face; light and tested first (the thumbnail measures are numpy on small pictures).

### 0.4.4 - released 2026-10-15 - What it took: Claude's time, step by step

**Ships when**: a 1-min talking video made from a Prepare script to *Ready to post* shows its whole breakdown on its
Overview - every Claude step and every job, with minutes, tokens, model and effort, and the total - and the totals
match the Claude Code session logs on a hand check (within 1 %); the live line follows a running `/recreate-video`
from its first answer to its last.

**The user's words (2026-10-15)**: "0.4.4 a 'breakdown' oriented version: when i mean breakdown i mean to have more
concrete information about the process regarding claude usage. so if i run a claude /analyze-video or /recreate i
want to see if its a way to show that process in motion lab? to have a breakdown on time Claude spent and tokens
used? also, if i get a new video rendered in the Editor and click the Overview i want a new section below 'ready to
post' on the side bar called 'What it took' or something similar that will tell me the entire process kinda like a
timeline from up to top, so if the video is from a generated prompt ('Made from the script MotionLab vs other AI
editors') in the prepare section i want it to tell me (Prepare Transcript) X minutes it took claude to come up with it
and cost u X tokens with this model (Opus 5.5 xhigh e.g) (Edit Video) ... X minutes ... TOTAL SPENT: X minutes and X
tokens ... something i could understand see ok a 1-min talking head video from start to finish it took 1 hour of
claude usage."

**Built 2026-10-15 (Unreleased)**: steps 1-5 - `motionlab\usage.py` + `tools\usage.py sessions | project | analysis |
check | selfcheck`, `data.took` / `prompt_took` / `live_claude`, GET `/api/took/<project|analysis|prompt>/<name>`,
the heartbeat's `claude` list (API_LEVEL 24), jobs recorded in `.app\jobs\history.jsonl` when they end. Measured on
this PC's 28 logs (425 MB): read in 0.9 s, the big request copies skipped unparsed; the heartbeat stays ~1 ms. What
the logs taught: (a) minutes = Claude Code's own `turn_duration` per turn (lines sorted by time; local commands like
/effort are no turns); (b) attribution per **round** (a prompt and its answers), not per session - the app's window
"MotionLab script req-002" wrote the script in round 1 (1.9 min, tagged `write-script`) and then built Film it in
the same window (13 min, untagged): only round 1 counts, the rest is listed as "not counted"; work after /clear in a
named window is never counted; a background task's notice continues the round before it; (c) `cost-state` notes are
per run of the program and sometimes missing, so they are only the hand check: output tokens agree within 0.06 % for
every session the app opened (`usage.py check`); cache reads are 0-7 % lower than the note because Claude Code's own
side calls (the auto-mode permission check, Haiku page summaries) are not answers in the log - left out, said so.
The first talking video (*testing_entire_workflow*): Prepare 1.9 min · 1.3 M tokens · Opus 5.5 high, Edit 38.5 min ·
8.7 M · Fable 5.1 high = 40 min, 10.0 M tokens. **Then the user (2026-10-15, after seeing it): "the tokens stuff is
kinda wrong so lets just scrap that idea as well, just say the time it took"** - and "what is 1.4 min? 1:40 minutes?
or 1:25?": the app shows **time only**, as the clock shows it (45 s · 1:54 min · 1 h 05 min); no tokens on any page
(the headline mostly counted Claude re-reading its own conversation from the cache - true, but it says little). The
reader still counts tokens, only for `usage.py check`, which proves the logs are read right. Steps 3-5's token parts
are dropped. **Not built**: step 6 (*Your plan*) - the "% of a 5-hour window"
needs the measurement it describes, and the user does not need "$"; no setting without an effect. Jobs before
0.4.4 were never recorded (their logs are overwritten when the app restarts) - the page says so.

**Before it was built**: nothing shown. 0.5.0 had this as its step 0 (*Measure first*, generated videos only); it
moved here on 2026-10-15 and covers every video and every Claude task, and 0.5.0 judges its steps by these numbers.
The data is already on the PC (checked 2026-10-15):
- Claude Code writes every session to `%USERPROFILE%\.claude\projects\<lab>\<session>.jsonl` (`<lab>` = the lab's
  path with ':' and '\' as '-'; this PC: `C--MotionLab`), one JSON line per event. Subagents:
  `<session>\subagents\agent-<id>.jsonl` (lines marked `isSidechain`) + `agent-<id>.meta.json` (type, description,
  model, effort).
- The app names every session it opens (`--name "MotionLab <task> <object>"` -> a `custom-title` line): "MotionLab
  script req-002", "MotionLab recreate illdari_test_copy_1", "MotionLab generate <video>", "MotionLab review <video>".
- Every answer carries its `timestamp`, `message.model` (`claude-opus-5-5` ...), `effort`, `attributionSkill`
  (`write-script` ...) and `message.usage`: `input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`,
  `output_tokens`. One answer is written as several lines (one per content block) with the same `message.id` and the
  same usage - it counts once (a session of 2026-10-15: 179 lines, 83 answers).
- The app's own jobs (quick draft, renders, thumbnails, analyses) keep their start and end in `.app\jobs\`.

1. **The reader** (`motionlab\usage.py`, read-only, standard library, nothing leaves the PC; cached per log file size
   + time): every session -> its task + object, start and end, **active minutes** (the time between its events, gaps
   over 5 min left out - a window left open overnight is not work; the wall time kept beside it), tokens (new input,
   cache written, cache read, output), model(s) + effort, the skill. Subagents add to their session and are listed
   under it with their own model. A session started by hand (no name) is matched by its skill (`attributionSkill`)
   and the object in its first message (`/recreate-video ... <project>`). A line it does not know is skipped and a
   number it cannot read says "not measured" - never a guess (the log format is Claude Code's, not a public API).
2. **Sessions -> videos**: a script request (`req-NNN`) -> the script it wrote (`"request"`) -> the videos made from
   it (`made_from.json`, kind prompt); `recreate` / `generate` / `title` (the package) / `improve` by project;
   `review` / `feedback` by analysis; `prompt` / `script` by prompt id. Jobs by the project or analysis they ran on.
   One call returns a video's whole chain in time order: Prepare -> film -> edit -> package -> improve.
3. **What it took** on a video's Overview: an entry in the side index under *Ready to post* -> a section at the end
   of the page, a timeline from the top: one row per step in words ("Prepare - the script *MotionLab vs other AI
   editors*", "Quick draft", "Edit with Claude", "Thumbnails", "Review and improve") with when, minutes, tokens and
   "Opus 5.5 · xhigh"; jobs as their own rows (minutes, "no Claude, no tokens"); then **Total**: Claude's minutes, the
   jobs' minutes, the tokens, the sessions - "this 1-min video took 58 min of Claude and 12 min of renders". Tokens:
   one headline number (everything the model read and wrote), the split in plain words folded ("new 12 k · read
   again from the cache 1.2 M · cached 85 k · written 9 k").
4. **The same for an analysis** (Analyser > a video > Overview: what measuring and Claude's check took) and one line
   on Prepare's script and title cards ("written in 6 min · 240 k tokens").
5. **Live** (the user: "if i run a claude /analyze-video or /recreate i want to see ... that process in motion lab";
   2026-10-15: "minimalistic, straight to the point, do not overuse pc resources and 100% sure it doesn't use extra
   tokens"): ONE line, no panel - "● Claude is working on *testing_entire_workflow* · 12 min · 1.2 M tokens · reading
   the contact sheets" - on that video's (or analysis') page and in the sidebar's status corner, gone when it stops.
   - **Light**: the server reads only the bytes added to the log since its last read (a file offset - never the whole
     file again), only for sessions the app opened (named "MotionLab ..."), every 5 s and only while the app's window
     is open (the heartbeat) and the log grew in the last 2 min; nothing runs otherwise. No new process, no watcher.
   - **Zero extra tokens, by design**: MotionLab only reads files Claude Code writes anyway. It never sends anything to
     Claude Code - no hook, no status line, no MCP call, no message - and never starts or steers a session, so the
     session's context and its token count are exactly the same with the line on or off. The self-check proves the
     reader opens `.claude\projects` read-only and the app has no route that writes there.
6. **Your plan, Pro by default** (the user, 2026-10-15: "more people won't be on Max, so default it to the Pro plan but
   have options for Max users"; a "$ at API prices" line does not matter to them): Settings > Claude Code > *Your
   plan*: **Pro** (the default), Max 5×, Max 20×, or API (pay as you go). Everyone sees minutes and tokens. Pro and Max
   users care about their limit: "about N % of a 5-hour window on Pro" - the logs do not carry the plan's limit and
   Anthropic does not publish limits as token counts, so this line comes only after a measurement (Claude Code's own
   usage readout before and after a known session, on Pro; Max 5× / 20× = 5 / 20 times Pro, as the plans are sold),
   kept in one dated table with its source; until then the line is left out, never guessed. API users see "≈ $X"
   from a dated price table.

**Needs first**: nothing - the session logs and the names the app gives its sessions exist on this PC. **Size**: M.
**Tests**: fixed sample logs in `tools\dev\` (a named session, a session started by hand, subagents, a repeated
answer) for a self-check and `smoke.py`; one hand count against a real session before it ships.

### 0.4.3 - released 2026-10-15 - Title + thumbnail: packaging for clicks (horizontal and vertical)

**Ships when**: for one of the user's videos, 10 titles and 3 thumbnails (16:9 and the 9:16 cover) land in a
ready-to-post folder and pass the thumbnail check, whose rules have self-test cases with known answers.

**The user's words (2026-10-14)**: "un apartado de miniatura ... que tuviera opción tanto vertical como horizontal,
creo que la miniatura también es de lo más importante ya que: el impacto numérico: CTR (click-through rate) - la
miniatura y el título juntos determinan el CTR. Estaría guay que con Claude pudieras sacar el título y la miniatura
... para que así estuviera completo el vídeo de YouTube, y ayudara a convertir con más visitas."

**Where it goes in the app** (recommended; the user decides):
- **Prepare** gets a third way: **Title & thumbnail first**. Many creators decide the packaging before they film, so
  the video delivers what the title promises. Claude writes about 10 titles in different patterns and 2-3 thumbnail
  concepts, each with a sketch in words, the 2-4 words on it, and **the shot to film for it**. The hook of the script
  (`/write-script`) has to agree with the title: what they clicked for, they get in the first 3 s.
- **Edit > a video > Publish** (a new tab on the finished video, no new sidebar item) makes the final package:
  - the thumbnail **16:9** (1280×720) and the **9:16 cover** (1080×1920, with the 4:5 / 1:1 grid crops marked)
  - the title
  - the description with chapters from the edit or the transcript (YouTube's `0:00` format in the text; the app
    shows frame + timecode next to each)
  - hashtags
  All of it goes in a ready-to-post folder `build\publish\`. Check each platform's current cover / thumbnail options
  when building, because they change.

**How a thumbnail is made** (two routes, both end in the same check):
1. **From your own footage** (free, local): the lab picks candidate frames (sharp, still, well lit, and a big subject
   if a cheap detector proves good enough). Claude looks at them as a contact sheet and picks the expression or the
   moment. The design is an HTML template (the 0.3.2 graphics pipeline, rendered as a still): big text, outline /
   shadow, a colour block. Its settings stay editable in the app like any graphic. Cutting the subject out needs a
   background-removal model (rembg is ~170 MB). Measure it on an ordinary laptop first, or go without it
   (the lab's rule: light and tested first).
2. **With an AI image tool**: Claude writes the image prompt (kind `image` in the prompt library: Nano Banana / GPT
   Image, your photo as the reference). You make it on the site and bring the picture back; the lab adds the text
   and runs the check.

**The thumbnail check** (no Claude, like the script check):
- the thumbnail shown at the size of a phone feed: is the text still readable?
- 2-4 words, at least ~20 % of the height
- text / background contrast (WCAG ratio)
- the subject's share of the frame
- brightness / saturation compared with the outperforming videos of your niche (below)
- the title's length on a phone (rule of thumb ~50-60 characters before it is cut)
- the thumbnail text doesn't repeat the title
- the title's promise shows up in the script's first 3 s

Claude makes **3 variants** for YouTube Studio's own A/B test ("Test & compare"; check its current limits).

**Learning what gets clicks**:
- From references: downloads also keep the video's thumbnail (yt-dlp `--write-thumbnail`) into
  `analysis\<name>\content\`. The title is already in `refs\downloads.json`, and the outperformer score (views ÷
  followers) in `content\stats.json`. The lab measures cheaply: colours (colour.py's palette), contrast, brightness.
  Claude describes the composition (face, expression, text, arrows). The result is "packaging that worked" per niche
  in Claude's memory, outperformers first.
- From your own videos: CTR lives in YouTube Studio, and the lab never logs into accounts (no tokens). After posting,
  you type in the CTR per variant (or paste a screenshot), and the public views come from `content.py stats` with the
  link. It is saved with the video's *How did it turn out?* (a new aspect: packaging), and Claude repeats the
  patterns that won.

**Needs first**: Prepare (built 2026-10-14). The graphics pipeline exists (0.3.2). The content foundations (0.4.5, now 0.4.7)
and describe video (0.8.0) make the "what worked" part better later; it works without them. **Size**: medium.
Order: Prepare's concept card + titles first (text only), then the Publish tab from your frames, then the AI-image
route, then learning from references.
**Started 2026-10-15**, in two phases: (1) next to 0.4.2.1 - the thumbnail engine (`tools\thumbnail.py`:
candidates, HTML templates for 16:9 + the 9:16 cover, the check, reference thumbnails via `content.py`) and the
packaging (`/write-title` skill, prompt-library kind `title`, title requests, `tools\publish.py`: description,
chapters, hashtags); (2) after 0.4.2.1 ships - the app (Prepare's *Title & thumbnail first*, Edit > a video >
*Publish*). The shared file: `build\publish\package.json` (each tool updates only its own keys).
**Phase 1 built 2026-10-15**: `tools\thumbnail.py` (candidates, 3 templates in `tools\overlays\thumbnails\` rendered at
1280x720 + 1080x1920, the crops preview, the check - selfcheck every rule PASS / FAIL with known answers, `refs`);
`content.py thumbnail`; Claude's memory "Packaging that worked"; test_4am A / B / C made and checked (no FAIL). The
face detector: OpenCV 5 has no Haar cascades; YuNet (227 KB, MIT) measured 15/15 + 26/29 faces, 8-14 ms a frame ->
shipped in `tools\models\` (the user's choice). Packaging: `/write-title` (request / package / ab), kind `title`,
`script.save_title`, `tools\publish.py` (YouTube's chapter / hashtag / title rules checked 2026-10-15, selfcheck 22/22);
dry run req-001 -> title-001. **Phase 2 (the app) built 2026-10-15**: Prepare > *Title & thumbnail first*
(`script.save_title` -> `/write-title request`), title records in the prompt library (*Use this title* links a
video), Edit > a video > *Publish* (Claude or by hand: candidates, make A / B / C from a frame or a picture, the
check, settings + render again, title, chapters with frame + timecode, hashtags), *How did it turn out?* > Title and
thumbnail (CTR per variant + link in outcome.json `packaging`); API 19. Open: a posted project's public numbers
(`content.py stats` writes into analyses only). Platform notes: Instagram's grid is 3:4 since 2025 (not 1:1), YouTube now recommends
4K thumbnails (1280x720 still accepted), Test & compare = up to 3 variants, desktop only, not for Shorts.

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
