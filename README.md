<p align="center"><img src="tools/motionlab/app/ui/icon-192.png" width="96" alt="MotionLab"></p>

# MotionLab

[![tests](https://github.com/iveltal-tekeo/MotionLab/actions/workflows/tests.yml/badge.svg)](https://github.com/iveltal-tekeo/MotionLab/actions/workflows/tests.yml)

**A local lab that takes apart the editing of any video - every cut, flash, zoom, speed ramp, split screen, text
pop and transition, frame-accurately - so you can learn its style and pacing and rebuild it with your own footage.**

> **Status: v0.5.0 - Motion Graphics** ([what's new](CHANGELOG.md)): **Analyse** videos you like (several at once,
> by focus: content creation, cinematic or both - colour grading included), **Prepare** a script, a title and a
> thumbnail, **Edit** your clips like up to three of them or the way you say (a quick draft in minutes, then Claude
> makes it great), **Generate** a video from zero (a motion-graphics video, or every prompt for AI video tools),
> **Motion Graphics** - 74 ready-made animated graphics (titles, lower thirds, transitions, charts, call-outs, end
> screens...) you change live and put in any video - and **Claude's memory**: everything it learned, in one place,
> used when it edits or generates for you. Since 0.3: colour rebuilds, 3x faster renders,
> graphics written as HTML, Claude Code connected to the lab and to DaVinci Resolve, updates that only offer versions
> GitHub's automatic tests passed.
> Detection was tuned on music videos; other categories work and get better with every verdict you give.

## Contents

- [What it is](#what-it-is)
- [What it does](#what-it-does)
- [Install (Windows 10 / 11)](#install-windows-10--11)
- [First steps](#first-steps)
- [Editing your footage like a video you liked](#editing-your-footage-like-a-video-you-liked)
- [Claude Code in MotionLab](#claude-code-in-motionlab)
- [Updates](#updates)
- [Sharing knowledge - how it works](#sharing-knowledge---how-it-works)
- [Folders](#folders)
- [What comes next](#what-comes-next)
- [License](#license)

## What it is

Give it a reference - a music video, an Instagram reel, a cooking short, a tutorial, an ad, a motion-graphics piece,
a documentary. MotionLab measures every frame, finds the edits and effects, and shows them in a window where you scrub
frame by frame and read how each effect was made and how to rebuild it.
[Claude Code](https://claude.com/claude-code) looks at every effect and names it properly; you mark each one
Correct / Partly / Wrong, and the lab turns your corrections into rules.

**Built for a group of friends:** everyone runs MotionLab on their own PC with their own Claude plan and footage,
and what each install learns - reference cards with pacing and effects, and the rules from your feedback - is shared
through this GitHub repo. Analyse 10 videos each and everyone's MotionLab knows all 30.

![roadmap](docs/roadmap.png)

*The roadmap moves in the app (Home). Its data is [docs/roadmap/roadmap.json](docs/roadmap/roadmap.json): the big
badges are the major versions (x.y.0), the smaller versions hang below them.*

## What it does

- **Download** a reference from a link (YouTube, Vimeo, TikTok, Instagram ... via yt-dlp: MP4 up to 1080p, best
  quality, or MP3) - or drop a video into `refs\`. Only download and analyse videos you are allowed to use.
- **Categorise** it: music video, ad, motion graphics, documentary, vlog, tutorial, cooking, podcast, gaming, sports,
  travel, fashion, comedy, trailer, fan edit, other - plus your own tags. The format (vertical / horizontal, length)
  is measured.
- **Analyse** it: cuts and 30+ effect types with exact frame ranges (frame number + timecode on everything), beats
  and drops, **pacing** (cuts per minute, shot lengths, cuts in the first 3 seconds, cuts on the beat), contact sheets
  and previews per effect, "possible misses".
- **Review** with Claude Code: what happens, timing and easing, camera or post, and how to rebuild it.
- **Teach it**: your verdicts in the app's review tab (and your answers on the "possible misses") -> Claude turns
  them into rules, checked by a self-test.
- **Share it**: *Claude's memory > Share my knowledge* - your reference cards and new rules go to GitHub; your friends' come
  back with the next update. The *Knowledge* page compares pacing and effects per category across everybody.
- **Rebuild it** with your own clips, in colour, as a lab render or as an editable DaVinci Resolve project.
- **Motion Graphics**: 74 animated graphics - 57 learned from pro template clips, 17 for what template sites offer
  most - each with a live preview: type your words, pick colours and one of 28 shipped fonts, see it at once, then put
  it in a video at any size (vertical, horizontal, square), with its sound effects. The Generator builds whole videos
  from them.
- **Prompts**: keep the prompts that worked for you (Seedance / Higgsfield / Kling shots, hooks, talking scripts) or
  a creator's public one with its link; Claude splits each into its structure and writes new ones for your need in
  a structure that already worked. You paste them into the site and rate what they made.
- **Tidy up**: *Delete* on references, downloads, your videos and renders moves them to the Windows Recycle Bin.

MotionLab never modifies a source video: it only reads it and checks its SHA-256 before and after every analysis.

## Install (Windows 10 / 11)

**Recommended - with git** (needed for updates and sharing):

1. Install Git once: `winget install Git.Git` (or https://git-scm.com).
2. In a terminal: `git clone https://github.com/iveltal-tekeo/MotionLab.git C:\MotionLab`
   (a private repo asks you to log in to GitHub in the browser once).
3. Double-click **`C:\MotionLab\setup.bat`**: Python packages, a check of the programs below (it offers to install
   missing ones and asks first), HyperFrames if you want it, your name for sharing, a Desktop shortcut.
4. Start **MotionLab** from the shortcut (or `MotionLab.bat`). *Settings > Programs* shows what it found.

Downloaded the ZIP instead? Run `setup.bat` the same way; then *Settings > Sharing & updates > Connect to GitHub*
turns on updates and sharing.

| Program | Needed for | Get it |
|---|---|---|
| Python 3.12 (64-bit) | everything | `winget install Python.Python.3.12` or python.org (tick "Add to PATH") |
| ffmpeg | every analysis | `winget install Gyan.FFmpeg` |
| Microsoft Visual C++ Redistributable (x64) | the audio step of every analysis (beats, drops) - many PCs have it already, `setup.bat` checks | `winget install --id Microsoft.VCRedist.2015+.x64 -e` (as administrator) or https://aka.ms/vs/17/release/vc_redist.x64.exe |
| Git | updates + sharing knowledge | `winget install Git.Git` |
| Claude Code | reviews, learning from feedback, rebuilds | https://claude.com/claude-code (your own Claude plan) |
| yt-dlp | *Download from a link* (optional) | `winget install yt-dlp.yt-dlp`, or any `yt-dlp.exe` + its path in Settings |
| Node.js 22+ | graphics written as HTML ([HyperFrames](https://github.com/heygen-com/hyperframes)) when rebuilding (optional) | `winget install OpenJS.NodeJS.LTS`, then `setup.bat` or *Settings > Programs > Install* |
| DaVinci Resolve Studio | rebuilding as a Resolve project, Claude looking into Resolve (optional) | blackmagicdesign.com (Studio is paid; needed for scripting) |

Microsoft Edge (the app window) comes with Windows.

## First steps

1. **References > Download from a link** -> paste a link -> *Download* -> **Analyse it**.
2. Pick the **category** (and tags, e.g. `instagram, recipe`) and click **Analyse with Claude**: the lab measures the
   video (about 1-2 minutes per minute of video), then Claude Code opens by itself and checks every effect.
3. Open the reference: **Review effects** - Correct / Partly / Wrong (keys 1 2 3) and a note where needed - then the
   red **Possible misses** tab.
4. **Send feedback to Claude**: a new Claude Code window turns your verdicts into lessons.
5. **Claude's memory > Share my knowledge.**

The Analyser page shows these steps and where each video stands. Every frame number comes with its timecode
(`f480 (00:00:16:00)`), so you can check anything in your editor. New to Claude Code? Read
[docs/claude_tips.md](docs/claude_tips.md) (also in the app: *Tips for working with Claude*): one chat per task,
which effort level, how to use fewer tokens.

## Editing your footage like a video you liked

Put your clips (and a song, if you have one) in `projects\<name>\` and click *Editor > New edit*. Pick how:

- **Like videos you analysed** - up to three: Claude mixes their rhythm, hook, effects and captions with your music
  and length (*by feel*), or copies one of them exactly - same song, same cuts and effects, frame by frame (1:1).
- **With your words** - a ready-made style (fast & hooky, 3-second cuts, talking + captions, slow & cinematic,
  transition-driven, music montage) and / or what you want in your own words.
- **From a saved prompt** - a brief, a talking script or a hook.

*Quick draft now* makes a first version by rules in a few minutes - cuts on the beat, the best moments of your
clips, the style's effects; for a talking video the pauses are cut out (`tools\draft_edit.py`). *Make it with
Claude* plans the whole edit with you (`/recreate-video`), and the lab renders it frame-accurately.

- **In colour**, with each clip's own colour settings and grades you can tune (saturation included); black-and-white
  edits stay grey.
- **Fast**: renders run in several processes at once (a 2.5-minute edit in under 2 minutes).
- **Graphics written as HTML** - titles, counters, shapes, glows, particles - rendered by
  [HyperFrames](https://github.com/heygen-com/hyperframes) into transparent clips (`tools\overlay.py`). The same clip
  works in the lab render and in DaVinci Resolve (a plain clip, no Fusion). Examples: `tools\overlays\examples\`
  (one of them is a 10-second clip about 0.3.0).
- **In DaVinci Resolve Studio** (optional): the same edit as a native, editable project - clips, LUTs, Fusion where
  needed - with a check-up of what you changed by hand.

## Claude Code in MotionLab

- The app's **Claude buttons** open Claude Code in the lab folder with the exact request and a fitting effort level.
- **MotionLab's own MCP server** (`.mcp.json`) gives Claude compact views of the lab - every effect with frame +
  timecode, contact sheets and any frames as pictures, your verdicts, your videos - so it doesn't read big files.
  Claude Code asks once to allow it (`setup.bat` does that for you).
- **Claude + DaVinci Resolve** (optional): *Settings > Claude Code > Connect Claude Code to DaVinci Resolve* sets up
  the community MCP server [davinci-resolve-mcp](https://github.com/samuelgursky/davinci-resolve-mcp) on your PC
  (a fixed version, its safe mode on), so in a chat Claude can read your open project. It asks before changing
  anything there.

## Updates

When a new version is on GitHub, a bright **Update available** button appears in the sidebar. It shows what changed
(every version since yours), one click installs it and restarts MotionLab, and afterwards *What's new* shows what
came in. Friends' shared knowledge arrives the same way (*New from friends*, no restart). The sidebar's
**What's new** button shows the whole history ([CHANGELOG.md](CHANGELOG.md)) and the planned versions any time.
*Settings > Sharing & updates* can install updates at start-up instead, or turn checking off.
Every change is tested on GitHub first (the self-tests and the app, on a clean Windows machine - the badge at the
top): the button only offers versions that passed, so a broken change never reaches you.
An update never touches your videos, analyses, verdicts, settings or knowledge. Problems: errors go to
`.app\server.log`.

## Sharing knowledge - how it works

| What | Where | Shared? |
|---|---|---|
| Your videos, analyses, frames, contact sheets | `refs\`, `analysis\`, `projects\` | **never** |
| A **reference card** per analysed video: category, format, link, pacing, every reviewed effect + your verdict and note | `knowledge\references\` | yes |
| New **lessons** from your feedback (they work on your PC right away) | `knowledge\local\lessons.md` -> `knowledge\incoming\` | yes, reviewed first |
| Reviewed rules every MotionLab applies | `.claude\skills\analyze-reference\lessons.md` | yes |

- *Share my knowledge* commits your new cards and lessons and pushes them. Git asks you to log in to GitHub the first
  time (in the browser).
- To push, a friend needs write access: on GitHub, *Settings > Collaborators > Add people*. Friends without access
  get a pack file (`knowledge\outbox\*.mlpack.json`) to send to you; you drop it in `knowledge\inbox\` and *Import*.
- Lessons from others wait in `knowledge\incoming\` until someone reviews them (*Claude's memory > Review them in Claude
  Code*), so one wrong rule cannot silently change everybody's analyser.
- Only text and numbers about videos are shared - never videos, frames or file paths. Why no cloud database:
  [docs/knowledge_sharing.md](docs/knowledge_sharing.md).

## Folders

| Folder | What | In the repo? |
|---|---|---|
| `tools\` | the pipeline, the app (`tools\motionlab\app\`), the Resolve builder, MotionLab's MCP server, HTML overlays (`tools\overlays\`: HyperFrames, versions pinned; its `node_modules` stays on your PC) | yes |
| `.claude\skills\` | the Claude Code skills (`analyze-reference` + the shared `lessons.md`, `recreate-video`, `generate-video`, `write-prompt`, `whats-next`) | yes |
| `knowledge\` | shared reference cards and lessons waiting for review (`local\`, `inbox\`, `outbox\` are private) | partly |
| `docs\` | roadmap, plans, ideas, guides, design notes | yes |
| `refs\` | reference videos (read-only for the lab) | no - yours |
| `analysis\` | one folder per analysed video: report, events, sheets, previews, your verdicts | no - yours |
| `projects\` | your own videos and everything made for them (the app's *Videos* page) | no - yours |
| `library\` | saved effects (recipes + Fusion macros) | no - yours |
| `settings.json`, `.app\`, `.venv\` | your settings, app cache, Python packages | no |

## What comes next

- [docs/plans.md](docs/plans.md) - the planned versions (0.5.1 yapping mode for talking-to-camera videos and the
  clips a script needs, 0.5.2 faster videos: a minute of video in ~10 minutes of Claude, 0.5.3 prompt generator for
  every model, 0.5.4 motion graphics from template packs - Resolve / After Effects packs read exactly, a motion check,
  formats, a preview before the render, 0.5.5 colour: correct your own clips, adjustable grades in Resolve, 0.5.6
  content generation: AI clips back into the lab, voice and music, 0.6 describe video: what videos and courses say and
  show, 0.6.5 templates by feel: the story, 0.7 AI B-roll and cinematics, 0.7.5 macOS), also shown in the app's
  *What's new*.
- [docs/ideas.md](docs/ideas.md) - tools and features to consider later, each tested on a normal PC first.

## License

MIT - see [LICENSE](LICENSE).
