"""The brief (0.5.3): what Claude needs to start a video, made by the lab in one file - instead of ~70 k tokens of
reading the lab before the first decision. Nothing is dropped: what is not in it is named at its end ("Left out"),
with the command that prints it.

    .venv\\Scripts\\python tools\\brief.py <project>      -> projects\\<project>\\build\\brief.md (prints its path + size)
          A video from zero (build\\generate_request.json): the request with its blanks filled and marked (asked /
          default / a guess - format, song, look), the song's beats from the start used (beats.py), the templates
          that fit the words with their moves (tracks, frame + timecode), sizes they are checked at and text
          settings, the style of the `like` videos (style.py; else the closest ones), the user's ratings as rules
          (knowledge.py memory --rules), the lessons for this kind (knowledge.py lessons --kind generate).
          An edit (build\\edit_request.json): the request in words (edit_brief.md), the clips (length, rate, size,
          sound, their words if transcribed), the photos (2026-10-24: size, shape, date taken, the user's length /
          zoom, one sheet of them all), the references' style, the ratings as rules, the lessons (talking videos:
          --kind talking; others: every lesson).
The app writes it when a request is saved; /generate-video and /recreate-video read it first (they run this when it
is missing or older than the request). Reads only; writes brief.md (+ build\\photos\\photos_sheet.jpg).
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import knowledge as KN  # noqa: E402
from motionlab import overlay_settings as OS  # noqa: E402
from motionlab import templates as TM  # noqa: E402
from motionlab.timecode import frame_to_tc  # noqa: E402
from motionlab.util import LAB, setup_console  # noqa: E402

PY, TOOLS = sys.executable, LAB / "tools"
PROJECTS = LAB / "projects"
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".m4v", ".webm", ".avi"}


def tool(*args: str, timeout: int = 180) -> str:
    """A lab tool's printed output (its log lines with [ 1.2s] stamps dropped)."""
    r = subprocess.run([PY, str(TOOLS / args[0]), *args[1:]], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=str(LAB), timeout=timeout)
    return "\n".join(ln for ln in (r.stdout or "").splitlines() if not ln.startswith("[")).strip()


def last_format(skip: str) -> tuple[str, str] | None:
    """The format the user picked in their newest other Generate request: (format, project)."""
    rows = []
    for p in PROJECTS.glob("*/build/generate_request.json"):
        if p.parents[1].name == skip:
            continue
        try:
            f = json.loads(p.read_text(encoding="utf-8")).get("format")
        except (OSError, ValueError):
            continue
        if f:
            rows.append((p.stat().st_mtime, f, p.parents[1].name))
    return max(rows)[1:] if rows else None


def recent_line(recent: dict[str, int], lib: dict) -> list[str]:
    shown = sorted(((k, c) for k, c in recent.items() if k in lib), key=lambda x: (-x[1], x[0]))
    return [f"Used in the newest videos (up to {TM.RECENT_PROJECTS}; how many used it) - pushed down in the options "
            "here, another unless one is clearly the best fit: " + ", ".join(f"{k} ({c})" for k, c in shown)] \
        if shown else []


def edit_template_lines(skip: str, words: str, n: int = 8) -> list[str]:
    """The Editor's templates (2026-10-26, variety): what the newest videos used, and n options that fit the request's
    and the script's words (templates.py pick: those pushed down, this video's own order)."""
    lib = {t["id"]: t for t in TM.library()}
    recent = TM.recent(skip=skip)
    L = ["", "## Motion Graphics templates (for the `graphic` lines; templates.py pick --fresh)"] + recent_line(recent, lib)
    L.append("Options that fit the words - each template once a video unless a repeat is the point; more for one "
             "graphic: `templates.py pick \"<what it shows>\" --n 8 --fresh`; settings: `overlay.py settings <id>`:")
    for t in TM.pick(words, n, used=recent, seed=skip):
        L.append(f"- **{t['id']}** ({t.get('kind', '')}" + (f"; NOT at {', '.join(t['sizes_bad'])}" if t.get("sizes_bad")
                 else "") + f") - {(t.get('what') or '')[:110]}")
    return L


def template_lines(ids: list[str], want: str, lines: list[str], skip: str, size: str | None,
                   n: int = 10) -> tuple[list[str], int]:
    """The templates for the brief: the user's picks, then (2026-10-26, variety) 2-3 options for each line of the
    words - each line others, the scene templates a video without footage can use - or, with no lines, the n that fit
    the request; the ones the last videos used pushed down (templates.recent) and named."""
    lib = {t["id"]: t for t in TM.library()}
    recent = TM.recent(skip=skip)
    picked = [lib[i] for i in ids if i in lib]
    L = []
    if lines:
        k = max(2, min(3, 16 // len(lines)))
        for ln in lines[:12]:
            have = {q["id"] for q in picked}
            opts = [t["id"] for t in TM.pick(ln, 60, also=want, used=recent, seed=skip)
                    if t["id"] not in have and t.get("kind") not in ("transitions", "background", "lower_thirds")
                    and not t.get("needs_media") and not t.get("media_slots")
                    and not (size and size in (t.get("sizes_bad") or []))][:k]
            picked += [lib[i] for i in opts]
            L.append(f"- \"{ln}\" -> " + ", ".join(f"**{i}**" for i in opts))
        L.append("Each line has options of its own - choose by what the line shows, each template once unless the "
                 "video needs a repeat; a scene change: shape-wipe / pixel-wipe and the other transitions.")
    else:
        for t in TM.pick(want, n + len(picked), used=recent, seed=skip):
            if t["id"] not in {p["id"] for p in picked} and len(picked) < n + len(ids):
                picked.append(lib.get(t["id"], t))
    L += recent_line(recent, lib)
    if L:
        L.append("")
    for t in picked:
        c = OS.conf(LAB / t["folder"])
        fps = float(c["fps"])
        decl = OS.declared(LAB / t["folder"])
        texts = t.get("text_slots") or [d["id"] for d in decl if d["type"] == "string" and not any(
            w in d["id"] for w in ("media", "focus", "logo", "image", "photo", "video"))]
        texts = [s["id"] if isinstance(s, dict) else s for s in texts]
        tr = t.get("tracks") or []
        moves = "; ".join(f"{i}. {x.get('name')} f{x['start_f']} ({frame_to_tc(x['start_f'], fps)}) +{x['length_f']}"
                          for i, x in enumerate(tr[:6], 1)) + (f"; +{len(tr) - 6} more" if len(tr) > 6 else "")
        sizes = ((f"ok at {', '.join(t['sizes_ok'])}" if t.get("sizes_ok") else "")
                 + (f"; NOT at {', '.join(t['sizes_bad'])}" if t.get("sizes_bad") else "")) or "other sizes not checked yet"
        L.append(f"- **{t['id']}** ({t.get('kind', '')}{', yours' if t['id'] in ids else ''}; {c['width']}x{c['height']} "
                 f"{fps:g} fps {c['frames']} f; {sizes}) - {(t.get('what') or '')[:160]}"
                 + (f"\n  moves: {moves}" if moves else "\n  moves: not measured yet (templates.py tracks --measure)")
                 + (f"\n  words: {', '.join(texts)}" if texts else ""))
    return L, len(lib) - len(picked)


def generate_brief(p: Path, req: dict) -> list[str]:
    want, words = req.get("want", ""), req.get("text", "")
    L = [f"# Brief: {p.name} - a video from zero ({req.get('kind')})", "",
         f"Made by the lab (tools\\brief.py, {time.strftime('%Y-%m-%d %H:%M')}) from build\\generate_request.json "
         f"({req.get('date', '')}): everything to start with, in one read. *Left out* at the end names what is not "
         "here and the command that prints it. A guess below is yours to change - say which you kept.", "",
         "## The request", f"- what: {want}"]
    if words:
        L += ["- words on screen (the user's, one per line):"] + [f"  - {w}" for w in words.splitlines()]
    L.append(f"- length: {req['length_s']:g} s (asked)" if req.get("length_s") else
             "- length: not set - a guess: what the song's bars and the words need (30 s is the usual reel)")
    fmt = req.get("format")
    if fmt:
        L.append(f"- format: {fmt} (asked)")
    else:
        lf = last_format(p.name)
        L.append(f"- format: not set - a guess: {lf[0]} (what the user picked last time, {lf[1]})" if lf else
                 "- format: not set - a guess: vertical 1080x1920 (the repo templates are drawn for it); AE "
                 "templates only where the table below says ok at 1080x1920")
    song, start = req.get("music"), 0.0
    if song:
        L.append(f"- song: {Path(song).name} (asked) - only read; a part of it = cut a copy into build\\")
    elif req.get("kind") == "graphics":
        from motionlab import sfx as SFX
        ls = SFX.last_song()
        if ls:
            song, start = ls[0], ls[1]
            L.append(f"- song: none chosen - a guess: {Path(song).name} from {start:g} s (the last reel's, {ls[2]}); "
                     "ask before using it")
        else:
            L.append("- song: none - time it to the style's rhythm")
    look = json.loads((TM.MOTION / "_looks" / "index.json").read_text(encoding="utf-8")).get("default") \
        if (TM.MOTION / "_looks" / "index.json").exists() else None
    L.append("- look: " + ", ".join(x for x in (
        f"colours {req['colours']} (asked)" if req.get("colours") else "",
        f"font {req['font']} (asked)" if req.get("font") else "",
        ("a look of your own - surprise the user (asked): not the default look, not the last video's"
         if req.get("look") == "surprise" else
         f"the look '{req['look']}' (asked)" if req.get("look") else
         f"the default look '{look}' (default - `templates.py looks` lists the others)" if look else "")) if x)
             or "- look: the templates' own")
    if req.get("templates"):
        L.append(f"- templates the user picked (use every one): {', '.join(req['templates'])}")
    if req.get("kind") == "ai":
        L.append(f"- tool: {req.get('tool') or 'not named - ask'}")
    if req.get("brand"):                                     # 0.6.0: For my brand - the brand shapes the whole video
        from motionlab import brand as BR
        L += ["", "## For my brand", *BR.brief_lines(req["brand"], "video")]
    if song and req.get("kind") == "graphics":
        secs = req.get("length_s") or 60
        L += ["", f"## The beats ({'the song asked' if req.get('music') else 'the guessed song'}, frame 0 = {start:g} s "
                  "into it, 30 fps; tools\\beats.py)", "```", tool("beats.py", song, "--fps", "30", "--start",
                                                                f"{start}", "--length", f"{secs}"), "```"]
    left = []
    if req.get("kind") == "graphics":
        from motionlab.style import SIZES
        tl, rest = template_lines(req.get("templates") or [], want, [w.strip() for w in words.splitlines() if w.strip()],
                                  p.name, "x".join(map(str, SIZES[fmt])) if fmt in SIZES else None)
        L += ["", "## Templates that fit the words (the user's picks first; templates.py pick)",
              "Land a move on a beat: `overlay.py new <folder> --from <id> --land \"<track>@<plan frame>\" [--start "
              "<cut>]`. Their settings: `overlay.py settings <id>`."] + tl
        left.append(f"the other {rest} templates: `templates.py library --brief` (one line each)")
    like = req.get("like") or []
    L += ["", "## Style"]
    if like:
        L += [f"The style of {', '.join(like)} (tools\\style.py) - copy the style, never the content:", "```",
              tool("style.py", *like), "```"]
    else:
        L += ["No `like` video: the analysed videos whose measured style is closest to the words (style.py closest) - "
              "60 % or more = suggest it as the style:", "```", tool("style.py", "closest", want or words or "video"),
              "```"]
    L += ["", KN.memory_rules(), "", KN.lessons_for("generate" if req.get("kind") == "graphics" else "all")]
    left += ["Claude's memory beyond the ratings (every analysed video's style in one line, the effects seen and how "
             "they were made): `knowledge.py memory` - for a copy of one reference's effects",
             "the request as JSON: build\\generate_request.json"]
    return L + ["", "## Left out (nothing silently)"] + [f"- {x}" for x in left]


def photo_lines(p: Path, req: dict) -> list[str]:
    """The photos of the folder (2026-10-24): still shots - no motion, no sound, no words to transcribe. Their size,
    shape, the date taken and the user's length / zoom for each, and ONE sheet with every photo and its name
    (build\\photos\\photos_sheet.jpg) that Claude looks at to know what each shows."""
    from motionlab import photos as PH
    from motionlab.project import PHOTO_EXT, clip_files
    ph = clip_files(p, PHOTO_EXT)
    if not ph:
        return []
    asked = req.get("photos") or {}
    L = ["", "## The photos (still shots: no motion, no sound; only read)",
         f"Each is a clip of its own in the plan: a clip layer with `\"hold\": true, \"in\": 0` - {PH.SECONDS:g} s and "
         f"a slow zoom to {PH.KEN_BURNS:g} unless the user set otherwise below; `\"fit\": \"contain\"` shows the whole "
         "photo over a blurred copy of itself (a horizontal photo in a vertical video). Silent: the song or the "
         "clips' sound goes on under it. Place them where they tell the story."]
    sheet = p / "build" / "photos" / "photos_sheet.jpg"
    try:
        PH.sheet(ph, sheet)
        L.append(f"**Look at `build\\photos\\photos_sheet.jpg` once** (every photo with its name) to know what each "
                 "shows - no need to open them one by one.")
    except Exception as e:                                   # noqa: BLE001 - no sheet: the list still says enough
        L.append(f"(no sheet of the photos: {type(e).__name__}: {e} - open the photos themselves)")
    for f in ph:
        try:
            i = PH.info(f)
            what = f"{i['width']}x{i['height']} {i['orientation']} {i['format']}" + (f", taken {i['taken']}"
                                                                                    if i["taken"] else "")
        except Exception as e:                               # noqa: BLE001 - a photo that does not open is named
            what = f"could not be read ({type(e).__name__})"
        o = asked.get(f.name) or {}
        mine = ", ".join(x for x in (f"{o['seconds']:g} s (the user's)" if o.get("seconds") else "",
                                     "no zoom (the user's)" if o.get("zoom") is False else "",
                                     "the whole photo (the user's)" if o.get("fit") == "contain" else "") if x)
        L.append(f"- {f.name}: {what}" + (f"; {mine}" if mine else ""))
    return L


def clip_lines(p: Path) -> list[str]:
    from motionlab import speech as SP
    from motionlab.project import clip_files
    L = []
    for v in clip_files(p, VIDEO_EXT):
        try:
            i = SP.probe(v)
        except Exception:                                   # noqa: BLE001 - a clip that does not read is named
            L.append(f"- {v.name}: could not be read")
            continue
        fps = float(i.get("fps") or 30)
        n = int(i.get("frames") or 0)
        words = sorted((p / "build" / "speech").glob(f"{v.stem}.*.json"))
        L.append(f"- {v.name}: {n / fps if fps else 0:.1f} s, {n} frames at {fps:g} fps "
                 f"({frame_to_tc(max(n - 1, 0), fps)} last), {i.get('width')}x{i.get('height')}"
                 + (", sound" if i.get("has_audio") else ", no sound")
                 + (f"; its words: build\\speech\\{words[-1].name}" if words else
                    "; words not transcribed yet (tools\\speech.py transcribe)"))
    from motionlab.project import PHOTO_EXT, clip_files
    return L or (["- no video clips - only photos (below)"] if clip_files(p, PHOTO_EXT) else
                 ["- no clips in the folder"])


def edit_brief(p: Path, req: dict) -> list[str]:
    b = p / "build" / "edit_brief.md"
    talking = req.get("sound") == "talk" or str(req.get("prompt") or "").startswith(("script-", "hook-"))
    L = [f"# Brief: {p.name} - an edit of the user's clips", "",
         f"Made by the lab (tools\\brief.py, {time.strftime('%Y-%m-%d %H:%M')}): the request in words (what the app "
         "saved), then the lab's facts - the clips, the references' style, the user's ratings as rules, the lessons. "
         "*Left out* at the end names what is not here.", ""]
    L += [b.read_text(encoding="utf-8").strip() if b.exists() else "(no edit_brief.md: the request is "
          "build\\edit_request.json)", "", "## The clips (the lab measured them; only read)"] + clip_lines(p) \
        + photo_lines(p, req)
    pid = str(req.get("prompt") or "")
    rec = next(iter((KN.LOCAL / "prompts").glob(f"*/{pid}.json")), None) if pid else None
    said = ""
    if rec:
        r = json.loads(rec.read_text(encoding="utf-8"))
        said = str(r.get("text") or "")
        L += ["", f"## The {r.get('kind', 'text')} {pid}: {r.get('title', '')} (the prompt library, word for word)",
              "```", said.strip(), "```"]
    like = req.get("like") or []
    if like:
        L += ["", "## The references' style (tools\\style.py)", "```", tool("style.py", *like), "```"]
    if not req.get("exact"):                                 # a 1:1 copy takes the reference's graphics
        st = req.get("style") or {}
        L += edit_template_lines(p.name, " ".join([str(req.get("want") or ""), str(req.get("about") or ""), *(
            x if isinstance(x, str) else json.dumps(x, ensure_ascii=False) for x in req.get("on_screen") or []),
            str(st.get("type") or ""), " ".join(st.get("moods") or []), said]))
    L += ["", KN.memory_rules(), "", KN.lessons_for("talking" if talking else "all")]
    left = ["Claude's memory beyond the ratings: `knowledge.py memory` (a 1:1 copy of a reference reads it whole)",
            "the request as JSON: build\\edit_request.json",
            "every Motion Graphics template, one line each: `templates.py library --brief`"]
    return L + ["", "## Left out (nothing silently)"] + [f"- {x}" for x in left]


def make(project: str) -> Path:
    p = Path(project)
    p = (p if p.is_dir() else PROJECTS / project).resolve()
    gen, ed = p / "build" / "generate_request.json", p / "build" / "edit_request.json"
    req_p = max((x for x in (gen, ed) if x.exists()), key=lambda x: x.stat().st_mtime, default=None)
    if not req_p:
        raise SystemExit(f"{p.name}: no generate_request.json or edit_request.json in build\\")
    req = json.loads(req_p.read_text(encoding="utf-8"))
    L = generate_brief(p, req) if req_p == gen else edit_brief(p, req)
    out = p / "build" / "brief.md"
    out.write_text("\n".join(L).rstrip() + "\n", encoding="utf-8")
    return out


def main() -> int:
    setup_console()
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 2
    out = make(sys.argv[1])
    print(f"{out} ({out.stat().st_size / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
