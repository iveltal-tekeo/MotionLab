"""The Editor (0.6.0 step 6; the user, 2026-10-25: "a mini-editor so we can handle small cuts or edits without having
to re-run the entire program under claude"; 2026-10-26: "call it just editor ... an actual editor where i can select
clips, move them around, trim at my own liking ... add sfx to my liking, maybe remove a design and add a template from
our motion graphics template with the color of my liking, maybe add slow/speed to some clips"): a made video changed by
hand on its page, no Claude window - a timeline in the style of the open-source editors (OpenCut / CapCut's magnetic
main track: the shots always close up; graphics on lanes above it, sounds below; split at the playhead; Shotcut /
Kdenlive's ripple delete and light proxy copies for the preview). This module is the engine - pure plan changes, no
tool run; tools\\miniedit.py saves them (the next plan, the sound cut again, the graphics' copies and new ones, one
build) and makes the preview copies; the app's *Editor* tab draws `state()`.

    state(plan) -> what the page draws and plays: the shots (frames, where in their clip, speed, the room their clip
        has before / after), every graphic layer (its folder, frames, words, colours, settings), the captions, the
        sound effects (sfx.plan_cues - the effects', the graphics' and the plan's own - with the recorded sound the
        build will use), the drawing order for the live preview, the sound's mode
    apply(plan, ops, tag, copies, build) -> (the new plan, a line per change with frame + timecode, the tool steps to
        run) - the operations IN ORDER, each on the plan the ones before it made; layers are named by their id in the
        state the page drew (ids made unique first: `unique_ids`), sound effects by their frame and kind

Operations ({"op": ...}):
  the main track (the shots; what comes after always moves up or on - ripple):
    trim    {"shot": id, "side": "start" | "end", "by": n}   n < 0 = shorter, n > 0 = longer (more of its own clip)
    delete  {"shot": id}                                     the shot goes, what comes after closes up
    roll    {"shot": id, "by": n}                            the cut after this shot moves n frames (the length stays)
    move    {"shot": id, "to": k}                            the shot to place k (0 = first) in the order
    split   {"shot": id, "at": f}                            two shots: f = the first frame of the second
    speed   {"shot": id, "speed": x}                         SPEED_MIN..SPEED_MAX, the same part of its clip in
                                                             1/x the frames (its sound stretched, the pitch kept)
    slip    {"shot": id, "by": n}                            another moment of its clip in the same frames: n frames
                                                             later in it (< 0 = earlier) - its caption piece too
    take    {"shot": id, "src": clip, "in": f}               another clip of the video (the plan's "sources") in its
                                                             place, from the clip's frame f, the same length; the
                                                             captions said in the old take go
    shotdup {"shot": id}                                     the shot again right after itself (2026-10-27, the
                                                             timeline's right-click Duplicate): its part of its clip,
                                                             zoom, moves, keys and effects; what comes after moves on
    clipadd {"src": clip, "in": f, "len": n, "to": k}        a clip of the video as a new shot at place k: n frames
                                                             from its frame f (a photo: held); the rest moves on
    volume  {"shot": id, "db": d}                            its own sound louder / softer (VOL_MIN..VOL_MAX dB,
                                                             VOL_MIN = muted; after the voice is levelled) - the
                                                             clip's "sound_db"
  the song (a video whose sound is a song):
    song    {"start": s, "db": d}                            the video starts s seconds into the song, the song d dB
                                                             louder / softer - the plan's audio "cut" {from, start_s,
                                                             db}; on save a copy cut from the song (step "songcut")
  graphics (any overlay layer; a captions piece too):
    gmove   {"layer": id, "by": n}                           n frames later (< 0 = earlier)
    gtrim   {"layer": id, "side": "start" | "end", "by": n}  a later start cuts its first frames; an earlier one
                                                             holds its first frame; an end past its own length holds
                                                             its last frame
    gdelete {"layer": id, "all": bool}                       the layer (all = every layer of that graphic)
    gfit    {"layer": id, "key": k, "value": bool}           0.6.1, the graphic part of the shot (compose's keys):
                                                             behind (behind me, moves with the camera), glass (the room
                                                             frosted under it + a shadow), guard (off the face), pin
                                                             (pinned to the face); the footage's grain with any of them
    gadd    {"id": new id, "template": tid, "f": f, "len": n, "values": {...}}   a Motion Graphics template as a new
                                                             graphic over everything (its own copy on save)
    set     {"graphic": layer id, "key": setting, "value": v}   any setting (words, a colour ...) - in a copy of the
                                                             graphic (<folder>_<tag>), never the one an older version
                                                             shows ("words" = the same, the 0.6.0 first part's name)
    caption {"graphic": layer id, "cue": n, "text": t}       a caption's words in the same frames ("" = it goes)
    capmove {"graphic": layer id, "cue": n, "by": n}          a caption n frames later / earlier (its words with it)
    captrim {"graphic": layer id, "cue": n, "side": "start" | "end", "to": f}   a caption starts / ends on frame f
                                                             (its words keep their share) - both inside the shot it
                                                             is said in, never over the captions beside it
    capsplit {"graphic": layer id, "cue": n, "at": f}        a caption cut in two: f = the second one's first frame
    capmerge {"graphic": layer id, "cue": n}                 caption n and the one after it as one (said in the same
                                                             shot; each word keeps its frames)
    captions {"edits": [{"graphic": id, "cue": n, "text": t}, ...]}   many captions' words at once (the captions list's
                                                             find & replace, its case) - one change
    capadd  {"graphic": layer id, "at": f, "text": t}        a new caption from f (up to 1.5 s, up to the next one)
                                                             (captions are numbered as the state before the op has
                                                             them; the whole list is written on save: step "capfile")
    look    {"graphic": layer id, "look": id}                a ready-made look (presets.json): all its values
  effects (motionlab\\edfx): fxadd / fxmove / fxset / fxremove
  keyframes on a shot (motionlab\\edkeys - zoom, x, y, rotation, opacity, the zoom point):
    kset / kadd / kdel / kmove / kease / kreset {"shot": id, "prop": p | "props": [..], "f": f, ...}
  transitions on a plain cut (motionlab\\edtrans; stored on the shot after the cut, its helper layers stripped first
  and made again last, so no shot op ever breaks one):
    trans    {"shot": id, "kind": k | null, "len": n, "dir": d}    transall {"kind": k | null, "len": n, "dir": d}
  sound effects:
    sfx     {"f": f, "kind": k, "to": f2 | null, "db": d, "sound": file}   moved to f2 / dropped (null) / louder or
                                                             softer (-12..12 dB) / another recorded sound - the plan's
                                                             "sfx" "edits" (sfx.plan_cues applies them last)
    sfxadd  {"f": f, "kind": k, "sound": file | null, "db": d}   a sound effect of its own (the plan's "cues")

What moves with a shot (the page shows it as "moves with it"):
  - attached = a layer over exactly the shot's frames that has an "in" (a caption piece or a corner graphic cut with
    the shot): it changes exactly like the shot (its speed too)
  - pinned = a graphic that starts where the shot starts (it keeps its start and its own first frames: an intro is
    never cut off) or ends where it ends (it keeps its length and its exit)
  - a moved shot takes every layer and sound that STARTS on its frames with it; a sped-up / slowed shot moves the
    starts on its frames with its picture; every other layer keeps its length and moves with the frame it starts on
  - the sound follows the shots when the plan's sound is the clips' own ("follows": cut again on save), a song stays
    as it is ("song"), and a sound made some other way cannot be cut again ("fixed": the shots' timing is locked)
"""
from __future__ import annotations

import copy
import json
import math
import re
from pathlib import Path

from . import edfx as FX
from . import edkeys as KF
from . import editlist as EL
from . import edtrans as TR
from . import safezones as SZ
from . import i18n as I18N
from .timecode import frame_to_tc

SAY_KEYS = ("text", "title", "words", "headline", "line", "caption", "label", "quote", "name", "top", "main",
            "bottom", "tagline", "button", "cta", "price", "what", "subtitle", "heading", "hook")
SPEED_MIN, SPEED_MAX = 0.25, 4.0                # the slowest / fastest a shot plays (CapCut's usual chips' range)
SHOT_OPS = ("trim", "delete", "roll", "move", "split", "speed", "volume", "slip", "take", "clipadd", "shotdup")
VOL_MIN, VOL_MAX = -60.0, 12.0                  # a shot's own sound (dB; VOL_MIN = muted)
SONG_DB = (-24.0, 12.0)                         # the song's volume (dB)
FX_OPS = ("fxadd", "fxmove", "fxset", "fxremove")      # the effects (motionlab\edfx): a transition removed moves a cut
TR_OPS = ("trans", "transall")                          # transitions on cuts (motionlab\edtrans)
VALUES_KEY, CAPTIONS_KEY, NEW_KEY = "_me_values", "_me_captions", "_me_new"     # the engine's own, never saved
PROXY_SHORT, PROXY_GOP = 540, 12                # the preview copies' short side and key-frame distance (fast seeks)
MIN_CAP = 3                                     # a caption's shortest length (its graphic's frames) when trimmed
SCENE_HOLD_S = 10                               # a scene (a video made from zero) longer than its graphic: held


def media_key(src: Path, fps: float) -> str:
    """A clip's preview copy's name part: the clip's path, size, time and the plan's rate (a new copy when one
    changes)."""
    import hashlib
    st = Path(src).stat()
    return hashlib.sha1(f"{src}|{st.st_size}|{st.st_mtime_ns}|{fps:g}|{PROXY_SHORT}".encode()).hexdigest()[:10]


class EditError(ValueError):
    pass


# ------------------------------------------------------------------------------------------------- reading a plan
def shots(plan: dict) -> list[dict]:
    """The main track: the shots (editlist's), else a video made from zero's scenes."""
    return EL.shots(plan) or scenes(plan)


def scenes(plan: dict) -> list[dict]:
    """A video made from zero (no clips: the Generator's draft, its HyperFrames scenes): its full-frame graphics back
    to back from frame 0 to its last - the Editor's main track, reordered / trimmed / split like shots. [] when they
    do not tile the video (one composition over it all: its scenes are inside it)."""
    W, H, N = int(plan.get("width") or 0), int(plan.get("height") or 0), int(plan.get("frames") or 0)
    full = sorted((L for L in plan.get("layers", []) if L.get("type") == "overlay" and L.get("file")
                   and not L.get(NEW_KEY) and not _is_captions(L) and L.get("rect") in (None, [0, 0, W, H])
                   and not (int(L["start"]) == 0 and int(L["end"]) >= N - 1)), key=lambda L: int(L["start"]))
    out, nxt = [], 0
    for L in full:
        if int(L["start"]) == nxt:
            out.append(L)
            nxt = int(L["end"]) + 1
    return out if len(out) >= 2 and nxt >= N else []


def unique_ids(plan: dict) -> dict:
    """Every layer its own id (a plan may show one graphic as several layers of one id - corner pieces cut with the
    shots, "captions_b" ...): the second one of an id becomes <id>_2 and so on, the same way every time. In place."""
    taken = {str(L.get("id") or L.get("type")) for L in plan.get("layers", [])}
    seen: set[str] = set()
    for L in plan.get("layers", []):
        i = str(L.get("id") or L.get("type"))
        if i in seen:
            k = 2
            while f"{i}_{k}" in taken:
                k += 1
            i = f"{i}_{k}"
            taken.add(i)
        L["id"] = i
        seen.add(i)
    return plan


def sound_mode(plan: dict) -> str:
    """"follows" (the clips' own sound: cut again when the shots change), "song" (a song under the video: it stays),
    "none" (no sound) or "fixed" (made some other way: the shots' timing cannot change without it going out of
    sync)."""
    made = _dict(plan.get("made_by"))                       # (a hand-written plan may name its tool as one string)
    if made.get("sound") in ("talk", "clips"):
        return "follows"
    src = song_of(plan)
    if src is None:                                         # (the effects alone are made again on every build)
        a = str(_audio(plan).get("path") or "")
        return "fixed" if a and not _effects_made(Path(a)) else "none"
    if made.get("sound") == "music":                        # a music draft: its song excerpt (draft\vN_sound) stays
        return "song"
    if src.parent.name == "draft" and re.fullmatch(r"v\d+_sound", src.stem):
        return "follows"                                    # the draft's clip sound, cut to the shots
    parts = [x.lower() for x in src.parts]
    if src.suffix.lower() in (".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".opus") and (
            "refs" in parts or "build" not in parts                        # a download, a song in the video's folder
            or (src.parent.name == "build" and src.stem.startswith("song_from_"))):   # the Generator's cut copy
        return "song"
    return "fixed"                                          # made in build\ some other way: it cannot follow


def _fit_layers(P: dict, whole: dict, touched: set) -> None:
    """After the changes: a graphic / colour layer that covered the whole video still does (unless the user moved or
    trimmed it: `touched`), from its own first frame; any other one stays inside the video (a speed change or a trim
    left a logo at f-56, or ending before the video did) - cut at the ends as the render would show it. In place."""
    N = int(P["frames"])
    sh = {id(x) for x in shots(P)}
    keep = []
    for L in P["layers"]:
        if id(L) in sh or L.get("type") not in ("overlay", "solid"):
            keep.append(L)
            continue
        lid = str(L.get("id"))
        if lid in whole and lid not in touched:
            L["start"], L["end"] = 0, N - 1
            if whole[lid] is not None:
                L["in"] = whole[lid]
            keep.append(L)
            continue
        if int(L["end"]) < 0 or int(L["start"]) > N - 1:
            continue
        if int(L["start"]) < 0:
            EL._trim_front(L, 0)
        L["end"] = min(int(L["end"]), N - 1)
        keep.append(L)
    P["layers"] = keep


def _face_line(P: dict, L: dict, people: dict) -> dict | None:
    """A face-tracked clip's zoom point per frame (compose zoom_point: the face a little above its middle) for the
    preview - {"start", "values": [[x, y] | None]} - or None (not tracked, or no person track made yet: a render makes
    it)."""
    if L.get("track") != "face":
        return None
    sid = L.get("src")
    if sid not in people:
        from . import person as PS
        try:
            where = PS.source_of((P.get("sources") or {}).get(sid) or {})
            people[sid] = PS.load(*where) if where else None
        except (OSError, ValueError, KeyError):
            people[sid] = None
    T = people[sid]
    if T is None or T.faces is None:
        return None
    vals = []
    for f in range(int(L["start"]), int(L["end"]) + 1):
        fc = T.face(EL._src_at(L, f))
        vals.append([round(float(fc[0]), 4), round(float(fc[1]) + 0.05, 4)] if fc is not None and math.isfinite(float(fc[0]))
                    else None)
    return {"start": int(L["start"]), "values": vals}


def _talking(plan: dict) -> bool:
    """A talking video (the quick draft's "talk" sound): a stutter would pull the picture away from the voice. (A
    video with its clips' own sound otherwise - music, ambience, no words - takes one.)"""
    return _dict(plan.get("made_by")).get("sound") == "talk"


def _dict(x) -> dict:
    return x if isinstance(x, dict) else {}


def _audio(plan: dict) -> dict:
    """The plan's "audio" as a dict (a hand-written plan may give the path alone)."""
    a = plan.get("audio")
    return {"path": a} if isinstance(a, str) else _dict(a)


def _effects_made(p: Path) -> bool:
    """The plan's sound is sfx.py's (build\\sfx\\<name>_mix.wav = a song + the effects, <name>_sfx.wav = the effects
    alone - a video with no song): build.py makes it again from the plan."""
    return p.parent.name == "sfx" and p.stem.endswith(("_mix", "_sfx"))


def song_of(plan: dict) -> Path | None:
    """The sound under the video before its sound effects (a mix's own song), or None (no sound / unreadable)."""
    p = str(_audio(plan).get("path") or "")
    if not p:
        return None
    src = Path(p)
    if _effects_made(src):                                  # a mix (or the effects alone): the sound it was made from
        song = _mix_song(src)
        if song is None:
            return None
        src = Path(str(song.get("path") or ""))
        if not str(src) or str(src) == ".":
            return None
    return src


def _mix_song(mix: Path) -> dict | None:
    """sfx.py's record of a mix's song ({path, start_s, db}), {} for the effects alone, None when unreadable."""
    import json
    try:
        return _dict(_dict(json.loads(mix.with_name(mix.stem[:-4] + "_sfx.json").read_text(encoding="utf-8"))).get("song"))
    except (OSError, ValueError):
        return None


def _draft_song(plan: dict) -> tuple[Path, float] | None:
    """A music quick draft's song itself and where the draft starts in it (its sound is an excerpt exactly the
    draft's length: a longer edit would end in silence)."""
    made = _dict(plan.get("made_by"))
    if made.get("sound") != "music" or not made.get("music") or not Path(str(made["music"])).is_file():
        return None
    try:
        return Path(str(made["music"])), max(0.0, float(made.get("music_start_s") or 0))
    except (TypeError, ValueError):
        return None


def song_start(plan: dict) -> float:
    """Seconds into song_source(plan) that frame 0 hears: the Editor's own cut's start, else a music draft's, else the
    mix's (sfx.py --song-start), else 0."""
    au = _audio(plan)
    cut = _dict(au.get("cut"))
    if cut.get("from"):
        return float(cut.get("start_s") or 0)
    ds = _draft_song(plan)
    if ds:
        return ds[1]
    src = Path(str(au.get("path") or ""))
    song = _mix_song(src) if _effects_made(src) else None
    try:
        return max(0.0, float((song or {}).get("start_s") or 0))
    except (TypeError, ValueError):
        return 0.0


def song_source(plan: dict) -> Path | None:
    """The song the Editor shows and plays: the song itself when the Editor cut it (the plan's audio "cut" - played
    from its start_s), a music draft's song, else song_of."""
    cut = _dict(_audio(plan).get("cut"))
    if cut.get("from"):
        return Path(cut["from"])
    ds = _draft_song(plan)
    return ds[0] if ds else song_of(plan)


def _speed(L: dict) -> float:
    return float(L.get("speed", 1.0))


def _len(L: dict) -> int:
    return int(L["end"]) - int(L["start"]) + 1


def _attached(plan: dict, S: dict) -> list[dict]:
    return [L for L in plan["layers"] if L is not S and L.get("type") == "overlay" and "in" in L
            and int(L["start"]) == int(S["start"]) and int(L["end"]) == int(S["end"])]


def _pinned(plan: dict, S: dict, side: str) -> list[dict]:
    """Graphics pinned to a shot's start / end (not attached; a graphic over exactly the shot's frames is both)."""
    at = _attached(plan, S)
    k = "start" if side == "start" else "end"
    return [L for L in plan["layers"] if L is not S and L.get("type") == "overlay" and L not in at
            and int(L.get(k, -1)) == int(S[k])]


def _no(plan: dict, S: dict) -> int:
    """A shot's number on the page (1 = the first)."""
    return next((k for k, x in enumerate(shots(plan), 1) if x is S), 0)


def _frames_of(plan: dict, src: str) -> int:
    return int(((plan.get("sources") or {}).get(src) or {}).get("frames") or 0)


def room(plan: dict, S: dict) -> tuple[int, int]:
    """The timeline frames a shot could grow by before its first one and after its last one, at its speed (0 when it
    cannot grow: a stutter; a photo / held frame grows as long as wanted - up to 10 minutes)."""
    if S.get("jumps"):
        return 0, 0
    if S.get("hold"):
        n = int(600 * float(plan.get("fps") or 25))
        return n, n
    if S.get("type") == "overlay":                          # a scene: the frames cut off its start come back; past
        sp = _speed(S)                                      # its end it holds its last frame (up to SCENE_HOLD_S)
        return max(0, int(int(S.get("in", 0)) / sp + 1e-9)), int(SCENE_HOLD_S * float(plan.get("fps") or 25))
    n, sp = _frames_of(plan, S.get("src", "")), _speed(S)
    a, b = int(S.get("in", 0)), EL._src_at(S, int(S["end"]))
    return max(0, int(a / sp + 1e-9)), max(0, int((n - 1 - b) / sp + 1e-9)) if n else 0


def _find(plan: dict, sid: str) -> dict:
    S = next((x for x in shots(plan) if x.get("id") == sid), None)
    if S is None:
        raise EditError(I18N.t("no shot {shot}", shot=sid))
    return S


def _layer(plan: dict, lid: str) -> dict:
    L = next((x for x in plan["layers"] if x.get("id") == lid and x.get("type") in ("overlay", "solid")), None)
    if L is None:
        raise EditError(I18N.t("no graphic {graphic}", graphic=lid))
    return L


def _is_captions(L: dict) -> bool:
    f = Path(str(L.get("file") or ""))
    return f.parent.name.startswith("captions") or (f.parent / "assets" / "captions.js").exists()


def _is_word(i: str, v) -> bool:
    if not isinstance(v, str) or re.search(r"(media|logo|image|photo|video|picture|font|file|src|url|color|colour)", i):
        return False
    return any(i == k or i.startswith(k + "_") or i.endswith("_" + k) or i.rstrip("0123456789") == k for k in SAY_KEYS) \
        or (len(v) > 1 and " " in v)


def _say_settings(folder: Path) -> list[dict]:
    """A graphic's settings that are words (strings a viewer reads - never a colour, a file or a logo)."""
    from . import overlay_settings as OS
    try:
        decl, vals = OS.declared(folder), OS.values(folder)
    except (OSError, ValueError):
        return []
    return [{"key": d["id"], "label": d.get("label") or d["id"], "value": vals[d["id"]]} for d in decl
            if d.get("type") == "string" and _is_word(d["id"], vals.get(d["id"]))]


def _caption_cues(folder: Path) -> list[dict]:
    import json
    js = folder / "assets" / "captions.js"
    try:
        txt = js.read_text(encoding="utf-8")
        k = txt.index("window.CAPTIONS")                    # (the comment line above it has an "=" too)
        data = json.loads(txt[txt.index("=", k) + 1:].strip().rstrip(";"))
    except (OSError, ValueError):
        return []
    return data.get("cues") or []


def cue_list(P: dict, folder: Path, src: Path) -> list[dict]:
    """This edit's captions of a captions graphic, changed in place: on its first change the file's cues (from src -
    the graphic as it is on disk), then every change on the list - new words, other frames, a split, a new one, one
    gone. A changed cue carries "_e" (the page marks it). Written whole on save (the step "capfile")."""
    box = P.setdefault(CAPTIONS_KEY, {})
    if str(folder) not in box:
        box[str(folder)] = {"cues": copy.deepcopy(_caption_cues(src))}
    return box[str(folder)]["cues"]


def cues_now(folder: Path, ch: dict | None) -> list[dict]:
    """A captions graphic's captions as this edit has them (ch = its entry in the plan's CAPTIONS_KEY, else the
    file's): each {k, f0, f1, text, gone, edited}, k = its place in the list; frames are the graphic's."""
    cues = (ch or {}).get("cues") if ch else None
    return [{"k": k, "f0": int(c["f0"]), "f1": int(c["f1"]), "text": " ".join(w[0] for w in c["words"]), "gone": False,
             "edited": bool(c.get("_e")), "w0": [int(w[1]) for w in c["words"]]}
            for k, c in enumerate(cues if cues is not None else _caption_cues(folder))]


def cap_bounds(cs: list[dict], i: int, inn: int, span: int) -> tuple[int, int]:
    """The graphic frames caption i may take (first, last): inside the piece that shows it (its shot - a caption never
    leaves the words it was said with); into the captions before / after it only as far as they can give way (talking
    captions touch: the one it moves into gets shorter, down to MIN_CAP frames - a shared edge, as subtitle editors
    do it), never over them."""
    c = cs[i]
    prev, nxt = cap_neighbours(cs, i)
    lo = max(inn, prev["f0"] + MIN_CAP) if prev else inn
    hi = max(inn + span, c["f1"])
    if nxt:
        hi = min(hi, nxt["f1"] - MIN_CAP)
    return min(lo, c["f0"]), max(hi, c["f1"])


def cap_neighbours(cs: list[dict], i: int) -> tuple[dict | None, dict | None]:
    return (next((x for x in reversed(cs[:i]) if not x["gone"]), None),
            next((x for x in cs[i + 1:] if not x["gone"]), None))


def template_folder(tid: str) -> Path | None:
    """A Motion Graphics template's folder (MotionLab's own in tools\\overlays\\motion, else this PC's)."""
    from . import templates as TM
    if not re.fullmatch(r"[\w.-]{1,80}", str(tid or "")):
        return None
    f = TM.MOTION / tid
    if (f / "index.html").exists():
        return f
    return TM.local_folder(tid)


def _graphic_folder(L: dict) -> Path:
    new = L.get(NEW_KEY)
    if new:
        return template_folder(new["template"]) or Path(str(L.get("file") or "")).parent
    return Path(str(L.get("file") or "")).parent


def _curve_keys(v):
    return v if isinstance(v, (int, float, str)) or v is None else {k: v[k] for k in ("keys", "start", "values", "scale",
                                                                                      "offset") if k in v}


def state(plan: dict) -> dict:
    """What the Editor draws and plays (see the module's docstring). Frames are the plan's."""
    from . import overlay_settings as OS
    from . import sfx as SFX
    P = TR.strip(unique_ids(copy.deepcopy(plan)))
    attach_captions(P)
    fps, N = float(P["fps"]), int(P["frames"])
    S = shots(P)
    mode = sound_mode(P)
    out_shots = []
    for i, L in enumerate(S, 1):
        a, b = room(P, L)
        out_shots.append({"n": i, "id": L["id"], "src": L.get("src"), "start": int(L["start"]), "end": int(L["end"]),
                          "in": int(L.get("in", 0)), "speed": _speed(L), "room_start": a, "room_end": b,
                          "db": float(L.get("sound_db") or 0),
                          "special": bool(L.get("hold") or L.get("jumps")),
                          "scene": str(_graphic_folder(L)) if L.get("type") == "overlay" else None,
                          "attached": list(dict.fromkeys(_graphic_folder(x).name for x in _attached(P, L)))})
    TR.build(P)                                             # (drawn and heard like the save makes them)
    edits_v = P.get(VALUES_KEY) or {}
    edits_c = P.get(CAPTIONS_KEY) or {}
    folders: dict[str, dict] = {}                            # a graphic's folder -> its settings, size, length

    def folder_info(L: dict) -> dict:
        f = _graphic_folder(L)
        key = str(f)
        if key not in folders:
            try:
                st = OS.status(f)
            except (OSError, ValueError) as e:
                st = {"name": f.name, "settings": [], "frames": 0, "fps": fps, "width": 0, "height": 0,
                      "problem": str(e), "thumb": None}
            conf = {}
            try:
                conf = OS.conf(f)
            except (OSError, ValueError):
                pass
            try:                                     # its ready-made looks (presets.json): one click sets them all
                looks = {k: {"label": v["label"], "what": v["what"], "values": v["values"]} for k, v in OS.presets(f).items()}
            except (OSError, ValueError):
                looks = {}
            folders[key] = {"name": f.name, "settings": st.get("settings") or [], "frames": int(st.get("frames") or 0),
                            "fps": float(st.get("fps") or fps), "w": int(st.get("width") or 0),
                            "h": int(st.get("height") or 0), "thumb": st.get("thumb"), "problem": st.get("problem", ""),
                            "from": conf.get("from") or (L.get(NEW_KEY) or {}).get("template"),
                            "captions": _is_captions(L), "looks": looks}
        return folders[key]

    graphics, captions, done_caps, capedits = [], [], set(), {}
    for L in P["layers"]:
        if L.get("type") != "overlay" or not L.get("file"):
            continue
        fi = folder_info(L)
        f = _graphic_folder(L)
        vals = {s["id"]: s.get("value") for s in fi["settings"]}
        vals.update((L.get(NEW_KEY) or {}).get("values") or {})
        vals.update(edits_v.get(str(f)) or {})
        caps = fi["captions"]
        words = [] if caps else [{"key": s["id"], "label": s.get("label") or s["id"], "value": vals.get(s["id"])}
                                 for s in fi["settings"] if s.get("type") == "string" and _is_word(s["id"], vals.get(s["id"]))]
        graphics.append({"id": L["id"], "folder": f.name, "dir": str(f), "start": int(L["start"]), "end": int(L["end"]),
                         "in": int(L.get("in", 0)), "speed": _speed(L), "rect": L.get("rect"),
                         "blend": L.get("blend", "normal"), "opacity": _curve_keys(L.get("opacity")),
                         "values": vals, "words": words, "captions": caps, "new": bool(L.get(NEW_KEY)), "fit": fit_of(L),
                         "scene": any(L is x for x in S),
                         "pieces": sum(1 for x in P["layers"] if x.get("type") == "overlay" and x.get("file")
                                       and _graphic_folder(x) == f)})
        if caps and str(f) not in done_caps:
            done_caps.add(str(f))
            pieces = [x for x in P["layers"] if x.get("type") == "overlay" and x.get("file") and _graphic_folder(x) == f]
            ch = edits_c.get(str(f)) or {}
            if ch:
                capedits[str(f)] = ch
            cs = cues_now(f, ch)
            tails, mine = [], []
            for i, c in enumerate(cs):
                if c["gone"]:
                    continue                                 # removed (on save it goes from the file)
                main = None
                for x in pieces:                       # where this caption shows in the plan (each piece that shows it)
                    inn, s, e, sp = int(x.get("in", 0)), int(x["start"]), int(x["end"]), _speed(x)
                    span = int((e - s) * sp + 1e-6)
                    at = lambda g: s + (g - inn) / sp        # noqa: E731 - a graphic frame on the timeline
                    if main is None and inn <= c["f0"] <= inn + span:
                        main = x["id"]
                        lo, hi = cap_bounds(cs, i, inn, span)
                        f = int(round(at(c["f0"])))          # (this part: up to its shot's end)
                        n = max(1, min(int(round((c["f1"] - c["f0"] + 1) / sp)), e - f + 1))
                        captions.append({"graphic": x["id"], "cue": c["k"], "f": f, "text": c["text"], "len": n,
                                         "wf": [int(round(at(g))) for g in c["w0"]],   # (each word's first frame)
                                         "next_here": i + 1 < len(cs) and inn <= cs[i + 1]["f0"] <= inn + span,
                                         "edited": c["edited"], "lo": max(s, int(math.ceil(at(lo) - 1e-6))),
                                         "hi": min(e, int(math.floor(at(hi) + 1e-6))), "min": int(math.ceil(MIN_CAP / sp))})
                    elif c["f0"] < inn <= c["f1"]:           # its end said over a cut: it shows on the next piece too
                        n = max(1, min(int(round((min(c["f1"], inn + span) - inn + 1) / sp)), e - s + 1))
                        mine.append({"graphic": x["id"], "cue": c["k"], "f": s, "len": n, "text": c["text"],
                                     "edited": c["edited"], "tail": True})   # (a moved shot starts with its words)
                if main is None and mine:                    # its start's shot is gone: its first part leads
                    mine[0].pop("tail")
                    mine[0].update(lo=mine[0]["f"], hi=mine[0]["f"] + mine[0]["len"] - 1, min=1)
                    captions.append(mine.pop(0))
                    main = captions[-1]["graphic"]
                tails += [{**q, "graphic": main} for q in mine]      # (a part selects and changes the caption)
                mine.clear()
            captions.extend(tails)                           # (after the main parts: the page finds those first)
    notes: list = []
    cues = []
    try:
        lib = SFX.Library.load()
    except (OSError, ValueError):
        lib = None
    if lib is not None and isinstance(P.get("sfx"), dict) and P["sfx"].get("sounds"):
        lib = lib.only(P["sfx"]["sounds"])                  # (the sounds picked for this edit: as the build hears it)
    try:
        last: dict = {}
        for q in (SFX.plan_cues(P, notes) if P.get("sfx") or P.get("cues") else []):
            e = lib.entry(q["sound"]) if lib is not None and q.get("sound") else None
            if e is None and lib is not None:
                e = lib.pick(q, last.get(q["kind"]))
            if e is not None:
                last[q["kind"]] = e
            rec = e is not None and not e.get("synth")
            # a recorded sound's anchor lands on the cue's key moment; a made-up one starts on the frame (sfx.py mix)
            off = SFX.key_moment(q["kind"], q.get("params")) - float(e.get("anchor_s") or 0) if rec else 0.0
            dur = (q.get("params") or {}).get("dur")
            cues.append({"f": int(q["f"]), "kind": q["kind"], "what": str(q.get("what", ""))[:80],
                         "dur": float(dur) if dur and not rec and "dur" in SFX.KINDS[q["kind"]][1] else None,
                         "db": float(q.get("db") or 0), "sound": e["file"] if rec else None,
                         "pinned": bool(q.get("sound")), "own": q.get("source") == "plan cues",
                         "offset_s": round(off, 3), "len_s": round(float(e.get("len_s") or 0) if rec else
                                                                   float((q.get("params") or {}).get("dur") or 0.4), 3)})
    except (OSError, ValueError, KeyError):
        cues = []
    draw = []                                                # the live preview's layers, in the plan's order
    people: dict = {}
    for L in P["layers"]:
        t = L.get("type")
        if t == "clip":
            draw.append({"t": "clip", "id": L["id"], "src": L.get("src"), "start": int(L["start"]), "end": int(L["end"]),
                         "face": _face_line(P, L, people),
                         "in": int(L.get("in", 0)), "speed": _speed(L), "hold": bool(L.get("hold")),
                         "jumps": L.get("jumps"), "rect": L.get("rect"), "zoom": _curve_keys(L.get("zoom")),
                         "anchor": L.get("anchor"), "dx": _curve_keys(L.get("dx")), "dy": _curve_keys(L.get("dy")),
                         "rotation": _curve_keys(L.get("rotation")), "tr": L.get("tr"),
                         "opacity": _curve_keys(L.get("opacity")), "mirror": bool(L.get("mirror")),
                         "fit": L.get("fit", "cover"), "flash_over": L.get("flash_over"),
                         "flash_white": L.get("flash_white"), "black": L.get("black"), "tint": L.get("tint"),
                         "blend": L.get("blend", "normal")})
        elif t == "overlay" and L.get("file"):
            draw.append({"t": "overlay", "id": L["id"]})
        elif t == "solid":
            draw.append({"t": "solid", "id": L["id"], "start": int(L["start"]), "end": int(L["end"]),
                         "color": L.get("color"), "rect": L.get("rect"), "opacity": _curve_keys(L.get("opacity")),
                         "blend": L.get("blend", "normal"), "tr": L.get("tr"), "cover": bool(L.get("cover"))})
    cut, song = _dict(_audio(P).get("cut")), song_source(P)
    return {"fps": fps, "frames": N, "width": int(P.get("width", 1920)), "height": int(P.get("height", 1080)),
            "sound": mode, "timing_locked": mode == "fixed", "shots": out_shots, "graphics": graphics,
            "folders": folders, "captions": sorted(captions, key=lambda c: (bool(c.get("tail")), c["f"])), "capedits": capedits,
            "effects": FX.effects(P), "fx_kinds": list(FX.ADD), "transitions": TR.transitions(P),
            "fx_can": FX.availability(P, talk=_talking(P)),          # (why a kind cannot go where the playhead is)
            "trans_kinds": [[k, v[0], round(v[1] * fps)] for k, v in TR.KINDS.items()       # (one no longer offered:
                            if k in TR.OFFER or any(t["kind"] == k for t in TR.transitions(P))],   # where it is)
            "sfx": cues, "draw": draw,
            "curves": P.get("curves") or {}, "song": str(song) if song and mode == "song" else None,
            "song_cut": {"start_s": song_start(P), "db": float(cut.get("db") or 0)},
            "vol": [VOL_MIN, VOL_MAX], "song_db": list(SONG_DB),
            "clips": [{"id": k, "name": Path(str(s.get("source") or k)).name, "frames": int(s.get("frames") or 0),
                       "photo": _is_photo(s)} for k, s in (P.get("sources") or {}).items()],
            "audio_file": str(_audio(P).get("path")) if mode == "fixed" else None,
            "name": P.get("name", ""), "speeds": [SPEED_MIN, SPEED_MAX],
            "safe": SZ.for_page(int(P.get("width", 1920)), int(P.get("height", 1080)))}   # (the platforms' safe zones)


# ------------------------------------------------------------------------------------------------- changing a plan
def _sfx_edits(P: dict) -> list[dict]:
    sx = P.get("sfx")
    if not isinstance(sx, dict):
        sx = {}
        P["sfx"] = sx
    return sx.setdefault("edits", [])


def _points(P: dict, fn) -> None:
    """The plan's own frame references that are not layers - its cues and its sound effect edits - through fn
    (None = gone)."""
    keep = []
    for q in P.get("cues") or []:
        if isinstance(q.get("f"), int):
            f = fn(int(q["f"]))
            if f is None:
                continue
            q["f"] = f
        keep.append(q)
    if "cues" in P:
        P["cues"] = keep
    sx = P.get("sfx")
    if not isinstance(sx, dict) or not sx.get("edits"):
        return
    keep = []
    for e in sx["edits"]:
        f = fn(int(e["f"]))
        if f is None:
            continue
        e["f"] = f
        if e.get("to") is not None:
            t = fn(int(e["to"]))
            if t is None:
                continue
            e["to"] = t
        keep.append(e)
    sx["edits"] = keep


def _map_frames(P: dict, fn) -> None:
    """The sound effect edits alone through fn (EL.cut moves the plan's own cues itself)."""
    cues = P.get("cues")
    P["cues"] = []
    _points(P, fn)
    P["cues"] = cues if cues is not None else []


def _cut(P: dict, a: int, b: int) -> None:
    n = b - a + 1
    EL.cut(P, a, b)
    _map_frames(P, lambda f: None if a <= f <= b else (f - n if f > b else f))


def _insert(P: dict, p: int, n: int, skip: list[dict]) -> None:
    """n new frames from timeline frame p: every layer from p on moves on n frames (but the ones in skip, which the
    caller sets), one across p grows by n; the plan's own cues and sound effect edits from p move too."""
    for L in P["layers"]:
        if any(L is x for x in skip):
            continue
        s, e = int(L.get("start", 0)), int(L.get("end", int(P["frames"]) - 1))
        if s >= p:
            EL._shift(L, n)
        elif e >= p:
            L["end"] = e + n                              # across the new frames: it goes on (a graphic holds)
    _points(P, lambda f: f + n if f >= p else f)
    P["frames"] = int(P["frames"]) + n


def _retime(P: dict, fn, skip: list[dict], add: int = 0) -> None:
    """Every layer but the ones in skip moves with the frame it starts on (fn: old frame -> new frame), keeping its
    length; the plan's cues and sound effect edits too; the video gets `add` frames; a layer past its new end is cut
    there (one that would start after it goes)."""
    for L in P["layers"]:
        if any(L is x for x in skip):
            continue
        s = int(L.get("start", 0))
        d = fn(s) - s
        if d:
            EL._shift(L, d)
    _points(P, fn)
    P["frames"] = int(P["frames"]) + add
    _fit(P)


def _fit(P: dict) -> None:
    last = int(P["frames"]) - 1
    keep = []
    for L in P["layers"]:
        if int(L.get("start", 0)) > last:
            continue
        if "end" in L and int(L["end"]) > last:
            L["end"] = last
        keep.append(L)
    P["layers"] = keep


def _keys_through(L: dict, fn) -> None:
    """A layer's animated values (zoom, dx, dy, opacity, gain, rotation, the zoom point) through fn - a sped-up shot's
    punch-in comes sooner."""
    EL.move_curves(L, fn)


def _span(L: dict, fps: float) -> str:
    """f12-f40 (00:00:00:12-00:00:01:15): every frame shown with its timecode (hard rule 2)."""
    s, e = int(L["start"]), int(L["end"])
    return f"f{s}-f{e} ({frame_to_tc(s, fps)}-{frame_to_tc(e, fps)})"


def _tcf(f: int, fps: float) -> str:
    return f"f{f} ({frame_to_tc(int(f), fps)})"


def _trim(P: dict, S: dict, side: str, by: int, done: list[str], fps: float) -> None:
    if by == 0:
        return
    s, e = int(S["start"]), int(S["end"])
    ln = e - s + 1
    a_room, b_room = room(P, S)
    att = _attached(P, S)
    if by < 0:                                              # shorter: those frames go
        d = -by
        if d >= ln:
            raise EditError(I18N.t("shot {n} has {frames} frames - delete it instead", n=_no(P, S), frames=ln))
        pins = _pinned(P, S, side)                          # lifted out, then put back at the shot's new edge with
        P["layers"] = [L for L in P["layers"] if not any(L is x for x in pins)]    # their own frames and length
        _cut(P, s, s + d - 1) if side == "start" else _cut(P, e - d + 1, e)
        last = int(P["frames"]) - 1
        for L in pins:
            span = int(L["end"]) - int(L["start"])
            if side == "start":                             # an intro is never cut off: it starts with the shot
                L["start"], L["end"] = int(S["start"]), min(int(S["start"]) + span, last)
            else:                                           # an exit keeps its length: it ends with the shot
                L["end"] = int(S["end"])
                L["start"] = L["end"] - span
                if L["start"] < 0:
                    L["in"] = int(L.get("in", 0)) - L["start"]
                    L["start"] = 0
            L.pop("land", None)
            P["layers"].append(L)
        done.append(f"{S['id']}: {d} frame{'s' if d != 1 else ''} off its {side} (now {_span(S, fps)})")
        return
    d = by                                                  # longer: more of its own clip
    if side == "start":
        if d > a_room:
            raise EditError(I18N.t("shot {n} has {frames} frame(s) of its clip before it", n=_no(P, S), frames=a_room))
        pins = _pinned(P, S, "start")
        _insert(P, s, d, skip=[S, *att, *pins])
        S["in"] = max(0, int(S.get("in", 0)) - int(round(d * _speed(S))))
        S["end"] = e + d
        for L in att:
            k = int(round(d * _speed(L)))
            if int(L.get("in", 0)) >= k:
                L["in"] = int(L["in"]) - k
            L["end"] = int(L["end"]) + d
        # (pins - an intro at the shot's start - stay where they are: the shot still starts there)
    else:
        if d > b_room:
            raise EditError(I18N.t("shot {n} has {frames} frame(s) of its clip after it", n=_no(P, S), frames=b_room))
        pins = _pinned(P, S, "end")
        _insert(P, e + 1, d, skip=[S, *att, *pins])
        S["end"] = e + d
        for L in att:
            L["end"] = int(L["end"]) + d
        for L in pins:                                      # an exit stays at the end: it moves on with the cut
            EL._shift(L, d)
    done.append(f"{S['id']}: {d} frame{'s' if d != 1 else ''} more at its {side} (now {_span(S, fps)})")


def _roll(P: dict, S: dict, by: int, done: list[str], fps: float) -> None:
    """The cut after S moves `by` frames; the next shot gives / takes those frames - the length stays."""
    if by == 0:
        return
    S_all = shots(P)
    i = next(k for k, x in enumerate(S_all) if x is S)
    if i + 1 >= len(S_all):
        raise EditError(I18N.t("shot {n} is the last shot - trim its end instead", n=_no(P, S)))
    T = S_all[i + 1]
    if int(T["start"]) != int(S["end"]) + 1:
        raise EditError(I18N.t("shots {a} and {b} do not touch - trim them instead", a=_no(P, S), b=_no(P, T)))
    sa, ta = _attached(P, S), _attached(P, T)
    s_pin, t_pin = _pinned(P, S, "end"), _pinned(P, T, "start")
    if by > 0:
        if by > room(P, S)[1]:
            raise EditError(I18N.t("shot {n} has {frames} frame(s) of its clip after it", n=_no(P, S),
                                   frames=room(P, S)[1]))
        if by >= _len(T):
            raise EditError(I18N.t("shot {n} is only {frames} frames", n=_no(P, T), frames=_len(T)))
    else:
        if -by > room(P, T)[0]:
            raise EditError(I18N.t("shot {n} has {frames} frame(s) of its clip before it", n=_no(P, T),
                                   frames=room(P, T)[0]))
        if -by >= _len(S):
            raise EditError(I18N.t("shot {n} is only {frames} frames", n=_no(P, S), frames=_len(S)))
    S["end"] = int(S["end"]) + by
    for L in sa:
        L["end"] = int(L["end"]) + by
    for L in [T, *ta]:
        L["start"] = int(L["start"]) + by
        if L.get("type") == "clip" or "in" in L:
            L["in"] = max(0, int(L.get("in", 0)) + int(round(by * _speed(L))))
    for L in s_pin:                                         # an exit at the cut moves with it (its length kept)
        EL._shift(L, by)
    for L in t_pin:                                         # an intro at the cut too
        EL._shift(L, by)
    done.append(f"the cut {S['id']} | {T['id']} moved {by:+d} frame{'s' if abs(by) != 1 else ''}: now at "
                f"{_tcf(int(T['start']), fps)}")


def _move(P: dict, S: dict, to: int, done: list[str], fps: float) -> None:
    """The shot to place `to` in the order; it takes every layer and sound that starts on its frames; the shots after
    its old place close up, the ones from its new place make room - the length stays."""
    order = shots(P)
    i = next(k for k, x in enumerate(order) if x is S)
    if not 0 <= to < len(order):
        raise EditError(I18N.t("there is no place {k} - the video has {n} shots", k=to + 1, n=len(order)))
    if to == i:
        return
    s, e = int(S["start"]), int(S["end"])
    n = e - s + 1
    rest = [x for x in order if x is not S]
    p_old = int(rest[to]["start"]) if to < len(rest) else int(rest[-1]["end"]) + 1
    p_new = p_old - n if p_old > e else p_old

    def fn(f: int) -> int:
        if s <= f <= e:
            return f - s + p_new
        g = f - n if f > e else f
        return g + n if g >= p_new else g
    _retime(P, fn, skip=[])
    done.append(f"{S['id']} moved to place {to + 1} (now {_span(S, fps)})")


def _split(P: dict, S: dict, at: int, done: list[str], fps: float) -> None:
    s, e = int(S["start"]), int(S["end"])
    if not s < at <= e:
        raise EditError(I18N.t("{frame} is not inside shot {n} - split it between its first and last frame",
                               frame=f"f{at}", n=_no(P, S)))
    ids = {str(L.get("id")) for L in P["layers"]}

    def new_id(i: str) -> str:
        k = 2
        while f"{i}_{k}" in ids:
            k += 1
        ids.add(f"{i}_{k}")
        return f"{i}_{k}"
    for L in [S, *_attached(P, S)]:
        second = EL._trim_front(copy.deepcopy(L), at)
        second["id"] = new_id(str(L["id"]))
        second.pop("trans", None)                           # (its transition stays on the cut before the first part)
        L["end"] = at - 1
        P["layers"].insert(P["layers"].index(L) + 1, second)
    done.append(f"{S['id']} split at {_tcf(at, fps)}: {_span(S, fps)} + {_span({'start': at, 'end': e}, fps)}")


def _slip(P: dict, S: dict, by: int, done: list[str], fps: float) -> None:
    """Another moment of its clip in the same place (an editor's slip): its frames stay, its part of the clip moves
    `by` timeline frames later (< 0 = earlier); what moves with it (its caption piece) slips with it."""
    if by == 0:
        return
    a_room, b_room = room(P, S)
    if not -a_room <= by <= b_room:
        raise EditError(I18N.t("shot {n} can slip {before} frame(s) earlier and {after} later in its clip",
                               n=_no(P, S), before=a_room, after=b_room))
    for L in [S, *_attached(P, S)]:
        L["in"] = max(0, int(L.get("in", 0)) + int(round(by * _speed(L))))
    done.append(f"{S['id']}: {abs(by)} frame{'s' if abs(by) != 1 else ''} {'later' if by > 0 else 'earlier'} in its clip "
                f"(still {_span(S, fps)})")


def _source(P: dict, src: str) -> dict:
    s = (P.get("sources") or {}).get(src)
    if not s:
        raise EditError(I18N.t("no clip {clip} in this video", clip=src))
    return s


def _is_photo(s: dict) -> bool:
    from .project import PHOTO_EXT
    return Path(str(s.get("source") or "")).suffix.lower() in PHOTO_EXT


def _take(P: dict, S: dict, src: str, f: int, done: list[str], fps: float) -> list[dict]:
    """Another clip of the video in the shot's place, from its frame f, the same length and speed (a photo: held).
    Returns the caption pieces that went with it (their words were the old take's)."""
    s = _source(P, src)
    n_src = int(round(_len(S) * _speed(S)))
    if _is_photo(s):
        S.update(src=src, hold=True, **{"in": 0})
        S.pop("jumps", None)
    else:
        if int(s.get("frames") or 0) < n_src:
            raise EditError(I18N.t("clip {clip} has {frames} frames - shot {n} needs {need}", clip=src,
                                   frames=int(s.get("frames") or 0), n=_no(P, S), need=n_src))
        S.update(src=src, **{"in": max(0, min(int(f), int(s["frames"]) - n_src))})
        S.pop("hold", None)
        S.pop("jumps", None)
    caps = [L for L in _attached(P, S) if _is_captions(L)]
    done.append(f"{S['id']}: now {Path(str(s.get('source'))).name} from its frame {S['in']} (still {_span(S, fps)})"
                + ("; its captions went with the old take" if caps else ""))
    return caps


def _clip_add(P: dict, src: str, f: int, n: int, to: int, done: list[str], fps: float) -> dict:
    """A clip of the video as a new shot at place `to` (0 = first): n frames from its frame f (a photo: held); what
    comes after moves on (a graphic across the new cut keeps its frames)."""
    s = _source(P, src)
    order = shots(P)
    if not 0 <= to <= len(order):
        raise EditError(I18N.t("there is no place {k} - the video has {n} shots", k=to + 1, n=len(order)))
    photo = _is_photo(s)
    n = max(1, int(n))
    if not photo:
        n = min(n, int(s.get("frames") or 0))
        if n < 1:
            raise EditError(I18N.t("clip {clip} has no frames", clip=src))
        f = max(0, min(int(f), int(s["frames"]) - n))
    p = int(order[to]["start"]) if to < len(order) else (int(order[-1]["end"]) + 1 if order else 0)
    nums = [int(m[1]) for x in order if (m := re.match(r"s(\d+)_", str(x.get("id"))))]
    new = {"type": "clip", "id": f"s{max(nums, default=0) + 1:02d}_{src}", "src": src, "start": p, "end": p + n - 1,
           "in": 0 if photo else int(f)}
    if photo:
        new["hold"] = True
    nb = order[min(to, len(order) - 1)] if order else None    # its framing like the shot beside it
    for k in ("rect", "fit"):
        if nb is not None and k in nb:
            new[k] = copy.deepcopy(nb[k])
    _retime(P, lambda x: x + n if x >= p else x, skip=[], add=n)
    i = P["layers"].index(order[to]) if to < len(order) else (P["layers"].index(order[-1]) + 1 if order else 0)
    P["layers"].insert(i, new)
    done.append(f"{new['id']}: {Path(str(s.get('source'))).name} added at place {to + 1} ({_span(new, fps)}, {n} frames)"
                + ("" if photo else f" from its frame {new['in']}") + " - what came after moved on")
    return new


def _shot_dup(P: dict, S: dict, done: list[str], fps: float) -> dict:
    """The shot again right after itself: the same part of its clip with its zoom, moves, keyframes and effects on it
    (moved with it); its transition stays on the original; what comes after moves on."""
    if S.get("scene"):
        raise EditError(I18N.t("a scene is duplicated by Claude - ask for it"))
    order = shots(P)
    n, p = _len(S), int(S["end"]) + 1
    nums = [int(m[1]) for x in order if (m := re.match(r"s(\d+)_", str(x.get("id"))))]
    new = EL._shift(copy.deepcopy(S), n)
    new["id"] = f"s{max(nums, default=0) + 1:02d}_{S.get('src', 'clip')}"
    new.pop("trans", None)
    _retime(P, lambda x: x + n if x >= p else x, skip=[], add=n)
    P["layers"].insert(P["layers"].index(S) + 1, new)
    done.append(f"{S['id']} duplicated as {new['id']} ({_span(new, fps)}) - what came after moved on")
    return new


def _set_speed(P: dict, S: dict, x: float, done: list[str], fps: float) -> None:
    """The same part of its clip in 1/x of its frames (from its current speed): what starts on its frames comes
    sooner / later with its picture, an exit at its end stays at its end, the rest moves up or on."""
    if S.get("hold") or S.get("jumps"):
        raise EditError(I18N.t("shot {n} is a held frame or a stutter - its speed stays", n=_no(P, S)))
    if not SPEED_MIN <= x <= SPEED_MAX:
        raise EditError(I18N.t("a speed from {lo}x to {hi}x", lo=SPEED_MIN, hi=SPEED_MAX))
    x0 = _speed(S)
    if abs(x - x0) < 1e-6:
        return
    s, e = int(S["start"]), int(S["end"])
    n0 = e - s + 1
    n1 = max(1, int(round(n0 * x0 / x)))
    src_n = _frames_of(P, S.get("src", ""))
    if src_n and int(S.get("in", 0)) + int((n1 - 1) * x + 1e-6) > src_n - 1:
        n1 = max(1, int((src_n - 1 - int(S.get("in", 0))) / x) + 1)
    d = n1 - n0
    att, pins = _attached(P, S), _pinned(P, S, "end")

    def fn(f: int) -> int:
        if f < s:
            return f
        if f <= e:
            return s + min(n1 - 1, int(round((f - s) * x0 / x)))
        return f + d
    for L in pins:
        EL._shift(L, d)
    _retime(P, fn, skip=[S, *att, *pins], add=d)
    for L in [S, *att]:
        L["end"] = s + n1 - 1
        sp = x if L is S else _speed(L) * x / x0
        if abs(sp - 1.0) < 1e-6:
            L.pop("speed", None)
        else:
            L["speed"] = round(sp, 6)
        _keys_through(L, lambda f: fn(f) if s <= f <= e else (f + d if f > e else f))
    _fit(P)
    done.append(f"{S['id']} at {x:g}x speed (was {x0:g}x): {n0} -> {n1} frames, now {_span(S, fps)}")


def _cap_time(P: dict, L: dict, o: dict, op: str, folder: Path, src: Path, steps: list, done: list[str],
              fps: float) -> None:
    """A caption moved (capmove, "by" timeline frames) or one edge trimmed (captrim, "side", "to" = the timeline frame
    it now starts / ends on): kept inside the shot it is said in and off the captions beside it (cap_bounds), at least
    MIN_CAP frames; its words keep their share of its frames (caption_retime on save)."""
    lst = cue_list(P, folder, src)
    cs = cues_now(src, {"cues": lst})
    k = int(o["cue"])
    i = next((j for j, c in enumerate(cs) if c["k"] == k and not c["gone"]), None)
    if i is None:
        raise EditError(I18N.t("no caption {n}", n=k + 1))
    inn, s, e, sp = int(L.get("in", 0)), int(L["start"]), int(L["end"]), _speed(L)
    lo, hi = cap_bounds(cs, i, inn, int((e - s) * sp + 1e-6))
    c = cs[i]
    if op == "capmove":
        dg = max(lo - c["f0"], min(hi - c["f1"], int(round(int(o["by"]) * sp))))
        f0, f1 = c["f0"] + dg, c["f1"] + dg
    else:
        g = inn + int(round((int(o["to"]) - s) * sp))     # the timeline frame -> its graphic frame
        if o.get("side") == "start":
            f0, f1 = max(lo, min(c["f1"] - MIN_CAP + 1, g)), c["f1"]
        else:
            f0, f1 = c["f0"], max(c["f0"] + MIN_CAP - 1, min(hi, g))
    if (f0, f1) == (c["f0"], c["f1"]):
        raise EditError(I18N.t("caption {n} cannot go further - its shot's edge or the caption beside it is there", n=k + 1))
    moved = [(c, f0, f1)]
    prev, nxt = cap_neighbours(cs, i)
    if prev and f0 <= prev["f1"]:                           # the one before gives way: it ends sooner
        moved.append((prev, prev["f0"], f0 - 1))
    if nxt and f1 >= nxt["f0"]:                             # the one after starts later
        moved.append((nxt, f1 + 1, nxt["f1"]))
    at = lambda g: s + int(round((g - inn) / sp))          # noqa: E731
    for x, a, b in moved:
        lst[x["k"]] = {**caption_retime(lst[x["k"]], a, b), "_e": 1}
    done.append(f"caption {k + 1}: " + ("moved" if op == "capmove" else f"its {o.get('side', 'end')} trimmed")
                + f", now {_span({'start': at(f0), 'end': at(f1)}, fps)}"
                + "".join(f"; caption {x['k'] + 1} gave way ({_span({'start': at(a), 'end': at(b)}, fps)})"
                          for x, a, b in moved[1:]))


def _cap_merge(L: dict, o: dict, lst: list[dict], done: list[str]) -> None:
    """Caption n and the next one as one caption (capmerge): its words keep their frames, the pause between them goes
    to the first one's last word - only when the next one is said in the same shot (the piece L shows)."""
    k = int(o["cue"])
    if not 0 <= k < len(lst) - 1:
        raise EditError(I18N.t("caption {n} has no caption after it", n=k + 1))
    a, b = lst[k], lst[k + 1]
    inn, span = int(L.get("in", 0)), int((int(L["end"]) - int(L["start"])) * _speed(L) + 1e-6)
    if not inn <= int(b["f0"]) <= inn + span:
        raise EditError(I18N.t("the next caption is said in another shot - they stay apart"))
    words = [list(w) for w in a["words"]] + [list(w) for w in b["words"]]
    words[len(a["words"]) - 1][2] = int(b["f0"]) - 1
    lst[k:k + 2] = [{**a, "f1": int(b["f1"]), "words": words, "_e": 1}]
    done.append(f"captions {k + 1} and {k + 2} as one: \"{' '.join(w[0] for w in words)}\"")


def _cap_split(P: dict, L: dict, o: dict, folder: Path, src: Path, done: list[str], fps: float) -> None:
    """A caption cut in two at a frame (capsplit, "at" = the timeline frame the second one starts on): the words
    said before it stay, the rest make the second caption."""
    lst = cue_list(P, folder, src)
    k = int(o["cue"])
    if not 0 <= k < len(lst):
        raise EditError(I18N.t("no caption {n}", n=k + 1))
    c = lst[k]
    inn, s, sp = int(L.get("in", 0)), int(L["start"]), _speed(L)
    g = inn + int(round((int(o["at"]) - s) * sp))
    a = [list(w) for w in c["words"] if int(w[1]) < g]
    b = [list(w) for w in c["words"] if int(w[1]) >= g]
    if not a or not b or not int(c["f0"]) < g <= int(c["f1"]):
        raise EditError(I18N.t("caption {n} has words on one side of {frame} only - move the playhead between two "
                               "words", n=k + 1, frame=f"f{int(o['at'])}"))
    a[-1][2], b[0][1] = g - 1, g                            # the words beside the split reach it
    lst[k:k + 1] = [{**c, "f1": g - 1, "words": a, "_e": 1}, {**c, "f0": g, "words": b, "_e": 1}]
    done.append(f"caption {k + 1} split at {_tcf(int(o['at']), fps)}: \"{' '.join(w[0] for w in a)}\" + "
                f"\"{' '.join(w[0] for w in b)}\"")


def _cap_add(P: dict, L: dict, o: dict, folder: Path, src: Path, done: list[str], fps: float) -> None:
    """A new caption at a frame (capadd, "at", "text"): up to 1.5 s, inside its shot, up to the next caption; never
    over one (split or edit that one instead)."""
    lst = cue_list(P, folder, src)
    words = " ".join(str(o.get("text") or "").split())
    if not words:
        raise EditError(I18N.t("a caption needs words"))
    inn, s, e, sp = int(L.get("in", 0)), int(L["start"]), int(L["end"]), _speed(L)
    g = inn + int(round((int(o["at"]) - s) * sp))
    end_g = inn + int((e - s) * sp + 1e-6)
    if any(int(c["f0"]) <= g <= int(c["f1"]) for c in lst):
        raise EditError(I18N.t("there is a caption at {frame} already - change its words or split it",
                               frame=f"f{int(o['at'])}"))
    nxt = min((int(c["f0"]) for c in lst if int(c["f0"]) > g), default=None)
    f1 = min(g + int(round(1.5 * fps * sp)) - 1, end_g, (nxt - 1) if nxt is not None else end_g)
    if f1 - g + 1 < MIN_CAP:
        raise EditError(I18N.t("no room for a caption at {frame}", frame=f"f{int(o['at'])}"))
    new = {**caption_words({"f0": g, "f1": f1, "words": []}, words), "_e": 1}
    k = sum(1 for c in lst if int(c["f0"]) < g)
    lst.insert(k, new)
    done.append(f"caption added at {_tcf(int(o['at']), fps)}: \"{words}\"")


FIT_KEYS = ("behind", "glass", "guard", "pin")
IN_SHOT_KEYS = ("behind", "guard", "follow", "snap", "glass", "shadow", "match", "over_face")


def in_shot(folder: Path, P: dict) -> dict:
    """A template's own way into a shot with a person (template.json "in_shot": compose's keys - a word behind you, a
    glass card, brackets on your face) - only when the video has clips (a video of graphics has nobody in it)."""
    if not any(x.get("type") == "clip" for x in P.get("layers", [])):
        return {}
    try:
        t = json.loads((Path(folder) / "template.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    s = t.get("in_shot") if isinstance(t.get("in_shot"), dict) else {}
    return {k: s[k] for k in IN_SHOT_KEYS if k in s}


def fit_of(L: dict) -> dict:
    """A graphic's place in the shot as the Editor's switches show it (compose's keys behind / glass / guard / follow)."""
    return {"behind": bool(L.get("behind")), "glass": bool(L.get("glass")), "guard": bool(L.get("guard")),
            "pin": L.get("follow") == "face"}


def _gfit(L: dict, key: str, on: bool) -> None:
    """One switch of fit_of() on / off: behind = hidden on the person + "follow": "camera" (part of the room) unless it
    is pinned to the face; glass = the footage frosted under it + a shadow; guard = never over the face; pin =
    "follow": "face". The footage's softness and grain ("match") with any of them."""
    if L.get("type") != "overlay":
        raise EditError(I18N.t("only a graphic can go behind you or turn to glass"))
    if key not in FIT_KEYS:
        raise EditError(I18N.t("no such change: {op}", op=f"gfit {key}"))
    if key == "behind":
        if on:
            L["behind"] = True
            if L.get("follow") != "face":
                L["follow"] = "camera"
        else:
            L.pop("behind", None)
            if L.get("follow") == "camera":
                L.pop("follow")
    elif key == "glass":
        if on:
            L["glass"], L["shadow"] = True, True
        else:
            L.pop("glass", None)
            L.pop("shadow", None)
    elif key == "guard":
        if on:
            L["guard"] = True
        else:
            L.pop("guard", None)
    else:
        if on:
            L["follow"] = "face"
        elif L.get("follow") == "face":
            L.pop("follow")
            if L.get("behind"):
                L["follow"] = "camera"
    if any(L.get(k) for k in ("behind", "glass", "guard", "follow")):
        L["match"] = True
    else:
        L.pop("match", None)


def _gtrim(P: dict, L: dict, side: str, by: int, done: list[str], fps: float) -> None:
    if by == 0:
        return
    s, e = int(L["start"]), int(L["end"])
    N = int(P["frames"])
    if side == "start":
        if s + by > e:
            raise EditError(I18N.t("{graphic} would have no frames left", graphic=L["id"]))
        if s + by < 0:
            raise EditError(I18N.t("{frame} is outside the video", frame=f"f{s + by}"))
        if by > 0:
            EL._trim_front(L, s + by)
        else:                                               # earlier: its first frame holds a little longer
            L["start"] = s + by
            if L.get("type") == "overlay":
                L["in"] = int(L.get("in", 0)) + by          # (an "in" under 0 shows its first frame)
            L.pop("land", None)
    else:
        if e + by < s:
            raise EditError(I18N.t("{graphic} would have no frames left", graphic=L["id"]))
        if e + by > N - 1:
            raise EditError(I18N.t("{frame} is outside the video", frame=f"f{e + by}"))
        L["end"] = e + by
    done.append(f"{L['id']}: its {side} {by:+d} frame{'s' if abs(by) != 1 else ''} (now {_span(L, fps)})")


def attach_captions(P: dict) -> int:
    """A captions graphic over several shots in one layer (timed to the edit: draft_edit's `caption` line) cut into a
    piece per shot (each with its "in"), so its words move, trim and change speed with the shot they are said in -
    the picture stays the same frame for frame. In place; returns how many layers were cut."""
    S = shots(P)
    n = 0
    for L in list(P["layers"]):
        if L.get("type") != "overlay" or not L.get("file") or not _is_captions(L) or L.get("speed"):
            continue
        s, e = int(L["start"]), int(L["end"])
        over = [x for x in S if int(x["start"]) <= e and int(x["end"]) >= s]
        if len(over) < 2 and not (over and (int(over[0]["start"]) != s or int(over[0]["end"]) != e)):
            continue
        bounds = sorted({s, e + 1, *[max(s, int(x["start"])) for x in over], *[min(e, int(x["end"])) + 1 for x in over]})
        pieces = []
        for a, b in zip(bounds, bounds[1:]):
            if b <= a:
                continue
            p = copy.deepcopy(L)
            p["start"], p["end"], p["in"] = a, b - 1, int(L.get("in", 0)) + a - s
            pieces.append(p)
        if len(pieces) < 2:
            continue
        i = P["layers"].index(L)
        P["layers"][i:i + 1] = pieces
        n += 1
    if n:
        unique_ids(P)
    return n


def apply(plan: dict, ops: list[dict], tag: str = "m", copies: bool = True,
          build: Path | None = None) -> tuple[dict, list[str], list[dict]]:
    """The operations in order on a copy of the plan -> (the new plan, a line per change, the tool steps to run:
    graphics' copies and new graphics, their settings, captions' words). copies=False = a preview: the graphics keep
    their folders and new ones show their template, nothing is made. build = the video's build folder (where a new
    graphic goes on save). EditError names the operation it cannot do."""
    from . import overlay_settings as OS
    P = TR.strip(unique_ids(copy.deepcopy(plan)))          # (a transition's copies: made again after the changes)
    frames0 = int(P.get("frames") or 0)
    sh0 = {id(x) for x in shots(P)}                         # a logo, a progress bar over the whole video: it stays so
    whole = {str(L["id"]): L.get("in") for L in P["layers"] if id(L) not in sh0 and L.get("id")
             and L.get("type") in ("overlay", "solid") and not _is_captions(L)
             and int(L.get("start", 0)) <= 0 and int(L.get("end", -1)) >= frames0 - 1}
    P.setdefault("cues", [])
    fps = float(P["fps"])
    done: list[str] = []
    steps: list[dict] = []
    locked = sound_mode(P) == "fixed"
    attach_captions(P)                                      # (state() draws the same pieces: the page names them)
    made: dict[str, str] = {}                               # a graphic's folder -> its copy's
    decl: dict[str, list] = {}

    def declared(folder: Path) -> list:
        if str(folder) not in decl:
            try:
                decl[str(folder)] = OS.declared(folder)
            except (OSError, ValueError):
                decl[str(folder)] = []
        return decl[str(folder)]

    def own_copy(L: dict) -> Path:
        """The folder the change goes into: the graphic's copy for this save (made once), the folder itself in a
        preview."""
        old = Path(L["file"]).parent
        if not copies or str(old) in made.values():
            return old
        if str(old) not in made:                             # one copy per graphic, every layer that shows it moves
            new = old.with_name(re.sub(r"_m\d+$", "", old.name) + f"_{tag}")
            made[str(old)] = str(new)
            for x in P["layers"]:
                if x.get("file") and Path(x["file"]).parent == old:
                    x["file"] = str(new / f"{new.name}.mov")
            steps.append({"op": "copy", "from": str(old), "to": str(new)})
        return Path(made[str(old)])

    def original(folder: Path) -> Path:
        """A graphic's folder as it is on disk (its copy for this save is made only when the save runs)."""
        return Path(next((a for a, b in made.items() if b == str(folder)), str(folder)))

    for k, o in enumerate(ops, 1):
        op = o.get("op")
        try:
            if op in SHOT_OPS and locked:
                raise EditError(I18N.t("this video's sound was made in a way the Editor cannot cut again - its "
                                       "shots' timing stays (ask Claude)"))
            if op == "trim":
                _trim(P, _find(P, str(o["shot"])), "start" if o.get("side") == "start" else "end", int(o["by"]), done, fps)
            elif op == "delete":
                S = _find(P, str(o["shot"]))
                if len(shots(P)) < 2:
                    raise EditError(I18N.t("the only shot cannot go"))
                s, e = int(S["start"]), int(S["end"])
                _cut(P, s, e)
                done.append(f"{o['shot']} deleted ({_span({'start': s, 'end': e}, fps)}, {e - s + 1} frames): what "
                            "came after moved up")
            elif op == "roll":
                _roll(P, _find(P, str(o["shot"])), int(o["by"]), done, fps)
            elif op == "move":
                _move(P, _find(P, str(o["shot"])), int(o["to"]), done, fps)
            elif op == "split":
                _split(P, _find(P, str(o["shot"])), int(o["at"]), done, fps)
            elif op == "speed":
                _set_speed(P, _find(P, str(o["shot"])), float(o["speed"]), done, fps)
            elif op == "slip":
                _slip(P, _find(P, str(o["shot"])), int(o["by"]), done, fps)
            elif op == "take":
                for L in _take(P, _find(P, str(o["shot"])), str(o["src"]), int(o.get("in", 0)), done, fps):
                    inn, span = int(L.get("in", 0)), int((int(L["end"]) - int(L["start"])) * _speed(L) + 1e-6)
                    lst = cue_list(P, own_copy(L), original(_graphic_folder(L)))
                    lst[:] = [c for c in lst if not inn <= int(c["f0"]) <= inn + span]
            elif op == "clipadd":
                _clip_add(P, str(o["src"]), int(o.get("in", 0)), int(o["len"]), int(o["to"]), done, fps)
            elif op == "shotdup":
                _shot_dup(P, _find(P, str(o["shot"])), done, fps)
            elif op == "volume":
                if sound_mode(P) != "follows":
                    raise EditError(I18N.t("this video's sound is not its clips' own - change the song's volume instead"))
                S = _find(P, str(o["shot"]))
                db = max(VOL_MIN, min(VOL_MAX, round(float(o["db"]), 1)))
                if db:
                    S["sound_db"] = db
                else:
                    S.pop("sound_db", None)
                done.append(f"{S['id']}: its sound " + ("muted" if db <= VOL_MIN else f"{db:+g} dB" if db else "as it was")
                            + f" ({_span(S, fps)})")
            elif op == "song":
                if sound_mode(P) != "song":
                    raise EditError(I18N.t("this video has no song to change"))
                au = P["audio"] = _audio(P)
                cut = dict(_dict(au.get("cut")))
                orig = cut.get("from") or str(song_source(P))
                start = max(0.0, min(3600.0, float(o.get("start", song_start(P)))))   # (a volume alone: where it was)
                db = max(SONG_DB[0], min(SONG_DB[1], float(o.get("db", cut.get("db", 0)))))
                au["cut"] = {"from": orig, "start_s": round(start, 3), "db": round(db, 1)}
                done.append(f"the song: from {int(start // 60)}:{start % 60:05.2f} of it, {db:+g} dB")
            elif op == "gmove":
                L = _layer(P, str(o["layer"]))
                by = int(o["by"])
                if int(L["start"]) + by < 0 or int(L["end"]) + by > int(P["frames"]) - 1:
                    raise EditError(I18N.t("{frame} is outside the video", frame=f"f{int(L['start']) + by}"
                                    if int(L["start"]) + by < 0 else f"f{int(L['end']) + by}"))
                EL._shift(L, by)
                L.pop("land", None)
                done.append(f"{L['id']} moved {by:+d} frame{'s' if abs(by) != 1 else ''} (now {_span(L, fps)})")
            elif op == "gtrim":
                _gtrim(P, _layer(P, str(o["layer"])), "start" if o.get("side") == "start" else "end", int(o["by"]),
                       done, fps)
            elif op == "gfit":
                L = _layer(P, str(o["layer"]))
                _gfit(L, str(o.get("key")), bool(o.get("value")))
                done.append(f"{L['id']}: {o.get('key')} {'on' if o.get('value') else 'off'}")
            elif op == "gdelete":
                L = _layer(P, str(o["layer"]))
                f = _graphic_folder(L) if L.get("file") else None
                gone = [x for x in P["layers"] if x is L or (o.get("all") and f is not None and x.get("file")
                                                             and _graphic_folder(x) == f)]
                P["layers"] = [x for x in P["layers"] if not any(x is g for g in gone)]
                done.append(f"{L['id']} removed ({_span(L, fps)})" + (f" with its {len(gone) - 1} other piece(s)"
                                                                      if len(gone) > 1 else ""))
            elif op == "gadd":
                lid, tid = str(o["id"]), str(o["template"])
                if not re.fullmatch(r"[A-Za-z][\w-]{0,40}", lid) or any(x.get("id") == lid for x in P["layers"]):
                    raise EditError(I18N.t("a new graphic needs a name of its own"))
                folder = template_folder(tid)
                if folder is None:
                    raise EditError(I18N.t("no template {template}", template=tid))
                N = int(P["frames"])
                f = int(o["f"])
                if not 0 <= f < N:
                    raise EditError(I18N.t("{frame} is outside the video", frame=f"f{f}"))
                ln = max(1, int(o.get("len") or round(float(OS.conf(folder).get("frames") or fps * 3)
                                                      / float(OS.conf(folder).get("fps") or fps) * fps)))
                vals, bad = OS.check(declared(folder), o.get("values") or {})
                if bad:
                    raise EditError("; ".join(bad))
                L = {"type": "overlay", "id": lid, "file": str(folder / f"{lid}.mov"), "start": f,
                     "end": min(N - 1, f + ln - 1), "blend": "normal", NEW_KEY: {"template": tid, "values": vals}}
                L.update(in_shot(folder, P))                # (0.6.1: behind you / glass / on your face, as it was made)
                P["layers"].append(L)                       # over everything
                done.append(f"{lid}: the template {tid} added at {_span(L, fps)}")
            elif op in FX_OPS:
                try:
                    line = FX.apply_op(P, o, talk=_talking(P))
                except FX.FxError as e:
                    raise EditError(str(e)) from None
                done.append(re.sub(r"\bf(\d+)\b", lambda m: _tcf(int(m[1]), fps), line))
            elif op in TR_OPS:
                try:
                    line = TR.apply_op(P, o)
                except TR.TransError as e:
                    raise EditError(str(e)) from None
                done.append(re.sub(r"\bf(\d+)\b", lambda m: _tcf(int(m[1]), fps), line))
            elif op in KF.KEY_OPS:
                S = _find(P, str(o["shot"]))
                if S.get("type") != "clip":
                    raise EditError(I18N.t("keyframes move a clip's picture - this scene is a graphic"))
                try:
                    line = KF.apply_op(P, S, o)
                except KF.KeyError_ as e:
                    raise EditError(str(e)) from None
                done.append(re.sub(r"\bf(\d+)\b", lambda m: _tcf(int(m[1]), fps), line))
            elif op == "captions":                          # many captions' words at once (find & replace, case)
                lists: dict[str, tuple[list, list]] = {}
                for e in o.get("edits") or []:
                    L = next((x for x in P["layers"] if x.get("id") == e.get("graphic") and x.get("file")), None)
                    if L is None:
                        raise EditError(I18N.t("no graphic {graphic}", graphic=str(e.get("graphic"))))
                    if L.get(NEW_KEY):
                        raise EditError(I18N.t("a graphic added here gets its captions changed after Save"))
                    fo = own_copy(L)
                    if str(fo) not in lists:
                        lists[str(fo)] = (cue_list(P, fo, original(_graphic_folder(L))), [])
                    lists[str(fo)][1].append(e)
                n = 0
                for lst, es in lists.values():              # (from the last: a caption that goes renumbers the rest)
                    for e in sorted(es, key=lambda e: -int(e["cue"])):
                        k = int(e["cue"])
                        if not 0 <= k < len(lst):
                            raise EditError(I18N.t("no caption {n}", n=k + 1))
                        txt = " ".join(str(e.get("text") or "").split())
                        if txt:
                            lst[k] = {**caption_words(lst[k], txt), "_e": 1}
                        else:
                            del lst[k]
                        n += 1
                done.append(f"{n} captions' words changed at once")
            elif op in ("words", "set", "caption", "capmove", "captrim", "capsplit", "capmerge", "capadd", "look"):
                L = next((x for x in P["layers"] if x.get("id") == o.get("graphic") and x.get("file")), None)
                if L is None:
                    raise EditError(I18N.t("no graphic {graphic}", graphic=str(o.get("graphic"))))
                src = original(_graphic_folder(L))          # its settings and captions are read from the original
                if op.startswith("cap") and L.get(NEW_KEY):
                    raise EditError(I18N.t("a graphic added here gets its captions changed after Save"))
                if op == "caption":
                    lst = cue_list(P, own_copy(L), src)
                    k = int(o["cue"])
                    if not 0 <= k < len(lst):
                        raise EditError(I18N.t("no caption {n}", n=k + 1))
                    txt = " ".join(str(o.get("text") or "").split())
                    if txt:
                        lst[k] = {**caption_words(lst[k], txt), "_e": 1}
                    else:
                        del lst[k]
                    done.append(f"caption {k + 1}: " + (f"\"{txt}\"" if txt else "removed"))
                    continue
                if op in ("capmove", "captrim"):
                    _cap_time(P, L, o, op, own_copy(L), src, steps, done, fps)
                    continue
                if op == "capmerge":
                    _cap_merge(L, o, cue_list(P, own_copy(L), src), done)
                    continue
                if op in ("capsplit", "capadd"):
                    if not int(L["start"]) <= int(o["at"]) <= int(L["end"]):
                        raise EditError(I18N.t("{frame} is outside {graphic}", frame=f"f{int(o['at'])}", graphic=L["id"]))
                    (_cap_split if op == "capsplit" else _cap_add)(P, L, o, own_copy(L), src, done, fps)
                    continue
                if op == "look":                            # a ready-made look = all its values at once
                    pre = OS.presets(src)
                    if str(o.get("look")) not in pre:
                        raise EditError(I18N.t("{graphic} has no look {look}", graphic=L["id"], look=str(o.get("look"))))
                    clean, _ = OS.check(declared(src), pre[str(o["look"])]["values"])
                    if L.get(NEW_KEY):
                        L[NEW_KEY]["values"].update(clean)
                    else:
                        folder = own_copy(L)
                        P.setdefault(VALUES_KEY, {}).setdefault(str(folder), {}).update(clean)
                        steps.append({"op": "values", "folder": str(folder), "values": clean})
                    done.append(f"{o['graphic']}: the look \"{pre[str(o['look'])]['label']}\"")
                    continue
                key, value = str(o["key"]), o.get("value")
                clean, bad = OS.check(declared(src), {key: value})
                if bad or key not in clean:
                    raise EditError("; ".join(bad) or I18N.t("{graphic} has no setting {key}", graphic=L["id"], key=key))
                value = clean[key]
                if L.get(NEW_KEY):                          # a new graphic: its values until it is made
                    L[NEW_KEY]["values"][key] = value
                else:
                    folder = own_copy(L)
                    P.setdefault(VALUES_KEY, {}).setdefault(str(folder), {})[key] = value
                    steps.append({"op": "set", "folder": str(folder), "key": key, "value": value})
                done.append(f"{o['graphic']}: {key} = \"{value}\"")
            elif op == "sfx":
                from . import sfx as SFX
                f, kind = int(o["f"]), str(o["kind"])
                to = o.get("to", f)
                to = None if to is None else int(to)
                if to is not None and not 0 <= to < int(P["frames"]):
                    raise EditError(I18N.t("{frame} is outside the video", frame=f"f{to}"))
                ed = {"f": f, "kind": kind, "to": to}
                if o.get("db") is not None:
                    ed["db"] = max(-12.0, min(12.0, float(o["db"])))
                if o.get("sound"):
                    ed["sound"] = _sound_file(SFX, str(o["sound"]))
                _sfx_edits(P).append(ed)
                what = ("dropped" if to is None else ", ".join(
                    ([f"moved to {_tcf(to, fps)}"] if to != f else [])
                    + ([f"{ed['db']:+g} dB"] if "db" in ed else []) + ([f"the sound {ed['sound']}"] if "sound" in ed
                                                                       else [])) or "kept")
                done.append(f"sound effect {kind} at {_tcf(f, fps)} {what}")
            elif op == "sfxadd":
                from . import sfx as SFX
                f, kind = int(o["f"]), SFX.ALIASES.get(str(o["kind"]), str(o["kind"]))
                if kind not in SFX.KINDS:
                    raise EditError(I18N.t("no sound effect kind {kind}", kind=kind))
                if not 0 <= f < int(P["frames"]):
                    raise EditError(I18N.t("{frame} is outside the video", frame=f"f{f}"))
                q = {"f": f, "kind": kind, "what": "added in the Editor"}
                if o.get("db") is not None:
                    q["db"] = max(-12.0, min(12.0, float(o["db"])))
                if o.get("sound"):
                    q["sound"] = _sound_file(SFX, str(o["sound"]))
                P["cues"].append(q)
                done.append(f"sound effect {kind} added at {_tcf(f, fps)}" + (f" ({q['sound']})" if q.get("sound") else ""))
            else:
                raise EditError(I18N.t("no such change: {op}", op=str(op)))
            unique_ids(P)
        except EditError as e:
            raise EditError(I18N.t("change {k}: {why}", k=k, why=str(e))) from None
        except (KeyError, TypeError, ValueError) as e:
            raise EditError(I18N.t("change {k}: {why}", k=k, why=str(e))) from None
    _fit_layers(P, whole, {str(o.get("layer")) for o in ops if o.get("layer")})
    if any(o.get("op") == "song" for o in ops):              # the song cut again from the song itself
        steps.append({"op": "songcut", **P["audio"]["cut"]})
    elif int(P["frames"]) != frames0 and _draft_song(P) and sound_mode(P) == "song" \
            and not _dict(_audio(P).get("cut")).get("from"):   # a music draft longer / shorter: its excerpt no
        P["audio"] = {**_audio(P), "cut": {"from": str(song_source(P)), "start_s": song_start(P), "db": 0.0}}
        steps.append({"op": "songcut", **P["audio"]["cut"]})   # longer fits - cut again from the song itself
    for folder, ch in (P.get(CAPTIONS_KEY) or {}).items():  # a captions graphic's captions, written whole
        steps.append({"op": "capfile", "folder": folder,
                      "cues": [{k: v for k, v in c.items() if k != "_e"} for c in ch["cues"]]})
    if copies:                                              # the new graphics' own folders (made on save)
        b = Path(build) if build else None
        news = [L for L in P["layers"] if L.get(NEW_KEY)]
        for i, L in enumerate(news, 1):
            if b is None:
                raise EditError(I18N.t("a new graphic needs the video's folder"))
            new = L.pop(NEW_KEY)
            folder = b / "overlays" / f"n{tag.lstrip('m')}_{i:02d}_{new['template']}"
            L["file"] = str(folder / f"{folder.name}.mov")
            steps.append({"op": "new", "template": new["template"], "to": str(folder), "frames": _len(L),
                          "values": new["values"]})
    TR.build(P)                                             # the transitions' copies, from the shots as they are now
    return P, done, steps


def _sound_file(SFX, name: str) -> str:
    """A recorded sound of this PC's library by its file (as sounds.json names it), or "made-up"."""
    if name == "made-up":
        return name
    lib = SFX.Library.load()
    if lib is None or lib.entry(name) is None:
        raise EditError(I18N.t("no sound {sound} in the library", sound=name))
    return name


def saved(P: dict) -> dict:
    """The plan as it is written: the engine's own keys out."""
    for k in (VALUES_KEY, CAPTIONS_KEY):
        P.pop(k, None)
    for L in P.get("layers", []):
        L.pop(NEW_KEY, None)
    return P


def record(base_name: str, ops: list[dict], done: list[str]) -> str:
    """build\\edit_vN.list for this save - a record Claude reads (what the user changed by hand), not a list to apply
    again: the Editor's changes are in order, each on the plan before it."""
    import json
    return ("# made by the Editor (the app) on " + base_name + " - the user's own changes, IN ORDER, each on the\n"
            "# plan the ones before it made (a record: draft_edit.py --apply does not read these lines)\n"
            + "".join(f"# {ln}\n" for ln in done)
            + "".join(f"# op {json.dumps(o, ensure_ascii=False)}\n" for o in ops))


def caption_retime(cue: dict, f0: int, f1: int) -> dict:
    """A caption in other frames: each word keeps its share of them (its start and end scaled), the last one ends on
    the caption's end - the word being said stays in step."""
    a0, a1 = int(cue["f0"]), int(cue["f1"])
    k = (f1 - f0) / max(1, a1 - a0)
    words, prev = [], f0 - 1
    for w in cue["words"]:                               # in order, never over the word before it, inside the caption
        a = min(f1, max(f0 + int(round((int(w[1]) - a0) * k)), prev + 1))
        b = min(f1, max(f0 + int(round((int(w[2]) - a0) * k)), a))
        words.append([w[0], a, b])
        prev = b
    if words:
        words[-1][2] = f1
    return {**cue, "f0": f0, "f1": f1, "words": words}


def caption_words(cue: dict, text: str) -> dict:
    """A caption with new words in the same frames: each word gets a share of them by its length."""
    words = text.split()
    if not words:
        raise EditError(I18N.t("a caption needs words"))
    f0, f1 = int(cue["f0"]), int(cue["f1"])
    n = f1 - f0 + 1
    weights = [max(1, len(w)) for w in words]
    tot, acc, out = sum(weights), 0, []
    for w, k in zip(words, weights):
        a = f0 + round(n * acc / tot)
        acc += k
        b = f0 + round(n * acc / tot) - 1
        out.append([w, a, max(a, b)])
    out[-1][2] = f1
    return {**cue, "words": out}


def sound_segments(P: dict) -> list[tuple]:
    """The shots' parts of their clips for the sound cut again (draft_edit.cut_sound): (clip, first source frame,
    last, speed, the shot's timeline frames, its own volume in dB)."""
    out = []
    S = shots(P)
    for i, L in enumerate(S):
        a = EL._src_at(L, int(L["start"]))
        sp = _speed(L)
        n_t = min(_len(L), int(S[i + 1]["start"]) - int(L["start"])) if i + 1 < len(S) else _len(L)   # (an overlap
        n = int(round(max(1, n_t) * sp))                                                              # heard once)
        out.append((L["src"], a, a + max(1, n) - 1, sp, max(1, n_t), float(L.get("sound_db") or 0)))
    return out


# ------------------------------------------------------------------------------------------------- self-check
def selfcheck() -> dict:
    """Known answers on a made-up plan: three shots with a caption piece each, a title at the first's start and a pill
    at the second's end, a plan cue."""
    import time
    t0, lines, ok = time.time(), [], True

    def case(name, cond):
        nonlocal ok
        ok = ok and bool(cond)
        lines.append(f"{'PASS' if cond else 'FAIL'} {name}")

    def plan():
        return {"fps": 25.0, "frames": 300, "width": 1080, "height": 1920, "made_by": {"sound": "talk"},
                "sources": {"A": {"frames": 1000}},
                "layers": [{"type": "clip", "id": "s01_A", "src": "A", "start": 0, "end": 99, "in": 100},
                           {"type": "clip", "id": "s02_A", "src": "A", "start": 100, "end": 199, "in": 300,
                            "zoom": {"keys": [[100, 1.0, "smooth"], [140, 1.2, "hold"]]}},
                           {"type": "clip", "id": "s03_A", "src": "A", "start": 200, "end": 299, "in": 500},
                           {"type": "overlay", "id": "cap", "file": "x/captions/captions.mov", "start": 0, "end": 99, "in": 100},
                           {"type": "overlay", "id": "cap_b", "file": "x/captions/captions.mov", "start": 100, "end": 199, "in": 300},
                           {"type": "overlay", "id": "cap_c", "file": "x/captions/captions.mov", "start": 200, "end": 299, "in": 500},
                           {"type": "overlay", "id": "title", "file": "x/title/title.mov", "start": 0, "end": 60},
                           {"type": "overlay", "id": "pill", "file": "x/pill/pill.mov", "start": 160, "end": 199}],
                "cues": [{"f": 250, "kind": "pop"}]}
    lay = lambda P, i: next(x for x in P["layers"] if x["id"] == i)    # noqa: E731
    has = lambda P, i: any(x["id"] == i for x in P["layers"])         # noqa: E731
    P, done, _ = apply(plan(), [{"op": "trim", "shot": "s01_A", "side": "start", "by": -10}])
    case("trim a shot's start shorter: 10 frames go, its caption piece with it, the title keeps its first frames, "
         "the rest moves up", P["frames"] == 290 and lay(P, "s01_A")["in"] == 110 and lay(P, "s01_A")["end"] == 89
         and lay(P, "cap")["in"] == 110 and lay(P, "title").get("in", 0) == 0 and lay(P, "title")["start"] == 0
         and lay(P, "s02_A")["start"] == 90 and P["cues"][0]["f"] == 240)
    P, _, _ = apply(plan(), [{"op": "trim", "shot": "s02_A", "side": "end", "by": -15}])
    case("trim a shot's end shorter: the pill keeps its length and exit, moved up with the cut",
         lay(P, "s02_A")["end"] == 184 and lay(P, "pill")["end"] == 184 and lay(P, "pill")["start"] == 145
         and lay(P, "pill").get("in", 0) == 0 and lay(P, "cap_b")["end"] == 184 and lay(P, "s03_A")["start"] == 185)
    P, _, _ = apply(plan(), [{"op": "trim", "shot": "s02_A", "side": "end", "by": 12}])
    case("trim a shot's end longer: 12 more frames of its clip, the pill stays at the end, the rest moves on",
         P["frames"] == 312 and lay(P, "s02_A")["end"] == 211 and lay(P, "cap_b")["end"] == 211
         and lay(P, "pill")["start"] == 172 and lay(P, "pill")["end"] == 211 and lay(P, "s03_A")["start"] == 212
         and P["cues"][0]["f"] == 262)
    P, _, _ = apply(plan(), [{"op": "trim", "shot": "s02_A", "side": "start", "by": 20}])
    case("trim a shot's start longer: 20 earlier frames of its clip (in 280), its caption piece too",
         lay(P, "s02_A")["in"] == 280 and lay(P, "s02_A")["start"] == 100 and lay(P, "s02_A")["end"] == 219
         and lay(P, "cap_b")["in"] == 280 and lay(P, "s03_A")["start"] == 220 and P["frames"] == 320)
    P, _, _ = apply(plan(), [{"op": "delete", "shot": "s02_A"}])
    case("delete a shot: it, its caption piece and the pill go, what came after closes up",
         P["frames"] == 200 and not any(x["id"] in ("s02_A", "cap_b", "pill") for x in P["layers"])
         and lay(P, "s03_A")["start"] == 100)
    P, _, _ = apply(plan(), [{"op": "roll", "shot": "s01_A", "by": 8}])
    case("move a cut 8 frames later: the first shot longer, the next one shorter from its start, the length stays",
         P["frames"] == 300 and lay(P, "s01_A")["end"] == 107 and lay(P, "s02_A")["start"] == 108
         and lay(P, "s02_A")["in"] == 308 and lay(P, "cap_b")["in"] == 308 and lay(P, "cap")["end"] == 107)
    P, _, _ = apply(plan(), [{"op": "roll", "shot": "s02_A", "by": -6}])
    case("move a cut earlier: the pill at the cut moves with it", lay(P, "s02_A")["end"] == 193
         and lay(P, "pill")["end"] == 193 and lay(P, "s03_A")["in"] == 494)
    P, _, _ = apply(plan(), [{"op": "sfx", "f": 250, "kind": "pop", "to": 244},
                             {"op": "trim", "shot": "s01_A", "side": "end", "by": -4}])
    case("a sound effect moved, then a trim before it: the edit moves up with the timeline",
         P["sfx"]["edits"] == [{"f": 246, "kind": "pop", "to": 240}])
    bad = []
    for o in ({"op": "trim", "shot": "s01_A", "side": "start", "by": 101}, {"op": "trim", "shot": "zz", "side": "end", "by": -1},
              {"op": "roll", "shot": "s03_A", "by": 2}, {"op": "trim", "shot": "s01_A", "side": "end", "by": -100},
              {"op": "speed", "shot": "s01_A", "speed": 9}, {"op": "split", "shot": "s01_A", "at": 0},
              {"op": "move", "shot": "s01_A", "to": 3}, {"op": "gmove", "layer": "pill", "by": 200},
              {"op": "gadd", "id": "cap", "template": "lower-third", "f": 10}):
        try:
            apply(plan(), [o])
            bad.append(o)
        except EditError:
            pass
    case("what cannot be done is refused (no room in its clip, no such shot, the last cut, the whole shot, a speed "
         "out of range, a split on the first frame, no such place, a graphic off the end, a name already used)", not bad)
    fx = plan()
    fx["made_by"] = {}
    fx["audio"] = {"path": "C:/x/build/vo_by_hand.wav"}
    try:
        apply(fx, [{"op": "delete", "shot": "s01_A"}])
        locked = False
    except EditError:
        locked = True
    case("a sound made some other way locks the shots' timing", locked and sound_mode(fx) == "fixed"
         and sound_mode({**fx, "audio": {"path": "C:/x/song.mp3"}}) == "song")
    draft = str(Path("C:/x/build/draft/v1_sound.m4a"))
    case("the sound of a quick draft: the clips' own (cut again) or a music draft's song (it stays); a hand-written "
         "plan's made_by / audio as one string",
         sound_mode({"made_by": {"sound": "clips"}, "audio": {"path": draft}}) == "follows"
         and sound_mode({"made_by": {"sound": "music"}, "audio": {"path": draft}}) == "song"
         and sound_mode({"made_by": "by hand", "audio": "C:/x/song.mp3"}) == "song"
         and song_source({"made_by": "by hand", "audio": "C:/x/song.mp3"}) == Path("C:/x/song.mp3"))
    W2 = plan()
    W2["layers"].append({"type": "overlay", "id": "logo", "file": "x/logo/logo.mov", "start": 0, "end": 299, "in": 7})
    P, _, _ = apply(W2, [{"op": "speed", "shot": "s03_A", "speed": 4}])
    P2, _, _ = apply(W2, [{"op": "trim", "shot": "s01_A", "side": "start", "by": -20}])
    P3, _, _ = apply(W2, [{"op": "gtrim", "layer": "logo", "side": "end", "by": -50}])
    case("a logo over the whole video stays over it after a speed change or a trim (from its own first frame), unless "
         "it was trimmed itself", (lay(P, "logo")["start"], lay(P, "logo")["end"], lay(P, "logo")["in"]) == (0, P["frames"] - 1, 7)
         and (lay(P2, "logo")["start"], lay(P2, "logo")["end"], lay(P2, "logo")["in"]) == (0, P2["frames"] - 1, 7)
         and lay(P3, "logo")["end"] == 249 and all(int(L["start"]) >= 0 and int(L["end"]) <= P["frames"] - 1
                                                   for L in P["layers"] if L.get("type") == "overlay"))
    dp = plan()
    dp["layers"][1]["jumps"] = [[100, 300], [150, 300], [153, 303]]
    P, _, _ = apply(dp, [{"op": "shotdup", "shot": "s02_A"}])
    cp_ = next(x for x in P["layers"] if x["id"] == "s04_A")
    case("a shot duplicated: right after itself, its zoom keys and stutter moved with it, the rest moved on",
         (cp_["start"], cp_["end"]) == (200, 299) and cp_["zoom"]["keys"][0][0] == 200 and cp_["jumps"][1][0] == 250
         and lay(P, "s03_A")["start"] == 300 and P["frames"] == 400 and [x["id"] for x in shots(P)][1:3] == ["s02_A", "s04_A"])
    ph = plan()
    ph["sources"]["F"] = {"frames": 1, "photo": True}
    ph["layers"][2] = {"type": "clip", "id": "s03_F", "src": "F", "start": 200, "end": 299, "in": 0, "hold": True}
    P, _, _ = apply(ph, [{"op": "trim", "shot": "s03_F", "side": "end", "by": 50}])
    case("a photo is made longer", lay(P, "s03_F")["end"] == 349 and P["frames"] == 350)
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as td:            # a music draft: its song itself, from where the draft started
        song = Path(td) / "song.mp3"
        song.write_bytes(b"x")
        md = plan()
        md["made_by"] = {"sound": "music", "music": str(song), "music_start_s": 31.5}
        md["audio"] = {"path": str(Path(td) / "build" / "draft" / "v1_sound.m4a")}
        P, _, st = apply(md, [{"op": "speed", "shot": "s03_A", "speed": 0.5}])
        P4, _, st4 = apply(md, [{"op": "move", "shot": "s03_A", "to": 0}])
        case("a music draft made longer: its song cut again from the song itself where the draft started it (its "
             "excerpt would end in silence); a change that keeps the length keeps the excerpt",
             sound_mode(md) == "song" and song_source(md) == song and song_start(md) == 31.5
             and {"op": "songcut", "from": str(song), "start_s": 31.5, "db": 0.0} in st
             and not any(x.get("op") == "songcut" for x in st4))
    with tempfile.TemporaryDirectory() as td:            # a song mixed with its effects from 12.5 s (sfx.py --song-start)
        mix = Path(td) / "sfx" / "x_v2_mix.wav"
        mix.parent.mkdir()
        mix.with_name("x_v2_sfx.json").write_text(json.dumps({"song": {"path": "C:/x/song.mp3", "start_s": 12.5}}),
                                                  encoding="utf-8")
        sp = {"audio": {"path": str(mix)}}
        S2 = copy.deepcopy(sp)
        S2["layers"], S2["frames"], S2["fps"] = [], 100, 25.0
        ok_cut = False
        try:
            S3, _, _ = apply(S2, [{"op": "song", "db": -3}])
            ok_cut = S3["audio"]["cut"]["start_s"] == 12.5
        except EditError:
            pass
        case("a mix's song plays from where the mix starts it, and a volume change alone keeps that start",
             song_of(sp) == Path("C:/x/song.mp3") and song_start(sp) == 12.5 and ok_cut)
    P, _, _ = apply(plan(), [{"op": "move", "shot": "s03_A", "to": 0}])
    case("move the last shot first: it takes its caption piece and the cue on it, the title and the pill go with the "
         "shots they start on, the length stays", P["frames"] == 300 and lay(P, "s03_A")["start"] == 0
         and lay(P, "s01_A")["start"] == 100 and lay(P, "s02_A")["start"] == 200 and lay(P, "cap_c")["start"] == 0
         and lay(P, "cap_c")["in"] == 500 and lay(P, "title")["start"] == 100 and lay(P, "title")["end"] == 160
         and lay(P, "pill")["start"] == 260 and lay(P, "pill")["end"] == 299 and P["cues"][0]["f"] == 50
         and lay(P, "s02_A")["zoom"]["keys"][1][0] == 240)
    P, _, _ = apply(plan(), [{"op": "move", "shot": "s01_A", "to": 2}])
    case("move the first shot last", lay(P, "s02_A")["start"] == 0 and lay(P, "s03_A")["start"] == 100
         and lay(P, "s01_A")["start"] == 200 and lay(P, "s01_A")["end"] == 299 and lay(P, "cap")["start"] == 200
         and lay(P, "pill")["start"] == 60 and P["cues"][0]["f"] == 150)
    P, _, _ = apply(plan(), [{"op": "split", "shot": "s02_A", "at": 150}])
    case("split a shot: two shots, its caption piece split with it", lay(P, "s02_A")["end"] == 149
         and lay(P, "s02_A_2")["start"] == 150 and lay(P, "s02_A_2")["in"] == 350 and lay(P, "cap_b")["end"] == 149
         and lay(P, "cap_b_2")["start"] == 150 and lay(P, "cap_b_2")["in"] == 350 and P["frames"] == 300
         and len(shots(P)) == 4)
    P, done, _ = apply(plan(), [{"op": "speed", "shot": "s02_A", "speed": 2}])
    case("speed a shot up 2x: half its frames, its caption piece at 2x, its punch-in sooner, the pill's exit at its "
         "end, the rest moves up", lay(P, "s02_A")["end"] == 149 and lay(P, "s02_A")["speed"] == 2
         and lay(P, "cap_b")["speed"] == 2 and lay(P, "cap_b")["end"] == 149 and lay(P, "pill")["end"] == 149
         and lay(P, "pill")["start"] == 110 and lay(P, "s03_A")["start"] == 150 and P["frames"] == 250
         and P["cues"][0]["f"] == 200 and lay(P, "s02_A")["zoom"]["keys"][1][0] == 120)
    P, _, _ = apply(plan(), [{"op": "speed", "shot": "s02_A", "speed": 0.5},
                             {"op": "trim", "shot": "s02_A", "side": "end", "by": 10}])
    case("slow a shot to 0.5x, then trim it longer: 200 frames, then 10 more (5 more of its clip)",
         lay(P, "s02_A")["end"] == 309 and lay(P, "s02_A")["speed"] == 0.5 and room(P, lay(P, "s02_A"))[1] > 0
         and lay(P, "s03_A")["start"] == 310 and P["frames"] == 410
         and sound_segments(P)[1] == ("A", 300, 404, 0.5, 210, 0.0))
    P, _, _ = apply(plan(), [{"op": "gmove", "layer": "title", "by": 30}, {"op": "gtrim", "layer": "title", "side": "end", "by": -10},
                             {"op": "gtrim", "layer": "pill", "side": "start", "by": 5}, {"op": "gdelete", "layer": "cap", "all": True}])
    case("move a graphic, trim its end and another's start, remove the captions everywhere",
         lay(P, "title")["start"] == 30 and lay(P, "title")["end"] == 80 and lay(P, "pill")["start"] == 165
         and lay(P, "pill")["in"] == 5 and not any(has(P, i) for i in ("cap", "cap_b", "cap_c")))
    try:
        apply(plan(), [{"op": "set", "graphic": "title", "key": "main", "value": "One"}])
        refused = False
    except EditError:
        refused = True
    case("a setting the graphic does not declare is refused", refused)
    tpl = template_folder("lower-third")
    if tpl is not None:
        from . import overlay_settings as OS
        dk = next((d["id"] for d in OS.declared(tpl) if d.get("type") == "string"), None)
        ck = next((d["id"] for d in OS.declared(tpl) if d.get("type") == "color"), None)
        ops = [{"op": "gadd", "id": "add1", "template": "lower-third", "f": 40, "len": 50, "values": {}},
               {"op": "set", "graphic": "add1", "key": dk, "value": "Hello"},
               {"op": "set", "graphic": "add1", "key": ck, "value": "#FF0044"},
               {"op": "gmove", "layer": "add1", "by": 10}]
        P, _, st = apply(plan(), ops, copies=False)
        sv = state(P)
        g = next(x for x in sv["graphics"] if x["id"] == "add1")
        case("add a template: a new graphic over everything, its words and colour set before it is made (the preview "
             "shows the template)", g["start"] == 50 and g["end"] == 99 and g["values"][dk] == "Hello"
             and g["values"][ck] == "#ff0044" and g["new"] and not st and P["layers"][-1]["id"] == "add1")
        P, _, st = apply(plan(), ops, tag="m7", build=Path("x/build"))
        case("... saved: one step makes it from the template with its values, into the video's own folder",
             [s["op"] for s in st] == ["new"] and st[0]["to"].replace("\\", "/").endswith("x/build/overlays/n7_01_lower-third")
             and st[0]["frames"] == 50 and st[0]["values"][dk] == "Hello"
             and lay(P, "add1")["file"].replace("\\", "/").endswith("n7_01_lower-third/n7_01_lower-third.mov")
             and NEW_KEY not in lay(P, "add1"))
        P, _, _ = apply(plan(), ops[:1] + [{"op": "gfit", "layer": "add1", "key": "behind", "value": True},
                                           {"op": "gfit", "layer": "add1", "key": "pin", "value": True},
                                           {"op": "gfit", "layer": "add1", "key": "behind", "value": False}], copies=False)
        L1 = lay(P, "add1")
        a = (L1.get("follow"), L1.get("match"), "behind" in L1)
        P, _, _ = apply(P, [{"op": "gfit", "layer": "add1", "key": "pin", "value": False},
                            {"op": "gfit", "layer": "add1", "key": "glass", "value": True}], copies=False)
        L1 = lay(P, "add1")
        g = next(x for x in state(P)["graphics"] if x["id"] == "add1")
        case("a graphic part of the shot (gfit): behind me = moves with the camera, pinned = with the face, the "
             "footage's grain with either; glass + its shadow; the state shows the switches",
             a == ("face", True, False) and L1.get("glass") and L1.get("shadow") and "follow" not in L1
             and L1.get("match") and g["fit"] == {"behind": False, "glass": True, "guard": False, "pin": False})
    else:
        case("the lower-third template is there (tools\\overlays\\motion\\lower-third)", False)
    P, _, _ = apply(plan(), [{"op": "sfxadd", "f": 120, "kind": "pop", "db": -3},
                             {"op": "sfx", "f": 250, "kind": "pop", "db": 4}])
    case("add a sound effect, make another one louder", {"f": 120, "kind": "pop", "what": "added in the Editor", "db": -3.0}
         in P["cues"] and P["sfx"]["edits"] == [{"f": 250, "kind": "pop", "to": 250, "db": 4.0}])
    P, _, _ = apply(plan(), [{"op": "slip", "shot": "s02_A", "by": 20}])
    case("slip a shot 20 frames later in its clip: the same frames, its caption piece slips with it",
         lay(P, "s02_A")["in"] == 320 and lay(P, "s02_A")["start"] == 100 and lay(P, "s02_A")["end"] == 199
         and lay(P, "cap_b")["in"] == 320 and P["frames"] == 300)
    try:
        apply(plan(), [{"op": "slip", "shot": "s01_A", "by": -150}])
        case("a slip past its clip's start is refused", False)
    except EditError:
        case("a slip past its clip's start is refused", True)
    two = plan()
    two["sources"]["B"] = {"frames": 500, "source": str(Path("x/take_B.mp4"))}
    P, done, _ = apply(two, [{"op": "take", "shot": "s02_A", "src": "B", "in": 50}])
    case("another take in a shot's place: from its frame 50, the same frames",
         lay(P, "s02_A")["src"] == "B" and lay(P, "s02_A")["in"] == 50 and lay(P, "s02_A")["end"] == 199
         and "captions went" in done[-1])
    P, _, _ = apply(two, [{"op": "clipadd", "src": "B", "in": 10, "len": 40, "to": 1}])
    nw = next(x for x in shots(P) if x["src"] == "B")
    case("a clip added as a new shot at place 2: 40 frames from its frame 10, what came after moved on, a graphic "
         "before it stays", (nw["id"], nw["start"], nw["end"], nw["in"]) == ("s04_B", 100, 139, 10)
         and lay(P, "s02_A")["start"] == 140 and lay(P, "cap_b")["start"] == 140 and lay(P, "pill")["start"] == 200
         and lay(P, "title")["end"] == 60 and P["frames"] == 340 and [x["id"] for x in shots(P)][1] == "s04_B")
    gen = {"fps": 30.0, "frames": 300, "width": 1080, "height": 1920, "layers": [
        {"type": "overlay", "id": "logo", "file": "x/logo/logo.mov", "start": 0, "end": 299, "rect": [40, 40, 200, 200]},
        *[{"type": "overlay", "id": f"g{k}", "file": f"x/g{k}/g{k}.mov", "start": 100 * (k - 1), "end": 100 * k - 1}
          for k in (1, 2, 3)]]}
    case("a video made from zero: its full-frame graphics back to back are its scenes (the main track), a corner "
         "logo is not", [x["id"] for x in shots(gen)] == ["g1", "g2", "g3"]
         and [s["scene"] is not None for s in state(gen)["shots"]] == [True] * 3)
    P, _, _ = apply(gen, [{"op": "move", "shot": "g3", "to": 0}, {"op": "trim", "shot": "g1", "side": "end", "by": -20},
                          {"op": "trim", "shot": "g2", "side": "end", "by": 30}, {"op": "delete", "shot": "g3"}])
    case("its scenes reordered, trimmed (what comes after closes up), one held 30 frames past its end, one deleted",
         [(x["id"], x["start"], x["end"]) for x in shots(P)] == [("g1", 0, 79), ("g2", 80, 209)] and P["frames"] == 210
         and lay(P, "logo")["start"] == 0)
    P, _, _ = apply(plan(), [{"op": "volume", "shot": "s02_A", "db": -6}, {"op": "volume", "shot": "s03_A", "db": -99}])
    case("a shot's own sound softer, another muted: the sound cut again carries them",
         [s[5] for s in sound_segments(P)] == [0.0, -6.0, VOL_MIN])
    sg = plan()
    sg.pop("made_by")
    sg["audio"] = {"path": str(Path("refs/audio/song.mp3"))}
    P, _, st = apply(sg, [{"op": "song", "start": 12.5}, {"op": "song", "db": -3}])
    sv = state(P)
    case("the song from 12.5 s, 3 dB softer: one cut from the song itself on save, the Editor plays the song from there",
         P["audio"]["cut"] == {"from": str(Path("refs/audio/song.mp3")), "start_s": 12.5, "db": -3.0}
         and st[-1]["op"] == "songcut" and sv["song_cut"] == {"start_s": 12.5, "db": -3.0}
         and sv["song"] == str(Path("refs/audio/song.mp3")))
    try:
        apply(sg, [{"op": "volume", "shot": "s01_A", "db": -6}])
        case("a shot's own volume is refused under a song", False)
    except EditError:
        case("a shot's own volume is refused under a song", True)
    one = plan()
    one["layers"] = [x for x in one["layers"] if not x["id"].startswith("cap")] + [
        {"type": "overlay", "id": "words", "file": "x/captions/captions.mov", "start": 0, "end": 299}]
    P, _, _ = apply(one, [{"op": "move", "shot": "s03_A", "to": 0}])
    case("captions timed to the edit in one layer are cut with the shots: their words move with the shot they are "
         "said in", lay(P, "words_3")["start"] == 0 and lay(P, "words_3")["in"] == 200
         and lay(P, "words")["start"] == 100 and lay(P, "words")["in"] == 0 and lay(P, "words_2")["in"] == 100)
    import json
    import shutil
    import tempfile
    from . import overlay_settings as OS
    with tempfile.TemporaryDirectory() as td:            # a captions graphic of its own (the example's page + looks)
        cf = Path(td) / "captions"
        (cf / "assets").mkdir(parents=True)
        for n in ("index.html", "presets.json"):
            shutil.copy2(OS.EXAMPLES / "captions" / n, cf / n)
        cues = [{"f0": 100, "f1": 140, "words": [["one", 100, 119], ["two", 120, 140]]},     # in shot 1 (in 100)
                {"f0": 150, "f1": 180, "words": [["three", 150, 165], ["four", 166, 180]]},
                {"f0": 300, "f1": 360, "words": [["five", 300, 360]]}]                       # in shot 2 (in 300)
        (cf / "assets" / "captions.js").write_text("// test\nwindow.CAPTIONS = " + json.dumps({"fps": 25, "cues": cues}),
                                                   encoding="utf-8")
        cp = plan()
        for L in cp["layers"]:
            if L["id"].startswith("cap"):
                L["file"] = str(cf / "captions.mov")
        fr = lambda P: [(c["f0"], c["f1"]) for c in P[CAPTIONS_KEY][str(cf)]["cues"]]     # noqa: E731
        txt = lambda P: [" ".join(w[0] for w in c["words"]) for c in P[CAPTIONS_KEY][str(cf)]["cues"]]   # noqa: E731
        P, _, st = apply(cp, [{"op": "capmove", "graphic": "cap", "cue": 1, "by": 4},
                              {"op": "captrim", "graphic": "cap", "cue": 0, "side": "end", "to": 30}], copies=False)
        sv = state(P)
        c1 = next(c for c in sv["captions"] if c["cue"] == 1)
        case("move a caption 4 frames and trim another's end: the timeline shows them there, the list is written whole",
             c1["f"] == 54 and c1["len"] == 31 and fr(P) == [(100, 130), (154, 184), (300, 360)]
             and [s["op"] for s in st] == ["capfile"] and len(st[0]["cues"]) == 3 and "_e" not in st[0]["cues"][0]
             and c1["edited"] and c1["lo"] == 3 and c1["hi"] == 99)
        P, _, _ = apply(cp, [{"op": "capmove", "graphic": "cap", "cue": 1, "by": 30}], copies=False)
        case("a caption never leaves its shot (moved as far as it can: to the shot's last frame)",
             fr(P)[1] == (169, 199))
        P, _, _ = apply(cp, [{"op": "capmove", "graphic": "cap", "cue": 0, "by": 60}], copies=False)
        case("... into the next caption it moves as far as that one can give way (it starts later, MIN_CAP frames left)",
             fr(P)[:2] == [(137, 177), (178, 180)])
        P, _, _ = apply(cp, [{"op": "captrim", "graphic": "cap", "cue": 1, "side": "start", "to": 40}], copies=False)
        case("a caption's start trimmed into the one before: that one ends sooner (a shared edge)",
             fr(P)[:2] == [(100, 139), (140, 180)])
        P, _, _ = apply(cp, [{"op": "captrim", "graphic": "cap_b", "cue": 2, "side": "start", "to": 180}], copies=False)
        case("a trimmed caption keeps at least MIN_CAP frames", fr(P)[2] == (360 - MIN_CAP + 1, 360))
        P, _, _ = apply(cp, [{"op": "capsplit", "graphic": "cap", "cue": 0, "at": 10}], copies=False)
        cs = P[CAPTIONS_KEY][str(cf)]["cues"]
        case("split a caption at the playhead: the words before it stay, the rest make the next caption, the words "
             "beside the split reach it", fr(P)[:3] == [(100, 109), (110, 140), (150, 180)]
             and cs[0]["words"] == [["one", 100, 109]] and cs[1]["words"] == [["two", 110, 140]])
        try:
            apply(cp, [{"op": "capsplit", "graphic": "cap", "cue": 0, "at": 25}], copies=False)
            case("a split with every word on one side is refused", False)
        except EditError:
            case("a split with every word on one side is refused", True)
        P, _, _ = apply(cp, [{"op": "capadd", "graphic": "cap", "at": 85, "text": "hello there"}], copies=False)
        sv = state(P)
        case("add a caption at the playhead: up to 1.5 s, up to its shot's end, in its place in the list, numbered "
             "after the ones before it", fr(P) == [(100, 140), (150, 180), (185, 199), (300, 360)]
             and txt(P)[2] == "hello there" and [c["f"] for c in sv["captions"] if c["cue"] == 2] == [85])
        try:
            apply(cp, [{"op": "capadd", "graphic": "cap", "at": 60, "text": "over"}], copies=False)
            case("a caption over another is refused (change that one's words or split it)", False)
        except EditError:
            case("a caption over another is refused (change that one's words or split it)", True)
        P, done, _ = apply(cp, [{"op": "captions", "edits": [{"graphic": "cap", "cue": 0, "text": "ONE TWO"},
                                                             {"graphic": "cap", "cue": 1, "text": ""},
                                                             {"graphic": "cap_b", "cue": 2, "text": "five!"}]}], copies=False)
        case("many captions at once (one change): new words, one removed, the others renumbered after it",
             txt(P) == ["ONE TWO", "five!"] and fr(P) == [(100, 140), (300, 360)] and len(done) == 1)
        P, _, _ = apply(cp, [{"op": "capmerge", "graphic": "cap", "cue": 0}], copies=False)
        cs = P[CAPTIONS_KEY][str(cf)]["cues"]
        sv = state(cp)
        c0 = next(c for c in sv["captions"] if c["cue"] == 0)
        try:
            apply(cp, [{"op": "capmerge", "graphic": "cap", "cue": 1}], copies=False)
            apart = False
        except EditError:
            apart = True
        case("two captions as one: each word keeps its frames, the pause goes to the first one's last word; the state "
             "gives each word's first frame; a caption said in another shot stays apart",
             fr(P)[:2] == [(100, 180), (300, 360)] and cs[0]["words"][1] == ["two", 120, 149]
             and c0["wf"] == [0, 20] and c0["next_here"] and apart)
        tp = copy.deepcopy(cp)
        tp[CAPTIONS_KEY] = {str(cf): {"cues": [{"f0": 190, "f1": 310, "words": [["over", 190, 250], ["cut", 251, 310]]}]}}
        sv = state(tp)
        case("a caption said over a cut shows on the next shot too: its end drawn there, selecting the caption itself",
             [(c["f"], c["len"], c["graphic"], bool(c.get("tail"))) for c in sv["captions"]]
             == [(90, 10, "cap", False), (100, 11, "cap", True)])
        P, _, st = apply(cp, [{"op": "caption", "graphic": "cap_b", "cue": 2, "text": ""},
                              {"op": "caption", "graphic": "cap", "cue": 0, "text": "won too"}], tag="m5")
        case("remove a caption and change another's words: one copy, the list written on it whole, the plan shows the copy",
             [s["op"] for s in st] == ["copy", "capfile"] and st[1]["folder"] == str(cf.with_name("captions_m5"))
             and [" ".join(w[0] for w in c["words"]) for c in st[1]["cues"]] == ["won too", "three four"]
             and lay(P, "cap")["file"].replace("\\", "/").endswith("captions_m5/captions_m5.mov"))
        r = caption_retime(cues[1], 150, 165)
        case("a caption in fewer frames: its words keep their share, in order, the last on its end",
             r["words"] == [["three", 150, 158], ["four", 159, 165]])
        P, _, st = apply(cp, [{"op": "look", "graphic": "cap_b", "look": "classic"}, {"op": "set", "graphic": "cap_c",
                              "key": "font_size", "value": 90}], tag="m6")
        case("a look and a setting on the same captions in a save: one copy, all its values then the setting on it",
             [s["op"] for s in st] == ["copy", "values", "set"] and st[1]["values"].get("font") == "Archivo Black"
             and st[2]["folder"].endswith("captions_m6") and lay(P, "cap")["file"].endswith("captions_m6.mov"))
    dup = {"fps": 25.0, "frames": 10, "layers": [{"type": "overlay", "id": "g", "start": 0, "end": 4},
                                                  {"type": "overlay", "id": "g", "start": 5, "end": 9},
                                                  {"type": "overlay", "id": "g_2", "start": 0, "end": 9}]}
    case("layers that share an id get their own (g, g_2 taken -> g_3), the same every time",
         [x["id"] for x in unique_ids(copy.deepcopy(dup))["layers"]] == ["g", "g_3", "g_2"])
    c = caption_words({"f0": 10, "f1": 29, "words": [["helo", 10, 29]]}, "hello world")
    case("a caption's new words share its frames", c["words"][0][1] == 10 and c["words"][-1][2] == 29
         and c["words"][1][1] == c["words"][0][2] + 1)
    return {"passed": ok, "seconds": round(time.time() - t0, 3), "lines": lines}
