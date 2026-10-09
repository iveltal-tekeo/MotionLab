---
name: recreate-video
description: MotionLab - recreate a reference video's edit 1:1 with the user's own footage (same song, same cuts, effects and timing) as a lab render, then optionally as an editable DaVinci Resolve Studio project. Use for "/recreate-video <reference> <project>" or when the user asks to rebuild / remake / recreate a reference with their clips.
argument-hint: <reference analysis name> <project folder name>
---

# /recreate-video

Arguments: `$ARGUMENTS` = the reference (a folder in `analysis\`) and the project (a folder in `projects\` with the
user's clips). If one is missing, list `analysis\` / `projects\` and ask. Work from `C:\MotionLab` with
`.venv\Scripts\python`. This is long, multi-step work: the app starts it with effort xhigh.

Only "1:1" exists today (same song, same frames). "By feel" (use the reference as a template for the user's own
story, length and music) is planned for v0.5 - say so if the user asks for it, and offer 1:1 or a free edit.

## 0. Always first (and only this - don't explore the whole lab)
1. Hard rules (CLAUDE.md): the user's clips and the reference are read-only; everything you make goes into
   `projects\<project>\build\`. Every frame you mention to the user: frame number + timecode, e.g. `f480 (00:00:19:05)`.
2. The reference: `analysis\<ref>\events.json` - reviewed events (`events[i].final`: type, what, timing, easing,
   rebuild), `hard_cuts`, `shots`, `audio` (bpm, beats, drops), `video` (fps, frames, size). With the `motionlab` MCP
   tools use `events` / `event` / `frame_info` / `verdicts` / `project` / `stills` instead of reading the big JSON
   files and image files one by one. The user's verdicts and
   notes in `analysis\<ref>\feedback\verdicts.json` win over Claude's review (WRONG / PARTLY notes say what is
   really there). If the reference was never reviewed by Claude (no `review` on the events), say so: rebuilding
   unreviewed drafts copies their mistakes - suggest `/analyze-reference` first.
3. Lessons that concern rebuilding: the shared `.claude\skills\analyze-reference\lessons.md` and
   `knowledge\local\lessons.md` (e.g. over-exposed flashes are Gain on the picture, not a white solid - L001).
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
- Map every reference shot to the user's footage and show the user the mapping as a table (reference shot
  `fA-fB (timecodes)` -> clip ID + in-point -> why it fits). Where the footage has nothing comparable, say so and
  propose the closest option instead of inventing.
- Check before a full render: `tools\render_video.py build\plan_v1.json --stills 480,1633` or
  `--sheet 0:<last>:25` (rendered frames with numbers), `--range A B` for a part.

## 3b. Graphics = HTML overlays (HyperFrames, since 0.3.0)
Titles, counters, lower thirds, shapes, glows, light leaks, particles: write them as HTML / CSS / SVG / GSAP, not as
new compositor or Fusion code. One file serves both the lab render and Resolve (a plain clip, no Fusion to crash).
1. `tools\overlay.py new build\overlays\<name> --frames N` (the plan's size and fps; N = the frames it shows).
2. Edit `index.html`, keeping the rules in its header: transparent background, absolute positions in output pixels,
   animation only on the paused GSAP timeline, times in frames (`F(n)` for tweens, `AT(n)` for jumps that show from
   frame n), no timers / `Math.random` (`rnd(seed)`). Fonts: system fonts or files in the overlay folder.
   Geometry of the lab's own looks: `graphics.text_layout` (pixel font) and `graphics.seg_layout` (seven segment)
   give SVG-ready points; worked examples: `tools\overlays\examples\` (4AM's title and clock).
3. `tools\overlay.py render <folder>` (prints the plan layer), `tools\overlay.py stills <folder> 0,10,40` and look at
   those stills (frame + timecode on a checkerboard) - fix, render again.
4. Plan layer: `{"type": "overlay", "id": ..., "start": f0, "end": f1, "file": "<the .mov>", "blend": "normal"}`
   (`"add"` / `"screen"` for light, `"in"` = first clip frame). In Resolve it becomes a clip on its own track.
Measured on 4AM's title and clock (2026-10-09): same frames as the lab's layers, title within 4/255 (99.9 %).

## 4. Render and verify
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

## Keep it lean
Don't re-read files you have already read in this chat; read tool docstrings instead of whole tools; look at
sheets and stills rather than full renders; work section by section and summarise progress to the user after each.
