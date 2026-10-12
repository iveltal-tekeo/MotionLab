# MotionLab - planned versions

What comes next and how it should plug into the lab. The app shows these under *What's new* as "planned" (newest
plan on top); the release itself goes into `CHANGELOG.md` when it ships (never put planned versions there: the
Update button treats every version heading in CHANGELOG.md as released). Headings: `## x.y.z - planned - title`.
Written 2026-10-09 from the user's notes (re-planned 2026-10-11 and, from the user's notes, 2026-10-12); the user decides scope and order - ask before starting a plan.

## 0.7.0 - planned - AI B-roll and cinematics

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
- **Shot requests come from the analysis** (`/write-prompt`, shipped in 0.3.1, already writes them as text; 0.7 adds the paid
  API call): for reference shot fA-fB Claude writes the request - length (frames at
  the plan's fps, rounded up to the model's minimum, trimmed in the plan), aspect and size, camera move (measured
  pan / zoom from events.json), light and look (contact sheets + the plan's grade), subject from the user's story.
  Image-to-video starts from a frame of the user's own footage so the look matches.
- **In `/recreate-video`**: step 3 ("where the footage has nothing comparable") offers *Generate this shot* with a
  cost estimate; the user approves each paid generation. "By feel" edits (0.5) can ask for whole sequences.
- **Files**: `projects\<name>\build\generated\<id>.mp4` + `generated.json` (prompt, model, seed, reference frames,
  cost, date - provenance); registered in `sources.json` as sources G1, G2... with `"generated": true`, cached by
  prep_footage, used in plans like any clip, imported by resolve_build as media. The user's own clips stay
  read-only as always.
- **Costs and keys**: the API key lives only on the PC (settings.json or the Windows credential store, never in the
  repo or in shared knowledge); a cost estimate and an explicit OK before every paid job; a budget per project;
  every spend logged. Generation runs as an app job (group net).
- **Rules**: no likeness of real people without their consent; AI clips are labelled as generated in the project
  and its Resolve timeline; the provider's terms apply.
- **Needs first**: 0.5 (story-driven edits); 0.3's colour pipeline (done).

## 0.5.0 - planned - Templates by feel + macOS

- **Use a reference as a template**: its feel and pacing - shot lengths, cuts on the beat, effect families, the
  structure of what is said (0.4's HEIT structure, the yapping profile) - with your own story, length
  and music instead of a 1:1 copy. Builds on the
  pacing numbers (`knowledge.pacing`), the effect library and the HTML graphics (0.3).
- **A macOS version** of the app (the lab is Python + a browser window; Edge-only parts, the Recycle Bin, `.bat`
  files and the Windows paths need macOS twins; DaVinci Resolve's scripting paths differ).

## 0.4.1 - planned - Prompt generator: every model, every specialty

**The user's notes (2026-10-12):** "prompt generator (easier): we should have a 'database' of good prompts based on
prompts we have given and you have analysed structurally so we can generate good prompts for our model agents
(seedance, claude, chatgpt), every category or every specialty."

- **Already shipped (0.3.1, 2026-10-12)**: the database and the generator for three kinds - the *Prompts* page,
  `knowledge\local\prompts\<kind>\<id>.json`, `tools\prompts.py`, MCP `prompts()`, the `/write-prompt` skill: each
  prompt split into its structure (slots), 3 new variants built on the best-rated examples, your rating of what the
  model made (good / ok / bad + a note) moves the good ones to the top; shot prompts can be filled from a reference's
  frames (measured camera move, look). Kinds: `shot` (Seedance / Higgsfield / Kling), `hook`, `script`. Empty until
  you add your prompts (~10 per kind; the tested ones count most).
- **To do**:
  - **Text-model prompts** (Claude, ChatGPT, agents): a kind `agent` with its own slots - role, context, task, steps,
    constraints, output format, examples - so a prompt that worked in one chat becomes a template for the next.
  - **Per category / specialty**: every prompt gets a specialty (the lab's categories - music video, vlog, cooking,
    ... - plus your own, e.g. "make money online", "fitness"); the page filters by it and `/write-prompt` copies
    examples of the same specialty and the same model first.
  - **Per model**: the model a prompt was written for stays part of its structure (Seedance's lengths and camera
    words, Claude's tags...); a new prompt for another model says what it changed.
  - **Filled by the analyses**: the first 3 s of every analysed talking video become hook examples, its HEIT
    structure a script example (0.3.5 / 0.4), with the link and frame + timecode.
  - **Sharing** your own prompts and ratings through *Knowledge > Share* (text); creators' prompts stay on the PC.
- **Needs**: your prompts (the Prompts page or pasted in the chat).

## 0.4.0 - planned - Yapping mode: the yap-maxing framework

**The user's notes (2026-10-12):** "using the v0.3.5 as an exceptional tool when creating a video: 'yapping mode' or
talking to the camera. Focused on content creators: yap maxing framework. Influential videos, lots of views videos.
Basically making content short or long form; take into account formats. HEIT framework = hook / explain / teach /
illustrate. Validated topics. Copy and learn structure. Extras: 1) text on screen 2) environment: experiment
different environments 3) delivery: authentic content 4) graphics: visual hooks." (Earlier, 2026-10-11: analyse
talking-head creators AND edit the user's own recording that way.)

- **Goal**: learn from talking-to-camera videos that work (many views) and make your own - short or long form - in
  the same proven structure, from the topic to the finished edit in the lab and in DaVinci Resolve.
- **Learn** (from 0.3.5's analyses of influential videos):
  - **Validated topics**: topics of videos that outperform (views against the channel's followers / usual views,
    0.3.5), per niche - not just any topic, the ones the audience already proved.
  - **HEIT structure**: every talk split into Hook / Explain / Illustrate / Teach parts with frame + timecode and
    seconds; per format (short <= 90 s, mid, long; vertical / horizontal - measured already) the usual order and
    share of each part = the structure to copy and learn.
  - **The four extras, measured per video**: *text on screen* (how often, how many words, where - 0.3.5's on-screen
    text); *environment* (the setting of each shot - 0.3.5's descriptions; your own videos log theirs, so trying
    different environments becomes a comparison); *delivery* (words per minute, pauses, energy = loudness changes,
    looking at the camera - light numbers + Claude's notes on how authentic it feels); *graphics / visual hooks*
    (what happens on screen in the first 3 s: a cut, a zoom, a text pop, a graphic - from the edit analysis).
  - **The edit's yapping profile**: jump cuts inside one talking shot (a pause cut out), punch-ins (a 1.1-1.3x scale
    step, held), word captions, B-roll cutaways over continuing speech - new detectors, each with a synthetic
    self-test video and ground truth first.
- **Make (yapping mode)**:
  1. **Topic + script**: pick a validated topic (or yours); `/write-prompt` writes the hook and a HEIT script in the
     structure of the best videos of your format (0.4.1's database).
  2. **Record**: a one-page brief - format, length, the HEIT outline with seconds, delivery notes, the environment
     to try.
  3. **Edit your raw recording** (read-only, hard rule 1): your words with timings (local Whisper - own footage has
     no platform subtitles), silences and fluffs cut on word boundaries, punch-ins at a chosen reference's rhythm,
     text on screen and captions as HTML overlays timed to your words (0.3's HyperFrames, 0.3.2's captions), a visual
     hook in the first 3 s, B-roll slots (your clips; generated ones in 0.7) -> a lab render, then the Resolve build.
     You approve the cut list (every removed part with frame + timecode) before anything renders.
  4. **Check**: the first 3 s say the hook, the HEIT parts land at their target seconds, the extras are there.
- **Steps**: (1) 3-5 influential talking videos you pick, analysed by 0.3.5; Whisper measured on one of them
  (`tools\dev\whisper_bench.py`, tiny / base / small on a laptop setting) -> you pick the engine; (2) HEIT labels +
  the extras' numbers on them; (3) the yapping detectors + self-tests; (4) brief + the edit of your own recording.
- **Needs first**: 0.3.5 (describe video, incl. the words of your own recordings for captions).
- **Started 2026-10-12** (the user asked for "minimal motion graphics for a good content creator talking head
  video"; not released): `tools\overlays\examples\talking-head-pack` - progress bar, hook title, number pop-ups
  (a counter for numbers that count up), a numbered list built point by point, an end card; the look = settings
  (accent, text colour, font, size, height on screen, progress bar, panel opacity), WHAT shows WHEN =
  `assets\beats.js` (texts + frames, written from the transcript - Claude's part in yapping mode).
  `overlay.py fit <folder> --like <video>` takes a video's size / rate / length. First use: the user's
  `projects\talk_test` (vertical 1080 x 1920, 30 fps): beats on the frames of the spoken words (57 at f1087
  (00:00:36:07), the list's points at f1524 / f1601 / f1692), with the speech captions underneath; a 720p preview
  went to the user's phone. Next: a beats writer (Claude from the transcript, HEIT labels) and the pack's
  styles per category.

## 0.3.5 - planned - Describe video: videos as information

**Carried over from 0.3.2** (released 2026-10-12, see CHANGELOG.md; its Resolve measurements: docs\resolve_notes.md):
captions from the user's own recordings - captions from any .srt / .vtt work since 0.3.2; for a recording without
one the lab needs speech to text: measure the engines on the user's talking video (script:
`.app\dev\whisper\script_v1.txt`, the recording into `projects\talk_test\`; HyperFrames' `transcribe` = local
whisper.cpp / Parakeet with `--to srt`, and faster-whisper `tools\dev\whisper_bench.py`, tiny / base / small, also on
a laptop setting), the user picks one, then `overlay.py captions` takes a recording directly.
**Measured 2026-10-12** on the user's recording (72 s, phone, read from the script with own changes - so every
engine's error rate below includes those; `tools\dev\speech_bench.py`, report `projects\talk_test\build\speech\`):
faster-whisper int8 on 4 threads: tiny 39.9 % (2 s, 75 MB), base 28.4 % (3.4 s, 141 MB, 360 MB RAM), small 26.1 %
(12.9 s + 5 s load, 464 MB, 730 MB RAM) and **21.1 % with the video's names as a prompt** (MotionLab, 4AM, Nemzzz
right - base with a prompt dropped a whole paragraph); Parakeet (HyperFrames, `models install parakeet`: 640 MB,
5 s here, ~20 CPU-seconds, 1.15 GB RAM, 25 European languages, no names prompt) 26.1 %. HyperFrames' whisper
engine needs whisper.cpp built by hand on Windows - out. Word starts agree within 0.02-0.12 s (median) between
engines. Names are what every engine gets wrong without help.
**Decided + built 2026-10-12** (the user picked faster-whisper small, base as the light option; not released):
`motionlab\speech.py` + `tools\speech.py install | status | transcribe` (optional: Settings > Programs > Speech to
text > Install = the pinned faster-whisper 1.2.1 in the lab's venv + the small model; names via --names / the
dialog, ignored by base); `overlay.py captions --from <a video>` (size / rate / length from the plan or the video -
phone videos stored lying with a 90 deg flag count as upright); App: Graphics > *Captions...* = from the words in a
video (a render of the edit or a clip) or from a subtitle file. Measured on the user's recording: 214 words in
14.5 s, captions at 1080 x 1920, 30 fps, 2159 frames (UI test 9/9). Still open here: references without subtitles
(content.py transcript falling back to speech), Parakeet as a later option. Also: the SRT onto
Resolve's subtitle track by script (test in the scratch project); the HTML clock's grain tuned to the lab's texture.

**The user's notes (2026-10-09, again 2026-10-12):** "describe video: instead of focusing on our already existing
analyze video for effects, transitions and pacing, we focus on analysing videos informatively (the content inside
the video) so we can get all the information from audio and video and generate notes accordingly in our UI to
correctly apply to video recreation or other tools. So if we analyse 10 videos related to making money online we can
get common topics, add notes, ask about it... similar UI as references but dedicated to content as information
instead of filmmaking / effects." Planned as 0.4 (2026-10-09), then 0.6 (2026-10-11); 0.3.5 since the user's notes
of 2026-10-12: it is the base tool of 0.4's yapping mode.

- **Done (0.3.1)**: what is said - `tools\content.py transcript <name>` (the platform's subtitles, frame + timecode
  per line and word), MCP `transcript`.
- **Shipped in 0.3.2** (2026-10-12): **performance** - `content.py stats <name>` (one `yt-dlp -J` request, no
  download; the transcript fetch saves them too) -> `content\stats.json`: views, likes, comments, the channel's
  followers, upload date, **views ÷ followers** (the outperformer score), views a day, and a history of every fetch.
  4AM: 3,434,506 views, 768,000 followers = 4.47x, 56,722 views a day since 2026-08-13. **App: a Content tab** on
  the analysis page (the numbers + *Update the numbers*; the transcript with frame + timecode, a click moves the
  player, the line being said is marked, search, *Get the transcript* / *Fetch again*). UI test 12/12. Not yet:
  saving the numbers at download time, the numbers in shared cards, topics / shots / OCR / collections.
- **Audio = what is said**: the transcript (local Whisper for videos without subtitles - measured first, see below),
  split into topics, with the claims, numbers, tools / products, steps, the hook (first 3 s) and the call to action.
- **Video = what is shown**: per shot (the lab already finds every cut) a short description by Claude - setting /
  environment, who and what is on screen, talking head or B-roll, graphics - read from a sheet of one key frame per
  shot (about 20 shots per picture keeps the tokens low); text on screen with a light OCR engine (measure first:
  Windows' built-in OCR needs no install; on 2026-10-09 the user said "OCR not now", the 2026-10-12 notes ask for
  text on screen).
- **Performance**: views, likes, comments, the channel's followers and the upload date, saved by the download
  (yt-dlp knows them; today `refs\downloads.json` keeps link, platform, uploader, id, duration) -> an outperformer
  score (views against followers) that 0.4 turns into validated topics.
- **Notes**: your notes per video and per topic (one home), read by `/recreate-video`, `/write-prompt` and 0.4.
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
- **Measured so far**:
  - **Transcripts (0.3.1)**: `tools\content.py transcript <name>` (yt-dlp: uploaded subtitles in the video's
    language, else YouTube's auto captions of the original audio, which carry word timings) ->
    `analysis\<name>\content\transcript.json / .txt`, frame + timecode per line and per word; `content.py show`;
    MCP `transcript(reference, start, end, words)`. 4AM: 72 lines / 463 words in ~7 s. Timings are the platform's,
    not measured by the lab.
  - **Measuring Whisper**: `tools\dev\whisper_bench.py <name>` (faster-whisper int8 on the CPU in a separate venv,
    each model in its own process, `--threads 4` ~ a laptop; WER and word-timing difference against the subtitles).
    First run, mechanics only (4AM is rap over a beat, so its WER says nothing about talking videos): tiny = 75 MB
    model, 318 MB RAM, 27x real time on 4 threads of the RTX 4070 PC's CPU (a laptop core is slower). Still to do:
    tiny / base / small on a talking video the user picks (0.4 step 1), then the user decides.
  - Other engines seen 2026-10-09: HyperFrames (in `tools\overlays\`, optional, needs Node) has a whisper.cpp
    `transcribe` command; ffmpeg's `whisper` filter is in BtbN builds but NOT in Gyan's essentials build (CI's; winget's
    full build: unchecked).
