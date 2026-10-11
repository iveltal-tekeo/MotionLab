---
name: write-prompt
description: MotionLab - the prompt library (0.4). Save the user's proven prompts (video-model shots for Seedance / Higgsfield / Kling, hooks, talking scripts), split each into its structure, and write new prompts that follow a structure that worked. Use for "/write-prompt ...", when the user pastes prompts (PROMPT 1 / kind / source / result / text blocks), or asks for a Seedance / video prompt, a hook or a script.
argument-hint: split <ids> | <shot|hook|script> [like <id>] | shot <reference> f<a>-<b>
---

# /write-prompt

`$ARGUMENTS`:
- `split <id> <id> ...` -> split those prompts into structure (section 2)
- `<kind>` or `<kind> like <id>` -> write a new prompt (section 3; `like` = start from that example)
- `shot <reference> f<a>-<b>` -> a shot prompt filled from a reference's frames (section 4)
- empty -> ask what they need: a new prompt (which kind) or adding examples
The app opens this with effort medium. Work from `C:\MotionLab` with `.venv\Scripts\python`; don't explore the lab.

## 0. Rules
- **Text only.** You never call a video model, an API or a website and never ask for a key - the user pastes the
  prompt into the site. (Paid generation through the API is 0.7.)
- **One home**: `knowledge\local\prompts\<kind>\<id>.json`, written only through `tools\prompts.py` (import /
  annotate / rate). Read with the MCP tool `prompts(kind)` / `prompts(id=...)` (or `prompts.py list / show`).
- Never invent a source, a rating or a result: ratings are the user's (the Prompts page or `prompts.py rate`).
  Creators' prompts stay on this PC; keep their link.
- Frames you mention: frame number + timecode, e.g. `f480 (00:00:16:00)` (hard rule 2).
- No likeness of a real person without their consent; no logos / brands the user has no rights to.

## 1. The user pastes prompts
Save their text unchanged to a file in your scratchpad, then
`.venv\Scripts\python tools\prompts.py import <file>` (format: `prompts.py template`; one bad block = nothing saved,
the error names it - fix only the format with the user, never their prompt text). Then split the new ones
(section 2). Missing info (model, how it turned out) -> ask once, in one message, or leave it empty.

## 2. Split into structure (`split`)
For each id: read it (`prompts(id=...)`), then write a JSON file and run
`.venv\Scripts\python tools\prompts.py annotate <id> <file>`:
```json
{"title": "Neon alley dolly-in", "pattern": "", "tags": ["night", "city"],
 "structure": [{"slot": "subject", "text": "a young man in a black hoodie"}, {"slot": "camera", "text": "slow dolly-in"}]}
```
- Slots in the order they appear in the prompt, `text` = the prompt's own words (verbatim, shortened with ... if
  long). Slot names (`prompts()` lists them): shot = subject, action, setting, camera, lens, light, look, motion,
  audio, length / aspect, avoid; hook = pattern, opening line, on screen, promise; script = hook, problem, points,
  proof, call to action (+ seconds per part when the script has them). Add another slot name only when nothing fits.
- Hooks: `pattern` = question, bold claim, number, story, contrarian, demo, curiosity gap or call-out.
- Title: up to 6 words, what it makes. Afterwards one line per prompt in the chat: id, title, the slot order.

## 3. Write a new prompt
1. What they need - ask only for what is missing, in one message: shot = subject / story, model, length and aspect;
   hook = topic, audience, platform; script = topic, audience, length.
2. Examples: `prompts(kind)` - best first (rated good, tested before written before creator). Pick 1-2 and say so:
   "built on shot-003's structure, camera wording from shot-007". With `like <id>` start from that one. Fewer than
   3 examples of the kind: say the structure is thin and suggest adding the user's tested prompts.
3. Write **3 variants** that keep the example's slot order, length and way of writing (comma list vs sentences,
   tense, how the camera is named) and change the content to the user's need. Each in its own code block (easy to
   copy) with one line of slots under it.
   - Shots: one shot per prompt, one camera move; length / aspect the model offers (check the site's options).
   - Hooks: the first 3 s = about 7-9 spoken words; name the pattern.
   - Scripts: seconds per part; ~2.5 spoken words per second.
4. Save them: a JSON list -> `prompts.py import <file>.json`, each with `"source": {"type": "written"}`,
   `"made_from": [example ids]`, kind, title, model, structure. Tell the user the new ids and: paste one into the
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
