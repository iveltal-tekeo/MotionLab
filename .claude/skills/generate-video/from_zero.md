# /generate-video - a motion-graphics video (HyperFrames)

Read after SKILL.md (the hard rules, the brief, the waits). Needs Node.js + HyperFrames (`tools\overlay.py doctor`;
missing -> the app's Settings > Programs > Install, or `tools\overlay.py install`).

## The style and the templates
- **The style**: `like` -> the brief has it (`tools\style.py <video> [<video> <video>]`: rhythm, the hook, how text
  appears, effects per minute, colour, Claude's breakdown). A `like` video's `analysis\<name>\feedback\verdicts.json`
  `"sound": {"amount": "none|some|many", "where": "..."}` = the user's answer about its sound effects (Claude cannot
  hear): add cues to match (step 4).
- **Starting blind** (no `like`, only words; 0.4.2): the brief lists the analysed videos whose measured style fits the
  words (`style.py closest`) - 60 % or more -> suggest it as `like`, else suggest analysing one video in that feel
  (one analysed reference turns guessing into measuring).
- **The Motion Graphics library** (0.5.0): build the scenes from the library's templates - designed motion learned
  from pro clips - instead of writing graphics from zero. The brief lists the ones that fit the words (the user's
  `templates` first) with their moves (`tracks`: frame + length), the sizes they are checked at (`ok at` / `NOT at` -
  a template NOT ok at the video's size draws wrong there: pick another or snap it at that size first) and their
  text settings; all of them: `templates.py library --brief`; more by words: `templates.py pick "<words>" --n 8`.
  Match each scene to a template by what it shows - the brief gives each line of the words options of its own
  (2026-10-26); these names are examples, not defaults: a hook word -> kinetic-stack / scatter-text, a number ->
  big-counter, a list -> checklist / wheel-list / rank-number, a story -> story-lines, a chat -> chat-thread, the song
  -> now-playing / audio-bars, a name -> lower-third, pointing at something -> callout-line, a scene change ->
  shape-wipe / pixel-wipe, the end -> end-screen / subscribe-cta / logo-reveal... **Variety** (the user, 2026-10-26:
  the same templates video after video): each template once a video unless a repeat is the point; the ones the brief
  says the last videos used only when clearly the best fit; with 191 templates, look past the first match (`pick
  "<a line>" --n 8 --fresh`, `library --brief`). Write new code only for what no template does. Only when there is no reference, the library has nothing close and the words are vague: the hook
  (the first 3 s) as `overlay.py snap` stills in 2-3 looks (e.g. clean and slick / raw and glitchy / slow and
  cinematic: one small composition per look, the same words, snap 4-6 frames each, one sheet labelled A / B / C) -
  this costs Claude tokens, so keep it to the hook. The user picks or mixes ("B's pacing with A's colours") - that is
  the plan.
- **Motion rules** (measured on 120 pro clips, local-make-9 - in the brief's lessons): something moves in the first 2
  frames; moves ~13 f at 30 fps (7-35 f), S-curve or slow end, linear only for clocks; holds ~20 f, 65 f at most,
  something alive in them; exits faster than entrances. Check the scene table and the cut-sheet against them.
- **The next version** of a generated video: `improve.md`.

## The build
The graphics rules are the ones of `/recreate-video`'s `graphics.md` (read `.claude\skills\recreate-video\graphics.md`,
not the whole skill): HTML / CSS / SVG / GSAP on a paused timeline, times in frames (`F(n)`, `AT(n)`), no timers /
`Math.random` (`rnd(seed)`), fonts from the lab's font library (`tools\fonts.py list`, 0.4.6), settings the user can
change in `data-composition-variables`. Real logos of apps, platforms and AI tools come from the logo library, never
drawn by hand: `tools\logos.py find "<the user's words>"` names them (`show <id>` = its versions); a logo setting takes
`youtube` / `youtube/mono` / `a|b|c`, a text `:youtube:` - the templates logo-wall, logo-reveal, icon-pop, connect-hub,
notification-stack, phone-list and lower-third draw them, renders bundle them by themselves. The user's own logo
(My Brand) is the logo `brand` (2026-10-26): the version that reads on the background is drawn by itself.
**Cheapest check first** (the first video's ~29 min of renders mostly went on bugs a 1-second snapshot shows). The
user approves each step in plain words; no polish before step 3 is approved: (1) the plan in words and numbers - the
scene table with frame + timecode and the feel as numbers ("a cut every 0.5 s, moves over 4-6 frames, a whoosh on
each") - seconds; (2) snapshots at every scene change: `overlay.py snap <folder> <frames>` (no render, ~5 s for 10
frames -> `snap\sheet.png`, + FIT lines for text off the frame / outside its box / overlapping) - seconds; (3) one
plain build: `tools\build.py <project> plan_vN.json --sfx` (every graphic that changed, the sound, the video, the
precheck, the cut-sheet - one call, a 10-line summary) - fix what it flags, look at the cut-sheet once; (4) the final
with the polish (motion blur, the sound mix, Resolve) - once, as a job (SKILL.md *Waits*).
0. **The quick draft first** (0.5.3, no Claude, seconds): `.venv\Scripts\python tools\gen_draft.py <project>
   [--start <s into the song>] [--build]` = scenes changing on the song's downbeats (the first drop a cut), one per
   line of the request's words (the first the hook, the last the end card), a template per scene picked by its words
   (the user's picks first, never one NOT ok at the size), the look and size set -> `plan_vN.json` + `gen_draft_vN.md`
   (the scene table with frames + timecodes, template, words, why); `--build` = its plain build and cut-sheet. Your
   work starts from that table: the words and their order, which template says what, the rhythm against the song -
   change the scenes' settings (`overlay.py set`), swap a template (`overlay.py new --from ... --force`), land a move
   (`--land`), then build again. Always tell the user it began as a rule-made draft. Skip it only when the request
   asks for something no template does.
1. **Timing**: with a song, the brief has its beats (downbeats marked, the drops) as frame + timecode from the
   video's frame 0 (`tools\beats.py <song> --fps 30 [--start S] [--length L]` for another part of the song) - scene
   changes on downbeats, the biggest change on the drop, text hits on beats. Without a song: the style's rhythm
   (shot lengths, the hook).
2. **Scenes**: write the script as scenes (frame ranges + what each shows + which template) and show it to the user
   as a table (`f0-f74 (00:00:00:00-00:00:02:24)`: hook - "the line" - kinetic-stack; ...). The first 3 s are the
   hook (the style's hook numbers).
3. **Build**: one composition per scene, each an overlay layer in the plan one after another. **A scene from a motion
   template** (the usual way): `tools\overlay.py new projects\<p>\build\overlays\<scene> --from <template id> --frames
   <scene frames> --fps <fps> --width <W> --height <H> --values "{\"text\": \"STOP SCROLLING\", \"bg\": \"#0b0b0c\"}"`
   (1080x1920 vertical, 1920x1080 horizontal, 1080x1080 square; 30 fps unless the style says otherwise) - every
   template takes any size, rate and length; its words, colours, font and timing are settings (`overlay.py settings
   <id | folder>`, `set` after); its sound cues come with it (`sfx.py cues`). **A move on a beat**: add `--land
   "<track>@<plan frame>" [--start <the scene's cut>]` - the layer's `start` / `in` worked out from the template's
   tracks (no snapshot rounds for an in-point; render prints the layer, `build.py` keeps it landed). TOO SHORT = the
   template cannot finish its move in that many frames (give it the frames it names). A template's scene setting
   `background` paints the frame. Also the examples (`overlay.py graphics`; `whats-new-0.3.0` is a 10-second
   stand-alone video, `talking-head-pack` kinetic captions). New code: `tools\overlay.py new <folder> --frames <N> ...`,
   expose the texts, colours and timings as settings; animate only with the template's helpers (`set` / `to` / `ft`,
   `bump` = a camera jolt, `smear` for moves over ~60 px a frame): they keep a plain render, a motion-blur render and
   a snapshot the same (M003, M004).
4. **Check** (steps 2-3 above): snapshots at every scene change and text hit (a cut as n-1, n, n+1) - read the FIT
   lines, look at the sheet, fix; then the plain build and its cut-sheet. What the user rated "clunky" (2026-10-14, a
   UI-motion reel): UI drawn too small for the frame, nothing moving between the big moves, no motion blur. Draw it at
   the reference's size (measure it on `frames(<ref>, ...)`), give it a camera (push-ins, a jolt on hits, a slow
   drift), curved cursor paths with a press, and the final with motion blur 5 (`build.py --final`, as a job).
   **Sound effects** (none was rated bad - always add them): while writing a graphic, give each move its cue in
   overlay.json `"cues"` (`{"f": <frame or a formula of the settings>, "kind": ..., "what": ...}`; typed text = one
   key per character, `"repeat": "len(<setting>)"`; kinds: `tools\sfx.py kinds`); templates bring theirs. `build.py
   --sfx` runs `sfx.py plan` on the whole plan: recorded sounds from this PC's library where a kind has them (0.5.4,
   `sfx.py library`), else made up; each effect levelled against
   the song under it and never more than 24 dB under it (so the precheck passes first time); its mix becomes the
   plan's `"audio"`, `build\sfx\<name>_sfx.wav` goes on its own track in Resolve at 01:00:00:00. Read the summary (the
   cues the precheck would flag; `sfx.py plan <plan> --all` = every cue); to change one set the cue's `"db"` or
   `"level"` - never guess a volume. My Brand's sound logo (the brief says when the end card plays it): the plan's
   `"sfx": {"logo": "<path>"}` - it replaces the end card's own cues (the layer `end_card`, or `"end_card": true`).
5. **The plan**: `build\plan_vN.json` = `{"name": "<p>_vN", "width": W, "height": H, "fps": fps, "frames": N,
   "sources": {}, "grades": {}, "layers": [{"type": "overlay", "id": "<name>", "file": "<the .mov>", "start": 0, "end":
   N - 1}], "audio": {"path": "<the song>"}, "output": "<p>_vN.mp4"}` (several compositions = several overlay layers
   one after another; a WAV / FLAC song is encoded to AAC, MP3 / M4A copied; paths may be relative to `build\`) ->
   `tools\build.py <p> plan_vN.json --sfx`. A part of the song that starts later: cut it into `build\` with ffmpeg
   first - never change the user's file. Without a song `overlay.py render <folder> --mp4` alone is the video.
6. Tell the user the render, the scene table (frame + timecode) and which settings they can change in the app
   (Editor > the video > Graphics); a graphic they like can go to the library (`overlay.py save`).
