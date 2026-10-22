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
- **Export to other editors** (OpenTimelineIO / FCPXML for Premiere, Final Cut, free Resolve) - not needed for now.
- **Better camera-motion measurement** (optical flow, e.g. RAFT) - zooms, pans, shakes measured, not guessed; detection
  is the weak spot (40 % right before review). GPU-hungry: test a light variant.
- **Separate music from voice** (Demucs stems) - cleaner beats / drops and cleaner speech for transcripts. Heavy on CPU.
  -> moved into 0.5.4 *Sound* (step 5, measure first; 2026-10-22).
- **A small classifier trained on the verdicts** - once friends have given ~300+ verdicts.
- **Auto-reframe 16:9 -> 9:16** following the subject (MediaPipe / YOLO) - for shorts.
- **Proposed for content generation** (2026-10-14): voice-over (ElevenLabs / local TTS), music only with clear
  licences -> moved into 0.5.4 *Sound* (steps 3 and 4, 2026-10-22).
- **For 0.7**: upscaling (Real-ESRGAN), smooth slow motion (RIFE).
- **Background analyses** with Claude Code headless (`claude -p`) for a 10-video collection - with a per-batch limit,
  since it spends the plan without anyone watching. -> moved into 0.4.5 (Bulk, step 5, measure first; 2026-10-15).

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
