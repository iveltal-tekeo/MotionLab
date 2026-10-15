# MotionLab - planned versions

What comes next and how it plugs into the lab. The app shows these under *What's new* as "planned" (newest plan on
top); a version goes into `CHANGELOG.md` only when it ships (the Update button treats every version heading there as
released). Headings: `## x.y.z - planned - title`. The user decides scope and order - ask before starting a plan.
How the plans got their numbers, and finished measurements: [plans_history.md](plans_history.md) - older notes, chats
and code comments use old numbers; its table says which plan they mean.

**Version numbers**: a new `0.x.0` is a big step (a badge on the roadmap); `0.x.y` adds a smaller feature; a
four-part `0.x.y.z` is a small step between them (fixes, upkeep, polish).
**Each plan**: the user's words, *Ships when* (what has to be true to release it - a number where one exists), the
steps in order, *Needs first*. At most two versions are "next" at a time: finish and release one before starting
another.

## Where it stands (2026-10-15)

Released last: **0.4.3.5** (2026-10-15, CHANGELOG.md) - a simpler app: the Editor overhaul, Film it, a new player,
Analyser / Generator, dated cards newest first. Before it: **0.4.3** (2026-10-15) - title + thumbnail: Prepare's
*Title & thumbnail first*, Ready to post (thumbnails A / B / C, the check, chapters, hashtags), CTR per variant; 0.4.2.1
(downloads that keep working, Report a problem) and 0.4.2 (check before you render). The released plans' full
text: plans_history.md.

| Version | Plan | State | Size |
|---|---|---|---|
| 0.4.4 | What it took | **next** - Claude's minutes and tokens per step of a video; the data is already in Claude Code's session logs | M |
| 0.4.5 | *open* | kept free by the user (2026-10-15) | - |
| 0.4.6 | Prompt generator | planned - the library, `/write-prompt`, briefs and the title kind shipped in 0.3.x / 0.4.3 | M |
| 0.4.7 | Yapping mode | planned - talking quick draft + talking-head pack shipped; starts with the content foundations | L |
| 0.4.8 | Colour + DaVinci Resolve | planned - measuring a look + the match LUT shipped in 0.4.0 | M |
| 0.5.0 | Content generation | planned - its sound effects tool shipped early in 0.4.1.1 | L, ships in parts |
| 0.6.5 | Templates by feel | later - first part shipped in 0.4.0 | L |
| 0.7.0 | AI B-roll and cinematics | later | L |
| 0.7.5 | macOS | later | M |
| 0.8.0 | Describe video | later - transcripts, numbers, the content panel shipped | L |

## 0.8.0 - planned - Describe video: videos as information

**Ships when**: a collection of ~10 analysed videos gives its topics with counts and quotes (frame + timecode), each
video's content reviewed Correct / Partly / Wrong by the user like effects, and searchable from Claude.

**Shipped in 0.4.0** (2026-10-13, the user's overhaul): the *content creation* focus of Analyze - references
without subtitles get their words by speech to text when it is installed (`content.py auto`); the analysis
Overview's Content creation panel (`motionlab\profile.py`: the hook - cuts, words, text in the first 3 s; words per
minute and how much is talked; text on screen per minute; captions likely); Claude's breakdown per focus (review.json
`_breakdown`: hook, structure, captions, text & graphics, B-roll, sound, CTA); all searchable in Claude's memory.
**Moved to 0.4.7** (2026-10-14): the foundations - text on screen, the shots described, topics and claims per video
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
  call to action; one line per shot read from a sheet of one key frame per shot; text on screen): built in 0.4.7's
  first step. Here: across many videos.
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
  cost estimate; the user approves each paid generation. "By feel" edits (0.6.5) can ask for whole sequences.
- **In *Generate***: 0.5.0 brings the clips the user made on a tool's site back into the lab (checked against the
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
- **Needs first**: 0.5.0 (AI clips back into the lab), 0.6.5 (story-driven edits); 0.3's colour pipeline (done).

## 0.6.5 - planned - Templates by feel

**Ships when**: an edit of the user's footage with their own story follows a reference's measured pacing (cuts per
minute and shot lengths within ~15 %) and the structure of what is said, and the user rates it OK or better.

- **Use a reference as a template**: its feel and pacing - shot lengths, cuts on the beat, effect families, the
  structure of what is said (0.4.7's HEIT structure, the yapping profile) - with your own story, length and music
  instead of a 1:1 copy. Builds on the pacing numbers (`knowledge.pacing`), the effect library and the HTML
  graphics (0.3).
  **Shipped in 0.4.0, the first part** (2026-10-13, the user's overhaul): *Editor > New edit* takes the style of up to
  three analysed videos or the user's words / presets (`tools\style.py`), a quick draft by rules
  (`tools\draft_edit.py`: beat-cut shots, the best moments, the style's effects, a talking mode) and
  `/recreate-video` section 6 for Claude to refine it - and its colour matched to the references (0.4.0's colour
  analysis, a match LUT). Still open: the story (the HEIT structure of what is said), captions and graphics made by
  the draft itself (0.5.0's building blocks and sound effects are what the draft would place).

## 0.5.0 - planned - Content generation: videos from zero that come out right

**Ships when** (the benchmark: a "top 3 tracks" reel from zero like illdari's): the first version is rated OK or
better on graphics and on sound effects (v1: graphics "too clunky", sound effects bad), it needs one final render
(v1: ~29 min of renders), and its time and Claude's tokens are lower than the baseline 0.4.4 (*What it took*) measured.

**The user's words (2026-10-14)**: "while moving from 0.4.1 to 0.5.0 id like to have the 0.5.0 version as a
'contente generation oriented version' ... i want the generation of video through claude and other tools such as
hyper frame or other to be more redefined and work better."

**Where it stands** (0.4.0, 0.4.1 and the Unreleased work): *Generate* makes two things. **A motion-graphics video**:
Claude writes the HTML / CSS / GSAP from zero for every video, HyperFrames renders it, `tools\beats.py` times it to a
song, `overlay.py stills` checks it (`/generate-video graphics`, effort xhigh). **A video for AI video tools**: a shot
list and every prompt saved in the prompt library, then a hand-off to *Editor > New edit* (`/generate-video ai`). The
first real one (illdari_test_copy_1, 2026-10-14) showed the weak spots: graphics rated "too clunky" (drawn ~40 %
smaller than the reference, nothing moving between the big moves), no sound effects (rated bad), ~29 min of renders
for 25 s, and a bug in hand-written code (the logo's badge missing at f38 (00:00:01:08)). Added during that rebuild:
real motion blur (`overlay.py render --motion-blur N`) and a sound-effects script for that one project (`sfx_v2.py`).

**Goal**: a video from zero that is right the first time more often, in less time and with fewer Claude tokens.
Claude decides what it says and the scenes; the lab gives it tested building blocks, sound, a preview before the
render and checks. The AI-tools route comes back into the lab instead of ending at a hand-off.

**Gathered from every plan and idea** (2026-10-14; the user decides what stays): from *Check before you render*
(0.4.2) its sound effects tool, live preview, faster motion blur and templates (steps 4, 6, 7, 2 below); from
`docs\ideas.md` voice-over and music (step 5, measure first); the rest is new. **0.4.2 came first** (released 2026-10-14): its snapshots,
notes on moments, ratings as rules, lessons on making videos (M###) and safe starter graphic are what this plan
builds on. The paid API for AI video stays in 0.7.0; describe video (0.8.0) later improves *what* a video says, not
needed here.

0. **Measure first** - moved to 0.4.4 (*What it took*, 2026-10-15) and widened to every video: Claude's minutes
   and tokens per step and the renders' minutes, read from the Claude Code session logs and the app's jobs on this
   PC. The generated videos measured there before this plan starts are the baseline every step is judged by.
1. **Building blocks for HyperFrames**: a tested kit Claude puts scenes together from, instead of writing every
   graphic from zero - text (type-on, word pops, mask reveals, the 3D lyric stack), UI (a phone / app / window frame,
   a cursor on a curved path with a press), numbers (counters, bars), lists, a logo sting and an end card,
   transitions between scenes (whip, zoom-through, mask wipe, flash) and a camera (push-in, a jolt on hits, a slow
   drift, a smear for fast moves). Each one: settings the user can change, its own sound cues (step 4), safe with
   motion blur and snapshots (0.4.2 item 7's helpers), and a test - its frames rendered and compared like
   `overlay.py upgrade-test` (max 4/255), so a HyperFrames upgrade cannot break it unseen. Shared through the repo
   next to `tools\overlays\examples\`; the user's approved ones in the graphics library. Claude writes new code only
   for what no block does (fewer tokens, fewer bugs: the f38 badge was hand-written).
2. **Formats - a made video as a template** (was item 13 of *Check before you render*): a generated video the user
   approved is saved as a format - "top 3 tracks", a lyric video, a list / explainer, an app promo, a quote or number
   reel... = its scenes as settings (texts, pictures, colours, song, length). The next video in that format is new
   settings, no new code (the biggest saving in Claude's tokens). *Generate* gets *Start from a format*. The first
   one: illdari's "top 3 tracks" reel, once the user approves v2.
3. **A quick draft for Generate** (made by rules, no Claude, like the Editor's quick draft): a format or the style of up to
   3 analysed videos (`style.py`) + the user's texts + the song's beats (`beats.py`) -> scenes on the downbeats, the
   biggest change on the drop, the blocks filled in -> a first video in minutes; Claude refines it (what it says, the
   custom parts) instead of starting from an empty page. The style of a motion-graphics reference gets the numbers v1
   got wrong: how long text holds, how fast things move (pixels per frame), the size of the main element on the frame
   (Claude measures it once on the reference's frames; saved with the style).
4. **Sound effects as a lab tool** (was item 8 of *Check before you render*; **Shipped in 0.4.1.1** (2026-10-14,
   built early): `tools\sfx.py` + `motionlab\sfx.py` - 22 synthesised kinds, sample-identical to `sfx_v2.py`; cues in
   overlay.json "cues" as formulas of the settings (`repeat` / `if`), the starter graphic has them; cues from a plan's
   layers; each effect levelled against the song - the quieter of 400 ms around it and its own loud part, so a sound
   in a short gap before a loud line follows the gap; a -1 dBFS limiter; stem + mix + a level report; ~1 s per minute
   of video; self-check in `selftest.py`. The user's listen of the illdari v2 rebuild: "kinda too loud" -> every level
   3 dB lower, effects' peaks at most -6 dBFS, sparse sounds (sparks) measured near their peak: now 3.1 dB under
   `sfx_v2.py` (median), none more than 2.9 dB over (was up to +10.6). Open: a `--sfx` flag for the quick draft):
   `tools\sfx.py`, from `sfx_v2.py` - a graphic lists its cues (frame + kind:
   whoosh, click, key, pop, hit, riser...) next to its settings, so the sound follows when a setting moves the timing
   (the typed text); synthesised (no samples to license); each effect levelled against the song under it -
   measured, since Claude cannot hear; the effects alone as a stem for Resolve + the mix for the plan. Blocks carry
   their cues (a whip = a whoosh); the Editor's quick-draft effects (zooms, whips, flashes) become cues the same way.
5. **Voice and music** (from ideas.md, measure first): a voice-over for explainers and lists - ElevenLabs (the user's
   own account) or a local text-to-speech measured on a laptop first (time per minute of speech, size, how natural);
   its words timed like speech to text, so captions and scenes follow the voice. A voice only with the speaker's
   consent. Music only with clear licences: the user's own song, a licensed library, or a music model whose terms
   allow it.
6. **A preview before the render** (was item 11 of *Check before you render*, measure first): (a) an **animatic** -
   the scene snapshots (0.4.2's `overlay.py snap`) held on their frames with the song and the sound effects -> an MP4
   in seconds, so the timing and the sound are checked before anything renders for minutes; (b) the **live preview**
   - HyperFrames' `hyperframes preview` (in the pinned 0.8.149), not yet tried: does the 3D lyric part play smoothly
   on a laptop, does it play the song. If it does: *Play* on the video's page - live with the song and its sound
   effects, a scrub bar, frame + timecode, settings change at once without a render (no motion blur in the preview;
   the render is the final word).
7. **Faster renders** (was item 12 of *Check before you render*, measure first): motion-blur sub-frames only for
   frames that move (HyperFrames found about a third of illdari's frames static; the 9 min could drop a lot - not
   measured); `overlay.py render --workers N` measured on a laptop setting; plain renders for checks, the polish once
   (0.4.2's order of checks).
8. **AI clips back into the lab** (Generate's AI route, end to end): the user drops the clips made on the tool's
   site into the project (named `01_<shot>.mp4`... as `ai_plan.md` asks); the lab matches them to the shot list,
   checks each one's length, size and frame rate against its shot, and makes a sheet of every clip's first and last
   frames (frame + timecode) so continuity - the same face, product, place, light - is checked on stills. Then it
   cuts them on the song's beats as the shot list says, and the blocks add titles, captions, graphics and sound
   effects on top -> one video, in the lab and in DaVinci Resolve. Each clip is rated against its prompt (good / ok /
   bad + a note), so the prompt library learns per model (0.4.6); a shot to redo gets a new prompt that says what
   changes. Today the route ends at *Editor > New edit*, which treats the clips as footage and forgets the shot list.
9. **One video, three sizes**: the compositions are HTML, so 9:16, 16:9 and 1:1 come from one video with layout
   rules per size (`overlay.py fit` already takes a size); the user ticks the sizes to render.
10. **Other tools** (measure first, only where a block cannot do it): Lottie animations (After Effects exports)
    played frame by frame inside a composition; image tools (Nano Banana / GPT Image) for pictures in a scene, through
    the prompt library's `image` kind. HyperFrames stays the one graphics engine (pinned, upgrade-tested).
11. **The made video's page**: a video made from zero opens on its project's page (Editor); it gets Generate's steps
    there - the scene table (frame + timecode), the animatic and *Play*, the settings, the sound, *Render*, *How did
    it turn out?* with notes on moments (0.4.2) - in plain words.

**Order** (the user decides): 0 comes with 0.4.4; 1 (it fixes what was rated "too clunky"; 4 is being built early);
2 once illdari's v2 is approved; 6a (small); 3 when a few blocks and formats exist; 8; then 6b, 7, 5 and 10 after
measuring; 9 last. **Size**: large - it can ship in parts: 0.5.0 = 1, 2, 6a and 11; then 0.5.x for the rest.
**Rules**: light and tested first (every new tool optional and measured on a laptop); copy a style, never someone's
content (their words, logos, characters); AI clips and voices labelled as generated.

## 0.4.8 - planned - Colour: measure a look, match it, grade in DaVinci Resolve

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

## 0.4.7 - planned - Yapping mode: the yap-maxing framework

**Ships when**: on 3-5 talking videos the user picked, the content foundations and the HEIT parts are there with frame
+ timecode and reviewed by the user; the yapping detectors pass their synthetic self-tests; the user's own recording
is edited from a cut list they approved before anything rendered, every cut on a word boundary.

**Shipped in 0.4.0** (2026-10-13): first pieces of *Make* - the quick draft's talking mode (`draft_edit.py --sound
talk`, New edit's *Talking + captions* preset: the spoken parts in order, the pauses cut - by loudness, not yet on
word boundaries -, a punch-in every other cut, B-roll over the talking) and Claude's breakdown of a talking video
(hook, structure, captions). **Built early (2026-10-14)**: Prepare - `/write-script` and the script check (step
"Topic + script" below). Still open: the content foundations, HEIT labels, validated topics, delivery / environment
numbers, the yapping detectors with self-tests, cuts on word boundaries with the user approving the cut list, the
beats writer for the talking-head pack.

**The user's notes (2026-10-12)** ("v0.3.5" = describe video, now 0.8.0): "using the v0.3.5 as an exceptional tool
when creating a video: 'yapping mode' or talking to the camera. Focused on content creators: yap maxing framework.
Influential videos, lots of views videos. Basically making content short or long form; take into account formats.
HEIT framework = hook / explain / teach / illustrate. Validated topics. Copy and learn structure. Extras: 1) text on
screen 2) environment: experiment different environments 3) delivery: authentic content 4) graphics: visual hooks."
(Earlier, 2026-10-11: analyse talking-head creators AND edit the user's own recording that way.)

- **Goal**: learn from talking-to-camera videos that work (many views) and make your own - short or long form - in
  the same proven structure, from the topic to the finished edit in the lab and in DaVinci Resolve.
- **First: the content foundations** (moved here from describe video, 2026-10-14 - this settles the order conflict
  between the two; 0.8.0 builds on them): per analysed video `analysis\<name>\content\content.json`, reviewed by the
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
     HEIT script in the structure of the best videos of your format (0.4.6's database).
  2. **Record**: a one-page brief - format, length, the HEIT outline with seconds, delivery notes, the environment
     to try.
  3. **Edit your raw recording** (read-only, hard rule 1): your words with timings (local Whisper - own footage has
     no platform subtitles), silences and fluffs cut on word boundaries, punch-ins at a chosen reference's rhythm,
     text on screen and captions as HTML overlays timed to your words (0.3's HyperFrames, 0.3.2's captions; the SRT
     onto Resolve's subtitle track by script, tested in the scratch project), a visual hook in the first 3 s, B-roll
     slots (your clips; generated ones in 0.7) -> a lab render, then the Resolve build. You approve the cut list
     (every removed part with frame + timecode) before anything renders.
  4. **Check**: the first 3 s say the hook, the HEIT parts land at their target seconds, the extras are there.
- **Steps**: (0) the content foundations above, on 3-5 influential talking videos you pick, analysed with the
  content focus; (1) HEIT labels + the extras' numbers on them; (2) the yapping detectors + self-tests; (3) brief +
  the edit of your own recording.
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

## 0.4.6 - planned - Prompt generator: every model, every specialty

**Ships when**: every prompt has a specialty and the model it was written for; the Prompts page filters by both;
`/write-prompt` copies examples of the same specialty and model first; at least one kind holds ~10 prompts the user
rated after using them.

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
    **First part built in 0.3.4** (the user's Spanish London vlog brief had landed under "script"): kind `brief` =
    the user tells Claude how to make / edit a whole video, 14 parts (format & length ... questions first); Claude's
    check marks each part clear / vague / missing with a tip, the user writes what they want per part, *Optimize
    with Claude* writes a new version (`made_from`), *Run it* = Create video. Still open: other agent prompts.
  - **Per category / specialty**: every prompt gets a specialty (the lab's categories - music video, vlog, cooking,
    ... - plus your own, e.g. "make money online", "fitness"); the page filters by it and `/write-prompt` copies
    examples of the same specialty and the same model first.
  - **Per model**: the model a prompt was written for stays part of its structure (Seedance's lengths and camera
    words, Claude's tags...); a new prompt for another model says what it changed.
  - **Filled by the analyses**: the first 3 s of every analysed talking video become hook examples, its HEIT
    structure a script example (0.4.7; describe video, 0.8.0, adds more), with the link and frame + timecode.
  - **Sharing** your own prompts and ratings through *Claude's memory > Share* (text); creators' prompts stay on the PC.
  - **A structure per purpose** (2026-10-12: "a vlog prompt differs from a talking head, SFX, transitions..."):
    0.3.3 gave prompts their purposes (tags) and videos a "how did it turn out?" per part (`build\outcome.json`,
    shown on the prompt as "Used in"); learn from those answers which structure works per purpose - needs a few
    made videos rated first.
  - **Style from analysed references** (built 2026-10-13, after 0.3.4: "the optimized prompt asks for a link to a
    Clavero vlog - what if I analysed one already?"): *Style like* on brief / script / hook cards links analysed
    references; their measured pacing / effects / BPM go into Claude's check, Optimize and Create video. Next: the
    look measured too (0.4.8), and several references of one creator averaged into one style.
- **Needs**: your prompts (the prompt library or pasted in the chat).

## 0.4.4 - planned - What it took: Claude's time and tokens, step by step

**Ships when**: a 1-min talking video made from a Prepare script to *Ready to post* shows its whole breakdown on its
Overview - every Claude step and every job, with minutes, tokens, model and effort, and the total - and the totals
match the Claude Code session logs on a hand check (within 1 %); the live panel follows a running `/recreate-video`
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

**Where it stands**: nothing shown yet. 0.5.0 had this as its step 0 (*Measure first*, generated videos only); it
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
5. **Live** (the user: "if i run a claude /analyze-video or /recreate i want to see ... that process in motion lab"):
   while a Claude window the app opened is working (its log's last line under 2 min old), its video's page and the
   Jobs page show a panel - running for N min, tokens so far, the model, the current step in words (the skill + the
   last tool: "reading the contact sheets", "rendering v2") - read from the growing log every few seconds. Read-only:
   it never writes to Claude Code or steers it.
6. **Optional, ask the user first**: "≈ $X at API prices" as a size, never a bill (the user is on a Max plan; the
   plan's limits are not in the logs) - prices in one dated table with their source.

**Needs first**: nothing - the session logs and the names the app gives its sessions exist on this PC. **Size**: M.
**Tests**: fixed sample logs in `tools\dev\` (a named session, a session started by hand, subagents, a repeated
answer) for a self-check and `smoke.py`; one hand count against a real session before it ships.
