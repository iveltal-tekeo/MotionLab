# Changelog

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
