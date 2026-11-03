---
name: spark
description: MotionLab - SPARK, why a video worked (the Analyser's Content creation way): one fixed rubric for every video - the idea, the packaging, the hook (0-3 s), the promise kept, open loops, pacing, emotion, why people send it / comment, craft, the ending, context - each point labelled measured / judgement / unknown with its evidence (the video's words, a frame, a number of the lab's table), its numbers against the creator's usual, what the video cannot explain, and what to take for your own videos. Use for "/spark <name>", "/spark pending", "why did this video go viral", "why did it work", "why it flopped", "por qué funcionó", "por qué se hizo viral".
argument-hint: <name> | pending | test <id> | month <YYYY-MM>
---

# /spark

If the first message says to reply in Spanish, talk to the user in Spanish (Spain, tú); write the write-up in the
video's own language unless the user's question (`ask`) asks for another.

`$ARGUMENTS`:
- `<name>` → the SPARK of `analysis\spark\<name>\` (the app prepared it: the words, the numbers, the pictures).
- `pending` → `tools\spark.py pending` lists every video waiting; write each in turn (a line to the user after each).
- `test <id>` → a test of one idea (Content agency > Tests): the keep / change / cut review - *A test of one idea*
  at the end; skip sections 1-5.
- `month <YYYY-MM>` → the monthly review of the user's own posts (Content agency > Monthly review): three next tests -
  *The monthly review* at the end; skip sections 1-5.
- a link or a file instead → tell the user to add it in the app (Analyser > Content creation > *Analyze with SPARK*), or
  run `.venv\Scripts\python tools\spark.py prepare "<video>" [--url <link>]` yourself for a file already on this PC
  (it looks the numbers up - a lookup the user asked for).

Work from `C:\MotionLab` with `.venv\Scripts\python`. Don't explore the lab. Never ask the user to correct anything
first; finish, then say what you made.

## 1. Read
1. `tools\spark.py show <name>` - the video, the user's question (`ask`: what they want to learn - it decides what the
   write-up stresses), **the table** (every number you may cite, by key), the creator's usual and its caveats, the
   chapters, the *Most replayed* moments, the paths.
2. `shots\hook.jpg` (the first 3 s) and `shots\end.jpg` (the last 3 s) - always. The thumbnail / cover and
   `content\info.json` (the title, the description) - the packaging.
3. The transcript `content\transcript.txt` - whole. A video without words: the sheets carry it.
4. The sheets `shots\sheet_NN.jpg` (one frame per shot, `#n` = the shot) - all of them for a short video; for a long
   one the sheets around the hook, the *Most replayed* moments and the payoff.
5. When show lists them: its FLUX analysis' line (craft) and its notes (INDEX); `knowledge\local\brand.json` for the
   take-aways (the user's goal and audience).

## 2. The rubric - every point, in this order (`key`)
| key | the question | evidence that fits |
|---|---|---|
| `idea` | What is it, who is it for - does it reach past the niche? | quotes, numbers (views_per_follower) |
| `packaging` | The promise of the title, thumbnail / cover and first frame - the glance | thumb_* numbers, frame 0, the title |
| `hook` | The first 3 s: what stops the scroll; picture, words and text saying the same thing? | quotes / frames in the first 3 s, hook_* |
| `payoff` | Is the promise kept - where does it land? | the quote or frame where it lands (the tool says how far in) |
| `loops` | Open loops and re-hooks: questions, "but", "so", where *Most replayed* rises | quotes, frames |
| `pacing` | Structure and pacing - against the creator's own usual, never "more cuts = better" | cuts_per_min, median_shot_s, words_per_min |
| `emotion` | Awe, anger, worry, humour, pride - which, how strong | quotes, frames |
| `send` | Why someone would send it: useful to one person, or makes the sharer look good | quotes, shares_per_1k |
| `comment` | Why people would comment: a question, a split opinion, a call | comments_per_1k, quotes |
| `craft` | Captions, sound, graphics, the look - FLUX's line when there is one | frames, text_pct, the FLUX line |
| `ending` | A loop back to the start, a call to action, a cliff | frames of end.jpg, quotes |
| `context` | A trend, a collab, timing, paid views, the creator's audience | numbers (followers, days_online), the description |

- `label`: **measured** = the point rests on a number of the table (cite it); **judgement** = your reading of the
  video's own evidence (quote it / show it); **unknown** = the video cannot tell (say why, no evidence).
- `hook_type` (one): question, bold_claim, result_first, curiosity, story, problem, promise, list, visual, callout,
  trend, other.
- The verdict: one line - what the evidence says about why it did what it did. **The result** (outlier / above / usual
  / below) is the tool's, from the outlier number: a video at its creator's usual is explained as ordinary, not as a
  hit.
- **High views with low likes / comments per 1,000 = the packaging did it, not the video** - say so.
- `not_explained`: always - what the video cannot account for (social influence makes hits partly unpredictable; the
  algorithm's first test, timing, a share by a big account, paid views).
- `takeaways`: 3-5 concrete actions for the user's own videos (`from` = the rubric key it comes from); with My Brand,
  for THEIR audience.

**The user's own video** (show says *THE USER'S OWN VIDEO*: their retention graph, traced by the lab from their
screenshot): the table has `ret_3s`, `ret_10s`, `ret_end`, `ret_drop` and, from 5 other traced videos, `ret_usual_*`.
`hook` cites `ret_3s` (measured; against `ret_usual_3s` when there is one - never against other creators); `pacing`,
`loops` and `payoff` look at show's steepest drops - each with its frames, the words said and the shot: quote those
words or show that frame as the evidence. **A drop shows where people left, never why**: the reason is your
judgement ("consistent with the answer arriving late"), and a drop where nothing was said is said so. The take-aways
then speak of their next video (keep what held, change what lost them). A graph show marks NOT used (another length)
is not evidence.

**The words** (the gate refuses the rest): "consistent with", "suggests", "likely" - never "caused", "proves",
"will go viral", "guaranteed". No simulated audience ("70 % of viewers would..."). A number with x or % in a text must be
a cited number's value (or how far in a moment lands) - never a ratio of your own. Compare only with the creator's own
usual. A *Most replayed* spike can mean rewatching, sharing or confusion.

## 3. The draft (JSON, written with the Write tool into `.app\dev\spark_<name>.json`)
```json
{"lang": "en", "title": "the subject in plain words", "verdict": "One line.", "hook_type": "curiosity",
 "rubric": [
  {"key": "idea", "label": "measured", "text": "Plain words around the evidence.",
   "evidence": [{"number": "outlier"}, {"quote": "the exact words, 3+ of them", "at": 120}]},
  {"key": "hook", "label": "judgement", "text": "...", "evidence": [{"shown": 0}, {"quote": "..."}]},
  {"key": "context", "label": "unknown", "text": "The video cannot tell whether ..."}],
 "not_explained": "...",
 "takeaways": [{"text": "One concrete action.", "from": "hook"}],
 "tags": ["music video", "rap"]}
```
- Evidence: 1-4 per point, each ONE of `quote` (word for word from the transcript; `...` joins two pieces; `at` = a frame
  hint between repeats), `shown` (a frame from shots.json "frames" - the tiles of hook.jpg, end.jpg and the sheets),
  `number` (a key of the table). Never type a timecode or a number the table has: the tool sets them.

## 4. Save through the gate
`.venv\Scripts\python tools\spark.py save <name> .app\dev\spark_<name>.json` - nothing is saved when a check fails; it
lists every problem. Fix those and save again; never write spark.json / spark.md by hand.

## 5. Tell the user
In two or three lines: the verdict, the result against the creator's usual, the strongest point and one take-away, and
that it is in Analyser > Content creation. Every time you mention has frame + timecode, e.g. f480 (00:00:16:00).

## A test of one idea (`test <id>`, 2026-11-02 - plans.md *Learn from your own posts* R2)
Two or three versions of one idea the user posted on one platform, decided by a number they picked first. Write what
the NEXT version keeps, changes and cuts - never a verdict on the idea.
1. `.venv\Scripts\python tools\experiments.py show <id>` - the rule, the result (winner / too close / waiting), each
   version's numbers, its SPARK and its steepest drops with the words said. Then for EACH version `tools\spark.py show
   <its spark>`, its `content\transcript.txt` (whole) and `shots\hook.jpg` + its sheets. Frames are each version's own.
2. Compare like with like: the same passage in A and B (the hook, the payoff, the ending), what the one change was
   (`what differs`), where each lost people. The result is the tool's: too close or waiting = say the numbers cannot
   tell yet, and review the words and the pictures only. **One post each is not a controlled test** (other days,
   other audiences): "consistent with", never "proves" or "caused".
3. The draft (Write it to `.app\dev\test_<id>.json`):
```json
{"summary": "One line: what the numbers and the words say, as far as they go.",
 "items": [
  {"version": "B", "kind": "keep", "from": 0, "to": 89, "text": "What works and stays.", "quote": "words said there"},
  {"version": "A", "kind": "change", "from": 280, "to": 380, "how": "edit_only", "metric": "hold_10s",
   "text": "What to change and why it may hold people.", "quote": "words said there"},
  {"version": "A", "kind": "cut", "from": 381, "to": 500, "metric": "end", "text": "What goes."}],
 "next_test": {"try": "the one change to test next", "same": "what stays the same", "metric": "hold_10s"}}
```
   - 2-12 items, at least one keep and one change or cut; `from` / `to` = frames of THAT version's video; a `quote`
     (optional) must be said inside them. `how`: `edit_only` (the footage has it) or `re_record` (it must be filmed or
     said again - say what). `metric` = the number the change should move (`experiments.py` METRICS). Every change and
     cut is saved as *to test* - the next test measures it. A % or x in a text must be one of the test's numbers.
4. `.venv\Scripts\python tools\experiments.py review <id> .app\dev\test_<id>.json` - the gate; fix what it lists.
5. Tell the user in two lines: what to keep, the main change, and that *Make the next version* in the test's pop-up
   hands it to `/recreate-video` (frames with timecode, e.g. f280 (00:00:09:10)).

## The monthly review (`month <YYYY-MM>`, 2026-11-02 - plans.md step 18 + *Learn from your own posts* R4)
A month of the user's OWN posts, ending in exactly three next tests. The lab already measured what worked (the page
shows it); you write what to try next - never why a video did well.
1. `.venv\Scripts\python tools\monthly.py show <YYYY-MM>` - each post with its evidence key, its views against the
   user's usual (`x usual`; *young* posts are still growing - never compare them), retention when traced, the measured
   features, the groups (a hint), the tests of one idea, the lessons (What works) and last month's next tests with
   where they got to. Read `knowledge\local\brand.json` (goal, audience, pillars) and the posts' titles; for a post
   SPARK read, `tools\spark.py show <name>` when its words or hook matter to a test.
2. Pick three tests the numbers point to: a hunch from What works to confirm, the follow-up of a test's winner, what
   the best posts share that the others lack, last month's test not done yet. Each test = ONE change (`try`), what
   stays the same (`same`: the topic, the length, the hour...), the number that decides it (`metric`, one of
   show's list; Instagram: hold_3s, hold_10s, end or avg_pct) and `why` with its numbers. **A month is a few posts**:
   "consistent with", "suggests" - never "caused", "proves", "will go viral".
3. The draft (Write it to `.app\dev\month_<YYYY-MM>.json`):
```json
{"summary": "One line: what this month's posts say, as far as they go.",
 "next_tests": [
  {"platform": "tiktok", "try": "the one change", "same": "what stays the same", "metric": "hold_3s",
   "why": "the evidence in words, with show's numbers", "evidence": [{"post": "tiktok:7697654084920266006"}]},
  {"platform": "youtube", "try": "...", "same": "...", "metric": "views_7d", "why": "...",
   "evidence": [{"lesson": "f2"}, {"test": "t1"}, {"post": "youtube:RH3Kj9X7kTg"}]},
  {"...": "the third"}]}
```
   - Exactly 3, three different tries; evidence = 1-6 of the posts (keys from show, the last 120 days), lessons and
     tests show lists - at least one post of the month across the three. A % or x in a text must be one of show's
     numbers. Write in English (what the lab keeps stays English).
4. `.venv\Scripts\python tools\monthly.py review <YYYY-MM> .app\dev\month_<YYYY-MM>.json` - the gate; fix what it
   lists.
5. Tell the user in two or three lines: the month in one sentence and the three tests; *Put it on the calendar* on a
   test's card makes it an idea in the content calendar.
