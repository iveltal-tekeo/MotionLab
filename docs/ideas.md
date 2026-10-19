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
**match the reference's colour grade** -> 0.3.7 (2026-10-12; now 0.5.6, its first part shipped in 0.4.0);
**on-screen text (OCR)** -> yapping mode's content foundations, now 0.5.2 (2026-10-14, measure first); **Report a
problem** from the app -> 0.4.2.1 (2026-10-14).

| Idea | Why | Cost to check |
|---|---|---|
| **Find footage that matches a shot** (image embeddings - CLIP / SigLIP - of every clip, compared with each reference shot) | the slowest manual step of `/recreate-video`; "templates by feel" (0.6.5) needs it too | an embedding pass per clip: test a small CPU model vs the GPU, time per minute of footage, and whether its top-3 picks beat Claude reading storyboards |

## Later / not now

- **Left from 0.4.6** (2026-10-16): DaVinci Resolve with the shipped fonts (Fusion's text needs them installed in
  Windows; 11 of the 25 families are variable fonts only - measure what Resolve does with them first); a caption look
  the user saves from their own settings (only the shipped looks exist) and more looks from the six mock-ups; caption
  position by platform / off the face; captions "like a reference" (waits for 0.5.2's text on screen).
- **Export to other editors** (OpenTimelineIO / FCPXML for Premiere, Final Cut, free Resolve) - not needed for now.
- **Better camera-motion measurement** (optical flow, e.g. RAFT) - zooms, pans, shakes measured, not guessed; detection
  is the weak spot (40 % right before review). GPU-hungry: test a light variant.
- **Separate music from voice** (Demucs stems) - cleaner beats / drops and cleaner speech for transcripts. Heavy on CPU.
- **A small classifier trained on the verdicts** - once friends have given ~300+ verdicts.
- **Auto-reframe 16:9 -> 9:16** following the subject (MediaPipe / YOLO) - for shorts.
- **Proposed for content generation** (2026-10-14; now 0.5.7, its step 1 - measure first; the user confirms):
  voice-over (ElevenLabs / local TTS), music only with clear licences.
- **For 0.7**: upscaling (Real-ESRGAN), smooth slow motion (RIFE).
- **Background analyses** with Claude Code headless (`claude -p`) for a 10-video collection - with a per-batch limit,
  since it spends the plan without anyone watching. -> moved into 0.4.5 (Bulk, step 5, measure first; 2026-10-15).
