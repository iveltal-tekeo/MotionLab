---
name: write-prompt
description: "MotionLab - the prompt library: save prompts (briefs for Claude, Seedance / Higgsfield / Kling shots, Nano Banana / GPT Image pictures), check each part by part (clear / vague / missing, 0-5 stars), optimize one from the user's wishes, write new ones like one that worked. Use for '/write-prompt ...', pasted or uploaded prompts (text, PDFs, docs), 'a brief', 'a Seedance / video / image prompt'."
argument-hint: "analyse <ids> | optimize <id> | import <files> | <brief|shot|image|hook|script> [like <id>] [- want: ...] [- style: <reference>] | shot <reference> f<a>-<b> | request <req-NNN>"
---

# /write-prompt

If the first message says to reply in Spanish, talk to the user in Spanish (Spain, tu); keep what you write into the lab's files in English.

`$ARGUMENTS`:
- `analyse <id> <id> ...` (old name: `split`) -> Claude's check of each prompt, part by part (section 2): what it
  says per part, clear / vague / missing, a tip, the stars. The app shows it as a checklist where the user writes
  what they want per part.
- `optimize <id>` -> a better version from your check + the user's wishes (section 2b); the original stays. Not
  checked yet (the app's first *Optimize with Claude*): check it first (section 2, saved), then optimize.
- `import <file> ... [- kind <k>] [- source: ...]` -> the app's *Let Claude sort it*: files the user attached or
  pasted, in `knowledge\local\prompts\files\` (.txt / .md / .docx / .pdf). Read each whole and save every usable
  prompt in it ("Collected files" in section 1; `source.file` = the file's name; the source the user picked, else
  ask once), then split and review the new ones. Tell the user the new ids per kind.
- `<kind>` or `<kind> like <id>` -> write a new prompt (section 3; `like` = start from that example)
  - `<kind> - want: <what> [- for: <purposes>] [- model: <model>] [- style: <reference>]` (the app's *Generate a
    new prompt from zero*): the user's need in their words; ask once for what is missing, then write it (section 3).
    `style` = an analysed reference to copy the style of (section 2a).
  - `... like <id> - change: <what>` (the app's *Use it, change…*): keep that prompt's structure, wording and what
    worked; change only what the user wrote; say in one line what changed.
  - `request <req-NNN>` (the app's *Generate a new prompt* and *Use it, change…* since 2026-10-19: the user's words
    reach you whole in a file, never through the cmd line): read it with `.venv\Scripts\python tools\script.py show
    <req-NNN>` (the kind, what the user wants, start from <id>, what to change, for, model, style like) and work as
    for the two lines above; save what you write with `"request": "<req-NNN>"` in the JSON import, so the app sees the
    request is done.
- A prompt's `tags` = what it is for (vlog, talking head, sfx, transitions, colour, ... or the user's own): copy
  examples with the same tags and model first. Videos made from a prompt keep how they turned out per part in
  `projects\<p>\build\outcome.json` (the prompt library shows it as "Used in"): repeat the parts rated good, fix bad.
- `shot <reference> f<a>-<b>` -> a shot prompt filled from a reference's frames (section 4)
- empty -> ask what they need: a new prompt (which kind) or adding examples
The app opens this with effort medium. Work from `C:\MotionLab` with `.venv\Scripts\python`; don't explore the lab.

**Read `.claude\skills\write-prompt\writing.md` first, every time**: section 0 (the rules), section 3 (write a new
prompt) and section 4 (a shot from a reference) live there - /generate-video reads the same file.

## 0. Rules
In `writing.md` (read it first).

## 1. The user pastes prompts
Save their text unchanged to a file in your scratchpad, then
`.venv\Scripts\python tools\prompts.py import <file>` (any text = one prompt, its kind guessed; lines of only `---`
separate several; the older `prompts.py template` format with kind / source / result lines still works; one bad
prompt = nothing saved, the error names it - never change their prompt text). Then split the new ones (section 2). Missing info (model, how it turned out) -> ask once, in one message, or leave it empty.

**Collected files (PDFs, docs) from creators**: read every file; one record per usable prompt (a guide with 10
templates = 10 records), text copied as written (no translation - say in the review when it should be translated),
`source` = creator (as the file names them, else "unknown") + `file`; a multi-step recipe (image prompt -> video
prompt) gets the same `workflow` name and `step` 1, 2, ...; `notes` = how to use it (what to upload, what to fill).
Save them as one JSON list (`prompts.py import <file>.json`) with `structure` and `review` already in it.
**The import checks your copy against the file** (2026-10-18): every line / sentence of a record's text must be in its
`source.file`, in the file's order (punctuation, case and line breaks may differ; a page number between two is fine).
A record that is not - translated, cleaned up, two prompts merged, a heading of yours - is refused, nothing is saved,
and the error names the closest real passage: copy that passage, never re-word to get past it. The lab reads PDFs
itself once setup / the Update button installed its PDF reader; until then a PDF's copy is not checked (the import
says so) - be exact anyway. Never install anything into the lab's `.venv` yourself (a scratch venv is fine).

**Reviewing (stars)**: judge whether a model will do what the text asks: 5 = one clear job, every reference has a
role, locks first then the change, one camera move (or timed beats), the usual failures closed; 4 = solid with one
real weakness; 3 = good ideas but overloaded (too many beats for the length, several moves in one shot) or missing
locks / length; 2 = vague or self-contradicting; 1 = keywords only; 0 = won't work. `why` in one or two sentences,
`fix` = the concrete change. Things that cost stars: keyword padding (8K, IMAX), several camera moves in one shot,
sub-perceptual details (a 2-pixel shift), fine hand actions, contradictions (locked camera + "camera shake"), a
language other than English when the guide itself says to translate, content filters (violence, minors).

## 2. Check a prompt (`analyse`; older name `split`)
The app shows your check as a checklist - one row per part of the prompt's kind, in the kind's order, each with what
the prompt says, a mark and a tip, and a box where the user writes what they want. So: **every part of the kind gets
a row** (also the ones the prompt never mentions), with `status` = `clear` (a model / Claude can act on it as
written), `vague` (said, but open to guessing or self-contradicting) or `missing` (not said and it matters for this
prompt), and `tip` = the concrete change, one sentence (for clear parts only when something small would still
help). `text` = the prompt's own words for that part (verbatim, in its language, shortened with ...; "" when
missing). A part that does not apply to this prompt (no transitions in a single-shot prompt, the length set on the
site) goes in `"skipped": {"<part>": "why it is not part of this prompt"}` - every part is a row or skipped.
**The tool checks your quotes** (2026-10-18, `prompts.verify_check` - annotate, a JSON import and the Analyser's text
sets): every row's `text` must be found in THIS prompt - its whole words in its order, pieces left out with ... (in
the prompt's order), at most 400 characters; case, accents, curly quotes and punctuation may differ, and the saved
quote becomes the prompt's own words + where they are (`at`, the app lights them up). "missing" quotes nothing;
"clear" / "vague" quote the prompt (a part that is fine but not said is `skipped`, not "clear" with no words); the
part names are the kind's (below); words in double quotes inside `review.why` must be the prompt's (a new line goes in
`fix` or a tip); a `model` the prompt does not name is left out. Refused = exit 2, nothing saved, every problem named
with the closest real passage - fix the quote to that passage (or the status, or move the part to `skipped`), never
re-word it to get past the check. A record checked before this has no `at`: the app says "not verified" - check it
again.
- **Briefs** (kind `brief` = the user tells Claude how to make / edit a whole video), in the order a video is made
  (the app groups them): *the plan* - format & length (long / short form, minutes, aspect, platform), story & hook,
  feel / style (an analysed reference beats an adjective, section 2a), footage (folders, cameras, log profiles,
  b-roll: what covers what), order & structure; *the edit* - pacing & cuts, transitions, effects (zooms / punch-ins,
  speed ramps, shake, freeze frames); *sound* - voice & audio (silences cut, noise, levels, the voice over the
  music), music (licensed or made where), sfx; *look & text* - colour (one base LUT or per scene - never both),
  motion graphics, captions & text; *finish* - ending (outro, call to action, end screen), deliverable (Resolve
  project name, export), questions first (what Claude must ask before starting). Mark what the lab cannot do or
  measure today as vague with the tip. A part that does not apply (no music in a silent edit) goes in `skipped` with
  why.
- Wrong kind (a brief saved as a talking script): move it first - `prompts.py kind <id> <kind>` - and say the new id.
For each id: read it (`prompts(id=...)`), then write a JSON file and run
`.venv\Scripts\python tools\prompts.py annotate <id> <file>`:
```json
{"title": "Neon alley dolly-in", "pattern": "", "tags": ["night", "city"],
 "structure": [{"slot": "subject", "text": "a young man in a black hoodie", "status": "clear"},
               {"slot": "camera", "text": "slow dolly-in", "status": "clear"}],
 "skipped": {"audio": "the site adds no sound to this model's clips"}}
```
- `structure` items: `{"slot": "colour", "text": "un mismo lut ... luts acorde a la escena", "status": "vague",
  "tip": "Pick one: one base LUT for the D-Log M clips + per-scene exposure / white balance, or a LUT per scene"}`.
  Slot names (`prompts()` lists them): brief = format & length, story & hook, feel / style, footage, order &
  structure, pacing & cuts, transitions, effects, voice & audio, music, sfx, colour, motion graphics, captions &
  text, ending, deliverable, questions first; shot = references, keep, change, subject, action, setting, camera,
  lens, light, look, motion, beats, audio, length / aspect, avoid; image = references, keep, change, subject,
  setting, composition, light, look, materials, avoid; hook = pattern, opening line, on screen, promise; script =
  hook, promise, problem, points, re-hooks, proof, payoff, call to action, on screen (`/write-script` section 2). `references` = what
  each upload is for, `keep` = what must not change, `change` = the transformation. Add a slot only when none fits.
- Hooks: `pattern` = question, bold claim, number, story, contrarian, demo, curiosity gap or call-out.
- Title (the card shows only the title, so it must say which prompt this is): 3-6 words in the prompt's language -
  what it makes + what sets it apart, e.g. "Londres día 1 · vlog estilo Clavero", "FPV drone around the subject",
  "Hook: nobody tells you this". Never "Prompt for...", an id or the model name. Replace the automatic title
  (first words of the text) when you check a prompt. Afterwards one line per prompt in the chat: id, title, the
  slot order.
- Put your `review` (section 1, "Reviewing") in the same JSON: `why` = the main point in two sentences, `fix` =
  the one change that helps most. In the chat afterwards: one line per prompt - id, title, n clear / vague /
  missing - and "write what you want next to the parts in the prompt library (Generate), then click Optimize with Claude".

## 2a. Style from an analysed reference
"al estilo de Clavero", "like this creator's vlogs": when the user analysed one of their videos, use what the lab
MEASURED instead of asking for a link. `prompts(id=...)` shows it: `style from your reference <name>: ...` (linked
on the card's *Style like*, or `- style:`) or `analysed references it may mean (not linked)` (matched by who made it
/ its title).
- Check (section 2): a clear match (made by the creator the prompt names) -> link it,
  `.venv\Scripts\python tools\prompts.py style <id> <name>`, and say so; the feel / style row is then `clear`
  ("measured from <title>"). A weaker match (a title word) -> don't link; the tip names it ("Analysed: <title> - link
  it under Style like if that is the style"). Nothing analysed -> tip: "Download one of their videos in References
  and Analyse it, then link it under Style like" (not "give a link": a link alone measures nothing).
- Optimize / write (2b, 3): turn the measurements into instructions in the prompt's language, in a "feel / style"
  section that names the reference (`analysis\<name>`, so the Claude that runs it can open it): cuts per minute and
  the typical shot (median, short-long range) -> pacing & cuts; cuts in the first 3 s -> the hook's rhythm; effects
  per family and per minute -> transitions / motion graphics / SFX moments; BPM -> music. Effects the user marked
  correct are safe to copy (`events(<name>)`, the reviewed labels); say which. Colour: not measured yet (0.3.7) -
  look at 4-6 frames spread over it (`frames(<name>, "a,b,c,d")`) and describe the grade in words (warm / cool,
  contrast, saturation, skin, blacks), frame + timecode for each you cite. Words (`words: yes`): how it talks in
  the hook (`transcript(<name>, 0, <3 s>)`) - its rhythm, never its sentences.
- Copy the style, never the content: no clips, music, words or graphics of the creator in the prompt.

## 2b. Optimize (`optimize <id>`)
No check on it yet (no part has a status): do the check of section 2 first and save it (`annotate`), so the card shows
it, then go on here. Read the prompt (`prompts(id=...)`): its check (each part's status / tip), its `review`, the user's wishes
("what the user wants") and its style references (section 2a - link a clear match first). The user's per-part verdicts
(`verdicts`, the app's *Is Claude right?*): Wrong = the user disagrees with your check of that part, keep their words
unless the note says otherwise; Partly = follow the note; Correct = your check stands. Write ONE better
version: the user's wishes win over your tips; every vague / missing part gets fixed (wish, else your tip; when neither and it matters, ask once - or pick a sensible default
and say so); keep their language, voice and every good part word for word. A brief is written in clear sections, one
per part (short headings), so the Claude that runs it cannot misread it; drop asks the lab cannot do (say so).
Save it as a NEW prompt (the original stays): a JSON list -> `prompts.py import <file>.json` with the same kind,
tags, model and `style_refs`, `"source": {"type": "written"}`, `"made_from": ["<id>"]`, title "<old title> -
optimized" (optimizing an optimized one: "- optimized 2"), and its own `structure` (statuses - mostly clear now) +
`review`. Then tell the user the new id, the 3-5 changes that matter, and how to run it (a brief or script: *Run it* on its card = Create video; a shot / image: copy it into the
site) and to rate what it made.
- Prompts added in the app have a GUESSED kind (and maybe no title / model): when the kind is wrong (an image prompt
  saved as a shot), move it first - `.venv\Scripts\python tools\prompts.py kind <id> <right kind>` (it gets a new id;
  say so) - then annotate the new id.

## 3. Write a new prompt
In `writing.md` (read it first).

## 4. A shot from a reference (`shot <reference> f<a>-<b>`)
In `writing.md` (read it first).

## 5. Hooks from talking videos (until 0.4 step 2 automates it)
When the user names an analysed talking reference: `transcript(reference, 0, <3 s in frames>)` = its hook. Offer to
save it as a creator hook (JSON import, `source` creator + the link from `refs\downloads.json`), then split it.
