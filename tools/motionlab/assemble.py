"""Build events.json data, merge Claude's review.json over the auto drafts, write report + review todo."""
from __future__ import annotations

import datetime
from pathlib import Path

from . import report_html, taxonomy
from .describe import beat_info
from .timecode import frame_to_tc, nominal_rate
from .util import read_json, write_json

REVIEW_FIELDS = ("type", "what", "evidence", "origin", "origin_why", "timing", "easing", "confidence", "rebuild",
                 "duration_text", "on_beat", "on_drop")


def _overlap(a0, a1, b0, b1) -> float:
    inter = max(0, min(a1, b1) - max(a0, b0) + 1)
    return inter / max(1, min(a1 - a0 + 1, b1 - b0 + 1))


def merge_review(events: list[dict], review: dict) -> list[str]:
    """Attach review entries to events. Entries carry start/end, so they still match after re-detection
    renumbers events. Returns review ids that matched nothing."""
    unmatched = []
    used = set()
    for rid, r in review.items():
        if rid.startswith("_") or not isinstance(r, dict):
            continue
        best, score = None, 0.0
        for ev in events:
            if ev["id"] in used:
                continue
            if "start" in r and "end" in r:
                ov = _overlap(ev["start"], ev["end"], int(r["start"]), int(r["end"]))
                ov += 0.01 if ev["id"] == rid else 0.0
            else:
                ov = 1.0 if ev["id"] == rid else 0.0
            if ov > score:
                best, score = ev, ov
        if best is not None and score >= 0.5:
            best["review"] = {**r, "review_id": rid}
            used.add(best["id"])
        else:
            unmatched.append(rid)
    return unmatched


def finalize(ev: dict) -> None:
    f = dict(ev["auto"])
    r = ev.get("review") or {}
    for k in REVIEW_FIELDS:
        if r.get(k) not in (None, "", []):
            f[k] = r[k]
    if r.get("type"):
        t = r["type"]
        f["type"] = t if t in taxonomy.TYPES else taxonomy.normalize(t)
    if isinstance(f.get("evidence"), str):
        f["evidence"] = [f["evidence"]]
    f["false_alarm"] = bool(r.get("false_alarm"))
    # the detector's sub-label ("iris / circle closing") describes its own type; drop it when the review re-types
    f["sub"] = r.get("sub") or ("" if r.get("type") and f["type"] != ev["type"] else ev.get("sub", ""))
    # stacked types: a reviewed type replaces the detector's stack (its extra types were drafts too);
    # the reviewer keeps extra effects inside the event with "stacked": [...]
    if r.get("stacked"):
        extra = [t if t in taxonomy.TYPES else taxonomy.normalize(t) for t in r["stacked"]]
    elif r.get("type"):
        extra = []
    else:
        extra = [t for t in ev["types"] if t != ev["type"]]
    f["types"] = list(dict.fromkeys([f["type"]] + extra))
    ev["final"] = f


def counts(events: list[dict], plain_cuts: list[dict]) -> tuple[dict, dict]:
    by_type, by_family = {}, {}
    for ev in events:
        if ev["final"].get("false_alarm"):
            continue
        for t in ev["final"]["types"]:
            by_type[t] = by_type.get(t, 0) + 1
            fam = taxonomy.family(t)
            by_family[fam] = by_family.get(fam, 0) + 1
    for c in plain_cuts:
        by_type[c["type"]] = by_type.get(c["type"], 0) + 1
    return by_type, by_family


def cut_rows(plain: list[dict], shots: list[dict], audio: dict | None, fps: float, cfg: dict, drop_tc: bool,
             thumbs: dict) -> list[dict]:
    tol = cfg["audio"]["on_beat_tolerance_frames"]
    starts = sorted(s["start"] for s in shots)
    rows = []
    for i, c in enumerate(plain, 1):
        f = c["frame"]
        bi = beat_info(f, audio, fps, tol)
        prev = max([s for s in starts if s < f], default=0)
        rows.append({
            "id": f"C{i:03d}", "frame": f, "tc": frame_to_tc(f, fps, drop_tc), "time_s": f / fps,
            "kind": "jump cut" if c["type"] == "jump_cut" else "hard cut",
            "on_beat": None if bi is None else bi["on_beat"], "on_drop": None if bi is None else bi["on_drop"],
            "offset_frames": None if bi is None else bi["offset_frames"],
            "bar_beat": (f"{bi['bar']}.{bi['beat_in_bar']}" if bi and bi.get("bar") else None),
            "shot_before_frames": f - prev, "thumb": thumbs.get(f), "evidence": {k: v for k, v in c.items()
                                                                               if k not in ("frame", "type")},
        })
    return rows


def build(name: str, analysis_id: str, source: dict, info: dict, vmeta: dict, audio: dict | None, events: list[dict],
          plain: list[dict], shots: list[dict], cfg: dict, fps: float, drop_tc: bool, cut_thumb_map: dict) -> dict:
    v = info["video"]
    nom = nominal_rate(fps)
    tc_note = (f"{'drop-frame' if drop_tc else 'non-drop'} HH:MM:SS:FF counting {nom} frames per second"
               + (f" (source runs at {fps:g} fps)" if abs(nom - fps) > 0.001 else "") + ", frame 0 = 00:00:00:00")
    for ev in events:
        ev["tc_start"] = frame_to_tc(ev["start"], fps, drop_tc)
        ev["tc_end"] = frame_to_tc(ev["end"], fps, drop_tc)
        ev["tc_key"] = frame_to_tc(ev["key"], fps, drop_tc)
        finalize(ev)
    hard = cut_rows(plain, shots, audio, fps, cfg, drop_tc, cut_thumb_map)
    by_type, by_family = counts(events, plain)
    aud = None
    if audio and audio.get("available"):
        aud = {k: v for k, v in audio.items() if k != "per_frame"}
        for d in aud.get("drops", []):
            d["tc"] = frame_to_tc(int(round(d["frame"])), fps, drop_tc)
    durations = [s["frames"] / fps for s in shots] or [0]
    return {
        "schema": "motionlab.events/1",
        "name": name, "analysis_id": analysis_id,
        "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": source,
        "video": {**{k: v.get(k) for k in ("codec", "pix_fmt", "width", "height", "display_width", "display_height",
                                           "rotation", "r_frame_rate", "avg_frame_rate", "hdr")},
                  "fps": fps, "frames": vmeta["n_frames"], "duration_s": vmeta["n_frames"] / fps,
                  "vfr": vmeta["vfr"], "vfr_detail": vmeta.get("timing"), "analysis_video": vmeta["analysis_video"],
                  "timecode_note": tc_note, "container": info.get("container")},
        "audio": aud, "on_beat_tolerance": cfg["audio"]["on_beat_tolerance_frames"],
        "counts": by_type, "family_counts": by_family,
        "shots": shots, "avg_shot_s": sum(durations) / len(durations),
        "hard_cuts": hard, "events": events,
        "config": cfg,
    }


def write_all(out_dir: Path, data: dict) -> None:
    write_json(out_dir / "events.json", data)
    report_html.render(data, out_dir / "report.html")
    write_todo(out_dir, data)


def write_todo(out_dir: Path, data: dict) -> None:
    lines = [f"# Review todo - {data['name']}", "",
             "1. Read `.claude/skills/analyze-reference/lessons.md` first and apply every rule.",
             "2. Open every sheet below (Read tool). Classify from what you SEE, using the measured evidence.",
             "3. Write `review.json` in this folder (format in SKILL.md), then run `tools/report.py " + data["name"] + "`.",
             "", "| ID | auto type | frames | timecode | reviewed | sheets | first evidence line |",
             "|---|---|---|---|---|---|---|"]
    for ev in data["events"]:
        ev_line = (ev["auto"]["evidence"] or [""])[0].replace("|", "/")
        lines.append(f"| {ev['id']} | {ev['type']} ({ev.get('sub', '')}) | f{ev['start']}-{ev['end']} | "
                     f"{ev['tc_start']}-{ev['tc_end']} | {'yes' if ev.get('review') else 'NO'} | "
                     f"{', '.join(ev.get('sheets', []))} | {ev_line[:140]} |")
    near = data.get("near_misses") or []
    if near:
        lines += ["", "## Possible misses - look at these frames too (sudden changes no event or cut explains)",
                  "If one is an effect, mention it in your summary and in the nearest event's `notes`; check it with "
                  "`tools/sheet.py " + data["name"] + " <start> <end>`.", "",
                  "| frame | timecode | signal | frames |", "|---|---|---|---|"]
        for n in near:
            lines.append(f"| f{n['frame']} | {n['tc']} | {n['signal']} {n['z']}x | {', '.join(n.get('frames', []))} |")
    (out_dir / "review_todo.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def rerender(out_dir: Path) -> dict:
    """Re-merge review.json into events.json and re-render report.html (no recomputation)."""
    data = read_json(out_dir / "events.json")
    review = read_json(out_dir / "review.json") if (out_dir / "review.json").exists() else {}
    for ev in data["events"]:
        ev.pop("review", None)
    unmatched = merge_review(data["events"], review)
    for ev in data["events"]:
        finalize(ev)
    plain = [{"type": "jump_cut" if c["kind"] == "jump cut" else "hard_cut"} for c in data["hard_cuts"]]
    data["counts"], data["family_counts"] = counts(data["events"], plain)
    data["review_unmatched"] = unmatched
    attach_miss_checks(data, review)
    write_all(out_dir, data)
    return data


def attach_miss_checks(data: dict, review: dict) -> None:
    """The reviewer's verdicts on the possible misses (review.json "_near_misses": {"<frame>": "text"}), shown in the
    report next to each candidate so the user does not have to re-check them."""
    checks = review.get("_near_misses") or {}
    for n in data.get("near_misses") or []:
        n["checked"] = checks.get(str(n["frame"]), "")
