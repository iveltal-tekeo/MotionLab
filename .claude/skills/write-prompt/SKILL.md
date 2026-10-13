---
name: write-prompt
description: MotionLab - the prompt library (0.4). Save the user's proven or collected prompts (briefs that tell Claude how to make a video, video-model shots for Seedance / Higgsfield / Kling, image prompts for Nano Banana / GPT Image, hooks, talking scripts), check each part by part (clear / vague / missing + tips, 0-5 stars), optimize it from the user's wishes, and write new prompts from zero or like one that worked. Use for "/write-prompt ...", when the user pastes or uploads prompts (text, PDFs, docs), or asks for a brief, a Seedance / video / image prompt, a hook or a script.
argument-hint: analyse <ids> | optimize <id> | import <files> | <brief|shot|image|hook|script> [like <id>] [- want: ...] [- style: <reference>] | shot <reference> f<a>-<b>
---

# /write-prompt

`$ARGUMENTS`:
- `analyse <id> <id> ...` (old name: `split`) -> Claude's check of each prompt, part by part (section 2): what it
  says per part, clear / vague / missing, a tip, the stars. The app shows it as a checklist where the user writes
  what they want per part.
- `optimize <id>` -> a better version from your check + the user's wishes (section 2b); the original stays.
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
- A prompt's `tags` = what it is for (vlog, talking head, sfx, transitions, colour, ... or the user's own): copy
  examples with the same tags and model first. Videos made from a prompt keep how they turned out per part in
  `projects\<p>\build\outcome.json` (the Prompts page shows it as "Used in"): repeat the parts rated good, fix bad.
- `shot <reference> f<a>-<b>` -> a shot prompt filled from a reference's frames (section 4)
- empty -> ask what they need: a new prompt (which kind) or adding examples
The app opens this with effort medium. Work from `C:\MotionLab` with `.venv\Scripts\python`; don't explore the lab.

## 0. Rules
- **Text only.** You never call a video model, an API or a website and never ask for a key - the user pastes the
  prompt into the site. (Paid generation through the API is 0.7.)
- **One home**: `knowledge\local\prompts\<kind>\<id>.json`, written only through `tools\prompts.py` (import /
  annotate / rate). Read with the MCP tool `prompts(kind)` / `prompts(id=...)` (or `prompts.py list / show`).
- Never invent a source or a result. Two ratings, never mixed: `result` = the user's Good / OK / Bad of what a model
  made (the Prompts page or `prompts.py rate`); `review` = YOUR reading of the text, 0-5 stars + why + fix (will a
  model do what it asks?). The user's rating always outranks your stars. Creators' prompts stay on this PC; keep
  their link or the file they came from (`source.file`).
- Frames you mention: frame number + timecode, e.g. `f480 (00:00:16:00)` (hard rule 2).
- No likeness of a real person without their consent; no logos / brands the user has no rights to.

## 1. The user pastes prompts
Save their text unchanged to a file in your scratchpad, then
`.venv\Scripts\python tools\prompts.py import <file>` (any text = one prompt, its kind guessed; lines of only `---`
separate several; the older `prompts.py template` format with kind / source / result lines still works; one bad
prompt = nothing saved, the error names it - never change their prompt text). Then split the new ones (section 2). Missing info (model, how it turned out) -> ask once, in one message, or leave it empty.

**Collected files (PDFs, docs) from creators**: read every file; one record per usable prompt (a guide with 10
templates = 10 records), text copied as written (no translation - say in the review when it should be translated),
`source` = creator (as the file names them, else "unknown") + `file`; a multi-step recipe (image prompt -> video
prompt) gets the same `workflow` name and `step` 1, 2, ...; `notes` = how to use it (what to upload, what to fill).
Save them as one JSON list (`prompts.py import <file>.json`) with `structure` and `review` already in it. Big PDFs
that don't render: extract the text in a scratch venv (`pypdf`), never into the lab's `.venv`.

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
missing). A part that does not apply to this prompt (no transitions in a single-shot prompt) gets no row.
- **Briefs** (kind `brief` = the user tells Claude how to make / edit a whole video), in the order a video is made
  (the app groups them): *the plan* - format & length (long / short form, minutes, aspect, platform), story & hook,
  feel / style (an analysed reference beats an adjective, section 2a), footage (folders, cameras, log profiles,
  b-roll: what covers what), order & structure; *the edit* - pacing & cuts, transitions, effects (zooms / punch-ins,
  speed ramps, shake, freeze frames); *sound* - voice & audio (silences cut, noise, levels, the voice over the
  music), music (licensed or made where), sfx; *look & text* - colour (one base LUT or per scene - never both),
  motion graphics, captions & text; *finish* - ending (outro, call to action, end screen), deliverable (Resolve
  project name, export), questions first (what Claude must ask before starting). Mark what the lab cannot do or
  measure today as vague with the tip. Skip parts that do not apply (no music in a silent edit).
- Wrong kind (a brief saved as a talking script): move it first - `prompts.py kind <id> <kind>` - and say the new id.
For each id: read it (`prompts(id=...)`), then write a JSON file and run
`.venv\Scripts\python tools\prompts.py annotate <id> <file>`:
```json
{"title": "Neon alley dolly-in", "pattern": "", "tags": ["night", "city"],
 "structure": [{"slot": "subject", "text": "a young man in a black hoodie"}, {"slot": "camera", "text": "slow dolly-in"}]}
```
- `structure` items: `{"slot": "colour", "text": "un mismo lut ... luts acorde a la escena", "status": "vague",
  "tip": "Pick one: one base LUT for the D-Log M clips + per-scene exposure / white balance, or a LUT per scene"}`.
  Slot names (`prompts()` lists them): brief = format & length, story & hook, feel / style, footage, order &
  structure, pacing & cuts, transitions, effects, voice & audio, music, sfx, colour, motion graphics, captions &
  text, ending, deliverable, questions first; shot = references, keep, change, subject, action, setting, camera,
  lens, light, look, motion, beats, audio, length / aspect, avoid; image = references, keep, change, subject,
  setting, composition, light, look, materials, avoid; hook = pattern, opening line, on screen, promise; script =
  hook, problem, points, proof, call to action (+ seconds per part when the script has them). `references` = what
  each upload is for, `keep` = what must not change, `change` = the transformation. Add a slot only when none fits.
- Hooks: `pattern` = question, bold claim, number, story, contrarian, demo, curiosity gap or call-out.
- Title (the card shows only the title, so it must say which prompt this is): 3-6 words in the prompt's language -
  what it makes + what sets it apart, e.g. "Londres día 1 · vlog estilo Clavero", "FPV drone around the subject",
  "Hook: nobody tells you this". Never "Prompt for...", an id or the model name. Replace the automatic title
  (first words of the text) when you check a prompt. Afterwards one line per prompt in the chat: id, title, the
  slot order.
- Put your `review` (section 1, "Reviewing") in the same JSON: `why` = the main point in two sentences, `fix` =
  the one change that helps most. In the chat afterwards: one line per prompt - id, title, n clear / vague /
  missing - and "write what you want next to the parts on the Prompts page, then click Optimize with Claude".

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
Read the prompt (`prompts(id=...)`): its check (each part's status / tip), its `review`, the user's wishes
("what the user wants") and its style references (section 2a - link a clear match first). Write ONE better
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
1. What they need - ask only for what is missing, in one message: brief = the footage (project folder, cameras),
   long / short form and length, the feel (an analysed reference - `- style:` or one it names, section 2a - else
   a link to analyse first), where it ends up (Resolve project name); shot = subject / story, model, length and aspect; hook = topic, audience, platform; script =
   topic, audience, length. A brief from zero: write every part of section 2's brief list, in sections.
2. Examples: `prompts(kind)` - best first (the user's good ratings, then your stars). Pick 1-2 and say so:
   "built on shot-003's structure, camera wording from shot-007". With `like <id>` start from that one, and apply its
   review's `fix`. Fewer than 3 examples of the kind: say the structure is thin and suggest adding tested prompts.
   A workflow step (e.g. image prompt -> video prompt) means writing the whole recipe, every step in order.
3. Write **3 variants** that keep the example's slot order, length and way of writing (comma list vs sentences,
   tense, how the camera is named) and change the content to the user's need. Each in its own code block (easy to
   copy) with one line of slots under it.
   - Shots: one shot per prompt, one camera move (or timed beats with seconds); lock what stays before describing
     the change; length / aspect the model offers (check the site's options). Images: references + locks first.
   - Hooks: the first 3 s = about 7-9 spoken words; name the pattern.
   - Scripts: seconds per part; ~2.5 spoken words per second.
4. Save them: a JSON list -> `prompts.py import <file>.json`, each with `"source": {"type": "written"}`,
   `"made_from": [example ids]`, kind, title, model, structure, review (your stars for your own text, honestly).
   Tell the user the new ids and: paste one into the
   site, then rate it on the Prompts page (Good / OK / Bad + a note) - good ones become the first examples.

## 4. A shot from a reference (`shot <reference> f<a>-<b>`)
Fill the slots from the analysis instead of guessing: `frame_info` / `events(reference, start=a, end=b)` (camera
moves with easing words, cuts inside the range), `frames(reference, "a-b:step")` to look at it (light, colours,
lens, framing), the size and fps for aspect and length ((b-a+1) / fps seconds, rounded up to what the model
offers - the edit trims it). The subject comes from the user's story, not the reference's people. Name the range as
`f<a>-<b> (<tc a> - <tc b>)`. Image-to-video: suggest a start frame from the user's own footage so the look matches.

## 5. Hooks from talking videos (until 0.4 step 2 automates it)
When the user names an analysed talking reference: `transcript(reference, 0, <3 s in frames>)` = its hook. Offer to
save it as a creator hook (JSON import, `source` creator + the link from `refs\downloads.json`), then split it.
