"""Parse feedback pasted from a report ("Generate feedback" button) and map it onto the current analysis.

    .venv\\Scripts\\python tools\\feedback.py <analysis name or folder> <feedback.txt>
    .venv\\Scripts\\python tools\\feedback.py <analysis name or folder> -        (read from stdin)

Archives the raw text + a parsed JSON in analysis\\<name>\\feedback\\ and prints, for every verdict, the event as it
stands now (type, frames, sheets) so each WRONG / PARTLY item can be re-checked. Frame numbers and timecodes
mentioned in notes are converted to frames.
"""
from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab.timecode import frame_to_tc, tc_to_frame  # noqa: E402
from motionlab.util import ANALYSIS, read_json, setup_console, write_json  # noqa: E402

LINE = re.compile(r"^(CORRECT|PARTLY|WRONG|NOTE)\s*\|\s*(E\d+|C\d+)\s*\|\s*([^|]+?)\s*\|\s*f(\d+)(?:-(\d+))?[^|]*"
                  r"(?:\|\s*note:\s*(.*))?$", re.IGNORECASE)
# "--- possible misses ---" (app 0.2.5): the user's answer per near-miss frame
MISS = re.compile(r"^(EFFECT|NOT AN EFFECT|NOTE)\s*\|\s*f(\d+)[^|]*(?:\|\s*note:\s*(.*))?$", re.IGNORECASE)


def frames_in_text(text: str, fps: float) -> list[int]:
    """Frame references in free text: f123, frame 123, 00:01:02:03 (timecode), 1:23 / 01:23.5 (min:sec)."""
    out = set()
    for m in re.finditer(r"\b(?:f|frame\s*)(\d{1,6})\b", text, re.IGNORECASE):
        out.add(int(m.group(1)))
    for m in re.finditer(r"\b(\d{1,2}):(\d{2}):(\d{2})[:;.](\d{2})\b", text):
        try:
            out.add(tc_to_frame(m.group(0), fps))
        except ValueError:
            pass
    for m in re.finditer(r"(?<![\d:])(\d{1,2}):(\d{2}(?:\.\d+)?)(?![\d:])", text):
        out.add(int(round((int(m.group(1)) * 60 + float(m.group(2))) * fps)))
    return sorted(out)


def parse(text: str) -> dict:
    res = {"video": None, "analysis_id": None, "events": [], "cuts": [], "misses": [], "missed": "", "unparsed": []}
    section = None
    missed = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line == "END":
            continue
        if line.startswith("video:"):
            m = re.search(r"video:\s*([^|]+)", line)
            res["video"] = m.group(1).strip() if m else None
            m = re.search(r"analysis:\s*([^|]+)", line)
            res["analysis_id"] = m.group(1).strip() if m else None
            continue
        if line.startswith("--- events"):
            section = "events"
            continue
        if line.startswith("--- hard cuts"):
            section = "cuts"
            continue
        if line.startswith("--- missed"):
            section = "missed"
            continue
        if line.startswith("--- possible misses"):
            section = "misses"
            continue
        if line.startswith(("MOTIONLAB FEEDBACK", "report:", "(no verdict", "(all hard cuts", "(none checked")):
            continue
        if section == "missed":
            if line != "(none)":
                missed.append(line)
            continue
        if section == "misses":
            m = MISS.match(line)
            if m:
                res["misses"].append({"verdict": m.group(1).upper(), "frame": int(m.group(2)),
                                      "note": (m.group(3) or "").strip()})
            else:
                res["unparsed"].append(line)
            continue
        m = LINE.match(line)
        if m:
            item = {"verdict": m.group(1).upper(), "id": m.group(2).upper(), "type": m.group(3).strip(),
                    "start": int(m.group(4)), "end": int(m.group(5) or m.group(4)),
                    "note": (m.group(6) or "").strip()}
            (res["cuts"] if item["id"].startswith("C") else res["events"]).append(item)
        else:
            res["unparsed"].append(line)
    res["missed"] = "\n".join(missed)
    return res


def overlap(a0, a1, b0, b1) -> int:
    return max(0, min(a1, b1) - max(a0, b0) + 1)


def main() -> int:
    setup_console()
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    arg = Path(sys.argv[1])
    out = arg if arg.is_dir() else ANALYSIS / sys.argv[1]
    data = read_json(out / "events.json")
    text = sys.stdin.read() if sys.argv[2] == "-" else Path(sys.argv[2]).read_text(encoding="utf-8")
    fb = parse(text)
    fps = data["video"]["fps"]
    n_frames = int(data["video"].get("frames") or 10 ** 9)
    events = {e["id"]: e for e in data["events"]}
    cuts = {c["id"]: c for c in data["hard_cuts"]}

    for item in fb["events"]:
        ev = events.get(item["id"])
        if not ev or overlap(ev["start"], ev["end"], item["start"], item["end"]) == 0:
            # analysis was re-run and IDs moved: find the event by frame overlap
            best = max(data["events"], key=lambda e: overlap(e["start"], e["end"], item["start"], item["end"]),
                       default=None)
            ev = best if best and overlap(best["start"], best["end"], item["start"], item["end"]) else None
        item["current_id"] = ev["id"] if ev else None
        if ev:
            item["current"] = {"type": ev["final"]["type"], "frames": [ev["start"], ev["end"]],
                               "tc": [ev["tc_start"], ev["tc_end"]], "sheets": ev.get("sheets", []),
                               "preview": ev.get("preview"), "confidence": ev["final"]["confidence"],
                               "what": ev["final"]["what"]}
        # only frames inside the video: "04:00" in a note is clock text, not minute 4
        item["frames_mentioned"] = [f for f in frames_in_text(item["note"], fps) if f < n_frames]
    for item in fb["cuts"]:
        c = cuts.get(item["id"])
        item["current"] = {"frame": c["frame"], "tc": c["tc"], "thumb": c.get("thumb")} if c else None
    fb["missed_frames"] = [f for f in frames_in_text(fb["missed"], fps) if f < n_frames]

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    d = out / "feedback"
    d.mkdir(exist_ok=True)
    (d / f"feedback_{stamp}.txt").write_text(text, encoding="utf-8")
    write_json(d / f"feedback_{stamp}.json", fb)

    counts = {}
    for it in fb["events"] + fb["cuts"]:
        counts[it["verdict"]] = counts.get(it["verdict"], 0) + 1
    print(f"feedback for {data['name']} (report {fb['analysis_id']}, current {data['analysis_id']}): {counts}")
    print(f"saved: {d / f'feedback_{stamp}.json'}\n")
    for it in fb["events"]:
        if it["verdict"] == "CORRECT" and not it["note"]:
            continue
        cur = it.get("current")
        print(f"[{it['verdict']}] {it['id']} (now {it.get('current_id')}) reported as {it['type']} f{it['start']}-{it['end']}")
        if it["note"]:
            print(f"    user note: {it['note']}")
        if it["frames_mentioned"]:
            print(f"    frames mentioned: {it['frames_mentioned']}")
        if cur:
            print(f"    current: {cur['type']} f{cur['frames'][0]}-{cur['frames'][1]} ({cur['tc'][0]}-{cur['tc'][1]}), "
                  f"confidence {cur['confidence']}")
            for s in cur["sheets"]:
                print(f"    sheet: {out / s}")
        else:
            print("    no matching event in the current analysis")
    for it in fb["cuts"]:
        print(f"[{it['verdict']}] {it['id']} hard cut f{it['start']}" + (f" - note: {it['note']}" if it["note"] else "")
              + (f" (thumb {out / it['current']['thumb']})" if it.get("current") and it["current"].get("thumb") else ""))
    if fb["misses"]:
        tcs = {n["frame"]: n.get("tc", "") for n in data.get("near_misses") or []}
        print("\nPOSSIBLE MISSES (the user's answer; EFFECT = a missed effect: look at it and add it):")
        for it in fb["misses"]:
            print(f"  [{it['verdict']}] f{it['frame']} ({tcs.get(it['frame']) or frame_to_tc(it['frame'], fps)})"
                  + (f" - note: {it['note']}" if it["note"] else "")
                  + (f"  -> tools\\sheet.py {data['name']} {it['frame'] - 6} {it['frame'] + 6}"
                     if it["verdict"] == "EFFECT" else ""))
    if fb["missed"]:
        print(f"\nMISSED / GENERAL:\n{fb['missed']}")
        if fb["missed_frames"]:
            print(f"frames mentioned: {fb['missed_frames']}  -> inspect with tools\\sheet.py {data['name']} <start> <end>")
    if fb["unparsed"]:
        print("\nlines not understood:", *fb["unparsed"], sep="\n  ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
