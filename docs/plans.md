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

## Where it stands (2026-10-26)

Released last: **0.6.0** (2026-10-26) - Content agency, a big release (CHANGELOG.md + CHANGELOG.es.md): **My Brand** (the
page in three tabs - goal, audience, colours by role, fonts, logo versions, voice, pillars, products with facts and
media, captions, the editing look, the mood board, the end card with its sound logo - read from the user's website,
used *For my brand* by New edit, the Generator and Prepare), the **Content agency** (the calendar, When to post, the
post's checklist and A/B, Your videos and the stats exports, How it did), the **Editor** (a timeline: shots, speed,
graphics from the templates, captions and their style, sounds, effects), **Sound** (the library on every PC, the
sounds picked by ear, ElevenLabs sounds - 20 kept ship with MotionLab -, the music library and ambience beds, every
render mastered), cleaner talking edits (stumbles opt-in, captions off the face, the voice clean-up off until its A/B).
At the user's word ("i want to finish eveyrthing we have and only have released the 0.6.0", then "Build them first"
for the music library and the sound logo) it shipped once every step Claude could build was built; what waits on the
user is listed at the top of 0.6.1 (*Left from 0.6.0*). Its plan text: plans_history.md.

Before it **0.5.4** (2026-10-25) - Sound: recorded sound effects instead of made-up ones (this PC's library,
levelled against the song, picked by ear in three listening rounds - a sound not picked is set off, never deleted),
quick drafts with their own sound effects, a song from a link with a copy without it to post. It shipped in steps -
**0.5.3.3** and **0.5.3.4** - and its plan text is in plans_history.md. Released as it stood (the user, 2026-10-25:
"idk lets just upload the 0.5.4 version and start working on the 0.5.5 (which u will move to 0.6.0 since it will be a
big rrelease) and the otehr stuff just put it on version above"): its open steps - sounds on friends' PCs (an import
list), a music library and ambience, the user picking the sounds, crackle, plain cuts, the rating on two real videos -
moved into 0.6.0 (*Sound, continued*), and the plans renumbered: Content agency 0.5.5 -> **0.6.0** (a big release),
template packs 0.5.6 -> 0.6.1, colour 0.5.7 -> 0.6.2, content generation 0.5.8 -> 0.6.3, yapping mode 0.5.9 -> 0.6.4,
take notes from videos 0.6.0 -> 0.6.5 (plans_history.md, *Renumbers*). **Right after 0.5.4** (the user, 2026-10-25:
"after the 0.5.4 lets run the impeccable check on the app"): Impeccable's checker (pbakaus/impeccable, `detect`, no
AI, its telemetry off, the skill and its hooks not installed) on the app's pages, then fix what it finds (ideas.md,
*GitHub repos checked 2026-10-25*).

Before it, since 0.5.3: **0.5.3.1** (2026-10-25, 114 Motion Graphics templates) and **0.5.3.2** (2026-10-25, Film it
hands over to the Editor, Finish it with Claude).

Before them **0.5.3** (2026-10-24, CHANGELOG.md + CHANGELOG.es.md) - Faster videos (one build, the brief, the edit list, quick drafts for Generate, the waits as jobs) + a friend's asks (photos in edits, folders, no Mac / iPhone junk, pages that update by themselves, the NEW badge, Improve my script keeping one card, changes that survive updates, MotionLab's own taskbar icon) + *Preview your thumbnail* + fewer zooms in edits. Its plan text: plans_history.md. Still open from it: the re-runs (ae_50_test, testing_entire_workflow, What's new 0.4.3) with `usage.py project <name> --steps` before / after - the halving was not measured before the release (the user's call, 2026-10-24) - and F3 (the effort per task) after them; the Resolve builder does not place photos.

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
| 0.6.1 | Quality over quantity: many clips edited well, template packs | next - the user's focus (2026-10-26): edits done well, ten more minutes of Claude are fine; first many B-roll clips edited well (a clip catalogue made once, a shot list with pictures before any render, Claude's own review); shorts from a long video, scored on a researched rubric (moved from 0.6.4, 2026-10-27); vertical framing for every edit and editing by segments - a choice per segment, then the whole edit (2026-10-29); *Left from 0.6.0* (what waits on the user); then the template packs - the library shipped in 0.5.0; Resolve / After Effects / Lottie packs read exactly (AE with py-aep, no AE needed - 2026-10-25), templates used as they are, 3D blocks (Three.js), the motion check, formats, a preview before the render | L, ships in parts |
| 0.6.2 | Colour + DaVinci Resolve | planned - measuring a look + the match LUT shipped in 0.4.0; + the edit as a timeline file for Premiere / Final Cut (2026-10-25) | M |
| 0.6.3 | Content generation | planned - AI clips back into the lab, pictures from image tools, voice-over (voice and music moved to 0.5.4 2026-10-22; voice back 2026-10-25) | M |
| 0.6.4 | Yapping mode | planned - talking quick draft + talking-head pack shipped; starts with the content foundations; + the clips a script needs (from 0.5.0, 2026-10-15) (moved from 0.5.2, 2026-10-22); + *Research it* for scripts (2026-10-25; shorts from a long video moved to 0.6.1, 2026-10-27) | L |
| 0.6.5 | Take notes from videos: competitors, videos, courses | later - transcripts, numbers, the content panel shipped; courses added 2026-10-15; competitor analysis, music / voice stems and a reference's sound effects added 2026-10-25; SPARK - why a video worked - planned 2026-10-29 (can ship early, as Notes did) | L |
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
- **In *Generate***: 0.6.3 brings the clips the user made on a tool's site back into the lab (checked against the
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
- **Needs first**: 0.6.3 (AI clips back into the lab); 0.3's colour pipeline (done).

## 0.6.5 - planned - Take notes from videos: competitors, videos and courses

**Ships when**: a collection of ~10 analysed videos gives its topics with counts and quotes (frame + timecode), each
video's content reviewed Correct / Partly / Wrong by the user like effects, and searchable from Claude; a course of
~10 lessons gives the steps each lesson teaches (frame + timecode, the screen shown) and a course summary Claude
uses when it edits; a niche of ~10 profiles the user picked is scanned, its ~20 outliers get the light pass overnight
on a laptop setting, and its niche card - each reason with its videos and frame + timecode - is rated by the user.

**Renamed 2026-10-22** (the user: "Rename 'describe videos' to 'take notes froms videos'"); older notes call it
*describe video*. Competitors added 2026-10-25.

**The Analyser's three ways of analysing a video** (the user, 2026-10-27: "3 ways of analizing videos: 1) animations
and effects (currently) 2) content creation (scripts, why its viral, structure...) 3) information (take notes, how to
apply to urself, context to apply to other ai's...)"; for 3: "kinda like a notion but not that big, i just want to be
simple and effective"; then "before implementing the notes section i want you to deep research the topic, the best
way and most simplest way of taking notes, how to analyze teh video corretly with our tools (yt-dlp included) and if
we need to change anyuthing to optimize and how to structurally present the information ... like a professional, not
crowded"). 1 = today's Videos (unchanged); 2 = *coming soon* on the page (the friend's ideas below); 3 = **Notes**,
designed from the research below. **Built 2026-10-27, released in 0.6.0.5** after the user's answers ("yeah go ahead", "video
at 720p with option to delete the video afterwards but keep the notes", "drop test yourself questions", and each way
shown "with a "character" made in motion graphics"): the three ways with their scenes and the lab's round character,
`tools\notes.py` + `motionlab\notes.py` (the words, key frames, chapters, Most replayed, SponsorBlock; the quote gate),
the `/take-notes` skill, the job `notes` (Claude opens by itself when a batch is ready), the notes page
(docs\app_pages.md *Notes*), *Delete the video, keep the notes*. Not yet: words only (no download), the TikTok
captions in several languages, large-v3-turbo measured, collections across many notes.

**Notes - the research (2026-10-27)**:
- *How people remember notes.* Cornell notes (notes + cue questions + a summary) recalled lecture content best against
  outline and verbatim notes in a lecture study; reviewing the notes mattered most
  (dspace.unijos.edu.ng/jspui/handle/123456789/2566). Testing yourself beats rereading a week later (the testing
  effect, Roediger & Karpicke 2006, widely replicated). Progressive summarization (Tiago Forte): notes -> bold ->
  highlight -> an executive summary, each layer a filter, added when needed, not all up front. Typing more words
  verbatim did not hurt conceptual recall in the 2021 replication of Mueller & Oppenheimer (Urry et al., Psychological
  Science) - but a transcript is still not notes. So: a short summary on top, few points in our words with the
  video's own words as evidence, questions to test yourself, actions, and the user's own notes beside them.
- *What the video already tells us (yt-dlp, checked in its source 2026-10-27).* One `yt-dlp -J` (no download) gives
  the title, the description (links, resources, often the creator's chapters), `chapters`, YouTube's `heatmap` (the
  *Most replayed* graph: 100 points, 0-1), views / likes / comments, on TikTok `repost_count` (shares) and
  `save_count` (saves), the followers, the language, the subtitles and automatic captions (TikTok's auto captions
  too). SponsorBlock is built into yt-dlp (`--sponsorblock-mark`; it asks with the first 4 characters of the id's
  SHA-256, so the video is not named): sponsor, self-promotion, "like and subscribe", intro / outro ranges and the
  highlight (`poi_highlight`).
- *The words.* The platform's subtitles first (YouTube: uploaded ones, else the `-orig` auto captions with word
  timings), else speech to text (faster-whisper small, with VAD - Instagram has none). Pass the title, the channel
  and the chapter names as `names` (the spelling of names and brands). large-v3-turbo is clearly more accurate on GPU
  benchmarks; no CPU numbers were found - measure it on the laptop before switching.
- *What is shown.* Key frames only where the screen changes (a new slide, code, a new shot): ffmpeg decoding only the
  keyframes (`-skip_frame nokey`) with its scene score - seconds, not a full decode - capped at ~36 frames, filled
  every N s where nothing changes; sheets of 12, each frame labelled f480 (00:00:16:00); Claude reads them (no OCR to
  install). Talking heads and podcasts need none.
- *Claude.* The transcript, chapters, description, the *Most replayed* peaks and the sheets first, the user's question
  last; quotes first, then the notes (Anthropic's long-context advice: docs.anthropic.com/en/docs/long-context-window-tips).
  The gate = every point quotes the video's words (or names a frame it shows) and the tool finds the words and sets
  the frame + timecode itself; nothing is saved when one check fails.
- *To change in the tools*: `content.py` keeps a trimmed `info.json` (description, chapters, heatmap, tags, language)
  and shares / saves in stats.json; TikTok captions in several languages with no language named are skipped today
  (speech to text then hears it - slower); the `names` hint; a notes download of at most 720p (small, the screen
  still readable) or *words only* (nothing downloaded - a podcast, a long talk; the frame rate from `-J`).
- *How to show it (professional, not crowded).* Progressive disclosure: the little most readers need first, the rest
  one click away. A reading column (~70 characters) with the player and *My notes* beside it. In order: the title (the
  subject, not the clickbait) and one muted line (channel · platform · length · date · tags); **TL;DR** (1-2
  sentences); **Key takeaways** (3-7: a bold phrase + one sentence + a time chip that moves the player, the quote on
  hover, a mark on a *Most replayed* moment); **Sections** (the video's chapters, or Claude's: a title + one line each,
  folded; open = 2-5 points); **Steps** (how-to videos only, a checklist); **Apply it** (3-5 actions to tick - My
  Brand's goal and audience when there is one); **Test yourself** (3-5 questions, answers hidden); folded at the end:
  Resources (the description's links) and *Context for another AI* (Copy). The limits are the tool's, not the
  wording's. The kind of video picks the shape: tutorial (steps first), lecture / explainer (concepts), interview /
  podcast (topics, who said what), list video (the list), opinion / news (claims and their evidence). The Markdown
  download = the same order + My notes (+ the transcript when ticked).

**The friend's ideas for Content creation, reviewed (2026-10-27, pasted by the user)**:
- *The numbers from a screenshot* (comments = it shocked or split people, shares = people saw themselves in it): yes,
  as ratios against the channel's usual, not alone. yt-dlp already reads views, likes and comments, and on TikTok the
  shares and saves; a screenshot only where the platform hides them (Instagram's shares and saves, your own
  insights - watch time, retention), the numbers Claude reads shown to the user to confirm.
- *Merge it with Videos*: one video can be analysed both ways and its page shows both - not one combined pass (the
  effects pass is heavy, the *why* is cheap).
- *Learn from all of them, by itself*: yes - the collections / niche card above, after one video's *why it worked*
  works.
- *Claude right after the download, no corrections asked*: yes for Content creation and Notes (Claude's part starts by
  itself; the user's review stays optional, as Teach Claude is today).
- *Voice apart from the music, why that song*: the stems (*Sound*, below, measure first) + the song's measured tempo,
  energy and where its drop lands against the cuts + the platform's own track name (TikTok gives it) -> Claude's
  explanation; a lesson only when the user agrees.
- *A text's engagement as if 200-500 people read it*: a model cannot measure people - a simulated panel's
  percentages would look like data and are not. Instead: the script check part by part (0-5 stars, exists) and *where
  a viewer would drop* line by line, named as Claude's judgement, later checked against the user's real retention
  (step 19 below).
- *The same for a video before posting*: yes - a pre-post check of a render (the hook in the first 3 s, dead air,
  pacing against the references, captions readable, loudness: precheck.py measures part of it) with Claude's notes per
  moment, frame + timecode; Editor > Review.
- *Save the final video where you want*: yes, small - *Save a copy…* on a render (a copy; the build keeps its own).

**SPARK - why a video worked** (planned 2026-10-29 - the user: "after that maybe start working on the SPARK content
creation section on the analyser, make a good plan for everything and dont rush"; the Analyser's second way, its page
says *coming soon* since 0.6.0.5; researched the same day: docs\ideas.md *SPARK (why a video worked) - researched
2026-10-29*). It can ship early, as Notes did (0.6.0.5), and it is built the way Notes is: the lab prepares, Claude
writes, a gate checks, the page shows. **Before it**: the analysis Overview's Content creation panel (`profile.py`:
the first 3 s, words per minute, text on screen), Claude's `_breakdown` per focus, `content.py stats` (views, likes,
comments, followers, views / followers; TikTok's shares and saves), Most replayed kept at download, the thumbnail's
measures - spread over pages, with no *why* and nothing to compare against.
**Steps 1-4 built 2026-10-30, released in 0.6.0.8** (the user: "can u work on the SPARK section?"; "Put SPARK in
0.6.0.8"): `tools\spark.py` +
`motionlab\spark.py` (always its own folder `analysis\spark\<name>\` - the other ways are linked by SHA-256, not
shared), the `/spark` skill, the app (Content creation's way, its tab and page, #/spark/<name>, *Analyze with SPARK*
from an analysis or a video's notes; API_LEVEL 53). Measured on this PC: a light read of every frame at the analyser's
size on a fixed frame grid (its cut detector + text measure; a flash under 0.25 s is no shot) - a 2:36 min 1080p
video in ~37 s, a 26 s reel in 5 s; the words reused from the same video's notes / analysis; the creator's usual from
one flat yt-dlp list (~2 s; YouTube's videos tab rounds views and gives approximate months, the Shorts tab neither
dates nor lengths - its neighbours are its era); never across 2026-08-24; Instagram: views and the creator's list
unknown (likes / comments shown raw). Tested on NEMZZZ - 4AM (3.29x its usual - an outlier; Claude's write-up through
the gate on the first try but for a long verdict: the 3:59 -> 04:00 clock found as the title's payoff at 91 %) and an
Instagram reel (waiting for Claude). A FLUX analysis of the same video gives the hook's text (its checked text events
beat the rough measure). **2026-11-02**: the user's retention from a screenshot (traced by the lab, *Learn from your
own posts* R1 below) - on the user's own videos, with the drops at their frames and words. **Not yet**: step 1's
screenshot of Instagram's hidden shares / saves; steps 5-6 (6 begun with R1); the ship test on the user's 5 videos.
1. **`tools\spark.py prepare <video>`** (the lab, no Claude) -> `analysis\spark\<name>\` (or the analysis' own
   folder when it has one - one video, three ways): the words with timings, the first 3 s (cuts, words, text on
   screen), the pacing against the creator's own videos, the chapters and Most replayed, the thumbnail's measures, a
   sheet of one key frame per shot; **the numbers** (one `yt-dlp -J` the user starts, kept on this PC): views, likes,
   comments, shares and saves where the platform gives them, each per 1,000 views; **the creator's usual**: the median
   of the same creator's same-format videos from the same era (YouTube counts a view the moment it starts playing,
   ad views included, since 2026-08-24 - never compared across that date), the video itself left out, Shorts apart
   from long videos; the outlier score = views / that median (views / followers is weak for Shorts, Reels and TikTok,
   where most views come from non-followers). What a platform hides (Instagram shares and saves, the user's own
   retention and CTR): a screenshot Claude reads and the user confirms.
2. **Claude writes it** (a `/spark` skill, opened by itself when a video is ready, like Notes - nothing for the user
   to correct): one rubric for every video, so videos can be compared (a builder of such a tool: free-form answers
   could not be compared, a fixed list was his biggest gain) - **the idea and who it is for** (does it reach past the
   niche); **the packaging promise** (title, thumbnail / cover, first frame - the glance); **the hook, 0-3 s** (its
   type from a fixed list; picture, words and text saying the same thing); **the promise kept** (where the payoff
   lands, as a share of the length); **open loops and re-hooks** (questions, "but", where Most replayed rises);
   **structure and pacing** (against the creator's own median - never "more cuts = better": a 2026 study found faster
   pacing lowered completion); **emotion** (awe, anger, worry, humour - moderate evidence); **why people would send
   it** (useful to one person, or makes the sharer look good); **why people would comment** (a question, a split
   opinion); **craft** (captions, sound, graphics - FLUX's measures where the video has an analysis); **the ending**
   (loop, call to action); **context** (a trend, a collab, timing, paid views) - and always the line **"not
   explained"**: what the video itself cannot account for. Each point is labelled *measured* / *Claude's judgement* /
   *unknown* and carries its evidence (a quote, a frame + timecode, or a number); words like "consistent with", never
   "caused" or "will go viral"; no simulated audience. Then **what to take for your videos** (3-5 actions, with My
   Brand's audience when there is one; a ticked one goes to Prepare's script check and hooks). High views with low
   ratios = the packaging did it, not the video - said so.
3. **The gate** (`spark.py save`, like `notes.py save`): every quote found in the words, every frame + timecode set by
   the tool, every number recomputed by the tool from the saved numbers (Claude cannot write a ratio of its own), every
   rubric point labelled, the *not explained* line present; nothing saved when a check fails.
4. **The page**: SPARK's list (like Notes'); a video's page - one line of verdict, its numbers against the creator's
   usual (bars), the rubric as cards whose evidence chips play the moment, *not explained*, the take-aways;
   *Analyze with SPARK* on a FLUX or INDEX video, and the other way round.
5. **Many videos** (the second step): the contrast set - a creator's or a niche's outliers against the same
   creators' weak videos of the same format and era, "present in X of 20 outliers vs Y of 10 weak", matched pairs
   (same topic, different result) - is the *Competitor analysis* below (its depths 1-3), its niche card read by
   Prepare, New edit and the quick draft.
6. **Learn from real results**: the user's own posts (Content agency's check, their screenshots of retention) set
   against what SPARK said of the references they followed. The retention part: *Learn from your own posts* R1 below
   (built 2026-11-02); the tests, the lessons' confidence and the next tests: R2-R4 (all built 2026-11-02).

**Data rules - checked 2026-10-29 in YouTube's API developer policies** (they correct step 17's "fixes a terms
problem" below): III.E.6 no scraping; III.E.4.b statistics not authorised by their owner kept at most 30 days;
III.E.4.h no "new or derived data or metrics" from API data unless an audited developer asked for it (III.L) - so the
API makes the *fetching* allowed, not an outlier score made from its numbers. The choices were: (a) per-video
lookups the user starts with yt-dlp (as `content.py stats` does today - YouTube's terms bar automated access; few,
user-started, never shared), (b) the API showing its numbers as they are with the creator's usual beside them and no
score, or (c) the user's own channel only, through their login (step 19). **The user's choice (2026-10-29): (a)** -
"Lookups you start": one video at a time when the user clicks, the outlier score kept, the numbers on this PC only,
never in shared cards. Instagram bars automated collection; TikTok's research API is for non-profit academics.

**Ships when (SPARK)**: on 5 videos the user picks (3 that went viral and 2 ordinary ones of the same creators), every
SPARK page passes the gate, the numbers match what the platform shows, and the user calls at least 4 of the 5
explanations useful, with no measured fact wrong. **Needs first**: the user's data-rules choice above; nothing to
install (Notes' parts are built; the data rules chosen: (a)).

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
   3 s, camera moves), the words by speech to text, music and its tempo, sound effects (*Sound*, below), one sheet of a
   key frame per shot. Measured on a laptop first: the time per minute of video decides how many fit in a night
   (0.4.5's bulk runs them).
3. **Why it worked** (Claude, per niche, in batches): the numbers, transcripts and sheets of ~20 outliers against ~10
   of the same profiles' weakest videos - what differs, not what they all do: the hook, the script's structure (HEIT,
   0.6.4), the format, music, sound effects, shots and B-roll, what keeps people watching; each reason with the videos
   and frame + timecode it comes from -> a niche card in Claude's memory (text, shareable), read by Prepare
   (*Research it*, the formats), New edit (the style of a niche) and the quick draft.
The deep, frame-accurate analysis stays for the few videos the user wants to copy (the Analyser, as today). Rules:
public posts only, the videos and transcripts stay on the PC, only numbers, short quotes and the niche card are
shared.

**Your stats and the competitors' through YouTube's own APIs** (0.6.0's steps 17-19, moved here 2026-10-26 - the
user: "youtube analytics stuff for later 0.6.x versions"; the scan above runs through step 17's API once it is built):
- 17. **The YouTube competitor and outlier scan through the Data API** (S-M): a free API key (no login; 10,000 units a
    day, a video or channel = 1 unit). **Fixes a terms problem**: reading YouTube stats with yt-dlp (`content.py
    stats`, 0.6.5's planned scan) is against YouTube's terms (no automated access); the API does the same within
    them (other channels' stats kept 30 days at most unless refreshed; checked 2026-10-29 - true for fetching, but
    a score derived from the API's numbers is barred too: *Data rules* under SPARK above). TikTok / Instagram competitors stay single
    lookups the user starts. YouTube is testing the same idea in Studio (a *Research* tab with outlier multipliers).
- 18. **What worked this month** (M, once there is data; **built 2026-11-02** with R4 as Content agency > *Monthly
    review*, released in 0.6.0.9): top videos by retention and views, which pillar, hook and format worked, the A/B winners -
    into Claude's lessons, with R3's confidence and ending in R4's three next tests (*Learn from your own posts*,
    below - what was built and what is not yet).
- 19. **YouTube Analytics connection** (M, later): retention curves, traffic sources, impressions + CTR (the bulk
    Reporting API, since 2026-01) - OAuth with the user's own Google project (a desktop client, 127.0.0.1; in
    *Testing* the login lapses every 7 days, so the client is published unverified - a warning screen, 100 users at
    most). Instagram after it (a Creator account - not Business, which loses music - and a token pasted from Meta's
    dashboard, 60 days, refreshable); TikTok's API last, if ever (counts only, an app review with a demo video).

**Learn from your own posts** (2026-11-02 - the user brought a creator's "AI content coach" guide (six prompts and a
TikTok Studio collector) and asked whether it fits Content agency; reviewed the same day, then: "add them to plans and
start working on improving the SPARK and content agency secitons"). **Not taken**: its tooling - a collector that reads
TikTok Studio with the user's saved login on a daily timer (its own notes: it "does not make automated access
undetectable or remove account risk"; the lab reads public numbers only, when the user presses it), PostgreSQL,
Descript, NotebookLM, scheduled runs. **Kept: four ideas**, fitted to SPARK's labels (measured / judgement / unknown)
and steps 18-19:
- R1. **Where people left** (S-M, **built 2026-11-02**, released in 0.6.0.9): the user's own retention graph - a screenshot of
  TikTok Studio's, YouTube Studio's or Instagram's (the user's own numbers, no login, no reading of the platforms) -
  traced by the lab, not read by Claude (more exact than a reading, no Claude time): the user puts four lines on the
  graph's axes (0 s, the end, the top and bottom %), the tool finds the curve's colour (or the user clicks it) and
  follows it column by column -> the share still watching at every second, *unknown* where the curve cannot be seen
  (never filled in). Then every 3-second window's relative loss, `1 - r(t+3) / r(t)` (when r(t) > 0), the holds at 3 s,
  10 s and the end, and the user's usual (the median of their own traced videos on that platform, from 5). In Content
  agency a video card gets *Where people left*; in SPARK, the user's own video gets the curve under its player with
  the steepest drops lined up with the words and the shot on screen (frame + timecode), and the table's `ret_*`
  numbers for Claude - "a drop shows where people left, not why": the why stays *judgement*. This is SPARK step 1's
  screenshot and the first piece of step 6; step 19's API gives the same curves for YouTube later.
- R2. **Tests of one idea** (M, **built 2026-11-02**, released in 0.6.0.9 - the user: "continue with R2"): Content agency's
  third tab *Tests* (`motionlab\experiments.py`, `tools\experiments.py`, `knowledge\local\experiments.json`): 2-3
  versions of one idea posted on ONE platform (A / B / C - a fixed id, never told apart by their caption), each its
  post link (picked from Check my pages' videos or pasted) and optionally the MotionLab video it was made in; the rule
  picked first = one number (views at 48 h / 7 d / 28 d from the checks near that age, held at 3 s / 10 s / the end
  from R1's graphs, likes / comments per 1,000 views, the stats file's average % viewed) + a minimum of views; the
  tool's result = waiting (and why) / too close to call / a winner that beats every other version by 25 % (views,
  ratios) or 3 points (%), always with "one post each - not a controlled test, repeat it". The states are worked out:
  planned (a version not posted) -> testing -> compared -> reviewed (Claude) -> closed (the user's pick + note; a
  closed test stays closed); *Test again* = a new test linked to its parent with the picked version as A. Claude's
  review (`/spark test <id>`, the gate `experiments.py review`): needs every version read by SPARK (the test's button
  starts it, no Claude) - **keep / change / cut** at frames of each version's video (frame + timecode set by the
  tool, quotes found in that version's words), each change `edit_only` / `re_record`, every change and cut *to test*
  with the number it should move, the retention over its frames when traced, and a next test (try / the same / the
  number); *Make the next version* = `/recreate-video improve <project> test:<id>` (improve.md *From a test*:
  edit-only items done, re-record items listed for the user). The post's `ab` line stays - it is YouTube's own Test &
  compare (thumbnails / titles inside one video), another thing.
- R3. **Lessons that earn their confidence** (M, **built 2026-11-02**, released in 0.6.0.9 - the user: "continue with R3"):
  Content agency's fourth tab *What works* (`motionlab\findings.py`, `tools\findings.py`,
  `knowledge\local\findings.json`). Every own post (Check my pages + the traced graphs, the last 120 days) = its numbers
  (R2's) + features **measured by the lab only** - length, the hour and day it went up, the calendar's pillar, and when
  SPARK read it: text / cuts / words in the first 3 s, the first cut, cuts and words per minute - so nothing is
  labelled after the numbers were seen. A pattern = one feature split (a number at its median, yes / no, one value
  against the rest) x one number, per platform; it stands out only with >= 8 videos a side, a clear margin (R2's) and
  still with its strongest video left out ("one video carried it" = can't tell). The scan lists what stands out now
  (hunches only, with how many patterns were tried - some are chance); the user keeps one = confirmation 1 (*hunch*).
  Every *Check my pages* (and a traced graph, and the button) tests the active lessons again: supports with >= 3 videos
  no counted run used = +1 (2 *likely*, 3 *settled*); the same videos = nothing; can't tell with >= 3 new = *weakened*
  (one step down); the other way = *refuted* (the claim kept, the run's numbers shown); untested 30 days = one step
  lower, 90 = *stale* (worked out, never stored). Likely / settled lessons go into Claude's memory (`knowledge.py
  memory` and `--rules`: "patterns across the user's posts, never one video's cause"; hunches only counted). Measured
  2026-11-02 on the user's posts: 38 in the window, nothing testable yet (likes per 1,000 views known for 14 TikTok
  posts, 16 needed) - the tab shows each platform's distance to the bar and *Measure my posts with SPARK* (no Claude,
  ten at a time). **Not yet**: Claude's blind labels (the hook's type and the like, written by a pass that sees no
  numbers) - SPARK's own `hook_type` is written with the numbers in view, so it is not used.
- R4. **The review ends in three next tests** (S, with step 18; **built 2026-11-02** with step 18 as Content agency's
  fifth tab *Monthly review*, released in 0.6.0.9 - the user: "continue with R4"; `motionlab\monthly.py`, `tools\monthly.py`,
  `knowledge\local\monthly.json`): the lab's month first, no Claude - per platform the month's median against the usual
  (the median views of the platform's posts of the last 120 days that were 7+ days old at their check, from 5; younger
  posts are *still growing*, never ranked), the best posts by views and by held at 3 s, the month's posts grouped by
  pillar / length (up to 30 s, 31-60 s, 1-3 min, over 3 min - the long videos apart) / text in the first 3 s (median
  × and n: "a hint, not a pattern"), the month's tests, the lessons and their runs that month, last month's next tests
  and where they got to on the calendar. Then Claude (`/spark month <YYYY-MM>`, the gate `monthly.py review`): one
  line of summary and exactly three next tests - `try` (one change), `same`, `metric` (R2's; Instagram only retention /
  average viewed), `why` and 1-6 evidence items (posts of the last 120 days, lessons, tests; at least one post of the
  month); three different tries, no cause words, every × / % / per 1,000 one of the month's numbers **of that unit**
  (an × must be an × against the usual - a % that happens to be near is refused). *Put it on the calendar* = an idea
  (`"next": "<month>:<n>"`, its words, the same + the number in the notes), once per test; a new review keeps the
  picks. Checked 2026-11-02 on the user's October (20 posts, 6 still growing at the 2026-10-26 check): it reads and
  ranks them; nothing written to the real stores. **Not yet**: the review into Claude's memory (the lessons already
  go there through R3); YouTube's own retention per month (step 19).
**The bars** (measured 2026-11-02 on the user's pages, the last *Check my pages*, 2026-10-26): 10 TikTok and 10
YouTube videos with 1,000+ views in the last 60 days - the guide's own bar (20 per platform) would answer "too few"
for now, so R3 waits for more posts; R1 works from the first video and R4's review from the first month of posts (its
groups say "a hint", the patterns stay R3's).

**Sound** (moved from 0.5.4's steps 5 and 7, 2026-10-25 - the user: "lets just move to a later version"):
- **Separate music from voice** (measure first - heavy on CPU): Demucs stems for cleaner beats / drops and cleaner
  speech, and to lower the music under the voice.
- **A reference's sound effects, measured** (the friend's point 5, after the stems; measure first): the whooshes and
  hits of an analysed video found apart from its music, placed against its cuts and effects with frame + timecode ->
  the light pass's sound effects (above) and *like the reference* in New edit's Sound step (its amount and kinds). A
  self-test with known cues first.

**Courses** (the user, 2026-10-15: "and maybe in the future maybe bulk analyze courses? of davinci resolve or courses
on content creation? (i think this is a similar idea we have for the 'describe video' version. what do you think?
so maybe make that instead of v.0.8.0 to 0.6.0, but have the bulk stuff in 0.4.5 so it links up well to 0.5.4 and
then we just move upwards to 0.6.0"): a course = a collection of long videos (its lessons), analysed with the
content focus on 0.4.5's batch runner. Per lesson: the transcript, the steps taught (one key frame per step - the
screen, the panel, the values set), the tools and settings named (DaVinci Resolve's pages, nodes, values), the
lesson's notes; per course: a summary, "how do I ...?" answered with the lesson + frame + timecode, and techniques
Claude can rebuild (a Resolve technique from a course -> a recipe in the library, tested like the effects; the
templates a course gives go through 0.6.1's template packs). Measure
first: Claude's time per minute of a long lesson (0.4.4), then decide what is read from the transcript only and
what needs pictures. **Rules**: courses are someone's paid work - the user's own copies only (paid platforms are
usually locked against downloads), everything stays on the PC, only the user's notes can be shared.

**Shipped in 0.4.0** (2026-10-13, the user's overhaul): the *content creation* focus of Analyze - references
without subtitles get their words by speech to text when it is installed (`content.py auto`); the analysis
Overview's Content creation panel (`motionlab\profile.py`: the hook - cuts, words, text in the first 3 s; words per
minute and how much is talked; text on screen per minute; captions likely); Claude's breakdown per focus (review.json
`_breakdown`: hook, structure, captions, text & graphics, B-roll, sound, CTA); all searchable in Claude's memory.
**Moved to yapping mode** (2026-10-14; now 0.6.4): the foundations - text on screen, the shots described, topics and claims per video
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
  first step (0.6.4). Here: across many videos.
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

## 0.6.4 - planned - Yapping mode: the yap-maxing framework

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

**The user's notes (2026-10-12)** ("v0.3.5" = describe video, now 0.6.5 *Take notes from videos*): "using the v0.3.5 as an exceptional tool
when creating a video: 'yapping mode' or talking to the camera. Focused on content creators: yap maxing framework.
Influential videos, lots of views videos. Basically making content short or long form; take into account formats.
HEIT framework = hook / explain / teach / illustrate. Validated topics. Copy and learn structure. Extras: 1) text on
screen 2) environment: experiment different environments 3) delivery: authentic content 4) graphics: visual hooks."
(Earlier, 2026-10-11: analyse talking-head creators AND edit the user's own recording that way.)

- **Goal**: learn from talking-to-camera videos that work (many views) and make your own - short or long form - in
  the same proven structure, from the topic to the finished edit in the lab and in DaVinci Resolve.
- **First: the content foundations** (moved here from describe video, 2026-10-14 - this settles the order conflict
  between the two; 0.6.5 builds on them): per analysed video `analysis\<name>\content\content.json`, reviewed by the
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
     Which formats work comes from videos that did well against their channel (0.6.5's competitor analysis), not from
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
  5. **Shorts from a long video** (the user, 2026-10-25): **moved to 0.6.1** (2026-10-27, the user's ask), researched
     and planned there.
- **The clips a script needs** (added 2026-10-15, from the first talking video made from a Prepare script, *MotionLab
  vs other AI editors*; its v4 note: "the script's B-roll (the report with its contact sheet, a generic AI editor,
  your render beside the reference, the Prepare page) does not exist in the project, so those moments stay on you
  with the punch-ins and the list". The user: "wouldn't it be better to know which clips to prepare or give you
  before I make the decision to edit it with MotionLab? so maybe in the prepare section when creating the script,
  you could advertise to create the specific clips (as vague as possible) and if not you could create it as I need
  it?"). Today a script's `[B-ROLL]` / `[VISUAL]` notes are text: *Film it* lists them under *Film these too*,
  nothing checks that they were filmed, and the edit finds out at the end. Moved here
  from the motion-graphics plan (now 0.6.1, its step 12) on 2026-10-15.
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
    `compare_renders.py`; contact sheets: `sheet.py`); a motion graphic from 0.6.1's blocks (an app window, a
    cursor, a list, numbers - "a generic AI editor, the same template on three clips" as a mock-up, no real
    product's logo); a prompt for an AI video tool (`/write-prompt shot`, made on the tool's site, back into the lab
    by 0.6.3's step 1; through the API in 0.7.0); else a punch-in with the words on screen (what v4 did). Made clips go to
    `build\made\` and are named as made in the edit.
  - (d) **The edit follows the list**: `/recreate-video` lays each clip over the words it belongs to (speech to text
    gives the frames - v4: f310-450, f609-769, f770-888) and lists what is still missing before it renders. *Make*'s
    step 3 (the B-roll slots, above) is this list.
  - **What it needs**: the clip list in the script format (`/write-script`, guidelines section 9, `script.py check`
    - text, small); Film it's checklist (the app, small); a recorder for MotionLab's own pages (new - its frame rate
    and time measured on a laptop setting first; 3 of the first script's 4 B-roll notes were MotionLab screens);
    0.6.1's blocks for the mock-ups; from the user, which stand-ins matter most for their videos.
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

## 0.6.3 - planned - Content generation: AI clips, pictures and voice

**Ships when**: the clips of a shot list made on an AI video tool's site come back into the lab, are checked against
their shots (length, size, frame rate, a first / last frame sheet for continuity) and cut on the song with 0.6.1's
blocks and 0.5.4's sound on top - one video, in the lab and in DaVinci Resolve - and each clip is rated against its
prompt.

**The user's words (2026-10-14)**: "while moving from 0.4.1 to 0.5.4 id like to have the 0.5.4 version as a
'contente generation oriented version' ... i want the generation of video through claude and other tools such as
hyper frame or other to be more redefined and work better." On 2026-10-15 its motion-graphics part became its own plan
(now 0.6.1, *Motion graphics*; the user: "yeah go ahead"); on 2026-10-22 its voice and music went to 0.5.4 (*Sound*);
this plan keeps the rest (its old step numbers: plans_history.md); on 2026-10-25 the voice-over came back (step 3) so
0.5.4 can ship with sound effects and music.

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
2. **Pictures from image tools** (was part of 0.6.1's step 10; measure first, only where a block cannot do it): Nano
   Banana / GPT Image for pictures in a scene, through the prompt library's `image` kind.
3. **Voice-over** (back from 0.5.4's step 4, 2026-10-25; measure first): ElevenLabs (the user's own account) or a
   local text-to-speech measured on a laptop first (time per minute of speech, size, how natural) - VoiceStudio
   (debpalash/VoiceStudio: a local ElevenLabs alternative, the app AGPL, each voice model its own licence - commercial
   use checked per model; ideas.md *GitHub repos checked 2026-10-25*) is the first local one to measure; its words
   timed like speech to text, so captions and scenes follow the voice. A voice only with the speaker's consent.

**Order** (the user decides): 1 (it closes the AI route), then 2 and 3. **Size**: medium.
**Rules**: AI clips labelled as generated, generated voices too; the paid API for AI video stays in 0.7.0.
**Needs first**: 0.6.1's blocks and 0.5.4's sound (what goes on top of the clips); the prompt library's ratings per
model, to rate each clip against its prompt.

## 0.6.2 - planned - Colour: measure a look, match it, grade in DaVinci Resolve

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
  0.6.1 step 4 (a template rendered by `aerender` into a clip). Not planned: Claude driving all three at once - Resolve
  already gives the edit and the colour, HyperFrames the motion graphics; Premiere's and After Effects' scripting
  needs paid Adobe apps most friends lack (ideas.md *Later*).

## 0.6.1 - planned - Quality over quantity: many clips edited well, motion graphics from template packs

**The focus: quality over quantity** (the user, 2026-10-26: "for future plans i want to focus 0.6.1 on a "quality over
quantity" version, idc if you spend 10 more minutes in editing a video or sum but i want it well done, as feedback igot
that u are having a bad time editing videos when i give u lots of b-rolls, how could we improve that?"). The measure of
an edit is the result, not Claude's minutes (0.5.3 halved them; ten more are fine). Two halves of one aim: **many clips
edited well** (below, first) and the graphics from **template packs** (the rest of this plan, the 2026-10-15 text);
between them **shorts from a long video** (2026-10-27).

**Many clips edited well - why it goes badly today** (read in the code 2026-10-26; no many-clip project on this PC -
the biggest has 3 clips - so the friend's case is the test):
- *Claude edits blind*: `brief.md`'s *The clips* is one line of numbers per clip (length, size, sound, transcribed or
  not), nothing about what it shows. To know, Claude reads `storyboard.py`'s boards - a tile every 25 frames, 36 per
  sheet: 40 clips of 15 s = ~720 tiles on ~20 sheets - and has to remember "clip Q = the coffee pour" by itself
  through a long chat; an *Improve* or *Finish it* window starts again from nothing.
- *The quick draft picks by numbers only*: each shot = the sharpest, best exposed, right-motion moment not used yet
  (`draft.py pick_windows`), in no story order; B-roll over talking = a random clip nobody talks in, every few
  seconds for 1.5-2.5 s (`broll_layers`) - never the clip that shows what is being said. It avoids the same clip twice
  in a row, not two clips of the same scene.
- *Every clip is decoded whole first* (`prep_footage.py`): by its own formula ~5.6 GB per minute of footage in a
  1080x1920 edit at 30 fps, ~18 GB per minute for a 4K horizontal clip in a vertical edit - 10 minutes of B-roll =
  56-180 GB and the time to write it, before the first shot is picked; under 2 GB free it stops.
- *Clips that do not match*: phone clips are often HDR (iPhones record it by default) and come out flat beside the rest
  (no tone mapping - the cache warns); a horizontal clip in a vertical edit is cut in the middle or shown whole over a
  blur - its subject is not looked for.

**Where it stands (2026-10-26, the user's "go" to steps 5 + 1 first)** - test bed `projects\zz_many_clips` / `2`: 36
clips (6.5 min) cut from four music videos and a reel in `refs\` (25 / 30 fps, horizontal and vertical, three filming
days) - not the friend's B-roll, which is still the real test. **Step 5 built**: the light cache + sparse full cache
(prep_footage `prep_light` / `fill` / `ensure`, footage `SparseFrames` / `needed`; render_video fills before it renders):
33.0 GB / 131 s -> 2.1 GB / 35 s, a 30 s draft's full frames ~2.2 GB; every filled frame on the light cache's own
frame (checked on all 36 clips). **Step 1 built** (the lab's part + Claude's lines): `tools\catalogue.py` make / sheets
/ say / show - 244 moments in 48 s (the analyser's cut detector on the light frames), quality words tuned on the test
bed (dark grades are a look, not a fault), look-alikes by shape + colours + layout + edges; the brief carries it
(`brief.catalogue_lines`), the skill's by_feel / improve read it. **Step 4, the lab's part, built**: the quick draft
scores down windows outside the usable parts, across a cut inside a clip, like the shot before, back in time (test
bed: 1 -> 0 crossing shots, 2 -> 0 look-alikes back to back). **Released as 0.6.0.3** (2026-10-27). Then (2026-10-27,
the user: "release the 0.6.0.3 and continue"): **step 6** - each moment's `subject` (YuNet face, else a
spectral-residual saliency centre) is the quick draft's anchor (the crop of a horizontal clip in a vertical video and
any punch-in centre on it); HDR clips tone-mapped in the light read, the fill and `--full` (prep_footage.tone, the
analyser's zscale / hable chain - a PQ test clip: contrast 32 -> 86, colour 59 -> 131); **steps 3 + 7, the lab's
part** - `catalogue.py shots <project> [plan]`: every shot as it will look from the light cache, no render, and what
to fix (outside the usable part, across a cut, like the shot before, a moment twice, the subject cut off); the skill
fixes those before any render and shows the user the sheet. The quick draft now also scores down a moment already
used and a scene used often (test bed: 18 -> 26 different scenes in 28 shots, the most used scene 9x -> 2x, the shot
check 3 -> 0). Then (2026-10-27, the user: "the b roll is to have the sound from the clip before going on, so NOT
changing" + "repos where people might have some presets"): **B-roll on the words** - researched rules (docs\ideas.md
*B-roll rules*) as the quick draft's numbers: an insert on the word its catalogue line says (+0.25 s) or on a jump
cut, 1.5-4 s, the face keeps the first 15 % and the last 10 %, no face under 2 s between inserts, at most 40 %
covered, picture only (test project `zz_talk_broll`: a 26 s take + 10 music-video clips, inserts on "post" and
"singing", the voice under them = the take, envelope correlation 1.00 at 0 ms); clips loud all through (music,
ambience) next to a real take are B-roll (pauses under 15 % of 10 ms windows; takes 30-49 %, B-roll 0-9 % on 4 takes
+ 25 clips); `catalogue.py shots` no longer flags a take's own jump cuts. **The shot list in the app, built 2026-11-03**
(the user's /whats-next pick "Shot list in the app"; steps 1 + 3 below): a plan's shots as pictures before any render
(the video's page: *Check the shots*), swap any for another moment of the clips, then *Render with these shots*; New
edit's *Check the shots first* (on from 6 clips) = the quick draft makes the catalogue and stops before its render,
Claude stops before its build; the Editor shows each shot's line and takes the user's correction. **Next**: the
friend's real clips (the ship test below).

**Steps** (each measured on one many-clip project before / after: Claude's minutes and tokens, the disk, the user's
rating):
1. **A clip catalogue, made once** - `build\clips.json`. The lab's part (no Claude): every clip split into its moments
   (a new scene or camera move inside a clip, a steady hold), the usable windows (sharp, exposed, steady or one clean
   move) and the bad ones (a shaky start, the floor, out of focus), moments that look alike grouped, the date each was
   filmed (the file's creation time, like photos' date taken), one key frame per moment. Claude's part: those key
   frames ~20 per sheet with frame + timecode, one line per moment - what it shows, shot size (wide / medium / close /
   detail), where, light, motion, a few tags (person, place, product, screen, food, text). Every later window
   (*Improve*, *Finish it*) reads it instead of looking again; the Editor shows the line under each clip and the user
   can correct it (a correction wins).
2. **The brief holds it**: *The clips* = the catalogue grouped by scene and by date, the bad windows named to leave
   out.
3. **A shot list with pictures before any render**: Claude builds the story from the catalogue - the strongest moments
   for the hook, an order (by date for a vlog, a build for a promo or a music edit), shot sizes that vary (wide ->
   close), no two moments of one scene back to back unless that is the point; a talking video's B-roll on the words it
   shows (the transcript matched to the catalogue's lines). The user sees it as one sheet - a key frame per shot, frame
   + timecode, the words under it - and swaps or approves before anything renders (*cheapest check first* 1-2, with
   pictures).
4. **The quick draft reads the catalogue**: the lab's part always (bad windows never used, look-alike moments not back
   to back, date order when there is one), Claude's lines when they exist (B-roll matched to the words) - so *Quick
   draft now* with many clips is a fair start. A small local picture-and-words model for that match without Claude
   only if it earns its install (measured first against Claude's lines, on a laptop).
5. **Cache only what the edit uses**: the numbers (sharpness, motion, light) and the key frames from a small proxy of
   every clip; full-size frames only for the picked moments with handles (re-cached when a pick changes). Disk and
   prep time measured before / after on the many-clip project.
6. **Clips that match each other**: HDR clips tone-mapped (this ffmpeg has `zscale` + `tonemap` - checked 2026-10-26;
   tried on a real iPhone clip first); a horizontal clip in a vertical edit framed on its subject (a face, else the
   most salient part - 0.6.4's reframe) instead of the middle; exposure and white balance brought close to one hero
   clip (a shot match - the grade stays 0.6.2's).
7. **Claude's own review before the user sees it** (the ten minutes the user offered): after the plain build, a sheet
   of every shot checked against one list - the best moment of its clip, no repeat, nothing blurry / shaky / dark, the
   subject in the frame, each B-roll on its words, colours that match, moves only where the picture changes (M rules)
   - fixed, then shown with what was fixed (frame + timecode). What it teaches goes to `lessons_making.md`.

**Ships when (this half)**: one project with many B-roll clips (at least 30 clips / 5 minutes of footage, phones and
orientations mixed - the friend's clips if they share them, else the user's) edited by Claude is rated **good** by the
user on the shot picks and on the B-roll fitting the words / story, with no shot they call bad (blurry, shaky,
repeated, wrong subject); a second window (*Improve*) reads the catalogue without looking at the clips again; the
prep's disk and time measured before / after. **Needs first**: that project (only read, as always); nothing to
install (OpenCV + ffmpeg split, tone-map and pick the key frames; Claude writes the lines).

**Vertical framing for every edit** (planned 2026-10-29 - the user: "encuadre para redes (en vertical)"; researched
the same day: docs\ideas.md *Vertical framing - researched 2026-10-29*). One piece the many-clips half (step 6),
the shorts (step 5 below) and the Editor share, built once. **Released as 0.6.0.8** (2026-10-30): steps 1, 2, 4, 5
and 7; steps 3 and 6 wait on the user's three videos. **Today**: a horizontal clip in a vertical edit is cropped
round one fixed point per moment (the catalogue's `subject`: a YuNet face, else a saliency centre); the person track
(`person.py`, smoothed both ways) moves only the zoom point of the face-led effects; a photo can be shown whole over a
blurred copy (`"fit": "contain"`). The renderer already draws everything a reframe needs - an `anchor` that moves
(a curve), a clip in part of the frame (`rect`: splits, a corner camera), the blurred fill - what is missing is the
decision per shot, the layouts, who is talking, the limits and the controls.
1. **Hold or follow, per shot** (the lab, `motionlab\reframe.py`, no Claude): with the whole shot known in advance
   (AutoFlip's way), the subject's track (the face track, else the person mask's centre, else saliency; detected at
   ~480 px wide, ~5 fps, on the light cache) -> **hold** = one still crop when the face box stays inside the crop
   with >= 8 % margin in >= 95 % of its frames (most talking shots), snapped to the centre only within ~3 % of the
   crop; else **follow** = a path of holds, constant pans and eases (never a frame-by-frame wobble): moves under 4 %
   of the source width skipped, pans at most ~0.5 crop widths a second, eases of >= 12 frames, a new path at every
   cut. Written as the clip's `anchor` curve (compose draws it); the eye line stays where the camera put it (a
   full-height crop cannot move it without a zoom). **Built 2026-10-29** (released in 0.6.0.8): `motionlab\reframe.py`
   (`apply(plan)`; faces at ~5 a second from the light cache, kept in `<ID>.faces.json`; pans that touch joined into
   one - an S-curve stops at both ends; a close-up wider than the crop kept on its middle; never changed: a clip that
   follows the face itself, a shake, keyframes, a point set by hand) run by every quick draft (`framing:` in its log,
   *Framing* in `draft_vN.md`); self-check 11 cases (`selftest.py` *reframe*; the path the same as compose draws it).
   On `zz_many_clips2` (28 shots of music-video clips): 23 framed in 0.9 s (0.06 s once the faces are kept) - 9 held
   on the face, 14 kept (no face, or a shake); s22_I f697 (00:00:23:07) had half the face cut off by the catalogue's
   point, now centred. Not yet: a real follow (no test clip with someone crossing the picture), a vertical clip in a
   horizontal video (the y axis), the subtitles burned in at the crop's edges (step 4).
2. **Layouts** (a shot's `layout`, picked by rules, changed by the user): **Fill** (9:16 on the subject - one face);
   **Fit** (the source cropped to 4:3, over a blurred copy - a solid colour when its background is plain; not the
   whole 16:9 band, which fills 32 % of the height) for a wide shot, a chart or two people too far apart; **Split**
   (two people stacked - never 50 / 50 when a half loses the top of a head: bands measured on the faces, the captions
   on the seam, at most two panels); **Screen + face** (a screen recording on top, the face below - a dense screen
   as a cutaway instead); **Game** (the face 30 %, the game 70 %). **Built 2026-10-29** (released in 0.6.0.8; the user's
   changes = step 5): compose draws a clip in `panels` over a `backdrop` (one layer per shot, so the Editor's moves,
   cuts and transitions carry them; the first panel's crop centre = the clip's own anchor - its keys, a shake, the
   face track - the others' their own + a shake's swing; the face found in whichever panel shows it); reframe.py
   picks per shot: **fill** (one face, or people that fit in one crop together), **split** (two people of a size -
   the second at least half the first's face, in 70 % of the samples - too far apart for one crop: the left one on
   top, each panel zoomed so the other face stays out and both faces come out 30 % of their panel wide, the upscale
   at most 2.2x; else a fit), **fit** (a 4:3 band - zoomed in on a group, the faces 40 % down - over a blurred copy,
   or the wall's own colour when the band's edges are plain: seamless; three or more people, a split that does not
   fit, someone too fast to follow), **screen** / **game** (a face camera found by its straight borders round a
   small face that stays put - the screen on top 58 % cropped round where it changes, the face below; a moving
   picture round it = a game, the face on top 30 %); captions on a split's seam (facefit.py). The Editor's preview
   draws them, and two older preview faults it showed are fixed (a crop off the middle of a horizontal clip in a
   vertical video showed the middle; a clip placed before its size was known stayed wrong while paused). Tested:
   self-check 23 cases + the panels rendered from a made-up clip (selftest *reframe*); `zz_layouts` (made from the
   user's two takes, only read: one talker, two far apart, two side by side, two in tiles, a screen recording and a
   game with a face camera, a dash across) - every layout where expected, the renders and the Editor's preview
   alike; `zz_many_clips2`'s draft unchanged (a passer-by in s22_I first turned its shot into a fit: the size and
   presence rule above). Not yet: a real two-person talk or screen recording (the user's three videos), a
   borderless or round face camera (Loom's bubble), a voice-over screen recording without a face (step 4's text
   check), the face camera's upscale (2.7-3.1x on the tests: soft - step 4).
3. **Who is talking** (two or more faces in one shot, one mixed sound): the words' timings say when someone speaks;
   per face a mouth signal (a frame difference in the mouth box YuNet's landmarks give - nothing to install)
   correlated with the sound's loudness over 1-2 s windows - a nodding listener moves but does not correlate.
   Measured first on a two-person clip; Light-ASD (MIT, 1 M parameters, needs PyTorch) only if that fails and earns
   its install. Cuts only in word gaps, each speaker held >= 2 s, turns under 1 s ignored ("yeah", "mm-hmm"), after
   ~10 s on one speaker a variant (the wide shot or a punch-in); crosstalk = Split.
4. **Limits**: the total upscale at most ~2.0-2.2x (a 1080p source in a 1080 x 1920 crop is already 1.78x; a 4K
   source can punch in freely) - past it Fit or Split; a chart, a chyron or text burned in at the frame's edge kept
   whole (an edge-text check on the light frames -> Fit); captions and graphics inside `safezones.py`'s safe area and
   never over the mouth (the face box). **Built 2026-10-29** (released in 0.6.0.8): layouts decided on the zoom a shot holds
   (80 % of its frames - a zoom-through's 1.7x peak at a cut no longer counts; step 2 took the peak); a fill past
   2.2x = a fit (a 720p clip: 2.7x -> its band 1.1x); text burned in (subtitles, lyrics, chyrons, titles - lines of
   letter edges, wide, near the top or the bottom, at one place in 40 % of the samples; the poster on the user's wall,
   a shelf, a room's words never) that a fill or a split would cut = a fit as wide as the text needs (up to the whole
   picture), its crop kept round the text; a shot with no face whose crop cuts it = a fit round it too; the panels'
   faces inside the apps' safe area (safezones.py "all"): the eyes under the top band, the mouth over the bottom one
   (the chin may go under it, as captions may) - a split zooms both panels in alike (at most 1.5x, while the faces
   stay under 45 % of the panel) for a low face, a game's face camera moves down under the tabs, a screen + face ends
   at the bottom band (the backdrop under it; its face camera less blown up: 2.4x, was 3.1x); captions on the seam of
   any two stacked panels, the least-covering place when a moving face blocks every other one, and off text burned in
   (`"reframe"` `"text"`). Tested: reframe self-check 30 cases, facefit's 7; `zz_layouts` + a subtitled talker, a 720p
   talker and a two-shot with a chyron (renders and the Editor alike); a 6-shot captions test (overlay.py captions +
   facefit: every caption on a seam, under the text or off the faces); `zz_many_clips2`: the lyrics burned into its
   music-video clips found in 6 shots and nothing else in any shot - those 6 now fits (the people smaller: the user
   decides whether a montage keeps that). Not yet: charts (only lines of text are found), text in the room's middle
   (a slide, a sign held up), a person who moves a lot vertically in a held split (a hold does not chase it).
5. **Where it is used**: the quick draft (every clip whose shape is not the video's); New edit's step *Framing*
   (Auto / Fill / Fit / Split, Auto by default); the Editor (a shot's *Framing* section: the layout, hold / follow,
   the crop dragged on the preview - its keys in *Position and size*; the safe zones already drawn); the shorts (step
   5); Claude's edit lists (`frame <shot> fill|fit|split|screen|game [hold|follow]`). **Built 2026-10-29** (released in 0.6.0.8,
   API_LEVEL 51): `reframe.frame_shot` = the user's framing of one shot (a layout - the rules' limits aside - Still /
   Follow, or the crop's dragged centre per panel), marked `"by": "user"` so no automatic run changes it, Auto = the
   rules' again (its own point back); refused with why (a split of one person, screen / game with no face camera, a
   shaking shot, a picture shown whole); the Editor: a shot's *Framing* section above *Position and size* (Auto /
   Fill / Fit / Split / Screen / Game as little phones - Auto's own pick dashed -, Still / Follow, *yours* once
   changed; the change `frame`) and the crop dragged on the preview (the picture follows the pointer, the panel under
   it, a press that does not move still plays; `EdPreview.cropDown`; the faces found kept only on a save, never by a
   preview); the edit list's `frame 4 split | frame s04_A fit hold | frame 3 follow | frame 2 auto`; New edit: a
   *Framing* question in 6. Final beside the format (not a step of its own: it only matters with a vertical or square
   format, and shows only then) -> the request's `framing`, the brief's line, the quick draft's `--framing` (every
   shot that way where it can be, the rules elsewhere). Tested: reframe self-check 34, miniedit 55; on `zz_layouts`'s
   faces every choice, refusal, Auto and drag through the Editor's change; in the app (a test server + headless Edge):
   the section, Fit, a refused Split, Auto, an 80 px drag, New edit's question shown / hidden with the format; the
   save (`tools\miniedit.py apply`) -> plan_v3 rendered as chosen. The shorts: when step 5 of *Shorts* is built.
6. **Checks** (`catalogue.py shots` + the precheck): the face out of the crop, half a person, the crop on the
   listener, the upscale past its cap, text cut at the edge, captions over the mouth; a test set of the known
   failures built once (`make_testvideo.py` + the user's clips): a reacting listener, "mm-hmm" flicker, three people,
   two people too far apart, fast walking, a profile / tiny face, a face on a poster or a TV, no subject at all, a
   chart at the edge, small screen text, a cut inside a pan, a soft upscale.
7. **Film it** (Prepare): a short checklist - the lens at eye level, eyes on the upper third, mid-chest up, ~1-1.2 m
   away, facing a window; filming horizontal for both shapes: 4K, the subject centred. **Built 2026-10-29**
   (released in 0.6.0.8): Film it's *Before you film* (`FI_FRAME`, `FI_CHECKS`) = a framing picture (a 16:9 picture, you in
   the middle from the chest up, the eye line on its upper third, the 9:16 crop drawn in it) + five rows with icons,
   their why in the tooltips; it replaces two lines of *While you film* (eye level / light in front; "vertical for
   TikTok, horizontal for YouTube" - now "only vertical? film vertical; both shapes? horizontal, 4K, you in the
   middle"). Checked in the app in English and Spanish.

**Ships when (framing)**: three of the user's horizontal videos - a talking head, a two-person talk, a screen
recording - come out of the quick draft as vertical videos with the face in frame in every shot, no wrong speaker, no
cut-off chart or screen text and no wobble, and the user calls them good; the test set passes; the cost on a laptop
measured (seconds per minute of footage). **Needs first**: those three videos (only read); nothing to install.

**Edit by segments: a choice per segment, then the whole edit** (planned 2026-10-29 - the user: "editar por
segmentos" and "borrador (quick draft) select each segment how u would like it edited and then create the edit
entirely"; researched the same day: docs\ideas.md *Editing by segments - researched 2026-10-29*). Step 3's shot list
grown up: the list the user approves becomes the list the user edits with. **Released as 0.6.0.8** (2026-10-30): all
seven steps. **Today**: the quick draft follows one
style for the whole video (a preset, a feel or up to three references); the feel test shows only the hook in 2-3
feels; anything per shot is changed afterwards in the Editor, one by one.
1. **Segments** (the lab, no Claude), by kind of video: talking / vlog = sentences (word timings + pauses >= 0.4 s -
   the same splitter as the shorts' step 1) grouped into one-idea beats of ~3-12 s, never cut inside a sentence, with
   topic edges above them (Claude reads the transcript once - or 0.6.4's Hook / Explain / Illustrate / Teach parts
   once they exist); a music edit = phrases of 4 or 8 bars between downbeats, the drop its own segment (`beats.py`);
   a tutorial = its steps (the words + where the screen changes); a B-roll montage = the catalogue's moments. Each
   segment: a key frame, its words (or its bars), first / last frame + timecode. **Built 2026-10-29** (with step 2;
   released in 0.6.0.8; the app = step 6): `motionlab\segments.py` + `tools\segments.py <project> [plan]` ->
   `build\segments_vN.json`. Talk: the edit's words (`draft_edit.edit_words`, now with each word's end) ->
   `stumbles.sentences` (a pause of 0.4 s, and a **jump cut between two words = a pause**: a quick draft cuts the
   pauses out, so on its timeline the words run on - without this a 36 s draft gave 3 segments, one 14.6 s long) ->
   beats of 3-12 s; a count said before its pause ("... and four | Color grade") opens the next part. Music: phrases
   of 8 / 4 bars between downbeats (only with a song under the video - the clips' own sound is no song), the drop on
   its own, no piece under 3 s. Else (a montage, no words, no song): runs of shots. The segments tile the edit.
   Not yet: a tutorial's steps (where the screen changes). Topic edges: built in step 7 (Claude's topics).
2. **Treatments** - recipes the lab knows, each with what it needs: *Plain* (nothing - the rest between busier
   parts); *Punch-in + key word* (the framing above + the word to stress); *B-roll on the words* (a catalogue moment
   that shows a concrete word, starting within ~1 s of it - B-Script: 73 % of expert inserts); *List / steps* (an
   enumeration said + a template with that many slots); *Number* (a number said -> a counter / callout); *Split /
   picture in picture* (a second source: a screen, a product); *Section title* (at a topic edge); *Screen zoom /
   cursor* (a tutorial); *Beat montage / drop hit* (music); *A motion graphic* (a library template picked by the
   words). Each segment shows ONE recommended treatment with its reason in one line and two alternatives (the
   research: more options overwhelm) - by rules: a number -> *Number*, an enumeration -> *List*, a concrete word with
   a matching clip -> *B-roll*, a topic edge -> *Section title*, else *Plain* or *Punch-in* in turn. **Built
   2026-10-29** (the recommendations; their build = step 4): in this order - two items counted inside it -> list, a
   part opened by a count ("Three, every graphic...") -> title (its count no number said), a number -> number, a word
   a B-roll clip's catalogue line says (`draft.stem`, as the quick draft matches) -> broll, a softer opening ("next",
   "now") -> title, mostly a screen recording (its framing) -> screen, else a punch-in on its key word (a number, else
   its longest content word, never a "something") and plain in turn, the hook a punch-in; music: the drop, the
   build-up before it -> beat, the intro -> plain, then beat / plain in turn; a motion graphic always an alternative
   (`templates.pick` names the template when its words score 6+); never one treatment three times in a row. On the
   user's footage: the corner-camera take (36 s) = 6 segments - the hook a *Number*, each numbered part opening its
   own with a *Section title*; *Your song needs a real video* = 8 (its "200" a *Number*, *now-playing* offered from
   "music, song"); `zz_talk_broll` = B-roll on "scroll" (the clip of a phone with an Instagram feed); a song test and
   two montages. Self-check 10 cases (selftest *segments*). Not yet: the word the voice stresses (its loudness) as the
   key word.
3. **Three layers, as Descript does**: the style once (fonts, colours, the caption look, zoom strength, the sounds,
   the transition family, the pacing measured from the references - New edit's steps as today); the rules' picks;
   the user's own picks - kept through any re-run or style change. *Recommended for all*, then only the exceptions;
   *Apply to all like this* (same kind of segment or same treatment); limits across segments: never one treatment
   three times in a row, a template once a video, B-roll coverage capped - today's 40 % (`draft.py` BROLL_COVER) is a
   ceiling, and B-Script's experts covered 13.2 % of 3-minute vlogs: the drafts' real share measured first, then the
   target taken from the references' own measured B-roll share. **Built 2026-10-30** (with step 4; the lab only - the
   app is step 6): the style = the request's (its captions look, the brand's / the palette's colours and fonts on the
   cards - a dark accent gives way to the brand's light text colour over footage); the user's picks in
   `build\segment_picks.json` (`segments.py --set 3=broll[:C]`, `--like 3` = Apply to all like this: the segments the
   rules gave the same pick, `--reset 3 | all` = Recommended for all; a set of changes all or nothing, a pick a segment
   cannot take refused with what it can), each tied to where its segment starts in its clip (talk / clips) or its song
   (music), so a re-run of the draft keeps it (within 0.6 s); a pick whose part is gone is kept aside. Limits for the
   rules' picks (the user's stay): never one treatment three times in a row, a template the words pick once a video,
   a B-roll moment once, never on the hook, at most draft.BROLL_COVER (40 %) of the edit; music = beat and plain in turn.
   The drafts' B-roll share measured: 21-26 % (`zz_talk_broll`, the only draft with B-roll). Not yet: the references'
   own B-roll share (the analysis does not measure it) as the target.
4. **The build** (the lab, seconds): the picks compiled into an edit list (`cut`, `graphic <template> at f for n`,
   `effect`, `caption`, `sfx`, `frame`) on the quick draft - one plan, deterministic; nothing is guessed that the
   user picked. Claude fills only what needs judgement when asked (*Finish it with Claude*: which clip, the words on
   a card), then checks every cut boundary and that each claimed change is in the plan (the research: editing agents
   claim cuts they never made). **Built 2026-10-30**: `segments.py <project> --build` - on a BARE quick draft
   (`draft_edit.py --bare`: the cuts, sound, colour and framing only; made first from a full draft's own arguments,
   now kept in its made_by "args", else its notes' *Arguments* line; a built plan builds again on its bare one), the
   picks as edit-list lines (`build\segments_vB.list`, a block per segment with frame + timecode and whose pick) ->
   `draft_edit.py --apply --base` -> the next plan, then `segments.verify`: every cut where it was, each segment's
   pick in the plan, nothing added to a plain one, the B-roll share. New list lines: `broll C at f for n from k
   anchor=x,y`, `jump f to k` (a cut inside a shot, music), `column` on a graphic (below). punch = 15 % closer on the
   key word, back at the segment's end; number = big-counter (the value said, its unit, the words after it); title =
   headline-box (the part's opening words / the next 4); list = checklist (the items counted); graphic = the template
   the words pick, its main words the first phrase; screen = a slow push; drop = a flash + a shake (a punch-in on a
   panned shot); beat = a cut on every beat, each piece inside one usable part of its clip (a catalogue moment - one
   that crossed into the next scene was the precheck's vanish). Cards (`"clear_face": true`) are moved the least way
   off the faces and the captions once rendered (`facefit.fit_cards`, build.py); in a wide video each card is a
   column a quarter of the width at its edge, size 1.5 (local-make-1, -25 - a 1920-wide headline-box was 1327 px
   wide, over the face in every close-up). Tested: the corner-camera take (horizontal, For my brand) = a number, three
   titles, a punch-in - every card clear of the face (the precheck agrees); `zz_talk_broll` (vertical) = a punch-in,
   B-roll on "beat", the user's title kept through the bare draft's re-run; a music montage (a song from refs\audio)
   = beat / drop / plain / beat, precheck PASS; a montage through the framing's fit = punch-ins inside the band.
   Not yet: the words on the cards are the rules' (the transcript's - often no punctuation) - Claude's (*Finish it
   with Claude*) or the user's in the Editor; a split with a second clip; captions by the brand's own values (only
   its look's id).
5. **Previews that cost nothing**: per segment a still with its treatment at its key frame (from the light cache,
   `render_video.py --stills`) and one line saying what changes; *Preview this segment* = a small render of that
   segment alone; the full render once, at the end. **Built 2026-10-30** (with step 6): `segments.py --stills` = the
   bare draft's frame at each segment's key frame (render_video.py --stills from the light cache, ~2 s for all) ->
   `build\segments\v<B>\seg_<n>.jpg` - the footage, not the edit: a still is made once and never goes stale; what the
   edit does is its chip + its why line, and its preview; `--preview N` = that segment's own lines on the bare draft
   as a plan that is no version (`draft_edit.py --apply --out segpreview_v<B>_s<N>.json`), its cards rendered and
   moved off the faces, `render_video.py --range` its frames -> `build\segments\v<B>\preview_<N>_<f0>-<f1>.mp4`
   (19 s with B-roll, 28 s with a card on zz_talk_broll); previews.json keeps the pick it shows (a changed pick = no
   preview shown).
6. **The app**: New edit gets a *Segments* step after Clips and Text - one row per segment (its picture, its words,
   the treatment chip with its two alternatives, *Recommended for all*, *Apply to all like this*), then *Build the
   edit*; the Editor shows the segments as a lane (a changed pick rebuilds only that segment). **Built
   2026-10-30**: New edit's 7th step *Segments* (after Final, not after Text: the parts come from the draft's cuts,
   which need steps 3-6) - *Cut it into parts* (the job `segments` = `segments.py --request`: a bare draft from the
   request + the parts + their pictures; 4 s with the caches made), a row per part (its picture / preview, frame +
   timecode, its words, its edit + two others + the rest, why in one line - translated by key -, *yours*, back to the
   suggestion, *Apply to all like this*, *Preview*), *Recommended for all*, *Cut it again* (the picks stay with their
   parts), *Build the edit* (the job `segments_build` = `--build --render`, 32 s on zz_talk_broll); GET / POST
   `/api/project/<p>/segments` (a pick in 1.6 s, all or nothing); the Editor's *Parts* lane on a bare draft or a
   version built from one (a part's panel, dashed = changed since that build, *Build again with these picks*). The
   app's test found one thing the engine fixed: a pick of the user's moved the next part (the rules' plain / punch-in
   turns counted it) - now the rules' run follows the rules' picks only. Not done: "rebuilds only that segment" - a
   changed pick builds the whole edit again from the bare draft (seconds + its cards' renders); hand changes made in
   the Editor after a build are not carried into the next one (the panel says so).
7. **Claude's way in**: `brief.md` gets *Segments* (the list with the picks); `/recreate-video` writes its own picks
   in the same form, so a Claude edit and the user's picks are one format, and the user can change Claude's. **Built
   2026-10-30**: Claude is a layer between the rules and the user - `segments.py --claude <file>` (`{"picks": [{"n",
   "t", "opt", "text", "why"}], "topics": [{"n", "name"}]}`, checked against the parts - all or nothing - and replacing
   Claude's earlier ones; `--reset claude`) puts them in segment_picks.json as `"by": "claude"`, anchored like the
   user's; the suggestion = Claude's pick where it made one, else the rules'; the user's stay on top (*back to the
   suggestion* = Claude's; *Recommended for all* takes back only the user's). What rules cannot do and Claude adds:
   `text` = the word a punch-in / B-roll lands on, or a card's words (a title "line 1|line 2", a number's words, a
   list's items, a graphic's main words - the rules' are the transcript's), `why` in the video's language, and the
   **topic edges** (step 1's not-yet): a topic's first part gets a title card with its name (never the hook). B-roll
   is now a pick for any talking part when the edit has B-roll clips (a clip the user / Claude chooses where the
   rules' stems matched nothing - a phone scrolling for "scroll past"); a Claude B-roll's moment is kept from the
   rules' later picks. brief.py's *Segments* = the list (every word, whose pick, all a part can have, the topics) when
   the parts were cut from THIS request (the bare draft's arguments = the request's), a line to cut again when they
   were not and the user picked some, else nothing; recreate-video `by_feel.md` *By segments* = how Claude picks
   (never over the user's) and builds (`--build --render`, never a free edit list over it); New edit's Segments step
   shows *Make it with Claude* beside *Build the edit*; the rows, the Editor's lane and panel mark *Claude's* with its
   own why and words, a topic above its first part. Tested on `zz_talk_broll`: a file with five mistakes refused whole
   (a pick a part cannot have, a word not said, no such template, no such part, a part starting two topics); Claude's
   3 picks + 2 topics built as picked (plan_v10: the punch-in on "real" f24, clip G on "scroll" f174, the title "What to
   do / Sing the hook" f212, the rules' B-roll on part 4 moved to clip I since Claude's took G), the app in English and
   Spanish (a pick over Claude's and back). Not yet: a real Claude window's run on the user's footage (the corner-camera
   take) - the user's to start; Claude's why stays in the video's language in a Spanish app.

**Ships when (segments)**: on one ~60 s talking video and one music edit, the user sets every segment in under ~3
minutes (*Recommended for all* + a few changes), the edit builds from the picks in one go with no segment unlike its
pick, a re-run keeps them, and the user calls the result good; the B-roll share measured against the references.
**Needs first**: the vertical framing above (for punch-ins and splits on horizontal footage), the sentence splitter
(shared with the shorts' step 1); nothing to install (topics by Claude; a small sentence-embedding model only if it
earns its install, measured first).

**From the research, picked for 0.6.1** (2026-10-29, the user ticked three of docs\ideas.md *Claude's guides,
skills and repos*; the user's order: vertical framing first, then segments, then SPARK):
- **HyperFrames' craft checks**: the upgrade from 0.8.149 tried with `overlay.py upgrade-test` and the self-test
  first; then `check`'s `line_unread` (a line on screen too briefly to read), `dead_stretch` (over 3 s with nothing
  changing), `text_below_floor`, `first_frame_empty`, `film_silent` in the build summary, the contrast audit back on
  (`overlay.py` passes `--no-contrast` today) and the review sheets (scene starts / middles, a strip across every
  cut, the beats at phone width). A template the upgrade draws differently is fixed or the pin stays.
- **A waveform and the words on the cut-sheet**: `render_video.py --cuts` draws stills only - under each cut the
  sound's waveform and the words around it, so a cut inside a word or a pop shows on the sheet Claude reads after
  every build.
- **Hard rule 1 enforced by Claude Code**: deny rules in `.claude\settings.json` for writing into `refs\` and the top
  of `projects\<name>\`, and a hook that stops a delete / move / rename aimed at them - in every permission mode; the
  tools' own SHA-256 checks stay. **Built 2026-10-29** (released in 0.6.0.8): `Edit(/refs/**)` denied; the PreToolUse hook
  `.claude\hooks\guard-sources.sh` -> `guard_sources.py` on Bash, PowerShell, Edit, Write and NotebookEdit - refuses
  a write at a project's top level (a `projects/*/*` deny rule would also match `build` itself, so that part is the
  hook's) and a delete / move / rename / overwrite (a redirect's target only) of `refs\` or a project's top; 32 known
  cases (`--selfcheck`, in `tools\dev\smoke.py`); seen live: `rm refs\<a file>` refused in this session.

**Shorts from a long video** (moved here from 0.6.4 step 5, 2026-10-27 - the user: "in the 0.6.1 it could be possible
for it to take a 10min video and get shorts from it (calculating from the possibility of going viral like good moments
or dramatic ...) search to see the best possible way"; it reuses this half's light cache, catalogue, subject framing
and B-roll on the words). **Researched 2026-10-27** (docs\ideas.md *Shorts from a long video*): the paid tools
(OpusClip's 0-99 score = hook, flow, value, trend; Vizard, Klap, Descript, Riverside) and the open repos (ClipsAI,
OpenShorts, SamurAIGPT's generator, SupoClip, video-use) all work the same way - the words with timings -> candidate
stretches on sentence / topic edges -> an LLM scores them on a rubric -> cut, reframe to 9:16, captions. Nobody's score
is proven: OpusClip's own blog says 60-scored clips sometimes beat 85-scored ones, and on 13k podcasts labelled by
YouTube's *Most replayed* (Rhapsody, 2025) GPT-4o and Gemini without training did about as well as simple rules. So the
score ranks the moments of ONE video against each other - never "this will go viral" - and learns from real results.
1. **The words and the signals** (the lab, no Claude): the video read once into the light cache and transcribed
   (faster-whisper small, word timings); split into sentences (punctuation or a pause >= 0.4 s - ~120-150 in 10
   minutes); per sentence, against this video's own median: loudness and its peak, pitch range, words a second, the
   pause before it, faces and motion (the catalogue), scene cuts, laughter / applause (the transcript's own marks; a
   light detector - YAMNet, 3.7 M weights - only if it earns its install, measured first), text flags (a question, a
   number, "but / actually / nobody / mistake", "you"); minus points for a greeting, a sponsor read, an outro, "as I
   said".
2. **Claude reads the whole transcript** (10 minutes = ~5k tokens with sentence numbers and marks like `[LOUD +2.1]`
   `[LAUGH]`; over ~20 minutes only the lab's top 20 windows, a sentence of context each side) and returns twice the
   shorts wanted (~10-12): first / last sentence, the hook line, the payoff line, the rubric's parts, *stands alone*
   yes / no, an optional cold open (a 2-5 s line from later, put first). **The rubric** (0-5 each, x weight):
   - **hook x2**: a claim, a question, a conflict, a number or a reaction in the first 3 s - no greeting, no setup;
   - **stands alone** (a gate): no start mid-sentence, on a filler or on a "that / he" whose subject is not in the
     clip, no "as I said" - fixed by starting earlier;
   - **arc and payoff x1.5**: setup -> tension -> something specific -> the payoff, ending on its last word (a payoff
     at 60-90 % of the length);
   - **value or emotion x1.5**: a concrete tip, or awe / anger / worry / humour;
   - **shareable x1**: a line people would send or quote, an opinion, a "that's me";
   - **energy x1**: above the speaker's own level, laughter, an animated delivery;
   - **density x0.5**: words a second once the pauses go;
   - **picture** (a gate, x0.5): a face to crop for most of it, a readable screen, the action in frame.
   OpusClip's *trend* becomes **fits My Brand's audience** (brand.json), later what 0.6.5's competitor scan finds.
3. **The lab cuts them**: start / end on word edges (50 ms before, 80-200 ms after, never inside a word; a pause of
   0.4 s or more = a clean cut), past a laugh, 20-45 s by default (60 s for a story or a tutorial; the platforms allow
   up to 3 minutes), a candidate overlapping a better one by more than half dropped, then talking mode's pause and
   filler cuts.
4. **The user picks** (the app): a card per short - its key frames as a 9:16 strip, the hook line, the score's parts
   and why, first / last frame + timecode, a preview from the light cache; tick the ones to make. Before building,
   Claude checks each pick on one sheet of 8 frames of the 9:16 crop (the hook, the crop, the ending).
5. **Each one as a vertical short**: reframed per scene by *Vertical framing for every edit* above (built once; its
   first design, kept for the record - AutoFlip's design: a still crop when the face stays inside
   ~60 % of the crop's width - most talking shots - else following it with a dead zone of ~8 % and smoothing; a blurred
   fill when it cannot fit; the framing's own numbers win); two people: a hard cut to whoever talks at a sentence
   edge, each held 2 s or more (1.5 s in the first design),
   never a pan between them, a stacked split for crosstalk (who talks: mouth movement against the sound, tried first;
   a model only if that fails); a screen recording: the screen in the top band, the face below; captions and a hook
   title inside the platforms' safe zone and not over subtitles already burned in; B-roll on its words; the sound
   finished -> `build\shorts\short_N` plans -> renders.
6. **Learn from real results**: YouTube's *Most replayed* curve (yt-dlp's `heatmap`, kept at download for references)
   shows which parts people replay - the lab's pre-rank is measured against it; the user's posted shorts (Content
   agency's check) and their good / bad ratings move the weights.

**Ships when (shorts)**: on one 10-minute video of the user's (a talk or a podcast - and one gaming or music video, to
see where picking by the words fails) the lab + Claude offer 8-12 candidates in under ~5 minutes on a laptop
(measured), the user rates the top 5 and calls at least 3 good, and 3 picks render as vertical shorts with the face in
frame - no wrong speaker, no half person, no chart cut off (OpusClip's own list of misses). **Needs**: that video
(only read); nothing to install unless the laughter detector earns it.

**Graphics part of the shot** (2026-10-27 - the user, of Vibha Ramprakash's claude-video-effects skill (MIT, 45
face-tracked effects): "the results are pretty impressive", then "hyperframe is good on its own but combining it with
talking heads or people is where it gets kinda AI-ish"; Claude's read: not the drawing tool - our graphics are made
blind to the footage and pasted on top; the user: "yes go ahead"). **Built**: `motionlab\person.py` - per
clip, from its light cache, the person's mask (Google's Selfie Segmenter, 250 KB, `tools\models\`, read by OpenCV's
own TFLite reader - no MediaPipe; the same SHA-256 as Google's file) and the face (YuNet), smoothed both ways; made by
`render_video.py` only for plans that ask (the user's 54 s webcam take: 31.5 ms a frame, a face in 100 % of
frames); compose.py layer keys `behind` / `guard` / `follow` ("face" or "camera") / `glass` / `shadow` / `match`
(the mask refined at full size by a guided filter on the frame); a self-test with a made-up person (behind, guard,
glass 70 -> 3 detail, a camera follow within 1 px); the skill's graphics.md says when to use which. **The A/B**:
projects\zz_behind_test (a copy of the user's corner-camera take, 1920x1080) - the library's frosted-glass pill and a
big word, today's overlays vs the same graphics integrated (`build\compare\today_vs_integrated_v2.mp4`); integrated
renders at ~9 fps vs ~18. What the test taught: a lower third must not follow the face (it chases the punch-in into
the face), a word behind the person follows the camera (the room), not the head; a punch-in under a lower third puts
the chin on it. **Then built** (the user: "look very cool but maybe u zoom in too much? try some ease-in ease-out ...
basic flow keyframe charts ... carry on with the switch, the face-led effects, recreate vibhas best design as templates
and lets review the entire workflow"): designers' eases (easy / strong / glide / launch + "cubic(...)") and
the Editor's curve tiles + a two-handle chart; clip `track: "face"` + `room` (dim / blur / grey) in compose; Editor
effects *Lean in* (15 %), *Slow push* (12 %, room melting), *Spotlight* (room to 30 %) with room chips; the graphic
panel's *In the shot* (`gfit`); `snap` (a graphic centred on the face, fitted inside the frame); templates' `in_shot`
applied by the Editor and by edit lists (`graphic ... [behind|glass|guard|pin|plain]`, `effect <kind> at f`, the
backdrop off over a video); the shot check flags a graphic over the face and one the face cuts into; the looks' film
grain no longer veils a video; **13 templates** after Vibha's designs (three builders in parallel; word-behind,
led-sign, lock-on-brackets, countdown-flip, scribble-callout, comment-box, follow-tap, message-stack, reject-stamp,
settings-toggles, glass-graph, task-checklist, headline-box - Spanish included); the skill's graphics.md maps her 45
to ours. **The workflow demo**: projects\zz_vibha_demo (a copy of the user's "Your song needs a real video" take, 16:9
webcam) - talking draft -> `build\edit_v2.list` (7 graphics + 2 effects on the words) -> v2: the brackets past the frame,
three cards bitten by the face (taught the fit + the check) -> `edit_v4.list` (cards smaller, far right) -> graphics ->
shot check 0 -> `zz_vibha_demo_v4.mp4`. Then the user's vertical phone take (script-009, "Why MotionLab is different",
copied into projects\zz_vibha_vertical so their own v1-v6 stay apart): talking draft -> `edit_v2.list` (3 cuts, 7
graphics, 2 effects on the script's words) -> graphics -> shot check (a face bite, a card into the apps' bottom band,
light words on a white shirt, a skin smudge under glass - each fixed: placement, `tone=smoke`, `glass: 60`) ->
`zz_vibha_vertical_v2.mp4`, the shot check 0 and the safe zone clear but the LED sign's dimmed room. **The release
check** (the user: "make sure all of the video effecets from vibha are actually here and can be used smoothly"):
`edit_v4.list` = all 13 templates + the 3 effects on one 30 s vertical take -> `zz_vibha_vertical_v4.mp4`, every
graphic rendered, the shot check 0, face / safe-zone flags 0 (what it fixed: a pinned graphic shrinks into the frame
and out of the apps' top band, the brackets and the scribble carry `over_face`, a behind layer's dimmed room is not
counted as drawn, `glass: true` = 44 px - 18 left a skin smudge); each of the 13 added through the Editor's apply
lands with its own placement and switches. **Released as 0.6.0.4** (2026-10-27). Not built of her 45 (graphics.md
has the map): reels-around-you (noise, orbit, carousel, phone fan, profile wall, place-in-grid, check pills), lineup,
the bill, swipe, uninstall, reel frame, shortcut rain, rabbit hole, cover star, glass widgets, pastel word, timeline,
tier list, B-roll split, dot reveal, headline wall, match cut, over-the-shoulder zoom. **Round 4** (built 2026-10-27,
lost in a git stash by the next chat, restored and merged with the Editor's review 2026-10-29, **0.6.0.7**): 20 of
those as templates + `motionlab\screenfx.py` (a `fx` layer: frame, grade, glitch, tunnel, dots, swipe, push) + the
painted rooms; the 14 new effects are Claude's (`edfx.ADD_MORE`: edit lists and a template's `"with"`), not in the
Editor's menu until the user has seen them. The release check: `showcase_a.list` / `showcase_b.list` -> 
`zz_vibha_vertical_v10.mp4` / `_v12.mp4` (10 templates each, every companion landed; shoulder-graphs' template-literal
selectors crashed the bundler - local-make-31) + `_v6` (the 11 effects). Still open from it: pastel word, B-roll
split and split headline not built; a room look (check-pills' grid paper, carousel-spin's spotlight) stays inside one
shot, so it stops at a cut while the graphic goes on; reel-phone-fan's headline sits at face height on an upright
take and the face guard cuts holes in it; the reels-around-you and cover-star templates reach into the apps' right
rail (the precheck's safe-zone lines). **Next**: the user's rating of the demos and the showcases; the Editor's preview
showing behind / glass (it has no mask today); the person track on every second frame if 31 ms a frame is slow on a
laptop (measure first).

**Left from 0.6.0** (released 2026-10-26; each waits on the user or was not needed yet - 0.6.0's text: plans_history.md):
- *Cut the stumbles* (0.6.0 step 20) stays opt-in (`--stumbles on`) until a take with mistakes in it (an "um", a
  restart, a "cut, again") shows what it catches - on by default if it handles it well, removed if not.
- *A finished sound* (22): the user's loudness target (-14 LUFS for every platform, or louder for shorts) and the
  song-under-voice level.
- *The voice cleaned up* (23): the user's A/B listen - `.app\dev\voice_ab\A_as_recorded.m4a` vs `B_cleaned.m4a`;
  B wins = on by default for talking drafts and Claude's talking edits.
- Sound: crackle (Freesound with the user's free key, or sparks from Pixabay), flutter (not rated), a soft sound on
  some of a quick draft's plain cuts (an A/B); the VideoEditingSFX pack's page (the user has no link); music searched
  from the app (Jamendo / Free Music Archive) - the music library reads the user's own downloads for now.
- My Brand: services whose prices are plain text on the website (a Claude read); the quick draft placing a product
  card without Claude. **Held** (the user): 3b's line suggestions from transcripts - only from takes said freely, if
  ever.

**The Editor and My Brand - the user's asks for 0.6.x** (2026-10-26, "as future plans for 0.6.x"; not tied to the
template packs - any 0.6.x can take them; the keyframes, transitions and a clip's opacity are being built now):
1. *Sounds, graphics, effects (and now transitions) with more presence* - "put them in a more respective place
   instead of an overcrowded tab bar": e.g. CapCut's row of big icons (Media / Audio / Text / Effects / Transitions
   ...) as a rail of their own, each opening its panel - not four small tabs over one list.
2. *A layout you change* - "make the preview bigger, move from left to right... like a normal video editor": panels
   resized by dragging their borders (preview / timeline / side panels), the side panels swapped left - right, kept
   per PC.
3. *Blend modes* - "an option to modify opacity for the clip, as well as to add a mode, like screen mode, add colour,
   difference": the clip's opacity comes with the keyframes; modes for clips and graphics (normal, screen, add,
   multiply, overlay, colour, difference ...) need compose's blend() to learn them and the preview's
   mix-blend-mode the same.
4. *Subject masking* (an idea, docs\ideas.md *Later / not now*): "implement corridorkey2.0 to mask subjects ... if u
   specify u want the user masked it can improve edits and have motion graphics from behind". **The light version
   is built** (2026-10-27, 0.6.1 *Graphics part of the shot*: a 250 KB person mask through OpenCV, no CorridorKey);
   left here: the Editor's *Behind me* toggle.
5. *The mood board, its own tab in My Brand* - and pictures / videos added from a link ("so i don have to download
   anything directly"): a post's link (Instagram, TikTok, Pinterest, YouTube) through the download tool, a picture's
   link straight in; the files stay on this PC like the rest of the board.

**Ships when (the template packs half)**: (1) the user's template packs are read with no Claude - every template's moves, eases, timing and
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
honestly could be 100x times better. where could this version fit" - then, to Claude's proposal (this plan, now 0.6.1,
the rest of content generation, now 0.6.3): "yeah go ahead". The plan it grew from (2026-10-14): "i want the generation
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
0.6.3; voice and music since 2026-10-22 in 0.5.4 *Sound*); the clips a script needs -> 0.6.4 (yapping mode's B-roll
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
