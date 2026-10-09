"""MotionLab's own MCP server for Claude Code: compact, read-only views of the lab (analyses, events, verdicts,
knowledge, projects) and pictures returned inline (contact sheets, any frames of a reference, rendered stills of a
plan, overlay stills). Every frame it names comes with its timecode. It writes nothing: long work (analyze.py,
render_video.py, overlay.py render) stays on the command line.

    registered in the repo's .mcp.json (project scope): Claude Code starts it by itself in this folder
    .venv\\Scripts\\python tools\\mcp_server.py --enable        approve it for this PC once (.claude\\settings.local.json
                                                              enabledMcpjsonServers; setup.bat asks), so the app's
                                                              Claude buttons don't stop at Claude Code's trust prompt
    .venv\\Scripts\\python tools\\mcp_server.py --selftest      call every tool once on this PC's data (no MCP client)

Why: events.json is ~0.7 MB for a 2.5-minute video; `events` / `event` return the part a task needs instead, and the
picture tools save a separate Read per image. Tools are listed in TOOLS below (the names Claude sees are
mcp__motionlab__<name>).
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image as PILImage, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab.timecode import frame_to_tc  # noqa: E402
from motionlab.util import ANALYSIS, LAB, tool  # noqa: E402

MAX_FRAMES = 24                              # pictures per call (frames / stills)
PROJECTS = LAB / "projects"
KNOWLEDGE = LAB / "knowledge" / "local"


# ------------------------------------------------------------------------------------------------ helpers
def _ref_dir(reference: str) -> Path:
    """The analysis folder for a name (exact, else the unique folder that contains it, case-insensitive)."""
    name = Path(str(reference)).name
    d = ANALYSIS / name
    if (d / "events.json").exists():
        return d
    hits = [p for p in ANALYSIS.iterdir() if p.is_dir() and name.lower() in p.name.lower()
            and (p / "events.json").exists()]
    if len(hits) == 1:
        return hits[0]
    raise ValueError(f"no analysis '{reference}'" + (f" - several match: {[h.name for h in hits]}" if hits else
                                                     " - call references() for the names"))


def _events(d: Path) -> dict:
    return json.loads((d / "events.json").read_text(encoding="utf-8"))


def _verdicts(d: Path) -> dict:
    p = d / "feedback" / "verdicts.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _ftc(f: int, fps: float) -> str:
    return f"f{int(f)} ({frame_to_tc(int(f), fps)})"


def _rng(a: int, b: int, fps: float) -> str:
    return _ftc(a, fps) if a == b else f"f{a}-{b} ({frame_to_tc(a, fps)}-{frame_to_tc(b, fps)})"


def _label(e: dict) -> str:
    f = e.get("final") or {}
    return f.get("type_label") or e.get("type_label") or e.get("type", "?")


def _review_state(e: dict) -> str:
    r = e.get("review") or {}
    if not r:
        return "not reviewed"
    if r.get("false_alarm") or (e.get("final") or {}).get("false_alarm"):
        return "false alarm"
    return "reviewed" + (" (relabelled)" if (e.get("final") or {}).get("type") not in (None, e.get("type")) else "")


def _jpeg(img: np.ndarray | PILImage.Image, width: int = 1400, quality: int = 82):
    from mcp.server.fastmcp import Image
    im = img if isinstance(img, PILImage.Image) else PILImage.fromarray(img)
    if im.width > width:
        im = im.resize((width, int(round(im.height * width / im.width))), PILImage.LANCZOS)
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "JPEG", quality=quality)
    return Image(data=buf.getvalue(), format="jpeg")


def _frame_list(spec: str, last: int) -> list[int]:
    """'480,481,500' or '480-500' or '480-600:10' (every 10th) -> frames (at most MAX_FRAMES)."""
    out: list[int] = []
    for part in str(spec).replace(" ", "").split(","):
        if not part:
            continue
        if "-" in part:
            rng, _, step = part.partition(":")
            a, b = (int(v) for v in rng.split("-", 1))
            out += list(range(a, b + 1, max(1, int(step or 1))))
        else:
            out.append(int(part))
    out = [min(max(0, f), last) for f in out]
    if len(out) > MAX_FRAMES:
        raise ValueError(f"{len(out)} frames asked, at most {MAX_FRAMES} per call (use a step, e.g. 0-600:25)")
    return out


def _tile(images: list[tuple[np.ndarray, str]], cols: int = 4, tile_w: int = 480) -> PILImage.Image:
    from motionlab.media import fonts
    F = fonts(0.9)
    h0, w0 = images[0][0].shape[:2]
    th = int(round(tile_w * h0 / w0))
    rows = (len(images) + cols - 1) // cols
    sheet = PILImage.new("RGB", (cols * (tile_w + 6) + 6, rows * (th + 26) + 6), (18, 18, 20))
    d = ImageDraw.Draw(sheet)
    for i, (img, lab) in enumerate(images):
        x, y = 6 + (i % cols) * (tile_w + 6), 6 + (i // cols) * (th + 26)
        sheet.paste(PILImage.fromarray(img).convert("RGB").resize((tile_w, th), PILImage.LANCZOS), (x, y))
        d.text((x + 2, y + th + 3), lab, fill=(255, 196, 0), font=F["small"])
    return sheet


def _video_frames(video: Path, frames: list[int], width: int = 640) -> dict[int, np.ndarray]:
    """Decode exact frames (0-based) of a video, read-only."""
    want = sorted(set(frames))
    sel = "+".join(f"eq(n\\,{f})" for f in want)
    probe = subprocess.run([tool("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height", "-of", "json", str(video)], capture_output=True, text=True)
    s = json.loads(probe.stdout)["streams"][0]
    w = width
    h = int(round(w * int(s["height"]) / int(s["width"]) / 2)) * 2
    r = subprocess.run([tool("ffmpeg"), "-v", "error", "-nostdin", "-i", str(video), "-map", "0:v:0", "-vf",
                        f"select='{sel}',scale={w}:{h}:flags=area", "-fps_mode", "passthrough", "-f", "rawvideo",
                        "-pix_fmt", "rgb24", "-"], capture_output=True)
    n = w * h * 3
    got = [np.frombuffer(r.stdout[i * n:(i + 1) * n], np.uint8).reshape(h, w, 3) for i in range(len(r.stdout) // n)]
    return dict(zip(want, got))


def _analysis_video(d: Path, ev: dict) -> Path:
    proxy = d / "proxy_cfr.mp4"                    # VFR sources are analysed on a constant-rate copy
    if proxy.exists():
        return proxy
    src = Path((ev.get("source") or {}).get("path", ""))
    if not src.exists():
        raise ValueError(f"the analysed video is gone: {src}")
    return src


# ------------------------------------------------------------------------------------------------ tools
def references() -> str:
    """Every analysed reference: name (use it in the other tools), category, length, effects found / reviewed by
    Claude / given a verdict by the user, possible misses, and the next workflow step."""
    from motionlab.app import data
    rows = []
    for r in data.list_references():
        fl = r.get("flow", {})
        fps, n = float(r.get("fps") or 25), int(r.get("frames") or 0)
        rows.append(f"- {r['name']} | {r.get('category_label') or r.get('category', '')} | {n} frames at {fps:g} fps "
                    f"({frame_to_tc(max(n - 1, 0), fps)} last) | effects {r.get('events', 0)}, reviewed "
                    f"{r.get('reviewed', 0)}, verdicts {r.get('verdicts', 0)}, cuts {r.get('cuts', 0)} | next: "
                    f"{fl.get('next', '-')}")
    return "\n".join(rows) or "no analysed references yet (References > Download / Analyse in the app)"


def events(reference: str, type: str = "", start: int | None = None, end: int | None = None,
           unreviewed_only: bool = False, include_false_alarms: bool = False) -> str:
    """One line per detected effect of a reference: id, label (after Claude's review), frames + timecodes, score,
    review state and the user's verdict. Filters: type (substring of type / label / family), frame range,
    unreviewed_only, include_false_alarms. Detail of one effect: event()."""
    d = _ref_dir(reference)
    ev = _events(d)
    fps = float(ev["video"]["fps"])
    v = _verdicts(d).get("events", {})
    out = []
    for e in ev["events"]:
        lab = _label(e)
        st = _review_state(e)
        hay = " ".join([e.get("type", ""), lab, e.get("family", ""), str((e.get("final") or {}).get("type", "")),
                        " ".join(e.get("types") or [])]).lower()
        if type and type.lower() not in hay:
            continue
        if start is not None and e["end"] < start or end is not None and e["start"] > end:
            continue
        if unreviewed_only and st != "not reviewed":
            continue
        if st == "false alarm" and not include_false_alarms:
            continue
        vv = v.get(e["id"], {})
        out.append(f"{e['id']} | {lab} | {_rng(e['start'], e['end'], fps)} | score {e.get('score', 0):.2f} | {st}"
                   + (f" | verdict {vv.get('v')}" + (f": {vv['note']}" if vv.get("note") else "") if vv.get("v") else ""))
    head = (f"{ev.get('name', d.name)}: {len(out)} of {len(ev['events'])} effects, {ev['video']['frames']} frames at "
            f"{fps:g} fps, {len(ev.get('hard_cuts', []))} hard cuts, {len(ev.get('shots', []))} shots")
    return head + "\n" + "\n".join(out)


def event(reference: str, id: str) -> str:
    """Everything about one effect (id like E004): detected type and parts with their measured evidence, Claude's
    review (what happens, timing, easing, how to rebuild), the user's verdict and note, and its files."""
    d = _ref_dir(reference)
    ev = _events(d)
    fps = float(ev["video"]["fps"])
    e = next((x for x in ev["events"] if x["id"].lower() == str(id).lower()), None)
    if not e:
        raise ValueError(f"{reference} has no event {id}")
    L = [f"{e['id']} {_label(e)} - {_rng(e['start'], e['end'], fps)}, key {_ftc(e.get('key', e['start']), fps)}, "
         f"{e.get('duration_frames')} frames, detected as {e.get('type_label')} ({e.get('sub') or '-'}), score "
         f"{e.get('score')}", f"cuts inside: {', '.join(_ftc(c, fps) for c in e.get('cuts') or []) or 'none'}"]
    for c in e.get("components") or []:
        L.append(f"- part {c.get('label')} {_rng(c['start'], c['end'], fps)}: " + "; ".join(c.get("notes") or []))
    f = e.get("final") or {}
    for k in ("what", "timing", "easing", "origin", "rebuild", "notes"):
        if f.get(k):
            L.append(f"{k}: {f[k] if isinstance(f[k], str) else json.dumps(f[k])}")
    vv = _verdicts(d).get("events", {}).get(e["id"])
    L.append(f"user's verdict: {vv.get('v')}" + (f" - {vv['note']}" if vv.get("note") else "") if vv else
             "user's verdict: none yet")
    L.append(f"files: sheets {e.get('sheets')} (sheet()), preview {e.get('preview')}")
    return "\n".join(L)


def sheet(reference: str, id: str, page: int = 1):
    """The contact sheet of one effect as a picture (the frames around it, frame + timecode on each tile)."""
    d = _ref_dir(reference)
    e = next((x for x in _events(d)["events"] if x["id"].lower() == str(id).lower()), None)
    if not e or not e.get("sheets"):
        raise ValueError(f"{reference} {id}: no contact sheet")
    sheets = e["sheets"]
    p = d / sheets[min(max(page, 1), len(sheets)) - 1]
    return [f"{e['id']} sheet {min(max(page, 1), len(sheets))} of {len(sheets)}: {p.relative_to(LAB)}",
            _jpeg(PILImage.open(p), width=1600)]


def frames(reference: str, frames: str):
    """Any frames of a reference's analysed video as one picture, frame + timecode on each tile: '480,481,500',
    '480-500' or '0-3895:100' (every 100th); at most 24 per call. Read-only."""
    d = _ref_dir(reference)
    ev = _events(d)
    fps, last = float(ev["video"]["fps"]), int(ev["video"]["frames"]) - 1
    want = _frame_list(frames, last)
    got = _video_frames(_analysis_video(d, ev), want)
    tiles = [(got[f], _ftc(f, fps)) for f in want if f in got]
    if not tiles:
        raise ValueError("no frames decoded")
    return [f"{d.name}: {len(tiles)} frame(s)", _jpeg(_tile(tiles, cols=min(4, len(tiles))))]


def frame_info(reference: str, frame: int) -> str:
    """What is at one frame of a reference: timecode, its shot, the nearest hard cut and beat (on the beat = within
    one frame), and the effects that cover it."""
    d = _ref_dir(reference)
    ev = _events(d)
    fps = float(ev["video"]["fps"])
    f = int(frame)
    shot = next((s for s in ev.get("shots", []) if s["start"] <= f <= s["end"]), None)
    cuts = [c["frame"] for c in ev.get("hard_cuts", [])]
    near = min(cuts, key=lambda c: abs(c - f)) if cuts else None
    beats = [float(b["frame"]) if isinstance(b, dict) else float(b) * fps
             for b in (ev.get("audio") or {}).get("beats", [])]
    nb = min(beats, key=lambda b: abs(b - f)) if beats else None
    cover = [f"{e['id']} {_label(e)} {_rng(e['start'], e['end'], fps)}" for e in ev["events"]
             if e["start"] <= f <= e["end"] and _review_state(e) != "false alarm"]
    return "\n".join([
        f"{_ftc(f, fps)} of {ev['video']['frames']} frames",
        f"shot {shot['index']}: {_rng(shot['start'], shot['end'], fps)}" if shot else "shot: -",
        f"nearest hard cut: {_ftc(near, fps)} ({near - f:+d} frames)" if near is not None else "no hard cuts",
        (f"nearest beat: {nb:.1f} ({nb - f:+.1f} frames, {'on' if abs(nb - f) <= 1 else 'off'} the beat)"
         if nb is not None else "no beats"),
        "effects here: " + ("; ".join(cover) or "none")])


def verdicts(reference: str) -> str:
    """The user's verdicts on a reference: counts, every Partly / Wrong with its note, effects they say were
    missed, and their answers on the possible misses."""
    d = _ref_dir(reference)
    ev = _events(d)
    fps = float(ev["video"]["fps"])
    V = _verdicts(d)
    evs = V.get("events", {})
    cnt: dict[str, int] = {}
    for x in evs.values():
        cnt[x.get("v", "?")] = cnt.get(x.get("v", "?"), 0) + 1
    L = [f"{d.name}: " + (", ".join(f"{n} {k}" for k, n in sorted(cnt.items())) or "no verdicts yet")]
    for k, x in sorted(evs.items()):
        if x.get("v") in ("partly", "wrong"):
            L.append(f"- {k} {x['v']}: {x.get('note', '')}")
    for m in V.get("missed", []) or []:
        L.append(f"- missed: {json.dumps(m)}")
    for fr, m in sorted((V.get("misses") or {}).items(), key=lambda kv: int(kv[0])):
        L.append(f"- possible miss {_ftc(int(fr), fps)}: {m.get('v', m) if isinstance(m, dict) else m}"
                 + (f" - {m.get('what') or m.get('note')}" if isinstance(m, dict) and (m.get("what") or m.get("note"))
                    else ""))
    return "\n".join(L)


def knowledge(category: str = "") -> str:
    """What MotionLab knows from everyone's analysed references: the short summary (pacing norms, effects seen,
    corrections per category), or with a category id (music_video, vlog, cooking, ...) every reviewed effect of that
    category."""
    p = KNOWLEDGE / "summary" / f"{category}.md" if category else KNOWLEDGE / "summary.md"
    if not p.exists():
        return f"no {p.relative_to(LAB)} yet (Knowledge page > rebuild, or tools\\knowledge.py summary)"
    return p.read_text(encoding="utf-8")


def project(name: str) -> str:
    """One of the user's videos (projects\\<name>): footage with source IDs and frame caches (colour / grey), the edit
    plans (layers per type, length), renders and overlays."""
    from motionlab import footage as FC
    d = PROJECTS / Path(str(name)).name
    if not d.is_dir():
        have = [p.name for p in PROJECTS.iterdir() if p.is_dir()] if PROJECTS.exists() else []
        raise ValueError(f"no project '{name}' (projects: {have})")
    b = d / "build"
    L = [f"project {d.name}"]
    man = json.loads((b / "sources.json").read_text(encoding="utf-8")) if (b / "sources.json").exists() else {}
    for sid, s in sorted(man.get("sources", {}).items()):
        caches = []
        for color in (True, False):
            mp = FC.paths(b / "cache", sid, color)[1]
            if mp.exists():
                m = json.loads(mp.read_text(encoding="utf-8"))
                caches.append(f"{'colour' if color else 'grey'} {m['frames']} f @ {m['fps']:g} fps {m['width']}x{m['height']}")
        L.append(f"- {sid} = {s['name']}: " + ("; ".join(caches) or "no cache (prep_footage.py)"))
    for p in sorted(b.glob("plan_v*.json")):
        pl = json.loads(p.read_text(encoding="utf-8"))
        kinds: dict[str, int] = {}
        for lay in pl.get("layers", []):
            kinds[lay["type"]] = kinds.get(lay["type"], 0) + 1
        fps = float(pl.get("fps", 25))
        L.append(f"- {p.name}: {pl.get('width')}x{pl.get('height')}, {pl.get('frames')} frames "
                 f"({frame_to_tc(int(pl.get('frames', 1)) - 1, fps)} last), layers "
                 + ", ".join(f"{k} {n}" for k, n in sorted(kinds.items())))
    for p in sorted(b.glob("*.mp4")):
        L.append(f"- render {p.name} ({p.stat().st_size / 1e6:.0f} MB)")
    for p in sorted((b / "overlays").glob("*/overlay.json")) if (b / "overlays").exists() else []:
        c = json.loads(p.read_text(encoding="utf-8"))
        L.append(f"- overlay {c['name']}: {c['frames']} frames" + (" (rendered)" if (p.parent / f"{c['name']}.mov").exists()
                                                                  else " (not rendered)"))
    return "\n".join(L)


def stills(plan: str, frames: str):
    """Rendered frames of an edit plan (projects\\<name>\\build\\plan_vN.json) as one picture, frame + timecode on
    each tile - computed in memory, nothing is written. '480,1633' or '0-600:50'; at most 24."""
    from motionlab.compose import Renderer
    p = Path(plan)
    if not p.is_absolute():
        p = (PROJECTS / p) if not str(plan).lower().startswith("projects") else LAB / p
    p = p.resolve()
    if PROJECTS.resolve() not in p.parents or p.suffix != ".json":
        raise ValueError("give a plan inside projects\\, e.g. projects\\test_4am\\build\\plan_v1.json")
    pl = json.loads(p.read_text(encoding="utf-8"))
    want = _frame_list(frames, int(pl["frames"]) - 1)
    R = Renderer(pl)
    fps = float(pl["fps"])
    tiles = [(R.render(f), _ftc(f, fps)) for f in want]
    return [f"{p.relative_to(LAB)}: {len(tiles)} rendered frame(s)", _jpeg(_tile(tiles, cols=min(3, len(tiles)),
                                                                                tile_w=520))]


def overlay_stills(folder: str, frames: str):
    """Frames of a rendered HTML overlay (tools\\overlay.py) on a checkerboard, frame + timecode on each tile."""
    from motionlab import overlays as OV
    f = Path(folder)
    f = (LAB / f) if not f.is_absolute() else f
    c = json.loads((f / "overlay.json").read_text(encoding="utf-8"))
    m, arr = OV.load(f / f"{c['name']}.mov")
    want = _frame_list(frames, m["frames"] - 1)
    x, y, w, h = m["crop"]
    tiles = []
    for fr in want:
        a = np.asarray(arr[fr], np.float32) / 255.0
        yy, xx = np.mgrid[0:m["height"], 0:m["width"]]
        img = np.where((((yy // 16) + (xx // 16)) % 2)[..., None] == 0, 0.32, 0.22).astype(np.float32) * np.ones(3)
        reg = img[y:y + h, x:x + w]
        reg[:] = reg * (1 - a[..., 3:]) + a[..., :3] * a[..., 3:]
        tiles.append(((img * 255 + 0.5).astype(np.uint8), _ftc(fr, float(c["fps"]))))
    return [f"overlay {c['name']}: {len(tiles)} frame(s)", _jpeg(_tile(tiles, cols=min(3, len(tiles)), tile_w=520))]


TOOLS = [references, events, event, sheet, frames, frame_info, verdicts, knowledge, project, stills, overlay_stills]
INSTRUCTIONS = ("MotionLab lab data, read-only. Start with references() or project(); events()/event() instead of "
                "reading events.json; sheet()/frames()/stills()/overlay_stills() return pictures with frame + "
                "timecode on every tile. Long jobs (analyze.py, render_video.py, overlay.py render) stay in the shell.")


def build():
    from mcp.server.fastmcp import FastMCP
    srv = FastMCP("motionlab", instructions=INSTRUCTIONS, log_level="WARNING")
    for fn in TOOLS:
        srv.tool()(fn)
    return srv


def selftest() -> int:
    """Call every tool on this PC's data and print a short result (no MCP client needed)."""
    from motionlab.app import data
    refs = [r["name"] for r in data.list_references()]
    projs = [p.name for p in PROJECTS.iterdir() if p.is_dir()] if PROJECTS.exists() else []
    print(references()[:400], "\n")
    if refs:
        r = refs[0]
        out = events(r)
        print(out.splitlines()[0], f"({len(out)} chars, events.json {(_ref_dir(r) / 'events.json').stat().st_size} "
                                    f"bytes)")
        eid = out.splitlines()[1].split(" | ")[0]
        print(event(r, eid)[:300], "\n")
        print(frame_info(r, 480), "\n")
        print(verdicts(r)[:300], "\n")
        print([type(x).__name__ for x in sheet(r, eid)], [type(x).__name__ for x in frames(r, "0-100:25")])
    print(knowledge()[:200], "\n")
    if projs:
        print(project(projs[0])[:600])
        plans = sorted((PROJECTS / projs[0] / "build").glob("plan_v*.json"))
        if plans:
            print([type(x).__name__ for x in stills(str(plans[-1]), "480,1633")])
    print("MCP SELFTEST DONE")
    return 0


def enable(on: bool = True) -> int:
    """Approve (or un-approve) the project's 'motionlab' server for this PC in .claude\\settings.local.json."""
    p = LAB / ".claude" / "settings.local.json"
    s = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    names = [n for n in s.get("enabledMcpjsonServers", []) if n != "motionlab"] + (["motionlab"] if on else [])
    s["enabledMcpjsonServers"] = names
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(s, indent=2), encoding="utf-8")
    print(f"MotionLab MCP server {'approved' if on else 'no longer approved'} for Claude Code on this PC ({p})")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if "--enable" in sys.argv or "--disable" in sys.argv:
        sys.exit(enable("--enable" in sys.argv))
    build().run()
