# Option 2 - rebuild test_4am as a native DaVinci Resolve Studio project

Written 2026-10-05 on PC 1 after the user approved the option 1 render (`projects\test_4am\build\test_4am_v1.mp4`).
Goal on PC 2: the same edit, frame-exact, as an editable DaVinci Resolve Studio project (timeline + Fusion), rendered
from Resolve and verified against the v1 render. Every frame number below is 0-based at 25 fps; timecodes are
non-drop `HH:MM:SS:FF` with frame 0 = 00:00:00:00.

## 1. What already exists (copied from PC 1)

| Path | What it is |
|---|---|
| `refs\NEMZZZ - 4AM [OFFICIAL VIDEO] [VLDJ_-wrwj8].mp4` | the reference (read-only); its audio is the soundtrack of the private test |
| `analysis\NEMZZZ_-_4AM_OFFICIAL_VIDEO_VLDJ_-wrwj8\` | full analysis: `events.json`, `review.json` (all 57 events reviewed), `report.html`, `storyboard\`, `cache\gray380.u8` (used by `verify_timing.py`) |
| `projects\test_4am\DJI_*.MP4` | the user's 6 clips (read-only): 3840x2880 (4:3), **50 fps**, HEVC Main10, BT.709, ~2:11 total |
| `projects\test_4am\build\sources.json` | clip IDs A-F and the SHA-256 of every clip |
| `projects\test_4am\build\ref_timing.json` | the reference's measured timing: panel cuts, clock frames, per-frame curves (pans, flicker, stepped fade, dip, zoom) |
| `projects\test_4am\build\edit_v1.py` -> `plan_v1.json` | **THE EDIT** (65 layers). Single source of truth for the Resolve build |
| `projects\test_4am\build\test_4am_v1.mp4` | the approved lab render = the visual target for Resolve |
| `projects\test_4am\build\compare\test_4am_v1_compare.mp4` | reference vs v1 side by side, frame numbers burned in |
| `projects\test_4am\build\verify_timing.py` | checks a render changes picture on the reference's 54 key frames (v1: 51/54, the 3 others are small/dark changes on the right frames) |
| `tools\motionlab\compose.py` | **the exact specification of every layer type** (the renderer that made v1) |
| `tools\motionlab\graphics.py` | pixel font, seven-segment clock, firework and streak generators |
| `tools\render_video.py` | lab renders: `--stills`, `--sheet`, `--range`, `--compare [--left a.mp4 --right b.mp4]` |

Not copied (regenerated on PC 2): `.venv\` (recreate from `requirements.txt`), `projects\test_4am\build\cache\`
(5.3 GB; `tools\prep_footage.py test_4am` rebuilds it in ~3 min and re-verifies the clips' SHA-256).

## 2. Resolve set-up (user does this once)
1. DaVinci Resolve **Studio** (external scripting is a Studio feature).
2. Preferences > System > General > **External scripting using: Local**, then restart Resolve. Keep Resolve open
   while Claude works (the script talks to the running app).
3. The API reference for the installed version is the README in
   `%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\` - read it before writing code; it
   decides which calls exist (e.g. clip placement with `recordFrame`, `SetStartTimecode`, `SetLUT`, Fusion comps).
   Windows defaults: `RESOLVE_SCRIPT_API=%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting`,
   `RESOLVE_SCRIPT_LIB=C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll`,
   `PYTHONPATH=%RESOLVE_SCRIPT_API%\Modules`. Test the connection first (print `resolve.GetVersionString()`).

## 3. How the plan maps to Resolve

### 3.1 Timeline and frames
- Project/timeline: **1520 x 1080, 25 fps**, non-drop. Timeline start timecode 00:00:00:00 if the API allows it
  (otherwise keep 01:00:00:00 and add one hour whenever a timecode is shown). Plan frame f = timeline frame f.
- Length 3896 frames (f0-3895, 00:00:00:00-00:02:35:20). Audio: the reference's track on A1 from frame 0
  (AAC 44.1 kHz, starts at 0.000 s).
- **Source frames:** every `in` / `jumps` value in the plan is a *cache frame* at 25 fps = every 2nd frame of the
  50 fps DJI file (prep used `select=not(mod(n,2))`). **DJI frame = 2 x cache frame.** A layer shows cache frame
  `in + floor((f - start) * speed)` (see `ClipLayer.src_index`); `jumps` = [[timeline frame, new cache in-point], ...]
  restart the source at a new in-point (jump cuts in one layer). `hold: true` = freeze of DJI frame 2 x in.
- `speed` s -> Resolve clip speed s x 100 % (s = 0.5 on 50 fps footage plays every source frame: smooth slow motion).
- Clip IDs: A = ..._0002_D, B = ..._0003_D, C = ..._0006_D, D = ..._0007_D, E = ..._0013_D, F = ..._0014_D
  (`plan["sources"][ID]["source"]` holds the original path - use the originals in Resolve, never the cache).

### 3.2 Geometry (exact rules in `compose.sample_patch`)
- `rect` = destination box `[x, y, w, h]` in timeline pixels (x right, y down). The source frame is **cover-fit**
  into the box (scaled until it covers it, centred), then zoomed by `zoom` (>= 1) around `anchor` [ax, ay]
  (fractions of the source frame), with the crop clamped inside the source. Box edges are sub-pixel antialiased.
- `dx` / `dy` = offsets in px from a curve (`@pan1`, `@pan2`, `@pan3` = the measured board pans: cumulative px per
  frame, values in `plan["curves"]`). All layers on one pan move together - build each pan section as **one Fusion
  comp (a wide board of panels) with one Transform** keyframed every frame from the curve, so the pan stays
  editable in one place.
- Static panels may use Edit-page Zoom/Position/Crop if the mapping is proven exact on test frames; otherwise use
  Fusion (MediaIn -> Transform -> Crop/Rectangle mask -> Merge) for pixel control.
- Project setting for mismatched resolution: set it explicitly (cover = "Scale full frame with crop") and test.

### 3.3 Look
- Grade (per layer `grade` name -> `plan["grades"][name]`): B&W from Rec.709 luma Y (0-1), then
  `out = out_black + (out_white - out_black) * clip((255*Y - black) / (white - black), 0, 1) ** gamma`.
  Suggested: generate one 3D `.cube` LUT per grade from these numbers and apply it per clip (API `SetLUT` or a
  Color node). Check levels: the DJI files are video range; the lab expanded 16-235 to 0-255 before grading.
- `gain` multiplies; `opacity` blends over the black background; `flash_over` {f: k} = `v + k * (1 - v)` on that
  frame (over-exposed flash, image still visible); `flash_white` = flat `0.86 + 0.06 * v`; `solid` layers = white
  flash frames / black circle (f705); `master_gain` = fade to black f3150-3180 (values in the plan).
- Background black = 0.045 (about 11/255). Grain: Gaussian luma noise sigma 0.010, half resolution (Film Grain or
  Fusion noise).

### 3.4 Generated graphics (lab generators in `graphics.py` show the exact look)
- Title "TEST 4AM" (f0-29 and f3620-3674): boxy outline pixel font (`GLYPHS`), height 54 px, `width_scale` 2.0,
  red (0.86, 0.05, 0.05) with glow; the end card adds a faint dark-red rectangle frame. Placeholder text - the user
  will give real titles later. Build as Fusion Text+ / shapes; a lab-rendered alpha overlay is the fallback.
- Seven-segment clocks: grey grainy beveled ("3:59" -> "4:00" at f320 and f3221), small strobing clock in the logo
  slot f336-358 (opacity curve `logo_strobe`), red LED "04:00" with glow and red vignette f3536-3619. A
  seven-segment font (e.g. DSEG7, OFL licence) in Text+ or Fusion polygons.
- Fireworks f3076 and f3137 (procedural; Fusion particles), light streaks f358-361, photo-strip border f2583-3140.
- Mosaic zoom-out f3223-3530: 76 tiles (layer `mosaic`: cell 52 x 42 px, gap 5, tile list with source + cache frame
  + zoom/anchor crop; the clock tile is the colon's upper dot). One Fusion comp: tiles merged on a canvas, one
  Transform with Size from `mosaic_scale` (s(f) = the reference's measured zoom, 31.7x -> 1x) about the clock tile
  centre, centre y from `mosaic_ay`; tile twinkles f3498/f3519/f3530; red frames f3531, f3533, f3534 and black frames
  f3532, f3535, then the red LED card at f3536.

### 3.5 Prefer native, report fallbacks
Native/editable wherever possible (cuts, panels, flashes, fades, pans, zoom as keyframes, Text+). If an element can't
be built natively (or not exactly), render only that element with the lab as an alpha overlay (ProRes 4444) placed on
its own track, and say so in the report.

## 4. Verification (same standard as v1)
- After each section: render that range from Resolve (H.264, 1520x1080, 25 fps) into `projects\test_4am\build\resolve\`
  and compare with the lab render: `.venv\Scripts\python tools\render_video.py projects\test_4am\build\plan_v1.json
  --compare --left projects\test_4am\build\test_4am_v1.mp4 --right <resolve render>` (+ stills/sheets).
- Full render to `projects\test_4am\build\test_4am_resolve_v1.mp4`, then
  `.venv\Scripts\python projects\test_4am\build\verify_timing.py test_4am_resolve_v1` (target: 51/54 or better,
  like v1) and the side-by-side against v1 and against the reference.
- Every frame mentioned to the user: frame number + timecode.

## 5. Afterwards
- Release version: replace the placeholder titles; the 4AM song is for the private test only - a public release
  needs the user's own (licensed) track, which means re-analysing that track and re-timing the edit.
- When the user approves effects, save each as a Fusion macro (`.setting`) + recipe `.md` in `library\`.

## 6. Status (2026-10-06)
Built and verified: `projects\test_4am\build\resolve\option2_report.md` (full render vs v1 1.83/255, 53/54 key
frames, identical renders before/after reopening the project). Since then the builder also checks the project for
changes made by hand (`--diff`, `--doctor`), keeps them on rebuilds, and gives every Fusion generator float32 depth
(Resolve rendered them in 8-bit right after an import). See CLAUDE.md "Option 2" and "Resolve 21.1 gotchas".
