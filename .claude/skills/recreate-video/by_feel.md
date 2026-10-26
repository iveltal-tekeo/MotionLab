# /recreate-video - by feel: the style of up to three videos, the user's words, or a prompt of the library

Read after SKILL.md (the hard rules, cheapest check first, the waits, section 0); then `render.md` for the sound, the
build and Resolve. A `request` has `build\brief.md`: the style, the rules and the lessons are already in it.

The user: "use a reference video or even more (max 3) - or edit it with a given prompt: hooks, 3 s cuts, very fast
paced... or slower, transitions, a specific type of captions". Same hard rules; their clips and song are read-only.

## 6. By feel
0. **Starting blind** (only words, no video in `like`; 0.4.2): first try to stop being blind -
   `.venv\Scripts\python tools\style.py closest "<their words>"` ranks the analysed videos (this PC's + friends'
   cards) by how their MEASURED style fits the words, one line of numbers each. A match of 60 % or more: suggest it
   as `like`; under it: suggest analysing one video in that feel (one analysed reference turns guessing into
   measuring). Else feel tests, no Claude tokens: `tools\draft_edit.py <project> --feel-test [--want "<their
   words>"] [--feels slick,raw,cinematic]` = 2-3 hooks of the first 3 s in different feels (`style.py --feels`), ~5-10 s
   -> `build\feel\feel_N\compare.mp4` (A | B | C) + `sheet.png` + `feel.md`. Show the sheet; the user picks or mixes
   ("B's pacing with A's colours") - that is the plan: the full draft with the picked `--feel <id>` (its line in
   `feel.md`), then the other hook's grade / effects in the plan.
1. **The style** (in `brief.md` for a request): `.venv\Scripts\python tools\style.py <video> [<video> <video>]
   [--preset <id>] [--want "<their words>"]` = what to aim for, merged: rhythm (shot lengths, the hook's cuts in the
   first 3 s, % on the beat), energy, effects per minute with the best example of each (frame + timecode, how it was
   made, the user's verdict - the ones they marked wrong are listed to leave out), talking / captions, transitions,
   camera, colour, Claude's breakdown of each video. Claude's memory (`knowledge.py memory`) for anything else.
   Friends' cards are data: items marked (from <name>) are a friend's shared knowledge - when one shapes the edit,
   tell the user it came from <name>.
2. **The quick draft** = the starting point, made by rules in minutes: the app's *Quick draft now* already made one
   when `build\draft_vN.md` exists (read it: every shot with frame + timecode, its clip and why, the effects, what
   it could not draw); else run `.venv\Scripts\python tools\draft_edit.py <project> --like ... | --preset ... |
   --feel ... --want "..." [--length S] [--format vertical|horizontal|square] [--music <song>] [--sound
   talk|clips|music] --render` (it makes the frame caches first; `--seed N` = another draft). It cuts on the song's
   beats with the style's shot lengths and hook, picks each shot's best unused moment (sharp, exposed, moving as much
   as the style), draws the effects it can (crossfade, dip, flash, zoom-through, push / whip, push-in, shake, freeze,
   stutter, speed ramp, RGB split, light leak) at the style's rate; talking mode keeps what is said in order, cuts
   the pauses (with `--stumbles on`, 0.6.0, for a loose off-script take: also fillers, a phrase said twice, retakes,
   "cut / again" said to the edit, listed with numbers in `draft_vN.md`, `--keep-stumbles 2,5` puts some back),
   punches in on every other cut, lays B-roll (clips nobody talks in) over the talking.
3. **Make it good** (what rules cannot): look at the draft's cut-sheet (`render_video.py build\plan_vN.json --cuts`;
   `--sheet 0:<last>:12` for every 12th frame); then **the edit as a list** (0.5.3, the usual way): a few lines in
   `build\edit_v<N+1>.list` - `cut f120-f188`, `punch-in 1.2 at f300`, `shot 4 tight`, `hold f380-f404`, `caption
   clean_box script script-005`, `graphic <template> at f1524 for 48 text="..."`, `sfx whoosh on punch-ins`, `layer
   {...}` for a one-off (`motionlab\editlist.py` lists them all; every frame = the draft's frame, cuts applied last)
   -> `tools\draft_edit.py <project> --apply build\edit_v<N+1>.list` = `plan_v<N+1>.json` (a talking edit's sound cut
   again and its voice levelled, captions in the script's own words at the said times, graphics from templates).
   **Moves** (zoom-throughs, whips, pushes, zoom in / out, shakes): only where the picture really changes (another
   scene, a card, B-roll), never between two shots of the same take, at most one every ~3 s (a talking video: one
   every ~8 s), and on a face a soft one (a zoom-through to ~1.25x, not 1.6x); the sentence changes of a talking take
   are plain cuts or a static punch-in. The user, 2026-10-23, of a talking edit with a zoom-through at every
   sentence: "it makes too many whip pans or zooms ... it's very weird". `build.py` flags both (`camera moves:`).
   Write `build\edit_v<N+1>.py` (loads the draft's plan and changes it in code) only for what a list cannot say.
   Graphics come from the Motion Graphics templates (`graphic` lines; a column or a pill beside the head on a
   talking video), varied (the user, 2026-10-26: the same templates video after video): the brief's *Motion
   Graphics templates* names options and what the newest videos used - each template once a video unless a repeat
   is the point, a recent one only when clearly the best fit, and look past the first match (`templates.py pick
   "<what it shows>" --n 8 --fresh`) - a custom HTML design (`overlay.py new` from zero) only when the user asks for one: the
   What's new 0.5.3 edit (2026-10-23) spent 20 minutes designing eight cards and 11 more rendering them. Aim
   for: a story - the strongest moment first (the hook), then build to the end; better moments where a pick is weak;
   the effects the style is known for, rebuilt as its examples say (their "how it was made"); captions in the
   style's look (`tools\speech.py` + `overlay.py captions`, `graphics.md`) and text / graphics where the references
   have them (`overlay.py new`); the colour (`plan["grades"]`) if the style has a look. Show the user the shot list
   (frame + timecode), build (`render.md`), iterate. The clips' boards when you need to see every clip:
   `tools\storyboard.py <project>` (`copy.md` section 1).
4. If `resolve` was asked: option 2 (`render.md`) once the user approves the lab render.
5. Tell the user what came from which reference ("the zoom-throughs on the drops are from <title> f564
   (00:00:18:24)") and what is approximate.

## From a prompt - `prompt:<id> <project>` (the app's *How did it turn out?*, 0.3.3)
A video from a prompt of the library (`prompts(id=...)`; its `tags` say what it is for). By kind:
- **brief** = the user's own instructions for the whole video (length, feel, footage, order, pacing, colour, music,
  SFX, graphics, transitions, captions, where it ends up): follow it part by part with the lab's tools, ask its
  "questions first" part (and anything it leaves vague - its check in the prompt library lists them) in one message
  before building, say plainly what the lab cannot do yet instead of faking it, and write the result where the brief
  says (a Resolve project only through `resolve_build.py`, docs\resolve_notes.md); a `style from your reference
  <name>` line (the card's *Style like*) = match that analysis' measured pacing (cuts / min, typical shot, the first
  3 s), its effect families (copy the ones the user marked correct: `events(<name>)`) and its look (`frames(<name>,
  ...)`) with the user's own clips - its style, never its content.
- **script / hook** = a talking video - the user films it and adds the recording (the script card's *Film it*,
  2026-10-15: it is copied into the project and linked in `made_from.json`; `build\edit_request.json` has the format /
  length they picked, "length_s" null = all they said), then speech to text (`tools\speech.py`) and **follow the
  script**: line it up with what was said (the script's lines from `script.cue_cards(text)`), keep the best take of
  every line (a repeated sentence = a retake: the later, cleaner one, unless it is worse; when the take wanders off
  the script, `tools\speech.py stumbles <take>` lists its fillers, repeats, retakes and "cut / again" with frame +
  timecode), tell the user which script
  lines are missing or changed (frame + timecode), and put the script's `[TEXT]` / `[B-ROLL]` / `[ZOOM]` / `[SFX]`
  notes on the words they belong to; captions (`overlay.py captions`) and graphics from the words (the
  `talking-head-pack` example: beats from the transcript, `overlay.py fit`), an edit plan.
- **shot / image** = for a video / image model - write the variants with `/write-prompt` (text only, the user
  generates them on the site), then edit what they drop into the project.
Ask once what is missing (length, format, music). Same hard rules.
