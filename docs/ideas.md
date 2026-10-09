# MotionLab - ideas to review later

Tools and features Claude suggested on 2026-10-09 after working through the whole lab, with the user's first
reaction. These are NOT plans: an idea moves to [plans.md](plans.md) only when the user picks it.

**Rule for every idea: light on PCs and laptops, proven first.** Before adopting one, build a small test on a normal
machine (not only the RTX 4070 PC): measure the time, memory and disk it costs and what it improves (accuracy,
minutes saved per video, fewer tokens). Keep it optional or skip it when the gain is small or a laptop struggles.
Prefer CPU-friendly models and options that run only when asked.

## Liked - test first (2026-10-09)

| Idea | Why | Cost to check |
|---|---|---|
| **Automatic tests on GitHub** (GitHub Actions runs the self-tests on every push; a tag per release) | friends update with one click now - a broken push reaches everyone | none on PCs (runs on GitHub); the self-test videos are generated, ~minutes per run - **priority, see plans.md 0.3.1** |
| **Find footage that matches a shot** (image embeddings - CLIP / SigLIP - of every clip, compared with each reference shot) | the slowest manual step of `/recreate-video`; "templates by feel" needs it too | an embedding pass per clip: test a small CPU model vs the GPU, time per minute of footage, and whether its top-3 picks beat Claude reading storyboards |
| **Match the reference's colour grade** (measure its colours / contrast or transfer shot to shot -> a LUT for the lab and Resolve) | rebuilds are in colour since 0.3 but don't copy the look yet | cheap (numpy on a few frames); test how close a LUT gets on real references |
| **Transcription with word timings** (platform subtitles via yt-dlp first; faster-whisper / WhisperX otherwise) | the base of 0.4 content intelligence; also word-by-word captions as HTML overlays | Whisper can be heavy: compare the small / base models on CPU (laptop) vs large on GPU - minutes per minute of audio and errors |

## Later / not now

- **Export to other editors** (OpenTimelineIO / FCPXML for Premiere, Final Cut, free Resolve) - not needed for now.
- **Better camera-motion measurement** (optical flow, e.g. RAFT) - zooms, pans, shakes measured, not guessed; detection
  is the weak spot (40 % right before review). GPU-hungry: test a light variant.
- **Separate music from voice** (Demucs stems) - cleaner beats / drops and cleaner speech for transcripts. Heavy on CPU.
- **A small classifier trained on the verdicts** - once friends have given ~300+ verdicts.
- **Auto-reframe 16:9 -> 9:16** following the subject (MediaPipe / YOLO) - for shorts.
- **Beat-sync auto-cut** - a song + clips cut on the beats with a reference's pacing (a first step to 0.5).
- **On-screen text (OCR)** - text pops of a reference; feeds 0.4.
- **For 0.7**: upscaling (Real-ESRGAN), smooth slow motion (RIFE), voice-over (ElevenLabs / local TTS), music
  generation only with clear licences.
- **Background analyses** with Claude Code headless (`claude -p`) for a 10-video collection - with a per-batch limit,
  since it spends the plan without anyone watching.
- **Report a problem** from the app (a GitHub issue with the log attached).
