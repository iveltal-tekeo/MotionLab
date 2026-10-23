# /write-title - title & thumbnail first

Read after SKILL.md (sections 0, 1 and 5).

## 2. Title & thumbnail first (`request <req-NNN>` or empty)
0. **A record from this request exists already** (the app's *Send it to Claude* on it, was *Write new ones with
   Claude*): read it - its rating, note and your check's tips - and write a NEW record with `"made_from": ["title-NNN"]`
   that fixes what was weak; never a duplicate of the same titles. The user's per-part verdicts (`verdicts`, the app's
   *Is Claude right?*; their wishes per part are the notes): Wrong = the user disagrees with your check of that part,
   keep their words unless the note says otherwise; Partly = follow the note; Correct = your check stands.
1. Only the topic is required. When something important is missing (above all the angle: their story, number or
   opinion), ask in ONE message. For the rest use a default and say which: the viewer = the topic's obvious one,
   platforms = YouTube, orientation from the platforms (YouTube = horizontal, Shorts / TikTok / Reels = vertical,
   both = both), the language of their answers.
2. Write the promise in one sentence (guidelines section 2).
3. **About 10 titles, each in a different pattern** (guidelines section 4: curiosity gap, number / result, how-to,
   warning / mistake, question, I tried, before -> after, contrarian, challenge, list, story, call-out). Check each
   against the title rules (guidelines section 3): its characters (under ~60 for a phone, never over 100), the key words first,
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
