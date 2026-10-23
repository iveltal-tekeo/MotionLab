# /analyze-reference - a set of thumbnails

Read after SKILL.md (hard rules); section 0's lessons are about video effects and do not apply here.

## Thumbnail sets (`/analyze-reference thumbs <set>`, 0.4.5 - Analyser > Add thumbnails)
A set = `analysis\thumbs\<set>\`: `set.json` (every picture: title, views, the lab's measures - colours, brightness,
faces, where the text sits) and `sheet_N.png` (15 numbered pictures per sheet). Steps:
0. **The user's verdicts first** (2026-10-18: the set's page *Send it to Claude* after reviewing the patterns):
   `analysis\thumbs\<set>\verdicts.json` `{"patterns": {"P1": {"v": "correct|partly|wrong", "note"}}}` - keep the
   Correct patterns (their words and examples), fix the Partly ones the way the note says, redo or drop the Wrong ones
   (the note says why), and say in step 5 what changed. No file = the first look at the set.
1. `.venv\Scripts\python tools\thumbsets.py show <set>` (the measured summary), then look at EVERY sheet.
2. Name what repeats, with how many of the set and their numbers: the text (words per picture, capitals, outline /
   box / shadow, size, where), the font's STYLE in words ("heavy condensed sans, white, thick black outline") with the
   closest library fonts (`.venv\Scripts\python tools\fonts.py list`; an exact font name from a picture is a guess -
   write `"sure": false`), the colours (hex), the structure (face + big text, before / after split, an object and an
   arrow, a big number, a person reacting), faces (expression, looking at the camera, size), the emotion, what the
   title adds to the picture. Outperformers
   (views ÷ followers in set.json) count more - say which patterns they share.
3. Write `analysis\thumbs\<set>\style.json` in the shape `tools\motionlab\thumbsets.py`'s docstring gives (summary,
   patterns P1..Pn with `how_many` and `examples`, font, colours, words, structures, `for_make` = what
   `thumbnail.py make` should use: template outline / block / split, text and outline colours, font, words) AND
   `"texts"`: every piece of text the editor ADDED, `{"n": <picture number>, "words": "<exactly as written, case
   kept>", "box": [x0, y0, x1, y1]}` with the box in % of the picture (approximate, but around these words only). One
   entry per line of one size and colour (`3:00` and a smaller `AM` = two entries; two lines = two entries). Leave out
   signs, logos, products and text that is part of the scene, and tilted, curved or 3D words (the measurement needs
   straight letters). Open a picture from `img\` when the sheet is too small to read the words or place the box.
4. Run `.venv\Scripts\python tools\thumbsets.py fontmatch <set>` (a few seconds): it measures which library font the
   listed words are written in -> `fontmatch.json`, and *In the style of <set>* uses that font instead of your guess.
   A text it could not measure says why (fix its box or drop it, run it again).
5. Tell the user the 3-5 strongest patterns in plain words (with picture numbers), the measured font with its score
   (e.g. "Inter 800, overlap 0.82 over 14 texts - your guess Montserrat 0.74"), what changed since their verdicts
   (step 0), and that the set's page in the Analyser lets them mark each pattern Correct / Partly / Wrong with a note
   and send it back to you; *Ready to post* can then make thumbnails "in the style of <set>". Copy a style, never a
   design, a logo or a face.
