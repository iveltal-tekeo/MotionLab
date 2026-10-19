# knowledge - what all MotionLab installs learn together

| Folder | What | In the repo? |
|---|---|---|
| `references\` | one **reference card** per analysed video and person: category, format, link, pacing (cuts/min, shot lengths, hook, cuts on the beat), every reviewed effect with its verdict and note | yes - shared |
| `incoming\` | lessons from someone's feedback, **waiting for review** before they go into the shared lessons files (`*-making.md` = lessons on making videos) | yes - shared |
| `local\` | this PC only: your cards before sharing, your new lessons (`lessons.md`, ids `local-1` ...; on making videos `lessons_making.md`, ids `local-make-1` ...), `shared.json` (what was shared already and when, what you keep on this PC - unticked in *Shared knowledge*, tests until you tick them - and the friends' files you imported), and what Claude reads: `summary.md` (per category: pacing norms, effects seen, corrections) + `summary\<category>.md` (every reviewed effect) + `memory.md` (Claude's memory: your ratings as rules, every video's style, the effects seen; a friend's items marked "(from <name>)") | no |
| `inbox\`, `outbox\` | knowledge packs (`*.mlpack.json`) for friends without GitHub access | no |

The reviewed rules themselves are in `.claude\skills\analyze-reference\lessons.md` (analysing, L###) and
`.claude\skills\recreate-video\lessons.md` (making videos, M###) - both shared.

**How it moves**: in the app, *Claude's memory > Shared knowledge* lists everything of yours with a tick (unticked =
kept on this PC; anything that looks like a test starts unticked), and *Share my knowledge* commits the ticked new cards
and lessons to GitHub; everyone else gets them with their next update (automatic at start-up) and sees them marked
"from <your name>". Without GitHub access the app writes a pack file to `outbox\` (it counts as shared) - send it to
someone who can upload it; they drop it in their `inbox\` and click *Import* (*Shared knowledge > Files from friends*).

Never in here: videos, frames, contact sheets or file paths. See `docs\knowledge_sharing.md`.
