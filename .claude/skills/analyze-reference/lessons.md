# Lessons learned from user corrections

<!--
Rules are added here ONLY from the user's verdicts on reports (Correct / Partly / Wrong + notes).
Read this whole file before every analysis and apply every rule while classifying events.
Format for each rule:
  - [L###] (YYYY-MM-DD, from <video> <event id>[, category: <id>]) <concrete, checkable rule>
    Why: <what went wrong>   Config: <key changed, old -> new, or "none">
Categories (tools/motionlab/styles.py: music_video, ad, motion_graphics, documentary, vlog, tutorial, cooking,
podcast, gaming, sports, travel, fashion, comedy, trailer, edit, other). A rule applies to EVERY category unless it
says `category: <id>` (older rules: `style: <id>`); tag a rule only when it is specific to that kind of video (e.g. a
documentary's interview framing). Rules L001-L007 came from a music video but are general.
This file is SHARED and REVIEWED: new rules are first written to knowledge/local/lessons.md (ids local-N) on the PC
where the feedback was given, shared to knowledge/incoming/, then reviewed into here with the next L number
(docs/knowledge_sharing.md, skill section "Reviewing incoming lessons").
-->

- [L001] (2026-10-06, from NEMZZZ - 4AM E004 E011 E030 E033 E039) A bright flash frame is "white" only when the
  flashed area is flat (no texture) - and even then give its measured level, never "white" by default: 4AM's
  brightest flat frames are 85-89 % (light grey). If the flashed area keeps ANY texture or detail (blotches, edges,
  a soft gradient, parts of the next shot showing through) it is an over-exposed picture: write "over-exposed,
  light-grey picture (level N %)" and rebuild it with Gain / Lift / Offset on the clip itself (or a textured
  plate), never a white Solid Color. Sheets are too small to judge this: use the "flash look" line of the evidence
  (level + texture) or measure the area at full size.
  Why: five flashes were written as "white" / "flat white" with white-Solid rebuilds; measured, four kept texture
  (56-81 %, texture 4.6-23) and the flat ones were 87-88 % grey.   Config: none (flash look is now measured)
- [L002] (2026-10-06, from NEMZZZ - 4AM E005) Before deciding when a graphic or logo appears, check the frames before
  the detected start for any part of it peeking out from behind panels or layers that are still on screen: it
  starts on the first frame any part is visible, and the rebuild puts it on a track BELOW those panels.
  Why: the 'DON PROD' logo shows at f334 behind the city panel; the review said it appears at f336.   Config: none
- [L003] (2026-10-06, from NEMZZZ - 4AM E019-E027) Light flicker or fades inside one location where the light falls
  off unevenly (background and floor go dark before the subject, a hotspot, a light direction) while the subject
  keeps moving smoothly with no ghosting are a practical light during the shoot (flashlight, lamp): origin camera.
  Pixel-identical dark frames do not prove an edit (cameras and encoders hold black). The edit part is only the
  cuts hidden in the dark frames (pose jumps); the rebuild says "shoot it with a flashlight", with a Resolve
  approximation (Gain keys from the measured luma curve + a soft circular window as the hotspot) as plan B.
  Why: the run was reviewed as dissolves between takes and a dark plate (origin unclear).   Config: none
- [L004] (2026-10-06, from NEMZZZ - 4AM E044) When a panel or element comes up on the same frame as a light event
  (firework burst, flash, lightning), measure its brightness frame by frame: if it rises with the light and dims
  with it, describe it as lit by that light, not as a pop-in, and key its Gain / opacity to the light's curve.
  Why: the hooded-man panel was "popping in" at f3077; it comes up with each firework burst (f3077, f3138) and
  dims with the light.   Config: none
- [L005] (2026-10-06, from NEMZZZ - 4AM E052) Tiles of a mosaic / grid of shots: check whether they move (compare
  frames a few apart after compensating the zoom) before calling them stills; in 4AM they are short video clips
  that keep playing, and the rebuild must use clips, not frames.
  Why: the review (and the test_4am rebuild) used still photos.   Config: none
- [L006] (2026-10-06, from NEMZZZ - 4AM, user: "difficult to tell when you missed an effect") Check every entry of
  "Possible misses" in review_todo.md (frames before / at / after; `tools/sheet.py <name> <a> <b>` for context) and
  write a verdict for each into review.json `"_near_misses": {"<frame>": "EFFECT ... / not an effect: ..."}` - the
  report shows it so the user does not have to re-check. Graphics popping into an existing layout (a clock, a logo, a
  new panel) can stay below every threshold.
  Why: the '3:59' clock popping in at f270 (00:00:10:20) was never an event; the new list found it (with two
  non-effects: a chain swinging out of its panel at f1844 and f1901).   Config: new section near_miss (z_min 5.0,
  max_items 12, spacing_frames 12, pad_frames 3)
- [L007] (2026-10-06, from NEMZZZ - 4AM E007/E008, found while checking the library macros against the real
  frames) Before calling thin lines or light spots on a near-black frame a graphic (light streaks, flares),
  look at the next shot: if the same shapes sit at the same positions there, they are that shot's practical
  lights coming up first (a dissolve or the start of a fade-in), not an overlay. Measure at full size.
  Why: E007's 'light streaks f358-361' are the hall's vertical light (x 358 px, the same in f361-409) and its
  ceiling lamp; test_4am drew random streak graphics there.   Config: none
