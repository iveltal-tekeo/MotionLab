# /recreate-video improve <project> - the next version from the user's review

Read after SKILL.md; then `render.md` (the build). The user watched the newest render on its Review tab, rated it per
part and pressed *Send it to Claude*.

- Read `projects\<project>\build\outcome.json` (the user's good / ok / bad + notes per part: sound, sfx, colour,
  captions, graphics, effects, pacing, overall) and `made_from.json`; keep what was rated good, change what was rated
  OK / bad as the notes say (a new edit version, never overwrite the last one); when the video came from a prompt,
  add what worked / failed to that prompt's result note (`prompts.py rate <id> ... --note`).
- The clips: `build\clips.json` when there is one (0.6.1, `tools\catalogue.py show <project>`) - every moment with
  its line, usable part and look-alikes, written once; a shot to swap = another moment from it, never a new look at
  every clip. A clip added since: `catalogue.py make` again (the lines stay), then `sheets --todo` for the new ones.
- **Fixed by hand** (0.6.0, the Editor tab): `outcome.json` `"hand_fixes"` (and that version's `edit_vN.list`) =
  what the user trimmed, moved, split, sped up / slowed, deleted, added (sounds, templates) or reworded themselves - build on that version, never undo those changes, and
  treat them as lessons (a cut Claude placed 5 frames late, a sound on a word, a caption mis-heard). Since 2026-10-26
  the Editor also keys a shot's zoom / dx / dy / rotation / opacity / anchor (plain curve keys - keep them) and puts
  transitions on cuts: `"trans": {"kind", "len", "dir"}` on the shot after the cut, drawn by `tr_<shot>_*` layers
  (`"tr"`) that `motionlab\edtrans.build` makes again after every change (draft_edit.py does it too) - change the
  `"trans"`, never the `tr_` layers.
- **Notes on moments** (0.4.2): `"moments": [{"f": 113, "version": "v2", "aspect": "graphics", "note": "...",
  "date": "..."}]` = notes the user put on single frames of a render (frame of that version; the app stopped taking
  new ones on 2026-10-15 - the per-part ratings sit beside the render now - but saved ones still count). Fix exactly
  those moments, each named with frame + timecode (`f113 (00:00:03:23)`: what you changed), instead of reading one
  word per part; say which moment the new version fixes and how.
- **Fix or start over**: `"next": "fix"` = a new version with the notes (the feel is right, details are wrong);
  `"start_over"` = back to step 1 of *cheapest check first* or to feel tests (`by_feel.md` step 0) - never a v2 of a
  feel the user did not want.
- **A version that changes only settings** (words, colours, the look, the song, the sound): change the graphics'
  settings (`overlay.py set`) and the plan's audio / cues, then `build.py` - it renders only the graphics whose
  inputs changed and skips the rest.
- In every mode the ratings of ALL the user's videos are rules (`knowledge.py memory --rules`): a part rated bad once
  is a default.

## Finish a quick draft (`finish <project>`, 2026-10-24)
The user liked the quick draft's cuts and pressed *Finish it with Claude* on the video's page (the user: "it worked
good and actually made some good cuts and transitions but then what? how do i tell him to go next step which is some
motion graphics and stuff?"). `build\outcome.json` has `"next": "finish"` and `"finish": {"add": [...], "words":
"...", "from": "v1", "date"}` - `add` = what to put on it: `graphics` | `captions` | `sfx` | `colour`; `words` = their
own words (may name other things - follow them); `from` = the draft version they watched (else the newest render's).
- **Keep the draft's edit as it is**: start from `build\plan_<from>.json` (+ `draft_<from>.md`: every shot with frame +
  timecode) - every cut, shot, transition, punch-in and the timing stay; no new cuts, no moved shots, no new camera
  moves, unless `words` asks for them. Rules made the cuts; the user approved them by pressing Finish.
- **Add only the layers in `add`** (and what `words` asks), as an edit list on the draft (`by_feel.md` step 3):
  `build\edit_v<N+1>.list` with `graphic` / `caption` / `sfx` lines -> `tools\draft_edit.py <project> --apply
  build\edit_v<N+1>.list` = `plan_v<N+1>.json`. Graphics = the Motion Graphics templates (`graphics.md`; a talking
  video: a column or a pill beside the head, never over the face) where the script / `about` / `on_screen` put them;
  captions in the request's `style.captions` (a talking video: the script's own words at the said times); sound
  effects at the request's `sfx` amount and kinds (`render.md` *The sound*); colour = one look in `plan["grades"]`
  (the references' or the request's mood; a draft that already matched the references' colour keeps its LUT under
  it). The request's `style.palette` colours every title, caption and graphic. What is not in `add` stays as the
  draft has it (no captions / sound effects the user did not tick). A quick draft since 0.5.4 has its sound effects
  already (the plan's `"sfx"` = {amount, kinds, first}, its `"audio"` = the mix; the dialog then lists them under
  *Stays*): every build remakes them from the plan, the new graphics' cues with them - nothing to add.
- `build\brief.md` holds the request in words (the script word for word, the words on screen, the palette, the sound
  effect kinds; `tools\brief.py <project>` when it is missing or older than `edit_request.json`) - read it, not the
  JSON again.
- One build (`build.py <project> build\plan_v<N+1>.json [--sfx]`), fix what it flags, then tell the user what was added
  where, each with frame + timecode, and that `from` stays as it was.
