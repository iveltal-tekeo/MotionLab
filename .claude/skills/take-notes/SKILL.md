---
name: take-notes
description: MotionLab - notes from a video (the Analyser's Notes): what it says and shows, written like a professional's notes - a TL;DR, 3-7 key takeaways, the sections (the creator's chapters), the steps of a how-to, what to apply to yourself, the resources it links and a context block to paste into another AI, every point tied to the video's own words with frame + timecode. Use for "/take-notes <name>", "/take-notes pending", "take notes on this video", "notes of", "summarise this video", "toma notas", "resume este vídeo".
argument-hint: <name> | pending
---

# /take-notes

If the first message says to reply in Spanish, talk to the user in Spanish (Spain, tú); write the notes in the
video's own language unless the user's question (`ask`) asks for another; what you write into the lab stays as the
notes themselves.

`$ARGUMENTS`:
- `<name>` → the notes of `analysis\notes\<name>\` (the app prepared them: the words, key frames, chapters).
- `pending` → `tools\notes.py pending` lists every video waiting; write each one's notes in turn (one at a time, a
  line to the user after each).
- a link or a file instead → tell the user to add it in the app (Analyser > Notes > *Take notes*), or run
  `.venv\Scripts\python tools\notes.py prepare "<video>" [--url <link>]` yourself for a file already on this PC.

Work from `C:\MotionLab` with `.venv\Scripts\python`. Don't explore the lab. Never ask the user to correct anything
first (the user's ask: Claude's part runs by itself); finish, then say what you made.

## 1. Read
1. `tools\notes.py show <name>` - the video, the user's question (`ask`: what they want from it - it decides what the
   notes stress), the chapters, the *Most replayed* moments, the sponsor parts (never quoted), the paths.
2. The transcript: `content\transcript.txt` (one line per caption with f480 (00:00:16:00)). Long videos: read it whole
   anyway - the notes must cover the end too.
3. The key frames (`frames\sheet_NN.jpg`, labelled) **only when what is shown matters**: a tutorial, slides, code,
   a screen recording, a recipe, a diagram, a video without words. A talking head or a podcast needs none.
4. `content\info.json`: the description (its links are the only resources you may name), tags, the language.
5. With an `apply` about the user's own work: `knowledge\local\brand.json` when show names it (their goal, audience,
   what they sell) - the actions fit THEM, not a generic viewer.

## 2. Think first, then write (quotes first)
- Name the **kind**: tutorial (steps first), lecture / explainer (the concepts), interview / podcast (the topics, who
  said what), list (the list itself), opinion / news (the claims and their evidence), story, other.
- Pick the quotes first: the exact words where each idea is said (3+ words, at most 400 characters, word for word
  from the transcript; `...` joins two pieces of one passage). Then write each point in plain words around its quote.
- A point the video only SHOWS (a slide, a value on screen, a step done without words): `"shown": <frame>` - one of
  the frames on the sheets (frames.json), no quote.

## 3. The draft (JSON, written with the Write tool into `.app\dev\notes_<name>.json`)
```json
{"kind": "tutorial", "lang": "en", "title": "the subject in plain words, not the clickbait title",
 "tldr": "One or two sentences: what it is about and what it concludes.",
 "takeaways": [{"phrase": "Charge for outcomes", "text": "One sentence in plain words.",
                "quote": "charge for the outcome not the hours", "at": 5400}],
 "sections": [{"title": "Pricing", "gist": "one line", "chapter": 1,
               "points": [{"text": "...", "quote": "..."}, {"text": "...", "shown": 4410}]}],
 "steps": [{"text": "Open the colour page and ...", "quote": "..."}],
 "apply": ["One concrete action the user can take this week."],
 "resources": [{"name": "The template", "url": "https://... (from the description)"}],
 "ai_context": "A block the user pastes into ChatGPT / Claude / another tool: what the video teaches as facts and rules, in a few short paragraphs or bullets - no frame numbers, no 'the video says'.",
 "tags": ["pricing", "freelance"]}
```
- **Not crowded** (the user's ask - professional, not crowded; the tool enforces the limits): TL;DR 1-2 sentences;
  3-7 takeaways (a bold 2-6-word phrase + ONE sentence) - the ideas a reader keeps, not a list of everything;
  sections = the creator's chapters when there are some (`chapter` = its number from show, from 0), else 3-6 of your
  own, each a title + one-line gist + at most 5 points; `steps` only for a how-to (leave it out otherwise); 1-5
  `apply` actions, concrete and doable; `resources` only links the description gives (none = leave it out).
- `at` = a frame hint when a quote is said more than once (the tool picks the nearest). The tool finds every quote and
  sets the frame + timecode itself - never type a timecode into a text.
- Prefer a *Most replayed* moment's idea as a takeaway when it is one (show lists them; the page marks it).
- Leave out sponsor reads, self-promotion and "like and subscribe" (a quote inside a sponsor part is refused).
- Facts the video states are its claims: write "she says X costs Y", not "X costs Y", when it is a number or a claim
  you cannot check.

## 4. Save through the gate
`.venv\Scripts\python tools\notes.py save <name> .app\dev\notes_<name>.json` - nothing is saved when a check fails;
it lists every problem (a quote not found word for word, a frame not on the sheets, a link not in the description,
too many items). Fix those and save again; never write notes.json / notes.md by hand, never touch `mine.md` (the
user's own notes).

## 5. Tell the user
In two or three lines: the TL;DR, how many takeaways / sections / steps / actions, and that the notes are in
Analyser > Notes (the page plays each point's moment; *Download* gives the Markdown, *Copy for another AI* the
context block). Every time you mention has frame + timecode, e.g. f480 (00:00:16:00).
