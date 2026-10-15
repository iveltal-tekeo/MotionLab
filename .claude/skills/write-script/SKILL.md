---
name: write-script
description: MotionLab - Prepare a video, the words said on camera, written for reach. Improve a script the user already has (check it part by part against the viral-script guidelines - hook, structure, re-hooks, payoff, call to action - then rewrite it in their voice) or write one from zero from the user's answers (topic, viewer, takeaway, their angle, length, tone, call to action, style of analysed videos). Use for "/write-script ...", "improve / rewrite my script", "write me a script", "mejora mi guion", "escríbeme un guion", "hooks for my video".
argument-hint: improve <script id> | check <script id> | request <req-NNN> | hooks <script id> | (empty = ask the questions)
---

# /write-script

`$ARGUMENTS`:
- `improve <script id>` → the app's *Improve my script* (and *Optimize with Claude* on a script / hook card): check
  it (section 2) if not checked yet, then rewrite it (section 3).
- `check <script id>` → only the check (section 2). The app's *Check it again*.
- `request <req-NNN>` → the app's *Write one from zero*: a script from the user's answers (section 4).
- `hooks <script id>` → 5-8 more hooks for that script in different patterns, saved as kind `hook` (section 5).
- empty → ask the questions of section 4 in one message, then write it (section 4, without a request id).

The app opens this with effort high. Work from `C:\MotionLab` with `.venv\Scripts\python`. Don't explore the lab.

## 0. Rules
- **Read `.claude\skills\write-script\guidelines.md` first, every time.** It holds the viral rules, the structures,
  the stars rubric and the script format.
- **Text only.** No model, no API, no website. The user films it.
- **One home**: scripts and hooks live in the prompt library (`knowledge\local\prompts\script|hook\`), written only
  through `tools\prompts.py import / annotate`. The app's requests are in `knowledge\local\prompts\requests\`; read
  them with `tools\script.py show <id>`.
- **Their voice, their facts.** Keep the user's language, expressions and every good line. Never invent a result, a
  number, a story or a credential for them. Facts they must confirm are marked `[check]`. Copy the style of
  creators (rhythm, structure), never their sentences.
- Script times are estimates in seconds: there is no video yet. When you cite a moment of an analysed video, give
  frame + timecode, e.g. `f45 (00:00:01:15)` (hard rule 2).
- **Keep the title's promise.** Before writing, look for the video's packaging: a title & thumbnail record
  (`prompts.py list title` - the one whose `request` / `project` is this video, or the one the user names) or
  `projects\<p>\build\publish\package.json` "title". When there is one, read it first: the hook delivers that promise
  in the first 3 s (said + on screen), confirming the title without repeating it word for word
  (`.claude\skills\write-title\guidelines.md` section 8).
- Before writing, read Claude's memory: `.venv\Scripts\python tools\knowledge.py memory` (or MCP
  `knowledge(category="memory")`). It has every analysed video's style in one line. The user's scripts rated good
  (`prompts(kind="script")`, best first) are the first examples of what works for them.

## 1. What you read
`.venv\Scripts\python tools\script.py show <id>` prints the script (or the request = the user's answers), what the
user wants from the rewrite (length, where it goes, their words, the videos whose style they picked), the scripts
already made from it, and **the check**. The check is measured and needs no Claude: the hook, the length at the
speaking rate measured on the picked videos, sentences, fillers, the longest flat stretch, you / I, numbers, the CTA,
the last line, the notes for what is on screen. Use its numbers and don't re-count them by hand.
Picked or linked analysed videos: `.venv\Scripts\python tools\style.py <name> [<name>]` (words per minute, words in
the first 3 s, cuts in the hook) and MCP `transcript(<name>, 0, <3 s in frames>)` for how its hook sounds
(guidelines section 10).

## 2. Check (`check`, and the first half of `improve`)
Write Claude's check of the script as a JSON file and save it with
`.venv\Scripts\python tools\prompts.py annotate <id> <file>`. The app shows it as a checklist, one card per part,
where the user writes what they want:
```json
{"title": "Edits that doubled my views", "pattern": "contrarian", "tags": ["talking head", "tutorial"],
 "structure": [{"slot": "hook", "text": "Hey guys, welcome back...", "status": "vague",
                "tip": "Open with the result: 'This one cut doubled my views' - greet never"}],
 "review": {"stars": 2, "why": "...", "fix": "..."}}
```
- **Every part of a script gets a row**, in this order: `hook` (the first 3 s: what is said + shown), `promise` (what
  they get by staying, the open loop), `problem` (why the viewer should care), `points` (the value: steps, tips,
  story beats), `re-hooks` (something new every few seconds, from the check's flat stretch), `proof` (example,
  result, numbers), `payoff` (the promise kept), `call to action` (one, specific, at the end), `on screen` (text,
  B-roll, punch-ins written as notes). `status` = `clear` / `vague` / `missing`. `text` = the script's own words for
  that part (verbatim, shortened with ...; "" when missing). `tip` = the concrete change in one sentence, in the
  script's language when you quote a new line.
- **The check's ✗ and ~ lines are evidence.** A part they flag is never `clear` unless you say why the rule does not
  apply (a story that needs "I", for example).
- `review`: stars = viral potential of the text (guidelines section 8). `why` in two sentences, `fix` = the one
  change that helps most. `pattern` = the hook's pattern. Title = 3-6 words in the script's language that say what the
  video is about (not "Script for...").
- In the chat afterwards: the check's score (n of 11), the stars, and the 3 biggest problems, each with its fix.

## 3. Improve (`improve <id>`)
1. Not checked yet (no part has a status): do section 2 first and save it.
2. Read the user's wishes: the request (`want`, length, where it goes, picked videos) and the card's wishes per part.
   Their wishes win over your tips.
3. Write **one** improved script in the format of guidelines section 9. Use the structure that fits the topic
   (guidelines section 3); keep theirs when it works. Every vague or missing part gets fixed. Fit the length they
   want, or the length the check measured when they gave none. Keep their voice and every good line word for word.
4. Write **3 hooks** in different patterns. Put the best one in the script; the other two go in `notes` ("Other
   hooks: ...").
5. Save it as a NEW script (the original stays): a JSON list → `.venv\Scripts\python tools\prompts.py import <file>.json`
   with `"kind": "script"`, `"source": {"type": "written"}`, `"made_from": ["<id>"]`, the same `tags` and
   `style_refs`, title "<old title> - improved" ("- improved 2" for the next one), its own `structure` (mostly clear
   now) + `review`, `pattern`, `notes`.
6. Run `.venv\Scripts\python tools\script.py check <new id>`. Fix what it still flags if the fix is right; if not,
   say why it doesn't apply (a 90 s story can have one longer stretch).
7. Tell the user: the new id and title; before → after (checks n → m of 11, length, hook words, stars); the 3-5
   changes that matter; and the next step. Rehearse it out loud (cut every line they stumble on). Click **Film it**
   on its card: the teleprompter, then add the recording there and it gets edited; rate it once it's out.

## 4. From zero (`request <req-NNN>` or empty)
1. `tools\script.py show <req>` = the user's answers. Only the topic is required. When something important is
   missing, ask in ONE message. For everything else use a default and say which: their viewer = the topic's obvious
   one, a 30-45 s vertical short, the tone of their picked videos (else calm and clear), CTA = follow for more, the
   language of their answers.
2. Their angle (story, result, opinion) is the raw material for the hook. Without one, the hook uses the takeaway
   (result first or a question), and you ask once whether they have a story or a number for it.
3. Pick the structure (guidelines section 3) and say why in one line. Write 3 hooks in different patterns, then the
   full script with the best one, in the format of guidelines section 9: parts with seconds, `[TEXT]` / `[B-ROLL]` /
   `[ZOOM]` notes, the must-say points in, one CTA with a reason.
4. Check it: write it to a file, run `.venv\Scripts\python tools\script.py check <file> --length <s> [--like ...]`,
   and fix what it flags until the hook, length, re-hooks and CTA pass, or say why one shouldn't.
5. Save it: `prompts.py import` with `"kind": "script"`, `"source": {"type": "written"}`, `"request": "<req-NNN>"`
   (the app links it to the request), `style_refs` = the picked videos that are analysed on this PC, `structure` with
   statuses + `review` + `pattern` + `notes` (the other 2 hooks, and how to deliver it: energy, where to pause, which
   word to punch in on).
6. Tell the user the id, the hook, the length, n of 11 checks, and the next step (rehearse it, **Film it** on its
   card - teleprompter, add the recording, edit it - then rate it).

## 5. More hooks (`hooks <script id>`)
5-8 hooks for the script's topic in different patterns (guidelines section 4), each 7-12 words, each with its
`[TEXT: ...]` and `[VISUAL: ...]` line. Save them as kind `hook`, `made_from: ["<script id>"]`, `pattern` set,
`structure` = pattern / opening line / on screen / promise. Tell the user the ids and which one you would film first.

## 6. After filming
The user films it from the script card's *Film it* (cue cards, a teleprompter, what to film besides them; then the
recording is added there - copied into a new video named after the script - and edited: the talking quick draft or
`/recreate-video prompt:<id>`, which follows the script; the
talking quick draft cuts the pauses). How it turned out (the video's *How did it turn out?*) and their rating on the
card tell you what works for them next time. Repeat those patterns and drop the ones rated bad.
