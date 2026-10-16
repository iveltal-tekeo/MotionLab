---
name: recreate-video
description: MotionLab - edit the user's own clips like videos they analysed - an exact 1:1 copy of one (same song, same cuts, effects and timing) or in the style of up to three (by feel - their rhythm, effects and captions with the user's music and length) - or from their words / a preset / a prompt of the library; as a lab render, then optionally as an editable DaVinci Resolve Studio project; and improve a made video from the user's "how did it turn out?". Use for "/recreate-video <reference> <project>", "/recreate-video request <project>", "/recreate-video feel:<a>,<b> <project>", "/recreate-video want:<presets> <project>", "/recreate-video prompt:<id> <project>", "/recreate-video improve <project>", or when the user asks to rebuild / remake / recreate / edit a video like a reference with their clips.
argument-hint: <reference> <project> | request <project> | feel:<a>[,<b>,<c>] <project> | want:<presets> <project> - want: ... | prompt:<id> <project> | improve <project>
---

# /recreate-video

Arguments: `$ARGUMENTS` = the reference (a folder in `analysis\`) and the project (a folder in `projects\` with the
user's clips). If one is missing, list `analysis\` / `projects\` and ask. Work from `C:\MotionLab` with
`.venv\Scripts\python`. This is long, multi-step work: the app starts it with effort xhigh. `batch <id>` = several
of the user's videos edited the same way in this one window: section 7.

The app's *Editor > New edit* (0.4; the section was called Edit until 2026-10-15) saves what the user picked in `projects\<project>\build\edit_request.json` and
opens `/recreate-video request <project>`: read that file first - `how`: `copy` (1:1 of `like[0]`: the steps below),
`style` (up to three videos in `like`, plus any `presets` / `want`) or `words` (`presets` and / or the user's own
`want`, their words as they typed them) = **By feel** (section 6), `prompt` (`prompt:<id>` below); `length_s`,
`format`, `music` (a song in the project folder), `sound` (auto / music / clips / talk), `resolve` (build option 2
after the user approves the lab render). The same by typing: `feel:<video>[,<video>,<video>] <project> [- want: ...]`
or `want:<preset ids> <project> - want: ...` (presets: `tools\draft_edit.py --presets`).

More ways in (the app's *How did it turn out?*, 0.3.3):
- `prompt:<id> <project>` - a video from a prompt of the library (`prompts(id=...)`; its `tags` say what it is
  for). By kind: **brief** = the user's own instructions for the whole video (length, feel, footage, order, pacing,
  colour, music, SFX, graphics, transitions, captions, where it ends up): follow it part by part with the lab's
  tools, ask its "questions first" part (and anything it leaves vague - its check in the prompt library lists them)
  in one message before building, say plainly what the lab cannot do yet instead of faking it, and write the
  result where the brief says (a Resolve project only through `resolve_build.py`, docs\resolve_notes.md); a
  `style from your reference <name>` line (the card's *Style like*) = match that analysis' measured pacing (cuts /
  min, typical shot, the first 3 s), its effect families (copy the ones the user marked correct: `events(<name>)`)
  and its look (`frames(<name>, ...)`) with the user's own clips - its style, never its content;
  **script / hook** = a talking video - the user films it and adds the recording (the script card's *Film it*,
  2026-10-15: it is copied into the project and linked in `made_from.json`; `build\edit_request.json` has the format
  / length they picked, "length_s" null = all they said), then speech to text (`tools\speech.py`) and **follow the
  script**: line it up with what was said (the script's lines from `script.cue_cards(text)`), keep the best take of
  every line (a repeated sentence = a retake: the later, cleaner one, unless it is worse), tell the user which script
  lines are missing or changed (frame + timecode), and put the script's `[TEXT]` / `[B-ROLL]` / `[ZOOM]` / `[SFX]`
  notes on the words they belong to; captions (`overlay.py captions`) and graphics from the words (the
  `talking-head-pack` example: beats from the transcript, `overlay.py fit`), an edit plan; **shot / image** = for a
  video / image model - write the variants with `/write-prompt` (text only, the user generates them on the site),
  then edit what they drop into the project. Ask once what is missing (length, format, music). Same hard rules.
- `improve <project>` - read `projects\<project>\build\outcome.json` (the user's good / ok / bad + notes per part:
  sound, sfx, colour, captions, graphics, effects, pacing, overall) and `made_from.json`; keep what was rated good,
  change what was rated OK / bad as the notes say (a new edit version, never overwrite the last one); when the video
  came from a prompt, add what worked / failed to that prompt's result note (`prompts.py rate <id> ... --note`).
  **Notes on moments** (0.4.2): `"moments": [{"f": 113, "version": "v2", "aspect": "graphics", "note": "...",
  "date": "..."}]` = notes the user put on single frames of a render (frame of that version; the app stopped taking
  new ones on 2026-10-15 - the per-part ratings sit beside the render now - but saved ones still count). Fix exactly those
  moments, each named with frame + timecode (`f113 (00:00:03:23)`: what you changed), instead of reading one word
  per part; say which moment the new version fixes and how. **Fix or start over**: `"next": "fix"` = a new version
  with the notes (the feel is right, details are wrong); `"start_over"` = back to step 1 of *cheapest check first* or
  to feel tests (section 6) - never a v2 of a feel the user did not want.
- In every mode, Claude's memory (section 0) starts with the user's ratings of ALL their videos as rules: a part
  rated bad once is a default for every new video ("Sound effects: rated bad once -> always add sound effects"),
  good = keep doing it. Follow them; `build\outcome.json` of a video holds its notes.

Two kinds of edit: **1:1** (same song, same frames - sections 0-5) and, since 0.4, **by feel** (section 6: the
style of up to three videos, or the user's words, with their music and length).

**Cheapest check first** (every mode; renders cost minutes, a wrong guess costs a round). The user approves each
step in plain words; no polish before step 3 is approved:
1. The plan in words and numbers: the shots / scenes with frame + timecode, the feel as numbers ("a cut every
   0.5 s, moves over 4-6 frames, a whoosh on each") - seconds.
2. A sheet at every scene change: `render_video.py <plan> --stills a,b,c` / `--sheet`, graphics with `overlay.py snap
   <folder> <frames>` (no render) - seconds.
3. The motion: the quick draft (section 6) or a plain render. Then the checks, before any polish:
   `.venv\Scripts\python tools\precheck.py <render.mp4 | graphic .mov | snapshot folder> [--sfx <name>_sfx.json]
   [--motion-blur N]` flags frames where the picture vanishes for 1-2 frames, moves over ~60 px a frame without
   enough motion blur, and sound effects too loud or buried against the song -> `build\checks\<name>_precheck.json`
   + `.png`; exit 1 = look at the sheet. Fix what it flags (frame + timecode to the user) before step 4.
4. The final with the polish (motion blur, the sound mix, colour, Resolve) - once.

## 0. Always first (and only this - don't explore the whole lab)
1. Hard rules (CLAUDE.md): the user's clips and the reference are read-only; everything you make goes into
   `projects\<project>\build\`. Every frame you mention to the user: frame number + timecode, e.g. `f480 (00:00:19:05)`.
2. The reference: `analysis\<ref>\events.json` - reviewed events (`events[i].final`: type, what, timing, easing,
   rebuild), `hard_cuts`, `shots`, `audio` (bpm, beats, drops), `video` (fps, frames, size). With the `motionlab` MCP
   tools use `events` / `event` / `frame_info` / `verdicts` / `project` / `stills` instead of reading the big JSON
   files and image files one by one. The user's verdicts and
   notes in `analysis\<ref>\feedback\verdicts.json` win over Claude's review (WRONG / PARTLY notes say what is
   really there). If the reference was never reviewed by Claude (no `review` on the events), say so: rebuilding
   unreviewed drafts copies their mistakes - suggest `/analyze-reference` first. Claude cannot hear: the user's
   answer about its sound effects is `verdicts.json` `"sound": {"amount": "none|some|many", "where": "..."}` - add
   sound effects to match (section 4); no answer -> ask once.
3. Lessons on making videos: `.claude\skills\recreate-video\lessons.md` (M###, next to this file) and this PC's
   `knowledge\local\lessons_making.md` - read both and apply every rule; something new learned while making ->
   a lesson in the local file (id: `tools\knowledge.py next-lesson-id --kind making`, the shared file's format).
   Lessons that concern rebuilding an analysed effect: the shared `.claude\skills\analyze-reference\lessons.md` and
   `knowledge\local\lessons.md` (e.g. over-exposed flashes are Gain on the picture, not a white solid - L001).
   Claude's memory: `.venv\Scripts\python tools\knowledge.py memory` (or MCP `knowledge(category="memory")`) = every
   analysed video's style in one line and every effect seen with how it was made (the user's confirmed ones first,
   friends' cards included) - when an effect of the reference was rebuilt before, start from that recipe.
4. The worked example - copy its structure, not its numbers: `projects\test_4am\build\` = `edit_v1.py` (the edit as
   code -> `plan_v1.json`, 65 layers), `ref_timing.py` (measures the reference's per-frame curves ->
   `ref_timing.json`), `verify_timing.py` (does the render change picture on the reference's key frames). The plan
   format and every layer type are defined by `tools\motionlab\compose.py` (read its docstrings / `ClipLayer`,
   `sample_patch`); graphics generators are in `tools\motionlab\graphics.py`.

## 1. The footage
- `tools\prep_footage.py <project>` decodes each clip once into `build\cache\` (IDs A, B, ... + SHA-256 in
  `build\sources.json`, per-frame luma / motion / sharpness / pan stats): **colour** caches by default (~3.9 GB per
  minute of footage), `--grey` for a black-and-white edit (~2.6 GB, like test_4am). It refuses to start when less
  than 2 GB would stay free (the app's Storage page / `tools\storage.py` make room). Cache formats:
  `tools\motionlab\footage.py`.
- `tools\storyboard.py <project>` -> `build\boards\` (one frame per second, frame + timecode). Look at every board
  and note what each clip offers (subject, motion, light, framing).
- Levels: `prep_footage.py` caches expand video range once (cache meta `"levels": "single"`). Plans say which caches
  they were designed on: `"levels": "double"` = the old caches that expanded twice (test_4am v1 keeps its contrast);
  default "single". The compositor and the Resolve LUTs both convert accordingly.

## 2. The reference's timing
- Cuts, effect frames and beats come from events.json. Effects that move over many frames (pans, zooms, flicker,
  stepped fades, dips) need per-frame curves: write `build\ref_timing.py` like test_4am's (it reads the reference
  through its analysis folder, writes `build\ref_timing.json`).

## 3. The edit
- Write `build\edit_v1.py` -> `build\plan_v1.json`: the reference's fps, frame count and audio (same song: frame
  numbers = the reference's frame numbers), one layer per shot / graphic / effect. `plan["sources"] =
  footage.plan_sources(BUILD)` (colour caches; `color=False` for grey). Grades (`plan["grades"]`): levels / gamma /
  output range per channel + `"saturation"` (1 = as shot, 0 = black and white) - the Resolve build turns each into
  the same LUT. test_4am is a grey edit: its grades were tuned on grey caches.
- Colour (0.4): `.venv\Scripts\python tools\colour.py match <project> --like <reference>` = a .cube that moves the
  user's footage toward the reference's measured look (`build\colour\match_*.cube`, closeness before / after,
  0-100); put it in the plan's grade as `"lut3d": "<the .cube>"` (applied first; `"tint"` = per-channel multipliers,
  last) - the lab render and the Resolve build's LUTs both apply it. The look in words per shot: `tools\colour.py
  <reference>`. Phone / log footage that looks wrong after the match: fix exposure / white balance first, say so.
- Map every reference shot to the user's footage and show the user the mapping as a table (reference shot
  `fA-fB (timecodes)` -> clip ID + in-point -> why it fits). Where the footage has nothing comparable, say so and
  propose the closest option instead of inventing.
- Check before a full render: `tools\render_video.py build\plan_v1.json --stills 480,1633` or
  `--sheet 0:<last>:25` (rendered frames with numbers), `--range A B` for a part.

## 3b. Graphics = HTML overlays (HyperFrames, since 0.3.0)
Titles, counters, lower thirds, shapes, glows, light leaks, particles: write them as HTML / CSS / SVG / GSAP, not as
new compositor or Fusion code. One file serves both the lab render and Resolve (a plain clip, no Fusion to crash).
1. `tools\overlay.py new build\overlays\<name> --frames N` (the plan's size and fps; N = the frames it shows), or
   `--from <graphic>` = a copy of one in the graphics library (`overlay.py graphics`: the user's `library\graphics\`
   + `tools\overlays\examples\`) - then change only its settings.
2. Edit `index.html`, keeping the rules in its header: transparent background, absolute positions in output pixels,
   animation only on the paused GSAP timeline, times in frames through the template's helpers (`set` = a jump that
   shows from frame n, `to` / `ft` = tweens that end half a frame early, `bump` = a camera jolt, `smear` for moves
   over ~60 px a frame - so a render with motion blur and a snapshot match the plain render), no timers /
   `Math.random` (`rnd(seed)`). Fonts (0.4.6): a family of the lab's font library (`tools\fonts.py list`: free,
   the same render on every PC; the user's own in `library\fonts\` too) - name it in a font setting (an enum with id
   `font` / `*_font`; `tools\fonts.py sync` writes the library into the shipped designs' lists, a project graphic's
   list grows when the user picks one) and renders / snapshots copy it into `assets\fonts\` themselves; never a
   Windows-only font for something new. Logos (2026-10-16): a real app / platform logo comes from the logo library
   (`tools\logos.py find "<words>"`), never redrawn - a logo setting (`logo` / `*_logo` / `logos`: `youtube`,
   `youtube/mono`, `a|b`), `:youtube:` in a text, or overlay.json `"logos": [...]` for code-only uses; in the page
   `MLLogo.el(id, {dark, tint, mono})` after `<script src="assets/logos/logos.js">`; renders bundle them.
   Geometry of the lab's own looks: `graphics.text_layout` (pixel font) and `graphics.seg_layout` (seven segment)
   give SVG-ready points; worked examples: `tools\overlays\examples\` (4AM's title and clock, drawn from their
   settings in JS - the same pixels as the hard-coded 0.3.0 versions).
   **Settings (0.3.2)**: whatever the user may want to change (text, colours, sizes, positions, timing in frames)
   goes into `data-composition-variables` on `<html>` (types string / color / number with min / max / step / boolean
   / enum with options `[{"value", "label"}]`) and is read from `V = window.__hyperframes.getVariables()`; the app's
   Videos > Graphics tab edits them (overlay.json `values`), `overlay.py settings | set` from here.
3. First `tools\overlay.py snap <folder> 0,10,40` (no render, seconds: stills straight from the HTML + `snap\sheet.png`;
   a cut as n-1, n, n+1) - look, fix; then `tools\overlay.py render <folder>` (prints the plan layer) and
   `tools\overlay.py stills <folder> 0,10,40` (rendered frames, frame + timecode on a checkerboard) - fix, render again.
4. Plan layer: `{"type": "overlay", "id": ..., "start": f0, "end": f1, "file": "<the .mov>", "blend": "normal"}`
   (`"add"` / `"screen"` for light, `"in"` = first clip frame). In Resolve it becomes a clip on its own track
   (a numbered copy - Resolve locks the files it uses; after a new render `overlay.py refresh <folder>` swaps it and
   keeps the user's edits; measured 2026-10-12: same frames as the lab within 2.3/255).
5. One the user approves: `overlay.py save <folder> [--name N]` -> `library\graphics\<N>\` (or their Save to library
   button), so other videos can start from it.
6. Captions: `overlay.py captions build\overlays\captions --from <the render | a clip | .srt | .vtt> --names "..." --render`
   (styled, timed to the words; also `captions.srt` for Resolve's subtitle track). A video's words come from
   `tools\speech.py` (faster-whisper small; names it cannot guess go in --names); take the render of the edit so
   the captions follow its cuts. Looks (0.4.6): `--preset clean_box` (sentence case on a rounded dark box that fits
   the line, the said word cyan, a fade, 30 % from the bottom on 9:16) or `classic` (the default: capitals, outline,
   yellow word); `overlay.py preset <folder> [id]` lists / switches; the app's Graphics tab has the same choice and a
   live preview.
Measured on 4AM's title and clock (2026-10-09): same frames as the lab's layers, title within 4/255 (99.9 %).

## 4. Render and verify
- Sound effects (a part rated bad once is a default - see the ratings in Claude's memory): `tools\sfx.py plan
  build\plan_vN.json` (+ `--song <file>` when the plan's sound is not the song) puts a whoosh / hit / riser on the
  plan's zooms, whips, flashes and speed-ups and the cues of its graphics, levelled against the sound under each;
  make the plan change it prints (the mix as `"audio"`; the effects alone = their own Resolve track). How many and
  where: the reference's `"sound"` answer (section 0); `precheck.py --sfx` checks the levels before the final.
- `tools\render_video.py build\plan_v1.json` -> `build\<project>_v1.mp4` (renders in parallel processes: ~3x
  faster, `--workers 1` = one process; any frame looks the same alone, in a range or in a chunk); `--compare` ->
  reference | render side by side in `build\compare\` (frame numbers burned in).
- Copy and adapt `verify_timing.py` (its key frames from the reference's events.json: cuts, flashes, pop-ins,
  strobes) and report the score.
- Tell the user: the render path, the shot mapping, the score, what is approximate and why. Their notes become v2
  (`edit_v2.py`; never overwrite v1).

## 5. Option 2 - the same edit in DaVinci Resolve (only when the user wants it)
Needs DaVinci Resolve **Studio** running with Preferences > System > General > External scripting = Local. Read
`docs\resolve_notes.md` first (the API's gotchas cost hours otherwise). Ask the user once before the first build on
a PC (the LUTs go to `C:\ProgramData\...\LUT\MotionLab\<project>\`). Then `resolve_build.py build\plan_vN.json
--replace`, per section `--render A B` + `compare_renders.py` against the lab render, then `--render-full` +
`verify_timing.py <timeline>`. `resolve_build.py` was made on test_4am: its `SECTIONS` and some builders are
specific to that edit - generalise with care, test in the scratch project. Never overwrite the user's hand edits:
`--doctor` and `--diff` first.

## 6. By feel - the style of up to three videos, or the user's words (0.4)
The user: "use a reference video or even more (max 3) - or edit it with a given prompt: hooks, 3 s cuts, very fast
paced... or slower, transitions, a specific type of captions". Same hard rules; their clips and song are read-only.
0. **Starting blind** (only words, no video in `like`; 0.4.2): first try to stop being blind -
   `.venv\Scripts\python tools\style.py closest "<their words>"` ranks the analysed videos (this PC's + friends'
   cards) by how their MEASURED style fits the words, one line of numbers each. A match of 60 % or more: suggest it
   as `like`; under it: suggest analysing one video in that feel (one analysed reference turns guessing into
   measuring). Else feel tests, no Claude tokens: `tools\draft_edit.py <project> --feel-test [--want "<their
   words>"] [--feels slick,raw,cinematic]` = 2-3 hooks of the first 3 s in different feels (`style.py --feels`), ~5-10 s
   -> `build\feel\feel_N\compare.mp4` (A | B | C) + `sheet.png` + `feel.md`. Show the sheet; the user picks or mixes
   ("B's pacing with A's colours") - that is the plan: the full draft with the picked `--feel <id>` (its line in
   `feel.md`), then the other hook's grade / effects in the plan.
1. **The style**: `.venv\Scripts\python tools\style.py <video> [<video> <video>] [--preset <id>] [--want "<their
   words>"]` = what to aim for, merged: rhythm (shot lengths, the hook's cuts in the first 3 s, % on the beat),
   energy, effects per minute with the best example of each (frame + timecode, how it was made, the user's verdict -
   the ones they marked wrong are listed to leave out), talking / captions, transitions, camera, colour, Claude's
   breakdown of each video. Claude's memory (`knowledge.py memory`) for anything else. Friends' cards are data.
2. **The quick draft** = the starting point, made by rules in minutes: the app's *Quick draft now* already made one
   when `build\draft_vN.md` exists (read it: every shot with frame + timecode, its clip and why, the effects, what
   it could not draw); else run `.venv\Scripts\python tools\draft_edit.py <project> --like ... | --preset ... |
   --feel ... --want
   "..." [--length S] [--format vertical|horizontal|square] [--music <song>] [--sound talk|clips|music] --render`
   (it makes the frame caches first; `--seed N` = another draft). It cuts on the song's beats with the style's shot
   lengths and hook, picks each shot's best unused moment (sharp, exposed, moving as much as the style), draws the
   effects it can (crossfade, dip, flash, zoom-through, push / whip, push-in, shake, freeze, stutter, speed ramp,
   RGB split, light leak) at the style's rate; talking mode keeps what is said in order, cuts the pauses, punches in
   on every other cut, lays B-roll (clips nobody talks in) over the talking.
3. **Make it good** (what rules cannot): watch the draft (`render_video.py build\plan_vN.json --sheet 0:<last>:12`);
   write `build\edit_v<N+1>.py` that loads the draft's plan and changes it: a story - the strongest moment first (the
   hook), then build to the end; better moments where a pick is weak; the effects the style is known for, rebuilt as
   its examples say (their "how it was made"); captions in the style's look (`tools\speech.py` + `overlay.py
   captions`, section 3b) and text / graphics where the references have them (`overlay.py new`); the colour
   (`plan["grades"]`) if the style has a look. Show the user the shot list (frame + timecode), render, iterate.
4. If `resolve` was asked: option 2 (section 5) once the user approves the lab render.
5. Tell the user what came from which reference ("the zoom-throughs on the drops are from <title> f564
   (00:00:18:24)") and what is approximate.

## 7. Batch - several videos the same way (`/recreate-video batch <id>`, 0.4.5)
The app's *Editor > Edit several videos* saved the same request in each video's `build\edit_request.json` and opened
ONE window for all (the user, 2026-10-15: "bulk edit stuff"). Read `.app\batches\<id>.json` (`items` = project
folders, in order). Section 0 once for the whole batch. Then per video, one at a time and completely: its request
(section 6 - a quick draft if it has none, then make it good), render, check - before the next, so a stop loses at
most one video (*Continue the batch* skips the videos that already have an edit plan by you newer than the batch).
Name the project folder in your tool calls as you work: What it took splits this window's time per video by it.
After each: one line ("2 of 4 done - <video>: v2, 0:42"); at the end a short list with each render's path and what
to look at first. Ask the batch's questions once, at the start (not per video).

## Keep it lean
Don't re-read files you have already read in this chat; read tool docstrings instead of whole tools; look at
sheets and stills rather than full renders; work section by section and summarise progress to the user after each.
