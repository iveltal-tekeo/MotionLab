# /recreate-video - the sound, the build, the final and option 2 (DaVinci Resolve)

Read after SKILL.md and the way's file (copy / by_feel / improve / batch).

## The sound
Sound effects (a part rated bad once is a default - see the ratings as rules): `tools\sfx.py plan build\plan_vN.json`
(+ `--song <file>` when the plan's sound is not the song) puts a whoosh / hit / riser on the plan's zooms, whips,
flashes and speed-ups and the cues of its graphics, levelled against the sound under each (never further under it
than -24 dB: the precheck's "buried" line + 2, so the levels pass first time; its output is a summary and the cues
the precheck would flag, `--all` = every cue); `build.py --sfx` runs it and puts the mix in the plan as `"audio"`
(the effects alone = their own Resolve track). How many and where: the request's `sfx` when the user picked it
(`brief.md` *5. Sound*: the amount, the kinds as the plan's own `cues`, their notes; `none` = no effects), else the
reference's `"sound"` answer (`copy.md`); the precheck checks the levels before the final. A talking video's voice:
the plan's `"sfx": {"voice": true}` (or `sfx.py plan --voice`) - never lowered, and sound effects never over a word or
very subtle (the user, 2026-10-26): over a word sfx.py keeps an effect at least 22 dB under it, in a pause it levels it
against the voice around it - so put a whoosh where the cut has a breath if the picture allows, else it stays quiet.
A plan's `"sfx": {"amount": few | some | many, "kinds": [...],
"first": [drop frames], "song_db": 0, "voice": true}` (0.5.4: the quick draft's `--sfx`, from the request) thins the effects' own
cues the same way on every build - your `cues` and the graphics' are never thinned. 0.6.0: `"bed": {"file": "<music
library ambience>"}` = the room tone / café / street the user picked (`brief.md` *Ambience under the voice*), looped
under the voice 26 dB under its words (`"db"` changes that); `"logo": "<path>"` = My Brand's sound logo plays on the
end card (the layer `end_card`, or one marked `"end_card": true`) instead of its template's own sounds. A song from `refs\` (a download - someone else's song): every build and
quick draft also writes `build\publish\<render>_post.mp4` without it (the effects stem only) and says where the song
starts (the summary's "to post:" line) - tell the user to post that copy and add the same sound in TikTok / Instagram.

## The build and the final
- One plain build: `.venv\Scripts\python tools\build.py <project> build\plan_vN.json [--sfx]` = every graphic whose
  inputs changed rendered (N at a time; a settings-only change renders one), the sound, `render_video.py` (parallel
  processes, ~3x faster; any frame looks the same alone, in a range or in a chunk), `precheck.py` and the cut-sheet
  (`build\checks\<name>_cuts_01.jpg`) -> a 10-line summary (what rendered, flags with frame + timecode, the sheet).
  Read the flags, look at the cut-sheet once, fix, build again (unchanged parts are skipped). 0.6.0: the sound is
  mastered (-14 LUFS, true peak under -1 dBTP - the summary's "sound:" line) and a caption / graphic over the
  speaker's face is flagged ("over the face", measured: the frame without the graphics gives the face) - move it off
  the face (the kit rule: about 90 px of air), or put `"over_face": true` on a layer that is meant to be there (a
  before / after on the face); an upright video's graphics in the platforms' top / bottom bands or right rail are
  flagged too.
- The final only after the user rated the plain build (Editor > Review) - never unasked: a final the user
  then wants changed is its minutes lost twice. Then: `tools\job.py start build project=<project> plan=plan_vN.json
  final=1` (graphics with motion blur 5 - a graphic that hardly moves keeps its plain render, captions always
  render plain: the lines appear and fade, nothing travels -, the video, the
  precheck), then `tools\job.py wait <id>`. A build longer than ~9 minutes refuses to run in the shell and prints
  this job command.
- `render_video.py build\plan_vN.json` alone (a quick render without the checks), `--compare` = reference | render
  side by side.

## Option 2 - the same edit in DaVinci Resolve (only when the user wants it)
Needs DaVinci Resolve **Studio** running with Preferences > System > General > External scripting = Local. Read
`docs\resolve_notes.md` first (the API's gotchas cost hours otherwise). Ask the user once before the first build on
a PC (the LUTs go to `C:\ProgramData\...\LUT\MotionLab\<project>\`). Then `resolve_build.py build\plan_vN.json
--replace`, per section `--render A B` + `compare_renders.py` against the lab render, then `--render-full` +
`verify_timing.py <timeline>`. `resolve_build.py` was made on test_4am: its `SECTIONS` and some builders are
specific to that edit - generalise with care, test in the scratch project. Never overwrite the user's hand edits:
`--doctor` and `--diff` first.
