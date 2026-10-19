# /analyze-reference texts <set> - a set of scripts & prompts

The Analyser's *Scripts & prompts* (2026-10-18; the user: "imagine i wanted to analize 10 prompts at the same time i
could and it wouldnt allucinate"). A set = `analysis\texts\<set>\` around texts that live in the prompt library
(`knowledge\local\prompts\`). This window checks EVERY text of the set, one at a time, then names what they have in
common. A tool saves your work only when it holds - every word you quote must be in THAT text - so quote, never
paraphrase. Read this whole file first. Section 0 of SKILL.md does not apply (its lessons are about video effects);
nothing here has frames (a script's times are estimates in seconds).

## 1. Where the set stands
`.venv\Scripts\python tools\textsets.py state <set>` (JSON) and `... show <set>` (the set in lines, one line per text):
- `left` = the texts not checked yet (with `stale`: checked as another kind - check them again). Skip every text that
  is not in it: a stop (a limit, the window closed) loses at most one text, and *Continue with Claude* starts at the
  next. Say in one line what was done before.
- `to_sort` = files MotionLab could not read (a PDF, a scan): section 2 first.
- `disputed` = texts where the user marked parts of your check Wrong / Partly. When nothing else is left (the app's
  *Check them again*), check those again first - `show` prints "the user: WRONG / PARTLY" on each part and their notes
  as "what the user wants": Wrong = they disagree with your check of that part, keep their words unless the note says
  otherwise; Partly = follow the note; Correct = your check stands.
- `patterns`: none / stale = section 5 at the end (3 texts or more).
- The user's verdicts on the patterns: `show <set>` prints "the user: CORRECT / PARTLY / WRONG (their note)" on each
  P#. When one is Partly or Wrong (the set page's *Send it to Claude*), do section 5 again at the end even when
  `patterns` is ok: keep each Correct pattern as it is and with its id (the verdicts are stored by id), fix a Partly
  one by its note, drop or redo a Wrong one (a new pattern gets a new id), and say in one line what changed.

## 2. Files to sort (`to_sort`)
Read each file whole. Every usable script / prompt in it = one record, its text COPIED EXACTLY (no translating, no
cleaning up, no heading of yours), `"source": {"file": "<the file's name>"}` (the set's "whose" fills the rest), the
kind your call (shot, image, hook, script, brief). Save them all as one JSON list:
`.venv\Scripts\python tools\prompts.py import <list>.json --set <set>`. It refuses a record whose words are not in its
file and names the closest passage - copy that passage, never re-word. When MotionLab cannot read the file at all it
says the copy was not checked: be exact anyway.

## 3. Read once, before the first text (never again per text)
- `.claude\skills\write-prompt\SKILL.md` section 1 *Reviewing (stars)* and section 2 (each kind's parts, briefs).
- When the set has scripts or hooks: `.claude\skills\write-script\SKILL.md` section 2 and its `guidelines.md`.

## 4. Each text, one at a time (in the order of `left`)
1. `.venv\Scripts\python tools\textsets.py show <set> <n>`: #n's prompt id, kind and why, sha1, what MotionLab
   measured (evidence where to look, never proof: words that name a part, the script check's ✓ ~ ✗ lines, twins, the
   words it shares with other texts), the parts of its kind, your check so far with the user's verdicts, and the text
   with line numbers.
2. A wrong kind: `textsets.py kind <set> <n> <kind> --why "..."` (it gets a new id), then `show` again.
3. Write `analysis\texts\<set>\claude\item_<n>.json` = the draft line `show` printed (set, n, id, sha1 - copy them) +
   - `title`: 3-6 words in its language - what it makes or says, never "Prompt for..."; `pattern` for a hook /
     script; `tags`.
   - `structure`: one row per part of its kind, in the kind's order, `{"slot", "text", "status", "tip"}`. `text` = the
     text's OWN words for that part, copied (whole words, in its order, shortened with ... - at most 400 characters);
     "" when missing. `status`: `clear` (a model / Claude can act on it as written), `vague` (said, but open to
     guessing or contradicting itself), `missing` (not said, and it matters). `tip` = the concrete change, one
     sentence.
   - `skipped`: `{"<part>": "why it is not part of this text"}` for a part that does not apply (no music in a silent
     shot, the length set on the site). Every part is a row or skipped - none left out.
   - `overrides`: `{"<part>": "why"}` only for a part the measured script check flags (~ / ✗) that you still mark
     clear (a story that needs "I"); otherwise mark it vague or missing.
   - `review`: `{"stars": 0-5, "why": "...", "fix": "..."}`. Words in double quotes inside `why` must be the text's; a
     line you propose goes in `fix` or a tip (not checked).
   - `model` only when the text, or its file's name, names it.
4. `.venv\Scripts\python tools\textsets.py check <set> <n> analysis\texts\<set>\claude\item_<n>.json`
   - Saved: "saved #n ...: k quotes found in its text ... - m of N checked"; the draft is deleted. The record now holds
     the text's original words and where they are (the app lights them up).
   - REFUSED (exit 2): nothing saved. Each problem names the part and, for a quote it cannot find, the closest real
     passage; words of another text of the set are named as such. Fix exactly what it names - copy the real words
     (pieces in the text's order), change the status, or move the part to `skipped` - and run it again. Never re-word a
     quote to get past the check, and never keep two texts open: finish #n before you `show` the next one.
5. One line in the chat per text: "4 of 10 done - #4 <title>: ✓7 ~2 ✗1, 3 stars".

**More than 10 texts left: helpers.** After step 3, split `left` into runs of consecutive numbers (about 5 texts
each) and start one helper per run, all in one message so they run in parallel (Agent tool, general-purpose). Each
helper's prompt: the set and its numbers; read this file's section 4, write-prompt section 2 (+ write-script section
2 and guidelines.md for scripts / hooks) first; do section 4 for those numbers only - each text saved with
`textsets.py check`, nothing else written; reply with one line per text (n, title, kind, ✓ ~ ✗, stars, how often it
was refused). Then run `state` yourself: every helper's text must count - check the ones that do not.

## 5. What they have in common (3 texts or more, every one checked)
Write `analysis\texts\<set>\claude\patterns.json`:
`{"summary": "2-3 sentences", "patterns": [{"id": "P1", "kind": "hook|structure|wording|camera|look|length|cta|voice|format|other",
"what": "<what repeats, in words>", "examples": [{"n": 2, "quote": "<#2's own words that show it>"}], "except": [<texts that clearly do not>]}]}`
- 3-8 patterns, each shown by 2 different texts at least (twins count once). The user's good-rated texts weigh more:
  say which patterns they share.
- Never type a count ("8 of 10", "80 %"): MotionLab counts the examples and writes "how_many".
- A pattern the lab measures can say so: `"measure": "script.hook.pattern=question"` (the facts `show` prints) - its
  texts come from the facts, and an example that does not measure so is refused.
Then `.venv\Scripts\python tools\textsets.py patterns <set> analysis\texts\<set>\claude\patterns.json` (refused = fix
what it names, as in step 4).

## 6. The end
`textsets.py state <set>` must say every text is checked (`left` empty, nothing to sort) and, with 3 texts or more,
`patterns` ok. Report: one line per text (n, title, kind, ✓ ~ ✗, stars), the 3-5 strongest patterns with their
numbers, and where the user goes next - Analyser > Scripts & prompts > this set: each pattern Correct / Partly / Wrong;
a card opens a text with your check part by part (they can mark each part right or wrong, write what they want, and
*Optimize with Claude* writes a better version next to it).
