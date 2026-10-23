# /generate-video - a video for AI video tools (the plan + every prompt)

Read after SKILL.md (the hard rules, the brief). Text only: never call a video model, an API or a website, never ask
for a key (paid generation through the API is planned for 0.7). The user generates on the tool's own site with their
plan / credits.
1. **The tool decides the shape**: shot-based models (Higgsfield, Seedance, Kling, Runway, Veo, Sora, Pika, Luma,
   Hailuo) make 4-15 s clips (check the tool's current lengths; ask if unsure) -> a **shot list**: one prompt per
   shot, plus an image prompt for the first frame when the look must stay the same (Nano Banana / GPT Image ->
   image-to-video). Whole-video tools (InVideo AI, Pictory, Synthesia / HeyGen avatars) -> **one prompt for the whole
   video** (script, scenes, voice, music, captions, style) in the tool's own words.
2. **The shot list**: from the style's rhythm (shot lengths, the hook, where the energy rises - the brief's *Style*)
   and the user's idea; one line per shot - length, what is seen, camera move, light / look, the transition into the
   next. Show it to the user as a table before writing the prompts.
3. **The prompts**: follow `/write-prompt` (read `.claude\skills\write-prompt\writing.md` = its sections 0, 3, 4): the
   structure of the user's best-rated prompts for that model (`prompts(kind="shot")`), locks first then the change,
   one camera move per shot, the same character / product / place words in every shot (continuity). Save them all
   in one file and import: `.venv\Scripts\python tools\prompts.py import <file>.json` - one record per prompt, kind
   `shot` / `image` (or `brief` for a whole-video tool), the same `workflow` name (the project) and `step` 1, 2, ...,
   `model` = the tool, `tags` = what it is for, `style_refs` = the `like` videos, a `review` with your stars.
4. **The hand-off** in `projects\<project>\build\ai_plan.md`: the shot table (step, length, prompt id), what to
   generate where, how to name the downloads (`01_<shot>.mp4`, ...) and to put them into `projects\<project>\` -
   then *Editor > New edit* (or `/recreate-video request <project>`) cuts them; the song, captions and graphics are
   added there.
5. Tell the user the prompt ids (they are in the app's prompt library, *Copy Prompt* on each) and the order.
