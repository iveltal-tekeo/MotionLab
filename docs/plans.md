# MotionLab - planned versions

What comes next and how it should plug into the lab. The app shows these under *What's new* as "planned" (newest
plan on top); the release itself goes into `CHANGELOG.md` when it ships (never put planned versions there: the
Update button treats every version heading in CHANGELOG.md as released). Headings: `## x.y.z - planned - title`.
Written 2026-10-09 from the user's notes (0.4 / 0.6 re-planned 2026-10-11); the user decides scope and order - ask before starting a plan.

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
- **Shot requests come from the analysis** (0.4's `/write-prompt` already writes them as text; 0.7 adds the paid
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

## 0.6.0 - planned - Collections and topics: videos as information

**The user's words (2026-10-09):** "if we analyse 10 videos related to making money online we can get common
topics, add notes, ask about it... similar UI as references but dedicated to content as information instead of
filmmaking / effects." Moved here from 0.4 on 2026-10-11 (the user made prompts + yapping 0.4's focus).

- **Goal**: next to the edit analysis, a *content* analysis of a set of videos on one subject (e.g. 10 "make money
  online" videos): the topics they share, who says what, where they disagree, what nobody covers; your notes; ask
  Claude about the whole set.
- **Per video**: 0.4's transcript and hook > points > proof > CTA structure, plus segments by topic and the claims,
  numbers, tools / products and steps per segment (an `/analyze-content` skill -> `content.json`, reviewed by the
  user like effects: Correct / Partly / Wrong). On-screen text (OCR): not now (the user, 2026-10-09).
- **Collections**: a tag (e.g. `make-money-online`, ~10 videos) groups references; `content.py collection <tag>`
  counts topics across the videos with links to the exact frames, agreements and contradictions, gaps ->
  `knowledge\local\collections\<tag>\`. Your notes per topic are stored there too (one home, like verdicts.json).
- **App**: on a reference a *Content* tab (transcript with clickable timecodes that move the player, topic chips,
  claims, hook / CTA), and a *Topics* page per collection (topic cards with counts, quotes that open the frame,
  your notes, *Ask Claude about this collection* = a Claude window with the collection loaded).
- **MCP**: `topics(collection)`, `search(text)` next to 0.4's `transcript`, so Claude reads the part it needs.
- **Sharing**: transcripts are other people's words - they stay on the PC like the videos; only topic summaries,
  counts and short quotes go into shared cards.
- **Also here** if friends' verdicts are in by then: category profiles (~10 references per category).

## 0.5.0 - planned - Templates by feel + macOS

- **Use a reference as a template**: its feel and pacing - shot lengths, cuts on the beat, effect families, the
  structure of what is said (0.4's hook > points > proof > CTA, the yapping profile) - with your own story, length
  and music instead of a 1:1 copy. Builds on the
  pacing numbers (`knowledge.pacing`), the effect library and the HTML graphics (0.3).
- **A macOS version** of the app (the lab is Python + a browser window; Edge-only parts, the Recycle Bin, `.bat`
  files and the Windows paths need macOS twins; DaVinci Resolve's scripting paths differ).

## 0.4.0 - planned - Prompt library + the yapping method

**The user's words (2026-10-11):** "give like 10 prompts from content creators, or that i tested and that could be
used with its own structure to create another one for your needs (seedance/hooks... etc) and also the content
creator expansion for the yapping method." **Their choices (2026-10-11):** examples = prompts they tested + creators'
public prompts (with the link); kinds first = video-model shots, hooks (first 3 s), full talking scripts; yapping =
both (analyse talking-head creators AND edit their own recording that way); this is 0.4's focus (collections and
topics moved to 0.6).

### A. Prompt library + generator
- **What it is**: ~10 proven prompts per kind, each split into its structure, so Claude can write a new one for your
  need that follows a structure that already worked. Kinds first: `shot` (Seedance / Higgsfield / Kling...),
  `hook` (the first 3 s), `script` (a whole talking video). Text only: no model, no API, no cost - you paste the
  prompt into the site; 0.7 later sends the same request through the API.
- **One home**: `knowledge\local\prompts\<kind>\<id>.json` - the text, the source (`tested` by you, or `creator` +
  name + link + date), the model (shots), your result (good / ok / bad + a note; the clip itself stays local), the
  structure (ordered slots - e.g. subject, action, camera move, lens, light, style, length - with the words that
  filled them, written by Claude when the prompt is added), tags and category.
- **Writing a new one**: a `/write-prompt` skill (a Claude window from the app, effort per task): pick the kind, say
  what you need; Claude reads the best-rated examples of that kind (MCP `prompts(kind)`), says which it builds on
  ("structure of P3, camera wording of P7"), writes 3 variants with the slots marked. You rate what the site made
  -> the best-rated structures become the first examples next time.
- **Shots from a reference**: give a frame range fA-fB (frame + timecode) and the shot prompt is filled from the
  analysis - length at the model's minimum, aspect, the measured camera move (events.json), light and look from the
  contact sheet, the subject from your story. This is the shot request 0.7 will send.
- **Hooks and scripts from creators**: talking references get their transcript (`content.py transcript`, done); the
  first 3 s become hook examples automatically (pattern named by Claude: question, bold claim, number, story,
  contrarian, demo...), and the whole talk is split into hook > points > proof > call to action with frame +
  timecode and seconds per part -> `analysis\<name>\content\structure.json`.
- **App**: a *Prompts* page - kinds as tabs, cards with source, rating and structure chips, *Copy*, *Add prompt*,
  *Rate the result*, *Write one like this* (opens Claude).
- **Sharing**: your own prompts, their structures and ratings can be shared (text, like cards). Creators' full prompts
  and transcripts stay on the PC; shared = structure + link + a short quote (docs\knowledge_sharing.md).

### B. The yapping method (talking-head creators)
- **Analyse**: detectors music videos never needed - jump cuts inside one talking shot (same framing, a pause cut
  out), punch-ins (a 1.1-1.3x scale step on a cut, held), word captions (burned-in text changing on the words),
  B-roll cutaways over continuing speech. Per video a *yapping profile* on its card: cuts/min, average shot, punch-ins
  per minute, share of silence removed, words per caption, caption position / size. Each new detector gets a
  synthetic self-test video with ground truth first (selftest must PASS).
- **Edit your own recording**: your raw talk (read-only, hard rule 1) -> your words with timings (needs the local
  engine: own footage has no platform subtitles, so the Whisper measurement becomes required) -> silences and
  fluffs cut on word boundaries, punch-ins at a chosen reference's rhythm, word captions as HTML overlays (0.3's
  HyperFrames) timed to your words, B-roll slots (your clips; generated ones in 0.7) -> a lab render, then the
  DaVinci Resolve build (cuts + captions as clips). You approve the cut list (every removed part with frame +
  timecode) before anything renders.
- **Linked to A**: `/write-prompt` writes the hook and script for your next recording; the edit then checks that the
  first 3 s say the hook.

### Steps (each one usable on its own; light first)
1. Prompt library + `/write-prompt` for shots, hooks, scripts (text only). **You bring** ~10 prompts: the text, the
   model, how it turned out, and links for creators' ones. **Built 2026-10-11, ships with 0.3.1** (the user's choice):
   `tools\motionlab\prompts.py` + `tools\prompts.py`, MCP `prompts(kind, id)`, the `/write-prompt` skill (split /
   write / shot from a reference), the app's *Prompts* page (add in the paste format, rate, copy, *Write one like
   this*); tested on a scratch library in headless Edge + `smoke.py`. Library still empty - waiting for the prompts.
   Sharing your own prompts: later (with the Knowledge page's Share).
2. Hook + script structure from 2-3 talking-head references **you pick** (download, analyse, transcript).
3. Whisper measured on one of them (tiny / base / small on a laptop setting, `tools\dev\whisper_bench.py`) -> you
   pick the engine.
4. Yapping detectors (jump cut, punch-in, captions) + their self-test videos.
5. The yapping edit of your own raw recording (**you bring** one, ~1-3 min) -> lab render -> Resolve.

### Already done (2026-10-09)
- **Done (step 1, command line)**: `tools\content.py transcript <name>` (yt-dlp: uploaded subtitles in the video's
  language, else YouTube's auto captions of the original audio, which carry word timings) ->
  `analysis\<name>\content\transcript.json / .txt`, frame + timecode per line and per word; `content.py show`;
  MCP `transcript(reference, start, end, words)`. 4AM: 72 lines / 463 words in ~7 s. Timings are the platform's,
  not measured by the lab.
- **Measuring Whisper**: `tools\dev\whisper_bench.py <name>` (faster-whisper int8 on the CPU in a separate venv,
  each model in its own process, `--threads 4` ~ a laptop; WER and word-timing difference against the subtitles).
  First run, mechanics only (4AM is rap over a beat, so its WER says nothing about talking videos): tiny = 75 MB
  model, 318 MB RAM, 27x real time on 4 threads of the RTX 4070 PC's CPU (a laptop core is slower). Still to do:
  tiny / base / small on the user's talking video (step 3), then the user decides.
- Other engines seen 2026-10-09: HyperFrames (in `tools\overlays\`, optional, needs Node) has a whisper.cpp
  `transcribe` command; ffmpeg's `whisper` filter is in BtbN builds but NOT in Gyan's essentials build (CI's; winget's
  full build: unchecked).

## 0.3.2 - planned - Motion graphics <-> DaVinci Resolve, HyperFrames kept current

(0.3.1 shipped the automatic tests on GitHub and the Prompts page: CHANGELOG.md.) **The user's picks (2026-10-11)**,
in this order:

1. **HyperFrames update check**: HyperFrames releases several times a day (0.8.142 pinned 2026-10-08, 0.8.149 on
   2026-10-11), so never upgrade blindly. The app asks npm once a day (one small request: `registry.npmjs.org`) and
   *Settings > Programs* shows the pinned and the newest version + a link to the release notes (GSAP too).
   `overlay.py upgrade-test [<version>]` installs the candidate in a scratch folder (`.app\dev\`), renders the
   examples in `tools\overlays\examples\` with it and with the pinned version, compares every frame (max 4/255, like
   the 0.3.0 check) and the render time; only on PASS `overlay.py pin <version>` changes package.json / lock, then
   the self-test + smoke, and the upgrade reaches friends through GitHub's tests like any change. No automatic
   upgrades. Worth a look in the notes since the pin: `transcribe --to srt|vtt` + as a function (0.4 Whisper
   decision), `render --gpu` (measure on a laptop setting too), A/V sync and clip-past-the-end fixes, and
   HyperFrames' captions workflow for talking heads (0.4 yapping).
   **Built 2026-10-11**: `motionlab\upstream.py` (npm dist-tags, `.app\upstream.json`; skipped when Settings'
   update_mode is "off" and on test servers), `overlay.py versions | upgrade-test | pin`, Settings > Programs
   ("HTML overlay packages": versions, *Test it* = job `overlays_upgrade_test`, *Adopt it (repo owner)*). First run:
   HyperFrames 0.8.142 -> 0.8.149 + GSAP 3.14.2 -> 3.15.0 = PASS - the 4AM title and clock identical (0/255), the
   10 s What's new clip max 2/255; render times the same. Pinned and shipped with 0.3.1 (the user's OK, 2026-10-11);
   the Update button's `npm ci` now also fetches HyperFrames' Chrome when a new version wants another one.
2. **Real Resolve test + refresh in place**: the overlays have never run inside a real Resolve build - place 4AM's
   title and clock in a scratch Resolve project (none of the user's projects touched; ask when Resolve is free),
   compare with the lab render frame by frame, and measure colour (overlays are sRGB, a Resolve timeline usually
   Rec.709 gamma 2.4). Then *refresh in place*: re-render a changed overlay and swap it into the open timeline
   (Resolve's replace-clip), keeping the user's hand edits (position, trims, opacity).
3. **Editable overlays + a graphics library**: an overlay's text, colours and timing as settings in its
   `overlay.json` that the app edits (Videos page) -> a re-render job -> refresh in Resolve. Approved overlays saved
   like the effect library (`library\`, the Library page) and imported into a Resolve **Power Bin**, so every project
   has them.
4. **Captions both ways** (toward 0.4's yapping edit): styled / animated captions as a HyperFrames clip timed to the
   words, or plain captions on Resolve's subtitle track (SRT) that the user can correct in Resolve.

Also: tune the HTML clock's grain to the lab's texture (geometry and timing already match); whatever friends report
after updating. Ideas still to test: [ideas.md](ideas.md).
