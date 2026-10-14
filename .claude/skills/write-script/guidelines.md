# Viral script guidelines (Prepare a video)

Read this before every script you check, improve or write (`/write-script`). These are rules of thumb that creators
who grow on TikTok, Reels, Shorts and YouTube use. They are not laws. The user's own results come first: their
ratings, how their videos turned out, and the analysed videos whose style they picked (all measured). Then come these
rules. `tools\script.py check` measures the rules that can be counted. You judge the rest.

## 1. What "viral" means for a script
Platforms show a video to more people when the people who already saw it **stay** and **act**. A script can control
three things:
- **The hook rate**: people still there after 3 s. That is the first line, the first picture and the first text on screen.
- **Retention**: they watch to the end. Every line has to make them want the next one, and nothing is filler.
- **Actions**: shares, saves, comments, follows. The video has to be worth sending to someone, and it ends with one
  clear ask.
A script that is merely correct (true, complete, polite) loses to one that is gripping. Cut anything that does not
earn its second.

## 2. Before writing: one video = one idea
- **One idea, one viewer, one promise.** First write the takeaway in one sentence: "after this video you can ___"
  or "you'll never ___ again". If it takes two sentences, it is two videos.
- **Who it is for.** Name the viewer ("freelance editors who…", "si estás empezando en…"). A script for everyone
  hooks no one.
- **Why you (the angle).** The user's own story, result, mistake, number or opinion. That is what makes it theirs, and
  it is usually where the best hook is. Ask for it if it is missing. Never invent it.
- **True to the payoff.** The hook promises only what the video delivers. A clickbait hook that the video doesn't pay
  off loses retention and trust.

## 3. Structures (pick one for the topic and the length)
| structure | how it goes | good for |
|---|---|---|
| **HEIT** (the lab's talking structure) | Hook → Explain (what / why) → Illustrate (an example, a story, a demo) → Teach (the takeaway you can use) | explainers, talking heads |
| **Problem → Agitate → Solve** | the pain, why it gets worse, the fix | advice, products, "stop doing X" |
| **List / steps** | "3 things…", each its own mini-hook, the best one last (an open loop: "the 3rd is the one nobody does") | tips, tutorials |
| **Story** | setup → conflict (**but**) → turning point (**so / therefore**) → result → lesson | vlogs, personal, brand |
| **Result first** | the after, then the before, then how | transformations, tutorials, demos |
| **Myth → truth** | the belief, why it is wrong, what is true, proof | contrarian takes, expert content |
| **Long form** (YouTube) | hook (≤ 30 s) + promise + why trust you → chapters, each with its own mini-hook → payoff → CTA → end screen | 5-20 min videos |

Story rule: link beats with **but** and **therefore**, never "and then". Each beat should cause or upset the next one.

A short form's clock (≈ 2.5 spoken words a second):
| part | short (≤ 60 s) | what it does |
|---|---|---|
| hook | 0-3 s | stops the scroll: what they hear + read + see |
| promise / context | 3-8 s | why stay: what they get by the end (open the loop) |
| body | 8 s → end-5 s | the points, each with a turn or a new picture |
| payoff | last 5-8 s | the loop closed: the promise kept |
| call to action | last 2-4 s | one ask with a reason |

## 4. The hook (the first 3 s ≈ 7-9 spoken words)
- **Lead with the most interesting sentence.** Never a greeting ("hey guys", "hola a todos"), your name, "in this
  video I'm going to", or context first. Start mid-action.
- **Open a gap.** A question they need answered, a result they want explained, a claim they want to check.
- **Specific beats vague.** "I lost 40,000 followers in a week" beats "I made a big mistake".
- **Three layers, one message.** The words you **say** + a **text on screen** (≤ 6 words, it adds to the spoken
  line instead of repeating it) + a **picture** that moves in the first frame (you mid-gesture, the result, a prop,
  a fast push-in). Write all three.
- **Patterns** (`prompts.HOOK_PATTERNS`). Name the one you use:
  - *question*: "Why do your videos die at 200 views?" / "¿Por qué tus vídeos se quedan en 200 visitas?"
  - *bold claim*: "This one setting doubled my watch time." / "Este ajuste me duplicó el tiempo de visualización."
  - *number*: "3 edits every viral video has." / "3 cortes que tiene todo vídeo viral."
  - *story*: "Last year I quit my job with €600 in the bank." / "El año pasado dejé mi trabajo con 600 € en la cuenta."
  - *contrarian*: "Stop posting every day." / "Deja de publicar todos los días."
  - *demo*: "Watch this clip go from boring to cinematic." / "Mira cómo este plano pasa de aburrido a cinematográfico."
  - *curiosity gap*: "Nobody tells you this about the algorithm." / "Nadie te cuenta esto del algoritmo."
  - *call-out*: "If you film on your phone, you need this." / "Si grabas con el móvil, necesitas esto."
- **Write 3 hooks in different patterns** for every script and pick one. The user chooses in the end. Later their
  ratings show which pattern works for them.

## 5. Holding attention (the body)
- **Something new every few seconds**: every 5-8 s in a short, every 30-60 s in long form. That means a turn ("but",
  "here's the thing", "pero", "el problema es"), a question, a number, the next step, or a new picture. The check
  measures the longest stretch with none of these.
- **Open loops**, closed later: "I'll show you the third one at the end", and then do show it.
- **Short spoken sentences** with one idea each, about 8-15 words. Write for the ear: contractions, present tense,
  "you". Read it aloud. If you run out of breath, split the sentence.
- **Talk to the viewer**: "you" more than "I", even in a story. Turn "I learned X" into "here's what X does for you".
- **Concrete**: numbers, names, places, prices, time frames, one real example. Aim for one specific per ≈ 30 s.
- **No filler**: basically, literally, actually, "so yeah", o sea, en plan, básicamente, la verdad es que. No
  apologies, no "I'm not an expert but". Don't repeat the hook.
- **Show, don't only say.** Pair lines with what is on screen, written as notes in square brackets: `[TEXT: …]`,
  `[B-ROLL: …]`, `[ZOOM]`, `[SFX: …]`, `[CUT]`. The check counts them, and the edit (`/recreate-video`) uses them as
  its plan: punch-ins on the key words, B-roll on the examples, captions on the hook.

## 6. Payoff, call to action, ending
- **Pay off the promise in full.** The last part delivers exactly what the hook promised.
- **One call to action**, specific, with a reason, in the last 2-4 s: "comment CUTS and I'll send you the presets",
  "follow for part 2", "save this for your next edit", "comenta GUÍA y te la mando". In long form one soft ask can
  also go after the first payoff. Three asks get none done. An ask before the value costs viewers.
- **End strong.** Finish on the payoff or the ask. Never on "that's it", "bye", "espero que os haya gustado" or "y ya
  está". On shorts, a last line that flows back into the first one gets rewatches.

## 7. Length and pace
About 150 spoken words a minute (2.5 a second). Fast talking-head creators reach 170-190. The check uses the rate
MEASURED on the analysed videos the user picked (style.py's words/min), and that number wins over this table.
| length | ≈ words | platform |
|---|---|---|
| 15 s | 35-45 | TikTok, Reels, Shorts |
| 30 s | 70-85 | " |
| 45 s | 105-125 | " |
| 60 s | 140-165 | " (Shorts up to 3 min) |
| 90 s | 210-240 | TikTok, Reels |
| 8-12 min | 1,200-1,800 | YouTube |
Shorter is easier to watch to the end: say it in fewer words before you add more. Vertical shorts get burnt-in
captions (a few words at a time) and text on the first frame. On YouTube the title + thumbnail are the hook's first
line, so the spoken hook confirms them in the first 5-10 s.

## 8. Your stars: viral potential of the TEXT (0-5)
- **5**: a hook in ≤ 3 s with a named pattern and a gap; one idea and one viewer; something new on time (no flat
  stretch); the payoff keeps the promise; one specific CTA; every line earns the next; the notes for what is on screen
  are there.
- **4**: solid, with one real weakness (a soft hook, one flat stretch, a vague CTA).
- **3**: a good idea with a slow start or a flat middle, or two ideas fighting.
- **2**: no hook (greeting or context first), several ideas, no payoff.
- **1**: an essay or a blog post, not a script for speaking.
- **0**: it can't work as a video (no idea, or a promise it can't keep).
Stars are your reading of the text, not a view count. The user's rating of the filmed video (Good / OK / Bad) always
outranks them.

## 9. How a script you write looks
```
HOOK (0-3 s)  · pattern: contrarian
[TEXT: Stop cutting on the beat] [VISUAL: you mid-cut, timeline behind]
Stop cutting on every beat.

PROMISE (3-6 s)
Here's what doubled my views in 30 days.

POINT 1 (6-14 s)
[B-ROLL: waveform, the breath marked]
First: cut on the breath, not the beat. ...

PAYOFF (…)  ·  CTA (last 3 s)
Comment CUTS and I'll send you my 12 presets.
```
- Part headings in English capitals with estimated seconds. The check skips them, so put them on their own line.
- Spoken lines are in the user's language, the way they talk. Keep their expressions and slang when you improve
  their script.
- Notes for the camera or the edit go in `[BRACKETS]` with an English tag (TEXT, VISUAL, B-ROLL, ZOOM, SFX, CUT).
- Facts the user must confirm (their numbers, their story) are marked `[check]`. Never invent a result, a statistic
  or a story for them.

## 10. Learning from the user's references
For a talking video the user analysed (Analyze, focus content), `transcript(<name>, 0, <3 s in frames>)` gives its
hook, and `style.py <names>` gives its words per minute and the words in its first 3 s. Copy its rhythm and
structure: hook length, how often it turns, where the CTA goes. Never copy its sentences. Name what you took from
which video, with frame + timecode when you cite a moment of it (e.g. `f45 (00:00:01:15)`).
