# Title & thumbnail guidelines (packaging for clicks)

Read this before every title or thumbnail you write (`/write-title`). Two kinds of rules live here, and each one says
which it is:
- **Platform rules** come from the platforms' own help pages. They are hard limits, and `tools\publish.py` /
  `tools\thumbnail.py` check them. Each has the date it was checked. Platforms change them, so check again when one
  looks wrong.
- **Rules of thumb** are creator practice. They are NOT measured on the user's videos. The user's own results come
  first: their CTR per variant (typed in after posting), how their videos turned out, and the outperforming
  references of their niche (`thumbnail.py refs`, views ÷ followers). Then come these rules.

## 1. What packaging does
- The title and the thumbnail are seen **before** the video. Together they decide the click-through rate (CTR): how
  many of the people shown the video click it. That is the first line of the hook.
- **The click is a promise.** YouTube's own A/B test (Test & compare) picks the winner by **watch time**, not by CTR
  (platform docs, 2026-10-15). A title that gets clicks and then disappoints loses. So the video delivers what the
  packaging promised, and it starts in the first 3 s.
- **Packaging first** (*Title & thumbnail first*, before filming): many creators decide the title and thumbnail
  before they film, so the video is built to keep the promise and the thumbnail's shot gets filmed on purpose
  (creator practice).

## 2. Before writing: one promise
- Say the promise in one sentence: "the viewer clicks because they want to ___". Two promises = two videos.
- The viewer: who it is for. The angle: the user's own story, result, number or opinion. That is usually the best
  title. Never invent it: facts the user must confirm are marked `[check]`.
- Write titles in the user's language (the request's `language`, else the language of their answers).

## 3. Title rules
| rule | what it means | source |
|---|---|---|
| **At most 100 characters** | YouTube refuses a longer title. Studio also refuses `<` and `>`. | platform docs (YouTube help 57404), checked 2026-10-15 |
| **About 50-60 characters on a phone** | Feeds cut a long title, and how much shows depends on the screen and the surface (home, search, suggested). Write it so the first ~50 characters work alone. | rule of thumb (creator practice); the exact cut is not documented |
| **Front-load the key words** | The words that make someone click (and the ones they search for) go in the first 3-5 words. Never start with the channel name, "Vlog #12" or a date. | rule of thumb |
| **Specific beats vague** | A number, a time, a place, a result: "at 4AM", "in 24 hours", "for €0", "3.4M views". | rule of thumb |
| **One promise, kept** | No clickbait the video doesn't keep. If the title says "I tried X", the video shows X. | rule of thumb + the watch-time winner above |
| **The thumbnail adds, never repeats** | The title and the thumbnail's words say two different things that complete each other (title: what happens; thumbnail: the emotion, the result or the stakes). | rule of thumb |
| **Spoken words** | Words the viewer would say. At most one word in CAPITALS for stress. No hashtags in the title (they take the characters a phone shows). | rule of thumb |
| **Shorts / TikTok / Reels** | The title (or caption) shows small and briefly over the video: the first 3-5 words carry it, and the video's first frame does the rest. Put searchable words early. | rule of thumb |

## 4. Title patterns (write about 10, each in a different pattern)
`prompts.TITLE_PATTERNS`. Name the pattern of every title. Examples are for a made-up video; never copy them as they are.
| pattern | English | Español |
|---|---|---|
| **curiosity gap** | Nobody Tells You This About Filming at Night | Nadie te cuenta esto de grabar de noche |
| **number / result** | 3 Lights, 1 Room, a Whole Music Video | 3 luces, 1 habitación y un videoclip entero |
| **how-to** | How to Film a Music Video in Your Bedroom | Cómo grabar un videoclip en tu habitación |
| **warning / mistake** | Don't Film at Night Until You Know This | No grabes de noche sin saber esto |
| **question** | Can You Make a Music Video With No Budget? | ¿Se puede hacer un videoclip sin presupuesto? |
| **I tried** | I Tried Copying a 3M-View Music Video Shot by Shot | Intenté copiar un videoclip de 3 millones plano a plano |
| **before -> after** | My Room at 4PM vs 4AM | Mi habitación a las 4PM vs a las 4AM |
| **contrarian** | You Don't Need a Studio for a Music Video | No necesitas un estudio para un videoclip |
| **challenge** | One Night, One Room: Can I Finish a Music Video? | Una noche, una habitación: ¿termino un videoclip? |
| **list** | 5 Shots Every Bedroom Music Video Needs | 5 planos que necesita todo videoclip casero |
| **story** | I Couldn't Sleep, So I Made a Music Video | No podía dormir, así que hice un videoclip |
| **call-out** | If You Film on a DJI, Watch This | Si grabas con una DJI, mira esto |

Check every title against section 3: its characters (the record counts them), the key words in the first 3-5
words, specific, one promise the video keeps, and what its thumbnail adds. Say which 2-3 you would test first.

## 5. Thumbnail rules
| rule | what it means | source |
|---|---|---|
| **YouTube video: 16:9** | At least 640 px wide, JPG or PNG, up to 50 MB from a computer (2 MB from a phone); the help page lists 3840×2160 as the size to use (the lab makes 1280×720, which works). A verified account is needed. | platform docs (YouTube help 72431), checked 2026-10-15 |
| **Shorts: 9:16** | 2160×3840 suggested, at least 640 px tall. A custom Shorts thumbnail is uploaded only in YouTube Studio on a computer, and since July 2026 only for some channels (Partner Program first, widening). Others pick a frame of the video in the YouTube app (any frame, also after posting) or one of 3 suggested frames in Studio. | platform docs (YouTube help 72431) + YouTube's July 2026 announcement as reported, checked 2026-10-15 |
| **Readable at feed size** | A phone feed shows a thumbnail about 160-360 px wide. If the words can't be read there, they don't exist. `thumbnail.py check` measures it. | rule of thumb (the check measures it) |
| **2-4 words** | Big: at least ~20 % of the picture's height. One idea. | rule of thumb |
| **One face, one clear emotion** (when it fits) | Shock, joy, doubt, focus: slightly over-acted, eyes visible, the face large. A music video or a place can lead with the subject instead. | rule of thumb |
| **One subject, three elements at most** | A face or a subject + the words + one object or colour block. Clutter is unreadable small. | rule of thumb |
| **Contrast** | Text against its background (the check uses the WCAG ratio); the subject lit brighter than the background; one strong accent colour. Brightness and saturation are compared with the niche's outperformers (`thumbnail.py refs`). | rule of thumb (the check measures it) |
| **Keep the bottom right clear** | YouTube puts the video's length there. | rule of thumb |
| **It shows something the video has** | The moment, the place, the object. A thumbnail of something that never happens is clickbait. | rule of thumb |

## 6. The shot to film for it (Title & thumbnail first)
Every thumbnail concept says what to film so the picture exists:
- **Framing**: where the subject sits and where the words go (the subject on one third, the words on the other; for
  the 9:16 cover the face in the middle band - see section 7). A wide enough frame to crop both 16:9 and 9:16 when the
  request is for both.
- **Expression / action**: the emotion, held for 2-3 s so a sharp frame exists (or a photo burst).
- **Prop**: the object of the promise in the picture (the camera, the clock, the lamp).
- **Light**: the face lit, the background a step darker, one colour light for the accent; no motion blur on the face.
- **Colours**: 2-3 colours that also suit the text.
`thumbnail.py candidates` later finds the sharp, still, well-lit frames of it.

## 7. Vertical covers (Shorts, TikTok, Reels)
| platform | the cover | source |
|---|---|---|
| **YouTube Shorts** | Section 5. No A/B test for Shorts (Test & compare excludes them). | platform docs, checked 2026-10-15 |
| **TikTok** | In the app: pick a frame of the video, or upload a picture from the gallery, and add text on the cover. 1080×1920. The profile grid crops the cover around its centre and the caption covers the bottom, so the words and the face go in the middle. Tools outside the app can usually only pick a frame. | creator guides, not TikTok's own docs, checked 2026-10-15 |
| **Instagram Reels** | Upload the cover at 1080×1920. The profile grid has shown a 3:4 crop since 2025, so keep the words and the face inside the middle 1080×1440 (the cover template marks the 4:5 / 1:1 crops too). | creator guides, not Meta's docs, checked 2026-10-15 |
For a vertical video the first frame is a second cover: the hook's first picture (`/write-script`) shows the same
promise.

## 8. The hook keeps the promise
- The hook line (the first 3 s) **delivers or proves the title's promise**: the result shown, the question asked out
  loud, the "4AM" on screen. It does not repeat the title word for word. It confirms it.
- Write it in the `/write-script` format: what is said + `[TEXT: ...]` + `[VISUAL: ...]`. `/write-script` uses the
  saved record's hook when it writes the script.

## 9. YouTube Test & compare (`ab`)
Checked 2026-10-15 (YouTube help 13861714):
- **Up to 3** variants: *Thumbnail only*, *Title only*, or *Title and thumbnail* together.
- Only in **YouTube Studio on a computer**, with advanced features turned on.
- The winner = the variant with the **most watch time** (not CTR). A test takes from a few days up to two weeks.
- Not for **Shorts**, scheduled livestreams or Premieres (a Premiere can be tested after it ends). Not for videos
  made for kids, for mature audiences or private ones; age-restricted videos don't run a test.
- Make the 3 variants different in ONE idea (the emotion, the words, the subject), not three small changes of one
  picture. Otherwise the test can't teach anything.

## 10. Description, chapters, hashtags (`tools\publish.py` checks them)
Platform rules, checked 2026-10-15:
- **Chapters** (YouTube help 9884579): timestamps in the description, the first at `0:00`, at least 3 in ascending
  order, each chapter at least 10 s long. They replace the automatic chapters. publish.py writes `0:00 Name` lines
  (`1:02:03` once the video passes an hour) at the whole second each chapter's frame falls in, and keeps the frame +
  timecode in package.json.
- **Hashtags** (YouTube help 6390658): up to 3 of them show by the title. More than 60 on a video means YouTube
  ignores all of them. 3-5 relevant ones is a rule of thumb. A hashtag is letters, digits and `_` (no spaces).
- **Description** (YouTube help 57404): up to 5,000 characters, no `<` `>`. The first one or two lines show before
  "more", so they repeat the promise in other words and hold the main search words (rule of thumb).
- **Chapter names**: 1-4 words in the video's language that say what happens (rule of thumb).

## 11. How a title record looks
Kind `title` in the prompt library (`tools\prompts.py import`):
```json
{"kind": "title", "source": {"type": "written"}, "request": "req-001", "title": "4AM bedroom music video",
 "titles": [{"text": "I Filmed a Music Video in My Room at 4AM", "pattern": "story"}],
 "concepts": [{"id": "A", "title": "1", "sketch": "...", "words": "NO STUDIO", "shot": "...", "colours": "..."}],
 "hook": "[TEXT: 4:00 AM] [VISUAL: ...] Said: ...", "pattern": "story", "tags": ["music video"],
 "structure": [{"slot": "titles", "text": "...", "status": "clear"}], "notes": "test 1, 4 and 7 first"}
```
`chars` is counted when it is saved. `concepts[].title` = the number of the title it goes with. `project` = the video
it packages (the `package` mode). `chosen` = the final title.
