"""Re-merge review.json into events.json and re-render report.html (no recomputation).

    .venv\\Scripts\\python tools\\report.py <analysis name or folder>
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import knowledge  # noqa: E402
from motionlab.assemble import rerender  # noqa: E402
from motionlab.util import ANALYSIS, setup_console  # noqa: E402


def main() -> int:
    setup_console()
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    arg = Path(sys.argv[1])
    out = arg if arg.is_dir() else ANALYSIS / sys.argv[1]
    if not (out / "events.json").exists():
        print(f"ERROR: no events.json in {out}")
        return 2
    m = knowledge.meta(out.name)                            # the category / tags from meta.json win
    data = rerender(out)
    if m.get("category") and data.get("category") != m["category"]:
        import json
        data["category"] = data["style"] = m["category"]
        data["tags"] = m.get("tags", [])
        (out / "events.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
        data = rerender(out)
    if knowledge.build_local_cards([out.name]):
        print(f"reference card updated: knowledge/local/references/ ({out.name})")
    n_rev = sum(1 for e in data["events"] if e.get("review"))
    print(f"report updated: {out / 'report.html'}  ({n_rev}/{len(data['events'])} events reviewed)")
    if data.get("review_unmatched"):
        print(f"WARNING: review entries that match no event: {data['review_unmatched']}")
    missing = [e["id"] for e in data["events"] if not e.get("review")]
    if missing:
        print(f"not reviewed yet: {', '.join(missing)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
