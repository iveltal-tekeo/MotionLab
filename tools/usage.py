"""What it took (0.4.4): Claude's minutes and tokens, read from Claude Code's own session logs on this PC (read-only).

    .venv\\Scripts\\python tools\\usage.py sessions [--all]     every session: when, minutes, tokens, what it was for
    .venv\\Scripts\\python tools\\usage.py project <name>       a video's steps + jobs, as its Overview shows them
    .venv\\Scripts\\python tools\\usage.py analysis <name>      the same for an analysis
    .venv\\Scripts\\python tools\\usage.py check                our sums against Claude Code's own cost notes (1 %)
    .venv\\Scripts\\python tools\\usage.py selfcheck            known answers on tools\\dev\\usage_samples (no real logs)

The logs: %USERPROFILE%\\.claude\\projects\\<lab>\\*.jsonl (motionlab\\usage.py explains what counts). Nothing is written
anywhere and nothing is sent to Claude Code. Lab jobs (quick drafts, renders by the app) come from
.app\\jobs\\history.jsonl, recorded since 0.4.4.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import usage as U  # noqa: E402
from motionlab.util import setup_console  # noqa: E402


def _when(t) -> str:
    return datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M") if t else "?"


def _tok(n: int) -> str:
    return f"{n / 1e6:.1f} M" if n >= 1e6 else f"{n / 1e3:.0f} k" if n >= 1e3 else str(n)


def show(d: dict) -> None:
    for r in d["rows"]:
        tail = f"{_tok(r['total'])} tokens · {r['model'] or '?'} · {r['effort'] or '?'}" if r["kind"] == "claude" \
            else "a lab job, no tokens"
        print(f"{_when(r['t0'])}  {r['minutes']:6.1f} min  {r['step']}{' - ' + r['what'] if r.get('what') else ''}  ({tail})")
    T = d["total"]
    print(f"TOTAL  {T['claude_minutes']:.1f} min of Claude in {T['windows']} window(s) + {T['job_minutes']:.1f} min of "
          f"lab jobs · {_tok(T['tokens'])} tokens")
    if d["other"]["rounds"]:
        print(f"not counted: {d['other']['rounds']} other round(s) in the same windows, {d['other']['minutes']:.1f} min")


def main() -> int:
    setup_console()
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if a[0] == "selfcheck":
        return 0 if U.selfcheck()["passed"] else 1
    S = U.sessions()
    if a[0] == "sessions":
        for s in S:
            rs = [r for r in s["rounds"] if not r.get("clear")]
            mins = sum(r["minutes"] for r in rs)
            tok = sum(U.round_info(s, r)["total"] for r in rs)
            used = sorted({r["task"] for r in rs if r.get("task")})
            if not used and "--all" not in a:
                continue
            print(f"{_when(s['t0'])}  {s['id'][:8]}  {mins:6.1f} min  {_tok(tok):>8}  {len(rs):>3} rounds  "
                  f"{','.join(used) or '-':<16} {s['title'] or '(started by hand)'}")
        return 0
    if a[0] == "check":
        bad = 0
        for c in U.check(S):
            bad += not c["ok"]
            print(f"{'OK  ' if c['ok'] else 'DIFF'}  {c['session'][:8]}  cache read {c['mine']['cache_read']} vs "
                  f"{c['theirs']['cache_read']}, output {c['mine']['output']} vs {c['theirs']['output']}  {c['dev']} %"
                  f"  {c['title'] or ''}")
        return 1 if bad else 0
    if a[0] in ("project", "analysis") and len(a) > 1:
        from motionlab.app import data
        show(data.took(a[0], a[1]))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
