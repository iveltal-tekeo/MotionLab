---
name: write-title
description: MotionLab - the packaging of a video, written for clicks that the video keeps. Title & thumbnail first (before filming, from the user's answers - topic, viewer, angle, platforms, orientation, language, style of analysed videos - about 10 titles in different patterns, 2-3 thumbnail concepts with the 2-4 words and the shot to film for each, and the hook that keeps the promise), the final package of a finished video (title, description with YouTube chapters, hashtags, thumbnails A / B / C from its frames or an AI image), and 3 variants for YouTube's Test & compare. Use for "/write-title ...", "titles", "a title for my video", "thumbnail", "thumbnails", "cover", "packaging", "chapters", "description", "hashtags", "A/B test", "título", "títulos", "miniatura", "miniaturas", "portada", "descripción", "capítulos".
argument-hint: request <req-NNN> | package <project> | ab <project> | (empty = ask the questions)
---

# /write-title

`$ARGUMENTS`:
- `request <req-NNN>` → the app's *Title & thumbnail first* (Prepare): titles, thumbnail concepts and the hook from
  the user's answers, before filming (section 2).
- `package <project>` → the final package of a finished video in `projects\<project>\build\publish\` (section 3).
- `ab <project>` → 3 variants for YouTube Studio's Test & compare (section 4).
- empty → ask the questions of section 2 in one message, then write it (section 2, without a request id).

Work from `C:\MotionLab` with `.venv\Scripts\python`. Don't explore the lab.

## 0. Rules
- **Read `.claude\skills\write-title\guidelines.md` first, every time.** It holds the title and thumbnail rules
  (platform rules with their dates, rules of thumb marked as such), the patterns, the shot to film, the vertical
  covers, Test & compare and the description / chapter / hashtag rules.
- **One home**: titles and thumbnail concepts live in the prompt library as kind `title`
  (`knowledge\local\prompts\title\`), written only through `tools\prompts.py import / annotate`. Read a request with
  `tools\script.py show <req-NNN>`. The ready-to-post files live only in `projects\<p>\build\publish\`, written by
  `tools\publish.py` (title, description, chapters, hashtags) and `tools\thumbnail.py` (thumbnails). Never write
  `package.json` by hand: each tool updates only its own keys.
- **Hard rules**: never touch the user's footage or a source video (read only). Every frame you mention has frame +
  timecode, e.g. `f480 (00:00:16:00)`.
- **Their facts.** Never invent a result, a number or a story for them. Facts they must confirm are marked `[check]`.
  Copy the patterns of outperforming creators, never their titles.
- **No clickbait the video doesn't keep.** Test & compare picks the winner by watch time, and a broken promise
  costs both.
- Before writing, read Claude's memory: `.venv\Scripts\python tools\knowledge.py memory` (every analysed video's
  style in one line, the user's ratings as rules). Title records the user rated good (`prompts.py list title`) are
  the first examples of what works for them.

## 1. What you read
- `tools\script.py show <req-NNN>`: topic, viewer, angle, platforms (youtube / shorts / tiktok / instagram),
  orientation (horizontal / vertical / both), language, style references (analysed videos), notes.
- Picked style references: `.venv\Scripts\python tools\style.py <name> [<name>]` (format, hook, text on screen) and
  how their thumbnails look: `.venv\Scripts\python tools\thumbnail.py refs [--niche <category|tag>]` (the niche's
  outperformers first).
- For `package` / `ab`: `.venv\Scripts\python tools\publish.py show <project>` (what is there already), the video's
  title record if one exists (`prompts.py list title`: its `request` or `project`), the edit (`build\plan_vN.json`,
  `draft_vN.md`) and its script (a kind `script` record) if it had one.
- **What won before** (every mode): each `projects\*\build\outcome.json` `"packaging"` - `ctr` per variant (the
  highest = the winner: name what made it different - its words, face / expression, design, colours, from that
  project's `package.json` `thumbnails[id]` - and repeat that pattern) and `aspects.packaging` (a bad rating is a rule
  in Claude's memory: "Title and thumbnail: ..."). Prefer title records the user rated good and their notes.

## 2. Title & thumbnail first (`request <req-NNN>` or empty)
0. **A record from this request exists already** (the app's *Write new ones with Claude*): read it - its rating, note
   and your check's tips - and write a NEW record with `"made_from": ["title-NNN"]` that fixes what was weak; never a
   duplicate of the same titles.
1. Only the topic is required. When something important is missing (above all the angle: their story, number or
   opinion), ask in ONE message. For the rest use a default and say which: the viewer = the topic's obvious one,
   platforms = YouTube, orientation from the platforms (YouTube = horizontal, Shorts / TikTok / Reels = vertical,
   both = both), the language of their answers.
2. Write the promise in one sentence (guidelines section 2).
3. **About 10 titles, each in a different pattern** (guidelines section 4: curiosity gap, number / result, how-to,
   warning / mistake, question, I tried, before -> after, contrarian, challenge, list, story, call-out). Check each
   against the title rules (section 3): its characters (under ~60 for a phone, never over 100), the key words first,
   specific, one promise the video can keep. A title that breaks a rule gets fixed or a `note` that says why.
4. **2-3 thumbnail concepts** (A, B, C), each for one of the titles and different in ONE idea (the emotion, the words
   or the subject): `sketch` = the picture in words (where the face / subject is, where the words go, the background),
   `words` = the 2-4 words on it (they add to the title, never repeat it), `shot` = **the shot to film for it**
   (framing for 16:9 and / or the 9:16 cover, expression or action held 2-3 s, the prop, the light), `colours`.
   For vertical platforms say how the cover reads (guidelines section 7).
5. **The hook** (first 3 s) that keeps the titles' promise, in the `/write-script` format: what is said +
   `[TEXT: ...]` + `[VISUAL: ...]`.
6. Save it: a JSON list → `.venv\Scripts\python tools\prompts.py import <file>.json` with `"kind": "title"`,
   `"source": {"type": "written"}`, `"request": "<req-NNN>"` (empty mode: none), `title` = 3-6 words that say what
   the video is (the card's name), `titles`, `concepts`, `hook`, `pattern` = the pattern of the title you would test
   first, `style_refs` (picked videos analysed on this PC), `structure` = your check per slot (`titles`, `thumbnail`,
   `words on it`, `shot to film`, `colours`, `hook`: clear / vague / missing + a tip), `notes` (which 2-3 titles to
   test first and why; what to film first). Then `prompts.py show <id>` and read it back.
7. Tell the user: the id, the 3 titles you would test first, the concepts in one line each, the shots to film, the
   hook, and the next step: *write the script* (`/write-script request ...` - its hook keeps this promise), film the
   thumbnail shots, edit, then the package.

## 3. The final package (`package <project>`)
1. **The title.** From the video's title record - a record with `"project": "<project>"` first: the user linked it
   with *Use this title*, and its `chosen` is their pick - else the best one for the video as it was made (what the
   edit really delivers), or new ones when there is none (section 2, steps 2-3). Save the final choice on the record:
   `prompts.py annotate <id> <file>` with `{"chosen": "...", "project": "<project>"}`; with no record, save a new one
   with `"project": "<project>"`.
2. **Chapters.** `.venv\Scripts\python tools\publish.py chapters <project> [--from plan|transcript]` lists the
   candidate points with frame + timecode (the edit plan's picture changes, or the pauses and topic shifts of the
   video's words when `build\speech\` has them - a transcript of the final render, from `speech.py transcribe`).
   Pick the ones where the video really changes, starting from the suggested set, and name each in 1-4 words in the
   video's language. YouTube needs 0:00 first, at least 3, each at least 10 s; a short video without 3 real parts gets
   no chapters (leave `--chapters` out).
3. **Description + hashtags.** Write the description's own words to a .txt (the first 1-2 lines repeat the promise in
   other words with the search words; then what is in it; credits). 3-5 hashtags, the best 3 first.
4. Write it: `.venv\Scripts\python tools\publish.py write <project> --title "..." --chapters "f|name;f|name;..."
   --hashtags "#a #b #c" --description-file <txt> [--titles <title-NNN>]` → `build\publish\title.txt`,
   `description.txt`, `hashtags.txt` + `package.json`. On a FAIL nothing is written: fix it and run it again.
   `publish.py show <project>` prints the folder.
5. **Thumbnails A / B / C** (`tools\thumbnail.py`):
   1. `.venv\Scripts\python tools\thumbnail.py candidates <project> [--n 12]` → `build\publish\candidates.png`, a
      sheet with frame + timecode on every tile. Read the sheet.
   2. Pick 3 moments that fit the concepts (the shots filmed for them first), different in one idea each.
   3. `.venv\Scripts\python tools\thumbnail.py make <project> --id A --frame <f> [--clip <id>] --words "..."
      [--template <name>] [--set k=v]` for A, B and C (`thumbnail.py templates` lists the templates). For a vertical
      video or a request for both orientations: the 16:9 thumbnail and the 9:16 cover.
   4. `.venv\Scripts\python tools\thumbnail.py check <project> --title "<the final title>" [--script <id|file>]
      [--niche <category|tag>]` → PASS / WARN / FAIL per rule. Fix every FAIL (bigger words, fewer words, another
      frame, more contrast) and run the check again until it passes; say why a WARN stays.
   5. **AI-image route** (the user wants a generated picture, or no frame works): write the image prompt with
      `/write-prompt image` (kind `image`, the user's photo as the reference, the concept's sketch and colours, NO
      words in the picture - the lab adds them). The user makes it on the site and brings the file back; then
      `thumbnail.py make <project> --id A --image <file> --words "..."` and the check as above.
6. Tell the user: the final title, the chapters as `0:00 Name = f<f> (<timecode>)`, the hashtags, the thumbnails A / B
   / C with their check, and that all of it is on the video's Overview in the app, under **Ready to post** (Editor >
   the video: change a thumbnail's words / colours and render it again, edit chapters, copy the texts, open the
   folder). Next step: post it, then type the CTR per variant under *After posting* at the end of Ready to post
   (section 5) so the next package repeats what won.

## 4. Test & compare (`ab <project>`)
1. Read the current limits in guidelines section 9 (checked 2026-10-15): up to 3 variants, title only / thumbnail
   only / both, YouTube Studio on a computer only, the winner by watch time, no Shorts. A Short gets no test: say so,
   and make one cover instead.
2. Make 3 variants that differ in ONE idea each (the emotion, the words or the subject - guidelines section 9): from
   the package's thumbnails A / B / C (section 3 step 5) and, for *title and thumbnail*, the 3 best titles of the
   record, each paired with the thumbnail it was written for.
3. Every variant passes `thumbnail.py check` with its own title.
4. Tell the user: what each variant tests (one line), the files, and how to start it: YouTube Studio on a computer >
   the video > Thumbnail > *Test & compare* > upload A, B, C (and the titles); results in a few days up to two weeks.

## 5. After posting
CTR lives in YouTube Studio and the lab never logs into accounts. The user types the CTR per variant and the video's
link under the video's Ready to post > *After posting* (its rating of the title and thumbnail: the Review tab's *How
did it turn out?*) -> `build\outcome.json` `"packaging"`:
`{"ctr": {"A": 4.1, "B": 5.2}, "link": "...", "updated": "..."}`. Read it before the next package (section 1) and
repeat the patterns that won (title pattern, the kind of words on the thumbnail, the emotion); drop the ones that
lost. A posted video's public numbers are not fetched yet (`content.py stats` writes into analyses only).
