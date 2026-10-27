# Changelog

What changed in each version of MotionLab, newest first. When a new version is on GitHub, MotionLab shows an
**Update available** button in the sidebar; it opens the sections below that are newer than your copy.
Version numbers: a new `0.x.0` is a big step; `0.x.y` adds a smaller feature; a four-part `0.x.y.z` is a small step
between them (fixes, upkeep, polish). The same notes in Spanish, from 0.5.1 on: [CHANGELOG.es.md](CHANGELOG.es.md).

## Unreleased

- **The Analyser: three ways to learn from a video.** *Effects & animations* (what it did until now), *Content creation*
  (coming soon: why a video works and went viral) and **Notes** - each with its own animated mascot: **FLUX** the
  blue crystal (Animations & Effects), **SPARK** the golden star (Content Creation) and **INDEX** the teal orb (Notes &
  Knowledge). They float, blink and react: hover a way and its mascot answers, while an analysis or notes run its
  mascot gets to work, and it lights up when they are done. Each way also has its own page - click a card and its
  mascot greets you there with its videos; the tabs under the ways still list everything. Thumbnails and Scripts & prompts sit in a
  smaller row under them; their buttons say *Analyze thumbnails* and *Analyze scripts & prompts*.
- **Notes from videos** (Analyser > Notes > *Take notes*): paste links or pick videos; links are downloaded up to 720p.
  MotionLab gets the words (the platform's subtitles, else speech to text), the key frames where the screen changes,
  the creator's chapters, YouTube's *Most replayed* moments and the sponsor parts (SponsorBlock); then Claude writes
  the notes by itself - a TL;DR, 3-7 key takeaways, the sections, the steps of a how-to, what to apply, the
  resources the description links and a context block for another AI. Every point is tied to the video's own words
  (or a frame it shows) with frame + timecode, and a click plays that moment; nothing is saved when a quote is not in
  the video. Write your own notes beside them, tick the actions, download it all as Markdown (with the transcript if
  you like) or copy it for another AI. *Delete the video, keep the notes* frees the space once you are done.
- The numbers of a video now keep its shares and saves too (TikTok gives both).

## 0.6.0.4 - 2026-10-27 - In the shot: B-roll on your words, graphics behind you

- **Your subject stays in the frame** - a horizontal clip in a vertical video used to be cut in the middle; now the
  catalogue finds each shot's subject (a face, else what the eye goes to) and the crop - and any punch-in - centres
  on it.
- **iPhone HDR clips in real colour** - clips filmed in HDR (an iPhone's default) are converted to normal video
  colours instead of coming out flat and washed out (about 3x the colour and contrast they had).
- **More variety in quick drafts** - a quick draft no longer uses the same shot twice or one scene over and over: on
  36 test clips a 30-second draft went from 18 to 26 different scenes in 28 shots.
- **The shots before the render** - with many clips Claude now lays out every shot of an edit as it will look, before
  anything renders, fixes what is wrong (a blurry or dark part, the same shot twice, a face cut off) and shows you
  the sheet first.
- **B-roll on the words it shows** - in a talking video, B-roll now comes in on the word it shows (say "post" and
  the phone with your post appears a quarter of a second later) or right on a jump cut to hide it. Each insert lasts
  2-4 seconds, your face keeps the hook and the ending, there is never a flash of face between two inserts, and at
  most 40 % of the video is covered: rules taken from creators' editing guides instead of a fixed timer. Your voice
  goes on under the B-roll, never cut or swapped for the clip's own sound.
- **Music clips are B-roll, not talking** - a clip with a song or loud background sound beside your talking take was
  taken for a second talking take, so the draft played all of it and laid no B-roll. Clips that never pause now
  count as B-roll.
- **Graphics that belong in the shot** - a graphic over someone on camera no longer has to look pasted on: a big
  word can sit behind your head and stay on the wall when the camera punches in, a glass card frosts the real room
  behind it with a soft shadow, graphics take on your camera's own softness and grain, and anything near your head
  keeps off your face. MotionLab finds you and your face in each clip once (about 30 ms a frame, nothing to install);
  Claude uses it when it edits a talking video. The idea comes from Vibha Ramprakash's video effects for Claude.
- **Curves you can see and shape** - a keyframe's move now offers the curves motion designers use (Easy ease,
  Strong ease, Glide, Launch beside Ease in / out, Hold and Pop), each shown as a little curve, and a chart with two
  handles you drag to shape your own - like After Effects' graph or the Flow plugin. Zoom effects take them too.
- **Effects that follow your face** - three new effects in the Editor: *Lean in* (a small, quick push in on your face
  for one word - it glides in and eases out), *Slow push* (a slow push in while the room melts out of focus) and
  *Spotlight* (the room goes dark, you stay lit). Zooms stay small and eased, and they land on your face even as you
  move.
- **Graphics in the shot, from the Editor** - a graphic's panel has *In the shot*: *Behind me*, *Frosted glass*,
  *Keep off my face* and *Pin to my face*. Before anything renders, the shot check now also flags a graphic that
  covers your face or a card your face would cut into, with its frame. A graphic pinned to your face shrinks to stay
  inside the frame and out of the app's top bar and caption area on a close-up.
- **13 new templates for talking videos** (after Vibha Ramprakash's designs): *Word behind you*, *LED sign behind
  you*, *Lock-on brackets*, *Countdown flip clock*, *Marker scribble*, *Comment box*, *Follow tap*, *Message stack*,
  *Reject stamp*, *Settings toggles*, *Glass graph*, *Task checklist* and *Headline box*. Each knows its place in the
  shot - the word and the sign behind you, the brackets and the scribble on your face, the cards in frosted glass,
  everything off your face - and Claude can put them on the words you say ("a stamp when I say 'dies'").
- **Fixed: a grey veil over your video** - a Motion Graphics template placed see-through over a video (its own
  backdrop off) laid its film grain over the whole picture, a faint grey veil that flattened the footage. Now the grain
  stays off over a video; the graphic takes your camera's own grain instead.
- **Fixed: a word in the wrong place in the Editor** - a graphic that sizes itself to its words (the big word behind
  you) showed up shifted half a word to the right and lower in the Editor's preview, cut off at the frame's edge,
  while the video itself was right. The preview now shows it where the video has it.

## 0.6.0.3 - 2026-10-27 - Lots of clips: a light cache and a clip catalogue

- **Lots of clips, a fraction of the disk** - a video's clips are now read once into a light copy (every frame,
  small) and only the frames your edit actually shows are prepared full size, right before the render. Tested on 36
  clips / 6.5 minutes of footage: 2.1 GB in 35 seconds instead of 33 GB in 131 seconds - and a 30-second edit of them
  adds about 2 GB, not 30. Clips prepared before keep working as they are.
- **Claude knows your clips** - with many clips, Claude first makes a catalogue of them: every shot inside every
  clip, the usable parts and the ones to leave out (blurry, shaky, too dark), its camera move and light, shots that
  look alike, the day it was filmed, and one line on what it shows. Every later step reads it instead of looking at
  every clip again, so edits with lots of B-roll pick better moments and *Improve* starts from what Claude already
  knows.
- **Quick drafts with many clips** - a quick draft no longer cuts across a change of shot inside a clip or puts two
  look-alike shots back to back, and with clips from several days it tends to keep them in order.

## 0.6.0.2 - 2026-10-26 - Keyframes and transitions in the Editor

- **Keyframes in the Editor** - click a shot: its new *Video* tab has Scale, Position, Rotation, Opacity and the zoom
  point, each with a ◆. Put the playhead somewhere, press ◆, move the playhead, change the value - the shot moves
  between the two, the way CapCut and Premiere do it. The keys show as diamonds on the shot: drag one to another
  moment, click it to choose how the move goes (Linear, Ease in, Ease out, Ease in and out, Hold, or Pop - a little
  overshoot). Drag a value's name left or right and the preview follows as you drag.
- **Transitions between two clips** - a + on every cut, or the new *Transitions* panel: Mix, Dip to black, Dip to
  white, White flash, Zoom in, Zoom out, Slide, Whip, Spin, Glitch and Light leak. Drag the block's edges for its
  length, pick a direction for a slide or a whip, or *Apply to all cuts*. A clip with no frames to spare never stops
  one: those few frames hold still, and the block shows it with stripes.
- **Why not here** - an effect or a transition that cannot go where the playhead is says why, right under it (a
  stutter on a talking video, a cut that already zooms, no clip under the playhead...), greyed out before you click -
  and the line above the list says where the playhead is. It changes as you move the playhead.
- **What to add, on a rail** - Clips, Sounds, Graphics, Effects and Transitions are now big icons down the side of the
  Add panel, each in the colour of its lane on the timeline, instead of small tabs.
- **Fixes** - the Editor's Clips list piled its clips on top of each other (and its + did nothing); a shot moved in the
  Editor left its shake behind; on the Analyser, the panel of a running job sits a little lower under the three ways. Safer sharing: a
  friend's sound-effects zip can no longer write a file outside its own folder, and the app no longer shows files
  outside the folders it shares (your ElevenLabs key file never).

## 0.6.0.1 - 2026-10-26 - Effects that work in the Editor

- **Effects you can actually add** - in the Editor, most effects stopped with an error: a shot that already zoomed
  (the quick draft's slow zoom on your first shot, a zoom into a cut) took no push-in, pull-out, punch-in or shake,
  and an effect near a shot's end said it was too close. Now a shot holds as many zooms as you like - each one its own
  chip on the Effects lane that you drag, lengthen, make stronger or remove on its own - and an effect near a shot's
  end starts a little earlier so it fits.
- **Dragging an effect** - a chip dragged past its shot's edge (or into the zoom beside it) now stops at the edge
  instead of giving an error, and a Punch-in can finally be moved. A slow zoom is shown as *Zoom in* again, not as a
  Punch-in.
- **No more effects you cannot use** - effects that need a clip are greyed out on a video made of graphics, and the
  stutter on a talking video, with the reason when you point at them. A flash or a black frame where no clip is under
  the playhead (an end card) still works, as a colour layer over the picture.
- **The layout is not an effect** - a corner camera's frame and an end card's background no longer show on the
  Effects lane, where moving them broke the layout.

## 0.6.0 - 2026-10-26 - Content agency: My Brand, the Editor and your content calendar

- **Content agency, the version** - MotionLab now knows your brand and plans your posts. My Brand (your goal,
  audience, colours, fonts, logo, voice, products, captions and end card - read from your website, then yours to
  fix) goes into every video, script and title made *For my brand*; the Content agency plans your posts on a
  calendar and shows how they did; the Editor lets you change any video yourself on a timeline; and the sound grew
  up - real and ElevenLabs-made sound effects you pick by ear, your music and ambience, every render at the same
  loudness. Everything below came in this version.
- **My Brand** - a new page at the top of the sidebar, in three tabs so there is little to scroll: *Overview* (your
  website, goal, audience and pages), *Style* (brand identity, tone of voice, captions and your editing look as video
  cards) and *Catalogue* (your products). It holds your goal on social media, who your videos are for, your logo,
  your brand's colours and tone of voice, your website and your catalogue - each product with its price and a switch
  for whether Claude may use it in videos. Everything saves as you type and stays on your PC. Colours can be typed as
  hex codes (#2eaa5c), the tone of voice has its own card with quick words to tick, and once you add your logo it
  shows large and faint in the page's coloured band. Your brand's name and what it does, its fonts (titles and body
  text) and your pages (YouTube, TikTok, Instagram... each with its own call to action) have their place too.
  *Start from zero* clears it all to try again (a copy is kept: *Bring it back* right after). The catalogue shows
  your products as cards with their picture (click it to add your own), price and an *In videos* switch, with *Add a
  product* on top.
- **Product motion** - New edit's Text step has *Show a product*: pick up to 2 products from My Brand and when they
  appear (in passing, at the end, or both). Claude builds them with a new Motion Graphics template, *Product card*:
  the product's picture on a card, its name, the price popping in, a button with your website and your logo - in your
  brand's colours and fonts, upright or wide, over your footage or as the closing card.
- **Content agency: the content calendar** - a new row under My Brand. Plan your posts on a month calendar: each
  with its day and time, where it goes (TikTok, Instagram, YouTube...), its stage from idea to posted (a colour each),
  the MotionLab video, the trending sound to add in the app when posting, notes and the links once it is up. Drag
  posts between days or keep them as ideas; set the days you post and the empty ones show as slots, with "this week 2
  of 3". *Add to Windows Calendar* gives you a reminder an hour before each post. **Your videos**: *Check my pages*
  reads your YouTube and TikTok (the pages in My Brand - public numbers, no login, only when you press it) and shows
  your posted videos with when they went up, their views, likes and comments, which did better than usual and how
  much each grew since the last check; the calendar shows what went up each day. **Import your stats**: the file you
  download from YouTube Studio, TikTok Studio or Meta Business Suite (English or Spanish) adds watch time, % viewed and
  click-through to your videos - and brings in Instagram, which cannot be read otherwise. A post shows **how it did**
  (views now and at 48 hours, 7 days and 28 days after it went up, from your checks), the **Test & compare** winner, a
  **before you post** checklist per platform (chapters, the sound added in the app, hashtags, the paid-partnership
  label...) and which format each platform wants against your video's. **When to post**: type your audience's best
  hours from each platform's stats and they show as quick picks on every post (without them, generic times marked
  as such).
- **A tidier sidebar** - Motion Graphics sits above Claude's memory, and Jobs and Settings (now with a cog) open from
  *More* at the bottom; a running job's count shows on *More*.
- **More of your brand** - your voice in your own words (four sliders - formal to casual, serious to funny,
  respectful to cheeky, calm to excited -, the words you use and never use, lines that sound like you), your content
  pillars (each post on the calendar gets one, and the calendar shows the month's balance), a product's promo code and
  a *Paid partnership* switch (Claude then marks it as an ad), and what your website says - the import keeps its
  readable text for Claude to check facts against.
- **Your brand at a glance** - My Brand's Overview opens with a card of what *For my brand* gives Claude (logo, name
  in your title font, colours, fonts, tone, pages, products) and your latest videos made with *For my brand*. On Style, *Names and words* keeps names spelled exactly (RIFT in capitals...) in captions, scripts and
  titles, and speech to text gets them right.
- **Your captions** - My Brand has a caption style: the look, font, capitals or not, the text and spoken-word colours,
  how the words move, where they sit and a box behind - with a live preview. Claude's captions use it, and the
  Captions button on a video's Graphics tab offers it.
- **Your editing look** - pick up to 3 videos you analysed as how your brand's videos are cut. New edit offers them
  first as *My brand's look*, and with *For my brand* ticked and no reference picked, Claude and the quick draft
  follow your look.
- **Your mood board** - My Brand > Style has a mood board: drop in pictures you love the look of (saved from
  Pinterest or Instagram, screenshots, photos). MotionLab reads them - light, colour, contrast, how much room - and
  shows their main colours, one click from your brand colours. Videos made *For my brand* follow the board's feel in
  their graphics and thumbnails; Claude looks at the pictures themselves. They stay on your PC.
- **Your logo in every version** - My Brand > Style takes your logo for dark backgrounds, for light ones and the icon
  alone, and where it goes in your videos (the end card, also small in a corner, or nowhere); Claude puts in the
  version that reads on each background. Under your colours, *Does it read?* shows your text and accent colours on
  your background with their contrast, and Claude never puts words in a colour that doesn't read.
- **Your brand in New edit and the graphics** - New edit's colour palette offers *My Brand* (your colours, the accent
  first), every font list shows your brand fonts first, and with *For my brand* ticked the Generator's quick draft
  paints its graphics in your colours and fonts.
- **Your end card** - My Brand > Style lets you pick how your videos end: a logo card, a title card with your website,
  or a channel card, plus your sign-off line, with a live preview filled from your brand. Claude builds that exact
  card as the last scene of a video made *For my brand* (never before the hook), and so does the Generator's quick
  draft. It can also have your own sound logo: a short sound ElevenLabs makes from your words (or your own file),
  played on the end card instead of the template's sounds.
- **What worked for you** - My Brand's tone of voice shows the hooks, endings and titles of the scripts, titles and
  videos you rated good (each opens its script), and Claude follows their shape - never the same words - when it
  writes for your brand.
- **Caption size and words per line** - My Brand's caption style also sets how many words show at once (1 to 6) and
  the size (small to huge), and the preview shows both; captions made in your style follow them, also when they
  follow your script.
- **Product facts and media** - each product in My Brand's catalogue has *Facts & media*: its key benefit, the claims
  Claude may make (each with its proof), the ones it must never make, and screenshots or short screen recordings.
  Claude says only what they say about it.
- **Your logo in Motion Graphics** - the logo picker shows your own logo first (and under *My Brand*), next to the
  library's; any graphic with a logo can use it, and it draws the version that reads on its background by itself
  (the light one on dark, your main one on light). It stays on your PC.
- **Your sound library** - Motion Graphics has a *Sounds* tab: every recorded sound on your PC by kind, ▶ to hear it,
  where it came from and its licence; ★ makes one a favourite (its kind uses your favourites first) and *Hide* keeps
  one out of your videos. *Add sounds* takes a pack, a folder or a few files: a pack MotionLab knows is sorted the way
  MotionLab's own library is, the rest by their names. Friends get the same sounds: MotionLab now comes with four free
  (CC0) sounds and a list of which sound of which free pack it uses, so importing that pack gives them the same
  library. New edit's Sound step has *Choose the sounds*: listen and tick the ones a video may use. **Make sounds**
  with your own ElevenLabs key: pick how many of each kind (the kinds you have few of come first), it shows the
  credits it takes, and the new sounds wait under *New* for you to star the good ones and hide the rest. MotionLab
  comes with 20 of them already: whooshes, whips, pops, clicks and keystrokes made from premium motion-design
  descriptions. The free plan allows non-commercial use only, and a video you post credits elevenlabs.io, so its
  sounds are marked *non-commercial*; sounds made on a paid plan can be shared:
  *Share with friends* makes one file for Google Drive, and a friend adds it with *Add sounds* > the link.
- **Your music** - Motion Graphics has a *Music* tab: the songs you download in the Analyser and the ones you add,
  each measured once - its tempo, how energetic it is, its tone and its length - with ▶ to hear it, ★ and Hide. New
  edit shows your songs as cards with the same facts, so you pick by ear and by feel instead of a file name.
- **Ambience under your voice** - a quiet room, a café, a street or rain under a talking video fills the silence
  between your cuts. Make it with ElevenLabs (it loops with no seam) or add your own; New edit's Sound step has
  *Ambience under your voice*, and it is mixed far under your words.
- **The Editor** - a video's new *Editor* tab: a timeline like CapCut's, no Claude window. Your shots on a main track
  that closes up by itself, graphics and captions above, effects, sound effects and your voice (or song) below, and a
  live preview that plays your changes before you save. Shots: drag one to move it, its edges to trim it (more of its
  own clip, or less), split it at the playhead (S), play it slower or faster (¼× to 4× - its voice keeps its pitch),
  show another moment of its clip in the same place (Alt + drag), swap in another clip of the video, turn its sound
  down or mute it, delete it - and add a clip from the *Clips* tab. A video made from zero gets its scenes on that
  track, moved and trimmed the same way. Effects (zooms, shakes, flashes, transitions...) are chips you drag, make
  stronger, longer or eased, remove, or add from the *Effects* tab. Drag graphics and sounds to another moment or trim
  them; add sound effects from your library and templates from Motion Graphics (drag them onto the timeline), change
  their words and colours (your brand's colours one click away), turn a sound up or down or give it another sound. A
  song: drag it to start the video at another moment of it, or change its volume. Captions: drag one to move it or its
  edges to trim it (its words stay in step with the voice; a caption it runs into gives way), split one at the
  playhead, add one, fix or remove one, and change how they all look - Classic or Clean box, font, size, position,
  colours. *See it rendered* shows the two seconds around the playhead exactly as Save will. Undo / redo, snapping,
  zoom. *Save* makes a new version (the one you started from stays), cuts your voice again to fit, and makes again
  only what changed. Claude reads what you changed by hand next time.
- **A video's tabs, each its own colour** - Overview, Review and Editor carry an icon and a colour of their own:
  Review is violet (it hands the video to Claude), the Editor cyan (you, by hand). Under the Overview's player two
  ways on, in those colours - *Change it yourself* (the Editor) and *Improve it with Claude* (Review) - with *Start
  over* as a link under them, and the Editor in the Overview's side list. A video's renders are one *Selected version*
  list; the Editor's changes are a list under their button. The Editor's look checked against two design checkers
  (Impeccable and Hallmark): no gradients or glows, larger small text, a focus ring on every control.
- **Import from your website** - one button beside your website reads it and brings in what it finds: a shop's whole
  catalogue (Shopify, WooCommerce, or product details marked up on the pages) with prices, descriptions, pictures and
  links, plus your logo, colours, fonts, name, description and pages. A pop-up first shows everything and where each
  thing goes. You tick what comes in, and what My Brand already has is marked, so nothing is added twice. Fonts your
  site uses that are free Google fonts come into your fonts on this PC, with their licence, ready for titles and text.
  The colours come from a screenshot of your page - what a visitor sees - each with its job (background, text,
  accent) and how much of the page it covers, your logo's colours too, and the exact values your site's code uses.
  The button is big, a progress bar shows how far the reading is, and you can leave the page: when it finishes
  elsewhere, MotionLab tells you, a dot appears on My Brand, and what was found waits there until you import it.
- **For my brand** - New edit, the Generator and Prepare's scripts and titles have a *For my brand* switch: ticked,
  Claude makes it yours - your colours, your logo on the end card, your website in the call to action, your tone of
  voice, an ending that fits your goal, and only the products you allow, at your prices. In New edit it sits at the
  top, with a small preview of what Claude gets (your logo, colours, website, goal, products, tone of voice).
- **Build in DaVinci** - New edit's last step has one simple card with the DaVinci Resolve logo instead of the
  checkbox at the bottom.
- **Easier to read** - pale grey text is lighter (it now reads clearly on the dark background), no text is smaller
  than 11 px, long lines wrap shorter, and a paragraph no longer ends on one lonely word.
- **A cleaner look** - cards lose the coloured stripe down one side (a thin border in the same colour instead), and
  buttons and cards lose their coloured glow; the glassy colour of each section stays.
- **More varied motion graphics** - a generated video no longer leans on the same few templates: each scene gets
  its own (no more one template coming back every other scene), the templates your last videos used step aside unless
  one is clearly the best fit, and Claude gets a few options for every line of your words instead of one short list
  for the whole video. Edits of your clips in the Editor get the same: fresh template options that fit your words or
  script, and the ones your last videos used step aside. Fewer odd matches too: little words like "up" or "short" no
  longer pull in a chart or a random template, "stream" no longer counts as "streak", and a line nothing fits gets
  kinetic text instead of an end card in the middle of the video.
- **Finished sound** - every video MotionLab renders now comes out at one steady loudness (-14 LUFS, the level
  YouTube plays at) with its loudest peaks under -1 dB after the video is compressed: no more quiet talking videos,
  and no crackle when a platform encodes them again. A video made before gets it on its next build, without
  rendering the picture again.
- **Sound in videos made from zero** - a video with sound effects but no song came out silent; the effects are now
  its sound.
- **Sound effects stay off your words** - in a talking video a whoosh, pop or hit that lands on a word is now very
  quiet (at least 22 dB under your voice), and one in a pause sits at the right level next to your voice - it used to
  come out too loud in the pauses.
- **Nothing over your face** - every build of your video now checks that no caption or graphic covers your face
  (measured on the frames, also when you are in a corner picture), and in an upright video that none sits under the
  app's own buttons and captions at the top, bottom or right edge. Claude moves what it finds before you see the
  video; a graphic that is meant to be on your face (a before / after) can stay. Captions of what you say now place
  themselves shot by shot: under your chin when there is room, in a close-up just under your mouth - never over your
  eyes or mouth, never up on your forehead, and out of the platforms' bottom band.
- **Talking videos end on the word** - the build says when a talking video goes on after its last word (an end card
  there is fine) and when it has more than 4 whooshes in 30 seconds.
- **Keyword captions** - a third caption look beside Classic and Clean box: one or two small words with ONE big
  keyword under them in your accent colour, in a serif italic, each word as you say it. Pick it in My Brand's caption
  style or for a video's captions.

## 0.5.4 - 2026-10-25 - Sound: real sound effects, picked by ear

- **Sound, the version** - this closes the sound version that 0.5.3.3 and 0.5.3.4 began: sound effects from real
  recordings in your own sound library instead of made-up ones, quick drafts that come with their sound effects, a
  song from a link with a copy without it to post. The next steps - sounds shared with friends, choosing the sounds
  yourself, a music library - come with 0.6.0.
- **More recorded sound effects, picked by ear** - on the PC where the sound library lives, a third listening round
  added recorded sounds for glitches, glows (two glissandos), a phone buzzing and ticks, and more variety for soft air
  moves; where the made-up sound was the one liked (ghosts, pops, game hits) it stays. A sound not picked is set aside,
  never deleted.

## 0.5.3.4 - 2026-10-25 - A song from a link

- **A song from a link** - New edit's *Sound* step has *From a link…*: paste a TikTok, YouTube or SoundCloud link and
  the song downloads as an MP3 and is picked, so the edit cuts on its beats. A song you downloaded is someone else's,
  so every render on it also gets a copy without the song: *Ready to post* shows it with where the song starts (e.g.
  "from 0:11.63") - you add the same sound in TikTok or Instagram, and your post is not muted. Your sound effects stay
  in the copy.

## 0.5.3.3 - 2026-10-25 - Recorded sound effects, and quick drafts with sound

- **Sound effects from real recordings** - the whooshes, risers, hits, clicks, pops and camera sounds in your edits
  now come from recorded sound effects in your own sound library, not only made-up ones. Each one lands on its frame
  like before (a whoosh's peak on the move, a riser's end on the drop) and a different one plays each time. Claude
  can add a free pack you download; it stays on your PC. Kinds with nothing recorded yet keep the made-up sound.
  They also sit a little lower under the song (2 dB), never so low that the song buries them.
- **Quick drafts come with sound effects** - a quick draft from New edit now puts a sound on its own effects: a hit on
  the drop and on flashes, a riser before a speed-up, a quick swish on each punch-in of a talking video. How many and
  which kinds follow New edit's *Sound* step (Auto = a few on a talking video, some on a music edit; None = none).
  *Finish it with Claude* keeps them.

## 0.5.3.2 - 2026-10-25 - Film it hands over to the Editor, and Finish it with Claude

- **Film it hands over to the Editor** - a script's *Film it* keeps the teleprompter, the lines and adding your
  recording; its last step is now **Continue in the Editor**, which opens New edit with your recording and the script
  already loaded, so a talking video gets every New edit option (references, style, palette, sound effects, length,
  format). The script's *Edit it* step goes straight there too.
- **Finish it with Claude** - when the newest version of a video is a quick draft, its page shows *Happy with the cuts?
  Finish it with Claude*: tick what to add (motion graphics, captions, sound effects, colour - ticked already from
  what you picked in New edit), say anything else in your words, and Claude makes the next version on top of the
  draft. The cuts, transitions and timing stay as they are; the draft stays too.

## 0.5.3.1 - 2026-10-25 - 114 new Motion Graphics templates

- **114 new Motion Graphics templates** - text reveals, charts, social posts, app screens, a logo reveal and a
  transition, made by MotionLab in the Editorial warm look: 189 templates in all. Each takes your words, colours and
  fonts, and they play in the live preview while you change them.

## 0.5.3 - 2026-10-24 - Faster videos, photos in your edits and a thumbnail preview

Faster videos - Claude makes a video in fewer, shorter steps:
- **The Generator asks what Claude used to guess** - a look for the graphics (Editorial warm, Swiss signal, Night
  edition or Surprise me) and *The song from last time* next to the song. All optional: Claude still picks when you
  leave them.
- **Claude starts from a brief** - when you save a request, MotionLab writes everything Claude needs into one page
  (the song's beats, the templates that fit your words, your ratings as rules, the lessons for that kind of video) and
  lists what it left out, so nothing is dropped.
- **One build instead of many steps** - graphics, sound effects, the video, the checks and one sheet of every cut, in
  one go; only the graphics that changed are rendered again, several at a time. The final gives motion blur only to
  graphics that move (captions and still graphics stay plain: a 60-second final went from 13.5 to 6.5 minutes).
  Long final renders run as jobs on the Jobs page.
- **Fewer rounds of checking** - text that runs off the frame is flagged on the first snapshot, sound effects come out
  at levels that pass the check, template moves land on the beat by their measured timing, and every template is
  checked at vertical and square sizes.
- **Talking videos** - captions keep your script's own words, the voice is levelled per take, black screen-recording
  flashes are avoided, and Claude edits with a short list instead of a long program.
- **Review** - *Send it to Claude* now says which parts the next version will change.
- **What it took** shows how much of Claude's time was spent waiting for the lab's tools.

Also new - most of it asked by a friend who edits with MotionLab every day:
- **Photos in your edits** - *New edit > 1. Clips* (and *Film it*) take photos as photos: JPG, PNG, WebP, HEIC / HEIF
  from an iPhone, AVIF, BMP, TIFF, GIF, the right way up. Each shows with its own picture and a yellow PHOTO badge,
  and a click on its length (3 / 5 / 8 s) sets how long it stays on screen. In the edit a photo is a still shot with
  a slow zoom; a horizontal photo in a vertical video can show whole over a blurred copy of itself. Claude sees a sheet
  of your photos and places them in the story.
- **Add a whole folder** - *Add a folder…* (or drop one) takes every video, photo and song inside, sub-folders too, in
  order. Two files with the same name from different folders (C0001.MP4 of two days) both get in.
- **No more black clips from a Mac or iPhone** - the hidden "._" files a Mac or an iPhone leaves next to your clips
  are never copied in, and ones copied before no longer show.
- **Rename the new video in step 1** - its name stays editable after the clips are in.
- **Pages update by themselves** - a finished render, a script Claude wrote, a new analysis: they show up on the page
  you are looking at within a few seconds - never while a dialog is open or you are typing.
- **NEW on everything new** - a red NEW badge on new videos (a finished render), scripts, prompts, analyses, sets and
  motion graphics; it goes when you click the card or move to another section.
- **Improve my script keeps one card** - while Claude works your pasted script shows as *improving…*; when the new
  version is saved it takes the old one's place (the old one goes to the Recycle Bin - never one you already filmed).
- **Your changes survive updates** - thresholds tuned for this PC now live in their own file that updates never touch;
  other changes an update replaces are kept and come back with *Bring them back*. Settings this version does not know
  are kept too.
- **MotionLab's own taskbar button** - the window and a pinned MotionLab show MotionLab's icon, not Microsoft Edge's.
- **Preview your thumbnail** - *Analyser > Thumbnails* shows your thumbnail on a copy of YouTube's Home page (and
  Search, Up next, a phone) next to the newest, most viewed videos of big creators - MrBeast, Mark Rober, MKBHD and
  more; *Channels…* changes the list - or next to the thumbnails you analysed. Dark or light, *Squint* to see what pops,
  *Where is mine?*. Your pictures are not saved.
- **Fewer zooms in edits** - zooms, whips and pushes now keep their distance (one every few seconds, one every ~8 s on a
  talking video) and never jump between two shots of the same take; a build names an edit with too many of them.

## 0.5.2 - 2026-10-22 - New edit, step by step, and a lighter app

- **New edit, step by step** - *Editor > New edit* is now a pop-up of six numbered steps on a line, one at a time:
  1 Clips, 2 Text, 3 References, 4 Style, 5 Sound, 6 Final. Only the clips are needed - leave the rest on Auto and
  Claude decides. Back and Next at the bottom, a ✓ on every step you answered, and a click on a step jumps to it.
- **Your clips as pictures** - step 1 shows each clip of the video as a frame with its length: play it, drop more in,
  or remove one (to the Recycle Bin, after a yes). Picking an older video shows how many clips it has.
- **Text** - what the video is about and the words on screen side by side, or a script or brief from Prepare.
- **References** - up to 3 videos you analysed, as picture cards with their length: follow their style, or make an
  exact copy.
- **Style** - the ready-made styles in a row, a few short questions (where it was filmed, what kind of video, the
  rhythm, the mood, the captions) with 4 answers each and + for the rest, and a big colour palette for the motion
  graphics: 7 ready-made palettes or your own colours.
- **Sound** - the music (the video's own song, a song you pick, the sound as filmed, or talking with the pauses cut),
  how many sound effects and which kinds.
- **Final** - the length and the format for each platform, a summary of every step (click one to change it) and about
  how long Claude will take. Claude reads everything you picked first and follows it step by step; the quick draft
  follows the references, the style, your words, the length, the format and the music.
- **A script in three tabs** - a script's pop-up opens on **Script**: the whole text (no more *Show all*), its rhythm
  as a bar of its parts and their seconds, and beside it the shots to film and the text on screen, each in its part's
  colour. **Checks** has the check, Claude's check and the script again with the part you are reviewing highlighted -
  Claude's tip for that part sits right in your review. **Details** has the rest. Prompts get the same three tabs.
- **A script's road** - 1 The script, 2 Film it, 3 Edit it, 4 Post it on a line: what is done gets a ✓, the next step
  is lit, with its button at the end. *Film it* shows the same line, and its last step has *Make it with Claude* on
  the left and the quick draft on the right.
- **A lighter Home and Claude's memory** - Home ends with the roadmap (no Claude's memory line, no Status panel).
  Claude's memory keeps Overview, Lessons and Shared knowledge; the Videos, Effects and Graphics & saved effects tabs
  are gone - Claude still reads all of it, and your saved graphics and effects stay in the library. Motion Graphics
  moved to the bottom of the sidebar, above Jobs.
- **The roadmap, planned again** - 0.5.3 faster videos (with Claude's time on reviews, scripts and videos), 0.5.4
  **Sound** (real recorded sound effects, music and ambience from free libraries, a voice-over), 0.5.5 **Content
  agency** (a *My Brand* page: your goal, audience, look and products), 0.5.6 template packs, 0.5.7 colour + DaVinci
  Resolve, 0.5.8 content generation, 0.5.9 yapping mode; 0.6.0 is now *Take notes from videos*. The prompt generator
  and templates by feel left the plan.
- **Small things** - more room around the Analyser's "downloaded videos" row.

## 0.5.1 - 2026-10-19 - Phase 2 begins: MotionLab in Spanish, analyses in half the time, a one-file install, one way to review

- **Phase 2 starts here** - the path from 0.5.0 to 1.0.0, deployment. Phase 1 was everything up to 0.5.0.1. The
  roadmap on Home shows both phases, and the planned versions each moved one number up: yapping mode is 0.5.2 now,
  faster videos 0.5.3, the prompt generator 0.5.4, template packs 0.5.5, colour + DaVinci Resolve 0.5.6 and content
  generation 0.5.7.
- **Español** - *Settings > General > Language*: English or Español (Spain, tú). One click and the app reloads in that
  language - every page, dialog, message and check, the dates ("hace 2 días"), the numbers (4,5) and the counts, the
  names and settings of the Motion Graphics templates, a video's report and, from this version on, *What's new*. On a
  Spanish Windows the installer speaks Spanish too, and the MotionLab it installs starts in Spanish. Claude answers you
  in Spanish in every window the app opens; what it saves in MotionLab (reviews, lessons, its memory) stays in
  English, so what you share reads the same for your friends.
- **Installing is one file now** - *Install-MotionLab.cmd*: download it, double-click it, answer two small questions
  (motion graphics, your name) and press Y. It installs Git, Python, ffmpeg, Claude Code (and signs you in), the
  rest of the programs and MotionLab itself in one go - no terminal, no commands to type, no "open a new window and
  run it again" - and opens MotionLab when it is done, with an icon on the Desktop and in the Start menu. It says
  first what it will install, how big each part is and where Windows will ask for permission; it starts you on the
  last tested version (the one the Update button installs). Run it again (or setup.bat) any time: it only does what
  is missing. The README has the 3 steps, in English and in Spanish.
- **setup.bat repairs**: a copy downloaded as a ZIP gets connected to GitHub by itself (updates work), a missing
  program is installed after asking, and *Settings > Connect to GitHub* is filled in for you.
- **Three ways into the Analyser**, like Prepare: **Videos**, **Thumbnails** and the new **Scripts & prompts** - each
  says what is there and what Claude has not checked yet, and each kind has its own tab under them. On Home the first
  card is *Analyze what works* - Videos, Thumbnails, Scripts.
- **Scripts & prompts**: paste or drop up to 20 at once - talking scripts, hooks, prompts for AI video and image tools,
  briefs (.txt, .md, .docx, .pdf). MotionLab numbers and measures them on the spot (their kind, length, the words they
  share, twins); one Claude window then checks each one, part by part, and names what they have in common - you mark
  each pattern Correct / Partly / Wrong. They live in your prompt library, so Optimize, Film it and your ratings work on
  them too.
- **Claude quotes, it doesn't invent**: Claude can no longer put words in your prompt's mouth - every part it quotes
  from a prompt or a script is checked against the text before it is saved (a paraphrase, pieces out of order or words
  from another prompt are sent back), and MotionLab keeps the exact words and where they are.
- **Shared knowledge** - Claude's memory has its own tab for what you share with friends and what came from them: tick
  what goes with your next share (anything whose name looks like a test stays on your PC until you tick it, and a lesson
  that names a file on your PC is flagged), see what you shared before, and per friend their videos, their lessons
  waiting for a review and the rules that came from them. Everything a friend shared carries a lime "from <name>" badge.
- **In the style of** - every style picker lists only the videos you analysed on this PC, with their picture and a name
  a person would use (no more "Video by ..." or "[VLDJ_-wrwj8]"); in Prepare you can also pick your own scripts and hooks.
- **Honest counts** - "effects you confirmed" now counts only your own verdicts (your friends' are counted apart, so it
  can drop - on a PC with only friends' videos it shows 0), and Claude tells you when something it made came from a
  friend's knowledge.
- **Names a person would use** - the Analyser and a video's page show the name you gave a video, Claude's name for it
  or its title without the "[VLDJ_-wrwj8]", instead of the file name (point at the name to see the file's); Home's
  Status lists your edits by the names you gave them, and the Jobs list and the Delete dialog use them too.
- **Claude remembers your scripts & prompts** - Claude's memory now includes the sets of scripts & prompts you analysed
  and the patterns you marked right (never shared); writing a script or a title reads a shorter memory, without how the
  effects were made.
- **One way to review** - reviewing looks and works the same everywhere - an analysed video's effects and possible
  misses, a video's Review (Editor and Generator), a script or a prompt, a title, a thumbnail set, a set of scripts &
  prompts: the thing on the left, your review on the right, the same ✓ ~ ✗ buttons (keys 1 2 3, J K to move), one note
  that saves as you type, "N of M reviewed", and one last step: Send it to Claude.
- **Is Claude right?** on scripts and prompts: say if Claude's check of each part is right (Correct / Partly / Wrong) -
  Claude follows your verdicts when it improves them. Point at a part to see its words marked in the text.
- Thumbnail sets and sets of scripts & prompts: your note on each pattern is kept, and *Send it to Claude* looks at the
  patterns again with your verdicts - it keeps the ones you marked correct and fixes or drops the rest. A video made in
  the Generator is improved by the Generator's own Claude skill.
- Possible misses: "✓ Not an effect" is the first button now (key 1), "★ It's an effect" the second (key 2).
- Prepare lists only your own scripts: other creators' scripts you analyse stay in their set and the prompt library.
- MotionLab reads a PDF's text itself once the update installs its PDF reader (until then Claude reads PDFs, as before).
- **Claude starts lighter** - the notes every Claude window reads first are about a third shorter (the same rules),
  Claude reads its notes on an app page only when it changes that page, a helper reads only the part of a skill it
  needs, and four of MotionLab's Claude skills had lost their description, so asking in your own words ("apply this
  feedback", "remake my clips like this video") could miss them - they are back.
- **Analyses take about half the time** - the lab pass now measures several frames at once on your PC's cores and
  listens to the music at the same time, and the overview picture and the numbers file are written faster (a
  30-second test video: 35 s -> 19 s). The results are the same as before.
- **Faster to open** - the window appears about 3 seconds sooner after a double-click (MotionLab no longer waits on
  two slow checks of its own port first), and the restart after an update is about 5 seconds shorter.
- **Faster pages** - Home and Claude's memory answer several times faster: the Motion Graphics templates are no longer
  worked out there only to be left out. Motion Graphics' tabs and the Generator's graphics dialog rebuild the
  catalogue only after a template or a pack changed.
- **Learned from with hundreds of clips** - the clips' pictures load as you scroll, and a clip loads only when you
  point at it.
- **Lighter in the background** - while the app is open it no longer starts PowerShell every 20 seconds to ask whether
  DaVinci Resolve runs; it looks at the list of running programs (PowerShell only while Resolve is open).
- Fixes: a note on a part of a video is no longer lost when you click away without pressing Enter; every Claude button
  failed when the Windows user name or the MotionLab folder had an accent (José, María); a program installed while
  MotionLab was closed is found at the next start without signing out; *Update yt-dlp* no longer brings a second copy
  of ffmpeg along; "how to get it" hints point to setup.bat instead of terminal commands; a start that fails (for
  example after an update whose install step broke) is now written to the app's log, so *Report a problem* and Claude
  can see why; ffmpeg's own error now reaches the job log when a video's or a song's name has letters like Á or Í (a
  Python error showed instead); *Generate a new prompt* and *Use it, change…* hand your words to Claude whole - a long
  wish lost its end (and the style you picked), and signs like %, &, < or > were dropped on the way.
- Analysis fixes: a damaged video can no longer make an analysis (or the preparation of your footage for an edit) hang
  for ever; when a video is replaced by another one under the same file name, its new analysis no longer reuses the
  old video's sound and frame copy; the mirror-symmetry and repeated-tile measurements now give exactly the same
  numbers on every run.
- For developers: the UI tests (smoke, the update test, `tools\dev\cdp.py`) use free ports and a browser profile of
  their own, so two can run at once; a browser that does not start fails at once instead of after 2.5 minutes; the
  self-test's 75 motion snapshots run 4 at a time. `tools\dev\i18n_check.py` checks the translations (every text has
  its Spanish, its placeholders and tags kept, nothing unused), lists each area's work and merges the part files;
  smoke.py runs it and opens Home once in Spanish.

## 0.5.0.1 - 2026-10-16 - Logos for your motion graphics

- **Logos for your motion graphics** - 92 real logos of apps, platforms and AI tools (YouTube, TikTok, Instagram,
  Premiere Pro, After Effects, DaVinci Resolve, Figma, Claude, ChatGPT, Midjourney...), sharp at any size, in their
  own colours or in one colour of yours. *Motion Graphics > Logos* shows them all: pick a few and *Make a logo wall
  with them*. In a graphic's settings, *Pick a logo…* puts one in, and the texts that take an icon (a notification,
  a phone's rows, a hub and its nodes, a lower third's badge, an app tile) have *+ Logo*. A new template, **Logo
  wall**: your stack, the platforms you post on or your clients - tiles popping in one after another, an endless
  sliding strip, or one big logo at a time. When your words name an app ("the AI tools I use: Claude, Midjourney"),
  the Generator suggests the graphics that can show its logo.
- **New edit** is clearer: step 1 *Select your clips* asks plainly - *Clips you already have* (one of your videos) or
  *New clips* (name it, drop your files in); step 2 is now *How should it be edited?*; the last step is simply the
  *Make it with Claude* button, with *Also build it as a DaVinci Resolve project* as its own option under it.
- Fixes: the checklist's click sounds follow how many lines it has (it always played three); the shape wipe now
  covers the whole frame at its slant.

## 0.5.0 - 2026-10-16 - Motion Graphics: 74 ready-made graphics, and the Generator builds from them

- **Motion Graphics** - a new section in the sidebar: 74 ready-made motion graphics. 57 were learned from pro
  template clips - titles that stretch, scatter, fall apart or flicker like neon, counters and progress rings, bar,
  line and dashboard charts, checklists, sticky notes, chats and speech bubbles, notifications, a profile card, an
  envelope that opens, stories, a photobooth strip, phones fanning out, a pencil that circles things, a pixel wipe,
  a loading ring, a logo sting... - and 17 are new, for what template sites offer most and the clips lacked: **lower
  thirds**, a **subscribe button** with a cursor click, **call-outs**, **shape transitions**, an **end screen**, an
  **audio visualizer**, a **donut chart**, **before / after**, a **news bar**, **credits**, a **price tag**, a
  **review** with stars, a **map route**, a camera **REC frame**, a **chapter bar**, a **poll** and a **top-10 rank
  number**. Click one to play it and type your own words - it changes at once, before anything renders - then *Use in
  a video* or *Make a video with it*. Every one takes any size (vertical, horizontal, square) and comes with its sound
  effects. *Learned from* shows the clips you captured, what MotionLab measured in each and what Claude thinks it is
  good for.
- **The Generator builds from them** - a motion-graphics video now starts from these templates: the dialog suggests
  the ones that fit your words as you type (pick some to be sure they are used), and Claude builds the scenes from
  them instead of writing every graphic from zero.

## 0.4.6 - 2026-10-16 - Fonts and captions: 28 fonts, live previews, caption looks

- **Claude's check uses less of your Claude plan** - on videos with many effects, helpers look at the contact sheets
  in parallel and Claude keeps its notes as it goes, so nothing is looked at twice; every sheet is still read.
- **Fonts that come with MotionLab** - 28 free fonts (Anton, Bebas Neue, Montserrat, Poppins, Inter, Luckiest Guy,
  Permanent Marker...) in every graphic's, caption's and thumbnail's font list, grouped by what they suit, with a line
  in the picked font - the same render on every PC. Your own font files go in `library\fonts\` (they stay on your PC).
- **See a change before you render it** - a video's Graphics tab now draws each graphic live: change the font, a
  colour or the size and it shows at once; a slider and play move through it.
- **Caption looks** - *Classic* (as before) or **Clean box**: sentence case on a rounded dark box that fits the line,
  the word being said in cyan, a soft fade, higher on upright videos so the apps' buttons don't cover it. One click;
  captions you already made can take it too (your words and settings stay).
- **The font of a thumbnail set, measured** - MotionLab compares the words on a set's thumbnails with every font it
  has, letter by letter, and *In the style of* uses the best one (on Clavero's: Inter, where Claude had guessed
  Montserrat).

## 0.4.5 - 2026-10-15 - Bulk: thumbnail sets, many videos in one Claude window, several videos edited at once

- **Thumbnail sets** - *Analyser > Add thumbnails*: paste a channel link (or some video links, or drop your own
  pictures) and MotionLab keeps only their thumbnails, titles and views - no video is downloaded - and measures them
  in seconds: colours, faces, where the text sits. It lists the whole channel (246 videos in 3.5 s) and starts with
  the newest or the most viewed 10-30; **More from the channel** on the set's page adds the next 10-100 whenever you
  want, never one twice. Sort the pictures by most / least viewed or newest / oldest; each one shows its views, how
  it did against the channel's followers, the date it came out and its length (*Update the views and dates* asks
  the channel again - nothing is downloaded; the exact dates take about a second a video). *Find the patterns with Claude* names what repeats - the text, the
  font's style, the colours, the structure - and you mark each one Correct / Partly / Wrong. Then a video's *Ready to
  post* makes thumbnails **in the style of** that set (its design, colours and font), and the thumbnail check
  compares yours with the set.
- **Many videos, one Claude window** - *Add videos* with Claude's check now opens ONE Claude window for the
  whole batch when the last video is measured (not one window per video), and says first how long Claude usually
  takes per video on your PC. If the window stops half way, the Analyser shows *Continue the batch*.
- **Edit several videos the same way** - *Editor > Edit several videos*: pick 2-10 of your videos and one
  style, then a quick draft of each (no Claude) or one Claude window that edits them one after another.
- **The roadmap** shows only the versions now (no panel at the bottom).
- **Fixed**: a video named with spaces or an apostrophe - Film it names it after the script, e.g. "What's new in
  MotionLab 0.4.3" - stopped with "not a video folder name" when you opened it; it opens normally now.
- **Fixed**: in some dialogs (Add thumbnails, Edit several videos) the option you picked was invisible - dark on dark.
  It now lights up in the section's colour.

## 0.4.4 - 2026-10-15 - What it took: Claude's time for every step, and a simpler Prepare

- **Prepare**: the two big ways for a script stay on top (*Improve my script*, *Write one from zero*). Below them a
  slim row, **Only need a title or thumbnail?** - pick a video that is ready and Claude writes its title, thumbnails
  and description (or answer a few questions for one that is not in MotionLab yet). Your list is split in two:
  **Talking scripts** (the first line, the length, Filmed / Edited and a **Film it** button, faded once the
  script is filmed and edited) and **Titles &
  thumbnails** (the best title and the thumbnail ideas) - you can tell them apart before you open one. Each card
  has **Rename** and **Delete** (to the Recycle Bin) when the pointer is on it.
- **Videos you generate stay in the Generator** - their page too. *Move to the Editor* when you want to edit one with
  your clips, captions or music; it then shows there instead (never in both). *Back to the Generator* undoes it.
- **Analyser**: *Add videos* comes first; *show the test videos* sits beside the filters; a video's page says where it
  stands (✓ Ready, or not checked by Claude yet) and the one next thing, instead of numbered steps.
- **Prompts** (shots, images, briefs) no longer show numbered steps - just the next thing to do.
- **Claude's memory**: the videos come newest first, each with the day it was analysed.
- **What it took** - a video's Overview now ends with how it was made, as a timeline: every Claude step (the script
  in Prepare, the edit, the title and thumbnails, Review and improve) with how long it took and the model
  ("1:54 min · Opus 5.5 · high"), the app's own jobs (quick drafts, thumbnails) beside them, and the total - "This
  52 s video took 40:24 min of Claude". The side index lists it under Ready to post. An analysed video's Overview
  shows the same for Claude's check, and Prepare's cards say how long Claude took to write each script or title set.
  MotionLab reads Claude Code's own logs on your PC: nothing is sent anywhere and it costs Claude nothing. Other
  things you asked in the same Claude window are listed apart, not counted.
- **Claude is working** - while a Claude window MotionLab opened is busy, one line in the sidebar (and on that video's
  page) says on what, for how long and what it is doing ("looking at contact sheets and frames"). It goes away when
  Claude has answered.

## 0.4.3.5 - 2026-10-15 - A simpler app: the Editor overhaul, Film it, a new player

- **Analyser and Generator** - the sidebar's Analyze is now called **Analyser**, and Generate is now **Generator**.
- **Every list says when, newest first** - the Analyser's videos look like the Editor's: a frame of the video with the
  day it was analysed, the name, the length, its rhythm in one line and the next step. Prepare's scripts, hooks and
  titles and the Generator's prompts show their date. The Generator's videos get the Editor's cards (they play while
  the pointer is on them).
- **Downloads waiting to be analysed** - no more long list on top: one small row says how many wait, and a click
  opens them (analyse one, all of them, or delete what you don't need). Your analysed videos come first.
- **A new video player** - click the picture to play or pause, and drag the bar under the video to any moment (it
  shows the frame and timecode as you move). Play and the frame steps sit in the middle, with the length, speed, repeat,
  sound and full screen. Keys: Space, the arrows (Shift = 10 frames), M for sound, F for full screen.
- **Prepare is simpler** - below the three ways, just your scripts, hooks and titles (the rules box is gone). A
  script's window has no steps any more: it lists the videos you made from it - Filmed, Edited, Posted - and opens
  one with a click. The script's card shows every step it reached.
- **Claude's memory**: *Your ratings → rules for every new video* stands out - Claude reads these first.
- The Generator's button says what it does: **Generate a video with Claude and other tools**.
- **Coming next - 0.4.4 What it took**: how long Claude worked and how many tokens each step of a video took (script,
  edit, title and thumbnails), and the total, on the video's page.
- **Film it: from a script to the edit in one place** - a script's card now has **Film it** (was *Record it*, which
  only opened New edit). It shows the script as cue cards, a full-screen **teleprompter** (Space to start, arrows for
  the speed), what to film besides you, and the facts to confirm first. You film it with your phone or camera, then
  drop the recording into the same window: it is copied into a new video named after the script (your original
  stays where it is). Then **Quick draft now** (the pauses cut, captions, punch-ins - a few minutes, no Claude) or
  **Make it with Claude**, who follows the script: the good takes, the text, B-roll and zooms where the script puts
  them. The card shows how far it is - Written, Filmed, Edited, Posted - and the video says which script it came from.
- **New edit is clearer**: *Which video?* instead of *Your clips*, an **Add clips…** button that copies files in (no
  more copying into a folder by hand), and *From a script or brief* instead of *From a saved prompt* - a talking
  script now gets the quick draft too.
- **Editor: smaller cards that show the video** - each card shows a frame of the newest render (it plays while the
  pointer is on it) with that render's date, the name and the length. Below: your clips (or Generate's icon for a
  video made from zero) and your rating - or *Not reviewed yet* when the newest render has no rating yet. The newest
  render comes first.
- **Edit is now called Editor** in the sidebar and everywhere the app mentions it.
- **Rename a video** - the pencil next to Delete (or *Rename* on its page). Only the name MotionLab shows changes;
  its folder keeps its name, so your clips, edits and Resolve still find everything.
- **A video opens on its newest render**; beside it an index of the page - title, thumbnails, description, after
  posting, review, graphics, versions, footage - each saying how far it is. Under the video, two big buttons:
  *Something not right? Review it and improve it* and *Start over*. Happy with it? **Ready to post** is right below
  (no separate Publish tab), with the title, the thumbnails and making one yourself in one highlighted box.
- **A Review tab**: the player with *How did it turn out?* beside it, then *Improve it with Claude*. **Footage**
  has its own tab; **Versions** lists every edit version with its renders. *Timing check* and *Resolve & library*
  only show on videos that have them, each with a line on what it is for.
- Folder buttons have a folder icon; on a video's page the button sits under the name. Delete buttons just say Delete.
- **Finished jobs no longer stay on the page** - a finished job shows for 5 seconds; a failed one stays until you
  close it with its ✕.
- **yt-dlp**: Settings asks for the newest release once a day and says "the newest version" when you have it -
  before, it judged by age alone and asked you to update a yt-dlp that was already up to date.

## 0.4.3 - 2026-10-15 - Title + thumbnail: Title & thumbnail first, the Publish tab, the thumbnail check

- **Prepare: Title & thumbnail first** - a third way, before you film: answer a few questions and Claude writes
  about ten titles in different styles, two or three thumbnail ideas (the words on them and the shot to film for
  each) and the first 3 seconds that keep the promise. A title card shows every title with its length on a phone,
  the ideas and the hook, each with a Copy button; *Use this title* links it to your video, and your script opens by
  keeping that promise.
- **Each video has a Publish tab**: the title, thumbnails A / B / C as the YouTube 16:9 thumbnail and the vertical
  cover for Shorts, Reels and TikTok (with what the apps' grids cut off and where their buttons cover your words),
  the description with chapters - YouTube's time with the frame and timecode next to it - and hashtags. Everything
  is checked before you post, with Copy buttons and the folder one click away.
- **Make the package with Claude, or yourself**: MotionLab finds the sharpest, best-lit moments of your clips (with a
  face when it sees one) - pick one, type 2-4 words, choose a design (outlined words over the photo, words on a
  colour block, a raw -> final split). Or bring a picture you made with an AI image tool. Change a thumbnail's words,
  colours or size and render it again.
- **The thumbnail check**: readable at phone-feed size, 2-4 words, big enough, enough contrast, a big enough face,
  the brightness of your niche's best videos, the title's length, no repeating the title, and the title's promise in
  the first 3 seconds - each with its number. Three variants for YouTube's own A/B test, made for its current limits.
- **Learning what gets clicks**: *How did it turn out?* now asks about the title and thumbnail; after posting, type
  each thumbnail's click-through rate and the link, and Claude repeats what won. References keep their thumbnail,
  and Claude's memory learns what the thumbnails of the videos that beat their channel look like.

## 0.4.2.1 - 2026-10-15 - Downloads that keep working, Report a problem

- **Your downloader stays up to date**: Settings shows how old the downloader (yt-dlp) is and updates it with one
  click - TikTok and Instagram change often, so an old one stops working. Settings also checks for Deno, which
  YouTube downloads now need, and shows the one line to install it.
- **Videos your PC can't play still play**: a video in a format Windows can't show here (TikTok's HEVC without the
  HEVC extension, AV1...) gets a small playable copy for the player. Frame numbers stay the same, and the analysis
  still reads the original.
- **Carousels and photo posts keep every file**: an Instagram carousel or a TikTok photo post now keeps all its
  files, shown together as one post.
- **Downloads that need you logged in** (new option, off by default): use your browser's login for downloads
  (Instagram, Vimeo, YouTube's "are you a bot" check). Firefox works best. It stays on this PC.
- **Report a problem**: in Settings and on every failed job. You see the whole report first, with your name and
  folders taken out; then GitHub opens it filled in and you press Submit yourself. MotionLab sends nothing.
- **Fix**: *Don't ask again* in the "which Claude, how hard" dialog is remembered (it was saved as "ask again").

## 0.4.2 - 2026-10-14 - Check before you render: notes on moments, the sound question, feel tests

- **Notes on exact moments**: under any render of your video, pause where something is off (or just right), pick
  the part (sound, colour, graphics...) and write it. Claude fixes exactly those moments; a click on a note jumps
  there.
- **Fix it, or start over**: *How did it turn out?* now asks what's next - **Fix this version** (the feel is right,
  details are wrong) or **Start over** (a different feel, with a new edit of the same clips). Claude never makes a
  second version of a feel you didn't want.
- **Sound effects - only you can hear them**: each analysed video now asks you "sound effects: none, some or many,
  and where?". It is red until you answer, goes to Claude with your feedback, and Claude's memory keeps it per video,
  so a rebuild gets the sound right.
- **Claude's memory shows your rules**: your ratings as rules for every new video (a part you rated bad once stays a
  rule), and the lessons on making videos next to the lessons on analysing them.
- **Checks before the final render**: before the long render with the polish, MotionLab looks at the plain one (or a
  graphic's quick stills) and points out frames where part of the picture disappears for a frame or two, moves too
  fast for the motion blur, and sound effects too loud, buried or squeezed - on one sheet, each frame with its number
  and timecode. Claude fixes those first, so the final render is needed once.
- **Starting from words only?** MotionLab finds the analysed videos closest to what you describe ("fast, glitchy,
  dark"), with the numbers that make them close, so you can start from a real reference instead of guessing.
- **Feel tests**: with only words and no reference, the quick draft makes 2-3 versions of your first 3 seconds in
  different feels (clean & slick, raw & glitchy, slow & cinematic...) from your own clips - side by side and on one
  sheet in a few seconds, without Claude. Pick one, or mix them ("B's pacing with A's colours").

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
