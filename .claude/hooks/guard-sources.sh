#!/usr/bin/env bash
# Hard rule 1 (never change a source): runs .claude/hooks/guard_sources.py with whatever Python this PC has - the
# lab's own venv on Windows or Linux, else python3 - and passes the hook's JSON through. No Python = allowed (exit 0):
# the deny rules in .claude/settings.json and the tools' SHA-256 checks still hold.
d="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
g="$d/.claude/hooks/guard_sources.py"
for p in "$d/.venv/Scripts/python.exe" "$d/.venv/bin/python"; do
  if [ -x "$p" ]; then exec "$p" "$g"; fi
done
if command -v python3 >/dev/null 2>&1; then exec python3 "$g"; fi
exit 0
