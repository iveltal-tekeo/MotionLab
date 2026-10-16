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

## Where it stands (2026-10-16)

Released last: **0.5.0.1** (2026-10-16, CHANGELOG.md) - the logo library: 92 app / platform / AI-tool logos for the
motion graphics (`logos\`, `tools\logos.py`), the Logo wall template, *Pick a logo* / *+ Logo*, Motion Graphics >
Logos. Before it **0.5.0** (2026-10-16) - Motion Graphics: 74 templates (57 learned from the Swishy
clips, 17 MotionLab originals), the Motion Graphics page, Generate builds from them; with **0.4.6** (2026-10-16) -
fonts and captions: 28 shipped fonts, live previews, caption looks, the measured font of a thumbnail set. Before
them: **0.4.5** (bulk) and **0.4.4** (what it took). The released plans' full text: plans_history.md.

| Version | Plan | State | Size |
|---|---|---|---|
| 0.5.1 | Yapping mode | planned - talking quick draft + talking-head pack shipped; starts with the content foundations; + the clips a script needs (from 0.5.0, 2026-10-15) | L |
| 0.5.2 | Faster videos | planned - a minute of video in ~10 min of Claude: brief -> plan -> build -> one look (added 2026-10-15) | M-L, ships in parts |
| 0.5.3 | Prompt generator | planned - the library, `/write-prompt`, briefs and the title kind shipped in 0.3.x / 0.4.3 | M |
| 0.5.4 | Motion graphics: template packs | planned - the library shipped in 0.5.0; Resolve / After Effects / Lottie packs read exactly, templates used as they are, the motion check, formats, a preview before the render | L, ships in parts |
| 0.5.5 | Colour + DaVinci Resolve | planned - measuring a look + the match LUT shipped in 0.4.0 | M |
| 0.5.6 | Content generation | planned - AI clips back into the lab, voice and music, pictures from image tools (from 0.5.0, 2026-10-15) | M |
| 0.6.0 | Describe video + courses | later - transcripts, numbers, the content panel shipped; courses added 2026-10-15 | L |
| 0.6.5 | Templates by feel | later - first part shipped in 0.4.0 | L |
| 0.7.0 | AI B-roll and cinematics | later | L |
| 0.7.5 | macOS | later | M |

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
- **In *Generate***: 0.5.6 brings the clips the user made on a tool's site back into the lab (checked against the
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
- **Needs first**: 0.5.6 (AI clips back into the lab), 0.6.5 (story-driven edits); 0.3's colour pipeline (done).

## 0.6.5 - planned - Templates by feel

**Ships when**: an edit of the user's footage with their own story follows a reference's measured pacing (cuts per
minute and shot lengths within ~15 %) and the structure of what is said, and the user rates it OK or better.

- **Use a reference as a template**: its feel and pacing - shot lengths, cuts on the beat, effect families, the
  structure of what is said (0.5.1's HEIT structure, the yapping profile) - with your own story, length and music
  instead of a 1:1 copy. Builds on the pacing numbers (`knowledge.pacing`), the effect library and the HTML
  graphics (0.3).
  **Shipped in 0.4.0, the first part** (2026-10-13, the user's overhaul): *Editor > New edit* takes the style of up to
  three analysed videos or the user's words / presets (`tools\style.py`), a quick draft by rules
  (`tools\draft_edit.py`: beat-cut shots, the best moments, the style's effects, a talking mode) and
  `/recreate-video` section 6 for Claude to refine it - and its colour matched to the references (0.4.0's colour
  analysis, a match LUT). Still open: the story (the HEIT structure of what is said), captions and graphics made by
  the draft itself (0.5.4's building blocks and sound effects are what the draft would place).

## 0.6.0 - planned - Describe video: videos and courses as information

**Ships when**: a collection of ~10 analysed videos gives its topics with counts and quotes (frame + timecode), each
video's content reviewed Correct / Partly / Wrong by the user like effects, and searchable from Claude; a course of
~10 lessons gives the steps each lesson teaches (frame + timecode, the screen shown) and a course summary Claude
uses when it edits.

**Courses** (the user, 2026-10-15: "and maybe in the future maybe bulk analyze courses? of davinci resolve or courses
on content creation? (i think this is a similar idea we have for the 'describe video' version. what do you think?
so maybe make that instead of v.0.8.0 to 0.6.0, but have the bulk stuff in 0.4.5 so it links up well to 0.5.4 and
then we just move upwards to 0.6.0"): a course = a collection of long videos (its lessons), analysed with the
content focus on 0.4.5's batch runner. Per lesson: the transcript, the steps taught (one key frame per step - the
screen, the panel, the values set), the tools and settings named (DaVinci Resolve's pages, nodes, values), the
lesson's notes; per course: a summary, "how do I ...?" answered with the lesson + frame + timecode, and techniques
Claude can rebuild (a Resolve technique from a course -> a recipe in the library, tested like the effects; the
templates a course gives go through 0.5.4's template packs). Measure
first: Claude's time per minute of a long lesson (0.4.4), then decide what is read from the transcript only and
what needs pictures. **Rules**: courses are someone's paid work - the user's own copies only (paid platforms are
usually locked against downloads), everything stays on the PC, only the user's notes can be shared.

**Shipped in 0.4.0** (2026-10-13, the user's overhaul): the *content creation* focus of Analyze - references
without subtitles get their words by speech to text when it is installed (`content.py auto`); the analysis
Overview's Content creation panel (`motionlab\profile.py`: the hook - cuts, words, text in the first 3 s; words per
minute and how much is talked; text on screen per minute; captions likely); Claude's breakdown per focus (review.json
`_breakdown`: hook, structure, captions, text & graphics, B-roll, sound, CTA); all searchable in Claude's memory.
**Moved to 0.5.1** (2026-10-14): the foundations - text on screen, the shots described, topics and claims per video
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
  call to action; one line per shot read from a sheet of one key frame per shot; text on screen): built in 0.5.1's
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

## 0.5.6 - planned - Content generation: AI clips, voice and music

**Ships when**: the clips of a shot list made on an AI video tool's site come back into the lab, are checked against
their shots (length, size, frame rate, a first / last frame sheet for continuity) and cut on the song with 0.5.4's
blocks and sound effects on top - one video, in the lab and in DaVinci Resolve - and each clip is rated against its
prompt; a voice-over or music only after step 1's measurements.

**The user's words (2026-10-14)**: "while moving from 0.4.1 to 0.5.4 id like to have the 0.5.4 version as a
'contente generation oriented version' ... i want the generation of video through claude and other tools such as
hyper frame or other to be more redefined and work better." On 2026-10-15 its motion-graphics part became 0.5.4
(*Motion graphics*; the user: "yeah go ahead"); this plan keeps the rest. Steps 1 and 2 were 0.5.4's steps 5 and 8.

**Where it stands**: *Generate*'s AI route (`/generate-video ai`) writes a shot list and every prompt into the prompt
library, then hands off to *Editor > New edit*, which treats the clips as footage and forgets the shot list.

1. **Voice and music** (from ideas.md, measure first): a voice-over for explainers and lists - ElevenLabs (the user's
   own account) or a local text-to-speech measured on a laptop first (time per minute of speech, size, how natural);
   its words timed like speech to text, so captions and scenes follow the voice. A voice only with the speaker's
   consent. Music only with clear licences: the user's own song, a licensed library, or a music model whose terms
   allow it.
2. **AI clips back into the lab** (Generate's AI route, end to end): the user drops the clips made on the tool's
   site into the project (named `01_<shot>.mp4`... as `ai_plan.md` asks); the lab matches them to the shot list,
   checks each one's length, size and frame rate against its shot, and makes a sheet of every clip's first and last
   frames (frame + timecode) so continuity - the same face, product, place, light - is checked on stills. Then it
   cuts them on the song's beats as the shot list says, and the blocks add titles, captions, graphics and sound
   effects on top -> one video, in the lab and in DaVinci Resolve. Each clip is rated against its prompt (good / ok /
   bad + a note), so the prompt library learns per model (0.5.3); a shot to redo gets a new prompt that says what
   changes. Today the route ends at *Editor > New edit*, which treats the clips as footage and forgets the shot list.
3. **Pictures from image tools** (was part of 0.5.4's step 10; measure first, only where a block cannot do it): Nano
   Banana / GPT Image for pictures in a scene, through the prompt library's `image` kind.

**Order** (the user decides): 2 (it closes the AI route), 3, then 1 after measuring. **Size**: medium.
**Rules**: AI clips and voices labelled as generated; a voice only with the speaker's consent; music only with clear
licences; the paid API for AI video stays in 0.7.0.
**Needs first**: 0.5.4's blocks and sound effects (what goes on top of the clips); the prompt library's ratings per
model (0.5.3), to rate each clip against its prompt.

## 0.5.5 - planned - Colour: measure a look, match it, grade in DaVinci Resolve

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

## 0.5.4 - planned - Motion graphics: template packs, the motion check, formats

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
honestly could be 100x times better. where could this version fit" - then, to Claude's proposal (this plan as 0.5.4,
the rest of content generation as 0.5.6): "yeah go ahead". The plan it grew from (2026-10-14): "i want the generation
of video through claude and other tools such as hyper frame or other to be more redefined and work better."

**Where it stands** (2026-10-15): *Generate*'s motion-graphics videos are written by Claude from zero - HTML / CSS /
GSAP that HyperFrames renders, timed to a song by `beats.py`, checked with `overlay.py snap` / `stills` and
`precheck.py`, with sound from `sfx.py` (shipped in 0.4.1.1). MotionLab has 5 example graphics (7-16 KB each) and the
graphics library is empty. The first real one (illdari_test_copy_1, 2026-10-14) was rated "too clunky": drawn ~40 %
smaller than the reference, nothing moving between the big moves, a hand-written bug (the logo's badge missing at f38
(00:00:01:08)); every video from zero is ~42 KB of new animation code (0.5.2's review). **Why it looks dull**: Claude
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

**Builds on 0.5.2** (*Faster videos*): the blocks (step 5), the formats (6) and Generate's quick draft (7) run through
its one-page brief and its build command - Claude reads one page, writes a scene list, one command renders, checks
and makes one sheet - so a video from zero gets the same brief -> plan -> build -> one look as an edit. **Moved out**
(2026-10-15): voice and music, AI clips back into the lab and pictures from image tools -> 0.5.6 (*Content
generation*); the clips a script needs -> 0.5.1 (yapping mode's B-roll slots are that list); faster renders -> 0.5.2;
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
   `sfx_v2.py` (median), none more than 2.9 dB over (was up to +10.6). Open: a `--sfx` flag for the quick draft):
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
**Needs first**: 0.5.2's brief and build command (steps 5-7 run through them); 0.4.6's fonts (shipped 2026-10-16);
from the user: which packs first, ~20 templates starred, the verdict on the remade "top 3" reel.

## 0.5.3 - planned - Prompt generator: every model, every specialty

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
    structure a script example (0.5.1; describe video, 0.6.0, adds more), with the link and frame + timecode.
  - **Sharing** your own prompts and ratings through *Claude's memory > Share* (text); creators' prompts stay on the PC.
  - **A structure per purpose** (2026-10-12: "a vlog prompt differs from a talking head, SFX, transitions..."):
    0.3.3 gave prompts their purposes (tags) and videos a "how did it turn out?" per part (`build\outcome.json`,
    shown on the prompt as "Used in"); learn from those answers which structure works per purpose - needs a few
    made videos rated first.
  - **Style from analysed references** (built 2026-10-13, after 0.3.4: "the optimized prompt asks for a link to a
    Clavero vlog - what if I analysed one already?"): *Style like* on brief / script / hook cards links analysed
    references; their measured pacing / effects / BPM go into Claude's check, Optimize and Create video. Next: the
    look measured too (0.5.5), and several references of one creator averaged into one style.
- **Needs**: your prompts (the prompt library or pasted in the chat).

## 0.5.2 - planned - Faster videos: a minute of video in ten minutes of Claude

**Ships when** (measured with *What it took* (0.4.4) on this PC, everything included - captions, graphics, effects,
sound effects, the finished render): a 60 s talking video from the user's footage takes **12 min of Claude or less**
(now ~0.8-1 min of Claude per second of video, ~45-60 min), with at most one full render round; Claude's tokens per
video at least 3x lower; the user's side-by-side verdict against the same video made with today's lab (0.4.5) is "the
same or better". The test videos: `testing_entire_workflow` (51.9 s) and `What's new in MotionLab 0.4.3` (25.7 s)
re-made, then a 60 s talking clip the user films.

**The user's words (2026-10-15)**: "current benchmark is kinda like spent 1 minute of claude is equal to 1second of
video result so a 1min video takes cladue 50/60 mins, i want to go as down as to 1 min of video to 10 minutes of
claude (with everything included, sfx, motion graphics, effects, captions...) do you think it spossible?" - then
"could you write some steps in the plans doc or roadmap on what could we do, how, and if it could actually work?"

**Where the time goes now** (Claude's review, 2026-10-15: `usage.py` and the session logs of four videos):

| Video | Length | Claude's window | Thinking + writing | Waiting on tools | Turns | Tokens |
|---|---|---|---|---|---|---|
| What's new in MotionLab 0.4.3 (talking, Fable high) | 25.7 s | 24.5 min | 9.9 min | 13.9 min | 50 | 8.3 M |
| testing_entire_workflow (talking, Fable high) | 51.9 s | 38.5 min | 8.4 min | 27.2 min | 62 | 8.7 M |
| illdari_test_copy_2_fable_high (from zero, Fable high) | 25 s | 20.8 min | 8.8 min | 11.6 min | 47 | 8.2 M |
| illdari_test_copy_1 (from zero, Opus xhigh) | 25 s | 36.1 min | 22.0 min | 9.9 min | 104 | 21.2 M |

- Claude's own time is ~8-10 min a video (Fable high) and hardly grows with the length; the waiting grows with the
  length and with every render round. So a 60 s video needs both halves cut: Claude to ~5-6 min, the lab to ~4 min in
  one render round.
- **Waits that never ended**: in testing_entire_workflow Claude polled the render logs for an `exit` line that went
  to the background task's own output instead - both loops ran to their 560-try timeout, 9.8 min each, while the two
  renders took 108 s: ~16 of the 38.5 min, for nothing.
- **Render rounds**: the 0.4.3 video rendered the video 5x, the captions 4x, the info panel 3x, the sound effects 4x.
  A full round of a 60 s video is ~4-5 min; the target has room for one.
- **Code written per video**: a 10-15 KB `edit_vN.py` that writes the plan, then sed patches; 5-10 KB of captions
  JSON typed by Claude; from zero a 42 KB `index.html` and an 18 KB `sfx.py`. Claude's minutes follow its output
  (48-165 k tokens a video).
- **Turns x context**: 47-104 turns a video; the context starts at 55-63 k tokens and ends at 190-360 k, and every
  turn re-reads it - a late turn costs ~200 k tokens.

**Goal**: Claude makes only the decisions only it can make - what to cut, what goes on screen, which graphic with
which words - and the lab does every step in between in one go: from ~60 small steps to four, **brief -> plan ->
build -> one look**. Every new tool writes only inside `projects\<name>\build\` (hard rule 1).

**Steps** (each: what, how, and whether it can work):

1. **Waits that end** (small; the skills + `overlay.py`): never poll; anything under ~10 min runs in the foreground;
   several renders = one command that runs them in parallel and returns when all are done (`overlay.py render
   <folder> <folder> ...`). *Can it work*: yes, certain - pure waste, no change to the result; ~16 min on
   testing_entire_workflow.
2. **One build command** (`tools\build.py <project> [plan_vN.json]`, medium): prep (cached) -> captions + overlays in
   parallel -> sound effects from the plan (`sfx.py plan`) -> the render -> `precheck.py` -> one sheet (a still at
   every scene change and every graphic's hit, frame + timecode) + a 10-line summary (what rendered, the minutes,
   precheck's flags with frame + timecode, the sheet). A re-run skips the parts whose inputs did not change (a hash of
   each part's inputs). *Can it work*: yes - every piece exists and was run by hand in these sessions; new are the
   order, the skipping and the summary. It saves the turns between steps (~15-25 a video) and their re-reads; the
   render minutes stay the same until step 3.
3. **Faster overlay renders** (medium; each measured first, on this PC and a laptop setting): (a) render only the
   visible box - the captions covered 1537 x 82 px of 1920 x 1080 (~6 %), yet every frame was rendered and encoded
   full size (148 MB of ProRes 4444 for 52 s); the composition gets the box's size, the plan layer an offset;
   (b) find why the info panel's renders report HyperFrames' static-frame reuse "disabled (eligible)" while the
   captions reuse 63 % of their frames (likely one element that never stops moving - hold it when nothing happens);
   (c) after a fix, re-render only the changed range and splice it in (`render_video.py --range` exists; overlays need
   one); (d) check renders at half size, the final at full; (e) for the lab's own render, frames straight into its
   cache instead of the ProRes encode -> decode round trip; ProRes only when Resolve asks; (f) motion-blur sub-frames
   only for the frames that move and (g) `overlay.py render --workers N` measured on a laptop setting - both moved
   here from 0.5.4's step 7 (2026-10-15): HyperFrames found about a third of illdari's frames static, and a 750-frame
   graphic took 79-89 s plain against 6.5-9 min with motion blur 5; plain renders for the checks, the polish once
   (0.4.2's order of checks). *Can it work*: likely - an overlay took 62-108 s for 25-52 s of video; if (a) and (b)
   halve that or better, a 60 s build lands near 3-4 min. Not known yet: how much of HyperFrames' time follows the
   pixel count (Chrome's screenshot and the encode should, the page's JavaScript does not) - measure (a) first, it is
   the cheapest to try.
4. **A one-page brief** (`tools\brief.py <project>`, small): what Claude needs before it plans, in one command and
   ~3-5 k characters - the footage (clips, lengths, the board), the words with frame + timecode (the script and the
   transcript lined up), the chosen style's numbers (a short form of `style.py`), the sound answer, the user's request
   (`edit_request.json`), and only the memory lines that apply (`knowledge.py memory` prints 13-19 k characters now).
   *Can it work*: yes - all of it is measured already; it replaces 5-8 calls at the start of every session (memory,
   style, speech status, prompts, storyboard, project) and keeps ~30-50 k characters of tool output out of the
   context for the whole session.
5. **The plan as a short list, not a program** (medium): Claude changes the quick draft's `plan_vN.json` through a
   small edit list applied by `draft_edit.py` ("cut f120-f188", "punch-in 1.2x at f300", "caption style X", "graphic
   talking-head-pack: point 2 at f1524", "a whoosh on every whip") instead of a 10-15 KB `edit_vN.py` and sed patches;
   captions = the script's words lined up to the transcript's times by the tool, not JSON written by Claude.
   *Can it work*: yes for talking videos and edits by feel - the quick draft already builds the plan by rules. The
   risk is an edit the list cannot say: the list keeps a raw-layer escape for one-offs. It is the biggest cut in
   Claude's own minutes (its writing), so it is measured on the two test videos.
6. **One look, one fix** (small; the skills): after the build Claude looks at the sheet and precheck's flags; a fix is
   a new edit list on the changed range (3c), at most one more round before the user sees it. The user's notes start
   the next round as today. Keep the pictures - a sheet costs ~1.6 k tokens and it is where the quality comes from.
   *Can it work*: yes if precheck + one dense sheet catch what Claude now catches in 3-5 render rounds; the risk is
   quality, which is what the user's side-by-side verdict in *Ships when* checks.
7. **Leaner context** (small): the root `CLAUDE.md` is 27.8 KB, twice the ~13 KB it was trimmed to, and every turn of
   every window carries it - move the tools' detail into their own docstrings (the rule already says to read them);
   a `--brief` output for `style.py`, `knowledge.py memory` and `overlay.py settings` (21-29 k characters in one
   session). *Can it work*: yes, but the gain is small (~2 % of a video's tokens for CLAUDE.md); the big token cut is
   fewer turns (steps 2, 4, 6).
8. **Effort per task** (small, the user decides): measured, Fable high took 8.4-9.9 min of thinking + writing a video;
   Opus xhigh 22 min and 165 k output tokens against Fable high's 83 k (not a clean test: the Fable run reused the
   Opus run's files). xhigh only for a new kind of video, high for the rest; one test video at medium against high
   decides whether medium is enough for edits.
9. **Measure and compare** (small): re-make the two test videos after each pair of steps; *What it took* gives the
   minutes and tokens, the user watches old | new side by side (`compare_renders.py`) and gives the verdict.

**Videos from zero** (Generator): steps 1-4 and 6-9 apply too, but what makes them slow is the ~42 KB of animation
code written for every video - 0.5.4's steps 5-7 (building blocks, formats, a quick draft for Generate). With this
plan alone: ~15-20 min of Claude per minute of video; ~10 needs 0.5.4's blocks and formats, with hand-written code
only for one or two standout moments.

**Could it work - Claude's estimate** (2026-10-15; replaced by the measurements of step 9): a 60 s talking video =
brief ~1 min + plan ~3-4 min of Claude + build ~4 min of the lab (one round) + one look and fix ~2 min = **~10-12
min**, in ~15-20 turns instead of 50-100 (tokens ~4-6x lower). Most likely to fall short: step 3 (HyperFrames' time
may not follow the pixel count) and step 6 (one look may miss what more rounds caught). Renders are slower on a
laptop, so the number is given per PC.

**Order** (the user decides): 1 and 7 (small, no risk to the result) -> 4 -> 2 -> 3, measured, (a) first -> 5 -> 6 ->
8; 9 after each pair. **Size**: medium to large; it can ship in parts - 1, 2, 4 and 7 first (the waits and the
turns), then 3, 5 and 6.
**Needs first**: nothing new - *What it took* (0.4.4) to measure, precheck and snapshots (0.4.2), the quick draft
(0.4.0). From the user: the verdict on the re-made test videos and a 60 s talking clip for the last check.

## 0.5.1 - planned - Yapping mode: the yap-maxing framework

**Ships when**: on 3-5 talking videos the user picked, the content foundations and the HEIT parts are there with frame
+ timecode and reviewed by the user; the yapping detectors pass their synthetic self-tests; the user's own recording
is edited from a cut list they approved before anything rendered, every cut on a word boundary; a talking
video made from a Prepare script has a clip - the user's or one MotionLab made - on every B-roll note (*The clips
a script needs*, below).

**Shipped in 0.4.0** (2026-10-13): first pieces of *Make* - the quick draft's talking mode (`draft_edit.py --sound
talk`, New edit's *Talking + captions* preset: the spoken parts in order, the pauses cut - by loudness, not yet on
word boundaries -, a punch-in every other cut, B-roll over the talking) and Claude's breakdown of a talking video
(hook, structure, captions). **Built early (2026-10-14)**: Prepare - `/write-script` and the script check (step
"Topic + script" below). Still open: the content foundations, HEIT labels, validated topics, delivery / environment
numbers, the yapping detectors with self-tests, cuts on word boundaries with the user approving the cut list, the
beats writer for the talking-head pack.

**The user's notes (2026-10-12)** ("v0.3.5" = describe video, now 0.6.0): "using the v0.3.5 as an exceptional tool
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
     HEIT script in the structure of the best videos of your format (0.5.3's database).
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
  from 0.5.4 (its step 12) on 2026-10-15.
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
    `compare_renders.py`; contact sheets: `sheet.py`); a motion graphic from 0.5.4's blocks (an app window, a
    cursor, a list, numbers - "a generic AI editor, the same template on three clips" as a mock-up, no real
    product's logo); a prompt for an AI video tool (`/write-prompt shot`, made on the tool's site, back into the lab
    by 0.5.6's step 2; through the API in 0.7.0); else a punch-in with the words on screen (what v4 did). Made clips go to
    `build\made\` and are named as made in the edit.
  - (d) **The edit follows the list**: `/recreate-video` lays each clip over the words it belongs to (speech to text
    gives the frames - v4: f310-450, f609-769, f770-888) and lists what is still missing before it renders. *Make*'s
    step 3 (the B-roll slots, above) is this list.
  - **What it needs**: the clip list in the script format (`/write-script`, guidelines section 9, `script.py check`
    - text, small); Film it's checklist (the app, small); a recorder for MotionLab's own pages (new - its frame rate
    and time measured on a laptop setting first; 3 of the first script's 4 B-roll notes were MotionLab screens);
    0.5.4's blocks for the mock-ups; from the user, which stand-ins matter most for their videos.
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
