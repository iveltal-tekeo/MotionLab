# /analyze-reference - analyse one video (the lab pass, every event, the report)

Read after SKILL.md section 0 (the lessons, the summaries, the hard rules, `review_rules.md`).

## 1. Run the pipeline (skip it when the app already did)
If the request says `the lab pass is done: analysis\<name>` (the app's "Analyse with Claude" / "Send to Claude"
buttons), or `analysis\<name>\events.json` exists and is newer than `tools\config.json`, do NOT run it again: go to
step 2 (re-run only when the user asks or the config changed since). Otherwise:
```
.venv\Scripts\python tools\analyze.py "<path>"
```
Quote the path; add `--category <id>` / `--tags "a, b"` / `--focus content|cinematic|both` when the request names them. It prints progress and ends with
`REPORT:` and counts. Expect roughly 1-2 minutes per minute of 1080p30 video - for videos longer than ~4 minutes run
it in the background and wait for it. It probes (CFR/VFR - VFR gets a CFR proxy), analyzes audio (BPM, beats,
downbeats, drops, builds), measures every frame, detects events, extracts frames, builds contact sheets + looping
previews, and writes `report.html`, `events.json`, `metrics.csv`, `overview.png` and `review_todo.md` into
`analysis\<name>\`. If a run fails, show the user the error, fix the cause, re-run. `--redetect` re-uses the
per-frame metrics cache (use after config changes); `--force` recomputes everything.

## 2. Review EVERY event (the pipeline's types are drafts until you have looked)
Steps 1-3, for **each** event in order - the MCP tools to use, read every contact sheet, read the evidence, decide
and write - are in `.claude\skills\analyze-reference\review_rules.md` (section 0, item 4), with the review.json format
and the canonical types. Then:
4. Write all reviews into `analysis\<name>\review.json` (format: `review_rules.md`; built from `review_parts\`, see "Working
   through the sheets without waste" below). Start each event's entry from `review_draft.json` (0.5.3: the lab's
   measured draft of every event in that format - type, what, origin, easing, rebuild, confidence "unchecked"): after
   reading its sheets keep what they confirm, rewrite what they show differently, set the confidence yourself - the
   draft is never a review. Keep `start`/`end` so reviews survive a re-run that renumbers events. Then run `.venv\Scripts\python tools\report.py <name>` - it must say
   `N/N events reviewed`.
5. **Possible misses** (end of `review_todo.md`): sudden changes no event explains. Look at each (its 3 frames, or
   `tools\sheet.py <name> <a> <b>`) and record a verdict per frame in review.json
   `"_near_misses": {"270": "EFFECT ...: what it is" | "not an effect: why"}`; a real miss also goes into the nearest
   event's `notes` and your summary. The report shows these next to each candidate.

6. **The focus** - what the user asked this analysis to look at (meta.json / events.json `focus`, picked in the app:
   `content` = content creation, `cinematic`, `both`; analyses made before 0.4 have none - treat them as `both`).
   After the events, write the whole-video breakdown into review.json `"_breakdown"`: what makes this video work, so
   you can reuse it when you edit or generate for the user later. Start from the measured lines at the top of
   `review_todo.md` (rhythm, hook, talking, text on screen, signature effects, transitions). Text, or lists of short
   lines; every frame with its timecode; leave out the keys that do not apply:
   - **content**: `summary` (2-4 sentences), `hook` (f0 to 3 s: what is seen, said and written - why it stops the
     scroll), `structure` (the parts in order, e.g. "f0-89 (00:00:00:00-00:00:02:29) hook: ...", setup, payoff, CTA),
     `captions` (their look: font style, size, position, colours, outline, animation, words per caption - from the
     frames), `text_graphics` (titles, numbers, stickers, lower thirds), `broll` (how cutaways are used), `sound`
     (music, SFX, voice), `cta`, `rebuild_tips` (3-6 concrete steps to make one like it with the user's clips). Read
     `analysis\<name>\content\transcript.txt` when it exists (frame + timecode per line); quote at most a few words -
     they are other people's words and the breakdown goes into the shareable card.
   - **cinematic**: `summary`, `transitions` (which, where, how they are built), `camera` (moves; real or in post),
     `grade` (the look: contrast, colour, highlights / shadows - from the frames and `colour\colour.json`:
     `.venv\Scripts\python tools\colour.py <name>` prints the measured look per shot with frame + timecode; say
     where the measured words are wrong - a warm set can read as a warm grade), `rhythm` (cuts vs beats and drops,
     speed changes), `sound`, `rebuild_tips`.
   - **both**: every key that applies.
   - **always**: `name` = 3-6 words a person would call this video, e.g. "Neon kinetic-type promo for a studio" -
     never the file name, a handle or "Video by ..." (the app and Claude's memory show it instead of the file's title;
     2026-10-18, the user: names like "Video by yp.motionstudio" mean nothing to "normal people or my friends").
   Only these keys count: name summary hook structure captions text_graphics broll sound cta transitions camera grade
   rhythm rebuild_tips. `tools\report.py <name>` puts it on the video's Overview page in the app.

Every sheet of every event must be read - by you or by a helper. If `review.json` or `review_parts\` already has
reviews (an earlier chat stopped half-way), keep them and continue with the events that have none - don't redo
finished ones unless the user asks.

### Working through the sheets without waste (the user, 2026-10-15: same quality, less usage)
Every picture you open stays in the chat and is sent again with every later step, so the cost grows with pictures
held x steps taken (a 33 s video once took 14 M tokens: ~80 sheets in one chat, read 3-5 per step, ~45 read twice).
- **Save as you go.** After each batch of events, write their reviews (the per-event entries of the format in `review_rules.md`) to
  `analysis\<name>\review_parts\<first ID>-<last ID>.json` BEFORE you open more sheets. Never keep finished reviews
  only in your head: old pictures drop out of a long chat (a request limit) and reading them again doubles the cost.
  At the end merge all parts into `review.json` with `_meta`, `_near_misses` and `_breakdown`, run `report.py`, then
  delete `review_parts\`. Write `review.json` once, complete: the app takes its existence as "Claude's check done".
- **More than ~20 sheets: helpers read them.** First look at the whole video yourself, text and one picture only: the
  measured lines and table of `review_todo.md`, `overview.png`, and whatever holds for the whole video (e.g. a stepped
  frame rate: the share of repeated frames in `metrics.csv` column `dup`; a recurring graphic). Then split the events
  into runs of consecutive events of ~10-12 sheets and start one helper per run, all in one message so they run in
  parallel (Agent tool, general-purpose). Each helper's prompt: the analysis folder and its event IDs (with the event
  before and after, for context); the whole-video facts you found; read both lessons files and
  `.claude\skills\analyze-reference\review_rules.md` first (not this whole file); every sheet of its events; frame + timecode on every
  frame it names; write its reviews to `review_parts\<first ID>-<last ID>.json` and nothing else (no `review.json`, no
  `report.py`); reply with one line per event (ID, type, false alarm yes / no, confidence) plus what it saw beyond its
  events (an effect running into the next run, a possible miss). Then you: read the parts (text), make the runs agree
  (the same thing named the same way; a move spanning two runs described once and referred to from the other), open a
  sheet yourself only for low-confidence events, runs that disagree and what a helper flagged, then the possible
  misses and the breakdown.
- **Fewer sheets: read them yourself**, 8-10 per step, saving each batch as above.
Plain hard cuts are NOT reviewed visually (they are listed in the cuts table with on-beat yes/no).

### review.json format, canonical types
In `.claude\skills\analyze-reference\review_rules.md` (section 0, item 4).

## 3. Report back to the user
Give: video facts (fps, CFR/VFR, duration), BPM and drops, counts per effect family, the most notable events (with
frame + timecode), the low-confidence events worth checking first, and the possible misses you think are real.
Say in one line what the breakdown found (the hook / the signature). Then tell them the video is ready for their edits
(Editor > New edit can use it), and the optional next step that teaches you, in the MotionLab app: Analyser > this video >
**Effects** (Correct / Partly / Wrong + a note on each; keys 1 2 3, J / K / N to move), the red **Possible misses &
sound** tab, then **Send it to Claude** (it opens a new Claude Code window with the feedback - this chat can be closed). Without the app:
`analysis\<name>\report.html` > Generate feedback > Copy, and paste it into a chat.
