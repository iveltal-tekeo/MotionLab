# MotionLab - ideas to review later

Tools and features Claude suggested on 2026-10-09 after working through the whole lab, with the user's first
reaction. These are NOT plans: an idea moves to [plans.md](plans.md) only when the user picks it.

**Rule for every idea: light on PCs and laptops, proven first.** Before adopting one, build a small test on a normal
machine (not only the RTX 4070 PC): measure the time, memory and disk it costs and what it improves (accuracy,
minutes saved per video, fewer tokens). Keep it optional or skip it when the gain is small or a laptop struggles.
Prefer CPU-friendly models and options that run only when asked.

## Liked - test first (2026-10-09)

Shipped: **automatic tests on GitHub** (0.3.1, see CHANGELOG.md); **transcription with word timings** (the
platform's subtitles 0.3.1, faster-whisper small chosen after measuring 0.3.3, references without subtitles 0.4.0);
**beat-sync auto-cut** (0.4.0's quick draft: shots cut on the beats at a reference's pacing). Moved into a plan:
**match the reference's colour grade** -> 0.3.7 (2026-10-12; now 0.6.2, its first part shipped in 0.4.0);
**on-screen text (OCR)** -> yapping mode's content foundations, now 0.6.4 (2026-10-14, measure first); **Report a
problem** from the app -> 0.4.2.1 (2026-10-14).

| Idea | Why | Cost to check |
|---|---|---|
| **Find footage that matches a shot** (image embeddings - CLIP / SigLIP - of every clip, compared with each reference shot) | the slowest manual step of `/recreate-video` | an embedding pass per clip: test a small CPU model vs the GPU, time per minute of footage, and whether its top-3 picks beat Claude reading storyboards |

## Later / not now

- **Left from 0.4.6** (2026-10-16): DaVinci Resolve with the shipped fonts (Fusion's text needs them installed in
  Windows; 11 of the 25 families are variable fonts only - measure what Resolve does with them first); a caption look
  the user saves from their own settings (only the shipped looks exist) and more looks from the six mock-ups; caption
  position by platform / off the face; captions "like a reference" (waits for yapping mode's text on screen, 0.6.4).
- **Export to other editors** (OpenTimelineIO / FCPXML for Premiere, Final Cut, free Resolve) -> moved into 0.6.2
  (*Other editors*, 2026-10-25, from a friend's notes).
- **Claude editing live in Premiere, After Effects and Resolve together** (a friend's notes, 2026-10-25) - not now:
  Resolve already gives the edit and the colour, HyperFrames the motion graphics; Premiere's and After Effects'
  scripting needs paid Adobe apps most friends lack, and three live connections triple what can break. The timeline
  file (0.6.2) and After Effects templates as rendered clips (0.6.1 step 4) cover the useful part.
- **Better camera-motion measurement** (optical flow, e.g. RAFT) - zooms, pans, shakes measured, not guessed; detection
  is the weak spot (40 % right before review). GPU-hungry: test a light variant.
- **Separate music from voice** (Demucs stems) - cleaner beats / drops and cleaner speech for transcripts. Heavy on CPU.
  -> moved into 0.5.4 *Sound* (step 5, measure first; 2026-10-22), then into 0.6.5 (*Sound*, 2026-10-25).
- **A small classifier trained on the verdicts** - once friends have given ~300+ verdicts.
- **Subject masking: you cut out of your own footage** (the user, 2026-10-26: "maybe implement corridorkey2.0 to
  mask subjects? ... if u specify u want the user masked it can improve edits and have motion graphics from
  behind") - text and graphics behind the speaker, a background swapped, a glow round them. Checked the same day:
  CorridorKey (Corridor Digital, March 2026, github.com/nikopueringer/CorridorKey; no "2.0" found) is a neural
  *green-screen* keyer (clean alpha + the colour behind the edges, EXR, a Resolve plugin by the community) and wants
  about 24 GB of graphics memory - too heavy for ordinary PCs (*light and tested first*), and the user's talking
  takes have no green screen. For footage without one: a person-matting model - Robust Video Matting, MediaPipe's
  selfie segmentation (CPU, light), SAM 2 (heavier) - measured on a laptop first (seconds per minute of video, edge
  quality on hair); the mask as a clip layer the plan can put a graphic under (compose: a layer's alpha from a mask
  source). CorridorKey stays an option for a friend who films on green and has the GPU (or Beeble's hosted one).
- **Auto-reframe 16:9 -> 9:16** following the subject (MediaPipe / YOLO) - for shorts. -> moved into 0.6.4 (*Shorts
  from a long video*, 2026-10-25).
- **Checked 2026-10-25** (the user: "try the new after effects or free open source programs people have recently
  reversed engineered"; a research pass, sources in the chat; every repo in *GitHub repos checked 2026-10-25* below): *taken into plans* - py-aep (0.6.1 step 2), Three.js
  through HyperFrames' `three` adapter (0.6.1 step 5), Kdenlive through OTIO (0.6.2). *Look again later*: EffectCraft
  (Rust, MIT / Apache, an After Effects-like editor with a command-line render, Lottie and AE-style expressions - but
  three weeks old, alpha, "~45 % production-ready" by its own words: again ~2027-01); Blender Eevee (premium 3D hero
  shots, minutes per second on a laptop); Glaxnimate (cleaning Lottie files by hand); a few hand-picked LottieFiles
  icons (free licence allows commercial use, not resale; stock Lottie looks generic). *No*: Natron (no stable release
  since 2022), Friction and Olive (no command-line render / still alpha), Motion Canvas (quiet since 2024, HyperFrames
  covers it), Remotion (paid for companies over 3 people), Cavalry (its command-line render is Enterprise only).
- **Evals for the lab's own skills** (2026-10-25): Anthropic's `skill-creator` (github.com/anthropics/skills) runs
  test prompts against a skill and compares versions - a way to check that a skill change made /recreate-video or
  /write-script better, not just different.
- **Proposed for content generation** (2026-10-14): voice-over (ElevenLabs / local TTS), music only with clear
  licences -> moved into 0.5.4 *Sound* (steps 3 and 4, 2026-10-22); the voice-over back into 0.6.3 (step 3,
  2026-10-25).
- **For 0.7**: upscaling (Real-ESRGAN), smooth slow motion (RIFE).
- **Background analyses** with Claude Code headless (`claude -p`) for a 10-video collection - with a per-batch limit,
  since it spends the plan without anyone watching. -> moved into 0.4.5 (Bulk, step 5, measure first; 2026-10-15).

## GitHub repos checked 2026-10-25 - for the user's review

Two passes on 2026-10-25: tools that could raise the editing quality (the user: "not just make AI slop while
editing"), then GitHub's weekly / monthly trending and recent video / motion repos (the user: "look for trending
github repositories ... like impeccable or hallmark that improve design"). Read only - nothing installed or run. Stars
and versions as seen that day. *Claude's call*: **test** = a small test now, **plan** = written into a version,
**later** = look again, **ideas** = read it, take the ideas, install nothing, **no** = not for MotionLab. *Your pick*:
mark it.

**Design quality - the "AI look"**

| Repo | What it is | Licence | Use in MotionLab | Claude's call | Your pick |
|---|---|---|---|---|---|
| pbakaus/impeccable (87k stars) | a design skill + 62 automatic checks for AI tells: Inter everywhere, purple-blue gradients, cards in cards, bounce easing, dark glows, grey text on colour | Apache-2.0 | (1) its checker on the app's own pages - **after 0.5.4, the user's yes**; (2) its rules, adapted, in the motion check (0.6.1 step 10) - motion design keeps overshoot | **test** (checker only, telemetry off; the skill's hooks download a program - not installed) | |
| Nutlope/hallmark (33k) | a design skill that "refuses to look AI-generated": Floor / Reflex / Finish checks, 48 "material" themes, a browser lint | MIT | the three check levels for precheck + motion check; its AI tells ("one coloured word in every headline", small-caps labels on everything) checked on our own templates; a *material* (type, colour, surfaces, texture + a finished picture) as the shape of a look (0.6.0 brand kit, 0.6.1 formats) | **ideas** | |
| Vincentwei1021/mg-styles-15 (2.1k) | 15 motion-design styles (Bauhaus, glassmorphism, synthwave, isometric, collage, HUD...) - each a prompt, its code, a 10 s film and a review rubric | MIT (assets CC0 / OFL) | 2-3 styles rebuilt as Generator formats; its rubric in the motion check | **test** | |
| alesha-pro/tools - skills (691) | motion-reel, lyric-music-video, hand-drawn animation skills | MIT at the root (a skill "adapted from" a course) | QA ideas: frames out of order, text at 360 px, frames around fast moves, critique capped 3 x 3; a lyric pilot section first - in 0.6.1 | **ideas** (its installer re-resolves packages - not run) | |

**Motion graphics and 3D**

| Repo | What it is | Licence | Use in MotionLab | Claude's call | Your pick |
|---|---|---|---|---|---|
| forticheprod/py-aep | reads and writes After Effects .aep projects without After Effects (no render, no expressions) | MIT | AE template packs read exactly on any PC (0.6.1 step 2) | **plan** + test on one pack you own | |
| mrdoob/three.js (via HyperFrames' `three` adapter) | 3D in the graphics we already render | MIT | 3D blocks: type, a turning phone / laptop, logo extrusions (0.6.1 step 5) | **plan** + measure on a laptop | |
| heygen-com/hyperframes (72k, #1 this month) | our own graphics engine; its skills folder | Apache-2.0 | stay current through `overlay.py upgrade-test`; read its skills for the blocks | **plan** | |
| storytold/effectcraft (7.9k) | an After Effects-like editor in Rust with a command-line render | MIT / Apache-2.0 | a headless AE alternative - but three weeks old, alpha | **later** (~2027-01) | |
| Blender | Eevee renders, geometry-nodes type | GPL (renders are yours) | premium 3D hero shots - minutes per second on a laptop | **later** | |
| Glaxnimate / LottieFiles / ThorVG | Lottie editing, free Lottie icons, a light Lottie renderer | GPL / Lottie Simple License / MIT | a few hand-picked animated icons for SaaS reels (stock Lottie looks generic) | **later** | |
| Natron, Friction, Olive, Motion Canvas, Remotion, Cavalry | compositors / animation tools | various | no stable release since 2022 / no command-line render / alpha / quiet since 2024 / paid over 3 people / CLI Enterprise only | **no** | |

**Editors, screen recording, voice**

| Repo | What it is | Licence | Use in MotionLab | Claude's call | Your pick |
|---|---|---|---|---|---|
| getopenscreen/openscreen (4.9k) | screen recorder for demos: auto zoom on clicks, smooth cursor, backgrounds; a headless CLI + MCP | MIT | your app tutorials and SaaS demos; MotionLab's own screens as clips (0.6.4 *the clips a script needs*) | **test** | |
| debpalash/VoiceStudio (86k) | a local ElevenLabs alternative: voices, cloning, dubbing; CPU works, slowly | AGPL app; each voice model its own licence | voice-over candidate (0.6.3 step 3) - measured on a laptop, commercial use checked per model, consent only | **plan** (measure) | |
| Kdenlive / MLT via OTIO's Kdenlive adapter | a free editor; the edit as its project | GPL / LGPL / MIT adapter | an editable project for friends without Resolve Studio (0.6.2) | **plan** | |
| jub0t/Concat (11.5k) | a CapCut-like editor an agent can drive (MCP, JSON-RPC) | AGPL, beta | another editable target (0.6.2) once out of beta | **later** | |
| storytold/filmcraft (16k) | a new editor in Rust (EffectCraft's makers) | - | too new | **later** | |

**Shorts, references, skills**

| Repo | What it is | Licence | Use in MotionLab | Claude's call | Your pick |
|---|---|---|---|---|---|
| ClipsAI, OpenShorts, FunClip, AI-Youtube-Shorts-Generator | long video -> shorts | MIT / MIT core / unverified / unverified | how they score moments and reframe - for 0.6.4 step 5, built in the lab (they need torch + a Hugging Face token, or Gemini) | **ideas** | |
| google-ai-edge/mediapipe (BlazeFace) | face detection, ~3 ms a frame | Apache-2.0 | the 16:9 -> 9:16 reframe (0.6.4 step 5) | **plan** | |
| mikf/gallery-dl | downloads Pinterest boards / Instagram posts | GPL-2.0 | mood boards (0.6.0 step 7) - only later and started by you: both sites' terms forbid scraping | **later** | |
| anthropics/skills (`skill-creator`) | runs test prompts against a skill, compares versions | Apache-2.0 | checks that a skill change made the lab better, not just different | **later** | |
| cloudflare/security-audit-skill (46k) | a multi-step security audit skill | - | one audit of the app's local server before more friends use it | **later** | |
| veedstudio/open-edit (1.7k) | VEED's agent editing pipeline (HTML rendered per frame, word timings required) | Apache-2.0 | works the way MotionLab already does - nothing to take | **no** | |
| hypit-ai/hypit (25.6k) | clones viral videos: face / host / script swaps through paid cloud models | "Apache 2.0 with conditions" | no consent safeguards, videos sent to cloud services | **no** | |
| WyattBlue/auto-editor, video-shotcraft (Remotion), anything2explainer, video-talkcraft, onetake | silence cutting, product videos, explainers, one-take films | various / unchecked | the lab cuts pauses already; Remotion's licence; the rest not checked yet | **no** / unchecked | |

## B-roll rules researched 2026-10-27

The user: "the idea of the b roll is to have the sound from the clip before going on, so NOT changing right? maybe we
should look into some claude skills or online or repos where people might have some presets for u that work better
than imagining random stuff?" Read only - nothing installed. No repo has presets in a form the lab could load; what
they share is rules with numbers, and the skills and guides agree on them. Those numbers are now the quick draft's
(`motionlab\draft.py` BROLL_*) and the editing skill's (`recreate-video\by_feel.md`):

1. Picture only: the voice goes on under the insert, never the B-roll clip's own sound, never a cut in the voice.
2. On the word it shows, ~0.25 s after the word starts (0.2-0.5 s, "bias later"), never before it.
3. Or on a jump cut: it hides it (an insert under 0.5 s after a cut starts on the cut - no flash of face).
4. 2-4 s each (~2.5 s typical), never under ~1.5 s (a flicker).
5. The face keeps the hook (~the first 15 %) and the call to action (~the last 10 %).
6. Never under ~2 s of face between two inserts (it reads as a mistake): join them.
7. At most ~40 % of a talking reel covered; an explainer every 8-12 s, a dynamic reel every 4-6 s (the
   talking preset: every ~7 s).
8. The face stays for a punchline and an emotional line.
9. Cut in a word gap, not mid-word; an insert ends at the pause that ends its phrase when one comes in time.
10. Each B-roll moment once; vary shot sizes and places.
11. A concrete word (a thing, a place, an action) earns an insert; an abstract one does not.
12. L / J cuts of ~0.5 s for the clip's own sound only when the user asks for it.
13. A montage of inserts on the beat only where the voice pauses.
14. 3-6 overlays (text, graphics) a minute on top of the inserts, not instead of them.
15. A clip that is loud all through (music, ambience) beside a real take is B-roll, not talking (the lab's measure:
    a take is quiet between phrases in 30-49 % of its 10 ms windows, music or ambience in 0-9 %).

| Source | What it is | Licence | Taken | Claude's call |
|---|---|---|---|---|
| louisedesadeleer/b-roll-finder | a skill that places B-roll from a transcript | MIT | the +0.2-0.5 s anchor after the word, 2-4 s, concrete words | **ideas** (done) |
| gamussa/reels-producer-skill | a reels editing skill | not checked | hook / CTA on the face, density | **ideas** (done) |
| opus-pro/ai-producer-plugin | OpusClip's agent plugin | MIT | coverage by genre, B-roll pacing | **ideas** (done) |
| browser-use/video-use | an agent video editor | MIT | cuts in word gaps | **ideas** (done) |
| iart-ai/motion-design-skills | motion-design skills | MIT | overlays a minute | **ideas** (done) |
| OpenMontage | an AI montage tool | AGPL | the montage-on-beat rule only (no code) | **ideas** |
| OpusClip / Submagic docs | their B-roll features' help pages | - | the 15 % / 10 % face shares, no slivers | **ideas** (done) |

## Shorts from a long video - researched 2026-10-27

For 0.6.1's *Shorts from a long video* (the plan has the pipeline, the rubric and the numbers). Read only - nothing
installed or run. (s) = seen in search results only.

| Source | Licence / needs | How it picks | Taken (ideas only) |
|---|---|---|---|
| OpusClip (help: *virality score*; its API blog) | paid | 0-99 from hook, flow, value, trend; inputs: transcript, audio (pace, pitch, laughter, pauses), gestures; best on talking heads, low on music / animation | the four parts (trend -> fits My Brand), a cold-open hook |
| Vizard, Klap, Submagic | paid | 0-100, method not published; quotable lines, reveals, emotion, debates, laughs | the kinds of moment |
| Descript, Riverside Magic Clips | paid | "self-contained" moments, 1-20 clips, a topic / speaker focus | a user prompt or speaker focus |
| ClipsAI | MIT; WhisperX + pyannote (Hugging Face token) | no ranking: TextTiling on sentence embeddings at several sizes, near-duplicates dropped | topic edges at several scales |
| OpenShorts | MIT core; Gemini key | faster-whisper + PySceneDetect, Gemini picks 3-15 moments of 15-60 s, 3-8 windows a call; layouts TRACK / blurred / SPLIT / SCREENCAST | scoring in batches, the four layouts |
| SamurAIGPT AI-Youtube-Shorts-Generator | MIT; OpenAI / Gemini key | a ranked rubric (hook, emotional peak, opinion, revelation, conflict, quotable line, story peak, practical value), asks for 2x the clips, drops overlaps > 50 % | ask for 2x, then drop overlaps |
| SupoClip | AGPL-3.0 (ideas only, no code) | hook, engagement, value, shareability 0-25 each + a 0-1 "stands alone" | the stands-alone gate, start / end rules |
| opensource-clipping | MIT; Gemini | BlazeFace tracking with a dead zone and anti-jitter, split screen for two | dead-zone tracking |
| browser-use/video-use (a Claude skill) | MIT; ElevenLabs | ~12 KB of transcript, pictures only where a decision needs them; never cut inside a word, pad 30-200 ms, a 400 ms+ pause = a clean cut | text first, pictures on demand |
| Google AutoFlip | Apache-2.0 | per scene: a still crop when the subject stays put, else a smoothed follow; padding when it cannot fit | the reframe's design |
| Rhapsody (2025 paper, 13k podcasts labelled by *Most replayed*) | research | GPT-4o / Gemini untrained F1 0.057 / 0.065; a fine-tuned 1B model 0.163, 0.197 with audio | scores = a ranking within one video, learn from results |
| SnapUGC (2025 short-video engagement challenge) | research | watching past 5 s correlates 0.928 with average watch percentage; 8 frames a clip slightly better than 5 | the hook weighs double; 8-frame check sheets |

Not verified (marketing numbers, left out): "63-71 % decide in 3 s", "+23 % for hooks", "loop endings boost reach",
"sends weigh 3-5x likes", every *best length*. YouTube Shorts allow up to 3 minutes (YouTube's help); Reels 3 minutes
(s).

## Vertical framing - researched 2026-10-29

For 0.6.1's *Vertical framing for every edit* (the plan has the steps). The user: "encuadre para redes (en
vertical)". Read only - nothing installed. (v) = Claude read the source itself on 2026-10-29, (r) = read by the
research pass, (s) = search results only.

| Source | Licence / cost | What it does | Taken (ideas only) |
|---|---|---|---|
| Google AutoFlip (research blog; cropping.proto, scene_cropping_calculator.proto) (r) | Apache-2.0; legacy since 2023-03-01, OpenCV 3 only | decides per scene with the whole scene buffered; still crop when the subject moves less than a share of the SOURCE width (0.3-0.5), else a smoothed follow; letterbox when the required content cannot fit - a solid colour when >= 60 % of the frames have a plain background, else a blurred frame (blur 200, black 0.6 over it); detects at 480 px wide, 5 fps; weights face 0.8-0.9, person 0.75-0.8, object 0.1-0.2 | the design, not the code; the hold test made relative to the CROP (8 % margin in 95 % of frames - the source-width rule is too loose for a 608 px crop) |
| OpusClip layouts help + its *reframe benchmark* (2026-09, vendor-run) (r) | paid | Fill (9:16 on the speaker), Fit (the source cropped to 4:3, padded), Split / Three / Four (only when they share the frame), Screenshare (screen top, speaker bottom), Gameplay (face 30 %, game 70 %); failures named: crop on the listener, past the chart, one crop while the layout changes, a sliced chyron | the five layouts, the failure list as tests |
| Vizard stacking guide (2026-10-10) (r) | paid | never 50/50 (a half-frame head loses its top); band heights measured; captions in the gap; at most two panels; a dense screen as a cutaway | the split's rules |
| AutoCut (r), Descript multicam feedback (r) | paid | a 2-3 s minimum shot, a wide shot after ~10 s; users report split-second cuts on "yes / mm-hmm" | hold >= 2 s, turns under 1 s ignored, a variant after ~10 s |
| ClipsAI resizer.py (r) | MIT (pyannote + MTCNN) | merges moves under 4 % of the width; the talker = the face whose mouth opens most | skip small moves; the mouth signal |
| Grundmann et al., L1 optimal camera paths (r) | research | a path of constant / linear / parabolic pieces | holds, constant pans and eases - never a wobble |
| Light-ASD (CVPR 2023) (v licence) | MIT, 1.0 M parameters, needs PyTorch, GPU timings only | active speaker detection: 112x112 face crops + MFCC; cross-domain F1 81.1 vs TalkNet 56.2 | only if the mouth-vs-sound signal fails, measured first |
| Silero VAD (v licence) | MIT, ~2 MB, < 1 ms a 30 ms chunk on one thread | speech segments | only if the words' timings are not enough |
| TalkNet (r) MIT, CUDA by default; LoCoNet (r) no licence file | - | speaker detection | not used |
| Blitzcut, LSU / Maryland filming guides, Reap safe zones (2026-09) (r) | - | eyes on the upper third (~y 640 on 1920), mid-chest up, captions ~y 1200-1550 and never over the mouth; YouTube Shorts' interface changed in June 2026; Meta's ads zone keeps the bottom 35 % clear (stricter than our y 1480) | the Film it checklist; an *ads* safe-zone preset (option) |

Numbers that are Claude's or the research pass's own starting values, to measure (not sourced): pans capped at ~0.5
crop widths a second, eases >= 12 frames, a total upscale cap of ~2.0-2.2x (a 1080p source in a 1080 x 1920 crop
is already 1.78x - arithmetic), snap to the centre only within ~3 % of the crop. Not verified: AutoFlip's or
Light-ASD's CPU speed, CapCut's reframe settings, an official TikTok safe zone.

## Editing by segments - researched 2026-10-29

For 0.6.1's *Edit by segments* (the plan has the steps). The user: "editar por segmentos" and "borrador (quick
draft) select each segment how u would like it edited and then create the edit entirely". Read only. Marks as above.

| Source | What it shows | Taken (ideas only) |
|---|---|---|
| Descript help (scenes, layout packs, properties) + its feedback board (r) | a scene per idea (`/` in the script), one layout pack = the global style, layouts by role (talking head, screen, graphics) filled from the script, a user's edited layers kept when the layout changes; the most-asked missing piece: apply to many scenes at once ("200 scenes in a 9-minute video... a nightmare", 2023-2025) | the three layers (style, rules, overrides), *Apply to all like this* |
| Captions AI Edit (r) | one style for the whole video, then re-run one take in another style with *Keep existing images* | picks kept through a re-run |
| OpusClip, Pictory, VEED, Submagic (r) | a layout per segment; a scene per sentence with *Apply to all scenes*; regenerate / replace each B-roll; zoom styles on the transcript | per-card choices, few options |
| B-Script (CHI 2019) (v) | 115 expert edits of 3-minute talking vlogs: 13.2 % of the video replaced by B-roll on average; for 73 % of inserts the query word is within 1 s of the start; words predict placement better than pauses, sentence ends or blinks | B-roll on its word (we do +0.25 s); measure our own coverage (BROLL_COVER 0.40 is a ceiling) |
| LAVE (IUI 2024), ExpressEdit (IUI 2024) (r) | clips described as text for the model; users want the final say; plausible but wrong rationales; vague commands misread; 46 % of suggestions accepted, 58 % adjusted | a recommendation + alternatives, the user decides; the reason shown in one line |
| VideoDiff (CHI 2025) (r) | alternatives aligned on shared sections with a short description of each change: 38 s vs 74 s to compare, satisfaction 5.25 vs 3.67; 10 options overwhelmed some; it claimed cuts it had not made | 2-3 alternatives, a line per change, a check that every claimed change is in the plan |
| browser-use/video-use (r) | MIT; a ~12 KB phrase-level transcript, filmstrips only at decision points, every cut boundary checked after the render | text first, pictures on demand, the boundary check |
| BertSeg / TextTiling, librosa segmentation, Chapter-Llama (r, some abstracts only) | topic edges from sentence embeddings; music sections; chapters from the words | segments per kind (the plan's table) |

Not verified: Premiere's text-based editing (403), CapCut "smart segments" (no such feature found), Riverside /
Firefly per-segment features, GPT-4o vs TextTiling on lectures.

## SPARK (why a video worked) - researched 2026-10-29

For 0.6.5's *SPARK* (the plan has the steps). Evidence grades: [R] peer-reviewed or a registered trial, [P] a
platform's own statement, [C] a creator's claim. Marks as above.

- **What holds up** [R]: negative words raised headline clicks in the Upworthy trials (Robertson et al. 2023); arousing
  emotions were shared more in field data (Berger & Milkman 2012) but two 2024 replications of the experiment failed
  (Psychological Science) - moderate; moral-emotional words raise sharing ~12 % a word (2025 pooled replication);
  shared to one person = chosen to be useful, broadcast = chosen to make the sharer look good (Berger's review);
  controversy raises discussion up to a moderate level, then lowers it (Chen & Berger 2013); social influence makes
  success partly unpredictable (Salganik et al. 2006); the best cascade models explain under half the variance. A small
  2026 study (one 20 s talking clip, 7 versions, N = 242) found faster pacing LOWERED completion - never score "more
  cuts = better".
- **What the platforms say** [P]: TikTok: over 63 % of its highest-CTR ads state the key message in 3 s (winners only);
  YouTube: high CTR with low view duration reads as clickbait; YouTube counts "valued watch time" (rated 4-5 stars);
  YouTube's Most replayed is normalised within the video and a spike can mean rewatching, sharing or confusion.
- **Creators** [C]: Paddy Galloway (an outlier = 3-4x the channel's average; "the idea itself, the title or the
  thumbnail"; check whether similar videos flopped); the MrBeast production doc (not authenticated); Kallaway's hook
  steps; Jenny Hoyos (clear on mute, "but / so" between beats).
- **Data rules** (v, YouTube API developer policies, read 2026-10-29): III.E.6 no scraping; III.E.4.b statistics not
  authorised by their owner kept 30 days at most; III.E.4.h no "new or derived data or metrics" from API data, the
  exception being audited developers who asked for it (III.L). **Views** (v, YouTube help): since 2026-08-24 a view
  counts the moment a video starts to play, in every format, ad views included - compare a video only with the same
  creator's videos of the same era. Instagram: shares, saves, watch time only in the owner's Insights; Business
  Discovery gives likes, comments and views of other professional accounts (r). TikTok's Research API is for
  non-profit academics in the US / EU (r).
- **Tools** (r): 1of10, Viewstats, vidIQ, OutlierKit, Virlo, Sandcastles, Spotter, OpusClip's score - fast outlier
  finding against a channel baseline; formulas unpublished or inconsistent (mean vs median, subscribers vs uploads);
  none validates its "why". A builder of a "why it went viral" tool: free-form answers could not be compared across
  videos, a fixed taxonomy was his biggest gain (dev.to, 2025).
- **Repos** (r): pandich93/youtube-niche-finder (MIT, median multiplier, breakouts vs ordinary), shkuratovdesigner/
  yuben-app (MIT, likes per 1,000 views to spot bought views), ScrapeCreators/social-media-research-skills (MIT, needs
  their paid key), egbertbouman/youtube-comment-downloader + BERTopic (MIT, comment clusters), pelpeljakob-creator/
  viral-video-analyzer (no licence on GitHub, unvalidated hook score); the Upworthy Research Archive (32,487 headline
  tests).

## Claude's guides, skills and repos - checked 2026-10-29 (for the user's pick)

The user: "see what else could we improve based on claude style and guide on generating content, search online,
public courses, github repos, instagram". No official Anthropic guide to video scripts was found; Anthropic's useful
material is general (skills, evals, prompting, vision); no Instagram source could be verified. Ranked by what it would
improve now; none is planned yet. Checked in the lab's code by Claude: HyperFrames pinned to 0.8.149
(`tools\overlays\package.json`), `overlay.py check` runs with `--no-contrast`, the MCP `frames()` reads 640 px wide,
`.claude\settings.json` has no deny rules.

1. **HyperFrames' newer craft checks and review sheets** (M; v) -> picked for 0.6.1 (2026-10-29): `check` names a line on screen too briefly to read
   (`line_unread`), over 3 s with nothing changing (`dead_stretch`), text under 2.6 % of the short side, an empty first
   frame, a film over 15 s with no sound; `snapshot --review` sheets (scene starts / middles, a strip across every cut,
   the beats at phone width); review notes as `t=4.2s · where · problem -> exact change · what stays`, P0 / P1 / P2,
   "never score the film out of 10", "a busy film: remove a third of the motion". An upgrade from 0.8.149 through
   `overlay.py upgrade-test` + the self-test; the contrast audit turned back on.
2. **A divergent concept step before a Generate plan** (S; r): five ideas, three shown, one the bold one Claude would
   not pick first; no two with the same layout - against the *template variety* problem (Anthropic's Opus 5.5 guide:
   name the exact patterns to avoid and grow the list after each result).
3. **A slideshow-risk score on a plan before building** (M; r, OpenMontage - AGPL, the idea only): repetition,
   decorative visuals, weak motion, weak shot intent, text overuse, unsupported claims, 0-5 each; a critical finding
   needs a concrete fix.
4. **A zoom / crop on the MCP picture tools** (S; r, Anthropic's crop-tool recipe): `frames()` with a region read at
   full size - flashes, grain, glow, small text; each zoom costs tokens.
5. **A waveform and the words on the cut-sheet** (S-M; r, video-use's timeline view) -> picked for 0.6.1 (2026-10-29): a cut inside a word or an audio
   pop shows; every cut boundary checked after the render.
6. **Skill evals from the user's own verdicts** (M; r, Anthropic's agent-evals article, 2026-01): 20-50 tasks from
   real failures, code graders first; verdicts.json / outcome.json are the labels (with *Evals for the lab's own
   skills* under *Later*).
7. **Hard rule 1 enforced by Claude Code itself** (S; r, Claude Code best practices) -> picked for 0.6.1 (2026-10-29): deny rules for writing into
   `refs\` and a hook that blocks deleting or moving in source folders - they hold in every permission mode; the
   tools' SHA-256 check stays. A change to `.claude\settings.json` - the user's call.
8. **Skills carry their own effort / model** (S; r): a typed `/recreate-video` gets the effort the app picks.
9. **Untrusted text tagged** (S; r, Opus 5.5 guide): friends' lessons, downloaded subtitles, website text and pasted
   prompts handed to Claude inside `<pasted_content>` tags.
10. **A ban list for scripts and titles** (S; r, Fable 5.1 guide's "mannered prose" instruction + named AI-sounding
    patterns, English and Spanish) in `/write-script` and `/write-title`.
11. **Lesson hygiene** (S; second-hand): an exception never becomes a default - a lesson tagged to its kind, or seen
    twice, before it is global.

Don't copy: hosted clipping services and cloud editors (privacy), transcript-only editing that never looks at the
picture, Anthropic's "unattended" prompt (MotionLab keeps the user in the loop), parallel fan-out for quality
("parallelism multiplies incorrect cuts"), one-shot single-HTML screen recordings (not frame-accurate), scores shown as
promises, code under AGPL (OpenMontage) or without a licence (remotion-dev/skills per the GitHub API). Risk to know:
the DaVinci Resolve MCP's README says Resolve 21.1 moved Python scripting to Studio; whether the free edition's bridge
still works on 21.1 is unconfirmed (friends on free Resolve).

## Prompt library - still open (the 0.5.4 *Prompt generator* plan, removed 2026-10-22)

Its core shipped in 0.3.1-0.3.4: the library (*Generator > Prompts*), `/write-prompt`, each prompt's check,
*Optimize*, variants built on the best-rated ones. The user (2026-10-22): "Remove 0.5.4 prompt generator? i think we
alreadyy have that in the prepare video? or is prepare video only for transcripts and prompts is related to AI?" -
Prepare is the words said on camera and the title / thumbnail; the library holds prompts for AI tools (video and
image models, briefs for Claude). What the plan still had open:

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
  structure a script example (yapping mode, 0.6.4; take notes from videos, 0.6.5, adds more), with the link and frame
  + timecode.
- **Sharing** your own prompts and ratings through *Claude's memory > Share* (text); creators' prompts stay on the PC.
- **A structure per purpose** (2026-10-12: "a vlog prompt differs from a talking head, SFX, transitions..."):
  0.3.3 gave prompts their purposes (tags) and videos a "how did it turn out?" per part (`build\outcome.json`,
  shown on the prompt as "Used in"); learn from those answers which structure works per purpose - needs a few
  made videos rated first.
- **Style from analysed references** (built 2026-10-13, after 0.3.4: "the optimized prompt asks for a link to a
  Clavero vlog - what if I analysed one already?"): *Style like* on brief / script / hook cards links analysed
  references; their measured pacing / effects / BPM go into Claude's check, Optimize and Create video. Next: the
  look measured too (colour, 0.6.2), and several references of one creator averaged into one style.

## Used and not used - to look at again (checked 2026-11-10)

The user, 2026-11-10: "lets check for things we use/we dont use ... clean up features not used and then we go and
improve the current ones" - then, asked which to hide: **"nothing for now lets just put a check on it and later i
will look into it"**. So nothing was hidden or removed; this is the check. What each feature had produced on the
user's PC that day (counts only; what friends use is not known):

| Feature | On this PC | Last used |
|---|---|---|
| Notes (INDEX) | 43 videos | 2026-11-10 |
| Editor: drafts, builds, graphics, sound | 18 videos, 121 plans, 83 renders | 2026-11-05 |
| Downloads | 58 | 2026-11-10 |
| SPARK | 5 | 2026-11-03 |
| My Brand | filled in, 4 website imports | 2026-11-03 |
| Effects analysis (FLUX) | 8 videos; verdicts on 2 of them (74) | 2026-10-26 (verdicts 2026-10-15) |
| Editor timeline saves / Edit by segments / shot list | 11 saves in 4 videos / 2 videos / 3 videos | 2026-10-26 to 2026-11-04 |
| Prepare (scripts, titles) / prompt library | 10 requests / 49 prompts, none rated | 2026-10-27 |
| Thumbnail sets | 1 | 2026-10-15 |
| Content agency: calendar, Your videos | both empty | never |
| Content agency: stats, where people left, tests, what works, monthly | no data files | never |
| Ready to post + a video's thumbnails | 0 | never |
| DaVinci Resolve builds, saved library effects | 0 in the current videos | never (here) |
| Scripts & prompts sets | 0 | never |
| Sharing | "we dont actually use it" (the user) | on hold |

How much sits behind each never-used one, and what leans on it (measured the same day):

- **DaVinci Resolve side** - about 4,750 lines (resolve_build.py, library.py, fusion.py, resolve_mcp.py, its test);
  three other Python files lean on it (overlay.py's refresh / resolve-clip, editreq, overlay_settings), but its
  words are in seven page scripts. The biggest clean removal - if a lab render is the final video now.
- **Content agency** - about 3,600 lines + the page. SPARK reads `social` and `retention`, so only *tests*, *what
  works* and the *monthly review* (about 1,900 lines, built 2026-11-02, never tried) come out cleanly.
- **Scripts & prompts sets** - about 1,600 lines; data.py, knowledge.py and prompts.py lean on it.
- **Thumbnail sets + Preview your thumbnail** - about 2,200 lines; moodboard.py and thumbnail.py lean on it.
- **Ready to post + thumbnails** - `thumbnail.py` is a shared helper of 14 modules and build.py / draft_edit.py use
  `publish.py`: hide only, never remove.
- **Sharing** - woven into knowledge.py and the server: hide only (the cards themselves are Claude's memory).

The way to do it when the user picks: hide first (off the sidebar and its buttons for one version, the code stays),
then remove what nobody missed - one feature per commit (its page script, routes and jobs, module and tool, Spanish
texts, docs section, skill, self-check), each with the full gate. Never-used is not not-wanted: the Content agency
parts were eight days old on the day of the check.
