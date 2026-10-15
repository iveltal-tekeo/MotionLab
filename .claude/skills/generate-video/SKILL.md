---
name: generate-video
description: MotionLab - make a video from zero (no clips of the user's own needed) - a motion-graphics video written as HTML / CSS / GSAP and rendered by HyperFrames, timed to a song; or the plan of a video for AI video tools (Higgsfield, Seedance, Kling, Runway, Veo, Sora, InVideo...) - the shot list and every prompt, saved in the prompt library, which the user generates on the tool's site and then edits with /recreate-video. Use for "/generate-video request <project>", "/generate-video graphics <project>", "/generate-video ai <project>", or when the user asks for a video from scratch, a motion graphic / kinetic text / explainer video, or prompts for a whole AI video.
argument-hint: request <project> | graphics <project> - want: ... | ai <project> - want: ... - tool: ...
---

# /generate-video

The third way in of the app (*Analyser*, *Editor*, **Generator**). `$ARGUMENTS`:
- `request <project>` - the app's *Generator* page saved what the user asked for in
  `projects\<project>\build\generate_request.json`: read it first. `kind`: `graphics` (section 2) or `ai` (section 3);
  `want` (the user's words, as typed), `like` (up to 3 analysed videos whose style to follow), `length_s`, `format`
  (vertical / horizontal / square), `music` (a song: a path in the project folder or `refs\audio\`), `tool` (ai), `text`
  (graphics: the words to show, one item per line), `colours` / `font` (graphics, optional).
- `graphics <project> - want: ...` / `ai <project> - want: ... - tool: ...` - the same, typed.
Work from `C:\MotionLab` with `.venv\Scripts\python`; read tool docstrings, not whole tools. The app opens this with
effort xhigh (graphics) / medium (ai).

## 1. Always first
- Hard rules (CLAUDE.md): never change a file the user gave (songs, logos, footage) - read only; everything you make
  goes to `projects\<project>\build\`; every frame you mention: frame number + timecode, e.g. `f480 (00:00:16:00)`.
- The style: `like` -> `.venv\Scripts\python tools\style.py <video> [<video> <video>]` (rhythm, the hook, how text
  appears, effects per minute, colour, Claude's breakdown); Claude's memory: `tools\knowledge.py memory` - it starts
  with the user's ratings of all their videos as rules (a part rated bad once is a default now: follow them). Copy
  the style, never the content (no one else's words, logos, characters or footage). A `like` video's
  `analysis\<name>\feedback\verdicts.json` `"sound": {"amount": "none|some|many", "where": "..."}` = the user's
  answer about its sound effects (Claude cannot hear): add cues to match (section 2, step 4).
- **Starting blind** (no `like`, only words; 0.4.2): first `.venv\Scripts\python tools\style.py closest "<their
  words>"` - the analysed videos whose measured style fits the words, one line of numbers each; 60 % or more ->
  suggest it as `like`, else suggest analysing one video in that feel (one analysed reference turns guessing into
  measuring). Only when there is no reference and the words are vague: the hook (the first 3 s) as `overlay.py
  snap` stills in 2-3 looks (e.g. clean and slick / raw and glitchy / slow and cinematic: one small composition per
  look, the same words, snap 4-6 frames each, one sheet labelled A / B / C) - this costs Claude tokens, so keep it
  to the hook. The user picks or mixes ("B's pacing with A's colours") - that is the plan.
- **The next version** of a generated video: `build\outcome.json` - `"moments": [{"f", "version", "aspect", "note",
  "date"}]` = notes on single frames: fix exactly those, each named with frame + timecode; `"next": "fix"` = a new
  version with the notes, `"start_over"` = back to step (1) below or to the looks above - never a v2 of a feel the
  user did not want.
- Lessons on making videos: read `.claude\skills\recreate-video\lessons.md` (M###) and
  `knowledge\local\lessons_making.md` (this PC's, if there) and apply every rule. Something new learned here -> a
  lesson in the local file (id: `tools\knowledge.py next-lesson-id --kind making`, the shared file's format).
- Ask once, in one message, for what is missing (what it should say, length, format, the song, brand colours) - then
  build. Say plainly what the lab cannot do instead of faking it.

## 2. A motion-graphics video (HyperFrames)
Needs Node.js + HyperFrames (`tools\overlay.py doctor`; missing -> the app's Settings > Programs > Install, or
`tools\overlay.py install`). The graphics rules are the ones of `/recreate-video` section 3b (read it): HTML / CSS /
SVG / GSAP on a paused timeline, times in frames (`F(n)`, `AT(n)`), no timers / `Math.random` (`rnd(seed)`), system
fonts or font files in the folder, settings the user can change in `data-composition-variables`.
**Cheapest check first** (the first video's ~29 min of renders mostly went on bugs a 1-second snapshot shows). The
user approves each step in plain words; no polish before step 3 is approved:
(1) the plan in words and numbers - the scene table with frame + timecode and the feel as numbers ("a cut every
0.5 s, moves over 4-6 frames, a whoosh on each") - seconds; (2) a sheet at every scene change: `overlay.py snap
<folder> <frames>` (no render, ~5 s for 10 frames -> `snap\sheet.png`) - seconds; (3) the motion: a plain render (~2
min for 25 s), no motion blur, then `.venv\Scripts\python tools\precheck.py <the .mov | snap folder> [--sfx
<name>_sfx.json] [--motion-blur N]`: frames where the picture vanishes for 1-2 frames, moves over ~60 px a frame
without enough blur, effects too loud / buried against the song -> `build\checks\<name>_precheck.json` + `.png`;
exit 1 = look at the sheet, fix before (4); (4) the final with the polish (motion blur, the sound mix, Resolve) - once.
1. **Timing**: with a song, `.venv\Scripts\python tools\beats.py <song> --fps 30 [--start S] [--length L]` = every
   beat (downbeats marked) and the drops as frame + timecode from the video's frame 0 - scene changes on downbeats,
   the biggest change on the drop, text hits on beats (`--start`: the part of the song to use). Without a song: the
   style's rhythm (shot lengths, the hook).
2. **Scenes**: write the script as scenes (frame ranges + what each shows) and show it to the user as a table
   (`f0-f74 (00:00:00:00-00:00:02:24)`: hook - "the line"; ...). The first 3 s are the hook (the style's hook numbers).
3. **Build**: `tools\overlay.py new projects\<p>\build\overlays\<name> --frames <N> --fps <fps> --width <W> --height <H>`
   (1080x1920 vertical, 1920x1080 horizontal, 1080x1080 square; 30 fps unless the style says otherwise), or several
   compositions (one per scene) when it helps; a background that paints the whole frame (it is a video, not an
   overlay). Start from an example when one fits (`overlay.py graphics`; `whats-new-0.3.0` is a 10-second stand-alone
   video, `talking-head-pack` kinetic captions). Expose the texts, colours and timings as settings. Animate only
   with the template's helpers (`set` / `to` / `ft`, `bump` = a camera jolt, `smear` for moves over ~60 px a frame):
   they keep a plain render, a motion-blur render and a snapshot the same (M003, M004).
4. **Check** (steps 2-3 above): `overlay.py snap <folder> <frames>` at every scene change and text hit (a cut as
   n-1, n, n+1) - look at the sheet, show it, fix, repeat; then the plain render and `overlay.py stills`.
   What the user rated "clunky" (2026-10-14, a UI-motion reel): UI drawn too small for the frame, nothing moving
   between the big moves, no motion blur. Draw it at the reference's size (measure it on `frames(<ref>, ...)`), give
   it a camera (push-ins, a jolt on hits, a slow drift), curved cursor paths with a press, and render fast moves with
   `overlay.py render <folder> --motion-blur 5` in the final (5 sub-frames averaged, ~5x the render time).
   **Sound effects** (none was rated bad - always add them): while writing the graphic, give each move its cue in
   overlay.json `"cues"` (`{"f": <frame or a formula of the settings>, "kind": ..., "what": ...}`; typed text = one
   key per character, `"repeat": "len(<setting>)"`; kinds: `tools\sfx.py kinds`). Check them with `tools\sfx.py cues
   <folder>` against the snapshots at the same frames, then `tools\sfx.py make <folder> --song <song> [--song-start
   s]`: synthesised (no samples to license), each effect levelled against the song under it. Its
   `sfx\<name>_mix.wav` is the plan's `"audio"`; `<name>_sfx.wav` goes on its own track in Resolve at 01:00:00:00.
   Read the printed levels (song / floor / peak cap, the limiter); to change one set the cue's `"db"` or `"level"` -
   never guess a volume.
5. **Render**: `overlay.py render <folder>` (the .mov), then the video with its song through a plan:
   `build\plan_vN.json` = `{"name": "<p>_vN", "width": W, "height": H, "fps": fps, "frames": N, "sources": {},
   "grades": {}, "layers": [{"type": "overlay", "id": "<name>", "file": "<the .mov>", "start": 0, "end": N - 1}],
   "audio": {"path": "<the song>"}, "output": "<p>_vN.mp4"}` -> `tools\render_video.py build\plan_vN.json` (several
   compositions = several overlay layers one after another; a WAV / FLAC song is encoded to AAC, MP3 / M4A copied).
   A part of the song that starts later: cut it into `build\` with ffmpeg first - never change the user's file.
   Without a song `overlay.py render <folder> --mp4` alone is the video. Checked 2026-10-13: a 300-frame example +
   a WAV song -> a 10 s MP4 with AAC sound (HyperFrames ~1.6 s a frame on a 2-core cloud machine; a PC is faster).
6. Tell the user the render, the scene table (frame + timecode) and which settings they can change in the app
   (Editor > the video > Graphics); a graphic they like can go to the library (`overlay.py save`).

## 3. A video for AI video tools (the plan + every prompt)
Text only: never call a video model, an API or a website, never ask for a key (paid generation through the API is
planned for 0.7). The user generates on the tool's own site with their plan / credits.
1. **The tool decides the shape**: shot-based models (Higgsfield, Seedance, Kling, Runway, Veo, Sora, Pika, Luma,
   Hailuo) make 4-15 s clips (check the tool's current lengths; ask if unsure) -> a **shot list**: one prompt per
   shot, plus an image prompt for the first frame when the look must stay the same (Nano Banana / GPT Image ->
   image-to-video). Whole-video tools (InVideo AI, Pictory, Synthesia / HeyGen avatars) -> **one prompt for the whole
   video** (script, scenes, voice, music, captions, style) in the tool's own words.
2. **The shot list**: from the style's rhythm (shot lengths, the hook, where the energy rises) and the user's idea;
   one line per shot - length, what is seen, camera move, light / look, the transition into the next. Show it to the
   user as a table before writing the prompts.
3. **The prompts**: follow `/write-prompt` (read `.claude\skills\write-prompt\SKILL.md` sections 0, 3, 4): the
   structure of the user's best-rated prompts for that model (`prompts(kind="shot")`), locks first then the change,
   one camera move per shot, the same character / product / place words in every shot (continuity). Save them all
   in one file and import: `.venv\Scripts\python tools\prompts.py import <file>.json` - one record per prompt, kind
   `shot` / `image` (or `brief` for a whole-video tool), the same `workflow` name (the project) and `step` 1, 2, ...,
   `model` = the tool, `tags` = what it is for, `style_refs` = the `like` videos, a `review` with your stars.
4. **The hand-off** in `projects\<project>\build\ai_plan.md`: the shot table (step, length, prompt id), what to
   generate where, how to name the downloads (`01_<shot>.mp4`, ...) and to put them into `projects\<project>\` -
   then *Editor > New edit* (or `/recreate-video request <project>`) cuts them; the song, captions and graphics are
   added there.
5. Tell the user the prompt ids (they are in the app's prompt library, *Copy Prompt* on each) and the order.

## Keep it lean
Don't re-read what you already read in this chat; look at stills, not whole renders; summarise after each step.
