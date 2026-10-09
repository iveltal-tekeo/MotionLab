# MotionLab - planned versions

What comes next and how it should plug into the lab. The app shows these under *What's new* as "planned" (newest
plan on top); the release itself goes into `CHANGELOG.md` when it ships (never put planned versions there: the
Update button treats every version heading in CHANGELOG.md as released). Headings: `## x.y.z - planned - title`.
Written 2026-10-09 from the user's notes; the user decides scope and order - ask before starting a plan.

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
- **Shot requests come from the analysis**: for reference shot fA-fB Claude writes the request - length (frames at
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

## 0.5.0 - planned - Templates by feel + macOS

- **Use a reference as a template**: its feel and pacing - shot lengths, cuts on the beat, effect families, the
  structure of what is said (0.4) - with your own story, length and music instead of a 1:1 copy. Builds on the
  pacing numbers (`knowledge.pacing`), the effect library and the HTML graphics (0.3).
- **A macOS version** of the app (the lab is Python + a browser window; Edge-only parts, the Recycle Bin, `.bat`
  files and the Windows paths need macOS twins; DaVinci Resolve's scripting paths differ).

## 0.4.0 - planned - Content intelligence: videos as information

**The user's words (2026-10-09):** "if we analyse 10 videos related to making money online we can get common
topics, add notes, ask about it... similar UI as references but dedicated to content as information instead of
filmmaking / effects."

- **Goal**: next to the edit analysis, a *content* analysis - what a video says, not how it is cut. Analyse a set of
  videos on one subject (e.g. 10 "make money online" videos) and see the topics they share, who says what, where
  they disagree, what nobody covers; add your own notes; ask Claude about the whole set.
- **Per video** (`tools\content.py <video>` -> `analysis\<name>\content\`): a transcript with word timings (every
  line with frame + timecode, hard rule 2) - the platform's subtitles through yt-dlp when they exist, else local
  Whisper (decide one engine; HyperFrames ships whisper.cpp too - don't install two), any language; on-screen text
  from key frames (OCR, optional); segments by topic. Then a Claude skill `/analyze-content` (like
  `/analyze-reference`) names per segment the topic, claims, numbers, tools / products, steps, the hook (first
  3 s) and the call to action -> `content.json`, reviewed by the user like effects (Correct / Partly / Wrong).
- **Collections**: a tag (e.g. `make-money-online`) groups references; `content.py collection <tag>` counts topics
  across the videos with links to the exact frames, agreements and contradictions, gaps ->
  `knowledge\local\collections\<tag>\`. Your notes per topic are stored there too (one home, like verdicts.json).
- **App**: on a reference a *Content* tab (transcript with clickable timecodes that move the player, topic chips,
  claims, hook / CTA), and a *Topics* page per collection (topic cards with counts, quotes that open the frame,
  your notes, *Ask Claude about this collection* = a Claude window with the collection loaded).
- **MCP** (`tools\mcp_server.py`): `transcript(reference, start, end)`, `topics(collection)`, `search(text)`, so
  Claude reads the part it needs, not whole transcripts.
- **Sharing**: transcripts are other people's words - they stay on the PC like the videos; only topic summaries,
  counts and short quotes go into shared cards (docs\knowledge_sharing.md).
- **For the creation tools**: the measured structure (hook -> steps -> proof -> CTA with timings) feeds 0.5's
  templates by feel (script your own video with the same structure) and `/recreate-video` (captions, lower thirds
  and on-screen text as HTML overlays timed to the transcript).
- **Also in 0.4** if friends' verdicts are in by then: category profiles (~10 references per category).
- **Open questions for the user**: transcription engine and languages; OCR yes / no; how many videos per collection.

## 0.3.1 - planned - Follow-ups of 0.3.0

- **Automatic tests on GitHub (priority, the user's pick 2026-10-09)**: a GitHub Actions workflow runs
  `selftest.py --extended` (Windows runner, Python 3.12 + ffmpeg; the self-test videos are generated there) on every
  push and shows a red / green check, so a broken version never reaches friends' Update button; a git tag per
  release (`v0.3.0`, ...). Costs nothing on anyone's PC. Ideas still to test: [ideas.md](ideas.md).
- Try the HTML overlays inside a real DaVinci Resolve build (written without Resolve open; test in a scratch project).
- HyperFrames grain: tune the HTML clock's grain to the lab's texture (geometry and timing already match).
- Whatever friends report after updating.
