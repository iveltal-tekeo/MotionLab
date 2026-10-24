# /analyze-reference - apply the user's feedback (MOTIONLAB FEEDBACK)

Read after SKILL.md (hard rules). After it, remind the user of Claude's memory > Shared knowledge > Share my knowledge.

## Applying feedback (user pastes text starting with `MOTIONLAB FEEDBACK`, or gave it in the MotionLab app)
1. Read both lessons files and `review_rules.md` (section 0). Save the pasted text verbatim to `analysis\<name>\feedback\pasted_<YYYYMMDD-HHMM>.txt`
   (Write tool) and run `.venv\Scripts\python tools\feedback.py <name> <that file> --import` (`--import` = pasted
   feedback also goes into `verdicts.json`, where the app keeps the user's verdicts). It archives the feedback and
   prints each WRONG / PARTLY item with the event as it is now and its sheet paths (IDs are re-matched by frames).
   Feedback given in the app is already a file: the newest `analysis\<name>\feedback\app_<date time>.txt` (made by
   its "Send it to Claude" button; `verdicts.json` next to it is the live state) - run `feedback.py` on it (no
   `--import`: the app's own export is in verdicts.json already).
   A note starting with `[save to library]` means the user wants that effect in `library\`. The section
   `--- possible misses ---` holds the user's answer per possible miss: `EFFECT | f<n>` = an effect the pipeline
   missed (with what it is in the note), `NOT AN EFFECT | f<n>` = confirmed nothing.
2. For every WRONG / PARTLY event: open its sheets again and find the exact mistake (type? frames? timing?
   origin? rebuild?). For missed effects, possible misses marked EFFECT, or frames the user mentions, look with
   `.venv\Scripts\python tools\sheet.py <name> <start> <end>` (contact sheet + preview of any range); a miss your
   own `_near_misses` verdict called "not an effect" but the user calls an effect is a lesson candidate.
3. Decide the cause of each mistake:
   - **judgment / classification** -> a rule in `knowledge/local/lessons.md` (this PC's lessons);
   - **a threshold** (missed, split, merged or false event; wrong frame range) -> set it in
     `tools\config.local.json` (this PC's own values laid over `tools\config.json`, same keys, only what differs,
     e.g. `{"cut": {"jump_cut_diff_rel": 5.0}}`; not in git, so an update never takes it away - 2026-10-24) and
     record it in the lesson; `tools\config.json` itself (the `_comment` keys explain each section) only for a fix
     everyone's MotionLab needs, which the repo owner shares;
   - **detector logic** -> change `tools\motionlab\detect.py` only when a rule or threshold cannot fix it (an update
     may replace it: the app keeps the change and brings it back on a click, but tell the user).
4. Add rules to **`knowledge/local/lessons.md`** (not to the shared lessons.md - that one only changes when lessons
   are reviewed, see below) - concrete and checkable, one per mistake pattern. Get the id with
   `.venv\Scripts\python tools\knowledge.py next-lesson-id` (`local-N`; it also creates the file):
   `- [local-N] (YYYY-MM-DD, from <video> <event>[, category: <id>]) <rule>` + `Why:` + `Config:` lines - add the
   category tag only when the rule is specific to that kind of video (format at the top of the shared lessons.md).
   Example: "crossfade vs luma fade: check whether the highlights transition first - if the bright areas of the
   outgoing shot switch to the new shot before the dark areas, it is a luma fade, not a crossfade."
   The lesson applies on this PC right away; the user shares it with *Claude's memory > Shared knowledge > Share my
   knowledge* in the app (they tick what goes; a lesson whose source note says "test" stays on this PC until they tick
   it, and one that names a file on this PC is flagged - so name the video and event, never a path).
5. If config or code changed: re-run `.venv\Scripts\python tools\analyze.py "<source path>" --redetect`, then
   `.venv\Scripts\python tools\selftest.py --extended` - **all four self-tests must still PASS**; if one fails,
   rework or revert the change before continuing.
6. Re-check every event the user marked WRONG or PARTLY (and anything reported missed) in the new run: look at the
   sheets, update `review.json`, run `tools\report.py <name>`.
7. Tell the user exactly what changed: each lesson added (quoted), each config key `old -> new` and why, any code
   change, each re-checked event (old -> new type / frames, with timecodes), and the self-test result. Remind them
   that *Claude's memory > Shared knowledge > Share my knowledge* sends the new lessons and the updated reference card
   to their friends (whatever they tick there).
