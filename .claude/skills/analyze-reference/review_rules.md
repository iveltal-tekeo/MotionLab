# How to review an event - /analyze-reference section 2 steps 1-3, the review.json format, the canonical types

The one home of these rules: the main window reads this file in section 0 of SKILL.md, and every helper reads it
instead of the whole skill (SKILL.md section 2, *More than ~20 sheets: helpers read them*). Steps 4-6 of section 2
stay in SKILL.md.

## Section 2, steps 1-3
Open `analysis\<name>\review_todo.md`. With the `motionlab` MCP tools (0.3.0; `mcp__motionlab__*`), use them instead
of reading files: `events` (one line per event, filters by type / frames / unreviewed), `event` (evidence + auto
draft of one), `sheet` (its contact sheet as a picture), `frames` (any frames, e.g. around a possible miss) - never
read the whole `events.json` (~0.7 MB). For **each** event, in order:
1. **Read every contact sheet** listed for it (`sheet`, or the Read tool on each `events\<ID>\sheet_NN.jpg`). Tiles are labelled
   with frame number, timecode and a per-frame measurement (L = luma %, xN = scale per frame, %B = transition
   progress, Npx = RGB offset, %/f = motion speed, =N = repeats frame N). Yellow border = effect frames, grey =
   3 padding frames. CUT / BEAT / BAR / DROP flags mark cuts, beats, bar starts and drops.
2. Read the event's measured evidence and auto draft (`events.json` > `events[i].auto`, or the todo table).
3. Decide and write, for the event:
   - **type** (one canonical key, list below; use `unknown` rather than forcing a category) and **what**: what
     happens frame by frame, citing frame numbers;
   - **origin** `post` / `camera` / `unclear` + **origin_why** (real camera move vs effect added in post, and why:
     e.g. a pure 2D scale with no parallax = digital zoom in post);
   - **easing** in unambiguous words ("accelerating (slow start)", "decelerating (slow end)", "S-curve", "linear",
     "instant"), plus duration / timing if your reading differs from the measured draft;
   - **confidence** `high` / `medium` / `low`;
   - **rebuild**: one short paragraph - which Resolve tools / Fusion nodes, with the measured key values
     (frames, scale, pixels, durations, easing) plugged in.
   Use only measured numbers from the evidence; if you see something the measurements do not cover, say it is a
   visual observation and lower the confidence. If the event is not an edit effect at all (camera, lighting,
   subject motion), set `"false_alarm": true` and explain in `what`. If you notice an effect the pipeline did not
   flag (e.g. in the padding frames), mention it in `notes` and in your summary.

### review.json format
```json
{
  "_meta": {"reviewer": "Claude", "reviewed": "YYYY-MM-DD", "lessons_applied": ["L001"]},
  "E004": {
    "start": 480, "end": 482,
    "type": "flash_white",
    "what": "f479 is the last frame of shot A; f480 is fully white (the cut is hidden under it); f481-482 fade back ...",
    "origin": "post",
    "origin_why": "the whole frame, including the darkest areas, goes pure white over a cut",
    "easing": "instant attack, linear decay 100 > 66 > 33 > 0% over f480-483",
    "confidence": "high",
    "rebuild": "Cut at 480 on the drop; white Solid Color on V2 480-482, Opacity 100% > 0% by 483, linear ...",
    "notes": "optional"
  },
  "_near_misses": {"270": "not an effect: the singer turns into the light"},
  "_breakdown": {"name": "Neon kinetic-type promo for a studio", "summary": "...",
                 "hook": "f0-89 (00:00:00:00-00:00:02:29): ...", "structure": ["...", "..."],
                 "rebuild_tips": ["...", "..."]}
}
```
Optional keys: `"false_alarm": true`, `"evidence": [...]` (only to ADD observations; measured evidence is kept),
`"stacked": ["blur", ...]` (other effects that really happen inside this event - a reviewed `type` replaces the
detector's stacked types, so list the ones you confirmed; they count in the report header),
`"on_beat"` / `"on_drop"` (true/false - set them when the effect's real key frame differs from the detected range,
which is what the table's Beat column is computed from), `"duration_text"` (when the real extent differs) and
`"sub"` (a short sub-label; a re-typed event otherwise shows none).

### Canonical types
`hard_cut jump_cut flash_white flash flash_black dip_black dip_white fade_in fade_out crossfade zoom_transition
zoom_in zoom_out whip_pan spin shake speed_ramp freeze stutter frame_repeat strobe rgb_split glitch blur
flash_color invert sat_pop light_leak split_screen mirror multi_screen text wipe mask_reveal luma_fade push_slide
unknown`
