---
name: whats-next
description: MotionLab - review where the lab stands so the user can decide what to do next - what changed since the last release (pushed, tested, uncommitted), every planned version's state (built / done / still open), the roadmap, ideas not picked yet, and what waits on the user (verdicts, tests, inputs). Ends with options and a recommendation. Use for "/whats-next", "what should we do next", "review the roadmap / plans / ideas", "where are we", "status".
argument-hint: "[short | <version e.g. 0.3.5> | ideas]"
---

# /whats-next

`$ARGUMENTS`: empty = the full review with options; `short` = the status only, no options; a version (`0.3.5`) =
that version in depth (read its whole section in `docs\plans.md`); `ideas` = the ideas list looked at again.

This skill only looks and advises. It starts no work, and changes files only when the user decides something here
(step 4).

## 1. Gather (cheap first)
- Run `.venv\Scripts\python tools\whatsnext.py --fetch` - one digest: version, commits since the last release,
  GitHub's main / tested, uncommitted files, every plans.md section's status lines, the roadmap (+ its check), ideas,
  the lab's state (each reference's next workflow step, videos, prompts, friends' lessons, last self-test).
- Read more only where the digest is unclear or the argument asks for it: one section of `docs\plans.md`,
  `docs\ideas.md`, the top of `CHANGELOG.md`. Not the whole lab.
- Use the auto-memory notes too (REMIND / OPEN / unreleased entries, the user's priorities) - they are background:
  check them against the digest, which is current.

## 2. Answer (plain words, short; frame + timecode for any frame you mention)
1. **Since the last release** (version, date): what is on GitHub but in no release yet (group the commit titles
   into 2-5 themes), whether friends have it (tested = main?), anything uncommitted. If a version's items are all
   built, say it is ready to publish (`__version__`, a CHANGELOG section listing every unreleased commit's theme,
   the user commits / pushes, GitHub's tests).
2. **Roadmap**: one line per version, in order: released / in progress (n of m items) / planned, with what is
   built and what is still open or blocked.
3. **Waiting on the user**: only things they can do - try a new feature, verdicts / possible misses, rate prompts,
   send a video or links, open Resolve for a test, decide something - each with where to do it (app page / file).
4. **Options for next** (3-5, unless `short`): what, why now, size (S = under a session, M = a session, L = more),
   what it needs from the user, risk. Mark one **Recommended** and say why. Prefer: finish and publish a started
   version before opening a new one; things blocked on the user go after things Claude can do now; ideas only when
   the user asks or nothing planned is ready; "light and tested first" (ordinary laptops, measured gain).
5. Then ask which one to do (AskUserQuestion, the recommended one first) - unless `short`.

## 3. `ideas`
For each idea in `docs\ideas.md`: one line - what it would improve now, its cost to test on an ordinary laptop, and
whether something planned needs it. Suggest at most 2 worth a small test. Ideas are not plans.

## 4. When the user decides
- Picks an option: say what you will do first, then do it in this chat (or say which skill / chat fits better).
- Moves an idea into a version: add it to that version's section in `docs\plans.md` (`## x.y.z - planned - title`
  headings), take it out of `docs\ideas.md`. Planned versions never go into CHANGELOG.md.
- Adds, moves or re-orders versions: update `docs\plans.md`, then the roadmap - `tools\roadmap.py sync` (adds /
  drops versions to match plans.md and CHANGELOG.md), a short label for each new one and an icon + line for a new
  major (x.y.0) in `docs\roadmap\roadmap.json`, `roadmap.py check`, `roadmap.py render`. The app's Home reads the
  JSON live; the render is for README's picture.
