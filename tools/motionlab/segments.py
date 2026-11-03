"""Edit by segments (0.6.1, docs\\plans.md *Edit by segments*, steps 1-4 - the user, 2026-10-29: "editar por
segmentos" and "borrador (quick draft) select each segment how u would like it edited and then create the edit
entirely"): an edit (the quick draft's plan) cut into segments by kind of video, and per segment ONE treatment
recommended with its reason in one line and two alternatives (the research: more options overwhelm - docs\\ideas.md
*Editing by segments*). Rules on what the lab measured (the words, the song, the catalogue, the framing), no Claude.

The segments tile the edit, frame 0 to its last, and never start inside a sentence or a bar:
  talk   the words said in the edit -> sentences (stumbles.sentences, a pause of PAUSE_S) grouped into one-idea
         beats of MIN_S..MAX_S seconds: one closes at a pause of BEAT_GAP_S once it is MIN_S long, or before a sentence
         that would take it past MAX_S; a sentence longer than MAX_S is a segment alone; a last one under MIN_S joins
         the one before
  music  the song's phrases: PHRASE_BARS bars from downbeat to downbeat (fewer when they would run past MAX_S;
         audio.analyze's best-effort 4/4); a drop starts a segment of its own
  clips  neither words nor a song (a montage): its shots, in runs of MIN_S..MAX_S seconds
Each: {"n", "kind", "f0", "f1", "key" (the frame its picture and its treatment centre on), "say" (its words, or "bars
5-12"), "words": [[frame, word], ...], ("drop": true), "at" (anchor(): where it starts in its clip or its song)}.

Treatments: TREATMENTS (id -> its name); recommend() gives each segment {"pick", "why", "by" (rules | claude | user),
"rule" {"t", "why"} (the rules' own pick), ("claude" {"t", "why", ("opt")}: Claude's), "alts": [{"t", "why"} x2], "can":
[every treatment it can have], ("opt"), ("text")}. The rules, in this order: talk - a topic Claude marked starting here
(never on the hook) -> title, something counted ("number one ... number two", two LIST markers) -> list, a number
said -> number, a concrete word a B-roll clip's catalogue line says -> broll (never the hook - the face keeps it), a
part starting ("number two", "next", "finally" at its start) -> title, mostly a screen recording (its framing) ->
screen, else a punch-in on its key word and plain in turn (the first - the hook - a punch-in); music - the drop -> drop,
the phrase before it -> beat, the first -> plain, else beat and plain in turn; clips - punch and plain in turn.

The layers (step 3, as Descript does; Claude's since step 7): the style once (the request's - New edit's steps: the
draft's look, the captions, the colours, the sounds), the rules' picks, Claude's picks (/recreate-video: what needs
judgement - the edit, its clip or template, the word it lands on, the words on its card, why in one line) and topics
(where the talk turns to a new point, named), the user's own picks on top (build\\segment_picks.json, "by"). The
suggestion = Claude's pick where it made one, else the rules'; *back to the suggestion* = the user's pick taken back.
Every pick is kept through any re-run: tied to where its segment starts in its clip (or its song), not to the edit's
frames, it lands on the segment starting within PICK_NEAR_S of it. Limits across segments, for the suggestions (the
user's stay as picked and never move another part's): never one treatment three times in a row (the third takes its
first alternative), a template the words pick once a video, B-roll at most draft.BROLL_COVER of the edit (the quick
draft's ceiling; its drafts measured 21-26 %).

The build (step 4): build_list() = the picks as edit-list lines (motionlab\\editlist) on a BARE quick draft (its cuts,
sound, colour and framing only - draft_edit.py --bare), one block per segment, nothing inside a segment that is not
its pick: punch = PUNCH closer on the key word, back at the segment's end; broll = the clip on the word, BROLL_LATE_S
after it; number / title / list = TEMPLATE's graphic with the words the rules read (the number and what follows it,
the part's opening words - a topic's name -, the items counted); graphic = the template the words pick, its main
words = the segment's first phrase; screen = a slow push; drop = a flash and a shake; beat = a cut on every beat
(inside its clips). A pick's "text" (Claude's) = the word a punch-in or a B-roll lands on, or the words on its card
(a title "line 1|line 2", a number's words under it, a list's items "a|b|c", a graphic's main words) instead of the
rules'. verify() then checks the built plan: every cut where it was, every segment's pick in it, nothing in a plain one.

    talk(words, fps, frames)                      words = [{"t", ("t1"), "w"}] in the edit's seconds, in order
    music(downbeats, drops, fps, frames, bpm)     frames of the edit
    clips(shots, fps, frames)                     shots = [(first, last)] in order
    anchor(P, seg, song_s)                        where a segment starts in its clip / song
    mine_for(segs, picks, fps) -> ({n: pick}, [picks that found no segment])     (a topic {"at", "name"} too)
    recommend(segs, ctx=None, lang="en", mine=None, claude=None)   mine / claude = {n: pick}; a segment's "topic" =
                                                  its topic's name when one starts on it
                                                  ctx: "broll" [{"clip", "m", "words" {stems}, "line", "use"
                                                  [u0, u1], "anchor"}], "graphic" fn(words, used) -> (template id,
                                                  score, [words]) | None, "screen" {frames}, "frames" (the edit's)
    like(segs, n) -> [segment numbers]            Apply to all like this: those the rules gave n's rule pick
    build_list(segs, P, ctx, lang) -> (lines, claims)   ctx also: "any_graphic" fn(words, used) -> template id,
                                                  "captions" (a look), "look" {template values}, "beats" [frames]
    verify(base, built, claims) -> {"ok", "lines", "broll_share"}
    selfcheck() -> {"passed", "seconds", "lines"}
"""
from __future__ import annotations

import re
import time

from . import stumbles as SB

MIN_S, MAX_S = 3.0, 12.0        # a segment's length, seconds (the plan: one-idea beats of ~3-12 s)
PAUSE_S = 0.4                   # a pause this long ends a sentence (the plan; stumbles' own is 0.6)
BEAT_GAP_S = 0.7                # a pause this long closes a beat that is MIN_S long already
PHRASE_BARS = 8                 # a music phrase: 8 bars, or 4 (2) when 8 run past MAX_S
TREATMENTS = {"plain": "Plain", "punch": "Punch-in on a key word", "broll": "B-roll on the words",
              "list": "List / steps", "number": "Number", "title": "Section title",
              "screen": "Screen zoom", "graphic": "A motion graphic",
              "beat": "Beat montage", "drop": "Drop hit"}           # (a split with a second clip: not built yet)
GRAPHIC_SCORE = 6.0             # templates.pick's score from which a template is "picked by the words"
PICK_NEAR_S = 0.6               # a user's pick lands on the segment starting this near where it started (a re-run)
PUNCH = 1.15                    # a punch-in: a step this much closer (the Editor's), back at its segment's end
LEN_S = {"number": 2.5, "title": 2.5, "graphic": 3.0}     # a graphic's length - never past its segment
COLUMN_SIZE = 1.5                # ... and its size in a wide video's column (local-make-25: 1.3-1.5)
READ_S = 1.2                    # a graphic shorter than this where it lands starts earlier in its segment
BEAT_MIN_S = 0.4                # a beat montage: a cut on every beat at least this far from the last cut
BEAT_SKIP_S = 1.0               # ... each piece this much further on in its clip (from its start again at its end)
TEMPLATE = {"number": "big-counter", "title": "headline-box", "list": "checklist"}   # one look a video for each
NUM = {"en": {"two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "fifteen",
              "twenty", "thirty", "forty", "fifty", "hundred", "thousand", "million", "billion", "percent", "half",
              "double", "twice"},
       "es": {"dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez", "once", "doce", "quince",
              "veinte", "treinta", "cuarenta", "cincuenta", "cien", "ciento", "mil", "millon", "millones", "mitad",
              "doble", "porciento"}}
NUMVAL = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
          "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
          "hundred": 100, "thousand": 1000, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
          "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12, "quince": 15, "veinte": 20,
          "treinta": 30, "cuarenta": 40, "cincuenta": 50, "cien": 100, "ciento": 100}
UNITS = {"percent": "%", "porciento": "%", "thousand": "K", "mil": "K", "million": "M", "millon": "M",
         "millones": "M", "billion": "B"}                     # (said after a number: the counter's suffix)
WEAK = {"something", "everything", "anything", "nothing", "everyone", "someone", "anyone", "because", "actually",
        "really", "basically", "probably", "literally", "whatever", "obviously", "algo", "todo", "nada", "porque",
        "realmente", "basicamente", "probablemente", "literalmente", "obviamente"}   # (long, never the stressed word)
COUNT = ("one|two|three|four|five|six|seven|eight|nine|ten|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez"
         r"|\d+")
LIST = re.compile(rf"\b(?:number|step|tip|rule|reason|point|edit|mistake|way|part|numero|paso|consejo|regla|razon|"
                  rf"punto|error|forma|parte) (?:{COUNT})\b|\b(?:firstly|secondly|thirdly|lastly|primero|segundo|"
                  rf"tercero|en primer lugar|en segundo lugar)\b")
ORDINALS = re.compile(r"\b(?:first|second|third|fourth|fifth|primera|segunda|tercera|cuarta|quinta)\b")
LEAD = ("two|three|four|five|six|seven|eight|nine|ten|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|[2-9]|10")
STARTS = re.compile(rf"^(?:(?:number|step|tip|part|numero|paso|parte) (?:{COUNT})\b|(?:{LEAD})\b|first\b|next\b|"
                    r"finally\b|lastly\b|now\b|so here\b|primero\b|siguiente\b|despues\b|por ultimo\b|finalmente\b|"
                    r"ahora\b)")
TRAIL = {"and", "or", "but", "so", "the", "a", "an", "to", "of", "y", "o", "pero", "el", "la", "los", "las", "de",
         "que", "un", "una"}                                 # (never the last word on a card)
ALWAYS = {"talk":("plain", "punch", "title", "graphic"), "music": ("plain", "beat", "drop", "graphic"),
          "clips": ("plain", "punch", "graphic")}           # what any segment of a kind can have (a user's pick)


class _Why(str):
    """A why line in English that keeps its key and values: the app shows it in its own language (t(key, values) -
    the Spanish in ui\\i18n\\parts\\es.editor-1.json, listed in its "_by_key"); the files and the console stay English."""
    k: str = ""
    v: dict = {}


def W(key: str, **v) -> _Why:
    s = _Why(key.format(**v))
    s.k, s.v = key, {a: str(b) for a, b in v.items()}
    return s


def _wk(s) -> list:
    """A why line's [key, values] for the app."""
    return [s.k, s.v] if isinstance(s, _Why) and s.k else [str(s), {}]


def _plain(words: list) -> str:
    """Words normalized as the rules read them (stumbles.norm: lower case, no accents) and joined."""
    return " ".join(SB.norm(w) for w in words if SB.norm(w))


# ------------------------------------------------------------------------------------------------ 1. segments
def _tile(segs: list[dict], frames: int) -> list[dict]:
    """Segments numbered from 1, each running to the frame before the next one's first; the first from frame 0, the
    last to the edit's last frame."""
    segs = [s for s in segs if s["f0"] < frames]
    for i, s in enumerate(segs):
        s["n"] = i + 1
        s["f0"] = 0 if i == 0 else s["f0"]
        s["f1"] = segs[i + 1]["f0"] - 1 if i + 1 < len(segs) else frames - 1
        s["key"] = min(max(s.get("key", (s["f0"] + s["f1"]) // 2), s["f0"]), s["f1"])
    return segs


def talk(words: list[dict], fps: float, frames: int, cuts: list[int] | None = None) -> list[dict]:
    """The talk's segments: its sentences grouped into one-idea beats (the module's docstring). cuts = the frames the
    edit cuts between talking shots - a quick draft cuts the pauses out, so a cut between two words IS a pause."""
    if not words:
        return []
    fr = [float(w["t"]) * fps for w in words]
    cut = sorted(cuts or [])
    brk = {i for i in range(len(words) - 1) if any(fr[i] < c <= fr[i + 1] for c in cut)}
    S = SB.sentences(words, PAUSE_S, brk)
    for k in range(len(S) - 1):                      # "... gets this sound and four | Color grade": a count said
        if len(S[k]) > 1 and re.fullmatch(LEAD, SB.norm(words[S[k][-1]]["w"])):      # before its pause opens the
            S[k + 1].insert(0, S[k].pop())                                            # next part
            brk.discard(S[k + 1][0])
            brk.add(S[k][-1])
    end = lambda i: float(words[i].get("t1") or words[i]["t"] + 0.3)          # noqa: E731 (a word's end)
    beats, cur = [], []
    for k, s in enumerate(S):
        if cur and end(s[-1]) - float(words[cur[0]]["t"]) > MAX_S:            # it would run past MAX_S: closed first
            beats.append(cur)
            cur = []
        cur = cur + s
        gap = float(words[S[k + 1][0]]["t"]) - end(s[-1]) if k + 1 < len(S) else 99.0
        if s[-1] in brk:
            gap = max(gap, BEAT_GAP_S)                                        # (a pause the edit cut out)
        if end(s[-1]) - float(words[cur[0]]["t"]) >= MIN_S and gap >= BEAT_GAP_S:
            beats.append(cur)
            cur = []
    if cur:
        if beats and end(cur[-1]) - float(words[cur[0]]["t"]) < MIN_S:        # a short last one joins the one before
            beats[-1] += cur
        else:
            beats.append(cur)
    out = []
    for b in beats:
        ws = [[int(round(float(words[i]["t"]) * fps)), words[i]["w"]] for i in b]
        out.append({"kind": "talk", "f0": ws[0][0], "say": " ".join(w for _, w in ws), "words": ws})
    return _tile(out, frames)


def music(downbeats: list[int], drops: list[int], fps: float, frames: int, bpm: float | None = None) -> list[dict]:
    """The song's phrases (the module's docstring). downbeats / drops = frames of the edit."""
    db = sorted({int(f) for f in downbeats if 0 <= f < frames})
    if len(db) < 2:
        return []
    bar = (db[-1] - db[0]) / max(1, len(db) - 1)                              # (frames a bar, measured)
    n = PHRASE_BARS
    while n > 2 and n * bar / fps > MAX_S:
        n //= 2
    cuts = db[::n]
    dr = sorted({int(f) for f in drops if 0 < f < frames})
    for d in dr:                                     # a drop: a segment of its own from it (a cut a bar or less
        cuts = [c for c in cuts if abs(c - d) > bar] + [d]    # before or after it gives way)
    cuts = sorted(set([0] + cuts))
    merged = True                                    # a piece under MIN_S (a pickup before the first downbeat, a bar
    while merged and len(cuts) > 1:                  # left by a drop) joins the one before - a drop keeps its start
        merged = False                               # (then the piece after it joins it)
        for i, c in enumerate(cuts):
            nxt = cuts[i + 1] if i + 1 < len(cuts) else frames
            if nxt - c >= MIN_S * fps:
                continue
            if c in dr or c == 0:
                if i + 1 < len(cuts) and cuts[i + 1] not in dr:
                    del cuts[i + 1]
                    merged = True
                    break
                continue
            del cuts[i]
            merged = True
            break
    out = []
    for i, c in enumerate(cuts):
        nxt = cuts[i + 1] if i + 1 < len(cuts) else frames
        b0 = sum(1 for x in db if x < c) + 1
        b1 = max(b0, sum(1 for x in db if x < nxt))
        out.append({"kind": "music", "f0": c, "key": c + int(bar) if c + bar < nxt else c,
                    "say": f"bars {b0}-{b1}" if b1 > b0 else f"bar {b0}", "words": [],
                    **({"drop": True} if c in dr else {})})
    return _tile(out, frames)


def clips(shots: list[tuple[int, int]], fps: float, frames: int) -> list[dict]:
    """A montage's segments: its shots in runs of MIN_S..MAX_S seconds."""
    out, cur = [], []
    for s, e in shots:
        if cur and (e - cur[0][0] + 1) / fps > MAX_S:
            out.append(cur)
            cur = []
        cur.append((s, e))
        if (cur[-1][1] - cur[0][0] + 1) / fps >= MIN_S:
            out.append(cur)
            cur = []
    if cur:
        if out and (cur[-1][1] - cur[0][0] + 1) / fps < MIN_S:
            out[-1] += cur
        else:
            out.append(cur)
    return _tile([{"kind": "clips", "f0": r[0][0], "key": max(r, key=lambda x: x[1] - x[0])[0]
                   + (max(r, key=lambda x: x[1] - x[0])[1] - max(r, key=lambda x: x[1] - x[0])[0]) // 2,
                   "say": f"{len(r)} shot(s)", "words": []} for r in out], frames)


# ------------------------------------------------------------------------------------------------ 2. treatments
def key_word(seg: dict, lang: str = "en") -> tuple[int, str] | None:
    """The word a punch-in lands on: a number said, else its longest content word (the first of the longest)."""
    from .draft import stem
    nums = NUM["es" if lang.startswith("es") else "en"]
    for f, w in seg.get("words") or []:                # (a number first - stem() keeps letters only)
        if re.search(r"\d", w) or SB.norm(w) in nums:
            return f, w
    ws = [(f, w) for f, w in seg.get("words") or [] if stem(w) and SB.norm(w) not in WEAK]
    return max(ws, key=lambda x: (len(stem(x[1])), -x[0])) if ws else None


def num_value(w: str) -> float | None:
    """A word's number: its digits ("200", "2.5", "1,000", "30%") or a number word ("five", "cinco"), else None."""
    m = re.search(r"\d[\d,]*(?:\.\d+)?", w)
    if m:
        try:
            v = float(m[0].replace(",", ""))
        except ValueError:
            return None
        return int(v) if v == int(v) else v
    return NUMVAL.get(SB.norm(w))


def _opener(seg: dict) -> int:
    """How many words open the segment as a part ("Number two", "Three", "Next") - 0 when none does."""
    st = STARTS.match(_plain([w for _, w in seg.get("words") or []]))
    return len(st.group(0).split()) if st else 0


def _features(seg: dict, ctx: dict, lang: str) -> list[tuple[str, str]]:
    """The treatments this segment can have, most fitting first, each with why (one line). Sets seg["hit"] (a B-roll
    moment its words name) and seg["num"] (the number said: its word's index)."""
    out = []
    kind = seg["kind"]
    text = _plain([w for _, w in seg.get("words") or []])
    seg.pop("hit", None)
    seg.pop("num", None)
    if kind == "talk" and seg.get("topic") and seg["f0"] > 0:      # a topic Claude marked starts here: its title
        out.append(("title", W("a new topic: \"{name}\"", name=str(seg["topic"])[:40])))   # (the hook keeps the face)
    if kind == "talk":
        marks = LIST.findall(text)
        ords = set(ORDINALS.findall(text))
        if len(marks) >= 2 or len(ords) >= 2:
            said = marks[:3] if len(marks) >= 2 else sorted(ords)[:3]
            out.append(("list", W("it counts: {items}", items=" ... ".join(said))))
        st = STARTS.match(text)                      # a part starts: its title (its count is no number said) - first
        strong = bool(st and re.match(rf"(?:\w+ )?(?:{COUNT})\b", st.group(0)))       # when a count opens it
        title = ("title", W("a part starts here: \"{words}\"", words=" ".join(text.split()[:3])))
        if strong:                                   # (after a list: two items counted inside it are a list)
            out.append(title)
        nums = NUM["es" if lang.startswith("es") else "en"]
        skip = _opener(seg)
        num = next((k for k, (_, w) in enumerate(seg["words"]) if k >= skip
                    and (re.search(r"\d", w) or SB.norm(w) in nums) and num_value(w) is not None), None)
        if num is not None:
            seg["num"] = num
            out.append(("number", W("a number said: \"{word}\"", word=seg["words"][num][1].strip(".,!?"))))
        hit = _broll_hit(seg, ctx.get("broll") or [])
        if hit:
            seg["hit"] = {k: hit[k] for k in ("clip", "m", "f", "word")}
            out.append(("broll", hit["why"]))
        if st and not strong:                        # ("next", "now", "finally": after what it says)
            out.append(title)
    if kind == "music" and seg.get("drop"):
        out.append(("drop", W("the drop")))
    scr = ctx.get("screen") or set()
    if scr and sum(1 for f in range(seg["f0"], seg["f1"] + 1) if f in scr) * 2 > seg["f1"] - seg["f0"] + 1:
        out.append(("screen", W("a screen recording - zoom in where it changes")))
    return out


def word_at(seg: dict, text) -> int | None:
    """The frame of the segment's word that `text` names (its first word; Claude's: where a punch-in or a B-roll
    lands), None = no such word said in it."""
    want = SB.norm(str(text or "").split()[0]) if str(text or "").strip() else ""
    return next((int(f) for f, w in seg.get("words") or [] if want and SB.norm(w) == want), None)


def _broll_hit(seg: dict, broll: list) -> dict | None:
    """The B-roll moment whose catalogue line says most of the segment's words -> {"why", "clip", "m", "f" (the word's
    frame), "word"}, or None."""
    from .draft import stem
    have = {}
    for f, w in seg.get("words") or []:
        if stem(w) and stem(w) not in have:
            have[stem(w)] = (f, w)
    best = None
    for b in broll:
        hits = [have[s] for s in have if s in b["words"]]
        if hits and (best is None or len(hits) > len(best[0])):
            best = (hits, b)
    if best is None:
        return None
    hits, b = best
    f, w = hits[0]
    return {"why": W("\"{word}\" - clip {clip} shows it ({line})", word=w.strip(".,!?"), clip=b["clip"],
                     line=str(b["line"])[:48]), "clip": b["clip"],
            "m": b["m"], "f": f, "word": w}


# ------------------------------------------------------------------------------------------------ 3. the user's picks
def anchor(P: dict, seg: dict, song_s: float = 0.0) -> dict:
    """Where a segment starts in what it is made of - a re-run of the draft moves its frames, not this: talk / clips =
    the clip and its frame under the segment's first word (talk) or first frame; music = the song's second."""
    from . import editlist as EL
    if seg["kind"] == "music":
        return {"song": round(song_s + seg["f0"] / float(P["fps"]), 2)}
    f = seg["words"][0][0] if seg.get("words") else seg["f0"]
    L = next((x for x in EL.shots(P) if x["start"] <= f <= x["end"]), None)
    return {"src": L["src"], "at": EL._src_at(L, f)} if L else {"f": f}


def _apart(a: dict, b: dict, fps: float) -> float | None:
    """How far apart two anchors are in seconds (None = not the same clip / not the same kind)."""
    if "song" in a or "song" in b:
        return abs(a["song"] - b["song"]) if "song" in a and "song" in b else None
    if a.get("src") is None or a.get("src") != b.get("src"):
        return None
    return abs(int(a["at"]) - int(b["at"])) / fps


def mine_for(segs: list[dict], picks: list[dict], fps: float) -> tuple[dict, list[dict]]:
    """Picks (segment_picks.json "picks": {"at", "t", ("opt"), ("text"), ("why")} of one layer - the user's or
    Claude's -, or Claude's topics {"at", "name"}) on these segments: {n: pick} - each on the segment starting nearest
    where its own started, within PICK_NEAR_S - and the picks that found none (kept in the file: a later run may bring
    their part back)."""
    out, lost = {}, []
    for p in picks:
        near = [(d, s["n"]) for s in segs if s.get("at") and (d := _apart(s["at"], p.get("at") or {}, fps)) is not None
                and d <= PICK_NEAR_S]
        if near:
            out[min(near)[1]] = p
        else:
            lost.append(p)
    return out, lost


def recommend(segs: list[dict], ctx: dict | None = None, lang: str = "en", mine: dict | None = None,
              claude: dict | None = None) -> list[dict]:
    """Each segment's pick, why and two alternatives (the module's docstring); mine = the user's picks {n: {"t",
    ("opt")}} - kept as picked; claude = Claude's {n: {"t", ("opt"), ("text"), "why"}} - the suggestion where it made
    one (under the user's); the rules fill around them. A pick a segment cannot have is left out. In place, and
    returned."""
    from .draft import BROLL_COVER, BROLL_LEN_S
    ctx, mine, claude = ctx or {}, mine or {}, claude or {}
    fps = float(ctx.get("fps") or 30.0)
    cap = BROLL_COVER * float(ctx.get("frames") or (segs[-1]["f1"] + 1 if segs else 0))
    covered, used, taken = 0.0, set(), set()
    picks: list[str] = []
    turn = "punch"                                   # (the hook gets the punch-in; then plain and punch in turn)
    for i, seg in enumerate(segs):                   # (a moment an earlier segment shows: not named again)
        cand = _features(seg, {**ctx, "broll": [b for b in ctx.get("broll") or [] if (b["clip"], b["m"]) not in taken]},
                         lang)
        kind = seg["kind"]
        hook_broll = [c for c in cand if c[0] == "broll"] if i == 0 else []
        cand = [c for c in cand if c not in hook_broll]      # the hook keeps the face: B-roll only an alternative
        if kind == "music":
            if any(t == "drop" for t, _ in cand):
                pass
            elif i + 1 < len(segs) and segs[i + 1].get("drop"):
                cand.append(("beat", W("the build-up before the drop - cuts on the beat")))
            elif i == 0:
                cand.append(("plain", W("the intro - longer shots before the music builds")))
        kw = key_word(seg, lang) if kind == "talk" else None
        punch = ("punch", W("a punch-in on \"{word}\"", word=kw[1].strip(".,!?")) if kw
                 else W("a punch-in to keep it moving"))
        plain = ("plain", W("a breather between busier parts"))
        beat = ("beat", W("cuts on the beat"))
        busy, calm = (beat, plain) if kind == "music" else (punch, plain)
        rest = [busy, calm] if turn == "punch" else [calm, busy]
        gr = ctx.get("graphic")
        g = gr(seg.get("say") or "", used) if gr and kind != "music" else None
        tail = [("graphic", W("the {template} template fits its words ({words})", template=g[0],
                              words=", ".join(g[2][:3])) if g else
                 W("a motion graphic over it (a template picked when it is built)"))] + hook_broll
        seen, order = set(), []
        for t, why in cand + rest + tail:
            if t not in seen:
                seen.add(t)
                order.append((t, why))
        if covered + BROLL_LEN_S * fps > cap:        # the B-roll budget spent: the rules pick something else
            order = [o for o in order if o[0] != "broll"] + [o for o in order if o[0] == "broll"]
        if len(picks) >= 2 and picks[-1] == picks[-2] == order[0][0] and len(order) > 1:
            order[0], order[1] = order[1], order[0]                          # never three in a row
        can = [t for t, _ in order] + [t for t in ALWAYS.get(kind, ()) if t not in seen] + (
            ["broll"] if kind == "talk" and ctx.get("broll") and "broll" not in seen else [])   # (a clip of the
        #                                                  user's or Claude's choice, where the rules found no word)
        rule_t, rule_why = order[0]
        u, c = mine.get(seg["n"]), claude.get(seg["n"])
        c = c if c and c.get("t") in can else None
        sug_t = c["t"] if c else rule_t             # the suggestion: Claude's where it made one, else the rules'
        if u and u.get("t") in can:
            pick, why, by, src = u["t"], W("your pick"), "user", u
            if c and c["t"] == u["t"]:               # the user chose the treatment, Claude's words / template fill
                src = {**{k: c[k] for k in ("opt", "text") if c.get(k)}, **u}     # what theirs leaves open (2026-10-30)
        elif c:
            pick, why, by, src = c["t"], str(c.get("why") or ""), "claude", c     # (Claude's own line: no key)
        else:
            pick, why, by, src = rule_t, rule_why, "rules", None
        alts = [o for o in order if o[0] != pick][:2]
        for k in ("opt", "text", "claude", "template"):
            seg.pop(k, None)
        seg.update(pick=pick, why=str(why), why_k=None if by == "claude" else _wk(why), by=by, can=can,
                   rule={"t": rule_t, "why": str(rule_why), "why_k": _wk(rule_why)},
                   alts=[{"t": t, "why": str(w), "why_k": _wk(w)} for t, w in alts],
                   **{k: src[k] for k in ("opt", "text") if src and src.get(k)})
        if c:                                        # (kept under the user's: *back to the suggestion*)
            seg["claude"] = {"t": c["t"], "why": str(c.get("why") or ""), **({"opt": c["opt"]} if c.get("opt") else {})}
        if pick == "graphic" and (seg.get("opt") or g):
            seg["template"] = seg.get("opt") or g[0]
        if pick == "punch":                          # (on the word Claude named, else the key word)
            at = word_at(seg, seg.get("text"))
            if at is not None or kw:
                seg["key"] = at if at is not None else kw[0]
        # the run goes on from the SUGGESTION (2026-10-30, the app's test: a part set to plain turned the next one into
        # a punch-in): a pick of the user's never moves another part's - its build takes what is left
        if sug_t == "graphic" and ((c or {}).get("opt") or g):
            used.add((c or {}).get("opt") or g[0])
        if sug_t == "broll":
            covered += BROLL_LEN_S * fps
            h = seg.get("hit")
            if h and not (c and c.get("opt") and c["opt"] != h["clip"]):
                taken.add((h["clip"], h["m"]))
            elif c and c.get("opt"):                 # Claude's clip: the moment the build takes (most of its words)
                from .draft import stem
                have = {stem(w) for _, w in seg.get("words") or [] if stem(w)}
                its = [b for b in ctx.get("broll") or [] if b["clip"] == c["opt"] and (b["clip"], b["m"]) not in taken]
                if its:
                    b = max(its, key=lambda x: len(have & x["words"]))
                    taken.add((b["clip"], b["m"]))
        picks.append(sug_t)
        if sug_t in ("punch", "plain", "beat"):
            turn = "plain" if sug_t in ("punch", "beat") else "punch"
    return segs


def like(segs: list[dict], n: int) -> list[int]:
    """Apply to all like this: the other segments the rules gave segment n's rule pick, that can have n's pick."""
    s = next((x for x in segs if x["n"] == n), None)
    if s is None:
        return []
    return [x["n"] for x in segs if x["n"] != n and x["rule"]["t"] == s["rule"]["t"] and s["pick"] in x["can"]]


# ------------------------------------------------------------------------------------------------ 4. the build
def _clean(s: str) -> str:
    """Words for a card: no quotes, no '#' (an edit list's note), no trailing punctuation, the first letter capital."""
    s = re.sub(r"[\"#]", "", " ".join(s.split())).strip(" .,;:!?-")
    return s[:1].upper() + s[1:]


def _phrase(words: list[str], most: int) -> str:
    """The words up to the first that ends a phrase (, . ! ? ; :), at most `most`; never ending on "and" / "the"."""
    out = []
    for w in words[:most]:
        out.append(w)
        if re.search(r"[.,!?;:]$", w):
            break
    while len(out) > 1 and SB.norm(out[-1]) in TRAIL:
        out.pop()
    return _clean(" ".join(out))


def _items(seg: dict) -> list[tuple[int, str]]:
    """A list's items: after each counted marker ("number one", "step two", "firstly", "first") the words to the end
    of its phrase or the next marker (5 at most) -> [(the marker's frame, the item)]; none counted = its phrases."""
    ws = seg.get("words") or []
    norm = [SB.norm(w) for _, w in ws]
    starts = []
    for k, n in enumerate(norm):
        two = f"{n} {norm[k + 1]}" if k + 1 < len(norm) else ""
        if two and LIST.fullmatch(two):
            starts.append((k, 2))
        elif LIST.fullmatch(n) or ORDINALS.fullmatch(n):
            starts.append((k, 1))
    out = []
    for j, (k, m) in enumerate(starts):
        stop = starts[j + 1][0] if j + 1 < len(starts) else len(ws)
        item = _phrase([w for _, w in ws[k + m:stop]], 5)
        if item:
            out.append((ws[k][0], item))
    if len(out) < 2:                                 # (a user's list on a segment that counts nothing)
        out, cur = [], []
        for f, w in ws:
            cur.append((f, w))
            if re.search(r"[.,!?;:]$", w) or len(cur) == 5:
                out.append((cur[0][0], _clean(" ".join(x for _, x in cur))))
                cur = []
        if cur:
            out.append((cur[0][0], _clean(" ".join(x for _, x in cur))))
    return out[:6]


def _slots(tid: str) -> tuple[set, str | None]:
    """A template's setting ids and its main words' setting (its text_slots first, else the usual names)."""
    from . import miniedit as ME
    from . import overlay_settings as OS
    folder = ME.template_folder(tid)
    if folder is None:
        return set(), None
    decl = OS.declared(folder)
    ids = [d["id"] for d in decl if d["type"] == "string"]
    try:
        from . import templates as TM
        t = next((x for x in TM.library() if x["id"] == tid), {})
    except (OSError, ValueError):
        t = {}
    slots = [s["id"] if isinstance(s, dict) else s for s in t.get("text_slots") or []]
    for k in slots + [i for i in ("text", "title", "words", "headline", "line", "caption", "label", "quote")
                      if i in ids] + ids:
        if k in ids and not any(w in k for w in ("media", "focus", "logo", "image", "photo", "video", "emoji")):
            return {d["id"] for d in decl}, k
    return {d["id"] for d in decl}, None


def _values(tid: str, vals: dict, look: dict | None, main: str = "") -> dict:
    """The values a template declares (vals, the style's look over it - its accent / text / background colours by the
    names it uses), `main` into its main words when vals names none of its words."""
    ids, slot = _slots(tid)
    out = {k: v for k, v in vals.items() if k in ids}
    for k, v in (look or {}).items():
        if k in ids:
            out.setdefault(k, v)
    for k, src in (("accent", "signal"), ("text_color", "ink"), ("bg", "paper")):     # (gen_draft's BRAND_ALIASES)
        if k in ids and src in (look or {}):
            out.setdefault(k, look[src])
    if main and slot and not any(k in out for k in ids if k == slot):
        out[slot] = main
    return out


def _graphic(tid: str, f: int, n: int, vals: dict, column: bool = False) -> str:
    return f"graphic {tid} at f{f} for {n}" + "".join(
        f" {k}=\"{v}\"" if isinstance(v, str) else f" {k}={v:g}" if isinstance(v, (int, float)) and not isinstance(
            v, bool) else f" {k}={str(v).lower()}" for k, v in vals.items()) + (" column" if column else "")


def _fit_in(wins: list, want: int, need: int) -> int | None:
    """A beat cut's frame in its clip: `want` or the first later frame from which `need` frames stay inside one usable
    window (a catalogue moment's - never across a cut inside the clip), else from the first window long enough (from
    the clip's start again); None = none is. No windows known = `want`."""
    if not wins:
        return want
    for w0, w1 in wins:
        if max(w0, want) + need - 1 <= w1:
            return max(w0, want)
    return next((w0 for w0, w1 in wins if w1 - w0 + 1 >= need), None)


def build_list(segs: list[dict], P: dict, ctx: dict | None = None, lang: str = "en") -> tuple[list[str], list[dict]]:
    """The picks as edit-list lines on the bare draft P, a block per segment, and what each pick must have put in the
    plan (claims, for verify()). A pick the plan cannot take (no B-roll clip left, a segment too short for its card)
    stays plain, its claim saying why."""
    from . import editlist as EL
    from .compose import Curve
    from .draft import BROLL_LATE_S, BROLL_LEN_S, BROLL_MIN_S, stem
    from .timecode import frame_to_tc
    ctx = ctx or {}
    fps, N = float(P["fps"]), int(P["frames"])
    sec = lambda s: max(1, int(round(s * fps)))                              # noqa: E731
    zoom = lambda L, f: float(Curve(L.get("zoom"), P.get("curves") or {}, 1.0)(f))     # noqa: E731
    look = ctx.get("look") or {}
    lines = [f"caption {ctx['captions']}"] if ctx.get("captions") else []
    claims, used_m, used_t = [], set(), set()
    shots = EL.shots(P)
    under = lambda f: next((x for x in shots if x["start"] <= f <= x["end"]), None)          # noqa: E731

    wide = int(P["width"]) > int(P["height"])        # a wide video: each card a column at the edge, its words
    #                                                  bigger (local-make-1, -25); facefit.fit_cards picks the side

    def gline(tid, f, n, vals, main):
        return _graphic(tid, f, n, _values(tid, {**vals, **({"size": COLUMN_SIZE} if wide else {})}, look, main), wide)

    def card(f, want, f0, f1):                       # a card's first frame and length inside its segment
        n = min(want, f1 - f + 1)
        if n < sec(READ_S):
            f = max(f0, f1 + 1 - want)
            n = f1 - f + 1
        return f, n
    for s in segs:
        t, f0, f1 = s["pick"], s["f0"], s["f1"]
        out, c = [], {"n": s["n"], "t": t, "f0": f0, "f1": f1}
        ws = s.get("words") or []
        if t == "punch":
            f = min(max(int(s.get("key", f0)), f0), f1)
            L = under(f)
            if L is None:
                c["skip"] = "no shot under its key word"
            else:
                out.append(f"punch-in {round(zoom(L, f) * PUNCH, 4):g} at f{f}")
                if L["end"] > f1:                    # (the shot goes on into the next segment: back where it was)
                    out.append(f"punch-in {round(zoom(L, f1 + 1), 4):g} at f{f1 + 1}")
                c["f"] = f
        elif t == "broll":
            h = s.get("hit") or {}
            pool = [b for b in ctx.get("broll") or [] if (b["clip"], b["m"]) not in used_m
                    and (not s.get("opt") or b["clip"] == s["opt"]) and b["use"][1] - b["use"][0] + 1 >= sec(BROLL_MIN_S)]
            have = {stem(w) for _, w in ws if stem(w)}                  # (no moment named: the one saying most of
            pool.sort(key=lambda x: -len(have & x["words"]))           # its words first)
            b = next((x for x in pool if h and (x["clip"], x["m"]) == (h["clip"], h["m"])), None) or (
                pool[0] if pool else None)
            if b is None:
                c["skip"] = "no B-roll clip left with a usable part" + (f" in clip {s['opt']}" if s.get("opt") else "")
            else:
                said = word_at(s, s.get("text"))             # (the word Claude named, else the one the rules found)
                f = (said + sec(BROLL_LATE_S) if said is not None else
                     h["f"] + sec(BROLL_LATE_S) if h and b["clip"] == h["clip"] else f0 + sec(0.5))
                u0, u1 = b["use"]
                f, n = card(f, min(sec(BROLL_LEN_S), u1 - u0 + 1), f0, f1)
                if n < sec(BROLL_MIN_S):
                    c["skip"] = f"the segment is too short for B-roll ({n} frames)"
                else:
                    inn = u0 + (u1 - u0 + 1 - n) // 2
                    a = b.get("anchor")
                    out.append(f"broll {b['clip']} at f{f} for {n} from {inn}"
                               + (f" anchor={a[0]:.3f},{a[1]:.3f}" if a else ""))
                    used_m.add((b["clip"], b["m"]))
                    c.update(f=f, end=f + n - 1, src=b["clip"])
        elif t == "number":
            k = s.get("num")
            v = num_value(ws[k][1]) if k is not None else None
            if v is None:
                c["skip"] = "no number said in it"
            else:
                w = ws[k][1]
                rest = [x for _, x in ws[k + 1:]]
                unit = UNITS.get(SB.norm(rest[0])) if rest else None
                tid = s.get("opt") or TEMPLATE["number"]
                f, n = card(ws[k][0], sec(LEN_S["number"]), f0, f1)
                vals = {"from": 0, "to": v, "decimals": 0 if v == int(v) else 1, "label": "", "tag": "",
                        "prefix": "$" if "$" in w else "", "suffix": "%" if "%" in w else unit or "",
                        "caption": _clean(s["text"]) if s.get("text") else _phrase(rest[1:] if unit else rest, 4)}
                out.append(gline(tid, f, n, vals, f"{w.strip('.,!?')} {vals['caption']}"))
                c.update(f=f, template=tid)
        elif t == "title":
            k = _opener(s)
            say = [x for _, x in ws]
            top = _clean(str(s.get("topic") or ""))
            if s.get("text"):                                # Claude's words: "line 1|line 2"
                a, _, b = str(s["text"]).partition("|")
                l1, l2 = _clean(a), _clean(b)
            elif top:                                        # a topic's name (after "Number two" when it opens)
                l1, l2 = (_clean(" ".join(say[:k])), top) if k else (top, "")
            else:
                l1, l2 = (_clean(" ".join(say[:k])), _phrase(say[k:], 4)) if k else (_phrase(say, 4), "")
            tid = s.get("opt") or TEMPLATE["title"]
            f, n = card(ws[0][0] if ws else f0, sec(LEN_S["title"]), f0, f1)
            out.append(gline(tid, f, n, {"line1": l1, "line2": l2}, f"{l1} {l2}".strip()))
            c.update(f=f, template=tid)
        elif t == "list":
            items = _items(s)
            own = [_clean(x) for x in str(s.get("text") or "").split("|") if _clean(x)]
            if own:                                          # Claude's items "a|b|c" (the card starts where it did)
                items = [(items[min(j, len(items) - 1)][0] if items else f0, x) for j, x in enumerate(own[:6])]
            tid = s.get("opt") or TEMPLATE["list"]
            f, n = card(items[0][0] if items else f0, f1 - f0 + 1, f0, f1)
            vals = {"title": "", **{f"item{j + 1}": (items[j][1] if j < len(items) else "") for j in range(6)},
                    "steps": "|".join(x for _, x in items)}
            out.append(gline(tid, f, n, vals, " / ".join(x for _, x in items)))
            c.update(f=f, template=tid)
        elif t == "graphic":
            tid = s.get("template") or (ctx["any_graphic"](s.get("say") or "", used_t) if ctx.get("any_graphic")
                                        else None)
            if not tid:
                c["skip"] = "no template found for its words"
            else:
                used_t.add(tid)
                f, n = card(min(max(int(s.get("key", f0)), f0), f1), sec(LEN_S["graphic"]), f0, f1)
                out.append(gline(tid, f, n, {}, _clean(s["text"]) if s.get("text") else _phrase([x for _, x in ws], 6)))
                c.update(f=f, template=tid)
        elif t == "screen":
            f = min(max(int(s.get("key", f0)), f0), max(f0, f1 - sec(1.2)))
            out.append(f"effect slow-push at f{f}")
            c["f"] = f
        elif t == "drop":
            L = under(f0)
            out.append(f"effect flash at f{f0}")
            moving = L is not None and any(isinstance(a, dict) for a in (L.get("anchor") or []))
            out.append(f"effect {'punch-in' if moving else 'shake'} at f{f0}")    # (a shake would stop a pan)
            c["f"] = f0
        elif t == "beat":
            beats = sorted(int(b) for b in ctx.get("beats") or [] if f0 < b <= f1)
            k = 0
            for L in shots:
                if L["end"] < f0 or L["start"] > f1 or L.get("jumps") or L.get("hold"):
                    continue
                n_src = int(((P.get("sources") or {}).get(L["src"]) or {}).get("frames") or 0)
                wins = sorted((ctx.get("usable") or {}).get(L["src"]) or ([[0, n_src - 1]] if n_src else []))
                last, pos = int(L["start"]), int(L.get("in", 0))
                bs = [b for b in beats if L["start"] < b <= min(L["end"], f1) and L["end"] - b + 1 >= sec(BEAT_MIN_S)]
                for j, b in enumerate(bs):
                    if b - last < sec(BEAT_MIN_S):
                        continue
                    nxt = next((x for x in bs[j + 1:] if x - b >= sec(BEAT_MIN_S)), int(L["end"]) + 1)
                    to = _fit_in(wins, pos + (b - last) + sec(BEAT_SKIP_S), nxt - b)
                    if to is None:                   # (no usable part that long anywhere in the clip)
                        break
                    out.append(f"jump f{b} to {to}")
                    last, pos, k = b, to, k + 1
            if not k:
                c["skip"] = "no beat inside its shots to cut on"
            c["jumps"] = k
        if c.get("skip"):
            out = [f"# not built: {c['skip']}"]
        lines += ["", f"# {s['n']}. f{f0}-f{f1} ({frame_to_tc(f0, fps)}-{frame_to_tc(f1, fps)}) {t} ({s.get('by', 'rules')})"
                  f" - {s['why']}"] + out
        claims.append(c)
    return lines, claims


def verify(base: dict, built: dict, claims: list[dict]) -> dict:
    """The built plan against the picks: every cut where it was, each segment's pick in it, nothing added inside a
    plain one -> {"ok", "lines" (one a segment, "ok" or what is missing), "broll_share"}."""
    from . import editlist as EL
    from .compose import Curve
    fps, N = float(built["fps"]), int(built["frames"])
    zoom = lambda P, L, f: float(Curve(L.get("zoom"), P.get("curves") or {}, 1.0)(f))     # noqa: E731
    out, ok = [], True
    c0, c1 = [int(L["start"]) for L in EL.shots(base)], [int(L["start"]) for L in EL.shots(built)]
    if c0 != c1 or int(base["frames"]) != N:
        ok = False
        moved = sorted(set(c0) ^ set(c1))[:6]
        out.append(f"the cuts changed: {len(c0)} -> {len(c1)} shots, {base['frames']} -> {N} frames"
                   + (f" (at f{', f'.join(map(str, moved))})" if moved else ""))
    old = {L.get("id") for L in base["layers"]}
    new = [L for L in built["layers"] if L.get("id") not in old and not str(L.get("id", "")).startswith("captions_")]
    S0, S1 = EL.shots(base), EL.shots(built)
    at = lambda S, f: next((x for x in S if x["start"] <= f <= x["end"]), None)       # noqa: E731
    for c in claims:
        t, f0, f1 = c["t"], c["f0"], c["f1"]
        inside = [L for L in new if f0 <= int(L.get("start", 0)) <= f1]
        if c.get("skip"):
            good, why = all(L.get("type") != "overlay" and not str(L.get("id", "")).startswith("broll_")
                            for L in inside), f"not built ({c['skip']})"
        elif t == "plain":
            same = all(abs(zoom(base, at(S0, f), f) - zoom(built, at(S1, f), f)) < 1e-3
                       for f in range(f0, f1 + 1, 3) if at(S0, f) and at(S1, f))
            good, why = not inside and same, "nothing added" if not inside and same else \
                f"something added: {', '.join(str(L.get('id')) for L in inside) or 'a zoom'}"
        elif t in ("punch", "screen"):
            f = c["f"] + (int(round(fps)) if t == "screen" else 0)
            L0, L1 = at(S0, f), at(S1, f)
            good = bool(L0 and L1 and zoom(built, L1, min(f, L1["end"])) > zoom(base, L0, min(f, L0["end"]))
                        * (1.03 if t == "punch" else 1.005))
            why = f"closer from f{c['f']}" if good else f"no zoom at f{c['f']}"
        elif t == "broll":
            good = any(str(L.get("id", "")).startswith("broll_") and L.get("src") == c["src"] and int(L["start"]) == c["f"]
                       for L in inside)
            why = f"clip {c['src']} f{c['f']}-f{c['end']}" if good else f"no B-roll of clip {c['src']} at f{c['f']}"
        elif t in ("number", "title", "list", "graphic"):
            g = [L for L in inside if L.get("type") == "overlay" and c["template"] in str(L.get("id", ""))]
            good = bool(g) and all(int(L["end"]) <= f1 for L in g)
            why = (f"{c['template']} f{g[0]['start']}-f{g[0]['end']}" if good else
                   f"{c['template']} {'runs past the segment' if g else 'missing'}")
        elif t == "drop":
            L1 = at(S1, f0)
            good = bool(L1 and str(f0) in (L1.get("flash_over") or {}))
            why = f"a flash at f{f0}" if good else f"no flash at f{f0}"
        elif t == "beat":
            js = sum(1 for L in S1 for j in L.get("jumps") or [] if f0 < int(j[0]) <= f1)
            good, why = js >= c.get("jumps", 0) > 0, f"{js} cut(s) on the beat"
        else:
            good, why = False, f"{t}: no check"
        ok = ok and good
        out.append(f"{c['n']}. {t}: {'ok' if good else 'MISSING'} - {why}")
    cov = set()
    for L in built["layers"]:
        if L.get("type") == "clip" and str(L.get("id", "")).startswith("broll"):
            cov |= set(range(int(L["start"]), int(L["end"]) + 1))
    return {"ok": ok, "lines": out, "broll_share": round(len(cov) / max(1, N), 3)}


# ------------------------------------------------------------------------------------------------ self-check
def selfcheck() -> dict:
    t0, lines, ok = time.time(), [], True

    def case(what, cond):
        nonlocal ok
        ok = ok and bool(cond)
        lines.append(("PASS " if cond else "FAIL ") + what)

    def say(text, t, step=0.3, gap_after=None):     # words from t, one every `step` s; a pause after the last
        out = []
        for k, w in enumerate(text.split()):
            out.append({"t": round(t + k * step, 3), "t1": round(t + k * step + step * 0.9, 3), "w": w})
        return out
    fps = 30.0
    W = (say("Here are five quick edits that keep people watching all the way to the end.", 0.0)   # 0 - 4.5
         + say("Number one, cut the pauses and number two, punch in on the word.", 5.5)    # (pauses of ~1 s)
         + say("It works because the eye wants something new every few seconds", 10.6)
         + say("so you give it one.", 14.3)
         + say("Next, the B-roll: show the keyboard when you say keyboard.", 17.0)
         + say("That is it.", 21.0))
    N = int(23 * fps)
    S = talk(W, fps, N)
    case(f"talk: sentences grouped into beats of 3-12 s, never cut inside one, tiling the edit "
         f"({[(s['f0'], s['f1']) for s in S]})",
         len(S) >= 3 and S[0]["f0"] == 0 and S[-1]["f1"] == N - 1
         and all(a["f1"] + 1 == b["f0"] for a, b in zip(S, S[1:]))
         and all(MIN_S * fps - 1 <= s["f1"] - s["f0"] + 1 for s in S[:-1]))
    starts = {s["words"][0][1] for s in S}
    case("talk: every segment starts on a sentence's first word", starts <= {"Here", "Number", "It", "so", "Next,",
                                                                             "That"})
    kb = {"clip": "C", "m": 2, "words": {"keyboard", "desk"}, "line": "hands typing on a keyboard", "use": [10, 150],
          "anchor": [0.5, 0.45]}
    ctx = {"broll": [kb], "fps": fps, "frames": N}
    R = recommend(S, ctx)
    picks = [s["pick"] for s in R]
    lst = next((s for s in R if "Number" in s["say"]), None)
    kbs = next((s for s in R if "keyboard" in s["say"]), None)
    case(f"the rules: the hook's number -> number, the counting part -> list, 'keyboard' with a clip that shows one -> "
         f"B-roll ({picks}; {[s['why'] for s in R]})",
         R[0]["pick"] == "number" and lst is not None and lst["pick"] == "list" and kbs is not None
         and kbs["pick"] == "broll" and "keyboard" in kbs["why"])
    case("each segment: its pick, why in one line, two alternatives, all it can have",
         all(len(s["alts"]) == 2 and s["pick"] not in [a["t"] for a in s["alts"]] and s["pick"] in s["can"]
             and s["why"] for s in R))
    flat = [{"kind": "talk", "f0": i * 120, "f1": i * 120 + 119, "say": "ok", "words": [[i * 120, "ok"]], "n": i + 1,
             "key": i * 120} for i in range(6)]
    case("nothing special said: a punch-in first (the hook), then plain and punch-ins in turn",
         [s["pick"] for s in recommend(flat)] == ["punch", "plain", "punch", "plain", "punch", "plain"])
    same = [{"kind": "talk", "f0": i * 120, "f1": i * 120 + 119, "say": "about thirty", "n": i, "key": i * 120,
             "words": [[i * 120, "about"], [i * 120 + 9, "thirty"]]} for i in range(4)]
    case("never one treatment three times in a row (four numbers: the third takes its alternative)",
         [s["pick"] for s in recommend(same)][:3] in (["number", "number", "punch"], ["number", "number", "plain"]))
    db = list(range(0, 900, 60))                     # a bar every 2 s (120 bpm), 30 s
    M = music(db, [480], fps, 900, 120)
    mp = recommend(M)
    drop = next((s for s in M if s.get("drop")), None)
    case(f"music: phrases of bars that fit MAX_S (4 bars = 8 s at 120 bpm), the drop its own segment starting on it, "
         f"the phrase before it the build-up ({[(s['f0'], s['say'], s['pick']) for s in mp]})",
         drop is not None and drop["f0"] == 480 and drop["pick"] == "drop" and M[0]["f0"] == 0
         and M[-1]["f1"] == 899 and mp[M.index(drop) - 1]["pick"] == "beat" and mp[0]["pick"] == "plain"
         and all((s["f1"] - s["f0"] + 1) / fps <= MAX_S + 0.01 for s in M))
    M2 = music(list(range(40, 900, 60)), [303, 771], fps, 900, 120)  # a pickup before the first downbeat, two drops
    case(f"music: no piece under {MIN_S:g} s (a pickup joins the first phrase, a bar left by a drop joins a neighbour), "
         f"each drop still starts its own ({[(s['f0'], s['f1']) for s in M2]})",
         all((s["f1"] - s["f0"] + 1) / fps >= MIN_S - 0.01 for s in M2) and {303, 771} <= {s["f0"] for s in M2})
    C = clips([(0, 40), (41, 80), (81, 130), (131, 200), (201, 260), (261, 330)], fps, 331)
    case(f"a montage: its shots in runs of 3-12 s ({[(s['f0'], s['f1']) for s in C]})",
         C[0]["f0"] == 0 and C[-1]["f1"] == 330 and all(a["f1"] + 1 == b["f0"] for a, b in zip(C, C[1:]))
         and all((s["f1"] - s["f0"] + 1) / fps >= MIN_S - 0.01 for s in C))
    case("the key word: a number said first, else the longest content word",
         key_word({"words": [[1, "the"], [2, "people"], [3, "watching"]]}) == (3, "watching")
         and key_word({"words": [[1, "keeps"], [2, "30"], [3, "seconds"]]}) == (2, "30"))
    # ---- step 3: the user's picks, kept through a re-run; the limits
    import copy
    from . import editlist as EL

    def plan(cut_front=0):                           # the talk above as two takes of clip A (a jump cut at f300)
        P = {"fps": fps, "frames": N - cut_front, "width": 1080, "height": 1920,
             "sources": {"A": {"frames": 2000}, "C": {"frames": 200}},
             "layers": [{"type": "clip", "id": "s01_A", "src": "A", "start": 0, "end": 299 - cut_front,
                         "rect": [0, 0, 1080, 1920], "in": 40 + cut_front},
                        {"type": "clip", "id": "s02_A", "src": "A", "start": 300 - cut_front, "end": N - 1 - cut_front,
                         "rect": [0, 0, 1080, 1920], "in": 400, "zoom": 1.3}]}
        return P
    P1 = plan()
    S1 = talk(W, fps, N, [300])
    for s in S1:
        s["at"] = anchor(P1, s)
    third = S1[2]["n"]
    mine_p = [{"at": S1[2]["at"], "t": "graphic", "opt": "word-pills"}, {"at": {"src": "A", "at": 5}, "t": "plain"}]
    P2 = plan(9)                                     # a re-run: the edit starts 9 frames later in the take
    W2 = [{**w, "t": round(w["t"] - 9 / fps, 3), "t1": round(w["t1"] - 9 / fps, 3)} for w in W if w["t"] >= 9 / fps]
    S2 = talk(W2, fps, N - 9, [291])
    for s in S2:
        s["at"] = anchor(P2, s)
    m2, lost = mine_for(S2, mine_p, fps)
    case(f"a user's pick stays on its part through a re-run (its frames moved 9 earlier: segment {third} still), "
         f"one whose part is gone is kept aside ({m2}, {len(lost)} lost)",
         list(m2) == [third] and m2[third]["t"] == "graphic" and len(lost) == 1)
    R2 = recommend(S2, {**ctx, "frames": N - 9}, mine=m2)
    case("the user's pick is the pick (by: user, its template), the rules' own kept beside it as 'rule'",
         R2[third - 1]["pick"] == "graphic" and R2[third - 1]["by"] == "user"
         and R2[third - 1].get("template") == "word-pills" and R2[third - 1]["rule"]["t"] != "graphic")
    alone = [dict(s, n=s["n"]) for s in flat]
    mine1 = {1: {"t": "plain"}}
    case("a pick of the user's changes its own part only (part 1 set to plain: the rest as the rules had them)",
         [s["pick"] for s in recommend(alone, mine=mine1)][1:] == [s["pick"] for s in recommend(flat)][1:]
         and alone[0]["pick"] == "plain")
    # ---- step 7: Claude's picks between the rules' and the user's, its topics, its words
    cl = {2: {"t": "title", "why": "the second idea starts here", "text": "Cut the pauses|Then punch in"},
          4: {"t": "plain", "why": "let the example breathe"}, 5: {"t": "drop", "why": "no drop in a talk"}}
    Rc = recommend([dict(s) for s in flat], claude=cl, mine={4: {"t": "graphic"}})
    Rs = recommend([dict(s) for s in flat], claude=cl)
    case(f"Claude's pick is the suggestion (by claude, its own why, its words), the user's over it (Claude's kept "
         f"under it: back to the suggestion = Claude's), one a part cannot have left out "
         f"({[(s['pick'], s['by']) for s in Rc]})",
         Rc[1]["pick"] == "title" and Rc[1]["by"] == "claude" and Rc[1]["why"] == "the second idea starts here"
         and Rc[1]["why_k"] is None and Rc[1]["text"] == "Cut the pauses|Then punch in"
         and Rc[3]["pick"] == "graphic" and Rc[3]["by"] == "user" and Rc[3]["claude"]["t"] == "plain"
         and "text" not in Rc[3] and Rs[3]["pick"] == "plain" and Rs[3]["by"] == "claude" and Rc[4]["by"] == "rules"
         and [s["pick"] for k, s in enumerate(Rc) if k != 3] == [s["pick"] for k, s in enumerate(Rs) if k != 3])
    Ru = recommend([dict(s) for s in flat], claude=cl, mine={2: {"t": "title"}, 4: {"t": "title", "text": "Mine|Own"}})
    case("the user's pick of Claude's treatment takes Claude's words where theirs has none (and keeps its own)",
         Ru[1]["by"] == "user" and Ru[1]["pick"] == "title" and Ru[1]["text"] == "Cut the pauses|Then punch in"
         and Ru[3]["by"] == "user" and Ru[3]["text"] == "Mine|Own")
    tp = [dict(s) for s in flat]
    tp[0]["topic"], tp[2]["topic"] = "The hook", "Color grade"
    Rt = recommend(tp)
    case("a topic Claude marked: its title (named) where it starts, never on the hook",
         Rt[2]["pick"] == "title" and "Color grade" in Rt[2]["why"] and Rt[0]["pick"] != "title")
    Sk = recommend(copy.deepcopy(S1), ctx, claude={1: {"t": "punch", "why": "stress it", "text": "quick"}})
    case("Claude's punch-in lands on the word it names",
         Sk[0]["pick"] == "punch" and Sk[0]["key"] == word_at(Sk[0], "quick") is not None
         and word_at(Sk[0], "nowhere") is None)
    many = [{"kind": "talk", "f0": i * 150, "f1": i * 150 + 149, "n": i + 1, "key": i * 150, "say": "the keyboard",
             "words": [[i * 150, "the"], [i * 150 + 10, "keyboard"]]} for i in range(8)]
    Rb = recommend(many, {"broll": [kb], "fps": fps, "frames": 1200})
    nb = sum(1 for s in Rb if s["pick"] == "broll")
    case(f"the rules' B-roll stops at the cover budget (8 segments that all say 'keyboard': {nb} B-roll, under 40 % "
         f"of 40 s at 2.5 s each) and never on the hook",
         0 < nb <= 6 and Rb[0]["pick"] != "broll")
    lk = like(R, R[1]["n"])
    case("Apply to all like this: the segments the rules gave the same pick", all(R[n - 1]["rule"]["t"] ==
                                                                                   R[1]["rule"]["t"] for n in lk))
    # ---- step 4: the build - edit-list lines on the bare draft, then the check
    for s in S1:
        s["pick"], s["by"], s["why"] = "plain", "rules", "test"
    S1[0].update(pick="punch", key=S1[0]["words"][3][0])
    S1[1].update(pick="broll", hit={"clip": "C", "m": 2, "f": S1[1]["words"][2][0], "word": "x"})
    Lb, Cb = build_list(S1, P1, {"broll": [kb]})
    try:
        Pb, done, steps = EL.apply(P1, EL.parse("\n".join(Lb)))
        V = verify(P1, Pb, Cb)
    except EL.ListError as e:
        Pb, done, V = None, [str(e)], {"ok": False, "lines": [str(e)]}
    case(f"the build: a punch-in on the key word (back at the segment's end when its shot goes on), B-roll on the "
         f"word, nothing in the plain ones; verify finds every pick and every cut where it was ({V['lines']})",
         V["ok"] and any(ln.startswith("broll C at f") for ln in Lb) and sum(ln.startswith("punch-in") for ln in Lb) >= 1)
    bad = copy.deepcopy(Pb) if Pb else {"layers": [], "frames": 0, "fps": fps}
    bad["layers"] = [L for L in bad["layers"] if not str(L.get("id", "")).startswith("broll_")]
    bad["layers"][-1]["zoom"] = 1.5 if bad["layers"] else 1
    V2 = verify(P1, bad, Cb)
    case(f"verify: a pick missing from the plan, or something added inside a plain segment, is reported "
         f"({[ln for ln in V2['lines'] if 'MISSING' in ln]})",
         not V2["ok"] and any("broll: MISSING" in ln for ln in V2["lines"])
         and any("plain: MISSING" in ln for ln in V2["lines"]))
    Pm = {"fps": fps, "frames": 900, "width": 1080, "height": 1920, "sources": {"A": {"frames": 700}},
          "layers": [{"type": "clip", "id": "s01_A", "src": "A", "start": 0, "end": 479, "rect": [0, 0, 1080, 1920],
                      "in": 0}, {"type": "clip", "id": "s02_A", "src": "A", "start": 480, "end": 899,
                                 "rect": [0, 0, 1080, 1920], "in": 20}]}
    for s in M:
        s["by"] = "rules"
    Lm, Cm = build_list(M, Pm, {"beats": list(range(0, 900, 15))})
    try:
        Pmb = EL.apply(Pm, EL.parse("\n".join(Lm)))[0]
        Vm = verify(Pm, Pmb, Cm)
    except EL.ListError as e:
        Vm = {"ok": False, "lines": [str(e)]}
    case(f"the build, music: cuts on the beat inside the clip (wrapping to its start before its end), a flash and a "
         f"shake on the drop ({Vm['lines']})", Vm["ok"] and any(ln.startswith("jump f") for ln in Lm))
    try:
        EL.apply(P1, EL.parse("broll C at f10 for 60 from 180"))
        past = False
    except EL.ListError:
        past = True
    case("the list's B-roll line refuses a part past its clip's end", past)
    case("a beat cut stays inside one usable part of its clip (a catalogue moment ends at 54: a 13-frame piece from "
         "52 goes to 55), from the clip's start again past its last, none when no part is that long",
         _fit_in([[0, 54], [55, 88], [89, 103]], 52, 13) == 55 and _fit_in([[0, 54], [55, 88]], 80, 13) == 0
         and _fit_in([[0, 10]], 3, 30) is None and _fit_in([], 7, 5) == 7)
    case("a card's words: the number's value, its unit, a phrase cut at its punctuation",
         num_value("200") == 200 and num_value("five") == 5 and num_value("2.5x") == 2.5 and num_value("so") is None
         and _phrase(["every", "graphic,", "I", "add"], 6) == "Every graphic"
         and [x for _, x in _items({"words": [[0, "Number"], [1, "one,"], [2, "cut"], [3, "pauses"], [4, "and"],
                                             [5, "number"], [6, "two,"], [7, "punch"], [8, "in."]]})]
         == ["Cut pauses", "Punch in"])
    S3 = copy.deepcopy(S1)
    for s in S3:
        s.update(pick="plain", by="rules", why="test")
        s.pop("hit", None)
    S3[1].update(pick="title", by="claude", text="Cut the pauses|Then punch in")
    S3[2].update(pick="title", topic="Why it works")
    S3[3].update(pick="list", by="claude", text="Show it|Say it")
    L3 = build_list(S3, P1, {})[0]
    case(f"the cards' words: Claude's where it wrote them (a title's two lines, a list's items), a topic's name on its "
         f"title ({[ln for ln in L3 if ln.startswith('graphic')]})",
         any('line1="Cut the pauses"' in ln and 'line2="Then punch in"' in ln for ln in L3)
         and any('line1="Why it works"' in ln for ln in L3)
         and any('item1="Show it"' in ln and 'item2="Say it"' in ln and 'item3=""' in ln for ln in L3))
    return {"passed": ok, "seconds": round(time.time() - t0, 3), "lines": lines}
