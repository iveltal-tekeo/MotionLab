# knowledge - what all MotionLab installs learn together

| Folder | What | In the repo? |
|---|---|---|
| `references\` | one **reference card** per analysed video and person: category, format, link, pacing (cuts/min, shot lengths, hook, cuts on the beat), every reviewed effect with its verdict and note | yes - shared |
| `incoming\` | lessons from someone's feedback, **waiting for review** before they go into the shared `lessons.md` | yes - shared |
| `local\` | this PC only: your cards before sharing, your new lessons (`lessons.md`, ids `local-1` ...), what was shared already, and what Claude reads: `summary.md` (per category: pacing norms, effects seen, corrections) + `summary\<category>.md` (every reviewed effect) | no |
| `inbox\`, `outbox\` | knowledge packs (`*.mlpack.json`) for friends without GitHub access | no |

The reviewed rules themselves are in `.claude\skills\analyze-reference\lessons.md` (shared).

**How it moves**: in the app, *Knowledge > Share my knowledge* commits your new cards and lessons to GitHub; everyone
else gets them with their next update (automatic at start-up). Without GitHub access the app writes a pack file to
`outbox\` - send it to someone who can upload it; they drop it in their `inbox\` and click *Import*.

Never in here: videos, frames, contact sheets or file paths. See `docs\knowledge_sharing.md`.
