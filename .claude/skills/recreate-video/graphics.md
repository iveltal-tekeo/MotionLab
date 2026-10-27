# Graphics as HTML overlays - /recreate-video section 3b

The one home of these rules: /recreate-video and /generate-video read this file when a video has graphics.

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
   `MLLogo.el(id, {dark, tint, mono})` after `<script src="assets/logos/logos.js">`; renders bundle them. The
   user's own logo (My Brand) is the logo `brand` (2026-10-26; `brand/icon` = its icon): the version that reads on
   the background is drawn by itself.
   Geometry of the lab's own looks: `graphics.text_layout` (pixel font) and `graphics.seg_layout` (seven segment)
   give SVG-ready points; worked examples: `tools\overlays\examples\` (4AM's title and clock, drawn from their
   settings in JS - the same pixels as the hard-coded 0.3.0 versions).
   **Settings (0.3.2)**: whatever the user may want to change (text, colours, sizes, positions, timing in frames)
   goes into `data-composition-variables` on `<html>` (types string / color / number with min / max / step / boolean
   / enum with options `[{"value", "label"}]`) and is read from `V = window.__hyperframes.getVariables()`; the app's
   Videos > Graphics tab edits them (overlay.json `values`), `overlay.py settings | set` from here.
3. First `tools\overlay.py snap <folder> 0,10,40` (no render, seconds: stills straight from the HTML + `snap\sheet.png`;
   a cut as n-1, n, n+1; 0.5.3: its FIT lines name any text off the frame, outside its box or overlapping, with frame
   + element + pixels - fix those without looking for them) - look, fix; then `tools\overlay.py render <folder>`
   (prints the plan layer) and `tools\overlay.py stills <folder> 0,10,40` (rendered frames, frame + timecode on a
   checkerboard) - fix, render again. In a whole video `tools\build.py` renders every graphic that changed (SKILL.md).
   A copy of a template shorter than it can finish prints TOO SHORT (template.json "min_frames"); an overlay.json
   value out of range prints IGNORED (the default is used).
4. Plan layer: `{"type": "overlay", "id": ..., "start": f0, "end": f1, "file": "<the .mov>", "blend": "normal"}`
   (`"add"` / `"screen"` for light, `"in"` = first clip frame). A template's move on a beat (0.5.3): `overlay.py new
   <folder> --from <id> --land "<track>@<plan frame>" [--start <cut>]` works out `start` / `in` from the template's
   tracks (`templates.py tracks <id>` lists them with frames) - render prints that layer with its `"land"`: keep it
   in the plan and `build.py` lands it again when the copy's settings move the move (a layer you moved by hand
   stays); no snapshot rounds to find an in-point. In Resolve it becomes a clip on its own track
   (a numbered copy - Resolve locks the files it uses; after a new render `overlay.py refresh <folder>` swaps it and
   keeps the user's edits; measured 2026-10-12: same frames as the lab within 2.3/255).
   **On a person - part of the shot, not pasted on** (0.6.1; the user, 2026-10-27: graphics "combining it with
   talking heads or people is where it gets kinda AI-ish"): a graphic over someone on camera gets the layer keys that
   make it belong (compose.py; the person and face are made once per clip from its light cache, `motionlab\person.py`,
   before the render): a big word or shape BEHIND the person = `"behind": true, "follow": "camera", "match": true`
   (it stays on the wall: grows with a punch-in, never chases the head); a label, an arrow or brackets ON the person =
   `"follow": "face"`; a card or pill = `"glass": true` (the room under it frosted - set the template's own see-through
   background: off, its grain: 0), `"shadow": true`, `"match": true`; anything near the head = `"guard": true` (never
   over the face). Place them like an editor: a lower third below the chin with room for a punch-in (no punch-in while
   a lower third shows - the chin reaches it and guard cuts a hole in it), a word behind the head big enough to read
   round it; then the stills (`render_video.py <plan> --stills ...`, the middle of each graphic and every punch-in) and
   fix what touches the face. Short (1.5-4 s), few, on the word. The A/B that showed it: projects\zz_behind_test
   (`build\compare\today_vs_integrated_v2.mp4`).
   **Effects like Vibha Ramprakash's** (her claude-video-effects skill, MIT; the user, 2026-10-27: "so i can replicate
   the same design videos she has as examples"). The user names a moment in words ("spotlight when I say 'kill the
   lights', the word CLAUDIT behind me"): find the word's frame in the edit (the take's transcript through the shots -
   the talking draft's notes / `speech.py`), then edit-list lines (`effect <kind> at f`, `graphic <template> at f for n
   text="..."` - the template's own `in_shot` puts it in the shot), stills at the middle of each, then the render.
   Hers -> ours: lean-in = `effect lean-in`; locked-on = `graphic lock-on-brackets` (+ `effect lean-in`); slow-push =
   `effect slow-push`; spotlight = `effect spotlight` (+ `graphic word-behind` or `led-sign`); backdrop-word =
   `word-behind`; led-sign = `led-sign`; countdown-flip = `countdown-flip`; scribble / pause-point = `scribble-callout`
   (+ `hold fA-fB` to freeze); comment-box = `comment-box`; tap = `follow-tap`; messages = `message-stack`;
   reject-stamp = `reject-stamp`; apple-toggles = `settings-toggles`; liquid-glass-graph = `glass-graph`; checklist /
   todo = `task-checklist`; headline-box / split-headline = `headline-box`; moody = a grade; red-collage = `word-behind`
   red + a grey grade. Not yet (0.6.x plans): her reels-around-you ones (noise, orbit, carousel, phone-fan, profile
   wall, place-in-grid, check-pills - they need the user's own reel covers), lineup, the-bill, swipe, uninstall,
   reel-frame, shortcut-rain, rabbit-hole, cover-star, glass-widgets, pastel-word, timeline, tier-list, broll-split,
   dot-reveal, headline-wall, match-cut, over-the-shoulder-zoom - say so instead of faking one. Her rules hold here
   too: 1.5-4 s each, never over the face, zoom at most 2x (ours: small, eased - the user, 2026-10-27: "maybe u zoom in
   too much"), and she is honest that they are starter versions: the user's sound design and timing finish them.
   **Where cards fit** (learned on the user's own takes, 2026-10-27 - projects\zz_vibha_demo 16:9, zz_vibha_vertical
   9:16): upright, a card lives between the chin (the face's guard oval ends ~y 1040-1080 of 1920 when they lean in)
   and the apps' bottom band (precheck SAFE_BANDS: y 1500+), left of the right rail (x 930+): `y` 66-69, `x` ~46,
   `size` 0.7-0.8; a word or sign behind the head sits above it (`y` ~20-23; a sign's own dimmed room in the top band
   is meant). A 16:9 webcam close-up has the head in the middle: cards small at the far side (`x` ~85). Over a light
   shirt a glass card's light words vanish - `tone=smoke`; over skin the frost needs more blur (`"glass": 60` on the
   layer). The order that caught every one before the video render: render the graphics, `catalogue.py shots` (face
   bites), fix, then `build.py` (the safe zone), then frames at each graphic.
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
