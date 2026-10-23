# MotionLab - planned versions

What comes next and how it plugs into the lab. The app shows these under *What's new* as "planned" (newest plan on
top); a version goes into `CHANGELOG.md` only when it ships (the Update button treats every version heading there as
released). Headings: `## x.y.z - planned - title`. The user decides scope and order - ask before starting a plan.
How the plans got their numbers, and finished measurements: [plans_history.md](plans_history.md) - older notes, chats
and code comments use old numbers; its table says which plan they mean.

**Phase 2** (2026-10-18, the user: "put all of these changes (speed, language, setup...) as a 0.5.5 version that can
be inside a new "phase" called phase 2 of Motion Labs which is the path from 0.5.0 to v1.0.0 deployment!"): Phase 1 =
everything up to 0.5.0.1; Phase 2 = the path from 0.5.0 to **1.0.0** (*Deployment*, the first plan below), opened by
**0.5.1** - the user's changes took the next free number (0.5.5 was the planned colour version, and the Update button
only offers higher numbers), so every planned 0.5.x moved one up (plans_history.md, *Renumbers*, 2026-10-19). The
roadmap shows both phases (`docs\roadmap\roadmap.json` "phases").

**Version numbers**: a new `0.x.0` is a big step (a badge on the roadmap); `0.x.y` adds a smaller feature; a
four-part `0.x.y.z` is a small step between them (fixes, upkeep, polish).
**Each plan**: the user's words, *Ships when* (what has to be true to release it - a number where one exists), the
steps in order, *Needs first*. At most two versions are "next" at a time: finish and release one before starting
another.

## Where it stands (2026-10-22)

**Re-planned 2026-10-23**: 0.5.3 *Faster videos* rewritten from the review of every video made so far (`docs\review_video_time_2026-10-23.md`): the gate is half of Claude's time with the same result and the analysis -> review -> lessons -> memory loop untouched; six parts (A the PC answers what Claude looked at, B one build, C the brief, D the plan as a list, E fewer blind guesses, F the environment), shipped as 0.5.3.1-0.5.3.5, each measured on the re-run of ae_50_test / the two talking test videos. Built the same day: `projects\ae_50_test` v1 (the first video made only from the AE templates), not rated yet.

Built, released when the user pushes it: **0.5.2** (2026-10-22, CHANGELOG.md + CHANGELOG.es.md) - New edit, step
by step (the pop-up's six steps, the clips as pictures, edit_brief.md for Claude), a script's pop-up in three tabs
with its road, a lighter Home and Claude's memory. Its plan text: plans_history.md. Re-planned the same day from the user's notes (plans_history.md,
*Renumbers*): 0.5.4 = Sound, 0.5.5 = Content agency, yapping mode -> 0.5.9; the prompt generator and templates by
feel removed.

Released last: **0.5.1** (2026-10-19, CHANGELOG.md + CHANGELOG.es.md) - Phase 2 opens: the
whole app in Spanish (*Settings > General > Language*; what Claude stores in the lab stays English), analyses in about
half the time and faster pages (the speed audit's kept findings), the one-file install (`Install-MotionLab.cmd`), the
Analyser's three ways with *Scripts & prompts*, *Shared knowledge* in Claude's memory, one review pattern everywhere,
shorter notes for Claude. Its plan text and measurements: plans_history.md. Left for later: the words and the speed
findings in the files the user's other Claude window is changing (2026-10-19; `tools\dev\i18n_check.py` WAITS:
templates.py, overlay_settings.py, overlay.py, looks.py, template_match.py, template_read.py - the Motion Graphics
library's own labels are translated; a template pack's clips decoded 4 times; `/api/motion/pick`'s cache; the overlay
encodes' error text on accented names).

Before it **0.5.0.1** (2026-10-16) - the logo library: 92 app / platform / AI-tool logos for the motion graphics
(`logos\`, `tools\logos.py`), the Logo wall template, *Pick a logo* / *+ Logo*, Motion Graphics > Logos. Before it
**0.5.0** (2026-10-16) - Motion Graphics: 74 templates (57 learned from the Swishy clips, 17 MotionLab originals), the
Motion Graphics page, Generate builds from them; with **0.4.6** (2026-10-16) - fonts and captions. The released plans'
full text: plans_history.md.

Phase 2's planned versions (0.5.1 opened it, 1.0.0 ends it):

| Version | Plan | State | Size |
|---|---|---|---|
| 0.5.3 | Faster videos | **built 2026-10-23, not released** - all six parts (A-F) except F1 (the permission allowlist: the user adds it) and F3 (effort: the user's call after the re-runs); ships when the re-runs halve Claude's minutes with ratings the same or better | M-L, ships in parts |
| 0.5.4 | Sound | planned - recorded sound effects instead of the synthesised ones, music and ambience from public libraries, voice-over (added 2026-10-22; the synthesised effects shipped in 0.4.1.1) | M |
| 0.5.5 | Content agency: My Brand | planned - a My Brand page above the Analyser: goal, audience, identity, the catalogue with prices from the website; used by Prepare, New edit, Motion Graphics; product motion (added 2026-10-22) | L, ships in parts |
| 0.5.6 | Motion graphics: template packs | planned - the library shipped in 0.5.0; Resolve / After Effects / Lottie packs read exactly, templates used as they are, the motion check, formats, a preview before the render | L, ships in parts |
| 0.5.7 | Colour + DaVinci Resolve | planned - measuring a look + the match LUT shipped in 0.4.0 | M |
| 0.5.8 | Content generation | planned - AI clips back into the lab, pictures from image tools (voice and music moved to 0.5.4, 2026-10-22) | M |
| 0.5.9 | Yapping mode | planned - talking quick draft + talking-head pack shipped; starts with the content foundations; + the clips a script needs (from 0.5.0, 2026-10-15) (moved from 0.5.2, 2026-10-22) | L |
| 0.6.0 | Take notes from videos + courses | later - transcripts, numbers, the content panel shipped; courses added 2026-10-15 | L |
| 0.7.0 | AI B-roll and cinematics | later | L |
| 0.7.5 | macOS | later | M |
| 1.0.0 | Deployment | later - the end of Phase 2; what deployment means is the user's call (added 2026-10-19) | - |

## 1.0.0 - planned - Deployment

**Ships when**: the user decides what deployment means.

**The user's words (2026-10-18)**: "... a new "phase" called phase 2 of Motion Labs which is the path from 0.5.0 to
v1.0.0 deployment!" - 1.0.0 is where Phase 2 ends (0.5.1 opened it; the plans below are the path to it). Nothing is
planned for it yet: its scope, its steps and what "deployment" means are the user's to decide - ask before planning
it.

## 0.7.5 - planned - macOS

**Ships when**: setup, the app, an analysis and a lab render work on a Mac, and GitHub's tests pass on macOS too.

- **A macOS version** of the app (the lab is Python + a browser window; Edge-only parts, the Recycle Bin, `.bat`
  files and the Windows paths need macOS twins; DaVinci Resolve's scripting paths differ).
- GitHub's tests run on Ubuntu and Windows today (`.github\workflows\tests.yml`): a macOS run joins them, so the
  Update button only installs what passed there too.

## 0.7.0 - planned - AI B-roll and cinematics

**Ships when**: a shot missing from the user's footage is generated through a provider's API from the analysis'
shot request, its cost shown and approved first, and used in the lab render and the Resolve build with its
provenance saved.

**The user's words (2026-10-09):** "introduction of creation of B-rolls / complementary clips or even full video
cinematics with Higgsfield AI Seedance or other models and implement it with our creation video tool."

- **Goal**: when your footage has no shot for a part of the reference, MotionLab can generate one - B-roll,
  complementary clips, or a whole cinematic sequence - with a video model, and use it exactly like your own clips
  in the lab render and the DaVinci Resolve build.
- **Providers**: one provider-neutral tool, `tools\generate.py`, Higgsfield first (its API is a separate product
  from the website plans: a dollar balance, pay per generation, one key for every model in its catalog incl.
  ByteDance's Seedance 2.x; Python SDK `higgsfield-ai/higgsfield-client`, dashboard cloud.higgsfield.ai), others
  later (Seedance through other resellers, Kling, Veo, Runway...). Checked 2026-10-09: Seedance routes make 4-15 s
  (some up to 30 s) at 480p-1080p (4K on some), text-to-video and image-to-video with start / end frames and
  image / video / audio references; prices seen $0.06-$0.75 per second depending on provider, model tier and
  resolution - re-check live prices and the API reference before building.
- **Shot requests come from the analysis** (`/write-prompt`, shipped in 0.3.1, already writes them as text; 0.7 adds
  the paid API call): for reference shot fA-fB Claude writes the request - length (frames at the plan's fps, rounded
  up to the model's minimum, trimmed in the plan), aspect and size, camera move (measured pan / zoom from
  events.json), light and look (contact sheets + the plan's grade), subject from the user's story. Image-to-video
  starts from a frame of the user's own footage so the look matches.
- **In `/recreate-video`**: step 3 ("where the footage has nothing comparable") offers *Generate this shot* with a
  cost estimate; the user approves each paid generation.
- **In *Generate***: 0.5.8 brings the clips the user made on a tool's site back into the lab (checked against the
  shot list, cut on the beats, graphics and sound on top); 0.7.0 makes the same clips through the API instead of the
  site - the rest stays the same.
- **Files**: `projects\<name>\build\generated\<id>.mp4` + `generated.json` (prompt, model, seed, reference frames,
  cost, date - provenance); registered in `sources.json` as sources G1, G2... with `"generated": true`, cached by
  prep_footage, used in plans like any clip, imported by resolve_build as media. The user's own clips stay
  read-only as always.
- **Costs and keys**: the API key lives only on the PC (settings.json or the Windows credential store, never in the
  repo or in shared knowledge); a cost estimate and an explicit OK before every paid job; a budget per project;
  every spend logged. Generation runs as an app job (group net).
- **Rules**: no likeness of real people without their consent; AI clips are labelled as generated in the project
  and its Resolve timeline; the provider's terms apply.
- **Needs first**: 0.5.8 (AI clips back into the lab); 0.3's colour pipeline (done).

## 0.6.0 - planned - Take notes from videos: videos and courses as information

**Ships when**: a collection of ~10 analysed videos gives its topics with counts and quotes (frame + timecode), each
video's content reviewed Correct / Partly / Wrong by the user like effects, and searchable from Claude; a course of
~10 lessons gives the steps each lesson teaches (frame + timecode, the screen shown) and a course summary Claude
uses when it edits.

**Renamed 2026-10-22** (the user: "Rename 'describe videos' to 'take notes froms videos'"); older notes call it
*describe video*.

**Courses** (the user, 2026-10-15: "and maybe in the future maybe bulk analyze courses? of davinci resolve or courses
on content creation? (i think this is a similar idea we have for the 'describe video' version. what do you think?
so maybe make that instead of v.0.8.0 to 0.6.0, but have the bulk stuff in 0.4.5 so it links up well to 0.5.4 and
then we just move upwards to 0.6.0"): a course = a collection of long videos (its lessons), analysed with the
content focus on 0.4.5's batch runner. Per lesson: the transcript, the steps taught (one key frame per step - the
screen, the panel, the values set), the tools and settings named (DaVinci Resolve's pages, nodes, values), the
lesson's notes; per course: a summary, "how do I ...?" answered with the lesson + frame + timecode, and techniques
Claude can rebuild (a Resolve technique from a course -> a recipe in the library, tested like the effects; the
templates a course gives go through 0.5.6's template packs). Measure
first: Claude's time per minute of a long lesson (0.4.4), then decide what is read from the transcript only and
what needs pictures. **Rules**: courses are someone's paid work - the user's own copies only (paid platforms are
usually locked against downloads), everything stays on the PC, only the user's notes can be shared.

**Shipped in 0.4.0** (2026-10-13, the user's overhaul): the *content creation* focus of Analyze - references
without subtitles get their words by speech to text when it is installed (`content.py auto`); the analysis
Overview's Content creation panel (`motionlab\profile.py`: the hook - cuts, words, text in the first 3 s; words per
minute and how much is talked; text on screen per minute; captions likely); Claude's breakdown per focus (review.json
`_breakdown`: hook, structure, captions, text & graphics, B-roll, sound, CTA); all searchable in Claude's memory.
**Moved to yapping mode** (2026-10-14; now 0.5.9): the foundations - text on screen, the shots described, topics and claims per video
(`content.json`) - are yapping mode's first step; this plan builds on them. Still open here: notes, collections, the
Topics page, the numbers saved at download and in cards, an `/analyze-content` skill.

**The user's notes (2026-10-09, again 2026-10-12):** "describe video: instead of focusing on our already existing
analyze video for effects, transitions and pacing, we focus on analysing videos informatively (the content inside
the video) so we can get all the information from audio and video and generate notes accordingly in our UI to
correctly apply to video recreation or other tools. So if we analyse 10 videos related to making money online we can
get common topics, add notes, ask about it... similar UI as references but dedicated to content as information
instead of filmmaking / effects."

- **Done (0.3.1)**: what is said - `tools\content.py transcript <name>` (the platform's subtitles, frame + timecode
  per line and word), MCP `transcript`. Speech to text for videos without subtitles: measured and chosen 2026-10-12
  (faster-whisper small; plans_history.md), used for references since 0.4.0.
- **Shipped in 0.3.2** (2026-10-12): **performance** - `content.py stats <name>` (one `yt-dlp -J` request, no
  download; the transcript fetch saves them too) -> `content\stats.json`: views, likes, comments, the channel's
  followers, upload date, **views ÷ followers** (the outperformer score), views a day, and a history of every fetch.
  4AM: 3,434,506 views, 768,000 followers = 4.47x, 56,722 views a day since 2026-08-13. **App: a Content tab** on
  the analysis page (the numbers + *Update the numbers*; the transcript with frame + timecode, a click moves the
  player, the line being said is marked, search, *Get the transcript* / *Fetch again*). UI test 12/12. Not yet:
  saving the numbers at download time, the numbers in shared cards.
- **Audio = what is said** and **video = what is shown** (topics, claims, numbers, tools / products, steps, hook and
  call to action; one line per shot read from a sheet of one key frame per shot; text on screen): built in yapping mode's
  first step (0.5.9). Here: across many videos.
- **Performance**: views, likes, comments, the channel's followers and the upload date, saved by the download
  (yt-dlp knows them; today `refs\downloads.json` keeps link, platform, uploader, id, duration) -> an outperformer
  score (views against followers) that yapping mode turns into validated topics.
- **Notes**: your notes per video and per topic (one home), read by `/recreate-video`, `/write-prompt`,
  `/generate-video` and `/write-script`.
- **Collections**: a tag (e.g. `make-money-online`, ~10 videos) groups references; `content.py collection <tag>`
  counts the topics across them with links to the exact frames, agreements, contradictions and gaps ->
  `knowledge\local\collections\<tag>\`.
- **App**: on a reference a *Content* tab (the transcript with clickable timecodes that move the player, the shots
  described, topic chips, claims, hook / CTA, your notes) next to the effects review; a *Topics* page per collection
  (topic cards with counts, quotes that open the frame, your notes, *Ask Claude about this collection*).
- **Claude**: an `/analyze-content` skill -> `analysis\<name>\content\content.json`, reviewed by you like effects
  (Correct / Partly / Wrong); MCP `content(reference)`, `topics(collection)`, `search(text)`.
- **Sharing**: transcripts and descriptions are other people's work - they stay on the PC; only topic summaries,
  counts and short quotes go into shared cards. Also here if friends' verdicts are in: category profiles.

## 0.5.9 - planned - Yapping mode: the yap-maxing framework

**Ships when**: on 3-5 talking videos the user picked, the content foundations and the HEIT parts are there with frame
+ timecode and reviewed by the user; the yapping detectors pass their synthetic self-tests; the user's own recording
is edited from a cut list they approved before anything rendered, every cut on a word boundary; a talking
video made from a Prepare script has a clip - the user's or one MotionLab made - on every B-roll note (*The clips
a script needs*, below).

**Moved 2026-10-22** from 0.5.2 (the user: "move the current 0.5.2 'yapping' to later on, 0.5.9 for now").

**Shipped in 0.4.0** (2026-10-13): first pieces of *Make* - the quick draft's talking mode (`draft_edit.py --sound
talk`, New edit's *Talking + captions* preset: the spoken parts in order, the pauses cut - by loudness, not yet on
word boundaries -, a punch-in every other cut, B-roll over the talking) and Claude's breakdown of a talking video
(hook, structure, captions). **Built early (2026-10-14)**: Prepare - `/write-script` and the script check (step
"Topic + script" below). Still open: the content foundations, HEIT labels, validated topics, delivery / environment
numbers, the yapping detectors with self-tests, cuts on word boundaries with the user approving the cut list, the
beats writer for the talking-head pack.

**The user's notes (2026-10-12)** ("v0.3.5" = describe video, now 0.6.0 *Take notes from videos*): "using the v0.3.5 as an exceptional tool
when creating a video: 'yapping mode' or talking to the camera. Focused on content creators: yap maxing framework.
Influential videos, lots of views videos. Basically making content short or long form; take into account formats.
HEIT framework = hook / explain / teach / illustrate. Validated topics. Copy and learn structure. Extras: 1) text on
screen 2) environment: experiment different environments 3) delivery: authentic content 4) graphics: visual hooks."
(Earlier, 2026-10-11: analyse talking-head creators AND edit the user's own recording that way.)

- **Goal**: learn from talking-to-camera videos that work (many views) and make your own - short or long form - in
  the same proven structure, from the topic to the finished edit in the lab and in DaVinci Resolve.
- **First: the content foundations** (moved here from describe video, 2026-10-14 - this settles the order conflict
  between the two; 0.6.0 builds on them): per analysed video `analysis\<name>\content\content.json`, reviewed by the
  user Correct / Partly / Wrong like effects:
  - **what is said**: the transcript (exists: `content.py`, `speech.py`) split into topics, with the claims,
    numbers, tools / products, steps, the hook (first 3 s) and the call to action;
  - **what is shown**: per shot (the lab already finds every cut) one line by Claude - setting / environment, who
    and what is on screen, talking head or B-roll, graphics - read from a sheet of one key frame per shot (about 20
    shots per picture keeps the tokens low);
  - **text on screen** with a light OCR engine, measured first (Windows' built-in OCR needs no install).
- **Learn** (from analyses of influential videos):
  - **Validated topics**: topics of videos that outperform (views against the channel's followers / usual views,
    `content.py stats` since 0.3.2), per niche - not just any topic, the ones the audience already proved.
  - **HEIT structure**: every talk split into Hook / Explain / Illustrate / Teach parts with frame + timecode and
    seconds; per format (short <= 90 s, mid, long; vertical / horizontal - measured already) the usual order and
    share of each part = the structure to copy and learn.
  - **The four extras, measured per video**: *text on screen* (how often, how many words, where); *environment* (the
    setting of each shot - its shot descriptions; your own videos log theirs, so trying different environments
    becomes a comparison); *delivery* (words per minute, pauses, energy = loudness changes, looking at the camera -
    light numbers + Claude's notes on how authentic it feels); *graphics / visual hooks* (what happens on screen in
    the first 3 s: a cut, a zoom, a text pop, a graphic - from the edit analysis).
  - **The edit's yapping profile**: jump cuts inside one talking shot (a pause cut out), punch-ins (a 1.1-1.3x scale
    step, held), word captions, B-roll cutaways over continuing speech - new detectors, each with a synthetic
    self-test video and ground truth first.
- **Make (yapping mode)**:
  1. **Topic + script**: pick a validated topic (or yours); `/write-script` (built: Prepare) writes the hook and a
     HEIT script in the structure of the best videos of your format (the prompt library).
  2. **Record**: a one-page brief - format, length, the HEIT outline with seconds, delivery notes, the environment
     to try.
  3. **Edit your raw recording** (read-only, hard rule 1): your words with timings (local Whisper - own footage has
     no platform subtitles), silences and fluffs cut on word boundaries, punch-ins at a chosen reference's rhythm,
     text on screen and captions as HTML overlays timed to your words (0.3's HyperFrames, 0.3.2's captions; the SRT
     onto Resolve's subtitle track by script, tested in the scratch project), a visual hook in the first 3 s, B-roll
     slots (your clips; generated ones in 0.7) -> a lab render, then the Resolve build. You approve the cut list
     (every removed part with frame + timecode) before anything renders.
  4. **Check**: the first 3 s say the hook, the HEIT parts land at their target seconds, the extras are there.
- **The clips a script needs** (added 2026-10-15, from the first talking video made from a Prepare script, *MotionLab
  vs other AI editors*; its v4 note: "the script's B-roll (the report with its contact sheet, a generic AI editor,
  your render beside the reference, the Prepare page) does not exist in the project, so those moments stay on you
  with the punch-ins and the list". The user: "wouldn't it be better to know which clips to prepare or give you
  before I make the decision to edit it with MotionLab? so maybe in the prepare section when creating the script,
  you could advertise to create the specific clips (as vague as possible) and if not you could create it as I need
  it?"). Today a script's `[B-ROLL]` / `[VISUAL]` notes are text: *Film it* lists them under *Film these too*,
  nothing checks that they were filmed, and the edit finds out at the end. Moved here
  from the motion-graphics plan (now 0.5.6, its step 12) on 2026-10-15.
  - (a) **A clip list with the script**: `/write-script` turns each note into a clip to get - what it must show in
    a few loose words, so whatever the user has fits ("your screen while a video is analysed", not a shot recipe),
    its seconds and the part it covers, and the easiest ways to get it: film it, record your screen, a photo or clip
    you already have, or *MotionLab makes it* (c). Saved in the script (`"clips"`: B1, B2... with the part, the
    words, the seconds, the ways); the script check points at talking-only stretches with no clip.
  - (b) **Film it as a checklist**: one row per clip; a file dropped on its row is copied into the video's folder
    (as Film it does with the recording) and ticks it; *New edit* says before the edit "3 of 4 clips are here - B2:
    MotionLab makes it, or a punch-in".
  - (c) **What MotionLab makes when a clip is missing** (the user picks per clip; nothing paid without asking):
    MotionLab's own screens - its report, a contact sheet, the Prepare page, an analysis' timeline - recorded by the
    lab in headless Edge at the video's size, with a moving cursor (the app's tests drive Edge already:
    `tools\dev\cdp.py`); the lab's pictures as clips with a slow push-in (a render beside its reference:
    `compare_renders.py`; contact sheets: `sheet.py`); a motion graphic from 0.5.6's blocks (an app window, a
    cursor, a list, numbers - "a generic AI editor, the same template on three clips" as a mock-up, no real
    product's logo); a prompt for an AI video tool (`/write-prompt shot`, made on the tool's site, back into the lab
    by 0.5.8's step 1; through the API in 0.7.0); else a punch-in with the words on screen (what v4 did). Made clips go to
    `build\made\` and are named as made in the edit.
  - (d) **The edit follows the list**: `/recreate-video` lays each clip over the words it belongs to (speech to text
    gives the frames - v4: f310-450, f609-769, f770-888) and lists what is still missing before it renders. *Make*'s
    step 3 (the B-roll slots, above) is this list.
  - **What it needs**: the clip list in the script format (`/write-script`, guidelines section 9, `script.py check`
    - text, small); Film it's checklist (the app, small); a recorder for MotionLab's own pages (new - its frame rate
    and time measured on a laptop setting first; 3 of the first script's 4 B-roll notes were MotionLab screens);
    0.5.6's blocks for the mock-ups; from the user, which stand-ins matter most for their videos.
- **Steps**: (0) the content foundations above, on 3-5 influential talking videos you pick, analysed with the
  content focus; (1) HEIT labels + the extras' numbers on them; (2) the yapping detectors + self-tests; (3) brief +
  the edit of your own recording, with the clips its script needs (above).
- **Started 2026-10-12** (the user asked for "minimal motion graphics for a good content creator talking head
  video"; released in 0.3.3): `tools\overlays\examples\talking-head-pack` - progress bar, hook title, number pop-ups
  (a counter for numbers that count up), a numbered list built point by point, an end card; the look = settings
  (accent, text colour, font, size, height on screen, progress bar, panel opacity), WHAT shows WHEN =
  `assets\beats.js` (texts + frames, written from the transcript - Claude's part in yapping mode).
  `overlay.py fit <folder> --like <video>` takes a video's size / rate / length. First use: the user's
  `projects\talk_test` (vertical 1080 x 1920, 30 fps): beats on the frames of the spoken words (57 at f1087
  (00:00:36:07), the list's points at f1524 / f1601 / f1692), with the speech captions underneath; a 720p preview
  went to the user's phone. Next: a beats writer (Claude from the transcript, HEIT labels) and the pack's
  styles per category.

## 0.5.8 - planned - Content generation: AI clips and pictures

**Ships when**: the clips of a shot list made on an AI video tool's site come back into the lab, are checked against
their shots (length, size, frame rate, a first / last frame sheet for continuity) and cut on the song with 0.5.6's
blocks and 0.5.4's sound on top - one video, in the lab and in DaVinci Resolve - and each clip is rated against its
prompt.

**The user's words (2026-10-14)**: "while moving from 0.4.1 to 0.5.4 id like to have the 0.5.4 version as a
'contente generation oriented version' ... i want the generation of video through claude and other tools such as
hyper frame or other to be more redefined and work better." On 2026-10-15 its motion-graphics part became its own plan
(now 0.5.6, *Motion graphics*; the user: "yeah go ahead"); on 2026-10-22 its voice and music went to 0.5.4 (*Sound*);
this plan keeps the rest (its old step numbers: plans_history.md).

**Where it stands**: *Generate*'s AI route (`/generate-video ai`) writes a shot list and every prompt into the prompt
library, then hands off to *Editor > New edit*, which treats the clips as footage and forgets the shot list.

1. **AI clips back into the lab** (Generate's AI route, end to end): the user drops the clips made on the tool's
   site into the project (named `01_<shot>.mp4`... as `ai_plan.md` asks); the lab matches them to the shot list,
   checks each one's length, size and frame rate against its shot, and makes a sheet of every clip's first and last
   frames (frame + timecode) so continuity - the same face, product, place, light - is checked on stills. Then it
   cuts them on the song's beats as the shot list says, and the blocks add titles, captions, graphics and sound
   effects on top -> one video, in the lab and in DaVinci Resolve. Each clip is rated against its prompt (good / ok /
   bad + a note), so the prompt library learns per model; a shot to redo gets a new prompt that says what
   changes. Today the route ends at *Editor > New edit*, which treats the clips as footage and forgets the shot list.
2. **Pictures from image tools** (was part of 0.5.6's step 10; measure first, only where a block cannot do it): Nano
   Banana / GPT Image for pictures in a scene, through the prompt library's `image` kind.

**Order** (the user decides): 1 (it closes the AI route), then 2. **Size**: medium.
**Rules**: AI clips labelled as generated; the paid API for AI video stays in 0.7.0.
**Needs first**: 0.5.6's blocks and 0.5.4's sound (what goes on top of the clips); the prompt library's ratings per
model, to rate each clip against its prompt.

## 0.5.7 - planned - Colour: measure a look, match it, grade in DaVinci Resolve

**Ships when**: the transfer methods are measured on real shots (ΔE2000 to the reference, ms per frame on a laptop
setting) and the best one is used; the user's own clips get white balance / exposure corrected (log / HDR detected
from the file, never guessed); a Resolve build has adjustable correction + look nodes that match the lab render
within 1/255.

**The user's note (2026-10-12):** "a color correction focused version since i think it kinda weak in that point
(regarding davinci, LUTs and stuff)". Talking videos need it too (phone footage: white balance, exposure, skin).

**Shipped in 0.4.0, the first part** (2026-10-13, the user's overhaul: "cinematic - effects, transitions and colour
grading"): `motionlab\colour.py` measures a reference's look per shot from the analysis' own metrics and thumbnails
(black / white point, contrast, saturation, white balance, split toning, vignette, letterbox, main colours) -> a look
in words (`colour\colour.json`, the analysis' Overview, cards, Claude's memory, styles); a Reinhard transfer in Lab
-> a 33-point .cube (`tools\colour.py match`, the quick draft) used by the lab renders (grade `"lut3d"`) and the
Resolve build's LUTs, with closeness 0-100. Still open below: correcting the user's own clips (white balance,
exposure, log / HDR), adjustable CDL nodes in Resolve, a looks library, skin / grain / bloom, waveform and
vectorscope, the transfer methods measured on real shots (ΔE2000).

**Where the lab stands**: since 0.3.0 rebuilds are in colour (each clip decoded with its own colour settings, within
1/255); a plan's grade = levels / gamma / output range per channel + saturation (`compose.grade_lut`); the Resolve
build turns each grade into a .cube LUT on the Color page. Missing: grades that stay adjustable in Resolve (a LUT is
fixed), white balance / exposure for the user's own clips, HDR and log footage. The user's clips so far: the talking
video = phone H.264, full range (`yuvj420p`), bt709 with sRGB tags; test_4am = DJI 10-bit HEVC 3840x2880, bt709.

- **Measure a reference's look** (per shot, from frames the lab already extracts; numpy, a few frames per shot):
  black / white point and contrast, saturation, white balance, the colour of shadows / mids / highlights (split
  toning), skin tones against the skin line, vignette, grain, bloom -> a *look card* in plain words ("teal shadows,
  warm highlights, blacks lifted to 6 %, saturation 80 %"); numbers only in the shared reference card.
- **Match it on the user's footage**: a colour transfer from a reference shot to their clip -> a 33-point .cube LUT
  for the lab's renders, Resolve, CapCut / Premiere, with before / after stills (frame + timecode).
- **Correct the user's own clips first**: white balance, exposure and contrast per clip, one look across the clips of
  a scene (shot matching); full-range phone video, HDR and log footage (iPhone HLG / Dolby Vision, Apple Log, D-Log M,
  S-Log3) detected from the file and converted the documented way (Resolve's Color Space Transform or the maker's
  LUT), never guessed.
- **DaVinci Resolve, adjustable**: a correction node (CDL: slope / offset / power + saturation, the API's `SetCDL`)
  and a look node (the LUT), so the wheels still work after the build; LUTs installed under Resolve's LUT folder
  `MotionLab\` per look; the project's colour management stated (Resolve Color Management changed every Rec.709 clip
  in 0.3.2's test, docs\resolve_notes.md) and checked by `--doctor`.
- **Looks library**: looks the user liked (from references or their own grades) saved like effects - name, .cube,
  before / after stills, where it came from -> *Library > Looks*, *Use in a video*; shareable (a .cube is text).
- **App**: a *Colour* tab on the analysis page (the look card, the shots' colours as a strip, a waveform /
  vectorscope picture of any frame); *Videos > a video > Colour*: clips before / after, the look picked, *Make LUT*,
  *Send to Resolve*. **Claude**: `/recreate-video` uses the look card; a look is reviewed Correct / Partly / Wrong.
- **Measure first** (light and tested first): transfer methods (Reinhard, histogram matching, MKL - all light numpy)
  on real shots of 4AM and test_4am: ΔE2000 to the reference and ms per frame on a laptop setting; CDL in the scratch
  project against the lab's numbers (within 1/255); whether 33 LUT points are enough (vs 65).

## 0.5.6 - planned - Motion graphics: template packs, the motion check, formats

**Ships when**: (1) the user's template packs are read with no Claude - every template's moves, eases, timing and
controls, plus a preview with a frame + timecode sheet - for at least two Resolve packs (Free Starter Pack 2.0 and
Swift Pack 2 are on this PC; a pack of preview clips: done in 0.5.0); (2) the motion rules (0.5.0: from 500 moves
measured on clips) are checked against the packs' exact keyframes and kept in Claude's memory; (3) the "top 3
tracks" benchmark (illdari_test_copy_1, v1: graphics "too clunky", sound effects bad) made again from blocks rebuilt from templates is rated **good** on graphics and on
sound effects, with one final render, and its time and Claude's tokens are below the baseline *What it took* (0.4.4)
measured; (4) one Resolve template is used as it is - the user's words in it - in a lab render and in a Resolve
build.

**The user's words (2026-10-15)**: "also look into a "motion graphics" oriented version? and where could i go cuz i am
getting like a lot of free templates from some courses and wanted to give them to motionlab to analyze and possibly
use in the future cuz they right now the motion graphics by default are very dull, lack creativity, very simple and
honestly could be 100x times better. where could this version fit" - then, to Claude's proposal (this plan, now 0.5.6,
the rest of content generation, now 0.5.8): "yeah go ahead". The plan it grew from (2026-10-14): "i want the generation
of video through claude and other tools such as hyper frame or other to be more redefined and work better."

**Where it stands** (2026-10-15): *Generate*'s motion-graphics videos are written by Claude from zero - HTML / CSS /
GSAP that HyperFrames renders, timed to a song by `beats.py`, checked with `overlay.py snap` / `stills` and
`precheck.py`, with sound from `sfx.py` (shipped in 0.4.1.1). MotionLab has 5 example graphics (7-16 KB each) and the
graphics library is empty. The first real one (illdari_test_copy_1, 2026-10-14) was rated "too clunky": drawn ~40 %
smaller than the reference, nothing moving between the big moves, a hand-written bug (the logo's badge missing at f38
(00:00:01:08)); every video from zero is ~42 KB of new animation code (0.5.3's review). **Why it looks dull**: Claude
invents every graphic with nothing to learn the craft from. The lab measures edits (cuts, zooms, flashes), not motion
design - the ease of a move, overshoot, letters arriving one after another, things still drifting during a hold,
layers, texture. Building blocks written the same way would come out the same.

**What the templates give** (checked read-only on this PC, 2026-10-15): `Documents\EditingVault\Plugins` holds DaVinci
Resolve packs from courses - Free Starter Pack 2.0 (228 templates), Swift Pack 2 (72 transitions, each with a preview
picture), Shot Pack (31), Paper Animator, tracked text / image and 5 Hyperlapse macros; the same packs are installed
in Resolve. A `.drfx` is a zip of Fusion `.setting` files, which are plain text: the exact keyframes, their ease
handles, the controls a user can change and the expressions can be read (a quick count: *Shake - Main* 168 keys and
217 expressions, *Animation In & Out* 32 keys and 42 expressions) - nothing guessed from pixels. After Effects 2025 is
installed with `aerender.exe` (renders a project without opening a window) and Motion Bro (a template-pack manager);
the `.aep` files found look like the user's own projects. The pinned HyperFrames (0.8.149) has Lottie support in its
code (`data-lottie-src`; not tried yet), so After Effects animations exported to Lottie (the free Bodymovin plug-in,
not installed) could play inside MotionLab's graphics.

**Shipped in 0.5.0** (2026-10-16; its text when it shipped: plans_history.md): steps 1-3 and 5 for a pack of
preview clips (Swishy, 131 clips: `templates.py read`, Claude's cards, the motion rules = local-make-9), **74
templates** in `tools\overlays\motion\` (57 rebuilt from the clips, 17 MotionLab originals for the kinds the
template marketplaces list most), the Motion Graphics page, Generate building from them. **No Correct / Partly /
Wrong reviews of cards or templates** (the user, 2026-10-16: "i dont need to review templates with ok partly or
wrong so just go in with it") - how a made video turned out is the check.

**Still open** (this plan): steps 1-2 for Resolve / After Effects / Lottie packs (keyframes read exactly); step 4
(templates used as they are); step 5's frame test (a template under `overlay.py upgrade-test` - the self-test
only snapshots each one for "not empty"); 6 formats; 7 Generate's quick draft from templates; 9 the animatic; 10
the motion check against the rules; 11; 12; the Ships-when benchmark (the "top 3 tracks" remake).

**Goal**: graphics that look designed, not generated - learned from professional templates the user owns, used as
they are where that is best, rebuilt as MotionLab's own blocks where they must bend to any video, and checked against
measured motion rules before anything renders. Claude decides what a video says and its scenes; the templates, the
rules and the blocks decide how it moves.

**Builds on 0.5.3** (*Faster videos*): the blocks (step 5), the formats (6) and Generate's quick draft (7) run through
its one-page brief and its build command - Claude reads one page, writes a scene list, one command renders, checks
and makes one sheet - so a video from zero gets the same brief -> plan -> build -> one look as an edit. **Moved out**
(2026-10-15): voice and music, AI clips back into the lab and pictures from image tools -> content generation (now
0.5.8; voice and music since 2026-10-22 in 0.5.4 *Sound*); the clips a script needs -> 0.5.9 (yapping mode's B-roll
slots are that list); faster renders -> 0.5.3;
measuring -> 0.4.4 (shipped). The old step numbers: plans_history.md.

**Learn from the templates**

1. **Template packs in** (the Analyser, next to videos): drop a pack - .drfx, .setting, a .zip or a folder, an .aep /
   .mogrt, a Lottie .json, or only its preview videos - or point at the folder where it already is. The pack stays
   where it is, read-only like a reference video (hard rule 1, its SHA-256 recorded and checked); MotionLab writes only
   to `analysis\templates\<pack>\` (like 0.4.5's thumbnail sets in `analysis\thumbs\`). The pack's licence text is
   kept with it and shown. *Can it work*: yes.
2. **Read them exactly** (`tools\templates.py read <pack>`, no Claude, in bulk): per template what moves, its keyframes
   in frames, the ease of each move as numbers (the cubic-bezier) and in words (decelerating, S-curve...), overshoot,
   the stagger between parts, the expressions (a wiggle's or shake's size and speed), the layers and effects used and
   the controls a user can change -> `motion.json`; plus a preview rendered by Resolve (on a test clip, the way
   `library.py test` renders macros) or by `aerender`, and a sheet with frame + timecode on every tile. Sources:
   Resolve's `.setting` text (certain - checked above); After Effects through a script run inside it (`AfterFX.exe
   -r`, only on a PC that has it: likely - measure its start-up and that it runs without clicks); Lottie JSON (the
   keyframes and eases are in the file); preview videos only (the lab's own analysis, category motion_graphics -
   measured, less exact). *Can it work*: Resolve yes, After Effects likely; the preview render time per template is
   measured first (Starter Pack alone is 228 templates).
3. **Motion cards and motion rules** (Claude, in batches like 0.4.5's bulk; the templates the user stars first): per
   template a short card - what it is (a title, a transition, a lower third, a counter...), frames in / hold / out,
   the eases, what keeps it alive during a hold, layering and depth, texture (grain, glow, a chromatic split), the type,
   and why it works - no Correct / Partly / Wrong review (the user, 2026-10-16). Across the cards Claude writes **motion rules**
   with numbers ("entrances 8-12 frames, decelerating; letters 2 frames apart; exits about twice as fast; nothing
   fully still during a hold"), saved like lessons on making videos (`local-make-N`) and read before every graphic.
   Cards and rules are text and numbers - shareable through *Claude's memory > Share*; the templates never leave the
   PC. *Can it work*: yes - the numbers come from step 2, Claude adds the why from a sheet (~1.6 k tokens a picture);
   ~20 cards are enough to start, not all 330.
4. **Use templates as they are** (where the user's licence allows): a Resolve template on a Resolve build's timeline
   with its controls filled in (the user's words, colours) through Resolve's API (Fusion titles and generators have
   calls; effects as a clip's Fusion comp, `ImportFusionComp` - the lab uses it already); the same template rendered
   by Resolve or `aerender` into a transparent clip that the lab render uses like any overlay (a plan layer); a Lottie
   export played inside a HyperFrames composition (was part of step 10). HyperFrames stays MotionLab's own graphics
   engine; a template used as it is arrives as a rendered clip. *Can it work*: likely. Measure: which kinds the API can
   place (a transition between two clips may need a workaround) and the render time per template. Resolve's scripting
   needs the Studio edition (the free 21.1 and later can't be scripted from outside), so friends on the free edition
   get steps 3 and 5 only.

**Make with what was learned**

5. **Building blocks for HyperFrames, rebuilt from the best templates** (was step 1): a tested kit Claude puts scenes
   together from, instead of writing every graphic from zero - text (type-on, word pops, mask reveals, the 3D lyric
   stack), UI (a phone / app / window frame, a cursor on a curved path with a press), numbers (counters, bars), lists,
   a logo sting and an end card, transitions between scenes (whip, zoom-through, mask wipe, flash) and a camera
   (push-in, a jolt on hits, a slow drift, a smear for fast moves). **New**: each block starts from templates the user
   liked (steps 2-3) - their curves converted exactly (Fusion's and After Effects' ease handles -> GSAP eases), their
   timing and layering kept, their effects rebuilt in CSS / SVG / WebGL once per block - MotionLab's own code, never a
   template's pictures or fonts and never a 1:1 copy of a paid one. Each block: settings the user can change, its own
   sound cues (step 8), safe with motion blur and snapshots (0.4.2 item 7's helpers), and a test - its frames rendered
   and compared like `overlay.py upgrade-test` (max 4/255), so a HyperFrames upgrade cannot break it unseen. Shared
   through the repo next to `tools\overlays\examples\`; the user's approved ones in the graphics library. Claude writes
   new code only for what no block does (fewer tokens, fewer bugs: the badge missing at f38 (00:00:01:08) was
   hand-written). *Can it work*: the moves and eases yes (the conversion is math); heavy effects (particles,
   displacement, 3D) only partly - those stay template clips (step 4).
6. **Formats - a made video as a template** (was item 13 of *Check before you render*): a generated video the user
   approved is saved as a format - "top 3 tracks", a lyric video, a list / explainer, an app promo, a quote or number
   reel... = its scenes as settings (texts, pictures, colours, song, length). The next video in that format is new
   settings, no new code (the biggest saving in Claude's tokens). *Generate* gets *Start from a format*. The first
   one: illdari's "top 3 tracks" reel, once the user approves v2.
7. **A quick draft for Generate** (made by rules, no Claude, like the Editor's quick draft): a format or the style of up to
   3 analysed videos (`style.py`) + the user's texts + the song's beats (`beats.py`) -> scenes on the downbeats, the
   biggest change on the drop, the blocks filled in -> a first video in minutes; Claude refines it (what it says, the
   custom parts) instead of starting from an empty page. The style of a motion-graphics reference gets the numbers v1
   got wrong: how long text holds, how fast things move (pixels per frame), the size of the main element on the frame
   (Claude measures it once on the reference's frames; saved with the style); the motion rules (step 3) set its
   eases, holds and staggers.
8. **Sound effects as a lab tool** (was item 8 of *Check before you render*; **Shipped in 0.4.1.1** (2026-10-14,
   built early): `tools\sfx.py` + `motionlab\sfx.py` - 22 synthesised kinds, sample-identical to `sfx_v2.py`; cues in
   overlay.json "cues" as formulas of the settings (`repeat` / `if`), the starter graphic has them; cues from a plan's
   layers; each effect levelled against the song - the quieter of 400 ms around it and its own loud part, so a sound
   in a short gap before a loud line follows the gap; a -1 dBFS limiter; stem + mix + a level report; ~1 s per minute
   of video; self-check in `selftest.py`. The user's listen of the illdari v2 rebuild: "kinda too loud" -> every level
   3 dB lower, effects' peaks at most -6 dBFS, sparse sounds (sparks) measured near their peak: now 3.1 dB under
   `sfx_v2.py` (median), none more than 2.9 dB over (was up to +10.6). Open: a `--sfx` flag for the quick draft - now in 0.5.4 *Sound*, with recorded samples):
   `tools\sfx.py`, from `sfx_v2.py` - a graphic lists its cues (frame + kind:
   whoosh, click, key, pop, hit, riser...) next to its settings, so the sound follows when a setting moves the timing
   (the typed text); synthesised (no samples to license); each effect levelled against the song under it -
   measured, since Claude cannot hear; the effects alone as a stem for Resolve + the mix for the plan. Blocks carry
   their cues (a whip = a whoosh); the Editor's quick-draft effects (zooms, whips, flashes) become cues the same way.
   It was step 4 until 2026-10-15 (code comments still say so).
9. **A preview before the render** (was item 11 of *Check before you render*, measure first): (a) an **animatic** -
   the scene snapshots (0.4.2's `overlay.py snap`) held on their frames with the song and the sound effects -> an MP4
   in seconds, so the timing and the sound are checked before anything renders for minutes; (b) the **live preview**
   - HyperFrames' `hyperframes preview` (in the pinned 0.8.149), not yet tried: does the 3D lyric part play smoothly
   on a laptop, does it play the song. If it does: *Play* on the video's page - live with the song and its sound
   effects, a scrub bar, frame + timecode, settings change at once without a render (no motion blur in the preview;
   the render is the final word).
10. **The motion check** (new): `precheck.py` learns the motion rules (step 3) and flags, with frame + timecode: a
    stretch where nothing on screen moves for longer than the rules allow, moves with no ease (linear), every move at
    one speed, the main element smaller than the style's measured size (illdari's v1 was ~40 % small), text on screen
    shorter than its reading time, parts outside the platform's safe area. Claude also checks the snapshot sheet
    against the rules before the first render. *Can it work*: yes for what can be measured (movement per frame is
    already measured for the motion-blur check); "does it look designed" stays the user's rating.
11. **The made video's page**: a video made from zero opens on its project's page (Editor); it gets Generate's steps
    there - the scene table (frame + timecode), the animatic and *Play*, the settings, the sound, *Render*, *How did
    it turn out?* with notes on moments (0.4.2) - in plain words.
12. **One video, three sizes**: the compositions are HTML, so 9:16, 16:9 and 1:1 come from one video with layout
    rules per size (`overlay.py fit` already takes a size); the user ticks the sizes to render.

**Order** (the user decides): 1 and 2 on the Resolve packs first (no Claude - they can be built early, like the sound
effects tool was); 3 on ~20 templates the user stars; 10 (the check, from the rules); 5 (the "top 3" reel's blocks
first); 6 once illdari's v2 is approved; 9a (small); 11; 7 when a few blocks and formats exist; 4, measured (Resolve
first, After Effects after); then 9b and 12. **Size**: large - 0.5.0 shipped 1-3 and 5 for preview-clip packs; the
rest ships in parts.
**Rules**: light and tested first (every new tool optional and measured on a laptop; After Effects and Resolve Studio
only where they are installed); the templates are the user's copies under their licences - they stay on the PC, never
in the repo, a pack for friends or a shared graphic; motion cards, rules and MotionLab's own blocks are what is shared;
copy a style, never someone's content (their words, logos, characters, pictures).
**Needs first**: 0.5.3's brief and build command (steps 5-7 run through them); 0.4.6's fonts (shipped 2026-10-16);
from the user: which packs first, ~20 templates starred, the verdict on the remade "top 3" reel.

## 0.5.5 - planned - Content agency: My Brand

**Ships when**: a *My Brand* page above the Analyser holds the user's goal on social media, their audience, identity
(colours, fonts, logo, voice) and catalogue with prices - read from their website and checked by them; Prepare, New
edit and Motion Graphics use it (a script in the brand's voice, the brand's colours as a palette, its logo); one video
places a product - in passing or as a call to action at the end - and the user rates it OK or better.

**The user's words (2026-10-22)**: "0.5.5 Content Agency - implement a new section above Analyze which would be called
'My Brand'". Their mock-up deck (`new_edit_section.html`, slides 10-11, in Spanish): *Mi marca* - "a page where Claude
learns your goal on social media, your audience, your identity and the whole catalogue with prices, reading your web;
used in Prepare, the Editor and Motion Graphics" ("that it knows the whole catalogue, prices included"); *Motion de
producto* - "with My Brand's catalogue Claude puts a product in the video: indirectly or with a call to buy at the end,
mixed with your clips in the same edit".

1. **The page** (the sidebar, above the Analyser): goal, audience, identity, voice, catalogue - each a card the user
   fills or corrects; stored on this PC (`knowledge\local\brand.json`), never in shared knowledge unless the user
   shares it.
2. **Read the website**: the user gives a link; MotionLab fetches that site's pages only, Claude takes the products /
   services with their prices, the tone and the colours; the user ticks what is right before it is saved.
3. **The brand kit in the app**: the brand's colours as the first palette in New edit's *Colour palette*, its fonts
   (`fonts\` or added) and logo (`logos\` or the user's file) offered first in Motion Graphics and captions.
4. **The skills read it**: `/write-script` and `/write-title` (voice, audience, goal), `/recreate-video` and
   `/generate-video` (identity, products), `/write-prompt` (product shots).
5. **Product motion**: a product from the catalogue in the video - in passing (a lower third, a card over B-roll) or a
   call to action at the end (price, link) - built from the Motion Graphics library's templates.

**Order** (the user decides): 1-3 first, then 4 and 5. **Size**: large, ships in parts.
**Rules**: the brand stays on the PC; only the user's own site is read; prices shown as the user confirmed them.
**Needs first**: nothing; from the user: their website and their goal.

## 0.5.4 - planned - Sound: real sound effects, music and voice

**Ships when**: an edit's sound effects come from recorded samples (every file's licence recorded) and the user rates
them good - not "AI created" - on two videos (a talking video and a music edit); `precheck.py --sfx` passes on both; a
laptop measures the library's size and the time it adds per minute of video.

**The user's words (2026-10-22)**: "the Claude sounds we are getting are very dull, AI created and very plain (i want
you to expand on this and see if its possible to improve the way u generate sound effects or ambiance music) if not we
could search in the future to get some sounds from free libraries or pages or viral sounds"; then: "lets try to review
the current roadmap and see if we can move all sound related ideas to 0.5.4 instead so we can remove that AI-look for
SFX or maybe even create ambience music or random stuff from public libraries".

**Where it stands**: `motionlab\sfx.py` synthesises 22 kinds from noise and tones (shipped in 0.4.1.1), each levelled
against the music; New edit's step 5 asks how many effects and which kinds (0.5.2). Claude's assessment (2026-10-22):
synthesis has a ceiling - more tuning helps a little but never sounds recorded; music models that run locally need a
strong GPU, and their licences often forbid commercial use.

1. **A sound library** (like `fonts\` and `logos\`): recorded effects sorted by the cue kinds (`sounds\<kind>\` +
   `sounds.json`: source, author, licence, link per file). In the repo only CC0 and small (a few MB): Kenney's packs,
   Freesound filtered to CC0. Free libraries whose terms forbid passing the files on (Sonniss' GDC bundles, Pixabay,
   Mixkit - each licence checked live) stay on the PC: the user downloads them and `sfx.py` indexes them.
2. **`sfx.py` prefers a sample**: per cue the closest kind and length, a different one each time (no repeats in a
   row), a little pitch and level variation; the levelling against the music stays; synthesis is the fallback when
   no sample fits. Measured before / after on the test videos - the user's listen decides.
3. **Music and ambience from public libraries**: picked by mood, tempo and length (`beats.py` measures them), only
   with clear licences (CC0 / free for commercial use; CC BY = its credit line goes into the publish package's
   description); room tone and ambience beds (city, nature, a café) under talking videos. New edit's *Music* gets
   *From the library*.
4. **Voice-over** (was content generation's step 1, measure first): ElevenLabs (the user's own account) or a local
   text-to-speech measured on a laptop first (time per minute of speech, size, how natural); its words timed like
   speech to text, so captions and scenes follow the voice. A voice only with the speaker's consent.
5. **Separate music from voice** (from ideas.md, measure first - heavy on CPU): Demucs stems for cleaner beats / drops
   and cleaner speech, and to lower the music under the voice.
6. **The quick draft's `--sfx`** (open since 0.4.1.1): the draft places its effects as cues, `sfx.py plan` makes them.

**Not here**: viral / trending sounds are copyrighted - they are added in TikTok or Instagram when posting, never built
into a render (the *Trending sounds* plan was scrapped 2026-10-15). Music made by a model stays out until a light one
with clear commercial terms exists.
**Order** (the user decides): 1 + 2 first (the AI look), then 3, 6, 4, 5. **Size**: medium.
**Rules**: light and tested first; every file's licence recorded; music and voices only with clear licences and
consent; generated voices labelled as generated.
**Needs first**: nothing - New edit's sound step (0.5.2) already asks for it.

## 0.5.3 - planned - Faster videos: half of Claude's time, the same result, the loop untouched

**Ships when** (revised 2026-10-23; measured with *What it took* on this PC, everything included): on the re-run of the
same requests Claude's minutes are **at least halved** - ae_50_test 27 -> 13.5 or less, testing_entire_workflow
(51.9 s) 38.5 -> 19 or less, What's new in MotionLab 0.4.3 (25.7 s) 24.5 -> 12 or less - with Claude's tokens per
video 3x lower, at most one full render round, the user's side-by-side verdict "the same or better", and **nothing
removed from how context is given**: the references analysed, the user's personal review of every result, the lessons
and Claude's memory all reach Claude as before. The old target (a minute of video in ten minutes of Claude) stays the
direction, not the gate.

**The user's words**: 2026-10-15: "current benchmark is kinda like spent 1 minute of claude is equal to 1second of
video result so a 1min video takes cladue 50/60 mins, i want to go as down as to 1 min of video to 10 minutes of
claude (with everything included, sfx, motion graphics, effects, captions...) do you think it spossible?" -
2026-10-23, after the review `docs\review_video_time_2026-10-23.md`: "its okay if we dont get to the target but if you
can cut the time in half its a MAJOR improvement if it does not affect the result or the way we give context.
remember motionlab is different from other apps because we analyze and reiterate with personal review to improve our
engine". **The rule for every step below**: it replaces Claude's mechanical checking, writing or waiting with a PC
tool; it never trims the loop (analysis -> review -> lessons -> memory), and a rating that drops means it does not ship.

**Where the time goes - measured** (Claude's review 2026-10-15 of four talking / hand-coded videos; 2026-10-23 of
every video made since, `usage.py sessions --all`, the build scripts' docstrings, the ae_50_test session turn by turn):

| Video | Kind | Length | Claude min | Tokens | What cost rounds |
|---|---|---|---|---|---|
| What's new 0.4.3 (Fable high) | talking edit | 25.7 s | 24.5 | 8.3 M | the video rendered 5x, captions 4x, sfx 4x |
| testing_entire_workflow (Fable high) | talking edit | 51.9 s | 38.5 | 8.7 M | two polling loops that never ended: ~16 min |
| What's new 0.5.1 and 0.5.2 | talking edit, 3 versions | ~19 s | 56.5 | 21.6 M | ~19 min a version; two versions from the ratings (colour, graphics, pacing, sound) |
| illdari_test_copy_2 (Fable high) | from zero, hand-coded | 25 s | 20.8 | 8.2 M | |
| saas_motionlab | from zero, hand-coded | 20 s | 15.1 | 6.7 M | v2 = a song + motion blur, no graphic change |
| test_0.5.0_motionlab_graphics | from zero, templates | 20 s | 28.3 | 16.0 M | 3 snap rounds on the wipe and the hook |
| ae_50_test | from zero, 110 AE templates | 30 s | 27.3 + the final | 10.8 M | 0 lines of animation code; 22 snap calls (16 answerable by the PC); 7 orchestration turns; 55 buried cues |

Read as a rate: a video from zero costs 0.6-1.0 min of Claude per second of video, a talking edit 0.5-0.75, a version
driven by the ratings ~19 min. **Templates removed the code, not the minutes**: the hand-coded reels and the template
reels cost the same, because checking and orchestration replaced writing. The ae_50_test session, phase by phase:
reading the lab ~5 min (~70 k tokens before the first decision), deciding ~3, snapshot rounds ~7 (22 calls, 17
sheets), plan / sound / precheck ~4, renders 7 turns (~8 min plain + ~35 min motion blur of PC time, one after
another, one failed detached launch) - Claude's own judgement was ~5 of the 27 minutes.

**Everything that holds Claude back today** (2026-10-23, the whole Claude-use process, not only videos):
1. **Context read per window**: the root `CLAUDE.md` is 24 KB on every turn (claude_tips.md promises ~3.5 k tokens);
   a skill is 12-22 KB plus its companions (recreate-video 21.5 + graphics 4.7; analyze-reference 21.7 + lessons 5.6
   + review_rules 4.6 + texts 8.1; write-title 13.5 + guidelines 12); Claude's memory 28 KB, the making lessons
   21.6 KB, the motion_graphics category summary 51 KB (77 % unverified), the 110-template dump 14 KB.
2. **Snapshots taken to read a number** the lab already holds (a template's move frames, a text's width, a size).
3. **Orchestration and waits**: renders one after another, the 10-minute tool limit, detached launches with their
   gotcha (local-make-6), polling loops, 5-8 turns per video just to run tools in order.
4. **Rounds caused by tool defaults**: cue levels designed on a quiet reference (55 flags), captions regrouped by the
   tool's rules (local-make-17), a transition shorter than it can clear (local-make-11), a template at a size it was
   never checked at (local-make-18).
5. **Claude writing what the lab can derive**: captions JSON from the script (twice), 10-15 KB `edit_vN.py` per
   video, a stills-sheet script, a cue-levelling script, a render runner.
6. **Blind guesses that become versions**: format, song, look, the number on screen - each blank in a request is a
   guess, and a wrong guess is a ~19-minute version ("always the same color palette", 2026-10-22).
7. **Verbose tool output**: `overlay.py settings` prints three font lists of 34 names per graphic (~1.5 KB of noise
   a call), `sfx.py plan` every cue (74 lines), `knowledge.py memory` 13-19 k characters.
8. **Claude's own environment slips**: a heredoc that eats backslashes (2 turns in ae_50_test), PowerShell argument
   quoting (1), a blocked sleep (1), `overlay.py settings` refusing a library template's folder (1).
9. **No permission allowlist** in `.claude\settings.json`: a friend without auto mode approves every lab tool call.
10. **The measure itself**: `usage.py` counts Claude's windows but not the lab's time when Claude runs a tool from
    its shell, and gives no thinking / waiting split per step - the 2026-10-15 table was worked out by hand.

**Built 2026-10-23** (one window, from this plan; not released - the re-runs and the user's ratings decide):
- A: template landing (`overlay.py new --land "<track>@<frame>"`, `templates.py land / tracks [--measure]`: the repo's
  templates' moves measured into `measured.json`), the text-fit check (HyperFrames' layout pass in every `overlay.py
  snap` and `templates.py check`: FIT lines), the size table (`templates.py sizes` -> ok / NOT ok per size, run in bulk
  for every template), sound levels that pass first time (`sfx.py --floor-vs-song -24`, the default), fast moves found
  when a template is measured or finished (FAST lines), the cut-sheet (`render_video.py --cuts`), screen-recording dips
  (`prep_footage.py` -> sources.json "dips", the quick draft avoids them), captions from the script (`overlay.py
  captions --script`), the voice levelled per take in the quick draft.
- B: one build (`tools\build.py`: changed graphics N at a time, the sound, the video, the precheck, the cut-sheet,
  a 10-line summary; a final with motion blur keeps graphics that hardly move plain - HyperFrames renders no frame
  ranges, so "only frames that move" is per graphic), Claude's long steps as the app's jobs (`tools\job.py start |
  wait`, the job kind `build`; without the app a detached runner), the waits rule in the skills.
- C: the brief (`tools\brief.py`, written by the app when a Generate or New edit request is saved, with a *Left out*
  footer), `knowledge.py memory --rules`, lessons by kind (`{kinds}` tags, `knowledge.py lessons --kind`, the ones the
  tools now do as one line), `--brief` outputs (sfx summary, `templates.py library --brief`, settings without font
  lists), the skills as a router + one file per way (generate-video, recreate-video, analyze-reference, write-title),
  the root CLAUDE.md 24.1 -> 16.4 KB (the long text in `docs\lab_map.md`), verified-only category summaries (51 ->
  12 KB) + `review_draft.json` (the lab's measured draft of every event in review.json's format).
- D: the edit list (`draft_edit.py --apply <list>`, `motionlab\editlist.py`), captions + voice from the tools, the
  quick draft for Generate (`tools\gen_draft.py`).
- E: the Generator asks the look (the three looks + Surprise me) and offers the song from last time; Review's *Send it
  to Claude* names the parts the next version changes; settings-only versions rebuild only what changed.
- F: tools take template ids (`overlay.py settings <id>`, `new --from <folder>`), errors name the command to use;
  `usage.py project <name> --steps` + *What it took* split Claude's thinking from the time its tools ran (ae_50_test
  before: 27.3 min = 22.2 thinking + writing, 5.0 waiting, 144 tool calls). F1 (`.claude\settings.json`
  permissions.allow) was refused to Claude itself: the proposed list is in the chat for the user to add; F3 waits on
  the re-runs.
- Fixed in the tools instead of kept as lessons: a plan's relative paths (local-make-11(3)), one graphic's bad cue
  no longer silences a plan (-13), TOO SHORT for templates with a minimum length (-11), IGNORED for an out-of-range
  value (-16), speech-bubble's plain pill and `new --from` a folder (-17).
**Waiting on the user**: the re-runs (ae_50_test, testing_entire_workflow, What's new 0.4.3) with `usage.py project
<name> --steps` before / after and the ratings; F1; F3.

### The plan - six parts, each a measured cut

**Part A - the PC answers what Claude used to look at** (small items, each removes rounds a real session paid for)

| | What | How | Result | Risk |
|---|---|---|---|---|
| A1 | **Template landing from its tracks** | every template records its moves as `tracks` (`start_f`, `length_f`); `overlay.py new --from <id> --land "<track>@<plan frame>"` (and `templates.py land <id>`) computes the plan layer's `in` so the move lands on the beat (SMASH's hit at f80 of the template, the cut at f136, the beat f172 -> in 44) | ~10 snap rounds a template video (~4 min, ~25 k tokens of sheets); local-make-12 / -14 retired | none: the tracks were measured when the template was finished; the one cut-sheet (A6) still shows it |
| A2 | **Text-fit check in every snapshot** | `overlay.py snap --fit` and inside `templates.py check`: ink touching the frame's edge, a text box wider than the frame, two text elements overlapping -> a flag with frame, element, pixels | 2-3 rounds a video (~2 min): the hook's last word, step 3 off the right edge, the torn-paper headline (ae_50_test) | none, a flag |
| A3 | **A size table for every template** | the PC in bulk, overnight: `templates.py check --size 1080x1920` and `1080x1080` over the 76 + 110 templates, `sizes_ok` into template.json / index.json, the failures listed for a batch agent | the vertical test round; vertical videos from the AE library | none |
| A4 | **Sound levels that pass first time** | `sfx.py plan --floor-vs-song -24` (the precheck's "buried" rule applied while levelling, M002's measured way) | one sound round (~2 min) a video | the "spamming sfx" note is about count and sameness - unchanged |
| A5 | **Motion-blur copies checked at finish time** | `templates.py finish` runs `precheck.py --motion-blur 5` on the template's render; a fast move that shows copies gets a smear in the template (local-make-11(4)), once | the stepped stripes and the rising title of ae_50_test, found by the PC when the template is built, not by Claude per video | none |
| A6 | **The cut-sheet as a tool** | `render_video.py <plan> --cuts`: a still at every layer boundary and every cue frame, frame + timecode, one sheet (dense: 24-32 tiles) | the one look that stays; replaces the hand-written `stills_sheet.py` and 12 per-scene sheets (~1.6 k tokens each) | none |
| A7 | **Screen-recording dips in prep** | `prep_footage.py` lists the one-frame black repaints of a screen recording (luma under 60 % of the stretch's median, local-make-15) in `sources.json`; the quick draft keeps shots inside clean runs | one render round of a talking video with the app on screen | none |
| A8 | **Captions from the script by the tool** | `overlay.py captions --from <script> --align <transcript>`: one cue per script line at the transcript's times, held to the next (+0.5 s), the script's wording (local-make-2, -17) | Claude stops typing 5-10 KB of captions JSON (two videos did) | names the transcript mis-hears: `--names` as today |
| A9 | **Voice levelling in the quick draft** | `draft_edit.py --talk` levels the take (one gain per take, the user's rule of 2026-10-16; per shot only with `--per-shot`) before `sfx.py plan` (local-make-3) | the levelling block of every talking `edit_vN.py` | none |

**Part B - one build, one look** (the orchestration turns and the waits)

| | What | How | Result | Risk |
|---|---|---|---|---|
| B1 | **One build command** | `tools\build.py <project> plan_vN.json`: every composition the plan names rendered plain (in parallel), the composite, `precheck.py`, the cut-sheet (A6), a 10-line summary (what rendered, minutes, flags with frame + timecode, the sheet's path); `--final` = the motion-blur renders detached with `HYPERFRAMES_RENDER_DETACHED` set by the tool, the composite, the precheck, one "done" line; a re-run skips parts whose inputs' hash did not change (a settings-only version re-renders one composition) | 5-6 turns (~3-4 min) a video; local-make-6 and the ae_50_test launch failure disappear into the tool | none |
| B2 | **Parallel and partial overlay renders** | `overlay.py render <a> <b> <c>` N at a time (default by CPU count, measured on a laptop setting too); motion-blur sub-frames only for frames that move (~40 % of ae_50_test's frames are holds); render only the visible box for captions and lower thirds | the 35-minute motion-blur pass of ae_50_test ~12 min; a 60 s build near 4 min | measure first: Chrome and the GPU are shared (0.5.3's old step 3 kept as written) |
| B3 | **Claude's long steps as app jobs** | `tools\job.py start <kind> ...` sends the job to the running app's server (its queue, its Jobs page, the server keeps it alive, *What it took* counts it as lab time) and returns; `job.py wait <id>` blocks under the 10-minute limit; without the app the same runner runs in-process | no polling, no detached launches, Claude's waits visible on the Jobs page; the lab's minutes finally measured (10.) | none |
| B4 | **The waits rule in the skills** | never poll; a run under ~10 min stays in the foreground; longer = a job (B3); one tool call = one build (B1) | the two 9.8-minute loops of testing_entire_workflow can no longer happen | none |

**Part C - the brief: context once, complete** (the ~70 k tokens before the first decision)

| | What | How | Result | Risk |
|---|---|---|---|---|
| C1 | **A Generate brief, made by the app** | when a Generate request is saved the app runs `brief.py <project>` -> `build\brief.md` (3-5 KB): the request with its blanks filled by the lab's defaults and marked as defaults (format = the templates' native size / what the user picked last time; the song used in the last reel with `beats.py` already run from its start; the look), the template catalogue filtered to the request's words (id, what, key moves with frames, sizes ok, text slots), the lessons tagged for this kind, the ratings-as-rules block; the window's first message names the brief | ~8 k tokens instead of ~70 k; Claude starts at the scene table | the brief must list what it left out (a `left out` footer) so nothing a verdict or a lesson depends on goes missing - the test in section *Tests* |
| C2 | **An edit brief** (0.5.3's step 4 as written) | the footage (clips, lengths, the board), the words with frame + timecode (script and transcript lined up), the chosen style's numbers, the sound answer, `edit_request.json`, the applicable rules | replaces 5-8 calls at the start of every edit session | the same footer |
| C3 | **Claude's memory in parts** | `knowledge.py memory --rules` (the ratings block, ~1.5 KB) for Generate and edits by feel; `--styles` stays for scripts; the whole memory for 1:1 edits of a reference | 13-19 k characters a session | none: memory.md stays the whole memory |
| C4 | **Lessons by kind, the stable ones rolled into tools** | each lesson gets `kind: talking / generate / templates / all`; a skill reads its kind + `all`; lessons that are now tools leave the text: local-make-6 -> B1, -11(1) -> the template refuses shorter, -12 / -14 -> A1, -15 -> A7, -17 -> A8, -18(3) -> A4, -3 -> A9 | 21.6 KB -> ~6 KB read per video | a lesson tagged `all` is always read; nothing deleted, moved to a "built into the lab" block |
| C5 | **`--brief` outputs** | `overlay.py settings` without the font lists (`--fonts` shows them), `sfx.py plan` a summary (count, floor, limiter, the flagged cues only; `--all` as today), `templates.py library --brief` | ~10-15 k characters a session | none |
| C6 | **Skills as a router + one file per way** | `generate-video`: request / templates / improve / ai; `analyze-reference`: review / batch / thumbs / texts / feedback / lessons; `recreate-video`: request / 1:1 / feel / improve / batch; `write-title`: first / package / test. The SKILL.md keeps section 0 and the table of ways; a way's file is read only for that way | 12-22 KB -> ~6-8 KB read per window | none |
| C7 | **`CLAUDE.md` back to ~13 KB** | the tools' detail into their docstrings (the rule already says to read them), the Layout block shortened to the folders Claude writes into, the Workflow block to the rules | ~3 k tokens a turn, every turn of every window | none |
| C8 | **Verified-only category summaries** (the 2026-10-20 addendum, item 1) | the summary read before a review keeps only verified effects; the lab writes a draft per event (type, frames + timecodes, evidence) for Claude to check | reviews: 51 KB -> ~12 KB read; Claude corrects instead of writing from zero | none to the verdict loop (Claude still looks at every sheet) |

**Part D - the plan as a list, not a program** (Claude's writing)

| | What | How | Result | Risk |
|---|---|---|---|---|
| D1 | **The edit list** (0.5.3's step 5) | `draft_edit.py <project> --apply <list>`: "cut f120-f188", "punch-in 1.2x at f300 (snap)", "shot 4 tight", "caption clean_box", "graphic talking-head-pack point 2 at f1524", "a whoosh on every whip", "hold f380-f404"; a raw-layer escape for one-offs; the list saved as `edit_vN.list` beside `plan_vN.json` | no 10-15 KB `edit_vN.py` per talking video - the biggest cut of Claude's own writing | an edit the list cannot say -> the escape; measured on the two talking test videos |
| D2 | **Captions and voice from the tools** | A8 + A9 called by the quick draft and the list | with D1, a talking video is: brief -> list -> build -> one look | |
| D3 | **A quick draft for Generate** (0.5.6's step 7, moved here) | by rules, no Claude: beats -> scene changes on downbeats, the biggest change on the drop; templates from `templates.py pick` matched to the request's words, landed by their tracks (A1); the words = the request's lines; the hook and end card from the kind; plan + compositions + `sfx.py plan` + the plain build (B1). Claude edits a scene table (frame + timecode, template, words), not a build | for ae_50_test the draft would have produced the beat grid, the 1-bar montage, the how-to block and the end card; Claude's ~3 min of words and matching stay | quality: the user's rating on the re-run decides; the draft is always shown as a draft |

**Part E - fewer blind guesses, cheaper versions** (the ~19-minute versions)

| | What | How | Result | Risk |
|---|---|---|---|---|
| E1 | **The Generate form asks what Claude guesses** | format, song (*the one from last time* as a button, the downloads list as today), look (Editorial warm / Swiss signal / Night edition / the app's colours / "surprise me"), the words or number that must appear; each with a default shown, none required (Auto = Claude's call, but the brief then says "a guess") - in English and Spanish | fewer versions from a wrong guess | none |
| E2 | **Versions that change only settings** | Review's *Send it to Claude* carries which parts were rated OK / bad; when the fix is words, colours, the look, the song or the sound only, `improve` changes the settings and B1 re-renders only what changed (its hashes) | a settings-only version ~5-8 min instead of ~19 | a note that asks for a new feel still starts from the plan (never a v2 of a feel the user did not want) |
| E3 | **Saved formats** (0.5.6's step 6, later) | a generated video the user approved saved as a format = its scenes as settings; the next one in that format is new settings, no new plan | the from-zero path under 10 min a minute | after D3 |

**Part F - the environment Claude works in**

| | What | How | Result | Risk |
|---|---|---|---|---|
| F1 | **A permission allowlist** | `.claude\settings.json` `permissions.allow`: `.venv\Scripts\python tools\*`, reads under `analysis\`, `projects\`, `knowledge\`, `refs\` (never writes outside `build\` / `analysis\` - hard rule 1 stays enforced by the tools) | a friend without auto mode stops approving every call | none: the tools refuse writes elsewhere |
| F2 | **Tools take ids and library paths** | `overlay.py settings <template id | library folder>` (it refused a library template in ae_50_test), every tool's error says the command to run instead | one turn a slip | none |
| F3 | **Effort per task, re-measured** (0.5.3's step 8) | after A-C: Generate and edits at medium against high on the same request, `usage.py` before / after, the rating as the gate; the app's recommendation changes only on the user's say | ~1.5-2x fewer tokens per turn where it holds | the user decides |
| F4 | **The measure** | `usage.py project <name> --steps`: per window thinking / writing, waiting on tools, lab jobs (B3), turns, tokens; the live line unchanged | step 9 becomes one command | none |

**Expected results** (hypotheses, replaced by the re-runs' numbers):

| Kind | Today | After A + B + C | After D + E | Tokens |
|---|---|---|---|---|
| a 30 s video from zero (ae_50_test) | 27 min, ~45 turns | 12-13 min, ~15 turns | 8-10 min | 3-4x lower |
| a 52 s talking edit (testing_entire_workflow) | 38.5 min | ~22 min (B, C) | 15-19 min (D1, D2) | 3x |
| a version from the ratings | ~19 min | 12-15 | 5-8 min (E2), or a new build when the feel changes | |
| a review of a reference | 5-20 min | 4-12 min (C8) | | |

Honest limits: the cuts in A-C are counted turns replaced by deterministic tools (high confidence); D3 and E2 are
tools that do not exist yet (medium); the 2026-10-15 estimate also promised 10-12 min and then 0.5.0's templates
moved the cost from writing to checking - so every pair of items is measured before the next is built.

**Order and shipping in parts** (each part: the re-run of the benchmark requests, `usage.py` before / after, the
user's ratings; a drop stops the part):
1. **0.5.3.1 - the rounds** (small, no risk): A1, A2, A4, C5, F1, F2. Benchmark: ae_50_test re-run.
2. **0.5.3.2 - one build**: B1, B3, B4, A6, A5, A3 (the overnight table), B2 measured. Benchmark: ae_50_test, What's
   new 0.4.3.
3. **0.5.3.3 - the brief**: C1, C2, C3, C4, C6, C7, C8. Benchmark: all three + one review session.
4. **0.5.3.4 - the list**: D1, D2 (A7-A9 inside), E1, E2. Benchmark: testing_entire_workflow, a version of it from the
   user's ratings.
5. **0.5.3.5 - the draft**: D3, F3, F4; E3 stays in 0.5.6.

**Tests**: `selftest.py --extended` + `tools\dev\smoke.py` after every `tools\motionlab\` change; the new app words
(Generate's three questions, the Jobs rows for Claude's jobs, Review's changed-parts line) with their Spanish in the
area's part file in the same change (`i18n_check.py check` PASS); the brief's completeness check = a test that every
lesson tagged for the kind, every rule of the ratings block and every verdict of the picked references appears in
`brief.md` or in its `left out` footer (nothing silently dropped); the re-runs above.

**What changes for the user** (plain words): the Generate form asks format, song and look with a default each; a
video's page shows the cut-sheet of the last build and Claude's builds appear on the Jobs page; *What it took* shows
thinking, waiting and the lab's minutes; Claude's windows open on a brief and ask less; friends approve less; the
Review tab's *Send it to Claude* says which parts Claude will change. Nothing changes in the analysis page, the
reviews, Send it to Claude for a reference, Share my knowledge or Claude's memory page.

**Size**: large; it ships in the five parts above. **Needs from the user**: the ratings of each re-run, the pick of
the song / look defaults on the Generate form, and the effort decision in F3. **Needs first**: nothing new - What it
took (0.4.4), precheck and snapshots (0.4.2), the quick draft (0.4.0), the templates' tracks (0.5.0 / the AE batches).

### Claude's time on reviews, scripts and videos (added 2026-10-20)
The user (2026-10-20): "could you add to the plan or roadmap the plans you have to improve the time claude takes to
review a video, write a script or generate a video?" - 0.5.1 made the lab's own steps faster (a lab pass 35.0 s ->
18.9 s); Claude's minutes did not change. Quality first: nothing here may lower the user's verdicts or ratings.
**Review 2026-10-23** (`docs\review_video_time_2026-10-23.md`, every video made so far + ae_50_test measured): its
findings are the plan above (parts A-F).
0. **Measure first**: What it took (`tools\usage.py`) already times Claude per step - 3 real runs each of a video
   review, a script and a generated video; list the slowest steps with their minutes and tokens. No change ships
   without these numbers (F4 makes it one command).
1. **Review a video** (`/analyze-reference`): C8 - the lab writes a draft per event from what it measured (type, frames
   + timecodes, evidence), so Claude checks and corrects it instead of writing from zero; the category summary read
   before a review keeps only verified effects (measured 2026-10-18: up to 50.7 KB, 77 % unverified). Claude still
   looks at every contact sheet.
2. **Write a script / title** (`/write-script`, `/write-title`): a short "your voice" card made from the user's
   rated scripts, read instead of every past script; the request carries the script check's results so Claude starts
   from them; only the guideline sections the request needs are read (C6 for these skills too).
3. **Generate a video**: parts A-E above.
*Ships when*: each of the three takes measurably less of Claude's time on the same inputs (usage.py before / after)
and the user's ratings / verdicts do not drop.
