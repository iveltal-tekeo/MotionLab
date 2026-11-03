"""An edit's segments, the treatment for each, the user's own picks and the edit built from them (0.6.1, docs\\plans.md
*Edit by segments*, steps 1-7; the rules: motionlab\\segments.py) - the lab; Claude only through --claude.

    .venv\\Scripts\\python tools\\segments.py <project> [plan_vN.json] [--json]
        every segment (frame + timecode, its words or its bars) with its treatment, why, two alternatives, all it can
        have and whose pick it is (the rules' / CLAUDE'S / YOURS), under its topic -> build\\segments_vN.json
    ... [--set 3=broll] [--set 5=graphic:word-pills] [--like 3] [--reset 3 | --reset all]
        the user's own picks (build\\segment_picks.json - kept through any re-run of the draft): a treatment for a
        segment, ":<option>" = which B-roll clip / which template; --like 3 = segment 3's pick on every segment the
        rules treated like it (Apply to all like this); --reset = the suggestion again (Claude's where it made one,
        else the rules'; all = Recommended for all)
    ... --claude build\\segments_claude.json | --reset claude
        step 7 (/recreate-video): Claude's picks and topics - {"picks": [{"n", "t", ("opt"), ("text"), "why"}],
        "topics": [{"n", "name"}]} - checked against these segments, all or nothing, replacing Claude's earlier ones;
        they are the suggestion under the user's picks, which stay. "text" = the word a punch-in / B-roll lands on, or
        a card's words (a title "line 1|line 2", a number's words under it, a list's items "a|b|c", a graphic's main
        words); --reset claude = Claude's picks and topics taken away
    ... --stills | --preview N
        step 5: a picture of each segment (the bare draft at its key frame -> build\\segments\\v<B>\\seg_<n>.jpg);
        segment N alone with its pick, rendered (its graphics too) -> build\\segments\\v<B>\\preview_<N>_<f0>-<f1>.mp4
    ... --request
        the app's New edit > Segments: a bare draft from the saved request (build\\edit_request.json) first, then the
        list and the pictures
    ... --build [--captions clean_box | keyword | classic | none] [--render]
        the edit: on a bare draft (the plan when it is one, else made first - draft_edit.py with the plan's own
        arguments + --bare), every pick as edit-list lines (build\\segments_vB.list) -> draft_edit.py --apply ->
        plan_v<B+1>.json, then the check: every cut where it was, each segment's pick in the plan, nothing added to a
        plain one, the B-roll share. Captions: the request's (New edit's *Captions*), else none. --render = build.py.
A talking edit: the words said in it (each clip's transcript, made when missing - tools\\speech.py); a music edit:
its song's downbeats and drops (cached in build\\draft\\); a montage: its shots. Writes only into the project's build
folder; the clips and the song are only read.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import editlist as EL  # noqa: E402
from motionlab import segments as SG  # noqa: E402
from motionlab.project import Project  # noqa: E402
from motionlab.timecode import frame_to_tc  # noqa: E402
from motionlab.util import LAB, load_config, read_json, setup_console, write_json  # noqa: E402

TOOLS = Path(__file__).resolve().parent
PICKS = "segment_picks.json"
TEXT_MAX, WHY_MAX = 80, 120     # Claude's words on a card / a topic's name, and its why line: at most this long
CARD = ("graphic", "number", "title", "list")                 # the picks with a template ("opt") and words on a card
CAPTION_LOOK = {"words": "clean_box", "key": "keyword"}       # New edit's *Captions* -> the captions look
ACCENT_ON_FOOTAGE = 4.5         # an accent drawn on the footage: at least this contrast with black (WCAG ratio)
SEGDIR = "segments"             # build\segments\v<B>\ = a bare draft's segment pictures and previews
STILL_PX = 360                  # a segment's picture: its long side


def context(prj: Project, P: dict, talking: set, req: dict) -> dict:
    """What the rules and the build can use beyond the segment itself: the B-roll clips' catalogue moments (their
    longest usable part, their subject), the template library, the shots framed as a screen recording, the request's
    style (captions, the brand's / the palette's colours)."""
    from motionlab import catalogue as CT
    from motionlab import templates as TM
    from motionlab.draft import BROLL_MIN_S, stem
    broll, usable = [], {}
    shortest = int(round(BROLL_MIN_S * float(P["fps"])))     # (a moment shorter than an insert: never named)
    srcs = P.get("sources") or {}
    for c in (CT.load(prj) or {}).get("clips", []):
        if c.get("id") not in srcs or int(c.get("frames", 0)) != int(srcs[c["id"]].get("frames", -1)):
            continue                                 # (a catalogue at the plan's frames only)
        usable[c["id"]] = [[int(u0), int(u1)] for m in c.get("moments", []) for u0, u1 in m.get("usable") or []]
        if c.get("id") in talking:
            continue
        for i, m in enumerate(c.get("moments", []), 1):
            s = m.get("say") or {}
            words = {stem(w) for w in " ".join([s.get("what", ""), s.get("where", ""), *s.get("tags", [])]).split()
                     if stem(w)}
            use = max(m.get("usable") or [[0, -1]], key=lambda r: r[1] - r[0])
            if words and use[1] - use[0] + 1 >= shortest:
                sj = m.get("subject") or {}
                broll.append({"clip": c["id"], "m": i, "words": words, "line": s.get("what", ""),
                              "use": [int(use[0]), int(use[1])],
                              "anchor": [float(sj["x"]), float(sj["y"])] if "x" in sj and "y" in sj else None})
    fixed = set(SG.TEMPLATE.values())

    def ranked(words: str, n: int) -> list[dict]:
        try:
            return TM.pick(words, n=n)
        except (OSError, ValueError):
            return []

    def graphic(words: str, used=()):
        t = next((x for x in ranked(words, 8) if x["id"] not in used and x["id"] not in fixed), None)
        return (t["id"], t["score"], t.get("matched") or []) if t and t["score"] >= SG.GRAPHIC_SCORE else None

    def any_graphic(words: str, used=()):
        return next((x["id"] for x in ranked(words, 16) if x["id"] not in used and x["id"] not in fixed), None)
    screen = {f for L in P.get("layers", []) if L.get("type") == "clip"
              and (L.get("reframe") or {}).get("layout") == "screen" for f in range(int(L["start"]), int(L["end"]) + 1)}
    st = req.get("style") or {}
    look = {}
    if st.get("palette"):                            # (the palette's first colour = its accent)
        look["signal"] = st["palette"][0]
    if req.get("brand"):                             # For my brand: its colours by role and its fonts
        from motionlab import brand as BR
        look.update(BR.look_values(req["brand"]))
    if look.get("signal"):                           # over the footage (no card of its own behind it): a dark accent
        from motionlab import brand as BR            # does not read - the brand's light text colour instead
        if BR.contrast(look["signal"], "#000000") < ACCENT_ON_FOOTAGE:
            ink = look.get("ink")
            if ink and BR.contrast(ink, "#000000") >= ACCENT_ON_FOOTAGE:
                look["signal"] = ink
            else:
                look.pop("signal")
    cap = CAPTION_LOOK.get(st.get("captions") or "")
    if cap == "clean_box" and req.get("brand"):
        from motionlab import brand as BR
        cap = (BR.caption_look(req["brand"]) or (cap,))[0]
    return {"broll": broll, "usable": usable, "graphic": graphic, "any_graphic": any_graphic, "screen": screen,
            "fps": float(P["fps"]),
            "frames": int(P["frames"]), "look": look, "captions": cap}


def plans_of(prj: Project) -> list[Path]:
    return sorted(prj.build.glob("plan_v*.json"), key=lambda q: int(re.sub(r"\D", "", q.stem) or 0))


def load_picks(prj: Project) -> dict:
    """build\\segment_picks.json: {"picks": [{"at", "t", ("opt"), ("text"), ("why"), "by" (user - the default -
    | claude)}], "topics": [{"at", "name"}] (Claude's), "claude" {"made", "file"}}."""
    d = (read_json(prj.build / PICKS) or {}) if (prj.build / PICKS).exists() else {}
    return {"picks": list(d.get("picks") or []), "topics": list(d.get("topics") or []), "claude": d.get("claude") or {}}


def save_picks(prj: Project, F: dict) -> None:
    write_json(prj.check(prj.build / PICKS), {
        "v": 1, "picks": F["picks"], "topics": F.get("topics") or [],
        **({"claude": F["claude"]} if F.get("claude") else {}),
        "note": "the user's own treatment per segment, and Claude's (\"by\": claude - the suggestion under the user's) "
                "(tools\\segments.py): \"at\" = where its segment starts in its clip / song"})


def by_user(p: dict) -> bool:
    return p.get("by", "user") == "user"


def analyse(prj: Project, pp: Path, write: bool = True) -> dict:
    """The plan's segments, its context and every pick (the rules', Claude's, the user's) and topic -> {"doc", "P",
    "ctx", "lost" (the user's picks that found no segment), "v"}; writes build\\segments_vN.json."""
    from motionlab.compose import resolve_paths
    from motionlab import miniedit as ME
    P = resolve_paths(json.loads(pp.read_text(encoding="utf-8")), prj.build)
    fps, N = float(P["fps"]), int(P["frames"])
    t0 = time.time()
    shots = EL.shots(P)
    talking = {L.get("src") for L in shots} if (P.get("made_by") or {}).get("sound") == "talk" else set()
    kind, segs, lang, note, beats, song_s = "clips", [], "en", "", [], 0.0
    if talking:
        import draft_edit as DE
        import speech as SPT
        words = sorted((w for ln in DE.edit_words(prj, P, fps)["lines"] for w in ln["words"]), key=lambda w: w["t"])
        if words:
            kind, segs = "talk", SG.talk(words, fps, N, [int(L["start"]) for L in shots[1:]])
            src = Path(str((P["sources"].get(next(iter(talking))) or {}).get("source", "")))
            lang = (SPT.transcript(src)[1].get("lang") or "en") if src.is_file() else "en"
        else:
            note = "no words said in it (no transcript): its shots instead"
    song = ME.song_source(P) if not segs and ME.sound_mode(P) == "song" else None   # (a song under it: not the
    if song is not None and song.is_file():                                          # clips' own sound)
        import draft_edit as DE
        d = prj.check(prj.build / "draft")
        d.mkdir(parents=True, exist_ok=True)         # (a hand-made plan's project may have none yet)
        try:
            info = DE.music_info(prj, d, song, fps, load_config())
        except SystemExit as e:
            info = {"downbeats": [], "note": str(e)}
        song_s = ME.song_start(P)
        sf = song_s * fps
        if info.get("downbeats"):
            kind = "music"
            segs = SG.music([round(f - sf) for f in info["downbeats"]], [round(f - sf) for f in info.get("drops", [])],
                            fps, N, info.get("bpm"))
            beats = [round(f - sf) for f in info.get("beats", []) if 0 < f - sf < N]
        else:
            note = f"its song has no beats found ({info.get('note') or 'none'}): its shots instead"
    if not segs:
        kind, segs = "clips", SG.clips([(int(L["start"]), int(L["end"])) for L in shots], fps, N)
    for s in segs:
        s["at"] = SG.anchor(P, s, song_s)
    req = (read_json(prj.build / "edit_request.json") or {}) if (prj.build / "edit_request.json").exists() else {}
    ctx = {**context(prj, P, talking, req), "beats": beats}
    F = load_picks(prj)
    mine, lost = SG.mine_for(segs, [p for p in F["picks"] if by_user(p)], fps)
    cl, cl_lost = SG.mine_for(segs, [p for p in F["picks"] if not by_user(p)], fps)
    tops, tp_lost = SG.mine_for(segs, F["topics"], fps)
    for s in segs:
        if s["n"] in tops:
            s["topic"] = tops[s["n"]]["name"]
    SG.recommend(segs, ctx, lang, mine, cl)
    v = re.sub(r"\D", "", pp.stem) or "0"
    doc = {"plan": pp.name, "kind": kind, "fps": fps, "frames": N, "lang": lang, "made": time.strftime("%Y-%m-%d %H:%M"),
           "bare": bool((P.get("made_by") or {}).get("bare")), "treatments": SG.TREATMENTS,
           "picks_lost": len(lost), "claude_lost": len(cl_lost) + len(tp_lost), "claude": F["claude"],
           "segments": segs, "note": note, "seconds": round(time.time() - t0, 1)}
    if write:
        write_json(prj.check(prj.build / f"segments_v{v}.json"), doc)
    return {"doc": doc, "P": P, "ctx": ctx, "lost": lost, "v": v}


def change_picks(prj: Project, R: dict, sets: list[str], like: list[int], reset: list[str]) -> list[str]:
    """--set / --like / --reset on build\\segment_picks.json (the user's layer; --reset claude = Claude's); each change
    in one line (or an error line)."""
    from motionlab import miniedit as ME
    segs = {s["n"]: s for s in R["doc"]["segments"]}
    F, done = load_picks(prj), []
    picks = F["picks"]
    fps = R["doc"]["fps"]
    sug = lambda s: (f"Claude's: {s['claude']['t']}" if s.get("claude") else f"the rules': {s['rule']['t']}")  # noqa: E731

    def put(s, t, opt=None):
        nonlocal picks
        picks = [p for p in picks if not by_user(p) or (d := SG._apart(p.get("at") or {}, s["at"], fps)) is None
                 or d > SG.PICK_NEAR_S]                  # (this part's own pick goes; 0 apart is the same part)
        if t is not None:
            picks.append({"at": s["at"], "t": t, **({"opt": opt} if opt else {}), "by": "user", "say": s["say"][:60],
                          "made": time.strftime("%Y-%m-%d %H:%M")})
    for r in reset:
        if r == "all":
            n = sum(1 for p in picks if by_user(p))
            picks = [p for p in picks if not by_user(p)]
            done.append(f"Recommended for all: {n} pick(s) of yours taken back")
        elif r == "claude":
            n = len(picks) - sum(1 for p in picks if by_user(p))
            done.append(f"Claude's {n} pick(s) and {len(F['topics'])} topic(s) taken away (the user's stay)")
            picks, F["topics"], F["claude"] = [p for p in picks if by_user(p)], [], {}
        elif r.isdigit() and int(r) in segs:
            put(segs[int(r)], None)
            done.append(f"segment {r}: the suggestion again ({sug(segs[int(r)])})")
        else:
            done.append(f"ERROR --reset {r}: no segment {r} (1-{len(segs)}) and not 'all' / 'claude'")
    for x in sets:
        m = re.fullmatch(r"(\d+)=([a-z]+)(?::(\S+))?", x.strip())
        if not m or int(m[1]) not in segs:
            done.append(f"ERROR --set {x}: write it as <segment>=<treatment>[:<clip or template>], segment 1-{len(segs)}")
            continue
        s, t, opt = segs[int(m[1])], m[2], m[3]
        if t not in s["can"]:
            done.append(f"ERROR --set {x}: segment {s['n']} can have {', '.join(s['can'])}")
            continue
        if opt and t == "broll" and opt not in (R["P"].get("sources") or {}):
            done.append(f"ERROR --set {x}: no clip {opt} in this edit ({', '.join(sorted(R['P']['sources']))})")
            continue
        if opt and t in ("graphic", "number", "title", "list") and ME.template_folder(opt) is None:
            done.append(f"ERROR --set {x}: no template {opt} (tools\\templates.py read)")
            continue
        put(s, t, opt)
        done.append(f"segment {s['n']}: {t}" + (f" ({opt})" if opt else "") + f" - yours (the suggestion: {sug(s)})")
    for n in like:
        if n not in segs:
            done.append(f"ERROR --like {n}: no segment {n}")
            continue
        s = segs[n]
        alike = SG.like(R["doc"]["segments"], n)
        for k in alike:
            put(segs[k], s["pick"], s.get("opt"))
        done.append(f"like segment {n} ({s['pick']}): segment(s) {', '.join(map(str, alike)) or 'none'} - the ones the "
                    f"rules gave {s['rule']['t']}")
    if any(ln.startswith("ERROR") for ln in done):   # all or nothing
        return done + ["nothing changed"]
    F["picks"] = picks
    save_picks(prj, F)
    return done


def claude_layer(prj: Project, R: dict, src: Path) -> list[str]:
    """--claude <file> (step 7, /recreate-video): Claude's picks and topics, checked against these segments - all or
    nothing - then they replace Claude's earlier ones whole; the user's picks stay on top. Each in one line (or an
    error line saying what the segment can have)."""
    from motionlab import miniedit as ME
    segs = {s["n"]: s for s in R["doc"]["segments"]}
    try:
        J = json.loads(src.read_text(encoding="utf-8"))
        if not isinstance(J, dict):
            raise ValueError("not {\"picks\": [...], \"topics\": [...]}")
    except (OSError, ValueError) as e:
        return [f"ERROR --claude {src}: {e}", "nothing changed"]
    out, picks, topics, seen = [], [], [], set()
    srcs = R["P"].get("sources") or {}
    one = lambda x: " ".join(str(x or "").split())                         # noqa: E731
    for x in J.get("picks") or []:
        x = x if isinstance(x, dict) else {}
        n, t, opt, text, why = x.get("n"), str(x.get("t") or ""), x.get("opt"), one(x.get("text")), one(x.get("why"))
        s = segs.get(n) if isinstance(n, int) else None
        err = (f"no segment {n} (1-{len(segs)})" if s is None else f"segment {n} twice" if n in seen else
               f"segment {n} can have {', '.join(s['can'])}" if t not in s["can"] else
               f"its why: one line of at most {WHY_MAX} characters" if not why or len(why) > WHY_MAX else
               f"its text: at most {TEXT_MAX} characters" if len(text) > TEXT_MAX else
               "an option only for broll (a clip) or a card (a template)" if opt and t not in ("broll", *CARD) else
               f"no clip {opt} in this edit ({', '.join(sorted(srcs))})" if opt and t == "broll" and opt not in srcs
               else f"no template {opt} (tools\\templates.py read)" if opt and t in CARD and
               ME.template_folder(str(opt)) is None else
               f"no words on a {t}" if text and t not in ("punch", "broll", *CARD) else
               f"\"{text}\" is no word said in segment {n}" if text and t in ("punch", "broll")
               and SG.word_at(s, text) is None else None)
        if err:
            out.append(f"ERROR pick {json.dumps(x, ensure_ascii=False)[:120]}: {err}")
            continue
        seen.add(n)
        picks.append({"at": s["at"], "t": t, **({"opt": str(opt)} if opt else {}), **({"text": text} if text else {}),
                      "why": why, "by": "claude", "say": s["say"][:60], "made": time.strftime("%Y-%m-%d %H:%M")})
        out.append(f"segment {n}: {t}" + (f" ({opt})" if opt else "") + (f" \"{text}\"" if text else "") + " - Claude's"
                   + (f" (the user's {s['pick']} stays on top - yours is the suggestion under it)"
                      if s["by"] == "user" else ""))
    tops = set()
    for x in J.get("topics") or []:
        x = x if isinstance(x, dict) else {}
        n, name = x.get("n"), one(x.get("name"))
        err = (f"no segment {n} (1-{len(segs)})" if not isinstance(n, int) or n not in segs else
               f"segment {n} starts two topics" if n in tops else
               f"its name: at most {TEXT_MAX} characters" if not name or len(name) > TEXT_MAX else None)
        if err:
            out.append(f"ERROR topic {json.dumps(x, ensure_ascii=False)[:120]}: {err}")
            continue
        tops.add(n)
        topics.append((n, {"at": segs[n]["at"], "name": name}))
        out.append(f"topic from segment {n}: {name}")
    if any(ln.startswith("ERROR") for ln in out):
        return out + ["nothing changed"]
    F = load_picks(prj)
    F["picks"] = [p for p in F["picks"] if by_user(p)] + picks
    F["topics"] = [tp for _, tp in sorted(topics, key=lambda x: x[0])]
    F["claude"] = {"made": time.strftime("%Y-%m-%d %H:%M"), "file": src.name}
    save_picks(prj, F)
    return out + [f"Claude's layer: {len(picks)} pick(s), {len(topics)} topic(s) - the earlier ones replaced"]


def args_of(prj: Project, P: dict, pp: Path) -> list[str]:
    """A quick draft's own arguments (its made_by "args", else its notes' *Arguments* line) without the project."""
    a = list((P.get("made_by") or {}).get("args") or [])
    if a:
        return a[1:]
    v = re.sub(r"\D", "", pp.stem)
    md = prj.build / f"draft_v{v}.md"
    m = re.search(r"^- Arguments: `(.*)`$", md.read_text(encoding="utf-8"), re.M) if md.exists() else None
    if not m:
        raise SystemExit(f"{pp.name}: its draft's arguments are not recorded - make a bare draft "
                         f"(draft_edit.py \"{prj.name}\" <its style> --bare), then --build on it")
    rest = m[1][len(prj.name):] if m[1].startswith(prj.name) else m[1].split(" ", 1)[-1]
    out = []
    for part in re.split(r"\s+(?=--)", rest.strip()):
        k, _, val = part.partition(" ")
        out += [k] + ([val.strip()] if val.strip() else [])
    return out


def run(cmd: list[str], ok: tuple = (0,)) -> str:
    r = subprocess.run([sys.executable, *cmd], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=str(LAB))
    if r.returncode not in ok:
        raise SystemExit(f"{Path(cmd[0]).name} failed:\n{(r.stdout + r.stderr)[-1500:]}")
    return r.stdout


def seg_dir(prj: Project, v: str) -> Path:
    """build\\segments\\v<B>\\: a bare draft's segment pictures (stills.json) and previews (previews.json)."""
    d = prj.check(prj.build / SEGDIR / f"v{v}")
    d.mkdir(parents=True, exist_ok=True)
    return d


def make_stills(prj: Project, pp: Path, doc: dict) -> dict:
    """Step 5: a picture of each segment - the bare draft's frame at its key frame (render_video.py --stills, from the
    light cache) -> build\\segments\\v<B>\\seg_<n>.jpg (STILL_PX on its long side) + stills.json {n: {"f", "file"}}."""
    from PIL import Image
    segs = doc["segments"]
    run([str(TOOLS / "render_video.py"), str(pp), "--stills", ",".join(str(f) for f in sorted({s["key"] for s in segs}))])
    name = json.loads(pp.read_text(encoding="utf-8")).get("name", pp.stem)
    v = re.sub(r"\D", "", pp.stem)
    out, idx = seg_dir(prj, v), {}
    for s in segs:
        im = Image.open(prj.build / "stills" / f"{name}_f{s['key']:05d}.png").convert("RGB")
        im.thumbnail((STILL_PX, STILL_PX))
        im.save(out / f"seg_{s['n']}.jpg", quality=85)
        idx[str(s["n"])] = {"f": s["key"], "file": f"{SEGDIR}/v{v}/seg_{s['n']}.jpg"}
    write_json(out / "stills.json", {"plan": pp.name, "made": time.strftime("%Y-%m-%d %H:%M"), "stills": idx})
    return idx


def prepare(prj: Project) -> Path:
    """--request (the app's New edit > Segments): a bare quick draft from the saved request (build\\edit_request.json:
    its style, sound, length, format and framing - editreq.draft_args, as the quick draft job reads it) -> its plan."""
    from motionlab import editreq as ER
    rq = prj.build / "edit_request.json"
    if not rq.exists():
        raise SystemExit(f"no request in {prj.build} - New edit saves one")
    try:
        args = ER.draft_args(read_json(rq) or {})
    except ValueError as e:
        raise SystemExit(str(e))
    out = run([str(TOOLS / "draft_edit.py"), prj.name, *[x for x in args if x != "--render"], "--bare"])
    return Path(out.strip().splitlines()[-1])


def preview(prj: Project, pp: Path, n: int) -> int:
    """--preview N (step 5, *Preview this segment*): segment N alone with its pick - its lines on the bare draft as a
    plan that is no version (build\\segpreview_v<B>_s<N>.json, draft_edit.py --apply --out), its graphics rendered
    and moved off the faces, then that part rendered (render_video.py --range) -> build\\segments\\v<B>\\preview_<N>_*.mp4
    + previews.json {n: {"t", "opt", "file"}} (the pick it shows: a changed pick makes it stale)."""
    from motionlab import facefit as FF
    R = analyse(prj, pp, write=False)
    doc, P = R["doc"], R["P"]
    s = next((x for x in doc["segments"] if x["n"] == n), None)
    if not doc["bare"] or s is None:
        print(f"ERROR: {'no segment ' + str(n) if doc['bare'] else pp.name + ' is no bare draft'} - "
              f"segments.py \"{prj.name}\" --build makes one")
        return 2
    lines, _ = SG.build_list(doc["segments"], P, {**R["ctx"], "captions": None}, doc["lang"])
    i = next(k for k, ln in enumerate(lines) if ln.startswith(f"# {n}. "))
    block = lines[i:next((k for k in range(i + 1, len(lines)) if not lines[k]), len(lines))]
    v = R["v"]
    d = seg_dir(prj, v)
    lst = d / f"preview_{n}.list"
    lst.write_text("\n".join(block) + "\n", encoding="utf-8")
    name = f"segpreview_v{v}_s{n}"
    run([str(TOOLS / "draft_edit.py"), prj.name, "--apply", str(lst), "--base", pp.name, "--out", f"{name}.json"])
    plan_p = prj.build / f"{name}.json"
    plan = json.loads(plan_p.read_text(encoding="utf-8"))
    cards = [L for L in plan["layers"] if L.get("type") == "overlay" and str(L.get("id", "")).startswith(name)]
    for L in cards:
        L["clear_face"] = True
        f = Path(L["file"]) if Path(L["file"]).is_absolute() else prj.build / L["file"]
        run([str(TOOLS / "overlay.py"), "render", str(f.parent)])
    if cards:
        FF.fit_cards(plan, prj.build)
    write_json(plan_p, plan)
    run([str(TOOLS / "render_video.py"), str(plan_p), "--range", str(s["f0"]), str(s["f1"]),   # (again: over its file)
         "--out", str(d / f"preview_{n}.mp4")])
    mp4 = d / f"preview_{n}_{s['f0']}-{s['f1']}.mp4"
    idx = read_json(d / "previews.json") or {} if (d / "previews.json").exists() else {}
    idx[str(n)] = {"t": s["pick"], "opt": s.get("opt"), "text": s.get("text"), "file": f"{SEGDIR}/v{v}/{mp4.name}",
                   "made": time.strftime("%Y-%m-%d %H:%M")}
    write_json(d / "previews.json", idx)
    print(f"segment {n} f{s['f0']}-f{s['f1']} ({frame_to_tc(s['f0'], doc['fps'])}-{frame_to_tc(s['f1'], doc['fps'])}): "
          f"{s['pick']} ({s['why']})")
    print(mp4)
    return 0


def build(prj: Project, pp: Path, captions: str | None, render: bool) -> int:
    """--build (the module's docstring)."""
    P0 = json.loads(pp.read_text(encoding="utf-8"))
    mb = P0.get("made_by") or {}
    up = prj.build / str(mb.get("from") or "-")      # (an edit built from a bare draft: built again on that one)
    if mb.get("bare"):
        base_p = pp
    elif up.is_file() and (json.loads(up.read_text(encoding="utf-8")).get("made_by") or {}).get("bare"):
        base_p = up
        print(f"{pp.name} was built on the bare {up.name}: built again on it")
    elif mb.get("tool") == "draft_edit.py":
        skip = {"--render", "--bare", "--feel-test"}
        args = [x for x in args_of(prj, P0, pp) if x not in skip]
        print(f"{pp.name} has effects of its own: a bare draft of it first (the same cuts, sound, colour and framing)")
        out = run([str(TOOLS / "draft_edit.py"), prj.name, *args, "--bare"])
        base_p = Path(out.strip().splitlines()[-1])
    else:
        print(f"ERROR: {pp.name} was made by {mb.get('tool') or 'hand'} - the build starts from a quick draft "
              f"(draft_edit.py \"{prj.name}\" <its style> --bare)")
        return 2
    R = analyse(prj, base_p)
    doc, P = R["doc"], R["P"]
    ctx = dict(R["ctx"])
    if captions:
        ctx["captions"] = None if captions == "none" else captions
    if doc["kind"] != "talk":
        ctx["captions"] = None                       # (captions are the words said)
    lines, claims = SG.build_list(doc["segments"], P, ctx, doc["lang"])
    fps = doc["fps"]
    head = [f"# Edit by segments: {len(doc['segments'])} segments of {base_p.name} ({doc['kind']}), one block each - "
            f"tools\\segments.py {time.strftime('%Y-%m-%d %H:%M')}",
            "# The words on its cards: Claude's where it wrote them, else the rules' (the number and what follows it, "
            "the part's first words or its topic, the items counted) - change them in the Editor"]
    lst = prj.check(prj.build / f"segments_v{R['v']}.list")
    lst.write_text("\n".join(head + lines) + "\n", encoding="utf-8")
    out = run([str(TOOLS / "draft_edit.py"), prj.name, "--apply", str(lst), "--base", base_p.name])
    new_p = Path(out.strip().splitlines()[-1])
    built = json.loads(new_p.read_text(encoding="utf-8"))
    nv = re.sub(r"\D", "", new_p.stem)
    for L in built["layers"]:                        # its cards: moved off the faces once rendered (build.py)
        if L.get("type") == "overlay" and str(L.get("id", "")).startswith(f"v{nv}_") and not str(
                L.get("id", "")).startswith("captions_"):
            L["clear_face"] = True
    write_json(new_p, built)
    V = SG.verify(json.loads(base_p.read_text(encoding="utf-8")), built, claims)
    write_json(prj.check(prj.build / f"segments_v{nv}.json"),
               {**doc, "plan": new_p.name, "built_from": base_p.name, "list": lst.name, "check": V["lines"],
                "check_ok": V["ok"], "broll_share": V["broll_share"], "made": time.strftime("%Y-%m-%d %H:%M")})
    from motionlab.draft import BROLL_COVER
    print(f"{base_p.name} + {lst.name} -> {new_p.name}: {len(doc['segments'])} segments, "
          f"{sum(1 for s in doc['segments'] if s['by'] == 'user')} of them your picks, "
          f"{sum(1 for s in doc['segments'] if s['by'] == 'claude')} Claude's")
    for s, ln in zip(doc["segments"], V["lines"][-len(claims):]):
        print(f"  f{s['f0']}-f{s['f1']} ({frame_to_tc(s['f0'], fps)}-{frame_to_tc(s['f1'], fps)}) {ln}")
    for ln in V["lines"][:-len(claims)]:
        print(f"  {ln}")
    print(f"  B-roll covers {V['broll_share']:.0%} of the edit (the draft's ceiling {BROLL_COVER:.0%})"
          + (" - over it, by your picks" if V["broll_share"] > BROLL_COVER else ""))
    print(f"check: {'every segment as picked, every cut where it was' if V['ok'] else 'NOT as picked - see above'}")
    if R["lost"]:
        print(f"  {len(R['lost'])} pick(s) of yours found no segment in this edit (kept in {PICKS})")
    if render:                                       # (build.py 2 = built, its precheck flags something to look at)
        print(run([str(TOOLS / "build.py"), prj.name, new_p.name], ok=(0, 2)).strip().splitlines()[-1])
    else:
        print(f"next: .venv\\Scripts\\python tools\\build.py \"{prj.name}\" {new_p.name}")
    print(new_p)
    return 0 if V["ok"] else 1


def table(doc: dict) -> list[str]:
    """The segments as lines (the console, the brief): frame + timecode, its pick and whose, why, two alternatives,
    all it can have, every word said; a topic's name above its first segment."""
    fps = doc["fps"]
    tc = lambda f: frame_to_tc(f, fps)                                      # noqa: E731
    out = []
    for s in doc["segments"]:
        if s.get("topic"):
            out.append(f"    -- topic: {s['topic']} --")
        sg = s.get("claude") or s["rule"]
        who = {"user": f" YOURS (the suggestion: {sg['t']})", "claude": " CLAUDE'S"}.get(s["by"], "")
        alts = ", ".join(f"{x['t']} ({x['why']})" for x in s["alts"])
        out.append(f"{s['n']:>2}. f{s['f0']}-f{s['f1']} ({tc(s['f0'])}-{tc(s['f1'])}) {(s['f1'] - s['f0'] + 1) / fps:4.1f} s"
                   f"  [{s['pick']}{':' + s['opt'] if s.get('opt') else ''}]{who}"
                   + (f" \"{s['text']}\"" if s.get("text") else "") + f" {s['why']}")
        out.append(f"      or: {alts}; can: {', '.join(s['can'])}")
        out.append(f"      {s['say']}")
    return out


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("plan", nargs="?")
    ap.add_argument("--json", action="store_true", help="print the JSON instead of the table")
    ap.add_argument("--set", action="append", default=[], help="a pick of yours: 3=broll, 5=graphic:word-pills")
    ap.add_argument("--like", action="append", type=int, default=[], help="segment N's pick on the ones like it")
    ap.add_argument("--reset", action="append", default=[], help="N = the suggestion again; all = for every one; "
                                                                 "claude = Claude's picks and topics taken away")
    ap.add_argument("--claude", metavar="FILE", help="Claude's picks and topics (/recreate-video): a JSON file")
    ap.add_argument("--build", action="store_true", help="the edit from the picks (on a bare draft)")
    ap.add_argument("--captions", help="--build: a captions look (clean_box, keyword, classic) or none")
    ap.add_argument("--render", action="store_true", help="--build: build.py on the new plan")
    ap.add_argument("--request", action="store_true", help="a bare draft from New edit's request first, then the list "
                                                           "and a picture of each segment")
    ap.add_argument("--stills", action="store_true", help="a picture of each segment (build\\segments\\v<N>\\)")
    ap.add_argument("--preview", type=int, metavar="N", help="segment N alone with its pick, rendered small")
    a = ap.parse_args()
    prj = Project(a.project)
    plans = plans_of(prj)
    pp = prepare(prj) if a.request else prj.build / a.plan if a.plan else (plans[-1] if plans else None)
    if pp is None or not pp.is_file():
        print(f"ERROR: no plan {a.plan or ''} in {prj.build} - a quick draft first (draft_edit.py {prj.name} ...)")
        return 2
    if a.preview:
        return preview(prj, pp, a.preview)
    if a.claude:
        src = Path(a.claude)
        src = src if src.is_file() else prj.build / src.name
        lines = claude_layer(prj, analyse(prj, pp, write=False), src)
        print("\n".join(lines))
        if any(ln.startswith("ERROR") for ln in lines):
            return 2
    if a.set or a.like or a.reset:
        bad = False
        for ln in change_picks(prj, analyse(prj, pp, write=False), a.set, a.like, a.reset):
            print(ln)
            bad = bad or ln.startswith("ERROR")
        if bad:
            return 2
    if a.build:
        return build(prj, pp, a.captions, a.render)
    R = analyse(prj, pp)
    doc = R["doc"]
    if a.request or a.stills:
        make_stills(prj, pp, doc)
    if a.json:
        print(json.dumps(doc, ensure_ascii=False))
        return 0
    fps, segs = doc["fps"], doc["segments"]
    note = f" ({doc['note']})" if doc["note"] else ""
    print(f"{prj.name} {pp.name}: {len(segs)} segment(s), {doc['kind']}, words in {doc['lang']}, {doc['frames']} frames "
          f"at {fps:g} fps - {doc['seconds']:.1f} s{note}"
          + ("" if doc["bare"] else " - not a bare draft: --build makes one first"))
    print("\n".join(table(doc)))
    if R["lost"]:
        print(f"{len(R['lost'])} pick(s) of yours found no segment in this edit (kept in build\\{PICKS})")
    if doc["claude_lost"]:
        print(f"{doc['claude_lost']} of Claude's picks / topics found no segment in this edit (kept in build\\{PICKS})")
    print(f"-> {prj.build / ('segments_v' + R['v'] + '.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
