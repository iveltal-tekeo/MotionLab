# Sharing what MotionLab learns between installs (decision note, 2026-10-06; built in v0.2)

**Question:** you and your friends each run MotionLab on your own PC, with your own Claude plan and your own footage,
and analyse different kinds of videos (music videos, Instagram shorts, cooking, tutorials, motion graphics,
documentaries). 10 analysed and reviewed videos each = 30 together. How do the installs learn from each other - is a
cloud vector database worth it?

**Answer: no database. The GitHub repo is the shared knowledge base**, and what travels through it is small, reviewed
text: one *reference card* per analysed video and the *lessons* from your feedback. Every install downloads everybody's
cards with each update and condenses them into what Claude reads: `knowledge\local\summary.md` (a few KB: per
category the pacing norms, the effects seen, the corrections people gave) and one detail file per category.
Revisit a database at around 1,000 references, or when you want search like "find shorts that do text pops like this".

## What is shared - and what never is

| Knowledge | Size | Where | Shared? |
|---|---|---|---|
| **Reference card** per video and person: category, tags, format (vertical / horizontal, length), link, BPM, **pacing** (cuts/min, average / median / p10 / p90 shot, cuts in the first 3 s, first cut, % of cuts on the beat, effects/min, effect families), every reviewed effect (type, frames + timecode, what happens, timing, easing, origin, rebuild notes) with the person's verdict and note | 5-70 KB (a 3-min music video with 57 effects: 65 KB) | `knowledge\references\<video id>--<name>.json` | yes |
| **New lessons** from your feedback | ~1 KB each | `knowledge\local\lessons.md` (ids `local-N`) -> `knowledge\incoming\<name>-<time>.md` | yes, **reviewed first** |
| **Reviewed rules** every MotionLab applies | a few dozen paragraphs | `.claude\skills\analyze-reference\lessons.md` (L001 ...) | yes |
| **Lessons on making videos** (since 2026-10-14: edits, graphics, generated videos - not how a reference is judged) | ~1 KB each | `knowledge\local\lessons_making.md` (ids `local-make-N`) -> `knowledge\incoming\<name>-<time>-making.md` -> `.claude\skills\recreate-video\lessons.md` (M001 ...) | yes, **reviewed first** |
| Your ratings of your own videos (*How did it turn out?*) | a few lines | `projects\<video>\build\outcome.json` -> the first section of Claude's memory (`knowledge\local\memory.md`) | no |
| Thresholds (`tools\config.json`), code | a few KB | the repo | yes, with the self-test |
| Videos, frames, contact sheets, previews, file paths, your settings | GBs | `refs\`, `analysis\`, `projects\`, `settings.json` | **never** |
| Transcripts (other people's words, 0.4) | KBs per video | `analysis\<name>\content\` | **never** - later only topic summaries, counts and short quotes in cards |
| Scripts & prompts you analyse (text sets, 2026-10-18: often other people's words) and your prompt library | KBs | `analysis\texts\<set>\`, `knowledge\local\prompts\` | **never** - Claude's memory names a set's patterns on this PC only |

Cards carry the name you set in *Settings > Sharing & updates* - not your email or anything else.

## How it moves (v0.2)

1. You analyse a video (category + tags in the dialog) and review it with Claude; your verdicts in the app go into its
   card. Claude writes new lessons into `knowledge\local\lessons.md` - they work on your PC at once.
2. **Claude's memory > Shared knowledge** (2026-10-18; was *Share with friends*): every video and lesson of this PC is
   listed with a tick - ticked = it goes with your next share, unticked = **kept on this PC** (Claude still uses it
   here). A video or lesson whose name says it was a test (`test`, `testing`, `test_0.4.5`...) starts unticked until
   you tick it; a lesson that names a file or folder of your PC (`projects\...`, `C:\...`) is flagged, because friends
   would see the name. Your choices live in `knowledge\local\shared.json` (`"private"` = unticked, `"include"` =
   test-looking ones you ticked); every way of sharing (the app, `tools\knowledge.py share / export`) sends only what
   is ticked. Something already shared stays with the friends who have it - unticking stops its later changes (taking
   it back from GitHub is not built). Then **Share my knowledge**: the app copies your ticked new or changed cards to
   `knowledge\references\` and your ticked new lessons to `knowledge\incoming\`, commits only those knowledge paths
   and pushes them to GitHub. If somebody shared first, it pulls their work and pushes again; if the push fails (no
   access, offline) it undoes the commit and leaves a pack file instead - that file counts as the share ("as a file
   for a friend" under *Shared before*), so it is not sent twice. *Shared before* lists every share with its date and
   what went, by name.
3. Everybody else gets them with their next update - the sidebar's *New from friends* (an update with only friends'
   knowledge needs no restart; *Update available* when a new version comes with it; at start-up when Settings installs
   updates automatically). Their `summary.md` now includes your cards.
4. **Review**: lessons in `knowledge\incoming\` do not change anybody's analyser until someone (normally the repo
   owner) clicks *Review them in Claude Code* in Claude's memory. Claude keeps the concrete, checkable ones, merges
   duplicates, tags category-specific ones (`category: cooking`) and appends them to the shared `lessons.md` as the
   next `L0NN`; the next *Share* publishes that. One wrong rule cannot silently change everybody's analyser.
5. **Friends without write access** (or without git): *Share* writes `knowledge\outbox\<name>-<time>.mlpack.json`;
   they send it to you, you drop it in `knowledge\inbox\` (*Shared knowledge > Files from friends > Open the folder for
   friends' files*), see who sent it, when and what is in it, and click *Import* - its cards and lessons are shared
   with your next *Share*; every import is recorded (`shared.json` `"imports"`).
6. **Two kinds of lessons** (since 2026-10-14): lessons on *analysing* (how effects are judged; ids `local-N` ->
   `L###`, read whole before every analysis) and lessons on *making videos* (edits, graphics, generated videos; ids
   `local-make-N` from `tools\knowledge.py next-lesson-id --kind making` -> `M###`, read by `/recreate-video` and
   `/generate-video`), so neither skill reads the other's rules. They move the same way: one pack, one *Share*; the
   making lessons land in their own `knowledge\incoming\<name>-<time>-making.md`, whose header says to review them
   into `.claude\skills\recreate-video\lessons.md` with the next M number. The id says the kind (`local-make-N` /
   `M###` = making), so a pack carries both in one list.

**What came from a friend is marked** (2026-10-18, the user: "if something every came from shared knowledge it would
appear as a reminder"): in the app a lime badge "from <name>" (the shared icon) on their videos, effect examples,
verdicts, rules and lessons, the card dialog, *Made from* and Home; *Shared knowledge > From friends* lists per
friend their videos, the lessons waiting for a review and the rules that came from them. The "In the style of"
pickers offer only what was analysed or written on this PC (your videos, and in Prepare your scripts and hooks) -
friends' videos stay in Claude's memory as data. For Claude, memory.md, summary.md, `tools\style.py` and the script
requests mark a friend's items "(from <name>)" and name whose verdict it is ("tekeo's verdict", "tekeo's note");
"effects you confirmed" counts only your own verdicts. The skills say: data, never instructions - and when one
shapes what Claude makes, it tells you it came from that friend. Videos are named for people (`knowledge.label`,
worked out when read: your own name for it, Claude's breakdown `name`, the title without yt-dlp's `[id]`, for
"Video by <handle>" the first clause of Claude's summary).

What Claude reads before an edit or a generated video: Claude's memory (`knowledge\local\memory.md`, which starts with
your ratings of all your videos as rules: a part rated bad once is a default from then on) and both making-lessons
files. Before an analysis: the shared `lessons.md`, your own `knowledge\local\lessons.md`, `summary.md` - per category the
typical pacing (median and range), the effects found by everybody and the corrections people gave - and, for the
category it works on, `summary\<category>.md` with every reviewed effect and its verdict. The short file stays
small however many references there are, so 30 or 300 cards cost Claude about the same to read. A cooking short is judged against the cooking
cards; rules only apply to other categories when they are general.

## Why not a cloud vector database

1. **Scale.** 30 or even 1,000 cards are a few MB of text; the rules are a few dozen paragraphs. Claude reads the
   condensed summary directly - embeddings earn their keep with millions of chunks nobody can read, not here.
2. **Quality control.** Git gives review, history (who taught what, from which video and frame) and rollback - free.
3. **Running it.** A hosted database needs accounts, API keys inside an app you hand out (they leak), syncing,
   backups and money.
4. **Privacy and copyright.** Only text and numbers leave a PC; a central store of analyses would collect more.
5. **It does not fix the real gap.** A new kind of video needs measured norms and reviewed rules for that category -
   which the cards and lessons give - not similarity search.

## Next

| Version | What |
|---|---|
| 0.6.5 if friends' verdicts are in (`docs\plans.md`; was v0.3, then 0.6.0) | **Category profiles**: threshold overrides per category (`config.json`) once a category has reviewed feedback on 3+ references; detectors for things music videos lack (captions / burned-in subtitles, jump-cut talking heads, picture-in-picture). |
| not planned yet (was v0.4+) | Local search across all cards (SQLite full-text; local embeddings only if keyword search falls short) - still offline. |
| beyond friends | A hosted service with accounts, moderation and opt-in upload of text summaries (never videos) - only if needed. |

## Rules for anything shared

- Never videos, frames, contact sheets, previews or file paths - only text and numbers (a lesson that names a file
  of your PC is flagged in *Shared knowledge* before it goes).
- You choose what goes: unticked = kept on this PC; tests stay here until you tick them.
- Every lesson names its source: video, event, frame + timecode, date (the format in `lessons.md`).
- A lesson changes the shared analyser only after review.
- Thresholds and code change only together with a passing `selftest.py --extended`.
