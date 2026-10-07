# Changelog

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

## 0.1.0 - 2026-10-05/06

- Analysis pipeline (`tools\analyze.py`): frame-accurate cuts and effects, audio beats and drops, contact sheets,
  previews, report, self-tests.
- Rebuild a reference's style with your footage: lab renderer (option 1) and a native DaVinci Resolve Studio project
  (option 2) with drift check.
- MotionLab app v0.1: local window, references with verdicts, projects, library picks, jobs, storage.
