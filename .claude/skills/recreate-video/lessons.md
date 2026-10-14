# Lessons learned making videos (edits, graphics, generated videos)

<!--
Rules for MAKING videos. /recreate-video and /generate-video read this whole file (and this PC's
knowledge/local/lessons_making.md) before an edit, a graphic or a generated video, and apply every rule.
Format for each rule:
  - [M###] (YYYY-MM-DD, from <project> <version>[, frame + timecode]) <concrete, checkable rule>
    Why: <what went wrong, measured>   Tool: <the tool or helper that does it, or "none">
This file is SHARED and REVIEWED: new rules are first written to knowledge/local/lessons_making.md (ids
local-make-N, from `tools\knowledge.py next-lesson-id --kind making`) on the PC where they were learned, shared to
knowledge/incoming/<author>-<when>-making.md, then reviewed into here with the next M number
(docs/knowledge_sharing.md). How a reference's effects are judged is the other file:
.claude/skills/analyze-reference/lessons.md (L###).
-->

- [M001] (2026-10-14, from illdari_test_copy_1 v1 -> v2) Draw a graphic that copies a reference at the reference's
  measured size: measure its elements on the reference's frames (bar width, card size, title height in px, in the
  output frame's pixels) before drawing, and put one snapshot next to the reference frame before any render.
  Why: v1 drew the app ~40 % smaller than illdari's reel; the user rated the graphics "too clunky". v2 at the
  measured size (bar 640 px, cards 814 x 205, 44 px titles) fixed it.   Tool: `frames(<ref>, ...)` (MCP),
  `overlay.py snap`
- [M002] (2026-10-14, from illdari_test_copy_1 v2) Level every sound effect against the song under it (the song's
  RMS where the effect sounds + a dB offset per kind of effect, with a floor), never one fixed volume for all: the
  song was -25 dBFS in the intro and -8.5 dBFS after the drop, so a fixed level is lost in one place and too loud in
  the other. Claude cannot hear: measure, and ask the user to listen.
  Why: v1 had no sound effects ("no sfx at all", rated bad); one fixed level for all effects cost a round, levelling
  each against the song worked first time.   Tool: `projects\illdari_test_copy_1\build\sfx_v2.py` `level()` (the
  worked example)
- [M003] (2026-10-14, from illdari_test_copy_1 kidwild_top3 f530 (00:00:17:20)) In a HyperFrames graphic, end every
  tween half a frame early and set a tween's start pose at AT(f0) - always, so a plain render, a render with motion
  blur and a snapshot show the same frame. A tween that ends exactly at F(n) is still running after a set at AT(n)
  on the same property and undoes it.
  Why: a zoom tween ending at F(530) undid the set at AT(530): the scene stayed zoomed until f561 (00:00:18:21) in
  the render, and motion blur (sub-frames at +-0.4 frame) made it worse.   Tool: the helpers set / to / ft of
  `overlay.py new`'s template (since 2026-10-14)
- [M004] (2026-10-14, from illdari_test_copy_1 v2 f113-f116 (00:00:03:23-00:00:03:26)) Before rendering with motion
  blur, work out each fast move's pixels per frame (distance / frames, at the ease's fastest frame): over ~60 px a
  frame, N sub-frames show N separate copies - add a smear along the move for those frames, or a gentler ease
  (power3, not expo).
  Why: the search bar and the cards flying in at f113-f116 showed 5 copies with 5 sub-frames; a vertical blur
  pulse on the moving layer merged them into one smear.   Tool: `smear()` in `overlay.py new`'s template
