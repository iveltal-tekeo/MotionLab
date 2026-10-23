# /write-title - the final package

Read after SKILL.md (sections 0, 1 and 5).

## 3. The final package (`package <project>`)
1. **The title.** From the video's title record - a record with `"project": "<project>"` first: the user linked it
   with *Use this title*, and its `chosen` is their pick - else the best one for the video as it was made (what the
   edit really delivers), or new ones when there is none (`first.md`, steps 2-3). Save the final choice on the record:
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
   (SKILL.md section 5) so the next package repeats what won.
