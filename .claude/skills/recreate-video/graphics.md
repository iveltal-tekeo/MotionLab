# Graphics as HTML overlays - /recreate-video section 3b

The one home of these rules: /recreate-video reads this file in its section 0, /generate-video in its section 2.

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
