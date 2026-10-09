<p align="center"><img src="tools/motionlab/app/ui/icon-192.png" width="96" alt="MotionLab"></p>

# MotionLab

**A local lab that takes apart the editing of any video - every cut, flash, zoom, speed ramp, split screen, text
pop and transition, frame-accurately - so you can learn its style and pacing and rebuild it with your own footage.**

> **Status: v0.3.0 - rebuild toolkit** ([what's new](CHANGELOG.md)): colour rebuilds, 3x faster renders, graphics
> written as HTML, Claude Code connected to the lab and to DaVinci Resolve, and an *Update available* button.
> Detection was tuned on music videos; other categories work and get better with every verdict you give.

## Contents

- [What it is](#what-it-is)
- [What it does](#what-it-does)
- [Install (Windows 10 / 11)](#install-windows-10--11)
- [First steps](#first-steps)
- [Rebuilding a video with your footage](#rebuilding-a-video-with-your-footage)
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
- **Share it**: *Knowledge > Share my knowledge* - your reference cards and new rules go to GitHub; your friends' come
  back with the next update. The *Knowledge* page compares pacing and effects per category across everybody.
- **Rebuild it** with your own clips, in colour, as a lab render or as an editable DaVinci Resolve project.
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
5. **Knowledge > Share my knowledge.**

The References page shows these steps and where each video stands. Every frame number comes with its timecode
(`f480 (00:00:16:00)`), so you can check anything in your editor. New to Claude Code? Read
[docs/claude_tips.md](docs/claude_tips.md) (also in the app: *Tips for working with Claude*): one chat per task,
which effort level, how to use fewer tokens.

## Rebuilding a video with your footage

Put your clips in `projects\<name>\` and click *Recreate with my footage* on a reference (or ask Claude Code for
`/recreate-video <reference> <project>`). Claude maps every shot of the reference to your clips and writes the edit;
the lab renders it frame-accurately.

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
- Lessons from others wait in `knowledge\incoming\` until someone reviews them (*Knowledge > Review them in Claude
  Code*), so one wrong rule cannot silently change everybody's analyser.
- Only text and numbers about videos are shared - never videos, frames or file paths. Why no cloud database:
  [docs/knowledge_sharing.md](docs/knowledge_sharing.md).

## Folders

| Folder | What | In the repo? |
|---|---|---|
| `tools\` | the pipeline, the app (`tools\motionlab\app\`), the Resolve builder, MotionLab's MCP server, HTML overlays (`tools\overlays\`: HyperFrames, versions pinned; its `node_modules` stays on your PC) | yes |
| `.claude\skills\` | the Claude Code skills (`analyze-reference` + the shared `lessons.md`, `recreate-video`) | yes |
| `knowledge\` | shared reference cards and lessons waiting for review (`local\`, `inbox\`, `outbox\` are private) | partly |
| `docs\` | roadmap, plans, ideas, guides, design notes | yes |
| `refs\` | reference videos (read-only for the lab) | no - yours |
| `analysis\` | one folder per analysed video: report, events, sheets, previews, your verdicts | no - yours |
| `projects\` | your own videos and everything made for them (the app's *Videos* page) | no - yours |
| `library\` | saved effects (recipes + Fusion macros) | no - yours |
| `settings.json`, `.app\`, `.venv\` | your settings, app cache, Python packages | no |

## What comes next

- [docs/plans.md](docs/plans.md) - the planned versions (0.4 content intelligence: videos as information, 0.5
  templates by feel + macOS, 0.7 AI B-roll and cinematics), also shown in the app's *What's new*.
- [docs/ideas.md](docs/ideas.md) - tools and features to consider later, each tested on a normal PC first.

## License

MIT - see [LICENSE](LICENSE).
