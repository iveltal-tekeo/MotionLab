# /generate-video templates <pack> - rebuild captured clips as Motion Graphics templates (0.5.0)

Read after SKILL.md (the hard rules). The user's captured template clips (e.g. `refs\swishy\`) are measured with no
Claude: `tools\templates.py read <folder> --pack <pack>` -> `analysis\templates\<pack>\` (pack.json: every move with
frame + timecode, its ease, the holds; `<id>\sheet.png` per clip; `overview_N.png`, 8 clips a page) and Claude's
`cards.json` (what each clip is, use_for, tags, `rebuild` 1 / 2 / 3 - write a card for every clip without one, from
the overviews). The clips stay untouched (hard rule 1) and private; the repo gets only MotionLab's own templates.
Lessons for this work: `tools\knowledge.py lessons --kind templates` - apply every rule.
1. `templates.py todo <pack>` = the clips not rebuilt yet, priority 1 first. Take up to 8 per session; group clips that
   are one motion (two chat clips = one chat template). Skip `rebuild` 3 (a brand's logo, someone's character).
2. Per template: read the clip's sheet and `templates.py show <pack> <id>` (the moves' frames and eases), then write
   `tools\overlays\motion\<template>\`: `index.html` - copy the helper block of an existing template (FPS / FRAMES,
   W / H lines for `retime`, F / AT / K (frames designed at 30 fps), set / to / ft / enter); everything sized from
   `U = min(W, H) / 1080`; the settings declared on `<html>` (the words, colours, a `font` enum - `fonts.py sync` fills
   its list -, `background` + `bg`, `size`, position, `start`); never a brand's logo, name or someone's words copied
   from a clip - a template that shows logos loads `assets/logos/logos.js` in `<head>` and draws the library's
   (`motionlab\logos.py`: a logo setting `logo` / `*_logo` / `logos` -> `MLLogo.fill(box, V.logo, {dark, tint, mono})`,
   a text -> `MLLogo.text()` / `MLLogo.lead()` for `:youtube:`).
   `overlay.json` = frames / fps / size + sound `cues` (formulas of the settings; `sfx.py cues <folder>` must list them
   inside the frames; a list setting "a|b|c" counts with `parts(words)` - formulas have no `.split`). `template.json` =
   name, kind (text / numbers / charts / lists / ui / chat / social / music / logo / photos / places / background /
   transitions / lower_thirds / callouts / broadcast / promo), what, use_for, tags, `learned_from` [{pack, clip, what}]
   (a MotionLab original made for a common need, not from a clip: `[]` + `origin` = the need, in words), motion (in
   words + frames), scene / overlay, general (0-1: how often it fits), thumb_f, check_frames; `tracks` (each move:
   name, what, start_f, length_f, easing) when you know them, else the PC measures them; `min_frames` (a formula of
   the settings) + `min_why` when it cannot finish its move in fewer frames (shape-wipe, story-lines).
3. `templates.py check <template>` = a snapshot sheet at the check frames (no render, ~4 s) + its thumb.png + FIT lines
   (text off the frame, outside its box, overlapping); look, fix, again; then `--size 1920x1080@25` (another size and
   rate) and `--values '{...}'` for each look. The lessons list the bugs that look fine in code (font stacks in single
   quotes; no top-level `const top`).
4. What the PC measures once a template is done (no Claude): `templates.py tracks <id> --measure` (its moves from a
   plain render, when template.json has no `tracks` -> measured.json; FAST lines = moves over 60 px a frame that show
   copies with motion blur: smear() them in the template), `templates.py sizes <id>` (1080x1920 and 1080x1080: ok / NOT
   ok -> `library --brief`). A local template learned from the user's clips: `templates.py finish <id>` (render,
   motion match with its clip, preview, the FAST lines).
5. Tell the user what was added (the app's Motion Graphics page shows them with a live preview, the clip beside it).
