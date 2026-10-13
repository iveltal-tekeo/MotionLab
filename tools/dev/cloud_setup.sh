#!/bin/bash
# MotionLab in a Claude Code cloud session (Ubuntu, Linux) - docs/cloud.md explains it.
#
# Two ways it runs, both safe to repeat (it only does what is missing):
#   1. pasted into the cloud environment's "Setup script" box on claude.ai: runs before Claude starts and the result
#      is cached with the environment (ffmpeg + uv's download cache), so sessions start fast;
#   2. by the SessionStart hook in .claude/settings.json (cloud sessions only): makes .venv in the checkout.
#
# What it sets up:
#   - ffmpeg 9.0.x (the version GitHub's tests use; Ubuntu's 6.1 cannot build the self-test videos) in /opt/ffmpeg-9,
#     linked into /usr/local/bin so it comes before /usr/bin on PATH
#   - .venv = Python 3.12 + requirements.txt, plus .venv/Scripts/python(.exe) -> bin/python so .mcp.json and the
#     Windows-style commands in the docs (.venv\Scripts\python tools\...) work unchanged
# Never touches refs\, analysis\, projects\ (they are not in the repo, so a cloud checkout has no videos).
set -uo pipefail

FF_DIR=/opt/ffmpeg-9
FF_URL=https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-n9.0-latest-linux64-gpl-9.0.tar.xz

say() { echo "[motionlab setup] $*" >&2; }

# ---- ffmpeg 9 ---------------------------------------------------------------------------------------------------
if [ ! -x "$FF_DIR/bin/ffmpeg" ]; then
  say "downloading ffmpeg 9.0 (static build, about 150 MB) ..."
  tmp=$(mktemp -d)
  if curl -sSfL --retry 3 -o "$tmp/ff.tar.xz" "$FF_URL" && tar -xJf "$tmp/ff.tar.xz" -C "$tmp"; then
    src=$(dirname "$(ls "$tmp"/*/bin/ffmpeg)")
    mkdir -p "$FF_DIR/bin" && cp "$src/ffmpeg" "$src/ffprobe" "$FF_DIR/bin/"
  else
    say "ffmpeg download failed - the self-test needs it; run this script again later"
  fi
  rm -rf "$tmp"
fi
if [ -x "$FF_DIR/bin/ffmpeg" ]; then
  ln -sf "$FF_DIR/bin/ffmpeg" /usr/local/bin/ffmpeg 2>/dev/null || true
  ln -sf "$FF_DIR/bin/ffprobe" /usr/local/bin/ffprobe 2>/dev/null || true
fi

# ---- the checkout (the hook passes it; as a setup script it may not be cloned yet) --------------------------------
LAB="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$LAB" ]; then
  for d in "$PWD" /home/user/*; do
    [ -f "$d/requirements.txt" ] && [ -d "$d/tools/motionlab" ] && { LAB=$d; break; }
  done
fi
if [ -z "$LAB" ]; then
  say "no MotionLab checkout yet: ffmpeg only (the session's hook makes .venv)"
  exit 0
fi

# ---- .venv (Python 3.12 + requirements.txt), redone only when requirements.txt changes -----------------------------
cd "$LAB" || exit 0
stamp=.venv/.requirements.sha256
want=$(sha256sum requirements.txt | cut -d' ' -f1)
if [ ! -x .venv/bin/python ] || [ "$(cat "$stamp" 2>/dev/null)" != "$want" ]; then
  say "installing the Python packages into .venv ..."
  if command -v uv >/dev/null; then
    uv venv -q --allow-existing -p 3.12 .venv && VIRTUAL_ENV="$LAB/.venv" uv pip install -q -r requirements.txt
  else
    python3.12 -m venv .venv && .venv/bin/python -m pip install -q --disable-pip-version-check -r requirements.txt
  fi && echo "$want" > "$stamp" || say "installing the Python packages failed"
fi
if [ -x .venv/bin/python ]; then
  mkdir -p .venv/Scripts
  ln -sf ../bin/python .venv/Scripts/python
  ln -sf ../bin/python .venv/Scripts/python.exe
fi

# ---- one line for Claude (a SessionStart hook's output is added to the session) -----------------------------------
py=$(.venv/bin/python -c 'import platform; print(platform.python_version())' 2>/dev/null || echo "missing")
ff=$(ffmpeg -version 2>/dev/null | head -1 | awk '{print $3}')
echo "MotionLab cloud session: Linux checkout, no videos (refs/analysis/projects are not in git). Python $py in .venv," \
     "ffmpeg ${ff:-missing}. Run tools as .venv/bin/python tools/<tool>.py; selftest.py --extended and" \
     "tools/dev/smoke.py work here, the Windows app window, DaVinci Resolve, setup.bat and winget do not."
exit 0
