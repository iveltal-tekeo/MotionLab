# /analyze-reference - several videos in one window

Read after SKILL.md section 0; each video follows `review.md`.

## Batch (`/analyze-reference batch <id>`, 0.4.5 - the app's *Add videos* with Claude's check, or *Continue the batch*)
The app measured several videos and opened ONE window for all of them (the user, 2026-10-15: "bulk analyze ...").
1. Read `.app\batches\<id>.json`: `items` = analysis folder names, in order. Section 0 (the lessons, the summary) once
   for the whole batch, not per video.
2. Skip every item whose `analysis\<name>\review.json` already exists (done in an earlier window - say so in one line).
   An item with `review_parts\` but no `review.json` was stopped half-way: continue it first, from its parts.
3. The rest, one at a time and completely: `review.md` sections 2-3 for that video (every contact sheet - helpers for videos with
   more than ~20, one video's helpers at a time; review.json with its
   `_breakdown` and `_near_misses`, `report.py <name>`) before you start the next - so a stop (a limit, the window
   closed) loses at most one video and *Continue the batch* starts at the next. Name the analysis folder in your tool
   calls as you work (paths, `report.py <name>`): What it took splits this window's time per video by it.
4. After each video: one short line ("3 of 8 done - <title>: 14 effects, 2 possible misses kept"); at the end the
   `review.md` section 3 report per video, short, then what the batch has in common (pacing, the effect families, the hooks).
Keep it lean across videos: don't re-read the lessons or tool docstrings per video.
