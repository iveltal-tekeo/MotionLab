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
**match the reference's colour grade** -> 0.3.7 (2026-10-12; now 0.5.7, its first part shipped in 0.4.0);
**on-screen text (OCR)** -> yapping mode's content foundations, now 0.5.9 (2026-10-14, measure first); **Report a
problem** from the app -> 0.4.2.1 (2026-10-14).

| Idea | Why | Cost to check |
|---|---|---|
| **Find footage that matches a shot** (image embeddings - CLIP / SigLIP - of every clip, compared with each reference shot) | the slowest manual step of `/recreate-video` | an embedding pass per clip: test a small CPU model vs the GPU, time per minute of footage, and whether its top-3 picks beat Claude reading storyboards |

## Later / not now

- **Left from 0.4.6** (2026-10-16): DaVinci Resolve with the shipped fonts (Fusion's text needs them installed in
  Windows; 11 of the 25 families are variable fonts only - measure what Resolve does with them first); a caption look
  the user saves from their own settings (only the shipped looks exist) and more looks from the six mock-ups; caption
  position by platform / off the face; captions "like a reference" (waits for yapping mode's text on screen, 0.5.9).
- **Export to other editors** (OpenTimelineIO / FCPXML for Premiere, Final Cut, free Resolve) -> moved into 0.5.7
  (*Other editors*, 2026-10-25, from a friend's notes).
- **Claude editing live in Premiere, After Effects and Resolve together** (a friend's notes, 2026-10-25) - not now:
  Resolve already gives the edit and the colour, HyperFrames the motion graphics; Premiere's and After Effects'
  scripting needs paid Adobe apps most friends lack, and three live connections triple what can break. The timeline
  file (0.5.7) and After Effects templates as rendered clips (0.5.6 step 4) cover the useful part.
- **Better camera-motion measurement** (optical flow, e.g. RAFT) - zooms, pans, shakes measured, not guessed; detection
  is the weak spot (40 % right before review). GPU-hungry: test a light variant.
- **Separate music from voice** (Demucs stems) - cleaner beats / drops and cleaner speech for transcripts. Heavy on CPU.
  -> moved into 0.5.4 *Sound* (step 5, measure first; 2026-10-22).
- **A small classifier trained on the verdicts** - once friends have given ~300+ verdicts.
- **Auto-reframe 16:9 -> 9:16** following the subject (MediaPipe / YOLO) - for shorts. -> moved into 0.5.9 (*Shorts
  from a long video*, 2026-10-25).
- **Checked 2026-10-25** (the user: "try the new after effects or free open source programs people have recently
  reversed engineered"; a research pass, sources in the chat; every repo in *GitHub repos checked 2026-10-25* below): *taken into plans* - py-aep (0.5.6 step 2), Three.js
  through HyperFrames' `three` adapter (0.5.6 step 5), Kdenlive through OTIO (0.5.7). *Look again later*: EffectCraft
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
  licences -> moved into 0.5.4 *Sound* (steps 3 and 4, 2026-10-22).
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
| pbakaus/impeccable (87k stars) | a design skill + 62 automatic checks for AI tells: Inter everywhere, purple-blue gradients, cards in cards, bounce easing, dark glows, grey text on colour | Apache-2.0 | (1) its checker on the app's own pages - **after 0.5.4, the user's yes**; (2) its rules, adapted, in the motion check (0.5.6 step 10) - motion design keeps overshoot | **test** (checker only, telemetry off; the skill's hooks download a program - not installed) | |
| Nutlope/hallmark (33k) | a design skill that "refuses to look AI-generated": Floor / Reflex / Finish checks, 48 "material" themes, a browser lint | MIT | the three check levels for precheck + motion check; its AI tells ("one coloured word in every headline", small-caps labels on everything) checked on our own templates; a *material* (type, colour, surfaces, texture + a finished picture) as the shape of a look (0.5.5 brand kit, 0.5.6 formats) | **ideas** | |
| Vincentwei1021/mg-styles-15 (2.1k) | 15 motion-design styles (Bauhaus, glassmorphism, synthwave, isometric, collage, HUD...) - each a prompt, its code, a 10 s film and a review rubric | MIT (assets CC0 / OFL) | 2-3 styles rebuilt as Generator formats; its rubric in the motion check | **test** | |
| alesha-pro/tools - skills (691) | motion-reel, lyric-music-video, hand-drawn animation skills | MIT at the root (a skill "adapted from" a course) | QA ideas: frames out of order, text at 360 px, frames around fast moves, critique capped 3 x 3; a lyric pilot section first - in 0.5.6 | **ideas** (its installer re-resolves packages - not run) | |

**Motion graphics and 3D**

| Repo | What it is | Licence | Use in MotionLab | Claude's call | Your pick |
|---|---|---|---|---|---|
| forticheprod/py-aep | reads and writes After Effects .aep projects without After Effects (no render, no expressions) | MIT | AE template packs read exactly on any PC (0.5.6 step 2) | **plan** + test on one pack you own | |
| mrdoob/three.js (via HyperFrames' `three` adapter) | 3D in the graphics we already render | MIT | 3D blocks: type, a turning phone / laptop, logo extrusions (0.5.6 step 5) | **plan** + measure on a laptop | |
| heygen-com/hyperframes (72k, #1 this month) | our own graphics engine; its skills folder | Apache-2.0 | stay current through `overlay.py upgrade-test`; read its skills for the blocks | **plan** | |
| storytold/effectcraft (7.9k) | an After Effects-like editor in Rust with a command-line render | MIT / Apache-2.0 | a headless AE alternative - but three weeks old, alpha | **later** (~2027-01) | |
| Blender | Eevee renders, geometry-nodes type | GPL (renders are yours) | premium 3D hero shots - minutes per second on a laptop | **later** | |
| Glaxnimate / LottieFiles / ThorVG | Lottie editing, free Lottie icons, a light Lottie renderer | GPL / Lottie Simple License / MIT | a few hand-picked animated icons for SaaS reels (stock Lottie looks generic) | **later** | |
| Natron, Friction, Olive, Motion Canvas, Remotion, Cavalry | compositors / animation tools | various | no stable release since 2022 / no command-line render / alpha / quiet since 2024 / paid over 3 people / CLI Enterprise only | **no** | |

**Editors, screen recording, voice**

| Repo | What it is | Licence | Use in MotionLab | Claude's call | Your pick |
|---|---|---|---|---|---|
| getopenscreen/openscreen (4.9k) | screen recorder for demos: auto zoom on clicks, smooth cursor, backgrounds; a headless CLI + MCP | MIT | your app tutorials and SaaS demos; MotionLab's own screens as clips (0.5.9 *the clips a script needs*) | **test** | |
| debpalash/VoiceStudio (86k) | a local ElevenLabs alternative: voices, cloning, dubbing; CPU works, slowly | AGPL app; each voice model its own licence | voice-over candidate (0.5.4 step 4) - measured on a laptop, commercial use checked per model, consent only | **plan** (measure) | |
| Kdenlive / MLT via OTIO's Kdenlive adapter | a free editor; the edit as its project | GPL / LGPL / MIT adapter | an editable project for friends without Resolve Studio (0.5.7) | **plan** | |
| jub0t/Concat (11.5k) | a CapCut-like editor an agent can drive (MCP, JSON-RPC) | AGPL, beta | another editable target (0.5.7) once out of beta | **later** | |
| storytold/filmcraft (16k) | a new editor in Rust (EffectCraft's makers) | - | too new | **later** | |

**Shorts, references, skills**

| Repo | What it is | Licence | Use in MotionLab | Claude's call | Your pick |
|---|---|---|---|---|---|
| ClipsAI, OpenShorts, FunClip, AI-Youtube-Shorts-Generator | long video -> shorts | MIT / MIT core / unverified / unverified | how they score moments and reframe - for 0.5.9 step 5, built in the lab (they need torch + a Hugging Face token, or Gemini) | **ideas** | |
| google-ai-edge/mediapipe (BlazeFace) | face detection, ~3 ms a frame | Apache-2.0 | the 16:9 -> 9:16 reframe (0.5.9 step 5) | **plan** | |
| mikf/gallery-dl | downloads Pinterest boards / Instagram posts | GPL-2.0 | mood boards (0.5.5 step 7) - only later and started by you: both sites' terms forbid scraping | **later** | |
| anthropics/skills (`skill-creator`) | runs test prompts against a skill, compares versions | Apache-2.0 | checks that a skill change made the lab better, not just different | **later** | |
| cloudflare/security-audit-skill (46k) | a multi-step security audit skill | - | one audit of the app's local server before more friends use it | **later** | |
| veedstudio/open-edit (1.7k) | VEED's agent editing pipeline (HTML rendered per frame, word timings required) | Apache-2.0 | works the way MotionLab already does - nothing to take | **no** | |
| hypit-ai/hypit (25.6k) | clones viral videos: face / host / script swaps through paid cloud models | "Apache 2.0 with conditions" | no consent safeguards, videos sent to cloud services | **no** | |
| WyattBlue/auto-editor, video-shotcraft (Remotion), anything2explainer, video-talkcraft, onetake | silence cutting, product videos, explainers, one-take films | various / unchecked | the lab cuts pauses already; Remotion's licence; the rest not checked yet | **no** / unchecked | |

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
  structure a script example (yapping mode, 0.5.9; take notes from videos, 0.6.0, adds more), with the link and frame
  + timecode.
- **Sharing** your own prompts and ratings through *Claude's memory > Share* (text); creators' prompts stay on the PC.
- **A structure per purpose** (2026-10-12: "a vlog prompt differs from a talking head, SFX, transitions..."):
  0.3.3 gave prompts their purposes (tags) and videos a "how did it turn out?" per part (`build\outcome.json`,
  shown on the prompt as "Used in"); learn from those answers which structure works per purpose - needs a few
  made videos rated first.
- **Style from analysed references** (built 2026-10-13, after 0.3.4: "the optimized prompt asks for a link to a
  Clavero vlog - what if I analysed one already?"): *Style like* on brief / script / hook cards links analysed
  references; their measured pacing / effects / BPM go into Claude's check, Optimize and Create video. Next: the
  look measured too (colour, 0.5.7), and several references of one creator averaged into one style.
