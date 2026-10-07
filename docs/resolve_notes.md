# DaVinci Resolve notes (read before any Resolve scripting)

Moved out of CLAUDE.md on 2026-10-07 so that sessions which never touch Resolve don't carry them. Read this file
before working with `tools\resolve_build.py`, `tools\library.py test|install`, Fusion comps or a Resolve project.
The full option 2 spec (how the test_4am plan was rebuilt) is `docs\option2_resolve.md`.

## resolve_build.py (option 2: a plan as a native DaVinci Resolve Studio project)
`resolve_build.py <plan.json> --replace` rebuilds a plan as a Resolve project (project = the project folder name,
timeline `<project>_resolve_vN`; Resolve Studio must be running with external scripting = Local). `--sections S1,S2`
builds part of it (sections in `SECTIONS`), `--render A B` renders frames A..B to
`build\resolve\<timeline>_A-B.mp4`, `--render-full` to `build\<timeline>.mp4`, `--no-build` only renders, `--only
u1,u2` re-imports just those Fusion comps (fast tuning), `--timeline X` works on another timeline, `--doctor` checks
Resolve/media/LUTs/timeline (read-only), `--diff` lists what the user changed by hand in Resolve since the build.
`--replace` keeps the old timeline (renamed `... (replaced <date time>)`); `--delete-old` deletes it; `--only` refuses
to replace a hand-edited comp unless `--overwrite-edits` (saved first to `edits\<date time>\`). Writes
`build\resolve\`: `luts\` (one .cube per grade/gain/flash), `comps\` (latest .comp per Fusion unit;
`comps\imported\<sha1>.comp` = every version ever imported), `media\` (grey carrier clip, `stills\` = lab-rendered
photo strips + mosaic wall levels), `<timeline>_build.json` (manifest: units, clips, LUTs, comp sha1 per unit),
`edits\live\` (hand-edited comps as text, from `--diff`), `checks\`.
It was built and verified on test_4am: `SECTIONS` and several builders are specific to that edit - generalise with
care and test in a scratch project.

## How resolve_build.py maps a plan to Resolve (details: docs\option2_resolve.md, code comments)
- Timeline 1520x1080 25 fps starting at 00:00:00:00 (plan frame f = timeline frame f), A1 = reference audio, V1 = a
  grey 0.045 ProRes carrier clip = the background; every Fusion comp sits on a piece of that carrier.
- Static panels = Edit-page clips of the original DJI files (in-point 2 x cache frame) with Edit-page Zoom/Pan/
  Tilt/Crop reproducing `compose.sample_patch` exactly; grades = Color-page LUTs; flash frames = 1-frame cuts with a
  flash LUT; holds = freeze frames. Animated layers = Fusion: pan boards (panels + ONE Transform keyed per frame),
  fades (grey overlay keyed per frame), titles (rectangles), clocks (polygons), streaks, fireworks (particles),
  mosaic (ONE `MosaicZoom` control keyed per frame; the wall = lab-rendered level images), grain (Linear Light).
- LUTs: Resolve's Color page only applies LUTs from its LUT folders, so the build copies them to
  `C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\MotionLab\<project>\` (outside the lab: ask the user
  once before the first build on a PC - the original user approved it on theirs).
  For `"levels": "double"` plans they include the old caches' extra tv->full step (Resolve decodes correctly).
- Drift check: the manifest + `comps\imported\<sha1>.comp` record exactly what each timeline got; `--diff` compares
  every comp input (static ones at first/middle/last frame, keyed ones on every frame), connections, expressions,
  added/deleted tools, Edit-page transform, in-point, LUT, extra Color nodes, opacity/composite/enabled, missing or
  added clips. Tested on scripted edits in a scratch project (all caught). test_4am: the user's grain edit (strength
  0.0077 -> 0.0157, size 1 -> 1.63) is kept in the timeline; `build\test_4am_resolve_v1.mp4` used the lab grain.
- Verified 2026-10-06: full render vs v1 1.83/255 mean |difference|, 53/54 key frames (v1 51/54); the same timeline
  renders identically before and after reopening the project.

## Working on a Resolve project the user may have touched
- Before changing it: `--doctor` (a NOTE line counts hand edits) and `--diff`. To verify the lab's version without
  touching their edits, duplicate the timeline (`Timeline.DuplicateTimeline`) or build a separate one with
  `--timeline X`, render that, then delete it.
- Hand edits in Resolve are the user's: never overwrite them silently (`--diff` first); good ones become knowledge.
- Option 2 per section: `resolve_build.py <plan> --replace`, then per section `--render A B` + `compare_renders.py`
  against the lab render, then `--render-full` + `verify_timing.py <timeline>`.

## library.py (the effect library: Fusion macros + recipes)
`library.py build [effect ...]` writes `library\` (macros from the `fx_*` builders + recipes from `META` /
`RECIPE_ONLY`; reference frames decoded read-only with a SHA-256 check); `library.py test [effect ...]` renders every
macro (`CASES`) in a throwaway Resolve project `motionlab_scratch` (deleted afterwards; the open project is saved and
reopened), measures it against the real reference frames and writes `check.png` + the numbers into the recipe;
`library.py title "TEXT"` = a pixel-font title macro for any text (`library\pixel-title\variants\`). Macros: effects =
MainInput1 -> MainOutput1; titles draw on a 1920x1080 canvas placed at native size (Position / Size / Opacity);
additive light = alpha 0 after the colour (ChannelBoolean ToAlpha=15). Values only from the reviewed analysis, the
user's feedback and the verified test_4am rebuild (`resolve_build` FIREWORK, blur_size, text_strokes).
`library.py install | uninstall | verify-install` (Resolve Templates\Edit\{Titles,Effects}\MotionLab,
Macros\MotionLab; recorded in library\installed.json) writes outside the lab: only when the user asks (on the
roadmap for later; 2026-10-06 the user postponed it). Test scratch (plates, frame cache, `checks.json`) lives in
`analysis\<ref>\inspect\library_test\`.

## Resolve 21.1 scripting gotchas (measured on PC 2, 2026-10-05)
- `ImportMedia([path])` (list form) works, the documented dict form returns None. `AppendToTimeline` endFrame is
  exclusive, in source frames (50 fps for DJI). `SetSettings`: one key per call for timeline settings (a combined
  call froze Resolve); render settings one key per call too (H.264 refuses `VideoQuality`).
- Speed 0 freezes the FIRST frame only when the playhead is before the clip (after it: last frame; inside it:
  Resolve splits the clip). Edit page: Tilt is in units of 1080/1140 px for 4:3 sources; crop is in input-scaled
  source px before zoom.
- A clip's Fusion comp starts at frame 0 on the clip's first frame (keys must be offset by the clip start); on a DJI
  clip it runs in 50 fps source frames at 3840x2880, so comps go on the 25 fps carrier.
- Never `comp.AddTool("Loader")` in a live Resolve: it opens a file dialog that blocks scripting (the user saw it);
  write comps as text and `ImportFusionComp`. Fusion's Loader cannot read the DJI HEVC files; `MediaIn` by media ID
  can. Give every panel / still its OWN MediaIn: many TimeStretchers on one long-GOP HEVC MediaIn = a keyframe seek
  per request (a 600-frame section estimated 100 h, and cancelling it hung Resolve).
- Keep comps lean (the user saw Resolve crash on heavy Fusion work): ~40-90 tools per comp is fine; the first mosaic
  (499 tools, 75 live 4K decodes) and live photo strips were replaced by lab-rendered stills + native animation.
- Fusion: chained masks need PaintMode Maximum (Merge paints a level-0 shape OVER the mask = erases it); Custom tool
  has no `pow()` (returns 0, use `^`); a Custom tool's alpha-0 output is premultiplied to black (use ChannelBoolean
  ToAlpha=15 afterwards); output with alpha 0 adds onto the tracks below; Resolve clips negative added values (grain
  = Linear Light layer 0.5 + n/2); Gaussian Blur size -> sigma is non-linear (table `BLUR_CAL`); particles: velocity
  1 = 152 px/frame, drag v *= 1 - k per frame, disable pre-roll, Line style needs RotationMode 1; ErodeDilate amount
  is NOT pixels (1.0 whitened the frame).
- A script that exits while Resolve renders makes Resolve abort the render: `Session.render` re-fetches the project
  when a scripting object drops out instead of exiting.
- Macros (MacroOperator) in an imported comp: connections across the macro boundary must name the REAL tools (the
  plate -> the macro's first tool, the macro's last tool -> MediaOut1); a link to the macro's own output
  (`SourceOp = "ML_x", Source = "MainOutput1"`) is silently dropped on import, MediaOut1 has no input and the job
  fails ("The Fusion composition at ... could not be processed successfully"). A failed comp still leaves output
  files - stale frames of OTHER comps - so always check `GetRenderJobStatus(...)["JobStatus"] == "Complete"`.
  Resolve turns a Loader of a still into a media-pool Loader (MEDIA_ID) on import; UserControls + expressions on
  tools inside a macro survive.
- EllipseMask Width AND Height are fractions of the mask WIDTH (a circle of d px: Width = Height = d / W); measured
  2026-10-06 (round colon dots came out 1.78x tall with d / H). RectangleMask Height is a fraction of the HEIGHT
  (pixel-exact in the test_4am rebuild). test_4am v1's f705 circle and firework cores were drawn with d / H (fixed in
  resolve_build for the next build; the existing timeline is unchanged).
- Fusion Transform: Size scales about Pivot, Center only translates (out = P + (X - P) s + Center - 0.5); verified
  against 4AM's mosaic zoom (tile path within 1 px).
- (2026-10-06) Fusion tools that generate images (Background, Rectangle/Polyline/Ellipse masks, FastNoise, pRender)
  with Depth = Default render in 8-bit right after `ImportFusionComp` and in float after the project is reopened
  (the comp prefs say float both times): the same timeline rendered differently before/after a reload. The builder
  sets Depth = 4 (float32) on them (`GEN_DEPTH`); Film Grain in float has no mean bias (the old "bias" was 8-bit
  rounding of the mid grey). Always compare renders, not just input values, when testing persistence.
- `GetSourceStartFrame()` floors start time x fps and reads one source frame low on some clips; `GetLeftOffset()`
  (timeline frames) is exact. `SetInput(id, v)` without a time on a keyed input changes nothing - pass the frame.
  `TimelineItem.ExportFusionComp(path, 1)` and `Timeline.DuplicateTimeline(name)` work. Fusion auto-creates
  `LUTBezier` modifiers (particle over-life curves, Custom tool LUTs): not user edits.
- Throwaway tests go in a scratch project (`motionlab_scratch`, deleted afterwards), never in the user's project;
  scripts that switch projects must end with `LoadProject("<the user's project>")`.
