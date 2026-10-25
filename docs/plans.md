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

## Where it stands (2026-10-25)

Since 0.5.3, four small steps: **0.5.3.1** (114 Motion Graphics templates), **0.5.3.2** (Film it hands over to the
Editor, Finish it with Claude), **0.5.3.3** (2026-10-25: 0.5.4's steps 1, 2 and 6 - recorded sound effects from this
PC's library, quick drafts with their own sound effects, every effect 2 dB lower) and **0.5.3.4** (2026-10-25: step 3
(a) - a song from a link, a copy without it to post). 0.5.4 stays open: a music library, ambience, voice-over,
separating music from voice, and the rating on two real videos. **Right after 0.5.4** (the user, 2026-10-25: "after
the 0.5.4 lets run the impeccable check on the app"): Impeccable's checker (pbakaus/impeccable, `detect`, no AI, its
telemetry off, the skill and its hooks not installed) on the app's pages, then fix what it finds (ideas.md, *GitHub
repos checked 2026-10-25*).

Released last: **0.5.3** (2026-10-24, CHANGELOG.md + CHANGELOG.es.md) - Faster videos (one build, the brief, the edit list, quick drafts for Generate, the waits as jobs) + a friend's asks (photos in edits, folders, no Mac / iPhone junk, pages that update by themselves, the NEW badge, Improve my script keeping one card, changes that survive updates, MotionLab's own taskbar icon) + *Preview your thumbnail* + fewer zooms in edits. Its plan text: plans_history.md. Still open from it: the re-runs (ae_50_test, testing_entire_workflow, What's new 0.4.3) with `usage.py project <name> --steps` before / after - the halving was not measured before the release (the user's call, 2026-10-24) - and F3 (the effort per task) after them; the Resolve builder does not place photos.

Before it **0.5.2** (2026-10-22) - New edit, step by step (the pop-up's six steps, the clips as pictures, edit_brief.md for Claude), a script's pop-up in three tabs with its road, a lighter Home and Claude's memory. Re-planned the same day from the user's notes (plans_history.md, *Renumbers*): 0.5.4 = Sound, 0.5.5 = Content agency, yapping mode -> 0.5.9; the prompt generator and templates by feel removed.

Before them **0.5.1** (2026-10-19, CHANGELOG.md + CHANGELOG.es.md) - Phase 2 opens: the
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
| 0.5.4 | Sound | in progress - recorded sound effects + quick drafts with sound shipped in 0.5.3.3; open: music from a link or a library, ambience, voice-over, stems, a reference's sound effects (added 2026-10-22; widened 2026-10-25) | M |
| 0.5.5 | Content agency: My Brand | planned - a My Brand page above the Analyser: goal, audience, identity, the catalogue with prices from the website; used by Prepare, New edit, Motion Graphics; product motion (added 2026-10-22); the mini-editor for cuts and effects, mood boards from pictures; quality over quantity (2026-10-25) | L, ships in parts |
| 0.5.6 | Motion graphics: template packs | planned - the library shipped in 0.5.0; Resolve / After Effects / Lottie packs read exactly (AE with py-aep, no AE needed - 2026-10-25), templates used as they are, 3D blocks (Three.js), the motion check, formats, a preview before the render | L, ships in parts |
| 0.5.7 | Colour + DaVinci Resolve | planned - measuring a look + the match LUT shipped in 0.4.0; + the edit as a timeline file for Premiere / Final Cut (2026-10-25) | M |
| 0.5.8 | Content generation | planned - AI clips back into the lab, pictures from image tools (voice and music moved to 0.5.4, 2026-10-22) | M |
| 0.5.9 | Yapping mode | planned - talking quick draft + talking-head pack shipped; starts with the content foundations; + the clips a script needs (from 0.5.0, 2026-10-15) (moved from 0.5.2, 2026-10-22); + *Research it* for scripts, shorts from a long video (2026-10-25) | L |
| 0.6.0 | Take notes from videos: competitors, videos, courses | later - transcripts, numbers, the content panel shipped; courses added 2026-10-15; competitor analysis added 2026-10-25 | L |
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

## 0.6.0 - planned - Take notes from videos: competitors, videos and courses

**Ships when**: a collection of ~10 analysed videos gives its topics with counts and quotes (frame + timecode), each
video's content reviewed Correct / Partly / Wrong by the user like effects, and searchable from Claude; a course of
~10 lessons gives the steps each lesson teaches (frame + timecode, the screen shown) and a course summary Claude
uses when it edits; a niche of ~10 profiles the user picked is scanned, its ~20 outliers get the light pass overnight
on a laptop setting, and its niche card - each reason with its videos and frame + timecode - is rated by the user.

**Renamed 2026-10-22** (the user: "Rename 'describe videos' to 'take notes froms videos'"); older notes call it
*describe video*. Competitors added 2026-10-25.

**Competitor analysis** (the friend's points 3 and 5, 2026-10-25, pasted by the user: "un análisis de competencia
estaría súper potente coger los 20 vídeos más virales de la competencia ... analiza los 20 perfiles más influyentes y
más reconocidos en instagram, tik tok y YouTube y de esos perfiles analiza sus 20 vídeos más virales, extrae el guion,
efectos de sonidos, música, planos ..., b roll y que te de una explicación de porque han funcionado ... y lo mismo
para otros ámbitos"; "centrarte en pasarle cantidad, que pueda imitar los efectos, planos, recursos, sonidos,
transiciones ... que entienda los guiones"). 20 profiles x 20 videos x 3 platforms = up to 1,200 videos: at today's
depth (a lab pass + Claude's frame-accurate review each) that is days of a PC and far beyond a Claude plan - so three
depths, wide and cheap first:
1. **Scan** (no download, seconds per profile): the user lists the profiles (Claude can suggest some for a niche from
   a web search; the user ticks them); yt-dlp lists each one's videos with views, likes and dates -> each video
   against its own profile's usual views (the outperformer score; `content.py stats` does it for one video since
   0.3.2) -> the top ~5 per profile. YouTube and TikTok work without a login; Instagram needs Settings > Downloads'
   browser login.
2. **A light pass on the outliers** (MotionLab, no Claude): download, the lab pass (cuts, pacing, beats, the first
   3 s, camera moves), the words by speech to text, music and its tempo, sound effects (0.5.4 step 7), one sheet of a
   key frame per shot. Measured on a laptop first: the time per minute of video decides how many fit in a night
   (0.4.5's bulk runs them).
3. **Why it worked** (Claude, per niche, in batches): the numbers, transcripts and sheets of ~20 outliers against ~10
   of the same profiles' weakest videos - what differs, not what they all do: the hook, the script's structure (HEIT,
   0.5.9), the format, music, sound effects, shots and B-roll, what keeps people watching; each reason with the videos
   and frame + timecode it comes from -> a niche card in Claude's memory (text, shareable), read by Prepare
   (*Research it*, the formats), New edit (the style of a niche) and the quick draft.
The deep, frame-accurate analysis stays for the few videos the user wants to copy (the Analyser, as today). Rules:
public posts only, the videos and transcripts stay on the PC, only numbers, short quotes and the niche card are
shared.

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
     **Research it** (the friend's point 2, 2026-10-25: "añadiría la opción de investigación para que recopile toda la
     información posible sobre lo que vas a decir ... contradecir las costumbres ... qué errores comete la mayoría de
     personas ... que se base en unas estadísticas ... formatos virales tipo, 3 errores que todo el mundo comete"): a
     *Research it* tick in Prepare's two scripts - Claude searches the web for the topic's common mistakes, myths and
     numbers before writing, and offers formats that work for it (*3 mistakes everyone makes*, myth vs fact, *stop
     doing X*, before / after). Every number and claim carries the link Claude opened and found it in (like the text
     sets' quote check - an unchecked number is left out, never guessed); the sources sit in the script's Details.
     Which formats work comes from videos that did well against their channel (0.6.0's competitor analysis), not from
     Claude's taste. Small (the skill + one tick, no new tool) - it can ship early on its own, like Prepare did.
  2. **Record**: a one-page brief - format, length, the HEIT outline with seconds, delivery notes, the environment
     to try.
  3. **Edit your raw recording** (read-only, hard rule 1): your words with timings (local Whisper - own footage has
     no platform subtitles), silences and fluffs cut on word boundaries, punch-ins at a chosen reference's rhythm,
     text on screen and captions as HTML overlays timed to your words (0.3's HyperFrames, 0.3.2's captions; the SRT
     onto Resolve's subtitle track by script, tested in the scratch project), a visual hook in the first 3 s, B-roll
     slots (your clips; generated ones in 0.7) -> a lab render, then the Resolve build. You approve the cut list
     (every removed part with frame + timecode) before anything renders.
  4. **Check**: the first 3 s say the hook, the HEIT parts land at their target seconds, the extras are there.
  5. **Shorts from a long video** (the user, 2026-10-25: "get shorts from a long video (analyze contenct and
     transcript) and see which moments could make good shorts?"): a podcast, a talk or a long video of the user's ->
     its words with timings (faster-whisper) -> candidate stretches of 20-60 s, which Claude scores the way the
     clipping tools do (OpusClip's score: hook, flow, value, trend): a hook that works without what came before, no
     "as I said", a payoff, energy (loudness, laughter), length; "trend" = what 0.6.0's competitor scan found - each
     candidate with frame + timecode and why, the user picks. Then each pick as a vertical short: reframed 16:9 ->
     9:16 by face detection sampled ~5 times a second (MediaPipe's BlazeFace, ~3 ms a frame on a phone CPU), a still
     or a following frame chosen per scene (AutoFlip's design), the speaker kept when two talk; screen recordings as
     screen + face, not a crop; captions and a hook title from yapping mode. Built in the lab - ClipsAI (torch,
     pyannote with a Hugging Face token) and OpenShorts (Gemini by default) are read for ideas, not installed.
     Measure first: the minutes per 60 s short on a laptop CPU; the reframe's misses (OpusClip's own benchmark: the
     wrong speaker, charts cut off, half people, lower thirds cut).
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
- **Other editors** (the friend's point 4, 2026-10-25: "fusionar premier, after effects y da vinci para que Claude
  edite en los tres aprovechando los puntos fuertes de cada uno"; was *Export to other editors* in ideas.md): the
  plan as a timeline file Premiere Pro, Final Cut and the free Resolve open (FCP XML / OpenTimelineIO) - the cuts,
  speed changes, the graphics as transparent clips, the sound effects on their own track, the grade as the .cube;
  checked by opening it in each and comparing against the lab render (frame + timecode). Kdenlive too (free; through
  the OTIO Kdenlive adapter, MIT, "might be unstable") - an editable project for friends without Resolve Studio,
  since the free Resolve 21.1 can no longer be scripted. After Effects joins through
  0.5.6 step 4 (a template rendered by `aerender` into a clip). Not planned: Claude driving all three at once - Resolve
  already gives the edit and the colour, HyperFrames the motion graphics; Premiere's and After Effects' scripting
  needs paid Adobe apps most friends lack (ideas.md *Later*).

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
   measured first (Starter Pack alone is 228 templates). **After Effects without After Effects** (checked
   2026-10-25, the user: "try ... free open source programs people have recently reverse engineered"): `py-aep`
   (MIT, pure Python, 0.18.2 of 2026-10-17, pypi.org/project/py-aep) reads and writes .aep projects - compositions,
   layers, keyframes, properties - with no After Effects installed; it cannot render or evaluate expressions (those
   stay numbers to read, a preview needs `aerender`). So an AE pack's keyframes can be read exactly on any PC - a
   small test first on one pack the user owns (its licence decides what may be converted).
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
   **3D blocks** (the user, 2026-10-25: "add 3d motion graphics that work well"): the HyperFrames runtime the lab pins
   already has a `three` adapter (checked in `node_modules\hyperframes` 2026-10-25: each frame's time reaches the
   scene through `hf-seek` / `window.__hfThreeTime`, and it waits for THREE's loading manager) - so Three.js scenes
   (3D type, a phone or laptop turning, logo extrusions, depth of field, bloom; CC0 HDRIs from Poly Haven) render like
   any block. Measure first on a laptop: seconds per second of 1080p with hardware WebGL vs the software fallback
   (SwiftShader, reported ~4-10x slower - unmeasured); the three to five that look premium, not many. Blender Eevee
   (minutes per second on a laptop, a 383 MB program) only later, for short hero shots.
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
    **Checks taken from open-source skills** (reviewed 2026-10-25, the user: "analize open soruce skills taht we could
    use for those specific sections"; github.com/alesha-pro/tools, MIT at its root, its motion-reel "adapted from" a
    course - so ideas, never its text, and nothing installed): frames rendered out of order compared with in order
    (a graphic that depends on the previous frame shows up); the text read at a 360 px phone width; a sheet of the
    frames around every fast move, not only the key frames; Claude's critique capped at 3 rounds of 3 fixes. From its
    lyric-video skill, for lyric edits: a pilot section approved before the whole video, words timed by syllable,
    checks at the seams between sections. HyperFrames' own skills (Apache-2.0, `hyperframes`, `media-use`) are read
    for the blocks.
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
places a product - in passing or as a call to action at the end - and the user rates it OK or better; a cut, an
effect and a caption fixed in the mini-editor render again without Claude; a mood board's style card is used by a
video the user rates good.

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
6. **The mini-editor** (the user, 2026-10-25: "for the 0.5.5 agency brand section i need you to add also a
   "mini-editor" so we can handle small cuts or edits withotu having to re-run the entire program under claude"): on
   a video's page, the newest render's plan as a strip of shots under the player (each shot's picture, its first frame
   + timecode, its length). Small changes by hand, no Claude window: trim a shot's start / end frame by frame, delete
   a shot (what comes after closes up - graphics, captions and sound effects move with it), move a cut, swap a shot
   for another take from the same clips, fix a caption's or a graphic's words, drop or nudge a sound effect, the
   song's start and volume. *Save* = the next plan (`plan_v(N+1).json`, the old one stays) + a `build.py` job (only
   what changed renders again: a trim = the video and the sound, no graphic). Bigger wishes (a new effect, another
   style, re-timing to the music) stay Claude's: *Ask Claude* writes the change as a request. What the user fixed by
   hand goes into `outcome.json` so Claude reads it next time (the cuts it got wrong are lessons too). Measure first:
   a one-shot trim's build time on a laptop. Never touches the clips (hard rule 1).
   **The effects too** (the user, 2026-10-25, later: "so if we do the mini editor on the version we can maybe choose
   some effects, edit them?"): each effect of the plan as a chip on the strip at its frames (a zoom, a whip, a flash,
   a speed ramp, a graphic) - swap it for another kind or a library effect, change its length, strength and ease
   (the easing words: decelerating, S-curve...), nudge it a frame, remove it, add one at the playhead; before *Save*,
   a preview of the second around it (`render_video.py` renders any range alike), so a change is seen, not guessed.
7. **Mood boards: references beyond videos** (the user, 2026-10-25: "what if our references go beyond just videos?
   add instagram or pinterest directly?"): pictures the user likes - a Pinterest board, Instagram posts, screenshots -
   as references for the brand's look. First from pictures on the PC (saved or screenshotted, dropped into the
   Analyser): per board a style card - the palette (Lab clusters, saturation, contrast), text on the picture (OCR:
   how much, where, how big), faces (count, size, place), composition (thirds, empty space, clutter), and Claude's
   words for the type and the mood - used as My Brand's identity, New edit's palette, Motion Graphics and thumbnails.
   Fetching a board by its link (gallery-dl - GPL, reads Pinterest boards without a login) only later and started by
   the user: Pinterest's and Instagram's terms forbid automated collection, and Instagram needs the account's cookies
   (a risk to the account) - so never by default, never Instagram cookies. The pictures stay on the PC.

**Quality over quantity** (the user, 2026-10-25: "for the content agency version section id like to focus on quality
of videos instead of quantity ... we have to really dig in those things if we want to make motionlab great and
actually usable and not just make AI slop while editing"): this version is judged by how good one video gets, not by
how many - the mini-editor (6), the brand's own look (3, 7) and the user's ratings decide; 0.6.0's wide scan is for
learning only, never for making more videos.

**Order** (the user decides): 1-3 first, then 4 and 5; 6 and 7 need nothing from My Brand's page. **Size**: large,
ships in parts.
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
   **Built 2026-10-25, released in 0.5.3.3** (with step 1: `library\sounds\`, 108 recorded, on this PC only). The user's listen
   of the A/B demo (28 cues on EsDeeKid - Century): **B, the library, sounds better** ("b sounds better i guess") -
   not yet the *Ships when* rating on two real videos. Then "the sounds are a kind too high but other than that good
   enough" -> `sfx.TRIM_DB` -3 -> -5 (every level 2 dB lower; the -24 dB song floor holds, so the quiet ones - clicks,
   keys, air - move less). The demo page's third player = B at the new level.
3. **Music and ambience from public libraries**: picked by mood, tempo and length (`beats.py` measures them), only
   with clear licences (CC0 / free for commercial use; CC BY = its credit line goes into the publish package's
   description); room tone and ambience beds (city, nature, a café) under talking videos. New edit's *Music* gets
   *From the library*. Widened by the friend's notes (2026-10-25, below):
   - (a) **A song from a link, in the Sound step** (small - the Analyser's downloader, its MP3 preset, into
     `refs\audio\`): paste a TikTok / YouTube / SoundCloud link, the edit cuts on that song's beats. A viral song is
     someone's copyright: the render comes twice - with the song (to watch) and without it (to post; the same sound
     picked in TikTok / Instagram, with where it starts, e.g. "the sound from 0:12.40") - so a post is never muted.
     **Built 2026-10-25, released in 0.5.3.4** (the user's pick): New edit's Sound step *From a link…* (the `download` job,
     preset mp3, the song picked when it ends); `publish.post_copy` after every render of a quick draft or a build
     whose song lies in `refs\` -> `build\publish\<render>_post.mp4` (the same video stream, copied; the sound effects
     stem or no sound) + `post_copy.json` (the song, where it starts, its link); *Ready to post* shows it. Measured on
     a 15 s draft on a downloaded song: the copy's video packets identical to the render's, its sound = the effects
     stem (correlation 1.00; 0.10 with the render's mix), 0.17 s to make; the app tested in headless Edge on a copy of
     the lab (the download picked the song, the summary named it, Ready to post showed "from 0:11.63").
   - (b) **A music library on the PC** (like `library\sounds\`): Pixabay Music and YouTube's Audio Library have no
     API for music - the user downloads tracks there (YouTube's only for YouTube videos) and MotionLab indexes them
     (tempo, mood, length, licence); sites with an API and commercial-use licences (Jamendo, Freesound, Free Music
     Archive - each checked live) searched from the app. Never automatic downloads from YouTube: covers, sped-up
     versions and unknown licences are why *Trending sounds* was scrapped (plans_history.md, 2026-10-15).
4. **Voice-over** (was content generation's step 1, measure first): ElevenLabs (the user's own account) or a local
   text-to-speech measured on a laptop first (time per minute of speech, size, how natural); its words timed like
   speech to text, so captions and scenes follow the voice. A voice only with the speaker's consent.
5. **Separate music from voice** (from ideas.md, measure first - heavy on CPU): Demucs stems for cleaner beats / drops
   and cleaner speech, and to lower the music under the voice.
6. **The quick draft's `--sfx`** (open since 0.4.1.1): the draft places its effects as cues, `sfx.py plan` makes them.
   **Built 2026-10-25, released in 0.5.3.3**: `draft_edit.py --sfx few | some | many | auto [--sfx-kinds]` (New edit's step 5
   passes it; Auto = few for a talking video, else some) -> the plan's `"sfx"` {amount, kinds, first = the drops} thins
   the effects' cues (`sfx.choose`: the drops first, then hits > risers > whips > whooshes, 5 / 2 / 0 s apart), the
   mix becomes its audio; punch-ins on one take = a whip peaking on the cut (a talking draft had no effect with a
   sound before); *Finish it with Claude* lists them under *Stays*. Self-test `check_draft`. Measured on the
   synthetic test clips: a 30 s music draft = 3 effects (2 hits, 1 tick, all recorded), a talking draft = 3 whips,
   each peaking inside its cut frame; ~1.5 s added. Still open: plain cuts get no sound (a beat montage's 31 cuts ->
   3 effects at *some*) - the user's listen decides.
7. **A reference's sound effects, measured** (the friend's point 5, after step 5 - measure first): the whooshes and
   hits of an analysed video found apart from its music (the stems), placed against its cuts and effects with frame +
   timecode -> *like the reference* in New edit's Sound step uses its amount and kinds. A self-test with known cues
   first.

**The friend's notes (2026-10-25, in Spanish, pasted by the user)**: "en sonidos ... tener un descargador como el del
analizador pero que solo se quede el audio ... si hay una canción viral en tik tok, coger descargarla justo en el
apartado de sonidos y que trabaje con esa música, o tener conectado a pixabay, YouTube y algunas otras apps de música
libre de derecho de autor" (a downloader in the Sound step that keeps the audio; a viral TikTok song or free music
from Pixabay, YouTube and other royalty-free sites) -> step 3 (a) and (b).

**Not here**: viral / trending sounds are copyrighted - the lab never fetches them by itself, and the render you post
leaves them out (step 3 (a): you add the same sound in TikTok or Instagram); the *Trending sounds* plan was scrapped
2026-10-15. Music made by a model stays out until a light one with clear commercial terms exists.
**Order** (the user decides): 1, 2 and 6 shipped in 0.5.3.3; then 3 (a first - small), 4, 5, 7. **Size**: medium.
**Rules**: light and tested first; every file's licence recorded; music and voices only with clear licences and
consent; generated voices labelled as generated.
**Needs first**: nothing - New edit's sound step (0.5.2) already asks for it.
