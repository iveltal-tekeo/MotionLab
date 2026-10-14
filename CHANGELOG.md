# Changelog

What changed in each version of MotionLab, newest first. When a new version is on GitHub, MotionLab shows an
**Update available** button in the sidebar; it opens the sections below that are newer than your copy.
Version numbers: a new `0.x.0` is a big step; `0.x.y` adds a smaller feature; a four-part `0.x.y.z` is a small step
between them (fixes, upkeep, polish).

## 0.4.1.1 - 2026-10-14 - Each section its own feel, Prepare, sound effects, check before you render

- **Each section has its own feel**: Analyze, Prepare, Edit, Generate and Claude's memory open with their title on
  a band in the section's colour - like the card you clicked on Home, with its big icon - over a faint pattern of
  its own (a measuring grid, ruled script lines, film-strip holes, sparkles, a constellation). The main buttons and
  the panels' edges take the section's colour too, and so does each section's row in the sidebar, so you always
  know where you are. Generate is fuchsia now. The sections lost their numbers: they are not steps you have to take
  in order.
- **Which Claude, how hard** - every button that opens Claude Code first shows a small dialog: the model (Opus, the
  one every plan includes and the default; Fable, the strongest, for checking, recreating or generating a video -
  the dialog says where it is stronger; or what you set in Claude Code) and the effort, pre-filled for the task.
  *Don't ask again* keeps your choice; Settings > Claude Code has the defaults and brings the dialog back.
- **Check before you render**: Claude can look at any moment of a motion graphic in seconds, without rendering it,
  and works in steps you approve - the plan, then pictures of every scene change, then the motion, and only then
  the final polish. New motion graphics start from a safer template: they look the same with motion blur, without
  it and in a quick preview - no more vanishing logos or moves that get stuck.
- **Claude remembers how you rated every video**: a part you rated bad (for example "no sound effects") becomes a
  rule for every video after it, and what you rated good is kept. Lessons on making videos are kept and shared with
  friends like the analysis lessons.
- **Sound effects, made by the lab**: whooshes, clicks, key taps, pops and hits are made by MotionLab itself (no
  samples, nothing to license), placed on the exact frames of a graphic or an edit, and each one set against the
  music under it - heard, without drowning the song (a sound in a short quiet gap is set against the gap, not the
  loud part after it). A graphic lists its sounds next to its settings, so changing
  the typed text moves the key taps with it; an edit's zooms, whips, flashes and speed-ups get their sounds the same
  way. You get the effects on their own (a track for DaVinci Resolve) and mixed with the song, never clipping.
- **Prepare a video - the script, before you film** (a new section between Analyze and Edit, also on Home):
  *Improve my script* - paste or attach the script you have; MotionLab checks it on the spot (the hook in the
  first 3 seconds, the length, dead stretches with nothing new, filler words, "you" vs "I", the call to
  action, the last line, what is on screen), then Claude marks every part as clear, vague or missing and rewrites
  it in your voice for more reach. *Write one from zero* - answer a few questions (what it is about, who it is
  for, what they get, your story, length, tone, the ask at the end, the style of talking videos you analysed);
  Claude writes three hooks and the whole script with what goes on screen. Scripts sit with your prompts:
  rate them, and *Record it* starts the edit.
- **Analyze and Edit**: their main buttons sit in the first row under the title (*Download from link* - before
  "Download only" - and *Add videos*; *New edit* and *Folder*).
- **Optional steps look optional**: in every dialog (Add videos, Prepare, New edit, Generate), on a video's step
  strip (*Teach Claude*) and in a prompt's steps, a step you can skip has a grey dashed number and an **OPTIONAL**
  tag; the steps you need keep their coloured number.
- **Motion graphics with real motion blur**: Claude can render a graphic with motion blur - five in-between
  moments blended into every frame, so fast moves smear like a camera's instead of jumping from frame to frame.
  Later renders of that graphic (Edit > the video > Graphics) keep it; they take about five times as long.
- **A new roadmap on Home**: it moves now - the line draws itself, each version pops in, a light runs along what
  has shipped to *you are here*. The big versions (0.4.0, 0.5.0...) are badges with an icon; the smaller ones hang
  below them. Click it to see it full size, and hover a version for its full name.
- *What's new* shows the plans in their new order: **0.5.0 is about videos made from zero** (Generate) - ready-made
  building blocks for motion graphics, sound effects, formats you can reuse, a preview before the long render, and
  clips made with AI video tools brought back in to be finished. Templates by feel moved to 0.6.5, macOS to 0.7.5
  and describe video to 0.8.0. Next come **check before you render** (0.4.2: stills of the key moments before the
  long render, your ratings remembered for every later video) and **downloads that keep working** (0.4.2.1, with a
  *Report a problem* button); title + thumbnail, the prompt generator, yapping mode and colour follow as 0.4.3-0.4.6.

## 0.4.1 - 2026-10-13 - Fixes after 0.4.0: quick drafts, waiting jobs, new videos never overwrite old ones

- **Quick draft of a talking video**: when a clip's sound starts a little before or after its picture (common on
  phones), the cuts used to move the wrong way and could clip the first or last word - they now land on the voice.
- **Quick draft with short clips** no longer stops with "no clip is long enough for a shot": a shot longer than
  every clip uses the longest one and holds its last frame (the draft's notes say so), speed ramps go only where
  the clip has the frames they need, and B-roll cutaways are never longer than the clip (none at all from clips
  under a second, rather than a flicker).
- **A quick draft started while the lab is busy (an analysis, a render, another draft) now waits its turn**
  instead of being refused with "... is still running" - and so does *Measure the colour*. The Jobs page shows a
  waiting job as *waiting its turn* with **Remove from the queue**, and no running time for it in the list.
- Jobs waiting in line: one that cannot start no longer leaves the ones behind it stuck, and a job removed just
  as its turn comes no longer runs anyway.
- The *Working on* panels (Analyze, a video's page in Edit) refresh when any job ends - a download that started
  its analysis, or a draft followed by the next one, used to leave the page out of date until you reloaded it.
- **Generate never overwrites a video**: the name it suggests is always a free one (after a deleted video it could
  suggest the name of one that exists), and a name that is already a video is refused with "give this one another
  name".
- **Claude's memory** shows a friend's new lesson and an analysis you added or deleted at once (it needed the app
  to restart), and Claude reading it through MotionLab's MCP server no longer rewrites `memory.md`.
- *What's new* lists the planned versions with their new numbers: 0.4.2 describe video, 0.4.3 colour (your own
  clips, grades in Resolve), 0.4.4 yapping mode, 0.4.5 prompt generator - each says what 0.4.0 already shipped.

## 0.4.0 - 2026-10-13 - Analyze, Edit, Generate: three ways in, Claude's memory, quick drafts, colour

- **Three ways in**: the sidebar is now Home, **1 Analyze**, **2 Edit**, **3 Generate** and **Claude's memory**,
  with Jobs and Settings at the bottom (Claude skills is a Settings tab). Home asks *What do you want to do?* with
  one card per way, its buttons and counts. Old links keep working.
- **Analyze several videos at once, the way you want**: *Add videos* takes up to 10 links (one per line) and files;
  pick what to look at - **Content creation** (what is said, the hook, captions, text on screen), **Cinematic**
  (effects, transitions, camera, colour) or **both** - and whether Claude checks each one. They queue up and run one
  after another (links download first); a panel shows what runs and what waits. Each analysed video opens on an
  **Overview** for its mode: the rhythm, the content or cinematic numbers, Claude's breakdown of what makes it work
  and *Use it*: edit my clips like this, prompts for AI tools like this. Talking videos without subtitles get their
  words by speech to text when it is installed.
- **Claude's memory** (sidebar): everything Claude learned in one place with one search - every video you and your
  friends analysed with its style (rhythm, hook, talking, captions, signature effects, Claude's breakdown), every
  effect seen with how often, your verdicts and how each was made (the ones you confirmed first), the lessons, your
  saved graphics and effects, and sharing with friends. Claude reads the same before an edit or a prompt, so a
  video you liked shapes what it makes for you.
- **New edit - your clips, cut the way you want**: *Edit > New edit* asks four things: your clips; how - **like
  videos you analysed** (up to three: their rhythm, hook, effects and captions mixed, with your music and length -
  or an exact copy of one, frame by frame), **with your words** (ready-made styles: fast & hooky, 3-second cuts,
  talking + captions, slow & cinematic, transition-driven, music montage - and / or what you want, e.g. "a hook in
  the first second, 2 s cuts, captions word by word") or **from a saved prompt**; length, format and sound; then
  **Quick draft now** or **Make it with Claude**. The quick draft is made by rules in a few minutes, no Claude:
  cuts on the beat of your song with the style's shot lengths, the best moments of your clips (sharp, well exposed,
  each used once), the style's effects (crossfades, dips, flashes on the drops, zoom-throughs, pushes, whips,
  push-ins, shakes, freezes, stutters, speed ramps, RGB splits, light leaks); a talking video keeps what is said
  and cuts the pauses, with a punch-in every other cut and B-roll over the talking. Its notes list every shot with
  frame and timecode. Claude then makes it great - a story, captions, graphics - and, if you want, a DaVinci
  Resolve project.
- **Generate - a video from zero**: **A motion-graphics video** - say what it is about (and, if you like, the words
  on screen, a song, your colours, up to three analysed videos whose style to follow); Claude shows you the scenes,
  writes the video as HTML (HyperFrames), times it to the song's beats and renders it - every text, colour and
  timing stays editable in the video's Graphics tab. **With AI video tools** - your idea, the tool (Higgsfield,
  Seedance, Kling, Runway, Veo, Sora, InVideo AI…) and a style: Claude plans the shots and writes every prompt into
  your prompt library, in order, ready to copy into the tool's site; the clips you make come back to Edit. Nothing
  is paid in MotionLab. A new Claude Code command does both: `/generate-video`.
- **Colour & look** (the cinematic focus): every analysed video now says what its colour grade is - per shot and for
  the whole video: warm or cool, teal & orange, contrast, lifted or crushed blacks, saturation, vignette, letterbox,
  its main colours - shown on the video's Overview as words, a palette and a strip of every shot's colour (with
  frame and timecode). An edit **in its style** matches your footage to that look automatically: a match LUT (.cube)
  that also works on DaVinci Resolve's Color page, with how close your clips get (0-100). Videos analysed before:
  *Measure the colour* on their Overview (a few seconds).
- A render whose song is a WAV or FLAC file now gets AAC sound (it used to fail: an MP4 cannot hold WAV sound).
- Frame caches are never bigger than the clip itself: a horizontal clip in a vertical edit used to be cached at
  1.8x its size (about 3x the disk) for no extra detail.
- **Fixed: the analysis stopped at the audio step on PCs without the Microsoft Visual C++ Redistributable**
  ("DLL load failed while importing _typeconv"): the audio analysis needs it and some Windows PCs do not have
  it. The job now ends with one plain line saying what to install
  (`winget install --id Microsoft.VCRedist.2015+.x64 -e`, or https://aka.ms/vs/17/release/vc_redist.x64.exe),
  and `setup.bat` checks for it and offers to install it.
- **GitHub's tests run less often**: the 15-minute test run no longer starts on every push - only for a new
  `x.y.0` version (until it passes), when started by hand (Actions > tests > Run workflow) or with `[tests]` in a
  commit message. Updates still come only from tested pushes; friends' shared cards and lessons are released
  within a minute as before. *Settings > Sharing & updates* now says "not released yet" for newer, untested
  changes on GitHub.
- **Prompts, clearer buttons**: a prompt Claude has not looked at yet shows **Optimize with Claude** - Claude
  reviews each part and writes an improved version in one go (yours stays). A hook's run button says *Use current
  version in a video*, *Copy text* is now **Copy Prompt** with a clipboard icon, and *What it makes* explains its
  *+ Add picture / clip* button: pictures or clips of what the prompt made, kept on your PC, the first one on the card.
- **Claude Code on the web**: a cloud session sets itself up for MotionLab (Python packages, ffmpeg 9) so Claude
  can run the self-test and the app's checks there - see `docs/cloud.md`.
- **Home moves**: a small, slow animation at the top shows how MotionLab is used - *Like a video? / Use it as a
  reference. / Claude names each one. / Make yours.* - with a timeline whose cuts light up, effect tags that pop in
  and your clips that slide in. It is drawn by the graphics card (no video, no script running), stops while the
  window is hidden and stays still if Windows animations are off. *Paste a link* starts right there.
- **A prompt, opened, is easier to read and to act on**: a header in the kind's colour with the title, what it
  needs and **Run it**; five steps (Claude checks it, you say what you want, Claude improves it, run it, rate the
  result) with the one to do now lit and a **Next** box holding its button; then two columns - the prompt in
  readable text and Claude's check as a coloured card per part (✓ clear green, ~ vague amber, ✗ missing red, a tip,
  and a box for what you want; *Needs work* shows only what needs it) | big Good / OK / Bad buttons, what it makes,
  Style like and the details. **Claude skills** is the new name of the Skills page.
- **Claude skills** (Settings > Claude skills): the commands you can type in Claude Code for MotionLab -
  `/analyze-reference`, `/recreate-video`, `/generate-video`, `/write-prompt`, `/whats-next` - each with what it
  does in a line, how to type it (Copy), where the app runs it for you, and *Open in Claude Code*. The roadmap's
  *What next? Ask Claude* (a developer's command) is there too.
- **Plainer**: an empty page shows what goes there and one button in the middle instead of a "No ... yet" line.
  Plainer words everywhere: no file paths, version numbers, checksums or effort levels where you work; "lab pass"
  is now *Measure*.
- **Prompt filters**: *Needs another tool* (a prompt that runs on Higgsfield, Kling, InVideo... - an account,
  credits or a setup; the card shows the tool in amber), *No other tool*, and *Not checked yet* - which replaces
  the "not checked by Claude" alert and has the *Check with Claude* button next to it.
- **Home, calmer**: no "Next steps" list and no "Updated to ..." box any more (the What's new window still opens
  once after an update); Status sits below the roadmap. Missing programs still show, only when something is missing.
- **Prompts page, calmer**: no filter rows any more - cards, 3 per row, newest first, each with only its title, the
  rating (yours, else Claude's ★), what it needs (Claude + Resolve, Seedance on Higgsfield...; your clips, your
  photo, you on camera, or text only) and one category - plus a search box. Prompts nobody titled yet get a readable
  title (a brief: its footage folder, format and style, e.g. "Londres Día 1 · vlog · estilo Clavero"). **Click a
  prompt** and it opens in a pop-up with everything about it: the whole text, *What it makes* (add a picture or
  clip of the result - it becomes the card's picture), Style like, Claude's check with *what you want* per part,
  Optimize, Run it, your rating. Dialogs opened from there (For, kind, Delete, Run it...) have **← Back** - so do
  Esc and the ✕.
- **Add prompts in steps**: choose *1. I have a prompt* or *2. Generate a new prompt from zero* and the next screen
  shows only that, with **← Back** to change your mind.
- **A brief's check covers more of the video**, grouped in the order a video is made - the plan (format, story &
  hook, feel, footage & b-roll, order), the edit (pacing, transitions, and now **effects**: zooms, speed ramps,
  shake), sound (now **voice & audio clean-up**: silences, noise, levels; music, SFX), look & text (colour, motion
  graphics, captions) and finish (now **ending & call to action**; where it ends up, questions first).
- **Style like - a video you analysed** (Prompts): a brief that says "in the style of Clavero's vlogs" now finds
  the Clavero video you analysed in References (by who made it or its title) and offers *Use its style*; or pick
  any analysed video with *+ pick from your references*, also in *Generate a new prompt from zero*. Claude then
  writes what the lab measured in it - cuts per minute, shot lengths, the first 3 seconds, its effects, the beat,
  and its look from its frames - into the prompt when it checks or optimizes it, and follows it when the prompt
  makes a video. No more "send a link to measure the style" when you already analysed one.
- Claude's check and what you wrote per part now reach Claude in one read when it optimizes a prompt.

## 0.3.4 - 2026-10-12 - Prompts you can check, improve and run

- **A new kind: Brief for Claude** - a prompt that tells Claude how to make or edit a whole video (length, feel,
  footage, colour, pacing, SFX, graphics...). Until now such a prompt landed under "Talking script", which is
  something else: the words you say on camera. MotionLab recognises briefs (in Spanish too), and you can change any
  prompt's kind by clicking its badge.
- **Claude's check, in plain words**: on every prompt, *Claude's check* lists each part - for a brief: long or short
  and how long, story & hook, feel, footage, order, pacing & cuts, colour grading, music, SFX, motion graphics,
  transitions, captions, where it ends up, what to ask you first - marked ✓ clear, ~ vague or ✗ missing, with a tip.
  Write what you want next to any part and click **Optimize with Claude**: it writes a better version (the original
  stays) - then **Run it** (a brief makes the video through *Create video*; a shot or image prompt is copied for the
  site) and rate what it made.
- **Tidier cards**: the kind as a coloured badge, a title, the prompt folded to a few lines (*Show all*), the check
  folded into one line until you open it.
- **Add prompts** asks first: *1. I have a prompt* (paste it or attach a file; Claude checks it) or *2. Generate a
  new prompt from zero* (say what you want to make; Claude writes it from the best examples in your library).

## 0.3.3 - 2026-10-12 - Fixes, Create video, captions from your own words, a livelier app

- **Captions from your own recordings** (*Videos > your video > Graphics > Captions...*): pick a video and MotionLab
  writes down what is said - on your PC, nothing uploaded - and makes the captions from it, timed to the words.
  Install it once in *Settings > Programs > Speech to text* (about 460 MB; *base* is a lighter choice for slow
  laptops). Give it the names in your video (your channel, songs, products) and it spells them right. Phone videos
  filmed upright come out upright.
- **A talking-head graphics pack** (*Library > Graphics*): a progress bar, a hook title, numbers that pop up (and
  count up) the moment you say them, a list that builds point by point, and an end card - all in a band clear of
  your face. Colour, font, size, height and opacity are settings; it fits any video size.
- **Fixed: videos with odd titles** (reported by a friend): a video whose title was cut short with "..." (TikTok
  hashtags) was analysed, but its page never opened ("bad name"). Such analyses are renamed when MotionLab starts,
  and new ones never get "..". *Download from a link* also said "download failed" for a title with an emoji (🎬),
  though the video had downloaded. Now it is found and listed.
- **Vertical videos download in full size**: "best up to 1080p" counts the short side now, so TikToks, Reels and
  Shorts come at their real size (a TikTok came at 576x1024 although 720x1280 was there). A link with no video (a
  SoundCloud track) now says to pick *MP3 audio only*, and a failed download says why in words (the site blocks
  this PC for a while, wants a login, does not know the link, or yt-dlp is out of date).
- **Add prompts without a format**: paste a prompt as it is, or attach a .txt, .md, .docx or PDF. MotionLab guesses
  its kind (you can change it), *Let Claude sort it* reads a whole guide and saves every prompt in it, and Claude
  reviews and splits the new prompts by itself.
- **Prompts on one page**: video shots, images, hooks and scripts in one list, each with a coloured badge; filter by
  kind and by what a prompt is for - mark it for vlog, talking head, SFX, transitions, colour... (or your own
  words) - and search. *Use it, change…* asks Claude for a new prompt that
  keeps what worked and changes what you say. *Delete* moves a prompt to the Recycle Bin.
- **Create video** (*Videos*): start a video from a reference (its edit with your clips) or from a prompt in your
  library, with your clips or a new folder for them; Claude Code does the work.
- **How did it turn out?** (a video's *Overview*): Good / OK / Bad and a note for the sound, SFX, colour, captions,
  motion graphics, effects, pacing and overall. Claude reads it next time (*Improve it with Claude* fixes the parts
  you marked), and the prompt the video came from shows it as "Used in".
- **A tidier, livelier app**: the sidebar is grouped (Home, Videos · Media · Additional · Tools), Storage moved into
  Settings, and every section has its own colour, softer cards and dialogs that pop in. It stays as light as before.

## 0.3.2 - 2026-10-12 - Graphics you can edit, captions, and graphics in DaVinci Resolve

- **Graphics with settings** (*Videos > your video > Graphics*): every HTML graphic of a video - titles, clocks,
  lower thirds - shows a picture of itself and a form with what you can change: text, colours, size, position and
  timing in frames. *Save*, then *Render*, and the next render of your edit uses it; the card says when a graphic
  needs rendering again. 4AM's pixel title and seven-segment clock are now editable too (any text, any colour),
  and at their old settings they come out pixel for pixel as before.
- **A graphics library** (*Library > Graphics*, at the top): the graphics you saved from a video (*Save to
  library*) and the examples that come with MotionLab. *Use in a video* copies one into a video and renders it.
- **Captions** (*Graphics > Captions from a subtitle file*): give it an .srt or .vtt of your video's words (from
  YouTube, CapCut, or DaVinci Resolve's *Create Subtitles from Audio*) and MotionLab makes styled captions timed to
  the words - the spoken word highlighted, words popping in, or a plain line; font, size, colours, outline, a box
  and the height on screen are settings - plus the same captions as an .srt for Resolve's subtitle track
  (*Subtitles for Resolve*). The word highlight changes on exactly the right frame. Captions straight from your own
  recordings (speech to text) come with 0.3.5.
- **Graphics in DaVinci Resolve - tested inside Resolve**: the graphics look the same in Resolve as in the lab's
  renders (within 2/255, frame-exact, normal / screen / add blending). Resolve keeps the files it uses open, so
  *Clip for Resolve* gives it a numbered copy to drag into your project, and after you change and render a graphic,
  *Swap in DaVinci Resolve* replaces it in the open project - its place, length, size, opacity and blend mode on
  your timeline stay. (A project with Resolve's Color Management on shows every Rec.709 clip a little darker, the
  graphics as much as your footage.)
- **Content tab** on every analysed video (a first part of 0.3.5): how it performs - views, likes, comments, the
  channel's followers and *views ÷ followers* (above 1 = it reached past the channel) - and what it says: the
  transcript with frame + timecode, a click moves the player, the line being said is marked, and a search.
- **Check for updates**, bottom left, always there: asks GitHub now and offers the update, or says you are up to
  date (and when it last checked).
- **What next?** (*Home > Roadmap*): Claude reviews what changed, where every planned version stands and what waits
  on you, and suggests what to do next (`/whats-next`).
- For developers: `tools\motionlab\overlay_settings.py` (settings = HyperFrames' `data-composition-variables`),
  `tools\motionlab\captions.py`, `overlay.py new --from | settings | set | save | graphics | captions | refresh |
  resolve-clip`, `content.py stats`, `tools\whatsnext.py`; the page needs `API_LEVEL` 7. Resolve test:
  `tools\dev\resolve_overlay_test.py` (scratch project; results in `docs\resolve_notes.md`), examples:
  `tools\dev\examples_compare.py`. Scripts never save Resolve's unsaved "Untitled Project" (its name dialog blocks
  scripting). GitHub's "mark as tested" step retries its push and writes its errors into the public notes.

## 0.3.1 - 2026-10-12 - Tested on GitHub first, and a prompt library

- **Every change is tested first**: each change pushed to GitHub is now tested automatically on a clean Windows
  machine - the self-tests (synthetic videos with known effects, made there) and a check that the app starts, every
  page opens and Claude's MCP connection works. The *Update available* button only offers what passed; a change
  still being tested shows as "waiting for GitHub's tests" in *Settings > Sharing & updates*. Friends' shared cards
  and lessons take a quick check and arrive within minutes.
- **ffmpeg 9.0.2**: `setup.bat` installs the newest ffmpeg through winget, which is 9.0.2 now - the self-tests pass
  with it (21 of 21 effects, every cut exact, no false alarms), and GitHub's tests use the same version.
- Each version gets a tag on GitHub (`v0.3.1`, ...), so any earlier version can be fetched again.
- **Prompts** (new page in the sidebar, the first part of 0.4): keep the prompts that worked for you - for video
  models like Seedance / Higgsfield / Kling, hooks (the first 3 seconds) and talking scripts - or a creator's public
  prompt with its link. Claude splits each one into its structure (subject, camera, light, look... or hook > points >
  call to action); *Write one like this* opens Claude Code, which writes three new prompts for your need in a
  structure that already worked. Text only - you paste the prompt into the site, nothing is paid or sent - then rate
  what it made (Good / OK / Bad + a note), and the best-rated ones become the first examples next time. A shot
  prompt can also be filled from a reference's frames (its measured camera move and look). Image prompts (Nano
  Banana, GPT Image, Kling Image) have their own tab; prompts collected from creators get Claude's review - 0 to 5
  stars, why, and what to fix - next to your own rating of what a model really made, and recipes in several steps
  (an image prompt, then a video prompt) show their steps. Your prompts stay on your PC for now.
- **HyperFrames kept current, safely**: HyperFrames (the HTML graphics) now uses 0.8.149 and GSAP 3.15.0 - tested
  first: the 4AM title and clock come out identical, the 10-second What's new clip within 2/255. HyperFrames releases
  several times a day, so MotionLab never upgrades by itself: *Settings > Programs* shows the version in use and the
  newest one (asked once a day, nothing about you is sent), and *Test it* renders the examples with the newer version
  and compares every frame. A version that passes reaches you with a MotionLab update, which installs it by itself
  (where HyperFrames is installed).
- **Transcripts**: `tools\content.py transcript <reference>` fetches the video's own subtitles (or YouTube's
  automatic captions) and writes what is said, every line and word with frame + timecode, into the reference's
  analysis folder. Claude reads it through MotionLab's MCP server (hooks and scripts of talking videos build on it
  next). Nothing is shared: transcripts are other people's words and stay on your PC.
- For developers: `.github\workflows\tests.yml`, `tools\dev\smoke.py` (the app smoke test - also worth running
  after any change to the app); how the `tested` branch works: `docs\organization.md`, "Tests on GitHub". The prompt
  library: `tools\prompts.py`, `tools\motionlab\prompts.py`, MCP `prompts`, the `/write-prompt` skill; the page needs
  `API_LEVEL` 5. Overlay packages: `tools\motionlab\upstream.py`, `overlay.py versions | upgrade-test | pin`.
  Detection: no zoom is read from frames inside (or next to) a whip pan any more - on GitHub's test machines a
  blurred whip read as a zoom transition; a failed test now shows its lines in GitHub's public error notes.

## 0.3.0 - 2026-10-09 - Update button, colour rebuilds, HTML graphics, Claude + Resolve

- **Update available**: when a new version is on GitHub, a bright button appears in the sidebar. It shows what
  changed (every version since yours, from this file); *Update now* installs it and restarts MotionLab (about 10
  seconds), and afterwards *What's new* pops up once. Friends' shared cards and lessons arrive the same way (*New
  from friends*, no restart). MotionLab checks every hour and no longer installs updates by itself at start-up -
  *Settings > Sharing & updates* can switch that back on, or turn checking off.
- **Rebuilds in colour**: your clips are cached in colour now (about 3.9 GB per minute of footage; `--grey` keeps
  black-and-white edits at 2.6 GB), decoded with each clip's own colour settings (checked within 1/255 on a 10-bit
  test clip). Grades can set the saturation, and the DaVinci Resolve build gets matching colour LUTs. Black-and-white
  edits like test_4am look exactly as before. Preparing footage stops before it would leave less than 2 GB free.
- **Lab renders about 3x faster**: a render runs in several processes at once (test_4am: about 40 frames per second
  instead of 12; a full render takes under 2 minutes). Every frame now looks the same whether it is rendered alone,
  in a range or in a full render - the film grain is drawn per frame, so its pattern differs from 0.2 renders.
- **Graphics written as HTML** (optional, needs Node.js; [HyperFrames](https://github.com/heygen-com/hyperframes)):
  titles, counters, shapes, glows and particles are written as HTML/CSS and rendered to transparent video clips
  (`tools\overlay.py`). The lab render and the DaVinci Resolve build use the same clip - in Resolve a plain clip on
  its own track, no Fusion that can crash. Tried on 4AM's title and clock: the same frames as the lab's own
  graphics, within 4/255. `setup.bat` installs it (a fixed version, its usage statistics switched off). The Resolve
  side is new: try it on a copy of a project first.
- **Claude Code can look into DaVinci Resolve** (optional): *Settings > Claude Code > Connect Claude Code to DaVinci
  Resolve* sets up the community MCP server [davinci-resolve-mcp](https://github.com/samuelgursky/davinci-resolve-mcp)
  on your PC (a fixed version, its safe mode on), so in a chat Claude can read your open project - timelines, clips,
  markers. It asks before changing anything there; rebuilds still use the lab's own Resolve builder.
- **MotionLab's own MCP server** (`.mcp.json`): Claude gets compact views of the lab - every effect with frame +
  timecode, your verdicts, your videos - and contact sheets, any frames of a reference and rendered stills as
  pictures. A review no longer reads the whole `events.json` (0.7 MB for a 2.5-minute video). Claude Code asks once
  to allow it; `setup.bat` does that for you.
- **What's new** (sidebar, above *Open Claude Code*): every version as a timeline - yours marked, a newer one
  on GitHub on top with *Update now*, and the planned versions above them (`docs\plans.md`).
- *Settings > Programs* shows Node.js and HyperFrames (with an *Install* button when it is missing). This changelog has a fuller history (0.1.0) and is linked from the README; the roadmap
  is redrawn.
- For developers: `tools\dev\` (a headless-Edge driver and the fake-GitHub update test),
  `tools\motionlab\footage.py` (cache formats), `tools\motionlab\overlays.py`. `overlay.py render --mp4` renders a
  stand-alone motion graphic (example: `tools\overlays\examples\whats-new-0.3.0`, a 10-second clip about this version).

## 0.2.5 - 2026-10-07 - Review tab, possible misses, Delete, Claude effort

- **The analysis page**: the player uses the full width; below it the effect list and the selected effect are one
  **Review effects** tab - a looping preview of the effect (frame + timecode in the picture, ¼ ½ 1× speed), what
  happens, the evidence, and a bar that stays in view with Correct / Partly / Wrong (keys 1 2 3), your note and
  Previous / Next / Next without a verdict (J K N). *Correct* moves on by itself; *Partly* / *Wrong* put you in the
  note (Ctrl+Enter moves on); after the last effect it shows what is left to do.
- **Possible misses** have their own red tab, red cards and red ▲ marks on the timelines, so they can't be mistaken
  for effects of the list. Answer each one: *It's an effect* (+ what it is) or *Not an effect*; the answers go into
  the feedback Claude gets.
- **The workflow, visible**: References shows the six steps (download > lab pass > Claude checks > your verdicts >
  feedback > share); every card and every analysis shows where the video stands, with a button for its next step.
  Downloads that are not analysed yet are listed with *Analyse* and *Delete*.
- **Analyse with Claude** (the bright button): the lab pass runs as a job and Claude Code opens by itself when it is
  done, to check every effect - no Claude time is spent waiting. *Lab pass only* (grey) just measures.
- **Delete** for references (the analysis + its video in `refs\`), downloads, your videos (a whole project) and
  single renders: always after a dialog that lists every item with its size, into the Windows **Recycle Bin**. A
  video one of your edits uses (soundtrack, Resolve timeline) starts unticked; what the lab learned stays.
- **Claude buttons pick the effort level per task** (checking a video and feedback: high, recreating a video: xhigh;
  *Settings > Claude Code > Effort*) and name the chat so `/resume` finds it. *Tips for working with Claude* (Home,
  Settings): one chat per task, effort levels, saving tokens.
- **Recreate with my footage** (on a reference's page) starts the new `/recreate-video` skill: the reference's edit
  1:1 with your own clips, as a lab render and optionally in DaVinci Resolve.
- **Fewer tokens per chat**: `CLAUDE.md` (read by every chat) went from 31 KB to 13 KB; the app's internals load only
  when Claude works on the app, the Resolve notes only for Resolve work. The analysis skill skips the lab pass when
  the app already ran it and continues a half-finished review.
- Roadmap: v0.5 = use a reference as a template (its feel and pacing with your own story, not 1:1) and a macOS
  version.

## 0.2.0 - 2026-10-06 - MVP for friends

- **Share knowledge with friends** (new *Knowledge* page): every analysed video gets a reference card (category,
  format, link, pacing, every reviewed effect with your verdict and note). *Share my knowledge* sends your new cards
  and lessons to GitHub; everyone gets them with the next update. Lessons from others wait for review before they
  change anybody's analyser. Friends without GitHub access exchange pack files (*Import*). Claude reads all cards
  condensed per category (`knowledge\local\summary.md` + one detail file per category). No videos, frames or file
  paths are ever shared.
- **Automatic updates** from GitHub when MotionLab starts (git pull + restart; Settings can turn it off or only
  show a banner with what's new); *Settings > Sharing & updates* with *Check now* / *Update now*, and *Connect to
  GitHub* for copies installed from a ZIP. Starting MotionLab while an older version still runs replaces it.
- **Categories** for references (music video, ad, motion graphics, documentary, vlog, tutorial, cooking, podcast,
  gaming, sports, travel, fashion, comedy, trailer, fan edit, other) + free tags; the format is measured (vertical /
  horizontal / square, length); filters on the References page; editable later. Lessons can be tagged per category.
- **Pacing** per video: cuts per minute, shot lengths (average, median, shortest / longest 10 %), cuts in the first
  3 seconds, first cut, cuts on the beat, effects per minute - on every card and compared per category.
- App: sections renamed - **References** (videos by others that the lab analyses) and **Videos** (your own footage,
  edited in a reference's style); icons in the sidebar; new app icon (window, Desktop / Start-menu shortcuts).
- App: **Settings** page - finds Python, ffmpeg, Git, Claude Code, yt-dlp, DaVinci Resolve and Edge (version, path,
  how to install what is missing); download preferences; shortcut buttons.
- App: **Download from a link** (yt-dlp, very basic): MP4 up to 1080p / best quality / MP3, one video per link, into
  `refs\` (audio into `refs\audio\`), then *Analyse it*; the link, platform and uploader are kept with the analysis.
- App: **Open in Claude Code** buttons start Claude Code in the lab folder with the right request (review a video,
  apply feedback, review incoming lessons, save library effects); one in the sidebar opens it without a request.
- App: clear messages instead of silent failures (an error toast; a banner when the window is newer than the
  running server).
- `setup.bat` (Python packages + program check incl. Git, asks before installing anything, asks your name for
  sharing, Desktop shortcut), `README.md`, `LICENSE` (MIT), `.gitignore` (videos, analyses, projects, library,
  settings and local knowledge stay private).
- Knowledge: lessons L001-L007 from the first round of feedback; "flash look" and "possible misses" in every analysis.
- Effect library tool (`tools\library.py`): recipes + Fusion macros checked in DaVinci Resolve; installing them into
  Resolve is on the roadmap.
- Fixes found while checking against the reference: Fusion EllipseMask heights, macro outputs in imported comps.

## 0.1.0 - 2026-10-05/06 - The lab: analysis, rebuild, DaVinci Resolve

- **Analysis** (`tools\analyze.py`): every frame of a reference is measured (brightness, motion, sharpness, colour,
  pan) and turned into hard cuts, transitions and 30+ effect types with exact frame ranges. Every timestamp carries
  its frame number and timecode. Videos with a variable frame rate get a constant-rate copy first. The source's
  SHA-256 is checked before and after: a source video is never modified.
- **Audio**: beats refined to the attack (~5 ms on the click-track self-test), drops and BPM; "on the beat" = within
  one frame.
- **Per effect**: contact sheets, a looping preview, measured timing and easing, and how to rebuild it, in
  `report.html` / `events.json`; `tools\sheet.py` makes sheets for any frame range (effects the lab missed).
- **Claude checks every effect** (the `/analyze-reference` skill) and names it properly; your feedback
  (`MOTIONLAB FEEDBACK`, `tools\feedback.py`) becomes lessons and threshold changes in `tools\config.json`.
- **Self-tests** (`tools\selftest.py`): synthetic videos with known cuts and effects (basic, extended, negative,
  variable frame rate); every change has to pass them.
- **Rebuild with your footage** (option 1): your clips are decoded once into frame caches (`prep_footage.py`, a
  SHA-256 per clip), storyboards show what each clip offers, the edit is written as code (`edit_vN.py` ->
  `plan_vN.json`) and rendered by the lab compositor: clips with zoom and pan, solids, text, clocks, mosaic,
  fireworks, light streaks and photo strips, with eased keyframes (`render_video.py`: full render, part, stills,
  contact sheets, side-by-side with the reference). First rebuild: test_4am v1 (65 layers, 51 of 54 key frames on
  time).
- **Rebuild in DaVinci Resolve Studio** (option 2, `resolve_build.py`): the same edit as a native, editable Resolve
  project - Edit-page clips with zoom and pan, Color-page LUTs, Fusion for everything animated. `--doctor` checks the
  project and `--diff` lists what you changed by hand. test_4am: 1.83/255 average difference from the lab render, 53
  of 54 key frames on time.
- **MotionLab app 0.1** (`MotionLab.bat`): a local window with references and verdicts, projects, library picks,
  jobs and storage (`tools\storage.py`: disk use per category, pruning of what the lab can rebuild).
