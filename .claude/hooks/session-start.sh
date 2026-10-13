#!/bin/bash
# Cloud sessions only (Claude Code on the web): ffmpeg 9 + .venv for MotionLab - see tools/dev/cloud_setup.sh.
# On your own PC this does nothing.
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
export CLAUDE_PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
exec bash "$CLAUDE_PROJECT_DIR/tools/dev/cloud_setup.sh"
