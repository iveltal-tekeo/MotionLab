# /recreate-video improve <project> - the next version from the user's review

Read after SKILL.md; then `render.md` (the build). The user watched the newest render on its Review tab, rated it per
part and pressed *Send it to Claude*.

- Read `projects\<project>\build\outcome.json` (the user's good / ok / bad + notes per part: sound, sfx, colour,
  captions, graphics, effects, pacing, overall) and `made_from.json`; keep what was rated good, change what was rated
  OK / bad as the notes say (a new edit version, never overwrite the last one); when the video came from a prompt,
  add what worked / failed to that prompt's result note (`prompts.py rate <id> ... --note`).
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
