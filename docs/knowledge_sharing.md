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
| Thresholds (`tools\config.json`), code | a few KB | the repo | yes, with the self-test |
| Videos, frames, contact sheets, previews, file paths, your settings | GBs | `refs\`, `analysis\`, `projects\`, `settings.json` | **never** |

Cards carry the name you set in *Settings > Sharing & updates* - not your email or anything else.

## How it moves (v0.2)

1. You analyse a video (category + tags in the dialog) and review it with Claude; your verdicts in the app go into its
   card. Claude writes new lessons into `knowledge\local\lessons.md` - they work on your PC at once.
2. **Knowledge > Share my knowledge**: the app copies your new or changed cards to `knowledge\references\` and your new
   lessons to `knowledge\incoming\`, commits only those knowledge paths and pushes them to GitHub. If somebody shared
   first, it pulls their work and pushes again; if the push fails (no access, offline) it undoes the commit and leaves
   a pack file instead.
3. Everybody else gets them with their next update - MotionLab updates itself from GitHub when it starts (git pull;
   the app restarts on the new version). Their `summary.md` now includes your cards.
4. **Review**: lessons in `knowledge\incoming\` do not change anybody's analyser until someone (normally the repo
   owner) clicks *Review them in Claude Code* on the Knowledge page. Claude keeps the concrete, checkable ones, merges
   duplicates, tags category-specific ones (`category: cooking`) and appends them to the shared `lessons.md` as the
   next `L0NN`; the next *Share* publishes that. One wrong rule cannot silently change everybody's analyser.
5. **Friends without write access** (or without git): *Share* writes `knowledge\outbox\<name>-<time>.mlpack.json`;
   they send it to you, you drop it in `knowledge\inbox\` and click *Import* - its cards and lessons are shared with
   your next *Share*.

What Claude reads: the shared `lessons.md`, your own `knowledge\local\lessons.md`, `summary.md` - per category the
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
| v0.3 | **Category profiles**: threshold overrides per category (`config.json`) once a category has reviewed feedback on 3+ references; detectors for things music videos lack (captions / burned-in subtitles, jump-cut talking heads, picture-in-picture). |
| v0.4+ | Local search across all cards (SQLite full-text; local embeddings only if keyword search falls short) - still offline. |
| beyond friends | A hosted service with accounts, moderation and opt-in upload of text summaries (never videos) - only if needed. |

## Rules for anything shared

- Never videos, frames, contact sheets, previews or file paths - only text and numbers.
- Every lesson names its source: video, event, frame + timecode, date (the format in `lessons.md`).
- A lesson changes the shared analyser only after review.
- Thresholds and code change only together with a passing `selftest.py --extended`.
