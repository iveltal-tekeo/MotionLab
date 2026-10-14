# MotionLab - how the plans got their numbers

The history behind [plans.md](plans.md): renumbers, where each plan came from, and measurements that are finished.
plans.md keeps only what is planned now. Older notes, chats and code comments use the old numbers: look them up in
the table below.

## Which plan an old number means

| Plan (number now) | Earlier numbers |
|---|---|
| Each section its own feel (0.4.1.1) | none (added 2026-10-14) |
| Check before you render (0.4.2) | 0.4.6 (2026-10-14) |
| Downloads that keep working + Report a problem (0.4.2.1) | none (added 2026-10-14 evening; its download items were "carried over from 0.3.3" inside describe video, *Report a problem* was in ideas.md) |
| Title + thumbnail (0.4.3) | 0.4.2 (2026-10-14) |
| Prompt generator (0.4.4) | 0.4.1 (until 2026-10-13), 0.4.5 (2026-10-13), 0.4.3 (2026-10-14) |
| Yapping mode (0.4.5) | 0.4.0 (until 2026-10-13), 0.4.4 (2026-10-13 to 2026-10-14) |
| Colour (0.4.6) | 0.3.7 (2026-10-12), 0.4.3 (2026-10-13), 0.4.5 (2026-10-14) |
| Content generation (0.5.0) | none (2026-10-14); "0.5" before that meant templates by feel + macOS |
| Templates by feel (0.6.5) | 0.5 (with macOS, 2026-10-07 to 2026-10-14) |
| AI B-roll and cinematics (0.7.0) | 0.7 |
| macOS (0.7.5) | 0.5 (with templates by feel, 2026-10-07 to 2026-10-14) |
| Describe video (0.8.0) | 0.4 (2026-10-09), 0.6 (2026-10-11), 0.3.5 (2026-10-12), 0.4.2 (2026-10-13), 0.4.7 (2026-10-14) |

## Renumbers

- **2026-10-09**: plans written from the user's notes; re-planned 2026-10-11 and, from the user's notes, 2026-10-12.
- **2026-10-13**, when 0.4.0 shipped the user's overhaul (Analyze / Edit / Generate, Claude's memory, quick drafts,
  colour): the plans that were 0.3.5, 0.3.7, 0.4.0 and 0.4.1 became 0.4.2, 0.4.3, 0.4.4 and 0.4.5 - the same order -
  and 0.4.1 became the fixes after 0.4.0.
- **2026-10-14, morning**: 0.4.6 (check before you render) added, from the rebuild of the first generated video.
  **Prepare** built the same day (Unreleased), the user's ask: improve a script or write one from zero for reach
  (`/write-script` + its guidelines.md, `tools\script.py` = the script check) - yapping mode's step "Topic + script"
  done early.
- **2026-10-14, from the user's notes**: title + thumbnail (horizontal and vertical) and each section its own feel
  added. Renumbered the same day (the user): title + thumbnail up to 0.4.2 and describe video down to 0.4.7; the
  prompt generator up to 0.4.3 and colour down to 0.4.5; each section its own feel = 0.4.1.1, a small step to do
  right away (a four-part number: the updater and What's new read up to x.y.z.w; GitHub's tests run for it by hand or
  with [tests], like 0.4.1).
- **2026-10-14, again** (the user): 0.5.0 = content generation - videos from zero (*Generate*: Claude, HyperFrames,
  AI video tools) made better; gathered from every plan and idea: 0.4.6's sound effects tool, live preview, faster
  motion blur and templates, two ideas (voice-over, music) and new steps. Templates by feel -> 0.6.5, macOS -> 0.7.5
  (its own plan; both were 0.5 together), describe video -> 0.8.0 (was 0.4.7).
- **2026-10-14, evening** (the user picked Claude's review of the plans): check before you render 0.4.6 -> **0.4.2**
  (it saves time on every later video and 0.5.0 builds on it); title + thumbnail 0.4.2 -> 0.4.3; prompt generator
  0.4.3 -> 0.4.4; yapping mode 0.4.4 -> 0.4.5; colour 0.4.5 -> 0.4.6. New: **0.4.2.1** downloads that keep working +
  *Report a problem*. Describe video's foundations (text on screen, shots described, topics) moved into yapping mode
  as its first step, which settles the order conflict between them. plans.md got a status table, a *Ships when* line
  per plan, and this file for the history. 0.5.0's sound effects tool (step 4) was built early the same evening.
- **2026-10-14, released 0.4.1.1**: each section its own feel (the user picked variant B "Bold band" of three shot on
  a test server, then asked for no section numbers, each sidebar row in its section's colour, and Generate in
  fuchsia `#e05cff` instead of pink - picked from tangerine / fuchsia / lime / a sunset gradient), plus everything
  built since 0.4.1: Prepare, the model dialog, check before you render's items 1, 5, 6, 7, and the sound effects
  tool (made 3 dB quieter after the user's listen). Its plan section left plans.md; CHANGELOG.md has it.

## Where some plans came from

- **Describe video**: planned as 0.4 (2026-10-09), then 0.6 (2026-10-11), 0.3.5 since the user's notes of
  2026-10-12, 0.4.2 since 0.4.0 shipped (2026-10-13), 0.4.7 since 2026-10-14 (the user moved title + thumbnail
  ahead), 0.8.0 since later that day (the user made 0.5.0 the content generation version). It was planned as the
  base tool of yapping mode, which comes long before it now - so yapping mode builds the foundations itself.
- **Colour**: the user's note of 2026-10-12 ("a color correction focused version since i think it kinda weak in that
  point"). Placed then after describe video and before yapping mode, because talking videos need it too (phone
  footage: white balance, exposure, skin); the order changed since.
- **Templates by feel / macOS**: planned together as 0.5 since the user's roadmap of 2026-10-07; split 2026-10-14.
- **Yapping mode**: planned as 0.4.0 until 2026-10-13, when 0.4.0 became the Analyze / Edit / Generate overhaul. The
  user's notes of 2026-10-12 say "v0.3.5" for describe video.
- **Prompt generator**: planned as 0.4.1 until 2026-10-13 (0.4.1 became the fixes after 0.4.0), then 0.4.5, then
  0.4.3, now 0.4.4.

## Speech to text: measured and decided (2026-10-12, shipped in 0.3.3 and 0.4.0)

Carried over from 0.3.2 (released 2026-10-12; its Resolve measurements: docs\resolve_notes.md): captions from the
user's own recordings. Captions from any .srt / .vtt worked since 0.3.2; for a recording without one the lab needed
speech to text: the engines were measured on the user's talking video (script `.app\dev\whisper\script_v1.txt`, the
recording in `projects\talk_test\`; HyperFrames' `transcribe` = local whisper.cpp / Parakeet with `--to srt`, and
faster-whisper `tools\dev\whisper_bench.py`, tiny / base / small, also on a laptop setting).

**Measured 2026-10-12** on the user's recording (72 s, phone, read from the script with own changes - so every
engine's error rate below includes those; `tools\dev\speech_bench.py`, report `projects\talk_test\build\speech\`):
faster-whisper int8 on 4 threads: tiny 39.9 % (2 s, 75 MB), base 28.4 % (3.4 s, 141 MB, 360 MB RAM), small 26.1 %
(12.9 s + 5 s load, 464 MB, 730 MB RAM) and **21.1 % with the video's names as a prompt** (MotionLab, 4AM, Nemzzz
right - base with a prompt dropped a whole paragraph); Parakeet (HyperFrames, `models install parakeet`: 640 MB,
5 s here, ~20 CPU-seconds, 1.15 GB RAM, 25 European languages, no names prompt) 26.1 %. HyperFrames' whisper
engine needs whisper.cpp built by hand on Windows - out. Word starts agree within 0.02-0.12 s (median) between
engines. Names are what every engine gets wrong without help.

**Decided + built 2026-10-12** (the user picked faster-whisper small, base as the light option; released in 0.3.3):
`motionlab\speech.py` + `tools\speech.py install | status | transcribe` (optional: Settings > Programs > Speech to
text > Install = the pinned faster-whisper 1.2.1 in the lab's venv + the small model; names via --names / the
dialog, ignored by base); `overlay.py captions --from <a video>` (size / rate / length from the plan or the video -
phone videos stored lying with a 90 deg flag count as upright); App: Graphics > *Captions...* = from the words in a
video (a render of the edit or a clip) or from a subtitle file. Measured on the user's recording: 214 words in
14.5 s, captions at 1080 x 1920, 30 fps, 2159 frames (UI test 9/9). References without subtitles fall back to speech
since 0.4.0 (`content.py auto`). Parakeet stays a possible later option. Small leftovers: the HTML clock's grain tuned
to the lab's texture.

**Earlier measurements** (describe video's "measured so far"):
- **Transcripts (0.3.1)**: `tools\content.py transcript <name>` (yt-dlp: uploaded subtitles in the video's language,
  else YouTube's auto captions of the original audio, which carry word timings) -> `analysis\<name>\content\
  transcript.json / .txt`, frame + timecode per line and per word; `content.py show`; MCP `transcript(reference,
  start, end, words)`. 4AM: 72 lines / 463 words in ~7 s. Timings are the platform's, not measured by the lab.
- **Measuring Whisper**: `tools\dev\whisper_bench.py <name>` (faster-whisper int8 on the CPU in a separate venv, each
  model in its own process, `--threads 4` ~ a laptop; WER and word-timing difference against the subtitles). First
  run, mechanics only (4AM is rap over a beat, so its WER says nothing about talking videos): tiny = 75 MB model,
  318 MB RAM, 27x real time on 4 threads of the RTX 4070 PC's CPU (a laptop core is slower).
- Other engines seen 2026-10-09: HyperFrames (in `tools\overlays\`, optional, needs Node) has a whisper.cpp
  `transcribe` command; ffmpeg's `whisper` filter is in BtbN builds but NOT in Gyan's essentials build (CI's;
  winget's full build: unchecked).
