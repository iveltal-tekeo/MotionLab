# MotionLab in Claude Code on the web (cloud sessions)

A cloud session (claude.ai/code, the Claude app's Code tab, `claude --cloud`) is a fresh Linux machine with a clone
of the repo. It is for working on MotionLab's **code**: fixing bugs, the app's pages, the workflow, docs. It has no
videos (refs\, analysis\, projects\, library\ and knowledge\local\ never go to GitHub), no Windows app window, no
DaVinci Resolve and no winget, so analysing your references and rebuilding videos stay on your PC.

What works there: every tool with `.venv/bin/python tools/<tool>.py`, `selftest.py --extended` (it makes its own test
videos), `tools/dev/smoke.py` (the app server + every page in headless Chromium), a test server
(`app.py --no-window --stay --no-update --port 8797`).

## One-time setup (2 minutes)

1. **Nothing to do for it to work**: the repo's `.claude/settings.json` runs `.claude/hooks/session-start.sh` when a
   cloud session starts. It calls `tools/dev/cloud_setup.sh`, which installs ffmpeg 9 (the version GitHub's tests
   use) and makes `.venv` (Python 3.12 + requirements.txt), then tells Claude in one line what the session has.
   It does nothing on your own PC. First start of a session: about 30 seconds.
2. **Faster starts (optional)**: on claude.ai/code open the cloud environment menu (the environment name in the
   session's title bar) > **Edit** > **Setup script**, and paste the whole content of `tools/dev/cloud_setup.sh`.
   It then runs once before Claude starts and is cached with the environment for about 7 days, so ffmpeg is already
   there in every new session (and the Python packages too when the repo was already cloned at that point); the hook
   then only makes `.venv`.
3. **Network access**: the default **Trusted** level is enough (github.com for ffmpeg, pypi.org for the packages).

## Working in a cloud session

- Start it on the repo `iveltal-tekeo/motionlab`; Claude works on a `claude/...` branch and pushes there. Merge it
  into main yourself (a pull request on GitHub) when you are happy; the app's Update button on your PC installs only
  what GitHub's tests passed (docs\organization.md "Tests on GitHub").
- The MotionLab MCP server (`.mcp.json`) has no lab data to show in the cloud; if it says "failed to connect" at the
  very first start, that is only because `.venv` did not exist yet - it is harmless.
- Rules that still hold: never commit videos, frames or anything from refs\ / analysis\ / projects\; the self-test
  must PASS after any change to `tools\motionlab\` or `config.json`.

## If the setup fails

The hook prints `[motionlab setup] ...` lines: "ffmpeg download failed" (network - run
`bash tools/dev/cloud_setup.sh` again in the session) or "installing the Python packages failed" (a package without
a Linux wheel for Python 3.12 - check requirements.txt). A failing Setup script stops new sessions from starting:
fix it in the environment's settings, or clear the box.
