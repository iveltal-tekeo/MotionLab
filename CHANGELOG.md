# Changelog

What changed in each version of MotionLab, newest first. When a new version is on GitHub, MotionLab shows an
**Update available** button in the sidebar; it opens the sections below that are newer than your copy.
Version numbers: `0.x.0` adds features, `0.x.y` fixes things.

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
