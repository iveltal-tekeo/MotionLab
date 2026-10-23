# Claude's time on videos: a review (2026-10-23)

The user's ask (2026-10-23, after `/generate-video request ae_50_test`): review every video Claude made or edited in
this lab, this one included, against the 0.5.3 plan (*Faster videos*, docs\plans.md) - what to improve, what the PC
can take over, and what information or prompts would give the same result in less of Claude's time. Quality first:
nothing below may lower the user's ratings (knowledge\local\memory: a part rated bad once is a rule).

Sources: `tools\usage.py sessions --all` and `usage.py project <name>` (What it took, 0.4.4), the docstrings of every
`projects\<name>\build\edit_v*.py` (each records the rounds it cost and why), the lessons (M001-M004, local-make-1 to
-18), the user's ratings (`outcome.json`), and the step-by-step timeline of the ae_50_test session (this chat).

## 1. The numbers so far

Minutes = Claude's own windows (What it took); the lab's render time is extra, not counted by usage.py when the render
runs from Claude's shell.

| Video | Kind | Length | Claude min | Tokens | Rounds / versions | Notes |
|---|---|---|---|---|---|---|
| illdari_test_copy_1 (Opus xhigh) | from zero, hand-written HTML | 25 s | 36.1 + 90.4 (v2) | 21.2 M + 79 M | 3 sessions | the first one; v2 = sound + size fixes (M001, M002) |
| illdari_test_copy_2_fable_high | from zero, hand-written | 25 s | 20.8 | 8.2 M | 1 | reused copy_1's files |
| test_0.4.5_motionlab_graphics | from zero, hand-written | 30 s | 50.4 | 26.5 M | 2 windows, 13 rounds | the detached-render gotcha (local-make-6) cost 4 launches |
| saas_motionlab | from zero, hand-written | 20 s | 15.1 (v1) | 6.7 M | 2 versions | v2 = a song + motion blur, no graphic change |
| test_0.5.0_motionlab_graphics | from zero, templates | 20 s | 28.3 | 16.0 M | 1 | the first reel from Motion Graphics templates; 3 snap rounds on the wipe / hook (local-make-11) |
| 0.5.1_test_motiongraphics | from zero, templates | 20 s | ~25 | ~10 M | 1 | in-points measured on 72-frame sheets (local-make-14) |
| **ae_50_test** | from zero, AE templates | 30 s | **27.3 + the final round** | 10.8 M | 2 windows | 0 lines of animation code; 22 snap calls, ~150 stills |
| testing_entire_workflow | talking edit | 51.9 s | 38.5 | 8.7 M | v1-v3 | 16 min lost to two polling loops that never ended |
| What's new 0.4.3 | talking edit | 25.7 s | 24.5 | 8.3 M | 1 | the video rendered 5x, captions 4x, sfx 4x |
| What's new 0.5.0 | talking edit | ~25 s | 16.0 | 10.0 M | v1 + v2 | |
| 92 logos built in | talking edit | ~20 s | 21.4 | 8.1 M | 1 | |
| What's new 0.5.1 and 0.5.2 | talking edit | ~19 s | 56.5 (three versions) | 21.6 M | v1, v2 (review), v3 (New edit) | ~19 min a version |

Read as a rate: **a video from zero costs 0.6-1.0 min of Claude per second of video, a talking edit 0.5-0.75**; the
0.5.3 target is 0.17 (10 min per 60 s). Two things stand out against the 2026-10-15 analysis in 0.5.3:

1. **Templates removed the code, not the minutes.** The hand-written reels (saas 15 min, illdari copy 2 21 min) and
   the template reels (test_0.5.0 28 min, ae_50_test 27 min) cost the same. ae_50_test wrote no animation code at
   all; its minutes went to reading the lab's context (~70 k tokens before the first decision), 22 snapshot rounds
   to learn where each template's move lands and whether its words fit, and ~10 turns of orchestration (12 renders,
   the plan, the sound pass, the precheck, a failed detached launch, two waits).
2. **The version loop is the other half.** What's new 0.5.1 and 0.5.2 took three versions of ~19 min each; two of the
   three came from the user's ratings (colour, graphics, pacing, sound). A better first guess (section 4) and cheaper
   versions (a settings change, not a rebuild) matter as much as a faster first build.

## 2. Where the minutes went in ae_50_test (this session, measured on the chat)

| Phase | Turns | Claude's time | What it was |
|---|---|---|---|
| Read the lab | 10 | ~5 min, ~70 k tokens in | request, memory (13 KB), 22 lessons (24 KB), graphics rules, HANDOFF, the 110-template dump (14 KB), the closest style, 5 tool docstrings, the review log |
| Decide | 1 | ~3 min | horizontal, the song, 12 scenes on the downbeats, template per scene, the words |
| Snapshot rounds | 22 calls, 17 sheets looked at | ~7 min | find each move's frame for the in-point (10 scenes), text fit (3 fixes: the hook's last word, step 3 clipped, the torn-paper tile), one wasted size test (vertical) |
| Plan, sound, precheck | 6 | ~4 min | edit_v1.py, sfx.py plan (74 cues), the precheck (55 buried cues -> a levelling script), the lesson |
| Renders | 7 turns | ~8 min plain + ~13 min motion blur of PC time, Claude waiting or re-launching | 12 compositions one after another; the detached launch failed once on PowerShell quoting |

Of the 22 snapshot calls, 13 asked a question the template's own data already answers (`template.json` "tracks":
`shatter start_f 80`), 3 asked "does the text fit" (a pixel check), 1 was the vertical test (a fact a table could
hold), and 5 were real looks (the hook, the how-to, the plain composite at the cuts). So ~16 of 22 can be the PC's.

## 3. What the PC can take over (no change to the result)

Each item: what Claude did by hand, the tool that does it, the saving measured on the videos above, the risk.

1. **Template landing from its tracks** (`templates.py land <id> --window N --at <frame>` or `overlay.py new --from
   <id> --land "<track>@<plan frame>"`). Every one of the 110 AE templates (and the repo's 76) records its moves as
   tracks with `start_f` / `length_f`; the in-point that puts "shatter" on the beat f172 of a cut at f136 is
   arithmetic (in = 80 - 36 = 44), not a sheet. Saves ~10 snap rounds (~4 min, ~25 k tokens of pictures) per
   template video; local-make-14's measured in-points become unnecessary. Risk: none (the tracks were measured when
   the template was finished; a wrong track shows on the one cut-sheet that stays).
2. **A text-fit check in every snapshot** (`overlay.py snap --fit`, also inside `templates.py check`): on the
   snapshot, ink touching the frame's edge, a text box wider than the frame, two text elements overlapping -> a flag
   with the frame, the element and how much. Caught by eye three times this session (the hook's "in MotionLab" at
   260 px, "Render, or send to Resolve" off the right edge, the torn-paper headline under the bottom edge), each a
   round. Saves 2-3 rounds a video (~2 min). Risk: none (a flag, not a change).
3. **A size table for every template**, made by the PC in bulk (`templates.py check <id> --size 1080x1920` and
   `1080x1080` for all 110 + 76, overnight, `sizes_ok` written into template.json / index.json; the failures listed
   for a batch agent). ae_50_test lost its first round to this (the shatter template drew no word at 9:16) and then
   had to be horizontal. Saves the test and unlocks vertical videos from the AE library. Risk: none.
4. **Sound levels that pass the precheck first time** (`sfx.py plan --floor-vs-song -24`, or the precheck's "buried"
   rule inside sfx.py): the templates' cues carry `db` offsets of -9 to -13 designed on a quiet reference; under a
   loud song 55 of 74 cues sat 26-29 dB under it and the precheck flagged them all. A measured floor (M002's rule
   already levels each cue against the song) removes a sound round (~2 min) per video. Risk: the user's "spamming
   sfx" note (0.5.1/0.5.2 v1) is about count and sameness, not level - unchanged.
5. **One build command for Generate too** (0.5.3 step 2, `build.py <project> plan_vN.json`): render every
   composition the plan names (plain, in parallel), composite, precheck, the cut-sheet (a still at every layer
   boundary and every cue frame, frame + timecode), a 10-line summary; `--final` = the motion-blur renders detached
   with HYPERFRAMES_RENDER_DETACHED set by the tool, the composite, the precheck again, one "done" line. This session
   spent 7 turns and a failed PowerShell launch on exactly this; local-make-6 and -11(3) stop being lessons Claude
   must remember. Saves 5-6 turns (~3-4 min) and the launch gotcha. Risk: none.
6. **Parallel and partial overlay renders** (0.5.3 steps 1 and 3): the 12 motion-blur renders ran one after another
   (450 sub-frames in 47 s, 240 in 31 s: ~0.1-0.13 s a sub-frame on this PC - i5-13600KF, 20 threads, RTX 4070,
   HyperFrames in hardware GPU mode); three at a time would cut the ~13 min pass to ~5. Motion blur only on frames
   that move (3f): ~40 % of this video's frames are holds. Measure first (Chrome and the GPU are shared). Risk: none
   to the picture.
7. **The cut-sheet as a tool** (`render_video.py <plan> --cuts`): stills at every layer boundary + every cue frame,
   labelled. Written by hand this session (`build\checks\stills_sheet.py`), one turn each time it is needed.
8. **A Generate quick draft by rules** (0.5.6 step 7, the biggest one): beats -> scene changes on downbeats, the
   biggest change on the drop; scenes = templates from `templates.py pick` matched to the request's words, landed by
   their tracks (item 1); the words = the request's text lines; the end card and the hook from the kind; the plan,
   the compositions and the sound pass written with no Claude. For ae_50_test the rule-made draft would have
   produced the beat grid, the 1-bar montage, the how-to block and the end card; Claude's value was the words and
   which template says what - ~3 min of a 27-min session. Claude then edits a scene table, not a build.

9. **The motion-blur copies check at finish time** (`templates.py finish` runs `precheck.py --motion-blur 5` on the
   template's render): ae_50_test's final shows stepped copies where a template's own move crosses 200-270 px a
   frame (the colour stripes f330-f344 (00:00:11:00-00:00:11:14), the end title rising f818-f822
   (00:00:27:08-00:00:27:12)); these templates drive their moves in a per-frame `render(t)` callback, so the fix is a
   smear inside the template (local-make-11(4)), found once by the PC when the template is finished, not by Claude in
   every video that uses it. Risk: none.

Not a sub-agent: a cheaper model doing the snap-and-check loops costs tokens and still reads pictures; items 1-4 are
deterministic and free on the PC. (The user's rule for the AE batches, one agent at a time, stays.)

## 4. Information and prompts: the same result in less of Claude's time

1. **A Generate brief in one command** (0.5.3 step 4, `brief.py <project>`): the request with its blanks filled by
   the lab's defaults - format (the templates' native size when the request has none; what the user picked last
   time), the song (the one used in the last reel, with `beats.py` already run from the same start), the look - the
   template catalogue filtered to the request's words (id, what, key moves with frames, sizes ok, text slots: 2-3 KB,
   not 14), the beats, the lessons tagged for this kind, the ratings-as-rules block (1.5 KB) instead of the whole
   memory (13 KB). This session read ~70 k tokens to make five decisions; a brief is ~8 k.
2. **The request form asks what Claude otherwise guesses**: format, song ("the one from last time" as a button),
   palette / look (Editorial warm / Swiss signal / Night edition / the app's colours), the number or words that must
   appear. Every blank is a guess and a note in the chat; a wrong guess is a version (~19 min). The 2026-10-22 note
   "always the same color palette" was one such guess.
3. **Lessons by kind**: 22 lessons (24 KB) are read before every video; most are about talking edits (voice levels,
   captions, screen recordings). Tag each `kind: talking | generate | templates | all` and read the matching ones.
   Roll the stable ones into tools so they stop being text: local-make-6 (the detached launch) -> build.py;
   local-make-11(1) (shape-wipe's minimum length) -> the template refuses shorter; local-make-12 / -14 (in-points) ->
   item 3.1; local-make-18(3) (cue levels) -> item 3.4.
4. **Claude's memory in parts**: `knowledge.py memory --rules` (the ratings block alone) for Generate, like
   `--styles` for scripts; the effects list (8 KB) is for edits that copy a reference.
5. **The first message carries the decisions already made**: the app's window opens with "request ae_50_test"; it
   could open with the brief's one-paragraph summary (format, song, look, the number of scenes the beats give), so
   Claude starts at the scene table.
6. **Effort per task**: this video ran at Fable high with the plan's reasoning being the only part that needed it;
   the snap-and-check loops run the same at medium. Once items 3.1-3.5 exist, Generate's window can default to
   medium with xhigh for a new kind of video (0.5.3 step 8, the user's call).

## 5. What stays Claude's

The words on screen and their order, which template says what, the scene table's rhythm against the song, the one
look at the cut-sheet before the final, the user's notes turned into the next version. These were ~5 min of the 27
and they are where the ratings come from (graphics good 3x, title good 2x).

## 6. Against the 0.5.3 plan

- **Confirmed**: steps 1 (waits), 2 (one build command), 4 (the brief), 6 (one look), 7 (leaner context), 8 (effort).
- **Changed**: the from-zero path's bottleneck is no longer "~42 KB of animation code per video" - the Motion
  Graphics library (0.5.0) and the AE templates removed it (ae_50_test: 0 lines). It is now the checking (section 2:
  16 of 22 snapshot rounds answerable by the PC) and the orchestration (7 turns). Add to 0.5.3: **template landing
  (3.1), the text-fit check (3.2), the size table (3.3), sound levels that pass first time (3.4), the cut-sheet
  (3.7)**; move 0.5.6's quick draft for Generate (3.8) forward, it is what takes the from-zero path under 10 min.
- **Order suggested**: 3.1 + 3.2 + 3.4 (small, each removes rounds this session paid for) -> 3.5 with 3.7 (the build
  command) -> 4.1 + 4.3 (the brief and the lessons by kind) -> 3.6 measured -> 3.8.
- **Expected** for a request like ae_50_test after 3.1-3.5 and 4.1: read the brief ~1 min, decide ~3 min, one
  cut-sheet look ~2 min, the final ~1 min = **~8-10 min of Claude** (from 27), the PC ~8-10 min in parallel
  (plain + motion blur, three at a time), in ~10 turns instead of ~45. A talking edit keeps 0.5.3's estimate
  (10-12 min for 60 s) once step 5 (the plan as an edit list) exists.

## 7. How to know it worked

Re-run this request (`generate_request.json` of ae_50_test) after each pair of items; `usage.py project ae_50_test`
gives the minutes and tokens of each run; the user watches old | new side by side (`compare_renders.py`) and rates
the new one on its Review tab. The 0.5.3 test videos (testing_entire_workflow, What's new 0.4.3) stay the talking
benchmark. No item ships if a rating drops.
