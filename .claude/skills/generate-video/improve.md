# /generate-video improve <project> - the next version from the user's review

Read after SKILL.md; the build is `from_zero.md`'s. The user watched the newest render on its Review tab, rated it per
part and pressed *Send it to Claude*.
1. Read `projects\<project>\build\outcome.json`: `"aspects"` = good / ok / bad + a note per part (sound, sfx, colour,
   captions, graphics, effects, pacing, packaging, overall); `"moments"` (older notes on single frames: fix exactly
   those, each named with frame + timecode); `"next"`: `"fix"` = a new version with the notes (the feel is right),
   `"start_over"` = the feel is wrong - back to `from_zero.md`'s step (1), the plan in words, in a different feel (or
   the looks A / B / C), never a v2 of a feel the user did not want. Then what was asked (`build\brief.md`,
   `generate_request.json`) and what was made (the newest `plan_vN.json`, its compositions in `build\overlays\`,
   their settings and sound cues).
2. Keep what was rated good. Change what was rated OK or bad the way its note says (the note wins over your own idea;
   a bad part with no note: name the fix you will make in one line before building).
3. Build it with the same flow - the same templates and compositions (their settings first: `overlay.py settings` /
   `set`; new code only where a setting cannot do it), cheapest check first (the snap sheet, one plain `build.py`
   and its cut-sheet, then the final once, as a job), the sound cues again - as `plan_v<N+1>.json` ->
   `<project>_v<N+1>.mp4`. Never overwrite the old render or its plan (the user compares them; Review rates the
   newest). **A version that changes only settings** (words, colours, the look, the song, the sound): copy the
   compositions (`overlay.py new <new folder> --from <old folder>` keeps their settings), `set` what the notes ask,
   then `build.py` - it renders only the graphics whose inputs changed.
4. Tell the user what changed for each part they rated (frame + timecode where it shows) - and that the video's
   Review tab rates the new version.
