# /recreate-video - an exact 1:1 copy of one analysed video

Read after SKILL.md (the hard rules, cheapest check first, the waits, section 0). Same song, same frames: the plan's
frame numbers are the reference's frame numbers. Then `render.md` for the sound, the build and option 2 (Resolve).

## The reference
`analysis\<ref>\events.json` - reviewed events (`events[i].final`: type, what, timing, easing, rebuild), `hard_cuts`,
`shots`, `audio` (bpm, beats, drops), `video` (fps, frames, size). With the `motionlab` MCP tools use `events` /
`event` / `frame_info` / `verdicts` / `project` / `stills` instead of reading the big JSON files and image files one
by one. The user's verdicts and notes in `analysis\<ref>\feedback\verdicts.json` win over Claude's review (WRONG /
PARTLY notes say what is really there). If the reference was never reviewed by Claude (no `review` on the events),
say so: rebuilding unreviewed drafts copies their mistakes - suggest `/analyze-reference` first. Claude cannot hear:
the user's answer about its sound effects is `verdicts.json` `"sound": {"amount": "none|some|many", "where": "..."}` -
add sound effects to match (`render.md`); no answer -> ask once. A 1:1 copy reads Claude's whole memory
(`knowledge.py memory`, SKILL.md section 0 item 3): an effect of the reference rebuilt before starts from that recipe.

The worked example - copy its structure, not its numbers: `projects\test_4am\build\` = `edit_v1.py` (the edit as code
-> `plan_v1.json`, 65 layers), `ref_timing.py` (measures the reference's per-frame curves -> `ref_timing.json`),
`verify_timing.py` (does the render change picture on the reference's key frames).

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
- Check before a full render: `tools\render_video.py build\plan_v1.json --cuts` (every cut on one sheet), `--stills
  480,1633` or `--sheet 0:<last>:25` (rendered frames with numbers), `--range A B` for a part.
- Graphics: `graphics.md` (section 3b).

## 4. Verify the copy
- Copy and adapt `verify_timing.py` (its key frames from the reference's events.json: cuts, flashes, pop-ins,
  strobes) and report the score; `render_video.py <plan> --compare` -> reference | render side by side in
  `build\compare\` (frame numbers burned in).
- Tell the user: the render path, the shot mapping, the score, what is approximate and why. Their notes become v2
  (`edit_v2.py`; never overwrite v1).
